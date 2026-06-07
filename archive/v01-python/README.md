# CONSTRUCT v0.1 — Python Runtime (Archived)

**Status:** Archived — preserved for future Python runtime exploration  
**Superseded by:** Claude-native implementation (`CONSTRUCT-CLAUDE-impl/`, `CONSTRUCT-CLAUDE-spec/`)

---

## For agents — read this first

**Do not treat this directory as the active product specification.**

| If you need… | Go here instead |
|--------------|-----------------|
| Current spec, PRD, schemas | [`CONSTRUCT-CLAUDE-spec/`](../../CONSTRUCT-CLAUDE-spec/) |
| Agent config, skills, workflows | [`CONSTRUCT-CLAUDE-impl/`](../../CONSTRUCT-CLAUDE-impl/) |
| Repository agent rules | [`AGENTS.md`](../../AGENTS.md) |
| v0.3 UI-primary planning | [`CONSTRUCT-CLAUDE-v03-planning/`](../../CONSTRUCT-CLAUDE-v03-planning/) |

Open this archive **only** when explicitly exploring Python runtime topics (cloud deployment, MCP server, SQLite indexing, custom UI backend) or tracing historical v0.1 design decisions.

---

## What is here

| Path | Former location | Contents |
|------|-----------------|----------|
| [`spec/`](spec/) | `CONSTRUCT-spec/` | Full v0.1 Python-first spec: PRD, agent specs, data schemas, SQLite schema, test strategy, development strategy |

---

## Related dormant code (repo root)

These remain at the repository root and belong to the same paused Python track:

| Path | Contents |
|------|----------|
| [`src/construct/`](../../src/construct/) | Partial Python implementation (Phase 1 skeleton: init, validate, schemas) |
| [`tests/`](../../tests/) | Python unit and integration tests |
| [`pyproject.toml`](../../pyproject.toml) | Python build configuration |
| [`gsd/`](gsd/) | `.planning/` | Frozen GSD state for Python v0.1 track (Phase 1–3 plans, research) |

Do not modify these unless explicitly resuming the Python approach.

---

## GSD (Get Shit Done)

GSD project state for the Python track is archived in [`gsd/`](gsd/). **No active `.planning/` at repo root.** Restart GSD fresh when CONSTRUCT03 implementation begins — see [`CONSTRUCT-CLAUDE-v03-planning/README.md`](../../CONSTRUCT-CLAUDE-v03-planning/README.md).

---

## Product lineage

```text
v0.1 Python spec (this archive)
    → partial Python build (src/, gsd/)
    → Claude-native runtime pivot (ADR in CONSTRUCT-CLAUDE-spec/adrs/)
    → v0.1 Claude implementation (CONSTRUCT-CLAUDE-impl/)
    → v0.2 extensions (views, cross-domain — CONSTRUCT-CLAUDE-spec/spec-v02-*)
    → v0.3 planning (UI-as-primary — CONSTRUCT-CLAUDE-v03-planning/)
```

The **knowledge model and workspace file format** are shared across all eras. Only the runtime differs.
