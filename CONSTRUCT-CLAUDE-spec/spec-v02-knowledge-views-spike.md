# spec-v02-knowledge-views-spike — Knowledge-Graph Restyle + Wiki View

**Status:** Spike A locked 2026-04-30 → shipped 2026-05-02 (Slice 12.2 done) · Spike B locked 2026-05-02 (Slice 12.1 ready to plan)
**Date:** 2026-04-29 (initial) · 2026-04-30 (Spike A decisions locked) · 2026-05-02 (Spike A shipped, Spike B locked)
**Owner:** ;-)mab
**Type:** Two parallel spikes feeding one decision
**Related:** `spec-v02-views.md` §4.5 (current KG), `spec-v02-design-prototype.md`, `spec-v02-data-model.md` §5.2 (cards), §5.3 (connections), `views/design-example/src/public/archive/isw-analysis/knowledge-graph.html` (visual reference), `architecture-overview.md` §3.2 (two-writer invariant), `CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 12 (slice 12.2 = Spike A, slice 12.1 = Spike B)

---

## 1. Why This Spike

User testing on `test-ws/my-construct` (33–24 cards per workspace, ~50 connections each) surfaced two related but distinct problems:

1. **The current force-directed knowledge graph is unusable.** Concrete complaints, in user's words:
   - "the bubbles are thick, so they touch each other"
   - "the edges are not really visible for that reason"
   - "without dragging it is not possible to get overviews and clean up for a specific view"
   - "the labels now are a too big a scale and all overlap and are therefore not readable at all"

2. **A graph is not the right primary read mode for accumulated knowledge.** A wiki-style representation is needed *in addition to* the graph — for daily reading, linking from digests/articles, and printable synthesis output. The graph is for cluster-spotting and contradiction-finding; the wiki is for actually consuming the content.

Both spikes share the same data sources (`cards.json`, `connections.json`) and must respect the v0.2 two-writer invariant (`architecture-overview.md` §3.2): no new HTML writer to `views/build/`.

---

## 2. Spike A — Knowledge-Graph Restyle (current engine)

### 2.1 What's actually rendering today

**File:** `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/src/pages/KnowledgeGraph.jsx` (537 lines).

**Library:** `react-force-graph-2d@^1.27.0` — a React wrapper around `d3-force` simulation + HTML5 Canvas rendering. (NB: `d3@^7.9.0` is also already a direct dep, so a raw-D3 path needs no new dependency either.)

**Rendering pipeline:**

```
cards.json  ─┐
             ├──> useFetch ──> graphData{nodes,links} ──> ForceGraph2D
connections ─┘                                                │
                                                              ▼
                                          d3-force simulation (link, charge, center)
                                                              │
                                                              ▼
                                          Canvas paint loop (every tick)
                                                              │
                                                              ▼
                                          nodeCanvasObject(node, ctx) per node
                                          linkCanvasObject(link, ctx) per link
```

Everything visual is drawn inside two callbacks (`nodeCanvasObject`, `linkCanvasObject`) that get the raw 2D canvas context. We have **full control over per-node and per-link rendering** — fills, strokes, glows, dashed lines, labels, icons. We are not constrained by the library's defaults.

### 2.2 What we control (configuration surface)

| Lever | Current value | What it does |
|---|---|---|
| `nodeRelSize` | `1` | Multiplier on default node area; we override drawing entirely so this only affects pointer hit area |
| Node radius formula | `6 + sqrt(degree)*2.2` | Gives high-degree nodes visual weight; *too aggressive at our scale (33 cards × ~50 edges)* |
| `d3Force('link').distance()` | `140` | Target edge length; smaller = denser cluster |
| `d3Force('link').strength()` | `0.4` | How rigidly edges hold their length |
| `d3Force('charge').strength()` | `-600` | Node-node repulsion; more negative = more breathing room |
| `d3VelocityDecay` | `0.32` | Friction; higher = faster settle |
| `d3AlphaDecay` | `0.018` | How fast simulation cools; lower = longer wiggle |
| `cooldownTicks` | `Infinity` | Sim never stops → CPU never idles |
| `warmupTicks` | `40` | Pre-render ticks before first paint |
| `linkDirectionalArrowLength` | `4` | Arrowheads on edges |
| `linkLineDash` | per type | Dashed for `contradicts`/`challenges`, dotted for `gap-for` |
| `linkWidth` | `1.8` spotlit, `0.7` ambient | Edge weight |
| Label font | `'500 11px Manrope'` | Node labels |
| Edge-label font | `'9px Manrope'` | When `showEdgeLabels=true` |
| Label visibility gate | `globalScale > 0.5` | Hidden when zoomed out |
| `onNodeDragEnd` → `fx,fy` | yes | Drag pins a node |
| `onBackgroundClick` | clears selection | |
| Filter chips | type + lifecycle | Multi-select; URL-backed |
| Ego-network highlight | hover or selected → 1-hop set | Everything else fades to alpha 0.18 |
| Side panel | `CardSidePanel` (existing) | Opens on click; full card detail |

What we don't have: legend-toggle filtering (clicking a type in the legend to hide it), auto fit-to-view on first settle, node-collision force, edge bundling, hierarchical layouts.

### 2.3 Pain points → fixes (mapped 1:1)

| User complaint | Root cause in code | Fix |
|---|---|---|
| Bubbles thick / touching | radius `6 + sqrt(deg)*2.2` peaks at ~22px at avg degree 6; with charge -600 the layout doesn't separate them | Shrink to `4 + sqrt(deg)*1.4` (peaks ~12px); add `d3-force` collision with `r + 4` padding; bump charge to `-1400` |
| Edges not visible | `linkWidth` 0.7 ambient, alpha 0.4–0.85; loses to thick fills | Drop opacity to `0.22` ambient / `0.85` spotlit (matches design-example), increase contrast on stroke vs background, draw edges *before* nodes (already do, but verify with z-order) |
| Can't get overview without dragging | No `cooldownTicks` finite → no `onEngineStop` → never auto-fits | Set `cooldownTicks={150}`; on engine stop call `fgRef.current.zoomToFit(600, 40)` (built-in), then disable further auto-fit so user pan/zoom isn't fought |
| Labels overlap, too big | Always-on at zoom > 0.5; no collision detection between labels | (a) Bump zoom gate to `> 1.0` for ambient labels; (b) keep labels visible only on `egoSet` (spotlit nodes + neighbours); (c) lower font to `10px`; (d) add 2px text-shadow stroke for readability against edges |

### 2.4 Restyle scope — match `views/design-example` visual grammar

The design-example HTML at `views/design-example/src/public/archive/isw-analysis/knowledge-graph.html` (1544 lines, raw D3) defines a coherent visual language we want to adopt. Mapping each element to our React component:

| Element | Design-example value | Apply to ours |
|---|---|---|
| Background | `#0a0e17` (deep navy) | Current dark `bg-black/40` → use `#0a0e17` |
| Side panel bg | `#111827` | New panel surface (currently transparent/glass) |
| Node stroke | `#445566` (muted slate) | Replace `brighten(baseColor)` |
| Edge default opacity | `0.35` | Currently varies 0.18–0.85; standardise |
| Edge highlighted opacity | `0.9` | Already close |
| Edge dimmed opacity | `0.07` | Currently 0.18; lower it |
| Type colour palette | 6 fixed pairs (theme blue, provocation purple, finding green, gap amber, method cyan, weird pink) | Replace our 10-colour palette with the 6 + 4 extension; use the design-example's `bg/fg` pairs for badges |
| Confidence indicator | 5 small dots, filled per level | Add `<ConfidencePill>` to side panel (already speccd in `spec-v02-design-prototype.md` §5.2) |
| Edge labels | always-on at 9px | Optional toggle stays; default to **on** when ≤ 30 edges, **off** above |
| Connection list in panel | Hover-highlight items, click-to-jump | We already have this via `CardSidePanel` — match the row styling (8px padding, `#1a2332` bg, `#243447` hover) |
| Legend | Bottom-left, click-to-toggle-type | Currently bottom legend is read-only; add click → toggle visibility (drives same filter URL state) |
| Drag-to-pin indicator | Small white dot upper-right of pinned node | Already implemented in `nodeCanvasObject` |

**Effort estimate:** ~½ day. Pure styling + force-tuning + a finite cooldown + legend-as-filter wiring. No new dependencies. No architecture change. Existing `CardSidePanel`, filter URL state, useFetch all stay.

### 2.5 Why we are NOT replacing the engine

Considered alternatives and rejected:

| Alternative | Why rejected |
|---|---|
| Raw D3 transcribed from design-example | ~600–800 lines of mostly imperative D3 to maintain. We'd lose React's reactivity for filter chips, side panel, URL state. The design-example mixes concerns we've already separated. Net: more code, no visual gain over a faithful restyle. |
| `cytoscape.js` + CoSE-Bilkent layout | Better for dense graphs but new ~300kb dep; loses our existing canvas drawing investment; CSS-driven theming clashes with our Tailwind+Canvas mix |
| iframe with generated HTML | Breaks two-writer invariant — see `architecture-overview.md` §3.2 and discussion below |
| Static SVG + d3-force | We already have canvas; SVG at 500-node budget hurts perf; no clear visual win |

### 2.6 Why iframe-style HTML is off the table

Detailed because the user explicitly asked. The cost is structural, not aesthetic:

1. **Three writers, not two.** Per `architecture-overview.md` §3.2 the only writers to `views/build/` are `views-build` (Vite, rare) and `views-generate-data` (Python, every cycle). A KG-HTML generator would be a third writer with overlapping output paths; the safe-delete invariant on `views/build/data/` (build_id determinism) would have to extend to a new HTML namespace.

2. **HTML becomes both data and presentation.** Today: edit a card → JSON regenerated → SPA picks it up via UPDATE flag in 30s, no Vite rebuild. With per-graph HTML: every card edit forces an HTML regen too; visual changes (palette, node size) require touching the data-generation toolchain. The clean cut between `views-build` (Vite-owned) and `views-generate-data` (Python-owned) breaks.

3. **UPDATE flag stops applying to the graph.** The polling diff at `version.json` triggers `useVersionFlag` in the SPA. An iframe's content is opaque to the parent; the user's open tab won't see graph staleness without ad-hoc cache-busting per iframe.

4. **The React shell terminates at the iframe boundary.** Header, workspace switcher, breadcrumbs, "see also" links from side panel into `/artifacts?card=…`, the wiki cross-links from §3 below — none traverse iframes natively. We'd reinvent navigation.

5. **Two toolchains for one feature.** Vite + npm for the SPA vs. Python + string-templating for the HTML generator. Test coverage doubles; CI pipelines diverge.

6. **Graph code lives outside the SPA.** 1544 lines of imperative D3 outside the rest of the React codebase. Each schema change (new epistemic type, new connection type, new metadata field) means hand-editing the HTML in addition to the SPA.

The **lift-D3-into-React middle path** (option 2 from the prior conversation) avoids all six problems but trades faithful 1:1 port for ~1 day of porting work. Given that the restyle path achieves ~90% of the visual goal in ~½ day with zero new code in unfamiliar shape, the recommendation is **restyle first, evaluate, port D3 only if restyle proves insufficient.**

### 2.7 Spike A questions — RESOLVED 2026-04-30

- **Q-A1.** Edge labels default. **→ Auto-on when `links.length ≤ 30`, toggle override stays.** Equivalent to D2.
- **Q-A2.** Node sizing metric. **→ Keep degree, shrunk: `4 + sqrt(deg) × 1.4` (peak ~12px).** Confidence×lifecycle considered but rejected for v0.2 — the graph's job is cluster-spotting, and degree is the right visual proxy. Equivalent to D3.
- **Q-A3.** Drag-to-pin persistence across navigation. **→ Deferred.** Implementing requires per-workspace localStorage (or server round-trip); not in scope for the restyle. Backlog item.
- **Q-A4.** Side panel collapse animation. **→ 300ms ease.** Matches design-example feel; one CSS transition on existing `CardSidePanel`.
- **Q-A5.** Legend behaviour. **→ Click-to-toggle-type.** Drives the same `?type=…` URL state as the chip toolbar — two surfaces on one state, no duplicate logic.

---

## 3. Spike B — Wiki-Style Representation (new view)

### 3.1 Concept

A read-mode page for accumulated knowledge. Cards rendered as a long, browsable, searchable, linkable document — *not* a graph, *not* a filterable table (Artifacts already does that). Closer in spirit to a domain handbook or living textbook.

**Primary use cases:**
- Daily reading mode: scroll through what's been accumulated, click into details
- Link target for digests/articles: `[Bostrom's argument](#bostrom-simulation-argument)` resolves
- Synthesis input: copy-paste-friendly continuous prose
- Print/export-friendly format for reports

**What it is not:**
- Not the graph (no positions, no force, no overview)
- Not the artifacts page (artifacts is filterable index → side panel; wiki is reading view)
- Not the landscape page (landscape is health metrics + taxonomy heatmap)

### 3.2 Layout options (need a decision)

**Option A — Long scroll, grouped, in-line collapsibles.**

```
┌────────────────────────────────────────────────────────┐
│  Search / filter chips (lifecycle, confidence, cat)    │
├────────────────────────────────────────────────────────┤
│  THEMES (3)                                            │
│  ▸ enactivism-as-domain-spine          confidence ●●●○○│
│  ▸ self-debate-mpe-axis                confidence ●●●●○│
│  ...                                                   │
│  CLAIMS (12)                                           │
│  ▸ chalmers-reality-plus               confidence ●●●○○│
│      [click to expand inline: full body, sources,      │
│       outbound connections list, inbound backlinks]    │
│  ...                                                   │
│  PAPERS (8) ...                                        │
└────────────────────────────────────────────────────────┘
```

- ✓ Single scrolling spine; matches paper-reading mental model
- ✓ Collapsibles keep noise low; expand reveals body markdown + connections + sources
- ✓ Anchored URLs (`#card-id`) for deep links from digests
- ✗ Long pages need solid jump-to-section; scroll restoration matters

**Option B — Two-pane: TOC sidebar + content.**

```
┌──────────────┬────────────────────────────────────────┐
│ Themes       │  Chalmers: Reality+ ...               │
│ ▸ Enactivism │  ─────────────────────                │
│ ▸ Self       │  [body markdown]                      │
│ ─────────────│  [sources block]                      │
│ Claims       │  ─────────────────────                │
│ ▸ Chalmers ◄ │  ## Connections                       │
│ ▸ Bostrom    │  → supports bostrom-simulation-arg    │
│ ▸ Putnam     │  ← challenged-by dreyfus-on-internet  │
│ ─────────────│  ─────────────────────                │
│ Papers       │  ## Cited as source                   │
│ ▸ Maudlin    │  in digest-2026-04-25, article ...    │
└──────────────┴────────────────────────────────────────┘
```

- ✓ Familiar wiki/docs pattern (MDN, Vite docs, GitBook)
- ✓ Scales to 100s of cards without scroll-fatigue
- ✓ Sticky TOC = always-visible context
- ✗ Side-by-side eats horizontal real estate; mobile/tablet awkward
- ✗ Two scrollers can fight focus

**Option C — List + side-panel detail (mirror Artifacts pattern).**

```
┌────────────────────────────┬──────────────────────────┐
│ chalmers-reality-plus      │ Chalmers: Reality+       │
│ bostrom-simulation-argument│ ──────────────────       │
│ putnam-brain-in-vat ◄─sel  │ [body markdown]          │
│ ...                        │ [connections]            │
└────────────────────────────┴──────────────────────────┘
```

- ✗ This *is* Artifacts. Adds nothing new. Skip.

**Recommendation:** Start with **Option A**. Ship in v0.2; if scrollability proves painful at >100 cards per workspace, revisit Option B in v0.2.1. Option A also degrades gracefully to print/export.

### 3.3 Content model per card (in wiki view)

Per card the page renders, in order:

1. **Anchor**: `<h2 id={card.id}>{card.title}</h2>` (deep-linkable)
2. **Meta row**: epistemic-type badge · lifecycle pill · confidence dots · source-tier · last-reviewed date
3. **Body**: full markdown from `body_markdown` (already in cards.json per data-model spec §5.2)
4. **Sources block**: list of `sources[]` — refs and URLs as link list with titles
5. **Connections out**: grouped by connection type, each with link to target card's anchor
6. **Connections in (backlinks)**: derived from `connects_to` reverse-index; each links back
7. **Mentioned in**: digest IDs and article IDs that reference this card-id (derived from scanning `digests.json` body + `articles.json` provenance) — this is the **payoff for the digest-link problem from question 1**: every backticked card-id surfaces here automatically

Items 6 and 7 are computed client-side from already-fetched JSON.

### 3.4 Filters / search

| Control | Behaviour |
|---|---|
| Search box | Substring match on `title`, `body_markdown`, `tags[]` (debounced 200ms; client-side; Lunr.js optional) |
| Lifecycle | Multi-select chip: `seed`/`growing`/`mature`/`archived` |
| Confidence | Range slider 1–5 (or chips) |
| Category | Multi-select from `content_categories` union |
| Type | Multi-select epistemic types |
| Sort | Default: type → category → title alphabetical. Alternates: created-desc, last-reviewed-desc, confidence-desc |

Filters narrow the rendered list; URL-backed via `useSearchParams` so links survive.

### 3.5 Cross-references this view enables

| From | To | Mechanism |
|---|---|---|
| Digest top finding | Wiki anchor | Backticked card-id in finding text → `<Link to="/${ws}/wiki#${cardId}">` |
| Article body | Wiki anchor | Same — markdown processor rewrites `` `card-id` `` to anchor link |
| Knowledge graph side panel | Wiki anchor | "Open in wiki" button on `CardSidePanel` |
| Landscape category cell | Wiki section | "View cards in this category" → `/wiki?category=X` |
| Wiki anchor → graph | Reverse | "Locate in graph" button → `/knowledge-graph?card=cardId` |

This is what the user identified in question 1: cards have URL sources that aren't being surfaced. The wiki view is the natural surfacing place — every card displays its sources prominently, and every digest/article that mentions it gets a backlink.

### 3.6 Routing + nav

- New route: `/:workspace/wiki` (and `/:workspace/wiki?…filters` query state)
- Header bottom row: insert "Wiki" between "Artifacts" and "Knowledge Graph" — order becomes: Dashboard · Articles · Digests · Wiki · Artifacts · Knowledge Graph · Landscape
- Optional: "Wiki" becomes the default workspace landing replacement at `/:workspace` (currently goes to dashboard) — defer that decision

### 3.7 Effort estimate

| Item | Effort |
|---|---|
| Route + page scaffolding | 1h |
| Card list rendering with badges/meta | 2h |
| Inline collapsible body + markdown | 2h |
| Sources block | 1h |
| Out/in connections lists | 2h |
| "Mentioned in" derivation | 2h |
| Filters + search | 3h |
| URL state | 1h |
| Cross-link wiring (digest → wiki, graph → wiki) | 2h |
| Polish | 2h |
| **Total** | **~½–1 day** |

No new dependencies. All data already in the existing JSON.

### 3.8 Spike B questions — RESOLVED 2026-05-02

- **Q-B1.** Inline collapsible (Option A) vs TOC sidebar (Option B)? → **Option A** (long scroll + inline collapsibles). Locked as D4.
- **Q-B2.** Should `/:workspace` (workspace root) redirect to `/:workspace/wiki` or stay on dashboard? → **Stay on dashboard.** Wiki is an option, not the workspace default; `/:workspace` continues to land on the status overview. Locked as D5.
- **Q-B3.** Lunr.js for full-text search, or start with naive `.includes()` substring? → **Naive substring.** Revisit at >500 cards/workspace.
- **Q-B4.** Print stylesheet — in scope for v0.2 or defer? → **Defer to v0.2.1.**
- **Q-B5.** Does the artifacts page still earn its keep once wiki exists, or merge them? → **Keep both.** Artifacts is the filter-heavy index → side-panel pattern; Wiki is the continuous reading view. Different UX, shared data.

### 3.9 Karpathy LLM-Wiki cross-check (2026-05-02)

Spike B was cross-checked against `analysis-karpathi/llm_wiki_mabstruct_analysis.md` before locking. Outcome: no structural conflict.

- **Aligned:** persistent interlinked human-readable knowledge, cross-references + backlinks ("Mentioned in"), citation-grounded, markdown surface, compounding over time.
- **Beyond LLM-Wiki (already in mabstruct):** claim layer (epistemic_type/confidence/lifecycle/provenance), typed knowledge graph, temporal lifecycle, multi-agent governance. The Wiki view is a *read-mode rendering* over this richer substrate, not a markdown-only system.
- **Deliberate gap:** Karpathy-style **synthesis / topic pages** that aggregate many atomic claims into a topic narrative are NOT in 12.1. The existing `synthesis` workflow + cross-workspace `articles/` cover this concern; deeper compilation is a future improvement to that workflow, not a Wiki-layer responsibility.
- **Positioning consequence locked into Q-B2:** Wiki is a sibling reading view, not the workspace default landing. If product framing later shifts toward "wiki is home" (Karpathy-style), revisit Q-B2 in v0.3+.

---

## 4. Coexistence Model

| Page | Role | Primary use |
|---|---|---|
| `/:workspace` (Dashboard) | Status overview | "What state is this domain in?" |
| `/:workspace/wiki` | **Reading view (NEW)** | "Read what we know about X" |
| `/:workspace/artifacts` | Filterable index | "Find me cards matching Y" |
| `/:workspace/knowledge-graph` | **Visual exploration (RESTYLED)** | "Spot clusters, contradictions, gaps" |
| `/:workspace/digests` | Cycle output | "What did the researcher do?" |
| `/:workspace/landscape` | Domain health | "Where are the gaps?" |
| `/articles` | Cross-workspace | "What synthesis exists?" |

Each route earns its keep with a distinct use case. The wiki + graph pair is the read/explore duality; artifacts/landscape are the find/diagnose duality.

---

## 5. Decision Points

Spike A locked 2026-04-30, shipped 2026-05-02. Spike B locked 2026-05-02.

| ID | Decision | Locked value |
|---|---|---|
| D1 | Spike A: restyle current engine vs. lift-D3 vs. defer | **Restyle** — locked 2026-04-30 (½ day, low risk; lift-D3 / library swap / iframe rejected per §2.5–§2.6) |
| D2 | Spike A: edge labels default (Q-A1) | **Auto-on when ≤ 30 edges, toggle override** — locked 2026-04-30 |
| D3 | Spike A: node sizing metric (Q-A2) | **Degree-based, shrunk to `4 + sqrt(deg) × 1.4`** — locked 2026-04-30 |
| D4 | Spike B: layout option A vs B (Q-B1) | **Option A** (long scroll + inline collapsibles) — locked 2026-05-02 |
| D5 | Spike B: workspace root redirect to wiki (Q-B2) | **Stay on dashboard** — locked 2026-05-02. Wiki is an option, not the default. |
| D6 | Order of work | **Spike A first → Spike B** — locked 2026-04-30 (overrides original wiki-first recommendation; user-driven sequencing call) |
| D7 | Backlog placement | **Epic 12 in v0.2** — locked 2026-04-30; Slice 12.2 active and 12.1 placeholder in `CONSTRUCT-CLAUDE-v02-planning/backlog.md` |
| D8 | Spike B: synthesis / topic-page layer | **Out of scope for 12.1** — locked 2026-05-02. Compilation of cards into topic narratives stays with the existing synthesis workflow + cross-workspace articles. Wiki view renders the atomic-card layer in reading mode only. |

---

## 6. Recommended Path — UPDATED 2026-05-02 (Spike A shipped, Spike B locked)

1. ~~**Slice 12.2 — KG restyle**~~ — **shipped 2026-05-02** at the locked spec values (charge -1400 + d3 collision r+4, cooldownTicks 150 + onEngineStop fit, ambient/spotlit/dimmed alpha 0.22/0.85/0.07, ambient label gate >1.0, design-example palette, click-to-toggle legend, side-panel #111827 + 300ms collapse). The earlier "canvas blanks on drag" failure that pushed deviations was a cross-workspace edge bug, fixed by filtering links to nodes-in-workspace.
2. **Now (~½–1 day):** Build Wiki view — slice 12.1, Option A (D4) at `/:workspace/wiki`, dashboard remains workspace landing (D5). Per §3.3 content model: anchor + meta row + body markdown + sources + connections-out + backlinks (connections-in) + "Mentioned in" (digest/article references). Per §3.4: substring search + filters + URL state. Per §3.5: digest/article/graph cross-links. Per §3.8 D8: no synthesis/topic-page layer (handled by existing synthesis workflow).
3. **Backlog updated** in `CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 12: Slice 12.2 marked done; Slice 12.1 expanded with locked decisions + implementation parameters.

---

## 7. Out of Scope

- Engine swap from `react-force-graph-2d` to anything else
- iframe / per-workspace HTML generation (rejected on architectural grounds — §2.6)
- Cross-workspace knowledge graph (already deferred to v0.2.1 per `spec-v02-views.md` §4.5)
- Print stylesheet (defer to v0.2.1)
- Full-text search beyond substring (defer until card count justifies it)

---

## 8. Cross-References

- `architecture-overview.md` §3.2 — two-writer invariant (motivates §2.6 rejection of iframe)
- `spec-v02-views.md` §4.5 — current knowledge-graph spec (this doc supersedes its visual prescriptions when restyle ships)
- `spec-v02-views.md` §4.7 — artifacts page (clarifies wiki vs artifacts distinction in §4)
- `spec-v02-design-prototype.md` §5.2 — `<ConfidencePill>` component (consumed by wiki + KG side panel)
- `spec-v02-data-model.md` §5.2 — card schema (`body_markdown`, `sources`, `connects_to` already present)
- `views/design-example/src/public/archive/isw-analysis/knowledge-graph.html` — visual reference for §2.4
