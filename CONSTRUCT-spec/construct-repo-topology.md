# CONSTRUCT — Repository Topology

**Version:** 0.1.0
**Date:** 2026-04-21
**Status:** Accepted (per ADR-0001, Option D)
**Resolves:** Gap analysis §3.2.1

---

## 1. Separation from MABSTRUCT

The `construct` repository is **completely separate** from `mabstruct-workspace`.

| Concern | Where it lives |
|---------|---------------|
| Product specs, planning, ADRs | `mabstruct-workspace/CONSTRUCT-product-development/` |
| Source code, tests, CI, runtime | `construct/` (its own git repo) |
| Running MABSTRUCT system | `mabstruct-workspace/` (unchanged) |

The planning workspace is a starting reference. Once the repo exists, specs migrate into `construct/specs/` and the planning workspace becomes archival.

---

## 2. Top-Level Directory Tree

```
construct/
├── .github/
│   └── workflows/
│       └── ci.yml                    # pytest + vitest + ruff + mypy + tsc + vite build
│
├── src/
│   └── construct/                    # Python package (the entire product)
│       ├── __init__.py               # Version, entry point
│       ├── cli.py                    # construct init / status / run / stop
│       ├── server.py                 # HTTP + WebSocket (serves UI + chat + events)
│       │
│       ├── agents/                   # Agent runtime
│       │   ├── __init__.py
│       │   ├── orchestrator.py       # CONSTRUCT agent — top-level delegation
│       │   ├── curator.py            # Card lifecycle, connections, decay
│       │   ├── researcher.py         # Search, fetch, ingest, refs
│       │   ├── session.py            # Session model, heartbeat, state machine
│       │   └── llm.py               # LLM provider abstraction (tiered model routing)
│       │
│       ├── graph/                    # Knowledge graph engine
│       │   ├── __init__.py
│       │   ├── build.py              # NetworkX graph from cards/ directory
│       │   ├── query.py              # Traversals, bridge detection, clusters
│       │   └── metrics.py            # Graph health: orphans, density, staleness
│       │
│       ├── storage/                  # Persistence
│       │   ├── __init__.py
│       │   ├── indexer.py            # Walk SOT → populate SQLite + FTS5
│       │   ├── rebuild.py            # Full index rebuild from source of truth
│       │   └── sqlite.py             # Connection management, schema migrations
│       │
│       ├── research/                 # External knowledge acquisition
│       │   ├── __init__.py
│       │   ├── search.py             # Search seed management, query generation
│       │   ├── clients/              # API clients (Semantic Scholar, arXiv, web)
│       │   └── ingest.py             # Reference parsing, card drafting
│       │
│       ├── views/                    # Internal UI data layer renderer
│       │   ├── __init__.py
│       │   └── heartbeat.py          # Rebuild views/ on timer (debounced)
│       │
│       └── workflows/                # BMAD-inspired skill execution
│           ├── __init__.py
│           └── engine.py             # SKILL.md parser, handoff chains
│
├── ui/                               # React UI (Vite build → static artifact)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── stores/                   # Zustand state
│   │   ├── components/               # Shared components
│   │   ├── pages/                    # Route-level views
│   │   │   ├── Graph.tsx             # D3 force-directed graph
│   │   │   ├── Cards.tsx             # Card browser / reader
│   │   │   ├── Chat.tsx              # WebSocket chat interface
│   │   │   └── Dashboard.tsx         # Agent status, recent events
│   │   ├── hooks/                    # Custom React hooks
│   │   └── types/                    # Generated from Pydantic (JSON Schema → TS)
│   └── public/
│
├── templates/                        # Governance artifacts (git-tracked, not code)
│   ├── agents/                       # SOUL.md, IDENTITY.md per agent
│   │   ├── construct/
│   │   │   ├── SOUL.md
│   │   │   └── IDENTITY.md
│   │   ├── curator/
│   │   └── researcher/
│   ├── configs/                      # Default YAML configs
│   │   ├── domains.yaml
│   │   ├── governance.yaml
│   │   └── model-routing.yaml
│   └── workflows/                    # SKILL.md workflow definitions
│       ├── domain-init.md
│       └── research-cycle.md
│
├── specs/                            # Product specs (migrated from planning workspace)
│   └── ...
│
├── dev/                              # Development process
│   ├── CURRENT.md                    # Living state tracker
│   ├── decisions/                    # ADRs
│   │   └── adr-0001-python-first-drop-openclaw.md
│   └── plans/                        # Implementation plans (per task)
│
├── tests/                            # Test suite (mirrors src/ structure)
│   ├── conftest.py                   # Shared fixtures, fixture workspace
│   ├── fixtures/                     # Reusable test data
│   │   └── workspace/               # 5-card fixture workspace (per test strategy)
│   │       ├── cards/
│   │       ├── domains.yaml
│   │       └── expected_views/
│   ├── unit/
│   │   ├── test_graph_build.py
│   │   ├── test_graph_query.py
│   │   ├── test_indexer.py
│   │   ├── test_card_schema.py
│   │   └── test_session.py
│   ├── integration/
│   │   ├── test_heartbeat_pipeline.py
│   │   └── test_research_cycle.py
│   └── contract/
│       └── test_views_schema.py
│
├── scripts/                          # Dev tooling
│   ├── dev.sh                        # Start dev server (Python + Vite HMR)
│   └── generate-types.sh             # Pydantic → JSON Schema → TS types
│
├── CLAUDE.md                         # Working agreements for Claude Code
├── pyproject.toml                    # Python project config (ruff, mypy, pytest, build)
├── LICENSE                           # Apache-2.0
├── README.md                         # Project README
└── .gitignore
```

---

## 3. Four-Category Storage Model

A CONSTRUCT **workspace** (the runtime data directory, distinct from the repo) follows this layout:

```
~/my-knowledge-workspace/              # User's workspace (construct init creates this)
│
├── cards/                             # ── Source of Truth (git-tracked) ──
│   ├── concept-neural-scaling.md      # Knowledge cards: YAML frontmatter + body
│   └── ...
├── domains.yaml                       # Domain definitions
├── governance.yaml                    # Agent governance config
├── model-routing.yaml                 # LLM tier configuration
├── search-seeds.json                  # Research search patterns
├── refs/                              # Reference library (per-paper JSON)
├── workflows/                         # SKILL.md definitions
│
├── inbox/                             # ── Agent Workspace (git-tracked) ──
│   ├── action-001.json                # Proposed actions awaiting governance
│   └── ...
├── digests/                           # Research cycle digests (per domain)
│   └── {domain}/
│       └── digest-{date}.md
├── log/
│   └── events.jsonl                   # Structured event log
│
├── db/                                # ── Persistent Indexes (gitignored, rebuildable) ──
│   ├── construct.db                   # SQLite + FTS5
│   └── chroma/                        # ChromaDB (v0.2)
│
├── views/                             # ── Disposable Views (gitignored, heartbeat-rebuilt) ──
│   ├── graph.json                     # D3 node-link format
│   ├── cards/                         # Denormalized card JSON for UI
│   ├── landscape.json                 # Domain / cluster overview
│   ├── agents-status.json             # Agent health
│   ├── events-recent.json             # Last N events
│   └── responses.json                 # Chat response queue
│
└── publish/                           # ── Curated Outputs (git-tracked) ──
    ├── articles/                      # Long-form synthesized articles
    ├── reports/                       # Analysis reports
    ├── drafts/                        # Work-in-progress (v0.2, Narrator agent)
    └── exports/                       # Visualizations, data exports
```

### Git tracking rules

| Category | Tracked | Why |
|----------|---------|-----|
| Source of Truth | Yes | The canonical knowledge |
| Agent Workspace | Yes | Audit trail for governance |
| Persistent Indexes | No | Rebuildable from SOT via `construct rebuild` |
| Disposable Views | No | Heartbeat-rebuilt every 30s |
| Curated Outputs | Yes | Intentional external artifacts |

### .gitignore (workspace)

```gitignore
# Persistent indexes (rebuildable)
db/

# Disposable views (heartbeat-rebuilt)
views/

# OS / editor
.DS_Store
*.swp
```

---

## 4. Module Ownership

| Module | Responsibility | Key dependencies |
|--------|---------------|-----------------|
| `construct.agents` | Agent lifecycle, session, heartbeat, delegation | `construct.llm`, `construct.graph`, `construct.storage` |
| `construct.agents.llm` | LLM provider abstraction, tiered model routing | httpx (API), ollama (local) |
| `construct.graph` | Build graph from cards, traversals, metrics | networkx |
| `construct.storage` | SQLite indexer, FTS5 search, rebuild | sqlite3 (stdlib) |
| `construct.research` | External APIs, ingestion, reference mgmt | httpx, `construct.storage` |
| `construct.views` | Heartbeat renderer: SOT+graph → views/*.json | `construct.graph`, `construct.storage` |
| `construct.workflows` | SKILL.md parser, handoff chain execution | `construct.agents` |
| `construct.server` | HTTP (static UI) + WebSocket (chat, events) | starlette or uvicorn |
| `construct.cli` | CLI entry points (init, status, run, stop) | click or typer |
| `ui/` | React SPA consuming views/ via WebSocket | react, d3, zustand, tailwindcss |

---

## 5. Build & Package

```toml
# pyproject.toml (key sections)
[project]
name = "construct"
requires-python = ">=3.11"

[project.scripts]
construct = "construct.cli:main"

[tool.ruff]
target-version = "py311"

[tool.mypy]
strict = true
```

The UI builds as a Vite static artifact:
1. `cd ui && npm run build` → produces `ui/dist/`
2. `construct.server` serves `ui/dist/` at `/` and WebSocket at `/ws`
3. `scripts/dev.sh` runs Vite HMR + Python server concurrently for development

---

## 6. Dependency Graph (Python)

```
construct.cli
  └── construct.server
        ├── construct.agents.orchestrator
        │     ├── construct.agents.curator
        │     │     ├── construct.graph
        │     │     └── construct.storage
        │     ├── construct.agents.researcher
        │     │     ├── construct.research
        │     │     └── construct.storage
        │     └── construct.agents.llm
        ├── construct.views.heartbeat
        │     ├── construct.graph
        │     └── construct.storage
        └── construct.workflows.engine
              └── construct.agents
```

No circular dependencies. `construct.graph` and `construct.storage` are leaf modules.
