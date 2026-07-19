---
phase: 11-curation-pipe-steps
plan: 01
subsystem: testing
tags: [pytest, langgraph, curation, red-suite, nyquist, cli-mcp-parity]

# Dependency graph
requires:
  - phase: 10-research-run
    provides: durable research.run template (graph + SqliteSaver + run-id + dual-mode shim) the curation suite mirrors
provides:
  - Wave-0 failing pytest suite pinning the curation.run contract before any production code exists
  - tests/llm/test_curation_run.py — 8 node/graph/scan/status/no-write/anti-placeholder red tests
  - tests/contract/test_curation_run_cli_mcp.py — registry/MCP/CLI parity red tests + mcp-no-hardcoded GREEN guard
  - curation_workspace fixture + write_card created/last_verified params (additive)
affects: [11-02 curation_run module, 11-03 catalog/cli wiring, phase-12 curation gates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy in-body import of the unbuilt module so collection succeeds and tests fail RED on ImportError"
    - "Date-relative fixtures (date.today() - timedelta) so decay/orphan windows never drift"
    - "Contract test imports the result model lazily to keep the mcp-no-hardcoded guard GREEN pre-build"

key-files:
  created:
    - tests/llm/test_curation_run.py
    - tests/contract/test_curation_run_cli_mcp.py
    - .planning/phases/11-curation-pipe-steps/11-01-SUMMARY.md
  modified:
    - tests/llm/conftest.py

key-decisions:
  - "Curation fixtures write the canonical edge list at workspace-root connections.json (not connections/connections.json) to match WorkspaceLoader.load_connections"
  - "_initial_state mirrors research_run's single-arg form _initial_state(inp)"
  - "CUR-01 left INCOMPLETE — this is the red-suite plan; the requirement is satisfied only when Plans 02-03 land"

patterns-established:
  - "Pattern 1: lazy in-body import keeps a red suite collectable while failing on the missing module"
  - "Pattern 2: governance-threshold delta test (tight vs widened windows) proves D-05 wiring, not hardcoding"
  - "Pattern 3: no-canonical-writes snapshot scopes D-06 to cards/refs/connections.json/search-seeds.json, excluding derived log/ and views/"

requirements-completed: []  # CUR-01 intentionally NOT marked — red suite only; production lands in Plans 02-03

# Metrics
duration: 20min
completed: 2026-06-28
---

# Phase 11 Plan 01: Curation Wave-0 Red Suite Summary

**A collectable, intentionally-failing pytest suite that pins every CUR-01 distinction (real findings, completed-vs-degraded, skipped-deferred, threshold honoring, no-canonical-writes, anti-placeholder) as the executable spec for the curation.run module and its CLI/MCP wiring.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 completed
- **Files modified:** 3 (1 modified, 2 created; +1 SUMMARY)

## Accomplishments
- Extended `write_card` additively with `created`/`last_verified` params (byte-identical default output) and added the deterministic `curation_workspace` fixture (fresh + stale-orphan + stale-connected + stale-archived cards, plus one root `connections.json` edge for degree counting).
- Authored `tests/llm/test_curation_run.py` — 8 sampling-point tests covering full-run concrete findings, degraded-vs-completed aggregation, deferred-skip visibility, anti-placeholder, governance-threshold wiring, no-canonical-writes, auto-archive report-not-act, and inspect-no-rerun. All RED on the missing module; all collect cleanly via lazy in-body imports.
- Authored `tests/contract/test_curation_run_cli_mcp.py` — registry presence, positional-arg rejection, MCP auto-discovery, CLI presence, and CLI/MCP schema parity (offline, no `ANTHROPIC_API_KEY`). 6 RED (unwired) + 1 GREEN guard (`test_mcp_no_hardcoded_curation`) proving Plan 03 must not edit `mcp/server.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend conftest fixtures for decay/orphan determinism** - `1be3a4b` (test)
2. **Task 2: Write tests/llm/test_curation_run.py red suite** - `898e52e` (test)
3. **Task 3: Write tests/contract/test_curation_run_cli_mcp.py red suite** - `e05dc56` (test)

**Plan metadata:** this commit (docs)

## Files Created/Modified
- `tests/llm/conftest.py` - Added `created`/`last_verified` kwargs to `write_card` and the `curation_workspace` fixture (canonical root `connections.json`, date-relative stale anchors).
- `tests/llm/test_curation_run.py` - 8 red tests; the Nyquist sampling points for CUR-01 (lazy in-body imports of `construct.llm.curation_run`).
- `tests/contract/test_curation_run_cli_mcp.py` - CLI/MCP parity contract suite; `_CAPS` maps both curation capabilities to their MCP tool names.

## Contract Pinned (for Plans 02-03)
The suite is the executable spec for these public names Plan 02/03 must implement:
- `build_curation_run_graph(checkpointer)`, `_initial_state(inp)`, `run_curation_run(inp)`, `inspect_curation_run(inp)`
- `CurationRunInput(workspace_path, run_id=None)`, `CurationInspectInput(workspace_path, run_id)`
- `CurationStepResult(step, status, required, findings, summary, reason)`, `CurationRunResult(status, run_id, steps, events, message)`
- Capabilities `curation.run` → `construct_curation_run`, `curation.inspect` → `construct_curation_inspect`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Canonical connections path corrected to workspace root**
- **Found during:** Task 1
- **Issue:** The plan (Task 1 and Task 2) specified writing/snapshotting `connections/connections.json`, but `WorkspaceLoader.load_connections` and `init._write_connections` use `connections.json` at the workspace **root** (REQUIRED_PATHS, schemas/workspace.py). A fixture under `connections/` would be invisible to the Plan 02 orphan-scan, and the no-canonical-writes snapshot would guard the wrong path.
- **Fix:** Wrote the fixture edge to root `connections.json` and scoped `_snapshot_canonical` to root `connections.json`. Verified the fixture loads via `WorkspaceLoader.load_connections` (1 record) and passes `validate_workspace` (0 errors).
- **Files modified:** tests/llm/conftest.py, tests/llm/test_curation_run.py
- **Commit:** `1be3a4b`, `898e52e`

### Intentional Scope Note

**CUR-01 not marked complete.** This plan delivers only the failing test suite; the requirement ("receive real curation results") is satisfied when Plans 02-03 implement the module and wiring. `requirements.mark-complete` was deliberately skipped to avoid a false-complete signal.

## Verification
- `pytest tests/llm/test_curation_run.py -q` → 8 RED on the missing `construct.llm.curation_run` module (in-body ImportError, not collection error).
- `pytest tests/contract/test_curation_run_cli_mcp.py -q` → 6 RED (unwired registry/CLI) + 1 GREEN (`test_mcp_no_hardcoded_curation`).
- `pytest tests/llm/test_research_run.py -q` → 26 passed (additive conftest change broke nothing).
- `pytest --collect-only` on both new files → 15 tests collected, no collection errors.
- Greps confirm: "placeholder" appears only in the negative `not in` guard; no assertion references `log/` or `views/`.

## Self-Check: PASSED
- FOUND: tests/llm/test_curation_run.py
- FOUND: tests/contract/test_curation_run_cli_mcp.py
- FOUND: tests/llm/conftest.py (curation_workspace fixture)
- FOUND commit: 1be3a4b (Task 1)
- FOUND commit: 898e52e (Task 2)
- FOUND commit: e05dc56 (Task 3)
