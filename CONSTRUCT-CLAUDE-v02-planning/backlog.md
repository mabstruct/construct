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

### Epic 4: Design Prototype — RESOLVED + IMPLEMENTED + VERIFIED

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-design-prototype.md` — **Accepted** (browser-side visual verification passed 2026-05-09).

**Implementation:** 10 components at `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/src/components/` — Layout, CosmicBG, Header (TopRow + conditional BottomRow), Brand, WorkspaceSwitcher (with hardcoded mock workspaces; Epic 8 swaps to useFetch), UpdateFlag (unwired stub; Epic 8 wires useVersionFlag), Footer, EmptyState, LoadingState, ErrorState. Plus updated `index.css` with full theme tokens per spec §3.1 and `App.jsx` wrapping AppRoutes in Layout.

**Mechanical acceptance verified:** all CSS custom properties on `:root`, fonts registered via Tailwind 4 `@theme`, `data-workspace` attribute on Layout wrapper, sticky glass-morphism header, bottom row conditional on `useParams().workspace`, no rotating rings, no "OpenClaw" string, 1539 modules build successfully (build size 241kb JS / 25kb CSS gzipped to ~82kb total).

**Visual verification passed** (2026-05-09): typography, contrast, and responsive layout confirmed in browser.

- [x] Audit `views/design-example/` → spec §13 (Layout/Header lifted in spirit; flat single-workspace nav rejected; Analysis/Architecture/Thought-Stream pages dropped; OpenClaw footer line removed)
- [x] Lock navigation taxonomy → spec §4 implemented in Header.jsx (two-row, sticky, BottomRow conditional)
- [x] Define visual language → index.css with theme tokens, Syne+Manrope fonts via Layout useEffect
- [x] Define component inventory → 10 components shipped; missing: StatusCard, MetricTile, ChartWrapper, Table, MarkdownRenderer, Tag, Badge, ConfidencePill (deferred to Epic 8 — they're page-content components, not layout chrome)
- [x] Define responsive baseline → Tailwind `md:` / `lg:` breakpoints used; desktop primary, tablet acceptable
- [x] Define accessibility baseline → focus rings on all interactives, ARIA labels, prefers-reduced-motion respected
- [x] Build a static design prototype → page stubs remain placeholder; layout chrome (Header, Footer, CosmicBG) renders on every route. Per-page visual prototypes deferred to Epic 8 implementation

### Epic 5: Data Generation Workflow — RESOLVED + IMPLEMENTED + VERIFIED

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-data-generation.md` — **Accepted** (verified 2026-04-29).

**Implementation:** `CONSTRUCT-CLAUDE-impl/skills/views-generate-data/` — `SKILL.md` + `generate.py` main + 9 lib/ modules (frontmatter, discover, envelope, build_id, parse_cards, parse_connections, parse_domains, parse_digests, parse_articles, parse_events, parse_curation, compute_stats) + `requirements.txt` (pyyaml). ~700 lines of Python.

**Verification (test fixture with 1 workspace, 2 valid cards + 1 broken card, 1 connection, 1 digest, 1 article with 2 source cards + 1 missing reference):**
- All 11 expected files written (3 global: domains/articles/stats; 6 per-workspace: cards/connections/digests/events/stats/curation-history; version.json; warnings log)
- Envelope correct on every file (schema_version, build_id, generated_at, data)
- DETERMINISM verified: `build_id e2f2f98c` identical across two runs against unchanged state — only `generated_at` differs
- `source_cards[]` expansion: present cards get full title/type/confidence/contribution objects; absent card gets `{status: "missing"}`
- `connects_to` denormalised correctly (both directions of the supports edge present)
- Stats: avg_confidence, lifecycle histogram, confidence histogram, connection count
- Warnings: broken card flagged with the 4 missing required fields, excluded from cards.json, other cards unaffected
- Safe-delete invariant: `build_id` is a deterministic function of input content, so wiping `views/build/data/` and regenerating produces the same `build_id` (proven by determinism check)

- [x] Design `views-generate-data` skill (`SKILL.md`) → spec §3.4 / implemented
- [x] Define file discovery rules → spec §4 / `lib/discover.py`
- [x] Define parsing rules for markdown, frontmatter, JSON, and event logs → spec §5 / `lib/parse_*.py`
- [x] Define aggregate/stat computation rules → spec §5.8 / `lib/compute_stats.py`
- [x] Define failure behavior for partial or malformed data → spec §7 / per-parser warning emission
- [x] Define incremental vs full regeneration → full only in v0.2 (spec §8); incremental deferred to v0.2.1
- [x] Define `version.json` write semantics and `build_id` hashing → spec §6 / `lib/build_id.py`

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

### Epic 9: Skill and Workflow Integration — RESOLVED + IMPLEMENTED

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-hook-integration.md` (Draft).

**Implementation (2026-05-09):** Step 8 (Views Refresh Hook) added to `research-cycle/SKILL.md`, `curation-cycle/SKILL.md`, `synthesis/SKILL.md`. Views bootstrap check added to `domain-init/SKILL.md` Step 0. `daily-cycle.md` workflow updated with auto-refresh notes.

- [x] Identify all existing skills that should trigger data regeneration → spec §4 (3 skills, with rationale for excluding 2)
- [x] Define optional vs. mandatory hook behavior → §2, §8 (conditionally automatic; opt-out deferred to v0.2.1)
- [x] Define hook for `research-cycle` → §4.1 → **implemented**
- [x] Define hook for `curation-cycle` → §4.2 → **implemented**
- [x] Define hook for `synthesis` → §4.3 → **implemented**
- [x] ~~Define hook for `card-create`~~ → excluded in v0.2 (§4.4)
- [x] ~~Define hook for `card-connect`~~ → excluded in v0.2 (§4.4)
- [x] Define lazy `construct-up` invocation in `domain-init` → §6 → **implemented**
- [x] Define updates required to `daily-cycle.md` → §10 → **implemented**
- [x] Define updates required to command/reference docs → §11 → **implemented** (Epic 11)

### Epic 10: Validation and Acceptance — RESOLVED + EXECUTED

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-validation.md` (Draft).

**Execution (2026-05-09):**
- 4 fixtures created under `tests/fixtures/v02/` (empty, single-domain-small, multi-domain-medium, adversarial-corrupt)
- `views-generate-data` ran successfully on all 4 fixtures (exit 0)
- **I1 PASS:** Only `views-generate-data` writes to `views/build/data/`
- **I2 PASS:** No POST/PUT/DELETE/PATCH in SPA source
- **I3 PASS:** Safe-delete determinism — `build_id` identical after wipe+regen (single-domain-small: `2ffe6f81` both runs)
- Adversarial fixture: 2 valid cards, 0 connections (malformed JSON), orphan article with `{status: "missing"}`, 4 warnings logged
- Empty fixture: all collections produce empty arrays
- Browser-side checks (all routes, empty states, UPDATE flag, deep-URL reload) confirmed by user

- [x] Define fixture workspace(s) → §3 → **created**
- [x] Define acceptance checks for each route → §4.7 → **browser-verified by user**
- [x] Define broken-data resilience checks → §3.4 → **verified on adversarial fixture**
- [x] Define source-of-truth invariant tests → §4.1 → **I1–I3 automated, I4 by spec traceability**
- [x] Define manual rebuild and serve verification flow → §5 → **verified by user on live workspace**
- [x] Define performance expectations → §6 (small ≤30s pipeline, medium ≤90s, browser targets)
- [x] Define portability expectations → §7 (macOS, Linux, Node 20+, Python 3.10+, browsers)

### Epic 11: Documentation and Migration — DONE

Goal: make v0.2 understandable and deployable.

**Implementation (2026-05-09):**
- [x] Update `CONSTRUCT-CLAUDE-impl/README.md` for views workflows → **done** (Local Views section, skill tree, prerequisites, key phrases)
- [x] Document v0.2 commands and user phrases → **done** (commands.md Views & Server table)
- [x] Document setup prerequisites for Node-based local views → **done** (README prerequisites, Views section)
- [x] Document migration and upgrade path from v0.1 workspaces → **N/A** (v0.2 is additive — no migration needed; existing workspaces work unchanged; views are opt-in via `views-scaffold`)
- [x] Document what remains deferred to v0.2.1 and v0.3 → captured in backlog sequencing and per-epic out-of-scope notes
- [x] Patch `prd-v02-live-views.md` §3.3, §3.4, §5.3, §7, §8, §9 for consistency with final specs → **done** (hooks don't run build, direct serve invocation, no views-serve skill, react-force-graph-2d, search in wiki, route count)

### Epic 12: Knowledge Views — Restyle + Wiki

**Spec:** `../CONSTRUCT-CLAUDE-spec/spec-v02-knowledge-views-spike.md` — Spike A locked 2026-04-30 → shipped 2026-05-02. Spike B locked 2026-05-02 → 12.1 ready to plan.

Two sibling slices feeding the daily read/explore experience. Spike A (12.2) is the urgent visual + dynamics fix to the existing graph; Spike B (12.1) introduces a new wiki read-mode page. Decision rationale and rejected alternatives (iframe HTML, raw-D3 lift, library swap) are captured in the spec.

#### Slice 12.2 — Knowledge Graph Restyle (Spike A) — DONE 2026-05-02

Goal: turn the current `react-force-graph-2d` view from "unusable at 33 cards × ~50 connections" into a calm, legible exploration surface that matches the `views/design-example` visual grammar.

**Shipped commits:** `ba957cb` (initial implementation, with deviations documented at the time) → `ae2d0d7` (locked-spec values restored after the cross-workspace edge guard fixed the underlying drag-blanks bug).

**Locked decisions** (spec §5):

| ID | Decision | Locked value |
|---|---|---|
| D1 | Scope | Restyle current engine (no library swap, no D3 lift, no iframe) |
| D2 | Edge labels default | Auto-on when ≤ 30 edges; toggle override stays |
| D3 | Node sizing | Degree-based, shrunk: `4 + sqrt(deg) × 1.4` (peak ~12px) |
| D6 | Sequencing | Slice 12.2 (Spike A) before 12.1 (Spike B) |
| D7 | Backlog placement | Epic 12 in v0.2 (this entry) |

**Q-A answers** (spec §2.7): Q-A1 → D2; Q-A2 → D3; Q-A3 → drag-pin persistence deferred (no localStorage yet); Q-A4 → side panel collapse 300ms ease; Q-A5 → legend becomes click-to-toggle, drives the same `?type=` URL state as the chip toolbar.

**Implementation parameters** (locked by spec §2.3 + §2.4 — all shipped at locked values):

- [x] Layout dynamics: charge `-1400`, `d3-force` collision with `r + 4` padding, link distance `140`, link strength `0.4`
- [x] Cooldown: `cooldownTicks={150}`, `onEngineStop` calls `fgRef.current.zoomToFit(600, 40)` once per dataset (re-fit gate resets only on `graphData` change, so pin/release reheats don't re-fit)
- [x] Node radius formula: `4 + Math.sqrt(degree) * 1.4`
- [x] Edge alpha: `0.22` ambient · `0.85` spotlit · `0.07` dimmed
- [x] Label visibility: ambient gate `globalScale > 1.0`; ego-set labels always; 10px font; 2px text-shadow stroke
- [x] Edge-labels default: auto-on when `links.length ≤ 30`, toggle persists
- [x] Palette swap: type colours → design-example 6+4 grouping (theme blue, provocation purple, finding green, gap amber, method cyan, weird pink, +4 extension)
- [x] Surfaces: canvas bg `#0a0e17`, side panel surface `#111827/95` + header `#111827/80`, node stroke `#445566`
- [x] Side panel: 300ms ease open + 300ms ease collapse on close (intercepts X, schedules `onClose` after the animation; mid-exit card switch cancels the pending close)
- [x] Legend: click-to-toggle-type, drives `?type=` URL state shared with chip toolbar
- [x] Cross-workspace edge guard: filter links to nodes present in this workspace's `cards.json` (root cause of canvas-blanks-on-drag; unblocks the locked layout dynamics)

**Out of scope for 12.2** (deferred): drag-pin persistence across navigation (Q-A3), node sizing by confidence×lifecycle, cross-workspace KG, engine swap.

#### Slice 12.1 — Wiki Read-Mode View (Spike B) — DONE 2026-05-09

Goal: new `/:workspace/wiki` route as a long, browsable, anchor-linkable rendering of cards — the read-mode counterpart to the graph; the natural link target for digest/article cross-references. **Verified by user in live cosmology workspace.**

**Locked decisions** (spec §5):

| ID | Decision | Locked value |
|---|---|---|
| D4 | Layout (Q-B1) | **Option A** — long scroll + inline collapsibles. Anchored URLs (`#card-id`) for deep links from digests/articles. |
| D5 | Workspace landing (Q-B2) | **Stay on dashboard.** Wiki is an option, not the default. `/:workspace` continues to land on the status overview. |
| D8 | Synthesis / topic-page layer (Karpathy LLM-Wiki check, spec §3.9) | **Out of scope for 12.1.** Compilation of cards into topic narratives stays with the existing `synthesis` workflow + cross-workspace `articles/`. Wiki view renders the atomic-card layer in reading mode only. |

**Q-B answers** (spec §3.8): Q-B1 → D4; Q-B2 → D5; Q-B3 → naive substring search (revisit at >500 cards); Q-B4 → defer print stylesheet to v0.2.1; Q-B5 → keep both Artifacts and Wiki (different UX, shared data).

**Karpathy LLM-Wiki cross-check** (spec §3.9): aligned on persistent interlinked human-readable knowledge, cross-references + backlinks, citation grounding, markdown surface. mabstruct already extends beyond the markdown-only baseline (claim layer, typed graph, lifecycle, governance). The deliberate gap — Karpathy-style synthesis/topic pages — is owned by the synthesis workflow per D8, not by 12.1.

**Implementation parameters** (per spec §3.3–§3.6):

- [x] Route: `/:workspace/wiki` + URL-backed `useSearchParams` filter state
- [x] Header nav: insert "Wiki" between "Artifacts" and "Knowledge Graph" → Dashboard · Articles · Digests · Wiki · Artifacts · Knowledge Graph · Landscape
- [x] Per-card render order: `<h2 id={card.id}>` anchor → meta row (epistemic-type · lifecycle · confidence · source-tier · last-reviewed) → body markdown → sources block → connections-out (grouped by type, link to target anchor) → connections-in (backlinks from `connects_to` reverse-index) → "Mentioned in" (digest IDs + article IDs that reference the card-id; derived client-side from `digests.json` body + `articles.json` provenance)
- [x] Inline collapsibles per card (Option A); anchor + meta row always visible, expand reveals body + sources + connections + mentioned-in
- [x] Search: substring match on `title` + `body_markdown` + `tags[]` (debounced 200ms; client-side; no Lunr)
- [x] Filters: lifecycle multi-select, confidence range, category multi-select, type multi-select; default sort type → category → title; alternates created-desc / last-reviewed-desc / confidence-desc
- [x] Cross-link wiring: digest top-finding card-id → wiki anchor; article body backticked card-id → wiki anchor; KG `CardSidePanel` "Open in wiki" button; landscape category cell → `/wiki?category=X`; wiki anchor "Locate in graph" button → `/knowledge-graph?card=cardId`
- [x] Workspace landing stays on dashboard (D5); no redirect from `/:workspace`

**Out of scope for 12.1** (deferred): topic-synthesis/compilation pages (D8 — owned by synthesis workflow), Lunr.js full-text (Q-B3 — revisit at >500 cards), print stylesheet (Q-B4 — v0.2.1), Wiki-as-workspace-landing (D5 — revisit if positioning shifts in v0.3+).

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
