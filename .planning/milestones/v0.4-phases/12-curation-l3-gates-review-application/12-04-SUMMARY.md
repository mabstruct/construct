---
phase: 12-curation-l3-gates-review-application
plan: 04
subsystem: api
tags: [langgraph, hitl, interrupt-resume, curation, sqlite-checkpointer, event-log]

# Dependency graph
requires:
  - phase: 12-03
    provides: "read-side HITL spine — gate_queue state, CurationProposal envelope, three producer nodes, interrupt-only process_inbox, empty-queue short-circuit, minimal review_curation_run/CurationReviewInput"
  - phase: 11
    provides: "deterministic curation.run graph (integrity/decay/orphan/connection/report), _open_checkpointer, _aggregate_status, _validate_run_id"
provides:
  - "Three post-gate apply nodes (apply_promotions/apply_connections/apply_archives) that write ONLY after Command(resume=...)"
  - "Decision resolution (_normalize_decision/_resolve_decisions) with approve-all/reject-all, default = gate recommendation (D-07); escalate is review-only"
  - "Idempotent canonical writes: skip-if-at-target promotion, add_connection dedup, skip-if-archived"
  - "Extended review_curation_run (write-side grafted), run-start pause detection, inspect_curation_run awaiting_review branch"
  - "Full event emission per spec 6.6: workflow_step_complete per deterministic step + gate_review_approved/rejected per proposal + single curation_cycle_complete"
affects: [12-05 (curation.review/card.evaluate registration + placeholder removal), curation-cycle skill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WRITE BOUNDARY: canonical writes live strictly downstream of the interrupt node (CUR-03 by construction)"
    - "operator.add reducers on events/rejected/escalated so multi-node contributions survive the interrupt/resume boundary without overwrite"
    - "Terminal node (compile_report) stamps status + emits the single cycle-complete event; runners read state, never re-emit"

key-files:
  created: []
  modified:
    - src/construct/llm/curation_run.py
    - src/construct/storage/workspace.py

key-decisions:
  - "escalate proposals are review-only this phase: recorded as escalated with NO SOT write (Open-Q 3 / D-07)"
  - "curation_cycle_complete emitted from compile_report (the one node both terminal paths run exactly once) rather than the runners, so it never double-fires across resume"
  - "load_cards normalizes lifecycle to its string value (enum -> str) while keeping recency dates python-mode; required so the authoritative target tests can compare str(lifecycle) to bare values"

patterns-established:
  - "Per-item apply-node isolation: each write wrapped in try/except so one failure never aborts the batch (D-08)"
  - "Idempotent apply: skip-if-at-target / add_connection dedup / skip-if-archived make rerun and crash-resume no-ops"

requirements-completed: [CUR-03, CUR-04]

# Metrics
duration: 35min
completed: 2026-07-02
---

# Phase 12 Plan 04: Curation Review Application (Write-Side) Summary

**Grafted the write-side of the curation HITL machine: three approved-only, idempotent post-gate apply nodes behind the single human interrupt, full per-step + gate-review event emission (spec 6.6), and pause-aware review/inspect runners — the entire tests/llm/test_curation_run.py suite is GREEN.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 completed
- **Files modified:** 2 (`curation_run.py`, `workspace.py`)
- **Commits:** `911254c` (Task 1), `0fd6dc1` (Task 2)

## Accomplishments

### Task 1 — Post-gate apply nodes + decision resolution + WRITE BOUNDARY (`911254c`)
- `apply_promotions` → `edit_card(..., author=CardAuthor.curator)`; skip-if-already-at-target-lifecycle. `growing`/`mature` only (Discrepancy 1). escalate/no-target → recorded escalated, NO write.
- `apply_connections` → `add_connection(..., created_by=ConnectionAuthor.construct)`; relies on the built-in dup dedup ("Connection already exists") so rerun is a no-op.
- `apply_archives` → `archive_card(..., author=CardAuthor.curator)`; skip-if-already-archived.
- `_normalize_decision`/`_resolve_decisions`: default per-item verdict = the gate recommendation (D-07); approve-all reproduces recommendations, reject-all writes nothing; only APPROVED verdicts write.
- Wired `process_inbox → apply_promotions → apply_connections → apply_archives → compile_report`; made `rejected`/`escalated`/`events` `operator.add` reducers.
- Per-item `try/except` isolation (D-08); `_card_lifecycle_map` idempotency helper; `_emit` audit-event helper.

### Task 2 — Events + terminal status + pending-review inspect (`0fd6dc1`)
- `workflow_step_complete` emitted from every deterministic step (integrity/decay/orphan/promotion_review/connection_maintenance) and the apply/report nodes.
- `compile_report` now stamps the D-09 `status` onto the state channel and emits the single `curation_cycle_complete` event (runs exactly once on both the empty-queue and post-gate terminal paths).
- Runners read `status`/`events` from graph state instead of manually re-emitting.
- `inspect_curation_run` gained an `awaiting_review` branch (before the empty-values guard) surfacing `gate_queue` without resuming.
- `process_inbox` stays completely event-free (Pitfall 1 — no double-fire on resume).

## Verification

- `.venv/bin/pytest tests/llm/test_curation_run.py -q` → **18 passed** (all reviewed-write + resume + inspect + events tests; read-side + legacy Phase-11 tests stay green).
- `.venv/bin/pytest tests/llm/ -q` → **101 passed** (no research_run regression).
- Full suite excluding contract → **294 passed**.
- **Write-boundary grep:** `process_inbox` holds exactly one `interrupt(`, and zero of `edit_card`/`add_connection`/`archive_card`/`append_event`/`_emit(`/`write_text`/`.write(`. The three write symbols live at lines 873/920/969, all inside the apply nodes downstream of `process_inbox` (line 744) — no write symbol upstream of the interrupt.

## Invariants held

- **Only-approved writes:** rejected AND escalate produce no SOT write this run (`test_no_unreviewed_writes`, `test_reviewed_promotion_applied` reject path).
- **Idempotent:** rerun/crash-resume never double-writes — skip-if-at-target, add_connection dedup, skip-if-archived (`test_reviewed_connection_idempotent`).
- **Completed-run no-rewrite:** `review_curation_run`'s paused-state guard (`snap.next != ("process_inbox",)`) returns completed/failed without re-running writes (WR-05).
- **Event coverage:** a `workflow_step_complete` event fires for every deterministic step, `gate_review_approved`/`gate_review_rejected` per reviewed proposal, and one `curation_cycle_complete`; nothing fires from `process_inbox`.
- **Cross-process resume:** pause in one SqliteSaver, re-open on the same DB, single resume completes (`test_cross_process_resume`).

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 - Blocking] `load_cards` lifecycle normalization (`src/construct/storage/workspace.py`)**
- **Found during:** Task 1 (`test_reviewed_promotion_applied`, `test_reviewed_archive_applied`).
- **Issue:** The authoritative target tests compare `str(c["lifecycle"])` from `WorkspaceLoader.load_cards()` to bare values (`"growing"`, `"archived"`). `load_cards` used python-mode `model_dump()`, so `lifecycle` was a `Lifecycle` enum whose `str()` is `"Lifecycle.growing"` — the tests could not pass regardless of the write-side code (they read the workspace directly, not via `curation_run.py`).
- **Fix:** In `load_cards`, normalize `card_data["lifecycle"]` to its string value (`getattr(lifecycle, "value", lifecycle)`) while keeping recency dates (`created`/`last_verified`) as `datetime.date` objects — the curation decay/orphan scans explicitly rely on python-mode dates (`decay_scan` comment), so a full `mode="json"` switch was deliberately avoided. `Lifecycle` is a `(str, Enum)`, so all existing `== Lifecycle.X` / `.value` / `getattr(...,"value",...)` comparisons keep working against the string form; no code calls `.value` on a lifecycle dict result (verified by grep), and no date math on load_cards dates exists in research_score/bridge_detect.
- **Files modified:** `src/construct/storage/workspace.py`
- **Commit:** `911254c`
- **Blast radius verified:** `tests/unit`, `tests/pipelines`, `tests/llm`, `tests/storage`, `tests/integration` all green (294 passed excluding the intentionally-RED Plan 12-05 contract suite).

## Notes for Plan 12-05

- `tests/contract/test_curation_run_cli_mcp.py` stays RED as expected (6 failing): `curation.review` / `card.evaluate` are not yet registered in `catalog.py`, the CLI `curation review` command is absent, and `_get_workflow_steps` (the D-10 placeholder in catalog.py + cli.py) is not yet removed. All are 12-05 scope; none are regressions from this plan.

## Self-Check: PASSED
- `src/construct/llm/curation_run.py` contains `def apply_promotions`, `def apply_connections`, `def apply_archives`, `def review_curation_run` — FOUND.
- Commits `911254c` and `0fd6dc1` — FOUND in git history.
- `tests/llm/test_curation_run.py` — 18 passed.
