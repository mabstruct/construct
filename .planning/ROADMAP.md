# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first (v0.3), then migrates multi-step skill workflows to Python LangGraph/LangChain (v0.4), then delivers a browser-first UI-primary shell (v0.5) — without pulling UI work ahead of proven workflow and runtime behavior.

## Milestones

- ✅ **v0.3 Claude-Native Runtime & Workflow Hardening** — Phases 1–7 (shipped 2026-06-16)
- 📋 **v0.4 Agent Workflows (LangGraph / LangChain)** — planned (research/curation pipelines, model-agnostic search; see [`CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md))
- 📋 **v0.5 UI-Primary Experience** — planned (browser-first shell on the hardened v0.4 runtime)

## Phases

<details>
<summary>✅ v0.3 Claude-Native Runtime & Workflow Hardening (Phases 1–7) — SHIPPED 2026-06-16</summary>

Full phase detail (goals, success criteria, plans) archived in
[`milestones/v0.3-ROADMAP.md`](milestones/v0.3-ROADMAP.md). Milestone audit:
[`milestones/v0.3-MILESTONE-AUDIT.md`](milestones/v0.3-MILESTONE-AUDIT.md).

- [x] **Phase 1: Contract Canon & Artifact Governance** — canonize schemas, write gates, spec-aligned contracts (completed 2026-06-08)
- [x] **Phase 2: Governed Knowledge Operations** — reliable card/ref/connection/storage ops (completed 2026-06-10)
- [x] **Phase 3: Capability Registry, CLI & MCP Spine** — one shared runtime contract + stdio MCP server (completed 2026-06-12)
- [x] **Phase 4: Guided Workflow Operability** — state-aware help/ingestion/workflow runner + resume (completed 2026-06-10)
- [x] **Phase 5: Grounded Synthesis & Graph Reasoning** — bounded Q&A, synthesis, bridge detection (completed 2026-06-11)
- [x] **Phase 6: Derived Data, Ops UI & Governed Spikes** — view data contracts, Streamlit ops UI, governed spikes (completed 2026-06-11)
- [x] **Phase 7: Close v0.3 blockers** — RT-03 MCP schema parity, ING-02 ingest cluster validation, ING-05 graph.status wiring (completed 2026-06-16)

</details>

### 📋 v0.4 Agent Workflows (Planned)

Not yet scoped in GSD. Start with `/gsd-new-milestone` using
[`spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md) as the baseline requirements spec.

**Priority deliverables:** search provider spine (Tavily), `research.run`, `curation.run`, LangGraph/LangChain gates, thin skill migrations (remove Claude `WebSearch` from research cycle).

**Carry-over from v0.3 audit** (see `milestones/v0.3-MILESTONE-AUDIT.md`): curation-cycle placeholder steps, RT-01/RT-02 registry unification, `views.generate_data` stub, verification/Nyquist/security coverage gaps.

### 📋 v0.5 UI-Primary Experience (Planned)

Browser-first product shell on the v0.4 workflow runtime. HTTP API, capability buttons, LLM modals, extend v0.2 views SPA or CoPilotKit (decision deferred until v0.4 workflows stable).

Streamlit ops UI (v0.3) and view data contracts prepare this milestone; they do **not** replace it.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Contract Canon & Artifact Governance | v0.3 | 4/4 | Complete | 2026-06-08 |
| 2. Governed Knowledge Operations | v0.3 | 3/3 | Complete | 2026-06-10 |
| 3. Capability Registry, CLI & MCP Spine | v0.3 | 3/3 | Complete | 2026-06-12 |
| 4. Guided Workflow Operability | v0.3 | 4/4 | Complete | 2026-06-10 |
| 5. Grounded Synthesis & Graph Reasoning | v0.3 | 4/4 | Complete | 2026-06-11 |
| 6. Derived Data, Ops UI & Governed Spikes | v0.3 | 4/4 | Complete | 2026-06-11 |
| 7. Close v0.3 blockers (RT-03, ING-02, ING-05) | v0.3 | 3/3 | Complete | 2026-06-16 |
