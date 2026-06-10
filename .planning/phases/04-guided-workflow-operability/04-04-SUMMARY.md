---
phase: 04-guided-workflow-operability
plan: 04
subsystem: skills
tags: skill-migration, claude-native, cli, ingest, gap-analysis, workflow-docs, wf-02
requires:
  - phase: 04-guided-workflow-operability
    plan: 03
    provides: Skill migration pattern (allowed-tools, CLI/MCP invocation, I/O documentation)
provides:
  - Migrated construct-research-cycle skill (CLI ingest pipeline)
  - Migrated construct-gap-analysis skill (CLI graph data acquisition)
  - Updated daily-cycle workflow doc (Inputs, Outcome, Error Handling, workflow runner)
  - Updated cold-start workflow doc (Inputs, Outcome)
  - Updated co-authorship workflow doc (Inputs, Outcome)
affects: 05-runtime-pipeline (view-layer and pipeline hardening)
tech-stack:
  patterns:
    - Ref/seed card creation via construct ingest source CLI
    - Graph data acquisition via construct knowledge card/connection CLI
    - Workflow doc standard (WF-02): Inputs + Outcome + Error Handling per workflow
key-files:
  modified:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-gap-analysis/SKILL.md
    - CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md
    - CONSTRUCT-CLAUDE-impl/construct/workflows/cold-start.md
    - CONSTRUCT-CLAUDE-impl/construct/workflows/co-authorship.md
key-decisions:
  - "construct ingest source is the CLI entry point for ref/seed card creation (replaces inline file writes)"
  - "construct knowledge card list is referenced but not yet implemented — skills document the target pattern"
  - "Workflow docs get additive Inputs/Outcome/Error Handling sections; existing procedure content preserved exactly"
requirements-completed: [WF-02, ING-01, ING-05]
duration: 5min
completed: 2026-06-10
---

# Phase 04 Plan 04: Skill Migrations Batch 2 + Workflow Docs Summary

**Two remaining skills migrated to CLI (research-cycle → construct ingest, gap-analysis → construct knowledge) and three workflow docs updated with structured Inputs/Outcome sections per WF-02 standard**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-10T20:34:11Z
- **Completed:** 2026-06-10T20:39:30Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- **construct-research-cycle** — Migrated Step 5 (Ingest Findings) from inline file writes to `construct ingest source` CLI. Web search (Step 3) and extraction/scoring (Step 4) preserved as LLM-driven work. Digest compilation (Step 6) preserved as LLM synthesis. Each step now documents INPUT and OUTPUT.
- **construct-gap-analysis** — Migrated Step 1 (Load Graph State) from `Read all cards/*.md` + inline scanning to CLI commands (`construct knowledge card list`, `construct knowledge connection list`, `construct status`). Coverage analysis, quality assessment, and recommendations preserved as LLM reasoning. Read reserved for small config files (domains.yaml, governance.yaml). Gap report format preserved.
- **Workflow documentation (WF-02)** — All three workflow documents updated:
  - **daily-cycle.md**: Added Inputs (workspace, config, optional domain focus), Outcome (research/curation/user-action results), Error Handling (4 edge cases), and workflow runner reference (`construct workflow run daily-cycle`)
  - **cold-start.md**: Added Inputs (user topic/domain, optional source material), Outcome (workspace scaffolded, domain configured, search seeded)
  - **co-authorship.md**: Added Inputs (workspace, user request, graph connectivity), Outcome (draft published, confidence propagation, card citations)

## Task Commits

1. **Task 1: Migrate construct-research-cycle to use CLI ingestion pipeline** — `836f4a3` (feat)
2. **Task 2: Migrate construct-gap-analysis to use CLI commands for graph data** — `04c9992` (feat)
3. **Task 3: Update workflow documentation with clear inputs/outputs/outcomes** — `c4c5f4e` (docs)

## Files Modified

- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md` — CLI `construct ingest source` for ref/seed cards; `allowed-tools: Read, Bash(construct), WebSearch, WebFetch, MCP(connect)`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-gap-analysis/SKILL.md` — CLI `construct knowledge card list`/`construct knowledge connection list`/`construct status` for graph data; `allowed-tools: Bash(construct), MCP(connect), Read`
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` — Added Inputs, Outcome, Error Handling, workflow runner reference
- `CONSTRUCT-CLAUDE-impl/construct/workflows/cold-start.md` — Added Inputs and Outcome sections
- `CONSTRUCT-CLAUDE-impl/construct/workflows/co-authorship.md` — Added Inputs and Outcome sections

## Decisions Made

- **construct ingest source as ref/seed card entry point** — The research-cycle skill now delegates all ref and seed card creation to the `construct ingest source` CLI. This provides consistent ref/card format, deterministic validation, and traceable event log entries.
- **Config files stay as Read** — domains.yaml and governance.yaml remain as `Read` operations (small, agent-exclusive config files; not worth routing through CLI for a single file read).
- **Workflow doc sections are additive** — All existing workflow procedure content (steps, examples, cadence, failure recovery) preserved exactly. Inputs/Outcome/Error Handling are new sections, not modifications.

## Deviations from Plan

**None - plan executed exactly as written for all 5 files.**

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `construct knowledge card list --json` referenced in gap-analysis skill (Step 1) | `construct-gap-analysis/SKILL.md` | Command not yet implemented — skill documents target pattern from Phase 04 batch 1; `Read cards/*.md` fallback available to agent |

This stub does not block the plan's goal — the skill document is the correct interface specification. The agent can still gather card data via the existing `Read` fallback if the CLI command is unavailable.

## Issues Encountered

None — all 5 files updated smoothly. Migration pattern from Plan 04-03 was consistent and applied cleanly to both remaining skills.

## Next Phase Readiness

- **D-09 skill migration complete** — All 5 skills in the migration plan now use CLI/MCP invocation (3 from batch 1, 2 from batch 2)
- **WF-02 workflow documentation standard met** — All 3 workflow documents have structured Inputs/Outcome sections
- **Remaining gap: `construct knowledge card list` CLI command** — Still unimplemented; needed to fully close the gap-analysis skill's Step 1 data acquisition path. Without it, the agent falls back to `Read cards/*.md` for card enumeration.
- **Next work: Phase 05** — Pipeline hardening, views contract finalization, and derived data cache

---

*Phase: 04-guided-workflow-operability*
*Completed: 2026-06-10*
