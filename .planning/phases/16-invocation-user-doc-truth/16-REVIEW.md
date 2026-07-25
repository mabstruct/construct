---
phase: 16-invocation-user-doc-truth
reviewed: 2026-07-25T14:00:08Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - src/construct/services/knowledge.py
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - src/construct/llm/curation_run.py
  - tests/contract/test_card_list_cli_mcp.py
  - tests/contract/test_doc_command_references.py
  - tests/contract/test_mcp_contracts.py
  - tests/contract/test_skill_migration.py
  - tests/llm/test_curation_run.py
  - tests/llm/test_views_refresh.py
  - tests/unit/test_capability_registry.py
  - tests/unit/test_knowledge_operations.py
  - AGENTS.md
  - CONSTRUCT-CLAUDE-impl/USER_GUIDE.md
  - CONSTRUCT-CLAUDE-impl/construct/references/commands.md
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues-found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-07-25T14:00:08Z
**Depth:** standard
**Files Reviewed:** 16 (4 Python source, 8 test, 4 docs)
**Status:** issues-found

## Summary

Phase 16 adds a `knowledge card list` capability with CLI + MCP registration, rewords
the `decay_scan` summary string, and corrects a large body of user-facing docs. The
core runtime code (`list_cards`, its registry record, the CLI leaf) is small,
correct on the happy path, and well-tested at the service and CLI layers. The
`decay_scan` summary change is factually accurate against the actual runtime behaviour
(the node genuinely enqueues archive proposals under the governance flag). All 8 test
files assert non-vacuously — the doc-reference and skill-migration suites even carry
explicit meta-guards against false-green. The affected tests pass (98 passed, 1 skipped;
the skip is the deliberately-empty `_KNOWN_BROKEN` parametrization).

Two genuine defects surfaced, both on the **MCP boundary** — the one surface the phase's
"CLI/MCP parity" claim leans on but the new tests do not exercise on the failure path:

1. The MCP dispatch cannot serialize a failing `list_cards` result — the structured
   "Not a workspace" error is replaced at runtime by a generic
   `Object of type OperationError is not JSON serializable` string.
2. `CardListInput`'s `extra="forbid"` (advertised in-code as an "ASVS V5 boundary
   reject") is never enforced at the MCP boundary; the model is never instantiated in
   dispatch, so no field validation or type-coercion happens for MCP callers.

Both root-cause in shared infrastructure (`src/construct/mcp/server.py`, unchanged this
phase) but are newly *reachable* through the capability this phase ships, and both are
contradicted by claims made in the phase-16 diff itself. Neither is a crash, data-loss,
or security-exploit path, so both are WARNING rather than BLOCKER.

## Structural Findings (fallow)

No `<structural_findings>` block was provided with this review. None to report.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: MCP failure path for `list_cards` returns an unserializable error, breaking CLI/MCP parity

**File:** `src/construct/services/knowledge.py:615-627` (failure branches of `list_cards`), realized through `src/construct/mcp/server.py:13-20,31-37`

**Issue:** `list_cards` returns an `OperationResult` whose `errors` list holds
`OperationError` **dataclass instances** on both failure branches (missing cards dir,
`WorkspaceLoadError`). The MCP dispatch serializes results via `_serialize_result`, which
for a dataclass does `{f: getattr(result, f) for f in result.__dataclass_fields__}` —
leaving `errors` as a list of raw `OperationError` objects — and then calls
`json.dumps(serialized)`. That `json.dumps` raises `TypeError: Object of type
OperationError is not JSON serializable`, which the handler's blanket `except Exception`
swallows into `{"error": "Object of type OperationError is not JSON serializable"}`.

Reproduced directly:
```
$ list_cards('/tmp/not-a-workspace') -> success=False, errors[0] is OperationError
$ _serialize_result(...) then json.dumps(...) -> TypeError (confirmed)
```

The CLI failure path is unaffected — `_display_result` hand-builds a plain dict for
`errors` — so an MCP client hitting the exact same "point `--workspace` at a
non-workspace" mistake gets a useless generic string while the CLI gets the actionable
"Not a workspace … run `construct init`" guidance. This is precisely the CLI/MCP parity
the phase claims to deliver, and it is broken on the error path. `test_cli_mcp_schema_parity`
only exercises the **success** path, so the divergence is untested.

Root cause is `_serialize_result` (shared, unchanged this phase, affects every operation
that returns errors over MCP), but the new capability makes it trivially reachable.

**Fix:** Make `_serialize_result` serialize nested dataclasses, e.g.:
```python
from dataclasses import is_dataclass, asdict

def _serialize_result(result):
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if is_dataclass(result):
        return asdict(result)   # recurses into OperationError, dates still need care
    ...
```
`asdict` recurses into `OperationError`, fixing the crash. (If any `data` payload can
carry `date` objects that were not pre-coerced, add a `default=str` to the `json.dumps`
call in the handler as a belt-and-braces guard.) Add a failure-path parity test that
runs the MCP handler against a non-workspace and asserts the JSON round-trips with the
structured error intact.

### WR-02: `CardListInput.extra="forbid"` is never enforced at the MCP boundary — the security claim and its test are false assurance

**File:** `src/construct/capabilities/catalog.py:147-156` (the `# ASVS V5 … reject unexpected MCP payload fields at the boundary` comment) and `tests/contract/test_card_list_cli_mcp.py:85-94`

**Issue:** The in-code comment asserts that `model_config = {"extra": "forbid"}` on
`CardListInput` rejects unexpected MCP payload fields "at the boundary." It does not.
The MCP server (`src/construct/mcp/server.py:30-44`) builds each tool from
`def handler(**kwargs)` and calls `capability.handler(**kwargs)` — it **never instantiates
`CardListInput`**. `registry.list_mcp_tools()` computes an `input_schema` from the model
(`registry.py:63`), but `create_server` discards it and passes only `name`/`description`
to `app.add_tool`, so FastMCP derives its schema from the `**kwargs` signature (open, no
declared properties). Consequences:
- `extra="forbid"` is dead for MCP; unknown fields are rejected only incidentally, via a
  Python `TypeError` from `list_cards(**kwargs)` (which then hits WR-01's broken
  serialization).
- No type coercion happens: an MCP caller sending `include_archived: "false"` forwards a
  non-empty string, which `not include_archived` treats as *falsey*→wait, non-empty
  string is truthy, so `include_archived="false"` would **include** archived cards — a
  silent CLI/MCP behavioural divergence (Typer coerces `--include-archived` to a real
  bool; MCP does not).

`test_input_model_forbids_extra_fields` constructs `CardListInput(bogus=1)` in isolation
and asserts it raises. That proves the model *can* forbid extras, not that the boundary
*does* — it is green while the runtime boundary is unprotected, which is exactly the kind
of false assurance an adversarial review flags.

**Fix:** Route MCP dispatch through the declared `input_model` so validation and coercion
actually run at the boundary:
```python
def make_handler(capability=cap):
    def handler(**kwargs):
        try:
            validated = capability.input_model(**kwargs)   # extra=forbid + coercion here
            result = capability.handler(**validated.model_dump())
            return json.dumps(_serialize_result(result), indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)})
    return handler
```
(This is server-level and out of the phase-16 diff, but until it lands, soften the
catalog.py comment so it does not claim boundary enforcement that does not exist, and add
a test that drives an extra field *through the MCP handler*, not the bare model.)

## Info

### IN-01: `knowledge card list` prints no card data in human-readable mode

**File:** `src/construct/cli.py:1452-1469` via `src/construct/cli.py:182-190`

**Issue:** Without `--json`, `_display_result` prints only `✓ Found N card(s)` — it never
renders `result.data`, so a human running `construct knowledge card list` sees a count but
no cards. This matches the shared behaviour of `connection list` and the docs steer users
to `--json`, so it is consistent, not a regression. Flagging because the command's stated
purpose is enumeration and the default invocation enumerates nothing.

**Fix:** Optional — teach `_display_result` (or a list-specific renderer) to print card
ids/titles when `data` is a list of dicts and `--json` is off.

### IN-02: `_json_safe` only coerces top-level values

**File:** `src/construct/services/knowledge.py:603-612`, applied at `:640`

**Issue:** `_json_safe` is applied per top-level value in the card dict comprehension. It
is currently correct because the only `date` fields in `KnowledgeCard` (`created`,
`last_verified`) are top-level and the nested models (`sources`, `connects_to`) contain
only `(str, Enum)` values, which `json.dumps` handles. It is silently fragile: if the card
schema ever gains a nested `date`/`datetime` (e.g. a per-source `retrieved_at`), the
enumerate handler would leak a raw date and `_display_result`'s bare `json.dumps` would
raise at runtime — with no test catching it, since the parity test only checks top-level
keys.

**Fix:** Either make `_json_safe` recurse into dicts/lists, or add a comment pinning the
invariant "card frontmatter has no nested temporal fields" next to a schema-level guard.

### IN-03: Unused `ctx: typer.Context` parameter in `card_list`

**File:** `src/construct/cli.py:1453`

**Issue:** `card_list` declares `ctx: typer.Context` but never reads it. Consistent with
sibling commands (`connection_list`, `status`), so it is house style, not a defect — noted
for completeness.

**Fix:** None required; drop the parameter if a future cleanup standardizes on omitting
unused `ctx`.

### IN-04: AGENTS.md "nothing reads [model-routing.yaml]" is slightly overstated and conflicts with generated workspace README

**File:** `AGENTS.md:134` (Configuration section)

**Issue:** AGENTS.md now says `.construct/model-routing.yaml` is "deprecated and inert;
nothing reads it." `validation.py:129` does call `loader.load_model_routing()` to
*schema-validate* the file when present — so it is parsed, just not used to route LLM
calls. Separately, `services/init.py:175` (unchanged this phase) still writes into every
new workspace's README that "`.construct/model-routing.yaml` stores runtime routing
guidance," directly contradicting the new deprecation note. The AGENTS.md claim is
defensible for *runtime routing* but the absolute "nothing reads it" is imprecise, and the
init-generated doc string is now stale.

**Fix:** Reword to "nothing reads it *for routing*; it is only schema-validated and kept in
REQUIRED_PATHS." Follow up (outside this phase) by correcting the init-generated README
line in `services/init.py:175`.

---

_Reviewed: 2026-07-25T14:00:08Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
