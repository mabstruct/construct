---
phase: 04-guided-workflow-operability
plan: 02
subsystem: "ingestion + help + cli-wiring"
tags:
  - ingestion-pipeline
  - help-service
  - cli
  - capability-registry
  - workflow-cli
requires:
  - 04-guided-workflow-operability-01
provides:
  - ING-01 (unified ingestion)
  - WF-01 (help --suggest)
  - workflow CLI commands
  - CLI integration test contracts
affects:
  - src/construct/cli.py
  - src/construct/capabilities/catalog.py
  - tests/contract/test_mcp_contracts.py
  - tests/unit/test_capability_registry.py
tech-stack:
  added:
    - "Python: dataclass-based OperationResult from knowledge.py"
  patterns:
    - "Capability registry delegation: get_registry().get('cap.id').handler(...)"
    - "Lazy import for circular dependency avoidance"
    - "WorkspaceLoader for workspace state analysis"
key-files:
  created:
    - src/construct/pipelines/ingestion.py
    - src/construct/services/help.py
    - tests/unit/test_ingestion.py
    - tests/unit/test_help.py
  modified:
    - src/construct/cli.py
    - src/construct/capabilities/catalog.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py
decisions:
  - "help CLI command function named help_cmd with @app.command(name='help') to avoid shadowing built-in"
  - "import get_registry inside suggest() body to break circular import"
  - "Note text stored as abstract field on ReferenceRecord (no dedicated note field)"
metrics:
  duration: ~45 min
  completed: 2026-06-10
  files_created: 4
  files_modified: 4
  tasks_completed: 3
  tests_passing: 126
---

# Phase 04 Plan 02: Ingestion + Help + CLI Wiring Summary

**One-liner:** Unified ingestion pipeline (file/URL/note/research) + workspace health suggestion engine + workflow/ingest/help CLI commands wired through capability registry.

---

## Objective

Deliver:
1. **ING-01**: Unified ingestion via `construct ingest <source>` with auto source type detection
2. **WF-01**: State-aware help via `construct help --suggest` consuming capability registry data
3. Workflow CLI commands (`construct workflow run/status/resume`) delegating to WorkflowRunner

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create unified ingestion pipeline | `c219bfc` | `src/construct/pipelines/ingestion.py` |
| 2 | Create help suggestion service | `a79bbf5` | `src/construct/services/help.py` |
| 3 | Wire CLI commands, register capabilities, add tests | `7119263`, `f67971c` | `cli.py`, `catalog.py`, test files |

## Key Implementation Details

### Ingestion Pipeline (`src/construct/pipelines/ingestion.py`)
- `detect_source_type()` classifies sources: `file` (existing path), `url` (http/https), `research:`, `note` (everything else)
- `ingest_source()` follows D-04 flow: capture → type → domain → ref record → seed card → log event
- URL sources create ReferenceRecord with URL and route to workspace domain
- Note/research sources store content as `abstract` on ReferenceRecord
- All refs validated through `validate_ref_write()` before writing
- Events logged via `append_event()` after each ingestion

### Help Suggestion Service (`src/construct/services/help.py`)
- `suggest()` analyzes workspace state returning structured JSON with priorities
- Domain scoring uses construct-help priority ordering:
  1. Empty domain (no cards/refs)
  2. Not interviewed (no categories/priorities)
  3. Cards but no connections
  4. Stale research (>7 days)
  5. Curation needed
  6. Healthy
- Consumes `graph.status` capability and `WorkflowRunner.status()` per D-08
- Lazy import of `get_registry` to avoid circular dependency

### CLI and Capability Registry
- 4 new capabilities registered in `catalog.py`: `workflow.run`, `workflow.status`, `ingest.source`, `help.suggest`
- All new capabilities have `mcp_tool_name` for MCP server auto-registration
- `_get_workflow_steps()` provides curation-cycle step definitions (placeholder handlers)
- `construct workflow run/status/resume` commands delegate to capability registry
- `construct ingest source` auto-detects source type and routes through ingestion pipeline
- `construct help --suggest` returns structured JSON with suggestions

---

## Deviations from Plan

### Auto-fixed Issues (Rule 1 — Bugs)

**1. [Rule 1 - Bug] ReferenceRecord has no `note` field**
- **Found during:** Task 1 (writing ingestion.py)
- **Issue:** Plan code used `note=note_text` when creating `ReferenceRecord` for notes, but `ReferenceRecord` uses `model_config = ConfigDict(extra="forbid")` and has no `note` field — would raise Pydantic ValidationError.
- **Fix:** Store note text as `abstract` field instead.
- **Files modified:** `src/construct/pipelines/ingestion.py`
- **Commit:** `c219bfc`

**2. [Rule 1 - Bug] ExtractionStatus has no `pending` value**
- **Found during:** Task 1 (writing ingestion.py)
- **Issue:** Plan code used `ExtractionStatus.pending` but the enum only contains `complete`, `partial`, `skipped`.
- **Fix:** Use `ExtractionStatus.partial` which semantically matches "ingested but not fully extracted".
- **Files modified:** `src/construct/pipelines/ingestion.py`
- **Commit:** `c219bfc`

### Auto-fixed Issues (Rule 2 — Missing Critical Functionality)

**3. [Rule 2 - Missing validation] ingest_source() doesn't check workspace exists**
- **Found during:** Task 1 verification
- **Issue:** `ingest_source('/nonexistent/workspace', 'test')` crashed with `FileNotFoundError` from `WorkspaceLoader` trying to read `domains.yaml` from a non-existent directory.
- **Fix:** Added `root.exists()` check before attempting workspace load, returning a clear OperationResult error with creation suggestion.
- **Files modified:** `src/construct/pipelines/ingestion.py`
- **Commit:** `c219bfc`

### Auto-fixed Issues (Rule 3 — Blocking)

**4. [Rule 3 - Blocking] Circular import between catalog.py and help.py**
- **Found during:** Task 3 verification
- **Issue:** `catalog.py` imports `help_suggest` from `help.py` at module level; `help.py` imported `get_registry` from `catalog.py` at module level — circular import.
- **Fix:** Moved `from construct.capabilities.catalog import get_registry` inside the `suggest()` function body (lazy import).
- **Files modified:** `src/construct/services/help.py`
- **Commit:** `7119263`

### Intentional Deviations

**5. help CLI function renamed to avoid built-in shadow**
- **Context:** `help` is a Python built-in. Using `def help(...)` would shadow it. Plan noted this possibility.
- **Action:** Named the function `help_cmd` and used `@app.command(name="help")`.
- **Files modified:** `src/construct/cli.py`
- **Commit:** `7119263`

## Test Results

```
126 passed, 2 warnings in 1.01s
```

Two pre-existing contract tests (`test_mcp_tool_count`, `test_catalog_loads`) were updated to include the 4 new capabilities and 3 new MCP tool names. All tests now pass.

---

## Verification Checklist

- [x] `ingest_source()` detects file/URL/note/research types
- [x] `ingestion pipeline creates ref records and seed cards
- [x] `suggest()` returns structured workspace health data with prioritized suggestions
- [x] Help suggestions follow construct-help priority ordering
- [x] `construct workflow run/status/resume` CLI commands wired via capability registry
- [x] `construct ingest source` CLI command wired via capability registry
- [x] `construct help --suggest` CLI command wired via capability registry
- [x] All 4 new capabilities registered in catalog with input models
- [x] All new capabilities have MCP tool names
- [x] Ingestion and help unit tests pass
- [x] Full test suite: 126 passed

---

## Self-Check: PASSED

- [x] `src/construct/pipelines/ingestion.py` exists (262 lines, ≥200)
- [x] `src/construct/services/help.py` exists (219 lines, ≥120)
- [x] `src/construct/cli.py` updated (464 lines, ≥450)
- [x] `src/construct/capabilities/catalog.py` updated (317 lines, ≥300)
- [x] `tests/unit/test_ingestion.py` exists (5 tests)
- [x] `tests/unit/test_help.py` exists (2 tests)
- [x] All 4 commits present in git log
- [x] Full test suite: 126 passed
