"""Pydantic contract models for all 8 views data file types.

Each file-level model represents the envelope-wrapped data structure from
views/build/data/*.json. Records define the inner data shapes. Models follow
Pydantic v2 conventions with ``model_config = ConfigDict(extra="forbid")``.

Usage::

    envelope = ViewsEnvelope[BridgesFile].model_validate(raw_json)
    assert envelope.data.bridges[0].source_domain == "cosmology"

    schema_dict = schema_for(BridgesFile)
    validated = validate_data(BridgesFile, raw_dict)
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Generic envelope
# ---------------------------------------------------------------------------


class ViewsEnvelope(BaseModel, Generic[T]):
    """Generic envelope wrapper for all views data files.

    Carries metadata (schema_version, generated_at, build_id, workspace_id)
    plus a contract ``version`` (semver) per D-01 and the inner ``data``
    payload of type *T*.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.2.0"
    generated_at: str
    build_id: str
    workspace_id: str | None = None
    version: str = "1.0.0"
    data: T


# ---------------------------------------------------------------------------
# Bridges — data payload models
# ---------------------------------------------------------------------------


class BridgeRecord(BaseModel):
    """Single cross-domain bridge (confirmed or candidate)."""

    model_config = ConfigDict(extra="forbid")

    source_domain: str
    target_domain: str
    type: str = Field(..., pattern=r"^(structural|category|semantic)$")
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    cards: list[str] = Field(default_factory=list)


class BridgeSummary(BaseModel):
    """Aggregate sums and L3 gate statistics for bridges.json."""

    model_config = ConfigDict(extra="forbid")

    totals: dict = Field(default_factory=dict)
    l1_l2_only: bool = False
    l3_calls: int = 0
    l3_candidates_eligible: int = 0
    l3_candidates_total: int = 0


class BridgesFile(BaseModel):
    """Data payload for bridges.json (inside the ViewsEnvelope ``data`` key)."""

    model_config = ConfigDict(extra="forbid")

    bridges: list[BridgeRecord] = Field(default_factory=list)
    summary: BridgeSummary


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------


class DomainRecord(BaseModel):
    """One domain entry with derived graph metrics."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    card_count: int = 0
    connection_count: int = 0
    digest_count: int = 0
    article_count: int = 0
    keywords: list[str] = Field(default_factory=list)


class DomainsFile(BaseModel):
    """Data payload for domains.json."""

    model_config = ConfigDict(extra="forbid")

    settings: dict = Field(default_factory=dict)
    domains: list[DomainRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------


class ArticleRecord(BaseModel):
    """One cross-workspace published article."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    url: str
    workspaces: list[str] = Field(default_factory=list)
    published_date: str | None = None


class ArticlesFile(BaseModel):
    """Data payload for articles.json."""

    model_config = ConfigDict(extra="forbid")

    articles: list[ArticleRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stats (global)
# ---------------------------------------------------------------------------


class StatsFile(BaseModel):
    """Data payload for global stats.json."""

    model_config = ConfigDict(extra="forbid")

    total_cards: int = 0
    total_connections: int = 0
    total_domains: int = 0
    total_digests: int = 0
    total_articles: int = 0
    cards_by_domain: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cards (per-workspace)
# ---------------------------------------------------------------------------


class CardRecord(BaseModel):
    """One knowledge card with denormalised connection data."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    epistemic_type: str
    confidence: int = Field(ge=1, le=5)
    source_tier: int = Field(ge=1, le=5)
    lifecycle: str
    domains: list[str] = Field(default_factory=list)
    summary: str
    connections: list[dict] = Field(default_factory=list)
    content_categories: list[str] = Field(default_factory=list)


class CardsFile(BaseModel):
    """Data payload for per-workspace cards.json."""

    model_config = ConfigDict(extra="forbid")

    cards: list[CardRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Connections (per-workspace)
# ---------------------------------------------------------------------------


class ConnectionRecord(BaseModel):
    """One typed edge between two cards."""

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    type: str
    created_at: str
    created_by: str
    note: str | None = None


class ConnectionsFile(BaseModel):
    """Data payload for per-workspace connections.json."""

    model_config = ConfigDict(extra="forbid")

    connections: list[ConnectionRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------


class DigestRecord(BaseModel):
    """One research-cycle digest."""

    model_config = ConfigDict(extra="forbid")

    id: str
    domain_id: str
    title: str
    generated_at: str
    card_ids: list[str] = Field(default_factory=list)
    summary: str


class DigestsFile(BaseModel):
    """Data payload for per-workspace digests.json."""

    model_config = ConfigDict(extra="forbid")

    digests: list[DigestRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventRecord(BaseModel):
    """One audit-trail event entry."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str
    type: str
    actor: str
    card_id: str | None = None
    details: dict | None = None


class EventsFile(BaseModel):
    """Data payload for per-workspace events.json."""

    model_config = ConfigDict(extra="forbid")

    events: list[EventRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def schema_for(model_type: type[BaseModel]) -> dict:
    """Return the JSON Schema dict for *model_type* via ``model_json_schema()``."""
    return model_type.model_json_schema()


def validate_data(model_type: type[BaseModel], data: dict) -> BaseModel:
    """Validate a raw dict against *model_type*.

    Raises ``pydantic.ValidationError`` if the data does not conform to the
    model schema.
    """
    return model_type.model_validate(data)
