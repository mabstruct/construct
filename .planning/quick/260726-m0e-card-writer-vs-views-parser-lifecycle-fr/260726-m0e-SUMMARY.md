---
phase: quick-260726-m0e
plan: 01
subsystem: knowledge-services / views-data-contract
tags: [card-writer, views-parser, frontmatter, data-contract, tdd, v0.4.1-audit]
status: complete
quick: true
quick_id: 260726-m0e

requires:
  - "src/construct/services/knowledge.py::_card_dict_to_markdown (sole card serializer)"
  - "src/construct/views/lib/parse_cards.py::REQUIRED_FIELDS (read-only counterparty)"
  - "tests/integration/conftest.py::scaffolded_install_root"
provides:
  - "Every card the codebase writes carries a literal `lifecycle:` key in its on-disk frontmatter"
  - "Two permanent writer-to-parser round-trip guards, derived from parse_cards.REQUIRED_FIELDS at call time"
affects:
  - "create_card, edit_card, archive_card and every caller funnelling through them (research_run.py:589, pipelines/ingestion.py:246, capabilities/catalog.py:881-882)"
  - "views generate output: cards.json / stats.json now include CLI-created cards"

tech_stack:
  added: []
  patterns:
    - "Contract lives on the writer, not the reader (adr-0001 markdown-as-truth)"
    - "Guard derives its expectation from the live parser module rather than a hardcoded literal"
    - "Anti-weakening pin: the guard asserts the parser's contract still holds the field, so the suite cannot be made green by relaxing the parser"

key_files:
  created: []
  modified:
    - "src/construct/services/knowledge.py (+8)"
    - "tests/integration/test_views_generate.py (+120)"
  modified_untracked:
    - "test-ws/my-construct/cards/a-research-note-about-cosmology-inflation.md (+1, gitignored)"
    - "test-ws/smoke202606201640/cards/semantic-caching-cuts-gateway-latency.md (+1, gitignored)"
    - "test-ws/smoke202606201640/cards/token-based-rate-limiting.md (+1, gitignored)"

decisions:
  - "D-01 honoured: the writer is the contract owner. parse_cards.py untouched; the default applied on the serializer so all three writers inherit it."
  - "Copy-then-setdefault rather than mutate-in-place, so create_card's post-serialization read of data['epistemic_type'] and edit_card's raw dict cannot be perturbed (T-m0e-02)."
  - "Lifecycle.seed.value used rather than the bare string 'seed', so serializer and schema cannot drift apart."
  - "Task 3 deviation: the three fixture files are gitignored and untracked, so the backfill was applied on disk but NOT committed. Force-adding gitignored paths was rejected."

metrics:
  duration: "~20 min"
  tasks: 3
  files_committed: 2
  files_modified_untracked: 3
  commits: 2
  tests_before: "526 passed, 1 skipped"
  tests_after: "528 passed, 1 skipped"
  completed: 2026-07-26
---

# Quick Task 260726-m0e: Card writer vs views parser lifecycle frontmatter contract — Summary

**One-liner:** `_card_dict_to_markdown` — the codebase's sole card serializer — now applies the
`Lifecycle.seed` schema default before dumping frontmatter, so cards written by `create_card` are no
longer silently dropped by the strict views parser; pinned by two round-trip guards that derive their
expectation from `parse_cards.REQUIRED_FIELDS` at call time.

## What Was Built

### Task 1 — Round-trip guards (RED) — commit `3328a09`

Two tests plus a shared `_create_demo_card` helper appended to
`tests/integration/test_views_generate.py`, tracing one card through every layer the defect spans:
service writer → disk bytes → views frontmatter splitter → parser field contract → `generate()` →
per-workspace `cards.json`.

- `test_written_card_frontmatter_satisfies_views_parser_contract` — the contract guard. Uses
  `construct.views.lib.frontmatter.parse` (the parser's own splitter), **not**
  `schemas.card.parse_card_markdown`; the docstring states why, since the Pydantic path fills exactly
  the default the raw path cannot see and would reproduce the blindness the test exists to remove.
  Carries two non-vacuity floors (non-empty `meta`, non-empty `REQUIRED_FIELDS`), the anti-weakening
  pin (`"lifecycle" in parse_cards.REQUIRED_FIELDS`, T-m0e-03), the derived subset assertion, and the
  named `lifecycle == "seed"` regression pin.
- `test_written_card_reaches_generated_cards_json` — the end-to-end symptom the v0.4.1 audit
  reproduced. One `generate()` call only (a second can be served by the incremental fingerprint
  cache). Non-empty-ids floor before membership, then the targeted per-file warning check, then the
  full `report.warnings == []` contract.

### Task 2 — The writer always serializes lifecycle (GREEN) — commit `ac45d0e`

Eight lines in `_card_dict_to_markdown`: copy the incoming mapping, `setdefault("lifecycle",
Lifecycle.seed.value)`, plus one docstring sentence recording that the serializer owns this contract
because `views/lib/parse_cards.py` requires the literal key in raw frontmatter.

Absent-only by design: `create_card` gains the key appended last (an append, never a reorder);
`edit_card` output is byte-identical for any card that already carries it; `archive_card` is
unchanged because `:338` sets `raw["lifecycle"]` explicitly before the call.

### Task 3 — Fixture backfill — **applied on disk, not committed** (see Deviations)

`lifecycle: seed` added immediately after `content_categories:` in each of the three named
`test-ws/` card files, matching the placement in the hand-authored
`test-ws/my-construct/cards/card-global-workspace.md`. Nothing else changed — not the body, not the
other keys, not their order.

## Verification

**1. RED was demonstrated, not asserted.** Against the unmodified writer, both new tests failed, with
the exact signature the plan predicted:

```
E  AssertionError: /private/var/.../install/demo/cards/round-trip-guard-card.md is missing
   parser-required frontmatter field(s) ['lifecycle']; views generate will silently drop this card
E  assert not {'lifecycle'}

E  AssertionError: the generator produced zero cards in /private/var/.../data/demo/cards.json
E  assert []

FAILED tests/integration/test_views_generate.py::test_written_card_frontmatter_satisfies_views_parser_contract
FAILED tests/integration/test_views_generate.py::test_written_card_reaches_generated_cards_json
========================= 2 failed, 12 passed in 1.16s =========================
```

Test 1 failed on the derived subset check naming `{'lifecycle'}` and Test 2 on the non-vacuity
zero-cards floor — not on the non-vacuity floors or the `REQUIRED_FIELDS` pin, which would have meant
the wiring was wrong. Task 1's commit (`3328a09`) precedes Task 2's (`ac45d0e`).

**2. Full suite: `528 passed, 1 skipped`** — baseline 526 plus exactly the 2 new tests, zero
regressions. The archive assertions at `tests/unit/test_knowledge_operations.py:220`/`:235` and the
raw-content checks at `tests/integration/test_knowledge_cli.py:141`/`:190` stayed green.

**3. Fixture probe: `OK parsed 18 warnings 0`** — up from the measured pre-task state of 15 parsed /
3 warnings, across all three `test-ws/` workspaces.

**4. End-to-end sanity, matching the audit's reproduction.** Scaffolded a throwaway install root in a
scratch dir via `initialize_workspace`, `create_card` into its workspace, then
`construct views generate --install-root <root>`:

```
create_card: True {'id': 'end-to-end-sanity-card', ...}
--- frontmatter on disk ---
title: End to end sanity card
epistemic_type: finding
domains:
-   myws
confidence: 3
source_tier: 3
created: '2026-07-26'
author: construct
id: end-to-end-sanity-card
lifecycle: seed
--- construct views generate ---
Views data generation: build fd38487b, 11 files written, 0 validation errors, 0 content warnings
exit=0
--- cards.json ---
card ids: ['end-to-end-sanity-card']
```

The audit reproduced `11 files written, 0 validation errors, **1** content warnings` with
`{"cards": []}`. It is now `0 content warnings` with the card present. Exit code and report shape
unmoved (D-03).

**5. Diff scope.** `git diff --stat f6c5df7..HEAD` touches exactly two paths —
`src/construct/services/knowledge.py` (+8) and `tests/integration/test_views_generate.py` (+120).
Nothing under `src/construct/views/lib/`, nothing under `src/construct/llm/`, no `schemas/card.py`,
no `ROADMAP.md`, nothing under `.planning/milestones/`. The three fixture edits are on disk but
outside git (see below).

## Deviations from Plan

### 1. [Rule 4 — plan premise wrong] Task 3's three fixture files are gitignored and untracked; the backfill was applied but not committed

**Found during:** Task 3, at the commit step.

**Issue:** The plan's `<done>` criterion for Task 3 expected `git diff --stat` to show "exactly
3 files, 3 insertions, 0 deletions". It showed nothing. `.gitignore:1` is `test-ws/`, and while
31 `test-ws/` paths were force-added historically (Phases 01 and 07), these three were not:

```
test-ws/my-construct/cards/a-research-note-about-cosmology-inflation.md   -> UNTRACKED
test-ws/smoke202606201640/cards/semantic-caching-cuts-gateway-latency.md  -> UNTRACKED
test-ws/smoke202606201640/cards/token-based-rate-limiting.md              -> UNTRACKED
```

**Consequence — the D-02 premise does not hold.** An audit of every *tracked* `test-ws` card shows
**15 tracked cards, none missing `lifecycle`**. On-disk there are 18. So the repo never "shipped
three cards its own generator silently drops"; those three are local working-tree artifacts of
earlier ingest and smoke runs (`smoke202606201640` is a timestamped smoke workspace, 2026-06-20
16:40). A fresh clone already parsed 15/15 with zero warnings. The measured "15 parsed / 3 warnings"
was a property of this dev machine's working tree only.

**Action taken:** the three edits were applied on disk — the local fixtures now parse 18/0, which is
the plan's stated done-criterion and keeps this working tree honest — but **no `git add -f`**. Force
-adding paths the maintainer deliberately excluded at `.gitignore:1` would silently expand the
tracked fixture set with two smoke-run byproducts, a far larger scope violation than the backfill it
was meant to serve. No Task 3 commit exists.

**If the intent was for these fixtures to be tracked**, that is a separate decision (which of the 18
on-disk cards belong in the repo, and why `test-ws/` is ignored-with-exceptions at all) and should be
made deliberately rather than as a side effect of this quick task.

No other deviations. Tasks 1 and 2 executed exactly as written. No auto-fixes were needed; no
architectural changes were made.

## Known Consequences (deliberate, not oversights)

1. **User workspaces are not reached by this fix.** Cards already sitting in a *user's* workspace
   without `lifecycle` stay invisible to `views generate` until something re-saves them
   (`card update`, `card archive`, or a curation promotion). The fix is writer-side by design (D-01);
   there is no migration or backfill path for existing user workspaces. Recorded in STATE.md.

2. **`archive_card` destroys the card body — found, deliberately not fixed.**
   `src/construct/services/knowledge.py:327`/`:342` discards the body from `_read_card_file`
   (`_, _, raw = ...`) and calls `_card_dict_to_markdown(raw)` with `body=None`, which substitutes
   the empty canonical section template — while the sibling `edit_card:276` correctly passes
   `body=body`. Verified live during planning: a card created with
   `--summary "Important summary text."` came back from archive with an empty `## Summary`. This is
   real data loss on every archive, unrelated to the lifecycle contract and outside this task's
   boundary. The Task 2 default flows through `archive_card` (harmlessly — `:338` already sets the
   key explicitly), but its body handling was left untouched and no test was added for it. Added to
   STATE.md Blockers/Concerns.

3. **This closes one of three views data-contract forks** flagged at the v0.4.1 audit. The other two
   remain open and unowned: the `views validate` ↔ `views generate` byte mismatch (pinned by
   `test_views_validate_does_not_yet_accept_generated_bytes`, which must stay red-on-resolution) and
   the missing per-card refresh path (v0.6 OQ-3).

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change at a trust boundary
was introduced. The threat register's five entries were all discharged as planned: T-m0e-01 mitigated
by the round-trip guard, T-m0e-02 by copy-before-default, T-m0e-03 by the anti-weakening pin,
T-m0e-04/05 accepted with no new surface.

## Commits

| Task | Type | Commit | Description |
|------|------|--------|-------------|
| 1 | `test` | `3328a09` | writer-to-parser round-trip guards (RED, both failing) |
| 2 | `fix` | `ac45d0e` | card serializer always emits lifecycle frontmatter (GREEN) |
| 3 | — | *(none)* | fixture backfill applied on disk; files are gitignored/untracked |

## Self-Check: PASSED

- `src/construct/services/knowledge.py` — FOUND, contains the `setdefault` and the docstring sentence
- `tests/integration/test_views_generate.py` — FOUND, contains both new test functions and the helper
- All three `test-ws/` fixture files — FOUND on disk, each carrying `lifecycle: seed` after
  `content_categories:` (untracked by design, see Deviations)
- Commit `3328a09` — FOUND in `git log`
- Commit `ac45d0e` — FOUND in `git log`
- Full suite re-run after all three tasks: `528 passed, 1 skipped`
