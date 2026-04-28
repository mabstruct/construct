"""Parse workspace digests/*.md per data-model spec §5.4.

Heuristic-based section parsing — best effort. Missing sections produce
parse_status='partial' with whatever cleanly parsed.
"""
import re
from pathlib import Path

from .frontmatter import parse as parse_frontmatter


def parse(workspace: Path, warnings: list) -> list[dict]:
    digests_dir = workspace / "digests"
    if not digests_dir.is_dir():
        return []

    digests = []
    for md_file in sorted(digests_dir.glob("*.md")) + sorted(digests_dir.glob("**/*.md")):
        if md_file in [d for d in digests_dir.glob("*.md")] and md_file in [d for d in digests_dir.glob("**/*.md") if d.parent == digests_dir]:
            # avoid double-listing top-level files
            pass
        rel = f"{workspace.name}/digests/{md_file.relative_to(digests_dir)}"
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError as e:
            warnings.append({"workspace": workspace.name, "file": rel, "reason": f"read error: {e}"})
            continue

        digest = _parse_one(text, rel, md_file, warnings, workspace)
        digests.append(digest)

    # Deduplicate (could happen with the glob workaround above)
    seen = set()
    unique = []
    for d in digests:
        if d["id"] not in seen:
            seen.add(d["id"])
            unique.append(d)

    unique.sort(key=lambda d: d.get("date", ""), reverse=True)
    return unique


def _parse_one(text: str, rel: str, md_file: Path, warnings: list, workspace: Path) -> dict:
    digest_id = md_file.stem
    parse_status = "ok"
    meta: dict = {}
    body = text

    # Try frontmatter first; if absent, fall back to header heuristics
    if text.startswith("---"):
        try:
            meta, body = parse_frontmatter(text)
        except ValueError:
            meta = {}
            body = text

    date = str(meta.get("date") or _extract_field(body, "Date") or "")
    domain = str(meta.get("domain") or _extract_field(body, "Domain") or "")
    theme = str(meta.get("theme") or _extract_first_h1(body) or "")

    summary = _extract_section(body, "Summary")
    summary_text = summary or ""

    counts = _extract_counts(summary or body)
    top_findings = _extract_top_findings(body)
    search_clusters = _extract_clusters_table(body)
    coverage_notes = _extract_section(body, "Coverage Notes") or ""
    suggested = _extract_section(body, "Suggested Adjustments") or ""

    if not summary and not top_findings:
        parse_status = "partial"
        warnings.append({"workspace": workspace.name, "file": rel,
                         "reason": "missing 'Summary' and 'Top Findings' sections"})

    digest = {
        "id": digest_id,
        "date": date,
        "domain": domain,
        "theme": theme,
        "summary_text": summary_text.strip(),
        "papers_found": counts.get("found", 0),
        "papers_ingested": counts.get("ingested", 0),
        "papers_skipped": counts.get("skipped", 0),
        "seed_cards_created": counts.get("seed_cards", 0),
        "top_findings": top_findings,
        "search_clusters": search_clusters,
        "coverage_notes": coverage_notes.strip(),
        "suggested_adjustments": suggested.strip(),
        "raw_path": str(md_file.relative_to(workspace)),
    }
    if parse_status != "ok":
        digest["parse_status"] = parse_status
    return digest


def _extract_field(body: str, name: str) -> str | None:
    m = re.search(rf"\*\*{name}:\*\*\s*(.+)", body)
    return m.group(1).strip() if m else None


def _extract_first_h1(body: str) -> str | None:
    m = re.search(r"^#\s+(.+)", body, re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_section(body: str, name: str) -> str | None:
    pat = rf"^##\s+{re.escape(name)}\s*\n+(.*?)(?=\n##\s+|\Z)"
    m = re.search(pat, body, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else None


def _extract_counts(text: str) -> dict:
    out = {}
    patterns = {
        "found": r"Papers found:\s*(\d+)",
        "ingested": r"Papers ingested:\s*(\d+)",
        "skipped": r"Papers skipped:\s*(\d+)",
        "seed_cards": r"Seed cards created:\s*(\d+)",
    }
    for k, p in patterns.items():
        m = re.search(p, text)
        if m:
            out[k] = int(m.group(1))
    return out


def _extract_top_findings(body: str) -> list[dict]:
    section = _extract_section(body, "Top Findings")
    if not section:
        return []
    findings = []
    # Split on numbered list items like "1. **Title** ..."
    blocks = re.split(r"\n(?=\d+\.\s+)", section)
    for block in blocks:
        m = re.match(r"(\d+)\.\s+\*\*(.+?)\*\*\s*(?:\(([^)]*)\))?\s*\n?(.*)", block, re.DOTALL)
        if not m:
            continue
        rank = int(m.group(1))
        title = m.group(2).strip()
        meta_str = m.group(3) or ""
        summary = m.group(4).strip()
        relevance = 0
        m2 = re.search(r"relevance:\s*(\d+)", meta_str)
        if m2:
            relevance = int(m2.group(1))
        findings.append({
            "rank": rank,
            "title": title,
            "relevance": relevance,
            "summary": summary,
            "url": "",
            "cluster": "",
        })
    return findings


def _extract_clusters_table(body: str) -> list[dict]:
    section = _extract_section(body, "Search Clusters")
    if not section:
        return []
    clusters = []
    for line in section.splitlines():
        # Markdown table rows: | cluster | queries | results | ingested |
        if "|" not in line or "---" in line or "Cluster" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[0]:
            try:
                clusters.append({
                    "id": cells[0],
                    "queries": int(cells[1]) if cells[1].isdigit() else 0,
                    "results": int(cells[2]) if cells[2].isdigit() else 0,
                    "ingested": int(cells[3]) if cells[3].isdigit() else 0,
                })
            except (ValueError, IndexError):
                continue
    return clusters
