---
description: "Run a full graph maintenance pass — delegate to the Python curation capability, drive the consolidated approve/reject review loop, narrate the health report. Use when user says 'curate', 'clean up the graph', 'check graph health', 'run maintenance'."
allowed-tools: Read, Bash(construct), MCP(connect)
---

> **Migrated for Phase 12 (API-04, D-08):** Integrity, decay, orphan, promotion, and connection-typing logic no longer live in this skill's prose — they are the Python `curation.run` capability (Phase 11/12). This skill is a **thin orchestrator**: it invokes `construct curation run`, presents the single consolidated gate queue, collects approve/reject decisions, resumes via `construct curation review`, and narrates the report. The skill drives the conversation; Python enforces the contracts and owns every write. No inline curation logic survives here.

# Skill: Curation Cycle

**Trigger:** User says "curate", "clean up the graph", "check graph health", "run maintenance", or similar.
**Agent:** Curator
**Produces:** Lifecycle promotions, typed connections, archives, health report, event log entries — all written by the Python capability behind the human gate.

---

## Prerequisites

The CLI must be available on `$PATH`. For MCP-based operation, start the server:

```bash
construct mcp &
```

## Procedure

### Step 1: Invoke the Curation Capability

**INPUT:** Workspace on disk
**OUTPUT:** A durable curation run that runs the deterministic maintenance pass and pauses at the consolidated review gate (no writes before approval)
**METHOD:** CLI `construct curation run` (owns integrity, decay, orphan, promotion, connection-typing, and the write boundary)

Run the capability against the workspace:

```bash
construct curation run --workspace . --json
```

**Alternative (MCP):** invoke the `construct_curation_run` tool with `{"workspace_path": "."}`.

The run executes the deterministic prefix (integrity → decay → orphan → promotion evaluation → connection maintenance) and then **pauses** at a single consolidated review gate, returning `status: awaiting_review`, a `run_id`, and a consolidated `gate_queue`. It writes nothing to the source of truth until you resume it (Step 3). If the queue is empty, the run completes immediately with a report — skip to Step 4.

### Step 2: Present the Consolidated Gate Queue

**INPUT:** `gate_queue` + `run_id` from Step 1
**OUTPUT:** The user's per-item approve/reject decisions

The `gate_queue` is a single consolidated list mixing several proposal kinds. Present them grouped so the user sees each write type distinctly:

- **promotion** — a card proposed for `seed → growing` or `growing → mature`
- **connection** — a proposed typed edge between two cards
- **archive** — a stale card proposed for archiving (decay path)
- **escalate** — a card the gate could not decide; review-only this phase (no default write)

**Surface the `method` field on each promotion/escalate item** so the user can tell failure-driven escalations apart from genuine borderline ones:
- `method: rule-based` → the gate escalated because the LLM evaluation failed/retried out — a mechanical escalation, not a judgment call.
- `method: llm-judgment` → a genuine borderline decision the model reasoned about.

For each item show the reasoning the capability returned. Do not re-derive or override the judgment — it is the Python gate's, and it is the single source of truth. Let the user:
- approve a subset and reject the rest, or
- approve everything (approve-all), or
- reject everything (reject-all).

### Step 3: Resume via Review

**INPUT:** `run_id` from Step 1 + the user's decisions
**OUTPUT:** Approved lifecycle/connection/archive writes applied; rejected items dropped
**METHOD:** CLI `construct curation review` (the write boundary — only approved items are persisted)

Resume the paused run with the collected decisions:

```bash
# Approve every proposal's recommended write:
construct curation review --workspace . --run-id <run_id> --approve-all --json

# Or reject (write nothing for) every proposal:
construct curation review --workspace . --run-id <run_id> --reject-all --json

# Or a per-item decision set (pipe JSON on stdin or pass --decisions-file):
echo '<decisions-json>' | construct curation review --workspace . --run-id <run_id> --json
```

Use exactly one of `--approve-all`, `--reject-all`, or a decisions payload. Only approved items are written; the capability applies promotions (`edit_card` lifecycle), connections (`add_connection`, idempotent), and archives (`archive_card`) with per-item isolation and event logging.

### Step 4: Narrate the Report

**INPUT:** The review/run result
**OUTPUT:** A human-readable graph health report + confirmation

Relay the capability's report back to the user. Cite the counts it returned; do not recompute them:

```
## Graph Health Report — {date}

### Overview
- Total cards: {N} (seed / growing / mature / archived)
- Total connections: {N}
- Domains: {N} active

### Quality
- Integrity errors: {N}
- Stale cards (decay): {N}
- Orphan cards: {N}

### Actions Taken (approved this cycle)
- Cards promoted: {N}
- Connections typed: {N}
- Cards archived: {N}

### Attention Needed
- {escalated items surfaced for human review}
```

The capability logs `curation_cycle_complete` to `log/events.jsonl` — no manual log entry needed.

> **No views refresh step here.** The `curation.run` capability regenerates the views data itself in the Python layer, gated on `views/build/` and `views.auto_regenerate`, as a side effect that never changes the run's status (D-11; rationale in [`adr-0005-views-refresh-ownership.md`](../../../../CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md)).

---

## Validation

- [ ] `construct curation run` invoked (no inline integrity/decay/orphan/promotion/connection logic)
- [ ] Consolidated `gate_queue` presented, grouped by kind, with the `method` field visible on promotion/escalate items
- [ ] User decisions collected (subset / approve-all / reject-all)
- [ ] `construct curation review` resumed the run — only approved items written
- [ ] Health report relayed with the capability's own counts
- [ ] No direct workspace writes performed by this skill
