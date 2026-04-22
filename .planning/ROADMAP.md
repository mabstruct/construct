# Roadmap: CONSTRUCT

## Overview

CONSTRUCT v0.1 will ship as a sequential, Python-first, local-first knowledge system that proves the canonical markdown workspace, rebuildable derived state, governed runtime, and browser read path before deeper polish. The roadmap prioritizes source-of-truth integrity, deterministic rebuildability, and auditable agent workflows so the first release validates the product thesis without drifting into cloud, multi-user, or non-canonical shortcuts.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Workspace & Canonical Data Foundation** - Create a valid local workspace and lock markdown/YAML as the canonical knowledge layer.
- [ ] **Phase 2: Rebuildable Retrieval & Graph Health** - Turn canonical knowledge into searchable indexes and inspectable graph health.
- [ ] **Phase 3: Runtime & Command Surface** - Run CONSTRUCT locally with auditable runtime behavior, routing, and recovery.
- [ ] **Phase 4: Governed Research & Curation Loops** - Let agents ingest and improve knowledge under human-governed workflows.
- [ ] **Phase 5: Views, Browser UI & Activity Visibility** - Expose graph, cards, chat surfaces, and agent activity through heartbeat-backed browser views.

## Phase Details

### Phase 1: Workspace & Canonical Data Foundation
**Goal**: Users can create a valid CONSTRUCT workspace and manage knowledge as validated markdown/YAML source-of-truth files.
**Depends on**: Nothing (first phase)
**Requirements**: WORK-01, WORK-02, WORK-03, CARD-01, CARD-03, CARD-04
**Success Criteria** (what must be TRUE):
  1. User can run `construct init <path>` and receive a valid local workspace with the canonical directories and config files required by the product spec.
  2. User can complete guided domain setup and see domain scope, taxonomy seeds, source priorities, and research seeds written into the workspace without hand-editing application code.
  3. User can create or edit markdown knowledge cards that validate against the canonical schema, and malformed cards or config files show clear validation errors.
  4. User can inspect the workspace and confirm markdown/YAML files are the canonical state while future indexes and UI artifacts remain derived and rebuildable.
**Plans**: TBD

### Phase 2: Rebuildable Retrieval & Graph Health
**Goal**: Users can rebuild disposable read/query layers from canonical files and inspect the resulting search and graph state.
**Depends on**: Phase 1
**Requirements**: CARD-02, INDX-01, INDX-02, GRAPH-01, GRAPH-02
**Success Criteria** (what must be TRUE):
  1. User can add a lightweight seed from a URL, title, question, or hunch and receive a structured card draft that fits the canonical workspace model.
  2. User can delete rebuildable index state, run a rebuild, and recover a working SQLite + FTS5 index from source-of-truth files.
  3. User can search cards and references with full-text queries and get accurate results from the rebuilt index.
  4. User can inspect graph size, connectivity, components, and graph health signals such as orphan cards, stale cards, and bridge nodes.
**Plans**: TBD

### Phase 3: Runtime & Command Surface
**Goal**: Users can run CONSTRUCT as a local orchestrator with auditable events, configurable routing, and safe session recovery.
**Depends on**: Phase 2
**Requirements**: RUNT-01, RUNT-02, RUNT-03, RUNT-04, CHAT-01
**Success Criteria** (what must be TRUE):
  1. User can start and stop a local CONSTRUCT session cleanly and see orchestrator, curator, and researcher runtime state initialize without corrupting workspace files.
  2. User can use chat or command flows to inspect domain status, ask for graph gaps, and steer local CONSTRUCT actions from one shared command surface.
  3. User can verify that tasks route to the configured model tier/provider and can inspect structured event logs for agent actions, session lifecycle events, failures, and recoveries.
  4. User can restart after interruption and recover the session without losing recoverable runtime state or damaging canonical markdown/YAML data.
**Plans**: TBD

### Phase 4: Governed Research & Curation Loops
**Goal**: Users can grow and maintain the knowledge graph through agent-mediated research and curation workflows that stay reviewable.
**Depends on**: Phase 3
**Requirements**: RSRH-01, RSRH-02, CURA-01, CURA-02
**Success Criteria** (what must be TRUE):
  1. User can trigger a research cycle from configured search seeds and see structured candidate knowledge ingested into the workspace pipeline.
  2. User can add a reference through chat or command flow and have its metadata retrieved, evaluated, and attached to the graph pipeline.
  3. User can review curator proposals for promotions, flags, and connection suggestions instead of having the interface write directly to source-of-truth files.
  4. User can see duplicates, low-confidence items, stale cards, and weak or missing connections surfaced by curator workflows.
**Plans**: TBD

### Phase 5: Views, Browser UI & Activity Visibility
**Goal**: Users can explore CONSTRUCT through a browser UI backed only by heartbeat-generated views and can audit ongoing agent activity.
**Depends on**: Phase 4
**Requirements**: VIEW-01, VIEW-02, VIEW-03, CHAT-02
**Success Criteria** (what must be TRUE):
  1. User can rely on heartbeat-generated `views/` artifacts that rebuild browser read models from canonical workspace state without the UI reading raw source files.
  2. User can open a browser UI that renders the graph, card browser, dashboard, and activity/chat surfaces from generated view models.
  3. User can click a graph node or card result and inspect card content, metadata, connections, and status in the UI.
  4. User can see agent status and recent activity in the UI so background or overnight changes are visible and auditable.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Workspace & Canonical Data Foundation | 0/TBD | Not started | - |
| 2. Rebuildable Retrieval & Graph Health | 0/TBD | Not started | - |
| 3. Runtime & Command Surface | 0/TBD | Not started | - |
| 4. Governed Research & Curation Loops | 0/TBD | Not started | - |
| 5. Views, Browser UI & Activity Visibility | 0/TBD | Not started | - |
