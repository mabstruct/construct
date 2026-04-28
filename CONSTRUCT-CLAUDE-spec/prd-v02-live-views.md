# CONSTRUCT v0.2 — Live Views — Product Requirements Document

**Version:** 0.2.0
**Date:** 2026-04-24 (revised 2026-04-28)
**Status:** Draft — vision and product requirements; implementation details live in the specs below
**Prerequisite:** v0.1 (Claude-native agent system — complete)
**Companion:** [v0.1 PRD (prd.md)](prd.md)

**Implementation specs (binding — supersede this PRD where they conflict):**

- `architecture-overview.md` — three-layer canonical/derived/presentation pattern, the four invariants
- `adrs/adr-0002-v02-packaging.md` — v0.2 packaging (Accepted)
- `spec-v02-runtime-topology.md` — server, routing, `construct-up`/`construct-down`
- `spec-v02-data-model.md` — JSON schemas + envelope
- `spec-v02-scaffold.md` — toolchain, deps, directory layout
- `spec-v02-design-prototype.md` — visual contract, components, navigation taxonomy
- `spec-v02-data-generation.md` — `views-generate-data` skill
- `spec-v02-build-pipeline.md` — `views-scaffold` + `views-build`
- `spec-v02-views.md` — per-view implementation plans
- `spec-v02-hook-integration.md` — v0.1 skill hooks
- `spec-v02-validation.md` — fixtures + acceptance

This PRD captures the product vision and high-level requirements. The specs above hold the binding implementation details; where this document diverges from them, the specs are authoritative.

---

## 1. Summary

v0.1 delivered CONSTRUCT as a Claude-native agent system: skills, workflows, epistemic governance, and a working multi-domain knowledge workspace — all text-based. The primary gap identified in v0.1 review is **visual access to knowledge state**. Users cannot see the graph, browse artifacts, or track curation history without reading raw files or asking Claude for text summaries.

v0.2 closes this gap with **live views**: a set of web pages generated from workspace data, served locally, and updated on demand or by trigger.

---

## 2. Design Principles

| Principle | Implication |
|-----------|-------------|
| **Workspace files remain source of truth** | Views are derived — regenerated from `cards/`, `connections.json`, `domains.yaml`, etc. |
| **Claude generates, browser renders** | View generation is a skill (or set of skills). The output is a built web app. |
| **Vite + React stack** | Matches the existing design prototype in `views/design-example/src/`. Tailwind CSS, lucide-react icons, recharts for charts. |
| **Local-first** | Views are served by `serve --single` from `views/build/`, on a port in 3001–3009 (chosen by `construct-up`). No cloud deployment in v0.2. |
| **Publish is deferred** | Publishing views to a public host (e.g., here.now) is a v0.3 concern. v0.2 is localhost only. |

---

## 3. Architecture

### 3.1 Directory Layout

> **Drilled into:** `spec-v02-scaffold.md` §3 (full layout) and `architecture-overview.md` §3 (three-layer rationale).

```
views/
├── design-example/          # Reference design — read-only, may be removed in a later milestone
├── src/                     # Vite project root; SPA source
│   ├── package.json
│   ├── vite.config.js       # build.outDir = '../build', emptyOutDir = false
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── routes.jsx
│       ├── index.css        # Tailwind directives + theme tokens
│       ├── components/      # Layout, Header, MetricTile, ...
│       ├── pages/           # One per route
│       ├── hooks/           # useFetch, useVersionFlag
│       └── lib/
└── build/                   # Vite output + generated data — served by serve --single
    ├── index.html           # written by views-build (Vite)
    ├── assets/              # written by views-build (Vite, hashed bundles)
    ├── data/                # written by views-generate-data (NEVER touched by Vite)
    │   ├── domains.json     # global
    │   ├── articles.json    # global, cross-workspace
    │   ├── stats.json       # global
    │   └── <workspace>/     # per-workspace files (cards.json, connections.json, etc.)
    ├── version.json         # written by views-generate-data; SPA polls for UPDATE flag
    └── server.pid           # written by construct-up
```

**Key correction from earlier draft:** generated JSON lives at `views/build/data/` (fetched at runtime), not `views/src/data/` (which would be bundled at build time). This decoupling lets `views-generate-data` rewrite data without triggering a Vite rebuild — it's the load-bearing change for the UPDATE-flag polling story. See `architecture-overview.md` §3.2 for the two-writer invariant.

### 3.2 Data Flow

```
Workspace files (cards/, connections.json, domains.yaml, refs/, digests/, publish/, log/)
    │
    │  views-generate-data (Python helper script invoked via SKILL.md)
    ▼
views/build/data/*.json + views/build/version.json    (runtime JSON, fetched by SPA)


views/src/                                           views/build/index.html + assets/
(SPA source)  ── views-build (Vite) ──────►          (compiled bundle)


views/build/  ── construct-up (serve --single) ──►   localhost:<port>
                                                      │
                                                      ▼
                                                    Browser SPA
                                                    fetches /data/*.json + /version.json
                                                    (read-only)
```

Two **independent** writers into `views/build/`:
- `views-build` writes `index.html` + `assets/` (rare — only when SPA source changes)
- `views-generate-data` writes `data/` + `version.json` (frequent — every regen-hook trigger)

These never overlap. `vite.config.js`'s `emptyOutDir: false` is the load-bearing config that prevents Vite from wiping `data/` on rebuild.

### 3.3 Generation Triggers

| Trigger | When | What happens |
|---------|------|-------------|
| **On demand** | User says "update views" / "rebuild views" | Full data regeneration + build |
| **Post-skill hook** | After `research-cycle`, `curation-cycle`, `synthesis` complete | Data regeneration + incremental build |
| **Scheduled** | During `daily-cycle` workflow, after curation step | Full regeneration + build |

### 3.4 Serving

> **Drilled into:** `spec-v02-runtime-topology.md` (server lifecycle, ports, PID, lifecycle).

The built site in `views/build/` is a static SPA. Served via the `serve` npm package with `--single` for SPA history-fallback:

```bash
cd views/src && npm run serve -- -l <port>
# In production: invoked by the construct-up skill which picks a port from 3001–3009
```

`construct-up` is the user-facing entry. It picks a free port, starts the server detached, writes `views/server.pid`, and reports the URL. `construct-down` reads the PID and stops it.

**Why not `python -m http.server`:** it doesn't do SPA history fallback. Reloading at `/<workspace>/digests` would 404. We use BrowserRouter (clean URLs) which requires the server to fall back to `index.html` for unknown paths. `serve --single` does this; Python's stdlib server doesn't.

**Why not `vite preview`:** it's dev tooling, not a stable production-grade server. Used in scaffold sanity-checks only.

No backend API. All data is fetched at runtime as JSON files served as static assets.

---

## 4. Required Views

### 4.1 Dashboard (Home)

**Route:** `/`
**Purpose:** At-a-glance health and activity overview of the entire workspace.

**Content:**
- Aggregate stats: total cards, connections, refs, domains, digests, published articles
- Cards by lifecycle (seed / growing / mature / archived) — bar or donut chart
- Cards by confidence distribution — histogram
- Recent activity timeline (from `log/events.jsonl`) — last N events
- Per-domain summary cards with card counts, avg confidence, connection density
- Quick links to all other views

**Data source:** `cards/`, `connections.json`, `domains.yaml`, `log/events.jsonl`, `digests/`, `publish/`

---

### 4.2 Knowledge Graph

**Route:** `/knowledge-graph`
**Purpose:** Interactive force-directed graph visualization of cards and connections.

**Content:**
- Nodes = cards, colored by epistemic type (finding, claim, concept, gap, etc.)
- Node size = confidence level or connection count
- Edges = typed connections from `connections.json`, labeled by type
- Edge styling: color or dash pattern by connection type (supports, contradicts, extends, etc.)
- Filters: by domain, by epistemic type, by lifecycle, by confidence range
- Click node → side panel with card title, type, confidence, source tier, lifecycle, excerpt
- Click edge → connection note and type
- Legend for all types and colors
- Domain selector (single domain or cross-domain view)

**Data source:** `cards/` (frontmatter), `connections.json`

**Reference:** `views/design-example/src/pages/KnowledgeGraph.jsx` (D3 iframe approach)

---

### 4.3 Domain Landscape

**Route:** `/landscape`
**Purpose:** Visual map of configured domains with health indicators.

**Content:**
- One panel per domain showing:
  - Name, description, status (active / paused / archived)
  - Category taxonomy with card counts per category
  - Coverage heatmap: categories with cards vs. empty categories
  - Key metrics: total cards, avg confidence, connection density, orphan count
  - Cross-domain links (from `domains.yaml` `cross_domain_links`)
- Comparison view: domains side-by-side on key metrics
- Research activity: last digest date, active search clusters per domain

**Data source:** `domains.yaml`, `cards/`, `connections.json`, `search-seeds.json`, `digests/`

---

### 4.4 Artifacts Overview

**Route:** `/artifacts`
**Purpose:** Browse all knowledge cards with sorting, filtering, and detail view.

**Content:**
- Table/list of all cards with columns: title, epistemic type, confidence, source tier, lifecycle, domain, connections count, created date, last reviewed
- Filters: by domain, type, lifecycle, confidence range, source tier
- Sort: by any column
- Click row → detail view with full card content (markdown rendered) and connection list
- Card counts and breakdown stats at top

**Data source:** `cards/` (full content + frontmatter), `connections.json`

---

### 4.5 Digests

**Route:** `/digests`
**Purpose:** Browse research cycle digests — what was found and when.

**Content:**
- List of digests by date, grouped by domain
- Each digest shows: date, domain, summary, candidate count, top-rated items
- Click → full digest detail with all candidates, relevance scores, clusters
- Stats: total digests, total candidates found, top-rated count
- Filter by domain, date range

**Data source:** `digests/**/*.md`

**Reference:** `views/design-example/src/pages/Digests.jsx`

---

### 4.6 Articles (Published Outputs)

**Route:** `/articles`
**Purpose:** Browse published synthesis outputs and drafts.

**Content:**
- List of published articles/drafts from `publish/`
- Each entry: title, date, domains, register/type, excerpt
- Click → full rendered markdown content
- Confidence provenance: which cards contributed, at what confidence
- Filter by domain, type, date

**Data source:** `publish/`, `cards/` (for provenance tracing)

**Reference:** `views/design-example/src/pages/Blog.jsx`

---

### 4.7 Overview & Navigation

**All views share:**
- Glass-morphism dark theme (matching design example)
- Responsive layout (desktop + mobile)
- Sticky header with navigation to all views
- Branding: MABSTRUCT / CONSTRUCT
- Footer with generation timestamp and workspace path

**Reference:** `views/design-example/src/components/Layout.jsx`

---

## 5. Skills Required

### 5.1 `views-generate-data`

> **Drilled into:** `spec-v02-data-generation.md` and `spec-v02-data-model.md`.

**Purpose:** Read workspace files and produce JSON data files into `views/build/data/`. **Sole writer** to that directory (architecture-overview invariant I1).

**Inputs:** Install root path (containing `AGENTS.md`, workspace subdirectories).
**Outputs:** Hybrid global + per-workspace layout:
- `views/build/data/domains.json` — global workspace registry with computed metrics
- `views/build/data/articles.json` — global, cross-workspace published outputs
- `views/build/data/stats.json` — global aggregates
- `views/build/data/<workspace>/cards.json` — per-workspace cards (frontmatter + body)
- `views/build/data/<workspace>/connections.json` — per-workspace UI-shaped graph
- `views/build/data/<workspace>/digests.json` — per-workspace research digests
- `views/build/data/<workspace>/events.json` — per-workspace recent events
- `views/build/data/<workspace>/stats.json` — per-workspace metrics
- `views/build/data/<workspace>/curation-history.json` — per-workspace curation history
- `views/build/version.json` — `{schema_version, build_id, generated_at}` polled by SPA

**Procedure:** Workspace discovery + per-schema parsing + aggregation + deterministic JSON serialisation + `build_id` hashing. Skill is procedural SKILL.md plus a Python helper for the heavy lifting (see `spec-v02-data-generation.md` §3).

### 5.2 `views-build`

> **Drilled into:** `spec-v02-build-pipeline.md`.

**Purpose:** Run `npm install && npm run build` in `views/src/`, producing `views/build/{index.html, assets/}`.

**Procedure:**
1. Verify `views/src/` exists, `vite.config.js` declares `emptyOutDir: false`
2. `npm install` if `node_modules/` missing/stale
3. `npm run build` (Vite writes to `../build/` per outDir config)
4. Verify post-build artefacts; report bundle size

**Critically does NOT:**
- Chain `views-generate-data` (separate writer, separate schedule)
- Touch `views/build/data/` or `views/build/version.json`

### 5.3 `views-serve` and `construct-up`

> **Drilled into:** `spec-v02-runtime-topology.md`.

`views-serve` is the low-level "start an HTTP server on `views/build/`" primitive (`npm run serve -- -l <port>`). The user-facing entry is **`construct-up`**, which wraps it: picks a port (3001–3009), starts the server detached, writes `views/server.pid`, reports the URL.

`construct-down` reads the PID and stops the server.

### 5.4 `views-scaffold`

> **Drilled into:** `spec-v02-scaffold.md` (toolchain) and `spec-v02-build-pipeline.md` §3 (skill behavior).

**Purpose:** One-time setup of `views/src/`. Creates the Vite + React + Tailwind project structure with all components and page stubs.

**Procedure:**
1. Verify install root has `AGENTS.md` + `.construct/`
2. Verify `views/src/` doesn't already exist (or `--force` flag passed)
3. Copy template at `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/` → `views/src/`
4. Substitute `{{VERSION}}` placeholder from `CONSTRUCT-CLAUDE-impl/VERSION`
5. Run `npm install`

`design-example/` is **visual reference only** — not vendored. The template materialises `spec-v02-design-prototype.md`'s component inventory directly.

---

## 6. Workspace Integration

### 6.1 Event Hooks

> **Drilled into:** `spec-v02-hook-integration.md`.

Hooks are **conditionally automatic**: they fire when `views/build/` exists, no-op silently otherwise. No config opt-out for v0.2 MVP.

| Skill | Hook point | Action |
|-------|-----------|--------|
| `research-cycle` | After Step 7 (Report) | `views-generate-data` |
| `curation-cycle` | After Step 7 (Report) | `views-generate-data` |
| `synthesis` | After publish step | `views-generate-data` |
| ~~`card-create`~~ | n/a | **Excluded in v0.2.** Inside parent skills (research-cycle), per-card hooks would fire dozens of times redundantly. Direct invocation is rare; v0.2.1 may add with debouncing |
| ~~`card-connect`~~ | n/a | **Excluded in v0.2.** Same rationale |

**Note: hooks invoke `views-generate-data` only — not `views-build`.** SPA source rarely changes during normal use; rebuild is its own (manual) operation.

**Failure isolation:** A failed `views-generate-data` MUST NOT cause the parent skill to fail. The parent reports success with a `⚠ views regeneration failed: <msg>` warning line.

**Bootstrap hook:** `domain-init` lazily invokes `construct-up` if no server is running (per `spec-v02-runtime-topology.md` §3.2).

### 6.2 Curation History

Views should support historized reports:

- Each curation cycle produces a curation report (already exists: `CURATION-REPORT.md`)
- Data generation should parse all historical curation reports into `data/curation-history.json`
- Dashboard shows curation timeline: when cycles ran, what changed, quality trend over time

---

## 7. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Build tool | Vite 7.x | Pinned at 7 because @vitejs/plugin-react peers Vite 4–7; Vite 8 deferred until plugin-react bumps |
| UI framework | React 19.x | Matches design example |
| Styling | Tailwind CSS 4.x | Matches design example |
| Charts | Recharts | Matches design example |
| Icons | lucide-react | Matches design example |
| Routing | react-router-dom 7.x | Matches design example |
| Markdown rendering | react-markdown | For card content and article display |
| Graph visualization | D3.js (force-directed) | For knowledge graph view; design example uses iframe approach |
| HTTP server | `serve` (npm package) with `--single` | SPA history fallback for `BrowserRouter`; Node already required by Vite. Python `http.server` rejected (no fallback) |
| Knowledge graph | `react-force-graph` (D3 under the hood) | React-friendly wrapper; saves D3 imperative-vs-declarative boilerplate |

---

## 8. What v0.2 Does NOT Include

| Excluded | Deferred to |
|----------|------------|
| Public deployment / hosting | v0.3 (publish to here.now) |
| Real-time live reload (WebSocket) | v0.3+ |
| User authentication | Not planned (local-first) |
| Server-side API | Not planned (static SPA with baked data) |
| Edit capabilities in views | Not planned (Claude is the editor) |
| Search within views | v0.3 (client-side search with FTS) |

---

## 9. Success Criteria

1. `views-scaffold` creates a buildable Vite project from scratch
2. `views-generate-data` reads a real multi-domain workspace and produces valid JSON data files
3. `views-build` produces a deployable static site in `views/build/`
4. All 6 views render correctly with real workspace data
5. Knowledge graph displays nodes and edges from `connections.json` with interactive exploration
6. Domain landscape shows all configured domains with health metrics
7. Dashboard aggregates stats accurately (cross-checked against `graph-status` skill output)
8. Local HTTP server serves the site and all views are navigable
9. Regeneration after a curation cycle correctly updates all data
10. Design matches the glass-morphism dark theme from `views/design-example/`

---

## 10. Development Phases

### Phase 6 — Views Scaffold & Data Pipeline

**Goal:** Project structure, data generation, and build pipeline work.

- Scaffold Vite project in `views/src/` from design-example reference
- Implement `views-generate-data` skill
- Implement `views-build` skill
- Dashboard view (Home) with real data
- Verify: build succeeds, dashboard renders with real workspace data

### Phase 7 — Core Views

**Goal:** All 6 views render with real data.

- Knowledge Graph view (D3 force-directed, interactive)
- Domain Landscape view
- Artifacts Overview view (card browser)
- Digests view
- Articles view
- Shared navigation and layout

### Phase 8 — Integration & Polish

**Goal:** Event hooks, curation history, and design polish.

- Wire post-skill hooks for automatic regeneration
- Curation history timeline on dashboard
- Responsive design pass (mobile)
- `views-serve` skill
- Performance: build time and page load benchmarks
- Verify all success criteria
