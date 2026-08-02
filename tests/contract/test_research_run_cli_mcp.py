"""Contract tests for research.run / review / inspect CLI + MCP parity (Phase 10 Plan 05).

Proves the durable workflow is invokable through the shared registry from both the
Typer CLI and the auto-discovered stdio MCP server, with no edit to
``mcp/server.py`` (parity is free). Mirrors the score parity test, plus an offline
smoke that drives ``research.run`` to ``awaiting_review`` through the registry
handler via the existing mock-LLM seam.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.llm.research_run import RunResult
from construct.mcp import server as mcp_server
from construct.capabilities.results import serialize_result
from construct.mcp.server import create_server
from construct.search.models import SearchResult
from tests.llm.conftest import create_test_workspace, make_scored_findings_batch

runner = CliRunner()

_CAPS = {
    "research.run": "construct_research_run",
    "research.review": "construct_research_review",
    "research.inspect": "construct_research_inspect",
}


# ── Offline seam helpers ──────────────────────────────────────────────────


def _sample_search_results() -> list[SearchResult]:
    """Normalized SearchResult fixtures whose URLs line up with the scored batch."""
    return [
        SearchResult(
            title="Loop Quantum Gravity and the Big Bounce",
            url="https://arxiv.org/abs/2401.00001",
            snippet="A peer-reviewed treatment of the quantum bounce in LQG cosmology.",
            source_tier=2,
            score=0.91,
            provider_specific={"published_date": "2024-01-02"},
            source_domain="arxiv.org",
        ),
        SearchResult(
            title="A blog take on quantum gravity",
            url="https://example-blog.test/quantum-gravity",
            snippet="An informal opinion piece with limited sourcing.",
            source_tier=4,
            score=0.42,
            provider_specific={},
            source_domain="example-blog.test",
        ),
        SearchResult(
            title="Unrelated marketing page",
            url="https://shop.test/widgets",
            snippet="Buy widgets now, lowest prices guaranteed.",
            source_tier=5,
            score=0.12,
            provider_specific={},
            source_domain="shop.test",
        ),
    ]


def _patch_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the search + score seams so research.run runs fully offline."""
    from construct.llm import research_run, research_score

    monkeypatch.setattr(
        research_score, "run_gate", lambda *a, **k: make_scored_findings_batch()
    )
    monkeypatch.setattr(
        research_run,
        "_run_search",
        lambda *a, **k: [r.model_dump(mode="json") for r in _sample_search_results()],
    )


def _run_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    return ws


# ── Registry presence + dual-mode shim discipline ─────────────────────────


def test_run_review_inspect_registered() -> None:
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


def test_three_tools_in_mcp_tool_list() -> None:
    names = {entry["name"] for entry in get_registry().list_mcp_tools()}
    assert set(_CAPS.values()) <= names


def test_mcp_server_exposes_three_tools() -> None:
    create_server()  # builds the FastMCP app from the registry without error
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        assert reg.get_by_mcp_name(mcp_name).id == cap_id


def test_mcp_server_has_no_hardcoded_research_run() -> None:
    """Parity is free: the server auto-discovers records, so it must contain no
    research-run-specific wiring (proves mcp/server.py was not edited)."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "construct_research_run" not in src
    assert "research.run" not in src


# ── CLI command presence ──────────────────────────────────────────────────


def test_cli_commands_present() -> None:
    for sub in ("run", "review", "inspect"):
        result = runner.invoke(app, ["research", sub, "--help"])
        assert result.exit_code == 0, result.stdout


# ── CLI/MCP result-schema parity + offline smoke ──────────────────────────


def test_cli_run_offline_smoke_awaiting_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _run_workspace(tmp_path)
    _patch_offline(monkeypatch)

    cap = get_registry().get("research.run")
    result = cap.handler(workspace_path=str(ws))

    assert result.success
    assert result.data["status"] == "awaiting_review"
    assert result.data["run_id"]
    assert result.data["gate_id"]
    assert result.data["gate_queue"], "pending findings must be carried for review"


def test_cli_mcp_result_schema_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _run_workspace(tmp_path)
    _patch_offline(monkeypatch)

    # Direct handler → MCP serialization path (same handler the MCP tool wraps).
    cap = get_registry().get("research.run")
    handler_result = cap.handler(workspace_path=str(ws))
    mcp_serialized = serialize_result(handler_result)

    # CLI path.
    cli = runner.invoke(app, ["research", "run", "--workspace", str(ws), "--json"])
    assert cli.exit_code == 0, cli.stdout
    cli_payload = json.loads(cli.stdout)

    # Same OperationResult envelope across CLI and MCP.
    assert set(cli_payload.keys()) == set(mcp_serialized.keys())
    # Same RunResult data shape, and it matches the in-module RunResult model.
    assert set(cli_payload["data"].keys()) == set(mcp_serialized["data"].keys())
    assert set(cli_payload["data"].keys()) == set(RunResult.model_fields.keys())
    assert cli_payload["data"]["status"] == "awaiting_review"
