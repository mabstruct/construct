# CONSTRUCT-CLAUDE v0.2 Backlog

## Objective

Turn the `prd-v02-live-views.md` draft into an implementation-ready backlog for the Claude-native v0.2 release.

## Source Inputs

- `../CONSTRUCT-CLAUDE-spec/prd-v02-live-views.md`
- `../CONSTRUCT-CLAUDE-impl/README.md`
- `../CONSTRUCT-CLAUDE-impl/AGENTS.md`
- existing skills, workflows, references, and templates under `../CONSTRUCT-CLAUDE-impl/`

## Release Frame

- Baseline: `CONSTRUCT-CLAUDE-impl/` v0.1 complete
- Target: derived live views for local browsing and visibility
- Constraint: workspace files remain source of truth; views remain rebuildable

## Open Questions

- ~~Should v0.2 live in-place inside `CONSTRUCT-CLAUDE-impl/` or become a new deployable package assembled from `CONSTRUCT-CLAUDE-v02-planning/`?~~ **Resolved** by `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md` — in-place inside `CONSTRUCT-CLAUDE-impl/`.
- How much of `views/design-example/` is directly reusable versus only a visual reference?
- Are view-generation hooks mandatory after mutating skills, or optional behind a config flag?
- ~~What is the minimum supported local serving workflow: Vite preview, static serve, or both?~~ **Moved** to Epic 6 (Runtime Topology) — to be answered by `../CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md`.
- Should multi-domain aggregation be first-class in v0.2 or follow after single-domain live views are solid?

## Epics

### Epic 1: v0.2 Architecture and Packaging — RESOLVED

**Resolution:** See `../CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md`. v0.2 implements in-place inside `CONSTRUCT-CLAUDE-impl/`; this directory (`CONSTRUCT-CLAUDE-v02-planning/`) is planning-only and archived after ship.

- [x] Decide repository structure for v0.2 implementation artifacts → in-place
- [x] Define whether `CONSTRUCT-CLAUDE-v02-planning/` is planning-only or becomes the new implementation source → planning-only
- [x] Define migration path from `CONSTRUCT-CLAUDE-impl/` to v0.2 runtime layout → no migration; new `views-*` skills added alongside existing skills
- [x] Record versioning and compatibility expectations for existing workspaces → `CONSTRUCT-CLAUDE-impl/VERSION` carries the bare semver; data files carry `schema_version` field

### Epic 2: Views Data Model

Goal: define the exact derived JSON contracts consumed by the browser app.

- [ ] Specify `cards.json` schema
- [ ] Specify `connections.json` schema for UI consumption
- [ ] Specify `domains.json` schema with computed metrics
- [ ] Specify `digests.json` schema
- [ ] Specify `articles.json` schema
- [ ] Specify `events.json` schema
- [ ] Specify `stats.json` aggregate schema
- [ ] Specify `curation-history.json` schema
- [ ] Decide what provenance and confidence metadata must survive into view data

### Epic 3: Views Scaffold

Goal: establish the generated React/Vite app structure for v0.2.

- [ ] Define canonical `views/` directory layout
- [ ] Decide whether `views/design-example/` stays vendored in repo
- [ ] Create scaffold rules for `views/src/`, `views/build/`, and shared assets
- [ ] Define dependency list: React, Vite, Tailwind, lucide-react, recharts, graph library
- [ ] Define route map and top-level layout shell
- [ ] Define theming constraints and responsiveness baseline

### Epic 4: Data Generation Workflow

Goal: add a repeatable workflow that converts workspace state into UI-ready data.

- [ ] Design `views-generate-data` skill
- [ ] Define file discovery rules across cards, refs, digests, publish, and log artifacts
- [ ] Define parsing rules for markdown, frontmatter, JSON, and event logs
- [ ] Define aggregate/stat computation rules
- [ ] Define failure behavior for partial or malformed workspace data
- [ ] Define incremental versus full regeneration behavior

### Epic 5: Build Pipeline

Goal: make views buildable from generated data.

- [ ] Design `views-scaffold` skill (one-time `views/src/` setup from design-example reference)
- [ ] Design `views-build` skill (`npm install && npm run build` → `views/build/`)
- [ ] Define install/build commands and expected outputs
- [ ] Define stale-build detection (rebuild only when data or source changed)
- [ ] Define build-time success and error reporting

### Epic 6: Runtime Topology + User-Facing Entry

Goal: define how the user starts, browses, and stops CONSTRUCT — local-first now, cloud-ready later.

Spec target: `../CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md`

- [ ] Pick the local serving option (Python `http.server` / `npx serve` / `vite preview`) and record rationale
- [ ] Design `views-serve` (or rename to `views-up`) — single user-facing command that does *generate-data → build-if-stale → start-server → report-URL*
- [ ] Define server lifetime: foreground vs. background, behaviour across Claude conversations
- [ ] Define port collision and restart behavior
- [ ] Define stop / shutdown story
- [ ] Define refresh model: SPA tab reload vs. live-reload (defer live-reload to v0.3)
- [ ] Diagram local topology and cloud-future topology side-by-side, marking the stable JSON-data boundary
- [ ] State explicit non-goals: backend API, dialog-in-browser, auth (deferred to v0.3+)

### Epic 7: Required Views Implementation Plan

Goal: break each required view into concrete implementation work.

#### Dashboard

- [ ] Define dashboard metrics and activity widgets
- [ ] Define per-domain summary card contents
- [ ] Define chart set and empty-state behavior

#### Knowledge Graph

- [ ] Choose graph rendering approach
- [ ] Define node/edge visual encodings
- [ ] Define filtering model and side-panel interactions
- [ ] Define domain-scoped versus cross-domain graph behavior

#### Domain Landscape

- [ ] Define domain health metrics
- [ ] Define taxonomy coverage visualization
- [ ] Define comparison view behavior

#### Artifacts Overview

- [ ] Define card list columns, sort, and filters
- [ ] Define markdown detail rendering rules
- [ ] Define connection summary presentation

#### Digests

- [ ] Define digest parser output fields
- [ ] Define list/detail UI behavior
- [ ] Define filtering and stats behavior

#### Articles

- [ ] Define publish artifact discovery and rendering rules
- [ ] Define provenance trace display
- [ ] Define draft versus published states in UI

### Epic 8: Skill and Workflow Integration

Goal: integrate views into the existing Claude-native operating model.

- [ ] Identify all existing skills that should trigger data regeneration
- [ ] Define optional hook behavior after `research-cycle`
- [ ] Define optional hook behavior after `curation-cycle`
- [ ] Define optional hook behavior after `synthesis`
- [ ] Define optional hook behavior after `card-create`
- [ ] Define optional hook behavior after `card-connect`
- [ ] Define updates required to `daily-cycle.md`
- [ ] Define updates required to command/reference docs

### Epic 9: Validation and Acceptance

Goal: define how we know v0.2 is done.

- [ ] Define fixture workspace(s) for view validation
- [ ] Define acceptance checks for each route
- [ ] Define broken-data resilience checks
- [ ] Define manual rebuild and serve verification flow
- [ ] Define performance expectations for small and medium workspaces
- [ ] Define portability expectations across Claude surfaces and local machines

### Epic 10: Documentation and Migration

Goal: make v0.2 understandable and deployable.

- [ ] Update the main implementation README for views workflows
- [ ] Document v0.2 commands and user phrases
- [ ] Document setup prerequisites for Node/Vite-based local views
- [ ] Document migration and upgrade path from v0.1 workspaces
- [ ] Document what remains deferred to v0.3

## Sequencing Proposal

1. Epic 1: architecture and packaging — **resolved** by ADR-0002
2. Epic 6: runtime topology + user-facing entry — answer first, locks the user experience boundary
3. Epic 2: data model contracts — load-bearing for everything downstream
4. Epic 3: scaffold decisions
5. Epic 4: data generation workflow
6. Epic 5: build pipeline
7. Epic 7: implement views in descending user value order (Dashboard → Artifacts → Digests → Knowledge Graph → Domain Landscape → Articles)
8. Epic 8: hook integration
9. Epic 9 and Epic 10: validation and docs hardening

## Suggested First Planning Pass

- [ ] Convert each epic into a small design note or implementation spec
- [ ] Mark dependencies between epics and tasks
- [ ] Separate must-have v0.2 scope from nice-to-have items
- [ ] Decide the first execution slice for the live-views system
