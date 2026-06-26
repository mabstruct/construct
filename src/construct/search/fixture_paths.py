"""Resolve mock search fixture directories for workspace and package defaults."""

from __future__ import annotations

from pathlib import Path

_BUILTIN_ALIASES = frozenset({"builtin", "@builtin", "@package"})
_LEGACY_REPO_FIXTURE_DIR = "tests/fixtures/search"


def package_fixture_dir() -> Path:
    """Return bundled mock fixtures shipped inside the construct package."""
    return Path(__file__).resolve().parent / "fixtures"


def resolve_fixture_dir(fixture_dir: str, workspace: Path | None = None) -> Path:
    """Resolve a configured fixture_dir to an existing directory.

    Resolution order:
    1. Built-in aliases and legacy repo template path → package fixtures
    2. Absolute path that exists
    3. Path relative to workspace root (when provided)
    4. Path relative to current working directory
    5. Package fixtures as safe fallback when nothing else exists
    """
    raw = fixture_dir.strip()
    normalized = raw.lower()

    if normalized in _BUILTIN_ALIASES or raw.replace("\\", "/") == _LEGACY_REPO_FIXTURE_DIR:
        return package_fixture_dir()

    path = Path(raw)
    if path.is_absolute() and path.is_dir():
        return path

    candidates: list[Path] = []
    if workspace is not None:
        candidates.append(workspace / raw)
    candidates.append(Path.cwd() / raw)

    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()

    return package_fixture_dir()
