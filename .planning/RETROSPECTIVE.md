# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v0.3 — Claude-Native Runtime & Workflow Hardening

**Shipped:** 2026-06-16
**Phases:** 7 (1–7) | **Plans:** 25 | **Tests:** 224 passing

### What Was Built
- Canonical Claude-native workspace contract with pre-write validation gates, proven against `test-ws/` fixtures (Phase 1).
- Reliable governed knowledge operations — card/ref/connection/storage CRUD with non-blocking event logging (Phase 2).
- A capability registry + Click CLI + stdio MCP server as one shared runtime contract, with skills as thin wrappers (Phases 3–4).
- Grounded Q&A, synthesis, and bridge detection over the graph (Phase 5); view data contracts + Streamlit ops UI + governed spikes (Phase 6).
- Closure of the three v0.3 audit blockers — RT-03 MCP schema parity, ING-02 ingest cluster validation, ING-05 graph.status wiring (Phase 7).

### What Worked
- **Milestone audit caught real integration rot the green test suite hid.** 209 unit tests passed while 3 advertised E2E flows were broken — the audit + a handler-invocation contract test exposed and then gated the gap.
- **Fixing data to conform to the gate, not weakening the gate** (ING-02) kept canonical truth trustworthy.
- **Adversarial code review during execution** found a phase-caused BLOCKER (CR-01: ING-02 seeding broke help.py stale scoring) before it shipped.

### What Was Inefficient
- **Worktree isolation was unusable** in this harness — parallel executors spawned from inconsistent/stale bases (one at HEAD, two at the merge-base). Had to abort and re-run all 3 plans sequentially on the main tree. Lost a parallel-execution attempt.
- **`gsd-sdk` v1.42.3 bugs caused repeated manual fallback** — mutation verbs drop positional args; `summary-extract` mis-parses inline-list frontmatter; `phase.complete`/`milestone.complete` left stale ROADMAP cells and undercounted the milestone scope (1 phase vs 7). Most tracking edits were done by hand.
- **Verification was retrofitted, not continuous** — phases 1–6 shipped with no per-phase VERIFICATION.md; the milestone audit became the first real verification and is the verification-of-record.

### Patterns Established
- **Contract test that invokes every handler** (not just shape) as a regression gate against signature drift (`test_mcp_contracts.py`).
- **Dual-mode capability shims** — positional CLI pass-through vs keyword MCP marshalling behind one registry handler, so CLI and MCP share a surface without touching the service layer.
- **Milestone re-audit as the green-close gate** — supersede the prior audit in place; require 0 unsatisfied requirements before completing.

### Key Lessons
1. A green unit suite is not integration coverage — assert the actual cross-surface invocation (MCP/UI handler path), or blockers hide until milestone audit.
2. When a data-seeding change reorders shared structures, audit every consumer that indexes into them (CR-01 was caused by `clusters[0]` after reordering).
3. Tooling that silently mis-scopes or drops args (gsd-sdk here) needs a verify-after-write habit — check git/ROADMAP/STATE state rather than trusting the CLI's success JSON.

### Cost Observations
- Model mix: execution/verification predominantly Opus (executors, integration check, code review); Sonnet for verifier/integration-checker per config.
- Notable: sequential-on-main execution cost wall-clock vs the intended parallel worktrees, but produced clean linear history and avoided the worktree-base corruption.

---

## Milestone: v0.4 — Agent Workflows (LangGraph / LangChain)

**Shipped:** 2026-07-07
**Phases:** 6 (8–13) | **Plans:** 24 | **Tests:** 404 passing

### What Was Built
- Provider-agnostic search spine — `research.search` with Tavily + fixture-driven mock providers, config-driven caps, and structured degraded errors, zero SOT writes (Phase 8).
- Model-agnostic LLM provider factory and three L3 gates — `research.score`, `card.evaluate`, connection-typing — with governance clamping, bounded fan-out, retry-then-skip, and total-outage discrimination (Phases 9, 12).
- Durable checkpointed LangGraph workflows for `research.run` and `curation.run` with a real `interrupt()` human-review gate that writes nothing before approval and resumes across process restarts (Phases 10–12).
- Thin `daily.run` composition folding `research.run → curation.run → graph.status` into one non-blocking cycle — isolate-and-degrade, escalate excluded, no false `completed` (Phase 13).
- Full CLI/MCP parity for every new capability via the shared registry, with MCP tools auto-discovered (`mcp/server.py` never hand-edited); research/curation skills migrated to thin CLI/MCP delegators (API-04).

### What Worked
- **Worktree isolation worked cleanly this milestone** (it was unusable in v0.3). The manifest-scoped `worktree.cleanup-wave` helper merged each single-plan wave back with correct base pinning and no base-corruption — each wave forked from the prior wave's merged HEAD, preserving the strict dependency chain.
- **Post-merge full-suite gate in the main checkout** correctly distinguished a worktree-only environmental failure (empty untracked fixture dirs git can't store) from a real regression — the executor flagged it, the main-checkout gate confirmed it was benign.
- **The verifier ran live, unscripted CLI invocations** (real isolate-and-degrade, receipt round-trip, missing-run handling) instead of trusting SUMMARYs — goal-backward proof that caught nothing wrong because the work was sound, but would have caught a fabricated claim.
- **Mechanical clone of a proven quartet** — Phase 13 registered `daily.*` by cloning the curation registration/CLI/contract-test pattern symbol-for-symbol, making a new capability fast and low-risk, with MCP parity free.

### What Was Inefficient
- **Stale tracking artifacts recurred and needed hand-correction** — REQUIREMENTS.md left SRCH-01..04 as "Pending" long after Phase 8 shipped; ROADMAP.md pinned Phase 12 at "3/6 In Progress" though it was complete; a stray `phase-008/` directory (early pre-rename Phase 8 planning) inflated `milestone.complete`'s phase count to 7. Same class of `gsd-sdk` mis-scoping seen in v0.3 — verify-after-write is still mandatory.
- **No milestone audit was run before close** — proceeded on the strength of per-phase verifications (all passed) + the full 404-test suite, but without a dedicated cross-phase E2E audit like v0.3 had.

### Patterns Established
- **Thin composition over frozen children** — compose stable capabilities by calling their public `run_*`/`review_*` entrypoints in a synchronous try/except (isolate-and-degrade), rather than building a parent LangGraph graph/checkpointer that duplicates child state.
- **Registry auto-discovery = free MCP parity** — new capabilities appear on the MCP surface via `list_mcp_tools()` with `mcp/server.py` untouched, guarded by a `test_mcp_no_hardcoded_*` invariant + a `git diff` check.
- **Propose-then-reviewed-apply HITL by construction** — no canonical-write node exists upstream of the human `interrupt()`; escalate items are surfaced as a pending count and never auto-written.

### Key Lessons
1. `gsd-sdk` tracking verbs still silently mis-scope (phase counts, stale status cells, orphan dirs) — the v0.3 "verify git/ROADMAP/STATE state, don't trust the CLI's success JSON" habit remains load-bearing.
2. Worktree isolation is viable when each wave pins an explicit base and cleanup is manifest-scoped — the failure mode in v0.3 was base inconsistency, not worktrees themselves.
3. When adding a capability symmetric to an existing one, cloning the proven quartet (module → registration → CLI sub-app → contract test) beats designing fresh — lower risk, and inventory tests localize the required edits.
4. Rename phase directories in place; a leftover pre-rename dir silently corrupts milestone counts.

### Cost Observations
- Model mix: executors Opus (per config `executor_model: opus`); verifier + inherited code-reviewer on Sonnet. Background async worktree agents ran cleanly.
- Notable: the strict linear dependency chain (one plan per wave) meant no intra-wave parallelism — worktree isolation bought clean history and orchestrator-owned tracking writes rather than wall-clock savings here.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v0.3 | 7 | First milestone-level audit + integration check; retrofitted verification; contract-test regression gate established |
| v0.4 | 6 | Per-phase verification became continuous (every phase has a passing VERIFICATION.md); worktree isolation made viable via manifest-scoped cleanup; verifier runs live CLI proof; no milestone-level audit run |

### Cumulative Quality

| Milestone | Tests | Unsatisfied Reqs at Close | Notes |
|-----------|-------|---------------------------|-------|
| v0.3 | 224 | 0 (2 partial deferred to v0.4) | Verification/Nyquist/security coverage incomplete; carried as debt |
| v0.4 | 404 | 0 | 22/22 requirements delivered; per-phase verifications all passed; 3 advisory (non-blocking) Phase-13 robustness findings carried forward |

### Top Lessons (Verified Across Milestones)

1. (v0.3, v0.4) Integration/E2E verification must be explicit — unit-green ≠ wired. v0.4 improved this with continuous per-phase verification + live-CLI verifier proof.
2. (v0.3, v0.4) `gsd-sdk` tracking verbs silently mis-scope (phase counts, stale status cells, orphan dirs) — verify git/ROADMAP/STATE state after every CLI write; do not trust the success JSON.
