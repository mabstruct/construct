---
phase: 11-curation-pipe-steps
verified: 2026-06-28T22:00:00Z
status: passed
human_verified: 2026-06-29
score: 3/3 must-haves verified
overrides_applied: 0
human_verification_note: "Both human-UAT items resolved 2026-06-29 (see 11-HUMAN-UAT.md): visual render confirmed against test-ws/ping-eon; WR-04 exit-code semantics accepted (exit 0 = ran without crashing; failure visible via status/JSON/event log)."
human_verification:
  - test: "Run `construct curation run -w <workspace>` (without --json) against a real workspace and inspect the terminal output"
    expected: "Output shows status (completed/degraded), run_id, and a per-step line for each of the 5 real steps plus 3 deferred steps. Completed real steps have concrete summaries (e.g., '0 error(s), 1 warning(s)', '2 decay candidate(s) over a 28d window'). Deferred nodes show 'skipped — <step> deferred to Phase 12'. Status line clearly distinguishes completed vs degraded."
    why_human: "The _render_curation_result function is not covered by automated assertions — only --json output is tested. Criterion #2 ('user can distinguish') depends partly on the visual rendering being meaningful."
  - test: "Decide on exit-code semantics for a degraded curation run (code review WR-04)"
    expected: "Deliberate product decision: should `construct curation run` exit 0 or non-zero when a required check degrades? Currently exits 0 even when CurationRunResult.status == 'degraded'. This affects scripting and CI integration."
    why_human: "This is a deliberate contract decision. The code review (WR-04) flags it as an automation gap — automation cannot detect a required-step failure via exit code. Whether success = (status != 'failed') is intentional or an oversight requires developer judgment."
---

# Phase 11: Curation Pipe Steps Verification Report

**Phase Goal:** Users can run curation and receive real deterministic integrity, decay, orphan, connection-health, and report results instead of placeholder success responses.
**Verified:** 2026-06-28T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can run `curation.run` from the CLI and stdio MCP server and receive real integrity, decay, orphan, connection-health, and report output | VERIFIED | `test_cli_mcp_schema_parity` invokes CLI with a real workspace and confirms output keys match `CurationRunResult.model_fields`; `test_full_run_offline_real_findings` asserts concrete findings (candidate_ids, counts, ok flag) for all 5 real steps; all 7 contract tests pass |
| 2 | User can distinguish completed deterministic checks, degraded checks, and skipped optional views refresh in the curation result | VERIFIED (auto) / needs human check (visual) | `test_run_status_degraded_on_step_failure` confirms clean run = "completed", required-step failure = "degraded"; `test_deferred_nodes_visible_skipped` confirms deferred nodes show status="skipped" required=False reason="deferred to Phase 12"; `_render_curation_result` prints per-step lines — human visual check needed |
| 3 | User no longer receives placeholder success messages; each reported step includes concrete findings, counts, or an explicit degraded/skipped state | VERIFIED | `test_steps_return_concrete_findings` fails if any real step summary/reason contains "placeholder" and asserts all findings dicts are non-empty; `test_full_run_offline_real_findings` verifies concrete candidate_ids from decay_scan and orphan_scan |

**Score:** 3/3 truths verified (automated); human check needed for visual rendering of criterion #2.

---

### CUR-01 Requirement Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| CUR-01 | 11-01, 11-02, 11-03 | User can run `curation.run` through CLI/MCP surface and receive real results instead of placeholder success responses | SATISFIED | REQUIREMENTS.md line 30 marks `[x]`; traceability table line 100 shows `Complete`; 359 tests pass including 8 llm behavioral tests + 7 contract tests |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/construct/llm/curation_run.py` | CurationRunState, 4 models, 8 graph nodes, build_curation_run_graph, run_curation_run, inspect_curation_run | VERIFIED | 583 lines; all named exports importable; substantive graph nodes with try/except; linear §4.3 topology |
| `src/construct/capabilities/catalog.py` | curation.run + curation.inspect CapabilityRecord registration; dual-mode shims | VERIFIED | Registration at lines 433-452; `_curation_run_shim`/`_curation_inspect_shim` at lines 596-611; `_curation_result_to_operation` at lines 572-593 |
| `src/construct/cli.py` | curation Typer sub-app with run/inspect + `_render_curation_result` | VERIFIED | `curation_app` at line 409; `curation_run_cmd` at line 729; `curation_inspect_cmd` at line 745; `_render_curation_result` at line 695 iterates steps |
| `tests/llm/test_curation_run.py` | 8 named test functions covering all CUR-01 distinctions | VERIFIED | 298 lines; 8 tests pass; concrete assertions on candidate_ids, governance threshold delta, canonical write absence, deferred-reason text |
| `tests/contract/test_curation_run_cli_mcp.py` | Registry presence, positional rejection, MCP auto-discovery, CLI presence, schema parity | VERIFIED | 122 lines; 7 tests pass; `test_cli_mcp_schema_parity` does a live CLI + handler invocation |
| `tests/llm/conftest.py` | `write_card` extended with created/last_verified; `curation_workspace` fixture | VERIFIED | `write_card` at line 183 accepts `created`/`last_verified` kwargs; `curation_workspace` at line 262 builds date-relative 4-card set with 1 connection |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py:curation_run_cmd` | `get_registry().get('curation.run').handler` | registry dispatch | WIRED | Line 741: `cap.handler(workspace_path=str(workspace))` |
| `catalog.py:_curation_run_shim` | `construct.llm.curation_run.run_curation_run` | keyword-only shim | WIRED | Line 601: `lambda: run_curation_run(CurationRunInput(**kwargs))` |
| `curation_run.py:load_config` | `WorkspaceLoader.load_governance()` | governance threshold read (D-05) | WIRED | Line 191: `gov = WorkspaceLoader(Path(state["workspace_path"])).load_governance()` |
| `curation_run.py:integrity_check` | `construct.services.validation.validate_workspace` | primitive extraction (Pitfall 4) | WIRED | Line 283: `report = validate_workspace(Path(state["workspace_path"]))` |
| `curation_run.py:_open_checkpointer` | `.construct/workflow/curation-run.sqlite` | persistent sqlite3 connection | WIRED | Line 213: `db = Path(workspace) / ".construct" / "workflow" / "curation-run.sqlite"` |
| `stdio MCP server` | `construct_curation_run` / `construct_curation_inspect` | registry auto-discovery (no server.py edit) | WIRED | `grep "construct_curation" mcp/server.py` returns 0; `test_in_mcp_tool_list` + `test_mcp_server_exposes_curation` pass |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `integrity_check` node | `report.errors`, `report.warnings`, `report.ok` | `validate_workspace(Path(...))` | Yes — calls validation service against workspace files | FLOWING |
| `decay_scan` node | `candidate_ids` | `loader.load_cards()` with date math vs `decay_window_days` from governance | Yes — computes per-card age from `created`/`last_verified` date objects | FLOWING |
| `orphan_scan` node | `candidate_ids`, `degree` map | `loader.load_connections()` + `loader.load_cards()` | Yes — builds degree map from ConnectionRecord.from_/to, filters by age | FLOWING |
| `connection_maintenance` node | `totals`, `l1_l2_only` | `bridge_detect(state["workspace_path"])` | Yes — runs bridge detection (L1/L2 offline; L3 auto-skips without API key) | FLOWING |
| `compile_report` node | `cards`, `connections`, `domains` | `graph_status(state["workspace_path"])` | Yes — reads workspace file counts | FLOWING |
| Deferred skip nodes | `status="skipped"`, `required=False` | `_deferred_step(step)` helper | N/A — intentional explicit skips with Phase 12 reason (D-10) | FLOWING (by design) |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module imports cleanly | `python -c "from construct.llm.curation_run import CurationRunInput, CurationStepResult, CurationRunResult, build_curation_run_graph, run_curation_run, inspect_curation_run; print('ok')"` | `import ok` | PASS |
| run_id trust boundary: bad id rejected | `python -c "from construct.llm.curation_run import CurationRunInput; CurationRunInput(workspace_path='x', run_id='Bad_ID')"` | `ValidationError` raised | PASS |
| run_id trust boundary: valid id accepted | `python -c "from construct.llm.curation_run import CurationRunInput; CurationRunInput(workspace_path='x', run_id='valid-run-1')"` | accepted | PASS |
| CLI `curation run --help` exits 0 | `construct curation run --help` | exit 0; shows `--workspace/-w`, `--json/-j`; no `--provider` option | PASS |
| CLI `curation inspect --help` exits 0 | `construct curation inspect --help` | exit 0; shows `--workspace/-w`, `--run-id` (required), `--json/-j` | PASS |
| Full LLM test suite | `pytest tests/llm/test_curation_run.py -q` | 8 passed | PASS |
| Full contract test suite | `pytest tests/contract/test_curation_run_cli_mcp.py -q` | 7 passed | PASS |
| Full regression suite | `pytest -q` | 359 passed, 5 warnings | PASS |

---

### Structural Integrity Checks

| Check | Expected | Result |
|-------|----------|--------|
| `grep -c "add_conditional_edges\|interrupt(\|print("` on curation_run.py | 0 (linear graph, stderr-only) | 0 |
| `grep -c "from_conn_string"` on curation_run.py | 0 (persistent-connection checkpointer) | 0 |
| `grep "construct_curation" src/construct/mcp/server.py` | No match (auto-discovery only) | No match |
| Lifecycle.archived exclusion in both decay_scan and orphan_scan | lines 317 + 371 | Present in both nodes |
| Both `record.from_` and `record.to` in orphan degree map | orphan_scan lines 363-364 | Both counted |
| Legacy curation-cycle placeholder lambdas at catalog.py ~725-741 | Untouched (D-11) | Present and unmodified |
| TBD/FIXME/XXX markers in Phase 11 new files | None | None found |

---

### Anti-Patterns Found

| File | Pattern | Severity | Notes |
|------|---------|----------|-------|
| `catalog.py` ~725-741 | Legacy `workflow.run curation-cycle` placeholder lambdas: `"Integrity check placeholder"`, `"Decay scan placeholder"`, etc. | INFO | Pre-existing D-11 debt, deliberately left intact this phase. Flagged for Phase 12 / CUR-05. These are under the separate `workflow.run` capability id, not `curation.run`. |
| `catalog.py` line 299 | `handler=lambda **kwargs: OperationResult(success=False, message="Not yet implemented — see Plan 02")` | INFO | Pre-existing `views.generate_data` placeholder, not introduced by Phase 11. |

No new placeholder, TBD, FIXME, or XXX patterns were introduced in Phase 11 files.

---

### Code Review Warnings (from 11-REVIEW.md)

The code review found 4 warnings and 2 info items. None are BLOCKER-class. Their relevance to goal achievement:

| Finding | Impact on Goal | Recommendation |
|---------|----------------|----------------|
| WR-01: Reused run_id duplicates steps in `operator.add` channel | Does not block goal; CLI auto-generates run_id so this only affects agents that supply a stable run_id | Consider adding a completed-thread guard before `graph.invoke` |
| WR-02: Terminal `curation_cycle_complete` event not persisted; run/inspect events disagree | Minor divergence; inspect still returns correct steps and status | Persist terminal event into graph state or document the run-only behavior |
| WR-03: `orphan_scan` inner exception handler catches only `WorkspaceLoadError`, not `FileNotFoundError`/`OSError` | Could cause unnecessary `degraded` on a missing connections.json; normal workspaces are unaffected | Broaden handler: `except (WorkspaceLoadError, FileNotFoundError, OSError): pass` |
| WR-04: `degraded` run returns `OperationResult.success=True` and CLI exits 0 | Automation cannot detect a required-step failure via exit code; human visual output does show "degraded"; **requires product decision** | Surfaced as human verification item below |
| IN-01: `inspect_curation_run` creates `.construct/workflow/` despite "no mutation" docstring | Cosmetic — docstring inaccuracy; behavior is correct (derived artifact) | Reword docstring |
| IN-02: `_validate_run_id` docstring overstates path-traversal surface | Cosmetic — run_id is only a LangGraph thread_id here, not a filesystem path component | Reword docstring |

---

### Human Verification Required

#### 1. Visual rendering of `_render_curation_result` (criterion #2)

**Test:** Run `construct curation run -w <path-to-a-real-workspace>` (without `--json`) against an actual workspace.
**Expected:** The terminal output should show:
- `status: completed` (or `degraded` if a step failed)
- `run_id: cur-<timestamp>-<hex>`
- A per-step line for each of the 5 real steps and 3 deferred steps, e.g.:
  - `  - integrity_check: completed — 0 error(s), N warning(s)`
  - `  - decay_scan: completed — N decay candidate(s) over a 28d window`
  - `  - promotion_review: skipped — promotion_review deferred to Phase 12 (curation gates land in Phase 12)`
- An events line if events are populated
**Why human:** The `_render_curation_result` function (cli.py:695) iterates steps and prints per-step lines. Automated tests only assert on `--json` output (`test_cli_mcp_schema_parity`). Criterion #2 ("user can visually distinguish completed vs degraded vs skipped") depends on the rendered table being meaningful, which requires a human to observe.

#### 2. Product decision: exit code semantics for degraded runs (WR-04)

**Test:** Run `construct curation run -w <workspace>` against a workspace where a step fails (e.g., corrupt `governance.yaml`), or observe the exit code for a clean run that has a required-step degraded.
**Expected:** Developer confirms whether exit code 0 on a degraded run is intentional (i.e., success = "run completed without crashing" rather than "all checks passed") or a bug (should exit non-zero when `status == "degraded"`).
**Why human:** `_curation_result_to_operation` at catalog.py:589 sets `success = result.status != "failed"`. A degraded run (status="degraded") maps to success=True and CLI exits 0. This is a product contract decision: if automation scripts need to detect required-step failures via exit code, the mapping needs changing. The code review (WR-04) flags this but the correct behavior requires a deliberate developer decision.

---

### Gaps Summary

No gaps blocking goal achievement. All 3 success criteria are satisfied by the test suite. Two code review warnings (WR-03 and WR-04) are robustness improvements worth addressing in a follow-up:

- **WR-03 (one-liner fix):** `except (WorkspaceLoadError, FileNotFoundError, OSError): pass` in orphan_scan prevents an edge-case degraded run when connections.json is deleted.
- **WR-04 (product decision):** `success = result.status == "completed"` in `_curation_result_to_operation` would make the CLI exit non-zero for degraded runs, enabling automation to detect required-step failures.

These can be addressed as part of Phase 12 curation hardening or as a targeted fix, after the WR-04 product decision is made.

---

_Verified: 2026-06-28T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
