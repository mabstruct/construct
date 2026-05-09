# spec-v02-cross-domain-graph — Cross-Domain Graph Mode

**Status:** Draft
**Date:** 2026-05-09
**Companion PRD:** `prd-v02-cross-domain-cluster.md`
**Companion data spec:** `spec-v02-cross-domain-data.md`
**Companion view spec:** `spec-v02-cross-domain-views.md`

This spec defines the first binding contract for the **cross-domain graph**.

It extends the existing single-workspace knowledge graph contract in `spec-v02-views.md` §4.5 without replacing it.

---

## 1. Summary

The current graph route is single-workspace only:

- `/:workspace/knowledge-graph`

The cross-domain wave adds a second graph surface:

- `/cross-domain/graph`

This new route provides a **global, multi-domain graph mode** for bridge-centric exploration.

The first cut is intentionally constrained:

- default mode is **bridges-first**, not all-nodes-everywhere
- user can inspect only `2` or `3` domains at a time
- the graph is **read-only**
- node drill-down still resolves to the existing per-workspace artifact/card surfaces

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Existing KG route | Preserve `/:workspace/knowledge-graph` exactly |
| New graph surface | Add `/cross-domain/graph` as a separate global route |
| Default graph scope | Bridges-first subset |
| Domain count | Support 2–3 domains in first cut |
| Selection model | Route state via query params |
| Rendering bias | Prioritize interpretability over maximum graph completeness |
| Node drill-down | Open existing per-workspace artifact/detail surfaces |
| Write actions | None; read-only |
| Future all-install graph | Deferred behind an explicit mode toggle |

---

## 3. Route Contract

### 3.1 New Route

Add one new route:

```text
/cross-domain/graph
```

This is a global route.

### 3.2 URL State

The route uses query params:

```text
/cross-domain/graph?domains=cosmology,philosophy-of-mind
/cross-domain/graph?domains=cosmology,philosophy-of-mind,philosophy-of-physics&bridge=cosmology__philosophy-of-mind__observer-models
/cross-domain/graph?domains=cosmology,philosophy-of-mind&mode=all
```

Rules:

- `domains` is required for a populated graph state
- `domains` supports `2` or `3` domains only in first cut
- `bridge` is optional and preselects/highlights one bridge cluster
- `mode` defaults to `bridges`
- `mode=all` is explicitly secondary and hidden behind a user action

Allowed modes:

- `bridges`
- `all`

---

## 4. Data Inputs

Required inputs:

- `/data/bridges.json`
- `/data/domains.json`
- `/data/<workspace>/cards.json`
- `/data/<workspace>/connections.json`

The graph route should only fetch per-workspace card/connection payloads for the selected domain set.

### 4.1 Bridges-First Data Slice

For `mode=bridges`, the rendered graph contains:

- cards referenced by confirmed bridges in the selected domains
- cards referenced by strong bridge candidates in the selected domains
- one-hop local neighbors needed to make those bridges intelligible

This means the graph is a **curated subgraph**, not the full union of all cards.

### 4.2 All Mode Data Slice

For `mode=all`, the rendered graph contains:

- full card sets for the selected domains
- all intra-domain connections for those domains
- all cross-domain bridge edges available from `bridges.json`

This mode exists, but it is not the default and should carry a density warning when large.

---

## 5. Purpose

The cross-domain graph should let the user answer:

- where are the strongest bridge clusters across domains?
- which cards act as conceptual connectors across domains?
- are these bridges isolated parallels, or embedded in larger local structures?

It should not attempt to be:

- a complete global install map by default,
- a write/apply interface,
- a replacement for the per-workspace graph.

---

## 6. Composition

### 6.1 Layout

```text
┌─────────────────────────────────────────────────────────────────┐
│  Cross-Domain Graph                                             │
│  Explore bridge-centric graph structure across domains          │
│  [domain selector] [mode: bridges/all] [filters]               │
├───────────────────────────────────────────────┬─────────────────┤
│                                               │ Selected detail │
│                                               │ ─────────────── │
│        [react-force-graph canvas]            │ card / bridge   │
│                                               │ evidence        │
│                                               │ source/target   │
│                                               │ local neighbors │
├───────────────────────────────────────────────┴─────────────────┤
│  Legend: domains, epistemic types, bridge status               │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Major UI Regions

1. toolbar
2. graph canvas
3. detail panel
4. legend

---

## 7. Toolbar Contract

The toolbar must include:

- domain selector (`2` or `3` domains)
- mode toggle: `Bridges` / `All`
- bridge-status filter:
  - confirmed
  - strong
- node filters:
  - epistemic type
  - lifecycle
- clear/reset action

The toolbar should not include advanced layout tuning in the first cut.

---

## 8. Graph Semantics

### 8.1 Node Semantics

Each node is still a card.

Minimum node fields needed in runtime state:

- `id`
- `workspace`
- `title`
- `epistemic_type`
- `lifecycle`
- `confidence`
- `isBridgeEndpoint` boolean

### 8.2 Edge Semantics

There are two edge families:

1. **Intra-domain edges**
   - sourced from existing `connections.json`
   - same semantics as the single-workspace KG
2. **Cross-domain bridge edges**
   - sourced from `bridges.json`
   - status = `confirmed` or `strong`
   - detection provenance preserved for the detail panel

### 8.3 Default Visibility

In `mode=bridges`:

- bridge edges are prominent
- intra-domain context edges are present but visually secondary
- non-bridge nodes outside the selected subgraph are omitted

In `mode=all`:

- all selected-domain nodes render
- cross-domain bridge edges remain visually distinct

---

## 9. Visual Encoding

This spec deliberately reuses the existing KG visual language where possible.

### 9.1 Node Encoding

- base color = epistemic type
- outer ring or badge color = workspace/domain identity
- bridge endpoints get an extra visual marker

### 9.2 Edge Encoding

- intra-domain edges keep the existing connection-type color rules
- cross-domain bridge edges use a distinct overlay treatment:
  - `confirmed` = solid and high-contrast
  - `strong` = dashed or lighter but still prominent

### 9.3 Domain Boundaries

Domain membership must be legible without requiring hover.

Acceptable first-cut encodings:

- domain-colored node halos
- domain-colored chips in side panel and legend
- optional soft cluster hulls if easy, but not required

### 9.4 Layout Goal

The layout should naturally separate domains while keeping bridge endpoints close enough to see cross-domain structure.

Interpretation target:

- local clusters remain visible
- bridge paths are legible
- the graph does not collapse into one undifferentiated mass

---

## 10. Detail Panel

### 10.1 Node Selection

Clicking a node opens card detail similar to the existing per-workspace KG panel, with added domain context:

- title
- workspace/domain
- type / confidence / lifecycle
- excerpt
- local connections
- cross-domain bridge membership, if any

### 10.2 Bridge Selection

If the selected item is a bridge edge or bridge candidate:

- show source card + target card
- show relation label
- show status (`confirmed` / `strong`)
- show score
- show detection signals / provenance
- show actions to open source/target cards

### 10.3 Actions

Provide:

- `Open source card`
- `Open target card`
- `Open comparison`

`Open comparison` routes to:

```text
/cross-domain?domains=<a>,<b>[,<c>]&bridge=<bridge-id>
```

---

## 11. Interactions

Required interactions:

- click node → open node detail panel
- click bridge edge or bridge row if represented in panel → open bridge detail
- hover node → title tooltip
- drag node → reposition during session
- zoom/pan → standard KG behavior
- click empty space → clear selection

Optional for first cut:

- fit-to-selection
- isolate selected bridge cluster

---

## 12. Empty / Loading / Error States

### 12.1 No Domains Selected

Render:

```text
Select 2 or 3 domains to explore cross-domain structure.
Start from the strongest pair on the landing page or choose domains here.
```

### 12.2 No Bridges In Selection

In `mode=bridges`, render:

```text
No confirmed or strong bridge candidates for this selection.
Try another domain set or switch to All mode.
```

### 12.3 Large Graph Warning

In `mode=all`, if the selected-domain union is above the current interactive budget, render a warning above the canvas:

```text
This graph is dense. Switch back to Bridges mode or narrow the domain set for a clearer view.
```

### 12.4 Loading

- toolbar skeleton
- static graph placeholder
- detail panel skeleton

### 12.5 Error

Use the standard `<ErrorState />` pattern.

---

## 13. Navigation Contract

### 13.1 Entry Points

The graph is discoverable from:

- the landing Cross-Domain card
- the `/cross-domain` comparison route

The comparison route should expose `Open global graph` / `Open graph` actions that preserve current domain and bridge selection.

### 13.2 No Permanent Global Nav Item Yet

Do not add a dedicated persistent top-nav item in first cut.

Reason: discovery is adequate via the new landing card and comparison route, and the cross-domain surface area is still stabilizing.

---

## 14. Relationship to Existing KG

The existing route remains the best tool for domain-internal analysis:

- `/:workspace/knowledge-graph`

The new route is for domain-spanning analysis:

- `/cross-domain/graph`

This separation is deliberate.

It avoids overloading the current KG route with global behavior and keeps bookmarks, existing user expectations, and per-workspace debug workflows stable.

---

## 15. Validation Checklist

- [ ] `/:workspace/knowledge-graph` remains unchanged in contract
- [ ] `/cross-domain/graph` supports `2` and `3` selected domains
- [ ] default route behavior is bridges-first
- [ ] `mode=all` exists but is secondary
- [ ] cross-domain bridge edges are visually distinct from intra-domain edges
- [ ] clicking a node deep-links cleanly back to the relevant per-workspace surface
- [ ] clicking `Open comparison` preserves selected domains/bridge
- [ ] empty states are explicit for no-selection and no-bridge cases

---

## 16. Open Follow-ups

1. Should the graph support bridge-cluster presets such as `top score`, `confirmed only`, or `recently detected`?
2. Should cross-domain graph selection be shareable via a richer encoded state later?
3. Should domain boundaries eventually use hulls/regions instead of halos only?
4. Does `mode=all` need client-side sampling/pruning if larger installs exceed the current budget?
