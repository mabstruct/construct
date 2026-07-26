# Phase 18: Contract & Governance Foundations - Pattern Map

**Mapped:** 2026-07-26
**Files analyzed:** 20 (3 new test files, 1 deletion, 16 modified)
**Analogs found:** 19 / 20

This phase creates almost no new files — it repairs existing ones. The "analog" for a
modified file is therefore usually **a sibling in the same file that already does the thing
correctly** (the RESEARCH § Don't Hand-Roll insight: "the defects are consistently *two*
correct implementations that never learned about each other"). Those in-file analogs are
called out explicitly below because they are what the implementer should copy.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/integration/test_surface_parity.py` **(new)** | test (contract/parity) | request-response | `tests/contract/test_card_list_cli_mcp.py` | exact |
| `tests/contract/test_capability_seam.py` **(new)** | test (registry introspection) | batch/transform | `tests/contract/test_mcp_contracts.py` | exact |
| `tests/integration/test_surface_honesty.py` **(new)** | test (cross-surface rendering) | request-response | `tests/contract/test_curation_run_cli_mcp.py` + `test_card_list_cli_mcp.py::test_cli_mcp_schema_parity` | role-match |
| `src/construct/capabilities/registry.py` (add `invoke`) | registry/seam | request-response | `mcp/server.py:30-38` (already does step 3) | partial (in-repo half-implementation) |
| `src/construct/mcp/server.py` (pure insertion) | surface adapter | request-response | itself — `:40-44` vs `registry.py:63` | exact |
| `src/construct/capabilities/catalog.py` (`extra="forbid"` ×14, `views.validate` record, 5 mismatches, shim retirement) | config/registry records | CRUD | `catalog.py:314-323` (`knowledge.card.list` record) + `catalog.py:145-147` | exact |
| `src/construct/cli.py` (call-site normalization, `views validate` → capability, degraded/escalated renderers) | controller | request-response | `cli.py` `views generate` command `:869-924` | exact |
| `src/construct/views/models.py` (13 models: renames + `extra="ignore"` + `events` conform + 2 new models) | model | transform | `views/models.py` `DomainRecord`/`ArticleRecord` (`:97-170`) — models already conformed to parser output in a prior pass | exact |
| `src/construct/views/generate.py` (delete adapter tables, direct validate-before-write) | service (writer) | file-I/O | `generate.py::_write_atomic` `:518-522` + `install_root_error` `:175-194` | exact |
| `src/construct/llm/curation_run.py` (`proposal_id`, id-keyed decisions, ETag, escalate event, conditional approve event) | service (workflow) | event-driven | `curation_run.py::_validate_run_id` `:64-77`, `_emit` `:311-327`, `_card_lifecycle_map` `:799-815` | exact |
| `src/construct/llm/research_run.py` (same GOV-02/03 treatment; **plus `DigestRecord` write path `:644`**) | service (workflow + writer) | event-driven + file-I/O | `curation_run.py` (the sibling graph) | exact |
| `src/construct/ui/gate_review.py` **(deleted)** | component | — | — | n/a |
| `src/construct/ui/streamlit_app.py` (`:46`, `:48`) | config/routing | — | `streamlit_app.py:44-48` (the two surviving `st.Page` lines) | exact |
| `src/construct/ui/capability_runner.py:130` | component | request-response | `mcp/server.py:33` | role-match |
| `src/construct/services/help.py:141` | service (internal caller) | request-response | `mcp/server.py:33` | role-match |
| `.../construct-views-scaffold/template/src/components/ActivityList.jsx` | component (SPA reader) | transform | sibling SPA components already on writer names (`Artifacts.jsx:211`, `Wiki.jsx:214`) | role-match |
| `tests/integration/test_views_generate.py:285` (guard replacement) | test | file-I/O | `test_views_generate.py::test_generated_card_connections_are_id_strings` `:85-120` | exact |
| `tests/contract/test_views_contracts.py` | test | transform | itself (existing rejection-mechanics tests) | exact |
| `tests/llm/test_curation_run.py` (extend: decisions, etag, migration, event count) | test | event-driven | `tests/llm/test_research_run.py:758-773` (`test_gate_review_is_interrupt_only`) | exact |
| `tests/llm/test_research_run.py` (extend: GOV-04 source guard) | test | event-driven | same file `:758-773` | exact |

---

## Pattern Assignments

### `tests/integration/test_surface_parity.py` (new — GOV-01 / D-08)

**Analog:** `tests/contract/test_card_list_cli_mcp.py`

**Module docstring + Wave-status convention** (lines 1-11) — this project writes the RED/GREEN
wave status into the docstring; copy the form:

```python
"""Contract tests for knowledge.card.list CLI + MCP parity (Phase 16, D-01).
...
Wave 2 status: RED until Task 2 registers ``knowledge.card.list`` ...
``test_mcp_no_hardcoded_card_list`` is the GREEN guardrail proving Task 2 must NOT
hand-wire the MCP server ...
"""
```

**Imports + module-level table** (lines 12-27) — the `_CAPS` dict is the existing shape of
"a fixed table of cases"; D-08's `(capability, payload)` table extends it:

```python
from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from construct.capabilities.catalog import get_registry
from construct.cli import app
from construct.mcp import server as mcp_server
from construct.mcp.server import _serialize_result, create_server

runner = CliRunner()

_CAPS = {"knowledge.card.list": "construct_list_cards"}
```

**Fixture-workspace helper** (lines 30-60) — build the fixture through real services, never by
hand-writing files:

```python
def _card_workspace(tmp_path: Path) -> Path:
    """A scaffolded workspace holding two cards."""
    from construct.services.init import DomainInitInput, initialize_workspace
    from construct.services.knowledge import create_card

    ws = tmp_path / "workspace"
    initialize_workspace(ws, DomainInitInput(domain_id="test-domain", ...))
    for card_id, title in (("card-a", "Card A"), ("card-b", "Card B")):
        create_card(ws, {"id": card_id, "title": title, ...})
    return ws
```

**Core parity pattern** (lines 146-166) — this is the existing CLI↔MCP differential, and the
exact shape D-08 broadens. Note it already asserts key-set equality both at the envelope and
per-record level:

```python
def test_cli_mcp_schema_parity(tmp_path: Path) -> None:
    ws = _card_workspace(tmp_path)

    cap = get_registry().get("knowledge.card.list")
    mcp_serialized = _serialize_result(cap.handler(workspace=ws))

    cli = runner.invoke(app, ["knowledge", "card", "list", "--workspace", str(ws), "--json"])
    assert cli.exit_code == 0, cli.stdout
    cli_payload = json.loads(cli.stdout)

    assert set(cli_payload.keys()) == set(mcp_serialized.keys())
```

**Deltas the new file must apply (do NOT copy these from the analog):**
1. The analog's MCP arm calls `cap.handler(...)` **directly**. D-08 requires the *real MCP
   dispatch path* — drive the closure registered by `create_server()`, not `cap.handler`.
2. The analog's CLI arm is `CliRunner` (in-process). RESEARCH Pitfall 5: use
   `subprocess` + `.venv/bin/python -m construct.cli` for at least the error-shape rows;
   `CliRunner` may cover breadth only. The registry singleton is cached in a module global
   (`catalog.py:988-993`), so an in-process test shares it.
3. Add the unknown-field row: same payload + `{"bogus": 1}` must be rejected identically on
   both arms.

**Anti-pattern guard to copy verbatim in spirit** (lines 112-120) — the "server must contain no
capability-specific wiring" check; keep it, since GOV-01 must not restructure `mcp/server.py`:

```python
def test_mcp_no_hardcoded_card_list() -> None:
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "construct_list_cards" not in src
```

---

### `tests/contract/test_capability_seam.py` (new — GOV-01 audit as a permanent guard)

**Analog:** `tests/contract/test_mcp_contracts.py`

**Docstring stating the two layers** (lines 1-14) — reuse this framing; the new file is
layer 2 generalized to all 28 capabilities:

```python
"""Contract tests for MCP server tool definitions.

1. **Schema-shape tests** assert the advertised MCP tool definitions exist ...
   which is precisely the CI blind spot that let RT-03 (handlers raising TypeError
   on their own advertised kwargs) ship undetected.
2. **Handler-invocation tests** (D-08.1) close that blind spot ...
"""
```

**Registry-introspection pattern** (lines 33-42):

```python
def test_mcp_tools_match_registry() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    assert len(mcp_tools) >= 4
    for tool in mcp_tools:
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
```

**Cardinality-over-membership pattern** — the analog has an explicit `expected = {...}` name
set (`:53-80`). Per D-04/D-08/WR-01, the new file must assert **counts**, e.g.
`len([c for c in reg.list() if c.input_model.model_config.get("extra") == "forbid"]) == len(reg)`
and `len(reg) == 29`, not a name set. Use `test_mcp_tool_count`'s structure but flip the
assertion from `tool_names == expected` to a count.

**`extra="forbid"` rejection pattern** — from `test_card_list_cli_mcp.py:85-94`:

```python
def test_input_model_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CardListInput(workspace=".", bogus=1)
```

**Model↔handler binding audit (Finding G3, new but mechanical):** use `inspect.signature` over
`get_registry().list()` comparing `input_model.model_fields` to handler params. The
positional-rejection guard already exists in
`tests/contract/test_curation_run_cli_mcp.py:54-58` and is the closest existing shape:

```python
def test_shims_reject_positional_args() -> None:
    reg = get_registry()
    for cap_id in _CAPS:
        with pytest.raises(TypeError):
            reg.get(cap_id).handler("positional")
```

---

### `tests/integration/test_surface_honesty.py` (new — GOV-05 / D-15 / D-16)

**Analog:** `tests/contract/test_curation_run_cli_mcp.py` (fixture + dual-surface driving) and
`test_card_list_cli_mcp.py::test_cli_mcp_schema_parity` (the surface comparison).

**Fixture pattern** (lines 36-40) — reuse the shared LLM-test workspace builder rather than
writing a new one:

```python
from tests.llm.conftest import create_test_workspace

def _run_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    return ws
```

**Table-driven rows (D-16 discretion):** one row per surface — CLI human output, CLI `--json`,
MCP serialized result — driven against (a) a run forced degraded, (b) a run with an escalated
item. Assert on **rendered text**, not the result model: the defect is in
`cli.py:687-692` where `✓ {result.message}` prints for `success=True` while
`_render_curation_result` honestly printed `status: degraded` two lines earlier.

**D-15 regression row:** assert `exit_code == 0` for the degraded run — the Phase 11 contract is
preserved, not changed. Model it on the exit-code assertion style used at
`test_views_generate.py:316` (`assert validated.exit_code == 1, validated.stdout`).

**No analog exists for:** the degraded-run and escalated-item fixtures themselves (Wave 0 gap).
Closest starting point is `create_test_workspace` plus forcing the state channels
`escalated` / `status` documented at `curation_run.py:112,117`.

---

### `src/construct/capabilities/registry.py` — add `invoke()` (GOV-01 / D-07)

**Analog:** the correct half already exists in `mcp/server.py:30-38`; the missing half is
`registry.py:36-40`'s `get`.

**`get` — the existing error convention to preserve** (`registry.py:36-40`):

```python
def get(self, cap_id: str) -> CapabilityRecord:
    if cap_id not in self._capabilities:
        available = ", ".join(sorted(self._capabilities))
        raise KeyError(f"Capability '{cap_id}' not found. Available: {available}")
    return self._capabilities[cap_id]
```

**The schema that is computed and then discarded** (`registry.py:55-65`) — `invoke` must use
`input_model`, and `mcp/server.py` must start passing `entry["input_schema"]`:

```python
def list_mcp_tools(self) -> list[dict]:
    tools: list[dict] = []
    for cap in self._capabilities.values():
        if cap.mcp_tool_name is None:
            continue
        tools.append({
            "name": cap.mcp_tool_name,
            "description": cap.description,
            "input_schema": cap.input_model.model_json_schema(),
        })
    return tools
```

**Target shape** (RESEARCH Pattern 1) — three lines, `from __future__ import annotations` at
module top already present, full type annotations per AGENTS.md:

```python
def invoke(self, cap_id: str, payload: dict) -> Any:
    cap = self.get(cap_id)
    model = cap.input_model.model_validate(payload)
    return cap.handler(**model.model_dump())
```

**Error-conversion pattern (AGENTS.md § Error Handling):** convert `pydantic.ValidationError`
into a domain error with `raise NewError(...) from exc` at this boundary — the seam is the
boundary. The CLI then renders it per its own convention (`typer.echo(f"ERROR {exc}")` +
`raise typer.Exit(code=1)`), and MCP renders it via its existing `{"error": str(exc)}` branch.
Both surfaces must produce the **same reason string**, which is what D-08 asserts.

---

### `src/construct/mcp/server.py` — pure insertion (GOV-01)

**Analog:** itself. Lines 30-44 as they stand:

```python
def make_handler(capability=cap) -> Any:
    def handler(**kwargs: Any) -> str:
        try:
            result = capability.handler(**kwargs)          # ← becomes registry.invoke(...)
            serialized = _serialize_result(result)
            return json.dumps(serialized, indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)})
    return handler

app.add_tool(
    fn=make_handler(),
    name=entry["name"],
    description=entry["description"],
)                                   # ← entry["input_schema"] dropped on the floor
```

**Constraint:** do not restructure this file (52 lines, registry-driven). The only edits are
(1) `capability.handler(**kwargs)` → the seam, and (2) passing `entry["input_schema"]` to
`add_tool` **if** the pinned FastMCP accepts it (verify with `inspect.signature`; RESEARCH A1
is unverified). The guard `test_card_list_cli_mcp.py::test_mcp_no_hardcoded_card_list` keeps
this honest.

---

### `src/construct/capabilities/catalog.py` (config/registry records)

**Analog: the `knowledge.card.list` record** (`catalog.py:314-323`) — the template for D-02's
new `views validate` record. Note `cli_name` **and** `mcp_tool_name` both set:

```python
registry.register(CapabilityRecord(
    id="knowledge.card.list",
    name="List Cards",
    description="List cards, optionally filtered by domain or lifecycle",
    input_model=CardListInput,
    output_model=OperationResult,
    handler=list_cards,
    cli_name="knowledge.card.list",
    mcp_tool_name="construct_list_cards",
))
```

**Analog: the existing views record** (`catalog.py:335-347`) — copy its structure and its
comment discipline, and note the RT-01/RT-02 comment that D-02 retires:

```python
registry.register(CapabilityRecord(
    id="views.generate_data",
    ...
    handler=_views_generate_handler,
    mcp_tool_name="construct_views_generate_data",
))
```

**Security constraint to carry into the new record:** `views/generate.py::install_root_error`
(`:175-194`) must be called by the `views.validate` handler before touching the path — the
`install_root` parameter becomes agent-supplied over MCP the moment the record exists.
The docstring at `:180-188` explains the exact reason and the "reason string carries no path"
convention for the MCP surface.

**`extra="forbid"` pattern** — `catalog.py:145-147` (`CardListInput`) for the `ConfigDict` form,
and `curation_run.py:127` for the plain-dict form (`model_config = {"extra": "forbid"}`). Both
are valid v2; match the surrounding file rather than harmonizing.

**Anti-pattern to remove:** the deliberately dual-mode handler at `catalog.py:329-334`:

```python
# ING-05: ... Accepts workspace both positionally (help.py:126 calls
# handler(workspace_id)) and by keyword (GraphStatusInput / MCP pass workspace=...).
handler=lambda workspace: graph_status(workspace),
```

Retiring it requires fixing `services/help.py:141` in the same task (route it through
`registry.invoke("graph.status", {"workspace": workspace_id})`).

**Ordering constraint (Finding G5):** the six `if args:` dual-mode shims at `catalog.py:854-940`
may only be deleted **after** `cli.py`'s positional call sites are normalized.

---

### `src/construct/views/models.py` (D-01/D-03/D-17/D-18/D-20)

**Analog: this file's own already-conformed models.** `DomainRecord` (`:97-123`) and
`ArticleRecord` (`:139-163`) were conformed to parser output in a prior pass, and carry the
comment style the phase should reuse — a `# D-NN:` block naming the parser function that is
the field set's source and naming the phantom fields removed:

```python
# D-02: the field set below is derived from what ``lib/parse_domains.parse``
# emits and is corroborated field-for-field by spec-v02-data-model.md §5.1. The
# previous scalar counters (card_count, connection_count, ...) were phantoms —
# no parser emitted them and no consumer read them; the real counts live inside
# ``metrics``. ``cross_domain_links`` and ``metrics`` stay open (bare list / dict)
# rather than becoming nested models: the parser guards them with nothing stronger
# than an ``isinstance(list)`` check ...
class DomainRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    ...
```

**Models to rename** (Finding V2 has the full map; the writer names come from
`generate.py:109-163`'s adapter lambdas, which are the authoritative rename table):
`CardRecord` (`:196-214`), `ConnectionRecord` (`:230-240`), `DigestRecord` (`:256-266`),
`StatsFile` (`:178-188`), `EventRecord` (`:287-296`).

**`extra` relaxation (D-03)** — mechanical, per model:
`model_config = ConfigDict(extra="forbid")` → `ConfigDict(extra="ignore")`. Note AGENTS.md
§ Pydantic Conventions mandates `forbid`; record D-03 as the named exception in the module
docstring (`:1-14`) so a reviewer does not "restore convention".

**`EventRecord` conform target (D-17)** — the canonical shape is the emitter's, in a
*different module with the same class name* (RESEARCH Pitfall 8). Always import qualified.
Source: `src/construct/schemas/config.py:353-361`:

```python
class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime
    agent: EventAgent
    action: str = Field(min_length=1)
    target: str | None = None
    detail: str | None = None
    result: EventResult
```

`EventResult` (`config.py:347-350`) already has an `escalated` member — D-16's new event type
threads through `EventAgent`/`EventResult`/`append_event`, not around them.

**Two new models (D-18)** — `<ws>/stats.json` and `<ws>/curation-history.json`. Follow the
`StatsFile`/`ArticlesFile` shape (a flat payload model with defaults) and derive fields from
`views/lib/compute_stats.compute_workspace`, exactly as `DomainRecord` derived from
`parse_domains.parse`.

**Envelope/unwrap contract to preserve** (`models.py:316-342`) — `ENVELOPE_METADATA_KEYS` must
grow to include any newly tolerated top-level writer key (`type_counts` is the measured
example that currently trips `extra_forbidden` in `connections.json`):

```python
ENVELOPE_METADATA_KEYS = frozenset({
    "version", "generated", "workspace",
    "schema_version", "generated_at", "build_id", "workspace_id",
})

def unwrap_payload(raw: dict) -> dict:
    inner = raw.get("data")
    if isinstance(inner, dict):
        return inner
    return {k: v for k, v in raw.items() if k not in ENVELOPE_METADATA_KEYS}
```

---

### `src/construct/views/generate.py` (D-01, OQ-C)

**Anti-pattern to delete** (`:85-164`) — the adapter tables. Their lambdas *are* the rename map;
mine them before deleting:

```python
_PER_WS_FILES: list[tuple[str, type[BaseModel], _Adapter]] = [
    ("cards.json", CardsFile, lambda d: {"cards": [{
        "summary": c.get("summary_excerpt", c.get("body_markdown", "")),
        "connections": c.get("connects_to", []),
        ...
    } for c in d.get("cards", [])]}),
    ("digests.json", DigestsFile, lambda d: {"digests": [{
        "domain_id": digest.get("domain", ""),
        "title": digest.get("theme", ""),
        "generated_at": digest.get("date", ""),
        "card_ids": [],                       # ← hard-coded; no parser emits it
        "summary": digest.get("summary_text", ""),
    } for digest in d.get("digests", [])]}),
]
```

**Pattern to preserve — the install-root guard** (`:175-194`), reused by D-02's new capability:

```python
def install_root_error(install_root: Path | str) -> str | None:
    root = Path(install_root)
    if not root.is_dir():
        return "install root is not an existing directory"
    if not (root / INSTALL_ROOT_MARKER).is_file():
        return f"not a CONSTRUCT installation: missing {INSTALL_ROOT_MARKER}"
    return None
```

**Pattern to preserve — atomic write** `_write_atomic` (`:518-522`); do not write new write logic.

**OQ-C:** `_validate_file_data` (`:484-490`) is the tables' only consumer, called from the write
loop at `:377`. Replace it with a direct `model_validate` of the raw dict — after D-01 the
adapter is the identity function — so `views generate` stays a validating writer and the
"a run that rejected any file did not produce the build" invariant at `:394-423` survives.

---

### `src/construct/llm/curation_run.py` (GOV-02..05, D-09..D-12, D-16)

**Analog: `_validate_run_id`** (`:64-77`) — the identifier-guard pattern to reuse verbatim for
`proposal_id`, including the docstring's threat statement and the ValueError message-with-example
convention AGENTS.md requires:

```python
def _validate_run_id(value: str | None) -> str | None:
    """Reject any ``run_id`` that is not kebab-case (CR-01 / T-11-01 guard).

    ``run_id`` becomes the LangGraph ``thread_id`` ... The MCP/CLI shims pass
    caller-supplied ``**kwargs`` straight into the input models, so an unvalidated
    value such as ``"../../../tmp/evil"`` would cross into the persistence/path layer.
    """
    if value is not None and KEBAB_CASE_PATTERN.fullmatch(value) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9] segments joined by single hyphens)")
    return value
```

Wired into a model with `field_validator` (`:131`): `_check_run_id = field_validator("run_id")(_validate_run_id)`.

**Model to extend (D-09)** — `CurationProposal` `:164-178`. It is `{"extra": "forbid"}` and is
both a serialization target and a deserialization source for durable checkpoint state
(RESEARCH Pitfall 4), so D-12's migration must inject the id at the **raw-dict** stage:

```python
class CurationProposal(BaseModel):
    model_config = {"extra": "forbid"}
    kind: Literal["promotion", "connection", "archive", "escalate"]
    decision: str = ""  # default = the gate recommendation (D-07)
    payload: dict = Field(default_factory=dict)
```

**Anti-pattern to replace (D-10)** — `_resolve_decisions` `:777-796`, positional zip with a
silent default:

```python
gate_queue = state.get("gate_queue", [])
raw = state.get("decisions")
resolved: list[str] = []
if isinstance(raw, list):
    for i, entry in enumerate(gate_queue):
        value = raw[i] if i < len(raw) else None       # ← short payload → silent write
        resolved.append(_normalize_decision(value, entry.get("decision", "")))
```

Target shape is RESEARCH Pattern 3 (`queued - supplied` / `supplied - queued` → `ReviewRejected`),
raised **before** `graph.invoke(Command(resume=...))`, not inside a node — a node-raised error
still advances the checkpoint. `research_run._resolve_decisions:479-501`'s url-keyed branch is
removed in the same task, not kept as an alternative.

**Audit-emission analog — `_emit`** (`:311-327`). Every new event type must go through it:

```python
def _emit(workspace_path: str, action: str, target: str | None, detail: str | None = None) -> str:
    from construct.schemas.config import EventAgent
    from construct.services.event_log import append_event

    append_event(Path(workspace_path), EventAgent.curator, action, target=target, detail=detail)
    return action
```

**Anti-pattern to fix (D-16)** — `apply_promotions` `:844-876`. Note the three-branch emission
and the escalate branch mislabelled as a rejection:

```python
if kind == "escalate" or decision == "escalate":
    escalated.append(card_id)
    events.append(_emit(workspace, "gate_review_rejected", card_id, "escalated (review-only)"))
    continue                                   # ← D-16: own event type, own bucket
...
try:
    if lifecycles.get(card_id) == target:
        promoted.append(card_id)               # idempotent NO-OP: nothing written
    else:
        res = edit_card(workspace, card_id, {"lifecycle": target}, author=CardAuthor.curator)
        if res.success: promoted.append(card_id)
        else:           logger.warning(...)     # WRITE FAILED
    events.append(_emit(workspace, "gate_review_approved", card_id, f"promote → {target}"))
    #             ↑ emitted on ALL THREE paths
```

Same shape recurs in `apply_connections` (~`:923`) and `apply_archives` (~`:968`) — fix all three.

**Per-item isolation pattern to preserve** — the `try/except` around each write with
`logger.warning(..., _sanitize_error(exc))` so one failure never aborts the batch (D-08 of
Phase 12). And `_card_lifecycle_map` (`:799-815`) is the "rebuild inside the apply node, never
store in state" pattern (Pitfall 3) — reuse it, do not add derived data to `CurationRunState`.

**ETag read sites (D-11)** — the codebase already reads snapshots at `:1172`, `:1229`, `:1278`
and in `research_run.py`; exposing the id is one dict lookup per site:
`graph.get_state(cfg).config["configurable"]["checkpoint_id"]`.

---

### `src/construct/llm/research_run.py:644` — the `DigestRecord` write path (D-20)

**Analog:** `compile_digest` (`:630-660`) — this is a **writer** using the views model, so a
rename here changes a workspace file, not a projection:

```python
def compile_digest(state: ResearchRunState) -> dict:
    """... Writes ``digests/<id>.md`` and appends a ``construct.views.models.DigestRecord``
    to the ``digests/digests.json`` record store (RESEARCH A1/D-09), replacing any
    record with the same id so a rerun stays idempotent."""
    from construct.views.models import DigestRecord, DigestsFile
```

Rename the fields here in the **same task** as `views/models.py::DigestRecord`. Second consumer
to move with it: `tests/llm/test_research_run.py:37` imports `DigestsFile`. This is the one
model where the `Field(alias=...)` + `populate_by_name=True` alternative is worth weighing
(RESEARCH § Alternatives) — two spellings with two legitimate authors.

---

### `.../components/ActivityList.jsx` — SPA event reader (D-17)

**Analog:** sibling SPA components that already read writer names — `Artifacts.jsx:211`
(`c.connects_to`), `Wiki.jsx:214,401` (`c.summary_excerpt`), `Wiki.jsx:178` (`d.theme`, `d.date`),
`DigestDetail.jsx:73,77` (`digest.summary_text`). Those are the proof of what "conformed to the
writer" looks like on the SPA side.

**Current (non-conforming) reader** — the canonical file is the scaffold template at
`CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/src/components/ActivityList.jsx`
(the `test-ws/*` copies are generated scaffolds, not sources):

```jsx
<li key={`${e.timestamp}-${i}`} ...>
  <span ...>{formatTime(e.timestamp)}</span>   // → e.ts
  <span ...>{e.actor || '—'}</span>            // → e.agent
  <span ...>{prettyType(e.type)}</span>        // → e.action
  <span ...>{describeSubject(e)}</span>        // → e.target / e.detail
</li>
```

```jsx
function describeSubject(event) {
  const s = event.subject || {}      // ← `subject` exists in no emitter
  if (s.title) return s.title
  if (s.card_id) return s.card_id
  ...
}
```

Conform these five accessors to `ts` / `agent` / `action` / `target` / `detail` / `result`.
`formatTime` and `prettyType` are shape-agnostic and stay.

**Upstream reader that renames nothing** — `views/lib/parse_events.py:22-36` passes JSONL lines
through verbatim and sorts on `e.get("timestamp", "")`. That sort key must move to `"ts"` with
the rename, or every event sorts equal.

---

### `src/construct/ui/streamlit_app.py` (D-13, Pitfall 6)

**Analog:** the two surviving lines beside the one being removed (`:44-48`):

```python
home = st.Page("dashboard.py", title="Dashboard", icon="📊")
runner = st.Page("capability_runner.py", title="Capability Runner", icon="⚡")
gates = st.Page("gate_review.py", title="Gate Review", icon="🔍")   # ← delete

pg = st.navigation([home, runner, gates])                            # ← drop `gates`
```

Both edits in one task, plus the module docstring at `:3-6` which enumerates three panels.
`streamlit_app.py` is the **only** in-repo reference to the module; every other `gate_review`
grep hit is either `research_run.py`'s LangGraph node of the same name (keep) or the
`gate_review_approved` / `gate_review_rejected` event strings (keep — D-16's concern).

---

### `tests/integration/test_views_generate.py` — the D-04/D-19 round-trip guard

**Analog:** `test_generated_card_connections_are_id_strings` (`:85-120`) — the existing
non-vacuous round-trip in the same file, including the explicit anti-vacuity precondition:

```python
def test_generated_card_connections_are_id_strings(tmp_path: Path) -> None:
    root = _populated_install_root(tmp_path)
    report = generate(root)
    assert report.validation_errors == [], report.validation_errors
    ...
    # Load-bearing precondition: without a non-empty list somewhere, the type
    # assertion below passes vacuously — the Pitfall 1 failure mode.
    assert any(card["connects_to"] for card in all_cards), (
        "no generated card has connections; CardRecord.connections is untested"
    )
```

**Fixture helper to reuse — do not build a new one** (`:55-65`):

```python
def _populated_install_root(tmp_path: Path) -> Path:
    """Copy the shared populated fixture into *tmp_path* and clear its build dir.
    ... The pre-built ``views/build/`` is removed so the fingerprint cache cannot
    short-circuit generation and mask the model change (Pitfall 2)."""
    root = tmp_path / "populated"
    shutil.copytree(POPULATED_FIXTURE, root)
    shutil.rmtree(root / "views" / "build", ignore_errors=True)
    return root
```

**Test being replaced** (`:285-323`) — its structure (invoke generate, invoke validate, parse the
`✗` lines into a set) is exactly the harness the new guard inherits; only the assertion inverts
from "these 3 fail" to "all 8 pass, all record lists non-empty, `total_files_written == 4 + 6*n_ws + 1`":

```python
runner.invoke(app, ["views", "generate", "--install-root", str(root)])
validated = runner.invoke(app, ["views", "validate", "--install-root", str(root)])
failing = {
    line.strip().removeprefix("✗ ").strip()
    for line in validated.stdout.splitlines()
    if line.strip().startswith("✗")
}
assert failing == {"stats.json", "demo/connections.json", "demo/events.json"}, failing
```

Note the replaced test uses `scaffolded_install_root` — the vacuous fixture. The new guard must
use `_populated_install_root`. The module-level `ALL_MODEL_NAMES` list (`:34-52`) is the existing
model-inventory guard and must grow by the two D-18 models.

---

### `tests/llm/test_curation_run.py` / `test_research_run.py` — GOV-04 source guard

**Analog:** `test_gate_review_is_interrupt_only` (`test_research_run.py:758-773`) — the
source-inspection guard shape GOV-04's "no canonical writer outside apply nodes" test copies:

```python
def test_gate_review_is_interrupt_only():
    """T-10-07: the gate node body contains a single interrupt() and no writes."""
    from construct.llm import research_run

    src = inspect.getsource(research_run.gate_review)
    assert src.count("interrupt(") == 1
    for forbidden in ("_write_ref_file", "create_card", "append_event",
                      "append_rejected", "write_text", ".write("):
        assert forbidden not in src, f"gate node must not perform {forbidden}"
```

Generalize the forbidden-token list to `edit_card` / `add_connection` / `archive_card` and apply
it across every non-apply-node module (this is how D-13's removal stays enforced after the fact).

---

## Shared Patterns

### Module preamble (every new/edited Python file)
**Source:** AGENTS.md § Code Style, visible in every module read
**Apply to:** all Python files in this phase

```python
"""One-line summary, then the decision ids this module carries."""
from __future__ import annotations
```

Full type annotations on all signatures, including `-> None`.

### Decision-ID comment blocks
**Source:** `views/models.py:97-108`, `catalog.py:329-334`, `curation_run.py:96-101`
**Apply to:** every behaviour change in this phase

This codebase records *why* inline with a `# D-NN:` / `# WR-NN:` prefix naming the decision, the
prior wrong behaviour, and the evidence. D-01 (ING-02 tension), D-03 (`extra="ignore"` vs
AGENTS.md), and D-13 (the deletion) each explicitly require this.

```python
# D-02: the field set below is derived from what ``lib/parse_domains.parse``
# emits ... The previous scalar counters were phantoms — no parser emitted them
# and no consumer read them; the real counts live inside ``metrics``.
```

### Boundary validation
**Source:** `catalog.py:145-147` + `curation_run.py:127`
**Apply to:** all 28 capability input models (D-06)

```python
model_config = ConfigDict(extra="forbid")   # views/models.py style
model_config = {"extra": "forbid"}          # curation_run.py style — match the file
```

### Error handling at the seam
**Source:** AGENTS.md § Error Handling; `mcp/server.py:36-37` vs the CLI's `typer.Exit(1)`
**Apply to:** `registry.invoke`, both surfaces

Convert `pydantic.ValidationError` to a domain error with `raise ... from exc` at the seam; each
surface renders it. MCP currently swallows everything into `{"error": str(exc)}` while the CLI
raises `typer.Exit(1)` — if the seam does not raise a *typed* error, D-08 compares two different
renderings of the same failure.

### Audit events
**Source:** `services/event_log.py:13-41` + `schemas/config.py:340-361`
**Apply to:** every event D-16 adds or makes conditional

```python
def append_event(workspace_root, agent: EventAgent, action: str, *,
                 target: str | None = None, detail: str | None = None,
                 result: EventResult = EventResult.success) -> None:
    record = EventRecord(ts=datetime.now(timezone.utc), agent=agent, action=action,
                         target=target, detail=detail, result=result)
    ...
    f.write(record.model_dump_json() + "\n")
```

Note `EventResult.escalated` already exists — D-16's escalate outcome has a home in the enum.
`append_event` is deliberately non-blocking (warns to stderr, never raises); do not "fix" that.

### Test fixture construction
**Source:** `test_card_list_cli_mcp.py:30-60`, `tests/llm/conftest.create_test_workspace`,
`test_views_generate.py:55-65`
**Apply to:** all three new test files

Build fixtures through real services (`initialize_workspace` / `create_card` /
`create_test_workspace`) or by copying a fixture tree into `tmp_path`. Never generate into
`test-ws/` or `tests/fixtures/` in place.

### Cardinality over set-membership
**Source:** the WR-01 lesson; the anti-pattern is `test_artifact_catalog.py` and
`test_mcp_contracts.py::test_mcp_tool_count`'s `expected = {...}` name set
**Apply to:** D-04 (`4 + 6*n_ws + 1`), D-06 (all-28 forbid), D-08 (parity coverage)

Assert counts, not name sets. A set-membership assertion proves a thing is *listed*, never that
nothing was *added*.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Degraded / escalated `curation.run` fixtures | test fixture | event-driven | Neither exists today (RESEARCH § Wave 0 Gaps). Closest starting point is `tests/llm/conftest.create_test_workspace` plus forcing the `status` / `escalated` state channels (`curation_run.py:112,117`) — but no test currently produces a degraded or escalated run. |
| Pre-migration id-less checkpoint fixture (D-12) | test fixture | file-I/O | No test constructs a `.construct/workflow/*.sqlite` in a legacy shape. `test_research_run.py:775-786` (`test_open_checkpointer_targets_construct`) shows how to open a real `SqliteSaver` against `tmp_path`, which is the nearest building block. |
| `registry.invoke` itself | seam | request-response | No dispatch seam exists anywhere in the repo. Assemble it from `registry.get:36-40` (error convention) + `mcp/server.py:33` (call convention); RESEARCH Pattern 1 is the target. |
| `<ws>/curation-history.json` contract model (D-18) | model | transform | No model, no parser docstring, and RESEARCH A5 flags that its shape may not be stable. Follow `StatsFile`'s shape and derive fields from the writer in `views/generate.py`. |

---

## Metadata

**Analog search scope:** `src/construct/{capabilities,views,llm,mcp,ui,services,schemas}/`,
`tests/{contract,integration,llm}/`, and the SPA scaffold template under
`CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/src/`
**Files read:** 17
**Pattern extraction date:** 2026-07-26
