"""Pre-registered catalog of all CONSTRUCT capabilities."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

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
    list_cards,
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
#
# D-06: every model below sets ``extra="forbid"``. The seam validates a payload
# against the declared model before dispatch (GOV-01), so a model that forbids
# nothing is a seam that enforces nothing — it would type-check the declared
# fields and then hand the handler whatever else the caller sent.
# ``tests/contract/test_capability_seam.py`` holds this as a cardinality guard:
# the number of forbidding models must equal the registry size, so a capability
# cannot be added unguarded.


class WorkspacePathInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path


class WorkspaceInitInput(BaseModel):
    """Input for ``workspace.init`` — describes ``initialize_workspace``.

    ``WorkspacePathInput`` declared a single ``path`` and was therefore a
    contract for a call nobody could make: the service takes ``root`` and a
    ``domain``. T-18-13: ``domain`` is the *typed* ``DomainInitInput``, not an
    open dict, so its own shape is enforced at the boundary before any directory
    is created.
    """

    model_config = ConfigDict(extra="forbid")

    root: Path
    domain: DomainInitInput


class CardCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict(extra="forbid")

    card_id: str
    workspace: Path
    title: str | None = None
    confidence: int | None = Field(None, ge=1, le=5)
    source_tier: int | None = Field(None, ge=1, le=5)
    lifecycle: str | None = None
    summary: str | None = None
    author: str = "curator"


class CardArchiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    workspace: Path
    author: str = "curator"


class ConnectionAddInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_id: str
    to_id: str
    conn_type: str
    note: str | None = None
    workspace: Path
    created_by: str = "construct"


class ConnectionRemoveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_id: str
    to_id: str
    conn_type: str
    workspace: Path


class ConnectionListInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace: Path
    card_id: str | None = None
    include_archived: bool = False


class CardListInput(BaseModel):
    # ASVS V5 (T-16-09): reject unexpected MCP payload fields at the boundary.
    # Set explicitly — this is not inherited from a module-level config.
    model_config = {"extra": "forbid"}

    workspace: Path
    domain: str | None = None
    include_archived: bool = False


class GraphStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace: Path


class ViewsGenerateDataInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # D-05: the contract is install-root scoped, not workspace scoped.
    # ``discover_workspaces`` scans only the *children* of its argument, so
    # handing it a single workspace discovers zero workspaces and silently
    # emits empty views.
    install_root: Path


class ViewsValidateInput(BaseModel):
    """Input for ``views.validate_data`` (D-02).

    ``install_root``, spelled exactly as ``ViewsGenerateDataInput`` spells it, so
    the two views capabilities present one vocabulary to an agent reading the
    tool list. Same reason the generate side is install-root scoped rather than
    workspace scoped: the validator walks the *children* of the data directory
    the generator wrote.
    """

    model_config = ConfigDict(extra="forbid")

    install_root: Path


class WorkflowRunInput(BaseModel):
    # Retained per plan 18-02. A grep at the time of that change found no
    # remaining consumer: ``workflow.run`` was removed by D-10/CUR-05, and
    # ``workflow.status`` moved to ``WorkflowStatusInput`` below because this
    # model's ``workflow_name`` / ``start_step`` are fields its single-parameter
    # runner lambda cannot receive.
    model_config = ConfigDict(extra="forbid")

    workspace: Path
    workflow_name: str = "workflow"
    start_step: int = 0


class WorkflowStatusInput(BaseModel):
    """Input for ``workflow.status`` — one workspace, which is all its handler takes."""

    model_config = ConfigDict(extra="forbid")

    workspace: Path


class IngestSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict(extra="forbid")

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
        input_model=WorkspaceInitInput,
        output_model=type(None),
        # 18-02 adapter: the seam dumps nested models, so the shim rebuilds the
        # DomainInitInput dataclass before calling initialize_workspace.
        handler=_workspace_init_shim,
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
        # 18-02 adapter: map schema workspace → archive_card's workspace_root,
        # coerce the author enum. Dual-mode until plan 18-03 normalizes cli.py.
        handler=_archive_card_shim,
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
        # 18-02 adapter: map schema workspace → remove_connection's
        # workspace_root, coerce conn_type. Dual-mode until plan 18-03.
        handler=_remove_connection_shim,
        cli_name="knowledge.connection.remove",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.connection.list",
        name="List Connections",
        description="List typed connections, optionally filtered by card",
        input_model=ConnectionListInput,
        output_model=OperationResult,
        # 18-02 adapter: map schema workspace → list_connections's
        # workspace_root. Dual-mode until plan 18-03 normalizes cli.py.
        handler=_list_connections_shim,
        cli_name="knowledge.connection.list",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.card.list",
        name="List Cards",
        description="List cards, optionally filtered by domain or lifecycle",
        input_model=CardListInput,
        output_model=OperationResult,
        handler=list_cards,
        cli_name="knowledge.card.list",
        mcp_tool_name="construct_list_cards",
    ))
    registry.register(CapabilityRecord(
        id="graph.status",
        name="Graph Status",
        description="Produce graph health report for a workspace",
        input_model=GraphStatusInput,
        output_model=OperationResult,
        # ING-05 wired the real graph_status() report behind a lambda deliberately
        # shaped to bind BOTH a positional and a keyword caller, because
        # services/help.py called it positionally. 18-03 put that caller on the
        # seam, so the accommodation is gone: keyword-only, like every sibling.
        handler=_graph_status_handler,
        mcp_tool_name="construct_graph_status",
    ))
    registry.register(CapabilityRecord(
        id="views.generate_data",
        name="Generate Views Data",
        description="Generate JSON view data from workspace state",
        input_model=ViewsGenerateDataInput,
        output_model=OperationResult,
        # V41-01 / FIX-01 (D-01): the permanent-failure placeholder is replaced
        # by a real call into construct.views.generate.generate().
        #
        # The registry-holdout note that stood here is retired by 18-03 / D-02:
        # the views group is no longer a holdout, because `views validate` is the
        # record below rather than a hand-written command body. What remains true
        # of *this* record is narrower and is stated as itself: per D-03 the
        # `construct views generate` CLI command still reaches generate() by an
        # independent path, so the generate side keeps two paths where the
        # validate side now has one. Closing that is a later decision, not an
        # oversight (adr-0005).
        handler=_views_generate_handler,
        mcp_tool_name="construct_views_generate_data",
    ))
    registry.register(CapabilityRecord(
        id="views.validate_data",
        name="Validate Views Data",
        description=(
            "Validate the generated views JSON data files against their contract "
            "models and report per-file pass/fail (read-only; writes nothing)"
        ),
        input_model=ViewsValidateInput,
        output_model=OperationResult,
        # D-02: the last hand-written command group joins the registry. Both
        # names are set, so CLI and MCP reach it by the one path — and Phase 19's
        # generated HTTP adapter inherits it without a code change.
        handler=_views_validate_handler,
        cli_name="views.validate_data",
        mcp_tool_name="construct_views_validate_data",
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
        input_model=WorkflowStatusInput,
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

    A **named single parameter**. It used to be described here as binding both
    the positional and the keyword call form "like the ``graph.status`` lambda";
    that lambda is gone (18-03 made ``graph.status`` keyword-only once its one
    positional caller moved onto the seam). No caller reaches this handler
    positionally either — the seam always dispatches ``handler(**model_dump())``.

    D-04 splits the report's two failure channels: validation errors are fatal
    and become ``OperationResult.errors``; content warnings are advisory and
    never make ``success`` False. The message names both counts separately so
    the two are not confused at a glance.

    Like every sibling shim in this module the handler NEVER raises: the MCP
    surface must not receive raw exception text (which carries filesystem paths)
    and the CLI must not traceback. Both the install-root guard and the generator
    call are therefore reduced to an ``OperationResult`` naming only the
    exception class.
    """
    # Deferred import — matches the convention for heavy views imports.
    from construct.views.generate import generate, install_root_error

    # CR-03: validate before the generator touches the filesystem. This
    # ``install_root`` is agent-supplied over MCP, and generate() creates
    # views/build/data/ under whatever it is handed.
    guard = install_root_error(install_root)
    if guard is not None:
        return OperationResult(
            success=False,
            message=f"views.generate_data refused the install root: {guard}",
            errors=[OperationError(field="views.install_root", reason=guard, suggestion="")],
            data={"failed": True},
        )

    try:
        report = generate(Path(install_root))
    except Exception as exc:  # noqa: BLE001 — surface parity with the sibling shims
        reason = type(exc).__name__
        return OperationResult(
            success=False,
            message=f"views.generate_data failed: {reason}",
            errors=[OperationError(field="views.generate", reason=reason, suggestion="")],
            data={"failed": True},
        )

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


def _views_validate_handler(*, install_root) -> OperationResult:
    """D-02: run the views contract validator and report it.

    Keyword-only, like every other handler the seam reaches. The heavy lifting —
    including the install-root guard — lives in
    ``construct.views.generate.validate_build_data``; this wraps its report in an
    ``OperationResult`` exactly as ``_views_generate_handler`` wraps the
    generator's, so the two views capabilities answer in one shape.

    Like every sibling shim it NEVER raises: the MCP surface must not receive raw
    exception text (which carries filesystem paths) and the CLI must not
    traceback. Both failure channels reduce to an ``OperationResult`` naming only
    a field-and-constraint reason or an exception class.

    The two pre-file failures are kept distinguishable in ``data`` because the
    CLI renders them differently — the install-root refusal is surfaced verbatim
    (it carries no path by construction), while the missing-data-directory case
    lets the *local* caller append the path itself, which is the convention
    ``install_root_error`` documents.
    """
    # Deferred import — matches the convention for heavy views imports.
    from construct.views.generate import validate_build_data

    try:
        report = validate_build_data(install_root)
    except Exception as exc:  # noqa: BLE001 — surface parity with the sibling shims
        reason = type(exc).__name__
        return OperationResult(
            success=False,
            message=f"views.validate_data failed: {reason}",
            errors=[OperationError(field="views.validate", reason=reason, suggestion="")],
            data={"failed": True},
        )

    if report.guard_error is not None:
        return OperationResult(
            success=False,
            message=f"views.validate_data refused the install root: {report.guard_error}",
            errors=[
                OperationError(
                    field="views.install_root", reason=report.guard_error, suggestion=""
                )
            ],
            data={"failed": True},
        )

    if report.missing_data_dir:
        reason = "no views data directory under the install root"
        return OperationResult(
            success=False,
            message=f"views.validate_data found nothing to validate: {reason}",
            errors=[
                OperationError(
                    field="views.data_dir",
                    reason=reason,
                    suggestion="Run `construct views generate` first.",
                )
            ],
            data={"results": [], "all_passed": False, "missing_data_dir": True},
        )

    passed = sum(1 for entry in report.results if entry["status"] == "pass")
    failed = sum(1 for entry in report.results if entry["status"] == "fail")
    missing = sum(1 for entry in report.results if entry["status"] == "missing")

    return OperationResult(
        success=report.all_passed,
        message=(
            f"Views data validation: {passed} passed, {failed} failed, "
            f"{missing} missing"
        ),
        errors=[
            OperationError(field=entry["file"], reason="; ".join(entry["errors"]), suggestion="")
            for entry in report.results
            if entry["status"] == "fail"
        ],
        data={
            "results": report.results,
            "all_passed": report.all_passed,
            "missing_data_dir": False,
        },
    )


def _graph_status_handler(*, workspace: str | Path) -> OperationResult:
    """Handler for graph.status — keyword-only, by design.

    The record used to carry ``lambda workspace: graph_status(workspace)``, whose
    single named parameter bound a positional caller as readily as a keyword one.
    That was an accommodation for ``services/help.py``'s positional
    capability-to-capability call, and it is exactly the second dispatch path
    GOV-01 exists to remove. Declaring the parameter keyword-only makes a
    positional call a ``TypeError`` rather than a silent success.
    """
    return graph_status(workspace)


def _validate_shim(*, path: Path | str) -> ValidationReport:
    """Marshalling adapter for workspace.validate.

    ``WorkspacePathInput.path`` → ``validate_workspace(root)``. The positional
    branch that also accepted ``handler(path)`` is retired: plan 18-03 put every
    ``cli.py`` command on the seam, so no caller passes positionally any more.
    """
    return validate_workspace(path)


def _research_search_shim(**kwargs):
    """Marshalling adapter for research.search.

    Re-hydrates ``ResearchSearchInput`` from the seam's ``model_dump()``. The
    positional branch — which invented a two-argument ``(workspace, query)`` call
    form no caller in the repository ever used — is retired.
    """
    return research_search(ResearchSearchInput(**kwargs))


def _research_score_shim(**kwargs):
    """RT-03 adapter for research.score."""
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
        # GOV-05: the run's own status rides on the envelope so a surface can
        # report HOW IT WENT without re-deriving it from ``data``. The success
        # flag's computation above is deliberately untouched — it drives the exit
        # code and D-15 holds it fixed.
        outcome=result.status,
    )


def _research_run_shim(**kwargs):
    """RT-03 adapter for research.run (run-start; pauses at the human gate)."""
    return _run_result_to_operation(
        "research.run", lambda: run_research_run(ResearchRunInput(**kwargs))
    )


def _research_review_shim(**kwargs):
    """RT-03 adapter for research.review (resume with per-finding decisions)."""
    return _run_result_to_operation(
        "research.review", lambda: review_research_run(ReviewInput(**kwargs))
    )


def _research_inspect_shim(**kwargs):
    """RT-03 adapter for research.inspect (read-only get_state; never resumes)."""
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
        # GOV-05 — see ``_run_result_to_operation``. A degraded curation run is a
        # successful invocation (exit 0, D-15) of a run that did not fully
        # succeed; ``outcome`` is where the second half of that gets said.
        outcome=result.status,
    )


def _curation_run_shim(**kwargs):
    """RT-03 adapter for curation.run (deterministic findings-only cycle)."""
    return _curation_result_to_operation(
        "curation.run", lambda: run_curation_run(CurationRunInput(**kwargs))
    )


def _curation_inspect_shim(**kwargs):
    """RT-03 adapter for curation.inspect (read-only get_state; never re-runs)."""
    return _curation_result_to_operation(
        "curation.inspect", lambda: inspect_curation_run(CurationInspectInput(**kwargs))
    )


def _curation_review_shim(**kwargs):
    """RT-03 adapter for curation.review (resume a paused run with per-item
    decisions; applies approved lifecycle/connection/archive writes)."""
    return _curation_result_to_operation(
        "curation.review", lambda: review_curation_run(CurationReviewInput(**kwargs))
    )


def _card_evaluate_shim(**kwargs):
    """RT-03 adapter for card.evaluate (L3 promotion gate; read-only, no writes).

    Mirrors ``_research_score_shim``'s error discipline (T-12-04 / WR-06): a total
    provider outage → ``success=False`` carrying only ``degraded``/``total_outage``
    flags (never raw provider text); any other exception → a key-safe sanitized
    message via the gate module's ``_safe_scoring_cause`` (never raw ``str(exc)``).
    """
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
        # GOV-05 — see ``_run_result_to_operation``. The daily cycle degrades on
        # any pending escalation, so this is the adapter where a "nothing was
        # written" outcome most often needs to survive to a surface.
        outcome=result.status,
    )


def _daily_run_shim(**kwargs):
    """Keyword-only adapter for daily.run (thin research→curation→graph cycle)."""
    return _daily_result_to_operation(
        "daily.run", lambda: run_daily_run(DailyRunInput(**kwargs))
    )


def _daily_inspect_shim(**kwargs):
    """Keyword-only adapter for daily.inspect (read a receipt; never re-runs)."""
    return _daily_result_to_operation(
        "daily.inspect", lambda: inspect_daily_run(DailyInspectInput(**kwargs))
    )


def _create_card_shim(**kwargs):
    """Marshalling adapter for knowledge.card.create.

    Schema fields (workspace, title, epistemic_type, …) are marshalled into the
    ``card_data`` dict ``create_card`` takes. The positional branch, which let a
    caller hand over an already-marshalled ``card_data``, is retired — ``cli.py``
    now sends the declared fields and this is the only marshaller.
    """
    return create_card(
        kwargs["workspace"],
        _build_card_data(kwargs),
        author=CardAuthor(kwargs.get("author", "construct")),
    )


def _edit_card_shim(**kwargs):
    """Marshalling adapter for knowledge.card.edit.

    Provided non-None schema fields are marshalled into an ``updates`` dict. The
    ``is not None`` filter in ``_build_card_updates`` is the T-18-15 guard: the
    seam dispatches ``handler(**model.model_dump())`` and ``model_dump()``
    materialises a default for every declared field, so forwarding them verbatim
    would blank a field the caller never named. The positional branch is retired.
    """
    return edit_card(
        kwargs["workspace"],
        kwargs["card_id"],
        _build_card_updates(kwargs),
        author=CardAuthor(kwargs.get("author", "curator")),
    )


def _add_connection_shim(**kwargs):
    """Marshalling adapter for knowledge.connection.add.

    ``workspace`` maps to ``add_connection``'s ``workspace_root``; ``conn_type``
    and ``created_by`` are coerced to their enums. The positional branch, which
    accepted an already-coerced ``ConnectionType`` from ``cli.py``, is retired.
    """
    return add_connection(
        kwargs["workspace"],
        kwargs["from_id"],
        kwargs["to_id"],
        ConnectionType(kwargs["conn_type"]),
        note=kwargs.get("note"),
        created_by=ConnectionAuthor(kwargs.get("created_by", "construct")),
    )


def _workspace_init_shim(root: str | Path, domain: DomainInitInput | dict) -> Path:
    """18-02 adapter for workspace.init.

    ``initialize_workspace`` takes ``root`` and a ``DomainInitInput`` dataclass,
    while the seam dispatches ``handler(**model.model_dump())`` — and
    ``model_dump()`` flattens a nested model into a plain dict. The dict is
    already *validated* (``WorkspaceInitInput.domain`` is typed), so rebuilding
    the dataclass here is a re-hydration, not a second validation.

    Named parameters rather than ``*args``/``**kwargs``, so the binding audit in
    ``tests/contract/test_capability_seam.py`` can still see this handler's
    shape; they bind the positional and the keyword call form alike.
    """
    if isinstance(domain, dict):
        domain = DomainInitInput(**domain)
    return initialize_workspace(root, domain)


def _archive_card_shim(
    *,
    workspace: str | Path,
    card_id: str,
    author: str | CardAuthor = "curator",
) -> OperationResult:
    """Marshalling adapter for knowledge.card.archive.

    ``workspace`` maps to ``archive_card``'s ``workspace_root`` and ``author`` is
    coerced to its enum. The positional branch plan 18-02 added to keep the CLI
    alive is retired now that ``cli.py`` dispatches through the seam (research
    Finding G5's ordering constraint, discharged).
    """
    return archive_card(workspace, card_id, author=CardAuthor(author))


def _list_connections_shim(
    *,
    workspace: str | Path,
    card_id: str | None = None,
    include_archived: bool = False,
) -> OperationResult:
    """Marshalling adapter for knowledge.connection.list.

    ``workspace`` maps to ``list_connections``'s ``workspace_root``. The
    positional branch is retired.
    """
    return list_connections(
        workspace, card_id=card_id, include_archived=include_archived
    )


def _remove_connection_shim(
    *,
    workspace: str | Path,
    from_id: str,
    to_id: str,
    conn_type: str | ConnectionType,
) -> OperationResult:
    """Marshalling adapter for knowledge.connection.remove.

    ``workspace`` maps to ``remove_connection``'s ``workspace_root`` and
    ``conn_type`` is coerced to its enum, mirroring ``_add_connection_shim``. The
    positional branch is retired.
    """
    return remove_connection(workspace, from_id, to_id, ConnectionType(conn_type))


def _ingest_source_shim(**kwargs):
    """Marshalling adapter for ingest.source.

    ``IngestSourceInput.workspace`` maps to ``ingest_source``'s
    ``workspace_root`` positional; every remaining field already matches one of
    its keyword parameters by name. The positional branch is retired.
    """
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
