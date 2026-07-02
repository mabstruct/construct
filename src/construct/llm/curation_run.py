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
  * Three deferred steps (``promotion_review``, ``process_inbox``,
    ``views_refresh_hook``) report ``status="skipped", required=False`` with a
    "deferred to Phase 12" reason — explicit skipped nodes, not fake success (D-10).
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
    decisions: list | None = None
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
    """

    model_config = {"extra": "forbid"}
    kind: Literal["promotion", "connection", "archive", "escalate"]
    decision: str = ""  # default = the gate recommendation (D-07)
    payload: dict = Field(default_factory=dict)


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


def _deferred_step(step: str) -> dict:
    """Emit a deferred skip-node result (D-10): skipped, optional, Phase-12 reason."""
    result = CurationStepResult(
        step=step, status="skipped", required=False,
        reason="deferred to Phase 12",
        summary=f"{step} deferred to Phase 12 (curation gates land in Phase 12)",
    )
    return {"steps": [result.model_dump(mode="json")]}


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
                "; auto_archive_on_decay is set — archiving deferred to Phase 12 "
                "(no card archived this phase)"
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
    return {"decisions": decisions}


# ── Post-gate write nodes (WRITE BOUNDARY — run ONLY after Command(resume); CUR-03) ──


def _normalize_decision(value: Any, default: str) -> str:
    """Map a resume decision token to a concrete per-proposal verdict (D-07).

    ``None`` falls back to the proposal's recommended ``default`` decision (the
    gate's own verdict); the convenience synonym ``approve`` also expands to that
    default so approve-all reproduces every gate recommendation, and ``reject``
    collapses to a hard ``"reject"`` (no write). Any explicit token is passed
    through verbatim so a structured per-item payload keeps full control.
    """
    if value is None:
        return default
    if value == "approve":
        return default
    if value == "reject":
        return "reject"
    return str(value)


def _resolve_decisions(state: CurationRunState) -> list[str]:
    """Resolve the effective per-proposal verdict list aligned with ``gate_queue``.

    The resume payload (``state['decisions']``) is a positional ``list`` aligned
    with the consolidated ``gate_queue`` (built by ``_build_resume_decisions``); a
    short/absent payload falls back to each proposal's recommended ``decision`` so
    no proposal is ever dropped. Only ``approved`` verdicts authorize a write — the
    apply nodes below enforce the only-approved invariant per proposal kind.
    """
    gate_queue = state.get("gate_queue", [])
    raw = state.get("decisions")
    resolved: list[str] = []
    if isinstance(raw, list):
        for i, entry in enumerate(gate_queue):
            value = raw[i] if i < len(raw) else None
            resolved.append(_normalize_decision(value, entry.get("decision", "")))
    else:
        for entry in gate_queue:
            resolved.append(entry.get("decision", ""))
    return resolved


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
    gate_queue = state.get("gate_queue", [])
    decisions = _resolve_decisions(state)
    lifecycles = _card_lifecycle_map(workspace)

    promoted: list[str] = []
    rejected: list[str] = []
    escalated: list[str] = []
    events: list[str] = []

    for entry, decision in zip(gate_queue, decisions):
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
    gate_queue = state.get("gate_queue", [])
    decisions = _resolve_decisions(state)

    added: list[str] = []
    rejected: list[str] = []
    events: list[str] = []

    for entry, decision in zip(gate_queue, decisions):
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
    gate_queue = state.get("gate_queue", [])
    decisions = _resolve_decisions(state)
    lifecycles = _card_lifecycle_map(workspace)

    archived: list[str] = []
    rejected: list[str] = []
    events: list[str] = []

    for entry, decision in zip(gate_queue, decisions):
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
    return _deferred_step("views_refresh_hook")


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
                gate_queue=values.get("gate_queue", []),
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


def _build_resume_decisions(inp: CurationReviewInput, gate_queue: list[dict]) -> list:
    """Resolve the resume payload for one consolidated review (D-07).

    ``reject_all`` maps every proposal to ``"reject"`` (no write); ``approve_all``
    reproduces each proposal's recommended ``decision`` (the gate's own verdict);
    an explicit ``decisions`` list is passed through verbatim. Plan 03 resumes the
    graph with this payload but performs no canonical write (the apply nodes that
    consume these decisions are Plan 04).
    """
    if inp.reject_all:
        return ["reject" for _ in gate_queue]
    if inp.decisions is not None:
        return list(inp.decisions)
    # approve_all (or default): reproduce the recommended per-item decision.
    return [entry.get("decision", "approve") for entry in gate_queue]


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

        if snap.next != ("process_inbox",):
            # Not paused: already-completed run → report as-is; unknown → failed.
            if values and not snap.next:
                steps = [CurationStepResult(**s) for s in values.get("steps", [])]
                return CurationRunResult(
                    status=_aggregate_status(steps),
                    run_id=inp.run_id, steps=steps,
                    events=list(values.get("events", [])),
                    message="Curation run already complete (no re-review).",
                )
            return CurationRunResult(
                status="failed", run_id=inp.run_id,
                message="No paused curation run to review.",
            )

        decisions = _build_resume_decisions(inp, values.get("gate_queue", []))
        result = graph.invoke(Command(resume=decisions), cfg)

        steps = [CurationStepResult(**s) for s in result["steps"]]
        status = result.get("status") or _aggregate_status(steps)
        return CurationRunResult(
            status=status, run_id=inp.run_id, gate_id=inp.run_id, gate_queue=[],
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
                gate_queue=values.get("gate_queue", []),
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
            status=status, run_id=inp.run_id, steps=steps,
            events=list(values.get("events", [])),
            message="Curation run inspected (read-only).",
        )
    finally:
        conn.close()
