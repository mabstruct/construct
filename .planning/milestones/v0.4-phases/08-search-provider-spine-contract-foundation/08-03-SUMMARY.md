---
phase: 08-search-provider-spine-contract-foundation
plan: 03
subsystem: api
tags: [search, tavily, contract-tests, mcp, pytest, offline-testing]

requires:
  - phase: 08-02
    provides: research.search handler, CLI/MCP registration, search.yaml loading
provides:
  - Full offline contract test suite for research.search (normalized, seed cluster, CLI, degraded error)
  - MCP contract parity with construct_research_search (12 tools)
  - TavilySearchProvider adapter behind optional [search] extra with lazy SDK import
  - Offline Tavily response normalization unit tests
affects: [09-research-score, 10-research-run]

tech-stack:
  added: []
  patterns:
    - "Tavily SDK import isolated to providers/tavily.py with lazy _import_tavily_sdk()"
    - "normalize_tavily_response() pure function testable without network or SDK"
    - "overlay_mock_search_config() shared helper for MCP contract workspace fixtures"

key-files:
  created:
    - src/construct/search/providers/tavily.py
  modified:
    - src/construct/search/registry.py
    - tests/search/test_search_contract.py
    - tests/search/conftest.py
    - tests/search/test_search_provider_mock.py
    - tests/contract/test_mcp_contracts.py
    - tests/fixtures/expected-workspace-tree.txt
    - tests/unit/test_capability_registry.py

key-decisions:
  - "Tavily content field maps to snippet; default source_tier=3 per RESEARCH A3 heuristic"
  - "MCP workspace fixture overlays mock search.yaml so construct_research_search invokes offline"
  - "Normalization helpers exported for unit tests without requiring tavily-python install"

patterns-established:
  - "Contract tests invoke registry handler for normalized path; direct research_search for cluster/error cases"
  - "Regression gate: grep -r 'from tavily' src/construct/ must match exactly providers/tavily.py"

requirements-completed: [SRCH-01, SRCH-03, SRCH-04]

duration: 18min
completed: 2026-06-21
---

# Phase 8 Plan 03: Search Verification and Tavily Adapter Summary

**Offline contract suite covers research.search end-to-end; MCP parity at 12 tools; Tavily adapter isolated behind optional extra with pure normalization tests — 246 tests green**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-21T15:56:00Z
- **Completed:** 2026-06-21T16:14:41Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Completed `tests/search/test_search_contract.py` with seed cluster, CLI, degraded error, and registry-handler normalized coverage plus SOT immutability snapshots
- Updated MCP contract tests: `construct_research_search` in expected tool set (12 tools) with schema-shaped payload and mock search config overlay
- Implemented `TavilySearchProvider` with lazy SDK import, exception mapping, and `normalize_tavily_response()` helper
- Wired factory to instantiate Tavily when `default_provider: tavily`; raises `ProviderUnavailableError` when SDK not installed
- Full pytest regression: 246 passed (18 new search tests, zero regression)

## Task Commits

Each task was committed atomically:

1. **Task 1: Complete contract tests and MCP contract update** - `a70edc6` (test)
2. **Task 2: Tavily adapter, factory wiring, and full regression** - `0ec63d0` (feat)

## Files Created/Modified

- `src/construct/search/providers/tavily.py` - TavilySearchProvider with lazy import and response normalization
- `src/construct/search/registry.py` - Factory wires TavilySearchProvider for tavily default
- `tests/search/test_search_contract.py` - Seed cluster, CLI, degraded error, registry handler tests
- `tests/search/conftest.py` - `overlay_mock_search_config()` helper shared with MCP tests
- `tests/search/test_search_provider_mock.py` - Tavily normalization and unavailable-SDK factory tests
- `tests/contract/test_mcp_contracts.py` - 12-tool expected set and research_search payload
- `tests/fixtures/expected-workspace-tree.txt` - Added `.construct/search.yaml` from Plan 02 init
- `tests/unit/test_capability_registry.py` - Added `research.search` to expected capability IDs

## Decisions Made

- Tavily `content` → `snippet` mapping with default `source_tier=3` for search-time heuristic
- Pure `normalize_tavily_response()` exported for offline unit tests without SDK dependency
- MCP fixture copies overlay mock search config so handler tests stay network-free

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated init scaffold expected tree for search.yaml**
- **Found during:** Task 2 (full regression gate)
- **Issue:** Plan 02 added `.construct/search.yaml` to init but `expected-workspace-tree.txt` was stale
- **Fix:** Added `.construct/search.yaml` to expected workspace tree fixture
- **Files modified:** `tests/fixtures/expected-workspace-tree.txt`
- **Verification:** `test_construct_init_creates_full_workspace_scaffold` passes
- **Committed in:** `0ec63d0` (Task 2 commit)

**2. [Rule 3 - Blocking] Updated capability registry expected IDs**
- **Found during:** Task 2 (full regression gate)
- **Issue:** Plan 02 registered `research.search` but `test_catalog_loads` expected set was stale
- **Fix:** Added `research.search` to expected capability IDs
- **Files modified:** `tests/unit/test_capability_registry.py`
- **Verification:** `test_catalog_loads` passes; full suite 246 green
- **Committed in:** `0ec63d0` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking regression fixes from Plan 02 drift)
**Impact on plan:** Required for phase gate correctness; no scope creep.

## Issues Encountered

None beyond stale test fixtures from Plan 02 (auto-fixed above).

## User Setup Required

Optional live Tavily verification (manual-only per 08-VALIDATION.md):

- `pip install -e '.[search]'` to install tavily-python optional extra
- Set `TAVILY_API_KEY` from Tavily dashboard for live searches
- Default CI/offline path uses mock provider — no API key required

## Next Phase Readiness

- Phase 8 search spine complete: SRCH-01 through SRCH-04 satisfied with automated tests
- Phase 9 can integrate `research.score` on normalized search results
- Tavily adapter ready for manual live verification when `[search]` extra installed

## Self-Check: PASSED

- FOUND: `.planning/phases/08-search-provider-spine-contract-foundation/08-03-SUMMARY.md`
- FOUND: `src/construct/search/providers/tavily.py`
- FOUND: `tests/search/test_search_contract.py`
- FOUND: `tests/contract/test_mcp_contracts.py`
- FOUND: commit `a70edc6`
- FOUND: commit `0ec63d0`

---
*Phase: 08-search-provider-spine-contract-foundation*
*Completed: 2026-06-21*
