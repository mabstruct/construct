# CONSTRUCT v0.2.x — Cross-Domain Feature Cluster — Product Requirements Document

**Version:** 0.2.x planning draft
**Date:** 2026-05-09
**Status:** Draft
**Prerequisite:** v0.2.0 shipped; v0.2.0-post release patches shipped through per-card hooks / incremental regen
**Companion:** [v0.2 live views PRD](prd-v02-live-views.md)

**Related specs and sources:**

- `spec-v02-runtime-topology.md` — current landing/dashboard scope and deferred bridge panel
- `spec-v02-views.md` — current per-view scope; KG and landscape are single-workspace in v0.2
- `spec-v02-cross-domain-data.md` — binding contract for `bridges.json` and scoring
- `spec-v02-cross-domain-views.md` — binding UI contract for landing card and comparison route
- `spec-v02-cross-domain-graph.md` — binding graph contract for `/cross-domain/graph` and bridges-first exploration
- `spec-v02-data-model.md` — current global/per-workspace contracts; future `bridges.json` hook
- `spec-v02-knowledge-views-spike.md` — current KG + Wiki decisions and deferred cross-domain graph
- `agent-spec-curator.md` §6 — cross-domain bridge detection model (L1/L2/L3)
- `CONSTRUCT-CLAUDE-impl/skills/bridge-detect/SKILL.md` — current bridge-detection workflow and outputs

This PRD captures the requirements for the **cross-domain feature cluster** that follows v0.2.0. It is intentionally a requirements document, not a binding implementation spec. Future `spec-v02-*.md` implementation notes will supersede it where they conflict.

---

## 1. Summary

v0.2 shipped strong **single-workspace** knowledge views plus a flat set of **cross-workspace articles**. The next meaningful capability jump is not search polish or secondary UI refinements; it is making CONSTRUCT's differentiator visible: **cross-domain bridge discovery and comparison**.

This cluster turns bridge detection from a skill-side text report into a first-class views capability. Users should be able to:

1. see important cross-domain bridges without asking Claude to summarize them,
2. explore the graph across domain boundaries,
3. compare domains side-by-side to spot structural overlap and asymmetry,
4. move from a bridge candidate into the relevant cards, graphs, and wiki surfaces.

Lunr.js full-text search is **explicitly postponed** to a later `v0.2.x` release. The product priority is cross-domain visibility, not deeper in-page text retrieval.

---

## 2. Terminology

Use the terms precisely:

| Term | Meaning | Use when |
|---|---|---|
| **Cross-domain** | User-facing knowledge feature spanning multiple domains / conceptual areas | Bridges, cross-domain graph mode, comparison view, domain-to-domain insights |
| **Cross-workspace** | Data/routing/storage scope spanning multiple workspace directories | `articles.json`, future global `bridges.json`, future global activity feed, root-level routes |

Rule: the product surface is **cross-domain**; the implementation may still use **cross-workspace** global files and routes.

---

## 3. Problem

Today, users can ask CONSTRUCT to detect bridges across domains, but the views layer still makes them inspect each workspace separately. The result is a mismatch:

- the agent model understands cross-domain structure,
- the browser UI mostly does not,
- the system's strongest differentiator remains hidden behind text interaction.

This creates three practical problems:

1. **Discovery cost is too high.** Users must remember to run bridge detection and parse a report.
2. **Comparison is fragmented.** Landscape and KG views stop at workspace boundaries.
3. **Synthesis visibility is delayed.** Cross-domain signals appear late, usually only after a digest, synthesis, or explicit question.

---

## 4. Design Principles

| Principle | Implication |
|---|---|
| **Bridges are evidence-bearing, not decoration** | Every surfaced bridge needs provenance: why it exists, which cards it comes from, and what detection level produced it |
| **Workspace files remain source of truth** | Cross-domain views are derived; no manual bridge UI state becomes canonical |
| **Cross-domain first, not generic globalism** | A flat global graph is not enough; the UI should emphasize domain boundaries and relationships |
| **Read-first, act-second** | Users should understand bridge candidates before deciding to create/confirm connections |
| **Keep the v0.2 contract intact** | Existing single-workspace routes remain valid; new cross-domain capabilities extend rather than replace them |

---

## 5. Scope

### 5.1 In Scope

1. **Cross-domain bridges panel on landing**
   - Show strong/recent bridge candidates from `bridge-detect`
   - Link from each candidate into relevant workspace routes/cards
2. **Cross-domain graph mode**
   - Add a way to explore graph structure across workspace/domain boundaries
   - Preserve the current single-workspace KG mode
3. **Cross-domain comparison view**
   - Extend landscape/comparison capability so users can compare domains side-by-side
   - Make overlap, divergence, and bridge density visible
4. **Derived data contracts needed to support the above**
   - likely global `bridges.json`
   - possibly additional global aggregates required by comparison surfaces
5. **Navigation and routing updates**
   - new top-level/global entry points if needed
   - clear transitions from bridge cards to per-workspace detail routes

### 5.2 Out of Scope

1. **Lunr.js full-text search** — deferred to a later `v0.2.x` release
2. **General search-system redesign** — keep current wiki substring search
3. **Realtime collaboration / multi-user**
4. **Concurrency-hardening of background hooks** — separate architecture-consolidation track
5. **Replacing the bridge-detect epistemic model** — reuse the current L1/L2/L3 logic first

### 5.3 Lower-Priority Adjacent Work

These may support the cluster later, but are not core to the first requirements cut:

- global activity feed
- per-workspace theme differentiation
- graph layout determinism

---

## 6. User Outcomes

After this cluster ships, a user should be able to:

1. Open the landing page and immediately see meaningful cross-domain bridge candidates.
2. Jump from a bridge candidate into the two relevant cards or workspaces with one click.
3. Explore a graph that includes domain boundaries instead of pretending they do not exist.
4. Compare domains and answer questions like:
   - Which domains are densely connected?
   - Which domains share categories but lack confirmed edges?
   - Where are the highest-confidence bridges?
5. Use the browser UI to find promising cross-domain synthesis opportunities before asking Claude to write.

---

## 7. Functional Requirements

### 7.1 FR-A — Bridges Landing Surface

The root landing page must gain a **cross-domain bridges panel**.

Minimum requirements:

- Show a curated subset of bridge candidates (e.g. strongest/recent/high-confidence)
- Each item shows:
  - source domain and target domain
  - source card and target card
  - proposed/actual relation type
  - detection level (`L1`, `L2`, `L3`)
  - short rationale / note
- Each item links into the underlying workspace/card surfaces
- Empty state is explicit: no bridges yet, suggest `bridge-detect`

### 7.2 FR-B — Cross-Domain Graph Mode

The graph feature set must support a **cross-domain exploration mode**.

Minimum requirements:

- Preserve existing single-workspace KG route and behavior
- Add a global or multi-domain graph mode that includes cards from multiple workspaces
- Visually encode domain boundaries / membership
- Allow filtering by domain pair and/or domain set
- Support bridge-centric exploration, not just all-node dumping
- Clicking a node still resolves to its per-workspace detail surface

### 7.3 FR-C — Cross-Domain Comparison View

Landscape must support **cross-domain comparison**.

Minimum requirements:

- Compare at least two domains side-by-side
- Show overlap and asymmetry in category coverage / card maturity / bridge density
- Make cross-domain links explorable from the comparison surface
- Keep per-workspace landscape intact for domain-internal inspection

### 7.4 FR-D — Derived Data Contracts

The data layer must expose the minimum global contracts required by the cluster.

Expected direction:

- `bridges.json` as a global derived file
- optional derived comparison aggregates if computing everything client-side becomes awkward

Requirements:

- deterministic generation
- explicit provenance to underlying card/workspace IDs
- compatible with current `views-generate-data` incremental model
- safe to delete and regenerate

### 7.5 FR-E — Navigation and Routing

The views app must make the cross-domain surfaces easy to find.

Requirements:

- entry from landing without asking Claude first
- stable URLs for the new surfaces
- deep links back into per-workspace routes
- terminology consistent with this PRD: user-facing labels should say **cross-domain**, not **cross-workspace**, unless the route is explicitly a global index artifact like Articles

---

## 8. Non-Functional Requirements

1. **Interpretability first.** Cross-domain surfacing must not feel like a magical similarity engine; users need to see what cards and evidence support a bridge.
2. **Progressive complexity.** Landing panel = lightweight summary; graph/comparison views = deeper exploration.
3. **Performance must degrade gracefully.** The cross-domain graph must avoid unusable all-node overload on larger installs.
4. **No breakage of current routes.** Existing v0.2 bookmarks and workflow assumptions remain valid.
5. **Derived-only discipline.** No user edits are made in the views layer; any confirm/apply flow routes back through skills.

---

## 9. Open Questions for Follow-on Specs

1. What is the exact contract for `bridges.json`?
2. Should bridge candidates represent only confirmed edges, or also unconfirmed bridge-detect proposals?
3. Is the cross-domain graph a new route, a mode switch inside KG, or both?
4. Should comparison start as pairwise only, or support N domains?
5. Does activity feed belong in the first cross-domain cut, or remain separate?

---

## 10. Sequencing Recommendation

Recommended order:

1. **Data contract first** — define `bridges.json` and any comparison aggregates
2. **Landing bridges panel** — fastest visible product gain
3. **Cross-domain comparison view** — structured reasoning aid
4. **Cross-domain graph mode** — heavier UI/data work, but highest exploratory upside

Rationale: the landing panel and comparison view make the system's differentiator visible with lower implementation risk than jumping straight into a global graph.

---

## 11. Success Criteria

This cluster is successful when:

1. users can discover cross-domain bridge candidates from the UI without prompting Claude,
2. bridge candidates are grounded in specific cards and domains,
3. at least one cross-domain route/view is clearly more useful for synthesis preparation than the current per-workspace-only flow,
4. the implementation preserves current v0.2.0 views behavior for users who never engage with cross-domain features.
