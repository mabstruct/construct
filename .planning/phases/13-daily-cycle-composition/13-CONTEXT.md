# Phase 13: Daily-Cycle Composition - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a **`daily.run`** parent workflow that *composes* the now-stable `research.run` and `curation.run` capabilities (plus a closing `graph.status` health summary) into one daily maintenance run, exposed through the capability registry / CLI / stdio MCP with schema+result parity, **without duplicating child logic**. Also closes the remaining v0.4 parity/compat requirements (API-01/02/03/05).

**In scope:** the `daily.run` composition capability + `daily inspect`; registry/CLI/MCP registration + parity; degraded/partial-failure semantics; auto-apply of child gate recommendations; v0.3 compatibility proof.
**Out of scope:** any new curation/research/gate *logic* (children are frozen); views-refresh inside the capability (stays a skill hook); scheduling/cron infrastructure; a merged interactive review gate.

</domain>

<decisions>
## Implementation Decisions

### Review handling (non-blocking, optional)
- **D-01:** `daily.run` **never blocks on human review** and **never interrupts** — it runs the children to completion in a single pass. Review is optional and happens *after*, via the children's existing `research review` / `curation review` commands.
- **D-02:** By default `daily.run` **auto-applies each child gate's recommended decision** (curation: promote / connection-type / archive; research: approved finding ingest). This is the "approve-all recommendations" resume path applied programmatically.
- **D-03:** **`escalate` / undecided items are NEVER auto-written.** This is the safety valve for genuinely ambiguous cases (mirrors D-07 "no default write for escalate").
  - **D-03a (reconciliation — locked 2026-07-06 after research):** The child approve-all resume runs to END (LangGraph resume is all-or-nothing — it cannot apply recommended items *and* leave a live paused checkpoint in the same pass). Reconciled semantics: `daily.run` resumes each child to END applying ONLY the recommended decisions; **escalate items receive NO canonical write** and are surfaced as a **pending-escalation count** in the parent result (feeds DAY-03 "no false completed" — a run with pending escalations is `degraded`, never bare `completed`). Escalates remain recoverable later via the child's own `review` command on a fresh run. This supersedes the earlier literal "checkpoint stays persisted mid-pass" wording; the safety property (no auto-write of ambiguous items + human-visible surfacing) is fully preserved.
- **D-04:** Every auto-applied write is **event-logged** (per-item `gate_review_approved` + step events) exactly as an interactive review would log, so the unattended writes are fully auditable.
- **D-05 (DEPARTURE — flag for planner):** D-02 is a **deliberate departure from the Phase-12 "no canonical write before human approval" spine** (CUR-03 / threat T-12-09). It is justified *only* for the unattended daily-maintenance composition: the gate recommendations are real LLM/rule judgments with reasoning, escalates are excluded (D-03), and all writes are logged (D-04). The child capabilities `curation.run` / `research.run` themselves are unchanged and still pause for review when invoked directly. The planner MUST NOT weaken the children's own HITL contract; auto-apply lives only in the `daily.run` composition layer.

### Degraded / partial-failure rules
- **D-06:** **Isolate + degrade.** A failing child never aborts the cycle — the other child and the closing `graph.status` still run. Mirrors `curation.run`'s own per-step degrade posture and the spec's "web search fails → continue with partial results, report degraded."
- **D-07:** Parent status mirrors `curation.run._aggregate_status` vocabulary (`completed` / `degraded` / `failed`). The result **surfaces per-child status + a pending-escalation count + the final graph-health summary**, so a run with pending escalations or a failed child is **never reported as a bare "completed"** (DAY-03 "no false completed result"). Child failure detail is sanitized via the existing `_sanitize_error` (never raw provider text).

### Command surface & capability id
- **D-08:** Capability id **`daily.run`**; CLI **`construct daily run`**; MCP tool **`construct_daily_run`**; plus **`daily inspect`** (read-only past-run status). Mirrors the `research.run` (`construct research run`) and `curation.run` (`construct curation run`) siblings exactly. MCP parity comes from **registry auto-discovery — do NOT edit `mcp/server.py`** (guarded like `test_mcp_no_hardcoded_curation`). Do NOT revive the `workflow run/resume` group that Phase 12 (D-10) deleted.

### Composition scope
- **D-09:** `daily.run` composes, in order, **`research.run` → `curation.run` → `graph.status`** (the closing graph-health summary folded into the result). It calls the children's existing entrypoints (`run_research_run` / `run_curation_run`) — it does **not** re-implement their steps.
- **D-10:** **Views-refresh is EXCLUDED** from the `daily.run` capability. It stays a **skill-level hook** — the daily-cycle *skill* triggers a single views regeneration after the run completes, matching the established "parent owns the single views refresh" pattern in the skill files. `daily.run` stays a pure runtime workflow.

### Claude's Discretion
- Exact parent status enum surface and result payload shape (mirror `curation.run` result + `_aggregate_status`); whether `daily.run` is a thin Python composition of the child `run_*` functions vs a LangGraph parent graph with subgraph nodes — **an architecture choice for research/planning** (spec §gestures at a "parent graph"; the "compose, don't duplicate" mandate favors reusing the child `run_*` entrypoints). The exact `--auto-apply`-style flag surface, if any, is discretion — default posture is auto-apply per D-02.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec & requirements
- `.planning/REQUIREMENTS.md` — DAY-01/02/03 (daily-cycle) + API-01/02/03/05 (registry/CLI-MCP parity + v0.3 compat) definitions.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — daily-cycle orchestrator rows (~L83, L97-115 priority table, L355 graph sketch, L467 error-handling "web search fails → continue degraded", L484 capability table `workflow.daily_cycle` extend, L578 W6 "extend to call research + curation subgraphs").
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` — the v0.3 daily-cycle skeleton/journey (J2) being extended; note it references the now-removed `construct workflow run daily-cycle`.
- `CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md` §6.2 — Daily Cycle capability definition.

### Child workflows to compose (do NOT modify their logic)
- `src/construct/llm/research_run.py` — `run_research_run` (L900), `review_research_run` (L996), `inspect_research_run` (L1038), `RunResult`.
- `src/construct/llm/curation_run.py` — `run_curation_run` (L1071), `review_curation_run` (L1134), `inspect_curation_run` (L1182), `_aggregate_status`, `_sanitize_error`, `_build_resume_decisions` (the approve-all recommendation path D-02 reuses).

### Registration / CLI / test parity patterns to mirror
- `src/construct/capabilities/catalog.py` — `CapabilityRecord` registration + `cli_name`/`mcp_tool_name` shim pattern (research.run / curation.run analogs at L201-390; note `workflow.run` was removed at ~L311-316).
- `src/construct/cli.py` — the `curation` sub-app (`run`/`inspect`/`review`) to mirror as a `daily` sub-app.
- `tests/contract/test_curation_run_cli_mcp.py` — the registration + CLI/MCP parity + no-hardcoded-MCP contract test shape to mirror for `daily.run` (API-01/02/03).

### Prior HITL/composition decisions
- `.planning/phases/12-curation-l3-gates-review-application/12-CONTEXT.md` — CUR-03 spine, escalate=review-only (D-07), single consolidated gate.
- `.planning/phases/10-durable-human-review-research-run/10-CONTEXT.md` — research.run HITL/resume machine that curation mirrored.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Child entrypoints:** `run_research_run` / `run_curation_run` (+ their `review_*` / `inspect_*`) are the composition targets — `daily.run` calls these directly (D-09), no duplication.
- **`_aggregate_status` + `_sanitize_error`** (curation_run.py): reuse for the parent degrade/status roll-up (D-06/D-07).
- **`_build_resume_decisions` / approve-all path** (curation_run.py): the mechanism `daily.run` uses to auto-apply gate recommendations while excluding escalate (D-02/D-03).
- **`graph.status` capability**: source of the closing health summary (D-09).
- **`append_event`** (services/event_log): audit trail for auto-applied writes (D-04).
- **CapabilityRecord + cli_name/mcp_tool_name shim** (catalog.py): registration pattern giving free MCP parity (D-08).

### Established Patterns
- Registry-backed capability + MCP auto-discovery (never edit `mcp/server.py`).
- LangGraph `StateGraph` + checkpoint sqlite for the children (their checkpoints persist for later optional review of escalates).
- Degraded runs report status but exit 0 (curation exit-code contract — carried from Phase 11).
- Contract-test parity suite per capability (mirror `test_curation_run_cli_mcp.py`).

### Integration Points
- New `daily` Typer sub-app in `cli.py`; new `daily.run` + `daily.inspect` records in `catalog.py`.
- Parent composition module (e.g. `src/construct/llm/daily_run.py`) invoking the two child `run_*` functions + `graph.status`.
- The daily-cycle *skill* (`CONSTRUCT-CLAUDE-impl/claude/skills/`) keeps ownership of the single post-run views refresh (D-10).

</code_context>

<specifics>
## Specific Ideas

- "User review never blocks — it is optional" (verbatim user framing) → the defining constraint behind D-01/D-02.
- Auto-apply the gate's *recommended* decision (not a blanket approve of everything) — escalate is the explicit carve-out.

</specifics>

<deferred>
## Deferred Ideas

- **Scheduled/cron execution** of `daily.run` (true unattended automation) — the capability is designed to run non-blocking so it *could* be scheduled, but scheduling infrastructure is out of scope for this phase.
- **Per-run `--skip-research` / focus-domain flags** — plausible ergonomics, not required by DAY-01/02/03; revisit if needed.
- **Views-refresh inside the capability** — deliberately left as a skill hook (D-10); a runtime views-generation node is a v0.5 / derived-data concern.
- **Merged interactive review gate** across children — considered and rejected in favor of non-blocking auto-apply (D-01); revisit only if an "attended daily-cycle" mode is ever wanted.

</deferred>

---

*Phase: 13-daily-cycle-composition*
*Context gathered: 2026-07-06*
