from __future__ import annotations

import json
from pathlib import Path

import pytest

from construct.services.init import DomainInitInput, TEMPLATE_DIR, initialize_workspace
from construct.services.validation import (
    ArtifactValidationError,
    validate_card_write,
    validate_connections_write,
    validate_event_write,
    validate_ref_write,
    validate_workspace,
)


def test_invalid_artifacts_are_rejected_before_write() -> None:
    with pytest.raises(ArtifactValidationError):
        validate_card_write(
            """---
id: Not-Kebab
title: Bad Card
epistemic_type: finding
created: 2026-06-08
confidence: 2
source_tier: 3
domains:
  - example-domain
---

## Summary

Bad card.
""",
            source_path="cards/not-kebab.md",
        )

    with pytest.raises(ArtifactValidationError):
        validate_ref_write(
            {
                "id": "bad-ref",
                "title": "Bad Ref",
                "authors": [],
                "url": "https://example.com",
                "relevance_score": 1.5,
                "key_findings": [],
                "content_categories": ["examples"],
                "source_tier": 3,
                "extraction_status": "complete",
                "ingested_date": "2026-06-08",
                "domain": "example-domain",
                "search_cluster": "example-cluster",
                "cards_generated": [],
            },
            relative_path="refs/bad-ref.json",
        )

    with pytest.raises(ArtifactValidationError):
        validate_connections_write(
            {
                "version": 1,
                "updated": "2026-06-08",
                "connection_types": ["extends"],
                "connections": [
                    {
                        "from": "card-a",
                        "to": "card-b",
                        "type": "extends",
                        "created": "2026-06-08",
                        "created_by": "curator",
                    },
                    {
                        "from": "card-a",
                        "to": "card-b",
                        "type": "extends",
                        "created": "2026-06-08",
                        "created_by": "curator",
                    },
                ],
            }
        )

    with pytest.raises(ArtifactValidationError):
        validate_event_write({"ts": "2026-06-08T20:00:00Z", "agent": "construct", "action": "workspace_init"})


def test_initialize_workspace_uses_active_templates_and_canonical_layout(workspace_path: Path) -> None:
    workspace = initialize_workspace(
        workspace_path,
        DomainInitInput(
            domain_id="example-domain",
            display_name="Example Domain",
            scope="Example scope.",
            taxonomy_seeds=["examples"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["example seed"],
        ),
    )

    assert TEMPLATE_DIR.as_posix().endswith("CONSTRUCT-CLAUDE-impl/construct/templates")
    assert (workspace / "cards").is_dir()
    assert (workspace / "refs").is_dir()
    assert (workspace / "digests").is_dir()
    assert (workspace / "publish").is_dir()
    assert (workspace / ".construct" / "model-routing.yaml").is_file()
    assert (workspace / "governance.yaml").is_file()
    assert (workspace / "search-seeds.json").is_file()
    assert (workspace / "domains.yaml").is_file()
    assert (workspace / "connections.json").is_file()
    assert (workspace / "log" / "events.jsonl").is_file()
    assert not (workspace / "domains" / "example-domain" / "domain.yaml").exists()
    assert not (workspace / "workflows").exists()
    assert not (workspace / "db").exists()
    assert not (workspace / "model-routing.yaml").exists()


def test_post_write_validation_reports_cross_file_consistency_gaps(workspace_path: Path) -> None:
    workspace = initialize_workspace(
        workspace_path,
        DomainInitInput(
            domain_id="example-domain",
            display_name="Example Domain",
            scope="Example scope.",
            taxonomy_seeds=["examples"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["example seed"],
        ),
    )

    (workspace / "cards" / "valid-card.md").write_text(
        """---
id: valid-card
title: Valid Card
epistemic_type: concept
created: 2026-06-08
confidence: 2
source_tier: 3
domains:
  - unknown-domain
content_categories:
  - examples
connects_to:
  - target: missing-card
    relation: extends
---

## Summary

Valid body.
""",
        encoding="utf-8",
    )
    (workspace / "refs" / "bad-domain.json").write_text(
        json.dumps(
            {
                "id": "bad-domain",
                "title": "Bad Domain Ref",
                "authors": [],
                "url": "https://example.com",
                "relevance_score": 0.7,
                "key_findings": [],
                "content_categories": ["examples"],
                "source_tier": 3,
                "extraction_status": "complete",
                "ingested_date": "2026-06-08",
                "domain": "unknown-domain",
                "search_cluster": "example-cluster",
                "cards_generated": ["valid-card"],
            }
        ),
        encoding="utf-8",
    )
    (workspace / "search-seeds.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updated": None,
                "clusters": [
                    {
                        "id": "unknown-domain-seed",
                        "domain": "unknown-domain",
                        "terms": ["example"],
                        "weight": 0.5,
                        "status": "active",
                        "last_queried": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (workspace / "connections.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updated": "2026-06-08",
                "connection_types": ["extends"],
                "connections": [
                    {
                        "from": "valid-card",
                        "to": "missing-card",
                        "type": "extends",
                        "created": "2026-06-08",
                        "created_by": "curator",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = validate_workspace(workspace)

    error_paths = {finding.path for finding in report.errors}
    warning_paths = {finding.path for finding in report.warnings}

    assert "cards/valid-card.md" in error_paths
    assert "refs/bad-domain.json" in error_paths
    assert "search-seeds.json" in error_paths
    assert "connections.json" in error_paths
    assert "cards/valid-card.md" in warning_paths
