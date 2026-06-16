"""Workspace health analysis and next-step suggestion engine."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from construct.pipelines.workflow_runner import WorkflowRunner
from construct.services.knowledge import OperationError, OperationResult
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader


SuggestionPriority = list[dict[str, str]]

# Reserved ingest clusters (seeded at init) always carry last_queried=None and
# must be excluded from research-staleness scoring — see init._write_search_seeds.
_RESERVED_INGEST_CLUSTERS = frozenset({"manual-ingest", "web-ingest"})

# Priority levels matching the construct-help skill ordering
PRIORITY_MAP = [
    ("no_workspace", "No workspace exists"),
    ("empty_domain", "Domain exists but is empty"),
    ("not_interviewed", "Domain not configured"),
    ("no_connections", "Cards exist but no connections"),
    ("stale_research", "Research is stale"),
    ("pending_curation", "Items needing curation attention"),
    ("healthy", "Graph is healthy"),
]


def suggest(workspace_root: str | Path) -> OperationResult:
    """Analyze workspace state and return prioritized next-step suggestions.

    Per D-07, the command returns structured JSON with workspace health,
    priorities, and action suggestions. The agent renders this as natural
    language to the user.

    Per D-08, consumes data from capability registry (graph.status) and
    workflow runner (active workflow state). Does not scan files directly.
    """
    root = Path(workspace_root).resolve()

    # Load base namespace
    if not root.exists():
        return _result("no_workspace", workspace=str(root))

    try:
        loader = WorkspaceLoader(root)
        registry = loader.load_domains_registry()
    except (WorkspaceLoadError, OSError):
        return _result("workspace_error", workspace=str(root))

    if not registry.domains:
        return _result("no_workspace", workspace=str(root))

    # Check each domain — find the one that needs the most attention
    all_domains = list(registry.domains.keys())
    domains_state: list[dict[str, Any]] = []

    for domain_id in all_domains:
        domain_entry = registry.domains[domain_id]
        domain_root = root / domain_id
        cards_dir = domain_root / "cards"
        refs_dir = domain_root / "refs"
        connections_file = domain_root / "connections.json"

        card_count = len(list(cards_dir.glob("*.md"))) if cards_dir.exists() else 0
        ref_count = len(list(refs_dir.glob("*.json"))) if refs_dir.exists() else 0

        # Check if interviewed
        has_categories = bool(domain_entry.content_categories)
        has_priorities = bool(domain_entry.source_priorities)

        # Check connections
        conn_count = 0
        if connections_file.exists():
            try:
                conn_data = json.loads(connections_file.read_text(encoding="utf-8"))
                conn_count = len(conn_data.get("connections", []))
            except (json.JSONDecodeError, OSError):
                pass

        # Check stale research (search-seeds.json)
        research_stale_days = -1
        seeds_file = domain_root / "search-seeds.json"
        if seeds_file.exists():
            try:
                seeds = json.loads(seeds_file.read_text(encoding="utf-8"))
                clusters = seeds.get("clusters", [])
                # Staleness reflects the most recently queried *research* cluster.
                # Reserved ingest clusters always carry last_queried=None; the
                # research seed cluster is appended last by init, so a fixed index
                # (e.g. clusters[0]) reads the wrong cluster — aggregate instead.
                queried = [
                    c.get("last_queried")
                    for c in clusters
                    if c.get("id") not in _RESERVED_INGEST_CLUSTERS and c.get("last_queried")
                ]
                if queried:
                    try:
                        last = max(datetime.fromisoformat(q) for q in queried)
                        research_stale_days = (
                            (datetime.now(timezone.utc) - last).days
                            if last.tzinfo
                            else (datetime.now() - last).days
                        )
                        research_stale_days = max(0, research_stale_days)
                    except (ValueError, TypeError):
                        pass
            except (json.JSONDecodeError, OSError):
                pass

        domains_state.append({
            "domain_id": domain_id,
            "display_name": domain_entry.name or domain_id,
            "card_count": card_count,
            "ref_count": ref_count,
            "connection_count": conn_count,
            "has_categories": has_categories,
            "has_priorities": has_priorities,
            "research_stale_days": research_stale_days,
        })

    # Determine priority for each domain
    domain_priorities = []
    for ds in domains_state:
        priority, reason = _score_domain(ds)
        domain_priorities.append((priority, reason, ds))

    # Sort by priority (ascending index = more urgent)
    domain_priorities.sort(key=lambda x: x[0])

    # Get global status via capability registry
    from construct.capabilities.catalog import get_registry
    registry_caps = get_registry()
    workspace_id = str(root)
    graph_data = None
    try:
        cap = registry_caps.get("graph.status")
        graph_result = cap.handler(workspace_id)
        if graph_result.success:
            graph_data = graph_result.data
    except (KeyError, Exception):
        pass

    # Check active workflow state
    workflow_state = None
    try:
        runner = WorkflowRunner(root)
        ws = runner.status()
        if ws.success and ws.data and ws.data.get("active"):
            workflow_state = ws.data.get("state")
    except Exception:
        pass

    # Build suggestions
    suggestions = []
    for priority_idx, reason, ds in domain_priorities:
        priority_label = PRIORITY_MAP[priority_idx][1] if priority_idx < len(PRIORITY_MAP) else "ok"
        suggestions.append({
            "domain": ds["domain_id"],
            "priority": priority_label,
            "reason": reason,
            "card_count": ds["card_count"],
            "connection_count": ds["connection_count"],
        })

    # Build overall health assessment
    total_cards = sum(ds["card_count"] for ds in domains_state)
    total_connections = sum(ds["connection_count"] for ds in domains_state)

    health: dict[str, Any] = {
        "workspace": str(root),
        "domain_count": len(all_domains),
        "total_cards": total_cards,
        "total_connections": total_connections,
        "active_workflow": workflow_state,
        "suggestions": suggestions,
        "top_suggestion": suggestions[0] if suggestions else None,
    }

    if graph_data:
        health["graph_status"] = graph_data

    return OperationResult(
        success=True,
        message=f"Workspace health: {len(all_domains)} domains, {total_cards} cards, {total_connections} connections",
        data=health,
    )


def _score_domain(ds: dict[str, Any]) -> tuple[int, str]:
    """Score a domain's health on the priority scale. Lower index = more urgent.

    Priority order (matching construct-help skill):
    1. Domain exists but empty (no cards, no refs)
    2. Domain not interviewed (no categories, no priorities)
    3. Cards exist but no connections
    4. Research is stale (>7 days since last query)
    5. Cards need curation attention (flagged/decay items)
    6. Domain is healthy
    """
    if ds["card_count"] == 0 and ds["ref_count"] == 0:
        return (1, f"'{ds['display_name']}' has no cards or references yet")
    if not ds["has_categories"] or not ds["has_priorities"]:
        return (2, f"'{ds['display_name']}' hasn't been fully configured")
    if ds["card_count"] > 0 and ds["connection_count"] == 0:
        return (3, f"'{ds['display_name']}' has {ds['card_count']} card(s) but no connections")
    if ds["research_stale_days"] >= 7:
        return (4, f"'{ds['display_name']}' research is {ds['research_stale_days']} days stale")
    if ds["research_stale_days"] >= 0:
        return (5, f"'{ds['display_name']}' last research was {ds['research_stale_days']} days ago")
    return (6, f"'{ds['display_name']}' looks healthy")


def _result(status: str, **kwargs: Any) -> OperationResult:
    if status == "no_workspace":
        return OperationResult(
            success=True,
            message="No workspace found — create one to get started",
            data={"status": status, "suggestion": "init", **kwargs},
        )
    if status == "workspace_error":
        return OperationResult(
            success=True,
            message="Could not load workspace — check the path",
            data={"status": status, **kwargs},
        )
    return OperationResult(
        success=True,
        message="Workspace state analyzed",
        data={"status": status, **kwargs},
    )
