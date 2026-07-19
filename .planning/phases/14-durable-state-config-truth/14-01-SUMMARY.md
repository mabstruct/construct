---
phase: 14-durable-state-config-truth
plan: 01
subsystem: spec-documentation
tags: [adr, durable-state, langgraph, checkpointer, documentation-truth]
requires: []
provides:
  - "ADR-0004 (identifier cited by nfrs.md, architecture-overview.md, workspace-contract.md)"
  - "`durable orchestration state` artifact class (consumed by plan 14-03)"
  - "Complete ADR index in architecture-overview.md §9.1"
affects:
  - CONSTRUCT-CLAUDE-spec/architecture-overview.md
tech-stack:
  added: []
  patterns: [nygard-adr-format, plain-backticked-adr-citations-in-spec-docs]
key-files:
  created:
    - CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md
  modified:
    - CONSTRUCT-CLAUDE-spec/architecture-overview.md
decisions:
  - "`.construct/workflow/*.sqlite` is intentional durable state holding pending human-review decisions that are not reconstructible from layer 1"
  - "The rebuild guarantee is scoped to knowledge state (cards/, refs/, connections.json, search-seeds.json, log/events.jsonl, digests/), not to the whole workspace"
  - "Workflow checkpoints sit outside the layer 1/2/3 model rather than violating it — §4's invariants are each scoped to layer 2"
  - "adr-0004 is a new ADR rather than an Amendment C to adr-0003, for discoverability: adrs/ has no README"
  - "adr-0004 discharges Phase 10 D-02's deferred action and supersedes its weaker 'checkpoint state only' framing"
metrics:
  duration: ~12m
  tasks: 2
  files: 2
  completed: 2026-07-19
status: complete
---

# Phase 14 Plan 01: ADR-0004 Durable Workflow Checkpoints Summary

Recorded the LangGraph `SqliteSaver` checkpointer as sanctioned durable orchestration state in a new Nygard-format ADR, and reconciled `architecture-overview.md` so its database anti-pattern carries one named, cited carve-out and its ADR index is complete.

## What Was Built

**Task 1 — `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md`** (commit `7d1b268`)

New ADR following the `adr-0002` skeleton: header block (`Status`/`Date`/`Deciders`/`Context`/`Related`), then `## Context`, `## Decision`, `## Options Considered` (three options, Option A marked `(this decision)`), `## Consequences` (Positive/Negative/Neutral), plus two post-Consequences sections precedented by `adr-0002`'s trailing-section pattern.

The non-reconstructibility claim is stated as a verified fact with file:line evidence, read from source this session rather than assumed:

- `research_run.py:437-449` — `gate_review` contains only `interrupt(...)`; its docstring is explicit that no writes or event emission live in the node.
- `research_run.py:745` — `update_seeds_and_log` is a separate node defined after the gate.
- `research_run.py:786, :794, :808, :814, :820` — every `append_event` call in the module lives inside `update_seeds_and_log`. There is no other call site.

Therefore, while a run sits at `awaiting_review`, zero events have been appended to `log/events.jsonl`, and the scored findings plus per-finding default decisions exist only in the sqlite checkpoint. The checkpointer paths are `research_run.py:879-894` and the structurally identical `curation_run.py:277-291`.

`## Durable orchestration state (artifact class)` defines the class name, a three-part qualifying test, a one-row table, and the argument for why it fits neither the Support class (whose preamble says support artifacts "do not define workspace truth") nor the Derived class (whose artifacts are generated from source-of-truth files). This section is what plan 14-03 consumes.

`## Relationship to prior ADRs` preserves adr-0001's markdown-as-truth claim explicitly (scoped, not retracted), places adr-0004 downstream of adr-0003 §A.3, gives the discoverability reason for a new ADR over an amendment, and records the Phase 10 D-02 discharge with a read-only `../../` link to the archive.

**Task 2 — `CONSTRUCT-CLAUDE-spec/architecture-overview.md`** (commit `e54768e`)

Three edits, all anchored on strings rather than line numbers:

1. §8.2 — the `Add a database that owns part of the truth` bullet retains its `→ reconsider` verdict and both original rationale sentences; a carve-out clause is appended naming workflow orchestration state, `.construct/workflow/*.sqlite`, the "outside the model rather than violating it" framing, and the plain-backticked citation `adrs/adr-0004-durable-workflow-checkpoints.md`.
2. §9.1 — added both `adr-0003` and `adr-0004` in numeric order, matching the existing `` - `adrs/<file>.md` — <gloss> `` shape. Adding adr-0003 was deliberate: D-07's rationale is that a v0.5 planner finds decisions by scanning the index, which an index missing adr-0003 would leave asserted rather than satisfied.
3. Line 6 `**Related:**` — appended both ADRs as backticked paths with the existing ` · ` delimiter, preserving every prior entry.

Spec-doc citation convention (plain backticked paths, not markdown links) was followed; the ADRs' own markdown-link style was not imported into this file.

## Key Decisions

- **Scope the guarantee, don't weaken the principle.** Option B (emit findings pre-gate to restore reconstructibility) was rejected because it changes runtime behavior — Out of Scope for v0.4.1 — and would write unreviewed findings into the audit log, eroding RSCH-03. Option C (drop the checkpointer) was rejected as a v0.4 regression traded for a tidier sentence.
- **One decision covers both checkpointers.** `research-run.sqlite` and `curation-run.sqlite` are the identical `SqliteSaver` pattern and are governed as one artifact class, not two special cases.
- **Blast radius stated honestly.** The ADR claims only that losing a checkpoint costs a completed search-and-scoring cycle plus any entered decisions. It makes no claim of backup, replication, or restorability, per the plan's transparency prohibition.

## Deviations from Plan

### Acceptance criterion unsatisfiable as literally written (documented, not worked around)

**Found during:** Task 2 verification.

**Issue:** The Pitfall-1 guard `git diff CONSTRUCT-CLAUDE-spec/architecture-overview.md | grep -c 'views/build/data/'` returns `1`, not `0`. The cause is not a wrong-bullet edit: the `views/build/data/` anti-pattern bullet sits at line 240 and the edited bullet at line 243, so with `git diff`'s default three lines of context the untouched bullet appears as a **context line** in the diff. The criterion as written cannot return 0 for any correct edit to line 243.

**Resolution:** The guard's *intent* — that the wrong bullet is untouched — was verified instead with a context-free diff:

```
git diff -U0 <file> | grep -E '^[+-]' | grep -v '^[+-][+-][+-]' | grep -c 'views/build/data/'  →  0
```

`git diff -U0` confirms exactly three changed hunks: line 6, line 243, and two added lines after 251. No change touches the `views/build/data/` bullet. No file content was altered to satisfy the flawed assertion.

**Recommendation for the verifier:** treat the `-U0` form as the correct expression of this guard; the `-U3` default form should be corrected in any future plan reusing it.

### Minor

- The Task 2 `<verify>` block's `sed -n '/### 9.1/,/^## /p'` range works because §9.2 is an `###`, not a `##`; both adr-0003 and adr-0004 are inside the printed range. No change needed.

No Rule 1/2/3 auto-fixes were required; no Rule 4 architectural decisions arose.

## Verification Results

| Check | Result |
|---|---|
| Task 1 automated verify (`ADR-0004-OK`) | Pass |
| adr-0004 section counts (`## Context`/`Decision`/`Options Considered`/`Consequences`) | 1 each |
| `.construct/workflow/` occurrences in adr-0004 | 10 (≥ 3 required) |
| Negative grep `backed up\|replicated\|recoverable\|guaranteed durable` in adr-0004 | 0 |
| §8.2 rule retained, exactly once, carrying `adr-0004` and `.construct/workflow/` | Pass |
| `adrs/adr-0003-…` in architecture-overview.md | 2 |
| `adrs/adr-0004-…` in architecture-overview.md | 3 |
| §9.1 lists adr-0001..0004 | Pass |
| Pitfall-1 guard (`-U0` changed lines) | 0 |
| Full pytest suite | **439 passed**, 2 warnings, 5.99s |
| Edit fence (D-02) — AGENTS.md, USER-TEST-PLAYBOOK-v03.md, spec-v04-agentworkflows.md, migrations/, .planning/milestones/ | empty (untouched) |
| `git status --porcelain CONSTRUCT-CLAUDE-spec/` after Task 2 | only architecture-overview.md |

## Threat Mitigations Applied

- **T-14-01-01 (Repudiation, archived record):** `git status --porcelain .planning/milestones/` verified empty before the Task 1 commit. The Phase 10 record was read and cited, never edited; adr-0004 states explicitly that its integrity outweighs its consistency with today's decision.
- **T-14-01-03 (Tampering, durability claims):** the negative grep returns 0. The ADR names the loss cost and makes no protection claim.

## Known Stubs

None.

## Threat Flags

None — this plan introduces no executable surface, no network, auth, or crypto path.

## Notes for Downstream Plans

- **Plan 14-03** consumes the `durable orchestration state` class name, its three-part qualifying test, and the "created lazily / not in `REQUIRED_PATHS` / may legitimately be absent" rule sentence verbatim in spirit for the workspace-contract fourth table.
- **Plan 14-02** (`nfrs.md`) should cite `adrs/adr-0004-durable-workflow-checkpoints.md` as a plain backticked path and can reuse the scoped-guarantee wording from adr-0004's Decision section rather than re-deriving it.
- `REQUIRED_PATHS` is confirmed at `src/construct/schemas/workspace.py:14` and does not list `.construct/workflow/`.

## Self-Check: PASSED

- `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md` — FOUND
- `CONSTRUCT-CLAUDE-spec/architecture-overview.md` — FOUND
- Commit `7d1b268` — FOUND
- Commit `e54768e` — FOUND
