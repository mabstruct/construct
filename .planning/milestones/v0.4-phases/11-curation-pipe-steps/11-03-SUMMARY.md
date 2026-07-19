---
phase: 11-curation-pipe-steps
plan: 03
subsystem: curation-invoke-surface
tags: [registry, catalog, cli, mcp, rt-03, dual-mode-shim, schema-parity, curation]

# Dependency graph
requires:
  - phase: 11-curation-pipe-steps
    plan: 02
    provides: construct.llm.curation_run module (CurationRunInput/CurationInspectInput/run_curation_run/inspect_curation_run/CurationRunResult)
  - phase: 11-curation-pipe-steps
    plan: 01
    provides: tests/contract/test_curation_run_cli_mcp.py red suite this plan turns GREEN
provides:
  - curation.run + curation.inspect capabilities in the shared registry (cli_name + mcp_tool_name; MCP auto-discovered)
  - RT-03 dual-mode keyword-only shims (_curation_run_shim/_curation_inspect_shim) + _curation_result_to_operation wrap
  - curation Typer sub-app (run/inspect) + _render_curation_result per-step renderer in cli.py
affects: [phase-12 curation gates (CUR-05 legacy placeholder removal), daily-cycle composition]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MCP/CLI parity is free: a CapabilityRecord carrying cli_name + mcp_tool_name is auto-discovered by the stdio MCP server — no mcp/server.py edit (test_mcp_no_hardcoded_curation guards it)"
    - "Deterministic-runner shim: _curation_result_to_operation drops the research ResearchScoreOutageError branch — generic except → success=False with a class-name-only message (no provider/raw-text leak)"
    - "Sibling renderer for a divergent result shape: _render_curation_result iterates steps (step/status/summary) instead of reusing _render_run_result's gate_queue shape, while --json keeps full CurationRunResult fidelity"

key-files:
  created: []
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py

key-decisions:
  - "curation handler wraps CurationRunResult into OperationResult with success = status != 'failed' and data = result.model_dump(mode='json') — so _serialize_result (MCP) and _display_result (CLI --json) emit the identical envelope and data keys (schema parity)"
  - "Registry-inventory tests (test_mcp_tool_count, test_catalog_loads, _payload_for) were grown to include the two new capabilities — keeping the exact-inventory assertions accurate is maintenance, not weakening (research.run is listed there for the same reason)"
  - "Legacy workflow.run curation-cycle placeholder lambdas (catalog.py ~653–669) left byte-identical (D-11); flagged for Phase 12 / CUR-05 removal"

patterns-established:
  - "Pattern: a deterministic capability needs only a registration block + two keyword-only shims + a result→OperationResult wrap to gain BOTH CLI and stdio-MCP surfaces; no transport code is written"

requirements-completed: [CUR-01]

# Metrics
duration: 20min
completed: 2026-06-28
---

# Phase 11 Plan 03: Curation Invoke Surface (CLI + MCP) Summary

**Wires `curation.run` and `curation.inspect` into the shared capability registry with RT-03 dual-mode keyword-only shims and adds the `curation` Typer sub-app (run/inspect) with a per-step renderer — turning the Plan 01 contract suite fully GREEN and delivering CUR-01's CLI + auto-discovered stdio-MCP invocation surface, with MCP parity free (no `mcp/server.py` edit) and the legacy placeholder path left intact (D-11).**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 completed
- **Files modified:** 4 (2 production + 2 inventory tests)

## Accomplishments

- **Task 1 — catalog registration + shims:** Added the Phase 11 import block (`CurationInspectInput`/`CurationRunInput`/`inspect_curation_run`/`run_curation_run`), `_curation_result_to_operation` (the simpler, outage-free sibling of `_run_result_to_operation`), the keyword-only `_curation_run_shim`/`_curation_inspect_shim` (positional → `TypeError`), and registered `curation.run` + `curation.inspect` with `cli_name` == id and `mcp_tool_name` == `construct_curation_run`/`construct_curation_inspect`. MCP picked them up by auto-discovery — `mcp/server.py` untouched.
- **Task 2 — CLI sub-app + renderer:** Added `curation_app` (`app.add_typer`), `curation_run_cmd` (`-w`/`--json`, **no** `--provider`), `curation_inspect_cmd` (`-w`/`--run-id`/`--json`), plus `_render_curation_result` (prints run status/run_id and a per-step line so the user visually distinguishes completed/degraded/skipped — criterion #2) and `_emit_curation_result` (full `--json` fidelity via `_display_result`, per-step table on success, generic render on failure).
- **Task 3 — regression sweep + inventory sync:** Ran the full suite; grew the three exact-inventory tests (`test_mcp_tool_count`, `_payload_for` handler-invocation map, `test_catalog_loads`) to include the two new capabilities. Confirmed the legacy `workflow.run curation-cycle` placeholder lambdas are byte-identical (D-11) and flagged their fake-success path for Phase 12 / CUR-05.

## Task Commits

Each task was committed atomically:

1. **Task 1: Register curation.run + curation.inspect with dual-mode shims** - `4e37741` (feat)
2. **Task 2: Add curation Typer sub-app (run/inspect) + per-step renderer** - `2d06d9f` (feat)
3. **Task 3: Extend MCP/registry inventory for curation capabilities** - `9fb56ac` (test)

**Plan metadata:** this commit (docs)

## Files Created/Modified

- `src/construct/capabilities/catalog.py` — curation import block, `_curation_result_to_operation`, `_curation_run_shim`/`_curation_inspect_shim`, and the two `CapabilityRecord` registrations. Legacy curation-cycle placeholders untouched.
- `src/construct/cli.py` — `curation_app` sub-app, `curation_run_cmd`/`curation_inspect_cmd`, `_render_curation_result`, `_emit_curation_result`.
- `tests/contract/test_mcp_contracts.py` — added `construct_curation_run`/`construct_curation_inspect` to the tool-count set and the handler-invocation payload map.
- `tests/unit/test_capability_registry.py` — added `curation.run`/`curation.inspect` to the catalog-loads expected id set.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Grew the exact-inventory registry/MCP tests for the two new capabilities**
- **Found during:** Task 3 (full regression sweep)
- **Issue:** `test_mcp_tool_count`, `test_catalog_loads`, and `test_every_mcp_handler_invokes_without_type_error` assert against a frozen exact capability inventory. Registering two new capabilities makes `actual == expected` fail by the two extra members — exactly as adding `research.run` once required.
- **Fix:** Added `construct_curation_run`/`construct_curation_inspect` to the tool-count `expected` set and to the `_payload_for` invocation map (`{workspace_path}` / `{workspace_path, run_id}`), and `curation.run`/`curation.inspect` to the catalog-loads `expected_ids`. No existing assertion was weakened — the inventory tests are designed to track the registry exactly, and the curation shims correctly accept their advertised schema fields without `TypeError`.
- **Files modified:** tests/contract/test_mcp_contracts.py, tests/unit/test_capability_registry.py
- **Commit:** `9fb56ac`

No other deviations. The plan note left the CLI renderer choice open (reuse `_emit_run_result` vs. add a sibling); per the Task 2 action text the sibling `_render_curation_result` was added so the steps/events shape renders meaningfully (criterion #2), while `--json` retains full fidelity for the parity gate.

## Surviving Debt — Phase 12 / CUR-05 (D-11)

The legacy `workflow.run curation-cycle` placeholder lambdas at `catalog.py` (~653–669) still return fake-success (`"Integrity check placeholder…"`, `"Decay scan placeholder"`, …). They coexist with the new real `curation.run` capability under a separate capability id and were deliberately left byte-identical this phase (D-11; threat-register T-11-07 disposition: accept). **Phase 12 / CUR-05 must remove or redirect this placeholder path** so the only curation invocation surface is the real deterministic pipeline.

## Verification

- `pytest tests/contract/test_curation_run_cli_mcp.py -q` → **7 passed** (registration, positional-arg rejection, MCP auto-discovery, no-hardcoded guard, CLI presence, CLI/MCP schema parity).
- `pytest -q` → **359 passed** (full API-05 regression intact: CLI, MCP, validation, ingestion, graph, ask-domain, research.run, plus new curation suites).
- `pytest tests/llm/test_curation_run.py -q` → still GREEN (Plan 02 module unchanged).
- `grep "construct_curation" src/construct/mcp/server.py` → no match (parity auto-discovered; no server.py edit).
- `git diff` over the plan range → legacy curation-cycle placeholder lambdas byte-identical (D-11).
- CLI/MCP envelope: `_serialize_result(OperationResult)` and CLI `--json` both emit `{success, message, errors, data}`; `data` keys == `CurationRunResult.model_fields` (parity asserted GREEN).

## Threat Surface

No new trust boundaries beyond the plan's `<threat_model>`. T-11-01 (run_id tampering) is mitigated at the `CurationRunInput`/`CurationInspectInput` `field_validator` constructed inside the shim before run_id reaches the SQLite thread_id; T-11-05 (positional injection) is mitigated by the keyword-only shims (`reg.get(cap_id).handler("positional")` raises `TypeError`, asserted GREEN); T-11-07 (legacy placeholder coexistence) accepted and flagged for CUR-05; no package installs (T-11-SC).

## Known Stubs

None introduced by this plan. The surviving legacy placeholder lambdas are pre-existing D-11 debt (separate capability id), documented above for Phase 12 / CUR-05 — not a stub created here.

## Self-Check: PASSED
- FOUND: .planning/phases/11-curation-pipe-steps/11-03-SUMMARY.md
- FOUND modified: src/construct/capabilities/catalog.py (curation.run registration)
- FOUND modified: src/construct/cli.py (curation_app)
- FOUND commit: 4e37741 (Task 1)
- FOUND commit: 2d06d9f (Task 2)
- FOUND commit: 9fb56ac (Task 3)
