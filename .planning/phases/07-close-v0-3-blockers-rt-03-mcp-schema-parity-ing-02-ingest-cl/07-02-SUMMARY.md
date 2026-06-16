---
phase: 07-close-v0-3-blockers-rt-03-mcp-schema-parity-ing-02-ingest-cl
plan: 02
subsystem: ingestion
tags: [search-clusters, validation, ingest, search-seeds, e2e]

# Dependency graph
requires:
  - phase: 04
    provides: "construct ingest source CLI entry point for ref/seed card creation"
provides:
  - "Reserved manual-ingest and web-ingest SearchCluster entries seeded at every workspace init"
  - "Reserved clusters backfilled into the test-ws/my-construct and test-ws/ping-eon fixtures"
  - "ingest source -> validate passes E2E without weakening write-time validation"
affects: [ingestion, validation, fixtures]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Template placeholder domain rewritten to the workspace domain at init (init.py:_write_search_seeds)"
    - "research_seeds override APPENDS the domain seed cluster rather than replacing reserved clusters"

key-files:
  created:
    - tests/integration/test_ingest_validate_e2e.py
  modified:
    - CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json
    - src/construct/services/init.py
    - test-ws/my-construct/search-seeds.json
    - test-ws/ping-eon/search-seeds.json
    - tests/unit/test_schema_contracts.py
    - tests/unit/test_validation_service.py
    - tests/unit/test_workspace_contracts.py

key-decisions:
  - "Reserved clusters' domain is rewritten to the workspace domain at init time (template uses a placeholder 'ingest' domain) because validation.py:148 cross-checks each cluster.domain against domains.yaml — contrary to the plan's interface note, the domain IS cross-checked"
  - "research_seeds override now appends the domain seed cluster instead of replacing payload['clusters'], so research-seeded workspaces retain the reserved clusters"
  - "Fixture reserved clusters reuse an existing domain (cosmology / api-gateways) rather than a new 'ingest' domain, to satisfy the same cross-check without touching domains.yaml"

patterns-established:
  - "Make ingest data conform to the validation gate (seed clusters) rather than weakening the gate — validation.py and ingestion.py unchanged"

requirements-completed: [ING-02]

# Metrics
duration: 18min
completed: 2026-06-16
---

# Phase 07 Plan 02: Close ING-02 (ingest cluster validation) Summary

**Seeded reserved manual-ingest/web-ingest search clusters at init and in both test-ws fixtures so governed `ingest source` -> `validate` passes E2E, with validation.py:205 and the ingestion fallback names left strict and unchanged.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-16T11:00Z
- **Completed:** 2026-06-16T11:18Z
- **Tasks:** 3
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments
- Init template seeds two reserved SearchCluster entries (`manual-ingest`, `web-ingest`); init.py rewrites their placeholder domain to the workspace's own domain and appends rather than drops them under the research_seeds override.
- Both fixtures (`test-ws/my-construct`, `test-ws/ping-eon`) carry the reserved clusters reusing an existing domain; existing domain clusters preserved; both validate with zero errors.
- New E2E test reproduces the ING-02 audit repro (ingest note + URL into an isolated tmp_path copy, then validate -> zero errors). Full suite: 221 passed.
- ingestion.py and validation.py untouched — the data conforms to the gate, the gate stays strict.

## Task Commits

1. **Task 1: Seed reserved manual-ingest/web-ingest clusters at init** - `cd3f2e7` (feat)
2. **Task 2: Backfill reserved clusters into test-ws fixtures** - `16779a5` (fix)
3. **Task 3: Ingest-then-validate E2E test + contract test updates** - `97fba61` (test)

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified
- `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json` - Now seeds reserved manual-ingest/web-ingest clusters (placeholder domain "ingest", rewritten at init).
- `src/construct/services/init.py` - `_write_search_seeds` rewrites reserved cluster domains to the workspace domain and appends the research seed cluster instead of replacing.
- `test-ws/my-construct/search-seeds.json` - Reserved clusters added (domain cosmology); existing domain clusters preserved.
- `test-ws/ping-eon/search-seeds.json` - Reserved clusters added (domain api-gateways); existing domain cluster preserved.
- `tests/integration/test_ingest_validate_e2e.py` - New E2E (note + URL ingest -> validate passes; fixture-not-mutated guard).
- `tests/unit/test_schema_contracts.py` - Template round-trip now expects the reserved clusters.
- `tests/unit/test_workspace_contracts.py` - Canonical-workspace round-trip now expects the reserved clusters.
- `tests/unit/test_validation_service.py` - `_write_valid_workspace` mirrors init by rewriting reserved clusters' domain to its single domain.

## Decisions Made
- Plan interface note (line 66) was wrong: validation.py:148 DOES cross-check each `cluster.domain` against domains.yaml. A fixed "ingest" domain in the written file would fail validation for every init'd workspace. Resolved by rewriting the reserved clusters' domain to the workspace domain at init, and reusing an existing domain in each fixture.
- Kept `validate_search_seeds_write(payload)` in the init path; reserved clusters conform to SearchCluster (kebab-case id/domain, weight 0.0, status active).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reserved cluster domain must match the workspace domain, not a fixed "ingest"**
- **Found during:** Task 1 (seeding the init template)
- **Issue:** The plan specified `domain: "ingest"` for the reserved clusters and claimed (interface note) that the cluster's own domain is not cross-checked. In fact validation.py:148-152 errors when `cluster.domain not in valid_domains`. A literal "ingest" domain would make every freshly-init'd workspace fail validation with "cluster 'manual-ingest' references unknown domain 'ingest'".
- **Fix:** Kept the template's placeholder `"ingest"` domain (so the file literally contains `manual-ingest`/`web-ingest` per the must_have artifact) but rewrite each reserved cluster's `domain` to `domain.domain_id` inside `_write_search_seeds`. In the fixtures, used an existing domain (cosmology / api-gateways).
- **Files modified:** src/construct/services/init.py, test-ws/my-construct/search-seeds.json, test-ws/ping-eon/search-seeds.json
- **Verification:** Init'd workspaces (with and without research_seeds) validate with zero errors; both fixtures validate with zero errors.
- **Committed in:** cd3f2e7, 16779a5

**2. [Rule 3 - Blocking] Update contract tests to reflect the seeded template**
- **Found during:** Task 3 (running the full suite)
- **Issue:** Three contract/round-trip tests asserted the template search-seeds.json has `clusters == []`, and `_write_valid_workspace` copied the template verbatim into a single-domain workspace, producing the unknown-domain error. These broke as a direct result of the intended Task 1 behavior change.
- **Fix:** Updated the two template round-trip assertions to expect `{manual-ingest, web-ingest}`; made `_write_valid_workspace` mirror init by rewriting the reserved clusters' domain to its `example-domain`.
- **Files modified:** tests/unit/test_schema_contracts.py, tests/unit/test_workspace_contracts.py, tests/unit/test_validation_service.py
- **Verification:** Full suite 221 passed.
- **Committed in:** 97fba61

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both auto-fixes were necessary for correctness — the plan's stated "ingest" domain would have re-broken validation. No scope creep; ingestion.py and validation.py remain untouched and strict.

## Issues Encountered
- None beyond the deviations above. The plan's interface note about domain cross-checking was inaccurate; corrected during execution.

## Threat Model Compliance
- T-07-03 (weakening validation): Honored — validation.py:205 unchanged; an unseeded cluster on a ref still errors. Fix seeds the data, not the gate.
- T-07-04 (reserved cluster id collision): Reserved kebab ids manual-ingest/web-ingest; domain seed clusters use `<domain>-seed` naming. No collision.
- T-07-SC (package installs): No new packages installed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ING-02 closed. Plan 03 (last plan of Phase 07) is next.

## Self-Check: PASSED

- All created/modified files present on disk (template, init.py, both fixtures, E2E test, SUMMARY).
- All three task commits found in git history (cd3f2e7, 16779a5, 97fba61).
- Full suite: 221 passed.

---
*Phase: 07-close-v0-3-blockers-rt-03-mcp-schema-parity-ing-02-ingest-cl*
*Completed: 2026-06-16*
