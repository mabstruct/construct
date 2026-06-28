# Phase 10: Durable Human Review + research.run - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers **`research.run`** — a single durable, human-gated workflow capability (CLI + MCP) that composes the pieces built in Phases 8–9 into one reviewed research cycle:

```
load_config → build_queries → execute_search → deduplicate
  → score_and_extract (L3 research.score gate)
  → gate_review (HUMAN interrupt — approve/reject before any writes)
  → ingest_batch (refs + cards, approved only)
  → compile_digest → update_seeds_and_log → (optional views_refresh_hook)
```

It must: **pause** for human review before any workspace write; **resume across process restarts** with pending review state intact; **rerun idempotently** (no duplicate URLs, refs, re-proposed rejects, or double-written partial batches); and return a **run result** exposing status, gate IDs, approved-ingest counts, digest path, seed-update status, and emitted events.

**Hard boundary (carried from Phase 9 D-10):** `research.score` stays a pure read-only scoring gate. ALL writes — refs, cards, seed `last_queried`, digest artifacts, events — are owned by `research.run`, behind the human approval gate.

Requirements: **RSCH-02** (compose the workflow), **RSCH-03** (review/approve/reject before writes), **RSCH-04** (resume/inspect paused run across restarts), **RSCH-05** (idempotent reruns). (4 requirements.)

**Not in this phase:** curation workflow (Phase 11/12), daily-cycle composition (Phase 13), additional search providers (deferred), L2 narrative digest (deferred below).

</domain>

<decisions>
## Implementation Decisions

### Orchestration Engine
- **D-01:** `research.run` is orchestrated with **LangGraph `StateGraph`** (not the existing `WorkflowRunner`). The human gate uses LangGraph's **native `interrupt()`**; resume uses **`Command(resume=decisions)`**. This is the first time LangGraph drives a whole durable workflow here (today it only powers the linear `ask_domain` L2 gate). **Resolves the spec's open question J1 / line 614 in favor of LangGraph for this workflow.**
- **D-02:** Durable state is persisted via LangGraph's **`SqliteSaver` checkpointer**. **Scope exception (accepted):** the v0.4 "no SQLite" Out-of-Scope constraint is carved out for **workflow orchestration/checkpoint state only**. The SQLite store holds ONLY resumable LangGraph checkpoint state; the canonical SOT (`cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`, `digests/`) **stays file-based** — the "no database owns any facts" architecture rule is preserved. Checkpoint DB lives under workspace state (e.g. `.construct/` or a workflow state dir), not in the SOT tree. **Action:** update `REQUIREMENTS.md` Out-of-Scope to record this carve-out (see canonical_refs / git follow-up).

### Human Review Interface & Persistence
- **D-03:** Review is driven through **new registry-backed CLI/MCP capabilities** (full parity), not Streamlit-only. `research.run` pauses and returns a **`gate_id` + the pending scored findings**. An **inspect/status** capability lists the pending batch; a **review/resume** capability submits decisions and continues the graph via `Command(resume=...)`. The existing Streamlit `gate_review.py` becomes an **optional read view** over the same persisted checkpoint (no longer the only/authoritative surface, and no longer session-state-only).
- **D-04:** Review granularity is **per-finding** (RSCH-03 reads per-finding). Each finding carries its own approve/reject decision; the **default suggested decision = the LLM's `ingest_action`** from `research.score`. Provide **`approve-all` / `reject-all`** convenience. **Only approved findings are ingested**; rejected findings are recorded to the ledger (D-06). The persisted `gate_queue` holds per-finding decision state.

### Idempotency & Dedup (RSCH-05)
- **D-05:** The `deduplicate` step keys on **normalized URL** (lowercase host, strip tracking params + fragment + trailing slash, normalize http/https) matched against existing `refs/*.json` `url` fields **and** within the current batch, **plus a title fuzzy-match** secondary pass (token/ratio threshold) to catch same-article-different-URL near-dups. Deterministic and offline-testable.
- **D-06:** A persistent **rejected-findings ledger** (a workspace file, e.g. `research/rejected.json`) records normalized URL + `gate_id` + timestamp on every reject. The `deduplicate` step filters incoming results against **both `refs/` and this ledger**, so previously rejected findings are never re-proposed on rerun.
- **D-07:** **Partial-batch resume safety:** derive each ref ID **deterministically from the normalized URL** (not the suffixing `_deduplicate_ref_id` helper) and **skip-if-exists** on (re)ingest. Combined with LangGraph checkpoint resume, a crash mid-`ingest_batch` re-runs safely without double-writing refs/cards. **Explicitly do NOT use `_deduplicate_ref_id()` for `research.run`** — its `-2`/`-3` suffixing creates duplicates on rerun (the opposite of idempotency).

### Digest Creation
- **D-08:** `compile_digest` is a **deterministic template (PIPE) step — no LLM**. It builds the digest from approved findings + run counts (considered / approved / rejected / ingested), a degraded-state notice (carried from the score gate), and created ref/card IDs. Keeps the L3 score gate as the only LLM call. The optional L2 narrative summary is **deferred** to a later phase.
- **D-09:** `compile_digest` writes **both** a human-readable markdown digest at **`digests/<id>.md`** AND appends a structured **`DigestRecord`** (existing schema: `id`, `domain_id`, `title`, `generated_at`, `card_ids`, `summary`) to the digests store (`digests.json`). The **digest path is surfaced in the run result** (success criterion 5).

### Workflow Composition & Result (spec/requirements-determined — Claude's discretion on internals)
- **D-10:** `build_queries` derives the query list from **active `search-seeds.json` clusters** (respecting `status` and governance caps); `research.run` owns the full **search → score composition** (Phase 9 D-10 — `research.score` does not run search itself).
- **D-11:** `update_seeds_and_log` sets **`last_queried`** on the clusters that were queried this run, and emits events: **`research_search_complete`**, **`research_score_gate_complete`**, **`gate_review_approved` / `gate_review_rejected`** (per-finding, existing protocol), and **`research_cycle_complete`** on full completion (spec §6.6). Append via the existing `append_event()`.
- **D-12:** The **run result** satisfies success criterion 5: run status (`completed` / `awaiting_review` / `failed`), gate IDs, approved-ingest counts (refs + cards created), digest path, seed-update status, and the list of emitted events.

### Claude's Discretion
- LangGraph node/edge topology and state-channel schema (provided the gate is a real `interrupt()` and per-step writes stay behind it).
- Exact checkpoint DB location/filename under workspace state; checkpointer thread/`gate_id` scheme.
- URL-normalization rule details and the title fuzzy threshold/algorithm; ledger file exact path/shape.
- Deterministic ref-ID derivation function from normalized URL.
- Digest markdown template wording/structure and `DigestRecord.id` scheme.
- New review/inspect capability IDs and CLI/MCP names (follow the `research.score` registration + shim pattern for parity).
- Concurrency for `ingest_batch` (keep per-finding error isolation).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 10 goal + 5 success criteria; phase sequencing (Phases 8–13); `Depends on: Phase 9`.
- `.planning/REQUIREMENTS.md` — RSCH-02..05 (lines 23–26); the invocation contract (line 11, CLI/MCP/registry); Out-of-Scope table (**update the "no SQLite" row to carve out the LangGraph checkpointer per D-02**).
- `.planning/PROJECT.md` — v0.4 milestone scope, local-first constraint, product-continuity constraint (v0.3 behavior must keep passing, API-05).

### Specification (primary)
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — Key sections:
  - §4.4 (lines 136–153) — **research cycle target graph topology** (the node sequence D-01 implements) + hybrid path note.
  - §5.3 (lines 192–201) — **human-in-the-loop gate protocol** (approve/reject → events → SOT write allowed/blocked); `review_required: true` default.
  - §5.2 (lines 185–191) — registry integration; every workflow entrypoint is a `CapabilityRecord`; CLI/MCP 1:1 with capability IDs; handlers return `OperationResult` / gate output models.
  - §6.5 (lines 297–312) — **`WorkflowRunState`** schema (`status` incl. `awaiting_review`, `gate_queue`) — informs the checkpoint/state channel even under LangGraph.
  - §6.6 (lines 314–326) — **event types** (D-11): `research_search_complete`, `research_score_gate_complete`, `research_cycle_complete`, `gate_review_approved/rejected`, `workflow_step_complete`.
  - §6.1–6.3 (lines 229–284) — `SearchResult`, `SearchBatchOutput`, `ScoredFinding`, `ResearchScoreGateOutput` (the I/O flowing search → score → review).
  - §9 / line 541, 614 — acceptance walkthrough; **open question J1 (LangGraph vs WorkflowRunner) — resolved by D-01**.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Layer model + L1/L2/L3 gate tiers; registry/CLI/MCP 1:1 rule (A.1).

### Phase 9 carry-forward (the score gate this composes)
- `.planning/phases/09-llm-provider-factory-research-score/09-CONTEXT.md` — D-10 (score gate owns no writes; run owns composition), D-05 clamp, D-08/09 degraded-state vs total-outage distinction (the digest's degraded notice consumes this).

### Governance / config
- `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml` — `research:` block: `relevance_threshold`, `card_creation_threshold`, `max_papers_per_cycle` (caps consumed by `build_queries` / `load_config`).

### Primary code references (patterns to follow / files to touch)
- `src/construct/llm/ask_domain.py` — existing LangGraph `StateGraph` usage (`build_ask_domain_graph`, lines ~315–335) — the LangGraph pattern to extend for orchestration + interrupt.
- `src/construct/llm/research_score.py` — the L3 gate `research.run` invokes (`run_gate("research.score", ...)`, `GateMetadata`, `ResearchScoreGateOutput`).
- `src/construct/pipelines/workflow_runner.py` — existing file-state runner + `workflow-state.json` (NOT used to orchestrate research.run per D-01, but its state/resume/event conventions and `WorkflowRunState` shape inform the LangGraph state channel).
- `src/construct/pipelines/ingestion.py` — `_write_ref_file`, `create_card`, `_seed_card_body`, and `_deduplicate_ref_id` (**the helper to AVOID for research.run per D-07**); the `ingest_source` event.
- `src/construct/ui/gate_review.py` — existing Streamlit review + `_log_gate_event()` (`gate_review_approved/rejected`); becomes optional read view (D-03), reused event protocol.
- `src/construct/services/event_log.py` — `append_event()` + `EventAgent`/`EventResult` (D-11).
- `src/construct/capabilities/catalog.py` + `registry.py` — `CapabilityRecord` registration + shim pattern (`_research_score_shim`); register `research.run` + review/inspect capabilities here.
- `src/construct/cli.py` — Typer command group + capability dispatch (`research score` → add `research run` + review commands).
- `src/construct/mcp/server.py` — MCP auto-discovery from registry (parity for free).
- `src/construct/schemas/config.py` — `ReferenceRecord`, `SearchSeedsFile` / `SearchCluster` (`last_queried`), `EventRecord`.
- `src/construct/schemas/card.py` — `KnowledgeCard`, `CardSource`.
- `src/construct/views/models.py` — `DigestRecord` / `DigestsFile` (D-09).

### Tests (offline patterns to extend)
- `tests/llm/conftest.py` — `ConfigurableStructuredMock`, `InvalidOutputMock`, `TotalOutageMock`, `create_test_workspace`, `sample_search_results` — mock score-gate outputs for full-run offline tests.
- `tests/unit/test_workflow_runner.py` — state/resume test pattern to mirror for LangGraph checkpoint resume.
- `tests/llm/test_research_score.py`, `tests/contract/`, `tests/integration/` — gate, CLI/MCP parity, and end-to-end conventions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`research.score` gate** (`run_gate`, `ResearchScoreGateOutput`, `GateMetadata`, degraded flag) — invoked directly as the `score_and_extract` step.
- **LangGraph in `ask_domain.py`** — `StateGraph` build/compile pattern already in the repo; extend it for orchestration + `interrupt()`.
- **Ingestion writers** (`_write_ref_file`, `create_card`, `_seed_card_body`) — reuse for `ingest_batch`; wrap with deterministic-ref-ID skip-if-exists (D-07).
- **`append_event()`** + existing `gate_review_approved/rejected` protocol from `gate_review.py` — reuse for D-11 events.
- **Registry shim pattern** (`_research_score_shim`) — template for `research.run` + review/inspect capability handlers (CLI/MCP parity for free).
- **Mock LLM + sample_search_results fixtures** — drive offline full-run tests without live providers.

### Established Patterns
- Gate I/O models live in the gate module (avoid circular imports) — applies to any new run/review I/O models.
- Registry auto-exposure → CLI + MCP parity (Phase 8/9).
- Fail-loud, no silent fallback; per-item error isolation (Phase 9 D-08) — the run preserves this through to digest's degraded notice.
- Append-only `log/events.jsonl` is the audit trail; never truncate.

### Integration Points
- **New:** `research.run` workflow module (LangGraph graph + PIPE step handlers), review/inspect capabilities, rejected-ledger I/O, digest writer, seed `last_queried` updater, checkpointer wiring.
- **Modify:** `capabilities/catalog.py` (register run + review/inspect), `cli.py` (`research run` + review commands), `pyproject.toml` (langgraph checkpointer extra if needed), `REQUIREMENTS.md` (Out-of-Scope SQLite carve-out).
- **Bridges:** Phase 8 `search/` (input), Phase 9 `research_score` (gate), ingestion + event_log + seeds + digests (outputs, gated).

</code_context>

<specifics>
## Specific Ideas

- Resolve spec open question **J1** explicitly in the plan: LangGraph orchestrates `research.run`; the existing `WorkflowRunner` is not retired but is not used here.
- The SQLite checkpointer is **orchestration scratch state only** — document this boundary loudly so it isn't mistaken for SOT (and so Phase 11–13 reuse the same split deliberately).
- Default review decision per finding = the score gate's `ingest_action`, so "approve-all" reproduces the LLM's recommended ingest set.
- Digest must carry the **degraded/retried** signal from the score gate (Phase 9 D-08/09), so a partial-provider run is visible to the human.

</specifics>

<deferred>
## Deferred Ideas

- **L2 narrative digest** (optional prose summary via LLM) — considered, deferred from D-08; template-only this phase.
- **Title-fuzzy dedup tuning / additional dedup signals** — basic threshold this phase; richer near-dup detection is later hardening.
- **Curation workflow, daily-cycle composition** — Phases 11–13 (out of scope here).
- **Additional/academic search providers** — deferred (Phase 8 proved the interface; PROV-01 future).
- **Migrating `WorkflowRunner`-based flows onto LangGraph / converging orchestration** — spec line 559 convergence is future work; this phase only establishes the LangGraph path for `research.run`.

None of these are in Phase 10 scope.

</deferred>

---

*Phase: 10-Durable Human Review + research.run*
*Context gathered: 2026-06-28*
</content>
</invoke>
