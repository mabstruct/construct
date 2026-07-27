---
phase: 18-contract-governance-foundations
plan: 04
subsystem: views-contracts
tags: [vfix-01, views, pydantic, contracts, events, digests, migration]
status: complete

requires:
  - "construct.views.lib.* parsers (the writers whose spellings became the contract)"
  - "construct.schemas.config.EventRecord / EventAgent / EventResult (the canonical event vocabulary)"
provides:
  - "views contract models conformed to the bytes views generate writes"
  - "WorkspaceStatsFile — a contract for <ws>/stats.json"
  - "CurationHistoryFile / CurationCycleRecord — a contract for <ws>/curation-history.json"
  - "GlobalStatsTotals / WorkspaceStatsTotals — the discriminator between the two stats.json files"
  - "one canonical events.json shape, with legacy migration and drop-and-count in parse_events"
  - "a DigestRecord whose projection and workspace-writer authors agree"
affects:
  - "src/construct/views/generate.py — adapters reduced to identity"
  - "src/construct/cli.py — views validate now covers 6 per-workspace files, not 4"
  - "src/construct/llm/research_run.py — compile_digest writes a new on-disk shape"
  - "Plan 05 — inherits identity adapters ready to be replaced by views/contracts.py"

tech-stack:
  added: []
  patterns:
    - "identity adapter: the writer's dict IS the validator's input"
    - "two same-named files discriminated by a required field on a nested totals model"
    - "migrate-on-read: rename the store, never the decision"
    - "drop-and-count: an underivable record is refused loudly, never coerced"

key-files:
  created: []
  modified:
    - src/construct/views/models.py
    - src/construct/views/__init__.py
    - src/construct/views/generate.py
    - src/construct/views/lib/parse_events.py
    - src/construct/llm/research_run.py
    - src/construct/cli.py
    - tests/contract/test_views_contracts.py
    - tests/integration/test_views_generate.py
    - tests/llm/test_research_run.py

decisions:
  - "D-01 applied: views models conformed to the writer; recorded in source as the ING-02 reconciliation"
  - "D-03 applied: all views models relax to extra=ignore; scoped to the derived projection"
  - "D-17 applied: the Python emitter's shape is the canonical events.json contract"
  - "D-18 applied: <ws>/stats.json and <ws>/curation-history.json gain models AND are wired into views validate"
  - "D-20 applied: DigestRecord renamed rather than aliased; its store migrates on read"
  - "ts typed as datetime rather than str, so the projection validates the instant instead of a string"
  - "the 15-02 divergence pin test replaced by a passing (but deliberately weak) round-trip assertion"

metrics:
  duration: ~75 min
  tasks: 3
  commits: 7
  files-changed: 9
  tests-added: 65
  completed: 2026-07-27
---

# Phase 18 Plan 04: Views Contract Conformance Summary

`views validate` now accepts every file `views generate` writes, because the models
finally declare the field names the generator actually emits — plus one canonical
`events.json` shape, contracts for the two previously ungated files, and a `DigestRecord`
rename that no existing user digest pays for.

## What Changed

### The byte contract (Task 1)

The generator computed a correctly-adapted projection of each file, validated *that*, then
wrote the raw parser dict. `views validate` applied the same models to those raw bytes with
no adapter, so 5 of 8 files were rejected on disk — 4 of them purely from field renames that
D-03's relaxation could never have fixed. Both sides now gate the same object: the models
carry the writer's names and `generate.py`'s adapters are the identity function.

| Model | Renamed from → to | Newly declared writer keys |
|---|---|---|
| `CardRecord` | `summary`→`summary_excerpt`, `connections`→`connects_to` | `tags`, `author`, `created`, `last_reviewed`, `sources`, `body_markdown` |
| `ConnectionRecord` | `created_at`→`created`, `created_by`→`author` | `id` |
| `ConnectionsFile` | — | `type_counts` |
| `StatsFile` | six scalar counters → `compute_global`'s real shape | `totals`, `by_lifecycle`, `by_confidence`, `activity_last_30d` |
| `DigestRecord` | `domain_id`→`domain`, `title`→`theme`, `generated_at`→`date`, `summary`→`summary_text` | 10 counter/section keys the SPA renders |
| `EventRecord` | whole shape → the emitter's | `ts`, `agent`, `action`, `target`, `detail`, `result` |

### Declared fields vs. the D-03 relaxation

The plan asked which writer keys were declared and which were left to ignore-extra. Measured
answer, by generating both fixtures and diffing every written key against `model_fields`:

**Every key either fixture writes is a declared field. Nothing is currently carried by the
relaxation.**

That was a deliberate choice — the rule applied was *"a key a consumer renders is owed a
contract, not merely an absence of complaint"*, and a grep of the scaffold SPA
(`CardSidePanel`, `Wiki`, `Digests`, `DigestDetail`, `WorkspaceDashboard`, `Landscape`,
`Landing`) showed a consumer for essentially every parser key. It also means **D-03 currently
protects nothing that exists**: it is insurance against a *future* parser key and against
invalidating `views/build/` copies already on disk, not a fix for anything measured today.
Worth stating plainly, because "we relaxed the models" reads like the fix and it is not — the
renames were the fix (RESEARCH Pitfall 2).

Where the parser genuinely guarantees nothing, the field is declared but left open rather than
nested: `CardRecord.sources`, `DigestRecord.top_findings` / `search_clusters`,
`CurationCycleRecord.deltas`, the three stats breakdown maps. A nested model there would be
stricter than the parser promises.

### The two ungated files (D-18)

`<ws>/stats.json` and `<ws>/curation-history.json` were written with no validation at all.
Both now have models, and — see Deviations — both are wired into `views validate` as well as
the generate-time gate, because a model nothing invokes is not a gate.

The two `stats.json` files stay distinct by construction: `StatsFile.totals` requires
`workspaces` (only `compute_global` counts workspaces) and `WorkspaceStatsFile` requires
`connection_density` / `orphan_cards` / `avg_confidence` (only `compute_workspace` computes
them). Neither payload validates against the other's model, asserted both ways.

### `events.json` (Task 2, D-17)

`parse_events` passed JSONL lines through verbatim, so the file's shape was whichever of four
emitters had last written the log — and an audit-derived view could contain records no emitter
in this repository could have produced (T-18-17). The Python emitter's shape is now canonical.

**Legacy → canonical migration map:**

| Legacy key | Canonical field |
|---|---|
| `timestamp` | `ts` |
| `event` | `action` |
| `author` | `agent` |
| `card` | `target` |
| `details` | `detail` (a dict is JSON-serialised rather than dropped) |

A line is dropped, not coerced, when `ts` is unparseable or `agent` / `result` / `action`
cannot be derived. **`agent` is never defaulted** — inventing an actor for an audit record is
the specific failure mode this refuses.

**Measured drop counts** (each drop is one warning naming file and line, never the payload —
T-18-20):

| Fixture | Kept | Dropped |
|---|---|---|
| `test-ws/my-construct` + `test-ws/ping-eon` (canonical emitter logs) | 15 | 0 |
| `tests/fixtures/v02/multi-domain-medium` (legacy Claude-native logs) | 0 | **30** |

All 30 legacy fixture lines carry `event`/`timestamp`/`details` and nothing else — neither an
author nor a result — so neither `agent` nor `result` is derivable and every line is refused.
That is the honest consequence of D-17 on the shipped legacy fixtures, and it is visible in
`_generation-warnings.log` rather than silent.

`ts` is a `datetime`, not a string: an unparseable timestamp is now rejected instead of
sorting arbitrarily, microseconds and the UTC offset survive validation, and the sort compares
*instants* (a naive string sort orders `09:00+05:30` after `05:00+00:00` even though it is the
earlier moment). The sort is stable, so equal timestamps keep file order — verified by
mutation: replacing `sort(reverse=True)` with sort-then-`reverse()` turns
`test_equal_timestamps_keep_file_order` red.

### `DigestRecord`'s two authors (Task 3, D-20)

> **On-disk shape change:** `digests/digests.json` in every existing workspace changes shape.
> `research_run.compile_digest` is a *writer* using this model, so the rename alters what
> `research.run` puts in a user's workspace, not only what a projection validates. **Migration
> is read-side and automatic**: `_load_digest_store` maps the old keys to the new ones on load
> and rewrites in the new spelling on the next `research.run`. No user action is required, and
> no existing digest is lost.

Migration validates **per record**, not per file. The prior `except ValueError: DigestsFile()`
path would have replaced a user's entire research history with an empty store the moment the
rename landed (T-18-18); now one unmigratable record is dropped with a logged count and its
neighbours survive. Both paths are asserted with fixture stores in the old spelling.

`card_ids` is gone: the generator's adapter hard-coded it to `[]` and no parser ever emitted
it. The created card ids are still listed in the digest markdown's "Created cards" section,
which is the artifact a reader opens — but note that the JSON record store no longer carries
them in machine-readable form.

## Deviations from Plan

**1. [Rule 3 — Blocking] `generate.py` adapters had to change in the same commits**

- **Found during:** Task 1
- **Issue:** `generate.py`'s `_FILE_MODEL_MAP` / `_PER_WS_FILES` adapters mapped writer keys
  onto the *old* model field names. Renaming the model fields without touching them would have
  made `views generate` fail validation on every file it had previously passed — the adapters
  are the writer→validator projection and they cannot survive a rename of one side.
- **Fix:** each adapter became `_as_written` (identity) in the same commit as the model it
  serves, so no commit leaves the generator broken. `generate.py` was not in the plan's
  `files_modified`.
- **Bonus:** this is also the direct answer to RESEARCH Finding V6's warning not to let D-01
  silently downgrade `views generate` from validating-writer to blind-writer. It upgrades it:
  the generator now validates the exact bytes it is about to write, for 10 files instead of 8.
- **Commits:** `20c1144`, `2d5cfd5`, `a03d033`

**2. [Rule 2 — Missing critical functionality] `views validate` wired to the two new models**

- **Found during:** post-Task-3 review against the plan's truth *"no file `views generate`
  writes is left with no gate at all"*
- **Issue:** D-18 gave `<ws>/stats.json` and `<ws>/curation-history.json` models, but
  `views validate` still walked a hard-coded four-file per-workspace list. The two files that
  had no contract remained the two files the user's own check never looked at.
- **Fix:** added both to the list in `cli.py`, binding per-workspace `stats.json` to
  `WorkspaceStatsFile` (never the global `StatsFile`), plus an assertion that both appear in
  the command's checked set.
- **Note for Plan 05:** this is a second copy of the file→model map. Plan 05's
  `views/contracts.py` (`GLOBAL_FILE_CONTRACTS` / `PER_WORKSPACE_FILE_CONTRACTS`) should
  delete *both* this list and `generate.py`'s tables together.
- **Commit:** `730fba5`

**3. [Superseded test expectations] Three tests asserted the behaviour D-03 reverses**

- **Found during:** Tasks 1–2
- **Issue:** `test_models_still_forbid_unknown_fields`, `test_extra_fields_rejected` and
  `test_widened_domain_still_rejects_unknown_fields` encoded the D-02 forbid-extra prohibition
  that D-03 deliberately supersedes.
- **Fix:** inverted each to assert the new behaviour, and — because "the models no longer
  reject extras" is exactly the change that could hollow out the gate — paired each with a
  malformed-payload rejection test. Added `test_projection_relaxation_is_scoped`, which pins
  that `schemas.config.EventRecord` and `schemas.workspace.ConnectionsFile` keep `forbid`, so
  a future reader cannot mistake D-03 for a project-wide licence.
- **Commits:** `20c1144`, `2d5cfd5`

**4. [Unsatisfiable acceptance criterion] `grep -c 'timestamp' parse_events.py`**

- **Criterion:** *"`grep -c 'timestamp' src/construct/views/lib/parse_events.py` is lower than
  before the change"* — before was **1**, so it demanded **0**.
- **Conflict:** the same task mandates a legacy→canonical migration map that must name the
  legacy key `timestamp`. The criterion and the action cannot both be satisfied.
- **Resolution:** the criterion's *intent* is met — the sort key is the canonical `ts` field,
  and the string literal `"timestamp"` appears exactly once, in the migration map. The count is
  now 4; the other three are prose comments using the English word. Rewording readable comments
  to game a grep count was rejected as the wrong trade.

**5. [Stale reference] `test-ws/paskunas` does not exist**

- Task 2's acceptance criterion names `test-ws/paskunas`; the repository has `test-ws/my-construct`
  and `test-ws/ping-eon`. Both were used instead (into temporary copies, never in place), plus
  the v02 legacy fixture so the drop-and-count path was exercised on real legacy bytes rather
  than only synthetic ones.

## Assumptions & Consequences Carried Forward

- **A4 — the rename is a breaking change for any local SPA fork.** Greps covered `src/`,
  `tests/` and the scaffold template; a user's own fork of the views SPA is invisible to this
  repository. Any fork reading `c.summary`, `c.connections`, `conn.created_at`,
  `conn.created_by`, `d.domain_id`, `d.title`, `d.generated_at`, `d.summary`, `d.card_ids`, or
  the old event keys `e.timestamp` / `e.type` / `e.actor` / `e.card_id` / `e.details` will
  break. Plan 05 conforms the in-repo SPA.
- **The SPA's `ActivityList.jsx` is now definitively wrong.** It reads `e.timestamp`, `e.actor`,
  `e.type`, `e.subject.card_id` and `e.skill` — none of which the canonical shape has. It
  rendered blank for Python-emitted events *before* this plan too (RESEARCH Finding V3), so this
  is not a regression, but D-17 makes the fix unambiguous and it is Plan 05's.
- **A5 — `curation-history.json`'s shape may be unstable.** Mitigated structurally rather than
  by deferral: the envelope (`cycles` of id-bearing records) is pinned and the volatile
  `deltas` interior is a declared open mapping, so a new governance counter costs nothing.
- **`digests/digests.json` no longer records created card ids** in machine-readable form (see
  above). If a future consumer needs them, they should be reintroduced under a spelling
  `parse_digests` also emits — not re-added as a second phantom.

## Known Stubs

None. No file `views generate` writes is left without a contract model, and every model is
invoked by both `views generate` and `views validate`.

## Verification

| Check | Result |
|---|---|
| `pytest tests/contract/test_views_contracts.py -x -q` | 116 passed, 4 skipped (was 51 passed) |
| `pytest tests/llm/test_research_run.py -k digest -x -q` | 6 passed |
| `pytest tests/contract/test_views_contracts.py -k events -x -q` | 15 passed |
| No views model declares `extra="forbid"` | `[]` |
| `views.EventRecord` fields == emitter's fields | `True` |
| `grep -c 'D-01' src/construct/views/models.py` | 8 (≥ 2 required) |
| `grep -c 'ValidationError' tests/contract/test_views_contracts.py` | 23 (≥ 5 required) |
| `generate()` on both fixtures | `success=True`, 0 validation errors |
| Full suite | **605 passed**, 5 skipped, 2 failed |

### The two failures are pre-existing and environmental

`test_my_construct_has_canonical_layout` and `test_ping_eon_has_canonical_layout` assert that
`test-ws/*/digests/` etc. exist. Git does not track empty directories, so a freshly created
worktree does not have them. **Both fail identically on the plan's base commit `e53358b`
before any change in this plan** (baseline recorded before Task 1: `2 failed, 525 passed`).
Out of scope per the plan's scope boundary; not written to `deferred-items.md` because they are
a worktree artifact rather than a repository defect.

### Left deliberately weak for Plan 05

`test_views_validate_accepts_generated_bytes` (which replaces the 15-02 divergence pin test)
runs against the scaffolded fixture, whose `demo` workspace has no cards, connections or
digests — so most record models pass vacuously (RESEARCH Pitfall 1). Its docstring says so.
The non-vacuous guard belongs with Plan 05's contract tables; until then the weight is carried
by `test_populated_workspace_generates_clean` and by the contract file's
`TestWriterBytesAreTheContract`, which runs the real parsers over a populated fixture and
asserts non-emptiness before asserting shape.

## Commits

| Commit | Message |
|---|---|
| `86510d2` | test(18-04): add failing tests for writer-conformed views models |
| `20c1144` | feat(18-04): conform views models to writer bytes, relax to ignore-extra |
| `c7d6bcc` | test(18-04): add failing tests for the canonical events.json contract |
| `2d5cfd5` | feat(18-04): make the emitter shape the canonical events.json contract |
| `e69ba51` | test(18-04): add failing tests for the two-author DigestRecord rename |
| `a03d033` | feat(18-04): rename DigestRecord to the parser spelling and migrate its store |
| `730fba5` | fix(18-04): make views validate check the two newly modelled files |

## TDD Gate Compliance

All three tasks followed RED → GREEN. Each `feat` commit is preceded by a `test` commit whose
tests were confirmed failing before implementation. No REFACTOR commits were needed.

## Self-Check: PASSED

- `src/construct/views/models.py` — FOUND (`WorkspaceStatsFile`, `CurationHistoryFile`,
  `CurationCycleRecord`, `GlobalStatsTotals`, `WorkspaceStatsTotals` all importable)
- `src/construct/views/lib/parse_events.py` — FOUND (rewritten)
- `src/construct/llm/research_run.py` — FOUND (`_load_digest_store`, `_migrate_digest_record`)
- `tests/contract/test_views_contracts.py` — FOUND (116 passing)
- `tests/llm/test_research_run.py` — FOUND (digest migration tests passing)
- All 7 commits verified present in `git log`
