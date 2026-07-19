# Phase 11: Curation PIPE Steps - Pattern Map

**Mapped:** 2026-06-28
**Files analyzed:** 5 (2 new modules + 2 new test files + 1 edited catalog; CLI edit folded into catalog mirror)
**Analogs found:** 5 / 5 (all exact — Phase 11 is a structural mirror of the shipped Phase 10 `research.run`)

> One sentence orientation for the planner: **every file in this phase has an exact, in-repo analog.** `curation.run` is `research.run` with the human-gate/interrupt removed and the post-gate write nodes replaced by read-only/findings-only steps. Copy the research.run shapes and delete the write/interrupt machinery — do not invent new structure.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/llm/curation_run.py` (NEW) | service / LangGraph workflow module (+ in-module pydantic models `CurationStepResult`, `CurationRunResult`, `CurationRunInput`, `CurationInspectInput`, `CurationRunState`) | batch / event-driven graph (linear, no interrupt) | `src/construct/llm/research_run.py` | exact (sibling) |
| `src/construct/capabilities/catalog.py` (EDIT) | capability registration + RT-03 dual-mode shims + input-model wiring | request-response | `research.run` block (catalog.py:392–422) + `_run_result_to_operation`/`_research_run_shim`/`_research_inspect_shim` (catalog.py:481–539) | exact |
| `src/construct/cli.py` (EDIT) | CLI route (Typer sub-app `curation run` / `curation inspect`) | request-response | `research_app` + `research_run_cmd`/`research_inspect_cmd` (cli.py:402–407, 596–614, 664–681) + `_emit_run_result` (cli.py:583) | exact |
| `tests/llm/test_curation_run.py` (NEW) | test (unit + graph integration) | n/a | `tests/llm/test_research_run.py` | exact (mirror structure + reuse `tests/llm/conftest.py` fixtures) |
| `tests/contract/test_curation_run_cli_mcp.py` (NEW) | test (contract / CLI+MCP parity) | n/a | `tests/contract/test_research_run_cli_mcp.py` | exact |

**Step-source analogs (functions the 5 real nodes wrap — not new files, but the planner references them per node):**

| Curation node | Wraps existing fn | Source | Returns |
|---------------|-------------------|--------|---------|
| `integrity_check` | `validate_workspace(root)` | `src/construct/services/validation.py:106` | `ValidationReport` dataclass (`.errors`, `.warnings`, `.ok`) — **extract primitives, not the object** (Pitfall 4) |
| `decay_scan` (NEW logic) | `WorkspaceLoader.load_cards()` + `DecayConfig` | `storage/workspace.py:147` + `schemas/config.py:162` | new findings-only candidate-ID scan |
| `orphan_scan` (NEW logic) | `load_cards()` + `load_connections()` + `QualityConfig` | `storage/workspace.py:147/119` + `schemas/config.py:169` | new findings-only candidate-ID scan |
| `connection_maintenance` (connection-health) | `bridge_detect(workspace_path)` | `pipelines/bridge_detect.py:52` | `OperationResult`; read `.data["summary"]["totals"]` + `.data["summary"]["l1_l2_only"]` |
| `compile_report` | `graph_status(workspace)` | `pipelines/graph_status.py:12` | `OperationResult`; `.data` = `{cards, connections, domains, workspace}` |

---

## Pattern Assignments

### `src/construct/llm/curation_run.py` (NEW — primary work, mirror `research_run.py`)

**Analog:** `src/construct/llm/research_run.py` (full file). Copy the module skeleton; **strip** the human gate (`gate_review`/`interrupt`), the post-gate write nodes (`ingest_batch`/`compile_digest`/`update_seeds_and_log`), the outage short-circuit (`_route_after_score`/`ResearchScoreOutageError`), and the review/resume runner. Keep the state-TypedDict, in-module models, `_validate_run_id`, `_new_run_id`, `_initial_state`, the per-node `WorkspaceLoader`-rebuild pattern, the checkpointer helper, the graph builder, and the run/inspect runners.

**Imports + run-id guard** (research_run.py:31–65) — copy verbatim, drop the `interrupt` import:
```python
from __future__ import annotations
import logging, secrets, sqlite3
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, field_validator
from construct.schemas.config import KEBAB_CASE_PATTERN
logger = logging.getLogger(__name__)

def _validate_run_id(value: str | None) -> str | None:        # CR-01 trust boundary — copy as-is
    if value is not None and KEBAB_CASE_PATTERN.fullmatch(value) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9] segments joined by single hyphens)")
    return value
```

**State channel — serializable data ONLY** (research_run.py:71–103 pattern; RESEARCH Pattern 1). Use the `steps` accumulator. Note the reducer decision (RESEARCH "State accumulation note"): annotate `steps: Annotated[list[dict], operator.add]` so each node returns `{"steps": [one_result]}`:
```python
import operator
from typing import Annotated
class CurationRunState(TypedDict):
    workspace_path: str
    run_id: str
    # loaded by a load_config-style node (mirror research_run.load_config:225-240)
    decay_window_days: int
    auto_archive_on_decay: bool
    orphan_tolerance_days: int
    steps: Annotated[list[dict], operator.add]   # accumulates CurationStepResult dumps
    status: str          # running | completed | degraded | failed
    events: list[str]
```

**In-module models** (mirror research_run.py:108–175 — models live HERE not catalog.py to avoid the circular-import hazard). Use the D-07/D-08/D-09 shapes from RESEARCH "Code Examples":
```python
class CurationRunInput(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str | None = None
    _check_run_id = field_validator("run_id")(_validate_run_id)   # research_run.py:116

class CurationInspectInput(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str
    _check_run_id = field_validator("run_id")(_validate_run_id)   # research_run.py:139

class CurationStepResult(BaseModel):
    model_config = {"extra": "forbid"}
    step: str
    status: Literal["completed", "skipped", "failed"]   # D-08
    required: bool = True                                # Pitfall 5: deferred nodes set False
    findings: dict = Field(default_factory=dict)
    summary: str = ""
    reason: str | None = None

class CurationRunResult(BaseModel):                       # mirror RunResult research_run.py:155-175
    model_config = {"extra": "forbid"}
    status: Literal["completed", "degraded", "failed"]   # D-09 run aggregate
    run_id: str
    steps: list[CurationStepResult] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    message: str = ""
```

**Per-node `WorkspaceLoader`-rebuild pattern** (research_run.py:225–240, `load_config`) — every node rebuilds the loader locally; NEVER store it in state (Pitfall 3 / Pattern 2):
```python
def load_config(state: CurationRunState) -> dict:
    from construct.storage.workspace import WorkspaceLoader
    gov = WorkspaceLoader(Path(state["workspace_path"])).load_governance()
    return {
        "decay_window_days": gov.decay.decay_window_days,            # D-05, config.py:162
        "auto_archive_on_decay": gov.decay.auto_archive_on_decay,
        "orphan_tolerance_days": gov.quality.orphan_tolerance_days,  # config.py:169
    }
```

**Real-step adapter pattern** (wrap an existing fn, extract primitives into `findings`). `integrity_check` is the canonical "wrap a function, do not store the raw object" case (Pitfall 4 — `ValidationReport` is a dataclass, not JSON-serializable):
```python
def integrity_check(state: CurationRunState) -> dict:
    from construct.services.validation import validate_workspace
    report = validate_workspace(Path(state["workspace_path"]))
    result = CurationStepResult(
        step="integrity_check", status="completed",
        findings={"errors": len(report.errors), "warnings": len(report.warnings),
                  "ok": report.ok, "error_paths": [f.path for f in report.errors]},
        summary=f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)",
    )
    return {"steps": [result.model_dump(mode="json")]}
```
`compile_report` wraps `graph_status(workspace)` (graph_status.py:12 → `.data["cards"]/["connections"]/["domains"]`); `connection_maintenance` wraps `bridge_detect(workspace_path)` (bridge_detect.py:52 → `.data["summary"]["totals"]` = `{confirmed, strong_candidates, ...}`, `.data["summary"]["l1_l2_only"]`). **Connection-health is NOT pure read-only** — `bridge_detect` writes derived `log/bridge-candidates.json` + `views/build/data/bridges.json` (bridge_detect.py:81, `_persist_candidates`); that is allowed under D-06 (derived, not canonical SOT — Pitfall 1).

**New deterministic decay/orphan logic** — see RESEARCH "Decay-scan node" example. Critical load_cards shape note (verified `storage/workspace.py:147-165`): `load_cards()` returns `card.model_dump()` (Python mode, NOT `mode="json"`), so **`created`/`last_verified` come back as `datetime.date` objects and `lifecycle` as a `Lifecycle` enum** — the `card.get("lifecycle") == "archived"` filter must compare against the enum (`Lifecycle.archived`) or coerce, and the date math needs no `date.fromisoformat` when the value is already a `date`. Decay age = `today - (last_verified or created)` (Pitfall 2 / A1). Orphan degree = count of `ConnectionRecord` where card is `from_` OR `to` in `connections.json` (Pitfall 3 / A2; `ConnectionRecord.from_` is aliased `from`, `schemas/workspace.py:51-52`).

**Skip-emitting deferred node** (D-10) — `promotion_review`, `process_inbox`, `views_refresh_hook` (RESEARCH example): `status="skipped", required=False, reason="deferred to Phase 12"`.

**Checkpointer helper** (research_run.py:879–894) — copy verbatim, change only the DB filename to `curation-run.sqlite`. Do NOT use the `from_conn_string` context-manager form (Pitfall 2 / Pattern 3):
```python
def _open_checkpointer(workspace: Path):
    from langgraph.checkpoint.sqlite import SqliteSaver
    db = Path(workspace) / ".construct" / "workflow" / "curation-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    return SqliteSaver(conn), conn
```

**Graph builder** (research_run.py:836–873) — same `StateGraph(...) / add_node / add_edge / compile(checkpointer=...)` shape, but **purely linear, no `add_conditional_edges`, no interrupt node**. Spec §4.3 topology (from CONTEXT/RESEARCH diagram):
`START → integrity_check → decay_scan → orphan_scan → promotion_review(SKIP) → connection_maintenance → process_inbox(SKIP) → compile_report → views_refresh_hook(SKIP) → END`.

**Run-start runner + D-09 aggregation** (mirror research_run.py:900–954 `run_research_run`, but no interrupt/`__interrupt__`/outage branch — the graph runs to completion in one `graph.invoke`). The status roll-up is the genuinely new logic (Pitfall 5 — deferred skips are `required=False` so they never degrade):
```python
def run_curation_run(inp: CurationRunInput) -> CurationRunResult:
    run_id = inp.run_id or _new_run_id()                 # _new_run_id copied from research_run.py:180
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        result = graph.invoke(_initial_state(inp, run_id), {"configurable": {"thread_id": run_id}})
        steps = [CurationStepResult(**s) for s in result["steps"]]
        required_bad = [s for s in steps if s.required and s.status in ("failed", "skipped")]
        status = "degraded" if required_bad else "completed"
        return CurationRunResult(status=status, run_id=run_id, steps=steps,
                                 events=result.get("events", []), message=f"Curation run {status}.")
    finally:
        conn.close()
```

**Inspect runner** (mirror research_run.py:1038–1082 `inspect_research_run`) — re-open checkpointer, `graph.get_state(cfg)`, read persisted terminal state, never re-run. Map a nonexistent run (`not snap.values`) → `status` that the shim treats as `success=False` (WR-03 precedent).

**Terminal event** — emit `curation_cycle_complete` via `append_event(workspace, EventAgent.curator, ...)` (mirror `update_seeds_and_log` research_run.py:786–823; use `EventAgent.curator` per RESEARCH §6.6). Nodes log to stderr via `logging` only — no `print()` (Pitfall 6).

---

### `src/construct/capabilities/catalog.py` (EDIT — register `curation.run` + `curation.inspect`)

**Analog:** the `research.run`/`research.inspect` registration block (catalog.py:392–422) and the shim helpers `_run_result_to_operation` + `_research_run_shim` + `_research_inspect_shim` (catalog.py:481–539).

**Import block** (mirror catalog.py:49–57) — add at top with the other phase imports:
```python
# ── Curation Run imports (Phase 11) ──
from construct.llm.curation_run import (
    CurationInspectInput, CurationRunInput,
    inspect_curation_run, run_curation_run,
)
```

**Registration** (mirror catalog.py:392–422; exact shape from RESEARCH "Capability registration"):
```python
registry.register(CapabilityRecord(
    id="curation.run", name="Curation Run",
    description="Run deterministic curation checks (integrity, decay, orphan, connection-health, report); no canonical writes",
    input_model=CurationRunInput, output_model=OperationResult,
    handler=_curation_run_shim,
    cli_name="curation.run", mcp_tool_name="construct_curation_run",
))
registry.register(CapabilityRecord(
    id="curation.inspect", name="Curation Inspect",
    description="Report a curation run's persisted state (read-only; never re-runs)",
    input_model=CurationInspectInput, output_model=OperationResult,
    handler=_curation_inspect_shim,
    cli_name="curation.inspect", mcp_tool_name="construct_curation_inspect",
))
```

**Shim helper** — mirror `_run_result_to_operation` (catalog.py:481–512) but **simpler**: there is NO `ResearchScoreOutageError` branch in deterministic curation. Keep the generic `except Exception` → sanitized message guard and `success = result.status != "failed"`:
```python
def _curation_result_to_operation(cap_id: str, runner) -> OperationResult:
    try:
        result = runner()
    except Exception as exc:                              # no provider-outage path here
        return OperationResult(success=False, message=f"{cap_id} failed: {type(exc).__name__}",
                               data={"failed": True})
    return OperationResult(success=result.status != "failed",
                           message=result.message or result.status,
                           data=result.model_dump(mode="json"))

def _curation_run_shim(*args, **kwargs):                  # mirror _research_run_shim catalog.py:515-521
    if args:
        raise TypeError("curation.run handler requires keyword arguments")
    return _curation_result_to_operation("curation.run", lambda: run_curation_run(CurationRunInput(**kwargs)))

def _curation_inspect_shim(*args, **kwargs):              # mirror _research_inspect_shim catalog.py:533-539
    if args:
        raise TypeError("curation.inspect handler requires keyword arguments")
    return _curation_result_to_operation("curation.inspect", lambda: inspect_curation_run(CurationInspectInput(**kwargs)))
```

**Leave untouched (D-11):** `_get_workflow_steps("curation-cycle")` placeholder lambdas at catalog.py:653–669 and the `workflow.run` registration (catalog.py:294–307). They coexist; cleanup is Phase 12 / CUR-05. Flag in the plan but do not edit.

---

### `src/construct/cli.py` (EDIT — add `curation` Typer sub-app)

**Analog:** `research_app` definition (cli.py:402–407), `research_run_cmd` (cli.py:596–614), `research_inspect_cmd` (cli.py:664–681), and the shared `_emit_run_result` renderer (cli.py:583–593).

**Sub-app** (mirror cli.py:402–407):
```python
curation_app = typer.Typer(no_args_is_help=True, name="curation",
                           help="Run deterministic curation maintenance checks (read-only).")
app.add_typer(curation_app)
```

**`run` command** (mirror `research_run_cmd` cli.py:596–614 — drop the `--provider` option, keep `--workspace`/`--json`, resolve `curation.run` from the registry, render with `_emit_run_result` which is reused as-is):
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
    _emit_run_result(result, json_output)
```

**`inspect` command** — mirror `research_inspect_cmd` (cli.py:664–681) verbatim with `curation.inspect`, `--run-id`, `_emit_run_result`. NOTE: `_emit_run_result` calls `_render_run_result(result.data)` (cli.py:592) which currently renders the `RunResult` shape (status/run_id/gate_queue/...). The `CurationRunResult` shape differs (steps/events vs gate_queue). Either (a) reuse `_emit_run_result` and let the `--json` path carry full fidelity while the table path renders generic fields, or (b) add a small `_render_curation_result` sibling. Confirm with planner; the contract test only asserts on the `--json` payload so (a) is sufficient for the gate.

---

### `tests/llm/test_curation_run.py` (NEW — mirror `tests/llm/test_research_run.py`)

**Analog:** `tests/llm/test_research_run.py` (full structure) + reuse `tests/llm/conftest.py` fixtures.

**Reuse these existing fixtures** (`tests/llm/conftest.py`): `create_test_workspace` (l167), `write_card` (l181 — supports `lifecycle=`/`created` via frontmatter; **extend to control `created` date** for decay/threshold tests), `test_workspace` (l223), `sqlite_checkpointer` (l237 — factory returning `(saver, conn, db_path)`; **change the hardcoded db filename `research-run.sqlite` reference if a curation-specific fixture is added**, or open a generic tmp DB).

**New fixture needed** (RESEARCH Wave-0): cards with controllable `created`/`last_verified` dates + a `connections.json` with a known orphan (degree-0 card) and a connected card, to exercise decay/orphan thresholds deterministically.

**Test idiom to copy** (test_research_run.py:28–55 `test_full_run_offline`): build the graph directly via `curation_run.build_curation_run_graph(saver)`, call `graph.invoke(curation_run._initial_state(...), {"configurable": {"thread_id": ...}})`, assert on `result["steps"]`. Lazy in-body imports, red until built.

**Sampling points the suite MUST be able to FAIL on** (RESEARCH "Validation Architecture" — map 1:1 to test names): concrete counts/IDs present; `degraded ≠ completed` (inject a required-step failure); deferred nodes visible as `skipped` with reason; thresholds honored (vary governance values); no canonical SOT writes (assert `cards/`/`refs/`/`connections.json`/`search-seeds.json` byte-identical — do NOT assert on `log/`/`views/`, Pitfall 1); no "placeholder" substring in any real step message.

---

### `tests/contract/test_curation_run_cli_mcp.py` (NEW — mirror `tests/contract/test_research_run_cli_mcp.py`)

**Analog:** `tests/contract/test_research_run_cli_mcp.py` (full file, 181 lines).

**Direct-copy test shapes** (rename `research`→`curation`, drop the offline LLM seam since curation is deterministic):
- `_CAPS = {"curation.run": "construct_curation_run", "curation.inspect": "construct_curation_inspect"}` (mirror l27–31).
- `test_*_registered` — `cap.mcp_tool_name == mcp_name`, `cap.cli_name == cap_id` (l93–99).
- `test_shims_reject_positional_args` — `reg.get(cap_id).handler("positional")` raises `TypeError` (l102–106).
- `test_*_in_mcp_tool_list` / `test_mcp_server_exposes_*` — registry auto-discovery (l112–121).
- `test_mcp_server_has_no_hardcoded_curation` — assert `"construct_curation_run"`/`"curation.run"` NOT in `mcp/server.py` source (l124–129; Anti-pattern: do not edit `mcp/server.py`).
- `test_cli_commands_present` — `runner.invoke(app, ["curation", sub, "--help"])` exit 0 (l135–138).
- `test_cli_mcp_result_schema_parity` — CLI `--json` keys == `_serialize_result(handler_result)` keys == `CurationRunResult.model_fields.keys()` (l160–181). **Runs fully offline with no `ANTHROPIC_API_KEY`** (connection-health degrades to L1/L2; RESEARCH Environment Availability).

---

## Shared Patterns

### Run-id trust-boundary validation (CR-01 / V5)
**Source:** `src/construct/llm/research_run.py:52-65` (`_validate_run_id` + `KEBAB_CASE_PATTERN` from `schemas/config.py:14`)
**Apply to:** `CurationRunInput.run_id`, `CurationInspectInput.run_id` (the value becomes the SQLite `thread_id`). Copy `_validate_run_id` and attach via `field_validator` exactly as research_run.py:116/139.

### Persistent SqliteSaver (no connection-string footgun)
**Source:** `src/construct/llm/research_run.py:879-894` (`_open_checkpointer`)
**Apply to:** `run_curation_run`, `inspect_curation_run`. Open `sqlite3.connect(..., check_same_thread=False)`, wrap once, close in `finally`. DB → `.construct/workflow/curation-run.sqlite` (verify `.construct/` gitignore already covers it, as for `research-run.sqlite`).

### RT-03 dual-mode shim + RunResult→OperationResult wrap
**Source:** `src/construct/capabilities/catalog.py:481-539` (`_run_result_to_operation`, `_research_run_shim`, `_research_inspect_shim`)
**Apply to:** `curation.run`, `curation.inspect`. Keyword-only; positional → `TypeError`; `success = status != "failed"`; data = `result.model_dump(mode="json")`. **Drop** the `ResearchScoreOutageError` branch (no provider path in deterministic curation).

### CLI registry-dispatch + JSON/table render
**Source:** `src/construct/cli.py:596-614` (`research_run_cmd`) + `cli.py:583-593` (`_emit_run_result`)
**Apply to:** `curation run` / `curation inspect`. Resolve capability from `get_registry()`, call `cap.handler(**kwargs)`, render via `_emit_run_result` (reusable; confirm table-render field mismatch per the cli.py note above).

### CLI/MCP parity is free (no `mcp/server.py` edit)
**Source:** registration carries `cli_name` + `mcp_tool_name`; MCP auto-discovers from the registry (verified by `test_mcp_server_has_no_hardcoded_research_run`, contract test l124-129).
**Apply to:** all curation capabilities — set both names on the `CapabilityRecord`; never touch `mcp/server.py`.

### Governance threshold loading (no hardcoding — D-05)
**Source:** `WorkspaceLoader.load_governance()` (`storage/workspace.py:107`) → `.decay` (`config.py:162`) / `.quality` (`config.py:169`)
**Apply to:** the `load_config` node feeding `decay_scan`/`orphan_scan`. `decay.decay_window_days`, `decay.auto_archive_on_decay`, `quality.orphan_tolerance_days`.

---

## No Analog Found

None. Every Phase 11 file has an exact in-repo analog. The only **net-new logic** (no analog, build from the RESEARCH examples) is internal to `curation_run.py`:

| Logic | Why no analog | Source to follow |
|-------|---------------|------------------|
| `decay_scan` / `orphan_scan` candidate selection (date math + connection-degree count) | No findings-only deterministic scan exists yet | RESEARCH "Decay-scan node" example + Pitfalls 2/3; load_cards date/enum shape note above |
| Run-level `completed`/`degraded`/`failed` aggregation over per-step statuses | research.run uses interrupt/outage status, not a step roll-up | RESEARCH "Run-start runner + status aggregation" + Pitfall 5 (required vs optional) |
| `CurationStepResult` contract | new D-07 schema | RESEARCH "Code Examples" shape (mirrors `RunResult` discipline, research_run.py:155-175) |

---

## Metadata

**Analog search scope:** `src/construct/llm/`, `src/construct/capabilities/`, `src/construct/pipelines/`, `src/construct/schemas/`, `src/construct/storage/`, `src/construct/cli.py`, `tests/llm/`, `tests/contract/`
**Files read (full or targeted):** `research_run.py` (full), `catalog.py` (imports/registrations/shims/legacy ~310 lines), `graph_status.py` (full), `bridge_detect.py` (entry + summary), `config.py` (Decay/Quality/Governance), `cli.py` (research_app + emit helper), `test_research_run.py` (structure), `test_research_run_cli_mcp.py` (full), `tests/llm/conftest.py` (fixtures), `storage/workspace.py` (loader methods), `schemas/workspace.py` (ConnectionRecord)
**Project instructions:** no `./CLAUDE.md`; no `.claude/skills/` or `.agents/skills/` present
**Pattern extraction date:** 2026-06-28
