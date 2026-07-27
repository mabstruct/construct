"""Durable, human-gated ``research.run`` LangGraph workflow (Phase 10).

This module composes the already-built Phase 8 search (``research_search``) and
Phase 9 scoring (``research_score.run_gate``) into one durable LangGraph
``StateGraph`` whose single pause is a native ``interrupt()`` human-review gate.
The interrupt is the durability boundary: **no refs/cards/seeds/digest are
written before approval** because every write node is strictly downstream of the
gate, and the gate node re-executes top-to-bottom on resume (RESEARCH Pitfall 1,
empirically confirmed) — so it contains *only* ``interrupt()``.

Plan 03 builds the read-side: the state channel, the in-module I/O models, the
pre-gate nodes (``load_config`` → ``build_queries`` → ``execute_search`` →
``deduplicate`` → ``score_and_extract``), the interrupt-only ``gate_review``
node, ``build_research_run_graph`` + the ``SqliteSaver`` checkpointer wiring, and
a run-start runner that pauses at the gate. The post-gate write nodes exist here
as no-write skeletons so the graph compiles and pauses; **Plan 04 implements
their bodies**.

Design constraints honored here:
  * State channels hold ONLY plain serializable data — never a ``WorkspaceLoader``,
    LLM client, or sqlite connection (RESEARCH Pitfall 3).
  * I/O models live in THIS module, not ``catalog.py`` (avoid the circular-import
    hazard between the capability catalog and the gate runner).
  * Nodes log to stderr via ``logging`` only — never the builtin stdout writer
    (WR-04 / Pitfall 6: stdout is the MCP JSON-RPC transport).
  * The checkpointer uses ``SqliteSaver(sqlite3.connect(..., check_same_thread=False))``
    kept alive for the handler — never wrapped in a transient connection-string
    context manager (RESEARCH Pitfall 2: that closes the connection and breaks
    cross-process resume).
"""
from __future__ import annotations

import logging
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field, field_validator

from construct.llm.curation_run import (
    _ensure_proposal_ids,
    _new_proposal_id,
    _validate_proposal_id,
)
from construct.schemas.config import KEBAB_CASE_PATTERN

logger = logging.getLogger(__name__)

# GOV-02: the proposal-identity primitives are imported from ``curation_run``
# rather than re-declared here ON PURPOSE. Two independent implementations of the
# same contract is the parity fork this requirement exists to close — it is how
# this module ended up with a url-keyed decision mode the curation graph never
# had. ``curation_run`` imports nothing from this module, so the direction is
# acyclic.

# Title fuzzy near-dup threshold (D-05 — basic this phase).
_TITLE_FUZZY_THRESHOLD = 0.90


def _validate_run_id(value: str | None) -> str | None:
    """Reject any ``run_id`` that is not kebab-case (CR-01 trust-boundary guard).

    ``run_id`` is interpolated into the digest filename (``digest-{run_id}.md``)
    and used as the LangGraph ``thread_id``. The MCP shims pass caller-supplied
    ``**kwargs`` straight into the input models, so an unvalidated value such as
    ``"../../../tmp/evil"`` would escape the workspace. Constraining it to
    ``KEBAB_CASE_PATTERN`` ([a-z0-9] segments joined by single hyphens) makes
    path traversal impossible at the boundary; ``None`` is allowed (run-start
    auto-generates a safe id).
    """
    if value is not None and KEBAB_CASE_PATTERN.fullmatch(value) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9] segments joined by single hyphens)")
    return value


# ── State schema (TypedDict — LangGraph prefers this; plain serializable data ONLY) ──


class ResearchRunState(TypedDict):
    # Input (set before the graph starts)
    workspace_path: str
    run_id: str
    gate_id: str
    provider_override: str | None

    # Governance caps (loaded by load_config)
    relevance_threshold: float
    card_creation_threshold: float
    max_papers_per_cycle: int

    # Processing (populated by pre-gate nodes)
    queries: list[str]
    queried_clusters: list[str]
    search_results: list[dict]  # SearchResult dumps (serializable)
    deduped: list[dict]
    findings: list[dict]  # ScoredFinding dumps
    retrieval: dict
    gate_queue: list[dict]  # GateQueueEntry dumps (per-finding, default = ingest_action)
    decisions: Any  # resume payload from the human gate

    # Output (final / post-gate — filled by Plan 04 write nodes)
    status: str  # running | awaiting_review | completed | failed
    ingested: list[str]
    refs_created: list[str]
    cards_created: list[str]
    skipped_existing: list[str]
    rejected: list[str]
    digest_path: str | None
    seed_update: str | None
    events: list[str]


# ── In-module I/O models (defined HERE, not catalog.py — avoid circular import) ──


class ResearchRunInput(BaseModel):
    """Input for the ``research.run`` capability (run-start)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str | None = None
    provider_override: str | None = None

    _check_run_id = field_validator("run_id")(_validate_run_id)


class ReviewInput(BaseModel):
    """Input for ``research.review`` (resume with per-finding decisions, Plan 04)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str
    decisions: list[dict] | None = None
    approve_all: bool = False
    reject_all: bool = False

    _check_run_id = field_validator("run_id")(_validate_run_id)


class InspectInput(BaseModel):
    """Input for ``research.inspect`` (read pending batch via ``get_state``, Plan 04)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str

    _check_run_id = field_validator("run_id")(_validate_run_id)


class GateQueueEntry(BaseModel):
    """One per-finding review item: the scored finding + its default decision.

    The default ``decision`` is the LLM's ``ingest_action`` from ``research.score``
    (D-04): ``approve-all`` reproduces the recommended ingest set; ``reject-all``
    sets every decision to ``skip``.

    ``proposal_id`` (GOV-02 / D-09) is the same opaque 32-character name the
    curation queue carries, minted at enqueue by the same factory. It replaces the
    finding ``url`` this module previously keyed decisions on — a content-derived
    value that may be ``None`` and is not unique across findings.
    """

    model_config = {"extra": "forbid"}
    proposal_id: str = Field(default_factory=_new_proposal_id)
    finding: dict
    decision: str  # skip | ref_only | ref_and_card

    _check_proposal_id = field_validator("proposal_id")(_validate_proposal_id)


class RunResult(BaseModel):
    """Result surface for a ``research.run`` invocation (D-12 fields).

    Plan 03 populates the run-start shape (``awaiting_review`` + gate handle +
    pending ``gate_queue``); the completion counts/digest/seed/event fields are
    filled by the Plan 04 write nodes and review runner.
    """

    model_config = {"extra": "forbid"}
    status: str  # awaiting_review | completed | failed
    run_id: str
    gate_id: str | None = None
    gate_queue: list[dict] = Field(default_factory=list)
    refs_created: list[str] = Field(default_factory=list)
    cards_created: list[str] = Field(default_factory=list)
    digest_path: str | None = None
    seed_update: str | None = None
    events: list[str] = Field(default_factory=list)
    degraded: bool = False
    message: str = ""


# ── State helpers ──


def _new_run_id() -> str:
    """Generate a sortable, kebab-safe run/gate handle: UTC timestamp + random suffix.

    The stamp uses ``-`` (not ISO ``T``) between date and time so the handle
    satisfies ``KEBAB_CASE_PATTERN`` — the same invariant ``_validate_run_id``
    enforces on caller-supplied ids (CR-01).
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"run-{stamp}-{secrets.token_hex(3)}"


def _initial_state(inp: ResearchRunInput) -> dict:
    """Build the initial graph state from validated input (all plain data)."""
    run_id = inp.run_id or _new_run_id()
    return {
        "workspace_path": inp.workspace_path,
        "run_id": run_id,
        "gate_id": run_id,
        "provider_override": inp.provider_override,
        "relevance_threshold": 0.0,
        "card_creation_threshold": 0.0,
        "max_papers_per_cycle": 0,
        "queries": [],
        "queried_clusters": [],
        "search_results": [],
        "deduped": [],
        "findings": [],
        "retrieval": {},
        "gate_queue": [],
        "decisions": None,
        "status": "running",
        "ingested": [],
        "refs_created": [],
        "cards_created": [],
        "skipped_existing": [],
        "rejected": [],
        "digest_path": None,
        "seed_update": None,
        "events": [],
    }


# ── Pre-gate node 1: load governance caps + gate handle ──


def load_config(state: ResearchRunState) -> dict:
    """Load governance research caps read-only and set the gate handle.

    Rebuilds ``WorkspaceLoader`` INSIDE the node (never store it in state —
    Pitfall 3). Reads ``governance.yaml`` research thresholds; the gate_id is the
    run handle that the human review/inspect calls address.
    """
    from construct.storage.workspace import WorkspaceLoader

    research = WorkspaceLoader(Path(state["workspace_path"])).load_governance().research
    return {
        "gate_id": state.get("gate_id") or state["run_id"],
        "relevance_threshold": research.relevance_threshold,
        "card_creation_threshold": research.card_creation_threshold,
        "max_papers_per_cycle": research.max_papers_per_cycle,
    }


# ── Pre-gate node 2: build deterministic query list from active clusters (D-10) ──


def build_queries(state: ResearchRunState) -> dict:
    """Build a deterministic query list from active search clusters.

    Excludes non-active clusters (``paused``/``exhausted``) and reserved
    empty-term ingest clusters (``manual-ingest``/``web-ingest``). Caps the list
    at governance ``max_papers_per_cycle``.
    """
    from construct.pipelines.research_search import RESERVED_INGEST_CLUSTERS
    from construct.schemas.config import SearchClusterStatus
    from construct.storage.workspace import WorkspaceLoader

    seeds = WorkspaceLoader(Path(state["workspace_path"])).load_search_seeds()
    queries: list[str] = []
    queried_clusters: list[str] = []
    for cluster in seeds.clusters:
        if cluster.status != SearchClusterStatus.active:
            continue
        if cluster.id in RESERVED_INGEST_CLUSTERS:
            continue
        if not cluster.terms:
            continue
        queries.append(" ".join(cluster.terms))
        queried_clusters.append(cluster.id)

    cap = state.get("max_papers_per_cycle") or 0
    if cap > 0:
        queries = queries[:cap]
        queried_clusters = queried_clusters[:cap]

    logger.info("research.run built %d queries from active clusters", len(queries))
    return {"queries": queries, "queried_clusters": queried_clusters}


# ── Pre-gate node 3: execute provider-agnostic search (Phase 8 seam) ──


def _run_search(
    workspace_path: str, queries: list[str], provider_override: str | None
) -> list[dict]:
    """Call ``research_search`` and flatten the batches into SearchResult dicts.

    Isolated as a helper so tests can monkeypatch the provider call. Returns an
    empty list when there are no queries or the search degrades.
    """
    if not queries:
        return []
    from construct.pipelines.research_search import ResearchSearchInput, research_search

    result = research_search(
        ResearchSearchInput(
            workspace_path=workspace_path,
            queries=list(queries),
            provider_override=provider_override,
        )
    )
    if not result.success or not result.data:
        logger.warning("research.run search degraded or returned no data")
        return []
    flat: list[dict] = []
    for batch in result.data.get("batches", []):
        for item in batch.get("results", []):
            flat.append(item)
    return flat


def execute_search(state: ResearchRunState) -> dict:
    """Run the search for the built queries; store normalized result dicts."""
    results = _run_search(
        state["workspace_path"], state.get("queries", []), state.get("provider_override")
    )
    logger.info("research.run search returned %d results", len(results))
    return {"search_results": results}


# ── Pre-gate node 4: deterministic, idempotent deduplication (Plan 02 helpers) ──


def deduplicate(state: ResearchRunState) -> dict:
    """Drop candidates already known via refs/, the rejected ledger, or in-batch.

    Filters by normalized URL against the union of existing ref URLs, the rejected
    ledger URLs, and earlier-in-batch URLs; then a title fuzzy secondary pass drops
    candidates near-matching an existing ref title (D-05).
    """
    import json

    from construct.pipelines.research_dedup import (
        load_rejected_ledger,
        normalize_url,
        rejected_normalized_urls,
        title_is_near_dup,
    )

    workspace = Path(state["workspace_path"])

    existing_urls: set[str] = set()
    existing_titles: list[str] = []
    refs_dir = workspace / "refs"
    if refs_dir.exists():
        for ref_path in sorted(refs_dir.glob("*.json")):
            try:
                data = json.loads(ref_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            url = data.get("url")
            if url:
                existing_urls.add(normalize_url(url))
            title = data.get("title")
            if title:
                existing_titles.append(title)

    rejected_urls = rejected_normalized_urls(load_rejected_ledger(workspace))
    blocked = existing_urls | rejected_urls

    deduped: list[dict] = []
    seen_in_batch: set[str] = set()
    for candidate in state.get("search_results", []):
        url = candidate.get("url", "")
        norm = normalize_url(url) if url else ""
        if norm and (norm in blocked or norm in seen_in_batch):
            continue
        title = candidate.get("title", "")
        if title and existing_titles and title_is_near_dup(
            title, existing_titles, threshold=_TITLE_FUZZY_THRESHOLD
        ):
            continue
        if norm:
            seen_in_batch.add(norm)
        deduped.append(candidate)

    logger.info(
        "research.run deduplicated %d → %d candidates",
        len(state.get("search_results", [])),
        len(deduped),
    )
    return {"deduped": deduped}


# ── Pre-gate node 5: score + extract via the Phase 9 L3 gate (outage BEFORE gate) ──


def score_and_extract(state: ResearchRunState) -> dict:
    """Score deduped candidates through ``research_score.run_gate``.

    On a total provider outage (``ResearchScoreOutageError``) this catches the
    error BEFORE the gate, sets ``status='failed'`` and does NOT raise — the graph
    routes to END instead of pausing (see ``build_research_run_graph``). The
    partial-degraded signal (``degraded``/``retried``/``errors``) is carried into
    state for the digest (D-08/09). The default per-finding ``gate_queue`` decision
    is each finding's ``ingest_action`` (D-04).
    """
    from construct.llm import research_score
    from construct.search.models import SearchResult

    results = [SearchResult(**item) for item in state.get("deduped", [])]

    try:
        output = research_score.run_gate(
            "research.score",
            research_score.ResearchScoreInput(
                workspace_path=state["workspace_path"],
                results=results,
                provider_override=state.get("provider_override"),
            ),
        )
    except research_score.ResearchScoreOutageError as exc:
        # T-10-08: surface only the sanitized safe_message; never raw str(exc).
        logger.warning("research.run scoring total outage: %s", exc.safe_message)
        return {
            "status": "failed",
            "findings": [],
            "gate_queue": [],
            "retrieval": {"degraded": True, "total_outage": True},
        }

    findings = [f.model_dump(mode="json") for f in output.findings]
    gate_queue = [
        GateQueueEntry(finding=f, decision=f["ingest_action"]).model_dump(mode="json")
        for f in findings
    ]
    return {
        "status": "running",
        "findings": findings,
        "gate_queue": gate_queue,
        "retrieval": output.retrieval,
    }


# ── The human-review gate (interrupt-ONLY — re-runs on resume; NO side effects) ──


def gate_review(state: ResearchRunState) -> dict:
    """Pause for per-finding human review.

    *** ONLY the interrupt primitive lives here. NO writes, NO event emission, NO
    non-idempotent prep. *** The interrupted node re-executes top-to-bottom on
    resume (RESEARCH Pitfall 1, empirically confirmed), so any side effect here
    would double-fire AND leak a write before approval (breaking RSCH-03). All
    writes live in the downstream post-gate nodes that run only after resume.
    """
    decisions = interrupt(
        {
            "gate_id": state["gate_id"],
            "gate_queue": state["gate_queue"],  # per-finding, default = ingest_action (D-04)
        }
    )
    return {"decisions": decisions}


# ── Post-gate write nodes (REAL — run ONLY after Command(resume); RSCH-03 holds) ──

# The concrete ingest actions that produce a ref (and optionally a card).
_INGEST_ACTIONS = ("ref_only", "ref_and_card")


def _normalize_decision(value: Any, default: str) -> str:
    """Map a resume decision token to a concrete per-finding action.

    Accepts the concrete actions (``skip``/``ref_only``/``ref_and_card``) plus the
    convenience synonyms ``approve`` (→ the LLM's recommended ``default``) and
    ``reject`` (→ ``skip``). ``None`` falls back to the per-finding default. This
    keeps both the structured per-finding payload and the approve-all/reject-all
    shortcuts expressible through one channel.
    """
    if value is None:
        return default
    if value == "approve":
        return default if default in _INGEST_ACTIONS else "skip"
    if value == "reject":
        return "skip"
    return str(value)


def _resolve_decisions(state: ResearchRunState) -> list[str]:
    """Resolve the effective per-finding action list aligned with ``gate_queue``.

    The resume payload (``state['decisions']``) may be ``None`` (use each entry's
    default ``ingest_action``), a positional ``list[str]`` of actions, or a
    ``list[dict]`` keyed by finding ``url``. Anything missing falls back to the
    per-finding default, so a short/partial payload never drops findings.
    """
    gate_queue = state.get("gate_queue", [])
    raw = state.get("decisions")
    resolved: list[str] = []
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        by_url = {d.get("url"): d.get("decision") for d in raw}
        for entry in gate_queue:
            url = entry.get("finding", {}).get("url")
            resolved.append(_normalize_decision(by_url.get(url), entry.get("decision", "skip")))
    elif isinstance(raw, list):
        for i, entry in enumerate(gate_queue):
            value = raw[i] if i < len(raw) else None
            resolved.append(_normalize_decision(value, entry.get("decision", "skip")))
    else:
        for entry in gate_queue:
            resolved.append(entry.get("decision", "skip"))
    return resolved


def ingest_batch(state: ResearchRunState) -> dict:
    """Write approved refs/cards (deterministic IDs, skip-if-exists); ledger rejects.

    Approved findings (``ref_only``/``ref_and_card``) become refs via the v0.3
    ``_write_ref_file`` writer keyed by a deterministic ``ref_id_for`` slug+hash —
    if the ref file already exists it is skipped, never overwritten, so a rerun or
    a mid-batch crash+resume never double-writes (RSCH-05). ``ref_and_card`` also
    creates a deterministically-IDed seed card (skip-if-exists). Rejected/skipped
    findings are appended to the rejected ledger and never written to refs/cards
    (RSCH-03). Per-finding errors are isolated (Phase 9 D-08): one finding raising
    does not abort the batch. The legacy collision-suffix ingest helpers (D-07)
    are NOT used — ID stability comes from hashing the normalized URL.
    """
    from datetime import date

    from construct.pipelines.ingestion import (
        _get_first_domain,
        _seed_card_body,
        _write_ref_file,
    )
    from construct.pipelines.research_dedup import (
        append_rejected,
        normalize_url,
        ref_id_for,
    )
    from construct.schemas.card import CardAuthor
    from construct.schemas.config import ExtractionStatus, ReferenceRecord
    from construct.services.knowledge import create_card

    workspace = Path(state["workspace_path"])
    gate_id = state.get("gate_id") or state["run_id"]
    gate_queue = state.get("gate_queue", [])
    decisions = _resolve_decisions(state)
    domain_id = _get_first_domain(workspace) or "general"

    refs_created: list[str] = []
    cards_created: list[str] = []
    skipped_existing: list[str] = []
    rejected: list[str] = []

    for entry, decision in zip(gate_queue, decisions):
        finding = entry.get("finding", {})
        url = finding.get("url", "")
        title = finding.get("title") or "Untitled"
        norm = normalize_url(url) if url else ""
        try:
            if decision in _INGEST_ACTIONS:
                ref_id = ref_id_for(norm, title)
                ref_path = workspace / "refs" / f"{ref_id}.json"
                if ref_path.exists():
                    skipped_existing.append(ref_id)
                else:
                    ref = ReferenceRecord(
                        id=ref_id,
                        title=title,
                        url=url or f"note://{ref_id}",
                        relevance_score=float(finding.get("relevance_score", 0.0)),
                        key_findings=list(finding.get("key_findings", [])),
                        content_categories=list(finding.get("content_categories", [])),
                        source_tier=int(finding.get("source_tier", 5)),
                        extraction_status=ExtractionStatus.complete,
                        ingested_date=date.today(),
                        domain=domain_id,
                        search_cluster="web-ingest",
                    )
                    _write_ref_file(workspace, ref_id, ref)
                    refs_created.append(ref_id)
                if decision == "ref_and_card":
                    card_id = ref_id  # deterministic: card shares the ref's stable ID
                    card_path = workspace / "cards" / f"{card_id}.md"
                    if card_path.exists():
                        skipped_existing.append(card_id)
                    else:
                        card_data = {
                            "id": card_id,
                            "title": title,
                            "epistemic_type": "finding",
                            "domains": [domain_id],
                            "confidence": 1,
                            "source_tier": int(finding.get("source_tier", 5)),
                            "content_categories": list(finding.get("content_categories", [])),
                            "sources": [{"type": "url", "ref": ref_id}],
                        }
                        body = _seed_card_body(title, "url", list(finding.get("key_findings", [])))
                        card_result = create_card(
                            str(workspace), card_data, author=CardAuthor.construct, body=body
                        )
                        if card_result.success:
                            created_id = (
                                card_result.data.get("id", card_id)
                                if card_result.data
                                else card_id
                            )
                            cards_created.append(created_id)
                        else:
                            logger.warning(
                                "ingest_batch card create failed for %s: %s",
                                title,
                                card_result.message,
                            )
            else:  # skip / reject → ledger only, never a ref/card (RSCH-03)
                if norm:
                    append_rejected(
                        workspace, normalized_url=norm, gate_id=gate_id, title=title
                    )
                rejected.append(title)
        except Exception as exc:  # noqa: BLE001 — per-finding isolation (D-08)
            logger.warning("ingest_batch finding %r failed: %s", title, exc)

    logger.info(
        "ingest_batch: %d refs, %d cards, %d skipped, %d rejected",
        len(refs_created),
        len(cards_created),
        len(skipped_existing),
        len(rejected),
    )
    return {
        "ingested": refs_created + cards_created,
        "refs_created": refs_created,
        "cards_created": cards_created,
        "skipped_existing": skipped_existing,
        "rejected": rejected,
    }


#: Canonical ``DigestRecord`` field → the spelling it carried before D-20.
#: Read-side only: the store is migrated, never a decision (the same discipline
#: D-12 applies to checkpoints).
_DIGEST_LEGACY_KEYS = {
    "domain": "domain_id",
    "theme": "title",
    "date": "generated_at",
    "summary_text": "summary",
}


def _migrate_digest_record(raw: dict) -> dict:
    """Map a pre-D-20 digest record onto the current spelling.

    A record already in the new spelling passes through untouched: each
    canonical key is only filled from its legacy name when it is absent. The
    dropped ``card_ids`` needs no handling — the model ignores unknown keys, so
    it simply does not survive into the rewritten file.
    """
    migrated = dict(raw)
    for canonical, legacy in _DIGEST_LEGACY_KEYS.items():
        if canonical not in migrated and legacy in migrated:
            migrated[canonical] = migrated.pop(legacy)
    return migrated


def _load_digest_store(store_path: Path) -> DigestsFile:
    """Load ``digests/digests.json``, migrating pre-D-20 records on read.

    T-18-18: renaming required fields invalidates every record an existing
    workspace already holds. The previous ``except ValueError: DigestsFile()``
    path would have turned that into silent deletion of a user's entire research
    history on the next ``research.run``, so validation happens per record and a
    record that cannot be migrated is dropped with a warning rather than taking
    its neighbours with it.
    """
    import json

    from pydantic import ValidationError

    from construct.views.models import DigestRecord, DigestsFile

    try:
        raw = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning(
            "digest store at %s is unreadable (%s); starting a new one",
            store_path,
            exc,
        )
        return DigestsFile()

    entries = raw.get("digests") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        logger.warning("digest store at %s has no digests list; starting a new one", store_path)
        return DigestsFile()

    kept: list[DigestRecord] = []
    dropped = 0
    for entry in entries:
        if not isinstance(entry, dict):
            dropped += 1
            continue
        try:
            kept.append(DigestRecord.model_validate(_migrate_digest_record(entry)))
        except ValidationError:
            dropped += 1

    if dropped:
        logger.warning(
            "digest store at %s: %d record(s) could not be migrated and were dropped; "
            "%d kept",
            store_path,
            dropped,
            len(kept),
        )
    return DigestsFile(digests=kept)


def compile_digest(state: ResearchRunState) -> dict:
    """Render the cycle digest markdown + append a ``DigestRecord`` (template, no LLM).

    Builds a deterministic markdown digest from the approved findings and the run
    counts (considered/approved/rejected/ingested) plus the created ref/card IDs
    and — when the score gate degraded — a degraded notice (Phase 9 D-08/09).
    Writes ``digests/<id>.md`` and appends a ``construct.views.models.DigestRecord``
    to the ``digests/digests.json`` record store (RESEARCH A1/D-09), replacing any
    record with the same id so a rerun stays idempotent. Surfaces the markdown
    path via ``digest_path``. NO LLM call lives here (D-08).
    """
    import json

    from construct.pipelines.ingestion import _get_first_domain
    from construct.views.models import DigestRecord, DigestsFile

    workspace = Path(state["workspace_path"])
    run_id = state.get("run_id") or state.get("gate_id") or "run"
    gate_queue = state.get("gate_queue", [])
    refs_created = state.get("refs_created", [])
    cards_created = state.get("cards_created", [])
    skipped_existing = state.get("skipped_existing", [])
    decisions = _resolve_decisions(state)

    considered = len(gate_queue)
    approved = sum(1 for d in decisions if d in _INGEST_ACTIONS)
    rejected = considered - approved
    ingested = len(refs_created) + len(cards_created) + len(skipped_existing)

    retrieval = state.get("retrieval", {}) or {}
    degraded = bool(retrieval.get("degraded"))
    degraded_notice = ""
    if degraded:
        degraded_notice = (
            "\n> **Degraded notice:** the scoring gate ran in a degraded state "
            f"(retried={retrieval.get('retried', 0)}, errors={retrieval.get('errors', 0)}); "
            "some candidates may have been skipped.\n"
        )

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    domain_id = _get_first_domain(workspace) or "general"
    digest_id = f"digest-{run_id}"
    title = f"Research cycle digest — {run_id}"

    summary_line = (
        f"considered={considered}, approved={approved}, rejected={rejected}, "
        f"ingested={ingested}"
    )

    lines = [
        f"# {title}",
        "",
        f"Generated: {now_iso}",
        "",
        "## Summary",
        "",
        f"- Considered: {considered}",
        f"- Approved: {approved}",
        f"- Rejected: {rejected}",
        f"- Refs created: {len(refs_created)}",
        f"- Cards created: {len(cards_created)}",
        f"- Skipped (already ingested): {len(skipped_existing)}",
    ]
    if degraded_notice:
        lines.append(degraded_notice)
    if refs_created:
        lines += ["", "## Created references", ""]
        lines += [f"- `{ref_id}`" for ref_id in refs_created]
    if cards_created:
        lines += ["", "## Created cards", ""]
        lines += [f"- `{card_id}`" for card_id in cards_created]
    lines += ["", "## Approved findings", ""]
    for entry, decision in zip(gate_queue, decisions):
        if decision in _INGEST_ACTIONS:
            finding = entry.get("finding", {})
            lines.append(f"- {finding.get('title', 'Untitled')} ({decision})")
    markdown = "\n".join(lines) + "\n"

    digests_dir = workspace / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    # CR-01 defense-in-depth: run_id is already kebab-validated at the input
    # boundary, but re-check the resolved path stays inside digests/ so a future
    # caller that bypasses the model validators still cannot escape the workspace.
    md_path = (digests_dir / f"{digest_id}.md").resolve()
    if not str(md_path).startswith(str(digests_dir.resolve()) + "/"):
        raise ValueError("digest path escapes the workspace digests directory")
    md_path.write_text(markdown, encoding="utf-8")

    store_path = digests_dir / "digests.json"
    store = _load_digest_store(store_path) if store_path.exists() else DigestsFile()
    # D-20: the parser's spelling, which is now also the model's. The prior
    # ``card_ids`` argument is gone with the field — the created card ids are
    # still listed in the digest markdown's "Created cards" section above, which
    # is the artifact a reader actually opens.
    record = DigestRecord(
        id=digest_id,
        domain=domain_id,
        theme=title,
        date=now_iso,
        summary_text=summary_line,
    )
    # Idempotent append: drop any prior record with the same id, then add.
    store.digests = [d for d in store.digests if d.id != digest_id]
    store.digests.append(record)
    store_path.write_text(
        json.dumps(store.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )

    logger.info("compile_digest wrote %s + DigestRecord", md_path)
    return {"digest_path": str(md_path)}


def update_seeds_and_log(state: ResearchRunState) -> dict:
    """Stamp ``last_queried`` on queried clusters + emit the D-11 audit events.

    Loads ``SearchSeedsFile``, sets ``last_queried = now`` on each cluster queried
    this run, and writes ``search-seeds.json`` back. Emits via the existing
    append-only ``append_event`` (non-blocking): ``research_search_complete``,
    ``research_score_gate_complete``, per-finding ``gate_review_approved`` /
    ``gate_review_rejected`` (reusing the gate_review event protocol's agent), and
    ``research_cycle_complete`` on full completion. Sets ``status='completed'`` —
    this is the terminal write node (D-11/D-12).
    """
    import json

    from construct.schemas.config import EventAgent
    from construct.services.event_log import append_event
    from construct.storage.workspace import WorkspaceLoader

    workspace = Path(state["workspace_path"])
    gate_id = state.get("gate_id") or state["run_id"]
    queried = set(state.get("queried_clusters", []))
    events = list(state.get("events", []))

    seed_update = "skipped"
    try:
        seeds = WorkspaceLoader(workspace).load_search_seeds()
        now = datetime.now(timezone.utc)
        changed = False
        for cluster in seeds.clusters:
            if cluster.id in queried:
                cluster.last_queried = now
                changed = True
        seeds.updated = now
        (workspace / "search-seeds.json").write_text(
            json.dumps(seeds.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
        )
        seed_update = "updated" if changed else "no-clusters-queried"
    except Exception as exc:  # noqa: BLE001 — seed update must not abort the cycle
        logger.warning("update_seeds_and_log seed update failed: %s", exc)
        seed_update = "failed"

    # D-11 cycle events (append-only, non-blocking).
    append_event(
        workspace,
        EventAgent.researcher,
        "research_search_complete",
        target=gate_id,
        detail=f"{len(state.get('search_results', []))} results",
    )
    events.append("research_search_complete")
    append_event(
        workspace,
        EventAgent.researcher,
        "research_score_gate_complete",
        target=gate_id,
        detail=f"{len(state.get('findings', []))} findings",
    )
    events.append("research_score_gate_complete")

    # Per-finding gate decisions (reuse the gate_review protocol agent — construct).
    decisions = _resolve_decisions(state)
    for entry, decision in zip(state.get("gate_queue", []), decisions):
        title = entry.get("finding", {}).get("title", "")
        if decision in _INGEST_ACTIONS:
            append_event(
                workspace, EventAgent.construct, "gate_review_approved",
                target=gate_id, detail=title,
            )
            events.append("gate_review_approved")
        else:
            append_event(
                workspace, EventAgent.construct, "gate_review_rejected",
                target=gate_id, detail=title,
            )
            events.append("gate_review_rejected")

    append_event(
        workspace, EventAgent.researcher, "research_cycle_complete", target=gate_id
    )
    events.append("research_cycle_complete")

    return {"status": "completed", "seed_update": seed_update, "events": events}


# ── Graph builder (locked linear topology + outage short-circuit) ──


def views_refresh(state: ResearchRunState) -> dict:
    """Rebuild the SPA's views cache after the terminal write node (D-12).

    A side effect, never a success condition: this node returns an EMPTY dict so it
    cannot set, degrade or clear ``status`` — ``update_seeds_and_log`` upstream owns the
    terminal status and this node structurally cannot touch it. A refresh that is
    skipped, disabled or broken leaves the run reporting exactly what it would have
    reported without the refresh.

    Note the outage short-circuit in ``_route_after_score``: a caught score outage routes
    straight to END, so an outage run legitimately never reaches this node. That is
    correct — there is nothing new to publish from a run that never scored anything.
    """
    # WR-01: ``refresh_views`` never raises, but the prologue around it — the deferred
    # import and the install-root derivation — is not covered by that guarantee. The
    # whole body is guarded so this node keeps its structural inability to affect the
    # run, not merely its inability to set ``status``.
    try:
        from construct.views.refresh import refresh_views

        # D-05: install-root scoped, so the workspace's PARENT. Passing the workspace
        # would discover zero workspaces and publish an empty build that looks like a
        # success.
        install_root = Path(state["workspace_path"]).parent

        outcome = refresh_views(install_root)
        if outcome.status == "failed":
            logger.warning("views_refresh: refresh failed: %s", outcome.reason)
        else:
            logger.info("views_refresh: %s (%s)", outcome.status, outcome.reason or "no detail")
    except Exception as exc:  # noqa: BLE001 — D-12: the refresh can never fail the run
        # Class name only — this module has no local sanitizer and T-10-08 forbids
        # logging raw exception text.
        logger.warning("views_refresh: refresh raised: %s", type(exc).__name__)
    return {}


def _route_after_score(state: ResearchRunState) -> str:
    """Route to END on a caught total outage (never pause); otherwise to the gate."""
    return END if state.get("status") == "failed" else "gate_review"


def build_research_run_graph(checkpointer: Any):
    """Compile the durable research.run StateGraph with the given checkpointer.

    Linear topology: load_config → build_queries → execute_search → deduplicate →
    score_and_extract → [outage? END] → gate_review[interrupt] → ingest_batch →
    compile_digest → update_seeds_and_log → views_refresh → END. The single pause is
    the interrupt in ``gate_review``; all write nodes are strictly downstream of it
    (RSCH-03 holds by construction). ``views_refresh`` is a pure side effect appended
    after the terminal write node and returns no state (D-12).
    """
    builder = StateGraph(ResearchRunState)

    builder.add_node("load_config", load_config)
    builder.add_node("build_queries", build_queries)
    builder.add_node("execute_search", execute_search)
    builder.add_node("deduplicate", deduplicate)
    builder.add_node("score_and_extract", score_and_extract)
    builder.add_node("gate_review", gate_review)
    builder.add_node("ingest_batch", ingest_batch)
    builder.add_node("compile_digest", compile_digest)
    builder.add_node("update_seeds_and_log", update_seeds_and_log)
    builder.add_node("views_refresh", views_refresh)

    builder.add_edge(START, "load_config")
    builder.add_edge("load_config", "build_queries")
    builder.add_edge("build_queries", "execute_search")
    builder.add_edge("execute_search", "deduplicate")
    builder.add_edge("deduplicate", "score_and_extract")
    # Outage short-circuit: a caught ResearchScoreOutageError never reaches the gate.
    builder.add_conditional_edges(
        "score_and_extract",
        _route_after_score,
        {END: END, "gate_review": "gate_review"},
    )
    builder.add_edge("gate_review", "ingest_batch")  # WRITE BOUNDARY (post-resume)
    builder.add_edge("ingest_batch", "compile_digest")
    builder.add_edge("compile_digest", "update_seeds_and_log")
    builder.add_edge("update_seeds_and_log", "views_refresh")
    builder.add_edge("views_refresh", END)

    return builder.compile(checkpointer=checkpointer)


# ── Persistent checkpointer (NO connection-string footgun — RESEARCH Pattern 2) ──


def _open_checkpointer(workspace: Path):
    """Open a persistent ``SqliteSaver`` under ``.construct/`` (caller closes conn).

    Returns ``(saver, conn)``. The connection is kept alive for the whole handler
    and closed in the caller's ``finally`` — never wrapped in a transient
    connection-string context manager (Pitfall 2: that closes the connection on
    block exit and breaks cross-process resume). ``check_same_thread=False`` is
    required because ``score_all`` fans out across worker threads that may touch
    the checkpointer (Pitfall 5).
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    db = Path(workspace) / ".construct" / "workflow" / "research-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    return SqliteSaver(conn), conn


# ── Run-start runner (pauses at the gate; full completion/review land in Plan 04) ──


def run_research_run(inp: ResearchRunInput) -> RunResult:
    """Start a durable research run; pause at the human-review gate.

    Opens the persistent checkpointer, builds the graph, and invokes it with
    ``thread_id = run_id``. When the graph pauses (``__interrupt__`` present) this
    returns a ``RunResult`` with status ``awaiting_review`` carrying the gate
    handle and the pending per-finding ``gate_queue``. A caught total outage
    returns status ``failed`` (the graph routed to END without pausing). The
    review/inspect runners and full-completion path land in Plan 04.
    """
    from construct.llm.research_score import ResearchScoreOutageError

    run_id = inp.run_id or _new_run_id()
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_research_run_graph(saver)
        cfg = {"configurable": {"thread_id": run_id}}
        resolved = ResearchRunInput(
            workspace_path=inp.workspace_path,
            run_id=run_id,
            provider_override=inp.provider_override,
        )
        try:
            result = graph.invoke(_initial_state(resolved), cfg)
        except ResearchScoreOutageError as exc:
            return RunResult(
                status="failed",
                run_id=run_id,
                gate_id=run_id,
                degraded=True,
                message=exc.safe_message,
            )

        snap = graph.get_state(cfg)
        if "__interrupt__" in result and snap.next == ("gate_review",):
            return RunResult(
                status="awaiting_review",
                run_id=run_id,
                gate_id=snap.values.get("gate_id", run_id),
                gate_queue=_ensure_proposal_ids(snap.values.get("gate_queue", []), run_id),
                degraded=bool(snap.values.get("retrieval", {}).get("degraded", False)),
                message="Paused for human review; resume with research.review.",
            )

        # Outage short-circuit (status failed, no pause) or already-complete state.
        status = result.get("status", "completed")
        return RunResult(
            status="failed" if status == "failed" else "completed",
            run_id=run_id,
            gate_id=run_id,
            degraded=bool(result.get("retrieval", {}).get("degraded", False)),
            message="Run did not pause for review." if status == "failed" else "Run complete.",
        )
    finally:
        conn.close()


# ── Review/inspect runners (resume + read-only inspect; cross-process via the DB) ──


def _completion_result(run_id: str, values: dict, completed: bool) -> RunResult:
    """Assemble the D-12 ``RunResult`` from the final/merged graph state (SC5)."""
    retrieval = values.get("retrieval", {}) or {}
    status = values.get("status") or ("completed" if completed else "awaiting_review")
    return RunResult(
        status=status,
        run_id=run_id,
        gate_id=values.get("gate_id", run_id),
        gate_queue=_ensure_proposal_ids(values.get("gate_queue", []), run_id),
        refs_created=values.get("refs_created", []),
        cards_created=values.get("cards_created", []),
        digest_path=values.get("digest_path"),
        seed_update=values.get("seed_update"),
        events=values.get("events", []),
        degraded=bool(retrieval.get("degraded", False)),
        message="Run complete." if completed else "Run still awaiting review.",
    )


def _build_resume_decisions(inp: ReviewInput, gate_queue: list[dict]) -> Any:
    """Translate a ``ReviewInput`` into the per-finding resume payload.

    Explicit ``decisions`` win; otherwise ``reject_all`` → every finding ``skip``,
    ``approve_all`` → each finding's recommended ``ingest_action`` (the default),
    and the bare default (no flag) → ``None`` so ``ingest_batch`` uses the per-entry
    recommended decisions (i.e. the LLM's proposed ingest set).
    """
    if inp.decisions is not None:
        return inp.decisions
    if inp.reject_all:
        return ["skip"] * len(gate_queue)
    if inp.approve_all:
        return [entry.get("decision", "skip") for entry in gate_queue]
    return None


def review_research_run(inp: ReviewInput) -> RunResult:
    """Resume a paused run with per-finding decisions and run it to completion.

    Re-opens the SAME persistent checkpointer on the workspace DB, recompiles the
    graph, and submits ``Command(resume=decisions)`` against ``thread_id=run_id``
    so the post-gate write nodes execute exactly once. Supports approve-all /
    reject-all shortcuts (expanded to per-finding decisions). Returns the completed
    ``RunResult`` (D-12). Closes the sqlite connection in ``finally``.
    """
    from langgraph.types import Command

    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_research_run_graph(saver)
        cfg = {"configurable": {"thread_id": inp.run_id}}
        snap = graph.get_state(cfg)
        # WR-05: only resume a run that is actually paused at the gate. Resuming a
        # completed run would re-execute the post-gate write nodes, re-emitting
        # D-11 audit events and re-stamping seed timestamps; a nonexistent run has
        # nothing to resume at all.
        if snap.next != ("gate_review",):
            values = snap.values or {}
            if values and not snap.next:
                return _completion_result(inp.run_id, values, True)
            return RunResult(
                status="failed",
                run_id=inp.run_id,
                gate_id=values.get("gate_id", inp.run_id) if values else inp.run_id,
                message="No paused run awaiting review for this run_id.",
            )
        gate_queue = snap.values.get("gate_queue", []) if snap.values else []
        decisions = _build_resume_decisions(inp, gate_queue)

        result = graph.invoke(Command(resume=decisions), cfg)
        final = graph.get_state(cfg)
        completed = not final.next
        values = final.values if final.values else result
        return _completion_result(inp.run_id, values, completed)
    finally:
        conn.close()


def inspect_research_run(inp: InspectInput) -> RunResult:
    """Report a run's pending state via ``get_state`` — NEVER resumes (read-only).

    Re-opens the checkpointer on the workspace DB and reads the persisted snapshot
    for ``thread_id=run_id``. Maps ``snapshot.next``: ``("gate_review",)`` →
    ``awaiting_review`` (carrying the pending ``gate_queue``), empty → ``completed``
    (or the terminal ``status``), anything else → ``running``. Performs no writes
    and does not advance the graph. Closes the sqlite connection in ``finally``.
    """
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_research_run_graph(saver)
        cfg = {"configurable": {"thread_id": inp.run_id}}
        snap = graph.get_state(cfg)
        values = snap.values or {}

        if snap.next == ("gate_review",):
            status = "awaiting_review"
            message = "Run is paused awaiting human review."
        elif not snap.next:
            # WR-03: a nonexistent run has no persisted values — report it as
            # failed (not "unknown") so the catalog shim maps it to success=False
            # rather than a misleading successful OperationResult.
            status = values.get("status", "completed") if values else "failed"
            message = "Run is complete." if values else "No such run."
        else:
            status = "running"
            message = f"Run is running (next: {snap.next})."

        retrieval = values.get("retrieval", {}) or {}
        return RunResult(
            status=status,
            run_id=inp.run_id,
            gate_id=values.get("gate_id", inp.run_id),
            gate_queue=_ensure_proposal_ids(values.get("gate_queue", []), inp.run_id),
            refs_created=values.get("refs_created", []),
            cards_created=values.get("cards_created", []),
            digest_path=values.get("digest_path"),
            seed_update=values.get("seed_update"),
            events=values.get("events", []),
            degraded=bool(retrieval.get("degraded", False)),
            message=message,
        )
    finally:
        conn.close()
