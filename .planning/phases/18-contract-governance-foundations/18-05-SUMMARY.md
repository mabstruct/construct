---
phase: 18-contract-governance-foundations
plan: 05
subsystem: views-contracts
tags: [vfix-01, views, pydantic, contracts, spa, events, round-trip-guard]
status: complete

requires:
  - phase: 18-04
    provides: "views contract models conformed to the writer, with generate.py's adapters reduced to identity and a second file→model map added to cli.py"
provides:
  - "src/construct/views/contracts.py — one path-to-model table read by both the validating writer and the validate command"
  - "views generate validates the raw bytes it is about to write, with no adapter in between"
  - "views validate iterates the same table, so its slot list cannot diverge from the writer's"
  - "an SPA activity reader on the canonical event shape, with result rendered"
  - "test_views_generate_output_round_trips_through_views_validate — the non-vacuous, cardinality-asserting drift detector"
affects:
  - "Plan 18-03 — extracts views validate into a registry handler and will find this behaviour to extract"
  - "Plan 18-08 — the escalate action now has a place to render in the activity list"
  - "Phase 19 — model_json_schema() consumers, unchanged by this plan"

tech-stack:
  added: []
  patterns:
    - "one enumeration, two gates: writer and validator read the same table rather than two copies"
    - "no adapter callable in a contract table — an identity adapter is a place for a future fork to grow"
    - "cardinality over set membership: assert the count and the exact set, never just membership"
    - "prove an arithmetic expression at two values of N, so it cannot be a constant fitted to one"
    - "anti-vacuity floor: assert there are records before asserting the records validate"
    - "state an untestable gap as an explicit failing-on-change assertion rather than omitting it"

key-files:
  created:
    - src/construct/views/contracts.py
  modified:
    - src/construct/views/generate.py
    - src/construct/cli.py
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/src/components/ActivityList.jsx
    - tests/integration/test_views_generate.py

key-decisions:
  - "D-01 writer half applied: _validate_file_data validates the raw payload the write loop is about to write, looked up in the shared table — the adapter concept is deleted, not made identity"
  - "D-19 applied: the round-trip guard asserts total_files_written == 4 + 6·N_workspaces + 1, measured 11 at N=1 and 17 at N=2"
  - "The guard seeds canonical emitter events and one publish article into its tmp copies, because EventRecord and ArticleRecord would otherwise validate empty lists on the shipped fixtures — an unanticipated second and third instance of the bridges.json vacuity gap"
  - "The no-partial-build assertion is scoped to publication (version.json + _build_meta.json + the rejected file), because the write loop rewrites sibling data files by design and the plan mandates preserving that loop"
  - "ALL_MODEL_NAMES is now derived-checked against construct.views.models rather than walked as a hand-typed list (the WR-01 lesson applied to the inventory guard itself)"

patterns-established:
  - "Contract table module: a package's file→model map lives in one module that both the writer and the checker import"
  - "Fail-first proof: a guard is not accepted until a deliberate regression has been shown to turn it red"

requirements-completed: [VFIX-01]

coverage:
  - id: D1
    description: "One canonical path-to-model table (views/contracts.py) shared by the validating writer and the validate command; generate.py's adapter tables and cli.py's hand-enumerated list are both deleted"
    requirement: VFIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_contract_tables_are_the_single_file_enumeration"
        status: pass
      - kind: other
        ref: "grep -c '_FILE_MODEL_MAP' src/construct/views/generate.py → 0; grep -c '_PER_WS_FILES' → 0; grep -c 'FILE_CONTRACTS' generate.py → 4, cli.py → 4"
        status: pass
      - kind: other
        ref: "python -c 'from construct.views import contracts as c; print(len(c.GLOBAL_FILE_CONTRACTS), len(c.PER_WORKSPACE_FILE_CONTRACTS))' → 4 6"
        status: pass
    human_judgment: false
  - id: D2
    description: "views generate remains a validating writer: every data file it writes is gated, and it validates the exact bytes it writes rather than an adapted projection"
    requirement: VFIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_every_written_data_file_is_gated_by_a_contract"
        status: pass
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_a_model_violating_payload_is_rejected_and_no_build_is_published"
        status: pass
    human_judgment: false
  - id: D3
    description: "views validate accepts every file views generate writes on a populated install root — 10 slots, zero failed, zero missing"
    requirement: VFIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_views_generate_output_round_trips_through_views_validate"
        status: pass
      - kind: manual_procedural
        ref: "construct views generate && construct views validate on a copy of tests/fixtures/v02/single-domain-small → '11 files written, 0 validation errors' then '10 passed, 0 failed, 0 missing', exit 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "The pin test is replaced by a round-trip guard that asserts cardinality and non-vacuity, and that has been shown to fail when the contract drifts"
    requirement: VFIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_views_generate_output_round_trips_through_views_validate[one-workspace]"
        status: pass
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_views_generate_output_round_trips_through_views_validate[two-workspace]"
        status: pass
      - kind: other
        ref: "fail-first proof: renaming views.models.EventRecord.ts → timestamp turns both parametrisations red; restoring turns them green (recorded below)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The SPA activity list reads the canonical event shape (ts/agent/action/target/detail) and renders result, so an escalated or failed outcome is not drawn identically to a success"
    verification:
      - kind: other
        ref: "grep -c 'e\\.ts\\|e\\.agent\\|e\\.action\\|e\\.target\\|e\\.detail\\|e\\.result' ActivityList.jsx → 7; grep -c 'subject' → 0; grep -c 'e\\.actor\\|e\\.type\\|e\\.timestamp' → 0"
        status: pass
    human_judgment: true
    rationale: "No JavaScript toolchain is installed in this environment and installing one is out of scope (T-18-SC forbids package installs), so the component was never parsed, rendered or screenshotted. The greps prove which keys it reads, not that it compiles or that the escalated badge is legible. A browser-side check belongs to Phase 22 when the served shell exists."

duration: ~65 min
completed: 2026-07-27
---

# Phase 18 Plan 05: Views Byte Contract — Writer Half Summary

**One contract table now feeds both `views generate` and `views validate`; the generator validates the exact dict it hands to `_write_atomic`; and the weak pin test is replaced by a guard that asserts `4 + 6·N + 1` files at N=1 and N=2, refuses to pass on an empty record list, and has been proven to go red on a one-field rename.**

## Performance

- **Duration:** ~65 min
- **Tasks:** 3
- **Commits:** 4
- **Files changed:** 5 (1 created, 4 modified)
- **Tests:** 626 passing (was 620 at the plan's base commit)

## What Changed

### One table, two gates (Task 1)

Plan 04 left the file→model map written down **twice** — `generate.py`'s `_FILE_MODEL_MAP` / `_PER_WS_FILES` adapter tables, and the `ws_files` list inside `cli.py`'s `views validate`. Its executor flagged this explicitly and asked that Plan 05 delete both together. Both are gone; `src/construct/views/contracts.py` holds the only copy:

| Table | Entries |
|---|---|
| `GLOBAL_FILE_CONTRACTS` | `bridges.json`, `domains.json`, `articles.json`, `stats.json` |
| `PER_WORKSPACE_FILE_CONTRACTS` | `cards.json`, `connections.json`, `digests.json`, `events.json`, `stats.json`, `curation-history.json` |

Two tables rather than one, because `stats.json` exists twice with two different writers (`compute_global` vs `compute_workspace`) and two different contracts. A global file matches on exact path and a per-workspace file on a trailing `/<filename>`, so neither can be validated against the other's model.

**There is no adapter callable in the table.** After Plan 04 every adapter was the identity function, and an identity adapter left in place is a slot a future edit can quietly re-fork — which is exactly how the original divergence grew. The concept is deleted rather than defaulted.

### The writer still validates — and now validates the right object (Task 1, OQ-C / Finding V6)

`_validate_file_data` was the tables' only consumer. Deleting them without a replacement would have removed generate-time validation entirely and turned a validating writer into a blind one, leaving the phase dependent on `views validate` being run separately, which no workflow guarantees (T-18-21). It now looks the model up in the shared table and calls `model_validate` on **`raw_data` — the same dict the write loop is about to pass to `_write_atomic`**. `install_root_error`, `_write_atomic`, the error accumulation, the `total_files_written` accounting and the do-not-publish-a-rejected-build gating are all preserved verbatim.

### `views validate` grows with the table (Task 1)

The command iterates the same two tables. Its per-file output format and exit code are unchanged (Plan 03 extracts this command into a registry handler and must find the same behaviour). Measured end-to-end on a copy of the one-workspace populated fixture:

```
Views data generation: build 69415743, 11 files written, 0 validation errors, 30 content warnings
Views data validation: 10 passed, 0 failed, 0 missing        (exit 0)
```

### The SPA reads what the emitter writes (Task 2, D-17)

`ActivityList.jsx` read five keys — a legacy timestamp key, an actor key, a type key, a nested object, and a skill key — **none of which any CONSTRUCT emitter has ever produced**. The nested object existed in no emitter at all. Every Python-emitted event rendered with a blank actor and a blank type. Conformed to `ts` / `agent` / `action` / `target` / `detail`, with `describeTarget` composing the description from `target` and `detail`.

`result` is now rendered rather than merely read: `failure` and `escalated` get a coloured badge, `success` gets none. Plan 08 introduces an escalate action whose entire point is that it wrote nothing; an activity list that drew it identically to an applied change would recreate the audit-trail-that-lies defect in the browser.

The time formatter and label prettifier are shape-agnostic and were kept. Only the scaffold template was edited — nothing under `test-ws/` (generated scaffolds) or `views/design-example/` (a superseded prototype).

### The guard (Task 3, D-19)

`test_views_validate_accepts_generated_bytes` — which Plan 04 had already flagged as *"deliberately weak and Plan 05 replaces it"* — is replaced by:

**`test_views_generate_output_round_trips_through_views_validate`**

parametrised `[one-workspace]` / `[two-workspace]`. It:

- runs on **populated** roots (`single-domain-small`, `multi-domain-medium`), not the scaffolded one whose `demo` workspace has no cards, connections or digests;
- asserts `report.total_files_written == len(GLOBAL) + len(PER_WS)·N + 1`, computed from the fixture's real workspace count — **equality**, so one file more or one fewer fails;
- asserts the validated slot set **equals** the set the contract tables enumerate (a slot dropped from the tables would otherwise make "all slots pass" trivially true for a smaller set);
- asserts every record list is non-empty *before* asserting its contract holds;
- states the `bridges.json` gap as a live assertion rather than an omission.

**Measured file counts (D-19's arithmetic, corrected from D-04's literal 8):**

| Fixture | Workspaces | Expected `4 + 6·N + 1` | Measured |
|---|---|---|---|
| `single-domain-small` | 1 | 11 | **11** |
| `multi-domain-medium` | 2 | 17 | **17** |

D-04's "count equals 8" would have failed on its first run, exactly as the plan predicted.

### Fail-first proof (required by Task 3's acceptance criteria)

A guard that cannot be made to fail is not a guard. `views.models.EventRecord.ts` was deliberately renamed back to its pre-D-17 spelling `timestamp` and the guard re-run:

| Run | Result |
|---|---|
| `ts` → `timestamp` applied | **2 failed** — both parametrisations, `cosmology/events.json: 2 validation errors for EventsFile / events.0.timestamp / Field required` |
| field restored (`git checkout -- src/construct/views/models.py`) | **22 passed** |

The regression was chosen deliberately: `ts` is a *required* field, and under D-03's `extra="ignore"` a rename of an *optional* field (e.g. `summary_excerpt` → `summary`) would **not** fail — the written key becomes an ignored extra and the renamed field takes its default. That is a real and now-recorded limit on what any model-level guard can detect after D-03, and it is part of why the guard also asserts cardinality and set equality rather than validation success alone.

It is also why the event seeding below is load-bearing: on the shipped fixtures `events.json` is empty, so **this exact rename would have gone undetected** by a guard that did not seed events.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical] Two more models were passing vacuously than the plan anticipated**

- **Found during:** Task 3
- **Issue:** The plan's `must_haves` states that every record list is non-empty on the populated fixture and that **`bridges.json` alone** leaves a model unexercised. Measured, that is not true. `<ws>/events.json` is empty on *both* populated fixtures — D-17 refuses all 30 legacy Claude-native log lines (18-04 measured this: 0 kept, 30 dropped) — and `articles.json` is empty on the one-workspace fixture, which ships no `publish/*.md` at all. So `EventRecord` and `ArticleRecord` would both have validated `[]`, the same vacuity trap as bridges, on the model this phase reshaped most.
- **Fix:** the guard's fixture helper now (a) appends real events via `services.event_log.append_event` — the actual emitter, not hand-typed lines, so the guard exercises emitter → parser → model → `views validate` end to end, including one `escalated` result; and (b) writes one `publish/*.md` citing a real card id when no workspace has one. Both write into the test's own `tmp_path` copy; the shared fixtures under `tests/fixtures/` are untouched.
- **Verification:** with the seeding removed, the `EventRecord.ts` fail-first regression above is not detected. With it, both parametrisations go red.
- **Committed in:** `c662078`

**2. [Rule 1 — Bug] `Path.glob()` is truthy even when it yields nothing**

- **Found during:** Task 3
- **Issue:** the publish-article helper guarded with `any((ws / "publish").glob("*.md") for ws in workspaces)`. `Path.glob` returns a *generator object*, which is truthy regardless of contents, so the helper concluded "an article already exists" for every root and wrote nothing.
- **Fix:** materialise the matches into a list before testing. Caught by the guard's own non-vacuity assertion — which is itself modest evidence that the assertion is not decorative.
- **Committed in:** `c662078`

**3. [Rule 2 — Missing critical] Prototype-chain lookup in the SPA result badge**

- **Found during:** Task 2
- **Issue:** `RESULT_STYLES[result]` reads a plain object with a key taken straight from a JSON file. A `result` value of `constructor` or `__proto__` resolves to an inherited member, which is truthy, and would have been interpolated into `className`. This codebase already treats `views/build/data/` as untrusted on the way back in (see `_cards_are_well_shaped`'s docstring).
- **Fix:** `if (typeof style !== 'string') return null`, which handles the prototype case and the missing-key case together.
- **Committed in:** `954882c`

### Judgement calls recorded against the plan's own wording

**4. The no-partial-build assertion is scoped to *publication*, not to the whole directory**

Task 1's acceptance criterion reads *"a generate run with one model-violating payload leaves the existing build directory unchanged"*, and the corresponding `must_haves` truth says *"leaves the previous build directory untouched — no partial build is published"*.

**The first clause cannot hold under the write loop the same task mandates preserving.** The loop validates and writes file-by-file, so a run that rejects one file still rewrites its siblings; and `envelope.wrap` stamps a fresh `generated_at` into every file, so even an unchanged payload produces different bytes. A whole-directory byte-identity guarantee would require staging the build and swapping it, or validating all files before writing any — and the latter breaks the prior-phase test `test_validation_error_run_does_not_latch_into_permanent_success`, which asserts `second.total_files_written > 0` to prove a failed run retried rather than short-circuited. Both are architectural changes (Rule 4) that the plan explicitly excludes with *"preserve the surrounding behaviour exactly"*.

What **is** asserted, in `test_a_model_violating_payload_is_rejected_and_no_build_is_published`, is the second clause — the one that protects the consumer:

| Artifact | Guarantee |
|---|---|
| the rejected file (`stats.json`) | byte-identical — skipped, never written |
| `version.json` | byte-identical — the pointer the SPA polls still names the previously published build |
| `_build_meta.json` | byte-identical — the fingerprint cache did not advance, so the failure is retried rather than latched into permanent success |

The test carries a scope note saying in as many words that sibling data files *are* rewritten, so no future reader mistakes it for a full-directory guarantee. **A staged-build swap is the obvious way to make the literal clause true and is not attempted here.**

**5. `test-ws/paskunas` does not exist** — Task 1's fourth acceptance criterion names it. 18-04 already flagged this stale reference; the repository has `test-ws/my-construct` and `test-ws/ping-eon`, and neither is usable as an install root in a fresh worktree (no `AGENTS.md` marker, no workspace subdirectories — git does not track the empty directories). The criterion's intent — *"zero validation errors on generate and zero failed / zero missing on validate, across 10 slots"* — was satisfied against a copy of `tests/fixtures/v02/single-domain-small`, which is a one-workspace populated install root and therefore produces exactly the 10 slots the criterion names. Output quoted above.

**6. `test_views_validate_does_not_yet_accept_generated_bytes` was already gone** — Plan 04 replaced it with `test_views_validate_accepts_generated_bytes` and documented that as deliberately weak, to be replaced here. The test this plan replaced is therefore the latter, and it is named in the commit message and above so the substitution chain (15-02 pin → 18-04 weak → 18-05 guard) stays auditable.

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 bug) + 3 recorded judgement calls against plan wording.
**Impact on plan:** no scope creep. The two vacuity fixes strengthen the deliverable the plan describes as "the sole remaining detector of the next fork". Deviation 4 is the only place the shipped behaviour is narrower than a literal reading of the plan, and it is narrower because the plan's own `<action>` forbids the change that would widen it.

## Issues Encountered

- **No `.venv` inside the worktree.** `.venv/` is gitignored and lives only in the main checkout, so `AGENTS.md`'s mandated `.venv/bin/python -m pytest` cannot be run verbatim from here. The main checkout's interpreter was used instead; `pytest`'s `pythonpath = [".", "src"]` is resolved against the rootdir, so the **worktree's** `src/` is what gets imported — verified explicitly before relying on it. No packages were installed (T-18-SC).
- **No JavaScript toolchain.** Task 2's component was never parsed or rendered. See the `D5` coverage rationale.

## Known Stubs

None. No data file `views generate` writes is left ungated, and no contract model is stubbed.

**Unexercised contract model (not a stub, but a recorded coverage gap):** `BridgeRecord`. Even the populated fixtures produce an empty `bridges` list, so the guard cannot prove it against real data. Per the plan this is authored as a **backstop** truth: the guard asserts `bridges == []` explicitly, so the day a fixture starts producing bridges the assertion fails and forces the slot up into the non-vacuity probes rather than letting it stay silently unproven. Forcing bridges into a fixture is the obvious future fix and was not attempted.

## Verification

| Check | Result |
|---|---|
| `pytest tests/integration/test_views_generate.py -x -q` | **22 passed** |
| `pytest -q` (full suite) | **626 passed**, 5 skipped, 2 failed |
| `views generate` → `views validate` on a populated one-workspace root | 11 files written, 0 validation errors → 10 passed / 0 failed / 0 missing, exit 0 |
| `grep -c '_FILE_MODEL_MAP' generate.py` / `grep -c '_PER_WS_FILES'` | 0 / 0 |
| `grep -c 'FILE_CONTRACTS'` in `generate.py` / `cli.py` | 4 / 4 |
| `len(GLOBAL_FILE_CONTRACTS), len(PER_WORKSPACE_FILE_CONTRACTS)` | `4 6` |
| `grep -c 'subject'` / `'e\.actor\|e\.type\|e\.timestamp'` in `ActivityList.jsx` | 0 / 0 |
| canonical-field grep in `ActivityList.jsx` (≥6 required) | 7 |
| `grep -c 'does_not_yet_accept_generated_bytes'` | 0 |
| `grep -c '_populated_install_root'` (≥3 required) | 7 |
| `scaffolded_install_root` inside the new guard's body | 0 |
| Fail-first proof (`EventRecord.ts` → `timestamp`) | 2 failed → restored → 22 passed |

### The two failures are pre-existing and environmental

`test_my_construct_has_canonical_layout` and `test_ping_eon_has_canonical_layout` assert that `test-ws/*/digests/` etc. exist. Git does not track empty directories, so a fresh worktree does not have them. **Both fail identically on this plan's base commit `046de78` before any change here** — baseline recorded before Task 1: `2 failed, 620 passed, 5 skipped`. Same two failures 18-04 documented. Out of scope per the plan's scope boundary; a worktree artifact rather than a repository defect, so not written to `deferred-items.md`.

## TDD Gate Compliance

Tasks 1 and 3 carried `tdd="true"`.

- **Task 1:** RED `83813b8` (collection error — `construct.views.contracts` did not exist) → GREEN `afbd70b`. No refactor needed.
- **Task 3:** the guard's RED is its fail-first proof — the deliberate `EventRecord.ts` → `timestamp` regression turned both parametrisations red, and restoring the field turned them green. Recorded above with both runs. The guard also went red on first authoring for a real reason (deviation 2), which was fixed before the commit.

Task 2 was `type="auto"` without TDD; it edits a JSX template with no test harness in this repository, and its verification is the grep set in `<verify>`.

## Commits

| Commit | Message |
|---|---|
| `83813b8` | test(18-05): add failing tests for the shared views contract table |
| `afbd70b` | feat(18-05): one shared views contract table read by writer and validator |
| `954882c` | fix(18-05): conform the SPA activity reader to the canonical event shape |
| `c662078` | test(18-05): replace the pin test with a non-vacuous round-trip guard |

## Next Phase Readiness

- **VFIX-01 is met** and marked complete in `REQUIREMENTS.md` — both declaring plans (18-04, 18-05) now have summaries.
- **Plan 18-03** extracts `views validate` into a registry handler. It will find one import of `views.contracts` and the same per-file output format and exit code; nothing about the command's surface changed.
- **Plan 18-08's escalate action** has a rendering path in the SPA activity list the moment it starts emitting.
- **Carried forward — A4:** an external fork of the views SPA is invisible to this repository. A user who forked the scaffold template still carries the old accessors and will render blank actors; only the in-repo template was conformed.
- **Carried forward:** the D-03 relaxation means a rename of an *optional* model field is undetectable by validation alone. The guard's cardinality and set-equality assertions are the compensating control; anyone weakening them should read the fail-first note above first.

## Self-Check: PASSED

- `src/construct/views/contracts.py` — FOUND (`GLOBAL_FILE_CONTRACTS`, `PER_WORKSPACE_FILE_CONTRACTS` importable, sizes 4 and 6)
- `src/construct/views/generate.py` — FOUND (adapter tables absent, `contract_for` present)
- `src/construct/cli.py` — FOUND (`views validate` iterates the shared tables)
- `CONSTRUCT-CLAUDE-impl/.../components/ActivityList.jsx` — FOUND (canonical accessors, no legacy keys)
- `tests/integration/test_views_generate.py` — FOUND (22 passing, guard present under both parametrisations)
- All 4 commits verified present in `git log 046de78..HEAD`

---
*Phase: 18-contract-governance-foundations*
*Completed: 2026-07-27*
