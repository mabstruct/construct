# Technology Stack

**Project:** CONSTRUCT v0.3 foundation → v0.4 UI-primary
**Researched:** 2026-06-08
**Overall recommendation confidence:** HIGH for v0.3 backend path, MEDIUM for v0.4 UI details

## Recommended Stack

### Core framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12 | Primary runtime for Layer 2 pipelines and Layer 3 adapters | 3.12 is the standard 2025/2026 baseline for modern Python app work: fast enough, widely supported, and a clean upgrade from the repo's current `>=3.11` baseline without forcing a broader rewrite. | HIGH |
| uv | current stable | Project/dependency/tool runner | Standard 2025 Python workflow: fast lock/sync/run, good local developer UX, and ideal for a repo that needs CLI, tests, Streamlit, and MCP tooling without Poetry overhead. Keep `pyproject.toml`; use uv as the package manager. | HIGH |
| Hatchling | current stable | Build backend | Already present, sufficient, and boring. Do not churn packaging while v0.3 is about runtime hardening. | HIGH |

### Pipeline/API foundation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pydantic | 2.x | Canonical schemas for capability I/O, workspace files, and tool contracts | This should be the contract spine of v0.3. It already exists in dormant code, generates JSON Schema cleanly, and matches FastAPI + MCP well. Use strict validation for capability boundaries. | HIGH |
| Typer | 0.21.x | CLI surface for `construct run ...` and admin commands | Best fit for tranche 1 because the repo already has a Typer CLI and the v0.3 ADR explicitly says CLI-first. Easy to map Pydantic-backed inputs to human-usable commands. | HIGH |
| FastAPI | 0.12x | Future HTTP adapter for v0.3 tranche 2 / v0.4 | Standard Python API layer in 2025, pairs naturally with Pydantic v2/OpenAPI, and lets HTTP become just another adapter over the same capability registry. Do not lead with it in tranche 1; add it after CLI+MCP contracts stabilize. | HIGH |
| MCP Python SDK | 1.12.x | MCP stdio server for agent clients | The standard way to expose structured tools to Claude/Cursor-era clients. Use the Python SDK directly so MCP tools stay 1:1 with capability contracts. | HIGH |

### LLM orchestration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LangGraph | 1.x | L2/L3 gates only: grounded Q&A, structured review, human approval pauses | This exactly matches ADR-0003: keep deterministic work in plain Python, use LangGraph only where stateful LLM orchestration and provider swapping matter. | HIGH |
| LangChain model adapters | current stable | Provider abstraction under LangGraph | Use only as the thin model-init layer behind LangGraph. This preserves Anthropic/OpenAI/Ollama swapability without hand-rolling provider clients into pipeline code. | MEDIUM |

### Workspace/storage

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Markdown + YAML frontmatter | existing format | Canonical knowledge cards | This is a hard constraint from PROJECT.md and ADR-0003. Keep it as the SOT. The product continuity story depends on not replacing it. | HIGH |
| JSON / JSONL | existing format | Connections, refs, events, derived data | Matches the current workspace model and is ideal for deterministic pipelines, contract testing, and later UI consumption. | HIGH |
| ruamel.yaml | 0.18.x | YAML read/write for canonical files | Already present and appropriate when preserving formatting and comments matters. Keep it instead of swapping parsers mid-hardening. | MEDIUM |
| SQLite (FTS/index/cache) | defer to tranche 2+ behind an interface | Optional retrieval/index layer, not source of truth | Standard 2025 local-first move once `ask.domain` and search latency justify it. Define an index abstraction now, but do not make SQLite mandatory in tranche 1. | HIGH |

### Supporting libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Contract and regression tests | Required immediately for CLI/MCP schema parity and fixture-based capability tests. |
| anyio | 4.x | Async compatibility across FastAPI/MCP/HTTP tooling | Use for MCP server code and async pipeline edges where needed. |
| httpx | 0.27+/current | HTTP client for future research/index/provider helpers | Use for deterministic external calls; avoid requests in new code. |
| orjson | current stable | Fast JSON serialization | Use inside API/MCP/result paths if profiling shows JSON overhead; optional, not day-1 mandatory. |
| rich | current stable | Better CLI progress and readable local diagnostics | Use for developer/operator UX in CLI and possibly workflow progress output. |
| Streamlit | 1.54.x | v0.3 localhost ops UI spike only | Use for the approved spike: capability runner, result viewer, gate review. Do not confuse this with the v0.4 product UI choice. |

## Implementation choices for this repo

### 1. Make Pydantic the single contract language

Use one Pydantic model set for:

- workspace validation
- capability input/output schemas
- MCP tool input/output schemas
- FastAPI request/response models later
- LangGraph gate structured state at boundaries

This is the most important stack decision. CONSTRUCT's v0.3 problem is contract drift; Pydantic is the fastest path to one source of truth.

### 2. Keep the capability registry as the system center

Implement this shape:

`registry entry -> input model -> output model -> handler -> CLI command -> MCP tool -> future HTTP route`

Do not let CLI, MCP, and HTTP define their own contracts independently.

### 3. Keep deterministic retrieval simple in tranche 1

For `ask.domain`, start with:

- workspace file loading
- derived normalized text chunks from cards/refs/digests
- simple retrieval module invoked by LangGraph

Design an `Indexer` interface now, but postpone mandatory SQLite/FTS until tranche 2. The current milestone is proving the layered runtime, not building the permanent search engine.

### 4. Treat LangGraph as a gate runner, not the runtime

Use it only for:

- grounded Q&A over workspace content
- ambiguous evaluation / review pauses
- structured LLM decisions that return typed objects

Do **not** push validation, file writes, graph metrics, or workflow orchestration into LangGraph nodes unless an LLM is actually required.

### 5. Preserve the dormant Python code selectively

Reuse and extend these patterns already present in `src/construct/`:

- Typer CLI shell
- Pydantic schema layer
- validation services
- file-backed workspace loader

Do **not** revive the whole archived Python-first app plan. Revive only the parts ADR-0003 explicitly keeps.

## v0.4 UI stack recommendation

| Category | Recommended | Why |
|----------|-------------|-----|
| UI framework | React 19 + TypeScript | Standard 2025 choice, already aligned with the repo's v0.2 views direction. |
| Bundler/dev server | Vite 7 | Best fit for localhost-first product UI; fast, simple, no SSR burden. |
| Data fetching/cache | TanStack Query 5 | Strong fit for capability invocation, polling, invalidation, and result caching against the future HTTP API. |
| Graph canvas | React Flow 12 | Standard, mature React graph canvas for interactive node/edge browsing and editing. |
| Styling | Tailwind CSS 4 or lightweight CSS modules | Either is fine, but prefer Tailwind if v0.4 wants fast UI iteration; keep this secondary to the API work. |

**Recommendation:** for v0.4, extend the existing localhost/browser path with a React+Vite SPA over the v0.3 HTTP layer. Do **not** use Next.js unless the product direction changes toward cloud SSR, auth-heavy multi-user delivery, or SEO pages.

## Alternatives considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Python package workflow | uv + Hatchling | Poetry | More workflow overhead for no product benefit here. |
| CLI | Typer | Click-only / argparse | Typer is already present and gives stronger typed ergonomics for a capability CLI. |
| API | FastAPI | Flask / Django / Litestar | FastAPI remains the standard typed Python API choice; the others do not improve this repo's migration path. |
| Agent transport | MCP Python SDK | Custom JSON-RPC or ad-hoc subprocess protocol | Reinvents the ecosystem standard CONSTRUCT explicitly wants to join. |
| LLM orchestration | LangGraph | Hand-rolled provider calls everywhere | Too much bespoke glue, weaker gate testing story, harder provider swapping. |
| v0.3 spike UI | Streamlit | Build React UI immediately | Streamlit is the cheaper de-risking step already locked by ADR-0003. |
| v0.4 UI shell | React+Vite SPA | Next.js | Adds server/runtime complexity before local-first UI needs it. |
| Graph persistence now | File SOT + optional later SQLite index | Neo4j / graph DB | Grossly premature for a single-user local-first knowledge workspace. |
| Retrieval storage now | File-backed retrieval + later SQLite FTS | Vector DB first | Overkill before deterministic contracts and corpus scale justify it. |

## What not to use yet

- **No PostgreSQL / Supabase / cloud-first backend** — wrong product shape for v0.3.
- **No Neo4j** — the graph is small, local, file-backed, and governed; a graph DB adds operational cost without milestone payoff.
- **No vector database as a required dependency** — start with file-backed retrieval and optionally SQLite FTS later.
- **No Celery/Redis-style job stack** — local-first tranche 1 does not need distributed workers.
- **No Next.js app router backend** — avoid duplicating a Python API layer with a JS server layer.
- **No Electron/Tauri in v0.3** — localhost browser + CLI/MCP is enough to harden the foundation.

## Installation

```bash
# Runtime and core contracts
uv add pydantic typer fastapi "mcp>=1.12" langgraph langchain ruamel.yaml anyio httpx rich

# Dev and test
uv add --dev pytest pytest-asyncio

# v0.3 spike UI only
uv add streamlit
```

## Recommended adoption order

1. **Stabilize Python 3.12 + uv + pytest + Pydantic contracts**
2. **Refactor Typer CLI around capability registry**
3. **Expose the same contracts through MCP stdio**
4. **Add LangGraph only for `ask.domain` and later explicit review gates**
5. **Build Streamlit ops spike over CLI/MCP**
6. **Only then add FastAPI HTTP adapter for v0.4 UI**
7. **Only after retrieval pain appears, add optional SQLite FTS/index layer**

## Sources

- CONSTRUCT project docs reviewed: `.planning/PROJECT.md`, `README.md`, `CONSTRUCT-CLAUDE-v03-planning/README.md`, `tranche-1-mvp.md`, `adr-0003-v03-pipeline-v04-ui.md`, `artifact-catalog.md`
- uv docs: https://docs.astral.sh/uv/ (official)
- FastAPI docs via Context7: `/fastapi/fastapi` and official docs references
- Pydantic docs via Context7: `/pydantic/pydantic`
- Typer docs via Context7: `/fastapi/typer`
- MCP Python SDK docs via Context7: `/modelcontextprotocol/python-sdk`
- LangGraph docs via Context7: `/langchain-ai/langgraph`
- Streamlit docs: https://docs.streamlit.io/ (official)
- React Flow docs: https://reactflow.dev/ (official)
- TanStack Query docs: https://tanstack.com/query/latest (official)
