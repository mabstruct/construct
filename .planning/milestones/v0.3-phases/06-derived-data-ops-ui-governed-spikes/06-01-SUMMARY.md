---
phase: 06-derived-data-ops-ui-governed-spikes
plan: 06-01
subsystem: views-contracts
tags: [pydantic, json-schema, contract-tests, views, data-validation]
requires:
  - phase: 05-grounded-synthesis-graph-reasoning
    provides: pipeline architecture, capability registry patterns
  - phase: 04-guided-workflow-operability
    provides: skill migration patterns, CLI conventions
provides:
  - Pydantic contract models for all 8 views data file types with JSON Schema export
  - Schema-validating views data generator (validates before write per D-02)
  - Contract test suite validating fixture data against declared schemas
affects:
  - Phase 06 Plan 04 (tag/keyword pipeline) — will consume these models
  - Future v0.4 UI layer — will consume these contracts as stable API

tech-stack:
  added: [pydantic v2 Generics — ViewsEnvelope[T]]
  patterns: [Contract-first data pipeline — Pydantic models define output schema before generator writes data]
key-files:
  created:
    - src/construct/views/__init__.py
    - src/construct/views/models.py
    - src/construct/views/generate.py
    - tests/contract/test_views_contracts.py
  modified: []
key-decisions:
  - "ViewsEnvelope[T] generic separates envelope metadata from data payload — clean separation of concerns"
  - "version field (D-01) placed on ViewsEnvelope at file level, not duplicated on data payloads"
  - "Generator validation is non-fatal per file — errors collected in GenerateReport (failure isolation pattern)"
  - "Simplified contract models define target output shape; current generator may produce richer data that is flagged as validation gap"
patterns-established:
  - "Contract models as source of truth for data shapes — model_json_schema() generates JSON Schema declarations"
  - "validate_data() + schema_for() helpers for consistent schema gate across the pipeline"
  - "All Pydantic models use ConfigDict(extra='forbid') — no silent schema drift"
requirements-completed: [ADV-03]
duration: 8min
completed: 2026-06-11
---

# Phase 6 Plan 1: Views Data Contract Models Summary

**Pydantic contract models for all 8 views JSON data files with JSON Schema export, schema-validated generator, and 49 contract tests against test-ws fixture**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-11T20:06:58Z
- **Completed:** 2026-06-11T20:14:44Z
- **Tasks:** 3
- **Files created:** 4

## Accomplishments

- **17 Pydantic model types** defined — ViewsEnvelope[T], BridgesFile, BridgeRecord, BridgeSummary, DomainsFile, DomainRecord, ArticlesFile, ArticleRecord, StatsFile, CardsFile, CardRecord, ConnectionsFile, ConnectionRecord, DigestsFile, DigestRecord, EventsFile, EventRecord — covering all 8 views data file shapes
- **Schema-validated generator** (`generate()`) that validates each output dict against its contract model before atomic write, collecting errors in GenerateReport (non-fatal per file)
- **49 contract tests** passing, validating against test-ws/my-construct fixture data, confirming schema export, round-trip stability, and invalid-data rejection

## Task Commits

Each task was committed atomically:

1. **Task 1: Define Pydantic contract models** — `9d14c3a` (feat)
2. **Task 2: Add schema validation to views data generator** — `d009041` (feat)
3. **Task 3: Write contract tests validating views data file shapes** — `7d4de35` (test)

**Plan metadata:** _(pending final commit)_

## Files Created

- `src/construct/views/__init__.py` — Package exports for views models and generate pipeline
- `src/construct/views/models.py` — 17 Pydantic contract models with `model_config = ConfigDict(extra="forbid")` following project conventions
- `src/construct/views/generate.py` — `generate()` pipeline function wrapping existing skill lib functions with schema validation before atomic write; returns GenerateReport
- `tests/contract/test_views_contracts.py` — 49 contract tests across 6 classes: fixture validation, version field presence, schema export, round-trip, invalid-data rejection, envelope generics

## Decisions Made

- **Version field placement:** `version` (D-01 contract version semver) placed on `ViewsEnvelope[T]` at the file level rather than duplicated on data payload models — single source of truth, consistent across all file types
- **Validation strategy:** Generator validates output against Pydantic contract models before write. Mismatches are non-fatal per file (collected in report), allowing partial generation to proceed. This surfaces the gap between current generator output (rich structures) and target contracts (simplified models)
- **Generic envelope:** `ViewsEnvelope[T]` uses Pydantic v2 Generic type parameter, enabling type-safe access to `envelope.data` as the specific payload type
- **Helper functions:** `schema_for()` and `validate_data()` extracted as module-level utilities for consistent JSON Schema export and validation anywhere in the codebase

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Self-Check: PASSED

```
FOUND: src/construct/views/__init__.py
FOUND: src/construct/views/models.py
FOUND: src/construct/views/generate.py
FOUND: tests/contract/test_views_contracts.py
```

All 4 created files confirmed. All 3 commits present in git log. 49/49 tests pass.

## Threat Surface Scan

No new security-relevant surface introduced — the views generator reads workspace files and writes JSON data. Pydantic schemas with `extra="forbid"` prevent silent schema drift (T-06-01). Validation errors are collected in the report, not suppressed (T-06-02). No PII or sensitive data in views data files (T-06-03 accepted).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Contract models ready for consumption by Phase 06 Plan 04 (tag/keyword pipeline)
- Generator infrastructure ready for future phases to refine output shapes to match contract models
- Contract tests serve as regression gate for any views data format changes

---

*Phase: 06-derived-data-ops-ui-governed-spikes*
*Completed: 2026-06-11*
