# Phase 11: Curation PIPE Steps - Research

**Researched:** 2026-06-28
**Domain:** Deterministic LangGraph workflow (Python-only) — curation maintenance steps, mirroring `research.run`
**Confidence:** HIGH (all targets are in-repo, verified by direct read; no external/training-data dependence)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `curation.run` is a **new LangGraph capability** (its own module, mirroring `research.run` in `src/construct/llm/research_run.py`) — **not** the legacy `workflow.run curation-cycle` WorkflowRunner path.
- **D-02:** Wire the **full durability machinery now**: `SqliteSaver` checkpointer + run-id + resume/inspect surface, matching `research.run`. Phase 11's graph is linear (no interrupts yet); Phase 12 grafts `interrupt()` review nodes onto the already-durable graph.
- **D-03:** Build the graph to the **spec §4.3 topology whole** from the start so Phase 12 swaps node bodies (skip → gate/interrupt) rather than restructuring the graph.
- **D-04:** Decay and orphan steps are **findings-only** (counts + candidate card IDs + rationale in the step result). No proposal/queue schema committed in Phase 11 (zero coupling to Phase 12 queue format).
- **D-05:** Step thresholds read from **`governance.yaml`** — `decay.decay_window_days` drives decay-scan, `quality.orphan_tolerance_days` drives orphan-scan. No hardcoded thresholds.
- **D-06:** `decay.auto_archive_on_decay` is **reported but never acted on** in Phase 11. The decay step only reports candidates + notes "auto_archive_on_decay=true — archiving deferred to Phase 12 reviewed path." **Phase 11 performs no canonical writes.**
- **D-07:** Introduce a **`CurationStepResult`** model carrying a **structured findings payload** (machine-readable counts + candidate ID lists per step) **plus** a human-readable summary line.
- **D-08:** **Per-step status = `completed` / `skipped` / `failed`** (no per-step "degraded"; any per-item error fails the step).
- **D-09:** **Run-level aggregate status = `completed` / `degraded` / `failed`**, where **degraded = run finished but ≥1 step failed (or a non-optional step was skipped)**, `completed` = all steps completed/optional-skipped, `failed` = run aborted.
- **D-10:** `promotion-scan` (L3) and `process-inbox` (HUMAN) appear as **explicit nodes that report `skipped — deferred to Phase 12`**. `views_refresh_hook` likewise reports **skipped**. Skip ≠ fake success.
- **D-11:** The **legacy `workflow.run curation-cycle` placeholder lambdas** (`catalog.py:658–667`) are **left untouched in Phase 11** (coexist). Flag the surviving legacy fake-success path for Phase 12 (CUR-05).

### Claude's Discretion
- Exact per-step findings field names and `CurationStepResult` schema shape (pass through what `workspace.validate` / `graph.status` / `bridge.detect` already return where possible).
- Module location for the curation graph (`src/construct/llm/` vs `src/construct/pipelines/`) — follow `research.run` precedent.
- Run-id/inspect CLI command naming — follow `research.run` precedent.

### Deferred Ideas (OUT OF SCOPE)
- L3 `promotion-scan` gate (`card.evaluate`), `process-inbox` human-review queue, connection typing/writes, decay auto-archive application, research/curation skill migrations — all Phase 12 (CUR-02..05 + API-04).
- Structured proposal/queue handoff between curation steps and Phase 12 review gates (D-04).
- Legacy `workflow.run curation-cycle` placeholder removal — Phase 12 / CUR-05.
- Full `views.generate_data` emission (ADV-03) — Phase 11 only reports views_refresh_hook as skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CUR-01 | User can run `curation.run` through the CLI/MCP surface and receive real integrity, decay, orphan, connection, and report results instead of placeholder success responses. | The five deterministic steps each wrap an existing real function (`validate_workspace`, governance-threshold card scans, `bridge_detect`, `graph_status`) and return a `CurationStepResult` with concrete counts/IDs. Graph + checkpointer + capability registration mirror the verified `research.run` template (`src/construct/llm/research_run.py`). |

**ROADMAP success criteria mapped:**
1. Run `curation.run` from CLI + stdio MCP, receive real integrity/decay/orphan/connection-health/report output → capability registration (catalog.py) + 5 real step handlers.
2. Distinguish completed / degraded / skipped → per-step status (D-08) + run aggregate (D-09) + explicit skipped-deferred nodes (D-10).
3. No placeholder success for deterministic steps; each reported step includes concrete findings/counts or explicit degraded/skipped → anti-placeholder contract test (Validation Architecture below).
</phase_requirements>

## Summary

Phase 11 builds `curation.run` as a near-exact structural sibling of the already-shipped `research.run` (`src/construct/llm/research_run.py`, Phase 10). The pattern is fully verified in-repo: a `StateGraph` over a `TypedDict` state channel, a persistent `SqliteSaver` checkpointer opened under `.construct/workflow/`, a kebab-validated run-id used as the LangGraph `thread_id`, and run-start/inspect runners wrapped by dual-mode RT-03 shims registered in `catalog.py`. The single difference this phase: the curation graph is **linear with no `interrupt()`** — every node runs to completion in one `graph.invoke`. Phase 12 later grafts the `interrupt()` review gate onto this already-durable graph (D-02/D-03).

The five real deterministic steps each wrap an existing, verified function and pass its return shape through into a new `CurationStepResult` (D-07): **integrity-check** → `validate_workspace()` (returns `ValidationReport` with `.errors`/`.warnings`/`.ok`); **compile-report** → `graph_status()` (card/connection/domain counts); **connection-health** → `bridge_detect()` (L1/L2 structural bridge candidates; its L3 LLM tier auto-skips offline when `ANTHROPIC_API_KEY` is unset, keeping the step deterministic); **decay-scan** and **orphan-scan** are new but trivial — they iterate cards, compare each card's age against `governance.yaml` thresholds (`decay.decay_window_days=28`, `quality.orphan_tolerance_days=7`) and a connection-degree count from `connections.json`, and emit candidate IDs only (findings-only, D-04). Three nodes (`promotion_review`, `process_inbox`, `views_refresh_hook`) are present in the graph but return `status=skipped` with a "deferred to Phase 12" reason (D-10), so the full spec §4.3 topology is visible with honest gaps.

No external packages are needed — `langgraph 1.2.4`, `langgraph-checkpoint-sqlite 3.1.0`, `pydantic 2.13.4` are already installed and battle-tested by `research.run`. The principal risks are subtle, not structural: (1) `bridge_detect()` writes derived artifacts (`log/bridge-candidates.json`, `views/build/data/bridges.json`) as a side effect — this is **not** a canonical SOT write so it honors D-06, but the plan must not describe connection-health as "pure read-only"; (2) the run-level `degraded` vs `completed` discrimination (D-09) must be computed from per-step statuses, not from any single step; (3) cards have no explicit "last touched" timestamp — decay age must be derived from `created`/`last_verified` dates (documented below).

**Primary recommendation:** Create `src/construct/llm/curation_run.py` as a faithful sibling of `research_run.py`. Define `CurationStepResult` and `CurationRunResult` Pydantic models in that module (not `catalog.py` — avoid the circular-import hazard). Build a linear `StateGraph` over a `CurationRunState` TypedDict containing the full spec §4.3 node sequence; real steps wrap existing functions, deferred steps emit `skipped`. Register `curation.run` and `curation.inspect` in `catalog.py` with dual-mode shims mirroring `_research_run_shim`/`_research_inspect_shim`. Defer `curation.review`/resume to Phase 12 (no interrupt exists to resume yet).

## Architectural Responsibility Map

CONSTRUCT's layers (spec §5.1). This is a backend phase; "tier" = architectural layer.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `curation.run` orchestration (graph, checkpointer, run-id) | Layer 2 — Python workflow runtime (LangGraph) | Layer 3 — Invoke surface (CLI/MCP) | Mirrors `research.run`; node names map to catalog capability IDs (spec §5.1 rule). |
| integrity-check step | Layer 2 (PIPE handler) | Layer 1 — Workspace SOT (read) | Wraps `validate_workspace()` (`services/validation.py`); reads cards/refs/connections/configs read-only. |
| decay-scan / orphan-scan steps | Layer 2 (PIPE handler) | Layer 1 (read) | New deterministic scans; read cards + connections + governance thresholds; emit findings only (D-04). |
| connection-health step | Layer 2 (PIPE handler) | Layer 1 (read) + derived-data write | Wraps `bridge_detect()`; reads SOT, writes **derived** `log/`+`views/build/data/` (not canonical — D-06 honored). |
| compile-report step | Layer 2 (PIPE handler) | Layer 1 (read) | Wraps `graph_status()`; read-only health roll-up. |
| Capability registration (CLI + MCP parity) | Layer 3 — Invoke surface | Layer 0 — catalog semantics | `CapabilityRecord` in `catalog.py` with `cli_name` + `mcp_tool_name`; MCP auto-discovers (no `mcp/server.py` edit). |
| Deferred nodes (promotion_review, process_inbox, views_refresh_hook) | Layer 2 (skip-emitting stubs) | — | Present for topology completeness (D-03/D-10); bodies become real in Phase 12. |

## Standard Stack

### Core
| Library | Version (verified) | Purpose | Why Standard |
|---------|--------------------|---------|--------------|
| `langgraph` | 1.2.4 `[VERIFIED: .venv importlib.metadata]` | `StateGraph`, `START`/`END`, `.compile(checkpointer=...)`, `.invoke`, `.get_state` | Already the orchestration engine for `research.run`; the curation graph is its sibling. |
| `langgraph-checkpoint-sqlite` | 3.1.0 `[VERIFIED: .venv]` | `SqliteSaver` durable checkpointer | Same durability story as `research.run` (D-02); D-02 milestone carve-out permits SQLite under `.construct/` for workflow state only. |
| `langgraph-checkpoint` | 4.1.1 `[VERIFIED: .venv]` | Checkpointer base (transitive) | Pulled in by the sqlite saver; no direct import. |
| `pydantic` | 2.13.4 `[VERIFIED: .venv]` | `CurationStepResult` / `CurationRunResult` / input models | All workspace schemas + `OperationResult` are pydantic v2. |
| `typer` | 0.26.7 `[VERIFIED: .venv]` | `curation` CLI command group | Mirror the `research_app` Typer sub-app pattern. |

### Supporting (all in-repo, no install)
| Module / function | Location | Purpose in this phase |
|-------------------|----------|------------------------|
| `validate_workspace(root) -> ValidationReport` | `src/construct/services/validation.py:106` | integrity-check step source. Returns `ValidationReport` (dataclass: `.errors`, `.warnings`, `.ok`, `.by_file`); findings are `ValidationFinding(severity, path, message)`. |
| `graph_status(workspace) -> OperationResult` | `src/construct/pipelines/graph_status.py:12` | compile-report step source. `.data` = `{cards:{total,by_lifecycle,by_domain}, connections:{total,by_type}, domains:{total,names}, workspace}`. |
| `bridge_detect(workspace_path) -> OperationResult` | `src/construct/pipelines/bridge_detect.py:52` | connection-health step source. `.data["summary"]["totals"]` = `{confirmed, strong_candidates, medium_candidates, weak_candidates}`; `.data["summary"]["l1_l2_only"]` flags L3-skipped. |
| `WorkspaceLoader` | `src/construct/storage/workspace.py:38` | `load_cards()` (list[dict] incl. `id`/`created`/`lifecycle`/`last_verified`), `load_connections()`, `load_governance()`. |
| `GovernanceConfig` / `DecayConfig` / `QualityConfig` | `src/construct/schemas/config.py:194/162/169` | threshold source (D-05). `decay.decay_window_days`, `decay.auto_archive_on_decay`, `quality.orphan_tolerance_days`. |
| `append_event(workspace, agent, action, target=, detail=)` | `src/construct/services/event_log.py` | non-blocking audit events (§6.6). Use `EventAgent.curator`. |
| `OperationResult(success, message, data)` | `src/construct/services/knowledge.py` | the envelope the shim returns; `CurationRunResult` rides in `.data`. |
| `KEBAB_CASE_PATTERN` | `src/construct/schemas/config.py:14` | run-id trust-boundary validation (CR-01), exactly as `research_run._validate_run_id`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `curation.run` LangGraph module | Legacy `WorkflowRunner` + `_get_workflow_steps("curation-cycle")` | **Rejected by D-01.** WorkflowRunner is the path being superseded; would fork the durability model. Left intact (D-11). |
| Module at `src/construct/llm/curation_run.py` | `src/construct/pipelines/curation_run.py` | `llm/` chosen: `research_run.py` lives there and §11 mitigation targets converging both workflows in one orchestration module. The "no LLM this phase" fact does not outweigh sibling-locality. (Discretion item — either is acceptable; recommend `llm/`.) |
| Register `curation.run` + `curation.inspect` now | Also register `curation.review`/resume now | No `interrupt()` exists in Phase 11's linear graph, so there is nothing to resume. Register review/resume in Phase 12 with the gate. inspect is still useful (reads final/persisted state). |

**Installation:** None. All dependencies are already declared in `pyproject.toml` (`langgraph>=0.2`, `langgraph-checkpoint-sqlite>=3.1,<4`, `pydantic>=2.7`, `typer>=0.12`) and installed in `.venv`.

## Package Legitimacy Audit

**No external packages are installed in this phase.** Every dependency is already present and exercised by the shipped `research.run` workflow (Phase 10). slopcheck/registry verification is not applicable — there is nothing new to vet.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none — phase is internal Python only) | — | N/A |

## Architecture Patterns

### System Architecture Diagram

```text
construct CLI  ──┐                         ┌─ curation.run  (run-start: invoke graph to completion)
                 ├─ get_registry().get(id) ┤
stdio MCP server ┘  (RT-03 dual-mode shim) └─ curation.inspect (read-only get_state; no advance)
                                                     │
                                                     ▼
                              build_curation_run_graph(checkpointer)  [src/construct/llm/curation_run.py]
                                                     │  thread_id = run_id (kebab-validated)
                                                     ▼
   START → integrity_check → decay_scan → orphan_scan → promotion_review(SKIP)
         → connection_maintenance → process_inbox(SKIP) → compile_report
         → views_refresh_hook(SKIP) → END
                                                     │
        each real node:  rebuild WorkspaceLoader INSIDE node  ─► call existing fn ─► CurationStepResult
                                                     │
                          SqliteSaver  ──────────────┘  (.construct/workflow/curation-run.sqlite)
                                                     │
        terminal node: aggregate per-step statuses → run status (completed|degraded|failed),
                       append_event(curator, "curation_cycle_complete"), return CurationRunResult
                                                     │
                                                     ▼
                         OperationResult(success = status != "failed", data = CurationRunResult dump)
```

Data flow trace (primary use case): a CLI `construct curation run -w <ws>` call resolves `curation.run` from the registry → shim builds the graph + opens the checkpointer → `graph.invoke(initial_state, {"thread_id": run_id})` runs all nodes in order → real nodes read the workspace SOT read-only and produce `CurationStepResult`s with concrete counts/IDs → deferred nodes emit `skipped` → the terminal node rolls up the run status and emits the `curation_cycle_complete` event → the shim wraps the `CurationRunResult` in an `OperationResult` → CLI renders a table / `--json` dumps it. No human pause this phase.

### Recommended Project Structure
```
src/construct/
├── llm/
│   ├── research_run.py        # EXISTING — the template to mirror
│   └── curation_run.py        # NEW — CurationRunState, CurationStepResult,
│                              #       CurationRunResult, step nodes, graph builder,
│                              #       checkpointer, run/inspect runners
├── capabilities/
│   └── catalog.py             # EDIT — register curation.run + curation.inspect
│                              #        + _curation_run_shim / _curation_inspect_shim
├── cli.py                     # EDIT — add `curation` Typer sub-app (run / inspect)
tests/
├── llm/test_curation_run.py           # NEW — Wave-0 red suite (node + graph + scans)
└── contract/test_curation_run_cli_mcp.py  # NEW — CLI/MCP parity + offline smoke
```

### Pattern 1: TypedDict state with plain-serializable channels only
**What:** `CurationRunState(TypedDict)` holding `workspace_path: str`, `run_id: str`, the per-step result dicts, an accumulating `steps: list[dict]`, `status: str`, `events: list[str]`. NEVER store a `WorkspaceLoader`, sqlite connection, or any object in state.
**When to use:** Always — the checkpointer serializes state to SQLite; non-serializable channels break `get_state`/resume (research_run.py:68, Pitfall 3, empirically confirmed in Phase 10).
**Example:**
```python
# Source: src/construct/llm/research_run.py:71-103 (verified pattern)
class CurationRunState(TypedDict):
    workspace_path: str
    run_id: str
    # populated by load_config
    decay_window_days: int
    auto_archive_on_decay: bool
    orphan_tolerance_days: int
    # accumulated per-step results (CurationStepResult dumps)
    steps: list[dict]
    # output
    status: str          # running | completed | degraded | failed
    events: list[str]
```

### Pattern 2: Rebuild WorkspaceLoader INSIDE each node
**What:** Each node does `from construct.storage.workspace import WorkspaceLoader` and `WorkspaceLoader(Path(state["workspace_path"]))` locally; reads config/cards; returns a partial-state dict.
**When to use:** Every node. Mirrors `research_run.load_config` (research_run.py:225-240). Keeps state serializable.

### Pattern 3: Persistent SqliteSaver (no connection-string footgun)
**What:** Open `sqlite3.connect(db, check_same_thread=False)` once, wrap in `SqliteSaver(conn)`, keep alive for the whole handler, close in `finally`. DB at `.construct/workflow/curation-run.sqlite`.
**When to use:** The run/inspect runners. Mirrors `research_run._open_checkpointer` (research_run.py:879-894). Do NOT use the `SqliteSaver.from_conn_string(...)` context-manager form — it closes the connection on block exit and breaks cross-process inspect (Phase 10 RESEARCH Pitfall 2).
**Example:**
```python
# Source: src/construct/llm/research_run.py:879-894 (verified pattern)
def _open_checkpointer(workspace: Path):
    from langgraph.checkpoint.sqlite import SqliteSaver
    db = Path(workspace) / ".construct" / "workflow" / "curation-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    return SqliteSaver(conn), conn
```

### Pattern 4: Dual-mode RT-03 shim + RunResult→OperationResult wrap
**What:** A keyword-only shim that constructs the input model from `**kwargs`, runs the runner, and wraps the result `RunResult` in a sanitizing `OperationResult` (`success = status != "failed"`). Positional calls raise `TypeError`.
**When to use:** Registering `curation.run`/`curation.inspect`. Mirror `_research_run_shim` + `_run_result_to_operation` (catalog.py:481-539). There is no provider-outage path in deterministic curation, so the wrapper can be simpler than `_run_result_to_operation` (no `ResearchScoreOutageError` branch needed), but keep the generic `except Exception` → sanitized message guard.

### Anti-Patterns to Avoid
- **Returning a placeholder `OperationResult(success=True, message="…placeholder")`** — this is exactly the v0.3 behavior CUR-01/criterion #3 exists to kill. Every real step must carry concrete findings; the anti-placeholder test asserts on this.
- **Computing run `degraded` from a single step** — `degraded` is a roll-up over ALL per-step statuses (D-09). Compute it in the terminal node.
- **Describing connection-health as pure read-only** — `bridge_detect()` writes derived artifacts (see Pitfall 1). It performs no canonical SOT write, but the filesystem is touched.
- **Storing the WorkspaceLoader / sqlite conn in state** — breaks checkpoint serialization (Pattern 1).
- **Editing `mcp/server.py`** — MCP parity is free via registry auto-discovery; the contract test asserts no `curation`-specific string appears in `mcp/server.py` (mirror `test_mcp_server_has_no_hardcoded_research_run`).
- **Using `interrupt()` this phase** — the graph is linear (D-02). Adding an interrupt now is Phase 12 scope.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workspace integrity checks | A new card/connection/ref validator | `validate_workspace()` (`services/validation.py:106`) | Already validates cards, connection→card refs, ref domains/clusters, events; returns structured `ValidationReport`. |
| Graph health roll-up | New lifecycle/domain/connection counters | `graph_status()` (`pipelines/graph_status.py:12`) | Already produces `by_lifecycle`, `by_domain`, `by_type`, totals. |
| Connection / bridge candidate detection | New cross-domain edge scanner | `bridge_detect()` (`pipelines/bridge_detect.py:52`) | L1 structural + L2 category overlap (deterministic); L3 LLM tier auto-skips offline. |
| Durable run-id / checkpoint / inspect | New state-persistence layer | `SqliteSaver` + the `research_run.py` runner pattern | Phase 10 already solved cross-process durability + the connection-lifetime footgun. |
| CLI/MCP dual exposure | Separate CLI parser + MCP tool defs | One `CapabilityRecord` with `cli_name`+`mcp_tool_name` | RT-03 shim serves both surfaces; MCP auto-discovers. |
| Governance threshold loading | Reading/parsing governance.yaml ad hoc | `WorkspaceLoader(ws).load_governance()` → `.decay` / `.quality` | Validated pydantic config; thresholds already typed. |
| run-id safety | Custom sanitization | Reuse `_validate_run_id` + `KEBAB_CASE_PATTERN` | CR-01 path-traversal guard, identical to research_run. |

**Key insight:** Four of the five "real" steps are thin adapters over functions that already exist and are already tested. The genuine new logic is small: (a) decay/orphan candidate selection (date math + degree count), (b) the `CurationStepResult` contract, and (c) the run-level status aggregation. Everything else is structural mirroring.

## Runtime State Inventory

> This is a greenfield capability (new module + new graph + new SQLite DB), not a rename/refactor. There is **no existing curation runtime state to migrate**.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | New checkpoint DB `.construct/workflow/curation-run.sqlite` is created fresh by this phase. No existing curation run state exists. | None — created on first run. Ensure `.construct/` is gitignored (already done in Phase 10 for `research-run.sqlite`; verify the same ignore covers `curation-run.sqlite`). |
| Live service config | None — no external service holds curation state. | None — verified: curation has only the in-repo placeholder lambdas. |
| OS-registered state | None. | None. |
| Secrets/env vars | `ANTHROPIC_API_KEY` is read **optionally** by `bridge_detect`'s L3 tier; absent → L3 skipped gracefully. No new secret introduced. | None — connection-health stays deterministic without it. |
| Build artifacts | None. | None. |

**Coexistence note (D-11):** The legacy `_get_workflow_steps("curation-cycle")` placeholder lambdas (`catalog.py:658-667`) and the `workflow.run` capability remain untouched. They are a **separate** capability path from the new `curation.run`. Flag for Phase 12 (CUR-05): the legacy `workflow.run curation-cycle` still returns fake-success messages and must be removed/redirected there.

## Common Pitfalls

### Pitfall 1: connection-health silently writes derived files
**What goes wrong:** `bridge_detect()` calls `_persist_candidates()` which writes `log/bridge-candidates.json` and `views/build/data/bridges.json` (bridge_detect.py:527-547). A plan that asserts "curation.run makes zero filesystem writes" will be wrong.
**Why it happens:** `bridge_detect` was built as a standalone pipeline that persists its output.
**How to avoid:** Scope the D-06 invariant precisely: **no canonical SOT writes** (cards/refs/connections.json/search-seeds.json/digests/events as facts). Derived-data writes under `log/` and `views/build/data/` are allowed (they are classified `derived`/`support` by `WorkspaceLoader.classify`). State this explicitly in the plan and in the no-canonical-writes test (assert cards/refs/connections.json/search-seeds.json are byte-identical before/after; do NOT assert on `log/` or `views/`).
**Warning signs:** A test asserting an empty `log/` dir after a run fails.

### Pitfall 2: cards have no "last activity" timestamp for decay
**What goes wrong:** Decay-scan needs each card's age, but `KnowledgeCard` (schemas/card.py:92) has only `created: date` and optional `last_verified: date | None` — there is no "last_modified" or "last_touched" field.
**Why it happens:** The workspace model is file-based; modification recency is not tracked in card frontmatter.
**How to avoid:** Define decay age as `today - (last_verified or created)`. Document this as the candidate-selection rule. A card is a decay candidate when that age exceeds `decay_window_days` AND `lifecycle != archived`. (This is a deterministic, defensible rule; it is **not** a locked decision — surface it in the Assumptions Log for the planner/discuss to confirm.)
**Warning signs:** Decay-scan returns every card or no card regardless of threshold → age source mis-wired.

### Pitfall 3: orphan degree must count BOTH directions and both edge sources
**What goes wrong:** Counting only `connections.json` `from_` (outgoing) misses cards that are only targets, over-reporting orphans.
**Why it happens:** Connections are directed records (`from_`/`to`).
**How to avoid:** A card's degree = number of `ConnectionRecord`s where it is `from_` OR `to` in `connections.json`. (Optionally also consider in-card `connects_to`, but `connections.json` is the canonical edge list — `graph_status` and `bridge_detect` both treat `connections.json` as authoritative.) Orphan candidate = degree 0 AND age > `orphan_tolerance_days` AND `lifecycle != archived`.
**Warning signs:** A card that is only a connection target is reported as an orphan.

### Pitfall 4: `ValidationReport` is a dataclass, not JSON-serializable as-is
**What goes wrong:** Putting a raw `ValidationReport` into `CurationStepResult.findings` breaks `model_dump(mode="json")` / the MCP serializer.
**Why it happens:** `validate_workspace` returns a `@dataclass ValidationReport` with `ValidationFinding` items, not a pydantic model.
**How to avoid:** In integrity-check, extract plain primitives: `{"errors": len(report.errors), "warnings": len(report.warnings), "ok": report.ok, "error_paths": [f.path for f in report.errors]}`. Pass primitives into `CurationStepResult.findings` (a `dict`).
**Warning signs:** `TypeError: Object of type ValidationReport is not JSON serializable` at the CLI `--json` boundary.

### Pitfall 5: run-level `degraded` vs `completed` semantics (D-09)
**What goes wrong:** Marking the run `degraded` whenever any node is `skipped` — but the three deferred nodes are ALWAYS skipped this phase, which would make every run perpetually `degraded`.
**Why it happens:** D-10 deferred nodes are "optional skips"; D-09 degraded is for **non-optional** step failure/skip.
**How to avoid:** Tag each node as optional or required. `promotion_review`, `process_inbox`, `views_refresh_hook` are **optional** (skip ≠ degraded). The five real steps are **required**: a required step `failed`, or a required step `skipped`, → run `degraded`. All real steps `completed` + only optional nodes skipped → run `completed`. The run is `failed` only if it aborts (exception escapes a node). Encode the optional/required flag on each `CurationStepResult` or in the aggregation logic.
**Warning signs:** A clean run reports `degraded` — the deferred-node skips are being counted as degrading.

### Pitfall 6: nodes must not log to stdout (MCP transport)
**What goes wrong:** A `print()` in a node corrupts the stdio MCP JSON-RPC stream.
**Why it happens:** stdout is the MCP transport channel (WR-04).
**How to avoid:** Use `logging` to stderr only, exactly as research_run.py does (`logger = logging.getLogger(__name__)`).

## Code Examples

### CurationStepResult + CurationRunResult contract (recommended shape — D-07/D-08/D-09)
```python
# Source: pattern mirrors src/construct/llm/research_run.py RunResult (155-175); shapes new
from typing import Literal
from pydantic import BaseModel, Field

class CurationStepResult(BaseModel):
    model_config = {"extra": "forbid"}
    step: str                                   # node name, e.g. "decay_scan"
    status: Literal["completed", "skipped", "failed"]   # D-08
    required: bool = True                       # optional deferred nodes set False (Pitfall 5)
    findings: dict = Field(default_factory=dict)  # machine-readable counts + candidate IDs (D-04/D-07)
    summary: str = ""                           # human-readable one-liner (D-07)
    reason: str | None = None                   # skip/fail rationale, e.g. "deferred to Phase 12"

class CurationRunResult(BaseModel):
    model_config = {"extra": "forbid"}
    status: Literal["completed", "degraded", "failed"]  # D-09 run aggregate
    run_id: str
    steps: list[CurationStepResult] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    message: str = ""
```

### Decay-scan node (new deterministic logic, findings-only — D-04/D-05/D-06)
```python
# Source: composes WorkspaceLoader.load_cards (workspace.py:147) + DecayConfig (config.py:162)
from datetime import date, datetime

def decay_scan(state: CurationRunState) -> dict:
    from construct.storage.workspace import WorkspaceLoader
    loader = WorkspaceLoader(Path(state["workspace_path"]))
    window = state["decay_window_days"]
    auto = state["auto_archive_on_decay"]
    today = date.today()
    candidates = []
    for card in loader.load_cards():                 # list[dict]; has id/created/lifecycle/last_verified
        if card.get("lifecycle") == "archived":
            continue
        anchor = card.get("last_verified") or card.get("created")  # Pitfall 2
        anchor_date = anchor if isinstance(anchor, date) else date.fromisoformat(str(anchor))
        if (today - anchor_date).days > window:
            candidates.append(card["id"])
    summary = f"{len(candidates)} decay candidate(s) older than {window}d"
    if auto:                                          # D-06: report, never act
        summary += "; auto_archive_on_decay=true — archiving deferred to Phase 12 reviewed path"
    result = CurationStepResult(
        step="decay_scan", status="completed",
        findings={"window_days": window, "candidate_count": len(candidates),
                  "candidate_ids": candidates, "auto_archive_on_decay": auto},
        summary=summary,
    )
    return {"steps": [result.model_dump(mode="json")]}   # see reducer note below
```

### Skip-emitting deferred node (D-10 — first-class visible skip)
```python
def promotion_review(state: CurationRunState) -> dict:
    result = CurationStepResult(
        step="promotion_review", status="skipped", required=False,
        summary="skipped — deferred to Phase 12 (card.evaluate L3 gate, CUR-02)",
        reason="deferred to Phase 12",
    )
    return {"steps": [result.model_dump(mode="json")]}
```

### State accumulation note (LangGraph reducer)
`steps` must accumulate across nodes. Two valid approaches: (a) annotate the channel with an
`operator.add` reducer — `steps: Annotated[list[dict], operator.add]` — so each node returns
`{"steps": [one_result]}` and they concatenate; or (b) have each node read `state["steps"]` and
return the full extended list (as `research_run.update_seeds_and_log` does with `events`,
research_run.py:765/825). The reducer approach (a) is cleaner for a linear chain of single-result
nodes. Verify against installed langgraph 1.2.4 — `Annotated[..., operator.add]` reducers are
stable since langgraph 0.2. `[VERIFIED: langgraph 1.2.4 installed; reducer pattern is core API]`

### Run-start runner + status aggregation (mirror research_run.run_research_run:900)
```python
def run_curation_run(inp: CurationRunInput) -> CurationRunResult:
    run_id = inp.run_id or _new_run_id()             # reuse research_run's kebab-safe generator pattern
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_curation_run_graph(saver)
        cfg = {"configurable": {"thread_id": run_id}}
        result = graph.invoke(_initial_state(inp, run_id), cfg)
        steps = [CurationStepResult(**s) for s in result["steps"]]
        # D-09 aggregation (Pitfall 5):
        required_bad = [s for s in steps if s.required and s.status in ("failed", "skipped")]
        status = "degraded" if required_bad else "completed"
        return CurationRunResult(status=status, run_id=run_id, steps=steps,
                                 events=result.get("events", []),
                                 message=f"Curation run {status}.")
    finally:
        conn.close()
```

### Capability registration (catalog.py — mirror research.run, catalog.py:393-422)
```python
registry.register(CapabilityRecord(
    id="curation.run",
    name="Curation Run",
    description="Run deterministic curation checks (integrity, decay, orphan, connection-health, report); no canonical writes",
    input_model=CurationRunInput,
    output_model=OperationResult,
    handler=_curation_run_shim,
    cli_name="curation.run",
    mcp_tool_name="construct_curation_run",
))
registry.register(CapabilityRecord(
    id="curation.inspect",
    name="Curation Inspect",
    description="Report a curation run's persisted state (read-only; never re-runs)",
    input_model=CurationInspectInput,
    output_model=OperationResult,
    handler=_curation_inspect_shim,
    cli_name="curation.inspect",
    mcp_tool_name="construct_curation_inspect",
))
```

## State of the Art

| Old Approach (v0.3) | Current Approach (v0.4 Phase 11) | When Changed | Impact |
|---------------------|----------------------------------|--------------|--------|
| `workflow.run curation-cycle` placeholder lambdas returning `OperationResult(success=True, message="…placeholder")` | `curation.run` LangGraph capability with real per-step findings + status | Phase 11 (this) | Criterion #3 satisfied for `curation.run`; legacy path coexists until Phase 12 (D-11). |
| `WorkflowRunner` + `workflow-state.json` for durability | LangGraph `SqliteSaver` checkpointer under `.construct/workflow/` | Phase 10 (research.run), extended here | One durable orchestration model for research + curation (§11 mitigation). |

**Deprecated/outdated (do not introduce, but do not remove this phase):**
- Legacy `_get_workflow_steps("curation-cycle")` placeholders (catalog.py:658-667) — superseded by `curation.run`; removal is Phase 12 / CUR-05.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Decay age = `today - (last_verified or created)` (no per-card last-modified field exists). | Pitfall 2 / decay-scan example | Wrong candidate set if a different recency source is expected. Low risk — it is the only date data available; confirm in discuss/plan. |
| A2 | Orphan degree counted from `connections.json` (`from_` OR `to`), treating that file as the authoritative edge list. | Pitfall 3 | Could under/over-count if in-card `connects_to` is meant to be authoritative too. Mitigated by matching `graph_status`/`bridge_detect` convention. |
| A3 | Derived-data writes by `bridge_detect` (`log/`, `views/build/data/`) satisfy the "no canonical writes" invariant (D-06). | Pitfall 1 | If reviewer interprets D-06 as "zero filesystem writes," connection-health would need a read-only refactor of `bridge_detect`. Recommend confirming the canonical-vs-derived boundary in the plan. |
| A4 | Phase 11 registers `curation.run` + `curation.inspect` only (no `curation.review`/resume), since the linear graph has no interrupt. | Standard Stack / Alternatives | If reviewer wants full review/resume parity now, add a no-op `curation.review`. Low risk — D-02 explicitly defers the interrupt to Phase 12. |
| A5 | Module placed at `src/construct/llm/curation_run.py` (vs `pipelines/`). | Recommended Project Structure | Pure discretion (CONTEXT D); either compiles. No functional risk. |
| A6 | connection-health passes through `bridge_detect`'s L1/L2 summary; the spec's "untyped edge typing" is Phase 12 scope (the `ConnectionType` enum is closed — there is no "untyped" type in the schema). | connection-health rows | If "untyped edge counts" were expected as a real finding, none exists to count; bridge candidates are the deterministic substitute. Confirm in plan. |

## Open Questions (RESOLVED)

1. **Does the run need a stable `run_id` echoed for a later `curation.inspect`, given there is no pause?** — RESOLVED: register `curation.inspect` anyway for Phase-12 readiness and surface parity (implemented in plan 11-03-T1).
   - What we know: `research.run` exposes inspect for paused runs; curation runs to completion in one call.
   - What's unclear: whether inspect adds value when there is no mid-run pause to observe.
   - Recommendation: Still register `curation.inspect` for surface parity and Phase-12 readiness (it will matter once the interrupt lands). It reads the persisted terminal state — harmless and cheap.

2. **Should `curation_cycle_complete` be the only event, or also per-step `workflow_step_complete`?** — RESOLVED: emit `curation_cycle_complete` with `EventAgent.curator` (required); per-step events optional (implemented in plan 11-02-T3).
   - What we know: spec §6.6 lists both `curation_cycle_complete` and `workflow_step_complete`.
   - What's unclear: whether per-step events are wanted in Phase 11 or deferred with the gate.
   - Recommendation: Emit `curation_cycle_complete` (required by §6.6 for run completion) using `EventAgent.curator`; per-step `workflow_step_complete` is optional and low-cost — include if the planner wants step-level audit granularity for criterion #2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langgraph` | graph build/invoke | ✓ | 1.2.4 | — |
| `langgraph-checkpoint-sqlite` | durable checkpointer | ✓ | 3.1.0 | — |
| `pydantic` | result models | ✓ | 2.13.4 | — |
| `typer` | CLI sub-app | ✓ | 0.26.7 | — |
| `ANTHROPIC_API_KEY` | `bridge_detect` L3 tier (connection-health) | optional | — | L3 auto-skips offline; connection-health stays deterministic on L1+L2 (bridge_detect.py:315-317). |
| `test-ws/my-construct/governance.yaml` | threshold integration fixture | ✓ | decay 28 / orphan 7 / auto_archive false | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** `ANTHROPIC_API_KEY` — connection-health degrades to L1/L2 deterministic detection (desired for this phase; tests should run offline with no key set).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (cpython 3.13) `[VERIFIED: tests/ pyc artifacts]` |
| Config file | `pyproject.toml` (project) + `tests/conftest.py` + `tests/llm/conftest.py` |
| Quick run command | `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -x` |
| Full suite command | `./.venv/bin/python -m pytest -q` |

### What real-vs-placeholder distinctions the validation must SAMPLE
The phase exists to replace fake-success no-ops with real findings. The Nyquist sampling points must each be able to FAIL if a step regresses to placeholder behavior:
1. **Concrete counts/IDs present** — each real step's `CurationStepResult.findings` is non-trivial (has the expected keys: counts and candidate-ID lists), not a bare success message.
2. **degraded ≠ completed discrimination** — injecting a required-step failure flips the run to `degraded`; a clean run is `completed` (NOT `degraded` despite the 3 deferred skips — Pitfall 5).
3. **skipped-deferred nodes visible** — `promotion_review`, `process_inbox`, `views_refresh_hook` appear in `result.steps` with `status="skipped"` and a "deferred to Phase 12" reason — distinct from completed steps and from absent steps.
4. **Thresholds honored** — decay/orphan candidate selection changes when governance thresholds change (proves D-05 wiring, not hardcoding).
5. **No canonical SOT writes** — cards/refs/connections.json/search-seeds.json byte-identical before/after (Pitfall 1: do NOT assert on `log/`/`views/`).
6. **Anti-placeholder guard** — no real step returns a message containing "placeholder"; messages are derived from findings.

### Phase Requirements → Test Map
| Req / SC | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| CUR-01 / SC1 | Full offline `curation.run` produces real integrity+decay+orphan+connection+report results | integration | `pytest tests/llm/test_curation_run.py::test_full_run_offline_real_findings -x` | ❌ Wave 0 |
| SC2 | Clean run = `completed`; injected required-step failure = `degraded` | unit | `pytest tests/llm/test_curation_run.py::test_run_status_degraded_on_step_failure -x` | ❌ Wave 0 |
| SC2 | Deferred nodes appear as `skipped` with deferral reason | unit | `pytest tests/llm/test_curation_run.py::test_deferred_nodes_visible_skipped -x` | ❌ Wave 0 |
| SC3 / CUR-01 | Each real step carries concrete findings, no "placeholder" message | unit | `pytest tests/llm/test_curation_run.py::test_steps_return_concrete_findings -x` | ❌ Wave 0 |
| D-05 | decay-scan honors `decay_window_days`; orphan-scan honors `orphan_tolerance_days` | unit | `pytest tests/llm/test_curation_run.py::test_scans_use_governance_thresholds -x` | ❌ Wave 0 |
| D-06 | No canonical SOT writes (cards/refs/connections/seeds unchanged) | unit | `pytest tests/llm/test_curation_run.py::test_no_canonical_writes -x` | ❌ Wave 0 |
| D-06 | decay step reports auto_archive flag but never archives | unit | `pytest tests/llm/test_curation_run.py::test_auto_archive_reported_not_acted -x` | ❌ Wave 0 |
| API/parity | `curation.run`+`curation.inspect` registered with cli_name+mcp_tool_name; positional args rejected | contract | `pytest tests/contract/test_curation_run_cli_mcp.py::test_registered -x` | ❌ Wave 0 |
| API/parity | MCP auto-discovers tools; `mcp/server.py` has no curation-specific string | contract | `pytest tests/contract/test_curation_run_cli_mcp.py::test_mcp_no_hardcoded_curation -x` | ❌ Wave 0 |
| API/parity | CLI `construct curation run --json` == MCP-serialized `data` keys == `CurationRunResult.model_fields` | contract | `pytest tests/contract/test_curation_run_cli_mcp.py::test_cli_mcp_schema_parity -x` | ❌ Wave 0 |
| RT-03 | `curation.inspect` reads persisted state without re-running | unit | `pytest tests/llm/test_curation_run.py::test_inspect_no_rerun -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -x`
- **Per wave merge:** `./.venv/bin/python -m pytest tests/llm/ tests/contract/test_curation_run_cli_mcp.py -q`
- **Phase gate:** full suite (`pytest -q`) green before `/gsd:verify-work` (API-05 regression: existing v0.3/v0.4 behavior must still pass).

### Wave 0 Gaps
- [ ] `tests/llm/test_curation_run.py` — node-level + graph-level + scan-threshold + status-aggregation + no-write tests (mirror `tests/llm/test_research_run.py` structure: lazy in-body imports, red until built).
- [ ] `tests/contract/test_curation_run_cli_mcp.py` — registry presence, dual-mode shim, MCP auto-discovery, CLI/MCP schema parity, offline smoke (mirror `tests/contract/test_research_run_cli_mcp.py`).
- [ ] Reuse existing fixtures from `tests/llm/conftest.py`: `create_test_workspace`, `write_card` (supports `lifecycle`/`confidence`/`created` via frontmatter — extend with old `created` dates for decay tests), `sqlite_checkpointer`, `test_workspace`. New fixture needed: cards with controllable `created` dates + a `connections.json` with a known orphan, to exercise decay/orphan thresholds deterministically.
- [ ] Framework install: none — pytest already present.

## Security Domain

> `security_enforcement` not set in config (treat as enabled). This is a local, deterministic, read-mostly backend phase — limited attack surface.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local CLI/stdio MCP; no auth surface (out of scope per REQUIREMENTS). |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Single local user; file workspace. |
| V5 Input Validation | yes | `run_id` kebab-validated at the trust boundary via `KEBAB_CASE_PATTERN` (reuse `research_run._validate_run_id`) — it becomes the SQLite `thread_id` and could otherwise be an injection/path vector. Input models use `extra="forbid"`. |
| V6 Cryptography | no | No secrets minted; `ANTHROPIC_API_KEY` only read by the optional L3 tier, never logged (bridge_detect sanitizes errors). |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `run_id` → checkpoint DB path / future filenames | Tampering | Kebab-case validation at input boundary (CR-01), identical to `research_run.py:52-65`. |
| Unbounded card scan (very large workspace) DoS | Denial of Service | Scans are O(cards) read-only; `bridge_detect` already caps L3 at `MAX_L3_CANDIDATES=50` and skips L3 offline. No new unbounded loop introduced. |
| stdout contamination of MCP JSON-RPC | Tampering (transport) | Nodes log to stderr via `logging` only (WR-04 / Pitfall 6). |
| Leaking provider error text (if L3 ever runs) | Information Disclosure | `bridge_detect` already wraps L3 in try/except with class-name logging; do not echo raw provider text. |

## Sources

### Primary (HIGH confidence — direct in-repo read, this session)
- `src/construct/llm/research_run.py` — the LangGraph/SqliteSaver/run-id/shim template (full read).
- `src/construct/capabilities/catalog.py` — capability registration, RT-03 dual-mode shims, legacy curation placeholders (L658-667).
- `src/construct/pipelines/graph_status.py`, `src/construct/pipelines/bridge_detect.py` — compile-report + connection-health step sources.
- `src/construct/services/validation.py` — `validate_workspace` / `ValidationReport` (integrity-check source).
- `src/construct/schemas/config.py` — `GovernanceConfig`/`DecayConfig`/`QualityConfig`, `KEBAB_CASE_PATTERN`.
- `src/construct/schemas/card.py`, `src/construct/schemas/workspace.py` — `KnowledgeCard`, `Lifecycle`, `ConnectionRecord`/`ConnectionsFile`/`ConnectionType` (closed enum, no "untyped").
- `src/construct/storage/workspace.py` — `WorkspaceLoader.load_cards/load_connections/load_governance/iter_cards`.
- `src/construct/cli.py` — `research_app` Typer sub-app pattern (research run/review/inspect).
- `tests/llm/test_research_run.py`, `tests/contract/test_research_run_cli_mcp.py`, `tests/llm/conftest.py` — test harness/fixtures to mirror.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §4.3/§5.1/§6.4/§6.5/§6.6/§12 — curation topology, layer model, WorkflowRunState, events, W4 deliverables.
- `test-ws/my-construct/governance.yaml` — live thresholds (decay 28, orphan 7, auto_archive false).
- `.venv` `importlib.metadata` — installed versions (langgraph 1.2.4, checkpoint-sqlite 3.1.0, pydantic 2.13.4, typer 0.26.7).

### Secondary (MEDIUM)
- `.planning/STATE.md` Phase 09-03 decisions — degraded vs total-outage discrimination precedent (informs D-09 framing).

### Tertiary (LOW)
- None — no unverified web sources used; phase is fully grounded in the existing codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libs installed + verified versions; pattern proven by shipped `research.run`.
- Architecture: HIGH — mirrors a verified, tested, in-repo workflow line-for-line.
- Pitfalls: HIGH — each derived from direct source reading (bridge_detect writes, card date fields, ValidationReport dataclass, closed ConnectionType enum, D-09 deferred-skip trap).
- New logic (decay/orphan selection, status aggregation): MEDIUM — straightforward but the exact age/degree rules are reasoned assumptions (A1/A2) pending plan confirmation.

**Research date:** 2026-06-28
**Valid until:** 2026-07-28 (stable — internal codebase; only risk is upstream langgraph minor changes, already pinned `<4` for the sqlite saver).
