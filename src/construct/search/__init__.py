"""Search provider package — provider-agnostic search spine."""

from construct.search.errors import (
    AuthError,
    NetworkError,
    ParseError,
    ProviderUnavailableError,
    QuotaExceededError,
    RateLimitError,
    SearchError,
)
from construct.search.models import ProviderCapabilities, SearchBatchOutput, SearchResult
from construct.search.provider import SearchProvider
from construct.search.registry import SearchProviderFactory

__all__ = [
    "AuthError",
    "NetworkError",
    "ParseError",
    "ProviderUnavailableError",
    "ProviderCapabilities",
    "QuotaExceededError",
    "RateLimitError",
    "SearchBatchOutput",
    "SearchError",
    "SearchProvider",
    "SearchProviderFactory",
    "SearchResult",
]
