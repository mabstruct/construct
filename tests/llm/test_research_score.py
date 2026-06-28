"""Tests for the research.score L3 gate (Phase 9).

Plan 02 scope (REAL tests here): single-result scoring, the deterministic
governance ceiling-clamp (D-05), the threshold echo (D-06), soft taxonomy
steering (D-11), and the key_findings clamp rule (D-14 / Pitfall 5).

Plan 03/04 scope (skipped stubs below): bounded fan-out, per-item retry +
skip-with-reason (D-08), total-outage promotion (D-09), and registry/CLI/MCP
parity (D-13). They are named here so later waves fill in the bodies.
"""
from __future__ import annotations

import pytest

from construct.llm.research_score import (
    GovernanceThresholds,
    ScoredFinding,
    build_gate_output,
    clamp_action,
    load_governance_thresholds,
    load_taxonomy_categories,
    retrieval_echo,
    score_one,
)
from tests.llm.conftest import ConfigurableStructuredMock


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


# ── Plan 03/04 stubs (fan-out, degraded handling, registry parity) ──


@pytest.mark.skip(reason="Plan 03: bounded fan-out + per-item retry/skip (D-08)")
def test_invalid_output_degrades_to_skip() -> None:  # pragma: no cover
    ...


@pytest.mark.skip(reason="Plan 03: total provider outage → gate-level error (D-09)")
def test_total_outage_is_gate_error() -> None:  # pragma: no cover
    ...


@pytest.mark.skip(reason="Plan 03: full SearchResult[] fan-out via run_gate (D-04)")
def test_scores_results_with_mock_llm() -> None:  # pragma: no cover
    ...


@pytest.mark.skip(reason="Plan 04: registry handler CLI + MCP parity (D-13)")
def test_registry_handler_cli_mcp_parity() -> None:  # pragma: no cover
    ...
