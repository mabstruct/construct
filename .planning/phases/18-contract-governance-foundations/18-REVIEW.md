---
phase: 18-contract-governance-foundations
reviewed: 2026-07-30T18:45:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/src/components/ActivityList.jsx
  - CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md
  - CONSTRUCT-CLAUDE-spec/artifact-catalog.md
  - src/construct/capabilities/catalog.py
  - src/construct/capabilities/errors.py
  - src/construct/capabilities/registry.py
  - src/construct/cli.py
  - src/construct/llm/curation_run.py
  - src/construct/llm/daily_run.py
  - src/construct/llm/research_run.py
  - src/construct/mcp/server.py
  - src/construct/services/help.py
  - src/construct/services/knowledge.py
  - src/construct/ui/capability_runner.py
  - src/construct/ui/streamlit_app.py
  - src/construct/views/__init__.py
  - src/construct/views/contracts.py
  - src/construct/views/generate.py
  - src/construct/views/lib/parse_events.py
  - src/construct/views/models.py
  - tests/contract/test_canonical_write_boundary.py
  - tests/contract/test_capability_seam.py
  - tests/contract/test_mcp_contracts.py
  - tests/contract/test_views_contracts.py
  - tests/integration/test_knowledge_cli.py
  - tests/integration/test_surface_honesty.py
  - tests/integration/test_surface_parity.py
  - tests/integration/test_views_generate.py
  - tests/llm/test_curation_run.py
  - tests/llm/test_research_run.py
  - tests/llm/test_views_refresh.py
  - tests/unit/test_capability_registry.py
findings:
  critical: 5
  warning: 13
  info: 0
  total: 18
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-07-30T18:45:00Z
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

Phase 18 routes every surface through one validating seam and adds real contract
governance (id-keyed decisions, checkpoint ETag, single file→model table, canonical
write boundary). The structural work holds up: `views/contracts.py` really is the
only enumeration left (`grep` finds no third table; `generate.contract_for` and
`validate_build_data` both read it), the `Command(resume=…)` envelope is used on
every resume path in both graphs, and the contract suite passes (171 passed,
17 documented `**kwargs` skips).

The defects are concentrated where the phase's own claims are strongest, and four of
the five blockers were reproduced against the running code rather than inferred:

1. **The MCP surface drops the entire error channel.** `_serialize_result` returns
   `OperationResult` with its `errors` list still holding `OperationError`
   *dataclasses*; `json.dumps` then raises inside the handler's own `try`, so every
   failing MCP call answers `{"error": "Object of type OperationError is not JSON
   serializable"}`. Parity for the failure case — the case this phase is about — is
   not achieved, and no test covers it (the parity tests only exercise seam-level
   rejections, which never reach `_serialize_result`).
2. **`apply_connections` is default-allow.** Its two siblings require an exact
   `"promote"` / `"archive"` token; the connection apply node writes on *any* token
   that is not literally `"reject"`. `{"<pid>": "skip"}` — the vocabulary the
   research gate teaches — creates a canonical edge.
3. **`knowledge.card.edit` still blanks fields**, just via `""` rather than `None`.
   Both documented guards filter `None` only. Verified: `{"summary": ""}` deleted the
   card's Summary prose, `{"title": ""}` blanked the title. `construct_edit_card` is
   an MCP tool.
4. **Write capabilities have no workspace-marker guard**, while the views
   capabilities gained one. Verified: `construct_create_card` with
   `workspace=/tmp/definitely-not-a-workspace-9x8/secret-dir` created `cards/` and
   `log/` and wrote files there.
5. **The seam's ordering guarantee is depth-1 only.** Verified against
   `workspace.init`: the same nested `domain` dict with two key orders produces two
   different reason strings — the exact contract fork `from_validation_error`'s
   docstring says it closes.

D-21, D-03, D-23, D-24 and the `**kwargs` binding skip were treated as accepted and
are not reported.

## Critical Issues

### CR-01: MCP returns a serializer TypeError instead of the capability's errors

**File:** `src/construct/mcp/server.py:13-20`, `src/construct/mcp/server.py:31-37`
**Issue:** `_serialize_result` takes the `__dataclass_fields__` branch for
`OperationResult` (a plain dataclass) and returns `errors` as a list of
`OperationError` dataclass instances. `json.dumps(serialized, indent=2)` on line 35
then raises `TypeError`, which the surrounding `except Exception` converts into
`{"error": "Object of type OperationError is not JSON serializable"}`. Reproduced:

```
>>> _serialize_result(OperationResult(success=False, errors=[OperationError('f','r','s')]))
{'success': False, ..., 'errors': [OperationError(field='f', reason='r', suggestion='s')], ...}
>>> json.dumps(...)  ->  TypeError: Object of type OperationError is not JSON serializable
```

Every MCP tool that reports structured failure is affected — including the newly
registered `construct_views_validate_data`, whose *entire purpose* is returning
per-file errors, and `_views_generate_handler` / `_views_validate_handler`, which
were written specifically to put reasons in `errors`. The CLI renders those errors;
MCP renders a serializer bug. The failure is also silent: the tool call still
returns 200-equivalent JSON, so an agent reads a bogus reason and cannot tell a
validation failure from an infrastructure fault. Phase 19's HTTP adapter will
inherit this if it reuses `_serialize_result`.
**Fix:** serialize nested dataclasses:

```python
from dataclasses import asdict, is_dataclass

def _serialize_result(result: Any) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)          # recurses into OperationError
    ...
```

and add a parity case whose capability *fails with errors populated* (e.g.
`views.validate_data` against a corrupted data file), asserting the CLI and MCP
reasons still match.

### CR-02: `apply_connections` writes a canonical edge for any decision token that is not exactly `"reject"`

**File:** `src/construct/llm/curation_run.py:1316-1345`
**Issue:** The promotion node requires `decision == "promote"` (line 1255) and the
archive node requires `decision == "archive"` (line 1386) — both default-deny. The
connection node inverts that:

```python
if decision == "reject":
    rejected.append(key); ...; continue
try:
    conn_type = ConnectionType(payload.get("connection_type"))
    ...
    res = add_connection(...)          # reached by EVERY other token
```

`_normalize_decision` (line 1040) passes any unrecognised token through verbatim as
`str(value)`, so `{"<pid>": "skip"}`, `{"<pid>": "hold"}`, `{"<pid>": "no"}` or a
typo all authorise a write to `connections.json`. `"skip"` is not hypothetical: it
is the reject vocabulary of the *research* review gate, whose decision map an agent
(or `daily.run`'s operator) reasonably reuses. This is the same class as T-18-03 —
"a payload the user did not intend performed a canonical write" — surviving in the
one apply node nobody re-checked. No test exercises a non-`reject`, non-recommended
token, so the suite is green.
**Fix:** make the connection node default-deny like its siblings:

```python
if decision not in ("approve", "connect"):   # or whatever the approved vocabulary is
    rejected.append(key)
    events.append(_emit(workspace, "gate_review_rejected", key, "connection rejected"))
    continue
```

and add a red test: a queue of one connection proposal resumed with
`{"<pid>": "skip"}` must leave `connections.json` byte-identical.

### CR-03: `knowledge.card.edit` destroys stored title/prose when a field arrives as `""`

**File:** `src/construct/capabilities/catalog.py:1224-1238`, `src/construct/cli.py:1373-1394`
**Issue:** Both documented guards test `is not None` only:

```python
for field in ("title", "confidence", "source_tier", "lifecycle"):
    value = kwargs.get(field)
    if value is not None:            # "" passes
        updates[field] = value
summary = kwargs.get("summary")
if summary is not None:              # "" passes
    updates["_summary"] = summary
```

`CardEditInput.title`/`summary` are `str | None` with no `min_length`, so the seam
accepts `""`. Reproduced against a copy of the checked-in fixture:

```
invoke("knowledge.card.edit", {"workspace": ws, "card_id": cid, "summary": ""})
  RESULT True  "Card '…' updated"
  body before: '## Summary\n\nSeed card from ingested note: …\n\n## Evidence…'
  body after : '## Summary\n## Evidence…'          # prose deleted
invoke("knowledge.card.edit", {..., "title": ""})  ->  title: ''
```

`construct_edit_card` is an MCP tool, so this is agent-reachable. `cli.py:1373`
asserts "Guard 2 alone is sufficient today" — it is not — in a comment that also
records that this repository has destroyed user prose twice through this class of
defect, and `tests/integration/test_knowledge_cli.py` pins only the `None` variant.
**Fix:** treat empty-as-unset for the two free-text fields and reject rather than
silently blank:

```python
for field in ("title", "lifecycle"):
    value = kwargs.get(field)
    if value is not None and str(value).strip() != "":
        updates[field] = value
summary = kwargs.get("summary")
if summary is not None and summary.strip() != "":
    updates["_summary"] = summary
```

Better still, declare the constraint on the model (`title: str | None = Field(None,
min_length=1)`) so the seam rejects it with a reason instead of accepting a no-op,
and extend `test_card_edit_title_only_leaves_every_unnamed_field_byte_identical`
with an explicit `--summary ""` / `{"summary": ""}` arm.

### CR-04: agent-supplied `workspace` on write capabilities has no marker guard — arbitrary directory creation and file write

**File:** `src/construct/capabilities/catalog.py:333-407` (card/connection records), `src/construct/capabilities/catalog.py:471-482` (`ingest.source`)
**Issue:** `views.generate_data` / `views.validate_data` gained
`install_root_error()` precisely because "registration is what makes `install_root`
agent-supplied over MCP, so the marker check stopped being an internal convenience
and became a boundary control" (`views/generate.py:86-105`). The MCP-exposed *write*
capabilities — `construct_create_card`, `construct_add_connection`,
`construct_ingest_source`, `construct_edit_card` — took no such guard, and
`Path` accepts any absolute or `../`-relative value. Reproduced:

```
invoke("knowledge.card.create", {"workspace": "/tmp/definitely-not-a-workspace-9x8/secret-dir", ...})
  -> OperationResult(success=True, message="Card 't' created as t")
  -> /tmp/definitely-not-a-workspace-9x8/secret-dir/cards/t.md
  -> /tmp/definitely-not-a-workspace-9x8/secret-dir/log/events.jsonl
```

An MCP client therefore has a primitive for creating directories and writing
attacker-influenced markdown/JSONL anywhere the process can write, with a
`success: true` receipt. The same reasoning that made the views guard a boundary
control applies verbatim here, and this phase is where those call sites became
seam-dispatched.
**Fix:** add the workspace analogue of `install_root_error` and call it first in
each write shim (and in `_ingest_source_shim`):

```python
def workspace_error(workspace: Path | str) -> str | None:
    root = Path(workspace)
    if not root.is_dir():
        return "workspace is not an existing directory"
    if not (root / "domains.yaml").is_file():      # or the agreed marker
        return "not a CONSTRUCT workspace: missing domains.yaml"
    return None
```

returning an `OperationResult(success=False, …)` whose reason names no path (the
`install_root_error` convention), and pin it with a test mirroring
`test_views_validate_data_refuses_a_non_install_root_without_naming_a_path`.

### CR-05: the seam's payload-independent error ordering does not hold for nested models

**File:** `src/construct/capabilities/errors.py:88-103`
**Issue:** `from_validation_error`'s docstring states the errors are put into "a
**total order that does not depend on the payload**". `_error_order_key` only reads
`error["loc"][0]`, so every error under one declared field ties on `(0, index, "")`
and falls back to pydantic's order — which for `extra_forbidden` is *payload key
insertion order*. Reproduced against `workspace.init`:

```
{'root': …, 'domain': {..., 'zz': 1, 'aa': 2}}
  -> '… domain.zz: Unexpected keyword argument; domain.aa: Unexpected keyword argument'
{'root': …, 'domain': {..., 'aa': 2, 'zz': 1}}
  -> '… domain.aa: Unexpected keyword argument; domain.zz: Unexpected keyword argument'
```

Two callers sending the same logical payload receive two different reason strings —
the fork GOV-01 exists to close. `WorkspaceInitInput.domain` is the phase's own
example of a typed nested payload (T-18-13), and
`test_multi_error_reason_does_not_depend_on_payload_key_order` only covers
top-level keys, so the hole is unguarded.
**Fix:** order on the whole `loc` tuple, not just its head:

```python
def key(error):
    loc = tuple(str(item) for item in error.get("loc", ()))
    head = loc[0] if loc else ""
    rank = (0, declared[head]) if head in declared else (1, head)
    return (*rank, loc[1:])          # tail sorts undeclared nested keys by name
```

(note the tuple members must be made comparable — normalise ints to strings), and
extend the ordering test with a nested-payload arm using `workspace.init`.

## Warnings

### WR-01: `construct init` bypasses the seam entirely; `workspace.init` has no production caller

**File:** `src/construct/cli.py:60-80`, `src/construct/capabilities/catalog.py:301-311`
**Issue:** Every other CLI command was converted to `get_registry().invoke(...)`, but
`init` still calls `initialize_workspace(path, domain)` directly (line 76). The
`workspace.init` record declares `cli_name="init"` and no `mcp_tool_name`, so — after
the conversion — it has zero callers outside tests: the typed-`DomainInitInput`
boundary check T-18-13 added never runs on the only path a user takes. The guard in
`test_capability_seam.py::test_no_registry_aware_module_calls_a_handler_directly`
cannot see this, because it only detects `X.handler(...)`, not a surface calling the
underlying service function.
**Fix:** dispatch it — `get_registry().invoke("workspace.init", {"root": path,
"domain": {...}})`, catching `CapabilityInputError` alongside `WorkspaceInitError` —
or delete the record and stop advertising a capability nothing reaches. Consider
widening the AST guard to flag direct calls to any function bound as a
`CapabilityRecord.handler`.

### WR-02: the GOV-05 honest verdict is applied to one renderer out of three

**File:** `src/construct/cli.py:580-590`, `src/construct/cli.py:890-901`
**Issue:** `_verdict_line` exists to stop "an honest `status: degraded` line and an
unqualified `✓ …` in the same output block", and `_emit_curation_result` uses it.
`_emit_run_result` (research) and `_emit_daily_result` (daily) still print
`typer.echo(f"✓ {result.message}")` — while `_daily_result_to_operation` and
`_run_result_to_operation` both populate `outcome`. A degraded `daily run` therefore
prints `status: degraded` and `✓ Daily cycle degraded.` in the same block: exactly
the defect GOV-05 names, in the composition command that fans out over both graphs.
`test_surface_honesty.py` covers curation only.
**Fix:** replace both `f"✓ {result.message}"` calls with `_verdict_line(result)` and
add the daily/research arms to `test_degraded_human_output_has_no_unqualified_success_verdict`.

### WR-03: raw exception text and filesystem paths cross the MCP boundary

**File:** `src/construct/mcp/server.py:36-37`
**Issue:** `except Exception as exc: return json.dumps({"error": str(exc)})` renders
whatever a handler raised. Several MCP-reachable handlers do not sanitize:
`workspace.status` (`WorkspaceLoader.inspect_workspace`), `knowledge.*`, and
`graph.status`, whose *successful* `OperationResult.message` was observed as
`[Errno 2] No such file or directory: '/tmp/…/connections.json'`. The catalog's
views shims go to some length to emit class names only "because the MCP surface must
not receive raw exception text (which carries filesystem paths)"; the generic
fallback undoes that for every other capability.
**Fix:** sanitize at the boundary — `{"error": f"{capability.id} failed: {type(exc).__name__}"}`
— and log the full text to stderr. Separately, stop interpolating paths into
`graph_status`'s message.

### WR-04: the ordering guarantee is opt-in, so Phase 19 can bypass it

**File:** `src/construct/capabilities/errors.py:50-56`
**Issue:** `model` defaults to `None`. `registry.invoke` passes it, but the classmethod
is public and the HTTP adapter Phase 19 generates (or any future surface that builds
its own `CapabilityInputError`) gets payload-ordered reasons by simply omitting an
argument. A guarantee that a caller can drop is a convention, not a contract.
**Fix:** make `model` required (`model: type[BaseModel]`) — every call site already
has it — or move reason construction entirely inside the seam and stop exporting the
constructor.

### WR-05: the canonical-write guard grants its exemptions by substring match

**File:** `tests/contract/test_canonical_write_boundary.py:150-181`
**Issue:** `_direct_calls` is careful to use the AST specifically because "a docstring
that names `edit_card` is prose". `exemption_for` then decides the *exemption* with
`"StateGraph(" in source and "interrupt(" in source` and `"CapabilityRecord(" in
source` — raw text, comments and docstrings included. A new module can therefore
exempt itself from GOV-04 with one comment line mentioning both strings, and the
`test_guard_detects_a_planted_canonical_writer` fixture would not notice (its gated
graph plants real code). This weakens the phase's headline invariant more than the
recorded `UNRESOLVED_DIRECT_CALLERS` baseline does.
**Fix:** derive rules 2 and 3 from the AST — e.g. an `ast.Call` to `StateGraph` and
an `ast.Call` to `interrupt` at module scope, and an `ast.Call` to
`CapabilityRecord` — and add a planted module that mentions the strings only in a
comment, asserting it is still caught.

### WR-06: `decisions` / `approve_all` / `reject_all` have silent precedence instead of mutual exclusion

**File:** `src/construct/llm/curation_run.py:317-343` and `1635-1658`, `src/construct/llm/research_run.py:138-156` and `1137-1155`
**Issue:** The CLI refuses more than one of the three (`cli.py:823`, `cli.py:636`), but
the *models* do not, so an MCP or HTTP caller sending `approve_all=True,
reject_all=True` silently gets reject-all (checked first), and one sending
`decisions={...}, approve_all=True` silently gets the map. For a review gate that
authorises canonical writes, "the surface with the stricter validation is the one an
agent does not use" is the wrong way round.
**Fix:** add a `model_validator(mode="after")` to both review models rejecting more
than one of the three, and delete the now-redundant CLI pre-check (or keep it for the
nicer message).

### WR-07: the Streamlit Capability Runner submits `0` and `""` for every unnamed optional field

**File:** `src/construct/ui/capability_runner.py:86-95`, `src/construct/ui/capability_runner.py:113-119`
**Issue:** `_render_form_fields` always emits a value for every property: `int_val =
int(default) if default is not None else 0` for numbers and `str(default) if default
is not None else ""` for strings. With the seam now validating, `knowledge.card.edit`
from the runner is rejected outright (`confidence: Input should be greater than or
equal to 1` — verified), i.e. the capability is unusable from the UI; and for
capabilities without `ge=` constraints the `""` values are what makes CR-03
reachable from a browser form. The float branch is also wrong: `step=0.1` is paired
with an `int` value, and `int(default)` truncates a float default.
**Fix:** omit a field from the payload when the widget was left at its unset state
(exclude-unset semantics at the call site, mirroring `cli.py:1373`), use
`st.number_input(value=None)` for optional numerics, and pick the step from the
schema type consistently with the value type.

### WR-08: `typer.Option(Path.cwd(), …)` still captures the working directory at import time in ~15 commands

**File:** `src/construct/cli.py:133`, `239`, `267`, `324`, `362`, `410`, `1119`, `1193`, `1246`, `1264`, `1305`, `1346`, `1407`, `1468`, `1504`, `1533`, `1559`
**Issue:** The views commands document WR-09 and take `None` + `Path.cwd()` at call
time for exactly this reason. Every other `--workspace` default was left as an
import-time `Path.cwd()`, so any host that imports `construct.cli` before
`chdir` (test runners, long-lived processes, anything introspecting the CLI) gets a
stale default — and for write commands a stale *workspace* default is worse than a
stale install root.
**Fix:** apply the same pattern the views commands use:
`workspace: Path | None = typer.Option(None, "--workspace", "-w")` plus
`workspace = workspace or Path.cwd()` in the body.

### WR-09: the workflow refresh derives an install root by `.parent` and never marker-checks it

**File:** `src/construct/llm/curation_run.py:1443`, `src/construct/llm/research_run.py:968`, `src/construct/llm/daily_run.py:254`
**Issue:** All three do `install_root = Path(workspace_path).parent` and hand it to
`refresh_views`, which calls `generate(root)` (`views/refresh.py:132`) without
`install_root_error`. `install_root_error`'s docstring says "Every entrypoint that
can be handed an arbitrary path must call this BEFORE `generate()`". `workspace_path`
is agent-supplied over MCP, and `Path(".").parent == Path(".")`, so a relative
workspace argument points the generator at the workspace itself — the "discovers zero
workspaces and publishes an empty build that looks like a success" failure the same
comments warn about. Only `refresh_views`' `views/build` existence gate bounds it.
**Fix:** resolve first (`Path(workspace_path).resolve().parent`) and call
`install_root_error` on the result, reporting a `skipped` step with the guard reason
when it fails.

### WR-10: apply nodes can put `None` into `list[str]` result buckets, failing the whole review after writes landed

**File:** `src/construct/llm/curation_run.py:1247-1264`, `src/construct/llm/curation_run.py:1385-1392`
**Issue:** `card_id = entry.get("payload", {}).get("card_id")` is `None` when a
proposal payload lacks the key, and the value is appended unchecked into
`escalated` / `rejected` / `no_op`. `CurationRunResult` declares those as
`list[str]`, so the run ends in a `ValidationError` that the catalog shim reports as
`"curation.review failed: ValidationError"` — after `apply_promotions` /
`apply_connections` have already written to canonical truth. The same pattern exists
in `decay_scan` (`candidate_ids.append(card.get("id"))`, line 694).
**Fix:** skip or substitute a placeholder for an id-less proposal and record it in
`failed_writes` with a reason, e.g. `card_id = entry.get("payload", {}).get("card_id")
or "<unnamed proposal>"`.

### WR-11: a fixture-drift assertion no longer proves what it claims

**File:** `tests/contract/test_canonical_write_boundary.py:306`
**Issue:** `assert "handler(" in source, "fixture drift: the runner no longer
dispatches a capability"` is satisfied by the function name `_invoke_handler(` and by
the docstring that describes the retired pattern — `capability_runner.py` no longer
calls `cap.handler(...)` at all (that is the point of the phase). The assertion
passes for the wrong reason and would keep passing if the runner stopped dispatching
altogether.
**Fix:** assert the real property: `assert "get_registry().invoke(" in source`.

### WR-12: `research_run` imports ten private names from `curation_run`

**File:** `src/construct/llm/research_run.py:44-55`
**Issue:** `_check_coverage`, `_checkpoint_id`, `_decision_map`, `_ensure_proposal_ids`,
`_new_proposal_id`, `_unwrap_resume`, `_validate_proposal_id`, `_wrap_resume` are all
underscore-private members of another module. Sharing one implementation is right
(the docstring's reasoning is sound); reaching across a module's privacy boundary to
do it means the "private" marker now lies, and any refactor of `curation_run`'s
internals silently breaks the research graph's resume path — the one place a
regression means writes applied against the wrong queue.
**Fix:** move the shared primitives into a public module (e.g.
`construct/llm/review_protocol.py`) that both graphs import, leaving `curation_run`
importing them too.

### WR-13: dead imports and a computed-then-discarded schema

**File:** `src/construct/capabilities/registry.py:4-5`, `src/construct/mcp/server.py:10`, `src/construct/capabilities/registry.py:97-107`
**Issue:** `registry.py` imports `Sequence` (unused) and `field` from `dataclasses`
(unused); `mcp/server.py` imports `OperationResult` and never references it.
`list_mcp_tools()` computes `input_schema` for every capability and
`create_server()` ignores it (the D-21 situation), then re-resolves each record with
`get_by_mcp_name`, an O(n²) scan over a dict the caller already holds. Harmless
today, but it is the code Phase 19's generator is expected to be shaped from, so the
dead pieces are worth removing before they get copied.
**Fix:** drop the unused imports; have `create_server` iterate `registry.list()`
directly and keep `list_mcp_tools` as the discovery projection.

---

_Reviewed: 2026-07-30T18:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
