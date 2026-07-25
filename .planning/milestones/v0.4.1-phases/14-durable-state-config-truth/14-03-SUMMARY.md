---
phase: 14-durable-state-config-truth
plan: 03
subsystem: spec-documentation
tags: [workspace-contract, artifact-classes, durable-state, model-routing, deprecation, documentation-truth]
requires:
  - "ADR-0004 / `durable orchestration state` artifact class (plan 14-01)"
  - "`src/construct/llm/config.yaml` named as LLM authority (plan 14-02, nfrs.md §3)"
provides:
  - "`### Durable orchestration state` — fourth artifact class in workspace-contract.md"
  - "Complete D-12 artifact listing (.construct/workflow/, .construct/search.yaml, WORKSPACE.md)"
  - "model-routing.yaml deprecation markers in the final two D-02 fence targets"
affects:
  - CONSTRUCT-CLAUDE-spec/workspace-contract.md
  - CONSTRUCT-CLAUDE-spec/config-topology.md
tech-stack:
  added: []
  patterns: [plain-backticked-adr-citations-in-spec-docs, artifact-class-table-with-defining-preamble]
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-spec/workspace-contract.md
    - CONSTRUCT-CLAUDE-spec/config-topology.md
decisions:
  - "`.construct/workflow/*.sqlite` filed under a new fourth class, not Support — the Support preamble's denial of workspace truth is the exact falsehood DOC-03 removes"
  - "`WORKSPACE.md` classified Derived (generated prose), `.construct/search.yaml` classified Support (scaffolded config)"
  - "model-routing.yaml rows annotated, not deleted — D-01 keeps it a REQUIRED_PATHS entry"
  - "config-topology.md's Python-approach comparison cell left intact as historically accurate"
  - "`inbox/` tree omission deliberately left unfixed and recorded inline as known pre-existing drift"
metrics:
  duration: ~14m
  tasks: 3
  files: 2
  completed: 2026-07-19
status: complete
---

# Phase 14 Plan 03: Workspace Contract Artifacts and model-routing Deprecation Summary

Made `workspace-contract.md` list the artifacts a real workspace actually contains — classifying the LangGraph checkpoint under a new honest fourth artifact class rather than beneath a preamble that denies it holds workspace truth — and gave `model-routing.yaml` its recorded deprecated-but-scaffolded fate in the last two fence targets.

## What Was Built

**Task 1 — `workspace-contract.md` artifact listing and fourth class** (commit `49399ec`)

Three edits:

1. **New `### Durable orchestration state` section**, placed after the Support table and copying the Derived table's structure exactly: `###` heading, one defining preamble sentence, three-column `Path | Class | Role` table, trailing rule sentence. The single row gives `.construct/workflow/*.sqlite` the `Class` value `durable orchestration state` — a lowercase noun phrase matching the heading, consistent with `source of truth` / `derived` / `support`. The rule sentence records that the directory is **not** in `REQUIRED_PATHS`, is not scaffolded at init, is created lazily at first checkpointer construction, and may legitimately be absent, then cites `adrs/adr-0004-durable-workflow-checkpoints.md` as a plain backticked path per the spec-doc citation convention.

   The class definition was **cited from adr-0004, not re-derived** (D-12 key link). adr-0004's `## Durable orchestration state (artifact class)` section already carries the three-part qualifying test and the argument for why the artifact fits neither existing class; the contract states the classification and defers.

2. **The other two D-12 artifacts into existing tables.** `WORKSPACE.md` → Derived (it is generated prose written by `services/init.py:_write_workspace_doc`). `` `.construct/search.yaml` `` → Support, beside the `model-routing.yaml` row, with the Role cell naming the shipped template's `mock` provider default. Both rows match their destination table's three-column shape and cell style.

3. **Canonical shape tree.** `└── publish/` became `├── publish/`; added `├── WORKSPACE.md` and a final `└── .construct/` subtree containing `search.yaml` and `workflow/`, so the only `└──` at the top level is the last line. No trailing comments were introduced (that is `config-topology.md`'s convention, not this file's).

   Read-only confirmations behind the edits: `schemas/workspace.py:15-26` — `.construct/workflow/` is absent from `REQUIRED_PATHS`, `inbox/` is present; `services/init.py:58-59` scaffolds `search.yaml`; `research_run.py:891` and `curation_run.py:287` both create the checkpoint dir via `mkdir(parents=True, exist_ok=True)` at checkpointer construction.

**Task 2 — Support-table deprecation** (commit `e1774ae`)

The `.construct/model-routing.yaml` row was **kept and annotated**, not deleted. Under D-01 the file stays scaffolded because it is a `REQUIRED_PATHS` entry; deleting the row would make the contract document disagree with the contract the schema enforces. The Role cell now opens with **Deprecated and inert**, states the file is retained only for workspace-contract stability, and names `src/construct/llm/config.yaml` (resolved by `src/construct/llm/config.py`) as the LLM configuration authority. The `support` `Class` value, the three-column shape, the table heading, the preamble, and every sibling row are unchanged.

**Task 3 — `config-topology.md`, both references** (commit `810884c`)

- **Tree entry (line 56).** Comment replaced with the short marker `# DEPRECATED — use llm/config.yaml`, keeping the `#` at column 46 so the fenced tree's alignment with all sibling lines is preserved. No prose note was added below the fence: any additional `model-routing.yaml` mention would have pushed the file's occurrence count to 3 and broken the exact-2 criterion. The detail lives in `workspace-contract.md` and `nfrs.md` §3 instead, which is where the load-bearing record belongs anyway (see D-03 below).
- **§3 comparison row (line 135).** Claude-native cell became `🟡 (DEPRECATED, inert)`, reusing the table's existing marker vocabulary; the rationale column now reads `` LLM config authority is `llm/config.yaml` ``. The **Python-approach cell `✅ (controls routing)` was deliberately left alone** — that table compares against the Python approach, where the file genuinely did control routing, and rewriting it to read uniformly would falsify the comparison (T-14-03-04, accepted). The `db/`, `views/`, `inbox/`, and `workflows/` sibling rows are untouched.

## Key Decisions

- **A fourth class, not a reused one.** Filing the checkpoint under Support would have let Task 1's textual criteria pass while asserting, in the very document being corrected, that an artifact holding the only copy of pending review decisions "does not define workspace truth" — contradicting adr-0004 three files over. Derived was equally wrong: the checkpoint is generated from nothing on disk and is the sole input on resume.
- **Annotate, never delete.** Both `model-routing.yaml` fence targets keep their rows. The deprecation is a documentation correction; removing the artifact would be a workspace-format change, which v0.4.1 lists Out of Scope.
- **`inbox/` left alone and recorded inline.** Its absence from the shape tree is real, pre-existing drift, but unrelated to this phase; fixing it would have made the diff unreviewable against the five criteria. Rather than only noting it here, a bullet was added directly beneath the tree in `workspace-contract.md` marking it a known omission tracked separately — the drift is now visible to a reader of the contract, not just to a reader of this SUMMARY.

## D-03 Collision — Phase 17 (recorded per plan requirement)

Phase 17 (DOC-02) may **delete or rewrite `config-topology.md` wholesale** — REQUIREMENTS DOC-02 reads "`config-topology.md` is either corrected against the real layout or deleted." Task 3's two edits to that file may therefore be discarded by Phase 17. **This is accepted.** No cross-phase dependency is created and Phase 14 does not block on Phase 17.

A Phase 17 executor should treat the Task 3 deprecation notes as **discardable, not load-bearing**. The load-bearing record of `model-routing.yaml`'s fate lives in `nfrs.md` §3 (plan 14-02) and `workspace-contract.md` (Task 2), neither of which Phase 17 owns.

## Deviations from Plan

### Acceptance criterion unsatisfiable as literally written (diagnosed, not worked around)

**Found during:** Task 3 verification.

**Issue:** The tree-alignment criterion listed in `<acceptance_criteria>` is:

```
awk '/├── domains.yaml/{d=index($0,"#")} /model-routing/{m=index($0,"#")} END{exit !(d==m)}' config-topology.md
```

This **cannot pass for any correct edit**. `/model-routing/` matches two lines: the tree entry at 56 and the §3 comparison row at 135. The table row contains no `#`, so the last assignment sets `m=0` unconditionally, while `d=46`. Measured directly: `d=46 m=0`, exit 1.

**Resolution:** No document content was altered to satisfy it. The criterion's *intent* — that the tree line's comment column is unchanged — is correctly expressed by the guarded form already present in the same task's `<verify>` block:

```
awk '/├── domains.yaml/{d=index($0,"#")} /model-routing/{if(index($0,"#")>0)m=index($0,"#")} END{exit !(d==m)}'
```

which passes (`d=46`, `m=46`). Independently confirmed by column dump: sibling template-tree lines 52-60 all place `#` at index 46, and the edited line 56 still does.

**Note on a second latent hazard in the same criterion:** `d` is set by the *last* `├── domains.yaml` match, which is line 105 in the §2 workspace tree — a different tree from the one being edited. It happens to share the index-46 comment column, so the guard passes by coincidence rather than by construction. A future plan reusing this shape should anchor on a unique sibling within the target fence.

**Recommendation for the verifier:** treat the `<verify>`-block form as the correct expression of this guard; the `<acceptance_criteria>` form should be corrected in any future plan reusing it.

This is the fourth plan in Phase 14 (after 14-01, 14-04, 14-02) to hit an unsatisfiable acceptance criterion, and the shape matches the orchestrator's warning: a grep/awk whose match set is wider than the author's section-local mental model.

### Criteria that did NOT trip

The other two hazard shapes the orchestrator flagged were checked and were sound in this plan. The `git diff | grep -cE` sibling-row guard in Task 3 passes at default `-U3` because the adjacent `db/`/`workflows/` rows appear as context lines (leading space), not as `[-+]` lines. No line-anchored `sed -n 'A,Bp'` range was used in this plan's verification.

### Rules applied

No Rule 1/2/3 auto-fixes were required. No Rule 4 architectural decisions arose.

## Verification Results

| Check | Result |
|---|---|
| Task 1 automated verify (`WORKSPACE-CONTRACT-OK`) | Pass |
| Task 2 automated verify (`WC-DEPRECATION-OK`) | Pass |
| Task 3 automated verify (`CONFIG-TOPOLOGY-OK`) | Pass |
| Criterion 2a — all three D-12 artifacts present in workspace-contract.md | Pass (3/3) |
| `### Durable orchestration state` heading count | 1 |
| `.construct/workflow/*.sqlite` row carries `durable orchestration state` | Pass |
| Pitfall-2 guard — `sqlite` rows inside Support table section | 0 |
| `adr-0004` cited in workspace-contract.md | Pass |
| New section states not-required / may-be-absent | Pass |
| Criterion 4a/4b — non-deprecated `model-routing` mentions, both files | 0 and 0 |
| `model-routing.yaml` occurrence count in config-topology.md | 2 (neither deleted) |
| Both config-topology references name `llm/config.yaml` | 2/2 |
| Tree alignment (guarded awk form) | `d=46 m=46` — Pass |
| Comparison table four-column shape | 1 matching row |
| Sibling rows (`db/`, `views/`, `inbox/`, `workflows/`) in diff | 0 |
| Criterion 4e — D-01 scaffolding + `REQUIRED_PATHS` intact | Pass |
| `git status --porcelain -- src/ tests/` | empty |
| Edit fence (D-02) — AGENTS.md, USER-TEST-PLAYBOOK-v03.md, spec-v04-agentworkflows.md, migrations/, .planning/milestones/ | empty (untouched) |
| Full pytest suite | **443 passed**, 2 warnings, 6.04s (≥ 439 required) |

## Threat Mitigations Applied

- **T-14-03-01 (Tampering, `REQUIRED_PATHS` and scaffolding):** `git status --porcelain -- src/construct/schemas/ src/construct/storage/ src/construct/services/` verified empty before the Task 1 commit; `-- src/ tests/` empty before Tasks 2 and 3. `tests/unit` re-run green after Task 2, full suite after Task 3. No code-side file changed.
- **T-14-03-02 (Information Disclosure, artifact-class misread):** the Support-section `sqlite` grep returns 0 and the fourth-class section exists. An operator reading the contract is told the checkpoint holds pending review decisions and is not told it holds no workspace truth.
- **T-14-03-03 (Tampering, partial deprecation):** the exhaustive assertion — every `model-routing` mention in each file must carry a deprecation marker — returns 0 non-deprecated lines in both files, rather than checking known line numbers.
- **T-14-03-04 (Repudiation, historical accuracy):** accepted as planned. The Python-approach cell `✅ (controls routing)` is preserved verbatim.
- **T-14-03-05 (Information Disclosure, `search.yaml` row):** accepted. The row names the file and its `mock` default; it reproduces no `api_key_env` value or secret.

## Known Stubs

None.

## Threat Flags

None — this plan introduces no executable surface and touches no network, auth, or crypto path. Two markdown documents changed; no schema, storage, or service file was modified.

## Notes for Downstream Plans

- **Phase 17 (DOC-02):** the two `config-topology.md` edits are discardable (see D-03 collision above). Do not treat them as a dependency.
- **`inbox/`** remains absent from the `workspace-contract.md` shape tree while present in `REQUIRED_PATHS` — now flagged inline in the document. A future contract-drift phase can close it as a one-line tree addition.
- The `durable orchestration state` class name is now used in exactly two places: adr-0004 (definition) and workspace-contract.md (classification). Any third use should cite rather than restate.

## Self-Check: PASSED

- `CONSTRUCT-CLAUDE-spec/workspace-contract.md` — FOUND
- `CONSTRUCT-CLAUDE-spec/config-topology.md` — FOUND
- `.planning/phases/14-durable-state-config-truth/14-03-SUMMARY.md` — FOUND
- Commit `49399ec` — FOUND
- Commit `e1774ae` — FOUND
- Commit `810884c` — FOUND
