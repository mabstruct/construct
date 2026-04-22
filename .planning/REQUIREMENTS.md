# Requirements: CONSTRUCT

**Defined:** 2026-04-22
**Core Value:** The knowledge graph must become an active, persistent, agent-maintained system that compounds over time instead of a passive note store.

## v1 Requirements

Requirements for the initial release. Each maps to exactly one roadmap phase.

### Workspace Initialization

- [ ] **WORK-01**: User can run `construct init <path>` to create a valid local workspace with the canonical directories and config files defined by the spec.
- [ ] **WORK-02**: User can configure frontier, workhorse, and lightweight model routing through workspace config without changing application code.
- [ ] **WORK-03**: User can initialize at least one knowledge domain through a guided setup flow that captures scope, taxonomy seeds, source priorities, and research seeds.

### Knowledge Cards And Storage

- [ ] **CARD-01**: User can store knowledge cards as markdown files with YAML frontmatter that validate against the canonical card schema.
- [ ] **CARD-02**: User can add a lightweight seed from a URL, title, question, or hunch and have the system turn it into a structured card draft.
- [ ] **CARD-03**: User can view clear validation errors when a card or config file is malformed instead of silent failure.
- [ ] **CARD-04**: User data remains local-first, with markdown and YAML files treated as the canonical source of truth rather than derived indexes or UI artifacts.

### Indexing And Graph Engine

- [ ] **INDX-01**: User can rebuild SQLite plus FTS5 indexes from source-of-truth files after deleting rebuildable state.
- [ ] **INDX-02**: User can search cards and references with full-text queries and receive accurate results from the rebuilt index.
- [ ] **GRAPH-01**: User can derive a knowledge graph from cards and typed connections and inspect graph size, components, and connectivity.
- [ ] **GRAPH-02**: User can identify graph health issues including orphan cards, stale cards, and bridge nodes through graph metrics or status commands.

### Runtime And Agents

- [ ] **RUNT-01**: User can start and stop a local CONSTRUCT session that initializes orchestrator, curator, and researcher runtime state cleanly.
- [ ] **RUNT-02**: User can route tasks to the appropriate model tier and provider according to workspace configuration.
- [ ] **RUNT-03**: User can inspect structured event logs for agent actions, session lifecycle events, and failures.
- [ ] **RUNT-04**: User can recover from agent or session interruption without corrupting source-of-truth files.

### Research And Curation Workflows

- [ ] **RSRH-01**: User can trigger a research cycle from configured search seeds and have findings ingested into the workspace as structured candidate knowledge.
- [ ] **RSRH-02**: User can add a reference through chat or command flow and have metadata retrieved, evaluated, and attached to the graph pipeline.
- [ ] **CURA-01**: User can have curator workflows detect duplicates, low-confidence items, stale cards, and missing or weak connections.
- [ ] **CURA-02**: User can review agent-mediated proposals for promotions, flags, and connection suggestions instead of having the UI write directly to source-of-truth files.

### Views, UI, And Interaction

- [ ] **VIEW-01**: User can rely on heartbeat-generated `views/` artifacts that rebuild the UI read model from canonical workspace state.
- [ ] **VIEW-02**: User can open a browser UI that renders the graph, card browser, dashboard, and chat surfaces from the generated view models.
- [ ] **VIEW-03**: User can click a graph node or card result and inspect card content, metadata, connections, and status in the UI.
- [ ] **CHAT-01**: User can chat with CONSTRUCT over the local interface to start research, inspect domain status, ask for gaps, and steer the system.
- [ ] **CHAT-02**: User can see agent status and recent activity in the UI so overnight or background changes are visible and auditable.

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Synthesis And Publishing

- **SYNT-01**: User can generate article, briefing, overview, or whitepaper drafts from graph state with evidence-aware synthesis.
- **SYNT-02**: User can export polished outputs as markdown, PDF, DOCX, or publication-ready artifacts.
- **NARR-01**: User can render outputs in a distinct publication voice with register-aware framing.

### Advanced Knowledge Intelligence

- **SEMS-01**: User can discover semantic similarity and duplicate candidates through embeddings-backed retrieval.
- **XDOM-01**: User can receive deeper cross-domain bridge suggestions using embedding or LLM-assisted reasoning beyond structural heuristics.
- **DIFF-01**: User can compare domain landscapes and graph evolution across snapshots in dedicated diff views.

### Integrations And Distribution

- **MCP-01**: User can access CONSTRUCT capabilities through an MCP server and portable skill-pack integrations.
- **SYNC-01**: User can opt into cloud sync or remote dashboard access without giving up the local-first source of truth.
- **MOBL-01**: User can interact through Telegram or similar remote/mobile bridges.

## Out of Scope

Explicitly excluded from v0.1. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user collaboration and roles | v0.1 is intentionally single-user and local-first |
| Authentication and multi-tenancy | No auth is required for the local-only initial release |
| Hosted web dashboard or cloud deployment | Deferred until the local workflow proves out |
| Plugin platform | Too much surface area for the first release |
| Obsidian, Notion, or Roam import/export bridges | Not required to validate the core product thesis |
| Mobile or PWA support | Web plus local runtime is sufficient for v0.1 |
| ChromaDB or embeddings-first retrieval | Deferred until scale and semantic search justify the complexity |
| Synthesizer and Narrator agents | Valuable, but explicitly deferred beyond the initial research-and-collection release |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| WORK-01 | Unmapped | Pending |
| WORK-02 | Unmapped | Pending |
| WORK-03 | Unmapped | Pending |
| CARD-01 | Unmapped | Pending |
| CARD-02 | Unmapped | Pending |
| CARD-03 | Unmapped | Pending |
| CARD-04 | Unmapped | Pending |
| INDX-01 | Unmapped | Pending |
| INDX-02 | Unmapped | Pending |
| GRAPH-01 | Unmapped | Pending |
| GRAPH-02 | Unmapped | Pending |
| RUNT-01 | Unmapped | Pending |
| RUNT-02 | Unmapped | Pending |
| RUNT-03 | Unmapped | Pending |
| RUNT-04 | Unmapped | Pending |
| RSRH-01 | Unmapped | Pending |
| RSRH-02 | Unmapped | Pending |
| CURA-01 | Unmapped | Pending |
| CURA-02 | Unmapped | Pending |
| VIEW-01 | Unmapped | Pending |
| VIEW-02 | Unmapped | Pending |
| VIEW-03 | Unmapped | Pending |
| CHAT-01 | Unmapped | Pending |
| CHAT-02 | Unmapped | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 0
- Unmapped: 24 ⚠️

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after initial definition*
