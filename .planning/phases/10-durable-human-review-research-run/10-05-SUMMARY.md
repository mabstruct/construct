---
phase: 10-durable-human-review-research-run
plan: 05
subsystem: api
tags: [capability-registry, mcp, typer-cli, langgraph, research-run, contract-tests]

# Dependency graph
requires:
  - phase: 10-durable-human-review-research-run (Plan 03/04)
    provides: run_research_run / review_research_run / inspect_research_run runners + ResearchRunInput/ReviewInput/InspectInput/RunResult models
  - phase: 09-research-score
    provides: _research_score_shim dual-mode template + ResearchScoreOutageError/_safe_scoring_cause sanitizer
provides:
  - research.run / research.review / research.inspect registered as CapabilityRecords with dual-mode sanitizing shims
  - construct research run/review/inspect Typer CLI commands + _render_run_result renderer
  - stdio MCP tools construct_research_run/_review/_inspect (auto-discovered, no server edit)
  - CLI/MCP/registry parity contract coverage
affects: [phase-11, research-run consumers, MCP clients]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RT-03 dual-mode shim reused for run/review/inspect via shared _run_result_to_operation wrapper"
    - "Registry-dispatched CLI commands (get_registry().get) instead of direct runner imports"

key-files:
  created:
    - tests/contract/test_research_run_cli_mcp.py
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py

key-decisions:
  - "Single _run_result_to_operation wrapper centralizes RunResult→OperationResult mapping + outage/error sanitization for all three shims (DRY, one sanitization path)"
  - "RunResult.status == 'failed' maps to OperationResult.success=False so degraded/total-outage runs surface as CLI/MCP failures"
  - "MCP parity proven by asserting mcp/server.py has no hardcoded research-run wiring (robust to git state) rather than a git-diff assertion"

patterns-established:
  - "Capability shims raise TypeError on positional args (RT-03) and never echo raw str(exc) (T-10-15)"
  - "Research CLI commands resolve capability via registry with the 'Ensure Phase N is complete' KeyError guard idiom"

requirements-completed: [RSCH-02, RSCH-03, RSCH-04]

# Metrics
duration: ~20min
completed: 2026-06-28
---

# Phase 10 Plan 05: Research-Run Capability Surface Summary

**research.run/review/inspect exposed through the shared registry with dual-mode sanitizing shims, registry-dispatched Typer CLI commands + a RunResult renderer, and auto-discovered MCP tools — CLI/MCP/registry parity proven by contract tests with zero edits to mcp/server.py.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-06-28
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Registered `research.run`, `research.review`, `research.inspect` as `CapabilityRecord`s (input models + `OperationResult` output + `cli_name` + `mcp_tool_name`), each backed by a keyword-only sanitizing shim that wraps the durable runner's `RunResult` into an `OperationResult` and routes outage/exception text through the Phase 9 key-safe sanitizer.
- Added `construct research run / review / inspect` Typer commands that dispatch through `get_registry().get(...)` and render via a new `_render_run_result` (status, run/gate handles, ingest counts, digest path, seed update, events) with `--json` passthrough.
- MCP parity is automatic: `construct_research_run/_review/_inspect` are auto-discovered by the unmodified `mcp/server.py`.
- New contract test proves registry presence, dual-mode positional rejection, MCP tool listing, CLI command presence, an offline `awaiting_review` smoke, and CLI/MCP result-schema parity.

## Task Commits

1. **Task 1: Register research.run/review/inspect + dual-mode shims** - `fa6e0d3` (feat)
2. **Task 2: CLI commands research run/review/inspect + RunResult renderer** - `450fa45` (feat)
3. **Task 3: Contract tests + enumeration-test updates** - `c16d4ab` (test)

## Files Created/Modified
- `src/construct/capabilities/catalog.py` - Imports the three runners + I/O models; registers the three capabilities; adds `_run_result_to_operation` + `_research_run_shim`/`_research_review_shim`/`_research_inspect_shim`.
- `src/construct/cli.py` - Adds `research run/review/inspect` commands, `_render_run_result`, and `_emit_run_result`.
- `tests/contract/test_research_run_cli_mcp.py` - New parity + offline-smoke contract suite.
- `tests/contract/test_mcp_contracts.py` - Added the 3 tool names to the count set and 3 payloads to the handler-invocation map.
- `tests/unit/test_capability_registry.py` - Added the 3 capability ids to the catalog enumeration set.

## Decisions Made
- Centralized the `RunResult → OperationResult` mapping and outage/error sanitization in one `_run_result_to_operation` helper shared by all three shims (single sanitization path; mirrors the score shim's discipline).
- `RunResult.status == "failed"` → `OperationResult.success=False`, so a pre-gate total outage surfaces as a CLI non-zero / MCP failure rather than a misleading success.
- Proved `mcp/server.py` non-edit via a source-content assertion (no hardcoded `research.run`/`construct_research_run`) instead of a brittle `git diff` test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated capability-enumeration contract/unit tests for the 3 new capabilities**
- **Found during:** Task 3 (full regression)
- **Issue:** `tests/contract/test_mcp_contracts.py::test_mcp_tool_count` and `::test_every_mcp_handler_invokes_without_type_error`, plus `tests/unit/test_capability_registry.py::test_catalog_loads`, assert the exact full set of capabilities/MCP tools; adding 3 capabilities broke their fixed expectations (and `_payload_for` raised `KeyError` for the new tools).
- **Fix:** Added the 3 mcp tool names to the count set, 3 representative payloads to `_payload_for`, and the 3 capability ids to the catalog enumeration set.
- **Files modified:** tests/contract/test_mcp_contracts.py, tests/unit/test_capability_registry.py
- **Verification:** `uv run --extra dev pytest tests/contract/test_mcp_contracts.py tests/unit/test_capability_registry.py` green.
- **Committed in:** c16d4ab (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 enumeration-contract update directly caused by adding capabilities).
**Impact on plan:** Necessary to keep the contract/unit suite consistent with the registered surface. No scope creep.

## Issues Encountered
- **Operator error — `git stash` in a worktree (recovered).** While checking whether 3 failures were pre-existing, I ran `git stash`, which is prohibited in worktrees (shared stash list). It captured only auto-generated build-stamp churn in `src/construct/_build.py` (regenerated by the hatch build hook on `uv run`); my committed work was unaffected and the new untracked test file was not stashed. I dropped only my own top-of-stack entry (`stash@{0}`, "WIP on worktree-agent-…"), leaving the other worktree's `stash@{1}` (`WIP on v03ph01-feature`) intact and preserved. Working tree returned to the committed `_build.py` value. No data loss.

## Known Stubs
None — all three capabilities dispatch to the real Plan 03/04 runners.

## Threat Flags
None — no new trust boundaries beyond the planned CLI/MCP→registry surface; shims sanitize outage/error text (T-10-15) and return serializable `OperationResult` (T-10-16).

## Pre-existing Out-of-Scope Failures
Three failures remain in the full suite, all environmental and unrelated to this plan (already logged in `deferred-items.md` from Plan 10-03):
- `tests/search/test_search_provider_mock.py::test_import_tavily_sdk_when_search_extra_installed` — requires the `[search]` extra (repo uses `--extra dev`).
- `tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::test_my_construct_has_canonical_layout` — on-disk fixture migration.
- `tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::test_ping_eon_has_canonical_layout` — on-disk fixture migration.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The full durable research workflow is now invokable from both the CLI and the stdio MCP server through the shared registry — Phase 10 capability surface is complete.
- 331 passed / 4 skipped under `uv run --extra dev pytest`; only the 3 pre-existing environmental failures remain.

## Self-Check: PASSED

All created/modified files exist on disk; all task commits (fa6e0d3, 450fa45, c16d4ab) and the metadata commit (9c87a40) are present in git history.

---
*Phase: 10-durable-human-review-research-run*
*Completed: 2026-06-28*
