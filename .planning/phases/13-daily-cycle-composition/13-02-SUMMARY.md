---
phase: 13-daily-cycle-composition
plan: 02
subsystem: api
tags: [daily-run, capability-registry, cli, mcp-parity, contract-test]

# Dependency graph
requires:
  - phase: 13-daily-cycle-composition
    provides: run_daily_run / inspect_daily_run child entrypoints + DailyRunInput/DailyInspectInput/DailyRunResult models (Plan 01)
  - phase: 11-curation-pipe-steps
    provides: curation.run/inspect registry + Typer sub-app clone target (mechanical analog)
provides:
  - daily.run + daily.inspect CapabilityRecords (Pydantic I/O, handler, cli_name, mcp_tool_name)
  - _daily_result_to_operation + keyword-only _daily_run_shim/_daily_inspect_shim (degraded-exits-0 contract)
  - daily Typer sub-app (run/inspect) + _render_daily_result/_emit_daily_result
  - tests/contract/test_daily_run_cli_mcp.py (registration + CLI/MCP parity + no-hardcoded-MCP guard)
affects: [daily-cycle-skill, mcp-tool-surface]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry record + keyword-only shim clone of the curation quartet (D-08)"
    - "MCP parity is free via registry auto-discovery — mcp/server.py never edited"
    - "Degraded daily cycle maps to success=True; only status==failed → success=False (exit-code contract)"
    - "Inventory contract tests grown to include the two new MCP tools (test_mcp_tool_count / _payload_for / test_catalog_loads)"

key-files:
  created:
    - tests/contract/test_daily_run_cli_mcp.py
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py

key-decisions:
  - "daily.run/daily.inspect registered mirroring curation.run/inspect; workflow.run group NOT revived (D-08)"
  - "No daily.review record and no `daily review` CLI command — daily.run is non-blocking (D-01)"
  - "CLI dispatches ONLY through the registry handler (no direct run_daily_run import in cli.py)"
  - "mcp/server.py untouched — MCP tools auto-discovered from the registry (API-02 invariant, guarded by test_mcp_no_hardcoded_daily + git-diff check)"

patterns-established:
  - "New capability registration requires growing three inventory assertions in lockstep (test_mcp_tool_count expected-set, _payload_for map, test_catalog_loads expected_ids)"

requirements-completed: [API-01, API-02, API-03]

# Metrics
duration: 20min
completed: 2026-07-06
---

# Phase 13 Plan 02: Daily-Cycle Registration + CLI/MCP Parity Summary

**Registered `daily.run` + `daily.inspect` in the capability registry and exposed a `daily` Typer sub-app by mechanically cloning the curation quartet; MCP parity is free via registry auto-discovery (mcp/server.py untouched), proving API-01/02/03 with a cloned contract test.**

## Performance
- **Duration:** ~20 min
- **Tasks:** 3 (contract test RED-first → catalog registration → CLI sub-app)
- **Files created:** 1 | **Files modified:** 4

## Accomplishments
- `tests/contract/test_daily_run_cli_mcp.py`: seven contract tests (registration, keyword-only shim guard, MCP tool-list membership, MCP server exposure, no-hardcoded-MCP guard, CLI command presence, CLI/MCP schema+result parity) — all GREEN.
- `catalog.py`: `daily.run` + `daily.inspect` CapabilityRecords with `DailyRunInput`/`DailyInspectInput`, `OperationResult` output, `cli_name`, `mcp_tool_name`; `_daily_result_to_operation` + keyword-only `_daily_run_shim`/`_daily_inspect_shim`. Degraded status → `success=True` (degraded-exits-0 contract); any exception → `success=False` with a key-safe class-name message (T-13-07).
- `cli.py`: `daily` Typer sub-app with `run`/`inspect` commands dispatching through the registry handler (no direct `daily_run` import), plus `_render_daily_result`/`_emit_daily_result` mirroring the curation render/emit pair (parent status/run_id, per-child line, pending-escalation count, graph-health line).
- No `daily.review` record and no `daily review` command (D-01 — non-blocking, no parent pause).
- `mcp/server.py` unchanged — MCP tools `construct_daily_run`/`construct_daily_inspect` are auto-discovered from the registry (API-02); guarded by `test_mcp_no_hardcoded_daily` and a `git diff` check.

## Task Commits
1. **Task 1: Clone the daily contract test (RED for registration, GREEN guard for MCP)** - `c953758` (test)
2. **Task 2: Register daily.run + daily.inspect records and shims in catalog.py** - `cd3eda4` (feat)
3. **Task 3: Add the daily Typer sub-app (run/inspect) + grow inventory tests** - `1ca0078` (feat)

## Files Created/Modified
- `tests/contract/test_daily_run_cli_mcp.py` (created) - Registration + CLI/MCP parity + no-hardcoded-MCP contract tests (API-01/02/03).
- `src/construct/capabilities/catalog.py` (modified) - daily_run import block, two CapabilityRecords, `_daily_result_to_operation` + `_daily_run_shim`/`_daily_inspect_shim`.
- `src/construct/cli.py` (modified) - `daily_app` + `run`/`inspect` commands + `_render_daily_result`/`_emit_daily_result`.
- `tests/contract/test_mcp_contracts.py` (modified) - grew `test_mcp_tool_count` expected-set and `_payload_for` map with the two new tools.
- `tests/unit/test_capability_registry.py` (modified) - grew `test_catalog_loads` expected_ids with `daily.run`/`daily.inspect`.

## Decisions Made
- CLI/MCP schema-parity test runs fully offline (`monkeypatch.delenv("ANTHROPIC_API_KEY")`); each composed child isolates-and-degrades so the daily cycle still folds a `DailyRunResult`, keeping the parity assertion deterministic.
- Kept the shim identical in shape to `_curation_result_to_operation` so `mcp/server.py:_serialize_result` works unchanged and the degraded-exits-0 contract is preserved by the single `success = result.status != "failed"` line.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Grew MCP/registry inventory contract tests to include the two new capabilities**
- **Found during:** Task 3 (regression run after registration).
- **Issue:** `test_mcp_contracts.py::test_mcp_tool_count`, `test_mcp_contracts.py::test_every_mcp_handler_invokes_without_type_error`, and `test_capability_registry.py::test_catalog_loads` assert on the EXACT set of registered tools/capabilities. Adding `daily.run`/`daily.inspect` made these exact-match assertions fail — the same "inventory tests grown to match" pattern established in Phase 11-03.
- **Fix:** Added `construct_daily_run`/`construct_daily_inspect` to `test_mcp_tool_count`'s expected set and to the `_payload_for` payload map (`{"workspace_path": ws}` / `{"workspace_path": ws, "run_id": "no-such-run"}`), and added `daily.run`/`daily.inspect` to `test_catalog_loads`'s `expected_ids`.
- **Files modified:** `tests/contract/test_mcp_contracts.py`, `tests/unit/test_capability_registry.py`.
- **Commit:** `1ca0078` (bundled with the Task 3 CLI feat).

## Verification
- `python -m pytest tests/contract/test_daily_run_cli_mcp.py -q` → 7 passed (API-01/02/03).
- `git diff --name-only src/construct/mcp/server.py` → empty (server.py untouched; API-02 invariant).
- `construct daily --help` lists `run` + `inspect` only (no `review`).
- `grep -c "from construct.llm.daily_run import\|run_daily_run(" src/construct/cli.py` → 0 (CLI dispatches via registry).
- Full suite: 398 passed, 4 skipped, 2 pre-existing unrelated failures (see below).

## Issues Encountered
- **Pre-existing, out-of-scope (NOT fixed):** `tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::{test_my_construct_has_canonical_layout, test_ping_eon_has_canonical_layout}` fail in the worktree. Cause: the tests assert the on-disk fixtures contain empty `digests/` and `publish/` directories, but git cannot track empty directories, so a fresh worktree checkout lacks them (the main checkout has them as runtime-created dirs). This is a worktree-environment artifact unrelated to this plan's 5 changed files (none touch `test-ws/` or the migration test) and reproduces independently of the daily-cycle changes. Left untouched per the scope boundary.
- Worktree has no local `.venv`; ran the suite with the main repo's `.venv/bin/python` and `PYTHONPATH=<worktree>/src:<worktree>` so imports resolved against the worktree source (same approach as Plan 01).

## Known Stubs
None — the daily records wire the real `run_daily_run`/`inspect_daily_run` entrypoints end-to-end; no placeholder data paths.

## Threat Surface
- No new trust boundaries beyond the plan's threat model. T-13-05 (MCP surface drift) mitigated: `mcp/server.py` unchanged, guarded by `test_mcp_no_hardcoded_daily` + git-diff check. T-13-06 (positional-arg bypass) mitigated by the `if args: raise TypeError` shim guard, asserted by `test_shims_reject_positional_args`. T-13-07 (exception leakage) mitigated: `_daily_result_to_operation` reports `type(exc).__name__` only.

## Next Phase Readiness
- daily.run/daily.inspect are invokable from the CLI and the auto-discovered stdio MCP server. Ready for the daily-cycle skill migration (Plan 03) to delegate to `construct daily run` / `construct_daily_run` instead of any Claude-native orchestration.
- No blockers.

## Self-Check: PASSED
- `tests/contract/test_daily_run_cli_mcp.py` — FOUND
- `src/construct/capabilities/catalog.py` (daily records) — FOUND
- `src/construct/cli.py` (daily_app) — FOUND
- Commit `c953758` (test) — FOUND
- Commit `cd3eda4` (feat) — FOUND
- Commit `1ca0078` (feat) — FOUND

---
*Phase: 13-daily-cycle-composition*
*Completed: 2026-07-06*
