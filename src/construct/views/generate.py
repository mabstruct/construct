"""Schema-validated views data generator.

Validates each output file against its Pydantic contract model before atomic
write per D-02. Wraps results in a ``GenerateReport`` dataclass.

Usage::

    from pathlib import Path
    from construct.views.generate import generate

    report = generate(Path("test-ws/my-construct"))
    print(report.success, report.validation_errors)

Can also be invoked as a CLI::

    python3 -m construct.views.generate <install-root>
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from construct.views.models import (
    ArticlesFile,
    BridgesFile,
    CardsFile,
    ConnectionsFile,
    DigestsFile,
    DomainsFile,
    EventsFile,
    StatsFile,
    ViewsEnvelope,
)

# ---------------------------------------------------------------------------
# Path setup — import the existing construct-views-generate-data skill lib
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SKILL_LIB = (
    _PROJECT_ROOT
    / "CONSTRUCT-CLAUDE-impl"
    / "claude"
    / "skills"
    / "construct-views-generate-data"
)
if str(_SKILL_LIB) not in sys.path:
    sys.path.insert(0, str(_SKILL_LIB))

# pylint: disable=wrong-import-position,unused-import
from lib import (  # type: ignore[import-untyped]  # noqa: E402
    build_id as build_id_mod,
    compute_stats,
    discover,
    envelope,
    fingerprint as fp,
    parse_articles,
    parse_bridges,
    parse_cards,
    parse_connections,
    parse_curation,
    parse_digests,
    parse_domains,
    parse_events,
)


# ---------------------------------------------------------------------------
# Report type
# ---------------------------------------------------------------------------


@dataclass
class GenerateReport:
    """Result of a generate() run."""

    success: bool
    build_id: str
    workspace_stats: dict = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_files_written: int = 0


# ---------------------------------------------------------------------------
# Model map — which Pydantic model validates each output file's data field
# ---------------------------------------------------------------------------

# Each entry: (rel_path_in_data_dir, model_class, lambda to extract inner data)
_FILE_MODEL_MAP: list[tuple[str, type, callable]] = [
    ("bridges.json", BridgesFile, lambda d: {"bridges": d.get("bridges", []), "summary": d.get("summary", {})}),
    ("domains.json", DomainsFile, lambda d: {"settings": d.get("settings", {}), "domains": d.get("domains", [])}),
    ("articles.json", ArticlesFile, lambda d: {"articles": d.get("articles", [])}),
    ("stats.json", StatsFile, lambda d: {
        "total_cards": d.get("totals", {}).get("cards", 0),
        "total_connections": d.get("totals", {}).get("connections", 0),
        "total_domains": d.get("totals", {}).get("workspaces", 0),
        "total_digests": d.get("totals", {}).get("digests", 0),
        "total_articles": d.get("totals", {}).get("articles", len(d.get("articles", []))),
        "cards_by_domain": {},
    }),
]

# Per-workspace files share a common pattern
_PER_WS_FILES: list[tuple[str, type, callable]] = [
    ("cards.json", CardsFile, lambda d: {
        "cards": [
            {
                "id": c["id"],
                "title": c.get("title", ""),
                "epistemic_type": c.get("epistemic_type", ""),
                "confidence": c.get("confidence", 0),
                "source_tier": c.get("source_tier", 0),
                "lifecycle": c.get("lifecycle", ""),
                "domains": c.get("domains", []),
                "summary": c.get("summary_excerpt", c.get("body_markdown", "")),
                "connections": c.get("connects_to", []),
                "content_categories": c.get("content_categories", []),
            }
            for c in d.get("cards", [])
        ],
    }),
    ("connections.json", ConnectionsFile, lambda d: {
        "connections": [
            {
                "source": c.get("source", ""),
                "target": c.get("target", ""),
                "type": c.get("type", ""),
                "created_at": c.get("created", ""),
                "created_by": c.get("author", ""),
                "note": c.get("note"),
            }
            for c in d.get("connections", [])
        ],
    }),
    ("digests.json", DigestsFile, lambda d: {
        "digests": [
            {
                "id": digest.get("id", ""),
                "domain_id": digest.get("domain", ""),
                "title": digest.get("theme", ""),
                "generated_at": digest.get("date", ""),
                "card_ids": [],
                "summary": digest.get("summary_text", ""),
            }
            for digest in d.get("digests", [])
        ],
    }),
    ("events.json", EventsFile, lambda d: {
        "events": [
            {
                "timestamp": e.get("timestamp", ""),
                "type": e.get("type", ""),
                "actor": e.get("actor", e.get("author", "")),
                "card_id": e.get("card_id"),
                "details": e.get("details"),
            }
            for e in d.get("events", [])
        ],
    }),
]


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------


def generate(install_root: Path) -> GenerateReport:
    """Run the full views-generate-data pipeline with schema validation.

    Steps:
    1. Discover workspaces and parse all source files (same as skill generator)
    2. Assemble per-file data dicts
    3. Validate each output dict against its Pydantic contract model
    4. Wrap in envelope and write atomically
    5. Return a ``GenerateReport`` summarising success/failure
    """
    validation_errors: list[str] = []
    warnings_list: list[str] = []

    build_dir = install_root / "views" / "build"
    data_dir = build_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover workspaces
    workspaces = discover.discover_workspaces(install_root)

    # 1b. Incremental fingerprinting
    old_meta = fp.load_meta(data_dir)
    old_ws_fps = old_meta.get("workspaces", {})
    new_ws_fps: dict[str, str] = {}
    changed_ws: set[str] = set()

    _warnings: list[dict] = []

    for ws in workspaces:
        ws_id = ws.name
        new_fp = fp.workspace_fingerprint(ws)
        new_ws_fps[ws_id] = new_fp
        if new_fp != old_ws_fps.get(ws_id):
            changed_ws.add(ws_id)

    removed_ws = set(old_ws_fps.keys()) - {ws.name for ws in workspaces}
    cfg_fp = fp.config_fingerprint(install_root)
    arts_fp = fp.articles_fingerprint(install_root)
    config_changed = cfg_fp != old_meta.get("config_fingerprint")
    articles_changed = arts_fp != old_meta.get("articles_fingerprint")

    if not changed_ws and not removed_ws and not config_changed and not articles_changed:
        return GenerateReport(
            success=True,
            build_id=old_meta.get("build_id", ""),
            total_files_written=0,
        )

    # 2. Per-workspace parsing
    workspace_data: dict[str, dict] = {}
    for ws in workspaces:
        ws_id = ws.name
        if ws_id in changed_ws:
            cards = parse_cards.parse(ws, _warnings)
            connections = parse_connections.parse(ws, _warnings)
            parse_connections.denormalize_into_cards(cards, connections["connections"])
            digests = parse_digests.parse(ws, _warnings, cards=cards)
            events = parse_events.parse(ws, _warnings)
            curation = parse_curation.parse(ws, _warnings)

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
        else:
            cached = _load_cached_workspace(data_dir, ws_id)
            if cached is not None:
                workspace_data[ws_id] = cached
            else:
                changed_ws.add(ws_id)
                cards = parse_cards.parse(ws, _warnings)
                connections = parse_connections.parse(ws, _warnings)
                parse_connections.denormalize_into_cards(cards, connections["connections"])
                digests = parse_digests.parse(ws, _warnings, cards=cards)
                events = parse_events.parse(ws, _warnings)
                curation = parse_curation.parse(ws, _warnings)
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

    # 3. Cross-workspace artefacts
    domains = parse_domains.parse(install_root, workspace_data, _warnings)
    articles = parse_articles.parse(install_root, workspaces, workspace_data, _warnings)

    config_path = install_root / ".construct" / "config.yaml"
    spa_settings = {"workspace_landing": "dashboard"}
    if config_path.is_file():
        try:
            import yaml  # type: ignore[import-untyped]
            cfg = yaml.safe_load(config_path.read_text()) or {}
            views_cfg = cfg.get("views", {})
            if views_cfg.get("workspace_landing") in ("dashboard", "wiki"):
                spa_settings["workspace_landing"] = views_cfg["workspace_landing"]
        except Exception:
            pass
    domains["settings"] = spa_settings

    for ws_id in workspace_data:
        workspace_data[ws_id]["articles_count"] = sum(
            1 for a in articles["articles"] if ws_id in a.get("workspaces", [])
        )

    # 4. Stats and bridges
    global_stats = compute_stats.compute_global(workspace_data, articles["articles"])
    workspace_stats = {
        ws_id: compute_stats.compute_workspace(ws)
        for ws_id, ws in workspace_data.items()
    }
    bridges = parse_bridges.build(workspaces, workspace_data, _warnings)

    # 5. Assemble files
    files: dict[str, dict] = {
        "domains.json": domains,
        "articles.json": articles,
        "stats.json": global_stats,
        "bridges.json": bridges,
    }
    for ws_id, ws in workspace_data.items():
        files[f"{ws_id}/cards.json"] = {"cards": ws["cards"]}
        files[f"{ws_id}/connections.json"] = ws["connections"]
        files[f"{ws_id}/digests.json"] = {"digests": ws["digests"]}
        files[f"{ws_id}/events.json"] = {"events": ws["events"]}
        files[f"{ws_id}/stats.json"] = workspace_stats[ws_id]
        ws_curation = ws["curation"]
        if isinstance(ws_curation, dict):
            files[f"{ws_id}/curation-history.json"] = ws_curation
        else:
            files[f"{ws_id}/curation-history.json"] = {"cycles": ws_curation}

    # 6. Compute build_id
    build_id = build_id_mod.compute(files)

    # 7. Validate and write
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_files_written = 0

    for rel_path, raw_data in files.items():
        full = data_dir / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)

        # Validate the data field against its model contract
        error = _validate_file_data(rel_path, raw_data, validation_errors)
        if error:
            continue  # skip write — schema mismatch

        ws_id = rel_path.split("/")[0] if "/" in rel_path else None
        env = envelope.wrap(raw_data, generated_at, build_id, ws_id)
        _write_atomic(full, env)
        total_files_written += 1

    # 8. version.json
    _write_atomic(
        build_dir / "version.json",
        {
            "schema_version": envelope.SCHEMA_VERSION,
            "build_id": build_id,
            "generated_at": generated_at,
        },
    )
    total_files_written += 1

    # 9. Warnings log
    warnings_path = data_dir / "_generation-warnings.log"
    if _warnings:
        _write_atomic(warnings_path, _warnings)
    elif warnings_path.exists():
        warnings_path.unlink()

    # 10. Save build meta
    fp.save_meta(data_dir, {
        "workspaces": new_ws_fps,
        "config_fingerprint": cfg_fp,
        "articles_fingerprint": arts_fp,
        "build_id": build_id,
    })

    # 11. Clean up removed workspace dirs
    for ws_id in removed_ws:
        removed_dir = data_dir / ws_id
        if removed_dir.is_dir():
            shutil.rmtree(removed_dir)

    # 12. Build workspace stats summary for report
    ws_stats_summary: dict[str, dict] = {}
    for ws_id, ws in workspace_data.items():
        ws_stats_summary[ws_id] = {
            "cards": len(ws.get("cards", [])),
            "connections": len(ws.get("connections", {}).get("connections", [])),
            "digests": len(ws.get("digests", [])),
        }

    # Convert lib warnings to strings
    for w in _warnings:
        ws = w.get("workspace", "?")
        f = w.get("file", "?")
        r = w.get("reason", "?")
        warnings_list.append(f"{ws}/{f}: {r}")

    return GenerateReport(
        success=len(validation_errors) == 0,
        build_id=build_id,
        workspace_stats=ws_stats_summary,
        validation_errors=validation_errors,
        warnings=warnings_list,
        total_files_written=total_files_written,
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_file_data(
    rel_path: str,
    raw_data: dict,
    errors: list[str],
) -> bool:
    """Validate *raw_data* against the appropriate Pydantic model.

    Appends error messages to *errors* and returns ``True`` if a mismatch
    was found (caller should skip the file).
    """
    # Global files
    if rel_path == "bridges.json":
        return _try_validate(
            BridgesFile,
            {"bridges": raw_data.get("bridges", []), "summary": raw_data.get("summary", {})},
            rel_path,
            errors,
        )
    if rel_path == "domains.json":
        return _try_validate(
            DomainsFile,
            {"settings": raw_data.get("settings", {}), "domains": raw_data.get("domains", [])},
            rel_path,
            errors,
        )
    if rel_path == "articles.json":
        return _try_validate(
            ArticlesFile,
            {"articles": raw_data.get("articles", [])},
            rel_path,
            errors,
        )
    if rel_path == "stats.json":
        raw_totals = raw_data.get("totals", {})
        return _try_validate(
            StatsFile,
            {
                "total_cards": raw_totals.get("cards", 0),
                "total_connections": raw_totals.get("connections", 0),
                "total_domains": raw_totals.get("workspaces", 0),
                "total_digests": raw_totals.get("digests", 0),
                "total_articles": raw_totals.get("articles", len(raw_data.get("articles", []))),
                "cards_by_domain": {},
            },
            rel_path,
            errors,
        )

    # Per-workspace files
    if "/cards.json" in rel_path:
        return _try_validate(
            CardsFile,
            {
                "cards": [
                    {
                        "id": c["id"],
                        "title": c.get("title", ""),
                        "epistemic_type": c.get("epistemic_type", ""),
                        "confidence": c.get("confidence", 0),
                        "source_tier": c.get("source_tier", 0),
                        "lifecycle": c.get("lifecycle", ""),
                        "domains": c.get("domains", []),
                        "summary": c.get("summary_excerpt", c.get("body_markdown", "")),
                        "connections": c.get("connects_to", []),
                        "content_categories": c.get("content_categories", []),
                    }
                    for c in raw_data.get("cards", [])
                ],
            },
            rel_path,
            errors,
        )
    if "/connections.json" in rel_path:
        return _try_validate(
            ConnectionsFile,
            {
                "connections": [
                    {
                        "source": c.get("source", ""),
                        "target": c.get("target", ""),
                        "type": c.get("type", ""),
                        "created_at": c.get("created", ""),
                        "created_by": c.get("author", ""),
                        "note": c.get("note"),
                    }
                    for c in raw_data.get("connections", [])
                ],
            },
            rel_path,
            errors,
        )
    if "/digests.json" in rel_path:
        return _try_validate(
            DigestsFile,
            {
                "digests": [
                    {
                        "id": d.get("id", ""),
                        "domain_id": d.get("domain", ""),
                        "title": d.get("theme", ""),
                        "generated_at": d.get("date", ""),
                        "card_ids": [],
                        "summary": d.get("summary_text", ""),
                    }
                    for d in raw_data.get("digests", [])
                ],
            },
            rel_path,
            errors,
        )
    if "/events.json" in rel_path:
        return _try_validate(
            EventsFile,
            {
                "events": [
                    {
                        "timestamp": e.get("timestamp", ""),
                        "type": e.get("type", ""),
                        "actor": e.get("actor", e.get("author", "")),
                        "card_id": e.get("card_id"),
                        "details": e.get("details"),
                    }
                    for e in raw_data.get("events", [])
                ],
            },
            rel_path,
            errors,
        )

    # Per-workspace stats.json — skip for now (uses compute_stats shape)
    if "/stats.json" in rel_path:
        return False  # skip validation for stats.json (matches compute_stats shape)
    if "/curation-history.json" in rel_path:
        return False  # skip validation for curation-history.json

    return False


def _try_validate(
    model_class: type,
    data: dict,
    rel_path: str,
    errors: list[str],
) -> bool:
    """Try validation; append error message and return True on failure."""
    try:
        model_class.model_validate(data)
        return False  # success — no error
    except ValidationError as exc:
        errors.append(f"{rel_path}: {exc}")
        return True  # failure — skip this file
    except Exception as exc:
        errors.append(f"{rel_path}: unexpected error: {exc}")
        return True


# ---------------------------------------------------------------------------
# Atomic write (same pattern as existing generator)
# ---------------------------------------------------------------------------


def _write_atomic(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
    tmp.write_text(payload + "\n", encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Cache loading (match existing generator behaviour)
# ---------------------------------------------------------------------------


def _load_cached_workspace(data_dir: Path, ws_id: str) -> dict | None:
    ws_dir = data_dir / ws_id
    required = {
        "cards.json": "cards",
        "connections.json": "connections",
        "digests.json": "digests",
        "events.json": "events",
        "curation-history.json": "curation",
    }
    result: dict = {}
    for filename, key in required.items():
        path = ws_dir / filename
        if not path.is_file():
            return None
        try:
            envelope_data = json.loads(path.read_text(encoding="utf-8"))
            data = envelope_data.get("data", envelope_data)
        except (json.JSONDecodeError, OSError):
            return None
        if key == "cards":
            result[key] = data.get("cards", [])
        elif key == "digests":
            result[key] = data.get("digests", [])
        elif key == "events":
            result[key] = data.get("events", [])
        elif key == "curation":
            result[key] = data if isinstance(data, dict) else {"cycles": data}
        else:
            result[key] = data

    stats_path = ws_dir / "stats.json"
    if stats_path.is_file():
        try:
            stats_env = json.loads(stats_path.read_text(encoding="utf-8"))
            stats_data = stats_env.get("data", stats_env)
            result["refs_count"] = stats_data.get("totals", {}).get("papers", 0)
        except (json.JSONDecodeError, OSError):
            result["refs_count"] = 0
    else:
        result["refs_count"] = 0

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point: ``python3 -m construct.views.generate <install-root>``."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <install-root>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    if not (root / "AGENTS.md").is_file():
        print(f"Not a CONSTRUCT installation: missing AGENTS.md at {root}",
              file=sys.stderr)
        return 1

    report = generate(root)
    print(f"build_id: {report.build_id}")
    print(f"files_written: {report.total_files_written}")
    print(f"validation_errors: {len(report.validation_errors)}")
    if report.validation_errors:
        for err in report.validation_errors:
            print(f"  ! {err}")
    print(f"warnings: {len(report.warnings)}")
    if report.warnings:
        for w in report.warnings[:5]:
            print(f"  - {w}")
    print(f"success: {report.success}")
    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
