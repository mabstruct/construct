# Phase 13: Daily-Cycle Composition - Pattern Map

**Mapped:** 2026-07-06
**Files analyzed:** 4 (2 new, 2 modified) + 1 new test
**Analogs found:** 5 / 5 (all exact — this is a "clone the curation quartet" phase)

All line numbers below were re-verified against the live source this session. Where the
research doc's numbers were slightly off, the corrected ranges are noted inline.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/llm/daily_run.py` (NEW) | service (workflow composition module) | orchestration / request-response | `src/construct/llm/curation_run.py` (+ `research_run.py`) | exact (role + flow) |
| `src/construct/capabilities/catalog.py` (MODIFY) | config (capability registration) | request-response (shim wrappers) | curation.run/inspect records + shims in same file | exact (same file, same pattern) |
| `src/construct/cli.py` (MODIFY) | route (Typer sub-app) | request-response | `curation` sub-app in same file | exact (same file, same pattern) |
| `tests/contract/test_daily_run_cli_mcp.py` (NEW) | test (contract/parity) | request-response | `tests/contract/test_curation_run_cli_mcp.py` | exact (verbatim clone) |

**Supporting reads (unchanged, consumed by daily_run.py):**
- `src/construct/pipelines/graph_status.py` — `graph_status()` returns the closing health summary.
- `src/construct/services/event_log.py` — `append_event()` (audit trail; **fired by children, NOT by daily_run**).

---

## Pattern Assignments

### `src/construct/llm/daily_run.py` (NEW — composition service)

**Primary analog:** `src/construct/llm/curation_run.py`
**Secondary analog:** `src/construct/llm/research_run.py`

This module owns the I/O models, the `DailyRunResult` surface, `_aggregate_daily_status`,
`run_daily_run`, and `inspect_daily_run`. It defines models **in this module, not catalog.py**
(circular-import discipline — see `curation_run.py` L118 comment).

**A. `_validate_run_id` kebab guard — reuse verbatim** (`curation_run.py` L61-74):
```python
def _validate_run_id(value: str | None) -> str | None:
    if value is not None and KEBAB_CASE_PATTERN.fullmatch(value) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9] segments joined by single hyphens)")
    return value
```
`daily_run.py` should import/reuse this same guard (or `KEBAB_CASE_PATTERN`). **Security-critical**:
the `run_id` becomes the `.construct/workflow/daily/<run_id>.json` receipt path (V5 / path-traversal).

**B. Input models — mirror `CurationRunInput` / `CurationInspectInput`** (`curation_run.py` L121-138):
```python
class CurationRunInput(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str | None = None
    _check_run_id = field_validator("run_id")(_validate_run_id)

class CurationInspectInput(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str
    _check_run_id = field_validator("run_id")(_validate_run_id)
```
`DailyRunInput` mirrors `CurationRunInput` (optional `run_id`); `DailyInspectInput` mirrors
`CurationInspectInput` (required `run_id`). Same `extra="forbid"` + validator.

**C. `_new_run_id` — mirror** (`curation_run.py` L214-222). Change the prefix `cur-` → `daily-`;
the `-%H%M%S` (dash, not ISO `T`) is what keeps it kebab-valid:
```python
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
return f"cur-{stamp}-{secrets.token_hex(3)}"   # → f"daily-{stamp}-{secrets.token_hex(3)}"
```
Per RESEARCH Composition Flow, give each child a derived id: `f"{run_id}-research"`,
`f"{run_id}-curation"` (both kebab-safe, addressable by later child `review`/`inspect`).

**D. Result surface — mirror `CurationRunResult`** (`curation_run.py` L195-208):
```python
class CurationRunResult(BaseModel):
    model_config = {"extra": "forbid"}
    status: Literal["completed", "degraded", "failed", "awaiting_review"]
    run_id: str
    gate_id: str | None = None
    gate_queue: list[dict] = Field(default_factory=list)
    steps: list[CurationStepResult] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    message: str = ""
```
`DailyRunResult` parent status enum is `Literal["completed", "degraded", "failed"]` (no
`awaiting_review` at parent — D-01 never pauses). Fields per RESEARCH L191-198: `status`,
`run_id`, `children: list[DailyChildStatus]`, `pending_escalations: int`, `graph_health: dict`,
`message`. Keep `model_config = {"extra": "forbid"}`.

**E. Status aggregation — mirror `_aggregate_status`** (`curation_run.py` L1056-1068):
```python
def _aggregate_status(steps: list[CurationStepResult]) -> str:
    required_bad = [s for s in steps if s.required and s.status in ("failed", "skipped")]
    return "degraded" if required_bad else "completed"
```
`_aggregate_daily_status(children, pending_escalations)` (DAY-03 "no false completed"):
`failed` only if ALL children failed; `degraded` if any child is failed/degraded/awaiting_review
OR `pending_escalations > 0`; else `completed`. Full target shape in RESEARCH L200-207.

**F. Runner shape — mirror `run_curation_run`** (`curation_run.py` L1071-1114). Note the
pattern of `run_id = inp.run_id or _new_run_id()` then folding a typed result. **Departure:**
`daily_run` has NO checkpointer/graph — it is thin composition (three `try/except` calls + fold).
The `run_research_run` pause-detect branch (`research_run.py` L900-954) is the shape for
"call child, branch on `status == 'awaiting_review'` → call `review_*_run(approve_all=True)`".

**G. Failure sanitization — reuse `_sanitize_error`** (`curation_run.py` L296-305) for any
caught child exception detail (never raw provider text):
```python
def _sanitize_error(exc: Exception) -> str:
    text = str(exc).strip()
    first = text.splitlines()[0] if text else ""
    return f"{type(exc).__name__}: {first}" if first else type(exc).__name__
```

**H. Child entrypoints to CALL (do NOT modify — D-09):**
| Function | File:Line | Signature → Returns |
|----------|-----------|---------------------|
| `run_research_run` | `research_run.py` L900 | `(ResearchRunInput) -> RunResult` |
| `review_research_run` | `research_run.py` L996 | `(ReviewInput) -> RunResult` |
| `inspect_research_run` | `research_run.py` L1038 | `(InspectInput) -> RunResult` |
| `run_curation_run` | `curation_run.py` L1071 | `(CurationRunInput) -> CurationRunResult` |
| `review_curation_run` | `curation_run.py` L1134 | `(CurationReviewInput) -> CurationRunResult` |
| `inspect_curation_run` | `curation_run.py` L1182 | `(CurationInspectInput) -> CurationRunResult` |
| `graph_status` | `pipelines/graph_status.py` L12 | `(str \| Path) -> OperationResult` (`.data` = health summary) |

**I. Auto-apply mechanism (D-02/D-03) — reuse child `approve_all`, do NOT rebuild.**
Curation `_build_resume_decisions` (`curation_run.py` L1117-1131) reproduces the recommended
per-item decision; the apply node enforces escalate-exclusion by construction
(`apply_promotions`, `curation_run.py` L855-859):
```python
# escalate is review-only this phase — record outcome, NO write (Open-Q 3).
if kind == "escalate" or decision == "escalate":
    escalated.append(card_id)
    events.append(_emit(workspace, "gate_review_rejected", card_id, "escalated (review-only)"))
    continue
```
Research `_build_resume_decisions` (`research_run.py` L979-993) has no escalate kind.
**`daily_run` calls `review_*_run(approve_all=True)`; it writes no gate logic and no events.**

**J. Pending-escalation count — capture BEFORE resume** (Pitfall 5): the count comes from the
`awaiting_review` curation result's `gate_queue` (which is `[]` after resume):
```python
pending_escalations = sum(1 for p in c.gate_queue if p.get("kind") == "escalate")
```

**K. `graph_health` source** (`graph_status.py` L52-73): use `graph_status(ws).data` which is
`{"cards": {...}, "connections": {...}, "domains": {...}, "workspace": "..."}`.

**L. `daily.inspect` persistence:** thin composition has no LangGraph checkpoint, so `run_daily_run`
must persist the `DailyRunResult` JSON to `.construct/workflow/daily/<run_id>.json`;
`inspect_daily_run` reads it back. Missing file → `status="failed"`, `message="No such daily run."`
mirroring `inspect_curation_run`'s no-such-run branch (`curation_run.py` L1213-1217).

**M. Diagnostics:** `logging` to stderr only — NEVER `print()` (stdout is MCP JSON-RPC transport).
`event_log.append_event` (`event_log.py` L13-41) is fired by the CHILDREN's apply nodes via
`_emit` (`curation_run.py` L308-324); `daily_run` emits nothing itself (avoids double-logging).

---

### `src/construct/capabilities/catalog.py` (MODIFY — registration + shims)

**Analog:** the curation.run/curation.inspect records + shims **in this same file**.

**A. Import block** — add a `# ── Daily Run imports (Phase 13) ──` block mirroring the curation
import block (L59-67):
```python
# ── Curation Run imports (Phase 11) ──
from construct.llm.curation_run import (
    CurationInspectInput,
    CurationReviewInput,
    CurationRunInput,
    inspect_curation_run,
    review_curation_run,
    run_curation_run,
)
```
Add: `from construct.llm.daily_run import (DailyInspectInput, DailyRunInput, inspect_daily_run, run_daily_run)`.

**B. CapabilityRecords** — mirror curation.run/curation.inspect (L433-452, in the registration
function). **Add only `daily.run` + `daily.inspect` — NO `daily.review` (D-01 never pauses).**
```python
registry.register(CapabilityRecord(
    id="curation.run",
    name="Curation Run",
    description="Run deterministic curation checks (integrity, decay, orphan, connection-health, report); findings-only, no canonical writes",
    input_model=CurationRunInput,
    output_model=OperationResult,
    handler=_curation_run_shim,
    cli_name="curation.run",
    mcp_tool_name="construct_curation_run",
))
```
New records use `cli_name="daily.run"` / `mcp_tool_name="construct_daily_run"` and
`cli_name="daily.inspect"` / `mcp_tool_name="construct_daily_inspect"` (RESEARCH L233-247).
**`output_model=OperationResult`** (the shim wraps `DailyRunResult` into `OperationResult`).

**C. Shim wrappers** — clone `_curation_result_to_operation` (L594-615) + `_curation_run_shim`
(L618-624). The **positional-arg guard is load-bearing** (`test_shims_reject_positional_args`),
and `success = result.status != "failed"` encodes the **degraded-exits-0 contract** (Phase 11):
```python
def _curation_result_to_operation(cap_id: str, runner) -> OperationResult:
    try:
        result = runner()
    except Exception as exc:
        return OperationResult(
            success=False,
            message=f"{cap_id} failed: {type(exc).__name__}",
            data={"failed": True},
        )
    return OperationResult(
        success=result.status != "failed",   # degraded → success=True → exit 0
        message=result.message or result.status,
        data=result.model_dump(mode="json"),
    )

def _curation_run_shim(*args, **kwargs):
    if args:
        raise TypeError("curation.run handler requires keyword arguments")
    return _curation_result_to_operation(
        "curation.run", lambda: run_curation_run(CurationRunInput(**kwargs))
    )
```
Clone as `_daily_result_to_operation`, `_daily_run_shim` (→ `run_daily_run(DailyRunInput(**kwargs))`),
`_daily_inspect_shim` (→ `inspect_daily_run(DailyInspectInput(**kwargs))`).

**D. DO NOT** revive `workflow.run` (removed — see the L311-315 comment block in this file) and
DO NOT define I/O models here (circular import).

---

### `src/construct/cli.py` (MODIFY — `daily` Typer sub-app)

**Analog:** the `curation` sub-app in this same file.

**A. Sub-app declaration** — mirror `curation_app` (L368-373):
```python
curation_app = typer.Typer(
    no_args_is_help=True,
    name="curation",
    help="Run deterministic curation maintenance checks (read-only).",
)
app.add_typer(curation_app)
```
Add `daily_app` with `name="daily"`, help per RESEARCH L268-269.

**B. Render/emit helpers** — mirror `_render_curation_result` (L654-671) + `_emit_curation_result`
(L674-685). The daily renderer should print parent `status`/`run_id`, a per-child line, the
`pending_escalations` count, and a graph-health line:
```python
def _emit_curation_result(result: OperationResult, json_output: bool) -> None:
    if json_output:
        _display_result(result, json_output=True)
        return
    if not result.success:
        _display_result(result, json_output=False)
        return
    if result.data:
        _render_curation_result(result.data)
    typer.echo(f"✓ {result.message}")
```

**C. Commands** — `daily run` mirrors `curation_run_cmd` (L688-701); `daily inspect` mirrors
`curation_inspect_cmd` (L704-718). **Do NOT add a `review` command** (D-01, no parent pause):
```python
@curation_app.command(name="run")
def curation_run_cmd(
    workspace: Path = typer.Option(..., "--workspace", "-w", help="CONSTRUCT workspace path"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    try:
        cap = get_registry().get("curation.run")
    except KeyError:
        typer.echo("ERROR: Capability 'curation.run' not found. Ensure Phase 11 is complete.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace_path=str(workspace))
    _emit_curation_result(result, json_output)
```
`daily inspect` passes `run_id=run_id` (required `--run-id` option, as `curation_inspect_cmd` L707).

---

### `tests/contract/test_daily_run_cli_mcp.py` (NEW — contract/parity)

**Analog:** `tests/contract/test_curation_run_cli_mcp.py` (verbatim clone, 145 lines).

Clone every test, retargeting `curation` → `daily`. `_CAPS` becomes
`{"daily.run": "construct_daily_run", "daily.inspect": "construct_daily_inspect"}`.

**Tests to clone (with source line refs):**
- `test_registered` (L47-53) — input_model set, `mcp_tool_name`/`cli_name` correct.
- `test_shims_reject_positional_args` (L56-60) — asserts the shim `*args` guard.
- `test_in_mcp_tool_list` (L66-68) + `test_mcp_server_exposes_curation` (L71-75) → `..._daily`.
- **`test_mcp_no_hardcoded_curation` (L78-84) → `test_mcp_no_hardcoded_daily`** — the API-02 guard;
  assert `"construct_daily_run"` and `"daily.run"` do NOT appear in `mcp_server.__file__` source:
  ```python
  def test_mcp_no_hardcoded_curation() -> None:
      src = Path(mcp_server.__file__).read_text(encoding="utf-8")
      assert "construct_curation_run" not in src
      assert "curation.run" not in src
  ```
- `test_cli_commands_present` (L90-96) → assert `daily run --help` / `daily inspect --help` exit 0.
- **`test_cli_mcp_schema_parity` (L120-144)** — the API-03 proof. Clone the offline-degrade pattern
  (`monkeypatch.delenv("ANTHROPIC_API_KEY")`), assert CLI `--json` keys == `_serialize_result(...)`
  keys == `DailyRunResult.model_fields.keys()`:
  ```python
  assert set(cli_payload.keys()) == set(mcp_serialized.keys())
  assert set(cli_payload["data"].keys()) == set(mcp_serialized["data"].keys())
  assert set(cli_payload["data"].keys()) == set(CurationRunResult.model_fields.keys())
  ```
- Reuse `from tests.llm.conftest import create_test_workspace` (test L26). For the composition
  happy path, RESEARCH points to the mock search provider + `build_chat_model` monkeypatch seam
  (`tests/llm/conftest.py` L156, `create_test_workspace` L169).

**Do NOT clone** `test_no_placeholder_curation_path` (curation-specific); do NOT add a `review`
command to `test_cli_commands_present`.

---

## Shared Patterns

### Positional-arg shim guard (API-02 discipline)
**Source:** `catalog.py` L620-621 (`_curation_run_shim`)
**Apply to:** every daily shim (`_daily_run_shim`, `_daily_inspect_shim`)
```python
if args:
    raise TypeError("daily.run handler requires keyword arguments")
```
Asserted by `test_shims_reject_positional_args`.

### Degraded-exits-0 exit-code contract (Phase 11 carry-forward)
**Source:** `catalog.py` L611-614 (`_curation_result_to_operation`)
**Apply to:** `_daily_result_to_operation`
```python
return OperationResult(success=result.status != "failed", ...)  # degraded → True → exit 0
```
Only a hard `failed` maps to `success=False`. (See MEMORY "Curation exit-code contract".)

### run_id kebab validation (V5 / path-traversal — Input Validation)
**Source:** `curation_run.py` L61-74 (`_validate_run_id`)
**Apply to:** `DailyRunInput`, `DailyInspectInput` — MUST run before any `.construct/workflow/daily/<run_id>.json` path join.

### Failure sanitization (Information Disclosure)
**Source:** `curation_run.py` L296-305 (`_sanitize_error`) + `catalog.py` L608 (`type(exc).__name__` in shim)
**Apply to:** any caught child exception in `daily_run.py` and the daily shim.

### Audit trail — inherited, not re-emitted (D-04)
**Source:** children's `_emit` → `append_event` (`curation_run.py` L308-324; `event_log.py` L13-41)
**Apply to:** `daily_run.py` emits NO events itself — the children fire the full
`gate_review_approved`/`gate_review_rejected` + `workflow_step_complete` trail on auto-apply.

### MCP parity is free — never edit `mcp/server.py`
**Source:** registry auto-discovery (`mcp/server.py` L23-28 iterates `list_mcp_tools()`)
**Apply to:** all daily records. Guarded by `test_mcp_no_hardcoded_daily`.

---

## No Analog Found

None. Every new/modified file has an exact in-tree analog (this is a "clone the curation quartet"
composition phase). The only genuinely new logic — `_aggregate_daily_status`, the three-child
`try/except` fold, and the `.construct/workflow/daily/<run_id>.json` receipt — are close mirrors
of `_aggregate_status`, `run_curation_run`'s fold, and `inspect_curation_run`'s no-such-run branch
respectively (all cited above).

---

## Metadata

**Analog search scope:** `src/construct/llm/`, `src/construct/capabilities/`, `src/construct/cli.py`,
`src/construct/pipelines/`, `src/construct/services/`, `tests/contract/`.
**Files scanned/read:** curation_run.py, research_run.py, catalog.py, cli.py, graph_status.py,
event_log.py, test_curation_run_cli_mcp.py (7 analog files, all line numbers re-verified live).
**Verified drift vs RESEARCH:** curation shim `_curation_result_to_operation` is L594-615 (research
said L594-624; the `_curation_run_shim` starts L618) — no functional impact. Records confirmed at
L433-452; research/curation records span L400-462.
**Pattern extraction date:** 2026-07-06
</content>
</invoke>
