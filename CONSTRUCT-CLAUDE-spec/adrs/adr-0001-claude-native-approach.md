# ADR-0001: Claude-Native Implementation Approach

**Status:** Accepted
**Date:** 2026-04-23
**Deciders:** ;-)mab
**Context:** CONSTRUCT product has a Python-first implementation plan (CONSTRUCT-spec/). This ADR records the decision to pursue a parallel Claude-native approach.

---

## Context

CONSTRUCT is an agent-powered personal knowledge system. The original implementation plan (ADR-0001 in CONSTRUCT-spec/) chose a Python-first architecture: FastAPI, SQLite, NetworkX, React UI — a full custom backend where agents are Python classes calling LLM APIs.

Since that decision, Claude's capabilities have matured significantly:
- **File operations:** Claude can read, write, and manage files in a workspace directory
- **Web search:** Claude can search the web and extract structured information
- **Tool use:** Claude can invoke structured tools as part of reasoning
- **Dialog management:** Claude handles multi-turn conversations with context natively
- **Session persistence:** Claude maintains context within and across sessions
- **Reasoning depth:** Claude can perform the frontier reasoning CONSTRUCT requires for cross-domain ideation, synthesis, and editorial judgment

The entire CONSTRUCT agent runtime — session management, task routing, LLM calls, heartbeat cycles — is infrastructure that Claude already provides.

---

## Decision

Implement CONSTRUCT as **Claude agent configuration** — agent definitions, skills, workflows, templates, and reference tables — deployed as files in Claude's configuration directory (`~/.claude/`).

Claude IS the runtime. No Python backend, no SQLite, no React UI, no FastAPI server.

---

## Options Considered

### Option A: Python-First (Original Plan)

Build everything as a Python application per CONSTRUCT-spec/.

**Pros:**
- Full control over runtime behavior
- Custom UI with D3 graph visualization
- Offline capability (Ollama)
- Deterministic indexing (SQLite + FTS5)

**Cons:**
- Months of implementation across 8 phases
- Two languages (Python + TypeScript)
- Infrastructure code (session management, heartbeat, WebSocket) dominates
- Agent behavior is code, making iteration slow

### Option B: Claude-Native (This Decision)

Configure Claude to be CONSTRUCT through agent files, skills, and templates.

**Pros:**
- Zero infrastructure code — Claude handles dialog, search, reasoning, files
- Days to configure vs. months to build
- Skills are markdown — iterate by editing text, not code
- Frontier reasoning comes free (no API client to build)
- Web search comes free (no httpx/API clients to build)
- Session management comes free
- Immediate usability — works as soon as config is deployed
- Interactive visualization via artifacts — D3 graphs, charts, and dashboards without a custom frontend (see §Mitigations)
- MCP extensibility — Claude connects to external tools/data via connectors, enabling future scale solutions without rebuilding

**Cons:**
- ~~No custom UI (graph visualization, D3, dashboard)~~ → **Mitigated** by artifacts (React/D3), inline visualizations, Claude Design, and interactive MCP connectors (see §Mitigations)
- Dependent on Claude's capabilities and availability
- No offline mode (no Ollama fallback)
- ~~No deterministic indexing (Claude reads files each time)~~ → **Mitigatable** via CONSTRUCT MCP server + SQLite index layer (see §Future Enhancements)
- ~~Performance at scale (>1000 cards) untested~~ → **Partially mitigatable** via MCP + DB for filtered queries and aggregation (see §Future Enhancements)

### Option C: Hybrid

Build the data layer in Python, use Claude as the agent layer.

**Deferred (not rejected):** For v0.1, this over-engineers the problem — Claude can read files directly and artifacts handle visualization. However, as the workspace scales beyond ~500 cards, a lightweight MCP server + SQLite index becomes a natural evolution. This is now tracked in §Future Enhancements as the convergence path. The key difference from the original hybrid proposal: the Python layer serves Claude via MCP rather than replacing Claude's runtime.

---

## Consequences

### Positive
- CONSTRUCT becomes usable immediately after configuration
- Knowledge model and governance are identical — workspace format is shared
- Skills are editable text — non-programmers can customize agent behavior
- Future: if Python approach is also built, same workspace works with both

### Negative
- ~~No visual graph exploration (Claude is text-based)~~ → **Mitigated** — see §Mitigations below
- Scale limited by Claude's context window for large workspaces → **Partially mitigatable** via MCP + DB (see §Future Enhancements)
- Dependent on Anthropic's infrastructure availability
- ~~Some operations (counting all cards, computing graph metrics) may be slower than SQLite queries~~ → **Mitigatable** via MCP + DB (see §Future Enhancements)

### Neutral
- Both approaches can coexist — they share the workspace format
- The Python approach can be built later as a complement (e.g., for the UI layer)
- This decision doesn't invalidate CONSTRUCT-spec/; it adds a parallel path

---

## Mitigations: Visual Graph Exploration via Live Artifacts (Spike)

**Status:** Spike candidate — validated as feasible, not yet implemented

The original "no visual graph exploration" negative assumed Claude is purely text-based. As of April 2026, Claude's artifact and visualization capabilities substantially close this gap:

### Available capabilities (April 2026)

| Capability | Source | CONSTRUCT relevance |
|-----------|--------|-------------------|
| **Interactive React/D3 artifacts** | Artifacts (GA) | Force-directed graph of cards + connections, filterable by domain, colored by confidence/lifecycle |
| **AI-powered artifacts** | Artifacts (GA) | Graph artifact with embedded Claude intelligence — ask questions about graph structure, get explanations of clusters |
| **Persistent storage** (20MB/artifact) | Artifacts (GA) | Cache graph layout, user preferences, and exploration state across sessions |
| **Inline interactive visualizations** | Mar 2026 release | Claude generates charts/diagrams inline during conversation — domain coverage heatmaps, confidence distributions, timeline views |
| **MCP integration in artifacts** | Artifacts + MCP | Artifact reads live workspace data via MCP tools — real-time graph that reflects current card state |
| **Interactive MCP connectors** | MCP connectors (beta) | Inline cards and fullscreen dashboards rendered directly in conversation — graph explorer as a connector |
| **Claude Design** | Apr 17, 2026 (Anthropic Labs) | Code-powered interactive prototypes with 3D, shaders, built-in AI — polished graph exploration UI without a custom frontend |

### Spike proposal: CONSTRUCT Graph Artifact

Build an interactive artifact that reads CONSTRUCT workspace files and renders the knowledge graph:

1. **Input:** `connections.json` + card frontmatter (YAML) pasted or read via MCP
2. **Render:** D3 force-directed graph — nodes are cards, edges are typed connections
3. **Interactions:** Click node → card summary; filter by domain/lifecycle/confidence; color by epistemic type; cluster by domain
4. **AI-powered:** User asks "what are the weakest areas?" → Claude analyzes graph structure and highlights gaps
5. **Persistent:** Layout and filter preferences survive across sessions via artifact storage

**What this does NOT solve:** Real-time watching of workspace file changes (artifacts are session-scoped, not filesystem-reactive). For that, a lightweight MCP server or the Python complement is needed.

### Validation criteria for spike
- [ ] Artifact renders ≥50 cards with connections as interactive D3 graph
- [ ] Click-to-inspect shows card metadata (type, confidence, domain, summary)
- [ ] Domain filtering works
- [ ] Artifact storage persists layout across conversations
- [ ] AI-powered queries about graph structure return useful answers

---

## Future Enhancements: MCP + DB Integration

**Status:** Not started — backlog for after v0.1

Two capabilities can further close the remaining gaps (scale, query speed):

### MCP Integration (CONSTRUCT MCP Server)

Build a lightweight MCP server that exposes CONSTRUCT workspace operations as tools:

| Tool | Purpose | Mitigates |
|------|---------|----------|
| `list_cards(domain?, lifecycle?, min_confidence?)` | Filtered card listing without loading all files | Context window pressure |
| `get_card(id)` | Read single card by ID | Targeted access vs. scanning |
| `search_cards(query)` | Full-text search across card content | Slow file-by-file search |
| `graph_stats()` | Card counts, connection stats, domain coverage | Slow aggregate computations |
| `add_connection(source, target, type)` | Create typed connection | Direct write without full file management |
| `run_curation_check()` | Trigger decay scan and integrity check | Automated maintenance |

This server could be a thin Python (FastAPI) or Node layer over the workspace files — or over a SQLite index for scale. Claude connects to it as a custom connector from any surface (web, desktop, Cowork).

**Interactive connector variant:** The MCP server could render interactive UI (inline cards, fullscreen graph dashboard) directly in Claude conversations, using the interactive connector capability.

### SQLite Index Layer

A local SQLite + FTS5 database that indexes workspace files, providing:
- Deterministic queries (count, aggregate, full-text search)
- Graph metrics via SQL rather than Claude reasoning
- Rebuiltable from canonical markdown/YAML at any time (maintains the "derived, not source-of-truth" principle)

This aligns with the Python approach's `db/` layer but serves as a queryable cache for the Claude-native approach via MCP, rather than requiring a full Python application.

### Combined architecture (future state)

```
User ↔ Claude (agent runtime)
         ↕ MCP
   CONSTRUCT MCP Server
         ↕
   Workspace files (canonical)  ←→  SQLite index (derived)
         ↕
   Artifact (interactive graph UI)
```

This hybrid closes nearly all the original negatives while keeping the core principle: **Claude is the runtime, markdown is the truth, everything else is derived.**

---

## Relationship to CONSTRUCT-spec/ADR-0001

The Python-first ADR (dropping OpenClaw) remains valid for the Python approach. This new ADR doesn't supersede it — it opens a second implementation path. The knowledge model, epistemic governance, and workspace format are shared artifacts.

The MCP + DB integration path (§Future Enhancements) may converge the two approaches: the Python layer becomes a service layer that both the React UI and Claude access through the same interface.
