"""Compute global and per-workspace stats per data-model spec §5.7."""
from datetime import datetime, timedelta, timezone


def compute_workspace(ws: dict) -> dict:
    """Stats scoped to one workspace."""
    cards = ws.get("cards", [])
    conns = ws.get("connections", {}).get("connections", [])
    digests = ws.get("digests", [])
    events = ws.get("events", [])
    refs_count = ws.get("refs_count", 0)

    by_lifecycle = {"seed": 0, "growing": 0, "mature": 0, "archived": 0}
    by_confidence = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for c in cards:
        if c.get("lifecycle") in by_lifecycle:
            by_lifecycle[c["lifecycle"]] += 1
        cf = str(c.get("confidence"))
        if cf in by_confidence:
            by_confidence[cf] += 1

    activity = _activity_last_30d(cards, conns, digests, events)

    n = len(cards)
    density = round(len(conns) / (n * (n - 1) / 2), 4) if n > 1 else 0.0

    connected = set()
    for conn in conns:
        connected.add(conn["source"])
        connected.add(conn["target"])
    orphans = sum(1 for c in cards if c["id"] not in connected)

    avg_conf = round(sum(c["confidence"] for c in cards) / len(cards), 2) if cards else 0.0

    cat_coverage: dict[str, int] = {}
    for c in cards:
        for cat in c.get("content_categories", []):
            cat_coverage[cat] = cat_coverage.get(cat, 0) + 1

    return {
        "totals": {
            "papers": refs_count,
            "cards": len(cards),
            "connections": len(conns),
            "digests": len(digests),
            "articles": ws.get("articles_count", 0),
        },
        "by_lifecycle": by_lifecycle,
        "by_confidence": by_confidence,
        "activity_last_30d": activity,
        "connection_density": density,
        "orphan_cards": orphans,
        "avg_confidence": avg_conf,
        "category_coverage": dict(sorted(cat_coverage.items())),
        "search_clusters": [],
    }


def compute_global(workspace_data: dict, articles: list) -> dict:
    """Aggregate across all workspaces."""
    totals = {
        "workspaces": len(workspace_data),
        "papers": 0,
        "cards": 0,
        "connections": 0,
        "digests": 0,
        "articles": len(articles),
    }
    by_lifecycle = {"seed": 0, "growing": 0, "mature": 0, "archived": 0}
    by_confidence = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

    activity = {"cards_created": 0, "connections_added": 0, "digests": 0, "articles": 0}
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    for ws_id, ws in workspace_data.items():
        cards = ws.get("cards", [])
        conns = ws.get("connections", {}).get("connections", [])
        digests = ws.get("digests", [])

        totals["papers"] += ws.get("refs_count", 0)
        totals["cards"] += len(cards)
        totals["connections"] += len(conns)
        totals["digests"] += len(digests)

        for c in cards:
            if c.get("lifecycle") in by_lifecycle:
                by_lifecycle[c["lifecycle"]] += 1
            cf = str(c.get("confidence"))
            if cf in by_confidence:
                by_confidence[cf] += 1

        ws_act = _activity_last_30d(cards, conns, digests, ws.get("events", []))
        for k in activity:
            activity[k] += ws_act.get(k, 0)

    return {
        "totals": totals,
        "by_lifecycle": by_lifecycle,
        "by_confidence": by_confidence,
        "activity_last_30d": activity,
    }


def _activity_last_30d(cards: list, conns: list, digests: list, events: list) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "cards_created": sum(1 for c in cards if c.get("created", "") >= cutoff),
        "connections_added": sum(1 for c in conns if c.get("created", "") >= cutoff),
        "digests": sum(1 for d in digests if d.get("date", "") >= cutoff),
        "articles": 0,  # filled in compute_global from cross-workspace article dates if needed
    }
