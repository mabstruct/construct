"""Shared HTTP-surface fixtures — one install root, two workspaces, one token.

Every later plan in Phase 19 drives the app through these fixtures rather than
building its own, so a change to how the app is launched is made once. The
workspaces are built by the **real** services (``initialize_workspace`` /
``create_card``), not by writing fixture JSON: a hand-written tree can satisfy
``_is_workspace`` while being something the rest of the system would reject, and
then the contract tests would be asserting against a shape the product never
produces.

Two workspaces, not one — the allowlist gate's failure message names the known
ids, and a single-entry set cannot distinguish "listed the known ids" from
"echoed the one workspace that exists".
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from construct.api import TOKEN_HEADER
from construct.capabilities.workspaces import set_launch_install_root


#: A fixed, obviously-fake token. Fixed rather than minted so a failing
#: assertion prints something a reader recognises.
API_TOKEN = "test-token-not-a-real-secret"

#: The two workspace ids every HTTP contract test addresses.
WORKSPACE_IDS = ("demo", "second-demo")


def build_workspace(root: Path, name: str) -> Path:
    """A real, discoverable CONSTRUCT workspace holding two cards."""
    from construct.services.init import DomainInitInput, initialize_workspace
    from construct.services.knowledge import create_card

    workspace = root / name
    initialize_workspace(
        workspace,
        DomainInitInput(
            domain_id="test-domain",
            display_name="Test Domain",
            scope="A test domain for the HTTP surface contract tests.",
            taxonomy_seeds=["test-category"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["test research"],
        ),
    )
    for card_id, title in (("card-a", "Card A"), ("card-b", "Card B")):
        create_card(
            workspace,
            {
                "id": card_id,
                "title": title,
                "epistemic_type": "finding",
                "domains": ["test-domain"],
                "content_categories": ["test-category"],
                "confidence": 3,
                "source_tier": 3,
            },
        )
    return workspace


@pytest.fixture
def install_root(tmp_path: Path) -> Path:
    """An install root holding two discoverable workspaces.

    The ``AGENTS.md`` marker is what makes a directory a CONSTRUCT installation
    as far as ``install_root_error`` is concerned, so it is written here even
    though this plan's capabilities do not consult it — a fixture that is only
    *just* enough for today's assertions is the one that breaks the next plan.
    """
    root = tmp_path / "install"
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# CONSTRUCT test install root\n", encoding="utf-8")
    for name in WORKSPACE_IDS:
        build_workspace(root, name)
    return root


@pytest.fixture
def api_token() -> str:
    return API_TOKEN


@pytest.fixture
def client(install_root: Path) -> Iterator[TestClient]:
    """A ``TestClient`` over a freshly built app for this install root.

    The launch install root is process-level state (D-09), so it is cleared on
    teardown — otherwise one test's ``tmp_path`` would still be the resolution
    root for the next test, and a workspace-id assertion could pass against a
    tree the test never built.

    ``base_url`` carries a loopback ``Host``, which is what makes the default
    request a *passing* one; the Host-rejection case overrides it explicitly.
    """
    from construct.api.app import create_app

    app = create_app(install_root, API_TOKEN)
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client
    set_launch_install_root(None)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {TOKEN_HEADER: API_TOKEN}
