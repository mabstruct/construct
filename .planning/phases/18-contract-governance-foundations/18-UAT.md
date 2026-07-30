---
status: testing
phase: 18-contract-governance-foundations
source: [18-VERIFICATION.md]
started: 2026-07-30T23:00:00Z
updated: 2026-07-30T23:00:00Z
---

## Current Test

number: 1
name: ActivityList.jsx renders live Python-emitted events
expected: |
  Load a workspace with Python-emitted events in the CONSTRUCT Views SPA. Each activity
  row shows a non-blank agent and action (not empty cells), with target, detail and
  result populated where the source event carries them. An escalated event shows the
  amber "escalated" badge.
awaiting: user response

## Tests

### 1. ActivityList.jsx renders live Python-emitted events

expected: Each row shows a non-blank agent and action; an escalated event shows the amber "escalated" badge. No blank rows for events that carry data.
result: [pending]

why_human: |
  Plan 18-05 conformed the SPA's activity reader to D-17's canonical event shape —
  the component's destructured keys (`e.ts` / `e.agent` / `e.action` / `e.target` /
  `e.detail` / `e.result`) now match `views/lib/parse_events.py`'s canonical output
  exactly. That match was confirmed by source review only. There is no JS toolchain
  in this environment to execute or type-check the component, and installing one is
  forbidden by T-18-SC, so it was never exercised at runtime. The 18-05 SUMMARY
  itself flags this with `human_judgment: true`.

  This is the one deliverable in Phase 18 that no automated check covers. Everything
  else in the phase — including all five code-review blockers and the two-layer
  GOV-05 fix — was verified by live reproduction against running code.

how_to_test: |
  1. Pick a workspace with a populated event log, e.g. `test-ws/my-construct`
     (its `log/events.jsonl` is already in the canonical shape; 15/15 lines are kept
     by the reader).
  2. Run `construct views generate --workspace test-ws/my-construct` to write the
     projection, then build and serve the SPA from the scaffold template.
  3. Open the activity view and confirm the rows are populated.

  Note the D-17 consequence recorded in 18-04's SUMMARY: fixtures under
  `tests/fixtures/v02/multi-domain-medium` carry only `event`/`timestamp`/`details`,
  so all 30 of their lines are deliberately dropped with a warning naming file and
  line. Blank output from THAT fixture is correct behaviour, not a defect — use a
  canonical-log workspace for this test.

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
