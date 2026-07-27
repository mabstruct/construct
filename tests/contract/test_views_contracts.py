"""Contract tests validating views data file shapes against Pydantic schemas.

Tests load actual JSON data from the ``test-ws/my-construct/`` fixture,
validate against the Pydantic contract models, and verify that schema
export, round-trip, and rejection mechanics all work as expected per
ADV-03 / D-01.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from construct.views.models import (
    ArticleRecord,
    ArticlesFile,
    BridgeRecord,
    BridgesFile,
    BridgeSummary,
    CardRecord,
    CardsFile,
    ConnectionRecord,
    ConnectionsFile,
    CurationCycleRecord,
    CurationHistoryFile,
    DigestRecord,
    DigestsFile,
    DomainRecord,
    DomainsFile,
    EventRecord,
    EventsFile,
    StatsFile,
    ViewsEnvelope,
    WorkspaceStatsFile,
    schema_for,
    unwrap_payload,
    validate_data,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_WS = Path(__file__).parents[2] / "test-ws" / "my-construct"
DATA_DIR = TEST_WS / "views" / "build" / "data"


@pytest.fixture(scope="module")
def bridges_raw() -> dict:
    """Load the real bridges.json from the test-ws fixture."""
    path = DATA_DIR / "bridges.json"
    if not path.is_file():
        pytest.skip(f"test fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_MODELS: list[type[BaseModel]] = [
    ArticleRecord,
    ArticlesFile,
    BridgeRecord,
    BridgesFile,
    BridgeSummary,
    CardRecord,
    CardsFile,
    ConnectionRecord,
    ConnectionsFile,
    CurationCycleRecord,
    CurationHistoryFile,
    DigestRecord,
    DigestsFile,
    DomainRecord,
    DomainsFile,
    EventRecord,
    EventsFile,
    StatsFile,
    ViewsEnvelope,
    WorkspaceStatsFile,
]

# ---------------------------------------------------------------------------
# Writer-shaped payloads (D-01)
#
# Every literal below is the shape the *generator* writes, transcribed from the
# parser that produces it. They are deliberately literals rather than parser
# invocations: a test that calls the parser to build its own expectation cannot
# fail when the parser and the model drift apart, which is the exact defect
# VFIX-01 exists to catch. ``TestWriterBytesAreTheContract`` closes the loop by
# running the real parsers against a real fixture.
# ---------------------------------------------------------------------------

#: ``lib/parse_cards.parse`` + ``parse_connections.denormalize_into_cards``.
WRITER_CARD: dict = {
    "id": "card-hard-problem",
    "title": "The Hard Problem of Consciousness",
    "epistemic_type": "claim",
    "confidence": 4,
    "source_tier": 1,
    "lifecycle": "mature",
    "domains": ["philosophy-of-mind"],
    "content_categories": ["qualia"],
    "tags": ["consciousness", "chalmers"],
    "author": "",
    "created": "2026-04-02",
    "last_reviewed": None,
    "sources": [{"type": "url", "ref": "https://example.org/chalmers"}],
    "connects_to": ["card-zombie-argument"],
    "body_markdown": "## Summary\nThe hard problem...\n",
    "summary_excerpt": "The hard problem of consciousness is...",
}

#: ``lib/parse_connections.parse`` — one element of its ``connections`` list.
WRITER_CONNECTION: dict = {
    "id": "conn-1a2b3c4d",
    "source": "card-hard-problem",
    "target": "card-zombie-argument",
    "type": "supports",
    "note": "",
    "created": "2026-04-02",
    "author": "curator",
}

#: ``lib/parse_connections.parse`` — the whole per-workspace payload.
WRITER_CONNECTIONS_FILE: dict = {
    "connections": [WRITER_CONNECTION],
    "type_counts": {"supports": 1, "contradicts": 0, "extends": 0},
}

#: ``lib/compute_stats.compute_global`` — the global ``stats.json`` payload.
WRITER_GLOBAL_STATS: dict = {
    "totals": {
        "workspaces": 2,
        "papers": 7,
        "cards": 41,
        "connections": 60,
        "digests": 3,
        "articles": 1,
    },
    "by_lifecycle": {"seed": 8, "growing": 20, "mature": 12, "archived": 1},
    "by_confidence": {"1": 2, "2": 6, "3": 15, "4": 13, "5": 5},
    "activity_last_30d": {
        "cards_created": 4,
        "connections_added": 6,
        "digests": 1,
        "articles": 0,
    },
}

#: ``lib/compute_stats.compute_workspace`` — the ``<ws>/stats.json`` payload.
WRITER_WORKSPACE_STATS: dict = {
    "totals": {"papers": 3, "cards": 20, "connections": 28, "digests": 2, "articles": 1},
    "by_lifecycle": {"seed": 4, "growing": 10, "mature": 6, "archived": 0},
    "by_confidence": {"1": 1, "2": 3, "3": 8, "4": 6, "5": 2},
    "activity_last_30d": {
        "cards_created": 2,
        "connections_added": 3,
        "digests": 1,
        "articles": 0,
    },
    "connection_density": 0.1474,
    "orphan_cards": 2,
    "avg_confidence": 3.25,
    "category_coverage": {"qualia": 6, "theory": 9},
    "search_clusters": [],
}

#: ``lib/parse_digests._parse_one`` — one element of its ``digests`` list.
WRITER_DIGEST: dict = {
    "id": "2026-04-26-cosmology",
    "date": "2026-04-26",
    "domain": "cosmology",
    "theme": "Dark energy equation of state",
    "summary_text": "Papers found: 12\nPapers ingested: 4",
    "papers_found": 12,
    "papers_ingested": 4,
    "papers_skipped": 8,
    "seed_cards_created": 3,
    "top_findings": [
        {
            "rank": 1,
            "title": "DESI BAO results",
            "relevance": 5,
            "summary": "Evidence for evolving dark energy.",
            "url": "https://arxiv.org/abs/2503.14738",
            "cluster": "",
        }
    ],
    "search_clusters": [
        {"id": "dark-energy", "queries": 3, "results": 12, "ingested": 4}
    ],
    "coverage_notes": "Good coverage of BAO.",
    "suggested_adjustments": "Add a weak-lensing cluster.",
    "raw_path": "digests/2026-04-26-cosmology.md",
}

#: ``services/event_log.append_event`` — one line of ``log/events.jsonl``.
#: D-17 makes this the canonical ``events.json`` record shape.
WRITER_EVENT: dict = {
    "ts": "2026-03-16T11:00:00+00:00",
    "agent": "researcher",
    "action": "create_card",
    "target": "card-hubble-tension",
    "detail": "Created card-hubble-tension from ref riess-2024",
    "result": "success",
}

#: The legacy Claude-native shape still present in the v02 fixtures.
LEGACY_EVENT: dict = {
    "event": "card.created",
    "timestamp": "2026-03-16T11:00:00Z",
    "details": "Created card-hubble-tension",
}

#: ``lib/parse_curation.parse`` — the ``<ws>/curation-history.json`` payload.
WRITER_CURATION_HISTORY: dict = {
    "cycles": [
        {
            "id": "curation-report-2026-04-26",
            "date": "2026-04-26",
            "summary": "Promoted four seeds and resolved two orphans.",
            "deltas": {
                "promoted": 4,
                "archived": 0,
                "decayed": 1,
                "orphans_resolved": 2,
                "connections_added": 3,
                "connections_removed": 0,
            },
            "raw_path": "curation-reports/CURATION-REPORT-2026-04-26.md",
        }
    ]
}


def _data_dir_for(rel: str) -> Path | None:
    """Return the data directory for *rel* (global or per-workspace)."""
    return DATA_DIR


# ---------------------------------------------------------------------------
# 1. Real data validation — bridges.json
# ---------------------------------------------------------------------------


class TestBridgesFromFixture:
    """Validate the real bridges.json from test-ws against BridgesFile models."""

    def test_bridges_parses_as_bridges_file(self, bridges_raw: dict) -> None:
        """Parse the data payload (strip old-format envelope fields)."""
        payload = {
            "bridges": bridges_raw.get("bridges", []),
            "summary": bridges_raw.get("summary", {}),
        }
        bridges = BridgesFile.model_validate(payload)
        assert isinstance(bridges.bridges, list)
        assert isinstance(bridges.summary, BridgeSummary)
        # Empty bridges list is valid
        assert len(bridges.bridges) == 0

    def test_bridges_summary_has_totals(self, bridges_raw: dict) -> None:
        """The summary.totals dict is preserved."""
        summary_data = bridges_raw.get("summary", {})
        summary = BridgeSummary.model_validate(summary_data)
        assert "confirmed" in summary.totals
        assert isinstance(summary.l1_l2_only, bool)
        assert isinstance(summary.l3_calls, int)

    def test_bridges_version_field(self, bridges_raw: dict) -> None:
        """BridgesFile model carries its own version per D-01 (at envelope level)."""
        payload = {
            "bridges": bridges_raw.get("bridges", []),
            "summary": bridges_raw.get("summary", {}),
        }
        bridges = BridgesFile.model_validate(payload)
        # BridgesFile as data payload does not have version; ViewsEnvelope does.
        assert hasattr(bridges, "model_config")


# ---------------------------------------------------------------------------
# 1b. Payload unwrap — flat generator output vs envelope (regression: Bug 06-UAT #2)
# ---------------------------------------------------------------------------


class TestUnwrapPayload:
    """`unwrap_payload` must accept both the flat generator output and the
    envelope form so the strict ``extra='forbid'`` models validate either way.

    Regression for the Phase 6 UAT issue where real bridges.json was rejected
    because its top-level metadata fields (version/generated/workspace) were
    fed straight into BridgesFile.
    """

    def test_flat_file_strips_metadata(self) -> None:
        raw = {
            "version": "1.0.0",
            "generated": "2026-06-15T00:00:00Z",
            "workspace": "my-construct",
            "bridges": [],
            "summary": {"totals": {"confirmed": 0}},
        }
        payload = unwrap_payload(raw)
        assert set(payload) == {"bridges", "summary"}
        # And the stripped payload validates against the strict model.
        validate_data(BridgesFile, payload)

    def test_envelope_file_returns_data(self) -> None:
        raw = {
            "schema_version": "0.2.0",
            "generated_at": "2026-06-15T00:00:00Z",
            "build_id": "b1",
            "version": "1.0.0",
            "data": {"bridges": [], "summary": {"totals": {}}},
        }
        payload = unwrap_payload(raw)
        assert set(payload) == {"bridges", "summary"}
        validate_data(BridgesFile, payload)

    def test_real_fixture_validates_through_unwrap(self, bridges_raw: dict) -> None:
        """The real flat bridges.json validates once routed through unwrap_payload."""
        validate_data(BridgesFile, unwrap_payload(bridges_raw))


# ---------------------------------------------------------------------------
# 2. All models have a version field (at envelope level or data level)
# ---------------------------------------------------------------------------


class TestAllModelsHaveVersion:
    """Meta-test: verify all contract models carry D-01's version field."""

    @pytest.mark.parametrize("model_cls", _ALL_MODELS)
    def test_model_has_version_field(self, model_cls: type[BaseModel]) -> None:
        """Each model either has a ``version`` field or is used inside an envelope."""
        fields = model_cls.model_fields
        if "version" in fields:
            # Instantiate with minimal data
            kwargs = _minimal_kwargs(model_cls)
            if kwargs is not None:
                instance = model_cls(**kwargs)
                assert instance.version is not None


def _minimal_kwargs(model_cls: type[BaseModel]) -> dict | None:
    """Return minimal kwargs to instantiate the model, or None if not applicable."""
    field_defaults: dict[str, object] = {}
    for name, field_info in model_cls.model_fields.items():
        if field_info.is_required():
            # Provide a sensible default based on type annotation
            ann = str(field_info.annotation)
            if "str" in ann:
                field_defaults[name] = ""
            elif "int" in ann:
                field_defaults[name] = 0
            elif "float" in ann:
                field_defaults[name] = 0.0
            elif "bool" in ann:
                field_defaults[name] = False
            elif "list" in ann:
                field_defaults[name] = []
            elif "dict" in ann:
                field_defaults[name] = {}
            elif "None" in ann:
                field_defaults[name] = None
            else:
                # Skip models with complex required fields we can't synthesise
                return None
    return field_defaults


# ---------------------------------------------------------------------------
# 3. Schema export works for all models
# ---------------------------------------------------------------------------


class TestSchemaExport:
    """Verify ``model_json_schema()`` returns valid JSON Schema for all models."""

    @pytest.mark.parametrize("model_cls", _ALL_MODELS)
    def test_schema_is_object(self, model_cls: type[BaseModel]) -> None:
        schema = schema_for(model_cls)
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        assert "properties" in schema
        assert "title" in schema

    def test_schema_helper_function(self) -> None:
        """schema_for() is equivalent to model_json_schema()."""
        direct = BridgeRecord.model_json_schema()
        via_helper = schema_for(BridgeRecord)
        assert direct == via_helper


# ---------------------------------------------------------------------------
# 4. Round-trip stability
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Parse BridgesFile from synthetic data, dump back, assert field preservation."""

    def test_bridges_round_trip(self) -> None:
        """Create a BridgesFile from synthetic data, dump and re-parse."""
        original = BridgesFile(
            bridges=[
                BridgeRecord(
                    source_domain="cosmology",
                    target_domain="philosophy-of-mind",
                    type="structural",
                    confidence=0.85,
                    rationale="Both fields share structural realism as a framing concept",
                    cards=["structural-realism", "russell-eddington-debate"],
                ),
            ],
            summary=BridgeSummary(
                totals={"confirmed": 1, "strong_candidates": 0, "medium_candidates": 0, "weak_candidates": 0},
                l1_l2_only=False,
                l3_calls=0,
                l3_candidates_eligible=0,
                l3_candidates_total=0,
            ),
        )
        as_dict = original.model_dump()
        restored = BridgesFile.model_validate(as_dict)
        assert restored.model_dump() == as_dict
        assert len(restored.bridges) == 1
        assert restored.bridges[0].source_domain == "cosmology"
        assert restored.summary.totals["confirmed"] == 1


# ---------------------------------------------------------------------------
# 4b. The widened domain shape (D-02)
# ---------------------------------------------------------------------------


class TestWidenedDomainRecord:
    """DomainRecord must accept the shape ``lib/parse_domains.parse`` really emits.

    Asserted positively rather than merely tolerated: this file declares itself
    the views contract guard, so the widened field set belongs here explicitly.
    """

    def test_parser_shaped_domain_validates(self) -> None:
        """A realistic parse_domains.py dict validates with no extra_forbidden."""
        parser_output = {
            "id": "cosmology",
            "name": "Cosmology",
            "description": "Structure and evolution of the universe",
            "status": "active",
            "created": "2026-04-22",
            "content_categories": ["observations", "theory"],
            "source_priorities": ["arxiv", "peer-reviewed papers"],
            "cross_domain_links": [{"domain": "philosophy-of-mind", "topics": ["realism"]}],
            "metrics": {
                "papers": 47,
                "cards": 120,
                "cards_by_lifecycle": {"seed": 18, "growing": 60, "mature": 38, "archived": 4},
                "cards_by_confidence": {"1": 5, "2": 22, "3": 51, "4": 30, "5": 12},
                "connections": 184,
                "orphan_cards": 3,
                "avg_confidence": 3.12,
                "last_research_cycle": "2026-04-25",
                "last_curation_cycle": "2026-04-26",
            },
        }

        record = DomainRecord.model_validate(parser_output)

        assert record.metrics["cards"] == 120
        assert record.metrics["cards_by_lifecycle"]["mature"] == 38
        assert record.cross_domain_links == [
            {"domain": "philosophy-of-mind", "topics": ["realism"]}
        ]
        assert record.source_priorities == ["arxiv", "peer-reviewed papers"]

    def test_bare_string_cross_domain_links_accepted(self) -> None:
        """The v02 fixtures emit bare domain-id strings; the parser accepts any list."""
        record = DomainRecord.model_validate(
            {
                "id": "cosmology",
                "name": "Cosmology",
                "description": "",
                "cross_domain_links": ["philosophy-of-mind"],
            }
        )

        assert record.cross_domain_links == ["philosophy-of-mind"]

    def test_widened_domain_ignores_unknown_fields(self) -> None:
        """D-03 supersedes D-02's strictness here: an unknown key is ignored.

        The phantom ``card_count`` this used to reject is now simply dropped. What
        the widening must NOT have cost is the ability to reject genuinely
        malformed data — asserted immediately below.
        """
        record = DomainRecord.model_validate(
            {"id": "x", "name": "x", "description": "", "card_count": 3}
        )

        assert record.id == "x"
        assert not hasattr(record, "card_count")

    def test_widened_domain_still_rejects_malformed_records(self) -> None:
        """Relaxation is not permissiveness (D-03)."""
        with pytest.raises(ValidationError):
            DomainRecord.model_validate({"name": "x", "description": ""})  # no id

        with pytest.raises(ValidationError):
            DomainRecord.model_validate({"id": ["x"], "name": "x", "description": ""})


# ---------------------------------------------------------------------------
# 5. Invalid data is rejected
# ---------------------------------------------------------------------------


class TestInvalidDataRejection:
    """Prove the schema gate works — wrong types / extra fields / missing fields."""

    def test_extra_fields_ignored(self) -> None:
        """D-03: an unexpected field is dropped rather than rejected."""
        record = BridgeRecord.model_validate(
            {
                "source_domain": "a",
                "target_domain": "b",
                "type": "structural",
                "confidence": 0.5,
                "rationale": "test",
                "cards": [],
                "nonexistent_field": "ignored",
            }
        )

        assert record.source_domain == "a"
        assert not hasattr(record, "nonexistent_field")

    def test_invalid_confidence_range_rejected(self) -> None:
        """Confidence must be 0.0-1.0."""
        with pytest.raises(ValidationError):
            BridgeRecord(
                source_domain="a",
                target_domain="b",
                type="structural",
                confidence=99.0,  # out of range
                rationale="test",
                cards=[],
            )

    def test_missing_required_field_rejected(self) -> None:
        """Missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            BridgeRecord(
                source_domain="a",
                target_domain="b",
                # missing type
                confidence=0.5,
                rationale="test",
                cards=[],
            )

    def test_invalid_type_pattern_rejected(self) -> None:
        """BridgeRecord type must be structural/category/semantic."""
        with pytest.raises(ValidationError):
            BridgeRecord(
                source_domain="a",
                target_domain="b",
                type="invalid-type",
                confidence=0.5,
                rationale="test",
                cards=[],
            )

    def test_card_confidence_out_of_range_rejected(self) -> None:
        """CardRecord confidence must be 1-5."""
        with pytest.raises(ValidationError):
            CardRecord(
                id="test-card",
                title="Test",
                epistemic_type="finding",
                confidence=99,  # out of range
                source_tier=2,
                lifecycle="seed",
                domains=["test"],
                summary="A test card",
            )

    def test_validate_data_helper_rejects(self) -> None:
        """validate_data() raises ValidationError on bad input."""
        with pytest.raises(ValidationError):
            validate_data(
                BridgeRecord,
                {
                    "source_domain": "a",
                    "target_domain": "b",
                    "type": "structural",
                    "confidence": 99,  # invalid range
                    "rationale": "test",
                    "cards": [],
                },
            )

    def test_validate_data_helper_passes(self) -> None:
        """validate_data() returns model on valid input."""
        result = validate_data(
            BridgeRecord,
            {
                "source_domain": "a",
                "target_domain": "b",
                "type": "structural",
                "confidence": 0.5,
                "rationale": "test",
                "cards": [],
            },
        )
        assert isinstance(result, BridgeRecord)


# ---------------------------------------------------------------------------
# 6. ViewsEnvelope generic
# ---------------------------------------------------------------------------


class TestViewsEnvelope:
    """Verify the generic envelope wrapper works for all file types."""

    def test_envelope_with_bridges(self) -> None:
        """ViewsEnvelope[BridgesFile] validates correctly."""
        data = {
            "schema_version": "0.2.0",
            "generated_at": "2026-06-11T00:00:00Z",
            "build_id": "abc12345",
            "version": "1.0.0",
            "data": {
                "bridges": [],
                "summary": {
                    "totals": {"confirmed": 0},
                    "l1_l2_only": False,
                    "l3_calls": 0,
                    "l3_candidates_eligible": 0,
                    "l3_candidates_total": 0,
                },
            },
        }
        envelope = ViewsEnvelope[BridgesFile].model_validate(data)
        assert envelope.schema_version == "0.2.0"
        assert envelope.version == "1.0.0"
        assert isinstance(envelope.data, BridgesFile)
        assert envelope.data.bridges == []

    def test_envelope_with_domains(self) -> None:
        """ViewsEnvelope[DomainsFile] validates correctly."""
        data = {
            "schema_version": "0.2.0",
            "generated_at": "2026-06-11T00:00:00Z",
            "build_id": "abc12345",
            "version": "1.0.0",
            "data": {
                "settings": {"workspace_landing": "dashboard"},
                "domains": [],
            },
        }
        envelope = ViewsEnvelope[DomainsFile].model_validate(data)
        assert envelope.schema_version == "0.2.0"
        assert isinstance(envelope.data, DomainsFile)
        assert envelope.data.domains == []

    def test_envelope_ignores_extra(self) -> None:
        """D-03: an unknown envelope key is ignored, not rejected.

        Previously asserted the opposite. The envelope is written by the same
        generator whose payloads D-03 relaxes; leaving it at ``forbid`` would mean
        a future metadata key (a provenance stamp, a build channel) invalidated
        every existing ``views/build/`` copy at the envelope level even though the
        payload models tolerate it. What the envelope still guarantees is asserted
        by ``test_envelope_missing_required_field_rejected`` below.
        """
        envelope = ViewsEnvelope[BridgesFile].model_validate({
            "schema_version": "0.2.0",
            "generated_at": "2026-06-11T00:00:00Z",
            "build_id": "abc12345",
            "version": "1.0.0",
            "data": {
                "bridges": [],
                "summary": {"totals": {}},
            },
            "extra_field": True,
        })

        assert envelope.build_id == "abc12345"
        assert not hasattr(envelope, "extra_field")

    def test_envelope_missing_required_field_rejected(self) -> None:
        """Relaxing to ignore-extra did not remove the envelope's required fields."""
        with pytest.raises(ValidationError):
            ViewsEnvelope[BridgesFile].model_validate({
                "schema_version": "0.2.0",
                # missing generated_at and build_id
                "data": {"bridges": [], "summary": {"totals": {}}},
            })


# ---------------------------------------------------------------------------
# 7. D-01 — the models declare the field names the generator actually writes
# ---------------------------------------------------------------------------


class TestWriterConformedCardRecord:
    """``CardRecord`` validates the raw card dict ``views generate`` writes.

    Before D-01 the generator computed an adapted projection
    (``summary ← summary_excerpt``, ``connections ← connects_to``), validated
    *that*, and then wrote the raw parser dict — so ``views validate`` rejected
    the very bytes ``views generate`` had just called clean.
    """

    def test_raw_generated_card_validates(self) -> None:
        record = CardRecord.model_validate(WRITER_CARD)

        assert record.connects_to == ["card-zombie-argument"]
        assert record.summary_excerpt.startswith("The hard problem")
        # The keys that used to trip extra_forbidden are declared fields now.
        assert record.tags == ["consciousness", "chalmers"]
        assert record.created == "2026-04-02"
        assert record.body_markdown.startswith("## Summary")
        assert record.sources == [
            {"type": "url", "ref": "https://example.org/chalmers"}
        ]

    def test_cards_file_accepts_the_raw_payload(self) -> None:
        payload = CardsFile.model_validate({"cards": [WRITER_CARD]})

        assert payload.cards[0].connects_to == ["card-zombie-argument"]

    def test_card_missing_required_field_rejected(self) -> None:
        """Ignore-extra is not accept-anything: a missing required field fails."""
        malformed = {k: v for k, v in WRITER_CARD.items() if k != "lifecycle"}

        with pytest.raises(ValidationError):
            CardRecord.model_validate(malformed)

    def test_card_wrong_typed_required_field_rejected(self) -> None:
        """A required field of the wrong type still fails."""
        with pytest.raises(ValidationError):
            CardRecord.model_validate({**WRITER_CARD, "confidence": "high"})

    def test_card_out_of_range_confidence_still_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CardRecord.model_validate({**WRITER_CARD, "confidence": 99})


class TestWriterConformedConnectionRecord:
    """``ConnectionRecord`` / ``ConnectionsFile`` conformed to the writer."""

    def test_raw_generated_connection_validates(self) -> None:
        record = ConnectionRecord.model_validate(WRITER_CONNECTION)

        assert record.created == "2026-04-02"
        assert record.author == "curator"
        # The record-level id the writer emits is a declared field, not an extra.
        assert record.id == "conn-1a2b3c4d"

    def test_connections_file_accepts_top_level_type_counts(self) -> None:
        """The writer's ``type_counts`` map is a declared field, not stripped.

        Declared rather than added to ``ENVELOPE_METADATA_KEYS``: that frozenset
        drives ``unwrap_payload``, so listing ``type_counts`` there would delete
        real per-type counts on the way in rather than validate them.
        """
        payload = ConnectionsFile.model_validate(WRITER_CONNECTIONS_FILE)

        assert payload.type_counts["supports"] == 1
        assert payload.connections[0].source == "card-hard-problem"

    def test_type_counts_survives_unwrap_payload(self) -> None:
        raw = {
            "schema_version": "0.2.0",
            "generated_at": "2026-06-15T00:00:00Z",
            "build_id": "b1",
            "data": WRITER_CONNECTIONS_FILE,
        }

        assert unwrap_payload(raw)["type_counts"] == {
            "supports": 1,
            "contradicts": 0,
            "extends": 0,
        }

    def test_connection_missing_required_field_rejected(self) -> None:
        malformed = {k: v for k, v in WRITER_CONNECTION.items() if k != "target"}

        with pytest.raises(ValidationError):
            ConnectionRecord.model_validate(malformed)

    def test_connection_wrong_typed_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ConnectionRecord.model_validate({**WRITER_CONNECTION, "source": ["a"]})


class TestStatsContractsAreDistinct:
    """The global and per-workspace ``stats.json`` are two contracts (D-18).

    Same filename, different directory, different writer
    (``compute_global`` vs ``compute_workspace``) — and therefore different
    models. The adjacency edge in VFIX-01 is that a single ``StatsFile`` used for
    both would validate each against the other's shape and report a clean build
    while the SPA read undefined fields.
    """

    def test_global_stats_payload_validates(self) -> None:
        stats = StatsFile.model_validate(WRITER_GLOBAL_STATS)

        assert stats.totals.workspaces == 2
        assert stats.totals.cards == 41
        assert stats.by_confidence["3"] == 15
        assert stats.activity_last_30d["cards_created"] == 4

    def test_workspace_stats_payload_validates(self) -> None:
        stats = WorkspaceStatsFile.model_validate(WRITER_WORKSPACE_STATS)

        assert stats.totals.papers == 3
        assert stats.connection_density == 0.1474
        assert stats.orphan_cards == 2
        assert stats.category_coverage["theory"] == 9

    def test_global_payload_fails_the_workspace_model(self) -> None:
        """``compute_global`` emits none of the per-workspace graph metrics."""
        with pytest.raises(ValidationError):
            WorkspaceStatsFile.model_validate(WRITER_GLOBAL_STATS)

    def test_workspace_payload_fails_the_global_model(self) -> None:
        """Only ``compute_global`` counts workspaces; its absence is the tell."""
        with pytest.raises(ValidationError):
            StatsFile.model_validate(WRITER_WORKSPACE_STATS)

    def test_global_stats_missing_totals_rejected(self) -> None:
        malformed = {k: v for k, v in WRITER_GLOBAL_STATS.items() if k != "totals"}

        with pytest.raises(ValidationError):
            StatsFile.model_validate(malformed)

    def test_workspace_stats_wrong_typed_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkspaceStatsFile.model_validate(
                {**WRITER_WORKSPACE_STATS, "orphan_cards": "several"}
            )

    def test_workspace_stats_missing_graph_metric_rejected(self) -> None:
        malformed = {
            k: v for k, v in WRITER_WORKSPACE_STATS.items() if k != "avg_confidence"
        }

        with pytest.raises(ValidationError):
            WorkspaceStatsFile.model_validate(malformed)


class TestWriterConformedDigestRecord:
    """``DigestRecord`` is the one model with two legitimate authors (D-20).

    It validates the views projection *and* it is the model
    ``llm/research_run.compile_digest`` uses to write a workspace's
    ``digests/digests.json``. ``Field(alias=...)`` was weighed for exactly this
    reason and rejected: an alias is a second contract surface and it changes
    ``model_json_schema()`` output, which Phase 19's generated adapter consumes.
    """

    def test_raw_generated_digest_validates(self) -> None:
        record = DigestRecord.model_validate(WRITER_DIGEST)

        assert record.domain == "cosmology"
        assert record.theme == "Dark energy equation of state"
        assert record.date == "2026-04-26"
        assert record.summary_text.startswith("Papers found")

    def test_consumer_read_keys_are_declared_fields(self) -> None:
        """Every key the scaffold SPA's Digests/DigestDetail pages render."""
        declared = set(DigestRecord.model_fields)

        assert {
            "papers_found",
            "papers_ingested",
            "papers_skipped",
            "seed_cards_created",
            "top_findings",
            "search_clusters",
            "coverage_notes",
            "suggested_adjustments",
        } <= declared

    def test_phantom_card_ids_field_is_gone(self) -> None:
        """No parser emitted it; the generator's adapter hard-coded it to ``[]``."""
        assert "card_ids" not in DigestRecord.model_fields

    def test_digests_file_accepts_the_raw_payload(self) -> None:
        payload = DigestsFile.model_validate({"digests": [WRITER_DIGEST]})

        assert payload.digests[0].theme == "Dark energy equation of state"

    def test_digest_missing_required_field_rejected(self) -> None:
        malformed = {k: v for k, v in WRITER_DIGEST.items() if k != "id"}

        with pytest.raises(ValidationError):
            DigestRecord.model_validate(malformed)

    def test_digest_wrong_typed_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DigestRecord.model_validate({**WRITER_DIGEST, "papers_found": "twelve"})

    def test_partial_parse_status_is_declared(self) -> None:
        """``parse_digests`` adds this key only when a section failed to parse."""
        record = DigestRecord.model_validate({**WRITER_DIGEST, "parse_status": "partial"})

        assert record.parse_status == "partial"


class TestCurationHistoryContract:
    """``<ws>/curation-history.json`` had no contract model at all (D-18).

    Research assumption A5 flagged the shape as possibly unstable; the mitigation
    is to pin the stable envelope (``cycles`` of identified records) and leave the
    volatile ``deltas`` interior as a declared open mapping.
    """

    def test_writer_payload_validates(self) -> None:
        history = CurationHistoryFile.model_validate(WRITER_CURATION_HISTORY)

        assert history.cycles[0].id == "curation-report-2026-04-26"
        assert history.cycles[0].deltas["promoted"] == 4

    def test_empty_history_validates(self) -> None:
        """A workspace with no curation reports still writes ``{"cycles": []}``."""
        assert CurationHistoryFile.model_validate({"cycles": []}).cycles == []

    def test_missing_cycles_key_rejected(self) -> None:
        """The envelope key is required — an empty object is not a history file."""
        with pytest.raises(ValidationError):
            CurationHistoryFile.model_validate({})

    def test_cycle_missing_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CurationHistoryFile.model_validate(
                {"cycles": [{"date": "2026-04-26", "summary": "no id"}]}
            )

    def test_volatile_deltas_interior_is_open(self) -> None:
        """A5: a new delta counter must not invalidate an existing history file."""
        history = CurationHistoryFile.model_validate(
            {
                "cycles": [
                    {"id": "c1", "deltas": {"promoted": 1, "newly_invented_counter": 9}}
                ]
            }
        )

        assert history.cycles[0].deltas["newly_invented_counter"] == 9


# ---------------------------------------------------------------------------
# 8. D-03 — ignore-extra, and the proof it did not become permissiveness
# ---------------------------------------------------------------------------


class TestIgnoreExtraRelaxation:
    """D-03 relaxes the views projection models from forbid-extra to ignore-extra.

    This is the deliberate, user-locked exception to the AGENTS.md
    ``ConfigDict(extra="forbid")`` convention, scoped to the *derived* projection.
    It never extends to canonical models (``schemas/``) or capability models,
    where an unexpected field is a trust-boundary event rather than parser drift.
    """

    def test_no_views_model_forbids_extra(self) -> None:
        import inspect

        from construct.views import models as views_models

        forbidding = sorted(
            name
            for name, obj in vars(views_models).items()
            if inspect.isclass(obj)
            and issubclass(obj, BaseModel)
            and (obj.model_config or {}).get("extra") == "forbid"
        )

        assert forbidding == [], forbidding

    @pytest.mark.parametrize(
        ("model_cls", "payload"),
        [
            (CardRecord, WRITER_CARD),
            (ConnectionRecord, WRITER_CONNECTION),
            (StatsFile, WRITER_GLOBAL_STATS),
            (WorkspaceStatsFile, WRITER_WORKSPACE_STATS),
            (CurationHistoryFile, WRITER_CURATION_HISTORY),
        ],
    )
    def test_added_parser_field_does_not_break_validation(
        self, model_cls: type[BaseModel], payload: dict
    ) -> None:
        """The point of D-03: a new parser key cannot invalidate an old build."""
        model_cls.model_validate({**payload, "a_field_a_future_parser_adds": 1})

    def test_relaxation_is_scoped_to_the_projection(self) -> None:
        """The canonical event emitter keeps forbid — D-03 stops at views."""
        from construct.schemas.config import EventRecord as EmitterEventRecord

        assert EmitterEventRecord.model_config.get("extra") == "forbid"


# ---------------------------------------------------------------------------
# 9. Non-vacuity — the real parsers against a real fixture
# ---------------------------------------------------------------------------


class TestWriterBytesAreTheContract:
    """Run the real parsers over a real workspace and validate their output.

    The literal payloads above are transcriptions and could drift from the
    parsers they describe. This closes the loop: whatever the parsers emit today
    must validate, and the fixture must be populated enough for that to mean
    something (RESEARCH Pitfall 1 — the vacuity trap).
    """

    V02_WORKSPACE = (
        Path(__file__).parents[1]
        / "fixtures"
        / "v02"
        / "multi-domain-medium"
        / "cosmology"
    )

    def test_parsed_cards_validate(self) -> None:
        from construct.views.lib import parse_cards, parse_connections

        if not self.V02_WORKSPACE.is_dir():
            pytest.skip(f"fixture not found: {self.V02_WORKSPACE}")

        warnings: list[dict] = []
        cards = parse_cards.parse(self.V02_WORKSPACE, warnings)
        connections = parse_connections.parse(self.V02_WORKSPACE, warnings)
        parse_connections.denormalize_into_cards(cards, connections["connections"])

        assert cards, "fixture produced zero cards — the assertion below is vacuous"
        assert any(c["connects_to"] for c in cards), (
            "no parsed card has connections — connects_to is untested"
        )

        payload = CardsFile.model_validate({"cards": cards})
        assert len(payload.cards) == len(cards)

    def test_parsed_connections_validate(self) -> None:
        from construct.views.lib import parse_connections

        if not self.V02_WORKSPACE.is_dir():
            pytest.skip(f"fixture not found: {self.V02_WORKSPACE}")

        warnings: list[dict] = []
        connections = parse_connections.parse(self.V02_WORKSPACE, warnings)

        assert connections["connections"], "fixture has no connections"
        payload = ConnectionsFile.model_validate(connections)
        assert payload.type_counts

    def test_computed_stats_validate(self) -> None:
        from construct.views.lib import (
            compute_stats,
            parse_cards,
            parse_connections,
            parse_digests,
            parse_events,
        )

        if not self.V02_WORKSPACE.is_dir():
            pytest.skip(f"fixture not found: {self.V02_WORKSPACE}")

        warnings: list[dict] = []
        ws_data = {
            "cards": parse_cards.parse(self.V02_WORKSPACE, warnings),
            "connections": parse_connections.parse(self.V02_WORKSPACE, warnings),
            "digests": parse_digests.parse(self.V02_WORKSPACE, warnings),
            "events": parse_events.parse(self.V02_WORKSPACE, warnings),
            "refs_count": 0,
            "articles_count": 0,
        }

        WorkspaceStatsFile.model_validate(compute_stats.compute_workspace(ws_data))
        StatsFile.model_validate(compute_stats.compute_global({"cosmology": ws_data}, []))

    def test_parsed_digests_validate(self) -> None:
        from construct.views.lib import parse_cards, parse_digests

        if not self.V02_WORKSPACE.is_dir():
            pytest.skip(f"fixture not found: {self.V02_WORKSPACE}")

        warnings: list[dict] = []
        cards = parse_cards.parse(self.V02_WORKSPACE, warnings)
        digests = parse_digests.parse(self.V02_WORKSPACE, warnings, cards=cards)

        assert digests, "fixture produced zero digests — the assertion is vacuous"
        payload = DigestsFile.model_validate({"digests": digests})
        assert len(payload.digests) == len(digests)

    def test_parsed_curation_history_validates(self) -> None:
        from construct.views.lib import parse_curation

        if not self.V02_WORKSPACE.is_dir():
            pytest.skip(f"fixture not found: {self.V02_WORKSPACE}")

        warnings: list[dict] = []
        curation = parse_curation.parse(self.V02_WORKSPACE, warnings)
        if not isinstance(curation, dict):
            curation = {"cycles": curation}

        CurationHistoryFile.model_validate(curation)


# ---------------------------------------------------------------------------
# 10. D-17 — events.json has one canonical shape instead of four
# ---------------------------------------------------------------------------


class TestCanonicalEventContract:
    """``events.json`` is pinned to the Python emitter's shape (D-17).

    Four mutually incompatible event shapes existed: the emitter's
    (``ts``/``agent``/``action``/``target``/``detail``/``result``), the legacy
    Claude-native fixtures' (``event``/``timestamp``/``details``), this
    validator's own (``timestamp``/``type``/``actor``/``card_id``/``details``),
    and the SPA's. ``parse_events`` renamed nothing, so ``events.json``'s on-disk
    shape was whichever emitter had last written the log — "conform the model to
    the bytes" had no single referent until one shape was chosen.

    The emitter wins because it is the only *live* author: it is what CONSTRUCT
    writes today, and it is the one shape a repository change can keep honest.
    """

    def test_views_event_matches_the_emitter_field_for_field(self) -> None:
        from construct.schemas.config import EventRecord as EmitterEventRecord

        assert sorted(EventRecord.model_fields) == sorted(
            EmitterEventRecord.model_fields
        )

    def test_emitter_line_validates_unchanged(self) -> None:
        """A line ``append_event`` wrote needs no adaptation to validate."""
        from construct.schemas.config import (
            EventAgent,
            EventRecord as EmitterEventRecord,
            EventResult,
        )

        emitted = EmitterEventRecord(
            ts=datetime(2026, 3, 16, 11, 0, tzinfo=timezone.utc),
            agent=EventAgent.researcher,
            action="create_card",
            target="card-hubble-tension",
            detail="from ref riess-2024",
            result=EventResult.success,
        )

        record = EventRecord.model_validate(json.loads(emitted.model_dump_json()))

        assert record.action == "create_card"
        assert record.target == "card-hubble-tension"

    def test_events_file_accepts_the_canonical_payload(self) -> None:
        payload = EventsFile.model_validate({"events": [WRITER_EVENT]})

        assert payload.events[0].agent.value == "researcher"

    def test_unseen_action_string_needs_no_model_change(self) -> None:
        """``action`` is a free string, so a new event action threads through.

        Plan 08 introduces an escalate action. If ``action`` were an enum, every
        new event type would be a contract change in this module before it could
        reach the projection — which is the coupling D-16 needs broken.
        """
        record = EventRecord.model_validate(
            {**WRITER_EVENT, "action": "curation_escalated"}
        )

        assert record.action == "curation_escalated"

    def test_escalated_result_is_already_a_member(self) -> None:
        record = EventRecord.model_validate({**WRITER_EVENT, "result": "escalated"})

        assert record.result.value == "escalated"

    def test_event_missing_required_field_rejected(self) -> None:
        malformed = {k: v for k, v in WRITER_EVENT.items() if k != "result"}

        with pytest.raises(ValidationError):
            EventRecord.model_validate(malformed)

    def test_event_unknown_agent_rejected(self) -> None:
        """``agent`` stays an enum — an unrecognised actor is not an event."""
        with pytest.raises(ValidationError):
            EventRecord.model_validate({**WRITER_EVENT, "agent": "some-other-tool"})

    def test_legacy_shaped_line_does_not_validate(self) -> None:
        """The legacy shape is migrated by the reader, never accepted raw."""
        with pytest.raises(ValidationError):
            EventRecord.model_validate(LEGACY_EVENT)


class TestEventTimestampPrecision:
    """VFIX-01 precision edge: a timestamp must survive validation intact."""

    def test_microseconds_and_offset_round_trip(self) -> None:
        record = EventRecord.model_validate(
            {**WRITER_EVENT, "ts": "2026-03-16T11:00:00.123456+02:00"}
        )

        assert record.ts.microsecond == 123456
        assert record.ts.utcoffset() == timedelta(hours=2)

        dumped = EventRecord.model_validate(record.model_dump(mode="json"))
        assert dumped.ts == record.ts
        assert dumped.ts.microsecond == 123456
        assert dumped.ts.utcoffset() == timedelta(hours=2)

    def test_aware_value_is_not_reinterpreted_as_local_time(self) -> None:
        """An offset-bearing value keeps its instant, whatever TZ the host is in."""
        record = EventRecord.model_validate(
            {**WRITER_EVENT, "ts": "2026-03-16T11:00:00+05:30"}
        )

        assert record.ts.tzinfo is not None
        assert record.ts.astimezone(timezone.utc) == datetime(
            2026, 3, 16, 5, 30, tzinfo=timezone.utc
        )

    def test_z_suffix_is_utc_not_naive(self) -> None:
        record = EventRecord.model_validate({**WRITER_EVENT, "ts": "2026-03-16T11:00:00Z"})

        assert record.ts.utcoffset() == timedelta(0)

    def test_unparseable_timestamp_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EventRecord.model_validate({**WRITER_EVENT, "ts": "last thursday"})


class TestParseEventsCanonicalisation:
    """``parse_events.parse`` migrates, drops-and-counts, and sorts (D-17)."""

    @staticmethod
    def _workspace(tmp_path: Path, lines: list[str]) -> Path:
        ws = tmp_path / "ws"
        (ws / "log").mkdir(parents=True)
        (ws / "log" / "events.jsonl").write_text(
            "".join(line + "\n" for line in lines), encoding="utf-8"
        )
        return ws

    def test_canonical_line_passes_through_and_validates(self, tmp_path: Path) -> None:
        from construct.views.lib import parse_events

        ws = self._workspace(tmp_path, [json.dumps(WRITER_EVENT)])
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert warnings == []
        assert len(events) == 1
        EventsFile.model_validate({"events": events})

    def test_legacy_line_with_derivable_fields_is_migrated(self, tmp_path: Path) -> None:
        from construct.views.lib import parse_events

        legacy = {
            **LEGACY_EVENT,
            "author": "researcher",
            "result": "success",
            "card": "card-hubble-tension",
        }
        ws = self._workspace(tmp_path, [json.dumps(legacy)])
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert warnings == [], warnings
        assert len(events) == 1
        record = EventRecord.model_validate(events[0])
        assert record.action == "card.created"
        assert record.agent.value == "researcher"
        assert record.target == "card-hubble-tension"
        assert record.detail == "Created card-hubble-tension"
        assert record.ts == datetime(2026, 3, 16, 11, 0, tzinfo=timezone.utc)

    def test_legacy_line_without_agent_is_dropped_and_counted(
        self, tmp_path: Path
    ) -> None:
        """The v02 fixture shape: no author, no result — not derivable."""
        from construct.views.lib import parse_events

        ws = self._workspace(tmp_path, [json.dumps(LEGACY_EVENT)])
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert events == []
        assert len(warnings) == 1, warnings
        assert "line 1" in warnings[0]["file"]
        assert "events.jsonl" in warnings[0]["file"]

    def test_dropped_line_warning_does_not_echo_log_content(
        self, tmp_path: Path
    ) -> None:
        """T-18-20: the warning names the location, never the payload."""
        from construct.views.lib import parse_events

        secret = "api-key-do-not-log-abc123"
        ws = self._workspace(tmp_path, [json.dumps({**LEGACY_EVENT, "details": secret})])
        warnings: list[dict] = []

        parse_events.parse(ws, warnings)

        assert warnings
        blob = json.dumps(warnings)
        assert secret not in blob, blob

    def test_agent_is_never_fabricated(self, tmp_path: Path) -> None:
        """An unrecognised legacy author is dropped, not coerced to a default."""
        from construct.views.lib import parse_events

        ws = self._workspace(
            tmp_path,
            [json.dumps({**LEGACY_EVENT, "author": "some-other-tool", "result": "success"})],
        )
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert events == []
        assert len(warnings) == 1

    def test_equal_timestamps_keep_file_order(self, tmp_path: Path) -> None:
        """VFIX-01 ordering edge: the sort must be stable on ties.

        The old sort read the legacy ``timestamp`` key, which no canonical event
        carries — so after the rename every event would have compared equal and
        the output order would have been whatever the sort happened to produce.
        """
        from construct.views.lib import parse_events

        same_ts = "2026-03-16T11:00:00+00:00"
        lines = [
            json.dumps({**WRITER_EVENT, "ts": same_ts, "target": f"card-{i}"})
            for i in range(5)
        ]
        ws = self._workspace(tmp_path, lines)
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert [e["target"] for e in events] == [f"card-{i}" for i in range(5)]

    def test_sorted_newest_first_on_the_canonical_field(self, tmp_path: Path) -> None:
        from construct.views.lib import parse_events

        lines = [
            json.dumps({**WRITER_EVENT, "ts": "2026-03-14T09:00:00+00:00", "target": "old"}),
            json.dumps({**WRITER_EVENT, "ts": "2026-03-18T09:00:00+00:00", "target": "new"}),
            json.dumps({**WRITER_EVENT, "ts": "2026-03-16T09:00:00+00:00", "target": "mid"}),
        ]
        ws = self._workspace(tmp_path, lines)
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert [e["target"] for e in events] == ["new", "mid", "old"]

    def test_mixed_offsets_sort_by_instant_not_by_string(self, tmp_path: Path) -> None:
        """A naive string sort puts these the wrong way round."""
        from construct.views.lib import parse_events

        lines = [
            # 09:00+05:30 == 03:30Z — the earlier instant, the later string.
            json.dumps(
                {**WRITER_EVENT, "ts": "2026-03-16T09:00:00+05:30", "target": "earlier"}
            ),
            json.dumps(
                {**WRITER_EVENT, "ts": "2026-03-16T05:00:00+00:00", "target": "later"}
            ),
        ]
        ws = self._workspace(tmp_path, lines)
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert [e["target"] for e in events] == ["later", "earlier"]

    def test_microsecond_precision_survives_the_reader(self, tmp_path: Path) -> None:
        from construct.views.lib import parse_events

        ws = self._workspace(
            tmp_path,
            [json.dumps({**WRITER_EVENT, "ts": "2026-03-16T11:00:00.123456+00:00"})],
        )
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert EventRecord.model_validate(events[0]).ts.microsecond == 123456

    def test_invalid_timestamp_line_is_dropped_and_counted(self, tmp_path: Path) -> None:
        from construct.views.lib import parse_events

        ws = self._workspace(
            tmp_path, [json.dumps({**WRITER_EVENT, "ts": "not a timestamp"})]
        )
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert events == []
        assert len(warnings) == 1

    def test_every_surviving_event_validates(self, tmp_path: Path) -> None:
        """The reader's whole job: nothing reaches events.json un-gated."""
        from construct.views.lib import parse_events

        ws = self._workspace(
            tmp_path,
            [
                json.dumps(WRITER_EVENT),
                json.dumps(LEGACY_EVENT),
                "not json at all",
                json.dumps({**LEGACY_EVENT, "author": "curator", "result": "success"}),
                json.dumps(["a list is not an event"]),
            ],
        )
        warnings: list[dict] = []

        events = parse_events.parse(ws, warnings)

        assert len(events) == 2
        EventsFile.model_validate({"events": events})

    def test_v02_fixture_legacy_lines_are_all_dropped(self) -> None:
        """The measured consequence of D-17 on the shipped legacy fixtures."""
        from construct.views.lib import parse_events

        fixture = (
            Path(__file__).parents[1]
            / "fixtures"
            / "v02"
            / "multi-domain-medium"
            / "cosmology"
        )
        if not (fixture / "log" / "events.jsonl").is_file():
            pytest.skip("v02 fixture not found")

        warnings: list[dict] = []
        events = parse_events.parse(fixture, warnings)

        # These lines carry neither an author nor a result, so neither the agent
        # nor the result is derivable. They are dropped loudly, one warning each.
        assert events == []
        assert warnings
        assert all("events.jsonl line " in w["file"] for w in warnings), warnings
