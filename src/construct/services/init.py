"""Workspace initialization service."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil

from ruamel.yaml import YAML


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "CONSTRUCT-agents" / "templates"


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
            f"domains/{domain.domain_id}",
            "refs",
            "workflows",
            "log",
            "inbox",
            "digests",
            "db",
            "views",
            "publish/articles",
            "publish/reports",
            "publish/drafts",
            "publish/exports",
        ],
    )

    shutil.copy(TEMPLATE_DIR / "model-routing.yaml", workspace_root / "model-routing.yaml")
    shutil.copy(TEMPLATE_DIR / "governance.yaml", workspace_root / "governance.yaml")

    _write_domains_registry(workspace_root, domain)
    _write_domain_file(workspace_root, domain)
    _write_connections(workspace_root)
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
                "path": f"domains/{domain.domain_id}/domain.yaml",
                "description": domain.scope,
                "status": "active",
                "created": "2026-04-22",
            }
        }
    }
    with (root / "domains.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _write_domain_file(root: Path, domain: DomainInitInput) -> None:
    yaml = YAML()
    payload = {
        "id": domain.domain_id,
        "name": domain.display_name,
        "description": domain.scope,
        "status": "active",
        "scope": domain.scope,
        "content_categories": domain.taxonomy_seeds,
        "source_priorities": domain.source_priorities,
        "research_seeds": domain.research_seeds,
        "created": "2026-04-22",
    }
    domain_path = root / "domains" / domain.domain_id / "domain.yaml"
    with domain_path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _write_connections(root: Path) -> None:
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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_events_log(root: Path) -> None:
    (root / "log" / "events.jsonl").write_text("", encoding="utf-8")


def _write_gitignore(root: Path) -> None:
    (root / ".gitignore").write_text("# Persistent indexes (rebuildable)\ndb/\n\n# Disposable views (heartbeat-rebuilt)\nviews/\n\n# OS / editor\n.DS_Store\n*.swp\n", encoding="utf-8")


def _write_workspace_doc(root: Path) -> None:
    (root / "WORKSPACE.md").write_text(
        "# CONSTRUCT Workspace\n\n"
        "## Canonical Paths\n\n"
        "- `cards/`\n"
        "- `domains.yaml`\n"
        "- `domains/{domain_id}/domain.yaml`\n"
        "- `connections.json`\n"
        "- `governance.yaml`\n"
        "- `model-routing.yaml`\n"
        "- `refs/`\n"
        "- `workflows/`\n"
        "- `log/events.jsonl`\n\n"
        "## Derived Paths\n\n"
        "- `db/` contains rebuildable indexes.\n"
        "- `views/` contains rebuildable UI read models.\n\n"
        "## Support Paths\n\n"
        "- `inbox/`, `digests/`, and `publish/` are durable workspace support areas.\n",
        encoding="utf-8",
    )
