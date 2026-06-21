# Phase 3: Capability Registry, CLI & MCP Spine — Research

**Researched:** 2026-06-10
**Purpose:** Answer "What do I need to know to PLAN Phase 3 well?"

---

## 1. Standard Stack & Available Abstractions

### MCP Python SDK (mcp>=1.0)

The `mcp` library provides the Model Context Protocol implementation for Python. Two API styles:

**FastMCP (decorator-based):**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Construct")

@mcp.tool()
def validate(path: str) -> str:
    """Validate a CONSTRUCT workspace."""
    return json.dumps({"status": "ok"})

mcp.run(transport="stdio")
```

**Low-level Server (handler-based — best for dynamic tool registration):**
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

async def handle_list_tools(params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=[
        types.Tool(
            name="construct_validate",
            description="Validate a CONSTRUCT workspace",
            input_schema={...},
        )
    ])

async def handle_call_tool(params) -> types.CallToolResult:
    name = params.name
    args = params.arguments or {}
    # Dynamic dispatch via capability registry
    cap = registry.get_by_mcp_name(name)
    result = cap.handler(**args)
    return types.CallToolResult(content=[
        types.TextContent(type="text", text=json.dumps(result))
    ])

app = Server("construct", on_list_tools=handle_list_tools, on_call_tool=handle_call_tool)
```

**D-09 mandates dynamic registration** — iterate the capability registry, build `types.Tool` objects from each capability's schema. Use the **low-level Server API** with `on_list_tools`/`on_call_tool` handlers.

| API | When to Use |
|-----|-------------|
| FastMCP decorators | Static tools known at import time |
| Low-level Server | **Dynamic tools** (our case — registry may grow/shrink) |

**Stdio transport pattern:**
```python
async def arun():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

anyio.run(arun)
```

### Capability Registry Pattern

The CONTEXT.md defines the pattern in D-01 through D-03. Research confirms this is sound:

**Pydantic model for capability definitions:**
```python
from pydantic import BaseModel, Field
from typing import Any, Callable, Optional

class CapabilityRecord(BaseModel):
    id: str                                # e.g. "workspace.validate"
    name: str                              # Human-readable name
    description: str
    input_model: type[BaseModel]           # Pydantic model reference (not instance)
    output_model: type[BaseModel]          # Pydantic model reference
    handler: Callable[..., Any]            # Direct callable
    cli_name: Optional[str] = None         # e.g. "validate"
    mcp_tool_name: Optional[str] = None    # e.g. "construct_validate"

class CapabilityRegistry:
    _capabilities: dict[str, CapabilityRecord]

    def register(self, cap: CapabilityRecord) -> None: ...
    def get(self, id: str) -> CapabilityRecord: ...
    def list(self) -> list[CapabilityRecord]: ...
    def get_by_mcp_name(self, name: str) -> CapabilityRecord: ...
    def list_mcp_tools(self) -> list[CapabilityTool]: ...
```

**Key insight:** Pydantic model references are stored at class level, not instance level. `input_model.model_json_schema()` generates JSON Schema dynamically.

### Existing CLI Patterns (typer)

Phase 2 established nested Typer groups:
```python
knowledge_app = typer.Typer()
app.add_typer(knowledge_app, name="knowledge")

card_app = typer.Typer()
knowledge_app.add_typer(card_app, name="card")

@card_app.command()
def create(...):
    # Before: result = create_card(workspace, card_data, author=...)
    # After (Phase 3): registry.get("knowledge.card.create").handler(...)
    ...
```

### Existing Handler Functions (reuse targets)

| Capability ID | Existing Handler | Location |
|---------------|-----------------|----------|
| `workspace.init` | `initialize_workspace()` | `src/construct/services/init.py` |
| `workspace.validate` | `validate_workspace()` | `src/construct/services/validation.py` |
| `workspace.status` | `WorkspaceLoader().inspect_workspace()` | `src/construct/storage/workspace.py` |
| `knowledge.card.create` | `create_card()` | `src/construct/services/knowledge.py` |
| `knowledge.card.edit` | `edit_card()` | `src/construct/services/knowledge.py` |
| `knowledge.card.archive` | `archive_card()` | `src/construct/services/knowledge.py` |
| `knowledge.connection.add` | `add_connection()` | `src/construct/services/knowledge.py` |
| `knowledge.connection.remove` | `remove_connection()` | `src/construct/services/knowledge.py` |
| `knowledge.connection.list` | `list_connections()` | `src/construct/services/knowledge.py` |

### New PIPE Handlers Needed

| Capability ID | What It Does | Implementation |
|---------------|-------------|----------------|
| `graph.status` | Produce graph status: card count, connection count, domains, archived count | New `graph_status()` in `src/construct/pipelines/graph_status.py` |
| `views.generate_data` | Generate view data JSON from workspace | Wrapper calling existing `CONSTRUCT-CLAUDE-impl/.../generate.py` or port key parsers |

---

## 2. Architecture Patterns

### Registry → CLI → MCP Invocation Flow

```
User CLI
  │
  ▼
cli.py (thin adapter)
  │  Parse args → cap_id = resolve_cli_to_cap(command_name)
  │  result = registry.get(cap_id).handler(**parsed_args)
  │  _display_result(result)
  ▼
CapabilityRegistry
  │
  ├── workspace.validate → validate_workspace()
  ├── graph.status       → graph_status()
  ├── views.generate_data → generate_views_data()
  ├── knowledge.card.create → create_card()
  └── ...

MCP Client (Claude/Cursor)
  │
  ▼
mcp/server.py
  │  on_list_tools → registry.list_mcp_tools() → types.Tool[]
  │  on_call_tool  → cap = registry.get_by_mcp_name(name)
  │                  result = cap.handler(**args)
  │                  → types.CallToolResult
  ▼
CapabilityRegistry (same instance)
```

### MCP Tool Error Format

Per D-08 (same contract as CLI):
```python
# Success
types.CallToolResult(content=[
    types.TextContent(type="text", text=json.dumps({"success": True, ...}))
])
# Error
types.CallToolResult(
    content=[types.TextContent(type="text", text=json.dumps({"success": False, ...}))],
    isError=True
)
```

### Standard Structured Response

All PIPE capabilities return `OperationResult` (already defined in `knowledge.py`):
```python
@dataclass
class OperationResult:
    success: bool = True
    message: str = ""
    errors: list[OperationError] = field(default_factory=list)
    data: Any = None
```

---

## 3. Don't Hand-Roll

| What | Why not | Use instead |
|------|---------|-------------|
| MCP protocol parsing | Complex, versioned | `mcp>=1.0` library handles stdio transport, JSON-RPC framing |
| JSON Schema generation | Must match Pydantic models | `model.model_json_schema()` (built-in Pydantic v2) |
| CLI argument parsing | Error-prone | Typer (already installed, established in Phase 2) |
| Schema validation | Must match canonical spec | Pydantic models (already exist) |
| Tool registration wiring | Manual, fragile | Registry-driven iteration: `reg.list_mcp_tools()` → `types.Tool[]` |
| Structured responses | Format drift | `OperationResult` already defined |

---

## 4. Common Pitfalls

### Pitfall: MCP tool input schemas not matching CLI expectations
**Mitigation:** Both CLI and MCP use `input_model.model_json_schema()` from the same capability registry entry. Schema is shared — no dual maintenance.

### Pitfall: Stale capability catalog after new commands added
**Mitigation:** Registry should raise `KeyError` on `get()` for unknown IDs. CLI refactoring wraps all lookups with error handling and suggestions.

### Pitfall: Async/sync mismatch between registry handlers (sync) and MCP server (async)
**Mitigation:** Use `anyio.to_thread.run_sync(cap.handler, *args)` to wrap sync handlers in the async MCP call tool handler. Or make all PIPE handlers async. The CONTEXT.md doesn't specify — at discretion use `run_sync` for existing sync handlers.

### Pitfall: `construct mcp` CLI command blocking forever
**Mitigation:** The stdio transport runs until the process terminates. This is expected MCP behavior. The `construct mcp` command is long-running — document this in help text.

### Pitfall: Duplicate capability IDs on registration
**Mitigation:** Registry `register()` should raise `ValueError` on duplicate `id`.

---

## 5. Key Dependencies

| Dependency | Purpose | Already installed |
|-----------|---------|-----------------|
| typer | CLI framework | ✓ (v0.24.1) |
| pydantic v2 | Schema validation, JSON Schema generation | ✓ (v2.13.3) |
| ruamel.yaml | YAML parsing | ✓ (v0.19.1) |
| **mcp>=1.0** | MCP stdio server, tool protocol | ✗ — needs adding |
| anyio | Async runtime for MCP server | ✓ (transitive from mcp) |

---

## 6. File Inventory

### New Directories
- `src/construct/capabilities/` — Capability registry module
- `src/construct/pipelines/` — PIPE capability handlers
- `src/construct/mcp/` — MCP server
- `tests/contract/` — Contract tests (new)

### Files to Create
- `src/construct/capabilities/__init__.py`
- `src/construct/capabilities/registry.py` — CapabilityRecord, CapabilityRegistry
- `src/construct/capabilities/catalog.py` — Pre-registered capabilities
- `src/construct/pipelines/__init__.py`
- `src/construct/pipelines/graph_status.py` — graph.status handler
- `src/construct/pipelines/views_generate_data.py` — views.generate_data handler
- `src/construct/mcp/__init__.py`
- `src/construct/mcp/server.py` — MCP stdio server
- `tests/unit/test_capability_registry.py` — Registry unit tests
- `tests/contract/test_cli_contracts.py` — CLI contract tests
- `tests/contract/test_mcp_contracts.py` — MCP schema parity tests

### Files to Modify
- `pyproject.toml` — Add `mcp>=1.0` dependency
- `src/construct/cli.py` — Refactor commands to delegate to registry; add `construct mcp` subcommand
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md` — Migrate to MCP invocation

---

## 7. Test Strategy

### Unit Tests
- `test_capability_registry.py` — Registry CRUD, duplicate detection, MCP tool list
- Existing test suites unaffected

### Integration Tests
- `test_cli_contracts.py` — CLI commands still work after refactoring (run against `test-ws/`)

### Contract Tests
- `test_mcp_contracts.py` — MCP tool list matches CLI; schema parity; tool invocation returns expected types

---

## Validation Architecture

### Pre-write validation (existing)
All write operations validate through existing Pydantic models. No change for Phase 3.

### Capability registry validation
- Registry `register()` validates: unique `id`, handler is callable, models are Pydantic BaseModel subclasses
- Registry `get()` raises `KeyError` with suggestion for unknown IDs

### MCP contract validation
- Every registered capability with `mcp_tool_name` gets a `types.Tool` entry
- JSON Schema derived from `input_model.model_json_schema()` — automatic, no drift

---
