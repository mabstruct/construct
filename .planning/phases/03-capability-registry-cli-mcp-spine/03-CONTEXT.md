# Phase 3: Capability Registry, CLI & MCP Spine - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the shared capability registry that powers both CLI and MCP surfaces with one contract. Core deterministic capabilities run through one shared contract surface that both maintainers and Claude-native workflows can trust.

**Requirements:** RT-01, RT-02, RT-03

</domain>

<decisions>
## Implementation Decisions

### Registry Implementation Pattern
- **D-01:** The capability registry uses a **Pydantic-based model** for capability definitions. Each capability record bundles id, input/output schema (as Pydantic model references), a direct callable handler reference, CLI command name, and MCP tool name.
- **D-02:** Input/output schemas reference **existing Pydantic models directly** (e.g., `ValidationReport`, `KnowledgeCard`) rather than standalone JSON Schema dicts. JSON Schema is auto-derived via `model_json_schema()` for MCP tool contracts. One source of truth.
- **D-03:** Handler dispatch uses **direct callable references** stored in the capability record — not module-path strings. Calling a capability is `cap.handler(**inputs)`.

### Capability Scope
- **D-04:** Phase 3 registers **all existing CLI commands + the 3 new tranche-1 PIPE capabilities**: `workspace.validate`, `graph.status`, `views.generate_data`, plus existing `init`, `validate`, `status`, `knowledge` (card/connection CRUD operations). Maximum coverage from the start.

### CLI Migration Approach
- **D-05:** Existing direct commands (`construct validate`, `construct status`, `construct knowledge *`) **stay at their current paths** but internally delegate to the capability registry for dispatch. No separate `construct run` namespace — the registry IS the dispatch engine.
- **D-06:** The existing `construct validate` command becomes one of the registered capabilities in the registry. CLI commands become thin adapters: parse CLI args → look up capability → call handler → render output.

### First Migrated Skill (MCP Proof)
- **D-07:** `construct-workspace-validate` is the **first skill migrated to call MCP**. Skill becomes: user says "validate workspace" → skill invokes MCP `construct_validate` tool → shows structured results. Simple PIPE capability with no LLM dependency — clean proof of the agentic MCP path.
- **D-08:** The MCP tool should accept the same inputs and return the same structured outputs as the CLI command (shared via capability registry contract).

### MCP Server
- **D-09:** MCP server at `src/construct/mcp/server.py` uses **stdio transport** (`construct mcp`). Tools are auto-registered from the capability registry — every registered capability with an MCP tool name gets an MCP tool. No manual tool-by-tool wiring.
- **D-10:** `mcp>=1.0` added to `pyproject.toml` dependencies.

### test-ws/ Fixtures
- **D-11:** Create `test-ws/my-construct/` and `test-ws/ping-eon/` as part of this phase. These are real CONSTRUCT workspaces used by contract tests to prove CLI commands work. Created from templates with enough cards, connections, and domains to exercise validate, graph-status, knowledge ops, and views-generate-data.
- **D-12:** Test suite now includes contract tests at `tests/contract/` that run against `test-ws/` fixtures.

### the agent's Discretion
- Exact Pydantic model fields for `CapabilityRecord` in the registry.
- How `test-ws/` fixtures are populated (manual or via `construct init` + seed scripts).
- MCP tool error format details as long as they match the CLI error contract.
- Migration of existing skill wrappers beyond `construct-workspace-validate` (deferred to Phase 4).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria (RT-01/02/03), dependency on Phase 2.
- `.planning/REQUIREMENTS.md` — RT-01 (capability registry), RT-02 (CLI surface), RT-03 (MCP tools).
- `.planning/PROJECT.md` — Product continuity, sequencing constraints.
- `.planning/phases/02-governed-knowledge-operations/02-CONTEXT.md` — Prior D-01 through D-15 including Python enforcement model, `construct knowledge` namespace, source routing decisions.
- `.planning/codebase/CONCERNS.md` — Dual runtime, missing `test-ws/` fixtures, v0.3 deps not in pyproject.toml, no contract tests.

### Architecture decisions
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Four-layer architecture, CLI→MCP→HTTP path, capability registry, LangGraph L2 gates, Streamlit spike. **MUST read §A.1 (invoke surfaces), repository mapping table, migration pattern.**
- `CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md` — Locked tranche 1 scope: capability registry (deliverable 1), CLI commands (deliverable 2), MCP stdio (deliverable 3), capability table with IDs, CLI names, MCP tool names.

### Existing implementation
- `src/construct/cli.py` — Current Typer CLI with `init`, `validate`, `status`, `knowledge` command groups. These will delegate to the registry.
- `src/construct/services/knowledge.py` — Existing knowledge operations (card CRUD, connection CRUD) that will be registered as capabilities.
- `src/construct/services/validation.py` — Existing `validate_workspace()` that will be the handler for `workspace.validate` capability.
- `src/construct/schemas/workspace.py` — WorkspaceScaffold, ConnectionRecord. Source for auto-derived JSON Schema.
- `src/construct/schemas/card.py` — KnowledgeCard model. Source for card-related capability schemas.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md` — First skill to migrate to MCP invocation.
- `pyproject.toml` — Needs `mcp>=1.0` added to dependencies.

### Fixtures
- `test-ws/my-construct/` — To be created (primary test workspace).
- `test-ws/ping-eon/` — To be created (smaller fixture).
- `tests/contract/` — To be created (contract test directory).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/cli.py` — Full Typer CLI with 6+ commands across 3 groups. The `_display_result` pattern with structured `OperationResult` is the standard CLI response format.
- `src/construct/services/validation.py` — `validate_workspace()` returns `ValidationReport` with typed errors/warnings. This is the handler for `workspace.validate`.
- `src/construct/services/knowledge.py` — `create_card`, `edit_card`, `archive_card`, `add_connection`, `remove_connection`, `list_connection` — all return `OperationResult`. These are the handlers for `knowledge.*` capabilities.
- `src/construct/schemas/` — Pydantic models for all workspace artifacts. Can derive JSON Schema via `model_json_schema()`.
- `CONSTRUCT-CLAUDE-impl/construct/templates/` — Template files for workspace creation. `setup-construct.sh` deploys these.

### Established Patterns
- CLI commands use Typer with Pydantic-backed validation (Phase 1/2 pattern).
- `OperationResult` is the standard structured response type (success + message + errors + data).
- Skills are thin wrappers calling Python CLI (Phase 2 migration pattern).
- Workspace files are the only source of truth.
- Pre-write validation gates established in Phase 1 (D-05).

### Integration Points
- New `src/construct/capabilities/` directory — capability registry module.
- New `src/construct/mcp/server.py` — MCP stdio server, tools registered from capability registry.
- `src/construct/cli.py` — existing commands refactored to delegate to capability registry.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md` — edited to call MCP `construct_validate` tool.
- `test-ws/` — new fixture workspaces for contract tests.
- `pyproject.toml` — add `mcp>=1.0`.

</code_context>

<specifics>
## Specific Ideas

- Registry should be simple enough that adding a new capability is one file edit: define the Pydantic input/output models, write the handler function, register in the capability catalog.
- The registry should be importable and queryable — `registry.get("workspace.validate")` returns the capability record with handler, schemas, CLI name, MCP tool name.
- Direct CLI commands become registry-aware: `construct validate` internally calls `registry.get("workspace.validate").handler(path)`.
- MCP server starts the same way: iterate `registry.list_mcp_tools()`, register each as an MCP tool, dispatch incoming tool calls to `cap.handler(**arguments)`.
- Use existing `OperationResult` and `ValidationReport` as capability output schemas — no need to invent new response types.

</specifics>

<deferred>
## Deferred Ideas

- LangGraph L2 `ask.domain` capability — Phase 5 (requires Phase 3's registry pattern).
- Workflow runner skeleton (`workflow.daily_cycle`) — Phase 4.
- Streamlit ops UI spike — Phase 6 (or later in v0.3).
- Full skill migration beyond `construct-workspace-validate` — Phase 4.
- `construct run <capability>` namespace — not needed per D-05 (direct commands delegate to registry).

</deferred>

---

*Phase: 03-capability-registry-cli-mcp-spine*
*Context gathered: 2026-06-10*
