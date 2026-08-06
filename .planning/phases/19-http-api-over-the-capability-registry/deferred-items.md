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

---

## Assumption A3 (the cross-origin refusal) was never exercised

**Found during:** plan 19-10 (the blocking human-verify checkpoint), 2026-08-06.

**What is open:** the design's CSRF story is that `X-Construct-Token` is **not** a
CORS-safelisted header, so a cross-origin page carrying it is preflighted and
blocked — and no `CORSMiddleware` is installed to answer that preflight.
`middleware.py` states the blind spot itself: *a test client sends no `Origin` of
its own*. `curl` does not implement CORS at all. **Only a real browser enforces
it**, and step 6 of `HOWTO-verify-phase-19.md` — the one step that tests it — was
not run.

**Consequence:** T-19-02 (drive-by CSRF, severity high) is mitigated *by design*
and unproven *as deployed*. It is not a known defect; it is an unmeasured
mitigation, recorded so the phase's pass is not read as covering it.

**Why it is not closed here:** it needs a browser process and about a minute.
Phase 21 is the natural owner, because it serves the first page from this API and
because the regression to watch for lives there: a `CORSMiddleware` added for
convenience turns this refusal into a capability list.

**How to close it:** from a console on any foreign origin (`https://example.com`),
`fetch("http://127.0.0.1:<port>/api/capabilities", {headers: {"X-Construct-Token":
"<token>"}})`. Pass = the browser blocks it, with no `access-control-allow-origin`
on the preflight and no response body.

## The API token file path does not vary by port

**Found during:** plan 19-10's dry run, 2026-08-06.

**Symptom:** the token file is `{install_root}/.construct/api-token` regardless of
`--port`. A second `construct serve --port 8788 --install-root X` overwrites the
on-disk token of the server already running on 8787 against the same install root.
The first server keeps working — it holds its token in memory — so the on-disk copy
now authenticates against the *second* server only, silently.

**Why it matters beyond the test:** **Phase 21 reads that file.** A served app
would authenticate against whichever server launched last, regardless of which one
it is talking to.

**Why it is not fixed here:** it is a token-delivery design decision, not a bug in
a Phase 19 deliverable, and 19-10's verdict is that token delivery **needs
redesign** for the served shell anyway. Whether the file becomes per-port, per-
server, or is replaced by a mechanism that does not use a file belongs to that
redesign. No test covers this today.
