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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ValidationError

# D-08: the views source parsers ship inside the package. The distribution
# packages only ``src/construct``, so the previous deployed-skill-directory
# lookup raised ImportError on an installed CONSTRUCT.
from construct.views.lib import (
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
from construct.views.models import (
    ArticlesFile,
    BridgesFile,
    CardsFile,
    ConnectionsFile,
    CurationHistoryFile,
    DigestsFile,
    DomainsFile,
    EventsFile,
    StatsFile,
    WorkspaceStatsFile,
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

# Each entry: (rel_path_in_data_dir, model_class, adapter from raw parser dict to
# the model's field names).
#
# These two tables are the SINGLE definition of the writer→validator projection:
# ``_validate_file_data`` iterates them rather than repeating each adapter inline.
# They used to be dead code duplicated verbatim inside that function, which is
# exactly the drift hazard the known writer-vs-validator divergence already
# demonstrates — a fix applied to one copy would not have reached the other.
_Adapter = Callable[[dict], dict]


def _as_written(data: dict) -> dict:
    """The identity adapter — validate exactly the bytes the writer will write.

    D-01: every adapter that used to sit here renamed writer keys into a model
    field set that disagreed with them, so ``generate`` validated a projection it
    then discarded and wrote the raw parser dict instead. ``views validate``
    applied the same models to those raw bytes with no adapter and rejected them.
    With the models conformed to the writer, the adapter has nothing left to do,
    and the two commands finally gate the same object.
    """
    return data


_FILE_MODEL_MAP: list[tuple[str, type[BaseModel], _Adapter]] = [
    ("bridges.json", BridgesFile, _as_written),
    ("domains.json", DomainsFile, _as_written),
    ("articles.json", ArticlesFile, _as_written),
    ("stats.json", StatsFile, _as_written),
]

# Per-workspace files share a common pattern; keyed on the filename, matched
# against the trailing ``<ws_id>/<filename>`` segment of the relative path.
#
# The global ``stats.json`` above and the ``stats.json`` below are different
# files with different writers and different models. ``_validate_file_data``
# keeps them apart by matching the global table on an exact path and this one on
# a trailing ``/<filename>``, so a per-workspace file can never be validated
# against the global contract or vice versa.
_PER_WS_FILES: list[tuple[str, type[BaseModel], _Adapter]] = [
    ("cards.json", CardsFile, _as_written),
    ("connections.json", ConnectionsFile, _as_written),
    ("stats.json", WorkspaceStatsFile, _as_written),
    ("curation-history.json", CurationHistoryFile, _as_written),
    ("digests.json", DigestsFile, _as_written),
    ("events.json", EventsFile, _as_written),
]


# ---------------------------------------------------------------------------
# Install-root guard
# ---------------------------------------------------------------------------

#: The file whose presence marks a directory as a CONSTRUCT install root.
INSTALL_ROOT_MARKER = "AGENTS.md"


def install_root_error(install_root: Path | str) -> str | None:
    """Return why *install_root* is not a CONSTRUCT install root, or ``None``.

    Every entrypoint that can be handed an arbitrary path must call this BEFORE
    ``generate()``: the generator creates ``views/build/data/`` under whatever it
    is given, so an unguarded path argument scaffolds a views tree in an
    unrelated directory and then reports an empty build as a success. The
    ``views.generate_data`` handler's ``install_root`` is agent-supplied over MCP,
    and the CLI option defaults to the process working directory.

    The returned reason deliberately does **not** embed the path, so a caller
    that must not echo filesystem locations (the MCP surface) can surface it
    verbatim while a local caller (the CLI) appends the path itself.
    """
    root = Path(install_root)
    if not root.is_dir():
        return "install root is not an existing directory"
    if not (root / INSTALL_ROOT_MARKER).is_file():
        return f"not a CONSTRUCT installation: missing {INSTALL_ROOT_MARKER}"
    return None


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
    # NOT created yet (CR-03): creating the output tree used to be this function's
    # very first filesystem action, before anything had established that the
    # argument is a CONSTRUCT install root. Discovery and the incremental gate
    # below are read-only and tolerate a missing data_dir, so the directory is
    # created at the point of the first write instead.

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
        except Exception as exc:  # noqa: BLE001 — a bad config must not fail the build
            # WR-11: this used to be a bare `pass`, so an operator who set
            # `views.workspace_landing: wiki` with a YAML typo silently got
            # `dashboard` with nothing in the warnings log and nothing on stdout.
            # refresh.py::_read_views_config logs its equivalent failure; the two
            # config readers in the same package should not disagree on this.
            _warnings.append({
                "workspace": "(root)",
                "file": ".construct/config.yaml",
                "reason": f"unreadable views config: {type(exc).__name__}",
            })
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

    # First filesystem mutation of the run — everything above is read-only.
    data_dir.mkdir(parents=True, exist_ok=True)

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

    # A run that rejected any file did NOT produce the build it computed. Neither
    # the version pointer nor the fingerprint cache may be advanced for it: writing
    # version.json would tell the SPA to refetch data files that were never
    # updated, and saving the source fingerprints would make the *next* run
    # short-circuit at the incremental gate above and return success with zero
    # files written — permanently, until a source file is touched or
    # _build_meta.json is deleted. That latch also silently converts
    # refresh_views' "failed" into "succeeded" on every subsequent run.
    build_ok = not validation_errors

    # 8. version.json — only advertise a build whose files actually landed.
    if build_ok:
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

    # 10. Save build meta — only cache fingerprints for a build that succeeded, so
    #     a failed run is retried on the next invocation rather than latched.
    if build_ok:
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
        # Some parsers already qualify ``file`` with the workspace name. Only
        # prepend the workspace id when it is not already the leading segment,
        # otherwise the warning names the workspace twice (Pitfall 4).
        if f == ws or f.startswith(f"{ws}/"):
            warnings_list.append(f"{f}: {r}")
        else:
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

    Drives off ``_FILE_MODEL_MAP`` / ``_PER_WS_FILES`` so the writer→validator
    projection is defined in exactly one place (WR-04).

    D-18: per-workspace ``stats.json`` and ``curation-history.json`` used to have
    no table entry and fell through to ``False`` — written with no gate at all.
    Both now carry a model. A file that still has no entry (``version.json``,
    ``_build_meta.json``, the warnings log) is build metadata rather than view
    data and is deliberately not validated here.
    """
    for name, model_class, adapt in _FILE_MODEL_MAP:
        if rel_path == name:
            return _try_validate(model_class, adapt(raw_data), rel_path, errors)

    for name, model_class, adapt in _PER_WS_FILES:
        if rel_path.endswith(f"/{name}"):
            return _try_validate(model_class, adapt(raw_data), rel_path, errors)

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


def _cards_are_well_shaped(cards) -> bool:
    """Whether a cached ``cards`` payload is safe for the downstream consumers.

    ``views/build/data/`` is written by this generator but read by the SPA, by
    ``views validate`` and by users, so it is an untrusted boundary on the way back
    in. Freshly parsed cards are coerced by ``parse_cards``; the cache path bypasses
    the parser entirely, so a structurally wrong but syntactically valid JSON file
    used to reach ``c["id"]`` (KeyError) and
    ``sum(c["confidence"] for c in cards)`` (TypeError) and crash out of
    ``generate()`` altogether.
    """
    if not isinstance(cards, list):
        return False
    return all(
        isinstance(c, dict)
        and isinstance(c.get("id"), str)
        and isinstance(c.get("confidence"), int)
        and not isinstance(c.get("confidence"), bool)
        for c in cards
    )


def _load_cached_workspace(data_dir: Path, ws_id: str) -> dict | None:
    """Load a workspace's previously generated payload, or ``None`` on any problem.

    ``None`` means "cache miss" and the caller re-parses from source, so every
    malformed-cache path below is a safe degradation rather than an error.
    """
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
        except (json.JSONDecodeError, OSError):
            return None
        # A top-level non-object is not an envelope and not a payload.
        if not isinstance(envelope_data, dict):
            return None
        data = envelope_data.get("data", envelope_data)
        if key == "curation":
            result[key] = data if isinstance(data, dict) else {"cycles": data}
            continue

        # Every remaining key indexes into a mapping; a non-dict payload would
        # raise AttributeError straight out of generate().
        if not isinstance(data, dict):
            return None

        if key == "cards":
            cards = data.get("cards", [])
            if not _cards_are_well_shaped(cards):
                return None  # treat a malformed cache as a cache miss
            result[key] = cards
        elif key == "digests":
            digests = data.get("digests", [])
            if not isinstance(digests, list):
                return None
            result[key] = digests
        elif key == "events":
            events = data.get("events", [])
            if not isinstance(events, list):
                return None
            result[key] = events
        else:
            result[key] = data

    stats_path = ws_dir / "stats.json"
    if stats_path.is_file():
        try:
            stats_env = json.loads(stats_path.read_text(encoding="utf-8"))
            stats_data = stats_env.get("data", stats_env) if isinstance(stats_env, dict) else {}
            totals = stats_data.get("totals", {}) if isinstance(stats_data, dict) else {}
            papers = totals.get("papers", 0) if isinstance(totals, dict) else 0
            result["refs_count"] = papers if isinstance(papers, int) else 0
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
    guard = install_root_error(root)
    if guard is not None:
        print(f"{guard} (at {root})", file=sys.stderr)
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
