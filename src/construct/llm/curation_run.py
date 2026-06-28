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


# ── Graph builder + runners (implemented in Tasks 2–3; importable now) ──


def build_curation_run_graph(checkpointer: Any):  # noqa: D401 — filled in Task 2
    raise NotImplementedError("build_curation_run_graph lands in Task 2")


def run_curation_run(inp: CurationRunInput) -> CurationRunResult:  # filled in Task 3
    raise NotImplementedError("run_curation_run lands in Task 3")


def inspect_curation_run(inp: CurationInspectInput) -> CurationRunResult:  # filled in Task 3
    raise NotImplementedError("inspect_curation_run lands in Task 3")
