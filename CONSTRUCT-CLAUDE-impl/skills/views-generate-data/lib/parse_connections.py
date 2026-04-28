"""Parse workspace connections.json per data-model spec §5.3."""
import json
import hashlib
from pathlib import Path

CANONICAL_TYPES = {
    "supports", "contradicts", "extends", "parallels",
    "requires", "enables", "challenges", "inspires", "gap-for",
}


def parse(workspace: Path, warnings: list) -> dict:
    """Return {connections: [...], type_counts: {...}}."""
    conn_file = workspace / "connections.json"
    if not conn_file.is_file():
        return {"connections": [], "type_counts": {t: 0 for t in CANONICAL_TYPES}}

    try:
        raw = json.loads(conn_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        warnings.append({"workspace": workspace.name,
                         "file": f"{workspace.name}/connections.json",
                         "reason": f"JSON parse error: {e}"})
        return {"connections": [], "type_counts": {t: 0 for t in CANONICAL_TYPES}}

    raw_conns = raw.get("connections", []) if isinstance(raw, dict) else []

    out = []
    type_counts = {t: 0 for t in CANONICAL_TYPES}
    for c in raw_conns:
        if not isinstance(c, dict):
            continue
        source = str(c.get("source", "")) or str(c.get("from", ""))
        target = str(c.get("target", "")) or str(c.get("to", ""))
        ctype = str(c.get("type", "unknown"))
        if not source or not target:
            continue
        if ctype not in CANONICAL_TYPES:
            warnings.append({"workspace": workspace.name,
                             "file": f"{workspace.name}/connections.json",
                             "reason": f"unknown connection type '{ctype}' between {source}->{target}; tagged 'unknown'"})

        cid = c.get("id") or _stable_id(source, target, ctype)
        out.append({
            "id": cid,
            "source": source,
            "target": target,
            "type": ctype,
            "note": str(c.get("note", "")),
            "created": str(c.get("created", "")),
            "author": str(c.get("author", "")),
        })
        if ctype in type_counts:
            type_counts[ctype] += 1

    out.sort(key=lambda c: (c["source"], c["target"], c["type"]))
    return {"connections": out, "type_counts": type_counts}


def _stable_id(source: str, target: str, ctype: str) -> str:
    h = hashlib.sha256(f"{source}|{target}|{ctype}".encode("utf-8")).hexdigest()[:8]
    return f"conn-{h}"


def denormalize_into_cards(cards: list, connections: list) -> None:
    """Fill each card's connects_to with deduplicated, sorted neighbours."""
    by_id = {c["id"]: c for c in cards}
    neighbours: dict[str, set] = {c["id"]: set() for c in cards}
    for conn in connections:
        if conn["source"] in neighbours:
            neighbours[conn["source"]].add(conn["target"])
        if conn["target"] in neighbours:
            neighbours[conn["target"]].add(conn["source"])
    for cid, nset in neighbours.items():
        by_id[cid]["connects_to"] = sorted(nset)
