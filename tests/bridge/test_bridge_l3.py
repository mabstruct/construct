"""Tests for L3 semantic bridge assessment."""
from __future__ import annotations

from pathlib import Path

import pytest

from construct.pipelines.bridge_detect import L3_THRESHOLD, MAX_L3_CANDIDATES


class TestL3Semantic:
    """Verify L3 only fires for promising candidates and respects cost guards."""

    def test_l3_threshold_constant(self) -> None:
        """L3 threshold is 0.3 per spec."""
        assert L3_THRESHOLD == 0.3

    def test_max_candidates_guard(self) -> None:
        """MAX_L3_CANDIDATES limits LLM calls."""
        assert MAX_L3_CANDIDATES == 50
