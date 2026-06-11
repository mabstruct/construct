"""Tests for L1 structural bridge detection (cross-domain connections)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from construct.pipelines.bridge_detect import _l1_structural
from construct.storage.workspace import WorkspaceLoader


def _write_connections(workspace: Path, connections: list[dict]) -> None:
    """Write connections.json fixture."""
    payload = {
        "version": 1,
        "updated": "2025-01-01",
        "connection_types": ["supports", "contradicts", "extends", "parallels"],
        "connections": connections,
    }
    (workspace / "connections.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


class TestL1Structural:
    """Verify L1 detects cross-domain edges from connections.json."""

    def test_detects_cross_domain_edges(self, cross_domain_workspace: Path) -> None:
        """L1 returns entries for cross-domain connections."""
        loader = WorkspaceLoader(cross_domain_workspace)
        results = _l1_structural(loader)
        assert len(results) > 0
        # The cross_domain_workspace fixture has one cross-domain connection
        # between cosmo-1 and phil-1 with type 'parallels'

    def test_returns_empty_for_no_cross_domain(self, tmp_path: Path) -> None:
        """No connections -> empty results."""
        from tests.llm.conftest import create_test_workspace
        ws = create_test_workspace(tmp_path / "no-cd")
        loader = WorkspaceLoader(ws)
        results = _l1_structural(loader)
        assert results == {} or len(results) == 0

    def test_excludes_same_domain_connections(self, tmp_path: Path) -> None:
        """Connections within the same domain are not bridges."""
        from tests.llm.conftest import create_test_workspace, write_card
        ws = create_test_workspace(tmp_path / "same-domain")
        write_card(ws, "card-a", title="Card A", body="Content A")
        write_card(ws, "card-b", title="Card B", body="Content B")
        # Write intra-domain connection
        _write_connections(ws, [
            {"from": "card-a", "to": "card-b", "type": "extends",
             "created": "2025-01-01", "created_by": "construct", "note": ""},
        ])
        loader = WorkspaceLoader(ws)
        results = _l1_structural(loader)
        # Both cards are in test-domain, so this is same-domain
        # L1 should not report this as a bridge
        assert results == {} or len(results) == 0
