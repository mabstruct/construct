---
phase: 10-durable-human-review-research-run
plan: 03
subsystem: api
tags: [langgraph, interrupt, sqlite-checkpointer, research-run, human-in-the-loop, idempotency]

# Dependency graph
requires:
  - phase: 10-01
    provides: langgraph-checkpoint-sqlite dependency + SqliteSaver availability
  - phase: 10-02
    provides: research_dedup helpers (normalize_url, ref_id_for, title_is_near_dup, rejected-ledger I/O)
  - phase: 08
    provides: research_search provider-agnostic search + normalized SearchResult contract
  - phase: 09
    provides: research_score.run_gate L3 scoring + ResearchScoreOutageError + degraded retrieval signal
provides:
  - "ResearchRunState channel (TypedDict, plain serializable data only)"
  - "In-module I/O models: ResearchRunInput, ReviewInput, InspectInput, RunResult, GateQueueEntry"
  - "Pre-gate nodes: load_config, build_queries, execute_search, deduplicate, score_and_extract"
  - "Interrupt-only gate_review node (durability boundary; RSCH-03 holds by construction)"
  - "build_research_run_graph(checkpointer) + outage short-circuit"
  - "_open_checkpointer (.construct/workflow/research-run.sqlite, no conn-string footgun)"
  - "run_research_run run-start runner returning awaiting_review + gate_queue"
affects: [10-04, 10-05]

# Tech tracking
tech-stack:
  added: [langgraph-checkpoint-sqlite>=3.1,<4]
  patterns:
    - "Durable LangGraph StateGraph with a single native interrupt() gate"
    - "Persistent SqliteSaver via explicit sqlite3.connect (check_same_thread=False), closed in finally"
    - "Conditional edge after score_and_extract to short-circuit total outage to END (never pause)"

key-files:
  created:
    - src/construct/llm/research_run.py
  modified:
    - tests/llm/test_research_run.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "build_queries excludes paused/exhausted clusters and empty-term reserved ingest clusters; caps at max_papers_per_cycle"
  - "Total outage routes to END via a conditional edge so the graph never pauses on failure"
  - "Corrected langgraph-checkpoint-sqlite pin from >=2.0,<3 to >=3.1,<4 (API incompatibility with checkpoint 4.1.1)"

patterns-established:
  - "Interrupt-only gate node: gate_review contains a single interrupt() and zero side effects (re-runs on resume)"
  - "Pre-gate nodes rebuild WorkspaceLoader inside the node; state holds only plain serializable data"

requirements-completed: [RSCH-02, RSCH-03, RSCH-04]

# Metrics
duration: 15min
completed: 2026-06-28
---

# Phase 10 Plan 03: research.run Read-Side + Durable Interrupt Gate Summary

**A checkpointed LangGraph workflow that composes Phase 8 search + Phase 9 scoring, pauses at a real `interrupt()` exposing a per-finding `gate_queue`, writes nothing before approval, and short-circuits total provider outage to END before the gate.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-28T15:40:00Z
- **Completed:** 2026-06-28T15:50:30Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4

## Accomplishments
- `ResearchRunState` TypedDict + five in-module I/O models (no `catalog.py` circular-import risk).
- Five pre-gate nodes composing active-cluster query building, provider search, idempotent dedup (refs/ + rejected ledger + in-batch + title-fuzzy), and Phase 9 scoring with outage caught BEFORE the gate.
- Interrupt-only `gate_review` node — the durability boundary that makes RSCH-03 (no writes before approval) true by construction.
- `build_research_run_graph` (locked linear topology + outage short-circuit), `_open_checkpointer` under `.construct/`, and `run_research_run` returning `awaiting_review` with the pending per-finding `gate_queue`.
- Skeleton post-gate write nodes (no writes) so the graph compiles and pauses; Plan 04 implements their bodies.

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 RED: state/models/pre-gate node tests** - `20f4829` (test)
2. **Task 1 GREEN: state, models, pre-gate nodes** - `f37d4cb` (feat)
3. **Task 2 RED: gate/graph/checkpointer/runner tests** - `5b5f7d0` (test)
4. **Deviation: dependency pin correction** - `411e526` (chore)
5. **Task 2 GREEN: gate, graph, checkpointer, runner** - `10b58ec` (feat)

## Files Created/Modified
- `src/construct/llm/research_run.py` - The durable workflow module: state channel, I/O models, pre-gate nodes, interrupt gate, skeleton write nodes, graph builder, checkpointer, run-start runner.
- `tests/llm/test_research_run.py` - Added 12 implemented tests (models, build_queries, deduplicate, score_and_extract, gate-interrupt-only, checkpointer, graph pause, outage-never-pauses, skeleton no-writes); converted the `no_writes_before_approval` scaffold to a real test.
- `pyproject.toml` / `uv.lock` - Corrected `langgraph-checkpoint-sqlite` pin to a version compatible with `langgraph-checkpoint` 4.1.1.

## Decisions Made
- `build_queries` produces one query per active cluster (joined terms), excluding paused/exhausted clusters and the reserved empty-term `manual-ingest`/`web-ingest` clusters, capped at governance `max_papers_per_cycle`.
- Used a conditional edge from `score_and_extract` (`END` on `status==failed`, else `gate_review`) so a caught `ResearchScoreOutageError` never reaches the interrupt — satisfying "status failed, never pauses".
- `gate_id` defaults to `run_id` (the thread handle the human review/inspect calls address).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected langgraph-checkpoint-sqlite version pin**
- **Found during:** Task 2 (first checkpoint write during a paused graph invoke)
- **Issue:** The prior-wave pin `langgraph-checkpoint-sqlite>=2.0,<3` resolved to 2.0.10, which calls `JsonPlusSerializer.dumps()` / `.loads()`. `langgraph-checkpoint` 4.1.1 (required by langgraph 1.2.4) removed those methods (only `dumps_typed`/`loads_typed` remain), so the first `SqliteSaver.put` raised `AttributeError: 'JsonPlusSerializer' object has no attribute 'dumps'`. The incompatibility was latent because all prior `test_research_run.py` tests were xfail scaffolds that never exercised the saver.
- **Fix:** Updated the pin to `>=3.1,<4`; `langgraph-checkpoint-sqlite` 3.1.0 declares `langgraph-checkpoint<5.0.0,>=4.1.0` and restores compatibility. Same trusted langchain-ai package — a compatible version bump, not a new/unknown package install (slopsquat exclusion does not apply).
- **Files modified:** pyproject.toml, uv.lock
- **Verification:** `uv lock && uv sync --extra dev` upgraded 2.0.10 → 3.1.0; the paused-invoke + cross-checkpoint tests then pass.
- **Committed in:** `411e526`

---

**Total deviations:** 1 auto-fixed (1 blocking dependency-compatibility correction)
**Impact on plan:** Necessary to make the checkpointer (the plan's core durability mechanism) function at all. No scope creep — corrects a latent prior-wave foundation pin.

## Issues Encountered
- Two grep gates (`print(`, `from_conn_string`) initially tripped on docstring mentions of those tokens; reworded the docstrings so the gates reflect only real code. No behavior change.

## Out-of-Scope / Deferred
Three pre-existing, unrelated test failures were logged to `deferred-items.md` (two fixture-layout migration checks on `test-ws/`, and one tavily-extra import test that passes under `--extra search`). None reference `research_run` or the checkpointer; left untouched per scope boundary.

## User Setup Required
None - no external service configuration required. The checkpoint DB and rejected ledger live under the gitignored `.construct/`.

## Next Phase Readiness
- The graph compiles and pauses at a real interrupt with a persisted per-finding `gate_queue` — Plan 04 can now implement the post-gate write-node bodies (`ingest_batch`, `compile_digest`, `update_seeds_and_log`), the `research.review` resume runner (`Command(resume=...)`), the `research.inspect` `get_state` runner, and register the three capabilities + CLI/MCP parity.
- `ReviewInput`/`InspectInput`/`RunResult` D-12 fields are defined and ready to be populated by Plan 04.

---
*Phase: 10-durable-human-review-research-run*
*Completed: 2026-06-28*

## Self-Check: PASSED
- Created files verified present: `src/construct/llm/research_run.py`, `10-03-SUMMARY.md`, `deferred-items.md`.
- Commits verified in git history: `20f4829`, `f37d4cb`, `5b5f7d0`, `411e526`, `10b58ec`.
