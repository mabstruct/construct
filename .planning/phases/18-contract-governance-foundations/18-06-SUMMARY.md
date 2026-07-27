---
phase: 18-contract-governance-foundations
plan: 06
subsystem: workflow-governance
tags: [langgraph, checkpoints, human-in-the-loop, etag, uuid4, pydantic, sqlite]

requires:
  - phase: 18-contract-governance-foundations (plan 04)
    provides: the reviewed-write apply nodes whose decision payload this plan re-shapes
  - phase: 12
    provides: the consolidated curation review gate and its three queue producers
  - phase: 10
    provides: the durable research.run interrupt/resume machine
provides:
  - "CurationProposal.proposal_id / GateQueueEntry.proposal_id — an opaque 32-char uuid4 hex minted at enqueue and persisted into .construct/workflow/*.sqlite"
  - "_validate_proposal_id — the identifier guard for a caller-supplied proposal id (T-18-08)"
  - "IncompleteDecisionMap and StaleQueue — the two typed review rejections both graphs return"
  - "checkpoint_id on CurationRunResult / RunResult (returned) and on CurationReviewInput / ReviewInput (required)"
  - "migrate-on-read for runs paused before this phase, deterministic and write-free"
  - "_wrap_resume/_unwrap_resume — the resume transport envelope that keeps a uuid4-hex-keyed map from being eaten by LangGraph's interrupt-id mapping"
affects: [phase-19-api, phase-22-review-wizards, daily-run, cli, mcp]

tech-stack:
  added: []
  patterns:
    - "Opaque id-keyed human-review decisions with all-or-nothing coverage"
    - "LangGraph checkpoint_id as an ETag for optimistic concurrency on a paused run"
    - "Migrate-on-read at the raw-dictionary stage, before forbid-extra model validation"

key-files:
  created: []
  modified:
    - src/construct/llm/curation_run.py
    - src/construct/llm/research_run.py
    - src/construct/llm/daily_run.py
    - src/construct/cli.py
    - tests/llm/test_curation_run.py
    - tests/llm/test_views_refresh.py

key-decisions:
  - "Proposal id form is uuid4-hex (full 32 chars, never truncated), persisted as proposal_id, resume payload is a map from id to a bare decision string — settled by the user at a blocking checkpoint"
  - "Migration of pre-Phase-18 queues uses a deterministic uuid5(namespace, run_id:index) so it can be write-free; persisting it would advance the very checkpoint the D-11 ETag depends on"
  - "research_run imports the proposal-identity and coverage primitives from curation_run rather than re-declaring them, so the two graphs cannot fork again"
  - "The decision map crosses Command(resume=...) inside a one-element list envelope, because LangGraph reads a bare dict as an interrupt-id mapping and a uuid4 hex is exactly an interrupt id's shape"
  - "Typed rejections are raised internally and converted to status=failed results at the entry point, so the CLI/MCP surface still names the offending ids instead of a bare class name"

patterns-established:
  - "Coverage and staleness are checked at the review entry point, never inside a graph node, because a node-raised error still advances the checkpoint"
  - "Blanket approve/reject expand into a complete map so they satisfy the coverage check instead of bypassing it"
  - "Apply nodes consume paired (proposal, decision) tuples; no index arithmetic survives anywhere in the write path"

requirements-completed: [GOV-02, GOV-03]

coverage:
  - id: D1
    description: "Every queued proposal carries a stable opaque id assigned at enqueue and persisted in the checkpoint; identical proposals get different ids and a non-opaque id is rejected by the identifier guard"
    requirement: GOV-02
    verification:
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_proposal_id_is_opaque_and_unique"
        status: pass
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_proposal_id_rejects_non_opaque_values"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_proposal_id_survives_pause_and_reload"
        status: pass
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_research_gate_entries_carry_the_same_shape"
        status: pass
    human_judgment: false
  - id: D2
    description: "A run paused before this phase is migrated on read: its queue gains stable ids, no decision is carried over, nothing is written back to the checkpoint, and it still requires a complete id-keyed map to resume"
    requirement: GOV-02
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_legacy_checkpoint_migrated_on_read"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_migrated_queue_requires_a_complete_map"
        status: pass
    human_judgment: false
  - id: D3
    description: "Decisions are keyed by proposal id; a map that does not cover the queue exactly is rejected in full with zero canonical writes, and a resume carrying no decisions never falls back to the gate's own recommendation"
    requirement: GOV-02
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_complete_decision_map_is_applied"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_incomplete_decision_map_rejected_in_full"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_unknown_decision_id_rejected_in_full"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_resume_with_no_decisions_is_rejected"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_legacy_positional_payload_is_rejected"
        status: pass
    human_judgment: false
  - id: D4
    description: "Blanket approve/reject expand into a complete map rather than bypassing the coverage check, and the outcome does not depend on decision-map key order"
    requirement: GOV-02
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_blanket_flags_expand_into_a_complete_map"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_decision_key_order_does_not_change_the_outcome"
        status: pass
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_empty_queue_with_empty_map_resolves_cleanly"
        status: pass
    human_judgment: false
  - id: D5
    description: "research_run's url-keyed decision mode is removed outright, not kept as a compatible alternative"
    requirement: GOV-02
    verification:
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_research_url_keyed_decision_mode_is_gone"
        status: pass
      - kind: other
        ref: "grep -c 'url' src/construct/llm/research_run.py -> 18 (was 21); grep -c by_url -> 0"
        status: pass
    human_judgment: false
  - id: D6
    description: "The checkpoint id is returned as an ETag alongside the queue and required on resume; exact-equality comparison rejects near misses and a replayed resume, always with zero writes"
    requirement: GOV-03
    verification:
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_inspect_returns_the_checkpoint_id_etag"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_resume_with_current_etag_proceeds"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_stale_etag_rejected_with_zero_writes"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_etag_comparison_is_exact_string_equality"
        status: pass
      - kind: integration
        ref: "tests/llm/test_curation_run.py#test_replayed_resume_is_rejected_as_stale_etag"
        status: pass
    human_judgment: false
  - id: D7
    description: "The checkpoint concurrency contract (WAL, busy timeouts, locking) stays Phase 19's — this phase adds none of it"
    verification:
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_concurrency_configuration_stays_phase_19s"
        status: pass
    human_judgment: false
  - id: D8
    description: "Two callers resuming the same paused run cannot both apply their decisions (the second holds a pre-resume ETag); genuine sqlite lock contention under parallel access is NOT guaranteed by this phase"
    verification: []
    human_judgment: true
    rationale: "Authored as a backstop truth in the plan. The single-process replay case is proven by test_replayed_resume_is_rejected_as_stale_etag, but genuine concurrent multi-process access is Phase 19's contract (OQ-4, T-18-26 transferred). This must abstain at verify time rather than pass silently."
  - id: D9
    description: "The human-facing review surface (CLI --checkpoint-id workflow: inspect --json, then review with the id and an id-keyed decisions file) is usable end to end"
    verification:
      - kind: manual_procedural
        ref: "construct curation review --help (renders the required --checkpoint-id option and the {\"proposal_id\": \"decision\"} payload shape)"
        status: pass
    human_judgment: true
    rationale: "The CLI now requires the operator to read an ETag from one command and pass it to another. Whether that two-step flow is acceptable ergonomics before Phase 22's wizards land is a judgment call no test makes."

duration: 1h 05m
completed: 2026-07-27
status: complete
---

# Phase 18 Plan 06: Id-Keyed Review Decisions and the Checkpoint ETag Summary

Human-review decisions now name the proposal they apply to by an opaque `uuid4().hex` id, an incomplete decision map rejects the whole resume instead of silently writing the gate's own recommendation, and a queue that moved between render and submit is detected by exact comparison of LangGraph's `checkpoint_id`.

## The defect this closes

`_resolve_decisions` zipped the resume payload against `gate_queue` **positionally** and, whenever the payload was short or absent, fell back to `entry.get("decision", "")` — the gate's own recommendation. A truncated, misaligned, or entirely missing payload therefore performed a canonical write the user never approved. `research_run`'s version carried three decision shapes in one function, one of them keyed on a finding `url` that can be `None` and is not unique across findings.

Both are gone. The positional zip is deleted, the `None → default` fallback is deleted, and the url-keyed branch is removed rather than deprecated.

## Accomplishments

- **Opaque proposal identity.** `CurationProposal.proposal_id` and `GateQueueEntry.proposal_id` are the full 32-character `uuid4().hex`, minted by a `default_factory` that fires when a producer *constructs* the proposal — i.e. at enqueue, so a proposal that is never read still gets a name. `_validate_proposal_id` reuses the `_validate_run_id` identifier-guard pattern (T-18-08); the `ValueError` names a valid example per the AGENTS.md convention. **These ids are now persisted in `.construct/workflow/*.sqlite`** and are the contract Phase 19's API and Phase 22's wizards will be built against.
- **Migrate-on-read for already-paused runs.** `_ensure_proposal_ids` injects ids at the raw-dictionary stage, before any model validation, so the forbid-extra model never sees an id-less proposal (T-18-25). Migration restores the queue and *no* decision.
- **Complete-coverage rejection.** `_check_coverage` raises `IncompleteDecisionMap` naming both the uncovered and the unknown ids, at the review entry point, **before** `Command(resume=…)` — never inside a node, because a node-raised error still advances the checkpoint.
- **One shape across both graphs.** `research_run` imports the identity, coverage, and transport primitives from `curation_run` instead of re-declaring them.
- **Checkpoint-id ETag.** Returned alongside the queue by run/inspect/review, required on both review inputs, compared by exact string equality, evaluated *before* the coverage check.
- **No concurrency configuration added.** `grep -c 'busy_timeout\|WAL\|journal_mode'` returns 0 in both modules; T-18-26 stays transferred to Phase 19 (OQ-4).

## Checkpoint decision (settled by the user, blocking)

The plan's first task was a blocking `checkpoint:decision` on the one-way door: the concrete id form, its persisted field name, and the resume payload shape. The user selected:

| Question | Answer |
|---|---|
| Id form | **`uuid4-hex`** — `uuid.uuid4().hex`, the **full 32 characters**, never truncated |
| Persisted field | **`proposal_id`** |
| Resume payload | a map from proposal id to a **bare decision string**, `{proposal_id: "approved" \| …}`, replacing the positional list |
| Queue order | lives in the queue list **only** — never encoded in, or inferred from, the id |

**Rationale to preserve:** uniqueness spans runs as well as queues, so a decision payload cannot be replayed against a *different* run by accident. That is the property neither alternative had. The bare-string map value is the smallest contract that fixes the defect; if Phase 22 later needs a reviewer note or timestamp, that is an additive change to a map value rather than a reshape, so no room was pre-built for it.

**Rejected alternatives:**

- **`run-scoped-counter`** — rejected because it carries queue position inside the id, inviting exactly the positional reasoning GOV-02 exists to remove.
- **`uuid4-hex-short` (12 chars)** — rejected because it reintroduces the collision reasoning D-09 wanted removed, in exchange for ergonomics Phase 22 can solve in the UI.

## The rejection response shape (Phase 19 / Phase 22 build against this)

Both graphs return their normal result model with `status="failed"` and a `message` naming only ids and checkpoint ids (T-18-10 — never a workspace path or card body). The typed exceptions are raised internally and converted at the entry point, because the catalog shim reduces an escaping exception to its class name, which would have destroyed the "name the uncovered ids" half of the requirement.

Incomplete / unknown coverage — `IncompleteDecisionMap`, exposing `.missing` and `.unknown` (both sorted):

```
Review rejected — no decision was supplied for <id>, <id>; unknown proposal id(s) <id>.
Nothing was written; the run is still paused. Resubmit a decision for every queued proposal.
```

Stale queue — `StaleQueue`, exposing `.supplied` and `.current`:

```
Review rejected — the queue changed since it was rendered (submitted checkpoint '<x>',
current checkpoint '<y>'). Nothing was written. Re-read the queue and resubmit against
the current checkpoint.
```

Both carry `.safe_message`, and both subclass `ReviewRejected`. On every rejection the result still carries `checkpoint_id` (the *current* one) so a caller can retry without a second round trip.

## Deviations from Plan

### 1. [Rule 1 - Bug] A `uuid4().hex`-keyed resume map is silently eaten by LangGraph

- **Found during:** Task 2, when the first id-keyed resume left the run at `status="running"`.
- **Issue:** `Command.resume` accepts *either* a single resume value *or* a **mapping of LangGraph interrupt ids** to resume values, and distinguishes them by inspecting the value — a `dict` is read as the interrupt-id mapping. A `proposal_id` is a 32-character uuid4 hex, which is **exactly the shape of a LangGraph interrupt id**. A bare decision map therefore matched no pending interrupt, was consumed as an empty resume, and left the run **paused with zero writes and no error**. Verified empirically against the pinned langgraph: a 32-hex-keyed dict resume returns the run still interrupted, while a `"pid-a"`-keyed dict resumes fine — so this fails *only* for the id form the checkpoint selected, and only in production.
- **Fix:** `_wrap_resume` / `_unwrap_resume` carry the map across `Command(resume=…)` in a one-element list envelope. Purely a transport detail: the state channel and the capability contract both stay the id-keyed map. A payload that is not the envelope passes through verbatim, so a legacy positional list still reaches `_decision_map` and is rejected rather than coerced.
- **Files modified:** `curation_run.py`, `research_run.py`, `tests/llm/test_curation_run.py`, `tests/llm/test_views_refresh.py`
- **Commit:** 903ed18
- **Note for Phase 19/22:** any caller invoking `graph.invoke(Command(resume=<decision map>))` directly **must** wrap it. This is the sharpest edge the chosen id form introduced.

### 2. [Rule 3 - Blocker] Migration had to be deterministic, not persisted

- **Issue:** The obvious migrate-on-read (inject ids, then write them back) is unsafe here. Persisting would advance the LangGraph checkpoint — the very value D-11 uses as an ETag — so `inspect` would bump the ETag on every read and no resume could ever be current. Writing back is also blocked structurally: `gate_queue` uses an `operator.add` reducer, so `update_state` appends rather than replaces.
- **Fix:** `_migrated_proposal_id` derives the id from `uuid5(namespace, f"{run_id}:{index}")` — the same 32-char opaque hex on every read, in every process, so the id `inspect` shows is the id `review` accepts, and migration performs **zero writes**. Queue position feeds the digest but does not survive it: uuid5 is a hash, the index is not recoverable, and the ids are not ordered, so the "order lives in the queue list only" constraint holds.
- **Files modified:** `curation_run.py`
- **Commit:** 65fa35a

### 3. [Rule 3 - Blocker] Internal callers of the review capabilities

- **Issue:** Making `checkpoint_id` required broke every existing caller. `daily_run.py` (both children) and both CLI `review` commands are outside the plan's `files_modified`, but leaving them broken would break `daily.run` outright.
- **Fix:** `daily_run` passes the ETag it just read from the `awaiting_review` result — which is also a genuine improvement, since the child now resumes the queue it actually rendered. Both CLI commands gained a required `--checkpoint-id` option pointing at `inspect --json`, and their `--decisions-file` help now documents the `{"proposal_id": "decision"}` object shape.
- **Files modified:** `daily_run.py`, `cli.py`
- **Commit:** 6001fae

### 4. [Rule 3 - Blocker] One resume site in `tests/llm/test_views_refresh.py`

- **Issue:** `test_research_run_status_unchanged_when_refresh_raises` drove the research graph with a positional-list resume.
- **Fix:** converted to an id-keyed map inside the transport envelope. This file is not owned by a concurrent plan.
- **Commit:** 903ed18

**Total deviations:** 4 auto-fixed (1 bug, 3 blockers). **Impact:** deviation 1 is the significant one — without it the feature would have shipped silently non-functional in production while every entry-point test passed.

## Issues Encountered

### `tests/llm/test_research_run.py` — 10 failures, deliberately NOT fixed here

Plan 18-07 owns this file concurrently this wave, and the executor prompt explicitly forbids editing it. Every failure is the *intended* contract change landing against tests that assert the removed contract; none indicates a defect in this plan's code. Baseline before this plan: 2 pre-existing failures (`test_workspace_contract_migration.py::TestFixtureRoot::*`, unrelated `test-ws/` fixture layout). After: those 2 plus these 10.

Each needs a mechanical one-line edit:

| Test | Cause | Fix |
|---|---|---|
| `test_full_run_offline` (L58) | positional `Command(resume=defaults)` | `defaults = {e["proposal_id"]: e["decision"] for e in ...}`; wrap in `research_run._wrap_resume(...)` |
| `test_digest_degraded_notice` (L132) | same | same |
| `test_per_finding_decisions` (L366) | `Command(resume=["skip", "ref_only", "skip"])` | map the three actions onto the queue's `proposal_id`s, then wrap |
| `test_reject_all_and_approve_all` (L416, L433) | same | same |
| `test_cross_process_resume` (L482) | same | same |
| `test_idempotent_rerun` (L593) | same | same |
| `test_partial_batch_resume_safe` (L656) | same (`["ref_and_card", "ref_only", "skip"]`) | same |
| `test_run_result_fields` (L546) | `ReviewInput` missing `checkpoint_id` | pass `checkpoint_id=start.checkpoint_id` |
| `test_review_does_not_resume_completed_run` (L1085, L1094) | same | pass the ETag from the run result; note the **second** call is now correctly rejected as *stale* rather than returning the completed run, so that assertion needs re-aiming at `status == "failed"` |
| `test_review_nonexistent_run_reports_failed` (L1107) | same | pass `checkpoint_id=""`; a ghost run has no checkpoint, so the staleness check is skipped and the existing `status == "failed"` assertion still holds |

`test_review_does_not_resume_completed_run` is the only one whose *intent* shifts: re-reviewing a completed run is now refused by the ETag before the paused-state guard is reached. That is GOV-03's replay protection working, and it is a strictly stronger guarantee than the WR-05 behaviour it replaces.

### Behaviour changes a reviewer of `research_run.py` should expect

- `ReviewInput.decisions` is now `dict[str, str] | None`, not `list[dict] | None`.
- A bare `review_research_run` call with **no** flag and **no** payload used to ingest the scoring gate's proposed set. It is now rejected. That was the T-18-03 defect, not a feature.

## Verification

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest tests/llm/test_curation_run.py -x -q` | **39 passed** |
| `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k etag -x -q` | 5 passed |
| `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k decision -x -q` | 6 passed |
| `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k "proposal_id or migrat" -x -q` | 5 passed |
| Every rejection path asserted by reading the workspace back | yes — `_workspace_state` re-reads cards, refs, `connections.json`, `search-seeds.json` and card lifecycles |
| No locking / WAL / busy-timeout added | `grep -c 'busy_timeout\|WAL\|journal_mode'` → 0 in both modules |
| `.venv/bin/python -m pytest -q` | 631 passed, 12 failed — 2 pre-existing + 10 in the concurrently-owned `test_research_run.py` (table above) |

Acceptance criteria greps:

| Criterion | Before | After |
|---|---|---|
| `grep -c 'zip(' curation_run.py` | 3 | **0** (none in decision resolution) |
| `grep -c 'zip(' research_run.py` | 3 | **0** |
| `grep -c 'url' research_run.py` | 21 | **18** (`by_url` → 0) |
| `grep -c 'proposal_id' research_run.py` | 0 | **9** |
| `grep -c 'checkpoint_id' research_run.py` | 0 | **15** |
| `'proposal_id' in CurationProposal.model_fields` | — | True |
| `'checkpoint_id' in CurationRunResult/CurationReviewInput.model_fields` | — | True True |

## Success Criteria

- **GOV-02 met** — decisions are keyed by proposal id and a missing decision never defaults to applying a write.
- **GOV-03 met** — a queue that went stale between render and submit is detected and rejected with zero writes.
- **Runs already paused keep their pending work** and still require an explicit, complete decision.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change at a trust boundary was introduced beyond the two guarded input fields (`proposal_id`, validated; `checkpoint_id`, compared by equality and never used in a path).

## Self-Check: PASSED

All 6 modified source/test files and the SUMMARY exist on disk; all 7 plan commits
(`245fe97`, `65fa35a`, `8c2148f`, `903ed18`, `01b38e3`, `6001fae`, `50146d0`) are present
on the worktree branch; the working tree is clean. Every task's `<acceptance_criteria>`
was re-run and logged in the Verification section above — the only unmet item is
`pytest -q` with no new failures, which is the documented `test_research_run.py` issue
(file owned by concurrent plan 18-07; fixes tabulated under Issues Encountered).

## Next

Ready for phase verification. Phase 19's API and Phase 22's review wizards should be built against the `proposal_id` map contract and the rejection shapes documented above — and must use `_wrap_resume` if they invoke the graph directly.
