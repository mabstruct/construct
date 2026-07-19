# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first (v0.3), then migrates multi-step skill workflows to Python LangGraph/LangChain (v0.4), then reconnects that runtime to the surfaces users and agents touch (v0.4.1), then delivers a browser-first UI-primary shell (v0.5) — without pulling UI work ahead of proven workflow and runtime behavior.

## Milestones

- ✅ **v0.3 Claude-Native Runtime & Workflow Hardening** — Phases 1–7 (shipped 2026-06-16)
- ✅ **v0.4 Agent Workflows (LangGraph / LangChain)** — Phases 8–13 (shipped 2026-07-07)
- 🚧 **v0.4.1 Surface Integration & Documentation Truth** — Phases 14–17 (active)
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

### 🚧 v0.4.1 Surface Integration & Documentation Truth (Phases 14–17) — ACTIVE

**Milestone Goal:** Reconnect the sound v0.4 runtime to the surfaces users and agents actually touch — every documented invocation path resolves and executes, the v0.4 runtime is discoverable by both users and agents, and the architecture doc set describes the system that actually exists.

**Nature:** integration defects in shipped work, not new capability. No phase here adds runtime capability. Basis: [`milestones/v0.4-MILESTONE-AUDIT.md`](milestones/v0.4-MILESTONE-AUDIT.md).

**Pre-milestone deliverable:** FIX-04 shipped 2026-07-19 (`tests/contract/test_doc_command_references.py`, commit `11f20f4`). Its `_KNOWN_BROKEN` allowlist can only shrink and is the mechanical completion criterion for Phases 15 and 16.

- [ ] **Phase 14: Durable-State & Config Truth** — settle the durable-checkpointer and LLM-config decisions and record them in the invariant docs; gates v0.5 design and every downstream doc rewrite.
- [ ] **Phase 15: views.generate_data Resolution** — remove the permanent-failure stub from the MCP surface and make all four documented callers consistent with the decision.
- [ ] **Phase 16: Invocation & User-Doc Truth** — empty the `_KNOWN_BROKEN` allowlist, close the synthesis tool-grant exception, and make the user doc set executable.
- [ ] **Phase 17: Architecture Doc Set & daily.run Discoverability** — rewrite the architecture inventory against the decisions from Phases 14–15 and give the flagship daily cycle a chat entry point.

### 📋 v0.5 UI-Primary Experience (Planned)

Browser-first product shell on the v0.4 workflow runtime. HTTP API, capability buttons, LLM modals, extend v0.2 views SPA or CoPilotKit (decision deferred until v0.4 workflows stable).

Streamlit ops UI (v0.3) and view data contracts prepare this milestone; they do **not** replace it.

**Blocked on:** DOC-03 (Phase 14). Define scope via `/gsd:new-milestone` once Phase 14 lands.

## Phase Details

### Phase 14: Durable-State & Config Truth

**Goal**: A v0.5 planner and a developer configuring LLM behavior each find exactly one true, recorded answer about where durable state and configuration live.
**Depends on**: Nothing (first phase of v0.4.1)
**Requirements**: DOC-03, FIX-02
**Success Criteria** (what must be TRUE):

  1. `nfrs.md` §2 and `architecture-overview.md:243` no longer assert that no database owns part of the truth and no derived state is required; both name `.construct/workflow/*.sqlite` as intentional durable state holding pending human-review decisions that are not reconstructible from layer 1.
  2. `workspace-contract.md` lists `.construct/workflow/*.sqlite`, `.construct/search.yaml`, and `WORKSPACE.md` among workspace artifacts, and `nfrs.md` §4 names Tavily instead of asserting "Third-party APIs: None".
  3. The Streamlit ops UI's LLM config path default resolves to the file the runtime actually reads — `ui/streamlit_app.py`'s default agrees with `llm/config.py`'s resolution order (including the `CONSTRUCT_LLM_CONFIG` override).
  4. `model-routing.yaml` has exactly one recorded fate: either it is gone from `services/init.py` new-workspace scaffolding, or it is scaffolded and marked deprecated in every doc that currently calls it authoritative (`workspace-contract.md` Support table, `config-topology.md:56,135`).
  5. Full pytest suite green (≥439 tests) with no new `_KNOWN_BROKEN` entries.

**Plans**: 2/4 plans executed
**Wave 1**

- [x] 14-01-PLAN.md — Create adr-0004 (durable workflow checkpoints) and add the named carve-out + complete ADR index to `architecture-overview.md` [wave 1]
- [x] 14-04-PLAN.md — Extract `resolve_llm_config_path()` with tests; make the Streamlit sidebar display the effective resolved path read-only [wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 14-02-PLAN.md — Scope `nfrs.md` §2's rebuild guarantee, rewrite "No Hidden State", name the LLM config authority at §3, correct §4 for Tavily [wave 2]
- [ ] 14-03-PLAN.md — Add the three missing artifacts + durable-orchestration-state class to `workspace-contract.md`; deprecate `model-routing.yaml` there and in `config-topology.md` [wave 2]

### Phase 15: views.generate_data Resolution

**Goal**: A user or agent invoking `views.generate_data` over CLI or MCP gets real generated view data or an honest, documented absence — never a permanent-failure stub.
**Depends on**: Nothing (independent of Phase 14; sequenced second because its outcome dictates Phase 16 and 17 content)
**Requirements**: FIX-01
**Success Criteria** (what must be TRUE):

  1. No permanent-failure handler for `views.generate_data` remains in `capabilities/catalog.py` — the `OperationResult(success=False, "Not yet implemented — see Plan 02")` lambda at `catalog.py:317` is gone, either by wiring the real `views/generate.py:175` implementation or by removing the capability from the registry and the MCP surface.
  2. `("views", "generate")` is deleted from `_KNOWN_BROKEN` and the paired still-broken assertion no longer covers it.
  3. The `install_root` vs `workspace` contract mismatch (`catalog.py:149-150` vs `views/generate.py:175`) and the deployed-skill-directory import coupling (`generate.py:43-51`) each have an explicit recorded decision, not an implicit resolution.
  4. Running a daily cycle's post-run views refresh either produces view data or reports an honest, actionable skip — its remediation message never tells the user to run a command that does not exist.
  5. Full pytest suite green with no new `_KNOWN_BROKEN` entries; if the views command group had to be touched, the bounded RT-01/RT-02 exception is scoped to that group only.

**Plans**: TBD

### Phase 16: Invocation & User-Doc Truth

**Goal**: Every command string a user or agent executes from CONSTRUCT's documentation resolves against the live registry and runs.
**Depends on**: Phase 15 (FIX-01's decision determines what the curation-cycle, research-cycle, and daily-cycle references should say)
**Requirements**: FIX-03, DEC-01, DOC-04
**Success Criteria** (what must be TRUE):

  1. `_KNOWN_BROKEN` in `tests/contract/test_doc_command_references.py` is **empty** and the full suite is green — every `construct ...` string in skills, workflow docs, and the release playbook resolves against the live Typer app.
  2. `knowledge card list` / `knowledge ref list` have one recorded decision — implemented as real commands, or both dependent skills (`construct-synthesis`, `construct-gap-analysis`) rewritten onto commands that exist.
  3. `construct-synthesis/SKILL.md` either no longer declares `WebSearch` / `WebFetch`, or `PROJECT.md` records it as a deliberate, reasoned exception to the thin-wrapper claim — `spec-v04:436` is closed either way.
  4. A user can invoke `research search|score|run|review|inspect`, `curation run|review|inspect`, `daily run|inspect`, and `card evaluate` directly from `USER_GUIDE.md`, and `construct/references/commands.md` lists real commands.
  5. The release-validation artifact runs end to end — `USER-TEST-PLAYBOOK-v03.md` is retired or superseded by a playbook whose every step executes — and `README.md` lineage plus `AGENTS.md:284`'s CLI description match the live 25-command surface.

**Plans**: TBD

### Phase 17: Architecture Doc Set & daily.run Discoverability

**Goal**: A v0.5 planner reading the architecture doc set sees the system that actually exists, and the flagship v0.4 capability is reachable from the chat interface.
**Depends on**: Phase 14 (durable-state and config decisions), Phase 15 (capability counts and views outcome)
**Requirements**: DOC-01, DOC-02, UX-01
**Success Criteria** (what must be TRUE):

  1. `architecture-overview.md` presents ADR-0003's four-layer model including the Python runtime layer, with no surviving claim that skills are the only legitimate writers to layer 1 (:39, :73, :236) and no citation of the non-existent `spec-v02-data-model.md`.
  2. `artifact-catalog.md` contains rows for every registered capability, CLI command, and MCP tool with counts that match live introspection of the registry and Typer app, plus the search spine, the LLM gates, and the missing `construct-spike-run` skill row.
  3. `config-topology.md` is either corrected against the real on-disk layout or deleted, with every document that defers to it updated accordingly.
  4. A user can trigger `daily.run` from Claude-native chat through a skill, and that skill's command strings pass the FIX-04 guard with zero additions to `_KNOWN_BROKEN`.
  5. The no-parent-graph design decision for `daily.run` is recorded in a durable document (PROJECT.md Key Decisions and/or the architecture doc set), not only in the `daily_run.py:10-11` docstring.

**Plans**: TBD

## Coverage (v0.4.1 — active)

| Requirement | Phase | Rationale for placement |
|-------------|-------|-------------------------|
| DOC-03 | Phase 14 | Gates v0.5 design — lands first per audit sequencing note |
| FIX-02 | Phase 14 | Config-location decision must precede the doc rewrites that describe it (conflict C1) |
| FIX-01 | Phase 15 | Its decision determines what four of the six broken invocation references should say |
| FIX-03 | Phase 16 | Depends on FIX-01's decision for three of six files; completion = empty allowlist |
| DEC-01 | Phase 16 | Edits `construct-synthesis/SKILL.md`, the same file FIX-03 rewrites |
| DOC-04 | Phase 16 | Playbook retirement removes two allowlist entries — coupled to FIX-03 by construction |
| DOC-01 | Phase 17 | Must reflect DOC-03 and FIX-02 decisions; rewriting it earlier means rewriting it twice |
| DOC-02 | Phase 17 | Capability/CLI/MCP counts are only stable after FIX-01 resolves |
| UX-01 | Phase 17 | New skill must reflect the FIX-01 views outcome and pass the guard clean |

**Coverage:** 9/9 open v0.4.1 requirements mapped exactly once. Unmapped: 0. Duplicated: 0.

**Not mapped (by design):** FIX-04 — delivered 2026-07-19 ahead of the milestone (commit `11f20f4`). It is a pre-milestone deliverable, not phase work; its `_KNOWN_BROKEN` allowlist supplies the mechanical completion criteria for Phases 15 and 16.

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
| 14. Durable-State & Config Truth | v0.4.1 | 2/4 | In Progress|  |
| 15. views.generate_data Resolution | v0.4.1 | 0/? | Not started | - |
| 16. Invocation & User-Doc Truth | v0.4.1 | 0/? | Not started | - |
| 17. Architecture Doc Set & daily.run Discoverability | v0.4.1 | 0/? | Not started | - |
