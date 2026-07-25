# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first (v0.3), then migrates multi-step skill workflows to Python LangGraph/LangChain (v0.4), then reconnects that runtime to the surfaces users and agents touch (v0.4.1), then delivers a browser-first UI-primary shell (v0.5) — without pulling UI work ahead of proven workflow and runtime behavior.

## Milestones

- ✅ **v0.3 Claude-Native Runtime & Workflow Hardening** — Phases 1–7 (shipped 2026-06-16)
- ✅ **v0.4 Agent Workflows (LangGraph / LangChain)** — Phases 8–13 (shipped 2026-07-07)
- ✅ **v0.4.1 Surface Integration & Documentation Truth** — Phases 14–17 (shipped 2026-07-25)
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
[`milestones/v0.4-ROADMAP.md`](milestones/v0.4-ROADMAP.md). Milestone audit:
[`milestones/v0.4-MILESTONE-AUDIT.md`](milestones/v0.4-MILESTONE-AUDIT.md).

**Milestone Goal:** Move CONSTRUCT's highest-value multi-step workflows from opaque Claude-native procedures into testable, model-agnostic LangGraph/LangChain pipelines while preserving the existing workspace format and current skill UX.

- [x] **Phase 8: Search Provider Spine + Contract Foundation** — provider-agnostic `research.search`, normalized search contracts, config/caps, degraded errors, and offline provider tests. (completed 2026-06-21)
- [x] **Phase 9: LLM Provider Factory + research.score** — model-agnostic structured scoring that turns normalized search results into governed finding proposals. (completed 2026-06-28)
- [x] **Phase 10: Durable Human Review + research.run** — reviewed, resumable research workflow with deduplication, approved ingest, digest, seed updates, and events. (completed 2026-06-28)
- [x] **Phase 11: Curation PIPE Steps** — real deterministic curation checks and reports replace v0.3 placeholder success responses. (completed 2026-06-29)
- [x] **Phase 12: Curation L3 Gates + Review Application** — promotion and connection proposals use reusable human review before canonical writes, with migrated skills. (completed 2026-07-05)
- [x] **Phase 13: Daily-Cycle Composition** — parent daily workflow composes stable research and curation capabilities with final CLI/MCP and compatibility parity. (completed 2026-07-07)

</details>

<details>
<summary>✅ v0.4.1 Surface Integration & Documentation Truth (Phases 14–17) — SHIPPED 2026-07-25</summary>

Full phase detail (goals, success criteria, plans) archived in
[`milestones/v0.4.1-ROADMAP.md`](milestones/v0.4.1-ROADMAP.md). Basis audit:
[`milestones/v0.4-MILESTONE-AUDIT.md`](milestones/v0.4-MILESTONE-AUDIT.md).

**Milestone Goal:** Reconnect the sound v0.4 runtime to the surfaces users and agents actually touch — every documented invocation path resolves and executes, the v0.4 runtime is discoverable by both users and agents, and the architecture doc set describes the system that actually exists. Integration defects in shipped work, not new capability.

- [x] **Phase 14: Durable-State & Config Truth** — settle the durable-checkpointer and LLM-config decisions and record them in the invariant docs; gates v0.5 design (DOC-03, FIX-02). (completed 2026-07-19)
- [x] **Phase 15: views.generate_data Resolution** — remove the permanent-failure stub from the MCP surface, vendor the views library, own post-run refresh in the Python layer (FIX-01, adr-0005). (completed 2026-07-20)
- [x] **Phase 16: Invocation & User-Doc Truth** — empty the `_KNOWN_BROKEN` allowlist, close the synthesis tool-grant exception, make the user doc set executable (FIX-03, DEC-01, DOC-04). (completed 2026-07-25)
- [x] **Phase 17: Architecture Doc Set & daily.run Discoverability** — rewrite the architecture inventory against the Phase 14–15 decisions and give the flagship daily cycle a chat entry point (DOC-01, DOC-02, UX-01). (completed 2026-07-25)

</details>

### 📋 v0.5 UI-Primary Experience (Planned)

Browser-first product shell on the v0.4 workflow runtime. HTTP API, capability buttons, LLM modals, extend v0.2 views SPA or CoPilotKit (decision deferred until scope is set).

Streamlit ops UI (v0.3) and view data contracts prepare this milestone; they do **not** replace it.

**Prerequisite satisfied:** DOC-03 landed in Phase 14 — the durable-checkpointer invariant is recorded, so a UI-primary shell can reason about resumable gate state. Define scope via `/gsd-new-milestone`.

**Known handoff items into v0.5 planning:** the `views validate` ↔ `views generate` byte-contract fork (pinned by test) needs an owner before SPA work; per-card refresh path and `card list` MCP-boundary hardening are logged follow-ups.

## Coverage (v0.4.1 — shipped)

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOC-03 | Phase 14 | Complete |
| FIX-02 | Phase 14 | Complete |
| FIX-01 | Phase 15 | Complete |
| FIX-03 | Phase 16 | Complete |
| DEC-01 | Phase 16 | Complete |
| DOC-04 | Phase 16 | Complete |
| DOC-01 | Phase 17 | Complete |
| DOC-02 | Phase 17 | Complete |
| UX-01 | Phase 17 | Complete |

**Coverage:** 9/9 v0.4.1 requirements mapped exactly once and delivered. Unmapped: 0. Duplicated: 0. Full detail archived in [`milestones/v0.4.1-REQUIREMENTS.md`](milestones/v0.4.1-REQUIREMENTS.md).

**Not mapped (by design):** FIX-04 — delivered 2026-07-19 ahead of the milestone (commit `11f20f4`), the pre-milestone guard whose `_KNOWN_BROKEN` allowlist supplied the mechanical completion criteria for Phases 15 and 16.

## Coverage (v0.4 — shipped)

| Requirement group | Requirements | Phase(s) |
|-------------------|--------------|----------|
| Search Provider Spine | SRCH-01, SRCH-02, SRCH-03, SRCH-04 | Phase 8 |
| Research Workflow | RSCH-01, RSCH-02, RSCH-03, RSCH-04, RSCH-05 | Phases 9–10 |
| Curation Workflow | CUR-01, CUR-02, CUR-03, CUR-04, CUR-05 | Phases 11–12 |
| CONSTRUCT API And Runtime Parity | API-01, API-02, API-03, API-04, API-05 | Phases 12–13 |
| Daily-Cycle Composition | DAY-01, DAY-02, DAY-03 | Phase 13 |

**Coverage:** 22/22 v0.4 requirements mapped exactly once and delivered. Full detail archived in [`milestones/v0.4-REQUIREMENTS.md`](milestones/v0.4-REQUIREMENTS.md).

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
| 14. Durable-State & Config Truth | v0.4.1 | 4/4 | Complete | 2026-07-19 |
| 15. views.generate_data Resolution | v0.4.1 | 5/5 | Complete | 2026-07-20 |
| 16. Invocation & User-Doc Truth | v0.4.1 | 7/7 | Complete | 2026-07-25 |
| 17. Architecture Doc Set & daily.run Discoverability | v0.4.1 | 4/4 | Complete | 2026-07-25 |
