"""CLI shell for CONSTRUCT."""

from __future__ import annotations

from pathlib import Path
import builtins
import json
import re
import sys
from typing import Any, List, Optional

import typer

from construct.schemas.card import CardAuthor, Lifecycle
from construct.schemas.workspace import ConnectionAuthor, ConnectionType
from construct.services.init import DomainInitInput, WorkspaceInitError, initialize_workspace
from construct.services.knowledge import OperationResult
from construct.capabilities.catalog import get_registry
from construct.mcp.server import run_server


app = typer.Typer(no_args_is_help=True)

KEBAB_CASE_SANITIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def _version_callback(value: bool) -> None:
    if value:
        from construct import __version__

        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the CONSTRUCT version and exit.",
    ),
) -> None:
    """CONSTRUCT — local-first, agent-powered personal knowledge system."""


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


# D-10 / CUR-05: the `workflow run` / `workflow resume` commands existed only to
# drive the fake-success curation-cycle step placeholder (which lived in both
# catalog.py and here — Pitfall 6). Both are removed; `construct curation run` is
# now the sole canonical curation entrypoint. Only `workflow status` remains — it
# reports real persisted workflow-runner state.
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
    title: str = typer.Option(None, "--title", "-t", help="Title to record (also used to derive the ref id)"),
    relevance: float = typer.Option(None, "--relevance", help="Relevance score 0.0-1.0"),
    tier: int = typer.Option(None, "--tier", help="Source tier 1 (best) - 5 (unverified)"),
    finding: Optional[List[str]] = typer.Option(None, "--finding", help="Key finding (repeatable)"),
    category: Optional[List[str]] = typer.Option(None, "--category", help="Content category (repeatable)"),
    year: int = typer.Option(None, "--year", help="Publication year"),
    venue: str = typer.Option(None, "--venue", help="Publication venue"),
    cluster: str = typer.Option(None, "--cluster", help="Search cluster label"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Ingest a source (file, URL, note, or web research) into the workspace.

    Metadata flags let the orchestrator persist what it already extracted from a
    source instead of relying on the pipeline's conservative defaults.
    """
    try:
        cap = get_registry().get("ingest.source")
    except KeyError:
        typer.echo("ERROR: Capability not found.")
        raise typer.Exit(code=1)
    result = cap.handler(
        workspace,
        source=source,
        domain_hint=domain,
        author=author,
        title=title,
        relevance=relevance,
        source_tier=tier,
        key_findings=finding or None,
        content_categories=category or None,
        year=year,
        venue=venue,
        search_cluster=cluster,
    )
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
# Research command group (Phase 8)
# ---------------------------------------------------------------------------

research_app = typer.Typer(
    no_args_is_help=True,
    name="research",
    help="Read-only research search via configured providers.",
)
app.add_typer(research_app)

curation_app = typer.Typer(
    no_args_is_help=True,
    name="curation",
    help="Run deterministic curation maintenance checks (read-only).",
)
app.add_typer(curation_app)

daily_app = typer.Typer(
    no_args_is_help=True,
    name="daily",
    help="Run the non-blocking daily maintenance cycle (research → curation → graph health).",
)
app.add_typer(daily_app)


@research_app.command(name="search")
def research_search_cmd(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    query: str | None = typer.Option(None, "--query", "-q", help="Single search query"),
    queries: Optional[str] = typer.Option(
        None,
        "--queries",
        help="Comma-separated batch queries",
    ),
    cluster_id: str | None = typer.Option(None, "--cluster-id", help="Search by seed cluster ID"),
    max_results: int | None = typer.Option(None, "--max-results", help="Max results per query (1-50)"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Run provider-agnostic web search and return normalized results (read-only)."""
    modes = [query is not None, queries is not None, cluster_id is not None]
    if sum(modes) != 1:
        typer.echo("ERROR: specify exactly one of --query, --queries, or --cluster-id")
        raise typer.Exit(code=1)

    handler_kwargs: dict[str, object] = {"workspace_path": str(workspace)}
    if query is not None:
        handler_kwargs["query"] = query
    elif queries is not None:
        handler_kwargs["queries"] = _parse_csv(queries)
    else:
        handler_kwargs["cluster_id"] = cluster_id

    if max_results is not None:
        handler_kwargs["max_results"] = max_results

    try:
        cap = get_registry().get("research.search")
    except KeyError:
        typer.echo("ERROR: Capability 'research.search' not found. Ensure Phase 8 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)
    _display_result(result, json_output)


def _flatten_search_results_payload(payload: Any) -> list[Any]:
    """Flatten a pre-fetched search payload into SearchResult dicts (D-10)."""
    from construct.search.models import SearchResult

    def _validate(items: list[Any]) -> list[Any]:
        return [SearchResult.model_validate(item).model_dump(mode="json") for item in items]

    # NB: `list` is shadowed at module scope by the `list` Typer commands below,
    # so reference the builtin explicitly here.
    if isinstance(payload, builtins.list):
        if not payload:
            return []
        first = payload[0]
        if isinstance(first, dict) and "results" in first and "provider_name" in first:
            flat: list[Any] = []
            for batch in payload:
                if not isinstance(batch, dict):
                    raise ValueError("batch entries must be objects with a 'results' array")
                flat.extend(batch.get("results", []))
            return _validate(flat)
        return _validate(payload)

    if isinstance(payload, dict):
        if "batches" in payload:
            batches = payload["batches"]
            if not isinstance(batches, builtins.list):
                raise ValueError("'batches' must be an array of batch objects")
            flat = []
            for batch in batches:
                if not isinstance(batch, dict):
                    raise ValueError("batch entries must be objects with a 'results' array")
                flat.extend(batch.get("results", []))
            return _validate(flat)
        if "results" in payload:
            return _validate(payload["results"])

    raise ValueError("Unrecognized search results payload shape")


def _load_search_results_json(raw: str) -> list[Any]:
    payload = json.loads(raw)
    return _flatten_search_results_payload(payload)


def _render_research_score_table(data: dict[str, Any]) -> None:
    """Human-readable url/score/tier/action table plus degraded notice (D-13)."""
    typer.echo("url\tscore\ttier\taction")
    for finding in data.get("findings", []):
        typer.echo(
            f"{finding.get('url', '')}\t"
            f"{finding.get('relevance_score', '')}\t"
            f"{finding.get('source_tier', '')}\t"
            f"{finding.get('ingest_action', '')}"
        )
    retrieval = data.get("retrieval", {})
    typer.echo(
        f"degraded: {retrieval.get('degraded', False)}, "
        f"retried: {retrieval.get('retried', 0)}, "
        f"errors: {retrieval.get('errors', 0)}"
    )


@research_app.command(name="score")
def research_score_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    results_file: Path | None = typer.Option(
        None, "--results-file", help="JSON file of SearchResults (or batches envelope)"
    ),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Score pre-fetched search results into governance-aware finding proposals."""
    if results_file is not None:
        raw = results_file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        typer.echo("ERROR: provide --results-file or pipe JSON on stdin")
        raise typer.Exit(code=1)

    try:
        flattened = _load_search_results_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"ERROR: invalid results payload: {exc}")
        raise typer.Exit(code=1) from exc

    handler_kwargs = {
        "workspace_path": str(workspace),
        "results": flattened,
    }

    try:
        cap = get_registry().get("research.score")
    except KeyError:
        typer.echo("ERROR: Capability 'research.score' not found. Ensure Phase 9 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)

    if json_output:
        _display_result(result, json_output=True)
        return

    if not result.success:
        _display_result(result, json_output=False)
        return

    if result.data:
        _render_research_score_table(result.data)
    typer.echo(f"✓ {result.message}")


def _render_run_result(data: dict[str, Any]) -> None:
    """Human-readable RunResult summary: status, handles, ingest counts, digest,
    seed update, and the audit event trail (D-12)."""
    typer.echo(f"status: {data.get('status', '')}")
    typer.echo(f"run_id: {data.get('run_id', '')}")
    typer.echo(f"gate_id: {data.get('gate_id', '')}")
    gate_queue = data.get("gate_queue") or []
    refs = data.get("refs_created") or []
    cards = data.get("cards_created") or []
    typer.echo(f"pending: {len(gate_queue)}, refs: {len(refs)}, cards: {len(cards)}")
    if data.get("digest_path"):
        typer.echo(f"digest_path: {data.get('digest_path')}")
    if data.get("seed_update"):
        typer.echo(f"seed_update: {data.get('seed_update')}")
    events = data.get("events") or []
    if events:
        typer.echo(f"events: {', '.join(events)}")
    if data.get("degraded"):
        typer.echo("degraded: True")


def _emit_run_result(result: OperationResult, json_output: bool) -> None:
    """Render a research-run OperationResult: JSON passthrough or RunResult table."""
    if json_output:
        _display_result(result, json_output=True)
        return
    if not result.success:
        _display_result(result, json_output=False)
        return
    if result.data:
        _render_run_result(result.data)
    typer.echo(f"✓ {result.message}")


@research_app.command(name="run")
def research_run_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Override the search/scoring provider"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Start a durable research run; pauses at the human-review gate (no writes before approval)."""
    handler_kwargs: dict[str, object] = {"workspace_path": str(workspace)}
    if provider is not None:
        handler_kwargs["provider_override"] = provider

    try:
        cap = get_registry().get("research.run")
    except KeyError:
        typer.echo("ERROR: Capability 'research.run' not found. Ensure Phase 10 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)
    _emit_run_result(result, json_output)


@research_app.command(name="review")
def research_review_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The paused run/gate handle to resume"),
    decisions_file: Optional[Path] = typer.Option(
        None, "--decisions-file", help="JSON file of per-finding decisions (or pipe on stdin)"
    ),
    approve_all: bool = typer.Option(
        False, "--approve-all", help="Approve every finding's recommended ingest action"
    ),
    reject_all: bool = typer.Option(False, "--reject-all", help="Reject (skip) every finding"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Resume a paused run with per-finding decisions (or --approve-all / --reject-all)."""
    if sum([decisions_file is not None, approve_all, reject_all]) > 1:
        typer.echo("ERROR: specify at most one of --decisions-file, --approve-all, or --reject-all")
        raise typer.Exit(code=1)

    handler_kwargs: dict[str, object] = {"workspace_path": str(workspace), "run_id": run_id}

    raw: str | None = None
    if decisions_file is not None:
        raw = decisions_file.read_text(encoding="utf-8")
    elif not approve_all and not reject_all and not sys.stdin.isatty():
        raw = sys.stdin.read()

    if raw:
        try:
            handler_kwargs["decisions"] = json.loads(raw)
        except json.JSONDecodeError as exc:
            typer.echo(f"ERROR: invalid decisions payload: {exc}")
            raise typer.Exit(code=1) from exc
    if approve_all:
        handler_kwargs["approve_all"] = True
    if reject_all:
        handler_kwargs["reject_all"] = True

    try:
        cap = get_registry().get("research.review")
    except KeyError:
        typer.echo("ERROR: Capability 'research.review' not found. Ensure Phase 10 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)
    _emit_run_result(result, json_output)


@research_app.command(name="inspect")
def research_inspect_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The run/gate handle to inspect"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Report a run's pending review state (read-only; never resumes or writes)."""
    handler_kwargs = {"workspace_path": str(workspace), "run_id": run_id}

    try:
        cap = get_registry().get("research.inspect")
    except KeyError:
        typer.echo("ERROR: Capability 'research.inspect' not found. Ensure Phase 10 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)
    _emit_run_result(result, json_output)


# ---------------------------------------------------------------------------
# Curation command group (Phase 11)
# ---------------------------------------------------------------------------


def _render_curation_result(data: dict[str, Any]) -> None:
    """Human-readable CurationRunResult summary: run status, run_id, and a
    per-step line (step name, status, one-line summary) so the user can VISUALLY
    distinguish completed vs degraded vs skipped steps (criterion #2)."""
    typer.echo(f"status: {data.get('status', '')}")
    typer.echo(f"run_id: {data.get('run_id', '')}")
    steps = data.get("steps") or []
    for step in steps:
        name = step.get("step", "")
        status = step.get("status", "")
        summary = step.get("summary", "") or step.get("reason", "") or ""
        line = f"  - {name}: {status}"
        if summary:
            line += f" — {summary}"
        typer.echo(line)
    events = data.get("events") or []
    if events:
        typer.echo(f"events: {', '.join(events)}")


def _emit_curation_result(result: OperationResult, json_output: bool) -> None:
    """Render a curation OperationResult: full-fidelity JSON passthrough, or the
    curation per-step table on success / the generic error render on failure."""
    if json_output:
        _display_result(result, json_output=True)
        return
    if not result.success:
        _display_result(result, json_output=False)
        return
    if result.data:
        _render_curation_result(result.data)
    typer.echo(f"✓ {result.message}")


@curation_app.command(name="run")
def curation_run_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Run the deterministic curation cycle (integrity, decay, orphan, connection-health, report)."""
    try:
        cap = get_registry().get("curation.run")
    except KeyError:
        typer.echo("ERROR: Capability 'curation.run' not found. Ensure Phase 11 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(workspace_path=str(workspace))
    _emit_curation_result(result, json_output)


@curation_app.command(name="inspect")
def curation_inspect_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The curation run to inspect"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Report a curation run's persisted state (read-only; never re-runs)."""
    try:
        cap = get_registry().get("curation.inspect")
    except KeyError:
        typer.echo("ERROR: Capability 'curation.inspect' not found. Ensure Phase 11 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(workspace_path=str(workspace), run_id=run_id)
    _emit_curation_result(result, json_output)


@curation_app.command(name="review")
def curation_review_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The paused curation run to resume"),
    decisions_file: Optional[Path] = typer.Option(
        None, "--decisions-file", help="JSON file of per-item decisions (or pipe on stdin)"
    ),
    approve_all: bool = typer.Option(
        False, "--approve-all", help="Approve every proposal's recommended write"
    ),
    reject_all: bool = typer.Option(
        False, "--reject-all", help="Reject (write nothing for) every proposal"
    ),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Resume a paused curation run with per-item decisions (or --approve-all / --reject-all)."""
    if sum([decisions_file is not None, approve_all, reject_all]) > 1:
        typer.echo("ERROR: specify at most one of --decisions-file, --approve-all, or --reject-all")
        raise typer.Exit(code=1)

    handler_kwargs: dict[str, object] = {"workspace_path": str(workspace), "run_id": run_id}

    raw: str | None = None
    if decisions_file is not None:
        raw = decisions_file.read_text(encoding="utf-8")
    elif not approve_all and not reject_all and not sys.stdin.isatty():
        raw = sys.stdin.read()

    if raw:
        try:
            handler_kwargs["decisions"] = json.loads(raw)
        except json.JSONDecodeError as exc:
            typer.echo(f"ERROR: invalid decisions payload: {exc}")
            raise typer.Exit(code=1) from exc
    if approve_all:
        handler_kwargs["approve_all"] = True
    if reject_all:
        handler_kwargs["reject_all"] = True

    try:
        cap = get_registry().get("curation.review")
    except KeyError:
        typer.echo("ERROR: Capability 'curation.review' not found. Ensure Phase 12 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)
    _emit_curation_result(result, json_output)


# ---------------------------------------------------------------------------
# Daily command group (Phase 13)
# ---------------------------------------------------------------------------


def _render_daily_result(data: dict[str, Any]) -> None:
    """Human-readable DailyRunResult summary: parent status/run_id, one line per
    composed child (capability + status), the pending-escalation count, and a
    graph-health line (cards/connections/domains) so the user can VISUALLY
    distinguish a clean daily cycle from a degraded one."""
    typer.echo(f"status: {data.get('status', '')}")
    typer.echo(f"run_id: {data.get('run_id', '')}")
    children = data.get("children") or []
    for child in children:
        capability = child.get("capability", "")
        status = child.get("status", "")
        line = f"  - {capability}: {status}"
        message = child.get("message", "") or ""
        if message:
            line += f" — {message}"
        typer.echo(line)
    typer.echo(f"pending_escalations: {data.get('pending_escalations', 0)}")
    health = data.get("graph_health") or {}
    if health:
        typer.echo(
            "graph_health: "
            f"cards={health.get('cards', '?')}, "
            f"connections={health.get('connections', '?')}, "
            f"domains={health.get('domains', '?')}"
        )


def _emit_daily_result(result: OperationResult, json_output: bool) -> None:
    """Render a daily OperationResult: full-fidelity JSON passthrough, or the
    daily child/health summary on success / the generic error render on failure."""
    if json_output:
        _display_result(result, json_output=True)
        return
    if not result.success:
        _display_result(result, json_output=False)
        return
    if result.data:
        _render_daily_result(result.data)
    typer.echo(f"✓ {result.message}")


@daily_app.command(name="run")
def daily_run_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Run the non-blocking daily cycle (research.run → curation.run → graph.status)."""
    try:
        cap = get_registry().get("daily.run")
    except KeyError:
        typer.echo("ERROR: Capability 'daily.run' not found. Ensure Phase 13 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(workspace_path=str(workspace))
    _emit_daily_result(result, json_output)


@daily_app.command(name="inspect")
def daily_inspect_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The daily run to inspect"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Read a persisted daily-run receipt (read-only; never re-runs)."""
    try:
        cap = get_registry().get("daily.inspect")
    except KeyError:
        typer.echo("ERROR: Capability 'daily.inspect' not found. Ensure Phase 13 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(workspace_path=str(workspace), run_id=run_id)
    _emit_daily_result(result, json_output)


# ---------------------------------------------------------------------------
# Views command group (Phase 6)
# ---------------------------------------------------------------------------

views_app = typer.Typer(
    no_args_is_help=True,
    name="views",
    help="Generate and validate views data contracts for an install root.",
)
app.add_typer(views_app)


@views_app.command()
def generate(
    ctx: typer.Context,
    install_root: Path | None = typer.Option(None, "--install-root"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Generate the views JSON data files from workspace state.

    Reads every workspace under the install root and writes
    views/build/data/*.json. Validation errors are fatal; content warnings
    describe source material and do not fail the run.

    ``--install-root`` defaults to the working directory AT CALL TIME. Declaring
    ``typer.Option(Path.cwd(), ...)`` would evaluate it at *import* time, so any
    process that imports construct.cli before changing directory -- test runners,
    long-lived hosts, anything introspecting the CLI -- would silently get the
    wrong default (WR-09).
    """
    from construct.views.generate import generate as run_generate, install_root_error

    install_root = install_root or Path.cwd()

    # CR-03: --install-root defaults to the process working directory, so an
    # accidental bare `construct views generate` would otherwise scaffold a
    # views/build/data/ tree wherever the user happens to be standing and report
    # the resulting empty build as a success.
    guard = install_root_error(install_root)
    if guard is not None:
        typer.secho(f"ERROR: {guard} (at {install_root})", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    report = run_generate(install_root)

    if json_output:
        typer.echo(json.dumps({
            "success": bool(report.success) and not report.validation_errors,
            "build_id": report.build_id,
            "total_files_written": report.total_files_written,
            "validation_errors": list(report.validation_errors),
            "warnings": list(report.warnings),
        }, indent=2))
    else:
        typer.echo(
            f"Views data generation: build {report.build_id}, "
            f"{report.total_files_written} files written, "
            f"{len(report.validation_errors)} validation errors, "
            f"{len(report.warnings)} content warnings"
        )
        for err in report.validation_errors:
            typer.secho(f"  ✗ validation error: {err}", fg=typer.colors.RED)
        for warn in report.warnings:
            typer.echo(f"  ! warning (advisory): {warn}")

    if report.validation_errors:
        raise typer.Exit(code=1)


@views_app.command()
def validate(
    ctx: typer.Context,
    install_root: Path | None = typer.Option(None, "--install-root"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Validate views data files against their Pydantic schemas.

    Reads <install-root>/views/build/data/*.json and validates each file
    against its declared contract model. Reports per-file pass/fail.

    ``--install-root`` is resolved at call time, not import time (WR-09).
    """
    install_root = install_root or Path.cwd()
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
        unwrap_payload,
        validate_data,
    )

    build_data_dir = install_root / "views" / "build" / "data"
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
            # A view file the generator did not emit is reported but is not a
            # validation failure — completeness of the build is the generator's
            # concern, not the schema gate's.
            results.append({"file": filename, "status": "missing", "errors": []})
            continue
        try:
            import json
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            data = raw if isinstance(raw, dict) else {}
            # Accept both the flat generator output and the envelope form.
            payload = unwrap_payload(data)
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
                payload = unwrap_payload(data)
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


# Top-level `card` group hosting the L3 promotion gate (`construct card evaluate`).
# Distinct from the `knowledge card` CRUD group: evaluate proposes lifecycle
# promotions (read-only), it is not a card CRUD op.
card_gate_app = typer.Typer(
    no_args_is_help=True,
    name="card",
    help="Card-level L3 gates (promotion evaluation).",
)
app.add_typer(card_gate_app)


@card_gate_app.command(name="evaluate")
def card_evaluate_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Override the evaluation provider"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Evaluate non-mature cards through the L3 promotion gate (read-only; no writes)."""
    handler_kwargs: dict[str, object] = {"workspace_path": str(workspace)}
    if provider is not None:
        handler_kwargs["provider_override"] = provider

    try:
        cap = get_registry().get("card.evaluate")
    except KeyError:
        typer.echo("ERROR: Capability 'card.evaluate' not found. Ensure Phase 12 is complete.")
        raise typer.Exit(code=1)

    result = cap.handler(**handler_kwargs)
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
