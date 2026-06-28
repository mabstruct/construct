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
    kept alive for the handler — never ``with SqliteSaver.from_conn_string(...)``
    (RESEARCH Pitfall 2: that closes the connection and breaks cross-process resume).
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
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Title fuzzy near-dup threshold (D-05 — basic this phase).
_TITLE_FUZZY_THRESHOLD = 0.90


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


class ReviewInput(BaseModel):
    """Input for ``research.review`` (resume with per-finding decisions, Plan 04)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str
    decisions: list[dict] | None = None
    approve_all: bool = False
    reject_all: bool = False


class InspectInput(BaseModel):
    """Input for ``research.inspect`` (read pending batch via ``get_state``, Plan 04)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str


class GateQueueEntry(BaseModel):
    """One per-finding review item: the scored finding + its default decision.

    The default ``decision`` is the LLM's ``ingest_action`` from ``research.score``
    (D-04): ``approve-all`` reproduces the recommended ingest set; ``reject-all``
    sets every decision to ``skip``.
    """

    model_config = {"extra": "forbid"}
    finding: dict
    decision: str  # skip | ref_only | ref_and_card


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
    """Generate a sortable run/gate handle: UTC timestamp + short random suffix."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
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
