---
phase: 05-grounded-synthesis-graph-reasoning
plan: 04
subsystem: claude-native (skill)
tags: [synthesis, confidence-propagation, hedging, cli-migration, skill-doc]
requires:
  - phase: 04-guided-workflow-operability
    provides: Skill migration pattern (restricted allowed-tools, CLI/MCP invocation, INPUT/OUTPUT documentation)
provides:
  - Updated construct-synthesis SKILL.md with CLI command references for card acquisition
  - Confidence propagation documentation (per-citation + aggregate + hedging rules)
  - Error handling table for CLI failures and low-confidence scenarios
affects: [construct-curation-cycle (composed skill referencing synthesis), claude-native skill docs]
tech-stack:
  added: []
  patterns:
    - CLI command replacement pattern: construct ask domain / construct knowledge card list for card acquisition
    - Confidence metadata block format with min/mean/weighted aggregate
    - Three-tier hedging rule pattern (>= 4 direct, == 3 neutral, <= 2 hedge)
    - Error handling table for skill procedures
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md
key-decisions:
  - "Synthesis remains Claude-native per D-02; skill updated to call CLI commands instead of doing inline file I/O"
  - "Hedging rules simplified to three tiers (>=4 direct, ==3 neutral, <=2 hedge) matching ask.domain confidence model"
  - "Write removed from allowed-tools per Phase 4 migration pattern — synthesis output is CLI structured output"
requirements-completed: [ING-06]
duration: 5min
completed: 2026-06-11
---

# Phase 05 Plan 04: Synthesis Skill Update — CLI Commands & Confidence Propagation Summary

**Synthesis skill updated with CLI command references for grounded Q&A and confidence-aware inline hedging annotations**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-11T13:38:00Z
- **Completed:** 2026-06-11T13:43:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Restricted `allowed-tools` to `Read, Bash(construct), MCP(connect), WebSearch, WebFetch` — removing `Write` and `Edit` per Phase 4 migration pattern
- Added `INPUT` section documenting workspace, query/topic, optional domain, and max_cards parameters
- Added `OUTPUT` section documenting synthesis, citations, and confidence metadata (per-citation + aggregate + inline hedging)
- Replaced inline `Read cards/*.md` card acquisition with `construct ask domain` and `construct knowledge card list` CLI commands
- Added Step 4 for confidence metadata analysis: min/mean/weighted aggregate computation
- Added Step 5 with three-tier hedging rules: direct (`>=4`), neutral (`==3`), hedge (`<=2`)
- Added structured `Synthesis Metadata` block format with confidence range and aggregate
- Added `Error Handling` section covering CLI failures, low confidence, and missing API key
- Preserved existing valuable steps: Understand the Request, Assess Knowledge Strength, Review Prompt, Views Refresh Hook

## Task Commits

Each task was committed atomically:

1. **Task 1: Update construct-synthesis SKILL.md with CLI commands and confidence propagation** - `e2d9b69` (feat)

## Files Created/Modified

- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md` - Updated synthesis skill procedure with CLI command references, confidence propagation documentation, and hedging rules

## Decisions Made

- **Hedging tier alignment:** Used three tiers (>=4 direct, ==3 neutral, <=2 hedge) matching the `ask.domain` confidence model, rather than the original five-tier scheme. This is simpler and aligns with ING-06's requirement for clear confidence bands in synthesis output.
- **Allowed-tools alignment:** Followed the exact Phase 4 migration pattern from `construct-gap-analysis` — restricted to `Read, Bash(construct), MCP(connect), WebSearch, WebFetch` with `Write` and `Edit` removed.
- **Preserved pre/post steps:** Kept "Understand the Request" (clarification), "Assess Knowledge Strength" (source audit), "Review Prompt" (user engagement), and "Views Refresh Hook" from the original skill — these are not replaced by CLI patterns and remain valuable.

## Deviations from Plan

None — plan executed exactly as written. All six changes from the plan were applied:

1. ✅ Frontmatter updated with restricted allowed-tools
2. ✅ INPUT section added (workspace, query/topic, domain, max_cards)
3. ✅ OUTPUT section added (synthesis, citations, confidence metadata)
4. ✅ Procedure steps updated: 3 core steps (acquire via CLI → analyze confidence → draft with hedging) plus preserved pre/post steps
5. ✅ Error Handling section added (ask.domain, card list, low confidence, API key)
6. ✅ allowed-tools rationale note added

## Issues Encountered

None

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Synthesis skill now references `construct ask domain` (L2 gate) and `construct knowledge card list` CLI commands, which must exist before the skill can be used. These are implemented in other Phase 5 plans (Wave 1: ask.domain LangGraph gate, Wave 2: bridge.detect pipeline).
- The confidence propagation documentation assumes the `ask.domain` CLI returns per-card confidence in its JSON output — verify this contract when ask.domain is implemented.
- Future plans should ensure `construct knowledge card list` and `construct knowledge ref list` CLI commands support the `--domain` filter flag.

## Self-Check: PASSED

- ✅ `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md` exists
- ✅ Commit `e2d9b69` exists in git history
- ✅ `.planning/phases/05-grounded-synthesis-graph-reasoning/05-04-SUMMARY.md` exists

---

*Phase: 05-grounded-synthesis-graph-reasoning*
*Completed: 2026-06-11*
