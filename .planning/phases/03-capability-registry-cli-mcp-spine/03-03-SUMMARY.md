---
phase: 03-capability-registry-cli-mcp-spine
plan: 03
type: execute
tags: [mcp-server, stdio, contract-tests, skill-migration, RT-02, RT-03]
requires: [03-01, 03-02]
affects: [phase-04-skill-migrations]
key-files:
  created:
    - src/construct/mcp/__init__.py
    - src/construct/mcp/server.py
    - tests/contract/test_mcp_contracts.py
    - tests/contract/test_cli_contracts.py
  modified:
    - src/construct/cli.py
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md
decisions:
  - "MCP server uses stdio transport (D-09)"
  - "MCP tools auto-register from the capability registry — schema parity with the CLI by construction"
  - "construct-workspace-validate is the first skill migrated to MCP invocation (D-07)"
metrics:
  completed: "2026-06-12"
  tests: 7 (4 CLI contract + 3 MCP contract, all passing)
  files_created: 4
  files_modified: 2
  note: "Retroactive summary — backfilled 2026-06-15 from plan, commits, and passing tests."
---

# Phase 03 Plan 03: MCP Server + Contract Tests + Skill Migration Summary

Created the MCP stdio server, wired it to the capability registry so tools are
auto-registered with schema parity to the CLI, proved that parity with contract
tests, and migrated the first Claude-native skill to MCP invocation. This is the
agentic invocation path that replaces fragile inline file behavior (RT-02, RT-03).

## Key Features

### MCP server (`src/construct/mcp/server.py` — 52 lines)
- stdio-transport MCP server (D-09)
- Tools auto-registered from `catalog.get_registry()` — every registered capability becomes an MCP tool with JSON Schema derived from its Pydantic input model, guaranteeing parity with the CLI surface

### `construct mcp` command (`src/construct/cli.py`)
- `mcp()` Typer subcommand (cli.py:119) spawns the stdio server

### Contract tests
- `tests/contract/test_cli_contracts.py` (4 tests) — CLI commands run against `test-ws/` fixtures
- `tests/contract/test_mcp_contracts.py` (3 tests) — MCP tool schemas match CLI command signatures

### First skill migration
- `construct-workspace-validate/SKILL.md` migrated to call the `construct_validate` MCP tool instead of inline file checking (D-07) — establishes the pattern Phase 4 used for batch skill migration

## Deviations from Plan

- `server.py` is **52 lines vs the plan's `min_lines: 80`**. The implementation is functionally complete — auto-registration keeps the server small precisely because schemas come from the registry, not hand-written per tool. No scope dropped.

## Verification Results

- ✅ 7 contract tests pass (4 CLI + 3 MCP)
- ✅ MCP server starts via `construct mcp` (stdio)
- ✅ MCP tools auto-registered from the registry; `construct_validate` schema matches the CLI
- ✅ `construct-workspace-validate` skill invokes the MCP tool

## Commits

| Commit | Description |
|--------|-------------|
| `f0a7ccd` | feat(v03ph01): MCP server + workspace-validate skill rewrite + contract tests |
| `aac52a7` | fix(v03): wire MCP, single version source, bump to 0.3.0 |

> Note: Phase 3 work landed under broad `v03ph01` commits rather than per-plan commits, which is why this summary was backfilled rather than written at execution time.
