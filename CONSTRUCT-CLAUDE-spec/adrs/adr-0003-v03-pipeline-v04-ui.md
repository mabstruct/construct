# ADR-0003: Layered Pipeline (v0.3) Then UI-Primary (v0.4)

**Status:** Accepted  
**Date:** 2026-06-07  
**Amended:** 2026-06-07 — invoke surfaces (CLI → MCP), UI spike path, LangGraph for LLM layer  
**Deciders:** ;-)mab  
**Context:** CONSTRUCT03 planning originally framed a single jump to UI-as-primary-interface. Implementation experience (v0.1 Claude-native skills, v0.2 views SPA, artifact catalog audit) showed that durable UI requires a testable backend first. This ADR splits delivery into two product versions and defines the layered runtime architecture.

**Supersedes (partially):** The monolithic “CONSTRUCT03 = UI shell in one step” framing in [`CONSTRUCT-CLAUDE-v03-planning/README.md`](../../CONSTRUCT-CLAUDE-v03-planning/README.md). That directory now tracks **v0.3 planning**; v0.4 UI work gets its own planning cycle once v0.3 pipelines ship.

**Related:** [`artifact-catalog.md`](../artifact-catalog.md) (PIPE / UI / LLM / HYB audit), [`adr-0001-claude-native-approach.md`](adr-0001-claude-native-approach.md), [`adr-0002-v02-packaging.md`](adr-0002-v02-packaging.md), archived [`archive/v01-python/spec/adrs/adr-0001-python-first-drop-openclaw.md`](../../archive/v01-python/spec/adrs/adr-0001-python-first-drop-openclaw.md)

---

## Context

### Where we are

| Version | What shipped |
|---------|--------------|
| **v0.1** | Claude-native configuration — skills, workflows, agents; chat-as-primary-interface |
| **v0.2** | Local views SPA + `views-*` skills; derived JSON from workspace SOT |
| **v0.3 (planned)** | Hardened capabilities, Python pipeline runtime, testable API/CLI |
| **v0.4 (planned)** | UI-as-primary — structured controls call v0.3 pipelines |

The [`artifact-catalog.md`](../artifact-catalog.md) CONSTRUCT03 audit classifies every skill as `UI`, `PIPE`, `LLM`, or `HYB`. Attempting to build all `UI` affordances before `PIPE` implementations exist produces untestable UI and chat-shaped backends.

### What failed in the monolithic CONSTRUCT03 plan

- **UI without contracts** — buttons need stable invoke targets (inputs, outputs, errors, progress).
- **Skills as opaque chat procedures** — hard to regression-test; behavior drifts from spec.
- **Python v0.1 archived but not reused** — `src/construct/` already has schemas, validation, init; v0.2 already embeds Python in `views-generate-data`.
- **Claude doing deterministic work** — wastes model capacity on validation, parsing, file I/O that should be code.

### What we want

1. **Workspace files remain canonical** — same SOT as today (`cards/`, `connections.json`, etc.).
2. **Deterministic work in Python** — testable, spec-aligned, CI-friendly.
3. **LLM only when needed** — explicit gates, not ambient chat for every operation.
4. **UI last** — v0.4 builds on proven pipelines; browser UI may extend v0.2 views, spike via Streamlit, or adopt CoPilotKit (see Amendment A below).

---

## Amendment A (2026-06-07) — Invoke surfaces, UI spike, LangGraph

Follow-up decisions from v0.3/v0.4 planning discussion.

### A.1 Invoke surfaces — CLI first, then MCP

Layer 3 exposes **one capability contract, multiple adapters**. All adapters call the same Python pipeline core (Layer 2).

| Surface | Priority | Role |
|---------|----------|------|
| **CLI** | **v0.3 tranche 1** | Primary development and CI path (`construct run <capability>`). Contract tests run against CLI. |
| **MCP** | **v0.3 tranche 1–2** | Agentic integration — Claude, Cursor, and other MCP clients invoke capabilities as tools without chat-shaped file ops. Same schemas as CLI. |
| **HTTP** | v0.3 tranche 2 / v0.4 | Browser UI and remote clients; localhost first, cloud-deployable later. |

**Rule:** MCP tools and CLI subcommands are **1:1 with catalog capabilities** — not freeform agent prompts. Skills in `CONSTRUCT-CLAUDE-impl/` become thin wrappers that call MCP or CLI.

```text
Claude / Cursor / other agents
        │ MCP tools
        ▼
Layer 3  CLI ──┐
        MCP ──┼──► same capability registry ──► Layer 2 pipelines
        HTTP ─┘
```

### A.2 Browser UI — spike path (localhost → cloud)

v0.4 remains UI-primary, but **evaluate UI technology before committing**. Three candidates:

| Option | Fit | When |
|--------|-----|------|
| **v0.2 views SPA** (React/Vite) | Read-heavy dashboard already shipped; add write actions via HTTP | v0.4 default if spike confirms fit |
| **Streamlit** | Python-native; fast spike for pipeline ops console, capability runner, gate review on localhost | **v0.3 spike** — validate Layer 3 without building v0.4 chrome |
| **CoPilotKit** | Rich agent+UI patterns; React; heavier; no Java runtime | **v0.4 candidate** if agent-in-the-loop UI (L1/L2 modals, copilot sidebar) needs more than views SPA |

**Decision:** Run a **Streamlit spike in v0.3** as a localhost browser shell over CLI/MCP capabilities (pipeline status, run buttons, gate review). Use spike learnings to choose v0.4 direction: extend views SPA, adopt CoPilotKit, or hybrid (views for graph/read, CoPilotKit for agent panels).

Deployment path: **localhost first** (same as v0.2 views) → optional **cloud webserver** later. No cloud-first architecture in v0.3.

### A.3 LangGraph — LLM orchestration layer (provider-independent)

**Amends:** LangGraph section below — no longer fully deferred.

Adopt **LangGraph for L2 and L3 LLM subgraphs** (talk-to-my-data, in-skill decision gates), not for the deterministic PIPE layer.

| Layer | Technology |
|-------|------------|
| Deterministic PIPE steps | Plain Python in `src/construct/pipelines/` |
| LLM gates (L2, L3) | LangGraph subgraphs with structured inputs/outputs |
| Model provider | Config-driven (YAML/env) — swap Anthropic/OpenAI/Ollama/etc. without pipeline code changes |

**Why LangGraph:** Provider independence is the primary driver — model selection is configuration, not implementation surgery. Multi-step gate flows (retrieve → score → branch → re-retrieve) are the secondary benefit.

**Scope limits (unchanged intent):**

- LangGraph does **not** replace CONSTRUCT identity (`AGENTS.md`), skill catalog, or workspace SOT.
- LangGraph does **not** replace Python for validation, parsing, file I/O, metrics.
- Each LangGraph graph is a **named gate** invoked by the pipeline runner; graphs are unit/integration tested with mocked models where possible.

**LangGraph spike:** **L2 “talk to my data”** — locked for tranche 1.

**Streamlit spike:** **Richer UI** — capability runner + gate review panel — locked for tranche 1.

**MCP transport:** **stdio** (`construct mcp`) — locked for tranche 1; SSE deferred.

**Relationship to archived Python ADR-0001:** LiteLLM-as-routing-layer is superseded for LLM gates by LangGraph + LangChain model init; deterministic layers remain pure Python.

---

## Decision

Adopt a **four-layer architecture** delivered in two product versions:

### Layer model (permanent)

```text
Layer 4  UI shell (v0.4)           Forms, buttons, dashboards, review modals
         │                         Calls Layer 3; never writes SOT directly
Layer 3  Invoke surface           CLI (first) → MCP → HTTP
         │                         Same capability registry; strict schemas
Layer 2  Python pipeline runtime   Workflows, orchestration, validation, file I/O
         │                         Implements PIPE steps; emits progress/events
Layer 1  Workspace SOT             Markdown + JSON (unchanged)
         ▲
Layer 0  Skill specifications      SKILL.md + artifact catalog (procedure + audit)
         │                         Authoritative *what*; Layer 2 is authoritative *how* for PIPE
LLM gates (cross-cutting)            Invoked only at declared boundaries (see below)
```

### v0.3 — Pipeline hardening (backend + API)

**Goal:** Make capabilities **strict, testable, and spec-aligned** before building UI.

| Deliverable | Description |
|-------------|-------------|
| **Hardened skill specs** | Each skill audited: deterministic steps vs LLM gates documented in SKILL.md and catalog |
| **Python pipeline modules** | Revive [`src/construct/`](../../src/construct/) surgically — pipeline runner, validators, parsers, workflow orchestration — not the full v0.1 monolith (no mandatory SQLite/heartbeat/WebSocket in v0.3) |
| **Testable invoke layer** | **CLI first** (`construct run <capability>`); **MCP tools** for agentic clients (same contracts); HTTP later for browser UI |
| **Workflow engine** | Cold Start, Daily Cycle, Co-Authorship as orchestrated pipelines with step progress → `log/events.jsonl` |
| **Claude as test client** | Skills and MCP invoke Layer 3 — not inline deterministic file ops |
| **LangGraph LLM gates** | L2/L3 subgraphs; provider config in YAML/env; spike in tranche 1 |
| **UI spike (Streamlit)** | Localhost browser ops console over CLI/MCP — informs v0.4 choice (views vs CoPilotKit) |
| **Strict capabilities** | Each catalog capability: input schema, output schema, error catalog, idempotency rules |

**Claude's role in v0.3:** Primary **integration test harness** and **LLM gate executor** — not the deterministic runtime. Chat remains available for development and LLM-gated flows; it is not the production invoke path for PIPE operations.

### v0.4 — UI-primary (presentation)

**Goal:** Users invoke capabilities through structured UI; chat demoted to LLM-gated flows only.

| Deliverable | Description |
|-------------|-------------|
| **UI shell** | Browser on localhost → cloud later; direction chosen after v0.3 Streamlit spike (extend v0.2 views, CoPilotKit, or hybrid) |
| **Capability buttons** | Each strict v0.3 capability → UI affordance (HTTP → same registry as CLI/MCP) |
| **Progress + results** | Pipelines stream status; UI shows reports, not chat transcripts |
| **LLM modals** | Co-authorship, gap discussion, promotion review, ambiguous connections — chat *inside* a bounded modal with explicit commit |

---

## LLM involvement — three tiers

**Principle:** LLM-only-when-needed. Default path for any operation is Layer 2 Python. LLM is opt-in per gate, declared in skill spec and catalog.

| Tier | Name | When | v0.3 | v0.4 surface |
|------|------|------|------|--------------|
| **L1** | User-facing dialogue | Discussing gaps, open research questions, strategy, co-authorship voice | Claude test client / dev chat | Dedicated chat panels, “talk to my data”, co-authorship workspace |
| **L2** | Grounded Q&A (“talk to my data”) | User asks questions over workspace context; retrieval + synthesis; read-mostly or suggest-then-confirm writes | API with RAG over cards/refs; LLM generates answer with citations | Search/ask panel with source cards linked |
| **L3** | In-skill decision maker | Relevance scoring, extraction quality, promotion calls, ambiguous connection typing, bridge assessment | LLM gate inside pipeline — pipeline pauses, calls model, returns structured decision; user review before SOT write where required | Review modal → approve/reject/edit |

**Not LLM by default:** validation, schema checks, graph metrics, template scaffold, views data generation, dedup, ref file writes, digest structure, domain list CRUD, search-seeds CRUD.

### LangGraph — LLM orchestration (Amendment A.3)

**Adopted for L2/L3 gates.** See Amendment A.3 above for scope, provider independence, and spike plan.

Plain Python remains the default for all PIPE steps. Hand-rolled LLM calls are **not** the target end state for L2/L3 — LangGraph subgraphs are.

---

## Options considered

### Option A: UI-first CONSTRUCT03 (rejected)

Build UI shell immediately; skills stay Claude procedures behind buttons.

**Rejected because:** No testable backend; UI encodes chat assumptions; regression risk; duplicates deterministic logic in prompts.

### Option B: Pipeline-first then UI (chosen)

v0.3 = Layer 2 + 3; v0.4 = Layer 4.

**Chosen because:** Matches artifact catalog PIPE/UI split; reuses `src/construct/` and v0.2 views; CLI-before-UI principle from archived spec; Claude remains valuable as test client and L1/L2/L3 gate without being the deterministic runtime.

### Option C: Resume full Python v0.1 app (rejected)

FastAPI + SQLite + NetworkX + heartbeat per archived spec.

**Rejected because:** Scope explosion; SQLite/heartbeat not required for v0.3 tranche; contradicts Claude-native identity layer which stays in `CONSTRUCT-CLAUDE-impl/`.

---

## Consequences

### Positive

- Capabilities become **contract-tested** against specs before UI investment.
- **Artifact catalog** drives implementation order: PIPE skills first, then UI affordances.
- **Claude skills** stay the user-facing *spec and adapter*; Python owns determinism — clear separation of concerns.
- **v0.2 views** has a natural evolution path to v0.4 shell (already consumes JSON; adds write actions via API).
- **Archived Python v0.1** work (schemas, validation, CLI patterns) is reused without resurrecting the full app.
- **GSD restart** for v0.3 implementation can track pipeline epics with pytest verification.

- **MCP + CLI** give agentic clients first-class access without chat-shaped backends.
- **LangGraph** centralizes provider switching for LLM gates — config change, not code change.
- **Streamlit spike** de-risks v0.4 UI choice cheaply.

### Negative

- **Dual maintenance during v0.3** — SKILL.md, Python pipelines, and MCP tool schemas must stay aligned; catalog is master.
- **Three invoke surfaces to maintain** — mitigated by single capability registry backing CLI, MCP, HTTP.
- **UI stack uncertainty** until Streamlit spike completes — possible throwaway spike code.
- **LangGraph dependency** — new stack surface; graph + provider testing patterns to establish.
- **Transitional complexity** — hybrid skills until full MCP/CLI migration.

### Neutral

- Chat remains available for L1 throughout; “chat-as-primary” ends in v0.4 for PIPE/UI operations only.
- SQLite indexing, full cloud deploy — still deferred beyond localhost HTTP.

---

## Repository mapping (v0.3)

| Concern | Location |
|---------|----------|
| Skill specs (Layer 0) | `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md` |
| Capability audit | `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` |
| Pipeline runtime (Layer 2) | `src/construct/pipelines/` (new), existing `services/`, `schemas/` |
| LLM gates (L2/L3) | `src/construct/llm/` — LangGraph subgraphs, provider config |
| CLI (Layer 3) | `src/construct/cli.py` (extend) |
| MCP server (Layer 3) | `src/construct/mcp/` (new) — tools mirror CLI capabilities |
| HTTP (Layer 3) | `src/construct/api/` (v0.3 tranche 2+) — localhost, cloud later |
| UI spike | `src/construct/ui/` or `spikes/streamlit/` — Streamlit ops console (v0.3) |
| Tests | `tests/` + `test-ws/` fixtures |
| Claude adapter skills | `CONSTRUCT-CLAUDE-impl/` — skills call CLI/API instead of inline file ops where migrated |
| v0.3 planning | `CONSTRUCT-CLAUDE-v03-planning/` |
| v0.4 planning | `CONSTRUCT-CLAUDE-v04-planning/` (create when v0.3 pipelines stable) |

---

## Migration pattern (per skill)

For each catalog row:

1. **Audit** — mark steps: `PYTHON` | `LLM-L1` | `LLM-L2` | `LLM-L3` | `USER-REVIEW`
2. **Implement** — Python for all `PYTHON` steps; gate functions for LLM tiers
3. **Expose** — CLI subcommand + MCP tool (+ HTTP when UI needs it) with shared input/output schema
4. **Test** — contract test via CLI; MCP tool schema test; fixture workspace in [`test-ws/`](../../test-ws/)
5. **Adapt skill** — SKILL.md: validate input → invoke MCP/CLI → format output → LangGraph gate if L2/L3
6. **UI (v0.4)** — button/wizard calls same API Claude used in v0.3

---

## Relationship to prior ADRs

| ADR | Relationship |
|-----|--------------|
| **Archived Python ADR-0001** | v0.3 revives pipeline portions; LiteLLM routing → LangGraph provider config for LLM gates only |
| **Claude-native ADR-0001** | Still valid for identity, voice, governance, L1 dialogue; Claude is no longer the runtime for PIPE steps |
| **v0.2 packaging ADR-0002** | Views remain browser artefact; v0.4 extends them as UI shell |

---

## Open questions (for follow-up planning)

**Tranche 1 locked** — see [`CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md`](../../CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md):

- LangGraph spike: **L2 talk-to-my-data**
- Streamlit: **richer UI** (gate review panel)
- MCP: **stdio** first

Remaining:

1. **Provider config file location** — repo default vs per-workspace `.construct/llm.yaml`?
2. **Streamlit package path** — `src/construct/ui/` vs `spikes/v03-streamlit/`?
3. **First migrated skill** — which SKILL.md calls MCP first (suggest `construct-workspace-validate`)?
4. **Catalog columns** — split `C03 target` into `v0.3` / `v0.4`?
5. **GSD initialization** — when v0.3 implementation starts, fresh `.planning/` at repo root

---

## Success criteria

**v0.3 tranche 1 (approved):** See [`tranche-1-mvp.md`](../../CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md) — registry, CLI (validate, graph-status, views-generate-data), MCP stdio, LangGraph L2 ask, Streamlit richer UI, Daily Cycle skeleton.

### v0.3 done when

- Tranche 1 PIPE capabilities run headless via **CLI** with passing contract tests.
- **MCP tools** expose the same tranche 1 capabilities to agent clients.
- At least one **LangGraph gate** (L2 or L3) runs with swappable provider config.
- **Streamlit spike** on localhost invokes CLI/MCP capabilities (ops console).
- At least one workflow (Daily Cycle) orchestrates as a Python pipeline with step events.
- Migrated skills invoke MCP/CLI; Claude drives end-to-end as test client.

### v0.4 done when

- Primary user journeys (J1–J3) completable through UI without chat for PIPE/UI operations.
- Chat/modals reserved for L1/L2/L3 as defined above.
- v0.2 read-only views upgraded to read-write via Layer 3 API.
