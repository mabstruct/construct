"""CLI shell for CONSTRUCT."""

from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Optional

import typer

from construct.schemas.card import CardAuthor, Lifecycle
from construct.schemas.workspace import ConnectionAuthor, ConnectionType
from construct.services.init import DomainInitInput, WorkspaceInitError, initialize_workspace
from construct.services.knowledge import (
    OperationResult,
    add_connection,
    archive_card,
    create_card,
    edit_card,
    list_connections,
    remove_connection,
)
from construct.services.validation import validate_workspace
from construct.storage.workspace import WorkspaceLoader


app = typer.Typer(no_args_is_help=True)

KEBAB_CASE_SANITIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_kebab_case(value: str) -> str:
    normalized = KEBAB_CASE_SANITIZE_PATTERN.sub("-", value.strip().lower()).strip("-")
    return normalized


@app.command()
def init(path: Path) -> None:
    """Create a new CONSTRUCT workspace."""
    domain_id = _to_kebab_case(typer.prompt("Domain slug (spaces will be normalized to kebab-case)"))
    display_name = typer.prompt("Display name")
    scope = typer.prompt("Scope/description")
    taxonomy_seeds = [_to_kebab_case(item) for item in _parse_csv(typer.prompt("Taxonomy seeds (comma-separated; spaces will be normalized to kebab-case)"))]
    domain = DomainInitInput(
        domain_id=domain_id,
        display_name=display_name,
        scope=scope,
        taxonomy_seeds=[item for item in taxonomy_seeds if item],
        source_priorities=_parse_csv(typer.prompt("Source priorities (comma-separated)")),
        research_seeds=_parse_csv(typer.prompt("Research seeds (comma-separated)")),
    )
    try:
        workspace = initialize_workspace(path, domain)
    except WorkspaceInitError as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1)
    typer.echo(f"Initialized CONSTRUCT workspace at {workspace}")


@app.command()
def validate(path: Path) -> None:
    """Validate a CONSTRUCT workspace."""
    report = validate_workspace(path)
    for finding in report.errors:
        typer.echo(f"ERROR {finding.path}: {finding.message}")
    for finding in report.warnings:
        typer.echo(f"WARNING {finding.path}: {finding.message}")
    typer.echo(f"Validation complete: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    if report.errors:
        raise typer.Exit(code=1)


@app.command()
def status(path: Path) -> None:
    """Show workspace ownership categories."""
    loader = WorkspaceLoader(path)
    categories = {
        "canonical": "Canonical",
        "support": "Support",
        "derived": "Derived",
    }
    for item in loader.inspect_workspace():
        label = categories.get(item.category, "Unknown")
        state = "present" if item.exists else "missing"
        typer.echo(f"{label}: {item.relative_path} [{state}]")


# ---------------------------------------------------------------------------
# Knowledge command group
# ---------------------------------------------------------------------------

knowledge_app = typer.Typer(
    no_args_is_help=True,
    name="knowledge",
    help="Manage knowledge artifacts — cards, connections, and source files.",
)
app.add_typer(knowledge_app)

card_app = typer.Typer(no_args_is_help=True, name="card", help="Card CRUD operations.")
knowledge_app.add_typer(card_app)


def _display_result(result: OperationResult, json_output: bool) -> None:
    """Render an OperationResult to stdout as either JSON or human-readable text."""
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "success": result.success,
                    "message": result.message,
                    "errors": [
                        {"field": e.field, "reason": e.reason, "suggestion": e.suggestion}
                        for e in result.errors
                    ],
                    "data": result.data,
                },
                indent=2,
            )
        )
    else:
        if result.success:
            typer.echo(f"✓ {result.message}")
        else:
            typer.secho(f"✗ {result.message}", fg=typer.colors.RED)
            for error in result.errors:
                typer.echo(f"  • {error.field}: {error.reason}")
                if error.suggestion:
                    typer.echo(f"    Suggestion: {error.suggestion}")
    if not result.success:
        raise typer.Exit(code=1)


# -- Card commands -------------------------------------------------------


@card_app.command()
def create(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w", help="Workspace root directory"),
    title: str = typer.Option(..., "--title", "-t", help="Card title"),
    epistemic_type: str = typer.Option(..., "--type", "-y", help="Epistemic type (finding, claim, concept, …)"),
    domains: str = typer.Option(..., "--domains", "-d", help="Comma-separated domain IDs"),
    confidence: int = typer.Option(1, "--confidence", "-c", min=1, max=5, help="Confidence 1-5"),
    source_tier: int = typer.Option(5, "--source-tier", "-s", min=1, max=5, help="Source tier 1-5"),
    content_categories: str = typer.Option("", "--categories", help="Comma-separated content categories"),
    author: str = typer.Option("construct", "--author", "-a", help="Card author"),
    summary: str = typer.Option("", "--summary", "-m", help="Card summary (or pipe via stdin)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output JSON for machine consumption"),
) -> None:
    """Create a new knowledge card."""
    domain_list = [d.strip() for d in domains.split(",") if d.strip()]
    category_list = [c.strip() for c in content_categories.split(",") if c.strip()]

    card_data: dict[str, object] = {
        "title": title,
        "epistemic_type": epistemic_type,
        "domains": domain_list,
        "confidence": confidence,
        "source_tier": source_tier,
        "content_categories": category_list,
        "author": author,
    }
    if summary:
        card_data["_summary"] = summary

    result = create_card(workspace, card_data, author=CardAuthor(author))
    _display_result(result, json_output)


@card_app.command()
def edit(
    ctx: typer.Context,
    card_id: str = typer.Argument(..., help="Card ID to edit"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    confidence: Optional[int] = typer.Option(None, "--confidence", "-c", min=1, max=5),
    source_tier: Optional[int] = typer.Option(None, "--source-tier", "-s", min=1, max=5),
    lifecycle: Optional[str] = typer.Option(None, "--lifecycle", "-l", help="New lifecycle (seed/growing/mature/archived)"),
    summary: Optional[str] = typer.Option(None, "--summary", "-m", help="New summary"),
    author: str = typer.Option("curator", "--author", "-a"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Edit an existing knowledge card."""
    updates: dict[str, object] = {}
    if title is not None:
        updates["title"] = title
    if confidence is not None:
        updates["confidence"] = confidence
    if source_tier is not None:
        updates["source_tier"] = source_tier
    if lifecycle is not None:
        updates["lifecycle"] = lifecycle
    if summary is not None:
        updates["_summary"] = summary

    if not updates:
        typer.echo("No updates provided. Use --title, --confidence, etc. to specify changes.")
        raise typer.Exit(code=1)

    result = edit_card(workspace, card_id, updates, author=CardAuthor(author))
    _display_result(result, json_output)


@card_app.command()
def archive(
    ctx: typer.Context,
    card_id: str = typer.Argument(..., help="Card ID to archive"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    author: str = typer.Option("curator", "--author", "-a"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Archive a knowledge card. Preserves connections."""
    result = archive_card(workspace, card_id, author=CardAuthor(author))
    _display_result(result, json_output)


def main() -> None:
    """Run the CONSTRUCT CLI application."""
    app()


if __name__ == "__main__":
    main()
