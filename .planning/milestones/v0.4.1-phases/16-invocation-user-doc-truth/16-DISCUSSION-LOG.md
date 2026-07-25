# Phase 16: Invocation & User-Doc Truth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-20
**Phase:** 16-invocation-user-doc-truth
**Areas discussed:** card list / ref list fate, Playbook retire vs supersede, User-doc shape (CLI vs NL), synthesis WebSearch/WebFetch

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| card list / ref list fate | Implement the two commands vs rewrite the dependent skills | ✓ |
| Playbook retire vs supersede | Delete USER-TEST-PLAYBOOK-v03.md vs replace with an executable v0.4.1 playbook | ✓ |
| User-doc shape (CLI vs NL) | CLI-first vs NL-first vs parallel surfaces for USER_GUIDE.md and commands.md | ✓ |
| synthesis WebSearch/WebFetch | Strip the grants vs record a reasoned exception | ✓ |

**User's choice:** all four areas.

---

## card list / ref list fate

### Q1 — How do `knowledge card list` and `knowledge ref list` resolve?

| Option | Description | Selected |
|--------|-------------|----------|
| Split: implement card list, drop ref list | Implement `card list` mirroring the existing `connection list`; rewrite synthesis's soft `ref list` call. Avoids a new sub-app for one advisory lookup | ✓ |
| Implement both | Add `card list` plus a new `knowledge ref` sub-app. Fully symmetric, both skills stay thin, but costs a sub-app + tests for an advisory use | |
| Rewrite both skills, implement neither | Read-glob fallbacks. Cheapest, but reverses Phase 12's thin-wrapper direction | |

**User's choice:** Split — implement `card list`, drop `ref list`.
**Notes:** Grounded on the discovery that `knowledge connection list` already exists — `card list` closes a node/edge asymmetry rather than adding a capability. gap-analysis needs structured frontmatter for every card, which a Read-glob fallback gives up.

### Q2 — What does `knowledge card list` return per card?

| Option | Description | Selected |
|--------|-------------|----------|
| Full frontmatter, no body | Every field gap-analysis names; bodies excluded so synthesis's enumerate-then-Read flow survives | ✓ |
| Minimal projection (id, title, domains) | Small payload, but gap-analysis re-parses frontmatter in the skill layer | |
| Full frontmatter plus body | One call gives synthesis everything, but returns the whole graph's prose | |

**User's choice:** Full frontmatter, no body.

### Q3 — What happens to synthesis's `knowledge ref list` line?

| Option | Description | Selected |
|--------|-------------|----------|
| Replace with Read over refs/ | The call is advisory; rewrite as a scoped Read, note the future sub-app home | ✓ |
| Delete the step entirely | Cleanest for the guard, but synthesis loses sight of supporting references | |
| Log as v0.6 follow-up and delete now | Same as delete, but tracked in REQUIREMENTS.md | |

**User's choice:** Replace with Read over `refs/`.
**Notes:** The skill already grants `Read` and already uses it for individual card inspection — no new tool grant needed.

### Q4 — Registry/MCP parity vs Phase 17's inventory ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Full parity, note the count shift for Phase 17 | Register like `connection.list`; record 34 CLI / 22 MCP in CONTEXT.md; no blocking dependency | ✓ |
| CLI-only, skip MCP registration | Leaves Phase 17 undisturbed but breaks the parity principle and repeats Phase 15 D-03's drift | |
| Full parity, and update artifact-catalog.md here | Closes the count now, but reaches into Phase 17's owned document | |

**User's choice:** Full parity, note the count shift for Phase 17.

---

## Playbook retire vs supersede

### Q1 — What happens to `USER-TEST-PLAYBOOK-v03.md`?

| Option | Description | Selected |
|--------|-------------|----------|
| Supersede with a v0.4.1 playbook | New file kept in `_DOC_GLOBS`; allowlist entries die because commands left a *scanned* doc | ✓ |
| Retire outright — delete it | Empties the allowlist in one commit, but by shrinking what the guard scans — the "unscanned, not empty" outcome STATE.md:203 warns about | |
| Keep v0.3, patch the two broken steps | Cheapest path to an empty allowlist, but still validates only the v0.3 surface | |

**User's choice:** Supersede with a v0.4.1 playbook.
**Notes:** `.planning/STATE.md:203` had already flagged this exact trap. `spec-v05-ui-primary.md:152` anticipates a `USER-TEST-PLAYBOOK-v05`, implying the artifact lives on per-version.

### Q2 — What does the v0.4.1 playbook cover?

| Option | Description | Selected |
|--------|-------------|----------|
| Carry v0.3 sections forward, add v0.4 workflows | Replace §5.2/5.3 with research/curation review flows; add daily, card evaluate, views, card list; reorganise by capability | ✓ |
| v0.4 workflows only | Shorter, but stops being an end-to-end walkthrough from zero | |
| Full sweep — every command on the live surface | Exhaustive, but turns the playbook into a test matrix | |

**User's choice:** Carry v0.3 sections forward, add v0.4 workflows.

### Q3 — Execution profile given Tavily and the LLM gates

| Option | Description | Selected |
|--------|-------------|----------|
| Offline-runnable by default, credentialed sections marked | Mirrors the v0.3 file's own §6 pattern; release validation stays runnable from a bare checkout | ✓ |
| Assume full credentials throughout | Exercises real end-to-end paths but can fail for reasons unrelated to the build | |
| Two playbooks — offline core plus credentialed supplement | Clean separation, doubles maintenance and guard surface | |

**User's choice:** Offline-runnable by default, credentialed sections marked.

### Q4 — How do playbook steps express pass/fail?

| Option | Description | Selected |
|--------|-------------|----------|
| Assert on `--json` status fields, not exit codes | Honours Phase 11's contract that a degraded `curation.run` exits 0 on purpose | ✓ |
| Exit codes with a caveat note | Simpler, but a skimming reader takes the exit code at face value | |
| Both — exit code and status field | Belt-and-braces, but the exit-code half is near-vacuous by design | |

**User's choice:** Assert on `--json` status fields.
**Notes:** Surfaced from a recalled Phase 11 decision — a playbook asserting "exit 0 = passed" would silently green-light a degraded run.

### Q5 — What proves the playbook "runs end to end"?

| Option | Description | Selected |
|--------|-------------|----------|
| Guard test resolves it + one real execution pass | Resolution is mechanical and permanent; execution catches steps that parse but error | ✓ |
| Guard test resolution only | Fully repeatable, but "resolves" is weaker than "runs" | |
| Add the playbook to CI as an executed smoke suite | Strongest guarantee, but that's new test infrastructure | |

**User's choice:** Guard test resolves it + one real execution pass.

---

## User-doc shape (CLI vs NL)

### Q1 — What shape does the user-facing command reference take?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep NL-first, add a CLI column | Third column with the real invocation; preserves the Claude-native framing; rows with no CLI equivalent show that honestly | ✓ |
| CLI-first, NL phrases secondary | Cleanest mapping to criterion 4, but demotes the interaction model PROJECT.md names as the near-term UX | |
| Add a separate CLI reference section | Least disruptive, but leaves two parallel references that can drift | |

**User's choice:** Keep NL-first, add a CLI column.

### Q2 — Should `USER_GUIDE.md` and `commands.md` join `_DOC_GLOBS`?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add both | Any doc carrying executable strings should be guarded, or this phase creates fresh unguarded drift | ✓ |
| Add USER_GUIDE.md only | Narrower blast radius, but the agent-facing reference stays unchecked | |
| No — leave `_DOC_GLOBS` as is | Avoids expanding a test's surface, but criterion 4's fixes get no mechanical protection | |

**User's choice:** Yes — add both.

### Q3 — How should the doc set express the command-surface size?

| Option | Description | Selected |
|--------|-------------|----------|
| Avoid hard counts; point at the guard | Any number goes stale — exactly how "25" rotted | ✓ |
| State the corrected count (34) explicitly | Concrete today, reintroduces the same staleness mechanism | |
| State the count and add a test asserting it | Cannot rot silently, but fails on every legitimate command addition | |

**User's choice:** Avoid hard counts; point at the guard.
**Notes:** Raised after probing the live Typer app showed 33 leaves, not the 25 that ROADMAP criterion 5 asserts.

### Q4 — How far does this phase reach into `AGENTS.md` / `README.md`?

| Option | Description | Selected |
|--------|-------------|----------|
| Criterion-scoped: AGENTS.md:284, README lineage, plus the Phase 14 deferrals | Bounded named edit list, including `AGENTS.md:91,134` which Phase 14 D-02 fenced to this phase | ✓ |
| Criterion-scoped only | Tighter, but leaves the Phase 14 hand-off unowned | |
| Full AGENTS.md accuracy pass | Thorough, but collides with Phase 17's DOC-01 | |

**User's choice:** Criterion-scoped plus the Phase 14 deferrals.

---

## synthesis WebSearch/WebFetch

### Q1 — DEC-01: how does `construct-synthesis` resolve?

| Option | Description | Selected |
|--------|-------------|----------|
| Remove both grants, bring synthesis into the forbidden-tool test | Closes `spec-v04:436` on its own terms; costs nothing at runtime since the skill never invoked them | ✓ |
| Remove the grants, leave test scope alone | Closes DEC-01 but leaves the last removal unguarded while the other two skills are protected | |
| Record a reasoned exception in PROJECT.md | Permitted by criterion 3, but would document an exception for capabilities the skill does not use | |

**User's choice:** Remove both grants and extend the test.
**Notes:** Evidence was one-sided — `spec-v04:436` mandates removal once `research.run` ships (it did, Phase 10); the grants appear only in frontmatter with zero body references; `test_skill_migration.py:34` already defines the forbidden list.

### Q2 — Does this phase close `spec-v04-agentworkflows.md:436`?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — mark :436 discharged, leave :211/:557 to Phase 17 | DEC-01 names :436; the model-routing lines stay with Phase 17's spec pass per Phase 14 D-02 | ✓ |
| Leave the spec untouched | Avoids a spec edit, but leaves an instruction to do work already done | |
| Close :436 and :211/:557 together | Fewer passes, but pulls Phase 14's deferred lines into a phase that didn't scope them | |

**User's choice:** Close `:436` only; fence `:211`/`:557` to Phase 17.

---

## Claude's Discretion

- Exact flag surface, handler location, and JSON envelope for `knowledge card list` (guided by `connection list`).
- Whether `card list` is one commit or shares a plan with the skill rewrites.
- `USER-TEST-PLAYBOOK-v041.md`'s filename slug, section numbering, and smoke-workspace setup.
- CLI column header wording and how "no CLI equivalent" rows are rendered.
- Whether ROADMAP/REQUIREMENTS' "25-command surface" text is corrected here or flagged for the milestone audit.
- Replacement prose for `AGENTS.md:284` and the `README.md` lineage block.
- Mechanism for extending `test_skill_migration.py`'s scope to `construct-synthesis`.
- Plan decomposition across the four areas.

## Deferred Ideas

- `knowledge ref` sub-app with `list` — future home if refs need structured enumeration.
- Playbook as an automated CI smoke suite.
- `spec-v04-agentworkflows.md:211` / `:557` model-routing references — Phase 17.
- `artifact-catalog.md` inventory update to 34 CLI / 22 MCP — Phase 17 (DOC-02).
- Full `AGENTS.md` accuracy pass — overlaps Phase 17 (DOC-01).
- Workspace-shipped `commands.md` copies drifting from the guarded source.
- `views validate` accepting the bytes `views generate` writes — Phase 15's known-open contract question.
