# Phase 11: Curation PIPE Steps - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the **real deterministic curation PIPE steps** behind a new `curation.run`
capability — **integrity, decay, orphan, connection-health, and report** —
replacing the v0.3 placeholder no-op handlers. `curation.run` is runnable from the
`construct` CLI and the stdio MCP server, and every deterministic step returns
concrete findings (counts, candidate IDs) with an explicit per-step status; the
overall run distinguishes completed / degraded / skipped (Requirement **CUR-01**,
spec tranche **W4** — "Python only" handlers).

**In scope:** integrity-check, decay-scan, orphan-scan, connection-health (the
read-only bridge.detect portion of connection_maintenance), compile-report, and an
optional views_refresh_hook (reports skipped). LangGraph graph + checkpointer +
run-id/resume/inspect surface for `curation.run`. CLI + MCP parity for the new
capability. Structured `CurationStepResult` contract. Contract tests with the
deterministic steps.

**Out of scope (→ Phase 12, W5):** the L3 `promotion-scan` gate (`card.evaluate`),
`process-inbox` human-review queue, connection **typing**/writes, any high-impact
canonical writes (archiving, lifecycle changes, connection writes), human review
application, and the research/curation **skill migrations**. Daily-cycle
composition is Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Runner architecture
- **D-01:** `curation.run` is a **new LangGraph capability** (its own module,
  mirroring `research.run` in `src/construct/llm/research_run.py`) — **not** the
  legacy `workflow.run curation-cycle` WorkflowRunner path. Chosen over
  "WorkflowRunner-first" (spec §14 Q1 / §11 risk row) so curation and research
  share one durable orchestration model.
- **D-02:** Wire the **full durability machinery now**: `SqliteSaver` checkpointer
  + run-id + resume/inspect surface, matching `research.run` exactly. Phase 11's
  graph is linear (no interrupts yet); Phase 12 grafts `interrupt()` review nodes
  onto the already-durable graph.
- **D-03:** Build the graph to the **spec §4.3 topology whole** from the start so
  Phase 12 swaps node bodies (skip → gate/interrupt) rather than restructuring the
  graph.

### Write posture / step outputs
- **D-04:** Decay and orphan steps are **findings-only** (counts + candidate card
  IDs + rationale in the step result). Phase 12 independently derives its review
  queues — **no proposal/queue schema is committed in Phase 11** (zero coupling to
  Phase 12 queue format).
- **D-05:** Step thresholds are read from **`governance.yaml`** — `decay.decay_window_days`
  drives decay-scan, `quality.orphan_tolerance_days` drives orphan-scan. No
  hardcoded thresholds (config already exists: `DecayConfig`, `QualityConfig`).
- **D-06:** `decay.auto_archive_on_decay` is **reported but never acted on** in
  Phase 11. Even when a workspace sets it `true`, the decay step only reports
  candidates and notes "auto_archive_on_decay=true — archiving deferred to Phase 12
  reviewed path." Keeps the "human review before lifecycle writes" invariant
  absolute. **Phase 11 performs no canonical writes.**

### Step result contract
- **D-07:** Introduce a **`CurationStepResult`** model carrying a **structured
  findings payload** (machine-readable counts + candidate ID lists per step) **plus**
  a human-readable summary line. Downstream skills/views/Phase 12 read fields, not
  parsed prose.
- **D-08:** **Per-step status = `completed` / `skipped` / `failed`** (no per-step
  "degraded"/partial state — any per-item error fails the step).
- **D-09:** **Run-level aggregate status = `completed` / `degraded` / `failed`**,
  where **degraded = the run finished but ≥1 step failed (or a non-optional step
  was skipped)**, `completed` = all steps completed/optional-skipped, `failed` =
  the run aborted. This is where ROADMAP criterion #2's "degraded" lives.

### Deferred-step handling
- **D-10:** `promotion-scan` (L3) and `process-inbox` (HUMAN) appear as **explicit
  nodes that report `skipped — deferred to Phase 12`** in the Phase 11 graph. Skip
  ≠ fake success, so criterion #3 holds. The `views_refresh_hook` likewise reports
  **skipped** (carry-forward: `views.generate_data` deferred, warning-only hooks
  allowed).
- **D-11:** The **legacy `workflow.run curation-cycle` placeholder lambdas**
  (`catalog.py:658–667`) are **left untouched in Phase 11** (coexist). `curation.run`
  is the new canonical path; the legacy placeholder cleanup lands in Phase 12 with
  CUR-05's anti-placeholder test. *Verification note:* criterion #3 targets
  `curation.run`'s deterministic steps (which are real), so coexistence is
  acceptable — but flag the surviving legacy fake-success path for Phase 12.

### Claude's Discretion
- Exact per-step findings field names and the `CurationStepResult` schema shape
  (pass through what `workspace.validate` / `graph.status` / `bridge.detect`
  already return where possible).
- Module location for the curation graph (`src/construct/llm/` vs
  `src/construct/pipelines/`) and the run-id/inspect CLI command naming — follow the
  `research.run` precedent.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement & roadmap
- `.planning/ROADMAP.md` — Phase 11 goal, success criteria; Phase 12 boundary (what defers).
- `.planning/REQUIREMENTS.md` — **CUR-01** (this phase); CUR-02..05 (Phase 12 boundary).

### Spec (authoritative design source)
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §4.3 — Curation cycle target graph topology (PIPE/L3/HUMAN annotations per step).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §6.5 — `WorkflowRunState` persisted runner state.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §11 — risk row "LangGraph complexity vs WorkflowRunner duplication" (the mitigation we chose to override toward LangGraph-now).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §12 — W4 deliverables ("Real integrity/decay/orphan/report handlers (Python only)").
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §14 Q1 — the runner-architecture open question (resolved: LangGraph from now).

### Pattern reference (mirror this)
- `src/construct/llm/research_run.py` — the LangGraph StateGraph + `SqliteSaver` checkpointer + run-id/resume/inspect pattern `curation.run` mirrors; degraded vs total-outage discrimination precedent (Phase 09-03).

### Reusable capabilities & config
- `src/construct/capabilities/catalog.py` — `workspace.validate` (id, ~L194), `graph.status` (~L274), `bridge.detect` (~L361); legacy `_get_workflow_steps("curation-cycle")` placeholders (L658–667).
- `src/construct/pipelines/graph_status.py` — `graph_status()` for the report step.
- `src/construct/pipelines/bridge_detect.py` — `bridge_detect()` for connection-health.
- `src/construct/schemas/config.py` — `DecayConfig` (L162), `QualityConfig` (L169), `GovernanceConfig` (L194).
- `test-ws/my-construct/governance.yaml` — live thresholds (`decay_window_days: 28`, `auto_archive_on_decay: false`, `orphan_tolerance_days: 7`).
- `src/construct/pipelines/workflow_runner.py` — legacy WorkflowRunner (the path being superseded, left intact).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`workspace.validate`** (`catalog.py` id `workspace.validate`) → drives the **integrity-check** step (real validation, not placeholder).
- **`graph.status` / `graph_status()`** → drives the **compile-report** step (node/edge counts, lifecycle distribution, health roll-up).
- **`bridge.detect` / `bridge_detect()`** → drives the **connection-health** step (bridge candidates + untyped-edge counts).
- **`GovernanceConfig` / `DecayConfig` / `QualityConfig`** → supply decay/orphan thresholds; no new config surface needed.
- **`research.run` graph + `SqliteSaver` wiring** → architectural template for the curation graph, checkpointer, run-id and resume/inspect surface.

### Established Patterns
- Capabilities exposed via the registry with `cli_name` + `mcp_tool_name` for CLI/MCP parity (RT-03 dual-mode shim pattern).
- Handlers return `OperationResult(success, message, data)`; the new `CurationStepResult` rides in step `data`.
- No LLM in Phase 11 — purely deterministic Python; the `factory.build_chat_model` seam is **not** needed here (it returns in Phase 12 for the L3 gate).

### Integration Points
- New `curation.run` capability registered in `catalog.py` (CLI + MCP), independent of the legacy `workflow.run curation-cycle` path.
- Events: emit per spec §6.6 conventions (curation cycle completion / step events), consistent with research.run event logging.

</code_context>

<specifics>
## Specific Ideas

- Build the curation graph as a faithful sibling of `research.run` — same checkpointer
  story, same run-id/resume/inspect ergonomics — so Phase 12 only adds the
  `interrupt()` gate node, and the two workflows can converge in one orchestration
  module later (per §11 mitigation).
- "Skipped — deferred to Phase 12" must be a first-class, visible status in the run
  report, distinct from a successful step, so a reader can see the full intended
  curation shape with honest gaps.

</specifics>

<deferred>
## Deferred Ideas

- **L3 `promotion-scan` gate (`card.evaluate`)**, **`process-inbox` human-review
  queue**, **connection typing/writes**, **decay auto-archive application**, and the
  **research/curation skill migrations** — all Phase 12 (W5), CUR-02..05 + API-04.
- **Structured proposal/queue handoff** between curation steps and Phase 12 review
  gates — deliberately not committed now (D-04); revisit in Phase 12 if recomputation
  proves wasteful.
- **Legacy `workflow.run curation-cycle` placeholder removal** — Phase 12 / CUR-05.
- **Full `views.generate_data` emission** (ADV-03) — deferred track; Phase 11 only
  reports the views_refresh_hook as skipped.

None of these arose as scope creep — discussion stayed within the phase boundary.

</deferred>

---

*Phase: 11-curation-pipe-steps*
*Context gathered: 2026-06-28*
