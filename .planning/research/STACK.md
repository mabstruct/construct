# Stack Research

**Domain:** CONSTRUCT v0.4 model-agnostic agent workflows — LangGraph/LangChain workflow runtime + Tavily/search provider spine  
**Researched:** 2026-06-21  
**Confidence:** HIGH  
**Scope boundary:** This is a v0.4 delta only. It assumes v0.3 shipped the canonical workspace contracts, capability registry, CLI, MCP stdio, `ask.domain`, bridge detection, governed ingest, `WorkflowRunner`, Streamlit ops UI, and view data contracts. It does **not** re-scope v0.5 browser UI, HTTP, cloud, or unrelated v0.3 carry-over debt.

## Executive Recommendation

Keep the existing Python/Pydantic/Typer/MCP/file-workspace spine. v0.4 only needs a focused runtime/search delta: tighten the LangGraph/LangChain package bounds to the current 1.x line, add Tavily's official Python SDK behind a provider abstraction, add a durable local LangGraph checkpointer for human review pauses, and add a small retry utility as a direct dependency if provider calls use it.

Use **LangGraph** for stateful workflows with pause/resume (`research.run`, `curation.run`, later daily-cycle composition), **LangChain provider adapters** for bounded structured L2/L3 gates (`research.score`, `card.evaluate`, promotion/connection decisions), and **plain Python** for deterministic steps (query building, dedup, validation, graph metrics, ingest, event logging). Do not let LangGraph become the general runtime for file I/O or validation.

Use **Tavily as the default real web search provider** because its SDK returns structured result JSON with `title`, `url`, `content`, `score`, optional `raw_content`, response timing, and search filters that map cleanly to CONSTRUCT's planned `SearchResult`. But Tavily must sit behind `SearchProvider`; all tests and CI should run against a mock provider/fixture provider with no network or API key.

## Recommended Stack Delta

### Core Technologies

| Technology / package | Current latest verified | pyproject action | Purpose | Why Recommended | Confidence |
|---|---:|---|---|---|---|
| Python | keep `>=3.11` | No v0.4 change | Runtime for pipelines/capabilities | Current dependencies support Python >=3.10; repo already targets >=3.11. Do not force a Python-version migration inside workflow work. | HIGH |
| `pydantic` | 2.13.4 | Keep existing `>=2.7` unless phase wants tighter tested bounds | Capability/search/gate/workflow schemas | Existing contract language; all new provider and gate outputs should be `extra="forbid"` Pydantic v2 models. | HIGH |
| `langgraph` | 1.2.6 | Change from `>=0.2` to `>=1.2,<2` | Stateful workflow graphs, interrupts, checkpointing | Official docs position LangGraph as the orchestration runtime for durable execution, persistence, and human-in-the-loop workflows; v0.4 needs exactly that. The current lower bound is too loose for the 2026 docs/API line. | HIGH |
| `langchain-core` | 1.4.8 | Change from `>=0.3` to `>=1.4,<2` | Message/model interfaces and structured-output base | v0.3 already imports `langchain_core`; v0.4 gates should stay on direct chat-model interfaces instead of full agent loops. | HIGH |
| `langchain-anthropic` | 1.4.6 | Change from `>=1.1.0` to `>=1.4,<2` | Default L2/L3 provider | Existing default provider; current docs confirm `ChatAnthropic` supports structured output, streaming, async, token usage, and newer features. | HIGH |
| `tavily-python` | 0.7.26 | **Add** `>=0.7,<1` | Default real `SearchProvider` implementation | Official SDK supports sync/async clients and `search()` with `search_depth`, `topic`, `time_range`, `max_results`, `include_raw_content`, domain filters, timeout, usage metadata. It maps cleanly to `SearchResult`. | HIGH |
| `langgraph-checkpoint-sqlite` | 3.1.0 | **Add** `>=3.1,<4` by W3 at latest | Durable local checkpoints for LangGraph interrupts/resume | LangGraph checkpointers are required for human-in-the-loop, time travel, and fault tolerance. SQLite checkpointer is the local workflow option and is separate from `langgraph`. This is not a knowledge index or SOT database. | HIGH |
| `tenacity` | 9.1.4 | **Add** `>=9.1,<10` if provider retry/backoff is implemented | Explicit retry/backoff for search/provider calls | LangChain model calls have retry controls, but search providers need bounded retry/backoff and degraded-state reporting. Add as direct dependency if code imports it; do not rely on transitive installation. | MEDIUM |
| `ruamel.yaml` | 0.19.1 | Keep existing `>=0.18` | Config loading for new `search/config.yaml` | Already used for YAML config; reuse it rather than introducing another parser. | HIGH |
| `typer`, `mcp`, `streamlit` | Typer 0.26.7, MCP 1.28.0, Streamlit 1.58.0 | No v0.4 stack change | CLI, MCP stdio, existing ops UI | v0.4 adds capabilities behind the registry. CLI/MCP parity comes from registry records; Streamlit only needs gate-panel extension, not a new UI stack. | HIGH |

### Optional Provider Packages

| Package | Current latest verified | pyproject action | Purpose | When to Use | Confidence |
|---|---:|---|---|---|---|
| `langchain-openai` | 1.3.2 | Add under optional extra `providers` | OpenAI-compatible LLM gate provider | Needed only when `src/construct/llm/config.yaml` or `CONSTRUCT_LLM_CONFIG` selects OpenAI/Azure/OpenAI-compatible routes. Keep out of core if Anthropic remains default. | HIGH |
| `langchain-ollama` | 1.1.0 | Add under optional extra `providers` | Local Ollama LLM gate provider | Needed for local lightweight/workhorse tests or offline experiments. Gate schemas must still pass with mocked providers in CI. | HIGH |
| Full `langchain` package | not required | Do **not** add by default | `init_chat_model`, agents, `create_agent` helpers | Add only if a phase explicitly adopts `init_chat_model` or LangChain agent APIs. v0.4 gate work can use `langchain-core` + provider classes directly. | MEDIUM |

### Development / Test Tools

| Tool | Current latest verified | Action | Purpose | Notes |
|---|---:|---|---|---|
| `pytest` | 9.1.1 | Tighten dev extra to `>=9,<10` or keep existing `>=8` | Contract/regression tests | Current environment has 9.0.3; v0.4 should add provider and capability contract tests, not a new test runner. |
| `pytest-httpx` | 0.36.2 | Optional dev extra only if direct HTTP or async HTTP is tested | HTTP-client mocking | If using Tavily SDK directly and testing via fake provider/fixtures, `pytest` monkeypatching is enough. Add only if adapter code owns HTTP calls. |
| `pytest-asyncio` | 1.4.0 | Optional dev extra only if async graph/provider tests are introduced | Async tests | Prefer synchronous Tavily client and sync graph tests for W1/W3 unless async is clearly needed. |

## Concrete `pyproject.toml` Recommendation

Update only the dependency lines relevant to v0.4:

```toml
[project]
dependencies = [
  "langchain-anthropic>=1.4,<2",
  "langchain-core>=1.4,<2",
  "langgraph>=1.2,<2",
  "langgraph-checkpoint-sqlite>=3.1,<4",
  "mcp>=1.0",
  "pydantic>=2.7",
  "ruamel.yaml>=0.18",
  "streamlit>=1.35",
  "tavily-python>=0.7,<1",
  "tenacity>=9.1,<10",
  "typer>=0.12",
]

[project.optional-dependencies]
dev = [
  "pytest>=9,<10",
  # Add only if adapter tests mock direct HTTP calls:
  # "pytest-httpx>=0.36,<1",
]
providers = [
  "langchain-openai>=1.3,<2",
  "langchain-ollama>=1.1,<2",
]
```

If the team wants the smallest W1 slice, `langgraph-checkpoint-sqlite` can land in W3 (`research.run`) rather than W1 (`research.search`). Do not ship a human-review LangGraph workflow with only `InMemorySaver`; it will not survive process restart.

## Search Provider Spine

### Recommended module layout

| Path | Responsibility |
|---|---|
| `src/construct/search/models.py` | `SearchResult`, `SearchBatchOutput`, provider config models; Pydantic `extra="forbid"`. |
| `src/construct/search/config.py` | Load search config with resolution order: CLI flag → `CONSTRUCT_SEARCH_CONFIG` → `src/construct/search/config.yaml`. |
| `src/construct/search/config.yaml` | Default provider/caps; no secrets. |
| `src/construct/search/providers/base.py` | `SearchProvider` `Protocol` and normalized error types. |
| `src/construct/search/providers/tavily.py` | Tavily SDK adapter; maps SDK JSON into `SearchResult`. |
| `src/construct/search/providers/mock.py` | Deterministic provider for tests/CI and no-key local development. |
| `tests/fixtures/search/tavily_basic.json` | Captured representative Tavily response shape for mapping tests; no live network. |

### Recommended default config

```yaml
version: 1
default_provider: tavily

providers:
  tavily:
    type: tavily
    api_key_env: TAVILY_API_KEY
    search_depth: basic
    topic: general
    max_results: 5
    include_raw_content: markdown
    timeout_seconds: 30
    include_answer: false
  mock:
    type: mock
    fixture_dir: tests/fixtures/search

caps:
  max_queries_per_cycle: 8
  max_results_per_query: 5
  max_raw_content_chars: 20000
  degraded_on_provider_error: true
```

**Why these defaults:** Tavily's official docs cap `max_results` at 20, and `include_raw_content="markdown"` returns cleaned page content useful for L3 extraction but can increase latency/cost. Keep query and result caps low, disable Tavily-generated `answer` because CONSTRUCT's own L3 gate owns relevance/extraction, and truncate raw content before passing to LLM gates.

### Tavily mapping

| Tavily field | CONSTRUCT field | Notes |
|---|---|---|
| `title` | `SearchResult.title` | Required. |
| `url` | `SearchResult.url` | Required; derive `source_domain` with `urllib.parse.urlparse`. |
| `content` | `SearchResult.snippet` | Tavily's query-relevant content excerpt. |
| `score` | `SearchResult.provider_score` | Provider relevance score; do not treat as CONSTRUCT epistemic confidence. |
| `raw_content` | `SearchResult.raw_content` | Include only when configured; truncate before scoring. |
| `published_date` | `SearchResult.published_date` | Official docs say this appears for `topic: news`; do not require it for general search. |
| `response_time` | `SearchBatchOutput.response_time_ms` | Convert seconds to milliseconds or preserve documented unit clearly. |

### What `research.search` should be

`research.search` should be a plain Python capability, not a LangGraph graph:

```text
CLI/MCP args → SearchProvider factory → provider.search() → normalized SearchBatchOutput → OperationResult
```

No LLM scoring, no ingestion, no SOT writes. This makes W1 the provider-contract proof before workflow complexity.

## LangGraph / LangChain Workflow Runtime

### Use LangGraph for workflows with pause/resume

Recommended v0.4 graph targets:

| Capability | Runtime | Why |
|---|---|---|
| `research.search` | Plain Python | Search adapter contract only; graph would add noise. |
| `research.score` | LangChain structured-output gate, callable directly | Single bounded judgment over normalized results. Can be tested independently before `research.run`. |
| `research.run` | LangGraph `StateGraph` + checkpointer | Multi-step search → dedup → L3 score/extract → human review → ingest → digest → seed update. Needs pause/resume. |
| `curation.run` | LangGraph or WorkflowRunner wrapper over real steps | Use LangGraph once promotion/connection review needs interrupts; keep integrity/decay/orphan/report as plain Python nodes. |
| `workflow.daily_cycle` | LangGraph parent graph after research/curation stabilize | Composes subgraphs; do not build before W3/W5. |

### Checkpointing recommendation

Use `langgraph-checkpoint-sqlite` for durable local graph state, stored under workspace support state, for example:

```text
{workspace}/log/langgraph-checkpoints.sqlite
```

Operational rules:

- Compile human-review graphs with a checkpointer; use `thread_id = "{capability_id}:{run_id}"`.
- Set `LANGGRAPH_STRICT_MSGPACK=true` or configure allowed msgpack modules when using SQLite checkpoints, per the package security note.
- Store only JSON-serializable graph state: strings, numbers, lists, dicts, and `model_dump(mode="json")` output. Do not put client instances, `Path` objects, LLM model objects, functions, or file handles in graph state.
- Put side effects after human interrupt/review nodes. LangGraph nodes can re-run from the beginning on resume; non-idempotent file writes before an interrupt can duplicate writes.
- Treat checkpoint SQLite as runtime/derived state, not knowledge SOT. Cards, refs, connections, search seeds, governance, and events remain canonical files.

### LLM provider factory recommendation

Extend `src/construct/llm/config.py` instead of hardcoding provider classes in graph nodes.

Add gate IDs to `src/construct/llm/config.yaml`:

```yaml
gates:
  ask.domain:
    provider: anthropic
    temperature: 0.2
    review_required: true
  research.score:
    provider: anthropic
    temperature: 0.1
    review_required: true
  card.evaluate:
    provider: anthropic
    temperature: 0.1
    review_required: true
  curation.promotion:
    provider: anthropic
    temperature: 0.1
    review_required: true
  curation.connection_type:
    provider: anthropic
    temperature: 0.1
    review_required: true
```

Factory behavior:

| Provider `type` | Package | Behavior |
|---|---|---|
| `langchain_anthropic` | `langchain-anthropic` | Default; instantiate `ChatAnthropic` from config. |
| `langchain_openai` | optional `langchain-openai` | Dynamic import; if missing, return actionable config error. |
| `langchain_ollama` | optional `langchain-ollama` | Dynamic import; local model route; tests should not require Ollama running. |
| `mock` | in-repo fake | Deterministic structured outputs for contract tests. |

Use Pydantic structured outputs at the gate boundary. For current Anthropic/OpenAI-style providers, prefer `with_structured_output(PydanticModel, method="json_schema")` where supported and tested. Keep `include_raw=True` optional for debugging/token metadata, but return only validated gate models through capability results.

## Capability / CLI / MCP Integration Points

New registry records should be the only public invocation surface:

| Capability ID | CLI shape | MCP tool | Handler target |
|---|---|---|---|
| `research.search` | `construct research search ...` | `construct_research_search` | `construct.search` provider factory + adapter. |
| `research.score` | `construct research score ...` or internal-only in W2 | `construct_research_score` if public | `construct.llm.research_score.run_gate`. |
| `research.run` | `construct research run ...` | `construct_research_run` | `construct.pipelines.research.run_research_workflow`. |
| `curation.run` | `construct curation run ...` | `construct_curation_run` | `construct.pipelines.curation.run_curation_workflow`. |
| `card.evaluate` | `construct card evaluate ...` | `construct_card_evaluate` | `construct.llm.promotion_review` / card gate. |

Implementation requirements:

- Add Pydantic input models beside existing catalog models or in feature modules and import into `catalog.py`.
- Keep MCP tool names registered through `CapabilityRecord`; `src/construct/mcp/server.py` should continue auto-registering from the registry.
- CLI commands should call the registry just like v0.3 commands, not direct-import provider/graph internals.
- Capability outputs should be `OperationResult` with JSON-serializable `data`, including `review_required`, `run_id`, `gate_queue`/interrupt payloads, counts, and event IDs.
- Human approval should be expressible from CLI/MCP, not only Streamlit. Streamlit can render the same persistent review payloads.

## Thin Skill Migration Stack Rules

No new tool/runtime is needed for skill migration. The stack change is procedural:

| Skill | Current issue | v0.4 target |
|---|---|---|
| `construct-research-cycle` | `allowed-tools` includes `WebSearch`, `WebFetch`; skill performs search/extraction inline. | Remove `WebSearch`/`WebFetch`; allowed tools should be `Read, Bash(construct), MCP(connect)`; delegate to `research.search` / `research.run`. |
| `construct-curation-cycle` | Already thin-ish but points at placeholder workflow steps and some direct procedure text. | Delegate to `curation.run`; present report and pending review actions. |

Do not add Tavily MCP to the skill. That would bypass the CONSTRUCT capability registry and break CLI/MCP parity.

## Alternatives Considered

| Recommended | Alternative | When alternative makes sense | Why not for v0.4 default |
|---|---|---|---|
| Tavily SDK behind `SearchProvider` | Tavily MCP | External agent experimenting outside CONSTRUCT | Bypasses registry, no CLI parity, hard to contract-test as a CONSTRUCT capability. |
| Tavily SDK | `langchain-tavily` / `langchain-community` wrapper | If building a LangChain agent tool loop | CONSTRUCT needs normalized `SearchResult` contracts and provider swap; direct SDK is cleaner and avoids LC tool abstractions. |
| Tavily default | Brave Search API | Privacy/index diversification later | Requires separate adapter; useful as P2 provider, not necessary to prove W1. |
| Tavily default | Exa / Serper | Semantic/niche search experiments | Same interface slot later; not needed for baseline. |
| Tavily default + future academic provider | arXiv / Semantic Scholar first | If v0.4 narrows to academic-only papers | v0.4 needs general web research migration from Claude WebSearch; academic adapters can be second provider after spine is stable. |
| LangGraph + local SQLite checkpointer | Existing JSON `WorkflowRunner` only | Pure deterministic curation steps | Human-in-loop resume is a first-class LangGraph feature; JSON runner can wrap or mirror but should not reimplement graph interrupts. |
| SQLite checkpointer | Postgres/Redis/cloud checkpointer | Multi-user/server deployment | Out of scope; local-first single workspace should not add infra. |
| Direct provider classes + factory | Full LangChain `create_agent` | Open-ended autonomous tool agents | v0.4 gates are bounded structured judgments; full agent loops increase nondeterminism. |

## What NOT to Add

| Avoid | Why | Use Instead |
|---|---|---|
| Tavily MCP as a migrated skill dependency | Breaks registry/CLI/MCP parity and hides result contracts from tests. | Tavily Python SDK inside `src/construct/search/providers/tavily.py`. |
| Claude `WebSearch` / `WebFetch` in migrated research skill | Maintains Anthropic runtime lock-in and cannot be CI-tested. | `research.search` / `research.run` capabilities. |
| HTTP API / FastAPI / browser UI work | v0.5 scope; pulls UI-primary work ahead of workflow hardening. | CLI + MCP + existing Streamlit gate panel. |
| LangSmith deployment / Agent Server as required runtime | Cloud/service dependency conflicts with local-first milestone scope. | Local LangGraph graphs + SQLite checkpointer. Optional tracing can be env-only later. |
| Postgres, Redis, Celery, distributed workers | Unnecessary for local single-user workflow execution. | Synchronous CLI/MCP runs with durable local checkpoints. |
| Vector DB, embeddings, SQLite FTS dedup/indexer | Spec explicitly defers SQLite indexer/FTS dedup; v0.4 search dedup can be file-based. | URL/title dedup over `refs/`, cards, and simple normalized strings. |
| Playwright/Scrapy/crawler stack | Tavily already supplies search snippets and optional raw markdown/extract; browser crawling is scope creep. | Tavily `include_raw_content` / extract in a provider adapter if needed. |
| Secrets in YAML config | Project config is committed; API keys must not enter workspace or repo files. | Env vars such as `TAVILY_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. |
| LLM-driven tag extraction or validation | v0.3 explicitly keeps deterministic validation/tagging plain Python. | Existing Python validators and regex/category rules. |

## Stack Patterns by Phase Variant

**W1 — Search provider spine**
- Use `tavily-python`, Pydantic search models, mock provider, provider config.
- No LangGraph needed.
- Tests: fixture mapping, config resolution, no-key error, mock provider contract, CLI/MCP schema parity.

**W2 — Research score gate**
- Use `langchain-core` + provider factory + `langchain-anthropic` default.
- Add mock LLM provider for deterministic gate output tests.
- No SOT writes; gate output is `review_required: true` by default.

**W3 — Research run**
- Use LangGraph `StateGraph` + SQLite checkpointer.
- Use dynamic interrupts or an equivalent persistent review queue before ingest.
- Only `ingest.source` writes refs/cards after approval.

**W4/W5 — Curation run**
- Integrity, decay, orphan, report: plain Python using existing validate/graph/knowledge services.
- Promotion and connection typing: LangChain gates; LangGraph only where batch review/pause/resume matters.

**W6 — Daily cycle**
- Parent graph composes stabilized `research.run` and `curation.run`.
- No new stack; do not introduce UI/HTTP here.

## Version Compatibility / Gotchas

| Concern | Recommendation |
|---|---|
| Existing `pyproject.toml` lower bounds are stale-loose | `langgraph>=0.2` and `langchain-core>=0.3` can resolve broad API ranges. Tighten to current 1.x ranges before building new workflow APIs. |
| SQLite checkpointer is not bundled as `langgraph.checkpoint.sqlite` | Install `langgraph-checkpoint-sqlite`; otherwise only in-memory checkpointing is available. |
| LangGraph interrupts re-run nodes on resume | Keep non-idempotent SOT writes after approval/interrupt nodes, and separate side-effect nodes from review nodes. |
| LangGraph interrupt payloads must be serializable | Use Pydantic `model_dump(mode="json")`; no clients, Paths, functions, model instances, or exceptions in state. |
| Tavily `published_date` is not general-purpose metadata | Official docs tie it to news results. Treat date as optional and let L3/ingest metadata infer year/venue only when present or extracted. |
| Tavily `score` is provider relevance, not CONSTRUCT confidence | Store as `provider_score`; L3 gate produces `relevance_score`, source tier, and ingest action separately. |
| OpenAI/Ollama providers are configured but not installed today | Either move them to optional extras with dynamic import errors or add them to core. Recommendation: optional `providers` extra plus mock provider in tests. |
| `method="json_schema"` support varies by provider/model | Test each real provider route behind the factory; fallback/error clearly when unsupported. Do not silently parse free text. |

## Installation

After updating `pyproject.toml`:

```bash
# Refresh editable install with v0.4 runtime/test dependencies
.venv/bin/python -m pip install -e '.[dev]'

# Optional: install non-default model providers for local provider-swap testing
.venv/bin/python -m pip install -e '.[dev,providers]'
```

For real Tavily runs, set:

```bash
export TAVILY_API_KEY=tvly-...
export LANGGRAPH_STRICT_MSGPACK=true
```

CI and normal contract tests should not require `TAVILY_API_KEY`; they should use the mock provider and fixture JSON.

## Sources

| Source | What was verified | Confidence |
|---|---|---|
| `.planning/PROJECT.md` | v0.4 scope, active requirements, out-of-scope constraints. | HIGH |
| `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` | Target capabilities, LangGraph/LangChain split, search config, Tavily provider role, acceptance criteria. | HIGH |
| `.planning/milestones/v0.3-MILESTONE-AUDIT.md` | v0.3 shipped state and deferred debt relevant to workflows. | HIGH |
| `pyproject.toml` + installed package check | Current dependencies and observed installed versions. | HIGH |
| Context7 `/langchain-ai/langgraph/1.0.8` + official LangGraph docs (`overview`, `persistence`, `interrupts`, `checkpointers`) | LangGraph role, checkpointers, thread IDs, interrupts, durable execution, SQLite checkpointer separation. | HIGH |
| Official LangChain docs (`models`, `structured-output`, `ChatAnthropic integration`) | `with_structured_output`, provider packages, chat model interfaces, structured output considerations. | HIGH |
| Context7 `/tavily-ai/tavily-python` + official Tavily Python SDK reference | Tavily `search()` parameters, sync/async clients, result fields, `include_raw_content`, max results, response shape. | HIGH |
| PyPI JSON / package pages checked 2026-06-21 | Current versions: `langgraph` 1.2.6, `langchain-core` 1.4.8, `langchain-anthropic` 1.4.6, `tavily-python` 0.7.26, `langgraph-checkpoint-sqlite` 3.1.0, optional provider/test packages. | HIGH |

---
*Stack research for: CONSTRUCT v0.4 Agent Workflows*  
*Researched: 2026-06-21*
