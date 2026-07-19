"""Pre-registered catalog of all CONSTRUCT capabilities."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from construct.capabilities.registry import CapabilityRegistry, CapabilityRecord
from construct.pipelines.workflow_runner import WorkflowRunner
from construct.pipelines.ingestion import ingest_source
from construct.services.init import DomainInitInput, WorkspaceInitError, initialize_workspace
from construct.services.help import suggest as help_suggest
from construct.services.knowledge import (
    CardAuthor,
    ConnectionAuthor,
    OperationError,
    OperationResult,
    add_connection,
    archive_card,
    create_card,
    edit_card,
    list_connections,
    remove_connection,
)
from construct.services.validation import ValidationReport, validate_workspace
from construct.storage.workspace import WorkspaceLoader
from construct.schemas.workspace import ConnectionType
from construct.pipelines.graph_status import graph_status

# ── Ask Domain imports (Phase 5) ──
from construct.llm.ask_domain import (
    AskDomainInput,
    AskDomainOutput,
    run_gate as ask_domain_gate,
)

# ── Bridge Detection imports (Phase 5) ──
from construct.pipelines.bridge_detect import bridge_detect

# ── Research Search imports (Phase 8) ──
from construct.pipelines.research_search import ResearchSearchInput, research_search

# ── Research Score imports (Phase 9) ──
from construct.llm.research_score import (
    ResearchScoreInput,
    ResearchScoreOutageError,
    run_gate as research_score_gate,
)

# ── Research Run imports (Phase 10) ──
from construct.llm.research_run import (
    InspectInput,
    ResearchRunInput,
    ReviewInput,
    inspect_research_run,
    review_research_run,
    run_research_run,
)

# ── Curation Run imports (Phase 11) ──
from construct.llm.curation_run import (
    CurationInspectInput,
    CurationReviewInput,
    CurationRunInput,
    inspect_curation_run,
    review_curation_run,
    run_curation_run,
)

# ── Curation L3 gate imports (Phase 12) ──
from construct.llm.curation_promote import (
    CardEvaluateInput,
    CardEvaluateOutageError,
    run_gate as card_evaluate_gate,
)

# ── Daily Run imports (Phase 13) ──
from construct.llm.daily_run import (
    DailyInspectInput,
    DailyRunInput,
    inspect_daily_run,
    run_daily_run,
)


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class WorkspacePathInput(BaseModel):
    path: Path


class CardCreateInput(BaseModel):
    workspace: Path
    title: str
    epistemic_type: str
    domains: list[str]
    confidence: int = Field(ge=1, le=5)
    source_tier: int = Field(ge=1, le=5)
    content_categories: list[str] = []
    author: str = "construct"
    summary: str = ""


class CardEditInput(BaseModel):
    card_id: str
    workspace: Path
    title: str | None = None
    confidence: int | None = Field(None, ge=1, le=5)
    source_tier: int | None = Field(None, ge=1, le=5)
    lifecycle: str | None = None
    summary: str | None = None
    author: str = "curator"


class CardArchiveInput(BaseModel):
    card_id: str
    workspace: Path
    author: str = "curator"


class ConnectionAddInput(BaseModel):
    from_id: str
    to_id: str
    conn_type: str
    note: str | None = None
    workspace: Path
    created_by: str = "construct"


class ConnectionRemoveInput(BaseModel):
    from_id: str
    to_id: str
    conn_type: str
    workspace: Path


class ConnectionListInput(BaseModel):
    workspace: Path
    card_id: str | None = None
    include_archived: bool = False


class GraphStatusInput(BaseModel):
    workspace: Path


class ViewsGenerateDataInput(BaseModel):
    # D-05: the contract is install-root scoped, not workspace scoped.
    # ``discover_workspaces`` scans only the *children* of its argument, so
    # handing it a single workspace discovers zero workspaces and silently
    # emits empty views.
    install_root: Path


class WorkflowRunInput(BaseModel):
    workspace: Path
    workflow_name: str = "workflow"
    start_step: int = 0


class IngestSourceInput(BaseModel):
    workspace: Path
    source: str
    domain_hint: str | None = None
    author: str = "construct"
    # Optional agent-extracted metadata persisted onto the ref/seed card.
    title: str | None = None
    relevance: float | None = None
    source_tier: int | None = None
    key_findings: list[str] | None = None
    content_categories: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    search_cluster: str | None = None


class HelpSuggestInput(BaseModel):
    workspace: Path


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class ValidateOutput(BaseModel):
    valid: bool
    errors: int
    warnings: int
    report: dict


class StatusOutput(BaseModel):
    items: list[dict]


class BridgeDetectInput(BaseModel):
    """Input for bridge.detect pipeline."""
    model_config = {"extra": "forbid"}
    workspace_path: str


# ---------------------------------------------------------------------------
# Registry factory
# ---------------------------------------------------------------------------


def create_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    registry.register(CapabilityRecord(
        id="workspace.init",
        name="Initialize Workspace",
        description="Create a new CONSTRUCT workspace",
        input_model=WorkspacePathInput,
        output_model=type(None),
        handler=initialize_workspace,
        cli_name="init",
    ))
    registry.register(CapabilityRecord(
        id="workspace.validate",
        name="Validate Workspace",
        description="Validate a CONSTRUCT workspace for structural correctness",
        input_model=WorkspacePathInput,
        output_model=ValidateOutput,
        # RT-03 adapter: WorkspacePathInput.path → validate_workspace(root=...)
        handler=_validate_shim,
        cli_name="validate",
        mcp_tool_name="construct_validate",
    ))
    registry.register(CapabilityRecord(
        id="workspace.status",
        name="Workspace Status",
        description="Show workspace ownership categories and file status",
        input_model=WorkspacePathInput,
        output_model=StatusOutput,
        handler=lambda path: WorkspaceLoader(path).inspect_workspace(),
        cli_name="status",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.card.create",
        name="Create Card",
        description="Create a new knowledge card in the workspace",
        input_model=CardCreateInput,
        output_model=OperationResult,
        # RT-03 adapter: build card_data dict from schema fields (mirrors cli.py:754-771)
        handler=_create_card_shim,
        cli_name="knowledge.card.create",
        mcp_tool_name="construct_create_card",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.card.edit",
        name="Edit Card",
        description="Edit an existing knowledge card",
        input_model=CardEditInput,
        output_model=OperationResult,
        # RT-03 adapter: build updates dict from provided non-None fields (mirrors cli.py:789-799)
        handler=_edit_card_shim,
        cli_name="knowledge.card.edit",
        mcp_tool_name="construct_edit_card",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.card.archive",
        name="Archive Card",
        description="Archive a knowledge card, preserving its connections",
        input_model=CardArchiveInput,
        output_model=OperationResult,
        handler=archive_card,
        cli_name="knowledge.card.archive",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.connection.add",
        name="Add Connection",
        description="Add a typed connection between two cards",
        input_model=ConnectionAddInput,
        output_model=OperationResult,
        # RT-03 adapter: map schema workspace → workspace_root, coerce conn_type/created_by enums
        handler=_add_connection_shim,
        cli_name="knowledge.connection.add",
        mcp_tool_name="construct_add_connection",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.connection.remove",
        name="Remove Connection",
        description="Remove a typed connection between two cards",
        input_model=ConnectionRemoveInput,
        output_model=OperationResult,
        handler=remove_connection,
        cli_name="knowledge.connection.remove",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.connection.list",
        name="List Connections",
        description="List typed connections, optionally filtered by card",
        input_model=ConnectionListInput,
        output_model=OperationResult,
        handler=list_connections,
        cli_name="knowledge.connection.list",
    ))
    registry.register(CapabilityRecord(
        id="graph.status",
        name="Graph Status",
        description="Produce graph health report for a workspace",
        input_model=GraphStatusInput,
        output_model=OperationResult,
        # ING-05: wire the real graph_status() report. Accepts workspace both
        # positionally (help.py:126 calls handler(workspace_id)) and by keyword
        # (GraphStatusInput / MCP pass workspace=...).
        handler=lambda workspace: graph_status(workspace),
        mcp_tool_name="construct_graph_status",
    ))
    registry.register(CapabilityRecord(
        id="views.generate_data",
        name="Generate Views Data",
        description="Generate JSON view data from workspace state",
        input_model=ViewsGenerateDataInput,
        output_model=OperationResult,
        # V41-01 / FIX-01 (D-01): the permanent-failure placeholder is replaced
        # by a real call into construct.views.generate.generate(). Per D-03 the
        # `construct views generate` CLI command reaches the same function by an
        # independent path rather than through this registry, so the two surfaces
        # can drift — RT-01/RT-02 stays open for the views group deliberately.
        handler=_views_generate_handler,
        mcp_tool_name="construct_views_generate_data",
    ))
    # D-10 / CUR-05: the legacy ``workflow.run`` capability existed only to drive
    # the fake-success curation-cycle step placeholder. It is removed here —
    # ``curation.run`` is now the sole canonical curation entrypoint.
    # ``workflow.status`` stays: it reads real persisted WorkflowRunner state and
    # carries no placeholder.
    registry.register(CapabilityRecord(
        id="workflow.status",
        name="Workflow Status",
        description="Check active workflow status",
        input_model=WorkflowRunInput,
        output_model=OperationResult,
        handler=lambda workspace: WorkflowRunner(workspace).status(),
        cli_name="workflow.status",
    ))
    registry.register(CapabilityRecord(
        id="ingest.source",
        name="Ingest Source",
        description="Ingest a file, URL, note, or research source into the workspace",
        input_model=IngestSourceInput,
        output_model=OperationResult,
        # RT-03 adapter: IngestSourceInput.workspace → ingest_source(workspace_root=...);
        # remaining IngestSourceInput fields already match ingest_source keyword params.
        handler=_ingest_source_shim,
        cli_name="ingest.source",
        mcp_tool_name="construct_ingest_source",
    ))
    registry.register(CapabilityRecord(
        id="help.suggest",
        name="Help Suggest",
        description="Analyze workspace state and return next-step recommendations",
        input_model=HelpSuggestInput,
        output_model=OperationResult,
        handler=lambda workspace: help_suggest(workspace),
        cli_name="help.suggest",
        mcp_tool_name="construct_help_suggest",
    ))

    # ── Ask Domain gate (Phase 5) ──
    registry.register(CapabilityRecord(
        id="ask.domain",
        name="Ask Domain",
        description="Grounded Q&A with citations over workspace knowledge cards for a domain",
        input_model=AskDomainInput,
        output_model=AskDomainOutput,
        handler=lambda **kwargs: (
            lambda result: OperationResult(
                success=result.answer is not None,
                message=result.answer or "No answer could be generated from available cards.",
                data=result.model_dump(mode="json"),
            )
        )(ask_domain_gate("ask.domain", AskDomainInput(**kwargs))),
        cli_name="ask.domain",
        mcp_tool_name="construct_ask_domain",
    ))

    # ── Bridge detection (Phase 5) ──
    registry.register(CapabilityRecord(
        id="bridge.detect",
        name="Bridge Detect",
        description="Detect cross-domain bridges via L1 structural, L2 category, and L3 semantic assessment pipeline",
        input_model=BridgeDetectInput,
        output_model=OperationResult,
        handler=lambda **kwargs: bridge_detect(kwargs.get("workspace_path", "")),
        cli_name="bridge.detect",
        mcp_tool_name="construct_bridge_detect",
    ))

    registry.register(CapabilityRecord(
        id="research.search",
        name="Research Search",
        description="Provider-agnostic web search returning normalized results (read-only)",
        input_model=ResearchSearchInput,
        output_model=OperationResult,
        handler=_research_search_shim,
        cli_name="research.search",
        mcp_tool_name="construct_research_search",
    ))

    registry.register(CapabilityRecord(
        id="research.score",
        name="Research Score",
        description="Score normalized search results into governance-aware finding proposals (read-only, no writes)",
        input_model=ResearchScoreInput,
        output_model=OperationResult,
        handler=_research_score_shim,
        cli_name="research.score",
        mcp_tool_name="construct_research_score",
    ))

    # ── Durable research-run workflow (Phase 10) ──
    registry.register(CapabilityRecord(
        id="research.run",
        name="Research Run",
        description="Start a durable, human-gated research cycle (search → score → review); pauses at the review gate, no writes before approval",
        input_model=ResearchRunInput,
        output_model=OperationResult,
        handler=_research_run_shim,
        cli_name="research.run",
        mcp_tool_name="construct_research_run",
    ))
    registry.register(CapabilityRecord(
        id="research.review",
        name="Research Review",
        description="Resume a paused research run with per-finding decisions (or approve-all/reject-all); writes approved refs/cards and the cycle digest",
        input_model=ReviewInput,
        output_model=OperationResult,
        handler=_research_review_shim,
        cli_name="research.review",
        mcp_tool_name="construct_research_review",
    ))
    registry.register(CapabilityRecord(
        id="research.inspect",
        name="Research Inspect",
        description="Report a research run's pending review state (read-only; never resumes or writes)",
        input_model=InspectInput,
        output_model=OperationResult,
        handler=_research_inspect_shim,
        cli_name="research.inspect",
        mcp_tool_name="construct_research_inspect",
    ))

    # ── Deterministic curation-run workflow (Phase 11) ──
    registry.register(CapabilityRecord(
        id="curation.run",
        name="Curation Run",
        description="Run deterministic curation checks (integrity, decay, orphan, connection-health, report); findings-only, no canonical writes",
        input_model=CurationRunInput,
        output_model=OperationResult,
        handler=_curation_run_shim,
        cli_name="curation.run",
        mcp_tool_name="construct_curation_run",
    ))
    registry.register(CapabilityRecord(
        id="curation.inspect",
        name="Curation Inspect",
        description="Report a curation run's persisted state, including any pending-review (awaiting_review) gate queue (read-only; never re-runs)",
        input_model=CurationInspectInput,
        output_model=OperationResult,
        handler=_curation_inspect_shim,
        cli_name="curation.inspect",
        mcp_tool_name="construct_curation_inspect",
    ))
    registry.register(CapabilityRecord(
        id="curation.review",
        name="Curation Review",
        description="Resume a paused curation run with per-item decisions (or approve-all/reject-all); applies approved lifecycle/connection/archive writes",
        input_model=CurationReviewInput,
        output_model=OperationResult,
        handler=_curation_review_shim,
        cli_name="curation.review",
        mcp_tool_name="construct_curation_review",
    ))

    # ── Card promotion L3 gate (Phase 12) ──
    registry.register(CapabilityRecord(
        id="card.evaluate",
        name="Card Evaluate",
        description="Evaluate non-mature cards through the L3 promotion gate into governance-reviewable promote/hold/escalate proposals (read-only, no writes)",
        input_model=CardEvaluateInput,
        output_model=OperationResult,
        handler=_card_evaluate_shim,
        cli_name="card.evaluate",
        mcp_tool_name="construct_card_evaluate",
    ))

    # ── Thin daily-cycle composition (Phase 13) ──
    # D-08: daily.run/daily.inspect mirror the curation.run/inspect siblings; the
    # deleted workflow.run group is NOT revived. MCP parity is free via registry
    # auto-discovery (mcp/server.py is never edited).
    registry.register(CapabilityRecord(
        id="daily.run",
        name="Daily Run",
        description="Run the non-blocking daily maintenance cycle: compose research.run → curation.run → graph.status, auto-apply each gate's recommended decisions, exclude escalate (surfaced as a pending count), and never report a false completed",
        input_model=DailyRunInput,
        output_model=OperationResult,
        handler=_daily_run_shim,
        cli_name="daily.run",
        mcp_tool_name="construct_daily_run",
    ))
    registry.register(CapabilityRecord(
        id="daily.inspect",
        name="Daily Inspect",
        description="Read a persisted daily-run receipt (read-only; never re-runs the cycle)",
        input_model=DailyInspectInput,
        output_model=OperationResult,
        handler=_daily_inspect_shim,
        cli_name="daily.inspect",
        mcp_tool_name="construct_daily_inspect",
    ))

    return registry


def _views_generate_handler(install_root) -> OperationResult:
    """V41-01 / FIX-01 (D-01): run the real views generator and report it.

    A **named single parameter**, so the handler binds both the positional and
    the keyword call form — the same property the ``graph.status`` lambda has.

    D-04 splits the report's two failure channels: validation errors are fatal
    and become ``OperationResult.errors``; content warnings are advisory and
    never make ``success`` False. The message names both counts separately so
    the two are not confused at a glance.
    """
    # Deferred import — matches the convention for heavy views imports.
    from construct.views.generate import generate

    report = generate(Path(install_root))
    errors = [
        OperationError(field="views.validation", reason=err, suggestion="")
        for err in report.validation_errors
    ]
    success = bool(report.success) and not report.validation_errors

    n_err = len(report.validation_errors)
    n_warn = len(report.warnings)
    if success:
        message = (
            f"Views data generated (build {report.build_id}): "
            f"{report.total_files_written} files written, 0 validation errors, "
            f"{n_warn} content warnings"
        )
        if n_warn:
            message += (
                " — the run succeeded; the warnings are advisory and describe "
                "source content, not contract violations"
            )
    else:
        message = (
            f"Views data generation failed (build {report.build_id}): "
            f"{n_err} validation errors, {report.total_files_written} files "
            f"written, {n_warn} content warnings"
        )

    return OperationResult(
        success=success,
        message=message,
        errors=errors,
        data={
            "build_id": report.build_id,
            "workspace_stats": report.workspace_stats,
            "total_files_written": report.total_files_written,
            "warnings": list(report.warnings),
        },
    )


def _validate_shim(*args, **kwargs):
    """RT-03 adapter for workspace.validate. Accepts the MCP keyword form
    (``path=`` from WorkspacePathInput) and the CLI positional form
    (cli.py:88 calls ``handler(path)``)."""
    if args:
        return validate_workspace(args[0])
    return validate_workspace(kwargs["path"])


def _research_search_shim(*args, **kwargs):
    """RT-03 adapter for research.search."""
    if args:
        return research_search(ResearchSearchInput(workspace_path=str(args[0]), query=str(args[1])))
    return research_search(ResearchSearchInput(**kwargs))


def _research_score_shim(*args, **kwargs):
    """RT-03 adapter for research.score."""
    if args:
        raise TypeError("research.score handler requires keyword arguments")
    input_data = ResearchScoreInput(**kwargs)
    try:
        output = research_score_gate("research.score", input_data)
    except ResearchScoreOutageError as exc:
        return OperationResult(
            success=False,
            message=exc.safe_message,
            data={"degraded": True, "total_outage": True},
        )
    except Exception as exc:
        # Pre-flight provider/config failures (missing config, unknown provider,
        # missing API key during model construction, governance/taxonomy load
        # errors) raise before score_all runs, so they never become a
        # ResearchScoreOutageError. Route them through the same key-safe
        # sanitizer used in-loop so the CLI never tracebacks and the MCP surface
        # never leaks raw provider text (CR-01 / T-09-06).
        from construct.llm.research_score import _safe_scoring_cause

        return OperationResult(
            success=False,
            message=f"research.score failed: {_safe_scoring_cause(exc)}",
            data={"degraded": True, "total_outage": False},
        )
    degraded = bool(output.retrieval.get("degraded"))
    message = f"Scored {len(output.findings)} findings"
    if degraded:
        message += " (degraded)"
    return OperationResult(
        success=True,
        message=message,
        data=output.model_dump(mode="json"),
    )


def _run_result_to_operation(cap_id: str, runner) -> OperationResult:
    """Run a research-run runner and wrap its ``RunResult`` in a sanitizing
    ``OperationResult`` (so ``mcp/server.py:_serialize_result`` works unchanged).

    Mirrors ``_research_score_shim``'s error discipline (T-10-15): a total
    provider outage → ``success=False`` carrying only ``degraded``/``total_outage``
    flags (never raw provider text); any other exception → a key-safe sanitized
    message via ``_safe_scoring_cause`` (never raw ``str(exc)``). On a normal
    return the result is a success unless the ``RunResult.status`` is ``failed``
    (e.g. the score gate degraded to a total outage before the gate).
    """
    try:
        result = runner()
    except ResearchScoreOutageError as exc:
        return OperationResult(
            success=False,
            message=exc.safe_message,
            data={"degraded": True, "total_outage": True},
        )
    except Exception as exc:
        from construct.llm.research_score import _safe_scoring_cause

        return OperationResult(
            success=False,
            message=f"{cap_id} failed: {_safe_scoring_cause(exc)}",
            data={"degraded": True, "total_outage": False},
        )
    return OperationResult(
        success=result.status != "failed",
        message=result.message or result.status,
        data=result.model_dump(mode="json"),
    )


def _research_run_shim(*args, **kwargs):
    """RT-03 adapter for research.run (run-start; pauses at the human gate)."""
    if args:
        raise TypeError("research.run handler requires keyword arguments")
    return _run_result_to_operation(
        "research.run", lambda: run_research_run(ResearchRunInput(**kwargs))
    )


def _research_review_shim(*args, **kwargs):
    """RT-03 adapter for research.review (resume with per-finding decisions)."""
    if args:
        raise TypeError("research.review handler requires keyword arguments")
    return _run_result_to_operation(
        "research.review", lambda: review_research_run(ReviewInput(**kwargs))
    )


def _research_inspect_shim(*args, **kwargs):
    """RT-03 adapter for research.inspect (read-only get_state; never resumes)."""
    if args:
        raise TypeError("research.inspect handler requires keyword arguments")
    return _run_result_to_operation(
        "research.inspect", lambda: inspect_research_run(InspectInput(**kwargs))
    )


def _curation_result_to_operation(cap_id: str, runner) -> OperationResult:
    """Run a curation runner and wrap its ``CurationRunResult`` in a sanitizing
    ``OperationResult`` (so ``mcp/server.py:_serialize_result`` works unchanged).

    Simpler than ``_run_result_to_operation``: curation is deterministic, so there
    is NO ``ResearchScoreOutageError`` provider-outage path. Any exception →
    ``success=False`` with a key-safe class-name message; a normal return is a
    success unless the ``CurationRunResult.status`` is ``failed``.
    """
    try:
        result = runner()
    except Exception as exc:
        return OperationResult(
            success=False,
            message=f"{cap_id} failed: {type(exc).__name__}",
            data={"failed": True},
        )
    return OperationResult(
        success=result.status != "failed",
        message=result.message or result.status,
        data=result.model_dump(mode="json"),
    )


def _curation_run_shim(*args, **kwargs):
    """RT-03 adapter for curation.run (deterministic findings-only cycle)."""
    if args:
        raise TypeError("curation.run handler requires keyword arguments")
    return _curation_result_to_operation(
        "curation.run", lambda: run_curation_run(CurationRunInput(**kwargs))
    )


def _curation_inspect_shim(*args, **kwargs):
    """RT-03 adapter for curation.inspect (read-only get_state; never re-runs)."""
    if args:
        raise TypeError("curation.inspect handler requires keyword arguments")
    return _curation_result_to_operation(
        "curation.inspect", lambda: inspect_curation_run(CurationInspectInput(**kwargs))
    )


def _curation_review_shim(*args, **kwargs):
    """RT-03 adapter for curation.review (resume a paused run with per-item
    decisions; applies approved lifecycle/connection/archive writes)."""
    if args:
        raise TypeError("curation.review handler requires keyword arguments")
    return _curation_result_to_operation(
        "curation.review", lambda: review_curation_run(CurationReviewInput(**kwargs))
    )


def _card_evaluate_shim(*args, **kwargs):
    """RT-03 adapter for card.evaluate (L3 promotion gate; read-only, no writes).

    Mirrors ``_research_score_shim``'s error discipline (T-12-04 / WR-06): a total
    provider outage → ``success=False`` carrying only ``degraded``/``total_outage``
    flags (never raw provider text); any other exception → a key-safe sanitized
    message via the gate module's ``_safe_scoring_cause`` (never raw ``str(exc)``).
    """
    if args:
        raise TypeError("card.evaluate handler requires keyword arguments")
    input_data = CardEvaluateInput(**kwargs)
    try:
        output = card_evaluate_gate("card.evaluate", input_data)
    except CardEvaluateOutageError as exc:
        return OperationResult(
            success=False,
            message=exc.safe_message,
            data={"degraded": True, "total_outage": True},
        )
    except Exception as exc:
        from construct.llm.curation_promote import _safe_scoring_cause

        return OperationResult(
            success=False,
            message=f"card.evaluate failed: {_safe_scoring_cause(exc)}",
            data={"degraded": True, "total_outage": False},
        )
    degraded = bool(output.retrieval.get("degraded"))
    message = f"Evaluated {len(output.decisions)} cards"
    if degraded:
        message += " (degraded)"
    return OperationResult(
        success=True,
        message=message,
        data=output.model_dump(mode="json"),
    )


def _daily_result_to_operation(cap_id: str, runner) -> OperationResult:
    """Run a daily runner and wrap its ``DailyRunResult`` in a sanitizing
    ``OperationResult`` (so ``mcp/server.py:_serialize_result`` works unchanged).

    Mirrors ``_curation_result_to_operation``: any exception →
    ``success=False`` with a key-safe class-name message; a normal return is a
    success unless the ``DailyRunResult.status`` is ``failed`` — a degraded cycle
    still maps to ``success=True`` (the degraded-exits-0 exit-code contract).
    """
    try:
        result = runner()
    except Exception as exc:
        return OperationResult(
            success=False,
            message=f"{cap_id} failed: {type(exc).__name__}",
            data={"failed": True},
        )
    return OperationResult(
        success=result.status != "failed",
        message=result.message or result.status,
        data=result.model_dump(mode="json"),
    )


def _daily_run_shim(*args, **kwargs):
    """Keyword-only adapter for daily.run (thin research→curation→graph cycle)."""
    if args:
        raise TypeError("daily.run handler requires keyword arguments")
    return _daily_result_to_operation(
        "daily.run", lambda: run_daily_run(DailyRunInput(**kwargs))
    )


def _daily_inspect_shim(*args, **kwargs):
    """Keyword-only adapter for daily.inspect (read a receipt; never re-runs)."""
    if args:
        raise TypeError("daily.inspect handler requires keyword arguments")
    return _daily_result_to_operation(
        "daily.inspect", lambda: inspect_daily_run(DailyInspectInput(**kwargs))
    )


def _create_card_shim(*args, **kwargs):
    """RT-03 adapter for knowledge.card.create.

    - MCP keyword form: schema fields (workspace, title, epistemic_type, …) are
      marshalled into a card_data dict mirroring cli.py:754-764.
    - CLI positional form (cli.py:771): ``handler(workspace, card_data, author=…)``
      is already marshalled — pass straight through to create_card.
    """
    if args:
        return create_card(*args, **kwargs)
    return create_card(
        kwargs["workspace"],
        _build_card_data(kwargs),
        author=CardAuthor(kwargs.get("author", "construct")),
    )


def _edit_card_shim(*args, **kwargs):
    """RT-03 adapter for knowledge.card.edit.

    - MCP keyword form: provided non-None schema fields marshalled into an
      updates dict mirroring cli.py:789-799.
    - CLI positional form (cli.py:810): ``handler(workspace, card_id, updates,
      author=…)`` is already marshalled — pass straight through to edit_card.
    """
    if args:
        return edit_card(*args, **kwargs)
    return edit_card(
        kwargs["workspace"],
        kwargs["card_id"],
        _build_card_updates(kwargs),
        author=CardAuthor(kwargs.get("author", "curator")),
    )


def _add_connection_shim(*args, **kwargs):
    """RT-03 adapter for knowledge.connection.add.

    - MCP keyword form: schema fields (workspace, from_id, to_id, conn_type, …);
      conn_type/created_by are coerced to their enums and workspace maps to
      workspace_root.
    - CLI positional form (cli.py:865-868): ``handler(workspace, from_id, to_id,
      ctype, note=…, created_by=…)`` already passes a ConnectionType — pass
      straight through to add_connection.
    """
    if args:
        return add_connection(*args, **kwargs)
    return add_connection(
        kwargs["workspace"],
        kwargs["from_id"],
        kwargs["to_id"],
        ConnectionType(kwargs["conn_type"]),
        note=kwargs.get("note"),
        created_by=ConnectionAuthor(kwargs.get("created_by", "construct")),
    )


def _ingest_source_shim(*args, **kwargs):
    """RT-03 adapter for ingest.source.

    - MCP keyword form: IngestSourceInput.workspace maps to ingest_source's
      ``workspace_root`` positional; remaining fields already match its keyword
      params.
    - CLI positional form (cli.py:306): ``handler(workspace, source, …)`` passes
      straight through to ingest_source.
    """
    if args:
        return ingest_source(*args, **kwargs)
    rest = dict(kwargs)
    workspace = rest.pop("workspace")
    return ingest_source(workspace, **rest)


def _build_card_data(kwargs: dict) -> dict:
    """Marshal CardCreateInput schema kwargs into a create_card card_data dict.

    Mirrors the CLI marshalling at cli.py:754-764: summary maps to the
    ``_summary`` key when non-empty; author is carried in card_data too.
    """
    card_data: dict[str, object] = {
        "title": kwargs.get("title"),
        "epistemic_type": kwargs.get("epistemic_type"),
        "domains": kwargs.get("domains", []),
        "confidence": kwargs.get("confidence"),
        "source_tier": kwargs.get("source_tier"),
        "content_categories": kwargs.get("content_categories", []),
        "author": kwargs.get("author", "construct"),
    }
    summary = kwargs.get("summary")
    if summary:
        card_data["_summary"] = summary
    return card_data


def _build_card_updates(kwargs: dict) -> dict:
    """Marshal CardEditInput schema kwargs into an edit_card updates dict.

    Mirrors the CLI marshalling at cli.py:789-799: only provided non-None
    fields are included; summary maps to the ``_summary`` key.
    """
    updates: dict[str, object] = {}
    for field in ("title", "confidence", "source_tier", "lifecycle"):
        value = kwargs.get(field)
        if value is not None:
            updates[field] = value
    summary = kwargs.get("summary")
    if summary is not None:
        updates["_summary"] = summary
    return updates


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: CapabilityRegistry | None = None


def get_registry() -> CapabilityRegistry:
    global _registry
    if _registry is None:
        _registry = create_registry()
    return _registry
