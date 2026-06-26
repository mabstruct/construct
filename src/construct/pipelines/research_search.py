"""Read-only research search PIPE capability."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from construct.schemas.config import SearchConfig, SearchProviderName
from construct.search.errors import AuthError, RateLimitError, SearchError
from construct.search.registry import SearchProviderFactory
from construct.services.knowledge import OperationError, OperationResult
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader

RESERVED_INGEST_CLUSTERS = frozenset({"manual-ingest", "web-ingest"})


class ResearchSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_path: str
    query: str | None = None
    queries: list[str] | None = None
    cluster_id: str | None = None
    max_results: int | None = Field(default=None, ge=1, le=50)
    provider_override: str | None = None

    @model_validator(mode="after")
    def validate_exactly_one_query_mode(self) -> ResearchSearchInput:
        modes = [
            self.query is not None,
            self.queries is not None,
            self.cluster_id is not None,
        ]
        if sum(modes) != 1:
            raise ValueError("exactly one of query, queries, or cluster_id must be set")
        if self.queries is not None and len(self.queries) == 0:
            raise ValueError("queries must contain at least one item when set")
        return self


class ResearchSearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batches: list[dict[str, Any]]
    provider: str
    degraded: bool
    warnings: list[str] = Field(default_factory=list)


def _safe_error_message(exc: SearchError) -> str:
    if isinstance(exc, AuthError):
        if exc.message.startswith("Missing API key environment variable:"):
            env_name = exc.message.rsplit(":", maxsplit=1)[-1].strip()
            return (
                f"Environment variable {env_name} is not set. "
                f"Export it in this shell: export {env_name}='your-key'"
            )
        return (
            "Authentication failed for search provider — "
            "check that the API key env var is set and valid"
        )
    return exc.message


def _build_search_error_result(exc: SearchError, config: SearchConfig) -> OperationResult:
    error_metadata: dict[str, Any] = {
        "provider": exc.provider_name,
        "degraded": config.caps.degraded_on_provider_error,
    }
    if isinstance(exc, RateLimitError) and exc.retry_after_seconds is not None:
        error_metadata["retry_after_seconds"] = exc.retry_after_seconds

    output = ResearchSearchOutput(
        batches=[],
        provider=exc.provider_name,
        degraded=config.caps.degraded_on_provider_error,
        warnings=[],
    )
    data = output.model_dump(mode="json")
    data.update(error_metadata)

    return OperationResult(
        success=False,
        message=_safe_error_message(exc),
        errors=[
            OperationError(
                reason=exc.__class__.__name__,
                field=exc.provider_name,
                suggestion=_safe_error_message(exc),
            )
        ],
        data=data,
    )


def research_search(input: ResearchSearchInput) -> OperationResult:
    try:
        root = Path(input.workspace_path)
        loader = WorkspaceLoader(root)

        if not loader.resolve(".construct/search.yaml").exists():
            return OperationResult(
                success=False,
                message="missing .construct/search.yaml",
                errors=[
                    OperationError(
                        reason="missing_config",
                        field=".construct/search.yaml",
                    )
                ],
            )

        try:
            config = loader.load_search_config()
        except WorkspaceLoadError as exc:
            return OperationResult(
                success=False,
                message=str(exc),
                errors=[
                    OperationError(
                        reason="invalid_config",
                        field=".construct/search.yaml",
                    )
                ],
            )

        if input.provider_override:
            if input.provider_override not in config.providers:
                return OperationResult(
                    success=False,
                    message=f"unknown provider override: {input.provider_override}",
                    errors=[
                        OperationError(
                            reason="invalid_provider",
                            field="provider_override",
                        )
                    ],
                )
            try:
                override = SearchProviderName(input.provider_override)
            except ValueError:
                return OperationResult(
                    success=False,
                    message=f"invalid provider override: {input.provider_override}",
                    errors=[
                        OperationError(
                            reason="invalid_provider",
                            field="provider_override",
                        )
                    ],
                )
            config = config.model_copy(update={"default_provider": override})

        warnings: list[str] = []
        if input.cluster_id in RESERVED_INGEST_CLUSTERS:
            warnings.append("cluster is reserved for ingest, not a research target")

        max_results = input.max_results or config.caps.max_results_per_query

        query_list: list[str] | None = None
        if input.queries is not None:
            query_list = list(input.queries)
            if len(query_list) > config.caps.max_batch_queries:
                query_list = query_list[: config.caps.max_batch_queries]
                warnings.append(
                    f"queries truncated to max_batch_queries ({config.caps.max_batch_queries})"
                )
            if len(query_list) > config.caps.max_queries_per_request:
                query_list = query_list[: config.caps.max_queries_per_request]
                warnings.append(
                    "queries truncated to max_queries_per_request "
                    f"({config.caps.max_queries_per_request})"
                )

        try:
            provider = SearchProviderFactory.create(config, workspace=loader.root)
        except SearchError as exc:
            if config.caps.degraded_on_provider_error:
                return _build_search_error_result(exc, config)
            raise

        try:
            if input.query is not None:
                batches = [
                    provider.search(input.query, max_results=max_results)
                ]
            elif query_list is not None:
                batches = provider.search_batch(query_list, max_results=max_results)
                if len(batches) > config.caps.max_queries_per_request:
                    batches = batches[: config.caps.max_queries_per_request]
            else:
                assert input.cluster_id is not None
                batches = [
                    provider.search_by_seed_cluster(
                        input.cluster_id,
                        loader.root,
                        max_results=max_results,
                    )
                ]
        except SearchError as exc:
            if config.caps.degraded_on_provider_error:
                return _build_search_error_result(exc, config)
            raise

        provider_name = batches[0].provider_name if batches else config.default_provider.value
        total_results = sum(len(batch.results) for batch in batches)

        output = ResearchSearchOutput(
            batches=[batch.model_dump(mode="json") for batch in batches],
            provider=provider_name,
            degraded=False,
            warnings=warnings,
        )

        return OperationResult(
            success=True,
            message=f"Search complete ({total_results} results)",
            data=output.model_dump(mode="json"),
        )
    except (WorkspaceLoadError, OSError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=str(exc),
            errors=[OperationError(reason=str(exc))],
        )
