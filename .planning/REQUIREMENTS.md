# Requirements: CONSTRUCT v0.4 Agent Workflows

**Defined:** 2026-06-21  
**Milestone:** v0.4 Agent Workflows  
**Core Value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.

## v0.4 Requirements

Requirements for the v0.4 Agent Workflows milestone. Each requirement maps to exactly one roadmap phase.

**Invocation contract:** When a requirement says the user can "run" a workflow or capability, it means the capability is exposed through the current CONSTRUCT invoke surfaces: the `construct` CLI, the stdio MCP server, and the shared capability registry/API used by both. v0.4 extends the existing CONSTRUCT capability API; it does not create a separate workflow API or require direct Python imports.

### Search Provider Spine

- [ ] **SRCH-01**: User can run a provider-agnostic `research.search` capability through the CONSTRUCT CLI/MCP surface, returning normalized search results without writing to the workspace source of truth.
- [ ] **SRCH-02**: Developer can configure search providers, API-key environment variables, query caps, and result caps without changing workflow code.
- [ ] **SRCH-03**: Developer can run the full search contract test suite offline using a mock provider and fixture responses.
- [ ] **SRCH-04**: User receives structured degraded-state errors when a search provider fails, times out, or hits configured caps.

### Research Workflow

- [ ] **RSCH-01**: User can run `research.score` through the CONSTRUCT CLI/MCP surface to convert normalized search results into structured, governance-aware finding proposals with relevance, source tier, ingest action, and reasoning.
- [ ] **RSCH-02**: User can run `research.run` through the CONSTRUCT CLI/MCP surface to execute search, deduplication, scoring, review, approved ingest, digest creation, seed updates, and event logging as one workflow.
- [ ] **RSCH-03**: User can review, approve, or reject research findings before any refs, cards, seed timestamps, or digest artifacts are written.
- [ ] **RSCH-04**: User can resume or inspect a paused research workflow with pending review state preserved across process restarts.
- [ ] **RSCH-05**: Rerunning a research workflow is idempotent for duplicate URLs, duplicate refs, rejected findings, and partially completed batches.

### Curation Workflow

- [ ] **CUR-01**: User can run `curation.run` through the CONSTRUCT CLI/MCP surface and receive real integrity, decay, orphan, connection, and report results instead of placeholder success responses.
- [ ] **CUR-02**: User can evaluate lifecycle promotion candidates through a structured `card.evaluate` gate that proposes promote, hold, or escalate decisions with evidence.
- [ ] **CUR-03**: User can review and approve or reject lifecycle and connection proposals before canonical card or connection writes occur.
- [ ] **CUR-04**: User can inspect curation workflow status, degraded states, and emitted events for every deterministic step and review gate.
- [ ] **CUR-05**: Developer can verify curation behavior with offline tests that fail if placeholder no-op handlers or unreviewed writes remain.

### CONSTRUCT API And Runtime Parity

- [ ] **API-01**: Developer can see every new v0.4 capability registered in the existing CONSTRUCT capability registry/API with Pydantic input/output schemas, handler metadata, CLI command metadata, and MCP tool metadata.
- [ ] **API-02**: User and agent can invoke every new v0.4 workflow capability through the same registry-backed handler from the `construct` CLI and stdio MCP server.
- [ ] **API-03**: Developer can verify CLI/MCP schema and result parity for all new research, curation, gate, and daily-cycle capabilities.
- [ ] **API-04**: User can run migrated research and curation Claude-native skills that delegate to CLI/MCP instead of direct `WebSearch`, `WebFetch`, or workspace writes.
- [ ] **API-05**: Existing v0.3 CLI, MCP, Streamlit, validation, ingestion, graph, and ask-domain behavior continues to pass while v0.4 workflow capabilities are added.

### Daily-Cycle Composition

- [ ] **DAY-01**: User can run a daily-cycle workflow through the CONSTRUCT CLI/MCP surface that composes stable research and curation child workflows instead of duplicating their logic.
- [ ] **DAY-02**: User can see parent and child workflow status, pending reviews, degraded states, and final graph-health summary in the daily-cycle result.
- [ ] **DAY-03**: User can run daily-cycle safely when research or curation pauses for review, fails partially, or skips optional views refresh.

## Future Requirements

Deferred to later milestones or separate tracks. These are acknowledged but not part of the v0.4 Agent Workflows roadmap.

### UI-Primary Experience

- **UI-01**: User can operate CONSTRUCT from a browser-primary shell with capability buttons, LLM review modals, and HTTP-backed workflows.
- **UI-02**: User can use a production-grade browser workflow review experience beyond the v0.3 Streamlit ops UI.

### Expanded Workflow Surface

- **AUTHR-01**: User can run a full co-authorship workflow that composes gap analysis, optional research, outline, draft, revision, and publish gates.
- **GAP-01**: User can run standalone gap analysis with graph metrics and L2 recommendations.
- **PROV-01**: Developer can add multiple real search providers, including academic metadata providers, after Tavily and the mock provider prove the interface.

### Runtime Cleanup

- **REG-01**: Developer can route views, spike, and tag command groups through the capability registry so every runtime surface sees the same contracts.
- **VIEW-01**: User can regenerate the full v0.2/v0.3 views data set from implemented `views.generate_data` emission instead of warning-only or partial behavior.
- **VER-01**: Developer can close historical per-phase verification, Nyquist, and security documentation gaps from v0.3.

## Out of Scope

Explicitly excluded from v0.4 Agent Workflows to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Browser-primary product UI | v0.5 depends on stable v0.4 workflow capabilities first. |
| HTTP API, MCP SSE, cloud deploy, auth, or multi-user runtime | v0.4 is local-first workflow hardening through existing CLI/MCP/Streamlit surfaces. |
| SQLite, vector database, queue workers, or crawler stack | File workspace, provider fixtures, and governed ingest are sufficient for v0.4. |
| Full co-authorship graph | Depends on stable research, curation, review, and daily-cycle foundations. |
| Broad RT-01/RT-02 registry cleanup | Tracked separately unless a specific command path blocks v0.4 workflow delivery. |
| Full views data emission | Optional warning-only refresh hook is acceptable; full emission is a separate track. |
| Automatic LLM lifecycle promotion or connection writes | Human review before canonical SOT writes is non-negotiable. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRCH-01 | TBD | Pending |
| SRCH-02 | TBD | Pending |
| SRCH-03 | TBD | Pending |
| SRCH-04 | TBD | Pending |
| RSCH-01 | TBD | Pending |
| RSCH-02 | TBD | Pending |
| RSCH-03 | TBD | Pending |
| RSCH-04 | TBD | Pending |
| RSCH-05 | TBD | Pending |
| CUR-01 | TBD | Pending |
| CUR-02 | TBD | Pending |
| CUR-03 | TBD | Pending |
| CUR-04 | TBD | Pending |
| CUR-05 | TBD | Pending |
| API-01 | TBD | Pending |
| API-02 | TBD | Pending |
| API-03 | TBD | Pending |
| API-04 | TBD | Pending |
| API-05 | TBD | Pending |
| DAY-01 | TBD | Pending |
| DAY-02 | TBD | Pending |
| DAY-03 | TBD | Pending |

**Coverage:**
- v0.4 requirements: 22 total
- Mapped to phases: 0
- Unmapped: 22 warning

---
*Requirements defined: 2026-06-21*
*Last updated: 2026-06-21 after v0.4 milestone requirements definition*
