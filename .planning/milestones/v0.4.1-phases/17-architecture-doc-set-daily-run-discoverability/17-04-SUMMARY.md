---
phase: 17-architecture-doc-set-daily-run-discoverability
plan: 04
subsystem: documentation
tags: [documentation, config-topology, model-routing, spec-fence]
requires: ["17-03"]
provides:
  - "config-topology.md deleted; its three roles consolidated into workspace-contract.md / artifact-catalog.md / architecture-overview.md"
  - "spec-v04 model-routing fence closed (deprecated per Phase 14 D-01/D-02)"
affects:
  - CONSTRUCT-CLAUDE-spec/README_FIRST.md
  - CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md
tech-stack:
  added: []
  patterns: ["single-source-of-truth doc consolidation (delete duplicated authority rather than correct a fourth copy)"]
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-spec/README_FIRST.md
    - CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md
  deleted:
    - CONSTRUCT-CLAUDE-spec/config-topology.md
decisions:
  - "D-06: Deleted config-topology.md (stale 2026-04-23) rather than correcting it — its three sections are already owned by milestone-corrected docs; correcting would create a fourth copy of the workspace contract."
  - "D-07: Marked model-routing.yaml deprecated/inert in spec-v04:211 and reframed the :557 dual-config risk as Resolved, without deleting model-routing.yaml (workspace-format change deferred to v0.5+)."
metrics:
  duration: "~5m"
  completed: "2026-07-25"
  tasks: 2
  files_changed: 3
status: complete
---

# Phase 17 Plan 04: Delete config-topology.md & Close model-routing Fence Summary

Deleted the stale `config-topology.md`, redirected its one remaining live spec-tree deferrer (README_FIRST.md), and marked the last two `model-routing.yaml` references in `spec-v04-agentworkflows.md` deprecated — closing DOC-02's config-truth work and D-07's Phase 14 hand-off.

## What Was Built

**Task 1 — Delete config-topology.md and redirect its deferrer (D-06)** — commit `6273bef`
- `git rm CONSTRUCT-CLAUDE-spec/config-topology.md`. The file (dated 2026-04-23) was stale across all three sections; its roles are owned by `workspace-contract.md` (workspace artifacts / §3), `artifact-catalog.md` (capability/CLI/MCP inventory), and `architecture-overview.md` (layer/deployment model). The model-routing deprecation truth already lives in `workspace-contract.md` and `nfrs.md`, so nothing was lost.
- Redirected `README_FIRST.md:74`: the directory-layout row that linked `config-topology.md` now points to `workspace-contract.md` (workspace directory layout) with the implementation inventory attributed to `artifact-catalog.md`.
- The self-reference at former `config-topology.md:82` disappeared with the file.

**Task 2 — Close the model-routing fence in spec-v04-agentworkflows.md (D-07)** — commit `00a801c`
- `:211` config-surfaces row: `.construct/model-routing.yaml` reframed as **DEPRECATED / inert** (Phase 14 D-01), naming `src/construct/llm/config.yaml` (already listed at :209) as the LLM config authority.
- `:557` risk row: "Dual config confusion" severity changed from `Medium` (open, "validation warns on conflict") to `Resolved` — model-routing deprecated per Phase 14 D-01/D-02, `llm/config.yaml` sole LLM authority, `search/config.yaml` owns search.
- `model-routing.yaml` itself was NOT deleted and `REQUIRED_PATHS` was untouched (deferred to v0.5+, per plan prohibition).

## Intentional Deletion

`CONSTRUCT-CLAUDE-spec/config-topology.md` was removed via `git rm` as the primary deliverable of Task 1 (D-06). The post-commit deletion check flagged it in commit `6273bef` — this is expected and correct, not a Rule 1 regression. Grep-verified zero code/test references before deletion; the only live spec-tree deferrer was `README_FIRST.md:74`, redirected in the same commit.

## No-Dangling-Reference Verification

Before and after deletion, `grep -rn config-topology CONSTRUCT-CLAUDE-spec/` was run:
- Before: two hits — `README_FIRST.md:74` (redirected) and `config-topology.md:82` (self-reference, removed with the file).
- After: zero hits under `CONSTRUCT-CLAUDE-spec/`.
- Remaining repo-wide hits live only under `.planning/` (STATE/ROADMAP/REQUIREMENTS) where they record the delete *decision* — explicitly out of scope per the plan's prohibitions (not deferrers). The sealed `v0.4-MILESTONE-AUDIT.md` was not edited.
- No references under `src/`, `tests/`, or `CONSTRUCT-CLAUDE-impl/`.

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes, no auth gates, no checkpoints.

## Verification Results

- `test ! -e CONSTRUCT-CLAUDE-spec/config-topology.md` — PASS (file deleted)
- `grep -rn config-topology CONSTRUCT-CLAUDE-spec/` — returns nothing (PASS)
- `README_FIRST.md` no longer references config-topology.md — PASS
- Every surviving `model-routing` mention in spec-v04 framed as deprecated/inert; `llm/config.yaml` named authoritative — PASS
- `pytest tests/contract/test_doc_command_references.py -x` — 37 passed, 1 skipped
- `pytest -q` full suite — 524 passed, 1 skipped

## Known Stubs

None. This is a documentation-only plan; no data-wired components introduced.

## Self-Check: PASSED
- MODIFIED CONSTRUCT-CLAUDE-spec/README_FIRST.md — FOUND
- MODIFIED CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md — FOUND
- DELETED CONSTRUCT-CLAUDE-spec/config-topology.md — CONFIRMED ABSENT
- Commit 6273bef — FOUND
- Commit 00a801c — FOUND
