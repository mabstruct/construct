# Phase 13: Daily-Cycle Composition - Research

**Researched:** 2026-07-06
**Domain:** Workflow composition over shipped LangGraph child capabilities (registry / CLI / stdio-MCP parity)
**Confidence:** HIGH (every claim below is grounded in a direct read of the current source; line numbers verified)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `daily.run` **never blocks on human review** and **never interrupts** — runs children to completion in a single pass. Review is optional and happens *after*, via the children's existing `research review` / `curation review` commands.
- **D-02:** By default `daily.run` **auto-applies each child gate's recommended decision** (curation: promote / connection-type / archive; research: approved finding ingest) — the "approve-all recommendations" resume path, applied programmatically.
- **D-03:** **`escalate` / undecided items are NEVER auto-written** — they stay pending at the child's gate for optional human review (safety valve; mirrors D-07 "no default write for escalate"). *(See Open Question 1 — this phrasing needs a precise reading against the all-or-nothing resume model.)*
- **D-04:** Every auto-applied write is **event-logged** (per-item `gate_review_approved` + step events) exactly as an interactive review would log. *(Already emitted by the child apply nodes — no new logging code in `daily.run`.)*
- **D-05 (DEPARTURE — flag for planner):** D-02 is a deliberate departure from the Phase-12 "no canonical write before human approval" spine (CUR-03 / T-12-09), justified ONLY for this unattended composition layer. The children's own HITL contract MUST NOT be weakened; auto-apply lives only in `daily.run`.
- **D-06:** **Isolate + degrade.** A failing child never aborts the cycle — the other child and the closing `graph.status` still run.
- **D-07:** Parent status mirrors `curation.run._aggregate_status` vocabulary (`completed` / `degraded` / `failed`). Result surfaces per-child status + a pending-escalation count + the final graph-health summary; a run with pending escalations or a failed child is **never** reported as bare `completed` (DAY-03). Child failure detail sanitized via existing `_sanitize_error`.
- **D-08:** Capability id **`daily.run`**; CLI **`construct daily run`**; MCP tool **`construct_daily_run`**; plus **`daily inspect`**. MCP parity via registry auto-discovery — do **NOT** edit `mcp/server.py`. Do **NOT** revive the `workflow run/resume` group Phase 12 deleted.
- **D-09:** `daily.run` composes, in order, **`research.run` → `curation.run` → `graph.status`**, calling the children's existing entrypoints (`run_research_run` / `run_curation_run`) — no re-implementation of their steps.
- **D-10:** **Views-refresh is EXCLUDED** from the capability — stays a skill-level hook. `daily.run` is a pure runtime workflow.

### Claude's Discretion
- Exact parent status enum surface and result payload shape (mirror `curation.run` result + `_aggregate_status`).
- **Whether `daily.run` is a thin Python composition of the child `run_*` functions vs a LangGraph parent graph with subgraph nodes** — resolved below (Architecture Patterns → decisively **thin composition**).
- The exact `--auto-apply`-style flag surface, if any (default posture = auto-apply per D-02).

### Deferred Ideas (OUT OF SCOPE)
- Scheduled/cron execution of `daily.run`.
- Per-run `--skip-research` / focus-domain flags.
- Views-refresh inside the capability (stays a skill hook, D-10).
- Merged interactive review gate across children.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DAY-01 | Run a daily-cycle workflow through CLI/MCP that **composes** stable research + curation children instead of duplicating logic | Thin-composition module calling `run_research_run` / `run_curation_run` / `graph_status` (Architecture Patterns). |
| DAY-02 | See parent + child status, pending reviews, degraded states, final graph-health summary in the result | `DailyRunResult` payload shape (Architecture Patterns → Result Shape); folds child `RunResult` / `CurationRunResult` + `graph_status().data`. |
| DAY-03 | Run safely when research/curation pauses for review, fails partially, or skips optional views refresh | Isolate-and-degrade try/except per child + `_aggregate_daily_status` mirroring `_aggregate_status`; "no false completed" rule. |
| API-01 | Every new capability registered with Pydantic I/O schemas + handler + CLI + MCP metadata | Two `CapabilityRecord`s (`daily.run`, `daily.inspect`) mirroring the curation records (catalog.py L433-462). |
| API-02 | Invoke every new capability through the same registry-backed handler from CLI + stdio MCP | Shim wrappers (`_daily_run_shim`, `_daily_inspect_shim`) + `daily` Typer sub-app; MCP free via auto-discovery. |
| API-03 | Verify CLI/MCP schema + result parity for all new capabilities | Contract test mirroring `test_curation_run_cli_mcp.py` (`test_cli_mcp_schema_parity`). |
| API-05 | Existing v0.3 CLI/MCP/Streamlit/validation/ingestion/graph/ask-domain behavior continues to pass | Additive-only change (no edits to `mcp/server.py`, child modules, or existing records) + full-suite green regression gate. |
</phase_requirements>

## Summary

Phase 13 is a **pure composition** phase inside an already-mature codebase. The two children being composed — `research.run` and `curation.run` — are shipped LangGraph workflows exposed through plain, self-contained runner functions that each open and close their own SQLite checkpointer, manage their own `thread_id`, and return a typed Pydantic result model. The closing health summary comes from `graph_status(workspace)`, a plain function returning an `OperationResult` with a `{cards, connections, domains}` data block.

The central architecture question — thin Python composition vs. a LangGraph parent graph with subgraph nodes — resolves **decisively in favor of thin composition**. The children are not designed to be embedded as nodes: each owns its own graph, checkpointer connection, and thread lifecycle. A parent `StateGraph` would nest graph-invocations inside nodes for **zero durability benefit** (D-01 mandates no parent-level interrupt/resume), while adding a second checkpoint DB, a parent state schema, and conditional error edges to replicate what a `try/except` per child does in three lines. The spec's "LangGraph parent graph" gesture (spec-v04 L101/L355/L578) is a v0.3-era P2 sketch that predates the shipped child entrypoints; CONTEXT D-09 ("compose, don't duplicate; call the children's existing entrypoints") supersedes it, and DAY-01 only requires "composes … instead of duplicating," which thin composition satisfies better.

The auto-apply mechanism (D-02/D-03) requires **no new gate logic**: it reuses each child's existing `approve_all` resume path (`_build_resume_decisions`), and the curation apply nodes already treat `escalate`-kind proposals as review-only (no write). Registration/CLI/MCP/contract-test patterns are mechanical clones of the curation quartet already in the tree.

**Primary recommendation:** Implement `daily.run` as a thin synchronous composition module `src/construct/llm/daily_run.py` that (1) calls `run_research_run` then, if it paused, `review_research_run(approve_all=True)`; (2) calls `run_curation_run` then, if it paused, `review_curation_run(approve_all=True)`; (3) calls `graph_status(workspace)`; each wrapped in isolate-and-degrade `try/except`; folds all three into a `DailyRunResult` whose status is aggregated by a `_aggregate_daily_status` mirroring curation's `_aggregate_status`. Register `daily.run` + `daily.inspect` records and a `daily` Typer sub-app exactly like the curation quartet; add a contract test cloned from `test_curation_run_cli_mcp.py`. Never edit `mcp/server.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `daily.run` orchestration | Workflow Runtime (L2, plain Python composition) | — | D-09 composes children; no new graph, no SOT writes of its own |
| research child (search→score→review→ingest) | Workflow Runtime (child LangGraph) | Workspace SOT (writes refs/cards/digest on approve) | Owned entirely by `research_run.py`; parent only invokes/reviews |
| curation child (integrity→decay→orphan→connection→apply) | Workflow Runtime (child LangGraph) | Workspace SOT (lifecycle/connection/archive writes on approve) | Owned entirely by `curation_run.py`; parent only invokes/reviews |
| closing graph-health summary | Read-only pipeline (`graph_status`) | — | Pure read of workspace SOT; folded into parent result |
| registry / CLI / MCP exposure | Invoke Surfaces (L3) + Capability Registry | — | Mechanical clone of curation records + `daily` Typer sub-app; MCP auto-discovered |
| views refresh | Skill layer (L0) — **excluded** | — | D-10: parent-skill owns the single post-run views refresh, not the capability |

## Standard Stack

No new external packages. Everything needed is already a project dependency and already imported by the child modules.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | already vendored | `DailyRunInput` / `DailyInspectInput` / `DailyRunResult` I/O models | Every capability model in the tree is Pydantic with `extra="forbid"` [VERIFIED: read of research_run.py L108-174, curation_run.py L121-208] |
| `typer` | already vendored | `daily` CLI sub-app | Mirrors the `curation_app` sub-app [VERIFIED: cli.py L368-373, L688-767] |
| `langgraph` | already vendored | **Only transitively** — the children own the graphs; `daily.run` calls them as plain functions | Thin composition uses no LangGraph API directly [VERIFIED: children own `_open_checkpointer` + `graph.invoke`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `logging` | — | stderr diagnostics (never `print` — stdout is MCP JSON-RPC transport) | All node/handler diagnostics [CITED: curation_run.py L26-27 module docstring] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Thin Python composition | LangGraph parent `StateGraph` with child subgraph nodes | Rejected — see Architecture Patterns. Nested graph-in-node, second checkpoint DB, parent state schema, conditional error edges, all for zero durability benefit under D-01 (no parent interrupt/resume). |

**Installation:** none required — no `npm/pip/cargo` install in this phase.

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** All code reuses existing project dependencies (`pydantic`, `typer`, `langgraph`, stdlib). No registry install, no slopcheck run needed.

## Architecture Patterns

### GROUNDED Recommendation: Thin Python Composition (not a parent graph)

**Verified child entrypoint signatures** (all are plain, synchronous, self-contained functions returning Pydantic models):

| Function | File:Line | Signature | Returns | Self-contained? |
|----------|-----------|-----------|---------|-----------------|
| `run_research_run` | research_run.py **L900** | `(inp: ResearchRunInput) -> RunResult` | `RunResult` | Yes — opens+closes its own `SqliteSaver` (`research-run.sqlite`), owns `thread_id=run_id`, closes conn in `finally` |
| `review_research_run` | research_run.py **L996** | `(inp: ReviewInput) -> RunResult` | `RunResult` | Yes — re-opens same DB, `Command(resume=…)`, runs to END |
| `inspect_research_run` | research_run.py **L1038** | `(inp: InspectInput) -> RunResult` | `RunResult` | Yes — read-only `get_state` |
| `run_curation_run` | curation_run.py **L1071** | `(inp: CurationRunInput) -> CurationRunResult` | `CurationRunResult` | Yes — own `curation-run.sqlite`, closes conn in `finally` |
| `review_curation_run` | curation_run.py **L1134** | `(inp: CurationReviewInput) -> CurationRunResult` | `CurationRunResult` | Yes |
| `inspect_curation_run` | curation_run.py **L1182** | `(inp: CurationInspectInput) -> CurationRunResult` | `CurationRunResult` | Yes |
| `graph_status` | pipelines/graph_status.py **L12** | `(workspace: str \| Path) -> OperationResult` | `OperationResult` (data = `{cards, connections, domains, workspace}`) | Yes — pure read |

**Evidence the children are NOT graph-node-shaped:**
1. Each runner **opens and closes its own SQLite connection** in a `try/finally` (`_open_checkpointer` + `conn.close()`), and **compiles its own graph** internally (`build_*_run_graph`). Embedding them as parent-graph nodes would nest a full `graph.invoke` (and a second live sqlite connection) inside a parent node — a documented LangGraph anti-pattern and an unnecessary connection-lifecycle hazard.
2. Each runner **manages its own `thread_id`** derived from its own `run_id`. A parent graph would have a third `thread_id`/checkpoint with no interrupt to persist across — D-01 forbids any parent-level pause.
3. The children **return typed Pydantic result models** (`RunResult`, `CurationRunResult`), not partial-state dict updates — they are already "call and fold," i.e., function-shaped.
4. `graph_status` returns an `OperationResult`, not graph state — trivially a function call, awkward as a node.

**Conclusion (HIGH confidence):** thin composition. A parent `StateGraph` buys nothing here because the only LangGraph value-adds — interrupt/resume/durable checkpoint/branching — are all consumed *inside* the children and explicitly disallowed at the parent by D-01. Isolate-and-degrade (D-06) is a `try/except` per call in Python vs. conditional error edges in a graph.

**Spec drift to flag:** spec-v04 rows L101 ("Daily cycle orchestrator … LangGraph parent graph"), L355 (`DAY[daily_cycle]` inside the LangGraph subgraph box), and L578 (W6 "extend `workflow.daily_cycle` to call research + curation subgraphs") all describe a parent graph. These predate the shipped child runner functions and the D-09 "compose, don't duplicate" mandate. **DAY-01 does not require a graph** — it requires composition without duplication. Recommend the planner explicitly note the departure from the spec sketch (the sketch is aspirational; D-09 governs).

### Composition Flow (the module to build)

```
daily.run(workspace_path, run_id?)                         # src/construct/llm/daily_run.py
  │
  ├─ run_id = inp.run_id or _new_run_id()   # "daily-YYYYMMDD-HHMMSS-<hex>", kebab-safe
  │
  ├─ RESEARCH child  (isolate+degrade, D-06)
  │     try:
  │        r = run_research_run(ResearchRunInput(workspace_path, run_id=<child id>))
  │        if r.status == "awaiting_review":
  │            r = review_research_run(ReviewInput(workspace_path, run_id=r.run_id, approve_all=True))
  │     except Exception as e: r = <degraded child status via _sanitize_error(e)>
  │
  ├─ CURATION child  (isolate+degrade, D-06)
  │     try:
  │        c = run_curation_run(CurationRunInput(workspace_path, run_id=<child id>))
  │        pending_escalations = sum(1 for p in c.gate_queue if p.get("kind") == "escalate")   # count BEFORE resume
  │        if c.status == "awaiting_review":
  │            c = review_curation_run(CurationReviewInput(workspace_path, run_id=c.run_id, approve_all=True))
  │     except Exception as e: c = <degraded child status via _sanitize_error(e)>
  │
  ├─ GRAPH HEALTH   g = graph_status(workspace_path)        # OperationResult; g.data = health summary
  │
  └─ fold → DailyRunResult(status=_aggregate_daily_status(...), children=[...], pending_escalations, graph_health=g.data, ...)
     persist result JSON → .construct/workflow/daily/<run_id>.json     # for daily.inspect (see Open Q 2)
```

Note: give each child its own child `run_id` (e.g. `f"{run_id}-research"`, `f"{run_id}-curation"`) so `daily.inspect` / the child inspect commands can resolve them, and so escalate items left un-written are addressable by a later `curation review --run-id <run_id>-curation` if desired. Child `run_id` must satisfy `KEBAB_CASE_PATTERN` (the `_validate_run_id` guard) — the `daily-…` / `-research` suffix form is kebab-safe.

### Auto-apply mechanism (D-02 / D-03) — reuse, do not rebuild

The "approve-all recommendations" path already exists in both children and already excludes escalate from writes. **No new gate logic is required.**

**Curation** (`_build_resume_decisions`, curation_run.py **L1117-1131**):
```python
# approve_all (or default): reproduce the recommended per-item decision.
return [entry.get("decision", "approve") for entry in gate_queue]
```
Downstream, the apply nodes enforce D-03 by construction:
- `apply_promotions` (L824-882): `if kind == "escalate" or decision == "escalate": escalated.append(card_id); ... continue` → **escalate is recorded, never written** (emits `gate_review_rejected` "escalated (review-only)"). Only `decision == "promote"` writes via `edit_card`.
- `apply_connections` (L885-933): writes unless `decision == "reject"`.
- `apply_archives` (L936-978): writes only when `decision == "archive"`.

So calling `review_curation_run(approve_all=True)` reproduces every proposal's *recommended* decision, applies promote/connection/archive, and **auto-excludes escalate** — exactly D-02 + D-03, using the shipped code path.

**Research** (`_build_resume_decisions`, research_run.py **L979-993**):
```python
if inp.approve_all:
    return [entry.get("decision", "skip") for entry in gate_queue]  # recommended ingest_action per finding
```
Research findings have **no escalate kind**; the recommended `ingest_action` (`skip` / `ref_only` / `ref_and_card`, per `GateQueueEntry` L142-152) is reproduced. Low-relevance findings whose recommendation is `skip` are simply not written. D-02 satisfied; D-03's escalate carve-out is curation-only.

**Event logging (D-04) is automatic:** every child apply node calls `_emit(...)` → `append_event(...)` with `gate_review_approved` / `gate_review_rejected` + `workflow_step_complete`, identical to an interactive review [VERIFIED: curation_run.py L308-324 `_emit`, L858/L878/L929/L974 per-item events; event_log.py L13-41 `append_event` is non-blocking]. `daily.run` writes **no** events of its own — it inherits the full audit trail from the children.

### Result Shape (DAY-02 / D-07) — mirror CurationRunResult + `_aggregate_status`

`CurationRunResult` (curation_run.py **L195-208**) fields: `status, run_id, gate_id, gate_queue, steps, events, message`. `_aggregate_status` (**L1056-1068**): `"degraded" if any required step failed/skipped else "completed"`. Mirror both at the parent level:

```python
# in src/construct/llm/daily_run.py (models HERE, not catalog.py — circular-import discipline)
class DailyChildStatus(BaseModel):
    model_config = {"extra": "forbid"}
    capability: str                 # "research.run" | "curation.run" | "graph.status"
    status: str                     # completed | degraded | failed | awaiting_review | skipped
    run_id: str | None = None
    pending_escalations: int = 0
    message: str = ""

class DailyRunResult(BaseModel):
    model_config = {"extra": "forbid"}
    status: Literal["completed", "degraded", "failed"]   # parent aggregate (D-07 vocabulary)
    run_id: str
    children: list[DailyChildStatus] = Field(default_factory=list)
    pending_escalations: int = 0                          # total un-written escalate items across children
    graph_health: dict = Field(default_factory=dict)      # = graph_status().data (cards/connections/domains)
    message: str = ""

def _aggregate_daily_status(children: list[DailyChildStatus], pending_escalations: int) -> str:
    """DAY-03 'no false completed': degraded if ANY child is failed/degraded/awaiting_review
    OR any escalations remain unresolved; failed only if the cycle could not run at all."""
    if all(ch.status == "failed" for ch in children):
        return "failed"
    if pending_escalations > 0 or any(ch.status in ("failed", "degraded", "awaiting_review") for ch in children):
        return "degraded"
    return "completed"
```

- **Pending-escalation count** = count `kind == "escalate"` proposals in the curation `awaiting_review` result's `gate_queue`, captured **before** the `approve_all` resume (research contributes 0 — no escalate kind). This is the D-07 surface.
- **Exit-code contract (carried from Phase 11):** a `degraded` result is still a *successful* `OperationResult` → exit 0. Only a total/hard `failed` maps to `success=False`. This is enforced by the shim wrapper (see below) which sets `success = result.status != "failed"`, exactly like `_curation_result_to_operation` (catalog.py L611-615). [Ref: memory — "Curation exit-code contract"; STATE Phase 11.]

### Registration + CLI + MCP + contract-test parity (API-01/02/03)

Clone the curation quartet mechanically. Verified reference locations:

**1. Input models** — define in `daily_run.py` (NOT catalog.py — circular-import hazard, same discipline as curation_run.py L118). Mirror `CurationRunInput` (L121-128) and `CurationInspectInput` (L131-138), including the `_validate_run_id` kebab guard:
```python
class DailyRunInput(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str | None = None
    _check_run_id = field_validator("run_id")(_validate_run_id)

class DailyInspectInput(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_path: str
    run_id: str
    _check_run_id = field_validator("run_id")(_validate_run_id)
```

**2. Catalog records** — mirror curation.run/curation.inspect (catalog.py **L433-452**):
```python
registry.register(CapabilityRecord(
    id="daily.run", name="Daily Run",
    description="Compose research.run → curation.run → graph.status into one non-blocking daily maintenance cycle; auto-applies gate recommendations, excludes escalate, never blocks on review",
    input_model=DailyRunInput, output_model=OperationResult,
    handler=_daily_run_shim,
    cli_name="daily.run", mcp_tool_name="construct_daily_run",
))
registry.register(CapabilityRecord(
    id="daily.inspect", name="Daily Inspect",
    description="Report a past daily-cycle run's persisted parent+child status and graph-health summary (read-only)",
    input_model=DailyInspectInput, output_model=OperationResult,
    handler=_daily_inspect_shim,
    cli_name="daily.inspect", mcp_tool_name="construct_daily_inspect",
))
```

**3. Shim wrappers** — clone `_curation_result_to_operation` + `_curation_run_shim` (catalog.py **L594-633**). The `*args → TypeError` guard is load-bearing (the contract test `test_shims_reject_positional_args` asserts it):
```python
def _daily_result_to_operation(cap_id, runner) -> OperationResult:
    try:
        result = runner()
    except Exception as exc:
        return OperationResult(success=False, message=f"{cap_id} failed: {type(exc).__name__}", data={"failed": True})
    return OperationResult(success=result.status != "failed", message=result.message or result.status,
                           data=result.model_dump(mode="json"))

def _daily_run_shim(*args, **kwargs):
    if args: raise TypeError("daily.run handler requires keyword arguments")
    return _daily_result_to_operation("daily.run", lambda: run_daily_run(DailyRunInput(**kwargs)))
# _daily_inspect_shim analogous → inspect_daily_run(DailyInspectInput(**kwargs))
```

**4. CLI sub-app** — mirror `curation_app` (cli.py **L368-373** declaration, **L688-718** commands). Add a `_render_daily_result` / `_emit_daily_result` pair mirroring L654-685 (render parent status + per-child lines + graph-health + pending-escalation count):
```python
daily_app = typer.Typer(no_args_is_help=True, name="daily",
                        help="Run the non-blocking daily maintenance cycle (research → curation → graph health).")
app.add_typer(daily_app)
# @daily_app.command(name="run"): --workspace/-w, --json/-j → cap.handler(workspace_path=str(workspace))
# @daily_app.command(name="inspect"): --workspace/-w, --run-id, --json/-j → cap.handler(workspace_path=..., run_id=...)
```

**5. MCP parity is FREE** — `create_server()` iterates `registry.list_mcp_tools()` and builds a FastMCP tool per record with an `mcp_tool_name` [VERIFIED: mcp/server.py L23-28; registry.py L55-61]. **Do NOT touch `mcp/server.py`.** Guard it with a `test_mcp_no_hardcoded_daily` cloned from `test_mcp_no_hardcoded_curation` (contract test L78-84) asserting `"construct_daily_run"` and `"daily.run"` do not appear in the server source.

**6. Contract test** — new `tests/contract/test_daily_run_cli_mcp.py`, cloning `test_curation_run_cli_mcp.py` verbatim in shape:
- `test_registered` (input_model set, `mcp_tool_name`/`cli_name` correct)
- `test_shims_reject_positional_args`
- `test_in_mcp_tool_list` / `test_mcp_server_exposes_daily`
- `test_mcp_no_hardcoded_daily` (API-02 guard)
- `test_cli_commands_present` (`daily run --help`, `daily inspect --help` exit 0)
- **`test_cli_mcp_schema_parity`** — the **API-03 proof**: CLI `--json` keys == `_serialize_result(handler_result)` keys == `DailyRunResult.model_fields.keys()` (mirror contract test L120-144). Run offline (see Validation Architecture for the offline degrade seam).

### `daily.inspect` persistence (read-only past-run status, D-08)

Because thin composition has **no parent LangGraph checkpoint**, `daily.inspect` needs a persisted artifact to read. Recommended (discretion — flag): at the end of `run_daily_run`, write the `DailyRunResult` JSON to `.construct/workflow/daily/<run_id>.json`; `inspect_daily_run` reads it back (missing file → `status="failed"`, `message="No such daily run."`, mirroring the curation "no such run" precedent at curation_run.py L1213-1217). This is a small derived-state file under `.construct/`, consistent with the workflow-state carve-out and the "no database owns any facts" rule (it's a run receipt, not canonical SOT). See Open Question 2.

### Anti-Patterns to Avoid
- **Parent LangGraph graph with child subgraph nodes** — nests graph-in-node + a redundant checkpoint; no durability benefit under D-01. Use plain function composition.
- **Editing `mcp/server.py`** — breaks the "parity is free" invariant; the guard test will fail. MCP tools are auto-discovered.
- **Reviving `workflow run/resume`** — Phase 12 deleted it (catalog.py L311-316 comment; `test_no_placeholder_curation_path` asserts `_get_workflow_steps` is gone). Do not re-add a `workflow` run group.
- **Re-implementing gate/apply logic in `daily.run`** — D-09 / D-05. Auto-apply = calling the child `approve_all` resume path; escalate exclusion is already in the child apply nodes.
- **Emitting events from `daily.run`** — double-logging. The children already emit the full `gate_review_*` + `workflow_step_complete` + cycle-complete trail.
- **Defining I/O models in catalog.py** — circular-import hazard (curation_run.py L118, L25 discipline). Models live in `daily_run.py`.
- **`print()` in the composition module** — stdout is the MCP JSON-RPC transport; use `logging` to stderr.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Applying gate recommendations while excluding escalate | A custom decision-resolver in `daily.run` | `review_*_run(approve_all=True)` → child `_build_resume_decisions` + existing apply nodes | Escalate exclusion + idempotent skip-if-at-target + per-item isolation + event logging already shipped and tested |
| Parent status roll-up | A new status enum + reducer | Mirror `_aggregate_status` (curation_run.py L1056) with `_aggregate_daily_status` | Same `completed/degraded/failed` vocabulary, DAY-03 "no false completed" |
| Sanitizing child failure detail | String slicing on exceptions | `_sanitize_error` (curation_run.py L296) | Never echoes raw provider text (T-11-02/T-11-06 discipline) |
| Graph-health summary | Recomputing card/connection counts | `graph_status(workspace).data` | Already returns `{cards, connections, domains}` (graph_status.py L52-67) |
| MCP tool exposure | Any `mcp/server.py` edit | Registry auto-discovery via `mcp_tool_name` | `create_server` iterates the registry (server.py L27) |
| Audit trail for auto-applied writes | Manual `append_event` calls | Child `_emit` in the apply nodes | Fires `gate_review_approved`/`_rejected` per item automatically |

**Key insight:** the entire "compose, don't duplicate" mandate reduces to *calling six functions and folding three result models*. Every hard part (HITL, checkpointing, idempotency, sanitization, event logging, MCP parity) is already solved inside the children and the registry.

## Common Pitfalls

### Pitfall 1: Treating "escalate stays pending at the gate" literally
**What goes wrong:** Planner tries to leave the curation run paused (un-resumed) so escalates "stay pending," but that means D-02's auto-apply applies nothing.
**Why it happens:** LangGraph resume is **all-or-nothing to END** — you cannot apply some proposals and leave others paused on the same thread. `Command(resume=decisions)` runs the whole apply chain to END.
**How to avoid:** Read D-03 as "escalate → **no auto-write** + surfaced as a pending-escalation **count**," not "left on an open checkpoint." `approve_all` writes the recommended promote/connection/archive items and records escalates as `escalated` (no write). Optional human review of those escalates is a *later* action (a fresh cycle or manual card review), not a resume of the now-terminal thread. **Flag for planner confirmation (Open Question 1).**
**Warning signs:** Any design that skips calling `review_curation_run` when escalates are present.

### Pitfall 2: Research child never "completes" on its own
**What goes wrong:** Composition assumes `run_research_run` returns `completed`; it doesn't write anything.
**Why it happens:** `run_research_run` **pauses at the gate** (`awaiting_review`) or returns `failed` on a total provider outage — it does not run past the review gate by itself (research_run.py L934-952).
**How to avoid:** After `run_research_run`, branch on `status == "awaiting_review"` → call `review_research_run(approve_all=True)` to perform the approved ingest. On `status == "failed"` → record degraded child, continue (D-06).
**Warning signs:** No refs/cards written despite findings; research child status shows `awaiting_review` in the final result.

### Pitfall 3: Curation empty-queue short-circuit skips the review call
**What goes wrong:** Calling `review_curation_run` on a run that never paused returns "No paused curation run to review" (curation_run.py L1163-1166).
**Why it happens:** With an empty `gate_queue`, `run_curation_run` short-circuits straight to `compile_report` and returns `completed`/`degraded` (L1094-1112, `_route_before_inbox` L988-996) — there is nothing to resume.
**How to avoid:** Only call `review_curation_run` when `run_curation_run` returned `status == "awaiting_review"`.
**Warning signs:** Spurious "No paused run" messages in the curation child status.

### Pitfall 4: Second sqlite connection / checkpoint at the parent
**What goes wrong:** Building a parent `StateGraph` opens a third checkpoint DB and a live sqlite connection wrapping the children's own.
**Why it happens:** Following the spec's "parent graph" sketch literally.
**How to avoid:** Thin composition — no parent checkpointer at all. Persist only a small `DailyRunResult` receipt JSON for `daily.inspect`.
**Warning signs:** A `daily-run.sqlite` appearing; connection-lifecycle `finally` blocks nested around child calls.

### Pitfall 5: `pending_escalations` read after resume
**What goes wrong:** Counting escalates from the *post-resume* curation result — but `CurationRunResult.gate_queue` is `[]` after a completed resume (L1109).
**Why it happens:** The gate queue is only populated on the `awaiting_review` result.
**How to avoid:** Capture `sum(1 for p in c.gate_queue if p.get("kind") == "escalate")` from the `awaiting_review` result **before** calling `review_curation_run`.

### Pitfall 6: Positional-arg shim guard
**What goes wrong:** Omitting `if args: raise TypeError(...)` in the shim; `test_shims_reject_positional_args` fails.
**How to avoid:** Copy the guard from `_curation_run_shim` (catalog.py L620-621) verbatim.

## Code Examples

Verified reference patterns (all from the current tree):

### Auto-apply recommended decisions (child resume path)
```python
# Source: src/construct/llm/curation_run.py L1117-1131 (_build_resume_decisions)
def _build_resume_decisions(inp: CurationReviewInput, gate_queue: list[dict]) -> list:
    if inp.reject_all:
        return ["reject" for _ in gate_queue]
    if inp.decisions is not None:
        return list(inp.decisions)
    # approve_all (or default): reproduce the recommended per-item decision.
    return [entry.get("decision", "approve") for entry in gate_queue]
```

### Escalate is review-only, never written
```python
# Source: src/construct/llm/curation_run.py L855-859 (apply_promotions)
# escalate is review-only this phase — record outcome, NO write.
if kind == "escalate" or decision == "escalate":
    escalated.append(card_id)
    events.append(_emit(workspace, "gate_review_rejected", card_id, "escalated (review-only)"))
    continue
```

### Shim → OperationResult with the degraded-exits-0 contract
```python
# Source: src/construct/capabilities/catalog.py L594-624 (curation shim — clone for daily)
def _curation_result_to_operation(cap_id, runner) -> OperationResult:
    try:
        result = runner()
    except Exception as exc:
        return OperationResult(success=False, message=f"{cap_id} failed: {type(exc).__name__}", data={"failed": True})
    return OperationResult(success=result.status != "failed",   # degraded → success=True → exit 0
                           message=result.message or result.status, data=result.model_dump(mode="json"))
```

### MCP auto-discovery (why you never edit server.py)
```python
# Source: src/construct/mcp/server.py L23-28
def create_server() -> FastMCP:
    ...
    for entry in registry.list_mcp_tools():        # every record with mcp_tool_name
        cap = registry.get_by_mcp_name(entry["name"])
        # ... FastMCP tool built from the record — no per-capability wiring
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `workflow.run daily-cycle` placeholder driving fake-success steps | Real child capabilities `research.run` + `curation.run`; `workflow.run` **removed** | Phase 12 (D-10/CUR-05) | `daily.run` composes real children; must NOT revive `workflow run/resume` |
| Spec sketch: "LangGraph parent graph … subgraphs" (spec-v04 L101/L355/L578) | Thin Python composition of child runner functions (D-09) | Phase 13 CONTEXT | Parent graph is superseded; DAY-01 needs composition, not a graph |
| Direct `WebSearch`/`WebFetch`/workspace writes in skills | Skills delegate to CLI/MCP capabilities (API-04, done Phase 12) | Phase 12 | The daily-cycle **skill** (D-10) invokes `daily.run` + owns the single post-run views refresh |

**Deprecated/outdated:**
- `workflow run` / `workflow resume` CLI group and the `_get_workflow_steps` placeholder — deleted in Phase 12; asserted absent by `test_no_placeholder_curation_path`. Do not reintroduce.
- `CONSTRUCT-CLAUDE-impl/.../workflows/daily-cycle.md` references `construct workflow run daily-cycle` (now-removed) — treat as historical; the capability is `construct daily run`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-03 "escalate stays pending at the child's gate (checkpoint persisted)" is satisfied by "escalate not auto-written + surfaced as a pending count," NOT by leaving the curation thread paused. Resume is all-or-nothing to END, so literal "stays paused" is incompatible with D-02 auto-apply. | Auto-apply mechanism / Pitfall 1 / Open Q1 | If the user truly wants the thread left paused for later `curation review`, then `daily.run` must **not** resume curation when escalates exist — which means D-02 applies *nothing* that cycle. These are mutually exclusive; the planner/discuss must confirm the intended reading. |
| A2 | `daily.inspect` reads a persisted `DailyRunResult` receipt JSON under `.construct/workflow/daily/<run_id>.json` (no parent LangGraph checkpoint exists in thin composition). | daily.inspect persistence / Open Q2 | If a different inspect source is wanted (e.g. re-deriving from child inspects via stored child run_ids), the persistence design changes. Low risk — receipt file is simplest and consistent with `.construct/` carve-out. |
| A3 | Each child is given a derived child `run_id` (`<daily-run-id>-research` / `-curation`) so child inspect/review remain addressable and kebab-valid. | Composition Flow | If children must share the parent `run_id` exactly, the two child sqlite threads would collide only across *different* DB files (they use separate DBs) — low risk, but suffix form is safer and unambiguous. |
| A4 | API-05 proof = additive-only change + full existing suite green (390 baseline). No dedicated v0.3-compat harness beyond the existing `tests/contract/test_mcp_contracts.py` + full suite. | API-05 approach / Validation | If a formal per-requirement compat checklist is expected, more explicit assertions may be needed. Low risk — additive change with green full suite is the established gate. |

## Open Questions (RESOLVED)

*All three resolved before plan lock (2026-07-06). Kept for traceability.*

1. **D-03 exact semantics (escalate handling). — (RESOLVED)** *What we knew:* the child `approve_all` path writes recommended promote/connection/archive and records escalates as un-written (`escalated`), then the run completes. *What was unclear:* whether the user wanted escalates literally left on an open, resumable checkpoint (which forbids applying anything else that pass — contradicts D-01/D-02) vs. "not written + surfaced as a pending count" (compatible). **RESOLVED by CONTEXT.md D-03a (locked 2026-07-06, user-confirmed):** adopt the compatible reading — auto-apply recommendations, escalate items get NO canonical write and are surfaced as a pending-escalation count (forces `degraded`, never bare `completed`); escalates recoverable later via the child's own `review` command on a fresh run.
2. **`daily.inspect` persistence location/format. — (RESOLVED)** *What we knew:* thin composition has no parent checkpoint; a small receipt is needed. **RESOLVED (research recommendation adopted by plan 13-01):** `.construct/workflow/daily/<run_id>.json` holding the serialized `DailyRunResult`; missing → `failed` (mirrors curation "no such run" at curation_run.py L1213-1217). This is Claude's Discretion per CONTEXT.md.
3. **Auto-apply flag surface. — (RESOLVED)** *What we knew:* default is auto-apply (D-02); discretion allows an opt-out flag. **RESOLVED (research recommendation adopted by the plans):** ship default-on with **no** flag this phase (deferred flags stay out per Deferred Ideas); revisit only if an attended mode is ever wanted.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python + pytest | build + tests | ✓ | project venv (testpaths=`tests`, pyproject.toml L40-41) | — |
| langgraph / langgraph-checkpoint-sqlite | child runners (transitive) | ✓ | already used by shipped `research.run`/`curation.run` | — |
| Search provider API key (Tavily/Anthropic) | research child **happy path** only | ✗ (offline in CI) | — | Research child degrades to `failed` on total outage → daily `degraded`, exit 0 (the DAY-03/D-06 path). Offline happy-path uses the shipped **mock search provider** (`src/construct/search/providers/mock.py`) + fixtures (SRCH-03) and the `build_chat_model` monkeypatch seam (tests/llm/conftest.py L156). |

**Missing dependencies with no fallback:** none — the phase is code-only over existing deps.
**Missing dependencies with fallback:** live provider keys → offline mock provider + degrade path (both are *desired* test paths, not blockers).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`[tool.pytest.ini_options]`, pyproject.toml L40) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`) |
| Quick run command | `pytest tests/contract/test_daily_run_cli_mcp.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DAY-01 | `daily.run` composes children (no duplicated logic) | integration (offline mock) | `pytest tests/llm/test_daily_run.py::test_composes_children -x` | ❌ Wave 0 |
| DAY-02 | Result surfaces parent+child status, pending escalations, graph-health | unit | `pytest tests/llm/test_daily_run.py::test_result_surface -x` | ❌ Wave 0 |
| DAY-03 | Safe when a child fails/pauses (isolate+degrade; no false completed) | unit | `pytest tests/llm/test_daily_run.py::test_degrade_on_child_failure -x` | ❌ Wave 0 |
| API-01 | `daily.run`/`daily.inspect` registered with schemas + CLI + MCP metadata | contract | `pytest tests/contract/test_daily_run_cli_mcp.py::test_registered -x` | ❌ Wave 0 |
| API-02 | Invokable via registry from CLI + auto-discovered MCP (no server edit) | contract | `pytest tests/contract/test_daily_run_cli_mcp.py::test_mcp_no_hardcoded_daily -x` | ❌ Wave 0 |
| API-03 | CLI `--json` == MCP-serialized == `DailyRunResult.model_fields` | contract | `pytest tests/contract/test_daily_run_cli_mcp.py::test_cli_mcp_schema_parity -x` | ❌ Wave 0 |
| API-05 | v0.3 CLI/MCP/validation/ingest/graph/ask-domain still pass | regression | `pytest` (full suite green; additive change only) | ✅ existing suite (`tests/contract/test_mcp_contracts.py` + 46 files) |

### Sampling Rate
- **Per task commit:** `pytest tests/contract/test_daily_run_cli_mcp.py tests/llm/test_daily_run.py -x`
- **Per wave merge:** `pytest tests/contract tests/llm`
- **Phase gate:** full `pytest` green (regression proof for API-05) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/contract/test_daily_run_cli_mcp.py` — clone of `test_curation_run_cli_mcp.py`; covers API-01/02/03 (RED until registration + CLI land). Include `test_mcp_no_hardcoded_daily` as the GREEN guardrail.
- [ ] `tests/llm/test_daily_run.py` — composition/degrade/auto-apply/result-surface unit + integration tests; covers DAY-01/02/03. Reuse `tests/llm/conftest.py::create_test_workspace` (L169) and the `build_chat_model` monkeypatch seam (L156); use the mock search provider for the happy path and no-API-key for the degrade path.
- [ ] No framework install needed — pytest is configured.

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (absent = enabled), so this section is included. This phase adds **no** new network, auth, crypto, or external-data-parsing surface — it composes existing internal capabilities. Applicable controls are narrow.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local-first CLI/stdio MCP; no auth surface (v0.4 out-of-scope excludes auth) |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No multi-user runtime |
| V5 Input Validation | **yes** | Pydantic `extra="forbid"` on `DailyRunInput`/`DailyInspectInput` + `_validate_run_id` kebab guard (blocks path traversal via `run_id` → sqlite/thread path). Mirror curation_run.py L61-73. |
| V6 Cryptography | no | None introduced |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `run_id` path traversal into `.construct/workflow/daily/<run_id>.json` | Tampering | `_validate_run_id` (`KEBAB_CASE_PATTERN`) on both input models — the same guard the children already enforce (curation_run.py L61-73). **Critical**: the receipt-file path is derived from `run_id`, so the validator MUST be applied before any path join. |
| Leaking raw provider/exception text in child-failure detail | Information Disclosure | `_sanitize_error` (curation_run.py L296) for any caught child exception; shim uses `type(exc).__name__` only (catalog.py L608). |
| Secrets written to stdout (breaks MCP JSON-RPC + leaks) | Information Disclosure | `logging` to stderr only; never `print` in the composition module. |
| Unattended auto-write bypassing HITL (D-05 departure) | Elevation / Tampering | Bounded by construction: escalates never written (child apply nodes); all writes event-logged (D-04); children's own HITL contract unchanged (auto-apply lives only in `daily.run`). |

## Sources

### Primary (HIGH confidence — direct source reads, this session)
- `src/construct/llm/research_run.py` — L108-174 (input/result models), L900-954 (`run_research_run`), L960-993 (`_completion_result`, `_build_resume_decisions`), L996-1035 (`review_research_run`), L1038-1081 (`inspect_research_run`).
- `src/construct/llm/curation_run.py` — L61-73 (`_validate_run_id`), L121-208 (input/proposal/result models), L296-324 (`_sanitize_error`, `_emit`), L663-759 (producers + `process_inbox`), L765-802 (`_normalize_decision`, `_resolve_decisions`), L824-982 (apply nodes), L1056-1068 (`_aggregate_status`), L1071-1114 (`run_curation_run`), L1117-1131 (`_build_resume_decisions`), L1134-1179 (`review_curation_run`), L1182-1227 (`inspect_curation_run`).
- `src/construct/capabilities/catalog.py` — L291-301 (`graph.status` record), L311-324 (`workflow.run` removal + `workflow.status`), L400-462 (research/curation records), L533-643 (result→operation shims).
- `src/construct/cli.py` — L361-373 (research/curation sub-apps), L654-767 (curation render + commands).
- `src/construct/mcp/server.py` L23-28 + `src/construct/capabilities/registry.py` L24-61 (MCP auto-discovery).
- `src/construct/pipelines/graph_status.py` L12-79 (health-summary shape).
- `src/construct/services/event_log.py` L13-41 (`append_event`, non-blocking).
- `tests/contract/test_curation_run_cli_mcp.py` L1-145 (contract-test shape + `test_mcp_no_hardcoded_curation`).
- `.planning/config.json`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md`.

### Secondary (MEDIUM confidence)
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` L83/L97-115/L355/L484/L578 (daily-cycle rows + "parent graph" gesture — flagged as superseded by D-09).

## Metadata

**Confidence breakdown:**
- Architecture (thin vs graph): **HIGH** — grounded in verified child signatures, checkpointer/thread ownership, and D-01's no-parent-interrupt constraint.
- Auto-apply mechanism (D-02/D-03): **HIGH** for the reuse path; the D-03 "stays pending" nuance is a flagged assumption (A1/Open Q1) requiring user confirmation.
- Registration/CLI/MCP/contract parity: **HIGH** — mechanical clone of the verified curation quartet.
- Result shape / status aggregation: **HIGH** — mirrors verified `CurationRunResult` + `_aggregate_status`.
- API-05 proof approach: **MEDIUM-HIGH** — additive change + full-suite green is the established gate; no dedicated compat harness needed (A4).

**CONTEXT.md line-number verification:** All child-function refs verified accurate — `run_research_run` L900 ✓, `review_research_run` L996 ✓, `inspect_research_run` L1038 ✓, `run_curation_run` L1071 ✓, `review_curation_run` L1134 ✓, `inspect_curation_run` L1182 ✓, `workflow.run` removal ~L311-316 ✓, `test_mcp_no_hardcoded_curation` present ✓. **Minor drift:** CONTEXT says the catalog research/curation records sit at "L201-390" — the specific research.run/curation.run `CapabilityRecord`s are actually at **L400-462** (L201-390 is the broader registration region); the shims are at L533-643. No functional impact.

**Research date:** 2026-07-06
**Valid until:** ~2026-08-06 (stable internal codebase; no fast-moving external deps).
