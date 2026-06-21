# Project Research Summary

**Project:** CONSTRUCT
**Domain:** v0.4 Agent Workflows for a local-first, agent-powered knowledge system
**Researched:** 2026-06-21
**Confidence:** HIGH

## Executive Summary

CONSTRUCT v0.4 should be built as a workflow-runtime hardening milestone, not as a new UI/product-surface milestone. The research is consistent: preserve the current file-native workspace as the source of truth, keep deterministic validation/ingest/graph operations in Python, and move opaque Claude-native research and curation behavior behind registered CLI/MCP capabilities that thin skills can call.

The recommended approach is a narrow six-phase sequence: search provider spine, structured research scoring, durable reviewed research runs, deterministic curation PIPE steps, reviewed curation L3 gates, and only then daily-cycle composition. Use Tavily as the first real search adapter, but make the mock provider and normalized `SearchResult` contract the real interface. Use LangChain structured output for bounded gates and LangGraph only for stateful workflows that need pause/resume; do not use it for deterministic file I/O, validation, dedup, or graph metrics.

The core risks are provider lock-in, non-durable human review, writes before approval, fake curation no-ops, CLI/MCP drift, live-only tests, and premature daily-cycle/UI work. Mitigate them by enforcing provider factories, strict Pydantic contracts, durable gate queues, offline mock-provider tests, registry-first capability exposure, and a hard scope boundary: no v0.5 browser UI, HTTP/cloud transport, broad registry cleanup, full views emission, or unrelated verification debt in the v0.4 core unless it directly blocks these workflows.

## Key Findings

### Recommended Stack

Keep the existing Python/Pydantic/Typer/MCP/file-workspace spine. v0.4 adds only the workflow/search delta needed for model-agnostic research and curation: current LangGraph/LangChain 1.x bounds, Tavily's Python SDK behind a provider interface, durable local LangGraph checkpointing for human-review pauses, and explicit retry/backoff only where provider calls need it.

**Core technologies:**
- **Python `>=3.11`**: workflow/runtime implementation — no Python migration belongs inside v0.4.
- **Pydantic v2**: strict input/output schemas — all search, gate, review, and workflow models should use `extra="forbid"` and JSON-serializable fields.
- **Typer + capability registry**: golden CLI surface — every new workflow capability should invoke the same registry handler used by MCP.
- **MCP stdio**: agent invoke surface — parity with CLI is mandatory for `research.*`, `curation.*`, and `gate.*`.
- **LangGraph `>=1.2,<2`**: stateful workflows with interrupts/checkpoints — use for `research.run`, curation gates where pause/resume matters, and later daily-cycle composition.
- **`langgraph-checkpoint-sqlite >=3.1,<4`**: durable local checkpoints — required before shipping human-review LangGraph workflows; store under support/runtime state, not knowledge SOT.
- **LangChain Core `>=1.4,<2` + `langchain-anthropic >=1.4,<2`**: structured L2/L3 gate boundary — use provider factory and Pydantic structured output, not freeform agent loops.
- **`tavily-python >=0.7,<1`**: default real web search adapter — map once into normalized search models; CI uses mock/fixtures instead.
- **`tenacity >=9.1,<10`**: optional direct retry dependency — add only if provider retry/backoff is implemented.
- **`ruamel.yaml`, existing governance/model config**: YAML config loading — keep secrets in env vars, not workspace files.

**Critical version requirements:** tighten stale loose LangGraph/LangChain lower bounds before building workflow APIs; add `langgraph-checkpoint-sqlite` by the first durable human-review graph; do not add full `langchain`, HTTP frameworks, vector DBs, Postgres/Redis/Celery, Tavily MCP, or crawler stacks for v0.4 core.

### Expected Features

v0.4's feature promise is: the same governed workflow runs from CLI, MCP, Streamlit review, or thin Claude skills; search/LLM outputs are structured and reviewable; canonical writes only happen through validated services after required approval.

**Must have (table stakes):**
- **Search provider spine** — provider config, caps, normalized `SearchResult`/`SearchBatchOutput`, Tavily adapter, and mandatory mock provider.
- **`research.search`** — CLI/MCP capability returning the same normalized schema without LLM scoring or SOT writes.
- **`research.score`** — structured L3 gate producing relevance, source tier, key findings, ingest action, and reasoning under governance thresholds.
- **`research.run`** — search → dedup → score → durable human review → governed ingest → digest → seed/event updates.
- **Durable human review** — pending gates survive restart and can be approved/rejected through CLI/MCP, not only Streamlit.
- **Real `curation.run` PIPE steps** — integrity, decay, orphan scan, and report must be actual deterministic handlers, not v0.3 placeholders.
- **Curation promotion/connection gates** — L3 proposes lifecycle/edge changes; humans approve before writes.
- **CLI/MCP parity** — every new v0.4 capability has registry, CLI, MCP, and contract-test coverage.
- **Thin skill migrations** — research/curation skills delegate to capabilities and remove direct `WebSearch`/`WebFetch`/write orchestration when replacements are ready.
- **Workflow state/progress/events** — `awaiting_review`, degraded, failed, completed, gate IDs, run IDs, counts, and event IDs are visible and auditable.

**Should have (competitive / follow-on within v0.4):**
- Model/provider-agnostic gates with mockable provider factories.
- Review queues as first-class workflow state.
- Resilient partial-result behavior for provider failures and caps.
- Deterministic research digest, with optional L2 narrative only after structured digest fields exist.
- `workflow.daily_cycle` composition once research and curation are independently stable.
- Optional second provider/academic adapter after Tavily + mock prove the abstraction.

**Defer (v0.5+ / separate track):**
- Browser-primary UI, HTTP API, MCP SSE, cloud/multi-user deployment.
- Full co-authorship/authoring graph, unless W1-W6 finish cleanly.
- SQLite/FTS/vector indexer and broad provider suite.
- Full views data emission expansion; at most use an optional warning-only refresh hook.
- RT-01/RT-02 registry unification, general verification debt, and unrelated v0.3 cleanup unless a specific item blocks v0.4 workflow delivery.

### Architecture Approach

v0.4 should integrate as a Layer 2 workflow-runtime extension inside the existing architecture. Skills classify intent and present results; CLI/MCP invoke registry capabilities; registry handlers call Python pipelines; providers/gates return strict proposals; only reviewed deterministic services write canonical workspace files. The workspace format does not change.

**Major components:**
1. **Search provider spine** — `src/construct/search/` models, config, provider protocol/factory, Tavily adapter, mock adapter, fixture mapping tests.
2. **LLM provider factory** — shared model construction for `research.score`, `card.evaluate`, connection gates, and later `ask.domain` cleanup; no new hardcoded Anthropic imports in v0.4 gates.
3. **Research pipeline** — query building, caps, provider calls, dedup, score gate, gate queue, approved ingest, digest, seed/event updates.
4. **Curation pipeline** — real integrity/decay/orphan/report PIPE steps first, then promotion/connection L3 gates over deterministic candidates.
5. **Gate queue / review applier** — durable pending proposals, `gate.list`, `gate.review`, approval/rejection events, validated write application.
6. **Workflow state envelope** — keep `WorkflowRunner` as the public CONSTRUCT status/progress shape; adapt LangGraph checkpoints/interrupts behind it where needed.
7. **Capability registry + adapters** — `research.search`, `research.score`, `research.run`, `curation.run`, `card.evaluate`, `gate.list`, `gate.review`, and later daily-cycle exposed consistently through CLI/MCP.
8. **Thin Claude skills** — no direct provider calls, no direct SOT writes; invoke CLI/MCP and summarize results.

**Key patterns to follow:** registry-first entrypoints; provider interface + factory; gate-as-proposal, not gate-as-write; atomic validated SOT writes; offline contract tests with mock search/LLM providers; daily-cycle as parent composition only.

### Critical Pitfalls

1. **Provider abstraction leak** — avoid Tavily imports/fields in workflow code; map provider-native responses only inside the adapter and test provider swap with mock config.
2. **Model-agnostic gates that still hardcode Anthropic** — add a shared LLM provider factory before W2; tests monkeypatch the factory and require no real API key.
3. **Ungoverned LLM prose / writes before review** — gates must return strict Pydantic proposals, apply deterministic thresholds, persist pending review, and write SOT only after approve.
4. **Workflow state split-brain** — decide how `WorkflowRunner` wraps LangGraph checkpoints by W2/W3; expose one public run state with `awaiting_review`, gate IDs, child run IDs, and errors.
5. **Curation no-ops survive** — W4 must replace placeholder curation handlers with real validate/decay/orphan/report logic and tests that fail on `placeholder` output.
6. **CLI/MCP parity regressions** — every phase must extend registry, CLI, MCP handler invocation tests, and JSON output comparisons together.
7. **Live-only tests and weak negative coverage** — default pytest must pass offline; add fixtures for provider failure, invalid gate output, review rejection, duplicates, resume, and mid-batch failure.
8. **Premature daily-cycle/UI scope** — W6 only composes stable child capabilities; no v0.5 UI/HTTP/cloud/full views work in core v0.4.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase W1: Search Provider Spine + Contract Foundation
**Rationale:** Normalized, mockable search is the prerequisite for scoring, research runs, skill migration, and provider independence. Starting with full `research.run` would embed unstable provider semantics.
**Delivers:** `src/construct/search/`, `SearchResult`, `SearchBatchOutput`, search config resolution, env-only secret handling, query/result caps, mock provider, Tavily adapter, `research.search` registry/CLI/MCP, fixture mapping tests, no-network CI.
**Addresses:** Search provider spine, mockable provider, `research.search`, cost/rate caps, CLI/MCP parity.
**Avoids:** Provider abstraction leaks, config/secrets ambiguity, live-only tests, Tavily MCP bypass.
**Research flag:** Standard pattern; no extra phase research expected beyond checking current Tavily SDK behavior during implementation.

### Phase W2: LLM Provider Factory + `research.score`
**Rationale:** Scoring is the boundary between raw search and governed knowledge. Proving it independently keeps `research.run` from becoming opaque and prevents LLM prose from becoming ingest logic.
**Delivers:** Shared LLM provider factory, gate config entries, mock/fake LLM provider, `ResearchScoreInput/Output`, `ScoredFinding`, structured-output gate, governance threshold application, invalid-output tests.
**Addresses:** `research.score`, model-agnostic gates, epistemic scoring, source tier/action proposal, human-review metadata.
**Avoids:** Anthropic hardcoding, freeform LLM scoring, threshold duplication, writes before review.
**Research flag:** Mostly standard from docs; phase planning should decide exact structured-output fallback/error behavior per provider.

### Phase W3: Durable Human Review + `research.run`
**Rationale:** This is the first full workflow proof: provider → L3 gate → durable review → governed write. It should reuse W1/W2 contracts rather than define new ones.
**Delivers:** Gate queue storage, `gate.list`, `gate.review`, LangGraph/WorkflowRunner adapter, research run workflow, dedup/idempotency, approved ingest through existing services, deterministic digest, `search-seeds.json` updates, events, research skill migration removing `WebSearch`/`WebFetch`.
**Addresses:** `research.run`, human review, governed ingest, research digest, workflow state/pause/resume, deduplication, degraded partial results, thin research skill.
**Avoids:** Non-durable review, pre-approval writes, duplicate refs/cards, bad seed timestamps, batch partial-write ambiguity, Streamlit-only gates.
**Research flag:** Needs focused phase research/spike on `WorkflowRunner` + LangGraph checkpoint ownership and CLI approval UX before implementation locks storage semantics.

### Phase W4: Curation PIPE Steps
**Rationale:** Deterministic curation can and should be real before LLM promotion/connection gates. This closes the v0.3 placeholder/no-op debt without waiting on every L3 path.
**Delivers:** `curation.run` with real integrity, decay, orphan scan, report, optional warning-only views refresh hook, compatibility route from old `workflow.run curation-cycle`, no placeholder messages.
**Addresses:** Real curation PIPE, graph/workspace health reporting, workflow honesty, daily-cycle prerequisite.
**Avoids:** Curation no-ops, LLM overreach into validation/metrics, accidental dependency on API keys, false success reports.
**Research flag:** Standard deterministic Python/validation work; skip extra research unless current validation/graph services prove insufficient.

### Phase W5: Curation L3 Gates + Review Application
**Rationale:** Lifecycle and connection writes are high-impact epistemic changes. They should reuse W3's proven gate queue and W4's deterministic candidate evidence.
**Delivers:** `card.evaluate`, promotion decisions, connection/bridge proposal gate, candidate-scoped evidence prompts, approved lifecycle/connection writes through services, rejection no-op tests, curation skill migration.
**Addresses:** Curation promotion gate, connection maintenance gate, human approval for graph/lifecycle writes, thin curation skill.
**Avoids:** Autonomous promotions/connections, whole-workspace LLM curation, hardcoded model providers, partial batch writes, skill UX breakage.
**Research flag:** Needs phase-level design on candidate selection and relation/proposal semantics; does not need new provider-stack research.

### Phase W6: Daily-Cycle Composition
**Rationale:** Daily cycle is valuable only as composition of reliable child capabilities. Building it early would hide unfinished research/curation behavior and multiply state bugs.
**Delivers:** Parent workflow that calls `research.run`, waits/applies review as needed, calls `curation.run`, propagates child statuses/degraded states, reports `graph.status`, and optionally triggers one warning-only views refresh.
**Addresses:** Daily-cycle composition, unified progress/status, guided next action.
**Avoids:** Parent graph duplicating child logic, overwritten workflow state, double views refresh, success reports while children are awaiting review.
**Research flag:** Plan after W3/W5 acceptance data; deeper research only if parent/child LangGraph checkpointing remains unresolved.

### Phase Ordering Rationale

- Search contracts precede scoring because L3 gates must operate over provider-normalized data, not Tavily/Claude-native shapes.
- Scoring precedes research-run orchestration because gate schemas and thresholds must be independently testable before ingest is introduced.
- Durable review is introduced with research-run and then reused by curation; this avoids building separate review systems for Streamlit, CLI, MCP, and skills.
- Curation splits deterministic PIPE from L3 gates so validation/decay/orphan/report can land offline and stop v0.3 no-op behavior early.
- Skill migrations are tied to capability readiness: migrate research after W3 and curation after W5, not as standalone docs edits.
- Daily cycle comes last because it should compose stable child workflows and add no new search/scoring/curation logic.

### Research Flags

Phases likely needing deeper research or a focused spike during planning:
- **W3:** LangGraph checkpoint + `WorkflowRunner` ownership, durable gate queue storage shape, and non-interactive CLI review UX.
- **W5:** Curation candidate generation/proposal semantics for promotion and typed connections.
- **W6:** Parent/child workflow state only if W3/W5 leave checkpoint ownership ambiguous.

Phases with standard patterns (skip research-phase unless implementation uncovers a blocker):
- **W1:** Provider adapter + Pydantic model + fixture/mock testing is well documented.
- **W2:** Structured output gate + provider factory is well documented; validate exact provider behavior in tests.
- **W4:** Deterministic validation/decay/orphan/report handlers should reuse existing services and fixture tests.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official/current docs and package checks support LangGraph 1.x, LangChain structured output, Tavily SDK fields, and SQLite checkpointing; scope avoids speculative infra. |
| Features | HIGH | v0.4 behavior is strongly grounded in internal specs, user journeys, and v0.3 audit constraints; provider-specific UX details are less certain but not roadmap-blocking. |
| Architecture | HIGH | All research converges on Layer 2 runtime extension, registry-first contracts, provider factories, gate-as-proposal, and workspace SOT preservation. |
| Pitfalls | HIGH | Risks are repo-specific and mapped to concrete code/files/tests; severity estimates are MEDIUM where product impact depends on implementation choices. |

**Overall confidence:** HIGH

### Gaps to Address

- **Workflow state ownership:** Decide by W2/W3 whether `WorkflowRunner` wraps LangGraph or LangGraph replaces internals for migrated workflows; expose one public state schema either way.
- **Gate queue persistence format:** Choose support artifact/state shape, gate IDs, proposal action schema, and restart/resume semantics before W3 writes.
- **CLI approval UX:** Define `gate list --json`, `gate review --decision ...`, and any approve-batch/edit flow so Streamlit is optional.
- **Search seed update semantics:** Clarify whether `last_queried` means searched, approved, or ingested; do not advance failed/skipped clusters silently.
- **Curation candidate semantics:** Define deterministic evidence and candidate limits before L3 promotion/connection gates.
- **Batch mutation recovery:** Preflight all proposed writes, emit per-item + summary events, and make reruns idempotent rather than promising full rollback.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — recommended v0.4 stack delta, versions, provider/search/runtime rules.
- `.planning/research/FEATURES.md` — table stakes, differentiators, anti-features, dependencies, MVP definition.
- `.planning/research/ARCHITECTURE.md` — Layer 2 extension architecture, components, contracts, data flow, build order.
- `.planning/research/PITFALLS.md` — critical pitfalls, acceptance tests, phase warnings, recovery strategies.
- `.planning/PROJECT.md` — v0.4 milestone goals, constraints, and out-of-scope boundaries cited by researchers.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — authoritative workflow topology, capabilities, data structures, acceptance criteria.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — layer model, LLM tier boundaries, v0.4/v0.5 sequencing.
- `.planning/milestones/v0.3-MILESTONE-AUDIT.md` — shipped state and accepted v0.3 debt relevant to workflows.

### Secondary (MEDIUM confidence)
- Repo files cited by architecture/pitfalls research: `src/construct/capabilities/catalog.py`, `src/construct/pipelines/workflow_runner.py`, `src/construct/llm/ask_domain.py`, `src/construct/ui/gate_review.py`, ingestion/knowledge/validation services, MCP contract tests, current research/curation skill files.
- LangGraph docs via Context7 / official docs — StateGraph, interrupts, durable execution, checkpointers, SQLite checkpointer package.
- LangChain docs via Context7 / official docs — chat model interfaces and Pydantic/JSON Schema structured output.
- Tavily Python SDK docs — `search()` parameters and response fields (`title`, `url`, `content`, `score`, optional `raw_content`, `response_time`, `query`).

---
*Research completed: 2026-06-21*
*Ready for roadmap: yes*
