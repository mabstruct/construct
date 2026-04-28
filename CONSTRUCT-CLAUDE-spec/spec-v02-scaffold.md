# spec-v02-scaffold — Views SPA Scaffold

**Status:** Accepted
**Date:** 2026-04-28
**Accepted:** 2026-04-28 (verified via implementation: template at `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/`; `npm install` + `npm run build` + `serve --single` all pass on the staged template; `emptyOutDir: false` invariant verified by surviving rebuild with dummy `data/` and `version.json` present)
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 3
**Related:** `prd-v02-live-views.md` §3, §5.4 · `spec-v02-runtime-topology.md` · `spec-v02-data-model.md` · `architecture-overview.md` · `adrs/adr-0002-v02-packaging.md`

---

## 1. Scope

This spec defines the **toolchain, directory layout, dependency list, and route shell** for the views SPA. It is the foundation that Epic 4 (Design Prototype) styles, Epic 5 (Data Generation) feeds, Epic 6 (Build Pipeline) packages, and Epic 8 (Per-View Implementation) fills with content.

**Out of scope** (deferred to other epics):

- Visual identity, theme tokens, glass-morphism styling → Epic 4
- Component implementations (Layout, Header, etc.) → Epic 4
- Page implementations (Dashboard, KnowledgeGraph, etc.) → Epic 8
- Data-fetching logic and hooks → Epic 5/8
- `views-scaffold` and `views-build` SKILL.md drafts → Epic 6

This spec produces a **bare-but-runnable** scaffold: a default Vite + React + Tailwind app that boots, routes, and serves but renders mostly empty pages.

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Language | JavaScript with JSX. No TypeScript in v0.2. |
| Framework | React 19.x |
| Build tool | Vite 7.x (Vite 8 was tried and rejected — `@vitejs/plugin-react` peers Vite 4–7; bumping to plugin-react v5+ to chase Vite 8 is deferred) |
| Styling | Tailwind CSS 4.x via `@tailwindcss/vite` plugin (no separate `postcss.config.js`) |
| Component approach | Hand-built with Tailwind utility classes. No shadcn, Radix, or Mantine deps. |
| Routing | `react-router-dom` 7.x with `BrowserRouter` (matches `serve --single` history fallback) |
| Markdown rendering | `react-markdown` |
| Charts | `recharts` |
| Icons | `lucide-react` |
| Knowledge graph | `react-force-graph` (React wrapper around `d3-force`); `d3` available transitively for fine-grained customization |
| HTTP server | `serve` (npm package), dev dependency, invoked via `npm run serve` per topology spec |
| Dev server | `npm run dev` included (Vite's built-in dev server with HMR) |
| Project root | `views/src/` is the Vite project root (`package.json`, `vite.config.js`, `index.html` live here) |
| Build output | `views/build/` (Vite's `outDir` configured to `../build`) |
| Build cleanup behaviour | `emptyOutDir: false` — Vite must NOT clean `views/build/` because `data/` and `version.json` are owned by `views-generate-data` |
| Node version | Pin via `.nvmrc` at Node 20 (Vite 7 minimum is Node 18, Node 20 is current LTS) |
| Visual identity inheritance | None at this stage. Epic 4 audits `views/design-example/` and lifts what's keepable. Epic 3 ships a default-Tailwind look. |
| `views/design-example/` fate | Stays at current path. May be removed in a later milestone (v0.3+) once Epic 4 has extracted what's worth keeping. |

---

## 3. Directory Layout

After `views-scaffold` runs (one-time):

```
views/
├── design-example/             ← untouched (visual reference, may be removed later)
│
├── src/                        ← VITE PROJECT ROOT (views-scaffold creates this)
│   ├── package.json
│   ├── package-lock.json       (committed)
│   ├── vite.config.js
│   ├── jsconfig.json           (path aliases for editor support)
│   ├── .nvmrc                  (Node 20)
│   ├── .gitignore              (node_modules, .vite cache)
│   ├── index.html              (Vite entry)
│   ├── public/                 (static assets copied verbatim to build root)
│   │
│   └── src/                    (JSX source; nested `src/` per Vite convention)
│       ├── main.jsx            (React entry — mounts <App/> to #root)
│       ├── App.jsx             (top-level layout shell + <BrowserRouter>)
│       ├── routes.jsx          (single source of route definitions)
│       ├── index.css           (Tailwind directives + minimal global CSS)
│       │
│       ├── components/         ← Epic 4 fills (Layout, Header, MetricTile, ...)
│       ├── pages/              ← Epic 8 fills (Landing, WorkspaceDashboard, ...)
│       ├── hooks/              (data-fetching + version-polling hooks)
│       └── lib/                (small utility modules)
│
└── build/                      ← VITE OUTPUT (created by views-build)
    ├── index.html              ← from Vite
    ├── assets/                 ← from Vite (chunked JS, CSS, fonts)
    ├── data/                   ← from views-generate-data (NEVER touched by Vite)
    ├── version.json            ← from views-generate-data
    └── server.pid              ← from construct-up
```

### 3.1 Why `views/src/` as Vite project root (not `views/`)

The PRD framing keeps the three peer concerns visible at the `views/` level: `design-example/` (reference), `src/` (our app), `build/` (output). Putting Vite's project root one level deeper preserves that clarity and matches `design-example/`'s own structure (which has its `package.json` at `views/design-example/src/`).

### 3.2 Why nested `src/src/`

Vite's convention places source code under a `src/` subdirectory inside the project root. Combined with our outer `views/src/` (which IS the project root), the source files end up at `views/src/src/`. Slightly unusual but consistent with Vite's expectations.

### 3.3 Two writers to `views/build/`, never overlapping

Per `architecture-overview.md` §3.2 and the four invariants:

- `views-build` writes `views/build/{index.html, assets/}`
- `views-generate-data` writes `views/build/{data/*, version.json}`
- `construct-up` writes `views/server.pid` (note: NOT under `build/` — at `views/server.pid` per topology spec §7.3)

These three writers never touch the same paths. Vite's `emptyOutDir: false` is what makes this safe — without it, every `npm run build` would wipe `data/` and `version.json`.

---

## 4. Dependency List

### 4.1 Runtime dependencies (`package.json` `"dependencies"`)

```jsonc
{
  "react": "^19.0.0",
  "react-dom": "^19.0.0",
  "react-router-dom": "^7.0.0",
  "react-markdown": "^9.0.0",
  "recharts": "^2.12.0",
  "lucide-react": "^0.400.0",
  "react-force-graph": "^1.45.0",
  "d3": "^7.9.0"
}
```

### 4.2 Dev dependencies (`package.json` `"devDependencies"`)

```jsonc
{
  "vite": "^7.0.0",
  "@vitejs/plugin-react": "^4.3.0",
  "tailwindcss": "^4.0.0",
  "@tailwindcss/vite": "^4.0.0",
  "serve": "^14.2.0"
}
```

### 4.3 Locked-out dependencies

- ❌ TypeScript and `@types/*` packages (Q1 decision: JS only)
- ❌ shadcn/ui, Radix UI, Headless UI, Mantine, Chakra (Q2 decision: hand-built Tailwind)
- ❌ Test frameworks (Vitest, Jest) — deferred. v0.2 validation is fixture-based per Epic 10
- ❌ ESLint / Prettier — defer to Epic 11 (docs/migration) if it's worth it; not blocking MVP
- ❌ Storybook — overkill for v0.2; design prototype lives as a static page (Epic 4)

Adding anything from this list is a **deviation** that requires updating this spec.

### 4.4 Notes on specific picks

- **`d3`** is listed explicitly because `react-force-graph` re-exports many d3 utilities and depending on it directly is cleaner than relying on transitive resolution. Lets the knowledge-graph view drop into raw d3 for fine-grained tweaks.
- **`react-markdown` 9.x** — current major. Version-pin to avoid markdown-it migrations.
- **`recharts`** matches design-example's pick; widely supported; renders as SVG (theme-friendly).
- **`lucide-react`** — design-example uses this; lightweight; tree-shakable.
- **`@tailwindcss/vite`** — Tailwind 4's Vite plugin replaces the legacy `postcss + tailwindcss` setup. No `postcss.config.js` needed.

---

## 5. `package.json` scripts

```jsonc
{
  "name": "construct-views",
  "private": true,
  "version": "0.2.0-dev",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "serve": "serve ../build --single",
    "preview": "vite preview"
  }
}
```

### 5.1 Why `serve --single` and not the port flag

Port is passed by `construct-up` at runtime (topology spec §7.1, port range 3001–3009). The script stays portable; `construct-up` invokes:

```
cd views/src && npm run serve -- -l <chosen-port>
```

`npm run serve -- -l 3001` forwards `-l 3001` to `serve`. This way the script works on any port without per-instance config.

### 5.2 Why include `preview`

Vite's `preview` command serves the build output for sanity-checking after `vite build`. It's not the production path (that's `npm run serve`) but useful during scaffold/build debugging. Zero cost — it's part of Vite already.

### 5.3 What's NOT a script

- ❌ `start` — overloaded term; `dev` and `serve` are unambiguous
- ❌ `test` — no test framework in v0.2
- ❌ `lint` / `format` — no ESLint/Prettier in v0.2

---

## 6. `vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: '../build',
    emptyOutDir: false      // CRITICAL — see §3.3
  },
  server: {
    port: 5173,             // dev server port (separate from production serve)
    open: false
  }
})
```

The `emptyOutDir: false` is **load-bearing** for the two-writer invariant. Removing it breaks the safe-delete invariant (I3) for the wrong reason — `views-build` would silently wipe `data/`, and the next page reload would show empty workspace data.

---

## 7. Tailwind 4 Setup

Tailwind 4 supports configuration via CSS `@theme` directive. For Epic 3, ship a **minimal default** — Epic 4 owns the actual theme tokens.

`views/src/src/index.css`:

```css
@import "tailwindcss";

/* Epic 4 will populate this with theme tokens */
@theme {
  /* placeholder; Epic 4 fills with colors, fonts, spacing */
}

/* Minimal global resets (kept tiny on purpose) */
:root {
  color-scheme: dark;
}

body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #0a0a0a;
  color: #e5e5e5;
}
```

A bare dark background + system font stops the scaffold from looking actively broken before Epic 4 lands. It does NOT pre-empt the design-prototype's visual decisions.

---

## 8. Route Shell

`views/src/src/routes.jsx` is the single source of route definitions, mirroring `spec-v02-runtime-topology.md` §5.

```jsx
import { Routes, Route } from 'react-router-dom'

// Page imports — Epic 8 implements these. Epic 3 ships placeholders.
import Landing from './pages/Landing'
import Articles from './pages/Articles'
import ArticleDetail from './pages/ArticleDetail'
import WorkspaceDashboard from './pages/WorkspaceDashboard'
import KnowledgeGraph from './pages/KnowledgeGraph'
import Landscape from './pages/Landscape'
import Artifacts from './pages/Artifacts'
import Digests from './pages/Digests'
import DigestDetail from './pages/DigestDetail'
import NotFound from './pages/NotFound'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/articles" element={<Articles />} />
      <Route path="/articles/:slug" element={<ArticleDetail />} />
      <Route path="/:workspace" element={<WorkspaceDashboard />} />
      <Route path="/:workspace/knowledge-graph" element={<KnowledgeGraph />} />
      <Route path="/:workspace/landscape" element={<Landscape />} />
      <Route path="/:workspace/artifacts" element={<Artifacts />} />
      <Route path="/:workspace/digests" element={<Digests />} />
      <Route path="/:workspace/digests/:id" element={<DigestDetail />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
```

`App.jsx` wraps this in a `<BrowserRouter>` and the eventual layout shell:

```jsx
import { BrowserRouter } from 'react-router-dom'
import AppRoutes from './routes'
// import Layout from './components/Layout'   // Epic 4

export default function App() {
  return (
    <BrowserRouter>
      {/* Epic 4 will wrap AppRoutes in <Layout> */}
      <AppRoutes />
    </BrowserRouter>
  )
}
```

### 8.1 Page placeholders for Epic 3

Each page file (`pages/*.jsx`) ships as a one-line stub:

```jsx
// e.g., pages/Landing.jsx
export default function Landing() {
  return <div>Landing — Epic 8 implements this</div>
}
```

This makes the route shell runnable end-to-end before Epic 8 starts. Click a workspace switcher link (once Epic 4 ships one) → land on the placeholder. Typing `/cosmology/digests` directly → land on the placeholder. `serve --single`'s history fallback ensures these direct loads work.

---

## 9. `index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CONSTRUCT</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

Bare on purpose. Epic 4 may add favicon, meta tags, OG image, etc.

---

## 10. What This Scaffold Does NOT Include

- No theme tokens beyond a dark background (Epic 4)
- No Layout/Header components (Epic 4)
- No data fetching, hooks, or `version.json` polling worker (Epic 5/8)
- No `UPDATE` flag UI (Epic 4 + Epic 8)
- No real page content (Epic 8)
- No tests (deferred)
- No Storybook (rejected as overkill)

It is intentionally minimal. The scaffold's job is to **boot, route, and survive `serve --single` reloads**. Visual polish is Epic 4. Data wiring is Epic 5+.

---

## 11. Acceptance Checks

This spec is implemented when:

- [ ] `cd views/src && npm install` completes without warnings
- [ ] `npm run dev` starts Vite dev server on port 5173 and serves a dark-background page with a `<div>` for each placeholder route
- [ ] `npm run build` writes `index.html` + `assets/` to `views/build/` (not `views/src/build/`)
- [ ] `npm run build` does NOT delete `views/build/data/` or `views/build/version.json` if they exist (proves `emptyOutDir: false` is honoured)
- [ ] `cd views/src && npm run serve -- -l 3001` serves the build on port 3001
- [ ] Reloading at `/cosmology/digests` returns the page (proves `serve --single` history fallback)
- [ ] All ten routes (Landing through NotFound) render their placeholder content
- [ ] `package.json` `"dependencies"` matches §4.1 exactly (no extras)
- [ ] `package.json` `"devDependencies"` matches §4.2 exactly
- [ ] `vite.config.js` declares `emptyOutDir: false`

---

## 12. Open Follow-ups

1. **Tailwind theme location.** §7 places the placeholder `@theme` block in `index.css`. Epic 4 may decide to split tokens into a separate `theme.css` or use `tailwind.config.js`. Either is fine — don't pre-decide here.
2. **Path aliases.** `jsconfig.json` lets editors resolve `@/components/...` style imports. Whether to enable this is an Epic 4/8 ergonomics question. For Epic 3, `jsconfig.json` is shipped with `compilerOptions.baseUrl: "src"` but no aliases — covers basic editor IntelliSense without committing to a pattern.
3. **Public folder contents.** `views/src/public/` is empty for Epic 3. Epic 4 may add favicon, OG image, robots.txt.
4. **`react-force-graph` 2D vs 3D.** The package ships multiple variants (`react-force-graph-2d`, `-3d`, `-vr`). Epic 8 (Knowledge Graph view) picks one. For Epic 3, listing the umbrella `react-force-graph` is enough.
5. **Build determinism.** Vite produces hashed asset filenames (`main-a3f81c.js`). For the `version.json` / `build_id` mechanism to work, the **data files** are what hash deterministically — the SPA bundle hash is independent and changes only when source changes. Worth flagging here so it's clear in Epic 5 implementation.

---

## 13. References

- `prd-v02-live-views.md` §3 (architecture), §5.4 (`views-scaffold` skill), §7 (tech stack)
- `spec-v02-runtime-topology.md` §3 (`construct-up`), §5 (routing), §7 (port allocation)
- `spec-v02-data-model.md` §3 (file layout — what `views-generate-data` writes into `views/build/data/`)
- `architecture-overview.md` §3 (three layers), §4 (invariants), §7 (component locations)
- `views/design-example/` — visual reference (read-only); Epic 4 audits and lifts what's keepable
