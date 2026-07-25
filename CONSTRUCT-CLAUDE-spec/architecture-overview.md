# CONSTRUCT — Architectural Overview

**Status:** Draft (Living)
**Date:** 2026-04-27
**Scope:** Project-wide runtime layer model (ADR-0003 L0–L4) and component layering
**Related:** `adrs/adr-0001-claude-native-approach.md` · `adrs/adr-0002-v02-packaging.md` · `prd.md` · `prd-v02-live-views.md` · `spec-v02-runtime-topology.md` · `spec-v02-data-model.md` · `adrs/adr-0003-v03-pipeline-v04-ui.md` · `adrs/adr-0004-durable-workflow-checkpoints.md` · `adrs/adr-0005-views-refresh-ownership.md`

---

## 1. Purpose

This document captures the runtime architecture that underpins CONSTRUCT: the **L0–L4 layer model** established in ADR-0003, in which skill specifications, the workspace source-of-truth, a Python pipeline runtime, an invoke surface, and (in v0.5) a UI shell stack into one runtime with LLM gates as a cross-cutting concern. Threaded through that stack is a **strictly one-way data-flow property**: the workspace is canonical, derived view data is generated from it, and presentation reads derived view data — never the reverse.

It exists so future contributors — human or Claude — have a single place to understand *why* the directory layout looks the way it does, *which runtime layer owns what*, and *where new components should fit*.

This document does not replace the PRD, ADRs, or per-feature specs. It is the architectural lens through which they should be read. Its layer numbering is ADR-0003's `Layer model (permanent)` block, adopted verbatim; there is exactly one "Layer N" vocabulary in CONSTRUCT and it is defined here.

---

## 2. The Pattern in One Sentence

> **CONSTRUCT is a five-layer runtime — skill specs (L0), workspace source-of-truth (L1), a Python pipeline runtime (L2), an invoke surface (L3), and a UI shell (L4) — across which data flows strictly one way: the workspace is canonical, derived view data is generated from it, and presentation only ever reads.**

Workspace → derived view data → presentation. Never the reverse. Anything that wants to change canonical state (Layer 1) goes through the Python pipeline runtime (Layer 2), reached through the invoke surface (Layer 3) — not through derived view data or the browser.

---

## 3. The Layer Model (L0–L4)

CONSTRUCT's runtime is the permanent layer stack defined in `adrs/adr-0003-v03-pipeline-v04-ui.md`. This is the single "Layer N" vocabulary used everywhere in the project.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4 — UI SHELL  (v0.5)                                         │
│  Forms, buttons, dashboards, review modals.                         │
│  Calls Layer 3; never writes the workspace directly.               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  invokes capabilities
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3 — INVOKE SURFACE                                           │
│  CLI (first) → MCP → HTTP (v0.5), one capability registry.          │
│  Strict input/output schemas; 1:1 with catalog capabilities.       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  dispatches to handlers
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2 — PYTHON PIPELINE RUNTIME                                  │
│  Workflows, orchestration, validation, file I/O.                    │
│  Owns every write to Layer 1; generates derived view data.          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  reads / writes
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1 — WORKSPACE SOT  (the only source of truth)               │
│  Workspace files on the filesystem:                                 │
│    cards/*.md, connections.json, refs/*.json, digests/*.md,         │
│    publish/*.md, log/events.jsonl, curation-reports/*.md,           │
│    domains.yaml, governance.yaml, search-seeds.json                 │
│  Survives all derived/presentation state being deleted.             │
└──────────────────────────────▲──────────────────────────────────────┘
                               │  authoritative *what*
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 0 — SKILL SPECIFICATIONS                                    │
│  SKILL.md + artifact catalog (procedure + audit).                   │
│  Authoritative *what*; Layer 2 is authoritative *how* for PIPE.     │
└─────────────────────────────────────────────────────────────────────┘

  LLM gates (cross-cutting) — invoked only at declared boundaries
  (relevance scoring, promotion calls, ambiguous connection typing).
```

**The one-way data-flow property (a property of the stack, not a competing numbering):**

```
   Layer 1 workspace SOT ──► derived view data ──► presentation (Layer 4 UI shell)
        (canonical)          (generated by L2)       (read-only consumer)
```

Derived view data (`views/build/data/*.json`, `views/build/version.json`) is a **presentation cache** generated by the Layer 2 Python runtime from Layer 1. It is never a "Layer 2" of its own — Layer 2 is the Python runtime that *produces* it. The one-way arrows above are governed by the four invariants in §4.

### 3.0 Layer 0 — Skill Specifications

`SKILL.md` files plus the artifact catalog describe *what* each capability does and audit its steps. Skills are thin wrappers: post-v0.4 they own conversation and orchestration and delegate every side effect to the Python runtime through the invoke surface. They are authoritative for the *what*; Layer 2 is authoritative for the *how* of deterministic (PIPE) work.

### 3.1 Layer 1 — Workspace SOT

The workspace is the **only source of truth**. Every fact CONSTRUCT knows lives in a markdown, YAML, or JSON file that a human can read with a text editor. There is no database, no opaque store, no network-hosted state of record.

**Layer 2 (the Python runtime) owns every write to layer 1.** Skills, the CLI, MCP clients, and the future UI shell do not write workspace files themselves — they reach layer 1 only by invoking registered capabilities through the invoke surface (Layer 3). The capability registry is the single write contract: `catalog.py` registers the capabilities whose handlers create and edit cards, add connections, and run `research.run` / `curation.run` / `daily.run`, and every such write lands through one of those handlers. Skills like `card-create`, `card-edit`, `research-cycle`, `curation-cycle` are thin wrappers that delegate to those capabilities (Phase 12 API-04); they no longer touch workspace files directly. The user does not edit derived view data or presentation state — they ask Claude, Claude invokes a capability, and the runtime updates layer 1.

This is the principle established in ADR-0001: *"markdown is the truth, everything else is derived."* — with the v0.4 refinement that the deterministic writer of that truth is the Python runtime, not the skill layer.

### 3.2 Layer 2 — Python Pipeline Runtime

The Python pipeline runtime (`src/construct/`) performs workflows, orchestration, validation, and file I/O. Its capability registry (`catalog.py`) registers the live capabilities whose handlers create and edit cards, add connections, run `research.run` / `curation.run` / `daily.run`, and generate derived view data. `daily.run` is a thin synchronous Python composition over frozen children (`research.run` → `curation.run` → `graph.status`) with no parent LangGraph graph — each child owns its own checkpointer and typed result (Phase 13 D-09).

Among its outputs is **derived view data**: `views/build/data/` holds JSON generated from layer 1, shaped for the SPA's consumption, sorted for stable rendering, with computed aggregates inlined. It contains no facts that aren't ultimately traceable to layer 1.

Only one code path writes derived view data: the runtime's views generator. Every other component reads it (or doesn't touch it at all). Derived view data is treated as ephemeral. Deleting the entire `views/build/data/` directory is a no-op for the system's truth — regenerating it rebuilds it byte-identically. Ownership of the post-run views refresh sits in this layer (`adrs/adr-0005-views-refresh-ownership.md`).

### 3.3 Layer 3 — Invoke Surface

The invoke surface is **one capability contract behind multiple adapters**: CLI first, then MCP, then HTTP in v0.5. Each adapter calls the same capability registry in Layer 2 with strict input/output schemas; MCP tools and CLI subcommands are 1:1 with catalog capabilities, not freeform prompts. This is the single door through which skills, agents, and the future UI reach the Python runtime.

### 3.4 Layer 4 — UI Shell (v0.5) and Presentation

The presentation surface is the SPA in `views/build/{index.html, assets/}` — a static React app that fetches derived view data and renders it. It has no backend of its own and it cannot write. There is no PUT, POST, or DELETE path back into canonical state anywhere in the system.

Any future feature that *appears* to be "editing in the browser" must architecturally route as: browser action → invoke surface (Layer 3) → Python runtime (Layer 2) mutates layer 1 → runtime regenerates derived view data → browser fetches fresh data on reload (or on `UPDATE`-flag click).

---

## 4. The Four Invariants

These invariants keep the one-way data-flow property intact: they govern the relationship between the **workspace SOT (Layer 1)** and the **derived view data** the Python runtime generates from it. Every architectural decision in CONSTRUCT must preserve them.

| # | Invariant | Test |
|---|---|---|
| **I1** | **Single-writer** to derived view data. Only the Layer 2 runtime's views generator writes to `views/build/data/`. | Codebase grep for writes to that path returns one owner in the Python runtime. |
| **I2** | **Read-only direction** for presentation. The SPA (Layer 4) never writes back. No backend accepts writes into canonical state. | No PUT/POST/DELETE handlers exist. SPA has no fetch with non-GET method. |
| **I3** | **Safe-delete** invariant for derived view data. `rm -rf views/build/data/` followed by a views regeneration produces byte-identical output. | Hash-and-compare two regenerations across a delete. |
| **I4** | **No-novel-data** invariant for derived view data. Every field in every JSON file has a documented derivation rule from layer 1. | For each schema field, `spec-v02-data-model.md` traces it to a workspace artefact or a documented computation. |

Violating any of these is a bug, not a feature.

---

## 5. Why One-Way Flow Matters

### 5.1 Recoverability

Any derived or presentation state can be lost without losing knowledge. Delete the whole `views/` directory; the workspace is intact. Lose the browser cache; the workspace is intact. A bug in the views generator produces wrong JSON; the workspace is intact.

This makes derived view data and presentation **fully disposable**. That property is rare and valuable.

### 5.2 Multiple readers, one writer for derived view data

The property admits any number of Layer 2 derivers writing into different cache locations from the same canonical source. Today: the runtime's views generator writing for the SPA. Tomorrow: an MCP-exposed query surface reading layer 1; a SQLite indexer writing to a queryable cache. Each new derived pathway is additive — none of them displaces canonical state.

It also admits any number of presentation consumers. The current SPA is one; a future Claude Design dashboard, an artifact view, or a native desktop UI would each read from the same derived view data (or run their own derivation directly off layer 1 through the Python runtime).

### 5.3 Cloud topology preservation

`spec-v02-runtime-topology.md` §9 describes the local-vs-cloud topologies side-by-side. The property is **identical** across both:

- Local: layer 1 on user's filesystem, derived view data in `views/build/data/`, presentation served by `npx serve` on localhost.
- Cloud: layer 1 in cloud storage, derived view data on a CDN, presentation fetched by browser over HTTPS.

What changes is *where* each layer lives. What stays the same is *the directionality* and the JSON contract between the workspace and derived view data. **Because writes can only target layer 1 through the Python runtime**, no writes need a return path through CDN or browser. The cloud topology is feasible *because* of the invariants.

### 5.4 Predictable failure modes

Most failures in derived or presentation state are reversible by re-deriving. A corrupt derived-view-data JSON file is fixed by regenerating it. A wrong build is fixed by rebuilding the SPA. Only failures that touch layer 1 (a runtime bug that writes bad workspace state) require manual recovery — and the workspace is markdown, so manual recovery is editing a text file.

---

## 6. Topology Variants

### 6.1 Local (today)

```
┌─ User's machine ─────────────────────────────────────────────────┐
│                                                                  │
│  Skills (Layer 0) / Claude ── invoke surface (Layer 3) ──┐       │
│                                                          ▼       │
│  Python pipeline runtime (Layer 2, layer-1 writer)               │
│         │                                                        │
│         │ mutates                                                │
│         ▼                                                        │
│  cosmology/, climate-policy/, ...   ◄── layer 1 (workspace SOT) │
│         │                                                        │
│         │ views generator (Layer 2)                              │
│         ▼                                                        │
│  views/build/data/*.json            ◄── derived view data       │
│  views/build/{html, assets}         ◄── Layer 4 (built SPA)     │
│         │                                                        │
│         │ npx serve                                              │
│         ▼                                                        │
│  localhost:3001                                                  │
│         │                                                        │
│         │ HTTP GET (read only)                                   │
│         ▼                                                        │
│  Browser (Layer 4 presentation)                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Cloud (v0.5+ horizon)

```
┌─ Cloud ─────────────────────────────────────────┐  ┌─ Browser ─┐
│                                                 │  │           │
│  Python runtime (Layer 2, layer-1 writer)       │  │  Layer 4  │
│         │                                       │  │           │
│         ▼                                       │  └─────▲─────┘
│  Cloud workspace storage   ◄── layer 1          │        │ HTTPS
│         │                                       │        │
│         │ views generator (Layer 2)             │        │
│         ▼                                       │        │
│  Static asset host (CDN)   ◄── derived view data│────────┘
│                            + assets             │
└─────────────────────────────────────────────────┘
```

What changes between (a) and (b): infrastructure ownership, transport, network boundaries.
What is identical: the L0–L4 stack, the four invariants, the workspace → derived-view-data JSON contract.

### 6.3 Hybrid (an MCP-exposed query pathway)

Per ADR-0001 §"Future Enhancements" and ADR-0003's invoke-surface model, an MCP adapter sits on Layer 3 and lets agents query layer 1 through the Python runtime, exposing tool calls for filtered queries. The MCP adapter is **not** a new layer — it is another Layer 3 adapter over the same capability registry, and any cache it exposes for agent consumption is a sibling derived-view-data pathway, optimised for agents rather than the browser.

```
                Skills / Claude / Cursor
                  │  CLI + MCP (Layer 3 adapters)
                  ▼
                Python pipeline runtime (Layer 2)
                  │            │
                  │            └── MCP query tools ───┐
                  │ views generator                   │
                  ▼                              ┌────▼────────────┐
                views/build/data/                │ agent query     │
                (derived view data — for SPA)    │ cache (derived  │
                                                 │  view data)     │
                                                 └─────────────────┘
```

Same property. Two derivation pathways, one canonical source, one runtime that owns writes.

---

## 7. Where Components Live Today

| Path | Layer | Role |
|---|---|---|
| `~/my-construct/<workspace>/` | 1 | Workspace canonical state / SOT (one per research domain) |
| `src/construct/` | 2 | Python pipeline runtime — capability registry, workflows, validation, file I/O |
| `src/construct/cli.py`, `src/construct/mcp/` | 3 | Invoke surface — CLI and MCP adapters over one capability registry |
| `~/my-construct/.construct/` | 0 | Skill specs, agents, workflows, references, templates (Layer 0 + config) |
| `~/my-construct/AGENTS.md` | (config) | Boots Claude as CONSTRUCT |
| `~/my-construct/views/src/` | (source) | Layer 4 SPA source (JSX, components, pages, Vite config) |
| `~/my-construct/views/build/` | 4 | Compiled SPA bundle (HTML, JS, CSS) — presentation |
| `~/my-construct/views/build/data/` | **derived view data** | JSON generated by the Layer 2 runtime for the SPA |
| `~/my-construct/views/build/version.json` | **derived view data** | Build identity stamp; SPA polls this |
| `~/my-construct/views/server.pid` | (runtime) | PID of the running `npx serve` process |
| `~/my-construct/views/design-example/` | (reference) | Read-only visual prototype, never served |

---

## 8. Adding New Components — Where Should X Go?

Use this as a checklist before introducing any new component.

### 8.1 Decision tree

1. **Does the component contain facts that didn't exist before?** → It belongs in **layer 1** (workspace SOT). Persist it as markdown, YAML, or JSON. Mutate it through the Python runtime (Layer 2) via the invoke surface, never directly through a UI.
2. **Is the component a re-shaped or pre-computed view of layer-1 facts?** → It is **derived view data**, generated by the Layer 2 runtime. Extend the views generator, or introduce a new derivation pipeline (e.g., MCP query cache, SQLite index) inside Layer 2. Mark the writer; preserve the four invariants.
3. **Does the component render or query derived view data?** → It belongs in **presentation (Layer 4)** or a Layer 3 read adapter (MCP-driven tool, dashboard, etc.). It must be read-only with respect to canonical state.
4. **Does the component need to mutate layer-1 state?** → Add or modify a **registered capability in the Python runtime (Layer 2)** and invoke it through the invoke surface (Layer 3). The runtime owns every write to layer 1; a skill, the CLI, MCP, or the UI participates only by calling that capability — none of them writes workspace files directly.

### 8.2 Anti-patterns to reject

- "Stash this small piece of state in `views/build/data/` because it's convenient" → no. If it's facts, layer 1. If it's UI state, browser-local (localStorage), not derived view data.
- "Have the browser POST back to a small server endpoint to update X" → no. Browser → invoke surface (Layer 3) → Python runtime (Layer 2) → layer 1.
- "Replicate part of derived view data into a config file Claude reads" → no. The runtime reads layer 1 directly. Derived view data is for the SPA only.
- "Add a database that owns part of the truth" → reconsider. A database is fine as a derived pathway (a Layer 2 output) but never as the truth. Markdown stays canonical. One sanctioned carve-out exists: workflow orchestration state in `.construct/workflow/*.sqlite`, which holds pending human-review decisions that are not reconstructible from layer 1 — it sits outside the layer model rather than violating it. See `adrs/adr-0004-durable-workflow-checkpoints.md`.

---

## 9. References

### 9.1 Decisions and principles
- `adrs/adr-0001-claude-native-approach.md` — Claude-native approach; markdown as truth
- `adrs/adr-0002-v02-packaging.md` — v0.2 packaging; in-place implementation in `CONSTRUCT-CLAUDE-impl/`
- `adrs/adr-0003-v03-pipeline-v04-ui.md` — the L0–L4 layer model; invoke surfaces and LangGraph for the LLM layer
- `adrs/adr-0004-durable-workflow-checkpoints.md` — durable workflow checkpoints as sanctioned orchestration state
- `adrs/adr-0005-views-refresh-ownership.md` — the Python runtime layer owns the derived-view-data refresh

### 9.2 Specifications
- `prd.md` — v0.1 PRD (Claude-native agent system)
- `prd-v02-live-views.md` — v0.2 PRD (live views)
- `spec-v02-runtime-topology.md` — server lifecycle, routing, cloud-future seam
- `spec-v02-data-model.md` — derived-view-data JSON contract; the load-bearing artefact for the derivation from layer 1

### 9.3 Reference tables
- `references/epistemic-types.md`, `connection-types.md`, `lifecycle-states.md`, `confidence-levels.md`, `source-tiers.md` — vocabulary shared across all layers

### 9.4 Implementation
- `../CONSTRUCT-CLAUDE-impl/` — runtime source (agents, skills, workflows, templates)
- `../CONSTRUCT-CLAUDE-impl/VERSION` — global version marker
