# Technology Stack — CONSTRUCT

**Scope:** Stack research for a local-first, Python-first, agent-powered personal knowledge system  
**Researched:** 2026-04-22  
**Overall recommendation confidence:** HIGH

## Executive Recommendation

Use a **Python 3.12-first ASGI app** with **FastAPI + Uvicorn**, **Pydantic v2**, **NetworkX**, **stdlib sqlite3 + FTS5**, **HTTPX**, and a **React 19 + Vite 8** frontend that consumes heartbeat-generated JSON in `views/` and uses a plain browser **WebSocket** for chat/events.

This is the standard 2026 stack for this shape of product because it stays **single-language on the backend**, keeps the data model **local and rebuildable**, and avoids introducing infrastructure that only pays off in multi-user or cloud deployments. For CONSTRUCT specifically, the winning pattern is **typed Python core + file-based source of truth + derived SQLite/graph/view layers**.

## Recommended Stack

### 1) Runtime + Server

| Technology | Version guidance | Use for | Why this is the right choice | Confidence |
|---|---:|---|---|---|
| Python | **3.12 target**, support `>=3.11,<3.14` | Entire backend/runtime | 3.12 is the current sweet spot for performance, packaging maturity, and library compatibility while honoring the project's 3.11+ constraint. | HIGH |
| FastAPI | `~=0.136` | Local HTTP server + WebSocket routes + typed app surface | FastAPI is now the default typed Python app stack. It gives you Starlette's ASGI/WebSocket core plus first-class Pydantic integration. CONSTRUCT benefits from typed contracts more than it benefits from ultra-minimalism. | HIGH |
| Uvicorn | `~=0.45` | ASGI server | Standard FastAPI/Starlette runtime. Enough for localhost serving, static assets, and WebSocket chat without extra infra. | HIGH |
| Starlette | transitively via FastAPI, pin only if needed | WebSocket primitives, static serving, ASGI foundations | WebSocket support is directly inherited from Starlette. Use FastAPI as the app layer, not raw Starlette, unless you later prove FastAPI overhead matters. | HIGH |

**Recommendation:** prefer **FastAPI over raw Starlette** for v0.1. You still get Starlette's WebSocket primitives, but you also get cleaner typed contracts for views metadata, agent commands, health endpoints, and future API boundaries.

### 2) Schemas, Config, and Serialization

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| Pydantic | `~=2.13` | Canonical models for cards, configs, inbox actions, view schemas, WS payloads | Pydantic v2 is the standard typed data layer in Python. It emits JSON Schema cleanly and fits the repo topology's Python→TS contract generation. | HIGH |
| pydantic-settings | `~=2.14` | Environment/config loading | Clean separation between workspace config, env vars, and runtime settings. | HIGH |
| orjson | `~=3.11` | Fast JSON serialization for `views/` artifacts and WS payloads | Heartbeat-generated views are JSON-heavy; `orjson` is the standard performance upgrade without architecture cost. | HIGH |
| ruamel.yaml | `>=0.18,<0.20` | YAML frontmatter + config round-tripping | Better fit than PyYAML when humans edit the source of truth and you may want stable formatting or comment preservation. | MEDIUM |

**Recommendation:** model everything important in **Pydantic**, then generate TS types from JSON Schema. This keeps Python as the source of truth and stops schema drift between backend and React.

### 3) Knowledge Source of Truth + Parsing

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| Markdown files | n/a | Canonical knowledge cards | Matches the product's local-first, git-diffable, human-readable constraint exactly. | HIGH |
| ruamel.yaml frontmatter | see above | Card metadata and workspace configs | Stronger fit than JSON/TOML for human-edited metadata blocks that need validation after parse. | MEDIUM |
| markdown-it-py | `~=4.0` | Markdown rendering/parsing when you need AST or safe transforms | Good modern Python markdown parser if CONSTRUCT needs structured rendering or previews. Keep the graph semantics in YAML + app logic, not markdown AST tricks. | MEDIUM |

**Recommendation:** keep markdown parsing **boring**. Parse frontmatter deterministically, treat the markdown body mostly as content, and avoid building product logic on clever markdown AST mutations.

### 4) Graph + Indexing

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| NetworkX | `~=3.6` | Derived in-memory graph for traversals, bridge detection, cluster metrics | Exactly right for CONSTRUCT's v0.1 scale. It is simple, well-known, Python-native, and avoids graph-database operational weight. | HIGH |
| sqlite3 (stdlib) | Python-bundled; require **FTS5 enabled** | Structured index and metadata/query store | The right default for a local-first app. Zero extra service, durable, inspectable, and easy to rebuild from markdown. | HIGH |
| SQLite FTS5 | built into SQLite; verify on target machines | Full-text search over cards/refs/events | FTS5 is still the standard local full-text engine. It supports MATCH, prefix queries, ranking, tokenizers, and rebuild workflows without adding a separate search service. | HIGH |
| Hand-written SQL migrations | n/a | Schema and index evolution | Better than adding an ORM for an index-heavy local app. Your search schema is closer to a search/index engine than a business CRUD app. | HIGH |

**Recommendation:** use **stdlib `sqlite3` + raw SQL + FTS5 virtual tables**. Do **not** add SQLAlchemy/SQLModel in v0.1. They add abstraction where CONSTRUCT mainly needs explicit FTS tables, triggers/rebuilds, and predictable local file DB behavior.

### 5) Agent / Provider Integration Layer

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| HTTPX | `~=0.28` | All outbound provider/API calls | Standard modern Python HTTP client with sync/async APIs, HTTP/2 support, and strong typing. Good fit for Anthropic/OpenAI APIs, Ollama, arXiv, Semantic Scholar, and generic web fetches. | HIGH |
| Tenacity | `~=9.1` | Retry/backoff around provider and research calls | Simple, mature resilience layer for local agents that should continue after transient failures. | HIGH |
| Native provider adapters | app code | Anthropic/OpenAI/Ollama abstraction | A thin in-repo adapter layer keeps routing logic local and avoids framework lock-in. This project needs stable provider routing more than generic agent-framework abstractions. | MEDIUM |

**Recommendation:** build a **thin provider abstraction over HTTPX**, not a heavyweight agent framework. For CONSTRUCT, the durable asset is the knowledge graph and governance model, not the orchestration library.

### 6) CLI + Local Developer Experience

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| Typer | `~=0.24` | `construct init/run/status/rebuild/...` CLI | Still the best Python CLI fit for type-hint-driven command trees and good UX. It matches the team's FastAPI/Pydantic style. | HIGH |
| watchfiles | `~=1.1` | Dev-time file watching / heartbeat triggers | Helpful for local rebuild ergonomics; optional in prod because heartbeat can remain timer-based. | MEDIUM |

### 7) Frontend

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| React | `^19.2` | UI component layer | Standard 2026 choice for this kind of operator-style SPA. Mature ecosystem, strong TS ergonomics, and ideal for graph explorer + dashboard + chat surfaces. | HIGH |
| TypeScript | `^6.0` | UI type safety | Necessary because backend schemas should flow into generated TS types and event/view contracts. | HIGH |
| Vite | `^8.0` | Frontend dev/build pipeline | Still the default lightweight React build tool. Perfect for "build static assets, serve from Python" architecture. | HIGH |
| Zustand | `^5.0` | Small client-side UI state | Right-sized for filter state, panel state, selection state, and ephemeral chat UI state. Less boilerplate than Redux for a views-driven UI. | HIGH |
| D3 | `^7.9` | Force graph layout and graph interactions | D3 remains the standard when you need custom graph interaction instead of canned node editors. CONSTRUCT needs custom graph semantics more than generic flowchart tooling. | HIGH |
| react-router-dom | `^7.14` | Route-level navigation | Useful if graph, cards, dashboard, and chat are separate route surfaces. | MEDIUM |
| Tailwind CSS | `^4.2` with `@tailwindcss/vite` | Styling system | Fastest path to an internal-tool-quality UI with good density control and dark-mode ergonomics. | HIGH |

**Recommendation:** keep the frontend **thin**. It should render `views/*.json`, manage local interaction state, and use one WebSocket for chat/events. It should not become a second application server.

### 8) Realtime + View Model Pattern

| Technology | Version guidance | Use for | Why | Confidence |
|---|---:|---|---|---|
| Browser WebSocket API | standard | Chat + event stream | Native browser/WebSocket support is enough. No need for Socket.IO in a localhost Python app. | HIGH |
| `views/` JSON artifacts | app contract | Heartbeat-generated denormalized UI models | This is the correct contract for CONSTRUCT. It keeps UI fast, isolates raw workspace complexity, and creates a future API boundary. | HIGH |
| `orjson` + typed schemas | see above | Serialization for views and events | Gives fast writes and schema discipline. | HIGH |

**Recommendation:** use WebSockets for **events and chat**, not for the entire application state. The core UI contract should remain **file-backed / snapshot-backed view models**.

## What Not To Use

| Avoid | Why not for CONSTRUCT v0.1 |
|---|---|
| **LangChain / LangGraph / CrewAI as the core runtime** | Too much abstraction for a product whose real complexity is governance, graph maintenance, and local storage. They increase cognitive load and reduce control over local-first behavior. |
| **SQLAlchemy / SQLModel for the index layer** | CONSTRUCT's DB is search/index oriented, not classic CRUD. Raw SQLite + FTS5 is simpler and clearer. |
| **Neo4j / graph database first** | Wrong tradeoff for a single-user local-first product with ≤5k-card target scale. Adds ops and portability pain without delivering needed value. |
| **Postgres + pgvector** | Premature and cloud-shaped. Violates the local-first simplicity target. |
| **Socket.IO** | Native WebSockets already solve the problem. Socket.IO adds protocol and client complexity that CONSTRUCT does not need. |
| **Next.js / Remix / SSR-heavy frontend stack** | The UI is a static artifact served by Python and fed by heartbeat snapshots. Full-stack JS frameworks create a second backend mentality. |
| **Electron/Tauri for v0.1** | Browser + localhost server is enough. Desktop shell packaging is a later distribution concern, not a v0.1 architectural need. |
| **ChromaDB / embedding store in v0.1** | The product docs explicitly defer embedding-based similarity to v0.2. Keep v0.1 deterministic and rebuildable. |

## Recommended Package Seeds

### Python

```bash
pip install \
  "fastapi~=0.136" \
  "uvicorn[standard]~=0.45" \
  "pydantic~=2.13" \
  "pydantic-settings~=2.14" \
  "httpx[http2]~=0.28" \
  "tenacity~=9.1" \
  "networkx~=3.6" \
  "orjson~=3.11" \
  "ruamel.yaml>=0.18,<0.20" \
  "markdown-it-py~=4.0" \
  "typer~=0.24" \
  "watchfiles~=1.1"
```

### Frontend

```bash
npm install react react-dom zustand d3 react-router-dom
npm install -D vite typescript tailwindcss @tailwindcss/vite @types/react @types/react-dom
```

## Final Prescriptive Stack

If roadmap creation needs a single answer, use this:

1. **Backend/runtime:** Python 3.12 + FastAPI + Uvicorn
2. **Schemas/config:** Pydantic v2 + pydantic-settings + orjson
3. **Canonical storage:** Markdown + YAML frontmatter parsed with ruamel.yaml
4. **Graph/index:** NetworkX + stdlib sqlite3 + FTS5 + raw SQL migrations
5. **Agent/provider layer:** HTTPX + Tenacity + thin in-repo provider adapters
6. **CLI:** Typer
7. **Frontend:** React 19 + TypeScript + Vite + Zustand + D3 + Tailwind v4
8. **Realtime/UI contract:** browser WebSocket + heartbeat-generated `views/*.json`

That stack is the best fit for CONSTRUCT because it maximizes **local-first simplicity, typed contracts, rebuildability, and developer control** while staying on the mainstream 2026 path.

## Sources

- CONSTRUCT project docs: `.planning/PROJECT.md`, `CONSTRUCT-spec/construct-prd.md`, `construct-product-brief.md`, `construct-repo-topology.md`, `construct-nfrs.md`
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- Starlette WebSockets: https://starlette.dev/websockets/
- Pydantic docs (v2.13.3 current stable docs): https://docs.pydantic.dev/latest/
- NetworkX docs (3.6.1): https://networkx.org/documentation/stable/
- SQLite FTS5 official docs: https://www.sqlite.org/fts5.html
- HTTPX docs: https://www.python-httpx.org/
- Typer docs: https://typer.tiangolo.com/
- React docs: https://react.dev/learn
- Vite docs (v8.0.9): https://vite.dev/guide/
- Tailwind + Vite docs (v4.2): https://tailwindcss.com/docs/installation/using-vite
- Version checks performed via package registries on 2026-04-22: PyPI (`pip index versions`) and npm (`npm view ... version`)
