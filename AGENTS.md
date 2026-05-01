# AGENTS.md

## Project

Development project for CONSTRUCT.

CONSTRUCT is a local-first, agent-powered personal knowledge system. You systematically collect, curate, connect, and compound knowledge across domains — and produce high-quality outputs as derived views of accumulated knowledge.

**Active approach:** Claude-native agent configuration (`CONSTRUCT-CLAUDE-impl/`)
**Active spec:** `CONSTRUCT-CLAUDE-spec/`
**Dormant approach:** Python implementation (`src/`, `tests/`, `CONSTRUCT-spec/`) — on hold, may resume for cloud/MCP path

## Current Focus

Testing and validating the Claude-native agent system:
- Agent identity, skills, workflows, templates, and references in `CONSTRUCT-CLAUDE-impl/`
- Specification documents in `CONSTRUCT-CLAUDE-spec/`

## Test Workspaces

`test-ws/` contains CONSTRUCT workspaces used to exercise skills, workflows, and views against real workspace state. They are not user data — treat them as fixtures.

- **`test-ws/my-construct/`** — the larger, more complex fixture (multiple domains: cosmology, philosophy-of-mind, philosophy-of-physics, plus generated `views/`). Used regularly as the primary test workspace.
- **`test-ws/ping-eon/`** — smaller fixture (currently one domain: api-gateways). Used for lighter-weight tests.

## Workflow

When working in this repository:
- Read `CONSTRUCT-CLAUDE-spec/README_FIRST.md` for spec navigation.
- Read `CONSTRUCT-CLAUDE-impl/AGENTS.md` for the full agent identity and behavior rules.
- Treat markdown and YAML workspace files as the source of truth.
- Skills are markdown procedures — iterate by editing text.
- Templates in `CONSTRUCT-CLAUDE-impl/templates/` are the single source for workspace file formats (shared by both approaches).

## Key Principles

- **Claude is the runtime.** No Python backend needed for v0.1.
- **Markdown is canonical.** Cards, connections, configs are files.
- **Everything else is derived.** SQLite, views, digests are rebuildable.
- **Epistemic governance is non-negotiable.** Every claim has confidence, source tier, type, and lifecycle.

## Guardrails

- Do not introduce cloud-first, multi-user, or auth-heavy architecture into v0.1.
- Do not modify files under `src/`, `tests/`, or `CONSTRUCT-spec/` unless explicitly resuming the Python approach.
- Do not let GSD `.planning/` state drive agent-native work — it tracks the Python approach only.
- Keep the knowledge model and workspace format shared between both approaches.
