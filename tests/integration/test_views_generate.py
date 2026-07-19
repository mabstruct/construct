"""Integration tests for the schema-validated views data generator (D-02/D-04).

The done-bar is ``generate()`` returning ``success=True`` with zero validation
errors against a real install root — proven against BOTH a freshly scaffolded
root (zero cards) and a populated one (cards with connections), because a fresh
root never instantiates ``CardRecord.connections`` and would let the connections
defect pass unnoticed (RESEARCH Pitfall 1).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pydantic

from construct.views import models as views_models
from construct.views.generate import generate
from construct.views.models import CardRecord, unwrap_payload

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

# The populated-workspace source. ``multi-domain-medium`` was chosen over
# ``single-domain-small`` because both of its workspaces ship a non-empty
# ``connections.json`` whose endpoints are real card ids, so denormalisation
# produces non-empty ``connects_to`` lists and the CardRecord.connections
# contract is genuinely exercised. No connected cards had to be added.
POPULATED_FIXTURE = FIXTURES_DIR / "v02" / "multi-domain-medium"

# Every model declared in construct.views.models (D-02 strictness guard).
ALL_MODEL_NAMES = [
    "ViewsEnvelope",
    "BridgeRecord",
    "BridgeSummary",
    "BridgesFile",
    "DomainRecord",
    "DomainsFile",
    "ArticleRecord",
    "ArticlesFile",
    "StatsFile",
    "CardRecord",
    "CardsFile",
    "ConnectionRecord",
    "ConnectionsFile",
    "DigestRecord",
    "DigestsFile",
    "EventRecord",
    "EventsFile",
]


def _populated_install_root(tmp_path: Path) -> Path:
    """Copy the shared populated fixture into *tmp_path* and clear its build dir.

    The fixture is shared and generation writes files, so it is never generated
    into in place. The pre-built ``views/build/`` is removed so the fingerprint
    cache cannot short-circuit generation and mask the model change (Pitfall 2).
    """
    root = tmp_path / "populated"
    shutil.copytree(POPULATED_FIXTURE, root)
    shutil.rmtree(root / "views" / "build", ignore_errors=True)
    return root


def test_fresh_workspace_generates_clean(scaffolded_install_root: Path) -> None:
    report = generate(scaffolded_install_root)

    assert report.validation_errors == [], report.validation_errors
    assert report.warnings == [], report.warnings
    assert report.success is True, (report.validation_errors, report.warnings)


def test_populated_workspace_generates_clean(tmp_path: Path) -> None:
    root = _populated_install_root(tmp_path)

    report = generate(root)

    assert report.validation_errors == [], report.validation_errors
    assert report.success is True, report.validation_errors


def test_generated_card_connections_are_id_strings(tmp_path: Path) -> None:
    root = _populated_install_root(tmp_path)

    report = generate(root)
    assert report.validation_errors == [], report.validation_errors

    data_dir = root / "views" / "build" / "data"
    cards_files = sorted(data_dir.glob("*/cards.json"))
    assert cards_files, f"no per-workspace cards.json written under {data_dir}"

    all_cards: list[dict] = []
    for path in cards_files:
        payload = unwrap_payload(json.loads(path.read_text(encoding="utf-8")))
        all_cards.extend(payload["cards"])

    assert all_cards, "populated fixture produced zero cards"

    # generate() validates an *adapted projection* of each card but writes the
    # raw parser dict, so the denormalised neighbour list lands on disk under the
    # parser's key ``connects_to``. It is the same value the CardsFile adapter
    # feeds to CardRecord.connections (generate.py:110, :461).
    # Load-bearing precondition: without a non-empty list somewhere, the type
    # assertion below passes vacuously — the Pitfall 1 failure mode.
    assert any(card["connects_to"] for card in all_cards), (
        "no generated card has connections; CardRecord.connections is untested"
    )

    for card in all_cards:
        connections = card["connects_to"]
        assert all(isinstance(entry, str) for entry in connections), (
            f"card {card['id']} has non-string connections: {connections}"
        )
        # Probe edge E3: the ordering contract is sorted-by-target-id.
        assert connections == sorted(connections), (
            f"card {card['id']} connections are not sorted: {connections}"
        )
        # The value the writer emits must satisfy the model the validator applies.
        record = CardRecord(
            id=card["id"],
            title=card["title"],
            epistemic_type=card["epistemic_type"],
            confidence=card["confidence"],
            source_tier=card["source_tier"],
            lifecycle=card["lifecycle"],
            summary=card.get("summary_excerpt", ""),
            connections=connections,
        )
        assert record.connections == connections


def test_models_still_forbid_unknown_fields() -> None:
    for name in ALL_MODEL_NAMES:
        model = getattr(views_models, name)
        assert issubclass(model, pydantic.BaseModel), name
        assert model.model_config.get("extra") == "forbid", (
            f"{name} does not forbid unknown fields (D-02 prohibition)"
        )
