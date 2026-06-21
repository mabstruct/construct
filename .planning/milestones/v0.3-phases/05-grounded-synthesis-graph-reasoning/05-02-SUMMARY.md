---
phase: 05-grounded-synthesis-graph-reasoning
plan: 02
subsystem: llm
tags:
  - langgraph
  - l2-gate
  - ask-domain
  - capability-registration
  - cli
  - tdd
requirements_completed: [ADV-01]
requires:
  - 05-01
provides:
  - ask.domain LangGraph L2 gate
  - Capability registration + CLI command
  - Full test suite
affects:
  - src/construct/llm/
  - src/construct/capabilities/
  - src/construct/cli.py
  - tests/llm/
tech-stack:
  added:
    - langgraph>=0.2 (verified installed)
    - langchain-core>=0.3 (verified installed)
    - langchain-anthropic>=1.1.0 (verified installed)
key-files:
  created:
    - src/construct/llm/ask_domain.py (423 lines)
  modified:
    - src/construct/capabilities/catalog.py (+19 lines)
    - src/construct/cli.py (+32 lines)
    - tests/llm/test_ask_domain.py (replaced stubs, +364 lines)
    - tests/contract/test_ask_domain_mocked.py (replaced stubs)
decisions:
  - "Models defined in ask_domain.py instead of catalog.py to avoid circular imports"
  - "Empty context guard implemented in llm_synthesize node (check before LLM call)"
  - "Domain filter checks domain_id in card.domains list (not single domain_id field)"
metrics:
  duration: "~12 min"
  completed_date: "2026-06-11"
---

# Phase 05 Plan 02: ask.domain L2 Gate — LangGraph StateGraph, Capability Registration, CLI & Tests

Implemented the grounded Q&A gate (`ask.domain`): a 6-node LangGraph linear StateGraph that loads workspace cards, filters by domain, ranks by keyword relevance, builds an LLM context, invokes `ChatAnthropic.with_structured_output(method="json_schema")` for structured synthesis, and extracts validated citations with per-card confidence. Registered as a capability, exposed via CLI (`construct ask domain`), and backed by 11 passing tests.

## Deliverables

### 1. `src/construct/llm/ask_domain.py` (423 lines)

- **`AskDomainState`** — TypedDict graph state schema (not BaseModel) with all input, processing, LLM output, and metadata fields
- **`SynthesisOutput`** — Pydantic BaseModel for `with_structured_output(method="json_schema")` with `answer`, `cited_card_ids`, `confidence`
- **6 linear nodes**: `load_domain_cards` → `filter_by_domain` → `rank_by_relevance` → `build_context` → `llm_synthesize` → `extract_citations`
- **`build_ask_domain_graph()`** — factory function that compiles and returns the StateGraph
- **`run_gate()`** — loads LLM config from YAML, resolves provider/model, invokes graph, returns `AskDomainOutput`
- **Empty context guard** — checks if context is empty before LLM call, skips invocation when no relevant cards
- **Exact-match cache** — module-level `_CACHE` dict keyed by `domain_id::question` with 24h TTL
- **Input/Output models** — `AskDomainInput`, `AskDomainOutput`, `Citation`, `GateMetadata` defined here (decision: avoids circular imports with catalog.py)

### 2. Capability Registration (`catalog.py`)

- Registered `ask.domain` with `AskDomainInput`/`AskDomainOutput` models
- Handler wraps `run_gate()` result in `OperationResult` for CLI compatibility
- `cli_name="ask.domain"`, `mcp_tool_name="construct_ask_domain"`

### 3. CLI Commands (`cli.py`)

- `ask_app` Typer group with `domain` subcommand
- Options: `--question/-q`, `--domain/-d`, `--workspace/-w`, `--max-cards`, `--json/-j`

### 4. Test Suite (11 tests, all passing)

| Test | Coverage |
|------|----------|
| `test_graph_compiles` | Graph builds and has invoke method |
| `test_graph_has_six_nodes` | All 6 expected nodes present |
| `test_domain_filtering_works` | Only matching domain cards reach LLM |
| `test_citation_confidence_fidelity` | Citation confidence matches source card frontmatter |
| `test_empty_context_skips_llm` | No cards → None answer, no LLM call |
| `test_archived_cards_excluded` | lifecycle=archived excluded from counts |
| `test_provider_config_default_loads` | Config loads and resolves correctly |
| `test_max_cards_respected` | max_cards limit enforced |
| `test_llm_failure_returns_graceful_error` | LLM error → graceful None answer |
| `test_keyword_rank_orders_by_relevance` | Higher token overlap → higher rank |
| `test_full_pipeline_returns_answer_with_citations` | End-to-end contract test |

## Deviations from Plan

### Models located in ask_domain.py (not catalog.py)

The plan specified adding AskDomainInput/AskDomainOutput/Citation/GateMetadata models in `catalog.py` before the registry factory. However, `catalog.py` imports `run_gate` from `ask_domain.py`, and `run_gate`'s type signature references `AskDomainInput`. Defining the models in `catalog.py` would create a circular import (catalog → ask_domain → catalog). Models are defined in `ask_domain.py` instead, and imported by `catalog.py`. All names (`AskDomainInput`, `AskDomainOutput`, etc.) remain the same — just the defining module changed.

### Domain filter uses `domains` list (not `domain_id` field)

The plan's `filter_by_domain` pseudocode checked `c.get("domain_id")` as a single string. The actual `KnowledgeCard` schema has `domains: list[str]` (plural list). The filter checks `state["domain_id"] in c.get("domains", [])` instead. This is correct per the existing Pydantic schema — the plan pseudocode did not account for the actual data model.

## Threat Model Compliance

- **T-05-03 (Prompt injection):** System prompt restricts LLM to provided card context. User input is in HumanMessage only. No tool bindings used. ✓
- **T-05-04 (Repudiation/citation validation):** `extract_citations` validates every cited ID against the retrieved card set. Missing IDs are dropped with a structured warning. ✓
- **T-05-05 (Information disclosure):** `filter_by_domain` runs before `build_context` and `llm_synthesize`. Only domain-matching cards reach the LLM. ✓
- **T-05-06 (Denial of Service):** `max_cards` capped at 50 (default 20). Card body truncated to 2000 chars. Hard truncation at 100K estimated tokens. Empty context guard skips LLM call entirely. ✓

## Self-Check: PASSED

- [x] `build_ask_domain_graph()` compiles with 6 nodes ✓
- [x] `get_registry().get("ask.domain")` succeeds ✓
- [x] All 11 tests pass ✓
- [x] `ask_app` CLI group compiles ✓
