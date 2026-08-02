# Phase 19 — Deferred Items

Out-of-scope discoveries logged during execution. Not fixed, by the scope
boundary rule: an executor auto-fixes only what its own changes caused. Recorded
so they are not mistaken for regressions.

## `tests/integration/test_workspace_contract_migration.py::TestFixtureRoot` fails in a git worktree

**Found independently during:** plan 19-01 (plan-level full-suite verification),
plan 19-02 (Task 1 verification, `pytest tests/llm tests/integration`), and
plan 19-03 (which repaired it locally in its own worktree — see below).

**Symptom:** two failures — `test_my_construct_has_canonical_layout` and
`test_ping_eon_has_canonical_layout` — both asserting
`Missing canonical directory in .../test-ws/<ws>: digests/`.

**Cause:** environmental, not a code defect. `.gitignore` line 1 ignores
`test-ws/`, so the fixture workspaces are only *partly* tracked: `cards/`,
`refs/`, `log/`, `connections.json`, `domains.yaml`, `governance.yaml` and
`search-seeds.json` are committed, while `digests/`, `publish/` and `.construct/`
exist only in the main checkout as untracked, **empty** directories. Git cannot
represent an empty directory, so a `git worktree` checkout materialises an
incomplete fixture, and this test — which reads `test-ws/` from disk rather than
from a `tmp_path` — sees a workspace missing three of its six canonical
directories.

**Corroboration that this is pre-existing:** it reproduces on the plans' shared
base commit (`5eb61d4`) in any worktree and passes in the main checkout. Three
plans touching disjoint file sets (checkpointer functions; HTTP surface; result
boundary) all hit it identically. Plan 19-03 confirmed the diagnosis
constructively by creating the missing directories in its worktree, after which
the tests passed.

**Why it is not fixed here:** no Phase 19 plan owns this test, and none touches a
fixture or a `test-ws/` path. Fixing it is a decision about the fixture contract,
with two candidate approaches:

1. Commit the empty directories with `.gitkeep` sentinels so a worktree checkout
   materialises the full canonical layout.
2. Have the test build its fixture (or skip) rather than read a partly-ignored
   tree from disk.

**Expected recurrence:** every worktree-executed plan in this phase and in future
phases will surface these two failures until the fixture contract is settled.
Treat them as a known-red baseline, not a regression signal.
