from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from construct.schemas.card import SchemaParseError, parse_card_markdown
from construct.schemas.config import DomainConfig, DomainsRegistry, GovernanceConfig, ModelRoutingConfig
from construct.schemas.workspace import ConnectionsFile, WorkspaceScaffold


FIXTURES = Path(__file__).resolve().parents[2] / "templates" / "workspace"


def test_valid_markdown_card_validates_against_filename() -> None:
    markdown = """---
id: successor-representation-spatial
title: Successor Representation for Spatial Reasoning
epistemic_type: finding
created: 2026-04-19
confidence: 3
source_tier: 2
domains:
  - intelligent-spatial-worlds
lifecycle: growing
connects_to:
  - target: world-model-convergence
    relation: extends
---

## Summary

Valid card body.
"""

    card, body = parse_card_markdown(markdown, source_path="cards/successor-representation-spatial.md")

    assert card.id == "successor-representation-spatial"
    assert card.epistemic_type.value == "finding"
    assert card.lifecycle.value == "growing"
    assert "## Summary" in body


def test_malformed_yaml_raises_structured_parse_error() -> None:
    markdown = """---
id: bad-card
title: [broken
epistemic_type: concept
created: 2026-04-19
confidence: 1
source_tier: 5
domains:
  - example-domain
---

## Summary

Broken.
"""

    with pytest.raises(SchemaParseError, match="invalid YAML frontmatter"):
        parse_card_markdown(markdown, source_path="cards/bad-card.md")


def test_invalid_enum_and_bad_id_fail_validation() -> None:
    markdown = """---
id: Not-Kebab
title: Invalid Card
epistemic_type: nonsense
created: 2026-04-19
confidence: 1
source_tier: 5
domains:
  - example-domain
---

## Summary

Invalid.
"""

    with pytest.raises(ValidationError) as exc_info:
        parse_card_markdown(markdown, source_path="cards/not-kebab.md")

    message = str(exc_info.value)
    assert "epistemic_type" in message
    assert "id" in message


def test_root_registry_and_domain_file_parse_as_linked_models() -> None:
    registry = DomainsRegistry.model_validate(
        {
            "domains": {
                "intelligent-spatial-worlds": {
                    "name": "Intelligent Spatial Worlds",
                    "path": "domains/intelligent-spatial-worlds/domain.yaml",
                    "description": "Spatial AI systems.",
                    "status": "active",
                    "created": "2026-04-22",
                }
            }
        }
    )
    domain = DomainConfig.model_validate(
        {
            "id": "intelligent-spatial-worlds",
            "name": "Intelligent Spatial Worlds",
            "description": "Spatial AI systems.",
            "status": "active",
            "scope": "Reasoning and action in physical environments.",
            "content_categories": ["spatial-reasoning", "world-models"],
            "source_priorities": ["peer-reviewed papers", "technical reports"],
            "research_seeds": ["successor representation", "vision-language-action"],
            "created": "2026-04-22",
        }
    )

    assert registry.domains[domain.id].path == f"domains/{domain.id}/domain.yaml"
    assert domain.content_categories == ["spatial-reasoning", "world-models"]


def test_duplicate_connection_edges_fail() -> None:
    with pytest.raises(ValidationError, match="duplicate canonical connections"):
        ConnectionsFile.model_validate(
            {
                "version": 1,
                "updated": "2026-04-22",
                "connection_types": ["extends", "supports"],
                "connections": [
                    {
                        "from": "card-a",
                        "to": "card-b",
                        "type": "extends",
                        "created": "2026-04-22",
                        "created_by": "curator",
                    },
                    {
                        "from": "card-a",
                        "to": "card-b",
                        "type": "extends",
                        "created": "2026-04-22",
                        "created_by": "curator",
                    },
                ],
            }
        )


def test_workspace_scaffold_exposes_required_paths() -> None:
    scaffold = WorkspaceScaffold()

    assert "cards" in scaffold.required_paths
    assert "domains" in scaffold.required_paths
    assert "db" in scaffold.required_paths
    assert "views" in scaffold.required_paths
    assert "publish" in scaffold.required_paths
    assert "log/events.jsonl" in scaffold.required_paths
    assert "connections.json" in scaffold.required_paths


def test_default_templates_round_trip_through_models() -> None:
    yaml = YAML(typ="safe")

    domains = yaml.load((FIXTURES / "domains.yaml").read_text())
    routing = yaml.load((FIXTURES / "model-routing.yaml").read_text())
    governance = yaml.load((FIXTURES / "governance.yaml").read_text())

    domains_model = DomainsRegistry.model_validate(domains)
    routing_model = ModelRoutingConfig.model_validate(routing)
    governance_model = GovernanceConfig.model_validate(governance)

    assert domains_model.domains["example-domain"].path == "domains/example-domain/domain.yaml"
    assert routing_model.routing["domain_init_interview"] == "frontier"
    assert routing_model.routing["chat_conversation"] == "frontier"
    assert governance_model.promotion.seed_to_growing_confidence == 2
    assert governance_model.heartbeat.views_interval_seconds == 30
