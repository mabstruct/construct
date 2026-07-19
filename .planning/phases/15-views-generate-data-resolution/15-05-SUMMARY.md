---
phase: 15-views-generate-data-resolution
plan: 05
subsystem: skills-and-docs
tags: [skill-wrapper, d-09, d-11, adr, supersession, doc-truth, debounce-removal]

requires:
  - phase: 15
    plan: 03
    provides: "`construct views generate --install-root` — the CLI command the wrapper skill now invokes"
  - phase: 15
    plan: 04
    provides: "The Python-layer refresh at all three workflow call sites, so the three doc sections could be deleted rather than corrected"
provides:
  - "`construct-views-generate-data` as a CLI wrapper holding no Python — `run.sh` + `SKILL.md` only"
  - "`adr-0005-views-refresh-ownership.md` — the live-document record of the D-10 reversal and both ROADMAP criterion-3 decisions"
  - "A PROJECT.md Key Decisions row citing adr-0005"
  - "Three workflow docs with no views-refresh instruction and no unresolvable remediation string"
affects: [16, 17, views, skills, docs]

tech-stack:
  added: []
  patterns:
    - "Skill-as-CLI-wrapper: the entry point guards for a missing argument and a missing executable, then execs the CLI — the two failures the deleted bootstrap used to absorb are now explicit"
    - "Deletion-over-correction for a documented step whose behaviour moved layers: the instruction has no correct form in the old location, so a one-sentence pointer replaces it rather than a fixed command"
    - "New numbered ADR over in-place amendment for a reversal, with the superseded record cited read-only (adr-0004 / Phase 14 D-07 precedent)"

key-files:
  created:
    - CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md
  modified:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/run.sh
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md
    - CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md
    - .planning/PROJECT.md
  deleted:
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/generate.py
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/requirements.txt
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/debounced_hook.py
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/debounced-hook.sh
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/.gitignore

key-decisions:
  - "The two live `debounced-hook.sh` registrations in construct-card-create and construct-card-connect were REMOVED in the same commit as the deletion, per the plan's explicit instruction not to break a live registration silently — direct per-card edits consequently lose their debounced refresh, and `views.per_card_hooks.*` is now inert config"
  - "The skill's `.gitignore` was deleted too: it ignored only `.venv/` and `__pycache__/`, both of which are artefacts of the retired bootstrap"
  - "adr-0005 records the measured three-full-builds-per-daily-cycle cost from 15-04, NOT D-12's original near-no-op framing"
  - "adr-0005 states explicitly that a successful refresh is not a schema guarantee over the written bytes — the 15-03 writer/validator divergence is named, not papered over"
  - "The archived Phase 13 `13-CONTEXT.md:36` D-10 record is cited read-only and left unedited, following adr-0004's treatment of Phase 10 D-02"

requirements-completed: [FIX-01]

coverage:
  - id: D1
    description: "The views skill holds no Python implementation — its entry point invokes the CLI"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "`ls` on the skill dir returns exactly `run.sh` and `SKILL.md`; `grep -c 'views generate --install-root' run.sh` == 1; `grep -ci 'venv|virtualenv|pip install' run.sh` == 0"
        status: pass
      - kind: other
        ref: "`bash -n run.sh` exits 0; running with no argument exits 2 with a usage line naming <install-root>"
        status: pass
    human_judgment: false
  - id: D2
    description: "No views-refresh instruction remains in the two cycle skills or daily-cycle.md"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "`grep -c 'construct views generate'` == 0 for all three files; `grep -ic 'views refresh'` == 1 each (the D-11 pointer); `grep -c 'D-11'` >= 1 each"
        status: pass
    human_judgment: false
  - id: D3
    description: "No remediation string in any workflow doc names a command that does not resolve against the live CLI"
    requirement: FIX-01
    verification:
      - kind: contract
        ref: "tests/contract/test_doc_command_references.py — 34 passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "A reader of the live document set can find the recorded reversal of Phase 13's D-10 without consulting the archived v0.4 milestone"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "adr-0005 exists in the live ADR set, names D-10 6x, uses 'supersede' 2x, and is cited from PROJECT.md Key Decisions"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both ROADMAP criterion-3 ambiguities have an explicit recorded decision in a durable, live document"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "adr-0005 § Decision records the install-root contract (`install_root` 5x, with the discover_workspaces reasoning) and the import coupling (verbatim vendoring, `packages = [\"src/construct\"]`)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The known-broken allowlist still holds exactly the four Phase 16 entries after the doc removals"
    requirement: FIX-01
    verification:
      - kind: contract
        ref: "`len(_KNOWN_BROKEN) == 4`; no entry added or reworded"
        status: pass
    human_judgment: false
  - id: D7
    description: "The architecture doc set is untouched, preserved for Phase 17"
    requirement: FIX-01
    verification:
      - kind: other
        ref: "`git diff --name-only 5c5b9d6..HEAD -- CONSTRUCT-CLAUDE-spec/` returns only the new adr-0005"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-07-20
status: complete
---

# Phase 15 Plan 05: Views skill wrapper, doc-section removal, and adr-0005 Summary

**The `construct-views-generate-data` skill is now two files — a guarded `run.sh` that execs `construct views generate --install-root` and a `SKILL.md` describing a wrapper — with its parallel Python runtime deleted; the three views-refresh doc sections are gone rather than corrected, because the Python layer owns the behaviour and the instruction has no correct form in a skill document; and `adr-0005` records the reversal of Phase 13's D-10 plus both ROADMAP criterion-3 decisions in the live ADR set. One finding was escalated rather than absorbed: the debounce pair had two live registrations, and removing them costs a real feature.**

## Performance

- **Duration:** ~45 min (including one mid-run API disconnect and resume)
- **Tasks:** 3
- **Files:** 1 created, 8 modified, 5 deleted
- **Suite:** 471 passing throughout — no test changes were needed by this plan

## Task Commits

1. **Task 1: reduce the skill to a CLI wrapper** — `1807b59` (refactor)
2. **Task 2: remove the three views-refresh doc sections** — `1979ae4` (docs)
3. **Task 3: adr-0005 + PROJECT.md Key Decisions row** — `3c46168` (docs)

## The live debounce registrations — the finding the plan asked to be surfaced

The plan required a pre-deletion repository grep for registrations of `debounced-hook.sh`, with an instruction not to break a live one silently. **Two live registrations existed:**

| File | Line | What it did |
|---|---|---|
| `construct-card-create/SKILL.md` | 94 | Step 7 invoked `bash <install-root>/.claude/skills/views-generate-data/debounced-hook.sh <install-root> card-create` |
| `construct-card-connect/SKILL.md` | 106 | Step 9, the structurally identical sibling for `card-connect` |

Both were removed in the same commit as the deletion, which is the first of the two branches the plan sanctioned. The alternative — keeping the files — would have preserved a per-skill venv bootstrap and a second `generate.py` call path, defeating the whole of D-09.

**The cost is real and is not a documentation-only change.** Direct `card-create` / `card-connect` invocations no longer schedule any views refresh. 15-04's Python-layer refresh fires at the end of the three *workflow* capabilities; a direct single-card edit is not one of those, so there is now no refresh path for it at all. Re-homing debounce behaviour in the Python layer is new runtime capability, which v0.4.1 excludes (RESEARCH OQ-3 / COVERAGE.md OPT-OUT row). This is recorded in `adr-0005` § Consequences → Negative, and is a v0.6 backlog candidate.

**Three configuration/doc references to the now-inert feature survive and are out of this plan's scope:**

- `CONSTRUCT-CLAUDE-impl/construct/templates/config.yaml:9-12` — the `views.per_card_hooks.{enabled,debounce_seconds,mode}` block
- `CONSTRUCT-CLAUDE-impl/construct/references/commands.md:81` — describes `views.per_card_hooks.*` as scheduling a debounced refresh
- `CONSTRUCT-CLAUDE-impl/README.md:263-264` — the same, in the config reference list

These are a config knob documented as functional whose implementation no longer exists — precisely the doc-truth class this milestone targets, but in files this plan does not own. **Flagged for Phase 16 (DOC-04 / invocation & user-doc truth)** rather than fixed here.

## What changed in each of the three workflow documents

Neither cycle skill needed renumbering — the removed section was the last step in both cases (`curation-cycle` Step 5 of 5, `research-cycle` Step 7 of 7). `daily-cycle.md` did: §5 was removed and §6 renumbered to §5, leaving `### 1.` through `### 5.` consecutive.

`daily-cycle.md` also carried **three cross-references** to the removed section, which a section-only deletion would have left dangling:

| Line | Before | After |
|---|---|---|
| 68 | "**Views refresh:** Deferred — … runs once after the whole cycle completes (Step 5, D-10)" | "**View data:** regenerated by the `research.run` capability itself, in the Python layer." |
| 83 | "**Views refresh:** Deferred — same as research … runs once in Step 5 (D-10)" | "**View data:** regenerated by the `curation.run` capability itself, in the Python layer." |
| 157 | "**Views refresh fails:** Warning appended to report; workspace is unaffected" | "**View data regeneration fails:** logged by the capability that attempted it; the run's reported status and the workspace are both unaffected" |

Each of the three files gained a one-sentence blockquote pointer citing D-11 and linking `adr-0005`, so a later reader does not re-add the step because its absence looked like an oversight.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] `daily-cycle.md`'s three dangling cross-references**

- **Found during:** Task 2, pre-edit grep for references to the removed section.
- **Issue:** The plan named §5 as the deletion target. Two per-child notes (lines 68, 83) and one error-handling bullet (line 157) pointed at it by number and by D-10, and both per-child notes asserted the now-false "no per-child views work / deferred" rule that 15-04 reversed.
- **Fix:** All three rewritten to the real behaviour (see table above). The plan's own action text required this ("update any cross-reference elsewhere in the same document that points at a renumbered step or at the removed section by number or name"), so this is execution of the instruction rather than scope expansion.
- **Committed in:** `1979ae4`

**2. [Rule 3 - Blocking] The skill's `.gitignore` was orphaned**

- **Found during:** Task 1.
- **Issue:** Not named in the plan's deletion list. It ignored exactly `.venv/`, `__pycache__/` and `*.pyc` — three artefacts that only the retired bootstrap and the deleted `generate.py` could produce.
- **Fix:** Deleted with the rest of the runtime. It is a hidden file, so the plan's `ls`-based acceptance criterion could not have caught it either way; leaving it would have been a file whose entire purpose had been removed.
- **Committed in:** `1807b59`

### Acceptance-criterion arithmetic

**3. `grep -rc 'workspace \.' daily-cycle.md` outputs 1, not 0**

The survivor is line 38: `construct daily run --workspace . --json`. That is the **`daily run`** command, not `views generate`, and `--workspace` is its genuine required option — confirmed against `construct daily run --help`, which shows `--workspace  -w  PATH  [required]`. The criterion's intent was the removal of the views generator's workspace-named invocation, and that holds: `grep -c 'construct views generate'` is 0 in all three files. The command-reference contract test passes, which independently confirms the surviving invocation resolves.

**4. The adr-0004 / adr-0005 heading diff is non-empty on two lines**

The criterion's `diff` shows differences at the three `### Option A/B/C` titles and at the one domain-specific `##` section (`## Durable orchestration state (artifact class)` vs `## Views refresh ownership (contract)`). Both are necessarily content-specific: adr-0004's options are about a checkpointer and adr-0005's are about refresh ownership, and each ADR's penultimate section names the thing *it* defines. The structural heading set the criterion actually guards is identical — `## Context`, `## Decision`, `## Options Considered` with three `### Option` children, `## Consequences` with `### Positive` / `### Negative` / `### Neutral`, one domain `##` section, and `## Relationship to prior ADRs` — in the same order, with the same status-line format and citation style.

**5. PROJECT.md's `Last updated` footer was deliberately not touched**

Updating it would have added a `-` line to the diff and failed the criterion asserting that no existing row or line was removed or rewritten. The criterion is the stronger signal here — it exists to prove the reversal was recorded additively — so the footer still reads "Phase 14 … complete". Worth correcting at the phase transition, not in this plan.

---

**Total deviations:** 2 auto-fixed (1 × Rule 2, 1 × Rule 3), 3 criterion clarifications, 1 escalated finding (the debounce registrations, above).
**Impact on plan:** No scope creep beyond the two card-skill files, which the plan's own action text explicitly authorised ("remove the registration in the same commit"). Both prohibitions held: the architecture doc set (`architecture-overview.md`, `artifact-catalog.md`, `config-topology.md`) is untouched — `git diff --name-only 5c5b9d6..HEAD -- CONSTRUCT-CLAUDE-spec/` returns only the new `adr-0005` — and nothing in the archived v0.4 milestone was edited.

## What adr-0005 deliberately does not claim

Two carried-forward corrections from 15-03 and 15-04 shaped the ADR's wording, and both were honoured:

**It does not claim generate's output is schema-validated on disk.** The § "Views refresh ownership (contract)" section states in bold that a successful refresh is **not** a schema guarantee over the written artefacts, names the three files `views validate` currently rejects, and names the pinning test. The 15-03 divergence remains open and untouched.

**It does not repeat D-12's optimistic cost claim.** The § Decision records ~three *full* 11-file rebuilds per daily cycle and up to three `version.json` writes, with an explicit note that the fingerprint short-circuit bounds the cost only for a genuinely unchanged root while `daily.run`'s children mutate the workspace by construction. 15-04's measurement is recorded as the cost, not the near-no-op framing.

**`confirm_refresh` is described with 15-04's implemented semantics** wherever it appears (the contract table and § Decision): a verbosity switch that appends `✓ views updated` to a *successful* refresh and never gates execution.

## Known Stubs

None introduced. The skill now holds no implementation at all by design, which is the D-09 outcome rather than a stub — the behaviour it names is fully implemented in `construct.views.generate`.

## Notes for downstream phases

- **Phase 17 (DOC-01) fact correction.** `REQUIREMENTS.md` DOC-01 asserts that `architecture-overview.md` cites "the non-existent `spec-v02-data-model.md`". **That premise is false.** The file exists at `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md`, and this phase relied on its §5.1/§5.2 as the authoritative views data contract — `adr-0005` names it as the durable authority. Phase 17 must inherit this correction rather than act on the false premise.
- **Phase 17 (DOC-02) inventory deltas** for `artifact-catalog.md`: one CLI command added (`views generate`); one MCP tool moved from permanent-failure to real (`construct_views_generate_data`); one skill reduced to a CLI wrapper with five files deleted; three workflow docs lost a section; two card skills lost a step each; one ADR added (`adr-0005`).
- **Phase 16 (FIX-03) inheritance.** The allowlist stands at exactly 4 entries, all owned by FIX-03. Nothing was added or reworded by this plan.
- **Phase 16 (DOC-04) inheritance — new.** The three `views.per_card_hooks.*` references listed above now document an inert feature. Also still outstanding from 15-03: `USER-TEST-PLAYBOOK-v03.md` §7.1 still calls `views.generate_data` a known v0.4 stub, which is false — left alone deliberately, as it is outside this plan's scope too.
- **v0.6 backlog candidates surfaced this phase:** align `cards.json` with `spec-v02-data-model` §5.2 (OQ-1 reading (b)); port the vendored views parsers from PyYAML to ruamel.yaml (F6 Option B); registry unification for the views group (RT-01/RT-02, declined by D-03); **re-home debounce behaviour in the Python layer so direct per-card edits refresh again (OQ-3 — now a real regression, not a hypothetical)**; tighten `DomainRecord.metrics` and `cross_domain_links` into nested models once legacy `domains.yaml` shapes are known.

## Self-Check: PASSED

All three commit hashes resolve in `git log`. `adr-0005-views-refresh-ownership.md` exists and carries every asserted element. All five deleted paths are gone from disk, including `lib/` and the gitignored `.venv/`. The skill directory lists exactly `run.sh` and `SKILL.md`. `len(_KNOWN_BROKEN) == 4`. Full suite green at 471 passed.

---
*Phase: 15-views-generate-data-resolution*
*Completed: 2026-07-20*
