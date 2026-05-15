"""Build global bridges.json from canonical connections and bridge-detect artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def build(workspaces: list[Path], workspace_data: dict[str, dict], warnings: list) -> dict:
    """Return the global bridges.json payload (data field only)."""
    card_index = _build_card_index(workspace_data)
    bridges_by_key: dict[tuple, dict] = {}

    for ws in workspaces:
        ws_id = ws.name
        ws_payload = workspace_data.get(ws_id, {})
        for conn in ws_payload.get("connections", {}).get("connections", []):
            bridge = _build_confirmed_bridge(ws_id, conn, card_index, warnings)
            if bridge is None:
                continue
            _upsert_bridge(bridges_by_key, bridge)

    for ws in workspaces:
        candidate_path = ws / "log" / "bridge-candidates.json"
        if not candidate_path.is_file():
            continue
        for bridge in _load_candidate_bridges(candidate_path, card_index, warnings):
            _upsert_bridge(bridges_by_key, bridge)

    bridges = sorted(
        bridges_by_key.values(),
        key=lambda bridge: (
            0 if bridge["status"] == "confirmed" else 1,
            -bridge["score"],
            bridge["domains"][0],
            bridge["domains"][1],
            bridge["id"],
        ),
    )
    summary = _build_summary(bridges)
    return {"bridges": bridges, "summary": summary}


def _build_card_index(workspace_data: dict[str, dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    for ws_id, ws in workspace_data.items():
        for card in ws.get("cards", []):
            index[card["id"]].append({"workspace_id": ws_id, "card": card})
    return dict(index)


def _build_confirmed_bridge(
    owner_workspace_id: str,
    conn: dict,
    card_index: dict[str, list[dict]],
    warnings: list,
) -> dict | None:
    source_matches = _resolve_connection_endpoint(conn.get("source", ""), owner_workspace_id, card_index)
    target_matches = _resolve_connection_endpoint(conn.get("target", ""), owner_workspace_id, card_index)
    cross_pairs = [
        (source_meta, target_meta)
        for source_meta in source_matches
        for target_meta in target_matches
        if source_meta["workspace_id"] != target_meta["workspace_id"]
    ]
    if not cross_pairs:
        return None
    if len(cross_pairs) > 1:
        warnings.append(
            {
                "workspace": owner_workspace_id,
                "file": f"{owner_workspace_id}/connections.json",
                "reason": (
                    f"ambiguous cross-domain connection {conn.get('source')}->{conn.get('target')} "
                    f"for bridge generation; skipping"
                ),
            }
        )
        return None

    source_meta, target_meta = cross_pairs[0]
    shared_categories = _shared_categories(source_meta["card"], target_meta["card"])
    l1_score = 1.0
    l2_score = min(1.0, len(shared_categories) / 3) if shared_categories else 0.0
    l3_score = 0.0
    score = round((0.30 * l1_score) + (0.20 * l2_score) + (0.50 * l3_score), 2)

    return _bridge_record(
        status="confirmed",
        relation=conn.get("type", "unknown"),
        source_meta=source_meta,
        target_meta=target_meta,
        score=score,
        l1_present=True,
        l2_shared_categories=shared_categories,
        l3_summary="",
        l3_confidence=0.0,
        why_it_matters=str(conn.get("note", "")),
        provenance={
            "candidate_source": "",
            "candidate_workspace_id": "",
            "candidate_generated_at": "",
            "confirmed_via_connection": True,
            "connection_workspace_id": owner_workspace_id,
        },
    )


def _load_candidate_bridges(
    candidate_path: Path,
    card_index: dict[str, list[dict]],
    warnings: list,
) -> list[dict]:
    workspace_id = candidate_path.parent.parent.name
    try:
        raw = json.loads(candidate_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(
            {
                "workspace": workspace_id,
                "file": f"{workspace_id}/log/bridge-candidates.json",
                "reason": f"JSON parse error: {exc}",
            }
        )
        return []

    if not isinstance(raw, dict):
        warnings.append(
            {
                "workspace": workspace_id,
                "file": f"{workspace_id}/log/bridge-candidates.json",
                "reason": "bridge candidate payload must be a JSON object",
            }
        )
        return []

    generated_at = str(raw.get("generated_at", ""))
    source_workspace_id = str(raw.get("workspace_id", workspace_id))
    candidates = raw.get("candidates", [])
    if not isinstance(candidates, list):
        warnings.append(
            {
                "workspace": workspace_id,
                "file": f"{workspace_id}/log/bridge-candidates.json",
                "reason": "candidates must be a JSON array",
            }
        )
        return []

    bridges: list[dict] = []
    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        bridge = _candidate_to_bridge(
            source_workspace_id, generated_at, idx, candidate, card_index, warnings
        )
        if bridge is not None:
            bridges.append(bridge)
    return bridges


def _candidate_to_bridge(
    source_workspace_id: str,
    generated_at: str,
    idx: int,
    candidate: dict,
    card_index: dict[str, list[dict]],
    warnings: list,
) -> dict | None:
    file_label = f"{source_workspace_id}/log/bridge-candidates.json"
    source_card_id = str(candidate.get("source_card_id", ""))
    target_card_id = str(candidate.get("target_card_id", ""))
    target_workspace_id = str(candidate.get("target_workspace_id", ""))
    relation = str(candidate.get("proposed_relation", "parallels"))
    candidate_strength = str(candidate.get("candidate_strength", "possible"))
    signals = candidate.get("signals", {}) if isinstance(candidate.get("signals"), dict) else {}

    if not source_card_id or not target_card_id or not target_workspace_id:
        warnings.append(
            {
                "workspace": source_workspace_id,
                "file": file_label,
                "reason": f"candidate #{idx + 1} missing required endpoint fields; skipping",
            }
        )
        return None

    source_meta = _resolve_candidate_endpoint(source_card_id, source_workspace_id, card_index)
    target_meta = _resolve_candidate_endpoint(target_card_id, target_workspace_id, card_index)
    if source_meta is None or target_meta is None:
        warnings.append(
            {
                "workspace": source_workspace_id,
                "file": file_label,
                "reason": (
                    f"candidate #{idx + 1} references missing or ambiguous cards "
                    f"{source_card_id}->{target_card_id}; skipping"
                ),
            }
        )
        return None

    if source_meta["workspace_id"] == target_meta["workspace_id"]:
        warnings.append(
            {
                "workspace": source_workspace_id,
                "file": file_label,
                "reason": f"candidate #{idx + 1} is not cross-domain; skipping",
            }
        )
        return None

    l1_present = bool(signals.get("l1_structural", False))
    shared_categories = _string_list(signals.get("l2_shared_categories"))
    l2_score = min(1.0, len(shared_categories) / 3) if shared_categories else 0.0
    l3_summary = str(signals.get("l3_reasoning", ""))
    l3_score = 1.0 if candidate_strength == "strong" else 0.6 if candidate_strength == "possible" else 0.0
    score = round((0.30 * (1.0 if l1_present else 0.0)) + (0.20 * l2_score) + (0.50 * l3_score), 2)

    return _bridge_record(
        status="candidate",
        relation=relation,
        source_meta=source_meta,
        target_meta=target_meta,
        score=score,
        l1_present=l1_present,
        l2_shared_categories=shared_categories,
        l3_summary=l3_summary,
        l3_confidence=l3_score,
        why_it_matters=l3_summary,
        provenance={
            "candidate_source": "bridge-detect",
            "candidate_workspace_id": source_workspace_id,
            "candidate_generated_at": generated_at,
            "confirmed_via_connection": False,
            "connection_workspace_id": "",
        },
    )


def _bridge_record(
    *,
    status: str,
    relation: str,
    source_meta: dict,
    target_meta: dict,
    score: float,
    l1_present: bool,
    l2_shared_categories: list[str],
    l3_summary: str,
    l3_confidence: float,
    why_it_matters: str,
    provenance: dict,
) -> dict:
    source_workspace_id = source_meta["workspace_id"]
    target_workspace_id = target_meta["workspace_id"]
    source_card = source_meta["card"]
    target_card = target_meta["card"]
    strength_band = "strong" if status == "confirmed" or score >= 0.70 else "medium" if score >= 0.45 else "weak"
    domains = sorted([source_workspace_id, target_workspace_id])
    source_artifacts_url = f"/{source_workspace_id}/artifacts?card={source_card['id']}"
    target_artifacts_url = f"/{target_workspace_id}/artifacts?card={target_card['id']}"

    return {
        "id": _bridge_id(source_workspace_id, source_card["id"], target_workspace_id, target_card["id"]),
        "status": status,
        "strength_band": strength_band,
        "score": score,
        "relation": relation,
        "domains": domains,
        "workspaces": [source_workspace_id, target_workspace_id],
        "source": _card_projection(source_workspace_id, source_card),
        "target": _card_projection(target_workspace_id, target_card),
        "signals": {
            "l1_structural": l1_present,
            "l2_category_overlap": {
                "present": bool(l2_shared_categories),
                "shared_categories": l2_shared_categories,
                "overlap_score": round(min(1.0, len(l2_shared_categories) / 3) if l2_shared_categories else 0.0, 2),
            },
            "l3_reasoned": {
                "present": bool(l3_summary),
                "summary": l3_summary,
                "confidence": round(l3_confidence, 2),
            },
        },
        "provenance": provenance,
        "why_it_matters": why_it_matters,
        "drilldown": {
            "comparison_domains": domains,
            "source_artifacts_url": source_artifacts_url,
            "target_artifacts_url": target_artifacts_url,
        },
    }


def _upsert_bridge(bridges_by_key: dict[tuple, dict], bridge: dict) -> None:
    key = _canonical_key(bridge)
    existing = bridges_by_key.get(key)
    if existing is None:
        bridges_by_key[key] = bridge
        return

    if existing["status"] != "confirmed" and bridge["status"] == "confirmed":
        preferred, other = bridge, existing
    else:
        preferred, other = existing, bridge

    preferred["score"] = max(preferred["score"], other["score"])
    preferred["strength_band"] = _preferred_strength_band(preferred, other)
    preferred["signals"] = _merge_signals(preferred["signals"], other["signals"])
    preferred["why_it_matters"] = preferred.get("why_it_matters") or other.get("why_it_matters", "")
    preferred["provenance"] = _merge_provenance(preferred["provenance"], other["provenance"])
    if bridge["status"] == "confirmed":
        preferred["status"] = "confirmed"
    bridges_by_key[key] = preferred


def _build_summary(bridges: list[dict]) -> dict:
    totals = {
        "confirmed": sum(1 for bridge in bridges if bridge["status"] == "confirmed"),
        "strong_candidates": sum(1 for bridge in bridges if bridge["status"] == "candidate" and bridge["strength_band"] == "strong"),
        "medium_candidates": sum(1 for bridge in bridges if bridge["status"] == "candidate" and bridge["strength_band"] == "medium"),
        "weak_candidates": sum(1 for bridge in bridges if bridge["status"] == "candidate" and bridge["strength_band"] == "weak"),
    }
    pair_stats: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for bridge in bridges:
        pair_stats[tuple(bridge["domains"])].append(bridge)

    top_pairs = []
    for domains, items in sorted(pair_stats.items()):
        top_pairs.append(
            {
                "domains": list(domains),
                "confirmed": sum(1 for bridge in items if bridge["status"] == "confirmed"),
                "strong_candidates": sum(1 for bridge in items if bridge["status"] == "candidate" and bridge["strength_band"] == "strong"),
                "avg_score": round(sum(bridge["score"] for bridge in items) / len(items), 2),
            }
        )
    top_pairs.sort(key=lambda item: (-item["confirmed"], -item["strong_candidates"], -item["avg_score"], item["domains"][0], item["domains"][1]))

    return {"totals": totals, "top_domain_pairs": top_pairs}


def _resolve_connection_endpoint(card_id: str, owner_workspace_id: str, card_index: dict[str, list[dict]]) -> list[dict]:
    matches = card_index.get(card_id, [])
    local = [match for match in matches if match["workspace_id"] == owner_workspace_id]
    if local:
        return local + [match for match in matches if match["workspace_id"] != owner_workspace_id]
    return matches


def _resolve_candidate_endpoint(card_id: str, workspace_id: str, card_index: dict[str, list[dict]]) -> dict | None:
    matches = [match for match in card_index.get(card_id, []) if match["workspace_id"] == workspace_id]
    if len(matches) != 1:
        return None
    return matches[0]


def _shared_categories(source_card: dict, target_card: dict) -> list[str]:
    return sorted(set(_string_list(source_card.get("content_categories"))) & set(_string_list(target_card.get("content_categories"))))


def _card_projection(workspace_id: str, card: dict) -> dict:
    return {
        "card_id": card["id"],
        "workspace_id": workspace_id,
        "title": card.get("title", ""),
        "epistemic_type": card.get("epistemic_type", ""),
        "confidence": card.get("confidence", 0),
        "lifecycle": card.get("lifecycle", ""),
    }


def _bridge_id(source_workspace_id: str, source_card_id: str, target_workspace_id: str, target_card_id: str) -> str:
    ordered = sorted([(source_workspace_id, source_card_id), (target_workspace_id, target_card_id)])
    return f"{ordered[0][0]}__{ordered[1][0]}__{ordered[0][1]}__{ordered[1][1]}"


def _canonical_key(bridge: dict) -> tuple:
    endpoints = sorted(
        [
            (bridge["source"]["workspace_id"], bridge["source"]["card_id"]),
            (bridge["target"]["workspace_id"], bridge["target"]["card_id"]),
        ]
    )
    return endpoints[0][0], endpoints[0][1], endpoints[1][0], endpoints[1][1], bridge["relation"]


def _preferred_strength_band(primary: dict, secondary: dict) -> str:
    order = {"strong": 3, "medium": 2, "weak": 1}
    return primary["strength_band"] if order[primary["strength_band"]] >= order[secondary["strength_band"]] else secondary["strength_band"]


def _merge_signals(primary: dict, secondary: dict) -> dict:
    l2_primary = primary.get("l2_category_overlap", {})
    l2_secondary = secondary.get("l2_category_overlap", {})
    shared_categories = sorted(
        set(_string_list(l2_primary.get("shared_categories")))
        | set(_string_list(l2_secondary.get("shared_categories")))
    )
    l3_primary = primary.get("l3_reasoned", {})
    l3_secondary = secondary.get("l3_reasoned", {})
    summary = l3_primary.get("summary") or l3_secondary.get("summary", "")
    confidence = max(float(l3_primary.get("confidence", 0.0)), float(l3_secondary.get("confidence", 0.0)))
    return {
        "l1_structural": bool(primary.get("l1_structural") or secondary.get("l1_structural")),
        "l2_category_overlap": {
            "present": bool(shared_categories),
            "shared_categories": shared_categories,
            "overlap_score": round(min(1.0, len(shared_categories) / 3) if shared_categories else 0.0, 2),
        },
        "l3_reasoned": {
            "present": bool(summary),
            "summary": summary,
            "confidence": round(confidence, 2),
        },
    }


def _merge_provenance(primary: dict, secondary: dict) -> dict:
    return {
        "candidate_source": primary.get("candidate_source") or secondary.get("candidate_source", ""),
        "candidate_workspace_id": primary.get("candidate_workspace_id") or secondary.get("candidate_workspace_id", ""),
        "candidate_generated_at": primary.get("candidate_generated_at") or secondary.get("candidate_generated_at", ""),
        "confirmed_via_connection": bool(primary.get("confirmed_via_connection") or secondary.get("confirmed_via_connection")),
        "connection_workspace_id": primary.get("connection_workspace_id") or secondary.get("connection_workspace_id", ""),
    }


def _string_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []