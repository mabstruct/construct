"""Contract tests for curation.run / curation.inspect CLI + MCP parity (Phase 11).

Proves the deterministic curation workflow is invokable through the shared
registry from both the Typer CLI and the auto-discovered stdio MCP server, with
no edit to ``mcp/server.py`` (parity is free). Mirrors the research.run contract
test; curation is deterministic so there is no offline-LLM seam to patch.

Wave 0 status: RED until Plan 03 registers ``curation.run`` / ``curation.inspect``
and adds the ``curation`` Typer sub-app. ``test_mcp_no_hardcoded_curation`` is the
GREEN guardrail proving Plan 03 must NOT edit ``mcp/server.py``. The in-module
model is imported lazily so this file still collects before the module exists.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.mcp import server as mcp_server
from construct.mcp.server import _serialize_result, create_server
from tests.llm.conftest import create_test_workspace

runner = CliRunner()

_CAPS = {
    "curation.run": "construct_curation_run",
    "curation.inspect": "construct_curation_inspect",
    "curation.review": "construct_curation_review",  # NEW (Plan 04)
    "card.evaluate": "construct_card_evaluate",  # NEW (Plan 02)
}


def _run_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    return ws


# ── Registry presence + dual-mode shim discipline ─────────────────────────


def test_registered() -> None:
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        cap = reg.get(cap_id)
        assert cap.input_model is not None
        assert cap.mcp_tool_name == mcp_name
        assert cap.cli_name == cap_id


def test_shims_reject_positional_args() -> None:
    reg = get_registry()
    for cap_id in _CAPS:
        with pytest.raises(TypeError):
            reg.get(cap_id).handler("positional")


# ── MCP auto-discovery parity (NO edit to mcp/server.py) ───────────────────


def test_in_mcp_tool_list() -> None:
    names = {entry["name"] for entry in get_registry().list_mcp_tools()}
    assert set(_CAPS.values()) <= names


def test_mcp_server_exposes_curation() -> None:
    create_server()  # builds the FastMCP app from the registry without error
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        assert reg.get_by_mcp_name(mcp_name).id == cap_id


def test_mcp_no_hardcoded_curation() -> None:
    """Parity is free: the server auto-discovers records, so it must contain no
    curation-specific wiring. This GREEN guard proves Plan 03 never edits
    mcp/server.py."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "construct_curation_run" not in src
    assert "curation.run" not in src


# ── CLI command presence ──────────────────────────────────────────────────


def test_cli_commands_present() -> None:
    for sub in ("run", "inspect", "review"):
        result = runner.invoke(app, ["curation", sub, "--help"])
        assert result.exit_code == 0, result.stdout
    # card.evaluate is surfaced as its own `construct card evaluate` command.
    evaluate = runner.invoke(app, ["card", "evaluate", "--help"])
    assert evaluate.exit_code == 0, evaluate.stdout


# ── CUR-05: no placeholder curation path reachable from CLI or registry ─────


def test_no_placeholder_curation_path() -> None:
    """D-10 / CUR-05: the ``_get_workflow_steps`` placeholder shim is deleted from
    BOTH the catalog and the CLI (it lived in two files — Pitfall 6), so no
    ``curation-cycle`` placeholder handler is reachable from the registry or the
    CLI workflow group."""
    import construct.capabilities.catalog as catalog_mod
    import construct.cli as cli_mod

    catalog_src = Path(catalog_mod.__file__).read_text(encoding="utf-8")
    cli_src = Path(cli_mod.__file__).read_text(encoding="utf-8")

    assert "_get_workflow_steps" not in catalog_src, "placeholder shim must be gone from catalog.py"
    assert "_get_workflow_steps" not in cli_src, "placeholder shim must be gone from cli.py"


# ── CLI/MCP result-schema parity + offline smoke ──────────────────────────


def test_cli_mcp_schema_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI ``--json`` keys == MCP-serialized handler keys == CurationRunResult
    fields. Runs fully offline: no ANTHROPIC_API_KEY, so connection-health
    degrades to deterministic L1/L2 detection."""
    from construct.llm.curation_run import CurationRunResult

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ws = _run_workspace(tmp_path)

    # Direct handler → MCP serialization path (same handler the MCP tool wraps).
    cap = get_registry().get("curation.run")
    handler_result = cap.handler(workspace_path=str(ws))
    mcp_serialized = _serialize_result(handler_result)

    # CLI path.
    cli = runner.invoke(app, ["curation", "run", "--workspace", str(ws), "--json"])
    assert cli.exit_code == 0, cli.stdout
    cli_payload = json.loads(cli.stdout)

    # Same OperationResult envelope across CLI and MCP.
    assert set(cli_payload.keys()) == set(mcp_serialized.keys())
    # Same CurationRunResult data shape, matching the in-module model fields.
    assert set(cli_payload["data"].keys()) == set(mcp_serialized["data"].keys())
    assert set(cli_payload["data"].keys()) == set(CurationRunResult.model_fields.keys())
    assert "ANTHROPIC_API_KEY" not in os.environ
