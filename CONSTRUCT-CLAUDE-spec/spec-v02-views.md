# spec-v02-views — Per-View Implementation Plan

**Status:** Draft
**Date:** 2026-04-28
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 8
**Related:** `spec-v02-data-model.md` · `spec-v02-design-prototype.md` · `spec-v02-runtime-topology.md` §5 · `spec-v02-scaffold.md` · `architecture-overview.md`

---

## 1. Scope

This spec turns each route in `spec-v02-runtime-topology.md` §5 into a concrete implementation plan. For every page, it defines: data fetched, components composed, filters and interactions, empty/loading/error states, and the detail-view pattern.

**In scope:**
- All 9 page-level routes (Landing, Articles list, Article detail, Workspace dashboard, Knowledge graph, Landscape, Artifacts, Digests list, Digest detail) plus NotFound
- Cross-cutting patterns: filter UX, detail view shape, empty/loading/error
- Two SPA hooks introduced here: `useFetch` and `useVersionFlag`
- The mock-to-real data swap protocol from Epic 4

**Out of scope:**
- JSON shapes → `spec-v02-data-model.md`
- Visual tokens, components, density baselines → `spec-v02-design-prototype.md`
- Toolchain → `spec-v02-scaffold.md`
- The data-generation skill → `spec-v02-data-generation.md`
- Hook integration with v0.1 skills → `spec-v02-hook-integration.md`

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Detail view pattern | **Mixed.** Full page (own URL) for digest details and article details (long-form reading). Side panel for card detail (in Artifacts) and graph node detail (in Knowledge Graph) — rapid scanning |
| Filter UX | **Top chip toolbar** above each list view. Chips support multi-select. Heavy facets (confidence range, source-tier range) open popovers from their chip rather than living inline |
| Knowledge graph scope | **Single workspace only in v0.2.** Cross-workspace deferred to v0.2.1 alongside bridges |
| Knowledge graph filters | **Epistemic type + lifecycle** (chip multi-select). Confidence rides as visual encoding (node size), not a filter |
| Articles list style | **Magazine cards** (not table). Each article as a card with title, excerpt, metadata strip |
| Detail-link pattern | Click a `source_cards[]` entry in an article → `/<source.workspace_id>/artifacts?card=<id>` (opens the artifacts page with that card's side panel pre-opened) |
| Loading state | Skeleton placeholders matching final layout. No spinners |
| Error state | Single component (`<ErrorState/>`) with retry button → re-runs the same fetch |
| Empty state | Friendly text + suggested action (e.g., "no cards yet — run research on cosmology to start") |
| Performance budget | Knowledge graph: 500 nodes. Artifacts table: 1000 rows. Beyond → simple pagination (deferred unless needed in v0.2) |

---

## 3. Cross-Cutting Patterns

### 3.1 Detail view pattern (mixed)

| Route | Detail rendering | Why |
|---|---|---|
| `/articles` → `/articles/:slug` | Full page | Long-form reading; bookmarkable |
| `/<workspace>/digests` → `/<workspace>/digests/:id` | Full page | Long-form structured content; bookmarkable |
| `/<workspace>/artifacts` → side panel via `?card=:id` | Side panel | Browse many cards quickly; URL preserves selection |
| `/<workspace>/knowledge-graph` → side panel | Side panel (no URL state for v0.2) | Click node → see card without losing graph context |

### 3.2 Filter chip toolbar

```
┌───────────────────────────────────────────────────────────────────────┐
│  [Type ▾]  [Lifecycle ▾]  [Confidence ▾]  [Source tier ▾]   Clear all │
└───────────────────────────────────────────────────────────────────────┘
```

- Each filter is a chip. Closed: shows the facet name. Open (clicked): shows checklist (type/lifecycle) or range slider (confidence/source-tier).
- Active selections appear as smaller chips next to or replacing the main chip: `[Type: finding, claim ✕]`
- "Clear all" button right-aligned, visible only when ≥1 filter is active
- All filters are AND across facets, OR within a facet (standard expectation)

For v0.2, filter state is **URL search-param backed** (`?type=finding,claim&lifecycle=mature`) so a filtered view is shareable.

### 3.3 Empty / Loading / Error states

Each list view (and detail view) renders one of:

| State | Trigger | Component |
|---|---|---|
| Loading | `useFetch().loading === true` | `<LoadingState/>` — skeleton shell matching final layout |
| Error | `useFetch().error !== null` | `<ErrorState retry={...}/>` — message + retry button |
| Empty | Fetch succeeded, data array is empty | `<EmptyState message=... suggestion=.../>` |
| Populated | Fetch succeeded, data array non-empty | The view's normal render |

Empty-state copy is per-view (see each §4.x). Loading skeletons match the final layout's structural shape.

### 3.4 Hooks

Two cross-cutting hooks the SPA depends on:

#### `useFetch(path)`

```jsx
const { data, loading, error } = useFetch('/data/cosmology/cards.json')
```

- `path` is relative to the build root
- On mount: fires `fetch(path)`, parses JSON
- Returns `{ loading: true, data: null, error: null }` while in flight
- Returns `{ loading: false, data: <parsed>, error: null }` on success
- Returns `{ loading: false, data: null, error: <err> }` on failure
- Caches by path within session (subsequent calls return cached result; reload via `UPDATE` flag busts cache by full page reload)
- All data files share the same envelope (per data-model §4); the hook returns the **`data` field** of the envelope, not the full envelope. Envelope metadata accessible via `useFetch(path, { meta: true })` if needed

#### `useVersionFlag()`

```jsx
const { isStale, reload } = useVersionFlag()
```

- On mount: captures the loaded `build_id` (from `version.json` fetched at app boot)
- On `visibilitychange` to `visible` AND every 30s while visible: fetches `/version.json` (cache-busting query string)
- If `fetched.build_id !== loaded.build_id` → `isStale = true`
- `reload()` calls `window.location.reload()` (which busts every cache via fresh page load)
- Used by `<UpdateFlag/>` in the header

Implementation lives in `views/src/src/hooks/`. Both hooks are ≤50 lines each.

### 3.5 Mock-to-real data swap (handoff from Epic 4)

Epic 4 ships pages with `import mock from '../_mock/X.json'`. Epic 8 swaps these to real fetches.

The diff is mechanical:

```jsx
// Epic 4 form
import mock from '../_mock/cards.json'
export default function Artifacts() {
  const cards = mock
  return <ArtifactsTable cards={cards} />
}

// Epic 8 form
import { useFetch } from '../hooks/useFetch'
import { useParams } from 'react-router-dom'
export default function Artifacts() {
  const { workspace } = useParams()
  const { data: cards, loading, error } = useFetch(`/data/${workspace}/cards.json`)
  if (loading) return <LoadingState shape="artifacts" />
  if (error) return <ErrorState retry={...} />
  if (!cards || cards.length === 0) return <EmptyState ... />
  return <ArtifactsTable cards={cards} />
}
```

When all pages are swapped, delete `views/src/src/_mock/` entirely. Acceptance check (§7) verifies it's gone.

---

## 4. Per-View Implementation

### 4.1 Landing (`/`)

**Purpose:** Cross-workspace startpoint. Workspace switcher + status overview + cross-workspace articles.

**Header:** top row only (`useParams().workspace` is null → bottom row not rendered).

**Data fetched:**
- `/data/domains.json` (workspaces with metrics)
- `/data/stats.json` (global aggregates, optional — used in a hero band)
- `/data/articles.json` (cross-workspace; render last 3 in a strip)

**Composition:**
```
┌────────────────────────────────────────────────────┐
│  [Hero: CONSTRUCT, install path, total stats]     │
├────────────────────────────────────────────────────┤
│  Workspaces                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │StatusCard│ │StatusCard│ │StatusCard│   (grid)  │
│  └──────────┘ └──────────┘ └──────────┘           │
├────────────────────────────────────────────────────┤
│  Recent articles                                   │
│  [ArticleCard] [ArticleCard] [ArticleCard]   →all │
└────────────────────────────────────────────────────┘
```

**StatusCard contents** (per data-model §5.1 metrics):
- Workspace name + status badge (active/paused/archived)
- Papers count, cards count (with seed/growing/mature breakdown), connections count
- Last research-cycle date, last curation-cycle date
- Quick links: → workspace dashboard, → digests, → knowledge graph

**Density:** Spacious.

**Interactions:**
- Click StatusCard or any quicklink → `/<workspace>/...`
- Click ArticleCard → `/articles/<slug>` (full page)
- "→ all" link in articles strip → `/articles`

**Empty state:** No workspaces yet. Render: *"No workspaces initialised. Run `Initialize <topic>` from your CONSTRUCT conversation to get started."*

**Loading:** Skeleton: 3 grey StatusCard placeholders + 3 ArticleCard placeholders.

### 4.2 Articles list (`/articles`)

**Purpose:** Cross-workspace published outputs. Reading-focused magazine cards.

**Header:** top row only.

**Data fetched:** `/data/articles.json`

**Composition:**
```
┌──────────────────────────────────────────────────────┐
│  Articles                          (2 workspaces)    │
│  [Type ▾] [Status ▾] [Workspace ▾]    Clear all  → │
├──────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐   │
│  │ Article title (Syne, large)                  │   │
│  │ Excerpt (Manrope, 2 lines)…                  │   │
│  │ briefing • 2026-04-20 • cosmology • conf≥2  │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ Another title…                               │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

**Filters:**
- **Type** (chip multi-select): briefing, essay, review, etc. (whatever `articles[].type` values exist in data)
- **Status** (chip multi-select): draft / published
- **Workspace** (chip multi-select): from the workspaces represented in the data

Sort: `date` DESC, fixed (no sort UI for v0.2 — articles are typically few).

**Density:** Spacious magazine grid. ~2 columns at desktop, 1 at tablet.

**Interactions:** Click ArticleCard → `/articles/<slug>`.

**Empty state:** *"No articles published yet. Run `synthesis` to draft one from your knowledge cards."*

### 4.3 Article detail (`/articles/:slug`)

**Purpose:** Read one article with provenance trace.

**Header:** top row only.

**Data fetched:** `/data/articles.json` (filter to entry with matching `id` or filename slug). Loads full envelope (need full data because list version may carry only excerpt; data-model §5.5 has `body_markdown` so list & detail use the same file).

**Composition:**
```
┌────────────────────────────────────────────────────┐
│  Article title (Syne, very large)                 │
│  briefing  •  2026-04-20  •  cosmology, climate   │
│  confidence floor: ≥ 2                            │
├────────────────────────────────────────────────────┤
│                                                    │
│  [MarkdownRenderer renders body_markdown]          │
│                                                    │
├────────────────────────────────────────────────────┤
│  Sources                                           │
│  ┌────────────────────────────────────────────┐   │
│  │ Card title              type  conf  contrib│   │
│  │ … (one row per source_cards[] entry)       │   │
│  └────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

**Sources section (Provenance trace):**
- Each row from `source_cards[]` (data-model §5.5)
- Columns: card title (clickable), epistemic_type tag, ConfidencePill, contribution note
- Missing cards (`status: "missing"`) rendered greyed-out with "(card removed)"

**Density:** Spacious (long-form reading).

**Interactions:** Click a source card row → `/<source.workspace_id>/artifacts?card=<id>` (opens artifacts page with that card's side panel pre-opened).

**Empty state:** N/A — slug not found renders `<NotFound/>` page.

### 4.4 Workspace dashboard (`/:workspace/`)

**Purpose:** Per-workspace at-a-glance health.

**Header:** both rows (current workspace highlighted in bottom-row Dashboard pill).

**Data fetched:**
- `/data/<workspace>/stats.json`
- `/data/<workspace>/events.json` (recent activity)
- `/data/domains.json` (filter to this workspace; provides workspace name + status)

**Composition:**
```
┌────────────────────────────────────────────────────┐
│  Cosmology  •  active  •  Last research: 2026-04-25│
├────────────────────────────────────────────────────┤
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                  │
│  │MetTl│ │MetTl│ │MetTl│ │MetTl│  (papers, cards, │
│  │ 47  │ │ 120 │ │ 184 │ │ 32% │   edges, mature%)│
│  └─────┘ └─────┘ └─────┘ └─────┘                  │
├────────────────────────────────────────────────────┤
│  Lifecycle distribution      Confidence histogram  │
│  [Donut chart]               [Bar chart]           │
├────────────────────────────────────────────────────┤
│  Recent activity                                   │
│  [ActivityList — last 10 events]                   │
└────────────────────────────────────────────────────┘
```

**Charts (recharts):**
- **Lifecycle distribution:** PieChart/Donut with 4 slices (seed/growing/mature/archived). Colors from `--lifecycle-*` CSS vars
- **Confidence histogram:** BarChart, x-axis 1-5, y-axis count. Colors from `--confidence-*` CSS vars

**Activity list:** Each event from `events.json`, formatted as: `<time> <actor> <type> <subject>`. Use Tag for actor + ConnectionTypeIcon if relevant.

**Density:** Spacious.

**Interactions:**
- MetricTile click → relevant view (cards count → /<workspace>/artifacts; edges count → /<workspace>/knowledge-graph; etc.)
- Activity item click → relevant detail (card created → /<workspace>/artifacts?card=<id>)

**Empty state:** Workspace exists but no cards yet. Render: *"This workspace is initialized but empty. Run a research-cycle to start populating."*

### 4.5 Knowledge graph (`/:workspace/knowledge-graph`)

**Purpose:** Force-directed exploration of cards + connections.

**Header:** both rows.

**Data fetched:**
- `/data/<workspace>/cards.json`
- `/data/<workspace>/connections.json`

**Composition:**
```
┌────────────────────────────────────────────────────────────┐
│  [Type ▾] [Lifecycle ▾]                       Clear all   │
├────────────────────────────────────────────┬───────────────┤
│                                            │ Card detail  │
│                                            │ ───          │
│                                            │ Title        │
│         [react-force-graph canvas]         │ Type: finding│
│                                            │ Conf: 4/5    │
│                                            │ Tier: 2      │
│                                            │ Lifecycle: m │
│                                            │ ─── body ─── │
│                                            │ excerpt…     │
│                                            │ ─── conns ─  │
│                                            │ →supports: A │
├────────────────────────────────────────────┴───────────────┤
│  Legend (click to focus): Type colors, Connection colors  │
└────────────────────────────────────────────────────────────┘
```

**Visual encoding:**
- **Node color** = epistemic type. 10 colors from a categorical palette derived from `references/epistemic-types.md`.
- **Node size** = `1 + log10(connection_count + 1) * scale` — gives visual weight to well-connected cards without overwhelming the layout
- **Edge color** = connection type, 9 colors per `references/connection-types.md`
- **Edge style** = solid for `supports`/`extends`/`enables`/`requires`/`inspires`/`parallels`; dashed for `contradicts`/`challenges`; dotted for `gap-for`

**Filters:**
- **Type** chip multi-select: 10 epistemic types
- **Lifecycle** chip multi-select: 4 states
- Filter logic: AND across facets, OR within. Filtered-out nodes fade to ~10% opacity (don't disappear) so the graph keeps its shape

**Interactions:**
- **Click node** → side panel shows card detail (title, all frontmatter fields, body excerpt, full connection list)
- **Click empty space** → close side panel
- **Click connection in side panel** → focus the other endpoint node (animate camera, highlight)
- **Hover node** → show title tooltip
- **Drag** → reposition (force simulation re-equilibrates)
- **Wheel/pinch** → zoom

**Performance:**
- Budget: 500 nodes for v0.2
- Beyond that: render warning ("Graph too large to render interactively (N nodes). Use filters to narrow.")

**Density:** Spacious (full-bleed canvas; toolbar above).

**Empty state:** No cards yet — render *"Knowledge graph appears once you have cards. Run a research-cycle on this workspace."*

**Loading:** Skeleton: a static circle outline placeholder (no force animation).

### 4.6 Domain landscape (`/:workspace/landscape`)

**Purpose:** Domain health + taxonomy coverage.

**Header:** both rows.

**Data fetched:**
- `/data/<workspace>/stats.json`
- `/data/domains.json` (filter to this workspace)

**Composition:**
```
┌────────────────────────────────────────────────────┐
│  Cosmology — Intelligent spatial worlds            │
│  active  •  120 cards  •  47 papers  •  conf 3.12  │
├────────────────────────────────────────────────────┤
│  Categories                                        │
│  [HeatmapGrid — categories × cards count]          │
├────────────────────────────────────────────────────┤
│  Cross-domain links                                │
│  → climate-policy ("Earth-observation overlap")    │
├────────────────────────────────────────────────────┤
│  Health                                            │
│  Orphans: 3   Avg confidence: 3.12   Density: 0.47 │
└────────────────────────────────────────────────────┘
```

**HeatmapGrid:** simple grid where each cell = a content_category. Fill intensity by card count. Empty categories rendered light grey ("not yet covered").

**Density:** Spacious.

**Interactions:**
- Click a category cell → `/<workspace>/artifacts?content_categories=<cat>` (filtered cards browser)
- Click a cross-domain link → `/<other-workspace>/`

**Empty state:** Workspace has no domains.yaml entry. *"This workspace doesn't have a configured domain. Run domain-init to set up."*

**v0.2.1 deferral:** comparison view across multiple workspaces (PRD §4.3 had this; not in MVP).

### 4.7 Artifacts (`/:workspace/artifacts`)

**Purpose:** Cards browser. Compact table for scanning many cards.

**Header:** both rows.

**Data fetched:**
- `/data/<workspace>/cards.json`
- `/data/<workspace>/connections.json` (used to render connection-list in side panel)

**Composition:**
```
┌────────────────────────────────────────────────────────┐
│  [Type ▾] [Lifecycle ▾] [Conf ▾] [Tier ▾] [Tag…]  ✕  │
├────────────────────────────────────────────────────────┤
│  Title              Type    Conf  Tier  Life  Conns  │
│  ─────────────────  ─────   ────  ────  ────  ─────  │
│  Causal world…       finding  4    2    growing  12   │ ◄─ row click
│  Hi Robot: open…     finding  3    1    seed     5    │
│  …                                                    │
└────────────────────────────────────────────────────────┘
                        ┌────────────────────────────┐
                        │ Side panel — card detail   │
                        │ (when ?card=<id> in URL)   │
                        └────────────────────────────┘
```

**Filters:**
- **Type** chip multi (10 options)
- **Lifecycle** chip multi (4 options)
- **Confidence** chip-popover: range slider 1–5
- **Source tier** chip-popover: range slider 1–5
- **Tag** free-text input (autocompletes from existing tags) — multi
- All filter state in URL search params (per §3.2)

**Sort:** Click column header to sort ASC/DESC. Default: `created` DESC.

**Columns** (compact, density per design-prototype §6.2):
- Title (clickable, truncate)
- Epistemic type Tag
- ConfidencePill (1–5)
- SourceTierIndicator (1–5, terse)
- Lifecycle Badge
- Connections count (number)
- Last reviewed (relative time)

**Side panel (when `?card=:id`):**
- Title (Syne, larger)
- Frontmatter fields (type, confidence, tier, lifecycle, domains, content_categories, tags, author, created, last_reviewed)
- MarkdownRenderer of `body_markdown`
- Sources list (frontmatter `sources[]`)
- Connections list — joins with `connections.json` to show typed edges to other cards (clickable → `?card=<other-id>` swaps panel)

**Density:** Compact (table). Side panel is medium.

**Interactions:**
- Click table row → URL gains `?card=<id>` (side panel opens)
- Click connection in side panel → URL `?card=<other-id>` (side panel updates)
- ESC or click X → URL drops `?card`, side panel closes

**Empty state:** *"No cards yet. Run research-cycle to gather some."*

**Performance:** 1000-row budget. Beyond: simple paging (deferred unless Epic 10 fixtures exceed).

### 4.8 Digests list (`/:workspace/digests`)

**Purpose:** Browse past research-cycle outputs.

**Header:** both rows.

**Data fetched:** `/data/<workspace>/digests.json`

**Composition:**
```
┌────────────────────────────────────────────────────┐
│  [Date range ▾]                       Clear all   │
├────────────────────────────────────────────────────┤
│  2026-04-25  ·  Causal world models    12 papers │ ◄ row
│  Top: "Causal World Modeling for Robot Control"  │
├────────────────────────────────────────────────────┤
│  2026-04-22  ·  RLHF advances           8 papers │
│  Top: "Open-Ended Instruction Following…"         │
├────────────────────────────────────────────────────┤
│  …                                                 │
└────────────────────────────────────────────────────┘
```

Each list row shows date, theme, papers ingested count, and a one-line preview of the top finding.

**Filters:** Date range chip (popover with start/end date pickers).

**Sort:** Date DESC fixed.

**Density:** Compact (list rows, not table — slightly more breathing room than artifacts).

**Interactions:** Click row → `/<workspace>/digests/<id>` (full page).

**Empty state:** *"No research digests yet. Run a research-cycle on this workspace."*

### 4.9 Digest detail (`/:workspace/digests/:id`)

**Purpose:** Read one digest in full.

**Header:** both rows.

**Data fetched:** `/data/<workspace>/digests.json` (filter to this id).

**Composition:**
```
┌────────────────────────────────────────────────────┐
│  Research Digest — 2026-04-25                     │
│  Causal world models — closed-loop training       │
├────────────────────────────────────────────────────┤
│  Summary                                           │
│  Papers: 12 found, 8 ingested, 4 skipped, 5 cards │
├────────────────────────────────────────────────────┤
│  Top findings                                      │
│  1. Causal World Modeling for Robot Control       │
│     relevance ★★★★, source: arXiv                  │
│     Summary text (Markdown)…                       │
│  2. …                                              │
├────────────────────────────────────────────────────┤
│  Search clusters                                   │
│  [table: cluster, queries, results, ingested]     │
├────────────────────────────────────────────────────┤
│  Coverage notes & suggested adjustments            │
│  [MarkdownRenderer of two combined sections]      │
└────────────────────────────────────────────────────┘
```

**Density:** Spacious for prose sections, compact for the search-clusters table.

**Interactions:** None beyond reading. Top findings link out to source URL where present (`url` field per data-model §5.4).

**Empty state:** N/A — id not found → `<NotFound/>`.

**Note:** `raw_path` from data-model §5.4 is **not exposed** in the SPA UI per data-model §11.7 (security note about not fetching workspace files directly).

### 4.10 NotFound (`*`)

Catch-all route. Renders:
- "Page not found" header
- Suggested actions: "Back to landing" link, current workspace link (if `useParams().workspace` would be in the matched URL fragment)
- Footer

No data fetched. Always renders successfully.

---

## 5. Cross-View Composition

### 5.1 Header `<UpdateFlag/>` wiring

Per design-prototype §4.4 + this spec §3.4: `<UpdateFlag/>` consumes `useVersionFlag()` and renders the pill. On click, calls `reload()`.

```jsx
function UpdateFlag() {
  const { isStale, reload } = useVersionFlag()
  if (!isStale) return null   // Per design-prototype §11.1: invisible when fresh
  return (
    <button onClick={reload} className="px-3 py-1 rounded-full
      border border-cyan-400/50 text-cyan-300 text-xs font-medium
      hover:bg-cyan-400/10 focus:ring-2 focus:ring-cyan-400/50">
      ↻ UPDATE
    </button>
  )
}
```

### 5.2 Header `<WorkspaceSwitcher/>` wiring

Consumes `useFetch('/data/domains.json')` to list available workspaces. Reads `useParams().workspace` to know current. Renders pill + dropdown per design-prototype §4.5.

### 5.3 `<MarkdownRenderer/>` wiring

Wraps `react-markdown` with theme-aware styling (Tailwind prose classes adapted to dark theme + `--text-*` tokens). Used in: card detail side panel, article detail body, digest top findings, digest coverage notes.

Uses `remark-gfm` for tables and strikethrough (small, well-known dep — add to scaffold spec deps if not already? Actually it IS implied by `react-markdown` v9; document if package.json adds it).

---

## 6. Acceptance Checks

This spec is implemented when:

- [ ] All 9 routes from `spec-v02-runtime-topology.md` §5 plus NotFound render with real data
- [ ] `useFetch` hook implemented, caches per path, returns `{loading, data, error}`
- [ ] `useVersionFlag` hook implemented, polls `version.json` per design-prototype §4.4
- [ ] `<UpdateFlag/>` invisible when fresh, cyan pill when stale (design-prototype §11.1 follow-up resolved here)
- [ ] `views/src/src/_mock/` is **deleted** (mock-to-real swap complete)
- [ ] `useFetch` cache invalidates on full reload (verify by clicking UPDATE flag → fresh JSON loads)
- [ ] Filter state is URL-search-param-backed for Articles, Artifacts, Digests
- [ ] Article detail: `source_cards` rows are clickable and navigate to `/<workspace>/artifacts?card=<id>` with side panel pre-opened
- [ ] Artifacts side panel: clicking a connection swaps `?card=<id>` and re-renders panel with the connected card
- [ ] Knowledge graph: 500 nodes render at ≥30fps (manual smoke test)
- [ ] Knowledge graph: filters cause faded (not removed) nodes per §4.5
- [ ] Knowledge graph: click node → side panel; click empty → close
- [ ] All views have populated, loading, error, and empty-state renderings
- [ ] `LoadingState` skeletons match the structural layout of populated views (verify visually)
- [ ] No view fetches data from outside `views/build/data/` or `views/build/version.json` (verify with browser network tab)
- [ ] No PUT/POST/DELETE in any source file (per architecture-overview I2)
- [ ] All filter chips support multi-select where the data-model permits multi-value

---

## 7. Open Follow-ups

1. **Markdown deps.** §5.3 mentions `remark-gfm`. Confirm during implementation whether it's already a transitive dep of `react-markdown` v9 or needs explicit listing in `package.json`. If explicit → update `spec-v02-scaffold.md` §4.1.
2. **`useFetch` cache invalidation.** Beyond full reload, no explicit invalidation API. Acceptable for v0.2 (UPDATE flag is the only way fresh data lands). v0.2.1 may add a `refetch()` action if hooks-without-reload are needed.
3. **URL filter param shape.** §3.2 says `?type=finding,claim`. Comma-separated multi values are simple but require parsing. Alternatives: repeated params (`?type=finding&type=claim`) or JSON-encoded. Final picking is implementation detail; keep consistent across views.
4. **Knowledge graph layout determinism.** `react-force-graph` uses random initial positions, so the layout differs every load. Ok for v0.2 (graph as exploration tool). v0.2.1 may seed with a fixed RNG for reproducibility.
5. **Mobile fallback.** Per design-prototype §7.1, mobile is out of scope. Some views (knowledge graph especially) will render brokenly. Acceptable; documented in PRD patches (Epic 11).
6. **Artifacts virtualization.** §4.7 budgets 1000 rows. If real workspaces exceed this, react-window or similar virtualization is needed. Defer until proven.
7. **Activity feed event types.** §4.4 ActivityList renders `{actor} {type} {subject}` plain. Some events benefit from custom rendering (e.g., "card created" with title hyperlink). Implement per-type rendering as a small switch in `<ActivityList/>`; new event types fall back to the generic format.

---

## 8. References

- `spec-v02-runtime-topology.md` §5 (routing — every route enumerated here is in §5)
- `spec-v02-data-model.md` — every JSON shape consumed by these views
- `spec-v02-design-prototype.md` §4 (header), §5 (component inventory), §6 (density), §7 (responsive/a11y), §11 (open follow-ups including UPDATE-flag fresh state — **resolved here as invisible**)
- `spec-v02-scaffold.md` — directory layout, routes.jsx, hooks/ folder
- `spec-v02-data-generation.md` — produces the data this spec consumes
- `spec-v02-hook-integration.md` — defines when fresh data appears (post research/curation/synthesis)
- `architecture-overview.md` §3 (three layers; the SPA is layer 3, read-only), §4 (invariants — I2 read-only direction enforced here)
- `references/epistemic-types.md`, `connection-types.md`, `lifecycle-states.md`, `confidence-levels.md`, `source-tiers.md` — vocabulary surfaced in tags, badges, encodings
- `views/design-example/src/pages/*.jsx` — visual reference for some pages (Digests, Blog/Articles, KnowledgeGraph). Do NOT copy wholesale — content was domain-specific to ISW
