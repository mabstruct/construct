# Phase 4: Guided Workflow Operability — Research

**Date:** 2026-06-10
**Researched by:** planner (inline codebase analysis)

## Key Patterns and Building Blocks

### 1. Capability Registry Architecture (Phase 3 Foundation)

The Phase 3 capability registry (`src/construct/capabilities/registry.py`) provides:

- **`CapabilityRecord`** — dataclass with `id`, `name`, `description`, `input_model` (Pydantic), `output_model` (Pydantic), `handler` (direct callable), `cli_name`, `mcp_tool_name`
- **`CapabilityRegistry`** — singleton backing store with `register()`, `get()`, `list()`, `list_mcp_tools()`, `get_by_mcp_name()`
- **`catalog.py`** — pre-registered capabilities (workspace.*, knowledge.*, graph.status, views.generate_data)
- **`get_registry()`** — module-level singleton getter

**Import for Phase 4:** New capabilities (`workflow.*`, `ingest.source`, `help.suggest`) follow the same pattern: define input/output Pydantic models, register in `create_registry()` with direct handler references.

### 2. CLI Pattern (from `src/construct/cli.py`)

Current Typer structure:

```python
app = typer.Typer(no_args_is_help=True)
knowledge_app = typer.Typer(...)  # for `construct knowledge card` and `construct knowledge connection`
app.add_typer(knowledge_app)
```

Commands delegate to registry:
```python
cap = get_registry().get("workspace.validate")
report = cap.handler(path)
_display_result(result, json_output)  # renders OperationResult
```

**Import for Phase 4:** New command groups (`construct workflow`, `construct ingest`, `construct help`) follow the same `app.add_typer()` pattern. Nesting: `workflow` → `run/status/resume/list` subcommands.

### 3. MCP Server Pattern (from `src/construct/mcp/server.py`)

FastMCP with stdio transport:
```python
app = FastMCP("construct")
registry = get_registry()
for entry in registry.list_mcp_tools():
    cap = registry.get_by_mcp_name(entry["name"])
    # wrap in closure handler, add_tool
app.run(transport="stdio")
```

**Import for Phase 4:** New MCP tools (`construct_workflow_run`, `construct_ingest_source`, `construct_help_suggest`) are auto-registered by setting `mcp_tool_name` in their capability records. No manual MCP wiring.

### 4. OperationResult Response Pattern (from `src/construct/services/knowledge.py`)

```python
@dataclass
class OperationResult:
    success: bool = True
    message: str = ""
    errors: list[OperationError] = field(default_factory=list)
    data: Any = None
```

**Import for Phase 4:** All new handlers (workflow runner, ingestion, help) return `OperationResult`. This is the canonical response type consumed by CLI display and MCP serialization.

### 5. Event Log Pattern (from `src/construct/services/event_log.py`)

```python
def append_event(workspace_root, agent, action, *, target=None, detail=None, result=EventResult.success):
    # Appends JSONL line to log/events.jsonl
    # Non-blocking — OSError prints warning to stderr
```

**Import for Phase 4:** Workflow runner logs `workflow_started`, `workflow_step_complete`, `workflow_complete`, `workflow_resumed` events. Ingestion logs `ingest_source`, `ref_created`, `seed_card_created` events.

### 6. Knowledge Service Available Operations (from `src/construct/services/knowledge.py`)

All return `OperationResult`:
- `create_card(workspace_root, card_data, author)` — used by ingestion pipeline for seed cards
- `route_source_to_domain(workspace_root, source_path, domain_hint)` — used by ingestion pipeline
- `add_connection(workspace_root, from_id, to_id, conn_type, ...)` — potentially used by workflow runner for curation steps

### 7. Graph Status Pipeline (from `src/construct/pipelines/graph_status.py`)

```python
def graph_status(workspace: str | Path) -> OperationResult:
    # Returns card count, lifecycle counts, domain counts, connection counts, type counts
```

**Import for Phase 4:** The help `--suggest` command consumes `graph.status` via the capability registry (as per D-08). This gives workspace health snapshot without scanning files directly.

### 8. Skill-is-a-Markdown-Procedure Pattern

All skills in `CONSTRUCT-CLAUDE-impl/claude/skills/` have:
- YAML frontmatter: `description`, `allowed-tools`
- Structured procedure steps as numbered sections
- Trigger/Agent/Produces metadata block
- Validation checklist at end

**Migration pattern (from Phase 2/3):** Skills become thin wrappers. `allowed-tools` changes from file manipulation tools to `Bash(construct ...)` and `MCP(connect)`. The procedure steps change from "Read files, validate inline" to "Invoke CLI command, display result."

### 9. Existing Workflow Documents

Three workflows at `CONSTRUCT-CLAUDE-impl/construct/workflows/`:
- `daily-cycle.md` — research → curation → graph-status → user interaction
- `cold-start.md` — first-use workspace initialization
- `co-authorship.md` — synthesis and drafting

**Import for Phase 4:** These documents need to be updated to reference migrated skills and provide clear inputs/outputs/outcomes per WF-02.

## Implementation Paths to Consider

### Workflow Runner State Machine

**Approach:** Simple step-tracker, not a full workflow engine. The runner maintains a JSON state file (`log/workflow-state.json`) containing:
- `workflow_name`, `workflow_version`
- `total_steps`, `completed_steps`
- `current_step` (index or name)
- `status` (running/paused/completed/failed)
- `started_at`, `last_updated`
- `step_results` (per-step success/failure, output)
- `workspace` (path)

The runner reads workflow definitions from YAML/markdown or from a registry. For Phase 4, start with programmatic step lists (curation has 7 steps, etc.).

**Resume logic:** On `--step N` or auto-detect from state file: skip completed steps, start at `current_step`.

### Ingestion Source Type Detection

**Approach** (as per "Specific Ideas" in CONTEXT.md):
- `.pdf`, `.txt`, `.md` → file source
- `http://`, `https://` → URL source  
- Plain text (no matching pattern) → note source
- `research:` prefix or structured data → web research source

Each type triggers the same pipeline (type→domain→ref→seed→log) with type-specific preprocessing.

### Help Suggestion Priority

**Approach** (as per CONTEXT.md Specific Ideas, matching current `construct-help` skill):
1. No workspace exists → suggest init
2. Domain exists but empty → suggest research cycle
3. Domain not interviewed → suggest domain init
4. Cards exist but no connections → suggest curation
5. Research stale (last_queried > 7 days) → suggest research
6. Pending curation items → suggest curation
7. Graph healthy → suggest growth activities

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `typer>=0.12` | 0.24.1 | CLI framework — used for all command groups |
| `pydantic>=2.7` | 2.13.3 | Input/output models for capabilities |
| `mcp>=1.0` | installed | MCP server — auto-registers tools |
| `pytest>=9.0` | 9.0.3 | Test runner |

All already in `pyproject.toml` (mcp added in Phase 3). No new external dependencies needed for Phase 4.

## Files to Create/Modify

### New files:
- `src/construct/pipelines/workflow_runner.py` (~250 lines) — workflow state machine
- `src/construct/services/help.py` (~150 lines) — workspace health analysis
- `src/construct/pipelines/ingestion.py` (~200 lines) — unified ingestion pipeline

### Modified files:
- `src/construct/cli.py` — add `workflow`, `ingest`, `help` commands
- `src/construct/capabilities/catalog.py` — register `workflow.*`, `ingest.*`, `help.suggest` capabilities
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-graph-status/SKILL.md` — migration
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md` — migration
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md` — migration
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md` — migration
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-gap-analysis/SKILL.md` — migration
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` — documentation update
- `CONSTRUCT-CLAUDE-impl/construct/workflows/cold-start.md` — documentation update
- `CONSTRUCT-CLAUDE-impl/construct/workflows/co-authorship.md` — documentation update

### Test files:
- `tests/unit/test_workflow_runner.py`
- `tests/unit/test_ingestion.py`
- `tests/unit/test_help.py`
