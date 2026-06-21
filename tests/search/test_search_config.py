"""Unit tests for SearchConfig schema and search.yaml template."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from construct.schemas.config import SearchConfig, SearchProviderName
from construct.services.validation import validate_workspace
from construct.storage.workspace import WorkspaceLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
SEARCH_TEMPLATE = REPO_ROOT / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates" / "search.yaml"


def _load_template() -> SearchConfig:
    yaml = YAML(typ="safe")
    payload = yaml.load(SEARCH_TEMPLATE.read_text())
    return SearchConfig.model_validate(payload)


def test_template_round_trip() -> None:
    config = _load_template()
    assert config.version == 1
    assert config.default_provider == SearchProviderName.mock
    assert "mock" in config.providers
    assert "tavily" in config.providers
    assert config.providers["mock"].type == "mock"
    assert config.providers["tavily"].type == "tavily"
    assert config.providers["tavily"].api_key_env == "TAVILY_API_KEY"
    assert config.caps.max_results_per_query == 5


def test_reject_invalid_api_key_env() -> None:
    yaml = YAML(typ="safe")
    payload = yaml.load(SEARCH_TEMPLATE.read_text())
    payload["providers"]["tavily"]["api_key_env"] = "lowercase"

    with pytest.raises(ValidationError, match="api_key_env"):
        SearchConfig.model_validate(payload)


def test_reject_missing_default_provider_in_providers() -> None:
    yaml = YAML(typ="safe")
    payload = yaml.load(SEARCH_TEMPLATE.read_text())
    payload["default_provider"] = "tavily"
    del payload["providers"]["tavily"]

    with pytest.raises(ValidationError, match="default_provider"):
        SearchConfig.model_validate(payload)


def test_template_does_not_contain_literal_api_key() -> None:
    template_text = SEARCH_TEMPLATE.read_text()
    assert "api_key:" not in template_text
    assert "TAVILY_API_KEY" in template_text


def test_workspace_loader_load_search_config(search_workspace: Path) -> None:
    config = WorkspaceLoader(search_workspace).load_search_config()
    assert config.default_provider == SearchProviderName.mock
    assert config.default_provider.value == "mock"


def test_validate_workspace_reports_invalid_search_yaml(search_workspace: Path) -> None:
    search_yaml = search_workspace / ".construct" / "search.yaml"
    search_yaml.write_text("default_provider: tavily\nproviders: {}\n", encoding="utf-8")

    report = validate_workspace(search_workspace)
    assert not report.ok
    assert any(
        finding.path == ".construct/search.yaml" and finding.severity == "error"
        for finding in report.findings
    )
