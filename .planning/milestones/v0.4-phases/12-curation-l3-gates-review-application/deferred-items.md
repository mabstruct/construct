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

## From Plan 12-03 (read-side HITL graft) — out-of-scope items

Plan 12-03 turned the read-side tests GREEN (no_writes_before_approval,
single_consolidated, empty_queue, no_unreviewed_writes) and left the write-side
tests RED for Plan 12-04. Out-of-scope discoveries:

- **Contract tests RED (Plan 05/06 targets):** `tests/contract/test_curation_run_cli_mcp.py`
  has 6 failing tests (`test_registered`, `test_shims_reject_positional_args`,
  `test_in_mcp_tool_list`, `test_mcp_server_exposes_curation`, `test_cli_commands_present`,
  `test_no_placeholder_curation_path`). They assert `curation.review` / `card.evaluate`
  registration in `catalog.py` + `cli.py` and placeholder removal — none of which Plan 03
  touches (Plan 03 only modifies `curation_run.py`). Verified pre-existing at the Plan-03
  baseline (identical 6 failures with Task-2 changes stashed). Plans 05/06 own these.
