---
phase: 02-governed-knowledge-operations
plan: 02
type: execute
tags: [cli, knowledge-commands, card-crud, connection-crud, integration-tests]
requires: [02-01-service-layer]
provides: [cli-knowledge-commands]
affects: [skill-wrappers, construct-cli]
tech-stack:
  added:
    - "typer sub-groups for nested command hierarchy (knowledge → card | connection)"
  patterns:
    - "Typer group nesting: knowledge_app → card_app, connection_app"
    - "Service layer → CLI with _display_result() adapter"
    - "Structured errors with field/reason/suggestion on failure"
key-files:
  modified:
    - src/construct/cli.py (+142 lines): added knowledge command group with card + connection subcommands
  created:
    - tests/integration/test_knowledge_cli.py (216 lines, 8 tests): card create/edit/archive, connection add/list, event logging
decisions:
  - "Connection type validation at CLI layer (try/except ValueError on ConnectionType) before service call — per T-02-05"
  - "_display_result handles both JSON and human-readable output; exit code 1 on failure per T-02-07"
  - "Typer/Click handles range validation (confidence 1-5, source-tier 1-5) with exit code 2 — test adjusted to assert non-zero"
metrics:
  duration: "~15 min"
  completed: "2026-06-09"
  tests: 8 integration + 21 unit (all passing)
  files_created: 1
  files_modified: 1
---

# Phase 02 Plan 02: Knowledge CLI Surface Summary

Built the Typer CLI surface for card and connection operations under the `construct knowledge` command group. This is the machine interface that skills call (capturing JSON output) and users use for ad-hoc operations.

## Key Features

### CLI Hierarchy
- `construct knowledge` — top-level group with `--help` guidance
  - `construct knowledge card create` — creates cards with all epistemic governance fields
  - `construct knowledge card edit <id>` — field-level updates preserving unmentioned fields
  - `construct knowledge card archive <id>` — sets lifecycle to archived
  - `construct knowledge connection add <from> <to> --type <type>` — typed edge creation
  - `construct knowledge connection remove <from> <to> --type <type>` — exact match deletion
  - `construct knowledge connection list` — with `--card` filter and `--include-archived`

### Structured Output
- `--json` / `-j` flag on all commands returns machine-parseable JSON: `{"success", "message", "errors", "data"}`
- Default human-readable output with checkmark/cross, colored errors, and fix suggestions
- All failure paths exit with non-zero code

### Security Contract (Threat Model Compliance)
- **T-02-05 (tampering):** Typer handles int bounds (confidence 1-5, source-tier 1-5); ConnectionType validated at CLI layer via `try/except ValueError`
- **T-02-06 (info disclosure):** JSON output is local-only with card metadata already on filesystem — accepted
- **T-02-07 (elevation):** All code paths reach `_display_result`; `typer.Exit(code=1)` on failure terminates further command processing

## Test Coverage (8 integration tests)
| Test | Coverage |
|------|----------|
| `test_card_create_cli` | Happy path card creation via CLI |
| `test_card_create_cli_invalid` | Out-of-range confidence returns non-zero (Typer validation) |
| `test_card_create_cli_json` | `--json` flag returns parseable JSON with success + id |
| `test_card_edit_cli` | Edit title + confidence, verify file content changes |
| `test_card_archive_cli` | Archive card, verify lifecycle: archived in output |
| `test_connection_add_cli` | Add typed connection between two cards |
| `test_connection_list_cli` | List connections after creation |
| `test_cli_logs_event` | Card creation records event in `log/events.jsonl` |

## Deviations from Plan

### [Rule 1 - Plan accuracy] Invalid input test adjusted for Typer exit code
- **Found during:** Task 2 test execution
- **Issue:** Plan specified `assert result.exit_code == 1` for invalid `--confidence 99`, but Typer/Click's built-in range validation (`min=1, max=5`) returns exit code **2** (usage error) before reaching the service layer
- **Fix:** Changed assertion to `assert result.exit_code != 0` — still satisfies "CLI returns non-zero exit code on failure" per must-haves
- **Files modified:** `tests/integration/test_knowledge_cli.py`
- **Commit:** `c6747f2`

## Known Stubs

None — all CLI commands are fully wired to the service layer with no placeholder implementations.

## Threat Surface Scan

No new security-relevant surface introduced beyond the documented threat model. All CLI operations are filesystem-local with Typer-enforced type coercion and structured error handling. No network endpoints, no auth paths, no schema changes at trust boundaries.

## Verification Results

- ✅ All 8 integration tests pass (`tests/integration/test_knowledge_cli.py`)
- ✅ All 21 unit tests pass (`tests/unit/test_knowledge_operations.py`)
- ✅ `construct knowledge --help` shows card and connection subgroups
- ✅ `construct knowledge card create --help` lists all options
- ✅ `construct knowledge card edit --help` shows argument and options
- ✅ `construct knowledge card archive --help` works
- ✅ `construct knowledge connection add/remove/list --help` all work
- ✅ `init/validate/status` commands unchanged
- ✅ Pre-existing test failure in `test_init_cli.py` (workspace tree fixture) confirmed unrelated

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `src/construct/cli.py` exists | ✅ 296 lines, all commands registered |
| `tests/integration/test_knowledge_cli.py` exists | ✅ 216 lines, 8 tests |
| Task 1 commit `4506160` exists | ✅ |
| Task 2 commit `c6747f2` exists | ✅ |
| Integration tests pass | ✅ 8/8 |
| Unit tests pass | ✅ 21/21 |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `4506160` | feat(02-governed-knowledge-operations): add knowledge command group with card CRUD subcommands |
| 2 | `c6747f2` | feat(02-governed-knowledge-operations): add connection CLI subcommands and integration tests |
