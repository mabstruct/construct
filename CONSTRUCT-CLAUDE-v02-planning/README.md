# CONSTRUCT-CLAUDE-v0.2 — Planning

## Purpose

This directory is the **planning bridge** for CONSTRUCT Claude-native v0.2. It holds the v0.2 backlog and sequencing only — no implementation source.

v0.2 is an evolution of `CONSTRUCT-CLAUDE-impl/`, not a separate product. The main new capability is live, locally served derived views over workspace knowledge state.

Per `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md` (Proposed): v0.2 implementation lands **in-place** in `../CONSTRUCT-CLAUDE-impl/` (new `views-*` skills) and `../views/src/` (browser app). This directory is archived to `spec/archive/v02-backlog.md` once v0.2 ships.

## Inputs

- `../CONSTRUCT-CLAUDE-impl/` — current v0.1 implementation baseline (and v0.2 implementation target)
- `../CONSTRUCT-CLAUDE-spec/` — canonical Claude-native product/spec set
- `../CONSTRUCT-CLAUDE-spec/prd-v02-live-views.md` — v0.2 requirements source
- `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md` — packaging decision

## Scope

This workspace is for:

- translating the v0.2 PRD into implementation-ready backlog items
- identifying changes required in skills, workflows, templates, and docs
- sequencing work so v0.2 can be built incrementally

Per-epic specs (data model, skill contracts, hook design) are written into `../CONSTRUCT-CLAUDE-spec/spec-v02-*.md`, not here.

## Working Rule

When a requirement in this directory conflicts with `prd-v02-live-views.md`, the PRD wins unless we record an explicit decision to revise it.

## Primary File

- `backlog.md` — detailed implementation backlog for v0.2
