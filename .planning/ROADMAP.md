# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first, then establishes the v0.3 runtime spine, then adds bounded graph leverage and v0.4-facing contracts without pulling full browser UI work ahead of proven backend and workflow behavior.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Contract Canon & Artifact Governance** - Canonize schemas, write gates, and spec-aligned workflow contracts. (completed 2026-06-08)
- [ ] **Phase 2: Governed Knowledge Operations** - Make core card, ref, connection, and storage operations reliable in the existing workspace model.
- [ ] **Phase 3: Capability Registry, CLI & MCP Spine** - Expose deterministic capabilities through one shared runtime contract.
- [x] **Phase 4: Guided Workflow Operability** - Make help, ingestion, workflow execution, and resume behavior state-aware and dependable.
- [ ] **Phase 5: Grounded Synthesis & Graph Reasoning** - Add bounded question-answering, synthesis, and bridge detection on top of a reliable graph.
- [ ] **Phase 6: Derived Data, Ops UI & Governed Spikes** - Prepare v0.4-facing contracts and evaluate local UI/graph-analysis spikes without changing canonical truth.

## Phase Details

### Phase 1: Contract Canon & Artifact Governance
**Goal**: Maintainers and workflows share one canonical artifact contract and enforcement model for the existing Claude-native system.
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06
**Success Criteria** (what must be TRUE):
  1. Maintainer can point to one canonical schema set for cards, refs, connections, and workflow artifacts.
  2. Invalid cards, refs, connections, or workflow outputs are rejected before they become source-of-truth files.
  3. User and maintainer can follow artifact and workflow documentation that matches actual implementation behavior.
  4. Maintainer can trace v0.3 implementation decisions back to existing authoritative spec documents instead of re-invented contracts.
  5. Maintainer can validate contract hardening against the existing `test-ws/` fixture workspaces.
  6. Maintainer can describe how existing CONSTRUCT workspaces migrate safely to the hardened contract model.
**Plans**: 4 plans (3 original + 1 gap closure)

Plans:
- [ ] 01-01-PLAN.md — Canonize the Phase 1 workspace/artifact contract in the authoritative spec layer.
- [ ] 01-02-PLAN.md — Reconcile runtime schemas/init/validation to the canonical contract and add write gates.
- [ ] 01-03-PLAN.md — Align skills/docs, prove the contract on fixtures, and publish the migration playbook.
- [ ] 01-04-PLAN.md — Fix construct-workspace-init template path for deployed workspaces (gap closure).

### Phase 2: Governed Knowledge Operations
**Goal**: Users can reliably create and maintain governed knowledge artifacts inside the existing local-first workspace format.
**Depends on**: Phase 1
**Requirements**: ING-02, ING-03, ING-04
**Success Criteria** (what must be TRUE):
  1. Ingested source files are stored in a defined workspace location that keeps them organized and traceable.
  2. User can create, edit, and archive cards and references without losing required metadata or violating artifact validity.
  3. User can create and maintain typed connections between knowledge nodes using the established connection vocabulary.
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Core knowledge service layer: card CRUD, connection CRUD, event logging, workspace scaffold update
- [ ] 02-02-PLAN.md — CLI surface: `construct knowledge` command group with card and connection subcommands
- [ ] 02-03-PLAN.md — Source file storage (inbox routing) and skill wrappers calling Python CLI

### Phase 3: Capability Registry, CLI & MCP Spine
**Goal**: Core deterministic capabilities run through one shared contract surface that both maintainers and Claude-native workflows can trust.
**Depends on**: Phase 2
**Requirements**: RT-01, RT-02, RT-03
**Success Criteria** (what must be TRUE):
  1. Maintainer can define a shared capability registry once and use it as the contract source for runtime surfaces.
  2. User can invoke core deterministic capabilities through a stable Python CLI surface.
  3. Claude-native workflows can invoke MCP tools with the same schemas and behaviors as the CLI instead of relying on fragile inline file behavior.
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — Capability Registry Foundation
- [ ] 03-02-PLAN.md — CLI Registry Refactoring + PIPE Handlers
- [ ] 03-03-PLAN.md — MCP Server + Contract Tests + Skill Migration

### Phase 4: Guided Workflow Operability
**Goal**: Users can run, resume, and understand Claude-native workflows with dependable next-step guidance and observable progress.
**Depends on**: Phase 3
**Requirements**: WF-01, WF-02, WF-03, WF-04, ING-01, ING-05, RT-04
**Success Criteria** (what must be TRUE):
   1. User can ask what to do next and receive a clear recommendation based on current workspace and workflow state.
   2. User can follow documented workflows for current Claude-native skills and understand expected inputs, outputs, and outcomes.
   3. User can resume work from persisted workspace state without losing the current workflow context.
   4. User can ingest files, notes, URLs, and web research through a governed flow and understand what happened at each step.
   5. User can trust workflow progress, graph-health, and gap-analysis outputs to show weak coverage, missing links, and available next actions.
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md — Workflow runner: state machine, step execution, resume support, state file persistence
- [x] 04-02-PLAN.md — Ingestion pipeline + Help CLI + CLI/capability wiring
- [x] 04-03-PLAN.md — Skill migrations batch 1: graph-status, card-evaluate, curation-cycle
- [x] 04-04-PLAN.md — Skill migrations batch 2: research-cycle, gap-analysis + workflow documentation

### Phase 5: Grounded Synthesis & Graph Reasoning
**Goal**: Users can ask bounded domain questions and produce grounded synthesis outputs from a reliable knowledge graph.
**Depends on**: Phase 4
**Requirements**: ING-06, ADV-01, ADV-02
**Success Criteria** (what must be TRUE):
  1. User can generate synthesis outputs that remain tied to cards, refs, and graph structure with confidence-aware reasoning.
  2. User can ask grounded domain questions and receive bounded answers that cite relevant knowledge artifacts.
  3. User can identify promising cross-domain bridges more systematically once graph integrity is strong enough to support them.
**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md — Core LLM infrastructure: dependencies, llm/ package, config loader, test scaffolding
- [x] 05-02-PLAN.md — ask.domain LangGraph L2 gate: StateGraph, capability registration, CLI, tests
- [ ] 05-03-PLAN.md — Bridge detection pipeline: L1/L2/L3 multi-level detection, CLI, scoring, bridges.json
- [x] 05-04-PLAN.md — Synthesis skill update: CLI command references, confidence propagation documentation

### Phase 6: Derived Data, Ops UI & Governed Spikes
**Goal**: Maintainers can expose stable derived-data contracts for future UI work and safely test local ops UI and graph-analysis spikes without replacing canonical CONSTRUCT behavior.
**Depends on**: Phase 5
**Requirements**: ADV-03, ADV-04, SPK-01, SPK-02, SPK-03, SPK-04
**Success Criteria** (what must be TRUE):
  1. System emits stable derived-data contracts that a future UI layer can consume without redefining the knowledge model.
  2. Maintainer can exercise capabilities through a local ops UI spike without making that UI the source of truth.
  3. Maintainer can run external graph-analysis spikes without changing canonical workspace contracts or CONSTRUCT governance.
  4. Candidate tags, keywords, and graph-guided exploration outputs are routed into reviewable curation inputs rather than auto-accepted knowledge.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Contract Canon & Artifact Governance | 3/3 | Complete   | 2026-06-08 |
| 2. Governed Knowledge Operations | 0/3 | Being planned | - |
| 3. Capability Registry, CLI & MCP Spine | 0/3 | Planned | - |
| 4. Guided Workflow Operability | 4/4 | Complete   | 2026-06-10 |
| 5. Grounded Synthesis & Graph Reasoning | 3/4 | In Progress|  |
| 6. Derived Data, Ops UI & Governed Spikes | 0/TBD | Not started | - |
