# CONSTRUCT — Architectural Overview

**Status:** Draft (Living)
**Date:** 2026-04-27
**Scope:** Project-wide pattern and component layering
**Related:** `adrs/adr-0001-claude-native-approach.md` · `adrs/adr-0002-v02-packaging.md` · `prd.md` · `prd-v02-live-views.md` · `spec-v02-runtime-topology.md` · `spec-v02-data-model.md`

---

## 1. Purpose

This document captures the architectural pattern that underpins CONSTRUCT and which v0.2 (live views) makes load-bearing for the first time: a strict separation of **canonical state**, **derived state**, and **presentation**, with one-way data flow between them.

It exists so future contributors — human or Claude — have a single place to understand *why* the directory layout looks the way it does and *where new components should fit*.

This document does not replace the PRD, ADRs, or per-feature specs. It is the architectural lens through which they should be read.

---

## 2. The Pattern in One Sentence

> **CONSTRUCT separates canonical state (workspace files), derived state (the JSON cache), and presentation (the SPA), with strictly one-way data flow.**

Workspace → derived → presentation. Never the reverse. Anything that wants to change canonical state goes through the agent runtime (Claude), not through the cache or the browser.

---

## 3. The Three Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1 — CANONICAL STATE  (the only source of truth)              │
│                                                                     │
│  Workspace files on the filesystem:                                 │
│    cards/*.md, connections.json, refs/*.json, digests/*.md,         │
│    publish/*.md, log/events.jsonl, curation-reports/*.md,           │
│    domains.yaml, governance.yaml, search-seeds.json                 │
│                                                                     │
│  Edited only by Claude (via skills, on behalf of human or agent).   │
│  Survives all derived/presentation layers being deleted.            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ views-generate-data
                               │ (the only writer to layer 2)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2 — DERIVED STATE  (presentation cache)                      │
│                                                                     │
│  views/build/data/*.json                                            │
│  views/build/version.json                                           │
│                                                                     │
│  Wholly rebuildable from layer 1.                                   │
│  Never edited by humans, browsers, or any other skill.              │
│  Safe to delete: rm -rf views/build/data/ then regenerate.          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ HTTP GET (read only)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3 — PRESENTATION  (the SPA in the browser)                   │
│                                                                     │
│  views/build/{index.html, assets/}                                  │
│                                                                     │
│  Read-only consumer. Never writes back. Never POSTs.                │
│  Any "edit in browser" feature must flow through Claude (layer 1).  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Layer 1 — Canonical State

The workspace is the **only source of truth**. Every fact CONSTRUCT knows lives in a markdown, YAML, or JSON file that a human can read with a text editor. There is no database, no opaque store, no network-hosted state of record.

Edits to layer 1 happen exclusively through Claude (the agent runtime). Skills like `card-create`, `card-edit`, `research-cycle`, `curation-cycle` write to workspace files. The user does not edit derived or presentation state — they ask Claude to do it, and Claude updates layer 1.

This is the principle established in ADR-0001: *"markdown is the truth, everything else is derived."*

### 3.2 Layer 2 — Derived State

`views/build/data/` holds JSON files generated from layer 1. They are a **presentation cache**: shaped for the SPA's consumption, sorted for stable rendering, with computed aggregates inlined. They contain no facts that aren't ultimately traceable to layer 1.

Only one skill writes layer 2: `views-generate-data`. Every other component reads it (or doesn't touch it at all).

The cache is treated as ephemeral. Deleting the entire `views/build/data/` directory is a no-op for the system's truth — running `views-generate-data` rebuilds it byte-identically.

### 3.3 Layer 3 — Presentation

The SPA in `views/build/{index.html, assets/}` is a static React app. It fetches JSON from layer 2 and renders it. It has no backend. It cannot write. There is no PUT, POST, or DELETE endpoint anywhere in the system.

Any future feature that *appears* to be "editing in the browser" must architecturally route as: browser action → Claude conversation → Claude runs a skill → skill edits layer 1 → `views-generate-data` regenerates layer 2 → browser fetches fresh data on reload (or on `UPDATE`-flag click).

---

## 4. The Four Invariants

These invariants are what keep the layers from collapsing into each other. Every architectural decision in CONSTRUCT must preserve them.

| # | Invariant | Test |
|---|---|---|
| **I1** | **Single-writer** to layer 2. Only `views-generate-data` writes to `views/build/data/`. | Codebase grep for writes to that path returns one skill. |
| **I2** | **Read-only direction** for layer 3. The SPA never writes back. No backend accepts writes. | No PUT/POST/DELETE handlers exist. SPA has no fetch with non-GET method. |
| **I3** | **Safe-delete** invariant for layer 2. `rm -rf views/build/data/` followed by `views-generate-data` produces byte-identical output. | Hash-and-compare two regenerations across a delete. |
| **I4** | **No-novel-data** invariant for layer 2. Every field in every JSON file has a documented derivation rule from layer 1. | For each schema field, `spec-v02-data-model.md` traces it to a workspace artefact or a documented computation. |

Violating any of these is a bug, not a feature.

---

## 5. Why One-Way Flow Matters

### 5.1 Recoverability

Any layer below 1 can be lost without losing knowledge. Delete the whole `views/` directory; the workspace is intact. Lose the browser cache; the workspace is intact. Bug in `views-generate-data` produces wrong JSON; the workspace is intact.

This makes layer 2 and 3 **fully disposable**. That property is rare and valuable.

### 5.2 Multiple readers, one writer per layer

The pattern admits any number of layer-2 derivers writing into different cache locations from the same canonical source. Today: `views-generate-data` writing for the SPA. Tomorrow: an MCP server reading layer 1 and exposing tool calls; a SQLite indexer writing to a queryable cache. Each new derived layer is additive — none of them displaces canonical state.

The pattern also admits any number of layer-3 consumers. The current SPA is one; a future Claude Design dashboard, an artifact view, or a native desktop UI would each be a fresh layer-3 reading from the same layer-2 (or running their own derivation directly off layer 1).

### 5.3 Cloud topology preservation

`spec-v02-runtime-topology.md` §9 describes the local-vs-cloud topologies side-by-side. The pattern is **identical** across both:

- Local: layer 1 on user's filesystem, layer 2 in `views/build/data/`, layer 3 served by `npx serve` on localhost.
- Cloud: layer 1 in cloud storage, layer 2 on a CDN, layer 3 fetched by browser over HTTPS.

What changes is *where* each layer lives. What stays the same is *the directionality* and the JSON contract between layers 1→2. **Because writes can only target layer 1**, no writes need a return path through CDN or browser. The cloud topology is feasible *because* of the invariants.

### 5.4 Predictable failure modes

Most failures in derived layers are reversible by re-deriving. A corrupt cache JSON file is fixed by `views-generate-data`. A wrong build is fixed by `views-build`. Only failures that touch layer 1 (skill bug that writes bad workspace state) require manual recovery — and the workspace is markdown, so manual recovery is editing a text file.

---

## 6. Topology Variants

### 6.1 Local (today, v0.2 MVP)

```
┌─ User's machine ─────────────────────────────────────────────────┐
│                                                                  │
│  Claude (agent runtime, layer-1 writer)                          │
│         │                                                        │
│         │ runs skills                                            │
│         ▼                                                        │
│  cosmology/, climate-policy/, ...   ◄── layer 1 (workspace)     │
│         │                                                        │
│         │ views-generate-data                                    │
│         ▼                                                        │
│  views/build/data/*.json            ◄── layer 2 (cache)         │
│  views/build/{html, assets}         ◄── (built by views-build)   │
│         │                                                        │
│         │ npx serve                                              │
│         ▼                                                        │
│  localhost:3001                                                  │
│         │                                                        │
│         │ HTTP GET (read only)                                   │
│         ▼                                                        │
│  Browser (layer 3)                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Cloud (v0.3+ horizon)

```
┌─ Cloud ─────────────────────────────────────────┐  ┌─ Browser ─┐
│                                                 │  │           │
│  Claude (cloud agent, layer-1 writer)           │  │  Layer 3  │
│         │                                       │  │           │
│         ▼                                       │  └─────▲─────┘
│  Cloud workspace storage   ◄── layer 1          │        │ HTTPS
│         │                                       │        │
│         │ views-generate-data (cloud)           │        │
│         ▼                                       │        │
│  Static asset host (CDN)   ◄── layer 2 + assets │────────┘
│                                                 │
└─────────────────────────────────────────────────┘
```

What changes between (a) and (b): infrastructure ownership, transport, network boundaries.
What is identical: the three layers, the four invariants, the JSON contract.

### 6.3 Hybrid (one possible v0.3 step)

Per ADR-0001 §"Future Enhancements", an MCP server can sit alongside the agent runtime, reading layer 1 directly and exposing tool calls to Claude for filtered queries. The MCP server is **not** a new layer — it's a sibling layer-2 derivation pathway, optimised for agent consumption rather than browser consumption.

```
                Claude (layer-1 writer + reader)
                  │
                  ├─── via filesystem + skills
                  ▼
                Workspace (layer 1)
                  │            │
                  │            └── via MCP tool calls ───┐
                  │                                       │
                  │ views-generate-data                   │
                  ▼                                  ┌────▼────────────┐
                views/build/data/                    │ MCP server      │
                (layer 2 — for SPA)                  │ (layer 2 — for  │
                                                     │  agent queries) │
                                                     └─────────────────┘
```

Same pattern. Two derivation pipelines, one canonical source.

---

## 7. Where Components Live Today

| Path | Layer | Role |
|---|---|---|
| `~/my-construct/<workspace>/` | 1 | Workspace canonical state (one per research domain) |
| `~/my-construct/AGENTS.md` | (config) | Boots Claude as CONSTRUCT |
| `~/my-construct/.construct/` | (config) | Skills, agents, workflows, references, templates |
| `~/my-construct/views/src/` | (source) | SPA source (JSX, components, pages, Vite config) |
| `~/my-construct/views/build/` | 3 | Compiled SPA bundle (HTML, JS, CSS) |
| `~/my-construct/views/build/data/` | **2** | Derived JSON cache for the SPA |
| `~/my-construct/views/build/version.json` | **2** | Build identity stamp; SPA polls this |
| `~/my-construct/views/server.pid` | (runtime) | PID of the running `npx serve` process |
| `~/my-construct/views/design-example/` | (reference) | Read-only visual prototype, never served |

---

## 8. Adding New Components — Where Should X Go?

Use this as a checklist before introducing any new component.

### 8.1 Decision tree

1. **Does the component contain facts that didn't exist before?** → It belongs in **layer 1** (workspace). Persist it as markdown, YAML, or JSON. Edit it through a skill, never directly through a UI.
2. **Is the component a re-shaped or pre-computed view of layer-1 facts?** → It belongs in **layer 2**. Extend `views-generate-data`, or introduce a new derivation pipeline (e.g., MCP server, SQLite index). Mark the writer; preserve the four invariants.
3. **Does the component render or query layer-2 derived state?** → It belongs in **layer 3** (or a layer-3 sibling — MCP-driven tool, dashboard, etc.). It must be read-only.
4. **Does the component need to mutate layer-1 state?** → Add or modify a **skill**. Skills are the only legitimate writers to layer 1.

### 8.2 Anti-patterns to reject

- "Stash this small piece of state in `views/build/data/` because it's convenient" → no. If it's facts, layer 1. If it's UI state, browser-local (localStorage), not the cache.
- "Have the browser POST back to a small server endpoint to update X" → no. Browser → Claude → skill → layer 1.
- "Replicate part of the cache into a config file Claude reads" → no. Claude reads layer 1 directly. The cache is for the SPA only.
- "Add a database that owns part of the truth" → reconsider. A database is fine as a derived layer (layer 2 sibling) but never as the truth. Markdown stays canonical.

---

## 9. References

### 9.1 Decisions and principles
- `adrs/adr-0001-claude-native-approach.md` — Claude-native approach; markdown as truth
- `adrs/adr-0002-v02-packaging.md` — v0.2 packaging; in-place implementation in `CONSTRUCT-CLAUDE-impl/`

### 9.2 Specifications
- `prd.md` — v0.1 PRD (Claude-native agent system)
- `prd-v02-live-views.md` — v0.2 PRD (live views)
- `spec-v02-runtime-topology.md` — server lifecycle, routing, cloud-future seam
- `spec-v02-data-model.md` — JSON cache contract; the load-bearing artefact for layer 2

### 9.3 Reference tables
- `references/epistemic-types.md`, `connection-types.md`, `lifecycle-states.md`, `confidence-levels.md`, `source-tiers.md` — vocabulary shared across all three layers

### 9.4 Implementation
- `../CONSTRUCT-CLAUDE-impl/` — runtime source (agents, skills, workflows, templates)
- `../CONSTRUCT-CLAUDE-impl/VERSION` — global version marker
