---
phase: 18-contract-governance-foundations
verified: 2026-07-30T22:40:00Z
status: human_needed
score: 5/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "research.run / research.review / research.inspect now report the RunResult.degraded signal as the OperationResult.outcome (\"degraded\") on a genuinely completed-but-retrieval-degraded run, closing the gap the previous pass identified: catalog.py::_run_result_to_operation previously set outcome=result.status, and RunResult.status for the research graph never takes the value \"degraded\" (only awaiting_review | completed | failed) — the degraded signal lived only in the separate RunResult.degraded boolean, which the outcome mapping never read. Commit 9ad383e adds _run_outcome(result), which folds degraded into outcome at the single place the research envelope is built (failed wins over degraded), and _run_result_to_operation now calls it."
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
behavior_unverified_items: []
human_verification:
  - test: "Load a workspace with Python-emitted events in the CONSTRUCT Views SPA and visually confirm ActivityList.jsx renders agent/action/target/result instead of blank rows."
    expected: "Each row shows a non-blank agent and action; an escalated event shows the amber 'escalated' badge."
    why_human: "18-05's ActivityList.jsx change (D-17's reader-side conformance) has no JS toolchain in this environment to execute or type-check (`T-18-SC` forbids one). Verified by source review only (the component's destructured keys — `e.ts`/`e.agent`/`e.action`/`e.target`/`e.detail`/`e.result` — now match `parse_events.py`'s canonical output exactly), which the 18-05 SUMMARY itself flags with `human_judgment: true`; it was never exercised at runtime."
---

# Phase 18: Contract & Governance Foundations Verification Report

**Phase Goal:** Every contract a browser will depend on tells the truth before a browser exists — the views projection validates against its own validator, all invocation surfaces validate against one seam, and a human-review decision cannot be misapplied.
**Verified:** 2026-07-30T22:40:00Z
**Status:** human_needed
**Re-verification:** Yes — third pass, after a second gap-closure attempt (commit `9ad383e`)

## Goal Achievement

This is the third verification pass on criterion 5. The first pass found 4/5 roadmap success
criteria verified, with criterion 5 (GOV-05) failing on `daily.run` and `research.run`. The second
pass (commit `8aea454`) fixed the CLI renderer and `daily.run`/`curation.run`, but found the fix
incomplete: `research.run`/`research.review`/`research.inspect` still rendered an unqualified `✓`
on a real, completed-but-retrieval-degraded run, because `catalog.py::_run_result_to_operation` set
`outcome=result.status`, and `RunResult.status` for the research graph never actually takes the
value `"degraded"` — that signal lived only in a separate `RunResult.degraded` boolean the outcome
mapping never read.

**This pass does not trust the commit message or the SUMMARY's "774 passed, 0 failed" claim as
evidence of closure.** Every claim below was independently re-derived in this session:

- The suite was re-run from scratch (`774 passed, 18 skipped, 0 failed`, confirmed).
- The new `_run_outcome()` fold in `catalog.py` was read at the current commit and confirmed to
  be the single site feeding `_run_result_to_operation`'s `outcome=`.
- The fix was driven through the **REAL** capability pipeline, not just the new unit-level tests:
  a real `get_registry().invoke("research.run", ...)` → real `build_research_run_graph()` → real
  gate pause → a second real `get_registry().invoke("research.review", ...)` with
  `Command(resume=...)`-equivalent decisions → real completion, with `research_score.run_gate`
  monkeypatched to a degraded batch (the same fixture shape as
  `tests/llm/test_research_run.py::test_digest_degraded_notice`). This exercised the actual CLI
  human renderer (`cli._emit_run_result`), the actual `--json` path, and the actual MCP serializer
  (`mcp/server.py::_serialize_result`) — end to end, not synthetic `OperationResult` construction.
- The 4 new regression tests in `tests/integration/test_surface_honesty.py` were independently
  proven RED by temporarily reverting `outcome=_run_outcome(result)` back to `outcome=result.status`
  and re-running them: 2 of the 4 failed, reproducing the exact `'✓ Run complete.'` defect the
  second pass caught, byte-for-byte. The fix was then restored and the suite re-confirmed green.
- `research.inspect` and `research.review` were independently exercised (the second pass's own gap
  report named all three commands as failing; this pass verifies all three, not just one).
- A genuinely clean, non-degraded completed run was independently driven through the same
  real pipeline and confirmed to still render an unqualified `✓ Run complete.` — the fix is
  outcome-driven, not a blanket qualification (no over-qualification regression).
- `daily.run`/`curation.run` use their own separate wrap functions
  (`_curation_run_result_to_operation`, `_daily_run_result_to_operation`), untouched by this
  commit's diff (`git diff --stat 8aea454 9ad383e` touches only `catalog.py` and the test file);
  their 28/28 surface-honesty tests still pass, confirming no regression.
- Criteria 1-4's scoped files are untouched by this commit's diff, and the untouched-scope tests
  (`test_views_generate_output_round_trips_through_views_validate`,
  `tests/integration/test_surface_parity.py` 22/22) still pass.

**Result: criterion 5 is now fully closed.** All three research-run-family commands
(`research.run`, `research.review`, `research.inspect`) render honestly on a real,
completed-but-degraded run, on every surface checked (CLI human, CLI `--json`, MCP).

### Observable Truths (ROADMAP Phase 18 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `views validate` accepts every one of the 8 (really `4+6·N+1`) files `views generate` writes | ✓ VERIFIED (unchanged, no regression) | Untouched by commit `9ad383e` (diff touches only `catalog.py` + `test_surface_honesty.py`). `test_views_generate_output_round_trips_through_views_validate` still passing in the full 774/774 non-skipped run. |
| 2 | Same capability id + payload → identical structured result across CLI and MCP, unknown field rejected on both — including the failure path | ✓ VERIFIED (unchanged, no regression) | Untouched by commit `9ad383e`. `tests/integration/test_surface_parity.py` re-run independently: 22/22 pass. |
| 3 | A decision names its proposal; a resume against a changed queue is rejected with zero writes; a missing decision never falls back to applying a write | ✓ VERIFIED (unchanged, no regression) | Untouched by commit `9ad383e`. Staleness/ETag tests in `curation_run.py`/`research_run.py` scope still pass. |
| 4 | No surface writes canonical truth outside the reviewed workflow's resume path, and no approval event exists for a decision that was never applied | ✓ VERIFIED (unchanged, no regression) | Untouched by commit `9ad383e`. `test_no_canonical_writer_outside_the_apply_nodes` and the approval-event tests still pass. |
| 5 | A degraded or partially-applied run reports degraded on every surface that can report it, and escalated items surface as pending rather than folded into a success count | ✓ **VERIFIED — now fully closed** | `curation.run`/`daily.run` (confirmed honest in pass 2) plus `research.run`/`research.review`/`research.inspect` (confirmed honest in this pass) all render `⚠ degraded: ...` on a real degraded run, on CLI human, CLI `--json`, and MCP surfaces. See Behavioral Spot-Checks. |

**Score:** 5/5 roadmap success criteria verified

### Required Artifacts (delta from previous pass)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/construct/capabilities/catalog.py` | `outcome` carries the degraded signal for the research run-composition family | ✓ VERIFIED | `_run_outcome(result)` (new, ~line 917) folds `RunResult.degraded` into the outcome: `failed` if `result.status == "failed"`, else `"degraded"` if `result.degraded`, else `result.status`. `_run_result_to_operation` (research.run/review/inspect's shared builder) now calls `outcome=_run_outcome(result)` instead of `outcome=result.status`. Independently proven load-bearing by reverting the one-line change and re-running the targeted tests: 2/4 fail, reproducing the exact prior defect. |
| `tests/integration/test_surface_honesty.py` | Regression coverage that exercises the REAL production data shape, not a synthetic `OperationResult` | ✓ VERIFIED | 4 new tests: `test_research_envelope_reports_degraded_for_a_completed_degraded_run` and `test_research_envelope_keeps_failed_over_degraded` construct a real `RunResult` (the object the graph actually returns) and drive it through the real `_run_result_to_operation`; `test_research_degraded_run_renders_a_qualified_verdict` drives the whole chain to rendered stdout; `test_run_result_status_still_lacks_a_degraded_member` pins the precondition that makes the fold necessary (reads live `research_run.py` source). All 4 pass; all 4 independently confirmed RED against the reverted fix. |

### Behavioral Spot-Checks (this pass)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full test suite (once) | `.venv/bin/python -m pytest -q` | `774 passed, 18 skipped, 0 failed` | ✓ PASS (necessary, not sufficient) |
| **`research.run` real graph, degraded batch, paused at gate** | Real `get_registry().invoke("research.run", ...)` with `research_score.run_gate` monkeypatched to a degraded `ResearchScoreGateOutput` (mirrors `test_digest_degraded_notice`); rendered via real `cli._emit_run_result` | `RunResult.status == "awaiting_review"`, `degraded == True` → `OperationResult.outcome == "degraded"` → rendered `"⚠ degraded: Paused for human review; resume with research.review."` | ✓ **PASS — honest** |
| **`research.review` real graph, resumed to completion, degraded** | Same real graph/DB, second real `get_registry().invoke("research.review", ...)` with the paused gate's decisions, resumed to genuine completion | `RunResult.status == "completed"`, `degraded == True` → `OperationResult.outcome == "degraded"` → rendered `"⚠ degraded: Run complete."` (previously the exact defect: `"...\ndegraded: True\n✓ Run complete."`) | ✓ **PASS — the exact previously-failing case now honest** |
| **`research.inspect` real graph, after completion, degraded** | Same real DB, real `get_registry().invoke("research.inspect", ...)`, read-only, no resume | `status == "completed"`, `degraded == True` → `outcome == "degraded"` → rendered `"⚠ degraded: Run is complete."` | ✓ **PASS — honest** |
| `--json` agrees with the human renderer | `cli._emit_run_result(review_op, json_output=True)` on the same degraded `research.review` result | `{"outcome": "degraded", ...}` | ✓ PASS |
| MCP serializer agrees with `--json` | `mcp_server._serialize_result(review_op)` on the same degraded `research.review` result | `{"outcome": "degraded", ...}` — identical to the `--json` value | ✓ PASS |
| Genuinely clean, non-degraded completed run stays unqualified (no over-qualification regression) | Real graph, undegraded `scored_findings_batch`, run through `research.run` → `research.review` | `outcome == "completed"`, rendered `"✓ Run complete."` | ✓ PASS |
| `daily.run`/`curation.run` no regression | `tests/integration/test_surface_honesty.py` full file, 28 tests (includes the pass-2 daily/curation-degraded rows) | `28 passed` | ✓ PASS |
| New tests independently proven RED against the reverted fix | Reverted `outcome=_run_outcome(result)` → `outcome=result.status`; re-ran the 4 new tests | `2 failed` (`test_research_envelope_reports_degraded_for_a_completed_degraded_run`, `test_research_degraded_run_renders_a_qualified_verdict`), reproducing `'✓ Run complete.'` verbatim; fix restored and suite re-confirmed green | ✓ PASS — non-vacuous regression coverage confirmed |

### Requirements Coverage (delta)

| Requirement | Status | Evidence |
|---|---|---|
| GOV-05 | ✓ **SATISFIED** | Criterion 5 above, closed on all three research-run-family commands plus the previously-fixed `curation.run`/`daily.run`. |
| VFIX-01, GOV-01, GOV-02, GOV-03, GOV-04 | ✓ SATISFIED (unchanged) | No files in these requirements' scope were touched by commit `9ad383e`; full suite re-run confirms no regression. |

### Carried Debt (by decision — not scored as gaps, not re-litigated this pass)

Unchanged from the prior pass, per explicit instruction:

- **D-21** GOV-01's MCP schema-discoverability gap (behaviour true, discovery false — pinned test).
- **D-22** the `ui.safety-gate` override for this phase.
- **D-23** GOV-04 scopes to review-decided canonical writes; `pipelines/ingestion.py` sits in `UNRESOLVED_DIRECT_CALLERS` as a shrink-only baseline, not an exemption.
- **D-24** criterion 4's event-count invariant scopes to the curation graph; the research graph's `update_seeds_and_log` approval-from-decision is a known deferred instance.
- **12 remaining code-review warnings**, deliberately outside the fix scope — notably WR-03 (`mcp/server.py` returns `str(exc)`; `graph.status` messages carry filesystem paths), WR-05 (canonical-write guard grants exemptions by substring match while using AST rigor elsewhere), WR-06 (review models don't enforce mutual exclusion of `decisions`/`approve_all`/`reject_all`).
- **`escalate` on a connection proposal emits `gate_review_rejected`** — nothing is written either way, but recording an escalation as a rejection is the audit inconsistency 18-08 closed for the other three apply nodes; `apply_connections` has no `escalated` bucket.
- **`test_reviewed_connection_idempotent` is vacuous** — the `curation_workspace` fixture produces no bridge candidates, so `connection_maintenance` enqueues no connection proposal.
- **`ActivityList.jsx` (18-05)** source-verified only — no JS toolchain, forbidden by `T-18-SC`. Routed to human_verification below.
- **Minor, non-blocking, unchanged by this pass:** `research.score`'s success path (`catalog.py::_research_score_shim`) never sets `OperationResult.outcome` at all — its degraded signal is folded into the message text only (`"Scored N findings (degraded)"`), so the rendered line keeps the `✓` glyph (`"✓ Scored N findings (degraded)"`). This is not silent (the word "degraded" is in the message) and `research.score` was not one of the three commands named in either gap report as part of criterion 5's failing scope (it is a scoring gate, not a `run`/`review`/`inspect` composition command) — consistent with the prior pass's judgment, this is noted as carried, non-blocking debt, not a re-opened gap.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in the files touched by commit
`9ad383e`. The dishonesty anti-pattern (T-15-14, unqualified `✓` on a non-clean outcome) is now
resolved on all five terminal-emitter commands and all three research-run-family capability ids —
confirmed live against the real pipeline, not only against the commit's own synthetic-shape
regression tests.

### Human Verification Required

1. **ActivityList.jsx renders live Python-emitted events correctly** — unchanged from prior passes;
   not touched by commit `9ad383e`. See frontmatter `human_verification`.

### Gaps Summary

None remaining for criterion 5. Commit `9ad383e` closes the exact gap the second verification pass
named: `catalog.py::_run_result_to_operation` now folds `RunResult.degraded` into the reported
`outcome` for the research-run family (`_run_outcome`), the same way `curation.run` and `daily.run`
already baked `"degraded"` into their own status enums. All three research-run-family commands
(`research.run`, `research.review`, `research.inspect`) were independently driven through the real
LangGraph pipeline — a real gate pause and a real resume-to-completion, not a synthetic
`OperationResult` — and confirmed honest on the CLI human renderer, `--json`, and the MCP
serializer. A genuinely clean run was independently confirmed to remain unqualified, ruling out
over-qualification. The regression tests added in this commit were independently proven
non-vacuous by reverting the fix and observing them fail with the exact original defect.

**Status is `human_needed`, not `passed`**, solely because of the pre-existing, unrelated
`ActivityList.jsx` human-verification item (D-17/18-05), which this commit did not touch and which
was already routed to human verification in the first verification pass. All roadmap success
criteria (5/5) are now verified.

---

_Verified: 2026-07-30T22:40:00Z_
_Verifier: Claude (gsd-verifier)_
