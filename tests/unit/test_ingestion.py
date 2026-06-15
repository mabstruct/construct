"""Tests for the unified ingestion pipeline."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from construct.pipelines.ingestion import detect_source_type, ingest_source
from construct.schemas.card import validate_card_markdown
from construct.services.init import DomainInitInput, initialize_workspace


@pytest.fixture
def domain_workspace(tmp_path: Path) -> Path:
    """A minimal workspace with a single domain, ready for ingestion."""
    root = tmp_path / "workspace"
    initialize_workspace(
        root,
        DomainInitInput(
            domain_id="cosmology",
            display_name="Cosmology",
            scope="A test domain for ingestion tests.",
            taxonomy_seeds=["dark-energy"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["dark energy"],
        ),
    )
    return root


def test_detect_file_type():
    tmp = tempfile.mkdtemp()
    test_file = Path(tmp) / "test.txt"
    test_file.write_text("test")
    assert detect_source_type(str(test_file)) == "file"


def test_detect_url_type():
    assert detect_source_type("https://example.com") == "url"
    assert detect_source_type("http://test.org/page") == "url"


def test_detect_note_type():
    assert detect_source_type("a quick thought") == "note"
    assert detect_source_type("") == "note"


def test_detect_research_type():
    assert detect_source_type("research:quantum gravity") == "research"


def test_ingest_note_no_workspace():
    result = ingest_source("/nonexistent/workspace", "test note")
    assert not result.success


# --- Regression: Bug #2 — seed card creation used to always fail -------------


def test_ingest_url_creates_card(domain_workspace: Path):
    """URL ingestion must produce a seed card (no extra_forbidden on 'summary')."""
    result = ingest_source(
        domain_workspace,
        "https://www.desi.lbl.gov/dr2",
        domain_hint="cosmology",
    )
    assert result.success, result.message
    assert result.data["card_created"] is True, result.data
    card_id = result.data["card_id"]
    assert card_id
    card_md = (domain_workspace / "cards" / f"{card_id}.md").read_text(encoding="utf-8")
    # Frontmatter must validate and must NOT carry a forbidden 'summary' key.
    card = validate_card_markdown(card_md)
    assert "cosmology" in card.domains
    assert "\nsummary:" not in card_md


# --- Bug #1 — URL ingestion is no longer a metadata-blind stub ---------------


def test_ingest_url_records_supplied_metadata(domain_workspace: Path):
    result = ingest_source(
        domain_workspace,
        "https://www.desi.lbl.gov/dr2",
        domain_hint="cosmology",
        title="DESI DR2: Evolving Dark Energy at 4.2 sigma",
        relevance=0.95,
        source_tier=1,
        key_findings=["DESI DR2 favors evolving dark energy at 4.2 sigma"],
        content_categories=["Dark Energy"],
        year=2026,
        venue="arXiv",
        search_cluster="desi-dr2",
    )
    assert result.success, result.message
    # ref_id derived from the title, not the hostname
    ref_id = result.data["ref_id"]
    assert ref_id == "desi-dr2-evolving-dark-energy-at-42-sigma"
    ref = json.loads((domain_workspace / "refs" / f"{ref_id}.json").read_text())
    assert ref["title"] == "DESI DR2: Evolving Dark Energy at 4.2 sigma"
    assert ref["relevance_score"] == 0.95
    assert ref["source_tier"] == 1
    assert ref["key_findings"] == ["DESI DR2 favors evolving dark energy at 4.2 sigma"]
    assert ref["content_categories"] == ["dark-energy"]  # kebab-normalized
    assert ref["year"] == 2026
    assert ref["venue"] == "arXiv"
    assert ref["extraction_status"] == "complete"
    # The supplied finding lands in the card body Summary section.
    card_md = (domain_workspace / "cards" / f"{result.data['card_id']}.md").read_text()
    assert "evolving dark energy at 4.2 sigma" in card_md


def test_ingest_url_distinct_titles_avoid_host_collision(domain_workspace: Path):
    """Two arXiv papers must not collide into a single hostname slug."""
    first = ingest_source(
        domain_workspace, "https://arxiv.org/abs/2601.00001",
        domain_hint="cosmology", title="Hubble Tension Status 2026",
    )
    second = ingest_source(
        domain_workspace, "https://arxiv.org/abs/2601.00002",
        domain_hint="cosmology", title="S8 Tension Review 2026",
    )
    assert first.data["ref_id"] != second.data["ref_id"]
    assert first.data["ref_id"] == "hubble-tension-status-2026"
    assert second.data["ref_id"] == "s8-tension-review-2026"


def test_ingest_url_defaults_without_metadata(domain_workspace: Path):
    """Without supplied metadata, conservative defaults still apply."""
    result = ingest_source(
        domain_workspace, "https://example.com/page", domain_hint="cosmology",
    )
    ref = json.loads((domain_workspace / "refs" / f"{result.data['ref_id']}.json").read_text())
    assert ref["relevance_score"] == 0.5
    assert ref["source_tier"] == 5
    assert ref["extraction_status"] == "partial"
