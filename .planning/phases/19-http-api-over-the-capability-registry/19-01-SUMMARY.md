---
phase: 19-http-api-over-the-capability-registry
plan: 01
subsystem: api
tags: [fastapi, uvicorn, asgi, starlette, http, localhost, dns-rebinding, capability-registry, typer, pytest]

# Dependency graph
requires:
  - phase: 18-capability-seam-consolidation
    provides: "CapabilityRegistry.invoke as the single validating seam (GOV-01), the typed CapabilityInputError/CapabilityNotFoundError pair, and the surface-parity harness that pins invoke's signature"
  - phase: 15-views-data-contracts
    provides: "discover_workspaces / _is_workspace — the install-root scan reused verbatim as the workspace-id allowlist"
provides:
  - "A runnable loopback HTTP surface: `construct serve` + POST /api/capabilities/{cap_id}"
  - "workspace_id resolution inside the seam (D-01), so id addressing belongs to CLI, MCP and HTTP alike"
  - "LocalhostGuard — the Host / Origin / token trust boundary (HTTP-05)"
  - "The measured cap_id -> path-field map (WORKSPACE_FIELD / INSTALL_ROOT_FIELD) and PATH_SHAPED_KEYS derived from it"
  - "Launch context accessors set_launch_install_root / launch_install_root (D-09)"
  - "tests/contract/conftest.py — the shared app-factory + TestClient fixture every later Phase 19 plan drives"
  - "The per-launch token contract: stdout plus {install_root}/.construct/api-token at 0600 (D-17)"
affects: [19-02, 19-03, 19-04, 19-05, 19-06, 19-07, 19-08, 19-09, 19-10, 21-static-ui, 24-verdict-playbook]

# Tech tracking
tech-stack:
  added: ["fastapi>=0.141,<1 (0.141.1 — zero new transitive deps)", "uvicorn>=0.51 (already present transitively; now declared because serve imports it directly)"]
  patterns:
    - "Single-route envelope: one POST with the capability id as a path parameter, so no route generator and no loop over the registry"
    - "Two-gate id resolution with the shape gate strictly before the filesystem gate"
    - "ASGI middleware as the trust boundary, with the Host check folded in rather than delegated to TrustedHostMiddleware"
    - "Pre-flight socket probe so a CLI server command owns its own exit code"

key-files:
  created:
    - src/construct/api/__init__.py
    - src/construct/api/app.py
    - src/construct/api/middleware.py
    - src/construct/capabilities/workspaces.py
    - tests/contract/conftest.py
    - tests/contract/test_http_surface.py
    - .planning/phases/19-http-api-over-the-capability-registry/deferred-items.md
  modified:
    - pyproject.toml
    - src/construct/capabilities/registry.py
    - src/construct/cli.py
    - CONSTRUCT-CLAUDE-spec/artifact-catalog.md

key-decisions:
  - "D-09: the install root is process-level launch context (set_launch_install_root / launch_install_root), never an invoke() argument — test_seam_has_no_leniency_knob pins invoke to {self, cap_id, payload}"
  - "D-10: the HTTP envelope refuses path-shaped payload keys server-side with 422 before dispatch; PATH_SHAPED_KEYS is derived from the field maps so it cannot drift from them"
  - "D-17: token delivery is stdout plus a 0600 file at {install_root}/.construct/api-token; never a URL query string, and static serving is not pulled forward from Phase 21"
  - "DEFAULT_API_PORT = 8787 — fixed and bookmarkable (D-04), outside the well-known and macOS ephemeral ranges and not a default of Vite/Streamlit/`npx serve`"
  - "discover_workspaces is imported lazily inside resolve_workspace_id: it keeps the views contract-model package off every CLI startup, and it is what makes the gate-ordering proof patchable at the source module"
  - "The middleware's refusal body is {\"detail\": ...} — the same shape FastAPI's own HTTPException handler emits, so the 'one error shape' claim behind declining TrustedHostMiddleware is actually true"
  - "The token is compared as bytes: secrets.compare_digest raises TypeError on a non-ASCII str, and header values arrive latin-1 decoded, so a str comparison would let a caller turn the 401 into a 500"

patterns-established:
  - "Field-map indirection: a caller-facing vocabulary (workspace_id) mapped onto each capability's own declared field name, rather than renaming 27 declared contracts"
  - "Derived-not-listed constant: PATH_SHAPED_KEYS is computed from the maps, and a test asserts the derivation so a hand-list can never be reintroduced"
  - "Ordering asserted by spying, not by reading source: the shape gate is proven to precede the allowlist gate by patching discover_workspaces and asserting zero calls"
  - "Blocking-call stubbing for CLI server commands: uvicorn.run is monkeypatched so everything serve does before it is deterministically observable, while the exit-code claim still uses a real child process"

requirements-completed: [HTTP-01, HTTP-02, HTTP-03, HTTP-05]

coverage:
  - id: D1
    description: "`construct serve` starts a server bound to 127.0.0.1 and prints both the URL and a per-launch token"
    requirement: HTTP-01
    verification:
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_bind_address_is_the_loopback_constant"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_launch_token_reaches_a_0600_file_and_stdout"
        status: pass
      - kind: other
        ref: ".venv/bin/python -m construct.cli serve --help"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/capabilities/workspace.status with {\"workspace_id\": \"<name>\"} and a valid X-Construct-Token returns the same body the CLI and MCP surfaces return for that workspace"
    requirement: HTTP-01
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_browser_shaped_request_reaches_a_real_capability_by_workspace_id"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_the_shared_operation_result_envelope_survives_the_http_boundary"
        status: pass
    human_judgment: false
  - id: D3
    description: "A request with no X-Construct-Token is refused with 401 before any capability handler runs"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_request_without_a_token_is_refused_before_any_handler_runs"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_wrong_token_is_refused"
        status: pass
    human_judgment: false
  - id: D4
    description: "A foreign Host header is refused with 400 and a present, non-allowlisted Origin with 403; an absent Origin is allowed and a loopback Host with a port still passes"
    requirement: HTTP-05
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_foreign_host_header_is_refused"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_foreign_origin_is_refused"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_an_absent_origin_is_allowed"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_loopback_host_with_a_port_is_accepted"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_no_cors_middleware_is_installed"
        status: pass
    human_judgment: false
  - id: D5
    description: "A workspace_id that is not kebab-case is rejected with no filesystem call made — the shape gate runs before discover_workspaces"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_traversal_shaped_id_is_refused_with_no_filesystem_call"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_an_unknown_workspace_id_is_refused_and_names_the_known_ids"
        status: pass
    human_judgment: false
  - id: D6
    description: "Path-shaped payload keys are refused at the HTTP boundary (D-10), while CLI and MCP keep sending paths unchanged (HTTP-02)"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_a_path_shaped_key_beside_the_id_is_refused"
        status: pass
      - kind: integration
        ref: "tests/contract/test_http_surface.py#test_every_path_shaped_key_is_refused_by_the_envelope"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_a_bare_path_payload_is_still_reachable_off_the_http_surface"
        status: pass
    human_judgment: false
  - id: D7
    description: "A second `construct serve` on an occupied port prints an actionable message naming the port and a --port retry, and exits 1 — never uvicorn's exit code 3"
    verification:
      - kind: e2e
        ref: "tests/contract/test_http_surface.py#test_a_busy_port_exits_one_with_actionable_guidance"
        status: pass
    human_judgment: false
  - id: D8
    description: "The launch token is written to {install_root}/.construct/api-token with mode 0600 and never appears in a URL query string"
    verification:
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_launch_token_reaches_a_0600_file_and_stdout"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_token_never_appears_in_a_url"
        status: pass
    human_judgment: false
  - id: D9
    description: "The shared contract-test fixture (temp install root, two discoverable workspaces, known token, TestClient over create_app) that every later Phase 19 plan drives"
    verification:
      - kind: integration
        ref: ".venv/bin/python -m pytest tests/contract -q (357 passed, 22 skipped)"
        status: pass
    human_judgment: false
  - id: D10
    description: "HTTP-02's prohibition — the browser gets no behaviour over shared durable state that CLI and MCP cannot reach by the same path"
    requirement: HTTP-02
    verification:
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_route_table_is_one_capability_route"
        status: pass
      - kind: unit
        ref: "tests/contract/test_http_surface.py#test_the_seam_signature_is_unchanged_by_the_id_resolution"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_seam_has_no_leniency_knob"
        status: pass
    human_judgment: true
    rationale: "The structural half is proven (one route, no per-capability wiring, seam signature untouched, path payloads still accepted off-HTTP). The prohibition as written is a claim about the WHOLE surface vocabulary, and plans 19-02/19-03 add the capability-listing and shared-result-boundary pieces that make a full cross-surface parity assertion possible. The plan carries it as `status: unresolved` and a human should re-read it at phase verification rather than have this plan mark it closed."

# Metrics
duration: 41 min
completed: 2026-08-03
status: complete
---

# Phase 19 Plan 01: End-to-End Tracer and `construct serve` Failure Modes Summary

**A loopback FastAPI surface where one browser-shaped POST crosses a Host/Origin/token guard, is resolved from a workspace id inside the GOV-01 seam, reaches a real capability handler, and returns the identical body the CLI and MCP surfaces return.**

## Performance

- **Duration:** 41 min
- **Started:** 2026-08-03T00:19:00Z
- **Completed:** 2026-08-03T01:00:00Z
- **Tasks:** 2
- **Files modified:** 11 (7 created, 4 modified)

## Accomplishments

- **The whole Phase 19 architecture proven on one real request.** `POST /api/capabilities/workspace.status` with `{"payload": {"workspace_id": "demo"}}` and a valid `X-Construct-Token` returns 200 and a body asserted *equal to a direct seam call's serialized result* — not equal to a hand-written literal, so the test cannot drift from the other two surfaces.
- **Workspace-id resolution lives inside `CapabilityRegistry.invoke` (D-01), not in the adapter.** `invoke`'s signature is unchanged and `test_seam_has_no_leniency_knob` still passes, because the install root is process-level launch context (D-09) rather than a per-surface argument. CLI and MCP inherit id addressing for free; HTTP gets no private dialect.
- **`LocalhostGuard` runs Host, Origin and token in that order before dispatch.** DNS-rebinding refused at 400, foreign `Origin` at 403 (the MCP specification's status), a bad or missing token at 401 via `secrets.compare_digest` on bytes. No `CORSMiddleware` and no `TrustedHostMiddleware`, both declined for stated reasons.
- **The traversal gate's *ordering* is proven, not assumed.** `discover_workspaces` is patched and asserted zero-called for `workspace_id: "../../etc"`, so the kebab-case shape gate demonstrably runs before any `iterdir()`.
- **`construct serve` owns its failure modes.** A pre-flight socket probe turns a busy port into a red message naming the port, a concrete `--port <n+1>` retry and an `lsof` pointer, exiting **1** — asserted in a real child process, because uvicorn 0.50+ would have exited 3.
- **The shared contract fixture exists** (`tests/contract/conftest.py`): a temp install root with two real workspaces built through `initialize_workspace`/`create_card`, a known token, and a `TestClient` over `create_app`. Every later plan in this phase drives it.

## Task Commits

1. **Task 1: End-to-end "read a workspace's status from a browser" — one path only** — `5379d6f` (feat)
2. **Task 2: `serve` owns its failure modes — loopback bind, port collision, token delivery** — `bb971e7` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `src/construct/capabilities/workspaces.py` (new, 283 lines) — the shape gate, the allowlist gate, the measured `cap_id -> field` maps, `PATH_SHAPED_KEYS`, and the launch install-root accessors
- `src/construct/api/__init__.py` (new) — `TOKEN_HEADER`, `DEFAULT_API_PORT`, `CAPABILITY_ROUTE`, `TOKEN_FILE_RELPATH`; deliberately free of FastAPI so `cli.py` can read the port default without the ASGI stack
- `src/construct/api/app.py` (new) — `create_app`, the `Envelope` model, the single `POST /api/capabilities/{cap_id}` route, D-10's key refusal
- `src/construct/api/middleware.py` (new) — `ALLOWED_HOSTS` and `LocalhostGuard`
- `src/construct/capabilities/registry.py` — one call to `resolve_payload_workspace` between record resolution and model validation, plus the docstring paragraph recording why that is behaviour and not a knob
- `src/construct/cli.py` — `LOOPBACK_HOST` constant and the `serve` command (probe, token file, lazy ASGI imports)
- `pyproject.toml` — `fastapi>=0.141,<1` and `uvicorn>=0.51` declared
- `tests/contract/conftest.py` (new) — the shared fixture set
- `tests/contract/test_http_surface.py` (new, 602 lines) — 30 tests covering the tracer, the trust boundary, the id gate, the field-map exhaustiveness guards and `serve`'s failure modes
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — the `construct serve` row (see deviation 1)

## Decisions Made

Beyond the plan's named D-09 / D-10 / D-17:

- **`DEFAULT_API_PORT = 8787.** The plan left the literal to this task. Chosen for being outside the IANA well-known range and the macOS ephemeral range, and for not colliding with any tool this project already runs (Vite 5173, Streamlit 8501, `npx serve` 3000).
- **`discover_workspaces` is imported lazily inside `resolve_workspace_id`.** Two reasons: `construct.views` pulls the whole contract-model package in and this module now sits on `registry.py`'s import path (i.e. every CLI startup), and the call-time lookup is what makes the function patchable at its *source* module, which is how the gate-ordering proof is written.
- **The middleware's refusal body is `{"detail": ...}`.** The research sketch used `{"error": ...}`, which would have given this surface two body shapes — undermining the stated reason for declining `TrustedHostMiddleware`. Plan 19-07 replaces both with the shared `api/errors.py` body.
- **The token is compared as bytes.** `secrets.compare_digest` raises `TypeError` on a `str` carrying a non-ASCII code point, and Starlette hands header values over latin-1 decoded — so a `str` comparison would let a caller convert the 401 into a 500 by sending one high byte.
- **Allowed origins carry no port,** so `http://localhost:5173` is refused today. Recorded in the code as the honest current state rather than widened to a wildcard nobody would notice.
- **`INSTALL_ROOT_FIELD` participates in `resolve_payload_workspace`,** as the plan specifies — but the scope mismatch it leaves (an id resolves to one *workspace*, while the views capabilities want the root *above* the workspaces) is written into the docstring and handed to plan 19-04, which owns HTTP-03's completion. Not quietly patched, because the fix is a scoping decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Documented `construct serve` in the artifact catalog**

- **Found during:** Task 1, at the plan-level verification step
- **Issue:** `tests/contract/test_artifact_catalog.py::test_every_typer_leaf_is_represented` failed with `artifact-catalog.md does not document these CLI leaf commands: construct serve`. Adding a Typer leaf trips this guard by design — it is the same class of deliberate tripwire as `REGISTRY_SIZE`.
- **Fix:** Added a `construct serve` row to the "Non-registry CLI commands (independent path)" table beside `construct mcp`, noting that `serve` is a process entry point whose capabilities are all reached through the registry, and updated the prose leaf count 34 → 35.
- **Files modified:** `CONSTRUCT-CLAUDE-spec/artifact-catalog.md`
- **Verification:** `.venv/bin/python -m pytest tests/contract tests/integration/test_surface_parity.py -q` → 374 passed
- **Committed in:** `5379d6f`

**2. [Rule 3 - Blocking] Created a `.venv` symlink so the documented test invocation works in this worktree**

- **Issue:** The plan's `<verify>` and acceptance criteria all invoke `.venv/bin/python`, and a git worktree has no `.venv` — the environment lives at the main checkout root.
- **Fix:** `ln -s ../../../.venv .venv`. This is not an improvisation: the repository's own `.gitignore` documents the pattern in a comment ("a `.venv` SYMLINK (e.g. one pointing a git worktree at the main checkout's environment)") and ignores both the directory and the symlink forms.
- **Files modified:** none tracked — the symlink is gitignored and disappears with the worktree.
- **Verification:** `.venv/bin/python -V` → Python 3.14.5
- **Committed in:** n/a (untracked by design)

**3. [Rule 3 - Blocking] Installed `fastapi` without re-running the editable install**

- **Issue:** The plan's action says `.venv/bin/python -m pip install -e '.[dev]'`. Running that **from inside a worktree** would repoint the shared editable install's `.pth` at this worktree's `src/`, so the main checkout and every sibling worktree would silently import this agent's tree — and would break outright when the worktree is removed. That is the same hazard `test_surface_parity.py::_cli` documents for hardcoded interpreter paths.
- **Fix:** `.venv/bin/python -m pip install "fastapi>=0.141,<1" "uvicorn>=0.51"` — the two declared dependencies only. The dry run reproduced RESEARCH's measurement exactly (`Would install fastapi-0.141.1`, every other requirement already satisfied, zero new transitive dependencies), so the Package Legitimacy Audit's clearance holds and no install checkpoint was required.
- **Verification:** `PYTHONPATH=<worktree>/src .venv/bin/python -c "import fastapi, uvicorn"` exits 0
- **Committed in:** the declarations in `pyproject.toml` are part of `5379d6f`

**4. [Rule 2 - Missing Critical] Token compared as bytes, not as `str`**

- **Found during:** Task 1 (`LocalhostGuard`)
- **Issue:** The RESEARCH sketch calls `secrets.compare_digest(supplied, self.token)` on two `str` values. `compare_digest` raises `TypeError` when either `str` carries a non-ASCII code point, and Starlette decodes header values as latin-1 — so a caller could turn the token check into an unhandled 500 by sending a single high byte in `X-Construct-Token`. An authentication check that can be crashed is an authentication check that can be probed.
- **Fix:** Encode both operands to UTF-8 before comparison, keeping every rejection a 401. Constant-time comparison is unaffected.
- **Files modified:** `src/construct/api/middleware.py`
- **Verification:** covered by `test_a_wrong_token_is_refused` and `test_a_request_without_a_token_is_refused_before_any_handler_runs`; the reasoning is recorded inline at the call site
- **Committed in:** `5379d6f`

### Test-design choices that differ from the plan's literal wording

Recorded here because they are visible in the diff, not because they change scope:

- The plan's behavior block says the tracer body's `success` and `data` match the seam's result. `workspace.status`'s handler returns a **list** of `WorkspaceItem`, so `_serialize_result` yields `{"items": [...]}` and there is no `success` key to compare. The tracer therefore asserts **whole-body equality** against `_serialize_result(direct_invoke(...))` — a strictly stronger claim — and a second test (`test_the_shared_operation_result_envelope_survives_the_http_boundary`) makes the literal `success`/`data` claim against `workflow.status`, which does return an `OperationResult` and spells its workspace field `workspace` rather than `path`. Both readings are covered.
- The plan's Task 2 token-file case does not specify a driver. It uses `CliRunner` with `uvicorn.run` monkeypatched, because `serve`'s last statement blocks forever and a child process would need a poll-and-hope loop. The **port-collision** case still uses a real child process, since an exit code cannot be faked in-process — which is the assertion that case exists to make.
- Every `serve` test binds a freshly discovered free port rather than `DEFAULT_API_PORT`: the pre-flight probe really binds, so using the default would fail on any machine already running the server. The declared default is asserted separately by reading the Typer option.

---

**Total deviations:** 4 auto-fixed (3 blocking, 1 missing critical)
**Impact on plan:** No scope creep. Three of the four are worktree/tooling mechanics that the plan could not have anticipated; the fourth is a two-line hardening of the authentication check. Every plan acceptance criterion is met as written.

## Issues Encountered

**Two pre-existing test failures, out of scope, logged not fixed.**
`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::{test_my_construct_has_canonical_layout, test_ping_eon_has_canonical_layout}` fail in this worktree with `Missing canonical directory in .../test-ws/<ws>: digests/`. Cause: `.gitignore` ignores `test-ws/`, so those fixture workspaces are only partly tracked — `digests/`, `publish/` and `.construct/` exist solely as untracked directories in the main checkout and never materialise in a worktree. Plan 19-01 touches no fixture and no `test-ws` path; the failure reproduces on the plan's base commit. Full detail and the two candidate fixes are recorded in `deferred-items.md` in this phase directory.

Everything else is green: **826 passed, 22 skipped** on the full suite.

## Known Stubs

None. No `TODO`, `FIXME`, placeholder value, skipped test or unrun `<verify>` was introduced by this plan. The two forward-references in the new code are explicit hand-offs to named later plans, each with a passing test today:

- `_serialize_result` is duplicated from `mcp/server.py`; **plan 19-03** moves the single copy to a shared module and deletes both. The duplicate is fully exercised, not a placeholder.
- The route catches only the two typed seam errors and lets anything else propagate; **plan 19-07** installs the sanitizing exception handler. Deliberate: a `str(exc)` stopgap would be the exact T-18-10 path leak that would then have to be unpicked.

## Flagged Assumptions Carried Forward

- **HTTP-03 / unclassified — "review manually".** The spec-less probe fallback's one unresolved row, carried forward per the plan. Plan 19-04 owns HTTP-03's completion and repeats the flag.
- **RESEARCH assumption A2** — that emitting `str(resolved)` satisfies both the 13 `str`-typed and the 13 `Path`-typed workspace fields — is implemented and proven on the three capabilities this plan exercises, but **not** yet on all 26. Plan 19-04 Task 2 converts it into a parametrised test. The assumption is recorded in the `resolve_payload_workspace` docstring so the next reader meets it in the code.
- **The `INSTALL_ROOT_FIELD` scope mismatch** described under Decisions Made is handed to plan 19-04 with the same treatment.

## Threat Flags

None. No security-relevant surface outside the plan's `<threat_model>` was introduced. Every register row this plan owns is mitigated and covered:

| Threat | Mitigation shipped | Proven by |
|---|---|---|
| T-19-01 Host / rebinding | `ALLOWED_HOSTS` check, port stripped, 400 before dispatch | `test_a_foreign_host_header_is_refused`, `test_a_loopback_host_with_a_port_is_accepted` |
| T-19-12 Origin | present-and-not-allowlisted → 403; absent allowed | `test_a_foreign_origin_is_refused`, `test_an_absent_origin_is_allowed` |
| T-19-02 CORS / CSRF | no `CORSMiddleware`; non-safelisted token header forces an unanswerable preflight | `test_no_cors_middleware_is_installed` |
| T-19-03 traversal | shape gate strictly before the filesystem gate | `test_a_traversal_shaped_id_is_refused_with_no_filesystem_call` |
| T-19-07 token comparison | `secrets.compare_digest` on bytes, never `==` | `test_a_wrong_token_is_refused` |
| T-19-08 token delivery | header only; `0600` on-disk copy; no query string | `test_the_launch_token_reaches_a_0600_file_and_stdout`, `test_the_token_never_appears_in_a_url` |
| T-19-11 bind address | `LOOPBACK_HOST` named constant, asserted, and no wildcard literal anywhere in `cli.py` | `test_the_bind_address_is_the_loopback_constant` |
| T-19-SC supply chain | dry run reproduced RESEARCH's measurement (`fastapi-0.141.1`, zero new transitive deps) | recorded above under deviation 3 |

## User Setup Required

None — no external service configuration required. The launch token is generated per run; nothing to provision.

## Next Phase Readiness

Ready for the rest of Phase 19. The three seams the phase turns on are now wired and green together:

- **For 19-02 (capability listing):** `create_app` and the `Envelope`/route shape are stable; the registry is iterated nowhere in `app.py`, which is the property `GET /api/capabilities` must preserve.
- **For 19-03 (shared result boundary):** `_serialize_result` exists in two places on purpose, with the move recorded in both docstrings.
- **For 19-04 (HTTP-03 completion):** `WORKSPACE_FIELD` / `INSTALL_ROOT_FIELD` / `CREATE_MODE_CAPABILITIES` are classified and guarded by an exhaustiveness test; two named items are handed over (the A2 parametrisation and the `INSTALL_ROOT_FIELD` scope mismatch).
- **For 19-07 (error boundary):** the route's failure handling is deliberately minimal and typed, with no `str(exc)` to unpick.
- **For every later plan:** `tests/contract/conftest.py` is the shared driver.

**Concerns:** one, and it is environmental — the `test-ws` fixture failures in `deferred-items.md` will show up in any worktree-based execution of the remaining Phase 19 plans. They are not a Phase 19 regression, but a reviewer reading a red suite should know that before assuming otherwise.

## Self-Check: PASSED

- All 8 files listed under `key-files.created` exist on disk.
- All 3 plan commits present in `git log`: `5379d6f`, `bb971e7`, `ac7e4b1`.
- Working tree clean after the metadata commit.
- Plan `<verification>` re-run at close-out: `tests/contract` → 357 passed / 22 skipped; `test_seam_has_no_leniency_knob` → passed; full suite → 826 passed / 22 skipped, with the two out-of-scope `test-ws` fixture failures documented in `deferred-items.md`.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-03*
