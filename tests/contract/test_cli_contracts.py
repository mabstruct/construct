"""Contract tests for CLI commands against real test-ws/ fixtures."""
from __future__ import annotations

import pathlib

from typer.testing import CliRunner

from construct.cli import app

runner = CliRunner()


def _ws(name: str) -> pathlib.Path:
    return pathlib.Path(__file__).parents[2] / "test-ws" / name


def test_validate_passes_on_my_construct() -> None:
    ws = _ws("my-construct")
    result = runner.invoke(app, ["validate", str(ws)])
    assert result.exit_code == 0
    assert "0 error" in result.output


def test_validate_passes_on_ping_eon() -> None:
    ws = _ws("ping-eon")
    result = runner.invoke(app, ["validate", str(ws)])
    assert result.exit_code == 0
    assert "0 error" in result.output


def test_status_runs_on_my_construct() -> None:
    ws = _ws("my-construct")
    result = runner.invoke(app, ["status", str(ws)])
    assert result.exit_code == 0
    assert "Canonical" in result.output


def test_knowledge_connection_list_on_ping_eon() -> None:
    ws = _ws("ping-eon")
    result = runner.invoke(app, ["knowledge", "connection", "list", "--workspace", str(ws)])
    assert result.exit_code == 0
