# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first (v0.3), then migrates multi-step skill workflows to Python LangGraph/LangChain (v0.4), then delivers a browser-first UI-primary shell (v0.5) — without pulling UI work ahead of proven workflow and runtime behavior.

## Milestones

- ✅ **v0.3 Claude-Native Runtime & Workflow Hardening** — Phases 1–7 (shipped 2026-06-16)
- ✅ **v0.4 Agent Workflows (LangGraph / LangChain)** — Phases 8–13 (shipped 2026-07-07)
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

<details>
<summary>✅ v0.4 Agent Workflows (LangGraph / LangChain) (Phases 8–13) — SHIPPED 2026-07-07</summary>

Full phase detail (goals, success criteria, plans) archived in
[`milestones/v0.4-ROADMAP.md`](milestones/v0.4-ROADMAP.md).

**Milestone Goal:** Move CONSTRUCT's highest-value multi-step workflows from opaque Claude-native procedures into testable, model-agnostic LangGraph/LangChain pipelines while preserving the existing workspace format and current skill UX.

- [x] **Phase 8: Search Provider Spine + Contract Foundation** — provider-agnostic `research.search`, normalized search contracts, config/caps, degraded errors, and offline provider tests. (completed 2026-06-21)
- [x] **Phase 9: LLM Provider Factory + research.score** — model-agnostic structured scoring that turns normalized search results into governed finding proposals. (completed 2026-06-28)
- [x] **Phase 10: Durable Human Review + research.run** — reviewed, resumable research workflow with deduplication, approved ingest, digest, seed updates, and events. (completed 2026-06-28)
- [x] **Phase 11: Curation PIPE Steps** — real deterministic curation checks and reports replace v0.3 placeholder success responses. (completed 2026-06-29)
- [x] **Phase 12: Curation L3 Gates + Review Application** — promotion and connection proposals use reusable human review before canonical writes, with migrated skills. (completed 2026-07-05)
- [x] **Phase 13: Daily-Cycle Composition** — parent daily workflow composes stable research and curation capabilities with final CLI/MCP and compatibility parity. (completed 2026-07-07)

</details>

### 📋 v0.5 UI-Primary Experience (Planned)

Browser-first product shell on the v0.4 workflow runtime. HTTP API, capability buttons, LLM modals, extend v0.2 views SPA or CoPilotKit (decision deferred until v0.4 workflows stable).

Streamlit ops UI (v0.3) and view data contracts prepare this milestone; they do **not** replace it.

Define scope via `/gsd:new-milestone`.

## Coverage (v0.4 — shipped)

| Requirement group | Requirements | Phase(s) |
|-------------------|--------------|----------|
| Search Provider Spine | SRCH-01, SRCH-02, SRCH-03, SRCH-04 | Phase 8 |
| Research Workflow | RSCH-01, RSCH-02, RSCH-03, RSCH-04, RSCH-05 | Phases 9–10 |
| Curation Workflow | CUR-01, CUR-02, CUR-03, CUR-04, CUR-05 | Phases 11–12 |
| CONSTRUCT API And Runtime Parity | API-01, API-02, API-03, API-04, API-05 | Phases 12–13 |
| Daily-Cycle Composition | DAY-01, DAY-02, DAY-03 | Phase 13 |

**Coverage:** 22/22 v0.4 requirements mapped exactly once and delivered. Unmapped: 0. Unsatisfied: 0. Full detail archived in [`milestones/v0.4-REQUIREMENTS.md`](milestones/v0.4-REQUIREMENTS.md).

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
| 8. Search Provider Spine + Contract Foundation | v0.4 | 3/3 | Complete | 2026-06-21 |
| 9. LLM Provider Factory + research.score | v0.4 | 4/4 | Complete | 2026-06-28 |
| 10. Durable Human Review + research.run | v0.4 | 5/5 | Complete | 2026-06-28 |
| 11. Curation PIPE Steps | v0.4 | 3/3 | Complete | 2026-06-29 |
| 12. Curation L3 Gates + Review Application | v0.4 | 6/6 | Complete | 2026-07-05 |
| 13. Daily-Cycle Composition | v0.4 | 3/3 | Complete | 2026-07-07 |
