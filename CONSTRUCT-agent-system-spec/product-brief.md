# CONSTRUCT Agent System — Product Brief

**Version:** 1.0.0
**Date:** 2026-04-23
**Authors:** ;-)mab (human) + CONSTRUCT (co-author)
**Status:** Active
**Companion:** [PRD (prd.md)](prd.md) — technical requirements for the agent configuration approach

---

## 1. What Is CONSTRUCT (Agent System)?

CONSTRUCT is an open-source, agent-powered personal knowledge system — the same product described in `CONSTRUCT-spec/construct-product-brief.md` — but implemented entirely as **Claude agent configuration** rather than a custom Python backend.

The user talks to Claude. Claude IS CONSTRUCT. The knowledge graph, epistemic governance, research cycles, curation, and synthesis all happen through Claude's native capabilities — file management, web search, dialog, and reasoning — guided by structured agent definitions, skills, and workflows.

**One-line pitch:** *CONSTRUCT, delivered as Claude configuration. No code to build — knowledge architecture with agency, powered by the AI that's already there.*

---

## 2. Why a Claude-Native Approach?

### The Python approach is valid but heavy

The original CONSTRUCT architecture (CONSTRUCT-spec/) requires:
- Python backend: FastAPI + Uvicorn + SQLite + FTS5 + NetworkX
- React frontend: Vite + D3 + Zustand + TypeScript
- Agent runtime: session management, heartbeat, LLM provider abstraction
- Research clients: httpx + Semantic Scholar + arXiv API integration
- 8 implementation phases across months of development

Most of this is **infrastructure** — plumbing that connects the user to the knowledge. The actual value is in the knowledge model, the epistemic governance, and the agent intelligence.

### Claude already provides the infrastructure

| Infrastructure need | Python approach | Claude-native |
|--------------------|----------------|---------------|
| Dialog management | WebSocket server + chat UI | Native |
| Web research | httpx + API clients + rate limiting | Native (web search) |
| File management | Python I/O + path handling | Native (tool use) |
| Frontier reasoning | LLM API calls + prompt engineering | Native (it's Claude) |
| Session memory | Session state machine + events.jsonl | Native (conversation context) |
| Task routing | Python orchestrator class | Agent identity + skill system |

### What's left to configure

The value-carrying parts: identity, skills, workspace structure, epistemic rules, templates.

---

## 3. Core Concepts (Unchanged from Python Approach)

The knowledge model is identical. These concepts are shared:

### 3.1 The Knowledge Graph Is the Product

Atomic knowledge cards (markdown + YAML frontmatter) with:
- Epistemic type (finding, claim, concept, method, paper, theme, gap, provocation, question, connection)
- Confidence level (1–5: speculative → foundational)
- Source tier (1–5: peer-reviewed → unverified)
- Typed connections (supports, contradicts, extends, parallels, requires, enables, challenges, inspires, gap-for)
- Domain tags from configurable taxonomy
- Lifecycle state (seed → growing → mature → archived)
- Decay tracking

See [knowledge-card-schema.md](knowledge-card-schema.md) for the canonical schema.

### 3.2 CONSTRUCT Is Both the Product and the Agent

The user talks to CONSTRUCT. CONSTRUCT delegates to specialized roles:

```
Human
  │
  └── CONSTRUCT (thinking partner, co-author, orchestrator)
        │
        ├── Curator role     (knowledge graph maintenance, quality gates)
        ├── Researcher role  (web search cycles, extraction, ingestion)
        └── [future roles: Synthesizer, Narrator]
```

In the Claude-native approach, these aren't separate agent processes — they're **role modes** that Claude switches between, each with its own behavior rules and skill set.

### 3.3 The Research Cycle Is Continuous

CONSTRUCT doesn't wait for the user to ask. When prompted to research, it runs a structured cycle:

```
Search Pattern → Web Search → Extract → Score → Ingest → Report
       ↑                                         ↓
       └── User Adapts Pattern ← Curator Reviews ←
```

Web search replaces the Semantic Scholar / arXiv API clients. The search-seeds.json config drives the same structured pattern.

### 3.4 Epistemic Governance Is Not Optional

Every claim carries confidence, source tier, and epistemic type. This propagates into all outputs. Identical to the Python approach.

### 3.5 Cross-Domain Detection Is the Differentiator

Bridge detection across domains works through:
- **L1 (graph structure):** Cards connecting to cards in different domains
- **L2 (category overlap):** Shared content categories across domains
- **L3 (content reasoning):** Claude reads card content and identifies structural parallels

L3 is native to Claude — no embedding pipeline needed (though less systematic than vector search).

---

## 4. What's Different from the Python Approach

### 4.1 No Custom UI

There is no React dashboard, no D3 graph visualization, no browser-based card browser. The interaction surface is Claude's conversation interface.

**Mitigation:** All workspace data is in files. Users can browse `cards/`, `connections.json`, `digests/` with any editor. The graph-status skill produces a text-based dashboard. A future Python approach can add UI on top of the same workspace.

### 4.2 No SQLite Index

There is no persistent index. Claude reads files directly each time.

**Mitigation:** For workspaces <500 cards, file reading is fast enough. Claude can reason over file listings and card content without a pre-built index. For larger workspaces, the Python approach becomes complementary.

### 4.3 No Offline Mode

No Ollama fallback. Claude requires network access.

**Mitigation:** The workspace is local files — the user's knowledge never depends on connectivity. Claude is needed for agent intelligence, not data access.

### 4.4 Human-Triggered Cycles

Research and curation cycles run when the user asks, not on a timer. There is no heartbeat.

**Mitigation:** The daily-cycle workflow provides a structured session pattern. Claude can prompt the user when cycles are overdue based on `search-seeds.json` timestamps.

---

## 5. Evolution Path

### v0.1 — Foundation (This Release)

- Workspace initialization
- Domain initialization interview
- Card creation, editing, archival
- Research cycles via web search
- Curation cycles with promotion rules
- Gap analysis
- Graph health reporting
- Basic synthesis/drafting
- Cross-domain bridge detection (L1 + L2 + L3)

### v0.2 — Depth

- Improved synthesis with multi-source drafting
- Inbox pattern for pending actions
- Search pattern adaptation
- Card merge/split operations
- Digest summarization across cycles

### v0.3 — Complement

- Optional Python layer for SQLite indexing + graph visualization
- Shared workspace — Claude and Python tools operate on same files
- Visual graph exploration as a companion tool

---

## 6. Success Criteria

CONSTRUCT Agent System v0.1 is ready when a user can:

1. Initialize a workspace and configure a domain in <10 minutes
2. Run a research cycle that produces real cards from web search
3. Run a curation cycle that validates, promotes, and flags cards correctly
4. Ask "What gaps do you see?" and get an actionable analysis
5. Draft a document that draws on accumulated knowledge with confidence propagation
6. Detect cross-domain bridges when the knowledge spans multiple domains
7. Trust the epistemic metadata — confidence and source tiers are accurate and consistent
