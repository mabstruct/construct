# Project Research Summary

**Project:** CONSTRUCT
**Domain:** Local-first, agent-powered personal knowledge system
**Researched:** 2026-04-22
**Confidence:** HIGH

## Executive Summary

CONSTRUCT should be built as a local-first Python monolith for governed knowledge work, not as a generic note app or an over-abstracted agent framework. The consistent recommendation across the research is: keep markdown + YAML as the canonical workspace source of truth, derive SQLite/FTS5, NetworkX graph state, and `views/*.json` from that source, and expose everything through one shared application/service layer consumed by CLI, chat, and the React UI.

The winning v1 is narrow but opinionated: reliable workspace setup, validated markdown knowledge cards, fast capture, full-text + metadata search, graph browsing, card provenance inspection, chat-driven control, researcher ingestion, curator health workflows, and lightweight cross-domain bridge detection. That preserves the actual product thesis — an active, governed knowledge graph — while explicitly deferring cloud, collaboration, embeddings, publishing, broad integrations, and PKM-parity distractions.

The biggest risks are architectural, not model-related: split-brain state across files/db/views/runtime, unreliable inbox/task durability, unstable view contracts, graph edge semantics drift, and runaway agent loops or cost. The roadmap should treat rebuildability, idempotency, atomic views, deterministic governance rules, and budget visibility as first-class deliverables, not polish.

## Key Findings

### Recommended Stack

Use a Python 3.12-first backend with FastAPI/Uvicorn, Pydantic v2, stdlib `sqlite3` + FTS5, NetworkX, HTTPX, and thin in-repo provider adapters. Pair it with a thin React 19 + TypeScript + Vite frontend that renders heartbeat-generated `views/*.json`, uses Zustand for local UI state, D3 for graph interaction, Tailwind for dense operator UI styling, and a plain browser WebSocket for chat/events.

The stack recommendation is strong because it matches the product shape: local-first, single-user, rebuildable, typed, and graph-heavy. The clear “do not use” pattern is just as important: avoid LangChain-style core frameworks, ORMs, graph databases, Socket.IO, SSR/full-stack JS frameworks, desktop shells, and embedding infrastructure in v0.1.

**Core technologies:**
- **Python 3.12 + FastAPI + Uvicorn**: local server/runtime — typed ASGI foundation without backend sprawl.
- **Pydantic v2 + pydantic-settings + orjson**: canonical schemas/config/serialization — keeps Python as the contract source of truth.
- **Markdown + YAML frontmatter + ruamel.yaml**: canonical knowledge store — human-readable, editable, and git-diffable.
- **sqlite3 + FTS5 + raw SQL**: search/index layer — simple, durable, rebuildable local retrieval without extra services.
- **NetworkX**: derived graph engine — enough for v0.1 traversal, bridge, orphan, and cluster logic.
- **HTTPX + Tenacity + thin provider adapters**: agent/provider layer — preserves control and avoids framework lock-in.
- **React 19 + TypeScript + Vite + Zustand + D3 + Tailwind**: thin UI — optimized for rendering views, graph exploration, and operator workflows.

### Expected Features

The research is very clear that CONSTRUCT v1 must satisfy both local-first knowledge-tool expectations and its own stronger thesis around governed, agent-maintained knowledge. Table stakes are not optional, but differentiators should not be cut in the name of a “simpler MVP,” or the product becomes a generic notes shell with chat.

**Must have (table stakes):**
- Workspace/domain initialization with valid defaults.
- Markdown-backed knowledge cards with validation and provenance.
- Fast capture paths: manual card, URL seed, quick capture.
- Full-text + metadata search without embeddings.
- Graph browsing with useful filters.
- Card detail view with provenance, confidence, metadata, and links.
- System status / knowledge-health visibility.
- Chat/command control surface.
- Rebuildability and inspectability of indexes/views.

**Should have (competitive):**
- Epistemically governed cards with confidence, source tier, lifecycle, and typed relations.
- Agent-mediated research ingestion that produces structured cards.
- Continuous research + curation loop with durable state.
- Curator-driven graph health management.
- Cross-domain bridge detection using structural + metadata heuristics.
- Human-governed inbox/write-back workflow.
- Tiered local-first model routing and spend awareness.

**Defer (v2+ / keep out of scope):**
- Collaboration, auth, roles, cloud sync, hosted/remote access.
- Embedding/vector/semantic search.
- Publication/synthesis studio.
- Broad PKM parity features, plugin platform, broad import/export bridges.
- Mobile/PWA/chat integrations.
- Fully autonomous strategy drift or self-modifying search patterns.

### Architecture Approach

CONSTRUCT should use a layered architecture with a narrow write path and a derived-read pipeline: workspace files are canonical, storage/graph/runtime/views sit behind shared application services, and UI/chat/CLI stay thin. The crucial architectural rule is that markdown/YAML are authoritative, while SQLite, graph state, and `views/` are disposable projections that can always be rebuilt. Add an explicit `services/` layer early so CLI, chat, and UI all reuse the same commands/queries.

**Major components:**
1. **Workspace source of truth** — canonical cards, configs, refs, workflows, connections, and events on disk.
2. **Storage + schemas layer** — parse, validate, persist canonical artifacts, and rebuild indexes safely.
3. **Graph engine** — derive NetworkX graph, metrics, traversals, bridge/orphan detection, and graph serialization.
4. **Runtime / agents** — orchestrate research, curation, heartbeat, routing, logging, and governed execution.
5. **Views pipeline** — render read-only `views/*.json` contracts for UI consumption.
6. **Application services** — one shared command/query API for CLI, chat, and UI.
7. **React UI + WebSocket surface** — visualize views and submit structured actions only.

### Critical Pitfalls

1. **Split-brain storage** — keep files canonical and everything else derived; enforce one storage API and rebuild parity tests.
2. **Transient inbox/task loss** — make actions durable, idempotent, statusful, and event-correlated before rich write-back workflows.
3. **Graph edge semantics drift** — decide early whether one typed edge per ordered pair is a feature or a bug; validate collisions explicitly.
4. **SQLite/FTS drift from clever incremental indexing** — treat full rebuild as correctness oracle and test known query parity.
5. **Unstable `views/` contract** — schema-test, version, and atomically write all views; React must never read raw workspace files.
6. **Non-durable heartbeat / agent loops** — checkpoint long-running work, enforce idempotency, and test crash/restart/resume.
7. **LLM governance and cost failures** — keep deterministic rules for epistemic decisions, require HITL on high-impact actions, and log spend per task.

## Implications for Roadmap

Based on the research, the roadmap should follow dependency order rather than UI temptation. The product is most likely to succeed if it proves canonical data, governed execution, and read contracts before investing in rich interaction polish.

### Phase 1: Canonical Data Foundation
**Rationale:** Everything depends on locking the source-of-truth model before interfaces or agents invent their own versions.
**Delivers:** Card/config/action/view schemas, storage APIs, workspace init, validators, markdown/YAML persistence, SQLite rebuild path, TS type generation, rebuild parity tests.
**Addresses:** Workspace init, markdown canonical store, fast capture foundations, rebuildability, provenance-ready cards.
**Avoids:** Split-brain storage, schema drift, FTS drift, unresolved edge semantics.

### Phase 2: Shared Services and Runtime Skeleton
**Rationale:** CLI, chat, and future UI need one callable surface before interface-specific logic spreads.
**Delivers:** `services/` layer, CLI over services, runtime skeleton, provider routing, durable inbox/task model, event log, cost ledger, idempotent action processing.
**Addresses:** Conversational control surface foundation, governed write-back, tiered model routing, system status backbone.
**Avoids:** Logic duplication, transient inbox loss, duplicate tasks, invisible spend.

### Phase 3: Graph Engine and Knowledge Health
**Rationale:** CONSTRUCT’s core differentiator is the governed graph, so graph derivation must exist before UI or advanced agents.
**Delivers:** NetworkX derivation, graph metrics, orphan/duplicate/bridge heuristics, edge decision record, graph serialization, health queries.
**Addresses:** Graph browsing foundation, cross-domain bridge detection, curator health management, knowledge-health-aware interaction.
**Avoids:** Edge-model mismatch, unreadable graph semantics, ad hoc graph logic in UI/runtime.

### Phase 4: Views Contract and Heartbeat
**Rationale:** The UI should consume stable read models, not raw internals; this phase defines that contract.
**Delivers:** Versioned `views/*.json`, atomic snapshot rendering, dashboard/status/event/card/graph views, heartbeat semantics, contract tests.
**Addresses:** Card detail inspection, system status, graph visualization data, activity timeline, UI-ready read path.
**Avoids:** Unstable views, half-written snapshots, UI coupling to workspace internals, stale state confusion.

### Phase 5: React UI Read Path
**Rationale:** Once views are stable, the frontend becomes a contract-consumption problem rather than an architecture design problem.
**Delivers:** Browser UI for graph, cards, dashboard, filters, activity, spend/status visibility, WebSocket event/chat display, constrained graph UX.
**Uses:** React/Vite/Zustand/D3/Tailwind over versioned views and WebSocket notifications.
**Implements:** Read-only UI surface with strong filtering and provenance-first card inspection.
**Avoids:** Direct file reads/writes, graph-as-universal-navigation mistakes, premature performance tuning.

### Phase 6: Governed Research and Curation Workflows
**Rationale:** This is where CONSTRUCT proves its thesis: agents actively improve the knowledge graph under human governance.
**Delivers:** Researcher ingestion from URLs/questions, curator workflows, HITL review gates, durable inbox execution, restart/resume behavior, budget guardrails, end-to-end tests.
**Addresses:** Agent-mediated ingestion, continuous curation, graph health maintenance, human-governed write-back.
**Avoids:** Haunted background loops, cost blowouts, LLM-made governance decisions, lost user intent.

### Phase 7: Integration and Polish for v0.1 Ship
**Rationale:** Only after the core loop is reliable should the roadmap tighten UX and open future seams.
**Delivers:** Reliability hardening, crash/rebuild/resume tests, packaging/docs, API surface cleanup, future adapter seams.
**Addresses:** v0.1 ship-readiness and open-source onboarding.
**Avoids:** Premature adapters, demo-only happy paths, brittle release quality.

### Phase Ordering Rationale

- Canonical schemas/storage must precede agents, graph, and UI so every later module works against typed, validated data.
- Services must precede rich interfaces so CLI/chat/UI do not fork product logic.
- Graph engine must precede views, and views must precede UI, to preserve the derived-read architecture.
- Durable runtime/task semantics must exist before “continuous agents,” or the product will feel unreliable regardless of model quality.
- Reliability deliverables — rebuild parity, idempotency, atomic snapshots, crash recovery, spend visibility, HITL gates — belong inside the roadmap, not after it.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** durable scheduler/task semantics, provider routing, and cost accounting details need concrete implementation choices.
- **Phase 3:** graph edge semantics and bridge heuristics need an explicit v0.1 decision record.
- **Phase 5:** D3 graph interaction constraints and graph sampling/filter UX may need targeted UI/interaction research.
- **Phase 6:** research ingestion workflow, HITL gates, and restart-safe background execution deserve deeper phase-specific design.

Phases with standard patterns (likely skip research-phase):
- **Phase 1:** FastAPI/Pydantic/sqlite3/FTS5/workspace-init patterns are well-documented.
- **Phase 4:** schema-backed read-model generation and atomic file snapshots are straightforward once contracts are decided.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong alignment with official docs and the product’s local-first constraints; recommendations are mainstream and specific. |
| Features | HIGH | Product docs clearly define what v1 must prove; broader ecosystem table-stakes comparisons are slightly softer but direction is solid. |
| Architecture | HIGH | The PRD/topology/strategy all reinforce the same layered, derived-read design. |
| Pitfalls | HIGH | Risks are concrete, architecture-shaped, and backed by both project constraints and known tool behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **Canonical connection authority:** decide whether typed edges live only in one canonical file structure and document that rule early.
- **Graph edge multiplicity:** choose between one edge per ordered pair or multi-edge preservation before graph/UI contracts stabilize.
- **Task durability mechanism:** confirm the exact on-disk state model for inbox + long-running workflows during planning.
- **Heartbeat vs on-demand refresh balance:** decide how much UI freshness relies on heartbeat alone versus explicit rerender triggers.
- **v1 bridge heuristics scope:** keep cross-domain detection heuristic and interpretable; defer anything embedding-shaped.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — product scope, constraints, and key decisions.
- `.planning/research/STACK.md` — recommended technology stack and version guidance.
- `.planning/research/FEATURES.md` — table stakes, differentiators, anti-features, and dependency mapping.
- `.planning/research/ARCHITECTURE.md` — layered architecture, boundaries, build order, and roadmap implications.
- `.planning/research/PITFALLS.md` — critical failure modes and roadmap warnings.

### Secondary (MEDIUM confidence)
- FastAPI, Pydantic, NetworkX, SQLite FTS5, HTTPX, Typer, React, Vite, Tailwind official docs — stack verification.
- APScheduler docs — restart/misfire/idempotency warnings for scheduler semantics.
- LiteLLM docs — routing and spend-tracking patterns informing runtime guardrails.

### Tertiary (LOW confidence)
- Obsidian, Zotero, and Logseq product positioning used only as weak corroboration for table-stakes expectations.

---
*Research completed: 2026-04-22*
*Ready for roadmap: yes*
