"""Unit tests for mock fixture directory resolution."""
from __future__ import annotations

from pathlib import Path

from construct.schemas.config import SearchConfig
from construct.search.fixture_paths import package_fixture_dir, resolve_fixture_dir
from construct.search.registry import SearchProviderFactory
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[2]
SEARCH_TEMPLATE = REPO_ROOT / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates" / "search.yaml"


def test_package_fixture_dir_exists() -> None:
    fixture_dir = package_fixture_dir()
    assert fixture_dir.is_dir()
    assert any(fixture_dir.glob("*.json"))


def test_resolve_builtin_alias() -> None:
    assert resolve_fixture_dir("builtin") == package_fixture_dir()
    assert resolve_fixture_dir("@builtin") == package_fixture_dir()


def test_resolve_legacy_repo_template_path() -> None:
    resolved = resolve_fixture_dir("tests/fixtures/search")
    assert resolved == package_fixture_dir()


def test_resolve_missing_path_falls_back_to_package() -> None:
    resolved = resolve_fixture_dir("does/not/exist", workspace=Path("/tmp"))
    assert resolved == package_fixture_dir()


def test_builtin_config_returns_results_for_any_query() -> None:
    yaml = YAML(typ="safe")
    payload = yaml.load(SEARCH_TEMPLATE.read_text())
    config = SearchConfig.model_validate(payload)

    provider = SearchProviderFactory.create(config)
    output = provider.search("knowledge curators", max_results=5)

    assert len(output.results) == 1
    assert output.results[0].title == "Mock result: knowledge curators"
