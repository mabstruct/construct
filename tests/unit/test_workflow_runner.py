"""Unit tests for the WorkflowRunner state machine."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from construct.pipelines.workflow_runner import (
    StepResult,
    WorkflowRunner,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
)
from construct.services.knowledge import OperationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(**data: object) -> OperationResult:
    """Return a successful OperationResult, optionally with data."""
    return OperationResult(success=True, message="ok", data=data or None)


def _fail(msg: str = "fail") -> OperationResult:
    """Return a failed OperationResult."""
    return OperationResult(success=False, message=msg)


def _state_file_exists(workspace: Path) -> bool:
    return (workspace / "log" / "workflow-state.json").exists()


def _read_state_file(workspace: Path) -> dict:
    return json.loads((workspace / "log" / "workflow-state.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner(tmp_path: Path) -> WorkflowRunner:
    return WorkflowRunner(tmp_path)


# ===================================================================
# Run Tests
# ===================================================================


class TestRun:
    def test_run_completes_all_steps(self, runner: WorkflowRunner) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        def step2(**kw: object) -> OperationResult:
            return _ok()

        def step3(**kw: object) -> OperationResult:
            return _ok()

        steps = [
            WorkflowStep(name="step1", description="First step", handler=step1),
            WorkflowStep(name="step2", description="Second step", handler=step2),
            WorkflowStep(name="step3", description="Third step", handler=step3),
        ]

        result = runner.run(steps)

        assert result.success is True
        assert runner.state is not None
        assert runner.state.completed_steps == 3
        assert runner.state.status == WorkflowStatus.completed
        assert runner.is_running is False
        assert runner.progress == "3/3 steps complete"

    def test_run_stops_on_failure(self, runner: WorkflowRunner) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        def step2(**kw: object) -> OperationResult:
            return _fail("something went wrong")

        def step3(**kw: object) -> OperationResult:
            return _ok()

        steps = [
            WorkflowStep(name="step1", description="First step", handler=step1),
            WorkflowStep(name="step2", description="Failing step", handler=step2),
            WorkflowStep(name="step3", description="Should not run", handler=step3),
        ]

        result = runner.run(steps)

        assert result.success is False
        assert runner.state is not None
        # completed_steps counts only successful steps
        assert runner.state.completed_steps == 1
        assert runner.state.status == WorkflowStatus.failed
        assert "fail" in result.message or "something went wrong" in result.message

    def test_state_file_persists(self, runner: WorkflowRunner) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        def step2(**kw: object) -> OperationResult:
            return _ok()

        steps = [
            WorkflowStep(name="step1", description="First", handler=step1),
            WorkflowStep(name="step2", description="Second", handler=step2),
        ]

        runner.run(steps, workflow_name="test-workflow")

        assert _state_file_exists(runner._root) is True
        state = _read_state_file(runner._root)
        assert state["workflow_name"] == "test-workflow"
        assert state["completed_steps"] == 2
        assert state["status"] == "completed"

    def test_workflow_step_handler_exception(self, runner: WorkflowRunner) -> None:
        def crashing_step(**kw: object) -> OperationResult:
            msg = "internal error"
            raise RuntimeError(msg)

        steps = [
            WorkflowStep(name="ok-step", description="Fine", handler=lambda **kw: _ok()),
            WorkflowStep(name="crash-step", description="Boom", handler=crashing_step),
        ]

        result = runner.run(steps)

        assert result.success is False
        assert "raised an exception" in result.message

    def test_state_attributes(self, runner: WorkflowRunner) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        steps = [
            WorkflowStep(name="custom-step", description="Custom", handler=step1),
        ]

        runner.run(steps, workflow_name="my-custom-workflow", workflow_version="2.0")

        state = _read_state_file(runner._root)
        assert state["workflow_name"] == "my-custom-workflow"
        assert state["workflow_version"] == "2.0"


# ===================================================================
# Resume Tests
# ===================================================================


class TestResume:
    def test_resume_continues(self, tmp_path: Path) -> None:
        """Resume continues from the next uncompleted step after a failure."""
        call_log: list[str] = []

        def step1(**kw: object) -> OperationResult:
            call_log.append("step1")
            return _ok()

        def step2(**kw: object) -> OperationResult:
            call_log.append("step2")
            return _ok()

        def step3(**kw: object) -> OperationResult:
            call_log.append("step3")
            return _fail("step3 failed")

        steps = [
            WorkflowStep(name="step1", description="First", handler=step1),
            WorkflowStep(name="step2", description="Second", handler=step2),
            WorkflowStep(name="step3", description="Third", handler=step3),
        ]

        # First run: step1 and step2 succeed, step3 fails
        r1 = WorkflowRunner(tmp_path)
        r1.run(steps)
        assert r1.state is not None
        # completed_steps counts only successful steps
        assert r1.state.completed_steps == 2
        assert r1.state.status == WorkflowStatus.failed

        # Second run: resume with all steps succeeding now
        call_log2: list[str] = []

        def step3_ok(**kw: object) -> OperationResult:
            call_log2.append("step3")
            return _ok()

        resume_steps = [
            WorkflowStep(name="step1", description="First", handler=lambda **kw: _ok()),
            WorkflowStep(name="step2", description="Second", handler=lambda **kw: _ok()),
            WorkflowStep(name="step3", description="Third", handler=step3_ok),
        ]

        r2 = WorkflowRunner(tmp_path)
        result = r2.resume(resume_steps)

        assert result.success is True
        assert r2.state is not None
        assert r2.state.completed_steps == 3
        assert r2.state.status == WorkflowStatus.completed
        # step3 should have been called (resumed), step1/step2 were already done
        assert call_log2 == ["step3"]

    def test_resume_no_state(self, tmp_path: Path) -> None:
        runner = WorkflowRunner(tmp_path)
        steps = [WorkflowStep(name="s1", description="Test", handler=lambda **kw: _ok())]

        result = runner.resume(steps)

        assert result.success is False
        assert "No saved workflow state" in result.message

    def test_resume_already_complete(self, tmp_path: Path) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        steps = [WorkflowStep(name="s1", description="Only step", handler=step1)]

        r1 = WorkflowRunner(tmp_path)
        r1.run(steps)
        assert r1.state is not None
        assert r1.state.status == WorkflowStatus.completed

        r2 = WorkflowRunner(tmp_path)
        result = r2.resume(steps)

        assert result.success is True
        assert "already completed" in result.message


# ===================================================================
# Status Tests
# ===================================================================


class TestStatus:
    def test_status_no_active(self, runner: WorkflowRunner) -> None:
        result = runner.status()

        assert result.success is True
        assert result.data is not None
        assert result.data["active"] is False

    def test_status_after_run(self, runner: WorkflowRunner) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        steps = [WorkflowStep(name="s1", description="Only step", handler=step1)]
        runner.run(steps)

        result = runner.status()

        assert result.success is True
        assert result.data is not None
        assert result.data["active"] is False
        assert result.data["state"]["status"] == "completed"


# ===================================================================
# List Runs Tests
# ===================================================================


class TestListRuns:
    def test_list_runs_empty(self, runner: WorkflowRunner) -> None:
        result = runner.list_runs()

        assert result.success is True
        assert result.data is not None
        assert result.data["runs"] == []

    def test_list_runs_after_run(self, runner: WorkflowRunner) -> None:
        def step1(**kw: object) -> OperationResult:
            return _ok()

        steps = [WorkflowStep(name="s1", description="Only step", handler=step1)]
        runner.run(steps, workflow_name="list-test")

        result = runner.list_runs()

        assert result.success is True
        assert result.data is not None
        assert len(result.data["runs"]) == 1
        assert result.data["runs"][0]["workflow_name"] == "list-test"


# ===================================================================
# State File Edge Cases
# ===================================================================


class TestStateFileEdgeCases:
    def test_corrupt_state_file_returns_none(self, tmp_path: Path) -> None:
        """A corrupt/malformed state file should be treated as no state."""
        state_dir = tmp_path / "log"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "workflow-state.json"
        state_file.write_text("{invalid json!!!", encoding="utf-8")

        runner = WorkflowRunner(tmp_path)
        loaded = runner._load_state()
        assert loaded is None

    def test_resume_with_corrupt_state(self, tmp_path: Path) -> None:
        """Resume with corrupt state file returns failure."""
        state_dir = tmp_path / "log"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "workflow-state.json"
        state_file.write_text("{invalid}", encoding="utf-8")

        steps = [WorkflowStep(name="s1", description="Test", handler=lambda **kw: _ok())]
        runner = WorkflowRunner(tmp_path)
        result = runner.resume(steps)

        assert result.success is False
        assert "No saved workflow state" in result.message or "No workflow-state.json" in result.message

    def test_state_file_write_failure_non_blocking(self, runner: WorkflowRunner) -> None:
        """State file write failure should not crash the runner."""
        # Make the log directory a file to prevent directory creation
        log_path = runner._root / "log"
        log_path.write_text("I am a file, not a directory", encoding="utf-8")

        def step1(**kw: object) -> OperationResult:
            return _ok()

        steps = [WorkflowStep(name="s1", description="Only step", handler=step1)]
        # Should not crash despite being unable to write state file
        result = runner.run(steps)
        assert result.success is True


# ===================================================================
# WorkflowState / StepResult Dataclass Tests
# ===================================================================


class TestDataclasses:
    def test_workflow_state_defaults(self) -> None:
        state = WorkflowState(workflow_name="test")
        assert state.workflow_version == "1.0"
        assert state.status == WorkflowStatus.pending
        assert state.total_steps == 0
        assert state.step_results == []
        assert state.data == {}

    def test_step_result_defaults(self) -> None:
        sr = StepResult(name="test", success=True, message="done")
        assert sr.data is None
        assert sr.error is None


# ===================================================================
# Runner Property Tests
# ===================================================================


class TestRunnerProperties:
    def test_state_property_none_initially(self, runner: WorkflowRunner) -> None:
        assert runner.state is None

    def test_is_running_false_initially(self, runner: WorkflowRunner) -> None:
        assert runner.is_running is False

    def test_progress_no_active(self, runner: WorkflowRunner) -> None:
        assert runner.progress == "No active workflow"
