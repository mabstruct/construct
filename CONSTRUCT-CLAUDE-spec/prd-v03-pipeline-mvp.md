# CONSTRUCT v0.3 — Pipeline MVP (Tranche 1) — Product Requirements Document

**Version:** 0.3.0-tranche1  
**Date:** 2026-06-07  
**Status:** Draft — implementation binding for tranche 1  
**Prerequisite:** v0.1 Claude-native impl, v0.2 views (complete)  
**Architecture:** [ADR-0003](adrs/adr-0003-v03-pipeline-v04-ui.md)  
**Scope source:** [tranche-1-mvp.md](../CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md)

**Related (authoritative for domain semantics):**

| Document | Role |
|----------|------|
| [artifact-catalog.md](artifact-catalog.md) | Master capability inventory — registry entries must match catalog IDs |
| [data-schemas.md](data-schemas.md) | Workspace SOT schemas, base `events.jsonl` format |
| [spec-v02-data-model.md](spec-v02-data-model.md) | Views JSON contracts produced by `views.generate_data` |
| `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md` | Layer 0 procedure specs — Python implements PIPE steps only |

This PRD defines **binding contracts** for tranche 1: capability registry, JSON schemas, CLI, MCP tools, LangGraph L2 gate, Streamlit spike pages, and pipeline event format. Where this document conflicts with tranche-1-mvp.md on scope, tranche-1-mvp wins; where it conflicts with v0.2 views specs on data shape, v0.2 specs win.

---

## 1. Summary

v0.3 tranche 1 proves the layered runtime from ADR-0003:

```text
Layer 0  SKILL.md specs (unchanged authority for *what*)
Layer 1  Workspace SOT (unchanged)
Layer 2  Python pipelines + LangGraph L2 gates
Layer 3  CLI (first) + MCP stdio (same contracts)
         Streamlit spike (localhost ops console — not Layer 4 product UI)
```

**Goal:** Every tranche-1 capability is **headless-testable** via CLI, **agent-invokable** via MCP, and **browser-runnable** via Streamlit — without changing workspace file formats.

**Not in tranche 1:** HTTP API, MCP SSE, full Daily Cycle (research + curation), CoPilotKit, cloud deploy, SQLite indexer.

---

## 2. Design principles

| Principle | Tranche 1 implication |
|-----------|---------------------|
| **One registry, many adapters** | CLI, MCP, and Streamlit call the same handler functions |
| **Catalog is master** | Capability IDs, CLI names, and MCP tool names are registered centrally |
| **Workspace SOT unchanged** | Pipelines read/write the same paths Claude uses today |
| **PIPE before LLM** | Deterministic steps are plain Python; L2 is LangGraph only at declared gates |
| **Provider swap via config** | No provider-specific code in pipeline handlers |
| **Events are append-only** | Pipeline steps emit structured lines to `log/events.jsonl` |
| **Fail loud, structured** | Errors return machine-readable codes + human detail; never silent partial success |

---

## 3. Repository layout (tranche 1)

| Component | Path | Notes |
|-----------|------|-------|
| Capability registry | `src/construct/capabilities/registry.py` | Single source for IDs, schemas, handlers |
| Capability schemas | `src/construct/capabilities/schemas/` | Pydantic models → JSON Schema export |
| PIPE handlers | `src/construct/pipelines/` | One module per capability |
| LangGraph L2 gate | `src/construct/llm/ask_domain.py` | Graph definition + runner |
| Provider config | `src/construct/llm/config.yaml` | Repo default; workspace override optional |
| CLI | `src/construct/cli.py` | Extend existing Typer app |
| MCP server | `src/construct/mcp/server.py` | stdio transport |
| Streamlit spike | `src/construct/ui/streamlit_app.py` | **Decision:** co-locate under `src/construct/ui/` (not throwaway `spikes/`) so v0.4 can reuse patterns |
| Contract tests | `tests/contract/` | CLI golden paths against `test-ws/` fixtures |
| Workflow orchestrator | `src/construct/pipelines/workflow_daily_cycle.py` | Skeleton only |

**Dependencies to add** (tranche 1):

```toml
# pyproject.toml additions
"mcp>=1.0",
"langgraph>=0.2",
"langchain-core>=0.3",
"langchain-anthropic>=0.3",   # default provider; others via config
"streamlit>=1.35",
"jsonschema>=4.21",
```

Existing `validate` CLI command becomes a thin wrapper around `workspace.validate` registry entry (backward compatible).

---

## 4. Capability registry

### 4.1 Registry record shape

Each capability is a frozen record:

```python
@dataclass(frozen=True)
class Capability:
    id: str                          # dotted ID, e.g. "workspace.validate"
    layer: Literal["PIPE", "L2", "L3"]
    handler: Callable[..., CapabilityResult]
    input_model: type[BaseModel]     # Pydantic
    output_model: type[BaseModel]
    cli_command: str | None          # Typer subcommand path, e.g. "run validate"
    mcp_tool: str | None             # MCP tool name, e.g. "construct_validate"
    idempotent: bool
    mutates_sot: bool                # writes canonical workspace files
    skill_ref: str | None            # CONSTRUCT-CLAUDE-impl skill path
    errors: dict[str, str]           # error_code → description
```

### 4.2 Tranche 1 registry

| Capability ID | Layer | CLI | MCP tool | Idempotent | Mutates SOT | Skill ref |
|---------------|-------|-----|----------|------------|-------------|-----------|
| `workspace.validate` | PIPE | `construct run validate` | `construct_validate` | yes | no | `construct-workspace-validate` |
| `graph.status` | PIPE | `construct run graph-status` | `construct_graph_status` | yes | no | `construct-graph-status` |
| `views.generate_data` | PIPE | `construct run views-generate-data` | `construct_views_generate_data` | yes | derived-only | `construct-views-generate-data` |
| `workflow.daily_cycle` | PIPE | `construct run workflow daily-cycle` | `construct_run_daily_cycle` | no | no* | `daily-cycle` workflow |
| `ask.domain` | L2 | `construct run ask` | `construct_ask_domain` | yes | no | new — L2 gate only |

\* Skeleton writes **events only**; does not run research/curation in tranche 1.

### 4.3 Invocation flow

```text
CLI / MCP / Streamlit
        │
        ▼
  validate input (Pydantic)
        │
        ▼
  registry.get(capability_id).handler(input)
        │
        ├── PIPE → Python handler → CapabilityResult
        │
        └── L2   → LangGraph gate runner → GateResult (pending review if configured)
        │
        ▼
  validate output (Pydantic)
        │
        ▼
  optional: append pipeline events to log/events.jsonl
        │
        ▼
  return JSON to caller
```

### 4.4 Shared envelope types

All capability **inputs** extend a base request; all **outputs** extend a base result.

**`CapabilityRequest`** (base):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "construct.capability.request.v1",
  "type": "object",
  "required": ["correlation_id"],
  "properties": {
    "correlation_id": {
      "type": "string",
      "format": "uuid",
      "description": "Caller-generated ID for tracing across CLI/MCP/UI"
    },
    "emit_events": {
      "type": "boolean",
      "default": true,
      "description": "When true, handler appends pipeline events to workspace log"
    }
  },
  "additionalProperties": false
}
```

**`CapabilityResult`** (base):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "construct.capability.result.v1",
  "type": "object",
  "required": ["capability_id", "correlation_id", "status", "started_at", "finished_at", "duration_ms"],
  "properties": {
    "capability_id": { "type": "string" },
    "correlation_id": { "type": "string", "format": "uuid" },
    "status": { "enum": ["success", "failure", "partial"] },
    "started_at": { "type": "string", "format": "date-time" },
    "finished_at": { "type": "string", "format": "date-time" },
    "duration_ms": { "type": "integer", "minimum": 0 },
    "error": {
      "type": ["object", "null"],
      "required": ["code", "message"],
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" },
        "details": { "type": "object" }
      }
    }
  },
  "additionalProperties": true
}
```

**Standard error codes** (all capabilities):

| Code | HTTP-analog | When |
|------|-------------|------|
| `WORKSPACE_NOT_FOUND` | 404 | Path does not exist or missing `domains.yaml` |
| `INSTALL_ROOT_INVALID` | 404 | `install_root` missing `AGENTS.md` |
| `SCHEMA_VALIDATION_FAILED` | 422 | Input failed Pydantic validation |
| `PRECONDITION_FAILED` | 412 | e.g. `views/build/` missing for views generate |
| `HANDLER_ERROR` | 500 | Unexpected exception; message sanitized |
| `GATE_PROVIDER_ERROR` | 502 | LLM provider unreachable or misconfigured |
| `GATE_TIMEOUT` | 504 | LangGraph gate exceeded timeout |

---

## 5. Capability contracts

### 5.1 `workspace.validate`

**Purpose:** Run workspace integrity checks. Implements Layer 1–3 of `construct-workspace-validate` SKILL.md in tranche 1; Layers 4–5 (functional spot-check, audit trail) are warnings-only stubs returning `not_implemented` findings until tranche 2.

**Input** — `WorkspaceValidateInput`:

```json
{
  "$id": "construct.workspace.validate.input.v1",
  "allOf": [
    { "$ref": "construct.capability.request.v1" },
    {
      "type": "object",
      "required": ["workspace_path"],
      "properties": {
        "workspace_path": {
          "type": "string",
          "description": "Absolute or relative path to domain workspace root (contains domains.yaml or is a domain folder)"
        },
        "layers": {
          "type": "array",
          "items": { "enum": ["schema", "governance", "consistency", "functional", "audit_trail"] },
          "default": ["schema", "governance", "consistency"],
          "description": "Which validation layers to run"
        },
        "fail_fast": {
          "type": "boolean",
          "default": false,
          "description": "Stop after first error layer"
        }
      }
    }
  ]
}
```

**Output** — `WorkspaceValidateOutput`:

```json
{
  "$id": "construct.workspace.validate.output.v1",
  "allOf": [
    { "$ref": "construct.capability.result.v1" },
    {
      "type": "object",
      "required": ["summary", "findings"],
      "properties": {
        "summary": {
          "type": "object",
          "required": ["files_checked", "error_count", "warning_count", "pass"],
          "properties": {
            "files_checked": { "type": "integer" },
            "error_count": { "type": "integer" },
            "warning_count": { "type": "integer" },
            "pass": { "type": "boolean" }
          }
        },
        "findings": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["severity", "layer", "path", "message"],
            "properties": {
              "severity": { "enum": ["error", "warning", "info"] },
              "layer": { "enum": ["schema", "governance", "consistency", "functional", "audit_trail"] },
              "path": { "type": "string" },
              "message": { "type": "string" },
              "rule_id": { "type": "string" }
            }
          }
        },
        "layers_run": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  ]
}
```

**Status rule:** `status: failure` when `error_count > 0`; else `success`.

**Implementation note:** Reuse `construct.services.validation.validate_workspace`; extend with governance/consistency layers per SKILL.md checklist.

---

### 5.2 `graph.status`

**Purpose:** Compute knowledge graph health metrics. Implements `construct-graph-status` Step 1 (Gather Stats) as structured JSON; Step 3 interpretation remains L2/`ask.domain` or v0.5 UI.

**Input** — `GraphStatusInput`:

```json
{
  "$id": "construct.graph.status.input.v1",
  "allOf": [
    { "$ref": "construct.capability.request.v1" },
    {
      "type": "object",
      "required": ["workspace_path"],
      "properties": {
        "workspace_path": { "type": "string" },
        "include_archived": {
          "type": "boolean",
          "default": false
        }
      }
    }
  ]
}
```

**Output** — `GraphStatusOutput`:

```json
{
  "$id": "construct.graph.status.output.v1",
  "allOf": [
    { "$ref": "construct.capability.result.v1" },
    {
      "type": "object",
      "required": ["cards", "connections", "domains", "research", "quality"],
      "properties": {
        "cards": {
          "type": "object",
          "required": ["total", "by_lifecycle", "by_epistemic_type", "by_domain", "by_confidence"],
          "properties": {
            "total": { "type": "integer" },
            "by_lifecycle": { "type": "object", "additionalProperties": { "type": "integer" } },
            "by_epistemic_type": { "type": "object", "additionalProperties": { "type": "integer" } },
            "by_domain": { "type": "object", "additionalProperties": { "type": "integer" } },
            "by_confidence": {
              "type": "object",
              "properties": {
                "1": { "type": "integer" },
                "2": { "type": "integer" },
                "3": { "type": "integer" },
                "4": { "type": "integer" },
                "5": { "type": "integer" }
              }
            }
          }
        },
        "connections": {
          "type": "object",
          "required": ["total", "by_type", "avg_per_card", "max_hub", "orphan_count"],
          "properties": {
            "total": { "type": "integer" },
            "by_type": { "type": "object", "additionalProperties": { "type": "integer" } },
            "avg_per_card": { "type": "number" },
            "max_hub": {
              "type": "object",
              "required": ["card_id", "title", "count"],
              "properties": {
                "card_id": { "type": "string" },
                "title": { "type": "string" },
                "count": { "type": "integer" }
              }
            },
            "orphan_count": { "type": "integer" }
          }
        },
        "domains": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["domain_id", "display_name", "card_count", "avg_confidence", "category_coverage"],
            "properties": {
              "domain_id": { "type": "string" },
              "display_name": { "type": "string" },
              "card_count": { "type": "integer" },
              "avg_confidence": { "type": "number" },
              "category_coverage": {
                "type": "object",
                "required": ["populated", "total", "ratio"],
                "properties": {
                  "populated": { "type": "integer" },
                  "total": { "type": "integer" },
                  "ratio": { "type": "number" }
                }
              }
            }
          }
        },
        "research": {
          "type": "object",
          "properties": {
            "ref_count": { "type": "integer" },
            "active_search_clusters": { "type": "integer" },
            "last_research_cycle_at": { "type": ["string", "null"], "format": "date-time" }
          }
        },
        "quality": {
          "type": "object",
          "properties": {
            "stale_card_count": { "type": "integer" },
            "orphan_past_tolerance": { "type": "integer" }
          }
        }
      }
    }
  ]
}
```

---

### 5.3 `views.generate_data`

**Purpose:** Regenerate `views/build/data/` and `views/build/version.json` per v0.2 specs. Wraps existing `construct-views-generate-data/generate.py`.

**Input** — `ViewsGenerateDataInput`:

```json
{
  "$id": "construct.views.generate_data.input.v1",
  "allOf": [
    { "$ref": "construct.capability.request.v1" },
    {
      "type": "object",
      "required": ["install_root"],
      "properties": {
        "install_root": {
          "type": "string",
          "description": "CONSTRUCT install root (contains AGENTS.md and views/build/)"
        },
        "workspace_filter": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Optional workspace slugs to limit regeneration; default all discovered"
        },
        "force": {
          "type": "boolean",
          "default": false,
          "description": "Bypass incremental fingerprint skip"
        }
      }
    }
  ]
}
```

**Output** — `ViewsGenerateDataOutput`:

```json
{
  "$id": "construct.views.generate_data.output.v1",
  "allOf": [
    { "$ref": "construct.capability.result.v1" },
    {
      "type": "object",
      "required": ["incremental", "workspaces", "build_id"],
      "properties": {
        "incremental": {
          "type": "object",
          "required": ["mode"],
          "properties": {
            "mode": { "enum": ["full", "partial", "noop"] },
            "changed_workspaces": { "type": "array", "items": { "type": "string" } },
            "unchanged_workspaces": { "type": "array", "items": { "type": "string" } }
          }
        },
        "workspaces": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["slug", "cards", "connections"],
            "properties": {
              "slug": { "type": "string" },
              "cards": { "type": "integer" },
              "connections": { "type": "integer" },
              "digests": { "type": "integer" },
              "articles": { "type": "integer" }
            }
          }
        },
        "build_id": { "type": "string" },
        "warnings": { "type": "array", "items": { "type": "string" } },
        "output_paths": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Relative paths written under install_root"
        }
      }
    }
  ]
}
```

**Precondition:** `install_root/views/build/` must exist → else `PRECONDITION_FAILED`.

**Mutates:** `views/build/data/**`, `views/build/version.json` only (derived).

---

### 5.4 `workflow.daily_cycle` (skeleton)

**Purpose:** Orchestrate tranche-1 subset of Daily Cycle as a deterministic pipeline with step events. **Does not** invoke research-cycle or curation-cycle in tranche 1.

**Input** — `DailyCycleInput`:

```json
{
  "$id": "construct.workflow.daily_cycle.input.v1",
  "allOf": [
    { "$ref": "construct.capability.request.v1" },
    {
      "type": "object",
      "required": ["workspace_path", "install_root"],
      "properties": {
        "workspace_path": { "type": "string" },
        "install_root": { "type": "string" },
        "skip_views_regen": {
          "type": "boolean",
          "default": false
        }
      }
    }
  ]
}
```

**Output** — `DailyCycleOutput`:

```json
{
  "$id": "construct.workflow.daily_cycle.output.v1",
  "allOf": [
    { "$ref": "construct.capability.result.v1" },
    {
      "type": "object",
      "required": ["workflow_id", "steps"],
      "properties": {
        "workflow_id": { "const": "daily-cycle" },
        "steps": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["step_id", "capability_id", "status", "started_at", "finished_at"],
            "properties": {
              "step_id": { "enum": ["validate", "graph-status", "views-generate-data"] },
              "capability_id": { "type": "string" },
              "status": { "enum": ["success", "failure", "skipped"] },
              "started_at": { "type": "string", "format": "date-time" },
              "finished_at": { "type": "string", "format": "date-time" },
              "result_ref": {
                "type": "string",
                "description": "correlation_id of nested capability invocation"
              },
              "error": { "$ref": "#/definitions/error" }
            }
          }
        }
      }
    }
  ]
}
```

**Step sequence (fixed, tranche 1):**

1. `workspace.validate` — failure aborts workflow
2. `graph.status` — failure aborts workflow
3. `views.generate_data` — skipped when `skip_views_regen: true` or `views/build/` missing (status `skipped`, not failure)

---

### 5.5 `ask.domain` (L2 LangGraph gate)

**Purpose:** Grounded Q&A over workspace cards for a domain. Read-only in tranche 1 — no SOT writes without explicit USER-REVIEW approval via Streamlit gate panel.

**Input** — `AskDomainInput`:

```json
{
  "$id": "construct.ask.domain.input.v1",
  "allOf": [
    { "$ref": "construct.capability.request.v1" },
    {
      "type": "object",
      "required": ["workspace_path", "domain_id", "question"],
      "properties": {
        "workspace_path": { "type": "string" },
        "domain_id": { "type": "string" },
        "question": { "type": "string", "minLength": 3, "maxLength": 2000 },
        "max_cards": {
          "type": "integer",
          "default": 20,
          "minimum": 1,
          "maximum": 50,
          "description": "Retrieval budget for grounding context"
        },
        "provider_override": {
          "type": ["string", "null"],
          "description": "Optional provider key from config; default from llm/config.yaml"
        }
      }
    }
  ]
}
```

**Output** — `AskDomainOutput`:

```json
{
  "$id": "construct.ask.domain.output.v1",
  "allOf": [
    { "$ref": "construct.capability.result.v1" },
    {
      "type": "object",
      "required": ["answer", "citations", "gate"],
      "properties": {
        "answer": { "type": "string" },
        "citations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["card_id", "title", "snippet"],
            "properties": {
              "card_id": { "type": "string" },
              "title": { "type": "string" },
              "snippet": { "type": "string" },
              "confidence": { "type": "integer", "minimum": 1, "maximum": 5 }
            }
          }
        },
        "gate": {
          "type": "object",
          "required": ["gate_id", "tier", "review_required", "review_status"],
          "properties": {
            "gate_id": { "const": "ask.domain" },
            "tier": { "const": "L2" },
            "review_required": { "type": "boolean" },
            "review_status": {
              "enum": ["not_required", "pending", "approved", "rejected"]
            },
            "provider": { "type": "string" },
            "model": { "type": "string" },
            "token_usage": {
              "type": "object",
              "properties": {
                "input_tokens": { "type": "integer" },
                "output_tokens": { "type": "integer" }
              }
            }
          }
        },
        "retrieval": {
          "type": "object",
          "properties": {
            "cards_considered": { "type": "integer" },
            "cards_selected": { "type": "integer" }
          }
        }
      }
    }
  ]
}
```

**Tranche 1 rule:** `review_required: true` always; `review_status: pending` on success. Streamlit gate panel sets approved/rejected locally (no SOT write on reject).

---

## 6. CLI specification

### 6.1 Command tree

```text
construct
├── init <path>                    # existing — unchanged
├── validate <path>                # alias → construct run validate (backward compat)
├── status <path>                  # existing workspace ownership — unchanged
├── run
│   ├── validate [--workspace PATH] [--json]
│   ├── graph-status [--workspace PATH] [--json]
│   ├── views-generate-data [--install-root PATH] [--json]
│   ├── ask [--workspace PATH] [--domain ID] [--question TEXT] [--json]
│   └── workflow
│       └── daily-cycle [--workspace PATH] [--install-root PATH] [--skip-views] [--json]
└── mcp                            # stdio MCP server — no subcommands
```

### 6.2 Flags (all `run` commands)

| Flag | Effect |
|------|--------|
| `--workspace PATH` | Domain workspace root; required except views-generate-data |
| `--install-root PATH` | Install root; required for views-generate-data and daily-cycle |
| `--json` | Emit full `CapabilityResult` JSON to stdout; exit code 1 on `status: failure` |
| `--no-events` | Sets `emit_events: false` on request |
| `--correlation-id UUID` | Override auto-generated correlation ID |

### 6.3 Exit codes

| Code | Meaning |
|------|---------|
| 0 | `status: success` or `partial` with no errors |
| 1 | `status: failure` or validation errors |
| 2 | Usage / schema validation error |

### 6.4 Human-readable default

Without `--json`, CLI prints a concise summary (matching current `validate` style) plus correlation ID on stderr for log correlation.

---

## 7. MCP tool definitions

**Transport:** stdio via `construct mcp`  
**Protocol:** MCP 2024-11-05  
**Server name:** `construct`  
**Server version:** matches `construct.__version__`

Each tool accepts a **single JSON object** argument matching the capability input schema. Returns **text content** block containing pretty-printed capability output JSON.

### 7.1 Tool catalog

| MCP tool | Capability | Description |
|----------|------------|-------------|
| `construct_validate` | `workspace.validate` | Validate workspace integrity |
| `construct_graph_status` | `graph.status` | Knowledge graph health metrics |
| `construct_views_generate_data` | `views.generate_data` | Regenerate views JSON data |
| `construct_run_daily_cycle` | `workflow.daily_cycle` | Run daily-cycle skeleton pipeline |
| `construct_ask_domain` | `ask.domain` | L2 grounded Q&A with citations |

### 7.2 Example: `construct_validate`

**Tool descriptor** (MCP `tools/list`):

```json
{
  "name": "construct_validate",
  "description": "Validate CONSTRUCT workspace integrity. Returns structured findings with errors and warnings.",
  "inputSchema": {
    "$ref": "construct.workspace.validate.input.v1"
  }
}
```

**Example invocation:**

```json
{
  "workspace_path": "/path/to/test-ws/my-construct/cosmology",
  "layers": ["schema", "governance", "consistency"],
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example response** (text content):

```json
{
  "capability_id": "workspace.validate",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "summary": { "files_checked": 47, "error_count": 0, "warning_count": 2, "pass": true },
  "findings": []
}
```

### 7.3 MCP config snippet (Cursor / Claude Desktop)

```json
{
  "mcpServers": {
    "construct": {
      "command": "construct",
      "args": ["mcp"],
      "env": {
        "CONSTRUCT_LLM_CONFIG": "/path/to/repo/src/construct/llm/config.yaml"
      }
    }
  }
}
```

### 7.4 Schema parity test

Contract test `tests/contract/test_mcp_schema_parity.py` must assert: for each registered capability, MCP `inputSchema` equals CLI `--json` input schema (exported from same Pydantic model).

---

## 8. LangGraph L2 gate contract

### 8.1 Gate identity

| Field | Value |
|-------|-------|
| Gate ID | `ask.domain` |
| Tier | L2 |
| Graph module | `src/construct/llm/ask_domain.py` |
| State schema | `AskDomainState` (TypedDict) |

### 8.2 Graph topology (tranche 1)

```text
START
  │
  ▼
load_domain_cards ──► filter_by_domain ──► rank_by_relevance (keyword + optional embedding stub)
  │
  ▼
build_context ──► llm_synthesize ──► extract_citations ──► END
```

**Nodes:**

| Node | Type | Responsibility |
|------|------|----------------|
| `load_domain_cards` | PYTHON | Parse cards from workspace; filter archived |
| `filter_by_domain` | PYTHON | Match `domain_id` against card domains |
| `rank_by_relevance` | PYTHON | Score cards against question tokens; take top `max_cards` |
| `build_context` | PYTHON | Format card summaries for prompt |
| `llm_synthesize` | LLM | Structured output: answer + cited card IDs |
| `extract_citations` | PYTHON | Map cited IDs to `citations[]`; validate all IDs exist |

### 8.3 Structured LLM output schema

LangGraph `llm_synthesize` node uses **structured output** (not freeform):

```json
{
  "$id": "construct.llm.ask_domain.synthesis.v1",
  "type": "object",
  "required": ["answer", "cited_card_ids"],
  "properties": {
    "answer": { "type": "string" },
    "cited_card_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Subset of retrieved card IDs actually used"
    },
    "confidence": {
      "enum": ["high", "medium", "low"],
      "description": "Model self-assessed grounding confidence"
    }
  }
}
```

### 8.4 Provider configuration

**Decision (PRD):** Repo default at `src/construct/llm/config.yaml`; optional workspace override at `<workspace>/.construct/llm.yaml` (workspace wins on key collision).

**`config.yaml` shape:**

```yaml
version: 1
default_gate: ask.domain

providers:
  anthropic:
    type: langchain_anthropic
    model: claude-sonnet-4-20250514
    max_tokens: 4096
    timeout_seconds: 60
  openai:
    type: langchain_openai
    model: gpt-4o
    max_tokens: 4096
    timeout_seconds: 60
  ollama:
    type: langchain_ollama
    model: llama3.1
    base_url: http://localhost:11434
    timeout_seconds: 120

gates:
  ask.domain:
    provider: anthropic
    temperature: 0.2
    review_required: true
```

**Environment overrides:**

| Variable | Effect |
|----------|--------|
| `CONSTRUCT_LLM_CONFIG` | Path to config YAML |
| `CONSTRUCT_LLM_PROVIDER` | Override active provider key for all gates |
| `ANTHROPIC_API_KEY` | Provider credential |
| `OPENAI_API_KEY` | Provider credential |

**Provider swap acceptance test:** Run `ask.domain` twice with only `gates.ask.domain.provider` changed; both return valid structured output with citations.

### 8.5 Gate runner interface

```python
def run_gate(gate_id: str, input: BaseModel, *, config_path: Path | None = None) -> GateResult:
    """Execute LangGraph gate; never writes SOT."""
```

`GateResult` extends capability output with `gate.review_status: pending` until external reviewer acts.

### 8.6 Gate review protocol (Streamlit + future v0.4)

| Review action | Effect |
|---------------|--------|
| **Approve** | Log `gate_review_approved` event; optionally surface answer to user |
| **Reject** | Log `gate_review_rejected` event; discard answer |
| **Edit** | v0.4 — allow edited answer before approve |

Tranche 1: approve/reject is **local UI state + event log only** — no card or publish writes.

---

## 9. Pipeline event format

Pipeline and workflow steps extend the existing [`data-schemas.md`](data-schemas.md) §3.1 event log. **Do not break** existing event consumers in views generation.

### 9.1 Base event (unchanged)

Required fields: `ts`, `agent`, `action`, `result`.

### 9.2 New agent value

| Agent | When |
|-------|------|
| `pipeline` | All v0.3 Python pipeline and workflow events |

### 9.3 Pipeline action catalog (tranche 1)

| Action | When | Typical detail |
|--------|------|----------------|
| `capability_start` | Handler begins | `{capability_id, correlation_id}` |
| `capability_complete` | Handler succeeds | `{capability_id, correlation_id, duration_ms}` |
| `capability_failed` | Handler fails | `{capability_id, correlation_id, error_code}` |
| `workflow_start` | Workflow begins | `{workflow_id, correlation_id}` |
| `workflow_step` | Step completes | `{workflow_id, step_id, status}` |
| `workflow_complete` | Workflow ends | `{workflow_id, status, steps_run}` |
| `gate_invoked` | LangGraph gate starts | `{gate_id, provider, model}` |
| `gate_complete` | LangGraph gate succeeds | `{gate_id, review_required}` |
| `gate_failed` | LangGraph gate fails | `{gate_id, error_code}` |
| `gate_review_approved` | User approves L2 output | `{gate_id, correlation_id}` |
| `gate_review_rejected` | User rejects L2 output | `{gate_id, correlation_id}` |

### 9.4 Extended event shape (pipeline events)

Pipeline events add optional structured fields without removing base requirements:

```json
{
  "ts": "2026-06-07T10:15:30.123Z",
  "agent": "pipeline",
  "action": "capability_complete",
  "target": "workspace.validate",
  "detail": "0 errors, 2 warnings",
  "result": "success",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "capability_id": "workspace.validate",
  "duration_ms": 842,
  "context": {
    "workspace_path": "cosmology",
    "install_root": null
  }
}
```

**Rules:**

- `correlation_id` is **required** on all pipeline events when `emit_events: true`
- Events append to `<workspace>/log/events.jsonl` for workspace-scoped capabilities
- `views.generate_data` appends to a nominated workspace log (first workspace in filter) or install-root `log/events.jsonl` if present
- `workflow.daily_cycle` emits one `workflow_start`, one `workflow_step` per step, one `workflow_complete`

### 9.5 Example: daily-cycle skeleton run

```jsonl
{"ts":"2026-06-07T10:00:00.000Z","agent":"pipeline","action":"workflow_start","target":"daily-cycle","detail":"correlation abc-123","result":"success","correlation_id":"abc-123","workflow_id":"daily-cycle"}
{"ts":"2026-06-07T10:00:00.100Z","agent":"pipeline","action":"capability_start","target":"workspace.validate","result":"success","correlation_id":"def-456","capability_id":"workspace.validate"}
{"ts":"2026-06-07T10:00:01.200Z","agent":"pipeline","action":"capability_complete","target":"workspace.validate","detail":"0 errors","result":"success","correlation_id":"def-456","capability_id":"workspace.validate","duration_ms":1100}
{"ts":"2026-06-07T10:00:01.250Z","agent":"pipeline","action":"workflow_step","target":"validate","detail":"success","result":"success","correlation_id":"abc-123","workflow_id":"daily-cycle","step_id":"validate","status":"success"}
{"ts":"2026-06-07T10:00:05.000Z","agent":"pipeline","action":"workflow_complete","target":"daily-cycle","detail":"3 steps","result":"success","correlation_id":"abc-123","workflow_id":"daily-cycle","status":"success"}
```

---

## 10. Streamlit spike specification

**Purpose:** Localhost ops console to run capabilities and preview L2 gate review — informs **v0.5** modal pattern. **Not** product UI.

**Launch:**

```bash
streamlit run src/construct/ui/streamlit_app.py
```

**Config sidebar (persistent):**

| Control | Maps to |
|---------|---------|
| Workspace path | `workspace_path` on requests |
| Install root | `install_root` on views/workflow |
| LLM config path | `CONSTRUCT_LLM_CONFIG` |
| Provider override | `provider_override` on ask |

### 10.1 Pages

| Page | Route | Purpose |
|------|-------|---------|
| **Home** | `/` | Capability catalog table with layer badges; links to runner |
| **Capability Runner** | `/run` | Select capability → dynamic form from JSON schema → Run → raw JSON result |
| **Gate Review** | `/gates` | Queue of pending L2 results; approve/reject; citation expanders |
| **Workflow** | `/workflow` | Run daily-cycle skeleton; step progress timeline |
| **Event Tail** | `/events` | Last 50 lines of `log/events.jsonl` for selected workspace |

### 10.2 Capability Runner UX

1. Dropdown: capability ID
2. Auto-render form fields from Pydantic JSON schema (text inputs for paths, textarea for question)
3. **Run** invokes registry handler in-process (same code path as CLI)
4. Results pane: syntax-highlighted JSON + summary chips (status, duration, error count)
5. Copy correlation ID button

### 10.3 Gate Review panel

When `ask.domain` completes:

- Show answer markdown
- Citations as expandable cards (title, snippet, link to card path)
- Provider/model metadata
- **Approve** / **Reject** buttons → append gate review event
- Pending queue stored in session state (tranche 1); v0.4 may persist queue

### 10.4 Workflow page

- Single **Run Daily Cycle** button
- Live step indicator: validate → graph-status → views-generate-data
- Per-step JSON drill-down
- Failed step shows error code + stop indicator

### 10.5 Non-goals (Streamlit)

- No auth
- No multi-user
- No direct SOT editing
- No replacement for v0.2 views SPA

---

## 11. Testing requirements

### 11.1 Contract tests (`tests/contract/`)

| Test | Fixture | Assert |
|------|---------|--------|
| `test_validate_cli` | `test-ws/my-construct/` | exit 0; `summary.pass` matches known fixture |
| `test_validate_mcp` | same | MCP output schema ≡ CLI `--json` |
| `test_graph_status_cli` | same | required metric keys present |
| `test_views_generate_data` | install root with `views/build/` | `build_id` stable on noop re-run |
| `test_daily_cycle_skeleton` | same | 3 steps; events appended |
| `test_ask_domain_mocked` | same + mocked LLM | citations reference real card IDs |
| `test_schema_export` | n/a | registry exports JSON Schema for all 5 capabilities |

### 11.2 LangGraph tests (`tests/llm/`)

- Mock LLM returns fixed structured output → citations validated
- Provider config load + override
- Timeout → `GATE_TIMEOUT`

### 11.3 Parity rule

**CLI ≡ MCP ≡ Streamlit handler** — all three call `registry.invoke(capability_id, input)`; no duplicated business logic.

---

## 12. Skill migration (tranche 1 proof)

**First migrated skill:** `construct-workspace-validate`

**SKILL.md change pattern:**

```markdown
### Execution (v0.3+)

Invoke the pipeline capability instead of inline validation:

\`\`\`bash
construct run validate --workspace <workspace-path> --json
\`\`\`

Or via MCP tool `construct_validate` with the same JSON input.

Parse the JSON `findings` array to build the human report below.
```

Other skills remain Claude-native until their PIPE implementation lands.

---

## 13. Success criteria

Tranche 1 is **complete** when:

1. Capability registry lists all 5 capabilities with validated JSON schemas.
2. CLI contract tests pass on `test-ws/my-construct/` and `test-ws/ping-eon/`.
3. MCP stdio exposes 5 tools with schema parity to CLI.
4. LangGraph L2 `ask.domain` returns cited answers; provider swap via config only.
5. Streamlit runs on localhost — capability runner + gate review + workflow timeline.
6. `workflow.daily_cycle` skeleton emits step events to `log/events.jsonl`.
7. `construct-workspace-validate` SKILL.md migrated to MCP/CLI invoke path.

---

## 14. Open questions (deferred)

| # | Question | PRD decision | Revisit |
|---|----------|--------------|---------|
| 1 | Provider config location | Repo default + optional workspace override | After multi-workspace LLM routing |
| 2 | Streamlit path | `src/construct/ui/` | If spike abandoned, archive to `spikes/` |
| 3 | Catalog columns v0.3/v0.4 split | Defer to artifact-catalog edit | Before tranche 2 planning |
| 4 | Embedding-based retrieval for ask.domain | Keyword rank only in tranche 1 | Tranche 2 |
| 5 | GSD initialization | Fresh `.planning/` when implementation starts | At kickoff |

---

## 15. Document index update

When this PRD is accepted, add to [README_FIRST.md](README_FIRST.md) core narrative table:

| Document | What it is |
|----------|-----------|
| [prd-v03-pipeline-mvp.md](prd-v03-pipeline-mvp.md) | v0.3 tranche 1 pipeline contracts — registry, CLI, MCP, LangGraph, Streamlit, events |

---

*End of PRD — v0.3 tranche 1.*
