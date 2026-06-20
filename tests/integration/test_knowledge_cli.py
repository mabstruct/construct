"""Integration tests for knowledge CLI commands — card and connection operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from construct.cli import app
from construct.storage.workspace import WorkspaceLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def init_workspace(workspace_path: Path) -> Path:
    from construct.services.init import DomainInitInput, initialize_workspace

    domain = DomainInitInput(
        domain_id="test",
        display_name="Test",
        scope="Testing",
        taxonomy_seeds=["test-category"],
        source_priorities=["web"],
        research_seeds=["test"],
    )
    initialize_workspace(workspace_path, domain)
    return workspace_path


# ---------------------------------------------------------------------------
# Card CLI tests
# ---------------------------------------------------------------------------


def test_card_create_cli(init_workspace: Path, cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Test Card",
        "--type", "finding",
        "--domains", "test",
        "--categories", "test-category",
        "--confidence", "3",
        "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout
    assert "Test Card" in result.stdout


def test_card_create_cli_writes_summary_to_body(init_workspace: Path, cli_runner: CliRunner) -> None:
    summary = "Caching embeddings at the gateway reduces repeat-LLM-call latency."

    result = cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Semantic caching cuts gateway latency",
        "--type", "finding",
        "--domains", "test",
        "--confidence", "3",
        "--source-tier", "2",
        "--summary", summary,
        "--workspace", str(init_workspace),
    ])

    assert result.exit_code == 0, result.stdout
    content = (init_workspace / "cards" / "semantic-caching-cuts-gateway-latency.md").read_text(encoding="utf-8")
    assert "_summary" not in content
    assert f"## Summary\n\n{summary}" in content


def test_card_create_cli_invalid(init_workspace: Path, cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Bad Card",
        "--type", "finding",
        "--domains", "test",
        "--confidence", "99",
        "--workspace", str(init_workspace),
    ])
    # Typer/Click validates range constraints (min=1, max=5) before
    # reaching the service layer — returns exit code 2 for usage error
    assert result.exit_code != 0


def test_card_create_cli_json(init_workspace: Path, cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "JSON Card",
        "--type", "finding",
        "--domains", "test",
        "--confidence", "3",
        "--source-tier", "3",
        "--json",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert "id" in payload["data"]


def test_card_edit_cli(init_workspace: Path, cli_runner: CliRunner) -> None:
    # Create first
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Editable Card",
        "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    # Find the card file
    cards_dir = init_workspace / "cards"
    card_files = list(cards_dir.glob("*.md"))
    assert len(card_files) > 0
    card_id = card_files[0].stem
    # Edit
    result = cli_runner.invoke(app, [
        "knowledge", "card", "edit", card_id,
        "--title", "Edited Title",
        "--confidence", "4",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout
    # Verify
    content = card_files[0].read_text()
    assert "Edited Title" in content


def test_card_edit_cli_updates_summary_without_losing_body(init_workspace: Path, cli_runner: CliRunner) -> None:
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Editable Summary",
        "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--summary", "Original summary.",
        "--workspace", str(init_workspace),
    ])

    card_path = init_workspace / "cards" / "editable-summary.md"
    content = card_path.read_text(encoding="utf-8")
    card_path.write_text(
        content.replace("## Evidence\n\n", "## Evidence\n\nEvidence line.\n\n"),
        encoding="utf-8",
    )

    result = cli_runner.invoke(app, [
        "knowledge", "card", "edit", "editable-summary",
        "--summary", "Updated summary.",
        "--workspace", str(init_workspace),
    ])

    assert result.exit_code == 0, result.stdout
    content = card_path.read_text(encoding="utf-8")
    assert "_summary" not in content
    assert "Updated summary." in content
    assert "Evidence line." in content


def test_card_archive_cli(init_workspace: Path, cli_runner: CliRunner) -> None:
    # Create first
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Archivable Card",
        "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    card_id = list((init_workspace / "cards").glob("*.md"))[0].stem
    result = cli_runner.invoke(app, [
        "knowledge", "card", "archive", card_id,
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout
    content = (init_workspace / "cards" / f"{card_id}.md").read_text()
    assert "archived" in content or "lifecycle: archived" in content


# ---------------------------------------------------------------------------
# Connection CLI tests
# ---------------------------------------------------------------------------


def test_connection_add_cli(init_workspace: Path, cli_runner: CliRunner) -> None:
    # Create two cards first
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Card A", "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Card B", "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    cards = sorted((init_workspace / "cards").glob("*.md"))
    card_a, card_b = cards[0].stem, cards[1].stem

    result = cli_runner.invoke(app, [
        "knowledge", "connection", "add", card_a, card_b,
        "--type", "supports",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout


def test_connection_list_cli(init_workspace: Path, cli_runner: CliRunner) -> None:
    # Create two cards + connection
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Card A", "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Card B", "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    cards = sorted((init_workspace / "cards").glob("*.md"))
    cli_runner.invoke(app, [
        "knowledge", "connection", "add", cards[0].stem, cards[1].stem,
        "--type", "supports",
        "--workspace", str(init_workspace),
    ])

    result = cli_runner.invoke(app, [
        "knowledge", "connection", "list",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout


# ---------------------------------------------------------------------------
# Event log tests
# ---------------------------------------------------------------------------


def test_cli_logs_event(init_workspace: Path, cli_runner: CliRunner) -> None:
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Logged Card", "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--workspace", str(init_workspace),
    ])
    event_log = init_workspace / "log" / "events.jsonl"
    assert event_log.exists()
    lines = event_log.read_text().strip().splitlines()
    assert any("create_card" in line for line in lines)
