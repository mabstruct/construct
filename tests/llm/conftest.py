"""Shared fixtures for ask.domain tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from construct.schemas.card import CardAuthor, Lifecycle
from construct.services.init import DomainInitInput, initialize_workspace


# ── Mock ChatAnthropic for unit tests ──


class MockSynthesisOutput:
    """Mimics the Pydantic SynthesisOutput returned by with_structured_output."""
    def __init__(self, answer: str, cited_card_ids: list[str], confidence: str):
        self.answer = answer
        self.cited_card_ids = cited_card_ids
        self.confidence = confidence


class MockChatAnthropic:
    """Simplified mock returning fixed structured output.

    Usage in tests:
        monkeypatch.setattr(
            "construct.llm.ask_domain.ChatAnthropic",
            lambda **kwargs: MockChatAnthropic(),
        )
    """
    def __init__(self, **kwargs: Any) -> None:
        self.model = kwargs.get("model", "claude-sonnet-4-20250514")
        self.temperature = kwargs.get("temperature", 0.2)

    def with_structured_output(self, model_class: Any, **kwargs: Any) -> "MockChatAnthropic":
        self._output_model = model_class
        return self

    def invoke(self, messages: list) -> MockSynthesisOutput:
        """Return a canned SynthesisOutput. Tests override via monkeypatch."""
        return MockSynthesisOutput(
            answer="Mock answer based on provided card context.",
            cited_card_ids=["card-1", "card-2"],
            confidence="high",
        )


# ── Workspace creation helpers ──


def create_test_workspace(path: Path, domain_id: str = "test-domain") -> Path:
    """Initialize a minimal CONSTRUCT workspace for testing."""
    domain = DomainInitInput(
        domain_id=domain_id,
        display_name=domain_id.replace("-", " ").title(),
        scope=f"Test domain for {domain_id}.",
        taxonomy_seeds=["test-category"],
        source_priorities=["peer-reviewed papers"],
        research_seeds=["test research"],
    )
    initialize_workspace(path, domain)
    return path


def write_card(workspace: Path, card_id: str, *,
               title: str | None = None,
               domain: str = "test-domain",
               body: str = "Test card body content for testing.",
               confidence: int = 3,
               source_tier: int = 3,
               lifecycle: str = "seed",
               content_categories: list[str] | None = None) -> None:
    """Write a card fixture to the workspace."""
    categories = content_categories or ["test-category"]
    display_title = title or card_id.title()
    frontmatter = (
        f"---\n"
        f"id: {card_id}\n"
        f"title: {display_title}\n"
        f"epistemic_type: finding\n"
        f"created: 2025-01-01\n"
        f"confidence: {confidence}\n"
        f"source_tier: {source_tier}\n"
        f"domains:\n"
        f"  - {domain}\n"
        f"content_categories:\n"
    )
    for cat in categories:
        frontmatter += f"  - {cat}\n"
    frontmatter += (
        f"lifecycle: {lifecycle}\n"
        f"---\n\n"
        f"## Summary\n\n{body}\n"
    )
    (workspace / "cards" / f"{card_id}.md").write_text(frontmatter, encoding="utf-8")


# ── Pytest fixtures ──


@pytest.fixture
def mock_llm() -> MockChatAnthropic:
    """Returns a MockChatAnthropic for tests that don't need custom output."""
    return MockChatAnthropic()


@pytest.fixture
def test_workspace(tmp_path: Path) -> Path:
    """Create a fresh test workspace with sample cards."""
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    write_card(ws, "card-1", title="Test Card One", body="Content about testing methods and approaches.")
    write_card(ws, "card-2", title="Test Card Two", body="Different content covering test validation patterns.")
    write_card(ws, "card-3", title="Archived Card", body="Old content.", lifecycle="archived")
    return ws
