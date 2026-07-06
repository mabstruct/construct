"""Contract tests for daily.run / daily.inspect CLI + MCP parity (Phase 13).

Proves the thin ``daily.run`` composition (research.run → curation.run →
graph.status) is invokable through the shared registry from both the Typer CLI
and the auto-discovered stdio MCP server, with NO edit to ``mcp/server.py``
(parity is free). Mirrors the curation.run contract test; daily.run degrades
each child offline so the parity test runs with no ANTHROPIC_API_KEY.

Wave 2 status: RED until Task 2 registers ``daily.run`` / ``daily.inspect`` and
Task 3 adds the ``daily`` Typer sub-app. ``test_mcp_no_hardcoded_daily`` is the
GREEN guardrail proving those tasks must NOT edit ``mcp/server.py``. The in-module
result model is imported lazily so this file still collects before registration.
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
    "daily.run": "construct_daily_run",
    "daily.inspect": "construct_daily_inspect",
}


def _run_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    return ws


# ── Registry presence + keyword-only shim discipline ──────────────────────


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


def test_mcp_server_exposes_daily() -> None:
    create_server()  # builds the FastMCP app from the registry without error
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        assert reg.get_by_mcp_name(mcp_name).id == cap_id


def test_mcp_no_hardcoded_daily() -> None:
    """Parity is free: the server auto-discovers records, so it must contain no
    daily-specific wiring. This GREEN guard proves Tasks 2-3 never edit
    mcp/server.py."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "construct_daily_run" not in src
    assert "daily.run" not in src


# ── CLI command presence ──────────────────────────────────────────────────


def test_cli_commands_present() -> None:
    for sub in ("run", "inspect"):
        result = runner.invoke(app, ["daily", sub, "--help"])
        assert result.exit_code == 0, result.stdout


# ── CLI/MCP result-schema parity + offline smoke ──────────────────────────


def test_cli_mcp_schema_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI ``--json`` keys == MCP-serialized handler keys == DailyRunResult
    fields. Runs fully offline: no ANTHROPIC_API_KEY, so each composed child
    isolates-and-degrades (D-06) and the cycle still folds a DailyRunResult."""
    from construct.llm.daily_run import DailyRunResult

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ws = _run_workspace(tmp_path)

    # Direct handler → MCP serialization path (same handler the MCP tool wraps).
    cap = get_registry().get("daily.run")
    handler_result = cap.handler(workspace_path=str(ws))
    mcp_serialized = _serialize_result(handler_result)

    # CLI path.
    cli = runner.invoke(app, ["daily", "run", "--workspace", str(ws), "--json"])
    assert cli.exit_code == 0, cli.stdout
    cli_payload = json.loads(cli.stdout)

    # Same OperationResult envelope across CLI and MCP.
    assert set(cli_payload.keys()) == set(mcp_serialized.keys())
    # Same DailyRunResult data shape, matching the in-module model fields.
    assert set(cli_payload["data"].keys()) == set(mcp_serialized["data"].keys())
    assert set(cli_payload["data"].keys()) == set(DailyRunResult.model_fields.keys())
    assert "ANTHROPIC_API_KEY" not in os.environ
