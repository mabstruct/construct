---
phase: 10-durable-human-review-research-run
verified: 2026-06-28T17:30:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/5  # functionality passed; 1 security blocker
  gaps_closed:
    - "CR-01: run_id path traversal — @field_validator now on ResearchRunInput, ReviewInput, InspectInput; compile_digest has resolve/startswith containment guard"
    - "WR-01: append_rejected now idempotent (skip-if-exists in research_dedup.py)"
    - "WR-03: inspect_research_run returns status=failed for nonexistent run (not misleading unknown)"
    - "WR-05: review_research_run guards snap.next == ('gate_review',) before resuming"
  gaps_remaining: []
  regressions: []
---

# Phase 10: Durable Human-Review research.run — Re-Verification Report

**Phase Goal:** Users can run research as a durable reviewed workflow that ingests only approved findings and can resume safely.
**Verified:** 2026-06-28T17:30:00Z
**Status:** passed
**Re-verification:** Yes — after commit 9076aba gap closure (CR-01 + WR-01/WR-03/WR-05)

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                             | Status      | Evidence                                                                                                               |
|----|---------------------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------|
| 1  | User can run `research.run` from CLI and MCP to execute the full workflow as one command         | VERIFIED    | Unchanged from initial pass: 9-node graph, CLI dispatch, MCP auto-discovery, `test_full_run_offline` passes           |
| 2  | User can review, approve, or reject findings before any refs/cards/seeds/digests are written     | VERIFIED    | Unchanged: interrupt-only `gate_review`, `test_no_writes_before_approval` passes                                       |
| 3  | User can resume or inspect a paused workflow with state preserved across process restarts        | VERIFIED    | Unchanged: `SqliteSaver`/`_open_checkpointer`; `test_cross_process_resume` and `test_inspect_no_resume` pass          |
| 4  | User can rerun without duplicating URLs, refs, rejected findings, or partial batch writes        | VERIFIED    | `append_rejected` now skip-if-exists (WR-01 closed); `test_rejected_append_is_idempotent` passes                      |
| 5  | User can see run status, gate IDs, ingest counts, digest path, seed update, and events in result | VERIFIED    | Unchanged: `RunResult` D-12 fields; `test_run_result_fields` passes                                                   |

**Score:** 5/5 truths verified

---

### Security Gate (CR-01) — CLOSED

**CR-01: Path traversal via unvalidated `run_id` — FIXED**

All three input models now validate `run_id` at the trust boundary via a shared `_validate_run_id` helper wired through Pydantic `field_validator`:

- `research_run.py:52-65` — `_validate_run_id(value)` calls `KEBAB_CASE_PATTERN.fullmatch(value)` (pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`); raises `ValueError` on mismatch; `None` is allowed (auto-generated).
- `research_run.py:116` — `ResearchRunInput._check_run_id = field_validator("run_id")(_validate_run_id)`
- `research_run.py:129` — `ReviewInput._check_run_id = field_validator("run_id")(_validate_run_id)`
- `research_run.py:139` — `InspectInput._check_run_id = field_validator("run_id")(_validate_run_id)`
- `research_run.py:714-716` — `compile_digest` defense-in-depth containment check: `md_path = (digests_dir / f"{digest_id}.md").resolve()` followed by `if not str(md_path).startswith(str(digests_dir.resolve()) + "/"):  raise ValueError("digest path escapes the workspace digests directory")`
- `research_run.py:180-188` — `_new_run_id()` generates `run-{YYYYMMDD}-{HHMMSS}-{hex6}` which satisfies `KEBAB_CASE_PATTERN` by construction.

The MCP shim at `catalog.py:519-539` passes `**kwargs` into the validated model; a `ValidationError` is caught by `_run_result_to_operation`'s `except Exception` and returned as `OperationResult(success=False, ...)` — no file is written.

**Regression test:** `test_run_id_rejects_path_traversal` (line 852) asserts `ValidationError` is raised for `run_id="../../../../tmp/evil"` on all three models, and that `run_id=None` (auto-generate) still passes. `test_generated_run_id_is_kebab_safe` (line 872) confirms `_new_run_id()` satisfies `KEBAB_CASE_PATTERN` and round-trips through the validator.

---

### Correctness Warnings — Status After Gap Closure

**WR-01 — `append_rejected` idempotency: CLOSED**

`research_dedup.py:157-159`:
```python
if normalized_url in rejected_normalized_urls(ledger):
    return
```
A crash+resume that re-enters `ingest_batch` will not grow the rejected ledger with duplicate entries for the same URL. Regression test: `test_rejected_append_is_idempotent` (line 150 of `test_research_dedup.py`) — asserts two calls with the same URL leave exactly one ledger entry.

**WR-02 — `assert`-based kebab invariant in `ref_id_for`: NOTED, REMAINS**

`research_dedup.py:76`:
```python
assert KEBAB_CASE_PATTERN.fullmatch(ref_id) is not None, ref_id
```
The assertion is stripped under `python -O`. Risk remains low: the preceding `re.sub(r"[^a-z0-9]+", "-", ...)` already constrains the value to `[a-z0-9-]`, so the assert is a belt-and-suspenders invariant that can never fire in practice. Not treated as a blocker; no fix required this phase.

**WR-03 — `inspect_research_run` returns `status="failed"` for nonexistent run: CLOSED**

`research_run.py:1057-1061`:
```python
elif not snap.next:
    status = values.get("status", "completed") if values else "failed"
    message = "Run is complete." if values else "No such run."
```
When `snap.values` is empty (no persisted run for this `thread_id`), `status` is now `"failed"` rather than `"unknown"`, and the catalog shim's `success = result.status != "failed"` correctly maps it to `success=False`. Regression test: `test_inspect_nonexistent_run_reports_failed` (line 884) asserts `insp.status == "failed"` for a fresh workspace.

**WR-05 — `review_research_run` gate check before resume: CLOSED**

`research_run.py:1016-1025`:
```python
if snap.next != ("gate_review",):
    values = snap.values or {}
    if values and not snap.next:
        return _completion_result(inp.run_id, values, True)
    return RunResult(
        status="failed",
        run_id=inp.run_id,
        gate_id=values.get("gate_id", inp.run_id) if values else inp.run_id,
        message="No paused run awaiting review for this run_id.",
    )
```
A completed run returns its stored `_completion_result` without re-executing any write node. A nonexistent or mid-run thread returns `status="failed"`. Regression tests: `test_review_does_not_resume_completed_run` (line 895) asserts `second.events == first_events` on a double-review; `test_review_nonexistent_run_reports_failed` (line 931) asserts `status="failed"` for a ghost `run_id`.

---

### Test Suite Results

```
uv run --extra dev pytest tests/llm/test_research_run.py tests/pipelines/test_research_dedup.py tests/contract/test_research_run_cli_mcp.py -q
53 passed in 0.94s
```

Previous total: 47 (21 + 18 + 8). New total: 53 (+6 regression tests):

| New Test | File | Covers |
|---|---|---|
| `test_run_id_rejects_path_traversal` | `test_research_run.py:852` | CR-01 (all 3 input models) |
| `test_generated_run_id_is_kebab_safe` | `test_research_run.py:872` | CR-01 (`_new_run_id`) |
| `test_inspect_nonexistent_run_reports_failed` | `test_research_run.py:884` | WR-03 |
| `test_review_does_not_resume_completed_run` | `test_research_run.py:895` | WR-05 (no double-write) |
| `test_review_nonexistent_run_reports_failed` | `test_research_run.py:931` | WR-05 (ghost run) |
| `test_rejected_append_is_idempotent` | `test_research_dedup.py:150` | WR-01 |

---

### Required Artifacts

| Artifact                                          | Expected                                          | Status     | Details                                                                                             |
|---------------------------------------------------|---------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------|
| `src/construct/llm/research_run.py`               | Full durable workflow; nodes, gate, runners       | VERIFIED   | 1083 lines; `_validate_run_id` + `field_validator` on all 3 input models; containment guard in `compile_digest` |
| `src/construct/pipelines/research_dedup.py`       | normalize_url, ref_id_for, fuzzy, ledger I/O      | VERIFIED   | 183 lines; `append_rejected` now has skip-if-exists guard at lines 157-159                          |
| `src/construct/capabilities/catalog.py`           | research.run/review/inspect CapabilityRecords     | VERIFIED   | 3 shims at lines 515-539; `ValidationError` caught by `except Exception` in `_run_result_to_operation` |
| `src/construct/cli.py`                            | research run/review/inspect + `_render_run_result` | VERIFIED  | Unchanged from initial verification                                                                  |
| `tests/llm/test_research_run.py`                  | All regression tests present and green            | VERIFIED   | 27 tests (21 original + 6 new); all pass                                                            |
| `tests/pipelines/test_research_dedup.py`          | idempotency regression test present and green     | VERIFIED   | 19 tests (18 original + 1 new); all pass                                                            |
| `tests/contract/test_research_run_cli_mcp.py`     | Registry + CLI/MCP parity contract tests          | VERIFIED   | 8 tests; all pass (unchanged)                                                                       |

---

### Key Link Verification

No regressions on previously-verified links. Re-check of the CR-01 trust-boundary chain:

| From | To | Via | Status | Details |
|---|---|---|---|---|
| MCP caller (`**kwargs`) | `ResearchRunInput` / `ReviewInput` / `InspectInput` | `field_validator("run_id")` → `_validate_run_id` | WIRED | `ValidationError` raised before model is constructed; caught by shim's `except Exception` → `success=False` |
| `compile_digest` | `digests/<id>.md` | `(digests_dir / f"{digest_id}.md").resolve()` + `startswith` check | WIRED | Defense-in-depth guard at `research_run.py:714-716`; raises `ValueError` before any write if path escapes |

---

### Requirements Coverage

| Requirement | Source Plans       | Description                                                                                     | Status    | Evidence                                                                             |
|-------------|--------------------|-------------------------------------------------------------------------------------------------|-----------|--------------------------------------------------------------------------------------|
| RSCH-02     | 10-03, 10-04, 10-05 | `research.run` CLI/MCP executes full workflow as one command                                   | SATISFIED | Full workflow node chain + CLI/MCP registration; 53/53 tests pass                   |
| RSCH-03     | 10-03, 10-04       | Review/approve/reject before any SOT writes                                                     | SATISFIED | interrupt-only `gate_review`; `test_no_writes_before_approval` passes                |
| RSCH-04     | 10-03, 10-04       | Resume/inspect paused workflow across process restarts                                          | SATISFIED | `SqliteSaver` + `_open_checkpointer`; `test_cross_process_resume` passes             |
| RSCH-05     | 10-02, 10-04       | Idempotent rerun for duplicate URLs, refs, rejected findings, partial batches                   | SATISFIED | `append_rejected` now skip-if-exists; `test_rejected_append_is_idempotent` passes   |

**Note:** REQUIREMENTS.md traceability table still shows RSCH-02 through RSCH-05 as "Pending." Code fully implements all four requirements. Documentation-only gap, not a code defect.

---

### Anti-Patterns — Updated Status

| File                                              | Line    | Pattern                                          | Severity    | Status After Gap Closure                                                                      |
|---------------------------------------------------|---------|--------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------|
| `src/construct/llm/research_run.py`              | 52-65, 116, 129, 139 | `@field_validator("run_id")` + `_validate_run_id` | FIXED | CR-01 closed; kebab constraint now enforced at all 3 MCP trust-boundary entry points |
| `src/construct/llm/research_run.py`              | 714-716 | `resolve()` + `startswith()` containment guard   | FIXED       | Defense-in-depth path containment in `compile_digest` confirmed present                       |
| `src/construct/pipelines/research_dedup.py`      | 157-159 | `append_rejected` skip-if-exists guard           | FIXED       | WR-01 closed; idempotency confirmed by regression test                                        |
| `src/construct/pipelines/research_dedup.py`      | 76      | `assert KEBAB_CASE_PATTERN.fullmatch(ref_id)`    | INFO (WR-02) | Still present; `assert` stripped under `-O`; preceding `re.sub` makes the value safe; not blocking |
| `src/construct/llm/research_run.py`              | 1016-1025 | Gate check before `Command(resume=...)` in `review_research_run` | FIXED | WR-05 closed; completed/nonexistent runs return without re-executing write nodes |
| `src/construct/llm/research_run.py`              | 1061    | `status = "failed"` for empty `snap.values`      | FIXED       | WR-03 closed; nonexistent run now returns `success=False` via the catalog shim               |

---

### Human Verification Required

None — all 5 success criteria have offline test coverage that passes. The phase has no UI, real-time, or external service behaviors that require human testing.

---

### Gaps Summary

No gaps remain. The 1 security blocker (CR-01) and all 3 correctness warnings (WR-01, WR-03, WR-05) confirmed closed by code inspection and regression tests (53/53 green). WR-02 (`assert`-based kebab invariant in `ref_id_for`) is acknowledged as low-risk and does not block completion.

---

_Verified: 2026-06-28T17:30:00Z_
_Verifier: Claude (gsd-verifier) — re-verification after commit 9076aba_
