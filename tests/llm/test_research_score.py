"""Tests for the research.score L3 gate (Phase 9).

Plan 02 scope (REAL tests here): single-result scoring, the deterministic
governance ceiling-clamp (D-05), the threshold echo (D-06), soft taxonomy
steering (D-11), and the key_findings clamp rule (D-14 / Pitfall 5).

Plan 03/04 scope (skipped stubs below): bounded fan-out, per-item retry +
skip-with-reason (D-08), total-outage promotion (D-09), and registry/CLI/MCP
parity (D-13). They are named here so later waves fill in the bodies.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from construct.llm.research_score import (
    GovernanceThresholds,
    ResearchScoreInput,
    ResearchScoreOutageError,
    ScoredFinding,
    build_gate_output,
    clamp_action,
    load_governance_thresholds,
    load_taxonomy_categories,
    retrieval_echo,
    run_gate,
    score_all,
    score_one,
)
from tests.llm.conftest import (
    ConfigurableStructuredMock,
    InvalidOutputMock,
    TotalOutageMock,
    make_build_chat_model,
)


def _raw_finding(
    *,
    ingest_action: str,
    relevance_score: float,
    source_tier: int = 2,
    key_findings: list[str] | None = None,
    content_categories: list[str] | None = None,
) -> ScoredFinding:
    """Build a 'raw' LLM-proposed finding (pre-clamp) for the configurable mock."""
    return ScoredFinding(
        url="https://arxiv.org/abs/2401.00001",
        title="Loop Quantum Gravity and the Big Bounce",
        relevance_score=relevance_score,
        source_tier=source_tier,
        ingest_action=ingest_action,
        key_findings=key_findings if key_findings is not None else [],
        content_categories=content_categories or ["loop-quantum-gravity"],
        reasoning="LLM rationale for the proposed action.",
    )


_THRESHOLDS = GovernanceThresholds(
    relevance_threshold=0.3,
    card_creation_threshold=0.6,
    max_papers_per_cycle=50,
)


# ── clamp_action: deterministic ceiling-clamp (D-05) ──


def test_clamp_action_below_relevance_caps_to_skip() -> None:
    assert clamp_action("ref_and_card", 0.2, 0.3, 0.6) == "skip"


def test_clamp_action_between_bands_caps_to_ref_only() -> None:
    assert clamp_action("ref_and_card", 0.5, 0.3, 0.6) == "ref_only"


def test_clamp_action_above_card_band_permits_ref_and_card() -> None:
    assert clamp_action("ref_and_card", 0.9, 0.3, 0.6) == "ref_and_card"


def test_clamp_action_never_promotes_more_permissive() -> None:
    # LLM was conservative (ref_only) at a high score — clamp must not promote.
    assert clamp_action("ref_only", 0.9, 0.3, 0.6) == "ref_only"
    # LLM said skip in the ref_only band — stays skip.
    assert clamp_action("skip", 0.5, 0.3, 0.6) == "skip"


# ── score_one: validated finding where governance permits ──


def test_score_one_returns_validated_finding_unchanged_when_permitted(
    sample_search_results,
) -> None:
    raw = _raw_finding(
        ingest_action="ref_and_card",
        relevance_score=0.9,
        source_tier=2,
        key_findings=["f1", "f2", "f3"],
    )
    llm = ConfigurableStructuredMock(raw)
    finding = score_one(
        sample_search_results[0],
        llm=llm,
        thresholds=_THRESHOLDS,
        taxonomy_categories=["loop-quantum-gravity"],
    )
    assert isinstance(finding, ScoredFinding)
    assert finding.ingest_action == "ref_and_card"
    assert finding.source_tier == 2
    assert 0.0 <= finding.relevance_score <= 1.0
    assert len(finding.key_findings) == 3
    assert llm.output_model is ScoredFinding


# ── score_one: clamp integration (D-05) ──


def test_score_one_clamps_down_to_skip(sample_search_results) -> None:
    raw = _raw_finding(ingest_action="ref_and_card", relevance_score=0.2)
    finding = score_one(
        sample_search_results[0],
        llm=ConfigurableStructuredMock(raw),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
    )
    assert finding.ingest_action == "skip"


def test_score_one_clamps_middle_to_ref_only(sample_search_results) -> None:
    raw = _raw_finding(ingest_action="ref_and_card", relevance_score=0.5)
    finding = score_one(
        sample_search_results[0],
        llm=ConfigurableStructuredMock(raw),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
    )
    assert finding.ingest_action == "ref_only"


def test_score_one_preserves_llm_conservatism(sample_search_results) -> None:
    raw = _raw_finding(ingest_action="ref_only", relevance_score=0.9)
    finding = score_one(
        sample_search_results[0],
        llm=ConfigurableStructuredMock(raw),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
    )
    assert finding.ingest_action == "ref_only"


# ── key_findings rule on clamp-to-skip (D-14 / Pitfall 5) ──


def test_key_findings_cleared_when_clamped_to_skip(sample_search_results) -> None:
    raw = _raw_finding(
        ingest_action="ref_and_card",
        relevance_score=0.1,
        key_findings=["a", "b", "c"],
    )
    finding = score_one(
        sample_search_results[0],
        llm=ConfigurableStructuredMock(raw),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
    )
    assert finding.ingest_action == "skip"
    assert finding.key_findings == []
    # The reasoning must carry the clamp rationale (auditability).
    assert "clamp" in finding.reasoning.lower()


def test_key_findings_retained_for_non_skip(sample_search_results) -> None:
    raw = _raw_finding(
        ingest_action="ref_and_card",
        relevance_score=0.95,
        key_findings=["a", "b", "c", "d", "e"],
    )
    finding = score_one(
        sample_search_results[0],
        llm=ConfigurableStructuredMock(raw),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
    )
    assert finding.ingest_action == "ref_and_card"
    assert finding.key_findings == ["a", "b", "c", "d", "e"]


# ── threshold echo (D-06) ──


def test_retrieval_echo_contains_governance_thresholds() -> None:
    echo = retrieval_echo(_THRESHOLDS)
    assert echo["relevance_threshold"] == 0.3
    assert echo["card_creation_threshold"] == 0.6
    assert echo["max_papers_per_cycle"] == 50


def test_gate_output_echoes_thresholds_in_retrieval_block() -> None:
    output = build_gate_output(
        [],
        gate_id="research.score",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        thresholds=_THRESHOLDS,
    )
    assert output.gate.tier == "L3"
    assert output.retrieval["relevance_threshold"] == 0.3
    assert output.retrieval["card_creation_threshold"] == 0.6
    assert output.retrieval["max_papers_per_cycle"] == 50


# ── taxonomy soft steering (D-11) ──


def test_taxonomy_categories_injected_into_prompt(sample_search_results) -> None:
    raw = _raw_finding(ingest_action="ref_only", relevance_score=0.5)
    llm = ConfigurableStructuredMock(raw)
    score_one(
        sample_search_results[0],
        llm=llm,
        thresholds=_THRESHOLDS,
        taxonomy_categories=["loop-quantum-gravity", "big-bounce"],
    )
    prompt = llm.prompt_text()
    assert "loop-quantum-gravity" in prompt
    assert "big-bounce" in prompt


def test_taxonomy_loader_reads_workspace_categories(test_workspace) -> None:
    categories = load_taxonomy_categories(str(test_workspace))
    assert isinstance(categories, list)
    # Cards in the fixture carry content_categories=["test-category"].
    assert "test-category" in categories


def test_governance_loader_reads_thresholds(test_workspace) -> None:
    thresholds = load_governance_thresholds(str(test_workspace))
    assert isinstance(thresholds, GovernanceThresholds)
    assert 0.0 <= thresholds.relevance_threshold <= 1.0
    assert 0.0 <= thresholds.card_creation_threshold <= 1.0
    assert thresholds.max_papers_per_cycle >= 1


# ── Plan 03: bounded fan-out, retry, outage, run_gate ──


def test_score_all_returns_all_findings_with_cap(sample_search_results) -> None:
    raw = _raw_finding(ingest_action="ref_only", relevance_score=0.5)
    llm = ConfigurableStructuredMock(raw)
    batch = score_all(
        sample_search_results,
        llm=llm,
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
        cap=3,
    )
    assert len(batch.findings) == len(sample_search_results)
    assert batch.counters.results_total == len(sample_search_results)
    assert batch.total_outage is False


def test_invalid_output_retries_then_succeeds(sample_search_results) -> None:
    raw = _raw_finding(ingest_action="ref_only", relevance_score=0.5)
    llm = InvalidOutputMock(retry_succeeds=True, retry_output=raw)
    batch = score_all(
        [sample_search_results[0]],
        llm=llm,
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
        cap=1,
    )
    assert batch.findings[0].ingest_action == "ref_only"
    assert batch.counters.retried == 1
    assert batch.counters.errors == 0


def test_invalid_output_skip_with_reason_when_both_fail(sample_search_results) -> None:
    good_raw = _raw_finding(ingest_action="ref_and_card", relevance_score=0.9)
    bad_llm = InvalidOutputMock(retry_succeeds=False)
    good_llm = ConfigurableStructuredMock(good_raw)

    class _RoutingMock:
        def __init__(self) -> None:
            self._call = 0

        def with_structured_output(self, model_class, **kwargs):
            self._call += 1
            return bad_llm if self._call == 1 else good_llm

        def invoke(self, messages):
            return good_llm.invoke(messages)

    # Score two results: first uses bad mock path via InvalidOutputMock on first item only
    batch_bad = score_all(
        [sample_search_results[0]],
        llm=InvalidOutputMock(retry_succeeds=False),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
        cap=1,
    )
    assert batch_bad.findings[0].ingest_action == "skip"
    assert batch_bad.findings[0].key_findings == []
    assert batch_bad.findings[0].reasoning.startswith("scoring_failed:")
    assert batch_bad.counters.errors == 1
    assert batch_bad.counters.degraded is True

    batch_mixed = score_all(
        sample_search_results[:2],
        llm=ConfigurableStructuredMock(good_raw),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
        cap=2,
    )
    assert len(batch_mixed.findings) == 2


def test_total_outage_when_all_provider_failures(sample_search_results) -> None:
    llm = TotalOutageMock()
    batch = score_all(
        sample_search_results,
        llm=llm,
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
        cap=3,
    )
    assert batch.total_outage is True
    assert batch.findings == []


def test_run_gate_raises_on_total_outage(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(TotalOutageMock()),
    )
    with pytest.raises(ResearchScoreOutageError):
        run_gate(
            "research.score",
            ResearchScoreInput(
                workspace_path=str(test_workspace),
                results=sample_search_results,
            ),
        )


def test_sanitized_error_never_leaks_key_token(sample_search_results) -> None:
    class _LeakyMock:
        def with_structured_output(self, model_class, **kwargs):
            return self

        def invoke(self, messages):
            raise ValueError("parse failed sk-ant-api03-SECRETKEY123 in payload")

    batch = score_all(
        [sample_search_results[0]],
        llm=_LeakyMock(),
        thresholds=_THRESHOLDS,
        taxonomy_categories=[],
        cap=1,
    )
    reasoning = batch.findings[0].reasoning
    assert "sk-ant-api03-SECRETKEY123" not in reasoning
    assert "scoring_failed:" in reasoning


def test_run_gate_happy_path(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_finding(ingest_action="ref_and_card", relevance_score=0.9)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(ConfigurableStructuredMock(raw)),
    )
    output = run_gate(
        "research.score",
        ResearchScoreInput(
            workspace_path=str(test_workspace),
            results=sample_search_results,
        ),
    )
    assert len(output.findings) == len(sample_search_results)
    assert output.gate.tier == "L3"
    assert output.gate.gate_id == "research.score"
    assert output.retrieval["results_total"] == len(sample_search_results)
    assert output.retrieval["relevance_threshold"] == _THRESHOLDS.relevance_threshold


def test_run_gate_degraded_path(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_finding(ingest_action="ref_and_card", relevance_score=0.9)

    class _MixedMock:
        def __init__(self) -> None:
            self._calls = 0

        def with_structured_output(self, model_class, **kwargs):
            return self

        def invoke(self, messages):
            self._calls += 1
            if self._calls <= 2:
                raise ValueError("invalid structured output")
            return raw

    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(_MixedMock()),
    )
    output = run_gate(
        "research.score",
        ResearchScoreInput(
            workspace_path=str(test_workspace),
            results=sample_search_results[:2],
        ),
    )
    assert output.retrieval["degraded"] is True
    assert output.retrieval["errors"] >= 1
    assert len(output.findings) == 2


def test_run_gate_does_not_mutate_workspace(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    def _snapshot(root: Path) -> dict[str, float]:
        snap: dict[str, float] = {}
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = Path(dirpath) / name
                snap[str(path.relative_to(root))] = path.stat().st_mtime_ns
        return snap

    raw = _raw_finding(ingest_action="ref_only", relevance_score=0.5)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(ConfigurableStructuredMock(raw)),
    )
    before = _snapshot(test_workspace)
    run_gate(
        "research.score",
        ResearchScoreInput(
            workspace_path=str(test_workspace),
            results=sample_search_results[:1],
        ),
    )
    after = _snapshot(test_workspace)
    assert before == after


# ── Plan 04 stubs (registry parity filled in contract tests) ──


@pytest.mark.skip(reason="Plan 04: registry handler CLI + MCP parity (D-13) — see contract tests")
def test_registry_handler_cli_mcp_parity() -> None:  # pragma: no cover
    ...
