# External Integrations

**Analysis Date:** 2026-06-08

## LLM Providers

**Anthropic Claude (primary):**
- Role: The entire agent runtime in the Claude-native track (v0.1/v0.2); frontier and workhorse LLM tiers in model-routing config
- Models configured (template `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml`):
  - `frontier`: `claude-sonnet-4-6` — cross-domain ideation, synthesis, co-authorship, gap analysis, conversation
  - `workhorse`: `claude-haiku-3` — source evaluation, taxonomy tagging, duplicate detection, connection typing
- Auth: `ANTHROPIC_API_KEY` env var (referenced in model-routing.yaml as `api_key_env: ANTHROPIC_API_KEY`)
- SDK: No Python SDK currently installed; v0.3 will use `langchain-anthropic>=0.3`
- Schema: `ProviderName.anthropic` in `src/construct/schemas/config.py`

**OpenAI (schema-supported, not configured by default):**
- Role: Optional alternate provider; schema supports `ProviderName.openai` in `src/construct/schemas/config.py`
- Auth: env var configurable via `api_key_env` field in `ProviderConfig`
- Status: Not used in default workspace config; available as swap-in via model-routing.yaml

**Google (schema-supported, not configured by default):**
- Role: Optional alternate provider; `ProviderName.google` in config schema
- Status: Not used; placeholder in schema for future routing

**Ollama (local LLM):**
- Role: `lightweight` tier — `llama3.2:8b` by default; used for extraction, card formatting, research ingestion
- Auth: None (local process, no API key)
- Schema: `ProviderName.ollama` in `src/construct/schemas/config.py`
- Endpoint: Local Ollama process (no URL configured in schema; assumed localhost)

## Web Search

**Claude WebSearch:**
- Role: Research cycle — Researcher agent uses Claude's built-in WebSearch tool to find papers and sources
- Enabled via: `"WebSearch"` entry in `.claude/settings.json` `permissions.allow` list (template at `CONSTRUCT-CLAUDE-impl/claude/settings.json`)
- No API key required — handled natively by Claude Code / Claude Desktop
- Usage: Invoked by `construct-research-cycle` skill during research cycles; findings become `refs/*.json` and draft cards

## Data Storage

**Databases:**
- None — CONSTRUCT is explicitly database-free by design (ADR-0001)
- All state lives in filesystem files within the workspace directory

**Canonical workspace files (the "database"):**
- `cards/*.md` — knowledge cards (YAML frontmatter + markdown body)
- `connections.json` — edge list (the knowledge graph)
- `domains.yaml` — domain registry
- `governance.yaml` — curation thresholds
- `search-seeds.json` — research search patterns
- `refs/*.json` — source reference entries
- Schemas validated by `src/construct/schemas/` Pydantic models

**Derived/cache files:**
- `views/build/data/*.json` — JSON cache for SPA; rebuilt by `construct-views-generate-data` skill
- `views/build/version.json` — build metadata
- `digests/{domain}/*.md` — research digest outputs (rebuildable)
- `log/events.jsonl` — append-only audit trail of agent operations

**Planned (v0.3):**
- SQLite indexer deferred to tranche 2+ (mentioned as out-of-scope in `prd-v03-pipeline-mvp.md`)

**File Storage:**
- Local filesystem only — workspace directory is user-specified at runtime
- No cloud storage in v0.1/v0.2/v0.3
- Views SPA (`views/build/`) served from local filesystem

**Caching:**
- None explicit — `views/build/data/` acts as a presentation cache but is generated, not a caching system

## Agent / Tool Protocol

**Model Context Protocol (MCP) — planned v0.3 tranche 1:**
- Role: Enable Claude, Cursor, and other MCP clients to invoke CONSTRUCT capabilities as structured tools (1:1 with capability registry)
- Transport: stdio (v0.3 tranche 1); SSE deferred to tranche 2 / cloud deploy
- Server location: `src/construct/mcp/server.py` (planned)
- Tools will mirror CLI commands: `construct_validate`, `construct_graph_status`, `construct_views_generate_data`, `construct_ask_domain`, `construct_run_daily_cycle`
- Dependency: `mcp>=1.0`

**LangGraph (planned v0.3 tranche 1):**
- Role: L2 LLM gate for grounded Q&A (`ask.domain` capability); graph orchestration for the daily cycle workflow skeleton
- Location: `src/construct/llm/ask_domain.py` (planned)
- Provider config: `src/construct/llm/config.yaml` (planned; workspace override optional)
- Dependency: `langgraph>=0.2`, `langchain-core>=0.3`, `langchain-anthropic>=0.3`

## Authentication & Identity

**Auth Provider:**
- None — CONSTRUCT is single-user, local-first; no auth system
- No user accounts, no sessions, no tokens
- The only "auth" is API key management for LLM providers (env vars)

## Browser UI

**Views SPA (`views/design-example/src/`):**
- Served locally from filesystem (`views/build/`) — no server required (can open `index.html` directly or use `vite preview`)
- HTTP GET read-only access to `views/build/data/*.json`
- No POST, no backend calls, no WebSocket — presentation only
- Built with Vite; output is static files

**Streamlit (planned v0.3 spike):**
- Role: Localhost ops console — capability runner, pipeline status, L2 gate review panel
- Location: `src/construct/ui/streamlit_app.py` (planned)
- Dependency: `streamlit>=1.35`
- Scope: localhost only; not a production UI

## Monitoring & Observability

**Error Tracking:**
- None — no external error tracking service

**Logs:**
- `log/events.jsonl` in each workspace — append-only structured event log; written by skills and (planned) pipeline steps
- Console output via `typer.echo()` in CLI

**Structured error format (v0.3 plan):**
- Pipeline steps emit machine-readable codes + human detail; no silent partial success (per `prd-v03-pipeline-mvp.md` design principles)

## CI/CD & Deployment

**Hosting:**
- Local filesystem only (current)
- Cloud-deployable as future goal (mentioned in ADRs; not in v0.3 scope)

**CI Pipeline:**
- None configured — no `.github/workflows/`, no CI service detected
- Tests run manually with `pytest` from workspace root

**Deployment:**
- `setup-construct.sh` — bash script; assembles a CONSTRUCT workspace by copying `CONSTRUCT-CLAUDE-impl/` skills, agents, templates to a target directory
- `refresh-construct.sh` — bash script; additive update of existing workspace from latest impl; uses `rsync`
- Workspace is a directory; "deployment" = running setup script + opening in Claude Code / Cursor

## Environment Configuration

**Required env vars (for LLM-enabled operations):**
- `ANTHROPIC_API_KEY` — required for frontier and workhorse tiers (Anthropic Claude)

**Optional env vars:**
- Any OpenAI or Google API key — only if alternate providers configured in model-routing.yaml
- Ollama requires no env var (local process)

**Secrets location:**
- Env vars only — no secrets in files; `.gitignore` excludes `.env` patterns; `.claude/settings.local.json` excluded from git

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (current v0.1/v0.2)
- v0.2 views hooks: optional event hooks on `research-cycle`, `curation-cycle`, `card-create`, `card-connect` skills — invoke `views-generate-data` to rebuild derived JSON after workspace writes (spec in `CONSTRUCT-CLAUDE-spec/spec-v02-hook-integration.md`)

---

*Integration audit: 2026-06-08*
