# CONSTRUCT-CLAUDE v0.2 Backlog

## Objective

Turn the `prd-v02-live-views.md` draft into an implementation-ready backlog for the Claude-native v0.2 release.

## Source Inputs

- `../CONSTRUCT-CLAUDE-spec/prd-v02-live-views.md`
- `../CONSTRUCT-CLAUDE-spec/architecture-overview.md`
- `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md`
- `../CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md`
- `../CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md`
- `../CONSTRUCT-CLAUDE-impl/README.md`
- `../CONSTRUCT-CLAUDE-impl/AGENTS.md`
- existing skills, workflows, references, and templates under `../CONSTRUCT-CLAUDE-impl/`

## Release Frame

- Baseline: `CONSTRUCT-CLAUDE-impl/` v0.1 complete
- Target: derived live views for local browsing and visibility
- Constraint: workspace files remain source of truth; views remain rebuildable
- Approach: **spec-everything-first**. Every epic gets a dedicated `spec-v02-*.md` design note before implementation begins. Walking-skeleton implementation comes after specs are settled.

## Open Questions

- ~~Should v0.2 live in-place inside `CONSTRUCT-CLAUDE-impl/` or become a new deployable package assembled from `CONSTRUCT-CLAUDE-v02-planning/`?~~ **Resolved** by `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md` — in-place inside `CONSTRUCT-CLAUDE-impl/`.
- ~~How much of `views/design-example/` is directly reusable versus only a visual reference?~~ **Resolved** — visual reference only. The example has navigation discrepancies that disqualify wholesale vendoring. A clean design prototype is the goal of Epic 4.
- ~~Are view-generation hooks mandatory after mutating skills, or optional behind a config flag?~~ **Resolved** by `../CONSTRUCT-CLAUDE-spec/spec-v02-hook-integration.md` — conditionally automatic when `views/build/` exists; no opt-out config for v0.2 MVP. Three skills hook regen (research-cycle, curation-cycle, synthesis); card-create and card-connect explicitly excluded. domain-init lazily bootstraps construct-up.
- ~~What is the minimum supported local serving workflow: Vite preview, static serve, or both?~~ **Resolved** by `../CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md` — `serve --single` via `npm run serve`.
- Should multi-domain aggregation be first-class in v0.2 or follow after single-domain live views are solid? — open. Current direction: cross-workspace **articles** are first-class in v0.2; cross-workspace **bridges** and **activity feed** deferred to v0.2.1 (per `spec-v02-runtime-topology.md` §6).

## Epics

### Epic 1: v0.2 Architecture and Packaging — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md` (Accepted). v0.2 implements in-place inside `CONSTRUCT-CLAUDE-impl/`; this directory (`CONSTRUCT-CLAUDE-v02-planning/`) is planning-only and archived after ship.

- [x] Decide repository structure for v0.2 implementation artifacts → in-place
- [x] Define whether `CONSTRUCT-CLAUDE-v02-planning/` is planning-only or becomes the new implementation source → planning-only
- [x] Define migration path from `CONSTRUCT-CLAUDE-impl/` to v0.2 runtime layout → no migration; new `views-*` skills added alongside existing skills
- [x] Record versioning and compatibility expectations for existing workspaces → `CONSTRUCT-CLAUDE-impl/VERSION` carries the bare semver; data files carry `schema_version` field

### Epic 2: Views Data Model — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md` (Draft). Hybrid global + per-workspace JSON layout under `views/build/data/`; 8 schemas with shared envelope (`schema_version`, `generated_at`, `build_id`); expanded article provenance; determinism rules; empty/broken handling; source-of-truth invariants codified in §12.

- [x] Specify `cards.json` schema → `spec-v02-data-model.md` §5.2
- [x] Specify `connections.json` schema for UI consumption → §5.3
- [x] Specify `domains.json` schema with computed metrics → §5.1
- [x] Specify `digests.json` schema → §5.4
- [x] Specify `articles.json` schema → §5.5
- [x] Specify `events.json` schema → §5.6
- [x] Specify `stats.json` aggregate schema → §5.7
- [x] Specify `curation-history.json` schema → §5.8
- [x] Decide what provenance and confidence metadata must survive into view data → §6

### Epic 3: Views Scaffold — RESOLVED + IMPLEMENTED + VERIFIED

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-scaffold.md` — **Accepted** (verified 2026-04-28).

**Implementation:** template tree at `../CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/` (commit `c9cc7dd`).

**Verification:** copied template to a clean test layout, ran `npm install` (416 pkgs, 53s, no errors), `npm run build` (52 modules, 593ms, ~233kb JS), `serve --single` (HTTP 200 on root + history-fallback verified for `/cosmology/digests/2026-04-25`), `emptyOutDir: false` invariant verified (dummy `data/cosmology/cards.json` and `version.json` survived rebuild byte-identical).

**Vite version correction:** spec said Vite 8; install failed because `@vitejs/plugin-react` peers Vite 4–7. Pinned to Vite 7. Spec updated.

- [x] Define canonical `views/` directory layout → spec §3, materialised in `template/`
- [x] Lock dependency list → spec §4 (with Vite 7 correction)
- [x] Create scaffold rules → template tree exists; views-scaffold skill (Epic 6) copies it
- [x] Define `package.json` scripts → `dev`, `build`, `serve`, `preview` per spec §5
- [x] Define route map and top-level layout shell → 10 routes in `routes.jsx` per topology §5
- [x] Define theming entry-points → `index.css` with `@theme` placeholder for Epic 4

### Epic 4: Design Prototype — NEW

Goal: lock the visual language, navigation taxonomy, and reusable component inventory before any view implementation begins. Treat `views/design-example/` as a visual reference only — it has navigation discrepancies that must be resolved here.

Spec target: `../CONSTRUCT-CLAUDE-spec/spec-v02-design-prototype.md` (TBD)

- [ ] Audit `views/design-example/` for navigation discrepancies vs. `spec-v02-runtime-topology.md` §5 routing; record what to keep, drop, or revise
- [ ] Lock navigation taxonomy: header structure, workspace switcher placement, breadcrumbs, route hierarchy display, `UPDATE` flag location
- [ ] Define visual language: theme (glass-morphism dark, per PRD §4.7), color palette, typography scale, spacing system
- [ ] Define component inventory: Layout, Header, WorkspaceSwitcher, StatusCard, MetricTile, ChartWrapper, Table, MarkdownRenderer, Tag, Badge, EmptyState, LoadingState, UpdateFlag — and which are needed in what view (cross-reference Epic 8)
- [ ] Define responsive baseline: desktop primary, tablet acceptable; mobile out-of-scope for v0.2
- [ ] Define accessibility baseline: keyboard nav, focus states, WCAG AA contrast minimum
- [ ] Build a static design prototype (HTML or JSX, no data fetching) demonstrating each route in empty and populated states — serves as the visual contract Epic 8 implements against

### Epic 5: Data Generation Workflow

Goal: add a repeatable workflow that converts workspace state into UI-ready data per `spec-v02-data-model.md`.

Spec target: `../CONSTRUCT-CLAUDE-spec/spec-v02-data-generation.md` (TBD)

- [ ] Design `views-generate-data` skill (`SKILL.md`)
- [ ] Define file discovery rules across cards, refs, digests, publish, and log artifacts
- [ ] Define parsing rules for markdown, frontmatter, JSON, and event logs
- [ ] Define aggregate/stat computation rules (reference `spec-v02-data-model.md` §5.7)
- [ ] Define failure behavior for partial or malformed workspace data (reference data-model spec §9)
- [ ] Define incremental versus full regeneration behavior — and whether the incremental path is in v0.2 or deferred to v0.2.1
- [ ] Define `version.json` write semantics and `build_id` hashing rule (reference topology spec §4 + data-model spec §8)

### Epic 6: Build Pipeline — RESOLVED + IMPLEMENTED + VERIFIED

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-build-pipeline.md` — **Accepted** (verified 2026-04-28).

**Implementation:** `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/SKILL.md` (consumes the template tree from Epic 3) and `CONSTRUCT-CLAUDE-impl/skills/views-build/SKILL.md`.

**Verification (full walking skeleton on staged install):**
- views-scaffold: install root detected, template copied, `{{VERSION}}` substituted to `0.2.0-dev`, `npm install` completed (~30s cached), node_modules/vite verified
- views-build: preconditions checked, `emptyOutDir: false` confirmed via grep, `npm run build` succeeded (52 modules, ~602ms), `views/build/{index.html, assets/}` produced
- INVARIANT verified: created dummy `views/build/data/cosmology/cards.json` and `views/build/version.json`, ran a second `views-build` — both files survived byte-identical
- End-to-end chain (scaffold → build → construct-up → curl → construct-down) all passed; `/version.json` even served correctly to the browser-style fetch

- [x] Design `views-scaffold` skill (`SKILL.md`) → spec §3, implemented + verified
- [x] Design `views-build` skill (`SKILL.md`) → spec §4, implemented + verified
- [x] Define install/build commands and expected outputs → spec §5; bundle ~233kb JS, 5.8kb CSS, 0.4kb HTML
- [x] Define stale-build detection → deferred to v0.2.1 (spec §4.6); always rebuilds for v0.2 MVP
- [x] Define build-time success and error reporting → SKILL.md Failure-mode tables in both skills

### Epic 7: Runtime Topology + User-Facing Entry — RESOLVED + skills IMPLEMENTED + VERIFIED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md` (Draft). `construct-up` / `construct-down` skills, port range 3001–3009, `version.json` polling for `UPDATE` flag, `/<workspace>/` routing, MVP landing dashboard, local→cloud topology with stable JSON boundary, `serve --single` for SPA history fallback.

**Implementation:** `CONSTRUCT-CLAUDE-impl/skills/construct-up/SKILL.md` and `construct-down/SKILL.md` (this commit).

**Verification (skills-side):** End-to-end run on staged scaffold — `construct-up` picked port 3001, started detached `serve` directly via `node_modules/.bin/serve` (single-process model), wrote `views/server.pid`, served HTTP 200 on `/` and on `/cosmology/digests/X` (history fallback). `construct-down` read PID, SIGTERM cleanly killed the process within 1s, removed PID file, post-shutdown connection refused as expected.

**SPA-side checks (UPDATE flag, routing, landing) await Epic 8 implementation.** The runtime-topology spec stays in `Draft` status until those land — flip to `Accepted` after Epic 8 verification.

**Implementation note from testing:** Spec §3.1 originally suggested `nohup npm run serve` for the detached process. Verified that `npm run` adds an `sh -c` wrapper layer, making the recorded PID the npm process rather than the serve process — and SIGTERM doesn't always propagate. Updated to invoke `./node_modules/.bin/serve` directly, which gives a clean single-PID model. Spec updated.

- [x] Pick the local serving option → `serve --single` via `npm run serve`
- [x] Design `views-up` (named `construct-up`) — single user-facing command → §3.1
- [x] Define server lifetime → §3.3 (background, survives Claude conversations, no auto-restart)
- [x] Define port collision and restart behavior → §7
- [x] Define stop / shutdown story → §3.4 (`construct-down`)
- [x] Define refresh model → §4 (`UPDATE` flag via `version.json` polling)
- [x] Diagram local + cloud topology → §9
- [x] State explicit non-goals → §10

### Epic 8: Required Views Implementation Plan — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/spec-v02-views.md` (Draft) — single consolidated spec covering all 9 routes (Landing, Articles list/detail, Workspace dashboard, Knowledge graph, Landscape, Artifacts, Digests list/detail) plus NotFound. Defines per-view fetched data, composition, filters, interactions, empty/loading/error states. Cross-cutting decisions: mixed detail pattern (full page for digests/articles, side panel for cards/graph nodes); top chip toolbar for filters; magazine cards for articles list; URL-backed filter state. Knowledge graph is single-workspace only in v0.2 (cross-workspace deferred to v0.2.1 with bridges).

All sub-tasks resolved by `spec-v02-views.md`:

- [x] Landing — workspace switcher + status grid + articles strip + empty state → §4.1
- [x] Per-Workspace Dashboard — metrics, charts, activity, empty state → §4.4
- [x] Knowledge Graph — react-force-graph, node/edge encodings, type+lifecycle filters, side-panel interactions, 500-node budget → §4.5
- [x] Domain Landscape — health metrics, taxonomy heatmap, cross-workspace comparison deferred to v0.2.1 → §4.6
- [x] Artifacts Overview — columns, sort, chip-toolbar filters, side-panel detail with markdown body → §4.7
- [x] Digests — list/detail behavior, date-range filter, raw-source link handling (not exposed per data-model §11.7) → §4.8 + §4.9
- [x] Articles — magazine card list with chip filters, full-page detail with provenance trace, click-source-card → artifacts side-panel → §4.2 + §4.3

### Epic 9: Skill and Workflow Integration — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/spec-v02-hook-integration.md` (Draft). Hooks are conditionally automatic on `views/build/` existence; no config opt-out for v0.2 MVP. Three skills hook regeneration (research-cycle, curation-cycle, synthesis); card-create and card-connect deliberately excluded to avoid per-card thrash. domain-init prepends a lazy construct-up bootstrap. Failure isolation: hook failures emit a warning to the parent skill's report but never propagate as failure.

- [x] Identify all existing skills that should trigger data regeneration → spec §4 (3 skills, with rationale for excluding 2)
- [x] Define optional vs. mandatory hook behavior → §2, §8 (conditionally automatic; opt-out deferred to v0.2.1)
- [x] Define hook for `research-cycle` → §4.1
- [x] Define hook for `curation-cycle` → §4.2
- [x] Define hook for `synthesis` → §4.3
- [x] ~~Define hook for `card-create`~~ → excluded in v0.2 (§4.4)
- [x] ~~Define hook for `card-connect`~~ → excluded in v0.2 (§4.4)
- [x] Define lazy `construct-up` invocation in `domain-init` → §6
- [x] Define updates required to `daily-cycle.md` → §10
- [x] Define updates required to command/reference docs → §11 (Epic 11 / docs)

### Epic 10: Validation and Acceptance — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/spec-v02-validation.md` (Draft). Four fixtures (empty / single-domain-small / multi-domain-medium / adversarial-corrupt) under `tests/fixtures/v02/`. Cross-spec acceptance matrix consolidates checks from all 9 prior specs into one execution plan. Adversarial fixture validates all four architecture invariants. End-to-end smoke test sequence documented. Performance + portability + browser targets stated.

- [x] Define fixture workspace(s) → §3 (4 fixtures with full directory structures)
- [x] Define acceptance checks for each route → §4.7 (cross-references Epic 8 §6)
- [x] Define broken-data resilience checks → §3.4 (adversarial fixture + expected warnings)
- [x] Define source-of-truth invariant tests → §4.1 (the four invariants from architecture-overview)
- [x] Define manual rebuild and serve verification flow → §5 (end-to-end smoke test)
- [x] Define performance expectations → §6 (small ≤30s pipeline, medium ≤90s, browser targets)
- [x] Define portability expectations → §7 (macOS, Linux, Node 20+, Python 3.10+, browsers)

### Epic 11: Documentation and Migration

Goal: make v0.2 understandable and deployable.

- [ ] Update `CONSTRUCT-CLAUDE-impl/README.md` for views workflows
- [ ] Document v0.2 commands and user phrases
- [ ] Document setup prerequisites for Node-based local views
- [ ] Document migration and upgrade path from v0.1 workspaces
- [ ] Document what remains deferred to v0.2.1 and v0.3
- [ ] Patch `prd-v02-live-views.md` §3.1, §3.2, §3.4, §5 for consistency with the runtime-topology + data-model specs (currently has `src/data/` and lists Python `http.server` as an option)

## Sequencing Proposal

**Spec-first phase (current):**

1. ~~Epic 1 (Packaging)~~ — resolved by ADR-0002
2. ~~Epic 2 (Data Model)~~ — resolved by `spec-v02-data-model.md`
3. ~~Epic 7 (Runtime Topology)~~ — resolved by `spec-v02-runtime-topology.md`
4. **Epic 3 (Scaffold)** — `spec-v02-scaffold.md`
5. **Epic 4 (Design Prototype)** — `spec-v02-design-prototype.md` — load-bearing for Epic 8
6. **Epic 6 (Build Pipeline)** — `spec-v02-build-pipeline.md`
7. **Epic 5 (Data Generation)** — `spec-v02-data-generation.md` — can run in parallel with Epic 6 (depends only on data-model spec)
8. **Epic 8 (Per-View Implementation Plans)** — `spec-v02-views.md` (or per-view sub-specs)
9. **Epic 9 (Hook Integration)** — `spec-v02-hook-integration.md`
10. **Epic 10 (Validation)** — `spec-v02-validation.md`

**Implementation phase (after specs are settled):**

11. Walking skeleton: scaffold + minimal `views-generate-data` (domains + stats only) + `views-build` + `construct-up` + landing dashboard
12. Iterate views in descending user value: Per-Workspace Dashboard → Artifacts Overview → Digests → Articles → Knowledge Graph → Domain Landscape
13. Wire hooks (Epic 9)
14. Validation and docs hardening (Epic 10 + Epic 11)

## Suggested Next Spec

**Epic 3 (Scaffold)** is the next blocker — it locks the toolchain and directory layout that Epic 4 (Design Prototype) needs to live in. After Epic 3, Epic 4 unlocks Epic 8.
