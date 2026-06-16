"""E2E: governed ingest → validate (ING-02 audit repro, now green).

The v0.3 milestone audit reported that ``construct ingest source`` stamps refs
with ``search_cluster`` "manual-ingest" / "web-ingest" (ingestion.py:162,208)
but those clusters were never seeded, so ``construct validate`` hard-failed every
governed ingest at validation.py:205 ("ref search cluster '...' is not defined").

Phase 07 Plan 02 seeds ``manual-ingest`` and ``web-ingest`` as reserved
SearchCluster entries (at init and in the fixtures). These tests reproduce the
audit repro on an isolated tmp_path copy of a fixture workspace: ingest a note
(and a URL), then assert validation passes with zero errors. They fail before the
seeding fix and pass after it — without weakening validation.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from construct.pipelines.ingestion import ingest_source
from construct.services.validation import validate_workspace


FIXTURE = Path(__file__).resolve().parents[2] / "test-ws" / "my-construct"


@pytest.fixture
def workspace_copy(tmp_path: Path) -> Path:
    """An isolated copy of the my-construct fixture so the test never mutates it."""
    dest = tmp_path / "my-construct"
    shutil.copytree(FIXTURE, dest)
    # Sanity: the committed fixture must already carry the reserved clusters.
    seeds = json.loads((dest / "search-seeds.json").read_text(encoding="utf-8"))
    cluster_ids = {c["id"] for c in seeds["clusters"]}
    assert {"manual-ingest", "web-ingest"}.issubset(cluster_ids), cluster_ids
    return dest


def _error_messages(report) -> list[str]:
    return [f"{f.path}: {f.message}" for f in report.errors]


def test_ingest_note_then_validate_passes(workspace_copy: Path) -> None:
    """A note ingest stamps search_cluster 'manual-ingest'; validation must pass."""
    result = ingest_source(workspace_copy, "a test note", domain_hint="cosmology")
    assert result.success, result.message

    ref_id = result.data["ref_id"]
    ref = json.loads((workspace_copy / "refs" / f"{ref_id}.json").read_text(encoding="utf-8"))
    assert ref["search_cluster"] == "manual-ingest", ref

    report = validate_workspace(workspace_copy)
    assert report.ok, _error_messages(report)
    assert report.errors == [], _error_messages(report)


def test_ingest_url_then_validate_passes(workspace_copy: Path) -> None:
    """A URL ingest stamps search_cluster 'web-ingest'; validation must pass."""
    result = ingest_source(
        workspace_copy,
        "https://www.desi.lbl.gov/dr2",
        domain_hint="cosmology",
    )
    assert result.success, result.message

    ref_id = result.data["ref_id"]
    ref = json.loads((workspace_copy / "refs" / f"{ref_id}.json").read_text(encoding="utf-8"))
    assert ref["search_cluster"] == "web-ingest", ref

    report = validate_workspace(workspace_copy)
    assert report.ok, _error_messages(report)
    assert report.errors == [], _error_messages(report)


def test_fixture_not_mutated_by_run(workspace_copy: Path) -> None:
    """The ingest operates on the tmp copy; the committed fixture must be untouched."""
    before = (FIXTURE / "search-seeds.json").read_text(encoding="utf-8")
    refs_before = sorted(p.name for p in (FIXTURE / "refs").glob("*.json"))

    result = ingest_source(workspace_copy, "another test note", domain_hint="cosmology")
    assert result.success, result.message

    after = (FIXTURE / "search-seeds.json").read_text(encoding="utf-8")
    refs_after = sorted(p.name for p in (FIXTURE / "refs").glob("*.json"))
    assert before == after, "committed fixture search-seeds.json was mutated"
    assert refs_before == refs_after, "committed fixture refs/ was mutated"
