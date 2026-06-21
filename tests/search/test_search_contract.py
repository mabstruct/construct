"""Integration tests for research.search capability contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.pipelines.research_search import ResearchSearchInput, research_search

runner = CliRunner()


def _snapshot_sot_paths(workspace: Path) -> dict[str, str]:
    paths: list[Path] = [
        workspace / "search-seeds.json",
        workspace / "log" / "events.jsonl",
    ]
    paths.extend(sorted((workspace / "refs").glob("*.json")))
    paths.extend(sorted((workspace / "cards").glob("*.md")))

    snapshots: dict[str, str] = {}
    for path in paths:
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshots[path.relative_to(workspace).as_posix()] = digest
    return snapshots


def test_research_search_normalized(search_workspace: Path) -> None:
    before = _snapshot_sot_paths(search_workspace)

    result = research_search(
        ResearchSearchInput(
            workspace_path=str(search_workspace),
            query="quantum gravity",
        )
    )

    after = _snapshot_sot_paths(search_workspace)

    assert result.success is True
    assert result.data is not None
    assert "batches" in result.data
    assert result.data["provider"] == "mock"
    assert result.data["degraded"] is False
    assert len(result.data["batches"]) == 1
    batch = result.data["batches"][0]
    assert batch["query"] == "quantum gravity"
    assert len(batch["results"]) >= 1
    first = batch["results"][0]
    assert {"title", "url", "snippet", "source_tier", "score"} <= set(first.keys())
    assert before == after


def test_research_search_rate_limit_error(search_workspace: Path) -> None:
    result = research_search(
        ResearchSearchInput(
            workspace_path=str(search_workspace),
            query="__error_rate_limit__",
        )
    )

    assert result.success is False
    assert result.errors
    assert result.errors[0].reason == "RateLimitError"
    assert result.data is not None
    assert result.data.get("retry_after_seconds") == 30


def test_research_search_manual_ingest_warning(search_workspace: Path) -> None:
    seeds_path = search_workspace / "search-seeds.json"
    payload = json.loads(seeds_path.read_text(encoding="utf-8"))
    for cluster in payload["clusters"]:
        if cluster["id"] == "manual-ingest":
            cluster["terms"] = ["quantum gravity"]
            cluster["domain"] = "test-domain"
    seeds_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = research_search(
        ResearchSearchInput(
            workspace_path=str(search_workspace),
            cluster_id="manual-ingest",
        )
    )

    assert result.success is True
    assert result.data is not None
    assert any(
        "reserved for ingest" in warning
        for warning in result.data.get("warnings", [])
    )


def test_research_search_mcp_tool_registered() -> None:
    tool_names = {entry["name"] for entry in get_registry().list_mcp_tools()}
    assert "construct_research_search" in tool_names


def test_research_search_cli_json(search_workspace: Path) -> None:
    result = runner.invoke(
        app,
        [
            "research",
            "search",
            "-w",
            str(search_workspace),
            "-q",
            "quantum gravity",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["data"]["batches"]
