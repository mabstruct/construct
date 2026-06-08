---
phase: 01-contract-canon-artifact-governance
plan: 02
subsystem: runtime
tags: [pydantic, workspace-contract, validation, write-gates, init]
requires:
  - phase: 01-contract-canon-artifact-governance-01
    provides: canonical workspace and artifact authority set
provides:
  - Canonical runtime scaffold aligned to the Claude-native workspace contract
  - Pre-write validation helpers for cards, refs, connections, and events
  - Post-write audit checks for domain, graph, and search-seed consistency
affects: [cli-init, workspace-validation, fixture-tests, migration-proof]
tech-stack:
  added: []
  patterns: [canonical-workspace-scaffold, pre-write-artifact-gates, post-write-consistency-audit]
key-files:
  created:
    - tests/unit/test_workspace_contracts.py
    - tests/unit/test_artifact_write_gates.py
  modified:
    - src/construct/schemas/config.py
    - src/construct/schemas/workspace.py
    - src/construct/storage/workspace.py
    - src/construct/schemas/card.py
    - src/construct/services/init.py
    - src/construct/services/validation.py
    - tests/unit/test_schema_contracts.py
    - tests/unit/test_validation_service.py
key-decisions:
  - "Runtime domain data now lives inline in domains.yaml; archived per-domain YAML paths are no longer canonical."
  - "Pre-write validation helpers reject malformed cards, refs, connections, and events before persistence."
  - "Workspace init now scaffolds the canonical Claude-native layout and logs a workspace_init event."
patterns-established:
  - "Loader and validator code should classify `.construct/model-routing.yaml` as support, not canonical source-of-truth."
  - "Cross-file domain, search-cluster, and connection integrity checks belong to post-write audit paths."
requirements-completed: [FND-01, FND-02, FND-04]
duration: 8 min
completed: 2026-06-08
---

# Phase 01 Plan 02: Contract Canon Artifact Governance Summary

**Canonical runtime schemas, init scaffolding, and write gates now enforce the Phase 1 Claude-native workspace contract.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-08T20:15:58Z
- **Completed:** 2026-06-08T20:24:23Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Rebuilt workspace/config/runtime models around the canonical `cards/`, `refs/`, `domains.yaml`, `search-seeds.json`, and `log/events.jsonl` contract.
- Added deterministic pre-write validation helpers for cards, refs, connections, governance/search-seed payloads, and event-log appends.
- Reconciled workspace init and validation so canonical scaffolding, support-path handling, and cross-file audits all use the same artifact map.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild runtime contract models around the canonical workspace shape** - `848d430` (test), `9eb975e` (feat)
2. **Task 2: Add pre-write artifact rejection and init-path reconciliation** - `fe0f2fd` (test), `1b899ab` (feat)

**Plan metadata:** recorded in the final plan-artifacts commit

## Files Created/Modified
- `src/construct/schemas/config.py` - Replaces archived domain assumptions and adds canonical search-seed, ref, and event models.
- `src/construct/schemas/workspace.py` - Defines the canonical required, derived, and support paths used by the runtime scaffold.
- `src/construct/storage/workspace.py` - Loads canonical domains, search seeds, refs, events, and support-path model routing.
- `src/construct/schemas/card.py` - Adds a reusable card-validation helper for pre-write enforcement.
- `src/construct/services/init.py` - Scaffolds the active template-backed layout, writes canonical artifacts, seeds search clusters, and logs `workspace_init`.
- `src/construct/services/validation.py` - Separates pre-write artifact validation from post-write consistency auditing.
- `tests/unit/test_workspace_contracts.py` - Covers canonical scaffold paths, archived-path rejection, and loader/template round trips.
- `tests/unit/test_artifact_write_gates.py` - Covers pre-write rejection, canonical init layout, and post-write consistency reporting.
- `tests/unit/test_schema_contracts.py` - Updated legacy schema expectations to the Phase 1 canonical contract.
- `tests/unit/test_validation_service.py` - Updated legacy validation fixtures to the canonical workspace layout.

## Decisions Made
- Treat `.construct/model-routing.yaml` as support configuration rather than a canonical workspace artifact.
- Seed `search-seeds.json` during init from `DomainInitInput.research_seeds` so the canonical workspace starts with valid research steering data.
- Log `workspace_init` immediately in `log/events.jsonl` to satisfy the audit-trail contract for significant scaffold actions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used the repo virtualenv for verification commands**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** `python` is not available on PATH in this shell, so the plan's literal verification command could not run.
- **Fix:** Ran the equivalent commands with `.venv/bin/python`.
- **Files modified:** None
- **Verification:** `.venv/bin/python -m pytest tests/unit/test_workspace_contracts.py tests/unit/test_artifact_write_gates.py -x`
- **Committed in:** Not applicable

**2. [Rule 1 - Regression] Realigned legacy unit tests to the new canonical contract**
- **Found during:** Task 2 final verification
- **Issue:** Existing `tests/unit/test_schema_contracts.py` and `tests/unit/test_validation_service.py` still asserted archived runtime layout rules, causing the broader unit suite to fail after the contract reconciliation.
- **Fix:** Updated those tests to assert the Phase 1 canonical workspace shape and validation behavior.
- **Files modified:** `tests/unit/test_schema_contracts.py`, `tests/unit/test_validation_service.py`
- **Verification:** `.venv/bin/python -m pytest tests/unit -x`
- **Committed in:** `1b899ab`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 regression)
**Impact on plan:** Both fixes were required to complete verification against the canonical runtime contract. No product-scope creep.

## Issues Encountered
- `python -m pytest ...` could not run directly because this shell only exposes the project interpreter at `.venv/bin/python`.
- Legacy unit fixtures encoded the archived workspace layout and needed to be reconciled once the runtime contract changed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Runtime scaffold, loader, and validation boundaries now match the authoritative Phase 1 contract.
- Ready for `01-03-PLAN.md`, which can align skill/docs/migration work and prove the contract on fixture workspaces.

## Self-Check: PASSED

- Found `.planning/phases/01-contract-canon-artifact-governance/01-contract-canon-artifact-governance-02-SUMMARY.md`
- Found commits `848d430`, `9eb975e`, `fe0f2fd`, and `1b899ab`
