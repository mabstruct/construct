"""Tests for the help suggestion service."""
from __future__ import annotations

from construct.services.help import suggest


def test_suggest_no_workspace():
    result = suggest("/nonexistent/path")
    assert result.success
    assert result.data.get("status") == "no_workspace"


def test_suggest_returns_structured():
    result = suggest("/nonexistent/path")
    assert "workspace" in result.data
    assert "suggestion" in result.data
