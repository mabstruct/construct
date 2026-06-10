"""Workflow state machine — multi-step workflow execution with resume support."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from construct.schemas.config import EventAgent, EventResult
from construct.services.event_log import append_event
from construct.services.knowledge import OperationError, OperationResult


class WorkflowStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


@dataclass
class WorkflowStep:
    """A single step in a workflow procedure."""

    name: str
    description: str
    handler: Callable[..., OperationResult]
    handler_kwargs: dict[str, Any] | None = None


@dataclass
class StepResult:
    name: str
    success: bool
    message: str
    data: Any = None
    error: str | None = None


@dataclass
class WorkflowState:
    """Persistent state for a single workflow execution."""

    workflow_name: str
    workflow_version: str = "1.0"
    status: WorkflowStatus = WorkflowStatus.pending
    total_steps: int = 0
    completed_steps: int = 0
    current_step_index: int = 0
    step_results: list[StepResult] = field(default_factory=list)
    started_at: str | None = None
    last_updated: str | None = None
    workspace: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


class WorkflowRunner:
    STATE_DIR = "log"
    STATE_FILE = "workflow-state.json"

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._state: WorkflowState | None = None

    # --- Properties ---

    @property
    def state(self) -> WorkflowState | None:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state is not None and self._state.status == WorkflowStatus.running

    @property
    def progress(self) -> str:
        if self._state is None:
            return "No active workflow"
        return f"{self._state.completed_steps}/{self._state.total_steps} steps complete"

    # --- State file I/O ---

    def _state_path(self) -> Path:
        return self._root / self.STATE_DIR / self.STATE_FILE

    def _save_state(self) -> None:
        """Persist workflow state to JSON file."""
        if self._state is None:
            return
        import json

        path = self._state_path()
        state_dict = {
            "workflow_name": self._state.workflow_name,
            "workflow_version": self._state.workflow_version,
            "status": self._state.status.value,
            "total_steps": self._state.total_steps,
            "completed_steps": self._state.completed_steps,
            "current_step_index": self._state.current_step_index,
            "step_results": [
                {
                    "name": sr.name,
                    "success": sr.success,
                    "message": sr.message,
                    "data": sr.data,
                    "error": sr.error,
                }
                for sr in self._state.step_results
            ],
            "started_at": self._state.started_at,
            "last_updated": self._state.last_updated,
            "workspace": self._state.workspace,
            "data": self._state.data,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(state_dict, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"WARNING: could not write workflow state: {exc}", file=__import__("sys").stderr)

    def _load_state(self) -> WorkflowState | None:
        """Load persisted workflow state from JSON file."""
        path = self._state_path()
        if not path.exists():
            return None
        import json

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            step_results = [
                StepResult(
                    name=sr["name"],
                    success=sr["success"],
                    message=sr["message"],
                    data=sr.get("data"),
                    error=sr.get("error"),
                )
                for sr in data.get("step_results", [])
            ]
            return WorkflowState(
                workflow_name=data["workflow_name"],
                workflow_version=data.get("workflow_version", "1.0"),
                status=WorkflowStatus(data.get("status", "pending")),
                total_steps=data["total_steps"],
                completed_steps=data["completed_steps"],
                current_step_index=data.get("current_step_index", 0),
                step_results=step_results,
                started_at=data.get("started_at"),
                last_updated=data.get("last_updated"),
                workspace=data.get("workspace"),
                data=data.get("data", {}),
            )
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return None

    # --- Public API ---

    def run(
        self,
        steps: list[WorkflowStep],
        workflow_name: str = "workflow",
        workflow_version: str = "1.0",
        start_step: int = 0,
    ) -> OperationResult:
        """Execute a sequence of steps. Supports resuming from *start_step*."""
        now = datetime.now(timezone.utc).isoformat()

        self._state = WorkflowState(
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            status=WorkflowStatus.running,
            total_steps=len(steps),
            completed_steps=0,
            current_step_index=start_step,
            started_at=now,
            last_updated=now,
            workspace=str(self._root),
        )

        append_event(
            self._root,
            EventAgent.construct,
            "workflow_started",
            target=workflow_name,
            detail=f"{len(steps)} steps, starting at step {start_step}",
        )
        self._save_state()

        for i in range(start_step, len(steps)):
            step = steps[i]
            self._state.current_step_index = i
            self._state.last_updated = datetime.now(timezone.utc).isoformat()

            try:
                kwargs = step.handler_kwargs or {}
                result = step.handler(**kwargs)
            except Exception as exc:
                result = OperationResult(
                    success=False,
                    message=f"Step '{step.name}' raised an exception",
                    errors=[OperationError(reason=str(exc))],
                )

            step_result = StepResult(
                name=step.name,
                success=result.success,
                message=result.message,
                data=result.data,
                error=result.errors[0].reason if result.errors else None,
            )
            self._state.step_results.append(step_result)
            self._state.last_updated = datetime.now(timezone.utc).isoformat()

            append_event(
                self._root,
                EventAgent.construct,
                "workflow_step_complete",
                target=workflow_name,
                detail=f"Step {i+1}/{len(steps)}: {step.name} -- {'OK' if result.success else 'FAILED'}",
                result=EventResult.success if result.success else EventResult.failure,
            )

            if not result.success:
                self._state.status = WorkflowStatus.failed
                self._save_state()
                append_event(
                    self._root,
                    EventAgent.construct,
                    "workflow_failed",
                    target=workflow_name,
                    detail=f"Step {i+1} '{step.name}' failed: {result.message}",
                    result=EventResult.failure,
                )
                return OperationResult(
                    success=False,
                    message=f"Workflow '{workflow_name}' failed at step {i+1} ({step.name}): {result.message}",
                    data={"state": self._summarize_state()},
                )

            self._state.completed_steps = i + 1
            self._save_state()

        self._state.status = WorkflowStatus.completed
        self._state.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_state()
        append_event(
            self._root,
            EventAgent.construct,
            "workflow_completed",
            target=workflow_name,
            detail=f"All {len(steps)} steps completed",
        )

        return OperationResult(
            success=True,
            message=f"Workflow '{workflow_name}' completed: {len(steps)}/{len(steps)} steps",
            data={"state": self._summarize_state()},
        )

    def resume(self, steps: list[WorkflowStep]) -> OperationResult:
        """Resume a previously paused/failed workflow from its last saved state.

        Detects the last completed step index from the state file and resumes
        execution from the next uncompleted step.
        """
        loaded = self._load_state()
        if loaded is None:
            return OperationResult(
                success=False,
                message="No saved workflow state found to resume",
                errors=[OperationError(reason="No workflow-state.json exists")],
            )

        if loaded.status == WorkflowStatus.completed:
            return OperationResult(
                success=True,
                message=f"Workflow '{loaded.workflow_name}' is already completed",
                data={"state": self._summarize_state_from(loaded)},
            )

        self._state = loaded
        self._state.status = WorkflowStatus.running
        self._state.last_updated = datetime.now(timezone.utc).isoformat()

        resume_from = self._state.completed_steps  # next uncompleted step
        # Rebuild the step list -- use passed steps, preserve completed results
        completed_names = {sr.name for sr in self._state.step_results if sr.success}

        append_event(
            self._root,
            EventAgent.construct,
            "workflow_resumed",
            target=loaded.workflow_name,
            detail=f"Resuming from step {resume_from + 1}/{len(steps)}",
        )
        self._save_state()

        return self.run(steps, loaded.workflow_name, loaded.workflow_version, start_step=resume_from)

    def status(self) -> OperationResult:
        """Return current workflow status without running anything."""
        loaded = self._load_state()
        if loaded is None:
            return OperationResult(
                success=True,
                message="No active workflow",
                data={"active": False, "state": None},
            )
        return OperationResult(
            success=True,
            message=f"Workflow '{loaded.workflow_name}': {loaded.status.value}",
            data={
                "active": loaded.status in (WorkflowStatus.running, WorkflowStatus.paused),
                "state": self._summarize_state_from(loaded),
            },
        )

    def list_runs(self) -> OperationResult:
        """List all saved workflow state files (typically just one active)."""
        loaded = self._load_state()
        if loaded is None:
            return OperationResult(
                success=True,
                message="No workflow history found",
                data={"runs": []},
            )
        return OperationResult(
            success=True,
            message=f"Found workflow: {loaded.workflow_name}",
            data={"runs": [self._summarize_state_from(loaded)]},
        )

    # --- Internal ---

    def _summarize_state(self) -> dict[str, Any]:
        if self._state is None:
            return {}
        return self._summarize_state_from(self._state)

    @staticmethod
    def _summarize_state_from(state: WorkflowState) -> dict[str, Any]:
        return {
            "workflow_name": state.workflow_name,
            "status": state.status.value,
            "progress": f"{state.completed_steps}/{state.total_steps}",
            "total_steps": state.total_steps,
            "completed_steps": state.completed_steps,
            "current_step_index": state.current_step_index,
            "step_count": len(state.step_results),
            "started_at": state.started_at,
            "last_updated": state.last_updated,
        }
