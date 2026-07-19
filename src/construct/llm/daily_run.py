"""Thin ``daily.run`` composition workflow (Phase 13, DAY-01/02/03).

``daily.run`` is a THIN synchronous Python composition — NOT a LangGraph parent
graph. It calls the frozen child entrypoints in order and folds their typed
results into one ``DailyRunResult`` (D-09):

    research.run → curation.run → graph.status

Design constraints honored here (RESEARCH §Architecture Patterns / Anti-Patterns):
  * NO parent LangGraph graph, checkpointer, or graph invocation at this layer.
    Each child owns its own graph, SQLite checkpointer, and thread lifecycle;
    embedding them as nodes would nest a graph-in-node for zero durability benefit
    (D-01 forbids any parent-level pause). Isolate-and-degrade (D-06) is a
    ``try/except`` per child.
  * NON-BLOCKING (D-01): a paused research/curation child is auto-resumed with the
    gate's *recommended* decisions via the child ``review_*_run(approve_all=True)``
    path — daily.run never interrupts for review. Escalate items receive NO
    canonical write and are surfaced as a pending-escalation count (D-02/D-03a),
    captured BEFORE the curation resume (Pitfall 5).
  * NO false ``completed`` (DAY-03/D-07): a failed/degraded/awaiting child OR any
    pending escalation forces ``degraded``; ``failed`` only if the whole cycle
    could not run. Child-failure detail is sanitized via ``_sanitize_error``.
  * daily.run emits NO events of its own (D-04): the children's apply nodes fire
    the full ``gate_review_*`` + ``workflow_step_complete`` audit trail. This
    module never imports the event-log writer nor emits any event itself.
  * ``logging`` to stderr only — NEVER ``print`` (stdout is the MCP JSON-RPC
    transport).
  * ``run_id`` is kebab-validated (``_validate_run_id``) before it becomes the
    ``.construct/workflow/daily/<run_id>.json`` receipt path (V5 / path traversal).
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Reuse the frozen child entrypoints + security helpers verbatim (D-09 — do NOT
# re-author). Imported into this module's namespace so composition is a direct
# function call (and so tests can spy on the exact call sites).
from construct.llm.curation_run import (
    CurationRunInput,
    CurationReviewInput,
    _sanitize_error,
    _validate_run_id,
    review_curation_run,
    run_curation_run,
)
from construct.llm.research_run import (
    ResearchRunInput,
    ReviewInput,
    review_research_run,
    run_research_run,
)
from construct.pipelines.graph_status import graph_status

logger = logging.getLogger(__name__)


# ── In-module I/O models (defined HERE, not catalog.py — avoid circular import) ──


class DailyRunInput(BaseModel):
    """Input for the ``daily.run`` capability (run-start)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str | None = None

    _check_run_id = field_validator("run_id")(_validate_run_id)


class DailyInspectInput(BaseModel):
    """Input for ``daily.inspect`` (read a persisted receipt — never re-runs)."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str

    _check_run_id = field_validator("run_id")(_validate_run_id)


class DailyChildStatus(BaseModel):
    """One composed child's folded status surface (DAY-02)."""

    model_config = {"extra": "forbid"}
    capability: str  # "research.run" | "curation.run" | "graph.status"
    status: str  # completed | degraded | failed | awaiting_review | skipped
    run_id: str | None = None
    pending_escalations: int = 0
    message: str = ""


class DailyRunResult(BaseModel):
    """Run-level result surface for ``daily.run`` / ``daily.inspect`` (D-07)."""

    model_config = {"extra": "forbid"}
    status: Literal["completed", "degraded", "failed"]  # parent aggregate (no pause)
    run_id: str
    children: list[DailyChildStatus] = Field(default_factory=list)
    pending_escalations: int = 0
    graph_health: dict = Field(default_factory=dict)
    message: str = ""


# ── Helpers ──


def _new_run_id() -> str:
    """Generate a sortable, kebab-safe daily run handle (mirrors curation's form).

    The stamp uses ``-`` (not ISO ``T``) so the handle satisfies
    ``KEBAB_CASE_PATTERN`` — the same invariant ``_validate_run_id`` enforces on
    caller-supplied ids; the ``daily-`` prefix + ``-research`` / ``-curation``
    child suffixes stay kebab-valid.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"daily-{stamp}-{secrets.token_hex(3)}"


def _aggregate_daily_status(children: list[DailyChildStatus], pending_escalations: int) -> str:
    """DAY-03 'no false completed' roll-up over the composed children.

    ``failed`` only if the cycle could not run at all (every child failed);
    ``degraded`` if ANY child is failed/degraded/awaiting_review OR any escalation
    remains unresolved; ``completed`` otherwise.
    """
    if children and all(ch.status == "failed" for ch in children):
        return "failed"
    if pending_escalations > 0 or any(
        ch.status in ("failed", "degraded", "awaiting_review") for ch in children
    ):
        return "degraded"
    return "completed"


def _receipt_path(workspace_path: str, run_id: str) -> Path:
    """Resolve the receipt path (caller MUST have kebab-validated ``run_id``)."""
    return Path(workspace_path) / ".construct" / "workflow" / "daily" / f"{run_id}.json"


def _run_research_child(workspace_path: str, child_run_id: str) -> DailyChildStatus:
    """Run the research child; auto-resume a paused gate with recommended ingest.

    Isolate-and-degrade (D-06): any exception is caught and surfaced as a
    ``failed`` child with a sanitized message — it never aborts the cycle.
    """
    try:
        r = run_research_run(ResearchRunInput(workspace_path=workspace_path, run_id=child_run_id))
        if r.status == "awaiting_review":
            r = review_research_run(ReviewInput(workspace_path=workspace_path, run_id=r.run_id, approve_all=True))
        return DailyChildStatus(
            capability="research.run", status=r.status, run_id=r.run_id, message=r.message
        )
    except Exception as exc:  # noqa: BLE001 — isolate + degrade (D-06)
        logger.warning("daily.run: research child failed: %s", _sanitize_error(exc))
        return DailyChildStatus(
            capability="research.run", status="failed", run_id=child_run_id,
            message=_sanitize_error(exc),
        )


def _run_curation_child(workspace_path: str, child_run_id: str) -> tuple[DailyChildStatus, int]:
    """Run the curation child; count pending escalations BEFORE the resume.

    The escalate count is read from the ``awaiting_review`` result's ``gate_queue``
    (it is ``[]`` after resume — Pitfall 5), then the run is resumed with the
    gate's recommended decisions via ``review_curation_run(approve_all=True)``
    (D-02); escalate items are never written by the child apply nodes (D-03).
    The empty-queue short-circuit means a run that never paused is NOT resumed
    (Pitfall 3).
    """
    pending = 0
    try:
        c = run_curation_run(CurationRunInput(workspace_path=workspace_path, run_id=child_run_id))
        if c.status == "awaiting_review":
            pending = sum(1 for p in c.gate_queue if p.get("kind") == "escalate")
            c = review_curation_run(CurationReviewInput(workspace_path=workspace_path, run_id=c.run_id, approve_all=True))
        return DailyChildStatus(
            capability="curation.run", status=c.status, run_id=c.run_id,
            pending_escalations=pending, message=c.message,
        ), pending
    except Exception as exc:  # noqa: BLE001 — isolate + degrade (D-06)
        logger.warning("daily.run: curation child failed: %s", _sanitize_error(exc))
        return DailyChildStatus(
            capability="curation.run", status="failed", run_id=child_run_id,
            message=_sanitize_error(exc),
        ), 0


def _run_graph_child(workspace_path: str) -> tuple[DailyChildStatus, dict]:
    """Fold the closing ``graph.status`` health summary into the result."""
    try:
        op = graph_status(workspace_path)
        health = op.data or {}
        return DailyChildStatus(
            capability="graph.status",
            status="completed" if op.success else "failed",
            message=op.message,
        ), health
    except Exception as exc:  # noqa: BLE001 — isolate + degrade (D-06)
        logger.warning("daily.run: graph.status failed: %s", _sanitize_error(exc))
        return DailyChildStatus(
            capability="graph.status", status="failed", message=_sanitize_error(exc)
        ), {}


def _run_views_refresh(workspace_path: str):
    """Rebuild the SPA's views cache at the tail of the cycle (D-12).

    **Deliberately asymmetric with the other ``_run_*`` helpers: this one does NOT
    return a ``DailyChildStatus``.** ``DailyChildStatus`` is precisely the type
    ``_aggregate_daily_status`` consumes, so returning one would invite a future edit
    to append it to ``children`` — and an advisory cache rebuild would then be able to
    degrade a completed maintenance cycle. Returning the refresh helper's own type
    makes that mistake require a deliberate conversion rather than a one-line append.

    **D-12's accepted cost is paid here.** A single daily cycle triggers THREE sweeps:
    research.run's, curation.run's, and this one. That is a direct consequence of
    daily.run tracking no parent/child relationship (Phase 13 D-09 — there is no parent
    graph and no signal a child could read to know it is nested), and D-12 chose the
    rule that needs no parent-awareness: every workflow refreshes. The incremental
    fingerprinting in ``views/lib/fingerprint.py`` makes the later sweeps cheap — an
    unchanged install root short-circuits before any per-workspace file is rewritten
    (asserted by ``test_second_sweep_over_unchanged_root_writes_less``) — but the
    children DO mutate the workspace, so in a live cycle the later sweeps are usually
    real rebuilds rather than no-ops, and ``version.json`` churns more than once per
    cycle while the SPA polls it. Bounded by the ``views.auto_regenerate`` kill switch.
    """
    from construct.views.refresh import refresh_views

    # D-05: the generator is install-root scoped and discovers workspaces as its
    # children; passing the workspace itself would find zero and publish an empty
    # build that looks like a successful refresh.
    install_root = Path(workspace_path).parent

    outcome = refresh_views(install_root)
    if outcome.status == "failed":
        logger.warning("daily.run: views refresh failed: %s", outcome.reason)
    else:
        logger.info("daily.run: views refresh %s", outcome.status)
    return outcome


# ── Runners ──


def run_daily_run(inp: DailyRunInput) -> DailyRunResult:
    """Compose research.run → curation.run → graph.status into one daily cycle.

    Non-blocking (D-01): each paused child is auto-resumed with its recommended
    gate decisions; escalate items are surfaced as a pending count, never written
    (D-02/D-03). Isolate-and-degrade (D-06): a failing child is caught and the
    remaining children still run. The folded ``DailyRunResult`` never reports a
    false ``completed`` (DAY-03) and is persisted as a receipt for ``daily.inspect``.
    daily.run emits NO events of its own — the children own the audit trail (D-04).
    """
    run_id = inp.run_id or _new_run_id()
    workspace = inp.workspace_path

    research_child = _run_research_child(workspace, f"{run_id}-research")
    curation_child, pending_escalations = _run_curation_child(workspace, f"{run_id}-curation")
    graph_child, graph_health = _run_graph_child(workspace)

    children = [research_child, curation_child, graph_child]
    status = _aggregate_daily_status(children, pending_escalations)
    result = DailyRunResult(
        status=status,
        run_id=run_id,
        children=children,
        pending_escalations=pending_escalations,
        graph_health=graph_health,
        message=f"Daily cycle {status}.",
    )

    # D-12: refresh AFTER the children and AFTER `status` is computed, so the outcome
    # cannot reach `_aggregate_daily_status`, `children`, `pending_escalations` or
    # `graph_health` — the exclusion is structural, not a matter of discipline. Before
    # the receipt write so the persisted record covers a complete cycle. The returned
    # outcome is intentionally dropped: it is logged inside the helper and is not a
    # success condition of anything here.
    _run_views_refresh(workspace)

    # Persist the receipt AFTER run_id passed the kebab validator (path safety).
    path = _receipt_path(workspace, run_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    except OSError as exc:  # non-fatal — the run result still returns to the caller
        logger.warning("daily.run: could not persist receipt %s: %s", path, _sanitize_error(exc))
    return result


def inspect_daily_run(inp: DailyInspectInput) -> DailyRunResult:
    """Read a persisted daily-run receipt (read-only; never re-runs).

    A missing receipt resolves to ``status="failed"`` with the message
    ``"No such daily run."`` (mirrors ``inspect_curation_run``'s no-such-run
    branch). ``run_id`` is kebab-validated on the input model before the path join.
    """
    path = _receipt_path(inp.workspace_path, inp.run_id)
    if not path.exists():
        return DailyRunResult(status="failed", run_id=inp.run_id, message="No such daily run.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DailyRunResult(**data)
    except (OSError, ValueError) as exc:
        logger.warning("daily.run: unreadable receipt %s: %s", path, _sanitize_error(exc))
        return DailyRunResult(status="failed", run_id=inp.run_id, message="No such daily run.")
