"""Parse domains.yaml (root-level preferred, per-workspace legacy) and compute metrics.

Per data-model spec §5.1.
"""
from pathlib import Path
import yaml


def parse(install_root: Path, workspace_data: dict, warnings: list) -> dict:
    """Read domains.yaml from root + per-workspace, merge, compute metrics."""
    declared: dict[str, dict] = {}

    # Root-level domains.yaml takes precedence
    root_yaml = install_root / "domains.yaml"
    if root_yaml.is_file():
        for ws_id, meta in _read(root_yaml, "domains.yaml", warnings).items():
            declared[ws_id] = meta

    # Per-workspace fallback for v0.1 layouts
    for ws_id in workspace_data.keys():
        ws_yaml = install_root / ws_id / "domains.yaml"
        if not ws_yaml.is_file():
            continue
        for d_id, meta in _read(ws_yaml, f"{ws_id}/domains.yaml", warnings).items():
            # Don't overwrite root-level entries
            declared.setdefault(d_id, meta)

    # Build entries with metrics
    domains = []
    for ws_id, ws in workspace_data.items():
        meta = declared.get(ws_id, {})
        domains.append({
            "id": ws_id,
            "name": str(meta.get("name", ws_id)),
            "description": str(meta.get("description", "")),
            "status": str(meta.get("status", "active")),
            "created": str(meta.get("created", "")),
            "content_categories": _list(meta.get("content_categories")),
            "source_priorities": _list(meta.get("source_priorities")),
            "cross_domain_links": meta.get("cross_domain_links", []) if isinstance(meta.get("cross_domain_links"), list) else [],
            "metrics": _compute_metrics(ws),
        })

    domains.sort(key=lambda d: d["id"])
    return {"domains": domains}


def _read(path: Path, label: str, warnings: list) -> dict:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:
        warnings.append({"workspace": "(root)" if path.parent.name != path.name else path.parent.name,
                         "file": label, "reason": f"YAML parse error: {e}"})
        return {}
    if not isinstance(raw, dict):
        return {}
    domains = raw.get("domains", {})
    return domains if isinstance(domains, dict) else {}


def _list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return []


def _compute_metrics(ws: dict) -> dict:
    cards = ws.get("cards", [])
    conns = ws.get("connections", {}).get("connections", [])
    digests = ws.get("digests", [])
    refs_count = ws.get("refs_count", 0)

    by_lifecycle = {"seed": 0, "growing": 0, "mature": 0, "archived": 0}
    by_confidence = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for c in cards:
        lc = c.get("lifecycle")
        if lc in by_lifecycle:
            by_lifecycle[lc] += 1
        cf = str(c.get("confidence"))
        if cf in by_confidence:
            by_confidence[cf] += 1

    # Orphan = no incoming or outgoing connections
    connected = set()
    for conn in conns:
        connected.add(conn["source"])
        connected.add(conn["target"])
    orphans = sum(1 for c in cards if c["id"] not in connected)

    avg_conf = round(sum(c["confidence"] for c in cards) / len(cards), 2) if cards else 0.0

    last_research = max((d.get("date", "") for d in digests), default="")
    last_curation = ws.get("last_curation_date", "")

    return {
        "papers": refs_count,
        "cards": len(cards),
        "cards_by_lifecycle": by_lifecycle,
        "cards_by_confidence": by_confidence,
        "connections": len(conns),
        "orphan_cards": orphans,
        "avg_confidence": avg_conf,
        "last_research_cycle": last_research,
        "last_curation_cycle": last_curation,
    }
