# Phase 1: Contract Canon & Artifact Governance - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Canonize the artifact contracts and enforcement model for the current Claude-native CONSTRUCT system so later runtime work can rely on one authoritative workspace shape, one contract source, strict write gates, and a defined migration/proof story.

</domain>

<decisions>
## Implementation Decisions

### Canonical workspace shape
- **D-01:** The canonical workspace layout for Phase 1 is the active Claude-native shape defined by the current spec and template set, not the dormant Python `src/construct/` layout.
- **D-02:** Python/runtime work must be reconciled to the active Claude-native workspace contract rather than pulling the repo back to the older `domains/{id}/domain.yaml` + required `workflows/`/`db/`/`views/` shape.

### Contract authority
- **D-03:** `CONSTRUCT-CLAUDE-spec/`, the active template files in `CONSTRUCT-CLAUDE-impl/construct/templates/`, and `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` are the authoritative contract source set for this phase.
- **D-04:** Runtime code, validators, and skill procedures must be aligned to that authority set; current implementation behavior is not authoritative when it conflicts with the active spec/template/catalog layer.

### Validation and write gates
- **D-05:** Invalid cards, refs, connections, and workflow outputs must be blocked before they become canonical source-of-truth files.
- **D-06:** Post-write validation still matters, but only for cross-file consistency, audit checks, and fixture verification after a valid write has landed.

### Migration and proof targets
- **D-07:** Phase 1 must produce an explicit migration path for existing CONSTRUCT workspaces so contract hardening does not strand current users.
- **D-08:** `test-ws/` is the canonical proof target for Phase 1 validation. Older `tests/fixtures/v02/` assets may remain as supporting or historical fixtures, but they are not the primary acceptance target for this phase.
- **D-09:** Avoid building a broad dual-layout compatibility layer as the default solution. Prefer one canonical layout plus a defined migration path.

### Support artifact status
- **D-10:** `digests/` and `publish/` should be treated as derived outputs, not canonical graph source-of-truth artifacts.

### the agent's Discretion
- Exact mechanism for pre-write staging and rollback.
- Exact format of the migration document and checklist.
- Whether supporting historical fixtures are mirrored into the new proof flow or only referenced.
- Exact event-schema versioning mechanics, as long as they preserve the hard write-gate decision above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and project constraints
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and dependency boundary.
- `.planning/REQUIREMENTS.md` — FND-01 through FND-06 and the explicit out-of-scope constraints.
- `.planning/PROJECT.md` — product continuity, sequencing, and Claude-native compatibility constraints.
- `.planning/STATE.md` — current phase focus and the already-identified Phase 1 concern areas.
- `.planning/research/SUMMARY.md` — research-backed risks and recommended direction for contract canon, write gates, migration, and graph truth.

### Active contract docs
- `CONSTRUCT-CLAUDE-spec/README_FIRST.md` — navigation map for which spec documents are authoritative.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — master inventory and ownership/audit matrix for active Claude-native artifacts.
- `CONSTRUCT-CLAUDE-spec/knowledge-card-schema.md` — canonical card contract.
- `CONSTRUCT-CLAUDE-spec/data-schemas.md` — canonical non-card artifact contracts, including refs, connections, search seeds, and events.
- `CONSTRUCT-CLAUDE-spec/validation-strategy.md` — intended validation layers and the write-time validation posture for the Claude-native system.
- `CONSTRUCT-CLAUDE-spec/process.md` — contract change process and sync expectations across spec, templates, references, and skills.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — runtime layering decision and the rule that workspace files remain canonical while deterministic enforcement moves into Python.

### Active implementation contracts
- `CONSTRUCT-CLAUDE-impl/construct/templates/card.md` — active card template shape.
- `CONSTRUCT-CLAUDE-impl/construct/templates/connections.json` — active connection artifact template.
- `CONSTRUCT-CLAUDE-impl/construct/templates/domains.yaml` — active domain registry template.
- `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml` — active governance artifact template.
- `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml` — active model-routing artifact template.
- `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json` — active search-seed artifact template.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-init/SKILL.md` — current workspace initialization contract that downstream planning must reconcile with the chosen canonical layout.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md` — current validation contract and the intended validation layers.

### Proof and fixture references
- `README.md` — repo-level statement that `test-ws/` is the active fixture location.
- `CONSTRUCT-CLAUDE-spec/spec-v02-validation.md` — historical validation/fixture matrix; useful as supporting context, but not the primary Phase 1 acceptance target.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/schemas/card.py` — existing Pydantic card contract and markdown parsing helpers that can be aligned to the canonical spec.
- `src/construct/schemas/config.py` — existing schema layer for domains, governance, and model routing artifacts.
- `src/construct/schemas/workspace.py` — existing workspace scaffold contract, currently drifted from the active Claude-native layout.
- `src/construct/storage/workspace.py` — existing loader and typed parse boundary patterns for YAML/JSON artifacts.
- `src/construct/services/validation.py` — existing structured validation report pattern and canonical-path scan entry point.
- `CONSTRUCT-CLAUDE-impl/construct/templates/*` — the active artifact templates that should inform any contract reconciliation.

### Established Patterns
- Workspace files are the only source of truth; derived layers must not write back upstream.
- Contract changes are expected to update specs, templates, references, and skills together.
- Validation is already conceptually layered: schema, governance, cross-file consistency, functional proof, and audit trail.
- `artifact-catalog.md` already acts as the master inventory for artifact ownership and maintenance expectations.

### Integration Points
- `src/construct/` validators and workspace scaffolding must be reconciled to the chosen Claude-native contract before Phase 3 CLI/MCP work can trust them.
- `construct-workspace-init` and `construct-workspace-validate` are the highest-leverage skill contracts to align first because they define creation and enforcement behavior.
- Fixture validation must align roadmap requirements, README guidance, and actual checked-in workspace assets before downstream contract tests are planned.

</code_context>

<specifics>
## Specific Ideas

- Do not let the dormant Python workspace layout become a second official contract.
- Use one canonical layout plus migration, not long-lived parallel compatibility by default.
- Treat `test-ws/` as the real proof target for this phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-contract-canon-artifact-governance*
*Context gathered: 2026-06-08*
