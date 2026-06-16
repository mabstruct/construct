"""Tests for the help suggestion service."""
from __future__ import annotations

from construct.services.help import _score_domain, suggest


def test_suggest_no_workspace():
    result = suggest("/nonexistent/path")
    assert result.success
    assert result.data.get("status") == "no_workspace"


def test_suggest_returns_structured():
    result = suggest("/nonexistent/path")
    assert "workspace" in result.data
    assert "suggestion" in result.data


def _healthy_domain(**overrides) -> dict:
    """A domain that has passed tiers 1-3 (cards, configured, connected) so the
    research-staleness tiers (4/5) are the deciding factor."""
    ds = {
        "domain_id": "cosmology",
        "display_name": "Cosmology",
        "card_count": 5,
        "ref_count": 3,
        "connection_count": 4,
        "has_categories": True,
        "has_priorities": True,
        "research_stale_days": -1,
    }
    ds.update(overrides)
    return ds


def test_score_domain_stale_research_reaches_tier_4():
    # Regression for CR-01: a stale research cluster must surface as tier-4
    # priority. The bug read the wrong seeds key ("search_clusters") and a fixed
    # cluster index, so research_stale_days stayed -1 and this tier was dead.
    priority, reason = _score_domain(_healthy_domain(research_stale_days=30))
    assert priority == 4
    assert "stale" in reason


def test_score_domain_recent_research_reaches_tier_5():
    priority, _ = _score_domain(_healthy_domain(research_stale_days=2))
    assert priority == 5


def test_score_domain_healthy_when_research_fresh():
    priority, _ = _score_domain(_healthy_domain(research_stale_days=-1))
    assert priority == 6
