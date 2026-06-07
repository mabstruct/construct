# GSD State — Python v0.1 Track (Archived)

**Status:** Archived — frozen 2026-06-07  
**Former location:** `.planning/` (repository root)

This directory preserves the **Get Shit Done (GSD)** project state for the paused Python-first implementation track. It is not active and must not drive current work.

---

## For agents

**Do not read or update these files** unless explicitly resuming the Python runtime track or researching historical decisions.

| If you need… | Go here instead |
|--------------|-----------------|
| Current product spec | [`CONSTRUCT-CLAUDE-spec/`](../../CONSTRUCT-CLAUDE-spec/) |
| CONSTRUCT03 planning | [`CONSTRUCT-CLAUDE-v03-planning/`](../../CONSTRUCT-CLAUDE-v03-planning/) |
| Python v0.1 spec | [`../spec/`](../spec/) |
| Workspace map | [`../../README.md`](../../README.md) |

---

## What was here

| File / dir | Purpose |
|------------|---------|
| `PROJECT.md`, `ROADMAP.md`, `REQUIREMENTS.md` | Python v0.1 GSD project definition |
| `STATE.md` | Last frozen session state (Phase 1 ready, never executed) |
| `phases/` | Phase 1–3 plans for Python build (partial) |
| `research/` | Stack, architecture, pitfalls research for Python approach |
| `config.json` | GSD workflow configuration |

Internal paths may reference `CONSTRUCT-spec/` — that spec now lives at [`../spec/`](../spec/).

---

## Restarting GSD for CONSTRUCT03

When CONSTRUCT03 moves from **planning** to **implementation**, start **fresh GSD state** for the v0.3 track. Do not resume this archive.

Suggested approach:

1. Complete CONSTRUCT03 planning in `CONSTRUCT-CLAUDE-v03-planning/` and `CONSTRUCT-CLAUDE-spec/`
2. Initialize new `.planning/` at repo root (or a dedicated v03 workspace) from CONSTRUCT03 PRD and artifact catalog
3. Leave this directory unchanged as historical record of the Python v0.1 GSD run

See [`CONSTRUCT-CLAUDE-v03-planning/README.md`](../../CONSTRUCT-CLAUDE-v03-planning/README.md) for current v0.3 planning steps.
