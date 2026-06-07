# CONSTRUCT — Development Strategy

**Version:** 0.1.0
**Date:** 2026-04-21
**Status:** Draft — pending human approval
**Depends on:** Product brief, ADR-0001, Repo topology, Test strategy

---

## 1. Purpose

This document answers: **What do we build, in what order, and why that order?**

It bridges the product brief (what the product is) and PROCESS.md (how we code) with a phased implementation plan that respects dependency ordering, validates assumptions early, and delivers a usable system incrementally.

---

## 2. Guiding Principles

| Principle | Implication |
|-----------|-------------|
| **Vertical slices over horizontal layers** | Each phase delivers something runnable, not a layer in isolation |
| **Validate expensive assumptions first** | LLM integration and graph rendering are high-risk — test early |
| **Source of truth before derived artifacts** | Cards and schemas must work before views, indexes, or UI |
| **CLI before UI** | Every operation is testable headless before React exists |
| **Local-only, single-user** | No auth, no multi-tenancy, no network security until v0.2+ |
| **Agentic development with Claude Code** | Each phase maps to 1–3 branches. Plans in `dev/plans/`. Human approves before implementation. |

---

## 3. Dependency Graph (What Blocks What)

```
Phase 0: Skeleton
   │
   ▼
Phase 1: Data Foundation ──────────────────────┐
   │                                            │
   ▼                                            ▼
Phase 2: Agent Runtime              Phase 3: Graph Engine
   │                                            │
   ├────────────────────┬───────────────────────┘
   ▼                    ▼
Phase 4: Views Heartbeat
   │
   ▼
Phase 5: React UI
   │
   ▼
Phase 6: Integration & Polish
   │
   ▼
Phase 7: Open-Source Launch
```

Phases 2 and 3 can run in **parallel** — they share no code dependencies.

---

## 4. Phases

### Phase 0 — Repo Skeleton

**Goal:** A valid, installable, testable Python project with CI — zero functionality.

**What:**
- `construct` repo initialized (separate from mabstruct-workspace)
- `pyproject.toml` with ruff, mypy, pytest config
- `src/construct/__init__.py` with version
- Empty `construct.cli` with `construct --version`
- `ui/` scaffolded with Vite + React + Tailwind (renders "CONSTRUCT" text)
- `.github/workflows/ci.yml` running pytest + ruff + mypy + vitest + vite build
- `CLAUDE.md` with working agreements
- `dev/CURRENT.md` initialized

**Exit criteria:**
- `pip install -e .` succeeds
- `construct --version` prints version
- `cd ui && npm run build` produces `dist/`
- CI green on first commit

**Estimated scope:** 1 session

---

### Phase 1 — Data Foundation

**Goal:** Cards can be created, validated, loaded, and indexed. The data model is real.

**What:**
- Pydantic v2 models for knowledge cards (from knowledge-card-schema.md)
- Card loader: read `cards/*.md`, parse YAML frontmatter, validate
- `domains.yaml` loader and validator
- `governance.yaml` and `model-routing.yaml` loaders
- SQLite + FTS5 indexer: walk cards → populate index
- `construct rebuild` CLI command (full re-index from SOT)
- `construct status` CLI command (card count, domain count, index health)
- JSON Schema export from Pydantic models
- TS type generation script (`scripts/generate-types.sh`)

**Exit criteria:**
- Load the 5-card fixture workspace → index → FTS query returns results
- Invalid card frontmatter raises clear validation error
- `construct status` reports accurate counts

**Estimated scope:** 2–3 sessions

---

### Phase 2 — Agent Runtime

**Goal:** Agents can be instantiated, receive tasks, call LLMs, and produce structured output.

**What:**
- Session model: start, heartbeat, pause, stop state machine
- LLM provider abstraction: tiered routing (frontier / workhorse / lightweight)
- Ollama integration as zero-cost local tier
- API-based provider (Anthropic Claude) as frontier/workhorse tier
- Agent base class: identity (SOUL.md), task queue, structured output
- Orchestrator agent: receives intents, delegates to specialist agents
- Curator agent stub: accepts "curate card" task, returns structured result
- Researcher agent stub: accepts "research topic" task, returns structured result
- `events.jsonl` structured logging
- `construct run` CLI command (starts session, runs heartbeat)
- `construct stop` CLI command (graceful shutdown)

**Exit criteria:**
- `construct run` starts session, orchestrator delegates a hardcoded task to curator stub
- LLM call succeeds via Ollama (local) or API key
- `events.jsonl` records session lifecycle events
- Session heartbeat ticks and is observable

**Estimated scope:** 3–4 sessions

---

### Phase 3 — Graph Engine

**Goal:** Knowledge graph builds from cards, supports queries, and detects structure.

**What:**
- `graph/build.py`: walk `cards/` → build NetworkX digraph (nodes = cards, edges = `connects_to`)
- `graph/query.py`: neighbors, shortest path, connected components, bridge detection
- `graph/metrics.py`: orphan count, density, staleness (cards past decay threshold)
- Domain-based subgraph extraction
- Graph serialization to D3 node-link JSON format (`views/graph.json`)
- CLI: `construct graph stats` (node count, edge count, components, bridges)

**Exit criteria:**
- 5-card fixture → graph with correct edges
- Bridge detection identifies the correct bridge node
- `views/graph.json` validates against schema

**Estimated scope:** 2 sessions

---

### Phase 4 — Views Heartbeat

**Goal:** The system automatically rebuilds UI-consumable JSON from source of truth.

**What:**
- Heartbeat timer (configurable interval, default 30s debounce)
- Views renderer pipeline: cards + graph + index → views/*.json
  - `views/graph.json` — D3 node-link
  - `views/cards/*.json` — denormalized card data
  - `views/landscape.json` — domains/clusters overview
  - `views/agents-status.json` — agent health
  - `views/events-recent.json` — last N events
  - `views/responses.json` — chat response queue
- File-watching trigger (optional, complement to timer)
- `construct run` now includes heartbeat as part of session lifecycle

**Exit criteria:**
- Modify a card → heartbeat detects change → views/*.json updated within interval
- All views validate against their schemas (contract tests pass)
- Views survive agent restart (rebuilt from SOT, not from memory)

**Estimated scope:** 2 sessions

---

### Phase 5 — React UI

**Goal:** A browser-based interface for exploring knowledge and interacting with agents.

**What:**
- Python server: Starlette/Uvicorn serving static UI + WebSocket
- WebSocket protocol: subscribe to views updates, send chat messages
- Pages:
  - **Graph** — D3 force-directed visualization reading `views/graph.json`
  - **Cards** — browse, read, search cards
  - **Chat** — WebSocket chat interface to orchestrator agent
  - **Dashboard** — agent status, recent events, graph metrics
- Zustand stores consuming WebSocket data
- `construct run` now starts server, opens browser

**Exit criteria:**
- `construct run` → browser opens → graph renders with fixture data
- Click a node → card panel shows card content
- Type a chat message → agent responds via WebSocket
- Dashboard shows agent lifecycle events

**Estimated scope:** 4–5 sessions

---

### Phase 6 — Integration & Polish

**Goal:** End-to-end journeys work. The system is usable for real knowledge work.

**What:**
- `construct init` — interactive domain interview (J1 from user journeys)
- Researcher agent: real Semantic Scholar / arXiv integration
- Curator agent: real card creation, connection suggestion, confidence scoring
- Inbox write-back pattern: UI proposes → inbox/ → agent governance → views/
- BMAD-inspired workflow engine: SKILL.md parsing, handoff chains
- Search seed management: initial seeds from domain interview, evolving patterns
- `publish/` directory scaffolding (placeholder for v0.2 Narrator)

**Exit criteria:**
- Cold start journey (J1) completes in <30 minutes
- Daily use journey (J2) patterns are functional
- Research cycle produces real cards from real API sources
- Inbox actions flow through governance correctly

**Estimated scope:** 4–5 sessions

---

### Phase 7 — Open-Source Launch

**Goal:** The repo is ready for public release.

**What:**
- `README.md` with quickstart, architecture overview, screenshots
- `LICENSE` (Apache-2.0, pending confirmation)
- `CONTRIBUTING.md`
- Example domain workspace (not MABSTRUCT-specific)
- `construct init` works from `pip install construct` on clean machine
- All specs migrated from planning workspace to `construct/specs/`
- CI green, test coverage documented
- GitHub repo public, initial release tagged

**Exit criteria:**
- A stranger can `pip install construct && construct init` and have a working system
- Documentation is self-sufficient (no dependency on planning workspace)

**Estimated scope:** 2–3 sessions

---

## 5. Risk Register

| Risk | Impact | Mitigation | Phase |
|------|--------|-----------|-------|
| LLM cost unpredictable for research cycle | High ongoing cost | Ollama zero-cost tier as default; tier routing in model-routing.yaml | 2 |
| D3 graph rendering performance at scale | UI unusable | NFR: target ≤500 cards at 30fps; test with fixture | 5 |
| WebSocket complexity for chat + events | Over-engineering | Start with simple polling if WS proves brittle | 5 |
| Pydantic ↔ TS type generation fragile | Schema drift | Contract tests in CI; single-source Pydantic models | 1 |
| Agent runtime scope creep | Never ships | Stubs first, real behavior in Phase 6 only | 2 |
| Card schema changes mid-implementation | Migration burden | Lock schema after Phase 1; changes require ADR | 1 |

---

## 6. What Is Explicitly Out of Scope

These are **not v0.1** and should not be built, designed for, or abstractly prepared:

- Multi-user / collaborative editing
- Cloud deployment / remote access
- ChromaDB / vector embeddings (v0.2)
- Synthesizer agent (v0.2)
- Narrator agent / publish pipeline (v0.3)
- Telegram or Slack integration
- Mobile or PWA support
- Plugin system
- Import/export from Obsidian, Notion, Roam

---

## 7. Session Planning Heuristic

Each Claude Code session should:

1. Pick **one branch** from the current phase
2. Read the relevant spec + this strategy doc
3. Write a plan in `dev/plans/{phase}-{feature}.md`
4. Get human approval
5. Implement + test
6. PR → merge → update `dev/CURRENT.md`

A phase is complete when all its exit criteria pass on main.

---

## 8. Success Criteria for v0.1

The product is v0.1-ready when a user can:

1. `pip install construct` on macOS or Linux
2. `construct init` → answer domain questions → workspace created
3. `construct run` → agents start researching → cards appear → graph grows
4. Open browser → see graph, browse cards, chat with agents
5. Next day: `construct run` → agents resume, new research lands, graph evolves
6. All of this works with Ollama (zero cost) or an API key (better quality)

That's the product. Everything in this document serves getting there.
