---
phase: 19-http-api-over-the-capability-registry
plan: 10
subsystem: api
tags: [http, loopback, token-delivery, cors, csrf, manual-verification, human-verify]

requires:
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-01's `construct serve` — the one-command launcher, its loopback bind, the printed token and the 0600 token file"
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-05's discovery endpoint over registry.list() — the 30-capability surface a browser reads"
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-06's LocalhostGuard — the Host/Origin/token matrix whose deployed behaviour this checkpoint exercises"
provides:
  - "A human verdict on the two rows 19-VALIDATION.md marks manual-only: a real browser process reached the running server, and the token reached it"
  - "The token-delivery verdict Phase 21 needs: stdout plus a 0600 file NEEDS REDESIGN for the served shell"
  - "Two carried-forward findings no test covers: assumption A3 is still unverified, and the token file path does not vary by port"
  - "HOWTO-verify-phase-19.md — the executable walkthrough, kept as the record of how the check was run"
  - "A closed third instance of T-18-32 (help.suggest) plus the generic success-body sweep that replaces naming instances one at a time"
affects: [phase-21, phase-22, token-delivery, served-shell, csrf]

actuals:
  tokens: ~6000
  tasks: 1
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Sweep, don't name: a criterion asserted over every registered capability that can be invoked, with a declared exclusion list carrying reasons and a non-vacuity floor — instances found by hand become classes closed by measurement"

key-files:
  created:
    - .planning/phases/19-http-api-over-the-capability-registry/19-10-SUMMARY.md
  modified:
    - src/construct/services/help.py
    - tests/contract/test_result_boundary.py

key-decisions:
  - "Step 6 (the cross-origin refusal) was not exercised, and is recorded as a GAP rather than folded into the pass. It is the only test of assumption A3 that exists — curl cannot make it — so T-19-02's mitigation is unproven as deployed and Phase 21 inherits that."
  - "Token delivery is judged NEEDS REDESIGN, not 'workable'. Moving a token from a terminal into a browser by hand is not a flow the served shell can be built on; Phase 21 must own a delivery mechanism before it builds forms against the API."
  - "The help.suggest leak found during the dry run was fixed inline rather than deferred, because the fix is one field and the remedy is the sweep — deferring would have left criterion 3 knowingly violated at the phase boundary."
  - "19-VALIDATION.md's frontmatter (status: draft, nyquist_compliant) and its 16 TBD task IDs are deliberately left for /gsd-validate-phase §6, which resolves them against the executed plans. Hand-flipping them here would fake that pass."

patterns-established:
  - "Manual-checkpoint honesty: an unexercised step is recorded as unverified with its consequence named, not omitted from the pass table"

requirements-completed: [HTTP-01, HTTP-05]

coverage:
  - id: D1
    description: "A real browser process, at the printed loopback URL and carrying the launch token, reached a capability on the running server"
    requirement: HTTP-01
    verification:
      - kind: manual_procedural
        ref: "HOWTO-verify-phase-19.md steps 1-5 (browser console fetch to /api/capabilities and POST /api/capabilities/workspace.status)"
        status: pass
    human_judgment: true
    rationale: "A TestClient never opens a socket; only a separate browser process can show that loopback is bound and reachable as deployed"
  - id: D2
    description: "The printed URL is the loopback address, and the token file is owner-only with contents matching stdout"
    requirement: HTTP-01
    verification:
      - kind: manual_procedural
        ref: "HOWTO-verify-phase-19.md steps 1-2 (127.0.0.1 in the banner; ls -l shows -rw-------)"
        status: pass
    human_judgment: true
    rationale: "The suite asserts the bind constant; this asserts the deployment"
  - id: D3
    description: "The same browser invocation with the token header removed was refused rather than answered"
    requirement: HTTP-05
    verification:
      - kind: manual_procedural
        ref: "HOWTO-verify-phase-19.md step 5 (401 {\"detail\":\"missing or invalid token\"})"
        status: pass
    human_judgment: true
    rationale: "Refusal from a real browser origin, where the deployed guard runs before routing"
  - id: D4
    description: "The token-delivery ergonomics verdict for Phase 21 is recorded"
    requirement: HTTP-05
    verification:
      - kind: manual_procedural
        ref: "HOWTO-verify-phase-19.md step 8 — verdict: NEEDS REDESIGN"
        status: pass
    human_judgment: true
    rationale: "A UX judgement, which is the deliverable; research open question 1 was resolved by preference and needed measuring"
  - id: D5
    description: "The drive-by CSRF refusal as a real browser enforces it (assumption A3) — NOT EXERCISED"
    requirement: HTTP-05
    verification:
      - kind: manual_procedural
        ref: "HOWTO-verify-phase-19.md step 6 — not run"
        status: unknown
    human_judgment: true
    rationale: "Only a browser implements CORS, so no automated or curl-based check can substitute. Carried forward as an open gap, not a pass."
  - id: D6
    description: "The third T-18-32 success-path path leak (help.suggest) is closed, and the class is guarded by a sweep over every invocable capability rather than a third named test"
    verification:
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_no_successful_capability_body_carries_an_absolute_path"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_every_capability_excluded_from_the_sweep_still_exists"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-08-06
status: complete
---

# Phase 19 Plan 10: Manual Verification Summary

**A real browser reached the running server on loopback, read all 30 capabilities with their input schemas, invoked one with the launch token and was refused without it — and the two things the walkthrough could not close are recorded as open: the cross-origin refusal was never exercised, so assumption A3 remains unverified, and token delivery is judged not good enough for Phase 21 to build on.**

## Performance

- **Duration:** ~25 min (walkthrough + the defect it surfaced)
- **Tasks:** 1 (one blocking human-verify checkpoint)
- **Commits:** 2
- **Suite:** 1126 passed, 18 skipped, 0 failed

## What passed

| # | Check | Result |
|---|---|---|
| 1 | Printed URL is loopback | `http://127.0.0.1:PORT` — not `0.0.0.0` |
| 2 | Token file | `-rw-------`, contents match the `Token:` line on stdout |
| 3 | Browser navigation to the server | 401 JSON — the guard runs before routing, on a path that does not exist |
| 4 | Discovery from a real browser | **30** capabilities, `input_schema` populated |
| 5 | Capability call with the token | 200, real `workspace.status` body |
| 6 | Same call, token header removed | 401, refused before the capability ran |
| 8 | Token-delivery verdict | Recorded below |

Check 7 — the cross-origin fetch — is the one that did not happen. See the gap below.

## Gap: assumption A3 is still unverified

The cross-origin step was not exercised, and nothing else in the project can substitute for it.
`middleware.py` states the blind spot itself: *a test client sends no `Origin` of its own*. The CSRF
story is that `X-Construct-Token` is **not** CORS-safelisted, so a drive-by page carrying it gets
preflighted, and no `CORSMiddleware` is installed to answer that preflight. **Only a real browser
enforces CORS** — `curl` sends whatever it is told, and the suite drives an application object.

So T-19-02 (drive-by CSRF, severity high) is mitigated *by design* and unproven *as deployed*. This
plan's own instructions warned that "a silent pass here is a gap that reaches Phase 21", so it is
recorded as a gap: one browser console on a foreign origin closes it in about a minute, and Phase 21
should close it before it serves a page from this API. The failure mode to watch for is the one that
looks like a convenience: a `CORSMiddleware` added to the stack would turn this refusal into a
capability list.

## Verdict: token delivery needs redesign

stdout plus a `0600` file is adequate for a human running a walkthrough and inadequate as the basis
for the served shell. Phase 21 must own a real delivery mechanism rather than inheriting a manual
terminal→console transfer. A server-rendered `index.html` carrying the token was deliberately
declined in Phase 19 (it would have pulled Phase 21's static serving forward) — that decision stands
as scoping, not as a verdict that the current mechanism is sufficient.

**Second finding, no test covers it:** the token file path is `{install_root}/.construct/api-token`
and does **not** vary by port. A second `construct serve --port ...` against the same install root
overwrites the on-disk token of the server already running; the first server keeps working from its
in-memory copy, so the mismatch is silent. Phase 21 reads that file, which means it would
authenticate against whichever server launched last regardless of which one it is talking to.

## Defect found by the walkthrough, and fixed

`help.suggest` returned an absolute filesystem path in a **success** body —
`data.workspace = "/Users/.../test-ws/my-construct"`, from `services/help.py`. Against criterion 3
(*no raw exception text or filesystem paths in the body*) that is a violation, and it is the third
instance of the T-18-32 shape that plan 19-03 fixed for `graph.status` and `bridge.detect`.

It survived because the two success-path assertions in `tests/contract/test_result_boundary.py` name
those two capabilities individually. Naming instances is how a third one gets missed, so the remedy
is a sweep: every registered capability taking a workspace-shaped field is invoked against its own
copy of the fixture workspace, and criterion 3 is asserted over each body that comes back
successfully. `NOT_SWEPT` declares the 8 capabilities a contract test must not invoke (LLM, network,
durable workflows, workspace creation) with a reason each, plus an assertion that fails if one of
them leaves the registry. `MINIMUM_BODIES_SWEPT` pins the 12 measured bodies at a floor of 10, so a
sweep that silently stops invoking anything fails instead of passing.

Verified as a guard rather than decoration: restoring `str(root)` fails the sweep, naming
`help.suggest`.

## Commits

1. **The leak and its class** — `049caa2` (fix) — `help.suggest` carries the workspace name; the
   generic success-body sweep and its non-vacuity floor.
2. **This summary and the phase tracking** — (docs).

## Left for `/gsd-validate-phase`

`19-VALIDATION.md`'s two Manual-Only rows are resolved here and its approval is signed. Its
frontmatter (`status: draft`, `nyquist_compliant: false`) and the 16 `TBD` task IDs in the Per-Task
Verification Map are **not** touched: §6 of `/gsd-validate-phase` resolves those ids against the
executed PLAN.md files, and flipping them by hand would report a pass nothing performed.

## Follow-ups

- **Close A3** — one cross-origin fetch from a browser console, before or during Phase 21.
- **Port-independent token file** — decide in Phase 21 whether the file is per-port, per-server, or
  replaced by a delivery mechanism that does not use a file at all.
