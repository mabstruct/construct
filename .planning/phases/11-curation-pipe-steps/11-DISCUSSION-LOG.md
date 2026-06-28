# Phase 11: Curation PIPE Steps - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 11-curation-pipe-steps
**Areas discussed:** Runner architecture, Write posture / outputs, Step result contract, Deferred-step handling

---

## Runner architecture

### Q1 — How to build curation.run given Phase 12 adds review interrupts?

| Option | Description | Selected |
|--------|-------------|----------|
| WorkflowRunner now | Real handlers on existing WorkflowRunner; LangGraph in Phase 12 (spec §11 recommended mitigation) | |
| LangGraph from now | Adopt research.run LangGraph + checkpointer pattern now; uniform orchestration | ✓ |
| You decide | — | |

**User's choice:** LangGraph from now.
**Notes:** Overrides the spec §11/§14 "WorkflowRunner first" recommendation in favor of one shared durable model across research and curation.

### Q2 — How much durability machinery to wire now?

| Option | Description | Selected |
|--------|-------------|----------|
| Full checkpointer now | SqliteSaver + run-id + resume/inspect, matching research.run; Phase 12 just adds interrupt() | ✓ |
| Graph now, checkpointer in P12 | Build StateGraph, run in-memory; add durability with the interrupts in Phase 12 | |
| You decide | — | |

**User's choice:** Full checkpointer now.

---

## Write posture / outputs

### Q1 — What do decay/orphan emit in Phase 11?

| Option | Description | Selected |
|--------|-------------|----------|
| Findings report only | Counts + candidate IDs + rationale; Phase 12 re-derives its queues | ✓ |
| Structured proposal queue | Typed proposals into run state for Phase 12 to consume | |
| You decide | — | |

**User's choice:** Findings report only.
**Notes:** No proposal/queue schema committed in Phase 11 — zero coupling to Phase 12 queue format.

### Q2 — decay.auto_archive_on_decay (a write) when true?

| Option | Description | Selected |
|--------|-------------|----------|
| Report only, ignore flag | Never archive; note flag; defer to Phase 12 reviewed path | ✓ |
| Honor flag, archive deterministically | Treat true as operator opt-in to a deterministic write | |
| You decide | — | |

**User's choice:** Report only, ignore flag.
**Notes:** Keeps "human review before lifecycle writes" invariant absolute; Phase 11 performs no canonical writes. Thresholds confirmed to live in governance.yaml (decay_window_days, orphan_tolerance_days).

---

## Step result contract

### Q1 — What makes a deterministic step "degraded"?

| Option | Description | Selected |
|--------|-------------|----------|
| Partial-failure = degraded | Per-step degraded when some items couldn't be processed | |
| Three states only, no partial | Steps are completed / skipped / failed only | ✓ |
| You decide | — | |

**User's choice:** Three states only, no partial (per-step).

### Q2 — Where does criterion #2's "degraded" then live?

| Option | Description | Selected |
|--------|-------------|----------|
| Run-level aggregate | Run = completed/degraded/failed; degraded = finished but ≥1 step failed/skipped | ✓ |
| Failed steps don't degrade run | Run is completed or failed only; user reads failed steps individually | |
| You decide | — | |

**User's choice:** Run-level aggregate.
**Notes:** Reconciles the three-state per-step model with ROADMAP criterion #2's "degraded checks" requirement.

### Q3 — Structured findings or message string?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured findings payload | Machine-readable counts + ID lists + human summary; CurationStepResult model | ✓ |
| Rich message string only | Detailed prose, no structured fields | |
| You decide | — | |

**User's choice:** Structured findings payload.

---

## Deferred-step handling

### Q1 — How do promotion-scan and process-inbox appear in the Phase 11 graph?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit skipped steps | Nodes report "skipped — deferred to Phase 12"; full spec §4.3 shape now | ✓ (Claude recommendation, user deferred) |
| Omit until Phase 12 | Only the 5 real deterministic nodes; insert gates in Phase 12 | |
| You decide | — | |

**User's choice:** You decide → Claude recommended **Explicit skipped steps** (consistent with LangGraph-now / full-checkpointer-now through-line; skip ≠ fake success).

### Q2 — What happens to the legacy workflow.run curation-cycle placeholders?

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect legacy to curation.run | Remove/redirect placeholders so no fake-success path survives | |
| Coexist, leave legacy | Add curation.run new; leave legacy placeholders for Phase 12/CUR-05 | ✓ |
| You decide | — | |

**User's choice:** Coexist, leave legacy.
**Notes:** Flagged for Phase 12/CUR-05 cleanup; criterion #3 targets curation.run's real deterministic steps, so coexistence is acceptable for Phase 11.

---

## Claude's Discretion

- Area 4 step-handling recommendation (Explicit skipped steps) — user deferred.
- `CurationStepResult` exact field names / schema shape — pass through what
  workspace.validate / graph.status / bridge.detect already return where possible.
- Curation graph module location and run-id/inspect CLI command naming — follow the
  research.run precedent.

## Deferred Ideas

- Phase 12 (W5): L3 promotion-scan gate (card.evaluate), process-inbox human-review
  queue, connection typing/writes, decay auto-archive application, research/curation
  skill migrations, legacy placeholder removal (CUR-05).
- Structured proposal/queue handoff between curation steps and Phase 12 gates —
  intentionally not committed now; revisit in Phase 12.
- Full views.generate_data emission (ADV-03) — deferred track.
