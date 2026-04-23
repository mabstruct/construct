# CONSTRUCT v0.2 — Live Views — Product Requirements Document

**Version:** 0.2.0
**Date:** 2026-04-24
**Status:** Draft
**Prerequisite:** v0.1 (Claude-native agent system — complete)
**Companion:** [v0.1 PRD (prd.md)](prd.md)

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
| **Local-first** | Views are served by a local HTTP server (e.g., `python -m http.server` or `npx serve`). No cloud deployment in v0.2. |
| **Publish is deferred** | Publishing views to a public host (e.g., here.now) is a v0.3 concern. v0.2 is localhost only. |

---

## 3. Architecture

### 3.1 Directory Layout

```
views/
├── design-example/          # Reference design (existing prototype — read-only)
│   └── src/
├── src/                     # Generated Vite+React source (written by skills)
│   ├── index.html
│   ├── main.jsx
│   ├── App.jsx
│   ├── components/          # Shared layout, nav, reusable UI components
│   ├── pages/               # One component per view
│   ├── data/                # Generated JSON data files (from workspace)
│   ├── public/              # Static assets (graph HTML, etc.)
│   ├── package.json
│   ├── vite.config.js
│   └── index.css
└── build/                   # Production build output (served by local HTTP server)
```

### 3.2 Data Flow

```
Workspace files (cards/, connections.json, domains.yaml, refs/, digests/, publish/, log/)
    │
    ▼
[data-generation skill] ── reads workspace, produces JSON into views/src/data/
    │
    ▼
[vite build] ── builds views/src/ → views/build/
    │
    ▼
[local HTTP server] ── serves views/build/ on localhost
```

### 3.3 Generation Triggers

| Trigger | When | What happens |
|---------|------|-------------|
| **On demand** | User says "update views" / "rebuild views" | Full data regeneration + build |
| **Post-skill hook** | After `research-cycle`, `curation-cycle`, `synthesis` complete | Data regeneration + incremental build |
| **Scheduled** | During `daily-cycle` workflow, after curation step | Full regeneration + build |

### 3.4 Serving

The built site in `views/build/` is a static SPA. Served by any local HTTP server:

```bash
# Option A: Python
cd views/build && python -m http.server 3000

# Option B: Node
npx serve views/build -p 3000

# Option C: Vite preview
cd views/src && npm run preview
```

No backend API. All data is baked into the build as JSON imports.

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

**Purpose:** Read workspace files and produce JSON data files into `views/src/data/`.

**Inputs:** Workspace path (containing `cards/`, `connections.json`, etc.)
**Outputs:**
- `views/src/data/cards.json` — all cards (frontmatter + content)
- `views/src/data/connections.json` — full connection graph
- `views/src/data/domains.json` — domain taxonomy with computed stats
- `views/src/data/digests.json` — all digests parsed into structured JSON
- `views/src/data/articles.json` — all published outputs
- `views/src/data/events.json` — recent events from log
- `views/src/data/stats.json` — precomputed aggregate statistics

**Procedure:** Read every relevant workspace file, extract/aggregate, write JSON.

### 5.2 `views-build`

**Purpose:** Run `npm install && npm run build` in `views/src/`, producing output in `views/build/`.

**Procedure:**
1. Run `views-generate-data` first (ensure fresh data)
2. Execute Vite build
3. Copy/move build output to `views/build/`
4. Report success with file counts and size

### 5.3 `views-serve`

**Purpose:** Start or restart a local HTTP server on `views/build/`.

**Procedure:**
1. Check if `views/build/` exists and is non-empty
2. Start HTTP server on a configurable port (default 3000)
3. Report URL to user

### 5.4 `views-scaffold`

**Purpose:** Initial one-time setup — create `views/src/` from templates, install dependencies. Uses `views/design-example/` as the reference design.

**Procedure:**
1. Scaffold `views/src/` with Vite + React project structure
2. Adapt design-example Layout, theme, routing to CONSTRUCT domains
3. Create page components for each required view
4. Copy shared components (Layout, theme)
5. Run `npm install`

---

## 6. Workspace Integration

### 6.1 Event Hooks

The following existing skills should trigger view regeneration when `views/` exists:

| Skill | Hook point | Action |
|-------|-----------|--------|
| `research-cycle` | After Step 7 (Report) | `views-generate-data` + `views-build` |
| `curation-cycle` | After Step 7 (Report) | `views-generate-data` + `views-build` |
| `synthesis` | After publish step | `views-generate-data` + `views-build` |
| `card-create` | After card written | `views-generate-data` (build optional) |
| `card-connect` | After connection added | `views-generate-data` (build optional) |

Hooks are optional — views always work as on-demand rebuild too.

### 6.2 Curation History

Views should support historized reports:

- Each curation cycle produces a curation report (already exists: `CURATION-REPORT.md`)
- Data generation should parse all historical curation reports into `data/curation-history.json`
- Dashboard shows curation timeline: when cycles ran, what changed, quality trend over time

---

## 7. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Build tool | Vite 8.x | Matches design example; fast builds |
| UI framework | React 19.x | Matches design example |
| Styling | Tailwind CSS 4.x | Matches design example |
| Charts | Recharts | Matches design example |
| Icons | lucide-react | Matches design example |
| Routing | react-router-dom 7.x | Matches design example |
| Markdown rendering | react-markdown | For card content and article display |
| Graph visualization | D3.js (force-directed) | For knowledge graph view; design example uses iframe approach |
| HTTP server | Python `http.server` or `npx serve` | Zero-install for Python; near-zero for Node |

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
