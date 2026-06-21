# Phase 4: Guided Workflow Operability - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the Claude-native workflow experience dependable — state-aware help, governed ingestion, progress/resume tracking, and trustworthy graph health outputs. Users can run, resume, and understand workflows with dependable next-step guidance and observable progress.

**Requirements:** WF-01, WF-02, WF-03, WF-04, ING-01, ING-05, RT-04

</domain>

<decisions>
## Implementation Decisions

### Workflow Runner (RT-04)
- **D-01:** A **Python CLI workflow runner** manages multi-step workflow execution. `construct workflow run <name>` executes steps, persists progress state, and supports resuming mid-workflow (e.g., curation cycle step 4/7).
- **D-02:** Workflow progress is recorded to a structured workflow-state file (not just event log). The state file is consumed by the workflow runner for resume and by the help system for status reporting.

### Ingestion Flow (ING-01)
- **D-03:** A **unified ingestion pipeline** handles all source types: files, notes, URLs, and web research. Single `construct ingest <source>` CLI command that routes all source types through the same governed flow (metadata capture, domain routing, ref creation, seed card creation).
- **D-04:** The ingestion flow is: capture source → detect type → classify domain → create ref record → generate seed card → log event. Each step is deterministic and can be re-run.

### Resume Behavior (WF-03)
- **D-05:** **Workflow resume only** — resume mid-workflow when interrupted (e.g., curation was on step 4, pick up there). No session-level context persistence (discussion history, suggestions made, etc.). The workflow runner's state file is the resume mechanism.
- **D-06:** Cross-session workflow state persistence is included: if a workflow was in progress when the session ended, the runner can resume it in a new session.

### Help Architecture (WF-01)
- **D-07:** The help system becomes a **Python CLI command** (`construct help --suggest`) that returns structured JSON with workspace health, priorities, and action suggestions. The agent renders this as natural language to the user.
- **D-08:** The command consumes data from the capability registry (graph.status, workspace.validate) and the workflow runner (active workflow state). It does not scan files directly.

### Skill Migration Priority
- **D-09:** Phase 4 migrates 5 skills from Claude-native inline file ops to Python CLI/MCP invocation:
  1. `construct-graph-status` — already has Python `graph_status()` handler
  2. `construct-curation-cycle` — most-used skill, integrity/decay/promote/connect
  3. `construct-research-cycle` — most complex, web search + extraction + ref creation
  4. `construct-card-evaluate` — promotion/decay lifecycle assessment logic
  5. `construct-gap-analysis` — graph-powered gap computation

### the Agent's Discretion
- Exact CLI flag design for `construct workflow run` and `construct ingest`
- Workflow state file format and location
- How the ingestion pipeline detects source type (file extension, URL pattern, stdin)
- Order of skill migration within the phase (wave planning)
- `construct help --suggest` output schema details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 4 goal, success criteria (WF-01/02/03/04, ING-01/05, RT-04), dependency on Phase 3.
- `.planning/REQUIREMENTS.md` — Full requirement descriptions for WF-01 through WF-04, ING-01, ING-05, RT-04.
- `.planning/PROJECT.md` — Product continuity, compatibility constraints.
- `.planning/STATE.md` — Current progress, prior phase decisions, deferred items.
- `.planning/phases/03-capability-registry-cli-mcp-spine/03-CONTEXT.md` — Prior D-01 through D-12, especially the capability registry pattern and MCP server.
- `.planning/phases/02-governed-knowledge-operations/02-CONTEXT.md` — Prior D-01 through D-15 including Python enforcement model, skill-as-wrapper pattern.

### Active workflow documents
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` — Current daily cycle workflow (research → curation → graph-status → user interaction).
- `CONSTRUCT-CLAUDE-impl/construct/workflows/cold-start.md` — First-use workspace initialization workflow.
- `CONSTRUCT-CLAUDE-impl/construct/workflows/co-authorship.md` — Synthesis and drafting workflow.

### Skills targeted for migration
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-graph-status/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-gap-analysis/SKILL.md`

### Help and ingestion existing state
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-help/SKILL.md` — Current help skill (agent-inline file scanning).

### Existing implementation
- `src/construct/pipelines/graph_status.py` — Existing `graph_status()` PIPE handler returning structured OperationResult.
- `src/construct/services/knowledge.py` — `create_card`, `route_source_to_domain`, `add_connection` — existing operations the ingestion pipeline and workflow runner call.
- `src/construct/capabilities/registry.py` — `CapabilityRegistry` — dispatch engine for workflow steps.
- `src/construct/capabilities/catalog.py` — Pre-registered capabilities including `graph.status`, `workspace.validate`.
- `src/construct/cli.py` — Existing CLI with `init`/`validate`/`status`/`knowledge` commands — pattern for new `workflow` and `ingest` commands.
- `src/construct/mcp/server.py` — MCP server with auto-registered tools.

### Active skill procedures (not yet migrated)
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-edit/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-archive/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-domain-init/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-search-adjust/SKILL.md`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-bridge-detect/SKILL.md`

### Architecture decisions
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Four-layer architecture, CLI→MCP→HTTP path, capability registry.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/pipelines/graph_status.py` — `graph_status()` returns structured OperationResult with card/connection/domain counts. Can be consumed by help --suggest and graph status skill.
- `src/construct/services/knowledge.py` — `create_card()`, `route_source_to_domain()` — core operations for ingestion pipeline.
- `src/construct/capabilities/registry.py` — `CapabilityRegistry.get()` — dispatch engine for workflow runner.
- `src/construct/cli.py` — Typer app with command group pattern (`app.add_typer()`) for adding `workflow` and `ingest` command groups.
- `tests/unit/test_graph_status.py` — Test patterns for PIPE handlers.

### Established Patterns
- CLI commands delegate to capability registry (`registry.get("id").handler(...)`)
- Skills are markdown procedures — migrated skills become thin wrappers calling Python CLI/MCP
- `OperationResult` is the standard structured response type (success + message + errors + data)
- Pre-write validation gates on all canonical artifacts
- Event logging append-only to `log/events.jsonl`

### Integration Points
- New `src/construct/pipelines/workflow_runner.py` — workflow state machine
- New `src/construct/pipelines/ingestion.py` — unified ingestion handler
- New `src/construct/services/help.py` — workspace state analysis for `construct help --suggest`
- `src/construct/cli.py` — add `workflow` and `ingest` Typer command groups
- `src/construct/capabilities/catalog.py` — register new capabilities (workflow.run, ingest.source, help.suggest)
- `CONSTRUCT-CLAUDE-impl/claude/skills/` — migrate 5 skill files to call CLI/MCP
- `log/workflow-state.json` — new state file for workflow progress persistence

</code_context>

<specifics>
## Specific Ideas

- `construct workflow run <name>` should support `--step N` to start from a specific step
- The unified ingestion pipeline should auto-detect source type: `.pdf` → file, `http(s)://` → URL, plain text → note
- Help suggestions should follow the same priority ordering as the current `construct-help` skill (workspace exists → empty → not configured → no connections → stale research → pending items → healthy)
- Skill migration should update `allowed-tools` in frontmatter to replace `Bash(python3 *)` with `MCP(connect)` or `Bash(construct *)` as appropriate

</specifics>

<deferred>
## Deferred Ideas

- Cross-session context persistence (discussion history, conversation state) — not in scope for Phase 4 per D-05.
- Full migration of remaining ~10 skills (card-create, domain-init, etc.) — beyond the 5 scoped in D-09.
- Streamlit ops UI spike — Phase 6.
- LangGraph L2 `ask.domain` capability — Phase 5.

</deferred>

---

*Phase: 04-guided-workflow-operability*
*Context gathered: 2026-06-10*
