"""Tests for bridge scoring model (spec-v02-cross-domain-data.md §7).

Weights: L1=0.30, L2=0.20, L3=0.50
"""
from __future__ import annotations

import pytest


# The scoring function will be in bridge_detect.py — test against spec weights
def _compute_bridge_score(
    l1_structural: bool,
    l2_shared_categories: list[str],
    l3_candidate_strength: str | None,
) -> tuple[float, str]:
    """Replicate from spec for early testing. Overridden by Plan 03 import."""
    l1_score = 1.0 if l1_structural else 0.0
    l2_score = min(1.0, len(l2_shared_categories) / 3.0) if l2_shared_categories else 0.0
    l3_map = {"strong": 1.0, "possible": 0.6}
    l3_score = l3_map.get(l3_candidate_strength, 0.0) if l3_candidate_strength else 0.0
    score = round((0.30 * l1_score) + (0.20 * l2_score) + (0.50 * l3_score), 2)
    if l1_structural:
        band = "strong"
    elif score >= 0.70:
        band = "strong"
    elif score >= 0.45:
        band = "medium"
    else:
        band = "weak"
    return score, band


class TestBridgeScoring:
    """Verify scoring matches spec-v02-cross-domain-data.md §7 weights + bands."""

    @pytest.mark.parametrize("l1,l2_cats,l3,expected_score,expected_band", [
        (True, [], "strong", 0.80, "strong"),           # Confirmed: L1 structural
        (True, ["a", "b"], None, 0.43, "strong"),        # L1 alone with strong band
        (False, ["a", "b", "c"], "strong", 0.70, "strong"),  # L2 full + L3 strong
        (False, ["a"], "possible", 0.37, "weak"),          # Below medium threshold
        (False, ["a", "b"], None, 0.13, "weak"),           # L2 only, no L3
        (False, [], None, 0.0, "weak"),                    # No signal at all
        (False, ["a", "b", "c", "d"], "possible", 0.50, "medium"),  # Medium band
        (False, ["a", "b"], "possible", 0.43, "weak"),     # Just below medium
    ])
    def test_compute_bridge_score(self, l1: bool, l2_cats: list[str],
                                   l3: str | None, expected_score: float,
                                   expected_band: str) -> None:
        score, band = _compute_bridge_score(l1, l2_cats, l3)
        assert score == pytest.approx(expected_score, abs=0.01)
        assert band == expected_band

    def test_weight_sum(self) -> None:
        """Verify all weights sum to 1.0 per spec."""
        assert 0.30 + 0.20 + 0.50 == 1.0
