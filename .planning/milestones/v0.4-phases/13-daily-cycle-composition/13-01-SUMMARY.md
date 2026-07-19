---
phase: 13-daily-cycle-composition
plan: 01
subsystem: api
tags: [daily-run, langgraph-composition, workflow, pydantic, curation, research]

# Dependency graph
requires:
  - phase: 10-reviewed-research-run
    provides: run_research_run / review_research_run child entrypoints (approve_all resume)
  - phase: 12-curation-l3-gates-review-application
    provides: run_curation_run / review_curation_run / inspect_curation_run + escalate-is-review-only apply nodes
  - phase: 11-curation-pipe-steps
    provides: graph_status health summary, _validate_run_id / _sanitize_error / _aggregate_status precedents
provides:
  - src/construct/llm/daily_run.py thin composition module (run_daily_run + inspect_daily_run)
  - DailyRunInput / DailyInspectInput / DailyChildStatus / DailyRunResult models
  - _aggregate_daily_status (no-false-completed roll-up)
  - .construct/workflow/daily/<run_id>.json receipt persistence contract
affects: [daily-run-registration, daily-cli-mcp-parity, daily-cycle-skill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thin Python composition of frozen child run_* entrypoints (no parent LangGraph graph/checkpointer)"
    - "Isolate-and-degrade via try/except per child call (D-06)"
    - "Non-blocking auto-resume of paused children via review_*_run(approve_all=True)"
    - "Pending-escalation count captured from gate_queue BEFORE the approve_all resume (Pitfall 5)"
    - "Run receipt JSON under .construct/workflow/ read back by an inspect_* runner"

key-files:
  created:
    - src/construct/llm/daily_run.py
    - tests/llm/test_daily_run.py
  modified: []

key-decisions:
  - "daily.run is thin Python composition, NOT a LangGraph parent graph (D-09; supersedes spec-v04 parent-graph sketch)"
  - "Escalate items surfaced as a pending count and never auto-written; parent forced to degraded (D-03a)"
  - "daily_run emits NO events of its own — children own the full audit trail (D-04)"
  - "Reuse _validate_run_id / _sanitize_error from curation_run verbatim (import, not re-author)"

patterns-established:
  - "Composition module folds three typed child results into one DailyRunResult with a _aggregate_daily_status roll-up"
  - "Each child gets a derived kebab-safe run_id (<daily-id>-research / -curation) so child inspect/review stay addressable"

requirements-completed: [DAY-01, DAY-02, DAY-03]

# Metrics
duration: 18min
completed: 2026-07-06
---

# Phase 13 Plan 01: Daily-Cycle Composition Module Summary

**Thin `daily.run` composition that calls research.run → curation.run → graph.status, auto-applies each gate's recommended decisions via the child `approve_all` resume, excludes escalate (surfaced as a pending count), isolates-and-degrades on child failure, and never reports a false `completed`.**

## Performance

- **Duration:** ~18 min
- **Tasks:** 2 (TDD: RED test suite → GREEN implementation)
- **Files created:** 2

## Accomplishments
- `src/construct/llm/daily_run.py`: `run_daily_run` + `inspect_daily_run` thin composition with `DailyRunInput`/`DailyInspectInput`/`DailyChildStatus`/`DailyRunResult` models and `_aggregate_daily_status`.
- Non-blocking (D-01): each paused child is auto-resumed with its recommended gate decisions; daily.run never interrupts.
- Auto-apply excludes escalate (D-02/D-03): escalate items get no canonical write and are surfaced as a pending-escalation count captured BEFORE the resume (Pitfall 5), forcing `degraded`.
- Isolate-and-degrade (D-06): a raising/failed child is caught, sanitized, and does not abort the remaining children or the closing graph-health summary.
- Receipt persistence to `.construct/workflow/daily/<run_id>.json` (kebab-validated path) with a missing run resolving to `failed` / `"No such daily run."`.
- 7 RED-first unit + integration tests (DAY-01/02/03 + V5), all GREEN; full `tests/llm` suite green (109 passed).

## Task Commits

1. **Task 1: RED composition/degrade/auto-apply suite** - `d72013d` (test)
2. **Task 2: Implement thin daily.run composition module** - `662f5f5` (feat)

_TDD plan: RED (test) commit precedes GREEN (feat) commit._

## Files Created/Modified
- `src/construct/llm/daily_run.py` - Thin composition module: models, `_aggregate_daily_status`, `run_daily_run`, `inspect_daily_run`, receipt persistence.
- `tests/llm/test_daily_run.py` - RED-first suite (composition order, result surface, degrade, pending-escalation, auto-apply-excludes-escalate, inspect round-trip, kebab guard).

## Decisions Made
- Kept the composition offline-testable by spying/canning the child entrypoints in the module namespace for the composition/degrade/surface tests, while driving the REAL curation child (with the shipped L3-gate mock seam) for the escalate/auto-apply tests — proving both "invoked as functions" and the true approve_all/escalate-exclusion behavior.
- `graph.status` child status derived from `OperationResult.success` (`completed`/`failed`); `_aggregate_daily_status` returns `failed` only when every child failed.

## Deviations from Plan

None - plan executed exactly as written. One GREEN-phase adjustment was internal to Task 2 and not a scope change:
- Reworded the module docstring to remove the literal tokens `append_event` and `StateGraph`/`graph.invoke` so the D-04 "no self-emitted events" test and the "no parent graph" acceptance grep both read 0 (the tokens only appeared in prose explaining their intentional absence).

## Issues Encountered
- Worktree has no local `.venv`; ran the suite with the main repo's `.venv/bin/python` and `PYTHONPATH=<worktree>/src:<worktree>` so imports resolved against the worktree source rather than the editable-installed main-repo source.

## Known Stubs
None — `daily_run.py` wires real child entrypoints end-to-end; no placeholder data paths.

## Next Phase Readiness
- The `run_daily_run` / `inspect_daily_run` surface + `DailyRunResult` model are ready for the follow-up plan(s) that register `daily.run` / `daily.inspect` in `catalog.py`, add the `daily` Typer sub-app, and add the CLI/MCP contract test (API-01/02/03). MCP parity will be free via registry auto-discovery — do NOT edit `mcp/server.py`.
- No blockers.

## Self-Check: PASSED
- `src/construct/llm/daily_run.py` — FOUND
- `tests/llm/test_daily_run.py` — FOUND
- Commit `d72013d` (test) — FOUND
- Commit `662f5f5` (feat) — FOUND

---
*Phase: 13-daily-cycle-composition*
*Completed: 2026-07-06*
