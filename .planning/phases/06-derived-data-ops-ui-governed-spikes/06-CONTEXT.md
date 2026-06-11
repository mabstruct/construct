# Phase 6: Derived Data, Ops UI & Governed Spikes - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose stable derived-data contracts for future UI work, build a local Streamlit ops dashboard for exercising capabilities, and create a governed spike framework for safely evaluating external graph-analysis tools without changing canonical CONSTRUCT behavior.

**Requirements:** ADV-03, ADV-04, SPK-01, SPK-02, SPK-03, SPK-04

</domain>

<decisions>
## Implementation Decisions

### Derived Data Contracts (ADV-03)
- **D-01:** Full stability package — **JSON schemas + version fields + contract tests** for all `views/build/data/*.json` files. Each data file gets a JSON Schema declaration, a `version` field in its metadata, and Pydantic-backed contract tests that validate format on load.
- **D-02:** The generator (`construct-views-generate-data`) validates output against schema *before* writing, catching drift at write time.

### Ops UI — Streamlit (ADV-04)
- **D-03:** Full ops suite with three panels:
  1. **Dashboard** — Graph health: card/connection/domain counts, recent events from `log/events.jsonl`
  2. **Gate review** — Review `ask.domain` Q&A results and bridge candidates. Approve/reject candidates from UI.
  3. **Capability runner** — Execute any registered capability from UI with form inputs, view structured results.
- **D-04:** Streamlit app at `src/construct/ui/streamlit_app.py` (as specced in PRD). Read-only for derived data; all capability executions go through the capability registry. Never writes to SOT directly.

### Spike Framework (SPK-01)
- **D-05:** **Spike runner CLI + documented procedures.** `construct spike run <tool-name> --workspace <path>` creates a temp workspace copy, runs the external tool in isolation, captures output, reports findings without risk to canonical data.
- **D-06:** Documented SKILL.md for each spike type (Graphify, InfraNodus) describing how to run, what to evaluate, and how to interpret results.

### Tag/Keyword Pipeline (SPK-02, SPK-03)
- **D-07:** Full pipeline that:
  1. Extracts candidate tags/keywords from ingested `refs/*.json` source material using LLM-assisted extraction
  2. Writes candidates to a reviewable file at `log/tag-candidates.json`
  3. On user approval via curation cycle → updates `search-seeds.json`
- **D-08:** Tags are NEVER auto-accepted. All candidates must pass through the curation review cycle (SPK-03).

### InfraNodus-Style Exploration (SPK-04)
- **D-09:** Evaluated via the spike framework (D-05/06) — not built as a permanent feature in Phase 6. Documented procedure for running InfraNodus (or similar) against a workspace copy and interpreting results for future UI patterns.

### the Agent's Discretion
- Exact JSON Schema structure for each views data file
- Streamlit layout and component choices (within the three-panel scope)
- Spike runner implementation detail (temp dir, copy semantics, tool interface contract)
- Tag extraction approach (LLM-based, regex, hybrid) as long as candidates are reviewable
- Whether to add `streamlit>=1.35` to `pyproject.toml` or keep as optional dependency

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 6 goal, success criteria (ADV-03, ADV-04, SPK-01–04), UI hint.
- `.planning/REQUIREMENTS.md` — Full requirement descriptions for ADV-03, ADV-04, SPK-01–04.
- `.planning/PROJECT.md` — Product continuity, v0.3→v0.4 sequencing constraints.

### Prior phase decisions
- `.planning/phases/05-grounded-synthesis-graph-reasoning/05-CONTEXT.md` — Deferred items: Streamlit ops UI / gate review panel.
- `.planning/phases/04-guided-workflow-operability/04-CONTEXT.md` — Ingestion pipeline, CLI patterns, capability registry wiring.
- `.planning/phases/03-capability-registry-cli-mcp-spine/03-CONTEXT.md` — Registry pattern, MCP server, test fixtures.

### Architecture and specs
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Four-layer architecture, invoke surfaces, Streamlit spike mention.
- `CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md` — Streamlit spike scope (lines 1001–1040), capability runner UI, gate review panel.

### Existing implementation
- `src/construct/views/` — Views data generator pipeline (create if doesn't exist yet).
- `src/construct/capabilities/registry.py` — CapabilityRegistry — dispatch engine for capability runner panel.
- `src/construct/capabilities/catalog.py` — Registered capabilities — UI lists these for execution.
- `src/construct/cli.py` — Typer CLI — Streamlit capability runner maps to these.
- `src/construct/pipelines/graph_status.py` — Graph health data for dashboard.
- `src/construct/llm/ask_domain.py` — L2 gate — review panel consumes its output.
- `src/construct/pipelines/bridge_detect.py` — Bridge pipeline — review panel consumes its output.
- `src/construct/pipelines/ingestion.py` — Ingestion pipeline — tag extraction hooks into ref creation.
- `views/build/data/` — Current views JSON files — target for contract schemas.
- `test-ws/my-construct/` — Test workspace for ops UI and spike testing.

### Existing spec docs for views data format
- `CONSTRUCT-CLAUDE-spec/spec-v02-cross-domain-data.md` — `bridges.json` schema contract.
- `CONSTRUCT-CLAUDE-spec/spec-v02-cross-domain-graph.md` — Cross-domain graph contract.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/capabilities/registry.py` — `registry.list()` and `registry.get()` — capability runner panel can enumerate and invoke capabilities.
- `src/construct/pipelines/graph_status.py` — `graph_status()` returns structured graph health data — dashboard panel reads this.
- `src/construct/pipelines/bridge_detect.py` — Bridge candidate output format — review panel consumes this.
- `src/construct/llm/ask_domain.py` — `AskDomainOutput` model with citations and confidence — review panel reviews these.
- `src/construct/services/knowledge.py` — `create_card`, `add_connection` — tag pipeline creates reviewable candidates.
- `src/construct/workspace_sot/` — Workspace loader for reading workspace state.

### Established Patterns
- Capability registry dispatch for all operations (capability runner panel).
- `OperationResult` as standard structured response.
- Event logging to `log/events.jsonl` — dashboard reads recent events.
- Pydantic models with `model_json_schema()` for JSON Schema generation.
- Workspace files as only source of truth — spikes operate on copies.

### Integration Points
- New `src/construct/ui/` — Streamlit app module.
- New `src/construct/ui/streamlit_app.py` — Main Streamlit app with 3 panels.
- New `src/construct/ui/dashboard.py` — Graph health dashboard panel.
- New `src/construct/ui/gate_review.py` — Gate review panel (ask.domain + bridge candidates).
- New `src/construct/ui/capability_runner.py` — Capability runner panel.
- New `src/construct/pipelines/spike_runner.py` — Spike isolation runner.
- New `src/construct/pipelines/tag_extraction.py` — Tag/keyword extraction pipeline.
- Updated `src/construct/views/` — Views data contracts (schemas, version, tests).
- Updated `CONSTRUCT-CLAUDE-impl/claude/skills/` — New spike SKILL.md procedures.

### What Does NOT Exist Yet
- `src/construct/ui/` directory (must be created).
- Streamlit dependency (needs `streamlit>=1.35` added).
- Views JSON Schema declarations.
- Spike runner framework.
- Tag extraction pipeline.

</code_context>

<specifics>
## Specific Ideas

- Streamlit app structure: sidebar with 3 tabs (Dashboard / Gate Review / Capability Runner)
- Dashboard tab shows: card counts by domain, connection counts by type, recent events timeline, workflow status
- Gate review tab shows: pending ask.domain Q&A results for review, bridge candidates for approve/reject
- Capability Runner tab shows: dropdown of capabilities, form inputs for selected capability, output display
- Spike runner: `cp -r workspace temp-workspace`, run tool, capture output to `log/spike-results/`, clean up temp
- Tag extraction: LLM extracts candidate tags from ref abstract/notes → dedup against existing search-seeds.json → write `log/tag-candidates.json`
- JSON Schema for each views file generated from Pydantic model via `model_json_schema()`
- Version field format: `semver` (major.minor.patch) in each data file's metadata block

</specifics>

<deferred>
## Deferred Ideas

- Full v0.4 browser UI — explicitly out of scope per PROJECT.md constraints. Streamlit is the spike; it informs but does not replace v0.4.
- Embedding-based retrieval for ask.domain — still deferred (keyword rank only).
- Full migration of all remaining skills to CLI/MCP — beyond the spike procedures scoped here.

</deferred>

---

*Phase: 06-derived-data-ops-ui-governed-spikes*
*Context gathered: 2026-06-11*
