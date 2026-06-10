# Phase 5: Grounded Synthesis & Graph Reasoning - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Add bounded LLM judgment to the Python layer — grounded Q&A with citations, deterministic bridge detection with LLM-assisted semantic assessment, and confidence-aware outputs. Users can ask domain questions, detect cross-domain bridges systematically, and produce synthesis outputs tied to the graph knowledge base.

**Requirements:** ING-06, ADV-01, ADV-02

</domain>

<decisions>
## Implementation Decisions

### L2 Gate Scope (ADV-01)
- **D-01:** `ask.domain` is a **LangGraph L2 gate** for grounded Q&A with citations. It handles bounded domain questions — not document drafting. Read-only in Phase 5 (no SOT writes).
- **D-02:** `synthesis` stays as a **Claude-native skill** — not migrated to Python in Phase 5. The synthesis skill is updated to call CLI commands and demonstrate confidence propagation in output, but drafting remains Claude's native capability.

### Bridge Detection Model (ADV-02)
- **D-03:** Bridge detection is a **full multi-level Python pipeline** (L1 → L2 → L3) producing `bridges.json`.
  - **L1 — Structural:** Deterministic scan of `connections.json` for cross-domain edges.
  - **L2 — Category Overlap:** Deterministic scan of card `content_categories` across domains.
  - **L3 — Semantic Similarity:** Bounded LLM call(s) within the pipeline to assess whether content suggests genuine parallels.
- **D-04:** The pipeline is registrable as `bridge.detect` capability — callable via CLI and MCP.

### Confidence Propagation (ING-06)
- **D-05:** Both aggregate and per-citation confidence:
  - **Overall aggregate** (min/mean/weighted) in output metadata.
  - **Per-citation source confidence** in structured citations for `ask.domain` output.
  - Synthesis skill output demonstrates inline confidence annotation and structured metadata.

### Phase 5 Deliverables
- **D-06:** Five concrete deliverables:
  1. `ask.domain` LangGraph L2 gate at `src/construct/llm/ask_domain.py`
  2. `bridge.detect` multi-level Python pipeline at `src/construct/pipelines/bridge_detect.py`
  3. `bridge.detect` capability registered in `src/construct/capabilities/catalog.py`
  4. `views/build/data/bridges.json` derived data file per existing spec contract
  5. Updated `construct-synthesis` SKILL.md — calls CLI commands, demonstrates confidence propagation

### Dependencies
- **D-07:** Phase 5 adds `langgraph>=0.2`, `langchain-core>=0.3`, `langchain-anthropic>=0.3` to `pyproject.toml` dependencies. These are NOT currently installed.

### the Agent's Discretion
- Exact LangGraph graph structure for `ask.domain` (state, nodes, edges) within the PRD-specified input/output contract.
- L3 semantic similarity approach for bridge detection (embedding comparison vs LLM classification vs hybrid).
- `bridges.json` schema details (must align with existing `spec-v02-cross-domain-data.md` contract).
- CLI command structure for `construct bridge detect` and `construct ask`.
- Which LLM tier to use for L3 bridge assessment vs L2 Q&A.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 5 goal, success criteria (ING-06, ADV-01, ADV-02), dependency on Phase 4.
- `.planning/REQUIREMENTS.md` — Full requirement descriptions for ING-06, ADV-01, ADV-02.
- `.planning/PROJECT.md` — Product continuity, sequencing constraints.
- `.planning/STATE.md` — Current progress, prior phase decisions.
- `.planning/phases/04-guided-workflow-operability/04-CONTEXT.md` — Prior decisions, especially deferred LangGraph L2 topic and help/ingestion/wiring patterns.

### Architecture and pipeline specs (MUST read for ask.domain)
- `CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md` — Full LangGraph L2 gate contract: `ask.domain` input/output JSON schemas (lines 586–670), provider config (lines 870–905), test strategy (lines 1070–1080), and tranche scope boundaries (lines 1115–1135).
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Four-layer architecture, L2 gate role, invoke surface model.

### Bridge detection specs
- `CONSTRUCT-CLAUDE-spec/spec-v02-cross-domain-data.md` — `bridges.json` schema contract, scoring model, visibility rules. Binding for derived data output.
- `CONSTRUCT-CLAUDE-spec/spec-v02-cross-domain-graph.md` — Bridge graph contract, bridges-first exploration mode.
- `CONSTRUCT-CLAUDE-spec/prd-v02-cross-domain-cluster.md` — Cross-domain feature PRD, bridge discovery UX intent.

### Existing skill implementations
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-bridge-detect/SKILL.md` — Current Claude-native bridge detection procedure (L1/L2/L3 levels are defined here).
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md` — Current Claude-native synthesis skill — will be updated to call CLI commands.

### Existing code patterns
- `src/construct/capabilities/registry.py` — CapabilityRegistry pattern for registering new capabilities.
- `src/construct/capabilities/catalog.py` — Pre-registered capabilities — extend for `ask.domain` and `bridge.detect`.
- `src/construct/pipelines/graph_status.py` — Existing PIPE handler pattern for deterministic capabilities.
- `src/construct/services/knowledge.py` — Core knowledge operations (card CRUD, connection CRUD, source routing).
- `src/construct/cli.py` — CLI with Typer command group pattern — extend for `ask` and `bridge` groups.
- `src/construct/schemas/config.py` — Provider config model, routing tasks enum including `synthesis_drafting` and `cross_domain_ideation`.
- `pyproject.toml` — Current dependency set (no langgraph yet — must be added).
- `CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md` — Tranche 1 scope, `ask.domain` L2 gate mapping.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/capabilities/registry.py` — Direct callable handler dispatch pattern. New capabilities follow the same registration pattern.
- `src/construct/pipelines/graph_status.py` — Pattern for deterministic PIPE handlers that read workspace state and return structured `OperationResult`.
- `src/construct/services/knowledge.py` — `route_source_to_domain()`, card reading operations — reusable for bridge detection.
- `src/construct/cli.py` — Typer app with `add_typer()` for command groups. Pattern for `construct ask` and `construct bridge` groups.
- `src/construct/schemas/config.py` — `RoutingTask.synthesis_drafting` and `RoutingTask.cross_domain_ideation` already in the task enum — can be used for LLM tier routing.

### Established Patterns
- Capabilities registered in `catalog.py` with `CapabilityRecord(id, handler, input_model, output_model, cli_command, mcp_tool)`.
- CLI commands delegate to `registry.get("id").handler(...)`.
- `OperationResult` is the standard structured response type (success + message + errors + data).
- Event logging append-only to `log/events.jsonl`.
- Provider routing via `model-routing.yaml` with frontier/workhorse/lightweight tiers.

### Integration Points
- New `src/construct/llm/` directory — L2 LangGraph gate modules.
- New `src/construct/llm/__init__.py` — package init.
- New `src/construct/llm/ask_domain.py` — LangGraph graph definition + runner.
- New `src/construct/llm/config.py` — LLM provider config loading.
- New `src/construct/pipelines/bridge_detect.py` — multi-level bridge detection pipeline.
- `src/construct/capabilities/catalog.py` — register `ask.domain` and `bridge.detect`.
- `src/construct/cli.py` — add `construct ask` and `construct bridge` command groups.
- `src/construct/mcp/server.py` — auto-register MCP tools for new capabilities.
- `pyproject.toml` — add `langgraph>=0.2`, `langchain-core>=0.3`, `langchain-anthropic>=0.3`.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md` — update to call CLI commands.

### What Does NOT Exist Yet
- `src/construct/llm/` directory (must be created).
- `langgraph` / `langchain-core` / `langchain-anthropic` packages (not installed, not in pyproject.toml).
- Any existing LLM calling code in `src/construct/` (no LangChain/LangGraph usage today).
- Provider config at `src/construct/llm/config.yaml` (specced in PRD but not created).

</code_context>

<specifics>
## Specific Ideas

- `ask.domain` input follows the PRD contract: workspace_path + domain_id + question + max_cards + optional provider_override.
- Output includes answer (text), citations (array of card_id + title + snippet + confidence), gate metadata, and overall confidence score.
- Bridge detection pipeline: L1 (structural edges) → L2 (category overlap across domains) → L3 (LLM semantic assessment). L1 and L2 are fast deterministic checks; L3 fires only for promising L1/L2 candidates.
- `bridges.json` follows the spec-v02-cross-domain-data.md contract with confirmed bridges + strong candidates.
- The synthesis skill update demonstrates how to call `construct knowledge card` / `construct ask` CLI commands, and shows confidence annotation in draft output.

</specifics>

<deferred>
## Deferred Ideas

- Full synthesis capability migration to Python — stayed Claude-native per D-02. Revisit if ask.domain Q&A patterns prove reusable for drafting.
- Streamlit ops UI / gate review panel — Phase 6.
- Embedding-based retrieval for ask.domain (keyword rank only in Phase 5 per PRD tranche 1 scope).
- Full migration of remaining skills to CLI/MCP — beyond the synthesis skill update scoped here.

</deferred>

---

*Phase: 05-grounded-synthesis-graph-reasoning*
*Context gathered: 2026-06-10*
