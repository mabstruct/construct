"""Workspace discovery — find subdirectories that look like CONSTRUCT workspaces.

Per data-generation spec §4.1: a subdirectory is a workspace if it contains
`cards/` OR `domains.yaml` OR (`connections.json` AND `governance.yaml`).
Excludes .construct, views, dotfiles, common cruft.
"""
from pathlib import Path

EXCLUDED_NAMES = {
    ".construct", "views", "node_modules", ".venv", ".git",
    ".pytest_cache", "__pycache__", "dist", "build", ".vscode",
    ".idea", ".DS_Store",
}


def discover_workspaces(install_root: Path) -> list[Path]:
    """Return sorted list of workspace directory Paths."""
    workspaces = []
    for entry in sorted(install_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.name in EXCLUDED_NAMES:
            continue
        if _is_workspace(entry):
            workspaces.append(entry)
    return workspaces


def _is_workspace(path: Path) -> bool:
    if (path / "cards").is_dir():
        return True
    if (path / "domains.yaml").is_file():
        return True
    if (path / "connections.json").is_file() and (path / "governance.yaml").is_file():
        return True
    return False
