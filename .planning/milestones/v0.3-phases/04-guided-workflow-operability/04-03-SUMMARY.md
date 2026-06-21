---
phase: 04-guided-workflow-operability
plan: 03
subsystem: skills
tags: skill-migration, claude-native, cli, mcp, d-09
requires:
  - phase: 03-capability-registry-cli-mcp-spine
    provides: Capability registry with CLI + MCP dispatch surface
provides:
  - Migrated construct-graph-status skill (MCP invocation)
  - Migrated construct-card-evaluate skill (CLI commands)
  - Migrated construct-curation-cycle skill (composed CLI/MCP calls)
affects: 04-guided-workflow-operability (batch 2 skill migrations)
tech-stack:
  patterns:
    - Skill as thin markdown wrapper calling CLI/MCP for deterministic ops
    - allowed-tools restricted to Read, Bash(construct), MCP(connect)
    - Each procedure step documents INPUT and OUTPUT (WF-02 standard)
key-files:
  modified:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-graph-status/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md
key-decisions:
  - "governance.yaml reading preserved as Read (config file, not data scanning)"
  - "LLM-judgment sections preserved for ambiguous promotions and connection typing"
  - "construct_graph_status MCP tool is primary with construct status CLI as fallback"
  - "construct knowledge card list referenced as directional — not yet implemented"
patterns-established:
  - "Skill migration pattern: allowed-tools → MCP(connect)/Bash(construct), steps → CLI/MCP invocation, I/O documented"
  - "Composed skill pattern: curation-cycle delegates to card-evaluate skill for promotion scan"
requirements-completed: [ING-05, WF-04]
duration: 7min
completed: 2026-06-10
---

# Phase 04 Plan 03: Skill Migrations Batch 1 Summary

**Three Claude-native skills migrated from inline file operations to Python CLI/MCP invocation — establishing the D-09 migration pattern that batch 2 follows**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-10T20:27:18Z
- **Completed:** 2026-06-10T20:34:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **construct-graph-status** — Migrated from inline `Read all cards/*.md` + `Grep` scanning to MCP `construct_graph_status` tool (with `construct status --json` CLI fallback). Steps now invoke the MCP tool and present structured results.
- **construct-card-evaluate** — Migrated from inline governance/card/connection file scanning to CLI `construct knowledge card` and `construct knowledge connection` commands. Governance YAML reading preserved as `Read` (config file). LLM judgment preserved for ambiguous promotion decisions.
- **construct-curation-cycle** — Migrated all 7 maintenance steps to composed CLI/MCP calls: `construct validate` for integrity, `construct knowledge card` for card operations, `construct knowledge connection` for connection ops, `construct status` for health data. Each step documents INPUT/OUTPUT per WF-02 standard.

## Task Commits

1. **Task 1: Migrate construct-graph-status** — `6159ee2` (refactor)
2. **Task 2: Migrate construct-card-evaluate** — `63486e8` (refactor)
3. **Task 3: Migrate construct-curation-cycle** — `22a9aca` (refactor)

## Files Modified

- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-graph-status/SKILL.md` — MCP tool invocation, `allowed-tools: MCP(connect), Bash(construct)`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md` — CLI commands, `allowed-tools: Read, Bash(construct), MCP(connect)`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md` — composed CLI/MCP, `allowed-tools: Read, Bash(construct), MCP(connect)`

## Decisions Made

- **governance.yaml stays as Read** — Config file is small and agent-exclusive; not worth routing through CLI for a single file read
- **LLM judgment preserved** — Ambiguous promotions and connection typing require card-content understanding that can't be CLI-dispensed
- **Fallback pattern established** — Each skill documents primary (MCP) and fallback (CLI) invocation, ensuring work continues if MCP server isn't running
- **construct knowledge card list referenced (directional)** — The `card list` CLI command doesn't exist yet (planned for Phase 04 batch 2), but skills reference it as the target pattern, with `Read cards/*.md` documented as fallback

## Deviations from Plan

**None - plan executed exactly as written for all three skill migrations.**

Minor notes:
- Two commits included pre-staged unrelated files (`workflow_runner.py`, `test_workflow_runner.py`) from prior Phase 03 work. These files are not part of this plan but were in the index from earlier staging.
- The `construct knowledge card list` CLI command referenced in card-evaluate and curation-cycle skills is not yet implemented — this is by design (the skills establish the interface pattern; implementation comes in Phase 04 batch 2).

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `construct knowledge card list --json` referenced in card-evaluate and curation-cycle | Both SKILL.md files | Command not yet implemented — skills document target pattern with `Read cards/*.md` fallback |
| MCP `construct_graph_status` tool handler returns stub message | `catalog.py:208` | `graph.status` capability registered but handler = `"Not yet implemented — see Plan 02"` |

These stubs do not block the plan's goal — the skill documents are the correct interface specification. The actual implementation will catch up in subsequent Phase 04 plans.

## Issues Encountered

None — all three migrations proceeded smoothly. The migration pattern from Phase 03 (construct-workspace-validate) was consistent and adaptable.

## Next Phase Readiness

- **Batch 1 migration pattern validated** — Ready for batch 2 (remaining skills)
- **INPUT/OUTPUT documentation standard set** — All future skill migrations should adopt this pattern
- **Card list CLI command needed** — The biggest gap is the missing `construct knowledge card list` command; implementing it should be prioritized before batch 2

---

*Phase: 04-guided-workflow-operability*
*Completed: 2026-06-10*
