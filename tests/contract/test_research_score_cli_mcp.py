"""Contract tests for research.score CLI + MCP parity (Phase 9 Plan 04)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.llm.research_score import ScoredFinding
from tests.llm.conftest import (
    ConfigurableStructuredMock,
    TotalOutageMock,
    create_test_workspace,
    make_build_chat_model,
    write_card,
)

runner = CliRunner()


def _raw_finding() -> ScoredFinding:
    return ScoredFinding(
        url="https://arxiv.org/abs/2401.00001",
        title="Loop Quantum Gravity",
        relevance_score=0.9,
        source_tier=2,
        ingest_action="ref_and_card",
        key_findings=["a"],
        content_categories=["loop-quantum-gravity"],
        reasoning="High relevance peer-reviewed source.",
    )


def _results_payload() -> list[dict]:
    return [
        {
            "title": "Loop Quantum Gravity and the Big Bounce",
            "url": "https://arxiv.org/abs/2401.00001",
            "snippet": "Peer-reviewed LQG cosmology.",
            "source_tier": 2,
            "score": 0.91,
            "provider_specific": {},
            "source_domain": "arxiv.org",
        }
    ]


def test_construct_research_score_in_mcp_tool_list() -> None:
    tool_names = {entry["name"] for entry in get_registry().list_mcp_tools()}
    assert "construct_research_score" in tool_names


def _score_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    write_card(ws, "card-1", title="Test Card One", body="Content about testing.")
    return ws


def test_cli_score_renders_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_workspace = _score_workspace(tmp_path)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(ConfigurableStructuredMock(_raw_finding())),
    )
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(_results_payload()), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "research",
            "score",
            "--workspace",
            str(test_workspace),
            "--results-file",
            str(results_path),
        ],
    )

    assert result.exit_code == 0
    assert "url\tscore\ttier\taction" in result.stdout
    assert "arxiv.org" in result.stdout
    assert "degraded:" in result.stdout


def test_cli_json_matches_registry_handler_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_workspace = _score_workspace(tmp_path)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(ConfigurableStructuredMock(_raw_finding())),
    )
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(_results_payload()), encoding="utf-8")
    handler_kwargs = {
        "workspace_path": str(test_workspace),
        "results": _results_payload(),
    }

    cap = get_registry().get("research.score")
    handler_result = cap.handler(**handler_kwargs)

    cli_result = runner.invoke(
        app,
        [
            "research",
            "score",
            "--workspace",
            str(test_workspace),
            "--results-file",
            str(results_path),
            "--json",
        ],
    )
    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["data"] == handler_result.data


def test_cli_total_outage_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_workspace = _score_workspace(tmp_path)
    monkeypatch.setattr(
        "construct.llm.factory.build_chat_model",
        make_build_chat_model(TotalOutageMock()),
    )
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(_results_payload()), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "research",
            "score",
            "--workspace",
            str(test_workspace),
            "--results-file",
            str(results_path),
        ],
    )
    assert result.exit_code != 0
