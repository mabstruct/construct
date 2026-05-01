#!/usr/bin/env python3
"""views-generate-data — derive views/build/data/ from CONSTRUCT workspace files.

Sole writer to views/build/data/ and views/build/version.json
(architecture-overview invariant I1).

Usage: python3 generate.py <install-root>
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running this file directly OR as `-m skill.views-generate-data.generate`
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Defense in depth: friendly error if invoked directly without PyYAML.
# Normal path is via run.sh which auto-bootstraps a per-skill venv.
try:
    import yaml  # noqa: F401
except ImportError:
    print(
        "Error: PyYAML is required but not available in this Python interpreter.\n"
        "Run via the wrapper instead, which auto-bootstraps a per-skill venv:\n"
        "    bash <install-root>/.construct/skills/views-generate-data/run.sh <install-root>",
        file=sys.stderr,
    )
    sys.exit(1)

from lib import (  # noqa: E402
    build_id as build_id_mod,
    compute_stats,
    discover,
    envelope,
    parse_articles,
    parse_cards,
    parse_connections,
    parse_curation,
    parse_digests,
    parse_domains,
    parse_events,
)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: generate.py <install-root>", file=sys.stderr)
        return 2

    install_root = Path(sys.argv[1]).resolve()
    if not (install_root / "AGENTS.md").is_file():
        print(f"Not a CONSTRUCT installation: missing AGENTS.md at {install_root}",
              file=sys.stderr)
        return 1

    build_dir = install_root / "views" / "build"
    if not build_dir.is_dir():
        print("views/build/ not found. Run views-build first.", file=sys.stderr)
        return 1

    data_dir = build_dir / "data"
    data_dir.mkdir(exist_ok=True)

    warnings: list[dict] = []

    # 1. Discover workspaces
    workspaces = discover.discover_workspaces(install_root)

    # 2. Per-workspace parsing
    workspace_data: dict[str, dict] = {}
    for ws in workspaces:
        ws_id = ws.name
        cards = parse_cards.parse(ws, warnings)
        connections = parse_connections.parse(ws, warnings)
        parse_connections.denormalize_into_cards(cards, connections["connections"])

        digests = parse_digests.parse(ws, warnings, cards=cards)
        events = parse_events.parse(ws, warnings)
        curation = parse_curation.parse(ws, warnings)

        refs_dir = ws / "refs"
        refs_count = (
            sum(1 for _ in refs_dir.glob("*.json")) if refs_dir.is_dir() else 0
        )

        workspace_data[ws_id] = {
            "cards": cards,
            "connections": connections,
            "digests": digests,
            "events": events,
            "curation": curation,
            "refs_count": refs_count,
        }

    # 3. Cross-workspace artefacts (need workspace_data populated first)
    domains = parse_domains.parse(install_root, workspace_data, warnings)
    articles = parse_articles.parse(install_root, workspaces, workspace_data, warnings)

    # Decorate per-workspace data with article count for stats
    for ws_id in workspace_data:
        workspace_data[ws_id]["articles_count"] = sum(
            1 for a in articles["articles"] if ws_id in a.get("workspaces", [])
        )

    # 4. Stats
    global_stats = compute_stats.compute_global(workspace_data, articles["articles"])
    workspace_stats = {
        ws_id: compute_stats.compute_workspace(ws)
        for ws_id, ws in workspace_data.items()
    }

    # 5. Assemble files (data field only; envelope wrapped after build_id)
    files: dict[str, dict] = {
        "domains.json": domains,
        "articles.json": articles,
        "stats.json": global_stats,
    }
    for ws_id, ws in workspace_data.items():
        files[f"{ws_id}/cards.json"] = {"cards": ws["cards"]}
        files[f"{ws_id}/connections.json"] = ws["connections"]
        files[f"{ws_id}/digests.json"] = {"digests": ws["digests"]}
        files[f"{ws_id}/events.json"] = {"events": ws["events"]}
        files[f"{ws_id}/stats.json"] = workspace_stats[ws_id]
        files[f"{ws_id}/curation-history.json"] = ws["curation"] if isinstance(
            ws["curation"], dict
        ) else {"cycles": ws["curation"]}

    # 6. Compute build_id (excludes generated_at — happens after envelope wrapping)
    build_id = build_id_mod.compute(files)

    # 7. Wrap with envelope and write atomically
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for rel_path, data in files.items():
        full = data_dir / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        ws_id = rel_path.split("/")[0] if "/" in rel_path else None
        env = envelope.wrap(data, generated_at, build_id, ws_id)
        _write_atomic(full, env)

    # 8. version.json
    _write_atomic(build_dir / "version.json", {
        "schema_version": envelope.SCHEMA_VERSION,
        "build_id": build_id,
        "generated_at": generated_at,
    })

    # 9. Warnings log
    warnings_path = data_dir / "_generation-warnings.log"
    if warnings:
        _write_atomic(warnings_path, warnings)
    elif warnings_path.exists():
        warnings_path.unlink()

    # 10. Report
    _print_report(workspaces, workspace_data, articles["articles"], build_id, warnings)
    return 0


def _write_atomic(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
    tmp.write_text(payload + "\n", encoding="utf-8")
    tmp.replace(path)


def _print_report(workspaces, workspace_data, articles, build_id, warnings) -> None:
    print(f"workspaces: {len(workspaces)}")
    for ws in workspaces:
        d = workspace_data[ws.name]
        n_cards = len(d["cards"])
        n_conns = len(d["connections"].get("connections", []))
        n_digests = len(d["digests"])
        n_arts = d.get("articles_count", 0)
        print(f"  {ws.name}: {n_cards} cards, {n_conns} connections, "
              f"{n_digests} digests, {n_arts} articles")
    print(f"global: {len(articles)} articles total")
    print(f"build_id: {build_id}")
    if warnings:
        print(f"warnings: {len(warnings)}")
        for w in warnings[:5]:
            ws = w.get("workspace", "?")
            f = w.get("file", "?")
            r = w.get("reason", "?")
            print(f"  {ws}/{f}: {r}")
        if len(warnings) > 5:
            print(f"  … and {len(warnings) - 5} more "
                  f"(see views/build/data/_generation-warnings.log)")
    else:
        print("warnings: none")


if __name__ == "__main__":
    sys.exit(main())
