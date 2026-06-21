"""Fixture-driven mock search provider for offline testing."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from construct.schemas.config import MockProviderConfig
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
from construct.storage.workspace import WorkspaceLoader


_ERROR_TYPE_MAP: dict[str, type[SearchError]] = {
    "NetworkError": NetworkError,
    "RateLimitError": RateLimitError,
    "AuthError": AuthError,
    "QuotaExceededError": QuotaExceededError,
    "ParseError": ParseError,
    "ProviderUnavailableError": ProviderUnavailableError,
}


class MockSearchProvider(SearchProvider):
    """Search provider backed by per-query JSON fixtures."""

    def __init__(self, config: MockProviderConfig, *, provider_name: str = "mock") -> None:
        self._config = config
        self._provider_name = provider_name
        self._fixture_dir = Path(config.fixture_dir)
        self._fixtures = self._load_fixtures()

    def _load_fixtures(self) -> dict[str, dict]:
        if not self._fixture_dir.is_dir():
            raise ProviderUnavailableError(
                provider_name=self._provider_name,
                message=f"fixture_dir not found: {self._fixture_dir}",
            )

        fixtures: dict[str, dict] = {}
        for path in sorted(self._fixture_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ParseError(
                    provider_name=self._provider_name,
                    message=f"invalid fixture JSON in {path.name}: {exc}",
                ) from exc
            query = payload.get("query")
            if not isinstance(query, str):
                raise ParseError(
                    provider_name=self._provider_name,
                    message=f"fixture {path.name} missing string 'query' field",
                )
            fixtures[query] = payload
        return fixtures

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_batch=True,
            supports_seed_cluster=True,
            max_results=20,
        )

    def search(
        self,
        query: str,
        *,
        max_results: int,
        cluster_id: str | None = None,
    ) -> SearchBatchOutput:
        payload = self._resolve_fixture(query)
        self._maybe_sleep(payload)
        self._maybe_raise_error(payload)

        results = self._normalize_results(payload, max_results=max_results)
        raw_results = payload.get("response", {}).get("results", [])
        raw_count = len(raw_results) if isinstance(raw_results, list) else 0
        truncated = raw_count > max_results

        return SearchBatchOutput(
            results=results,
            truncated=truncated,
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

    def _resolve_fixture(self, query: str) -> dict:
        try:
            return self._fixtures[query]
        except KeyError as exc:
            raise ParseError(
                provider_name=self._provider_name,
                message=f"no mock fixture for query: {query!r}",
            ) from exc

    def _maybe_sleep(self, payload: dict) -> None:
        latency_ms = payload.get("latency_ms")
        if isinstance(latency_ms, (int, float)) and latency_ms > 0:
            time.sleep(latency_ms / 1000.0)

    def _maybe_raise_error(self, payload: dict) -> None:
        error_block = payload.get("error")
        if not isinstance(error_block, dict):
            return

        error_type = error_block.get("type")
        message = error_block.get("message", f"Mock {error_type}")
        if not isinstance(error_type, str):
            raise ParseError(
                provider_name=self._provider_name,
                message="fixture error block missing string 'type'",
            )

        error_cls = _ERROR_TYPE_MAP.get(error_type)
        if error_cls is None:
            raise ParseError(
                provider_name=self._provider_name,
                message=f"unknown fixture error type: {error_type}",
            )

        if error_cls is RateLimitError:
            retry_after = error_block.get("retry_after_seconds")
            raise RateLimitError(
                provider_name=self._provider_name,
                message=str(message),
                retry_after_seconds=float(retry_after) if retry_after is not None else None,
            )

        raise error_cls(provider_name=self._provider_name, message=str(message))

    def _normalize_results(self, payload: dict, *, max_results: int) -> list[SearchResult]:
        response = payload.get("response")
        if not isinstance(response, dict):
            raise ParseError(
                provider_name=self._provider_name,
                message="fixture missing response block",
            )

        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            raise ParseError(
                provider_name=self._provider_name,
                message="fixture response.results must be a list",
            )

        normalized: list[SearchResult] = []
        for item in raw_results[:max_results]:
            if not isinstance(item, dict):
                continue
            try:
                provider_specific = item.get("provider_specific", {})
                if provider_specific is None:
                    provider_specific = {}
                if not isinstance(provider_specific, dict):
                    provider_specific = {"value": provider_specific}

                core_fields = {
                    key: value
                    for key, value in item.items()
                    if key != "provider_specific"
                }
                result = SearchResult.model_validate(
                    {
                        **core_fields,
                        "provider_specific": provider_specific,
                        "source_domain": _source_domain(item.get("url")),
                    }
                )
            except ValidationError as exc:
                raise ParseError(
                    provider_name=self._provider_name,
                    message=f"invalid fixture result: {exc}",
                ) from exc
            normalized.append(result)
        return normalized


def _source_domain(url: object) -> str | None:
    if not isinstance(url, str) or not url:
        return None
    parsed = urlparse(url)
    return parsed.netloc or None
