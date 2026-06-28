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


def test_shim_preflight_provider_error_returns_sanitized_failure(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-01: a pre-flight provider/config failure (raised before score_all runs)
    must be translated into OperationResult(success=False) with a sanitized
    message that never echoes raw provider exception text or an API key."""

    _SECRET = "sk-ant-api03-PREFLIGHTSECRET999"

    def _boom(cfg, *, temperature=0.2):
        # Mirrors langchain's "Did not find anthropic_api_key ..." style failure
        # that escapes the gate before any item is scored.
        raise RuntimeError(
            f"GATE_PROVIDER_ERROR: could not build model, key {_SECRET}"
        )

    monkeypatch.setattr("construct.llm.factory.build_chat_model", _boom)

    cap = get_registry().get("research.score")
    result = cap.handler(
        workspace_path=str(test_workspace),
        results=[r.model_dump(mode="json") for r in sample_search_results[:1]],
    )
    assert result.success is False
    assert result.data.get("total_outage") is False
    assert result.data.get("degraded") is True
    # Sanitization: no raw provider text / API key leaks into the message.
    assert _SECRET not in result.message
    assert "GATE_PROVIDER_ERROR" not in result.message


def test_shim_unknown_provider_does_not_traceback(
    test_workspace, sample_search_results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-01: an unknown provider type raised during model construction must
    surface as success=False, not an uncaught traceback on the CLI."""

    def _boom(cfg, *, temperature=0.2):
        raise RuntimeError("GATE_PROVIDER_ERROR: unknown provider type 'bogus'")

    monkeypatch.setattr("construct.llm.factory.build_chat_model", _boom)

    cap = get_registry().get("research.score")
    result = cap.handler(
        workspace_path=str(test_workspace),
        results=[r.model_dump(mode="json") for r in sample_search_results[:1]],
    )
    assert result.success is False
    assert result.message.startswith("research.score failed:")
