"""Workspace initialization service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from ruamel.yaml import YAML

from construct.services.validation import (
    validate_connections_write,
    validate_domains_write,
    validate_event_write,
    validate_governance_write,
    validate_search_seeds_write,
)


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates"


@dataclass(frozen=True)
class DomainInitInput:
    domain_id: str
    display_name: str
    scope: str
    taxonomy_seeds: list[str]
    source_priorities: list[str]
    research_seeds: list[str]


class WorkspaceInitError(ValueError):
    """Raised when workspace initialization cannot proceed safely."""


def initialize_workspace(root: str | Path, domain: DomainInitInput) -> Path:
    workspace_root = Path(root).expanduser().resolve()
    if workspace_root.exists() and any(workspace_root.iterdir()):
        raise WorkspaceInitError(f"target path already exists and is not empty: {workspace_root}")

    workspace_root.mkdir(parents=True, exist_ok=True)

    _create_directories(
        workspace_root,
        [
            "cards",
            "refs",
            "log",
            "digests",
            "publish",
            ".construct",
        ],
    )

    shutil.copy(TEMPLATE_DIR / "model-routing.yaml", workspace_root / ".construct" / "model-routing.yaml")

    _write_governance(workspace_root)
    _write_domains_registry(workspace_root, domain)
    _write_connections(workspace_root)
    _write_search_seeds(workspace_root, domain)
    _write_events_log(workspace_root)
    _write_gitignore(workspace_root)
    _write_workspace_doc(workspace_root)

    return workspace_root


def _create_directories(root: Path, relative_paths: list[str]) -> None:
    for relative_path in relative_paths:
        (root / relative_path).mkdir(parents=True, exist_ok=True)


def _write_domains_registry(root: Path, domain: DomainInitInput) -> None:
    yaml = YAML()
    payload = {
        "domains": {
            domain.domain_id: {
                "name": domain.display_name,
                "description": domain.scope,
                "status": "active",
                "created": datetime.now(timezone.utc).date().isoformat(),
                "content_categories": domain.taxonomy_seeds,
                "source_priorities": domain.source_priorities,
                "cross_domain_links": [],
            }
        }
    }
    validate_domains_write(payload)
    with (root / "domains.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _write_connections(root: Path) -> None:
    payload = json.loads((TEMPLATE_DIR / "connections.json").read_text(encoding="utf-8"))
    validate_connections_write(payload)
    (root / "connections.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_governance(root: Path) -> None:
    yaml = YAML(typ="safe")
    payload = yaml.load((TEMPLATE_DIR / "governance.yaml").read_text(encoding="utf-8"))
    validate_governance_write(payload)
    shutil.copy(TEMPLATE_DIR / "governance.yaml", root / "governance.yaml")


def _write_events_log(root: Path) -> None:
    event = validate_event_write(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": "construct",
            "action": "workspace_init",
            "target": None,
            "detail": "Initialized canonical CONSTRUCT workspace scaffold",
            "result": "success",
        }
    )
    (root / "log" / "events.jsonl").write_text(event.model_dump_json() + "\n", encoding="utf-8")


def _write_search_seeds(root: Path, domain: DomainInitInput) -> None:
    payload = json.loads((TEMPLATE_DIR / "search-seeds.json").read_text(encoding="utf-8"))

    # Reserved ingest clusters (manual-ingest / web-ingest) are seeded from the
    # template so governed ingest output passes validation.py:205. validation.py
    # also cross-checks each cluster.domain against domains.yaml (validation.py:148),
    # so the template's placeholder domain must be rewritten to the workspace's own
    # domain — otherwise a freshly-init'd workspace would fail validation with
    # "cluster 'manual-ingest' references unknown domain 'ingest'".
    reserved_clusters = payload.get("clusters", [])
    for cluster in reserved_clusters:
        cluster["domain"] = domain.domain_id

    if domain.research_seeds:
        # Append the domain seed cluster; do NOT drop the reserved clusters, or
        # ingested refs in a research-seeded workspace would fail validation.
        reserved_clusters.append(
            {
                "id": f"{domain.domain_id}-seed",
                "domain": domain.domain_id,
                "terms": domain.research_seeds,
                "weight": 1.0,
                "status": "active",
                "last_queried": None,
            }
        )
    payload["clusters"] = reserved_clusters

    validate_search_seeds_write(payload)
    (root / "search-seeds.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_gitignore(root: Path) -> None:
    (root / ".gitignore").write_text("# OS / editor\n.DS_Store\n*.swp\n", encoding="utf-8")


def _write_workspace_doc(root: Path) -> None:
    (root / "WORKSPACE.md").write_text(
        "# CONSTRUCT Workspace\n\n"
        "## Canonical Paths\n\n"
        "- `cards/`\n"
        "- `refs/`\n"
        "- `connections.json`\n"
        "- `domains.yaml`\n"
        "- `governance.yaml`\n"
        "- `search-seeds.json`\n"
        "- `log/events.jsonl`\n\n"
        "## Derived Paths\n\n"
        "- `digests/` contains rebuildable workflow summaries.\n"
        "- `publish/` contains derived outward-facing outputs.\n\n"
        "## Support Paths\n\n"
        "- `.construct/model-routing.yaml` stores runtime routing guidance.\n",
        encoding="utf-8",
    )
