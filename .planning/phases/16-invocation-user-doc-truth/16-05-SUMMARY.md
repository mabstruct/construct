---
phase: 16-invocation-user-doc-truth
plan: 05
subsystem: user-facing-documentation
tags: [documentation, cli-surface, invocation-guard, doc-truth]
requires:
  - "16-03 (knowledge card list — the shipped flag surface named in the CLI cells)"
  - "16-01 (the _MUST_CARRY_INVOCATIONS guard these edits turn green)"
provides:
  - "A CLI-invocation column in CONSTRUCT-CLAUDE-impl/USER_GUIDE.md"
  - "A CLI-invocation column in CONSTRUCT-CLAUDE-impl/construct/references/commands.md"
  - "A settled, cross-checked picture of the documented command surface for 16-06 and Phase 17"
affects:
  - "16-06 (playbook supersession — may lift invocations from these tables)"
  - "16-07 (glob extension — these are the strings the extended scan will police)"
  - "17 DOC-02 (published surface inventory)"
tech-stack:
  added: []
  patterns:
    - "Doc-as-executable-surface: every backticked `construct ...` span in a user-facing doc is expected to run verbatim, not merely resolve"
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-impl/USER_GUIDE.md
    - CONSTRUCT-CLAUDE-impl/construct/references/commands.md
    - .planning/REQUIREMENTS.md
decisions:
  - "The guard's resolution check is necessary but not sufficient — it validates the command path only, so a cell can pass the guard and still fail at runtime. Task 3's cross-check was executed by running every documented invocation, not by re-reading the guard."
  - "`construct init <domain>` was corrected to `construct init <path>` — the CLI argument is a workspace path, and the natural-language 'init {domain}' framing had been carried into the CLI cell where it was wrong."
  - "Bare command mentions in prose (the per-card-edits note) were given their required flags too, so the rule 'every backticked construct span executes' holds without exception and needs no reader-facing caveat."
metrics:
  duration: ~35 min
  tasks: 3
  files-modified: 3
  completed: 2026-07-20
status: complete
---

# Phase 16 Plan 05: Executable CLI columns in the user-facing doc set Summary

`USER_GUIDE.md` and `construct/references/commands.md` each gained a CLI column that a reader can
copy and run — 67 invocations across the two files, every one of which both resolves against the
live Typer app and executes without a usage error, closing the two `test_key_docs_are_not_vacuous`
cases that had been RED since 16-01.

## What Was Built

**`USER_GUIDE.md` — a third `CLI` column across all nine Full Command Reference group tables.**
`You say` remains the first column: the natural-language path is the product's real entry model
(D-10), and the CLI column is an addition, not a replacement. Two new groups were added —
`### Daily cycle` and `### Ingestion, spikes & tags` — plus rows for research score/review/inspect,
curation review/inspect, card and connection enumeration, connection removal, `ask domain`,
`views validate`, `workflow status`, and `mcp`. The Workflows table was left two-column as
instructed; it describes multi-skill sequences, and a CLI cell there would invite an invented
composite invocation.

**`commands.md` — a fourth `CLI` column between `Skill` and `What it does`.** The `Skill` column
was preserved rather than repurposed: a skill name and a shell invocation are different axes, and
collapsing them would destroy the skill mapping this document exists to provide. Rows marked `—`
are skill-only. `## Starting Point` and `## Natural Language` are byte-identical to their
pre-plan state, as the plan required.

**The inert views configuration note was corrected.** `views.per_card_hooks.*` was documented as
scheduling a debounced refresh after direct card-create / card-connect edits. Phase 15-05 deleted
that debounce pair along with its two skill registrations, leaving the key inert. The clause is
gone; the note now states plainly that direct per-card edits have **no** views-refresh path, and
names the workflow capabilities and `construct views generate` as what actually regenerates data.
The three still-live keys (`auto_regenerate`, `workspace_landing`, `confirm_refresh`) survive.

## Invocation counts

| Document | Distinct command paths extracted | Distinct invocation strings executed |
|---|---|---|
| `USER_GUIDE.md` | 34 | 34 |
| `construct/references/commands.md` | 33 | 33 |

All 67 executed with zero usage errors against a scratch workspace.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 19 documented invocations resolved but did not execute**

- **Found during:** Task 3 (the cross-check the task exists to perform)
- **Issue:** The invocation guard validates the *command path* only — it truncates at the first
  argument-looking token by design. That means a cell naming a real command but omitting its
  required arguments passes `_resolves()` and the whole contract test suite, yet fails immediately
  with a Typer usage error when a reader copies it verbatim. Task 1 and Task 2 populated their
  cells from the plan's own mapping table, which used bare command paths; both tasks' verify
  scripts passed cleanly because those scripts only exercise the guard. The plan's `<verification>`
  section anticipated exactly this — "confirm each executes rather than merely resolving" — and
  spot-running three invocations is what surfaced it.
- **Fix:** Determined the full required-parameter set for every documented leaf from the live
  `--help` output, then completed each cell: `status`/`validate`/`init` take a positional
  `<path>`; `card evaluate`, `research score`, `curation review/inspect`, `daily inspect` and
  `research review/inspect` require `--workspace` (plus `--run-id` where the run handle is
  mandatory); `knowledge card create` requires `--title`/`--type`/`--domains`; `card edit` and
  `card archive` take `<card-id>`; `connection add`/`remove` take `<from-id> <to-id> --type`;
  `spike run` takes `<tool-name>`; `tag approve` takes `<candidate-ids>`; `ask domain` requires
  `--question` and `--domain`. Verified by executing all 67 invocations, not by re-running the guard.
- **Files modified:** both documents
- **Commit:** 908bbb4

**2. [Rule 1 - Bug] `construct init <domain>` named the wrong argument**

- **Found during:** Task 3
- **Issue:** The plan's mapping table specified `construct init <domain>`, carrying the
  natural-language "init {domain}" framing into the CLI cell. The `init` command's argument is a
  workspace **path**, not a domain name. The cell resolved (the placeholder is truncated) but
  misinstructed the reader about what to substitute — the quietest possible failure, since it
  would never fail a test.
- **Fix:** Corrected to `construct init <path>` in both documents.
- **Commit:** 908bbb4

**3. [Scope] Generated `views/build/` output removed**

My verification spot-runs invoked `construct views generate` from the repository root, which is
not a CONSTRUCT workspace, producing an untracked `views/build/` tree. It was never tracked and is
pure runtime output, so it was removed with a targeted `rm -rf views/build` (no `git clean`). The
working tree is clean.

## Cross-check results (Task 3)

**Residual asymmetry between the two documents — one, and it is intended.**

| Command path | Present in | Reason |
|---|---|---|
| `construct help` | `USER_GUIDE.md` only | `commands.md` reaches `help` through its `## Starting Point` table, whose bare single-backtick `` `construct` `` span deliberately does not fire the extractor (the regex requires a following lowercase token). The plan explicitly instructed leaving that table alone; adding an invocation there would duplicate the help row. |

Otherwise the `commands.md` invocation set is an **exact subset** of `USER_GUIDE.md`'s
(`commands.md \ USER_GUIDE.md = ∅`), which is the intended relationship: the guide is the fuller
reference.

**Live leaf commands documented in neither file: none.** The plan allowed up to two internal-only
leaves; the actual count is zero. The two candidates the plan anticipated were both given rows —
`construct mcp` (the MCP server entry point, in Entry & orientation) and
`construct knowledge connection remove` (in Knowledge operations) — as were `construct ask domain`
and `construct workflow status`, which the plan's mapping had not assigned anywhere. Every one of
the 34 live leaf commands is now reachable from the user-facing doc set.

**No invented commands.** Every extracted path is an exact member of `LEAF_COMMANDS` or
`COMMAND_GROUPS`; not one path needed the extend-a-leaf fallback, meaning every placeholder
truncates cleanly at its bracket. Every cell without a CLI equivalent is `skill-only`
(`USER_GUIDE.md`) or `—` (`commands.md`) — 13 such cells, none quietly filled with a guess.

## Requirement Traceability

**DOC-04 remains `Pending` — deliberately not marked complete.** Its criterion has four clauses:

| Clause | Status |
|---|---|
| (a) `USER_GUIDE.md` covers the v0.4 commands | **Discharged by this plan** — all twelve criterion-4 paths present and executable |
| (b) `commands.md` lists real commands | **Discharged by this plan** |
| (c) `README.md` lineage + `AGENTS.md` CLI description accurate | Discharged by 16-02 |
| (d) `USER-TEST-PLAYBOOK-v03.md` retired or superseded | **Open — 16-06 owns it** |

Because (d) is still open, the requirement checkbox stays unchecked. Only the traceability note
was refreshed, to record which clauses are now evidenced. This follows the phase's twice-learned
lesson about marking requirements ahead of their evidence (FIX-03, DOC-04).

## Verification

- `.venv/bin/python -m pytest -q -p no:cacheprovider` → **515 passed, 0 failed**
  (entry baseline was 513 passed / 2 failed; both RED guards are now green and no new failure
  was introduced)
- `tests/contract/test_doc_command_references.py` → 36 passed, including all three
  `test_key_docs_are_not_vacuous` cases
- All 67 documented invocations executed verbatim against a scratch workspace → 0 usage errors
- Guard not weakened: `tests/` is untouched by this plan. `_MUST_CARRY_INVOCATIONS` still holds 3
  entries and `_DOC_GLOBS` still holds 3 — 16-07 owns the glob extension. The two cases pass
  because real invocations were added, which is the point.
- Neither document asserts a numeric command, capability, or MCP tool count (D-12); both cite
  `tests/contract/test_doc_command_references.py` as the live authority instead.

## Note for 16-07

These two documents are now the largest concentration of `construct ...` strings in the repository
and are **not yet globbed** by `_DOC_GLOBS`. Until 16-07 extends the scan, they are policed only by
the per-document non-vacuity guard, which checks that at least one invocation exists — not that
they all resolve. Nothing currently prevents a future edit from introducing a broken invocation
here. That is precisely the gap 16-07 closes, and this plan is what makes closing it meaningful.

A caveat worth carrying into 16-07: extending `_DOC_GLOBS` will police *resolution*, not
*executability*. The 19 defects found in Task 3 would all have passed an extended glob. If the
executability property is worth keeping, it needs its own check.

## Self-Check: PASSED

- `CONSTRUCT-CLAUDE-impl/USER_GUIDE.md` — FOUND (modified)
- `CONSTRUCT-CLAUDE-impl/construct/references/commands.md` — FOUND (modified)
- Commit c8399ba (Task 1) — FOUND
- Commit 56fbf83 (Task 2) — FOUND
- Commit 908bbb4 (Task 3) — FOUND
