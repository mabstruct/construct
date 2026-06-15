---
phase: 03-capability-registry-cli-mcp-spine
plan: 01
type: execute
tags: [capability-registry, contract-surface, json-schema, mcp-tools, RT-01]
requires: [02-governed-knowledge-operations]
affects: [cli-registry-delegation, mcp-server]
key-files:
  created:
    - src/construct/capabilities/__init__.py
    - src/construct/capabilities/registry.py
    - src/construct/capabilities/catalog.py
    - tests/unit/test_capability_registry.py
  modified:
    - pyproject.toml
decisions:
  - "Capability registry uses a Pydantic-based CapabilityRecord model for capability definitions (D-01)"
  - "Input/output schemas reference existing Pydantic models directly rather than redefining them (D-02)"
  - "Handler dispatch uses direct callable references (D-03)"
  - "list_mcp_tools() derives JSON Schema via Pydantic model_json_schema() — single source of truth for CLI + MCP"
metrics:
  completed: "2026-06-12"
  tests: 9 (all passing)
  files_created: 4
  files_modified: 1
  note: "Retroactive summary — backfilled 2026-06-15 from plan, commits, and passing tests."
---

# Phase 03 Plan 01: Capability Registry Foundation Summary

Created the capability registry — the shared contract surface that both the CLI
and the MCP server build on. Every deterministic capability in CONSTRUCT is
defined once in the registry (id, description, input/output Pydantic models,
handler callable) and queried from there, satisfying requirement RT-01.

## Key Features

### Registry (`src/construct/capabilities/registry.py` — 68 lines)
- `CapabilityRecord` — Pydantic model holding id, description, input/output model refs, and the handler callable (D-01, D-02, D-03)
- `CapabilityRegistry` — register/get/list operations; enforces **unique capability IDs** (duplicate registration raises)
- `list_mcp_tools()` — emits MCP tool definitions, generating JSON Schema from each capability's Pydantic input model via `model_json_schema()`

### Catalog (`src/construct/capabilities/catalog.py` — 372 lines)
- `get_registry()` — returns the singleton registry pre-populated with all Phase 3 capabilities
- Input models for each capability (e.g. `IngestSourceInput`, validate, knowledge ops)
- The catalog grew over later phases as capabilities were added (`ask.domain` in 05-02, `bridge.detect` in 05-03) — the registration pattern established here is the extension point.

### Dependency
- `mcp>=1.0` declared in `pyproject.toml` (prereq for plan 03-03's server)

## Deviations from Plan

- `registry.py` is **68 lines vs the plan's `min_lines: 80`**. The deliverable is functionally complete (all must-have truths met); the target was simply generous. No scope was dropped.

## Verification Results

- ✅ 9 unit tests pass (`tests/unit/test_capability_registry.py`)
- ✅ Registry enforces unique IDs, lists MCP tools, generates JSON Schema from Pydantic models
- ✅ `mcp>=1.0` present in `pyproject.toml`

## Commits

| Commit | Description |
|--------|-------------|
| `f0a7ccd` | feat(v03ph01): capabilities registry (registry.py landed here) |
| `7119263`, `f364639`, `f6d918f` | incremental catalog registrations (CLI wiring 04-02, ask.domain 05-02, bridge.detect 05-03) |

> Note: Phase 3 work landed under broad `v03ph01` commits rather than per-plan commits, which is why this summary was backfilled rather than written at execution time.
