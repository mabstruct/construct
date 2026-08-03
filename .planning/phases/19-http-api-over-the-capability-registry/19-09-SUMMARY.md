---
phase: 19-http-api-over-the-capability-registry
plan: 09
subsystem: api
tags: [fastapi, subprocess, langgraph, checkpoints, workflow-runs, http, cli-parity]

requires:
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-07's single error body (error_body / STATUS_FOR_SEAM_ERROR / install_error_handlers)"
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-05's create_app, LocalhostGuard and the COVERAGE.md ledger the guard parses"
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-04's workspace-id addressing (resolve_workspace_id, PATH_SHAPED_KEYS, launch_install_root)"
  - phase: 19-http-api-over-the-capability-registry
    provides: "19-02's checkpoint concurrency contract (WAL + explicit busy timeout, ETag arbitration)"
provides:
  - "POST /api/runs — the one non-capability route: starts a workflow run in a detached subprocess and answers with the minted run id before the workflow begins"
  - "src/construct/api/runs.py — runs_router, start_run, RUN_LOG_RELPATH, RUNS_ROUTE, startable_workflows()"
  - "A registry-derived startable-workflow set: any capability whose id ends in .run becomes startable with no edit to the spawner"
  - "Captured run output at {workspace}/.construct/workflow/logs/<run_id>.err, whose relative path the start response advertises before the child writes a byte"
  - "--run-id on 'curation run', 'research run' and 'daily run' — the caller-minted handle the detached start depends on"
  - "Proof, against persisted cards, that a run started on either surface is resumable from the other"
affects: [phase-20, phase-21, guided-ui, run-progress, workflow-resume]

tech-stack:
  added: []
  patterns:
    - "Non-capability route by exception, not by convenience: a route exists only where the capability envelope is structurally unable to express the operation, and COVERAGE.md's parsed table is what keeps that list from growing quietly"
    - "Detached-subprocess run lifecycle: the checkpoint is the run's state, the server holds none, and a restart loses nothing"
    - "Advertise-then-fail: the failure path's artifact (the log) is named in the success response, so a failure that produces no response is still locatable"
    - "Derive the child's code from the parent's: PYTHONPATH is pinned to the running process's own package root so a server and its children can never be two different checkouts"

key-files:
  created:
    - src/construct/api/runs.py
    - tests/integration/test_http_runs.py
  modified:
    - src/construct/api/app.py
    - src/construct/api/COVERAGE.md
    - src/construct/cli.py
    - tests/contract/test_http_surface.py

key-decisions:
  - "D-12 realised: a run is a detached subprocess and only *starting* is a non-capability route; polling and resume stay on the ordinary capability envelope"
  - "D-26 widened on measurement: BOTH child streams are captured, not stderr alone, because construct.cli reports a failed capability with typer.echo on stdout — a stderr-only capture would have discarded exactly the sentence a failed run needs to leave behind"
  - "The run id is minted by the generator belonging to the workflow's own module, reached through the capability's declared input_model — registry-derived rather than a lookup table, and it avoids stamping 'cur-' on a research run"
  - "The child's PYTHONPATH is pinned to the parent's package root: sys.executable alone would let an editable install resolve construct to a different checkout than the one the server is running from"
  - "The start response carries pid and a null checkpoint_id: the pid is the only thing distinguishing 'has not written a checkpoint yet' from 'died before it could', and declaring the ETag key now means Phase 21 does not change the shape"
  - "HTTP resumes in the test suite submit an explicit per-proposal decisions map, never approve_all, so HTTP-06's prohibition is discharged by construction rather than assumed"

patterns-established:
  - "Registry-derived startable set: {id[:-4]: id for capability ids ending in .run}, recomputed per request the way D-02 rescans the install root"
  - "Refuse-with-the-neighbour's-reason: a mode='before' model validator fires ahead of extra='forbid' so a path-shaped key gets the envelope's actionable message instead of pydantic's generic one"
  - "Resume proofs assert on canonical files: a resume LangGraph swallowed as an empty interrupt map returns a well-formed success, so only reading the cards back off disk can catch it"

requirements-completed: [HTTP-06]

coverage:
  - id: D1
    description: "Starting a workflow run over HTTP returns a run id immediately, before the run finishes"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_starting_a_run_answers_with_an_id_before_the_workflow_begins"
        status: pass
    human_judgment: false
  - id: D2
    description: "A run that is still executing is pollable through the ordinary capability envelope, with no new read path"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_a_started_run_is_pollable_through_the_ordinary_envelope"
        status: pass
    human_judgment: false
  - id: D3
    description: "A run started in the browser is resumable from the CLI, and a run started from the CLI is resumable in the browser"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_started_in_the_browser_and_resumed_from_the_cli"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_started_from_the_cli_and_resumed_in_the_browser"
        status: pass
    human_judgment: false
  - id: D4
    description: "A resume goes through the review capabilities; no default, blanket approval or missing decision produces a canonical write"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_a_resume_with_no_decisions_writes_nothing"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_a_stale_checkpoint_handle_is_refused_and_writes_nothing"
        status: pass
    human_judgment: false
  - id: D5
    description: "A spawn that fails writes its output to a file under the workspace and the start response names that file"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_a_child_that_dies_at_startup_leaves_a_readable_trace"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_an_invalid_workspace_makes_the_run_fail_in_the_log"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_the_response_names_the_log_rather_than_echoing_it"
        status: pass
    human_judgment: false
  - id: D6
    description: "The spawner passes an argument list, never invokes a shell, and validates the run id before it reaches the argument vector"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_the_spawn_passes_an_argument_list_and_never_a_shell"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_a_traversal_shaped_workspace_id_is_refused"
        status: pass
    human_judgment: false
  - id: D7
    description: "Every run response carries the checkpoint handle a later phase needs for optimistic concurrency"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_the_start_response_carries_the_checkpoint_handle_field"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_the_poll_response_carries_the_checkpoint_handle"
        status: pass
    human_judgment: false
  - id: D8
    description: "The startable workflows are derived from the registry, so a future run capability becomes startable with no edit to the spawner"
    requirement: HTTP-06
    verification:
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_the_startable_workflows_are_derived_from_the_registry"
        status: pass
      - kind: integration
        ref: "tests/integration/test_http_runs.py#test_an_unknown_workflow_is_refused_and_names_the_startable_set"
        status: pass
    human_judgment: false
  - id: D9
    description: "The run-start route sits behind the same guard and the same error body as the envelope, and is recorded in the parsed COVERAGE.md ledger"
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_every_non_dispatch_api_route_is_documented_in_the_ledger"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_ledger_guard_can_see_a_route_added_through_include_router"
        status: pass
    human_judgment: false
  - id: D10
    description: "A real browser, against a real bound socket, can start a run and watch it progress"
    verification: []
    human_judgment: true
    rationale: "This suite drives the ASGI app object through TestClient and never binds a port. Host/Origin handling under a real uvicorn lifecycle, and a browser's actual fetch, are outside what any assertion here can observe — plan 19-10's manual verification covers them."

duration: 71min
completed: 2026-08-03
status: complete
---

# Phase 19 Plan 09: Run Addressability Summary

**`POST /api/runs` starts a workflow in a detached subprocess and answers with the run id in ~20ms, with polling and resume left on the ordinary capability envelope — cross-surface resume proven in both directions against the cards on disk, and a start that dies captured to a file the response named before the child wrote a byte.**

## Performance

- **Duration:** ~71 min
- **Tasks:** 2 (committed across 7 atomic commits)
- **Files created:** 2
- **Files modified:** 4
- **Suite:** 1120 passed, 22 skipped, 0 failed

## Accomplishments

- **A run outlives the process that started it.** The route mints the id, hands it to a detached child through the CLI, and returns. Measured: 20ms to respond against a run that takes ~1.2s to reach its review gate. The non-blocking claim is asserted twice over without timing — the child is still alive *and* the run has no checkpoint at all when the response is read, which is the state a synchronous implementation could never return in.
- **Cross-surface resume, proven on canonical state.** A browser-started run is resumed by a real `construct curation review` child process, and a CLI-started run is resumed over HTTP through `curation.review`. Both assert the card lifecycles read back off disk changed from `seed` to `archived` — because a resume LangGraph silently consumed as an empty interrupt map returns a well-formed success and writes nothing, which is exactly the defect a response-shape assertion would pass over.
- **A failed start is legible.** Both child streams land at `{workspace}/.construct/workflow/logs/<run_id>.err`, and the start response names that relative path *before* the child has run. The suite proves the sharp case: a child that dies at startup leaves `curation.inspect` reporting "No such curation run" forever, and the log is the only thing distinguishing that from a run nobody started.
- **A deterministic, fully offline paused-run fixture.** `decay_scan` becomes an archive *producer* under `auto_archive_on_decay` — no model, no network — so a curation run pauses at its review gate in a real child process. The idiom used elsewhere in the repo (monkeypatching `build_chat_model`) is structurally unavailable here, because the run happens in another process.
- **The exposure ledger can now see the routes it is supposed to police.** Starlette wraps `include_router` in one opaque pathless entry; the D-20 guard was passing while being unable to observe the route this plan added.

## Task Commits

1. **Task 1 (prerequisite): expose the declared `run_id` on the run-start CLI commands** — `2d391ef` (feat)
2. **Task 1: the run-start route, the detached spawn, the captured output** — `b336fc3` (feat)
3. **Task 2: suite scaffold — offline paused fixture and surface drivers** — `781cd67` (test)
4. **Task 2: non-blocking start, envelope polling, checkpoint handle, refusals** — `0583684` (test)
5. **Task 2: cross-surface resume, both directions, on persisted cards** — `5c7109e` (test)
6. **Task 2: a failed start is visible at the advertised path** — `fdded7f` (test)
7. **Deviation: make the ledger guard see `include_router` routes** — `53394d5` (fix)

## Files Created/Modified

- `src/construct/api/runs.py` — **created.** `runs_router`, `start_run`, `RUN_LOG_RELPATH`, `RUNS_ROUTE`, `startable_workflows()`, the request/response models, the run-id minting and the child-environment pin.
- `tests/integration/test_http_runs.py` — **created.** 18 cases: non-blocking start, envelope polling, both resume directions, the two HTTP-06 write prohibitions, three failed-spawn cases, the registry-derived startable set, and the refusals.
- `src/construct/api/app.py` — includes `runs_router` after the guard and after `install_error_handlers`; `create_app`'s docstring records D-12 and why this is the only non-capability route.
- `src/construct/api/COVERAGE.md` — the `POST /api/runs` row now carries its real reason, plus a paragraph recording what the route deliberately does *not* do (drive the graph).
- `src/construct/cli.py` — `--run-id` on `curation run`, `research run` and `daily run`.
- `tests/contract/test_http_surface.py` — `_flatten_routes`, a non-vacuity assertion on the ledger guard, and a test naming the route that exposed the gap.

## Decisions Made

- **D-26 widened after measurement: capture both child streams, not stderr alone.** The tidier design — a file holding nothing but errors — was tried and rejected on evidence: `construct.cli` reports a failed capability with `typer.echo(f"ERROR {exc}")`, which is **stdout**. A stderr-only capture would have preserved the logging warnings a *healthy* run emits while discarding the one sentence a failed run needs to leave behind. The accepted cost is that "the log is non-empty" is no longer a verdict — a degraded-but-fine run writes there too — so a test pins that limit explicitly rather than leaving a later reader to discover it.
- **The run id is minted per workflow, through the registry.** `curation.run` declares `CurationRunInput`, which is defined in `construct.llm.curation_run` (deliberately, to avoid a circular import through `catalog.py`), and that module owns `_new_run_id`. So the generator is reached via `capability.input_model.__module__` — registry data, not a maintained table. Using one workflow's generator for all three would have stamped `cur-` on every research run.
- **The child is pinned to the parent's own code.** `sys.executable` is right, but `-m construct.cli` then imports whatever `construct` that interpreter's environment resolves — for an editable install, the checkout the install points at, which need not be the checkout the server is running from. This was not theoretical: in this worktree the venv's editable install resolves to the *main* checkout, so an unpinned child would have run code this plan never touched, including a CLI without `--run-id`.
- **`pid` on the start response.** It is the only thing that distinguishes "the run has not written a checkpoint yet" from "the run died before it could" during the first second of a run's life — the exact window D-26 exists to make legible — and it is what lets the non-blocking claim be asserted rather than timed.
- **HTTP resumes use an explicit per-proposal `decisions` map.** `approve_all` expands to the same map inside the capability, but it is the *shape* HTTP-06's prohibition names, and a review UI built by reading these tests should be built on the explicit form.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `--run-id` to the three run-start CLI commands**

- **Found during:** Task 1
- **Issue:** The plan's mechanism requires minting the run id *before* the child starts, and states that "both run inputs already accept one". The input models do (`CurationRunInput`, `ResearchRunInput`, `DailyRunInput` each declare a kebab-validated `run_id`), but the CLI commands the spawner invokes did not expose it. Without the flag the id can only exist once the run has finished, which is the blocking call D-12 rules out.
- **Fix:** An optional `--run-id` on `curation run`, `research run` and `daily run`, sharing one `_RUN_ID_HELP` constant declared above all three (a Typer option default is evaluated when the `def` executes, so a constant declared later would be a `NameError` on every CLI startup). The payload omits the key entirely when the flag is absent, so a caller that does not use it submits the exact payload it submitted before.
- **Files modified:** `src/construct/cli.py`
- **Verification:** `--help` exits 0 for all three; the full suite is green, including `tests/contract/test_doc_command_references.py`.
- **Committed in:** `2d391ef`

**2. [Rule 2 - Missing Critical] The exposure-ledger guard could not see `include_router` routes**

- **Found during:** Task 1 (wiring `runs_router` into `create_app`)
- **Issue:** `tests/contract/test_http_surface.py::test_every_non_dispatch_api_route_is_documented_in_the_ledger` exists so no `/api` route can be served without a row in `COVERAGE.md`. Starlette wraps an `include_router(...)` call in a single opaque `_IncludedRouter` entry whose own `path` is `""` and which exposes its children only through `original_router` — so the guard walked past `POST /api/runs` entirely. It passed, vacuously, for exactly the class of route this plan introduced. Left alone, D-20's "no undocumented surface" claim would have been false for every future router-mounted route.
- **Fix:** A `_flatten_routes` walk that descends through `original_router`, an assertion that the walk found *something* (the guard's failure mode is silence, and a subset assertion cannot distinguish "nothing undocumented" from "nothing seen"), and a test naming `RUNS_ROUTE` explicitly.
- **Files modified:** `tests/contract/test_http_surface.py`
- **Verification:** `tests/contract` green (108 in that module); the new test fails if the walk cannot reach the run route.
- **Committed in:** `53394d5`

**3. [Rule 2 - Missing Critical] The run response carries `pid`, and finished children are reaped**

- **Found during:** Task 1
- **Issue:** Task 2's behaviour block requires proving the response returns "while the spawned process is still alive", which nothing in the planned response shape made observable. Separately, a long-lived server that never waits on its children accumulates zombie process-table entries — the same envelope as T-19-10's accepted unbounded spawning, but avoidable for the cost of a list.
- **Fix:** `pid` on `RunStarted`, plus a module-level `_SPAWNED` list pruned on each start. Documented as *not* run state: it is empty after a restart while every run it started stays addressable, which is the property D-12 was chosen for.
- **Files modified:** `src/construct/api/runs.py`
- **Verification:** `test_starting_a_run_answers_with_an_id_before_the_workflow_begins` asserts liveness through it.
- **Committed in:** `b336fc3`

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 missing critical)
**Impact on plan:** All three were required to make the plan's own claims true or checkable. No scope creep — the CLI change exposes a field the models already declared and guarded, and the guard fix restores a property 19-05 intended.

## Issues Encountered

- **The fixture workspace's curation run does not pause offline.** `promotion_review` degrades to "provider outage — no promotion proposals enqueued", leaving an empty gate queue and a `completed` run, so there is nothing to resume. The repo's existing paused-run fixture monkeypatches `build_chat_model` — structurally unavailable here, because the run must happen in a *child process*. Resolved by finding the LLM-free producer: `decay_scan` enqueues one archive proposal per decay candidate under `auto_archive_on_decay`, so setting that flag with `decay_window_days: 0` and backdating the cards produces a real, fully offline pause in a real child.
- **"Pollable while the process is alive" is not assertable without flakiness.** The window in which the child is simultaneously running *and* has written a checkpoint is a few tens of milliseconds on this workflow. Rather than write a timing-dependent assertion, the suite asserts what is deterministic and says the same thing — the response arrives before the run has started, every poll issued while the child is alive is answered with a well-formed 200 rather than an error, and the run is still unfinished (`awaiting_review`) when polling reaches it. Recorded in the test module's docstring as a named blind spot.
- **Two pre-existing worktree-only failures** in `tests/integration/test_workspace_contract_migration.py::TestFixtureRoot` (git cannot represent the empty `digests/`, `publish/`, `.construct/` directories under gitignored `test-ws/`). Confirmed as the documented known-red baseline, not a regression: creating the directories locally gives a fully green run — 1120 passed, 22 skipped, 0 failed.

## Known Stubs

None. Every symbol this plan introduced is wired and exercised; no placeholder values, no unimplemented branches.

## Threat Flags

None. The route introduces one new trust boundary — an HTTP body reaching a process argument vector — and it is the boundary the plan's threat register already covers (T-19-09, T-19-25, T-19-03, T-19-05, T-19-26). No new network endpoint, auth path or schema was added beyond `POST /api/runs`, which sits behind the same `LocalhostGuard` as every dispatch.

## User Setup Required

None.

## Next Phase Readiness

- **Ready:** a browser can start a run, poll it, and resume it, with the ETag key already present on every run response so Phase 21's optimistic concurrency needs no shape change.
- **Open, and owned elsewhere:** plan 19-10's manual verification is what covers a real bound socket — this suite never binds a port (D10 above).
- **Carried forward:** RESEARCH assumption A4 (the detached spawn: working directory, interpreter resolution, environment inheritance) is now *exercised* rather than assumed. The one thing it surfaced — that an editable install can resolve `construct` to a different checkout than the server is running from — is fixed here, but it is worth re-checking on a machine where CONSTRUCT is installed non-editably.
- **A note for the guided layer:** the log file answers "what did this run say", never "did it succeed". Status comes from the inspect capabilities. A UI that colours a run red because its log is non-empty would misreport every healthy run — `test_a_healthy_runs_log_exists_too_so_non_empty_is_not_a_verdict` exists to make that concrete.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-03*
