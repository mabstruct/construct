---
phase: 06-derived-data-ops-ui-governed-spikes
plan: 06-04
subsystem: cli-views-spike-tag
tags:
  - cli
  - views-validate
  - spike-runner
  - tag-extraction
  - curation-cycle
  - search-seeds
requires: [06-01, 06-03]
provides: [cli-views-validate, cli-spike-run, cli-tag-pipeline]
affects:
  - src/construct/cli.py
  - src/construct/pipelines/tag_extraction.py
  - src/construct/services/knowledge.py
tech-stack:
  added: []
  patterns:
    - "Typer subcommand groups with nested apps"
    - "Hybrid regex-based phrase extraction for tags"
    - "Atomic file writes for workspace artifacts"
key-files:
  created:
    - src/construct/pipelines/tag_extraction.py
  modified:
    - src/construct/cli.py
    - src/construct/services/knowledge.py
decisions:
  - "Tag extraction uses hybrid regex approach (not LLM) within agent's discretion per D-07"
  - "Approved tags become new SearchCluster entries in search-seeds.json (not seeds array)"
  - "Confidence scoring: frequency-based (0-0.5) + phrase length (0-0.3) + substance ratio (0-0.2)"
metrics:
  duration: 3m 6s
  completed_date: 2026-06-11
---

# Phase 06 Plan 04: CLI Integration + Tag Pipeline Summary

Wire the Phase 6 subsystems (Views Contracts, Spike Framework, Tag Pipeline) into the CLI surface, and build the tag/keyword extraction pipeline that extracts candidates from source refs and routes them through the curation cycle.

## Tasks Completed

### Task 1: Add CLI command groups for views, spike, and tag
**Commit:** `83db2db`
**Files:** `src/construct/cli.py`

Added three new Typer command groups with full subcommands:

- **`views_app`** — `construct views validate` validates views build data files against their Pydantic contract schemas (BridgesFile, CardsFile, etc.)
- **`spike_app`** — `construct spike list` shows available spike types (graphify, infranodus); `construct spike run <tool>` executes a governed spike on an isolated temp workspace copy
- **`tag_app`** — `construct tag extract` runs extraction pipeline; `construct tag approve <ids>` writes to search-seeds.json; `construct tag list [--status]` queries candidates

All follow existing Typer patterns: `--workspace/-w`, `--json/-j`, `_display_result()`.

### Task 2: Create tag extraction pipeline
**Commit:** `35472a6`
**Files:** `src/construct/pipelines/tag_extraction.py` (new, 590 lines)

Created `extract_candidates(workspace)` that:
1. Reads `refs/*.json` from the workspace
2. Extracts candidate phrases using hybrid regex approach: capitalized multi-word phrases, adjective-noun patterns, "X of Y" constructions, acronym expansions
3. Scores by frequency across refs with confidence formula: frequency (0-0.5) + phrase length (0-0.3) + substance ratio (0-0.2)
4. Deduplicates against existing `search-seeds.json` clusters
5. Differs against existing `tag-candidates.json` for new/novel tracking
6. Merges and writes atomically to `log/tag-candidates.json`

All candidates start as `status: "pending"` — never auto-accepted per D-08.

Helpers: `normalize_tag()`, `extract_phrases()`, `load_search_seeds()`, `load_existing_candidates()`.

### Task 3: Wire tag candidate approval into knowledge service
**Commit:** `c93d70c`
**Files:** `src/construct/services/knowledge.py` (310 lines added)

Three new functions:

- **`approve_tag_candidates(workspace, candidate_ids)`** — Loads candidates from `log/tag-candidates.json`, validates `pending` status, marks as `approved`, creates new `SearchCluster` entries in `search-seeds.json` with domain context and confidence-based weight. Atomic writes. Logs `tag_candidates_approved` event.
- **`reject_tag_candidates(workspace, candidate_ids)`** — Same flow but sets status to `rejected`, does NOT update search-seeds.json. Logs `tag_candidates_rejected` event.
- **`list_tag_candidates(workspace, status=None)`** — Reads candidates with optional status filter, returns sorted by confidence descending.

D-08 enforced throughout: candidates start as "pending" and only explicit `approve_tag_candidates()` writes to search-seeds.json. Returned `OperationResult` with structured errors (T-06-11).

## Threat Model Compliance

| Threat | Disposition | Status |
|--------|-------------|--------|
| T-06-10 — CLI tool_name injection | mitigate | `tool_name` validated against `KNOWN_SPIKES` keys in spike_runner.py (pre-existing) |
| T-06-11 — Tag auto-accept | mitigate | D-08 enforced: all candidates start `pending`, only `approve_tag_candidates()` changes status |
| T-06-12 — search-seeds.json overwrite | mitigate | Atomic write via `.tmp` → rename, existing clusters preserved |
| T-06-13 — Tag candidate corruption | accept | Reviewable file, re-running extraction recreates candidates |

## Verification Results

```text
✓ CLI syntax OK
✓ CLI commands found: ['validate', 'run', 'validate', 'list', 'run', 'extract', 'approve', 'list']
✓ Tag pipeline import OK
✓ Knowledge service tag functions import OK
✓ Full CLI import OK

Functional test (test-ws/my-construct):
  ✓ extract_candidates() found 26 candidates
  ✓ 1 existing seed skipped
  ✓ All candidates start as "pending"
  ✓ Output written to log/tag-candidates.json
```

## Deviations from Plan

None — plan executed exactly as written. Minor note: the `search-seeds.json` format description in the plan used an approximate `"seeds"` array syntax; the actual implementation writes `SearchCluster` entries matching the existing `SearchSeedsFile` Pydantic model format.

## Decisions Made

1. **Tag extraction approach**: Hybrid regex-based extraction (capitalized phrases, adjective-noun, X-of-Y) rather than LLM-assisted, per the agent's discretion in D-07. The module is designed for upgrade to LLM-assisted extraction if needed — `extract_phrases()` is a single function to replace.
2. **Confidence formula**: Linear combination of frequency ratio (0-0.5), phrase length specificity (0-0.3), and non-stop-word substance ratio (0-0.2), capped at 1.0.
3. **Min confidence threshold**: 0.15 — filters out single-word fragments and noise from general text.
4. **Atomic write pattern**: `write → .tmp → replace()` for both `tag-candidates.json` and `search-seeds.json`, consistent with existing workspace I/O patterns.

## Self-Check: PASSED

- [x] src/construct/cli.py parses without errors
- [x] views, spike, and tag command groups exist
- [x] construct tag extract reads refs and writes tag-candidates.json
- [x] construct tag approve writes to search-seeds.json (via approve_tag_candidates)
- [x] approve_tag_candidates NEVER auto-accepts per D-08
- [x] Events logged for approve/reject actions
- [x] All existing CLI commands remain intact
- [x] 3 commits, 3 tasks, 3 files (2 modified + 1 created)
