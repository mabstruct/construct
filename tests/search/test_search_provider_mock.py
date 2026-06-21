"""Unit tests for MockSearchProvider."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from construct.schemas.config import SearchConfig
from construct.search.errors import RateLimitError
from construct.search.registry import SearchProviderFactory
from tests.search.conftest import SEARCH_TEMPLATE


def _mock_config(fixture_dir: Path) -> SearchConfig:
    yaml = YAML(typ="safe")
    payload = yaml.load(SEARCH_TEMPLATE.read_text())
    payload["providers"]["mock"]["fixture_dir"] = str(fixture_dir)
    return SearchConfig.model_validate(payload)


def test_happy_path_fixture(mock_fixtures_dir: Path) -> None:
    provider = SearchProviderFactory.create(_mock_config(mock_fixtures_dir))
    output = provider.search("quantum gravity", max_results=5)

    assert output.provider_name == "mock"
    assert output.query == "quantum gravity"
    assert len(output.results) >= 1

    result = output.results[0]
    assert result.title
    assert result.url.startswith("https://")
    assert result.snippet
    assert 1 <= result.source_tier <= 5
    assert 0.0 <= result.score <= 1.0


def test_error_injection(mock_fixtures_dir: Path) -> None:
    provider = SearchProviderFactory.create(_mock_config(mock_fixtures_dir))

    with pytest.raises(RateLimitError) as exc_info:
        provider.search("__error_rate_limit__", max_results=5)

    assert exc_info.value.retry_after_seconds == 30
    assert exc_info.value.provider_name == "mock"


def test_result_cap(mock_fixtures_dir: Path) -> None:
    provider = SearchProviderFactory.create(_mock_config(mock_fixtures_dir))
    output = provider.search("quantum gravity", max_results=1)

    assert len(output.results) == 1
    assert output.truncated is True


def test_search_by_seed_cluster(search_workspace: Path, mock_fixtures_dir: Path) -> None:
    seeds_path = search_workspace / "search-seeds.json"
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
    seeds["clusters"].append(
        {
            "id": "quantum-research",
            "domain": "test-domain",
            "terms": ["quantum", "gravity"],
            "weight": 1.0,
            "status": "active",
            "last_queried": None,
        }
    )
    seeds_path.write_text(json.dumps(seeds, indent=2) + "\n", encoding="utf-8")

    before_text = seeds_path.read_text(encoding="utf-8")
    before_mtime = seeds_path.stat().st_mtime_ns

    provider = SearchProviderFactory.create(_mock_config(mock_fixtures_dir))
    output = provider.search_by_seed_cluster("quantum-research", search_workspace, max_results=5)

    assert output.cluster_id == "quantum-research"
    assert output.query == "quantum gravity"
    assert len(output.results) >= 1
    assert seeds_path.read_text(encoding="utf-8") == before_text
    assert seeds_path.stat().st_mtime_ns == before_mtime
