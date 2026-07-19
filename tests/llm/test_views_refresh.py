"""Post-workflow views refresh: gates, swallow-and-log, and the D-12 side-effect rule.

The load-bearing tests here are the *paired* ones: each workflow is run twice against
equivalent state — once with a healthy refresh, once with the generator monkeypatched to
raise — and the two runs must report the **same** status. Asserting only that a single run
completed would pass even if a failing refresh were silently degrading the workflow.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from construct.views.refresh import refresh_views


def _scaffold_build_dir(install_root: Path) -> None:
    """Create the `views/build/` directory the existence gate looks for."""
    (install_root / "views" / "build").mkdir(parents=True, exist_ok=True)


def _write_views_config(install_root: Path, body: str) -> None:
    """Write a `.construct/config.yaml` carrying a `views:` block."""
    cfg_dir = install_root / ".construct"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(body, encoding="utf-8")


class _Spy:
    """Records generator invocations; optionally raises."""

    def __init__(self, raises: Exception | None = None) -> None:
        self.calls: list[Path] = []
        self._raises = raises

    def __call__(self, install_root: Path):  # noqa: ANN204 — test double
        self.calls.append(Path(install_root))
        if self._raises is not None:
            raise self._raises
        from construct.views.generate import GenerateReport

        return GenerateReport(success=True, build_id="spy-build", total_files_written=9)


def _patch_generator(monkeypatch: pytest.MonkeyPatch, spy: _Spy) -> _Spy:
    monkeypatch.setattr("construct.views.generate.generate", spy)
    return spy


# ── Task 1: the two gates and the never-raise contract ──


def test_refresh_skipped_when_no_build_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spy = _patch_generator(monkeypatch, _Spy(raises=AssertionError("generator must not run")))

    outcome = refresh_views(tmp_path)

    assert outcome.status == "skipped"
    assert spy.calls == []


def test_refresh_skipped_when_auto_regenerate_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scaffold_build_dir(tmp_path)
    _write_views_config(tmp_path, "views:\n  auto_regenerate: false\n")
    spy = _patch_generator(monkeypatch, _Spy(raises=AssertionError("generator must not run")))

    outcome = refresh_views(tmp_path)

    assert outcome.status == "skipped"
    assert "auto_regenerate" in outcome.reason
    assert spy.calls == []


def test_refresh_succeeds_and_carries_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scaffold_build_dir(tmp_path)
    spy = _patch_generator(monkeypatch, _Spy())

    outcome = refresh_views(tmp_path)

    assert outcome.status == "succeeded"
    assert outcome.build_id == "spy-build"
    assert outcome.files_written == 9
    assert spy.calls == [tmp_path]


def test_refresh_failed_when_generator_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scaffold_build_dir(tmp_path)
    _patch_generator(monkeypatch, _Spy(raises=RuntimeError("boom")))

    # Must NOT propagate — D-12: the refresh is a side effect, never a failure channel.
    outcome = refresh_views(tmp_path)

    assert outcome.status == "failed"
    assert "RuntimeError" in outcome.reason


def test_refresh_failed_when_report_has_validation_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scaffold_build_dir(tmp_path)

    from construct.views.generate import GenerateReport

    def _bad(install_root: Path) -> GenerateReport:
        return GenerateReport(
            success=False, build_id="b", validation_errors=["stats.json: nope"]
        )

    monkeypatch.setattr("construct.views.generate.generate", _bad)

    outcome = refresh_views(tmp_path)

    assert outcome.status == "failed"
    assert "1" in outcome.reason


# ── Task 2: curation.run and research.run — the paired-status side-effect proof ──


def test_curation_run_status_unchanged_when_refresh_raises(
    curation_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-12: a refresh that blows up must not move the curation run's status.

    The two runs differ ONLY in whether the generator raises. Comparing them is what
    proves the rule — asserting a single run "completed" would still pass if the
    failure branch were quietly degrading the run.
    """
    from construct.llm import curation_run

    install_root = curation_workspace.parent
    _scaffold_build_dir(install_root)

    healthy = _Spy()
    monkeypatch.setattr("construct.views.generate.generate", healthy)
    good = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-vr-ok")
    )

    monkeypatch.setattr("construct.views.generate.generate", _Spy(raises=RuntimeError("boom")))
    bad = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-vr-bad")
    )

    assert good.status == bad.status
    # The refresh really ran, and against the INSTALL ROOT — not the workspace (D-05).
    assert healthy.calls == [install_root]


def test_curation_refresh_step_reports_what_happened(
    curation_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The replaced node must report its real outcome, never a hardcoded status."""
    from construct.llm import curation_run

    install_root = curation_workspace.parent
    _scaffold_build_dir(install_root)
    monkeypatch.setattr("construct.views.generate.generate", _Spy())

    run = curation_run.run_curation_run(
        curation_run.CurationRunInput(workspace_path=str(curation_workspace), run_id="cur-vr-step")
    )

    step = next(
        (s if isinstance(s, dict) else s.model_dump())
        for s in run.steps
        if (s if isinstance(s, dict) else s.model_dump())["step"] == "views_refresh_hook"
    )
    assert step["status"] == "completed"
    assert step["required"] is False
    assert "deferred to Phase 12" not in (step.get("reason") or "")
    assert "deferred to Phase 12" not in (step.get("summary") or "")


def test_research_run_status_unchanged_when_refresh_raises(
    tmp_path: Path,
    sample_search_results,
    scored_findings_batch,
    sqlite_checkpointer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-12, research edition: paired healthy/raising runs must agree on status."""
    from langgraph.types import Command

    from construct.llm import research_run, research_score
    from tests.llm.conftest import create_test_workspace

    monkeypatch.setattr(research_score, "run_gate", lambda *a, **k: scored_findings_batch)
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in sample_search_results],
    )

    def _drive(ws: Path, thread: str) -> str:
        saver, _conn, _db = sqlite_checkpointer()
        graph = research_run.build_research_run_graph(saver)
        cfg = {"configurable": {"thread_id": thread}}
        graph.invoke(
            research_run._initial_state(
                research_run.ResearchRunInput(workspace_path=str(ws), run_id=thread)
            ),
            cfg,
        )
        defaults = [e["decision"] for e in graph.get_state(cfg).values["gate_queue"]]
        return graph.invoke(Command(resume=defaults), cfg)["status"]

    root_ok = tmp_path / "ok"
    root_bad = tmp_path / "bad"
    ws_ok = create_test_workspace(root_ok / "ws")
    ws_bad = create_test_workspace(root_bad / "ws")
    _scaffold_build_dir(root_ok)
    _scaffold_build_dir(root_bad)

    healthy = _Spy()
    monkeypatch.setattr("construct.views.generate.generate", healthy)
    good_status = _drive(ws_ok, "run-vr-ok")

    monkeypatch.setattr("construct.views.generate.generate", _Spy(raises=RuntimeError("boom")))
    bad_status = _drive(ws_bad, "run-vr-bad")

    assert good_status == bad_status == "completed"
    assert healthy.calls == [root_ok]


def test_research_graph_ends_through_the_refresh_node() -> None:
    """The documented terminal edge must be the built one."""
    import inspect

    from construct.llm import research_run

    src = inspect.getsource(research_run.build_research_run_graph)
    assert 'add_node("views_refresh"' in src
    assert 'add_edge("update_seeds_and_log", "views_refresh")' in src
    assert 'add_edge("views_refresh", END)' in src
    assert 'add_edge("update_seeds_and_log", END)' not in src


def test_deferred_step_placeholder_is_gone() -> None:
    """T-15-14: the fabricated skipped-status helper must not survive."""
    from construct.llm import curation_run

    assert not hasattr(curation_run, "_deferred_step")
    src = Path(curation_run.__file__).read_text(encoding="utf-8")
    assert "deferred to Phase 12" not in src
