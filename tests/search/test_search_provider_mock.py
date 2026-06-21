"""Unit tests for MockSearchProvider."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from construct.schemas.config import SearchConfig
from construct.search.errors import ProviderUnavailableError, RateLimitError
from construct.search.providers.tavily import normalize_tavily_response
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


def test_tavily_normalization() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "search" / "tavily_basic.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    raw_response = payload["response"]
    raw_results = raw_response["results"]
    sdk_response = {
        "results": [
            {
                "title": item["title"],
                "url": item["url"],
                "content": item.get("content", item.get("snippet", "")),
                "score": item["score"],
                **{
                    key: value
                    for key, value in item.get("provider_specific", {}).items()
                },
            }
            for item in raw_results
        ]
    }

    output = normalize_tavily_response(
        sdk_response,
        max_results=5,
        query=payload["query"],
        cluster_id=None,
        provider_name="tavily",
    )

    assert output.provider_name == "tavily"
    assert output.query == "api gateway patterns"
    assert len(output.results) == 1

    result = output.results[0]
    assert result.title == "Tavily Sample Result"
    assert result.url.startswith("https://")
    assert "normalization" in result.snippet.lower()
    assert result.source_tier == 3
    assert result.score == 0.85
    assert result.provider_specific.get("published_date") == "2025-06-01"


def test_tavily_factory_unavailable_without_sdk(
    mock_fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yaml = YAML(typ="safe")
    payload = yaml.load(SEARCH_TEMPLATE.read_text())
    payload["default_provider"] = "tavily"
    config = SearchConfig.model_validate(payload)

    def _raise_unavailable() -> tuple[object, ...]:
        raise ProviderUnavailableError(
            provider_name="tavily",
            message="Install with: pip install -e '.[search]'",
        )

    monkeypatch.setattr(
        "construct.search.providers.tavily._import_tavily_sdk",
        _raise_unavailable,
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        SearchProviderFactory.create(config)

    assert exc_info.value.provider_name == "tavily"
    assert "search" in exc_info.value.message.lower()
