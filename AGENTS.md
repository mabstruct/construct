# AGENTS.md

## Project

Development project for CONSTRUCT.

CONSTRUCT is a local-first, agent-powered personal knowledge system. You systematically collect, curate, connect, and compound knowledge across domains — and produce high-quality outputs as derived views of accumulated knowledge.

## Active vs archived — do not confuse

| Track | Status | Paths |
|-------|--------|-------|
| **Claude-native (active)** | Current product | `CONSTRUCT-CLAUDE-impl/`, `CONSTRUCT-CLAUDE-spec/` |
| **Python v0.1 (archived)** | Paused; preserved for future runtime work | `archive/v01-python/spec/`, `archive/v01-python/gsd/`, `src/`, `tests/` |

**Default:** All work uses the Claude-native track unless the user explicitly asks to resume Python runtime exploration.

## Current focus

Testing and validating the Claude-native agent system:

- Agent identity, skills, workflows, templates, and references in `CONSTRUCT-CLAUDE-impl/`
- Specification documents in `CONSTRUCT-CLAUDE-spec/`

## Test workspaces

`test-ws/` contains CONSTRUCT workspaces used to exercise skills, workflows, and views against real workspace state. They are not user data — treat them as fixtures.

- **`test-ws/my-construct/`** — the larger, more complex fixture (multiple domains: cosmology, philosophy-of-mind, philosophy-of-physics, plus generated `views/`). Used regularly as the primary test workspace.
- **`test-ws/ping-eon/`** — smaller fixture (currently one domain: api-gateways). Used for lighter-weight tests.

## Workflow

When working in this repository:

- Read `CONSTRUCT-CLAUDE-spec/README_FIRST.md` for spec navigation.
- Read `CONSTRUCT-CLAUDE-impl/AGENTS.md` for the full agent identity and behavior rules.
- Read root `README.md` for the workspace map and product lineage.
- Use the repository-local `.venv/` for all Python runtime dependencies, CLI commands, developer tools, and tests.
- Run pytest as `.venv/bin/python -m pytest` from the repository root. Do not use bare `pytest` or system `python -m pytest` unless `.venv` is already activated.
- Refresh Python dependencies with `.venv/bin/python -m pip install -e '.[dev]'` if the local environment is missing packages.
- Treat markdown and YAML workspace files as the source of truth.
- Skills are markdown procedures — iterate by editing text.
- Templates in `CONSTRUCT-CLAUDE-impl/construct/templates/` are the single source for workspace file formats.

## Product lineage (short)

```text
v0.1 Python spec (archive/v01-python/) → Claude-native pivot → v0.1 impl → v0.2 views → v0.3 planning
```

## Key principles

- **Claude is the runtime.** No Python backend needed for v0.1/v0.2 Claude-native path.
- **Markdown is canonical.** Cards, connections, configs are files.
- **Everything else is derived.** Views, digests, dashboards are rebuildable.
- **Epistemic governance is non-negotiable.** Every claim has confidence, source tier, type, and lifecycle.

## Guardrails

- Do not introduce cloud-first, multi-user, or auth-heavy architecture into v0.1.
- Do not modify `archive/v01-python/`, `src/`, or `tests/` unless explicitly resuming the Python approach.
- **No active GSD.** `.planning/` was archived to `archive/v01-python/gsd/`. Do not recreate GSD state until CONSTRUCT03 implementation begins — use `CONSTRUCT-CLAUDE-v03-planning/` for planning work now.
- Do not treat `archive/v01-python/spec/` as the living specification — use `CONSTRUCT-CLAUDE-spec/`.
- Keep the knowledge model and workspace format shared between both approaches.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**CONSTRUCT**

CONSTRUCT is a local-first knowledge management system that helps a user collaboratively understand source material from files, notes, and web research. It builds a governed knowledge graph of knowledge nodes and typed connections, then exposes that knowledge through agentic workflows, graph views, and dynamic wiki-style browsing. The current Claude-native implementation is the proof-of-concept foundation; upcoming work hardens that foundation and evolves it toward a clearer product experience.

**Core Value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.

### Constraints

- **Product continuity**: Preserve the existing knowledge model and workspace format across prototype, v0.3, and v0.4 — the system's continuity depends on shared semantics and files.
- **Sequencing**: Do not pull v0.4 UI-primary work ahead of v0.3 runtime and workflow hardening — the UI must sit on proven foundations.
- **Compatibility**: Protect existing Claude-native workflows while hardening and migrating them — users should not lose current capabilities.
- **Implementation posture**: v0.3 should still be usable through the Claude-native skill/workflow model even as it prepares a richer runtime and interface layer.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ — dormant v0.1 runtime (`src/construct/`), active v0.3 pipeline implementation target
- JavaScript (JSX) — views SPA (`views/design-example/src/`)
- Bash — deployment scripts (`setup-construct.sh`, `refresh-construct.sh`)
- YAML — workspace canonical config files (`.construct/governance.yaml`, `.construct/model-routing.yaml`, `domains.yaml`)
- JSON — workspace state files (`connections.json`, `refs/*.json`, `search-seeds.json`)
- Markdown — knowledge cards (`cards/*.md`), digests, publish outputs, all agent skill procedures
## Runtime
- Python 3.14.5 (dev), requires `>=3.11` per `pyproject.toml`
- Node.js v26.0.0 — views SPA build and dev server
- Claude (Anthropic) — **primary runtime** for v0.1/v0.2 Claude-native track; Claude IS the agent runtime
- pip / hatchling 1.25+ — Python build and dependency management
- Lockfile: `pyproject.toml` (no separate lock; `.venv/` present for dev)
- npm 11.12.1 — JavaScript packages for views SPA
- Lockfile: `views/design-example/src/package-lock.json` (present)
## Frameworks
- Typer 0.24+ — CLI framework; entry point `construct` → `src/construct/cli.py`
- Pydantic v2 (2.13+) — data validation for all workspace schemas (cards, config, connections)
- ruamel.yaml 0.18+ — YAML parsing with round-trip support for workspace config files
- hatchling 1.25+ — PEP 517 build backend
- React 19 — UI library
- Vite 8 — build tool and dev server
- Tailwind CSS v4 (via `@tailwindcss/vite`) — utility-first styling
- react-router-dom v7 — client-side routing
- recharts 3.x — chart components
- lucide-react 0.577+ — icon set
- react-markdown 10.x — markdown rendering
- React 19, react-router-dom v7, react-markdown v9, recharts v2
- react-force-graph-2d v1.27 — force-directed graph visualization
- d3 v7 — general-purpose data visualization
- Vite 7+, Tailwind CSS v4 (same stack as design-example, template versions pinned at v7/v9/v2)
- pytest 9.0+ — test runner; config in `pyproject.toml` `[tool.pytest.ini_options]`
- typer.testing.CliRunner — CLI integration test helper
- Claude (Anthropic) — skills in `CONSTRUCT-CLAUDE-impl/claude/skills/`; agents in `CONSTRUCT-CLAUDE-impl/claude/agents/`; no Python runtime for this track
- `.claude/settings.json` — permissions, allowed tools, WebSearch flag
## Key Dependencies
- `pydantic>=2.7` (installed: 2.13.3) — schema validation, strict Pydantic v2 models for all workspace file types
- `ruamel.yaml>=0.18` (installed: 0.19.1) — YAML I/O for workspace config; chosen for comment-preserving round-trip
- `typer>=0.12` (installed: 0.24.1) — CLI; `construct init`, `construct validate`, `construct status`
- `pytest>=8.0` (installed: 9.0.3) — test runner
- `mcp>=1.0` — MCP stdio server (`src/construct/mcp/server.py`)
- `langgraph>=0.2` — LangGraph orchestration for L2 LLM gate (`src/construct/llm/ask_domain.py`)
- `langchain-core>=0.3` — LangChain base abstractions
- `langchain-anthropic>=0.3` — Anthropic provider for LangChain/LangGraph
- `streamlit>=1.35` — localhost ops UI spike (`src/construct/ui/streamlit_app.py`)
- `jsonschema>=4.21` — JSON schema validation for capability contracts
## Configuration
- `.construct/model-routing.yaml` — LLM provider and task-tier routing (frontier/workhorse/lightweight); template at `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml`
- `.construct/governance.yaml` — promotion thresholds, decay windows, quality gates; template at `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml`
- `.claude/settings.json` — Claude tool permissions; template at `CONSTRUCT-CLAUDE-impl/claude/settings.json`
- `ANTHROPIC_API_KEY` — Anthropic API key (frontier + workhorse tiers)
- Any `OPENAI_API_KEY`, `GOOGLE_API_KEY` for alternate providers (schema supports them; not required for default config)
- `pyproject.toml` — Python project config, build system, pytest paths
- `views/design-example/src/vite.config.js` — Vite config for design-example SPA
## Platform Requirements
- Python 3.11+ (3.14 used in dev)
- Node.js >=20 (Node 26 in dev), npm
- Claude Code or Cursor IDE (Claude-native track; skills deployed to workspace `~/.claude/`)
- Local filesystem (workspace directory is the database)
- Claude (Anthropic) as runtime — no server process
- Browser (for views SPA, served locally from `views/build/`)
- Python process running CLI or MCP stdio server
- Anthropic API (default); Ollama optional for lightweight tier
- Streamlit server (localhost spike)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Python Layer
### Naming Patterns
- `snake_case.py` for all Python modules
- One module per concern: `card.py`, `validation.py`, `workspace.py`
- Schemas in `src/construct/schemas/`, services in `src/construct/services/`, storage in `src/construct/storage/`
- `snake_case` for all functions and methods
- Private helper functions prefixed with `_`: `_split_frontmatter`, `_write_domains_registry`, `_to_kebab_case`
- Factory/builder helpers prefixed with `_write_`: `_write_domain_file`, `_write_connections`
- `snake_case` throughout
- Compiled regex patterns are module-level constants in `UPPER_SNAKE_CASE`: `KEBAB_CASE_PATTERN`, `ENV_VAR_PATTERN`, `ROUTING_TASKS`
- Pydantic model names: `PascalCase` — `KnowledgeCard`, `DomainConfig`, `WorkspaceScaffold`
- Enum names: `PascalCase`, enum values: `lowercase` snake/kebab matching the data format — `EpistemicType.finding`, `Lifecycle.seed`
- Exception classes: `PascalCase` with `Error` suffix — `SchemaParseError`, `WorkspaceLoadError`, `WorkspaceInitError`
- Dataclass value objects: `PascalCase` — `ValidationFinding`, `ValidationReport`, `DomainInitInput`, `WorkspaceItem`
### Code Style
- All modules begin with `from __future__ import annotations`
- Required Python ≥ 3.11 (`pyproject.toml`)
- Module docstrings on every source file (one-line summary, e.g., `"""Knowledge card schema and markdown parsing helpers."""`)
- No formatter config detected (no `.prettierrc`, no `ruff.toml`, no `.black`)
- Style follows PEP 8 conventions observed in source: 4-space indent, one blank line between top-level definitions, two blank lines between classes
- No linting config detected in active codebase (archived Python path may have had it)
- Type annotations on all function signatures including `-> None` returns
- Return types declared explicitly: `-> tuple[str, str]`, `-> list[WorkspaceItem]`
### Import Organization
- None (direct package imports via `pythonpath = ["src"]` in pytest; package installed in `.venv`)
### Pydantic Conventions
- Every Pydantic model sets `model_config = ConfigDict(extra="forbid")` — no extra fields allowed
- Use `Field()` for constraints: `Field(ge=1, le=5)`, `Field(min_length=1)`, `Field(default_factory=list)`
- Use `@field_validator("field_name")` + `@classmethod` pattern (Pydantic v2)
- Use `@model_validator(mode="after")` for cross-field validation
- Validators raise `ValueError` with human-readable messages including examples: `"entries must be kebab-case, e.g. 'quantum-gravity' not 'quantum gravity'"`
- Validator return type explicitly declared: `def validate_id(cls, value: str) -> str:`
- All domain enums inherit from `(str, Enum)` so they serialize to strings automatically
- Enum values match the literal strings used in data files (not uppercase Python convention)
### Error Handling
- Define custom `ValueError` subclasses for each domain boundary: `SchemaParseError` (card parsing), `WorkspaceLoadError` (file loading), `WorkspaceInitError` (workspace setup)
- Always chain exceptions with `raise NewError("message") from original_exc`
- Convert third-party exceptions (YAMLError, JSONDecodeError, pydantic.ValidationError) to domain errors at the boundary
- Let `ValidationError` propagate unmodified when already correct type (the `except ValidationError: raise` pattern in `card.py`)
- Catch domain exceptions in CLI commands, emit `typer.echo(f"ERROR {exc}")`, then `raise typer.Exit(code=1)`
- Never let raw exceptions reach the user in CLI context
### Dataclasses
### Data Identifiers
## Claude-Native Agent Layer
### Skill File Conventions
### Agent File Conventions
### Workflow Files
### Markdown Specification Files
- Document title as `# H1`, sections as `## H2`, sub-sections as `### H3`
- Tables for structured enumerations (enum values, responsibility matrices, validation rules)
- All workspace file references in code fences: `` `cards/` ``, `` `connections.json` ``
- ADRs in `adrs/` with format `adr-NNNN-{slug}.md`
- Validation strategy embedded in specs — each SKILL.md ends with a validation checklist
## Views Frontend Layer
### Naming Patterns
- `PascalCase.jsx` for all React components — `Layout.jsx`, `KnowledgeGraph.jsx`
- Pages in `src/pages/`, shared components in `src/components/`
- Data files as JSON in `src/data/` — `articles.json`, `digests.json`
- Default export function with PascalCase name matching filename
- Internal helper components defined in the same file with PascalCase (e.g., `function CosmicBG()`)
- Constant data arrays and objects defined at module level before the component
### Code Style
- Single quotes for imports
- Inline JSX for small helper components, separate function for complex sub-components
- ESLint v9 with `eslint-plugin-react-hooks` and `eslint-plugin-react-refresh` (`package.json`)
- No separate `.eslintrc` — config likely in `eslint.config.js` at project root
### Import Organization (React files)
### Component Design
- Default export arrow function or named function — both observed; prefer named function for pages
- Props destructured inline (when used)
- `useState` + `useMemo` for local filtering/sorting state (pattern in `Blog.jsx`, `Digests.jsx`, `Landscape.jsx`)
- Data loaded from static JSON imports (no API calls in current implementation)
- `react-router-dom` v7 with `<Routes>` / `<Route>` in `App.jsx`
- Route tree defined in `App.jsx`, wrapped in `HashRouter` in `main.jsx`
- All routes nested under `<Layout />`
### Styling
- `bg-black/40 backdrop-blur-2xl` for glass elements
- `border-white/[0.06]` for subtle borders
- `text-white/50` for muted text
- Custom `.glass` utility class defined in `index.css`
## Comments
- Module-level docstrings: one-line description on every module
- No inline comments in existing code — code is self-documenting via naming
- Exception messages serve as inline documentation for validation rules
- Purpose comments in frontmatter `description` field
- Context blocks (Trigger/Agent/Produces) at top of each SKILL.md
- JSDoc-style block comment when a component has a complex non-obvious purpose (seen in `KnowledgeGraph.jsx`)
- No `//` comments for obvious code
## Module Design
- `__init__.py` files are minimal (only `__version__` in root `__init__.py`)
- No barrel files — import from specific modules: `from construct.schemas.card import KnowledgeCard`
- Each module has one primary public concern; private helpers have `_` prefix
- Skills are the unit of reuse — compose workflows from skill invocations
- No code sharing between skills; each SKILL.md is self-contained
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Workspace files (markdown + JSON/YAML) are the only source of truth — no database owns any facts
- Claude is the sole runtime for v0.1/v0.2; Python pipeline layer added in v0.3
- Data flows strictly downward: SOT → derived state → presentation; nothing writes back up
- LLM involvement is explicit and gate-bounded — deterministic work runs in Python by default
- Three invoke surfaces (CLI / MCP / HTTP) all call the same capability registry in v0.3+
## Layers
- Purpose: Authoritative *what* — procedure definitions, capability audit, vocabulary
- Location: `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md`, `CONSTRUCT-CLAUDE-spec/artifact-catalog.md`
- Contains: Skill procedure files, capability audit matrix, epistemic vocabulary, workspace templates
- Depends on: Nothing (read-only reference layer)
- Used by: Layers 1–4; `setup-construct.sh` deploys to `.claude/skills/` in target workspaces
- Purpose: The only source of truth; all knowledge lives here
- Location: `{workspace}/cards/`, `{workspace}/connections.json`, `{workspace}/domains.yaml`, `{workspace}/governance.yaml`, `{workspace}/search-seeds.json`, `{workspace}/refs/`, `{workspace}/log/events.jsonl`
- Contains: Markdown knowledge cards with YAML frontmatter, JSON edge list, YAML domain config, append-only event log
- Depends on: Nothing external; governed by epistemic rules (confidence, source tier, lifecycle, type)
- Used by: Layer 2 (read); skills (write via Claude)
- Purpose: Deterministic work — validation, parsing, file I/O, orchestration; authoritative *how* for PIPE steps
- Location: `src/construct/` — `cli.py`, `schemas/`, `services/`, `storage/`; planned: `pipelines/`, `llm/`, `mcp/`, `api/`
- Contains: Pydantic schemas (`card.py`, `workspace.py`, `config.py`), services (`validation.py`, `init.py`), storage loader (`workspace.py`), CLI entry point
- Depends on: Layer 1 (reads workspace SOT); pydantic, typer, ruamel.yaml
- Used by: Layer 3 (CLI/MCP/HTTP dispatch all invoke this layer)
- Purpose: Pre-computed presentation cache; rebuildable from Layer 1; browser-optimised shapes
- Location: `{workspace}/views/build/data/*.json`, `{workspace}/views/build/version.json`
- Contains: 8 JSON contract files generated by `construct-views-generate-data` skill
- Depends on: Layer 1 (sole input); generated by the `views-generate-data` skill Python helper
- Used by: Layer 3 SPA (read-only HTTP GET)
- Purpose: Expose capability contracts to callers; CLI for development/CI, MCP for agentic clients, HTTP for browser
- Location: `src/construct/cli.py` (current); planned `src/construct/mcp/` and `src/construct/api/`
- Contains: CLI subcommands (`init`, `validate`; more in v0.3); planned MCP tool definitions; planned HTTP routes
- Depends on: Layer 2 pipeline runtime; all surfaces share one capability registry
- Used by: CLI callers, Claude/Cursor MCP clients, browser UI (v0.4); skills in `CONSTRUCT-CLAUDE-impl/` become thin adapters calling these surfaces
- Purpose: Read-only browser dashboard rendering derived state; never writes back to SOT
- Location: `{workspace}/views/build/` (compiled); source scaffold at `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/`
- Contains: React + Vite SPA; pages, components, hooks, lib; polls `version.json` for data freshness
- Depends on: Layer 2b JSON cache (HTTP GET only); no server writes
- Used by: End users; refreshed by re-running `construct-views-generate-data`
- Purpose: UI-as-primary-interface; structured controls invoke Layer 3 capabilities
- Location: TBD — extend `views/` SPA, adopt CoPilotKit, or hybrid (decided post-Streamlit spike in v0.3)
- Contains: Capability buttons, progress/result panels, LLM modal overlays for L1/L2/L3 gates
- Depends on: Layer 3 HTTP API; never writes SOT directly
- Used by: End users; chat demoted to LLM-gated modals only
- Purpose: Model judgment at declared boundaries only — relevance scoring, extraction quality, promotion calls, synthesis
- Implementation: LangGraph subgraphs in `src/construct/llm/` (v0.3); provider config in YAML/env (swap Anthropic/OpenAI/Ollama)
- Three tiers: L1 (user-facing dialogue), L2 (grounded Q&A / RAG), L3 (in-skill decision maker inside pipeline)
- Not LLM by default: validation, schema checks, graph metrics, file I/O, dedup, template scaffold
## Data Flow
- Layer 1 (SOT): filesystem files; edited only via skills; append-only `log/events.jsonl` for audit trail
- Layer 2b (derived): regenerated on demand; safe to delete and rebuild
- Layer 3b (SPA): stateless; reads JSON cache; no local write state persisted server-side
- No in-memory state between Claude sessions — workspace files are the session-independent state store
## Key Abstractions
- Purpose: Atomic epistemic unit — one claim, concept, finding, or gap
- Examples: `{workspace}/cards/{id}.md`
- Pattern: Markdown body + YAML frontmatter; required fields: `id`, `epistemic_type`, `confidence` (1–5), `source_tier` (1–5), `lifecycle` (seed → growing → mature → archived)
- Pydantic schema: `src/construct/schemas/card.py`
- Purpose: Typed edge list linking cards into a knowledge graph
- Examples: `{workspace}/connections.json`
- Pattern: JSON edge list with typed relations (`supports`, `contradicts`, `extends`, `parallels`, `requires`, `enables`, `challenges`, `inspires`, `gap-for`); validated by `src/construct/schemas/workspace.py`
- Purpose: Canonical directory layout definition; drives validation and init
- Examples: `src/construct/schemas/workspace.py` (`WorkspaceScaffold`), `src/construct/services/init.py`
- Pattern: Pydantic model lists `canonical_paths`, `derived_paths`, `support_paths`; `WorkspaceLoader` classifies files against scaffold
- Purpose: Executable procedure for Claude — the unit of capability
- Examples: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md`, `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md`
- Pattern: Markdown file with YAML frontmatter (`description`, `allowed-tools`); procedure steps as numbered sections; in v0.3+ migrated skills call CLI/MCP instead of inline file ops
- Purpose: Multi-skill orchestration sequence for user journeys
- Examples: `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md`, `CONSTRUCT-CLAUDE-impl/construct/workflows/cold-start.md`, `CONSTRUCT-CLAUDE-impl/construct/workflows/co-authorship.md`
- Pattern: Markdown narrative with DAG diagram; maps to a user journey; becomes a Python pipeline in v0.3
- Purpose: Pre-shaped data for the SPA; stable schema between data generator and browser
- Examples: `{workspace}/views/build/data/*.json` (8 files)
- Pattern: Generated by `construct-views-generate-data` Python helper; sole writer principle; any schema change requires updating both generator and SPA components
## Entry Points
- Location: `{workspace}/AGENTS.md` + `{workspace}/.claude/skills/`
- Triggers: User opens Claude in a CONSTRUCT workspace directory
- Responsibilities: Routes user intent → skill procedures → Layer 1 writes; runs `construct-help` on session start
- Location: `src/construct/cli.py` (entry: `app` Typer instance; `pyproject.toml` script: `construct = "construct.cli:main"`)
- Triggers: `construct init <path>`, `construct validate <path>`
- Responsibilities: Interactive workspace init, workspace validation, structured output; v0.3 expands to full capability surface
- Location: `{workspace}/views/build/index.html`
- Triggers: Browser loads via `npx serve views/build` or local HTTP server
- Responsibilities: Renders knowledge graph, cards, stats from JSON cache; polling `version.json` for freshness
- Location: `setup-construct.sh`
- Triggers: Developer runs `./setup-construct.sh <target>` to provision a new CONSTRUCT installation
- Responsibilities: Deploys `CONSTRUCT-CLAUDE-impl/` artifacts to target workspace directory layout
## Error Handling
- Python layer raises typed exceptions: `WorkspaceInitError`, `WorkspaceLoadError`, `SchemaParseError` (all in `src/construct/`)
- `ValidationReport` aggregates findings with severity (`error`/`warning`), path, and message — never raises for warnings
- Pydantic `ValidationError` caught at service boundaries; wrapped into `WorkspaceLoadError` before propagating
- Skills fail with structured error messages that the user can act on (not raw tracebacks)
- Append-only `log/events.jsonl` provides audit trail; errors do not truncate the log
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
