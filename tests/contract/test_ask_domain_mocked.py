"""Contract test: full ask.domain pipeline with mocked LLM."""
from __future__ import annotations

from pathlib import Path

import pytest

from construct.llm.ask_domain import build_ask_domain_graph, run_gate
from tests.llm.conftest import MockChatAnthropic, MockSynthesisOutput, create_test_workspace, write_card


class TestAskDomainMocked:
    """Full gate pipeline with mocked LLM — verifies end-to-end contract."""

    def test_full_pipeline_returns_answer_with_citations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full gate pipeline returns structured answer + citations."""
        mock = MockChatAnthropic()
        monkeypatch.setattr(
            "construct.llm.ask_domain.ChatAnthropic",
            lambda **kwargs: mock,
        )

        ws = create_test_workspace(tmp_path / "e2e")
        write_card(ws, "card-a", title="Dark Matter Overview",
                   body="Dark matter is a hypothetical form of matter.", confidence=4)
        write_card(ws, "card-b", title="Cosmic Expansion",
                   body="The universe expands at an accelerating rate.", confidence=3)

        from construct.capabilities.catalog import get_registry

        cap = get_registry().get("ask.domain")
        result = cap.handler(
            workspace_path=str(ws),
            domain_id="test-domain",
            question="What is dark matter?",
            max_cards=10,
        )
        # The handler wraps AskDomainOutput in OperationResult
        assert result.success, f"Gate failed: {result.message}"
        assert result.data is not None
        data = result.data
        assert "answer" in data, f"Missing 'answer' in output: {data.keys()}"
        assert "citations" in data, f"Missing 'citations' in output: {data.keys()}"
        assert "gate" in data, f"Missing 'gate' in output: {data.keys()}"
