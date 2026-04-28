"""Parse <workspace>/publish/*.md across all workspaces per data-model spec §5.5.

Articles are cross-workspace. Expand source_cards from raw IDs to objects
with title/type/confidence/contribution by joining against all parsed cards.
"""
import re
from pathlib import Path

from .frontmatter import parse as parse_frontmatter


def parse(install_root: Path, workspaces: list[Path], workspace_data: dict, warnings: list) -> dict:
    articles = []
    # Build a global card index for source_cards expansion
    card_index: dict[str, tuple[str, dict]] = {}
    for ws_id, ws in workspace_data.items():
        for card in ws.get("cards", []):
            card_index[card["id"]] = (ws_id, card)

    for ws_path in workspaces:
        ws_id = ws_path.name
        publish_dir = ws_path / "publish"
        if not publish_dir.is_dir():
            continue
        for md_file in sorted(publish_dir.glob("*.md")):
            rel = f"{ws_id}/publish/{md_file.name}"
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError as e:
                warnings.append({"workspace": ws_id, "file": rel, "reason": f"read error: {e}"})
                continue

            article = _parse_one(text, ws_id, md_file, card_index, warnings, rel)
            if article:
                articles.append(article)

    articles.sort(key=lambda a: a.get("date", ""), reverse=True)
    return {"articles": articles}


def _parse_one(text: str, ws_id: str, md_file: Path, card_index: dict, warnings: list, rel: str) -> dict | None:
    if not text.startswith("---"):
        warnings.append({"workspace": ws_id, "file": rel, "reason": "missing frontmatter"})
        return None
    try:
        meta, body = parse_frontmatter(text)
    except ValueError as e:
        warnings.append({"workspace": ws_id, "file": rel, "reason": str(e)})
        return None

    aid = md_file.stem
    title = str(meta.get("title", aid))
    atype = str(meta.get("type", ""))
    status = str(meta.get("status", "draft"))
    date = str(meta.get("date", ""))
    domains = _list(meta.get("domains")) or [ws_id]
    confidence_floor = int(meta.get("confidence_floor", 0)) if isinstance(meta.get("confidence_floor"), int) else 0

    source_card_ids = _list(meta.get("source_cards"))
    contributions = _extract_contributions(body)

    expanded = []
    workspaces_for_article: set[str] = set()
    for cid in source_card_ids:
        if cid in card_index:
            src_ws, card = card_index[cid]
            workspaces_for_article.add(src_ws)
            expanded.append({
                "id": cid,
                "workspace_id": src_ws,
                "title": card["title"],
                "epistemic_type": card["epistemic_type"],
                "confidence": card["confidence"],
                "contribution": contributions.get(cid, ""),
            })
        else:
            expanded.append({"id": cid, "status": "missing"})

    return {
        "id": aid,
        "title": title,
        "type": atype,
        "status": status,
        "date": date,
        "workspaces": sorted(workspaces_for_article) or [ws_id],
        "domains": domains,
        "confidence_floor": confidence_floor,
        "source_cards": expanded,
        "body_markdown": body.rstrip() + "\n",
        "excerpt": _excerpt(body),
        "raw_path": rel,
    }


def _list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def _excerpt(body: str, n: int = 280) -> str:
    text = re.sub(r"[*_`]+", "", body)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > n:
        text = text[: n - 1].rstrip() + "…"
    return text


def _extract_contributions(body: str) -> dict[str, str]:
    """Parse the Sources table for per-card contribution notes."""
    contribs = {}
    in_sources = False
    for line in body.splitlines():
        if line.strip().lower().startswith("## sources"):
            in_sources = True
            continue
        if in_sources and line.startswith("##"):
            break
        if in_sources and "|" in line and "---" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Format: | [title](path/card-id.md) | type | conf | contrib |
            if len(cells) >= 4:
                m = re.search(r"/([\w\-]+)\.md", cells[0])
                if m:
                    contribs[m.group(1)] = cells[3]
    return contribs
