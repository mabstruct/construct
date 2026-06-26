"""Tavily search provider adapter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from construct.schemas.config import TavilyProviderConfig
from construct.search.errors import (
    AuthError,
    NetworkError,
    ParseError,
    ProviderUnavailableError,
    RateLimitError,
    SearchError,
)
from construct.search.models import ProviderCapabilities, SearchBatchOutput, SearchResult
from construct.search.provider import SearchProvider
from construct.storage.workspace import WorkspaceLoader


def _import_tavily_sdk() -> tuple[Any, ...]:
    try:
        from tavily import InvalidAPIKeyError, TavilyClient, UsageLimitExceededError
        from tavily.errors import TimeoutError as TavilyTimeoutError
    except ImportError as exc:
        raise ProviderUnavailableError(
            provider_name="tavily",
            message="Install with: pip install -e '.[search]'",
        ) from exc
    return TavilyClient, InvalidAPIKeyError, UsageLimitExceededError, TavilyTimeoutError


def normalize_tavily_result(
    item: dict[str, Any],
    *,
    default_source_tier: int = 3,
) -> SearchResult:
    """Map a Tavily SDK result dict to normalized SearchResult."""
    known_keys = {"title", "url", "content", "score", "snippet", "source_tier"}
    provider_specific = {
        key: value for key, value in item.items() if key not in known_keys
    }

    snippet = item.get("snippet")
    if not snippet:
        snippet = item.get("content", "")

    score_raw = item.get("score", 0.0)
    score = float(score_raw) if score_raw is not None else 0.0
    score = min(max(score, 0.0), 1.0)

    source_tier_raw = item.get("source_tier", default_source_tier)
    source_tier = int(source_tier_raw)

    return SearchResult(
        title=str(item.get("title", "")),
        url=str(item.get("url", "")),
        snippet=str(snippet),
        source_tier=source_tier,
        score=score,
        provider_specific=provider_specific,
        source_domain=_source_domain(item.get("url")),
    )


def normalize_tavily_response(
    response: dict[str, Any],
    *,
    max_results: int,
    query: str,
    cluster_id: str | None,
    provider_name: str,
    default_source_tier: int = 3,
) -> SearchBatchOutput:
    """Normalize a Tavily SDK search response to SearchBatchOutput."""
    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        raise ParseError(
            provider_name=provider_name,
            message="Tavily response results must be a list",
        )

    results = [
        normalize_tavily_result(item, default_source_tier=default_source_tier)
        for item in raw_results[:max_results]
        if isinstance(item, dict)
    ]
    truncated = len(raw_results) > max_results

    return SearchBatchOutput(
        results=results,
        truncated=truncated,
        query=query,
        cluster_id=cluster_id,
        provider_name=provider_name,
    )


def _source_domain(url: object) -> str | None:
    if not isinstance(url, str) or not url:
        return None
    parsed = urlparse(url)
    return parsed.netloc or None


class TavilySearchProvider(SearchProvider):
    """Search provider backed by the Tavily Python SDK."""

    def __init__(self, config: TavilyProviderConfig, *, provider_name: str = "tavily") -> None:
        (
            tavily_client_cls,
            invalid_api_key_error,
            usage_limit_exceeded_error,
            tavily_timeout_error,
        ) = _import_tavily_sdk()

        self._config = config
        self._provider_name = provider_name
        self._TavilyClient = tavily_client_cls
        self._InvalidAPIKeyError = invalid_api_key_error
        self._UsageLimitExceededError = usage_limit_exceeded_error
        self._TavilyTimeoutError = tavily_timeout_error

        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise AuthError(
                provider_name=provider_name,
                message=f"Missing API key environment variable: {config.api_key_env}",
            )

        self._client = tavily_client_cls(api_key=api_key)

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_batch=True,
            supports_seed_cluster=True,
            max_results=self._config.max_results,
        )

    def search(
        self,
        query: str,
        *,
        max_results: int,
        cluster_id: str | None = None,
    ) -> SearchBatchOutput:
        capped_results = min(max_results, self._config.max_results)
        try:
            response = self._client.search(
                query,
                max_results=capped_results,
                search_depth=self._config.search_depth,
                topic=self._config.topic,
                include_raw_content=self._config.include_raw_content,
                timeout=self._config.timeout_seconds,
                include_answer=self._config.include_answer,
            )
        except self._InvalidAPIKeyError as exc:
            raise AuthError(provider_name=self._provider_name, message=str(exc)) from exc
        except self._UsageLimitExceededError as exc:
            retry_after = getattr(exc, "retry_after_seconds", None)
            raise RateLimitError(
                provider_name=self._provider_name,
                message=str(exc),
                retry_after_seconds=float(retry_after) if retry_after is not None else None,
            ) from exc
        except self._TavilyTimeoutError as exc:
            raise NetworkError(provider_name=self._provider_name, message="timeout") from exc
        except SearchError:
            raise
        except Exception as exc:
            raise NetworkError(provider_name=self._provider_name, message=str(exc)) from exc

        if not isinstance(response, dict):
            raise ParseError(
                provider_name=self._provider_name,
                message="Tavily search returned non-dict response",
            )

        return normalize_tavily_response(
            response,
            max_results=capped_results,
            query=query,
            cluster_id=cluster_id,
            provider_name=self._provider_name,
        )

    def search_batch(
        self,
        queries: list[str],
        *,
        max_results: int,
    ) -> list[SearchBatchOutput]:
        return [
            self.search(query, max_results=max_results)
            for query in queries
        ]

    def search_by_seed_cluster(
        self,
        cluster_id: str,
        workspace: Path,
        *,
        max_results: int,
    ) -> SearchBatchOutput:
        loader = WorkspaceLoader(workspace)
        seeds = loader.load_search_seeds()
        cluster = next((item for item in seeds.clusters if item.id == cluster_id), None)
        if cluster is None:
            raise ParseError(
                provider_name=self._provider_name,
                message=f"search cluster '{cluster_id}' not found in search-seeds.json",
            )

        query = " ".join(cluster.terms).strip()
        if not query:
            raise ParseError(
                provider_name=self._provider_name,
                message=f"search cluster '{cluster_id}' has no terms",
            )

        return self.search(query, max_results=max_results, cluster_id=cluster_id)
