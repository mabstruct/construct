# Phase 10: Durable Human Review + research.run - Pattern Map

**Mapped:** 2026-06-28
**Files analyzed:** 8 (3 new code, 2 new test, 3 modified code/docs)
**Analogs found:** 8 / 8 (every new file has a strong in-repo analog; only the LangGraph durable wiring — interrupt + SqliteSaver — is genuinely new API)

> All file-creation excerpts below are copy-from sources, not specifications.
> The planner should reference the analog path + line range in each plan's action
> section. Concrete reuse seams (`run_gate`, `build_*_graph`, `_write_ref_file`,
> `create_card`, `append_event`, `_research_score_shim`) already exist — Phase 10
> composes them; it does not re-implement them.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/llm/research_run.py` (NEW) | service / workflow-orchestrator (LangGraph graph + node handlers + run/review/inspect runners + I/O models) | event-driven (durable interrupt/resume) + request-response | `src/construct/llm/ask_domain.py` | role-match (same StateGraph build idiom; new interrupt+checkpointer) |
| `src/construct/pipelines/research_dedup.py` (NEW) | utility (URL normalize, deterministic ref-ID, title-fuzzy, rejected-ledger JSON I/O) | transform + file-I/O | `src/construct/pipelines/ingestion.py` (`_deduplicate_ref_id`, `_write_ref_file`) | role-match — **explicitly diverges** from `_deduplicate_ref_id` (D-07 anti-pattern) |
| `src/construct/capabilities/catalog.py` (MODIFY) | config / registry | request-response | `_research_score_shim` + `research.score` registration (same file, lines 371-436) | exact (same file, same pattern) |
| `src/construct/cli.py` (MODIFY) | controller (Typer command group) | request-response | `research_app` `score` command (same file, lines 513-559) | exact (same file, same group) |
| `src/construct/mcp/server.py` (NO EDIT — parity for free) | controller (auto-discovery) | request-response | existing `create_server()` loop (lines 23-46) | exact (auto-discovers any `mcp_tool_name`; no change needed) |
| `.planning/REQUIREMENTS.md` (MODIFY) | docs | n/a | Out-of-Scope "no SQLite" row | doc edit (D-02 carve-out) |
| `pyproject.toml` (MODIFY) | config | n/a | existing `langgraph` dep entries | add `langgraph-checkpoint-sqlite>=2.0,<3` |
| `tests/llm/test_research_run.py` (NEW) | test | event-driven + transform | `tests/unit/test_workflow_runner.py` (r1/r2 resume) + `tests/llm/conftest.py` (mocks) | role-match (file-state resume → checkpoint resume) |

## Pattern Assignments

### `src/construct/llm/research_run.py` (service / workflow-orchestrator)

**Analog:** `src/construct/llm/ask_domain.py` (StateGraph build + `run_gate` runner + I/O models defined in-module) and `src/construct/llm/research_score.py` (`run_gate`, outage handling, degraded flag).

**Imports / module-header pattern** (`ask_domain.py:1-16`, `research_score.py:23-36`) — TypedDict state, `langgraph.graph` imports, models defined here to avoid circular import with `catalog.py`:
```python
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from construct.llm import factory
logger = logging.getLogger(__name__)
# Phase 10 ADD: from langgraph.types import interrupt, Command
#               from langgraph.checkpoint.sqlite import SqliteSaver  (new dep)
```
> **In-module models (critical):** `ask_domain.py:69` and `research_score.py:15-16,64`
> both define gate I/O models IN the gate module "to avoid the circular-import
> hazard between the capability catalog and the gate runner." Phase 10's
> `ResearchRunInput`, `ReviewInput`, `InspectInput`, `RunResult`, and the
> per-finding `gate_queue` entry model MUST live here, not in `catalog.py`
> (CONTEXT established-pattern; RESEARCH §Project Constraints).

**State schema pattern** (`ask_domain.py:22-49`) — TypedDict, NOT BaseModel ("LangGraph prefers this"). Phase 10 state holds ONLY plain serializable data (RESEARCH Pitfall 3 — no LLM clients / `WorkspaceLoader` / sqlite conn in channels):
```python
class AskDomainState(TypedDict):
    # Input (set before graph starts)
    question: str
    workspace_path: str
    # Processing (populated by nodes)
    cards: list[dict]
    provider_cfg: ProviderConfig   # NOTE: Phase 10 must NOT store non-serializable
    # Output (final)
    citations: list[dict]
    review_required: bool
    review_status: str
```

**Graph builder factory pattern** (`ask_domain.py:315-335`) — the exact idiom to extend with `add_node` per node, linear `add_edge` topology, and `.compile()`. Phase 10 adds `interrupt()` in the `gate_review` node and passes a `checkpointer=` to `.compile()`:
```python
def build_ask_domain_graph() -> StateGraph:
    builder = StateGraph(AskDomainState)
    builder.add_node("load_domain_cards", load_domain_cards)
    builder.add_node("filter_by_domain", filter_by_domain)
    # ...
    builder.add_edge(START, "load_domain_cards")
    builder.add_edge("load_domain_cards", "filter_by_domain")
    # ...
    builder.add_edge("extract_citations", END)
    return builder.compile()
# Phase 10: build_research_run_graph(checkpointer) → ... return builder.compile(checkpointer=checkpointer)
# Topology (RESEARCH §Pattern 1): load_config→build_queries→execute_search→deduplicate
#   →score_and_extract→gate_review[interrupt-ONLY]→ingest_batch→compile_digest→update_seeds_and_log→END
```

**Per-node return-dict + MCP-safe logging pattern** (`ask_domain.py:119-140, 298-309`) — each node returns a partial-state dict; NEVER `print()` (WR-04 / RESEARCH Pitfall 6 — stdout is the MCP JSON-RPC transport); log to stderr via `logging`:
```python
def load_domain_cards(state: AskDomainState) -> dict:
    loader = WorkspaceLoader(Path(state["workspace_path"]))  # rebuild client INSIDE node
    # ...
    return {"cards": active, "retrieval_cards_considered": len(active)}
# WR-04:
if missing:
    logger.warning("cited card IDs not in retrieved set: %s", missing)  # stderr, never print()
```

**Gate-node (interrupt-ONLY) pattern** — NO direct analog in repo (first interrupt here); RESEARCH §Pattern 1 is the canonical source. The gate node re-executes top-to-bottom on resume (RESEARCH Pitfall 1, empirically confirmed), so it contains ONLY `interrupt()` + return-value mapping; all writes live downstream:
```python
# Source: RESEARCH §Pattern 1 (verified against langgraph 1.2.4 in repo .venv)
def gate_review(state: ResearchRunState) -> dict:
    decisions = interrupt({
        "gate_id": state["gate_id"],
        "gate_queue": state["gate_queue"],   # per-finding; default decision = ingest_action (D-04)
    })
    return {"decisions": decisions}
```

**Runner pattern** (`research_score.py:535-583` `run_gate`, and `ask_domain.py:365-449`) — resolve config, build graph, invoke, assemble typed output. Phase 10's `research.run` runner additionally opens the checkpointer and catches the outage error BEFORE the gate (RESEARCH §Reused Outputs Behind the Gate):
```python
def run_gate(gate_id, input_data, *, config_path=None) -> ResearchScoreGateOutput:
    config = load_llm_config(config_path)
    gate_cfg = config.gates.get(gate_id, config.gates.get("research.score"))
    # ...
    batch = score_all(input_data.results, llm=llm, thresholds=thresholds, ...)
    if batch.total_outage:
        raise ResearchScoreOutageError(batch.outage_message or "...")
    # Phase 10 score_and_extract node: call research_score.run_gate("research.score", ResearchScoreInput(...))
    #   catch ResearchScoreOutageError BEFORE the interrupt → status="failed", do NOT pause.
    #   carry output.retrieval["degraded"]/["retried"]/["errors"] into state for the digest (D-08/09).
```

**Checkpointer wiring** — NEW (no repo analog); copy verbatim from RESEARCH §Pattern 2 (the `from_conn_string` footgun is the key hazard). Open `SqliteSaver(sqlite3.connect(..., check_same_thread=False))` under `.construct/`, keep alive for the handler, `conn.close()` in `finally`:
```python
# Source: RESEARCH §Pattern 2 + Pitfall 2/5 (DO NOT use `with SqliteSaver.from_conn_string(...)`)
def _open_checkpointer(workspace: Path) -> tuple[SqliteSaver, sqlite3.Connection]:
    db = workspace / ".construct" / "workflow" / "research-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), check_same_thread=False)  # ThreadPool scoring (Pitfall 5)
    return SqliteSaver(conn), conn
```

**Inspect-without-resume** (RESEARCH §Pattern 3) — `graph.get_state(config)`; status from `snap.next`:
```python
snap = graph.get_state({"configurable": {"thread_id": run_id}})
status = "awaiting_review" if snap.next == ("gate_review",) else ("completed" if not snap.next else "running")
pending = snap.values.get("gate_queue", [])
```

---

### `src/construct/pipelines/research_dedup.py` (utility — normalize / ref-ID / fuzzy / ledger)

**Analog:** `src/construct/pipelines/ingestion.py` — reuse `_write_ref_file` and `_seed_card_body`, **but explicitly REPLACE `_deduplicate_ref_id` with a deterministic-from-URL ID + skip-if-exists** (D-07).

**Ref-file writer to REUSE as-is** (`ingestion.py:336-343`):
```python
def _write_ref_file(root: Path, ref_id: str, ref: ReferenceRecord) -> None:
    ref_path = root / "refs" / f"{ref_id}.json"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(json.dumps(ref.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
```

**ANTI-PATTERN to AVOID** (`ingestion.py:315-322`) — the `-2`/`-3` suffixer that breaks idempotency (D-07, RESEARCH Pitfall 4). `research.run` must NOT call this, and must NOT call `ingest_source()` (lines 132-135, 184-187 route through it):
```python
def _deduplicate_ref_id(root: Path, desired_id: str) -> tuple[str, None] | ...:
    resolved = desired_id
    counter = 1
    while (root / "refs" / f"{resolved}.json").exists():
        counter += 1
        resolved = f"{desired_id}-{counter}"   # ← DUPLICATES ON RERUN. DO NOT USE.
    return (resolved, None)
```

**Deterministic-ID + skip-if-exists REPLACEMENT** (RESEARCH §Idempotency Mechanics) — stdlib only; `ReferenceRecord.id` must satisfy `KEBAB_CASE_PATTERN` (`schemas/config.py:328-338`):
```python
# Source: RESEARCH §Idempotency Mechanics (D-05/D-07)
import hashlib, re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
def normalize_url(url: str) -> str: ...   # lowercase host, strip tracking params/fragment/trailing slash
def ref_id_for(normalized_url: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "ref"
    h = hashlib.sha1(normalized_url.encode()).hexdigest()[:8]
    return f"{slug}-{h}"   # kebab-valid, deterministic; skip-if-exists before _write_ref_file
```

**Ref + seed-card builders to REUSE** — `ReferenceRecord` (`schemas/config.py:308-326`) is the validated write contract; `_seed_card_body` (`ingestion.py:296-312`) and `create_card` (`services/knowledge.py:153-158`) build the seed card. Pattern from `ingestion.py:148-165, 235-246`:
```python
ref = ReferenceRecord(id=ref_id, title=source_title, url=source, relevance_score=...,
                      source_tier=..., key_findings=..., content_categories=..., extraction_status=...,
                      ingested_date=today, domain=domain_id, search_cluster=...)
validate_ref_write(ref.model_dump(), relative_path=f"refs/{ref_id}.json")
_write_ref_file(root, ref_id, ref)
card_body = _seed_card_body(source_title, source_type, key_findings)
card_result = create_card(str(root), card_data, author=CardAuthor(author), body=card_body)
```

**Rejected-ledger I/O** — NEW (no repo analog); shape per RESEARCH §Rejected ledger; home `.construct/research/rejected.json` (NOT SOT root). `deduplicate` reads it each run; `ingest_batch` appends on each per-finding reject.

---

### `src/construct/capabilities/catalog.py` (MODIFY — register run/review/inspect)

**Analog:** the `research.score` registration + `_research_score_shim` in the SAME file.

**Registration pattern** (`catalog.py:371-380`):
```python
registry.register(CapabilityRecord(
    id="research.score",
    name="Research Score",
    description="Score normalized search results into governance-aware finding proposals (read-only, no writes)",
    input_model=ResearchScoreInput, output_model=OperationResult,
    handler=_research_score_shim,
    cli_name="research.score", mcp_tool_name="construct_research_score",
))
# Phase 10: three records — research.run / research.review / research.inspect,
#   mcp_tool_name=construct_research_run / _review / _inspect.
```

**RT-03 dual-mode shim pattern** (`catalog.py:401-436`) — keyword-only MCP form + outage/error sanitization returning `OperationResult` (so `mcp/server.py:_serialize_result` works). This is the exact template for `_research_run_shim` / `_research_review_shim` / `_research_inspect_shim` (RESEARCH §Code Examples shim skeleton):
```python
def _research_score_shim(*args, **kwargs):
    if args:
        raise TypeError("research.score handler requires keyword arguments")
    input_data = ResearchScoreInput(**kwargs)
    try:
        output = research_score_gate("research.score", input_data)
    except ResearchScoreOutageError as exc:
        return OperationResult(success=False, message=exc.safe_message,
                               data={"degraded": True, "total_outage": True})
    except Exception as exc:
        from construct.llm.research_score import _safe_scoring_cause
        return OperationResult(success=False, message=f"research.score failed: {_safe_scoring_cause(exc)}",
                               data={"degraded": True, "total_outage": False})
    return OperationResult(success=True, message=..., data=output.model_dump(mode="json"))
```

**Import-block pattern** (`catalog.py:39-47`) — add a `# ── Research Run imports (Phase 10) ──` block importing `ResearchRunInput`, the runner, and `ResearchScoreOutageError` re-use from `research_run`.

---

### `src/construct/cli.py` (MODIFY — add `research run` / `review` / `inspect` commands)

**Analog:** the `research score` command in the same `research_app` group.

**Command + registry-dispatch pattern** (`cli.py:513-559`) — resolve cap from registry, build `handler_kwargs`, call `cap.handler(**kwargs)`, render + `_display_result`. The `KeyError` guard message ("Ensure Phase N is complete") is the established idiom:
```python
@research_app.command(name="score")
def research_score_cmd(workspace: Path = typer.Option(..., "--workspace", "-w"), ..., json_output=...):
    handler_kwargs = {"workspace_path": str(workspace), "results": flattened}
    try:
        cap = get_registry().get("research.score")
    except KeyError:
        typer.echo("ERROR: Capability 'research.score' not found. Ensure Phase 9 is complete.")
        raise typer.Exit(code=1)
    result = cap.handler(**handler_kwargs)
    if json_output:
        _display_result(result, json_output=True); return
    if result.data:
        _render_research_score_table(result.data)
    typer.echo(f"✓ {result.message}")
# Phase 10: research run (start; surfaces run_id+gate_id), research review --run-id (Command(resume)),
#   research inspect --run-id (get_state, no resume). Add a _render_run_result(...) like _render_research_score_table.
```

---

### `src/construct/mcp/server.py` (NO EDIT — parity is automatic)

**Analog / mechanism** (`server.py:23-46`) — `create_server()` iterates `registry.list_mcp_tools()` and auto-registers any record with an `mcp_tool_name`; `_serialize_result` (lines 13-20) handles pydantic `model_dump` and dataclasses. As long as the three new shims return `OperationResult` (or a pydantic model), MCP parity is free — confirm via a contract test, do NOT edit this file (RESEARCH §Pattern 4).

---

### `tests/llm/test_research_run.py` (NEW)

**Analogs:** `tests/unit/test_workflow_runner.py` (r1/r2 resume idiom) + `tests/llm/conftest.py` (mock LLM + workspace + search fixtures).

**Cross-process resume idiom to mirror** (`test_workflow_runner.py:164-215`) — two runner instances over the same persisted state; Phase 10 builds TWO `SqliteSaver` instances on the same DB file (RESEARCH §Code Examples cross-process resume):
```python
# First run: pause/fail
r1 = WorkflowRunner(tmp_path); r1.run(steps)
assert r1.state.status == WorkflowStatus.failed
# Second (fresh) instance: resume from persisted state
r2 = WorkflowRunner(tmp_path); result = r2.resume(resume_steps)
assert r2.state.status == WorkflowStatus.completed
assert call_log2 == ["step3"]   # only the unfinished step re-ran
# Phase 10: g1.invoke(initial, cfg) → assert "__interrupt__" in r1; conn1.close()
#           g2 (new SqliteSaver, same .sqlite) → g2.get_state(cfg).next == ("gate_review",)
#           g2.invoke(Command(resume=decisions), cfg) → completes (ingest→digest→seeds)
```

**Mock-LLM seam + fixtures to reuse** (`conftest.py:55-80, 142-157, 159-170, 226-260`) — `ConfigurableStructuredMock`, `make_build_chat_model` (monkeypatch `construct.llm.factory.build_chat_model`), `create_test_workspace`, `sample_search_results`. These drive the full offline run; the score gate runs deterministically:
```python
# conftest.py:142 — monkeypatch seam shared with the score gate
def make_build_chat_model(mock): ...   # returns _build(cfg, *, temperature=0.2) -> mock
# conftest.py:227 — sample_search_results() → list[SearchResult] (arxiv/blog/shop fixtures)
# Phase 10 conftest extension (Wave 0): tmp-sqlite checkpointer fixture + ScoredFinding batch helper.
```

**No-writes-before-approval assertion** (RESEARCH §Offline test construction) — after the paused `invoke`, assert `refs/`, `cards/`, `digests/` unchanged and `search-seeds.json.last_queried` untouched (proves RSCH-03).

---

## Shared Patterns

### Event audit (D-11)
**Source:** `src/construct/services/event_log.py:13-41` (`append_event`) + `src/construct/ui/gate_review.py:26-49` (`_log_gate_event` → `gate_review_approved`/`gate_review_rejected`).
**Apply to:** `update_seeds_and_log` and the per-finding gate-decision events (POST-gate nodes only).
```python
append_event(workspace_root, EventAgent.researcher, action,           # event_log.py:13
             target=..., detail=..., result=EventResult.success)
# gate_review.py:42 reuse protocol — agent EventAgent.construct today (A6: researcher/human acceptable):
append_event(workspace, EventAgent.construct, "gate_review_approved", target=gate_id, detail=...)
```
> Append-only `log/events.jsonl`; `append_event` is non-blocking (warns to stderr on OSError, never raises). Events to emit: `research_search_complete`, `research_score_gate_complete`, per-finding `gate_review_approved`/`gate_review_rejected`, `research_cycle_complete` (D-11).
> **EventAgent/EventResult enums:** `schemas/config.py:341-351` (`construct|curator|researcher|human`; `success|failure|escalated`).

### Digest write (D-09)
**Source:** `src/construct/views/models.py:219-237` (`DigestRecord` / `DigestsFile`).
**Apply to:** `compile_digest` (POST-gate, template-only, no LLM — D-08). Write markdown to `digests/<id>.md` AND append a `DigestRecord` to the digest store. Surface the markdown path in `RunResult` (success criterion 5).
```python
class DigestRecord(BaseModel):                 # views/models.py:219 — D-09 means THIS schema
    model_config = ConfigDict(extra="forbid")
    id: str; domain_id: str; title: str; generated_at: str
    card_ids: list[str] = Field(default_factory=list); summary: str
```
> **Two `DigestRecord`/`EventRecord` definitions exist** (RESEARCH §Reused Outputs warning). Audit events use `schemas/config.EventRecord` via `append_event`. D-09's digest uses `views/models.DigestRecord`/`DigestsFile`. Do not confuse them. Record-store path is an open question (A1; recommend `digests/digests.json`).

### Seed `last_queried` update (D-10/D-11)
**Source:** `src/construct/storage/workspace.py:113-117` (`load_search_seeds → SearchSeedsFile`) + `schemas/config.py:210-233` (`SearchCluster.last_queried: datetime | None`, `SearchSeedsFile`).
**Apply to:** `build_queries` (read active clusters respecting `status` + governance caps) and `update_seeds_and_log` (set `last_queried = now` on queried clusters, write back `search-seeds.json`).

### Governance caps (D-10)
**Source:** `src/construct/llm/research_score.py:114-130` (`load_governance_thresholds` / `retrieval_echo`).
**Apply to:** `load_config` / `build_queries` (`relevance_threshold`, `card_creation_threshold`, `max_papers_per_cycle`).

### Error sanitization (no raw provider text leaks)
**Source:** `src/construct/llm/research_score.py:326-389` (`ResearchScoreOutageError`, `_safe_scoring_cause`) + the shim's dual catch (`catalog.py:406-427`).
**Apply to:** the `research.run` runner/shim — catch `ResearchScoreOutageError` BEFORE the gate → `RunResult(status="failed")`, never pause; never echo `str(exc)` (WR-03/T-09-06).

### In-module I/O models (avoid circular import)
**Source:** `research_score.py:64` / `ask_domain.py:69` comments.
**Apply to:** all Phase-10 I/O models (`ResearchRunInput`, `ReviewInput`, `InspectInput`, `RunResult`, gate-queue entry) — define in `research_run.py`, not `catalog.py`.

## No Analog Found

Genuinely new code with no in-repo precedent (planner uses RESEARCH §Patterns 1-3 + §Idempotency Mechanics instead):

| Concern | Role | Data Flow | Reason / Source |
|---------|------|-----------|-----------------|
| `interrupt()` gate node + `Command(resume=...)` | workflow gate | event-driven | First durable interrupt in repo; `ask_domain` graph has no interrupt. Source: RESEARCH §Pattern 1 (verified vs langgraph 1.2.4). |
| `SqliteSaver` checkpointer wiring (`_open_checkpointer`, cross-process resume) | persistence | event-driven | New dep `langgraph-checkpoint-sqlite` (not installed); no checkpointer used today. Source: RESEARCH §Pattern 2 + Pitfalls 2/5. |
| URL normalization + deterministic ref-ID + title-fuzzy + rejected-ledger | utility | transform + file-I/O | No idempotent dedup exists; `_deduplicate_ref_id` is the anti-pattern. Source: RESEARCH §Idempotency Mechanics (stdlib `urllib.parse`/`hashlib`/`difflib`). |
| Template digest markdown writer | utility | file-I/O | `DigestRecord` schema exists but no writer; template-only (D-08). |
| `research.inspect` `get_state` capability | controller | request-response | No read-only graph-state capability exists. Source: RESEARCH §Pattern 3. |

## Metadata

**Analog search scope:** `src/construct/{llm,pipelines,capabilities,cli,mcp,services,views,schemas,storage,ui}`, `tests/{llm,unit}`.
**Files scanned (read in full or targeted):** `ask_domain.py`, `research_score.py`, `ingestion.py`, `workflow_runner.py`, `catalog.py`, `registry.py`, `cli.py`, `mcp/server.py`, `event_log.py`, `views/models.py`, `schemas/config.py`, `ui/gate_review.py`, `storage/workspace.py`, `services/knowledge.py`, `tests/llm/conftest.py`, `tests/unit/test_workflow_runner.py`.
**Project instructions:** no root `CLAUDE.md`; no `.claude/skills` or `.agents/skills` (binding constraints come from CONTEXT/RESEARCH/spec).
**Pattern extraction date:** 2026-06-28
