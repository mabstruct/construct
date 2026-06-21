"""Granular search provider error taxonomy."""

from __future__ import annotations


class SearchError(Exception):
    """Base exception for search provider failures."""

    def __init__(self, *, provider_name: str, message: str) -> None:
        self.provider_name = provider_name
        self.message = message
        super().__init__(message)


class NetworkError(SearchError):
    """Network or connectivity failure reaching the provider."""


class RateLimitError(SearchError):
    """Provider rate limit exceeded."""

    def __init__(
        self,
        *,
        provider_name: str,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(provider_name=provider_name, message=message)


class AuthError(SearchError):
    """Authentication or API key failure."""


class QuotaExceededError(SearchError):
    """Provider usage quota exceeded."""


class ParseError(SearchError):
    """Response parsing or seed-cluster resolution failure."""


class ProviderUnavailableError(SearchError):
    """Provider adapter missing or misconfigured."""
