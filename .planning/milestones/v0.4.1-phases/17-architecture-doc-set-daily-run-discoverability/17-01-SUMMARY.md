---
phase: 17-architecture-doc-set-daily-run-discoverability
plan: 01
subsystem: documentation
tags: [architecture, layer-model, adr-0003, doc-truth, spec-tree]

# Dependency graph
requires:
  - phase: 15-views-generate-data-resolution
    provides: adr-0005 views-refresh ownership (Python layer owns the derived-view-data refresh)
  - phase: 14-durable-state-config-truth
    provides: adr-0004 durable-workflow-checkpoints carve-out (referenced in the layer-model anti-patterns)
provides:
  - "architecture-overview.md rewritten onto ADR-0003's L0-L4 runtime stack as the single 'Layer N' vocabulary"
  - "The views cache renamed 'derived view data'; the false single-writer claim removed; Python-runtime write-ownership stated"
  - "Five broken vocabulary-doc citations repointed to their real on-disk home; spec-v02-data-model.md citations preserved"
affects: [17-02 catalog expansion, 17-03 daily skill, v0.5 UI planning, DOC-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single canonical layer vocabulary (ADR-0003 L0-L4); one-way data flow expressed as a property within/across the stack, not a competing numbering"

key-files:
  created:
    - .planning/phases/17-architecture-doc-set-daily-run-discoverability/17-01-SUMMARY.md
  modified:
    - CONSTRUCT-CLAUDE-spec/architecture-overview.md

key-decisions:
  - "Adopt ADR-0003's L0-L4 numbering verbatim; the views cache becomes 'derived view data' and is never 'Layer 2' (Layer 2 = Python pipeline runtime)"
  - "Layer 2 (Python runtime) owns every write to layer 1; the capability registry is the single write contract; skills/CLI/MCP/UI reach it only through the invoke surface (Layer 3)"
  - "Invariants I1-I4 re-anchored to the workspace-SOT <-> derived-view-data relationship; I4's spec-v02-data-model.md citation kept"
  - "Five vocab citations repointed to ../CONSTRUCT-CLAUDE-impl/construct/references/; spec-v02-data-model.md exists (audit mis-named it) so its three citations are untouched"

patterns-established:
  - "Guard-adjacent doc truth: layer numbering in the overview must match ADR-0003's permanent Layer-model block exactly"

requirements-completed: [DOC-01]

coverage:
  - id: D1
    description: "architecture-overview.md presents ADR-0003's L0-L4 model with the Python runtime named as Layer 2 and the views cache renamed 'derived view data' (single layer vocabulary)"
    requirement: DOC-01
    verification:
      - kind: other
        ref: "grep -c 'derived view data' architecture-overview.md == 30 (>=1); grep -c 'Layer 2 — DERIVED STATE' == 0; grep -niE 'python (pipeline )?runtime' matches Layer 2 desc"
        status: pass
    human_judgment: true
    rationale: "'Exactly one Layer N vocabulary survives' and 'the narrative reads correctly to a v0.5 planner' are prose-coherence judgments a grep cannot fully confirm; a human should skim the rewritten §2/§3/§7/§8."
  - id: D2
    description: "The false 'skills are the only legitimate writers to layer 1' claim is removed and Python-runtime write-ownership is visible"
    requirement: DOC-01
    verification:
      - kind: other
        ref: "grep -c 'only legitimate writers' architecture-overview.md == 0; grep -c 'skills are the only' == 0; 'owns every write to layer 1' present"
        status: pass
    human_judgment: false
  - id: D3
    description: "The five broken vocab-doc citations resolve to real files; the three spec-v02-data-model.md citations are preserved"
    requirement: DOC-01
    verification:
      - kind: other
        ref: "all five CONSTRUCT-CLAUDE-impl/construct/references/*.md exist; grep -c 'spec-v02-data-model.md' == 3 (>=3); full resolve-sweep finds no other broken citation"
        status: pass
      - kind: integration
        ref: "tests/contract/test_doc_command_references.py — 36 passed, 1 skipped"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-25
status: complete
---

# Phase 17 Plan 01: Architecture-Overview Rewrite onto ADR-0003 L0-L4 Summary

**architecture-overview.md rewritten onto ADR-0003's L0-L4 runtime stack as the single layer vocabulary — Python runtime named as Layer 2, views cache renamed "derived view data", the false single-writer claim removed with Python-runtime write-ownership stated, and the five broken vocab citations repointed while spec-v02-data-model.md's citations are preserved.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-07-25T17:26Z (approx)
- **Completed:** 2026-07-25T17:38Z
- **Tasks:** 3
- **Files modified:** 1 (source doc) + 1 created (this summary)

## Accomplishments
- Replaced the v0.2 "Three Layers" data-flow model (canonical → views cache → SPA) with ADR-0003's permanent L0-L4 runtime stack (L0 skill specs, L1 workspace SOT, L2 Python pipeline runtime, L3 invoke surface, L4 UI shell), with LLM gates as a cross-cutting concern. Exactly one "Layer N" vocabulary now survives.
- Re-expressed the one-way data-flow narrative (workspace → derived view data → presentation) as a *property* within/across the stack, not a competing numbering; the views cache is now consistently "derived view data" (30 occurrences).
- Removed the false "skills are the only legitimate writers to layer 1" claim at §3.1 and §8.1 decision-tree item 4; stated that Layer 2 (the Python runtime) owns every write to layer 1, reached only through registered capabilities via the invoke surface. Grounded in `catalog.py` handlers and adr-0005.
- Re-anchored invariants I1-I4 to the workspace-SOT ↔ derived-view-data relationship; kept I4's `spec-v02-data-model.md` citation.
- Repointed the five §9.3 vocabulary citations to `../CONSTRUCT-CLAUDE-impl/construct/references/` (real on-disk files) and preserved the three `spec-v02-data-model.md` citations (the file exists; the audit mis-named it).

## Task Commits

Each task was committed atomically:

1. **Task 1: Adopt ADR-0003's L0-L4 as the single layer vocabulary (D-01)** - `f9a23e0` (docs)
2. **Task 2: Remove the false single-writer claim; make Python-runtime write-ownership visible (D-02)** - `dd9bbe0` (docs)
3. **Task 3: Repoint the five broken vocab-doc citations; keep spec-v02-data-model.md (D-03)** - `b29406c` (docs)

**Plan metadata:** committed with STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified
- `CONSTRUCT-CLAUDE-spec/architecture-overview.md` - Full rewrite of the layer narrative (§1-§9) onto ADR-0003's L0-L4 spine; +131 / -107 lines. Prose only, no new code symbols.
- `.planning/phases/17-architecture-doc-set-daily-run-discoverability/17-01-SUMMARY.md` - This summary.

## Decisions Made
- Kept ADR-0003's `Layer model (permanent)` numbering verbatim (L0-L4) as THE spine; the views cache is "derived view data", never a "Layer 2".
- Framed the capability registry as the single write contract; skills are thin delegating wrappers (Phase 12 API-04), not direct workspace writers.
- Added an `adr-0005-views-refresh-ownership.md` entry to the Related header and §9.1, since Layer 2's ownership of the derived-view-data refresh is now described in-doc.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' grep gates and the contract-test backstop passed on the first verification.

## Issues Encountered
None. The full resolve-sweep of the doc's backtick citations confirmed only the five vocab refs were broken (matching RESEARCH Finding 1); the `???` entries the sweep flagged were illustrative workspace/code paths (`~/my-construct/AGENTS.md`, bare `catalog.py`, `SKILL.md`), not repo citations.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DOC-01 satisfied for the architecture-overview.md portion; ROADMAP criterion 1 met.
- Ready for 17-02 (artifact-catalog expansion + guard + config-topology deletion + spec-v04 fence) and 17-03 (daily skill). The layer vocabulary those plans reference is now canonical here.
- No blockers introduced.

## Self-Check: PASSED

- FOUND: `CONSTRUCT-CLAUDE-spec/architecture-overview.md`
- FOUND: `17-01-SUMMARY.md`
- FOUND commits: `f9a23e0`, `dd9bbe0`, `b29406c`

---
*Phase: 17-architecture-doc-set-daily-run-discoverability*
*Completed: 2026-07-25*
