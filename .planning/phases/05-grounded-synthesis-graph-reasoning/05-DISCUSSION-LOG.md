# Phase 5: Grounded Synthesis & Graph Reasoning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 05-grounded-synthesis-graph-reasoning
**Areas discussed:** L2 Gate Scope, Bridge Detection Model, Confidence Propagation, Phase 5 Outputs

---

## L2 Gate Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Option A: Unified | One LangGraph L2 gate handling both Q&A and synthesis | |
| Option B: Separate | ask.domain = L2 Q&A gate. Synthesis stays as Claude-native skill | ✓ |
| Option C: Hybrid | ask.domain = L2 Q&A gate. Synthesis gets a Python pipeline handler | |

**User's choice:** Option B — Separate
**Notes:** Synthesis stays Claude-native; ask.domain is the L2 LangGraph Q&A gate.

---

## Bridge Detection Model

| Option | Description | Selected |
|--------|-------------|----------|
| Option A: L1+L2 PIPE | Deterministic structural + category overlap detection in Python | |
| Option B: All three + L3 gate | L1+L2 PIPE, L3 as bounded LLM gate | |
| Option C: Full Python pipeline | Multi-step pipeline combining all three levels, producing bridges.json | ✓ |

**User's choice:** Option C — Full Python pipeline
**Notes:** L1 → L2 → L3 multi-step pipeline producing bridges.json. L3 involves bounded LLM call for semantic assessment.

---

## Confidence Propagation

| Option | Description | Selected |
|--------|-------------|----------|
| Option A: Aggregate score only | Single overall confidence score for the output | |
| Option B: Per-citation annotation | Each cited claim carries source card's confidence inline | |
| Option C: Both | Overall aggregate + per-citation source confidence | ✓ |

**User's choice:** Option C — Both
**Notes:** Overall aggregate in output metadata + per-citation source confidence in structured citations.

---

## Phase 5 Outputs

| Deliverable | Selected |
|-------------|----------|
| ask.domain L2 gate | ✓ |
| bridge.detect pipeline | ✓ |
| bridge.detect capability | ✓ |
| bridges.json derived data | ✓ |
| Update synthesis skill | ✓ |

**User's choice:** All five deliverables selected.

---

## Deferred Ideas

- Full synthesis capability migration to Python — stayed Claude-native per D-02.
- Embedding-based retrieval for ask.domain — keyword rank only in Phase 5.

---

*Phase: 05-grounded-synthesis-graph-reasoning*
*Discussion logged: 2026-06-10*
