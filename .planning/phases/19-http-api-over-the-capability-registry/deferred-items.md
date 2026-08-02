# Deferred items — Phase 19

Out-of-scope discoveries logged during execution. Not fixed; recorded so they are
not mistaken for regressions.

## `test_workspace_contract_migration::TestFixtureRoot` fails inside a git worktree

**Found during:** plan 19-02, Task 1 verification (`pytest tests/llm tests/integration`)

**Symptom:** two failures —
`TestFixtureRoot::test_my_construct_has_canonical_layout` and
`TestFixtureRoot::test_ping_eon_has_canonical_layout` — both asserting
`Missing canonical directory ...: digests/`.

**Cause:** environmental, not a code defect. `test-ws/` is gitignored
(`.gitignore:1`) with a handful of fixture files force-added, and `digests/` is an
**empty** directory. Git cannot represent an empty directory, so it exists in the
main checkout (`/Users/mab/dev/mabstruct/construct/test-ws/ping-eon/digests`) but
is never materialised in a linked worktree. Any phase executed in a worktree will
see these two failures.

**Unrelated to this plan:** the assertions touch workspace fixture layout only;
plan 19-02 changed two checkpointer functions, one test module, and one ADR.

**Not fixed because:** the fix is either scaffolding the empty directory in the
test fixture setup or teaching the test to skip when the fixture root is absent —
both are changes to a workspace-contract test that no Phase 19 plan owns.
