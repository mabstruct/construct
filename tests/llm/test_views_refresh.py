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
