---
phase: 18-contract-governance-foundations
plan: 01
subsystem: api
tags: [pydantic, mcp, fastmcp, typer, capability-registry, contract-governance]

# Dependency graph
requires:
  - phase: 16-graph-enumeration
    provides: the knowledge.card.list capability record and its CLI/MCP parity contract test, used here as the seam's first subject and structural analog
provides:
  - "CapabilityRegistry.invoke(cap_id, payload) — the single validating invocation seam every surface routes through (GOV-01)"
  - "capabilities/errors.py — CapabilityInputError / CapabilityNotFoundError, so both surfaces render one reason string"
  - "MCP dispatch routed through the seam, with mcp/server.py still fully registry-generated"
  - "knowledge.card.list CLI call site converted onto the seam (1 of 26; Plan 03 owns the rest)"
  - "tests/integration/test_surface_parity.py — differential real-CLI-process vs real-MCP-dispatch harness with an extensible case table"
  - "A measured answer to assumption A1: the pinned FastMCP cannot advertise a per-tool input schema"
affects: [18-02, 18-03, 18-04, 18-05, 18-06, 18-07, 18-08, phase-19-http-adapter]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Resolve → validate → dispatch: the three-step invocation seam, with no strict/lenient knob (D-05)"
    - "Typed seam errors subclass Exception, not ValueError, so a pydantic field validator upstack cannot capture them"
    - "Differential surface testing: a real child process for the CLI arm, the FastMCP-registered closure for the MCP arm"
    - "Mutation probe as a substitute for a RED phase when the behaviour under test was already delivered by a tracer task"

key-files:
  created:
    - src/construct/capabilities/errors.py
    - tests/integration/test_surface_parity.py
  modified:
    - src/construct/capabilities/registry.py
    - src/construct/mcp/server.py
    - src/construct/cli.py
    - AGENTS.md
    - .planning/codebase/CONVENTIONS.md

key-decisions:
  - "A1 resolved by execution: FastMCP.add_tool has no input-schema parameter, so add_tool is left unchanged and the advertised-schema gap is pinned by a test instead of implied away"
  - "Seam errors subclass Exception rather than ValueError (deliberate, documented departure from AGENTS.md § Error Handling)"
  - "Added a CapabilityError base class so Plan 03's 25 call sites can catch the seam with one clause"
  - "Seam-level reason parity is proven in a fresh child process, because Typer's parser rejects an undeclared flag before a payload exists — the real CLI structurally cannot deliver an undeclared field to the seam"
  - "The all-optional empty-payload edge is proven against a purpose-built record in a local registry, because no capability in the catalog has an all-optional model today"

patterns-established:
  - "Case table drives the parity harness: adding a converted capability is a table row, never new test logic"
  - "Known-limitation tests: assert the gap so a future dependency upgrade fails loudly and prompts the fix"

requirements-completed: [GOV-01]

coverage:
  - id: D1
    description: "One capability round-trips identically through the real CLI process and real MCP dispatch — same success verdict, same message, same record key set"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_success_parity_verdict_message_and_records"
        status: pass
    human_judgment: false
  - id: D2
    description: "CapabilityRegistry.invoke exists with the signature Phase 19's HTTP adapter routes through, and carries no leniency knob"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_seam_exists_with_the_cross_phase_signature"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_seam_has_no_leniency_knob"
        status: pass
    human_judgment: false
  - id: D3
    description: "A payload carrying an undeclared field is rejected with one identical reason string across both dispatch paths, and the handler never runs"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_undeclared_field_reason_is_identical_across_dispatch_paths"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_a_rejected_payload_never_reaches_the_handler"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty-payload and exact-fit adjacency edges: a missing required field yields one identical reason; the exact declared field set is accepted and one extra key flips it; an all-optional model runs with its declared defaults"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_missing_required_field_reason_is_identical_across_dispatch_paths"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_exact_fit_payload_is_accepted_and_one_extra_key_flips_it"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_all_optional_model_accepts_an_empty_payload_and_uses_its_defaults"
        status: pass
    human_judgment: false
  - id: D5
    description: "The MCP surface stays registry-generated after the seam insertion — no capability-specific identifier in mcp/server.py"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_mcp_server_names_no_capability"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_mcp_dispatch_routes_through_the_seam"
        status: pass
    human_judgment: false
  - id: D6
    description: "The seam's reason string never echoes submitted payload values back to an MCP client (T-18-10)"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_seam_reason_does_not_echo_the_submitted_payload_values"
        status: pass
    human_judgment: false
  - id: D7
    description: "AGENTS.md no longer forbids the phase it governs: src/ and tests/ are no longer declared frozen, and the 'No active GSD' claim is gone, with live conventions intact"
    verification:
      - kind: other
        ref: "grep -c \"Do not modify \\`archive/v01-python/\\`, \\`src/\\`, or \\`tests/\\`\" AGENTS.md == 0; grep -ci 'No active GSD' AGENTS.md == 0; grep -c 'archive/v01-python' AGENTS.md == 5; grep -c '.venv/bin/python' AGENTS.md == 2 (unchanged)"
        status: pass
    human_judgment: false
  - id: D8
    description: "The advertised MCP schema is still FastMCP's **kwargs inference, not the capability's model — GOV-01 holds for enforcement but not for discovery on this pinned FastMCP"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_advertised_mcp_schema_is_not_yet_the_model_schema"
        status: pass
    human_judgment: true
    rationale: "The test proves the gap exists and is pinned, but whether shipping GOV-01 with a known discoverability gap is acceptable — versus pinning a newer FastMCP or hand-building tool definitions — is a product/scope call for the user, not something a passing test can settle."

# Metrics
duration: 16 min
completed: 2026-07-27
status: complete
---

# Phase 18 Plan 01: The GOV-01 Validating Invocation Seam Summary

**`CapabilityRegistry.invoke()` now resolves, validates against the declared `input_model`, then dispatches — proven end-to-end on `knowledge.card.list` by a differential harness driving a real `construct` subprocess against the closure FastMCP actually registered.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-07-27T07:14:00Z
- **Completed:** 2026-07-27T07:30:00Z
- **Tasks:** 3
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- **The seam exists and is enforced.** `input_model` was previously computed into a JSON Schema for MCP discovery and then discarded, which is why `CardListInput`'s `extra="forbid"` was inert over MCP (WR-02). Every payload crossing the seam is now validated before a handler runs.
- **Both surfaces agree, proven differentially.** The harness drives a real `construct` child process against the real FastMCP-registered closure and asserts the same verdict, message, and record key set — rather than testing the seam once and assuming both callers reach it.
- **One reason string on rejection.** An undeclared field and a missing required field each produce a byte-identical reason across both dispatch paths, and the handler provably never runs.
- **`mcp/server.py` stayed registry-generated.** The change was one line inside `make_handler`. A test asserts no capability id or tool name appears anywhere in that file, because Phase 19's HTTP adapter is generated from that structure.
- **Assumption A1 was resolved by execution, not assumed.** The pinned FastMCP cannot advertise a per-tool input schema; the resulting discoverability gap is pinned by a test instead of being implied away.
- **AGENTS.md no longer forbids this phase.**

## Task Commits

1. **Task 1 (tracer): one capability, one seam, two real surfaces** — `829c222` (feat)
2. **Task 2: the rejection contract + A1 resolution** — `7fe8dbe` (test)
3. **Task 3: correct the two stale AGENTS.md directives** — `e78b02b` (docs)

## Recorded facts the plan asked for

### Baseline test counts (Task 1 precondition, assumption A3)

| Stage | Collected | Passed | Skipped | Failed |
|---|---|---|---|---|
| Baseline as the worktree was handed over | 532 | 525 | 5 | **2** |
| Baseline after repairing the worktree's gitignored fixtures | 532 | 531 | 1 | **0** |
| After this plan | 547 | 546 | 1 | **0** |

The two initial failures were **not** inherited `dev-v05` defects. `test-ws/` is gitignored, so the worktree received only a partial copy — `digests/`, `publish/`, `views/` and `AGENTS.md` were missing from both fixture workspaces, and `TestFixtureRoot::test_*_has_canonical_layout` correctly reported that. Copying the fixtures from the main checkout produced a genuinely green baseline (and un-skipped 4 tests that had been silently skipping for want of the same content). A3 therefore holds: every failure this plan could have caused was distinguishable from environment noise. Net new tests: **15**.

### `inspect.signature(FastMCP.add_tool)` — verbatim

```
(self, fn: 'AnyFunction', name: 'str | None' = None, title: 'str | None' = None, description: 'str | None' = None, annotations: 'ToolAnnotations | None' = None, icons: 'list[Icon] | None' = None, meta: 'dict[str, Any] | None' = None, structured_output: 'bool | None' = None) -> 'None'
```

### Is `input_schema` now advertised over MCP? **No.**

There is no `input_schema` / `inputSchema` / `schema` / `parameters` argument on `add_tool`, so the already-computed `entry["input_schema"]` cannot be passed through. Per the plan's instruction for this branch, `add_tool` was left unchanged and the limit is recorded rather than implied away. Measured, side by side:

```
ADVERTISED (FastMCP-inferred from make_handler's **kwargs):
  {"properties": {"kwargs": {"title": "Kwargs"}}, "required": ["kwargs"],
   "title": "handlerArguments", "type": "object"}

MODEL SCHEMA (registry, CardListInput):
  {"additionalProperties": false,
   "properties": {"workspace": {...}, "domain": {...}, "include_archived": {...}},
   "required": ["workspace"], "title": "CardListInput", "type": "object"}
```

**So GOV-01 is true for behaviour and false for discovery on this pinned FastMCP.** Enforcement is closed unconditionally — the seam validates every payload, and an MCP client sending `{"bogus": 1}` is rejected. But a client *reading* the advertised schema sees a single opaque `kwargs` property and cannot discover the real field set. `test_advertised_mcp_schema_is_not_yet_the_model_schema` pins this; when a FastMCP upgrade makes that test fail, that is the signal to pass the schema through and delete the test. This is flagged for the user as decision D8 in the coverage block.

## Files Created/Modified

- `src/construct/capabilities/errors.py` *(new)* — `CapabilityError` base plus `CapabilityInputError` / `CapabilityNotFoundError`; `from_validation_error` builds the reason from pydantic's field-level errors with `include_input=False` / `include_context=False` (T-18-10).
- `src/construct/capabilities/registry.py` — added `invoke(cap_id, payload) -> Any`: resolve via existing `get`, validate, dispatch with `**model.model_dump()`; both third-party errors chained with `from exc`.
- `src/construct/mcp/server.py` — one line: `capability.handler(**kwargs)` → `registry.invoke(capability.id, kwargs)`. Nothing else touched; still 52 lines.
- `src/construct/cli.py` — `knowledge card list` builds a payload dict and dispatches through the seam, catching the two typed errors per AGENTS.md § Error Handling. The other 24 `.handler(` call sites are untouched (Plan 03).
- `tests/integration/test_surface_parity.py` *(new)* — 15 tests over an extensible case table.
- `AGENTS.md` — the two stale directives corrected.
- `.planning/codebase/CONVENTIONS.md` — the `extra="ignore"` views-projection note at its source.

## Decisions Made

- **Seam errors subclass `Exception`, not `ValueError`** — a documented departure from AGENTS.md § Error Handling, on the plan's explicit instruction: a `ValueError` subclass raised inside the seam can be captured by a pydantic field validator upstack and re-emitted against an unrelated field, forking the reason string per surface.
- **Added a `CapabilityError` base class** (beyond the plan's two named exports) so Plan 03's 25 conversions can catch the seam with one clause. The CLI still catches the two subclasses explicitly, as instructed.
- **No leniency knob** (D-05), asserted by a test rather than left to reviewer vigilance.
- **`model_dump()` in python mode, not JSON mode**, so `Path` fields reach handlers as `Path` rather than `str`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The worktree had no `.venv`**

- **Found during:** Task 1 precondition
- **Issue:** Every command in this plan is specified as `.venv/bin/python …`, but `.venv` is gitignored and so absent from the worktree — the precondition run failed with exit 127.
- **Fix:** Symlinked the main checkout's `.venv` into the worktree. The repository's own `.gitignore` explicitly anticipates this case ("a `.venv` SYMLINK (e.g. one pointing a git worktree at the main checkout's environment)"), so this is a sanctioned pattern, not an invention. Verified the symlink does not make the environment lie: pytest's `pythonpath = [".", "src"]` resolves against the worktree rootdir, and `import construct` from the worktree resolves to the worktree's `src`.
- **Files modified:** none tracked (`.venv` is gitignored)

**2. [Rule 3 - Blocking] The worktree's gitignored test fixtures were only partially materialised**

- **Found during:** Task 1 precondition
- **Issue:** 2 tests failed on a supposedly-green baseline. `test-ws/` is gitignored; the worktree copy was missing `digests/`, `publish/`, `views/` and `AGENTS.md` in both fixture workspaces.
- **Fix:** Copied `test-ws/` from the main checkout. Confirmed by direct comparison that the missing content exists there, so these were environment gaps and not `dev-v05` defects — the distinction assumption A3 depends on.
- **Verification:** baseline went from `525 passed / 5 skipped / 2 failed` to `531 passed / 1 skipped / 0 failed`
- **Files modified:** none tracked (`test-ws/` is gitignored)

**3. [Rule 3 - Blocking] The CLI subprocess arm cannot hardcode `.venv/bin/python`**

- **Found during:** Task 1
- **Issue:** The plan specifies the CLI arm as `subprocess.run` on `.venv/bin/python -m construct.cli`. Inside a worktree that path is either absent or — once symlinked — points at an environment whose editable install resolves to a *different checkout*. The child process would silently test code the test never touched.
- **Fix:** The harness uses `sys.executable` with `PYTHONPATH` pinned to this checkout's `src`. This preserves the property the plan actually requires (a real, independent process, so the cached registry singleton is not shared — RESEARCH Pitfall 5) while guaranteeing the child imports the tree under test. Documented in the helper's docstring.
- **Files modified:** `tests/integration/test_surface_parity.py`
- **Committed in:** `829c222`

**4. [Rule 2 - Missing critical] AGENTS.md restated the stale "src/ and tests/ are archived" claim in a second place**

- **Found during:** Task 3
- **Issue:** Correcting only the guardrail would have left the "Active vs archived" table listing `src/` and `tests/` under **Python v0.1 (archived)**, and the line "**Default:** All work uses the Claude-native track unless the user explicitly asks to resume Python runtime exploration" — leaving the file internally contradictory and still misdirecting a reader away from `src/`.
- **Fix:** Split the table into an active Python-runtime row and a frozen `archive/v01-python/` row, and rewrote the default line to match. The plan's "change nothing else" is glossed by the conventions it enumerates as needing to survive; all of those are intact (`.venv/bin/python` count unchanged at 2, pytest rule, Pydantic conventions, `__future__` annotations, type annotations, error handling).
- **Files modified:** `AGENTS.md`
- **Committed in:** `e78b02b`

**5. [Rule 2 - Missing critical] The `extra="forbid"` note would have been silently overwritten**

- **Found during:** Task 3
- **Issue:** The Pydantic conventions in AGENTS.md live inside a generated block (`<!-- GSD:conventions-start source:CONVENTIONS.md -->`). A note added only there is destroyed by the next codebase-map regeneration — precisely the "future reviewer restores it" failure the plan wanted to prevent.
- **Fix:** Added the D-03 views-projection exception note to `.planning/codebase/CONVENTIONS.md` as well, so it survives regeneration.
- **Files modified:** `.planning/codebase/CONVENTIONS.md`
- **Committed in:** `e78b02b`

---

**Total deviations:** 5 auto-fixed (3 blocking, 2 missing-critical)
**Impact on plan:** No scope creep. Three were worktree-environment repairs required to run the plan at all; two were consistency fixes without which Task 3's own goal would have been only half-achieved. No production behaviour differs from what the plan specified.

## Issues Encountered

**Task 2 had no RED phase, and the reason matters.**

Task 2 is marked `tdd="true"`, but every test written for it passed on first run. Investigated rather than accepted: the behaviour was already delivered by Task 1 — the tracer builds the seam end-to-end by design — and Task 2's only *implementation* instruction was conditional on A1, which resolved to "make no change to `add_tool`". So there was no new behaviour to drive, and manufacturing an artificial failing test would have proved nothing.

Instead, the tests were verified non-vacuous by a **mutation probe**: validation was temporarily removed from `registry.invoke` and the suite re-run. Exactly the five rejection-contract tests failed (`…undeclared_field…`, `…missing_required…`, `…never_reaches_the_handler`, `…exact_fit…`, `…all_optional…`); the seam was then restored with a single-file `git checkout --`. This is stronger evidence than a hand-written RED, and it is recorded here rather than left as an unexplained green.

**The real CLI structurally cannot deliver an undeclared field to the seam.**

The plan's `<behavior>` asks for the CLI and MCP reason strings to be equal for `{"workspace": ws, "bogus": 1}`. Measured, they cannot be, and this is a property of the surface rather than a defect:

```
CLI:  construct knowledge card list --workspace <ws> --bogus 1
      → exit 2, "No such option: --bogus"      (Click's parser, before a payload exists)
MCP:  {"error": "Invalid input for capability 'knowledge.card.list':
                 bogus: Extra inputs are not permitted"}   (the seam)
```

Typer rejects the undeclared flag before the seam is reached, so the CLI's *flag-level* message is Click's, not the seam's. Rather than paper over this, the harness proves both halves separately: the real CLI process rejects undeclared input non-zero and without a traceback (`test_cli_process_rejects_an_undeclared_flag_without_a_traceback`), and seam-level reason parity is proven where it is decidable — the same payload crossing the same seam in an independent child process versus through MCP dispatch, rendered with the CLI's exact convention (`ERROR {exc}` + exit 1) so "strip the framing" means the same thing on both arms.

This is a substantive GOV-01 finding, not a workaround: **the CLI surface's payload is seam-valid by construction while an MCP payload is caller-controlled**, which is exactly why WR-02 was an MCP defect and never a CLI one.

**No capability in the catalog has an all-optional input model.** `CardListInput` requires `workspace`, `CurationInspectInput` requires both fields, and `WorkspacePathInput` requires `path` (and does not even set `extra="forbid"` — that generalisation is D-06/Plan 02). The empty-payload acceptance edge is therefore proven against a purpose-built record in a *local* registry, rather than by asserting something untrue about the real catalog.

## Known Stubs

None. No placeholder values, no skipped tests added, and every `<verify>` in the plan was executed.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or trust-boundary schema change beyond the seam the plan specifies. T-18-01 and T-18-10 are mitigated and test-covered (D3, D6). T-18-02 is **partially** mitigated: the enforcement half is closed by the seam, the discoverability half cannot be closed on this pinned FastMCP (see D8). T-18-11 remains `accept` as planned — the broad `except` in `mcp/server.py` is preserved deliberately, and is what makes the seam's typed error comparable as a string across surfaces. T-18-SC holds: **no packages were installed.**

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `registry.invoke` is stable and is the signature Phase 19's generated HTTP adapter routes through. It has no leniency knob, and a test enforces that.
- **GOV-01 is proven on a slice, not yet at scale.** 1 of 26 call sites is converted; the remaining 24 `.handler(` sites in `cli.py` plus the non-CLI callers are Plan 03's work. `requirements-completed: [GOV-01]` reflects this plan's declared requirement, but GOV-01 is not fully satisfied until Plan 03 lands — the phase's shared-ID gate should keep it open until then.
- The parity harness is a case table: Plan 03 adds rows, not logic.
- **One decision is queued for the user (D8):** whether shipping GOV-01 with a known MCP schema-discoverability gap is acceptable, or whether a newer FastMCP should be pinned.
- Plan 02 can proceed on `WorkflowStatusInput`; Plan 03's conversions should catch `CapabilityError` rather than the two subclasses individually.

## Self-Check: PASSED

- Created files exist on disk: `src/construct/capabilities/errors.py`, `tests/integration/test_surface_parity.py`
- Task commits exist in `git log`: `829c222`, `7fe8dbe`, `e78b02b`
- Plan `<verification>` re-run at close-out: `tests/integration/test_surface_parity.py` 15 passed; full suite 546 passed / 1 skipped / 0 failed; `mcp/server.py` asserted free of capability-specific identifiers
- `key_links` present: `invoke(` in both `src/construct/mcp/server.py` and `src/construct/cli.py`
- All `<acceptance_criteria>` for Tasks 1–3 executed and passing

---
*Phase: 18-contract-governance-foundations*
*Completed: 2026-07-27*
