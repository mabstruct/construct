# AGENTS.md

## Project

CONSTRUCT is an open-source, local-first, agent-powered personal knowledge system. The knowledge graph is the central product artifact, with markdown and YAML as canonical state and SQLite, NetworkX, and `views/` as rebuildable projections.

Current planning state:
- Project context: `.planning/PROJECT.md`
- Requirements: `.planning/REQUIREMENTS.md`
- Roadmap: `.planning/ROADMAP.md`
- State: `.planning/STATE.md`
- Research context: `.planning/research/`

Current focus:
- Phase 1: Workspace & Canonical Data Foundation

## Workflow

When working in this repository:
- Read `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` before making roadmap-aligned changes.
- Keep the project Python-first, local-first, and markdown-canonical.
- Treat markdown and YAML workspace files as the source of truth.
- Treat SQLite indexes, NetworkX graphs, and `views/` outputs as derived and rebuildable.
- Prefer phased work that preserves rebuildability, auditable agent behavior, and a UI that reads `views/` rather than raw source files.

## Technology Stack

Recommended implementation stack for v0.1:
- Python 3.12+ backend
- FastAPI + Uvicorn server/runtime surface
- Pydantic v2 for schemas and validation
- SQLite + FTS5 for indexing and search
- NetworkX for derived graph operations
- HTTPX for provider and research API access
- React 19 + TypeScript + Vite for the browser UI
- Zustand for UI state
- D3 for graph visualization

## Guardrails

- Do not introduce cloud-first, multi-user, or auth-heavy architecture into v0.1.
- Do not let `db/`, `views/`, or transient runtime state become canonical.
- Do not let the browser UI write directly to source-of-truth workspace files.
- Keep runtime capabilities accessible through stable Python callables so future integrations remain possible.
