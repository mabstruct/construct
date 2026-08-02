---
phase: 19-http-api-over-the-capability-registry
plan: 05
subsystem: api
tags: [fastapi, capability-registry, json-schema, discovery, coverage-guard, non-vacuity, contract-test, http-boundary]

# Dependency graph
requires:
  - phase: 19-http-api-over-the-capability-registry
    plan: 01
    provides: "create_app, the Envelope/single-route shape, PATH_SHAPED_KEYS and the WORKSPACE_FIELD/INSTALL_ROOT_FIELD maps, and tests/contract/conftest.py's app-factory fixture"
  - phase: 18-capability-seam-consolidation
    provides: "extra=\"forbid\" pinned across the whole registry (test_capability_seam.py Layer 1) — the property that makes an undeclared-key probe work for every capability without a hand-written payload table"
provides:
  - "GET /api/capabilities — every registered capability's id, name, description and declared input JSON Schema, iterated from registry.list()"
  - "src/construct/api/COVERAGE.md — the machine-read exposure ledger (capability table, exclusions table, non-capability routes, accepted risks)"
  - "A cardinality-not-membership coverage guard whose exclusions are parsed from the ledger"
  - "Two non-vacuity meta-tests: one over the assertion, one end-to-end with a capability the app cannot resolve"
  - "D-10 path-shaped-key refusal asserted for every registered capability, with the install-root tree unchanged and the seam proven zero-called"
affects: [19-07, 19-08, 19-09, 21-static-ui, 24-verdict-playbook]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Machine-read ledger: a markdown document colocated with the package it constrains, parsed by the guard so an exclusion cannot be added as prose"
    - "Registry-derived probe: a payload that works for every capability because of a separately-guarded property (extra=\"forbid\"), not because someone enumerated fields"
    - "Discriminated reachability: 404 vs a 422 that names the capability, so a guard cannot degrade into 'every id returned some status code'"
    - "Meta-test against the real assertion function, never a re-implementation of it"

key-files:
  created:
    - src/construct/api/COVERAGE.md
  modified:
    - src/construct/api/app.py
    - tests/contract/test_http_surface.py

key-decisions:
  - "D-06 iterates registry.list(), never list_mcp_tools() — the MCP projection omits the six capabilities with no mcp_tool_name, and a membership test over the 23 it does return would pass"
  - "D-18: COVERAGE.md lives at src/construct/api/COVERAGE.md and is parsed by the guard; a planning-only document cannot participate in an assertion"
  - "D-20: GET /api/capabilities and (forward-referenced) POST /api/runs are recorded as non-capability routes, and that table is parsed in the one direction that catches something — a served route the ledger has never heard of"
  - "The reachability probe is an undeclared sentinel key, not an empty payload: the empty-payload rejection depends on 'no model is all-optional' (measured, could change), while the sentinel's rejection depends on extra=\"forbid\" (permanently guarded)"
  - "test_the_route_table_is_one_capability_route now selects dispatch routes by their {cap_id} parameter rather than by path prefix — loosening its count to 2 would have quietly readmitted per-capability routes"
  - "REQUIREMENTS.md deliberately not written by this plan — see 'Deviations'"

patterns-established:
  - "Parse strictly, never skip: the ledger parser asserts on a malformed row rather than ignoring it, because a silently-skipped row is the same defect as an undocumented exclusion"
  - "Vacuity floors as first-class tests: 'the registry is non-empty', 'some capability has no MCP tool name', 'no model is all-optional' — each asserted separately so the comparison above it cannot pass by comparing nothing"
  - "Two-arm meta-testing: the guard is shown to fail on a missing capability AND on a double-counted one, because the second is how the first could hide"

requirements-completed: []

coverage:
  - id: D1
    description: "GET /api/capabilities returns every registered capability's id, name, description and JSON Schema, iterated from registry.list() rather than list_mcp_tools()"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_discovery_endpoint_advertises_every_registered_capability"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_discovery_endpoint_is_not_the_mcp_projection"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_advertised_schema_is_the_capabilitys_own_declared_model"
        status: pass
    human_judgment: false
  - id: D2
    description: "A coverage guard asserts reachable + documented exclusions == registry size, disjoint, and exhaustive"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_every_registered_capability_is_reachable_over_http"
        status: pass
    human_judgment: false
  - id: D3
    description: "The coverage guard is not vacuous — it is demonstrated to fail when a capability is made unreachable"
    requirement: HTTP-02
    verification:
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_coverage_guard_fails_when_a_capability_is_unreachable"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_guard_would_notice_a_capability_the_app_cannot_reach"
        status: pass
    human_judgment: false
  - id: D4
    description: "Reachability is distinguished from a missing route — a validation rejection proves the model ran, a 404 proves it did not, and the discriminator is asserted explicitly"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_an_unregistered_id_is_route_missing_and_a_registered_one_is_not"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_probe_key_discriminates_before_it_is_trusted"
        status: pass
    human_judgment: false
  - id: D5
    description: "COVERAGE.md is machine-read by the guard; it lists every capability today and holds an empty exclusions section"
    requirement: HTTP-02
    verification:
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_ledger_has_one_row_per_registered_capability"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_ledger_records_no_exclusions_today"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_every_non_dispatch_api_route_is_documented_in_the_ledger"
        status: pass
    human_judgment: false
  - id: D6
    description: "Two capability ids sharing a prefix route to different capabilities — the path parameter matches a full id, never a prefix"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_two_ids_sharing_a_prefix_route_to_different_capabilities"
        status: pass
    human_judgment: false
  - id: D7
    description: "An empty payload object reaches the seam and returns the capability's own validation reason rather than a server error; discovery never returns an empty list while the registry is non-empty"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_an_empty_payload_gets_the_capabilitys_own_reason_not_a_server_error"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_no_capability_model_is_all_optional_today"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_discovery_endpoint_never_answers_with_an_empty_list"
        status: pass
    human_judgment: false
  - id: D8
    description: "GET /api/capabilities returns capabilities in registry.list()'s id-sorted order, and two consecutive calls return the same order"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_discovery_order_is_the_registrys_and_is_stable"
        status: pass
    human_judgment: false
  - id: D9
    description: "An HTTP payload carrying any path-shaped key is refused with 422 before dispatch, for every capability, and the workspace is unchanged afterwards"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_no_capability_accepts_a_filesystem_path_over_http"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_path_key_refusal_happens_before_dispatch_for_every_capability"
        status: pass
    human_judgment: false
  - id: D10
    description: "Two capability invocations issued concurrently against one app instance each return their own capability's result"
    requirement: HTTP-02
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_two_concurrent_invocations_each_return_their_own_result"
        status: pass
    human_judgment: true
    rationale: "Authored as a backstop by the plan, and shipped as one. TestClient drives the ASGI app in-process: it exercises the app object's per-request state, not the deployed server's socket handling, event loop under load, or uvicorn's worker model. A green result is evidence about create_app binding install_root and token once; it is not proof about the running server. A human should read it that way at phase verification."

# Metrics
duration: 15 min
completed: 2026-08-03
status: complete
---

# Phase 19 Plan 05: Coverage, Discovery, and a Guard That Would Notice Summary

**Every one of the 29 registered capabilities is now provably reachable over HTTP — asserted by cardinality against a live registry read, with exclusions parsed from a colocated ledger, and the guard itself demonstrated to fail when a capability is made unreachable.**

## Performance

- **Duration:** 15 min
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)
- **Tests:** `tests/contract/test_http_surface.py` 39 → 107

## Accomplishments

- **`GET /api/capabilities` iterates `registry.list()`, and the reason is asserted, not just written down.** `list_mcp_tools()` skips every capability whose `mcp_tool_name` is `None` — six of the twenty-nine. Iterating it would have shipped a 23-capability surface that a set-membership test passes cleanly, because every id it returned would have been correct. `test_the_discovery_endpoint_is_not_the_mcp_projection` names those six from a live registry read and fails if they are absent, and it refuses to pass vacuously: if every capability ever declares an MCP tool name, the test asserts that fact and tells the reader to replace it.
- **The schema-advertising half of GOV-01 is recovered on HTTP.** Phase 18's D-21 had to concede it upstream because the pinned MCP library has no schema-override parameter. Nothing about that was inherent to the contract — it was a property of one library. Each entry now carries the capability's own `input_model.model_json_schema()`, asserted equal rather than spot-checked, because the browser builds a form from it and a *nearly* correct schema produces a form that silently omits a field.
- **The guard asserts cardinality, not membership.** `len(reachable) + len(documented exclusions) == len(registry)`, then disjointness, then the union — in that order, each failure message naming the offending ids. Reachability is *measured* per capability with a registry-derived probe, never a hand-written payload table.
- **Reachability is discriminated from a missing route.** A 404 means the id never resolved; a 422 whose reason *names the capability* means the record resolved and its declared model ran. `does.not.exist` is asserted as the control through the same classifier, so the guard cannot degrade into "every id returned some status code" — and the 422 must name the capability specifically, because a 422 that did not would be the D-10 envelope gate firing ahead of dispatch, which says nothing about reachability.
- **The guard is demonstrated to fail, twice, against the real assertion function.** One meta-test exercises `_assert_full_coverage` directly on a set with a capability removed (cardinality arm) and on one counted twice (disjointness arm — how a missing capability could otherwise hide behind a total that still adds up). A second runs the whole measured pipeline — probe, classify, count — against a registry presented as holding a phantom capability the app cannot resolve, which is the arm that would catch a probe that had quietly stopped discriminating.
- **`src/construct/api/COVERAGE.md` is parsed, not trusted.** 29 capability rows, an exclusions table with a declared shape and zero rows, and a non-capability-routes table. The parser asserts on a malformed row rather than skipping it — a silently skipped row is the same defect as an undocumented exclusion.
- **D-10 is proven for every capability, both ways.** A parametrised case sends each capability's *own* declared path field (derived from the maps, so a rename keeps working) and asserts 422 with the install-root tree byte-identical afterwards; a companion test spies on the seam across the whole registry and asserts it was zero-called, because an unchanged tree shows no write happened and cannot show that no read handler ran.

## Task Commits

1. **Task 1: The discovery endpoint and the machine-read exposure ledger** — `6f5a604` (feat)
2. **Task 2: A coverage guard that would notice — cardinality, non-vacuity, and the path-key refusal** — `7dd2b4a` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `src/construct/api/COVERAGE.md` (new, ~130 lines) — the exposure ledger: a "How to read it" parse contract, the 29-row capability table with each one's addressing mode and declared field, the empty exclusions table, the non-capability-routes table (D-20), and the two accepted risks
- `src/construct/api/app.py` — `DISCOVERY_ROUTE`, the `list_capabilities` endpoint, and the module-docstring paragraph distinguishing "iterate the registry to answer a request" (data) from "loop over the registry to generate routes" (the wiring D-05 forbids)
- `tests/contract/test_http_surface.py` — 68 new tests: the ledger parser and its three ledger assertions, six discovery cases, the coverage guard and its two non-vacuity meta-tests, prefix adjacency, empty-payload (parametrised over the registry), ordering, concurrency, and the D-10 refusal parametrised over all 29 capabilities

## Decisions Made

Beyond the plan's named D-18 / D-20:

- **The probe is an undeclared sentinel key, not an empty payload.** `{"payload": {}}` would in fact reject for all 29 capabilities today — no registered model is all-optional. But that is a *measured* property that a future capability could change, and when it did, the probe would silently start **running handlers** instead of testing reachability. The sentinel's rejection rests on `extra="forbid"`, which `test_capability_seam.py` pins for the whole registry permanently. The measured property is still used, for the empty-payload case the plan asks for — with `test_no_capability_model_is_all_optional_today` asserted beside it as the tripwire, and the parametrisation derived from the same predicate so the case can never quietly execute a workflow.
- **The probe's two preconditions are asserted before the probe is trusted** (`test_the_probe_key_discriminates_before_it_is_trusted`): the key is declared by no capability, and it is not in `PATH_SHAPED_KEYS`. Either being false would turn the refusal into a *different* refusal and collapse the discriminator — the D-10 gate would answer 422 to every id, registered or not.
- **`test_the_route_table_is_one_capability_route` selects on `{cap_id}`, not on the `/api/capabilities` prefix.** Adding the discovery route broke it under the old prefix selector. The obvious repair — loosening the count from 1 to 2 — would have made the guard tolerate a second capability-shaped route, which is how per-capability routes get readmitted one at a time. Selecting dispatch routes by their path parameter keeps the count at exactly 1, and a new assertion was added beside it: no route path may contain a registered capability id literally, which is the property a route generator would break and the count alone cannot see.
- **The non-capability-routes table is parsed too, as a subset in one direction.** Every non-dispatch `/api` route the app serves must appear in the ledger; the reverse is not required, because a row may legitimately be written *before* the plan that adds the route — which is how `POST /api/runs` is listed today for plan 19-09. The direction that catches something is a served route nobody documented.
- **The ledger records the `views.*` scope mismatch rather than smoothing it.** Both views capabilities are install-root scoped, so an id-addressed call resolves to a single workspace and scans its children, while sending `install_root` directly is refused by D-10. They are therefore genuinely *reachable* (the model validates, the handler runs) and not yet *usefully* addressable. Reachability is what the guard asserts; usefulness is HTTP-03's completion, which plan 19-04 owns. A ledger that only recorded good news would not be worth parsing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1's acceptance criteria required test edits, which the plan scoped to Task 2**

- **Found during:** Task 1
- **Issue:** Two things. (a) Adding `GET /api/capabilities` immediately broke `test_the_route_table_is_one_capability_route`, whose selector was the `/api/capabilities` path *prefix* — so Task 1 could not leave the suite green without touching the test file. (b) Task 1's acceptance criteria are assertions about HTTP responses and about the ledger's structure; a task whose criteria are verified by nothing is not done.
- **Fix:** Task 1's commit carries the route-table repair (see Decisions Made) and the tests that verify Task 1's own criteria — the six discovery cases and the three ledger cases, plus the parser they share. Task 2's commit carries what the plan scoped to it: the coverage guard, both non-vacuity meta-tests, prefix adjacency, empty payload, concurrency and the parametrised D-10 refusal. No test the plan asked for was dropped or moved out of the plan.
- **Files modified:** `tests/contract/test_http_surface.py`
- **Verification:** `.venv/bin/python -m pytest tests/contract/test_http_surface.py -q` → 39 passed at Task 1, 107 at Task 2
- **Committed in:** `6f5a604`

**2. [Rule 3 - Blocking] Recreated the `.venv` symlink for this worktree**

- **Issue:** The plan's `<verify>` blocks all invoke `.venv/bin/python`, and a fresh git worktree has no `.venv` — the environment lives at the main checkout root. Same mechanic plan 19-01 hit.
- **Fix:** `ln -s ../../../.venv .venv`. The repository's own `.gitignore` documents this exact pattern in a comment and ignores both the directory and symlink forms.
- **Files modified:** none tracked — the symlink is gitignored and disappears with the worktree.
- **Committed in:** n/a (untracked by design)

**3. [Rule 4 - Deferred to the orchestrator] `REQUIREMENTS.md` deliberately not written**

The plan's frontmatter names `requirements: [HTTP-02, HTTP-03]`, and the executor contract offers to check them off. Not done here, for two reasons, both of which make writing the file the wrong call rather than a skipped step:

- **It would be a false claim.** HTTP-03's completion is owned by plan 19-04 (the A2 parametrisation and the `INSTALL_ROOT_FIELD` scope mismatch handed over by 19-01), and 19-04 is executing concurrently in this wave. HTTP-02's own prohibition is discussed below: this plan resolves the part it was written for, and the whole-surface parity claim still belongs to phase verification.
- **It would be a merge conflict.** 19-04 declares the same requirement and is editing the same file in the same wave.

`requirements-completed` in this summary's frontmatter is therefore empty, and the coverage table above carries the per-criterion mapping instead. The orchestrator has both plans' summaries and can mark the requirements once, after the wave.

### Test-design choices that differ from the plan's literal wording

Recorded because they are visible in the diff, not because they change scope:

- The plan says the non-vacuity meta-test should remove "one live capability id from the measured set". That is implemented, and a **second arm** was added — a capability counted as both reachable and excluded. Without it, the disjointness assertion would itself be untested, and disjointness is precisely how an unreachable capability could hide behind a total that adds up. A **third** test makes the same claim end to end, through the real probe, which the pure-assertion arms cannot cover.
- The plan asks the D-10 refusal case to assert "422 plus an unchanged install-root tree". Both are asserted, and a companion test adds the claim the tree cannot make: that the **seam was never entered**. An unchanged tree proves no write happened; a read handler that ran on a caller-supplied path would already be an information disclosure and would leave the tree untouched.
- The prefix-collision case is parametrised over two pairs rather than the one the plan names, and asserts in **both directions** for each pair (the reason string names the requested capability and not its neighbour). One direction would not distinguish "resolves correctly" from "always resolves to the first match".

---

**Total deviations:** 2 auto-fixed (both blocking mechanics), 1 deliberate deferral to the orchestrator
**Impact on plan:** No scope creep. Every plan acceptance criterion is met as written; three cases are stronger than their literal wording and none is weaker.

## Issues Encountered

**Two pre-existing test failures, out of scope, not fixed — the documented worktree baseline.**
`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::{test_my_construct_has_canonical_layout, test_ping_eon_has_canonical_layout}` fail with `Missing canonical directory in .../test-ws/<ws>: digests/`. `test-ws/` is gitignored and `digests/`, `publish/` and `.construct/` exist only as empty directories git cannot represent, so they never materialise in a worktree. They pass in the main checkout, reproduce on this plan's base commit, and are recorded in this phase's `deferred-items.md`. This plan touches no fixture and no `test-ws` path.

Everything else is green: **933 passed, 22 skipped** on the full suite.

## Known Stubs

None. No `TODO`, `FIXME`, placeholder value, skipped test or unrun `<verify>` was introduced by this plan.

The exclusions table in `COVERAGE.md` holding zero rows is **not** a stub — it is the finding (every capability is reachable) and its emptiness is asserted by a test. The `views.*` scope mismatch recorded in the ledger is a forward reference to plan 19-04, which owns it; both capabilities are reachable today, which is the property this plan is responsible for.

## Flagged Assumptions Carried Forward

- **HTTP-03 / unclassified — "review manually".** The spec-less probe fallback's one unresolved row, carried forward per the plan. Plan 19-04 owns HTTP-03's completion and repeats the flag.
- **The HTTP-02 concurrency edge is a backstop, by design.** `test_two_concurrent_invocations_each_return_their_own_result` passes, and what that means is bounded: `TestClient` runs the ASGI app in-process. It is evidence that `create_app` binds `install_root` and `token` once and mutates neither per request; it is not evidence about the deployed server's socket handling or uvicorn's worker model. Marked `human_judgment: true` in the coverage block for exactly this reason.
- **HTTP-02's prohibition (`status: unresolved` in the plan) is resolved for the part this plan was written for.** "No set-membership coverage assertion" — the guard counts, and asserts disjointness and union. "No undocumented exclusion" — exclusions are parsed from the ledger, and the table is empty. "No guard that still passes when a capability is made unreachable" — demonstrated to fail, three ways. What remains outside this plan is the *whole-surface vocabulary* half of HTTP-02 that 19-01 also flagged, which is a phase-verification judgment across all ten plans and not something one plan should close.

## Threat Flags

None. No security-relevant surface outside the plan's `<threat_model>` was introduced. The discovery endpoint is a new route and it is inside the register (T-19-20, disposition `accept`) and behind the same `LocalhostGuard` — asserted by `test_the_discovery_endpoint_is_behind_the_same_trust_boundary`, added because a `GET` that published the shape of every write capability without a token would hand an unauthenticated reader a map of the surface.

| Threat | Disposition | Shipped | Proven by |
|---|---|---|---|
| T-19-03 path-shaped payload keys | mitigate | 422 before dispatch, per capability, tree unchanged | `test_no_capability_accepts_a_filesystem_path_over_http`, `test_the_path_key_refusal_happens_before_dispatch_for_every_capability` |
| T-19-17 client-supplied `install_root` | mitigate | `install_root` is a `PATH_SHAPED_KEYS` entry, so it is covered by the parametrisation above for both views capabilities | same two tests |
| T-19-19 a capability silently unreachable | mitigate | cardinality guard + two non-vacuity meta-tests, exclusions parsed from the ledger | `test_every_registered_capability_is_reachable_over_http`, `test_the_coverage_guard_fails_when_a_capability_is_unreachable`, `test_the_guard_would_notice_a_capability_the_app_cannot_reach` |
| T-19-10 unbounded run spawning | accept | recorded explicitly in `COVERAGE.md` under "Out of scope by construction", with the condition that expires the acceptance | ledger prose (accepted risk, not a mitigation) |
| T-19-20 advertised JSON Schemas | accept | schemas describe the local tool's own inputs and carry no secrets; the endpoint is still token-gated | `test_the_discovery_endpoint_is_behind_the_same_trust_boundary` |

## User Setup Required

None.

## Next Phase Readiness

- **For 19-07 (the error boundary):** the guard's classifier reads `response.status_code` and asks whether the reason **names the capability**. That is a behavioural contract on the error body, not a wording match — 19-07's shared `api/errors.py` body must keep the capability id in the reason for a seam error, and must keep the D-10 envelope refusal *not* naming one. Both properties are what distinguish "the model ran" from "refused before dispatch".
- **For 19-08 (adds the `workflow.list` capability):** the ledger's capability table needs a row, and `REGISTRY_SIZE` moves 29 → 30. That is the intended tripwire, not an obstacle: the coverage guard fails until the row exists, which is the whole design.
- **For 19-09 (adds `POST /api/runs`):** the ledger already carries its row under non-capability routes, so the route-documentation assertion passes on arrival. If the route lands under a different path, that row is what needs updating.
- **For Phase 21 (static UI):** `GET /api/capabilities` is the form-building contract, id-sorted and stable across polls. Note the accepted consequence: the schema is now a *consumed* contract, so changing an input model is a visible break rather than a quiet one.

## Self-Check: PASSED

- `src/construct/api/COVERAGE.md` exists on disk; `src/construct/api/app.py` and `tests/contract/test_http_surface.py` exist and are modified.
- Both task commits present in `git log`: `6f5a604`, `7dd2b4a`. Neither commit deletes a tracked file.
- Plan `<verification>` re-run at close-out: `tests/contract` → 387 passed / 22 skipped at Task 1, and the full suite → **933 passed, 22 skipped** with only the two documented `test-ws` worktree-baseline failures.
- Working tree clean apart from this SUMMARY at the time of writing.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-03*
