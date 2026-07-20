from __future__ import annotations

from pathlib import Path

import pytest

from construct.services.init import DomainInitInput, initialize_workspace


@pytest.fixture
def scaffolded_install_root(tmp_path: Path) -> Path:
    """A freshly scaffolded CONSTRUCT install root containing one workspace.

    Yields the **install root**, not the workspace (D-05):
    ``discover.discover_workspaces`` scans only the *children* of its argument,
    so passing the workspace directory itself finds zero workspaces and silently
    emits empty view data.
    """
    root = tmp_path / "install"
    root.mkdir()
    # The install-root marker every entrypoint guards on (CR-03). A real install
    # root always has one; without it the CLI and the capability handler refuse
    # the path before the generator can create anything under it.
    (root / "AGENTS.md").write_text("# CONSTRUCT test install root\n", encoding="utf-8")

    initialize_workspace(
        root / "demo",
        DomainInitInput(
            domain_id="demo",
            display_name="Demo",
            scope="test scope",
            taxonomy_seeds=["t1"],
            source_priorities=["arxiv"],
            research_seeds=["seed one"],
        ),
    )

    return root
