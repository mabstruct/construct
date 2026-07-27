"""Pydantic contract models for the views data files.

Each file-level model represents the envelope-wrapped data structure from
``views/build/data/*.json``. Records define the inner data shapes.

Usage::

    envelope = ViewsEnvelope[BridgesFile].model_validate(raw_json)
    assert envelope.data.bridges[0].source_domain == "cosmology"

    schema_dict = schema_for(BridgesFile)
    validated = validate_data(BridgesFile, raw_dict)

D-01: these models declare the field names ``views/generate.py`` actually
writes, not a hand-transcribed ideal of them. The generator used to compute a
correctly-adapted projection of each file, validate *that*, and then write the
raw parser dict — so ``views validate`` rejected five of the eight files
``views generate`` had just called clean, four of them purely from field
renames. Every rename below was taken from the generator's own adapter tables,
which were the only place the writer→validator projection was written down.

D-01 is not a reversal of the standing ING-02 decision ("conform the data to the
gate, not the gate to the data"). ING-02 governs **canonical truth** — cards,
refs, connections — where strictness protects the knowledge model and a
surprising field is a governance event. ``views/build/`` is a **derived
projection**: its sole author is ``views/generate.py``, its sole consumer is the
SPA, and it is regenerated from canonical state on demand. There the written
bytes *are* the contract, and a model that disagrees with them is simply wrong.
The distinction is why the emitter models in ``construct.schemas`` keep
``extra="forbid"`` while this module does not.

D-03: every model here uses ``ConfigDict(extra="ignore")``. This is a
deliberate, scoped exception to the AGENTS.md § Pydantic Conventions rule that
every model sets ``extra="forbid"``. A parser that starts emitting one more key
must not invalidate the models, and must not invalidate the ``views/build/``
copies already sitting on users' disks. The exception stops at this module: it
never extends to canonical models or to capability input models, where an
unexpected field crosses a trust boundary rather than reflecting parser drift.

Relaxing to ignore-extra is only safe while the models still *reject* things.
A model with no required fields that ignores extras validates literally
anything, which removes the gate rather than fixing it. Every record model below
therefore keeps a required core, and ``tests/contract/test_views_contracts.py``
asserts a malformed-payload rejection for each one.
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

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

    totals: dict = Field(default_factory=dict)
    top_domain_pairs: list[dict] = Field(default_factory=list)
    l1_l2_only: bool = False
    l3_calls: int = 0
    l3_candidates_eligible: int = 0
    l3_candidates_total: int = 0


class BridgesFile(BaseModel):
    """Data payload for bridges.json (inside the ViewsEnvelope ``data`` key)."""

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

    articles: list[ArticleRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stats — two files, two contracts
#
# ``stats.json`` exists twice: once at the data-dir root (written by
# ``compute_stats.compute_global``) and once per workspace (written by
# ``compute_stats.compute_workspace``). Same filename, different directory,
# different writer, different shape. Modelling them with one class would let each
# validate against the other's contract and report a clean build while the SPA
# read fields that were never written — so they get two models, and the contract
# tests assert that neither payload validates against the other's model.
# ---------------------------------------------------------------------------


# D-01: derived from ``compute_stats.compute_global``'s ``totals`` literal.
# ``workspaces`` is required and is the discriminator: only the cross-workspace
# aggregator counts workspaces, so its absence identifies a per-workspace payload
# that has been pointed at the global model by mistake.
class GlobalStatsTotals(BaseModel):
    """The ``totals`` map of the global stats.json."""

    model_config = ConfigDict(extra="ignore")

    workspaces: int
    papers: int = 0
    cards: int = 0
    connections: int = 0
    digests: int = 0
    articles: int = 0


class WorkspaceStatsTotals(BaseModel):
    """The ``totals`` map of a per-workspace stats.json."""

    model_config = ConfigDict(extra="ignore")

    papers: int = 0
    cards: int = 0
    connections: int = 0
    digests: int = 0
    articles: int = 0


# D-01: the field set below is derived from what ``compute_stats.compute_global``
# actually returns, exactly as ``DomainRecord`` was derived from
# ``parse_domains.parse``. The six scalar counters it replaces
# (total_cards, total_connections, total_domains, total_digests, total_articles,
# cards_by_domain) were phantoms: no writer emitted any of them, and the
# generator's adapter synthesised all six from ``totals`` before validating,
# then wrote ``totals``. That single adapter was the whole of the stats.json
# byte-contract failure.
# The three breakdown maps stay open ``dict[str, int]`` rather than becoming
# nested models with named members: their keys are lifecycle states, confidence
# levels and activity counters, all of which are vocabulary that governance can
# extend, and a nested model would be stricter than ``compute_global`` promises.
class StatsFile(BaseModel):
    """Data payload for the global stats.json."""

    model_config = ConfigDict(extra="ignore")

    totals: GlobalStatsTotals
    by_lifecycle: dict[str, int] = Field(default_factory=dict)
    by_confidence: dict[str, int] = Field(default_factory=dict)
    activity_last_30d: dict[str, int] = Field(default_factory=dict)


# D-18: ``<ws>/stats.json`` had no contract model and was therefore written with
# no validation at all — one of the only two data files the generator produced
# blind. Field set derived from ``compute_stats.compute_workspace``.
# The three graph metrics are required rather than defaulted: they are what
# distinguishes this file from its global namesake, and the SPA's
# WorkspaceDashboard renders all three unconditionally.
class WorkspaceStatsFile(BaseModel):
    """Data payload for a per-workspace stats.json."""

    model_config = ConfigDict(extra="ignore")

    totals: WorkspaceStatsTotals = Field(default_factory=WorkspaceStatsTotals)
    by_lifecycle: dict[str, int] = Field(default_factory=dict)
    by_confidence: dict[str, int] = Field(default_factory=dict)
    activity_last_30d: dict[str, int] = Field(default_factory=dict)
    connection_density: float
    orphan_cards: int
    avg_confidence: float
    category_coverage: dict[str, int] = Field(default_factory=dict)
    search_clusters: list = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Cards (per-workspace)
# ---------------------------------------------------------------------------


# D-01: the field names below are ``lib/parse_cards.parse``'s, taken from the
# generator's own cards.json adapter. Two were renames — ``summary_excerpt`` was
# read as ``summary`` and ``connects_to`` as ``connections`` — and six writer
# keys (author, body_markdown, created, last_reviewed, sources, tags) had no
# field at all and produced 243 validation errors on a populated install root.
#
# Those six are *declared* rather than left to the D-03 relaxation: the scaffold
# SPA reads every one of them (CardSidePanel reads card.author, card.tags,
# card.sources, card.last_reviewed, card.body_markdown, card.created; Wiki reads
# the same set). A declared field is a contract; an ignored key is only an
# absence of complaint, and a key a consumer renders is owed the former.
#
# ``sources`` stays an open list: ``parse_cards`` passes the frontmatter value
# through behind nothing stronger than an ``isinstance(list)`` check, so a
# nested model would be stricter than the parser guarantees.
class CardRecord(BaseModel):
    """One knowledge card with denormalised connection data."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    epistemic_type: str
    confidence: int = Field(ge=1, le=5)
    source_tier: int = Field(ge=1, le=5)
    lifecycle: str
    domains: list[str] = Field(default_factory=list)
    content_categories: list[str] = Field(default_factory=list)
    summary_excerpt: str = ""
    # D-02: ``lib/parse_connections.denormalize_into_cards`` assigns
    # ``sorted(nset)`` where ``nset`` is a set of neighbour card ids, so this is
    # always a list of id strings. Spec §5.2 corroborates: the full edge list
    # with types lives in connections.json, not here.
    connects_to: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    author: str = ""
    created: str = ""
    # ``parse_cards`` hands the raw frontmatter value through for this one key.
    # An unquoted YAML date therefore arrives as a ``datetime.date``, which this
    # annotation rejects at validation time. That is the intended outcome and an
    # improvement: such a value could never reach disk anyway — ``json.dumps`` in
    # ``_write_atomic`` raises TypeError on it — so the choice is between a
    # reported validation error and an unhandled crash out of ``generate()``.
    last_reviewed: str | None = None
    sources: list = Field(default_factory=list)
    body_markdown: str = ""


class CardsFile(BaseModel):
    """Data payload for per-workspace cards.json."""

    model_config = ConfigDict(extra="ignore")

    cards: list[CardRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Connections (per-workspace)
# ---------------------------------------------------------------------------


# D-01: field names taken from ``lib/parse_connections.parse`` via the
# generator's connections.json adapter — ``created_at`` was reading ``created``
# and ``created_by`` was reading ``author``. The record-level ``id`` the parser
# assigns (the connections.json value, or a stable hash of source|target|type)
# had no field and tripped extra_forbidden on every edge.
# Both timestamp and author default to "" because ``parse_connections`` emits
# ``str(c.get(...,""))`` for each: a legacy connections.json with no provenance
# still produces an edge, and rejecting it would drop real graph structure.
class ConnectionRecord(BaseModel):
    """One typed edge between two cards."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    source: str
    target: str
    type: str
    created: str = ""
    author: str = ""
    note: str | None = None


# D-01: ``type_counts`` is declared here rather than added to
# ``ENVELOPE_METADATA_KEYS``. That frozenset drives ``unwrap_payload``, which
# *strips* the keys it names — listing a real payload field there would delete
# the per-type counts on the way in instead of validating them.
class ConnectionsFile(BaseModel):
    """Data payload for per-workspace connections.json."""

    model_config = ConfigDict(extra="ignore")

    connections: list[ConnectionRecord] = Field(default_factory=list)
    type_counts: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------


class DigestRecord(BaseModel):
    """One research-cycle digest."""

    model_config = ConfigDict(extra="ignore")

    id: str
    domain_id: str
    title: str
    generated_at: str
    card_ids: list[str] = Field(default_factory=list)
    summary: str


class DigestsFile(BaseModel):
    """Data payload for per-workspace digests.json."""

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")

    timestamp: str
    type: str
    actor: str
    card_id: str | None = None
    details: str | dict | None = None


class EventsFile(BaseModel):
    """Data payload for per-workspace events.json."""

    model_config = ConfigDict(extra="ignore")

    events: list[EventRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Curation history (per-workspace)
# ---------------------------------------------------------------------------


# D-18: ``<ws>/curation-history.json`` is the second of the two files the
# generator wrote with no contract model of any kind. Field set derived from
# ``lib/parse_curation.parse``.
#
# RESEARCH assumption A5 flagged this shape as possibly unstable and recommended
# deferring the model; D-18 overrides that. The mitigation for A5 is structural
# rather than a skip: the *envelope* is pinned (a ``cycles`` list of identified
# records, which is what the generator's write loop guarantees) while the
# volatile interior — the ``deltas`` counter map, whose keys are governance
# vocabulary — is a declared open mapping. A new counter therefore costs nothing
# and a missing cycle id still fails.
class CurationCycleRecord(BaseModel):
    """One curation cycle, parsed from a CURATION-REPORT-*.md."""

    model_config = ConfigDict(extra="ignore")

    id: str
    date: str = ""
    summary: str = ""
    deltas: dict = Field(default_factory=dict)
    raw_path: str = ""


class CurationHistoryFile(BaseModel):
    """Data payload for per-workspace curation-history.json.

    ``cycles`` is required, not defaulted: the generator always writes the key
    (a workspace with no curation reports gets ``{"cycles": []}``), so a payload
    without it is malformed rather than empty. Defaulting it would make this
    model accept ``{}`` — and an ignore-extra model that accepts ``{}`` accepts
    anything, which is the failure mode D-03 has to avoid.
    """

    model_config = ConfigDict(extra="ignore")

    cycles: list[CurationCycleRecord]


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
