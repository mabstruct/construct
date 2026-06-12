from __future__ import annotations

import json
from pathlib import Path

from ruamel.yaml import YAML

from construct.schemas.config import DomainsRegistry, GovernanceConfig, ModelRoutingConfig, SearchSeedsFile
from construct.schemas.workspace import WorkspaceScaffold
from construct.storage.workspace import WorkspaceLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates"


def _write_canonical_workspace(root: Path) -> Path:
    (root / "cards").mkdir(parents=True)
    (root / "refs").mkdir()
    (root / "log").mkdir()
    (root / "digests").mkdir()
    (root / "publish").mkdir()
    (root / "inbox").mkdir()
    (root / ".construct").mkdir()

    (root / "connections.json").write_text((TEMPLATE_DIR / "connections.json").read_text(), encoding="utf-8")
    (root / "domains.yaml").write_text((TEMPLATE_DIR / "domains.yaml").read_text(), encoding="utf-8")
    (root / "governance.yaml").write_text((TEMPLATE_DIR / "governance.yaml").read_text(), encoding="utf-8")
    (root / "search-seeds.json").write_text((TEMPLATE_DIR / "search-seeds.json").read_text(), encoding="utf-8")
    (root / ".construct" / "model-routing.yaml").write_text(
        (TEMPLATE_DIR / "model-routing.yaml").read_text(),
        encoding="utf-8",
    )
    (root / "log" / "events.jsonl").write_text("", encoding="utf-8")

    return root


def test_canonical_workspace_paths_match_phase_one_contract(workspace_path: Path) -> None:
    workspace = _write_canonical_workspace(workspace_path)
    loader = WorkspaceLoader(workspace)

    required = {item.relative_path: item for item in loader.inspect_workspace()}

    assert required["cards"].category == "canonical"
    assert required["refs"].category == "canonical"
    assert required["domains.yaml"].category == "canonical"
    assert required["search-seeds.json"].category == "canonical"
    assert required["log/events.jsonl"].category == "canonical"
    assert required["digests"].category == "derived"
    assert required["publish"].category == "derived"
    assert required[".construct/model-routing.yaml"].category == "support"
    assert all(item.exists for item in required.values())


def test_archived_only_paths_are_not_canonical_defaults(workspace_path: Path) -> None:
    workspace = _write_canonical_workspace(workspace_path)
    loader = WorkspaceLoader(workspace)

    assert "domains/example-domain/domain.yaml" not in loader.scaffold.canonical_paths
    assert "workflows" not in loader.scaffold.required_paths
    assert "db" not in loader.scaffold.required_paths
    assert loader.classify("domains/example-domain/domain.yaml") == "unknown"
    assert loader.classify("workflows") == "unknown"
    assert loader.classify("db") == "unknown"
    assert loader.classify("digests/topic/digest-2026-06-08.md") == "derived"
    assert loader.classify("publish/briefing.md") == "derived"


def test_template_backed_files_round_trip_through_updated_models_and_loader(workspace_path: Path) -> None:
    workspace = _write_canonical_workspace(workspace_path)
    yaml = YAML(typ="safe")

    domains_model = DomainsRegistry.model_validate(yaml.load((workspace / "domains.yaml").read_text()))
    governance_model = GovernanceConfig.model_validate(yaml.load((workspace / "governance.yaml").read_text()))
    routing_model = ModelRoutingConfig.model_validate(
        yaml.load((workspace / ".construct" / "model-routing.yaml").read_text())
    )
    search_seeds_model = SearchSeedsFile.model_validate(
        json.loads((workspace / "search-seeds.json").read_text())
    )

    loader = WorkspaceLoader(workspace)

    assert domains_model.domains == {}
    assert governance_model.promotion.seed_to_growing_confidence == 2
    assert routing_model.routing["chat_conversation"] == "frontier"
    assert search_seeds_model.clusters == []
    assert loader.load_domains_registry().domains == {}
    assert loader.load_governance().research.relevance_threshold == 0.3
    assert loader.load_model_routing().providers.frontier.provider.value == "anthropic"
    assert loader.load_search_seeds().clusters == []


def test_workspace_scaffold_names_canonical_derived_and_support_paths() -> None:
    scaffold = WorkspaceScaffold()

    assert scaffold.required_paths == (
        "cards",
        "refs",
        "connections.json",
        "domains.yaml",
        "governance.yaml",
        "search-seeds.json",
        "log/events.jsonl",
        "digests",
        "publish",
        "inbox",
        ".construct/model-routing.yaml",
    )
