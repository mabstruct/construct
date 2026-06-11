"""Tests for L2 category overlap bridge detection."""
from __future__ import annotations

from pathlib import Path

import pytest

from construct.pipelines.bridge_detect import _l2_category_overlap
from construct.storage.workspace import WorkspaceLoader


class TestL2CategoryOverlap:
    """Verify L2 detects shared content_categories across domains."""

    def test_detects_shared_categories(self, cross_domain_workspace: Path) -> None:
        """L2 returns entries for domains sharing content categories."""
        loader = WorkspaceLoader(cross_domain_workspace)
        results = _l2_category_overlap(loader)
        # Both cosmology and philosophy-of-mind have cards with "foundations" category
        assert len(results) > 0

    def test_excludes_same_domain_pairs(self, cross_domain_workspace: Path) -> None:
        """Self-pairs (same domain) are not included in results."""
        loader = WorkspaceLoader(cross_domain_workspace)
        results = _l2_category_overlap(loader)
        # No key should reference the same domain twice
        for key in results:
            domains = key.split("--")
            assert len(set(domains)) == 2, f"Self-pair found: {key}"
