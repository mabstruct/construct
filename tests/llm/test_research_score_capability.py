"""Capability registry tests for research.score (Phase 9 Plan 04)."""
from __future__ import annotations

import pytest

from construct.capabilities.catalog import get_registry
from construct.llm.research_score import ScoredFinding
from tests.llm.conftest import ConfigurableStructuredMock, TotalOutageMock, make_build_chat_model


def _raw_finding() -> ScoredFinding:
    return ScoredFinding(
        url="https://arxiv.org/abs/2401.00001",
        title="Loop Quantum Gravity",
        relevance_score=0.9,
        source_tier=2,
        ingest_action="ref_and_card",
        key_findings=["a"],
        content_categories=["loop-quantum-gravity"],
        reasoning="High relevance peer-reviewed source.",
    )


def test_research_score_registered_in_catalog() -> None:
    cap = get_registry().get("research.score")
    assert cap.id == "research.score"
    assert cap.cli_name == "research.score"
    assert cap.mcp_tool_name == "construct_research_score"


def test_shim_happy_path(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(ConfigurableStructuredMock(_raw_finding())),
    )
    cap = get_registry().get("research.score")
    result = cap.handler(
        workspace_path=str(test_workspace),
        results=[r.model_dump(mode="json") for r in sample_search_results[:1]],
    )
    assert result.success is True
    assert result.data is not None
    assert len(result.data["findings"]) == 1


def test_shim_total_outage_returns_failure(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(TotalOutageMock()),
    )
    cap = get_registry().get("research.score")
    result = cap.handler(
        workspace_path=str(test_workspace),
        results=[r.model_dump(mode="json") for r in sample_search_results],
    )
    assert result.success is False
    assert result.data.get("total_outage") is True
