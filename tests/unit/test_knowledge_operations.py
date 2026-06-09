"""Unit tests for the knowledge service layer — card and connection operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from construct.schemas.card import CardAuthor, Lifecycle
from construct.services.init import DomainInitInput, initialize_workspace
from construct.services.knowledge import (
    OperationResult,
    archive_card,
    create_card,
    edit_card,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_card_data(**overrides: Any) -> dict:
    data: dict = {
        "id": "test-card",
        "title": "Test Card",
        "epistemic_type": "finding",
        "domains": ["test-domain"],
        "content_categories": ["test-category"],
        "confidence": 3,
        "source_tier": 3,
    }
    data.update(overrides)
    return data


def _init_workspace(path: Path) -> None:
    domain = DomainInitInput(
        domain_id="test-domain",
        display_name="Test Domain",
        scope="A test domain for unit tests.",
        taxonomy_seeds=["test-category"],
        source_priorities=["peer-reviewed papers"],
        research_seeds=["test research"],
    )
    initialize_workspace(path, domain)


def _card_exists(workspace: Path, card_id: str) -> bool:
    return (workspace / "cards" / f"{card_id}.md").exists()


def _read_card_raw(workspace: Path, card_id: str) -> dict:
    from ruamel.yaml import YAML

    path = workspace / "cards" / f"{card_id}.md"
    text = path.read_text(encoding="utf-8")
    parts = text.split("\n---\n", 1)
    yaml = YAML(typ="safe")
    data = yaml.load(parts[0][4:]) or {}
    return data


def _count_events(workspace: Path) -> int:
    events_path = workspace / "log" / "events.jsonl"
    if not events_path.exists():
        return 0
    return len(events_path.read_text(encoding="utf-8").strip().splitlines())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def init_workspace(workspace_path: Path) -> Path:
    _init_workspace(workspace_path)
    return workspace_path


# ===================================================================
# Card Create Tests
# ===================================================================


class TestCardCreate:
    def test_create_card_minimal(self, init_workspace: Path) -> None:
        workspace = init_workspace
        data = _sample_card_data()

        result = create_card(workspace, data)

        assert result.success is True
        assert result.data is not None
        assert result.data["id"] == "test-card"
        assert _card_exists(workspace, "test-card")

        # Verify event logged
        assert _count_events(workspace) == 2  # workspace_init + create_card

    def test_create_card_invalid_confidence(self, init_workspace: Path) -> None:
        data = _sample_card_data(confidence=7)

        result = create_card(init_workspace, data)

        assert result.success is False
        assert any("confidence" in e.reason.lower() or "confidence" in err.field for err in result.errors for e in [err])

    def test_create_card_missing_domain(self, init_workspace: Path) -> None:
        data = _sample_card_data(domains=[])

        result = create_card(init_workspace, data)

        assert result.success is False
        assert any("domain" in e.reason.lower() or "domain" in err.field for err in result.errors for e in [err])

    def test_create_card_preserves_connects_to_empty(self, init_workspace: Path) -> None:
        data = _sample_card_data()

        result = create_card(init_workspace, data)

        assert result.success is True
        # Verify connects_to is empty via parsed card model
        from construct.schemas.card import parse_card_markdown

        markdown = (init_workspace / "cards" / "test-card.md").read_text(encoding="utf-8")
        card, _ = parse_card_markdown(markdown)
        assert card.connects_to == []

    def test_create_card_generates_id_from_title(self, init_workspace: Path) -> None:
        data = _sample_card_data(id="", title="My Awesome Finding")
        # Remove id from the data
        del data["id"]

        result = create_card(init_workspace, data)

        assert result.success is True
        assert result.data["id"] == "my-awesome-finding"
        assert _card_exists(init_workspace, "my-awesome-finding")


# ===================================================================
# Card Edit Tests
# ===================================================================


class TestCardEdit:
    def test_edit_card_title(self, init_workspace: Path) -> None:
        workspace = init_workspace
        create_card(workspace, _sample_card_data())

        result = edit_card(workspace, "test-card", {"title": "Updated Title"})

        assert result.success is True
        raw = _read_card_raw(workspace, "test-card")
        assert raw["title"] == "Updated Title"

    def test_edit_card_preserves_unchanged_fields(self, init_workspace: Path) -> None:
        workspace = init_workspace
        # Create with specific confidence & source_tier
        create_card(workspace, _sample_card_data(confidence=4, source_tier=2))

        # Edit only title
        result = edit_card(workspace, "test-card", {"title": "New Title"})

        assert result.success is True
        raw = _read_card_raw(workspace, "test-card")
        assert raw["title"] == "New Title"
        assert raw["confidence"] == 4
        assert raw["source_tier"] == 2

    def test_edit_card_nonexistent(self, init_workspace: Path) -> None:
        result = edit_card(init_workspace, "nonexistent-card", {"title": "Nope"})

        assert result.success is False


# ===================================================================
# Card Archive Tests
# ===================================================================


class TestCardArchive:
    def test_archive_card(self, init_workspace: Path) -> None:
        workspace = init_workspace
        create_card(workspace, _sample_card_data())

        result = archive_card(workspace, "test-card")

        assert result.success is True
        raw = _read_card_raw(workspace, "test-card")
        assert raw["lifecycle"] == Lifecycle.archived.value

    def test_archive_card_preserves_connects_to(self, init_workspace: Path) -> None:
        workspace = init_workspace
        create_card(
            workspace,
            _sample_card_data(
                connects_to=[{"target": "another-card", "relation": "extends"}],
            ),
        )

        result = archive_card(workspace, "test-card")

        assert result.success is True
        raw = _read_card_raw(workspace, "test-card")
        assert raw["lifecycle"] == Lifecycle.archived.value
        assert len(raw["connects_to"]) == 1
        assert raw["connects_to"][0]["target"] == "another-card"
