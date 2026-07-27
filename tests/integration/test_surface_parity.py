"""Differential CLI-process vs MCP-dispatch parity harness (GOV-01, D-08).

Two surfaces reached the same capability handlers by two different, independently
written paths, and nothing asserted they agreed. ``input_model`` was computed into
a JSON Schema for MCP discovery and then thrown away, so ``CardListInput``'s
``extra="forbid()"`` never ran against a real payload (WR-02). GOV-01 closes that
by routing both surfaces through one validating seam, ``CapabilityRegistry.invoke``.

This harness is the proof. It drives the two surfaces *as they actually run* and
asserts they agree — rather than testing the seam once and assuming both callers
reach it.

Wave 1 status: the case table is seeded with a single row. Plan 03 converts the
remaining call sites and adds rows; the table is the extension point, so growing
coverage never means growing this file's logic.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from construct.capabilities.catalog import get_registry
from construct.mcp import server as mcp_server
from construct.mcp.server import create_server

REPO_ROOT = Path(__file__).resolve().parents[2]

# (capability_id, mcp_tool_name, payload builder, CLI argv builder)
PARITY_CASES: list[tuple[str, str, Callable[[Path], dict], Callable[[Path], list[str]]]] = [
    (
        "knowledge.card.list",
        "construct_list_cards",
        lambda ws: {"workspace": str(ws)},
        lambda ws: ["knowledge", "card", "list", "--workspace", str(ws), "--json"],
    ),
]

_CASE_IDS = [case[0] for case in PARITY_CASES]


# ── Surface drivers ───────────────────────────────────────────────────────


def _cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the real ``construct`` CLI in a real child process.

    ``typer.testing.CliRunner`` would share this pytest process, and with it the
    registry singleton cached in a module global (``catalog.py`` ``get_registry``).
    A shared registry cannot prove that an independently started process reaches
    the same verdict, which is the entire claim of a differential harness
    (RESEARCH Pitfall 5). It also cannot produce a real exit code.

    ``sys.executable`` is the interpreter running this suite, and ``PYTHONPATH``
    pins the child to *this* checkout's ``src``. A hardcoded ``.venv/bin/python``
    would import whatever tree that environment's editable install points at —
    inside a git worktree that is a different checkout, so the child would happily
    test code this test never touched.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "construct.cli", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )


def _mcp(tool_name: str, payload: dict) -> dict:
    """Invoke the closure ``create_server()`` actually registered with FastMCP.

    Calling ``cap.handler`` directly would skip the very wiring under test — the
    handler is reached through ``make_handler``'s closure, and that closure is
    where dispatch goes through the seam.
    """
    tool = create_server()._tool_manager.get_tool(tool_name)
    return json.loads(tool.fn(**payload))


def _card_workspace(tmp_path: Path) -> Path:
    """A scaffolded workspace holding two cards, built through the real services."""
    from construct.services.init import DomainInitInput, initialize_workspace
    from construct.services.knowledge import create_card

    ws = tmp_path / "workspace"
    initialize_workspace(
        ws,
        DomainInitInput(
            domain_id="test-domain",
            display_name="Test Domain",
            scope="A test domain for surface-parity tests.",
            taxonomy_seeds=["test-category"],
            source_priorities=["peer-reviewed papers"],
            research_seeds=["test research"],
        ),
    )
    for card_id, title in (("card-a", "Card A"), ("card-b", "Card B")):
        create_card(
            ws,
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
    return ws


# ── The seam exists and carries the cross-phase signature ─────────────────


def test_seam_exists_with_the_cross_phase_signature() -> None:
    """Phase 19's generated HTTP adapter routes through this exact signature, so
    its shape is a cross-phase contract, not an implementation detail."""
    import inspect

    from construct.capabilities.registry import CapabilityRegistry

    signature = inspect.signature(CapabilityRegistry.invoke)
    assert list(signature.parameters) == ["self", "cap_id", "payload"]
    assert signature.return_annotation is not inspect.Signature.empty


def test_seam_has_no_leniency_knob() -> None:
    """D-05: a strict/lenient flag would let one surface diverge from another —
    the precise fork this seam exists to close. Its absence is load-bearing."""
    import inspect

    from construct.capabilities.registry import CapabilityRegistry

    parameters = set(inspect.signature(CapabilityRegistry.invoke).parameters)
    assert parameters == {"self", "cap_id", "payload"}


# ── Success parity across the two real surfaces ───────────────────────────


@pytest.mark.parametrize(
    ("cap_id", "tool_name", "build_payload", "build_argv"), PARITY_CASES, ids=_CASE_IDS
)
def test_success_parity_verdict_message_and_records(
    tmp_path: Path,
    cap_id: str,
    tool_name: str,
    build_payload: Callable[[Path], dict],
    build_argv: Callable[[Path], list[str]],
) -> None:
    """One payload, two real surfaces, one answer: same verdict, same message,
    same record key set."""
    ws = _card_workspace(tmp_path)

    cli = _cli(build_argv(ws))
    assert cli.returncode == 0, cli.stderr or cli.stdout
    cli_payload = json.loads(cli.stdout)

    mcp_payload = _mcp(tool_name, build_payload(ws))

    assert cli_payload["success"] == mcp_payload["success"] is True
    assert cli_payload["message"] == mcp_payload["message"]

    assert cli_payload["data"], "fixture produced no records to compare"
    assert len(cli_payload["data"]) == len(mcp_payload["data"])
    for cli_record, mcp_record in zip(cli_payload["data"], mcp_payload["data"]):
        assert set(cli_record.keys()) == set(mcp_record.keys())


# ── The MCP surface stays registry-generated ──────────────────────────────


def test_mcp_server_names_no_capability() -> None:
    """Inserting the seam must not have bought parity with hand-wiring.

    ``mcp/server.py`` is 52 lines of registry-driven generation, and that is the
    structure Phase 19's HTTP adapter is generated from. If any capability id or
    tool name appears in its source, the generation claim is already false.
    """
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    registry = get_registry()
    for cap in registry.list():
        assert cap.id not in src, f"capability id leaked into mcp/server.py: {cap.id}"
        if cap.mcp_tool_name:
            assert cap.mcp_tool_name not in src, (
                f"tool name leaked into mcp/server.py: {cap.mcp_tool_name}"
            )


def test_mcp_dispatch_routes_through_the_seam() -> None:
    """The key link this plan asserts: MCP reaches handlers via ``invoke``, not
    via ``capability.handler``."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "invoke(" in src
    assert "capability.handler(" not in src
