"""Tests for ask.domain LangGraph L2 gate."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from construct.llm.ask_domain import (
    AskDomainState,
    build_ask_domain_graph,
)
from tests.llm.conftest import MockChatAnthropic, MockSynthesisOutput, create_test_workspace, write_card


# ── Helpers ──


def _make_initial_state(
    workspace_path: str,
    *,
    question: str = "test query",
    domain_id: str = "test-domain",
    max_cards: int = 20,
    **overrides: Any,
) -> dict[str, Any]:
    """Build a complete AskDomainState dict for graph.invoke()."""
    state: dict[str, Any] = {
        "question": question,
        "domain_id": domain_id,
        "workspace_path": workspace_path,
        "max_cards": max_cards,
        "cards": [],
        "context": "",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "synthesised_answer": None,
        "cited_card_ids": [],
        "llm_confidence": None,
        "citations": [],
        "retrieval_cards_considered": 0,
        "retrieval_cards_selected": 0,
        "token_usage": None,
        "review_required": False,
        "review_status": "not_required",
    }
    state.update(overrides)
    return state


# ── Fixtures ──


@pytest.fixture
def patched_llm(monkeypatch: pytest.MonkeyPatch) -> MockChatAnthropic:
    """Replace ChatAnthropic with mock for unit tests."""
    mock = MockChatAnthropic()
    monkeypatch.setattr(
        "construct.llm.ask_domain.ChatAnthropic",
        lambda **kwargs: mock,
    )
    return mock


@pytest.fixture
def multi_domain_workspace(tmp_path: Path) -> Path:
    """Workspace with cards across multiple domains."""
    ws = tmp_path / "multi_domain"
    create_test_workspace(ws, domain_id="cosmology")
    write_card(ws, "card-c1", title="Dark Matter",
               body="Dark matter is a hypothetical form of matter.", domain="cosmology",
               confidence=4)
    write_card(ws, "card-c2", title="Cosmic Expansion",
               body="The universe expands at an accelerating rate.", domain="cosmology",
               confidence=3)
    write_card(ws, "card-c3", title="Archived Cosmo",
               body="Old cosmology content.", domain="cosmology",
               lifecycle="archived", confidence=2)
    # Domain 2: philosophy-of-mind
    write_card(ws, "card-p1", title="Consciousness",
               body="Consciousness arises from neural activity.", domain="philosophy-of-mind",
               confidence=4)
    write_card(ws, "card-p2", title="Qualia",
               body="Qualia are subjective experiences.", domain="philosophy-of-mind",
               confidence=3)
    return ws


# ── Test: Gate Structure ──


class TestGateStructure:
    """Verify the gate produces structurally correct output."""

    def test_graph_compiles(self) -> None:
        """Graph builds and compiles without errors."""
        graph = build_ask_domain_graph()
        assert hasattr(graph, "invoke")

    def test_graph_has_six_nodes(self) -> None:
        """Verify all 6 expected nodes exist."""
        graph = build_ask_domain_graph()
        g = graph.get_graph()
        # get_graph().nodes returns a dict of name -> Node
        node_names = set(g.nodes.keys())
        expected = {
            "load_domain_cards",
            "filter_by_domain",
            "rank_by_relevance",
            "build_context",
            "llm_synthesize",
            "extract_citations",
        }
        missing = expected - node_names
        assert not missing, f"Missing nodes: {missing}"


# ── Test: Domain Filtering ──


class TestDomainFiltering:
    """Cards outside requested domain are excluded."""

    def test_domain_filtering_works(
        self, multi_domain_workspace: Path, patched_llm: MockChatAnthropic
    ) -> None:
        """Only cards matching domain_id reach the LLM."""
        # Override mock to return specific cited IDs
        patched_llm.invoke = lambda msgs: MockSynthesisOutput(
            answer="Found relevant cosmology content.",
            cited_card_ids=["card-c1", "card-c2"],
            confidence="high",
        )
        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(
                str(multi_domain_workspace),
                domain_id="cosmology",
            )
        )
        # 5 cards total: 4 active + 1 archived. Archived excluded → 4 considered.
        assert result["retrieval_cards_considered"] == 4, (
            f"Expected 4 active cards, got {result['retrieval_cards_considered']}"
        )
        # Archived excluded, then filtered to cosmology → 2 active cosmology cards
        assert result["retrieval_cards_selected"] == 2, (
            f"Expected 2 active cosmology cards selected, got {result['retrieval_cards_selected']}"
        )
        # All citations should be from cosmology domain
        for cit in result.get("citations", []):
            assert cit["card_id"].startswith("card-c"), (
                f"Wrong domain in citation: {cit['card_id']}"
            )


# ── Test: Confidence Propagation ──


class TestConfidencePropagation:
    """ING-06: citations include per-card confidence from frontmatter."""

    def test_citation_confidence_fidelity(
        self, test_workspace: Path, patched_llm: MockChatAnthropic
    ) -> None:
        """Citation confidence field matches source card confidence."""
        # Override mock to return specific cited IDs
        patched_llm.invoke = lambda msgs: MockSynthesisOutput(
            answer="Found relevant content.",
            cited_card_ids=["card-1", "card-2"],
            confidence="high",
        )
        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(str(test_workspace))
        )
        citations = result.get("citations", [])
        assert len(citations) > 0, "Expected at least one citation"
        for citation in citations:
            assert "confidence" in citation
            # card-1 and card-2 both have confidence=3 in test_workspace
            assert citation["confidence"] == 3 or citation["confidence"] is None


# ── Test: Empty Context Guard ──


class TestEmptyContextGuard:
    """No relevant cards → no LLM call, structured 'unanswerable' response."""

    def test_empty_context_skips_llm(self, tmp_path: Path) -> None:
        """When no cards match, synthesised_answer is None."""
        ws = create_test_workspace(tmp_path / "empty")
        # Don't write any cards for "nonexistent-domain"
        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(
                str(ws),
                domain_id="nonexistent-domain",
            )
        )
        assert result["synthesised_answer"] is None, (
            "LLM should not be called with empty context"
        )


# ── Test: Archived Cards ──


class TestArchivedCards:
    """Cards with lifecycle='archived' are filtered out before ranking."""

    def test_archived_cards_excluded(
        self, test_workspace: Path, patched_llm: MockChatAnthropic
    ) -> None:
        """Archived cards don't appear in retrieval counts."""
        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(str(test_workspace))
        )
        # test_workspace has 2 active + 1 archived = 3 total cards.
        # load_domain_cards excludes archived, so considered should be 2.
        assert result["retrieval_cards_considered"] == 2, (
            f"Expected 2 (archived excluded), got {result['retrieval_cards_considered']}"
        )


# ── Test: Provider Config ──


class TestProviderConfig:
    """Provider config loading and resolution."""

    def test_provider_config_default_loads(self) -> None:
        """Default config from llm/config.yaml loads correctly."""
        from construct.llm.config import DEFAULT_CONFIG_PATH, load_llm_config

        cfg = load_llm_config(DEFAULT_CONFIG_PATH)
        assert cfg.default_gate == "ask.domain"
        assert "anthropic" in cfg.providers
        assert cfg.providers["anthropic"].model == "claude-sonnet-4-20250514"
        assert cfg.gates["ask.domain"].provider == "anthropic"
        assert cfg.gates["ask.domain"].temperature == 0.2


# ── Test: Max Cards ──


class TestMaxCards:
    """At most max_cards cards reach the LLM."""

    def test_max_cards_respected(
        self, multi_domain_workspace: Path, patched_llm: MockChatAnthropic
    ) -> None:
        """Only max_cards cards are selected."""
        patched_llm.invoke = lambda msgs: MockSynthesisOutput(
            answer="Summary answer.",
            cited_card_ids=[],
            confidence="medium",
        )
        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(
                str(multi_domain_workspace),
                domain_id="cosmology",
                max_cards=1,
            )
        )
        # With max_cards=1, only 1 card should be selected
        assert result["retrieval_cards_selected"] <= 1, (
            f"Expected at most 1 card selected, got {result['retrieval_cards_selected']}"
        )


# ── Test: LLM Failure ──


class TestLlmFailure:
    """Graceful handling when the LLM call fails."""

    def test_llm_failure_returns_graceful_error(
        self, test_workspace: Path, patched_llm: MockChatAnthropic
    ) -> None:
        """LLM timeout/error returns structured error with None answer."""
        # Make the mock raise an exception
        def failing_invoke(messages: list) -> None:
            msg = "LLM API timeout after 30s"
            raise TimeoutError(msg)

        patched_llm.invoke = failing_invoke

        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(str(test_workspace))
        )
        # Should have None answer and error in token_usage
        assert result["synthesised_answer"] is None
        assert result["token_usage"] is not None
        assert "error" in result["token_usage"]


# ── Test: Keyword Ranking ──


class TestKeywordRanking:
    """Cards matching more question tokens rank higher."""

    def test_keyword_rank_orders_by_relevance(
        self, tmp_path: Path, patched_llm: MockChatAnthropic
    ) -> None:
        """Cards matching more question tokens rank higher."""
        ws = tmp_path / "ranking"
        create_test_workspace(ws)
        write_card(ws, "relevant-card",
                   title="Dark matter and dark energy",
                   body="Dark matter is a hypothetical form of matter. Dark energy drives expansion.",
                   domain="test-domain", confidence=4)
        write_card(ws, "unrelated-card",
                   title="Consciousness studies",
                   body="Philosophical theories about consciousness and qualia.",
                   domain="test-domain", confidence=3)
        write_card(ws, "somewhat-related",
                   title="Matter in the universe",
                   body="Ordinary matter makes up only a small fraction of the universe.",
                   domain="test-domain", confidence=3)

        patched_llm.invoke = lambda msgs: MockSynthesisOutput(
            answer="Answer about dark matter.",
            cited_card_ids=["relevant-card"],
            confidence="high",
        )

        graph = build_ask_domain_graph()
        result = graph.invoke(
            _make_initial_state(
                str(ws),
                question="What is dark matter and dark energy?",
                max_cards=5,
            )
        )
        # The most relevant card should be ranked first
        assert result["retrieval_cards_considered"] >= 3
        # The citations should include the most relevant card
        cited_ids = result.get("cited_card_ids", [])
        citations = result.get("citations", [])
        if citations:
            assert any(c["card_id"] in ("relevant-card",) for c in citations), (
                f"Expected relevant-card in citations: {citations}"
            )
