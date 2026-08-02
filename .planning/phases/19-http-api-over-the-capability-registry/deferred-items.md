# Phase 19 — Deferred Items

Out-of-scope discoveries logged during execution. Not fixed, by the scope
boundary rule: an executor auto-fixes only what its own changes caused.

## `tests/integration/test_workspace_contract_migration.py::TestFixtureRoot` fails in a git worktree

**Found during:** plan 19-01, the plan-level full-suite verification.

**Symptom:** two failures —
`test_my_construct_has_canonical_layout` and `test_ping_eon_has_canonical_layout` —
both asserting `Missing canonical directory in .../test-ws/<ws>: digests/`.

**Cause:** environmental, not a code defect. `.gitignore` line 1 ignores
`test-ws/`, so the fixture workspaces are only *partly* tracked: `cards/`,
`refs/`, `log/`, `connections.json`, `domains.yaml`, `governance.yaml` and
`search-seeds.json` are committed, while `digests/`, `publish/` and `.construct/`
exist only in the main checkout as untracked directories. A `git worktree`
checkout therefore materialises an incomplete fixture, and this test — which
reads `test-ws/` from disk rather than from a `tmp_path` — sees a workspace
missing three of its six canonical directories.

**Why it is not fixed here:** plan 19-01 touches no fixture and no test-ws path.
The failure reproduces on the plan's base commit in any worktree and passes in
the main checkout. Fixing it is a decision about the fixture contract (commit
the empty directories with `.gitkeep`, or have the test build/skip rather than
read a partly-ignored tree), which is a separate work item.

**Verified green in this worktree:** everything else — 826 passed, 22 skipped.
