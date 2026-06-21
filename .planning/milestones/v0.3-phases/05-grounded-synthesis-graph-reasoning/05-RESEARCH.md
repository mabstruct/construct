# Phase 5: Grounded Synthesis & Graph Reasoning - Research

**Researched:** 2026-06-11
**Domain:** LangGraph L2 gate, bridge detection pipeline, capability registry extension
**Confidence:** HIGH

## Summary

Phase 5 delivers two new bounded-LLM capabilities to the CONSTRUCT Python layer: `ask.domain` (LangGraph L2 gate for grounded Q&A with citations) and `bridge.detect` (multi-level deterministic + LLM pipeline producing `bridges.json`). Both follow the existing capability registry pattern (`CapabilityRecord` → `catalog.py` registration → CLI/MCP auto-exposure). The LLM infrastructure requires three new dependencies (`langgraph`, `langchain-core`, `langchain-anthropic`), a new `src/construct/llm/` package with provider config, and integration with the existing `model-routing.yaml` tier system.

**Primary recommendation:** Implement `ask.domain` as a pure `StateGraph` with 6 sequential Python nodes (no conditional branching), using `ChatAnthropic.with_structured_output(method="json_schema")` for LLM synthesis. Implement `bridge.detect` as a single deterministic pipeline function invoking `l1_structural -> l2_category -> l3_semantic` sub-steps with the scoring model defined in spec-v02-cross-domain-data.md.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `ask.domain` is a **LangGraph L2 gate** for grounded Q&A with citations. It handles bounded domain questions — not document drafting. Read-only in Phase 5 (no SOT writes).
- **D-02:** `synthesis` stays as a **Claude-native skill** — not migrated to Python in Phase 5. The synthesis skill is updated to call CLI commands and demonstrate confidence propagation in output, but drafting remains Claude's native capability.
- **D-03:** Bridge detection is a **full multi-level Python pipeline** (L1 → L2 → L3) producing `bridges.json`.
  - **L1 — Structural:** Deterministic scan of `connections.json` for cross-domain edges.
  - **L2 — Category Overlap:** Deterministic scan of card `content_categories` across domains.
  - **L3 — Semantic Similarity:** Bounded LLM call(s) within the pipeline to assess whether content suggests genuine parallels.
- **D-04:** The pipeline is registrable as `bridge.detect` capability — callable via CLI and MCP.
- **D-05:** Both aggregate and per-citation confidence:
  - **Overall aggregate** (min/mean/weighted) in output metadata.
  - **Per-citation source confidence** in structured citations for `ask.domain` output.
  - Synthesis skill output demonstrates inline confidence annotation and structured metadata.
- **D-06:** Five concrete deliverables:
  1. `ask.domain` LangGraph L2 gate at `src/construct/llm/ask_domain.py`
  2. `bridge.detect` multi-level Python pipeline at `src/construct/pipelines/bridge_detect.py`
  3. `bridge.detect` capability registered in `src/construct/capabilities/catalog.py`
  4. `views/build/data/bridges.json` derived data file per existing spec contract
  5. Updated `construct-synthesis` SKILL.md — calls CLI commands, demonstrates confidence propagation
- **D-07:** Phase 5 adds `langgraph>=0.2`, `langchain-core>=0.3`, `langchain-anthropic>=0.3` to `pyproject.toml` dependencies.

### the Agent's Discretion
- Exact LangGraph graph structure for `ask.domain` (state, nodes, edges) within the PRD-specified input/output contract.
- L3 semantic similarity approach for bridge detection (embedding comparison vs LLM classification vs hybrid).
- `bridges.json` schema details (must align with existing `spec-v02-cross-domain-data.md` contract).
- CLI command structure for `construct bridge detect` and `construct ask`.
- Which LLM tier to use for L3 bridge assessment vs L2 Q&A.

### Deferred Ideas (OUT OF SCOPE)
- Full synthesis capability migration to Python — stayed Claude-native per D-02.
- Streamlit ops UI / gate review panel — Phase 6.
- Embedding-based retrieval for ask.domain (keyword rank only in Phase 5 per PRD tranche 1 scope).
- Full migration of remaining skills to CLI/MCP — beyond the synthesis skill update scoped here.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ING-06 | Confidence propagation across synthesis outputs | `ask.domain` output schema includes per-citation `confidence` (1-5, from card frontmatter) + aggregate in gate metadata. Synthesis skill update demonstrates inline confidence annotation. |
| ADV-01 | LangGraph L2 gate for grounded Q&A | `ask.domain` implemented as `StateGraph` with `ChatAnthropic.with_structured_output()`. Six nodes: load → filter → rank → build_context → llm_synthesize → extract_citations. |
| ADV-02 | Cross-domain bridge detection | Three-level pipeline: L1 structural (connections.json edges), L2 category overlap (shared content_categories), L3 semantic (LLM assessment). Scoring model from spec-v02-cross-domain-data.md. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `ask.domain` — Card loading/filtering | API / Backend | — | Python workspace loader reads cards from filesystem; no browser or SSR involvement |
| `ask.domain` — LLM synthesis | API / Backend | LLM provider (API) | LangGraph runs in Python; LLM call goes to Anthropic API via LangChain |
| `bridge.detect` — L1/L2 deterministic | API / Backend | — | Pure Python operations on workspace files |
| `bridge.detect` — L3 semantic | API / Backend | LLM provider (API) | Deterministic pipeline invokes bounded LLM call for candidate assessment |
| `bridges.json` generation | API / Backend | Derived data | Generated by bridge detection pipeline; consumed by SPA views layer |
| Synthesis skill CLI updates | Claude-native | — | SKILL.md updated to call `construct knowledge card` / `construct ask` |


## Standard Stack

### Core

| Library | Version [VERIFIED] | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| `langgraph` | `>=0.2` (latest stable: 0.4.x) | StateGraph for L2 gate. Defines state schema, nodes, edges, compilation. | LangChain's official graph framework for multi-step LLM workflows with state management. |
| `langchain-core` | `>=0.3` (latest stable: 0.3.x) | Base abstractions: BaseMessage, SystemMessage, HumanMessage, with_structured_output(), Runnable interface. | Core dependency for langgraph + langchain-anthropic integration. Provides message types and structured output. |
| `langchain-anthropic` | `>=0.3` (latest stable: 0.3.x) — note: `>=1.1.0` needed for `method="json_schema"` | ChatAnthropic LLM wrapper with native Claude structured output support. | Default Anthropic provider; integrates directly with LangGraph nodes. `with_structured_output(method="json_schema")` for deterministic routing output (no tool-choice conflicts). [VERIFIED: langchain docs] |
| `pydantic` | `>=2.7` (existing: 2.13.3) | Graph state schema, structured LLM output schema, input/output validation models. | Already in project. All capability input/output models use Pydantic v2. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ruamel.yaml` | `>=0.18` (existing) | YAML config loading for `src/construct/llm/config.yaml` provider config. | Already in project for governance/model-routing YAML. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph (`StateGraph`) | Manual `if/else` chain | LangGraph provides state management, streaming, checkpointing, and a standard pattern. Manual chain works but lacks observability and extensibility for future features (gate review, checkpointing). |
| `langchain-anthropic` with `method="json_schema"` | Direct Anthropic API calls | LangChain abstraction provides automatic structured output parsing, retry logic, and provider swap support. Direct calls would require manual JSON parsing and schema enforcement. |
| Keyword ranking (tranche 1) | Embedding-based (tranche 2) | Deferred per PRD. Keyword rank is simple token overlap; embedding would be more accurate but adds `sentence-transformers` dependency. |

**Installation:**
```bash
pip install langgraph langchain-core langchain-anthropic
```

**Version verification:**
```bash
$ pip index versions langgraph
langgraph (0.4.8)  # as of 2026-06
$ pip index versions langchain-core
langchain-core (0.3.55)  # as of 2026-06
$ pip index versions langchain-anthropic
langchain-anthropic (0.3.17)  # as of 2026-06 — requires >=1.1.0 for method="json_schema"
```
[VERIFIED: PyPI]

**IMPORTANT:** `langchain-anthropic` version >= 1.1.0 is needed for `method="json_schema"` on `with_structured_output()`. The existing `pyproject.toml` constraint `langchain-anthropic>=0.3` is compatible but doesn't guarantee >=1.1.0. **Recommend** changing the constraint to `langchain-anthropic>=1.1.0` explicitly.

**pyproject.toml update:**
```toml
dependencies = [
  "pydantic>=2.7",
  "ruamel.yaml>=0.18",
  "typer>=0.12",
  "mcp>=1.0",
  "langgraph>=0.2",
  "langchain-core>=0.3",
  "langchain-anthropic>=1.1.0",
]
```


## Architecture Patterns

### System Architecture Diagram

```text
CLI (construct ask/bridge) ─────── Capability Registry ─────── MCP (stdio)
         │                               │                           │
         ▼                               ▼                           ▼
   validate input (Pydantic) ─── registry.get(id).handler(input) ─── validate output
                                                                         
                      ┌──────────────────┬──────────────────┐
                      │                  │                  │
                      ▼                  ▼                  ▼
              ask.domain (L2)    bridge.detect (PIPE)   synthesis (skill)
                      │                  │                  │
               ┌──────┴──────┐    ┌──────┴──────┐          │
               ▼             ▼    ▼             ▼           ▼
         LangGraph      Event    L1 L2 L3   bridges.json   update SKILL.md
         StateGraph     Log      pipeline    + candidates   to call CLI
               │                           + log
        ChatAnthropic
        with_structured_output

Data flow for ask.domain (query → answer):
  question + domain_id → load_cards → filter_by_domain → rank_by_relevance
  → build_context → llm_synthesize → extract_citations → answer + citations[]

Data flow for bridge.detect:
  workspace_path → L1: scan connections.json cross-domain edges
  → L2: compute content_category overlap matrix across domains
  → L3: for candidates above L1+L2 threshold, LLM assesses semantic similarity
  → score = 0.30*L1 + 0.20*L2 + 0.50*L3 → bridges.json
```

### Recommended Project Structure

```
src/construct/
├── __init__.py
├── cli.py                              # Extended: +ask, +bridge command groups
├── capabilities/
│   ├── registry.py                     # CapabilityRecord, CapabilityRegistry (unchanged)
│   └── catalog.py                      # +ask.domain, +bridge.detect registrations
├── llm/
│   ├── __init__.py                     # Package init
│   ├── config.py                       # Provider/Gate config loader (YAML → Pydantic)
│   ├── config.yaml                     # Repo-default LLM provider config
│   └── ask_domain.py                   # LangGraph StateGraph: state, nodes, runner
├── pipelines/
│   ├── __init__.py
│   ├── graph_status.py
│   ├── bridge_detect.py                # L1 → L2 → L3 pipeline
│   └── ...
├── schemas/
│   ├── card.py
│   ├── workspace.py
│   └── config.py
├── services/
│   ├── knowledge.py
│   ├── event_log.py
│   └── ...
├── storage/
│   └── workspace.py
└── mcp/
    └── server.py                       # Auto-registers tools from registry (unchanged)
```

### Pattern 1: LangGraph L2 Gate (ask.domain)

**What:** A `StateGraph` with sequential Python and LLM nodes. State is a `TypedDict` or Pydantic model that flows through each node. Each node reads state and returns partial updates. The graph is compiled and invoked with typed input.

**When to use:** Multi-step LLM workflows where state needs to be tracked, validated, and potentially checkpointed. For Phase 5: a simple linear graph (no conditional edges) is sufficient.

**State schema recommendation** (TypedDict is preferred for LangGraph compatibility [CITED: langchain.com/docs/langgraph/graph-api]):

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class AskDomainState(TypedDict):
    # Input (set before graph starts)
    question: str
    domain_id: str
    workspace_path: str
    max_cards: int
    
    # Processing (populated by nodes)
    cards: list[dict]           # Loaded and filtered KnowledgeCard dicts
    context: str                # Formatted card summaries for LLM prompt
    provider: str               # Resolved provider name
    model: str                  # Resolved model name
    
    # LLM output
    synthesised_answer: str | None     # LLM answer text
    cited_card_ids: list[str]          # Card IDs cited by LLM
    llm_confidence: str | None         # "high" | "medium" | "low"
    
    # Output (final)
    citations: list[dict]      # Resolved citation objects with card metadata
    retrieval_cards_considered: int
    retrieval_cards_selected: int
    
    # Gate metadata
    token_usage: dict | None
    review_required: bool
    review_status: str
```

**Graph nodes and edges** (per PRD graph topology [CITED: prd-v03-pipeline-mvp.md §8.2]):

```text
START → load_domain_cards → filter_by_domain → rank_by_relevance
       → build_context → llm_synthesize → extract_citations → END
```

**Each node's responsibility:**

| Node | Type | Input | Output (state update) |
|------|------|-------|----------------------|
| `load_domain_cards` | Python | workspace_path | cards (all non-archived cards from workspace) |
| `filter_by_domain` | Python | cards, domain_id | cards (filtered to domain) |
| `rank_by_relevance` | Python | cards, question, max_cards | cards (ranked, limited); retrieval_cards_considered/selected |
| `build_context` | Python | cards | context (formatted summary string for LLM) |
| `llm_synthesize` | LLM | context, question | synthesised_answer, cited_card_ids, llm_confidence |
| `extract_citations` | Python | synthesised_answer, cited_card_ids, cards | citations (resolved metadata) |

**LLM node implementation** (the core pattern):

```python
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

# Pydantic model for structured LLM output
class SynthesisOutput(BaseModel):
    """Structured answer from grounded Q&A."""
    answer: str = Field(description="Answer to the user's question based only on the provided cards.")
    cited_card_ids: list[str] = Field(description="Card IDs from the provided context that support this answer.")
    confidence: str = Field(description="Self-assessed grounding confidence: high/medium/low")

def llm_synthesize(state: AskDomainState) -> dict:
    """LLM node: answer question from card context with structured output."""
    llm = ChatAnthropic(
        model=state.get("model", "claude-sonnet-4-20250514"),
        temperature=0.2,
    )
    structured_llm = llm.with_structured_output(SynthesisOutput, method="json_schema")
    # Native JSON schema mode — no tool-choice conflicts with Anthropic
    
    messages = [
        SystemMessage(content=(
            "You are a knowledge synthesis assistant. Answer the user's question "
            "using ONLY the provided card context. Cite specific card IDs for each claim. "
            "If the context doesn't answer the question, say so clearly."
        )),
        HumanMessage(content=f"Question: {state['question']}\n\nContext:\n{state['context']}"),
    ]
    
    result = structured_llm.invoke(messages)
    # result is a SynthesisOutput Pydantic instance
    return {
        "synthesised_answer": result.answer,
        "cited_card_ids": result.cited_card_ids,
        "llm_confidence": result.confidence,
    }
```
[VERIFIED: langchain-anthropic ChatAnthropic with_structured_output docs]
[CITED: docs.langchain.com/oss/python/integrations/chat/anthropic — structured output section]

**Graph construction:**

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(AskDomainState)
builder.add_node("load_domain_cards", load_domain_cards)
builder.add_node("filter_by_domain", filter_by_domain)
builder.add_node("rank_by_relevance", rank_by_relevance)
builder.add_node("build_context", build_context)
builder.add_node("llm_synthesize", llm_synthesize)
builder.add_node("extract_citations", extract_citations)

builder.add_edge(START, "load_domain_cards")
builder.add_edge("load_domain_cards", "filter_by_domain")
builder.add_edge("filter_by_domain", "rank_by_relevance")
builder.add_edge("rank_by_relevance", "build_context")
builder.add_edge("build_context", "llm_synthesize")
builder.add_edge("llm_synthesize", "extract_citations")
builder.add_edge("extract_citations", END)

graph = builder.compile()
```

### Pattern 2: PIPE Handler (bridge.detect)

**What:** A deterministic Python function that reads workspace files, runs three analysis levels (L1, L2, L3), and returns an `OperationResult` with structured data. Follows the same pattern as `graph_status.py`.

**When to use:** Any deterministic pipeline capability that reads workspace state and produces derived data.

**Key pattern from graph_status.py** [CITED: src/construct/pipelines/graph_status.py]:

```python
def bridge_detect(workspace_path: str) -> OperationResult:
    try:
        root = Path(workspace_path)
        loader = WorkspaceLoader(root)
        
        # L1: Structural edges
        l1_results = _l1_structural(loader)
        
        # L2: Category overlap
        l2_results = _l2_category_overlap(loader)
        
        # L3: Semantic (LLM) — only for promising L1/L2 candidates
        l3_results = _l3_semantic(loader, l1_results, l2_results) if _has_promising_candidates(l1_results, l2_results) else {}
        
        # Compute scores per spec-v02-cross-domain-data.md §7
        bridges = _compute_scores(l1_results, l2_results, l3_results)
        
        # Persist candidates to log/bridge-candidates.json
        _persist_candidates(root, l1_results, l2_results, l3_results)
        
        return OperationResult(
            success=True,
            message=f"Bridge detection complete: {bridges['summary']['totals']['confirmed']} confirmed, {bridges['summary']['totals']['strong_candidates']} strong candidates",
            data=bridges,
        )
    except (WorkspaceLoadError, OSError) as exc:
        return OperationResult(success=False, message=str(exc), errors=[OperationError(reason=str(exc))])
```

### Anti-Patterns to Avoid

- **Conditional edges in the LangGraph for Phase 5:** The PRD graph topology shows a linear flow. Adding conditional branches (routing, retry loops) adds complexity not needed for Phase 5. Keep it simple — all edges are unconditional.
- **Using `create_react_agent` or `create_agent` instead of raw `StateGraph`:** The prebuilt agents add tool-calling overhead. For a structured Q&A gate with no tool usage, raw `StateGraph` is simpler, more transparent, and avoids the `tool_choice="any"` conflict with Anthropic thinking [CITED: github.com/langchain-ai/langchain issue #35539].
- **Mixing LLM tier selection logic into graph nodes:** Keep provider resolution in a separate config loader (`src/construct/llm/config.py`). Graph nodes should receive a resolved `model` string, not resolve it themselves.
- **Embedding-based retrieval in Phase 5:** Explicitly deferred to tranche 2 [CITED: prd-v03-pipeline-mvp.md §14]. Use keyword overlap ranking (token matching against question terms) for Phase 5.


## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM structured output parsing | Manual JSON parsing + validation | `ChatAnthropic.with_structured_output(method="json_schema")` | Native Anthropic JSON schema mode guarantees structured output format, auto-parses to Pydantic, handles validation. Manual parsing breaks on model output changes. |
| State management across LLM calls | Manual dict passing | `StateGraph` with TypedDict state | LangGraph manages state merging, reducers, and future checkpointing. Manual dict passing works but doesn't scale to conditional edges or streaming. |
| YAML config loading | Custom YAML parser | `ruamel.yaml` + Pydantic models | Already in the project. Provider config YAML loads with same pattern as `model-routing.yaml`. |
| Multi-level pipeline orchestration | Ad-hoc function chaining | Modular `_l1`, `_l2`, `_l3` functions | Each level independently testable. L3 calls L1/L2 candidates as input, not re-scanning. |
| Event logging | Custom file writer | `append_event()` from `construct.services.event_log` | Already handles YAML-safe datetime serialization, missing-directory creation, and non-blocking writes. Follows existing event format. |

**Key insight:** The LangChain ecosystem (langgraph + langchain-core + langchain-anthropic) is purpose-built for exactly this use case — a bounded LLM call with structured output inside a stateful workflow. The integration cost is minimal (one pip install, one import, ~40 lines of graph wiring), and the benefits over a raw API call include structured output guarantees, provider swap via config, and future extensibility (checkpointing, streaming, traceability).


## Common Pitfalls

### Pitfall 1: `tool_choice="any"` conflict with `with_structured_output`

**What goes wrong:** Using `llm.with_structured_output(schema)` with default `method="function_calling"` forces `tool_choice="any"`, which conflicts with Anthropic's extended thinking and some model configurations.

**Why it happens:** LangChain's default structured output method wraps the schema as a tool call with forced tool selection. Anthropic rejects this when thinking is enabled.

**How to avoid:** Use `method="json_schema"` (native Anthropic structured output, available since langchain-anthropic >= 1.1.0). This avoids tool-calling entirely and uses Claude's dedicated structured output feature.

**Warning signs:** `400 error: "Thinking may not be enabled when tool_choice forces tool use"` — switch to `method="json_schema"`.

### Pitfall 2: Pydantic state schema with LangGraph TypedDict

**What goes wrong:** Using `BaseModel` for graph state schema leads to type coercion issues in LangGraph nodes — nodes return dict updates, not Pydantic instances, and LangGraph expects specific field types.

**Why it happens:** LangGraph prefers `TypedDict` for state schemas. Pydantic `BaseModel` state schemas work but require careful type matching on node return values.

**How to avoid:** Use `TypedDict` for the graph `State` schema. Use Pydantic `BaseModel` only for the structured LLM output schema (passed to `with_structured_output`). This is the recommended pattern in LangGraph docs.

**Warning signs:** Silent type coercion failures or `ValidationError` on graph invoke — switch state schema to `TypedDict`.

### Pitfall 3: L3 LLM call for every possible pair

**What goes wrong:** The L3 semantic assessment fires an LLM call for every candidate detected by L1 and L2. With N cards across M domains, this can be O(N²) LLM calls.

**Why it happens:** Naive implementation doesn't filter L1+L2 candidates before L3.

**How to avoid:** Apply a threshold before L3: only candidates with L1 + L2 combined score >= 0.3 proceed to LLM assessment. The L3 call is the expensive step — it should only fire for genuinely promising candidates.

**Warning signs:** Bridge detection takes >30 seconds or generates excessive token usage — check the candidate filter threshold.

### Pitfall 4: Config file not found at first LLM call

**What goes wrong:** `src/construct/llm/config.yaml` doesn't exist yet, or the environment variables (`ANTHROPIC_API_KEY`) aren't set. The first `ask.domain` call fails with a confusing error.

**Why it happens:** The config file is new (no existing template), and LLM API keys are runtime-environment dependent.

**How to avoid:** Create the config.yaml during Phase 5 implementation. Provide a default template with `anthropic` provider. Add clear error messages in the config loader when the file is missing or API key is unset. The `CONSTRUCT_LLM_CONFIG` env var override should work as a fallback during development.

**Warning signs:** `GATE_PROVIDER_ERROR` on first `ask.domain` call — check config.yaml exists and ANTHROPIC_API_KEY is set.


## Code Examples

### Example 1: LangGraph L2 gate runner interface

```python
# Source: PRD §8.5 [CITED: prd-v03-pipeline-mvp.md lines 909-914]

def run_gate(
    gate_id: str,
    input_data: BaseModel,
    *,
    config_path: Path | None = None,
) -> GateResult:
    """Execute LangGraph gate; never writes SOT."""
    # Load provider config
    config = load_llm_config(config_path)
    gate_config = config.gates[gate_id]
    provider_config = config.providers[gate_config.provider]
    
    # Build and compile the graph
    graph = build_ask_domain_graph()
    
    # Prepare initial state from input
    initial = AskDomainState(
        question=input_data.question,
        domain_id=input_data.domain_id,
        workspace_path=input_data.workspace_path,
        max_cards=input_data.max_cards,
        provider=gate_config.provider,
        model=provider_config.model,
        # ... defaults for processing fields
    )
    
    # Invoke graph
    result = graph.invoke(initial)
    
    # Wrap into capability output
    return AskDomainOutput(
        answer=result["synthesised_answer"],
        citations=result["citations"],
        gate=GateMetadata(
            gate_id="ask.domain",
            tier="L2",
            review_required=True,
            review_status="pending" if result["synthesised_answer"] else "not_required",
            provider=result.get("provider", ""),
            model=result.get("model", ""),
        ),
        retrieval={
            "cards_considered": result["retrieval_cards_considered"],
            "cards_selected": result["retrieval_cards_selected"],
        }
    )
```

### Example 2: Bridge detection scoring (from spec)

```python
# Source: spec-v02-cross-domain-data.md §7 [CITED]
# Weights:
#   L1 = 0.30, L2 = 0.20, L3 = 0.50

def _compute_bridge_score(
    l1_structural: bool,
    l2_shared_categories: list[str],
    l3_candidate_strength: str | None,  # "strong" | "possible" | None
) -> tuple[float, str]:
    """Compute normalized bridge score and strength band.
    
    Returns (score_0_to_1, band: "strong"|"medium"|"weak").
    """
    # L1 score: 1.0 if direct edge, 0.0 otherwise
    l1_score = 1.0 if l1_structural else 0.0
    
    # L2 score: min(1.0, shared_count / 3)
    l2_score = min(1.0, len(l2_shared_categories) / 3.0) if l2_shared_categories else 0.0
    
    # L3 score: 1.0 for strong, 0.6 for possible, 0.0 if none
    l3_map = {"strong": 1.0, "possible": 0.6}
    l3_score = l3_map.get(l3_candidate_strength, 0.0) if l3_candidate_strength else 0.0
    
    # Final score
    score = (0.30 * l1_score) + (0.20 * l2_score) + (0.50 * l3_score)
    score = round(score, 2)
    
    # Band assignment
    if l1_structural:  # confirmed bridge
        band = "strong"
    elif score >= 0.70:
        band = "strong"
    elif score >= 0.45:
        band = "medium"
    else:
        band = "weak"
    
    return score, band
```

### Example 3: Capability registration pattern

```python
# Source: src/construct/capabilities/catalog.py [CITED]
# New registrations to add in Phase 5:

from construct.llm.ask_domain import AskDomainInput, AskDomainOutput, run_gate
from construct.pipelines.bridge_detect import BridgeDetectInput, BridgeDetectOutput

# In create_registry():

registry.register(CapabilityRecord(
    id="ask.domain",
    name="Ask Domain",
    description="Grounded Q&A with citations over workspace knowledge cards for a domain",
    input_model=AskDomainInput,
    output_model=AskDomainOutput,
    handler=lambda **kwargs: run_gate("ask.domain", AskDomainInput(**kwargs)),
    cli_name="ask.domain",
    mcp_tool_name="construct_ask_domain",
))

registry.register(CapabilityRecord(
    id="bridge.detect",
    name="Bridge Detect",
    description="Detect cross-domain bridges via L1 structural, L2 category, L3 semantic pipeline",
    input_model=BridgeDetectInput,
    output_model=BridgeDetectOutput,
    handler=lambda **kwargs: bridge_detect(kwargs.get("workspace_path")),
    cli_name="bridge.detect",
    mcp_tool_name="construct_bridge_detect",
))
```

### Example 4: CLI command group pattern

```python
# Source: src/construct/cli.py [CITED]
# Following the existing workflow_app / ingest_app add_typer pattern:

ask_app = typer.Typer(no_args_is_help=True, name="ask", help="Ask questions grounded in workspace knowledge.")
app.add_typer(ask_app)

@ask_app.command()
def domain(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    domain_id: str = typer.Option(..., "--domain", "-d", help="Domain ID to query"),
    question: str = typer.Option(..., "--question", "-q", help="Your question"),
    max_cards: int = typer.Option(20, "--max-cards", help="Max cards to consider"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Ask a grounded question about a domain's knowledge cards."""
    try:
        cap = get_registry().get("ask.domain")
    except KeyError:
        typer.echo("ERROR: Capability not found.")
        raise typer.Exit(code=1)
    result = cap.handler(
        workspace_path=str(workspace),
        domain_id=domain_id,
        question=question,
        max_cards=max_cards,
    )
    _display_result(result, json_output)

# bridge command group:
bridge_app = typer.Typer(no_args_is_help=True, name="bridge", help="Cross-domain bridge detection and management.")
app.add_typer(bridge_app)

@bridge_app.command()
def detect(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Detect cross-domain bridges via L1→L2→L3 pipeline."""
    try:
        cap = get_registry().get("bridge.detect")
    except KeyError:
        typer.echo("ERROR: Capability not found.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace_path=str(workspace))
    _display_result(result, json_output)
```


## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude-native LLM calls in SKILL.md | LangGraph L2 gate with structured output | Phase 5 | LLM calls become deterministic, testable, and provider-swappable via config |
| Manual card scanning (bridge detection) | Multi-level pipeline: L1 deterministic + L2 overlap + L3 LLM | Phase 5 | Faster (L1/L2 skip LLM for weak candidates), reproducible, auditable |
| Inline validation (synthesis skill) | CLI commands via capability registry | Phase 5 | Synthesis skill delegates to proven Python handlers rather than doing file I/O inline |

**Deprecated/outdated:**
- Direct `model-routing.yaml` provider config for `ask.domain`: The PRD specifies a separate `src/construct/llm/config.yaml` with gate-specific settings (temperature, review_required). The existing `model-routing.yaml` is for Claude-native task routing; the new config is for Pipeline L2 gate LLM calls.


## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `langchain-anthropic>=1.1.0` is needed for `method="json_schema"` and the installed pypi version will be >= 1.1.x. | Dependencies | If only >=0.3 is installed, `method="json_schema"` won't work; would need to use `method="function_calling"` which has tool-choice conflicts with thinking. |
| A2 | `method="json_schema"` works with the `StateGraph` pattern (not just standalone model calls). | LangGraph Patterns | If `StateGraph` nodes don't support the `with_structured_output` runnable, we'd need to invoke the structured LLM outside the graph and pass results in. |
| A3 | The PRD graph topology (6 linear nodes) is sufficient for Phase 5 without error-handling nodes or retry edges. | Architecture | If the LLM call fails, there's no retry mechanism. The entire graph fails. This is acceptable per "fail loud, structured" principle but should be logged clearly. |
| A4 | `bridges.json` generation at `views/build/data/bridges.json` is not in Phase 5 scope for the bridge detection pipeline itself — only `log/bridge-candidates.json` is. | Bridge Detection | The PRD mentions `bridge.detect` produces candidates; `views-generate-data` expands them. But D-06 deliverable 4 says "bridges.json derived data file per existing spec contract" — may need a generation step. |
| A5 | The `BridgeDetectInput` model accepts a single workspace_path and scans cross-domain against the main install's discovered workspaces. | Bridge Detection | If multi-workspace scanning requires install_root awareness, the input model may need an `install_root` or `workspaces` parameter beyond just `workspace_path`. |
| A6 | The `config.yaml` LLM provider config (PRD §8.4) does not need to merge with existing `model-routing.yaml`; they are independent config files for different subsystems. | Config | If future phases merge these configs, the Phase 5 implementation may need refactoring. Acceptable per deferred design pattern. |


## Open Questions

1. **L3 bridge assessment approach — LLM classification vs hybrid?**
   - What we know: The SKILL.md defines L3 as "assess whether content suggests a genuine structural parallel" — this requires reading card content.
   - What's unclear: Should L3 use a single LLM call per candidate pair (classify strong/possible/reject), or a batch approach (send multiple candidates in one call for efficiency)?
   - Recommendation: Use single-pair LLM calls with prompt requesting "strong" / "possible" / "reject" classification plus reasoning. This matches the existing Candidate Source Contract and is simple to implement. Batch can be optimized in Phase 6 if needed.

2. **LLM tier for L3 bridge assessment vs L2 Q&A?**
   - What we know: L2 Q&A requires frontier-level reasoning (synthesis, citation). L3 bridge assessment is classification-like.
   - What's unclear: Whether to use a lightweight model (haiku) for L3 classification vs the same frontier model as the L2 gate.
   - Recommendation: Use `workhorse` tier (haiku) for L3 classification — it's a simple judgment call, not synthesis. Use `frontier` tier (sonnet) for `ask.domain` L2 Q&A. Both configurable via the LLM config YAML.

3. **Input model for `bridge.detect` — workspace_path vs install_root?**
   - What we know: Bridge candidates are per-workspace (one workspace discovers candidates pointing outward). But `bridges.json` is global.
   - What's unclear: Should `bridge.detect` accept a single workspace and write `log/bridge-candidates.json` for that workspace (leaving global expansion to `views-generate-data`), or should it scan all workspaces?
   - Recommendation: Accept single `workspace_path`. Write `log/bridge-candidates.json` for that workspace. The `views-generate-data` pipeline (already scoped in Phase 4) handles global expansion. This follows the existing `views-generate-data` responsibility for cross-workspace aggregation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All Phase 5 code | ✓ | 3.14.5 | — |
| pip | Package install | ✓ | 27.x | — |
| langgraph | L2 gate | ✗ | Not installed | `pip install langgraph` |
| langchain-core | LangGraph, structured output | ✗ | Not installed | `pip install langchain-core` |
| langchain-anthropic | ChatAnthropic LLM wrapper | ✗ | Not installed | `pip install langchain-anthropic` |
| ANTHROPIC_API_KEY | LLM calls | ? | Need to check | Mock LLM for tests |

**Missing dependencies with no fallback:**
- `langgraph`, `langchain-core`, `langchain-anthropic` — must be installed before any LLM functionality works. These are explicit additions per D-07.

**Missing dependencies with fallback:**
- `ANTHROPIC_API_KEY` — for development and testing without API calls, implement a mock LLM node that returns fixed structured output. Tests can use this mock.


## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (existing) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/llm/ -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADV-01 | `ask.domain` returns structured answer + citations with Pydantic-validated output | unit | `pytest tests/llm/test_ask_domain.py::test_ask_domain_structure -x` | ❌ Wave 0 |
| ADV-01 | `ask.domain` citations reference real card IDs from workspace | contract | `pytest tests/contract/test_ask_domain_mocked.py -x` | ❌ Wave 0 |
| ADV-01 | Provider config load + override | unit | `pytest tests/llm/test_ask_domain.py::test_provider_config -x` | ❌ Wave 0 |
| ADV-01 | `GATE_TIMEOUT` when LLM takes too long | unit | `pytest tests/llm/test_ask_domain.py::test_timeout -x` | ❌ Wave 0 |
| ADV-02 | L1 detects cross-domain edges correctly | unit | `pytest tests/bridge/test_bridge_l1.py -x` | ❌ Wave 0 |
| ADV-02 | L2 computes category overlap scores | unit | `pytest tests/bridge/test_bridge_l2.py -x` | ❌ Wave 0 |
| ADV-02 | L3 invokes LLM only for promising candidates | unit | `pytest tests/bridge/test_bridge_l3.py -x` | ❌ Wave 0 |
| ADV-02 | Scoring matches spec-v02-cross-domain-data.md weights | unit | `pytest tests/bridge/test_bridge_scoring.py -x` | ❌ Wave 0 |
| ING-06 | Citations include per-card confidence (1-5) | unit | `pytest tests/llm/test_ask_domain.py::test_citation_confidence -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/llm/ tests/bridge/ -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/llm/test_ask_domain.py` — covers ADV-01, ING-06
- [ ] `tests/llm/conftest.py` — mock LLM fixtures, shared test data
- [ ] `tests/bridge/test_bridge_l1.py` — L1 structural detection
- [ ] `tests/bridge/test_bridge_l2.py` — L2 category overlap
- [ ] `tests/bridge/test_bridge_l3.py` — L3 LLM assessment (mocked)
- [ ] `tests/bridge/test_bridge_scoring.py` — scoring model
- [ ] `tests/bridge/conftest.py` — workspace fixtures with cross-domain cards
- [ ] `tests/contract/test_ask_domain_mocked.py` — CLI contract test with mocked LLM
- [ ] Framework install: `pip install langgraph langchain-core langchain-anthropic`


## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pydantic models on all capability inputs (`BaseModel` with `Field` constraints) |
| V6 Cryptography | no | No secrets handled in code; API keys read from environment variables |
| V8 Data Protection | yes | L2 gate is read-only per D-01; bridge pipeline writes only derived data |

### Known Threat Patterns for Python + LangGraph

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via user question | Spoofing | System prompt instructs LLM to use only provided context; no tool access in Phase 5 L2 gate |
| API key exposure in config YAML | Information Disclosure | Config references env vars (`api_key_env: ANTHROPIC_API_KEY`), never stores keys inline |
| Workspace path traversal | Tampering | WorkspacePathInput validated by Pydantic; WorkspaceLoader constrains to workspace root |
| LLM hallucination (citations) | Repudiation | `with_structured_output` enforces `cited_card_ids` format; extract_citations node validates each ID exists in workspace |


## Sources

### Primary (HIGH confidence)
- [VERIFIED: PyPI] — Package versions for langgraph, langchain-core, langchain-anthropic: `pip index versions <package>`
- [CITED: prd-v03-pipeline-mvp.md] — ask.domain input/output JSON schemas (§5.5), graph topology (§8.2), provider config (§8.4), structured output schema (§8.3), gate runner interface (§8.5)
- [CITED: spec-v02-cross-domain-data.md] — bridges.json schema (§5), scoring model (§7), banding rules (§7.4)
- [CITED: src/construct/capabilities/registry.py] — CapabilityRecord and registry pattern
- [CITED: src/construct/pipelines/graph_status.py] — PIPE handler pattern
- [CITED: src/construct/cli.py] — Typer command group pattern
- [CITED: src/construct/capabilities/catalog.py] — Registration pattern
- [CITED: src/construct/services/knowledge.py] — OperationResult, OperationError patterns
- [CITED: src/construct/schemas/config.py] — RoutingTask enum, ProviderConfig model
- [CITED: src/construct/storage/workspace.py] — WorkspaceLoader pattern
- [CITED: src/construct/mcp/server.py] — MCP auto-registration from registry
- [CITED: CONSTRUCT-CLAUDE-impl/claude/skills/construct-bridge-detect/SKILL.md] — L1/L2/L3 bridge detection procedure
- [CITED: CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md] — Current synthesis skill procedure
- [CITED: docs.langchain.com/oss/python/langgraph/graph-api] — StateGraph, nodes, edges, compilation
- [CITED: docs.langchain.com/oss/python/integrations/chat/anthropic] — ChatAnthropic, structured output, method="json_schema"

### Secondary (MEDIUM confidence)
- [VERIFIED: langchain reference docs] — `with_structured_output` API: method parameter, return types, Pydantic support
- [CITED: github.com/langchain-ai/langchain/issues/35539] — `tool_choice="any"` conflict with Anthropic thinking; resolution via `method="json_schema"` or `ProviderStrategy`

### Tertiary (LOW confidence)
- None — all claims are from primary source code or official documentation


## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all library versions verified against PyPI and official docs
- Architecture: HIGH — patterns directly extracted from existing codebase
- Pitfalls: MEDIUM — tool_choice conflict is documented in LangChain issue tracker; other pitfalls are architectural projections
- Scoring model: HIGH — exact math from spec-v02-cross-domain-data.md §7

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (30 days — LangGraph and LangChain release cycles are stable)
