"""Unit tests for the graph.status PIPE handler."""
from __future__ import annotations

from pathlib import Path
import json

import pytest

from construct.schemas.card import CardAuthor, Lifecycle
from construct.services.init import DomainInitInput, initialize_workspace
from construct.pipelines.graph_status import graph_status


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


def _write_card(workspace: Path, card_id: str, lifecycle: str = "seed", domain: str = "test-domain") -> None:
    frontmatter = (
        f"---\n"
        f"id: {card_id}\n"
        f"title: {card_id.title()}\n"
        f"epistemic_type: finding\n"
        f"created: 2025-01-01\n"
        f"confidence: 3\n"
        f"source_tier: 3\n"
        f"domains:\n"
        f"  - {domain}\n"
        f"content_categories:\n"
        f"  - test-category\n"
        f"lifecycle: {lifecycle}\n"
        f"---\n"
        f"\n"
        f"## Summary\n\nTest card.\n"
    )
    (workspace / "cards" / f"{card_id}.md").write_text(frontmatter, encoding="utf-8")


def _write_connections(workspace: Path, connections: list[dict]) -> None:
    payload = {
        "version": 1,
        "updated": "2025-01-01",
        "connection_types": ["supports", "contradicts", "extends"],
        "connections": connections,
    }
    (workspace / "connections.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_graph_status_empty_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "empty"
    _init_workspace(ws)
    result = graph_status(ws)
    assert result.success is True
    assert result.data["cards"]["total"] == 0
    assert result.data["connections"]["total"] == 0
    assert result.data["domains"]["total"] == 1


def test_graph_status_with_cards(tmp_path: Path) -> None:
    ws = tmp_path / "with-cards"
    _init_workspace(ws)
    _write_card(ws, "card-a", lifecycle="seed")
    _write_card(ws, "card-b", lifecycle="growing")
    _write_card(ws, "card-c", lifecycle="mature")
    result = graph_status(ws)
    assert result.success is True
    assert result.data["cards"]["total"] == 3
    assert result.data["cards"]["by_lifecycle"]["seed"] == 1
    assert result.data["cards"]["by_lifecycle"]["growing"] == 1
    assert result.data["cards"]["by_lifecycle"]["mature"] == 1


def test_graph_status_with_connections(tmp_path: Path) -> None:
    ws = tmp_path / "with-connections"
    _init_workspace(ws)
    _write_card(ws, "card-a")
    _write_card(ws, "card-b")
    _write_connections(ws, [
        {"from": "card-a", "to": "card-b", "type": "supports", "created": "2025-01-01", "created_by": "construct"},
    ])
    result = graph_status(ws)
    assert result.success is True
    assert result.data["connections"]["total"] == 1
    assert result.data["connections"]["by_type"]["supports"] == 1


def test_graph_status_invalid_path(tmp_path: Path) -> None:
    result = graph_status(tmp_path / "does-not-exist")
    assert result.success is False


def test_graph_status_card_counts_by_domain(tmp_path: Path) -> None:
    ws = tmp_path / "by-domain"
    _init_workspace(ws)
    _write_card(ws, "card-a", domain="test-domain")
    _write_card(ws, "card-b", domain="test-domain")
    result = graph_status(ws)
    assert result.success is True
    assert result.data["cards"]["total"] == 2
    assert result.data["cards"]["by_domain"]["test-domain"] == 2
