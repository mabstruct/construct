# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first (v0.3), then migrates multi-step skill workflows to Python LangGraph/LangChain (v0.4), then delivers a browser-first UI-primary shell (v0.5) — without pulling UI work ahead of proven workflow and runtime behavior.

## Milestones

- ✅ **v0.3 Claude-Native Runtime & Workflow Hardening** — Phases 1–7 (shipped 2026-06-16)
- 🚧 **v0.4 Agent Workflows (LangGraph / LangChain)** — Phases 8–13 (ready to plan)
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

### 🚧 v0.4 Agent Workflows (Phases 8–13 — Ready to Plan)

**Milestone Goal:** Move CONSTRUCT's highest-value multi-step workflows from opaque Claude-native procedures into testable, model-agnostic LangGraph/LangChain pipelines while preserving the existing workspace format and current skill UX.

- [x] **Phase 8: Search Provider Spine + Contract Foundation** — provider-agnostic `research.search`, normalized search contracts, config/caps, degraded errors, and offline provider tests. (completed 2026-06-21)
- [x] **Phase 9: LLM Provider Factory + research.score** — model-agnostic structured scoring that turns normalized search results into governed finding proposals. (completed 2026-06-28)
- [x] **Phase 10: Durable Human Review + research.run** — reviewed, resumable research workflow with deduplication, approved ingest, digest, seed updates, and events. (completed 2026-06-28)
- [x] **Phase 11: Curation PIPE Steps** — real deterministic curation checks and reports replace v0.3 placeholder success responses. (completed 2026-06-29)
- [ ] **Phase 12: Curation L3 Gates + Review Application** — promotion and connection proposals use reusable human review before canonical writes, with migrated skills.
- [ ] **Phase 13: Daily-Cycle Composition** — parent daily workflow composes stable research and curation capabilities with final CLI/MCP and compatibility parity.

### 📋 v0.5 UI-Primary Experience (Planned)

Browser-first product shell on the v0.4 workflow runtime. HTTP API, capability buttons, LLM modals, extend v0.2 views SPA or CoPilotKit (decision deferred until v0.4 workflows stable).

Streamlit ops UI (v0.3) and view data contracts prepare this milestone; they do **not** replace it.

## Phase Details

### Phase 8: Search Provider Spine + Contract Foundation

**Goal**: Users and agents can run provider-agnostic research search through the existing CONSTRUCT contract without workspace source-of-truth writes.
**Depends on**: Phase 7
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04
**Success Criteria** (what must be TRUE):

  1. User can run `research.search` from the `construct` CLI and stdio MCP server through the shared capability registry and receive normalized search results without refs/cards/seeds/events source-of-truth writes.
  2. Developer can configure search provider selection, API-key environment variables, query caps, and result caps without changing workflow code.
  3. Developer can run the search contract test suite offline with a mock provider and fixture responses.
  4. User receives structured degraded-state errors when a provider fails, times out, or hits configured caps.

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Search module core: SearchConfig schema, errors, ABC, mock provider, factory

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-02-PLAN.md — Capability wiring: research.search handler, registry, CLI, config load/validation/init

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 08-03-PLAN.md — Contract tests, MCP parity update, Tavily adapter, full regression

### Phase 9: LLM Provider Factory + research.score

**Goal**: Users can turn normalized search results into governance-aware finding proposals through a model-agnostic scoring gate.
**Depends on**: Phase 8
**Requirements**: RSCH-01
**Success Criteria** (what must be TRUE):

  1. User can run `research.score` from the `construct` CLI and stdio MCP server through the shared capability registry.
  2. User receives structured finding proposals with relevance score, source tier, ingest action, and reasoning for each scored search result.
  3. User can see governance thresholds reflected in `skip`, `ref_only`, and `ref_and_card` recommendations before any workspace writes occur.
  4. Developer can verify the score gate offline with mock LLM providers, invalid-output fixtures, and degraded-state tests.

**Plans**: 4 plans (4 waves — sequential dependency chain: factory → gate core → fan-out/degraded → CLI/MCP surface)

Plans:
**Wave 1**

- [x] 09-01-PLAN.md — LLM provider factory + ask.domain retrofit + [BLOCKING] regression guard (D-01/D-02)

**Wave 2** *(blocked on Wave 1)*

- [x] 09-02-PLAN.md — research.score schema, single-result scoring, governance clamp, taxonomy steering (D-05/06/07/11/12/14)

**Wave 3** *(blocked on Wave 2)*

- [x] 09-03-PLAN.md — bounded fan-out, per-item retry+skip, total-outage promotion, run_gate runner (D-04/08/09)

**Wave 4** *(blocked on Wave 3)*

- [x] 09-04-PLAN.md — capability registration + CLI table / MCP parity surface (D-10/13)

### Phase 10: Durable Human Review + research.run

**Goal**: Users can run research as a durable reviewed workflow that ingests only approved findings and can resume safely.
**Depends on**: Phase 9
**Requirements**: RSCH-02, RSCH-03, RSCH-04, RSCH-05
**Success Criteria** (what must be TRUE):

  1. User can run `research.run` from the `construct` CLI and stdio MCP server to execute search, deduplication, scoring, review, approved ingest, digest creation, seed updates, and event logging as one workflow.
  2. User can review, approve, or reject research findings before any refs, cards, seed timestamps, or digest artifacts are written.
  3. User can resume or inspect a paused research workflow with pending review state preserved across process restarts.
  4. User can rerun research safely without duplicating URLs, refs, rejected findings, or partially completed batch writes.
  5. User can see run status, gate IDs, approved ingest counts, digest path, seed update status, and emitted events in the workflow result.

**Plans**: 5 plans (4 waves)

Plans:
**Wave 1** *(parallel — no file overlap)*

- [x] 10-01-PLAN.md — Wave 0 foundation: install langgraph-checkpoint-sqlite, .construct/ gitignore + D-02 carve-out, failing Nyquist suite (RSCH-02..05)
- [x] 10-02-PLAN.md — Idempotency primitives: normalize_url, deterministic ref-ID, title-fuzzy, rejected ledger (RSCH-05)

**Wave 2** *(blocked on Wave 1)*

- [x] 10-03-PLAN.md — Workflow read-side: state + I/O models, pre-gate nodes, interrupt gate, checkpointed graph, pause (RSCH-02/03/04)

**Wave 3** *(blocked on Wave 2)*

- [x] 10-04-PLAN.md — Workflow write-side: idempotent ingest, template digest+record, seed/events, review/inspect runners, cross-process resume (RSCH-02/03/04/05)

**Wave 4** *(blocked on Wave 3)*

- [x] 10-05-PLAN.md — Capability registration + CLI + MCP parity + contract/regression tests (RSCH-02/03/04)

### Phase 11: Curation PIPE Steps

**Goal**: Users can run curation and receive real deterministic integrity, decay, orphan, connection-health, and report results instead of placeholder success responses.
**Depends on**: Phase 10
**Requirements**: CUR-01
**Success Criteria** (what must be TRUE):

  1. User can run `curation.run` from the `construct` CLI and stdio MCP server and receive real integrity, decay, orphan, connection-health, and report output.
  2. User can distinguish completed deterministic checks, degraded checks, and skipped optional views refresh in the curation result.
  3. User no longer receives placeholder success messages for deterministic curation steps; each reported step includes concrete findings, counts, or an explicit degraded/skipped state.

**Plans**: 3 plans (3 waves — sequential: Wave-0 red tests → curation_run module → CLI/MCP wiring)

Plans:
**Wave 1**

- [x] 11-01-PLAN.md — Wave-0 failing suite: test_curation_run.py + test_curation_run_cli_mcp.py + conftest decay/orphan fixtures

**Wave 2** *(blocked on Wave 1)*

- [x] 11-02-PLAN.md — curation_run.py: CurationStepResult/RunResult contract, linear §4.3 graph, 5 real steps + 3 deferred skips, SqliteSaver, run/inspect runners, D-09 aggregation

**Wave 3** *(blocked on Wave 2)*

- [x] 11-03-PLAN.md — catalog registration + dual-mode shims + curation Typer sub-app + CLI/MCP parity + API-05 regression

### Phase 12: Curation L3 Gates + Review Application

**Goal**: Users can review lifecycle and connection proposals before any high-impact curation writes occur, and research/curation skills delegate to the runtime.
**Depends on**: Phase 11
**Requirements**: CUR-02, CUR-03, CUR-04, CUR-05, API-04
**Success Criteria** (what must be TRUE):

  1. User can run a structured `card.evaluate` gate that proposes promote, hold, or escalate decisions with evidence.
  2. User can approve or reject lifecycle and connection proposals before canonical card or connection writes occur.
  3. User can inspect curation workflow status, degraded states, pending reviews, review outcomes, and emitted events for deterministic steps and review gates.
  4. Developer can verify curation behavior offline with tests that fail if placeholder handlers or unreviewed canonical writes remain.
  5. User can run migrated research and curation Claude-native skills that delegate to CLI/MCP capabilities instead of direct `WebSearch`, `WebFetch`, or workspace writes.

**Plans**: 6 plans (6 waves — linear graft chain: tests -> gates -> graph read-side -> graph write-side -> registry/CLI -> skills)

Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Wave 0 failing-test scaffold: gate unit tests + HITL/reviewed-write integration tests + CLI/MCP parity + no-placeholder + skill-migration guards + conftest mock seams
**Wave 2** *(blocked on Wave 1)*

- [ ] 12-02-PLAN.md — Two L3 LLM gates: card.evaluate (curation_promote.py) + connection-typing (curation_connect.py) + config.yaml gate entries
**Wave 3** *(blocked on Wave 2)*

- [ ] 12-03-PLAN.md — curation_run.py read-side: gate_queue state + CurationProposal + producer nodes + interrupt-only process_inbox + empty-queue short-circuit + awaiting_review status
**Wave 4** *(blocked on Wave 3)*

- [ ] 12-04-PLAN.md — curation_run.py write-side: apply_promotions/connections/archives + decision resolution + review_curation_run + extended inspect + events
**Wave 5** *(blocked on Wave 4)*

- [ ] 12-05-PLAN.md — Registry + CLI: register card.evaluate + curation.review, extend curation.inspect, add `curation review` command, remove D-10 placeholder lambdas from catalog.py + cli.py
**Wave 6** *(blocked on Wave 5)*

- [ ] 12-06-PLAN.md — Skill migration (API-04): research-cycle + curation-cycle + card-evaluate become thin orchestrators; human-verify the review loop

### Phase 13: Daily-Cycle Composition

**Goal**: Users can run a daily maintenance workflow that composes stable research and curation capabilities while proving final registry, CLI/MCP, and v0.3 compatibility parity.
**Depends on**: Phase 12
**Requirements**: DAY-01, DAY-02, DAY-03, API-01, API-02, API-03, API-05
**Success Criteria** (what must be TRUE):

  1. User can run a daily-cycle workflow from the `construct` CLI and stdio MCP server that composes stable research and curation child workflows instead of duplicating their logic.
  2. User can see parent and child workflow status, pending reviews, degraded states, and final graph-health summary in the daily-cycle result.
  3. User can run daily-cycle safely when research or curation pauses for review, fails partially, or skips optional views refresh without receiving a false completed result.
  4. User and agent can invoke every new v0.4 workflow capability through the same registry-backed handler from CLI and MCP, and developer can verify registry metadata plus CLI/MCP schema/result parity for research, curation, gate, and daily-cycle capabilities.
  5. Existing v0.3 CLI, MCP, Streamlit, validation, ingestion, graph, and ask-domain behavior continues to pass after all v0.4 workflow capabilities are added.

**Plans**: TBD

## Coverage

| Requirement group | Requirements | Phase(s) |
|-------------------|--------------|----------|
| Search Provider Spine | SRCH-01, SRCH-02, SRCH-03, SRCH-04 | Phase 8 |
| Research Workflow | RSCH-01, RSCH-02, RSCH-03, RSCH-04, RSCH-05 | Phases 9–10 |
| Curation Workflow | CUR-01, CUR-02, CUR-03, CUR-04, CUR-05 | Phases 11–12 |
| CONSTRUCT API And Runtime Parity | API-01, API-02, API-03, API-04, API-05 | Phases 12–13 |
| Daily-Cycle Composition | DAY-01, DAY-02, DAY-03 | Phase 13 |

**Coverage:** 22/22 v0.4 requirements mapped exactly once. Unmapped: 0.

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
| 8. Search Provider Spine + Contract Foundation | v0.4 | 3/3 | Complete   | 2026-06-21 |
| 9. LLM Provider Factory + research.score | v0.4 | 4/4 | Complete   | 2026-06-28 |
| 10. Durable Human Review + research.run | v0.4 | 5/5 | Complete    | 2026-06-28 |
| 11. Curation PIPE Steps | v0.4 | 3/3 | Complete    | 2026-06-29 |
| 12. Curation L3 Gates + Review Application | v0.4 | 1/6 | In Progress|  |
| 13. Daily-Cycle Composition | v0.4 | 0/TBD | Not started | - |
