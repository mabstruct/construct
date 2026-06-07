# CONSTRUCT v0.1 Pitfalls and Failure Modes

**Domain:** Local-first agentic knowledge system  
**Researched:** 2026-04-22  
**Overall confidence:** HIGH for architecture-fit risks, MEDIUM for ecosystem mitigation details

This file focuses on the failure modes most likely to force a rewrite, silently corrupt knowledge, or make v0.1 feel unreliable/expensive. The roadmap should treat these as design constraints, not cleanup work.

## Most Important Roadmap Implication

CONSTRUCT should not treat `cards/`, `db/`, `views/`, `inbox/`, and in-memory agent state as peers. **Markdown/YAML source-of-truth must win every time, and every other layer must be explicitly derived, replayable, or disposable.** Most v0.1 failures come from violating that rule.

---

## Critical Pitfalls

### 1. Split-brain storage: more than one effective source of truth

**What goes wrong:** The app slowly treats `db/`, `views/`, in-memory graph state, or UI-local edits as authoritative alongside markdown cards/config. Users then see contradictions between CLI, UI, and rebuild results.

**Why this is a v0.1 risk:** CONSTRUCT intentionally has four storage categories plus chat/UI/agent surfaces. That is powerful, but it makes accidental authority leaks very likely.

**Warning signs:**
- `construct rebuild` changes visible behavior without any card edits
- UI shows data that cannot be traced back to files in `cards/`, configs, or refs
- bug fixes require “refreshing the DB” or “restarting the UI” to become true
- code starts reading raw `views/` or SQLite data as business truth

**Prevention strategy:**
- In Phase 1, define and test a strict storage contract: **only markdown/config/refs/log are canonical**
- Make every write path go through one storage API; ban direct writes from UI to cards/db/views
- Add rebuild parity tests: SOT → rebuild db/views/graph → outputs must match expected fixtures
- Document, per directory, whether it is canonical, durable workspace, rebuildable, or disposable

**Which phase should address it:**
- **Phase 1 — Data Foundation:** canonical storage API + invariants
- **Phase 4 — Views Heartbeat:** derived/disposable enforcement
- **Phase 6 — Integration & Polish:** end-to-end rebuild parity tests

---

### 2. Transient inbox loses user intent or agent work-in-progress

**What goes wrong:** UI actions enter `inbox/`, but crashes, restarts, or partial processing lose requests, duplicate them, or leave them in an ambiguous state.

**Why this is a v0.1 risk:** The PRD currently frames `inbox/` as transient and gitignored while also making it the write-back contract for important user actions. That is a durability gap.

**Warning signs:**
- users repeat an action because they cannot tell whether it was accepted
- same inbox action is applied twice after restart
- pending actions disappear after crash/shutdown
- agent logs show work completed but no durable record of the triggering request

**Prevention strategy:**
- Treat inbox items as durable until acknowledged, even if still gitignored
- Give every action a stable ID, status (`queued|running|succeeded|failed|needs_input`), timestamps, and correlation ID in `events.jsonl`
- Make handlers idempotent: reprocessing the same action must be safe
- On startup, reconcile inbox state from disk + event log before accepting new work
- Surface explicit pending/failed states in UI instead of “fire and forget”

**Which phase should address it:**
- **Phase 2 — Agent Runtime:** durable task state + idempotency rules
- **Phase 4 — Views Heartbeat:** pending/failed action views
- **Phase 6 — Integration & Polish:** real inbox governance flow

---

### 3. Graph model mismatch: `DiGraph` collapses meaning you may need to preserve

**What goes wrong:** Multiple typed relationships between the same two cards cannot coexist cleanly, so one edge silently overwrites or compresses another. Example: the same pair may both `extends` and `contradicts` across contexts, but `DiGraph` only keeps one edge per direction.

**Why this is a v0.1 risk:** CONSTRUCT explicitly values typed connections and epistemic nuance. NetworkX `DiGraph` supports directed edges but not parallel edges.

**Warning signs:**
- edge typing logic starts inventing “combined” relation types
- connection history disappears after edits
- graph serialization cannot explain why one relation won over another
- developers debate “one relation per pair” late in implementation

**Prevention strategy:**
- Make an explicit v0.1 decision in Phase 1/3: either
  - enforce **one canonical typed edge per ordered card pair**, or
  - switch early to a structure that preserves multiple relations
- Store relationship records canonically in files/schema first; derive NetworkX representation second
- Add validation that duplicate pair/type collisions are caught, not silently merged

**Which phase should address it:**
- **Phase 1 — Data Foundation:** schema decision
- **Phase 3 — Graph Engine:** graph representation + serialization tests

---

### 4. Incremental index cleverness creates SQLite/FTS drift

**What goes wrong:** Incremental writes to SQLite FTS become inconsistent with cards/refs, so search results differ from non-FTS reads or only recover after a rebuild.

**Why this is a v0.1 risk:** SQLite FTS5 is strong, but external-content/content synchronization has documented pitfalls. Early local-first systems often over-optimize incremental indexing before the invariants are proven.

**Warning signs:**
- search returns stale or missing cards after edits
- normal metadata queries and MATCH queries disagree
- delete/update behavior is brittle
- developers need ad hoc “reindex this one thing” fixes

**Prevention strategy:**
- Prefer simple, explicit indexing over clever trigger/external-content setups in v0.1
- Keep `construct rebuild` as a first-class, heavily tested recovery path
- Add parity tests: file corpus → rebuild DB → known FTS queries
- If incremental updates are added, treat rebuild as the correctness oracle

**Which phase should address it:**
- **Phase 1 — Data Foundation:** initial DB design + rebuild parity tests
- **Phase 6 — Integration & Polish:** real-world edit/delete regression tests

---

### 5. `views/` contract leaks or becomes unstable

**What goes wrong:** React starts depending on raw workspace layout, markdown parsing quirks, or unstable JSON shapes. Then any backend refactor breaks the UI, or the UI reads half-written files and shows nonsense.

**Why this is a v0.1 risk:** The views contract is one of CONSTRUCT's smartest architectural choices, but only if it stays strict.

**Warning signs:**
- UI code asks for direct file access to `cards/` or `db/`
- views schemas change casually without contract tests
- UI bugs appear during rebuild windows or heartbeat updates
- the same concept is encoded differently across multiple `views/*.json` files

**Prevention strategy:**
- Version and schema-test every `views/` artifact before the React app depends on it
- Write views atomically: build to temp files/snapshot dir, then swap into place
- Keep React read-only against `views/`; all mutations go through inbox/chat/programmatic APIs
- Establish one owner for denormalized shapes so UI-specific fields do not bleed back into domain models

**Which phase should address it:**
- **Phase 4 — Views Heartbeat:** schema/version/atomic snapshot design
- **Phase 5 — React UI:** consume contract only, no backdoor reads

---

### 6. Heartbeat and long-running workflows are not durable or idempotent

**What goes wrong:** Research/curation loops overlap, misfire, restart twice, or lose progress when the process stops. The system feels haunted: duplicate cards, duplicate events, repeated LLM calls, or “stuck” sessions.

**Why this is a v0.1 risk:** Long-running agent systems fail less from model quality than from weak execution semantics. APScheduler itself warns about persistent job stores, duplicate jobs on restart, missed executions, coalescing, and concurrent instances.

**Warning signs:**
- two heartbeat cycles run concurrently
- restart causes repeated tasks or backlogged executions
- jobs cannot resume from a known checkpoint
- logs show repeated external fetches/LLM calls for the same unit of work

**Prevention strategy:**
- Define every recurring task with explicit identity, max concurrency, misfire policy, and restart behavior
- Make research/curation steps checkpointed and resumable at artifact boundaries
- Use correlation IDs and idempotency keys for every LLM/research task
- Separate scheduler state from task state; scheduler decides *when*, durable task records decide *what is done*
- Add crash/restart integration tests before calling workflows “continuous”

**Which phase should address it:**
- **Phase 2 — Agent Runtime:** session/task state machine
- **Phase 4 — Views Heartbeat:** heartbeat concurrency + restart semantics
- **Phase 6 — Integration & Polish:** crash/restart/resume tests

---

### 7. LLM cost blowout from open-ended loops and weak routing discipline

**What goes wrong:** Costs stay invisible until a research cycle, chat loop, or repeated retry pattern consumes far more than expected. Local-first becomes “local data, cloud bill.”

**Why this is a v0.1 risk:** CONSTRUCT depends on tiered routing, retries, chat, research loops, and optional frontier escalation. That combination is exactly where hidden spend creeps in.

**Warning signs:**
- no per-task cost estimate before execution
- retries and fallbacks happen without budget checks
- frontier models are used for routine classification or formatting
- users cannot answer “what did this session cost?”

**Prevention strategy:**
- Add per-call cost logging from day one, even if approximate for local models and exact for API models
- Enforce per-session and per-workflow budgets/caps, not just provider config
- Make local/workhorse the default; require explicit escalation to frontier for high-cognitive tasks
- Track spend by task/action ID so costly prompts are attributable and tunable
- Add UI/CLI visibility for estimated vs actual spend

**Which phase should address it:**
- **Phase 2 — Agent Runtime:** routing, tagging, cost ledger
- **Phase 5 — React UI:** spend/status visibility
- **Phase 6 — Integration & Polish:** budget guardrails in real workflows

---

### 8. Letting LLMs make epistemic/governance decisions that should be deterministic or human-reviewed

**What goes wrong:** The graph fills with plausible-but-wrong cards, overconfident tags, bad promotions, or unjustified connections because the system asks models to decide truthiness instead of assisting bounded workflows.

**Why this is a v0.1 risk:** CONSTRUCT's value is governed knowledge, not raw generation volume. If governance quality slips early, trust in the whole product collapses.

**Warning signs:**
- promotion/confidence/source-tier logic lives mainly in prompts
- same input produces materially different governance outcomes across runs
- users start distrusting mature cards or graph health stats
- “fixes” require hand-editing many cards after automated curation passes

**Prevention strategy:**
- Reserve deterministic rules for validation, lifecycle thresholds, integrity checks, stale/orphan detection
- Use LLMs for proposals, summarization, and ambiguity resolution only
- Require HITL review for contradictions, confidence jumps, destructive actions, and cross-domain claims
- Log rationale fields for every governance-changing action

**Which phase should address it:**
- **Phase 2 — Agent Runtime:** action/result schemas
- **Phase 3 — Graph Engine:** deterministic health checks
- **Phase 6 — Integration & Polish:** HITL review loops

---

## Moderate Pitfalls

### 9. Schema drift between Pydantic, JSON Schema, TypeScript, and markdown fixtures

**What goes wrong:** Backend, views, tests, and UI all accept slightly different shapes; bugs become “works in backend, fails in UI.”

**Warning signs:**
- hand-maintained TS types drift from generated schema
- fixture cards stop representing real production shapes
- contract tests only validate happy paths

**Prevention strategy:**
- Generate schemas and TS types from one source
- Fail CI on stale generated types
- keep malformed-fixture tests for cards, events, inbox items, and views

**Which phase should address it:**
- **Phase 1 — Data Foundation**
- **Phase 4 — Views Heartbeat**
- **Phase 5 — React UI**

### 10. Interactive graph ambitions outrun D3 and v0.1 performance budgets

**What goes wrong:** The product promises “knowledge graph” but the first real dataset makes the graph unreadable or sluggish.

**Warning signs:**
- trying to render the whole graph by default
- graph page is treated as primary navigation instead of one lens
- performance tuning starts before clustering/filtering UX exists

**Prevention strategy:**
- Treat graph as a filtered exploratory view, not the universal UI
- enforce node-count caps and domain/subgraph filters
- make cards/search/dashboard equally first-class

**Which phase should address it:**
- **Phase 3 — Graph Engine**
- **Phase 5 — React UI**

---

## Phase-Specific Roadmap Warnings

| Phase | Roadmap warning | Why it matters |
|------|------------------|----------------|
| Phase 1 — Data Foundation | Lock source-of-truth and schema rules before any UI or agent convenience shortcuts | Almost every expensive rewrite starts here |
| Phase 2 — Agent Runtime | Build durable task identity, cost logging, and idempotency before “continuous agents” | Otherwise crashes, duplicates, and spend blowouts become baked in |
| Phase 3 — Graph Engine | Decide whether one edge per ordered pair is a feature or a bug | NetworkX `DiGraph` forces the choice |
| Phase 4 — Views Heartbeat | Treat `views/` as a versioned contract with atomic rebuilds | This is the API boundary for the future product |
| Phase 5 — React UI | Refuse direct workspace reads/writes | UI shortcuts will permanently weaken architecture |
| Phase 6 — Integration & Polish | Add restart/rebuild/budget/HITL journey tests, not just happy-path demos | v0.1 succeeds or fails on reliability, not feature count |

---

## Recommended Roadmap Additions

These should be explicit deliverables, not implied quality work:

1. **Storage invariants + rebuild parity suite** (Phase 1)
2. **Durable inbox/task model with status lifecycle** (Phase 2)
3. **Graph edge semantics decision record** (Phase 1 or 3)
4. **Views schema/version/atomic snapshot contract tests** (Phase 4)
5. **Per-task cost ledger and budget guardrails** (Phase 2)
6. **Crash/restart/resume integration tests** (Phase 6)
7. **HITL gates for high-impact epistemic actions** (Phase 6)

---

## Sources

### Primary project sources
- `/Users/mab/dev/mabstruct/construct/.planning/PROJECT.md`
- `/Users/mab/dev/mabstruct/construct/CONSTRUCT-spec/construct-prd.md`
- `/Users/mab/dev/mabstruct/construct/CONSTRUCT-spec/construct-nfrs.md`
- `/Users/mab/dev/mabstruct/construct/CONSTRUCT-spec/construct-development-strategy.md`
- `/Users/mab/dev/mabstruct/construct/CONSTRUCT-spec/construct-test-strategy.md`

### External verification
- SQLite FTS5 docs — external content table pitfalls and rebuild behavior: https://www.sqlite.org/fts5.html
- APScheduler user guide — persistence, duplicate job IDs on restart, max instances, misfires, coalescing: https://apscheduler.readthedocs.io/en/3.x/userguide.html
- NetworkX `DiGraph` docs — directed edges allowed, parallel edges not allowed: https://networkx.org/documentation/stable/reference/classes/digraph.html
- LiteLLM routing/load balancing docs: https://docs.litellm.ai/docs/routing-load-balancing
- LiteLLM spend tracking docs: https://docs.litellm.ai/docs/proxy/cost_tracking
