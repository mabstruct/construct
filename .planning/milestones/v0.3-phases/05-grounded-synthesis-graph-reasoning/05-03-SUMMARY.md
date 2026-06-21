---
phase: 05-grounded-synthesis-graph-reasoning
plan: 03
subsystem: pipelines
tags:
  - bridge-detect
  - cross-domain
  - L1
  - L2
  - L3
  - scoring
  - multi-level-detection
requirements_completed: [ADV-02]
requires:
  - 05-02 (ask.domain gate, provider config)
provides:
  - bridge.detect capability
  - construct bridge detect CLI
  - log/bridge-candidates.json
  - views/build/data/bridges.json
affects:
  - src/construct/capabilities/catalog.py (new registration)
  - src/construct/cli.py (new command group)
  - tests/bridge/ (real test implementations)
tech-stack:
  added:
    - ChatAnthropic L3 integration
  patterns:
    - PIPE handler (OperationResult return, WorkspaceLoader usage)
    - Multi-level gating (deterministic L1/L2 gate LLM L3)
key-files:
  created:
    - src/construct/pipelines/bridge_detect.py (547 lines)
  modified:
    - src/construct/storage/workspace.py (load_cards method)
    - src/construct/capabilities/catalog.py (BridgeDetectInput, registration)
    - src/construct/cli.py (bridge_app group, detect command)
    - tests/bridge/conftest.py (fixture fix)
    - tests/bridge/test_bridge_l1.py (real tests)
    - tests/bridge/test_bridge_l2.py (real tests)
    - tests/bridge/test_bridge_l3.py (real tests)
    - tests/bridge/test_bridge_scoring.py (import from real module)
decisions:
  - load_cards added to WorkspaceLoader (Plan 03 interface requirement — Rule 3 fix)
metrics:
  duration: 12 min
  completed: "2026-06-11"
---

# Phase 05 Plan 03: Bridge Detection Pipeline — L1/L2/L3 Multi-Level Detection, Registration, CLI & Tests

**One-liner:** Implemented the `bridge.detect` capability with a three-level Python pipeline: L1 structural edges from `connections.json`, L2 `content_category` overlap across domains, and bounded LLM assessment (L3) for promising candidates. Scoring follows spec-v02-cross-domain-data.md weights (L1=0.30, L2=0.20, L3=0.50).

## Context

ADV-02 requires systematic cross-domain bridge detection. The multi-level design ensures fast deterministic checks (L1/L2) gate the expensive LLM call (L3), preventing O(N²) token usage.

## Task Summary

### Task 1: Implement bridge_detect.py — L1/L2/L3 multi-level pipeline

**Status:** ✅ Complete

Created `src/construct/pipelines/bridge_detect.py` (547 lines) with:

- **`bridge_detect(workspace_path)`** — Main entry point returning `OperationResult`. Loads workspace, runs L1→L2→L3 pipeline, computes scores, persists results.
- **`_l1_structural(loader)`** — Scans `connections.json` for cross-domain edges. Groups by card-pair key, resolves card domains from pre-loaded cards. Returns dict keyed by `"{from_id}--{to_id}"`.
- **`_l2_category_overlap(loader)`** — Loads all cards, groups by domain, computes intersection of `content_categories` across domain pairs. Returns dict keyed by `"{domain_a}--{domain_b}"`.
- **`_merge_candidates(l1_results, l2_results, loader)`** — Merges L1 structural edges and L2 overlaps into unified candidates. Computes `pre_score` = `(L1_WEIGHT * l1_bool) + (L2_WEIGHT * min(1.0, len(cats)/3.0))`. Deduplicates pairs.
- **`_l3_semantic(loader, candidates)`** — Filters candidates with `pre_score >= L3_THRESHOLD (0.3)`, checks `ANTHROPIC_API_KEY`, enforces `MAX_L3_CANDIDATES (50)` cost guard. Uses `ChatAnthropic.with_structured_output(BridgeAssessmentOutput)` at temperature 0.0. Gracefully degrades (skips L3 with warning) when API key unavailable.
- **`_compute_bridge_score(l1, l2_cats, l3_strength)`** → `(score, band)` — Implements spec-v02-cross-domain-data.md §7 scoring: L1=0.30, L2=0.20, L3=0.50. Band: strong (L1 structural OR score>=0.70), medium (>=0.45), weak (<0.45).
- **`_persist_candidates(root, bridges)`** — Writes to `log/bridge-candidates.json` (pipeline log) and `views/build/data/bridges.json` (derived data contract per D-06 #4).
- **`BridgeAssessmentOutput`** — Pydantic model with `verdict` (strong/possible/reject) and `reasoning` fields.

**Deviation — Rule 3:** Added `load_cards()` method to `WorkspaceLoader` (the plan's interface section depends on `loader.load_cards()` but it didn't exist). Returns `list[dict]` with card metadata and body text, skipping unparseable cards.

**Commit:** `ae55dfc`

### Task 2: Register bridge.detect capability, add CLI, and implement tests

**Status:** ✅ Complete

- **`catalog.py`:** Added `BridgeDetectInput` model (Pydantic, `extra="forbid"`, single `workspace_path` field). Registered `bridge.detect` capability with `handler=lambda **kwargs: bridge_detect(kwargs.get("workspace_path", ""))`.
- **`cli.py`:** Added `bridge_app` Typer command group with `detect` subcommand. Supports `--workspace/-w` and `--json/-j` flags. Retrieves capability from registry and dispatches.
- **`test_bridge_l1.py`:** Three tests — cross-domain edge detection (`cross_domain_workspace` fixture), empty results for no connections, same-domain exclusion.
- **`test_bridge_l2.py`:** Two tests — shared categories detection (cosmology + philosophy-of-mind share "foundations"), same-domain exclusion.
- **`test_bridge_l3.py`:** Two tests — L3_THRESHOLD == 0.3, MAX_L3_CANDIDATES == 50.
- **`test_bridge_scoring.py`:** Imports `_compute_bridge_score` from real module. 8 parametrized test cases + weight sum test (no change from stub).
- **`conftest.py`:** Fixed `notes` → `note` field name (ConnectionRecord schema uses `note`, not `notes`).

**Commit:** `f6d918f`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Missing dependency] Added `load_cards()` to WorkspaceLoader**
- **Found during:** Task 1
- **Issue:** Plan interfaces section specifies `loader.load_cards()` but the method doesn't exist on `WorkspaceLoader`. Only `iter_cards()` returns file paths.
- **Fix:** Added `load_cards()` method that reads and parses all card files, returning `list[dict]` with metadata + body text. Uses `parse_card_markdown()` for parsing.
- **Files modified:** `src/construct/storage/workspace.py`
- **Commit:** `ae55dfc`

**2. [Rule 1 — Bug] Fixed conftest fixture field name `notes` → `note`**
- **Found during:** Task 2 test run
- **Issue:** `ConnectionRecord` schema has `note: str | None = None` field but the fixture wrote `notes`, causing Pydantic validation failure (`extra_forbidden`).
- **Fix:** Changed `notes` to `note` in `tests/bridge/conftest.py` and `tests/bridge/test_bridge_l1.py`.
- **Files modified:** `tests/bridge/conftest.py`, `tests/bridge/test_bridge_l1.py`
- **Commit:** `f6d918f`

## Verification Results

1. ✅ `python -c "from construct.pipelines.bridge_detect import bridge_detect; print('Module OK')"` → Module OK
2. ✅ `python -c "from construct.capabilities.catalog import get_registry; r = get_registry(); r.get('bridge.detect')"` → bridge.detect registered
3. ✅ `python -m pytest tests/bridge/ -x --tb=short -q` → 16 passed
4. ✅ `python -c "from construct.cli import bridge_app; print('bridge CLI group OK')"` → bridge CLI group OK

## Known Stubs

None — all functions in bridge_detect.py have real implementations (L3 is bounded and gracefully degrades when API key unavailable).

## Threat Surface Scan

No new threat flags. Bridge data is derived (written to `log/` and `views/build/data/` — non-canonical paths). Threat mitigations from plan are implemented:
- T-05-07: L3_THRESHOLD (0.3) gates L3; MAX_L3_CANDIDATES (50) cost guard
- T-05-08: WorkspaceLoader constrains file reads; BridgeDetectInput validates input
- T-05-09: Accepted — bridge candidates are derived data, not canonical knowledge

## Self-Check: PASSED

- [x] `src/construct/pipelines/bridge_detect.py` exists (547 lines, min 200 ✓)
- [x] `src/construct/capabilities/catalog.py` contains `bridge.detect` capability registration
- [x] `src/construct/cli.py` contains `bridge_app` Typer group with `detect` command
- [x] `tests/bridge/test_bridge_l1.py` has real L1 tests (cross-domain, no-conn, same-domain)
- [x] `tests/bridge/test_bridge_l2.py` has real L2 tests (shared-categories, same-domain exclusion)
- [x] `tests/bridge/test_bridge_l3.py` has real L3 tests (threshold, max candidates)
- [x] `tests/bridge/test_bridge_scoring.py` imports from real module
- [x] All 16 tests pass
- [x] Scoring weights match spec (L1=0.30, L2=0.20, L3=0.50)
- [x] `views/build/data/bridges.json` is written by `_persist_candidates`
