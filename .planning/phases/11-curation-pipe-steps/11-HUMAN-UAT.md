---
status: complete
phase: 11-curation-pipe-steps
source: [11-VERIFICATION.md]
started: 2026-06-28T22:05:00Z
updated: 2026-06-29T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Visual rendering of `_render_curation_result` (criterion #2)
expected: Run `construct curation run -w <real-workspace>` (without `--json`). Output shows status (completed/degraded), run_id (`cur-<timestamp>-<hex>`), and a per-step line for each of the 5 real steps plus 3 deferred steps. Completed real steps carry concrete summaries (e.g. "0 error(s), N warning(s)", "N decay candidate(s) over a 28d window"); deferred nodes show "skipped — <step> deferred to Phase 12". The status line clearly distinguishes completed vs degraded.
result: pass
evidence: "Ran `construct curation run -w test-ws/ping-eon` (2026-06-29). Output rendered status: completed, run_id cur-20260629-104923-9e8d3c, per-step lines with concrete summaries (2 decay / 2 orphan candidates, integrity error/warning counts) and 3 deferred nodes clearly marked 'skipped — <step> deferred to Phase 12'. Failure render also confirmed (✗ curation.run failed: FileNotFoundError on a broken workspace). User confirmed pass."

### 2. Product decision: exit-code semantics for degraded runs (WR-04)
expected: Deliberate product decision — should `construct curation run` exit 0 or non-zero when a required check degrades? Currently `_curation_result_to_operation` (catalog.py:589) sets `success = result.status != "failed"`, so a `degraded` run maps to success=True and the CLI exits 0. Confirm whether this is the intended contract or should be changed (`success = result.status == "completed"`) so automation/CI can detect required-step failures via exit code.
result: pass
decision: "Accepted — exit code 0 is intentional. Contract is 'exit 0 = the cycle ran without crashing', NOT 'exit 0 = all checks passed'. Failure/degraded is visible via the run-level status field, per-step status, JSON output, and the durable curation_cycle_complete event (detail carries the status). Automation branches on data.status, not exit code. Recorded in memory project_curation_exit_contract. Do not flip the success mapping without re-deciding."

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all items resolved]
