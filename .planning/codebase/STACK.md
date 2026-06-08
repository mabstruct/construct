# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.11+ — dormant v0.1 runtime (`src/construct/`), active v0.3 pipeline implementation target
- JavaScript (JSX) — views SPA (`views/design-example/src/`)
- Bash — deployment scripts (`setup-construct.sh`, `refresh-construct.sh`)

**Secondary:**
- YAML — workspace canonical config files (`.construct/governance.yaml`, `.construct/model-routing.yaml`, `domains.yaml`)
- JSON — workspace state files (`connections.json`, `refs/*.json`, `search-seeds.json`)
- Markdown — knowledge cards (`cards/*.md`), digests, publish outputs, all agent skill procedures

## Runtime

**Environment:**
- Python 3.14.5 (dev), requires `>=3.11` per `pyproject.toml`
- Node.js v26.0.0 — views SPA build and dev server
- Claude (Anthropic) — **primary runtime** for v0.1/v0.2 Claude-native track; Claude IS the agent runtime

**Package Managers:**
- pip / hatchling 1.25+ — Python build and dependency management
- Lockfile: `pyproject.toml` (no separate lock; `.venv/` present for dev)
- npm 11.12.1 — JavaScript packages for views SPA
- Lockfile: `views/design-example/src/package-lock.json` (present)

## Frameworks

**Core (Python — dormant v0.1, active in v0.3 plan):**
- Typer 0.24+ — CLI framework; entry point `construct` → `src/construct/cli.py`
- Pydantic v2 (2.13+) — data validation for all workspace schemas (cards, config, connections)
- ruamel.yaml 0.18+ — YAML parsing with round-trip support for workspace config files
- hatchling 1.25+ — PEP 517 build backend

**Views SPA (v0.2 — `views/design-example/src/`):**
- React 19 — UI library
- Vite 8 — build tool and dev server
- Tailwind CSS v4 (via `@tailwindcss/vite`) — utility-first styling
- react-router-dom v7 — client-side routing

**Views SPA charting/visualization:**
- recharts 3.x — chart components
- lucide-react 0.577+ — icon set
- react-markdown 10.x — markdown rendering

**Views SPA (canonical template for user workspaces — `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/package.json`):**
- React 19, react-router-dom v7, react-markdown v9, recharts v2
- react-force-graph-2d v1.27 — force-directed graph visualization
- d3 v7 — general-purpose data visualization
- Vite 7+, Tailwind CSS v4 (same stack as design-example, template versions pinned at v7/v9/v2)

**Testing (Python):**
- pytest 9.0+ — test runner; config in `pyproject.toml` `[tool.pytest.ini_options]`
- typer.testing.CliRunner — CLI integration test helper

**Agent Runtime (Claude-native — v0.1/v0.2 active track):**
- Claude (Anthropic) — skills in `CONSTRUCT-CLAUDE-impl/claude/skills/`; agents in `CONSTRUCT-CLAUDE-impl/claude/agents/`; no Python runtime for this track
- `.claude/settings.json` — permissions, allowed tools, WebSearch flag

## Key Dependencies

**Current (installed in `.venv/`):**
- `pydantic>=2.7` (installed: 2.13.3) — schema validation, strict Pydantic v2 models for all workspace file types
- `ruamel.yaml>=0.18` (installed: 0.19.1) — YAML I/O for workspace config; chosen for comment-preserving round-trip
- `typer>=0.12` (installed: 0.24.1) — CLI; `construct init`, `construct validate`, `construct status`
- `pytest>=8.0` (installed: 9.0.3) — test runner

**Planned additions for v0.3 tranche 1 (per `prd-v03-pipeline-mvp.md`):**
- `mcp>=1.0` — MCP stdio server (`src/construct/mcp/server.py`)
- `langgraph>=0.2` — LangGraph orchestration for L2 LLM gate (`src/construct/llm/ask_domain.py`)
- `langchain-core>=0.3` — LangChain base abstractions
- `langchain-anthropic>=0.3` — Anthropic provider for LangChain/LangGraph
- `streamlit>=1.35` — localhost ops UI spike (`src/construct/ui/streamlit_app.py`)
- `jsonschema>=4.21` — JSON schema validation for capability contracts

## Configuration

**Workspace-level (per deployed workspace, not this repo):**
- `.construct/model-routing.yaml` — LLM provider and task-tier routing (frontier/workhorse/lightweight); template at `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml`
- `.construct/governance.yaml` — promotion thresholds, decay windows, quality gates; template at `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml`
- `.claude/settings.json` — Claude tool permissions; template at `CONSTRUCT-CLAUDE-impl/claude/settings.json`

**Env vars (referenced by model-routing.yaml template):**
- `ANTHROPIC_API_KEY` — Anthropic API key (frontier + workhorse tiers)
- Any `OPENAI_API_KEY`, `GOOGLE_API_KEY` for alternate providers (schema supports them; not required for default config)

**Build:**
- `pyproject.toml` — Python project config, build system, pytest paths
- `views/design-example/src/vite.config.js` — Vite config for design-example SPA

## Platform Requirements

**Development:**
- Python 3.11+ (3.14 used in dev)
- Node.js >=20 (Node 26 in dev), npm
- Claude Code or Cursor IDE (Claude-native track; skills deployed to workspace `~/.claude/`)

**Production (current — Claude-native v0.1/v0.2):**
- Local filesystem (workspace directory is the database)
- Claude (Anthropic) as runtime — no server process
- Browser (for views SPA, served locally from `views/build/`)

**Production (planned v0.3):**
- Python process running CLI or MCP stdio server
- Anthropic API (default); Ollama optional for lightweight tier
- Streamlit server (localhost spike)

---

*Stack analysis: 2026-06-08*
