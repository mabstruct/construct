# Requirements: CONSTRUCT

**Defined:** 2026-06-08
**Core Value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.

## v1 Requirements

Requirements for the first committed roadmap scope, which in this repository maps to the v0.3 implementation and hardening path while preserving a clean v0.4 UI trajectory.

### Foundation Contracts

- [x] **FND-01**: Maintainer can define one canonical schema set for cards, refs, connections, and related workflow artifacts.
- [x] **FND-02**: System enforces artifact validity at write time so invalid cards, refs, connections, or workflow outputs are rejected before becoming source of truth.
- [x] **FND-03**: User and maintainer can rely on documented canonical artifact shapes and workflow contracts that match the implementation.
- [x] **FND-04**: Existing specification documents are treated as authoritative groundwork for capabilities and artifacts instead of being re-invented during implementation.
- [x] **FND-05**: Maintainer can validate core workflows and artifact contracts against the existing `test-ws/` fixture workspaces so hardening work is proven on real workspace state.
- [x] **FND-06**: Maintainer can define a migration strategy for existing CONSTRUCT projects and workspaces so newer runtime and workflow contracts do not strand prior users.

### Workflow Operability

- [ ] **WF-01**: User can ask the help flow what to do next and receive a clear state-aware next-step recommendation.
- [ ] **WF-02**: User can follow documented workflows for the current Claude-native skills and understand expected inputs, outputs, and outcomes.
- [ ] **WF-03**: User can resume work from persisted workspace state without losing the current workflow context.
- [ ] **WF-04**: User-facing commands and workflow outputs are clear enough that a power user can understand what happened and what action is available next.

### Knowledge Ingestion And Integrity

- [ ] **ING-01**: User can ingest source material from files, notes, URLs, and web research into the system through a reliable governed flow.
- [ ] **ING-02**: System assigns ingested files to a defined workspace storage location so source artifacts remain organized and traceable.
- [ ] **ING-03**: User can create, edit, and archive knowledge cards and references while preserving required metadata and artifact validity.
- [ ] **ING-04**: User can create and maintain typed connections between knowledge nodes using the established connection vocabulary.
- [ ] **ING-05**: User can trust graph-health and gap-analysis outputs to identify weak coverage, missing links, or next areas to strengthen.
- [ ] **ING-06**: User can generate grounded synthesis outputs that stay tied to the graph knowledge base and preserve confidence-aware reasoning.

### Runtime Transition

- [ ] **RT-01**: Maintainer can define a shared capability registry for core system operations so runtime surfaces use the same contracts.
- [ ] **RT-02**: User can invoke core deterministic capabilities through a stable Python CLI surface.
- [ ] **RT-03**: Claude-native workflows can invoke stable MCP tools with schema parity to the CLI instead of depending on fragile inline behavior.
- [ ] **RT-04**: System can execute multi-step workflows through a structured runner that records progress and outcomes.

### Advanced Graph Leverage

- [ ] **ADV-01**: User can ask grounded domain questions through a bounded reasoning gate that cites relevant knowledge artifacts.
- [ ] **ADV-02**: User can detect promising cross-domain bridges more systematically once graph integrity is reliable.
- [ ] **ADV-03**: System can emit stable derived-data contracts that a future UI layer can consume without redefining the knowledge model.
- [ ] **ADV-04**: Maintainer can exercise capabilities through a local ops UI spike without making that spike the source of truth.

### Governed Exploration Spikes

- [ ] **SPK-01**: Maintainer can run governed spikes on external graph-analysis tools without changing the established CONSTRUCT governance model or canonical workspace contracts.
- [ ] **SPK-02**: Maintainer can evaluate whether Graphify-style ingestion analysis is useful for producing candidate tags and keywords during document ingestion.
- [ ] **SPK-03**: Maintainer can route candidate tags and keywords from ingestion analysis into the curation cycle as reviewable inputs for adapting search patterns rather than auto-accepted knowledge.
- [ ] **SPK-04**: Maintainer can evaluate graph-guided exploration patterns inspired by tools such as InfraNodus for future UI and insight workflows without replacing typed knowledge cards and governed connections.

## v2 Requirements

Deferred to future release. Tracked but not in the current roadmap.

### Product Expansion

- **EXP-01**: User can browse and operate the product primarily through a broader-user v0.4 UI shell built on top of the hardened v0.3 runtime contracts.
- **EXP-02**: User can use richer graph and wiki interactions in the UI without bypassing governance or canonical file contracts.
- **EXP-03**: System can add indexing or retrieval accelerators when file-backed workflows no longer meet scale needs.

## Out of Scope

Explicitly excluded from the current roadmap scope.

| Feature | Reason |
|---------|--------|
| Full v0.4 browser-first product shell | The current scope must harden contracts, workflows, and runtime foundations before UI-primary delivery |
| Replacing the knowledge model or workspace format | Product continuity across prototype, v0.3, and v0.4 depends on preserving the established model |
| Breaking current Claude-native workflows during migration | Existing power-user flows must remain usable while the foundation is hardened |
| Multi-user collaboration or cloud-first architecture | Not aligned with the current local-first single-user milestone |
| Broad plugin or integration marketplace | Internal contracts and workflows must stabilize before ecosystem expansion |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Complete |
| FND-02 | Phase 1 | Complete |
| FND-03 | Phase 1 | Complete |
| FND-04 | Phase 1 | Complete |
| FND-05 | Phase 1 | Complete |
| FND-06 | Phase 1 | Complete |
| WF-01 | Phase 4 | Pending |
| WF-02 | Phase 4 | Pending |
| WF-03 | Phase 4 | Pending |
| WF-04 | Phase 4 | Pending |
| ING-01 | Phase 4 | Pending |
| ING-02 | Phase 2 | Pending |
| ING-03 | Phase 2 | Pending |
| ING-04 | Phase 2 | Pending |
| ING-05 | Phase 4 | Pending |
| ING-06 | Phase 5 | Pending |
| RT-01 | Phase 3 | Pending |
| RT-02 | Phase 3 | Pending |
| RT-03 | Phase 3 | Pending |
| RT-04 | Phase 4 | Pending |
| ADV-01 | Phase 5 | Pending |
| ADV-02 | Phase 5 | Pending |
| ADV-03 | Phase 6 | Pending |
| ADV-04 | Phase 6 | Pending |
| SPK-01 | Phase 6 | Pending |
| SPK-02 | Phase 6 | Pending |
| SPK-03 | Phase 6 | Pending |
| SPK-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-08*
*Last updated: 2026-06-08 after roadmap creation*
