---
phase: 15-views-generate-data-resolution
reviewed: 2026-07-20T00:00:00Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/run.sh
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/SKILL.md
  - CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md
  - CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - src/construct/llm/curation_run.py
  - src/construct/llm/daily_run.py
  - src/construct/llm/research_run.py
  - src/construct/views/generate.py
  - src/construct/views/lib/__init__.py
  - src/construct/views/lib/discover.py
  - src/construct/views/lib/fingerprint.py
  - src/construct/views/lib/frontmatter.py
  - src/construct/views/lib/parse_domains.py
  - src/construct/views/models.py
  - src/construct/views/refresh.py
  - tests/contract/test_doc_command_references.py
  - tests/contract/test_mcp_contracts.py
  - tests/contract/test_views_contracts.py
  - tests/integration/conftest.py
  - tests/integration/test_views_generate.py
  - tests/llm/test_curation_run.py
  - tests/llm/test_views_refresh.py
  - tests/unit/test_capability_registry.py
  - tests/unit/test_views_lib_imports.py
findings:
  critical: 4
  warning: 11
  info: 4
  total: 19
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-07-20
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

The D-12 side-effect discipline in `views/refresh.py` is the strongest part of this phase:
the gates are ordered correctly, the config read is genuinely defensive, and the
`RefreshOutcome` type really is incompatible with every caller's status-aggregation type.
The paired healthy/raising tests in `tests/llm/test_views_refresh.py` are the right shape
and would catch a regression.

The defects cluster elsewhere:

1. **`generate()` masks its own validation failures permanently.** The fingerprint meta and
   `version.json` are written unconditionally, including on runs that skipped file writes
   because of validation errors. The next run short-circuits and reports success forever.
2. **`_views_generate_handler` is the only registry handler with no exception handling.**
   Every sibling shim (`_curation_result_to_operation`, `_research_score_shim`,
   `_daily_result_to_operation`, `_card_evaluate_shim`) exists specifically to stop raw
   exception text reaching the CLI and MCP surfaces. This one does not, and the MCP contract
   test that should have caught it swallows every non-`TypeError`.
3. **No entrypoint validates the install root.** `main()` checks for `AGENTS.md`; the CLI
   command and the MCP-reachable handler do not, and `generate()` calls
   `mkdir(parents=True)` before discovery — so an arbitrary path argument creates
   directory trees anywhere the process can write.
4. **The new skill frontmatter grants `Bash(bash *)`**, the broadest grant in the skill set
   apart from bare `Bash`.

Known-context items (writer/validator divergence, `confirm_refresh` as a verbosity switch,
the stale `decay_scan` reason, the lost per-card debounce path) were excluded. WR-02 below
is a *distinct* `confirm_refresh` defect: the interpretation is fine, but the value is
discarded by all three callers, so the flag is inert.

## Structural Findings (fallow)

No structural pre-pass payload was supplied with this review.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: A validation-error run poisons the fingerprint cache and permanently reports success

**File:** `src/construct/views/generate.py:316-354`
**Issue:** In the write loop, a file that fails `_validate_file_data` is `continue`d — no
bytes are written and `total_files_written` is not incremented. But steps 8 and 10 then run
unconditionally:

- `version.json` is written with the **new** `build_id` (line 331-339), so the SPA's
  `version.json` poll sees a fresh build and refetches data files that were never updated.
- `fp.save_meta(...)` (line 349) records the **current** source fingerprints for the very
  workspace whose output was rejected.

On the next invocation the early-return at line 203 fires (`not changed_ws and not
removed_ws and ...`), returning `GenerateReport(success=True, build_id=<old>,
total_files_written=0)`. The failure is now invisible: `views generate` exits 0, the
capability reports success, and `refresh_views` reports `succeeded`. The only way to observe
the broken build again is to touch a source file or delete `_build_meta.json`.

This also silently breaks `refresh_views`'s failure channel — a workflow tail that hit a
validation error once will report `succeeded` on every subsequent run over unchanged state.

**Fix:** Do not commit build state for a failed run. At minimum, gate steps 8 and 10:

```python
    build_ok = not validation_errors

    # 8. version.json — only advertise a build whose files actually landed.
    if build_ok:
        _write_atomic(build_dir / "version.json", {...})
        total_files_written += 1

    # 10. Save build meta — only cache fingerprints for a build that succeeded,
    #     so a failed run is retried rather than short-circuited forever.
    if build_ok:
        fp.save_meta(data_dir, {...})
```

A finer-grained fix (drop only the failed workspaces from `new_ws_fps`) is preferable if
partial builds must be supported, but the all-or-nothing gate is correct and minimal.

### CR-02: `_views_generate_handler` propagates raw exceptions to the CLI and MCP surfaces

**File:** `src/construct/capabilities/catalog.py:522-573`
**Issue:** The handler calls `generate(Path(install_root))` with no `try`. Every other
handler in this file routes exceptions through a sanitizer
(`_run_result_to_operation`, `_curation_result_to_operation`, `_daily_result_to_operation`,
`_research_score_shim`, `_card_evaluate_shim`) precisely so the MCP surface never leaks raw
text and the CLI never tracebacks (the CR-01/T-09-06 discipline the file's own docstrings
cite). Reachable raising paths:

- `discover.discover_workspaces` → `install_root.iterdir()` raises `FileNotFoundError` /
  `NotADirectoryError` for a non-existent or file path (`views/lib/discover.py:19`).
- `data_dir.mkdir(parents=True, exist_ok=True)` raises `PermissionError` /
  `FileExistsError` on a read-only or occupied path (`views/generate.py:177`).
- `_load_cached_workspace` shape assumptions (see WR-03).

The resulting exception carries the **full filesystem path** into the MCP client's error
channel — the same leak the sanitizers exist to prevent.

**Fix:** Wrap the call and mirror the sibling discipline:

```python
    try:
        report = generate(Path(install_root))
    except Exception as exc:  # noqa: BLE001 — surface parity with the sibling shims
        return OperationResult(
            success=False,
            message=f"views.generate_data failed: {type(exc).__name__}",
            errors=[OperationError(field="views.generate", reason=type(exc).__name__, suggestion="")],
            data={"failed": True},
        )
```

### CR-03: No entrypoint validates the install root; `generate()` creates directories before discovery

**File:** `src/construct/views/generate.py:175-177`, `src/construct/cli.py:869-882`,
`src/construct/capabilities/catalog.py:522-536`
**Issue:** `generate()` unconditionally runs
`(<arg>/views/build/data).mkdir(parents=True, exist_ok=True)` as its **first** filesystem
action, before it has established that the argument is a CONSTRUCT install root. The
`AGENTS.md` guard exists in exactly one place — `generate.main()` at line 628 — which is the
`python3 -m` path that nothing in this phase uses. Neither the `construct views generate`
CLI command nor the MCP-exposed `views.generate_data` handler applies it. The skill doc
(`construct-views-generate-data/SKILL.md:21`) states the guard as prose an agent is trusted
to execute.

Consequences: `construct views generate --install-root /any/writable/path` (or the same via
`construct_views_generate_data`, whose `install_root` is attacker/agent-supplied over MCP)
silently creates `views/build/data/` plus `version.json`, `_build_meta.json` and
`_generation-warnings.log` in an unrelated directory, and reports `success=True` with an
empty build. `--install-root` also defaults to `Path.cwd()`, so an accidental bare
`construct views generate` scaffolds a views tree wherever the user happens to be standing.

**Fix:** Move the guard into `generate()` so all three entrypoints inherit it, and validate
before any `mkdir`:

```python
def generate(install_root: Path) -> GenerateReport:
    root = Path(install_root)
    if not (root / "AGENTS.md").is_file():
        return GenerateReport(
            success=False,
            build_id="",
            validation_errors=[f"not a CONSTRUCT installation: missing AGENTS.md at {root}"],
        )

    build_dir = root / "views" / "build"
    ...
```

Returning a report rather than raising keeps CR-02's contract and `refresh_views`'s
never-raise guarantee intact. `main()`'s own check then becomes redundant and can be deleted.

### CR-04: The views-generate-data skill grants `Bash(bash *)` — arbitrary command execution

**File:** `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/SKILL.md:3`
**Issue:**

```yaml
allowed-tools: Bash(construct views *), Bash(bash *)
```

`Bash(bash *)` matches `bash -c '<anything>'`, so it is an unrestricted shell grant. It is
newly introduced by this phase (the prior frontmatter was
`Read, Write, Grep, Glob, Bash(python3 *), Bash(git add *), Bash(git commit *)`), and it is
the broadest grant in the entire skill set other than the bare `Bash` on `construct-up` /
`construct-down`. The skill's only legitimate `bash` use is one fixed wrapper script
(`SKILL.md:42`). Compare `construct-spike-run`, which correctly narrows to
`Bash(construct spike *)`, and `construct-views-reset`, which narrows to `Bash(rm *)`.

**Fix:** Narrow to the wrapper, or drop it entirely since Step 2's first form
(`construct views generate --install-root …`) is already covered:

```yaml
allowed-tools: Bash(construct views *), Bash(bash */run.sh *)
```

## Warnings

### WR-01: The refresh call sites execute un-guarded prologue code outside `refresh_views`' safety net

**File:** `src/construct/llm/daily_run.py:234-246,286`, `src/construct/llm/research_run.py:844-855`, `src/construct/llm/curation_run.py:991-1024`
**Issue:** The D-12 guarantee ("a failing refresh never flips a workflow's status") is
carried entirely by `refresh_views`' internal `try`. But each call site runs code *before
and after* that call which is not covered, and — unlike every other child invocation in
`daily_run` — the call itself is not wrapped:

- `daily_run.py:286` calls `_run_views_refresh(workspace)` bare, while `_run_research_child`,
  `_run_curation_child` and `_run_graph_child` are each wrapped in `try/except Exception`
  (`daily_run.py:205`). The call sits **between** the status computation and the receipt
  write (line 289-294), so anything raising inside `_run_views_refresh` — `Path(None)`,
  a `logger` handler error, an `ImportError` from a partially installed `construct.views`
  — aborts `run_daily_run` before the receipt is persisted and turns the whole capability
  into `success=False` via `_daily_result_to_operation`. That is exactly the outcome D-12
  forbids, reached through the one line that was not defended.
- `curation_run.py:1023` calls `_emit(...)` after the refresh, outside any guard, in a node
  whose entire contract is "cannot fail the run".

The existing tests only inject failures *inside* the generator, so this gap is untested.

**Fix:** Defend the call site, matching the sibling children:

```python
    # daily_run.run_daily_run
    try:
        _run_views_refresh(workspace)
    except Exception as exc:  # noqa: BLE001 — D-12: the refresh can never fail the cycle
        logger.warning("daily.run: views refresh raised: %s", _sanitize_error(exc))
```

Add a paired test that monkeypatches `construct.views.refresh.refresh_views` itself (not the
generator) to raise, and asserts status parity plus receipt survival.

### WR-02: `views.confirm_refresh` is inert — every caller discards the reason it populates

**File:** `src/construct/views/refresh.py:125,139`, `src/construct/llm/curation_run.py:1006-1011`, `src/construct/llm/daily_run.py:244-245`, `src/construct/llm/research_run.py:853-854`
**Issue:** This is distinct from the known "verbosity switch, not a pre-run confirmation"
decision. Granting that interpretation, the implementation still does nothing:
`refresh_views` puts `"✓ views updated"` into `RefreshOutcome.reason` on success, and then

- `curation_run.views_refresh_hook`'s **succeeded** branch does not set `reason` at all and
  builds `summary` from `files_written` — the string is dropped;
- `daily_run._run_views_refresh` logs only `outcome.status` on the non-failure branch —
  the string is dropped;
- `research_run.views_refresh` logs at `INFO` and returns `{}`.

So no user-facing surface anywhere ever shows `✓ views updated`, while
`adr-0005:135` states as contract that `confirm_refresh: true` "appends `✓ views updated`".
The ADR and the code disagree, and `test_views_refresh.py` never asserts the flag's effect.

**Fix:** Either carry the reason through (cheapest at the curation hook, which already has a
user-visible `summary`):

```python
    elif outcome.status == "succeeded":
        summary = f"views refreshed ({outcome.files_written} files written)"
        if outcome.reason:
            summary = f"{summary} — {outcome.reason}"
        result = CurationStepResult(..., reason=outcome.reason, summary=summary)
```

…or delete the `confirm` branch from `refresh.py` and amend the ADR row to say the flag is
not honoured in the Python layer. Add a test asserting whichever is chosen.

### WR-03: `_load_cached_workspace` trusts on-disk cache with no shape validation

**File:** `src/construct/views/generate.py:572-613`, consumed at `:236-238`
**Issue:** The cache loader guards only `json.JSONDecodeError` / `OSError`. Any structurally
wrong but syntactically valid JSON flows straight into the pipeline:

- `data.get("cards", [])` on a `data` that is a list raises `AttributeError`.
- Card dicts missing `id` reach `c["id"]` at `:456` and `parse_domains._compute_metrics:90,92`
  → `KeyError`.
- A non-int `confidence` reaches `sum(c["confidence"] for c in cards)` at
  `parse_domains.py:92` → `TypeError`.

Freshly parsed cards are safe (`parse_cards.py:37,40` coerce), but the cache path bypasses
the parser entirely, so `views/build/data/` — a directory the SPA, `views validate`, and
users all touch — is an unvalidated trust boundary. The resulting crash escapes `generate()`
and, per CR-02, escapes the capability handler too.

**Fix:** Validate the cached payload shape and fall back to a re-parse on mismatch (the
function already has a `return None` contract for exactly this):

```python
        if key == "cards":
            cards = data.get("cards") if isinstance(data, dict) else None
            if not isinstance(cards, list) or not all(
                isinstance(c, dict) and isinstance(c.get("id"), str)
                and isinstance(c.get("confidence"), int)
                for c in cards
            ):
                return None      # treat a malformed cache as a cache miss
            result[key] = cards
```

### WR-04: Dead duplicate validation tables in `generate.py`

**File:** `src/construct/views/generate.py:83-154`
**Issue:** `_FILE_MODEL_MAP` and `_PER_WS_FILES` are never referenced. Every adapter lambda
in them is duplicated verbatim as an inline dict literal inside `_validate_file_data`
(compare `:99-115` with `:452-467`, `:116-128` with `:475-486`, `:129-141` with `:495-507`,
`:142-153` with `:512-525`). Two copies of the writer/validator projection is precisely the
drift hazard the known writer-vs-validator divergence already demonstrates; a fix applied to
one copy will not reach the other. The `ViewsEnvelope` import at `:57` is likewise unused.

**Fix:** Delete both constants and the unused import, or — better — make
`_validate_file_data` iterate them so there is a single projection definition.

### WR-05: `callable` used as a type annotation

**File:** `src/construct/views/generate.py:83,98`
**Issue:** `list[tuple[str, type, callable]]` uses the builtin *function* `callable` where a
type is required. This is not a valid annotation (`typing.Callable` / `collections.abc.Callable`
is), and type checkers will flag it. It survives only because the constants are dead (WR-04).

**Fix:** If the constants are retained, use
`list[tuple[str, type[BaseModel], Callable[[dict], dict]]]` with
`from collections.abc import Callable`.

### WR-06: `parse_domains._read` warning label always resolves to `(root)`

**File:** `src/construct/views/lib/parse_domains.py:52`
**Issue:**

```python
"workspace": "(root)" if path.parent.name != path.name else path.parent.name
```

`path` is always a `.../domains.yaml`, so `path.name == "domains.yaml"` and
`path.parent.name` is a directory name — the two can never be equal, and the ternary's false
branch is unreachable dead code. Every YAML parse warning is labelled `(root)`, including
per-workspace failures from the loop at `:24`. Downstream, `generate.py:379` then prepends
the bogus workspace id, producing `"(root)/<ws>/domains.yaml: YAML parse error: …"` — a
warning that names two different locations for one file.

**Fix:** Pass the workspace id explicitly instead of deriving it:

```python
def _read(path: Path, label: str, warnings: list, ws_id: str = "(root)") -> dict:
    ...
        warnings.append({"workspace": ws_id, "file": label, "reason": f"YAML parse error: {e}"})
```

and call `_read(ws_yaml, f"{ws_id}/domains.yaml", warnings, ws_id)` at `:24`.

### WR-07: SKILL.md documents a wrapper path that does not exist

**File:** `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/SKILL.md:42`
**Issue:** The copy-pasteable command is

```bash
bash <install-root>/.claude/skills/views-generate-data/run.sh <install-root>
```

but the skill directory is `construct-views-generate-data/`, matching the `construct-`
prefix every other skill in `CONSTRUCT-CLAUDE-impl/claude/skills/` uses (and the name
`AGENTS.md:181` lists). An agent following Step 2's second form gets
`bash: …/views-generate-data/run.sh: No such file or directory`, which the failure-mode
table (`:76-77`) has no row for. `tests/contract/test_doc_command_references.py` cannot
catch this: its `_INVOCATION` regex only matches strings beginning `construct `.

**Fix:** Correct the path to `.claude/skills/construct-views-generate-data/run.sh`, and
extend the doc contract test with a check that documented `bash <…>/skills/<name>/run.sh`
paths resolve to a real file under `CONSTRUCT-CLAUDE-impl/claude/skills/`.

### WR-08: Doc-truth leftovers contradict ADR-0005's "no skill carries a refresh step"

**File:** `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md:130-141`, `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-reset/SKILL.md:31,42,71,83,98,127`, `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-build/SKILL.md:181`
**Issue:** ADR-0005:31 states "No skill, workflow document, or parent orchestrator carries a
refresh step," and ADR-0005:43 states the skill holds no Python and has no virtual
environment. Three documents still say otherwise:

- `construct-synthesis/SKILL.md` retains a full skill-owned refresh step, including the
  `views.confirm_refresh` handling and remediation prose the phase deleted from
  curation-cycle / research-cycle / daily-cycle. It is a fourth refresh path with no Python
  equivalent.
- `construct-views-reset/SKILL.md` deletes
  `.claude/skills/views-generate-data/.venv/` in six places — a directory D-09 removed.
  The reset skill now promises a cleanup that is a no-op and describes a "~5s extra one-time
  cost" bootstrap that no longer exists.
- `construct-views-build/SKILL.md:181` still says data refresh is triggered by "a v0.1 skill
  that hooks it (research-cycle, curation-cycle, synthesis)".

**Fix:** Either bring synthesis under the Python-layer rule (or record in ADR-0005 why it is
exempt), strip the `.venv` references from views-reset, and update views-build's note to
point at the workflow capabilities.

### WR-09: `construct views generate|validate` defaults are bound at import time

**File:** `src/construct/cli.py:871,911`
**Issue:** `install_root: Path = typer.Option(Path.cwd(), "--install-root")` evaluates
`Path.cwd()` when the module is imported, not when the command runs. In any process that
imports `construct.cli` before changing directory (test runners, embedded/long-lived hosts,
the MCP server importing the CLI for introspection — which `test_doc_command_references.py`
does), the default silently points at the wrong directory. Combined with CR-03's missing
install-root guard, the failure mode is "scaffolds a views tree in an unexpected place and
reports success."

**Fix:** Make the parameter optional and resolve at call time:

```python
    install_root: Path | None = typer.Option(None, "--install-root"),
) -> None:
    root = install_root or Path.cwd()
```

### WR-10: The MCP contract test cannot detect unsanitized handler exceptions

**File:** `tests/contract/test_mcp_contracts.py:153-172`
**Issue:** `test_every_mcp_handler_invokes_without_type_error` catches `TypeError` and then
`except Exception: pass`. That blanket clause is why CR-02 shipped: the views handler raising
`FileNotFoundError` through the MCP boundary passes this gate. The stated scope ("only
signature mismatch") is defensible, but there is no companion test asserting the
never-raise/never-leak property that five handlers in `catalog.py` were written to provide.

Separately, the views payload (`:127`) points `install_root` at the real fixture
workspace's parent, so this "contract" test executes the full generator and writes
`views/build/data/`, `version.json` and `_build_meta.json` into the fixture tree as a side
effect of a shim-signature check.

**Fix:** Add a sibling test asserting every MCP handler returns an `OperationResult` (rather
than raising) when handed a deliberately invalid path, and point the views payload at a
`tmp_path` so the contract test stops writing into fixtures.

### WR-11: Silent `except Exception: pass` on the SPA settings config read

**File:** `src/construct/views/generate.py:266-274`
**Issue:** Unlike `refresh.py::_read_views_config`, which logs a sanitized warning on an
unreadable config, this copy swallows every exception with a bare `pass` and no log. An
operator who sets `views.workspace_landing: wiki` and has a YAML typo gets `dashboard`
silently, with nothing in the warnings log and nothing on stdout. The two config readers in
the same package should not disagree on this.

**Fix:** Append to `_warnings` so it reaches the generation warnings log and
`GenerateReport.warnings`:

```python
        except Exception as exc:  # noqa: BLE001 — a bad config must not fail the build
            _warnings.append({
                "workspace": "(root)",
                "file": ".construct/config.yaml",
                "reason": f"unreadable views config: {type(exc).__name__}",
            })
```

## Info

### IN-01: Dead test helper

**File:** `tests/contract/test_views_contracts.py:82-84`
**Issue:** `_data_dir_for(rel)` ignores its argument and returns the module constant
`DATA_DIR`. Its docstring claims it resolves "global or per-workspace" directories, which it
does not do. It has no callers.
**Fix:** Delete it, or implement the per-workspace branch its docstring promises.

### IN-02: Module-level name shadowing in `cli.py`

**File:** `src/construct/cli.py:82 vs :909`, `:100 vs :213`
**Issue:** `views validate` (`:909`) rebinds the module global `validate` previously defined
by the top-level `validate` command (`:82`); `workflow status` (`:213`) likewise shadows
`status` (`:100`). Typer registration is unaffected because it happens at decoration time,
but `from construct.cli import validate` now silently yields the views command.
**Fix:** Name the functions distinctly (`views_validate`, `workflow_status`) and pass the
CLI name via `@views_app.command("validate")`.

### IN-03: Redundant `import json` inside a loop body

**File:** `src/construct/cli.py:959`
**Issue:** `json` is already imported at module scope (used at `:885`). The re-import sits
inside the per-file `try` inside the global-files loop, so it re-executes once per file.
**Fix:** Delete the local import.

### IN-04: `unwrap_payload` is not re-exported from the package

**File:** `src/construct/views/__init__.py:12-52`
**Issue:** `__init__.py` re-exports every model plus `schema_for` and `validate_data`, but
omits `unwrap_payload` — which `cli.py:929` and `tests/integration/test_views_generate.py:20`
both import from `.models` directly. The three-function helper set is split across two import
paths for no stated reason.
**Fix:** Add `unwrap_payload` to the import list and `__all__`.

---

_Reviewed: 2026-07-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
