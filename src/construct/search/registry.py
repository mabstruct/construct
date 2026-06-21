"""Search provider factory and cap enforcement wrapper."""

from __future__ import annotations

from pathlib import Path

from construct.schemas.config import (
    MockProviderConfig,
    SearchCapsConfig,
    SearchConfig,
    SearchProviderName,
    TavilyProviderConfig,
)
from construct.search.errors import ProviderUnavailableError
from construct.search.models import ProviderCapabilities, SearchBatchOutput
from construct.search.provider import SearchProvider
from construct.search.providers.mock import MockSearchProvider


class _CappedSearchProvider(SearchProvider):
    """Wraps a provider to enforce workspace search caps."""

    def __init__(self, provider: SearchProvider, caps: SearchCapsConfig, provider_name: str) -> None:
        self._provider = provider
        self._caps = caps
        self._provider_name = provider_name

    def search(
        self,
        query: str,
        *,
        max_results: int,
        cluster_id: str | None = None,
    ) -> SearchBatchOutput:
        capped_results = min(max_results, self._caps.max_results_per_query)
        return self._provider.search(
            query,
            max_results=capped_results,
            cluster_id=cluster_id,
        )

    def search_batch(
        self,
        queries: list[str],
        *,
        max_results: int,
    ) -> list[SearchBatchOutput]:
        if len(queries) > self._caps.max_batch_queries:
            queries = queries[: self._caps.max_batch_queries]
        capped_results = min(max_results, self._caps.max_results_per_query)
        outputs = self._provider.search_batch(queries, max_results=capped_results)
        if len(outputs) > self._caps.max_queries_per_request:
            return outputs[: self._caps.max_queries_per_request]
        return outputs

    def search_by_seed_cluster(
        self,
        cluster_id: str,
        workspace: Path,
        *,
        max_results: int,
    ) -> SearchBatchOutput:
        capped_results = min(max_results, self._caps.max_results_per_query)
        return self._provider.search_by_seed_cluster(
            cluster_id,
            workspace,
            max_results=capped_results,
        )

    def get_capabilities(self) -> ProviderCapabilities:
        capabilities = self._provider.get_capabilities()
        return capabilities.model_copy(
            update={"max_results": min(capabilities.max_results, self._caps.max_results_per_query)}
        )


class SearchProviderFactory:
    """Resolve workspace search config to a configured provider instance."""

    @staticmethod
    def create(config: SearchConfig, workspace: Path | None = None) -> SearchProvider:
        provider_key = config.default_provider.value
        provider_config = config.providers.get(provider_key)
        if provider_config is None:
            raise ProviderUnavailableError(
                provider_name=provider_key,
                message=f"default_provider '{provider_key}' not found in providers",
            )

        if config.default_provider == SearchProviderName.mock:
            if not isinstance(provider_config, MockProviderConfig):
                raise ProviderUnavailableError(
                    provider_name=provider_key,
                    message=f"provider block for '{provider_key}' is not type mock",
                )
            provider = MockSearchProvider(provider_config, provider_name=provider_key)
        elif config.default_provider == SearchProviderName.tavily:
            if not isinstance(provider_config, TavilyProviderConfig):
                raise ProviderUnavailableError(
                    provider_name=provider_key,
                    message=f"provider block for '{provider_key}' is not type tavily",
                )
            from construct.search.providers.tavily import TavilySearchProvider

            provider = TavilySearchProvider(provider_config, provider_name=provider_key)
        else:
            raise ProviderUnavailableError(
                provider_name=provider_key,
                message=f"unknown provider type: {config.default_provider}",
            )

        return _CappedSearchProvider(provider, config.caps, provider_key)
