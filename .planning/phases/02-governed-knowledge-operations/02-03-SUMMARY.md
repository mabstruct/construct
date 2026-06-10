---
phase: 02-governed-knowledge-operations
plan: 03
subsystem: skill-wrappers
tags: [source-routing, inbox, skill-wrapper, python-cli]
requires:
  - phase: 02-governed-knowledge-operations
    provides: core service layer (02-01), CLI surface (02-02)
provides:
  - Source routing from inbox/ to {domain}/inbox/raw/
  - Updated skill procedures calling construct knowledge CLI
affects: card-create, card-edit, card-archive, card-connect skills

tech-stack:
  added: []
  patterns:
    - skills call Python CLI for file operations
    - inbox/ staging → agentic routing → domain inbox

key-files:
  created: []
  modified:
    - src/construct/services/knowledge.py
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-edit/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-archive/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md

key-decisions:
  - "Source routing auto-detects domain from filename, supports domain_hint override"
  - "Skills keep conversation-driven flow, delegate file operations to CLI"
  - "Connections preserved on archive (CLI handles it)"

patterns-established:
  - Python CLI as enforcement layer; skills orchestrate conversation
  - SKILL.md frontmatter includes Bash(construct knowledge *) for CLI invocation

requirements-completed: [ING-02, ING-03, ING-04]

duration: 20min
completed: 2026-06-10
---

# Phase 02: Governed Knowledge Operations — Plan 03 Summary

**Source routing (inbox → domain) and skill wrappers calling Python CLI**

## Performance

- **Duration:** ~20 min (resumed from partial execution)
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `route_source_to_domain()` routes files from `inbox/` to `{domain}/inbox/raw/` with auto-detection and hint-based targeting
- `_suggest_domain()` matches filename against domain name, description, or content_categories
- Missing domain returns structured error with creation suggestion
- Ref JSON created automatically with ReferenceRecord schema
- All 4 card skills (create/edit/archive/connect) updated to call `construct knowledge` CLI
- Skills retain conversation-driven flow; delegate file operations to Python
- 26 unit tests passing (including 5 new source routing tests)

## Task Commits

1. **Task 1: Source routing** - `a6e3d96` (feat: add source routing and update skills to call Python CLI)
2. **Task 2: Skill wrappers** - (included in same commit)

## Files Created/Modified
- `src/construct/services/knowledge.py` — Added `route_source_to_domain()`, `_suggest_domain()`, imports
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md` — Wraps `construct knowledge card create`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-edit/SKILL.md` — Wraps `construct knowledge card edit`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-archive/SKILL.md` — Wraps `construct knowledge card archive`
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md` — Wraps `construct knowledge connection *`
- `tests/unit/test_knowledge_operations.py` — Added 5 source routing tests

## Decisions Made
- Source routing auto-detection matches filename substrings against domain metadata
- Domain hint (`--domain-hint`) bypasses auto-detection for explicit targeting
- Skills keep conversation flow; Python handles validation and persistence
- Event logging handled by CLI, not manual skill steps

## Deviations from Plan
- Test filenames adjusted to match auto-detection logic ("test-article" → "physics-paper")
- All 4 skill changes committed together (not split per-task)

## Issues Encountered
- Event log test used filename that didn't match any domain — fixed by using domain-matching filename

---

*Phase: 02-governed-knowledge-operations*
*Completed: 2026-06-10*
