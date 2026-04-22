"""CLI shell for CONSTRUCT."""

from __future__ import annotations

from pathlib import Path
import re

import typer

from construct.services.init import DomainInitInput, WorkspaceInitError, initialize_workspace
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


def main() -> None:
    """Run the CONSTRUCT CLI application."""
    app()


if __name__ == "__main__":
    main()
