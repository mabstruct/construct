---
phase: 15-views-generate-data-resolution
plan: 01
subsystem: infra
tags: [packaging, hatchling, pyyaml, imports, vendoring, views]

requires:
  - phase: 14
    provides: views data-contract models and generator pipeline this plan makes importable
provides:
  - "`construct.views.lib` package — 15 vendored views source parsers shipped inside the distribution"
  - "`construct.views.generate` importable from an installed package with no interpreter-search-path mutation"
  - "`pyyaml>=6` as a declared runtime dependency of the `construct` distribution"
  - "Warning strings that name each source file exactly once (Pitfall 4 fix)"
  - "3 unit tests that go red if the skill-directory coupling is reintroduced"
affects: [15-02, 15-03, 15-04, 15-05, views, packaging]

tech-stack:
  added: [pyyaml]
  patterns:
    - "Vendor-by-git-mv: move deployed skill code into the shipped package with history preserved, changing import lines only"
    - "Coupling guard tests: assert the module search path is unmutated after import and that forbidden path literals are absent from source"

key-files:
  created:
    - src/construct/views/lib/__init__.py
    - src/construct/views/lib/discover.py
    - src/construct/views/lib/fingerprint.py
    - src/construct/views/lib/parse_domains.py
    - src/construct/views/lib/frontmatter.py
    - tests/unit/test_views_lib_imports.py
  modified:
    - src/construct/views/generate.py
    - pyproject.toml

key-decisions:
  - "Flat module set under `construct/views/lib/` — no `parsers/` subpackage, since 4 of the 14 modules are not parsers"
  - "Intra-package imports kept in explicit-relative form (`from .frontmatter import parse as parse_frontmatter`) — this is what the originals already used, so zero import lines needed changing"
  - "F6 Option A: declare `pyyaml>=6` rather than port the vendored parsers to ruamel.yaml, preserving D-08's move-not-a-rewrite invariant"
  - "Warning doubling fixed in the generate.py formatter, not in the parsers — the parsers' workspace-qualified `file` key is self-consistent and D-08 forbids altering parser behaviour"
  - "RESEARCH assumption A5 confirmed: `hatch_build.py` only stamps `_build.py` and does not filter subpackages; no packaging-config change was needed"

patterns-established:
  - "Verbatim-move discipline: a rename-detecting `git diff -M` across the move must show near-zero changed lines (this move: 1 line, the new package docstring)"
  - "Mutation-check a guard test before trusting it: reintroduce the defect, confirm red, revert"

requirements-completed: [FIX-01]

coverage:
  - id: D1
    description: "15 views modules vendored into `src/construct/views/lib/` with git history preserved and no behavioural change"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/unit/test_views_lib_imports.py#test_views_lib_modules_all_importable"
        status: pass
      - kind: other
        ref: "git diff -M --summary HEAD~1 HEAD | grep -c rename == 14; total changed lines == 1"
        status: pass
      - kind: other
        ref: "grep -rn 'yaml\\.load(' src/construct/views/ returns nothing (T-15-01)"
        status: pass
    human_judgment: false
  - id: D2
    description: "`generate.py` imports from `construct.views.lib` with no interpreter-search-path mutation and no skill-directory literal"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/unit/test_views_lib_imports.py#test_views_lib_imports_without_path_mutation"
        status: pass
      - kind: unit
        ref: "tests/unit/test_views_lib_imports.py#test_generate_module_declares_no_skill_directory_path"
        status: pass
      - kind: other
        ref: "cd /tmp && .venv/bin/python -c 'import construct.views.generate' exits 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "`pyyaml>=6` declared and a built wheel ships `construct/views/lib/` with all 15 files"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "uv build --wheel: 15 entries match construct/views/lib/*.py; METADATA carries Requires-Dist: pyyaml>=6"
        status: pass
    human_judgment: false
  - id: D4
    description: "Generation warnings no longer double the leading workspace segment (Pitfall 4)"
    verification:
      - kind: other
        ref: "scaffolded workspace + generate(root): no warning matches ^([^/]+)/\\1/ — vacuously true, the fresh workspace emitted zero warnings"
        status: unknown
    human_judgment: true
    rationale: "The harness workspace produced no warnings at all, so the fix is verified by code inspection only. A workspace with malformed card frontmatter is needed to exercise the formatter branch end-to-end."

duration: 21min
completed: 2026-07-19
status: complete
---

# Phase 15 Plan 01: Vendor the views library into the shipped package Summary

**The 15-module views parser library now ships inside `construct.views.lib` with git history intact, so `construct.views.generate` imports cleanly from an installed wheel instead of reaching into a deployed skill directory via an interpreter-search-path hack.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-07-19T21:32:00Z
- **Completed:** 2026-07-19T21:53:00Z
- **Tasks:** 3
- **Files modified:** 18 (15 moved, 2 modified, 1 created)

## Accomplishments

- Moved all 15 modules from `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/lib/` to `src/construct/views/lib/` with `git mv`; `git diff -M` detects 14 renames and the entire move changed exactly **1 line** (the new package docstring), satisfying threat T-15-02's drift control.
- Deleted the `_PROJECT_ROOT` / `_SKILL_LIB` path-injection block and the orphaned `wrong-import-position` / `E402` / `type: ignore` suppressions from `generate.py`, replacing them with a normal top-of-module `from construct.views.lib import (...)` carrying a D-08 decision-ID comment.
- Fixed Pitfall 4 in the warning formatter: the workspace id is now prepended only when the parser's `file` value does not already lead with it.
- Declared `pyyaml>=6` and verified by wheel inspection that `construct/views/lib/` ships with all 15 files and that `Requires-Dist: pyyaml>=6` reaches the metadata.
- Added `tests/unit/test_views_lib_imports.py` (3 tests), then mutation-checked it — reintroducing a search-path insertion turned 2 of the 3 red, confirming the guard has teeth.

## Task Commits

1. **Task 1: Move the 15 skill-lib modules into `src/construct/views/lib/` verbatim** — `091717b` (refactor)
2. **Task 2: Delete the skill-directory path injection and fix the doubled warning path** — `5fa32fd` (refactor)
3. **Task 3: Declare PyYAML, verify wheel inclusion, guard the coupling with a unit test** — `12a3ec9` (feat)

## Files Created/Modified

- `src/construct/views/lib/*.py` (15 files) — vendored views source parsers; `__init__.py` gained a one-line D-08 docstring, the other 14 are byte-identical to their originals
- `src/construct/views/generate.py` — package-rooted import block, path injection removed, warning formatter de-doubled
- `pyproject.toml` — `pyyaml>=6` inserted between `pydantic>=2.7` and `ruamel.yaml>=0.18`
- `tests/unit/test_views_lib_imports.py` — 3 coupling-guard tests

## Decisions Made

- **Import form: explicit-relative, chosen by inspection rather than by fiat.** The plan asked me to pick one form and apply it consistently. The originals already used `from .frontmatter import parse as parse_frontmatter` in `parse_articles.py`, `parse_cards.py`, and `parse_digests.py`, and no module used a skill-directory-absolute or implicit-relative import. Keeping the existing form meant **zero import lines had to change** inside the 14 moved modules — the strongest possible outcome for D-08's move-not-a-rewrite invariant.
- **RESEARCH assumption A5 resolved: no packaging change needed.** `hatch_build.py` defines a single `StampBuildHook.initialize` that writes `src/construct/_build.py`; it performs no file selection or filtering. `packages = ["src/construct"]` picked up the new subpackage automatically because `views/lib/__init__.py` exists.
- **Layout: flat module set, no `parsers/` subpackage**, per the plan's resolved discretion item.

## Deviations from Plan

### Acceptance-criterion arithmetic

**1. Line-count criterion off by one, by design**
- **Found during:** Task 1
- **Detail:** The criterion `wc -l src/construct/views/lib/*.py | tail -1` reports `1496` conflicts with the same task's instruction to add a one-line docstring to the previously-empty `__init__.py`. Actual total is **1497**.
- **Resolution:** Followed the instruction, not the arithmetic. The 14 non-`__init__` modules total 1496 lines unchanged; the extra line is the mandated docstring.

**2. Rename-detection criterion needed an unfiltered diff**
- **Found during:** Task 1
- **Detail:** `git diff -M --stat HEAD~1 -- src/construct/views/lib/` cannot show renames, because the path filter excludes the deletion side of each pair, so it reports 1498 insertions. Running the same diff without the path filter shows 14 renames and 1 insertion.
- **Resolution:** Verified with the unfiltered diff plus `git log --follow src/construct/views/lib/parse_bridges.py` (4 commits — history preserved).

### Auto-fixed Issues

**3. [Rule 3 - Blocking] Restored a dropped import during the Task 2 edit**
- **Found during:** Task 2
- **Issue:** My first edit to the import block accidentally consumed the adjacent `from construct.views.models import (...)` statement along with the path-injection block being deleted.
- **Fix:** Re-added the models import immediately, placed after the new `construct.views.lib` import to keep the group alphabetical.
- **Verification:** Full suite green at 443 passing (the pre-existing baseline) before committing Task 2.
- **Committed in:** `5fa32fd` — the defect never reached a commit.

---

**Total deviations:** 1 auto-fixed (blocking), 2 acceptance-criterion clarifications.
**Impact on plan:** No scope creep. Every prohibition held: no parser was rewritten, reformatted, or had its YAML loader touched.

## Issues Encountered

- **`generate()` on a fresh workspace reports `success: False`** with `bridges.json: summary.top_domain_pairs — Extra inputs are not permitted`. This is the **pre-existing parser/model mismatch that Plan 02 exists to reconcile**, not a regression from this plan — it is a Pydantic contract disagreement in `views/models.py`, and this plan changed no model and no parser. Confirms Plan 02's premise from the generator side.
- **Pitfall 4 fix could not be exercised end-to-end.** The scaffolded harness workspace emits zero warnings, so the doubled-segment assertion passed vacuously. The fix is correct by inspection (guarded on `f == ws or f.startswith(f"{ws}/")`) but has no live coverage. Flagged as `human_judgment: true` in the coverage block above.
- **`uv build` rewrites `src/construct/_build.py`** as a side effect of the stamp hook. Reverted with `git checkout` so the stamp did not leak into a task commit.

## v0.6 Backlog Item

**Port the vendored views parsers from PyYAML to ruamel.yaml for convention consistency (F6 Option B).** The rest of the codebase standardises on `ruamel.yaml>=0.18`; `views/lib/frontmatter.py` and `views/lib/parse_domains.py` are now the only PyYAML consumers. F6 Option A was chosen for this phase specifically because rewriting the loader calls would have violated D-08's move-not-a-rewrite invariant, which D-02's parsers-are-ground-truth rule depends on. Once Plan 02 has reconciled the models against the parsers, that invariant is discharged and the port becomes safe.

## User Setup Required

None — `pyyaml` 6.0.3 was already resolved in the live venv transitively via `langchain-core`; declaring it adds no new code to the environment.

## Next Phase Readiness

- **Plans 02–05 are unblocked.** Every one of them depends on `construct.views.generate` being importable from an installed package; that now holds, verified from a directory outside the checkout.
- **Plan 02 (model reconciliation)** should start from the `bridges.json` `top_domain_pairs` mismatch documented above — it is a live, reproducible instance of the disagreement Plan 02 targets.
- **Plan 05 (D-09)** still owns the skill directory's `generate.py`, `run.sh`, `requirements.txt`, `debounced_hook.py`, `debounced-hook.sh`, and `SKILL.md`, all of which were deliberately left untouched. Note that the skill's `generate.py` still expects a sibling `lib/` that no longer exists — Plan 05 must resolve that dangling reference.

---
*Phase: 15-views-generate-data-resolution*
*Completed: 2026-07-19*
