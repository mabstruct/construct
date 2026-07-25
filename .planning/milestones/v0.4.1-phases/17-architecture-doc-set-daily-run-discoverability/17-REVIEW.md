---
phase: 17-architecture-doc-set-daily-run-discoverability
reviewed: 2026-07-25T18:06:22Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md
  - CONSTRUCT-CLAUDE-spec/architecture-overview.md
  - CONSTRUCT-CLAUDE-spec/artifact-catalog.md
  - CONSTRUCT-CLAUDE-spec/README_FIRST.md
  - CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md
  - tests/contract/test_artifact_catalog.py
  - tests/contract/test_skill_migration.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-07-25T18:06:22Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 17 is a documentation-truth phase: a large rewrite of `architecture-overview.md` to the L0–L4 layer vocabulary, a +112-line runtime-capabilities section added to `artifact-catalog.md`, a new `construct-daily-cycle/SKILL.md` thin orchestrator, two small spec fixes (`README_FIRST.md`, `spec-v04-agentworkflows.md`), a new introspection guard (`test_artifact_catalog.py`), and one enrollment added to `test_skill_migration.py`.

I verified the load-bearing facts against the live codebase rather than trusting the prose:

- **Counts are accurate.** Registry = 28 capabilities, 22 MCP tools, 34 Typer leaves, 26 caps with a `cli_name`, 25 `construct-*` skill dirs — all match the catalog and the test docstring exactly.
- **Cross-references resolve.** Every ADR/spec/reference/workflow/agent path cited in the reviewed docs exists on disk, with **one exception** (VERSION, IN-01). The `README_FIRST.md` change specifically *fixed* a dangling `config-topology.md` link.
- **The two contract test files pass** (20/20 green) and their vacuity meta-guards are genuinely non-degenerate — the introspection sources and the doc extractor are both asserted non-empty against known anchors, so the subset guards cannot pass on an empty set. No vacuous guard was found.
- **The `construct-daily-cycle` SKILL.md** frontmatter (`Read, Bash(construct), MCP(connect)`) satisfies the migration guard, and its non-blocking narrative is consistent with `daily-cycle.md` and `architecture-overview.md` §3.2.

The defects that remain are internal-consistency/staleness issues, not correctness failures. The most substantive (WR-01) is a self-contradiction introduced in this phase: the catalog's new section promises "no hand-typed counts" while introducing three hand-typed, guard-unenforced counts in the same edit.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Catalog claims "no hand-typed counts" but this phase adds three that the guard does not enforce

**File:** `CONSTRUCT-CLAUDE-spec/artifact-catalog.md:77` and `:124-126`
**Issue:** The runtime-capabilities section added in this phase asserts (line 76–78):

> "No count in this file is a frozen hand-typed integer; whatever the code registers at run time is what the guard enforces."

Yet the same added block hard-codes cardinalities in prose (lines 124–126):

> "the registry (**28 caps / 22 MCP tools**) and the Typer app (**34 leaves**) are two distinct sources…"

Both the claim and the counts were introduced in this phase's diff (confirmed via `git diff`). The four guards in `test_artifact_catalog.py` are all `introspected <= documented` **set-membership** checks — none of them compares *cardinality*. So adding a 29th capability (with its row) keeps every guard green while the prose "28 caps" silently rots. This reintroduces exactly the "rot clock" the section claims to have eliminated, and directly contradicts the file's own blanket statement.
**Fix:** Either drop the specific integers, e.g.
```
> …the registry and the Typer app are two distinct sources, and this table
> documents the gap between them explicitly…
```
or scope the promise so it is truthful, e.g. change line 77 to "No count in the **runtime-capability row tables** below is a frozen hand-typed integer" and explicitly flag the 28/22/34 figures as non-enforced illustrative snapshots.

### WR-02: `test_skill_migration.py` module docstring is stale after the daily-cycle enrollment

**File:** `tests/contract/test_skill_migration.py:23-27`
**Issue:** This phase added `"construct-daily-cycle"` to `_MIGRATED_SKILLS` (now 5 skills), but the module docstring was not updated and now misdescribes the suite on two points:
1. "Current scope: the three Phase 12 skills plus `construct-synthesis`" — describes 4 skills; the tuple now has 5 (daily-cycle is unmentioned).
2. "Status: **RED** for `construct-synthesis`, which still carries `WebSearch` / `WebFetch`; those grants are removed in Plan 16-04, at which point the suite turns fully GREEN."

The suite is now fully GREEN (verified: 20/20 pass, `construct-synthesis` no longer carries the forbidden tools). A future reader of this docstring is told the suite is RED and mid-migration when it is neither. Stale narrative in a contract test misleads the next maintainer about invariant status.
**Fix:** Update the docstring to enumerate all five skills (add `construct-daily-cycle`, Phase 17) and change the status line to note the suite is fully GREEN — the `construct-synthesis` grants were removed in Phase 16 and daily-cycle shipped thin in Phase 17.

## Info

### IN-01: Dangling reference to a non-existent `VERSION` file

**File:** `CONSTRUCT-CLAUDE-spec/architecture-overview.md:291`
**Issue:** §9.4 lists `../CONSTRUCT-CLAUDE-impl/VERSION — global version marker`, but no `VERSION` file exists in `CONSTRUCT-CLAUDE-impl/` (`ls` confirms absent; only match in-tree is an unrelated `useVersionFlag.js`). This is **pre-existing** — the line was present at the diff base and was not touched by this phase — but the file was substantially rewritten here and every other cross-reference in it resolves, so this is the lone dangling link in an otherwise clean reference set.
**Fix:** Either add a `CONSTRUCT-CLAUDE-impl/VERSION` file (the impl already ships `AGENTS.md`, `README.md`, `USER_GUIDE.md`) or drop/repoint the bullet to the actual version marker.

### IN-02: `## Agents (2)` header lists three table rows

**File:** `CONSTRUCT-CLAUDE-spec/artifact-catalog.md:187`
**Issue:** The header reads "Agents (2)" but the table beneath it has three rows (CONSTRUCT orchestrator, Curator, Researcher). The "(2)" evidently counts the two sub-role files under `claude/agents/` (curator.md, researcher.md), with the orchestrator listed for context — but the header count and the visible row count disagree, which reads as a stale count. **Pre-existing** (section not modified in this phase). Note this header count is also *not* guard-checked, reinforcing WR-01.
**Fix:** Clarify the header, e.g. "## Agents (2 sub-roles + orchestrator)", or move the CONSTRUCT row into a separate note.

### IN-03: Test docstring hard-codes illustrative counts while claiming it hard-codes none

**File:** `tests/contract/test_artifact_catalog.py:34-37`
**Issue:** The docstring states "Counts are never hand-typed here. The live figures (28 capabilities / 22 MCP tools / 34 CLI leaves / 25 skills as of Phase 17) … this module hardcodes none of them." All four numbers are correct today (verified against the live registry/glob), and the actual assertions use bounds (`> 25`, `> 20`) plus set membership rather than these exact values — so the claim is *technically* true of the test logic. But the numbers are nonetheless written verbatim in the prose and carry the same rot risk as WR-01 if the surface grows. Low concern; flagged for consistency with the WR-01 theme.
**Fix:** Optional — annotate the parenthetical as an illustrative snapshot ("as of Phase 17, non-enforced"), which the "as of Phase 17" phrasing already half-does.

---

_Reviewed: 2026-07-25T18:06:22Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
