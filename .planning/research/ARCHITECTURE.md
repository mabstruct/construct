# Architecture Research

**Domain:** v0.4 agent workflows for a local-first, agent-powered knowledge system  
**Project:** CONSTRUCT  
**Researched:** 2026-06-21  
**Confidence:** HIGH

## Executive Answer

v0.4 should integrate as a **Layer 2 workflow-runtime extension**, not as a new product surface and not as a workspace-format migration. The existing v0.3 spine is correct: Layer 0 skills define intent, Layer 1 workspace files remain canonical, Layer 2 Python owns deterministic work and bounded gates, and Layer 3 CLI/MCP expose the same capability registry. v0.4 adds model-agnostic search, research/curation workflows, durable human gates, and thin skill migrations inside that spine.

The central architectural move is: **skills stop doing search/scoring/orchestration; registered Python capabilities do it.** `construct-research-cycle` should become an adapter over `research.search`, `research.score`, and `research.run`; `construct-curation-cycle` should become an adapter over `curation.run`. The skills may still negotiate scope and present results, but they must not call Claude `WebSearch` / `WebFetch` or write SOT files directly.

The highest-risk integration point is human review. The current Streamlit gate review state is session-local, so it is not enough for CLI/MCP parity. v0.4 needs a durable, registry-backed gate queue represented in `WorkflowRunner` state (or a small support artifact under `log/`) and applied through the same Python write services used by CLI/MCP. Model gates produce proposals; approved proposals become validated SOT writes.

## Standard Architecture

### System Overview

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Layer 0 — Skill specs and workflows                                        │
│                                                                            │
│  construct-research-cycle     construct-curation-cycle      daily-cycle    │
│  Thin wrappers: classify intent → invoke CLI/MCP → present result          │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ CLI/MCP calls only
┌───────────────────────────────▼────────────────────────────────────────────┐
│ Layer 3 — Invoke surfaces                                                  │
│                                                                            │
│  Typer CLI groups         MCP stdio tools          Streamlit ops review     │
│  research / curation      auto from registry       calls registry, no SOT   │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ one capability contract
┌───────────────────────────────▼────────────────────────────────────────────┐
│ Capability registry                                                        │
│                                                                            │
│  research.search  research.score  research.run  curation.run  gate.review  │
│  input_model      output_model    handler       cli_name      mcp_tool     │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ validated Pydantic inputs
┌───────────────────────────────▼────────────────────────────────────────────┐
│ Layer 2 — v0.4 workflow runtime                                            │
│                                                                            │
│  Search spine        Workflow graphs       L2/L3 gates       Gate queue     │
│  providers + config  research/curation     LangGraph/LC      durable state  │
│                                                                            │
│  Deterministic services: validate, dedup, ingest, card edit, connection add │
└──────────────┬──────────────────────┬──────────────────────┬───────────────┘
               │                      │                      │
               │ search API           │ LLM provider API      │ validated writes
┌──────────────▼──────────────┐ ┌─────▼──────────────┐ ┌─────▼────────────────┐
│ Provider integrations        │ │ LLM provider       │ │ Layer 1 — Workspace  │
│ Tavily default, mock in CI   │ │ factory/config     │ │ SOT unchanged       │
│ Brave/arXiv slot later       │ │ Anthropic/etc.     │ │ cards refs seeds... │
└─────────────────────────────┘ └────────────────────┘ └──────────────────────┘
```

### Architecture Rules

1. **Workspace SOT does not change.** v0.4 may update existing canonical files (`cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`) through validated services, but must not introduce new required canonical files or alter existing schemas.
2. **The registry is the public contract.** Every new workflow entrypoint must be a `CapabilityRecord` with Pydantic input/output models and both CLI/MCP exposure unless deliberately internal.
3. **Search and LLM providers are factories, not graph code.** Graph nodes call provider interfaces; they do not import Tavily or `ChatAnthropic` directly except inside provider adapters.
4. **Gates propose; services write.** `research.score`, promotion evaluation, and connection typing produce structured proposals. Only a reviewed apply step calls `ingest_source`, `edit_card`, or `add_connection`.
5. **No v0.5 HTTP/browser UI in this milestone.** Streamlit can be kept as a local ops/review client over registry capabilities, but v0.4 should not design the HTTP API or browser-primary UI.

## Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Search provider spine** | Normalize web/academic search results and isolate provider-specific APIs | `src/construct/search/` with Pydantic models, config loader, `SearchProvider` protocol, `TavilySearchProvider`, `MockSearchProvider` |
| **Research query builder** | Turn `search-seeds.json`, domain config, and user scope into capped query batches | Plain Python helper in `src/construct/pipelines/research.py`; no LLM required for MVP |
| **Research deduper** | Remove known URLs/titles against `refs/*.json` and existing card titles | Plain Python over `WorkspaceLoader`; no new database in v0.4 |
| **Research score gate** | Score relevance, source tier, categories, and ingest action for normalized results | LangChain structured output or LangGraph gate in `src/construct/llm/research_score.py` |
| **Research run graph** | Compose config → query → search → dedup → score → review → ingest → digest → seed update | LangGraph for stateful flow, wrapped by registry handler returning `OperationResult` |
| **Curation PIPE steps** | Integrity, decay, orphan scan, report, optional views hook | Plain Python in `src/construct/pipelines/curation.py`, reusing validation/knowledge services |
| **Curation L3 gates** | Promotion and ambiguous connection decisions | `src/construct/llm/card_evaluate.py` and optional `connection_type.py` with structured outputs |
| **Gate queue / review applier** | Persist pending proposals and apply approved writes through services | Extend `WorkflowRunner` state with `awaiting_review` + `gate_queue`, plus `gate.list` / `gate.review` capabilities |
| **Capability registry** | Single contract for CLI, MCP, Streamlit, future UI | Modify `src/construct/capabilities/catalog.py`; no direct-import bypass for new workflow features |
| **CLI adapters** | Human/CI invocation of new capabilities | Add `research`, `curation`, and `gate` Typer groups in `src/construct/cli.py` |
| **MCP tools** | Agent invocation with same schemas as registry | Mostly automatic via `registry.list_mcp_tools()`; add tests and ensure serialization of new outputs |
| **Thin skills** | Preserve current Claude-native UX while delegating execution | Update `construct-research-cycle` and `construct-curation-cycle`; remove `WebSearch`/`WebFetch` from research allowed-tools |

## Recommended Project Structure

```text
src/construct/
├── search/
│   ├── __init__.py
│   ├── models.py              # SearchResult, SearchBatchOutput, Search config models
│   ├── config.py              # CONSTRUCT_SEARCH_CONFIG resolution + defaults
│   └── providers.py           # SearchProvider protocol, factory, Tavily/mock adapters
├── pipelines/
│   ├── research.py            # research.search/run orchestration, query builder, dedup, digest
│   ├── curation.py            # real curation steps and curation.run handler
│   ├── gate_queue.py          # durable pending proposals + approve/reject application
│   └── workflow_runner.py     # extend status/data for awaiting_review and gate queue
├── llm/
│   ├── config.py              # extend with reusable model factory, not just config loading
│   ├── providers.py           # optional: build chat model by provider key
│   ├── research_score.py      # L3 scoring/extraction gate
│   ├── card_evaluate.py       # promotion/decay gate
│   └── connection_type.py     # optional ambiguous relation gate
├── capabilities/
│   └── catalog.py             # register v0.4 capabilities and compatibility aliases
├── ui/
│   └── gate_review.py         # modify to call gate.list/gate.review, not session-only state
└── cli.py                     # research/curation/gate command groups

tests/
├── fixtures/search/
│   ├── tavily_search_response.json
│   └── mock_search_results.json
├── contract/
│   ├── test_research_contracts.py
│   ├── test_curation_contracts.py
│   └── test_gate_review_contracts.py
├── unit/
│   ├── test_search_provider.py
│   ├── test_research_pipeline.py
│   └── test_curation_pipeline.py
└── integration/
    ├── test_research_run_e2e.py
    └── test_curation_run_e2e.py
```

### Structure Rationale

- **`search/` is separate from `pipelines/`:** provider normalization is reusable and testable without a workspace. `research.run` consumes it but does not own provider details.
- **Workflow models should not live in canonical workspace schemas:** `src/construct/schemas/config.py` currently defines workspace file formats. Keep v0.4 runtime-only models in `search/models.py` or pipeline modules to avoid implying a workspace format migration.
- **`gate_queue.py` belongs in `pipelines/`:** review is a workflow/runtime concern; it should call `services.knowledge` and `pipelines.ingestion` for writes rather than becoming a new storage layer.
- **LLM gates stay in `llm/`:** this matches existing `ask_domain.py` and makes provider-factory cleanup explicit.

## New vs Modified Modules

### New Modules

| Path | Purpose | Build Notes |
|------|---------|-------------|
| `src/construct/search/models.py` | Provider-agnostic search and search-config models | Use `ConfigDict(extra="forbid")`; include JSON-serializable fields only |
| `src/construct/search/config.py` | Load repo-default search config with env override | Resolution: explicit CLI flag → `CONSTRUCT_SEARCH_CONFIG` → repo default |
| `src/construct/search/providers.py` | `SearchProvider` protocol, factory, Tavily/mock adapters | Keep Tavily SDK import inside Tavily adapter so tests do not require API keys |
| `src/construct/pipelines/research.py` | Handlers for `research.search` and `research.run` | Owns query building, dedup, digest, seed update, event logging |
| `src/construct/llm/research_score.py` | `research.score` L3 gate | Use structured output; mock model in tests |
| `src/construct/pipelines/curation.py` | Real `curation.run` implementation | Replaces placeholder `_get_workflow_steps("curation-cycle")` behavior |
| `src/construct/llm/card_evaluate.py` | Promotion/lifecycle gate | Implements `card.evaluate` output consumed by `curation.run` |
| `src/construct/pipelines/gate_queue.py` | Durable review queue and proposal applier | Required for CLI/MCP parity; Streamlit should call this via registry |

### Modified Modules

| Path | Required Change | Why |
|------|-----------------|-----|
| `src/construct/capabilities/catalog.py` | Register `research.search`, `research.score`, `research.run`, `curation.run`, `card.evaluate`, and `gate.*`; route `workflow.run curation-cycle` to `curation.run` for compatibility | Keeps registry canonical and eliminates curation no-op placeholders |
| `src/construct/cli.py` | Add `research`, `curation`, and `gate` Typer groups; ensure new commands call registry handlers | CLI remains CI/golden invoke path |
| `src/construct/mcp/server.py` | Verify serializer handles nested `OperationResult.data` for new Pydantic payloads | MCP must return JSON strings without dataclass/Pydantic leakage |
| `src/construct/pipelines/workflow_runner.py` | Add `awaiting_review`, `gate_queue`, `run_id`, and resume/apply semantics, or wrap LangGraph checkpointer behind same status contract | Existing state file is the natural v0.4 progress/review surface |
| `src/construct/llm/config.py` | Add model factory and gate entries for `research.score`, `card.evaluate`, connection gates | Acceptance requires LLM provider swap without graph rewrites |
| `src/construct/llm/ask_domain.py` | Gradually remove direct `ChatAnthropic` construction in favor of factory | Prevents new v0.4 gates from copying hardcoded provider pattern |
| `src/construct/pipelines/bridge_detect.py` | Later: route L3 model construction through the same provider factory | Not a blocker for search, but curation connection maintenance should not deepen hardcoded Anthropic coupling |
| `src/construct/ui/gate_review.py` | Replace session-only queue with registry-backed `gate.list` / `gate.review` calls | Human review must work equally from CLI, MCP, and Streamlit |
| `pyproject.toml` | Add Tavily SDK dependency only when implementing Tavily adapter | `tavily-python` is not currently listed |
| `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md` | Remove `WebSearch`, `WebFetch`, and inline extraction/orchestration; call `construct research ...` or MCP tools | Delivers model-agnostic research UX |
| `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md` | Replace step-by-step CLI prose with `curation.run`; keep escalation/reporting guidance | Avoids drift between skill text and Python pipeline |

## Capability Contracts

### Recommended New Capabilities

| Capability ID | CLI | MCP Tool | Role | Public? |
|---------------|-----|----------|------|---------|
| `research.search` | `construct research search` | `construct_research_search` | Provider-normalized search batch | Yes |
| `research.score` | `construct research score` | `construct_research_score` | L3 scoring/extraction gate over search results | Yes, for tests/debug |
| `research.run` | `construct research run` | `construct_research_run` | Full research workflow | Yes |
| `curation.run` | `construct curation run` | `construct_curation_run` | Full curation workflow | Yes |
| `card.evaluate` | `construct card evaluate` or `construct curation evaluate-card` | `construct_card_evaluate` | Promotion/lifecycle gate | Yes or semi-public |
| `gate.list` | `construct gate list` | `construct_gate_list` | List pending review items | Yes |
| `gate.review` | `construct gate review` | `construct_gate_review` | Approve/reject/edit pending proposals | Yes |
| `workflow.daily_cycle` | `construct workflow run daily-cycle` | `construct_workflow_daily_cycle` or existing `construct_workflow_run` | Compose research + curation after stable | Later v0.4 |

`research.score` can be marked operator-facing rather than user-facing, but it should still be invocable in tests because it is the contract boundary that makes `research.run` explainable and mockable.

### Search Models

```python
class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    snippet: str
    provider_score: float | None = None
    raw_content: str | None = None
    published_date: str | None = None
    source_domain: str
    query: str
    cluster_id: str | None = None
    provider: str


class SearchBatchOutput(BaseModel):
    query: str
    results: list[SearchResult]
    provider: str
    response_time_ms: float | None = None
    truncated: bool = False
```

Tavily maps cleanly into this shape: official Tavily Python docs show `title`, `url`, `content`, `score`, optional `raw_content`, `response_time`, and `query`. `content` should become `snippet`; `score` should become `provider_score`; `raw_content` is optional and should be requested only when enabled by caps.

### Research Contracts

| Model | Key Fields | Notes |
|-------|------------|-------|
| `ResearchSearchInput` | `workspace`, `query`, `domain_id`, `cluster_id`, `max_results`, `include_raw_content`, `provider_override`, `search_config` | Support explicit query and cluster-driven search; never require provider secrets in workspace files |
| `ResearchSearchOutput` | `batches`, `total_results`, `provider`, `truncated`, `degraded`, `errors` | Return partial/degraded results instead of failing whole workflow on one provider error |
| `ResearchScoreInput` | `workspace`, `domain_id`, `results`, `cluster_id`, `provider_override`, `max_findings` | Results are already normalized; gate does not call search provider |
| `ScoredFinding` | `search_result_url`, `relevance_score`, `source_tier`, `key_findings`, `content_categories`, `ingest_action`, `reasoning` | `ingest_action` is `skip`, `ref_only`, or `ref_and_card`; keep key findings capped |
| `ResearchRunInput` | `workspace`, `domain_id`, `cluster_id`, `query`, `max_queries`, `max_results`, `include_raw_content`, `review_mode`, `dry_run`, `provider_override` | Default `review_mode="required"`; no ingest before approval |
| `ResearchRunOutput` | `run_id`, `status`, `search_counts`, `score_counts`, `gate_queue`, `ingest_results`, `digest_path`, `events` | `status="awaiting_review"` is a successful paused state, not an error |

### Curation Contracts

| Model | Key Fields | Notes |
|-------|------------|-------|
| `CurationRunInput` | `workspace`, `mode`, `include_llm`, `review_mode`, `refresh_views`, `max_gate_items` | `mode` can be `full`, `pipe-only`, or scoped for tests |
| `CurationStepResult` | `step`, `success`, `counts`, `findings`, `proposals`, `errors` | Every step returns a real result; no placeholder success strings |
| `PromotionDecision` | `card_id`, `decision`, `target_lifecycle`, `reasoning`, `method` | `method` distinguishes rule-based vs LLM judgment |
| `CurationRunOutput` | `run_id`, `status`, `step_results`, `gate_queue`, `actions_applied`, `report` | Report compiles graph health and attention-needed items |

### Human Review Contracts

```python
class GateQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    gate_id: str
    tier: Literal["L2", "L3"]
    status: Literal["pending", "approved", "rejected", "applied"]
    summary: str
    rationale: str | None = None
    proposed_actions: list[dict]
    created_at: str


class GateReviewInput(BaseModel):
    workspace: Path
    gate_item_id: str
    decision: Literal["approve", "reject"]
    edited_actions: list[dict] | None = None
    reviewer: str = "human"
```

`proposed_actions` should be explicit and low-level enough to apply through existing services, e.g. `ingest_source`, `edit_card`, `add_connection`, `archive_card`. The applier should validate each proposed write and emit `gate_review_approved` / `gate_review_rejected` plus the underlying write event.

## Data Flow

### Research Search Flow

```text
CLI/MCP/skill
  → research.search capability
  → validate ResearchSearchInput
  → load search config (explicit → env → repo default)
  → SearchProviderFactory(provider)
  → provider.search(query, caps)
  → normalize to SearchResult / SearchBatchOutput
  → optional research_search_complete event
  → OperationResult(data=ResearchSearchOutput)
```

**Writes:** none except optional event logging.  
**SOT impact:** none.

### Research Score Flow

```text
ResearchSearchOutput or explicit SearchResult list
  → research.score capability
  → load domains.yaml + governance.yaml thresholds
  → build scoring prompt/context from normalized result + domain config
  → L3 structured output gate
  → validate ResearchScoreGateOutput
  → OperationResult(data=scored findings, review_required=true)
```

**Writes:** none.  
**SOT impact:** none until a later reviewed ingest.

### Research Run Flow

```text
research.run
  → load workspace config: search-seeds.json, domains.yaml, governance.yaml
  → build capped queries from active clusters / user scope
  → execute search via provider spine
  → dedup against refs/*.json URLs and existing card titles
  → research.score L3 gate
  → persist gate_queue with proposed ingest actions
  → return status=awaiting_review

gate.review approve
  → apply approved actions through ingest_source(...metadata...)
  → write refs/cards via existing pre-write validation
  → update search-seeds.json last_queried with validate_search_seeds_write
  → write deterministic digest under digests/{domain}/
  → append research_cycle_complete
```

**Writes before review:** workflow/gate support state and events only.  
**Writes after approval:** existing SOT files through existing services.

### Curation Run Flow

```text
curation.run
  → integrity_check: validate_workspace
  → decay_scan: load cards + governance; propose archive/flag actions
  → orphan_scan: connection counts; propose attention items
  → promotion_review: rule candidates + card.evaluate L3 for ambiguous cases
  → connection_maintenance: bridge.detect + optional relation proposals
  → persist gate_queue for lifecycle/connection changes needing review
  → process approved actions through knowledge services
  → compile report from graph.status + step results
  → append curation_cycle_complete
  → optional views.generate_data hook (non-blocking, no dependency on v0.5)
```

**Important correction:** Valid `connections.json` requires a typed `ConnectionType`; “untyped edge” cleanup is therefore a legacy/invalid-data path, not the normal v0.4 connection-maintenance path. Normal connection maintenance should propose new/changed typed connections or bridge candidates.

### Daily Cycle Composition Flow

```text
workflow.daily_cycle or workflow.run daily-cycle
  → check due state from search-seeds.json + events.jsonl
  → call research.run if due/requested
  → wait/apply research gate review as needed
  → call curation.run
  → wait/apply curation gate review as needed
  → graph.status report
  → optional single views refresh hook
```

Build this only after `research.run` and `curation.run` are stable; otherwise daily cycle just composes unstable parts and multiplies debugging cost.

## Architectural Patterns

### Pattern 1: Registry-First Workflow Entrypoints

**What:** New workflows are normal registry capabilities. CLI and MCP are adapters, not separate implementations.

**When to use:** All v0.4 entrypoints and review actions.

**Trade-offs:** Requires more schema work up front, but prevents the RT-03 class of handler/schema drift already seen in v0.3.

**Example:**

```python
registry.register(CapabilityRecord(
    id="research.search",
    name="Research Search",
    description="Run provider-normalized search for a workspace/domain scope",
    input_model=ResearchSearchInput,
    output_model=ResearchSearchOutput,
    handler=research_search,
    cli_name="research.search",
    mcp_tool_name="construct_research_search",
))
```

### Pattern 2: Provider Interface + Factory

**What:** Search and LLM provider choices are loaded from config and instantiated by factories. Workflow graph nodes call a protocol, not vendor SDKs.

**When to use:** Search providers and all L2/L3 gates.

**Trade-offs:** Slight indirection; major gains in mockability and provider swap.

**Example:**

```python
class SearchProvider(Protocol):
    def search(
        self,
        query: str,
        *,
        max_results: int,
        cluster_id: str | None = None,
        include_raw_content: bool = False,
    ) -> SearchBatchOutput: ...
```

### Pattern 3: Gate-as-Proposal, Not Gate-as-Write

**What:** L3 outputs are queued proposals containing exact intended actions. Approval applies those actions through deterministic services.

**When to use:** Research ingest, card promotion/archive, connection creation, ambiguous bridge approval.

**Trade-offs:** Adds a review/apply step; avoids silent SOT corruption and makes CLI/MCP parity possible.

### Pattern 4: WorkflowRunner as CONSTRUCT Envelope, LangGraph as Workflow/Gate Engine

**What:** Keep `WorkflowRunner` as the stable CONSTRUCT progress/status/review-state envelope. Use LangGraph for stateful research/curation graphs where branching, pauses, and resume matter. Do not create a second user-facing workflow state API.

**When to use:** `research.run`, `curation.run`, and daily-cycle composition.

**Trade-offs:** Requires adapter glue between LangGraph state and `workflow-state.json`. This is still better than making CLI/MCP/Streamlit understand multiple state systems. LangGraph docs verify support for checkpointers, durable execution, and human-in-the-loop interrupts; use those features behind the existing CONSTRUCT status contract when needed.

### Pattern 5: Atomic, Validated SOT Writes

**What:** Every canonical file write passes the existing validation layer or a new equivalent helper, then writes atomically where possible.

**When to use:** Updating refs/cards/connections/search-seeds after gate approval.

**Trade-offs:** More helper code for `search-seeds.json` updates; prevents half-written canonical state.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Tavily Search API** | `TavilySearchProvider` behind `SearchProvider` protocol | Default general web provider; map `content` → `snippet`, `score` → `provider_score`; request `raw_content="markdown"` only when configured |
| **Mock search provider** | Same protocol, fixture-backed | Required for CI and contract tests; must be provider-swappable without graph code changes |
| **LangChain structured output** | Pydantic/JSON Schema response models via provider factory | Verified current docs support Pydantic and JSON Schema structured output |
| **LangGraph** | `StateGraph` workflows/gates, checkpoint/interrupt support behind CONSTRUCT runner state | Use where state, branching, human review, or resume matters; plain Python for deterministic steps |
| **Anthropic/OpenAI/Ollama/etc.** | LLM provider config/factory | Existing `llm/config.py` loads config but v0.4 should centralize model construction to avoid hardcoded imports |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Skill → CLI/MCP | Named command/tool invocation | Skills should not call search providers, LLM SDKs, `WebSearch`, `WebFetch`, or direct file writes |
| CLI/MCP → Registry | `CapabilityRecord` schemas and handlers | MCP tools auto-register; CLI is hand-wired today, so add parity tests for new CLI groups |
| Registry → Pipeline | Pydantic input models, `OperationResult` outputs | Keep `OperationResult.data` JSON-serializable; avoid raw Pydantic/dataclass objects that break MCP JSON dumps |
| Pipeline → Search provider | `SearchProvider` protocol | Search provider never writes workspace state |
| Pipeline → LLM gate | Gate input/output Pydantic models | Gates can read context but should not apply writes |
| Gate queue → Services | Proposed actions translated to `ingest_source`, `edit_card`, `add_connection`, `archive_card` | This is the only approved-write path for model-generated actions |
| Pipeline → Workspace SOT | Existing loader/validation/write services | No new canonical schema required |
| Streamlit gate review → Registry | `gate.list` / `gate.review` capabilities | Streamlit remains an ops client, not a state owner |

## Anti-Patterns

### Anti-Pattern 1: Direct Provider Calls from Skills

**What people do:** Keep `WebSearch`/`WebFetch` in `construct-research-cycle` and only add Python helpers around ingest.

**Why it's wrong:** Research remains Claude-locked, untestable, and unavailable to other MCP clients.

**Do this instead:** Remove search tools from the research skill and call `research.run` / `research.search` via CLI or MCP.

### Anti-Pattern 2: Session-Only Human Review

**What people do:** Put pending approvals only in Streamlit `st.session_state` or chat memory.

**Why it's wrong:** CLI/MCP cannot resume or approve; process restart loses review state; no audit trail.

**Do this instead:** Persist gate items in workflow state/support artifacts and expose `gate.list` / `gate.review` through registry.

### Anti-Pattern 3: LLM Writes Canonical Files

**What people do:** Let `research.score` or `card.evaluate` directly create cards, promote lifecycles, or add connections.

**Why it's wrong:** Bypasses human review and deterministic validation; makes failures hard to roll back.

**Do this instead:** Gates return proposals; approved proposals call existing services.

### Anti-Pattern 4: Workspace Config Creep

**What people do:** Add `.construct/search.yaml` or provider secrets to each workspace as part of v0.4 MVP.

**Why it's wrong:** Violates the “workspace format must not change” constraint and mixes secrets with portable knowledge state.

**Do this instead:** Use repo default `src/construct/search/config.yaml`, env override, and explicit CLI flag. Keep workspace `governance.yaml`/`search-seeds.json` as domain/cycle policy only.

### Anti-Pattern 5: Live Network/LLM Contract Tests

**What people do:** Test Tavily and LLM gates against real APIs in CI.

**Why it's wrong:** Flaky, costly, and not reproducible.

**Do this instead:** Mock provider factories and keep a small number of manual smoke checks outside the contract suite.

### Anti-Pattern 6: Treating `workflow.run` Placeholders as Compatibility

**What people do:** Leave `_get_workflow_steps("curation-cycle")` placeholder success handlers and add `curation.run` separately.

**Why it's wrong:** Users and skills can still run a fake curation cycle.

**Do this instead:** Route `workflow.run curation-cycle` to real `curation.run` or remove the old path after migration.

## Build Order

### Phase 1 — Search Provider Spine + Contract Foundation

**Deliver:** `src/construct/search/`, `SearchResult`, `SearchBatchOutput`, search config loader, mock provider, Tavily adapter, `research.search` registry/CLI/MCP, provider fixture tests.

**Depends on:** v0.3 registry and test fixtures.

**Why first:** It removes Claude WebSearch coupling in the smallest possible slice and establishes the mock-provider pattern that every later workflow needs.

**Do not include yet:** scoring, ingest, skill migration.

### Phase 2 — LLM Provider Factory + `research.score`

**Deliver:** LLM model factory, `ResearchScoreInput/Output`, `ScoredFinding`, LangChain structured output gate, mocked LLM tests, governance-threshold consumption.

**Depends on:** Phase 1 normalized results.

**Why second:** Scoring is the boundary between search and ingest. Proving it independently prevents `research.run` from becoming an opaque mega-feature.

### Phase 3 — Durable Human Review + `research.run`

**Deliver:** gate queue state, `gate.list`, `gate.review`, research graph/workflow, approval-applied ingest, digest generation, `search-seeds.json` timestamp update, research events, research skill migration removing `WebSearch`/`WebFetch`.

**Depends on:** Phases 1–2.

**Why third:** Research is the highest user-visible win and validates the full pattern: provider → L3 gate → human review → governed write.

### Phase 4 — Curation PIPE Steps

**Deliver:** `curation.run` with real integrity, decay, orphan, report, optional views hook; compatibility route from `workflow.run curation-cycle`; no placeholder messages.

**Depends on:** existing validation, graph_status, knowledge services.

**Why fourth:** This closes v0.3 curation no-op debt without waiting for every L3 gate. It also gives daily-cycle a real maintenance core.

### Phase 5 — Curation L3 Gates + Review Application

**Deliver:** `card.evaluate`, promotion decisions, connection/bridge proposal review, approved lifecycle/connection writes through services, curation skill migration.

**Depends on:** Phase 3 gate queue and Phase 4 curation steps.

**Why fifth:** Promotion and connection changes are riskier SOT writes; they should reuse the already-proven review infrastructure.

### Phase 6 — Daily Cycle Composition

**Deliver:** daily-cycle orchestration that composes `research.run`, `curation.run`, `graph.status`, and one optional views-refresh hook; resume/status tests; docs.

**Depends on:** stable research and curation workflows.

**Why last:** Daily cycle should compose reliable subgraphs, not hide unfinished research/curation behavior.

## Contract-Test Strategy

| Area | Tests to Add | Must Prove |
|------|--------------|------------|
| Search models | Unit tests for `SearchResult`, `SearchBatchOutput`, config loading | Extra fields rejected; env/default resolution works |
| Tavily adapter | Fixture mapping test with recorded Tavily JSON | `content`/`score`/`raw_content` normalize correctly; no network in CI |
| Mock provider | Unit and contract tests | Provider swap works without graph code changes |
| Registry | Capability list/schema tests | New capabilities have expected IDs, CLI names, MCP names, input JSON schemas |
| CLI | Typer `CliRunner` tests on copied `test-ws/my-construct` | `construct research search`, `research score`, `research run --dry-run`, `curation run --pipe-only`, `gate list/review` execute and return JSON |
| MCP | Extend RT-03 handler-invocation test | Every new MCP tool accepts its advertised kwargs without `TypeError` |
| Research score | Mock LLM structured-output tests | Scores validated 0–1, categories kebab-case/known, ingest actions valid, low relevance skipped |
| Research run pre-review | Integration test with mock search + mock LLM | Produces `awaiting_review`; no refs/cards created before approval |
| Research approval | Integration test applying one approved finding | Ref/card created through `ingest_source`, `search-seeds.json` updated, validation passes, events emitted |
| Curation PIPE | Unit tests per step | Integrity calls real `validate_workspace`; decay/orphan/report produce real counts; no placeholder strings |
| Curation gates | Mock LLM tests | Promotion proposals do not write until approved; reject path writes no SOT changes |
| Workflow state | Unit tests extending `test_workflow_runner.py` | `awaiting_review`, `gate_queue`, resume/apply behavior persists across process restart |
| Skill migration | Static tests or grep-like assertions in Python | Research skill allowed-tools exclude `WebSearch`/`WebFetch`; curation skill invokes `curation.run` |
| Workspace compatibility | Existing validation/integration tests plus v0.4 runs | Workspace canonical schemas unchanged; `construct validate` passes after workflows |

**Test rule:** New tests must use copied fixtures under `tmp_path`, never mutate `test-ws/` directly.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single local workspace / current v0.4 | File scans over cards/refs are fine; use query/result caps and mocked providers in tests |
| Large personal workspace | Add in-memory indexes per run, cap L3 candidates, store raw content only transiently or in refs when approved |
| Future multi-workspace/UI era | Introduce HTTP and optional indexing in v0.5+ only after v0.4 contracts prove stable |

### Scaling Priorities

1. **First bottleneck:** search/LLM cost and rate limits. Fix with `max_queries`, `max_results`, `max_papers_per_cycle`, raw-content caps, and degraded partial results.
2. **Second bottleneck:** O(N²) curation/bridge scans. Fix with candidate prefilters and `max_gate_items` before L3 calls.
3. **Do not optimize first:** SQLite/FTS/cloud workers. Those are out of scope for v0.4 and would violate the focused workflow migration.

## Roadmap Implications

- Start with **search provider + contracts**, not full `research.run`, because normalized search is the prerequisite for every downstream research feature.
- Implement **human review before curation L3 gates**, because curation writes affect existing mature knowledge and need the same approved-action path as research ingest.
- Keep **thin skill migration tied to capability readiness**: migrate research only after `research.run` is usable; migrate curation only after `curation.run` is real.
- Defer **daily-cycle composition** until both research and curation return stable `OperationResult` payloads and resumable workflow state.
- Explicitly defer **v0.5 HTTP/browser UI**, RT-01/RT-02 registry cleanup for unrelated views/spike/tag commands, full `views.generate_data` emission, SQLite indexing, and cloud deployment unless they directly block v0.4 workflow tests.

## Open Questions / Phase Research Flags

| Topic | Recommendation Now | Needs Phase Research? |
|-------|--------------------|-----------------------|
| LangGraph checkpointer vs `WorkflowRunner` only | Use `WorkflowRunner` as outer status/review envelope; use LangGraph where state/interrupts matter | MEDIUM — Phase 3 should spike minimal adapter |
| Academic search provider | Tavily-only MVP plus mock provider | LOW — add arXiv/Semantic Scholar later if Tavily metadata is insufficient |
| CLI review UX | Non-interactive JSON first (`gate list --json`, `gate review --decision approve`) | MEDIUM — choose exact flags in Phase 3 PRD |
| Workspace-level search config | Do not add in v0.4 | LOW — revisit only if users need per-workspace providers |
| Digest generation | Deterministic template first; L2 narrative optional later | LOW — avoids another review path in first research run |

## Sources

- Repo: `.planning/PROJECT.md` — v0.4 milestone goals, constraints, current state.
- Repo: `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — target workflows, data structures, capabilities, risks, phased next steps.
- Repo: `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — accepted layer model, CLI/MCP parity, LLM tiers, v0.4/v0.5 sequencing.
- Repo: `.planning/ROADMAP.md` — milestone sequencing and carry-over debt.
- Repo: `src/construct/capabilities/catalog.py` — current registry and curation placeholder steps.
- Repo: `src/construct/pipelines/workflow_runner.py` — current state persistence/resume behavior.
- Repo: `src/construct/llm/ask_domain.py` — existing LangGraph L2 gate and structured output pattern.
- Repo: `src/construct/ui/gate_review.py` — current Streamlit review pattern and session-state limitation.
- Repo: `src/construct/pipelines/ingestion.py`, `services/knowledge.py`, `services/validation.py` — governed write paths to reuse.
- Context7 docs: LangGraph `/langchain-ai/langgraph` — StateGraph, durable execution, checkpointers, human-in-the-loop interrupts.
- Context7 docs: LangChain `/websites/langchain_oss_python_langchain` — structured output with Pydantic/JSON Schema.
- Context7 docs: Tavily Python `/tavily-ai/tavily-python` — `TavilyClient.search()` response fields and `include_raw_content`.

---
*Architecture research for: CONSTRUCT v0.4 Agent Workflows*  
*Researched: 2026-06-21*
