---
phase: 19-http-api-over-the-capability-registry
plan: 02
subsystem: infra
tags: [sqlite, wal, langgraph, sqlitesaver, checkpoints, concurrency, adr]

# Dependency graph
requires:
  - phase: 10-durable-human-review-research-run
    provides: the SqliteSaver checkpointer and _open_checkpointer in research_run
  - phase: 11-curation-run-workflow
    provides: the twin _open_checkpointer in curation_run
  - phase: 18
    provides: D-11 checkpoint-id ETag (the race arbitrator this contract relies on) and the T-18-26 tripwire that reserved this work for Phase 19
provides:
  - CHECKPOINT_BUSY_TIMEOUT_MS = 30_000 declared in construct.llm.curation_run and construct.llm.research_run
  - both _open_checkpointer functions set PRAGMA journal_mode=WAL and pass timeout= to sqlite3.connect themselves
  - tests/llm/test_checkpoint_concurrency.py — the OQ-4 pin, asserting both PRAGMAs on a live connection
  - ADR-0004 concurrency-contract extension recording the contract, the absent cross-process lock, and the ETag arbitration
affects: [19-09, HTTP-06, run-addressability, any phase that spawns a run from the server while a CLI resume may be running]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inherited library/stdlib defaults that carry a guarantee are declared explicitly in this repo's code and pinned by a live-connection test, so a dependency bump fails a test instead of silently reverting the guarantee"
    - "A deliberate tripwire test is inverted rather than deleted when the phase it was waiting for lands, so the handover stays legible in the diff"

key-files:
  created:
    - tests/llm/test_checkpoint_concurrency.py
  modified:
    - src/construct/llm/curation_run.py
    - src/construct/llm/research_run.py
    - tests/llm/test_curation_run.py
    - CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md

key-decisions:
  - "D-14: the checkpoint concurrency contract is WAL plus an explicit 30 000 ms busy_timeout, with no locking of any kind"
  - "30 000 ms rather than the inherited 5 000 ms, recorded as a reasoned estimate and not a measurement — the upper bound of a curation resume's write transaction was never established"
  - "No cross-process mutual exclusion is added; racing resumes stay arbitrated by the Phase 18 D-11 checkpoint-id ETag, whose loser writes nothing"
  - "The Phase 18 T-18-26 tripwire (which forbade busy_timeout/journal_mode/WAL while OQ-4 was open) was inverted in place rather than deleted"

patterns-established:
  - "Contract-not-default: a behaviour that happens to be correct because of a library or stdlib default is re-declared locally and pinned, because an inherited default has no failure signal"
  - "ADR cites the constant (CHECKPOINT_BUSY_TIMEOUT_MS), never the number twice, so document and code cannot drift"
  - "Stated limitations over implied ones: the ADR says outright that cross-process mutual exclusion is not provided"

requirements-completed: [HTTP-06]

coverage:
  - id: D1
    description: "Both checkpointers declare PRAGMA journal_mode=WAL in this repo's own code rather than inheriting it from SqliteSaver.setup()"
    requirement: "HTTP-06"
    verification:
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_checkpointer_declares_wal_journal_mode[curation]"
        status: pass
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_checkpointer_declares_wal_journal_mode[research]"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both checkpointers declare an explicit 30 000 ms busy_timeout rather than inheriting sqlite3.connect's timeout=5.0 default"
    requirement: "HTTP-06"
    verification:
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_checkpointer_declares_the_d14_busy_timeout[curation]"
        status: pass
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_checkpointer_declares_the_d14_busy_timeout[research]"
        status: pass
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_both_checkpointers_agree_on_the_timeout_value"
        status: pass
    human_judgment: false
  - id: D3
    description: "A second, independently opened connection to the same checkpoint file also reports WAL, proving the mode is persisted in the database header"
    requirement: "HTTP-06"
    verification:
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_wal_persists_for_a_second_independent_connection[curation]"
        status: pass
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_wal_persists_for_a_second_independent_connection[research]"
        status: pass
    human_judgment: false
  - id: D4
    description: "No lockfile and no cross-process mutex are introduced by either checkpointer path"
    requirement: "HTTP-06"
    verification:
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_checkpointer_introduces_no_lockfile[curation]"
        status: pass
      - kind: unit
        ref: "tests/llm/test_checkpoint_concurrency.py#test_checkpointer_introduces_no_lockfile[research]"
        status: pass
      - kind: unit
        ref: "tests/llm/test_curation_run.py#test_concurrency_configuration_moved_to_phase_19"
        status: pass
    human_judgment: false
  - id: D5
    description: "ADR-0004 records the concurrency contract, the absent cross-process mutual exclusion, the ETag arbitration, and cites the pin"
    requirement: "HTTP-06"
    verification:
      - kind: other
        ref: "grep assertions over CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md for journal_mode=WAL, busy_timeout, 30_000, 'no cross-process mutual exclusion', 'checkpoint-id ETag', 'zero canonical writes', 'tests/llm/test_checkpoint_concurrency.py', 'CHECKPOINT_BUSY_TIMEOUT_MS' — all present"
        status: pass
      - kind: integration
        ref: ".venv/bin/python -m pytest tests/contract -q (327 passed, 22 skipped — no doc-reference guard regressed)"
        status: pass
    human_judgment: true
    rationale: "Whether the ADR's prose actually states the limitation honestly — rather than merely containing the required strings — is an editorial judgment a grep cannot make. The specific claim a human should check is that the 30 000 ms value is presented as a reasoned estimate and not as a measurement."

# Metrics
duration: 24min
completed: 2026-08-03
status: complete
---

# Phase 19 Plan 02: Checkpoint Concurrency Contract Summary

**Both LangGraph checkpointers now declare `journal_mode=WAL` and a 30 000 ms `busy_timeout` in this repo's own code, pinned by a live-connection test, with ADR-0004 recording that cross-process mutual exclusion is not provided and that racing resumes are arbitrated by the checkpoint-id ETag.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-08-03T00:00:00Z
- **Completed:** 2026-08-03T00:24:00Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Turned OQ-4 from an accident into a contract. The measured finding driving this plan was confirmed empirically during execution: a bare `sqlite3.connect` reports `journal_mode = delete` and `busy_timeout = 5000`, so before this change the WAL guarantee depended entirely on `SqliteSaver.setup()` running its own pragma, and the timeout was the stdlib default. Neither was ours, and no test would have noticed either going away.
- `CHECKPOINT_BUSY_TIMEOUT_MS = 30_000` is declared in both `curation_run` and `research_run`, and both `_open_checkpointer` functions now pass `timeout=CHECKPOINT_BUSY_TIMEOUT_MS / 1000` to `sqlite3.connect` and execute `PRAGMA journal_mode=WAL` on the connection before constructing the `SqliteSaver`.
- `tests/llm/test_checkpoint_concurrency.py` (9 tests) reads both PRAGMAs back from a **live** checkpointer connection, asserts `busy_timeout` for exact equality rather than a lower bound, proves WAL persists for a second independently opened connection, and asserts no lockfile appears beside the database.
- ADR-0004 carries a new concurrency-contract extension stating the contract, the limitation, and the arbitration — including that `SqliteSaver`'s `threading.Lock` is per-instance and gives two processes no shared lock at all.
- The Phase 18 T-18-26 tripwire fired exactly as designed and was retired in place.

## Task Commits

1. **Task 1: Both checkpointers declare their own concurrency PRAGMAs, and a test pins them** — `a664d42` (feat)
2. **Task 2: Extend ADR-0004 with the concurrency contract and its stated limitation** — `b8242d0` (docs)

## Files Created/Modified

- `tests/llm/test_checkpoint_concurrency.py` — **created.** The OQ-4 pin: 9 parametrised tests over both checkpointer modules covering WAL, exact `busy_timeout`, header persistence across a second connection, timeout-constant agreement, and the no-lockfile assertion.
- `src/construct/llm/curation_run.py` — added `CHECKPOINT_BUSY_TIMEOUT_MS`; `_open_checkpointer` sets both PRAGMAs; docstring records why an inherited default is not a contract and that no cross-process lock exists.
- `src/construct/llm/research_run.py` — the identical change to the twin `_open_checkpointer`, with a comment stating the value must not drift from curation's because adr-0004 governs both as one artifact class.
- `tests/llm/test_curation_run.py` — `test_concurrency_configuration_stays_phase_19s` inverted into `test_concurrency_configuration_moved_to_phase_19`.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md` — new `## Concurrency contract (extension — Phase 19, 2026-08-03)` section plus a status-line note; the original decision is untouched.

## Decisions Made

**D-14 — WAL plus an explicit 30 000 ms `busy_timeout`, with no locking.** Concurrent readers never block; a writer waits rather than erroring. Recorded in ADR-0004 with its two rejected alternatives: a server-held single-flight lock (rejected because a CLI resume cannot see it, so the guarantee would silently not apply to half its callers) and a lockfile (rejected because stale-lock recovery's failure mode is a permanently un-resumable run — a durable way to lose pending review decisions that exist nowhere else).

**The 30 000 ms value is documented as an estimate, not a measurement.** RESEARCH could not establish the realistic upper bound of a curation resume's write transaction, and the ADR says so explicitly rather than presenting the figure as derived. This is the one residue of the flagged `unclassified` HTTP-06 probe row that this plan touches.

**The ADR cites `CHECKPOINT_BUSY_TIMEOUT_MS`, not the number twice.** The value appears once in the ADR as the constant's declaration; every other reference is to the constant, so the document cannot drift from the code.

**The Phase 18 tripwire was inverted, not deleted.** See the deviation below — the reasoning is that a tripwire removed without a trace cannot be distinguished from one that never fired.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Retired the Phase 18 T-18-26 tripwire that forbade exactly this plan's change**

- **Found during:** Task 1 (verification run `pytest tests/llm tests/integration`)
- **Issue:** `tests/llm/test_curation_run.py::test_concurrency_configuration_stays_phase_19s` asserted that the strings `busy_timeout`, `journal_mode`, and `WAL` were **absent** from both run modules. Its docstring states the reason directly: *"the checkpoint concurrency contract … is Phase 19's (OQ-4)"*. It is a deliberate tripwire that Phase 18 planted to stop itself from quietly claiming that the ETag survives lock contention — and this plan is precisely the event it was waiting for. `tests/llm/test_curation_run.py` was not in the plan's `files_modified`, so the collision was not anticipated; leaving it would have made Task 1's acceptance criterion (`pytest tests/llm tests/integration` exits 0) unreachable.
- **Fix:** Inverted the assertion in place and renamed it `test_concurrency_configuration_moved_to_phase_19`. It now asserts the contract IS declared (`journal_mode=WAL` present, `CHECKPOINT_BUSY_TIMEOUT_MS == 30_000`), that the still-true half of T-18-26 holds (no `lockfile`/`flock`/`filelock` in either module), and that the live-connection pin module exists. The docstring records the handover and restates that the ETag stops cross-process *misapplication* and nothing provides cross-process *exclusion*. Deleting the test was rejected: a tripwire that vanishes without a trace cannot be told apart from one that never fired.
- **Files modified:** `tests/llm/test_curation_run.py`
- **Verification:** `.venv/bin/python -m pytest tests/llm tests/integration -q` — the failure cleared; full suite 805 passed.
- **Committed in:** `a664d42` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope creep. The tripwire's retirement is work this plan implicitly owned — Phase 18 assigned the contract to Phase 19 by name, and the guard was the mechanism enforcing that assignment.

## Issues Encountered

**Two pre-existing failures in `tests/integration/test_workspace_contract_migration.py` are a worktree artifact, not a regression.** `TestFixtureRoot::test_my_construct_has_canonical_layout` and `TestFixtureRoot::test_ping_eon_has_canonical_layout` both fail with `Missing canonical directory …: digests/`. Cause: `test-ws/` is gitignored with a handful of fixture files force-added, and `digests/` is an **empty** directory — git cannot represent one, so it exists in the main checkout but is never materialised in a linked worktree. Confirmed by inspection: `/Users/mab/dev/mabstruct/construct/test-ws/ping-eon/digests` exists in the main checkout and `git ls-files test-ws/ping-eon` lists no `digests/` entry. Unrelated to this plan's five files; logged to `deferred-items.md` and not fixed, per the scope boundary.

**The pin was verified to be a real pin, not a tautology.** Before trusting the green run, a bare `sqlite3.connect` was measured directly: `journal_mode = delete`, `busy_timeout = 5000`. So removing either declaration from `_open_checkpointer` genuinely fails the new tests. A test that passes for reasons other than the behaviour it names would have reproduced the exact problem this plan exists to fix.

## Verification

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest tests/llm/test_checkpoint_concurrency.py -q` | 9 passed |
| `.venv/bin/python -m pytest tests/llm tests/integration -q` | 296 passed, 2 failed (both pre-existing worktree artifacts, see above) |
| `.venv/bin/python -m pytest tests/contract -q` | 327 passed, 22 skipped |
| `.venv/bin/python -m pytest -q` | 805 passed, 22 skipped, 2 failed (the same two) |

## Known Stubs

None. No placeholder values, no skipped tests added, and every `<verify>` in the plan was run.

## Threat Flags

None. The plan's threat register covers the surface this plan touched (T-19-13 mitigated by WAL + `busy_timeout` + ETag arbitration; T-19-14 mitigated by the new pin; T-19-03 unchanged and still in force via `_validate_run_id`; T-19-10 accepted). No new network endpoint, auth path, file-access pattern, or schema change at a trust boundary was introduced — the change is two PRAGMAs on an existing connection.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The concurrency contract is in force and pinned, so plan 19-09 (HTTP-06 run addressability) can make a browser-spawned run and a CLI resume share a checkpoint file against a written, tested invariant rather than an inherited default.
- **Carried forward for 19-09:** the 30 000 ms value is a reasoned estimate. If a curation resume's write transaction is ever measured, the constant should be revisited — it is two module constants and a docstring, so D-14 is cheaply reversible by design.
- **Note for the verifier:** two `test_workspace_contract_migration` failures will appear in any worktree-executed phase until the fixture handles the empty `digests/` directory. See `deferred-items.md`.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-03*
