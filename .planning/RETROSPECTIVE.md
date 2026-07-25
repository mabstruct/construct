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

## Milestone: v0.4.1 — Surface Integration & Documentation Truth

**Shipped:** 2026-07-25
**Phases:** 4 (14–17) | **Plans:** 20 | **Tests:** 515 passing / 1 skipped (Phase 16 checkpoint)

### What Was Built
- Durable-state & config truth — `adr-0004` records `.construct/workflow/*.sqlite` as sanctioned durable state; `nfrs.md`/`architecture-overview.md`/`workspace-contract.md` scoped to match; `resolve_llm_config_path()` shares one resolution path; `model-routing.yaml` deprecated-but-scaffolded (Phase 14; DOC-03, FIX-02).
- `views.generate_data` resolution — real MCP handler behind an `install_root` contract, the 15-module views library vendored into `src/construct/views/`, models reconciled to parser output, and post-run views refresh owned by the Python workflow layer as a status-neutral side effect (Phase 15; FIX-01, adr-0005).
- Invocation & user-doc truth — `_KNOWN_BROKEN` emptied over a *widened* guard (`_DOC_GLOBS` 3→5), `knowledge card list` implemented with CLI/MCP parity, `construct-synthesis` web grants removed (`spec-v04:436` closed), executable user docs, and a superseded offline-runnable playbook, human-verified on a fresh workspace (Phase 16; FIX-03, DEC-01, DOC-04).
- Architecture doc set & discoverability — `architecture-overview.md` on ADR-0003's L0–L4 model, `artifact-catalog.md` staleness-proofed by a `test_artifact_catalog.py` introspection guard, `config-topology.md` deleted, and a thin `construct-daily-cycle` chat entry point for `daily.run` (Phase 17; DOC-01, DOC-02, UX-01).

### What Worked
- **Guard-first, allowlist-that-can-only-shrink.** FIX-04 landed *before* the milestone and *defined* the remaining work — FIX-01 and FIX-03 were complete precisely when `_KNOWN_BROKEN` was empty. Mechanical completion criteria replaced prose judgement about whether a doc-truth requirement was "done."
- **Widen the scan to prove the empty allowlist is real.** 16-07 grew `_DOC_GLOBS` from 3 to 5 (adding `USER_GUIDE.md`, `commands.md`) with the allowlist held empty — an empty allowlist that survives *widening* cannot be a narrowed-scan artefact. Strongest form of the criterion.
- **Mechanical introspection guards pin docs to live code.** `test_artifact_catalog.py` asserts every live capability/MCP tool/Typer leaf/skill dir has a catalog row and cannot pass vacuously — the inventory physically cannot silently rot.
- **A retrospective milestone audit was the load-bearing basis.** `v0.4-MILESTONE-AUDIT.md` (2026-07-19, file:line evidence for every defect) scoped the whole milestone — the audit v0.4 *didn't* run at close became the entry point for v0.4.1, validating v0.3's "milestone audit catches integration rot" lesson after the fact.

### What Was Inefficient
- **Doc-truth work is prose-heavy and hand-verified.** Several requirements (DOC-01/04, the playbook run) needed careful human reading and a fresh-workspace offline execution rather than a test — the mechanical guards cover *resolution*, not whether the prose describes reality.
- **Contract forks were escalated, not resolved, and became handoff debt.** `views validate` still rejects 3 of 8 files `views generate` writes (validates a projection, writes the raw dict); per-card edits lost their refresh path with the debounce-hook removal; the `card list` MCP boundary skips `OperationError` serialization. Each was deliberately deferred with a pinning test/log rather than fixed in a patch milestone — correct, but it means v0.5 inherits a known list.
- **The auto-generated MILESTONES/accomplishments were noisy.** `milestone.complete`'s `summary-extract` pulled `Task 1 —` fragments as one-liners; the entry was rewritten by hand — same `gsd-sdk` extraction weakness noted in v0.3/v0.4.

### Patterns Established
- **Allowlist-that-can-only-shrink + widen-to-prove** — a paired "still-broken" assertion forces deletion on a landed fix and blocks quiet widening; then *growing* the scanned surface while the allowlist stays empty proves the criterion isn't a scoping artefact.
- **Introspection guard as anti-staleness for inventory docs** — assert doc rows against live registry/Typer/MCP/glob enumeration with a non-vacuity check, so a catalog cannot drift from the code it describes.
- **Escalate-don't-absorb for out-of-scope contract forks** — when a fix surfaces a deeper contract question beyond the phase's scope, pin it with a test and log it as a named handoff item rather than silently deciding it.
- **Deprecate-but-scaffold for load-bearing-but-wrong config** — `model-routing.yaml` kept as a `REQUIRED_PATHS` scaffold entry (workspace-contract stability) while marked deprecated/inert everywhere it was called authoritative, instead of deleting it and churning the workspace format.

### Key Lessons
1. Mechanical completion criteria (an empty allowlist, a passing introspection guard) beat prose "is it done?" for documentation-truth work — but only cover what they mechanically check; prose accuracy still needs a human read.
2. Prove a negative result (empty allowlist) is real by *widening* its scope, not by trusting it under a fixed scan — a green result under a narrow scan is the failure mode.
3. A retrospective milestone audit with file:line evidence can scope an entire remediation milestone — run the audit v0.4 skipped, and its findings become the next milestone's requirements.
4. In a patch milestone, escalate deeper contract forks with a pinning test rather than fixing them — but track them explicitly, because they become the next milestone's inherited debt.

### Cost Observations
- Model mix: executors Opus per config (`model_profile: quality`); verifier/checker Sonnet. Mostly documentation and small code changes (one real feature: `knowledge card list`; one handler wire-up: `views.generate_data`).
- Sessions: milestone spanned 2026-07-19 → 2026-07-25 (7 days), 145 commits, 243 files (+21,796 / −1,905 — inflated by the vendored 15-module views library).
- Notable: a doc-heavy patch milestone, but the highest-leverage work was the *guards* (FIX-04, `test_artifact_catalog.py`) that make the fixes durable rather than one-time corrections.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v0.3 | 7 | First milestone-level audit + integration check; retrofitted verification; contract-test regression gate established |
| v0.4 | 6 | Per-phase verification became continuous (every phase has a passing VERIFICATION.md); worktree isolation made viable via manifest-scoped cleanup; verifier runs live CLI proof; no milestone-level audit run |
| v0.4.1 | 4 | Retrospective milestone audit (v0.4's skipped one) scoped the whole milestone; mechanical completion criteria (empty allowlist, introspection guard) replaced prose "done?" judgement; widen-to-prove and escalate-don't-absorb established |

### Cumulative Quality

| Milestone | Tests | Unsatisfied Reqs at Close | Notes |
|-----------|-------|---------------------------|-------|
| v0.3 | 224 | 0 (2 partial deferred to v0.4) | Verification/Nyquist/security coverage incomplete; carried as debt |
| v0.4 | 404 | 0 | 22/22 requirements delivered; per-phase verifications all passed; 3 advisory (non-blocking) Phase-13 robustness findings carried forward |
| v0.4.1 | 515 | 0 | 9/9 requirements delivered; artifact-open audit clear at close; 4 non-blocking contract/MCP-boundary items escalated as v0.5 handoff debt |

### Top Lessons (Verified Across Milestones)

1. (v0.3, v0.4, v0.4.1) Integration/E2E verification must be explicit — unit-green ≠ wired. v0.4 improved this with continuous per-phase verification + live-CLI verifier proof; v0.4.1 turned "wired" into a mechanical guard (documented invocations must resolve against the live Typer app).
2. (v0.3, v0.4, v0.4.1) `gsd-sdk` tracking verbs silently mis-scope (phase counts, stale status cells, orphan dirs, noisy auto-extracted accomplishments) — verify git/ROADMAP/STATE state after every CLI write; do not trust the success JSON.
3. (v0.3, v0.4.1) A milestone audit with file:line evidence catches integration rot a green suite hides — v0.3 caught it at close; v0.4 skipped it and v0.4.1 became the retrospective remediation. Run the audit before close, not after.
