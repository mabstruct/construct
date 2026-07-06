"""Wave 0 red suite for the ``daily.run`` thin-composition workflow (Phase 13).

``daily.run`` composes the frozen child entrypoints ``research.run`` →
``curation.run`` → ``graph.status`` into ONE non-blocking maintenance cycle
(D-09). It never pauses at the parent level (D-01): a paused research/curation
child is auto-resumed with the gate's *recommended* decisions via the child
``review_*_run(approve_all=True)`` path, escalate items are surfaced as a
pending-escalation count and NEVER auto-written (D-02/D-03), a failing child is
isolated-and-degraded (D-06), and the result never reports a false ``completed``
(DAY-03).

The production module ``construct.llm.daily_run`` does NOT exist yet, so it is
imported lazily INSIDE each test body — never at module top — so
``--collect-only`` succeeds while the suite stays RED on ImportError.

Sampling point → test map (RESEARCH §Validation Architecture):
  DAY-01  composes children in order         → test_composes_children
  DAY-02  result surface (per-child + health)→ test_result_surface
  DAY-03  isolate + degrade, no false done   → test_degrade_on_child_failure
  DAY-03  pending escalate → degraded        → test_no_false_completed_on_pending_escalation
  D-02/03 auto-apply excludes escalate       → test_auto_apply_excludes_escalate
  D-08    receipt round-trip / no-such-run   → test_inspect_roundtrip
  V5      run_id kebab path-traversal guard  → test_run_id_kebab_guard
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import pytest

from tests.llm.conftest import create_test_workspace


# ── Offline L3-gate seam (clone of tests/llm/test_curation_run.py) ──────────
#
# ``curation.run`` fans out over TWO L3 gates (promotion + connection-typing).
# One canned object cannot satisfy both, so this mock dispatches on the requested
# structured-output model class name. Card/pair identity is filled from the input
# by the gate runner, so a single canned verdict per gate is enough.


class _GateRoutingMock:
    def __init__(self, *, promotion, connection) -> None:
        self._promotion = promotion
        self._connection = connection
        self._selected = None

    def with_structured_output(self, model_class, **kwargs):
        name = getattr(model_class, "__name__", "")
        self._selected = self._connection if "Connection" in name else self._promotion
        return self

    def invoke(self, messages):
        return self._selected


def _install_curation_gate_mocks(
    monkeypatch,
    *,
    promotion_decision: str = "promote",
    target_lifecycle: str | None = "growing",
    connection_type: str = "supports",
) -> None:
    """Patch ``factory.build_chat_model`` so the curation child's L3 gates run
    fully offline. Lazily imports the gate output models (they already ship)."""
    from construct.llm.curation_promote import PromotionDecision
    from construct.llm.curation_connect import ConnectionTypeDecision
    from tests.llm.conftest import make_build_chat_model

    promotion = PromotionDecision(
        card_id="_",
        decision=promotion_decision,
        target_lifecycle=target_lifecycle,
        reasoning="gate reasoning",
        method="llm-judgment",
    )
    connection = ConnectionTypeDecision(
        from_card_id="_",
        to_card_id="_",
        connection_type=connection_type,
        reasoning="typed by the connection gate",
    )
    mock = _GateRoutingMock(promotion=promotion, connection=connection)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model", make_build_chat_model(mock)
    )


def _canned_research(status: str = "completed"):
    """Return a ``run_research_run`` replacement yielding a fixed ``RunResult``.

    Keeps the composition/degrade/surface tests offline and network-free: the
    research child's search/score path is exercised by its own suite, not here.
    """
    from construct.llm.research_run import RunResult

    def _fn(inp):
        return RunResult(status=status, run_id=inp.run_id)

    return _fn


def _canned_curation(status: str = "completed"):
    from construct.llm.curation_run import CurationRunResult

    def _fn(inp):
        return CurationRunResult(status=status, run_id=inp.run_id)

    return _fn


# ── DAY-01: composes research → curation → graph.status in order ────────────


def test_composes_children(tmp_path, monkeypatch):
    """DAY-01: ``run_daily_run`` invokes the child entrypoints as plain functions
    in the order research.run → curation.run → graph.status, and folds each into
    ``result.children`` in that order (no child logic re-implemented)."""
    from construct.llm import daily_run
    from construct.llm.research_run import RunResult
    from construct.llm.curation_run import CurationRunResult
    from construct.services.knowledge import OperationResult

    ws = create_test_workspace(tmp_path / "ws")
    calls: list[str] = []

    monkeypatch.setattr(
        daily_run, "run_research_run",
        lambda inp: calls.append("research.run") or RunResult(status="completed", run_id=inp.run_id),
    )
    monkeypatch.setattr(
        daily_run, "run_curation_run",
        lambda inp: calls.append("curation.run") or CurationRunResult(status="completed", run_id=inp.run_id),
    )
    monkeypatch.setattr(
        daily_run, "graph_status",
        lambda ws_: calls.append("graph.status")
        or OperationResult(success=True, message="ok", data={"cards": {}, "connections": {}, "domains": {}}),
    )

    result = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-compose")
    )

    assert calls == ["research.run", "curation.run", "graph.status"]
    assert [c.capability for c in result.children] == [
        "research.run",
        "curation.run",
        "graph.status",
    ]


# ── DAY-02: result surface (per-child status + escalation count + health) ───


def test_result_surface(tmp_path, monkeypatch):
    """DAY-02: ``DailyRunResult`` exposes status, run_id, per-child capability +
    status, an integer pending_escalations, a graph_health dict carrying
    cards/connections/domains, and a message."""
    from construct.llm import daily_run

    ws = create_test_workspace(tmp_path / "ws")
    monkeypatch.setattr(daily_run, "run_research_run", _canned_research())
    monkeypatch.setattr(daily_run, "run_curation_run", _canned_curation())
    # graph_status runs for real → graph_health is genuinely folded.

    result = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-surface")
    )

    assert result.status in ("completed", "degraded", "failed")
    assert result.run_id == "daily-surface"
    assert isinstance(result.pending_escalations, int)
    assert result.children, "at least the three composed children must surface"
    for child in result.children:
        assert child.capability
        assert child.status
    assert {"cards", "connections", "domains"} <= set(result.graph_health.keys())
    assert isinstance(result.message, str) and result.message


# ── DAY-03: isolate + degrade; failing child never aborts the cycle ─────────


def test_degrade_on_child_failure(tmp_path, monkeypatch):
    """DAY-03 / D-06: when the research child raises, curation + graph.status
    still run and the parent status is ``degraded`` (never ``completed``); the
    child-failure message is sanitized to the class name + first line only — no
    raw multi-line provider text leaks."""
    from construct.llm import daily_run

    ws = create_test_workspace(tmp_path / "ws")
    secret_tail = "sk-do-not-leak-0987654321"

    def _boom(inp):
        raise RuntimeError(f"provider handshake failed\nAUTH_TOKEN={secret_tail}")

    curation_calls: list[str] = []

    def _cur(inp):
        curation_calls.append(inp.run_id)
        return _canned_curation()(inp)

    monkeypatch.setattr(daily_run, "run_research_run", _boom)
    monkeypatch.setattr(daily_run, "run_curation_run", _cur)

    result = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-degrade")
    )

    # Isolate + degrade: the later children still ran despite the research raise.
    assert curation_calls, "curation child must run even when research fails (D-06)"
    caps = [c.capability for c in result.children]
    assert "curation.run" in caps and "graph.status" in caps

    assert result.status == "degraded"
    assert result.status != "completed"

    research_child = next(c for c in result.children if c.capability == "research.run")
    assert research_child.status in ("failed", "degraded")
    # Sanitized: class name present, raw multi-line tail dropped.
    assert "RuntimeError" in research_child.message
    assert secret_tail not in research_child.message
    assert "\n" not in research_child.message


def test_no_false_completed_on_pending_escalation(curation_workspace, monkeypatch):
    """DAY-03 / D-07: a curation ``awaiting_review`` result carrying an
    escalate-kind proposal yields pending_escalations >= 1 and a parent status of
    ``degraded`` (never a bare ``completed``); the count is captured BEFORE the
    approve_all resume (Pitfall 5)."""
    from construct.llm import daily_run

    _install_curation_gate_mocks(
        monkeypatch, promotion_decision="escalate", target_lifecycle=None
    )
    monkeypatch.setattr(daily_run, "run_research_run", _canned_research())

    result = daily_run.run_daily_run(
        daily_run.DailyRunInput(
            workspace_path=str(curation_workspace), run_id="daily-escalate"
        )
    )

    assert result.pending_escalations >= 1
    curation_child = next(c for c in result.children if c.capability == "curation.run")
    assert curation_child.pending_escalations >= 1
    assert result.status == "degraded"
    assert result.status != "completed"


# ── D-02/D-03: auto-apply recommended, exclude escalate; emit no events ─────


def test_auto_apply_excludes_escalate(curation_workspace, monkeypatch):
    """D-02/D-03: recommended promotions are auto-applied via
    ``review_curation_run(approve_all=True)``; an escalate recommendation is NEVER
    written; and ``daily_run`` emits NO events of its own (D-04 inherited from the
    children)."""
    from construct.llm import daily_run
    from construct.storage.workspace import WorkspaceLoader

    def _lifecycles() -> dict:
        return {c["id"]: str(c["lifecycle"]) for c in WorkspaceLoader(curation_workspace).load_cards()}

    monkeypatch.setattr(daily_run, "run_research_run", _canned_research())

    # ── escalate: the recommended escalate is surfaced but NEVER auto-written ──
    _install_curation_gate_mocks(
        monkeypatch, promotion_decision="escalate", target_lifecycle=None
    )
    before = _lifecycles()
    daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(curation_workspace), run_id="daily-esc")
    )
    after_escalate = _lifecycles()
    assert after_escalate == before, "escalate items must not be auto-written (no lifecycle change)"

    # ── promote: the recommended promotion IS auto-applied via approve_all ──
    _install_curation_gate_mocks(
        monkeypatch, promotion_decision="promote", target_lifecycle="growing"
    )
    daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(curation_workspace), run_id="daily-promote")
    )
    after_promote = _lifecycles()
    assert any(after_promote[cid] == "growing" for cid in before), (
        "recommended promotion must be auto-applied via the child approve_all resume"
    )

    # ── D-04: daily_run adds no logging of its own; the children own the trail ──
    src = _inspect.getsource(daily_run)
    assert "append_event" not in src
    assert "_emit(" not in src


# ── D-08: persisted receipt round-trips; missing run resolves to failed ─────


def test_inspect_roundtrip(tmp_path, monkeypatch):
    """D-08: after ``run_daily_run`` the persisted receipt is read back by
    ``inspect_daily_run``; a missing run_id resolves to status ``failed`` with the
    message ``"No such daily run."``."""
    from construct.llm import daily_run

    ws = create_test_workspace(tmp_path / "ws")
    monkeypatch.setattr(daily_run, "run_research_run", _canned_research())
    monkeypatch.setattr(daily_run, "run_curation_run", _canned_curation())

    ran = daily_run.run_daily_run(
        daily_run.DailyRunInput(workspace_path=str(ws), run_id="daily-roundtrip")
    )
    got = daily_run.inspect_daily_run(
        daily_run.DailyInspectInput(workspace_path=str(ws), run_id="daily-roundtrip")
    )
    assert got.run_id == ran.run_id
    assert got.status == ran.status
    assert [c.capability for c in got.children] == [c.capability for c in ran.children]

    missing = daily_run.inspect_daily_run(
        daily_run.DailyInspectInput(workspace_path=str(ws), run_id="daily-missing-xyz")
    )
    assert missing.status == "failed"
    assert missing.message == "No such daily run."


# ── V5: run_id kebab guard blocks path traversal before any receipt path join ─


def test_run_id_kebab_guard():
    """V5 / T-13-02: ``DailyRunInput`` / ``DailyInspectInput`` reject a non-kebab
    run_id (path-traversal guard) before it can reach the receipt file path."""
    from pydantic import ValidationError

    from construct.llm import daily_run

    for bad in ("../../etc/passwd", "Bad_Id", "spaces here", "UPPER", "a/b"):
        with pytest.raises(ValidationError):
            daily_run.DailyRunInput(workspace_path="ws", run_id=bad)
        with pytest.raises(ValidationError):
            daily_run.DailyInspectInput(workspace_path="ws", run_id=bad)

    ok = daily_run.DailyRunInput(workspace_path="ws", run_id="daily-2026-07-06")
    assert ok.run_id == "daily-2026-07-06"
