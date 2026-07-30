"""CLI shell for CONSTRUCT."""

from __future__ import annotations

from pathlib import Path
import builtins
import json
import re
import sys
from typing import Any, List, Optional

import typer

from construct.llm.curation_run import ESCALATED_LABEL
from construct.schemas.card import Lifecycle
from construct.schemas.workspace import ConnectionType
from construct.services.init import DomainInitInput, WorkspaceInitError, initialize_workspace
from construct.services.knowledge import OperationResult
from construct.capabilities.catalog import get_registry
from construct.capabilities.errors import CapabilityInputError, CapabilityNotFoundError
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
        report = get_registry().invoke("workspace.validate", {"path": path})
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
        items = get_registry().invoke("workspace.status", {"path": path})
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
            result = get_registry().invoke("help.suggest", {"workspace": workspace})
        except (CapabilityInputError, CapabilityNotFoundError) as exc:
            typer.echo(f"ERROR {exc}")
            raise typer.Exit(code=1) from exc
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


#: Outcomes that genuinely warrant an unqualified success verdict. Anything else
#: — degraded, awaiting_review, or a future member — is rendered qualified, so a
#: new outcome is honest by default rather than silently claiming success.
_CLEAN_OUTCOMES = frozenset({"completed", "succeeded"})


def _verdict_line(result: OperationResult) -> str:
    """The terminal verdict for a command that RAN, qualified by its outcome.

    GOV-05: ``result.success`` means "the command ran" and drives the exit code
    (D-15). It is therefore true for a degraded run, and rendering it as ``✓``
    produced the defect this replaces — an honest ``status: degraded`` line and
    an unqualified ``✓ Curation run degraded.`` in the same output block. A
    capability with no separate outcome to report is unaffected.
    """
    outcome = getattr(result, "outcome", None)
    if outcome and outcome not in _CLEAN_OUTCOMES:
        return f"⚠ {outcome}: {result.message}"
    return f"✓ {result.message}"


def _display_result(result: OperationResult, json_output: bool) -> None:
    """Render an OperationResult to stdout as either JSON or human-readable text."""
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "success": result.success,
                    # GOV-05: "the command ran" and "how it went" are two
                    # different answers, and a script reading only ``success``
                    # was being told a degraded run went fine.
                    "outcome": result.outcome,
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
            typer.echo(_verdict_line(result))
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
        result = get_registry().invoke("workflow.status", {"workspace": workspace})
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
    payload = {
        "workspace": workspace,
        "source": source,
        "domain_hint": domain,
        "author": author,
        "title": title,
        "relevance": relevance,
        "source_tier": tier,
        "key_findings": finding or None,
        "content_categories": category or None,
        "year": year,
        "venue": venue,
        "search_cluster": cluster,
    }
    try:
        result = get_registry().invoke("ingest.source", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
    payload = {
        "workspace_path": str(workspace),
        "domain_id": domain_id,
        "question": question,
        "max_cards": max_cards,
    }
    try:
        result = get_registry().invoke("ask.domain", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
        result = get_registry().invoke(
            "bridge.detect", {"workspace_path": str(workspace)}
        )
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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

    # Only the selected mode's key is placed in the payload. ``ResearchSearchInput``
    # requires exactly one of query/queries/cluster_id to be non-None, so sending
    # all three (two of them None) would still validate — but omitting the
    # unselected keys keeps the payload a description of what the user asked for.
    payload: dict[str, object] = {"workspace_path": str(workspace)}
    if query is not None:
        payload["query"] = query
    elif queries is not None:
        payload["queries"] = _parse_csv(queries)
    else:
        payload["cluster_id"] = cluster_id

    if max_results is not None:
        payload["max_results"] = max_results

    try:
        result = get_registry().invoke("research.search", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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

    payload = {
        "workspace_path": str(workspace),
        "results": flattened,
    }

    try:
        result = get_registry().invoke("research.score", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc

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
    payload: dict[str, object] = {"workspace_path": str(workspace)}
    if provider is not None:
        payload["provider_override"] = provider

    try:
        result = get_registry().invoke("research.run", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _emit_run_result(result, json_output)


@research_app.command(name="review")
def research_review_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The paused run/gate handle to resume"),
    checkpoint_id: str = typer.Option(
        ...,
        "--checkpoint-id",
        help=(
            "The checkpoint id the queue was rendered at (read it from "
            "'research inspect --json'). The resume is refused if the run has moved on."
        ),
    ),
    decisions_file: Optional[Path] = typer.Option(
        None,
        "--decisions-file",
        help='JSON object of per-proposal decisions, {"proposal_id": "decision"} (or pipe on stdin)',
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

    payload: dict[str, object] = {
        "workspace_path": str(workspace),
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
    }

    raw: str | None = None
    if decisions_file is not None:
        raw = decisions_file.read_text(encoding="utf-8")
    elif not approve_all and not reject_all and not sys.stdin.isatty():
        raw = sys.stdin.read()

    if raw:
        try:
            payload["decisions"] = json.loads(raw)
        except json.JSONDecodeError as exc:
            typer.echo(f"ERROR: invalid decisions payload: {exc}")
            raise typer.Exit(code=1) from exc
    if approve_all:
        payload["approve_all"] = True
    if reject_all:
        payload["reject_all"] = True

    try:
        result = get_registry().invoke("research.review", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _emit_run_result(result, json_output)


@research_app.command(name="inspect")
def research_inspect_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The run/gate handle to inspect"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Report a run's pending review state (read-only; never resumes or writes)."""
    payload = {"workspace_path": str(workspace), "run_id": run_id}

    try:
        result = get_registry().invoke("research.inspect", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _emit_run_result(result, json_output)


# ---------------------------------------------------------------------------
# Curation command group (Phase 11)
# ---------------------------------------------------------------------------


#: The outcome buckets, in the order a reader should meet them, each labelled for
#: WHAT ACTUALLY HAPPENED. ``applied`` is the only one behind which a canonical
#: write occurred; the other four exist so "nothing was written" can never again
#: reach a surface as silence, or worse, folded into the applied count (D-16).
_CURATION_BUCKETS = (
    ("applied", "applied"),
    ("no_op", "unchanged — already in that state"),
    ("escalated", f"escalated ({ESCALATED_LABEL})"),
    ("rejected", "rejected — nothing written"),
    ("failed_writes", "failed — nothing written"),
)


def _render_curation_result(data: dict[str, Any]) -> None:
    """Human-readable CurationRunResult summary: run status, run_id, and a
    per-step line (step name, status, one-line summary) so the user can VISUALLY
    distinguish completed vs degraded vs skipped steps (criterion #2).

    The outcome buckets are rendered as SEPARATE counts, never summed, and each
    is listed in queue order so this surface, the ``--json`` payload and the MCP
    result cannot disagree about which items they mean. An empty bucket prints
    nothing at all, which is what keeps a clean run's output byte-identical to
    what it produced before the buckets existed.
    """
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
    for key, label in _CURATION_BUCKETS:
        items = data.get(key) or []
        if not items:
            continue
        typer.echo(f"{label}: {len(items)}")
        for item in items:
            typer.echo(f"  · {item}")
    events = data.get("events") or []
    if events:
        typer.echo(f"events: {', '.join(events)}")


def _emit_curation_result(result: OperationResult, json_output: bool) -> None:
    """Render a curation OperationResult: full-fidelity JSON passthrough, or the
    curation per-step table on success / the generic error render on failure.

    The run-level verdict is the qualified one (GOV-05), so the honest
    ``status:`` line above it and the verdict below it can no longer contradict
    each other inside one output block. Exit codes are untouched: this function
    owns the curation commands' exit code and still returns without raising on
    every branch where the command ran (D-15).
    """
    if json_output:
        _display_result(result, json_output=True)
        return
    if not result.success:
        _display_result(result, json_output=False)
        return
    if result.data:
        _render_curation_result(result.data)
    typer.echo(_verdict_line(result))


@curation_app.command(name="run")
def curation_run_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Run the deterministic curation cycle (integrity, decay, orphan, connection-health, report)."""
    # D-15 / the Phase 11 exit-code contract: a *degraded* run still exits 0.
    # Conversion changes the dispatch path only — ``_emit_curation_result`` is the
    # sole owner of this command's exit code and is untouched.
    try:
        result = get_registry().invoke(
            "curation.run", {"workspace_path": str(workspace)}
        )
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _emit_curation_result(result, json_output)


@curation_app.command(name="inspect")
def curation_inspect_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The curation run to inspect"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Report a curation run's persisted state (read-only; never re-runs)."""
    try:
        result = get_registry().invoke(
            "curation.inspect", {"workspace_path": str(workspace), "run_id": run_id}
        )
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _emit_curation_result(result, json_output)


@curation_app.command(name="review")
def curation_review_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The paused curation run to resume"),
    checkpoint_id: str = typer.Option(
        ...,
        "--checkpoint-id",
        help=(
            "The checkpoint id the queue was rendered at (read it from "
            "'curation inspect --json'). The resume is refused if the run has moved on."
        ),
    ),
    decisions_file: Optional[Path] = typer.Option(
        None,
        "--decisions-file",
        help='JSON object of per-proposal decisions, {"proposal_id": "decision"} (or pipe on stdin)',
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

    payload: dict[str, object] = {
        "workspace_path": str(workspace),
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
    }

    raw: str | None = None
    if decisions_file is not None:
        raw = decisions_file.read_text(encoding="utf-8")
    elif not approve_all and not reject_all and not sys.stdin.isatty():
        raw = sys.stdin.read()

    if raw:
        try:
            payload["decisions"] = json.loads(raw)
        except json.JSONDecodeError as exc:
            typer.echo(f"ERROR: invalid decisions payload: {exc}")
            raise typer.Exit(code=1) from exc
    if approve_all:
        payload["approve_all"] = True
    if reject_all:
        payload["reject_all"] = True

    try:
        result = get_registry().invoke("curation.review", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
        result = get_registry().invoke("daily.run", {"workspace_path": str(workspace)})
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _emit_daily_result(result, json_output)


@daily_app.command(name="inspect")
def daily_inspect_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    run_id: str = typer.Option(..., "--run-id", help="The daily run to inspect"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Read a persisted daily-run receipt (read-only; never re-runs)."""
    try:
        result = get_registry().invoke(
            "daily.inspect", {"workspace_path": str(workspace), "run_id": run_id}
        )
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
            # List literals, not `list(...)`: the `tag list` command below shadows
            # the builtin in this module's globals, so a bare `list()` call here
            # resolves to that Typer command and raises.
            "validation_errors": [*report.validation_errors],
            "warnings": [*report.warnings],
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

    D-02: the validation body no longer lives here. It is the ``views.validate_data``
    capability, dispatched through the one seam — so an agent over MCP (and, from
    Phase 19, over HTTP) reaches exactly this behaviour rather than a re-implementation
    of it. This command's job is now rendering, plus the exit code.

    The file→model map is not written here either. ``construct.views.contracts``
    holds the single copy, and ``views generate`` validates against the same
    tables, so the writer and this command cannot enumerate different files — the
    failure mode that left ``<ws>/stats.json`` and ``<ws>/curation-history.json``
    both unmodelled by the generator and unchecked here. A file added to the
    tables is gated on both sides at once.

    ``--install-root`` is resolved at call time, not import time (WR-09).
    """
    from construct.views.generate import BUILD_DATA_RELPATH

    install_root = install_root or Path.cwd()

    try:
        result = get_registry().invoke(
            "views.validate_data", {"install_root": install_root}
        )
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc

    data = result.data or {}
    results: list[dict] = data.get("results", [])
    all_passed: bool = bool(data.get("all_passed", False))

    # The two pre-file refusals. Neither is a per-file verdict, so neither is
    # rendered through the table below. The reason strings carry no filesystem
    # path by construction (T-18-10) — this is the *local* caller, so it appends
    # the path itself, the convention ``install_root_error`` documents and
    # ``views generate`` above already follows.
    if not results and not all_passed:
        if data.get("missing_data_dir"):
            typer.echo(
                f"ERROR: No views data directory at {install_root / BUILD_DATA_RELPATH}"
            )
            raise typer.Exit(code=1)
        reason = result.errors[0].reason if result.errors else result.message
        typer.secho(f"ERROR: {reason} (at {install_root})", fg=typer.colors.RED)
        raise typer.Exit(code=1)

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

    # The card_data dict this command used to build by hand is now built by
    # ``_build_card_data`` inside the capability's marshalling shim, from these
    # declared field names — one marshaller instead of two copies of it.
    payload: dict[str, object] = {
        "workspace": workspace,
        "title": title,
        "epistemic_type": epistemic_type,
        "domains": domain_list,
        "confidence": confidence,
        "source_tier": source_tier,
        "content_categories": category_list,
        "author": author,
        "summary": summary,
    }
    try:
        result = get_registry().invoke("knowledge.card.create", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
    # T-18-15 — the data-loss edge this plan's prohibition names. ``card edit`` is a
    # PARTIAL update: a field the user did not name must keep its stored value. The
    # seam dispatches ``handler(**model.model_dump())``, and ``model_dump()``
    # materialises a default for every declared field — so a title-only edit would
    # arrive at the handler carrying ``summary=None``, ``lifecycle=None`` and the
    # rest, and any marshaller that forwarded them would blank stored prose.
    #
    # Two independent guards, deliberately both kept:
    #   1. HERE — a key the user did not supply is never put in the payload
    #      (exclude-unset semantics, built at the call site).
    #   2. In ``catalog._build_card_updates`` — it copies a field into the updates
    #      dict only ``if value is not None``, so a materialised default cannot
    #      reach ``edit_card`` even if a future caller sends one.
    # Guard 2 alone is sufficient today; guard 1 means a caller must go out of its
    # way to express "blank this". This repository has destroyed user prose twice
    # through this exact class of defect (the ``archive_card`` body destruction
    # closed by 4e2b909, unrecoverable), so a blanked field is a data-loss bug.
    supplied: dict[str, object] = {
        name: value
        for name, value in (
            ("title", title),
            ("confidence", confidence),
            ("source_tier", source_tier),
            ("lifecycle", lifecycle),
            ("summary", summary),
        )
        if value is not None
    }

    if not supplied:
        typer.echo("No updates provided. Use --title, --confidence, etc. to specify changes.")
        raise typer.Exit(code=1)

    payload: dict[str, object] = {
        "workspace": workspace,
        "card_id": card_id,
        "author": author,
        **supplied,
    }
    try:
        result = get_registry().invoke("knowledge.card.edit", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
    payload = {"workspace": workspace, "card_id": card_id, "author": author}
    try:
        result = get_registry().invoke("knowledge.card.archive", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
    payload: dict[str, object] = {"workspace_path": str(workspace)}
    if provider is not None:
        payload["provider_override"] = provider

    try:
        result = get_registry().invoke("card.evaluate", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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

    # ``ctype.value`` rather than the enum member: ``ConnectionAddInput.conn_type``
    # is declared ``str`` and the shim re-coerces it, so handing the seam a plain
    # string keeps the payload exactly the shape an MCP client would send.
    payload = {
        "workspace": workspace,
        "from_id": from_id,
        "to_id": to_id,
        "conn_type": ctype.value,
        "note": note,
        "created_by": created_by,
    }
    try:
        result = get_registry().invoke("knowledge.connection.add", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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

    payload = {
        "workspace": workspace,
        "from_id": from_id,
        "to_id": to_id,
        "conn_type": ctype.value,
    }
    try:
        result = get_registry().invoke("knowledge.connection.remove", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _display_result(result, json_output)


@card_app.command("list")
def card_list(
    ctx: typer.Context,
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived cards"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """List cards. Optionally filter by domain or include archived cards."""
    # GOV-01: dispatch through the one validating seam rather than reaching for
    # the record and calling its handler directly. Typer has already produced a
    # well-formed payload here, so the seam is a no-op for a valid invocation —
    # the point is that CLI and MCP now share one validation and one error shape.
    payload = {
        "workspace": workspace,
        "domain": domain,
        "include_archived": include_archived,
    }
    try:
        result = get_registry().invoke("knowledge.card.list", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
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
    payload = {
        "workspace": workspace,
        "card_id": card_id,
        "include_archived": include_archived,
    }
    try:
        result = get_registry().invoke("knowledge.connection.list", payload)
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
    _display_result(result, json_output)


def main() -> None:
    """Run the CONSTRUCT CLI application."""
    app()


if __name__ == "__main__":
    main()
