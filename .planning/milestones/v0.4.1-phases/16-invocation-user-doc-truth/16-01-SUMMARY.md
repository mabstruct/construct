---
phase: 16-invocation-user-doc-truth
plan: 01
subsystem: testing
tags: [pytest, contract-tests, typer, frontmatter, guard-vacuity]

# Dependency graph
requires:
  - phase: 12-skill-migration
    provides: test_skill_migration.py and its single-line allowed-tools parser
  - phase: 14-doc-invocation-guard
    provides: test_doc_command_references.py, _DOC_GLOBS, _invocations, _KNOWN_BROKEN
provides:
  - Per-document non-vacuity guard (_MUST_CARRY_INVOCATIONS + test_key_docs_are_not_vacuous), resolved independently of _DOC_GLOBS
  - knowledge card list pinned into test_command_surface_is_discoverable
  - Multi-dialect allowed-tools frontmatter parser (_allowed_tools_text) plus its meta-guard
  - construct-synthesis brought into _MIGRATED_SKILLS scope
affects: [16-03 card list, 16-04 synthesis grant removal, 16-05 CLI invocation columns, 16-07 doc glob widening]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Meta-guard convention: every static guard carries an assertion that it is still looking at non-empty input"
    - "Glob-independent document assertions: a named doc set is read from _REPO_ROOT so shrinking the scan surface cannot silence the guard"

key-files:
  created: []
  modified:
    - tests/contract/test_doc_command_references.py
    - tests/contract/test_skill_migration.py

key-decisions:
  - "Kept test_docs_contain_invocations alongside the new per-doc guard — global regex coverage and per-doc coverage are complements, not substitutes"
  - "Fixed the frontmatter parser rather than reshaping construct-synthesis's list-style frontmatter, per the orchestrator's carried-forward decision"
  - "Line-oriented continuation scan instead of a YAML dependency — keeps the guard dependency-free"
  - "_allowed_tools_text keeps the (str) -> str signature so both existing consumers work unchanged via substring containment"

patterns-established:
  - "Guard-vacuity discipline: prove a guard can go RED before changing the subject it guards"
  - "Asymmetric parametrization as proof-of-capability: a mixed pass/fail split across cases demonstrates the assertion discriminates"

# This plan CONTRIBUTES to FIX-03, DOC-04 and DEC-01 but completes none of them — it only
# lays the RED guards. They are closed by 16-03/16-05 (FIX-03), 16-05/16-07 (DOC-04) and
# 16-04 (DEC-01). See "Deviations from Plan" below.
requirements-completed: []
requirements-advanced: [FIX-03, DOC-04, DEC-01]

coverage:
  - id: D1
    description: "_MUST_CARRY_INVOCATIONS (3 entries) plus test_key_docs_are_not_vacuous, resolved against _REPO_ROOT independently of _DOC_GLOBS, with a loud is-file assertion for missing paths"
    requirement: DOC-04
    verification:
      - kind: other
        ref: "pytest tests/contract/test_doc_command_references.py::test_key_docs_are_not_vacuous -v — 3 params, 1 passed / 2 failed as designed"
        status: pass
      - kind: other
        ref: "python -c 'from tests.contract.test_doc_command_references import _MUST_CARRY_INVOCATIONS as m; assert len(m)==3'"
        status: pass
      - kind: unit
        ref: "tests/contract/test_doc_command_references.py::test_docs_contain_invocations (global guard preserved)"
        status: pass
    human_judgment: false
  - id: D2
    description: "knowledge card list pinned into test_command_surface_is_discoverable, with _resolves() and the len(VALID_PATHS) > 25 lower bound untouched"
    requirement: FIX-03
    verification:
      - kind: other
        ref: "pytest ...::test_command_surface_is_discoverable — exits 1, assertion names ('knowledge','card','list')"
        status: pass
      - kind: other
        ref: "inspect.getsource(_resolves) contains 'any(path[:i] in LEAF_COMMANDS'; getsource(test_command_surface_is_discoverable) contains 'len(VALID_PATHS) > 25'"
        status: pass
    human_judgment: false
  - id: D3
    description: "_allowed_tools_text reads both frontmatter dialects; construct-synthesis in _MIGRATED_SKILLS; test_allowed_tools_text_is_not_vacuous meta-guard"
    requirement: DEC-01
    verification:
      - kind: unit
        ref: "tests/contract/test_skill_migration.py::test_allowed_tools_text_is_not_vacuous (4 params, all pass)"
        status: pass
      - kind: unit
        ref: "tests/contract/test_skill_migration.py::test_skill_still_delegates_to_cli (4 params inc. synthesis, all pass)"
        status: pass
      - kind: other
        ref: "_allowed_tools_text('construct-synthesis') contains WebSearch and Bash(construct); _allowed_tools_text('construct-gap-analysis') contains zero newlines"
        status: pass
      - kind: other
        ref: "pytest ...::test_skill_drops_forbidden_tools -v — 3 passed, 1 failed (construct-synthesis), the designed RED"
        status: pass
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-07-20
status: complete
---

# Phase 16 Plan 01: Wave 0 RED Guards Summary

**Three guards made provably capable of failing — per-document invocation non-vacuity, `knowledge card list` discoverability, and a multi-dialect `allowed-tools` parser — all RED before the changes they guard land**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-20T15:07:50Z
- **Completed:** 2026-07-20T15:10:59Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Closed RESEARCH Pitfall 2: `test_docs_contain_invocations` asserts a repo-wide total, so a newly-globbed document whose CLI column the extractor misses would sail through on an empty set. `_MUST_CARRY_INVOCATIONS` now asserts three named documents individually non-vacuous, read from `_REPO_ROOT` rather than through `_doc_files()` — which is what lets the guard fail *now*, for documents `_DOC_GLOBS` does not yet scan.
- Closed RESEARCH Pitfall 4: `_allowed_tools_line()` read a single line, so adding the list-style `construct-synthesis` to `_MIGRATED_SKILLS` would have returned a bare `allowed-tools:` and made every forbidden-tool assertion pass unconditionally. The parser now consumes trailing YAML list items, and `test_allowed_tools_text_is_not_vacuous` makes that failure mode impossible to reintroduce silently.
- Pinned `knowledge card list` into the discoverability meta-guard without touching `_resolves()` or converting the `> 25` lower bound into an equality.

## Expected failing test ids (the deliverable of this plan)

This plan ends deliberately RED. These four ids are expected to fail, and each turns green in a specific later plan:

| Failing test id | Turns green in |
|---|---|
| `test_key_docs_are_not_vacuous[CONSTRUCT-CLAUDE-impl/USER_GUIDE.md]` | 16-05 (CLI-invocation column) |
| `test_key_docs_are_not_vacuous[CONSTRUCT-CLAUDE-impl/construct/references/commands.md]` | 16-05 (CLI-invocation column) |
| `test_command_surface_is_discoverable` | 16-03 (`knowledge card list` registered) |
| `test_skill_drops_forbidden_tools[construct-synthesis]` | 16-04 (`WebSearch`/`WebFetch` grants removed) |

Passing case that proves the doc guard discriminates rather than failing blanket-wide: `test_key_docs_are_not_vacuous[USER-TEST-PLAYBOOK-v03.md]`.

Signature pair proving the frontmatter parser genuinely reads the grants: `test_skill_drops_forbidden_tools[construct-synthesis]` FAILS while `test_skill_still_delegates_to_cli[construct-synthesis]` PASSES — both read the same string, so a vacuous parser could not produce that split.

## Task Commits

1. **Task 1: Per-doc non-vacuity guard** - `d770d7c` (test)
2. **Task 2: Pin `knowledge card list` into discoverability** - `39623dd` (test)
3. **Task 3: Multi-line frontmatter parser + synthesis in scope** - `8e1f7a2` (test)

## Files Created/Modified

- `tests/contract/test_doc_command_references.py` - Added `_MUST_CARRY_INVOCATIONS` and `test_key_docs_are_not_vacuous`; added the `knowledge card list` assertion to `test_command_surface_is_discoverable`. `_resolves()`, `_DOC_GLOBS`, `_KNOWN_BROKEN`, and `test_docs_contain_invocations` unchanged.
- `tests/contract/test_skill_migration.py` - Renamed `_allowed_tools_line` to `_allowed_tools_text` with list-item continuation scanning; added `construct-synthesis` to `_MIGRATED_SKILLS`; added `test_allowed_tools_text_is_not_vacuous`; rewrote the stale Phase 12 module docstring.

## Decisions Made

- **Kept `test_docs_contain_invocations`.** It guards the extractor regex globally; the new test guards per-document coverage. Deleting the global one to "replace" it would reopen the regex-regression hole.
- **Fixed the parser, not the data.** `construct-synthesis`'s list-style frontmatter stays as authored; the parser learned the second dialect. Per the orchestrator's carried-forward decision.
- **No YAML dependency.** A line-oriented continuation scan is sufficient and keeps the guard dependency-free.
- **Signature preserved.** `_allowed_tools_text` still returns `str`, so both pre-existing consumers work unchanged via substring containment over a longer string.

## Deviations from Plan

The three code tasks were executed exactly as written. One deviation occurred in the state-update step.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reverted premature requirement completion in REQUIREMENTS.md**
- **Found during:** State updates, after the three task commits
- **Issue:** The plan's `requirements:` frontmatter lists `[FIX-03, DOC-04, DEC-01]`, and the standard state-update step marks every such ID complete. Doing so here made the traceability matrix assert three false things: FIX-03's own stated completion condition is "`_KNOWN_BROKEN` is **empty** with the suite green" and it still holds four entries; DEC-01 requires `construct-synthesis`'s `WebSearch` / `WebFetch` grants to be gone, and this plan deliberately leaves them in place as the RED condition; DOC-04 requires the user-facing docs to carry invocations, which is precisely what two of this plan's assertions currently fail on. A guard that proves a requirement is unmet cannot also mark it met.
- **Fix:** Reverted `.planning/REQUIREMENTS.md` (three checkboxes back to `- [ ]`, three matrix rows back to `Pending`). Set `requirements-completed: []` in this SUMMARY and recorded the targeted IDs under a separate `requirements-advanced` key so the linkage is preserved without the false completion claim.
- **Files modified:** `.planning/REQUIREMENTS.md` (net zero — reverted to its pre-plan state)
- **Verification:** `git checkout -- .planning/REQUIREMENTS.md`; the three IDs read `- [ ]` / `Pending` as before.
- **Committed in:** the plan-metadata commit (no net change to REQUIREMENTS.md appears in it)

---

**Total deviations:** 1 auto-fixed (1 bug — false completion claim in the traceability matrix)
**Impact on plan:** None on the delivered code. The correction keeps FIX-03, DOC-04 and DEC-01 available for the plans that genuinely close them. **Later plans in this phase must mark these IDs complete**, since 16-01 no longer does: FIX-03 and DOC-04 at 16-07 (the last plan touching both), DEC-01 at 16-04.

## Prohibitions — verification status

All four prohibitions in the plan frontmatter were held, and three are mechanically verified rather than merely asserted:

- `_DOC_GLOBS` / `_MUST_CARRY_INVOCATIONS` entries dropped to silence a failure — **held**; `_DOC_GLOBS` is byte-unchanged in the diff, and `_MUST_CARRY_INVOCATIONS` was added, not substituted.
- `_resolves()` loosened — **held**; verified by `inspect.getsource` assertion in the acceptance run.
- `len(VALID_PATHS) > 25` converted to equality — **held**; verified by `inspect.getsource` assertion.
- `construct-synthesis` frontmatter reshaped — **held**; `git diff --name-only` after Task 3 listed only `tests/contract/test_skill_migration.py`, never the SKILL.md.

## Issues Encountered

None. The empirically observed failure set matched the plan's prediction exactly, including the arithmetic: baseline 489 passed → 494 passed + 4 failed (the 5 new passing cases are the playbook non-vacuity case plus the 4 meta-guard cases).

## Threat mitigations applied

- **T-16-01** (Tampering, `_DOC_GLOBS` / `_KNOWN_BROKEN`): mitigated. `_MUST_CARRY_INVOCATIONS` resolves against `_REPO_ROOT`, so shrinking the scan surface cannot silence it.
- **T-16-05** (Elevation of Privilege, `construct-synthesis` web-egress grants): mitigated. The multi-line parser plus the non-vacuity meta-guard make the forbidden-tool assertion capable of failing; it currently does.
- **T-16-SC** (supply chain): not applicable — zero packages installed, `pyproject.toml` untouched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three guards are in place and RED, so 16-03, 16-04, and 16-05 each have an unambiguous, pre-identified assertion to turn green.
- 16-07 widens `_DOC_GLOBS` to include `USER_GUIDE.md` and `commands.md`. Note the ordering constraint that survives into that plan: once globbed, those documents also come under `test_documented_commands_resolve`, so the CLI-invocation columns 16-05 adds must resolve, not merely exist.
- No other test in the repository changed status.

## Self-Check: PASSED

---
*Phase: 16-invocation-user-doc-truth*
*Completed: 2026-07-20*
