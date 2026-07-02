"""Wave 0 RED suite for the ``card.evaluate`` L3 promotion gate + the inline
connection-typing gate (Phase 12, CUR-02 / D-05).

The gate runners ``construct.llm.curation_promote`` and
``construct.llm.curation_connect`` do NOT exist yet — they are created in Plans
02-05 as symbol-for-symbol siblings of ``construct.llm.research_score``
(``score_one`` → ``evaluate_one``, ``score_all`` → ``evaluate_all``, ``run_gate``,
plus the outage error class + sanitizer). They are imported lazily INSIDE each
test body — never at module top — so this file COLLECTS cleanly (a top-level
``ModuleNotFoundError`` would abort the whole ``pytest tests/`` session, since the
repo runs without ``--continue-on-collection-errors``) while the suite stays RED
on the missing import at run time. When the gate modules land, these tests turn
GREEN one wave at a time.

Requirement → test map (12-VALIDATION.md CUR-02 rows):
  CUR-02  card.evaluate → PromotionDecision (promote/hold/escalate) + reasoning
          over NON-mature cards        → test_evaluate_one_{promote,hold,escalate}
  CUR-02  per-item retry → escalate + method="rule-based"
                                       → test_failure_escalates
  CUR-02  genuine borderline keeps method="llm-judgment"
                                       → test_retry_then_succeed_keeps_llm_method
  CUR-02  candidate pre-filter (D-02): mature + archived excluded before fan-out
                                       → test_candidate_prefilter_excludes_mature_and_archived
  CUR-02  bounded fan-out + total-outage discrimination
                                       → test_total_outage_when_all_provider_failures
                                       → test_run_gate_raises_on_total_outage
  T-12-01 sanitizer never leaks a key token (copied verbatim vs the new class)
                                       → test_sanitized_error_never_leaks_key_token
  D-05    connection-typing gate assigns a ConnectionType enum + reasoning
                                       → test_connection_typing_assigns_enum
                                       → test_type_all_returns_typed_decisions
"""
from __future__ import annotations

import pytest

from tests.llm.conftest import (
    ConfigurableStructuredMock,
    InvalidOutputMock,
    TotalOutageMock,
    make_build_chat_model,
)


# ── fixtures / builders ─────────────────────────────────────────────────────


def _raw_decision(
    *,
    card_id: str = "card-1",
    decision: str = "promote",
    target_lifecycle: str | None = "growing",
    method: str = "llm-judgment",
    reasoning: str = "LLM rationale for the proposed promotion.",
):
    """Build a 'raw' LLM-proposed PromotionDecision for the configurable mock.

    Imports ``PromotionDecision`` lazily so a missing Plan-02 module surfaces at
    RUN time (RED), never at collection time.
    """
    from construct.llm.curation_promote import PromotionDecision

    return PromotionDecision(
        card_id=card_id,
        decision=decision,
        target_lifecycle=target_lifecycle,
        reasoning=reasoning,
        method=method,
    )


def _raw_connection(
    *,
    from_card_id: str = "card-1",
    to_card_id: str = "card-2",
    connection_type: str = "supports",
    reasoning: str = "Card 1 provides empirical support for card 2.",
):
    from construct.llm.curation_connect import ConnectionTypeDecision

    return ConnectionTypeDecision(
        from_card_id=from_card_id,
        to_card_id=to_card_id,
        connection_type=connection_type,
        reasoning=reasoning,
    )


def _card(
    card_id: str,
    *,
    lifecycle: str = "seed",
    title: str | None = None,
    body: str = "Card body content under evaluation for lifecycle promotion.",
    confidence: int = 3,
    source_tier: int = 3,
    content_categories: list[str] | None = None,
) -> dict:
    """A minimal card payload the gate fans out over (D-02 pre-filter input)."""
    return {
        "id": card_id,
        "title": title or card_id.replace("-", " ").title(),
        "lifecycle": lifecycle,
        "body": body,
        "confidence": confidence,
        "source_tier": source_tier,
        "content_categories": content_categories or ["test-category"],
    }


def _pair(
    *,
    from_card_id: str = "card-1",
    to_card_id: str = "card-2",
) -> dict:
    """A ``bridge_detect`` candidate pair (bridge_detect.py:233-244 shape)."""
    return {
        "pair_id": f"{from_card_id}::{to_card_id}",
        "from_card_id": from_card_id,
        "to_card_id": to_card_id,
        "from_domain": "test-domain",
        "to_domain": "test-domain",
        "from_title": from_card_id.replace("-", " ").title(),
        "to_title": to_card_id.replace("-", " ").title(),
        "l1_structural": True,
        "l2_shared_categories": ["test-category"],
        "pre_score": 0.72,
    }


# ── evaluate_one: decision mapping over NON-mature cards (CUR-02) ────────────


def test_evaluate_one_promote() -> None:
    from construct.llm.curation_promote import PromotionDecision, evaluate_one

    raw = _raw_decision(card_id="card-1", decision="promote", target_lifecycle="growing")
    llm = ConfigurableStructuredMock(raw)
    decision = evaluate_one(_card("card-1", lifecycle="seed"), llm=llm)
    assert isinstance(decision, PromotionDecision)
    assert decision.decision == "promote"
    assert decision.target_lifecycle == "growing"
    assert decision.reasoning
    assert decision.method == "llm-judgment"
    assert llm.output_model is PromotionDecision


def test_evaluate_one_hold() -> None:
    from construct.llm.curation_promote import evaluate_one

    raw = _raw_decision(decision="hold", target_lifecycle=None)
    decision = evaluate_one(
        _card("card-1", lifecycle="growing"), llm=ConfigurableStructuredMock(raw)
    )
    assert decision.decision == "hold"
    assert decision.target_lifecycle is None


def test_evaluate_one_escalate() -> None:
    from construct.llm.curation_promote import evaluate_one

    raw = _raw_decision(decision="escalate", target_lifecycle=None)
    decision = evaluate_one(
        _card("card-1", lifecycle="growing"), llm=ConfigurableStructuredMock(raw)
    )
    assert decision.decision == "escalate"
    assert decision.reasoning


# ── candidate pre-filter (D-02): mature + archived excluded before fan-out ───


def test_candidate_prefilter_excludes_mature_and_archived() -> None:
    from construct.llm.curation_promote import evaluate_all

    cards = [
        _card("c-seed", lifecycle="seed"),
        _card("c-growing", lifecycle="growing"),
        _card("c-mature", lifecycle="mature"),
        _card("c-archived", lifecycle="archived"),
    ]
    llm = ConfigurableStructuredMock(_raw_decision(decision="promote"))
    batch = evaluate_all(cards, llm=llm, cap=4)
    evaluated_ids = {d.card_id for d in batch.decisions}
    assert "c-seed" in evaluated_ids
    assert "c-growing" in evaluated_ids
    # mature has nowhere to be promoted; archived is out of scope entirely.
    assert "c-mature" not in evaluated_ids
    assert "c-archived" not in evaluated_ids


# ── per-item retry → escalate (D-03) ────────────────────────────────────────


def test_failure_escalates() -> None:
    """A card that still fails after one retry becomes a rule-based ESCALATE — it
    never silently drops and never fabricates an llm-judgment verdict."""
    from construct.llm.curation_promote import evaluate_all

    batch = evaluate_all(
        [_card("card-1", lifecycle="seed")],
        llm=InvalidOutputMock(retry_succeeds=False),
        cap=1,
    )
    decision = batch.decisions[0]
    assert decision.decision == "escalate"
    assert decision.method == "rule-based"
    assert batch.counters.errors == 1


def test_retry_then_succeed_keeps_llm_method() -> None:
    """A genuine borderline verdict recovered on retry keeps method='llm-judgment'
    (only forced-failure escalations are 'rule-based')."""
    from construct.llm.curation_promote import evaluate_all

    raw = _raw_decision(decision="hold", target_lifecycle=None, method="llm-judgment")
    llm = InvalidOutputMock(retry_succeeds=True, retry_output=raw)
    batch = evaluate_all([_card("card-1", lifecycle="seed")], llm=llm, cap=1)
    decision = batch.decisions[0]
    assert decision.decision == "hold"
    assert decision.method == "llm-judgment"
    assert batch.counters.retried == 1
    assert batch.counters.errors == 0


# ── bounded fan-out + total-outage discrimination (CUR-02) ──────────────────


def test_evaluate_all_returns_all_candidates_with_cap() -> None:
    from construct.llm.curation_promote import evaluate_all

    cards = [_card("c1", lifecycle="seed"), _card("c2", lifecycle="growing")]
    llm = ConfigurableStructuredMock(_raw_decision(decision="hold", target_lifecycle=None))
    batch = evaluate_all(cards, llm=llm, cap=2)
    assert len(batch.decisions) == 2
    assert batch.total_outage is False


def test_total_outage_when_all_provider_failures() -> None:
    from construct.llm.curation_promote import evaluate_all

    cards = [_card("c1", lifecycle="seed"), _card("c2", lifecycle="growing")]
    batch = evaluate_all(cards, llm=TotalOutageMock(), cap=2)
    assert batch.total_outage is True
    assert batch.decisions == []


def test_run_gate_raises_on_total_outage(
    test_workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from construct.llm.curation_promote import CardEvaluateInput, CardEvaluateOutageError, run_gate

    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(TotalOutageMock()),
    )
    with pytest.raises(CardEvaluateOutageError):
        run_gate(
            "card.evaluate",
            CardEvaluateInput(workspace_path=str(test_workspace)),
        )


# ── T-12-01: sanitizer never leaks a key token (copied verbatim vs new class) ─


def test_sanitized_error_never_leaks_key_token() -> None:
    from construct.llm.curation_promote import evaluate_all

    class _LeakyMock:
        def with_structured_output(self, model_class, **kwargs):
            return self

        def invoke(self, messages):
            raise ValueError("parse failed sk-ant-api03-SECRETKEY123 in payload")

    batch = evaluate_all(
        [_card("card-1", lifecycle="seed")],
        llm=_LeakyMock(),
        cap=1,
    )
    decision = batch.decisions[0]
    # The raw provider text (with the key token) must NEVER reach the surface.
    assert "sk-ant-api03-SECRETKEY123" not in decision.reasoning
    # A failed evaluation escalates under a safe, class-level cause.
    assert decision.decision == "escalate"
    assert decision.method == "rule-based"


def test_run_gate_happy_path(
    test_workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from construct.llm.curation_promote import CardEvaluateInput, run_gate

    raw = _raw_decision(decision="promote", target_lifecycle="growing")
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(ConfigurableStructuredMock(raw)),
    )
    output = run_gate(
        "card.evaluate",
        CardEvaluateInput(workspace_path=str(test_workspace)),
    )
    # test_workspace carries card-1/card-2 (seed) + card-3 (archived); only the
    # two non-mature, non-archived cards are evaluated.
    evaluated_ids = {d.card_id for d in output.decisions}
    assert "card-3" not in evaluated_ids
    assert output.gate.gate_id == "card.evaluate"


# ── connection-typing L3 gate (D-05) ────────────────────────────────────────


def test_connection_typing_assigns_enum() -> None:
    from construct.llm.curation_connect import ConnectionTypeDecision, type_one
    from construct.schemas.workspace import ConnectionType

    raw = _raw_connection(from_card_id="card-1", to_card_id="card-2", connection_type="supports")
    decision = type_one(
        _pair(from_card_id="card-1", to_card_id="card-2"),
        llm=ConfigurableStructuredMock(raw),
    )
    assert isinstance(decision, ConnectionTypeDecision)
    assert decision.connection_type == ConnectionType.supports
    assert decision.from_card_id == "card-1"
    assert decision.to_card_id == "card-2"
    assert decision.reasoning


def test_type_all_returns_typed_decisions() -> None:
    from construct.llm.curation_connect import type_all
    from construct.schemas.workspace import ConnectionType

    pairs = [
        _pair(from_card_id="card-1", to_card_id="card-2"),
        _pair(from_card_id="card-2", to_card_id="card-3"),
    ]
    raw = _raw_connection(connection_type="extends", reasoning="B extends the argument in A.")
    batch = type_all(pairs, llm=ConfigurableStructuredMock(raw), cap=2)
    assert len(batch.decisions) == 2
    for decision in batch.decisions:
        assert isinstance(decision.connection_type, ConnectionType)
        assert decision.reasoning
