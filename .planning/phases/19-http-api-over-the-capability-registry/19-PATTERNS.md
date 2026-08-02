# Phase 19: HTTP API over the Capability Registry - Pattern Map

**Mapped:** 2026-08-02
**Files analyzed:** 15 (5 new source, 4 modified source, 5 new/modified tests, 1 doc artifact)
**Analogs found:** 14 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/api/app.py` (NEW) | adapter / route module | request-response | `src/construct/mcp/server.py` | role-match (both are generated-from-registry surfaces; HTTP is sync ASGI vs stdio) |
| `src/construct/api/middleware.py` (NEW) | middleware | request-response | *none in repo* | **no analog** — first ASGI middleware in the codebase |
| `src/construct/api/errors.py` (NEW) | error boundary / serializer | transform | `src/construct/mcp/server.py::_serialize_result` + `src/construct/capabilities/errors.py` | exact (this *is* the shared boundary both surfaces must use) |
| `src/construct/api/runs.py` (NEW) | service (process spawn) | event-driven / batch | `tests/integration/test_surface_parity.py::_cli` (subprocess idiom) + `llm/curation_run.py::_new_run_id` | partial (subprocess launch exists only in tests today) |
| `src/construct/capabilities/workspaces.py` (NEW) | utility / validator+resolver | transform | `src/construct/llm/curation_run.py::_validate_run_id` + `src/construct/views/lib/discover.py` | exact (both halves already written, in two places) |
| `src/construct/capabilities/registry.py` (MOD) | seam | request-response | itself — `invoke()` lines 47–82 | exact |
| `src/construct/capabilities/errors.py` (MOD) | error model | transform | itself — `from_validation_error` lines 50–85 | exact |
| `src/construct/capabilities/catalog.py` (MOD — `workflow.list`) | model + registration | CRUD (read) | `WorkflowStatusInput` (:268) + its `registry.register` block (:491) | exact |
| `src/construct/cli.py` (MOD — `serve`) | CLI command | request-response | `cli.py::mcp` (:119-126) for the server-launch shape; `cli.py::validate` (:1007-1042) for the `install_root or Path.cwd()` idiom | exact |
| `src/construct/llm/curation_run.py` (MOD — `_open_checkpointer`) | storage/connection | file-I/O | itself — `:494-508`; twin at `llm/research_run.py:1034-1048` | exact |
| `src/construct/pipelines/graph_status.py` (MOD — `:66` path leak) | pipeline | transform | `cli.py::validate:1048-1061` (the "local caller appends the path" convention) | role-match |
| `tests/contract/test_http_surface.py` (NEW) | contract test | request-response | `tests/contract/test_capability_seam.py` (cardinality guards, :77-119) | exact |
| `tests/contract/test_http_security.py` (NEW) | contract test | request-response | `tests/contract/test_capability_seam.py` (structure) | role-match |
| `tests/integration/test_surface_parity.py` (MOD — 3rd column) | differential test | request-response | itself — `ParityCase` (:35-59), `_cli` (:161), `_mcp` (:187) | exact |
| `.planning/phases/19-*/COVERAGE.md` (NEW) | doc artifact | — | none | **no analog** (intentional — new artifact class) |

---

## Pattern Assignments

### `src/construct/api/app.py` (adapter, request-response)

**Analog:** `src/construct/mcp/server.py` (71 lines — the whole-surface-from-registry proof)

**Imports pattern** (`mcp/server.py:1-11`):
```python
"""MCP stdio server with tools auto-registered from the capability registry."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from construct.capabilities.catalog import get_registry
from construct.services.knowledge import OperationResult
```
Copy: `from __future__ import annotations` first line after docstring (universal in this repo), absolute `construct.*` imports, no path aliases.

**Factory pattern to copy** (`mcp/server.py:42-71`):
```python
def create_server() -> FastMCP:
    app = FastMCP("construct")

    registry = get_registry()
    for entry in registry.list_mcp_tools():
        ...
    return app


def run_server() -> None:
    """Entry point for `construct mcp` — runs until stdin closes."""
    app = create_server()
    app.run(transport="stdio")
```
HTTP equivalent: `create_app(install_root: Path, token: str) -> FastAPI` + the CLI calls `uvicorn.run(app_instance, ...)`. **Deviate on one point:** do NOT copy the `registry.list_mcp_tools()` loop — RESEARCH measured 6 capabilities with no `mcp_tool_name`. Iterate `registry.list()` (`registry.py:84-85`) instead. Under D-05 there is no loop at all in `app.py`; the registry is iterated only in `GET /api/capabilities`.

**Dispatch pattern to copy** (`mcp/server.py:49-57`) — including the defect to NOT copy:
```python
def handler(**kwargs: Any) -> str:
    try:
        result = registry.invoke(capability.id, kwargs)
        serialized = _serialize_result(result)
        return json.dumps(serialized, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})   # ← M-4: the last unguarded str(exc). DO NOT COPY.
```
The HTTP route keeps `registry.invoke(...) → _serialize_result(...)` and replaces the `except Exception` arm with typed handling through `api/errors.py`.

---

### `src/construct/api/errors.py` (error boundary, transform)

**Analog A — serializer:** `src/construct/mcp/server.py:14-39`

```python
def _serialize_result(result: Any) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
    if isinstance(result, (list, tuple)):
        return {"items": [str(item) for item in result]}
    return {"result": str(result)}
```
Its docstring records the reasoning HTTP inherits verbatim: *"`json.dumps` is deliberately left without a `default=` fallback: coercing an unexpected value with `str()` would put filesystem paths into a string rendered straight back to an MCP client (T-18-10)"*. **Move this function to the shared boundary and have `mcp/server.py` import it** — A7 in RESEARCH assumes sharing; the move is what makes the sharing real rather than a copy.

**Analog B — reason-string construction:** `src/construct/capabilities/errors.py:50-85`
```python
errors = list(
    exc.errors(include_url=False, include_input=False, include_context=False)
)
if model is not None:
    errors.sort(key=_error_order_key(model))
parts = [
    f"{'.'.join(str(item) for item in error['loc']) or '<root>'}: {error['msg']}"
    for error in errors
]
return cls(cap_id, "; ".join(parts))
```
The FastAPI `RequestValidationError` handler must build its string this way (or call this classmethod) — never `exc.body` / `exc.errors()` with `input`. D-08's change: `model: Optional[type[BaseModel]] = None` (`errors.py:55`) becomes required, and the `if model is not None:` branch at `:79` becomes unconditional.

**Error-class pattern for any new typed error** (`errors.py:31-48`):
```python
class CapabilityNotFoundError(CapabilityError):
    """Raised when a capability id is not present in the registry."""

    def __init__(self, cap_id: str, available: Sequence[str]) -> None:
        self.cap_id = cap_id
        self.available: tuple[str, ...] = tuple(available)
        super().__init__(
            f"Capability '{cap_id}' not found. Available: {', '.join(self.available)}"
        )
```
Note the module docstring's rule: these subclass `Exception`, **not** `ValueError` — a documented exception to AGENTS.md § Error Handling. Any new seam error follows it.

---

### `src/construct/capabilities/workspaces.py` (utility, transform)

**Analog A — the shape gate:** `src/construct/llm/curation_run.py:79-95` (`_validate_run_id`)
```python
def _validate_run_id(value: str | None) -> str | None:
    """Reject any ``run_id`` that is not kebab-case (CR-01 / T-11-01 guard).

    ``run_id`` becomes the LangGraph ``thread_id`` and influences the checkpoint
    DB path. The MCP/CLI shims pass caller-supplied ``**kwargs`` straight into the
    input models, so an unvalidated value such as ``"../../../tmp/evil"`` would ...
```
Copy the pattern *and* the docstring convention: state the threat and the sink, not just the rule. `resolve_workspace_id` has the identical threat statement with `install_root` as the sink.

**Analog B — the allowlist gate:** `src/construct/views/lib/discover.py:16-38` (read whole, 38 lines)
```python
def discover_workspaces(install_root: Path) -> list[Path]:
    """Return sorted list of workspace directory Paths."""
    workspaces = []
    for entry in sorted(install_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.name in EXCLUDED_NAMES:
            continue
        if _is_workspace(entry):
            workspaces.append(entry)
    return workspaces
```
Call it — do not reimplement (D-02 locked; `EXCLUDED_NAMES` and `_is_workspace` are already written). Note `install_root.iterdir()` is filesystem contact, which is why the shape gate must run first.

---

### `src/construct/capabilities/registry.py` (seam, request-response) — MODIFIED

**Analog:** itself. `invoke()` at `:47-82`:
```python
    try:
        cap = self.get(cap_id)
    except KeyError as exc:
        raise CapabilityNotFoundError(cap_id, sorted(self._capabilities)) from exc

    # ← D-01's workspace_id resolution inserts HERE (between resolve and validate)

    try:
        model = cap.input_model.model_validate(payload)
    except ValidationError as exc:
        raise CapabilityInputError.from_validation_error(
            cap_id, exc, cap.input_model
        ) from exc

    return cap.handler(**model.model_dump())
```
**Constraint carried in the docstring at `:61-64`** — quote it in the plan, because D-01 brushes against it:
> *"There is deliberately no strict/lenient flag, no allowlist argument, and no per-surface exception (D-05): a knob here would let one surface diverge from another, which is the fork this seam exists to prevent."*

D-01 adds *behaviour applied to all surfaces uniformly*, not a knob. `install_root` must therefore be constructor/module state or derived, never an `invoke()` keyword that HTTP passes and CLI does not — that would be exactly the knob the docstring forbids. Record how it is threaded as a named decision. `test_surface_parity.py:320 test_seam_has_no_leniency_knob` already guards the signature.

---

### `src/construct/capabilities/catalog.py` — `workflow.list` (model + registration, CRUD read)

**Analog:** `WorkflowStatusInput` and its registration — the closest sibling (same workspace field type, same output model).

**Input model pattern** (`catalog.py:268-273`):
```python
class WorkflowStatusInput(BaseModel):
    """Input for ``workflow.status`` — one workspace, which is all its handler takes."""

    model_config = ConfigDict(extra="forbid")

    workspace: Path
```
`extra="forbid"` is mandatory — `test_capability_seam.py:87` asserts cardinality over the whole registry.

**Registration pattern** (`catalog.py:491-499`):
```python
    registry.register(CapabilityRecord(
        id="workflow.status",
        name="Workflow Status",
        description="Check active workflow status",
        input_model=WorkflowStatusInput,
        output_model=OperationResult,
        handler=lambda workspace: WorkflowRunner(workspace).status(),
        cli_name="workflow.status",
    ))
```
Note `mcp_tool_name` is absent here — deliberate for `workflow.status`. For `workflow.list`, decide it explicitly; omitting it removes it from the MCP surface while HTTP still reaches it via `registry.list()`.

**Six guards trip on registration** (RESEARCH Pattern 7): `test_capability_seam.py:84` (REGISTRY_SIZE 29→30), `:87` (forbid cardinality), `:138` (`signature.bind`), `test_mcp_contracts.py:102` (`_payload_for` — a miss is a bare `KeyError`), `test_doc_command_references.py`, plus this phase's new HTTP coverage guard.

---

### `src/construct/cli.py` — `serve` (CLI command, request-response)

**Analog A — server-launch command:** `cli.py:119-126`
```python
@app.command()
def mcp() -> None:
    """Start the MCP stdio server for agentic tool invocation.

    Runs until stdin is closed. Tools are auto-registered from the
    capability registry — no manual wiring needed.
    """
    run_server()
```
Keep the body this thin: `serve` should call an `api` entry point, not build the app inline.

**Analog B — install_root idiom + error rendering:** `cli.py:1007-1061`
```python
    install_root: Path | None = typer.Option(None, "--install-root"),
    ...
    install_root = install_root or Path.cwd()   # resolved at call time, not import time (WR-09)
    ...
        typer.secho(f"ERROR: {reason} (at {install_root})", fg=typer.colors.RED)
        raise typer.Exit(code=1)
```
The port-collision message (D-04's obligation) copies this exact rendering: `typer.secho("ERROR: ...", fg=typer.colors.RED)` then `raise typer.Exit(code=1)` — **not** uvicorn's `SystemExit(3)`.

**Seam-error rendering convention** (`cli.py:103-107`, repeated at 26 call sites):
```python
    try:
        items = get_registry().invoke("workspace.status", {"path": path})
    except (CapabilityInputError, CapabilityNotFoundError) as exc:
        typer.echo(f"ERROR {exc}")
        raise typer.Exit(code=1) from exc
```
`test_surface_parity.py:237 _cli_reason` parses exactly the `"ERROR "` prefix — do not change the framing.

---

### `src/construct/llm/curation_run.py::_open_checkpointer` (storage, file-I/O) — MODIFIED

**Analog:** itself, `:494-508` (twin at `research_run.py:1034-1048` — **both must change**):
```python
def _open_checkpointer(workspace: Path):
    """Open a persistent ``SqliteSaver`` under ``.construct/`` (caller closes conn).

    Returns ``(saver, conn)``. The connection is kept alive for the whole handler
    and closed in the caller's ``finally`` — never wrapped in a transient
    connection-string context manager (Pitfall 2: that closes the connection on
    block exit and breaks cross-process resume). ``check_same_thread=False`` is
    required because LangGraph may touch the checkpointer across threads.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    db = Path(workspace) / ".construct" / "workflow" / "curation-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    return SqliteSaver(conn), conn
```
The change is `timeout=` on `sqlite3.connect` + an explicit `PRAGMA journal_mode=WAL`, plus a docstring paragraph in this same style recording *why an inherited default is not a contract* (M-3 / Pitfall 7). The lazy `from langgraph...` import inside the function is the repo's idiom for heavy deps — keep it.

**Run-id minting pattern** (`curation_run.py:430-438`), which `api/runs.py` reuses rather than reinvents:
```python
def _new_run_id() -> str:
    """Generate a sortable, kebab-safe run handle: UTC timestamp + random suffix."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"cur-{stamp}-{secrets.token_hex(3)}"
```
`secrets`, never `random` — the same module supplies `serve`'s launch token.

---

### `src/construct/api/runs.py` (service, event-driven)

**Analog:** `tests/integration/test_surface_parity.py:161-184` — the only real subprocess launch in the repo:
```python
def _cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "construct.cli", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
```
Copy `sys.executable` + `-m construct.cli` (its docstring explains why a hardcoded `.venv/bin/python` is wrong inside a worktree). **Deviate:** `subprocess.Popen` (not `run`), and redirect stderr to `.construct/workflow/logs/<run_id>.err` rather than `capture_output=True` — a pipe nobody reads is the RESEARCH-named silent-failure mode. A4 in the assumptions log flags this as the phase's first spike.

---

### `tests/contract/test_http_surface.py` (contract test)

**Analog:** `tests/contract/test_capability_seam.py` — the canonical cardinality-guard file.

**Module docstring pattern** (`:1-30`): states the two layers, names the WR-01 anti-pattern it refuses, and names its own blind spot. New guard files follow this shape.

**Tripwire + cardinality pair** (`:47-54` and `:77-105`):
```python
REGISTRY_SIZE = 29   # a deliberate tripwire (not a name set)

def test_registry_size_is_the_declared_tripwire() -> None:
    """The cardinality guard below compares two live measurements, so it stays
    true if the registry shrinks to zero. This test is what makes that
    comparison meaningful."""
    assert len(get_registry().list()) == REGISTRY_SIZE


def test_every_capability_input_model_forbids_undeclared_fields() -> None:
    capabilities = get_registry().list()
    forbidding = [c for c in capabilities if _forbids(c.input_model)]
    open_models = sorted(... for c in capabilities if not _forbids(c.input_model))
    assert len(forbidding) == len(capabilities), (
        "these capability input models accept undeclared fields at the seam: "
        f"{open_models}"
    )
```
Copy exactly: (a) the standalone integer tripwire, (b) `len(x) == len(y)` over two live measurements, (c) the failure message built from the *offending* items so the diff names the capability. The HTTP coverage guard is `len(reachable) + len(documented_exclusions) == len(registry)`.

**Per-capability parametrisation** (`:62-69`, `:137-160`):
```python
def _capability_ids() -> list[str]:
    """Every registered capability, audited unconditionally.

    There is deliberately no exemption set here."""
    return [capability.id for capability in get_registry().list()]


@pytest.mark.parametrize("cap_id", _capability_ids())
def test_declared_fields_bind_to_the_handler(cap_id: str) -> None:
    ...
```
The `WORKSPACE_FIELD` map coverage guard (A1) and the `str`/`Path` coercion test (A2 / Pitfall 9) both use this parametrisation over all 29.

---

### `tests/integration/test_surface_parity.py` — third column (differential test) — MODIFIED

**Analog:** itself. The extension point is the `ParityCase` NamedTuple (`:35-59`) — its docstring states the rule the HTTP column must respect:
> *"The projection lives in the row so the test body stays one equality assertion — adding a capability is a row, never new test logic."*

Add `build_request`/`read_http` fields to `ParityCase` and an `_http` driver beside `_cli` (`:161`) and `_mcp` (`:187`), plus `_http_reason` beside `_cli_reason` (`:237`) and `_mcp_reason` (`:244`):
```python
def _mcp_reason(payload: dict) -> str:
    """The seam's reason with the MCP surface's own framing stripped."""
    assert "error" in payload, f"expected an error value, got: {payload!r}"
    return payload["error"]
```
`_http_reason` strips HTTP's framing the same way. Also note `_seam_in_fresh_process` (`:198-234`) exists because Typer cannot express an undeclared flag — HTTP *can* send an undeclared field, so the HTTP arm can compare directly against `_seam_in_fresh_process`, which is a strengthening of the harness worth calling out.

---

### `src/construct/pipelines/graph_status.py:66` (pipeline, transform) — MODIFIED

The success-path leak (T-18-32, Pitfall 5):
```python
            "workspace": str(root.resolve()),   # ← absolute path into OperationResult.data
```
**Convention to apply** — from `cli.py:1048-1052`, the repo's stated rule for who may render a path:
> *"The reason strings carry no filesystem path by construction (T-18-10) — this is the *local* caller, so it appends the path itself."*

The capability emits a relative/omitted value; the CLI appends the absolute path locally. Track as a **separate** work item from the exception sanitizer (M-4: an exception-boundary sanitizer never sees this).

---

## Shared Patterns

### Result envelope (`OperationResult`)
**Source:** `src/construct/services/knowledge.py:67-82`
**Apply to:** every HTTP response body, `workflow.list`'s output, the status-code mapping
```python
class OperationResult:
    """The shape every capability returns, across CLI, MCP and (Phase 19) HTTP.

    * ``success`` means **the command ran**. It is what the CLI turns into an exit
      code, so the Phase 11 contract that a degraded ``curation.run`` exits 0
      (D-15) is a statement about this flag, and nothing here may move it.
    * ``outcome`` means **how it went** — the run's own status ...
    """
```
This is the direct source for the "`success=False` → HTTP **200**" rule (RESEARCH Pattern 4). The docstring already names Phase 19.

### Error handling at a surface
**Source:** `src/construct/cli.py:103-107` (26 sites), `src/construct/mcp/server.py:55-56` (1 site, defective)
**Apply to:** `api/app.py` route body
Catch the typed seam errors (`CapabilityInputError`, `CapabilityNotFoundError` — or their base `CapabilityError`, `errors.py:23-28`), never a bare `except Exception: str(exc)`.

### Path-leak avoidance
**Source:** `src/construct/capabilities/errors.py:57-63` docstring + `mcp/server.py:29-31` docstring
**Apply to:** every new serializer, every exception handler, the FastAPI validation handler
Two written-down rules: `include_input=False, include_context=False` on pydantic errors; no `default=` on `json.dumps`.

### Docstring-as-decision-record
**Source:** universal in this repo — `registry.py:48-65`, `errors.py:57-75`, `test_capability_seam.py:1-30`, `curation_run.py:495-502`
**Apply to:** every new module and every new guard
Docstrings here record *the rejected alternative and why*, and cite decision ids (D-xx / T-xx / WR-xx / CR-xx). New Phase 19 files that omit this will read as foreign to the codebase. Cite D-01..D-08, T-18-10/32/34, HTTP-01..07 inline.

### Lazy heavy imports
**Source:** `curation_run.py:503` (`from langgraph.checkpoint.sqlite import SqliteSaver` inside the function), `cli.py:965`, `cli.py:1032`
**Apply to:** `import uvicorn` / `import fastapi` in `cli.py::serve` — keep CLI startup free of the ASGI stack.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/construct/api/middleware.py` | middleware | request-response | No ASGI/HTTP middleware exists anywhere in the repo. Use RESEARCH Pattern 5's `LocalhostGuard` sketch as the source, plus `secrets` usage from `curation_run.py:438` for token generation (`secrets.compare_digest`, never `==`). |
| `COVERAGE.md` | doc artifact | — | New artifact class (D-07). Closest structural precedent is the shrink-only baseline idiom (`UNRESOLVED_DIRECT_CALLERS`, Phase 18 D-23) — a written ledger whose entries each carry a reason. |

---

## Metadata

**Analog search scope:** `src/construct/{capabilities,mcp,llm,cli.py,views/lib,services,pipelines,ui}`, `tests/contract/`, `tests/integration/`
**Files scanned:** 14 read (targeted ranges), ~10 grepped
**Pattern extraction date:** 2026-08-02
