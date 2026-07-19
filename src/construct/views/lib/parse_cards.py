"""Parse workspace cards/*.md per data-model spec §5.2."""
import re
from pathlib import Path

from .frontmatter import parse as parse_frontmatter

REQUIRED_FIELDS = {"id", "title", "epistemic_type", "confidence", "source_tier", "lifecycle"}


def parse(workspace: Path, warnings: list) -> list[dict]:
    cards_dir = workspace / "cards"
    if not cards_dir.is_dir():
        return []

    cards = []
    for md_file in sorted(cards_dir.glob("*.md")):
        rel = f"{workspace.name}/cards/{md_file.name}"
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError as e:
            warnings.append({"workspace": workspace.name, "file": str(md_file.relative_to(workspace.parent)), "reason": f"read error: {e}"})
            continue

        try:
            meta, body = parse_frontmatter(text)
        except ValueError as e:
            warnings.append({"workspace": workspace.name, "file": rel, "reason": str(e)})
            continue

        missing = REQUIRED_FIELDS - set(meta.keys())
        if missing:
            warnings.append({"workspace": workspace.name, "file": rel,
                             "reason": f"missing required field(s): {', '.join(sorted(missing))}"})
            continue

        cards.append({
            "id": str(meta["id"]),
            "title": str(meta.get("title", "")),
            "epistemic_type": str(meta["epistemic_type"]),
            "confidence": int(meta["confidence"]),
            "source_tier": int(meta["source_tier"]),
            "lifecycle": str(meta["lifecycle"]),
            "domains": _list(meta.get("domains")),
            "content_categories": _list(meta.get("content_categories")),
            "tags": _list(meta.get("tags")),
            "author": str(meta.get("author", "")),
            "created": str(meta.get("created", "")),
            "last_reviewed": meta.get("last_reviewed"),
            "sources": meta.get("sources", []) if isinstance(meta.get("sources"), list) else [],
            "connects_to": [],  # filled by denormalisation step in generate.py
            "body_markdown": body.rstrip() + "\n",
            "summary_excerpt": _excerpt(body),
        })

    cards.sort(key=lambda c: c["id"])
    return cards


def _list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def _excerpt(body: str, n: int = 200) -> str:
    """First N chars of first prose section, with markdown stripped."""
    # Find Summary section if present
    m = re.search(r"^##\s+Summary\s*\n+([^\n#].+?)(?=\n##|\Z)", body, re.MULTILINE | re.DOTALL)
    text = m.group(1) if m else body
    # Strip markdown emphasis, links, headers
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > n:
        text = text[: n - 1].rstrip() + "…"
    return text
