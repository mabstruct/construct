---
phase: 11-curation-pipe-steps
reviewed: 2026-06-28T21:17:54Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - src/construct/llm/curation_run.py
  - tests/contract/test_curation_run_cli_mcp.py
  - tests/contract/test_mcp_contracts.py
  - tests/llm/conftest.py
  - tests/llm/test_curation_run.py
  - tests/unit/test_capability_registry.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-28T21:17:54Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 11 replaces the v0.3 curation placeholder no-ops with a real, deterministic
`curation.run`/`curation.inspect` LangGraph pipeline modeled faithfully on the
shipped `research.run`. The implementation is disciplined: state channels carry
only serializable primitives, the `WorkspaceLoader`/sqlite connection are never
stored in state, nodes log to stderr (stdout reserved for MCP JSON-RPC),
`run_id` is kebab-validated at the trust boundary to block path traversal, and
the `test_no_canonical_writes` contract is honored (only derived `log/`+`views/`
artifacts are written by `bridge_detect`). Registry/CLI/MCP wiring follows the
established RT-03 shim discipline and the contract suite proves parity without
editing `mcp/server.py`.

No BLOCKER-class bugs or security vulnerabilities were found. The findings below
are correctness/robustness gaps that surface on non-default call patterns
(reused `run_id`, missing `connections.json`) plus a run/inspect output
divergence and exit-code semantics worth fixing before this is exercised by
automated MCP agents.

There was no `<structural_findings>` block provided, so this report contains only
narrative findings.

## Narrative Findings (AI reviewer)

### Warnings

#### WR-01: Re-invoking `curation.run` with a reused `run_id` duplicates every step

**File:** `src/construct/llm/curation_run.py:83`, `514-549`
**Issue:** `steps` is the only reducer channel — `Annotated[list[dict], operator.add]` —
and the checkpointer is persistent (keyed by workspace DB + `thread_id=run_id`).
`run_curation_run` unconditionally calls `graph.invoke(_initial_state(resolved), cfg)`
with no guard against an already-completed thread. If a caller invokes `curation.run`
twice with the **same** `run_id`, the second `invoke` re-runs the graph from START on a
thread whose `steps` channel already holds 9 entries; the `operator.add` reducer
accumulates, so the result/inspect surface returns ~18 entries — every step duplicated —
and the per-step aggregate is computed over the doubled list. The CLI never triggers this
(it has no `--run-id` flag and always auto-generates), but the MCP tool `construct_curation_run`
advertises `run_id` as an optional input field (`CurationRunInput.run_id`, line 98), so an
agent that passes a stable `run_id` and retries will get corrupted, duplicated output. This
also re-writes the derived `bridge_detect` artifacts and re-appends a second
`curation_cycle_complete` event. `research.run` does not share this exposure because none of
its channels use `operator.add`; the curation `steps` reducer is uniquely vulnerable.
**Fix:** Guard against re-running a completed thread, mirroring the `research.review`
`snap.next` discipline:
```python
graph = build_curation_run_graph(saver)
cfg = {"configurable": {"thread_id": run_id}}
snap = graph.get_state(cfg)
if snap.values and not snap.next:
    # Already completed — return the persisted terminal state, do NOT re-invoke.
    steps = [CurationStepResult(**s) for s in snap.values.get("steps", [])]
    return CurationRunResult(
        status=_aggregate_status(steps), run_id=run_id, steps=steps,
        events=snap.values.get("events", []),
        message="Curation run already completed (idempotent re-run).",
    )
result = graph.invoke(_initial_state(resolved), cfg)
```

#### WR-02: Terminal `curation_cycle_complete` event is never persisted, so `inspect` and `run` disagree

**File:** `src/construct/llm/curation_run.py:537-542`, `577-581`
**Issue:** `run_curation_run` appends the terminal `curation_cycle_complete` event to a
local `events` list **after** `graph.invoke` returns and never writes it back into graph
state. No node ever writes the `events` channel either, so the persisted state's `events`
stays `[]`. Consequently `run_curation_run` returns `events=["curation_cycle_complete"]`
while `inspect_curation_run` on the *same* `run_id` reads `values.get("events", [])` and
returns `events=[]`. The CLI `_render_curation_result` prints the events line, so
`curation run` shows the event and `curation inspect <same-run>` does not — an observable
divergence for identical run handles. (`research.run` avoids this by writing events into
state inside `update_seeds_and_log`.)
**Fix:** Persist the terminal event into the checkpointed state (e.g., have a terminal node
emit it via the state channel, or update the snapshot after invoke) so `inspect` reads the
same `events` the run reported. Minimum: document that `events` is run-only and have
`inspect` reconstruct it, or add the event to the returned state before computing the result.

#### WR-03: `orphan_scan` connection-load fallback catches only `WorkspaceLoadError`, failing the whole step on a missing/unreadable `connections.json`

**File:** `src/construct/llm/curation_run.py:360-366`
**Issue:** The inner `try/except WorkspaceLoadError: pass` is clearly intended to let the
scan degrade gracefully to a degree-0-everywhere fallback when connections cannot be loaded.
But `WorkspaceLoader.read_json` only converts `json.JSONDecodeError` into `WorkspaceLoadError`;
a missing file raises `FileNotFoundError` and a permission error raises `OSError` from
`path.read_text()` — neither is a `WorkspaceLoadError`. Those escape the inner handler, hit
the outer `except Exception`, and turn `orphan_scan` into a `status="failed"` required step,
flipping the entire run to `degraded`. `initialize_workspace` always writes `connections.json`
so this is not hit on fresh workspaces, but deleting/chmod-ing the file produces a degraded
run instead of the intended degree-0 fallback, defeating the purpose of the guard.
**Fix:** Broaden the inner handler to cover the file-access failure modes the fallback is meant
to tolerate:
```python
except (WorkspaceLoadError, FileNotFoundError, OSError):
    pass
```

#### WR-04: A `degraded` run (a FAILED required step) still yields `OperationResult.success=True` and CLI exit code 0

**File:** `src/construct/capabilities/catalog.py:589-593`, `src/construct/llm/curation_run.py:503-511`
**Issue:** `_aggregate_status` never returns `"failed"` for a run — a failed/skipped REQUIRED
step maps to `"degraded"`. `_curation_result_to_operation` then sets
`success = result.status != "failed"`, so a degraded run (e.g., `integrity_check` raised and
became a `failed` required step) returns `success=True`. The CLI `_emit_curation_result` treats
that as the success branch and exits 0. A script or CI job invoking `construct curation run`
and checking the exit code therefore cannot detect that a required curation check actually
failed — the failure is only visible by parsing the per-step table. The per-step status is
honest, but the process-level signal masks a required-step failure.
**Fix:** Map `degraded` to a non-zero exit (or to `success=False`) so automation can detect a
required-step failure, e.g. in `_curation_result_to_operation` set
`success = result.status == "completed"`, or have the CLI exit non-zero on `status == "degraded"`.
If the success-on-degraded behavior is the deliberate D-09 contract, document it explicitly at
the shim and CLI so downstream automation does not assume exit 0 means "all required checks passed."

### Info

#### IN-01: `inspect_curation_run` creates `.construct/workflow/curation-run.sqlite` despite a "no workspace mutation" docstring

**File:** `src/construct/llm/curation_run.py:202-216`, `552-562`
**Issue:** `inspect_curation_run`'s docstring states "Performs no workspace mutation," but it
calls `_open_checkpointer`, which runs `db.parent.mkdir(parents=True, exist_ok=True)` and
`sqlite3.connect(...)`, creating the `.construct/workflow/` directory and an (empty)
`curation-run.sqlite` file when inspecting a workspace that has never run curation. This is a
derived/non-canonical artifact, so `test_inspect_no_rerun` (which snapshots only canonical
artifacts) still passes, but the read-only claim is inaccurate.
**Fix:** Reword the docstring to "no canonical SOT mutation; may create the derived checkpoint
DB," or open the connection read-only / short-circuit when the DB file does not yet exist.

#### IN-02: `_validate_run_id` docstring overstates the path-traversal surface

**File:** `src/construct/llm/curation_run.py:53-66`
**Issue:** The docstring claims `run_id` "influences the checkpoint DB path." In this module the
DB path is the fixed `.construct/workflow/curation-run.sqlite` and `run_id` is used only as the
LangGraph `thread_id` (stored inside sqlite, never as a filesystem path component). The kebab
validation is still correct and worth keeping as defense-in-depth, but the stated rationale does
not match the curation code path (it was accurate for `research.run`, where `run_id` is
interpolated into `digest-{run_id}.md`).
**Fix:** Adjust the docstring to describe the actual curation surface (`thread_id`) so future
maintainers do not assume a path-injection vector that does not exist here.

---

_Reviewed: 2026-06-28T21:17:54Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
