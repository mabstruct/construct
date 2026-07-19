# Phase 10: Durable Human Review + research.run - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 10-durable-human-review-research-run
**Areas discussed:** Orchestration engine, Review interface & persistence, Idempotency & dedup, Digest creation

---

## Orchestration engine

User first asked to clarify the difference between "Extend WorkflowRunner" and "LangGraph + JSON checkpointer" before answering (both are file-based, no SQLite). Clarified: alt 1 reuses the existing step-list engine with a hand-rolled pause (`awaiting_review` + a step that declines, runner halts and saves); alt 3 adopts LangGraph's native `interrupt()`/`Command(resume=)` but requires writing a custom JSON checkpointer (giving up `SqliteSaver`). The real difference is the orchestration paradigm + pause mechanism, not where state lands.

| Option | Description | Selected |
|--------|-------------|----------|
| Extend WorkflowRunner | Add `awaiting_review` + gate_queue to existing file-state runner; hand-rolled pause; reuse resume() | |
| LangGraph + JSON checkpointer | LangGraph StateGraph + native interrupt(), custom JSON checkpointer (no SQLite) | |
| Adopt LangGraph + SqliteSaver | Full LangGraph with built-in SqliteSaver; least custom durability code; needs v0.4 scope exception | ✓ |

**User's choice:** Adopt LangGraph + SqliteSaver.
**Notes:** Chose the off-the-shelf SqliteSaver despite it being flagged as a v0.4 scope exception (SQLite is in the Out-of-Scope table). Confirmed in the follow-up below that this is a deliberate override.

### Follow-up: SQLite scope boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Override, checkpoint-state only | SQLite holds ONLY LangGraph checkpoint/resume state; SOT stays files; amend REQUIREMENTS.md Out-of-Scope to carve out the checkpointer | ✓ |
| Override, no carve-out note | Same choice but don't amend REQUIREMENTS.md now | |
| Reconsider — custom JSON checkpointer | Avoid SQLite entirely; LangGraph + custom JSON-file checkpointer | |

**User's choice:** Override, checkpoint-state only.
**Notes:** SQLite is orchestration scratch state only; canonical SOT (cards/refs/seeds/connections/events/digests) stays file-based — the "no DB owns facts" rule holds. REQUIREMENTS.md Out-of-Scope to be amended with a carve-out for the LangGraph checkpointer SQLite. Resolves spec open question J1 in favor of LangGraph for this workflow.

---

## Review interface & persistence

| Option | Description | Selected |
|--------|-------------|----------|
| CLI/MCP review capabilities | Run pauses → gate_id + pending findings; inspect/status + review/resume capabilities → Command(resume=); Streamlit becomes optional read view | ✓ |
| Streamlit-primary, CLI/MCP minimal | Streamlit gate_review as main surface (over persisted checkpoint), thin CLI status only | |
| Resume-payload only | No dedicated review capability; re-invoke run with --decisions payload | |

**User's choice:** CLI/MCP review capabilities.
**Notes:** Satisfies RSCH-04's "inspect/resume through the CONSTRUCT surface" with full CLI/MCP parity and restart durability. Existing `gate_review.py` (currently Streamlit session-state only) demoted to optional read view over the same checkpoint.

### Follow-up: review granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-finding, with bulk convenience | Per-finding approve/reject (default = LLM ingest_action) + approve-all/reject-all | ✓ |
| Batch-only | Approve/reject the whole batch as one unit (spec's "approve batch" wording) | |
| Per-finding, no bulk shortcut | Per-finding only, no approve-all | |

**User's choice:** Per-finding, with bulk convenience.
**Notes:** RSCH-03 reads per-finding ("review, approve, or reject research findings"). Default suggested decision per finding = the score gate's `ingest_action`; only approved findings ingest.

---

## Idempotency & dedup

Surfaced a trap: existing `_deduplicate_ref_id()` suffixes collisions (`url-2.json`), which on rerun creates duplicates — the opposite of idempotency. research.run needs URL-identity dedup instead.

| Option | Description | Selected |
|--------|-------------|----------|
| Normalized-URL exact + title-fuzzy | Normalized URL vs refs/ + within batch, plus title fuzzy near-dup pass | ✓ |
| Normalized-URL exact only | Defer title-fuzzy to later hardening | |
| Raw-URL exact only | No normalization | |

**User's choice:** Normalized-URL exact + title-fuzzy.

### Follow-up: idempotency persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Rejected ledger file + deterministic ref IDs | Persistent research/rejected.json ledger; dedup filters vs refs/ AND ledger; deterministic URL-derived ref IDs + skip-if-exists for partial-batch safety | ✓ |
| Derive rejections from events.jsonl | Reconstruct rejected set by scanning gate_review_rejected events each run | |
| Checkpoint-state only | Track rejects + completed IDs only in the run checkpoint (weak cross-run) | |

**User's choice:** Rejected ledger file + deterministic ref IDs.
**Notes:** Bypass the suffixing helper for research.run. Deterministic ref IDs from normalized URL + skip-if-exists makes resume/rerun naturally idempotent.

---

## Digest creation

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic template only | PIPE templating from approved findings + counts + degraded notice; defer L2 narrative | ✓ |
| Template + optional L2 narrative gate | Add optional L2 LLM prose summary | |

**User's choice:** Deterministic template only.

### Follow-up: digest output format

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown file + DigestRecord JSON entry | digests/<id>.md + append DigestRecord to digests.json; path in run result | ✓ |
| DigestRecord JSON only | Structured record only, no markdown | |
| Markdown file only | Readable file only, no structured record | |

**User's choice:** Markdown file + DigestRecord JSON entry.
**Notes:** Keeps the only LLM call as the L3 score gate; digest carries the score gate's degraded/retried signal.

---

## Claude's Discretion

- LangGraph node/edge topology + state-channel schema (gate must be a real `interrupt()`).
- Checkpoint DB location/filename + thread/gate_id scheme.
- URL-normalization details, title-fuzzy threshold/algorithm, rejected-ledger path/shape.
- Deterministic ref-ID derivation function.
- Digest markdown template + DigestRecord.id scheme.
- New review/inspect capability IDs + CLI/MCP names (follow research.score pattern).
- ingest_batch concurrency (preserve per-finding isolation).
- build_queries cluster selection, update_seeds last_queried edge cases, run result schema internals (spec/requirements-determined; no separate question asked).

## Deferred Ideas

- L2 narrative digest (optional LLM prose summary).
- Title-fuzzy dedup tuning / additional dedup signals.
- Curation workflow (Phase 11/12), daily-cycle composition (Phase 13).
- Additional/academic search providers (PROV-01, future).
- Migrating WorkflowRunner flows onto LangGraph / orchestration convergence (spec line 559, future).
</content>
