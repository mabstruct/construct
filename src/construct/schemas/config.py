"""Workspace configuration and structured artifact schema models."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENV_VAR_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
ROUTING_TASKS = {
    "research_ingestion",
    "card_formatting",
    "source_evaluation",
    "taxonomy_tagging",
    "duplicate_detection",
    "connection_typing",
    "cross_domain_ideation",
    "synthesis_drafting",
    "co_authorship",
    "gap_analysis",
    "domain_init_interview",
    "chat_conversation",
}
PROVIDER_TIERS = {"frontier", "workhorse", "lightweight"}


class DomainStatus(str, Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class ProviderName(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    google = "google"
    ollama = "ollama"
    mock = "mock"


class CrossDomainLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    topics: list[str] = Field(default_factory=list)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        if not KEBAB_CASE_PATTERN.fullmatch(value):
            raise ValueError("domain must be kebab-case")
        return value


class DomainRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    status: DomainStatus = DomainStatus.active
    created: date | None = None
    content_categories: list[str] = Field(default_factory=list)
    source_priorities: list[str] = Field(default_factory=list)
    cross_domain_links: list[CrossDomainLink] = Field(default_factory=list)

    @field_validator("content_categories")
    @classmethod
    def validate_content_categories(cls, value: list[str]) -> list[str]:
        for item in value:
            if not KEBAB_CASE_PATTERN.fullmatch(item):
                raise ValueError("entries must be kebab-case, e.g. 'quantum-gravity' not 'quantum gravity'")
        return value


class DomainsRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domains: dict[str, DomainRegistryEntry]

    @field_validator("domains")
    @classmethod
    def validate_domain_ids(cls, value: dict[str, DomainRegistryEntry]) -> dict[str, DomainRegistryEntry]:
        for domain_id, entry in value.items():
            if not KEBAB_CASE_PATTERN.fullmatch(domain_id):
                raise ValueError("domain ids must be kebab-case")
        return value


DomainConfig = DomainRegistryEntry


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName
    model: str
    api_key_env: str | None = None

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not ENV_VAR_PATTERN.fullmatch(value):
            raise ValueError("api_key_env must be an environment variable name")
        return value


class ProviderMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frontier: ProviderConfig
    workhorse: ProviderConfig
    lightweight: ProviderConfig


class ModelRoutingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: ProviderMap
    routing: dict[str, str]
    fallback_chain: list[str]

    @field_validator("routing")
    @classmethod
    def validate_routing(cls, value: dict[str, str]) -> dict[str, str]:
        if set(value) != ROUTING_TASKS:
            missing = sorted(ROUTING_TASKS - set(value))
            extra = sorted(set(value) - ROUTING_TASKS)
            raise ValueError(f"routing must contain exactly the supported task keys; missing={missing}, extra={extra}")
        for tier in value.values():
            if tier not in PROVIDER_TIERS:
                raise ValueError("routing values must reference frontier, workhorse, or lightweight")
        return value

    @field_validator("fallback_chain")
    @classmethod
    def validate_fallback_chain(cls, value: list[str]) -> list[str]:
        for tier in value:
            if tier not in PROVIDER_TIERS:
                raise ValueError("fallback_chain must reference defined provider tiers")
        return value


class PromotionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_to_growing_confidence: int
    seed_to_growing_min_connections: int
    growing_to_mature_confidence: int
    growing_to_mature_source_tier: int
    growing_to_mature_min_connections: int
    require_human_approval: bool = False


class DecayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decay_window_days: int
    auto_archive_on_decay: bool = False


class QualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orphan_tolerance_days: int
    min_sources_for_promotion: int


class HeartbeatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    views_interval_seconds: int
    curation_interval_seconds: int
    research_interval_seconds: int


class ResearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevance_threshold: float
    card_creation_threshold: float
    max_papers_per_cycle: int
    lookback_days_initial: int
    max_retries: int | None = None


class GovernanceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    promotion: PromotionConfig
    decay: DecayConfig
    quality: QualityConfig
    heartbeat: HeartbeatConfig | None = None
    research: ResearchConfig


class SearchClusterStatus(str, Enum):
    active = "active"
    paused = "paused"
    exhausted = "exhausted"


class SearchCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    domain: str
    terms: list[str] = Field(default_factory=list)
    weight: float = Field(ge=0.0, le=1.0)
    status: SearchClusterStatus
    last_queried: datetime | None = None

    @field_validator("id", "domain")
    @classmethod
    def validate_cluster_ids(cls, value: str) -> str:
        if not KEBAB_CASE_PATTERN.fullmatch(value):
            raise ValueError("value must be kebab-case, e.g. 'quantum-gravity'")
        return value


class SearchSeedsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    updated: datetime | None = None
    clusters: list[SearchCluster] = Field(default_factory=list)


class ExtractionStatus(str, Enum):
    complete = "complete"
    partial = "partial"
    skipped = "skipped"


class ReferenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    url: str
    abstract: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    key_findings: list[str] = Field(default_factory=list)
    content_categories: list[str] = Field(default_factory=list)
    source_tier: int = Field(ge=1, le=5)
    extraction_status: ExtractionStatus
    ingested_date: date
    domain: str
    search_cluster: str
    cards_generated: list[str] = Field(default_factory=list)

    @field_validator("id", "domain", "content_categories", "cards_generated")
    @classmethod
    def validate_reference_kebab_case(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str):
            if not KEBAB_CASE_PATTERN.fullmatch(value):
                raise ValueError("value must be kebab-case, e.g. 'quantum-gravity'")
            return value
        for item in value:
            if not KEBAB_CASE_PATTERN.fullmatch(item):
                raise ValueError("entries must be kebab-case, e.g. 'quantum-gravity' not 'quantum gravity'")
        return value


class EventAgent(str, Enum):
    construct = "construct"
    curator = "curator"
    researcher = "researcher"
    human = "human"


class EventResult(str, Enum):
    success = "success"
    failure = "failure"
    escalated = "escalated"


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime
    agent: EventAgent
    action: str = Field(min_length=1)
    target: str | None = None
    detail: str | None = None
    result: EventResult
