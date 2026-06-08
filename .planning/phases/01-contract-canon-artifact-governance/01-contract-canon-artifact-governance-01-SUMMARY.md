---
phase: 01-contract-canon-artifact-governance
plan: 01
subsystem: docs
tags: [workspace-contract, artifact-governance, validation, claude-native]
requires: []
provides:
  - Phase 1 canonical workspace contract for Claude-native CONSTRUCT
  - Aligned non-card schema inventory with explicit refs, search seeds, and event log coverage
  - Authority-set and contract-sync rules for downstream runtime and skill work
affects: [runtime-validators, templates, skills, migration-docs]
tech-stack:
  added: []
  patterns: [single-canonical-layout, pre-write-rejection-vs-post-write-audit, contract-sync-checklist]
key-files:
  created: [CONSTRUCT-CLAUDE-spec/workspace-contract.md]
  modified:
    - CONSTRUCT-CLAUDE-spec/data-schemas.md
    - CONSTRUCT-CLAUDE-spec/artifact-catalog.md
    - CONSTRUCT-CLAUDE-spec/validation-strategy.md
    - CONSTRUCT-CLAUDE-spec/process.md
key-decisions:
  - "Phase 1 canon is the Claude-native workspace layout, not the dormant Python-first layout."
  - "Invalid canonical artifacts are rejected before write; post-write checks handle audit, consistency, and fixture proof."
  - "The authority set is spec plus templates plus artifact catalog; runtime and skills must follow it."
patterns-established:
  - "Contract changes must update spec, templates, skills, runtime validators, fixture proof, and migration docs together."
requirements-completed: [FND-01, FND-03, FND-04]
duration: 1 min
completed: 2026-06-08
---

# Phase 01 Plan 01: Contract Canon Artifact Governance Summary

**Canonical Claude-native workspace contract with explicit artifact classes, authority rules, and write-gate boundaries for downstream v0.3 hardening work.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-08T22:05:25+02:00
- **Completed:** 2026-06-08T20:06:21Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `workspace-contract.md` as the single canonical workspace and artifact contract for Phase 1.
- Aligned `data-schemas.md` to the same artifact inventory, explicitly covering refs, search seeds, and the event log.
- Synced `artifact-catalog.md`, `validation-strategy.md`, and `process.md` to one authority set and one contract-change checklist.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the canonical workspace contract** - `1944175` (docs)
2. **Task 2: Sync authority and change-process documentation** - `2c3aa98` (docs)

**Plan metadata:** recorded in the final plan-artifacts commit

## Files Created/Modified
- `CONSTRUCT-CLAUDE-spec/workspace-contract.md` - Defines the canonical workspace layout, artifact classes, authority order, proof target, and sync obligations.
- `CONSTRUCT-CLAUDE-spec/data-schemas.md` - Aligns non-card schema coverage to the canonical artifact inventory and marks `digests/` and `publish/` as derived.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` - Names the Phase 1 authority set and states that runtime/skills must follow it.
- `CONSTRUCT-CLAUDE-spec/validation-strategy.md` - Splits pre-write rejection from post-write audit and adds an enforcement summary table.
- `CONSTRUCT-CLAUDE-spec/process.md` - Adds workspace-contract change rules and a contract-sync checklist spanning spec, templates, skills, runtime, fixtures, and migration docs.

## Decisions Made
- Use one canonical Claude-native workspace layout for Phase 1 instead of preserving the dormant Python-first layout as a parallel default.
- Classify `refs/*.json` and `log/events.jsonl` as canonical artifacts alongside cards, graph, and config artifacts.
- Treat `digests/` and `publish/` as derived artifacts, not source-of-truth graph inputs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced missing scripted verification with equivalent in-session checks**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** The plan-specified target `tests/unit/test_workspace_contracts.py` does not exist, and `python` is not available on PATH in this shell.
- **Fix:** Ran the prescribed commands to confirm the blocker, then executed explicit grep-based acceptance checks plus a `.venv/bin/python` one-off verification script covering the plan's required contract assertions.
- **Files modified:** None
- **Verification:** Acceptance grep checks passed; one-off verification script reported `ALL CHECKS PASSED`.
- **Committed in:** Not applicable

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope creep in repo contents. Verification was completed, but via an equivalent session-local check because the named pytest target is absent and AGENTS.md forbids editing `tests/` outside an explicit Python-track resume.

## Issues Encountered
- `python -m pytest tests/unit/test_workspace_contracts.py ...` failed because `python` is not on PATH.
- `.venv/bin/python -m pytest tests/unit/test_workspace_contracts.py ...` still failed because the target test file is missing from the repo.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The authoritative docs now agree on workspace shape, artifact classes, authority, and enforcement timing.
- Ready for `01-02-PLAN.md`, which can now reconcile runtime schemas and write gates to the locked contract.

## Self-Check: PASSED

- Found `CONSTRUCT-CLAUDE-spec/workspace-contract.md`
- Found commit `1944175`
- Found commit `2c3aa98`

---
*Phase: 01-contract-canon-artifact-governance*
*Completed: 2026-06-08*
