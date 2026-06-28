# Phase 10: Durable Human Review + research.run - Research

**Researched:** 2026-06-28
**Domain:** Durable workflow orchestration (LangGraph `interrupt`/checkpointer), human-in-the-loop gating, idempotent file-based ingest
**Confidence:** HIGH (LangGraph durable APIs empirically verified against installed 1.2.4; in-repo patterns read from source)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `research.run` is orchestrated with **LangGraph `StateGraph`** (not `WorkflowRunner`). Human gate uses native **`interrupt()`**; resume uses **`Command(resume=decisions)`**. Resolves spec open question J1 in favor of LangGraph for this workflow.
- **D-02:** Durable state persisted via LangGraph **`SqliteSaver` checkpointer**. Scope exception accepted: the v0.4 "no SQLite" constraint is carved out for **workflow orchestration/checkpoint state ONLY**. The canonical SOT (`cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`, `digests/`) stays file-based. Checkpoint DB lives under workspace state, not the SOT tree. Action: update `REQUIREMENTS.md` Out-of-Scope "no SQLite" row.
- **D-03:** Review driven through **new registry-backed CLI/MCP capabilities** (full parity), not Streamlit-only. `research.run` pauses and returns a **`gate_id` + pending scored findings**. An **inspect/status** capability lists the pending batch; a **review/resume** capability submits decisions and continues via `Command(resume=...)`. Streamlit `gate_review.py` becomes an optional read view over the same checkpoint.
- **D-04:** Review granularity is **per-finding**. Each finding carries its own approve/reject decision; default suggested decision = the LLM's `ingest_action` from `research.score`. Provide **`approve-all`/`reject-all`**. Only approved findings are ingested; rejected findings recorded to the ledger (D-06). Persisted `gate_queue` holds per-finding decision state.
- **D-05:** `deduplicate` keys on **normalized URL** (lowercase host, strip tracking params + fragment + trailing slash, normalize http/https) matched against existing `refs/*.json` `url` fields AND within the current batch, PLUS a **title fuzzy-match** secondary pass. Deterministic and offline-testable.
- **D-06:** A persistent **rejected-findings ledger** (e.g. `research/rejected.json`) records normalized URL + `gate_id` + timestamp on every reject. `deduplicate` filters incoming results against BOTH `refs/` and this ledger.
- **D-07:** **Partial-batch resume safety:** derive each ref ID **deterministically from the normalized URL** (NOT the suffixing `_deduplicate_ref_id` helper) and **skip-if-exists** on (re)ingest. **Explicitly do NOT use `_deduplicate_ref_id()`** — its `-2`/`-3` suffixing creates duplicates on rerun.
- **D-08:** `compile_digest` is a **deterministic template (PIPE) step — no LLM**. Builds digest from approved findings + run counts + degraded-state notice (carried from score gate) + created ref/card IDs. L2 narrative summary deferred.
- **D-09:** `compile_digest` writes BOTH a markdown digest at **`digests/<id>.md`** AND appends a **`DigestRecord`** (existing schema) to the digests store. Digest path surfaced in run result.
- **D-10:** `build_queries` derives the query list from **active `search-seeds.json` clusters** (respecting `status` + governance caps); `research.run` owns the full search → score composition.
- **D-11:** `update_seeds_and_log` sets **`last_queried`** on queried clusters and emits events: `research_search_complete`, `research_score_gate_complete`, `gate_review_approved`/`gate_review_rejected` (per-finding), and `research_cycle_complete`. Append via existing `append_event()`.
- **D-12:** The **run result** satisfies success criterion 5: status (`completed`/`awaiting_review`/`failed`), gate IDs, approved-ingest counts (refs + cards), digest path, seed-update status, emitted events.

### Claude's Discretion
- LangGraph node/edge topology and state-channel schema (gate must be a real `interrupt()`; per-step writes stay behind it).
- Exact checkpoint DB location/filename under workspace state; checkpointer thread/`gate_id` scheme.
- URL-normalization rule details and title fuzzy threshold/algorithm; ledger file exact path/shape.
- Deterministic ref-ID derivation function from normalized URL.
- Digest markdown template wording/structure and `DigestRecord.id` scheme.
- New review/inspect capability IDs and CLI/MCP names (follow `research.score` registration + shim pattern).
- Concurrency for `ingest_batch` (keep per-finding error isolation).

### Deferred Ideas (OUT OF SCOPE)
- L2 narrative digest (optional prose summary via LLM) — template-only this phase.
- Title-fuzzy dedup tuning / additional dedup signals — basic threshold only.
- Curation workflow, daily-cycle composition — Phases 11–13.
- Additional/academic search providers — deferred (PROV-01).
- Migrating `WorkflowRunner`-based flows onto LangGraph — future work; this phase only establishes the LangGraph path for `research.run`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RSCH-02 | Run `research.run` (CLI/MCP) to execute search → dedup → score → review → approved ingest → digest → seed update → events as one workflow | LangGraph `StateGraph` topology (§Architecture Patterns); reuse `research_search`, `research_score.run_gate`, ingestion writers, `append_event`, seed/digest writers. New capability registered like `_research_score_shim`. |
| RSCH-03 | Review/approve/reject before any refs/cards/seed/digest writes | Native `interrupt()` at `gate_review` node; ALL write nodes are downstream of the interrupt. Empirically confirmed: no state writes occur before resume (§Code Examples, §Pitfall 1). Per-finding `gate_queue` (D-04). |
| RSCH-04 | Resume/inspect a paused run with pending state preserved across process restarts | `SqliteSaver` checkpointer + `thread_id`=run/gate id. Cross-process resume = re-open same DB file in fresh process, recompile graph, `invoke(Command(resume=...), config)`. Inspect = `graph.get_state(config)` (no resume). Both verified. |
| RSCH-05 | Idempotent rerun for duplicate URLs, refs, rejected findings, partial batches | Deterministic ref-ID from normalized URL + skip-if-exists (D-07, avoid `_deduplicate_ref_id`); normalized-URL dedup vs `refs/` + rejected ledger (D-05/06); checkpoint resume makes mid-`ingest_batch` crash re-runnable (§Idempotency Mechanics). |
</phase_requirements>

## Summary

This phase composes already-built pieces (Phase 8 `research.search`, Phase 9 `research.score`, the v0.3 ingestion writers, `append_event`, seed/digest schemas) into a single durable LangGraph workflow with a real human interrupt before any write. The **primary unknown — the LangGraph durable-execution API — is fully resolved and empirically verified** against the version actually installed here: **`langgraph` 1.2.4**, **`langgraph-checkpoint` 4.1.1**, **`langchain-core` 1.4.6**. The durable imports work today (`from langgraph.types import interrupt, Command`; `from langgraph.graph import StateGraph, START, END`). The one missing dependency is **`langgraph-checkpoint-sqlite`** (not installed; 2.0.11 current on PyPI), which provides `SqliteSaver`.

The single most important design constraint, **confirmed by running a real interrupt/resume cycle in this repo's venv**: when a graph resumes from `Command(resume=...)`, **the interrupted node re-executes from the top** — every line before the `interrupt()` call runs a second time. Therefore the `gate_review` node must contain *only* the `interrupt()` call (plus pure, side-effect-free prep), and **all writes (refs, cards, seeds, digest, events) must live in downstream nodes that run only after resume**. This maps cleanly onto the locked topology and is what makes RSCH-03 (no writes before approval) true by construction.

The second cluster of work is idempotency (RSCH-05), which is a pure-Python concern independent of LangGraph: derive ref IDs deterministically from a normalized URL, skip-if-exists on write, dedup incoming results against both `refs/` and a persistent rejected ledger, and add an offline title fuzzy-match pass (stdlib `difflib`). The existing `_deduplicate_ref_id()` suffixer is the anti-pattern to avoid.

**Primary recommendation:** Build a new `research_run` module exposing a `build_research_run_graph()` factory (mirroring `ask_domain.build_ask_domain_graph`) compiled with a persistent `SqliteSaver` under `.construct/`, a single `interrupt()`-only `gate_review` node, deterministic-ID ingest writers, and a `run_gate`-style runner. Register `research.run` + `research.review` + `research.inspect` via the `_research_score_shim` pattern for free CLI/MCP parity.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Query building from seeds | Workflow node (PIPE) | Config/SOT read (`load_search_seeds`) | Pure derivation from active clusters + governance caps; no writes. |
| Web search | Phase 8 `research.search` (read-only) | Provider adapter | Already a capability; `research.run` calls it, owns no provider logic. |
| Deduplication | Workflow node (PIPE) | SOT read (`refs/`) + ledger read | Deterministic, offline; reads existing refs + rejected ledger. |
| Scoring + extraction | Phase 9 `research.score` L3 gate (read-only LLM) | Provider factory | The only LLM call; gate owns no writes (Phase 9 D-10). |
| Human review gate | LangGraph `interrupt()` node | Checkpointer (SQLite) | Pauses graph; persists pending `gate_queue`; the durability boundary. |
| Approved ingest (refs+cards) | Workflow node (PIPE, post-gate) | Ingestion writers (`_write_ref_file`, `create_card`) | Writes happen ONLY after resume; deterministic IDs + skip-if-exists. |
| Digest creation | Workflow node (PIPE, post-gate) | `DigestRecord`/`DigestsFile` schema | Template-only, no LLM; writes `digests/<id>.md` + record store. |
| Seed update + event log | Workflow node (PIPE, post-gate) | `load_search_seeds`/write, `append_event` | Sets `last_queried`; emits D-11 events. |
| Checkpoint persistence | `SqliteSaver` under `.construct/` | sqlite3 connection | Orchestration scratch state ONLY — not SOT. |
| CLI/MCP exposure | Capability registry + shims | `cli.py` `research_app`, MCP auto-discovery | 1:1 parity via `mcp_tool_name`; no separate API. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | 1.2.4 (installed) | `StateGraph`, `interrupt`, `Command`, `compile(checkpointer=...)` | Already the orchestration engine in repo (`ask_domain.py`); D-01 locks it. `[VERIFIED: importlib.metadata]` |
| `langgraph-checkpoint` | 4.1.1 (installed) | Checkpoint base types, `JsonPlusSerializer` | Transitive; base for any saver. `[VERIFIED: importlib.metadata]` |
| `langgraph-checkpoint-sqlite` | 2.0.11 (PyPI; **NOT installed**) | `SqliteSaver` durable checkpointer (D-02) | First-party LangGraph package (langchain-ai monorepo `libs/checkpoint-sqlite`). `[CITED: github.com/langchain-ai/langgraph]` |
| `langchain-core` | 1.4.6 (installed) | `HumanMessage`/`SystemMessage` (reused via score gate) | Already a dep. `[VERIFIED: importlib.metadata]` |

### Supporting (all already in repo — reuse, do not add)
| Module | Purpose | When to Use |
|--------|---------|-------------|
| `construct.pipelines.research_search.research_search` | Provider-agnostic search (read-only) | `execute_search` node |
| `construct.llm.research_score.run_gate` + `ResearchScoreGateOutput` | L3 scoring gate | `score_and_extract` node |
| `construct.pipelines.ingestion._write_ref_file`, `_seed_card_body`, `construct.services.knowledge.create_card` | Ref + seed-card writers | `ingest_batch` node (with deterministic IDs, NOT `_deduplicate_ref_id`) |
| `construct.services.event_log.append_event` | Append `log/events.jsonl` audit | `update_seeds_and_log` + gate decision events |
| `construct.storage.workspace.WorkspaceLoader.load_search_seeds` | Read `SearchSeedsFile` | `build_queries` + seed `last_queried` update |
| `construct.views.models.DigestRecord` / `DigestsFile` | Digest record schema (D-09) | `compile_digest` node |
| `construct.schemas.config` `ReferenceRecord`, `SearchCluster`, `EventAgent`, `EventResult` | SOT contracts | ingest + seed update |
| `construct.capabilities.catalog` `_research_score_shim` | Registration/shim template | new capability handlers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `SqliteSaver` (sync) | `AsyncSqliteSaver` (`langgraph.checkpoint.sqlite.aio`) | Async saver needs an event loop and `async`/`await` nodes; the entire existing runtime (CLI handlers, `run_gate`, `score_all` ThreadPool) is sync. **Use sync `SqliteSaver`.** Async adds complexity with no benefit here. |
| LangGraph orchestration | Existing `WorkflowRunner` | D-01 explicitly chooses LangGraph; `WorkflowRunner` has no real interrupt (only failure-based resume) and no cross-process checkpoint of mid-step pending state. Not retired, not used here. |
| `interrupt()` native | `interrupt_before=[...]` compile flag (static interrupt) | Static interrupts pause but don't carry a payload to the human and don't accept a typed resume value cleanly. D-01 mandates dynamic `interrupt()`/`Command(resume=)`. |

**Installation:**
```bash
uv add langgraph-checkpoint-sqlite   # adds SqliteSaver (2.0.11); pin >=2.0,<3 in pyproject.toml
```
Add to `pyproject.toml` dependencies: `"langgraph-checkpoint-sqlite>=2.0,<3"`.

**Version verification performed this session:**
```
langgraph                 1.2.4   [VERIFIED: importlib.metadata in .venv]
langgraph-checkpoint      4.1.1   [VERIFIED: importlib.metadata in .venv]
langchain-core            1.4.6   [VERIFIED: importlib.metadata in .venv]
langgraph-checkpoint-sqlite  2.0.11 (PyPI latest; NOT installed) [VERIFIED: pip index versions]
```
Import smoke-test (in `.venv`): `from langgraph.types import interrupt, Command` ✅, `from langgraph.graph import StateGraph, START, END` ✅, `from langgraph.checkpoint.sqlite import SqliteSaver` ❌ ModuleNotFoundError (confirms the missing package).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `langgraph-checkpoint-sqlite` | PyPI | mature (1.0.0 → 2.0.11) | high (langchain-ai org) | github.com/langchain-ai/langgraph (`libs/checkpoint-sqlite`) | unavailable | **Approved** (first-party; cited via Context7 from the official monorepo) |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

> slopcheck was **not installable** this session. Per protocol, the single new package is therefore treated conservatively. It is the official first-party LangGraph SQLite saver (same org/monorepo as the already-installed `langgraph`, `langgraph-checkpoint`, `langgraph-sdk`, `langgraph-prebuilt`), cited from Context7's index of `github.com/langchain-ai/langgraph/libs/checkpoint-sqlite/README.md`. **Recommendation for planner:** add a single `checkpoint:human-verify` task confirming `uv add langgraph-checkpoint-sqlite` resolves to a langchain-ai-published artifact before install. Low risk.

## Architecture Patterns

### System Architecture Diagram

```
                         construct CLI / stdio MCP
                                   │
                    ┌──────────────┼───────────────┐
                    ▼              ▼                ▼
            research.run     research.inspect   research.review
            (start/resume)   (get_state only)   (Command(resume))
                    │              │                │
                    └──────────────┼────────────────┘
                                   ▼
                    ┌────────────────────────────────┐
                    │  LangGraph StateGraph (compiled │
                    │  with SqliteSaver checkpointer) │
                    │  thread_id = run_id / gate_id   │
                    └────────────────────────────────┘
                                   │
   START ─► load_config ─► build_queries ─► execute_search ─► deduplicate
              (gov caps)   (active seeds)   (research.search)  (URL norm +
                                                                refs/ + ledger
                                                                + title fuzzy)
                                   │
                                   ▼
                         score_and_extract  ── research.score L3 gate (LLM)
                          (carries degraded flag; ResearchScoreOutageError
                           on total outage ─► run = failed, no gate)
                                   │
                                   ▼
        ┌────────────── gate_review NODE ──────────────┐
        │  interrupt({gate_id, gate_queue=per-finding  │  ◄── PAUSE.
        │  pending w/ default decision=ingest_action}) │      Checkpoint
        │  *** ONLY the interrupt() lives here ***      │      persisted.
        └───────────────────────────────────────────────┘      Returns
                                   │  Command(resume=decisions)  __interrupt__
                                   ▼  (per-finding approve/reject)
   ─────────────────  WRITE BOUNDARY (everything below runs only after resume)  ────────────
                                   │
            ingest_batch ─► compile_digest ─► update_seeds_and_log ─► END
         (approved only;   (template, no    (last_queried on
          deterministic    LLM; digests/    queried clusters;
          ref-id + skip-    <id>.md + Digest append_event ×N;
          if-exists;        Record store;    research_cycle_complete)
          rejects→ledger)   degraded notice)
                                   │
                                   ▼
                          RunResult (D-12): status, gate_ids,
                          ref/card counts, digest_path, seed_update, events[]
```

**Data-flow trace (primary use case):** active seed clusters → query list → normalized search results → deduped candidates → scored findings → **human pause** → approved findings → refs+cards on disk → digest md+record → updated seeds + audit events → structured run result. Rejected findings branch to the ledger (never re-proposed).

### Recommended Project Structure
```
src/construct/
├── llm/
│   └── research_run.py        # NEW: state schema, node fns, build_research_run_graph(),
│   │                          #      run_gate-style runner, RunResult/Review I/O models
│   │                          #      (models defined HERE per the avoid-circular-import rule)
│   └── research_score.py      # reused (run_gate, ResearchScoreGateOutput)
├── pipelines/
│   ├── research_dedup.py      # NEW (or inside research_run): normalize_url, deterministic
│   │                          #      ref-id, title fuzzy match, rejected-ledger I/O
│   └── ingestion.py           # reuse _write_ref_file/_seed_card_body; do NOT call ingest_source
│   │                          #      (it routes through _deduplicate_ref_id — banned by D-07)
├── capabilities/catalog.py    # register research.run / research.review / research.inspect
├── cli.py                     # research_app: add `run`, `review`, `inspect` commands
└── (workspace runtime)
    .construct/                # ALLOWED non-SOT path (workspace.py line 103-104) →
                               # checkpoint DB + rejected ledger live here
```

### Pattern 1: Durable graph with single interrupt node (the core pattern)
**What:** Linear `StateGraph` whose only pause is one `interrupt()`-only node; compiled with a checkpointer bound to a SQLite file under `.construct/`.
**When to use:** the whole `research.run` workflow.
**Example (mirrors `ask_domain.build_ask_domain_graph`, adds checkpointer + interrupt):**
```python
# Source: pattern extends src/construct/llm/ask_domain.py:315-335 (verified in repo)
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

def gate_review(state: ResearchRunState) -> dict:
    # *** ONLY the interrupt lives here. NO writes, NO event emission,
    #     NO non-idempotent prep — this whole node re-runs on resume. ***
    decisions = interrupt({
        "gate_id": state["gate_id"],
        "gate_queue": state["gate_queue"],   # per-finding, default decision = ingest_action
    })
    return {"decisions": decisions}

def build_research_run_graph(checkpointer):
    b = StateGraph(ResearchRunState)
    for name, fn in [
        ("load_config", load_config), ("build_queries", build_queries),
        ("execute_search", execute_search), ("deduplicate", deduplicate),
        ("score_and_extract", score_and_extract), ("gate_review", gate_review),
        ("ingest_batch", ingest_batch), ("compile_digest", compile_digest),
        ("update_seeds_and_log", update_seeds_and_log),
    ]:
        b.add_node(name, fn)
    b.add_edge(START, "load_config")
    b.add_edge("load_config", "build_queries")
    b.add_edge("build_queries", "execute_search")
    b.add_edge("execute_search", "deduplicate")
    b.add_edge("deduplicate", "score_and_extract")
    b.add_edge("score_and_extract", "gate_review")
    b.add_edge("gate_review", "ingest_batch")      # WRITE BOUNDARY
    b.add_edge("ingest_batch", "compile_digest")
    b.add_edge("compile_digest", "update_seeds_and_log")
    b.add_edge("update_seeds_and_log", END)
    return b.compile(checkpointer=checkpointer)
```

### Pattern 2: Persistent SqliteSaver for cross-process resume (the `from_conn_string` footgun)
**What:** Open the SQLite checkpointer so its connection survives the handler call; do NOT wrap the graph lifetime in a transient `with SqliteSaver.from_conn_string(...)` that closes the connection on block exit.
**When to use:** every `research.run` / `research.review` / `research.inspect` invocation.
**Example:**
```python
# Source: langgraph checkpoint-sqlite README (Context7) + footgun verified
import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver

def _open_checkpointer(workspace: Path) -> tuple[SqliteSaver, sqlite3.Connection]:
    db = workspace / ".construct" / "workflow" / "research-run.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: score_all uses a ThreadPool; the checkpointer may be
    # touched from worker threads. Keep ONE connection alive for the whole handler.
    conn = sqlite3.connect(str(db), check_same_thread=False)
    return SqliteSaver(conn), conn

# Per capability call:
saver, conn = _open_checkpointer(workspace)
try:
    graph = build_research_run_graph(saver)
    config = {"configurable": {"thread_id": run_id}}   # run_id = gate handle
    result = graph.invoke(initial_state, config)        # or Command(resume=...) to continue
finally:
    conn.close()
```
> `SqliteSaver.from_conn_string(path)` is a **context manager** whose underlying connection closes when the `with` block exits. Using it as `with SqliteSaver.from_conn_string(db) as cp: graph = compile(cp); return graph` leaves a graph holding a **closed** connection — the classic footgun. For a CLI/MCP request lifecycle, construct `SqliteSaver(sqlite3.connect(...))` explicitly and close in `finally`. Each fresh process re-opens the same DB file and continues the same `thread_id`.

### Pattern 3: Inspect without resuming (D-03 `research.inspect`)
```python
# Source: graph.get_state — verified live this session
snap = graph.get_state({"configurable": {"thread_id": run_id}})
status = "awaiting_review" if snap.next == ("gate_review",) else (
         "completed" if not snap.next else "running")
pending = snap.values.get("gate_queue", [])                 # the per-finding batch
interrupts = [t.interrupts for t in snap.tasks]             # Interrupt(value=..., id=...)
```

### Pattern 4: Registration/shim parity (mirror `_research_score_shim`)
```python
# Source: src/construct/capabilities/catalog.py:371-436 (verified)
registry.register(CapabilityRecord(
    id="research.run", name="Research Run",
    description="Durable, human-gated research workflow: search→score→review→ingest→digest",
    input_model=ResearchRunInput, output_model=OperationResult,
    handler=_research_run_shim,            # builds input model, runs graph, returns OperationResult
    cli_name="research.run", mcp_tool_name="construct_research_run",
))
# research.review (Command(resume)) and research.inspect (get_state) registered the same way.
```
MCP parity is automatic: `mcp/server.py` auto-discovers any record with `mcp_tool_name` and serializes the result via `model_dump`. The run/review/inspect handlers must return an `OperationResult` (or a pydantic model) so `_serialize_result` works.

### Anti-Patterns to Avoid
- **Writes before the interrupt, or in the gate node.** The gate node re-executes on resume (empirically confirmed) — any write there double-fires and also leaks a write before approval (breaks RSCH-03). Keep all writes in post-gate nodes.
- **`with SqliteSaver.from_conn_string(...)` around the graph lifetime.** Closes the connection; breaks cross-process resume (RSCH-04).
- **Calling `ingest_source()` / `_deduplicate_ref_id()` for ingest.** The suffixer creates `-2`/`-3` duplicates on rerun — the exact opposite of RSCH-05. Use deterministic IDs + skip-if-exists.
- **Putting non-serializable objects in graph state.** LLM clients, `WorkspaceLoader`, file handles, sqlite connections must be rebuilt inside nodes, never stored in the state channel (checkpoint serializes via msgpack/JsonPlus).
- **Checkpoint DB or rejected ledger inside the SOT tree** (`cards/`, `refs/`, `digests/`, `log/`, etc.). Violates D-02's "no DB owns facts" boundary. Use `.construct/`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pause/resume + persistence | Custom JSON state machine | LangGraph `interrupt()` + `SqliteSaver` | D-01/D-02; handles checkpoint, pending-write replay, cross-process resume. |
| Cross-process resume | Re-implement `WorkflowRunner` reload | `thread_id` + re-open same checkpoint DB | Pending interrupt + channel state persist automatically. |
| Search / scoring | New provider/LLM code | `research_search`, `research_score.run_gate` | Already capabilities (Phases 8–9); composition only. |
| Ref + seed-card writes | New writer | `_write_ref_file` + `create_card` + `_seed_card_body` | Validated, event-logged primitives; wrap with deterministic ID. |
| Event audit | New log format | `append_event()` | Append-only `log/events.jsonl`; non-blocking. |
| Title near-dup match | New fuzzy algorithm/ML | stdlib `difflib.SequenceMatcher` (or token-set ratio) | Deterministic, offline, zero new deps; D-05 says "basic threshold this phase". |
| URL normalization | ad-hoc string ops only | stdlib `urllib.parse` (urlsplit/urlunsplit, parse_qsl) + explicit tracking-param denylist | Deterministic and testable; no new dep. |

**Key insight:** Almost everything here already exists. The genuinely new code is small: the LangGraph wiring, the interrupt node, URL normalization + deterministic ref-ID + ledger, the digest template/record writer, and three thin capability shims. Resist re-implementing search, scoring, ingest, or state persistence.

## Idempotency Mechanics (RSCH-05) — concrete recommendation

### URL normalization (D-05)
```python
# stdlib only; deterministic
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
_TRACKING = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content",
             "gclid","fbclid","mc_cid","mc_eid","ref","ref_src","spm"}
def normalize_url(url: str) -> str:
    s = urlsplit(url.strip())
    scheme = "https"                                   # normalize http/https (D-05)
    host = s.hostname.lower() if s.hostname else ""
    if s.port and not ((scheme=="https" and s.port==443) or s.port==80):
        host = f"{host}:{s.port}"
    path = s.path.rstrip("/") or "/"                   # strip trailing slash
    q = urlencode(sorted((k,v) for k,v in parse_qsl(s.query) if k.lower() not in _TRACKING))
    return urlunsplit((scheme, host, path, q, ""))     # fragment dropped
```

### Deterministic ref-ID from normalized URL (D-07)
`ReferenceRecord.id` must satisfy `KEBAB_CASE_PATTERN` (lowercase, hyphen-separated). Recommend a human-readable slug + a stable short hash of the normalized URL so distinct pages never collide and the ID is reproducible:
```python
import hashlib, re
def ref_id_for(normalized_url: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+","-", title.lower()).strip("-")[:40].strip("-") or "ref"
    h = hashlib.sha1(normalized_url.encode()).hexdigest()[:8]
    return f"{slug}-{h}"                                # kebab-valid, deterministic, collision-resistant
```
**Skip-if-exists:** before `_write_ref_file`, if `refs/{ref_id}.json` exists → skip (count as "already ingested"). Same for the seed card. Combined with checkpoint resume, a crash mid-`ingest_batch` re-runs every approved finding safely — existing ones skip, the unfinished one completes.

### Dedup pass (D-05/D-06)
1. Build the existing-URL set: `{normalize_url(ref.url) for ref in refs/*.json}` ∪ `{rejected ledger normalized URLs}`.
2. Drop any incoming result whose normalized URL is in that set, or duplicated earlier within the same batch.
3. **Title fuzzy secondary pass:** normalize title (lowercase, strip punctuation, sort tokens); drop a candidate if `difflib.SequenceMatcher(None, cand, existing).ratio() >= 0.90` against any existing ref title. Threshold is a tunable constant (D-05: basic this phase).

### Rejected ledger shape (D-06)
Recommend `.construct/research/rejected.json` (NOT `research/` at SOT root — see Runtime State Inventory):
```json
{ "version": 1, "rejected": [
  {"normalized_url": "https://example.com/x", "gate_id": "run-2026...", "title": "…", "rejected_at": "2026-06-28T..Z"} ] }
```
On every per-finding reject in `ingest_batch`, append an entry. The `deduplicate` node reads this file each run.

## Reused Outputs Behind the Gate

- **`score_and_extract`:** call `research_score.run_gate("research.score", ResearchScoreInput(...))`. It raises `ResearchScoreOutageError` on total provider outage — the run must catch this **before the gate**, set status `failed`/degraded, and not pause. The partial-degraded signal lives in `output.retrieval["degraded"]` (+ `retried`/`errors`) and must be carried into the digest (D-08/09, Phase 9 D-08/09).
- **`gate_queue` defaults (D-04):** each entry = `{finding, decision: <ingest_action>}`. `approve-all` reproduces the LLM's recommended ingest set; `reject-all` sets all to skip.
- **`ingest_batch`:** for each approved finding, write `ReferenceRecord` (deterministic ID, skip-if-exists) via `_write_ref_file`, then a seed card via `create_card` + `_seed_card_body`; rejects → ledger. Keep per-finding error isolation (Phase 9 D-08 style) so one bad finding doesn't abort the batch.
- **`compile_digest` (D-08/09):** template string from approved findings + counts (considered/approved/rejected/ingested) + degraded notice + created ref/card IDs. Write markdown to `digests/<id>.md`; append a `DigestRecord` (`id`, `domain_id`, `title`, `generated_at`, `card_ids`, `summary`) to the digest record store (`construct.views.models.DigestRecord`/`DigestsFile`). Surface the markdown path in the run result.
- **`update_seeds_and_log` (D-11):** load `SearchSeedsFile`, set `last_queried = now` on each queried cluster, write back `search-seeds.json`. Emit via `append_event` (agent `EventAgent.researcher` or `human` for gate decisions): `research_search_complete`, `research_score_gate_complete`, per-finding `gate_review_approved`/`gate_review_rejected` (reuse `gate_review._log_gate_event` protocol), and `research_cycle_complete` on full completion.

> **Two `EventRecord` / `DigestRecord` definitions exist.** Audit events use `construct.schemas.config.EventRecord` via `append_event` (the `log/events.jsonl` SOT). The `construct.views.models.{EventRecord,DigestRecord,DigestsFile}` are the *views build-data* payloads. **D-09 means the views-models `DigestRecord` schema.** Do not confuse the two.

## Runtime State Inventory

> This phase is greenfield composition (new module + new capabilities) — not a rename/refactor. Inventory included because it introduces persistent runtime state outside the SOT.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (new) | SQLite checkpoint DB (D-02) + rejected ledger (D-06) | Create under `.construct/` (allowed non-SOT path). Code writes; no migration of existing data. |
| Live service config | None — no external services registered. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | Reuses existing provider keys (Tavily `*_API_KEY`, LLM provider keys) via existing config; no new secret names. | None. |
| Build artifacts / installed packages | `langgraph-checkpoint-sqlite` must be added to `pyproject.toml` + `uv.lock` and installed. | `uv add langgraph-checkpoint-sqlite`; reinstall. |

**Verified non-SOT home:** `schemas/workspace.py` lists `.construct` and `.construct/**` among allowed workspace paths (lines 103-104), and `REQUIRED_PATHS` does not include the checkpoint DB or ledger — so placing them under `.construct/` will NOT trip `validate_workspace`. (`research/` at SOT root is NOT a known path and risks validation noise — prefer `.construct/research/rejected.json`.) **Planner:** confirm `.construct/` (or at least the new sub-paths) is git-ignored so the SQLite DB isn't committed.

## Common Pitfalls

### Pitfall 1: Interrupted node re-executes from the top on resume (EMPIRICALLY CONFIRMED)
**What goes wrong:** Code placed before `interrupt()` in the gate node (or any write in that node) runs a second time when `Command(resume=...)` continues the graph.
**Why it happens:** LangGraph replays the interrupted task; `interrupt()` returns the resume value on the second pass, but everything above it re-runs.
**Evidence (this session):** a node logging `"gate-before-interrupt"` then calling `interrupt()` produced side-effect order `['search', 'gate-before-interrupt', 'gate-before-interrupt', 'gate-after-interrupt']` — the pre-interrupt line fired twice.
**How to avoid:** gate node contains ONLY `interrupt()` + the returned-value mapping. All writes downstream. (This is also why RSCH-03 holds by construction.)
**Warning signs:** duplicate events, writes appearing before approval, side effects firing twice.

### Pitfall 2: `from_conn_string` context manager closes the DB (breaks RSCH-04)
**What goes wrong:** Graph compiled inside `with SqliteSaver.from_conn_string(db) as cp:` holds a closed connection after the block; resume in a new process fails or silently can't find state.
**How to avoid:** construct `SqliteSaver(sqlite3.connect(db, check_same_thread=False))`, keep alive for the handler, close in `finally`. Each process re-opens the same file.
**Warning signs:** "Cannot operate on a closed database", empty `get_state`, resume starting from scratch.

### Pitfall 3: Non-serializable state channels
**What goes wrong:** Storing an LLM client / `WorkspaceLoader` / connection in state raises a serialization error at checkpoint time (or silently fails to persist).
**How to avoid:** state holds only plain data (dicts, lists, pydantic models, primitives). Rebuild clients inside nodes from `workspace_path` + provider config.

### Pitfall 4: `_deduplicate_ref_id` suffixing defeats idempotency
**What goes wrong:** Rerun produces `foo`, then `foo-2`, then `foo-3` for the same URL.
**How to avoid:** deterministic ID from normalized URL + skip-if-exists (D-07). Never call `ingest_source()` (it routes through the suffixer) for `research.run`.

### Pitfall 5: `check_same_thread` + ThreadPool scoring
**What goes wrong:** `score_all` fans out across worker threads (Phase 9 D-04). A default sqlite connection (`check_same_thread=True`) used by the checkpointer can raise if touched cross-thread.
**How to avoid:** `sqlite3.connect(..., check_same_thread=False)` for the checkpointer connection; do not share the connection for unrelated writes.

### Pitfall 6: MCP stdout contamination
**What goes wrong:** Any `print()` to stdout inside a node corrupts the MCP JSON-RPC stream (documented in `ask_domain.py:298-303`, WR-04).
**How to avoid:** log to stderr via `logging`; never print in node code.

## Code Examples

### Cross-process resume (the RSCH-04 shape — mirrors `test_workflow_runner` r1/r2 two-instance pattern)
```python
# Process 1: start, pause at gate
saver1, conn1 = _open_checkpointer(ws); 
g1 = build_research_run_graph(saver1)
cfg = {"configurable": {"thread_id": run_id}}
r1 = g1.invoke(initial_state, cfg)
assert "__interrupt__" in r1                      # paused; pending payload present
conn1.close()                                     # simulate process exit

# Process 2 (fresh): re-open SAME db file, recompile, resume
saver2, conn2 = _open_checkpointer(ws)            # same .construct/.../research-run.sqlite
g2 = build_research_run_graph(saver2)
assert g2.get_state(cfg).next == ("gate_review",) # state survived
r2 = g2.invoke(Command(resume=decisions), cfg)    # completes: ingest→digest→seeds
conn2.close()
```

### Capability handler skeleton (shim — mirrors `_research_score_shim`)
```python
def _research_run_shim(*args, **kwargs):
    if args:
        raise TypeError("research.run handler requires keyword arguments")
    inp = ResearchRunInput(**kwargs)
    saver, conn = _open_checkpointer(Path(inp.workspace_path))
    try:
        graph = build_research_run_graph(saver)
        cfg = {"configurable": {"thread_id": inp.run_id or _new_run_id()}}
        out = graph.invoke(_initial_state(inp), cfg)
        return _to_operation_result(out, cfg)      # status awaiting_review/completed/failed + D-12 fields
    except ResearchScoreOutageError as exc:
        return OperationResult(success=False, message=exc.safe_message,
                               data={"degraded": True, "total_outage": True})
    finally:
        conn.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `interrupt_before=[node]` static interrupt + `update_state` | Dynamic `interrupt(value)` + `Command(resume=value)` | LangGraph 0.2+ (stable in 1.x) | Payload-carrying pause + typed resume; D-01 relies on this. |
| `langgraph.checkpoint.sqlite.SqliteSaver` bundled in `langgraph` | Split into `langgraph-checkpoint-sqlite` package | checkpoint refactor (≤1.0) | Must add the dependency explicitly (currently missing). |
| `WorkflowRunner` JSON state + failure-only resume | LangGraph checkpointer + mid-step interrupt resume | This phase (D-01) | Real pending-review persistence across restarts. |

**Deprecated/outdated:** `langchain` monolith imports — this repo correctly uses `langchain-core` + `langgraph` + provider packages. Do not import from a top-level `langchain` package.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Digest record store path = `digests/digests.json` (inside the derived `digests/` dir). The only existing `digests.json` is the *views build-data* file (`cli.py:643`); no SOT digest store exists yet. | Reused Outputs / D-09 | Low — schema is fixed (`DigestsFile`); only the path needs a planner decision. Could instead be a flat `digests.json` at root. |
| A2 | `.construct/research/rejected.json` is the right ledger home (vs CONTEXT's example `research/rejected.json`). | Idempotency / Runtime State | Low — `.construct/` is verified non-validated; `research/` at root would need a workspace-schema allowance. |
| A3 | Sync `SqliteSaver` (not async) suits the all-sync runtime. | Standard Stack | Low — async would force `await` through CLI/MCP handlers; sync matches every existing handler. |
| A4 | Default title-fuzzy threshold 0.90 via `difflib.SequenceMatcher`. | Idempotency D-05 | Low/tunable — CONTEXT marks tuning as deferred; any reasonable threshold satisfies the phase. |
| A5 | `langgraph-checkpoint-sqlite` 2.x is API-compatible with `langgraph` 1.2.4 / `langgraph-checkpoint` 4.1.1. | Standard Stack | Medium — verify at install (slopcheck was unavailable). Same monorepo release line; expected compatible. Gate with the install checkpoint. |
| A6 | Gate-decision events should use `EventAgent.human` (or `researcher`); existing `gate_review._log_gate_event` uses `EventAgent.construct`. | Reused Outputs D-11 | Low — cosmetic; reuse existing protocol's agent for consistency unless planner prefers `human`. |

## Open Questions (RESOLVED)

1. **Exact digest record store path (A1).** RESOLVED: `digests/digests.json` (Plan 04 Task 2 specifies it; verifier asserts the path).
   - Known: markdown → `digests/<id>.md`; schema → `views.models.DigestRecord`/`DigestsFile`; `digests/` is an allowed derived dir.
   - Unclear: filename/location of the JSON record store (no SOT precedent).
   - Recommendation: `digests/digests.json`; planner confirms and the verifier asserts the path.

2. **`run_id` / `gate_id` scheme and how `research.review`/`research.inspect` receive it.** RESOLVED: `run_id` = timestamp + short random, generated on `research.run`, surfaced in the result and used as the `thread_id`; `review`/`inspect` take `--run-id` (Plan 03 Task 2).
   - Recommendation: generate a `run_id` (timestamp + short random) on `research.run`; surface it in the result; `review`/`inspect` take `--run-id`/`run_id` as the `thread_id`. One `gate_id` per run (single gate this phase).

3. **`.construct/` gitignore status.** RESOLVED: `.construct/` git-ignored via the `.gitignore` rule added in Plan 01 Task 2 (verified by grep).
   - Recommendation: planner verifies `.construct/workflow/*.sqlite` and `.construct/research/rejected.json` are git-ignored (the SQLite DB must not be committed).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langgraph` | orchestration | ✓ | 1.2.4 | — |
| `langgraph-checkpoint` | checkpoint base | ✓ | 4.1.1 | — |
| `langchain-core` | messages (via score gate) | ✓ | 1.4.6 | — |
| `langgraph-checkpoint-sqlite` (`SqliteSaver`) | D-02 durable state | ✗ | — (2.0.11 on PyPI) | none — must install; no viable fallback for cross-process resume |
| `sqlite3` (stdlib) | checkpoint connection | ✓ | stdlib | — |
| `difflib` / `urllib.parse` / `hashlib` (stdlib) | dedup, ref-id | ✓ | stdlib | — |
| Mock search provider + mock LLM seam | offline tests | ✓ | Phase 8/9 | — |

**Missing dependencies with no fallback:** `langgraph-checkpoint-sqlite` — blocking; install via `uv add` (Plan Wave 0 / first task).
**Missing dependencies with fallback:** none.

## Validation Architecture

> `workflow.nyquist_validation: true` in config — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (repo standard; `tests/llm`, `tests/unit`, `tests/contract`, `tests/integration`) |
| Config file | `pyproject.toml` (pytest config) / existing `tests/` layout |
| Quick run command | `uv run pytest tests/llm/test_research_run.py -x -q` (new file) |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RSCH-02 | Full run composes search→dedup→score→review→ingest→digest→seeds→events; result carries D-12 fields | integration (offline) | `uv run pytest tests/llm/test_research_run.py::test_full_run_offline -x` | ❌ Wave 0 |
| RSCH-03 | At `awaiting_review` NO refs/cards/digest/seed writes exist; writes appear only after `Command(resume=approve)` | integration | `...::test_no_writes_before_approval -x` | ❌ Wave 0 |
| RSCH-03 | Per-finding reject → finding not ingested, appended to ledger; `approve-all`/`reject-all` | unit | `...::test_per_finding_decisions -x` | ❌ Wave 0 |
| RSCH-04 | Pause in one checkpointer/connection, close, re-open NEW SqliteSaver on same DB file, `get_state` shows pending, resume completes (mirror `test_workflow_runner` r1/r2) | integration | `...::test_cross_process_resume -x` | ❌ Wave 0 |
| RSCH-04 | `research.inspect` returns pending batch via `get_state` without resuming | unit | `...::test_inspect_no_resume -x` | ❌ Wave 0 |
| RSCH-05 | Rerun same inputs → no duplicate refs (deterministic ID skip); rejected findings not re-proposed (ledger); normalized-URL + title-fuzzy dedup | integration | `...::test_idempotent_rerun -x` | ❌ Wave 0 |
| RSCH-05 | Crash mid-`ingest_batch` (interrupt after first write) → resume completes without double-writing | integration | `...::test_partial_batch_resume_safe -x` | ❌ Wave 0 |
| RSCH-05 (unit) | `normalize_url`, `ref_id_for`, title-fuzzy threshold are deterministic | unit | `...::test_url_normalization`, `...::test_ref_id_deterministic` | ❌ Wave 0 |
| API parity | `research.run`/`research.review`/`research.inspect` registered; CLI present; MCP tool listed; schemas/result parity | contract | `uv run pytest tests/contract/ -k research_run -x` | ❌ Wave 0 |
| API-05 | v0.3 + Phase 8/9 suites still pass | regression | `uv run pytest -q` | ✓ existing |

**Success-criteria → test mapping (all 5):** SC1≡RSCH-02 full run; SC2≡RSCH-03 no-writes-before-approval; SC3≡RSCH-04 cross-process resume + inspect; SC4≡RSCH-05 idempotent rerun + partial-batch; SC5≡assert run result contains status, gate_ids, ref/card counts, digest_path, seed_update status, events list.

### Offline test construction
- **Mock LLM:** monkeypatch `construct.llm.factory.build_chat_model` with `ConfigurableStructuredMock(ScoredFinding(...))` (existing `tests/llm/conftest.py`). The score gate then runs deterministically.
- **Mock search:** Phase 8 mock provider (fixture_dir) — drive `research_search` offline; or inject a search result list fixture (`sample_search_results`) at the `execute_search` seam.
- **Checkpointer fixture:** `tmp_path` SQLite file; for cross-process simulation, build TWO `SqliteSaver` instances on the same path (the `test_workflow_runner.py` r1/r2 two-instance pattern is the exact template).
- **Resume injection:** `graph.invoke(Command(resume=[{"url":..,"decision":"approve"}...]), cfg)`.
- **No-writes assertion:** after the paused `invoke`, assert `refs/`, `cards/`, `digests/` unchanged and `search-seeds.json.last_queried` untouched.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/llm/test_research_run.py -x -q`
- **Per wave merge:** `uv run pytest tests/llm tests/contract -q`
- **Phase gate:** `uv run pytest -q` green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/llm/test_research_run.py` — RSCH-02..05 + SC5 (new)
- [ ] `tests/contract/` additions — research.run/review/inspect registry + CLI/MCP parity
- [ ] conftest extension: checkpointer/tmp-sqlite fixture; helper to build a `ResearchScoreGateOutput`/findings batch; mock-search seam
- [ ] Dependency install: `uv add langgraph-checkpoint-sqlite` (blocking, do first)

## Security Domain

> `security_enforcement` not present in config — treat as enabled; section included (scoped to what this phase touches).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local-first; no auth surface (v0.4 Out-of-Scope: no multi-user/HTTP). |
| V3 Session Management | no | No sessions; `thread_id` is a local run handle, not a credential. |
| V4 Access Control | no | Single local user. |
| V5 Input Validation | yes | All I/O via Pydantic models (`extra="forbid"`); SearchResult/ScoredFinding/ReferenceRecord validated before write; URL normalization sanitizes inputs. |
| V6 Cryptography | n/a (no secrets created) | Reuses existing provider-key handling; never hand-roll. Ref-ID hash is `sha1` for *identity only* (not security) — acceptable. |
| V7 Error Handling / Logging | yes | Reuse Phase 9 key-safe sanitization (`_safe_scoring_cause`); never echo raw provider text; `append_event` non-blocking. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted search snippet/title/URL escalates ingest action | Tampering/Elevation | Scoring output constrained to `ScoredFinding` + deterministic clamp (Phase 9 T-09-02); content is data, never instruction. Human gate is the final control (RSCH-03). |
| Provider error text leaks API key into events/CLI | Info Disclosure | Reuse `_safe_scoring_cause`/`safe_message`; map total outage to `OperationResult(success=False)` without raw text (Phase 9 T-09-03/06). |
| `print()` to stdout corrupts MCP stream | Tampering (protocol) | Log to stderr only (WR-04). |
| Checkpoint DB committed to git / leaks workspace data | Info Disclosure | `.construct/` git-ignored; checkpoint holds orchestration state only, not secrets. |
| Malicious URL with path traversal in ref-ID | Tampering | Ref-ID is derived via kebab-slug + hash (regex-stripped), never raw URL path → no traversal; `_write_ref_file` writes within `refs/`. |
| Rerun double-writes / replay | Tampering (integrity) | Deterministic IDs + skip-if-exists + ledger (RSCH-05). |

## Project Constraints (from CLAUDE.md)

No root `./CLAUDE.md` exists (the `CLAUDE.md` files found are in `CONSTRUCT-CLAUDE-impl/` and `test-ws/` workspaces, not project-level instructions). Binding constraints therefore come from STATE.md / CONTEXT.md / spec:
- Human review mandatory before research ingest, lifecycle, or connection writes (v0.4 Roadmap decision) — satisfied by the interrupt gate.
- Gate I/O models defined in the gate module, not `catalog.py`, to avoid circular imports (Phase 05-02 decision) — apply to new `ResearchRunInput`/`RunResult`/review models.
- RT-03 dual-mode shim convention (positional CLI / keyword MCP) for one registry handler serving both surfaces (Phase 07-01) — follow for the three new handlers.
- Fail-loud, no silent fallback; per-item error isolation (Phase 09 D-08).
- Append-only `log/events.jsonl`; never truncate.
- "No database owns any facts" — the SQLite carve-out (D-02) is orchestration state ONLY.

## Sources

### Primary (HIGH confidence)
- Context7 `/langchain-ai/langgraph` — `interrupt`/`Command(resume)`, `SqliteSaver.from_conn_string`, `thread_id` config, `get_state`, `langgraph-checkpoint-sqlite` install (`libs/checkpoint-sqlite/README.md`).
- Live verification in repo `.venv` (this session): import smoke-test of `langgraph.types`/`langgraph.graph`/`langgraph.checkpoint.sqlite`; full interrupt→`get_state`→`Command(resume)` cycle confirming `__interrupt__` payload, `snap.next`/`snap.tasks[].interrupts`, resume return value, and the **pre-interrupt re-execution footgun**.
- `importlib.metadata` / `pip index versions` — installed and PyPI versions.
- Repo source (read this session): `ask_domain.py` (StateGraph pattern), `research_score.py` (gate runner, outage error, degraded flag), `ingestion.py` (`_write_ref_file`/`_deduplicate_ref_id`/`_seed_card_body`), `workflow_runner.py` (resume conventions, r1/r2 test idiom), `catalog.py`/`registry.py` (`_research_score_shim`), `mcp/server.py` (auto-discovery/serialization), `event_log.py`, `views/models.py` (`DigestRecord`/`DigestsFile`), `schemas/config.py` (`SearchCluster.last_queried`, `ReferenceRecord`, `EventAgent`), `schemas/workspace.py` (`.construct` allowed paths), `cli.py` (`research_app`), `ui/gate_review.py` (`_log_gate_event`), `tests/llm/conftest.py`, `tests/unit/test_workflow_runner.py`.

### Secondary (MEDIUM confidence)
- PyPI version listing for `langgraph-checkpoint-sqlite` (2.0.11) — registry existence; compatibility with 1.2.4 to be confirmed at install (A5).

### Tertiary (LOW confidence)
- None — all load-bearing claims verified against installed code or live execution.

## Metadata

**Confidence breakdown:**
- LangGraph durable API (interrupt/resume/checkpointer/get_state): **HIGH** — empirically executed against installed 1.2.4.
- Standard stack / versions: **HIGH** — `importlib.metadata` + `pip index versions`.
- In-repo reuse seams (ingest, score, events, schemas, registry): **HIGH** — read from source.
- Idempotency scheme (normalize/ref-id/ledger/fuzzy): **MEDIUM-HIGH** — design is deterministic and grounded in repo constraints (kebab IDs, allowed paths); thresholds/paths are planner-confirmable (A1/A2/A4).
- `langgraph-checkpoint-sqlite` 2.x ⇄ langgraph 1.2.4 compatibility: **MEDIUM** — same release line; gate at install.

**Research date:** 2026-06-28
**Valid until:** ~2026-07-28 (LangGraph 1.x is fast-moving; re-verify checkpoint-sqlite at install).
