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

# ── Ask Domain imports (Phase 5) ──
from construct.llm.ask_domain import (
    AskDomainInput,
    AskDomainOutput,
    run_gate as ask_domain_gate,
)

# ── Bridge Detection imports (Phase 5) ──
from construct.pipelines.bridge_detect import bridge_detect


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
    workspace: Path


class WorkflowRunInput(BaseModel):
    workspace: Path
    workflow_name: str = "workflow"
    start_step: int = 0


class IngestSourceInput(BaseModel):
    workspace: Path
    source: str
    domain_hint: str | None = None
    author: str = "construct"


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
        handler=validate_workspace,
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
        handler=create_card,
        cli_name="knowledge.card.create",
        mcp_tool_name="construct_create_card",
    ))
    registry.register(CapabilityRecord(
        id="knowledge.card.edit",
        name="Edit Card",
        description="Edit an existing knowledge card",
        input_model=CardEditInput,
        output_model=OperationResult,
        handler=edit_card,
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
        handler=add_connection,
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
        handler=lambda **kwargs: OperationResult(success=False, message="Not yet implemented — see Plan 02"),
        mcp_tool_name="construct_graph_status",
    ))
    registry.register(CapabilityRecord(
        id="views.generate_data",
        name="Generate Views Data",
        description="Generate JSON view data from workspace state",
        input_model=ViewsGenerateDataInput,
        output_model=OperationResult,
        handler=lambda **kwargs: OperationResult(success=False, message="Not yet implemented — see Plan 02"),
        mcp_tool_name="construct_views_generate_data",
    ))
    registry.register(CapabilityRecord(
        id="workflow.run",
        name="Run Workflow",
        description="Execute a multi-step workflow with state persistence",
        input_model=WorkflowRunInput,
        output_model=OperationResult,
        handler=lambda workspace, workflow_name="workflow", start_step=0: (
            lambda w, name, step: WorkflowRunner(w).run(
                _get_workflow_steps(name), workflow_name=name, start_step=step
            )
        )(workspace, workflow_name, start_step),
        cli_name="workflow.run",
        mcp_tool_name="construct_workflow_run",
    ))
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
        handler=ingest_source,
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

    return registry


def _get_workflow_steps(name: str) -> list:
    """Get step definitions for a named workflow procedure."""
    from construct.pipelines.workflow_runner import WorkflowStep
    from construct.services.knowledge import OperationResult

    if name == "curation-cycle":
        return [
            WorkflowStep(name="integrity-check", description="Validate card integrity", handler=lambda **kw: OperationResult(success=True, message="Integrity check placeholder — see skill migration"), handler_kwargs={}),
            WorkflowStep(name="decay-scan", description="Check for stale cards", handler=lambda **kw: OperationResult(success=True, message="Decay scan placeholder")),
            WorkflowStep(name="orphan-scan", description="Detect orphan cards", handler=lambda **kw: OperationResult(success=True, message="Orphan scan placeholder")),
            WorkflowStep(name="promotion-scan", description="Evaluate cards for lifecycle promotion", handler=lambda **kw: OperationResult(success=True, message="Promotion scan placeholder")),
            WorkflowStep(name="connection-maint", description="Type untyped edges and detect bridges", handler=lambda **kw: OperationResult(success=True, message="Connection maintenance placeholder")),
            WorkflowStep(name="process-inbox", description="Process pending user actions", handler=lambda **kw: OperationResult(success=True, message="Inbox processing placeholder")),
            WorkflowStep(name="report", description="Compile stats and health report", handler=lambda **kw: OperationResult(success=True, message="Report placeholder")),
        ]
    # Default: single-step placeholder
    return [WorkflowStep(name="single-step", description="Single step", handler=lambda **kw: OperationResult(success=True, message=f"Workflow '{name}' executed (placeholder)"), handler_kwargs={})]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: CapabilityRegistry | None = None


def get_registry() -> CapabilityRegistry:
    global _registry
    if _registry is None:
        _registry = create_registry()
    return _registry
