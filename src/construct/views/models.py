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


# D-02: the field set below is derived from what the parsers actually emit —
# ``parse_bridges._build_summary`` returns exactly ``totals`` and
# ``top_domain_pairs``. The four L3 gate fields are retained because
# ``pipelines/bridge_detect.py`` emits them and ``llm/curation_run.py`` reads
# ``l1_l2_only``; they are defaulted and harmless.
class BridgeSummary(BaseModel):
    """Aggregate sums, top domain pairs, and L3 gate statistics for bridges.json."""

    model_config = ConfigDict(extra="forbid")

    totals: dict = Field(default_factory=dict)
    top_domain_pairs: list[dict] = Field(default_factory=list)
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


# D-02: the field set below is derived from what ``lib/parse_domains.parse``
# emits and is corroborated field-for-field by spec-v02-data-model.md §5.1. The
# previous scalar counters (card_count, connection_count, digest_count,
# article_count) and ``keywords`` were phantoms — no parser emitted them and no
# consumer read them; the real counts live inside ``metrics``.
# ``cross_domain_links`` and ``metrics`` stay open (bare list / dict) rather
# than becoming nested models: the parser guards them with nothing stronger than
# an ``isinstance(list)`` check, so a nested model would be stricter than the
# parser guarantees and would reject legacy domains.yaml content it accepts.
# Three element shapes exist in the wild — schemas/config.py's
# ``{"domain", "topics"}``, spec §5.1's ``{"to", "note"}``, and the bare domain-id
# strings the v02 fixtures use — so the element type is deliberately unconstrained.
class DomainRecord(BaseModel):
    """One domain entry with declared metadata and derived graph metrics."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    status: str = "active"
    created: str = ""
    content_categories: list[str] = Field(default_factory=list)
    source_priorities: list[str] = Field(default_factory=list)
    cross_domain_links: list = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class DomainsFile(BaseModel):
    """Data payload for domains.json."""

    model_config = ConfigDict(extra="forbid")

    settings: dict = Field(default_factory=dict)
    domains: list[DomainRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------


# D-02: the field set below is derived from what ``lib/parse_articles._parse``
# emits and is corroborated field-for-field by spec-v02-data-model.md §5.5. The
# previous ``url`` / ``published_date`` pair was a phantom — no parser emits
# either, and ``url`` being *required* meant every populated install root failed
# validation on articles.json. ``source_cards`` stays an open list[dict] because
# the parser emits two element shapes: an expanded card record, and the
# ``{"id", "status": "missing"}`` stub §5.5 mandates for unresolvable ids.
class ArticleRecord(BaseModel):
    """One cross-workspace published article with expanded source-card provenance."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    type: str = ""
    status: str = "draft"
    date: str = ""
    workspaces: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    confidence_floor: int = 0
    source_cards: list[dict] = Field(default_factory=list)
    body_markdown: str = ""
    excerpt: str = ""
    raw_path: str = ""


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
    # D-02: ``lib/parse_connections.denormalize_into_cards`` assigns
    # ``sorted(nset)`` where ``nset`` is a set of neighbour card ids, so this is
    # always a list of id strings. Spec §5.2 corroborates: the full edge list
    # with types lives in connections.json, not here.
    connections: list[str] = Field(default_factory=list)
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


# D-02: ``lib/parse_events.parse`` passes ``log/events.jsonl`` lines through
# verbatim, and ``details`` is free-form there — spec §5.6 explicitly declines to
# enumerate event shapes. Real logs carry a human-readable string
# (``"Created card-hubble-tension"``); structured emitters carry a dict. The
# union describes both rather than rejecting the string form.
class EventRecord(BaseModel):
    """One audit-trail event entry."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str
    type: str
    actor: str
    card_id: str | None = None
    details: str | dict | None = None


class EventsFile(BaseModel):
    """Data payload for per-workspace events.json."""

    model_config = ConfigDict(extra="forbid")

    events: list[EventRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


# Top-level metadata keys carried by views data files. The generator emits
# *flat* files where these sit alongside the payload (e.g. bridges.json:
# {version, generated, workspace, bridges, summary}); the ViewsEnvelope form
# nests the payload under ``data`` instead. Both are recognised on read.
ENVELOPE_METADATA_KEYS = frozenset(
    {
        "version",
        "generated",
        "workspace",
        "schema_version",
        "generated_at",
        "build_id",
        "workspace_id",
    }
)


def unwrap_payload(raw: dict) -> dict:
    """Return the contract payload from a raw views data dict.

    Supports both shapes produced/consumed across the pipeline:

    * **Envelope** — ``{..metadata.., "data": {<payload>}}`` → returns ``raw["data"]``.
    * **Flat** — ``{<metadata fields>, <payload fields>}`` (what the generator
      currently writes) → returns the payload with the known metadata keys
      stripped, so it validates against the strict ``extra="forbid"`` models.
    """
    inner = raw.get("data")
    if isinstance(inner, dict):
        return inner
    return {k: v for k, v in raw.items() if k not in ENVELOPE_METADATA_KEYS}


def schema_for(model_type: type[BaseModel]) -> dict:
    """Return the JSON Schema dict for *model_type* via ``model_json_schema()``."""
    return model_type.model_json_schema()


def validate_data(model_type: type[BaseModel], data: dict) -> BaseModel:
    """Validate a raw dict against *model_type*.

    Raises ``pydantic.ValidationError`` if the data does not conform to the
    model schema.
    """
    return model_type.model_validate(data)
