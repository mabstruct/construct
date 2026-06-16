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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v0.3 | 7 | First milestone-level audit + integration check; retrofitted verification; contract-test regression gate established |

### Cumulative Quality

| Milestone | Tests | Unsatisfied Reqs at Close | Notes |
|-----------|-------|---------------------------|-------|
| v0.3 | 224 | 0 (2 partial deferred to v0.4) | Verification/Nyquist/security coverage incomplete; carried as debt |

### Top Lessons (Verified Across Milestones)

1. (v0.3) Integration/E2E verification must be explicit — unit-green ≠ wired.
