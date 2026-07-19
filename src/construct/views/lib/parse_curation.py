"""Parse <workspace>/curation-reports/CURATION-REPORT-*.md per data-model spec §5.8.

MVP: extracts date, summary first paragraph, and high-level deltas via
heuristic regex. Falls back to zeros if not found.
"""
import re
from pathlib import Path


def parse(workspace: Path, warnings: list) -> list[dict]:
    cur_dir = workspace / "curation-reports"
    if not cur_dir.is_dir():
        return []

    cycles = []
    for md_file in sorted(cur_dir.glob("CURATION-REPORT-*.md")):
        rel = f"{workspace.name}/curation-reports/{md_file.name}"
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError as e:
            warnings.append({"workspace": workspace.name, "file": rel, "reason": f"read error: {e}"})
            continue

        cid = md_file.stem.lower()
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", md_file.name)
        date = date_m.group(1) if date_m else ""

        summary_m = re.search(r"^##\s+Summary\s*\n+(.+?)(?=\n##|\Z)",
                              text, re.MULTILINE | re.DOTALL)
        summary = summary_m.group(1).strip() if summary_m else _first_paragraph(text)

        deltas = {
            "promoted": _grab_int(text, r"Promoted:\s*(\d+)"),
            "archived": _grab_int(text, r"Archived:\s*(\d+)"),
            "decayed": _grab_int(text, r"Decayed:\s*(\d+)"),
            "orphans_resolved": _grab_int(text, r"Orphans resolved:\s*(\d+)"),
            "connections_added": _grab_int(text, r"Connections added:\s*(\d+)"),
            "connections_removed": _grab_int(text, r"Connections removed:\s*(\d+)"),
        }

        cycles.append({
            "id": cid,
            "date": date,
            "summary": summary,
            "deltas": deltas,
            "raw_path": str(md_file.relative_to(workspace)),
        })

    cycles.sort(key=lambda c: c.get("date", ""), reverse=True)
    return {"cycles": cycles}


def _grab_int(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


def _first_paragraph(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""
