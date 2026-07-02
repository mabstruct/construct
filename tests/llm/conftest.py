"""Shared fixtures for ask.domain and research.score tests."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from langgraph.checkpoint.sqlite import SqliteSaver

from construct.llm.research_score import (
    GateMetadata,
    ResearchScoreGateOutput,
    ScoredFinding,
)
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
               content_categories: list[str] | None = None,
               created: str = "2025-01-01",
               last_verified: str | None = None) -> None:
    """Write a card fixture to the workspace.

    ``created`` and ``last_verified`` control the recency anchors decay-scan and
    orphan-scan compare against governance thresholds (Phase 11). Both default to
    the pre-existing behaviour: ``created`` stays ``2025-01-01`` and the
    ``last_verified:`` frontmatter line is omitted unless a value is supplied, so
    callers that do not pass them produce byte-identical card output.
    """
    categories = content_categories or ["test-category"]
    display_title = title or card_id.title()
    frontmatter = (
        f"---\n"
        f"id: {card_id}\n"
        f"title: {display_title}\n"
        f"epistemic_type: finding\n"
        f"created: {created}\n"
    )
    if last_verified is not None:
        frontmatter += f"last_verified: {last_verified}\n"
    frontmatter += (
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


# ── Phase 11: curation.run decay/orphan determinism fixture (Wave 0) ──


# The full closed ``ConnectionType`` enum (schemas/workspace.py:29-39). The
# canonical edge list lives at ``connections.json`` at the WORKSPACE ROOT — the
# path ``WorkspaceLoader.load_connections`` reads — not under a ``connections/``
# subdirectory.
_CONNECTION_TYPES = [
    "supports", "contradicts", "extends", "parallels", "requires",
    "enables", "challenges", "inspires", "gap-for",
]


@pytest.fixture
def curation_workspace(tmp_path: Path) -> Path:
    """Deterministic workspace for decay/orphan threshold testing (Phase 11).

    Builds four cards whose recency anchors are computed RELATIVE to
    ``date.today()`` so the fixture never drifts inside the governance windows
    (default decay window 28d, orphan tolerance 7d):

    - ``fresh-card``           — created yesterday → NOT a decay candidate, NOT an orphan.
    - ``stale-orphan-card``    — created 400d ago, degree 0 → BOTH a decay AND an orphan candidate.
    - ``stale-connected-card`` — created 400d ago, degree 1 → a decay candidate but NOT an orphan.
    - ``stale-archived-card``  — created 400d ago, ``lifecycle=archived`` → EXCLUDED from both scans.

    A single ``ConnectionRecord`` links ``stale-connected-card`` (``from``) to
    ``fresh-card`` (``to``); degree counting must therefore credit BOTH endpoints
    (Pitfall 3) so ``fresh-card`` is non-orphan by virtue of being a target.
    """
    ws = tmp_path / "curation-workspace"
    create_test_workspace(ws)

    today = date.today()
    fresh = (today - timedelta(days=1)).isoformat()
    stale = (today - timedelta(days=400)).isoformat()

    write_card(ws, "fresh-card", title="Fresh Card",
               body="Recently created card; not a decay or orphan candidate.", created=fresh)
    write_card(ws, "stale-orphan-card", title="Stale Orphan Card",
               body="Old and unconnected; a decay and orphan candidate.", created=stale)
    write_card(ws, "stale-connected-card", title="Stale Connected Card",
               body="Old but connected; decay-eligible, not an orphan.", created=stale)
    write_card(ws, "stale-archived-card", title="Stale Archived Card",
               body="Old and archived; excluded from both scans.", created=stale,
               lifecycle="archived")

    connections = {
        "version": 1,
        "updated": today.isoformat(),
        "connection_types": list(_CONNECTION_TYPES),
        "connections": [
            {
                "from": "stale-connected-card",
                "to": "fresh-card",
                "type": "supports",
                "created": today.isoformat(),
                "created_by": "curator",
                "note": "links the connected stale card to the fresh card",
            }
        ],
    }
    (ws / "connections.json").write_text(json.dumps(connections, indent=2) + "\n", encoding="utf-8")
    return ws


# ── Phase 10: durable research.run fixtures (Wave 0) ──


@pytest.fixture
def sqlite_checkpointer(tmp_path: Path):
    """Factory that opens ``SqliteSaver`` instances on a SHARED tmp DB file.

    Returns a zero-arg callable ``open_checkpointer() -> (saver, conn, db_path)``.
    Call it twice on the same ``db_path`` to simulate cross-process resume: the
    first instance pauses at the review interrupt, ``conn.close()`` ends that
    "process", and a fresh ``SqliteSaver`` over the same file resumes from the
    persisted checkpoint (mirrors the ``test_workflow_runner`` r1/r2 idiom).

    ``check_same_thread=False`` is required so the saver can be used across the
    threads LangGraph may run nodes on. All opened connections are closed at
    teardown so the tmp file is releasable on every platform.
    """
    db_path = tmp_path / "research-run.sqlite"
    opened: list[sqlite3.Connection] = []

    def _open() -> tuple[SqliteSaver, sqlite3.Connection, Path]:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        opened.append(conn)
        return SqliteSaver(conn), conn, db_path

    yield _open

    for conn in opened:
        try:
            conn.close()
        except Exception:
            pass


def make_scored_findings_batch(
    *,
    gate_id: str = "research.score",
) -> ResearchScoreGateOutput:
    """Build a deterministic ``ResearchScoreGateOutput`` with MIXED ingest actions.

    Produces one finding per ``ingest_action`` band (skip / ref_only /
    ref_and_card) so offline review tests can exercise per-finding approve/reject
    routing, the rejected ledger, and ingest counts without a live LLM. The URLs
    line up with ``sample_search_results`` (arxiv / blog / shop).
    """
    findings = [
        ScoredFinding(
            url="https://arxiv.org/abs/2401.00001",
            title="Loop Quantum Gravity and the Big Bounce",
            relevance_score=0.91,
            source_tier=2,
            ingest_action="ref_and_card",
            key_findings=["Quantum bounce replaces the singularity."],
            content_categories=["test-category"],
            reasoning="High-tier peer-reviewed source directly on topic.",
        ),
        ScoredFinding(
            url="https://example-blog.test/quantum-gravity",
            title="A blog take on quantum gravity",
            relevance_score=0.55,
            source_tier=4,
            ingest_action="ref_only",
            key_findings=["Informal overview, useful as a pointer."],
            content_categories=["test-category"],
            reasoning="Relevant but low-tier; keep a reference only.",
        ),
        ScoredFinding(
            url="https://shop.test/widgets",
            title="Unrelated marketing page",
            relevance_score=0.12,
            source_tier=5,
            ingest_action="skip",
            key_findings=[],
            content_categories=[],
            reasoning="Off-topic commercial page; skip.",
        ),
    ]
    return ResearchScoreGateOutput(
        findings=findings,
        gate=GateMetadata(gate_id=gate_id),
        retrieval={
            "relevance_threshold": 0.5,
            "card_creation_threshold": 0.7,
            "max_papers_per_cycle": 5,
        },
    )


@pytest.fixture
def scored_findings_batch() -> ResearchScoreGateOutput:
    """A mixed-action ``ResearchScoreGateOutput`` for offline review tests."""
    return make_scored_findings_batch()


# ── Phase 12: L3 gate mock seams (Wave 0) ──
#
# Two fixture builders that hand the reusable ``ConfigurableStructuredMock`` a
# ``PromotionDecision``-shaped and a ``ConnectionTypeDecision``-shaped canned
# return. The gate output models live in ``construct.llm.curation_promote`` /
# ``construct.llm.curation_connect`` — created in Plans 02-05 — so they are
# imported lazily INSIDE the factory bodies. This keeps ``conftest`` collectable
# (existing research/curation tests import cleanly) while the curation gate
# modules are absent; only a test that actually *requests* one of these decisions
# goes RED on the missing import. The monkeypatch seam stays
# ``construct.llm.factory.build_chat_model`` (see ``make_build_chat_model``); no
# new mock class is introduced — these are fixture builders over the existing
# ``ConfigurableStructuredMock``.


@pytest.fixture
def promotion_decision_mock():
    """Factory → ``ConfigurableStructuredMock`` seeded with a ``PromotionDecision``.

    ``PromotionDecision`` (spec §6.4, ``extra="forbid"``) is created in Plan 02, so
    it is imported lazily. Callers override the canned verdict::

        llm = promotion_decision_mock(decision="escalate", target_lifecycle=None)
        decision = evaluate_one(card, llm=llm)
    """

    def _make(
        *,
        card_id: str = "card-1",
        decision: str = "promote",
        target_lifecycle: str | None = "growing",
        reasoning: str = "Card is mature enough to advance a lifecycle band.",
        method: str = "llm-judgment",
    ) -> ConfigurableStructuredMock:
        from construct.llm.curation_promote import PromotionDecision

        return ConfigurableStructuredMock(
            PromotionDecision(
                card_id=card_id,
                decision=decision,
                target_lifecycle=target_lifecycle,
                reasoning=reasoning,
                method=method,
            )
        )

    return _make


@pytest.fixture
def connection_type_decision_mock():
    """Factory → ``ConfigurableStructuredMock`` seeded with a ``ConnectionTypeDecision``.

    ``ConnectionTypeDecision`` (Discrepancy 2 — a REQUIRED ``ConnectionType`` enum,
    no ``None``) is created in Plan 02/05, so it is imported lazily. Drives the
    connection-typing L3 gate over a ``bridge_detect`` candidate pair::

        llm = connection_type_decision_mock(connection_type="extends")
        decision = type_one(pair, llm=llm)
    """

    def _make(
        *,
        from_card_id: str = "card-1",
        to_card_id: str = "card-2",
        connection_type: str = "supports",
        reasoning: str = "Card A empirically supports the claim in card B.",
    ) -> ConfigurableStructuredMock:
        from construct.llm.curation_connect import ConnectionTypeDecision

        return ConfigurableStructuredMock(
            ConnectionTypeDecision(
                from_card_id=from_card_id,
                to_card_id=to_card_id,
                connection_type=connection_type,
                reasoning=reasoning,
            )
        )

    return _make


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
