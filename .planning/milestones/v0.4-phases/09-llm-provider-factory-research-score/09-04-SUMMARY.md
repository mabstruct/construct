---
phase: 09-llm-provider-factory-research-score
plan: 04
subsystem: capabilities
tags: [research-score, capability-registry, cli, mcp-parity, d-10, d-13, total-outage, payload-flatten]

requires:
  - phase: 09-llm-provider-factory-research-score
    provides: run_gate + ResearchScoreInput/ResearchScoreGateOutput + ResearchScoreOutageError (Plans 02/03)
  - phase: 08-search-provider-spine-contract-foundation
    provides: SearchResult / SearchBatchOutput payload shapes + research.search registry analog
provides:
  - research.score CapabilityRecord + _research_score_shim adapter (outage -> success=False, T-09-03/T-09-04)
  - automatic MCP exposure as construct_research_score (registry-driven, no server.py edit)
  - "construct research score" CLI subcommand — required --workspace (D-12), --results-file/stdin payload (D-10), url/score/tier/action table + degraded notice (D-13), --json canonical contract
  - CLI/MCP registry parity (one structured OperationResult object on both surfaces)
affects: [research.score, research.run]

tech-stack:
  added: []
  patterns:
    - "Module-level _research_score_shim adapter (mirrors _research_search_shim) over inline lambda — keeps the outage->success=False mapping testable"
    - "Pre-fetched payload flattener accepts flat list[SearchResult] OR a batches envelope, validating each via SearchResult.model_validate at the trust boundary (T-09-V5)"
    - "Default CLI path renders a human table then defers --json to _display_result so the canonical ResearchScoreGateOutput is the single JSON contract (D-13)"
    - "_display_result already raises typer.Exit(1) on success=False — outage maps to a non-zero CLI exit for free"

key-files:
  created:
    - tests/llm/test_research_score_capability.py
    - tests/contract/test_research_score_cli_mcp.py
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py
    - tests/llm/test_research_score.py

key-decisions:
  - "Resumed substantial uncommitted partial work (4 files, no prior commits/SUMMARY) in place rather than re-executing from scratch — the implementation was ~90% complete and correct"
  - "Fixed a latent module-scope bug: two 'list' Typer commands shadow the builtin, so the payload flattener references builtins.list explicitly (isinstance(payload, list) was raising TypeError)"
  - "Updated three pre-existing inventory tests (tool-count, handler-invoke payload map, catalog ids) to account for the new capability — expected maintenance, not test-gaming"
  - "Removed the now-redundant Plan 04 parity stub (test_research_score.py) — its coverage is delivered by the new contract parity test; clears the lone remaining skip"

patterns-established:
  - "Capability surfaces (CLI + MCP) added purely via one CapabilityRecord + one shim; MCP tool is auto-discovered, proving the registry-as-single-source design"

requirements-completed: [RSCH-01]

duration: 20min
completed: 2026-06-28
---

# Phase 9 Plan 04: research.score CLI + MCP Exposure Summary

**Exposes the `research.score` L3 gate on both CLI and MCP through the shared capability registry (RSCH-01 criterion 1): one `CapabilityRecord` + `_research_score_shim` adapter, a `construct research score` subcommand with pre-fetched-payload plumbing (D-10) and a D-13 table/JSON result shape, automatic `construct_research_score` MCP exposure, and contract tests proving CLI/MCP parity and the D-09 outage→`success=False` mapping.**

## Performance

- **Duration:** ~20 min (resume + finish of partial work)
- **Tasks:** 3/3 complete
- **Files created:** 2 / **modified:** 5

## Accomplishments

- Registered `research.score` in the capability catalog with `input_model=ResearchScoreInput`, `output_model=OperationResult`, `cli_name="research.score"`, `mcp_tool_name="construct_research_score"`.
- `_research_score_shim` builds `ResearchScoreInput`, calls `run_gate("research.score", ...)`, maps a `ResearchScoreOutageError` (D-09) to `OperationResult(success=False, data={"total_outage": True})` with a sanitized message (T-09-03/T-09-04), and wraps a successful gate into `OperationResult(success=True, data=output.model_dump(mode="json"))`.
- Added the `construct research score` CLI subcommand: required `--workspace`/`-w` (D-12); pre-fetched payload via `--results-file` or stdin (D-10) with a flattener that accepts a flat `list[SearchResult]` OR a `batches` envelope and validates each item through `SearchResult` at the boundary; a `url/score/tier/action` table plus a `degraded/retried/errors` notice for the default path; `--json` fall-through to the canonical `ResearchScoreGateOutput` contract (D-13).
- MCP exposure is automatic — `construct_research_score` appears in `registry.list_mcp_tools()` with no `server.py` edit (verified by a contract assertion).
- Contract tests prove: table render + exit 0 on the happy mock; CLI `--json` `data` is byte-equal to the registry-handler `data` (parity); total outage exits non-zero.

## Task Commits

1. **Task 1: Register research.score in the capability registry** — `ed8dd3b` (feat)
2. **Task 2: `research score` CLI subcommand + table renderer + payload flattening** — `26bb020` (feat)
3. **Task 3: MCP parity + inventory-test updates + full-suite green** — `b698f8b` (test), `97adba0` (test, stub cleanup)

## Files Created/Modified

- `src/construct/capabilities/catalog.py` — `research.score` `CapabilityRecord` + `_research_score_shim` adapter (+ Phase-9 import block).
- `src/construct/cli.py` — `research_score_cmd`, `_flatten_search_results_payload`/`_load_search_results_json` helpers, `_render_research_score_table`; `import builtins` and `builtins.list` to dodge the `list`-command shadow.
- `tests/llm/test_research_score_capability.py` (new) — registration + shim happy/total-outage tests.
- `tests/contract/test_research_score_cli_mcp.py` (new) — MCP-tool-list, CLI table render, CLI↔registry `--json` parity, outage-exits-nonzero.
- `tests/contract/test_mcp_contracts.py`, `tests/unit/test_capability_registry.py` — inventory sets updated for the new capability.
- `tests/llm/test_research_score.py` — removed the now-redundant Plan 04 parity stub.

## Decisions Made

- **Resumed in place.** A prior session had left ~90% of this plan as uncommitted working-tree changes (all 4 plan files, zero commits, no SUMMARY). Inspection showed the implementation was correct and aligned to the plan, so it was finished/committed in place rather than discarded and re-executed in a worktree (which would have stranded the changes).
- **`list` shadow fix.** `cli.py` defines two Typer commands named `list`, shadowing the builtin at module scope; the new payload flattener's `isinstance(payload, list)` therefore raised `TypeError: isinstance() arg 2 must be a type`. Fixed by referencing `builtins.list` explicitly (minimal, localized; the broader shadow is pre-existing and out of scope).
- **Inventory-test maintenance.** The three failing pre-existing tests enumerate the catalog/MCP surface; adding the new capability is exactly what they exist to catch, so updating their expected sets is correct maintenance, not gaming green.
- **Stub removal.** The skipped `test_registry_handler_cli_mcp_parity` placeholder explicitly deferred to "the contract tests" this plan provides; removed it so coverage is honestly represented (no lingering skips).

## Deviations from Plan

- The plan assumed a from-scratch execution; in practice this was a **resume** of uncommitted partial work. No behavioral deviation — all tasks, acceptance criteria, and the threat model are satisfied as written.
- One pre-existing latent bug (`list` shadow) had to be fixed to make the CLI invocation path work; this was inside Task 2's surface and is documented above.

## Issues Encountered

- The partial work failed 2 CLI tests via the `list`-shadow `TypeError`; fixed. The post-merge full suite then surfaced 3 inventory-test failures from the added capability; updated.

## Verification

- Acceptance greps: `_research_score_shim` (2), `id="research.score"` (1), `name="score"` (1), `results-file|stdin` (6) all present; `construct_research_score` present in `list_mcp_tools()`; `get_registry().get("research.score")` resolves with the right ids.
- `tests/llm/test_research_score_capability.py` + `tests/contract/test_research_score_cli_mcp.py`: **7 passed**.
- Full suite (BLOCKING gate, Task 3): **289 passed, 0 skipped** — 290 collected, above the 253 baseline; no pre-existing test deleted, skipped, or xfail'd to pass.

## User Setup Required

None — offline mocks cover all tests; no external provider configuration required.

## Next Phase Readiness

- `research.score` is now runnable by users and agents on both the CLI (`construct research score`) and the stdio MCP server (`construct_research_score`), closing RSCH-01.
- The capability returns the same `ResearchScoreGateOutput`-backed `OperationResult` on both surfaces, with governance thresholds echoed in `retrieval` before any workspace write (read-only gate).

## Self-Check: PASSED

- `src/construct/capabilities/catalog.py` — `research.score` record + `_research_score_shim` FOUND
- `src/construct/cli.py` — `research_score_cmd` (`name="score"`) FOUND
- `tests/contract/test_research_score_cli_mcp.py` — parity + outage tests FOUND
- Commits `ed8dd3b`, `26bb020`, `b698f8b`, `97adba0` — FOUND
- Full suite: 289 passed, 0 skipped — green above baseline

---
*Phase: 09-llm-provider-factory-research-score*
*Completed: 2026-06-28*
