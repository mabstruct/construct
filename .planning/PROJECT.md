# CONSTRUCT

## What This Is

CONSTRUCT is a local-first knowledge management system that helps a user collaboratively understand source material from files, notes, and web research. It builds a governed knowledge graph of knowledge nodes and typed connections, then exposes that knowledge through agentic workflows, graph views, and dynamic wiki-style browsing. The current Claude-native implementation is the proof-of-concept foundation; upcoming work hardens that foundation and evolves it toward a clearer product experience.

## Core Value

The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.

## Current Milestone: v0.4 Agent Workflows — ✅ SHIPPED 2026-07-07

**Goal:** Move CONSTRUCT's highest-value multi-step workflows from opaque Claude-native procedures into testable, model-agnostic LangGraph/LangChain pipelines while preserving the existing workspace format and current skill UX.

**Delivered (Phases 8–13, 22/22 requirements):**
- Search provider spine with Tavily/default mockable provider and normalized search result contracts (Phase 8; SRCH-01..04).
- `research.search`, `research.score`, and `research.run` with L3 scoring, durable human review, governed ingest, events, and CLI/MCP parity (Phases 8–10; RSCH-01..05).
- `curation.run` with real integrity/decay/orphan/connection/report steps plus propose-only promotion/connection L3 gates and reviewed apply, replacing v0.3 placeholder no-ops (Phases 11–12; CUR-01..05).
- Thin skill migrations for research and curation delegating to CLI/MCP, removing direct `WebSearch` / `WebFetch` (Phase 12; API-04).
- Daily-cycle composition — thin non-blocking `daily.run` composing research → curation → graph.status with full CLI/MCP parity (Phase 13; DAY-01..03, API-01/02/03/05).

**Next:** v0.4.1 (surface integration) — see below. v0.5 (UI-primary experience) follows.

## Current Milestone: v0.4.1 Surface Integration & Documentation Truth

**Goal:** Reconnect the sound v0.4 runtime to the surfaces users and agents actually touch — every documented invocation path resolves and executes, the v0.4 runtime is discoverable by both users and agents, and the architecture doc set describes the system that actually exists.

**Target features:**
- Resolve `views.generate_data` — no permanent-failure handler may remain on the MCP surface (FIX-01)
- Re-point the Streamlit LLM config default and settle `model-routing.yaml`'s fate (FIX-02)
- Every `construct ...` string in skills, workflows, and the playbook resolves against the registry (FIX-03)
- Rewrite `architecture-overview.md` against ADR-0003's four-layer model (DOC-01)
- Capability/CLI/MCP inventory in `artifact-catalog.md`; fix or delete `config-topology.md` (DOC-02)
- Record the durable-checkpointer decision in the NFR/architecture/workspace-contract invariants — **gates v0.5 design** (DOC-03)
- CLI coverage in `USER_GUIDE.md`, corrected `README.md` / `AGENTS.md`, retired v0.3 playbook (DOC-04)
- Claude-native entry point for `daily.run`, the flagship v0.4 capability (UX-01)
- Close `spec-v04:436` — `WebSearch`/`WebFetch` in `construct-synthesis` (DEC-01)

**Already delivered ahead of the milestone:** FIX-04 — `tests/contract/test_doc_command_references.py` (2026-07-19). Introspects the live Typer app and asserts every documented `construct ...` string resolves, with a `_KNOWN_BROKEN` allowlist that can only shrink. FIX-01 and FIX-03 are complete precisely when that allowlist is empty.

**Basis:** `.planning/milestones/v0.4-MILESTONE-AUDIT.md` (retrospective audit, 2026-07-19). The runtime is sound and its 22/22 requirements genuinely met; these are integration defects in shipped work, not new capability.

## Requirements

### Validated

- ✓ Harden the Claude-native skills and workflows so they are reliable and consistently follow defined data formats — v0.3 (canonical contract + pre-write gates, Phases 1–2).
- ✓ Make the current agentic user experience clearer through documented workflows and dependable next-step guidance — v0.3 (guided workflow operability + help.suggest, Phase 4; graph-health surfacing, Phase 7).
- ✓ Define and deliver the v0.3 foundation that preserves the knowledge model while creating a stable path toward a UI-primary product in v0.5 — v0.3 (capability/CLI/MCP runtime spine + derived-data contracts, Phases 3, 5, 6).
- ✓ **Research workflow:** `research.score` scores search results through a model-agnostic structured gate and `research.run` executes search→dedup→score→durable human review→approved ingest→digest→seed updates→events as one resumable workflow — v0.4 (Phase 9 scoring, Phase 10 durable `research.run`; RSCH-01..05).
- ✓ **Curation PIPE steps:** `curation.run` / `curation.inspect` run real deterministic integrity, decay, orphan, connection-health, and report checks (replacing v0.3 placeholder no-ops) from the CLI and stdio MCP server, with completed/degraded/skipped status visible per step — v0.4 (Phase 11; CUR-01). Promotion/connection gates, human review application, and skill migration remain Phase 12.
- ✓ **Search provider spine:** provider-agnostic search contracts, Tavily/default + mock providers, config-driven caps, and CLI/MCP-accessible `research.search` with structured degraded errors and zero SOT writes — v0.4 (Phase 8; SRCH-01..04).
- ✓ **Thin skill migrations:** research and curation Claude-native skills delegate to CLI/MCP capabilities with direct `WebSearch` / `WebFetch` / workspace writes removed, guarded by a forbidden-tool test — v0.4 (Phase 12; API-04).
- ✓ **Daily-cycle composition:** `daily.run` / `daily.inspect` compose the stable `research.run → curation.run → graph.status` children as a thin, non-blocking Python cycle (isolate-and-degrade, escalate excluded, no false `completed`), registered with full CLI/MCP parity and wired into the daily-cycle skill which owns the single post-run views refresh — v0.4 (Phase 13; DAY-01/02/03, API-01/02/03/05). Closes v0.4.

### Active

**v0.4.1 Surface Integration & Documentation Truth** (see Current Milestone above). Nine open requirements: FIX-01/02/03 (live defects), DOC-01/02/03/04 (documentation truth), UX-01 (`daily.run` entry point), DEC-01 (synthesis skill tool grants). FIX-04 (doc-command guard) delivered 2026-07-19.

_Deferred past v0.4.1: v0.5 UI-primary experience (UI-01/02), RT-01/RT-02 registry unification, thin-wrapper migration for `construct-bridge-detect` / `domain-init` / `search-adjust` (logged for v0.6), historical verification/security debt._

### Out of Scope

- Replacing the existing knowledge model or workspace format — continuity across versions is a core constraint.
- Breaking current Claude-native workflows during the v0.5 UI build — existing user flows must remain usable.
- Pulling the v0.5 browser-primary shell into v0.4 — UI-primary work waits for stable workflow capabilities.
- Treating RT-01/RT-02 registry unification for views/spike/tag, full `views.generate_data` emission, or milestone-wide verification/security debt as primary v0.4 scope — these remain tracked follow-ups unless directly required by agent workflow delivery.
- Any v0.5 UI work in v0.4.1 — building a UI on surfaces known to be broken would also obscure v0.5's own delivery signal.
- RT-01/RT-02 registry unification in v0.4.1, unless FIX-01 requires touching the views group — in which case scope only that group.
- Migrating `construct-bridge-detect` / `construct-domain-init` / `construct-search-adjust` to thin wrappers in v0.4.1 — real debt, but larger than a patch milestone. Logged for v0.6.

## Context

CONSTRUCT is currently in a proof-of-concept phase and has already gone through multiple iterations. In v0.2, the project established a Claude-native implementation built from agentic skills and workflows. That prototype already supports a collaborative knowledge workflow in which the user and agent work from source files, notes, and web research to build a knowledge graph made of knowledge nodes and typed connections.

The product vision extends beyond the current prototype. The Claude-native approach remains important as the first working embodiment of the system and as the interaction model for v0.3, but it now needs hardening. Current pain points include inconsistent adherence to defined data formats, inconsistent workflow behavior, and insufficient clarity about what the user should do next.

The desired user experience in the near term is still guided by Claude-native skills and Python capabilities (CLI/MCP), especially with clear documentation, stronger workflow contracts, and a dependable help skill that can suggest the next sensible step. In the longer term, **v0.5** should present these same underlying capabilities through more obvious UI interactions so the product becomes easier for a broader audience to use. **v0.4** focuses on migrating multi-step workflows to LangGraph/LangChain in Python (model-agnostic search and gates), not the product UI shell.

There are already relevant analyses in the latest specification documents covering capabilities and artifacts. Those documents should inform requirements and roadmap structure rather than re-deriving the product from scratch.

**Current state (v0.4 shipped, 2026-07-07):** v0.4 Agent Workflows shipped across 6 phases (8–13) / 24 plans, delivering all 22 requirements with the full pytest suite green (404 tests). The runtime is a Python package (`src/construct/`, ~15k LOC) with a capability registry, a Typer CLI, and a stdio MCP server; Claude-native skills are thin wrappers that now delegate to CLI/MCP. On top of the v0.3 governed-workspace spine, v0.4 added: a provider-agnostic search spine (Tavily + mock, config-driven caps); a model-agnostic LLM provider factory and L3 gates (`research.score`, `card.evaluate`, connection-typing); durable checkpointed LangGraph workflows for `research.run` and `curation.run` with real `interrupt()` human review that writes nothing before approval; and a thin `daily.run` composition folding research → curation → graph.status into one non-blocking cycle. MCP parity for every new capability is free via registry auto-discovery (`mcp/server.py` never hand-edited). **Next:** v0.5 (UI-primary experience) sits on these proven pipelines; carry-over debt (RT-01/RT-02 registry unification, full `views.generate_data` emission, historical verification/security docs) remains deferred. Reference: [`spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md).

## Constraints

- **Product continuity**: Preserve the existing knowledge model and workspace format across prototype, v0.3, v0.4, and v0.5 — the system's continuity depends on shared semantics and files.
- **Sequencing**: Do not pull **v0.5** UI-primary work ahead of **v0.4** workflow/runtime hardening — the UI must sit on proven LangGraph pipelines and capabilities.
- **Compatibility**: Protect existing Claude-native workflows while hardening and migrating them — users should not lose current capabilities.
- **Implementation posture**: v0.3 should still be usable through the Claude-native skill/workflow model even as it prepares a richer runtime and interface layer.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat the current Claude-native system as the production-defining prototype, not a throwaway experiment | The existing implementation already embodies the core knowledge workflow and should shape future versions | ✓ Good — v0.3 hardened it into a Python runtime + MCP spine with skills as thin wrappers |
| Use v0.3–v0.4 to harden workflows and runtime contracts before building the v0.5 UI-primary experience | A clearer UI only helps if the underlying capabilities and workflows are reliable and well-bounded | ✓ Good — v0.3 shipped the runtime spine; v0.4 targets LangGraph workflows; v0.5 UI follows |
| Preserve the knowledge model and workspace format across versions | Cross-version continuity is central to the product architecture and migration story | ✓ Good — workspace format preserved; Phase 1 published a migration playbook |
| Python is the deterministic enforcement layer; skills orchestrate flow; the capability registry is the single contract behind CLI + MCP | Keeps behavior testable and gives agents and (future) UI one surface | ⚠️ Revisit — registry is canonical for core ops, but views/spike/tag groups still bypass it (RT-01/RT-02, v0.4 backlog) |
| Fix governed-ingest validation by conforming the data to the gate, not weakening the gate | Keeps validation strict so canonical truth stays trustworthy | ✓ Good — v0.3 (Phase 7, ING-02) |
| Scope v0.4 to agent workflows first, not all accepted v0.3 carry-over debt | Research and curation workflows are the highest leverage path to model-agnostic operation and v0.5 readiness; unrelated debt can obscure that goal | ✓ Good — v0.4 shipped all 22 workflow requirements; carry-over debt stayed deferred without blocking delivery |
| Compose the daily cycle as thin synchronous Python over frozen children, not a parent LangGraph graph/checkpointer | Each child already owns its own checkpointer + typed result; a parent graph would duplicate state and gate logic. Isolate-and-degrade is a per-child try/except | ✓ Good — v0.4 (Phase 13, D-09); `daily.run` is 268 lines with no parent graph, full CLI/MCP parity free via registry auto-discovery |
| Auto-apply only each gate's *recommended* decision via the child `approve_all` resume, excluding escalate | Keeps the non-blocking daily cycle safe: escalate items never get an unattended canonical write, and every applied write is event-logged by the children exactly as interactive review | ✓ Good — v0.4 (Phase 13, D-02/D-03); pending escalations surfaced as a count, never a false `completed` |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-19 — v0.4.1 Surface Integration & Documentation Truth milestone started (scope from `milestones/v0.4-MILESTONE-AUDIT.md`)*
