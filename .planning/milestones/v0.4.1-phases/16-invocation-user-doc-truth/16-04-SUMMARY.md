---
phase: 16-invocation-user-doc-truth
plan: 04
subsystem: claude-skills
tags: [skill-migration, allowed-tools, doc-truth, spec-hygiene]
status: complete
requires:
  - "16-01 (made test_skill_drops_forbidden_tools[construct-synthesis] capable of failing)"
  - "16-03 (shipped `knowledge card list`, so the surviving invocation resolves)"
provides:
  - "construct-synthesis with no web-egress grants"
  - "_KNOWN_BROKEN down to the two `workflow` entries"
  - "spec-v04 migration-fallback row marked discharged"
affects:
  - "16-06 (owns the two remaining _KNOWN_BROKEN workflow entries — FIX-03 closes there)"
tech-stack:
  added: []
  patterns: ["static frontmatter guard", "shrink-only allowlist"]
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md
    - tests/contract/test_doc_command_references.py
    - CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md
    - .planning/REQUIREMENTS.md
decisions:
  - "construct-gap-analysis/SKILL.md left untouched — its invocations already resolve; no diff manufactured"
  - "FIX-03 reverted to Pending: marked Complete by 16-03 while its own mechanical criterion (empty _KNOWN_BROKEN) is unmet"
requirements-completed: [DEC-01]
metrics:
  duration: ~12m
  completed: 2026-07-20
---

# Phase 16 Plan 04: Synthesis Web-Grant Removal & refs/ Rewrite Summary

`construct-synthesis` no longer declares `WebSearch`/`WebFetch`, its `refs/` lookup runs on
`Read` instead of a sub-app that does not exist, and the spec row that mandated the removal
records its own discharge.

## What Changed

| Task | Change | Commit |
|------|--------|--------|
| 1 | Dropped `WebSearch`/`WebFetch` from `allowed-tools` | `2b0e91e` |
| 2 | Rewrote Step 2's `refs/` lookup onto `Read`; deleted the `("knowledge","ref","list")` allowlist entry | `6cde651` |
| 3 | Marked the spec's migration-fallback row discharged | `12c2ffe` |

**Task 1.** The two grants appeared only in frontmatter. A full read of the body confirmed
RESEARCH's grep finding: no procedure step, failure-mode row, or checklist item depends on web
access, so removal is a dead-declaration cleanup rather than a capability reduction. `Read`,
`Bash(construct)` and `MCP(connect)` survive, and the list-style dialect was preserved rather
than collapsed to inline — 16-01 fixed the parser so the data would not have to be reshaped to
fit the test. `test_skill_drops_forbidden_tools[construct-synthesis]`, RED since 16-01, is green;
`test_skill_migration.py` is fully green across all four skills (12 passed).

**Task 2.** Step 2's second fenced block invoked `construct knowledge ref list`, a `ref` sub-app
that does not exist and, per D-03, will not be built. The step's intent — also consult `refs/`
for supporting references — is preserved; only the mechanism changed. Reference entries are
plain JSON files (one per source, per `AGENTS.md`), so the step now instructs `Read` over the
domain workspace's `refs/` directory, scoped to the domain under synthesis. `Read` was already
granted and survives Task 1, so closing the web grants introduced no new tool requirement.

The surviving card-enumeration invocation, `construct knowledge card list --domain <domain>
--json`, needed no flag correction: 16-03 shipped `--domain/-d` and `--json/-j`, matching what
the skill already wrote. It remains on one line (the extractor's `[ \t]+` will not match a
wrapped command). The failure-mode row and the validation checklist item that reference card
enumeration were checked and are correct as written.

Step 7 (views refresh) was not touched. It is an exemption recorded in
`adr-0005-views-refresh-ownership.md` — synthesis has no `synthesis.run` capability, so there is
no Python entry point to hang a refresh on, and without the step a synthesis never reaches the
SPA. It resembles Phase 15 cleanup residue and is not.

**`construct-gap-analysis/SKILL.md` needed no edit.** All three of its invocations
(`knowledge card list --workspace . --json`, `knowledge connection list --workspace . --json`,
`status --workspace . --json`) resolve against the live Typer app unchanged, verified
programmatically via `_invocations`/`_resolves`. No diff was manufactured.

The `("knowledge","ref","list")` allowlist deletion is legitimate under D-16 specifically because
the broken string left a document that **remains** in `_DOC_GLOBS` (still 3 entries) — the file
is still scanned, so the guard proves the string is gone rather than merely unwatched.

**Task 3.** The exact wording written into the search-provider table's migration-fallback row:

> **Discharged (Phase 16 / DEC-01).** `research.run` shipped in Phase 10; the
> `WebSearch`/`WebFetch` grants were removed from `construct-synthesis`'s `allowed-tools`, the
> last skill still carrying them. `test_skill_drops_forbidden_tools` keeps them out. Retained
> here for the fallback rationale, not as a live instruction.

The row was kept rather than deleted — a deleted row loses the reasoning; a discharged row keeps
it and closes it. `git diff --numstat` confirms exactly 1 line added, 1 removed. The
`model-routing` reference count is unchanged at 2, so the D-15 fence to Phase 17 holds.

## Prohibition Verification

| Prohibition | Status | Evidence |
|---|---|---|
| `refs/` step not silently deleted | verified | Intent sentence retained, mechanism moved to `Read`; `grep -ci 'refs/'` = 4 |
| Step 7 views-refresh not removed | verified | `grep -c 'adr-0005-views-refresh-ownership'` = 1 |
| Model-routing lines untouched | verified | `grep -c 'model-routing'` = 2 before and after |
| No grant removed while body depends on it | verified | Full body read + RESEARCH grep: zero references outside frontmatter |

## Requirement Traceability — action taken beyond plan frontmatter

**DEC-01 marked complete.** Per the hand-off from 16-01, this plan is what actually discharges
it. Both the checkbox and the traceability row now read complete, attributed to 16-04.

**FIX-03 reverted to Pending (deviation, Rule 1).** It was marked `[x]` / `Complete` by 16-03
(commit `7f86df4`), but its own mechanical completion criterion in `REQUIREMENTS.md:89` states it
is complete when `_KNOWN_BROKEN` is **empty**. The allowlist still holds two `workflow` entries
that 16-06 owns. FIX-03 is listed in this plan's frontmatter, so its status is in scope, and a
requirement claiming completion its evidence does not support is precisely the rot this milestone
exists to clear. The traceability row now names the blocking condition and the owning plan.

**DOC-04 is also falsely marked Complete — flagged, not edited.** Both
`test_key_docs_are_not_vacuous` cases (`USER_GUIDE.md`, `commands.md`) still fail, and those
documents are 16-05's work. DOC-04 is not in this plan's frontmatter, so it was left for the
orchestrator to route rather than edited here.

## Test State

Entry: 513 passed, 3 failed. Exit: **513 passed, 2 failed**. The target test is green and no new
failures were introduced. The two remaining failures are the `test_key_docs_are_not_vacuous`
cases owned by 16-05. The passed count is unchanged because one `_KNOWN_BROKEN` parametrization
was removed as one skill case flipped to passing.

## Deviations from Plan

**1. [Rule 1 - Bug] FIX-03 status corrected from Complete to Pending**
- **Found during:** Requirement traceability review
- **Issue:** Marked complete by 16-03 while `_KNOWN_BROKEN` is non-empty, contradicting its stated criterion
- **Fix:** Reverted checkbox and annotated the traceability row with the blocking condition and owner (16-06)
- **Files modified:** `.planning/REQUIREMENTS.md`

## Threat Mitigations

| Threat | Disposition | Evidence |
|---|---|---|
| T-16-05 (EoP — web grants) | mitigated | Grants removed; `test_skill_drops_forbidden_tools[construct-synthesis]` green |
| T-16-11 (DoS — `refs/` lookup) | mitigated | Step rewritten onto already-granted `Read`; all skill invocations resolve |
| T-16-12 (Repudiation — spec row) | mitigated | Row discharged with phase + requirement attribution, not deleted |
| T-16-SC (Tampering — installs) | accept | Zero packages installed; `pyproject.toml` untouched |

No new security-relevant surface introduced — no network endpoints, auth paths, or schema
changes. This plan only removes capability.

## Self-Check: PASSED

All claimed files exist on disk; all four commit hashes resolve in git history.
