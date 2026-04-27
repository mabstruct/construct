# ADR-0002: v0.2 Packaging and Planning Directory Layout

**Status:** Proposed
**Date:** 2026-04-27
**Deciders:** ;-)mab
**Context:** v0.2 (live views) needs a home. `CONSTRUCT-CLAUDE-v02-planning/` was created as a planning workspace. Before any v0.2 implementation work begins, we need to decide where v0.2 source code lives and what role v02/ plays going forward. This is Epic 1 in `CONSTRUCT-CLAUDE-v02-planning/backlog.md`.

---

## Context

After v0.1 shipped (Claude-native agent runtime — skills, workflows, agents, templates in `CONSTRUCT-CLAUDE-impl/`), the v0.2 PRD (`prd-v02-live-views.md`) added one major capability: **live views** — a locally served web app derived from workspace state.

Materially, v0.2 introduces:

- 4 new skills: `views-scaffold`, `views-generate-data`, `views-build`, `views-serve`
- A Vite + React SPA under `views/src/` (with `views/design-example/` as read-only reference)
- Optional event hooks attached to existing skills (`research-cycle`, `curation-cycle`, `synthesis`, `card-create`, `card-connect`)

The v02/ README already states: *"v0.2 is an evolution of `CONSTRUCT-CLAUDE-impl/`, not a separate product."* The product story reinforces this: the user-facing contract is "agent workspace + browser views = one product." A future cloud topology preserves this contract — what changes is where the agent runs, not how the source is organised.

Constraint: **v0.2 must be non-disruptive against working v0.1 features** (research agent information gathering, artefact creation).

---

## Decision

**Implement v0.2 in-place inside `CONSTRUCT-CLAUDE-impl/`.** New skills land alongside existing skills. The browser app lives in `views/` (already in place). `CONSTRUCT-CLAUDE-v02-planning/` stays a **planning-only bridge** and is archived once v0.2 ships.

Per-epic specs are written into `CONSTRUCT-CLAUDE-spec/`, not into v02/. v02/ holds only the high-level backlog and sequencing.

---

## Options Considered

### Option A: In-place inside `CONSTRUCT-CLAUDE-impl/` (this decision)

v0.2 skills (`views-*`) added under `CONSTRUCT-CLAUDE-impl/skills/`. `views/src/` remains the browser app. v02/ is a temporary planning artefact, archived after ship.

**Pros:**
- Aligns with v02/ README's stated framing ("evolution, not separate product")
- One source-of-truth tree for the agent runtime — no dual-maintenance
- Preserves v0.1 features without copy-and-divergence risk
- Skills remain discoverable to Claude in one location
- `views/` already lives outside impl/ — natural separation between agent runtime and browser artefact stays intact
- Cloud topology change later affects deployment, not source layout

**Cons:**
- No clean rollback boundary at the directory level (handled by git branches/tags instead)
- "v0.1 vs v0.2" distinction lives in version metadata, not folder structure
- v02/ ends up as a transitional artefact that needs explicit archival

### Option B: Assembled package from `CONSTRUCT-CLAUDE-v02-planning/`

v02/ becomes the new implementation root. impl/ deprecates over time. New skills land in `CONSTRUCT-CLAUDE-v02-planning/skills/` and v0.1 skills are migrated across.

**Pros:**
- Clean cutover artefact — "v0.2 = this directory"
- Forces explicit decisions about every v0.1 skill's continued relevance

**Cons:**
- Forks the canonical skills tree — every v0.1 skill must be either copied (drift), symlinked (fragile), or migrated (touches working code)
- Violates "non-disruptive against current features" constraint
- Two roots that Claude could discover, with unclear precedence
- Migration work has no product value — it's pure rearrangement
- Archiving is harder later: can't simply rename, since the v0.2 dir IS the runtime

### Option C: New parallel package (e.g., `CONSTRUCT-CLAUDE-v02-impl/`)

v02 implementation lives in a fresh sibling to impl/. Both run side-by-side until a cutover moment.

**Pros:**
- Hardest possible non-disruption guarantee for v0.1
- Easy rollback (delete the new dir)

**Cons:**
- Worst of both worlds: dual maintenance burden of Option B without the cleanup benefit
- Two parallel skill trees that must stay in sync for shared skills (almost all of them)
- Creates a permanent fork unless explicitly recombined later — and there's no automatic forcing function for the recombination

---

## Consequences

### Positive

- v0.2 work is additive: new skills, new app, new specs — no rearrangement of v0.1
- Single source-of-truth tree per concern: impl/ for runtime, views/ for browser app, spec/ for canonical decisions
- Cloud-deployment future stays open — the boundary is the JSON data contract between agent runtime and browser, which is independent of source layout
- Planning directories collapse from three (`spec/`, `v02/`, legacy `.planning/` and `CONSTRUCT-spec/`) toward one canonical (`spec/`) once cleanup happens

### Negative

- Anyone reading `CONSTRUCT-CLAUDE-impl/` won't see a "this is v0.2" marker without checking version metadata — addressed by a clear `VERSION` field in the README and skill manifest comments
- v02/ existing as a transitional directory needs a dated archival plan, otherwise it becomes a third permanent planning surface

### Neutral

- v0.1 and v0.2 skills coexist in `impl/skills/`. The `views-*` prefix is enough namespacing — they don't intersect with any existing skill name
- `views/design-example/` remains as a read-only design reference. Decision on whether to keep it vendored long-term is deferred (Epic 3)

---

## Planning Directory Layout (consequence of this decision)

| Directory | Role | Lifetime |
|---|---|---|
| `CONSTRUCT-CLAUDE-spec/` | Canonical PRD, ADRs, schemas, agent specs | Permanent — single source of canonical decisions |
| `CONSTRUCT-CLAUDE-spec/adrs/` | Decision records (this file lives here) | Permanent — append-only |
| `CONSTRUCT-CLAUDE-v02-planning/` | Backlog and sequencing for v0.2 only | Temporary — archived to `spec/archive/v02-backlog.md` after v0.2 ships |
| `CONSTRUCT-CLAUDE-impl/` | v0.x runtime source (agents, skills, workflows, templates) | Permanent — current version is the version |
| `views/` | Browser SPA source + design reference | Permanent — runtime artefact |
| `.planning/` (legacy GSD) | Legacy planning surface from earlier project setup | Deprecate — review contents, migrate any live items into `spec/`, then remove |
| `CONSTRUCT-spec/` (Python-first) | Original Python-first plan, superseded by ADR-0001 | Archive — move to `spec/archive/python-first/` or remove |

### Where v0.2 work products go

- **Backlog updates** → `CONSTRUCT-CLAUDE-v02-planning/backlog.md`
- **Per-epic specs** (data model, skill contracts, hook design) → `CONSTRUCT-CLAUDE-spec/spec-v02-*.md`
- **New ADRs** triggered by v0.2 decisions → `CONSTRUCT-CLAUDE-spec/adrs/adr-0003+...`
- **New skills** → `CONSTRUCT-CLAUDE-impl/skills/views-*/SKILL.md`
- **Browser app source** → `views/src/`

### Suggested epic resequencing

The v02/ backlog currently lists Epic 1 (architecture) → Epic 2 (data model) → Epic 3 (scaffold). With this ADR, **Epic 1 collapses to "accept ADR-0002"** and **Epic 2 (data model) becomes the load-bearing first piece of work** — because the JSON contract between agent runtime and browser is the stable boundary that survives any future runtime topology change (desktop, cloud, hybrid).

---

## Open Questions Surfaced by This Decision

1. **Versioning convention** — does `CONSTRUCT-CLAUDE-impl/` carry a `VERSION` file, or is the version implicit in spec/PRD references? (Recommend explicit.)
2. **Legacy directory cleanup timing** — `.planning/` and `CONSTRUCT-spec/` cleanup can happen now or be deferred. (Recommend a separate small cleanup ADR or just commit it as housekeeping.)
3. **`views/` as future package boundary** — if `views/` ever ships as its own npm package or extracts to a separate repo, does it still co-evolve with impl/? (Defer to v0.3 — flag in v02 backlog.)
4. **Hook attachment mechanism** — Section 6.1 of the PRD lists 5 skills that should regenerate views. Does each existing skill get edited to call `views-generate-data`, or is there a generic post-skill hook layer? (Epic 7 question — not blocked by this ADR.)
