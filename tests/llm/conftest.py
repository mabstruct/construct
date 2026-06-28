"""Shared fixtures for ask.domain and research.score tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from construct.schemas.card import CardAuthor, Lifecycle
from construct.search.models import SearchResult
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
            "construct.llm.factory.build_chat_model",
            lambda cfg, *, temperature=0.2: MockChatAnthropic(),
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


# ── research.score offline mocks (extend the canned-return seam above) ──


class ConfigurableStructuredMock:
    """Structured-output mock whose ``.invoke()`` returns a caller-supplied object.

    The caller passes the exact ``ScoredFinding``-shaped object the LLM should
    "produce" (built by the test), so per-result scoring is deterministic and
    offline. ``last_messages`` captures the prompt for D-11 taxonomy assertions.

    Usage in tests::

        raw = ScoredFinding(...)              # the test owns the schema shape
        llm = ConfigurableStructuredMock(raw)
        finding = score_one(result, llm=llm, thresholds=..., taxonomy_categories=...)
        assert "my-category" in llm.prompt_text()
    """

    def __init__(self, output: Any) -> None:
        self._output = output
        self.output_model: Any = None
        self.last_messages: list[Any] = []
        self.invoke_count = 0

    def with_structured_output(self, model_class: Any, **kwargs: Any) -> "ConfigurableStructuredMock":
        self.output_model = model_class
        return self

    def invoke(self, messages: list) -> Any:
        self.invoke_count += 1
        self.last_messages = messages
        return self._output

    def prompt_text(self) -> str:
        """Flatten captured prompt messages into a single searchable string."""
        parts: list[str] = []
        for msg in self.last_messages:
            content = getattr(msg, "content", msg)
            parts.append(content if isinstance(content, str) else str(content))
        return "\n".join(parts)


class InvalidOutputMock:
    """Mock that raises a parse/validation error on the FIRST ``.invoke()``.

    Exercises D-08 (retry-once-then-skip) in Plan 03. The retry behaviour is
    configurable: by default the retry also fails, but a ``retry_output`` may be
    supplied so the second call succeeds.
    """

    def __init__(self, *, retry_succeeds: bool = False, retry_output: Any = None) -> None:
        self._retry_succeeds = retry_succeeds
        self._retry_output = retry_output
        self.output_model: Any = None
        self.invoke_count = 0

    def with_structured_output(self, model_class: Any, **kwargs: Any) -> "InvalidOutputMock":
        self.output_model = model_class
        return self

    def invoke(self, messages: list) -> Any:
        self.invoke_count += 1
        if self.invoke_count == 1:
            raise ValueError("invalid structured output: failed to parse JSON schema response")
        if self._retry_succeeds:
            return self._retry_output
        raise ValueError("invalid structured output: retry also failed to parse")


class TotalOutageMock:
    """Mock whose ``.invoke()`` ALWAYS raises a provider/auth-style error.

    Exercises D-09 (total provider outage → gate-level degraded error, not an
    all-skip "success") in Plan 03. The message intentionally contains
    "authentication" so the runner can classify it as a provider-level cause.
    """

    def __init__(self) -> None:
        self.output_model: Any = None
        self.invoke_count = 0

    def with_structured_output(self, model_class: Any, **kwargs: Any) -> "TotalOutageMock":
        self.output_model = model_class
        return self

    def invoke(self, messages: list) -> Any:
        self.invoke_count += 1
        raise RuntimeError("provider error: authentication failed (401)")


def make_build_chat_model(mock: Any):
    """Return a ``build_chat_model`` replacement compatible with the Plan 01 seam.

    Mirrors ``factory.build_chat_model(cfg, *, temperature=...)`` so tests can
    monkeypatch ``construct.llm.factory.build_chat_model`` with a closure that
    returns the supplied mock chat model.
    """

    def _build(cfg: Any, *, temperature: float = 0.2) -> Any:
        return mock

    return _build


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


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Phase-8 normalized SearchResult fixtures (NOT the spec §6.1 draft schema).

    Uses the authoritative implemented contract: title, url, snippet,
    source_tier, score, provider_specific, source_domain.
    """
    return [
        SearchResult(
            title="Loop Quantum Gravity and the Big Bounce",
            url="https://arxiv.org/abs/2401.00001",
            snippet="A peer-reviewed treatment of the quantum bounce in LQG cosmology.",
            source_tier=2,
            score=0.91,
            provider_specific={"published_date": "2024-01-02"},
            source_domain="arxiv.org",
        ),
        SearchResult(
            title="A blog take on quantum gravity",
            url="https://example-blog.test/quantum-gravity",
            snippet="An informal opinion piece with limited sourcing.",
            source_tier=4,
            score=0.42,
            provider_specific={},
            source_domain="example-blog.test",
        ),
        SearchResult(
            title="Unrelated marketing page",
            url="https://shop.test/widgets",
            snippet="Buy widgets now, lowest prices guaranteed.",
            source_tier=5,
            score=0.12,
            provider_specific={},
            source_domain="shop.test",
        ),
    ]
