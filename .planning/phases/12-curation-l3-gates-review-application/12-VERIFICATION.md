---
phase: 12-curation-l3-gates-review-application
verified: 2026-07-02T22:15:00Z
status: verified
score: 5/5 must-haves verified (automated); human UAT PASSED 2026-07-05
overrides_applied: 0
human_verification:
  - test: "Run the migrated construct-curation-cycle skill conversationally against test-ws/my-construct"
    expected: "Skill invokes `construct curation run` (not inline logic), pauses presenting the consolidated gate_queue (promotion/connection/archive/escalate with method field visible); approve a subset + reject the rest -> calls `construct curation review`; only approved items written (confirm via `construct curation inspect`); zero direct WebSearch/WebFetch/Write during the session"
    why_human: "End-to-end conversational skill behavior (Plan 12-06 Task 3, checkpoint:human-verify) cannot be exercised programmatically; the executor intentionally deferred it."
    result: "PASSED 2026-07-05 — drove the migrated curation-cycle procedure end-to-end: `curation run` paused at awaiting_review with real llm-judgment proposals (method visible); approved via `curation review`; only-approved writes landed (2 cards → mature); re-review no-op (idempotent); events emitted (workflow_step_complete + gate_review_approved + curation_cycle_complete); zero WebSearch/WebFetch/Write. Surfaced+fixed a retired-model config bug (commit f14f958) and resynced stale workspace skill installs."
---

# Phase 12: Curation L3 Gates + Review Application — Verification Report

**Phase Goal:** Users can review lifecycle and connection proposals before any high-impact curation writes occur, and research/curation skills delegate to the runtime. (ROADMAP; brief restatement: "promotion and connection proposals use reusable human review before canonical writes, with migrated skills.")
**Verified:** 2026-07-02
**Status:** human_needed (code-complete + automated-verified; one conversational UAT outstanding)
**Re-verification:** No — initial verification
**Overall verdict:** **GOAL MET WITH CAVEATS** — all five success criteria are achieved in code and backed by passing offline tests; one human UAT (API-04 conversational skill loop) remains before the phase is fully verified-complete.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `card.evaluate` gate proposes promote/hold/escalate with evidence (CUR-02) | ✓ VERIFIED | `curation_promote.py` — real `PromotionDecision` (`decision: Literal["promote","hold","escalate"]`, `reasoning`, `target_lifecycle: Literal["growing","mature"]|None`). `_evaluate_one_with_retry` → retry then rule-based `escalate` (`method="rule-based"`, l.254-289). Total-outage → `CardEvaluateOutageError` (l.355-409). 13/13 unit tests pass incl. promote/hold/escalate/failure-escalates/retry-then-succeed/total-outage/key-leak-sanitizer. |
| 2 | Approve/reject lifecycle & connection proposals before canonical writes (CUR-03) | ✓ VERIFIED | Write-boundary by construction: graph is producers → `_route_before_inbox` → `process_inbox`(interrupt-ONLY, l.744-759) → `apply_promotions`(edit_card l.873) → `apply_connections`(add_connection l.920) → `apply_archives`(archive_card l.969) → compile_report. All three write symbols are strictly downstream of the interrupt (744); zero write calls upstream (grep-confirmed). `_resolve_decisions`+apply nodes write only on approved verdict; reject/escalate write nothing. Idempotent (skip-if-at-target / add_connection dedup / skip-if-archived). Tests: no_writes_before_approval, no_unreviewed_writes, reviewed_promotion/archive_applied, reviewed_connection_idempotent, cross_process_resume — all green. |
| 3 | Inspect status, degraded states, pending reviews, outcomes, and emitted events (CUR-04) | ✓ VERIFIED | `inspect_curation_run` surfaces `awaiting_review` + `gate_queue` without resuming (paused branch checked FIRST, l.1204-1211; read-only get_state, no node execution). Events: `workflow_step_complete` per deterministic step, `gate_review_approved`/`gate_review_rejected` per proposal, single `curation_cycle_complete` from compile_report. Tests test_inspect_pending_review + test_curation_events_emitted pass. `curation.inspect` description advertises awaiting_review. |
| 4 | Offline tests fail if placeholder handlers or unreviewed writes remain (CUR-05) | ✓ VERIFIED | `_get_workflow_steps` deleted from BOTH catalog.py and cli.py (`grep -rn _get_workflow_steps src/` → 0). `workflow.run` capability + `workflow run`/`workflow resume` CLI commands removed; only `workflow status` (real WorkflowRunner state reader) remains. Guards present & passing: `test_no_placeholder_curation_path` (source-greps both files), `test_no_unreviewed_writes` (inspects gate-node source: exactly one interrupt(), no edit_card/add_connection/archive_card/append_event/write_text/.write). |
| 5 | Migrated skills delegate to CLI/MCP (no WebSearch/WebFetch/workspace writes) (API-04) | ⚠ PARTIAL — code-complete, UAT pending | All three SKILL.md `allowed-tools` = `Read, Bash(construct), MCP(connect)` (no WebSearch/WebFetch/Write/Edit). All delegate to `construct research|curation|card` CLI. `test_skill_migration.py` 6/6 pass. **Outstanding:** Plan 12-06 Task 3 conversational UAT (checkpoint:human-verify) not performed — see Human Verification. |

**Score:** 5/5 truths achieved in code and automated-verified. Truth 5's deterministic deliverable is complete; its interactive UAT is the single outstanding item, so the phase is not yet *fully* verified-complete.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/construct/llm/curation_promote.py` | card.evaluate L3 promotion gate | ✓ VERIFIED | 421 lines; PromotionDecision, evaluate_one/all, run_gate, CardEvaluateOutageError, sanitizer. Wired into catalog `card.evaluate` + promotion_review producer. |
| `src/construct/llm/curation_connect.py` | connection-typing L3 gate | ✓ VERIFIED | 266 lines; ConnectionTypeDecision, type_one/all, run_gate. Wired into connection_maintenance producer. |
| `src/construct/llm/curation_run.py` | HITL graph (producers + interrupt + apply nodes + runners + inspect) | ✓ VERIFIED | 1227 lines; interrupt-only process_inbox, 3 apply nodes downstream, run/review/inspect runners. |
| `src/construct/capabilities/catalog.py` | register card.evaluate + curation.review; drop placeholder + workflow.run | ✓ VERIFIED | card.evaluate + curation.review + curation.inspect registered with cli_name + mcp_tool_name; _get_workflow_steps + workflow.run gone. |
| `src/construct/cli.py` | `card evaluate` + `curation review` commands; drop workflow run/resume | ✓ VERIFIED | Only `workflow status` remains; commands present (test_cli_commands_present green). |
| 3× SKILL.md (research/curation/card) | thin CLI orchestrators | ✓ VERIFIED | allowed-tools clean; delegate to CLI. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| process_inbox | (writes) | interrupt boundary | ✓ WIRED | All writes strictly downstream of l.744 interrupt; none upstream. |
| promotion_review producer | curation_promote.evaluate_all | direct call l.692 | ✓ WIRED | Real gate call; enqueues promote/escalate proposals into gate_queue. |
| catalog card.evaluate | curation_promote.run_gate | _card_evaluate_shim l.658 | ✓ WIRED | Registered + sanitizing shim; MCP tool auto-discovered. |
| catalog curation.review | review_curation_run | _curation_review_shim l.642 | ✓ WIRED | Resume path; Command(resume=decisions). |
| SKILL.md | construct CLI | Bash(construct) | ✓ WIRED | 9/9/5 delegation references; no direct web/write tools. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full offline suite | `.venv/bin/pytest tests/ -q` | 389 passed, 0 failed, 109 pre-existing warnings | ✓ PASS |
| Placeholder excised | `grep -rn _get_workflow_steps src/` | 0 matches | ✓ PASS |
| Write-boundary | grep process_inbox(744) vs edit_card(873)/add_connection(920)/archive_card(969) | all writes downstream | ✓ PASS |
| Skill allowed-tools | grep allowed-tools line for WebSearch/WebFetch/Write/Edit | 0 across all 3 skills | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| CUR-02 | 12-01/02/05 | ✓ SATISFIED | card.evaluate gate + registration; 13 unit tests. |
| CUR-03 | 12-01/03/04 | ✓ SATISFIED | Interrupt-only pause + downstream-only writes; reviewed-write + idempotency + cross-process-resume tests. |
| CUR-04 | 12-01/04 | ✓ SATISFIED | inspect awaiting_review + full event emission; tests green. |
| CUR-05 | 12-01/05 | ✓ SATISFIED | Placeholder + workflow.run removed; anti-placeholder + no-unreviewed-write guards. |
| API-04 | 12-01/06 | ⚠ PARTIAL | Deterministic skill migration complete + guard green; conversational UAT outstanding. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX debt markers in phase-modified source | ℹ Info | None. views_refresh_hook remains an intentional `required=False` deferred no-op (not reachable as a curation-write placeholder; documented, guarded by _aggregate_status). |

## Resolution of the Three Flagged Items

1. **REQUIREMENTS.md premature CUR-03 marking** — CONFIRMED-and-now-accurate. Plan 12-02 SUMMARY declared `requirements-completed: [CUR-02, CUR-03]` before the reviewed-write path existed (it landed in 12-03 read-side + 12-04 write-side). That marking was premature *at the time*, but the final code now genuinely satisfies CUR-03 (write-boundary + reviewed writes verified above), so the `[x] Complete` flag is no longer inaccurate. **However REQUIREMENTS.md is now STALE in the opposite direction:** CUR-04 and CUR-05 are still `[ ] Pending` / traceability "Pending" despite being fully automated-verified, and API-04 is "Pending" (code-complete, UAT outstanding). Recommended correction at phase close: CUR-04 → Complete, CUR-05 → Complete, API-04 → Complete-pending-UAT (or hold until UAT). I did not edit REQUIREMENTS.md — the flip is a phase-close/orchestrator action, and API-04 completion is gated on the outstanding UAT.

2. **Plan 12-04 out-of-scope deviation — workspace.py::load_cards lifecycle normalization** — CONFIRMED, NO REGRESSION. `load_cards` now normalizes `lifecycle` to its string value (`getattr(lifecycle,"value",lifecycle)`, workspace.py l.166-167) while keeping `created`/`last_verified` as `datetime.date`. `Lifecycle` is a `(str, Enum)` (card.py l.35). Every load_cards lifecycle consumer uses tolerant access: curation_run decay_scan (l.413-414), orphan_scan (l.482-483), _card_lifecycle_map (l.817-818) all use `getattr(lifecycle,"value",lifecycle)`; curation_promote `_lifecycle_value` (l.114) same. `graph_status.py:26` uses `card.lifecycle.value` but on Card *model objects*, not load_cards dicts (graph_status is not in the load_cards caller set), so it is unaffected. bridge_detect / research_score load_cards callers do no lifecycle comparison. Full suite 389 passed. **Recorded as a cross-cutting deviation with zero regression.**

3. **Plan 12-05 removal of `workflow run`/`resume` group + workflow.run capability (Open-Q 1)** — CONFIRMED, NOTHING LEGITIMATELY DEPENDED ON IT. The `workflow.run` capability's only content was the fake-success curation-cycle placeholder; `curation.run` is now the sole canonical curation entrypoint. Only `workflow status` remains in the CLI workflow group and it reads genuine persisted `WorkflowRunner` state (catalog.py l.322). No placeholder path survives (grep + test_no_placeholder_curation_path). Inventory guards (test_catalog_loads / test_mcp_tool_count / _payload_for) updated in lockstep.

**Additional confirmation — mcp/server.py NOT edited:** `src/construct/mcp/server.py` last changed in commit `f0a7ccd` (v0.3 phase 1); no Phase-12 commit touches it. MCP parity for card.evaluate + curation.review is achieved purely via registry auto-discovery (test_mcp_no_hardcoded_curation green). Confirmed.

### Human Verification Required

**1. Conversational skill review-loop UAT (Plan 12-06 Task 3 — OUTSTANDING)**

**Test:** Run the migrated `construct-curation-cycle` skill conversationally against `test-ws/my-construct`.
**Expected:** Skill invokes `construct curation run` (not inline logic), pauses presenting the consolidated `gate_queue` (promotion / connection / archive / escalate items, `method` field visible). Approve a subset + reject the rest → skill calls `construct curation review`; re-running `construct curation inspect` shows only the approved items written. Zero direct WebSearch / WebFetch / Write occurred during the session. Optionally repeat for `construct-research-cycle` and `construct-card-evaluate`.
**Why human:** End-to-end conversational skill behavior (checkpoint:human-verify) cannot be exercised programmatically; the executor intentionally deferred it per 12-VALIDATION.md "Manual-Only Verifications." The deterministic deliverable (SKILL.md edits + test_skill_migration.py guard + full-suite green) is complete; only the interactive verification remains.

### Gaps Summary

No code gaps. All five success criteria are implemented and backed by passing offline tests (389 passed / 0 failed, run independently by the verifier). The CUR-03 no-canonical-write-before-approval spine holds by construction (interrupt-only pause, all writes downstream, only-approved + idempotent). The three flagged items resolve cleanly: the load_cards deviation introduces no regression, the workflow.run removal leaves no orphaned dependency or placeholder, and mcp/server.py is untouched. The single non-code item is the outstanding API-04 conversational UAT (Plan 12-06 Task 3), which gates full phase completion — **do not mark Phase 12 fully verified-complete until that UAT passes.** Recommended follow-up: refresh REQUIREMENTS.md status for CUR-04/CUR-05 (now Complete) and API-04 (code-complete, UAT-pending) at phase close.

---

_Verified: 2026-07-02_
_Verifier: Claude (gsd-verifier)_
