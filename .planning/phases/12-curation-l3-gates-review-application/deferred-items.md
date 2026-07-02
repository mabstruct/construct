# Deferred Items — Phase 12

## From Plan 12-02 (out-of-scope, pre-existing RED scaffolds)

10 failing tests in `tests/llm/test_curation_run.py` are Wave 1 RED scaffolds for
the **curation_run.py HITL graft (Plans 12-03 / 12-04)** — the interrupt/resume,
write-node, and event-emission machine. They are NOT in the scope of Plan 12-02
(which only creates the two L3 judgment gates + config). `curation_run.py` does
not import `curation_promote`/`curation_connect`, so these failures are causally
isolated from this plan's changes.

Deferred failing tests (resolved by Plans 03-04):
- test_no_writes_before_approval
- test_reviewed_promotion_applied
- test_reviewed_connection_idempotent
- test_reviewed_archive_applied
- test_single_consolidated_gate
- test_empty_queue_no_pause
- test_no_unreviewed_writes
- test_cross_process_resume
- test_inspect_pending_review
- test_curation_events_emitted
