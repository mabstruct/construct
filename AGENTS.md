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
