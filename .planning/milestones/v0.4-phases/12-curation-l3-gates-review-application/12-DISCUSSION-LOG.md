# Phase 12: Curation L3 Gates + Review Application - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-30
**Phase:** 12-curation-l3-gates-review-application
**Areas discussed:** Promotion gate method, Reviewed-write scope, Review gate composition, Skill migration depth

---

## Promotion gate method

### Q1 — How should card.evaluate decide promote/hold/escalate?

| Option | Description | Selected |
|--------|-------------|----------|
| Rule-first, LLM on borderline | Deterministic governance thresholds first; only borderline cards escalate to the LLM (recommended) | |
| LLM-always | Every candidate goes through the LLM gate; richest reasoning, per-run LLM cost | ✓ |
| Rule-only this phase | Purely deterministic; defer LLM judgment | |

**User's choice:** LLM-always.
**Notes:** Wants a genuine judgment with reasoning (the evidence) on every card; accepts per-run cost.

### Q2 — Which cards get sent to the gate each run?

| Option | Description | Selected |
|--------|-------------|----------|
| Lifecycle-eligible only | Pre-filter to promotable cards past governance gates (recommended) | |
| All non-mature cards | Every card not at terminal lifecycle, each run | ✓ |
| Eligible + not-recently-judged | Eligible filter plus a cooldown window | |

**User's choice:** All non-mature cards.
**Notes:** Pre-filter is simply `lifecycle != mature`; max coverage, no cooldown bookkeeping.

### Q3 — Per-item LLM failure handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Default hold + step degraded | Un-judged cards implicitly hold; step reports degraded (recommended) | |
| Fail the whole step | Any per-item failure fails the entire step | |
| Retry then escalate to human | Retry, then surface still-failing cards as escalate | ✓ |

**User's choice:** Retry then escalate to human.
**Notes:** Failure-escalations disambiguated from genuine ones via `method` field
(`rule-based` + failure note vs `llm-judgment`).

---

## Reviewed-write scope

### Q1 — Which high-impact writes does Phase 12 apply after approval? (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Promotion lifecycle writes | Apply approved promote decisions per target_lifecycle | ✓ |
| Connection typing + writes | Type untyped edges and write connections after approval | ✓ |
| Decay auto-archive application | Apply archiving via reviewed path when auto_archive_on_decay=true | ✓ |

**User's choice:** All three.
**Notes:** Phase 12 is where Phase 11's findings-only/deferred writes all turn on.

### Q2 — How is each untyped edge's connection TYPE decided?

| Option | Description | Selected |
|--------|-------------|----------|
| LLM types each edge | L3 LLM gate assigns type per untyped edge | ✓ |
| Rule-based typing this phase | Deterministic heuristics; defer LLM typing | |
| LLM types only bridge.detect candidates | Only high-value bridges get LLM typing (recommended) | |

**User's choice:** LLM types each edge.
**Notes:** Consistent LLM-always posture; second L3 LLM gate in the phase.

---

## Review gate composition

### Q1 — How is human review structured across the three proposal types?

| Option | Description | Selected |
|--------|-------------|----------|
| Single consolidated gate | One interrupt collects all proposals into one queue (recommended) | ✓ |
| Per-step gates | Each step pauses its own interrupt | |
| Two gates: lifecycle + connections | One gate for card-state, one for connections | |

**User's choice:** Single consolidated gate.
**Notes:** Mirrors research.run; one gate_id/one resume. Defines process_inbox as the
consolidated review queue.

### Q2 — What appears in the consolidated review queue?

| Option | Description | Selected |
|--------|-------------|----------|
| Only actionable proposals | promote + connection + archive; escalate flagged | |
| All decisions reviewable | Every decision including holds | |
| Actionable + escalate only | Actionable items + escalate; plain holds events-only | ✓ |

**User's choice:** Actionable + escalate only.
**Notes:** Default suggested decision = gate recommendation; escalate carries no default write.

---

## Skill migration depth

### Q1 — How thin should the migrated skills become?

| Option | Description | Selected |
|--------|-------------|----------|
| Thin orchestrator | Invoke capability + drive review loop + present (recommended) | |
| Pure pass-through | Shell out and echo; human runs review CLI directly | |
| Orchestrator + scope negotiation | Thin orchestrator PLUS up-front scope negotiation + narrative digest | ✓ |

**User's choice:** Orchestrator + scope negotiation.
**Notes:** Zero direct WebSearch/WebFetch/writes; agent negotiates scope, drives review,
frames digest.

### Q2 — Which skills get migrated?

| Option | Description | Selected |
|--------|-------------|----------|
| All three; fold card-evaluate | Migrate research + curation; fold card-evaluate into Python gate (recommended) | ✓ |
| Just research + curation | Migrate the two cycle skills only | |
| You decide per-skill | Planner determines per-skill treatment | |

**User's choice:** All three; fold card-evaluate.
**Notes:** card-evaluate judgment absorbed into Python gate; skill thin-wrapped or retired.

---

## Claude's Discretion

- Promotion gate batching/fan-out shape — follow research.score precedent (Phase 9 D-04).
- Connection-typing gate registration — own capability vs inline node; follow card.evaluate pattern.
- Consolidated queue item representation — tagged-union proposal envelope (Phase 10 D-04 pattern).
- Review/inspect surface — add curation.review, extend curation.inspect; mirror research.review/inspect.
- Write idempotency / rerun safety for the three new write types — follow Phase 10 posture.

## Deferred Ideas

- Daily-cycle composition (DAY-01) + final CLI/MCP/compatibility parity sweep — Phase 13.
- Full views.generate_data emission (ADV-03) — deferred track; views_refresh_hook stays skipped.
- Last-evaluated cooldown / candidate-set narrowing — rejected now (D-02); revisit if cost bites.
