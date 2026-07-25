# Milestones

## v0.4.1 Surface Integration & Documentation Truth (Shipped: 2026-07-25)

**Phases completed:** 4 phases (14–17), 20 plans, 25 tasks
**Git range:** v0.4 → HEAD · 145 commits · 243 files changed (+21,796 / −1,905) · 7 days (2026-07-19 → 2026-07-25)
**Definition of done:** Reconnect the sound v0.4 runtime to the surfaces users and agents actually touch — every documented invocation path resolves and executes, the v0.4 runtime is discoverable by both users and agents, and the architecture doc set describes the system that actually exists. Integration defects in shipped work, not new capability.

**Key accomplishments:**

- **Phase 14 — Durable-State & Config Truth (DOC-03, FIX-02):** `adr-0004` records `.construct/workflow/*.sqlite` as sanctioned durable state holding pending human-review decisions not reconstructible from layer 1; `nfrs.md` §2/§4, `architecture-overview.md`, and `workspace-contract.md` scoped to match (rebuild guarantee named, "Third-party APIs: None" corrected for Tavily, the three missing artifacts + a fourth durable-orchestration-state class added); `resolve_llm_config_path()` gives the Streamlit ops UI and the runtime one shared resolution path; `model-routing.yaml` deprecated-but-scaffolded everywhere it was called authoritative. **Unblocks v0.5 design.**
- **Phase 15 — views.generate_data Resolution (FIX-01, adr-0005):** the permanent-failure stub is gone from the MCP surface, replaced by a real handler wired to the views generator reachable over MCP, `construct views generate` (plain + `--json`), and a CLI-wrapper skill; the 15-module views library is vendored into `src/construct/views/lib/` so an installed CONSTRUCT can import it; `views/models.py` reconciled to the parsers' actual output; the contract is `install_root` everywhere; and post-run views refresh is owned by the Python workflow layer across `curation.run`/`research.run`/`daily.run` as a side effect that never flips workflow status.
- **Phase 16 — Invocation & User-Doc Truth (FIX-03, DEC-01, DOC-04):** every `construct …` string in skills, workflow docs, and the release playbook resolves against the live Typer app — `_KNOWN_BROKEN` is empty and the guard was *widened* (`_DOC_GLOBS` 3→5, adding `USER_GUIDE.md` and `commands.md`) so an empty allowlist cannot be a narrowed-scan artefact; `knowledge card list` is a real registry-routed command with CLI/MCP parity; `construct-synthesis` dropped its `WebSearch`/`WebFetch` grants (closing `spec-v04:436`); the user doc set carries executable CLI invocations; and `USER-TEST-PLAYBOOK-v03.md` was superseded by an offline-runnable `USER-TEST-PLAYBOOK-v041.md`, human-verified on a fresh workspace.
- **Phase 17 — Architecture Doc Set & daily.run Discoverability (DOC-01, DOC-02, UX-01):** `architecture-overview.md` rewritten onto ADR-0003's permanent L0–L4 runtime model (Python runtime named, the false single-writer claim removed, five broken vocab citations repointed); `artifact-catalog.md` staleness-proofed by a new `tests/contract/test_artifact_catalog.py` guard asserting every live capability, MCP tool, Typer leaf, and `construct-*` skill dir has a catalog row and cannot pass vacuously; `config-topology.md` deleted with every deferrer redirected and the `spec-v04:211/:557` model-routing fence closed; and `daily.run` gained a thin Claude-native `construct-daily-cycle` skill enrolled in the forbidden-tools guard.

**Requirements:** 9/9 mapped · 9 Complete · 0 Partial · 0 unsatisfied. All phases verified; artifact-open audit clear at close (verified closeout). Suite grew to 515 passed / 1 skipped at the Phase 16 checkpoint.

**Known open at close (non-blocking, logged as follow-up):**
- `views validate` does not yet accept the bytes `views generate` writes (generator validates a projection but writes the raw dict) — a Phase 16/17 SPA-contract question, pinned by test; needs an owner before v0.5 SPA work.
- Per-card `card-create`/`card-connect` edits have no views-refresh path after the debounced-hook removal (15-05); `views.per_card_hooks.*` is inert config — v0.6 candidate (OQ-3).
- MCP boundary for `card list` does not serialize `OperationError` on the failure path nor enforce `CardListInput` validation — shared `mcp/server.py` debt, newly reachable (code-review WR-01/WR-02).
- `artifact-catalog.md`'s hand-typed 28/22/34 counts are guarded by set-membership, not cardinality, so prose counts could rot on a future capability addition; one stale test docstring.

---

## v0.4 Agent Workflows (Shipped: 2026-07-07)

**Phases completed:** 6 phases (8–13), 24 plans, 55 tasks
**Git range:** c27a566 (phase 8 context) → v0.4 tag · 177 commits · 171 files changed (+30,578 / −708) · ~16 days
**Definition of done:** Move CONSTRUCT's highest-value multi-step workflows from opaque Claude-native procedures into testable, model-agnostic LangGraph/LangChain pipelines (search spine, `research.score`/`research.run`, `curation.run` with L3 gates and reviewed apply, thin skill migrations, and daily-cycle composition) while preserving the workspace format and skill UX.

**Key accomplishments:**

- SearchConfig schema, four-method SearchProvider ABC, fixture-driven MockSearchProvider, and cap-enforcing factory — offline unit tests pass without Tavily SDK
- research.search callable via CLI and MCP through shared registry; search.yaml loads/validates/scaffolds; degraded provider errors return structured OperationResult with zero SOT writes
- Offline contract suite covers research.search end-to-end; MCP parity at 12 tools; Tavily adapter isolated behind optional extra with pure normalization tests — 246 tests green
- Model-agnostic LLM provider factory with ask.domain retrofit — single construction path for all gates.
- Governance-aware single-result scoring: a normalized SearchResult becomes a validated, ceiling-clamped ScoredFinding with thresholds echoed (D-06) and workspace taxonomy soft-injected (D-11) — read-only, offline-testable via mock LLM.
- Turns single-item scoring (Plan 02) into a usable batch gate: bounded concurrent fan-out (D-04), per-item retry-once-then-skip-with-reason and a gate-level degraded flag (D-08), total-provider-outage promotion to a gate error (D-09), key-safe error messages (T-09-03), and a read-only `run_gate()` that assembles a fully-populated `ResearchScoreGateOutput` (T-09-05).
- Exposes the `research.score` L3 gate on both CLI and MCP through the shared capability registry (RSCH-01 criterion 1): one `CapabilityRecord` + `_research_score_shim` adapter, a `construct research score` subcommand with pre-fetched-payload plumbing (D-10) and a D-13 table/JSON result shape, automatic `construct_research_score` MCP exposure, and contract tests proving CLI/MCP parity and the D-09 outage→`success=False` mapping.
- 1. [Rule 3 - Blocking] Reverted auto-regenerated build stamp from each commit
- Stdlib-only URL normalization, deterministic ref-ID derivation, title fuzzy near-dup detection, and a rejected-findings ledger that make research.run reruns idempotent without the D-07 collision suffixer.
- A checkpointed LangGraph workflow that composes Phase 8 search + Phase 9 scoring, pauses at a real `interrupt()` exposing a per-finding `gate_queue`, writes nothing before approval, and short-circuits total provider outage to END before the gate.
- Approved-only idempotent ingest (deterministic IDs + skip-if-exists), template digest with DigestRecord + degraded notice, seed last_queried updates with D-11 events, and research.review/inspect runners that resume or inspect a paused run across process restarts — closing the durable research.run workflow with a D-12 RunResult.
- research.run/review/inspect exposed through the shared registry with dual-mode sanitizing shims, registry-dispatched Typer CLI commands + a RunResult renderer, and auto-discovered MCP tools — CLI/MCP/registry parity proven by contract tests with zero edits to mcp/server.py.
- A collectable, intentionally-failing pytest suite that pins every CUR-01 distinction (real findings, completed-vs-degraded, skipped-deferred, threshold honoring, no-canonical-writes, anti-placeholder) as the executable spec for the curation.run module and its CLI/MCP wiring.
- `src/construct/llm/curation_run.py` — the real deterministic curation pipeline (five findings-bearing steps over the full spec §4.3 topology, three explicit deferred skips, durable SqliteSaver checkpointing, and D-09 completed/degraded aggregation) that replaces the v0.3 placeholder no-ops and turns the Plan 01 llm red suite GREEN.
- Wires `curation.run` and `curation.inspect` into the shared capability registry with RT-03 dual-mode keyword-only shims and adds the `curation` Typer sub-app (run/inspect) with a per-step renderer — turning the Plan 01 contract suite fully GREEN and delivering CUR-01's CLI + auto-discovered stdio-MCP invocation surface, with MCP parity free (no `mcp/server.py` edit) and the legacy placeholder path left intact (D-11).
- Authored the full Wave-0 failing-test net for Phase 12 — card.evaluate/connection-typing gate units, curation.run HITL + no-unreviewed-write integration tests, CLI/MCP parity + no-placeholder contract guards, and the API-04 skill forbidden-tool guard — all RED now and each a named GREEN target for Plans 02-06, with zero production code touched.
- Two propose-only L3 LLM judgment gates — card.evaluate (promote/hold/escalate PromotionDecision) and connection-typing (ConnectionTypeDecision over bridge_detect pairs) — copied symbol-for-symbol from research_score.py with retry-then-escalate and total-outage discrimination.
- Grafted the read-side of the research_run HITL machine onto curation_run.py: three deferred skip-nodes became proposal PRODUCERS that compute promotion / connection / archive proposals into ONE heterogeneous gate_queue, process_inbox became an interrupt-only consolidated review gate keyed by the module constant `_CURATION_GATE_ID`, and a conditional short-circuit routes an empty queue straight to compile_report without pausing — establishing the CUR-03 spine by construction (no write node exists upstream of the interrupt).
- Grafted the write-side of the curation HITL machine: three approved-only, idempotent post-gate apply nodes behind the single human interrupt, full per-step + gate-review event emission (spec 6.6), and pause-aware review/inspect runners — the entire tests/llm/test_curation_run.py suite is GREEN.
- card.evaluate + curation.review registered with CLI/MCP parity via the shim pattern, `construct card evaluate` / `construct curation review` commands added, and the D-10 curation-cycle fake-success placeholder removed atomically from catalog.py + cli.py.
- None functional.
- Thin `daily.run` composition that calls research.run → curation.run → graph.status, auto-applies each gate's recommended decisions via the child `approve_all` resume, excludes escalate (surfaced as a pending count), isolates-and-degrades on child failure, and never reports a false `completed`.
- Registered `daily.run` + `daily.inspect` in the capability registry and exposed a `daily` Typer sub-app by mechanically cloning the curation quartet; MCP parity is free via registry auto-discovery (mcp/server.py untouched), proving API-01/02/03 with a cloned contract test.
- Repointed the daily-cycle workflow doc at the real `construct daily run` capability and made the skill own the single post-run views refresh (D-10), then proved API-05 with a full pytest suite green (400 passed) — the additive daily capability introduces zero v0.3/v0.4 regressions.

**Requirements:** 22/22 mapped · 22 Complete · 0 Partial · 0 unsatisfied. Phase verifications all passed; final full suite 404 tests green.

**Known deferred items at close:** None blocking. Carry-over debt remains deferred to later tracks — RT-01/RT-02 registry unification (views/spike/tag command groups), full `views.generate_data` emission, and historical per-phase verification/Nyquist/security documentation gaps. Advisory (non-blocking) robustness findings from Phase 13 code review (WR-01/02/03 in `13-REVIEW.md`) are latent, not observed failures. See STATE.md "Deferred Items".

---

## v0.3 Claude-Native Runtime & Workflow Hardening (Shipped: 2026-06-16)

**Phases completed:** 7 phases (1–7), 25 plans
**Git range:** d62de4a (first commit) → v0.3 tag, retagged to include build hooks/versioning
**Definition of done:** Harden CONSTRUCT's Claude-native runtime and workflow foundation — one canonical artifact contract, reliable knowledge operations, a shared capability/CLI/MCP runtime spine, dependable guided workflows, grounded graph reasoning, and v0.5-facing derived-data contracts — without pulling browser-UI work ahead of proven backend behavior.

**Key accomplishments:**

- **Phase 1 — Contract canon & governance:** Canonical Claude-native workspace contract (schemas, authority rules, pre-write gates) proven against the `test-ws/` fixtures, with a published migration playbook.
- **Phase 2 — Governed knowledge operations:** Reliable card / ref / connection / storage CRUD with non-blocking event logging and source→domain routing.
- **Phase 3 — Capability registry, CLI & MCP spine:** Deterministic capabilities exposed through one shared runtime contract, with a stdio MCP server as the agentic surface.
- **Phase 4 — Guided workflow operability:** State-aware help/ingestion and a WorkflowRunner with persisted state and resume-from-last-successful-step; skills migrated to the CLI/MCP invocation pattern.
- **Phase 5 — Grounded synthesis & graph reasoning:** Bounded question-answering, synthesis, and bridge detection grounded in workspace cards/connections with confidence-aware hedging.
- **Phase 6 — Derived data, ops UI & governed spikes:** Pydantic data contracts for the 8 views files, a Streamlit ops dashboard, and isolated governed spikes (tag extraction, Graphify/InfraNodus evaluation).
- **Phase 7 — Closed the v0.3 audit blockers:** RT-03 (MCP schema parity), ING-02 (ingest cluster validation), and ING-05 (graph.status wiring) — milestone re-audits to **0 unsatisfied requirements** (228 tests passing after final build/versioning work).

**Requirements:** 28/28 mapped · 26 Complete · 2 Partial (RT-01/RT-02 registry-bypass + direct-import command groups, deferred to v0.4) · 0 unsatisfied.

**Known deferred items at close:** 2 UAT items acknowledged and accepted for close (Phase 06 partial UAT — 1 issue / 1 blocked, 0 pending; Phase 07 HUMAN-UAT passed). Plus accepted tech debt catalogued in `milestones/v0.3-MILESTONE-AUDIT.md` (curation-cycle no-op steps, views.generate_data stub, ADV-03 view emission, SPK-04 entry point, CR-02 help.py layout, missing per-phase VERIFICATION/Nyquist/SECURITY coverage). See STATE.md "Deferred Items".

---
