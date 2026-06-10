"""Unit tests for the knowledge service layer — card and connection operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import json

from construct.schemas.card import CardAuthor, Lifecycle
from construct.schemas.workspace import ConnectionAuthor, ConnectionType
from construct.services.init import DomainInitInput, initialize_workspace
from construct.services.knowledge import (
    OperationResult,
    add_connection,
    archive_card,
    create_card,
    edit_card,
    list_connections,
    remove_connection,
    route_source_to_domain,
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


def _create_two_cards(workspace: Path) -> None:
    """Create card-a and card-b for connection tests."""
    create_card(workspace, _sample_card_data(id="card-a", title="Card A"))
    create_card(workspace, _sample_card_data(id="card-b", title="Card B"))


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


@pytest.fixture
def workspace_with_cards(init_workspace: Path) -> Path:
    _create_two_cards(init_workspace)
    return init_workspace


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


# ===================================================================
# Connection Add Tests
# ===================================================================


class TestConnectionAdd:
    def test_add_connection_valid(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards

        result = add_connection(
            workspace,
            "card-a",
            "card-b",
            ConnectionType.supports,
            note="A supports B",
        )

        assert result.success is True
        # Verify in connections.json
        connections = json.loads((workspace / "connections.json").read_text(encoding="utf-8"))
        conns = connections["connections"]
        assert any(c["from"] == "card-a" and c["to"] == "card-b" and c["type"] == "supports" for c in conns)

    def test_add_connection_duplicate(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        result = add_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        assert result.success is True
        assert "already exists" in result.message.lower()

    def test_add_connection_orphan_prevention(self, init_workspace: Path) -> None:
        result = add_connection(
            init_workspace,
            "existing-card",
            "non-existent-card",
            ConnectionType.supports,
        )

        assert result.success is False
        assert "not found" in result.message.lower() or "exist" in result.message.lower()

    def test_add_connection_invalid_type(self, workspace_with_cards: Path) -> None:
        result = add_connection(
            workspace_with_cards,
            "card-a",
            "card-b",
            "invalid-type",  # type: ignore[arg-type]
        )

        assert result.success is False

    def test_add_connection_event_logged(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        before = _count_events(workspace)

        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        assert _count_events(workspace) == before + 1


# ===================================================================
# Connection Remove Tests
# ===================================================================


class TestConnectionRemove:
    def test_remove_connection(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        result = remove_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        assert result.success is True
        connections = json.loads((workspace / "connections.json").read_text(encoding="utf-8"))
        conns = connections["connections"]
        assert not any(c["from"] == "card-a" and c["to"] == "card-b" and c["type"] == "supports" for c in conns)

    def test_remove_nonexistent_connection(self, workspace_with_cards: Path) -> None:
        result = remove_connection(
            workspace_with_cards,
            "card-a",
            "card-b",
            ConnectionType.supports,
        )

        assert result.success is False
        assert "not found" in result.message


# ===================================================================
# Connection List Tests
# ===================================================================


class TestConnectionList:
    def test_list_connections(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        result = list_connections(workspace)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1

    def test_list_connections_filter_by_card(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        # Create a third card to have a connection not involving card-a
        create_card(workspace, _sample_card_data(id="card-c", title="Card C"))
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)
        add_connection(workspace, "card-c", "card-b", ConnectionType.parallels)

        result = list_connections(workspace, card_id="card-c")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["from"] == "card-c"

    def test_list_connections_exclude_archived(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)
        # Archive card-a
        archive_card(workspace, "card-a")

        result = list_connections(workspace, include_archived=False)

        assert result.success is True
        if result.data is not None:
            # Either no connections or none involving archived cards
            for conn in result.data:
                assert conn["from"] != "card-a"
                assert conn["to"] != "card-a"

    def test_list_connections_include_archived(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)
        archive_card(workspace, "card-a")

        result = list_connections(workspace, include_archived=True)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) >= 1


# ===================================================================
# Source Routing Tests
# ===================================================================


class TestSourceRouting:
    def test_route_source_to_domain(self, workspace_path: Path) -> None:
        """Source file in inbox gets routed to matching domain via content_categories."""
        from construct.services.init import DomainInitInput, initialize_workspace

        domain = DomainInitInput(
            domain_id="physics",
            display_name="Physics",
            scope="Test scope for physics",
            taxonomy_seeds=["quantum"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["quantum mechanics"],
        )
        initialize_workspace(workspace_path, domain)

        # Create inbox source file
        inbox_dir = workspace_path / "inbox"
        inbox_dir.mkdir(exist_ok=True)
        source_file = inbox_dir / "quantum-entanglement-paper.pdf"
        source_file.write_text("dummy content")

        result = route_source_to_domain(workspace_path, source_file)
        assert result.success, f"Routing failed: {result.message} {result.errors}"
        assert result.data is not None
        assert result.data["domain"] == "physics"

        # Verify file was routed
        assert (workspace_path / "physics" / "inbox" / "raw" / "quantum-entanglement-paper.pdf").exists()

        # Verify ref was created
        refs = list((workspace_path / "refs").glob("*.json"))
        assert len(refs) >= 1

    def test_route_source_no_domain_match(self, workspace_path: Path) -> None:
        """Source with no domain match returns suggestion to create domain."""
        from construct.services.init import DomainInitInput, initialize_workspace

        domain = DomainInitInput(
            domain_id="physics",
            display_name="Physics",
            scope="Test scope for physics",
            taxonomy_seeds=["quantum"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["quantum mechanics"],
        )
        initialize_workspace(workspace_path, domain)

        inbox_dir = workspace_path / "inbox"
        inbox_dir.mkdir(exist_ok=True)
        source_file = inbox_dir / "xyz-nonmatching-file.pdf"
        source_file.write_text("dummy content")

        result = route_source_to_domain(workspace_path, source_file)
        assert not result.success  # Should fail — no matching domain
        # Should suggest domain creation
        assert any("domain" in e.suggestion.lower() for e in result.errors)

    def test_route_source_with_domain_hint(self, workspace_path: Path) -> None:
        """Domain hint overrides auto-detection even when filename doesn't match."""
        from construct.services.init import DomainInitInput, initialize_workspace

        initialize_workspace(
            workspace_path,
            DomainInitInput(
                domain_id="physics",
                display_name="Physics",
                scope="Test scope for physics",
                taxonomy_seeds=["quantum"],
                source_priorities=["peer-reviewed papers"],
                research_seeds=["quantum mechanics"],
            ),
        )

        inbox_dir = workspace_path / "inbox"
        inbox_dir.mkdir(exist_ok=True)
        source_file = inbox_dir / "cooking-recipes.pdf"
        source_file.write_text("dummy content")

        result = route_source_to_domain(workspace_path, source_file, domain_hint="physics")
        assert result.success, f"Routing with hint failed: {result.message}"
        assert result.data is not None
        assert result.data["domain"] == "physics"

        # File should be in physics/inbox/raw/ despite filename not matching
        assert (workspace_path / "physics" / "inbox" / "raw" / "cooking-recipes.pdf").exists()

    def test_route_source_logs_event(self, workspace_path: Path) -> None:
        """Source routing logs ingest_paper event."""
        from construct.services.init import DomainInitInput, initialize_workspace

        initialize_workspace(
            workspace_path,
            DomainInitInput(
                domain_id="physics",
                display_name="Physics",
                scope="Test scope for physics",
                taxonomy_seeds=["quantum"],
                source_priorities=["peer-reviewed papers"],
                research_seeds=["quantum mechanics"],
            ),
        )

        inbox_dir = workspace_path / "inbox"
        inbox_dir.mkdir(exist_ok=True)
        source_file = inbox_dir / "physics-paper.pdf"
        source_file.write_text("dummy content")

        result = route_source_to_domain(workspace_path, source_file)
        assert result.success, f"Routing failed: {result.message} {result.errors}"
        event_log = workspace_path / "log" / "events.jsonl"
        assert event_log.exists()
        assert any("ingest_paper" in line for line in event_log.read_text().splitlines())

    def test_route_source_invalid_domain_hint(self, workspace_path: Path) -> None:
        """Invalid domain hint returns structured error."""
        from construct.services.init import DomainInitInput, initialize_workspace

        initialize_workspace(
            workspace_path,
            DomainInitInput(
                domain_id="physics",
                display_name="Physics",
                scope="Test scope",
                taxonomy_seeds=["quantum"],
                source_priorities=["peer-reviewed papers"],
                research_seeds=["quantum mechanics"],
            ),
        )

        inbox_dir = workspace_path / "inbox"
        inbox_dir.mkdir(exist_ok=True)
        source_file = inbox_dir / "test-article.pdf"
        source_file.write_text("dummy")

        result = route_source_to_domain(workspace_path, source_file, domain_hint="nonexistent-domain")
        assert not result.success
        assert any("domain_hint" in e.field for e in result.errors)
