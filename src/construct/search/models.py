"""Normalized search result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    snippet: str
    source_tier: int = Field(ge=1, le=5)
    score: float = Field(ge=0.0, le=1.0)
    provider_specific: dict[str, Any] = Field(default_factory=dict)
    source_domain: str | None = None


class SearchBatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[SearchResult]
    truncated: bool = False
    query: str | None = None
    cluster_id: str | None = None
    provider_name: str
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ProviderCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supports_batch: bool = True
    supports_seed_cluster: bool = True
    max_results: int = Field(ge=1)
