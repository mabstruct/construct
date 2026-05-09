# spec-v02-cross-domain-views — Cross-Domain Card and Comparison Route

**Status:** Draft
**Date:** 2026-05-09
**Companion PRD:** `prd-v02-cross-domain-cluster.md`
**Companion data spec:** `spec-v02-cross-domain-data.md`
**Companion graph spec:** `spec-v02-cross-domain-graph.md`

This spec defines the first binding UI contract for the cross-domain feature cluster:

1. the **Cross-Domain** card on the landing dashboard,
2. the **Cross-Domain comparison route** and its interactions.

This spec does **not** define the global cross-domain graph mode. That remains a follow-on spec. References to the future graph mode here are only to preserve drill-down continuity.

---

## 1. Summary

The first visible cross-domain feature wave adds one new landing surface and one new route:

- a **Cross-Domain** card on `/`
- a **Cross-Domain comparison** page at `/cross-domain`

The landing card gives the user a compact answer to:

- where are the strongest bridge candidates right now?

The comparison route gives the user a structured answer to:

- what do these domains have in common,
- where are the meaningful bridges,
- where is there overlap without confirmed connection?

This first cut is **read-only**. It helps the user inspect and interpret cross-domain structure, then hand off to Claude/skills for any confirm-or-apply action.

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Landing change | Add one **Cross-Domain** card alongside existing per-domain dashboard cards |
| Landing emphasis | Top bridge candidates |
| Visibility rule | Show confirmed bridges + strong candidates only |
| Comparison focus | Balanced dashboard |
| Drill-down target | Clicking a bridge candidate opens the cross-domain comparison route |
| Comparison granularity | Support 2–3 domains in first cut |
| Apply flow | Read-only |
| Per-domain cards | Keep mostly unchanged; at most a minor cross-domain signal later |
| Activity feed | Not part of this wave |
| Terminology | User-facing label is **Cross-Domain** |

---

## 3. Route Additions

### 3.1 New Route

Add one new global route:

```text
/cross-domain
```

This route is a global route like `/` and `/articles`.

### 3.2 URL State

The route uses query params to preserve comparison state:

```text
/cross-domain?domains=cosmology,philosophy-of-mind
/cross-domain?domains=cosmology,philosophy-of-mind,climate-policy&bridge=cosmology__philosophy-of-mind__observer-models
```

Rules:

- `domains` is required for a populated comparison state
- first cut supports `2` or `3` domains only
- `bridge` is optional; if present, the page preselects/highlights that bridge entry

If `domains` is missing, the route renders a chooser / guided empty state.

---

## 4. Landing (`/`) Additions

This spec extends `spec-v02-views.md` §4.1.

### 4.1 Purpose

The landing page becomes:

- workspace switcher/status overview,
- recent articles,
- **cross-domain bridge summary**.

### 4.2 Data Fetched

Landing now additionally fetches:

- `/data/bridges.json`

Existing landing data remains:

- `/data/domains.json`
- `/data/stats.json`
- `/data/articles.json`

### 4.3 Composition Update

Add one new card block after the workspace cards and before recent articles:

```text
┌────────────────────────────────────────────────────┐
│  [Hero: CONSTRUCT, install path, total stats]     │
├────────────────────────────────────────────────────┤
│  Workspaces                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │StatusCard│ │StatusCard│ │StatusCard│           │
│  └──────────┘ └──────────┘ └──────────┘           │
├────────────────────────────────────────────────────┤
│  Cross-Domain                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ Top bridge candidates                        │  │
│  │ cosmology ↔ philosophy-of-mind              │  │
│  │ observer-effects ↔ self-model loop          │  │
│  │ strong • parallels • score 0.82             │  │
│  │ ...                                          │  │
│  │ [Open cross-domain view]                     │  │
│  └──────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────┤
│  Recent articles                                   │
│  [ArticleCard] [ArticleCard] [ArticleCard]         │
└────────────────────────────────────────────────────┘
```

### 4.4 Cross-Domain Card Contents

Minimum content:

- title: `Cross-Domain`
- total counts summary:
  - confirmed bridges
  - strong candidates
- top 3 bridge entries
- one CTA: `Open Cross-Domain`

Each bridge row shows:

- domain pair
- source card title + target card title
- relation label
- `strong` or `confirmed`
- score

### 4.5 Landing Interactions

- click bridge row → `/cross-domain?domains=<a>,<b>&bridge=<bridge-id>`
- click CTA → `/cross-domain`

### 4.6 Empty / Loading / Error States

**Empty:**

```text
No cross-domain bridges yet.
Run bridge-detect or grow multiple domains to surface structural links.
```

**Loading:**

- skeleton card with 3 placeholder bridge rows

**Error:**

- compact error card: `Cross-Domain data unavailable. Retry.`

---

## 5. Cross-Domain Comparison Route (`/cross-domain`)

### 5.1 Purpose

Provide a balanced comparison dashboard for `2` or `3` domains.

The route answers:

- what bridges exist or are strongest here?
- what categories overlap?
- where are the domains asymmetric in maturity/confidence?

### 5.2 Header

Top row only.

Reason: this is a global route, not a single-workspace route.

### 5.3 Data Fetched

- `/data/bridges.json`
- `/data/domains.json`
- `/data/stats.json`
- optional lazy fetches for involved workspaces only if needed for deeper cards/links:
  - `/data/<workspace>/stats.json`

The first cut should prefer global/pre-aggregated data where possible.

### 5.4 Composition

```text
┌──────────────────────────────────────────────────────────┐
│  Cross-Domain                                            │
│  Compare domains and inspect bridge candidates           │
│  [domain selector: up to 3]                              │
├──────────────────────────────────────────────────────────┤
│  Summary                                                  │
│  confirmed 12 • strong 7 • top pair: cosmology ↔ mind    │
├──────────────────────────────────────────────────────────┤
│  Bridge candidates                                        │
│  [table/list of confirmed + strong candidates]            │
├──────────────────────────────────────────────────────────┤
│  Comparison dashboard                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │Domain A      │ │Domain B      │ │Domain C?     │       │
│  │cards/conf/...│ │cards/conf/...│ │cards/conf/...│       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                          │
│  overlap / asymmetry / bridge density modules            │
├──────────────────────────────────────────────────────────┤
│  Actions                                                  │
│  [Open global graph] [Open source card] [Open target card]│
└──────────────────────────────────────────────────────────┘
```

### 5.5 Comparison Modules

The first cut must include all three:

1. **Bridge candidates list**
   - confirmed + strong candidates only
   - sortable by score / status / domain pair
2. **Domain summary cards**
   - one card per selected domain
   - cards count, papers, avg confidence, lifecycle distribution
3. **Balanced comparison modules**
   - category overlap summary
   - bridge density summary
   - maturity/confidence asymmetry summary

### 5.6 Domain Selector

Rules:

- user can select `2` or `3` domains
- if fewer than `2`, render instructional empty state
- if more than `3` requested by URL, keep first `3` and show a small note

### 5.7 Candidate Selection Behavior

If `bridge=<id>` is in the URL:

- preselect that bridge row
- scroll it into view if necessary
- highlight the matching domain cards

Selecting a bridge candidate updates local UI state only; the URL update is optional in first cut.

### 5.8 Drill-Downs

From a selected bridge candidate:

- `Open source card` → `/<workspace>/artifacts?card=<id>`
- `Open target card` → `/<workspace>/artifacts?card=<id>`
- `Open global graph` → future cross-domain graph route/mode with the same bridge preselected

The graph action targets `/cross-domain/graph` per `spec-v02-cross-domain-graph.md`.

---

## 6. Comparison Semantics

### 6.1 Bridge Candidates List

Default list contents:

- all `confirmed` entries for the selected domain set
- all `strong` candidate entries for the selected domain set

Exclude by default:

- `medium`
- `weak`

### 6.2 Category Overlap Module

Show shared categories across selected domains.

At minimum:

- top shared categories
- which domains participate
- whether the category has confirmed bridges or only candidate bridges

### 6.3 Asymmetry Module

Show where selected domains differ materially.

At minimum:

- avg confidence delta
- lifecycle skew (`seed/growing/mature/archived`)
- card-count imbalance

### 6.4 Bridge Density Module

For each selected domain pair, show:

- confirmed bridge count
- strong candidate count
- avg bridge score

---

## 7. Empty / Loading / Error States

### 7.1 No Domains Selected

Render:

```text
Select 2 or 3 domains to compare.
Start with the strongest connected pair from the landing page, or choose domains below.
```

### 7.2 No Bridges for Selected Domains

Render:

```text
No strong cross-domain bridges found for this selection.
Try a different set of domains or run bridge-detect to refresh candidates.
```

### 7.3 Loading

- summary skeleton
- 3 domain-card skeletons
- bridge-list skeleton rows

### 7.4 Error

Use the standard `<ErrorState />` pattern.

---

## 8. Route and Navigation Updates

### 8.1 Route Map Additions

Extend the current route map with:

```text
/cross-domain                  cross-domain comparison dashboard
```

### 8.2 Global Navigation

Do **not** add a permanent top-row nav item yet.

First cut discovery path:

- landing Cross-Domain card
- direct URL

Reason: this keeps the nav stable while the cross-domain surface area settles, even though the graph route is now specified separately.

---

## 9. Validation Checklist

- [ ] Landing `/` shows a Cross-Domain card when `bridges.json` is present
- [ ] Landing card renders top 3 confirmed/strong bridge entries only
- [ ] Clicking a landing bridge row opens `/cross-domain?...`
- [ ] `/cross-domain` supports 2-domain and 3-domain comparison
- [ ] The comparison route is read-only
- [ ] Selected bridge candidates deep-link to the correct per-workspace artifact routes
- [ ] Empty states are explicit for no-selection and no-bridges cases

---

## 10. Open Follow-ups

1. Should medium candidates become user-toggleable in first cut, or wait?
2. Should per-domain cards eventually show a bridge-count badge sourced from `bridges.json`?
3. Does the comparison route need a saved/shareable preset concept later?
