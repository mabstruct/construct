from __future__ import annotations

import json
from pathlib import Path
import shutil

from construct.services.validation import validate_workspace
from construct.storage.workspace import WorkspaceLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "workspace"
INVALID_DIR = PROJECT_ROOT / "tests" / "fixtures" / "invalid"


def _write_valid_workspace(root: Path) -> Path:
    (root / "cards").mkdir(parents=True)
    (root / "domains" / "example-domain").mkdir(parents=True)
    (root / "refs").mkdir()
    (root / "workflows").mkdir()
    (root / "log").mkdir()
    (root / "db").mkdir()
    (root / "views").mkdir()

    shutil.copy(TEMPLATE_DIR / "domains.yaml", root / "domains.yaml")
    shutil.copy(TEMPLATE_DIR / "model-routing.yaml", root / "model-routing.yaml")
    shutil.copy(TEMPLATE_DIR / "governance.yaml", root / "governance.yaml")

    (root / "domains" / "example-domain" / "domain.yaml").write_text(
        """id: example-domain
name: Example Domain
description: Example domain for validation tests.
status: active
scope: Example scope.
content_categories:
  - examples
source_priorities:
  - peer-reviewed papers
research_seeds:
  - example seed
created: 2026-04-22
"""
    )
    (root / "connections.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updated": "2026-04-22",
                "connection_types": [
                    "supports",
                    "contradicts",
                    "extends",
                    "parallels",
                    "requires",
                    "enables",
                    "challenges",
                    "inspires",
                    "gap-for",
                ],
                "connections": [],
            }
        )
    )
    (root / "log" / "events.jsonl").write_text("")
    (root / "cards" / "valid-card.md").write_text(
        """---
id: valid-card
title: Valid Card
epistemic_type: concept
created: 2026-04-22
confidence: 2
source_tier: 3
domains:
  - example-domain
connects_to:
  - target: another-card
    relation: extends
---

## Summary

Valid summary section.
"""
    )

    return root


def test_valid_workspace_returns_warning_only_findings_for_soft_issues(workspace_path: Path) -> None:
    workspace = _write_valid_workspace(workspace_path)

    report = validate_workspace(workspace)

    assert report.errors == []
    assert len(report.warnings) == 1
    assert report.warnings[0].path == "cards/valid-card.md"
    assert "another-card" in report.warnings[0].message


def test_missing_required_files_and_broken_registry_links_are_errors(workspace_path: Path) -> None:
    workspace = _write_valid_workspace(workspace_path)
    shutil.copy(INVALID_DIR / "domains-missing-path.yaml", workspace / "domains.yaml")
    (workspace / "domains" / "example-domain" / "domain.yaml").unlink()
    (workspace / "model-routing.yaml").write_text("providers: [broken")
    (workspace / "connections.json").unlink()

    report = validate_workspace(workspace)

    error_paths = {finding.path for finding in report.errors}
    assert "model-routing.yaml" in error_paths
    assert "connections.json" in error_paths
    assert "domains/example-domain/domain.yaml" in error_paths


def test_derived_directories_are_not_treated_as_canonical_inputs(workspace_path: Path) -> None:
    workspace = _write_valid_workspace(workspace_path)
    loader = WorkspaceLoader(workspace)

    report = validate_workspace(workspace)

    assert report.errors == []
    assert loader.classify("db") == "derived"
    assert loader.classify("views") == "derived"
    assert all(finding.path not in {"db", "views"} for finding in report.errors)


def test_missing_summary_fixture_is_warning_not_error(workspace_path: Path) -> None:
    workspace = _write_valid_workspace(workspace_path)
    fixture_text = (INVALID_DIR / "invalid-card-no-summary.md").read_text()
    (workspace / "cards" / "invalid-card-no-summary.md").write_text(fixture_text)
    (workspace / "cards" / "valid-card.md").unlink()

    report = validate_workspace(workspace)

    assert report.errors == []
    assert len(report.warnings) == 1
    assert report.warnings[0].path == "cards/invalid-card-no-summary.md"
    assert "## Summary" in report.warnings[0].message
    assert report.by_file["cards/invalid-card-no-summary.md"][0].severity == "warning"
