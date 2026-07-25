---
phase: 17-architecture-doc-set-daily-run-discoverability
plan: 02
subsystem: claude-skills
tags: [skill, daily-cycle, thin-wrapper, discoverability]
requires:
  - "construct daily run capability (Phase 13, DAY-01/02/03)"
  - "test_skill_migration.py thin-wrapper guard (Phase 12/16)"
provides:
  - "construct-daily-cycle thin skill (Layer 0 chat entry point to daily.run)"
  - "D-09 forbidden-tools guard enrollment for construct-daily-cycle"
affects:
  - "CONSTRUCT-CLAUDE-impl/claude/skills/ (25 skills now)"
tech-stack:
  added: []
  patterns:
    - "Thin skill delegator (Layer 0 over Layer 3) — no inline logic, delegate every side effect to construct ... run"
    - "Static frontmatter enrollment in _MIGRATED_SKILLS"
key-files:
  created:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md
  modified:
    - tests/contract/test_skill_migration.py
decisions:
  - "Banner framed as 'Thin orchestrator (Phase 17, D-08)' rather than the siblings' 'Migrated for Phase 12' — this is a new skill, not a migration; the D-09 guard reads only allowed-tools frontmatter so banner text is free-form (honesty over verbatim mirroring)."
metrics:
  duration: "~12 min"
  completed: 2026-07-25
  tasks: 2
  files: 2
status: complete
---

# Phase 17 Plan 02: Daily Cycle Skill & Discoverability Summary

A new thin `construct-daily-cycle` skill gives the flagship `daily.run` composition a Claude-native chat entry point, and the skill is enrolled in the thin-wrapper forbidden-tools guard so it can never silently regain Write/Edit/WebSearch/WebFetch.

## What Was Built

**Task 1 — `construct-daily-cycle/SKILL.md` (commit `80ee6b2`):**
A Layer 0 thin-orchestrator skill mirroring the research-cycle / curation-cycle siblings' shape, with the two deliberate omissions:
- Frontmatter `allowed-tools: Read, Bash(construct), MCP(connect)` — byte-identical to the siblings; declares none of the forbidden tools.
- Thin-orchestrator banner: invokes `construct daily run`, narrates the composed result, Python owns every side effect.
- Prerequisites (`construct mcp &`), then a 5-step procedure: optional read-only domain-focus negotiation → invoke `construct daily run --workspace . --json` (MCP alternative noted) → narrate the `DailyRunResult` (`status`, `children`, `graph_health`) → surface `pending_escalations` → point to `construct research review` / `construct curation review` for interactive handling on a fresh cycle.
- Carries the "No views refresh step here" adr-0005 callout for parity; ends with a Validation checklist.
- **OMITS** the siblings' interactive gate loop (no "Present the Gate Queue" / "Resume via Review") because `daily.run` is non-blocking and auto-resumes children with each gate's recommended decision, and **OMITS** any views-refresh step (Python layer owns it).

**Task 2 — `_MIGRATED_SKILLS` enrollment (commit `3eddcc3`):**
Added the single string entry `"construct-daily-cycle"` to `_MIGRATED_SKILLS`. No test bodies, parser, or `_FORBIDDEN_TOOLS` touched — the three parametrized guards auto-extended to the new skill.

## Verification

- `pytest tests/contract/test_skill_migration.py` → 15 passed (5 skills × 3 guards, incl. the 3 new construct-daily-cycle cases).
- `pytest tests/contract/test_doc_command_references.py` → 37 passed, 1 skipped; `_KNOWN_BROKEN` still empty (the skill's four command strings — `construct daily run`, `construct research review`, `construct curation review`, `construct mcp` — all resolve against the live Typer app).
- `allowed-tools` line is exactly `Read, Bash(construct), MCP(connect)`.
- Manual/grep review: no "Present the Gate Queue", "Resume via Review", or "refresh views" section present.
- `_FORBIDDEN_TOOLS` unchanged `("WebSearch", "WebFetch", "Write", "Edit")` — guard not weakened.

## Threat Model Outcome

All four registered threats mitigated as planned:
- **T-17-02-01** (privilege escalation via forbidden tool grant): mechanically contained by the D-09 enrollment — the guard now fails the suite if any forbidden tool appears in the daily skill's frontmatter.
- **T-17-02-02** (non-resolving command string): FIX-04 doc-command guard passes; all four strings in VALID_PATHS; `_KNOWN_BROKEN` empty.
- **T-17-02-03** (inline logic drift): the skill is a pure delegator; banner + Validation checklist assert no inline logic.
- **T-17-02-SC** (supply chain): no package installs.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written.

### Design note (not a deviation)

The migration banner is worded "**Thin orchestrator (Phase 17, D-08)**" rather than copying the siblings' "Migrated for Phase 12 (API-04, D-08)" wording, because this is a newly authored skill, not a migration of pre-existing inline logic. The plan required "a migration banner stating this is a thin orchestrator that invokes `construct daily run`" and left the exact wording open; the D-09 guard reads only the `allowed-tools:` frontmatter, so banner prose is unconstrained. Honesty was preferred over verbatim mirroring.

## Requirements Satisfied

- **UX-01** — a user can trigger `daily.run` from Claude-native chat via the new `construct-daily-cycle` skill (ROADMAP criterion 4; criterion 5 already satisfied per PROJECT.md D-10).

## Known Stubs

None.
