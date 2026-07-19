# Phase 12: Curation L3 Gates + Review Application - Pattern Map

**Mapped:** 2026-06-30
**Files analyzed:** 12 (4 new, 8 modified)
**Analogs found:** 12 / 12 (every file has an in-repo analog — this is a grafting phase)

> This phase is **structural copying**, not greenfield. Every mechanism already
> ships and is test-covered. The planner's job is to faithfully preserve the
> invariants the analog modules encode. Treat every `# Pitfall N` / `# WR-NN` /
> `# T-NN` / `# D-NN` comment in the analog as a contract to carry over.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/llm/curation_promote.py` (NEW) | service (L3 gate runner) | transform / batch (LLM fan-out) | `src/construct/llm/research_score.py` | exact |
| `src/construct/llm/curation_connect.py` (NEW, optional — may inline) | service (L3 gate runner) | transform / batch (LLM fan-out) | `src/construct/llm/research_score.py` | exact |
| `src/construct/llm/curation_run.py` (MOD) | service (LangGraph workflow) | event-driven / HITL interrupt-resume | `src/construct/llm/research_run.py` | exact |
| `src/construct/capabilities/catalog.py` (MOD) | config (capability registry) | request-response (registration + shims) | `catalog.py` research.review/inspect block (411-430, 554-611) | exact (same file) |
| `src/construct/cli.py` (MOD) | route (Typer commands) | request-response | `cli.py` workflow sub-app (200-266) + curation sub-app | role-match |
| `src/construct/llm/config.yaml` (MOD) | config | n/a (static config) | `config.yaml` `gates.research.score` block | exact |
| `tests/llm/test_curation_promote.py` (NEW) | test (unit) | transform | `tests/llm/test_research_score.py` | exact |
| `tests/llm/test_curation_run.py` (MOD/extend) | test (integration) | event-driven / HITL | `tests/llm/test_research_run.py` | exact |
| `tests/llm/conftest.py` (MOD/extend) | test (fixtures/mocks) | n/a | `conftest.py` `ConfigurableStructuredMock` (65-101) | exact (same file) |
| `tests/contract/test_curation_run_cli_mcp.py` (MOD/extend) | test (contract) | request-response | self (mirror research.run contract) | exact (same file) |
| `tests/contract/test_skill_migration.py` (NEW) | test (static/lint guard) | n/a | `tests/contract/test_curation_run_cli_mcp.py` structure | role-match |
| `CONSTRUCT-CLAUDE-impl/claude/skills/construct-{research-cycle,curation-cycle,card-evaluate}/SKILL.md` (MOD) | provider (Claude skill) | orchestration (delegation) | `construct-card-create/SKILL.md` (thin `Bash(construct …)` delegator) | role-match |

---

## Pattern Assignments

### `src/construct/llm/curation_promote.py` — `card.evaluate` L3 gate (NEW)

**Role:** service (L3 LLM gate runner) · **Data flow:** transform + bounded batch fan-out
**Analog:** `src/construct/llm/research_score.py` (full module — copy its structure end-to-end)

This is the closest 1:1 mapping in the phase. Mirror `research_score.py` symbol-for-symbol:
`score_one` → `evaluate_one`, `_score_one_with_retry` → `_evaluate_one_with_retry`,
`score_all` → `evaluate_all`, `run_gate`, plus the outage error class and sanitization.

**Module-docstring + in-module-models rule** (research_score.py:14-16) — models live HERE, never in catalog.py:
```python
# Models are defined IN this module (not ``catalog.py``) to avoid the
# circular-import hazard between the capability catalog and the gate runner.
```

**Structured-output target + the gate-output contract** (mirror research_score.py:44-99). The promotion target is `PromotionDecision` per spec §6.4 — `extra="forbid"`, with `target_lifecycle: Literal["growing","mature"] | None` (see Discrepancy 1):
```python
# Mirror ScoredFinding (research_score.py:44-61)
class PromotionDecision(BaseModel):
    model_config = {"extra": "forbid"}
    card_id: str
    decision: Literal["promote", "hold", "escalate"]
    target_lifecycle: Literal["growing", "mature"] | None = None
    reasoning: str
    method: Literal["rule-based", "llm-judgment"] = "llm-judgment"
```

**Provider seam — route through the factory monkeypatch seam** (research_score.py:190-197):
```python
def build_scoring_llm(provider_cfg: ProviderConfig, gate_cfg: GateConfig) -> Any:
    # Routed via ``factory.build_chat_model`` so the shared test monkeypatch on
    # ``construct.llm.factory.build_chat_model`` covers this gate too.
    return factory.build_chat_model(provider_cfg, temperature=gate_cfg.temperature)
```

**Single-item call** (mirror `score_one`, research_score.py:250-297) — `with_structured_output(PromotionDecision, method="json_schema")`, `.invoke(messages)`. Drop the governance ceiling-clamp (`clamp_action`) — promotion has no relevance-band clamp; the human gate is the constraint instead.

**Per-item retry → escalate** (mirror `_score_one_with_retry`, research_score.py:406-434). D-03 mapping: a still-failing card after one retry becomes `PromotionDecision(decision="escalate", method="rule-based", reasoning="<safe_cause>")` (genuine borderline escalations keep `method="llm-judgment"`):
```python
# research_score.py:406-434 — copy the two-attempt loop verbatim; swap the
# _skip_finding_for_failure(...) builder for a _escalate_decision_for_failure(...)
# that sets decision="escalate", method="rule-based".
for attempt in range(2):
    try:
        return evaluate_one(...), retried, None
    except Exception as exc:
        last_exc = exc
        if attempt == 0:
            retried = 1
```

**Bounded fan-out + total-outage discrimination** (mirror `score_all`, research_score.py:458-532) — `ThreadPoolExecutor(max_workers=max(1, min(cap, len(items))))`, `as_completed`, ordered results, `scored_ok == 0 and provider_failures == len(items)` → `total_outage=True`. **Sync executor, never async gather** (the cap is not honored by `gather`).

**Outage error class + sanitization** (copy verbatim, research_score.py:326-389) — `_is_provider_outage_cause`, `_safe_scoring_cause`, the `_PROVIDER_OUTAGE_*` tables, and the word-boundary `_CODE_BOUNDARY_PATTERN`. These are security-load-bearing (T-09-03 / WR-06 — never echo raw provider text). Rename `ResearchScoreOutageError` → `CardEvaluateOutageError`.

**Candidate pre-filter (D-02):** `lifecycle != mature` AND not `archived` — applied deterministically *before* the LLM fan-out (mirror the archived-exclusion guard at `curation_run.py:317`):
```python
if getattr(lifecycle, "value", lifecycle) == Lifecycle.archived.value:
    continue
```

---

### `src/construct/llm/curation_connect.py` — connection-typing L3 gate (NEW, optional / may inline)

**Role:** service (L3 LLM gate runner) · **Data flow:** transform + batch
**Analog:** `src/construct/llm/research_score.py` (same fan-out/retry/outage skeleton as `curation_promote.py`)

Per RESEARCH A1 + CONTEXT discretion: **recommend an inline gate function called from `connection_maintenance`**, not a separately registered capability (no requirement names `connection.evaluate`; Phase 13 owns the parity sweep). Structurally identical to `curation_promote.py`.

**Input is `bridge_detect` candidate pairs, NOT existing ConnectionRecords** (see Discrepancy 2). Candidate shape (bridge_detect.py:233-244):
```python
{
  "pair_id": key, "from_card_id": from_id, "to_card_id": to_id,
  "from_domain": ..., "to_domain": ..., "from_title": ..., "to_title": ...,
  "l1_structural": True, "l2_shared_categories": [...], "pre_score": ...,
}
```

**Structured output target** — assign a `ConnectionType` enum value (from `schemas/workspace.py`: `supports | contradicts | extends | parallels | requires | enables | challenges | inspires | gap-for`) with reasoning:
```python
class ConnectionTypeDecision(BaseModel):
    model_config = {"extra": "forbid"}
    from_card_id: str
    to_card_id: str
    connection_type: ConnectionType   # required enum — no None (Discrepancy 2)
    reasoning: str
```

The gate *proposes*; the actual write happens post-gate via `add_connection` (already idempotent — knowledge.py:416-423).

---

### `src/construct/llm/curation_run.py` — graft interrupt + write nodes + review/inspect (MOD)

**Role:** service (LangGraph workflow) · **Data flow:** event-driven HITL interrupt-resume
**Analog:** `src/construct/llm/research_run.py` (the whole interrupt/resume/review/inspect machine)

The Phase-11 graph is already compiled, durable, and topology-complete (`build_curation_run_graph`, curation_run.py:466-497). Phase 12 grafts the `research_run.py` HITL pattern onto it. **No graph restructuring of the deterministic prefix** — only the three `_deferred_step` skip-nodes (curation_run.py:451-460) and the linear edges around `process_inbox` change.

**Extend the state channels** (mirror research_run.py:71-102) — add a heterogeneous `gate_queue` + `decisions` + per-write output channels, and **add `awaiting_review` to the status set**:
```python
# research_run.py:90-94
gate_queue: list[dict]   # GateQueueEntry dumps (per-finding, default = ingest_action)
decisions: Any           # resume payload from the human gate
status: str              # running | awaiting_review | completed | failed
```
For curation, `gate_queue` holds the tagged-union `CurationProposal` envelope (`kind: promotion | connection | archive | escalate`, see Code Examples in RESEARCH). Add `awaiting_review` to `CurationRunResult.status` Literal (currently `completed|degraded|failed`, curation_run.py:137).

**Interrupt-ONLY gate node** (copy research_run.py:437-452 — the spine of CUR-03). `process_inbox` becomes this; it must contain NOTHING but `interrupt()`:
```python
def gate_review(state):
    # *** ONLY the interrupt primitive. NO writes, NO event emission. ***
    # The interrupted node re-executes top-to-bottom on resume, so any side
    # effect here would double-fire AND leak a write before approval.
    decisions = interrupt({"gate_id": state["gate_id"], "gate_queue": state["gate_queue"]})
    return {"decisions": decisions}
```

**Producer nodes (no pause, no write):** `promotion_review` calls `curation_promote.evaluate_all` and enqueues promote/escalate items; `connection_maintenance` (already calls `bridge_detect`, curation_run.py:395-422) additionally runs the connection-typing gate and enqueues typed-connection proposals; decay archive proposals come from `decay_scan` candidates when `auto_archive_on_decay`. All three write ONLY into `gate_queue`.

**Conditional short-circuit on empty queue** (mirror research_run.py:831-867 `_route_after_score` + `add_conditional_edges`) — an empty `gate_queue` routes straight to `compile_report`, never pausing (Pitfall 2):
```python
def _route_before_inbox(state):
    return "process_inbox" if state.get("gate_queue") else "compile_report"
builder.add_conditional_edges("<last_producer>", _route_before_inbox,
    {"process_inbox": "process_inbox", "compile_report": "compile_report"})
```

**Post-gate write nodes (WRITE BOUNDARY — run only after `Command(resume=...)`):** mirror research_run.py:868 (`add_edge("gate_review", "ingest_batch")  # WRITE BOUNDARY`). Three apply-nodes downstream of the interrupt:
- `apply_promotions` → `edit_card(workspace, card_id, {"lifecycle": target_lifecycle}, author=CardAuthor.curator)` (knowledge.py:241). Skip if already at `target_lifecycle`.
- `apply_connections` → `add_connection(workspace, from_id, to_id, ConnectionType(...), created_by=ConnectionAuthor.construct)` (knowledge.py:372; already returns `success=True, "Connection already exists"` on dup — knowledge.py:416-423).
- `apply_archives` → `archive_card(workspace, card_id, author=CardAuthor.curator)` (knowledge.py:314). Skip if already `archived`.

**Per-item write isolation** (mirror research_run.py:611) — wrap each apply in `try/except` so one failing write never aborts the batch:
```python
except Exception as exc:  # noqa: BLE001 — per-finding isolation (D-08)
    logger.warning("ingest_batch finding %r failed: %s", title, exc)
```

**Decision resolution + approve-all/reject-all** (copy research_run.py:461-498 `_normalize_decision` / `_resolve_decisions` and 979-993 `_build_resume_decisions`). D-07: default per-item decision = the gate's recommendation; `escalate` carries no default write (treat escalate as review-only this phase per RESEARCH Open-Q 3).

**Review runner** `review_curation_run` (copy research_run.py:996-1035) — the paused-state guard is CUR-03's idempotency spine (WR-05):
```python
snap = graph.get_state(cfg)
if snap.next != ("process_inbox",):          # never re-resume a completed run
    if values and not snap.next:
        return _completion_result(...)        # already done → no re-write
    return CurationRunResult(status="failed", message="No paused run ...")
decisions = _build_resume_decisions(inp, snap.values.get("gate_queue", []))
result = graph.invoke(Command(resume=decisions), cfg)
```

**Run-start runner** `run_curation_run` already exists (curation_run.py:514-549) — extend it to detect the pause (mirror research_run.py:933-942): when `"__interrupt__" in result and snap.next == ("process_inbox",)` return `status="awaiting_review"` with the `gate_queue`.

**Extend inspect** `inspect_curation_run` (curation_run.py:552-583) — add the `awaiting_review` branch (mirror research_run.py:1038-1082 / 1054-1065). It already has the nonexistent-run → `failed` guard (curation_run.py:569); add a `snap.next == ("process_inbox",)` → `awaiting_review` branch BEFORE the `not values` check, and surface `gate_queue`:
```python
if snap.next == ("process_inbox",):
    status, message = "awaiting_review", "Curation run paused awaiting human review."
elif not snap.next:
    status = values.get("status", "completed") if values else "failed"
```

**Required-flag fix (Pitfall 5):** once `promotion_review`/`process_inbox` are real (no longer `required=False` deferred skips), `_aggregate_status` (curation_run.py:503-511) must learn `awaiting_review` — a paused or reviewed gate is NOT `degraded`. Teach the aggregate the research_run status set (`running|awaiting_review|completed|failed`).

**Carry over verbatim (do not re-derive):** `_validate_run_id` (curation_run.py:53-66, path-traversal guard — reuse for `CurationReviewInput`), `_open_checkpointer` (curation_run.py:202-216, persistent sqlite conn — Pitfall 2), `_sanitize_error` (curation_run.py:222-231), the Pitfall-3 "no loader in state" discipline, and the Pitfall-6 "logging not print" rule.

---

### `src/construct/capabilities/catalog.py` — register + extend + delete placeholder (MOD)

**Role:** config (capability registry) · **Data flow:** request-response
**Analog:** the research.review / research.inspect registration block in the SAME file (catalog.py:411-430) + the curation shims (554-611)

**Register `card.evaluate`** — mirror `research.score` registration (catalog.py:389-398):
```python
registry.register(CapabilityRecord(
    id="card.evaluate", name="Card Evaluate",
    description="Evaluate non-mature cards through the L3 promotion gate ...",
    input_model=CardEvaluateInput, output_model=OperationResult,
    handler=_card_evaluate_shim,
    cli_name="card.evaluate", mcp_tool_name="construct_card_evaluate",
))
```

**Register `curation.review`** — mirror `research.review` registration (catalog.py:411-420):
```python
registry.register(CapabilityRecord(
    id="curation.review", name="Curation Review",
    description="Resume a paused curation run with per-item decisions; applies "
                "approved lifecycle/connection/archive writes",
    input_model=CurationReviewInput, output_model=OperationResult,
    handler=_curation_review_shim,
    cli_name="curation.review", mcp_tool_name="construct_curation_review",
))
```

**Shims** — mirror `_curation_run_shim` / `_research_review_shim` (catalog.py:554-611). Reject positional args, wrap the runner via the existing `_curation_result_to_operation` (catalog.py:572-593, already maps `status != "failed"` → success):
```python
def _curation_review_shim(*args, **kwargs):
    if args:
        raise TypeError("curation.review handler requires keyword arguments")
    return _curation_result_to_operation(
        "curation.review", lambda: review_curation_run(CurationReviewInput(**kwargs))
    )
```

**Extend `curation.inspect`** — already registered (catalog.py:443-452); no registration change, the extended `inspect_curation_run` body (above) surfaces `gate_queue` + `awaiting_review`. Update its `description` to mention pending-review state.

**DELETE the placeholder (D-10):** remove `_get_workflow_steps` (catalog.py:725-741) AND its caller in the `workflow.run` registration lambda (catalog.py:308-312). See Shared Pattern "Placeholder removal" — it lives in TWO files (Pitfall 6).

**MCP parity is free** — do NOT edit `mcp/server.py`; auto-discovery from the registry handles it (guarded by `test_mcp_no_hardcoded_curation`, test_curation_run_cli_mcp.py:76-82).

---

### `src/construct/cli.py` — curation review command + placeholder rewire (MOD)

**Role:** route (Typer) · **Data flow:** request-response
**Analog:** the `curation` Typer sub-app (already present, parity-tested at test_curation_run_cli_mcp.py:88-91 for `run`/`inspect`) + the `workflow` sub-app (cli.py:200-266)

Add a `curation review` Typer command alongside the existing `curation run`/`curation inspect` (same `get_registry().get("curation.review")` → `cap.handler(...)` → `_display_result` shape as cli.py:228-234).

**Placeholder rewire (Pitfall 6 — D-10 lives in BOTH files):** `cli.py:208-216` `_get_workflow_steps_from_registry` imports and calls the deleted `_get_workflow_steps`; `cli.py:262` `workflow resume` calls it. Decide per RESEARCH Open-Q 1: **redirect `construct workflow run curation-cycle` → `curation.run`, or remove the `workflow` group.** The anti-placeholder contract test must assert no placeholder handler is reachable from either surface.

---

### `src/construct/llm/config.yaml` — gate config entries (MOD)

**Role:** config · **Analog:** the `gates.research.score` block (config.yaml:24-31)

Add gate entries so the gates don't fall back to `research.score` config (RESEARCH A2). Mirror the existing block exactly:
```yaml
gates:
  research.score:        # existing
    provider: anthropic
    temperature: 0.2
    review_required: true
    concurrency_cap: 5
  card.evaluate:         # NEW
    provider: anthropic
    temperature: 0.2
    review_required: true
    concurrency_cap: 5
  curation.connection_type:   # NEW (inline gate id)
    provider: anthropic
    temperature: 0.2
    review_required: true
    concurrency_cap: 5
```
The `run_gate` resolver falls back to `research.score` if the id is missing (research_score.py:543) — adding these entries prevents wrong provider/cap.

---

### `tests/llm/test_curation_promote.py` (NEW)

**Role:** test (unit) · **Analog:** `tests/llm/test_research_score.py` (mirror its 24 test functions)

Mirror the analog's structure: clamp/decision-band tests → `decision`-mapping tests; `test_score_one_*` → `test_evaluate_one_*`; `test_invalid_output_retries_then_succeeds` (test_research_score.py:263) + `test_invalid_output_skip_with_reason_when_both_fail` (278) → retry-then-`escalate` with `method="rule-based"`; `test_total_outage_when_all_provider_failures` (318) and `test_run_gate_raises_on_total_outage` (331); `test_sanitized_error_never_leaks_key_token` (348) — copy this security test verbatim against the new outage class. Use the `ConfigurableStructuredMock` mock seam (see conftest below).

---

### `tests/llm/test_curation_run.py` (MOD/extend)

**Role:** test (integration) · **Analog:** `tests/llm/test_research_run.py` (mirror its HITL tests by name)

The anti-placeholder test already exists (`test_steps_return_concrete_findings`, per RESEARCH — test_curation_run.py:188). Add, mirroring `test_research_run.py`:
- `test_no_writes_before_approval` ← research_run analog test_research_run.py:130 (CUR-03 spine)
- `test_gate_review_is_interrupt_only` ← test_research_run.py:758
- `test_graph_pauses_at_gate_interrupt` ← test_research_run.py:789
- `test_cross_process_resume` ← test_research_run.py:270
- `test_reject_all_and_approve_all` ← test_research_run.py:215
- `test_inspect_no_resume` / pending-review ← test_research_run.py:317
- `test_idempotent_rerun` ← test_research_run.py:390 (skip-if-exists writes)
- plus curation-specific: `test_reviewed_promotion_applied`, `test_reviewed_connection_idempotent`, `test_reviewed_archive_applied`, `test_single_consolidated_gate`, `test_empty_queue_no_pause`, `test_no_unreviewed_writes`.

---

### `tests/llm/conftest.py` (MOD/extend)

**Role:** test fixtures/mocks · **Analog:** `ConfigurableStructuredMock` in the SAME file (conftest.py:65-101)

The mock seam is reusable as-is — it returns any caller-supplied structured object. Add `PromotionDecision`-shaped and `ConnectionTypeDecision`-shaped canned-return fixtures, and reuse `InvalidOutputMock` (conftest.py:104) for the retry path. The monkeypatch target stays `construct.llm.factory.build_chat_model` (conftest.py:40-43). No new mock class is strictly required — just new fixture builders.

---

### `tests/contract/test_curation_run_cli_mcp.py` (MOD/extend)

**Role:** test (contract) · **Analog:** self (the file already proves curation.run/inspect parity)

Extend `_CAPS` (test_curation_run_cli_mcp.py:30-33) with the new caps and re-use every existing assertion (registration, positional-arg rejection, MCP auto-discovery, CLI presence):
```python
_CAPS = {
    "curation.run": "construct_curation_run",
    "curation.inspect": "construct_curation_inspect",
    "curation.review": "construct_curation_review",   # NEW
    "card.evaluate": "construct_card_evaluate",        # NEW
}
```
Add `test_no_placeholder_curation_path` (CUR-05) asserting `_get_workflow_steps` is gone and no placeholder handler is reachable. Keep `test_mcp_no_hardcoded_curation` (76-82) green — do not edit `mcp/server.py`.

---

### `tests/contract/test_skill_migration.py` (NEW)

**Role:** test (static guard) · **Analog:** `tests/contract/test_curation_run_cli_mcp.py` (file-read assertion style, e.g. line 80 `Path(...).read_text()`)

Grep-style guard (API-04): read each migrated `SKILL.md` frontmatter and assert no `WebSearch`, `WebFetch`, or workspace-write tool survives in `allowed-tools`. Mirror the `src = Path(...).read_text(...)` + `assert "x" not in src` pattern.

---

### Skill migrations: `construct-{research-cycle,curation-cycle,card-evaluate}/SKILL.md` (MOD)

**Role:** provider (Claude skill) · **Data flow:** orchestration/delegation
**Analog:** `construct-card-create/SKILL.md` (118 lines, thin `Bash(construct knowledge *)` delegator — "The skill drives the conversation; Python enforces contracts.")

**`construct-research-cycle`** (215 lines) — frontmatter `allowed-tools: Read, Bash(construct), WebSearch, WebFetch, MCP(connect)` (line 3) **must drop `WebSearch, WebFetch`**; steps 3-5 inline search/score/ingest are superseded by `construct research run` + `construct research review` (already shipped Phase 10). Becomes scope-negotiation → invoke CLI → drive the review loop → narrate digest (D-08).

**`construct-curation-cycle`** (286 lines) — already mostly delegates (`allowed-tools: Read, Bash(construct), MCP(connect)`); rewire to `construct curation run` → present the consolidated `gate_queue` → collect approve/reject → `construct curation review`.

**`construct-card-evaluate`** (178 lines) — fold its inline promotion-judgment rules into the Python `card.evaluate` gate (D-09); becomes a thin wrapper over `construct card evaluate`, or is retired and invoked inline by the curation skill. No duplicate LLM-judgment logic left in skill text.

---

## Shared Patterns

### Interrupt-only HITL gate (the CUR-03 spine)
**Source:** `research_run.py:437-452` (`gate_review`)
**Apply to:** `curation_run.py` `process_inbox`
The pause node holds NOTHING but `interrupt()`. All writes/events live strictly downstream of it. LangGraph re-executes the interrupted node top-to-bottom on resume, so any side effect double-fires and leaks a pre-approval write. This makes CUR-03 hold *by construction*, identically to RSCH-03.

### Paused-state resume guard (idempotent completion)
**Source:** `research_run.py:1011-1027` (`review_research_run`)
**Apply to:** `curation_run.py` `review_curation_run`
```python
if snap.next != ("process_inbox",):   # never re-resume a completed run
    ... return completed/failed without re-running write nodes ...
```

### Bounded LLM fan-out + per-item retry + outage discrimination
**Source:** `research_score.py:406-532` (`_score_one_with_retry` + `score_all`) and `326-389` (outage/sanitization)
**Apply to:** both L3 gates (`curation_promote.py`, `curation_connect.py`)
Sync `ThreadPoolExecutor(max_workers=max(1, min(cap, n)))` (NEVER async gather — cap not honored). `scored_ok == 0 and provider_failures == n` → total outage. Copy `_is_provider_outage_cause` / `_safe_scoring_cause` verbatim (security-load-bearing, T-09-03/WR-06).

### Persistent SqliteSaver checkpointer (cross-process resume)
**Source:** `curation_run.py:202-216` (`_open_checkpointer`, already correct) / `research_run.py:879-894`
**Apply to:** review + inspect runners
`sqlite3.connect(str(db), check_same_thread=False)` kept alive for the whole handler, closed in `finally`. NEVER the transient connection-string context-manager form (Pitfall 2).

### Path-traversal guard on run-id inputs
**Source:** `curation_run.py:53-66` (`_validate_run_id` + `KEBAB_CASE_PATTERN`)
**Apply to:** every new input model (`CurationReviewInput`, `CardEvaluateInput`) — `extra="forbid"` + `_check_run_id = field_validator("run_id")(_validate_run_id)`. `run_id`/`gate_id` flow into the checkpoint DB path (Tampering / path traversal — V5).

### Idempotent / skip-if-exists writes
**Source:** `knowledge.py:416-423` (`add_connection` dup → `success=True, "Connection already exists"`); `research_run.py:611` (per-item try/except isolation)
**Apply to:** all three apply-nodes. `add_connection` is already idempotent; `edit_card`-promotion skips if already at `target_lifecycle`; `archive_card` skips if already `archived`. One failing write never aborts the batch.

### Capability registration + dual-mode shim (CLI/MCP parity for free)
**Source:** `catalog.py:411-430` (registration) + `554-611` (shims) + `572-593` (`_curation_result_to_operation`)
**Apply to:** `card.evaluate`, `curation.review`
Register with `cli_name` + `mcp_tool_name`; shim rejects positional args and wraps the runner. MCP auto-discovery means `mcp/server.py` is never edited (guarded by test_curation_run_cli_mcp.py:76-82).

### Error sanitization (never echo raw provider text)
**Source:** `research_score.py:384-389` (`_safe_scoring_cause`) + `curation_run.py:222-231` (`_sanitize_error`)
**Apply to:** all node `except` blocks and gate failures. Reduce to class-name + first safe line; the outage class carries a pre-sanitized `safe_message`.

### Placeholder removal (D-10 — lives in TWO files; Pitfall 6)
**Source:** `catalog.py:725-741` (`_get_workflow_steps`) + caller `catalog.py:308-312`; `cli.py:208-216` (`_get_workflow_steps_from_registry`) + `cli.py:262` (`workflow resume`)
**Apply to:** delete the catalog lambdas AND rewire/remove the cli.py callers in lockstep, or `ImportError` results. Anti-placeholder test asserts no placeholder reachable from either surface.

---

## No Analog Found

None. Every file in this phase has a strong in-repo analog — this is a grafting/copy phase by design. The only judgment calls are **discretion** items (already decided in CONTEXT/RESEARCH), not missing-analog gaps:
- Connection-typing gate: registered capability vs inline node — **recommend inline** (RESEARCH A1); still copies `research_score.py`.
- `workflow` CLI group fate — **recommend redirect-or-remove** (RESEARCH Open-Q 1).
- `escalate`-item resume semantics — **recommend review-only this phase** (RESEARCH Open-Q 3).

---

## Three RESEARCH Discrepancies (write-surface mapping caveats)

1. **Lifecycle naming:** the enum is `seed`/`growing`/`mature`/`archived` (card.py:35-39) — there is no `seedling`. `PromotionDecision.target_lifecycle` is `Literal["growing","mature"] | None`. Promotions are `seed→growing` and `growing→mature` only; **archive is a SEPARATE write type** (decay path → `archived`), never a `target_lifecycle`. Use `seed` everywhere, never `seedling`.
2. **Connection typing input:** `ConnectionRecord.type` is a REQUIRED `ConnectionType` (workspace.py:48-54) — null-typed edges cannot persist, so "untyped edges" do not exist as records. The connection-typing gate's input is **`bridge_detect` candidate pairs** (bridge_detect.py:233-244); output is a NEW connection via `add_connection`. It does not retype existing edges.
3. **Placeholder in two files:** `_get_workflow_steps` is referenced from `catalog.py` (the `workflow.run` lambda, 308-312) AND `cli.py` (208-216, 262). D-10 deletion must touch both atomically (Pitfall 6).

---

## Metadata

**Analog search scope:** `src/construct/llm/`, `src/construct/capabilities/`, `src/construct/services/`, `src/construct/pipelines/`, `src/construct/schemas/`, `tests/llm/`, `tests/contract/`, `CONSTRUCT-CLAUDE-impl/claude/skills/`
**Files scanned (read for excerpts):** research_score.py, research_run.py, curation_run.py, catalog.py, cli.py, knowledge.py, bridge_detect.py, config.yaml, card.py, workspace.py, conftest.py, test_curation_run_cli_mcp.py, + 4 SKILL.md frontmatters
**Pattern extraction date:** 2026-06-30
