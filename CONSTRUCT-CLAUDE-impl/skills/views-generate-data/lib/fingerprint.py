"""Per-workspace fingerprinting for incremental regeneration.

Computes a fast hash from (relative-path, mtime_ns, size) of every
source file in a workspace.  Stat calls only — no file reads.
"""
import hashlib
import json
from pathlib import Path

# Directories / files inside a workspace that contribute to views data.
_SOURCE_GLOBS = [
    "cards/**/*",
    "connections.json",
    "domains.yaml",
    "governance.yaml",
    "search-seeds.json",
    "digests/**/*",
    "refs/**/*",
    "log/events.jsonl",
]


def workspace_fingerprint(ws_path: Path) -> str:
    """Return an 8-char hex fingerprint for a workspace's source files."""
    entries: list[tuple[str, int, int]] = []
    for pattern in _SOURCE_GLOBS:
        for p in sorted(ws_path.glob(pattern)):
            if not p.is_file():
                continue
            rel = str(p.relative_to(ws_path))
            stat = p.stat()
            entries.append((rel, stat.st_mtime_ns, stat.st_size))
    h = hashlib.sha256()
    h.update(json.dumps(entries, sort_keys=False).encode("utf-8"))
    return h.hexdigest()[:8]


def config_fingerprint(install_root: Path) -> str:
    """Fingerprint the install-level config.yaml (affects SPA settings)."""
    cfg = install_root / ".construct" / "config.yaml"
    if not cfg.is_file():
        return "none"
    stat = cfg.stat()
    h = hashlib.sha256()
    h.update(f"{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8"))
    return h.hexdigest()[:8]


def articles_fingerprint(install_root: Path) -> str:
    """Fingerprint the cross-workspace articles/ directory."""
    arts_dir = install_root / "articles"
    if not arts_dir.is_dir():
        return "none"
    entries: list[tuple[str, int, int]] = []
    for p in sorted(arts_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(arts_dir))
        stat = p.stat()
        entries.append((rel, stat.st_mtime_ns, stat.st_size))
    if not entries:
        return "none"
    h = hashlib.sha256()
    h.update(json.dumps(entries, sort_keys=False).encode("utf-8"))
    return h.hexdigest()[:8]


def load_meta(data_dir: Path) -> dict:
    """Load _build_meta.json if it exists."""
    meta_path = data_dir / "_build_meta.json"
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_meta(data_dir: Path, meta: dict) -> None:
    """Write _build_meta.json atomically."""
    meta_path = data_dir / "_build_meta.json"
    tmp = meta_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(meta, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(meta_path)
