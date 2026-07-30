---
phase: 18-contract-governance-foundations
plan: 08
subsystem: surface-honesty
tags: [langgraph, audit-log, cli, mcp, pydantic, dataclass, table-driven-test, gov-05]

# Dependency graph
requires:
  - phase: 18-06
    provides: the id-keyed decision map and checkpoint ETag the reviewed runs under test resume through
  - phase: 18-07
    provides: the canonical-write boundary guard these apply-node changes must not trip, and the surviving gate_review_* action strings whose emission this plan makes conditional
  - phase: 18-03
    provides: the registry.invoke seam both structured surfaces dispatch through
provides:
  - "CurationRunResult.applied / no_op / escalated / rejected / failed_writes — five mutually exclusive outcome buckets, applied being the only one behind which a canonical write happened"
  - "curation_run.ESCALATED_EVENT_ACTION ('curation_escalated') and ESCALATED_LABEL ('flagged — nothing written')"
  - "_emit gains a result parameter so an event can carry EventResult.escalated"
  - "_connection_key_set — the connection analogue of _card_lifecycle_map, so a dedup is told from a write by workspace state rather than by a message string"
  - "OperationResult.outcome — 'how it went', decoupled from the success flag that means 'the command ran'"
  - "cli._verdict_line — the shared qualified-verdict renderer"
  - "tests/integration/test_surface_honesty.py — the three-row cross-surface table Phase 19's HTTP surface joins by adding a row"
affects: [phase-19-http-surface, phase-22-review-wizards, daily-run, cli, mcp, views-events-projection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two orthogonal answers on one envelope: success = 'the command ran' (drives the exit code), outcome = 'how it went'"
    - "Outcome buckets that partition items by what actually happened, with exactly one bucket meaning a write occurred"
    - "Audit events emitted inside the branch that succeeded, never after the branch block"
    - "Cross-surface table tests asserting rendered output, so a new surface joins by adding a row"

key-files:
  created:
    - tests/integration/test_surface_honesty.py
  modified:
    - src/construct/llm/curation_run.py
    - src/construct/services/knowledge.py
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/llm/test_curation_run.py
    - .planning/phases/18-contract-governance-foundations/deferred-items.md
    - .planning/WINDOWS.md

key-decisions:
  - "The escalate action name is 'curation_escalated' — not chosen here but already pinned by plan 05's test_unseen_action_string_needs_no_model_change, so the projection contract and the emitter agree by construction"
  - "applied is DERIVED from the three existing write channels rather than accumulated in a fourth, so an item can be recorded as written in exactly one place and the two cannot disagree"
  - "apply_connections decides no-op-vs-write by reading the edge set inside the node, because add_connection's dedup returns success=True with only a message string to distinguish it — matching on that string would have made the invariant depend on prose"
  - "Empty outcome buckets render nothing at all, which is what keeps a clean run's human output byte-identical while still reporting zero applied and zero escalated in the structured payloads"
  - "The research graph's approval-without-a-write instance was surfaced, not fixed: it is outside Task 2's declared files and D-16's three enumerated sites, and an honest fix needs assertions in a test file this plan does not own"

patterns-established:
  - "A preservation guard is committed GREEN against the unchanged code before the change it protects against, so git history proves it predates the risk"
  - "A human-output snapshot masks only environment-derived content, leaving every renderer decision (line order, prefixes, verdict glyph) literal"

requirements-completed: [GOV-04, GOV-05]

coverage:
  - id: D1
    description: "An escalated proposal emits its own event action carrying the escalated result member, never a rejection, and reaches the run result in its own bucket"
    requirement: GOV-05
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_escalated_emits_its_own_action_not_a_rejection"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_escalated_bucket_reaches_the_run_result"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_missing_target_lifecycle_escalates_rather_than_rejects"
        status: pass
      - kind: unit
        ref: "tests/contract/test_views_contracts.py#TestCanonicalEventContract::test_unseen_action_string_needs_no_model_change"
        status: pass
    human_judgment: false
  - id: D2
    description: "Escalated items are counted in their own bucket, in queue order, and never folded into an applied or success count"
    requirement: GOV-05
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_escalated_and_applied_are_counted_separately"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_escalated_bucket_preserves_queue_order"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_applied_and_escalated_are_two_counts_never_their_sum"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_escalated_bucket_appears_in_queue_order_on_every_surface"
        status: pass
    human_judgment: false
  - id: D3
    description: "An approval event is emitted only when a canonical write actually happened — not for an idempotent no-op, not for a failed write — in all three apply nodes, with the count invariant asserted against the on-disk event log"
    requirement: GOV-04
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_approval_event_count_equals_applied_count"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_idempotent_promotion_emits_no_approval_event"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_failed_promotion_write_emits_no_approval_event"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_idempotent_connection_emits_no_approval_event"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_failed_connection_write_emits_no_approval_event"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_idempotent_archive_emits_no_approval_event"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_failed_archive_write_emits_no_approval_event"
        status: pass
    human_judgment: false
  - id: D4
    description: "A degraded run reports degraded on the CLI human output, in the CLI JSON payload and in the MCP result, proven by a table-driven test asserting rendered output with one row per surface"
    requirement: GOV-05
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_degraded_reads_as_degraded_on_every_surface[cli-human|cli-json|mcp]"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_degraded_human_output_has_no_unqualified_success_verdict"
        status: pass
    human_judgment: false
  - id: D5
    description: "A degraded curation.run still exits 0 — the Phase 11 contract is preserved, not changed (D-15)"
    requirement: GOV-05
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_degraded_curation_run_exits_zero"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_degraded_curation_run_json_exits_zero"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_completed_curation_run_exits_zero"
        status: pass
    human_judgment: false
  - id: D6
    description: "A run with zero proposals reports completed with zero applied and zero escalated and no degraded warning; a completed run's human output is unchanged from before this plan"
    requirement: GOV-05
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_empty_run_reports_zero_applied_and_zero_escalated[cli-human|cli-json|mcp]"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_completed_run_human_output_is_unchanged"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_honesty.py#test_completed_run_still_renders_a_clean_success_verdict"
        status: pass
    human_judgment: false
  - id: D7
    description: "Whether criterion 4's second half was meant to span the research graph as well as the curation graph — research_run emits gate_review_approved from the decision, while ingest_batch separately tracks refs/cards that already existed and were not written"
    requirement: GOV-04
    verification: []
    human_judgment: true
    rationale: "No test can decide the scoping question. The curation half is proven by the event-count invariant; the research instance is out of Task 2's declared files and outside D-16's three enumerated sites, and is filed in deferred-items.md and WINDOWS.md rather than fixed silently. A verifier must either accept the curation scoping (as D-23 did for GOV-04's ingestion finding) or open a follow-up."

# Metrics
duration: 22 min
completed: 2026-07-30
status: complete
---

# Phase 18 Plan 08: Surface Honesty Summary

**Three surfaces stopped reporting outcomes that did not happen: escalation is no longer logged as a rejection nor folded into a success count, an approval event now follows only a write that actually occurred, and a degraded run reads as degraded on the CLI, in `--json` and over MCP — while still exiting 0.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-30T17:00Z
- **Completed:** 2026-07-30T17:22Z
- **Tasks:** 3 (each RED → GREEN)
- **Files modified:** 7 (1 test file created, 4 source files, 1 test file extended, 2 planning artifacts)

## The three defects this closes

Each is an instance of the T-15-14 *audit-trail-that-lies* class this codebase already names.

| # | Defect | Where it lived |
|---|---|---|
| 1 | An escalated proposal — which writes nothing — was logged as `gate_review_rejected`. A rejection is a decision the reviewer made; an escalation is the absence of one. The audit trail recorded a decision nobody took, about an item nothing happened to. Escalated items also reached **no result surface at all**. | `apply_promotions`, both escalate branches |
| 2 | `gate_review_approved` sat *after* the whole three-branch write block, so it fired identically on a real write, on an idempotent no-op, and on a failed write. The approval count in `log/events.jsonl` was unrelated to the write count. | `apply_promotions:872`, `apply_connections:923`, `apply_archives:968` |
| 3 | The result model was honest (`status: degraded`) and the per-step renderer printed it — and then the next line printed `✓ Curation run degraded.` In `--json` and over MCP the outcome was flattened away entirely into a bare `success: true`. | `cli._emit_curation_result`, `cli._display_result`, the three catalog adapters |

## Task commits

| # | Task | RED | GREEN |
|---|---|---|---|
| 1 | Escalation gets its own event action and its own bucket | `ee3ce2a` (5 failed) | `47b6652` |
| 2 | An approval event only follows a write that happened | `993bcb2` (7 failed) | `b0b5420` |
| 3 | Degraded reads as degraded everywhere; exit codes pinned | `4367367` (guard, GREEN pre-change) + `bfa741f` (8 failed) | `d685915` |
| — | Deferred finding recorded | — | `bd174cf` |

## The new escalate event action

```
action:  curation_escalated
result:  EventResult.escalated
detail:  "flagged — nothing written"   (or "… (no target lifecycle)")
agent:   curator            (unchanged — routed through the existing _emit helper)
```

The name was **not chosen freshly here**: plan 05 had already pinned it in
`tests/contract/test_views_contracts.py::test_unseen_action_string_needs_no_model_change`, which
asserts `EventRecord.model_validate({..., "action": "curation_escalated"})` succeeds. Using any
other string would have left that test asserting a name nothing emits. `EventResult.escalated`
likewise already existed in the emitter enum (`schemas/config.py:351`) and simply had no caller —
so this outcome had a home in the audit vocabulary the whole time.

`_emit` gained a `result` parameter to carry it, so the new action still goes through
`append_event`, the shared `EventRecord`, and the same non-blocking write path as every other
event the graph produces. Nothing routes around the helper.

## The five outcome buckets

`CurationRunResult` gained a partition of every reviewed proposal by **what actually happened to
it**, replacing a surface on which "changed", "already in that state", "flagged and left alone"
and "the write failed" all arrived as the same silence:

| Bucket | Meaning | Write happened? |
|---|---|---|
| `applied` | a canonical write occurred | **yes — and only here** |
| `no_op` | already in the requested state | no |
| `escalated` | flagged for follow-up (D-16) | no |
| `rejected` | the reviewer declined | no |
| `failed_writes` | `"<item> — <sanitized reason>"` | no (attempted) |

`applied` is **derived** from the three existing write channels (`promoted` + `connections_added`
+ `archived`) rather than accumulated in a fourth, so an item can be recorded as written in
exactly one place and the two can never disagree. `no_op` and `failed_writes` are new
`operator.add` channels because all three apply nodes contribute to them. Every bucket preserves
queue order.

## Before / after — the human output

**A completed run: byte-identical.** Verified by `test_completed_run_human_output_is_unchanged`,
which snapshots the real pre-change CLI output and masks only environment-derived fragments (run
id, per-step summaries, event list) — every renderer decision is literal in the snapshot.

```
status: completed
run_id: cur-…
  - integrity_check: completed — 0 error(s), 0 warning(s)
  …
events: workflow_step_complete, …, curation_cycle_complete, workflow_step_complete
✓ Curation run completed.                     ← unchanged
```

**A degraded run:**

```diff
 status: degraded
 run_id: cur-…
   - connection_maintenance: failed — injected required-step failure
   …
-✓ Curation run degraded.
+⚠ degraded: Curation run degraded.
```

Exit code **0 before and 0 after**.

**A degraded run, `--json`:**

```diff
 {
   "success": true,
+  "outcome": "degraded",
   "message": "Curation run degraded.",
   "data": { "status": "degraded", "applied": [], "no_op": [], "escalated": [], … }
 }
```

`success` stays `true` — it means "the command ran" and drives the exit code, and D-15 holds it
fixed. `outcome` is where "how it went" is now said.

**A reviewed run carrying escalated items** (new; previously escalation reached no renderer):

```
applied: 1
  · applied-card
escalated (flagged — nothing written): 3
  · stale-connected-card
  · fresh-card
  · stale-orphan-card
```

Two separate counts. No surface prints `4`.

## D-15 fail-first evidence

D-15 is a **preservation** constraint, so the honest evidence is the inverse of a normal red/green:
the guard must be observed **passing against the unchanged code**, and committed before the change
it protects against exists.

| Run | Command | Result |
|---|---|---|
| **Pre-change** (commit `4367367`, before any renderer edit) | `pytest tests/integration/test_surface_honesty.py -q` | **4 passed** — the three exit-code assertions and the completed-run snapshot, against the original renderers |
| **Post-change** (commit `d685915`) | `pytest tests/integration/test_surface_honesty.py -q` | **19 passed** — the same four still green |

Git history therefore shows the guard predating the risk. The mechanism keeping it true is
structural, not incidental: `OperationResult.success` computation is untouched in all three
adapters, and `_emit_curation_result` still returns without raising on every branch where the
command ran.

The honesty tests themselves were observed RED in the normal way: **8 failed / 11 passed** at
`bfa741f`, including `KeyError: 'outcome'` on both structured surfaces and
`degraded run rendered an unqualified success verdict: '✓ Curation run degraded.'` on the human one.

## The surface table

`tests/integration/test_surface_honesty.py` drives **three real surfaces**, not three mocks:

| Row | Path exercised |
|---|---|
| `cli-human` | `typer.testing.CliRunner` → the real Typer command → stdout a person reads |
| `cli-json` | the same command with `--json` → the payload a script parses |
| `mcp` | `registry.invoke(...)` → `mcp/server.py:_serialize_result` — the exact function the generated stdio tool calls |

Phase 19's HTTP surface joins by appending one entry to `SURFACES`; the parametrised tests pick it
up with no other edit. Every assertion reads **rendered output**, never the result model — a
result-model assertion would have passed against the broken code, which is exactly why D-16 asked
for this shape.

## MCP needed no change

`_serialize_result` enumerates `__dataclass_fields__` generically, so `OperationResult.outcome`
rides along with **zero** capability-specific wiring. `tests/contract/test_curation_run_cli_mcp.py::test_mcp_no_hardcoded_curation`
(the guard proving the server is never hand-edited for a capability) stays green, as does
`test_cli_mcp_schema_parity` — `outcome` was added to `_display_result`'s JSON key set in the same
commit, so the two surfaces' envelopes stay identical.

## Deviations from Plan

### 1. [Rule 1 - Bug, in my own test] The sum-check matched a step summary, not a bucket

- **Found during:** Task 3, first GREEN run (18/19 passed).
- **Issue:** `test_applied_and_escalated_are_two_counts_never_their_sum[cli-human]` asserted
  `"4" not in output`. The fixture workspace legitimately renders `4 decay candidate(s)` and
  `4 orphan candidate(s)` in unrelated step summaries, so the assertion failed on correct output.
- **Fix:** added `_bucket_counts()`, which parses only the `<label>: <count>` lines whose label is
  one the CLI itself declares in `_CURATION_BUCKETS`. The test now asserts `applied == 1`,
  `escalated == 3`, and that no bucket reports 4 — strictly stronger than the original string
  check, and immune to numbers appearing in prose.
- **Files modified:** `tests/integration/test_surface_honesty.py`
- **Commit:** `d685915`

### 2. [Rule 4 - Scope, surfaced not fixed] The research graph has the same approval-without-a-write defect

- **Found during:** Task 1, checking the plan's conditional clause *"give the research graph's gate
  the same treatment **if it has an escalate path**"*.
- **The clause itself is inapplicable:** `grep -c 'escalat' src/construct/llm/research_run.py`
  returns **0**. There is no escalate path in the research graph, so no change was required for
  the escalate half, and `research_run.py` is correctly left untouched.
- **But the check turned up its sibling defect:** `update_seeds_and_log` (`research_run.py:919-932`)
  emits `gate_review_approved` for every finding whose **decision** is in `_INGEST_ACTIONS`, while
  `ingest_batch` (`:584-615`) separately tracks `skipped_existing` for refs and cards that already
  existed and were therefore **not written**. An idempotent research re-run records approvals for
  ingests that did not happen — the T-18-06 class, in the other graph.
- **Why it was not fixed here:** Task 2's declared `<files>` are `curation_run.py` and
  `tests/llm/test_curation_run.py`; its `<action>` says "in all three apply nodes", meaning
  curation's three; D-16 enumerates exactly three sites, all in `curation_run.py`. An honest fix
  needs assertions in `tests/llm/test_research_run.py`, which this plan does not own and which
  18-06 records as recently contended. Fixing it untested, or silently, would be worse than naming
  it.
- **How it is tracked instead:** `deferred-items.md` item 3 and `.planning/WINDOWS.md` entry 2.
- **Decision needed from:** phase verification — accept the curation scoping (as D-23 did for
  GOV-04's ingestion finding) or open a follow-up. Recorded as coverage item D7 with
  `human_judgment: true` so it abstains at verify time rather than passing silently.
- **Commit:** `bd174cf`

**Total deviations:** 2 (1 auto-fixed test bug, 1 scope finding surfaced and tracked).
**Impact on plan:** all three tasks shipped complete; no scope creep into modules this plan does
not own.

## Issues Encountered

- **No `.venv` inside the git worktree** (same as 18-07). All runs used
  `/Users/mab/dev/mabstruct/construct/.venv/bin/python` from the worktree root, with pytest's
  `pythonpath = [".", "src"]` resolving to the **worktree's** source tree — verified explicitly.
  A bare `python -c "import construct"` **does not**: it resolves the main checkout and silently
  reported `'escalated' in CurationRunResult.model_fields` → `False` while the same check under
  pytest returned `True`. Every acceptance-criteria one-liner in this SUMMARY was therefore run
  with `PYTHONPATH=src`. Worth knowing for anyone re-running the plan's criteria from a worktree.
- **`add_connection`'s dedup is indistinguishable from a write in its return value** — it returns
  `success=True, message="Connection already exists"`, with the message string as the only
  discriminator. Deciding the event-count invariant on a prose match would have made the invariant
  depend on wording. `_connection_key_set` reads the edge set inside the node instead, which is
  both the honest answer and symmetric with the lifecycle comparison `apply_promotions` and
  `apply_archives` already make.
- **Two pre-existing suite failures, unrelated and environmental** — the same
  `test_workspace_contract_migration.py::TestFixtureRoot::*` `digests/` fixture failures 18-07
  documented. They reproduce on the base commit; out of scope; already in `deferred-items.md`.

## Verification

| Check | Result |
|---|---|
| `pytest tests/integration/test_surface_honesty.py -x -q` | **19 passed** (≥8 required) |
| `pytest tests/llm/test_curation_run.py -x -q` | **51 passed** (39 before this plan, +12) |
| `pytest tests/contract/test_views_contracts.py -k events -x -q` | **passed** — the new action validates in the projection with no model change |
| `pytest tests/contract/test_canonical_write_boundary.py -x -q` | **5 passed** — Plan 07's guard untripped |
| `pytest tests/integration/test_surface_parity.py -x -q` | **passed** — the outcome field did not fork the two surfaces |
| `pytest tests/contract/test_curation_run_cli_mcp.py -x -q` | **passed** — CLI/MCP envelope keys still identical |
| `PYTHONPATH=src python -c "'escalated' in CurationRunResult.model_fields"` | **True** |
| `grep -Ec 'subprocess\|CliRunner' tests/integration/test_surface_honesty.py` | **2** (≥1 required) |
| `grep -c 'create_server\|_serialize_result' tests/integration/test_surface_honesty.py` | **3** (≥1 required) |
| `grep -c 'apply_connections\|apply_archives' tests/llm/test_curation_run.py` | **5** (≥2 required) |
| A degraded run exits 0, guard written and observed passing before the renderer change | **yes** — 4 passed at `4367367`, before any renderer edit |
| Approval events == applied items on a mixed run | **yes** — `test_approval_event_count_equals_applied_count`, read from `log/events.jsonl` on disk |
| `pytest -q` (full suite) | **728 passed, 22 skipped, 2 failed** — the 2 are the pre-existing `digests/` fixture failures (697 passed on the base commit; **+31 net new tests**) |

## Requirements

`requirements.ready-ids` reported **GOV-04 and GOV-05 both ready** (no other plan declares them
without a SUMMARY). Both are marked complete in `REQUIREMENTS.md`:

- **GOV-05 met** — no surface reports success for a degraded or partially-applied outcome, and
  escalated items surface as flagged rather than folded into a success count.
- **GOV-04 met** — its first half by 18-07 (no surface writes canonical truth outside the resume
  path, source-guarded); its second half here (no approval event exists for a decision that was
  never applied, in the curation graph, proven by the event-count invariant). The research-graph
  scoping question is recorded as D7 and in the deferred items.

## Known Stubs

None. Escalation still writes nothing — but that is D-16's deliberate scope ("this plan makes
escalation honest about writing nothing; it does not make it write something"), it is now named
for exactly that on every surface, and giving escalate a real write path is recorded in the
phase's deferred ideas as new capability rather than a Phase 18 repair.

## Threat Flags

None. No new network endpoint, auth path or file-access pattern. `OperationResult.outcome` is
populated only from a closed set of internally-computed run statuses, never from caller input;
`failed_writes` entries pass through `_safe_reason` (first line of an already-sanitized service
message) or `_sanitize_error` (class name + first line), preserving T-18-32.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 19's HTTP surface** joins `SURFACES` in `tests/integration/test_surface_honesty.py` by
  adding one row, and gets `outcome` on the envelope for free — the field is on `OperationResult`,
  not on any surface's serializer.
- **Phase 22's review wizards** can render the five outcome buckets directly; they are on the
  result model in queue order, identical across CLI, JSON and MCP.
- **`curation_escalated`** now appears in real `log/events.jsonl` files. The views `events.json`
  projection accepts it with no model change (`action` is a free string, pinned by D-17's contract
  test), but any SPA view that switches on action strings should learn the new one.
- **Open question carried forward:** the research graph's approval-without-a-write instance
  (`deferred-items.md` item 3, `WINDOWS.md` entry 2). Whoever verifies this phase should decide
  whether criterion 4's second half was scoped to the curation graph.

## Self-Check: PASSED

- `tests/integration/test_surface_honesty.py` — FOUND
- `src/construct/llm/curation_run.py`, `src/construct/services/knowledge.py`,
  `src/construct/capabilities/catalog.py`, `src/construct/cli.py` — FOUND, all modified
- `tests/llm/test_curation_run.py` — FOUND, extended by 12 tests
- `.planning/phases/18-contract-governance-foundations/deferred-items.md`, `.planning/WINDOWS.md` — FOUND, both updated
- Commits `ee3ce2a`, `47b6652`, `993bcb2`, `b0b5420`, `4367367`, `bfa741f`, `d685915`, `bd174cf` — all present on the worktree branch
- Every task's `<acceptance_criteria>` was re-run and logged in the Verification table above; no
  unmet item, with the single documented exception of the two pre-existing environmental failures
  that reproduce on the base commit.

---
*Phase: 18-contract-governance-foundations*
*Completed: 2026-07-30*
