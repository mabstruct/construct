# Phase 12: Curation L3 Gates + Review Application - Context

**Gathered:** 2026-06-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Graft the **human-review + L3 judgment layer** onto Phase 11's already-durable
`curation.run` LangGraph graph. Specifically, deliver:

- A **`card.evaluate` L3 promotion gate** producing structured promote/hold/escalate
  `PromotionDecision`s with evidence (CUR-02).
- A **connection-typing L3 gate** that types untyped edges (within
  `connection_maintenance`).
- **Reviewed application of high-impact canonical writes** — lifecycle promotions,
  connection typings/writes, and decay auto-archives — gated behind a single human
  `interrupt()` so **no canonical write happens before approval** (CUR-03).
- **Inspect/status surfacing** of curation run status, degraded states, pending
  reviews, review outcomes, and emitted events for deterministic steps and the
  review gate (CUR-04).
- **Anti-placeholder tests** that fail if placeholder no-op handlers or unreviewed
  canonical writes remain — including removal of the legacy
  `workflow.run curation-cycle` placeholder lambdas flagged in Phase 11 D-11 (CUR-05).
- **Skill migration**: research + curation Claude-native skills become thin
  orchestrators that delegate to CLI/MCP capabilities with no direct `WebSearch`,
  `WebFetch`, or workspace writes (API-04).

**In scope:** `card.evaluate` (LLM promotion gate), connection-typing L3 gate,
single consolidated review interrupt at `process_inbox`, `curation.review` resume
capability + extended `curation.inspect`, reviewed lifecycle/connection/archive
writes, anti-placeholder + unreviewed-write tests, legacy placeholder removal, and
the research/curation/card-evaluate skill migrations.

**Out of scope (→ Phase 13):** daily-cycle composition (DAY-01) and the final
CLI/MCP/compatibility parity sweep (API-01/02/03/05) beyond what these capabilities
require. Full `views.generate_data` emission (ADV-03) stays a deferred track —
`views_refresh_hook` continues to report skipped.

</domain>

<decisions>
## Implementation Decisions

### Promotion gate method (`card.evaluate`)
- **D-01:** **LLM-always.** Every candidate card goes through the LLM gate and
  receives a real promote/hold/escalate judgment; `PromotionDecision.reasoning` is
  the evidence (CUR-02). Chosen over rule-first/escalation and rule-only — the user
  wants genuine judgment on every card, accepting per-run LLM cost.
- **D-02:** **Candidate set = all non-mature cards.** Deterministic pre-filter is
  simply `lifecycle != mature` (terminal state); every other card is judged each
  run. Maximum coverage, no cooldown bookkeeping. (Cost/batch-size grows with the
  graph — accepted.)
- **D-03:** **Per-item failure → retry-then-escalate.** On LLM timeout / invalid
  output / partial outage, retry the failing cards; any still-failing card is
  surfaced into the review queue as `decision="escalate"`. **Disambiguation via the
  existing `method` field:** failure-driven escalations carry
  `method="rule-based"` with the failure noted in `reasoning`; genuine borderline
  escalations carry `method="llm-judgment"`. The review UI/inspect can split on
  `method`. Mirrors Phase 9 D-04/D-08/D-09 (per-item retry+skip, total-outage
  discrimination).

### Reviewed-write scope
- **D-04:** **All three high-impact write types are applied this phase** (all were
  findings-only / deferred in Phase 11):
  1. **Promotion lifecycle writes** — apply approved `promote` decisions per
     `PromotionDecision.target_lifecycle` (e.g. seedling→growing→mature).
  2. **Connection typing + writes** — type untyped edges and write connections
     after approval (closes Phase 11's connection-typing deferral).
  3. **Decay auto-archive application** — apply archiving when
     `governance.yaml auto_archive_on_decay=true`, through the reviewed path
     (closes Phase 11 D-06's explicit "deferred to Phase 12 reviewed path").
- **D-05:** **Connection typing uses an LLM L3 gate per untyped edge** —
  `bridge.detect` surfaces candidate/untyped edges; an LLM assigns the connection
  type with reasoning. Consistent LLM-always posture with the promotion gate (chosen
  over rule-based or bridge-candidates-only typing). This is the **second L3 LLM
  gate** in the phase.

### Review gate composition
- **D-06:** **Single consolidated review gate.** The graph computes ALL proposals
  (promotions + connection types + decay archives) first, then pauses at **one**
  `interrupt()` (the `process_inbox` node) collecting them into **one review queue**
  with one `gate_id` and one resume. Mirrors `research.run` exactly (Phase 10 D-03).
  The upstream `promotion_review` and `connection_maintenance` nodes **produce
  proposals into the queue rather than each pausing.** This defines what
  `process_inbox` *is*: the consolidated HITL review queue.
- **D-07:** **Queue holds actionable + escalate items only.** Items that would cause
  a canonical write (`promote`, connection-write, archive) plus `escalate` items
  appear in the queue. Plain `hold` decisions are **events-only** (logged in the
  report/event log, never surfaced for review). **Default suggested decision per
  queue item = the gate's recommendation** (Phase 10 D-04 pattern); `escalate` items
  carry **no default write** (a human must explicitly act). Per-item approve/reject
  with approve-all/reject-all; **only approved items are written** (Phase 10 D-04).

### Skill migration (API-04)
- **D-08:** **Skills become orchestrator + scope-negotiation thin skills.** Each
  migrated skill: (a) negotiates scope up front (which domains/seeds, how many
  candidates), (b) invokes the Python CLI/MCP capability (`construct research run` /
  `construct curation run`), (c) drives the review loop conversationally — presents
  the pending gate queue, collects approve/reject, calls the review capability to
  resume — and (d) frames the digest/report narratively. **Zero direct `WebSearch`,
  `WebFetch`, or workspace writes** survive. All search/score/ingest/curation logic
  lives in Python (spec "hybrid path").
- **D-09:** **Migrate all three skills; fold `card-evaluate`.** Migrate
  `construct-research-cycle` and `construct-curation-cycle` to thin orchestrators.
  `construct-card-evaluate`'s judgment logic is **absorbed into the Python
  `card.evaluate` gate**; the skill becomes a thin wrapper over `construct card
  evaluate` (or is retired and invoked inline by the curation skill). One coherent
  delegation story; no duplicate LLM-judgment logic left in skill text.

### Derived cleanup (CUR-05)
- **D-10:** **Remove the legacy `workflow.run curation-cycle` placeholder lambdas**
  (`catalog.py` `_get_workflow_steps("curation-cycle")`, flagged in Phase 11 D-11 as
  the surviving fake-success path). Add an **anti-placeholder test** that fails if
  any placeholder no-op handler or unreviewed canonical write remains in the curation
  path (CUR-05).

### Claude's Discretion
- **Promotion gate batching/fan-out shape** — single batched call vs per-card
  bounded concurrency + per-item retry — follow the `research.score` fan-out
  precedent (Phase 9 D-04); D-03's per-item retry implies per-item granularity.
- **Connection-typing gate registration** — its own registered capability vs an
  inline L3 node inside `connection_maintenance`. No requirement names a separate
  `connection.evaluate`; follow the `card.evaluate` pattern. Discretion.
- **Consolidated queue item representation** — a tagged-union proposal envelope
  (`kind: promotion | connection | archive | escalate` + typed payload) following the
  Phase 10 D-04 per-item decision-state pattern; the `gate_queue` channel holds the
  heterogeneous items.
- **Review/inspect capability surface** — add `curation.review` (resume w/ decisions,
  mirror `research.review`) and **extend the existing `curation.inspect`** (Phase 11)
  to report pending-review state + outcomes. Follow the `research.review` /
  `research.inspect` registration + shim pattern for CLI/MCP parity.
- **Write idempotency / rerun safety** for the three new write types — follow Phase
  10's deterministic skip-if-exists + checkpoint-resume posture so a crash mid-apply
  or a rerun never double-writes or re-proposes an already-applied change.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/ROADMAP.md` — Phase 12 goal + 5 success criteria; `Depends on: Phase 11`;
  Phase 13 boundary (daily-cycle, what defers).
- `.planning/REQUIREMENTS.md` — **CUR-02, CUR-03, CUR-04, CUR-05, API-04** (this
  phase); the CLI/MCP/registry invocation contract; the SQLite carve-out row (Phase
  10 D-02).
- `.planning/PROJECT.md` — v0.4 milestone scope; product-continuity constraint (v0.3
  behavior must keep passing, API-05).

### Spec (authoritative design source)
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §4.3 — curation target graph
  topology (`promotion_review` L3, `connection_maintenance` PIPE + L3 per untyped
  edge, `process_inbox` HUMAN).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §6.4 — **`PromotionDecision`**
  schema (`card_id`, `decision: promote|hold|escalate`, `target_lifecycle`,
  `reasoning`, `method: rule-based|llm-judgment`) — the gate output contract; the
  `method` field carries D-03's failure/borderline disambiguation.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §5.3 — HITL gate protocol
  (approve/reject → events → SOT write allowed/blocked; `review_required: true`).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §6.6 — event types for the
  curation cycle + gate review.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §12 (W5) — deliverables
  (promotion + connection typing gates, `curation.run` graph, skill migration).
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — L1/L2/L3 gate tiers;
  registry/CLI/MCP 1:1 rule.

### Pattern references (mirror these)
- `src/construct/llm/research_run.py` — the `interrupt()` + `Command(resume=...)` +
  review/inspect + `SqliteSaver` pattern to mirror for the curation review gate.
- `src/construct/llm/research_score.py` — L3 LLM gate via `factory.build_chat_model`;
  bounded fan-out + per-item retry/skip + degraded-vs-total-outage (Phase 9 D-04/08/09).
- `src/construct/llm/curation_run.py` — Phase 11's durable curation graph. Graft
  `interrupt()`/proposals onto `promotion_review` & `connection_maintenance`; turn
  `process_inbox` into the consolidated review gate; **replace the `_deferred_step`
  skip-nodes** (lines ~451–460) with real bodies.

### Reusable capabilities & config (files to touch / reuse)
- `src/construct/capabilities/catalog.py` — register `card.evaluate` + `curation.review`;
  extend `curation.inspect` (id ~L444, shim ~L605); `_add_connection_shim` (~L259) and
  `add_connection` for connection writes; **remove the legacy
  `_get_workflow_steps("curation-cycle")` placeholder lambdas (D-10)**.
- `src/construct/pipelines/bridge_detect.py` — `bridge_detect()` feeds the
  connection-typing gate candidate edges.
- `src/construct/schemas/config.py` — `DecayConfig` / `QualityConfig` /
  `GovernanceConfig` thresholds (decay window, orphan tolerance, `auto_archive_on_decay`).
- `src/construct/services/event_log.py` — `append_event()` for gate/review/write events.
- `src/construct/cli.py` + `src/construct/mcp/server.py` — CLI command + MCP parity
  (auto-discovery from registry).
- `test-ws/my-construct/governance.yaml` — live thresholds (`auto_archive_on_decay`
  etc.) for offline tests.

### Skills to migrate (source of truth)
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md` — still does
  direct `WebSearch`/`WebFetch` (line ~54) — must be removed (D-08).
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md` — already
  mostly delegates; rewire to `construct curation run` + review loop.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md` — fold into
  the Python `card.evaluate` gate; thin-wrap or retire (D-09).

### Phase carry-forward context
- `.planning/phases/11-curation-pipe-steps/11-CONTEXT.md` — Phase 11 D-01..D-11 (graph
  topology, `CurationStepResult`, deferred skip-nodes, D-11 legacy-placeholder flag).
- `.planning/phases/10-durable-human-review-research-run/10-CONTEXT.md` — D-01..D-12
  (LangGraph interrupt/resume, per-finding review, idempotency, review/inspect surface).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`research_run.py` interrupt/review/inspect + checkpointer** — architectural
  template for the consolidated curation review gate (one `gate_id`, resume via
  `Command`, `SqliteSaver`).
- **`research_score.py` L3 gate + `factory.build_chat_model`** — template for both
  Phase 12 LLM gates (promotion + connection typing), incl. degraded/outage handling.
- **`curation_run.py` Phase 11 graph** — already durable and topology-complete; Phase
  12 swaps the three `_deferred_step` skip-nodes for real bodies (no graph
  restructuring needed — Phase 11 D-03 built it for exactly this).
- **`bridge_detect()`, `add_connection`, `GovernanceConfig/DecayConfig/QualityConfig`,
  `append_event()`** — feed the new gates and writes; no new config surface needed.
- **Existing `curation.inspect` (Phase 11)** — extend to report pending-review state +
  outcomes (CUR-04), rather than a new capability.

### Established Patterns
- Capabilities registered with `cli_name` + `mcp_tool_name` shims for CLI/MCP parity
  (RT-03 dual-mode shim).
- Handlers return `OperationResult(success, message, data)`; gate outputs ride in
  `data` (e.g. `CurationStepResult`, `PromotionDecision`).
- Per-item review decision-state persisted in the LangGraph checkpoint `gate_queue`
  channel; only-approved-writes invariant enforced behind the interrupt.

### Integration Points
- Two new L3 LLM gates wired into the existing curation graph nodes; connection writes
  via `add_connection`; lifecycle/archive writes via card schema + lifecycle updates.
- Events emitted per spec §6.6 (gate review approved/rejected, curation cycle
  complete, step events) via `append_event()`.
- Legacy `workflow.run curation-cycle` placeholder path removed (D-10) — `curation.run`
  is the sole canonical curation path.

</code_context>

<specifics>
## Specific Ideas

- The phase is deliberately the "writes turn on" phase: Phase 11 was findings-only by
  design; Phase 12 is where promotion lifecycle, connection, and archive writes
  actually land — but **only behind a single human approval gate**. The "no canonical
  write without a real judgment AND a human approval" invariant is the spine.
- Keep the consolidated gate ergonomically identical to `research.run`'s review so a
  user (and a future UI) learns one review model for both workflows.
- The `method` field on `PromotionDecision` is doing double duty (judgment provenance
  AND failure-vs-borderline disambiguation) — make sure inspect/report surfaces it so
  failure-escalations are visibly distinct from genuine borderline escalations.

</specifics>

<deferred>
## Deferred Ideas

- **Daily-cycle composition (DAY-01)** and the final **CLI/MCP/compatibility parity
  sweep (API-01/02/03/05)** — Phase 13.
- **Full `views.generate_data` emission (ADV-03)** — deferred track;
  `views_refresh_hook` continues to report skipped.
- **Last-evaluated cooldown / candidate-set narrowing** — explicitly rejected for now
  (D-02 sends all non-mature cards each run); revisit if per-run LLM cost becomes a
  problem.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-curation-l3-gates-review-application*
*Context gathered: 2026-06-30*
