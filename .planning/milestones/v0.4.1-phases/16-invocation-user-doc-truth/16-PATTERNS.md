# Phase 16: Invocation & User-Doc Truth - Pattern Map

**Mapped:** 2026-07-20
**Files analyzed:** 13 (3 code/registry, 4 test, 6 doc)
**Analogs found:** 7 / 7 code+test files

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/capabilities/catalog.py` (`CardListInput` + `knowledge.card.list`) | config/registry | CRUD-read | `ConnectionListInput` `:140-143` + `knowledge.connection.list` `:294-302` | exact |
| `src/construct/cli.py` (`card_list` wrapper) | controller | request-response | `connection_list` `:1452-1467` | exact |
| `src/construct/services/knowledge.py` (`list_cards` handler) | service | CRUD-read | `list_connections` `:558-600` | exact |
| `tests/unit/test_knowledge_operations.py` (`TestCardList`) | test | CRUD-read | `TestConnectionList` `:335-384` | exact |
| `tests/contract/test_card_list_cli_mcp.py` (new) | test | request-response | `tests/contract/test_daily_run_cli_mcp.py` | exact |
| `tests/contract/test_doc_command_references.py` (per-doc non-vacuity; `_DOC_GLOBS`; `_KNOWN_BROKEN`) | test | transform | self (in-file `test_docs_contain_invocations` `:180-185`) | in-place |
| `tests/contract/test_skill_migration.py` (multi-line frontmatter parser) | test | file-I/O | self (`_allowed_tools_line` `:37-44`) | in-place |
| `CONSTRUCT-CLAUDE-impl/USER_GUIDE.md` | doc | — | self (§"Full Command Reference" tables) | structural |
| `CONSTRUCT-CLAUDE-impl/construct/references/commands.md` | doc | — | self (3-col `Command \| Skill \| What it does`) | structural |
| `USER-TEST-PLAYBOOK-v041.md` (new) | doc | — | `USER-TEST-PLAYBOOK-v03.md` §0.2 | structural |
| `README.md`, `AGENTS.md`, `spec-v04-agentworkflows.md:436` | doc | — | — | prose edit |

## Pattern Assignments

### `capabilities/catalog.py` — `CardListInput` + registry entry

**Analog:** `ConnectionListInput` / `knowledge.connection.list`

**Input model** (`catalog.py:140-143`):
```python
class ConnectionListInput(BaseModel):
    workspace: Path
    card_id: str | None = None
    include_archived: bool = False
```

Note: the class relies on the module-level `BaseModel` config for `extra=forbid` — verify where that is set before assuming the research's ASVS V5 claim is satisfied by a bare `BaseModel` subclass. `CardListInput` mirrors this with `domain: str | None = None` in place of `card_id`.

**Registry entry** (`catalog.py:294-302`) — 8 lines, no `mcp_tool_name` on this record:
```python
    registry.register(CapabilityRecord(
        id="knowledge.connection.list",
        name="List Connections",
        description="List typed connections, optionally filtered by card",
        input_model=ConnectionListInput,
        output_model=OperationResult,
        handler=list_connections,
        cli_name="knowledge.connection.list",
    ))
```

**MCP parity caveat for the planner:** `connection.list` sets `cli_name` but **no `mcp_tool_name`**. The neighbouring `graph.status` record (`:303-314`) sets `mcp_tool_name="construct_graph_status"` and no `cli_name`, and `knowledge.connection.add` (`:282-283`) sets *both*. D-01 requires CLI **and** MCP parity, so `knowledge.card.list` must follow the `connection.add` shape (both fields), not the `connection.list` shape. Copying `connection.list` verbatim yields a CLI-only command and silently misses D-01.

### `cli.py` — `card_list` wrapper

**Analog:** `connection_list` (`cli.py:1452-1467`)

**Sub-app already exists** (`cli.py:161-162`) — no new Typer group needed:
```python
card_app = typer.Typer(no_args_is_help=True, name="card", help="Card CRUD operations.")
knowledge_app.add_typer(card_app)
```

**Full wrapper pattern** (`cli.py:1452-1467`):
```python
@connection_app.command("list")
def connection_list(
    ctx: typer.Context,
    card_id: Optional[str] = typer.Option(None, "--card", "-c", help="Filter by card ID"),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived card connections"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """List typed connections. Optionally filter by card or include archived."""
    try:
        cap = get_registry().get("knowledge.connection.list")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
    result = cap.handler(workspace, card_id=card_id, include_archived=include_archived)
    _display_result(result, json_output)
```

Register as `@card_app.command("list")` — the explicit string name matters, since `_command_paths()` in the guard falls back to `callback.__name__.replace("_","-")`, which would yield `card-list`.

### `--json` emission — the D-02/serialization hazard, confirmed

**Source:** `_display_result` (`cli.py:165-192`)

```python
def _display_result(result: OperationResult, json_output: bool) -> None:
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "success": result.success,
                    "message": result.message,
                    "errors": [...],
                    "data": result.data,
                },
                indent=2,
            )
        )
```

**This is a bare `json.dumps` with no `default=` and no custom encoder.** A handler returning `load_cards()` output puts `datetime.date` into `result.data` and `--json` raises `TypeError: Object of type date is not JSON serializable` — a hard crash, not merely non-ISO output as RESEARCH.md hedged. The fix belongs in the handler (mirroring `list_connections`'s `model_dump(mode="json")`), **not** in `_display_result`, which is shared by every command.

### `services/knowledge.py` — `list_cards` handler

**Analog:** `list_connections` (`:558-600`)

**Load + error envelope** (`:567-577`):
```python
    root = Path(workspace_root)
    loader = WorkspaceLoader(root)

    try:
        connections = loader.load_connections()
    except WorkspaceLoadError as exc:
        return OperationResult(
            success=False,
            message=f"Could not load connections.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )
```

**Archive filter** (`:587-594`) — reuse `_get_archived_card_ids(root)` (`:603-617`) rather than re-deriving lifecycle.

**Return shape — the line that solves both hazards** (`:596-600`):
```python
    return OperationResult(
        success=True,
        message=f"Found {len(result_connections)} connection(s)",
        data=[c.model_dump(mode="json", by_alias=True) for c in result_connections],
    )
```

`list_connections` never touches `load_cards()`; it re-dumps Pydantic models in JSON mode. `list_cards` cannot copy this verbatim because `load_cards()` returns **plain dicts, already dumped in python mode** (`workspace.py:164`, `card.model_dump()`). Two options: re-parse and `model_dump(mode="json")` per card, or post-process the dicts. Either way the handler must also `card_data.pop("body", None)` — `load_cards()` sets `card_data["body"] = body` at `workspace.py:168` (D-02).

### `tests/unit/test_knowledge_operations.py` — `TestCardList`

**Analog:** `TestConnectionList` (`:335-384`) — class-per-command, `workspace_with_cards` fixture, one method per filter dimension:

```python
class TestConnectionList:
    def test_list_connections(self, workspace_with_cards: Path) -> None:
        workspace = workspace_with_cards
        add_connection(workspace, "card-a", "card-b", ConnectionType.supports)

        result = list_connections(workspace)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
```

Archived-exclusion pattern (`:360-373`) uses `archive_card(workspace, "card-a")` then asserts absence. The two Wave 0 tests slot in as additional methods: `test_card_list_excludes_body` (`assert "body" not in result.data[0]`) and `test_card_list_json_serializable` (`json.dumps(result.data)` must not raise — this directly exercises the `_display_result` crash path above).

### `tests/contract/test_card_list_cli_mcp.py` (new)

**Analog:** `tests/contract/test_daily_run_cli_mcp.py` (123 lines, read in full)

Structure to copy: module-level `_CAPS = {cap_id: mcp_tool_name}` dict, `runner = CliRunner()`, then five test shapes:

```python
def test_registered() -> None:
    reg = get_registry()
    for cap_id, mcp_name in _CAPS.items():
        cap = reg.get(cap_id)
        assert cap.input_model is not None
        assert cap.mcp_tool_name == mcp_name
        assert cap.cli_name == cap_id
```

```python
def test_mcp_no_hardcoded_daily() -> None:
    """Parity is free: the server auto-discovers records, so it must contain no
    daily-specific wiring."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "construct_daily_run" not in src
    assert "daily.run" not in src
```

This GREEN guard is the mechanical proof of D-01's "registry-routed, not hand-written" — it is the test that would catch the views-group exception being repeated.

```python
def test_cli_mcp_schema_parity(tmp_path, monkeypatch) -> None:
    cap = get_registry().get("daily.run")
    handler_result = cap.handler(workspace_path=str(ws))
    mcp_serialized = _serialize_result(handler_result)

    cli = runner.invoke(app, ["daily", "run", "--workspace", str(ws), "--json"])
    assert cli.exit_code == 0, cli.stdout
    cli_payload = json.loads(cli.stdout)

    assert set(cli_payload.keys()) == set(mcp_serialized.keys())
```

For `card list` this parity test doubles as the JSON-serialization regression: `json.loads(cli.stdout)` fails loudly if dates leak.

Also note `test_shims_reject_positional_args` (`:55-59`) — daily's handlers are keyword-only shims. `list_connections` accepts `workspace_root` positionally (`cli.py:1466` calls `cap.handler(workspace, card_id=...)`), so `card list` should follow the `connection list` calling convention and **omit** the positional-rejection test rather than import a discipline its analog does not have.

### `tests/contract/test_doc_command_references.py` — three in-place changes

**`_DOC_GLOBS`** (`:41-45`) — D-05 replaces the playbook line, D-11 adds two:
```python
_DOC_GLOBS = (
    (_IMPL / "claude" / "skills", "*/SKILL.md"),
    (_IMPL / "construct" / "workflows", "*.md"),
    (_REPO_ROOT, "USER-TEST-PLAYBOOK-v03.md"),
)
```
Entries are `(root, pattern)` pairs consumed by `_doc_files()` (`:131-138`), which handles both directory-glob and single-file forms. `USER_GUIDE.md` and `commands.md` are single files, so they take the `(root, "relative/path.md")` form — but note `_doc_files()` tests `(root / pattern).is_file()`, so a nested path like `(_IMPL, "construct/references/commands.md")` works.

**The global anti-vacuity assertion to make per-doc** (`:180-185`):
```python
def test_docs_contain_invocations() -> None:
    """Guard the extractor — a silent regex failure would make the suite vacuous."""
    documented = _documented()
    assert documented, "no documentation files found"
    total = sum(len(v) for v in documented.values())
    assert total > 10, f"extractor found only {total} invocations — regex likely broken"
```
The new `test_key_docs_are_not_vacuous` should follow the existing parametrize idiom (`:188-191`) over a named `_MUST_CARRY_INVOCATIONS` tuple:
```python
@pytest.mark.parametrize(
    "doc_path",
    [pytest.param(p, id=f"{p.parent.name}/{p.name}") for p in _doc_files()],
)
```
Keep `test_docs_contain_invocations` — it guards the regex globally; the new test guards per-doc coverage. They are complements, not a replacement.

**`_KNOWN_BROKEN`** (`:152-157`) — must reach `{}`:
```python
_KNOWN_BROKEN: dict[tuple[str, ...], str] = {
    ("knowledge", "card", "list"): "V41-03 / FIX-03 — no `list` on the card sub-app",
    ("knowledge", "ref", "list"): "V41-03 / FIX-03 — no `ref` sub-app exists",
    ("workflow", "run"): "V41-03 / FIX-03 — removed in Phase 12 (D-10)",
    ("workflow", "resume"): "V41-03 / FIX-03 — never existed",
}
```
The paired enforcer is `test_known_broken_entries_are_still_broken` (`:212-220`) — parametrized over the dict, so an empty dict yields **zero params**, which pytest reports as a skipped/empty parametrization rather than a failure. That is the intended terminal state.

**Do not touch `_resolves()`** (`:123-128`) — the leaf-vs-group logic is what makes `workflow run` fail:
```python
def _resolves(path: tuple[str, ...]) -> bool:
    if path in VALID_PATHS:
        return True
    return any(path[:i] in LEAF_COMMANDS for i in range(len(path) - 1, 0, -1))
```

**`test_command_surface_is_discoverable`** (`:170-177`) gains `assert ("knowledge", "card", "list") in VALID_PATHS`. Its `assert len(VALID_PATHS) > 25` is a lower bound and needs no change (D-12: do not convert it to an equality).

### `tests/contract/test_skill_migration.py` — multi-line parser

**The defective parser** (`:37-44`):
```python
def _allowed_tools_line(skill: str) -> str:
    """Return the ``allowed-tools:`` frontmatter line for a migrated skill."""
    path = _SKILLS_DIR / skill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("allowed-tools:"):
            return line
    raise AssertionError(f"{skill}/SKILL.md has no allowed-tools frontmatter line")
```

Both consumers take a single `str` and use substring containment:
```python
@pytest.mark.parametrize("skill", _MIGRATED_SKILLS)
def test_skill_drops_forbidden_tools(skill: str) -> None:
    line = _allowed_tools_line(skill)
    for tool in _FORBIDDEN_TOOLS:
        assert tool not in line, f"{skill} still allows forbidden tool {tool!r} in: {line}"
```

**Least-disruptive fix:** keep the `-> str` signature and rename to `_allowed_tools_text()`, returning the `allowed-tools:` line **plus** any following indented `- ` continuation lines joined. Both assertions then keep working unchanged (substring containment over a longer string), and `test_skill_still_delegates_to_cli`'s `"Bash(construct)" in line` starts passing for synthesis. This avoids adding a YAML dependency and touches one function.

**Scope list** (`:27-31`) gains `"construct-synthesis"`:
```python
_MIGRATED_SKILLS = (
    "construct-research-cycle",
    "construct-curation-cycle",
    "construct-card-evaluate",
)
```

**Ordering (Pitfall 4):** extend the parser *first*, add `construct-synthesis` to `_MIGRATED_SKILLS` *second*, and confirm `test_skill_drops_forbidden_tools[construct-synthesis]` goes **RED** before removing the grants. A green-on-first-run is the vacuity tell.

## Doc Structural Conventions (light touch)

### `CONSTRUCT-CLAUDE-impl/USER_GUIDE.md`
`## Full Command Reference` → `### {Capability group}` → a 2-column table per group:
```
| You say | What happens |
|---------|-------------|
| "help" / "what's next?" | Scans workspace, suggests the most valuable next action |
```
D-10 adds a third column. Groups are already capability-shaped (`Entry & orientation`, `Research`, `Knowledge operations`, …), so the criterion-named surface slots into existing or new `###` sections without restructuring.

### `CONSTRUCT-CLAUDE-impl/construct/references/commands.md`
Already **3 columns** — `| Command | Skill | What it does |` under `## {Group}` headings, separated by `---`. D-10's addition here is a fourth column (CLI) or a repurposing of the existing shape; the planner should decide which, since "Skill" is not the same axis as "CLI invocation". Note `## Starting Point` uses a different 2-column header (`| Say | What happens |`) and contains the bare `` `construct` `` at `:15` that the extractor correctly ignores.

### `USER-TEST-PLAYBOOK-v041.md`
Carry `USER-TEST-PLAYBOOK-v03.md` §0.2's smoke-workspace recipe. Per-step shape from §6's precedent: a heading suffixed `— requires ANTHROPIC_API_KEY` marks credentialed steps (D-07). Keep every CLI invocation on **one line** — `_INVOCATION`'s `[ \t]+` will not match a wrapped command (`test_doc_command_references.py:54-56`).

## Shared Patterns

### Registry-first capability wiring
**Source:** `catalog.py:285-302` + `cli.py:1452-1467`
**Apply to:** `knowledge.card.list` only
Handler lives in `services/`, registered as a `CapabilityRecord`, CLI is a 15-line `get_registry().get(...)` → `handler(...)` → `_display_result(...)` wrapper with zero logic. MCP is auto-discovered from the record.

### CLI error envelope
**Source:** `cli.py:1461-1465`
**Apply to:** the new CLI wrapper
```python
    try:
        cap = get_registry().get("knowledge.connection.list")
    except KeyError:
        typer.echo("ERROR: Capability not found. Ensure the registry is properly initialized.")
        raise typer.Exit(code=1)
```

### Service error envelope
**Source:** `services/knowledge.py:570-577`
**Apply to:** `list_cards`
`try` the load, return `OperationResult(success=False, message=..., errors=[OperationError(reason=str(exc))])` on `WorkspaceLoadError`. Exit code 1 follows automatically from `_display_result`'s `if not result.success` (`cli.py:191-192`).

### Guard-vacuity discipline
**Source:** `test_doc_command_references.py:170-185`, `:212-220`
**Apply to:** every test change in this phase
Each guard in this file has a *meta-guard* asserting it is still looking (`test_command_surface_is_discoverable`, `test_docs_contain_invocations`, `test_documented_script_paths_exist`'s `assert scanned`). New guards should carry the same. This is the established local convention behind both Wave 0 anti-vacuity deliverables.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `test_key_docs_are_not_vacuous` | test | transform | No per-document coverage assertion exists anywhere in the suite; the closest is the global `test_docs_contain_invocations`. Novel but small. |
| `USER-TEST-PLAYBOOK-v041.md` capability-organised structure | doc | — | Every existing playbook is organised by delivery phase (D-06 explicitly abandons that). No capability-organised precedent in the repo. |

## Metadata

**Analog search scope:** `src/construct/{cli.py,capabilities/,services/,storage/}`, `tests/{unit,contract}/`, `CONSTRUCT-CLAUDE-impl/{USER_GUIDE.md,construct/references/}`
**Files scanned:** 11 read, 4 grep sweeps
**Pattern extraction date:** 2026-07-20
</content>
</invoke>
