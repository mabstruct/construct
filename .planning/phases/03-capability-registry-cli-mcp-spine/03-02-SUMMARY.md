---
phase: 03-capability-registry-cli-mcp-spine
plan: 02
type: execute
tags: [cli-delegation, pipe-handlers, graph-status, views-data, RT-01, RT-02]
requires: [03-01]
affects: [mcp-server, skill-migrations]
key-files:
  created:
    - src/construct/pipelines/graph_status.py
    - tests/unit/test_graph_status.py
  modified:
    - src/construct/cli.py
    - src/construct/pipelines/views_generate_data.py
decisions:
  - "CLI is a thin adapter — commands look up cap = registry.get(id) and call cap.handler(**inputs) (D-04 enforcement layer)"
  - "graph.status implemented as a PIPE pipeline returning OperationResult with card/connection/domain counts"
  - "CLI delegation proven via contract tests (test_cli_contracts.py) rather than a dedicated integration suite"
metrics:
  completed: "2026-06-12"
  tests: 5 (graph_status) + CLI delegation covered by 03-03 contract tests
  files_created: 2
  files_modified: 2
  note: "Retroactive summary — backfilled 2026-06-15 from plan, commits, and passing tests."
---

# Phase 03 Plan 02: CLI Registry Refactoring + PIPE Handlers Summary

Refactored the CLI so commands delegate through the capability registry instead
of calling services directly, and implemented the PIPE handlers (`graph.status`,
`views.generate_data`) that fill the remaining capability gaps. This proves the
registry works end-to-end through the existing command surface (RT-01, RT-02).

## Key Features

### CLI registry delegation (`src/construct/cli.py`)
- Commands resolve their capability via `get_registry().get(cap_id)` and invoke `cap.handler(...)`, making the CLI a thin adapter over the registry (the same pattern the ingestion metadata fix later extended).

### graph.status PIPE handler (`src/construct/pipelines/graph_status.py` — 79 lines)
- `graph_status()` loads the workspace and returns an `OperationResult` carrying card / connection / domain counts and graph-health signals.

### views.generate_data handler (`src/construct/pipelines/views_generate_data.py`)
- PIPE handler wired for derived-view data generation (later expanded in Phase 6).

## Deviations from Plan

- **`tests/integration/test_cli_registry.py` (min_lines: 100) was not created.** CLI-to-registry delegation is instead verified by the contract suite `tests/contract/test_cli_contracts.py` delivered in plan 03-03 (4 tests against `test-ws/` fixtures). The "CLI commands work after refactoring" truth is covered; the coverage just lives in a contract test rather than a dedicated integration test. Tracked as a known gap.

## Verification Results

- ✅ 5 unit tests pass (`tests/unit/test_graph_status.py`)
- ✅ CLI commands delegate to registry handlers; existing tests continue to pass
- ✅ `graph.status` returns workspace graph-health data
- ⚠️ CLI delegation coverage via contract tests, not the planned integration suite (see Deviations)

## Commits

| Commit | Description |
|--------|-------------|
| `f0a7ccd` | feat(v03ph01): graph-status pipeline + CLI/registry wiring |

> Note: Phase 3 work landed under broad `v03ph01` commits rather than per-plan commits, which is why this summary was backfilled rather than written at execution time.
