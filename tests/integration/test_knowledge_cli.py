"""Integration tests for knowledge CLI commands — card and connection operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.capabilities.errors import CapabilityInputError
from construct.cli import app
from construct.schemas.card import CardAuthor, Lifecycle, parse_card_markdown
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


def test_card_edit_title_only_leaves_every_unnamed_field_byte_identical(
    init_workspace: Path, cli_runner: CliRunner
) -> None:
    """T-18-15: a partial update must not blank a field the caller never named.

    ``card edit`` dispatches through ``registry.invoke``, and the seam calls
    ``handler(**model.model_dump())`` — ``model_dump()`` materialises a default for
    every declared field, so ``CardEditInput``'s ``summary``/``lifecycle``/
    ``confidence``/``source_tier`` all arrive at the handler even when the user
    named only ``--title``. If any of those materialised ``None``s reached
    ``edit_card``'s ``raw.update(updates)`` the stored value would be destroyed.

    So this test does not assert the new title is present (``test_card_edit_cli``
    already does). It reads the card back and asserts that everything the user did
    *not* name is byte-identical to what was on disk beforehand — the assertion
    that would have caught the ``archive_card`` prose destruction of 4e2b909, whose
    damage was unrecoverable.
    """
    body_prose = "Gateways that cache embeddings avoid the repeat-LLM-call tax."

    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Partial Update Subject",
        "--type", "finding", "--domains", "test",
        "--categories", "test-category",
        "--confidence", "3", "--source-tier", "2",
        "--summary", body_prose,
        "--author", "researcher",
        "--workspace", str(init_workspace),
    ])

    card_path = init_workspace / "cards" / "partial-update-subject.md"
    assert card_path.exists(), sorted(p.name for p in (init_workspace / "cards").glob("*.md"))

    # Promote off the default lifecycle so "unchanged" cannot be satisfied by a
    # field that happens to already hold the value a blanking bug would write.
    cli_runner.invoke(app, [
        "knowledge", "card", "edit", "partial-update-subject",
        "--lifecycle", "growing",
        "--workspace", str(init_workspace),
    ])

    fields_before, body_before = parse_card_markdown(
        card_path.read_text(encoding="utf-8"), source_path=card_path
    )
    fields_before = fields_before.model_dump()
    assert fields_before["lifecycle"] == Lifecycle.growing
    assert fields_before["author"] == CardAuthor.researcher
    assert body_prose in body_before

    result = cli_runner.invoke(app, [
        "knowledge", "card", "edit", "partial-update-subject",
        "--title", "Renamed But Otherwise Untouched",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 0, result.stdout

    fields_after, body_after = parse_card_markdown(
        card_path.read_text(encoding="utf-8"), source_path=card_path
    )
    fields_after = fields_after.model_dump()

    assert fields_after["title"] == "Renamed But Otherwise Untouched"

    # Compared field by field rather than as a whole-file diff, so a failure names
    # the field that was blanked instead of dumping two documents.
    for field in sorted(set(fields_before) - {"title"}):
        assert fields_after[field] == fields_before[field], (
            f"a title-only edit changed {field!r}: "
            f"{fields_before[field]!r} -> {fields_after[field]!r}"
        )

    # The prose lives in the markdown body, not the frontmatter, so it needs its own
    # read-back: this is the exact byte range the historical defect destroyed.
    assert body_after == body_before, "a title-only edit rewrote the card body"
    assert body_prose in body_after


@pytest.mark.parametrize("field", ["title", "summary", "lifecycle"])
def test_card_edit_refuses_a_blank_free_text_field_rather_than_blanking_it(
    init_workspace: Path, cli_runner: CliRunner, field: str
) -> None:
    """CR-03: an empty string is a no-op request, never a request to destroy prose.

    The two documented guards — the exclude-unset payload builder in ``cli.py``
    and ``_build_card_updates``' filter — both tested ``is not None`` only, and
    ``CardEditInput.title``/``summary`` were ``str | None`` with no length
    constraint. So ``""`` passed all three layers: ``{"summary": ""}`` deleted the
    card's Summary prose and ``{"title": ""}`` blanked the title, both reporting
    ``success: True``. ``construct_edit_card`` is an MCP tool, so this was
    agent-reachable, and it is the third instance of the class this repository
    names as data loss.

    The constraint is declared on the model, so the seam **rejects with a reason**
    rather than accepting a silent no-op — the same choice the rest of this phase
    makes. Both surfaces are asserted, because the model is the only layer both
    of them share.
    """
    body_prose = "Prose that an empty-string edit must never be able to delete."
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", f"Blank Guard {field}",
        "--type", "finding", "--domains", "test",
        "--categories", "test-category",
        "--confidence", "3", "--source-tier", "2",
        "--summary", body_prose,
        "--workspace", str(init_workspace),
    ])
    card_path = init_workspace / "cards" / f"blank-guard-{field}.md"
    before = card_path.read_bytes()

    # ── the CLI surface ──
    result = cli_runner.invoke(app, [
        "knowledge", "card", "edit", f"blank-guard-{field}",
        f"--{field}", "",
        "--workspace", str(init_workspace),
    ])
    assert result.exit_code == 1, result.stdout
    assert field in result.stdout
    assert card_path.read_bytes() == before, f"--{field} '' rewrote the card"

    # ── the seam an MCP client reaches ──
    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke("knowledge.card.edit", {
            "workspace": str(init_workspace),
            "card_id": f"blank-guard-{field}",
            field: "",
        })
    assert field in excinfo.value.reason
    assert card_path.read_bytes() == before, f"{{'{field}': ''}} rewrote the card"


@pytest.mark.parametrize("field", ["title", "summary", "lifecycle"])
def test_card_edit_refuses_a_whitespace_only_free_text_field(
    init_workspace: Path, cli_runner: CliRunner, field: str
) -> None:
    """A length constraint alone would let ``"   "`` through, which blanks just the same.

    ``min_length=1`` is satisfied by three spaces, and a title of three spaces is
    a destroyed title. The model therefore rejects on the *stripped* value, so the
    guard cannot be walked around with whitespace.
    """
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", f"Whitespace Guard {field}",
        "--type", "finding", "--domains", "test",
        "--categories", "test-category",
        "--confidence", "3", "--source-tier", "2",
        "--summary", "Prose the whitespace path must not reach.",
        "--workspace", str(init_workspace),
    ])
    card_path = init_workspace / "cards" / f"whitespace-guard-{field}.md"
    before = card_path.read_bytes()

    with pytest.raises(CapabilityInputError) as excinfo:
        get_registry().invoke("knowledge.card.edit", {
            "workspace": str(init_workspace),
            "card_id": f"whitespace-guard-{field}",
            field: "   ",
        })
    assert field in excinfo.value.reason
    assert card_path.read_bytes() == before


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
    summary = "Archiving must not destroy this summary prose."

    # Create first
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Archivable Card",
        "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--summary", summary,
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
    # The body must survive the archive, not be replaced by the empty template.
    assert f"## Summary\n\n{summary}" in content


def test_card_archive_cli_body_stable_across_repeated_archives(
    init_workspace: Path, cli_runner: CliRunner
) -> None:
    """Repeated archives must be a fixed point — no blank-line accretion."""
    cli_runner.invoke(app, [
        "knowledge", "card", "create",
        "--title", "Twice Archived",
        "--type", "finding", "--domains", "test",
        "--confidence", "3", "--source-tier", "3",
        "--summary", "Stable body prose.",
        "--workspace", str(init_workspace),
    ])
    card_path = init_workspace / "cards" / "twice-archived.md"

    def _archive() -> None:
        result = cli_runner.invoke(app, [
            "knowledge", "card", "archive", "twice-archived",
            "--workspace", str(init_workspace),
        ])
        assert result.exit_code == 0, result.stdout

    _archive()
    after_first = card_path.read_text(encoding="utf-8")
    _archive()
    after_second = card_path.read_text(encoding="utf-8")

    assert after_second == after_first
    assert "Stable body prose." in after_second


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
