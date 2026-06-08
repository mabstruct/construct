# Project Research Summary

**Project:** CONSTRUCT
**Domain:** Local-first, agent-powered personal knowledge system
**Researched:** 2026-06-08
**Confidence:** HIGH

## Executive Summary

CONSTRUCT is not a generic notes app and should not be rebuilt as one. The research consistently points to a governed, local-first knowledge system whose core value is turning source material into durable knowledge cards, typed graph connections, and grounded outputs, while making the next sensible action obvious to the user. Experts would build this by preserving files as the canonical source of truth, hardening contracts first, and only then layering runtime adapters and UI on top.

The recommended approach is to use v0.3 to stabilize the shared contract spine: Pydantic schemas, capability registry, deterministic Python handlers, CLI-first execution, MCP parity for Claude-native workflows, bounded LangGraph gates only where judgment is needed, and optional HTTP/UI later. The roadmap should prioritize reliability, operability, and auditability over surface expansion.

The biggest risks are contract drift, ambiguous graph truth, soft validation, incomplete event logging, and letting UI or prompts become alternate runtimes. Mitigate them by canonizing schemas, enforcing write gates and idempotent mutations, choosing one owner for graph edges, making `events.jsonl` authoritative, and ensuring all writes flow through registered capabilities rather than direct file edits or prompt-shaped behavior.

## Key Findings

### Recommended Stack

The stack research is unusually aligned with the repo's stated direction: Python 3.12 + uv + pytest + Pydantic should be the v0.3 core, with Typer as the golden CLI surface, MCP as the Claude-facing transport, FastAPI deferred until contracts are stable, and LangGraph limited to read-mostly or review-gated judgment flows. Markdown/YAML/JSON remain canonical; SQLite FTS is optional later, never day-one.

**Core technologies:**
- **Python 3.12**: runtime for deterministic pipelines and adapters — modern baseline without forcing a larger rewrite.
- **uv**: package/dependency/tool runner — fastest path to a clean local Python workflow.
- **Pydantic 2.x**: canonical contract layer — should define workspace, capability, adapter, and gate schemas once.
- **Typer**: CLI surface — best first invoke path for testing and operability.
- **MCP Python SDK**: Claude/Cursor tool transport — keeps Claude-native workflows while moving logic into stable tools.
- **LangGraph**: bounded LLM orchestration — use only for `ask.domain`, synthesis/review gates, and ambiguous decisions.
- **FastAPI**: future HTTP adapter — add after CLI and MCP schema parity exists.

### Expected Features

Near-term scope is about making the current proof of concept dependable and legible, not broadening the product surface. Table-stakes features center on reliable workspace initialization, governed card/ref/connection operations, validation, research/curation/synthesis loops, graph health, gap analysis, session resumption, and next-step guidance.

**Must have (table stakes):**
- Reliable workspace initialization and guided domain setup.
- Consistent card creation/edit/archive and typed connection management.
- Workspace validation and data-contract enforcement.
- Repeatable research cycle, curation cycle, and grounded synthesis flow.
- Graph health reporting, gap analysis, session resumption, and help/next-step guidance.
- Confidence/source-tier propagation in outputs.

**Should have (competitive):**
- Epistemically governed cards as a first-class invariant.
- Agent-orchestrated research → curation → synthesis loop.
- Governed graph health workflows and state-aware next-step suggestions.
- Cross-domain bridge detection once graph integrity is trustworthy.
- Derived wiki/views over the same file-native workspace.

**Defer (v2+ / later phases):**
- Full browser-first product shell.
- Rich graph visualization as a phase driver.
- Vector search as foundational work.
- Multi-user/cloud sync, broad integrations, plugin ecosystems, and aggressive automation.

### Architecture Approach

Architecture research strongly supports the ADR-0003 spine: workspace files first, Python runtime second, invoke adapters third, UI shell last. The system should expose one capability contract through CLI, MCP, and later HTTP; keep files as canonical state; use LangGraph only at named gates; require human review before model-authored source-of-truth changes; and keep the UI above the runtime rather than letting it write directly.

**Major components:**
1. **Workspace SOT** — canonical markdown/YAML/JSON knowledge state and audit trail.
2. **Capability registry + runtime handlers** — shared schemas, validation, file I/O, graph ops, view generation.
3. **Adapters (CLI → MCP → HTTP)** — thin invoke surfaces over the same contracts.
4. **Workflow runner + event logger** — multi-step orchestration with replayable progress.
5. **LangGraph gates** — bounded, typed judgment steps only.
6. **Derived-data/UI layer** — consumes backend outputs, never writes canonical files directly.

### Critical Pitfalls

1. **Contract drift** — prevent with one canonical schema source and a contract-change checklist across templates, validators, skills, views, and runtime.
2. **Dual graph truth** — choose one canonical edge store and make any second representation derived-only.
3. **Advisory validation** — replace checklist validation with enforced preflight/post-write gates, staged mutations, and idempotent commands.
4. **Non-authoritative event logging** — define a versioned event schema and require all mutations to pass through one evented command path.
5. **Prompt-shaped tool boundaries / UI-first writes** — keep deterministic work in typed commands and require UI, Claude skills, and later API routes to invoke the same backend capabilities.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Contract Canon and Data Model Hardening
**Rationale:** Every source agrees the main current risk is inconsistency, not missing features.
**Delivers:** Canonical schemas for cards/refs/connections/events, artifact ownership rules, single graph-edge truth, contract docs, invariant tests.
**Addresses:** Workspace validation, template consistency, reliable artifact generation.
**Avoids:** Contract drift, dual graph truth, early UI/runtime rework.

### Phase 2: Deterministic Runtime and Golden CLI
**Rationale:** Once contracts are stable, the safest next step is a testable backend surface.
**Delivers:** Capability registry, Python handlers, atomic/idempotent write wrappers, `workspace.validate`, `graph.status`, derived-data generation, CLI contract tests.
**Uses:** Python 3.12, uv, Pydantic, Typer, pytest.
**Implements:** Runtime core, event schema, audit boundaries.

### Phase 3: Claude-Native Workflow Migration via MCP
**Rationale:** Preserve current UX while reducing prompt fragility.
**Delivers:** MCP stdio server with exact schema parity, thin skill adapters, session resumption/state-aware help, stable next-step guidance.
**Addresses:** Workflow operability, continuity, guidance.
**Avoids:** Too much agent discretion at the tool boundary.

### Phase 4: Workflow Orchestration, Research/Curation Reliability, and Eventing
**Rationale:** Multi-step workflows become safer after atomic operations work.
**Delivers:** Workflow runner, structured progress events, hardened research/curation/synthesis flows, governance enforcement, reconciliation tooling.
**Addresses:** Research cycle, curation cycle, auditability, confidence propagation.
**Avoids:** Advisory validation, event-log theater, stale workflow choreography.

### Phase 5: Bounded LangGraph Gates and Graph Leverage
**Rationale:** Add LLM statefulness only where deterministic systems are insufficient.
**Delivers:** `ask.domain`, grounded synthesis/review gates, better gap analysis, bridge detection, citation-rich outputs.
**Uses:** LangGraph behind typed I/O boundaries.
**Avoids:** LLM overreach into deterministic paths.

### Phase 6: UI-Path Preparation and Local Ops Shell
**Rationale:** UI should consume proven contracts, not define them.
**Delivers:** Derived-data contracts, optional Streamlit ops spike, HTTP planning, freshness/provenance semantics for later React/Vite UI.
**Addresses:** Future browser path without pulling UI work too early.
**Avoids:** Building the UI on chat-era workflows or hidden derived-state truth.

### Phase Ordering Rationale

- Contracts must precede runtime because every feature depends on shared artifact semantics.
- Runtime and CLI should precede MCP and UI because they are the cheapest place to prove schemas, errors, idempotency, and eventing.
- Workflow orchestration should follow atomic capability hardening so composition is safe.
- LangGraph should remain late and bounded so model complexity does not contaminate deterministic foundations.
- UI-path work should come last because v0.4 value depends on backend stability, not vice versa.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** graph-edge canonicalization decision, because current dual-truth model has real downstream consequences.
- **Phase 4:** event schema + mutation/audit design, because replayability and recovery semantics must be explicit.
- **Phase 5:** retrieval/indexing envelope for `ask.domain`, bridge detection, and scale limits.
- **Phase 6:** HTTP/derived-data contract design for the v0.4 UI path.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Python runtime + Typer CLI + Pydantic contract enforcement are well-documented patterns.
- **Phase 3:** MCP schema-parity transport is a standard migration once capability contracts are fixed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong alignment between repo constraints and current official tooling guidance; only v0.4 UI detail is less settled. |
| Features | HIGH | Near-term scope is clear and heavily grounded in PROJECT.md and current product docs. |
| Architecture | HIGH | ADR-0003 and supporting docs produce a coherent, low-risk build order. |
| Pitfalls | HIGH | Risks are repo-specific, concrete, and repeated across current docs and workflow behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **Canonical edge ownership:** decide whether `connections.json` or card frontmatter owns graph truth before phase planning locks APIs.
- **Event contract details:** define required event types, payload shape, and reconciliation rules before workflow implementation.
- **Mutation/concurrency semantics:** plan atomic writes, serialization/locking, and recovery expectations for local-first multi-writer scenarios.
- **Retrieval/index threshold:** define when file-backed retrieval stops being enough and when SQLite FTS becomes justified.
- **v0.4 UI contract boundary:** validate which derived artifacts and progress semantics the browser layer should rely on.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — milestone goals, constraints, scope, continuity requirements.
- `.planning/research/STACK.md` — recommended runtime, adapter, and UI-path stack.
- `.planning/research/FEATURES.md` — table stakes, differentiators, and deferrals.
- `.planning/research/ARCHITECTURE.md` — layered architecture, component boundaries, build order.
- `.planning/research/PITFALLS.md` — repo-specific failure modes and sequencing warnings.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` and related spec docs cited by the research files.

### Secondary (MEDIUM confidence)
- Official docs cited in research: uv, FastAPI, Pydantic, Typer, MCP, LangGraph, Streamlit, React Flow, TanStack Query.
- Anthropic tool-use and guardrail docs cited in pitfalls research.
- Ink & Switch local-first essay cited for long-term local-first risk framing.

---
*Research completed: 2026-06-08*
*Ready for roadmap: yes*
