---
phase: 11-curation-pipe-steps
plan: 02
subsystem: curation-workflow
tags: [langgraph, curation, sqlite-saver, findings, decay, orphan, status-aggregation]

# Dependency graph
requires:
  - phase: 10-research-run
    provides: durable research.run template (graph + SqliteSaver + run-id + run/inspect runners) curation_run mirrors
  - phase: 11-curation-pipe-steps
    plan: 01
    provides: tests/llm/test_curation_run.py red suite + curation_workspace fixture this plan turns GREEN
provides:
  - src/construct/llm/curation_run.py — deterministic curation.run module (contract + linear §4.3 graph + run/inspect runners)
  - CurationRunInput/CurationInspectInput/CurationStepResult/CurationRunResult public contract for Plan 03 catalog/CLI wiring
  - run_curation_run/inspect_curation_run/build_curation_run_graph public runners
affects: [11-03 catalog/cli/mcp wiring, phase-12 curation gates (promotion/decay action)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Findings-only deterministic scan: decay/orphan select candidate IDs from load_cards date math + connection-degree map, no queue schema (D-04)"
    - "Per-node try/except -> failed CurationStepResult with sanitized reason, so a bad card degrades honestly rather than crashing (D-08/T-11-02)"
    - "Run-level D-09 aggregation: degraded iff a REQUIRED step is failed/skipped; deferred nodes are required=False so they never degrade (Pitfall 5)"
    - "Python-mode load_cards dumps: created/last_verified are datetime.date, lifecycle is Lifecycle enum — isinstance-guarded date coercion + .value archived comparison"

key-files:
  created:
    - src/construct/llm/curation_run.py
  modified: []

key-decisions:
  - "_initial_state uses the single-arg form _initial_state(inp) (matching the Plan 01 red suite and 11-01 SUMMARY), not the plan's _initial_state(inp, run_id); the run_id is derived inside from inp.run_id or _new_run_id()"
  - "Lifecycle imported at module top (not per-node) so the archived-exclusion comparison Lifecycle.archived.value reads identically in both decay_scan and orphan_scan"
  - "Terminal curation_cycle_complete event is appended in the runner (not a graph node) via EventAgent.curator; the events state channel stays plain (no reducer) since no node emits events"

patterns-established:
  - "Pattern: linear LangGraph sibling of an interrupt-driven workflow — copy the StateGraph/add_node/add_edge/compile shape, drop add_conditional_edges + interrupt + outage routing"
  - "Pattern: _aggregate_status(steps) shared by run and inspect so a re-read reproduces the same D-09 verdict from persisted steps"

requirements-completed: []  # CUR-01 NOT marked — it requires the CLI/MCP surface delivered by Plan 03 (contract suite still RED)

# Metrics
duration: 25min
completed: 2026-06-28
---

# Phase 11 Plan 02: Curation Run Module Summary

**`src/construct/llm/curation_run.py` — the real deterministic curation pipeline (five findings-bearing steps over the full spec §4.3 topology, three explicit deferred skips, durable SqliteSaver checkpointing, and D-09 completed/degraded aggregation) that replaces the v0.3 placeholder no-ops and turns the Plan 01 llm red suite GREEN.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 completed
- **Files modified:** 1 created (+1 SUMMARY)

## Accomplishments

- **Task 1 — scaffold:** Added `CurationRunState` (plain serializable channels with a `steps` `operator.add` reducer), the four in-module pydantic models (`CurationRunInput`/`CurationInspectInput` with the kebab-case `run_id` trust-boundary guard, `CurationStepResult`, `CurationRunResult`, all `extra="forbid"`), `_new_run_id`/`_initial_state`, the `load_config` node reading decay/orphan thresholds from `governance.yaml` (D-05), and the persistent `_open_checkpointer` at `.construct/workflow/curation-run.sqlite`.
- **Task 2 — nodes + graph:** Implemented the five real step nodes (`integrity_check` → `validate_workspace` primitives; `decay_scan`/`orphan_scan` governance-thresholded findings-only candidate scans; `connection_maintenance` → `bridge_detect`; `compile_report` → `graph_status`), the three deferred skip-nodes (`promotion_review`/`process_inbox`/`views_refresh_hook`), and the purely linear `build_curation_run_graph` over spec §4.3 order. Every real node wraps its body in try/except so a failure surfaces as a `status="failed"` step (D-08/T-11-02).
- **Task 3 — runners:** Implemented `run_curation_run` (single `graph.invoke` to completion, `_aggregate_status` D-09 roll-up, one terminal `curation_cycle_complete` event via `EventAgent.curator`) and `inspect_curation_run` (reads persisted terminal state via `graph.get_state`, never re-runs; nonexistent run → `failed`). Connection closed in `finally` in both.

## Task Commits

Each task was committed atomically:

1. **Task 1: Module scaffold — contracts, state, run-id guard, checkpointer, load_config** - `699883b` (feat)
2. **Task 2: Five real step nodes + three deferred skip-nodes + linear graph builder** - `1f15078` (feat)
3. **Task 3: run/inspect runners + D-09 status aggregation + terminal event** - `ead95fc` (feat)

**Plan metadata:** this commit (docs)

## Files Created/Modified

- `src/construct/llm/curation_run.py` (583 lines) — the complete curation.run contract, linear §4.3 LangGraph, durable checkpointer, and run/inspect runners. Mirrors `research_run.py` with the human-gate/interrupt/outage-routing/write-node machinery removed.

## Contract Delivered (for Plan 03)

Public names Plan 03 wires into the capability registry / CLI / MCP:
- `build_curation_run_graph(checkpointer)`, `_initial_state(inp)`, `run_curation_run(inp)`, `inspect_curation_run(inp)`
- `CurationRunInput(workspace_path, run_id=None)`, `CurationInspectInput(workspace_path, run_id)`
- `CurationStepResult(step, status, required, findings, summary, reason)`, `CurationRunResult(status, run_id, steps, events, message)`

## Deviations from Plan

### Contract alignment

**1. [Rule 1 - Contract] `_initial_state` is single-arg `_initial_state(inp)`, not `_initial_state(inp, run_id)`**
- **Found during:** Task 1 (and required by Task 3 runner shape)
- **Issue:** The plan's Task 1/Task 3 action text specifies `_initial_state(inp, run_id)`, but the Plan 01 red suite calls `curation_run._initial_state(curation_run.CurationRunInput(...))` with a single argument, and the 11-01 SUMMARY explicitly decided "`_initial_state` mirrors research_run's single-arg form `_initial_state(inp)`". The executable spec (the test) is authoritative.
- **Fix:** Implemented `_initial_state(inp)` deriving `run_id = inp.run_id or _new_run_id()` internally (exactly like `research_run._initial_state`). `run_curation_run` generates the `run_id`, builds a `resolved` `CurationRunInput` carrying it, and passes that to `_initial_state` so the state's `run_id` matches the `thread_id` — identical to the research runner idiom.
- **Files modified:** src/construct/llm/curation_run.py
- **Commit:** `699883b`, `ead95fc`

**2. [Rule 1 - Avoid false-complete] CUR-01 left unmarked despite the plan frontmatter `requirements: [CUR-01]`**
- **Found during:** State update
- **Issue:** CUR-01 is worded "User can run `curation.run` **through the CONSTRUCT CLI/MCP surface** and receive real ... results." Plan 02 delivers the module, but the CLI/MCP registration/wiring is Plan 03 — and `tests/contract/test_curation_run_cli_mcp.py` is still RED (6 failing). Marking CUR-01 complete now would be a false-complete signal; the 11-01 SUMMARY explicitly deferred CUR-01 to "Plans 02-03".
- **Fix:** Reverted the `requirements.mark-complete CUR-01` edit to REQUIREMENTS.md (CUR-01 stays Pending). Plan 03 marks it once the CLI/MCP surface lands and the contract suite goes GREEN.
- **Files modified:** .planning/REQUIREMENTS.md (reverted to unchanged)
- **Commit:** n/a (no net change)

No other deviations — the module follows the 11-PATTERNS shapes and the threat-model mitigations (T-11-01 run-id guard, T-11-02 per-node try/except, T-11-03 stderr-only logging, T-11-04 no canonical writes) exactly.

## Verification

- `pytest tests/llm/test_curation_run.py -q` → **8 passed** (full Plan 01 llm red suite now GREEN).
- `pytest tests/llm/test_research_run.py -q` → 26 passed (no regression; module is additive).
- `pytest tests/contract/test_curation_run_cli_mcp.py -q` → 6 RED + 1 GREEN — **expected**; CLI/MCP/registry wiring is Plan 03. The GREEN guard `test_mcp_no_hardcoded_curation` confirms no `mcp/server.py` edit.
- `grep -c "add_conditional_edges\|interrupt(\|print("` → 0 (linear graph, stderr-only logging).
- `grep -c "from_conn_string"` → 0 (persistent-connection checkpointer).
- `Lifecycle.archived` archived-exclusion present in BOTH `decay_scan` and `orphan_scan`; orphan degree counts both `record.from_` and `record.to`.

## Threat Surface

No new trust boundaries beyond the plan's `<threat_model>`. The run_id boundary (T-11-01) is guarded at the input-model `field_validator`; node robustness (T-11-02) via per-node try/except; transport hygiene (T-11-03) via logging-only; no canonical SOT write (T-11-04) verified by `test_no_canonical_writes`. No package installs (T-11-SC).

## Known Stubs

None. The three deferred nodes (`promotion_review`/`process_inbox`/`views_refresh_hook`) are intentional, explicit `skipped`/`required=False` steps carrying a "deferred to Phase 12" reason (D-10) — they are not silent placeholders and are asserted on by `test_deferred_nodes_visible_skipped`. Phase 12 implements their bodies.

## Self-Check: PASSED
- FOUND: src/construct/llm/curation_run.py
- FOUND: .planning/phases/11-curation-pipe-steps/11-02-SUMMARY.md
- FOUND commit: 699883b (Task 1)
- FOUND commit: 1f15078 (Task 2)
- FOUND commit: ead95fc (Task 3)
