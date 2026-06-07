# Architecture Patterns

**Domain:** Local-first agentic knowledge system
**Project:** CONSTRUCT
**Researched:** 2026-04-22
**Confidence:** HIGH — based primarily on the project PRD, repo topology, development strategy, and schema specs.

## Recommended Architecture

CONSTRUCT v0.1 should be a **layered local-first system with a narrow write path and a derived-read pipeline**:

1. **Workspace source of truth**: markdown cards, YAML configs, refs, workflows, event log, and connection records live on disk and remain human-readable.
2. **Core Python runtime**: one Python package owns orchestration, storage access, graph derivation, workflow execution, and UI-serving.
3. **Derived state layer**: SQLite/FTS indexes, NetworkX graph objects, and `views/` JSON are rebuildable projections, never canonical state.
4. **Interaction surfaces**: CLI, chat/WebSocket, and React UI all call the same internal application services.
5. **Governed write-back**: UI and future integrations never mutate source files directly; they submit structured actions that the runtime validates and applies.

That architecture keeps v0.1 minimal while preserving the most important future boundary: **core capabilities live behind stable Python services, while `views/` acts as the read contract and the inbox/action path acts as the write contract**.

## Architectural Thesis

The coherence rule for CONSTRUCT should be:

> **Markdown/YAML are canonical, everything else is derived, and every external surface talks to the same application layer instead of talking to files directly.**

This prevents the most likely v0.1 failure mode: accidentally building three systems at once (CLI logic, UI logic, and agent logic) that all bypass each other.

## System Shape

```text
User / Future Host Integration
        │
        ├─ CLI
        ├─ Chat / WebSocket
        └─ React UI
              │
              ▼
      Application Service Layer
  (commands, queries, workflows, governance)
              │
      ┌───────┼────────┬───────────────┬──────────────┐
      ▼       ▼        ▼               ▼              ▼
  Runtime   Storage   Graph         Views         Integrations
  /Agents    APIs     Engine       Pipeline      Adapters later
      │       │        │               │
      └───────┴────────┴──────┬────────┘
                              ▼
                   Workspace Source of Truth
      cards/ + connections.json + domains.yaml + governance.yaml
      model-routing.yaml + refs/ + workflows/ + log/events.jsonl

Derived, rebuildable artifacts:
  db/ (SQLite + FTS5), in-memory graph state, views/*.json
```

## Component Boundaries

| Component | Responsibility | Reads | Writes | Must Not Do |
|-----------|---------------|-------|--------|-------------|
| **Workspace SOT** | Canonical persistent knowledge/config state | — | markdown/YAML/JSON canonical files | Contain derived UI or index-only data |
| **Storage layer** | Parse, validate, load, persist canonical artifacts; rebuild SQLite | Workspace SOT | Workspace SOT, `db/` | Embed business rules in file handlers |
| **Graph engine** | Build derived NetworkX graph, metrics, traversal, bridge/orphan detection | Storage-loaded canonical entities | in-memory graph, serialized graph view | Read raw files directly from UI/agent code |
| **Core runtime / agents** | Sessions, heartbeat, task delegation, research/curation execution, logging | Storage APIs, graph/query APIs, workflow defs | events, inbox processing outcomes, canonical changes via storage | Own schema parsing or bypass governance |
| **Views pipeline** | Render denormalized read models for UI | Storage entities, graph metrics, event log, agent status | `views/*.json` only | Contain canonical business state |
| **Application service layer** | Shared command/query API for CLI, chat, and UI actions | All core modules | Delegates to runtime/storage/views | Duplicate logic inside each interface |
| **React UI** | Visualize graph/cards/status; submit user actions; display responses | `views/*.json`, websocket updates | inbox actions only | Read raw workspace files or mutate SOT directly |
| **Future integration boundary** | MCP/adapters later | Application services + views | structured commands/actions | Reach into workspace internals |

## Required Internal Layering

### 1. Canonical memory/storage interface

Everything that touches `cards/`, `connections.json`, config files, refs, or events should go through a single storage API. Even internal agent code should not open files directly.

**Why:** this is the cheapest way to preserve future MCP/external adapter support and keep rebuild behavior consistent.

### 2. Explicit application services above modules

Define programmatic use-cases like:

- `initialize_workspace()`
- `rebuild_indexes()`
- `build_graph_snapshot()`
- `get_graph_stats()`
- `submit_action()`
- `process_inbox()`
- `run_research_cycle()`
- `render_views()`

CLI commands, chat handlers, and UI write-backs should be thin wrappers over these services.

### 3. Read model / write model split

- **Write model**: canonical workspace files + validated action requests
- **Read model**: `views/*.json`, graph snapshots, status summaries, FTS query results

This is not full CQRS, but a lightweight version of it. That is the right amount of architecture for v0.1.

## Data Flow

### Primary write flow

```text
Human / UI / Chat / CLI intent
  → application service
  → governance / workflow / agent decision
  → storage validation + canonical write
  → event log append
  → derived rebuilds (db / graph / views)
  → UI reads refreshed views
```

### React UI flow

```text
views/*.json + websocket notifications
  → Zustand/UI state
  → user action
  → inbox/action-*.json or command endpoint
  → runtime processes action
  → canonical state changes
  → heartbeat or on-demand render updates views/
  → UI reflects result + responses.json message
```

### Research flow

```text
search-seeds.json + domain config
  → researcher fetch/extract
  → refs/*.json written
  → candidate cards/connections proposed
  → curator/governance validates
  → cards/ + connections.json updated
  → index rebuild / graph rebuild / views rebuild
```

### Graph derivation flow

```text
cards/ + connections.json + domains metadata
  → storage loaders / schema validation
  → graph builder
  → NetworkX graph
  → query/metrics
  → graph.json + landscape.json + card denormalization
```

## Directionality Rules

To keep the architecture coherent, dependencies should only point downward:

- UI depends on `views/` and service endpoints, never on workspace file formats.
- Application services depend on runtime/storage/graph/views modules.
- Runtime depends on storage + graph + workflow + provider abstractions.
- Graph depends on validated domain entities, not on UI types.
- Storage depends on schemas and filesystem, not on agents or UI.

**Forbidden directions:**

- UI directly editing cards/config
- graph module importing React/UI schemas
- storage layer invoking LLMs
- CLI/chat implementing business logic not available programmatically
- views pipeline becoming a shadow source of truth

## Minimal v0.1 Module Map

Recommended package shape inside `src/construct/`:

| Module | v0.1 role | Keep in v0.1? |
|--------|-----------|---------------|
| `schemas/` | Pydantic models for SOT, inbox, events, views | Yes — essential |
| `storage/` | canonical load/save/rebuild/index APIs | Yes |
| `graph/` | graph construction, metrics, query helpers | Yes |
| `agents/` | orchestrator, curator, researcher, session loop, llm routing | Yes, but keep behaviors modest |
| `views/` | render disposable JSON read models | Yes |
| `services/` | thin application use-cases for all interfaces | **Add explicitly** |
| `server/` | HTTP static serving + websocket endpoints | Yes |
| `cli/` | thin shell over services | Yes |
| `integrations/` | future adapters/MCP wrappers | No for v0.1, reserve namespace only if helpful |

The main architectural recommendation here is to **add an explicit `services/` layer**, even if small. It will keep the rest of v0.1 from coupling CLI, server, and agents together.

## Patterns to Follow

### Pattern 1: Canonical-on-disk, derived-in-code
**What:** Treat markdown/YAML/JSON workspace artifacts as authoritative and everything else as rebuildable projections.

**When:** Always, especially for graph state, search indexes, and UI payloads.

**Why:** Makes git diffs meaningful, keeps recovery simple, and avoids hidden state.

### Pattern 2: Thin interfaces, fat services
**What:** CLI commands, websocket handlers, and inbox consumers should validate input and delegate immediately.

**When:** For every user-triggered action.

**Why:** Prevents interface-specific logic drift.

### Pattern 3: Heartbeat-backed read models
**What:** Use a deterministic render step to generate UI-ready artifacts from current canonical state.

**When:** Graph view, dashboards, activity timeline, card details, agent status.

**Why:** Lets the React app stay simple and keeps the future API boundary obvious.

### Pattern 4: Governed async write-back
**What:** UI writes requests, not state. Runtime evaluates and applies them.

**When:** Promotions, edits, config changes, connection suggestions, research triggers.

**Why:** Preserves auditability and keeps human/agent actions in one pipeline.

### Pattern 5: Stable internal contracts before external integrations
**What:** Expose capabilities through Python callables and schema-backed inputs/outputs now, before MCP or adapters exist.

**When:** Any command/query likely to be used by future hosts.

**Why:** Makes v0.2 integration a wrapper exercise, not a rewrite.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Three business logic copies
**What:** CLI has one implementation, chat another, and UI actions a third.

**Why bad:** Behavior diverges fast and testing becomes impossible.

**Instead:** one service layer with multiple thin shells.

### Anti-Pattern 2: UI coupled to workspace internals
**What:** React parses markdown or knows file layout details.

**Why bad:** Any workspace/schema evolution breaks the frontend.

**Instead:** UI consumes `views/` contracts only.

### Anti-Pattern 3: Hidden mutable runtime state
**What:** Session memory contains graph or card truth not written back to disk.

**Why bad:** Restart behavior becomes lossy and non-deterministic.

**Instead:** persist canonical outcomes, derive everything else.

### Anti-Pattern 4: Over-building the agent framework in v0.1
**What:** complex multi-agent abstractions before real research/curation flows exist.

**Why bad:** burns time in infrastructure instead of proving product value.

**Instead:** simple orchestrator + curator + researcher with schema-backed tasks.

### Anti-Pattern 5: Premature integration abstraction
**What:** building plugin systems or generalized remote APIs in v0.1.

**Why bad:** adds weight before any adapter exists.

**Instead:** preserve seams now; ship adapters later.

## Suggested Build Order

The roadmap should preserve this order because each later component depends on the previous contract being real:

1. **Schemas + storage foundation**
   - Lock canonical card/config/action/view schemas.
   - Build loaders, validators, canonical write APIs, SQLite rebuild path.
   - This makes every later module operate on typed data instead of ad hoc parsing.

2. **Application services + CLI shell**
   - Add shared commands/queries early.
   - Make `construct rebuild`, `construct status`, and graph stats flow through services.
   - This prevents interface drift from the start.

3. **Graph engine**
   - Build graph from validated canonical data, not direct markdown parsing in multiple places.
   - Add graph metrics and D3 serialization.

4. **Session/runtime skeleton**
   - Heartbeat, event logging, provider routing, stub agents.
   - Keep agent behavior simple until storage and graph contracts are stable.

5. **Views pipeline**
   - Render graph/card/status/event views from the canonical + derived state.
   - Contract-test every emitted file.

6. **Server + React UI**
   - Serve static app, stream events, read only from `views/`.
   - Add inbox/action submission after read path is stable.

7. **Governed write-back + real research/curation loops**
   - Introduce inbox processing, real agent actions, and richer workflows.

## Why This Build Order Matters

- **Storage before runtime** prevents agent code from inventing accidental schemas.
- **Services before UI** ensures future integrations reuse the same callable surface.
- **Graph before views** keeps UI artifacts derived from one real graph engine.
- **Views before rich UI** makes frontend work mostly a contract-consumption problem.
- **Real agents after scaffolding** keeps v0.1 focused on usable product slices, not agent framework theory.

## Forward-Compatibility Constraints That Matter in v0.1

These constraints are worth enforcing immediately because violating them in v0.1 would make future integrations expensive:

| Constraint | v0.1 rule |
|-----------|------------|
| **Stable internal API** | All core capabilities must be exposed as Python callables outside CLI/chat code. |
| **No direct file access outside storage** | Agents, services, and integrations use storage interfaces, not raw file I/O. |
| **`views/` is read-only projection** | UI and adapters can consume it, but no business state originates there. |
| **Inbox/actions are schema-backed** | Every write-back request has an ID, schema, source, and auditable lifecycle. |
| **Schema-first contracts** | Pydantic models generate JSON Schema and TS types; hand-written parallel schemas are avoided. |
| **Namespaced workflow metadata** | Any CONSTRUCT-specific `SKILL.md` keys use a `construct.*` prefix to stay portable. |
| **Addressable HITL state** | Questions, approvals, and responses need IDs, not ephemeral chat-only context. |
| **Replaceable transport** | React/WebSocket is one surface; service contracts cannot assume the browser is the only caller. |

## Practical Boundary Decisions for v0.1

### Core runtime
- Own orchestration, scheduling, event logging, and task execution.
- Do not let it become the storage parser or UI formatter.

### Storage + schemas
- Own canonical validation and persistence semantics.
- Keep SQLite as a query accelerator, not a second source of truth.

### Graph engine
- Own structural intelligence: components, bridges, orphans, path queries, serialization primitives.
- Do not embed UI concerns beyond output adapters such as node-link serialization.

### Views pipeline
- Own denormalization and view shaping.
- Do not make business decisions; just project current state.

### React UI
- Own interaction ergonomics, local display state, and visual exploration.
- Treat agent decisions and knowledge edits as remote/governed operations, even though everything is local.

## Roadmap Implications

Recommended architecture-driven phase structure:

1. **Canonical data and contracts**
   - schemas, storage, rebuild, type generation
2. **Shared service layer and CLI**
   - one callable API for all interfaces
3. **Graph derivation and metrics**
   - NetworkX build/query/serialize
4. **Runtime and heartbeat skeleton**
   - session loop, eventing, stubs
5. **Views contract**
   - graph/cards/landscape/status/events/responses
6. **UI read path**
   - browser visualization from `views/`
7. **UI write-back + agent execution**
   - inbox, governance, curator/researcher real flows
8. **Future integration surface**
   - MCP/adapters only after the internal API is proven

## Architecture Risks / Research Flags

| Topic | Risk | Recommendation |
|------|------|----------------|
| Service layer omitted | Interface-specific logic duplication | Create `services/` in the first implementation milestone |
| Connections split unclear | Graph edges may drift between card frontmatter and `connections.json` | Pick one canonical edge authority early and enforce it |
| Heartbeat-only updates | UI may feel stale or complex to reason about | Support heartbeat first, but keep on-demand render trigger available |
| WebSocket scope creep | Server complexity may outpace value | Use websocket only for chat/events; keep views as file/HTTP contract |
| Agent framework ambition | Runtime may become over-abstracted | Ship concrete orchestrator/curator/researcher flows before abstractions |

## Recommended Decision Summary

For v0.1, CONSTRUCT should be built as a **Python monolith with strict internal boundaries**:

- **workspace files are the canonical write model**
- **SQLite, NetworkX, and `views/` are derived projections**
- **a small application service layer is the shared entrypoint for CLI, chat, and UI**
- **React reads `views/` and writes only structured actions**
- **future integrations wrap the same service/contracts rather than touching internals**

That is the minimal architecture that stays coherent now and does not corner the project later.

## Sources

- `.planning/PROJECT.md` — project constraints and key decisions
- `CONSTRUCT-spec/construct-prd.md` — architecture, storage, interaction model, forward-compatibility constraints
- `CONSTRUCT-spec/construct-repo-topology.md` — package layout and module ownership
- `CONSTRUCT-spec/construct-development-strategy.md` — dependency ordering and phase structure
- `CONSTRUCT-spec/construct-data-schemas.md` — canonical contracts between runtime, views, and UI
