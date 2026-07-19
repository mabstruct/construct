---
phase: 08-search-provider-spine-contract-foundation
plan: 02
subsystem: api
tags: [search, research.search, cli, mcp, workspace-config, pytest]

requires:
  - phase: 08-01
    provides: SearchConfig schema, SearchProviderFactory, MockSearchProvider, search.yaml template
provides:
  - WorkspaceLoader.load_search_config() with validation and init scaffolding
  - Read-only research.search PIPE handler returning normalized OperationResult
  - research.search capability registration with RT-03 shim and MCP auto-exposure
  - construct research search CLI command
affects: [08-03]

tech-stack:
  added: []
  patterns:
    - "search.yaml loaded via WorkspaceLoader parallel to model-routing.yaml"
    - "research.search read-only handler with cap enforcement and degraded SearchError mapping"
    - "RT-03 shim on ResearchSearchInput for CLI/MCP registry parity"

key-files:
  created:
    - src/construct/pipelines/research_search.py
    - tests/search/test_search_contract.py
  modified:
    - src/construct/storage/workspace.py
    - src/construct/services/validation.py
    - src/construct/services/init.py
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/search/test_search_config.py

key-decisions:
  - "AuthError messages redacted at handler boundary (T-8-05) — generic message returned to callers"
  - "Reserved ingest clusters (manual-ingest/web-ingest) allowed with explicit warning, not blocked"
  - "Query cap truncation emits warnings in output metadata rather than failing the request"

patterns-established:
  - "Invoke surface wiring: workspace config load → factory → read-only PIPE → registry → CLI/MCP"
  - "SOT immutability verified via SHA-256 snapshot of cards/refs/seeds/events before/after search"

requirements-completed: [SRCH-01, SRCH-02, SRCH-04]

duration: 12min
completed: 2026-06-21
---

# Phase 8 Plan 02: Search Invoke Surface Wiring Summary

**research.search callable via CLI and MCP through shared registry; search.yaml loads/validates/scaffolds; degraded provider errors return structured OperationResult with zero SOT writes**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-21T16:00:00Z
- **Completed:** 2026-06-21T16:12:06Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added `WorkspaceLoader.load_search_config()`, workspace validation block, and init template copy for `.construct/search.yaml`
- Implemented read-only `research_search()` PIPE with `ResearchSearchInput`/`ResearchSearchOutput` models
- Registered `research.search` capability with RT-03 shim; `construct_research_search` auto-exposes via MCP registry loop
- Added `construct research search` CLI with mutually exclusive query modes and JSON output
- Eleven search tests pass (config + contract); SOT file hashes unchanged after search invocation

## Task Commits

Each task was committed atomically:

1. **Task 1: Workspace config load, validation, and init template copy** - `b99c16c` (feat)
2. **Task 2: research.search handler, registry registration, and CLI command** - `196f965` (feat)

## Files Created/Modified

- `src/construct/storage/workspace.py` - `load_search_config()` reads `.construct/search.yaml`
- `src/construct/services/validation.py` - Validates search.yaml when present
- `src/construct/services/init.py` - Copies search.yaml template; documents support path
- `src/construct/pipelines/research_search.py` - Read-only search handler with cap/degraded error handling
- `src/construct/capabilities/catalog.py` - Registers `research.search` with `_research_search_shim`
- `src/construct/cli.py` - `research search` command group
- `tests/search/test_search_config.py` - Loader and validation error tests
- `tests/search/test_search_contract.py` - Handler, CLI, MCP, SOT immutability, rate-limit, ingest-warning tests

## Decisions Made

- AuthError messages redacted at handler boundary per T-8-05 — callers see generic auth failure text
- Reserved ingest clusters return success with warning rather than blocking search
- Batch query truncation surfaces warnings in output metadata

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - mock provider works offline with fixture directory configured in search.yaml.

## Next Phase Readiness

- Plan 08-03 can add Tavily adapter behind optional `[search]` extra
- `research.search` ready for Phase 9 scoring gate integration
- Existing workspaces need `.construct/search.yaml` copied manually or via re-init until migration tooling added

## Self-Check: PASSED

- FOUND: `.planning/phases/08-search-provider-spine-contract-foundation/08-02-SUMMARY.md`
- FOUND: `src/construct/pipelines/research_search.py`
- FOUND: `tests/search/test_search_contract.py`
- FOUND: commit `b99c16c`
- FOUND: commit `196f965`

---
*Phase: 08-search-provider-spine-contract-foundation*
*Completed: 2026-06-21*
