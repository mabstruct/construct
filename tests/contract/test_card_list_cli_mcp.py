"""Contract tests for knowledge.card.list CLI + MCP parity (Phase 16, D-01).

The graph had an enumerate command for edges (``knowledge connection list``) but
none for nodes. FIX-03 closes that asymmetry through the capability registry, so
both surfaces come from one record and ``mcp/server.py`` is never touched.

Wave 2 status: RED until Task 2 registers ``knowledge.card.list`` and adds the
``card list`` Typer leaf. ``test_mcp_no_hardcoded_card_list`` is the GREEN
guardrail proving Task 2 must NOT hand-wire the MCP server — the views-group
exception is not a precedent for a second bypass.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.mcp import server as mcp_server
from construct.mcp.server import _serialize_result, create_server

runner = CliRunner()

_CAPS = {"knowledge.card.list": "construct_list_cards"}


def _card_workspace(tmp_path: Path) -> Path:
    """A scaffolded workspace holding two cards."""
    from construct.services.init import DomainInitInput, initialize_workspace
    from construct.services.knowledge import create_card

    ws = tmp_path / "workspace"
    initialize_workspace(
        ws,
        DomainInitInput(
            domain_id="test-domain",
            display_name="Test Domain",
            scope="A test domain for contract tests.",
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


# ── Registry presence + binding discipline ────────────────────────────────


def test_registered() -> None:
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        cap = reg.get(cap_id)
        assert cap.input_model is not None
        assert cap.mcp_tool_name == mcp_name
        assert cap.cli_name == cap_id


def test_handler_accepts_workspace_keyword(tmp_path: Path) -> None:
    """MCP calls the handler with ``workspace=`` derived from CardListInput's
    field names while the CLI calls it positionally. Both must bind the same
    parameter with no shim — a mismatch here is the RT-03 defect class."""
    ws = _card_workspace(tmp_path)
    cap = get_registry().get("knowledge.card.list")
    result = cap.handler(workspace=ws)
    assert result.success, result.message


def test_input_model_forbids_extra_fields() -> None:
    """ASVS V5 (T-16-09): unexpected MCP payload fields are rejected at the
    boundary. Explicitly set on CardListInput — it is not inherited."""
    import pytest
    from pydantic import ValidationError

    from construct.capabilities.catalog import CardListInput

    with pytest.raises(ValidationError):
        CardListInput(workspace=".", bogus=1)


# ── MCP auto-discovery parity (NO edit to mcp/server.py) ───────────────────


def test_in_mcp_tool_list() -> None:
    names = {entry["name"] for entry in get_registry().list_mcp_tools()}
    assert set(_CAPS.values()) <= names


def test_mcp_server_exposes_card_list() -> None:
    create_server()  # builds the FastMCP app from the registry without error
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        assert reg.get_by_mcp_name(mcp_name).id == cap_id


def test_mcp_no_hardcoded_card_list() -> None:
    """Parity is free: the server auto-discovers records, so it must contain no
    card-list-specific wiring. This GREEN guard is the mechanical proof that
    D-01 is registry-routed."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "construct_list_cards" not in src
    assert "knowledge.card.list" not in src
    assert "list_cards" not in src


# ── CLI command presence ──────────────────────────────────────────────────


def test_cli_commands_present() -> None:
    result = runner.invoke(app, ["knowledge", "card", "list", "--help"])
    assert result.exit_code == 0, result.stdout


def test_cli_exposes_documented_flags() -> None:
    result = runner.invoke(app, ["knowledge", "card", "list", "--help"])
    assert result.exit_code == 0, result.stdout
    for flag in ("--domain", "--include-archived", "--workspace", "--json"):
        assert flag in result.stdout, flag


# ── CLI/MCP result-schema parity ──────────────────────────────────────────


def test_cli_mcp_schema_parity(tmp_path: Path) -> None:
    """CLI ``--json`` keys == MCP-serialized handler keys. Doubles as the
    date-serialization regression: ``json.loads`` fails loudly if date objects
    leak out of the handler."""
    ws = _card_workspace(tmp_path)

    cap = get_registry().get("knowledge.card.list")
    mcp_serialized = _serialize_result(cap.handler(workspace=ws))

    cli = runner.invoke(
        app, ["knowledge", "card", "list", "--workspace", str(ws), "--json"]
    )
    assert cli.exit_code == 0, cli.stdout
    cli_payload = json.loads(cli.stdout)

    assert set(cli_payload.keys()) == set(mcp_serialized.keys())
    assert cli_payload["data"]
    assert len(cli_payload["data"]) == len(mcp_serialized["data"])
    for cli_card, mcp_card in zip(cli_payload["data"], mcp_serialized["data"]):
        assert set(cli_card.keys()) == set(mcp_card.keys())
        assert "body" not in cli_card
