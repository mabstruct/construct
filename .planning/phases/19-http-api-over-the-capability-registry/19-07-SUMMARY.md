---
phase: 19-http-api-over-the-capability-registry
plan: 07
subsystem: api
tags: [http, error-shape, cross-surface-parity, http-04, information-disclosure, differential-testing, fastapi]

# Dependency graph
requires:
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-01's HTTP surface and LocalhostGuard, 19-03's serialize_result / sanitize_exception boundary, 19-05's route table and coverage ledger, 19-06's measured trust-boundary controls"
provides:
  - "src/construct/api/errors.py — the one body builder (error_body), the seam-error-to-status map (STATUS_FOR_SEAM_ERROR), and install_error_handlers overriding the two framework-owned emitters"
  - "One error body shape, {\"detail\": <str>}, across all four HTTP emitters: request-validation, unknown-route, pre-dispatch guard, and unexpected exception"
  - "tests/integration/test_surface_parity.py — a third surface column: _http driver, _http_reason projection, and three new ParityCase fields (build_http_root, build_http_payload, read_http)"
  - "Byte-identical refusal reasons across CLI/seam, MCP and HTTP, proven per parity row"
  - "_assert_no_environment_leak — three independent leak assertions run on both successful and failing bodies, on every surface"
affects: [19-09, 19-10, 21-static-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One body builder every emitter passes through, rather than four handlers that happen to agree today"
    - "The HTTP validation handler reuses the seam's own reason builder, so suppressing the echoed input is structural rather than remembered"
    - "Differential harness extended by a column, not replaced: adding a surface stays a row-shaped change"
    - "Leak assertions on the success path, where an exception-boundary sanitizer structurally cannot look"
    - "Mutation-checked arms: the HTTP projection was corrupted to confirm all three rows fail, so the new column is not passing vacuously"

key-files:
  created:
    - src/construct/api/errors.py
  modified:
    - src/construct/capabilities/errors.py
    - src/construct/api/app.py
    - src/construct/api/middleware.py
    - tests/integration/test_surface_parity.py

key-decisions:
  - "D-24 recorded: a capability that ran and reported failure returns HTTP 200 with its result body. The result envelope separates 'the command ran' from 'how it went'; the CLI encodes the second as an exit code (Phase 11's degraded-curation-exits-0 decision). Mapping a reported failure onto 4xx would re-fork that contract on a second surface."
  - "The body is exactly {\"detail\": <str>} — FastAPI's own HTTPException shape — chosen so a body this project did not write (the framework's 404) is already the project's shape rather than a second one discovered later."
  - "A CapabilityError subclass absent from STATUS_FOR_SEAM_ERROR gets 500, never a guessed 4xx: a 4xx asserts the caller's request was wrong, and the map has no basis for saying that about a class it was never told about."
  - "cap_id is folded into the reason rather than carried as a second body key — a key present on some refusals and absent on others is a fork wearing a smaller hat."
  - "T-19-16 rejected explicitly: FastAPI's documented validation handler returns exc.body (the caller's raw request) and exc.errors() (carrying pydantic's echoed input). The handler calls CapabilityInputError.from_validation_error instead, which already suppresses exactly that."
  - "The HTTP parity arm gets its own payload builder rather than reusing build_payload: the HTTP boundary refuses path-shaped keys and addresses workspaces by id, so the other arms' payload is one this surface is required to reject. Same request, this surface's vocabulary."
  - "Undeclared-field reason parity compares HTTP against the fresh-process seam, not the real CLI: Typer rejects an undeclared flag before a payload exists, so the CLI cannot express the request. Comparing against the seam in an independent process strengthens the harness rather than routing around the CLI."
  - "19-06's flagged loose end resolved: app.py's redundant _allowed_origins() is removed, since the guard derives loopback origins from the already-validated Host. Two copies of an allowlist is how an allowlist's silent failure mode gets written."

requirements-completed: [HTTP-04]

coverage:
  - id: D1
    description: "CapabilityInputError.from_validation_error requires its model argument — no default, so a caller cannot silently receive payload-ordered reasons"
    requirement: HTTP-04
    verification:
      - kind: unit
        ref: "tests/integration/test_surface_parity.py#test_from_validation_error_requires_the_model_it_orders_reasons_by"
        status: pass
    human_judgment: false
  - id: D2
    description: "All four HTTP error emitters produce one body shape: request-validation, unknown-route, pre-dispatch guard, unexpected exception"
    requirement: HTTP-04
    verification:
      - kind: integration
        ref: "tests/contract/test_http_security.py — asserts the body key *set*, so a second top-level key is a failing test rather than a silent fork"
        status: pass
      - kind: code
        ref: "src/construct/api/errors.py#install_error_handlers + middleware.py's three refusals rendering through error_body"
        status: pass
    human_judgment: false
  - id: D3
    description: "The HTTP validation handler builds its reason through the seam's own builder, so it never returns the raw request body and never returns pydantic's input field"
    requirement: HTTP-04
    verification:
      - kind: code
        ref: "src/construct/api/errors.py#_handle_request_validation calls CapabilityInputError.from_validation_error"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_undeclared_field_reason_is_byte_identical_on_all_three_surfaces"
        status: pass
    human_judgment: false
  - id: D4
    description: "A known-failing input returns byte-identical reason strings over CLI/seam, MCP and HTTP — the existing differential harness gained a third column rather than a new harness being written"
    requirement: HTTP-04
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_undeclared_field_reason_is_byte_identical_on_all_three_surfaces (3 rows)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_success_parity_across_all_three_real_surfaces (3 rows)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A capability whose result reports failure returns HTTP 200 with the result body — the run-happened flag and the how-it-went outcome stay separate (D-24)"
    requirement: HTTP-04
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_no_surface_leaks_the_environment_on_success_or_on_failure asserts status 200 with success false on the corrupted-fixture arm"
        status: pass
    human_judgment: false
  - id: D6
    description: "No response body — success or error — contains an absolute filesystem path or a traceback marker, asserted on both a successful and a failing request, on every surface"
    requirement: HTTP-04
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_no_surface_leaks_the_environment_on_success_or_on_failure"
        status: pass
      - kind: unit
        ref: "_assert_no_environment_leak verified to fire independently on each of its three classes (fixture root, foreign absolute path, traceback marker)"
        status: pass
    human_judgment: false
  - id: D7
    description: "HTTP-02's prohibition — no third fork in the vocabulary a caller meets — inherited from 19-01 as an open entry"
    requirement: HTTP-02
    verification:
      - kind: code
        ref: "All four emitters now share error_body; reason parity across three surfaces is proven byte-for-byte by D4"
        status: pass
    human_judgment: true
    note: >
      19-01 left this open because the prohibition is a claim about the whole
      surface vocabulary, which could not be asserted before the parity pieces
      existed. The structural half is now complete: the four emitters share one
      builder, and the reasons themselves are proven identical across three
      surfaces. What remains is an *enumeration* claim — that four is really all
      the emitters a caller can reach — which no test in this suite can settle,
      because it is a statement about the framework's behaviour outside the
      routes this project registers. Carried to 19-10 rather than marked closed.

deferred:
  - "RESEARCH A5 (per-request workspace scan cost) remains open — untouched by this plan."
---

# 19-07: One error shape across three surfaces

## What shipped

`src/construct/api/errors.py` is the new single-body boundary. RESEARCH measured that **four** different default error bodies could leave this surface and only one of them was written by the route: a request-validation rejection, the framework's unknown-route 404, a pre-dispatch guard rejection (which `LocalhostGuard` answers *before* the app, so no exception handler can reach it), and an unexpected exception raised while a capability ran. All four now render `{"detail": <str>}` through one builder.

`tests/integration/test_surface_parity.py` gained its third column. `ParityCase` carries `build_http_root` / `build_http_payload` / `read_http`; an `_http` driver posts through a real `TestClient` built from `create_app` — the same factory `construct serve` hands uvicorn — and `_http_reason` strips this surface's framing, which is one key lookup, and the fact that it is *only* a key lookup is itself the HTTP-04 claim.

Suite: 27 tests in the parity module (was 22); full suite **1074 passed, 22 skipped, 0 failed**.

## Three things worth a reviewer's attention

**The HTTP arm could not reuse the other arms' payload, and that is the interesting part.** The boundary refuses path-shaped keys and addresses workspaces by *id*, so the payload CLI and MCP send is one HTTP is required to reject. The row therefore carries a second payload expressing the same request in this surface's vocabulary. That makes the success-parity assertion stronger than it looks: the HTTP arm resolves an id against launch context while the other two resolve a path, so if id resolution and path resolution could ever disagree, this is where it surfaces — as a differing projection, on every row.

**The new column was mutation-checked before being believed.** It passed on first run and the parametrised count did not change, which is exactly when a new arm can be silently inert. Corrupting the HTTP projection was confirmed to fail all three rows. Likewise `_assert_no_environment_leak` was exercised against each of its three leak classes independently — fixture root, a foreign absolute path, and a traceback marker — because a leak assertion that cannot fail is worse than none, it is a green light.

**The leak assertion deliberately runs on the success path.** An exception-boundary sanitizer never sees a success-path value; nothing raised, so `sanitize_exception` cannot help. That is the structural reason the pipeline leaks 19-03 fixed survived as long as they did. The failing arm uses a *reported* failure (200 with `success: false`, D-24) rather than a seam refusal, so both bodies under test are real handler output rather than one being a rejection string. The CLI arm is exempt from the path assertions by construction — the user typed the path, so echoing it discloses nothing they do not have — but is still checked for tracebacks.

## Provenance — how this plan was executed

Task 1 was executed by the assigned executor agent (`86fe245`). Task 2 was executed **inline by the orchestrator**, at the user's direction, after the executor agent failed four consecutive times with `API Error: Connection closed mid-response` — three times at the Task 2 boundary and once immediately after. Each failure was a transport fault, not a work fault: the agent's branch, base and Task 1 commit were verified intact after every one, and no work was lost or redone.

The inline execution followed the plan's Task 2 `<action>` block and was committed in five small units (`7cc9d22`, `8d865ce`, `a94dc0f`, `86366bd`, `1178213`) rather than one, specifically so that a further transport failure would cost one step instead of the task. A reviewer should weigh these commits knowing they were not produced by an independent executor context.

## Deviation

One, and it closes another plan's flagged loose end rather than opening a new one. 19-06 made `LocalhostGuard(allowed_origins=...)` additive, deriving the origin port from the request's already-validated `Host`, which left `app.py::_allowed_origins()` correct but redundant. This plan owns `app.py`, so Task 1 removed it. Two spellings of one allowlist is precisely how an origin allowlist's silent failure mode gets written.

## Known-red baseline, unchanged

`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot` fails in any git worktree because `test-ws/` is gitignored and `digests/`, `publish/`, `.construct/` are empty directories git cannot represent. Materialising those directories locally makes the full suite green, which is the confirmation the diagnosis is right. Untouched here — see `deferred-items.md`.
