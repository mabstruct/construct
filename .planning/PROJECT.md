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

## Current Milestone: v0.4.1 Surface Integration & Documentation Truth — ✅ SHIPPED 2026-07-25

**Goal:** Reconnect the sound v0.4 runtime to the surfaces users and agents actually touch — every documented invocation path resolves and executes, the v0.4 runtime is discoverable by both users and agents, and the architecture doc set describes the system that actually exists.

**Delivered (Phases 14–17, 9/9 requirements):**
- `views.generate_data` runs a real handler behind an `install_root` contract — the permanent-failure stub is gone from the MCP surface, the 15-module views library is vendored into `src/construct/views/`, and post-run views refresh is owned by the Python workflow layer (Phase 15; FIX-01, adr-0005).
- One authoritative LLM config location — `resolve_llm_config_path()` shared by the Streamlit ops UI and runtime, with `model-routing.yaml` deprecated-but-scaffolded everywhere it was called authoritative (Phase 14; FIX-02).
- Every `construct …` string in skills, workflows, and the playbook resolves against the live Typer app — `_KNOWN_BROKEN` empty over a *widened* guard (`_DOC_GLOBS` 3→5), `knowledge card list` implemented, user docs made executable, and the v0.3 playbook superseded by an offline-runnable, human-verified v0.4.1 playbook (Phase 16; FIX-03, DOC-04).
- `construct-synthesis` dropped its `WebSearch`/`WebFetch` grants, closing `spec-v04:436` (Phase 16; DEC-01).
- The architecture doc set describes the system that exists — `architecture-overview.md` rewritten onto ADR-0003's L0–L4 model, `artifact-catalog.md` staleness-proofed by an introspection guard, `config-topology.md` deleted, and the durable-checkpointer decision recorded in the NFR/architecture/workspace-contract invariants (Phases 14, 17; DOC-01, DOC-02, DOC-03). **DOC-03 unblocks v0.5 design.**
- `daily.run` — the flagship v0.4 capability — reachable from Claude-native chat via a thin `construct-daily-cycle` skill (Phase 17; UX-01).

**Delivered ahead of the milestone:** FIX-04 — `tests/contract/test_doc_command_references.py` (2026-07-19). Introspects the live Typer app and asserts every documented `construct ...` string resolves, with a `_KNOWN_BROKEN` allowlist that can only shrink. It supplied the mechanical completion criteria for Phases 15 and 16.

**Basis:** `.planning/milestones/v0.4-MILESTONE-AUDIT.md` (retrospective audit, 2026-07-19). The runtime was sound and its 22/22 requirements genuinely met; these were integration defects in shipped work, not new capability.

**Next:** v0.5 (UI-primary experience) — browser-first shell on the hardened v0.4 runtime. DOC-03 prerequisite satisfied; scoped below.

## Current Milestone: v0.5 UI-Primary Experience — Proof of Concept

**Goal:** Prove on an isolated branch that a browser-first shell over the v0.4 runtime can guide a user through CONSTRUCT's core loops without touching the CLI — a technical *and* UX proof of concept, judged on whether the guided/wizard model actually makes the system usable unaided.

**Target features:**
- Reconcile the `views generate` ↔ `views validate` byte contract (3 of 8 files currently rejected; pinned by `test_views_validate_does_not_yet_accept_generated_bytes`) — the shared prerequisite named by both SEED-001 and SEED-003.
- An HTTP API over the capability registry serving both reads and capability invocation — CONSTRUCT has no HTTP surface today (Typer CLI + stdio MCP only), so HTTP becomes a third adapter over the same 28-capability contract.
- Promote the views SPA (React 19 / Vite 7 / Tailwind 4 / react-router 7) from a per-workspace skill template to a first-class app in the repo, served by the API.
- Document ingestion with real text extraction for txt, md, pdf, doc — `ingestion.py` today routes a file to a domain and writes a ref + seed card without reading it.
- A guided action layer that renders the existing `help.suggest` engine (`services/help.py:32`) in the browser, testing whether its prioritized next-steps are good enough to guide a person.
- Four wizard flows: workspace creation (`workspace.init` + domain setup), document ingestion (upload → extract → route → review), and the two HITL review gates (`research.review`, `curation.review`) — the latter two share one queue-of-proposals surface.
- Browse workspaces, the wiki reading view, and the knowledge graph on live API data (pages exist scaffolded but static-file-fed).
- Three evaluation spikes producing verdict documents, not shipped features: CoPilotKit as the Layer 4 framework (SEED-001), graphify.net for content ingestion (SEED-002), and LLM-Wiki alignment / open wiki-format interop (SEED-003).

**Key context:**
- Work happens on branch `dev-v05` off `main`, pushed to origin, so the v0.4.1 backend on `main` stays releasable. The stale `dev-v04` branch is left untouched.
- `daily.run` / daily-cycle composition is explicitly out of scope for this iteration.
- CoPilotKit is **evaluated, not adopted** — the PoC ships on the existing views SPA and the spike produces a framework verdict for v0.6. This deliberately defers the Layer 4 decision a third time, but with real evidence behind it for the first time.
- The Wiki honors locked decisions D5/D8 (`spec-v02-knowledge-views-spike.md`, 2026-05-02): it is a sibling reading view rather than the workspace default, and topic synthesis stays with the `synthesis` workflow.
- SEED-003's format question is scoped to "can CONSTRUCT emit an open wiki format as a read-only projection?" — the same shape as the views layer. A canonical workspace-format change stays out of scope.
- Success is a **UX verdict** — whether a person can navigate CONSTRUCT unaided — with an end-to-end demo path (upload a PDF → cards → wiki + graph) as the mechanical gate that supports it.

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
- ✓ **`views.generate_data` resolution:** the permanent-failure stub is gone from the MCP surface — a real handler wired to the views generator, reachable over MCP, over `construct views generate` (plain and `--json`), and through a CLI-wrapper skill. The 15-module views library is vendored into `src/construct/views/` so an installed CONSTRUCT can import it, `views/models.py` describes the shape the parsers actually emit, the contract is `install_root` everywhere, and post-run views refresh is owned by the Python workflow layer across `curation.run` / `research.run` / `daily.run` as a side effect that never flips a workflow's status — v0.4.1 (Phase 15; FIX-01, D-02/03/08/09/10/11/12, adr-0005). Known open: `views validate` does not yet accept the bytes `views generate` writes (Phase 16/17 contract question, pinned by test); per-card edits have no refresh path after the debounced-hook removal (v0.6 candidate).
- ✓ **Durable-state & config truth:** `.construct/workflow/*.sqlite` is recorded in `adr-0004` as sanctioned durable state holding pending human-review decisions not reconstructible from layer 1, with `nfrs.md` §2/§4, `architecture-overview.md`, and `workspace-contract.md` scoped to match; `resolve_llm_config_path()` gives the Streamlit ops UI and the runtime one shared code path, and `model-routing.yaml` is scaffolded-but-deprecated everywhere it was called authoritative — v0.4.1 (Phase 14; DOC-03, FIX-02). Unblocks v0.5 design.
- ✓ **Invocation & user-doc truth:** every `construct …` string in skills, workflow docs, and the release playbook resolves against the live Typer app — the `_KNOWN_BROKEN` allowlist is empty with the suite green, and the guard was *widened* (`_DOC_GLOBS` 3→5, adding `USER_GUIDE.md` and `commands.md`) so an empty allowlist cannot be a narrowed-scan artefact. `knowledge card list` is a real registry-routed command with CLI/MCP parity; `construct-synthesis` dropped its `WebSearch`/`WebFetch` grants (closing `spec-v04:436`); the user-facing doc set carries executable CLI invocations; and `USER-TEST-PLAYBOOK-v03.md` was superseded by an offline-runnable `USER-TEST-PLAYBOOK-v041.md`, human-verified on a fresh workspace — v0.4.1 (Phase 16; FIX-03, DEC-01, DOC-04). Known open (code-review WR-01/WR-02, non-blocking): the MCP boundary for `card list` does not serialize `OperationError` on the failure path and does not enforce `CardListInput` validation — shared `mcp/server.py` debt, newly reachable, logged as follow-up.
- ✓ **Architecture doc set & `daily.run` discoverability:** `architecture-overview.md` is rewritten onto ADR-0003's permanent L0–L4 runtime model (the Python runtime layer named, the false "skills are the only legitimate writers to layer 1" claim removed, Python-runtime write-ownership made visible, five broken vocab citations repointed); `artifact-catalog.md` is a staleness-proofed inventory — a new `tests/contract/test_artifact_catalog.py` guard asserts every live capability (28), MCP tool (22), Typer leaf (34), and `construct-*` skill dir (25) has a catalog row and physically cannot pass vacuously — expanded with the capability/CLI/MCP runtime surface plus the `construct-spike-run` and `construct-daily-cycle` rows; `config-topology.md` is deleted with every deferrer redirected and the `spec-v04:211/:557` model-routing fence closed against `llm/config.yaml`; and `daily.run` gained a thin Claude-native `construct-daily-cycle` skill (delegates to `construct daily run --json`, no gate loop, no views refresh) enrolled in the forbidden-tools guard with `_KNOWN_BROKEN` still empty — v0.4.1 (Phase 17; DOC-01, DOC-02, UX-01). Closes v0.4.1. Known open (code-review WR-01/WR-02, non-blocking): the catalog guard enforces row set-membership not cardinality, so the hand-typed 28/22/34 counts in prose could rot on a future capability addition; one stale test docstring.

### Active

**v0.5 UI-Primary Experience (Proof of Concept)** — Phase 18 complete; Phases 19–24 remain. Scope gathered 2026-07-26: data-contract reconciliation, an HTTP API over the capability registry, the views SPA promoted to a served app, real document extraction, a `help.suggest`-driven guided layer, four wizard flows, live-data browse/wiki/graph views, and three evaluation spikes (SEED-001/002/003). See `.planning/REQUIREMENTS.md`.

_Carried into Phase 19 from Phase 18 (see `18-SECURITY.md`, `18-REVIEW.md`):_
- _**T-18-10 / T-18-32 — path leakage, one root cause.** `mcp/server.py` returns `str(exc)`, and the success path serializes `OperationResult.message` built from `str(exc)` at ~27 sites in `services/knowledge.py`, plus `graph_status.py` putting a resolved path in `data`. This becomes a **Phase 19 criterion-3 failure** ("no raw exception text or filesystem paths in the body") if it survives._
- _**Workspace addressing vs. GOV-01.** Every input model declares `workspace: Path`; Phase 19 criterion 2 requires workspaces named **by id**, with paths and traversals rejected. Solving it above the seam rebuilds the fork GOV-01 closed; solving it in the models touches all 29 capabilities. Named for the Phase 19 research pass._
- _**`_wrap_resume` is mandatory** for any surface driving the graph directly — a bare id-keyed dict is read by LangGraph as an interrupt-id mapping and silently discarded, leaving the run paused with no error._
- _**Registering a capability trips five guards**, not one; `_payload_for`'s miss surfaces as a bare `KeyError`. Phase 19 adds an endpoint per capability — derive its route table and test payloads from the registry rather than hand-listing._
- _**WR-04** — `from_validation_error`'s `model` parameter is optional, so a generated HTTP adapter silently gets payload-ordered reasons. A guarantee a caller can drop is a convention, not a contract._
- _12 further code-review warnings, T-18-35 (substring-matched guard exemptions), and D-23/D-24's deferred instances._

_Deferred past v0.4.1: RT-01/RT-02 registry unification, thin-wrapper migration for `construct-bridge-detect` / `domain-init` / `search-adjust` (logged for v0.6), historical verification/security debt, the per-card views-refresh path (v0.6 OQ-3), `card list` MCP-boundary hardening (WR-01/WR-02), and stale `artifact-catalog.md` prose counts._

### Out of Scope

- Replacing the existing knowledge model or workspace format — continuity across versions is a core constraint.
- Breaking current Claude-native workflows during the v0.5 UI build — existing user flows must remain usable.
- Pulling the v0.5 browser-primary shell into v0.4 — UI-primary work waits for stable workflow capabilities.
- Treating RT-01/RT-02 registry unification for views/spike/tag, full `views.generate_data` emission, or milestone-wide verification/security debt as primary v0.4 scope — these remain tracked follow-ups unless directly required by agent workflow delivery.
- Any v0.5 UI work in v0.4.1 — building a UI on surfaces known to be broken would also obscure v0.5's own delivery signal.
- RT-01/RT-02 registry unification in v0.4.1, unless FIX-01 requires touching the views group — in which case scope only that group.
- Migrating `construct-bridge-detect` / `construct-domain-init` / `construct-search-adjust` to thin wrappers in v0.4.1 — real debt, but larger than a patch milestone. Logged for v0.6.
- `daily.run` / daily-cycle composition in the v0.5 UI — explicitly excluded from this iteration so the PoC's guidance signal is not diluted by the most complex composed workflow.
- Adopting CoPilotKit in v0.5 — it is evaluated by spike only (SEED-001). Building the PoC on an unvalidated framework would make a negative verdict cost the whole slice.
- Changing the canonical workspace format for open wiki-format interop (SEED-003) — the answerable v0.5 question is whether an open format can be emitted as a read-only projection, the same shape as the views layer.
- Repositioning the Wiki away from locked decisions D5/D8 — it stays a sibling reading view, not the workspace default, and topic synthesis stays with the `synthesis` workflow. Any change here is a deliberate repositioning, not v0.5 scope.
- Production hardening of the v0.5 HTTP API (auth, multi-user, remote hosting) — this is a local-first proof of concept on an isolated branch, not a deployable service.

## Context

CONSTRUCT is currently in a proof-of-concept phase and has already gone through multiple iterations. In v0.2, the project established a Claude-native implementation built from agentic skills and workflows. That prototype already supports a collaborative knowledge workflow in which the user and agent work from source files, notes, and web research to build a knowledge graph made of knowledge nodes and typed connections.

The product vision extends beyond the current prototype. The Claude-native approach remains important as the first working embodiment of the system and as the interaction model for v0.3, but it now needs hardening. Current pain points include inconsistent adherence to defined data formats, inconsistent workflow behavior, and insufficient clarity about what the user should do next.

The desired user experience in the near term is still guided by Claude-native skills and Python capabilities (CLI/MCP), especially with clear documentation, stronger workflow contracts, and a dependable help skill that can suggest the next sensible step. In the longer term, **v0.5** should present these same underlying capabilities through more obvious UI interactions so the product becomes easier for a broader audience to use. **v0.4** focuses on migrating multi-step workflows to LangGraph/LangChain in Python (model-agnostic search and gates), not the product UI shell.

There are already relevant analyses in the latest specification documents covering capabilities and artifacts. Those documents should inform requirements and roadmap structure rather than re-deriving the product from scratch.

**Current state (v0.4 shipped, 2026-07-07):** v0.4 Agent Workflows shipped across 6 phases (8–13) / 24 plans, delivering all 22 requirements with the full pytest suite green (404 tests). The runtime is a Python package (`src/construct/`, ~15k LOC) with a capability registry, a Typer CLI, and a stdio MCP server; Claude-native skills are thin wrappers that now delegate to CLI/MCP. On top of the v0.3 governed-workspace spine, v0.4 added: a provider-agnostic search spine (Tavily + mock, config-driven caps); a model-agnostic LLM provider factory and L3 gates (`research.score`, `card.evaluate`, connection-typing); durable checkpointed LangGraph workflows for `research.run` and `curation.run` with real `interrupt()` human review that writes nothing before approval; and a thin `daily.run` composition folding research → curation → graph.status into one non-blocking cycle. MCP parity for every new capability is free via registry auto-discovery (`mcp/server.py` never hand-edited). Reference: [`spec-v04-agentworkflows.md`](../CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md).

**Current state (v0.4.1 shipped, 2026-07-25):** the v0.4.1 patch milestone reconnected that runtime to its surfaces across 4 phases (14–17) / 20 plans, delivering all 9 requirements. `views.generate_data` now has a real MCP handler with the views library vendored into `src/construct/views/`; every documented `construct …` invocation resolves against the live Typer app (guarded, allowlist empty over a widened scan); the architecture doc set (`architecture-overview.md`, `artifact-catalog.md`, the NFR/workspace-contract invariants) describes the system that exists, with `config-topology.md` deleted and the durable-checkpointer decision recorded (adr-0004); and `daily.run` is reachable from chat via `construct-daily-cycle`. Suite grew to 515 passed / 1 skipped at the Phase 16 checkpoint. **Next:** v0.5 (UI-primary experience) sits on these proven pipelines and now-honest surfaces — DOC-03 prerequisite satisfied. Handoff debt (the `views validate`↔`views generate` byte contract, per-card refresh path, `card list` MCP-boundary hardening, RT-01/RT-02 registry unification, historical verification/security docs) remains deferred and logged.

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
| The Python capability layer owns the views refresh and every workflow capability refreshes — reversing Phase 13 D-10's skill-owned parent hook | A per-workflow refresh needs no parent-awareness, which Phase 13 D-09's deliberately flat `daily.run` composition cannot supply; and it leaves one tested implementation instead of a skill-local copy | ✓ Good — v0.4.1 (Phase 15, D-09/D-11/D-12); recorded in [`adr-0005-views-refresh-ownership.md`](../CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md). Accepted cost: three full view builds per daily cycle, not one |
| Treat `.construct/workflow/*.sqlite` as sanctioned durable state and make docs describe the system that exists, rather than softening the "no hidden state" invariant | Pending human-review decisions are genuinely not reconstructible from layer 1; a rebuild guarantee that names what it covers stays auditable, and mechanical guards beat prose for keeping the inventory honest | ✓ Good — v0.4.1 (Phase 14 adr-0004; Phase 17 introspection guard); the durable-checkpointer record unblocks v0.5 design |
| Fix documented invocations by conforming the docs/commands to the live registry, not by weakening the guard — allowlist emptied by supersession then the scan *widened* | An empty `_KNOWN_BROKEN` only proves truth if it survives widening the scanned surface; narrowing to pass would reintroduce the drift the guard exists to catch | ✓ Good — v0.4.1 (Phase 16, FIX-03/FIX-04); `_DOC_GLOBS` 3→5 with the allowlist held empty, suite green |

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
*Last updated: 2026-08-02 — after Phase 18 (Contract & Governance Foundations), the first v0.5 phase. 8 plans in 4 waves closed VFIX-01 and GOV-01..05: the views projection now validates against its own validator (13 conformed models + 2 new, one canonical `events.json` shape, a round-trip guard proven non-vacuous by a deliberate field rename), all invocation surfaces route through one validating seam (`registry.invoke`; `grep -c '\.handler(' cli.py` → 0, 29 capabilities all `extra="forbid"`, `views validate` registered), and a human-review decision names the proposal it applies to (opaque `uuid4-hex` `proposal_id`, checkpoint-id ETag, incomplete maps rejected with zero writes). The second canonical writer (`ui/gate_review.py`) is deleted and its absence is a source-level invariant. 532 → 802 tests. Code review found 5 blockers past 8 green self-reports — 4 reproduced against running code, 3 contradicting criteria the summaries claimed met — all fixed. Security audit added 3 threats the register omitted and found T-18-34 open and blocking (7 capabilities creating directories at any agent-supplied `workspace_path`); fixed with a regression test that derives its capability list by measurement. Carried: the T-18-10/T-18-32 path-leak pair (a Phase 19 criterion-3 dependency) and 12 code-review warnings.*

*Previously updated: 2026-07-26 — started milestone v0.5 (UI-Primary Experience — Proof of Concept). Scope gathered in conversation: fix the `views generate`↔`views validate` byte contract, build an HTTP API over the capability registry, promote the views SPA to a served first-class app, add real document extraction (txt/md/pdf/doc), render `help.suggest` as the guided action layer, deliver four wizard flows (workspace creation, ingestion, research review, curation review), serve browse/wiki/graph on live data, and run three evaluation spikes (SEED-001 CoPilotKit, SEED-002 graphify.net, SEED-003 LLM-Wiki open format). Work isolated on branch `dev-v05`; `daily.run` out of scope; success judged as a UX verdict with an E2E demo path as the mechanical gate. Phases continue from 17.*

*Previously updated: 2026-07-25 — after v0.4.1 milestone (Surface Integration & Documentation Truth). Shipped across Phases 14–17 / 20 plans, delivering all 9 requirements: real `views.generate_data` MCP handler with the views library vendored (FIX-01), one authoritative LLM config path (FIX-02), every documented `construct …` invocation resolving over a widened guard (FIX-03, FIX-04), the architecture/NFR/workspace-contract doc set describing the system that exists with the durable-checkpointer decision recorded (DOC-01/02/03), executable user docs and a superseded playbook (DOC-04), `construct-synthesis` web grants closed (DEC-01), and `daily.run` reachable from chat (UX-01). Tagged v0.4.1. Next: v0.5 UI-primary experience — DOC-03 prerequisite satisfied.*
