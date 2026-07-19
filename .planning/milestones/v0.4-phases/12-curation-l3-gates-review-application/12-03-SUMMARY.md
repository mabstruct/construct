---
phase: 12-curation-l3-gates-review-application
plan: 03
subsystem: llm
tags: [langgraph, hitl, interrupt, curation, gate-queue, cur-03, read-side]

# Dependency graph
requires:
  - phase: 12-02
    provides: card.evaluate + connection-typing L3 gates (evaluate_all / type_all)
  - phase: research.run
    provides: research_run.py interrupt/resume HITL machine mirrored here
provides:
  - CurationRunState gate_queue (operator.add) + decisions + per-write output channels
  - CurationProposal envelope (kind/decision/payload, extra=forbid)
  - _CURATION_GATE_ID constant for the single consolidated review gate
  - three proposal PRODUCERS (promotion_review, connection_maintenance, decay_scan archive)
  - interrupt-only process_inbox + empty-queue conditional short-circuit
  - run_curation_run run-start pause detection -> awaiting_review
  - minimal review_curation_run resume runner (no write nodes)
affects: [12-04, 12-05, 12-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Interrupt-only HITL gate: pause node holds ONLY interrupt(); all writes strictly downstream (CUR-03 spine by construction)"
    - "All proposals computed into ONE heterogeneous gate_queue BEFORE the single pause"
    - "Empty-queue conditional short-circuit: a run with nothing to review never pauses (Pitfall 2)"
    - "Producers degrade to zero proposals on provider outage (offline runs keep an empty queue and complete)"

key-files:
  created: []
  modified:
    - src/construct/llm/curation_run.py
    - tests/llm/test_curation_run.py

key-decisions:
  - "_CURATION_GATE_ID = 'curation.review' module constant; interrupt payload uses the constant, never state['gate_id'] (no KeyError)"
  - "gate_queue is Annotated[list[dict], operator.add] so three producers APPEND into one queue instead of overwriting"
  - "decay_scan stays a pure findings step (unchanged summary/findings) AND enqueues archive proposals under auto_archive_on_decay — keeps test_auto_archive green"
  - "Added a minimal review_curation_run + CurationReviewInput in Plan 03 (resume-only, no write nodes) because test_single_consolidated_gate's -k target calls it; Plan 04 grafts the write-side"
  - "CurationRunResult.gate_id surfaces the run_id review handle (per tests), distinct from the interrupt payload's internal _CURATION_GATE_ID"

patterns-established:
  - "run-start pause detection: '__interrupt__' in result AND snap.next == ('process_inbox',) -> awaiting_review + gate_queue (no terminal event, no write)"
  - "paused-state resume guard: review runner refuses to re-resume a non-paused run"

requirements-completed: [CUR-03]

# Metrics
duration: ~25min
completed: 2026-07-02
---

# Phase 12 Plan 03: Curation Read-Side HITL Graft Summary

**Grafted the read-side of the research_run HITL machine onto curation_run.py: three deferred skip-nodes became proposal PRODUCERS that compute promotion / connection / archive proposals into ONE heterogeneous gate_queue, process_inbox became an interrupt-only consolidated review gate keyed by the module constant `_CURATION_GATE_ID`, and a conditional short-circuit routes an empty queue straight to compile_report without pausing — establishing the CUR-03 spine by construction (no write node exists upstream of the interrupt).**

## What shipped

- **State + envelope (Task 1):** `CurationRunState` gains `gate_queue: Annotated[list[dict], operator.add]`, `decisions`, and the Plan-04 per-write output channels (`promoted`/`connections_added`/`archived`/`rejected`/`escalated`). `CurationProposal` envelope (`kind`/`decision`/`payload`, `extra="forbid"`). `_CURATION_GATE_ID = "curation.review"` module constant. `CurationRunResult` gains `gate_id` + `gate_queue` and the `awaiting_review` status. `CurationReviewInput` added with the kebab-case run-id path-traversal guard.
- **Producers + gate + routing (Task 2):**
  - `promotion_review` pre-filters non-mature/non-archived cards (D-02), runs `curation_promote.evaluate_all`, and enqueues `promotion`/`escalate` proposals; plain `hold` is events-only.
  - `connection_maintenance` keeps the `bridge_detect` call and feeds its candidate pairs to `curation_connect.type_all`, enqueuing typed `connection` proposals; bridge findings survive a typing outage.
  - `decay_scan` (unchanged findings/summary) additionally enqueues `archive` proposals under `auto_archive_on_decay`.
  - `process_inbox` is now interrupt-ONLY: `interrupt({"gate_id": _CURATION_GATE_ID, "gate_queue": state["gate_queue"]})` and nothing else.
  - `_route_before_inbox` conditional edge: `process_inbox` if `gate_queue` else `compile_report`.
  - `run_curation_run` detects the pause and returns `awaiting_review` + `gate_queue` + `gate_id=run_id` (no terminal event, no write); a minimal `review_curation_run` resumes the graph to completion (no write nodes yet).

## Test status

Read-side targets GREEN (`-k "no_writes_before_approval or empty_queue or single_consolidated or interrupt or pauses"`):
- `test_no_writes_before_approval`, `test_empty_queue_no_pause`, `test_single_consolidated_gate` — PASS.
- `test_no_unreviewed_writes` — PASS (process_inbox source has exactly one `interrupt(` and no `edit_card`/`add_connection`/`archive_card`/`append_event`/`write_text`/`.write(`).

All 8 legacy Phase-11 tests stay GREEN — including `test_steps_return_concrete_findings`, `test_deferred_nodes_visible_skipped`, and `test_auto_archive_reported_not_acted`. (Offline no-mock runs hit a provider total-outage → producers enqueue nothing → empty queue → the run completes through `compile_report` exactly as before.)

Write-side tests STAY RED (Plan 12-04 targets), as intended:
- `test_reviewed_promotion_applied`, `test_reviewed_archive_applied`, `test_cross_process_resume`, `test_inspect_pending_review`, `test_curation_events_emitted`.

`tests/llm/test_curation_run.py`: **13 passed, 5 failed** (all 5 failures are Plan-04 write-side targets).

## Deviations from Plan

### Auto-fixed / necessary scope additions

**1. [Rule 2 — Missing critical functionality] Added run-start pause detection + minimal `review_curation_run` + `CurationReviewInput`.**
- **Found during:** Task 2 (verify `-k single_consolidated`).
- **Issue:** The plan's Task-2 action text describes only the producers, interrupt node, and short-circuit, but its own `-k` verify target `test_single_consolidated_gate` calls `curation_run.review_curation_run(...)` and asserts `done.status == "completed"`, and `test_no_writes_before_approval` requires `run_curation_run` to return `awaiting_review` + `gate_queue` + `gate_id`. Both are run-start/resume runner concerns.
- **Fix:** Added run-start pause detection to `run_curation_run` and a minimal resume-only `review_curation_run` (+ `CurationReviewInput`). These contain NO write nodes — resume simply clears the interrupt and runs to `compile_report`. Plan 04 grafts the post-gate apply nodes onto the same runner.
- **Files modified:** `src/construct/llm/curation_run.py`. **Commit:** fcc0327.

**2. [Rule 1 — Invalidated legacy test] Updated `_DEFERRED_STEPS` in `tests/llm/test_curation_run.py`.**
- **Found during:** Task 2.
- **Issue:** `test_deferred_nodes_visible_skipped` asserted `promotion_review` and `process_inbox` are deferred skip-nodes with a "deferred to Phase 12" reason. Turning them into a producer and an interrupt gate (the plan's core mandate) makes that assertion structurally false (and `process_inbox` is routed around on an empty queue, so it never appears in `steps`).
- **Fix:** Narrowed `_DEFERRED_STEPS` to `("views_refresh_hook",)` — the only node still deferred — with an explanatory comment. No assertion was weakened; the test still verifies the remaining deferred node.
- **Files modified:** `tests/llm/test_curation_run.py`. **Commit:** fcc0327.
- **Note:** The plan frontmatter listed only `curation_run.py` in `files_modified`; this one-line test update is an unavoidable consequence of the deferred→producer transition.

### Observations (no action taken)

- **`test_reviewed_connection_idempotent` is GREEN rather than RED.** The user's brief listed it among the stay-RED Plan-04 set, but as written it only asserts `after_second == after_first` and no duplicate `(from,to,type)` tuples — it never asserts that a NEW connection was created. With no apply nodes in Plan 03 the connection set is unchanged, so the test passes vacuously. This is a property of the test's construction, not of any added write node; it stays GREEN in Plan 04 once real idempotent writes land. Left untouched.
- **6 contract tests RED (out of scope):** `tests/contract/test_curation_run_cli_mcp.py` failures (`test_registered`, `test_shims_reject_positional_args`, `test_in_mcp_tool_list`, `test_mcp_server_exposes_curation`, `test_cli_commands_present`, `test_no_placeholder_curation_path`) assert `catalog.py` / `cli.py` registration of `curation.review` + `card.evaluate` and placeholder removal — Plan 05/06 territory. Verified pre-existing at the Plan-03 baseline. Logged in `deferred-items.md`.

## Threat model

- **T-12-06 (Tampering, process_inbox):** mitigated — `process_inbox` holds ONLY `interrupt()`; `test_no_unreviewed_writes` enforces it. No write node exists upstream of the interrupt.
- **T-12-07 (EoP, producer proposals):** mitigated — producers only enqueue typed `CurationProposal` envelopes (`extra="forbid"`); the write boundary sits strictly downstream of the human resume (Plan 04).
- **T-12-08 (Tampering, logging):** mitigated — nodes log via `logging` only; node exceptions route through `_sanitize_error`; producer outages are logged, never `print()`ed.

## Self-Check: PASSED
