# CONSTRUCT — Product Requirements Document

**Version:** 1.0.0
**Date:** 2026-04-21
**Authors:** ;-)mab (human) + CONSTRUCT (co-author)
**Status:** Active — pre-implementation reference
**Companion:** [Product Brief (construct-product-brief.md)](construct-product-brief.md) — vision, concepts, user interactions

---

This document defines **how** CONSTRUCT is built. For **what** and **why**, see the product brief. For **when**, see the [development strategy](construct-development-strategy.md). For **where** (repo layout), see [repo topology](construct-repo-topology.md).

**Audience:** Developers, Claude Code (development agent), contributors.

---

## 1. Architecture Decision

### Evolution: Option C → Option D

The product brief (v1.1.0) originally proposed Option C: a local-first hybrid architecture built on a stripped-down OpenClaw runtime. Three options were evaluated:

| Option | Approach | Decided |
|--------|----------|---------|
| **A** | Local-only (OpenClaw core) | Rejected — too constrained |
| **B** | Web application (hosted) | Rejected — violates data sovereignty |
| **C** | Hybrid: local core, optional cloud | Originally selected, then superseded |
| **D** | Python-first, no OpenClaw | **Final decision** (ADR-0001) |

**Why Option D:** OpenClaw served only as a runtime loop — not essential infrastructure. The TypeScript dependency added a second language without proportional value. The "stripdown" task (estimated Week 1–2) risked being open-ended. Building natively in Python is simpler for single-language development, Claude Code as dev agent, and `pip install` onboarding.

See [ADR-0001](adrs/adr-0001-python-first-drop-openclaw.md) for the full decision record.

### v0.1 Architecture Principles

- **Python is the sole backend language** — agents, graph, storage, research, CLI, server
- **React UI is a build artifact** — `vite build` → static files served by Python
- **Local-first, single-user** — no auth, no multi-tenancy, no network security
- **Data sovereignty** — everything on user's machine, git-backed
- **Cloud-ready but cloud-deferred** — architecture allows Telegram bridge, web dashboard, sync in v2.0

---

## 2. Technology Stack

### Core Runtime (Python-Native)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Agent runtime | Python (native) | Session management, heartbeat, LLM integration, delegation. Built from scratch per ADR-0001. |
| Agent governance | SOUL/IDENTITY markdown definitions | Carried over from MABSTRUCT. Agent behavior governed by documents, not code. |
| Workflow coordination | BMAD-inspired SKILL.md definitions (native) | Progressive context, explicit handoff chains. No BMAD framework dependency. |
| Knowledge store | Markdown files + YAML frontmatter | Source of truth. Human-readable, git-diffable, editor-agnostic. |
| Graph engine | NetworkX (Python) | Derived graph rebuilt from markdown. Typed traversal, path queries, bridge detection. See [zettelkasten-kg-spec.md](zettelkasten-kg-spec.md). |
| Research automation | Python + httpx | Semantic Scholar, arXiv, web. Rate-limit-aware, resumable, historized. |
| Search & indexing | SQLite + FTS5 | Structured queries, full-text search. v0.2 adds ChromaDB for embeddings. |
| Server | Starlette / Uvicorn | HTTP (static UI) + WebSocket (chat + events). |
| CLI | Click or Typer | `construct init / status / run / stop / graph stats / rebuild` |
| Version control | Git | All knowledge, agent state, search patterns are git-tracked. |

### LLM Provider Strategy

CONSTRUCT is provider-agnostic. All providers accessed via API key, fully TOS-compliant.

| Provider | Auth | Cost | Best for |
|----------|------|------|----------|
| **Anthropic (Claude)** | API key | Per-token | Synthesis, cross-domain ideation, co-authorship |
| **OpenAI** | API key | Per-token | Alternative frontier provider |
| **Ollama (local)** | None | Free | Routine tasks: ingestion, formatting, curation |

### Tiered Model Routing

| Cognitive demand | Example tasks | Tier |
|------------------|---------------|------|
| **Low** — extraction, formatting | Parse API response, format card YAML, rebuild index | Local (Ollama) |
| **Medium** — evaluation, classification | Source quality, confidence levels, duplicate detection | Workhorse (Ollama / Haiku) |
| **High** — reasoning, synthesis | Cross-domain patterns, essays, gap analysis, co-authorship | Frontier (Claude Sonnet/Opus) |

Configured via `model-routing.yaml`:

```yaml
providers:
  frontier:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
  workhorse:
    provider: ollama
    model: llama3.3:70b
  lightweight:
    provider: ollama
    model: llama3.2:8b

routing:
  research_ingestion: lightweight
  card_formatting: lightweight
  source_evaluation: workhorse
  taxonomy_tagging: workhorse
  cross_domain_ideation: frontier
  synthesis_drafting: frontier
  co_authorship: frontier
  gap_analysis: frontier
```

**Zero-cost entry:** A user with no API budget runs entirely on Ollama. Quality on high-cognitive tasks is lower, but the system works. Adding an API key upgrades only the expensive tasks.

**Local LLM as strategic bet:** Local model quality is improving rapidly. Ollama support is not a concession — it's a bet that local 70B+ models will handle medium-cognitive tasks well enough that most users never need an API key for routine operations.

### React UI Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | React 18+ (Vite) | Fast, component-based. |
| Graph visualization | D3.js (force-directed) | Proven. Interactive, filterable, zoomable. Reads `views/graph.json`. |
| State management | Zustand | Lightweight, no boilerplate. |
| Styling | Tailwind CSS | Utility-first. Dark theme by default. |
| Type safety | TypeScript (generated from Pydantic) | Single-source schemas. |

---

## 3. Storage Architecture

### Four-Category Model

| Category | Git-tracked | Rebuildable | Purpose |
|----------|------------|-------------|---------|
| **Source of Truth** | Yes | No — this IS the source | Cards, connections, governance, config, event log |
| **Agent Workspace** | Yes | No — historical record | Research output, refs, digests, inbox queues |
| **Persistent Indexes** | No | Yes — from SOT + workspace | SQLite + FTS5, ChromaDB (v0.2) |
| **Disposable Views** | No | Yes — heartbeat-rebuilt | Pre-rendered JSON for React UI |

### Workspace Directory Structure

```
workspace/
├── cards/                  # SOURCE OF TRUTH: Knowledge cards (md + YAML frontmatter)
├── domains.yaml            # Domain taxonomy definitions
├── governance.yaml         # Agent governance config
├── model-routing.yaml      # LLM tier configuration
├── search-seeds.json       # Research search patterns
├── refs/                   # Reference library (per-paper JSON)
├── workflows/              # SKILL.md workflow definitions
├── log/
│   └── events.jsonl        # Append-only audit trail
│
├── inbox/                  # AGENT WORKSPACE: User action queue (transient, gitignored)
│
├── db/                     # PERSISTENT INDEXES (gitignored, rebuildable)
│   ├── construct.db        # SQLite + FTS5
│   └── chroma/             # ChromaDB (v0.2)
│
├── views/                  # DISPOSABLE VIEWS (gitignored, heartbeat-rebuilt)
│   ├── graph.json          # D3 node-link format
│   ├── cards/              # Denormalized card JSON
│   ├── landscape.json      # Domain/cluster overview
│   ├── agents-status.json  # Agent health
│   ├── events-recent.json  # Last N events
│   └── responses.json      # Chat response queue
│
└── publish/                # CURATED OUTPUTS (git-tracked)
    ├── articles/           # Long-form writing
    ├── reports/            # Landscape, gap analyses
    ├── exports/            # Graph SVG, CSV, JSON
    └── drafts/             # WIP before approval
```

### What `db/` Indexes

| Source | What gets indexed | Why |
|--------|-------------------|-----|
| `cards/` | All card metadata + full text | Core queries, FTS, similarity |
| `refs/` | Reference metadata | Duplicate detection |
| `log/events.jsonl` | Action history | "Show me all promotions this week" |
| `domains.yaml` | Taxonomy definitions | Domain-aware filtering |

**Rebuild guarantee:** `construct rebuild` walks all source-of-truth directories and repopulates from scratch.

### Git Tracking Rules

```gitignore
# Persistent indexes (rebuildable)
db/

# Disposable views (heartbeat-rebuilt)
views/

# Transient inbox (consumed by agents)
inbox/
```

---

## 4. Interaction Architecture

CONSTRUCT has two interaction surfaces that complement each other:

- **Chat interface** — conversation, commands, brainstorming, co-authorship
- **React UI** — visual browsing, graph exploration, contextual actions

Both read/write the same workspace. Neither replaces the other.

### Command System (Three Levels)

**Quick ops — no LLM, instant response:**

| Command | What it does |
|---------|--------------|
| `/graph status` | Card count, connections, orphans, confidence distribution |
| `/graph orphans` | List cards with no connections |
| `/graph stale` | List cards past decay threshold |
| `/card count [domain]` | Card count, optionally filtered |
| `/domains list` | Active domains with stats |
| `/research status` | Current pattern version, cycle timing |
| `/agents status` | Active agents, versions, current task |
| `/views now` | Force-trigger views rebuild |
| `/db rebuild` | Rebuild indexes from source of truth |

**Knowledge ops — uses LLM, agent reasoning:**

| Command | Invokes | What it does |
|---------|---------|--------------|
| `/card add <url or title>` | Researcher → Curator | Ingest, extract, evaluate |
| `/card seed <idea>` | Curator | Create speculative card |
| `/search adjust <instructions>` | CONSTRUCT | Propose search pattern changes |
| `/synthesize <topic>` | Synthesizer | Draft from graph state |
| `/gap-check [domain]` | Curator | Identify gaps and thin coverage |
| `/connect <card-a> <card-b>` | Curator | Evaluate and type a connection |

**Conversational — direct chat with CONSTRUCT (frontier model):**

Open-ended brainstorming, cross-domain ideation, co-authorship, editorial discussion.

### Cost Profile

| Level | LLM tier | Cost |
|-------|----------|------|
| Quick ops | None | Free |
| Knowledge ops | Workhorse / Ollama | Low |
| Conversational | Frontier | Higher — reserved for high-value interaction |

### The Views Contract

Agents work in the normal workspace. A heartbeat step renders current state into `views/` as clean, React-consumable JSON. The React app watches `views/`, not the raw workspace.

```
Agents (read/write workspace)       React UI (reads views/)
        │                                    ▲
        ▼                                    │
   workspace/                                │
        │                                    │
        ▼ heartbeat renders                  │
   views/*.json  ───────────────────────────►│
```

**Why `views/` works as the UI contract:**

- **Decoupling** — workspace structure can evolve without breaking the UI
- **Performance** — React reads pre-computed JSON instead of parsing markdown
- **Future API boundary** — Telegram bridge or web dashboard serve the same `views/` over HTTP

**Heartbeat (v0.1):** Lightweight process rebuilds `views/` every N seconds (default 30s, configurable via `governance.yaml`).

### The Inbox Pattern (Write-Back)

The React UI reads from `views/` but never writes to `cards/`, `config/`, or `db/` directly. User actions write to `inbox/` — a queue of structured action requests processed through agent governance.

```
React UI                  inbox/                    Agent layer
─────────────────────────────────────────────────────────────────
Comment on card      →  action-{ts}.json       →  Curator attaches
Flag card stale      →  action-{ts}.json       →  Curator evaluates
Adjust domain weight →  action-{ts}.json       →  CONSTRUCT proposes
Suggest connection   →  action-{ts}.json       →  Curator evaluates
Promote manually     →  action-{ts}.json       →  Curator runs gates
Edit card metadata   →  action-{ts}.json       →  Curator validates
```

**Why the inbox, not direct writes:**
- Governance preserved — every action goes through agent validation
- Audit trail — logged in `events.jsonl`
- Async — UI fires and doesn't block; sees results on next `views/` update
- Same pattern as chat commands — agents don't care which surface generated the request

### Response Loop

When an agent processes an inbox action, results surface back through `views/responses.json`:

| Response type | UI rendering | Example |
|------|-------------|---------|
| `confirm` | Toast, auto-dismiss | "Card promoted." |
| `confirm_with_followup` | Notification + action buttons | "Archived. 2 orphans. Review?" |
| `question` | Modal dialog | "Contradicts card X. Keep both?" |
| `error` | Error notification | "Cannot promote: source tier below threshold." |
| `info` | Inline annotation | "Connection typed as 'extends'." |

### Pure UI Interactions (No Inbox)

Visual-only state that doesn't touch the knowledge graph:
- Filter, zoom, pan the graph
- Expand/collapse panels
- Sort lists
- Toggle visualization modes
- Browser-local bookmarks

---

## 5. Agent Specifications

### Curator v0.1 Scope

| Capability | Mechanism | LLM tier |
|-----------|-----------|----------|
| Orphan detection | Graph query — zero-connection cards | None (free) |
| Decay flagging | Date math — configurable window | None (free) |
| Integrity checks | Validation — dangling connections, missing fields | None (free) |
| Health stats | Aggregation — counts, distributions | None (free) |
| Rule-based auto-promotion | Two-tier: seed→growing (confidence ≥ 2, ≥ 1 connection); growing→mature (confidence ≥ 3, source ≤ 2, ≥ 2 connections) | None (free) |
| Rule-based auto-flagging | No source, low confidence with no connections after N days | None (free) |
| Duplicate detection | Exact title/URL match (not semantic) | None (free) |
| Ambiguous card evaluation | Cards that pass some promotion rules but not all | Workhorse |
| Connection type proposals | Two linked cards with untyped edge | Workhorse |
| Graph health summary | Natural language summary for dashboard | Workhorse |
| Escalation to CONSTRUCT | Conflicts, contradictions between mature cards | Frontier (via CONSTRUCT) |

**Deferred (v0.2+):** Category split suggestions, semantic duplicate detection (needs ChromaDB), cross-domain bridge proposals (L3/L4), UI inbox comment handling.

### Cross-Domain Detection Layers

| Layer | Mechanism | Catches | Cost | Release |
|-------|-----------|---------|------|---------|
| **L1: Graph structural** | Bridge detection, connection propagation | Connections partially already made — edge chains crossing domain boundaries | Free | v0.1 |
| **L2: Keyword/tag overlap** | Shared content categories + source references across domains | Topical overlap visible in metadata | Free | v0.1 |
| **L3: Embedding similarity** | Cards embedded via Ollama, top-K cross-domain scan | Semantic similarity humans miss at scale | Local (Ollama) | v0.2 |
| **L4: LLM reasoning** | Frontier model reasons about structural parallels across batches | Deep parallels — same math, isomorphic problems, shared design patterns | Frontier API | v0.2+ |

Each layer feeds the one above it. L4 is a research-frontier problem — the system proposes, the human decides.

---

## 6. v0.1 Scope (MVP)

### Ships in v0.1

1. **Python agent runtime** — session management, heartbeat, WebSocket chat, LLM provider abstraction
2. **CONSTRUCT agent** — thinking partner, orchestrator, co-authorship, cross-domain ideation
3. **Curator sub-agent** — graph maintenance, quality gates, decay detection, orphan flagging (see §5)
4. **Researcher sub-agent** — automated search cycles, API integrations, structured ingestion
5. **Knowledge graph** — markdown cards + YAML frontmatter, NetworkX-derived graph, CLI query
6. **BMAD-inspired workflows** — SKILL.md definitions for research cycle, curation, agent handoffs
7. **`views/` heartbeat** — renders workspace state as React-consumable JSON
8. **React UI** — graph visualization, card browser, domain config, agent status, activity timeline
9. **CLI** — `construct init / run / stop / status / graph stats / rebuild`
10. **Git integration** — all state versioned, diffs meaningful

### Ships in v0.2

- Synthesizer agent (essays, whitepapers, gap analyses from graph state)
- ChromaDB for semantic similarity and duplicate detection
- Export pipeline (markdown, PDF, DOCX)
- Search pattern historization UI
- Landscape diff view
- Basic Telegram bridge
- **MCP server + portable SKILL.md skill pack** (first integration cut — see §8) — covers opencode, Anthropic skills/subagents, GSD

### Ships in v0.3

- Narrator agent (publication voice, register-aware writing)
- Publishing pipeline (graph → article → platform)
- Hosted web dashboard
- Team features (multi-user, shared graph, roles)
- Embedding-based similarity for 500+ node graphs
- **BMAD-METHOD adapter** (YAML agent module + marketplace listing — see §8)

---

## 7. Stack Candidates Under Evaluation

These are documented but not adopted for v0.1. Evaluate when specific pain points emerge.

> **Note on framing:** This section asks *should CONSTRUCT depend on these stacks?* §8 covers the inverse question — *should CONSTRUCT ship as a drop-in inside these stacks?* The two questions are independent; opencode and BMAD appear in both sections in different roles.

### OpenCode — Terminal-Native AI Agent UI

[opencode.ai](https://opencode.ai/) | Apache 2.0, 120k+ stars

**Fit:** Strong candidate for terminal interaction layer. Production-grade TUI (Go/Bubble Tea), 75+ LLM models, multi-session. Could complement React UI for terminal-native users. LLM abstraction layer potentially reusable.

**Limitation:** Can't deliver interactive graph viz, heatmaps, or rich card panels.

**Trigger:** "I want terminal/IDE access to the knowledge graph" → evaluate OpenCode.

### HIVE — Agent Orchestration Runtime

[GitHub: aden-hive/hive](https://github.com/aden-hive/hive) | Apache 2.0

**Fit:** Strong candidate for agent runtime layer. Session isolation, crash recovery, cost tracking, human-in-the-loop, auto-recovery. LiteLLM integration (100+ providers). TUI dashboard.

**Limitation:** No knowledge graph / epistemic concepts. Younger project — evaluate stability.

**Trigger:** "Agents crash mid-cycle and I lose progress" or "I need cost caps" → evaluate HIVE.

### BMAD Method — Workflow Methodology

[docs.bmad-method.org](https://docs.bmad-method.org/) | [GitHub](https://github.com/bmad-code-org/BMAD-METHOD)

**Decision:** Adopt BMAD's *patterns* (progressive context, skill format, handoff chains) natively. No dependency on BMAD framework or OpenClaw bridge (bridge evaluated as early PoC, not production-ready). CONSTRUCT implements its own SKILL.md definitions with knowledge-domain semantics.

See [capability matching §6.1](construct-capability-matching.md) for the full evaluation.

---

## 8. External Framework Integration (v0.2 / v0.3)

CONSTRUCT's primary deployment is as a self-contained system (chat + React UI + CLI). A secondary deployment target — planned for v0.2 / v0.3 — is as an installable adapter inside the major external agent frameworks: **opencode**, **Anthropic skills/subagents**, **GSD (get-shit-done)**, and **BMAD-METHOD**.

This section captures the integration intent, the per-framework adapter shape, and most importantly the **forward-compatibility constraints v0.1 must respect** so this future work does not require a re-architecture.

### 8.1 Intent

CONSTRUCT exposes its capabilities through a framework-agnostic interface (MCP) and ships a portable skill pack. Reference adapters ship for opencode, Anthropic skills/subagents, GSD, and BMAD. The core remains independently runnable. **CONSTRUCT's semantic memory remains the canonical store regardless of which host framework consumes it.**

### 8.2 The Convergence We Exploit

`SKILL.md` (a folder containing `SKILL.md` with YAML frontmatter, plus optional `scripts/`, `references/`, `assets/`) has emerged as the de facto cross-framework skill format. opencode, Anthropic skills/subagents, and GSD all consume the same file format — they differ only in discovery paths (`.opencode/skills/`, `.claude/skills/`, etc.).

This means **one CONSTRUCT skill pack covers three of four targets** with only path/install differences. BMAD-METHOD is the outlier — it uses its own `.agent.yaml` source format compiled to markdown, with a module-based marketplace.

### 8.3 Per-Framework Adapter Shape

| Framework | Distribution | Integration mechanism |
|-----------|--------------|------------------------|
| opencode | npm package + `opencode.json` block | SKILL.md skills dropped into `.opencode/skills/`; MCP server registered in `mcp` key |
| Anthropic skills/subagents | SKILL.md drop-in to `.claude/skills/` | Same skill files; MCP server registered separately |
| GSD (get-shit-done) | `agent_skills` injection via npm install | Same SKILL.md files; MCP deferred until GSD adds support (their issue #382) |
| BMAD-METHOD | YAML `.agent.yaml` + `module.yaml`, published to bmad-plugins-marketplace | MCP bridged via `bmad-mcp-server` pattern; CONSTRUCT positioned as a "Research Analyst" persona |

### 8.4 Memory Model Decision

Each host framework has its own memory model: BMAD has per-agent sidecars (`_bmad/_memory/`), GSD has a `.planning/` directory of state files, opencode leaves memory to plugins, Anthropic skills get memory via subagent context.

**Decision:** CONSTRUCT's semantic memory is the canonical store, exposed via MCP tools (`memory.read`, `memory.write`, `memory.query`). Each host framework's native memory location is treated as a *projection* — pointer files that defer to CONSTRUCT for actual content. This respects each framework's UX (a BMAD user can still browse `_bmad/_memory/`) without forking the source of truth.

### 8.5 v0.1 Forward-Compatibility Constraints

To keep the v0.2 / v0.3 integration cheap, v0.1 must respect these constraints. None of these are new design directions — they sharpen choices §3 and §4 already make. Documenting them here as constraints prevents drift.

| Constraint | Why |
|------------|-----|
| **Capabilities exposed through a stable internal Python API**, not buried in chat/CLI handlers | The future MCP server is a thin wrapper around this API. If every entry point lives inside chat/CLI code, the wrap step becomes a refactor. |
| **`workflows/` SKILL.md definitions stay format-compatible with the open SKILL.md spec** — folder + `SKILL.md` + YAML frontmatter, no CONSTRUCT-only frontmatter keys without a `construct.*` namespace prefix | These files become the basis of the cross-framework skill pack. Namespacing CONSTRUCT-specific keys lets them round-trip through other frameworks without conflict. |
| **Memory access is mediated, not direct** — no CONSTRUCT-internal code reads `cards/` files directly; everything goes through a memory/storage interface | The future MCP `memory.*` tools wrap the same interface. Direct file access would mean MCP callers and in-process callers see different things. |
| **Every CLI / chat command is a thin shell over a programmatic callable** | If `/synthesize <topic>` only exists as a chat command, an external BMAD or opencode agent calling `construct.synthesize(topic)` has no entry point. |
| **HITL responses are addressable by ID, not implicit on the chat session** | Inbox actions (§4) already follow this pattern; extend it so external frameworks can submit HITL questions and poll/await responses without needing an interactive chat surface. |

### 8.6 Workflow Alignment Opportunities (Positioning)

Two of the target frameworks have native workflow models that CONSTRUCT's research-curation loop maps onto, suggesting stronger positioning than "generic plugin":

- **GSD's six-phase workflow** (Initialize → Discuss → Plan → Execute → Verify → Complete) maps onto CONSTRUCT as: ingest → view-proposals → curation → publication, with HITL adaptation as the Verify phase. CONSTRUCT can ship as a *research-workflow specialization* rather than a generic skill bundle.
- **BMAD's persona/handoff model** has a natural slot for CONSTRUCT as a **Research Analyst** persona that decomposes inquiry into curation tasks for downstream agents (PM, architect, dev).

These are positioning notes for the v0.2 / v0.3 spec work; not v0.1 constraints.

### 8.7 Out of Scope for v0.1

- Building any of the four adapters
- Publishing to bmad-plugins-marketplace, npm, or any skill registry
- The MCP server itself (only its forward-compatibility footprint, per §8.5)
- Adapter test suites and host-framework CI

### 8.8 Open Questions (deferred to v0.2 spec)

1. **MCP transport** — stdio (subprocess) vs. local HTTP? Most clients prefer stdio; HTTP is friendlier for the BMAD bridge.
2. **Auth** — does the v2.0 cloud layer change MCP auth requirements? Local-only stdio sidesteps the question for v0.2.
3. **License compatibility** — how does the chosen CONSTRUCT license (Apache-2.0 proposed, §12) interact with each target framework's distribution model?
4. **Resource exposure** — should `publish/` outputs be exposed as MCP *resources* (not just memory tools) so downstream agents can consume curated articles directly?
5. **Capability negotiation** — when CONSTRUCT v0.4 adds a new MCP tool, how do older adapters degrade gracefully?

---

## 9. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interaction                         │
│                                                              │
│  ┌──────────────────┐       ┌─────────────────────────────┐  │
│  │ React Chat        │       │ React UI (localhost)        │  │
│  │ Agent commands    │       │ Knowledge graph viz         │  │
│  │ Brainstorming     │       │ Card browser · Dashboards   │  │
│  │ Research steering │       │ Domain config · Timeline    │  │
│  └────────┬─────────┘       └──────────────▲──────────────┘  │
│           │                                │                  │
│           ▼                                │ watches          │
│  ┌─────────────────────────────────┐  ┌────┴──────────────┐  │
│  │ CONSTRUCT Core (Python)         │  │ views/            │  │
│  │ Agent runtime · LLM calls       │  │ graph.json        │  │
│  │ Session management              │  │ cards/*.json      │  │
│  │ SOUL/IDENTITY governance        │──►│ landscape.json    │  │
│  │                                 │  │ agents-status.json│  │
│  │  ┌─────────────────────────┐    │  │ events.jsonl      │  │
│  │  │ BMAD-Inspired Workflows │    │  └───────────────────┘  │
│  │  │ SKILL.md definitions    │    │     heartbeat builds    │
│  │  │ Agent handoff chains    │    │     from workspace      │
│  │  │ Progressive context     │    │                         │
│  │  └─────────────────────────┘    │                         │
│  └────────────────┬────────────────┘                         │
│                   ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Local Filesystem (Git)                                │    │
│  │ cards/ · config/ · refs/ · log/ · inbox/ · views/     │    │
│  │ publish/ (external outputs, git-tracked)              │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### The Layering

- **CONSTRUCT Core (Python)** — agent runtime, chat interface, LLM integration. The engine.
- **BMAD-inspired workflows** — formalized agent handoffs and research cycles as SKILL.md definitions.
- **`views/`** — UI interface contract. Pre-computed JSON, disposable, heartbeat-rebuilt.
- **`publish/`** — external outputs. Curated articles, reports, exports. Git-tracked.
- **React UI** — visual viewer. Reads `views/`, renders graph, dashboards, card browsers.
- **Git** — versioning backbone. The workspace *is* the repository.

---

## 10. Optional Cloud Layer (v2.0)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Telegram bridge | Python (python-telegram-bot) | Mobile interaction: seeds, digests, research triggers |
| Web dashboard | Same React app, deployed | Serve `views/` over HTTP. Same files, different transport. |
| Sync | Git (GitHub) or custom API | Push/pull workspace state |

---

## 11. Deferred Stack Decisions

| Trigger | Then evaluate |
|---------|---------------|
| "I need to swap LLM providers without changing agent code" | → **LiteLLM** |
| "Agents crash mid-cycle and I lose progress" or "I need cost caps" | → **HIVE** as orchestration layer |
| "I want terminal/IDE access to the knowledge graph" | → **OpenCode** or custom CLI |

---

## 12. Open Technical Questions

1. **Views heartbeat granularity:** How often does the heartbeat rebuild `views/`? 5s / 30s / on-demand? Trade-off: UI responsiveness vs. CPU. Default: 30s debounced.

2. **License:** Apache-2.0 proposed, not formally decided.

---

*This PRD will evolve as implementation proceeds. For product vision and user interactions, see the companion [Product Brief](construct-product-brief.md).*
