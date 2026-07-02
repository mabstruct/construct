# Phase 12 — Plan Check (pre-execution, goal-backward)

**Checked:** 2026-07-01
**Phase goal:** Promotion and connection proposals use reusable human review before canonical writes, with migrated skills.
**Plans reviewed:** 12-01 … 12-06 (6 plans)
**Verdict:** READY-WITH-CONCERNS

---

## Verdict rationale

Every assigned requirement (CUR-02, CUR-03, CUR-04, CUR-05, API-04) has a concrete
delivering plan with real, named acceptance tests — not just a frontmatter tag. Every
locked decision (D-01…D-10) is operationalized by a specific task. The dependency graph
is linear, acyclic, and wave-consistent. The CUR-03 spine ("no canonical write without a
real judgment AND a human approval") is enforced *by construction*: Plan 03 installs an
interrupt-only `process_inbox` with no write nodes upstream, and Plan 04 adds the write
nodes strictly downstream of the resume — in that order. Nyquist/Wave-0 discipline holds
(Plan 01 authors all RED tests first; every implementation task has a matching
`<automated>` verify).

No blockers. Four warnings should be fixed before execution to remove ownership/ordering
ambiguity that would otherwise be discovered mid-execution.

---

## 1. Requirement coverage (per-requirement)

| Req | Delivering plan(s) | Real acceptance evidence | Status |
|-----|--------------------|--------------------------|--------|
| CUR-02 (`card.evaluate` promote/hold/escalate + evidence) | 02 (curation_promote.py gate) · 01 (RED tests) · 05 (register) | `test_curation_promote.py` decision-mapping + `test_failure_escalates`; PromotionDecision.reasoning is the evidence | COVERED |
| CUR-03 (review before lifecycle/connection writes) | 03 (producers + interrupt-only) · 04 (post-gate apply nodes) · 01 (tests) | `test_no_writes_before_approval`, `test_no_unreviewed_writes`, `test_reviewed_*_applied`, `test_single_consolidated_gate` | COVERED |
| CUR-04 (inspect status/degraded/pending/outcomes/events) | 04 (extend inspect + events) · 01 (tests) | `test_inspect_pending_review`, `test_curation_events_emitted`; awaiting_review branch + gate_queue | COVERED (see W-3 on per-step events) |
| CUR-05 (offline anti-placeholder + no-unreviewed-write tests) | 01 (tests) · 05 (delete `_get_workflow_steps`) | `test_no_placeholder_curation_path`, `test_no_unreviewed_writes`, existing `test_steps_return_concrete_findings` | COVERED |
| API-04 (skills delegate; no WebSearch/WebFetch/write) | 06 (migrate 3 skills + human verify) · 01 (guard) | `test_skill_migration.py` forbidden-tool guard on all 3 skills | COVERED |

No PROJECT/ROADMAP requirement mapped to Phase 12 is dropped. Deferred items
(DAY-01, API-01/02/03/05, views.generate_data, cooldown) are correctly absent — Plan 05's
only mention of API-05 is a "no-regression" verification, not implementation.

## 2. Design-decision fidelity (D-01…D-10)

| Decision | Operationalized by | Faithful? |
|----------|--------------------|-----------|
| D-01 LLM-always | 02 T1 (every non-mature card → LLM gate) | Yes |
| D-02 candidate = non-mature | 02 T1 + 03 T2 (pre-filter `lifecycle != mature` AND `!= archived`) | Yes |
| D-03 retry-then-escalate + `method` split | 02 T1 (`_escalate_decision_for_failure` → escalate/method=rule-based; borderline=llm-judgment) | Yes |
| D-04 all three write types | 04 T1 (apply_promotions/connections/archives) | Yes |
| D-05 connection typing = LLM L3 gate | 02 T2 (curation_connect.py over bridge_detect candidates) | Yes (correctly uses candidates, not "untyped edges" — RESEARCH Discrepancy 2) |
| D-06 single consolidated gate | 03 (one gate_queue, one interrupt) | Yes |
| D-07 actionable+escalate only, default=gate rec, only-approved writes | 03 T2 (hold=events-only) + 04 T1 (default=gate rec; escalate review-only) | Yes (see Note) |
| D-08 thin orchestrator + scope negotiation | 06 T1 | Yes |
| D-09 migrate all 3, fold card-evaluate | 06 T1/T2 | Yes |
| D-10 remove placeholder lambdas + anti-placeholder test | 05 T2 (both files atomically) + 01 T3 | Yes (Pitfall 6 two-file removal explicitly handled) |

Lifecycle naming (RESEARCH Discrepancy 1) correctly resolved: `target_lifecycle` is
`growing|mature` only; archive is a separate write type. Plan 02/04 explicitly reject
`seed`/`seedling`/`archived` as target_lifecycle.

## 3. Dependency / ordering

01 → 02 → 03 → 04 → 05(dep 02,04) → 06. Acyclic; waves consistent (05 = max(2,4)+1 = 5).
Review-before-write ordering is correct: read-side/interrupt (03) precedes write-side (04);
the write nodes cannot exist upstream of the interrupt because the interrupt is grafted
before the apply nodes are added. Plans 03 and 04 both edit curation_run.py in sequential
waves (different regions) — no conflict.

## 4. Warnings (fix before execution)

**W-1 (ownership gap) — `CardEvaluateInput` has no owning task.**
Plan 05 T1 registers `card.evaluate` with `input_model=CardEvaluateInput` and its
`read_first` expects `curation_promote.py (run_gate + CardEvaluateInput)`. But Plan 02
(owner of curation_promote.py) never lists `CardEvaluateInput` in its artifacts/tasks, and
Plan 05's `files_modified` is only catalog.py + cli.py. As written, no task creates the
model in a file it owns. Fix: add `CardEvaluateInput` to Plan 02 T1 artifacts/action, OR
add curation_promote.py to Plan 05 files_modified. Severity WARNING (executor can self-heal
a thin model, but the contract should be explicit).

**W-2 (implicit state channel) — `gate_id` not in Plan 03's state-channel list.**
Plan 03 T2's interrupt payload is `interrupt({"gate_id": ..., "gate_queue": ...})` and
`test_single_consolidated_gate` asserts "one gate_id", but Plan 03 T1 enumerates only
`gate_queue`, `decisions`, and per-write channels — no `gate_id` channel or its
population. `state["gate_id"]` would KeyError unless the executor adds it. Fix: have Plan 03
T1 add a `gate_id` channel and populate it (e.g., derived from run_id) mirroring research_run.

**W-3 (CUR-04 scope ambiguity) — per-deterministic-step events.**
CUR-04 requires events "for every deterministic step and review gate." Plan 04 T2 places
event emission "in the apply/report nodes and the review runner" — this may under-emit for
the deterministic prefix (integrity/decay/orphan/connection producers) unless Phase 11
already emits per-step events. `test_curation_events_emitted` is the safety net, but Plan 04
should state explicitly that per-step events cover the deterministic steps too (or confirm
Phase 11 already emits them). Fix: clarify event coverage of the deterministic prefix.

**W-4 (housekeeping) — VALIDATION.md sign-off not flipped.**
`12-VALIDATION.md` frontmatter still reads `nyquist_compliant: false`, `wave_0_complete:
false`, and the Sign-Off checklist is unchecked, even though Plan 01 delivers all Wave-0
tests and every task carries an `<automated>` verify. Flip these after confirming Plan 01
scope, so the phase's own gate record is accurate.

## 5. Notes (informational, no action required)

- **escalate = review-only this phase** (Plan 04, RESEARCH Open-Q 3). Consistent with D-07
  "no default write" (an escalate has no `target_lifecycle` to write anyway). The
  discussion log did not cover escalate resume semantics; the decision was made at
  research/plan time and is defensible. Surface to the user if a human-approvable escalate
  write is expected later (Phase 13).
- **Plan 04 volume:** one file, 2 tasks, but grafts many symbols (3 apply nodes + decision
  resolution + review runner + run-start pause + extended inspect + events). Within task/file
  budget and it is structural copying from research_run.py, so risk is moderate, not a
  blocker. Watch context during execution.

## Dimension summary

| Dimension | Result |
|-----------|--------|
| 1 Requirement coverage | PASS |
| 2 Task completeness | PASS (all auto tasks have files/action/verify/done; checkpoint task well-formed) |
| 3 Dependency correctness | PASS |
| 4 Key links planned | PASS (producers→gate_queue→apply nodes→knowledge writes all wired) |
| 5 Scope sanity | PASS (2–3 tasks/plan; ≤5 files/plan) |
| 6 must_haves derivation | PASS (truths are user-observable) |
| 7 Context compliance | PASS (no deferred ideas included) |
| 7b Scope reduction | PASS (no v1/simplified/static reductions of decisions) |
| 7c Architectural tier | PASS (judgment in Python L3; writes in post-gate nodes; inspect read-only) |
| 8 Nyquist | PASS (VALIDATION.md exists; every task has automated verify; Wave 0 authors all RED tests; no watch mode; continuity holds) |
| 9 Cross-plan data contracts | PASS (CurationProposal / PromotionDecision contracts consistent across 02/03/04) |
| 10 CLAUDE.md compliance | SKIPPED (no CLAUDE.md in repo/working dir) |
| 11 Research resolution | PASS (Open Questions marked RESOLVED; all 3 mapped to plans) |
| 12 Pattern compliance | PASS (every plan references its PATTERNS.md analog + excerpts) |

**Overall: READY-WITH-CONCERNS — 0 blockers, 4 warnings.** Execution can proceed; fixing
W-1 and W-2 first is recommended to avoid mid-execution ownership/KeyError surprises.
