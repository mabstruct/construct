"""Unit tests for MockSearchProvider — placeholders until Task 2 implementation."""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="MockSearchProvider not implemented until Task 2")
def test_error_injection() -> None:
    """Error injection via fixture should raise RateLimitError."""
    raise NotImplementedError


@pytest.mark.xfail(reason="MockSearchProvider not implemented until Task 2")
def test_result_cap() -> None:
    """max_results below fixture count should set truncated=True."""
    raise NotImplementedError
