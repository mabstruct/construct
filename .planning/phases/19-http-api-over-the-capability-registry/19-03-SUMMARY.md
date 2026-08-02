---
phase: 19-http-api-over-the-capability-registry
plan: 03
subsystem: api
tags: [serialization, error-handling, privacy, ast-guard, mcp, capability-registry]

# Dependency graph
requires:
  - phase: 18-capability-seam-hardening
    provides: "CapabilityRegistry.invoke as the one seam, CapabilityInputError.from_validation_error with include_input=False (T-18-10), and the UNRESOLVED_DIRECT_CALLERS shrink-only baseline shape (D-23)"
provides:
  - "src/construct/capabilities/results.py — serialize_result and sanitize_exception, the one result/error boundary CLI, MCP and the HTTP adapter all render through"
  - "ResultSerializationError — an unprojectable value is now a loud bug rather than a silently stringified path"
  - "MCP's generic exception arm sanitized; its typed CapabilityError arm left intact so GOV-01 reason parity is unchanged"
  - "graph.status and bridge.detect emit the workspace name on the success path (D-19)"
  - "PATH_LEAKING_EXCEPTION_HANDLERS — a shrink-only baseline keyed per function over the remaining source sites"
affects: [19-05, 19-06, 19-07, http-error-handling, http-validation-handler]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Exception -> reason string by structural reduction: the message is never read, only an allow-listed attribute (OSError.strerror)"
    - "Result projection with no stringifying arm anywhere, including per-item in the sequence branch"
    - "Shrink-only AST baseline keyed <module>::<function>, with both no-new-offender and no-stale-entry directions plus a non-vacuity floor"

key-files:
  created:
    - src/construct/capabilities/results.py
    - tests/contract/test_result_boundary.py
  modified:
    - src/construct/mcp/server.py
    - src/construct/pipelines/graph_status.py
    - src/construct/pipelines/bridge_detect.py
    - src/construct/capabilities/catalog.py
    - tests/contract/test_card_list_cli_mcp.py
    - tests/contract/test_curation_run_cli_mcp.py
    - tests/contract/test_daily_run_cli_mcp.py
    - tests/contract/test_research_run_cli_mcp.py
    - tests/integration/test_surface_honesty.py

key-decisions:
  - "D-16 applied as written: the sanitizer, the baseline, and the success-path data leaks are three separate tracks, so the third could not be quietly absorbed into the first"
  - "D-19 applied to both pipelines: a capability emits the workspace name; a local caller appends the absolute path. views/lib/parse_*.py already emitted workspace.name for the same field, so this converged on an existing convention"
  - "sanitize_exception never reads the exception message at all. A filter over str(exc) would have to be right about every message shape ever raised; not reading it is right by construction"
  - "ResultSerializationError is deliberately NOT a CapabilityError — a serialization gap rendered as a seam reason would look like a normal refusal and nobody would fix it"
  - "The sequence branch's per-item str(item) was removed too: it was a stringifying arm wearing a projection's name, and would have rendered a list[Path] as absolute paths through the very branch meant to keep them out"
  - "The baseline carries a handler COUNT alongside the per-function set, because a per-function set alone cannot see a tenth handler landing inside an already-listed function"

patterns-established:
  - "Allow-listed detail channel: a sanitizer names one attribute it may read and discards it whole if it carries a path marker, rather than trimming a message into shape"
  - "Criterion-3 tests assert against a SUCCESSFUL body and a path-SHAPED regex, not only against the fixture's own tmp path"
  - "Every shrink-only guard ships with a planted-offender test, so it has been observed failing"

requirements-completed: [HTTP-04]

coverage:
  - id: D1
    description: "One shared serializer and sanitizer exist in construct.capabilities.results, and the MCP surface imports them instead of holding its own copy"
    requirement: "HTTP-04"
    verification:
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_a_pydantic_model_is_projected_in_json_mode"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_a_dataclass_recurses_so_nested_errors_are_projected"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_a_real_operation_result_round_trips_without_a_stringifying_fallback"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_the_serializer_carries_no_stringifying_fallback_in_its_source"
        status: pass
    human_judgment: false
  - id: D2
    description: "The MCP surface's catch-all no longer renders raw exception text: an unexpected exception produces a reason carrying the class name, with no filesystem path and no traceback"
    requirement: "HTTP-04"
    verification:
      - kind: integration
        ref: "tests/contract/test_result_boundary.py#test_the_mcp_catch_all_no_longer_renders_raw_exception_text"
        status: pass
      - kind: integration
        ref: "tests/contract/test_result_boundary.py#test_the_mcp_catch_all_drops_a_path_from_an_untyped_exception"
        status: pass
      - kind: integration
        ref: "tests/contract/test_result_boundary.py#test_the_mcp_surface_still_renders_the_seams_typed_reason"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_a_validation_error_reason_does_not_echo_the_submitted_payload"
        status: pass
    human_judgment: false
  - id: D3
    description: "graph.status and bridge.detect place no absolute filesystem path in a successful result body; the emitted value is the workspace name"
    requirement: "HTTP-04"
    verification:
      - kind: integration
        ref: "tests/contract/test_result_boundary.py#test_a_successful_graph_status_body_carries_no_absolute_path"
        status: pass
      - kind: integration
        ref: "tests/contract/test_result_boundary.py#test_a_successful_bridge_detect_body_carries_no_absolute_path"
        status: pass
    human_judgment: false
  - id: D4
    description: "A shrink-only baseline pins the remaining exception handlers that build a message from raw exception text, keyed per function, failing on both a new offender and a stale entry"
    requirement: "HTTP-04"
    verification:
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_no_new_path_leaking_exception_handler"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_no_stale_entry_in_the_path_leak_baseline"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_the_path_leak_handler_count_can_only_shrink"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_the_leak_scan_is_not_vacuous"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_the_leak_scan_detects_a_planted_offender"
        status: pass
    human_judgment: false
  - id: D5
    description: "The shared serializer has no stringifying fallback, so a value it cannot project is a bug fixed at the boundary rather than a path coerced into a response"
    requirement: "HTTP-04"
    verification:
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_an_unprojectable_value_raises_instead_of_being_stringified"
        status: pass
      - kind: unit
        ref: "tests/contract/test_result_boundary.py#test_a_sequence_is_projected_item_by_item_and_never_stringified"
        status: pass
    human_judgment: false

# Metrics
duration: 32min
completed: 2026-08-02
status: complete
---

# Phase 19 Plan 03: The Shared Result and Error Boundary Summary

**One `capabilities/results.py` now owns both projections every invoke surface shares — a
never-stringifying `serialize_result` and a `sanitize_exception` that reduces an exception without
ever reading its message — with MCP routed through it, the two success-path path leaks closed at the
source, and the remaining 14 exception sites pinned by a shrink-only AST baseline.**

## Performance

- **Duration:** 32 min
- **Started:** 2026-08-02T22:08:00Z
- **Completed:** 2026-08-02T22:40:22Z
- **Tasks:** 2
- **Files modified:** 11 (2 created, 9 modified)

## Accomplishments

- **The boundary exists and is shared.** `src/construct/capabilities/results.py` carries
  `serialize_result` (moved from `mcp/server.py` with its CR-01 recursion rationale intact) and the
  new `sanitize_exception`. It imports nothing from `construct.services` or `construct.mcp`, so the
  HTTP adapter in 19-05/19-07 can import it without a cycle.
- **The sanitizer is structural, not a filter.** It never reads the exception message. Output is
  `type(exc).__name__` plus at most one bounded detail from a single allow-listed attribute
  (`OSError.strerror`, which CPython populates with the errno description alone and keeps the
  filename separate). A detail carrying a path marker is dropped whole rather than trimmed.
  `str(OSError)`'s embedded absolute path and `str(pydantic.ValidationError)`'s embedded
  `input_value=` are both structurally unreachable, and so is a `Traceback` marker.
- **MCP's last unguarded arm is closed.** `make_handler`'s bare `except Exception: str(exc)` split
  into a typed `CapabilityError` arm (unchanged — its reasons are path-free by construction, which is
  what keeps MCP's reason identical to the CLI's under GOV-01) and a sanitized catch-all.
- **Both success-path leaks are fixed at the source.** `graph_status` and `bridge_detect` emit
  `root.resolve().name`. Consumers were grepped first: none needed the absolute form, and
  `views/lib/parse_*.py` already emitted `workspace.name` for the same field.
- **The remaining sites cannot regrow.** `PATH_LEAKING_EXCEPTION_HANDLERS` pins 9 functions / 14
  handlers in `services/knowledge.py`, with no-new-offender, no-stale-entry, handler-count, and
  non-vacuity assertions, plus a planted-offender test.

## Task Commits

Each task was committed atomically:

1. **Task 1: One shared result/error boundary, and the MCP surface's last stringifying arm closed** — `c6e62d9` (feat)
2. **Task 2: Close the two success-path path leaks, and pin the remaining sites with a shrink-only baseline** — `975ed37` (fix)

## Files Created/Modified

**Created**

- `src/construct/capabilities/results.py` — `serialize_result`, `sanitize_exception`,
  `ResultSerializationError`. The one boundary MCP uses today and HTTP will use next.
- `tests/contract/test_result_boundary.py` — 21 tests: the projection, the sanitizer, the MCP
  wiring driven through `create_server()`, the two success-path bodies, and the shrink-only baseline.

**Modified**

- `src/construct/mcp/server.py` — local `_serialize_result` deleted; imports the shared pair; the
  generic exception arm now renders through `sanitize_exception` with an M-4 comment naming it as
  the last unguarded stringifying arm on a serialized surface.
- `src/construct/pipelines/graph_status.py` — success-path `data["workspace"]` is now the workspace
  name (T-18-32, D-19), with a comment recording the `cli.py` convention it follows and that the
  value is the workspace id HTTP-03 addresses by.
- `src/construct/pipelines/bridge_detect.py` — same change to `bridges["workspace"]`, plus a comment
  recording that no reader wants the absolute form.
- `src/construct/capabilities/catalog.py` — 3 docstring references to the moved symbol updated.
- `tests/contract/test_card_list_cli_mcp.py`, `tests/contract/test_curation_run_cli_mcp.py`,
  `tests/contract/test_daily_run_cli_mcp.py`, `tests/contract/test_research_run_cli_mcp.py`,
  `tests/integration/test_surface_honesty.py` — import the shared serializer under its public name.

## Decisions Made

- **D-16 was applied as three tracks, not folded.** The success-path leaks got their own task, their
  own assertions against a *successful* body, and their own commit. This is the item RESEARCH Pitfall 5
  predicted would be quietly missed if merged into the sanitizer work.
- **D-19 applied to both pipelines.** Consumers were grepped before either key changed:
  `curation_run.compile_report` reads only `cards`/`connections`/`domains`; `daily_run._run_graph_child`
  folds the whole dict into its own result verbatim (a second route the path took to a body, not a
  consumer); `views/lib/parse_bridges.py` reads only the `bridges` array; `BridgesFile` does not
  declare the key at all (`extra="ignore"`). No caller needed a local re-append.
- **The sanitizer does not reuse `llm/curation_run.py:_sanitize_error`.** That helper keeps the
  message's *first line*, which is exactly where `str(OSError)` puts the path. Its docstring trade-off
  is right for the audit trail it feeds (T-11-02/T-11-06) and wrong for a result boundary; the new
  docstring says so and states that `_sanitize_error` is not to be reused at a boundary.
- **The baseline counts handlers as well as functions.** Four of the nine baselined functions carry
  more than one leaking handler, so a per-function set alone would let a tenth land inside `edit_card`
  invisibly. `PATH_LEAKING_HANDLER_COUNT = 14` is asserted by equality, so a fix forces the number down.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] The sequence branch's per-item `str(item)` was removed, not carried over**

- **Found during:** Task 1
- **Issue:** The plan's behavior block says the list/tuple branch "returns an items projection", and the
  truth says the serializer has no stringifying fallback. The moved code's `{"items": [str(item) ...]}`
  is a stringifying arm wearing a projection's name — a `list[Path]` would have been rendered as a list
  of absolute paths through the very branch that exists to keep them out (T-18-10).
- **Fix:** Added `_project`, which passes primitives through, projects models and dataclasses, recurses
  into nested lists and dicts, and raises `ResultSerializationError` on anything else.
- **Files modified:** `src/construct/capabilities/results.py`
- **Verification:** `test_a_sequence_is_projected_item_by_item_and_never_stringified` asserts both the
  projection and the refusal on `[Path("/etc/passwd")]`. No consumer of the old `{"items": ...}` shape
  exists in `src/` or `tests/` (grepped).
- **Committed in:** `c6e62d9`

**2. [Rule 3 - Blocking] Five test modules and three catalog docstrings referenced the deleted symbol**

- **Found during:** Task 1
- **Issue:** The plan requires deleting `mcp/server.py:_serialize_result`. Five test modules imported it
  by that name (`test_card_list_cli_mcp`, `test_curation_run_cli_mcp`, `test_daily_run_cli_mcp`,
  `test_research_run_cli_mcp`, `test_surface_honesty`) and three `catalog.py` docstrings named it as
  the function a capability's return shape must satisfy. All would have been broken or stale.
- **Fix:** Repointed the five imports at `construct.capabilities.results.serialize_result` and updated
  the three docstring references to `capabilities/results.py:serialize_result`.
- **Files modified:** the five test modules plus `src/construct/capabilities/catalog.py`
- **Verification:** `.venv/bin/python -m pytest -q` — 819 passed, 22 skipped.
- **Committed in:** `c6e62d9`

**3. [Rule 1 - Bug] The `bridge.detect` L3 gate had to be forced offline in the new fixture**

- **Found during:** Task 2
- **Issue:** `_l3_semantic` reaches the Anthropic API whenever `ANTHROPIC_API_KEY` is set. A contract
  test whose body shape depends on whether the machine is provisioned is not a contract test — and it
  would have made real LLM calls on a developer's machine.
- **Fix:** The `workspace` fixture does `monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)`, with
  the reason stated in its docstring.
- **Files modified:** `tests/contract/test_result_boundary.py`
- **Verification:** `test_a_successful_bridge_detect_body_carries_no_absolute_path` runs in well under
  a second, which it could not do against a live L3 gate.
- **Committed in:** `975ed37`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 blocking, 1 bug)
**Impact on plan:** All three serve the plan's own stated truths. No scope creep — deviation 1 closes
a leak the plan's truth #5 explicitly forbids, deviation 2 is the mechanical consequence of a change
the plan mandates, and deviation 3 makes a required test deterministic.

## Issues Encountered

- **Both success-path guards were verified red before landing.** Rather than trusting that the
  assertions would have caught the old code, each fix was temporarily reverted and the corresponding
  test re-run: both failed with the tmp workspace's absolute path in the diff, then passed once
  restored. A criterion-3 assertion that has never been observed failing is not known to be one.
- **The measured baseline is 14, not RESEARCH's 13, and the difference is real.** The scan matches both
  `str(exc)` and f-string interpolation of the bound exception. M-4 scanned only for `str(exc)` and so
  could not see `_read_card_file`'s `raise OSError(f"Could not read cards/{card_id}.md: {exc}")`, which
  leaks identically. The reconciliation is written into the test module's docstring; a `str(exc)`-only
  count reproduces M-4's 13 exactly, which is what confirms the two measurements agree.
- **Errno auto-subclassing shapes the reason string.** `OSError(2, ...)` *is* a `FileNotFoundError`, so
  reasons name the errno subclass. That is the more useful of the two names and the tests assert it
  explicitly rather than working around it.
- **Worktree environment, resolved locally and not committed.** The worktree had no `.venv` (symlinked
  to the repo's, which `.gitignore` already anticipates in both directory and symlink form) and was
  missing the `digests/`, `publish/` and `refs/` fixture directories, which git cannot represent because
  they are empty. Both were fixed in the worktree only; neither produced a tracked change.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **19-05 / 19-07 can import the boundary directly.** `serialize_result` and `sanitize_exception` are
  the functions the HTTP adapter's success and error paths should call; the route never has a
  stringifying arm to inherit, because there is none to inherit.
- **19-07 owns the remaining HTTP-04 residue.** The plan's flagged `unclassified` probe row is carried
  forward there, as is RESEARCH assumption A6 — the 27 domain-error handlers classified by exception
  type rather than executed. The shared sanitizer covers them regardless of the classification; only
  the baseline's *size* depends on it, and the test module's docstring records that.
- **Pitfall 6 is still live for 19-07.** FastAPI's documented `RequestValidationError` handler returns
  `exc.body` and `exc.errors()` (which includes `input`). The seam's `from_validation_error` is the
  correct source for that reason string, and `sanitize_exception` is the correct fallback.
- **`OperationResult.message` remains outside the sanitizer's reach by design.** The baseline is what
  holds it, and it holds it by cardinality rather than by behaviour — stated as this plan's blind spot
  in the test module docstring.

## Self-Check: PASSED

- Files claimed created/modified all present on disk (`results.py`, `test_result_boundary.py`,
  `19-03-SUMMARY.md`, `mcp/server.py`, `graph_status.py`, `bridge_detect.py`).
- Commits `c6e62d9`, `975ed37`, `2da8119` all present in `git log`.
- `.venv/bin/python -m pytest -q` — 819 passed, 22 skipped.
- `.venv/bin/python -m pytest tests/contract tests/pipelines tests/integration -q` — 483 passed,
  22 skipped.
- Acceptance criterion `'default=' not in inspect.getsource(results)` exits 0.

## Known Stubs

None. No placeholder values, empty data sources, or TODO markers were introduced.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or trust-boundary schema changes
were introduced; the plan's `<threat_model>` rows T-19-05, T-19-06 and T-19-15 are all mitigated by
the assertions listed under `coverage:` above. T-19-16 remains owned by plan 19-07.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-02*
