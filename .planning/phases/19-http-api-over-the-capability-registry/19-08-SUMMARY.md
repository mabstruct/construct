---
phase: 19-http-api-over-the-capability-registry
plan: 08
subsystem: llm
tags: [run-enumeration, http-07, langgraph-checkpoints, durable-state, capability-registry, d-13]

# Dependency graph
requires:
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-04's capability classification maps (WORKSPACE_FIELD / INSTALL_ROOT_FIELD) and 19-05's COVERAGE.md exposure ledger with its cardinality guard"
provides:
  - "src/construct/llm/workflow_list.py — list_workflow_runs and the RunSummary shape, spanning all three durable stores"
  - "The workflow.list capability, registered with BOTH a CLI name and an MCP tool name, so CLI, MCP and HTTP gain run enumeration in the same act (D-13)"
  - "tests/contract/test_workflow_list.py — 20 tests covering three-store coverage, empty/single cases, ordering, run-id collision, status filtering, and the no-path-leak property"
affects: [19-09, 19-10, 21-static-ui, 23-review-wizards]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SELECT DISTINCT thread_id against the checkpointer's own schema, so listing latency scales with run count rather than run length"
    - "Per-run status delegated to the existing inspect primitives, so no fourth status vocabulary is invented"
    - "Registered as a capability rather than a CLI command, so a browser-side reader cannot exist over durable state the CLI cannot see"
    - "An unmatched status filter is an empty list, not a validation error — the three workflow families already carry three status vocabularies, and a closed enum here would be a fourth"

key-files:
  created:
    - src/construct/llm/workflow_list.py
    - tests/contract/test_workflow_list.py
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/capabilities/workspaces.py
    - src/construct/api/COVERAGE.md
    - tests/contract/test_capability_seam.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py
    - CONSTRUCT-CLAUDE-spec/artifact-catalog.md

key-decisions:
  - "D-13 recorded: workflow.list sets BOTH a CLI name and an MCP tool name, unlike its CLI-only workflow.status sibling. The asymmetry is the decision, not an oversight — the reason enumeration is a registry capability at all is that all three surfaces gain it at the same moment."
  - "Enumeration reads SELECT DISTINCT thread_id from the checkpoints table rather than iterating checkpoint tuples: listing cost is a function of how many runs exist, not how long they ran."
  - "Status comes from inspect_curation_run / inspect_research_run / inspect_daily_run rather than being re-derived, so the three existing status vocabularies are reused rather than a fourth being invented."
  - "Daily runs are read from their JSON receipts, which are not checkpoints — a checkpoint-only listing would report zero daily runs while daily.inspect answered for them. Pinned by a test that asserts exactly that counterfactual."
  - "status is a plain optional string, deliberately not an enum: an unmatched filter is an empty list, not a validation error."
  - "WorkflowListInput spells its field `workspace: Path` like workflow.status, not `workspace_path: str` like the run family, so the two workflow.* capabilities present one vocabulary to a caller reading them side by side."

requirements-completed: [HTTP-07]

coverage:
  - id: D1
    description: "Listing spans all three durable stores — curation checkpoints, research checkpoints, and daily JSON receipts — so no run becomes unreachable after its id is lost"
    requirement: HTTP-07
    verification:
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_all_three_stores_are_read"
        status: pass
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_a_checkpoint_only_listing_could_not_have_produced_the_daily_entry"
        status: pass
    human_judgment: false
  - id: D2
    description: "A run paused awaiting review appears with a status saying so, alongside its pending queue's identifying handle"
    requirement: HTTP-07
    verification:
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_a_paused_run_reports_awaiting_review_and_its_queue_handle"
        status: pass
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_a_completed_run_carries_no_gate_handle"
        status: pass
    human_judgment: false
  - id: D3
    description: "Enumeration reads distinct thread ids from the checkpoint schema rather than iterating checkpoint tuples, so latency scales with run count not run length"
    requirement: HTTP-07
    verification:
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_enumeration_never_uses_the_library_checkpoint_listing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Per-run status comes from the existing inspect primitives, so no fourth status vocabulary is invented"
    requirement: HTTP-07
    verification:
      - kind: code
        ref: "src/construct/llm/workflow_list.py imports inspect_curation_run / inspect_research_run / inspect_daily_run"
        status: pass
    human_judgment: false
  - id: D5
    description: "Run listing is a registry capability reachable from CLI, MCP and HTTP at the same moment — not a browser-only reader over durable state"
    requirement: HTTP-07
    verification:
      - kind: code
        ref: "src/construct/capabilities/catalog.py — the workflow.list record sets both cli_name and mcp_name (D-13)"
        status: pass
      - kind: contract
        ref: "tests/contract/test_mcp_contracts.py#test_mcp_tool_count includes construct_workflow_list"
        status: pass
      - kind: contract
        ref: "tests/contract/test_http_surface.py#test_the_ledger_has_one_row_per_registered_capability (COVERAGE.md row added)"
        status: pass
    human_judgment: false
  - id: D6
    description: "An empty workspace returns an empty list with the run-happened flag true, never an error; exactly one run returns exactly one entry"
    requirement: HTTP-07
    verification:
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_an_empty_workspace_lists_nothing_and_is_not_an_error"
        status: pass
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_a_workspace_with_exactly_one_run_lists_exactly_one_entry"
        status: pass
    human_judgment: false
  - id: D7
    description: "Two runs of different workflow types sharing a run id are listed as two distinct entries discriminated by workflow, never merged"
    requirement: HTTP-07
    verification:
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_a_shared_run_id_across_workflows_is_two_entries"
        status: pass
    human_judgment: false
  - id: D8
    description: "The listing order is specified and stable: sorted by workflow name then run id, and two consecutive calls return the same order"
    requirement: HTTP-07
    verification:
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_entries_are_ordered_by_workflow_then_run_id"
        status: pass
      - kind: contract
        ref: "tests/contract/test_workflow_list.py#test_two_consecutive_calls_return_the_same_order"
        status: pass
    human_judgment: false
---

# 19-08: Runs enumerable across three stores, on three surfaces

## What shipped

`src/construct/llm/workflow_list.py` enumerates every durable workflow run in a workspace by reading all three stores that actually hold them: the curation checkpoint database, the research checkpoint database, and `.construct/workflow/daily/<run_id>.json` receipts. The third is the one a plausible implementation misses — daily runs are not checkpointed, so a checkpoint-only listing reports zero daily runs while `daily.inspect` happily answers for them. That counterfactual is pinned by its own test rather than left as a comment.

`workflow.list` is registered as a capability with **both** a CLI name and an MCP tool name. Its `workflow.status` sibling directly above it in `catalog.py` is CLI-only, and the asymmetry is the point of D-13: run enumeration exists as a registry capability precisely so CLI, MCP and HTTP gain it in one act. A browser-side run list built any other way would have been a reader for durable state the CLI could not see.

Registry: 29 → 30 capabilities. Suite: **1096 passed, 22 skipped, 0 failed**.

## Two things worth a reviewer's attention

**Eight guards fired, and every one was satisfied by registering the capability rather than by loosening the guard.** Adding the 30th capability tripped the seam's `REGISTRY_SIZE` tripwire, 19-05's COVERAGE.md cardinality guard, the MCP tool-name set and its payload map, the artifact catalog's two row checks, and the registry id set. That is the designed behaviour of those guards — a capability cannot join this system without being declared everywhere it is now reachable from. Two of the eight looked alarming (`test_every_mcp_handler_invokes_without_type_error` and `test_mcp_handlers_report_rather_than_raise_on_an_invalid_path` reporting a raised `KeyError`) but were the test's own `_payload_for` fixture map lacking an entry — the `KeyError` came from the helper, not from a handler.

**Latency was made a property of run count, not run length.** Enumeration issues `SELECT DISTINCT thread_id` against the `checkpoints` table the checkpointer's own schema owns, rather than iterating checkpoint tuples through the library's listing API. A long-running curation with thousands of checkpoints costs the same to enumerate as a short one. This couples the module to a schema the pinned checkpoint library owns, which the module docstring states plainly, and a test asserts the library listing is never used so the coupling cannot be quietly reintroduced.

## Provenance — how this plan was executed

Tasks 1 and the bulk of Task 2 were executed by the assigned executor agent (`6bbd85c`, `607223c`). The agent then stalled (`no progress for 600s`) after a series of session-wide `Connection closed mid-response` transport failures. The remaining work — registering the new capability in the six ledgers and tripwires listed above, plus this SUMMARY — was completed **inline by the orchestrator** (`71cf9aa`), at the user's direction.

Worth noting for the record: the agent had been instructed to commit at each coherent checkpoint rather than batch, and that instruction is why `607223c` survived the stall. No work was lost or redone. A reviewer should weigh `71cf9aa` knowing it was not produced by an independent executor context.

## Files touched beyond `files_modified`

Three, all forced by registering a capability and none discretionary:

- `tests/unit/test_capability_registry.py` — the registry id set is an exact-equality assertion.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — two row checks (`test_every_capability_id_has_a_catalog_row`, `test_every_mcp_tool_has_a_catalog_row`) assert the catalog is complete.
- `src/construct/capabilities/workspaces.py` — one line, classifying `workflow.list` as `workspace`-scoped, without which 19-04's classification guard fails.

## Known-red baseline, unchanged

`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot` fails in any git worktree for the reason recorded in `deferred-items.md` (empty fixture directories git cannot represent). Materialising them locally makes the suite fully green. Untouched here.
