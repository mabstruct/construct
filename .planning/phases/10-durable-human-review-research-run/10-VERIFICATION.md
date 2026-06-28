---
phase: 10-durable-human-review-research-run
verified: 2026-06-28T15:10:21Z
status: gaps_found
score: 5/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "User can run research as a durable reviewed workflow that can resume safely"
    status: failed
    reason: "CR-01 (BLOCKER from 10-REVIEW.md): run_id flows unvalidated from the MCP trust boundary into compile_digest where it is interpolated into a filesystem path with no containment check. An attacker-controlled run_id such as '../../../../tmp/evil' writes the digest markdown outside the workspace. The fix — field_validator on ResearchRunInput/ReviewInput/InspectInput + resolve().startswith() guard in compile_digest — is documented in 10-REVIEW.md but has NOT been applied to the codebase."
    artifacts:
      - path: "src/construct/llm/research_run.py"
        issue: "ResearchRunInput.run_id (line 95), ReviewInput.run_id (line 104), InspectInput.run_id (line 115) are typed str with no @field_validator; compile_digest lines 618/643/682-683 write md_path = digests_dir / f'digest-{run_id}.md' with no resolve/containment guard"
    missing:
      - "Add @field_validator('run_id') enforcing KEBAB_CASE_PATTERN to ResearchRunInput, ReviewInput, and InspectInput"
      - "Add resolve().startswith() containment guard in compile_digest (defense-in-depth)"
---

# Phase 10: Durable Human-Review research.run Verification Report

**Phase Goal:** Users can run research as a durable reviewed workflow that ingests only approved findings and can resume safely.
**Verified:** 2026-06-28T15:10:21Z
**Status:** gaps_found — 1 security BLOCKER (CR-01), 4 correctness warnings
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                             | Status      | Evidence                                                                                                               |
|----|---------------------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------|
| 1  | User can run `research.run` from CLI and MCP to execute the full workflow as one command         | VERIFIED    | CLI `construct research run/review/inspect` all exit 0 with `--help`; `construct_research_run/_review/_inspect` auto-discovered via registry; `test_full_run_offline` passes (21/21 tests green)                             |
| 2  | User can review, approve, or reject findings before any refs/cards/seeds/digests are written     | VERIFIED    | `gate_review` (line 408-423) contains ONLY `interrupt()` — confirmed; `test_no_writes_before_approval` passes; writes are strictly downstream of `Command(resume=...)`                                                |
| 3  | User can resume or inspect a paused workflow with state preserved across process restarts        | VERIFIED    | `_open_checkpointer` opens `SqliteSaver` on `.construct/workflow/research-run.sqlite`; `test_cross_process_resume` and `test_inspect_no_resume` both pass; no `from_conn_string` usage (0 occurrences confirmed)        |
| 4  | User can rerun without duplicating URLs, refs, rejected findings, or partial batch writes        | VERIFIED    | `deduplicate` filters against refs/ + rejected ledger + in-batch; `ingest_batch` uses `ref_id_for` + skip-if-exists; `test_idempotent_rerun` and `test_partial_batch_resume_safe` pass                               |
| 5  | User can see run status, gate IDs, ingest counts, digest path, seed update, and events in result | VERIFIED    | `RunResult` exposes `status`, `gate_id`, `refs_created`, `cards_created`, `digest_path`, `seed_update`, `events`; `test_run_result_fields` passes and asserts all D-12 fields                                      |

**Score:** 5/5 truths verified for functionality

---

### Security Gate (CR-01) — BLOCKER

The code review (10-REVIEW.md) flagged one BLOCKER confirmed independently in the codebase:

**CR-01: Path traversal — unvalidated `run_id` flows into a written file path**

- `ResearchRunInput.run_id` (line 95), `ReviewInput.run_id` (line 104), `InspectInput.run_id` (line 115): typed `str` / `str | None` with `model_config = {"extra": "forbid"}` only. No `@field_validator` enforcing kebab-safe characters.
- `compile_digest` (lines 618, 643, 682-683): derives `digest_id = f"digest-{run_id}"` then writes `md_path = digests_dir / f"{digest_id}.md"` without calling `.resolve()` or checking the result stays within `digests_dir`.
- The MCP shim at `catalog.py:520,529,537` passes `**kwargs` directly into these models — `run_id` from an untrusted caller reaches `compile_digest` unmodified.
- A `run_id` of `../../../../tmp/evil` resolves outside the workspace and writes attacker-controlled markdown there.
- The CLI `research run` generates the handle internally (low risk), but `research review` (`--run-id`) and `research inspect` (`--run-id`) accept caller-supplied values, and the MCP surface is fully exposed.

`ref_id_for`/`ref_id` are path-safe (kebab slug + sha1 hash). The digest path is the one unguarded sink.

**Fix (documented in 10-REVIEW.md CR-01):**
```python
# In ResearchRunInput, ReviewInput, InspectInput:
from pydantic import field_validator
from construct.schemas.config import KEBAB_CASE_PATTERN

@field_validator("run_id")
@classmethod
def _validate_run_id(cls, v):
    if v is not None and KEBAB_CASE_PATTERN.fullmatch(v) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9-])")
    return v
```
Plus a defense-in-depth containment check in `compile_digest`:
```python
md_path = (digests_dir / f"{digest_id}.md").resolve()
if not str(md_path).startswith(str(digests_dir.resolve()) + "/"):
    raise ValueError("digest path escapes workspace")
```

---

### Required Artifacts

| Artifact                                          | Expected                                          | Status     | Details                                                           |
|---------------------------------------------------|---------------------------------------------------|------------|-------------------------------------------------------------------|
| `src/construct/llm/research_run.py`               | Full durable workflow; nodes, gate, runners       | VERIFIED   | 1031 lines; all 9 nodes present; interrupt-only gate confirmed    |
| `src/construct/pipelines/research_dedup.py`       | normalize_url, ref_id_for, fuzzy, ledger I/O      | VERIFIED   | 176 lines; all 7 functions present; stdlib-only                   |
| `src/construct/capabilities/catalog.py`           | research.run/review/inspect CapabilityRecords     | VERIFIED   | 3 capabilities registered; mcp_tool_names confirmed at runtime    |
| `src/construct/cli.py`                            | research run/review/inspect + _render_run_result  | VERIFIED   | All 3 commands dispatch via `get_registry().get()`; help exits 0  |
| `tests/llm/test_research_run.py`                  | 8 RSCH/SC tests (all green)                       | VERIFIED   | 21 tests total, 21 passed; all 8 named RSCH/SC tests present      |
| `tests/llm/conftest.py`                           | sqlite_checkpointer + scored_findings_batch       | VERIFIED   | Both fixtures present; check_same_thread=False confirmed          |
| `tests/pipelines/test_research_dedup.py`          | 18 unit tests for RSCH-05 primitives              | VERIFIED   | 18 passed                                                         |
| `tests/contract/test_research_run_cli_mcp.py`     | Registry + CLI/MCP parity contract tests          | VERIFIED   | 8 passed; MCP auto-discovery confirmed                            |
| `pyproject.toml`                                  | langgraph-checkpoint-sqlite>=3.1,<4 dependency    | VERIFIED   | Line 15 confirmed; pin corrected from >=2.0,<3 (API incompatibility) |
| `.gitignore`                                      | .construct/ ignore rule                           | VERIFIED   | Lines 15-16: `.construct/` rule present with explanatory comment  |

---

### Key Link Verification

| From                              | To                                        | Via                              | Status  | Details                                                                  |
|-----------------------------------|-------------------------------------------|----------------------------------|---------|--------------------------------------------------------------------------|
| `research_run.py`                 | `construct.llm.research_score.run_gate`   | `score_and_extract` node         | WIRED   | Imported inside node; `ResearchScoreOutageError` caught before gate      |
| `research_run.py`                 | `construct.pipelines.research_dedup`      | `deduplicate` + `ingest_batch`   | WIRED   | `normalize_url`, `ref_id_for`, `rejected_normalized_urls`, `append_rejected` all called |
| `build_research_run_graph`        | `langgraph.checkpoint.sqlite.SqliteSaver` | `compile(checkpointer=...)`      | WIRED   | `_open_checkpointer` returns `SqliteSaver(conn)`; passed to `build_research_run_graph` |
| `ingest_batch`                    | `ingestion._write_ref_file` + `create_card` | deterministic `ref_id_for` + skip-if-exists | WIRED | Lines 541-555; skip-if-exists on both ref and card paths                |
| `compile_digest`                  | `construct.views.models.DigestRecord`     | `DigestsFile` append + markdown  | WIRED   | Line 615 import confirmed; idempotent record append + `.md` write       |
| `update_seeds_and_log`            | `construct.services.event_log.append_event` | D-11 events                    | WIRED   | Lines 752-789; 4 event types emitted; D-11 set complete                 |
| `research.review` runner          | `langgraph Command(resume=...)`           | `graph.invoke(Command(resume=decisions), cfg)` | WIRED | Line 981; per-finding + approve-all/reject-all                         |
| `catalog.py` shims                | `construct.llm.research_run` runners      | `_research_run/review/inspect_shim` | WIRED | Lines 519-538; lazy import of runners; keyword-only RT-03 guards       |
| `cli.py` commands                 | `registry.get("research.run/review/inspect")` | `get_registry().get(...)` dispatch | WIRED | Lines 608, 655, 674; KeyError guard present                             |
| `mcp/server.py`                   | `research.run/review/inspect` tools       | `registry.list_mcp_tools()` auto-discovery | WIRED | No hardcoded research-run wiring in server.py; auto-discovered          |

---

### Data-Flow Trace (Level 4)

| Artifact          | Data Variable    | Source                             | Produces Real Data | Status    |
|-------------------|------------------|------------------------------------|-------------------|-----------|
| `ingest_batch`    | `gate_queue` / `decisions` | `Command(resume=decisions)` via LangGraph state + `_resolve_decisions` | Yes — from human review input | FLOWING |
| `compile_digest`  | `refs_created`, `cards_created`, `decisions` | `ingest_batch` state output | Yes — actual IDs written by ingest_batch | FLOWING |
| `update_seeds_and_log` | `seeds` + queried clusters | `WorkspaceLoader.load_search_seeds()` live workspace read | Yes — reads real search-seeds.json | FLOWING |
| `deduplicate`     | `existing_urls` + `rejected_urls` | refs/ directory scan + `load_rejected_ledger` | Yes — scans real workspace files | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                         | Command                                                    | Result               | Status |
|--------------------------------------------------|------------------------------------------------------------|----------------------|--------|
| `research.run` capability registered with MCP tool name | `uv run python -c "from construct.capabilities.catalog import create_registry; r=create_registry(); print(r.get('research.run').mcp_tool_name)"` | `construct_research_run` | PASS   |
| `research.review` registered                     | Same as above for `research.review`                        | `construct_research_review` | PASS   |
| `research.inspect` registered                    | Same as above for `research.inspect`                       | `construct_research_inspect` | PASS   |
| `research run --help` exits 0                    | `uv run construct research run --help`                     | Help text shown       | PASS   |
| `research review --help` exits 0                 | `uv run construct research review --help`                  | Help text shown       | PASS   |
| `research inspect --help` exits 0                | `uv run construct research inspect --help`                 | Help text shown       | PASS   |
| `SqliteSaver` importable                         | `uv run python -c "from langgraph.checkpoint.sqlite import SqliteSaver; print('ok')"` | `ok`        | PASS   |
| 21 research_run tests pass                       | `uv run --extra dev pytest tests/llm/test_research_run.py -q --tb=no` | `21 passed in 0.52s` | PASS   |
| 18 research_dedup tests pass                     | `uv run --extra dev pytest tests/pipelines/test_research_dedup.py -q --tb=no` | `18 passed in 0.03s` | PASS   |
| 8 contract tests pass                            | `uv run --extra dev pytest tests/contract/test_research_run_cli_mcp.py -q --tb=no` | `8 passed in 0.41s` | PASS   |

---

### Probe Execution

No `probe-*.sh` scripts found for this phase. Step 7c: SKIPPED (no probe scripts).

---

### Requirements Coverage

| Requirement | Source Plans       | Description                                                                                     | Status    | Evidence                                                             |
|-------------|--------------------|-------------------------------------------------------------------------------------------------|-----------|----------------------------------------------------------------------|
| RSCH-02     | 10-03, 10-04, 10-05 | `research.run` CLI/MCP executes full workflow as one command                                   | SATISFIED | Full workflow node chain + CLI/MCP registration + `test_full_run_offline` passes |
| RSCH-03     | 10-03, 10-04       | Review/approve/reject before any SOT writes                                                     | SATISFIED | interrupt-only `gate_review`; `test_no_writes_before_approval` passes |
| RSCH-04     | 10-03, 10-04       | Resume/inspect paused workflow across process restarts                                          | SATISFIED | SqliteSaver + `_open_checkpointer`; `test_cross_process_resume` + `test_inspect_no_resume` pass |
| RSCH-05     | 10-02, 10-04       | Idempotent rerun for duplicate URLs, refs, rejected findings, partial batches                   | SATISFIED | `ref_id_for` + skip-if-exists + rejected ledger filter; `test_idempotent_rerun` + `test_partial_batch_resume_safe` pass |

**Note:** REQUIREMENTS.md checkboxes for RSCH-02 through RSCH-05 remain `[ ]` (unchecked) and the traceability table still shows them as "Pending." The code implements all four requirements but the requirements document was not updated. This is a documentation gap only — not a code defect.

---

### Anti-Patterns Found

| File                                              | Line    | Pattern                                          | Severity | Impact                                                                               |
|---------------------------------------------------|---------|--------------------------------------------------|----------|--------------------------------------------------------------------------------------|
| `src/construct/llm/research_run.py`              | 95, 104, 115 | `run_id: str` with no `@field_validator` — flows into file path at lines 618/643/682-683 | BLOCKER (CR-01) | Path traversal via MCP surface; write to arbitrary location outside workspace |
| `src/construct/pipelines/research_dedup.py`      | 76      | `assert KEBAB_CASE_PATTERN.fullmatch(ref_id)` (WR-02) | WARNING  | `assert` stripped under `-O`; preceding `re.sub` constrains the value so residual risk is low |
| `src/construct/pipelines/research_dedup.py`      | 153-165 | `append_rejected` unconditionally appends without skip-if-exists (WR-01) | WARNING  | Ledger grows unboundedly on rerun/crash+resume; dedup filtering still works correctly via `set` in `rejected_normalized_urls` |
| `src/construct/llm/research_run.py`              | 962-987 | `review_research_run` does not check `snap.next == ("gate_review",)` before `Command(resume=...)` (WR-05) | WARNING  | Resuming an already-completed run re-triggers `update_seeds_and_log`, appending duplicate D-11 audit events and re-stamping `last_queried` |
| `src/construct/llm/research_run.py`              | 1009-1011 | `inspect_research_run` returns `status="unknown"` for nonexistent run; `_run_result_to_operation` maps `success = status != "failed"` so unknown → success=True (WR-03) | WARNING  | Inspecting a nonexistent run returns a misleading "successful" OperationResult |
| `src/construct/llm/research_run.py`              | 301, 489, 612, 723 | Repeated `import json` inside node bodies (IN-02) | INFO     | Noise; stdlib `json` has no circular-import risk |

---

### Gaps Summary

**One confirmed BLOCKER prevents marking this phase complete:**

**CR-01 (Path Traversal):** The `run_id` field in `ResearchRunInput`, `ReviewInput`, and `InspectInput` accepts arbitrary strings with no format validation. `compile_digest` derives the digest markdown path directly from `run_id` — `digests_dir / f"digest-{run_id}.md"` — with no `resolve()`/containment check. The MCP surface passes `**kwargs` directly into these models, making the vulnerability reachable from any MCP caller. The phase goal states "resume **safely**," and this breaks the safety property at the MCP trust boundary.

The fix is:
1. Add `@field_validator("run_id")` enforcing `KEBAB_CASE_PATTERN` to all three input models
2. Add a `resolve().startswith()` containment check in `compile_digest` (defense-in-depth)

The 4 warnings (WR-01 ledger append non-idempotency, WR-02 assert-based invariant, WR-03 inspect false-success, WR-05 review no gate check) are correctness/robustness concerns but do not prevent the workflow from functioning for legitimate input.

---

### Human Verification Required

None — all 5 success criteria have offline test coverage that passes. The phase has no UI, real-time, or external service behaviors that require human testing.

---

_Verified: 2026-06-28T15:10:21Z_
_Verifier: Claude (gsd-verifier)_
