---
phase: 07-close-v0-3-blockers-rt-03-mcp-schema-parity-ing-02-ingest-cl
plan: 01
subsystem: api
tags: [mcp, capability-registry, adapter-shim, contract-test, graph-status]

# Dependency graph
requires:
  - phase: 03-capability-registry-mcp
    provides: capability registry + MCP server dispatch (handler(**kwargs))
  - phase: 05-runtime-pipeline-hardening
    provides: graph_status() pipeline, ask.domain/bridge.detect working adapter pattern
provides:
  - All five previously-broken MCP tool handlers (construct_validate, construct_create_card, construct_edit_card, construct_add_connection, construct_ingest_source) invoke without TypeError on their advertised schema fields
  - graph.status wired to the real graph_status() report (cards/connections/domains)
  - help.suggest surfaces graph-health data instead of swallowing it
  - handler-invocation contract test that gates the suite against RT-03 recurrence
affects: [mcp, ingest, graph-views, help-suggest]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual-mode capability shim: named module-level *_shim(*args, **kwargs) function that passes positional CLI calls straight through to the service fn and marshals keyword MCP calls into the service signature"

key-files:
  created:
    - tests/contract/test_mcp_contracts.py (extended with handler-invocation tests)
  modified:
    - src/construct/capabilities/catalog.py

key-decisions:
  - "Shims accept BOTH the CLI positional call form and the MCP keyword form; the registry handler is a shared dispatch point used by cli.py (positional, pre-marshalled) and the MCP server (keyword, schema fields)"
  - "graph.status handler signature is lambda workspace: graph_status(workspace) so a single param resolves both positional (help.py) and keyword (MCP) calls"
  - "help.py and the service layer (knowledge.py, validation.py, ingestion.py) were left unchanged — the fix is localized to catalog.py handler bindings"

patterns-established:
  - "Pattern: named dual-mode adapter shim instead of lambda **kwargs when a registry handler is invoked by both the CLI (positional) and MCP (keyword)"

requirements-completed: [RT-03, ING-05]

# Metrics
duration: 11min
completed: 2026-06-16
---

# Phase 7 Plan 01: Close RT-03 (MCP schema parity) + ING-05 (graph.status wiring) Summary

**Dual-mode adapter shims restore the five broken MCP knowledge-write tools, graph.status is wired to the real graph_status() report and surfaced in help.suggest, and a handler-invocation contract test now gates the suite against RT-03 recurrence.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-06-16T08:24:11Z (first task commit)
- **Completed:** 2026-06-16T08:29:59Z (last task commit)
- **Tasks:** 3
- **Files modified:** 2 (catalog.py, test_mcp_contracts.py)

## Accomplishments
- RT-03 closed: construct_validate, construct_create_card, construct_edit_card, construct_add_connection, construct_ingest_source all accept their advertised input_model fields and marshal into the real service signatures without TypeError.
- ING-05 closed: graph.status returns the real cards/connections/domains health report (no more "Not yet implemented" stub) and help.suggest surfaces it via the `graph_status` data key.
- D-08.1 done-gate: a contract test invokes every MCP tool handler with schema-shaped kwargs and fails on any TypeError — proven to genuinely exercise the handler path (reverting the shims reproduces the original TypeError).
- Full suite green: 218 passed (up from the 207 that were passing once the dual-mode regression was fixed).

## Task Commits

Each task was committed atomically:

1. **Task 1: RT-03 adapter shims for the five broken capabilities** - `522ad1e` (fix)
2. **Task 1 (Rule 1 follow-up): dual-mode shims accepting CLI positional + MCP keyword** - `2424d9d` (fix)
3. **Task 2: wire graph.status to graph_status() + surface in help.suggest** - `e07c650` (fix)
4. **Task 3: handler-invocation contract test (D-08.1)** - `e4d6c70` (test)

_Note: graph.status (Task 2) committed at e07c650 chronologically precedes the Task 1 Rule-1 follow-up (2424d9d), because the dual-mode regression was discovered during Task 3's full-suite run after Task 2 had already been committed._

## Files Created/Modified
- `src/construct/capabilities/catalog.py` - Added ConnectionType + graph_status imports; replaced raw/lambda handler bindings for workspace.validate, knowledge.card.create, knowledge.card.edit, knowledge.connection.add, ingest.source with named dual-mode shims; wired graph.status to graph_status(); added _build_card_data / _build_card_updates marshalling helpers.
- `tests/contract/test_mcp_contracts.py` - Added handler-invocation contract tests: iterate list_mcp_tools(), invoke each handler with schema-shaped kwargs and fail on TypeError; assert the five RT-03 tools return result objects; assert graph.status returns cards/connections/domains and accepts positional+keyword; assert help.suggest surfaces the graph_status key. Write-capable tools run against a tmp copy of test-ws/my-construct.

## Decisions Made
- The registry handler is a shared dispatch point: cli.py calls it positionally with already-marshalled args, while the MCP server calls it with keyword schema fields. The shims branch on `if args:` — positional → straight pass-through to the service fn; keyword → marshal then dispatch. This keeps the service layer and CLI untouched while making both surfaces work.
- graph.status uses `lambda workspace: graph_status(workspace)` so the single param binds for both positional (help.py:126) and keyword (MCP) callers.
- help.py was not modified — its existing success branch already assigns `graph_result.data` and adds `health["graph_status"]`; it works correctly now that the handler returns success=True.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RT-03 shims rejected the CLI's positional invocation**
- **Found during:** Task 3 (full-suite regression run after Tasks 1 and 2)
- **Issue:** The initial Task 1 shims were `lambda **kwargs:` (keyword-only). But the registry handlers are ALSO invoked positionally by the CLI — cli.py calls `handler(workspace, card_data, author=...)`, `handler(workspace, card_id, updates, author=...)`, `handler(workspace, from_id, to_id, ctype, ...)`, `handler(path)`, and `handler(workspace, source=...)`. The keyword-only shims raised `TypeError: <lambda>() takes 0 positional arguments but 2 were given`, breaking 11 CLI/integration tests.
- **Fix:** Converted the five shims to named dual-mode functions (`_validate_shim`, `_create_card_shim`, `_edit_card_shim`, `_add_connection_shim`, `_ingest_source_shim`). When invoked with positional args (CLI, pre-marshalled) they pass straight through to the service fn; when invoked with keyword schema fields (MCP) they marshal first. Service layer and CLI remained untouched.
- **Files modified:** src/construct/capabilities/catalog.py
- **Verification:** Full suite 218 passed (the 11 CLI failures resolved); contract test still green; manual probe confirms reverting the shims reproduces the original RT-03 TypeError.
- **Committed in:** 2424d9d

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1)
**Impact on plan:** The fix is essential for correctness — it preserves the existing CLI surface (a hard plan constraint: "do NOT touch the CLI") while delivering the new MCP keyword surface. No scope creep; the service layer and CLI signatures are unchanged as required.

## Issues Encountered
- During Task 3 a git-operation mistake while probing whether the CLI failures were pre-existing left the working tree on a detached HEAD and produced a stash-pop conflict on STATE.md. Recovered cleanly: both Task 1 and Task 2 commits were intact on the `v03ph01-feature` branch (522ad1e, e07c650); reattached to the branch, restored the contract test from a backup, and confirmed the catalog shims were present. No committed work was lost.
- The contract test's iteration invokes construct_ask_domain, which makes a live LLM call; it succeeds and is wrapped so only TypeError fails the gate. Non-TypeError runtime outcomes (provider errors, validation-failure results) are intentionally out of scope for the RT-03 signature gate.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RT-03 and ING-05 are closed; the agentic MCP knowledge-write path and graph-health reporting work at runtime.
- The remaining v0.3 blocker ING-02 (ingest cluster validation) is handled by a later plan in this phase.
- The `views.generate_data` capability remains a stub (explicitly out of scope for this plan).

## Known Stubs
- `views.generate_data` (catalog.py) still returns `OperationResult(success=False, message="Not yet implemented — see Plan 02")`. This is intentional and explicitly out of scope per the plan ("Leave `views.generate_data` stub untouched").

## Self-Check: PASSED

All claimed files exist (catalog.py, test_mcp_contracts.py, 07-01-SUMMARY.md) and all task commits are present in the repo (522ad1e, e07c650, 2424d9d, e4d6c70).

---
*Phase: 07-close-v0-3-blockers-rt-03-mcp-schema-parity-ing-02-ingest-cl*
*Completed: 2026-06-16*
