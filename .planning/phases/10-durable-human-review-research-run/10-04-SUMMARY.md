---
phase: 10-durable-human-review-research-run
plan: 04
subsystem: api
tags: [langgraph, sqlite-checkpoint, research-run, idempotency, human-review, digest, event-log]

# Dependency graph
requires:
  - phase: 10-durable-human-review-research-run (Plan 03)
    provides: ResearchRunState, I/O models, pre-gate nodes, interrupt-only gate_review, build_research_run_graph, _open_checkpointer, run_research_run
  - phase: 10-durable-human-review-research-run (Plan 02)
    provides: research_dedup (ref_id_for, normalize_url, append_rejected, ledger)
  - phase: 09 (research.score)
    provides: run_gate, ScoredFinding, ResearchScoreGateOutput, degraded/outage signals
  - phase: 08 (research.search)
    provides: provider-agnostic search seam
provides:
  - "Post-gate write nodes: ingest_batch (approved-only, deterministic, idempotent), compile_digest (template + DigestRecord), update_seeds_and_log (last_queried + D-11 events)"
  - "research.review runner (Command(resume) with per-finding / approve-all / reject-all decisions)"
  - "research.inspect runner (get_state, no resume) for cross-process pending inspection"
  - "Finalized D-12 RunResult surface (SC5)"
  - "Fully completing durable research.run workflow with resumable, idempotent, audited writes"
affects: [10-05, research-run-cli, research-run-mcp]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deterministic ref/card IDs (slug + URL sha1) + skip-if-exists for crash-safe idempotent writes"
    - "Resume payload normalization: None/list[str]/list[dict] → per-finding actions with default fallback"
    - "Read-only get_state inspection vs Command(resume) completion across SqliteSaver instances on one DB file"

key-files:
  created:
    - .planning/phases/10-durable-human-review-research-run/10-04-SUMMARY.md
  modified:
    - src/construct/llm/research_run.py
    - tests/llm/test_research_run.py

key-decisions:
  - "Card shares the ref's deterministic ID (skip-if-exists on cards/<ref_id>.md) so ref_and_card approvals are idempotent across rerun and crash+resume"
  - "Digest record store at digests/digests.json; idempotent append replaces any prior record with the same digest id"
  - "Per-finding gate decision events use EventAgent.construct (reusing the existing gate_review protocol agent); cycle events use EventAgent.researcher (RESEARCH A6)"
  - "approve-all expands to each finding's recommended ingest_action (the LLM's proposed set); reject-all → all skip → ledger"

patterns-established:
  - "Per-finding error isolation in ingest_batch: a single finding raising never aborts the batch (D-08 style)"
  - "Both runners reuse _open_checkpointer and close the sqlite connection in finally"

requirements-completed: [RSCH-02, RSCH-03, RSCH-04, RSCH-05]

# Metrics
duration: 9min
completed: 2026-06-28
---

# Phase 10 Plan 04: Post-gate write nodes + review/inspect runners Summary

**Approved-only idempotent ingest (deterministic IDs + skip-if-exists), template digest with DigestRecord + degraded notice, seed last_queried updates with D-11 events, and research.review/inspect runners that resume or inspect a paused run across process restarts — closing the durable research.run workflow with a D-12 RunResult.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-06-28T14:27:00Z
- **Completed:** 2026-06-28T14:36:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `ingest_batch`: writes approved refs (deterministic `ref_id_for` + skip-if-exists) and seed cards for `ref_and_card`; routes skip/reject findings to the rejected ledger; per-finding error isolation; no double-write on rerun or mid-batch crash+resume.
- `compile_digest`: template-only (no LLM) markdown to `digests/<id>.md` with run counts + created IDs + degraded notice; idempotent `DigestRecord` append to `digests/digests.json`.
- `update_seeds_and_log`: stamps `last_queried` on queried clusters, writes back `search-seeds.json`, emits the full D-11 event set, sets terminal `status=completed`.
- `review_research_run` (Command(resume) with per-finding / approve-all / reject-all) and `inspect_research_run` (get_state, no resume), both closing the sqlite connection in `finally`.
- Finalized D-12 `RunResult` surface and turned all 8 RSCH/SC scaffold tests green (xfail markers removed).

## Task Commits

Each task was committed atomically:

1. **Task 1: ingest_batch (approved-only, deterministic, idempotent) + ledger rejects** - `c73e6d9` (feat)
2. **Task 2: compile_digest (template + DigestRecord) + update_seeds_and_log (events)** - `9a3cd4b` (feat)
3. **Task 3: research.review (resume) + research.inspect (get_state) runners + RunResult** - `4a13528` (feat)

## Files Created/Modified
- `src/construct/llm/research_run.py` - Implemented the three post-gate write nodes, the decision-resolution helpers, the review/inspect runners, the `_completion_result` D-12 assembler, and four new output state channels (`refs_created`, `cards_created`, `skipped_existing`, `rejected`).
- `tests/llm/test_research_run.py` - Turned 8 xfailed RSCH/SC scaffolds green (full_run_offline, per_finding_decisions, cross_process_resume, inspect_no_resume, idempotent_rerun, partial_batch_resume_safe, run_result_fields) + added degraded-notice and approve/reject-all coverage; added `_make_workspace` helper; removed the obsolete Plan 03 skeleton no-write test.

## Decisions Made
- Card uses the ref's deterministic ID and skip-if-exists, making `ref_and_card` approvals fully idempotent.
- Digest record store path `digests/digests.json`; idempotent append by digest id.
- Gate-decision events reuse `EventAgent.construct` (existing protocol); cycle events use `EventAgent.researcher`.

## Deviations from Plan

**1. [Grouping] All three node bodies implemented in the Task 1 commit**
- **Found during:** Task 1 implementation
- **Issue:** The Plan 03 skeletons for `ingest_batch`, `compile_digest`, and `update_seeds_and_log` lived in one contiguous block; replacing all three together was cleaner than splitting the edit.
- **Fix:** Node bodies landed in `c73e6d9` (Task 1); the Task 2 commit (`9a3cd4b`) carries the `compile_digest`/`update_seeds_and_log` *tests* (full_run_offline, degraded_notice). All per-task verification commands still pass against their own task boundary.
- **Files modified:** src/construct/llm/research_run.py
- **Verification:** Task 1 and Task 2 verify commands both green.
- **Committed in:** c73e6d9 / 9a3cd4b

**2. [Rule 1 - Obsolete test] Removed Plan 03 skeleton no-write test**
- **Found during:** Task 1
- **Issue:** `test_skeleton_post_gate_nodes_perform_no_writes` asserted the post-gate nodes contain no write calls — true only for the Plan 03 skeletons, now contradicted by the implemented bodies.
- **Fix:** Removed it; the enduring invariant (no writes before approval) remains covered by `test_no_writes_before_approval`.
- **Files modified:** tests/llm/test_research_run.py
- **Verification:** Full suite green.
- **Committed in:** c73e6d9

**3. [Hygiene] Reverted regenerated build stamp**
- **Found during:** post-Task-3 status check
- **Issue:** `src/construct/_build.py` (a tracked build stamp) was regenerated by the `uv build` hook during test runs — unrelated to this plan.
- **Fix:** `git checkout -- src/construct/_build.py` to keep commits focused.
- **Files modified:** none (reverted)

---

**Total deviations:** 3 (1 commit-grouping, 1 obsolete-test removal, 1 build-stamp hygiene)
**Impact on plan:** No scope creep. All planned behavior delivered; verification commands and the phase-level checks pass.

## Issues Encountered
- `Path` was not imported at the top of the test module; added `from pathlib import Path` (test infra fix).
- Simulating a mid-batch crash required an exception that escapes the per-finding `except Exception` isolation; used a local `BaseException` subclass so the node aborts hard and LangGraph resumes the pending task via `graph.invoke(None, cfg)`.

## Verification Results
- `uv run --extra dev pytest tests/llm/test_research_run.py -q` → 21 passed, 0 xfailed.
- `grep -c "_deduplicate_ref_id\|ingest_source\|from_conn_string" src/construct/llm/research_run.py` → 0.
- `uv run --extra dev pytest tests/llm tests/pipelines -q` → 83 passed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The durable `research.run` workflow now completes end-to-end with resumable, idempotent, audited writes — ready for Plan 05 (capability registration / CLI / MCP wiring).
- No blockers.

## Self-Check: PASSED

- SUMMARY.md present.
- `src/construct/llm/research_run.py` present with `ingest_batch`, `review_research_run`, `inspect_research_run`.
- All task commits present: `c73e6d9`, `9a3cd4b`, `4a13528`, `586b117`.

---
*Phase: 10-durable-human-review-research-run*
*Completed: 2026-06-28*
