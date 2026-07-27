"""Deterministic, interrupt-free ``curation.run`` LangGraph workflow (Phase 11).

This module is the real curation pipeline that replaces the v0.3 placeholder
no-ops (CUR-01). It is a faithful sibling of the shipped durable ``research.run``
(``construct.llm.research_run``) with the human-gate/``interrupt`` removed and the
post-gate write nodes replaced by read-only / findings-only steps:

  * Five REAL deterministic steps wrap existing functions and emit concrete
    findings (``integrity_check`` → ``validate_workspace``; ``decay_scan`` /
    ``orphan_scan`` → new findings-only candidate selection over ``load_cards`` /
    ``load_connections``; ``connection_maintenance`` → ``bridge_detect``;
    ``compile_report`` → ``graph_status``).
  * ``views_refresh_hook`` runs the real post-cycle views refresh (Phase 15 D-12)
    and reports what it ACTUALLY did — ``skipped`` when gated, ``completed`` with a
    failure reason when the refresh broke. It is ``required=False`` on every branch
    because the refresh is a side effect, never a success condition; it must never
    move the run's status. ``promotion_review`` and ``process_inbox`` became real
    proposal-producer / review-gate nodes in Phase 12 and are no longer deferred.
  * A purely LINEAR graph over spec §4.3 topology (no conditional edges, no
    interrupt pause) compiled over a durable persistent ``SqliteSaver``.
  * Run-level status aggregation (D-09): ``degraded`` if any REQUIRED step is
    ``failed``/``skipped``; ``completed`` otherwise. The three deferred skips are
    ``required=False`` so they never degrade a clean run (Pitfall 5).

Design constraints honored here (mirrors research_run discipline):
  * State channels hold ONLY plain serializable data — never a ``WorkspaceLoader``
    or sqlite connection (Pitfall 3). Every node rebuilds the loader locally.
  * I/O models live in THIS module, not ``catalog.py`` (circular-import hazard).
  * Nodes log to stderr via ``logging`` only — never ``print`` (stdout is the MCP
    JSON-RPC transport; Pitfall 6).
  * The checkpointer keeps a persistent ``sqlite3`` connection alive for the whole
    handler (Pitfall 2 — never the transient connection-string context-manager form).
  * curation.run performs NO canonical SOT writes (D-06): cards/refs/
    connections.json/search-seeds.json are never mutated; ``bridge_detect`` only
    writes DERIVED ``log/`` + ``views/`` artifacts (Pitfall 1).
"""
from __future__ import annotations

import logging
import operator
import secrets
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field, field_validator

from construct.schemas.card import Lifecycle
from construct.schemas.config import KEBAB_CASE_PATTERN

logger = logging.getLogger(__name__)

# The single consolidated review gate identifier (Phase 12, CUR-03). A FIXED
# module-level value for the ONE human-review pause — not a per-card state
# channel. ``process_inbox`` references this constant directly in its interrupt
# payload so the pause never reads an undefined ``state["gate_id"]`` (no
# KeyError). All promotion / connection / archive proposals share this one gate.
_CURATION_GATE_ID = "curation.review"


def _validate_run_id(value: str | None) -> str | None:
    """Reject any ``run_id`` that is not kebab-case (CR-01 / T-11-01 guard).

    ``run_id`` becomes the LangGraph ``thread_id`` and influences the checkpoint
    DB path. The MCP/CLI shims pass caller-supplied ``**kwargs`` straight into the
    input models, so an unvalidated value such as ``"../../../tmp/evil"`` would
    cross into the persistence/path layer. Constraining it to
    ``KEBAB_CASE_PATTERN`` ([a-z0-9] segments joined by single hyphens) makes path
    traversal impossible at the boundary; ``None`` is allowed (run-start
    auto-generates a safe id).
    """
    if value is not None and KEBAB_CASE_PATTERN.fullmatch(value) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9] segments joined by single hyphens)")
    return value


# ── Opaque proposal identity (GOV-02 / D-09) ──
#
# The id form was settled at a blocking checkpoint: the FULL 32-character
# ``uuid4().hex``, persisted under ``proposal_id``. Uniqueness spans runs as well
# as queues, so a decision payload cannot be replayed against a DIFFERENT run by
# accident — the property neither a run-scoped counter nor a truncated hex had.
# The id is deliberately NOT sortable: queue order lives in the queue list only
# and is never encoded in, or inferred from, the id.

#: A syntactically valid id, quoted in the validator's error message so a caller
#: who supplied a bad one can see the shape being asked for (AGENTS.md convention).
_PROPOSAL_ID_EXAMPLE = "3f2a9c1e5b7d4a8f9012345678abcdef"

#: Namespace for the ids assigned to PRE-Phase-18 queues by ``_ensure_proposal_ids``.
#: Fixed forever: changing it would rename every migrated proposal mid-review.
_MIGRATION_NAMESPACE = uuid.UUID("6f0c9b2e-1f7a-4c3d-9a5e-0b8d7c6e5f41")


def _new_proposal_id() -> str:
    """Mint one opaque proposal id: the full 32-character ``uuid4().hex``."""
    return uuid.uuid4().hex


def _validate_proposal_id(value: str) -> str:
    """Reject any ``proposal_id`` that is not opaque-shaped (T-18-08 guard).

    Built on the same identifier guard as ``_validate_run_id`` and for the same
    reason its docstring gives: the MCP/CLI surfaces pass caller-supplied
    ``**kwargs`` straight into the input models, and a resume payload names the
    proposals it applies to — so an unvalidated id would cross from an untrusted
    payload into the persistence layer. ``KEBAB_CASE_PATTERN`` ([a-z0-9] segments
    joined by single hyphens) admits a 32-character uuid4 hex as a single segment
    while excluding path separators, parent-directory segments and whitespace.
    """
    if KEBAB_CASE_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "proposal_id must be an opaque lowercase [a-z0-9] identifier (segments "
            f"joined by single hyphens) — for example {_PROPOSAL_ID_EXAMPLE}; a value "
            "containing a path separator, a parent-directory segment, uppercase, or "
            "whitespace is rejected at the trust boundary"
        )
    return value


def _migrated_proposal_id(run_id: str, index: int) -> str:
    """Mint the id a PRE-Phase-18 queued proposal is migrated to (D-12).

    Deterministic ON PURPOSE, because migration must perform NO write. Persisting
    migrated ids would advance the LangGraph checkpoint, and the checkpoint id is
    this phase's ETag (D-11) — an ``inspect`` that advanced it would make every
    subsequent resume read as stale, and the user could never resume at all.
    Deriving the id from ``uuid5(namespace, "{run_id}:{index}")`` instead yields
    the same 32-character opaque hex on every read, in every process, so the id a
    reader is shown is exactly the id a resume accepts.

    Queue position feeds the digest but does not survive it: uuid5 is a hash, so
    the index cannot be recovered from the id, and the ids are not ordered. The
    D-09 invariant holds — queue order lives in the queue list, never in the id.
    """
    return uuid.uuid5(_MIGRATION_NAMESPACE, f"{run_id}:{index}").hex


def _ensure_proposal_ids(gate_queue: list[dict], run_id: str) -> list[dict]:
    """Inject ids into a legacy id-less queue at the RAW-DICTIONARY stage (D-12).

    The gate queue is persisted as plain dictionaries in graph state, never as
    model instances, so this runs immediately after a state snapshot is read and
    strictly BEFORE any model validation. Doing it later fails — ``CurationProposal``
    forbids extra fields and would reject a dictionary that gained an id after
    validation — and doing it earlier is impossible.

    Only the gaps are filled: an entry that already carries an id keeps it, so a
    mixed queue (some legacy, some current) migrates without renaming anything.
    Nothing but the id is added; a migrated proposal carries the gate's own
    recommendation and NO reviewer decision, which is exactly what makes
    preserving the queue safe rather than a reintroduction of the positional
    assumption (D-10 and D-12 are one contract).
    """
    migrated: list[dict] = []
    for index, entry in enumerate(gate_queue):
        if entry.get("proposal_id"):
            migrated.append(entry)
            continue
        patched = dict(entry)
        patched["proposal_id"] = _migrated_proposal_id(run_id, index)
        migrated.append(patched)
    return migrated


# ── Typed review rejections (GOV-02 / GOV-03) ──
#
# Both are raised BEFORE ``Command(resume=…)`` is submitted, so a rejected resume
# performs zero canonical writes and leaves the run paused exactly where the user
# left it. Raising inside a graph node would not do: a node-raised error still
# advances the checkpoint.
#
# T-18-10: every message names proposal ids and checkpoint ids ONLY — never a
# workspace path, a card body, or any other content the caller did not already
# hold. ``research_run`` imports both so the two graphs return one rejection shape.


class ReviewRejected(Exception):
    """Base for a resume refused at the entry point, before any apply node ran."""

    #: A message safe to surface verbatim on the CLI/MCP boundary.
    safe_message: str = "Review rejected."


class IncompleteDecisionMap(ReviewRejected):
    """The decision map does not cover the queue exactly (D-10).

    ``missing`` are queued proposals the payload said nothing about; ``unknown``
    are keys naming proposals this queue does not contain. Either one rejects the
    WHOLE resume — a partially-covered queue is never partially applied.
    """

    def __init__(self, *, missing, unknown) -> None:
        self.missing = sorted(missing)
        self.unknown = sorted(unknown)
        parts: list[str] = []
        if self.missing:
            parts.append(f"no decision was supplied for {', '.join(self.missing)}")
        if self.unknown:
            parts.append(f"unknown proposal id(s) {', '.join(self.unknown)}")
        self.safe_message = (
            "Review rejected — " + "; ".join(parts) + ". Nothing was written; the run is "
            "still paused. Resubmit a decision for every queued proposal."
        )
        super().__init__(self.safe_message)


class StaleQueue(ReviewRejected):
    """The queue moved between being rendered and being submitted (D-11).

    Carries the checkpoint id the caller submitted and the run's current one. The
    comparison that raises this is exact string equality — no trimming, no case
    folding, no prefix matching.
    """

    def __init__(self, *, supplied: str, current: str | None) -> None:
        self.supplied = supplied
        self.current = current
        self.safe_message = (
            "Review rejected — the queue changed since it was rendered (submitted "
            f"checkpoint {supplied!r}, current checkpoint {current!r}). Nothing was "
            "written. Re-read the queue and resubmit against the current checkpoint."
        )
        super().__init__(self.safe_message)


# ── State schema (TypedDict — plain serializable data ONLY; Pitfall 3) ──


class CurationRunState(TypedDict):
    # Input (set before the graph starts)
    workspace_path: str
    run_id: str

    # Governance thresholds (loaded by load_config — D-05, no hardcoding)
    decay_window_days: int
    auto_archive_on_decay: bool
    orphan_tolerance_days: int

    # One CurationStepResult dump appended per node (reducer accumulates).
    steps: Annotated[list[dict], operator.add]

    # ── Review gate (Phase 12, CUR-03) ──
    # Heterogeneous consolidated review queue: CurationProposal dumps enqueued by
    # the three producers (promotion / connection / archive). ``operator.add`` so
    # each producer APPENDS into the single queue rather than overwriting it. The
    # producers never re-run on resume, so no double-accumulation occurs.
    gate_queue: Annotated[list[dict], operator.add]
    decisions: Any  # resume payload from the single human-review gate

    # Post-gate write outcomes — Plan 04's apply nodes fill these. ``promoted`` /
    # ``connections_added`` / ``archived`` each have a single writer node, but
    # ``rejected`` / ``escalated`` are contributed by more than one apply node, so
    # they use ``operator.add`` to accumulate across nodes instead of overwriting.
    promoted: list[str]
    connections_added: list[str]
    archived: list[str]
    rejected: Annotated[list[str], operator.add]
    escalated: Annotated[list[str], operator.add]

    # Output — ``events`` accumulates one audit-event name per emitting node
    # (``operator.add``) so per-step + gate-review events survive across the
    # interrupt/resume boundary without any node overwriting another's events.
    status: str  # running | awaiting_review | completed | degraded | failed
    events: Annotated[list[str], operator.add]


# ── In-module I/O models (defined HERE, not catalog.py — avoid circular import) ──


class CurationRunInput(BaseModel):
    """Input for the ``curation.run`` capability (run-start)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str | None = None

    _check_run_id = field_validator("run_id")(_validate_run_id)


class CurationInspectInput(BaseModel):
    """Input for ``curation.inspect`` (read persisted terminal state — never re-runs)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str

    _check_run_id = field_validator("run_id")(_validate_run_id)


class CurationReviewInput(BaseModel):
    """Input for ``curation.review`` (resume a paused run with per-item decisions).

    ``run_id`` becomes the LangGraph ``thread_id`` for resume, so it is guarded by
    the same kebab-case path-traversal validator as run/inspect. ``approve_all``
    reproduces every proposal's recommended decision (D-07); ``reject_all`` writes
    nothing. Plan 04 grows the write-side; Plan 03 resumes the graph to completion
    with no canonical write (the apply nodes do not exist yet).
    """

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str
    #: GOV-03 / D-11: the checkpoint id the queue was rendered at — an ETag, so
    #: every resume is a conditional request. REQUIRED: a resume that cannot say
    #: which queue it read cannot be checked for staleness, and an unverifiable
    #: resume is exactly the confused-deputy case this field exists to stop. Read
    #: it from ``curation.run``'s or ``curation.inspect``'s result.
    checkpoint_id: str
    #: GOV-02: an id-keyed map ``{proposal_id: decision}``, replacing the positional
    #: list whose alignment with the queue was the defect this phase removes.
    decisions: dict[str, str] | None = None
    approve_all: bool = False
    reject_all: bool = False

    _check_run_id = field_validator("run_id")(_validate_run_id)


class CurationProposal(BaseModel):
    """One consolidated-review item (the tagged-union review envelope, D-07).

    ``kind`` tags which write type the proposal would become AFTER human approval
    (promotion / connection / archive / escalate). ``decision`` defaults to the
    gate's recommendation (the per-item write the human is approving); a reviewer
    may override it. ``payload`` carries the plain-serializable fields the Plan 04
    apply node needs (card_id / target_lifecycle / from-to / connection_type …).
    ``extra="forbid"`` keeps a malicious card body from smuggling extra keys.

    ``proposal_id`` (GOV-02 / D-09) is the stable opaque name a human-review
    decision addresses. The ``default_factory`` fires when a producer CONSTRUCTS
    the proposal — i.e. at enqueue time, which is the only correct moment: minting
    lazily at read time would leave a proposal that is never read without a name.
    """

    model_config = {"extra": "forbid"}
    proposal_id: str = Field(default_factory=_new_proposal_id)
    kind: Literal["promotion", "connection", "archive", "escalate"]
    decision: str = ""  # default = the gate recommendation (D-07)
    payload: dict = Field(default_factory=dict)

    _check_proposal_id = field_validator("proposal_id")(_validate_proposal_id)


class CurationStepResult(BaseModel):
    """One curation step's outcome (D-07/D-08).

    ``status`` is the per-step verdict; ``required=False`` marks a deferred node so
    the run-level aggregation never degrades on it (Pitfall 5). ``findings`` carries
    concrete primitives (counts + candidate ids), never a raw dataclass (Pitfall 4).
    """

    model_config = {"extra": "forbid"}
    step: str
    status: Literal["completed", "skipped", "failed"]
    required: bool = True
    findings: dict = Field(default_factory=dict)
    summary: str = ""
    reason: str | None = None


class CurationRunResult(BaseModel):
    """Run-level result surface for a ``curation.run`` / ``curation.inspect`` call.

    ``status`` is the D-09 aggregate over the per-step results.
    """

    model_config = {"extra": "forbid"}
    status: Literal["completed", "degraded", "failed", "awaiting_review"]
    run_id: str
    gate_id: str | None = None
    #: GOV-03 / D-11: the run's checkpoint id at the moment this result was built.
    #: Returned alongside the queue so a caller can submit it back on resume.
    checkpoint_id: str | None = None
    gate_queue: list[dict] = Field(default_factory=list)
    steps: list[CurationStepResult] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    message: str = ""


# ── State helpers ──


def _new_run_id() -> str:
    """Generate a sortable, kebab-safe run handle: UTC timestamp + random suffix.

    The stamp uses ``-`` (not ISO ``T``) between date and time so the handle
    satisfies ``KEBAB_CASE_PATTERN`` — the same invariant ``_validate_run_id``
    enforces on caller-supplied ids (CR-01).
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"cur-{stamp}-{secrets.token_hex(3)}"


def _initial_state(inp: CurationRunInput) -> dict:
    """Build the initial graph state from validated input (all plain data).

    Single-arg form mirroring ``research_run._initial_state`` (and the Plan 01 red
    suite, which calls ``_initial_state(inp)``): the run_id is derived from
    ``inp.run_id`` or auto-generated here so the state's ``run_id`` matches the
    ``thread_id`` chosen by the runner.
    """
    run_id = inp.run_id or _new_run_id()
    return {
        "workspace_path": inp.workspace_path,
        "run_id": run_id,
        "decay_window_days": 0,
        "auto_archive_on_decay": False,
        "orphan_tolerance_days": 0,
        "steps": [],
        "gate_queue": [],
        "decisions": None,
        "promoted": [],
        "connections_added": [],
        "archived": [],
        "rejected": [],
        "escalated": [],
        "status": "running",
        "events": [],
    }


# ── Node 1: load governance thresholds (D-05 — no hardcoded windows) ──


def load_config(state: CurationRunState) -> dict:
    """Load decay/orphan thresholds from ``governance.yaml`` (read-only).

    Rebuilds ``WorkspaceLoader`` INSIDE the node (never store it in state —
    Pitfall 3). The three thresholds feed ``decay_scan``/``orphan_scan`` so those
    scans honor governance rather than hardcoding windows (D-05).
    """
    from construct.storage.workspace import WorkspaceLoader

    gov = WorkspaceLoader(Path(state["workspace_path"])).load_governance()
    return {
        "decay_window_days": gov.decay.decay_window_days,
        "auto_archive_on_decay": gov.decay.auto_archive_on_decay,
        "orphan_tolerance_days": gov.quality.orphan_tolerance_days,
    }


# ── Persistent checkpointer (NO connection-string footgun — Pitfall 2 / Pattern 3) ──


def _open_checkpointer(workspace: Path):
    """Open a persistent ``SqliteSaver`` under ``.construct/`` (caller closes conn).

    Returns ``(saver, conn)``. The connection is kept alive for the whole handler
    and closed in the caller's ``finally`` — never wrapped in a transient
    connection-string context manager (Pitfall 2: that closes the connection on
    block exit and breaks cross-process resume). ``check_same_thread=False`` is
    required because LangGraph may touch the checkpointer across threads.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    db = Path(workspace) / ".construct" / "workflow" / "curation-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    return SqliteSaver(conn), conn


# ── Node helpers (sanitization, date coercion, failed/deferred result builders) ──


def _sanitize_error(exc: Exception) -> str:
    """Reduce an exception to a class name + first safe line (never echo raw text).

    Mirrors the research-side discipline (T-11-02 / T-11-06): a node failure must
    surface as an honest ``failed`` step without leaking a multi-line message that
    might carry sensitive content.
    """
    text = str(exc).strip()
    first = text.splitlines()[0] if text else ""
    return f"{type(exc).__name__}: {first}" if first else type(exc).__name__


def _emit(workspace_path: str, action: str, target: str | None, detail: str | None = None) -> str:
    """Append one audit event (append-only, non-blocking) and return its name.

    Every deterministic step + apply/report node emits via this helper so the
    ``log/events.jsonl`` audit trail records the full curation cycle per spec §6.6
    (``workflow_step_complete`` per step, ``gate_review_approved`` /
    ``gate_review_rejected`` per reviewed proposal, ``curation_cycle_complete`` at
    the end). The returned name is appended into the ``events`` state channel. The
    interrupt-only ``process_inbox`` node NEVER calls this (avoids a double-fire on
    resume — Pitfall 1). ``append_event`` is non-blocking, so a log-write failure
    never aborts a node.
    """
    from construct.schemas.config import EventAgent
    from construct.services.event_log import append_event

    append_event(Path(workspace_path), EventAgent.curator, action, target=target, detail=detail)
    return action


def _coerce_date(value: Any) -> date | None:
    """Return a ``date`` for a date-or-isostring recency anchor; ``None`` if absent.

    ``load_cards`` returns Python-mode dumps so ``created``/``last_verified`` are
    already ``datetime.date`` — guard with ``isinstance`` so we never call
    ``date.fromisoformat`` on a value that is already a date (Pitfall 2).
    """
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _failed_step(step: str, exc: Exception) -> CurationStepResult:
    """Build a ``status="failed"`` step result from a caught node exception (D-08)."""
    safe = _sanitize_error(exc)
    logger.warning("curation step %s failed: %s", step, safe)
    return CurationStepResult(
        step=step, status="failed", findings={"error": safe},
        summary=f"{step} failed", reason=safe,
    )


# ── Real step nodes (wrap existing fns; extract PRIMITIVES into findings) ──


def integrity_check(state: CurationRunState) -> dict:
    """Wrap ``validate_workspace`` and store primitive counts (Pitfall 4).

    ``ValidationReport`` is a (non-JSON-serializable) dataclass — only its
    primitives (error/warning counts, ``ok``, error paths) cross into findings.
    """
    try:
        from construct.services.validation import validate_workspace

        report = validate_workspace(Path(state["workspace_path"]))
        result = CurationStepResult(
            step="integrity_check", status="completed",
            findings={
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "ok": report.ok,
                "error_paths": [f.path for f in report.errors],
            },
            summary=f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)",
        )
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("integrity_check", exc)
    event = _emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "integrity_check")
    return {"steps": [result.model_dump(mode="json")], "events": [event]}


def decay_scan(state: CurationRunState) -> dict:
    """Decay candidate scan + archive PRODUCER (D-04/D-05/D-06, Phase 12 CUR-03).

    Candidate = non-archived card whose recency anchor (``last_verified`` or
    ``created``) is older than the governance ``decay_window_days``. The findings
    surface is unchanged; when ``auto_archive_on_decay`` is set this node also
    enqueues one ``CurationProposal(kind="archive")`` per decay candidate into the
    consolidated ``gate_queue``. It PROPOSES only — no card is archived here (the
    archive write is a Plan 04 post-gate apply node behind the human review gate).
    """
    archive_dumps: list[dict] = []
    try:
        from construct.storage.workspace import WorkspaceLoader

        loader = WorkspaceLoader(Path(state["workspace_path"]))
        window = state["decay_window_days"]
        auto = state["auto_archive_on_decay"]
        today = date.today()
        candidate_ids: list[str] = []
        for card in loader.load_cards():
            lifecycle = card.get("lifecycle")
            if getattr(lifecycle, "value", lifecycle) == Lifecycle.archived.value:
                continue
            anchor = _coerce_date(card.get("last_verified")) or _coerce_date(card.get("created"))
            if anchor is None:
                continue
            if (today - anchor).days > window:
                candidate_ids.append(card.get("id"))
        summary = f"{len(candidate_ids)} decay candidate(s) over a {window}d window"
        if auto:
            summary += (
                "; auto_archive_on_decay is set — this scan reports decay candidates "
                "and archives nothing: each candidate is queued as an archive proposal "
                "and is archived only after explicit operator approval at the review gate"
            )
        result = CurationStepResult(
            step="decay_scan", status="completed",
            findings={
                "window_days": window,
                "candidate_count": len(candidate_ids),
                "candidate_ids": candidate_ids,
                "auto_archive_on_decay": auto,
            },
            summary=summary,
        )
        # Archive PRODUCER: candidate_ids already exclude archived cards, so each
        # is a valid archive proposal. Enqueue only under the governance flag.
        if auto and candidate_ids:
            archive_dumps = [
                CurationProposal(
                    kind="archive", decision="archive", payload={"card_id": cid}
                ).model_dump(mode="json")
                for cid in candidate_ids
            ]
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("decay_scan", exc)
    out: dict = {
        "steps": [result.model_dump(mode="json")],
        "events": [_emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "decay_scan")],
    }
    if archive_dumps:
        out["gate_queue"] = archive_dumps
    return out


def orphan_scan(state: CurationRunState) -> dict:
    """Findings-only orphan candidate scan (D-04/D-05).

    Candidate = non-archived card with connection degree 0 (counting each
    ``ConnectionRecord`` endpoint — both ``from_`` AND ``to`` — Pitfall 3) whose
    age exceeds the governance ``orphan_tolerance_days``.
    """
    try:
        from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader

        loader = WorkspaceLoader(Path(state["workspace_path"]))
        tolerance = state["orphan_tolerance_days"]
        today = date.today()

        degree: dict[str, int] = {}
        try:
            connections = loader.load_connections()
            for record in connections.connections:
                degree[record.from_] = degree.get(record.from_, 0) + 1
                degree[record.to] = degree.get(record.to, 0) + 1
        except WorkspaceLoadError:
            pass

        candidate_ids: list[str] = []
        for card in loader.load_cards():
            lifecycle = card.get("lifecycle")
            if getattr(lifecycle, "value", lifecycle) == Lifecycle.archived.value:
                continue
            cid = card.get("id")
            if degree.get(cid, 0) != 0:
                continue
            anchor = _coerce_date(card.get("last_verified")) or _coerce_date(card.get("created"))
            if anchor is None:
                continue
            if (today - anchor).days > tolerance:
                candidate_ids.append(cid)
        result = CurationStepResult(
            step="orphan_scan", status="completed",
            findings={
                "tolerance_days": tolerance,
                "candidate_count": len(candidate_ids),
                "candidate_ids": candidate_ids,
            },
            summary=f"{len(candidate_ids)} orphan candidate(s) over a {tolerance}d tolerance",
        )
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("orphan_scan", exc)
    event = _emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "orphan_scan")
    return {"steps": [result.model_dump(mode="json")], "events": [event]}


def _bridges_to_candidates(bridges: list[dict]) -> list[dict]:
    """Reshape ``bridge_detect`` bridge entries into connection-typing candidates.

    ``bridge_detect`` emits nested ``{"from": {card_id, domain, title}, "to": …}``
    entries; ``curation_connect.type_all`` expects the flat candidate-pair shape
    (``from_card_id`` / ``to_card_id`` / titles / ``l2_shared_categories``).
    """
    candidates: list[dict] = []
    for b in bridges:
        frm = b.get("from", {})
        to = b.get("to", {})
        candidates.append(
            {
                "from_card_id": frm.get("card_id"),
                "to_card_id": to.get("card_id"),
                "from_domain": frm.get("domain"),
                "to_domain": to.get("domain"),
                "from_title": frm.get("title"),
                "to_title": to.get("title"),
                "l2_shared_categories": b.get("l2_shared_categories") or [],
            }
        )
    return candidates


def connection_maintenance(state: CurationRunState) -> dict:
    """Connection-health via ``bridge_detect`` + connection-typing PRODUCER (CUR-03).

    Keeps the existing ``bridge_detect`` call (which writes DERIVED
    ``log/bridge-candidates.json`` + ``views/build/data/bridges.json`` — allowed
    under D-06, not canonical SOT) and additionally feeds its candidate pairs to
    the ``curation.connection_type`` L3 gate, enqueuing each typed result as a
    ``CurationProposal(kind="connection")``. It PROPOSES only — the connection
    write is a Plan 04 post-gate apply node. On a provider outage the typing step
    degrades to zero proposals while the bridge findings are still reported.
    """
    proposals: list[CurationProposal] = []
    typed = 0
    try:
        from construct.pipelines.bridge_detect import bridge_detect

        op = bridge_detect(state["workspace_path"])
        summary_block = (op.data or {}).get("summary", {})
        totals = summary_block.get("totals", {})
        l1_l2_only = summary_block.get("l1_l2_only")

        if op.success:
            candidates = _bridges_to_candidates((op.data or {}).get("bridges", []))
            if candidates:
                from construct.llm import curation_connect
                from construct.llm.config import load_llm_config

                config = load_llm_config(None)
                gate_cfg = config.gates.get("curation.connection_type") or config.gates.get(
                    "research.score"
                )
                provider_cfg = config.providers.get(
                    gate_cfg.provider, config.providers["anthropic"]
                )
                llm = curation_connect.build_typing_llm(provider_cfg, gate_cfg)
                batch = curation_connect.type_all(
                    candidates, llm=llm, cap=gate_cfg.concurrency_cap
                )
                if batch.total_outage:
                    logger.warning(
                        "connection_maintenance: provider outage — no connection "
                        "proposals enqueued"
                    )
                else:
                    for d in batch.decisions:
                        proposals.append(
                            CurationProposal(
                                kind="connection",
                                decision="approve",
                                payload={
                                    "from_card_id": d.from_card_id,
                                    "to_card_id": d.to_card_id,
                                    "connection_type": d.connection_type.value,
                                    "reasoning": d.reasoning,
                                },
                            )
                        )
                        typed += 1

        result = CurationStepResult(
            step="connection_maintenance",
            status="completed" if op.success else "failed",
            findings={
                "totals": totals,
                "l1_l2_only": l1_l2_only,
                "ok": op.success,
                "connection_proposals": typed,
            },
            summary=(
                "connection-health via bridge_detect; typed-connection proposals "
                "queued for review (derived log/+views/ only, no canonical SOT write)"
            ),
            reason=None if op.success else op.message,
        )
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("connection_maintenance", exc)
        event = _emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "connection_maintenance")
        return {"steps": [result.model_dump(mode="json")], "events": [event]}
    out: dict = {
        "steps": [result.model_dump(mode="json")],
        "events": [_emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "connection_maintenance")],
    }
    if proposals:
        out["gate_queue"] = [p.model_dump(mode="json") for p in proposals]
    return out


def compile_report(state: CurationRunState) -> dict:
    """Roll up the graph status report + set the terminal status/cycle event.

    Reads graph counts via ``graph_status`` (read-only), then computes the D-09
    aggregate over every step seen so far (including this one) and stamps it onto
    the ``status`` channel — this is the node both terminal paths (empty-queue
    short-circuit AND post-gate apply chain) always run exactly once, so it is the
    single place the ``curation_cycle_complete`` audit event fires (never
    double-emitted across the interrupt). ``views_refresh_hook`` runs after this
    but is ``required=False`` so it never changes the aggregate.
    """
    workspace = state["workspace_path"]
    run_id = state["run_id"]
    try:
        from construct.pipelines.graph_status import graph_status

        op = graph_status(workspace)
        data = op.data or {}
        result = CurationStepResult(
            step="compile_report",
            status="completed" if op.success else "failed",
            findings={
                "cards": data.get("cards", {}),
                "connections": data.get("connections", {}),
                "domains": data.get("domains", {}),
            },
            summary="graph status report compiled",
            reason=None if op.success else op.message,
        )
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("compile_report", exc)
    all_steps = [CurationStepResult(**s) for s in state.get("steps", [])] + [result]
    status = _aggregate_status(all_steps)
    events = [
        _emit(workspace, "workflow_step_complete", run_id, "compile_report"),
        _emit(workspace, "curation_cycle_complete", run_id, status),
    ]
    return {"steps": [result.model_dump(mode="json")], "status": status, "events": events}


# ── Promotion PRODUCER (no pause, no write — enqueues into gate_queue only) ──


def promotion_review(state: CurationRunState) -> dict:
    """Promotion PRODUCER: judge non-mature/non-archived cards → enqueue proposals.

    Pre-filters to promotion candidates (``lifecycle != mature`` AND
    ``!= archived``, D-02) BEFORE the LLM fan-out, runs the ``card.evaluate`` L3
    gate, and enqueues one ``CurationProposal`` per ``promote``/``escalate``
    verdict. A plain ``hold`` is events-only (logged, not enqueued — D-07). It
    PROPOSES only: no pause and no canonical write happen here. A provider outage
    degrades to zero proposals (the single pause lives in ``process_inbox``).
    """
    proposals: list[CurationProposal] = []
    enqueued = 0
    try:
        from construct.llm import curation_promote
        from construct.llm.config import load_llm_config
        from construct.storage.workspace import WorkspaceLoader

        cards = WorkspaceLoader(Path(state["workspace_path"])).load_cards()
        candidates = [c for c in cards if curation_promote.is_promotion_candidate(c)]

        if candidates:
            config = load_llm_config(None)
            gate_cfg = config.gates.get("card.evaluate") or config.gates.get(
                "research.score"
            )
            provider_cfg = config.providers.get(
                gate_cfg.provider, config.providers["anthropic"]
            )
            llm = curation_promote.build_scoring_llm(provider_cfg, gate_cfg)
            batch = curation_promote.evaluate_all(
                candidates, llm=llm, cap=gate_cfg.concurrency_cap
            )
            if batch.total_outage:
                logger.warning(
                    "promotion_review: provider outage — no promotion proposals enqueued"
                )
            else:
                for d in batch.decisions:
                    if d.decision == "hold":
                        logger.info(
                            "promotion_review: hold %s (events-only, not enqueued)",
                            d.card_id,
                        )
                        continue
                    kind = "promotion" if d.decision == "promote" else "escalate"
                    proposals.append(
                        CurationProposal(
                            kind=kind,
                            decision=d.decision,
                            payload={
                                "card_id": d.card_id,
                                "target_lifecycle": d.target_lifecycle,
                                "reasoning": d.reasoning,
                                "method": d.method,
                            },
                        )
                    )
                    enqueued += 1

        result = CurationStepResult(
            step="promotion_review",
            status="completed",
            findings={"candidates": len(candidates), "proposals": enqueued},
            summary=f"{enqueued} promotion/escalate proposal(s) from {len(candidates)} candidate(s)",
        )
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("promotion_review", exc)
        event = _emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "promotion_review")
        return {"steps": [result.model_dump(mode="json")], "events": [event]}
    out: dict = {
        "steps": [result.model_dump(mode="json")],
        "events": [_emit(state["workspace_path"], "workflow_step_complete", state["run_id"], "promotion_review")],
    }
    if proposals:
        out["gate_queue"] = [p.model_dump(mode="json") for p in proposals]
    return out


# ── Consolidated human-review gate (interrupt-ONLY — the CUR-03 spine) ──


def process_inbox(state: CurationRunState) -> dict:
    """Single consolidated review pause — interrupt-ONLY (CUR-03 spine).

    *** ONLY the interrupt primitive lives here. NO writes, NO event emission, NO
    non-idempotent prep. *** The interrupted node re-executes top-to-bottom on
    resume, so any side effect here would double-fire AND leak a write before
    approval. All promotion / connection / archive writes live strictly
    downstream in Plan 04's post-gate apply nodes, which run only after
    ``Command(resume=…)``. The gate id is the fixed module constant
    ``_CURATION_GATE_ID`` (never a per-card ``state["gate_id"]`` read → no
    KeyError); every proposal kind shares this one gate and one resume.
    """
    decisions = interrupt(
        {"gate_id": _CURATION_GATE_ID, "gate_queue": state["gate_queue"]}
    )
    return {"decisions": _unwrap_resume(decisions)}


# ── Post-gate write nodes (WRITE BOUNDARY — run ONLY after Command(resume); CUR-03) ──


def _normalize_decision(value: Any, default: str) -> str:
    """Map an EXPLICIT resume decision token to a concrete per-proposal verdict.

    Every value reaching this function was supplied by a human for a named
    proposal — the coverage check upstream guarantees it. The convenience synonym
    ``approve`` expands to the proposal's recommended ``default`` (an explicit
    "yes, do what you proposed", not a silent default), ``reject`` collapses to a
    hard ``"reject"`` (no write), and any other token passes through verbatim so a
    structured per-item payload keeps full control.

    The ``None`` → ``default`` branch this function used to carry is DELETED: it
    was the mechanism by which a short or absent payload performed a canonical
    write the user never approved (T-18-03). A missing decision is now a rejection
    of the whole resume, never a substitution.
    """
    if value == "approve":
        return default
    if value == "reject":
        return "reject"
    return str(value)


def _decision_map(raw: Any) -> dict[str, str]:
    """Coerce the resume payload to an id-keyed map; anything else is EMPTY.

    A legacy positional ``list`` payload therefore reads as "no decisions", which
    the coverage check turns into a rejection naming every queued id. That is the
    intended outcome: a positional payload can no longer be applied to a queue by
    accident, which is what makes D-12's migrate-on-read safe (D-10 and D-12 are
    one contract).
    """
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _checkpoint_id(snap: Any) -> str | None:
    """Read the LangGraph checkpoint id from a state snapshot — the D-11 ETag.

    ``StateSnapshot.config["configurable"]["checkpoint_id"]`` is already maintained
    by LangGraph and has all four properties staleness detection needs, verified
    empirically against the pinned langgraph / langgraph-checkpoint-sqlite: present
    while paused, stable across repeated reads, stable across a separate connection
    or process, and changed by both a state update and a resume.

    Deliberately NOT hand-rolled. A hash of the serialized queue would miss a state
    advance that leaves the queue textually identical, and a modification time on
    the database file is weaker still.
    """
    config = getattr(snap, "config", None) or {}
    return (config.get("configurable") or {}).get("checkpoint_id")


def _wrap_resume(decisions: dict[str, str]) -> list[dict[str, str]]:
    """Wrap the id-keyed decision map for transport through ``Command(resume=…)``.

    *** Do not send the map bare. *** ``Command.resume`` accepts EITHER a single
    resume value OR a mapping of LangGraph **interrupt ids** to resume values, and
    it distinguishes the two by inspecting the value: a ``dict`` is read as the
    interrupt-id mapping. A ``proposal_id`` is a 32-character ``uuid4().hex`` —
    exactly the shape of a LangGraph interrupt id — so a bare decision map matches
    no pending interrupt, is silently consumed as an empty resume, and leaves the
    run PAUSED with zero writes and no error. [VERIFIED empirically against the
    pinned langgraph: a 32-hex-keyed dict resume returns the run still interrupted.]

    Wrapping in a one-element list makes the payload a plain "single value" again,
    which LangGraph hands to ``interrupt()`` untouched. The envelope is purely a
    transport detail: ``_unwrap_resume`` removes it at the gate node, so the state
    channel — and the capability contract Phase 19's API and Phase 22's wizards are
    built against — stays the id-keyed map.
    """
    return [dict(decisions)]


def _unwrap_resume(value: Any) -> Any:
    """Undo ``_wrap_resume`` at the gate node; pass anything else through.

    A payload that is not the one-element envelope (a legacy positional list, say)
    is returned verbatim so it reaches ``_decision_map`` unchanged and is rejected
    there rather than being coerced into something appliable.
    """
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return value


def _check_coverage(queued_ids: list[str], supplied: dict[str, str]) -> None:
    """Raise unless the supplied key set EXACTLY equals the queued id set (D-10).

    Both differences are reported together so one round trip tells the caller
    everything that is wrong with the payload. An empty queue with an empty map
    has no difference in either direction and is therefore accepted — a resume
    with nothing to review succeeds with zero writes rather than erroring.
    """
    queued = set(queued_ids)
    keys = set(supplied)
    missing = queued - keys
    unknown = keys - queued
    if missing or unknown:
        raise IncompleteDecisionMap(missing=missing, unknown=unknown)


def _queue_and_decisions(state: CurationRunState) -> list[tuple[dict, str]]:
    """Pair each queued proposal with its resolved verdict, IN QUEUE ORDER.

    The single place the apply nodes read the review outcome from. Returning
    pairs (rather than two positionally-aligned lists to be zipped back together)
    removes the last place a positional assumption could re-enter: there is no
    longer any index arithmetic between a proposal and its decision.

    Queue order — not decision-map key order — drives the result, so the same
    decisions submitted in two different key orders produce identical writes and
    an identical event sequence.
    """
    gate_queue = _ensure_proposal_ids(state.get("gate_queue", []), state.get("run_id", ""))
    supplied = _decision_map(state.get("decisions"))
    queued_ids = [entry["proposal_id"] for entry in gate_queue]
    _check_coverage(queued_ids, supplied)
    return [
        (entry, _normalize_decision(supplied[entry["proposal_id"]], entry.get("decision", "")))
        for entry in gate_queue
    ]


def _resolve_decisions(state: CurationRunState) -> list[str]:
    """Resolve the effective per-proposal verdict list, aligned with ``gate_queue``.

    Id-keyed: the resume payload names the proposal each decision applies to, and
    a payload that does not cover the queue exactly raises rather than defaulting.
    Only ``approved`` verdicts authorize a write — the apply nodes below enforce
    the only-approved invariant per proposal kind.
    """
    return [decision for _entry, decision in _queue_and_decisions(state)]


def _card_lifecycle_map(workspace: str) -> dict[str, str]:
    """Load ``{card_id: lifecycle_value}`` for idempotent skip-if-at-target writes.

    Rebuilt INSIDE the apply node (never stored in state — Pitfall 3). Used so a
    rerun/crash-resume that re-approves the same proposal skips a card already at
    its target lifecycle / already archived rather than re-writing it.
    """
    from construct.storage.workspace import WorkspaceLoader

    out: dict[str, str] = {}
    try:
        for card in WorkspaceLoader(Path(workspace)).load_cards():
            lifecycle = card.get("lifecycle")
            out[card.get("id")] = getattr(lifecycle, "value", lifecycle)
    except Exception as exc:  # noqa: BLE001 — read robustness (T-11-02)
        logger.warning("apply node: could not load card lifecycles: %s", _sanitize_error(exc))
    return out


def apply_promotions(state: CurationRunState) -> dict:
    """Write APPROVED promotions via ``edit_card`` (idempotent; only-approved).

    For each proposal of ``kind="promotion"`` whose resolved verdict is
    ``"promote"``, advance the card lifecycle to ``target_lifecycle``
    (``growing``/``mature`` only — Discrepancy 1) via
    ``edit_card(..., author=CardAuthor.curator)``, skipping any card already at
    that lifecycle (idempotent — a rerun never re-writes). ``escalate`` proposals
    (and promotion verdicts resolving to ``escalate``) are REVIEW-ONLY: recorded as
    escalated with NO SOT write this phase (Open-Q 3). Rejected proposals write
    nothing. Each per-item write is isolated in try/except so one failure never
    aborts the batch (D-08); one ``workflow_step_complete`` event marks the node.
    """
    from construct.schemas.card import CardAuthor
    from construct.services.knowledge import edit_card

    workspace = state["workspace_path"]
    reviewed = _queue_and_decisions(state)
    lifecycles = _card_lifecycle_map(workspace)

    promoted: list[str] = []
    rejected: list[str] = []
    escalated: list[str] = []
    events: list[str] = []

    for entry, decision in reviewed:
        kind = entry.get("kind")
        if kind not in ("promotion", "escalate"):
            continue
        card_id = entry.get("payload", {}).get("card_id")
        # escalate is review-only this phase — record outcome, NO write (Open-Q 3).
        if kind == "escalate" or decision == "escalate":
            escalated.append(card_id)
            events.append(_emit(workspace, "gate_review_rejected", card_id, "escalated (review-only)"))
            continue
        if decision != "promote":
            rejected.append(card_id)
            events.append(_emit(workspace, "gate_review_rejected", card_id, "promotion rejected"))
            continue
        target = entry.get("payload", {}).get("target_lifecycle")
        if not target:
            escalated.append(card_id)
            events.append(_emit(workspace, "gate_review_rejected", card_id, "no target lifecycle"))
            continue
        try:
            if lifecycles.get(card_id) == target:
                promoted.append(card_id)  # already at target → idempotent no-op
            else:
                res = edit_card(workspace, card_id, {"lifecycle": target}, author=CardAuthor.curator)
                if res.success:
                    promoted.append(card_id)
                else:
                    logger.warning("apply_promotions: %s failed: %s", card_id, res.message)
            events.append(_emit(workspace, "gate_review_approved", card_id, f"promote → {target}"))
        except Exception as exc:  # noqa: BLE001 — per-item isolation (D-08)
            logger.warning("apply_promotions %s failed: %s", card_id, _sanitize_error(exc))
    events.append(_emit(workspace, "workflow_step_complete", state["run_id"], "apply_promotions"))
    return {"promoted": promoted, "rejected": rejected, "escalated": escalated, "events": events}


def apply_connections(state: CurationRunState) -> dict:
    """Write APPROVED connections via ``add_connection`` (idempotent dedup).

    For each proposal of ``kind="connection"`` whose resolved verdict is not a
    reject, persist a NEW typed edge via
    ``add_connection(..., created_by=ConnectionAuthor.construct)``.
    ``add_connection`` already dedups (a duplicate ``(from, to, type)`` returns
    ``success=True, "Connection already exists"`` — knowledge.py:416-423), so a
    rerun or crash-resume is a no-op that never duplicates an edge. Per-item
    isolation keeps one bad pair from aborting the batch (D-08).
    """
    from construct.schemas.workspace import ConnectionAuthor, ConnectionType
    from construct.services.knowledge import add_connection

    workspace = state["workspace_path"]
    reviewed = _queue_and_decisions(state)

    added: list[str] = []
    rejected: list[str] = []
    events: list[str] = []

    for entry, decision in reviewed:
        if entry.get("kind") != "connection":
            continue
        payload = entry.get("payload", {})
        from_id = payload.get("from_card_id")
        to_id = payload.get("to_card_id")
        key = f"{from_id}->{to_id}"
        if decision == "reject":
            rejected.append(key)
            events.append(_emit(workspace, "gate_review_rejected", key, "connection rejected"))
            continue
        try:
            conn_type = ConnectionType(payload.get("connection_type"))
            res = add_connection(
                workspace, from_id, to_id, conn_type,
                note=payload.get("reasoning"),
                created_by=ConnectionAuthor.construct,
            )
            if res.success:
                added.append(f"{key}:{conn_type.value}")
            else:
                logger.warning("apply_connections: %s failed: %s", key, res.message)
            events.append(_emit(workspace, "gate_review_approved", key, f"connection {conn_type.value}"))
        except Exception as exc:  # noqa: BLE001 — per-item isolation (D-08)
            logger.warning("apply_connections %s failed: %s", key, _sanitize_error(exc))
    events.append(_emit(workspace, "workflow_step_complete", state["run_id"], "apply_connections"))
    return {"connections_added": added, "rejected": rejected, "events": events}


def apply_archives(state: CurationRunState) -> dict:
    """Write APPROVED archives via ``archive_card`` (skip-if-already-archived).

    For each proposal of ``kind="archive"`` whose resolved verdict is ``"archive"``,
    set the card lifecycle to ``archived`` via
    ``archive_card(..., author=CardAuthor.curator)``, skipping any card already
    archived (idempotent). Rejected proposals write nothing. Per-item isolation
    keeps one failing archive from aborting the batch (D-08).
    """
    from construct.schemas.card import CardAuthor, Lifecycle
    from construct.services.knowledge import archive_card

    workspace = state["workspace_path"]
    reviewed = _queue_and_decisions(state)
    lifecycles = _card_lifecycle_map(workspace)

    archived: list[str] = []
    rejected: list[str] = []
    events: list[str] = []

    for entry, decision in reviewed:
        if entry.get("kind") != "archive":
            continue
        card_id = entry.get("payload", {}).get("card_id")
        if decision != "archive":
            rejected.append(card_id)
            events.append(_emit(workspace, "gate_review_rejected", card_id, "archive rejected"))
            continue
        try:
            if lifecycles.get(card_id) == Lifecycle.archived.value:
                archived.append(card_id)  # already archived → idempotent no-op
            else:
                res = archive_card(workspace, card_id, author=CardAuthor.curator)
                if res.success:
                    archived.append(card_id)
                else:
                    logger.warning("apply_archives: %s failed: %s", card_id, res.message)
            events.append(_emit(workspace, "gate_review_approved", card_id, "archived"))
        except Exception as exc:  # noqa: BLE001 — per-item isolation (D-08)
            logger.warning("apply_archives %s failed: %s", card_id, _sanitize_error(exc))
    events.append(_emit(workspace, "workflow_step_complete", state["run_id"], "apply_archives"))
    return {"archived": archived, "rejected": rejected, "events": events}


def views_refresh_hook(state: CurationRunState) -> dict:
    """Rebuild the SPA's views cache as a side effect of the cycle completing (D-12).

    The step result reflects what the refresh ACTUALLY did — a gated refresh reports
    ``skipped``, a broken one reports ``completed`` carrying the failure in its reason.
    Nothing here is hardcoded: this node previously returned a fixed ``skipped`` with a
    stale "deferred to Phase 12" reason, an audit trail that lied about the run
    (T-15-14), and ``workflow.run`` was removed in Phase 12 for the same fake-success
    class of defect (see the D-10/CUR-05 comment in ``catalog.py``).

    ``required=False`` on every branch: per D-12 the refresh is a side effect, never a
    success condition, so ``_aggregate_daily_status``'s required-step roll-up must never
    see it. A failed refresh is therefore reported as ``completed`` with the failure in
    ``reason`` rather than ``failed`` — the node ran to completion; the cache did not
    rebuild. Reporting ``failed`` would be honest about the refresh but would leave a
    ``failed`` step in the run record that a future aggregation change could pick up.
    """
    workspace = state["workspace_path"]

    # WR-01: the node's contract is "cannot fail the run", but ``refresh_views``'
    # own never-raise guarantee covers only itself — the deferred import, the
    # install-root derivation and the closing ``_emit`` all sit outside it. The whole
    # body is therefore guarded, so this node degrades to a reported skip rather than
    # propagating into the graph.
    try:
        from construct.views.refresh import refresh_views

        # D-05: the generator is INSTALL-ROOT scoped and discovers workspaces as its
        # children. Passing the workspace itself would discover zero workspaces and
        # write an empty build — a refresh that looks like it worked and produced
        # nothing.
        install_root = Path(workspace).parent
        outcome = refresh_views(install_root)
    except Exception as exc:  # noqa: BLE001 — D-12: this node can never fail the run
        safe = _sanitize_error(exc)
        logger.warning("views_refresh_hook: refresh raised: %s", safe)
        result = CurationStepResult(
            step="views_refresh_hook", status="skipped", required=False,
            reason=safe,
            summary=(
                f"views refresh could not run: {safe}. Workspace is intact; "
                f"run 'construct views generate' manually to refresh the views."
            ),
        )
        return {"steps": [result.model_dump(mode="json")], "events": []}

    if outcome.status == "skipped":
        result = CurationStepResult(
            step="views_refresh_hook", status="skipped", required=False,
            reason=outcome.reason,
            summary=f"views refresh skipped: {outcome.reason}",
        )
    elif outcome.status == "succeeded":
        # WR-02: `views.confirm_refresh: true` populates `outcome.reason` with
        # "✓ views updated". This is the one caller with a user-visible surface, so
        # it is the one that must carry the string through — otherwise the flag is
        # inert and ADR-0005's "appends ✓ views updated" contract is not honoured
        # anywhere. When the flag is false the reason is empty and the summary is
        # unchanged, which is the silence the flag selects.
        summary = f"views refreshed ({outcome.files_written} files written)"
        if outcome.reason:
            summary = f"{summary} — {outcome.reason}"
        result = CurationStepResult(
            step="views_refresh_hook", status="completed", required=False,
            reason=outcome.reason,
            findings={"build_id": outcome.build_id, "files_written": outcome.files_written},
            summary=summary,
        )
    else:
        logger.warning("views_refresh_hook: refresh failed: %s", outcome.reason)
        result = CurationStepResult(
            step="views_refresh_hook", status="completed", required=False,
            reason=outcome.reason,
            summary=(
                f"views regeneration failed: {outcome.reason}. Workspace is intact; "
                f"run 'construct views generate' manually to refresh the views."
            ),
        )

    # WR-01: the audit emit is a side effect of a node that cannot fail the run, so a
    # failing event write degrades to "no event" rather than propagating.
    try:
        events = [_emit(workspace, "workflow_step_complete", state["run_id"], "views_refresh_hook")]
    except Exception as exc:  # noqa: BLE001 — D-12: this node can never fail the run
        logger.warning("views_refresh_hook: event emit failed: %s", _sanitize_error(exc))
        events = []
    return {"steps": [result.model_dump(mode="json")], "events": events}


# ── Graph builder (deterministic prefix + one conditional short-circuit) ──


def _route_before_inbox(state: CurationRunState) -> str:
    """Route to the review gate only when the consolidated queue is non-empty.

    An empty ``gate_queue`` (no promotion / connection / archive proposals) skips
    ``process_inbox`` entirely and runs straight to ``compile_report`` — a run
    with nothing to review never pauses (Pitfall 2). A non-empty queue routes to
    the single interrupt-only gate.
    """
    return "process_inbox" if state.get("gate_queue") else "compile_report"


def build_curation_run_graph(checkpointer: Any):
    """Compile the durable curation StateGraph with the given checkpointer.

    Topology (spec §4.3 + Phase-12 HITL graft): START → load_config →
    integrity_check → decay_scan → orphan_scan → promotion_review(PRODUCER) →
    connection_maintenance(PRODUCER) → [gate_queue? process_inbox[interrupt] :
    compile_report] → apply_promotions → apply_connections → apply_archives →
    compile_report → views_refresh_hook(SKIP) → END. The three producers enqueue
    all proposals into ONE ``gate_queue`` BEFORE the single interrupt-only pause;
    the three apply nodes (the canonical SOT writers) sit strictly DOWNSTREAM of
    the interrupt, so no write node exists upstream of it — CUR-03 holds by
    construction. The empty-queue short-circuit skips both the pause and the apply
    nodes straight to compile_report (nothing to review, nothing to write).
    """
    builder = StateGraph(CurationRunState)

    builder.add_node("load_config", load_config)
    builder.add_node("integrity_check", integrity_check)
    builder.add_node("decay_scan", decay_scan)
    builder.add_node("orphan_scan", orphan_scan)
    builder.add_node("promotion_review", promotion_review)
    builder.add_node("connection_maintenance", connection_maintenance)
    builder.add_node("process_inbox", process_inbox)
    builder.add_node("apply_promotions", apply_promotions)
    builder.add_node("apply_connections", apply_connections)
    builder.add_node("apply_archives", apply_archives)
    builder.add_node("compile_report", compile_report)
    builder.add_node("views_refresh_hook", views_refresh_hook)

    builder.add_edge(START, "load_config")
    builder.add_edge("load_config", "integrity_check")
    builder.add_edge("integrity_check", "decay_scan")
    builder.add_edge("decay_scan", "orphan_scan")
    builder.add_edge("orphan_scan", "promotion_review")
    builder.add_edge("promotion_review", "connection_maintenance")
    # Empty-queue short-circuit: never pause when there is nothing to review.
    builder.add_conditional_edges(
        "connection_maintenance",
        _route_before_inbox,
        {"process_inbox": "process_inbox", "compile_report": "compile_report"},
    )
    # WRITE BOUNDARY (Plan 04): the three post-gate apply nodes run ONLY after
    # Command(resume=…) clears the interrupt. Every canonical SOT write lives here,
    # strictly downstream of process_inbox — CUR-03 holds by construction.
    builder.add_edge("process_inbox", "apply_promotions")
    builder.add_edge("apply_promotions", "apply_connections")
    builder.add_edge("apply_connections", "apply_archives")
    builder.add_edge("apply_archives", "compile_report")
    builder.add_edge("compile_report", "views_refresh_hook")
    builder.add_edge("views_refresh_hook", END)

    return builder.compile(checkpointer=checkpointer)


# ── Run/inspect runners + D-09 status aggregation + terminal event ──


def _aggregate_status(steps: list[CurationStepResult]) -> str:
    """D-09 run-level roll-up over COMPLETED runs (Pitfall 5).

    ``degraded`` if any REQUIRED step is ``failed`` or ``skipped``; ``completed``
    otherwise. Called only on runs that ran to END — a paused/reviewed run is
    surfaced as ``awaiting_review`` by the pause detection in ``run_curation_run``
    and never reaches this aggregate, so a pending review gate is NOT degraded.
    The producers (promotion_review / connection_maintenance) emit ``completed``
    required steps; ``views_refresh_hook`` stays ``required=False`` so the one
    remaining deferred node never degrades a clean run.
    """
    required_bad = [s for s in steps if s.required and s.status in ("failed", "skipped")]
    return "degraded" if required_bad else "completed"


def run_curation_run(inp: CurationRunInput) -> CurationRunResult:
    """Run the curation cycle, detecting the single consolidated review pause.

    Opens the persistent checkpointer, builds the graph, and invokes it once with
    ``thread_id = run_id``. If the run pauses at the interrupt-only
    ``process_inbox`` gate (a non-empty ``gate_queue``), returns
    ``status="awaiting_review"`` surfacing the pending consolidated queue and the
    ``run_id`` review handle — NO terminal event and NO write (resume via
    ``curation.review``). Otherwise (empty queue → short-circuit) the graph runs
    to END; ``compile_report`` has already stamped the D-09 ``status`` and emitted
    the terminal ``curation_cycle_complete`` audit event, so this runner just
    surfaces the persisted steps/status/events. The sqlite connection is always
    closed in ``finally``.
    """
    run_id = inp.run_id or _new_run_id()
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": run_id}}
        resolved = CurationRunInput(workspace_path=inp.workspace_path, run_id=run_id)
        result = graph.invoke(_initial_state(resolved), cfg)

        snap = graph.get_state(cfg)
        if "__interrupt__" in result and snap.next == ("process_inbox",):
            values = snap.values or {}
            return CurationRunResult(
                status="awaiting_review",
                run_id=run_id,
                gate_id=run_id,
                checkpoint_id=_checkpoint_id(snap),
                gate_queue=_ensure_proposal_ids(values.get("gate_queue", []), run_id),
                steps=[CurationStepResult(**s) for s in values.get("steps", [])],
                events=list(values.get("events", [])),
                message="Curation run paused for human review; resume with curation.review.",
            )

        steps = [CurationStepResult(**s) for s in result["steps"]]
        status = result.get("status") or _aggregate_status(steps)
        return CurationRunResult(
            status=status, run_id=run_id, gate_id=run_id, gate_queue=[],
            steps=steps, events=list(result.get("events", [])),
            message=f"Curation run {status}.",
        )
    finally:
        conn.close()


def _build_resume_decisions(inp: CurationReviewInput, gate_queue: list[dict]) -> dict[str, str]:
    """Build the id-keyed resume payload for one consolidated review (D-07/D-10).

    An explicit ``decisions`` map wins. Otherwise the blanket flags EXPAND into a
    complete map over the queued ids — ``reject_all`` to a hard ``"reject"`` (no
    write), ``approve_all`` to each proposal's recommended ``decision`` (the gate's
    own verdict, explicitly endorsed). Expanding rather than short-circuiting is
    the point (T-18-24): the flags then satisfy the coverage check like any other
    payload instead of becoming a second path to a write.

    With neither flag nor payload the result is an EMPTY map, which covers an
    empty queue cleanly and is rejected against a non-empty one. That is the
    D-10 contract: no decisions means no writes, never the gate's recommendation
    applied on the user's behalf.
    """
    if inp.decisions is not None:
        return _decision_map(inp.decisions)
    if inp.reject_all:
        return {entry["proposal_id"]: "reject" for entry in gate_queue}
    if inp.approve_all:
        return {
            entry["proposal_id"]: entry.get("decision") or "approve" for entry in gate_queue
        }
    return {}


def review_curation_run(inp: CurationReviewInput) -> CurationRunResult:
    """Resume a paused curation run with per-item decisions (read-side; Plan 03).

    Re-opens the checkpointer over the same DB and inspects the persisted snapshot
    for ``thread_id=run_id``. If the run is not paused at ``process_inbox`` it is
    already complete (or never paused) and is surfaced without re-running any write
    (the paused-state guard — CUR-03 idempotency spine). Otherwise it submits
    ``Command(resume=decisions)`` to clear the single interrupt and runs the graph
    to END, then aggregates the D-09 status. Plan 03 has no post-gate apply nodes,
    so resume completes without a canonical write; Plan 04 grafts the write-side.
    The sqlite connection is always closed in ``finally``.
    """
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": inp.run_id}}
        snap = graph.get_state(cfg)
        values = snap.values or {}
        current = _checkpoint_id(snap)

        # D-11: STALENESS FIRST, before the coverage check and before
        # Command(resume=…). Order matters: a stale queue means the coverage check
        # would be comparing the payload against a queue the caller never saw, so
        # its verdict would be meaningless. Exact string equality — no trimming,
        # no case folding, no prefix matching.
        #
        # This is also what makes a REPLAY safe: a successful resume advances the
        # checkpoint, so re-submitting the same decisions with the same id lands
        # here and is refused. ``current is None`` means there is no checkpoint at
        # all (an unknown run), which the paused-state guard below reports more
        # precisely than a staleness message could.
        if current is not None and inp.checkpoint_id != current:
            return CurationRunResult(
                status="failed", run_id=inp.run_id, gate_id=inp.run_id,
                checkpoint_id=current,
                message=StaleQueue(supplied=inp.checkpoint_id, current=current).safe_message,
            )

        if snap.next != ("process_inbox",):
            # Not paused: already-completed run → report as-is; unknown → failed.
            if values and not snap.next:
                steps = [CurationStepResult(**s) for s in values.get("steps", [])]
                return CurationRunResult(
                    status=_aggregate_status(steps),
                    run_id=inp.run_id, checkpoint_id=current, steps=steps,
                    events=list(values.get("events", [])),
                    message="Curation run already complete (no re-review).",
                )
            return CurationRunResult(
                status="failed", run_id=inp.run_id, checkpoint_id=current,
                message="No paused curation run to review.",
            )

        gate_queue = _ensure_proposal_ids(values.get("gate_queue", []), inp.run_id)
        decisions = _build_resume_decisions(inp, gate_queue)
        # D-10: coverage is checked HERE, before Command(resume=…) is submitted —
        # never inside a node, because a node-raised error still advances the
        # checkpoint and would leave the run somewhere other than where the user
        # left it. On rejection the graph is not touched at all.
        try:
            _check_coverage([entry["proposal_id"] for entry in gate_queue], decisions)
        except IncompleteDecisionMap as exc:
            return CurationRunResult(
                status="failed", run_id=inp.run_id, gate_id=inp.run_id,
                checkpoint_id=current, gate_queue=gate_queue,
                steps=[CurationStepResult(**s) for s in values.get("steps", [])],
                events=list(values.get("events", [])),
                message=exc.safe_message,
            )

        result = graph.invoke(Command(resume=_wrap_resume(decisions)), cfg)

        steps = [CurationStepResult(**s) for s in result["steps"]]
        status = result.get("status") or _aggregate_status(steps)
        return CurationRunResult(
            status=status, run_id=inp.run_id, gate_id=inp.run_id, gate_queue=[],
            checkpoint_id=_checkpoint_id(graph.get_state(cfg)),
            steps=steps, events=list(result.get("events", [])),
            message=f"Curation review {status}.",
        )
    finally:
        conn.close()


def inspect_curation_run(inp: CurationInspectInput) -> CurationRunResult:
    """Report a curation run's persisted terminal state — NEVER re-runs (RT-03).

    Re-opens the checkpointer and reads the persisted snapshot for
    ``thread_id=run_id`` via ``graph.get_state``; reconstructs the
    ``CurationRunResult`` from the persisted steps without executing any node. A
    run paused at ``process_inbox`` is surfaced as ``awaiting_review`` with the
    pending consolidated ``gate_queue`` (checked BEFORE the empty-values guard so a
    pending review never reads as failed). A nonexistent run (no persisted values)
    maps to ``status="failed"`` so the catalog shim surfaces ``success=False``
    (WR-03 precedent). NEVER resumes — read-only; closes the sqlite connection in
    ``finally``.
    """
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": inp.run_id}}
        snap = graph.get_state(cfg)
        values = snap.values or {}

        # Paused-at-gate branch FIRST — a run awaiting review has values + a
        # pending next node; surface it without resuming (CUR-04).
        if snap.next == ("process_inbox",):
            steps = [CurationStepResult(**s) for s in values.get("steps", [])]
            return CurationRunResult(
                status="awaiting_review", run_id=inp.run_id, gate_id=inp.run_id,
                checkpoint_id=_checkpoint_id(snap),
                gate_queue=_ensure_proposal_ids(values.get("gate_queue", []), inp.run_id),
                steps=steps, events=list(values.get("events", [])),
                message="Curation run paused awaiting human review.",
            )

        if not values:
            return CurationRunResult(
                status="failed", run_id=inp.run_id,
                message="No such curation run.",
            )

        steps = [CurationStepResult(**s) for s in values.get("steps", [])]
        status = values.get("status") or _aggregate_status(steps)
        return CurationRunResult(
            status=status, run_id=inp.run_id, checkpoint_id=_checkpoint_id(snap),
            steps=steps, events=list(values.get("events", [])),
            message="Curation run inspected (read-only).",
        )
    finally:
        conn.close()
