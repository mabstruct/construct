# Phase 1: Workspace & Canonical Data Foundation - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers a valid local CONSTRUCT workspace and the canonical markdown/YAML data foundation. It covers `construct init <path>`, guided domain setup, canonical workspace files, and validation for cards and config files. Search indexes, graph derivation, runtime orchestration, and browser/UI behavior remain out of scope for later phases.

</domain>

<decisions>
## Implementation Decisions

### Workspace Shape
- **D-01:** `construct init` should create the full long-term workspace scaffold immediately rather than a Phase 1-only subset.
- **D-02:** The initial scaffold should include both canonical source-of-truth areas and rebuildable/derived areas so the workspace contract is stable from day one, even if later phases populate more of it.

### Init Experience
- **D-03:** `construct init <path>` should be lightly guided with sensible defaults.
- **D-04:** Init should ask only for the essential inputs needed for domain setup, then write defaults for the rest so onboarding stays fast.

### Domain Configuration Model
- **D-05:** Domain setup should use per-domain folders from the start.
- **D-06:** A root `domains.yaml` must still exist as the canonical registry of domains.
- **D-07:** Per-domain files should hold the domain-local setup details, while the root registry remains the global source for domain indexing.

### Validation Posture
- **D-08:** Validation should be strict on canonical structure.
- **D-09:** Malformed YAML, missing required fields, invalid enum values, invalid filenames/IDs, and other schema-breaking issues should fail clearly.
- **D-10:** Softer quality issues should surface as warnings rather than hard failures.

### Claude's Discretion
- Exact prompt wording and UX flow for the essential init questions.
- Exact file naming for per-domain setup files, as long as it preserves the root registry plus per-domain-folder model.
- Exact warning phrasing and presentation format for non-blocking validation feedback.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product And Architecture
- `CONSTRUCT-spec/construct-prd.md` — v0.1 architecture principles, workspace directory structure, model-routing contract, and the local-first storage model.
- `CONSTRUCT-spec/adrs/adr-0001-python-first-drop-openclaw.md` — locks the Python-first architecture and the stable contract principle around `views/`, event logs, and source-of-truth files.

### Workspace Topology
- `CONSTRUCT-spec/construct-repo-topology.md` — target repository structure and the long-term user workspace layout, including tracked vs rebuildable areas.

### Canonical Data Contract
- `CONSTRUCT-spec/knowledge-card-schema.md` — canonical card file format, required frontmatter, validation rules, and connection metadata constraints.

### Planning Constraints
- `.planning/ROADMAP.md` — Phase 1 goal, scope, and success criteria.
- `.planning/REQUIREMENTS.md` — mapped Phase 1 requirements: `WORK-01`, `WORK-02`, `WORK-03`, `CARD-01`, `CARD-03`, `CARD-04`.
- `.planning/PROJECT.md` — product-level non-negotiables: markdown/YAML as source of truth, local-first architecture, and derived state remaining rebuildable.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No implementation code exists yet; Phase 1 is establishing the initial project and workspace contracts.

### Established Patterns
- Current constraints come from specs and planning docs, not existing runtime code.
- The codebase is still pre-implementation, so planning should prefer the smallest foundation that satisfies the documented workspace and schema contracts.

### Integration Points
- `construct init <path>` is the entry point for workspace creation.
- The workspace contract chosen here must leave later phases room to add rebuildable index, graph, runtime, and `views/` behavior without changing canonical ownership.

</code_context>

<specifics>
## Specific Ideas

- Keep onboarding fast: ask only the essential setup questions during init.
- Treat the full workspace scaffold as a stable contract from the first run, even if some areas are mostly placeholders until later phases.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-workspace-canonical-data-foundation*
*Context gathered: 2026-04-22*
