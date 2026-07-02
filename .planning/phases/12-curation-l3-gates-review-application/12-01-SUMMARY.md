---
phase: 12-curation-l3-gates-review-application
plan: 01
subsystem: testing
tags: [pytest, langgraph, hitl, curation, l3-gate, red-suite, wave-0]

# Dependency graph
requires:
  - phase: 09-research-score-l3-gate
    provides: research_score.py gate skeleton (score_one/score_all/run_gate/outage sanitizer) mirrored by the curation gates
  - phase: 10-research-run-durable-workflow
    provides: research_run.py interrupt/resume/review/inspect HITL machine mirrored by the curation-run integration tests
  - phase: 11-curation-run-deterministic
    provides: curation_run.py deterministic graph + CurationRunResult/CurationRunInput/inspect the new tests extend
provides:
  - Wave-0 RED test scaffold for every Phase 12 later-wave verify target
  - card.evaluate + connection-typing gate unit tests (CUR-02, D-05)
  - curation.run HITL + reviewed-write + no-unreviewed-write integration tests (CUR-03/04/05)
  - curation.review + card.evaluate CLI/MCP parity + no-placeholder contract tests (CUR-05, API parity)
  - API-04 skill-migration forbidden-tool guard
  - PromotionDecision / ConnectionTypeDecision mock-seam fixtures
affects: [12-02-card-evaluate-gate, 12-03-curation-run-hitl, 12-04-reviewed-writes, 12-05-registration-cli, 12-06-skill-migration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-now/GREEN-later Nyquist scaffold: lazy imports inside test bodies so absent modules do not abort collection"
    - "Single build_chat_model seam driving two L3 gates via a class-routing mock (_GateRoutingMock)"
    - "allowed-tools frontmatter-line static guard for skill migration"

key-files:
  created:
    - tests/llm/test_curation_promote.py
    - tests/contract/test_skill_migration.py
  modified:
    - tests/llm/conftest.py
    - tests/llm/test_curation_run.py
    - tests/contract/test_curation_run_cli_mcp.py

key-decisions:
  - "test_curation_promote.py uses lazy per-test imports (not top-level) because the repo runs pytest without --continue-on-collection-errors; a top-level missing import aborts the whole session"
  - "Integration tests drive the future gates through the factory.build_chat_model seam with a class-routing mock, so one run can exercise both the promotion and connection gates"
  - "Skill guard reads only the allowed-tools frontmatter line (not prose body) to avoid false positives on legitimate tool mentions"

patterns-established:
  - "Lazy-import RED suite: import the not-yet-existing module inside each test body / builder so the file collects and only fails at run time"
  - "Gate-routing mock: dispatch on with_structured_output(model_class).__name__ to serve PromotionDecision vs ConnectionTypeDecision from one seam"

requirements-completed: []  # CUR-02..05 + API-04 are turned GREEN in Plans 02-06; this plan only authors their RED targets

# Metrics
duration: ~35min
completed: 2026-07-02
---

# Phase 12 Plan 01: Wave-0 Curation L3 Gate + Review RED Scaffold Summary

**Authored the full Wave-0 failing-test net for Phase 12 — card.evaluate/connection-typing gate units, curation.run HITL + no-unreviewed-write integration tests, CLI/MCP parity + no-placeholder contract guards, and the API-04 skill forbidden-tool guard — all RED now and each a named GREEN target for Plans 02-06, with zero production code touched.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-02T06:26Z
- **Completed:** 2026-07-02T07:01Z
- **Tasks:** 3 (plus 1 blocking-fix deviation)
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- New `tests/llm/test_curation_promote.py` mirrors `test_research_score.py`: decision-mapping (promote/hold/escalate), D-02 candidate pre-filter, `test_failure_escalates` (retry→escalate + `method="rule-based"`), retry-then-succeed keeps `llm-judgment`, total-outage discrimination, `run_gate` raises `CardEvaluateOutageError`, verbatim key-leak sanitizer test (T-12-01), and connection-typing enum assignment (D-05).
- Extended `tests/llm/test_curation_run.py` mirroring `test_research_run.py` with the CUR-03 spine (`test_no_writes_before_approval`), reviewed promotion/connection/archive writes, `test_single_consolidated_gate`, `test_empty_queue_no_pause`, `test_no_unreviewed_writes`, `test_cross_process_resume`, `test_inspect_pending_review`, `test_curation_events_emitted`.
- Extended `tests/contract/test_curation_run_cli_mcp.py` `_CAPS` with `curation.review` + `card.evaluate`, added `test_no_placeholder_curation_path` (D-10), kept `test_mcp_no_hardcoded_curation` green.
- New `tests/contract/test_skill_migration.py` (API-04) asserts no `WebSearch`/`WebFetch`/`Write`/`Edit` survive in the three migrated skills' `allowed-tools`.
- Added `PromotionDecision`/`ConnectionTypeDecision` mock-seam fixtures to `tests/llm/conftest.py` without breaking existing collection.

## Task Commits

Each task was committed atomically:

1. **Task 1: Mock seams + card.evaluate / connection-typing gate unit tests** - `44b38ee` (test)
2. **Task 2: Curation-run HITL + reviewed-write integration tests** - `0396251` (test)
3. **Task 3: CLI/MCP parity + no-placeholder + skill-migration guards** - `82eca00` (test)

**Deviation fix:** `8e58630` (fix — lazy-import refactor of `test_curation_promote.py`)

## Files Created/Modified
- `tests/llm/conftest.py` - Added `promotion_decision_mock` / `connection_type_decision_mock` fixture builders (lazy-import the Plan-02 gate models over the existing `ConfigurableStructuredMock`).
- `tests/llm/test_curation_promote.py` - NEW. CUR-02/D-05 gate unit tests (13 tests, all RED pending Plan 02).
- `tests/llm/test_curation_run.py` - Extended with 10 HITL/reviewed-write integration tests (RED pending Plans 03-04); existing 8 Phase-11 tests unaffected.
- `tests/contract/test_curation_run_cli_mcp.py` - Extended `_CAPS` + `test_cli_commands_present`; added `test_no_placeholder_curation_path`.
- `tests/contract/test_skill_migration.py` - NEW. API-04 `allowed-tools` frontmatter guard for the three migrated skills.

## RED-Status Confirmation (per plan verify blocks)

| New test file | Verify signal | Result |
|---------------|---------------|--------|
| `tests/llm/test_curation_promote.py` | collects; 13 tests fail on lazy `ModuleNotFoundError: construct.llm.curation_promote/curation_connect` | RED-OK |
| `tests/llm/test_curation_run.py` | 10 new tests fail (ModuleNotFoundError on gate seam / missing `review_curation_run` / interrupt-only assertion); 8 existing pass | RED-OK |
| `tests/contract/test_curation_run_cli_mcp.py` | 6 fail (unregistered `curation.review`/`card.evaluate`; placeholder still present); `test_mcp_no_hardcoded_curation` stays green | RED-OK |
| `tests/contract/test_skill_migration.py` | `construct-research-cycle` fails (still carries WebSearch/WebFetch); other two skills pass | RED-OK |

**Existing suites:** `pytest tests/ -q` → **30 failed (all four Phase-12 files only), 359 passed**, no collection abort, no regressions in unrelated suites.

## Decisions Made
- Used lazy per-test imports in `test_curation_promote.py` (matching the `test_research_run.py` convention) rather than top-level imports, because the repo runs pytest without `--continue-on-collection-errors`.
- Drove the future L3 gates through the `factory.build_chat_model` monkeypatch seam with a class-routing mock so a single seam serves both `PromotionDecision` and `ConnectionTypeDecision`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Refactored test_curation_promote.py to lazy imports**
- **Found during:** Overall verification (plan verify step 2)
- **Issue:** The file's top-level `from construct.llm.curation_promote import ...` (module absent until Plan 02) raised `ModuleNotFoundError` at collection time. The repo runs pytest without `--continue-on-collection-errors`, so this **interrupted the entire `pytest tests/` session** — blocking all 359 existing green tests and violating the plan's verification step 2 ("no new collection errors from unrelated suites").
- **Fix:** Moved the `curation_promote` / `curation_connect` imports into each test body and the raw-decision builders, matching the established RED-suite convention in `test_research_run.py` / `test_curation_run.py`. The file now collects cleanly and each test errors at run time (still RED).
- **Files modified:** `tests/llm/test_curation_promote.py`
- **Verification:** `pytest tests/ -q` → 30 failed / 359 passed, no collection interruption; Task 1 verify grep still returns `RED-OK`.
- **Committed in:** `8e58630`

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** Necessary to satisfy the plan's own verification contract (existing green tests must stay runnable). No scope creep — still tests-only, no production code, RED preserved.

## Issues Encountered
- None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Every Plan 02-06 implementation task now has a named, currently-RED test to turn GREEN:
  - Plan 02 → `test_curation_promote.py` (gate modules `curation_promote` / `curation_connect`).
  - Plan 03-04 → `test_curation_run.py` HITL/reviewed-write tests (`awaiting_review` status, `gate_queue`/`gate_id` fields, `review_curation_run`, interrupt-only pause node, post-gate apply nodes).
  - Plan 05 → `test_curation_run_cli_mcp.py` (`curation.review` + `card.evaluate` registration, `_get_workflow_steps` deletion).
  - Plan 06 → `test_skill_migration.py` (`construct-research-cycle` frontmatter migration).
- `wave_0_complete` in 12-VALIDATION.md can flip true (Wave-0 tests landed).

## Self-Check: PASSED

All created/modified files present on disk; all four task commits (`44b38ee`, `0396251`, `82eca00`, `8e58630`) found in git history.

---
*Phase: 12-curation-l3-gates-review-application*
*Completed: 2026-07-02*
