---
phase: 12-curation-l3-gates-review-application
plan: 06
subsystem: claude-skills
tags: [skill-migration, api-04, thin-orchestrator, delegation]
requires:
  - "construct research run / research review (Phase 10)"
  - "construct curation run / curation review (Phase 11/12)"
  - "construct card evaluate (Phase 12, Plans 02-05)"
provides:
  - "thin research-cycle orchestrator delegating to research run/review"
  - "thin curation-cycle orchestrator driving the consolidated review loop"
  - "thin card-evaluate wrapper over the Python L3 promotion gate"
affects:
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md
tech-stack:
  added: []
  patterns: ["thin CLI-delegator skill (construct-card-create analog)"]
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md
decisions: [D-08, D-09]
requirements: [API-04]
metrics:
  duration: ~15m
  completed: 2026-07-02
  tasks_completed: 2
  tasks_deferred_to_human: 1
  files_modified: 3
---

# Phase 12 Plan 06: Skill Migration to Thin Orchestrators Summary

Migrated the three Claude-native skills (research-cycle, curation-cycle, card-evaluate)
from inline LLM search/judgment/write logic into **thin CLI orchestrators** that delegate
to the shipped Python `construct research run|review` / `curation run|review` / `card evaluate`
capabilities (API-04). No skill can now web-fetch or write the SOT directly; all side effects
flow through the Python reviewed-write path, and no duplicate judgment logic survives in skill text.

## What Was Built

### Task 1 — research-cycle + curation-cycle → thin orchestrators (commit 6a48a53)

- **construct-research-cycle:** dropped `WebSearch, WebFetch` from `allowed-tools`; replaced
  the inline search/score/dedup/ingest steps (old steps 3–5) with: load config (read-only) →
  negotiate scope → `construct research run` → present the pending `gate_queue` → collect
  approve/reject → `construct research review` to resume → narrate the digest. Legitimate
  Read of `search-seeds.json` / `domains.yaml` / `governance.yaml` for scope negotiation is
  preserved (informational only; the capability enforces thresholds).
- **construct-curation-cycle:** frontmatter already delegated (`Read, Bash(construct), MCP(connect)`);
  rewired the body from 7 inline maintenance steps to: `construct curation run` → present the
  **consolidated** `gate_queue` grouped by kind (promotion / connection / archive / escalate),
  surfacing the `method` field so failure-driven escalations (`rule-based`) read distinctly from
  borderline ones (`llm-judgment`) → collect approve/reject (subset / approve-all / reject-all) →
  `construct curation review` to resume → narrate the health report. No inline curation logic survives.

### Task 2 — card-evaluate → thin wrapper (commit ed6482b)

- **construct-card-evaluate:** removed the inline promotion-threshold ruleset and the ambiguous-card
  LLM rubric (old lines ~57–166). The skill now invokes `construct card evaluate` and presents its
  `PromotionDecision` output (`promote | hold | escalate` + `target_lifecycle` + `reasoning` + `method`).
  The Python `card.evaluate` L3 gate (Plan 02) is the single source of judgment (D-09); no second,
  unguarded judgment path can drift from the tested gate. The `method` field is surfaced so
  failure-driven (`rule-based`) escalations read differently from genuine borderline (`llm-judgment`)
  ones. The skill performs no lifecycle writes — approved promotions flow through the reviewed
  curation path.

## allowed-tools: Before / After

| Skill | Before | After |
|-------|--------|-------|
| construct-research-cycle | `Read, Bash(construct), WebSearch, WebFetch, MCP(connect)` | `Read, Bash(construct), MCP(connect)` |
| construct-curation-cycle | `Read, Bash(construct), MCP(connect)` | `Read, Bash(construct), MCP(connect)` (body rewired) |
| construct-card-evaluate | `Read, Bash(construct), MCP(connect)` | `Read, Bash(construct), MCP(connect)` (body rewired) |

All three now carry no `WebSearch`, `WebFetch`, `Write`, or `Edit` in `allowed-tools`, and all
retain `Bash(construct)` (thin delegators). `grep -c "WebSearch\|WebFetch"` returns 0 for the
whole research-cycle file (body prose reworded to avoid the literal tokens per the acceptance criterion).

## Verification

- `tests/contract/test_skill_migration.py` — **6 passed** (all three skills × drop-forbidden-tools
  + still-delegates-to-CLI). This was previously the only failing test in the repo
  (`construct-research-cycle` still carried `WebSearch, WebFetch`).
- Full suite `.venv/bin/pytest tests/ -q` — **389 passed, 0 failed** (109 warnings, all pre-existing
  deprecation/collection warnings unrelated to this plan).
- Task 1 acceptance greps: research-cycle WebSearch/WebFetch count = 0; research-cycle references
  `construct research run`/`research review` (9 hits); curation-cycle references
  `construct curation run`/`curation review` (9 hits).
- Task 2 acceptance greps: card-evaluate references `construct card evaluate` (4 hits), no inline
  promotion-threshold ruleset remains.

## Threat Model Compliance

- **T-12-17 (Elevation of Privilege — skill allowed-tools):** mitigated. All three skills dropped
  web-fetch/workspace-write from `allowed-tools`; `test_skill_migration.py` asserts their absence so
  a regression fails CI. All writes flow through the Python reviewed-write path.
- **T-12-18 (Tampering — duplicate judgment logic):** mitigated. card-evaluate inline rules folded
  into the Python gate (D-09); no second, unguarded judgment path.
- **T-12-SC (npm/pip installs):** N/A — no new packages.

## Deviations from Plan

**None functional.** One minor wording adjustment: the research-cycle prose migration note and a
validation checklist line originally mentioned the literal strings "WebSearch"/"WebFetch" while
explaining what was removed. The plan's Task 1 acceptance criterion requires
`grep -c "WebSearch\|WebFetch"` over the whole file to return 0, so those two prose mentions were
reworded to "web-fetch" / "web search / fetch". No behavioral impact; the `allowed-tools` frontmatter
(what the test guards) was correct on first write.

## Known Stubs

None. The skills delegate to already-shipped, test-green capabilities (Waves 1–5).

## OUTSTANDING MANUAL UAT (Human Action Required)

This plan is `autonomous: false`. **Task 3 is a `checkpoint:human-verify` end-to-end conversational
UAT that was intentionally NOT performed by the executor** (per 12-VALIDATION.md "Manual-Only
Verifications"). A human must run it to fully close the plan:

1. Run the migrated `construct-curation-cycle` skill conversationally against `test-ws/my-construct`.
2. Confirm it invokes `construct curation run` (not inline logic) and pauses presenting the
   consolidated `gate_queue` (promotion / connection / archive / escalate items, with the `method`
   field visible).
3. Approve a subset, reject the rest; confirm it calls `construct curation review` and only the
   approved items are written (re-run `construct curation inspect` to see outcomes).
4. Confirm zero direct WebSearch / WebFetch / Write occurred during the session.
5. Resume signal: type "approved" or describe issues with the skill review loop.

Optionally repeat the analogous conversational check for `construct-research-cycle`
(scope → `research run` → review gate → `research review` → digest) and `construct-card-evaluate`
(`card evaluate` → PromotionDecision presentation, method field visible).

The deterministic deliverable (SKILL.md edits + the automated `test_skill_migration.py` guard +
full-suite green) is complete; only the interactive human verification remains.

## Self-Check: PASSED

- FOUND: CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md (allowed-tools clean)
- FOUND: CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md (body rewired)
- FOUND: CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md (thin wrapper)
- FOUND: commit 6a48a53 (Task 1)
- FOUND: commit ed6482b (Task 2)
- test_skill_migration.py: 6 passed; full suite: 389 passed, 0 failed
