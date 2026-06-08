# Codebase Structure

**Analysis Date:** 2026-06-08

## Directory Layout

```
construct/                              # Repo root — CONSTRUCT development project
├── AGENTS.md                           # Repo-level agent rules (active vs archived tracks)
├── README.md                           # Workspace map and product lineage
├── pyproject.toml                      # Python package (hatchling build, pydantic/typer/ruamel.yaml deps)
├── setup-construct.sh                  # Deploy impl artifacts to a target workspace
├── refresh-construct.sh                # Re-deploy impl artifacts to an existing workspace
├── favicon.svg                         # Brand asset
│
├── CONSTRUCT-CLAUDE-impl/              # ACTIVE — Claude-native runtime artifacts (source of truth for deployed workspaces)
│   ├── AGENTS.md                       # Orchestrator identity, routing, governance (deployed to workspace root)
│   ├── CLAUDE.md                       # Claude config pointer (deployed to workspace root)
│   ├── README.md                       # Impl directory guide
│   ├── claude/
│   │   ├── agents/                     # Sub-role definitions (curator.md, researcher.md)
│   │   └── skills/                     # 23 skill procedures — one subdirectory per skill
│   │       ├── construct-card-create/SKILL.md
│   │       ├── construct-card-edit/SKILL.md
│   │       ├── construct-card-connect/SKILL.md
│   │       ├── construct-card-evaluate/SKILL.md
│   │       ├── construct-card-archive/SKILL.md
│   │       ├── construct-curation-cycle/SKILL.md
│   │       ├── construct-research-cycle/SKILL.md
│   │       ├── construct-search-adjust/SKILL.md
│   │       ├── construct-domain-init/SKILL.md
│   │       ├── construct-domain-manage/SKILL.md
│   │       ├── construct-workspace-init/SKILL.md
│   │       ├── construct-workspace-validate/SKILL.md
│   │       ├── construct-graph-status/SKILL.md
│   │       ├── construct-gap-analysis/SKILL.md
│   │       ├── construct-bridge-detect/SKILL.md
│   │       ├── construct-synthesis/SKILL.md
│   │       ├── construct-help/SKILL.md
│   │       ├── construct-up/SKILL.md
│   │       ├── construct-down/SKILL.md
│   │       ├── construct-views-build/SKILL.md
│   │       ├── construct-views-generate-data/SKILL.md  # Python helper + run.sh in lib/
│   │       ├── construct-views-scaffold/               # React/Vite SPA template
│   │       │   └── template/src/{App.jsx,components/,hooks/,lib/,pages/,routes.jsx}
│   │       └── construct-views-reset/SKILL.md
│   └── construct/
│       ├── templates/                  # Canonical workspace file templates (deployed to .construct/templates/)
│       │   ├── card.md                 # Knowledge card markdown + frontmatter template
│       │   ├── config.yaml             # Workspace config template
│       │   ├── connections.json        # Empty connections file template
│       │   ├── digest.md               # Research digest template
│       │   ├── domains.yaml            # Domains registry template
│       │   ├── governance.yaml         # Curator thresholds template
│       │   ├── model-routing.yaml      # LLM provider routing template
│       │   ├── publish.md              # Published output template
│       │   ├── ref.json                # Reference entry template
│       │   └── search-seeds.json       # Search seeds template
│       ├── workflows/                  # Multi-skill orchestration sequences (deployed to .construct/workflows/)
│       │   ├── cold-start.md           # J1: new workspace initialization workflow
│       │   ├── daily-cycle.md          # J2: ongoing research + curation workflow
│       │   └── co-authorship.md        # J3: synthesis and publication workflow
│       └── references/                 # Shared vocabulary deployed to .construct/references/
│           ├── capabilities.md         # User-facing capability handbook
│           ├── commands.md             # Quick-reference: commands → skills
│           ├── confidence-levels.md
│           ├── connection-types.md
│           ├── epistemic-types.md
│           ├── lifecycle-states.md
│           └── source-tiers.md
│
├── CONSTRUCT-CLAUDE-spec/              # ACTIVE — Living specification documents
│   ├── README_FIRST.md                 # Spec navigation guide
│   ├── prd.md                          # v0.1 PRD (Claude-native)
│   ├── prd-v02-live-views.md           # v0.2 PRD (views SPA)
│   ├── prd-v03-pipeline-mvp.md         # v0.3 PRD (pipeline + CLI/MCP)
│   ├── artifact-catalog.md             # Master capability inventory + CONSTRUCT03 audit matrix
│   ├── architecture-overview.md        # Three-layer pattern + invariants
│   ├── data-schemas.md                 # JSON/YAML workspace artifact schemas
│   ├── knowledge-card-schema.md        # Card markdown + frontmatter spec
│   ├── adrs/                           # Architecture Decision Records
│   │   ├── adr-0001-claude-native-approach.md
│   │   ├── adr-0002-v02-packaging.md
│   │   └── adr-0003-v03-pipeline-v04-ui.md   # Four-layer architecture; LangGraph; CLI→MCP→HTTP
│   └── spec-v02-*.md / spec-v03-*.md   # Feature specifications per version
│
├── CONSTRUCT-CLAUDE-v03-planning/      # ACTIVE — v0.3 pipeline planning documents
│   ├── README.md
│   └── tranche-1-mvp.md               # Locked tranche 1 scope (registry, CLI, MCP, LangGraph, Streamlit)
│
├── CONSTRUCT-CLAUDE-v02-planning/      # Planning artifacts from v0.2 cycle (reference)
│
├── src/construct/                      # ACTIVE (partial) — Python pipeline runtime (v0.1 archived CLI + v0.3 target)
│   ├── __init__.py
│   ├── cli.py                          # Typer CLI app — `construct init` and `construct validate`
│   ├── schemas/
│   │   ├── card.py                     # Pydantic: KnowledgeCard, EpistemicType, Lifecycle, SourceType
│   │   ├── workspace.py                # Pydantic: WorkspaceScaffold, ConnectionRecord, ConnectionType
│   │   └── config.py                   # Pydantic: DomainConfig, DomainsRegistry, GovernanceConfig, ModelRoutingConfig
│   ├── services/
│   │   ├── init.py                     # DomainInitInput, initialize_workspace(), WorkspaceInitError
│   │   └── validation.py               # validate_workspace() → ValidationReport with errors + warnings
│   └── storage/
│       └── workspace.py                # WorkspaceLoader — file discovery, path classification, YAML/JSON loading
│
├── tests/                              # Python test suite (pytest)
│   ├── conftest.py                     # Shared fixtures
│   ├── unit/
│   │   ├── test_schema_contracts.py
│   │   ├── test_validation_service.py
│   │   └── test_bootstrap.py
│   ├── integration/
│   │   └── test_init_cli.py
│   └── fixtures/
│       ├── v02/                        # Workspace fixtures for schema/validation tests
│       │   └── adversarial-corrupt/    # Invalid workspace for error-path testing
│       └── empty/                      # Empty workspace fixture
│
├── views/                              # Views reference artifacts (design examples)
│   └── design-example/                 # Read-only visual prototype; not served
│       └── src/
│
├── archive/                            # ARCHIVED — do not modify
│   └── v01-python/
│       ├── spec/                       # Original Python v0.1 spec (superseded by CONSTRUCT-CLAUDE-spec/)
│       │   └── adrs/
│       └── gsd/                        # GSD planning phases from Python v0.1 cycle
│           └── phases/{01,02,03}-*/
│
└── .planning/                          # GSD planning state (for v0.3 implementation when started)
    └── codebase/                       # Codebase map documents (this directory)
```

## Directory Purposes

**`CONSTRUCT-CLAUDE-impl/`:**
- Purpose: The authoritative source for every file deployed into a CONSTRUCT workspace
- Contains: AGENTS.md (orchestrator identity), agent role definitions, 23 skill SKILL.md procedures, workspace templates, workflow sequences, shared vocabulary references
- Key files: `AGENTS.md`, `claude/skills/*/SKILL.md`, `construct/templates/card.md`, `construct/workflows/daily-cycle.md`
- Note: `setup-construct.sh` copies this directory's contents into a target workspace; edits here propagate on next setup/refresh

**`CONSTRUCT-CLAUDE-spec/`:**
- Purpose: Living specification — PRDs, ADRs, data schemas, feature specs
- Contains: Product requirements, architecture decisions, data contract specs, capability audit
- Key files: `artifact-catalog.md` (master capability inventory), `adrs/adr-0003-v03-pipeline-v04-ui.md` (current architecture decision), `architecture-overview.md`

**`src/construct/`:**
- Purpose: Python pipeline runtime; currently partial (v0.1 archived CLI); v0.3 expands to full pipeline layer
- Contains: Typer CLI, Pydantic schemas, workspace services, storage loader
- Key files: `cli.py` (entry point), `schemas/card.py` (card model), `schemas/workspace.py` (connections + scaffold), `services/validation.py`

**`tests/`:**
- Purpose: Pytest suite for Python runtime layer
- Contains: Unit tests for schemas and services, integration tests for CLI, workspace fixtures
- Key files: `conftest.py`, `unit/test_schema_contracts.py`, `integration/test_init_cli.py`

**`CONSTRUCT-CLAUDE-v03-planning/`:**
- Purpose: v0.3 implementation planning (active; replaces `.planning/` until GSD restart for v0.3)
- Key files: `tranche-1-mvp.md` (locked scope for first tranche)

**`archive/v01-python/`:**
- Purpose: Preserved Python v0.1 work; do not modify; referenced for schema alignment only
- Contains: Original Python spec ADRs, GSD phase plans

## Key File Locations

**Entry Points:**
- `src/construct/cli.py`: Python CLI — `construct init <path>` and `construct validate <path>`
- `CONSTRUCT-CLAUDE-impl/AGENTS.md`: Claude orchestrator boot file (deployed to workspace root)
- `setup-construct.sh`: Workspace provisioning script
- `pyproject.toml`: Python package definition; `construct` CLI script binding

**Configuration:**
- `pyproject.toml`: Build system (hatchling), deps (pydantic>=2.7, typer>=0.12, ruamel.yaml>=0.18), pytest config
- `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml`: Curator threshold defaults
- `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml`: LLM provider config template

**Core Logic:**
- `src/construct/schemas/card.py`: Pydantic KnowledgeCard — epistemic governance fields enforced here
- `src/construct/schemas/workspace.py`: WorkspaceScaffold, ConnectionRecord — graph edge validation
- `src/construct/services/validation.py`: `validate_workspace()` — full workspace integrity check
- `src/construct/services/init.py`: `initialize_workspace()` — canonical workspace bootstrap
- `src/construct/storage/workspace.py`: `WorkspaceLoader` — file discovery and schema loading

**Skill Procedures:**
- `CONSTRUCT-CLAUDE-impl/claude/skills/{skill-name}/SKILL.md`: Each skill is a named directory with a single SKILL.md
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/lib/`: Python helper scripts for views data generation (co-located with the skill)

**Testing:**
- `tests/unit/`: Schema contract tests, service tests
- `tests/integration/`: CLI integration tests
- `tests/fixtures/v02/`: Workspace fixtures (valid and adversarial-corrupt variants)

**Specification:**
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md`: Master capability inventory — single source for what every skill does and its v0.3/v0.4 classification
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md`: Current architecture decision; repository mapping for v0.3

## Naming Conventions

**Files:**
- Skill procedures: `SKILL.md` (always uppercase) in a directory named `construct-{verb}-{noun}` using kebab-case
- Workflow files: `{noun}-cycle.md` or `{adjective}-{noun}.md` in kebab-case
- Python modules: `snake_case.py`
- Spec documents: `{type}-{version}-{topic}.md` (e.g., `spec-v02-data-model.md`, `prd-v03-pipeline-mvp.md`)
- ADRs: `adr-{NNNN}-{topic}.md` with four-digit zero-padded number

**Directories:**
- Skill directories: `construct-{verb}-{noun}` (kebab-case, always prefixed `construct-`)
- Version planning directories: `CONSTRUCT-CLAUDE-v{NN}-planning` (uppercase CONSTRUCT-CLAUDE prefix)
- Python packages: `snake_case`
- Workspace artifact directories: lowercase (`cards/`, `refs/`, `digests/`, `publish/`, `log/`)

**Identifiers (workspace):**
- Card IDs: kebab-case, validated by `KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")` in `src/construct/schemas/`
- Domain IDs: same kebab-case pattern
- Connection types: kebab-case enum values (`supports`, `gap-for`, etc.)

## Where to Add New Code

**New Skill Procedure:**
- Create directory: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-{verb}-{noun}/`
- Add: `SKILL.md` with YAML frontmatter (`description`, `allowed-tools`) and numbered procedure steps
- Register in: `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` (add row with audit columns)
- Update: `CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md` and `commands.md`

**New Python Pipeline Module (v0.3):**
- Pipeline steps: `src/construct/pipelines/{capability-name}.py`
- LangGraph gates: `src/construct/llm/{gate-name}.py`
- MCP tools: `src/construct/mcp/{tool-name}.py`
- HTTP routes: `src/construct/api/{route-group}.py`
- Tests: `tests/unit/test_{module}.py` (unit) or `tests/integration/test_{capability}.py` (integration)

**New Pydantic Schema:**
- Workspace file schemas: `src/construct/schemas/workspace.py` or new `src/construct/schemas/{artifact}.py`
- Keep aligned with `CONSTRUCT-CLAUDE-spec/data-schemas.md` (spec is the contract; Python is the enforcement)

**New CLI Subcommand:**
- Add `@app.command()` function in `src/construct/cli.py`
- Mirror as MCP tool in `src/construct/mcp/` (1:1 with CLI per ADR-0003 A.1)

**New Workspace Template:**
- Add template file: `CONSTRUCT-CLAUDE-impl/construct/templates/{artifact}.{ext}`
- Update: `src/construct/services/init.py` if used during workspace init
- Update: `src/construct/schemas/workspace.py` WorkspaceScaffold paths if it becomes a canonical path

**New Workflow:**
- Add: `CONSTRUCT-CLAUDE-impl/construct/workflows/{workflow-name}.md`
- Register in: `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` workflows section

## Special Directories

**`.planning/`:**
- Purpose: GSD planning state (currently dormant per AGENTS.md guardrails; will be initialized when v0.3 implementation begins)
- Generated: No
- Committed: Yes (when populated)

**`.venv/`:**
- Purpose: Python virtual environment for local development
- Generated: Yes (`python -m venv .venv`)
- Committed: No (gitignored)

**`archive/v01-python/`:**
- Purpose: Preserved Python v0.1 spec and GSD phases; do not modify
- Generated: No
- Committed: Yes (preservation)

**`CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/lib/__pycache__/`:**
- Purpose: Python bytecode cache for skill helper scripts
- Generated: Yes
- Committed: No (gitignored)

**`tests/fixtures/`:**
- Purpose: Workspace fixtures for pytest — not user data, treat as test fixtures
- Generated: No (hand-crafted; `adversarial-corrupt/` is intentionally invalid)
- Committed: Yes

---

*Structure analysis: 2026-06-08*
