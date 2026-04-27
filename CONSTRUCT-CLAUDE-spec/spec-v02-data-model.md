# spec-v02-data-model — Derived JSON Data Contracts

**Status:** Draft
**Date:** 2026-04-27
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 2
**Related:** `prd-v02-live-views.md` §4, §5.1 · `spec-v02-runtime-topology.md` · `adrs/adr-0002-v02-packaging.md`

---

## 1. Scope

This spec defines, for v0.2 MVP, **the JSON files that `views-generate-data` writes** into `views/build/data/`. These files are the contract between the agent runtime (which produces them) and the SPA (which consumes them). It is the **stable boundary** identified in `spec-v02-runtime-topology.md` §9.3 — the artefact that survives a future cloud topology swap unchanged.

This spec does not cover: how to compute aggregate stats efficiently (Epic 4 — `views-generate-data` skill design), nor how each view component renders the data (Epic 7 — view implementation).

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Source of truth | Workspace files only. `views/build/data/` is a derived cache, fully rebuildable, never canonical. See §12 |
| Layout | Hybrid: global files at `data/`, per-workspace files at `data/<workspace_id>/` |
| Workspace ID | The directory name under the CONSTRUCT install root (`cosmology`, `climate-policy`) — kebab-case, filesystem-safe |
| Schema version | `0.2.0` — written in every file's envelope; matches `CONSTRUCT-CLAUDE-impl/VERSION` |
| Card content | Full markdown body baked into `cards.json` (MVP simplification — split body into separate files in v0.2.1 if size becomes a problem) |
| Connection scope | Per-workspace for v0.2. Cross-workspace bridges are v0.2.1 |
| Article scope | Cross-workspace (flat list at `data/articles.json`) — per `spec-v02-runtime-topology.md` §5.1 |
| Digest scope | Per-workspace |
| Event log scope | Per-workspace, last 100 events. Cross-workspace activity feed is v0.2.1 |
| Curation history | Parsed, structured. MVP captures: date, summary, delta counts. Raw report path retained as link |
| Provenance into articles | Each `source_cards` entry expanded with title, type, confidence, contribution-note |
| Determinism | Output JSON is deterministic given identical workspace state — keys sorted, arrays sorted by stable keys (id, date) |
| Empty data | Empty workspace produces valid JSON with empty arrays — never null, never missing fields |

---

## 3. File Layout

```
views/build/
├── version.json                         (global — defined in spec-v02-runtime-topology.md §4.1)
└── data/
    ├── domains.json                     (global — workspace registry + computed metrics)
    ├── articles.json                    (global — cross-workspace published outputs)
    ├── stats.json                       (global — aggregate roll-up across all workspaces)
    │
    ├── cosmology/
    │   ├── cards.json
    │   ├── connections.json
    │   ├── digests.json
    │   ├── events.json
    │   ├── stats.json                   (per-workspace overrides global on workspace pages)
    │   └── curation-history.json
    │
    └── climate-policy/
        └── ... (same structure)
```

### 3.1 Why hybrid

Per `spec-v02-runtime-topology.md` §5.1: articles are cross-workspace; digests, knowledge graph, landscape, artifacts (cards) are per-workspace. The data layout mirrors the routing layout. The SPA loads global files at boot; per-workspace files are lazy-loaded when the user navigates to `/<workspace>/...`.

### 3.2 Why workspace ID = directory name

The agent already addresses workspaces by directory name (`cosmology/`, `climate-policy/`). Reusing it as the SPA route segment and JSON file scope avoids inventing a parallel ID system. Constraint: workspace directory names must be filesystem-safe AND URL-safe (kebab-case, no spaces). This is already enforced by `workspace-init` / `domain-init` in v0.1.

---

## 4. Common Envelope

Every JSON file starts with this envelope at the top level:

```json
{
  "schema_version": "0.2.0",
  "generated_at": "2026-04-27T14:32:11Z",
  "workspace_id": "cosmology",          // omitted for global files
  "build_id": "a3f81c2d",                // matches version.json
  "data": { ... }                        // schema-specific payload
}
```

- `schema_version` lets the SPA detect older builds it can't render.
- `generated_at` is ISO-8601 UTC.
- `build_id` matches `version.json` so the SPA can verify atomicity (all data files must share the same `build_id` per build).
- `data` contains the schema-specific payload. Each section below documents only the `data` shape.

---

## 5. Schemas

### 5.1 `domains.json` — global workspace registry

**Source:** `<install-root>/domains.yaml` (one root-level file aggregating all domains) + scan of workspace directories + per-workspace card/connection/ref counts.

> **Note for MVP:** v0.1 puts `domains.yaml` *inside each workspace*. v0.2 introduces a single `<install-root>/domains.yaml` aggregating across workspaces. If keeping per-workspace `domains.yaml` is preferred, `views-generate-data` simply scans each workspace and merges. Decide in Epic 4 implementation. For this spec, the contract is the same either way.

```jsonc
{
  "schema_version": "0.2.0",
  "generated_at": "...",
  "build_id": "...",
  "data": {
    "domains": [
      {
        "id": "cosmology",
        "name": "Cosmology",
        "description": "...",
        "status": "active",                  // active | paused | archived
        "created": "2026-04-22",
        "content_categories": ["string", ...],
        "source_priorities": ["string", ...],
        "cross_domain_links": [{"to": "climate-policy", "note": "..."}],
        "metrics": {
          "papers": 47,                      // refs/ count
          "cards": 120,
          "cards_by_lifecycle": {"seed": 18, "growing": 60, "mature": 38, "archived": 4},
          "cards_by_confidence": {"1": 5, "2": 22, "3": 51, "4": 30, "5": 12},
          "connections": 184,
          "orphan_cards": 3,
          "avg_confidence": 3.12,
          "last_research_cycle": "2026-04-25",
          "last_curation_cycle": "2026-04-26"
        }
      }
    ]
  }
}
```

### 5.2 `cards.json` — per-workspace

**Source:** All `*.md` under workspace `cards/` directory.

```jsonc
{
  "data": {
    "cards": [
      {
        "id": "string",                      // from frontmatter
        "title": "string",
        "epistemic_type": "finding",         // one of 10 types — references/epistemic-types.md
        "confidence": 3,                     // 1–5
        "source_tier": 2,                    // 1–5
        "lifecycle": "growing",              // seed | growing | mature | archived
        "domains": ["cosmology"],
        "content_categories": ["string"],
        "tags": ["string"],
        "author": "construct",               // construct | researcher | curator | human
        "created": "2026-04-23",
        "last_reviewed": "2026-04-26",       // optional — null if not yet reviewed
        "sources": [{"type": "url", "ref": "https://...", "title": "..."}],
        "connects_to": ["other-card-id", ...],
        "body_markdown": "## Summary\n\n...", // full card body (the part below frontmatter)
        "summary_excerpt": "string"          // first 200 chars of summary section, plain text — for list views
      }
    ]
  }
}
```

**Notes:**
- `body_markdown` is the **literal** card body (everything after the closing `---` of frontmatter). The SPA renders it via `react-markdown`.
- `summary_excerpt` is a derived field for the cards browser list view (PRD §4.4) — saves the SPA from running markdown extraction on every card.
- `connects_to` is a denormalised list of card IDs this card connects to (any direction). The full edge list with types lives in `connections.json`.

### 5.3 `connections.json` — per-workspace (UI-shaped)

**Source:** Workspace `connections.json` (canonical) — re-shaped for graph rendering.

```jsonc
{
  "data": {
    "connections": [
      {
        "id": "conn-0042",                    // stable ID for click-to-detail
        "source": "card-id-a",
        "target": "card-id-b",
        "type": "supports",                   // one of 9 — references/connection-types.md
        "note": "string",                     // freeform
        "created": "2026-04-25",
        "author": "curator"
      }
    ],
    "type_counts": {                          // precomputed for legend
      "supports": 84, "contradicts": 7, "extends": 19,
      "parallels": 11, "requires": 4, "enables": 12,
      "challenges": 6, "inspires": 9, "gap-for": 32
    }
  }
}
```

**Notes:**
- Source canonical `connections.json` is the single source of truth (per PRD §2). This UI-shaped version differs in: it has a `type_counts` precomputation, IDs may be added if missing, the array is sorted by `created` ASC for stable rendering.
- For the MVP graph (`/<workspace>/knowledge-graph`), the SPA joins `cards.json` and `connections.json` client-side. No precomputed graph layout — D3 force-direct on the fly.

### 5.4 `digests.json` — per-workspace

**Source:** Parsed from workspace `digests/**/*.md` files. Each digest follows `templates/digest.md`.

```jsonc
{
  "data": {
    "digests": [
      {
        "id": "2026-04-25-digest",            // derived from filename or date
        "date": "2026-04-25",
        "theme": "string",                    // pulled from "theme" line if present, else first line of summary
        "summary_text": "string",             // the Summary section, joined
        "papers_found": 12,
        "papers_ingested": 8,
        "papers_skipped": 4,
        "seed_cards_created": 5,
        "top_findings": [
          {"rank": 1, "title": "...", "relevance": 4, "summary": "...", "url": "...", "cluster": "..."}
        ],
        "search_clusters": [
          {"id": "string", "queries": 3, "results": 24, "ingested": 8}
        ],
        "coverage_notes": "string",
        "suggested_adjustments": "string",
        "raw_path": "digests/2026-04-25.md"   // for "view source" link
      }
    ]
  }
}
```

**Notes:**
- The design-example `digests.json` has a richer `candidates[]` with `icon`, `rank`, `cluster`, etc. We adopt that shape under `top_findings[]`.
- Parsing is best-effort. Missing sections produce empty fields, not parse failures.

### 5.5 `articles.json` — global, cross-workspace

**Source:** Parsed from `<workspace>/publish/**/*.md` for every workspace. Articles follow `templates/publish.md`.

```jsonc
{
  "data": {
    "articles": [
      {
        "id": "2026-04-20-cosmic-string-review",  // derived from filename
        "title": "...",
        "type": "briefing",                       // briefing | essay | review | ...
        "status": "draft",                        // draft | published
        "date": "2026-04-20",
        "workspaces": ["cosmology"],              // origin workspace(s)
        "domains": ["cosmology"],                 // mirrored from frontmatter
        "confidence_floor": 2,
        "source_cards": [                         // EXPANDED from raw card-ID list
          {
            "id": "card-id-x",
            "workspace_id": "cosmology",
            "title": "...",
            "epistemic_type": "finding",
            "confidence": 4,
            "contribution": "string"              // from publish.md Sources table
          }
        ],
        "body_markdown": "string",                // full content
        "excerpt": "string",                      // first 280 chars plain text
        "raw_path": "cosmology/publish/2026-04-20-cosmic-string-review.md"
      }
    ]
  }
}
```

**Notes:**
- `source_cards` is **expanded** from the raw card-ID list in frontmatter. The expander walks each ID, finds the matching card in any workspace, copies title/type/confidence. This is the provenance-into-views requirement from PRD §4.6 and Epic 2 last item.
- If an article references a missing card ID, the entry is `{"id": "...", "status": "missing"}` — never dropped, never silently ignored.

### 5.6 `events.json` — per-workspace

**Source:** Last 100 entries of workspace `log/events.jsonl`.

```jsonc
{
  "data": {
    "events": [
      {
        "timestamp": "2026-04-26T09:14:22Z",
        "type": "card_created",                   // event-type string from skill
        "actor": "researcher",                    // construct | researcher | curator | human
        "subject": {                              // event-specific shape
          "card_id": "...", "title": "..."
        },
        "skill": "research-cycle"                 // skill that emitted the event
      }
    ]
  }
}
```

**Notes:**
- Event types are not enumerated here — they're whatever skills emit. Documenting the canonical set is Epic 8 work.
- The SPA renders events from a small set of known types and falls back to `<actor> <type> <subject>` for unknown ones.

### 5.7 `stats.json` — global + per-workspace

Two variants of the same schema, one global, one per-workspace.

**Global** (`data/stats.json`):

```jsonc
{
  "data": {
    "totals": {
      "workspaces": 2,
      "papers": 89,                            // sum across workspaces
      "cards": 220,
      "connections": 312,
      "digests": 14,
      "articles": 7
    },
    "by_lifecycle": {"seed": 30, "growing": 110, "mature": 75, "archived": 5},
    "by_confidence": {"1": 8, "2": 41, "3": 92, "4": 62, "5": 17},
    "activity_last_30d": {
      "cards_created": 24,
      "connections_added": 31,
      "digests": 5,
      "articles": 1
    }
  }
}
```

**Per-workspace** (`data/<workspace>/stats.json`): same shape but scoped to one workspace, plus:

```jsonc
{
  "data": {
    "totals": { ... },                         // workspace-scoped
    "by_lifecycle": { ... },
    "by_confidence": { ... },
    "activity_last_30d": { ... },
    "connection_density": 0.47,                // edges / (n*(n-1)/2)
    "orphan_cards": 3,
    "avg_confidence": 3.12,
    "category_coverage": {                     // category → cards count
      "foundation-models": 18, "spatial-reasoning": 7, "rl": 0
    },
    "search_clusters": [                       // from search-seeds.json
      {"id": "...", "active": true, "cards_produced": 12}
    ]
  }
}
```

### 5.8 `curation-history.json` — per-workspace

**Source:** Parsed from `<workspace>/curation-reports/CURATION-REPORT-*.md` (or wherever curation cycle writes them — `daily-cycle.md` workflow location).

```jsonc
{
  "data": {
    "cycles": [
      {
        "id": "2026-04-26-curation",
        "date": "2026-04-26",
        "summary": "string",                   // first paragraph or H2 summary
        "deltas": {
          "promoted": 4,                       // seed→growing or growing→mature
          "archived": 2,
          "decayed": 1,                        // confidence dropped
          "orphans_resolved": 3,
          "connections_added": 7,
          "connections_removed": 0
        },
        "raw_path": "curation-reports/CURATION-REPORT-2026-04-26.md"
      }
    ]
  }
}
```

**Notes:**
- MVP captures only the high-level deltas. Full per-card change list is in the raw report and reachable via `raw_path`.
- "Quality trend over time" mentioned in PRD §6.2 is a derived chart over `cycles[]` — no separate field needed.

---

## 6. Provenance and Confidence Policy

PRD §2 ("Decide what provenance and confidence metadata must survive into view data") — explicit answer:

| Surface | What survives |
|---|---|
| Cards list | `confidence`, `source_tier`, `lifecycle`, `author`, `last_reviewed` |
| Card detail | All frontmatter fields + full markdown body + `sources[]` array |
| Connections | `type`, `note`, `created`, `author` |
| Digests | All frontmatter + `top_findings[].relevance` per item |
| Articles | `confidence_floor` from frontmatter + **expanded** `source_cards[]` with `confidence` per source |
| Events | `actor`, `skill`, `timestamp` |
| Stats | All histograms preserved; aggregates derived |

**Nothing is hidden from the view layer**, with one exception: the canonical `log/events.jsonl` may contain skill-internal scratch events. Generation filters to a documented event type allowlist (Epic 8).

---

## 7. Versioning

- `schema_version` in every file. Single global value, currently `0.2.0`.
- Bumped when **any** field's contract changes in a backwards-incompatible way (rename, remove, type change). Adding new optional fields does not bump.
- The SPA shows a clear "data was generated by an older version" banner if `schema_version` is older than the SPA expects, and refuses to render only if the major version differs.

---

## 8. Determinism Rules

`views-generate-data` must produce byte-identical output for identical workspace state. This makes `build_id` (a hash over data files) stable.

- All array elements sorted by stable key:
  - cards by `id`
  - connections by `(source, target, type)`
  - digests by `date` DESC
  - articles by `date` DESC
  - events by `timestamp` DESC
  - cycles by `date` DESC
- All object keys sorted alphabetically in serialisation (use `JSON.stringify` with sorted-keys helper or equivalent).
- No non-deterministic fields (no `random()`, no clock-derived data inside payloads — the only timestamp is `generated_at` in the envelope).
- Sub-second timestamps in events truncated to seconds.

---

## 9. Empty / Partial / Broken Workspace Handling

The SPA must render correctly when:

- A workspace has zero cards → `cards.json.data.cards` is `[]`, all metrics are `0`
- A workspace has cards but no connections → `connections.json.data.connections` is `[]`, the graph view shows "no connections yet"
- A digest fails to parse → the digest is included with `parse_status: "partial"` and only fields that parsed cleanly. Never omitted silently.
- An article references missing source cards → entry kept with `status: "missing"` as in §5.5

`views-generate-data` must complete and write all files even if individual artefacts fail to parse. The view layer's job is to render gracefully; the data layer's job is to never lie about what's there.

---

## 10. Acceptance Checks

This spec is implemented when:

- [ ] All 8 schemas validate against documented shapes for a real multi-domain workspace
- [ ] Empty workspace produces valid JSON with empty arrays for every collection
- [ ] `build_id` is stable across two runs of `views-generate-data` against unchanged workspace state
- [ ] `articles.json[].source_cards` are expanded with title/type/confidence, never bare ID strings
- [ ] Missing source cards in articles surface as `{"status": "missing"}` entries
- [ ] All array sorts are stable per §8
- [ ] `schema_version` and `build_id` match across all files in one build
- [ ] A workspace with corrupt frontmatter still produces a parseable `cards.json` (corrupt cards excluded with logged warning, not silent drop)
- [ ] **Safe-delete** (§12 I3): `rm -rf views/build/data/` followed by `views-generate-data` produces byte-identical output to a regen against an unchanged workspace
- [ ] **Single-writer** (§12 I1): grep for writes into `views/build/data/` across the codebase returns only `views-generate-data`

---

## 11. Open Follow-ups

1. **`domains.yaml` location.** v0.1 puts it inside each workspace; v0.2 implies a global registry. Decide in Epic 4. Either way, the JSON output contract is the same.
2. **Markdown body weight.** A workspace with 1000 cards × 5KB body = 5MB `cards.json`. Acceptable for MVP. v0.2.1 may split body into separate files keyed by ID.
3. **Connections cross-workspace.** Currently per-workspace only. Bridges (cross-workspace connections from `bridge-detect`) need a separate `bridges.json` global file when surfaced — v0.2.1.
4. **Activity feed cross-workspace.** Per-workspace `events.json` only for v0.2. Cross-workspace `events.json` global file — v0.2.1.
5. **Search index.** PRD §8 defers in-views search to v0.3. No `search-index.json` here.
6. **Source-tier authority.** `source_tier` ranges 1–5 per `references/source-tiers.md`. The data layer trusts what frontmatter says; no validation at generate time.
7. **`raw_path` security.** Article and digest `raw_path` fields point at workspace files. The SPA must NOT fetch them — they're for human reference only (or an opt-in "show raw" feature if/when added). For MVP, document that the SPA treats them as opaque strings.

---

## 12. Source of Truth and Cache Invariants

`views/build/data/` is a **derived presentation cache**, never source of truth. Workspace files are the only canonical state in CONSTRUCT.

This relationship is a load-bearing principle, not just a convention. Treating the cache as primary breaks recoverability, breaks the cloud-future topology (`spec-v02-runtime-topology.md` §9), and inverts the agent-as-runtime model from ADR-0001 ("markdown is the truth, everything else is derived").

The general pattern — three layers (canonical / derived / presentation), one-way data flow — is described project-wide in `architecture-overview.md`. This section restates the invariants as they bind v0.2 specifically.

### 12.1 The four invariants

| # | Invariant | What it guarantees | How to test |
|---|---|---|---|
| **I1** | **Single-writer.** Only `views-generate-data` writes to `views/build/data/`. | No silent state accumulates outside the canonical store. | Codebase grep for writes to that path returns one skill. |
| **I2** | **Read-only direction.** The SPA never writes back. There is no backend. No PUT/POST/DELETE handler exists anywhere. | Browser cannot bypass canonical state. Any "edit in browser" feature must route through Claude → skill → workspace. | No non-GET fetch calls in SPA source. |
| **I3** | **Safe-delete.** `rm -rf views/build/data/` followed by `views-generate-data` produces byte-identical output to a regen against an unchanged workspace. | The cache is wholly disposable. Recovery never requires anything but the canonical store. | Hash-and-compare two regenerations across a delete. |
| **I4** | **No-novel-data.** Every field in every JSON file in this spec has a documented derivation rule from a workspace artefact (or a documented computation over them). | The cache contains nothing that isn't traceable to layer 1. | Per-field audit against `templates/` and §5 above. |

### 12.2 What this rules in and out

**Allowed:**
- Computed aggregates (`avg_confidence`, `connection_density`, lifecycle histograms) — derivation rule is "aggregate over these source fields"
- Re-shaped data (UI-friendly `connections.json` with `type_counts` precomputed)
- Joined data (article `source_cards` expanded with card title/type/confidence — the join is derived, nothing new is invented)
- Excerpts (`summary_excerpt` = first N characters of card body — purely derived)
- Build identity (`build_id` = hash over data files; `generated_at` = wall clock at generation — both metadata about the build, not data content)

**Forbidden:**
- A field that exists only in the cache, with no traceable source in the workspace
- A skill (other than `views-generate-data`) writing to `views/build/data/`
- The SPA writing back to the cache, the workspace, or any backend
- The cache being treated as the only copy of any fact
- A "small convenience" piece of state stashed in the cache because there's no obvious workspace home for it (if it's a fact, it belongs in layer 1; if it's UI state, it belongs in browser localStorage)

### 12.3 Why this matters for v0.2 specifically

v0.2 is the first time CONSTRUCT introduces a derived layer that lives in the filesystem alongside the canonical workspace. Before v0.2, "everything is markdown" was self-enforcing because there was nothing else. With `views/build/data/` introduced, the discipline becomes explicit: every byte in that directory is rebuildable, replaceable, and ownership-clear.

If this discipline slips — even once, for one "convenient" cache field — the cloud-future topology breaks. The CDN can't accept writes; writes from a CDN edge can't propagate back to canonical storage; the JSON contract stops being a stable boundary. The four invariants are what keep the boundary stable.

---

## 13. References

- `architecture-overview.md` — general three-layer pattern (canonical / derived / presentation)
- `prd-v02-live-views.md` §4 (required views), §5.1 (`views-generate-data`), §6.2 (curation history)
- `spec-v02-runtime-topology.md` §4 (`version.json`), §5 (routing), §9 (cloud-future seam)
- `adrs/adr-0001-claude-native-approach.md` — "markdown is the truth, everything else is derived"
- `adrs/adr-0002-v02-packaging.md` — places `views-generate-data` skill in `CONSTRUCT-CLAUDE-impl/skills/`
- `templates/card.md`, `templates/connections.json`, `templates/digest.md`, `templates/publish.md`, `templates/ref.json`, `templates/domains.yaml`
- `references/epistemic-types.md`, `references/connection-types.md`, `references/lifecycle-states.md`, `references/confidence-levels.md`, `references/source-tiers.md`
- `views/design-example/src/data/digests.json`, `articles.json` — visual / shape reference
- `CONSTRUCT-CLAUDE-impl/VERSION` — `schema_version` source of truth
