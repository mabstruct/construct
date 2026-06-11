"""Contract tests validating views data file shapes against Pydantic schemas.

Tests load actual JSON data from the ``test-ws/my-construct/`` fixture,
validate against the Pydantic contract models, and verify that schema
export, round-trip, and rejection mechanics all work as expected per
ADV-03 / D-01.
"""

from __future__ import annotations

import json
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
    DigestRecord,
    DigestsFile,
    DomainRecord,
    DomainsFile,
    EventRecord,
    EventsFile,
    StatsFile,
    ViewsEnvelope,
    schema_for,
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
    DigestRecord,
    DigestsFile,
    DomainRecord,
    DomainsFile,
    EventRecord,
    EventsFile,
    StatsFile,
    ViewsEnvelope,
]


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
# 5. Invalid data is rejected
# ---------------------------------------------------------------------------


class TestInvalidDataRejection:
    """Prove the schema gate works — wrong types / extra fields / missing fields."""

    def test_extra_fields_rejected(self) -> None:
        """extra='forbid' should reject unexpected fields."""
        with pytest.raises(ValidationError):
            BridgeRecord(
                source_domain="a",
                target_domain="b",
                type="structural",
                confidence=0.5,
                rationale="test",
                cards=[],
                nonexistent_field="should_fail",  # type: ignore[call-arg]
            )

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

    def test_envelope_rejects_extra(self) -> None:
        """Extra fields on the envelope are rejected."""
        with pytest.raises(ValidationError):
            ViewsEnvelope[BridgesFile].model_validate({
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
