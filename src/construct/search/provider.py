"""SearchProvider abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from construct.search.models import ProviderCapabilities, SearchBatchOutput


class SearchProvider(ABC):
    """Provider-agnostic search interface."""

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        max_results: int,
        cluster_id: str | None = None,
    ) -> SearchBatchOutput:
        """Execute a single search query."""

    @abstractmethod
    def search_batch(
        self,
        queries: list[str],
        *,
        max_results: int,
    ) -> list[SearchBatchOutput]:
        """Execute multiple search queries."""

    @abstractmethod
    def search_by_seed_cluster(
        self,
        cluster_id: str,
        workspace: Path,
        *,
        max_results: int,
    ) -> SearchBatchOutput:
        """Build a query from search-seeds.json cluster terms and search."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capability metadata."""
