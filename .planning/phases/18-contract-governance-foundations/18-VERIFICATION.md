---
phase: 18-contract-governance-foundations
verified: 2026-07-30T19:06:00Z
status: gaps_found
score: 4/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A degraded or partially-applied run reports degraded on every surface that can report it, and escalated items surface as pending rather than folded into a success count. (ROADMAP Phase 18 success criterion 5 / REQ GOV-05)"
    status: partial
    reason: >
      The GOV-05 honest-verdict renderer (`cli._verdict_line`) is wired into
      `_emit_curation_result` only. `_emit_run_result` (research.run /
      research.review / research.inspect) and `_emit_daily_result` (daily.run)
      still call the old unconditional `typer.echo(f"✓ {result.message}")` on
      every success path, regardless of `result.outcome`. This is code-review
      finding WR-02 (18-REVIEW.md), explicitly left unfixed because the fix
      pass was scoped to the five Critical findings only (18-REVIEW-FIX.md).
      Live-reproduced against the actual `construct.cli` module (not merely
      inferred): a `daily.run` whose aggregate status is "degraded" (reachable
      any time `pending_escalations > 0` or any child is
      failed/degraded/awaiting_review — `daily_run.py:125-138`, not a rare
      edge) prints `✓ Daily cycle degraded.` as its final line. A `research.run`
      that completes with `retrieval.degraded = True` prints `degraded: True`
      immediately followed by the unqualified `✓ Run complete.` in the same
      output block — the exact "audit-trail-that-lies" pattern (T-15-14) GOV-05
      exists to close, on the two surfaces the fix pass did not touch.
      `test_surface_honesty.py` (the table-driven cross-surface honesty suite
      18-08 built) covers `curation.run` only; no test exercises
      `daily.run`'s or `research.run`'s human-readable degraded path, so the
      suite is green while the defect is live. The CLI `--json` payload and the
      MCP structured result ARE honest for both surfaces (outcome/degraded ride
      on the envelope untouched) — only the human-readable text renderer lies.
    artifacts:
      - path: "src/construct/cli.py"
        issue: "_emit_run_result (line ~580-590) and _emit_daily_result (line ~890-901) print an unqualified `✓ {message}` instead of calling `_verdict_line(result)`, unlike _emit_curation_result which was fixed."
    missing:
      - "Replace both `typer.echo(f\"✓ {result.message}\")` call sites with `typer.echo(_verdict_line(result))`, mirroring `_emit_curation_result`."
      - "Extend `tests/integration/test_surface_honesty.py` (or an equivalent table) with a `daily.run` degraded row and a `research.run` completed-but-`data.degraded=True` row, asserting no unqualified `✓` appears alongside a `degraded`/non-clean signal in the same human-readable block."
deferred: []
behavior_unverified_items: []
human_verification:
  - test: "Load a workspace with Python-emitted events in the CONSTRUCT Views SPA and visually confirm ActivityList.jsx renders agent/action/target/result instead of blank rows."
    expected: "Each row shows a non-blank agent and action; an escalated event shows the amber 'escalated' badge."
    why_human: "18-05's ActivityList.jsx change (D-17's reader-side conformance) has no JS toolchain in this environment to execute or type-check (`T-18-SC` forbids one). Verified by source review only (the component's destructured keys — `e.ts`/`e.agent`/`e.action`/`e.target`/`e.detail`/`e.result` — now match `parse_events.py`'s canonical output exactly), which the 18-05 SUMMARY itself flags with `human_judgment: true`; it was never exercised at runtime."
---

# Phase 18: Contract & Governance Foundations Verification Report

**Phase Goal:** Every contract a browser will depend on tells the truth before a browser exists — the views projection validates against its own validator, all invocation surfaces validate against one seam, and a human-review decision cannot be misapplied.
**Verified:** 2026-07-30T19:06:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

This phase went through code review (18-REVIEW.md: 5 critical, 13 warning findings) and a fix
pass scoped to critical findings only (18-REVIEW-FIX.md: 5/5 fixed, suite 734→765 passed). This
verification does not trust either document's claims — every fix below was re-reproduced
independently against the running code (fresh Python process, real registry, real CLI dispatch,
one live round-trip-guard mutation test), and every one of the 5 ROADMAP success criteria was
checked against the codebase rather than against the SUMMARYs' self-reports.

### Observable Truths (ROADMAP Phase 18 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `views validate` accepts every one of the 8 (really `4+6·N+1`) files `views generate` writes, proven by a non-vacuous round-trip guard replacing the pin test | ✓ VERIFIED | `tests/integration/test_views_generate.py::test_views_generate_output_round_trips_through_views_validate` passes on 1- and 2-workspace fixtures. Non-vacuity independently confirmed: temporarily renamed `CardRecord.title` → `card_title_renamed` in `views/models.py`; the guard failed with `Field required` on the renamed field; reverted, guard passed again. `test_views_validate_does_not_yet_accept_generated_bytes` was replaced, not deleted (git history: `18-05`). |
| 2 | Same capability id + payload → identical structured result across CLI and MCP, unknown field rejected on both — including the failure path | ✓ VERIFIED | `tests/integration/test_surface_parity.py` (22/22 pass), including `test_failure_parity_puts_the_capability_s_errors_on_both_surfaces` (CR-01's regression guard, drives the real CLI subprocess and the real MCP tool closure). `mcp/server.py`'s `_serialize_result` now uses `dataclasses.asdict` (recurses into `OperationError`); confirmed no capability-specific code remains in `mcp/server.py`. CLI structurally cannot deliver an undeclared field to a handler (Typer rejects at parse time) — the two halves are proven separately by design (D-08), not a gap. |
| 3 | A decision names its proposal; a resume against a changed queue is rejected with zero writes; a missing decision never falls back to applying a write | ✓ VERIFIED | `proposal_id`, id-keyed `_decision_map`/`_check_coverage`, and the checkpoint-id ETag are implemented in `curation_run.py` and mirrored in `research_run.py`. Live-reproduced: `apply_connections` (CR-02) is now default-deny — `if decision != "approve"` — confirmed by reading `curation_run.py:1339` (was `if decision == "reject"`). `test_stale_etag_rejected_with_zero_writes`, `test_etag_comparison_is_exact_string_equality`, `test_migrated_queue_requires_a_complete_map` all pass and assert workspace-state byte-identity across the rejection. |
| 4 | No surface writes canonical truth outside the reviewed workflow's resume path (D-13/D-14), and no approval event exists for a decision that was never applied (D-16) | ✓ VERIFIED | `src/construct/ui/gate_review.py` is deleted (`git log` confirms deletion commit `7c1f3a3`); `streamlit_app.py` has zero references. `test_no_canonical_writer_outside_the_apply_nodes` passes; `UNRESOLVED_DIRECT_CALLERS = {"pipelines/ingestion.py"}` is the sole, explicitly-named D-23 baseline and `test_guard_detects_a_planted_canonical_writer` proves the guard is shrink-only *in both directions* (fails on a newly planted writer, fails if a baseline entry stops being a real caller). Approval-event-implies-a-write is proven non-vacuously by 7 hand-constructed-queue tests (`test_idempotent_*_emits_no_approval_event`, `test_failed_*_write_emits_no_approval_event`) — distinct from the fixture-vacuous `test_reviewed_connection_idempotent` the fix report itself flags as a separate, lower-severity finding. D-24's research-graph deferral is honoured (untouched, tracked in `deferred-items.md`). |
| 5 | A degraded or partially-applied run reports degraded on every surface that can report it, and escalated items surface as pending rather than folded into a success count | ✗ **FAILED** | Holds for `curation.run` only (`test_surface_honesty.py`, 19/19 pass — but every row is curation-scoped). Live-reproduced failure on the other two run-composition surfaces: `daily.run` prints an unqualified `✓ Daily cycle degraded.`, and a completed-but-retrieval-degraded `research.run` prints `degraded: True` directly followed by an unqualified `✓ Run complete.` in the same block. This is review finding WR-02, deliberately left unfixed by the blockers-only fix pass. See Gaps below. |

**Score:** 4/5 roadmap success criteria verified (1 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/construct/capabilities/errors.py` | Typed seam errors, payload-order-independent multi-field reasons | ✓ VERIFIED | `CapabilityInputError.from_validation_error` now orders on the whole `loc` tuple (CR-05). Live-reproduced: two `workspace.init` payloads with reversed nested-dict key order now produce byte-identical reason strings. |
| `src/construct/capabilities/registry.py` | `invoke()` — the single validating seam | ✓ VERIFIED | `CapabilityRegistry.invoke` (`registry.py:47`) validates via `input_model.model_validate` then calls `handler(**model.model_dump())`. |
| `tests/integration/test_surface_parity.py` | Differential CLI-process vs MCP-dispatch harness | ✓ VERIFIED | 22 tests, real subprocess (`_cli`) + real MCP tool closure (`_mcp`), including the D-21 schema-gap pin and the CR-01 failure-parity regression test. |
| `src/construct/views/contracts.py` | One canonical path→model table shared by writer and validator | ✓ VERIFIED | `GLOBAL_FILE_CONTRACTS` / `PER_WORKSPACE_FILE_CONTRACTS` exported and consumed by both `generate.py` and the `views validate` capability; `grep` finds no third table. |
| `src/construct/views/models.py` | Conformed contract models, `extra="ignore"`, two new workspace-file models | ✓ VERIFIED | `WorkspaceStatsFile` present; `CardRecord`/`EventRecord`/etc. carry `extra="ignore"`; mutation test (above) proves the round-trip guard still catches a real drift. |
| `src/construct/llm/curation_run.py` | `proposal_id`, id-keyed resolution, checkpoint-id ETag, honest escalate/approval bucketing | ✓ VERIFIED | All present; `apply_connections` default-deny fix confirmed at `:1339`; escalation gets its own event action and bucket (`ESCALATED_EVENT_ACTION`, `escalated` list). |
| `tests/contract/test_canonical_write_boundary.py` | Repo-wide source guard for GOV-04 | ✓ VERIFIED (with carried debt) | Guard passes; shrink-only baseline behaviour proven. WR-05 (unfixed): `exemption_for` grants its `StateGraph(`/`interrupt(`/`CapabilityRecord(` exemptions by raw substring match over the whole source text (including comments), so a hostile module could in principle exempt itself with a comment. Not exploited by any module in the repo today — carried as review debt, not a proven violation. |
| `tests/integration/test_surface_honesty.py` | Table-driven degraded/escalated reporting across CLI human, CLI JSON, MCP | ⚠️ NARROWER THAN CLAIMED | 19/19 pass, but every row is a `curation.run` fixture. The plan-08 must-have text ("A degraded run reports degraded on the CLI human output...") reads as capability-agnostic; the test table is not. See Gap under criterion 5. |
| `src/construct/ui/streamlit_app.py` | Page list without the deleted gate-review page | ✓ VERIFIED | No `gate_review` reference remains; module imports cleanly (exercised indirectly by the full test run, 765 passed). |
| `CONSTRUCT-CLAUDE-impl/.../ActivityList.jsx` | Canonical event-shape reader | ✓ VERIFIED (source-level only) | Destructures `e.ts`/`e.agent`/`e.action`/`e.target`/`e.detail`/`e.result`, matching `parse_events.py`'s canonical output exactly. No JS toolchain available to execute — routed to Human Verification. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `src/construct/mcp/server.py` | `src/construct/capabilities/registry.py` | `make_handler` calls `registry.invoke` | ✓ WIRED | `mcp/server.py:52` calls `registry.invoke(capability.id, kwargs)`; no capability-specific branch anywhere in the 66-line file. |
| `src/construct/cli.py` | `src/construct/capabilities/registry.py` | every command dispatches through the seam | ✓ WIRED (one named exception) | `get_registry().invoke(...)` is the dominant pattern across `cli.py`. `construct init` (WR-01, carried debt) still calls `initialize_workspace(...)` directly rather than through `registry.invoke("workspace.init", ...)` — its input is still a validated Pydantic model (`DomainInitInput`), just not dispatched through the seam abstraction. Does not trip the AST guard (`X.handler(...)` only), and does not violate the letter of any of the 5 success criteria (the `workspace.init` capability remains invocable and differentially tested via MCP/tests), but is a real parity gap the review correctly flagged. |
| `src/construct/views/generate.py` | `src/construct/views/contracts.py` | validate-before-write iterates the shared contract table | ✓ WIRED | Confirmed by the round-trip guard's cardinality assertion passing and by the mutation test (renamed field caught at write-validation time, before any file changed). |
| `tests/contract/test_canonical_write_boundary.py` | `src/construct/` | repo-wide AST scan, not a hand-typed file list | ✓ WIRED | `unexempted_callers` walks the tree; `test_guard_detects_a_planted_canonical_writer` proves it reacts to a planted module rather than a fixed list. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Round-trip guard catches a renamed required field | rename `CardRecord.title`, run round-trip test, revert | `Field required` failure, then clean pass after revert | ✓ PASS |
| Nested-payload error ordering is payload-independent (CR-05) | `registry.invoke("workspace.init", {...domain with reversed key order...})` ×2 | Identical reason strings both orders | ✓ PASS |
| Workspace marker guard refuses a non-workspace path (CR-04) | `registry.invoke("knowledge.card.create", {"workspace": "/tmp/definitely-not-a-workspace-9x8/secret-dir", ...})` | `success=False`, "workspace is not an existing directory"; directory never created | ✓ PASS |
| Blank-field rejection on card edit (CR-03) | `CardEditInput(summary="")`, `CardEditInput(title="")`, `CardEditInput(summary="   ")` | All three raise `ValidationError` | ✓ PASS |
| `apply_connections` is default-deny (CR-02) | source read at `curation_run.py:1339` | `if decision != "approve": rejected...` | ✓ PASS (source-confirmed; also covered by 7+ passing unit tests) |
| MCP surface serializes a capability's structured errors, not a `TypeError` (CR-01) | `test_failure_parity_puts_the_capability_s_errors_on_both_surfaces` | Passes; `_serialize_result` uses `dataclasses.asdict` | ✓ PASS |
| **Degraded `daily.run` human output is honest** | `cli._emit_daily_result(OperationResult(success=True, message="Daily cycle degraded.", outcome="degraded"), json_output=False)` | Printed `✓ Daily cycle degraded.` — unqualified success glyph on a degraded outcome | ✗ **FAIL** |
| **Degraded (retrieval) `research.run` human output is honest** | `cli._emit_run_result(...data={"degraded": True, "status": "completed", ...}, outcome="completed")`, `json_output=False` | Printed `degraded: True` then unqualified `✓ Run complete.` in the same block | ✗ **FAIL** |
| Full test suite | `.venv/bin/python -m pytest -q` | `765 passed, 18 skipped, 0 failed` | ✓ PASS (necessary, not sufficient — the two failures above are on paths the suite doesn't exercise) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist in this repository and neither the PLANs nor the SUMMARYs reference any probe script. Skipped — no probes declared for this phase.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| VFIX-01 | 18-04, 18-05 | `views validate` accepts every file `views generate` writes | ✓ SATISFIED | Criterion 1 above. |
| GOV-01 | 18-01, 18-02, 18-03 | CLI, MCP (and HTTP, Phase 19) dispatch through one validating seam | ✓ SATISFIED (phase-scoped) | Criterion 2 above. REQUIREMENTS.md's own wording includes "and HTTP" — HTTP does not exist until Phase 19 by explicit ROADMAP design ("HTTP joins the same seam in Phase 19; it is not built here"), so full closure spans two phases; the Phase-18-owned portion (CLI+MCP) is fully verified. |
| GOV-02 | 18-06 | Decisions keyed by proposal id; missing decision never defaults to a write | ✓ SATISFIED | Criterion 3 above. |
| GOV-03 | 18-06 | Stale review queue detected and rejected | ✓ SATISFIED | Criterion 3 above (checkpoint-id ETag). |
| GOV-04 | 18-07, 18-08 | Gate-review screen routes through resume path; no orphan approval events | ✓ SATISFIED | Criterion 4 above. |
| GOV-05 | 18-08 | No surface reports success for a degraded/partial outcome | ✗ **BLOCKED** | Criterion 5 above — holds for `curation.run` only. |

No orphaned requirements: all 6 IDs (VFIX-01, GOV-01..05) are claimed by at least one plan's `requirements:` frontmatter and all 6 are mapped to Phase 18 in `REQUIREMENTS.md`'s traceability table.

**Documentation note (not a code gap, flagged for hygiene):** `REQUIREMENTS.md`'s top-level checklist currently shows `GOV-04` and `GOV-05` checked `[x]` and `GOV-01`/`GOV-02`/`GOV-03` unchecked `[ ]` — the inverse of the review's actual findings (GOV-01/02/03 are fully satisfied for their phase-18 scope; GOV-05 is not satisfied). This checklist should be corrected once GOV-05's gap is closed, not left to imply a stronger guarantee than the code currently provides.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any of the phase's modified files. One dishonesty anti-pattern found and reported above (unqualified `✓` on a degraded outcome in `_emit_run_result`/`_emit_daily_result`) — this is the T-15-14 "audit-trail-that-lies" class the phase exists to eliminate, surviving in exactly the two composition surfaces the blockers-only fix pass did not reach.

### Human Verification Required

1. **ActivityList.jsx renders live Python-emitted events correctly** — see frontmatter `human_verification`. Source-level conformance to the canonical event shape is confirmed by reading the code; runtime behavior was never exercised (no JS toolchain in this environment, and this was explicitly out of scope per `T-18-SC`).

### Gaps Summary

Of the phase's 5 ROADMAP success criteria, 4 are genuinely and non-vacuously achieved — including
the two (criteria 1 and 3) that plausibly could have been vacuous and were specifically stress-tested
here (a live mutation of the round-trip guard's target model, and reading the actual `apply_connections`
default-deny fix rather than trusting the fix report's prose).

**Criterion 5 fails.** GOV-05's honest-verdict rendering was applied to `curation.run` only
(`cli._emit_curation_result` uses `_verdict_line`); `research.run`/`research.review`/`research.inspect`
(`_emit_run_result`) and `daily.run` (`_emit_daily_result`) still print an unqualified `✓ {message}`
regardless of a non-clean `outcome`. This was found and named by the phase's own code review as WR-02,
and left unfixed by design — the fix pass was explicitly scoped to the 5 Critical findings only, and
WR-02 is a Warning. But WR-02 is not merely stylistic debt: it is a live violation of the phase's own
fifth success criterion ("reports degraded on **every** surface that can report it"), and this
verification reproduced it directly against running code on both remaining composition surfaces —
`daily run`, whose degraded status is reachable any time an escalation is pending or a child run
degrades (not a rare edge), and `research run`, whose retrieval-degraded flag can coexist with a
`"completed"` status. The `--json` and MCP structured payloads are unaffected (the `outcome`/`degraded`
fields ride on the envelope honestly); only the plain-text human renderer is dishonest.

**Suggested fix (small, scoped):** replace the two remaining `typer.echo(f"✓ {result.message}")`
call sites in `cli.py` (`_emit_run_result`, `_emit_daily_result`) with `_verdict_line(result)` — the
same one-line change `_emit_curation_result` already received — and add a `daily.run` degraded row
and a `research.run` completed-but-degraded row to `tests/integration/test_surface_honesty.py`'s
table. This is materially smaller than any of the five Critical fixes already completed in this phase.

---

_Verified: 2026-07-30T19:06:00Z_
_Verifier: Claude (gsd-verifier)_
