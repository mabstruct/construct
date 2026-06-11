"""Shared fixtures for bridge detection tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from construct.schemas.card import CardAuthor, Lifecycle
from construct.services.init import DomainInitInput, initialize_workspace

from tests.llm.conftest import create_test_workspace, write_card


def _write_connections(workspace: Path, connections: list[dict]) -> None:
    """Write connections.json fixture."""
    payload = {
        "version": 1,
        "updated": "2025-01-01",
        "connection_types": ["supports", "contradicts", "extends", "parallels"],
        "connections": connections,
    }
    (workspace / "connections.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _init_second_domain(workspace: Path, domain_id: str = "second-domain") -> None:
    """Initialize a second domain in the workspace."""
    domain = DomainInitInput(
        domain_id=domain_id,
        display_name=domain_id.replace("-", " ").title(),
        scope=f"Second test domain for {domain_id}.",
        taxonomy_seeds=["other-category"],
        source_priorities=["technical reports"],
        research_seeds=["more research"],
    )
    domain_dir = workspace / "cards" / domain_id
    domain_dir.mkdir(parents=True, exist_ok=True)
    # Write domain entry to domains.yaml
    import ruamel.yaml
    yaml = ruamel.yaml.YAML()
    domains_path = workspace / "domains.yaml"
    if domains_path.exists():
        data = yaml.load(domains_path.read_text(encoding="utf-8"))
    else:
        data = {"version": 1, "domains": {}}
    data["domains"][domain_id] = {
        "id": domain_id,
        "display_name": domain.display_name,
        "scope": domain.scope,
        "taxonomy_seeds": domain.taxonomy_seeds,
        "source_priorities": domain.source_priorities,
        "research_seeds": domain.research_seeds,
    }
    from io import StringIO
    buf = StringIO()
    yaml.dump(data, buf)
    domains_path.write_text(buf.getvalue(), encoding="utf-8")


@pytest.fixture
def cross_domain_workspace(tmp_path: Path) -> Path:
    """Workspace with two domains and cross-domain connections."""
    ws = tmp_path / "cross-domain"
    create_test_workspace(ws, domain_id="cosmology")
    _init_second_domain(ws, "philosophy-of-mind")

    # Cards in cosmology
    write_card(ws, "cosmo-1", title="Cosmic Expansion",
               domain="cosmology", body="The universe expands at an accelerating rate.",
               content_categories=["foundations", "observations"])
    write_card(ws, "cosmo-2", title="Dark Matter",
               domain="cosmology", body="Dark matter constitutes 85% of matter in the universe.",
               content_categories=["foundations", "matter"])

    # Cards in philosophy-of-mind
    write_card(ws, "phil-1", title="Consciousness Studies",
               domain="philosophy-of-mind", body="Consciousness remains a central problem.",
               content_categories=["foundations", "awareness"])
    write_card(ws, "phil-2", title="Qualia",
               domain="philosophy-of-mind", body="Qualia are subjective experiences.",
               content_categories=["awareness"])

    # Cross-domain connections
    _write_connections(ws, [
        {"from": "cosmo-1", "to": "phil-1", "type": "parallels",
         "created": "2025-01-01", "created_by": "construct",
         "notes": "Both address fundamental questions of existence."},
    ])

    return ws
