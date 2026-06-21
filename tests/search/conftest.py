"""Shared fixtures for search provider tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.llm.conftest import create_test_workspace

REPO_ROOT = Path(__file__).resolve().parents[2]
SEARCH_TEMPLATE = REPO_ROOT / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates" / "search.yaml"
MOCK_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "search"


@pytest.fixture
def mock_fixtures_dir() -> Path:
    """Return the repository mock search fixture directory."""
    return MOCK_FIXTURES_DIR


def overlay_mock_search_config(workspace: Path, *, fixture_dir: Path | None = None) -> None:
    """Write .construct/search.yaml configured for the mock provider onto a workspace."""
    fixtures = fixture_dir or MOCK_FIXTURES_DIR
    yaml = YAML(typ="safe")
    search_config = yaml.load(SEARCH_TEMPLATE.read_text())
    search_config["providers"]["mock"]["fixture_dir"] = str(fixtures)

    construct_dir = workspace / ".construct"
    construct_dir.mkdir(parents=True, exist_ok=True)
    yaml.dump(search_config, construct_dir / "search.yaml")


@pytest.fixture
def search_workspace(tmp_path: Path, mock_fixtures_dir: Path) -> Path:
    """Create a test workspace with .construct/search.yaml configured for mock provider."""
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    overlay_mock_search_config(ws, fixture_dir=mock_fixtures_dir)
    return ws
