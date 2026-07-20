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

    # Scoped to the views node rather than the whole file: `decay_scan`'s
    # auto_archive summary carries its own, unrelated "deferred to Phase 12" string,
    # pinned by test_auto_archive_reported_not_acted. That is a different node's
    # contract and is out of this plan's scope — see the 15-04 summary.
    src = Path(curation_run.__file__).read_text(encoding="utf-8")
    node_src = src[src.index("def views_refresh_hook"):]
    node_src = node_src[: node_src.index("\n# ──")] if "\n# ──" in node_src else node_src
    assert "deferred to Phase 12" not in node_src.split('"""')[-1]


# ── Task 3: daily.run — the refresh sits OUTSIDE the status fold ──


def _canned_daily_children(monkeypatch: pytest.MonkeyPatch, daily_run) -> None:
    """Stub the three children so the cycle is offline and its status is fixed."""
    from construct.llm.curation_run import CurationRunResult
    from construct.llm.research_run import RunResult
    from construct.services.knowledge import OperationResult

    monkeypatch.setattr(
        daily_run, "run_research_run",
        lambda inp: RunResult(status="completed", run_id=inp.run_id),
    )
    monkeypatch.setattr(
        daily_run, "run_curation_run",
        lambda inp: CurationRunResult(status="completed", run_id=inp.run_id),
    )
    monkeypatch.setattr(
        daily_run, "graph_status",
        lambda ws_: OperationResult(
            success=True, message="ok",
            data={"cards": {}, "connections": {}, "domains": {}},
        ),
    )


def test_daily_run_status_unchanged_when_refresh_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-12: the refresh outcome is structurally excluded from the daily status fold.

    Also asserts the receipt still lands when the refresh fails — a broken cache
    rebuild must not cost the cycle its audit record.
    """
    from construct.llm import daily_run
    from tests.llm.conftest import create_test_workspace

    ws = create_test_workspace(tmp_path / "ws")
    _scaffold_build_dir(tmp_path)
    _canned_daily_children(monkeypatch, daily_run)

    monkeypatch.setattr("construct.views.generate.generate", _Spy())
    good = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-vr-ok")
    )

    monkeypatch.setattr("construct.views.generate.generate", _Spy(raises=RuntimeError("boom")))
    bad = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-vr-bad")
    )

    assert good.status == bad.status == "completed"
    assert [c.status for c in good.children] == [c.status for c in bad.children]
    # No refresh child was smuggled into the fold.
    assert len(bad.children) == 3
    assert all(c.capability != "views.refresh" for c in bad.children)
    # The receipt survives a failing refresh.
    receipt = tmp_path / "ws" / ".construct" / "workflow" / "daily" / "daily-vr-bad.json"
    assert receipt.is_file(), "receipt must be written even when the refresh fails"


def test_refresh_runs_at_end_of_each_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The accepted D-12 cost is real and understood, not accidentally suppressed.

    A daily cycle triggers MORE THAN ONE sweep because daily.run tracks no
    parent/child relationship (Phase 13 D-09) — each child refreshes for itself and
    daily.run refreshes again at the end. Here the curation child is real, so the
    count is curation's sweep plus daily's own.
    """
    from construct.llm import daily_run
    from construct.llm.research_run import RunResult
    from construct.services.knowledge import OperationResult
    from tests.llm.conftest import create_test_workspace

    ws = create_test_workspace(tmp_path / "ws")
    _scaffold_build_dir(tmp_path)

    monkeypatch.setattr(
        daily_run, "run_research_run",
        lambda inp: RunResult(status="completed", run_id=inp.run_id),
    )
    monkeypatch.setattr(
        daily_run, "graph_status",
        lambda ws_: OperationResult(
            success=True, message="ok",
            data={"cards": {}, "connections": {}, "domains": {}},
        ),
    )
    spy = _Spy()
    monkeypatch.setattr("construct.views.generate.generate", spy)

    daily_run.run_daily_run(daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-vr-count"))

    assert len(spy.calls) > 1, (
        "a daily cycle must sweep more than once — the D-12 accepted cost. "
        f"got {len(spy.calls)}"
    )
    assert set(spy.calls) == {tmp_path}, "every sweep targets the install root (D-05)"


def test_second_sweep_over_unchanged_root_writes_less(tmp_path: Path) -> None:
    """The fingerprint no-op claim that makes the three-sweep cost acceptable.

    Asserted rather than assumed: if a repeat sweep over an unchanged install root
    cost the same as the first, D-12's accepted cost would be three full builds.
    """
    from construct.views.generate import generate
    from tests.llm.conftest import create_test_workspace

    create_test_workspace(tmp_path / "ws")

    first = generate(tmp_path)
    second = generate(tmp_path)

    assert first.success and second.success
    assert second.total_files_written < first.total_files_written


def test_refresh_keeps_reporting_failure_across_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-01 at the refresh boundary: a failed refresh must not self-heal.

    ``refresh_views`` reports ``failed`` when the generator reports validation
    errors. Before the CR-01 fix the failing run still saved the source
    fingerprints, so the *second* refresh over the same unchanged install root hit
    the generator's incremental short-circuit and reported ``succeeded`` — turning
    a permanently broken build into a permanently clean signal.
    """
    import construct.views.generate as gen_mod
    from tests.llm.conftest import create_test_workspace

    create_test_workspace(tmp_path / "ws")
    _scaffold_build_dir(tmp_path)

    real_validate = gen_mod._validate_file_data

    def _reject_stats(rel_path: str, raw_data: dict, errors: list[str]) -> bool:
        if rel_path == "stats.json":
            errors.append("stats.json: injected validation failure")
            return True
        return real_validate(rel_path, raw_data, errors)

    monkeypatch.setattr(gen_mod, "_validate_file_data", _reject_stats)

    first = refresh_views(tmp_path)
    second = refresh_views(tmp_path)

    assert first.status == "failed", first
    assert second.status == "failed", (
        "the refresh failure channel healed itself over unchanged state"
    )


# ── WR-01: the call sites themselves, not just refresh_views' internal try ──


def _patch_refresh_helper(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    """Make ``refresh_views`` ITSELF raise.

    The paired tests above inject failures inside the *generator*, which
    ``refresh_views`` catches — so they exercise the helper's guarantee, not the
    call sites'. The prologue at each call site (deferred import, install-root
    derivation, logging, and curation's closing ``_emit``) sits outside that
    guarantee, and only patching the helper reaches it.
    """

    def _boom(install_root):  # noqa: ANN001, ANN202 — test double
        raise exc

    monkeypatch.setattr("construct.views.refresh.refresh_views", _boom)


def test_daily_run_survives_a_raising_refresh_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-01: ``_run_views_refresh`` was the one child invocation with no try.

    It sits between the status computation and the receipt write, so anything
    raising through it aborted ``run_daily_run`` before the receipt was persisted
    and turned the whole capability into ``success=False`` — the outcome D-12
    forbids.
    """
    from construct.llm import daily_run
    from tests.llm.conftest import create_test_workspace

    ws = create_test_workspace(tmp_path / "ws")
    _scaffold_build_dir(tmp_path)
    _canned_daily_children(monkeypatch, daily_run)

    monkeypatch.setattr("construct.views.generate.generate", _Spy())
    good = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-helper-ok")
    )

    _patch_refresh_helper(monkeypatch, RuntimeError("helper exploded"))
    bad = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-helper-bad")
    )

    assert good.status == bad.status == "completed"
    assert [c.status for c in good.children] == [c.status for c in bad.children]
    receipt = tmp_path / "ws" / ".construct" / "workflow" / "daily" / "daily-helper-bad.json"
    assert receipt.is_file(), (
        "the receipt was lost because a raising refresh aborted the run before the write"
    )


def test_curation_run_survives_a_raising_refresh_helper(
    curation_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-01: the curation node's contract is 'cannot fail the run'."""
    from construct.llm import curation_run

    install_root = curation_workspace.parent
    _scaffold_build_dir(install_root)

    monkeypatch.setattr("construct.views.generate.generate", _Spy())
    good = curation_run.run_curation_run(
        curation_run.CurationRunInput(
            workspace_path=str(curation_workspace), run_id="cur-helper-ok"
        )
    )

    _patch_refresh_helper(monkeypatch, RuntimeError("helper exploded"))
    bad = curation_run.run_curation_run(
        curation_run.CurationRunInput(
            workspace_path=str(curation_workspace), run_id="cur-helper-bad"
        )
    )

    assert good.status == bad.status
    # The node still reports itself honestly rather than vanishing from the record.
    step = next(
        (s if isinstance(s, dict) else s.model_dump())
        for s in bad.steps
        if (s if isinstance(s, dict) else s.model_dump())["step"] == "views_refresh_hook"
    )
    assert step["required"] is False
    assert "RuntimeError" in (step.get("reason") or "")


def test_research_run_survives_a_raising_refresh_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-01: research.run's refresh node returns {} — but only if it returns."""
    from construct.llm import research_run

    node = research_run.views_refresh
    _scaffold_build_dir(tmp_path)
    _patch_refresh_helper(monkeypatch, RuntimeError("helper exploded"))

    ws = tmp_path / "ws"
    ws.mkdir(parents=True, exist_ok=True)

    assert node({"workspace_path": str(ws), "status": "completed"}) == {}
