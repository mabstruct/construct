---
phase: 17-architecture-doc-set-daily-run-discoverability
plan: 03
subsystem: testing
tags: [documentation, catalog, contract-guard, introspection, typer, mcp, capability-registry]

# Dependency graph
requires:
  - phase: 17-02
    provides: "construct-daily-cycle skill dir (the 25th construct-* skill the guard counts)"
  - phase: 16
    provides: "test_doc_command_references.py FIX-04 introspection helpers (_command_paths/LEAF_COMMANDS/VALID_PATHS/_invocations/_code_spans)"
  - phase: 03
    provides: "capability registry + get_registry() the guard introspects"
provides:
  - "tests/contract/test_artifact_catalog.py — a mechanical guard asserting artifact-catalog.md documents every live capability id, MCP tool, Typer leaf, and construct-* skill dir"
  - "artifact-catalog.md Runtime capabilities (L2/L3) section — capability registry table, non-registry CLI table, narrative search-spine/LLM-gate rows"
  - "construct-spike-run + construct-daily-cycle catalog skill rows"
affects: [17-04, architecture-docs, catalog-maintenance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Catalog-vs-introspection guard: derive documented-surface truth from live code + filesystem, assert introspected <= documented (subset, not equality), pair with a vacuity meta-guard"
    - "Import (not re-implement) the sibling guard's introspection helpers via sys.path.insert(parent) + bare import"

key-files:
  created:
    - tests/contract/test_artifact_catalog.py
  modified:
    - CONSTRUCT-CLAUDE-spec/artifact-catalog.md

key-decisions:
  - "Guard imports the FIX-04 helpers via a sys.path.insert(Path(__file__).parent) + bare `from test_doc_command_references import ...` because tests/contract carries an __init__.py (package) and pythonpath only adds repo-root+src, so a bare import would not otherwise resolve."
  - "Documented-surface extractor tokenizes catalog code spans keeping `.`/`_`/`-` intact (capability ids, MCP snake names, skill kebab names) and reuses FIX-04's _invocations for CLI leaf paths — two extractors, one per token shape."
  - "All 34 Typer leaves documented across TWO tables: the 27 registry-bound leaves in the capability table CLI column, and the 7 independent-path leaves (views validate, spike run/list, tag extract/approve/list, mcp) in a dedicated non-registry table — encoding the registry/Typer two-source split."
  - "No frozen integer counts in the doc: 'Skills (23)' and '23 skills' replaced with guard-checked phrasing; capability/MCP/leaf counts described as live-introspection-backed, never hand-typed (never 27)."

patterns-established:
  - "Pattern 1: A doc-truth guard that fails loudly on vacuity — assert len(reg.list())>25, len(reg.list_mcp_tools())>20, ('daily','run') in VALID_PATHS, a known skill dir present, AND the extractor found known tokens — so a broken import can never make subset checks pass on an empty set."
  - "Pattern 2: Registry and Typer app are distinct introspection sources; a leaf need not carry a registry id (views/spike/tag holdout documented explicitly, not implied to route through the registry)."

requirements-completed: [DOC-02]

coverage:
  - id: D1
    description: "Catalog-vs-introspection guard: every live capability id, MCP tool name, Typer leaf, and construct-* skill dir must have a catalog row; empty introspection fails loudly via a vacuity meta-guard"
    requirement: "DOC-02"
    verification:
      - kind: unit
        ref: "tests/contract/test_artifact_catalog.py (5 tests: 4 subset guards + vacuity meta-guard)"
        status: pass
    human_judgment: false
  - id: D2
    description: "artifact-catalog.md expanded with the L2/L3 runtime surface (capability/CLI/MCP rows), construct-spike-run + construct-daily-cycle skill rows, both config-topology deferrers removed"
    requirement: "DOC-02"
    verification:
      - kind: unit
        ref: "tests/contract/test_artifact_catalog.py#test_every_capability_id_has_a_catalog_row (+ mcp/leaf/skill variants)"
        status: pass
      - kind: other
        ref: "grep -c config-topology CONSTRUCT-CLAUDE-spec/artifact-catalog.md == 0"
        status: pass
    human_judgment: false

# Metrics
duration: 7min
completed: 2026-07-25
status: complete
---

# Phase 17 Plan 03: Architecture Doc Set & daily.run Discoverability (Catalog Guard) Summary

**A mechanical guard (`test_artifact_catalog.py`) that pins artifact-catalog.md to live introspection of the capability registry, Typer app, MCP tool list, and skills glob — plus a catalog expanded with the L2/L3 runtime surface it never carried, so the inventory physically cannot silently rot.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-25T17:44:40Z
- **Completed:** 2026-07-25T17:51:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- New `tests/contract/test_artifact_catalog.py` — four subset guards (capability ids ⊆ documented, MCP tool names ⊆ documented, Typer leaves ⊆ documented CLI, skill dirs ⊆ documented) plus a mandatory vacuity meta-guard, importing (not re-implementing) the FIX-04 introspection helpers.
- `artifact-catalog.md` gained a "Runtime capabilities (L2/L3)" section: a 28-row capability registry table (id → CLI → MCP), a 7-row non-registry CLI table for the views/spike/tag/mcp independent-path holdout, and narrative search-spine + LLM-gate rows.
- Added the criterion-named missing `construct-spike-run` row and the new `construct-daily-cycle` row; dropped every frozen hand-typed count in favour of guard-checked phrasing.
- Removed both config-topology deferrers this file owned (Related-documents row + Maintenance step 6) — the catalog now owns the directory/inventory role ahead of config-topology.md's deletion in plan 17-04.

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1: Write the catalog-vs-introspection guard (RED)** - `0fd7ad3` (test)
2. **Task 2: Expand artifact-catalog.md with runtime surface + missing skill rows (GREEN)** - `76821eb` (docs)

_TDD plan: the RED commit adds the failing guard; the GREEN commit turns it green by expanding the catalog._

## Files Created/Modified
- `tests/contract/test_artifact_catalog.py` (created) - Catalog-vs-introspection guard: 5 tests deriving truth from `get_registry().list()`, `get_registry().list_mcp_tools()`, `LEAF_COMMANDS`, and the `construct-*` skills glob.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` (modified) - New Runtime capabilities (L2/L3) section, two new skill rows, frozen counts removed, config-topology deferrers removed.

## Decisions Made
- Guard imports the FIX-04 helpers via `sys.path.insert(Path(__file__).parent)` + bare import, because `tests/contract` is a package (has `__init__.py`) and `pythonpath` only adds repo-root and `src`; a bare `from test_doc_command_references import ...` would not resolve otherwise. Verified empirically under `.venv/bin/pytest`.
- Two extractors, one per token shape: a code-span tokenizer that keeps `.`/`_`/`-` intact (for capability ids / MCP snake names / skill kebab names) and a reuse of FIX-04's `_invocations` for multi-token CLI leaf paths.
- All 34 Typer leaves are documented across two tables so the registry (28 caps / 22 MCP) and Typer (34 leaves) stay two distinct sources; the 7 independent-path leaves (views validate, spike run/list, tag extract/approve/list, mcp) are marked explicitly as NOT registry-routed.

## Deviations from Plan

None - plan executed exactly as written. (The plan's live-count expectations — 28 capabilities / 22 MCP tools / 34 leaves / 25 skills — matched live introspection exactly; the corrected capability count is 28, never 27, and no `27` appears in the guard or the doc.)

## Issues Encountered
None. The one point requiring care was the import path (tests/contract is a package), resolved by the `sys.path.insert(parent)` idiom and verified before writing the guard.

## Known Stubs
None - this plan ships a test and a documentation expansion; no placeholder data, no unwired components.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 17-04 can now safely `git rm config-topology.md`: this catalog no longer references it (both deferrers removed, `grep -c config-topology` == 0), and the catalog owns the directory/inventory role.
- The catalog is now self-defending: any new capability, MCP tool, CLI leaf, or skill dir added without a catalog row will fail `test_artifact_catalog.py`.
- Full suite green: 524 passed / 1 skipped; FIX-04 `_KNOWN_BROKEN` remains empty.

---
*Phase: 17-architecture-doc-set-daily-run-discoverability*
*Completed: 2026-07-25*
