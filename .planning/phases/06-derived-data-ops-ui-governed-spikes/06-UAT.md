---
status: partial
phase: 06-derived-data-ops-ui-governed-spikes
source:
  - 06-01-SUMMARY.md
  - 06-02-SUMMARY.md
  - 06-03-SUMMARY.md
  - 06-04-SUMMARY.md
started: 2026-06-13T00:00:00Z
updated: 2026-06-14T00:00:00Z
---

## Current Test

[testing paused — 1 item outstanding (Test 7 blocked: needs manual UI session)]

## Tests

### 1. Views contract test suite passes
expected: Running tests/contract/test_views_contracts.py passes all ~49 tests (schema export, round-trip, version field, invalid-data rejection).
result: pass
note: Verified by orchestrator — `uv run --extra dev pytest` → 49 passed in 0.04s.

### 2. construct views validate
expected: `construct views validate -w test-ws/my-construct` validates views build data files against their Pydantic contract schemas and reports a clean / structured result.
result: issue
reported: "Command works and reports structured output, but real fixture data fails the contract: bridges.json rejected for extra fields (version/generated/workspace) under ConfigDict(extra='forbid'), and 3 of 8 expected files (domains/articles/stats.json) are missing from the build. This is the validation gap documented in 06-01 (contract models define target shape; generator produces richer data) — known/accepted, not a regression."
severity: minor

### 3. construct spike list
expected: `construct spike list` shows the available spike types (graphify, infranodus) with descriptions.
result: pass
note: Verified by orchestrator — lists graphify + infranodus with descriptions.

### 4. construct spike run (isolation)
expected: `construct spike run <tool>` copies the workspace to a temp dir, runs the external tool, persists a structured result JSON to log/spike-results/, and cleans up the temp copy even on failure. With the tool absent it should fail gracefully (validated tool name, no crash).
result: pass
note: Verified by orchestrator — real graphify ran against an isolated temp copy (/private/var/folders/.../construct-spike-*), stdout/stderr captured, structured result written to log/spike-results/graphify-*.json, temp dir cleaned up. Tool exited 1 (no LLM API key — external), handled gracefully.

### 5. construct tag extract
expected: `construct tag extract -w test-ws/my-construct` reads refs/*.json, extracts candidate phrases, and writes log/tag-candidates.json with all candidates as status "pending" (never auto-accepted).
result: pass
note: Verified by orchestrator — 26 candidates extracted, all status "pending", written to log/tag-candidates.json.

### 6. construct tag list / approve governance
expected: `construct tag list` shows candidates sorted by confidence. `construct tag approve <id>` marks the candidate approved and adds a SearchCluster entry to search-seeds.json; pending candidates are NOT written to search-seeds.json until explicitly approved (D-08).
result: pass
note: Verified by orchestrator — tag list shows 26 sorted by confidence; approving one moved it pending→approved and added 1 SearchCluster (3→4) with correct shape; remaining 25 stayed pending. D-08 holds. Fixture mutations restored.

### 7. Streamlit ops dashboard launches with 3 panels
expected: Launching the Streamlit app opens a local ops console with a sidebar (workspace path, install root, LLM config) and three navigable panels — Dashboard (graph health metrics), Capability Runner (dropdown + dynamic form + run), and Gate Review (Q&A + bridge candidate tabs with approve/reject).
result: blocked
blocked_by: other
reason: "Requires a manual interactive Streamlit UI session; no browser-automation tool available to drive it in this run. Launch with: .venv/bin/streamlit run src/construct/ui/streamlit_app.py"

## Summary

total: 7
passed: 5
issues: 1
pending: 0
skipped: 0
blocked: 1

## Gaps

- truth: "construct views validate reports clean validation against real workspace build data"
  status: failed
  reason: "Real bridges.json fails ConfigDict(extra='forbid') on version/generated/workspace fields; 3 of 8 view files (domains/articles/stats.json) absent from build. Documented in 06-01 as a known contract-vs-generator gap, not a regression."
  severity: minor
  test: 2
  artifacts: []
  missing: []
