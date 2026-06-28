---
status: partial
phase: 11-curation-pipe-steps
source: [11-VERIFICATION.md]
started: 2026-06-28T22:05:00Z
updated: 2026-06-28T22:05:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual rendering of `_render_curation_result` (criterion #2)
expected: Run `construct curation run -w <real-workspace>` (without `--json`). Output shows status (completed/degraded), run_id (`cur-<timestamp>-<hex>`), and a per-step line for each of the 5 real steps plus 3 deferred steps. Completed real steps carry concrete summaries (e.g. "0 error(s), N warning(s)", "N decay candidate(s) over a 28d window"); deferred nodes show "skipped — <step> deferred to Phase 12". The status line clearly distinguishes completed vs degraded.
result: [pending]

### 2. Product decision: exit-code semantics for degraded runs (WR-04)
expected: Deliberate product decision — should `construct curation run` exit 0 or non-zero when a required check degrades? Currently `_curation_result_to_operation` (catalog.py:589) sets `success = result.status != "failed"`, so a `degraded` run maps to success=True and the CLI exits 0. Confirm whether this is the intended contract or should be changed (`success = result.status == "completed"`) so automation/CI can detect required-step failures via exit code.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
