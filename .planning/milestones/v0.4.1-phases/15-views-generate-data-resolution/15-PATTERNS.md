# Phase 15: views.generate_data Resolution - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 14 (created/modified)
**Analogs found:** 12 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/views/lib/*.py` (15 modules, vendored) | utility | file-I/O | verbatim move from skill `lib/` | move, no analog needed |
| `src/construct/views/lib/__init__.py` | config | — | `src/construct/views/__init__.py` | role-match |
| `src/construct/views/generate.py` (imports + warning fmt) | service | batch/file-I/O | itself (edit in place) | in-place |
| `src/construct/views/models.py` (D-02 widening) | model | transform | `DomainsFile` / `ArticleRecord` in same file | exact |
| `src/construct/cli.py` — `views generate` cmd | route | request-response | `cli.py:868-895` `views validate` | exact |
| `src/construct/cli.py` — `--install-root` rename | route | request-response | `cli.py:870` `--workspace/-w` option | exact |
| `src/construct/capabilities/catalog.py` — `ViewsGenerateDataInput` | model | — | `GraphStatusInput` (`catalog.py:144-145`) | exact |
| `src/construct/capabilities/catalog.py` — real handler | controller | request-response | `graph.status` record (`catalog.py:298-308`) | exact |
| `src/construct/llm/curation_run.py` — `views_refresh_hook` | service | event-driven | `apply_archives` node (`curation_run.py:~960-978`) | exact |
| `src/construct/llm/research_run.py` — refresh call | service | event-driven | `update_seeds_and_log` (`research_run.py:745`) + graph wiring at `:836-871` | exact |
| `src/construct/llm/daily_run.py` — refresh call | service | event-driven | `_run_graph_child` (`daily_run.py:195`) | role-match |
| `tests/integration/test_views_generate.py` | test | file-I/O | `tests/integration/test_init_cli.py` | exact |
| `tests/unit/test_views_lib_imports.py` | test | — | `tests/unit/test_capability_registry.py` | role-match |
| `tests/contract/test_doc_command_references.py` (delete entry) | test | — | itself (`:152-158`) | in-place |
| `pyproject.toml` — add `pyyaml>=6` | config | — | `pyproject.toml:11-20` dependency list | exact |
| D-11 supersession record (ADR / PROJECT.md row) | config/doc | — | Phase 14 D-07's ADR precedent | role-match |

---

## Pattern Assignments

### `src/construct/cli.py` — new `views generate` command (route, request-response)

**Analog:** `src/construct/cli.py:868-895` (`views validate`), same Typer group.

**Group + command declaration pattern** (`cli.py:859-877`):
```python
views_app = typer.Typer(
    no_args_is_help=True,
    name="views",
    help="Validate and manage views data contracts.",
)
app.add_typer(views_app)


@views_app.command()
def validate(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Validate views data files against their Pydantic schemas.
    ...
    """
```
Copy exactly for `generate`: `@views_app.command()`, `ctx: typer.Context` first, the same `--json/-j` option, a docstring. Rename the path option to `--install-root` per D-06 on **both** commands (discretion: whether `-w` survives as the alias).

**Deferred-import pattern** (`cli.py:875-889`): heavy imports live **inside** the command body, not at module top:
```python
    from construct.views.models import (
        ArticlesFile,
        BridgesFile,
        ...
    )
```
`generate` should follow this (`from construct.views.generate import generate`) — it also mitigates Pitfall 5's CLI-startup cost concern.

**Error/exit pattern** (`cli.py:893-896`):
```python
    build_data_dir = workspace / "views" / "build" / "data"
    if not build_data_dir.is_dir():
        typer.echo(f"ERROR: No views data directory at {build_data_dir}")
        raise typer.Exit(code=1)
```
`typer.echo` + `raise typer.Exit(code=1)` — never `sys.exit`, never a raw raise.

---

### `src/construct/capabilities/catalog.py` — input model + real handler (controller, request-response)

**Analog:** the `graph.status` record immediately above the target, `catalog.py:298-308`.

**Input model pattern** (`catalog.py:144-150`) — flat `BaseModel`, one field per CLI arg:
```python
class GraphStatusInput(BaseModel):
    workspace: Path


class ViewsGenerateDataInput(BaseModel):
    workspace: Path        # → install_root: Path  (D-05)
```

**Real-handler registration pattern** (`catalog.py:298-308`) — this is the exact shape that replaces the failure lambda at `:317`:
```python
    registry.register(CapabilityRecord(
        id="graph.status",
        name="Graph Status",
        description="Produce graph health report for a workspace",
        input_model=GraphStatusInput,
        output_model=OperationResult,
        # ING-05: wire the real graph_status() report. Accepts workspace both
        # positionally (help.py:126 calls handler(workspace_id)) and by keyword
        # (GraphStatusInput / MCP pass workspace=...).
        handler=lambda workspace: graph_status(workspace),
        mcp_tool_name="construct_graph_status",
    ))
```
Two load-bearing details to copy: (1) the **named single-parameter lambda** (`lambda install_root: ...`), which accepts both positional and keyword call forms — the current `lambda **kwargs:` at `:317` does not; (2) the **inline comment citing the defect ID** that authorised the wiring (here `V41-01 / FIX-01`, `D-01`). The neighbouring D-10/CUR-05 comment block at `:319-323` shows the house style for recording a decision in-line.

The handler must map `GenerateReport` → `OperationResult`: `validation_errors` fatal, `warnings` advisory in `message` (discretion item).

---

### `src/construct/views/models.py` — D-02 field widening (model, transform)

**Analog:** sibling models in the same file. `DomainRecord` at `:91-103` is the edit target; `ArticleRecord` (`:118-127`) and `DomainsFile` (`:106-113`) are the shape to copy.

**Model declaration pattern** (`models.py:91-113`):
```python
class DomainRecord(BaseModel):
    """One domain entry with derived graph metrics."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    card_count: int = 0
    keywords: list[str] = Field(default_factory=list)


class DomainsFile(BaseModel):
    """Data payload for domains.json."""

    model_config = ConfigDict(extra="forbid")

    settings: dict = Field(default_factory=dict)
    domains: list[DomainRecord] = Field(default_factory=list)
```
Invariants to preserve on every edited model:
- one-line docstring
- `model_config = ConfigDict(extra="forbid")` as the first body statement — **never removed, never relaxed** (D-02)
- required fields first, then defaulted ones
- scalars default inline (`= 0`, `= None`); collections use `Field(default_factory=list)` — never a bare mutable default
- optionals use PEP-604 unions (`published_date: str | None = None`, `:126`)

Fields to add per RESEARCH F3/F4 follow this exact style, e.g. `top_domain_pairs: list[dict] = Field(default_factory=list)`, `connections: list[str]`, `metrics: dict = Field(default_factory=dict)`.

---

### `src/construct/views/generate.py` — import block + warning formatter (service, batch)

**Analog:** in-place edit; the pattern to *delete* is `generate.py:43-70`.

**Delete this entire block** (`:43-55`):
```python
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SKILL_LIB = (
    _PROJECT_ROOT / "CONSTRUCT-CLAUDE-impl" / "claude" / "skills"
    / "construct-views-generate-data"
)
if str(_SKILL_LIB) not in sys.path:
    sys.path.insert(0, str(_SKILL_LIB))
```

**Rewrite the import to package-relative** — the existing grouped-alias form at `:56-70` is kept verbatim, only the module path changes:
```python
from lib import (                      # →  from construct.views.lib import (
    build_id as build_id_mod,
    compute_stats,
    discover,
    envelope,
    fingerprint as fp,
    parse_articles,
    ...
)
```
The `# pylint: disable=wrong-import-position` / `# noqa: E402` comments at `:55` become unnecessary once the `sys.path` block is gone — delete them too. Check whether `import sys` at the top is left orphaned.

**Report dataclass to leave untouched** (`generate.py:78-88`) — it already carries D-04's distinction:
```python
@dataclass
class GenerateReport:
    success: bool
    build_id: str
    workspace_stats: dict = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_files_written: int = 0
```

**Do not touch** `_FILE_MODEL_MAP` at `:95-165` — OQ-1 resolved to reading (a). Its entries stay exactly as-is:
```python
_FILE_MODEL_MAP: list[tuple[str, type, callable]] = [
    ("bridges.json", BridgesFile, lambda d: {"bridges": d.get("bridges", []), "summary": d.get("summary", {})}),
    ("domains.json", DomainsFile, lambda d: {"settings": d.get("settings", {}), "domains": d.get("domains", [])}),
    ...
]
```

Pitfall 4's cosmetic fix belongs at `:385-389` only.

---

### `src/construct/llm/curation_run.py` — `views_refresh_hook` (service, event-driven)

**Analog:** `apply_archives`, the node directly above the target (`curation_run.py:~968-978`).

**Node body pattern with per-item error isolation and event emission**:
```python
        except Exception as exc:  # noqa: BLE001 — per-item isolation (D-08)
            logger.warning("apply_archives %s failed: %s", card_id, _sanitize_error(exc))
    events.append(_emit(workspace, "workflow_step_complete", state["run_id"], "apply_archives"))
    return {"archived": archived, "rejected": rejected, "events": events}
```
Copy for the refresh: broad `except Exception` with the `# noqa: BLE001` comment and a decision-ID rationale, `logger.warning(...)` through `_sanitize_error(exc)` (never a raw exception into a log), then `_emit(...)` appended to `events`, then a dict return. **This idiom is exactly how D-12's "side effect, not a success condition" is expressed** — the except swallows and logs, and the returned dict never sets a failure status.

**Pattern to delete** (`curation_run.py:354-362` + its only call site at `:981-982`):
```python
def _deferred_step(step: str) -> dict:
    """Emit a deferred skip-node result (D-10): skipped, optional, Phase-12 reason."""
    result = CurationStepResult(
        step=step, status="skipped", required=False,
        reason="deferred to Phase 12",
        summary=f"{step} deferred to Phase 12 (curation gates land in Phase 12)",
    )
    return {"steps": [result.model_dump(mode="json")]}


def views_refresh_hook(state: CurationRunState) -> dict:
    return _deferred_step("views_refresh_hook")
```
Per RESEARCH Pitfall 3 the helper has no other caller — it goes with its last call site.

Note the sibling result-builder just above (`:346-351`) shows the `CurationStepResult(step=..., status=..., reason=safe, summary=...)` construction if the refresh needs to report a step result.

---

### `src/construct/llm/research_run.py` — refresh node + graph wiring (service, event-driven)

**Analog:** `update_seeds_and_log` (`:745`) as the current terminal node, and the builder at `:836-871`.

**Graph wiring pattern** (`research_run.py:847-871`) — every node registered then edged in linear order, terminating at `END`:
```python
    builder.add_node("update_seeds_and_log", update_seeds_and_log)

    builder.add_edge(START, "load_config")
    ...
    builder.add_edge("compile_digest", "update_seeds_and_log")
    builder.add_edge("update_seeds_and_log", END)
```
To append a refresh: `builder.add_node("views_refresh", views_refresh)`, re-point `update_seeds_and_log → views_refresh`, then `views_refresh → END`. Mirror the same insertion in `curation_run.py`'s builder (its existing `views_refresh_hook` edges are at `:1026, 1047-1048`).

**Function-local import precedent** (`research_run.py:644`, inside `_write_digest`): `llm → views` imports are already done function-locally in this package. Follow it for the refresh helper to keep CLI startup cheap and the dependency edge obviously acyclic.

---

### `src/construct/llm/daily_run.py` — refresh call (service, event-driven)

**Analog:** `_run_graph_child` (`daily_run.py:195-214`) — `daily_run.py` is **not** a LangGraph module; it is plain sequential orchestration inside `run_daily_run` (`:215`). Do not add graph nodes here.

**Child-invocation pattern** (`:146-214`): private `_run_*` helpers returning a `DailyChildStatus` (or a tuple with extra payload), called in sequence from `run_daily_run`, aggregated by `_aggregate_daily_status` (`:125`). A `_run_views_refresh(workspace_path)` helper called near the end of `run_daily_run` is the shape that fits — and per D-12 its outcome must **not** feed `_aggregate_daily_status`.

---

### `tests/integration/test_views_generate.py` (test, file-I/O) — NEW

**Analog:** `tests/integration/test_init_cli.py:1-36`.

**Header + fixture-path pattern** (`:1-19`):
```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from construct.cli import app


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
```
Use `FIXTURES_DIR` for the populated-workspace target (`tests/fixtures/v02/multi-domain-medium/`) per Pitfall 1.

**Test-function pattern** (`:21-36`):
```python
def test_construct_init_creates_full_workspace_scaffold(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"

    result = runner.invoke(app, ["init", str(workspace)], input="...")

    assert result.exit_code == 0, result.stdout
    assert "Initialized CONSTRUCT workspace" in result.stdout
```
Copy: module-level `def test_*` (no classes), `tmp_path: Path` fixture, `-> None` annotation, `CliRunner()` constructed per-test, arrange/invoke/assert separated by blank lines, and `assert result.exit_code == 0, result.stdout` — the stdout message is what makes CLI failures debuggable. For the direct-API tests, use RESEARCH's verified harness (`initialize_workspace` + `generate(root)`); for the CLI surface, use `runner.invoke(app, ["views", "generate", "--install-root", str(root)])`.

Per Pitfall 2, `tmp_path` isolation is what keeps the fingerprint cache from masking the model change — never assert against a reused build dir.

---

### `pyproject.toml` — declare PyYAML (config)

**Analog:** the `[project] dependencies` list at `:11-20` — alphabetically ordered, lower-bound-only, double-quoted, two-space indent:
```python
dependencies = [
  "langchain-anthropic>=1.1.0",
  ...
  "pydantic>=2.7",
  "ruamel.yaml>=0.18",
  "streamlit>=1.35",
  "typer>=0.12",
]
```
Insert `"pyyaml>=6",` between `pydantic` and `ruamel.yaml` (F6 → Option A).

Also relevant (`:37-38`): `[tool.hatch.build.targets.wheel] packages = ["src/construct"]` — subpackages are picked up provided `src/construct/views/lib/__init__.py` exists. RESEARCH A5 flags the custom hook at `:35` (`hatch_build.py`) as uninspected; one build-and-inspect check belongs in the vendoring wave.

---

### `tests/contract/test_doc_command_references.py` — allowlist shrink (test)

**Analog:** in-place, `:152-158`. The dict is self-enforcing — the paired test fails when an entry *starts* resolving, so deleting the line is the whole change:
```python
_KNOWN_BROKEN: dict[tuple[str, ...], str] = {
    ("knowledge", "card", "list"): "V41-03 / FIX-03 — no `list` on the card sub-app",
    ("knowledge", "ref", "list"): "V41-03 / FIX-03 — no `ref` sub-app exists",
    ("views", "generate"): "V41-01 / FIX-01 — views sub-app is `validate` only",   # ← DELETE
    ...
}
```
Note the value format: `"<audit-defect> / <FIX-id> — <reason>"`. Phase gate: exactly 4 entries remain.

---

## Shared Patterns

### Decision-ID comments in code
**Source:** `catalog.py:303-305`, `:319-323`; `curation_run.py:975`
**Apply to:** every non-obvious edit in this phase
```python
        # ING-05: wire the real graph_status() report. Accepts workspace both
        # positionally (help.py:126 calls handler(workspace_id)) and by keyword
        # (GraphStatusInput / MCP pass workspace=...).
```
This codebase records *why* inline with the decision ID (`D-08`, `ING-05`, `CUR-05`, `V41-01 / FIX-01`). Every D-01/D-05/D-08/D-11 edit should carry one. This is also the cheapest partial discharge of D-11's "durable enough that Phase 17 does not re-derive the old rule".

### Error sanitisation before logging
**Source:** `curation_run.py` `_sanitize_error` (used at `:976`)
**Apply to:** all three refresh call sites
```python
logger.warning("apply_archives %s failed: %s", card_id, _sanitize_error(exc))
```
Lazy `%s` formatting, never f-strings in log calls; exceptions always through `_sanitize_error`.

### Strict Pydantic contracts
**Source:** `views/models.py` — all 17 models
**Apply to:** every model touched by D-02
```python
    model_config = ConfigDict(extra="forbid")
```
D-02 and the RESEARCH security section both make this a guarded invariant: the phase must not weaken any `model_config`.

### Verbatim-move discipline (D-08)
**Source:** the 15 skill `lib/` modules
**Apply to:** the whole vendoring wave
Only import lines change. The security control is a byte-level diff of the moved modules with import lines excepted, plus the check `grep -rn "yaml.load\|sys.path" src/construct/views/` returning nothing (`yaml.safe_load` at `parse_domains.py:50` and in `frontmatter.py` must survive unchanged).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| D-11 supersession record (ADR or PROJECT.md Key Decisions row) | doc | — | No ADR directory located during this pass. Phase 14 D-07 is the cited precedent for choosing a new ADR over an amendment; the planner should locate the existing ADR set (if any) before choosing the form. |
| `CONSTRUCT-CLAUDE-impl/.../construct-views-generate-data/run.sh` (D-09 rewrite) | config | — | No existing skill in the repo is already a pure CLI wrapper — D-09 creates the first instance of the pattern. RESEARCH notes three other skills still violate it (deferred to v0.6), so there is nothing to copy from. |

---

## Metadata

**Analog search scope:** `src/construct/{cli.py,views/,capabilities/,llm/}`, `tests/{unit,integration,contract}/`, `pyproject.toml`
**Files scanned:** 12 (targeted reads; no full-file loads over 2,000 lines)
**Pattern extraction date:** 2026-07-19
