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

### Epic 3: Views Scaffold

Goal: establish the generated React/Vite app structure for v0.2.

Spec target: `../CONSTRUCT-CLAUDE-spec/spec-v02-scaffold.md` (TBD)

Note: `views/design-example/` is **visual reference only**. The scaffold is *not* produced by copying design-example wholesale — it is a clean structure that hosts the design prototype defined in Epic 4.

- [ ] Define canonical `views/` directory layout (consistent with `architecture-overview.md` §7)
- [ ] Lock dependency list: React, Vite, Tailwind, lucide-react, recharts, react-router-dom, react-markdown, D3 (graph), `serve`
- [ ] Create scaffold rules for `views/src/`, `views/build/`, and shared assets
- [ ] Define `package.json` scripts: `build`, `serve` (with `--single`), `dev` (Vite dev server, optional)
- [ ] Define route map and top-level layout shell (consumes Epic 4 component inventory)
- [ ] Define theming entry-points (Tailwind config, design tokens) — implementation in Epic 4

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

### Epic 6: Build Pipeline

Goal: make views buildable from generated data.

Spec target: `../CONSTRUCT-CLAUDE-spec/spec-v02-build-pipeline.md` (TBD)

- [ ] Design `views-scaffold` skill (`SKILL.md`) — one-time `views/src/` setup; consumes Epic 3 + Epic 4 outputs
- [ ] Design `views-build` skill (`SKILL.md`) — `npm install && npm run build` → `views/build/`
- [ ] Define install/build commands and expected outputs
- [ ] Define stale-build detection (rebuild only when SPA *source* changed; never on data-only changes per `architecture-overview.md` §3.2)
- [ ] Define build-time success and error reporting

### Epic 7: Runtime Topology + User-Facing Entry — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md` (Draft). `construct-up` / `construct-down` skills, port range 3001–3009, `version.json` polling for `UPDATE` flag, `/<workspace>/` routing, MVP landing dashboard, local→cloud topology with stable JSON boundary, `serve --single` for SPA history fallback.

- [x] Pick the local serving option → `serve --single` via `npm run serve`
- [x] Design `views-up` (named `construct-up`) — single user-facing command → §3.1
- [x] Define server lifetime → §3.3 (background, survives Claude conversations, no auto-restart)
- [x] Define port collision and restart behavior → §7
- [x] Define stop / shutdown story → §3.4 (`construct-down`)
- [x] Define refresh model → §4 (`UPDATE` flag via `version.json` polling)
- [x] Diagram local + cloud topology → §9
- [x] State explicit non-goals → §10

### Epic 8: Required Views Implementation Plan

Goal: break each required view into concrete implementation work, against the design prototype (Epic 4) and data contracts (Epic 2).

Spec target: per-view sub-specs under `../CONSTRUCT-CLAUDE-spec/spec-v02-view-*.md`, OR one consolidated `spec-v02-views.md` (TBD — decide as part of Epic 4 wrap-up).

#### Landing Dashboard (`/`)

- [ ] Define workspace switcher / status grid contents (consumes `domains.json`, global `stats.json`)
- [ ] Define per-workspace status panel (papers, cards, edges, landscape preview, last activity)
- [ ] Define cross-workspace articles strip (consumes `articles.json`)
- [ ] Define empty-state behavior (no workspaces yet)

#### Per-Workspace Dashboard (`/<workspace>/`)

- [ ] Define workspace-scoped metrics and activity widgets
- [ ] Define charts: lifecycle distribution, confidence histogram, activity timeline
- [ ] Define empty-state behavior

#### Knowledge Graph (`/<workspace>/knowledge-graph`)

- [ ] Choose graph rendering approach (D3 force-directed, recommended)
- [ ] Define node/edge visual encodings (color = epistemic type, size = confidence/connections, edge style by type)
- [ ] Define filtering model and side-panel interactions
- [ ] Define performance budget for large graphs (200+ nodes)

#### Domain Landscape (`/<workspace>/landscape`)

- [ ] Define domain health metrics and visualizations
- [ ] Define taxonomy coverage heatmap
- [ ] Defer: comparison view across workspaces (v0.2.1)

#### Artifacts Overview (`/<workspace>/artifacts`)

- [ ] Define card list columns, sort, and filters
- [ ] Define markdown detail rendering rules (per data-model spec §5.2 — `body_markdown` rendered via react-markdown)
- [ ] Define connection summary presentation in card detail

#### Digests (`/<workspace>/digests` + `/<workspace>/digests/<id>`)

- [ ] Define list/detail UI behavior
- [ ] Define filtering and stats behavior
- [ ] Define raw-source link handling (reference `raw_path` per data-model spec §11.7)

#### Articles (`/articles` + `/articles/<slug>`)

- [ ] Define list view (cross-workspace, sortable, filterable)
- [ ] Define detail view with provenance trace (consumes expanded `source_cards[]`)
- [ ] Define draft vs. published states

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

### Epic 10: Validation and Acceptance

Goal: define how we know v0.2 is done.

Spec target: `../CONSTRUCT-CLAUDE-spec/spec-v02-validation.md` (TBD)

- [ ] Define fixture workspace(s) for view validation (small + medium + edge-case workspaces)
- [ ] Define acceptance checks for each route (consolidate per-view acceptance from Epic 8)
- [ ] Define broken-data resilience checks (reference data-model spec §9 + §10)
- [ ] Define source-of-truth invariant tests (reference data-model spec §12)
- [ ] Define manual rebuild and serve verification flow
- [ ] Define performance expectations for small (≤50 cards) and medium (≤500 cards) workspaces
- [ ] Define portability expectations across Claude surfaces and local machines

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
