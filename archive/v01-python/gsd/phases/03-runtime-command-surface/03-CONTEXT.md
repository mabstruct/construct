# Phase 3: Runtime & Command Surface - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers the local runtime and the shared command/chat surface for steering CONSTRUCT, inspecting status, managing domains, routing work to configured model tiers, and recovering safely from interruption. It covers how users express intent through commands or chat and how the system turns that intent into auditable runtime actions. Browser-only UI behavior, graph exploration, and activity dashboards remain out of scope for later phases.

</domain>

<decisions>
## Implementation Decisions

### Command And Chat Input Model
- **D-01:** The primary end-user interaction model should be natural language first rather than raw structured field entry.
- **D-02:** Structured input should remain available as a fallback for power users, explicit correction, or low-level flows.
- **D-03:** Internal canonical structures such as comma-separated seed fields or schema lists are implementation details, not the primary user-facing UX.

### Clarification Flow
- **D-04:** When a user gives a broad or underspecified request, CONSTRUCT should use that natural-language request as the starting point and ask only for the missing or ambiguous fields.
- **D-05:** CONSTRUCT should not force users through the full field set when enough information is already present in the initial request.
- **D-06:** Follow-up clarification should happen step by step rather than silently inferring and writing canonical state.

### Confirmation And Auditability
- **D-07:** Before writing canonical workspace state or committing a runtime action that depends on parsed intent, CONSTRUCT should show a structured summary of the interpreted data.
- **D-08:** The structured summary is the main confirmation surface where users can verify or correct how their natural-language request was translated into internal fields.

### Workspace Bootstrap
- **D-09:** A new `construct chat <path>` command is the REPL entry point. When no workspace exists at `<path>`, it drops into the NL bootstrap flow; when one exists, it starts a normal runtime session. `construct init <path>` remains untouched as the deterministic structured fallback.
- **D-10:** Filesystem path stays a positional argument. NL clarification only captures canonical content — slug, display name, scope, taxonomy seeds, source priorities, research seeds — never paths or other filesystem-level inputs.
- **D-11:** NL bootstrap is a single continuous conversation from the user's perspective (workspace + first domain captured together, matching `construct init` scope), but internally composed of the workspace-bootstrap intent plus the domain-setup intent so the domain-setup handler stays reusable for later "add another domain" flows. The pre-write confirmation shows workspace-level and domain-level fields in one structured summary.

### Claude's Discretion
- Exact wording of clarification questions and structured summaries.
- Exact fallback affordance for advanced or power-user structured entry.
- Exact representation of internal parsed fields in confirmation views, as long as the user-facing language stays plain and the internal mapping remains auditable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product And Architecture
- `CONSTRUCT-spec/construct-prd.md` — v0.1 product contract, local-first runtime expectations, and shared command/chat interaction goals.
- `CONSTRUCT-spec/construct-user-journeys.md` — user-facing runtime journey showing interview-style domain setup and chat-led steering.
- `CONSTRUCT-spec/adrs/adr-0001-python-first-drop-openclaw.md` — Python-first architecture and stable interface boundaries around canonical state and derived read models.

### Planning Constraints
- `.planning/ROADMAP.md` — Phase 3 goal, scope, and success criteria.
- `.planning/REQUIREMENTS.md` — mapped Phase 3 requirements: `RUNT-01`, `RUNT-02`, `RUNT-03`, `RUNT-04`, `CHAT-01`, `WORK-04`.
- `.planning/PROJECT.md` — product-level non-negotiables: local-first operation, markdown/YAML as source of truth, and auditable agent behavior.

### Current Implementation Context
- `src/construct/cli.py` — current CLI prompts that use comma-separated list entry and therefore define the low-level baseline this phase should evolve beyond.
- `README.md` — current documented init flow and prompt wording that expose the comma-separated interface today.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/cli.py` already centralizes the current prompt flow and CSV parsing helpers, making it the likely starting point for evolving the interaction model.

### Established Patterns
- The current interface uses direct `typer.prompt(...)` calls for required values and converts some inputs into normalized internal forms.
- The init flow already separates user-facing input from canonical normalized storage for domain slugs and taxonomy seeds.

### Integration Points
- The shared command/chat surface introduced in Phase 3 should replace or wrap low-level comma-separated prompts with a natural-language interpretation layer.
- Any parsed intent must still resolve to canonical workspace data and auditable runtime events before state changes occur.

</code_context>

<specifics>
## Specific Ideas

- Treat comma-separated lists as a low-level or advanced fallback, not the main end-user interface.
- Let users state intentions naturally, then translate that intent into internal fields.
- Ask only for what is missing.
- Always show a structured parsed summary before writing.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-runtime-command-surface*
*Context gathered: 2026-04-22*
