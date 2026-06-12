"""Graph status PIPE capability — produce graph health report for a workspace."""
from __future__ import annotations

from pathlib import Path

from construct.schemas.card import KnowledgeCard, Lifecycle, SchemaParseError, parse_card_markdown
from construct.schemas.workspace import ConnectionType
from construct.services.knowledge import OperationError, OperationResult
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader


def graph_status(workspace: str | Path) -> OperationResult:
    try:
        root = Path(workspace)
        loader = WorkspaceLoader(root)

        card_total = 0
        lifecycle_counts: dict[str, int] = {}
        domain_card_counts: dict[str, int] = {}

        for card_path in loader.iter_cards():
            card_total += 1
            try:
                markdown = card_path.read_text(encoding="utf-8")
                card, _ = parse_card_markdown(markdown, source_path=card_path)
                lifecycle_counts[card.lifecycle.value] = lifecycle_counts.get(card.lifecycle.value, 0) + 1
                for domain in card.domains:
                    domain_card_counts[domain] = domain_card_counts.get(domain, 0) + 1
            except (SchemaParseError, OSError):
                lifecycle_counts["_unparseable"] = lifecycle_counts.get("_unparseable", 0) + 1
                domain_card_counts["_unparseable"] = domain_card_counts.get("_unparseable", 0) + 1

        conn_total = 0
        type_counts: dict[str, int] = {}
        try:
            connections = loader.load_connections()
            conn_total = len(connections.connections)
            for conn in connections.connections:
                type_counts[conn.type.value] = type_counts.get(conn.type.value, 0) + 1
        except WorkspaceLoadError:
            pass

        domain_total = 0
        domain_names: list[str] = []
        try:
            registry = loader.load_domains_registry()
            domain_total = len(registry.domains)
            domain_names = sorted(registry.domains)
        except WorkspaceLoadError:
            pass

        data = {
            "cards": {
                "total": card_total,
                "by_lifecycle": lifecycle_counts,
                "by_domain": domain_card_counts,
            },
            "connections": {
                "total": conn_total,
                "by_type": type_counts,
            },
            "domains": {
                "total": domain_total,
                "names": domain_names,
            },
            "workspace": str(root.resolve()),
        }

        return OperationResult(
            success=True,
            message=f"Graph status for {root.name}",
            data=data,
        )
    except (WorkspaceLoadError, OSError) as exc:
        return OperationResult(
            success=False,
            message=str(exc),
            errors=[OperationError(reason=str(exc))],
        )
