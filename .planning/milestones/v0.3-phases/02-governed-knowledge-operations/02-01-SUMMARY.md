---
phase: 02-governed-knowledge-operations
plan: 01
type: execute
tags: [service-layer, card-crud, connection-crud, event-logging, validation]
requires: [01-contract-canon-artifact-governance]
affects: [cli-knowledge-commands, skill-wrappers]
key-files:
  created:
    - src/construct/services/event_log.py
    - src/construct/services/knowledge.py
    - tests/unit/test_knowledge_operations.py
  modified:
    - src/construct/schemas/workspace.py
decisions:
  - "Event log append is non-blocking — OSError writes warning to stderr, does not raise"
  - "Card create generates kebab-case ID from title when id not provided, deduplicates with -2/-3 suffix"
  - "Card edit applies field-level updates — unmentioned fields preserved via raw frontmatter dict round-trip"
  - "Connection add uses Pydantic alias `from` for ConnectionRecord construction (Field(alias='from'))"
metrics:
  duration: "~20 min"
  completed: "2026-06-09"
  tests: 21 (all passing)
  files_created: 3
  files_modified: 1
---

# Phase 02 Plan 01: Governed Knowledge Operations — Foundation Layer Summary

Created the core Python service layer for governed knowledge operations — card CRUD, connection CRUD, event logging, and workspace scaffold updates. This is the foundational layer that all Phase 2 CLI commands and skill wrappers build upon.

## Key Features

### Event Log Service (`src/construct/services/event_log.py` — 81 lines)
- `append_event()` — appends JSON lines to `log/events.jsonl` with current UTC timestamp
- `append_card_event()` — convenience wrapper setting `target=card_id`
- `append_connection_event()` — convenience wrapper with `detail="{from}->{to} ({type})"`
- **Non-blocking** — OSError writes warning to stderr, does not raise (per research pitfall mitigation)
- Parent directory auto-created via `mkdir(parents=True, exist_ok=True)`

### Card CRUD (`src/construct/services/knowledge.py` — 573 lines)
- **`create_card()`** — validates via `KnowledgeCard` schema, generates kebab-case ID from title, deduplicates with -2/-3 suffix, writes `cards/{id}.md`, logs `create_card` event
- **`edit_card()`** — reads existing card, applies field-level updates (preserves unmentioned fields), validates, writes, logs `edit_card` event
- **`archive_card()`** — sets `lifecycle` to `archived`, preserves `connects_to` per D-06, validates, writes, logs `archive_card` event
- All operations return `OperationResult` with structured `OperationError` (field, reason, suggestion)

### Connection CRUD (`src/construct/services/knowledge.py`)
- **`add_connection()`** — validates kebab-case IDs, checks card file existence (orphan prevention), detects duplicates, creates `ConnectionRecord` with alias `from`, validates via `ConnectionsFile` schema, logs `add_connection` event
- **`remove_connection()`** — matches by from+to+type, removes single entry, validates and writes, logs `remove_connection` event
- **`list_connections()`** — optional `card_id` filter, `include_archived` flag to include/exclude archived card connections

### Workspace Scaffold Update (`src/construct/schemas/workspace.py`)
- Added `inbox` to `REQUIRED_PATHS` tuple
- Added `inbox` and `inbox/**` to `WorkspaceScaffold.support_paths`

## Deviations from Plan

**None — plan executed exactly as written.**

## Known Stubs

None — all functions are fully implemented with no stubs.

## Threat Surface Scan

No new security-relevant surface introduced. All operations are filesystem-local with Pydantic validation enforced before writes. Event log is append-only local file with no PII per schema.

## Verification Results

- ✅ All 21 unit tests pass (pytest exit 0)
- ✅ `event_log.py` imports correctly
- ✅ `REQUIRED_PATHS` includes `"inbox"`
- ✅ `WorkspaceScaffold.support_paths` includes `"inbox"` and `"inbox/**"`
- ✅ Min lines met: event_log.py (81 ≥ 50), knowledge.py (573 ≥ 250), test file (383 ≥ 200)

## Self-Check: PASSED

All files exist, all commits recorded, all verifications pass.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `e888d0a` | feat(02-governed-knowledge-operations): create event_log service and add inbox to WorkspaceScaffold |
| 2 | `467c1b9` | feat(02-governed-knowledge-operations): create card CRUD service functions with tests |
| 3 | `7202c22` | feat(02-governed-knowledge-operations): add connection CRUD service with tests |
