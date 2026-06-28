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
from pydantic import BaseModel, Field, field_validator

from construct.schemas.card import Lifecycle
from construct.schemas.config import KEBAB_CASE_PATTERN

logger = logging.getLogger(__name__)


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

    # Output
    status: str  # running | completed | degraded | failed
    events: list[str]


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
    status: Literal["completed", "degraded", "failed"]
    run_id: str
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
    return {"steps": [result.model_dump(mode="json")]}


def decay_scan(state: CurationRunState) -> dict:
    """Findings-only decay candidate scan (D-04/D-05/D-06).

    Candidate = non-archived card whose recency anchor (``last_verified`` or
    ``created``) is older than the governance ``decay_window_days``. Reports
    ``auto_archive_on_decay`` but NEVER archives a card (D-06 — archiving is
    deferred to Phase 12).
    """
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
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("decay_scan", exc)
    return {"steps": [result.model_dump(mode="json")]}


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
    return {"steps": [result.model_dump(mode="json")]}


def connection_maintenance(state: CurationRunState) -> dict:
    """Connection-health via ``bridge_detect`` (offline L1/L2; L3 auto-skips).

    ``bridge_detect`` is NOT pure read-only — it writes DERIVED
    ``log/bridge-candidates.json`` + ``views/build/data/bridges.json`` (Pitfall 1);
    that is allowed under D-06 (derived, not canonical SOT). No canonical fact is
    written.
    """
    try:
        from construct.pipelines.bridge_detect import bridge_detect

        op = bridge_detect(state["workspace_path"])
        summary_block = (op.data or {}).get("summary", {})
        totals = summary_block.get("totals", {})
        l1_l2_only = summary_block.get("l1_l2_only")
        result = CurationStepResult(
            step="connection_maintenance",
            status="completed" if op.success else "failed",
            findings={"totals": totals, "l1_l2_only": l1_l2_only, "ok": op.success},
            summary=(
                "connection-health via bridge_detect; derived log/+views/ artifacts "
                "written (no canonical SOT write)"
            ),
            reason=None if op.success else op.message,
        )
    except Exception as exc:  # noqa: BLE001 — node robustness (T-11-02)
        result = _failed_step("connection_maintenance", exc)
    return {"steps": [result.model_dump(mode="json")]}


def compile_report(state: CurationRunState) -> dict:
    """Roll up the graph status report via ``graph_status`` (read-only counts)."""
    try:
        from construct.pipelines.graph_status import graph_status

        op = graph_status(state["workspace_path"])
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
    return {"steps": [result.model_dump(mode="json")]}


# ── Deferred skip-nodes (D-10 — explicit skipped nodes, not fake success) ──


def promotion_review(state: CurationRunState) -> dict:
    return _deferred_step("promotion_review")


def process_inbox(state: CurationRunState) -> dict:
    return _deferred_step("process_inbox")


def views_refresh_hook(state: CurationRunState) -> dict:
    return _deferred_step("views_refresh_hook")


# ── Graph builder (purely LINEAR spec §4.3 topology — no conditional edges) ──


def build_curation_run_graph(checkpointer: Any):
    """Compile the deterministic curation StateGraph with the given checkpointer.

    Linear topology (spec §4.3): START → load_config → integrity_check →
    decay_scan → orphan_scan → promotion_review(SKIP) → connection_maintenance →
    process_inbox(SKIP) → compile_report → views_refresh_hook(SKIP) → END.
    ``load_config`` runs first to populate the governance thresholds the scans read.
    """
    builder = StateGraph(CurationRunState)

    builder.add_node("load_config", load_config)
    builder.add_node("integrity_check", integrity_check)
    builder.add_node("decay_scan", decay_scan)
    builder.add_node("orphan_scan", orphan_scan)
    builder.add_node("promotion_review", promotion_review)
    builder.add_node("connection_maintenance", connection_maintenance)
    builder.add_node("process_inbox", process_inbox)
    builder.add_node("compile_report", compile_report)
    builder.add_node("views_refresh_hook", views_refresh_hook)

    builder.add_edge(START, "load_config")
    builder.add_edge("load_config", "integrity_check")
    builder.add_edge("integrity_check", "decay_scan")
    builder.add_edge("decay_scan", "orphan_scan")
    builder.add_edge("orphan_scan", "promotion_review")
    builder.add_edge("promotion_review", "connection_maintenance")
    builder.add_edge("connection_maintenance", "process_inbox")
    builder.add_edge("process_inbox", "compile_report")
    builder.add_edge("compile_report", "views_refresh_hook")
    builder.add_edge("views_refresh_hook", END)

    return builder.compile(checkpointer=checkpointer)


# ── Run/inspect runners + D-09 status aggregation + terminal event ──


def _aggregate_status(steps: list[CurationStepResult]) -> str:
    """D-09 run-level roll-up (Pitfall 5).

    ``degraded`` if any REQUIRED step is ``failed`` or ``skipped``; ``completed``
    otherwise. The three deferred nodes are ``required=False`` so they never
    degrade a clean run.
    """
    required_bad = [s for s in steps if s.required and s.status in ("failed", "skipped")]
    return "degraded" if required_bad else "completed"


def run_curation_run(inp: CurationRunInput) -> CurationRunResult:
    """Run the deterministic curation cycle to completion and aggregate status.

    Opens the persistent checkpointer, builds the linear graph, and invokes it once
    (no resume/interrupt) with ``thread_id = run_id``. Reconstructs the per-step
    results, computes the D-09 aggregate, appends one terminal
    ``curation_cycle_complete`` event, and returns the ``CurationRunResult``. The
    sqlite connection is always closed in ``finally``.
    """
    from construct.schemas.config import EventAgent
    from construct.services.event_log import append_event

    run_id = inp.run_id or _new_run_id()
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": run_id}}
        resolved = CurationRunInput(workspace_path=inp.workspace_path, run_id=run_id)
        result = graph.invoke(_initial_state(resolved), cfg)

        steps = [CurationStepResult(**s) for s in result["steps"]]
        status = _aggregate_status(steps)

        events = list(result.get("events", []))
        append_event(
            Path(inp.workspace_path), EventAgent.curator,
            "curation_cycle_complete", target=run_id, detail=status,
        )
        events.append("curation_cycle_complete")

        return CurationRunResult(
            status=status, run_id=run_id, steps=steps, events=events,
            message=f"Curation run {status}.",
        )
    finally:
        conn.close()


def inspect_curation_run(inp: CurationInspectInput) -> CurationRunResult:
    """Report a curation run's persisted terminal state — NEVER re-runs (RT-03).

    Re-opens the checkpointer and reads the persisted snapshot for
    ``thread_id=run_id`` via ``graph.get_state``; reconstructs the
    ``CurationRunResult`` from the persisted steps without executing any node. A
    nonexistent run (no persisted values) maps to ``status="failed"`` so the
    catalog shim surfaces ``success=False`` (WR-03 precedent). Performs no
    workspace mutation; closes the sqlite connection in ``finally``.
    """
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": inp.run_id}}
        snap = graph.get_state(cfg)
        values = snap.values or {}

        if not values:
            return CurationRunResult(
                status="failed", run_id=inp.run_id,
                message="No such curation run.",
            )

        steps = [CurationStepResult(**s) for s in values.get("steps", [])]
        status = _aggregate_status(steps)
        return CurationRunResult(
            status=status, run_id=inp.run_id, steps=steps,
            events=values.get("events", []),
            message="Curation run inspected (read-only).",
        )
    finally:
        conn.close()
