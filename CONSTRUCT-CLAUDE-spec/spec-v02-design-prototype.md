# spec-v02-design-prototype — Visual Language, Navigation Taxonomy, Component Inventory

**Status:** Draft
**Date:** 2026-04-28
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 4
**Related:** `prd-v02-live-views.md` §4.7 · `spec-v02-runtime-topology.md` §5 (routing) · `spec-v02-scaffold.md` · `architecture-overview.md` · `views/design-example/` (visual reference, see §13)

---

## 1. Scope

This spec locks the **visual language, navigation taxonomy, and reusable component inventory** for the v0.2 SPA. It is the design contract that Epic 8 (Per-View Implementation) builds against.

**In scope:**
- Theme tokens, palette, typography, spacing, atmospheric background
- Navigation structure (two-row header) and `UPDATE` flag placement
- Component inventory and which view each component serves
- Density baselines, responsive baseline, accessibility baseline
- Forward-ready theming substrate for future per-workspace identities
- A static design prototype demonstrating each route

**Out of scope:**
- Toolchain and dependency list → `spec-v02-scaffold.md`
- Per-view content rules → Epic 8 (`spec-v02-views.md`)
- Data fetching, hooks, polling → Epic 5 / Epic 8

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Visual identity inheritance | `views/design-example/` is **visual reference only**. Lift theme primitives + atmosphere; replace nav (had single-workspace assumption + extraneous routes); rewrite footer (had outdated OpenClaw reference) |
| Theme | Glass-morphism dark. Header `bg-black/40 backdrop-blur-2xl`, borders `white/[0.06]` |
| Background | Static cosmic atmosphere: 3-color radial gradients + dark vignette + 5 fixed star particles. **No rotating rings** |
| Background mechanism | CSS custom properties (`--cosmic-grad-*`, `--star-opacity`) consumed by `<CosmicBG>`. Default theme on `:root`. Future per-workspace overrides via `[data-workspace="..."]` selectors (substrate ready in v0.2; actual variation in v0.2.1+) |
| Fonts | **Syne** for display/brand (weights 500–800), **Manrope** for body/UI (weights 300–600). Loaded once from Google Fonts |
| Header structure | Two-row, sticky. Top row: brand + global links + UPDATE flag. Bottom row: workspace-aware nav links; only present when route is `/<workspace>/...` |
| Workspace switcher | Pill in top-row right side, dropdown to switch. Always visible |
| `UPDATE` flag placement | Subtle pill in top row, left of workspace switcher. Cyan accent when stale. Click to reload |
| Footer | Minimal: brand mark, version, generation timestamp, install path. **No OpenClaw reference** |
| Density | Mixed: spacious for dashboards/detail pages, compact for list views (artifacts, digests) |
| Responsive baseline | Desktop primary, tablet acceptable. **Mobile out-of-scope for v0.2** (PRD §4.7 said "responsive" — refined here to mean tablet-up only) |
| Accessibility baseline | Keyboard nav, visible focus rings, WCAG AA contrast. No aria-rich live regions for v0.2 |
| Static prototype location | `views/src/src/pages/*.jsx` — page stubs become **mock-data prototypes** during Epic 4. Epic 8 swaps mock for real fetch. |

---

## 3. Visual Identity

### 3.1 Color palette

The palette is expressed as CSS custom properties so per-workspace overrides are a single attribute change (see §3.5).

```css
/* views/src/src/index.css */

:root {
  /* Surface colors — solid */
  --bg-base: #0a0a0a;                  /* page background */
  --bg-elevated: rgba(255, 255, 255, 0.04);
  --bg-glass: rgba(0, 0, 0, 0.40);     /* header */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-faint: rgba(255, 255, 255, 0.04);

  /* Text */
  --text-primary: rgba(255, 255, 255, 0.90);
  --text-secondary: rgba(255, 255, 255, 0.60);
  --text-tertiary: rgba(255, 255, 255, 0.40);
  --text-faint: rgba(255, 255, 255, 0.20);

  /* Accent (interactive, focus, UPDATE flag) */
  --accent-cyan: rgb(34, 211, 238);
  --accent-fuchsia: rgb(168, 85, 247);
  --accent-indigo: rgb(99, 102, 241);

  /* Cosmic background gradient stops (default theme) */
  --cosmic-grad-a: rgba(168, 85, 247, 0.18);    /* fuchsia */
  --cosmic-grad-b: rgba(34, 211, 238, 0.12);    /* cyan */
  --cosmic-grad-c: rgba(99, 102, 241, 0.14);    /* indigo */
  --star-opacity: 0.25;

  /* Semantic — mapped from accents */
  --status-active: var(--accent-cyan);
  --status-paused: rgba(234, 179, 8, 0.8);      /* amber */
  --status-archived: var(--text-tertiary);

  /* Confidence scale (1–5, see references/confidence-levels.md) */
  --confidence-1: rgba(220, 38, 38, 0.7);       /* red */
  --confidence-2: rgba(234, 88, 12, 0.7);
  --confidence-3: rgba(234, 179, 8, 0.8);
  --confidence-4: rgba(34, 197, 94, 0.8);
  --confidence-5: rgba(34, 211, 238, 0.9);

  /* Lifecycle (see references/lifecycle-states.md) */
  --lifecycle-seed: rgba(99, 102, 241, 0.7);
  --lifecycle-growing: rgba(34, 211, 238, 0.8);
  --lifecycle-mature: rgba(34, 197, 94, 0.9);
  --lifecycle-archived: rgba(255, 255, 255, 0.3);
}
```

### 3.2 Typography

Two fonts loaded from Google Fonts via `<link>` injected by Layout's `useEffect` (matching design-example's pattern):

```
Syne:    weights 500, 600, 700, 800   →  display headers, brand block
Manrope: weights 300, 400, 500, 600   →  body text, UI labels, navigation
```

Tailwind utility classes:

```js
// In tailwind theme extension (Epic 6 build pipeline reads this)
fontFamily: {
  display: ['Syne', 'sans-serif'],   // class: font-display
  body: ['Manrope', 'sans-serif'],   // class: font-body (default)
}
```

Type scale (Tailwind defaults, used as-is):

| Size | Class | Use |
|---|---|---|
| 10px | `text-[10px]` | Footer micro-text, captions |
| 12px | `text-xs` | Tag labels, table headers |
| 14px | `text-sm` | Body, navigation, UI labels |
| 16px | `text-base` | Article body, card body |
| 18px | `text-lg` | Subheaders |
| 20–24px | `text-xl` / `text-2xl` | Page-level headers |
| 30–36px | `text-3xl` / `text-4xl` | Display, dashboard hero metrics |

Body text is **Manrope 400**. Section headers are **Syne 600 or 700**. Brand block is **Syne 600** at `text-sm`.

### 3.3 Spacing system

Tailwind defaults (4px base). No custom spacing scale needed for v0.2.

| Scale | px | Use |
|---|---|---|
| `gap-1` / `p-1` | 4 | Tight inline (badges) |
| `gap-2` / `p-2` | 8 | Compact lists, button padding |
| `gap-3` / `p-3` | 12 | Default UI density |
| `gap-4` / `p-4` | 16 | Card internal padding |
| `gap-6` / `p-6` | 24 | Section padding (spacious mode) |
| `gap-8` / `p-8` | 32 | Page-level vertical rhythm |
| `gap-10` / `p-10` | 40 | Major section breaks |

### 3.4 Atmospheric background — `<CosmicBG>`

A fixed-position element (`fixed inset-0 z-0`) inside `<Layout>`, behind all content (main wraps in `relative z-10`).

Composition (5 layers, all consuming CSS vars from §3.1):

| Layer | Content | Notes |
|---|---|---|
| 1 | Three radial-gradient washes positioned at corners (uses `--cosmic-grad-a/b/c`) | Color atmosphere |
| 2 | Dark center-to-edge vignette (radial gradient, transparent center → `rgba(0,0,0,0.8)` edges) | Content legibility |
| 3 | Five 1px star particles at fixed positions, opacity = `var(--star-opacity)` | Subtle texture |
| ~~4~~ | ~~800px rotating ring~~ | **Removed** for v0.2 |
| ~~5~~ | ~~560px rotating ring~~ | **Removed** for v0.2 |

The rings are gone because v0.2 is a working tool, not a marketing site. Animation grates over a long session.

### 3.5 Forward-ready theming substrate (per-workspace identity)

The cosmic gradient stops are CSS custom properties. To enable per-workspace identities later, we add overrides keyed off a `data-workspace` attribute on the Layout wrapper:

```css
/* Default — used on /, /articles, and any cross-workspace route */
:root { --cosmic-grad-a: rgba(168, 85, 247, 0.18); /* etc */ }

/* Per-workspace — added in v0.2.1 or later */
[data-workspace="cosmology"] {
  --cosmic-grad-a: rgba(99, 102, 241, 0.18);   /* indigo dominant */
  --cosmic-grad-b: rgba(168, 85, 247, 0.12);
  --cosmic-grad-c: rgba(56, 189, 248, 0.14);
}
```

Layout reads workspace from route params (`useParams().workspace`) and renders:

```jsx
<div data-workspace={workspaceId || 'default'} className="min-h-screen">
  <CosmicBG />
  ...
</div>
```

For **v0.2 MVP**, only the default theme exists. The substrate is in place; the variation file (`per-workspace-themes.css` or similar) is empty. v0.2.1 (or later) adds per-workspace overrides — most likely sourced from a `theme:` block in `domains.yaml` and surfaced via `domains.json`. **No data-model spec change is needed for v0.2** — that field is added when the feature ships.

---

## 4. Navigation Taxonomy

### 4.1 Two-row header

The header is sticky (`sticky top-0 z-50`). Two rows, top always present, bottom conditional.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TOP ROW (always present)                                           │
│  ┌────────┐                                                         │
│  │ ✦ MAB  │   Articles                  [↻ UPDATE]  [▼ cosmology]  │
│  │CONSTR. │                                                         │
│  └────────┘                                                         │
├─────────────────────────────────────────────────────────────────────┤
│  BOTTOM ROW (only on /<workspace>/* routes)                         │
│  Dashboard  •  Knowledge Graph  •  Landscape  •  Artifacts  •  Digests
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Top row contents

Left → right:
1. **Brand** — MABSTRUCT/CONSTRUCT stack, links to `/`. Same as design-example.
2. **Global links** — currently just `Articles` (→ `/articles`). v0.2.1 may add Bridges, Activity. v0.3 may add Help.
3. **(Spacer)**
4. **`UPDATE` flag pill** — invisible (or text `Up to date` at low opacity) when fresh; cyan-accented `↻ UPDATE` when `version.json.build_id` differs from loaded. Click reloads. Detail in §4.4.
5. **Workspace switcher** — pill showing current workspace (or `Switch workspace` on cross-workspace routes). Click opens dropdown. Detail in §4.5.

### 4.3 Bottom row contents

Visible only when route matches `/:workspace/*`:

```
[ Dashboard ] [ Knowledge Graph ] [ Landscape ] [ Artifacts ] [ Digests ]
```

Each link is `NavLink` to `/<workspace>/...`, active state highlighted with `bg-white/[0.1] text-white` (same as design-example pattern). The current workspace ID is taken from `useParams()`.

On `/` and `/articles` routes, bottom row is **not rendered** at all (DOM absent, not just hidden).

### 4.4 `UPDATE` flag

A small pill component, sits in the top row left of the workspace switcher.

States:
- **Fresh** — `var(--text-tertiary)` opacity, text "Up to date" or invisible (TBD in §11)
- **Stale** — visible pill with `var(--accent-cyan)` border + glow, icon `↻`, text "UPDATE"

Behavior:
- A small worker (Epic 5 / Epic 8) polls `/version.json` on tab focus + every 30s
- When `fetched.build_id !== loaded.build_id` → state flips to stale
- Click → `window.location.reload()`

Implementation note: the worker exposes a single `useVersionFlag()` hook (Epic 5 / Epic 8 deliverable).

### 4.5 Workspace switcher

A right-aligned pill component:

- **On `/` or `/articles`** — shows "Switch workspace" placeholder
- **On `/<workspace>/...`** — shows current workspace name + chevron
- **Click** — opens a small dropdown listing all workspaces (from `domains.json`)
- **Current workspace highlighted** in dropdown
- **Click another** → navigate to `/<that-workspace>/`

For MVP, this is a hand-built dropdown using Tailwind + a `useState(open)` boolean. No accessibility-rich combobox primitive — we listed shadcn/Radix as out-of-scope. Trade-off: no keyboard arrow-key navigation in v0.2; click-to-pick only. Acceptable per the accessibility baseline (§7).

### 4.6 Footer

Minimal:

```
MABSTRUCT     CONSTRUCT v0.2.0-dev      generated 2026-04-28T14:32Z      ~/my-construct/
```

Three pieces of info (version, generation timestamp, install path) plus the brand. **No OpenClaw reference**. No social links, no copyright (defer if it ever matters).

Source of each field:
- Version → `CONSTRUCT-CLAUDE-impl/VERSION` (baked into build at compile time)
- Generation timestamp → `version.json.generated_at` (fetched at boot, refreshed on reload)
- Install path → exposed by `views-generate-data` somewhere in `domains.json` envelope or a dedicated meta field (Epic 5 to wire)

---

## 5. Component Inventory

Components live in `views/src/src/components/`. Ones marked **(global)** are imported into Layout. Ones marked **(reused)** are picked up by multiple views.

### 5.1 Core layout

| Component | Role | Used in |
|---|---|---|
| `Layout` (global) | Outer wrapper. Holds `<CosmicBG/>`, `<Header/>`, `<main><Outlet/></main>`, `<Footer/>` | Every route |
| `CosmicBG` (global) | Atmospheric background, consumes CSS vars | Layout only |
| `Header` (global) | Two-row header. Composes `<TopRow/>` + conditional `<BottomRow/>` | Layout only |
| `Header.TopRow` | Brand + global links + UpdateFlag + WorkspaceSwitcher | Header only |
| `Header.BottomRow` | Workspace-aware nav links | Header only, when in workspace route |
| `Footer` (global) | Brand + version + generation timestamp + install path | Layout only |

### 5.2 Navigation primitives

| Component | Role | Used in |
|---|---|---|
| `Brand` | MABSTRUCT/CONSTRUCT stack with sparkle icon | Header.TopRow, Footer |
| `WorkspaceSwitcher` | Pill + dropdown | Header.TopRow |
| `UpdateFlag` | The pill described in §4.4 | Header.TopRow |
| `NavLink` (reused) | Pill-style active-state link wrapping `react-router-dom`'s NavLink | Header.BottomRow, side panels |

### 5.3 Data display (reused across views)

| Component | Role | Used in |
|---|---|---|
| `StatusCard` | Workspace summary panel (papers, cards, edges, status, last activity) | Landing |
| `MetricTile` | Single big number + label + optional trend | Workspace dashboard |
| `Chart` | Wrapper around recharts; consumes data + theme tokens | Workspace dashboard, Stats overview |
| `Table` (compact) | Sortable, filterable table for list views | Artifacts, Digests |
| `MarkdownRenderer` | `react-markdown` with theme-aware styling | Card detail, Article detail, Digest detail |
| `Tag` | Small pill for epistemic-type, lifecycle, content-category | Cards, digests |
| `Badge` | Status indicator (active/paused/archived) | Workspace switcher rows, dashboard |
| `ConfidencePill` | 1–5 scale with color from `--confidence-*` | Cards, articles |
| `SourceTierIndicator` | 1–5 scale, terse | Cards, articles |
| `ConnectionTypeIcon` | Icon + color per connection type (9 types) | Knowledge graph side panel, card detail |

### 5.4 State components

| Component | Role | Used in |
|---|---|---|
| `EmptyState` | Friendly empty render with illustration + suggested action | Any list view with no data |
| `LoadingState` | Skeleton or spinner | While fetching |
| `ErrorState` | Failure render with retry | When fetch fails or data fails to parse |

### 5.5 Page-level components

These live in `views/src/src/pages/` (per scaffold spec) but their visual contract is defined here:

| Page | Composes | Density |
|---|---|---|
| `Landing` (`/`) | WorkspaceSwitcher (inline grid) + StatusCard×N + Articles strip | Spacious |
| `Articles` (`/articles`) | Filter bar + Table OR ArticleCard grid | Compact (table) / Spacious (grid) — pick in Epic 8 |
| `ArticleDetail` (`/articles/:slug`) | MarkdownRenderer + Provenance trace (source cards expanded) | Spacious |
| `WorkspaceDashboard` (`/:workspace/`) | MetricTile grid + Chart×N + recent activity list | Spacious |
| `KnowledgeGraph` (`/:workspace/knowledge-graph`) | `react-force-graph` canvas + side filter panel + click-to-detail panel | Spacious (full-bleed canvas) |
| `Landscape` (`/:workspace/landscape`) | Heatmap + Tag cloud + per-category panels | Spacious |
| `Artifacts` (`/:workspace/artifacts`) | Filter sidebar + Table + click-to-detail panel | Compact (table) |
| `Digests` (`/:workspace/digests`) | Date-grouped list + filters | Compact |
| `DigestDetail` (`/:workspace/digests/:id`) | MarkdownRenderer + candidates table + clusters table | Spacious for prose, compact for tables |
| `NotFound` | Friendly 404 + "back to landing" link | n/a |

---

## 6. Density Baselines

Two density modes, both expressed in Tailwind utility classes. A `density="compact"` or `density="spacious"` prop on relevant components selects which.

### 6.1 Spacious

| Property | Value |
|---|---|
| Section vertical rhythm | `space-y-8` to `space-y-12` |
| Section horizontal padding | `px-6` to `px-10` |
| Card internal padding | `p-6` |
| Header sizes | Syne 700, `text-2xl`–`text-4xl` |
| Body line-height | `leading-relaxed` (1.625) |
| Color contrast | Higher (text-primary on dark base) |

Used in: dashboards, detail pages, articles, digest details.

### 6.2 Compact

| Property | Value |
|---|---|
| Row height (table) | 36–40px |
| Row internal padding | `px-3 py-2` |
| Body line-height | `leading-tight` (1.25) |
| Header sizes | Manrope 600, `text-xs` uppercase |
| Color contrast | Mixed (primary cell text, secondary metadata) |
| Tag weight | `text-[10px]` for table-cell tags |

Used in: artifacts list, digests list, side panels with many entries.

---

## 7. Responsive + Accessibility Baselines

### 7.1 Responsive

| Breakpoint | Tailwind | Layout behavior |
|---|---|---|
| ≥1280px (desktop) | `xl` | Primary target; all features full quality |
| 1024–1279px (small desktop) | `lg` | All features; header may compress global-links text |
| 768–1023px (tablet) | `md` | Acceptable; bottom-row nav may scroll horizontally; graph canvas reduced |
| <768px (mobile) | — | **Out of scope for v0.2.** Page renders ungracefully; not a bug. Documented in `prd-v02-live-views.md` patches (Epic 11) |

Responsive implementation: Tailwind utility variants (`md:`, `lg:`, `xl:`). No JS breakpoint hooks.

### 7.2 Accessibility

| Concern | v0.2 commitment |
|---|---|
| Keyboard navigation | Tab order through interactive elements; Enter/Space activate. Workspace switcher dropdown opens on click only (no arrow keys — see §4.5 trade-off) |
| Visible focus | `focus:ring-2 focus:ring-cyan-400/50 focus:outline-none` on all interactive elements |
| Contrast | WCAG AA minimum (4.5:1 for body text on `--bg-base`). Verified in §11 |
| Reduced motion | `@media (prefers-reduced-motion: reduce)` disables any animation we add. Currently the only animations are removed (rings); fonts remain |
| ARIA | Minimal. Buttons are `<button>`, links are `<a>`. No live regions in v0.2 (UPDATE flag is a button, accessible label "Update available; reload page") |
| Screen readers | Page titles set per route via `<title>` (handled in App.jsx via a small effect). Sufficient for v0.2 |

Anything beyond this baseline is deferred to v0.3.

---

## 8. Static Design Prototype

### 8.1 Where it lives

The static prototype IS the page stubs in `views/src/src/pages/*.jsx`, populated with **hardcoded mock data** during Epic 4. Epic 8 implementation swaps mock data for real fetches against `views/build/data/`.

This means the Epic 4 deliverable is itself runnable: `npm run dev` shows every route fully designed against fake data. No separate prototype project to maintain.

### 8.2 Mock data

Each page imports a `mock` constant (or a small JSON file in `views/src/src/_mock/`) shaped to match the data-model spec. For example, `Landing.jsx` imports a mock `domains.json` shape; `WorkspaceDashboard.jsx` imports a mock per-workspace `cards.json` + `stats.json`.

The mock files are **not** part of `views/build/data/` (which is canonical-derived). They live in the source tree and are tree-shaken / replaced when Epic 8 wires real fetches. Mark them with a comment block stating their lifetime ends at Epic 8 completion.

### 8.3 What the prototype demonstrates

- Each route in **populated state** (mock data)
- Each route in **empty state** (a `?empty=1` query param toggle, or a separate `/__empty/` mirror — TBD)
- Spacious vs. compact density visible on the right pages
- The `UPDATE` flag rendered in both fresh and stale state (toggle via dev mock — it's a useState locally for now)
- Workspace switcher with 2–3 mock workspaces
- All component inventory items rendered in at least one place

### 8.4 What Epic 8 inherits

Epic 8 takes each page's prototype and:
- Replaces `import mock from '../_mock/X.json'` with `useFetch('/data/X.json')` (or whatever Epic 5 hook design produces)
- Removes the local `useState`-based UPDATE flag toggle, wires `useVersionFlag()` from Epic 5
- Adds `LoadingState` and `ErrorState` rendering paths

Epic 8 spec will define the per-view fetch logic, filtering rules, and detail interactions. This spec hands off the visual contract intact.

---

## 9. What This Spec Does NOT Include

- Per-view filtering rules and side-panel detail content (Epic 8)
- Real data fetching, polling worker, hooks (Epic 5 / Epic 8)
- D3 / `react-force-graph` rendering details for Knowledge Graph (Epic 8)
- Recharts series choices for dashboard (Epic 8)
- Internationalization (deferred — v0.2 is English only)
- Print stylesheets (out of scope)
- Dark-mode-only confirmation: there is no light mode; dark is the only theme

---

## 10. Acceptance Checks

This spec is implemented when:

- [ ] `views/src/src/index.css` declares all CSS custom properties from §3.1 on `:root`
- [ ] Tailwind config registers `font-display: Syne` and `font-body: Manrope`
- [ ] Google Fonts link injected by Layout's `useEffect` loads both fonts
- [ ] `<CosmicBG/>` renders 3 layers (gradients + vignette + stars) consuming CSS vars; **no rotating rings**
- [ ] Layout sets `data-workspace={workspaceId || 'default'}` on its outer wrapper (for future theming)
- [ ] Header is sticky, glass-morphism dark
- [ ] Top row is always rendered; bottom row renders only when `useParams().workspace` is set
- [ ] Workspace switcher pill is right-aligned in top row, opens dropdown on click
- [ ] `UPDATE` flag pill is left of workspace switcher, has fresh + stale visual states
- [ ] All 11 page-level components from §5.5 exist with hardcoded mock data
- [ ] All components from §5.1–5.4 exist and are exported
- [ ] Every interactive element has a visible focus ring
- [ ] Body text on `--bg-base` measures ≥4.5:1 contrast (verify with a tool — manual Lighthouse pass acceptable)
- [ ] No "OpenClaw" string appears anywhere in the SPA
- [ ] At desktop (≥1280px) every page renders without horizontal scroll
- [ ] At tablet (768–1023px) every page renders gracefully (some compromises acceptable)

---

## 11. Open Follow-ups

1. **`UPDATE` flag fresh state.** Should the pill be **invisible** when fresh or show a low-opacity "Up to date" label? Invisible is cleaner; "Up to date" is more reassuring. Recommendation: **invisible** for less header noise. Final decision in Epic 8 implementation.
2. **Mock data location.** §8.2 says `_mock/` under `views/src/src/`. Confirm that prefix convention (underscore = "internal, removed before Epic 8 ships") works for you, or pick another (e.g., `__mock__/`).
3. **Empty-state rendering trigger.** Production behavior: Epic 5 produces `cards.json: []`, SPA detects empty, renders `<EmptyState/>`. For prototype, do we use `?empty=1` query param to toggle, or `/__empty/` mirrored routes, or a Storybook-like hub? Recommendation: skip the toggle for prototype; show populated state only, and Epic 8 implements empty paths against real data conditions.
4. **Per-workspace theme variant file.** Empty CSS file at `views/src/src/themes/per-workspace.css` shipped in Epic 4? Or omit entirely until v0.2.1? Recommendation: **omit** — leave the substrate in `index.css` only; the variant file appears with the v0.2.1 feature.
5. **Page title strategy.** Should each page set `document.title` via `useEffect`, or use a wrapper component (e.g., `<PageTitle>`)? Recommendation: small `usePageTitle()` hook in Epic 8.
6. **Brand inflection.** `MABSTRUCT / CONSTRUCT` stack in design-example reads brand-first. For an internal tool, consider inverting: `CONSTRUCT / MABSTRUCT` (where MABSTRUCT is your studio mark, smaller). Lean: keep design-example's order; revisit if it bothers in real use.

---

## 12. Forward Hooks (v0.2.1 and beyond)

Substrate items in v0.2 that unlock future features without rework:

| Future feature | What v0.2 already has | What v0.2.1+ adds |
|---|---|---|
| Per-workspace cosmic theme | CSS vars + `data-workspace` attribute on Layout | `themes/per-workspace.css` with overrides; theme tokens in `domains.yaml` → `domains.json` |
| Cross-workspace bridges panel on landing | (none — explicit deferral) | New `bridges.json` global + `<Bridges>` component |
| Cross-workspace activity feed | (none — explicit deferral) | New global `events.json` + activity timeline component |
| Live-reload (filesystem watcher) | (none — explicit deferral) | WebSocket layer; replaces polling |
| Per-page edit-in-browser | Not architecturally compatible (architecture-overview I2) | Would route through Claude → skill → workspace; SPA stays read-only |

---

## 13. References

- `prd-v02-live-views.md` §4.7 (overview & navigation), §7 (tech stack)
- `spec-v02-runtime-topology.md` §5 (routing), §4 (UPDATE flag mechanism), §6 (landing dashboard MVP content)
- `spec-v02-data-model.md` §3 (file layout), §5.1 (`domains.json`), §5.5 (`articles.json`)
- `spec-v02-scaffold.md` — toolchain that hosts everything in this spec
- `architecture-overview.md` §3 (three layers), §4 (invariants), §6 (topology variants)
- `views/design-example/src/components/Layout.jsx` — visual reference; lift theme primitives + atmosphere; replace nav (single-workspace assumption + extraneous routes); rewrite footer (OpenClaw removed)
- `views/design-example/src/pages/*.jsx` — visual reference for page composition; do NOT copy wholesale (route names changed, content was domain-specific)
- `references/epistemic-types.md`, `connection-types.md`, `lifecycle-states.md`, `confidence-levels.md`, `source-tiers.md` — vocabulary the components display
- `CONSTRUCT-CLAUDE-impl/VERSION` — version baked into footer
