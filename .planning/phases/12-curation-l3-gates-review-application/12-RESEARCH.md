# Phase 12: Curation L3 Gates + Review Application - Research

**Researched:** 2026-06-30
**Domain:** LangGraph human-in-the-loop gates + L3 LLM judgment grafted onto a durable curation graph; reviewed canonical SOT writes; Claude-skill → CLI/MCP delegation
**Confidence:** HIGH (verification target is the live codebase + in-repo spec; the patterns to mirror — `research_run.py`, `research_score.py` — are already shipped and test-covered)

## Summary

Phase 12 is a **grafting phase, not a greenfield phase**. Every mechanism it needs already exists and is test-covered elsewhere in the repo: the consolidated `interrupt()` + `Command(resume=...)` + `SqliteSaver` review loop is fully built in `src/construct/llm/research_run.py` [VERIFIED: codebase]; the L3 `factory.build_chat_model` gate with bounded fan-out, per-item retry, and degraded-vs-total-outage discrimination is fully built in `src/construct/llm/research_score.py` [VERIFIED: codebase]; the curation graph topology (spec §4.3) is already compiled, durable, and linear in `src/construct/llm/curation_run.py` with three `_deferred_step` skip-nodes (`promotion_review`, `process_inbox`, `views_refresh_hook`) sitting exactly where Phase 12's real bodies must land [VERIFIED: codebase, lines 451-460]. The job is to **copy two proven patterns into the curation module and wire two new capabilities + an extended one through the registry**, then migrate three skills to thin orchestrators and delete one legacy placeholder path.

The spine invariant is **"no canonical write without a real LLM judgment AND a human approval."** This is enforced structurally, exactly as `research.run` enforces it: all write nodes live strictly downstream of a single `interrupt()` in `process_inbox`; the interrupt node contains *only* `interrupt()` (no side effects), because LangGraph re-executes the interrupted node top-to-bottom on resume [VERIFIED: codebase, research_run.py:437-452 + comment]. The upstream `promotion_review` and `connection_maintenance` nodes become **proposal producers** that write into one heterogeneous `gate_queue` channel; they never pause and never write.

**Primary recommendation:** Mirror `research_run.py` structurally for the review gate and `research_score.py` structurally for both L3 gates. Add `card.evaluate`, `curation.review`, and extend `curation.inspect` via the existing `cli_name` + `mcp_tool_name` shim pattern (MCP parity is free via registry auto-discovery — proven by Phase 11). Three discrepancies the planner must resolve are flagged in the Assumptions Log (the `seedling` vs `seed` lifecycle naming, the "untyped edge" semantics, and the gate-config additions to `config.yaml`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Promotion gate method (`card.evaluate`)**
- **D-01: LLM-always.** Every candidate card goes through the LLM gate and receives a real promote/hold/escalate judgment; `PromotionDecision.reasoning` is the evidence (CUR-02). Chosen over rule-first/escalation and rule-only — the user wants genuine judgment on every card, accepting per-run LLM cost.
- **D-02: Candidate set = all non-mature cards.** Deterministic pre-filter is simply `lifecycle != mature` (terminal state); every other card is judged each run. Maximum coverage, no cooldown bookkeeping. (Cost/batch-size grows with the graph — accepted.)
- **D-03: Per-item failure → retry-then-escalate.** On LLM timeout / invalid output / partial outage, retry the failing cards; any still-failing card is surfaced into the review queue as `decision="escalate"`. **Disambiguation via the existing `method` field:** failure-driven escalations carry `method="rule-based"` with the failure noted in `reasoning`; genuine borderline escalations carry `method="llm-judgment"`. The review UI/inspect can split on `method`. Mirrors Phase 9 D-04/D-08/D-09.

**Reviewed-write scope**
- **D-04: All three high-impact write types are applied this phase** (all were findings-only / deferred in Phase 11): (1) Promotion lifecycle writes per `PromotionDecision.target_lifecycle`; (2) Connection typing + writes after approval; (3) Decay auto-archive application when `governance.yaml auto_archive_on_decay=true`, through the reviewed path.
- **D-05: Connection typing uses an LLM L3 gate per untyped edge** — `bridge.detect` surfaces candidate/untyped edges; an LLM assigns the connection type with reasoning. Consistent LLM-always posture. This is the **second L3 LLM gate** in the phase.

**Review gate composition**
- **D-06: Single consolidated review gate.** The graph computes ALL proposals (promotions + connection types + decay archives) first, then pauses at **one** `interrupt()` (the `process_inbox` node) collecting them into **one review queue** with one `gate_id` and one resume. Mirrors `research.run` exactly. The upstream `promotion_review` and `connection_maintenance` nodes **produce proposals into the queue rather than each pausing.**
- **D-07: Queue holds actionable + escalate items only.** Items that would cause a canonical write (`promote`, connection-write, archive) plus `escalate` items appear in the queue. Plain `hold` decisions are **events-only**. **Default suggested decision per queue item = the gate's recommendation**; `escalate` items carry **no default write**. Per-item approve/reject with approve-all/reject-all; **only approved items are written.**

**Skill migration (API-04)**
- **D-08: Skills become orchestrator + scope-negotiation thin skills.** Each migrated skill: (a) negotiates scope up front, (b) invokes the Python CLI/MCP capability, (c) drives the review loop conversationally, (d) frames the digest/report narratively. **Zero direct `WebSearch`, `WebFetch`, or workspace writes** survive.
- **D-09: Migrate all three skills; fold `card-evaluate`.** Migrate `construct-research-cycle` and `construct-curation-cycle` to thin orchestrators. `construct-card-evaluate`'s judgment logic is **absorbed into the Python `card.evaluate` gate**; the skill becomes a thin wrapper over `construct card evaluate` (or is retired and invoked inline by the curation skill).

**Derived cleanup (CUR-05)**
- **D-10: Remove the legacy `workflow.run curation-cycle` placeholder lambdas** (`catalog.py` `_get_workflow_steps("curation-cycle")`). Add an **anti-placeholder test** that fails if any placeholder no-op handler or unreviewed canonical write remains in the curation path.

### Claude's Discretion
- **Promotion gate batching/fan-out shape** — single batched call vs per-card bounded concurrency + per-item retry — follow the `research.score` fan-out precedent; D-03's per-item retry implies per-item granularity.
- **Connection-typing gate registration** — its own registered capability vs an inline L3 node inside `connection_maintenance`. No requirement names a separate `connection.evaluate`; follow the `card.evaluate` pattern.
- **Consolidated queue item representation** — a tagged-union proposal envelope (`kind: promotion | connection | archive | escalate` + typed payload); the `gate_queue` channel holds the heterogeneous items.
- **Review/inspect capability surface** — add `curation.review` (resume w/ decisions, mirror `research.review`) and **extend the existing `curation.inspect`** to report pending-review state + outcomes.
- **Write idempotency / rerun safety** for the three new write types — follow Phase 10's deterministic skip-if-exists + checkpoint-resume posture.

### Deferred Ideas (OUT OF SCOPE)
- **Daily-cycle composition (DAY-01)** and the final **CLI/MCP/compatibility parity sweep (API-01/02/03/05)** — Phase 13.
- **Full `views.generate_data` emission (ADV-03)** — deferred track; `views_refresh_hook` continues to report skipped.
- **Last-evaluated cooldown / candidate-set narrowing** — explicitly rejected for now (D-02 sends all non-mature cards each run).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CUR-02 | Evaluate lifecycle promotion candidates through a structured `card.evaluate` gate proposing promote/hold/escalate with evidence | `PromotionDecision` schema verified at spec §6.4 (lines 289-295); mirror the `research_score.score_one`/`score_all` fan-out + retry pattern; candidate set = `lifecycle != mature` per D-02 (Lifecycle enum verified: `seed`/`growing`/`mature`/`archived`, card.py:35-39) |
| CUR-03 | Review and approve/reject lifecycle and connection proposals before canonical card or connection writes occur | Mirror `research_run.gate_review` (interrupt-only) + `_resolve_decisions` + post-gate write nodes; write surfaces verified: `edit_card`/`archive_card`/`add_connection` in services/knowledge.py (lines 241/314/372) |
| CUR-04 | Inspect curation workflow status, degraded states, and emitted events for every deterministic step and review gate | Extend `inspect_curation_run` (curation_run.py:552) to surface `gate_queue` + outcomes like `inspect_research_run` (research_run.py:1038); events via `append_event` per spec §6.6 |
| CUR-05 | Offline tests that fail if placeholder no-op handlers or unreviewed writes remain | Anti-placeholder test pattern already exists (`test_steps_return_concrete_findings`, test_curation_run.py:188); remove `_get_workflow_steps("curation-cycle")` lambdas (catalog.py:730-738) AND the cli.py:208-216 caller |
| API-04 | Migrated research and curation skills delegate to CLI/MCP instead of direct `WebSearch`/`WebFetch`/workspace writes | Three skills inventoried below; `construct-research-cycle` line 3 carries `WebSearch, WebFetch` in `allowed-tools` and uses `WebSearch` at step 3 (lines 53-56) — must be stripped per spec §5.5 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `card.evaluate` promotion judgment | API/Backend (Python L3 gate) | — | LLM judgment + governance clamp must be deterministic and offline-testable; never in skill text (D-01/D-09 fold) |
| Connection-typing judgment | API/Backend (Python L3 gate) | — | Second LLM gate; same offline + clamp posture as promotion (D-05) |
| Consolidated human review | API/Backend (LangGraph `interrupt()`) | Layer 0 skill (conversational driver) | The pause + per-item decision state lives in the checkpointed graph; the skill only *presents* the queue and collects approve/reject (D-06/D-08) |
| Canonical SOT writes (lifecycle/connection/archive) | API/Backend (post-gate graph nodes) | Layer 1 workspace files | Writes are strictly downstream of the interrupt; only Python touches `cards/`, `connections.json` (CUR-03) |
| Inspect/status surfacing | API/Backend (`get_state` read) | Layer 3 CLI/MCP shim | Read-only snapshot of the checkpoint; never re-runs (CUR-04, RT-03) |
| Scope negotiation + narrative digest | Layer 0 skill | — | The only genuinely conversational work; everything else delegates (D-08) |

## Standard Stack

This phase adds **no new external packages.** Everything is already installed and proven in-repo.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | 1.2.4 | StateGraph, `interrupt()`, `Command(resume=...)`, conditional edges | Already the durable-workflow substrate for `research.run` + `curation.run` [VERIFIED: `importlib.metadata.version`] |
| `langgraph-checkpoint-sqlite` | 3.1.0 | `SqliteSaver` persistent checkpointer | Already the carve-out checkpoint store under `.construct/workflow/*.sqlite` (RSCH-04 / D-02) [VERIFIED: `importlib.metadata.version`] |
| `langchain-core` | (installed) | `HumanMessage`/`SystemMessage`, `with_structured_output` | Already used by `research_score._build_messages` + `score_one` [VERIFIED: codebase] |
| `pydantic` | (installed) | I/O models, structured-output targets | Already the contract layer for every gate/result [VERIFIED: codebase] |

### Supporting (in-repo modules to reuse, not reimplement)
| Module / Symbol | Purpose | When to Use |
|-----------------|---------|-------------|
| `construct.llm.factory.build_chat_model` | Provider-agnostic chat model construction | Both L3 gates; it is the monkeypatch seam tests patch (`construct.llm.factory.build_chat_model`) |
| `construct.llm.research_score` (whole module) | Reference shape for L3 gate: `score_one`, `score_all`, `_score_one_with_retry`, `_is_provider_outage_cause`, `ResearchScoreOutageError` | Copy the structure for `card.evaluate` + connection-typing gates |
| `construct.pipelines.bridge_detect.bridge_detect` | Surfaces candidate cross-domain edges (the connection-typing gate's input) | Feed candidate pairs into the connection-typing gate |
| `construct.services.knowledge.edit_card` (line 241) | Lifecycle write surface (`--lifecycle` updates) | Apply approved promotions |
| `construct.services.knowledge.archive_card` (line 314) | Decay auto-archive write surface | Apply approved archives |
| `construct.services.knowledge.add_connection` (line 372) | Connection write surface (idempotent: dedup at lines 416-423) | Apply approved connection typings |
| `construct.services.event_log.append_event` | Append-only audit events (non-blocking) | Gate/review/write/cycle events per spec §6.6 |
| `construct.storage.workspace.WorkspaceLoader` | `load_cards`, `load_connections`, `load_governance` (read-only) | Inside every node (never store loader in state — Pitfall 3) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Mirroring `research_run` interrupt pattern | New bespoke pause mechanism | Rejected — research_run is shipped + test-covered; divergence breaks the "one review model" goal (CONTEXT specifics) |
| Separate `connection.evaluate` capability | Inline L3 node inside `connection_maintenance` | Discretion (CONTEXT). Inline keeps the registry surface minimal; a registered capability mirrors `card.evaluate` for parity. Recommend **inline node calling a gate function** (not a separate registered capability) since no requirement names it and Phase 13 owns the parity sweep |

**Installation:** None. No `npm`/`pip` install step. (Package Legitimacy Audit therefore N/A — see below.)

## Package Legitimacy Audit

**Not applicable.** Phase 12 installs **zero** new external packages — it is a pure code-grafting phase reusing `langgraph` 1.2.4, `langgraph-checkpoint-sqlite` 3.1.0, `langchain-core`, and `pydantic`, all already present in `.venv` and already depended on by the shipped `research.run` / `curation.run` / `research.score` capabilities. No registry lookup, slopcheck, or postinstall audit is required. If the planner introduces a new dependency during planning, run the Package Legitimacy Gate before adding it.

## Architecture Patterns

### System Architecture Diagram

```text
                    curation.run (run-start)
                          │
                          ▼
START → load_config → integrity_check → decay_scan → orphan_scan
                                                          │
                                                          ▼
                                    promotion_review  [L3 GATE: card.evaluate over
                                       (PRODUCER)       all non-mature cards →
                                          │             PromotionDecision[] → enqueue
                                          │             promote/escalate items only]
                                          ▼
                              connection_maintenance  [PIPE bridge_detect + L3 GATE
                                       (PRODUCER)       per candidate edge → typed
                                          │             connection proposals → enqueue]
                                          │
                              decay archive proposals  [from decay_scan + auto_archive
                                       (PRODUCER)        → enqueue archive items]
                                          │
                                          ▼
                          ┌──────── process_inbox ────────┐
                          │     *** interrupt() ***       │   ← SINGLE PAUSE
                          │   one gate_id, one gate_queue │      (no side effects)
                          │   heterogeneous proposals     │
                          └───────────────┬───────────────┘
                                          │  Command(resume=decisions)
                          ┌───────────────▼───────────────┐
                          │   WRITE BOUNDARY (post-resume) │
                          │  apply_promotions  → edit_card │
                          │  apply_connections → add_connection
                          │  apply_archives    → archive_card
                          │  (only-approved-writes; skip-if-exists; events)
                          └───────────────┬───────────────┘
                                          ▼
                              compile_report → views_refresh_hook(SKIP) → END
```

Data-flow notes:
- The three PRODUCER stages run **before** the interrupt and write **only** into `gate_queue` (a checkpointed state channel). They perform NO canonical writes.
- `process_inbox` contains **only** `interrupt()`. On resume it re-executes top-to-bottom (LangGraph semantics) — any side effect there would double-fire and leak a pre-approval write [VERIFIED: research_run.py:437-452].
- All canonical writes sit strictly downstream of the interrupt, so CUR-03 holds **by construction**, identically to RSCH-03.

### Recommended structure (where new code lands)
```
src/construct/llm/
├── curation_run.py        # GRAFT here: replace _deferred_step bodies (451-460);
│                          #   add gate_queue channel, interrupt, write nodes,
│                          #   review_curation_run + extended inspect_curation_run
├── curation_promote.py    # NEW (optional): card.evaluate L3 gate, mirrors
│                          #   research_score.py (PromotionDecision, evaluate_one,
│                          #   evaluate_all, retry/outage)
├── curation_connect.py    # NEW (optional): connection-typing L3 gate
│                          #   (or inline in curation_run.connection_maintenance)
└── research_score.py      # reference only — do not modify
src/construct/capabilities/catalog.py   # register card.evaluate + curation.review;
                                        #   extend curation.inspect; DELETE
                                        #   _get_workflow_steps curation-cycle lambdas
src/construct/cli.py                    # remove _get_workflow_steps_from_registry
                                        #   dependency on the deleted lambdas
```
> Models that the gate runners define MUST live in their own module (e.g. `curation_run.py` / `curation_promote.py`), **never in `catalog.py`** — circular-import hazard, explicitly documented in both `research_score.py:14-16` and `curation_run.py:90-91` [VERIFIED: codebase].

### Pattern 1: Interrupt-only gate node (re-runs on resume → zero side effects)
**What:** The pause node holds nothing but `interrupt()`.
**When to use:** The single `process_inbox` review gate.
**Example:**
```python
# Source: src/construct/llm/research_run.py:437-452 [VERIFIED: codebase]
def gate_review(state):
    # *** ONLY the interrupt primitive. NO writes, NO event emission. ***
    # The interrupted node re-executes top-to-bottom on resume, so any side
    # effect here would double-fire AND leak a write before approval.
    decisions = interrupt({"gate_id": state["gate_id"], "gate_queue": state["gate_queue"]})
    return {"decisions": decisions}
```
For Phase 12 `process_inbox`, the only change is the `gate_queue` payload is **heterogeneous** (promotion | connection | archive | escalate envelopes) instead of per-finding ingest actions.

### Pattern 2: Conditional short-circuit when there is nothing to review
**What:** If a run produces an empty `gate_queue` (no promotions, no connections, no archives), route past the interrupt to `compile_report` so the run completes without pausing.
**When to use:** `process_inbox` predecessor edge.
**Example:**
```python
# Source: research_run.py:831-867 _route_after_score + add_conditional_edges [VERIFIED]
def _route_before_inbox(state):
    return "process_inbox" if state.get("gate_queue") else "compile_report"
builder.add_conditional_edges("<producer>", _route_before_inbox,
    {"process_inbox": "process_inbox", "compile_report": "compile_report"})
```
This mirrors research_run's outage short-circuit (`_route_after_score` → END). Without it, a clean curation run with no proposals would hang at an interrupt with an empty queue.

### Pattern 3: Resume runner with paused-state guard (idempotent completion)
**What:** `review_curation_run` re-opens the same SqliteSaver, checks the snapshot is actually paused at `process_inbox`, then submits `Command(resume=decisions)`.
**When to use:** The new `curation.review` capability.
**Example:**
```python
# Source: research_run.py:996-1035 review_research_run [VERIFIED: codebase]
snap = graph.get_state(cfg)
if snap.next != ("process_inbox",):          # WR-05: never re-resume a completed run
    ...return failed/completed without re-running write nodes...
decisions = _build_resume_decisions(inp, snap.values.get("gate_queue", []))
result = graph.invoke(Command(resume=decisions), cfg)
```

### Pattern 4: L3 gate with per-item retry + outage discrimination
**What:** Bounded `ThreadPoolExecutor` fan-out, one retry per item, total-provider-outage promoted to a gate error; partial failures degrade.
**When to use:** `card.evaluate` and the connection-typing gate.
**Example:**
```python
# Source: research_score.py:406-434 _score_one_with_retry + 458-532 score_all [VERIFIED]
# Per item: try score_one twice; on final failure build a skip/escalate finding.
# Batch: if scored_ok == 0 and provider_failures == len(items) → total_outage=True.
```
For `card.evaluate` the D-03 mapping is: a still-failing card after retry → `PromotionDecision(decision="escalate", method="rule-based", reasoning="<failure>")`; a genuine borderline → `method="llm-judgment"`.

### Pattern 5: Idempotent / skip-if-exists writes (rerun + crash-resume safe)
**What:** Every write checks existence first; a duplicate is a skip, never an overwrite or error.
**When to use:** All three Phase 12 write types.
**Verified write-surface behaviors:**
- `add_connection` already returns `success=True, "Connection already exists"` on a duplicate (from/to/type match) [VERIFIED: knowledge.py:416-423] — connection writes are **already idempotent**.
- Lifecycle promotion via `edit_card` — idempotent if the target lifecycle equals the current; the apply node should skip a card already at `target_lifecycle`.
- `archive_card` — the apply node should skip a card already `lifecycle == archived` (decay_scan already filters archived cards at curation_run.py:317).
- Mirror `ingest_batch`'s per-item `try/except` isolation (research_run.py:611) so one failing write never aborts the batch.

### Anti-Patterns to Avoid
- **Side effects in the interrupt node** — re-fires on resume; leaks pre-approval writes. (research_run.py warns explicitly.)
- **Multiple interrupts (one per proposal type)** — D-06 mandates ONE consolidated gate. Producers enqueue; only `process_inbox` pauses.
- **Storing a `WorkspaceLoader`/sqlite conn/LLM client in graph state** — state holds plain serializable data only (Pitfall 3, documented curation_run.py:69 + research_run.py:68).
- **`print()` in any node** — stdout is the MCP JSON-RPC transport; use `logging` (Pitfall 6, documented curation_run.py:26).
- **Defining gate I/O models in `catalog.py`** — circular import. Define in the gate module.
- **Transient connection-string `SqliteSaver`** — closes the connection on block exit, breaks cross-process resume (Pitfall 2). Use the persistent `sqlite3.connect(..., check_same_thread=False)` form already in `_open_checkpointer`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pause/resume across process restarts | Custom state file + status flags | `interrupt()` + `Command(resume=...)` + `SqliteSaver` (already wired) | Phase 10 proved the durable, cross-process-resume semantics; `WorkflowRunner`/`workflow-state.json` is the legacy path being *removed* (D-10) |
| Bounded LLM fan-out + retry | New executor loop | `research_score.score_all` shape (`ThreadPoolExecutor(max_workers=cap)`) | Async `gather` does not honor the cap (STATE.md Phase 09-03); sync executor does |
| Provider-outage vs partial-degrade | Ad-hoc exception string checks | `_is_provider_outage_cause` + `ResearchScoreOutageError` shape | Already handles word-boundary HTTP codes, auth-phrase markers, MRO type checks, key-safe sanitization (WR-06, T-09-03) |
| Connection write idempotency | Pre-scan connections.json yourself | `add_connection` (dedups internally) | Duplicate detection + orphan/kebab validation already inside the service |
| CLI/MCP dual-mode dispatch | Edit `mcp/server.py` | Register with `cli_name` + `mcp_tool_name`; auto-discovery does the rest | Phase 11 proved MCP parity is free; `test_mcp_no_hardcoded_curation` guards against editing the server |
| Event audit trail | Write JSONL directly from nodes | `append_event` | Non-blocking, append-only, validated; spec §6.6 event types |

**Key insight:** This phase is almost entirely *structural copying*. The risk is not "can we build it" but "do we faithfully preserve the invariants the reference modules encode." Treat every `# Pitfall N` / `# WR-NN` / `# T-NN` comment in `research_run.py` and `research_score.py` as a contract to carry over.

## Runtime State Inventory

> This phase is a code-grafting + capability-addition phase, not a rename/migration. The relevant "runtime state" is the **LangGraph checkpoint store**, which interacts with re-runs.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `curation-run.sqlite` checkpoint DB under `.construct/workflow/` holds Phase 11 run snapshots. Adding `gate_queue` + interrupt changes the graph shape | Old Phase-11 thread snapshots predate the interrupt; `inspect`/`review` on a pre-Phase-12 `run_id` must degrade gracefully (the `not values` → `failed` guard at curation_run.py:569 already covers nonexistent; verify it covers shape-mismatch). Recommend: new runs get fresh `run_id`s; no migration of old snapshots needed. |
| Live service config | `governance.yaml` (`test-ws/my-construct/governance.yaml`) holds `auto_archive_on_decay`, decay/orphan/promotion thresholds — read at runtime, not in git as code | None — read-only consumption; the apply-archive node reads `auto_archive_on_decay` exactly as `decay_scan` already does (curation_run.py:194) |
| OS-registered state | None | None — no OS-level registration involved. Verified: no Task Scheduler / launchd / pm2 surface in this phase. |
| Secrets/env vars | LLM provider keys (`ANTHROPIC_API_KEY` etc.) consumed by `factory.build_chat_model` for the two new gates | None new — same keys the existing `research.score` gate uses; gate config lives in `src/construct/llm/config.yaml` |
| Build artifacts | None | None — no package rename; no egg-info/compiled artifact churn |

**Checkpoint-schema caution:** the single material runtime-state risk is that `curation.run`'s graph topology changes (new nodes + interrupt). A `run_id` checkpointed under the Phase-11 linear graph cannot be resumed under the Phase-12 interrupt graph. This is acceptable because curation runs are short and re-runnable, but the planner should add a test that `inspect_curation_run` on a stale/foreign `run_id` returns `failed` (not a crash).

## Common Pitfalls

### Pitfall 1: Side effects in the interrupt node leak pre-approval writes
**What goes wrong:** Putting event emission or a write in `process_inbox` causes it to fire on the run-start pass AND again on resume, violating CUR-03.
**Why it happens:** LangGraph re-executes the interrupted node top-to-bottom on resume.
**How to avoid:** `process_inbox` contains only `interrupt()`. All writes/events live in post-gate nodes.
**Warning signs:** A `gate_review_approved` event or a connection appearing in `connections.json` before `curation.review` is called.

### Pitfall 2: An empty gate_queue hangs the run at the interrupt
**What goes wrong:** A clean graph with no promotions/connections/archives still pauses, waiting forever for a review that has nothing to review.
**Why it happens:** Unconditional edge into the interrupt node.
**How to avoid:** Conditional edge (Pattern 2) routing empty queues straight to `compile_report`.
**Warning signs:** `curation.run` returns `awaiting_review` with `gate_queue == []`.

### Pitfall 3: Lifecycle name mismatch (`seedling` vs `seed`)
**What goes wrong:** CONTEXT D-04 says "seedling→growing→mature", but the actual `Lifecycle` enum is `seed`/`growing`/`mature`/`archived` (no `seedling`) [VERIFIED: card.py:35-39]. Spec §6.4 `PromotionDecision.target_lifecycle` is `Literal["growing", "mature"] | None` (no `seed`, no `archived`) [VERIFIED: spec:289-295].
**Why it happens:** Informal naming drift in the discussion notes.
**How to avoid:** Promotion transitions are `seed → growing` and `growing → mature` only. `target_lifecycle` is constrained to `growing`/`mature`. Archiving is a **separate** write type (decay path → `archived`), NOT a promotion `target_lifecycle`. The planner must use `seed` everywhere, not `seedling`.
**Warning signs:** A Pydantic validation error on `target_lifecycle="seedling"` or `"seed"`.

### Pitfall 4: "Untyped edges" do not exist as ConnectionRecords
**What goes wrong:** Planning a node that scans `connections.json` for edges with `type == null` finds nothing — `ConnectionRecord.type` is a **required** `ConnectionType` (no `| None`) [VERIFIED: workspace.py:48-54]. A null-typed connection cannot be persisted.
**Why it happens:** "type untyped edges" (D-05, spec §4.3) reads as if untyped records exist.
**How to avoid:** The connection-typing gate's input is **`bridge_detect` candidate pairs** (`from_card_id`/`to_card_id`/`pre_score`/titles, no existing ConnectionRecord) [VERIFIED: bridge_detect.py:233-282]. The L3 gate assigns a `ConnectionType` to a candidate and writes a **new** connection via `add_connection`. It does not retype existing edges. `bridge_detect`'s L1 pass surfaces existing cross-domain *typed* edges separately (lines 120-145) — those are already typed and are not gate inputs.
**Warning signs:** A "find untyped connections" query returning empty; confusion between bridge candidates and existing connections.

### Pitfall 5: Required-vs-optional step status flips the run aggregate
**What goes wrong:** Once `promotion_review`/`process_inbox` become real (no longer `_deferred_step` with `required=False`), the D-09 `_aggregate_status` (curation_run.py:503-511) will now degrade the run if they fail/skip. The current logic degrades on any `required and status in (failed, skipped)`.
**Why it happens:** The deferred nodes were `required=False` specifically so they never degraded a clean Phase-11 run.
**How to avoid:** Decide the `required` flag deliberately: a successfully-reviewed gate should report `completed`; an `awaiting_review` pause is a *new status*, not `degraded`. The aggregate must learn `awaiting_review` (mirror research_run's status set: `running|awaiting_review|completed|failed`, research_run.py:94).
**Warning signs:** A successful reviewed run reporting `degraded`.

### Pitfall 6: The placeholder lives in TWO files, not one
**What goes wrong:** Deleting only `catalog.py:_get_workflow_steps` (D-10) breaks `cli.py:_get_workflow_steps_from_registry` (lines 208-216) and `workflow resume` (line 262), which import and call it.
**Why it happens:** The placeholder is referenced from `catalog.py:310` (the `workflow.run` lambda) AND `cli.py:210/215/216`.
**How to avoid:** The D-10 removal must also rewire or remove the `workflow run curation-cycle` CLI path (`cli.py:208-234, 253-266`). Decide: does `construct workflow run curation-cycle` get removed, or redirected to `curation.run`? The anti-placeholder test (CUR-05) should assert no placeholder handler is reachable from either surface.
**Warning signs:** `ImportError: cannot import name '_get_workflow_steps'` after deletion; `construct workflow run` returning a placeholder success.

## Code Examples

### Heterogeneous gate-queue envelope (Claude's discretion — recommended shape)
```python
# Mirrors GateQueueEntry (research_run.py:142-153) but tagged-union for D-06.
class CurationProposal(BaseModel):
    model_config = {"extra": "forbid"}
    kind: Literal["promotion", "connection", "archive", "escalate"]
    decision: str            # default suggested action = the gate's recommendation (D-07)
    payload: dict            # PromotionDecision dump | connection candidate | card_id
```
Only `promote`/connection-write/`archive`/`escalate` items are enqueued; plain `hold` is events-only (D-07).

### Extended inspect surfacing pending review (CUR-04)
```python
# Source pattern: research_run.py:1038-1082 inspect_research_run [VERIFIED]
snap = graph.get_state(cfg)
if snap.next == ("process_inbox",):
    status, message = "awaiting_review", "Curation run paused awaiting human review."
elif not snap.next:
    status = values.get("status", "completed") if values else "failed"
# surface gate_queue, outcomes, events, degraded — read-only, never resume
```

### Registering the new capabilities (catalog.py)
```python
# Mirrors research.review / research.inspect registration (catalog.py:411-430) [VERIFIED]
registry.register(CapabilityRecord(
    id="curation.review", name="Curation Review",
    description="Resume a paused curation run with per-item decisions; applies approved "
                "lifecycle/connection/archive writes",
    input_model=CurationReviewInput, output_model=OperationResult,
    handler=_curation_review_shim,
    cli_name="curation.review", mcp_tool_name="construct_curation_review",
))
# card.evaluate mirrors research.score registration (catalog.py:389-398).
# Shims mirror _research_review_shim (catalog.py:554-560): reject positional args,
# wrap the runner via _curation_result_to_operation (catalog.py:572-593).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `WorkflowRunner` + `workflow-state.json` (`workflow.run curation-cycle`) | LangGraph graph + `SqliteSaver` checkpoint per workflow | Phase 10 (research.run) / Phase 11 (curation.run) | The legacy placeholder path is dead weight; D-10 removes it. `curation.run` is the sole canonical curation entrypoint |
| Curation writes deferred (findings-only) | Reviewed canonical writes turned on behind one interrupt | Phase 12 (this phase) | Promotion/connection/archive writes land for the first time |
| LLM judgment in skill text (`construct-card-evaluate` SKILL.md) | LLM judgment in Python `card.evaluate` gate | Phase 12 (D-09 fold) | Removes duplicate judgment logic; skill becomes a thin wrapper |
| Skills with `WebSearch`/`WebFetch`/inline writes | Thin orchestrators delegating to CLI/MCP | Phase 12 (API-04) | `construct-research-cycle` `allowed-tools` drops `WebSearch, WebFetch` |

**Deprecated/outdated after this phase:**
- `_get_workflow_steps("curation-cycle")` placeholder lambdas (catalog.py:725-741) — removed (D-10).
- `construct-card-evaluate` SKILL.md inline promotion rules (lines 57-120) — superseded by the Python gate.
- `construct-research-cycle` SKILL.md steps 3-5 inline `WebSearch`/scoring/ingest — superseded by `research.run` (already shipped Phase 10).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The connection-typing gate is an **inline L3 node** inside `connection_maintenance`, not a separately registered `connection.evaluate` capability | Standard Stack / Alternatives | Low — CONTEXT marks this as Claude's discretion; either works. If the planner registers it, add CLI/MCP shim + inventory tests |
| A2 | New gate configs (`card.evaluate`, and a connection-typing gate id) must be **added to `src/construct/llm/config.yaml`** under `gates:` with `provider`, `temperature`, `concurrency_cap`, `review_required` — mirroring the `research.score` block (config.yaml:24-31) | Code Examples / config | Medium — if the gate id is not in `config.yaml`, `load_llm_config` falls back (research_score.py:543 falls back to `research.score`). Confirm the exact gate ids + add config entries, else the gate uses wrong provider/cap |
| A3 | `construct workflow run curation-cycle` (cli.py:219-234) is **removed or redirected to `curation.run`** when D-10 deletes the placeholder | Pitfall 6 | Medium — leaving the CLI command pointing at a deleted function breaks `import`; the planner must decide remove-vs-redirect. User confirmation recommended on whether the `workflow` CLI group survives at all for v0.4 |
| A4 | Pre-Phase-12 `curation-run.sqlite` snapshots need **no migration**; stale/foreign `run_id`s just report `failed` on inspect | Runtime State Inventory | Low — curation runs are short and re-runnable; verify the inspect guard handles shape mismatch, not just nonexistent |
| A5 | The promotion candidate pre-filter `lifecycle != mature` (D-02) is applied **deterministically in `promotion_review` before the LLM fan-out** (archived cards also excluded, mirroring decay_scan:317) | Phase Requirements (CUR-02) | Low — D-02 is explicit; archived exclusion is implied (archived is terminal). Confirm archived cards are excluded from the LLM gate (cost + nonsensical to promote an archived card) |

## Open Questions

1. **Does the `workflow` CLI command group survive v0.4?**
   - What we know: D-10 removes the curation-cycle placeholder steps; `workflow.run`/`workflow.status`/`workflow.resume` capabilities + CLI commands still exist (catalog.py:302-330, cli.py:200-266).
   - What's unclear: whether `construct workflow run` is removed entirely, kept for non-curation workflows (there are none real), or redirected to `curation.run`.
   - Recommendation: Redirect `construct workflow run curation-cycle` → `curation.run` (or remove the `workflow` group) and let the anti-placeholder test (CUR-05) assert no placeholder handler is reachable. Surface to the user during discuss/plan-check.

2. **Exact gate ids + config entries for the two L3 gates.**
   - What we know: `card.evaluate` is named in spec §10 capability table (line 481) as `construct card evaluate` / `construct_card_evaluate` / L3.
   - What's unclear: the connection-typing gate id (no spec name; discretion A1).
   - Recommendation: register `card.evaluate` config in `config.yaml`; for connection typing, reuse a `curation.connection_type` gate id (inline) and add a `config.yaml` entry to avoid the research.score fallback.

3. **`escalate` item semantics on resume.**
   - What we know: D-07 says `escalate` items carry **no default write**; a human must explicitly act.
   - What's unclear: whether approving an `escalate` item triggers a write (and which), or whether escalate is review-only (record outcome, no SOT write this run).
   - Recommendation: Treat `escalate` as review-only this phase (record outcome + event, no canonical write), matching "no default write." Confirm with user.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langgraph` | interrupt/resume graph | ✓ | 1.2.4 | — |
| `langgraph-checkpoint-sqlite` | durable checkpoint | ✓ | 3.1.0 | — |
| `langchain-core` | L3 gate messages/structured output | ✓ | installed | — |
| LLM provider key (`ANTHROPIC_API_KEY`) | live L3 gate calls | n/a at test time | — | Offline tests use the `factory.build_chat_model` monkeypatch seam (no key needed) — proven by `tests/llm/conftest.py` mocks |
| `test-ws/my-construct/governance.yaml` | offline threshold fixtures | ✓ | — | `create_test_workspace` (tests/llm/conftest.py) builds fixtures programmatically |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** Live LLM access is not needed for the test suite — every gate is offline-testable via the `construct.llm.factory.build_chat_model` monkeypatch (the `ConfigurableStructuredMock` / `MockChatAnthropic` seam in conftest).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (3.13 venv) |
| Config file | repo `pyproject.toml` / `pytest` (existing; `tests/` rooted) |
| Quick run command | `.venv/bin/pytest tests/llm/test_curation_run.py -x -q` |
| Full suite command | `.venv/bin/pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CUR-02 | `card.evaluate` returns `PromotionDecision` (promote/hold/escalate) with reasoning over non-mature cards | unit | `.venv/bin/pytest tests/llm/test_curation_promote.py -x` | ❌ Wave 0 |
| CUR-02 | per-item retry; failed card → `escalate` + `method="rule-based"` | unit | `.venv/bin/pytest tests/llm/test_curation_promote.py::test_failure_escalates -x` | ❌ Wave 0 |
| CUR-03 | no canonical write before `Command(resume=approve)` | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_no_writes_before_approval -x` | ❌ Wave 0 (mirror research_run.py:130 test) |
| CUR-03 | approved promotion writes lifecycle; rejected does not | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_reviewed_promotion_applied -x` | ❌ Wave 0 |
| CUR-03 | approved connection typed + written via add_connection; idempotent on rerun | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_reviewed_connection_idempotent -x` | ❌ Wave 0 |
| CUR-03 | auto_archive applied only when approved + `auto_archive_on_decay=true` | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_reviewed_archive_applied -x` | ❌ Wave 0 |
| CUR-03 | single consolidated gate: one gate_id, one resume covers all three proposal types | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_single_consolidated_gate -x` | ❌ Wave 0 |
| CUR-03 | empty gate_queue → completes without pausing | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_empty_queue_no_pause -x` | ❌ Wave 0 |
| CUR-04 | inspect reports `awaiting_review` + gate_queue; never resumes | unit | `.venv/bin/pytest tests/llm/test_curation_run.py::test_inspect_pending_review -x` | ❌ Wave 0 (extend existing `test_inspect_no_rerun`) |
| CUR-04 | events emitted for each step + gate review (spec §6.6) | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_curation_events_emitted -x` | ❌ Wave 0 |
| CUR-05 | no real step emits "placeholder"; deferred-only nodes gone | unit | `.venv/bin/pytest tests/llm/test_curation_run.py::test_steps_return_concrete_findings -x` | ✅ exists (test_curation_run.py:188) |
| CUR-05 | `_get_workflow_steps` curation-cycle lambdas removed; no placeholder reachable from CLI/MCP | contract | `.venv/bin/pytest tests/contract/test_curation_run_cli_mcp.py::test_no_placeholder_curation_path -x` | ❌ Wave 0 |
| CUR-05 | unreviewed canonical write guard: assert no write outside the post-gate nodes | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_no_unreviewed_writes -x` | ❌ Wave 0 |
| API-04 | migrated skills carry no `WebSearch`/`WebFetch`/`Write` in `allowed-tools` | static/lint | `.venv/bin/pytest tests/contract/test_skill_migration.py -x` (or a grep-based guard) | ❌ Wave 0 |
| CUR-03 | cross-process resume (separate checkpointer open) | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_cross_process_resume -x` | ❌ Wave 0 (mirror research_run.py:270 test) |
| API parity | `curation.review` / `card.evaluate` registered with cli_name+mcp_tool_name; MCP auto-discovered | contract | `.venv/bin/pytest tests/contract/test_curation_run_cli_mcp.py::test_registered -x` | ✅ extend (test_curation_run_cli_mcp.py:46) |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/llm/test_curation_run.py tests/llm/test_curation_promote.py -x -q`
- **Per wave merge:** `.venv/bin/pytest tests/llm/ tests/contract/ -q`
- **Phase gate:** `.venv/bin/pytest tests/ -q` green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/llm/test_curation_promote.py` — covers CUR-02 (card.evaluate gate, retry/escalate, governance clamp). Mirror `tests/llm/test_research_score.py`.
- [ ] Connection-typing gate tests (in `test_curation_promote.py` or a sibling) — covers D-05.
- [ ] Extend `tests/llm/test_curation_run.py` with the reviewed-write + interrupt/resume + consolidated-gate + no-unreviewed-write tests (mirror `tests/llm/test_research_run.py`).
- [ ] Extend `tests/contract/test_curation_run_cli_mcp.py` with `curation.review` + `card.evaluate` registration + the no-placeholder guard.
- [ ] `tests/contract/test_skill_migration.py` (or grep guard) — assert the three migrated skills carry no forbidden tools (API-04).
- [ ] Reusable mock seam: extend `tests/llm/conftest.py` with a `PromotionDecision`-shaped `ConfigurableStructuredMock` and a connection-type mock.
- Framework install: none needed — pytest already present.

## Security Domain

> `security_enforcement` is not set in `.planning/config.json` → treated as enabled. Included.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local-first CLI/MCP; no auth surface (v0.4 out-of-scope per REQUIREMENTS) |
| V3 Session Management | no | No sessions; `thread_id`/`run_id` is a workflow handle, not a session |
| V4 Access Control | no | Single-user local workspace |
| V5 Input Validation | yes | Pydantic `extra="forbid"` on every I/O model; `run_id` kebab-case `field_validator` (`_validate_run_id`, curation_run.py:53-66) prevents path traversal into the checkpoint DB path. New `CurationReviewInput`/`CardEvaluateInput` MUST keep `extra="forbid"` + reuse `_validate_run_id` |
| V6 Cryptography | no | No crypto in scope |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `run_id`/`gate_id` into `.construct/workflow/*.sqlite` | Tampering | `KEBAB_CASE_PATTERN` validator on all run-id inputs (already enforced; reuse for new inputs) [VERIFIED: curation_run.py:53-66] |
| Prompt injection from card content escalating a promotion/connection write | Elevation of Privilege | Structured output (`with_structured_output`) + the human approval gate: an injected card can only *propose*; no write without explicit human approve (CUR-03). Mirror research_score.py:202-213 boundary comment |
| Provider exception text leaking secrets into logs/results | Information Disclosure | Reuse `_safe_scoring_cause` / `_sanitize_error` sanitization (research_score.py:384-389, curation_run.py:222-231) — never echo raw provider text |
| `print()` corrupting MCP JSON-RPC stdout | Tampering (transport) | `logging` only in nodes (Pitfall 6) [VERIFIED: documented curation_run.py:26] |
| Unreviewed/double write on rerun or crash-resume | Tampering | Skip-if-exists writes + post-gate-only writes + paused-state resume guard (Patterns 3 + 5); anti-unreviewed-write test (CUR-05) |

## Sources

### Primary (HIGH confidence)
- `src/construct/llm/research_run.py` — interrupt/resume/review/inspect + SqliteSaver pattern (full read) [VERIFIED: codebase]
- `src/construct/llm/research_score.py` — L3 gate, fan-out, retry, outage discrimination (full read) [VERIFIED: codebase]
- `src/construct/llm/curation_run.py` — Phase 11 durable graph, `_deferred_step` skip-nodes 451-460 (full read) [VERIFIED: codebase]
- `src/construct/capabilities/catalog.py` — registration + shims (lines 295-315, 380-454, 540-668, 725-741) [VERIFIED: codebase]
- `src/construct/cli.py` — workflow command wiring 200-266 [VERIFIED: codebase]
- `src/construct/services/knowledge.py` — `add_connection` (372), `edit_card` (241), `archive_card` (314) [VERIFIED: codebase]
- `src/construct/schemas/card.py:35-39` — `Lifecycle` enum (`seed`/`growing`/`mature`/`archived`) [VERIFIED: codebase]
- `src/construct/schemas/workspace.py:29-54` — `ConnectionType` enum + `ConnectionRecord.type` required [VERIFIED: codebase]
- `src/construct/pipelines/bridge_detect.py` — candidate shape (233-282) + summary (489-520) [VERIFIED: codebase]
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §4.3 (119-134), §5.3 (192-201), §6.4 (286-295), §6.6 (314-326) [CITED: in-repo spec]
- `tests/llm/test_curation_run.py`, `tests/llm/test_research_run.py`, `tests/llm/conftest.py`, `tests/contract/test_curation_run_cli_mcp.py` — test harness + mock seams [VERIFIED: codebase]
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-{research-cycle,curation-cycle,card-evaluate}/SKILL.md` — migration source of truth [VERIFIED: codebase]
- `langgraph` 1.2.4, `langgraph-checkpoint-sqlite` 3.1.0 [VERIFIED: importlib.metadata]

### Secondary (MEDIUM confidence)
- None — all claims verified against the live codebase or in-repo spec.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; versions verified via importlib; patterns shipped + test-covered.
- Architecture: HIGH — directly mirrors two shipped modules; topology already compiled in curation_run.py.
- Pitfalls: HIGH — derived from documented `# Pitfall`/`# WR`/`# T` comments and verified enum/schema facts.
- Open questions: 3 genuine planning decisions (workflow CLI fate, gate ids/config, escalate semantics) — flagged in Assumptions Log, not blockers.

**Research date:** 2026-06-30
**Valid until:** 2026-07-30 (stable — in-repo verification target; only invalidated by changes to research_run/research_score/curation_run or the spec)
