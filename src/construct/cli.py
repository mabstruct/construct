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
from construct.services.knowledge import OperationResult
from construct.capabilities.catalog import get_registry
from construct.mcp.server import run_server
from construct.pipelines.workflow_runner import WorkflowRunner


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
    try:
        cap = get_registry().get("workspace.validate")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    report = cap.handler(path)
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
    try:
        cap = get_registry().get("workspace.status")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    items = cap.handler(path)
    categories = {
        "canonical": "Canonical",
        "support": "Support",
        "derived": "Derived",
    }
    for item in items:
        label = categories.get(item.category, "Unknown")
        state = "present" if item.exists else "missing"
        typer.echo(f"{label}: {item.relative_path} [{state}]")


@app.command()
def mcp() -> None:
    """Start the MCP stdio server for agentic tool invocation.

    Runs until stdin is closed. Tools are auto-registered from the
    capability registry — no manual wiring needed.
    """
    run_server()


@app.command(name="help")
def help_cmd(
    ctx: typer.Context,
    suggest: bool = typer.Option(False, "--suggest", help="Show workspace-aware next-step suggestions"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Show help information and workspace-aware suggestions."""
    if suggest:
        try:
            cap = get_registry().get("help.suggest")
        except KeyError:
            typer.echo("ERROR: Capability not found.")
            raise typer.Exit(code=1)
        result = cap.handler(workspace)
        _display_result(result, json_output)
    else:
        typer.echo("Run `construct help --suggest` for workspace-aware suggestions.")
        typer.echo("Use `construct --help` to see all commands.")


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


# ---------------------------------------------------------------------------
# Workflow command group
# ---------------------------------------------------------------------------

workflow_app = typer.Typer(
    no_args_is_help=True,
    name="workflow",
    help="Run and manage multi-step workflows.",
)
app.add_typer(workflow_app)


def _get_workflow_steps_from_registry(runner: WorkflowRunner) -> list:
    """Get workflow step definitions. For Phase 4, return curation-cycle steps."""
    from construct.capabilities.catalog import _get_workflow_steps
    # Try loading from state file
    s = runner.status()
    if s.success and s.data and s.data.get("state"):
        name = s.data["state"].get("workflow_name", "curation-cycle")
        return _get_workflow_steps(name)
    return _get_workflow_steps("curation-cycle")


@workflow_app.command()
def run(
    ctx: typer.Context,
    workflow_name: str = typer.Argument("curation-cycle", help="Workflow name to run"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    start_step: int = typer.Option(0, "--step", "-s", help="Start from this step index"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Run a multi-step workflow with state persistence and resume support."""
    try:
        cap = get_registry().get("workflow.run")
    except KeyError:
        typer.echo("ERROR: Capability not found.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, workflow_name=workflow_name, start_step=start_step)
    _display_result(result, json_output)


@workflow_app.command()
def status(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Check active workflow status."""
    try:
        cap = get_registry().get("workflow.status")
    except KeyError:
        typer.echo("ERROR: Capability not found.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace)
    _display_result(result, json_output)


@workflow_app.command()
def resume(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Resume a paused or failed workflow from the last saved state."""
    try:
        runner = WorkflowRunner(workspace)
        steps = _get_workflow_steps_from_registry(runner)
        result = runner.resume(steps)
    except Exception as exc:
        result = OperationResult(success=False, message=str(exc))
    _display_result(result, json_output)


# ---------------------------------------------------------------------------
# Ingest command group
# ---------------------------------------------------------------------------

ingest_app = typer.Typer(
    no_args_is_help=True,
    name="ingest",
    help="Ingest source material into the workspace.",
)
app.add_typer(ingest_app)


@ingest_app.command()
def source(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Source: file path, URL, note text, or 'research:query'"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    domain: str = typer.Option(None, "--domain", "-d", help="Target domain hint"),
    author: str = typer.Option("construct", "--author", "-a"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Ingest a source (file, URL, note, or web research) into the workspace."""
    try:
        cap = get_registry().get("ingest.source")
    except KeyError:
        typer.echo("ERROR: Capability not found.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, source=source, domain_hint=domain, author=author)
    _display_result(result, json_output)


# ---------------------------------------------------------------------------
# Ask command group (Phase 5)
# ---------------------------------------------------------------------------

ask_app = typer.Typer(
    no_args_is_help=True,
    name="ask",
    help="Ask questions grounded in workspace knowledge.",
)
app.add_typer(ask_app)


@ask_app.command()
def domain(
    ctx: typer.Context,
    question: str = typer.Option(..., "--question", "-q", help="Your question about this domain"),
    domain_id: str = typer.Option(..., "--domain", "-d", help="Domain ID to query"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    max_cards: int = typer.Option(20, "--max-cards", help="Max cards to consider (1-50)"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Ask a grounded question about a domain's knowledge cards.

    Uses the LangGraph L2 gate to retrieve relevant cards, synthesize
    an answer, and return structured citations with confidence scores.
    """
    try:
        cap = get_registry().get("ask.domain")
    except KeyError:
        typer.echo("ERROR: Capability 'ask.domain' not found. Ensure Phase 5 is complete.")
        raise typer.Exit(code=1)
    result = cap.handler(
        workspace_path=str(workspace),
        domain_id=domain_id,
        question=question,
        max_cards=max_cards,
    )
    _display_result(result, json_output)


# ---------------------------------------------------------------------------
# Bridge command group (Phase 5)
# ---------------------------------------------------------------------------

bridge_app = typer.Typer(
    no_args_is_help=True,
    name="bridge",
    help="Cross-domain bridge detection and management.",
)
app.add_typer(bridge_app)


@bridge_app.command()
def detect(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Detect cross-domain bridges via L1->L2->L3 pipeline.

    Runs deterministic (L1 structural edges, L2 category overlap) and
    optional LLM-assisted (L3 semantic) assessment for promising candidates.
    Results are written to log/bridge-candidates.json.
    """
    try:
        cap = get_registry().get("bridge.detect")
    except KeyError:
        typer.echo("ERROR: Capability 'bridge.detect' not found. Ensure Phase 5 is complete.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace_path=str(workspace))
    _display_result(result, json_output)


# ---------------------------------------------------------------------------
# Views command group (Phase 6)
# ---------------------------------------------------------------------------

views_app = typer.Typer(
    no_args_is_help=True,
    name="views",
    help="Validate and manage views data contracts.",
)
app.add_typer(views_app)


@views_app.command()
def validate(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Validate views data files against their Pydantic schemas.

    Reads views/build/data/*.json and validates each file against its
    declared contract model. Reports per-file pass/fail.
    """
    from construct.views.models import (
        ArticlesFile,
        BridgesFile,
        CardsFile,
        ConnectionsFile,
        DigestsFile,
        DomainsFile,
        EventsFile,
        StatsFile,
        schema_for,
        validate_data,
    )

    build_data_dir = workspace / "views" / "build" / "data"
    if not build_data_dir.is_dir():
        typer.echo(f"ERROR: No views data directory at {build_data_dir}")
        raise typer.Exit(code=1)

    # Map relative paths to their contract models
    model_map: dict[str, type] = {
        "bridges.json": BridgesFile,
        "domains.json": DomainsFile,
        "articles.json": ArticlesFile,
        "stats.json": StatsFile,
    }

    results: list[dict] = []
    all_passed = True

    # Global files
    for filename, model_class in model_map.items():
        file_path = build_data_dir / filename
        if not file_path.exists():
            results.append({"file": filename, "status": "missing", "errors": []})
            all_passed = False
            continue
        try:
            import json
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            data = raw if isinstance(raw, dict) else {}
            # Unwrap from envelope if needed
            payload = data.get("data", data)
            validate_data(model_class, payload)
            results.append({"file": filename, "status": "pass", "errors": []})
        except Exception as exc:
            results.append({"file": filename, "status": "fail", "errors": [str(exc)]})
            all_passed = False

    # Per-workspace files (walk workspace subdirs)
    for ws_dir in sorted(build_data_dir.iterdir()):
        if not ws_dir.is_dir():
            continue
        ws_files: list[tuple[str, type]] = [
            ("cards.json", CardsFile),
            ("connections.json", ConnectionsFile),
            ("digests.json", DigestsFile),
            ("events.json", EventsFile),
        ]
        for fname, mclass in ws_files:
            fpath = ws_dir / fname
            if not fpath.exists():
                continue
            try:
                import json
                raw = json.loads(fpath.read_text(encoding="utf-8"))
                data = raw if isinstance(raw, dict) else {}
                payload = data.get("data", data)
                validate_data(mclass, payload)
                rel = f"{ws_dir.name}/{fname}"
                results.append({"file": rel, "status": "pass", "errors": []})
            except Exception as exc:
                rel = f"{ws_dir.name}/{fname}"
                results.append({"file": rel, "status": "fail", "errors": [str(exc)]})
                all_passed = False

    if json_output:
        typer.echo(json.dumps({"results": results, "all_passed": all_passed}, indent=2))
    else:
        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        missing = sum(1 for r in results if r["status"] == "missing")
        typer.echo(f"Views data validation: {passed} passed, {failed} failed, {missing} missing")
        for r in results:
            if r["status"] == "pass":
                typer.echo(f"  ✓ {r['file']}")
            elif r["status"] == "fail":
                typer.secho(f"  ✗ {r['file']}", fg=typer.colors.RED)
                for err in r.get("errors", []):
                    typer.echo(f"    {err}")
            else:
                typer.echo(f"  ? {r['file']} (missing)")

    if not all_passed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Spike command group (Phase 6)
# ---------------------------------------------------------------------------

spike_app = typer.Typer(
    no_args_is_help=True,
    name="spike",
    help="Run external graph-analysis tools on isolated workspace copies.",
)
app.add_typer(spike_app)


@spike_app.command()
def list(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """List available spike types."""
    from construct.pipelines.spike_runner import list_spikes
    spikes = list_spikes()
    if json_output:
        typer.echo(json.dumps(spikes, indent=2))
    else:
        if not spikes:
            typer.echo("No spike types registered.")
            return
        typer.echo("Available spike types:")
        for s in spikes:
            typer.echo(f"  {s['name']}: {s['description']}")


@spike_app.command()
def run(
    ctx: typer.Context,
    tool_name: str = typer.Argument(..., help="Spike tool name (graphify, infranodus, etc.)"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w", help="Workspace to copy and run against"),
    tool_path: Optional[str] = typer.Option(None, "--tool-path", help="Path to external tool binary"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Run an external spike tool on an isolated workspace copy.

    Creates a temp copy of the workspace, runs the tool in isolation,
    captures output to log/spike-results/, then cleans up.
    """
    from construct.pipelines.spike_runner import run_spike, SpikeResult

    result = run_spike(
        tool_name=tool_name,
        workspace=workspace,
        tool_path=tool_path,
    )
    if json_output:
        typer.echo(
            json.dumps({
                "success": result.success,
                "tool_name": result.tool_name,
                "duration_seconds": result.duration_seconds,
                "error": result.error,
                "outputs": result.outputs,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }, indent=2, default=str)
        )
    else:
        if result.success:
            typer.secho(
                f"✓ Spike '{result.tool_name}' completed in {result.duration_seconds}s",
                fg=typer.colors.GREEN,
            )
        else:
            typer.secho(
                f"✗ Spike '{result.tool_name}' failed: {result.error}",
                fg=typer.colors.RED,
            )
        if result.outputs:
            typer.echo(f"  Captured outputs: {', '.join(result.outputs)}")
        if result.stdout:
            lines = result.stdout.splitlines()
            show = lines[:20]
            typer.echo("  stdout:")
            for line in show:
                typer.echo(f"    {line}")
            if len(lines) > 20:
                typer.echo("  (stdout truncated)")
        if result.stderr:
            lines = result.stderr.splitlines()
            show = lines[:10]
            typer.echo("  stderr:")
            for line in show:
                typer.echo(f"    {line}")
            if len(lines) > 10:
                typer.echo("  (stderr truncated)")


# ---------------------------------------------------------------------------
# Tag command group (Phase 6)
# ---------------------------------------------------------------------------

tag_app = typer.Typer(
    no_args_is_help=True,
    name="tag",
    help="Extract and manage candidate tags from source material.",
)
app.add_typer(tag_app)


@tag_app.command()
def extract(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Extract candidate tags/keywords from refs source material.

    Reads refs/*.json from the workspace, uses hybrid extraction
    to identify candidate tags, and writes results to log/tag-candidates.json.
    Candidates are NEVER auto-accepted per D-08.
    """
    from construct.pipelines.tag_extraction import extract_candidates

    result = extract_candidates(workspace)
    if json_output:
        typer.echo(
            json.dumps({
                "success": result.success,
                "total_candidates": result.total_candidates,
                "new_candidates": result.new_candidates,
                "existing_seeds_skipped": result.existing_seeds_skipped,
                "error": result.error,
                "candidates": [
                    {"id": c.id, "tag": c.tag, "domain_id": c.domain_id,
                     "confidence": c.confidence, "status": c.status}
                    for c in result.candidates
                ],
            }, indent=2, default=str)
        )
    else:
        if not result.success:
            typer.secho(f"✗ {result.error}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho(
            f"✓ Extracted {result.total_candidates} candidates "
            f"({result.new_candidates} new, {result.existing_seeds_skipped} skipped)",
            fg=typer.colors.GREEN,
        )
        if result.candidates:
            typer.echo("  Candidates:")
            for c in result.candidates[:20]:
                typer.echo(
                    f"  [{c.id}] {c.tag} "
                    f"(domain: {c.domain_id or '?'}, confidence: {c.confidence:.2f}, "
                    f"status: {c.status})"
                )
            if len(result.candidates) > 20:
                typer.echo(f"  ... and {len(result.candidates) - 20} more")
        typer.echo(f"Results written to {workspace}/log/tag-candidates.json")


@tag_app.command()
def approve(
    ctx: typer.Context,
    candidate_ids: str = typer.Argument(..., help="Comma-separated tag candidate IDs to approve"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Approve tag candidates and write to search-seeds.json.

    Only approved candidates update search-seeds.json --
    never auto-accepted per D-08.
    """
    from construct.services.knowledge import approve_tag_candidates

    ids_list = [i.strip() for i in candidate_ids.split(",") if i.strip()]
    result = approve_tag_candidates(workspace, ids_list)
    _display_result(result, json_output)


@tag_app.command()
def list(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status: pending, approved, rejected"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """List tag candidates from log/tag-candidates.json."""
    from construct.services.knowledge import list_tag_candidates

    result = list_tag_candidates(workspace, status=status)
    if json_output:
        typer.echo(
            json.dumps({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            }, indent=2, default=str)
        )
    else:
        if not result.success:
            typer.secho(f"✗ {result.message}", fg=typer.colors.RED)
            return
        data = result.data or {}
        candidates = data.get("candidates", [])
        if not candidates:
            typer.echo("No tag candidates found.")
            return
        typer.echo(f"Tag candidates ({len(candidates)}):")
        for c in candidates:
            typer.echo(
                f"  [{c.get('id', '?')}] {c.get('tag', '?')} "
                f"(domain: {c.get('domain_id', '?')}, "
                f"confidence: {c.get('confidence', 0):.2f}, "
                f"status: {c.get('status', '?')})"
            )


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

    try:
        cap = get_registry().get("knowledge.card.create")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, card_data, author=CardAuthor(author))
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

    try:
        cap = get_registry().get("knowledge.card.edit")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, card_id, updates, author=CardAuthor(author))
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
    try:
        cap = get_registry().get("knowledge.card.archive")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, card_id, author=CardAuthor(author))
    _display_result(result, json_output)


# -- Connection commands ---------------------------------------------------

connection_app = typer.Typer(
    no_args_is_help=True,
    name="connection",
    help="Connection CRUD operations.",
)
knowledge_app.add_typer(connection_app)


@connection_app.command("add")
def connection_add(
    ctx: typer.Context,
    from_id: str = typer.Argument(..., help="Source card ID"),
    to_id: str = typer.Argument(..., help="Target card ID"),
    conn_type: str = typer.Option(..., "--type", "-t", help=f"Connection type: {[e.value for e in ConnectionType]}"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Optional note about this connection"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    created_by: str = typer.Option("construct", "--by", "-b", help="Creator role"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Add a typed connection between two cards."""
    try:
        ctype = ConnectionType(conn_type)
    except ValueError:
        typer.echo(f"Invalid connection type: {conn_type}. Valid: {[e.value for e in ConnectionType]}")
        raise typer.Exit(code=1)

    try:
        cap = get_registry().get("knowledge.connection.add")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(
        workspace, from_id, to_id, ctype,
        note=note, created_by=ConnectionAuthor(created_by),
    )
    _display_result(result, json_output)


@connection_app.command("remove")
def connection_remove(
    ctx: typer.Context,
    from_id: str = typer.Argument(..., help="Source card ID"),
    to_id: str = typer.Argument(..., help="Target card ID"),
    conn_type: str = typer.Option(..., "--type", "-t", help="Connection type to remove"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Remove a typed connection between two cards."""
    try:
        ctype = ConnectionType(conn_type)
    except ValueError:
        typer.echo(f"Invalid connection type: {conn_type}")
        raise typer.Exit(code=1)

    try:
        cap = get_registry().get("knowledge.connection.remove")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, from_id, to_id, ctype)
    _display_result(result, json_output)


@connection_app.command("list")
def connection_list(
    ctx: typer.Context,
    card_id: Optional[str] = typer.Option(None, "--card", "-c", help="Filter by card ID"),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived card connections"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """List typed connections. Optionally filter by card or include archived."""
    try:
        cap = get_registry().get("knowledge.connection.list")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, card_id=card_id, include_archived=include_archived)
    _display_result(result, json_output)


def main() -> None:
    """Run the CONSTRUCT CLI application."""
    app()


if __name__ == "__main__":
    main()
