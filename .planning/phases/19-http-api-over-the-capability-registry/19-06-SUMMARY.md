---
phase: 19-http-api-over-the-capability-registry
plan: 06
subsystem: api
tags: [http, security, dns-rebinding, csrf, cors, origin-validation, constant-time, fastapi, starlette, contract-tests]

# Dependency graph
requires:
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-01's LocalhostGuard / ALLOWED_HOSTS, the {\"detail\": ...} refusal shape, and tests/contract/conftest.py's app-factory fixture"
provides:
  - "ALLOWED_ORIGINS and allowed_origins(port) — the origin allowlist derived from ALLOWED_HOSTS and the launch port, so a non-default --port is not silently foreign"
  - "_split_host_port — a Host authority parser that keeps bracketed IPv6 literals intact and refuses a non-numeric port"
  - "tests/contract/test_http_security.py — the full HTTP-05 matrix (37 tests): Host, Origin, token, ordering, one-body-shape, no-CORS, drive-by content types, concurrency, and the tree-hash ordering proof"
  - "The measured basis for D-05's security rationale, pinned: no drive-by content type reaches a capability with a parsed payload on FastAPI 0.141.1"
affects: [19-07, 19-10, 21-static-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Derived-not-listed, applied to the origin allowlist: origins are built from ALLOWED_HOSTS × the request's validated Host port, never spelled a second time"
    - "Per-request derivation from an already-validated header, rather than a constructor argument — the guard needs no knowledge of the launch port because every browser puts it in Host"
    - "Effect-level refusal proof: a tree hash before/after, with a positive control, instead of a status-code assertion"
    - "Mutation-checked matrix: each control was reverted in turn and the matrix confirmed to fail"

key-files:
  created:
    - tests/contract/test_http_security.py
  modified:
    - src/construct/api/middleware.py

key-decisions:
  - "D-21 recorded in the module docstring: an absent Origin is allowed, a present-and-not-allowlisted one is refused with 403 — the MCP specification's own wording"
  - "D-22 recorded: the token travels in the non-CORS-safelisted X-Construct-Token header, never a query string, and no CORS middleware is installed, so the token doubles as the CSRF control"
  - "D-23 recorded: Host, Origin and token are checked in one middleware, in that order, through one refusal rendering"
  - "The origin allowlist is derived per request from the validated Host, not from a constructor argument — the launch port reaches the guard in every browser's Host header, and a page cannot forge Origin, so the derivation costs nothing in strength and removes the class of bug where --port 9000 makes every browser request foreign"
  - "A Host whose port is not a string of digits is refused with 400 rather than tolerated — the port is now an input to the derived origin set, so accepting '127.0.0.1:evil' would put attacker-controlled text into it"
  - "The drive-by content-type property is pinned by test, not enforced by the guard: it holds today because FastAPI 0.141.1 defaults strict_content_type=True, which the test records as a framework default rather than a project control"
  - "LocalhostGuard's allowed_origins argument is now ADDITIVE to the derived set (stored as extra_origins), which keeps api/app.py's existing call site correct without editing a file another wave-2 plan owns"

requirements-completed: [HTTP-05]

coverage:
  - id: D1
    description: "A request whose Host header names a foreign hostname is refused with 400; the port is stripped before the comparison, and the IPv6 loopback literal is accepted"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_foreign_host_is_refused_with_400"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_every_loopback_host_spelling_is_accepted_with_or_without_a_port"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_malformed_host_authority_is_refused"
        status: pass
    human_judgment: false
  - id: D2
    description: "A request whose Origin header is present and not allowlisted is refused with 403; a request with no Origin header at all is allowed, so curl, the CLI and any scripted client keep working"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_foreign_origin_is_refused_with_403_before_the_seam"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_an_absent_origin_is_allowed"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_the_servers_own_loopback_origin_is_allowed"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_the_origin_allowlist_follows_the_launch_port"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_security.py#test_the_derived_origin_set_covers_every_allowed_host_spelling"
        status: pass
    human_judgment: false
  - id: D3
    description: "A request with a missing or wrong per-launch token is refused with 401, and the comparison is constant-time"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_missing_token_is_refused_before_the_seam"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_token_differing_in_one_character_is_refused"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_security.py#test_the_token_comparison_is_constant_time_and_on_bytes"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_non_ascii_token_is_refused_rather_than_crashing"
        status: pass
    human_judgment: false
  - id: D4
    description: "The three checks run in the order Host, Origin, token, and all three run before any capability is dispatched"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_the_checks_run_in_the_order_host_origin_token"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_every_refusal_carries_the_same_body_shape"
        status: pass
    human_judgment: false
  - id: D5
    description: "A rejected request naming a write capability leaves the workspace byte-identical — proven by hashing the tree before and after, not by reading a status code"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_refused_write_leaves_the_tree_byte_identical"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_the_same_payload_with_correct_headers_does_change_the_tree"
        status: pass
      - kind: other
        ref: "mutation check: refusing AFTER call_next fails test_a_refused_write_leaves_the_tree_byte_identical[foreign-origin] with the created card file named in the diff"
        status: pass
    human_judgment: false
  - id: D6
    description: "No CORS middleware is installed, so a cross-origin read is blocked by the browser and the non-safelisted token header forces a preflight that nothing answers"
    requirement: HTTP-05
    verification:
      - kind: unit
        ref: "tests/contract/test_http_security.py#test_no_cors_middleware_is_installed"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_cross_origin_preflight_is_answered_by_nothing"
        status: pass
    human_judgment: false
  - id: D7
    description: "A request whose body is text/plain, form-encoded, or carries no content type does not reach a capability with a parsed payload"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_drive_by_content_type_never_reaches_a_capability"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_a_json_content_type_is_the_positive_control"
        status: pass
    human_judgment: true
    rationale: "The four rows pass, and the three that matter for CORS (text/plain, form-encoded, multipart) hold because FastAPI refuses to parse a non-JSON media type into a body model. The typeless row holds for a different and weaker reason — FastAPI 0.141.1's strict_content_type default — which is a framework behaviour this project does not enforce. The test pins it, so a regression is loud rather than silent, but a reader should know the property is inherited rather than owned before treating it as a control."
  - id: D8
    description: "The launch token is minted once per process and never rotated mid-run, so concurrent requests carrying it all pass and a concurrent request carrying a wrong token is refused regardless of interleaving"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py#test_concurrent_good_tokens_all_pass_while_a_bad_one_is_refused"
        status: pass
    human_judgment: false

# Metrics
duration: 9 min
completed: 2026-08-03
status: complete
---

# Phase 19 Plan 06: Localhost Hardening — the Measured Control Set Summary

**The HTTP trust boundary is now a measured control set rather than a plausible one: the origin allowlist is derived from the launch port instead of hard-coded, and a refused write is proven to change nothing on disk by hashing the workspace tree before and after, with a positive control proving the payload would otherwise have written.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-02T22:49:00Z
- **Completed:** 2026-08-02T22:58:00Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- **The origin allowlist follows the launch port.** 19-01 left `ALLOWED_ORIGINS` portless and said so honestly in a docstring; the consequence was that `construct serve --port 9000` would make *every* browser request foreign, with a symptom ("the UI stopped working") that looks exactly like a security control doing its job. `allowed_origins(port)` derives the set from `ALLOWED_HOSTS` × the port carried in the request's already-validated `Host`, so no module needs to be told the port. The negative half is asserted too: a *different* loopback port (Vite on 5173) is still 403.
- **The `Host` authority is parsed rather than split.** `_split_host_port` keeps `[::1]:8787` intact — the naive `split(":", 1)` cuts inside the IPv6 address and turns the loopback into a 400 that looks deliberate — and refuses a non-numeric port outright, because the port is now an input to the derived origin set.
- **"Refused before it reaches a capability" is asserted about the workspace, not about a status code.** A guard that returned 403 *after* dispatching would satisfy every status-code assertion in this phase. `_tree_hashes` maps every file under the install root to its content hash; the foreign-`Origin`, missing-token and foreign-`Host` cases each send a *fully valid* `knowledge.card.create` and assert the mapping is unchanged, and a positive control sends the identical payload with correct headers and asserts it changes.
- **The matrix was mutation-checked, not just run.** Four controls were reverted in turn and the matrix confirmed to fail each time: `str` token comparison (1 failure), portless origin set (1), first-colon `Host` split (1), and refusing *after* `call_next` (3 failures, with `demo/cards/refused-card.md` named in the diff). A green suite that stays green under mutation is not evidence; this one does not.
- **D-21, D-22 and D-23 are recorded where the next reader meets them** — in the guard's module docstring, together with the three advisories the control set derives from (`GHSA-w48q-cv73-mx4w`, `CVE-2025-66416`, `GHSA-89vp-x53w-74fx`), the measured facts about `TrustedHostMiddleware`, and an explicit statement that adding permissive CORS would dismantle the property the route shape was chosen for.
- **The one edit that would silently undo this is guarded from two sides.** `test_no_cors_middleware_is_installed` inspects the built stack; `test_a_cross_origin_preflight_is_answered_by_nothing` sends the real `OPTIONS` a browser sends before it will let a page use `X-Construct-Token`, and asserts no `Access-Control-Allow-Origin` comes back.

## Task Commits

1. **Task 1: The complete measured control set in one guard** — `f8e7edf` (feat)
2. **Task 2: Prove rejection precedes any capability effect** — `3f6c47a` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `src/construct/api/middleware.py` — `ALLOWED_ORIGIN_SCHEME`, `allowed_origins(port)`, `ALLOWED_ORIGINS`, `_split_host_port`; `LocalhostGuard.dispatch` now derives the permitted origin set per request; the module docstring becomes the decision record for D-21/D-22/D-23
- `tests/contract/test_http_security.py` (new, 647 lines) — 37 tests: the Host matrix (6 accept spellings, 1 foreign, 4 malformed), the Origin matrix (absent, 3 own-origin spellings, foreign, launch-port derivation, derivation-vs-`ALLOWED_HOSTS`), the token matrix (missing, one-character, correct, `compare_digest`-on-bytes, non-ASCII), ordering, one-body-shape, no-CORS, the unanswered preflight, the 4-row drive-by content-type matrix plus its positive control, concurrency, and the 3 tree-hash rejection cases plus their positive control

## Decisions Made

Beyond the plan's named D-21 / D-22 / D-23:

- **The origin allowlist is derived from the request's validated `Host`, not from a constructor argument.** The plan says "built from the launch host and port"; the launch port is not visible to `middleware.py` and `app.py` — which passes the origin set today — is owned by a concurrently-executing plan this wave. Deriving from `Host` is strictly better than plumbing the port through anyway: a browser sets `Origin` itself and a page cannot forge it, while a non-browser client that *could* forge it simply omits it (which D-21 already allows), so the matched value is trustworthy in precisely the case that matters, and the port is only ever used to *narrow* which loopback origins are accepted.
- **`LocalhostGuard(allowed_origins=...)` is now additive**, stored as `self.extra_origins` and unioned with the derived set. This keeps `api/app.py`'s existing call site correct without editing a file another wave-2 plan owns. `app.py::_allowed_origins()` is now redundant with `middleware.ALLOWED_ORIGINS` — see "Next Phase Readiness".
- **A malformed `Host` authority is a 400.** Not in the plan; it follows from the derivation. `127.0.0.1:evil` would otherwise contribute `http://127.0.0.1:evil` to the permitted set — harmless in practice, since no browser would ever send a matching `Origin`, but putting attacker-controlled text into an allowlist for no reason is the kind of thing that is only harmless until the code around it changes.
- **The drive-by content-type property is pinned by test rather than enforced by the guard.** See the measurement below; a fourth check in the guard would also have applied to the routes plans 19-02 and 19-05 are adding this wave, which is not this plan's call to make.
- **`ALLOWED_ORIGIN_SCHEME` is `http` only.** An `https` page fetching `http://127.0.0.1` is blocked by the browser as mixed content before this server sees it, so an `https` loopback origin is not a request shape that exists here.

## Measured Facts

Recorded because they are the load-bearing evidence behind two claims, and both were measured in this session rather than assumed:

| Content type on a JSON body | FastAPI 0.141.1 | Reached a capability? |
|---|---|---|
| `application/json` | 200 | yes |
| `application/vnd.api+json` | 200 | yes (not a CORS-simple type — still preflighted) |
| `text/plain` | 422 | no |
| `application/x-www-form-urlencoded` | 422 | no |
| `multipart/form-data` | 422 | no |
| *(none)* | 422 | no |

The first three refusals are FastAPI declining to parse a non-JSON media type into a body model. The typeless row is different in kind: `fastapi/routing.py` reads `if not content_type_value: if not actual_strict_content_type: json_body = await request.json()`, and `strict_content_type` defaults to `Default(True)`. A `fetch` of a typeless `Blob` is a CORS-simple request that sends no `Content-Type` at all, so on a FastAPI without that default it *would* deliver parseable JSON. The property is therefore inherited from the framework, not owned by this project — which is why the test says so in its docstring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created a `.venv` symlink so the documented test invocation works in this worktree**

- **Found during:** Task 1 setup
- **Issue:** Every `<verify>` and acceptance criterion invokes `.venv/bin/python`; a git worktree has no `.venv`.
- **Fix:** `ln -s ../../../.venv .venv` — the pattern the repository's own `.gitignore` documents in a comment and ignores in both forms. Identical to 19-01's deviation 2.
- **Files modified:** none tracked (the symlink is gitignored and disappears with the worktree)
- **Verification:** `.venv/bin/python -V` → Python 3.14.5

**2. [Rule 2 - Missing Critical] A `Host` with a non-numeric port is refused rather than tolerated**

- **Found during:** Task 1
- **Issue:** Once the origin allowlist is derived from the `Host` port, the port stops being inert text that gets discarded and becomes an input to a security decision. `Host: 127.0.0.1:evil` would have contributed `http://127.0.0.1:evil` to the permitted origin set.
- **Fix:** `_split_host_port` returns `("", None)` for a non-digit port, an unterminated bracket, or trailing text after `]`, all of which the existing `host not in ALLOWED_HOSTS` check then answers with 400 through the same rendering.
- **Files modified:** `src/construct/api/middleware.py`
- **Verification:** `test_a_malformed_host_authority_is_refused` (4 parametrised cases)
- **Committed in:** `f8e7edf`

### Design choices that differ from the plan's literal wording

Recorded because they are visible in the diff, not because they change scope:

- The plan's action says to declare `ALLOWED_ORIGINS` "built from the launch host and port". The symbol exists and is derived from `ALLOWED_HOSTS`, but the **port** arrives per request from the validated `Host` rather than from launch state — see Decisions Made for why that is stronger, not weaker, and why it also avoids editing `api/app.py`, which plan 19-05 holds this wave.
- The plan's behavior block lists the content-type rows under Task 1's `<action>` for the *guard*. They are implemented as tests only. The guard gained no fourth check, because the property already holds and a fourth check would have applied to routes two concurrently-executing plans are adding.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** No scope creep. Every plan acceptance criterion is met as written.

## Issues Encountered

**The two known-red worktree baseline failures, untouched.**
`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::{test_my_construct_has_canonical_layout, test_ping_eon_has_canonical_layout}` fail in any git worktree because `test-ws/` is gitignored and `digests/`, `publish/` and `.construct/` exist only as untracked directories in the main checkout. Documented in this phase's `deferred-items.md`; not a Phase 19 regression and explicitly out of scope. Full suite otherwise: **893 passed, 22 skipped**.

## Known Stubs

None. No `TODO`, `FIXME`, placeholder value, skipped test or unrun `<verify>` was introduced by this plan. Both `<verify>` commands for both tasks were run and are green.

One inherited-rather-than-owned property is recorded above and carried in `coverage.D7.rationale` with `human_judgment: true` rather than being presented as a control this project enforces: the typeless-body row of the drive-by content-type matrix holds because of FastAPI 0.141.1's `strict_content_type` default. It is pinned by a passing test, so a regression is loud.

## Flagged Assumptions Carried Forward

- **RESEARCH assumption A3** — that `X-Construct-Token` is not CORS-safelisted, and therefore that any cross-origin request carrying it is preflighted and blocked. Still standards-derived rather than browser-measured. This plan strengthens the *server-side* half of it (`test_a_cross_origin_preflight_is_answered_by_nothing` proves nothing here answers a preflight), but whether a real browser sends one remains plan **19-10**'s manual verification. If A3 is wrong, the token stops doubling as the CSRF control and `Origin` validation becomes load-bearing — which the derived allowlist now makes materially stronger than it was, but does not make sufficient on its own.

## Threat Flags

None. No security-relevant surface outside the plan's `<threat_model>` was introduced. Every register row this plan owns is mitigated and covered:

| Threat | Mitigation shipped | Proven by |
|---|---|---|
| T-19-01 Host / rebinding | port-stripped `Host` must be in `ALLOWED_HOSTS`, else 400 pre-dispatch; bracketed IPv6 parsed, malformed authority refused | `test_a_foreign_host_is_refused_with_400`, `test_every_loopback_host_spelling_is_accepted_with_or_without_a_port`, `test_a_malformed_host_authority_is_refused` |
| T-19-12 Origin | present-and-not-allowlisted → 403; absent allowed; allowlist derived from the launch port | `test_a_foreign_origin_is_refused_with_403_before_the_seam`, `test_an_absent_origin_is_allowed`, `test_the_origin_allowlist_follows_the_launch_port`, `test_the_derived_origin_set_covers_every_allowed_host_spelling` |
| T-19-02 drive-by CSRF | no CORS middleware; non-safelisted token header; no simple content type reaches a capability | `test_no_cors_middleware_is_installed`, `test_a_cross_origin_preflight_is_answered_by_nothing`, `test_a_drive_by_content_type_never_reaches_a_capability` |
| T-19-07 token comparison | `secrets.compare_digest` on bytes; one-character difference refused; a high byte is a 401, not a 500 | `test_the_token_comparison_is_constant_time_and_on_bytes`, `test_a_token_differing_in_one_character_is_refused`, `test_a_non_ascii_token_is_refused_rather_than_crashing` |
| T-19-08 token transport | header only, never a query string (unchanged from 19-01; re-stated in the guard docstring) | `test_http_surface.py#test_the_token_never_appears_in_a_url` |
| T-19-21 a rejected request still having an effect | tree-hash before/after on a genuine write capability, with a positive control | `test_a_refused_write_leaves_the_tree_byte_identical`, `test_the_same_payload_with_correct_headers_does_change_the_tree` |

## User Setup Required

None.

## Next Phase Readiness

- **For 19-07 (the shared error boundary):** all four refusal paths still render through the single `_refusal` function, and `test_every_refusal_carries_the_same_body_shape` asserts the 400/403/401 bodies are `{"detail": <non-empty str>}` and contain no echoed attacker text. Swapping in `api/errors.py` is one function, and that test is what will catch it if the swap forks the shape.
- **For 19-10 (manual browser verification):** the server-side half of A3 is now proven; what remains is a real browser.
- **One hand-off, deliberately not taken:** `src/construct/api/app.py::_allowed_origins()` is now redundant — it returns exactly `middleware.ALLOWED_ORIGINS`, and the guard would derive the same set (and more) if it were passed nothing. It is left in place because `app.py` belongs to plan 19-05 this wave; deleting it is a one-line follow-up for whoever next owns that file, and it is harmless in the meantime because the argument is unioned rather than substituted.

## Self-Check: PASSED

- `src/construct/api/middleware.py` and `tests/contract/test_http_security.py` both exist on disk.
- Both task commits present in `git log`: `f8e7edf`, `3f6c47a`.
- `git diff --diff-filter=D HEAD~2 HEAD` is empty — no file was deleted.
- Working tree clean and no untracked files after each task commit.
- Plan `<verification>` re-run at close-out: `tests/contract` → 415 passed / 22 skipped; full suite → 893 passed / 22 skipped, with only the two documented out-of-scope `test-ws` worktree failures.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-03*
