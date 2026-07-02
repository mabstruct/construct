---
phase: 12-curation-l3-gates-review-application
plan: 05
subsystem: api
tags: [capability-registry, typer-cli, mcp, curation, card-evaluate, hitl]

# Dependency graph
requires:
  - phase: 12 (Plan 02)
    provides: curation_promote.run_gate + CardEvaluateInput (L3 promotion gate)
  - phase: 12 (Plan 04)
    provides: curation_run.review_curation_run + CurationReviewInput (HITL review machine)
provides:
  - card.evaluate capability (construct_card_evaluate) registered with CLI + MCP parity
  - curation.review capability (construct_curation_review) registered with CLI + MCP parity
  - construct card evaluate + construct curation review Typer commands
  - curation.inspect description advertises pending-review (awaiting_review) state
  - legacy curation-cycle fake-success placeholder removed from catalog.py + cli.py
affects: [12-06 skill migration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Capability registration + dual-mode shim (CLI/MCP parity for free via registry auto-discovery)"
    - "card.evaluate shim mirrors research.score sanitizing error discipline (outage class + _safe_scoring_cause)"

key-files:
  created: []
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/unit/test_capability_registry.py
    - tests/contract/test_mcp_contracts.py

key-decisions:
  - "Open-Q 1: removed the workflow run/resume group + workflow.run capability entirely; curation.run is the sole canonical curation entrypoint (kept workflow.status — real state reader, no placeholder)"
  - "card.evaluate is surfaced as a dedicated top-level `construct card evaluate` group, not under `knowledge card` CRUD, to keep the promotion gate distinct from card CRUD"

patterns-established:
  - "New registry capabilities ripple into three exact-set inventory guards (test_catalog_loads, test_mcp_tool_count, _payload_for) — update them in lockstep"

requirements-completed: [CUR-02, CUR-03, CUR-05]

# Metrics
duration: ~25min
completed: 2026-07-02
---

# Phase 12 Plan 05: Expose L3 Gates + Excise Placeholder Summary

**card.evaluate + curation.review registered with CLI/MCP parity via the shim pattern, `construct card evaluate` / `construct curation review` commands added, and the D-10 curation-cycle fake-success placeholder removed atomically from catalog.py + cli.py.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-02
- **Completed:** 2026-07-02
- **Tasks:** 2
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments
- Registered `card.evaluate` (`construct_card_evaluate`, mirrors research.score) and `curation.review` (`construct_curation_review`, mirrors research.review) with `cli_name` + `mcp_tool_name`; both shims reject positional args and route through the sanitizing wrappers (`_card_evaluate_shim` uses the research.score outage discipline; `_curation_review_shim` uses `_curation_result_to_operation`).
- Extended `curation.inspect` description to advertise the pending-review (`awaiting_review`) gate queue.
- Added `construct curation review` (mirrors research review — decisions-file/stdin/approve-all/reject-all) and a dedicated top-level `construct card evaluate` command.
- Removed the D-10 curation-cycle placeholder (`_get_workflow_steps` in catalog.py + `_get_workflow_steps_from_registry` in cli.py) and the legacy `workflow.run` capability + `workflow run`/`workflow resume` CLI commands; no placeholder no-op is reachable from the registry or the CLI workflow group.
- `mcp/server.py` untouched — MCP parity is free via registry auto-discovery (`test_mcp_no_hardcoded_curation` stays GREEN).

## Task Commits

1. **Task 1: Register card.evaluate + curation.review; extend curation.inspect; add CLI commands** - `0857ad5` (feat)
2. **Task 2: Remove the curation-cycle placeholder lambdas from catalog.py + cli.py (D-10)** - `e580b00` (refactor)

## Files Created/Modified
- `src/construct/capabilities/catalog.py` - Registered card.evaluate + curation.review; added `_card_evaluate_shim` / `_curation_review_shim`; extended curation.inspect description; removed `_get_workflow_steps` and the `workflow.run` registration.
- `src/construct/cli.py` - Added `curation review` + top-level `card evaluate` commands; removed `_get_workflow_steps_from_registry`, `workflow run`/`workflow resume` commands, and the now-unused `WorkflowRunner` import.
- `tests/unit/test_capability_registry.py` - `test_catalog_loads` exact-set: added card.evaluate + curation.review, removed workflow.run.
- `tests/contract/test_mcp_contracts.py` - `test_mcp_tool_count` exact-set + `_payload_for`: added the two new MCP tools, removed construct_workflow_run.

## Decisions Made
- **Open-Q 1 (workflow group fate):** removed the `workflow run`/`workflow resume` commands and the `workflow.run` capability entirely rather than redirecting. Rationale: their only real content was the fake-success placeholder; `curation.run` is now the sole canonical curation path. `workflow.status` is retained because it reads genuine persisted WorkflowRunner state (used by help.py) and carries no placeholder.
- **card.evaluate CLI surface:** exposed as a dedicated top-level `construct card evaluate` group (`card_gate_app`) rather than under the `knowledge card` CRUD group, matching the contract test's `["card", "evaluate"]` expectation and keeping the promotion gate conceptually separate from card CRUD.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated three registry-inventory guards for the two new capabilities**
- **Found during:** Task 1 (registration)
- **Issue:** `test_catalog_loads` and `test_mcp_tool_count` use exact-set equality over registered IDs / MCP tool names, and `_payload_for` looks up a payload per MCP tool via `payloads[tool_name]`. Adding card.evaluate + curation.review broke all three (two AssertionErrors + one KeyError) — the plan touches only catalog.py/cli.py but the full-suite-green mandate requires these inventory guards to stay accurate.
- **Fix:** Added `card.evaluate`/`curation.review` to `test_catalog_loads`, `construct_card_evaluate`/`construct_curation_review` to `test_mcp_tool_count`, and payloads for both new MCP tools to `_payload_for`.
- **Files modified:** tests/unit/test_capability_registry.py, tests/contract/test_mcp_contracts.py
- **Verification:** `tests/unit/test_capability_registry.py` + `tests/contract/test_mcp_contracts.py` all GREEN.
- **Committed in:** 0857ad5 (Task 1 commit)

**2. [Rule 3 - Blocking] Removed workflow.run / construct_workflow_run from the same inventory guards**
- **Found during:** Task 2 (placeholder removal)
- **Issue:** Removing the `workflow.run` capability (Open-Q 1 resolution) broke the exact-set inventory guards that still listed `workflow.run` / `construct_workflow_run`.
- **Fix:** Dropped `workflow.run` from `test_catalog_loads`, and `construct_workflow_run` from both `test_mcp_tool_count` and `_payload_for`.
- **Files modified:** tests/unit/test_capability_registry.py, tests/contract/test_mcp_contracts.py
- **Verification:** Inventory guards GREEN; full suite shows no regression.
- **Committed in:** e580b00 (Task 2 commit)

**3. [Rule 2 - Missing Critical] Added the `construct card evaluate` CLI command**
- **Found during:** Task 1 (CLI commands)
- **Issue:** The plan's Task 1 action text named only the `curation review` command, but the contract file's `test_cli_commands_present` also asserts `construct card evaluate --help` exits 0, and the prompt requires the whole file GREEN. The existing `card` group is nested under `knowledge`, so a top-level `card evaluate` did not exist.
- **Fix:** Added a dedicated top-level `card` Typer group (`card_gate_app`) hosting `evaluate`, wired to the `card.evaluate` capability.
- **Files modified:** src/construct/cli.py
- **Verification:** `construct card evaluate --help` exits 0; `test_cli_commands_present` GREEN.
- **Committed in:** 0857ad5 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (3 blocking — 1 also missing-critical CLI surface)
**Impact on plan:** All auto-fixes are necessary consequences of the plan's required capability additions / placeholder removal and the full-suite-green mandate. No scope creep — no behavior beyond the plan's stated surface was added.

## Issues Encountered
- Initial `card evaluate` command was placed under the `knowledge card` group (nested), so `construct card evaluate` resolved to exit code 2. Resolved by introducing a top-level `card` group.
- The anti-placeholder contract test greps the raw source text for the literal `_get_workflow_steps`; explanatory comments that named the symbol initially failed the assertion. Reworded both comments to describe the removal without repeating the symbol name.

## TDD Gate Compliance
Not a TDD plan (`type: execute`). The contract tests (test_registered, test_no_placeholder_curation_path, test_cli_commands_present) were pre-authored RED and driven GREEN by this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- card.evaluate + curation.review are on the canonical CLI/MCP surface, ready for Plan 12-06 skill migrations to delegate to `construct card evaluate` / `construct curation review`.
- **Known RED (expected, owned by Plan 12-06):** `tests/contract/test_skill_migration.py::test_skill_drops_forbidden_tools[construct-research-cycle]` — the `construct-research-cycle` SKILL.md still allows `WebSearch`/`WebFetch`. This is Plan 12-06's responsibility, not a regression from this plan (the `construct-curation-cycle` and `construct-card-evaluate` skill cases already pass).

## Self-Check: PASSED
- catalog.py + cli.py modified, imports clean (`import construct.cli, construct.capabilities.catalog` → IMPORT-OK).
- `grep -rn "_get_workflow_steps" src/construct/` → no matches.
- Commits `0857ad5` and `e580b00` present in `git log`.
- Full suite: 388 passed, 1 failed (the expected Plan 12-06 skill_migration RED); mcp/server.py untouched.

---
*Phase: 12-curation-l3-gates-review-application*
*Completed: 2026-07-02*
