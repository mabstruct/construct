---
description: "Run a full daily cycle — delegate to the Python daily.run capability, narrate the composed digest. Use when user says 'daily', 'run the daily cycle', 'catch me up', 'daily digest'."
allowed-tools: Read, Bash(construct), MCP(connect)
---

> **Thin orchestrator (Phase 17, D-08):** research, curation, and graph-health logic do NOT live in this skill's prose — they are the frozen Python `research.run` / `curation.run` / `graph.status` capabilities, composed by the non-blocking `daily.run` workflow (Phase 13). This skill is a **thin orchestrator**: it optionally negotiates a domain focus, invokes `construct daily run`, and narrates the composed result. The skill drives the conversation; Python enforces the contracts and owns every side effect. This skill holds no direct web-fetch or workspace-write tool — every write flows through the Python capability, by design. Unlike the research- and curation-cycle siblings, this skill has **no interactive gate loop**: `daily.run` is non-blocking and auto-resumes each child with the gate's recommended decision, so the skill narrates and surfaces a pending-escalation count — it never collects per-item approve/reject decisions.

# Skill: Daily Cycle

**Trigger:** User says "daily", "run the daily cycle", "catch me up", "daily digest", or similar.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** A composed cross-capability digest — the research digest, the curation report, and the closing graph-health summary — all written by the Python capabilities behind their own gates. This skill writes nothing itself.

---

## Prerequisites

The CLI must be available on `$PATH`. For MCP-based operation, start the server:

```bash
construct mcp &
```

## Procedure

### Step 1: Optionally Negotiate a Domain Focus (read-only)

**INPUT:** Workspace files on disk, user request
**OUTPUT:** An optional focus decision confirmed with the user (default: full cycle across all active domains)

If the user named a domain or topic, confirm the scope conversationally. You may read small config files for context only — you are NOT scoring, searching, or ingesting from them:

- `domains.yaml` — domain definitions and categories
- `search-seeds.json` — active search clusters

`daily.run` composes the deterministic research → curation → graph-status pass itself; you do no searching or curation here. If nothing needs negotiating, proceed straight to Step 2 with the full cycle.

### Step 2: Invoke the Daily Capability

**INPUT:** Workspace on disk (optional confirmed focus)
**OUTPUT:** A single non-blocking daily run that composes the child cycles and returns one `DailyRunResult` (no pause, no parent resume)
**METHOD:** CLI `construct daily run` (composes `research.run` → `curation.run` → `graph.status`; owns every write boundary)

Run the capability against the workspace:

```bash
construct daily run --workspace . --json
```

**Alternative (MCP):** invoke the `construct_daily_run` tool with `{"workspace_path": "."}`.

`construct daily run` runs the research → curation → graph-status cycle in a single non-blocking pass (D-01): it auto-applies each child gate's recommended decision, never auto-writes escalated/ambiguous items, and returns per-child status plus a pending-escalation count and the closing graph-health summary. It does **not** pause for review — there is no gate queue to present and no run to resume here.

### Step 3: Narrate the Composed Result

**INPUT:** The `DailyRunResult` from Step 2
**OUTPUT:** A concise, honest daily digest for the user

Relay the capability's composed result. Cite the numbers it returned; do not recompute them. Use the `DailyRunResult` fields:

- **`status`** — the run-level aggregate: `completed`, `degraded`, or `failed`. Report it plainly. A `degraded` status means a child cycle failed/degraded or there are pending escalations — it is never a bare "completed".
- **`children`** — the per-child folded surface (`research.run`, `curation.run`, `graph.status`). For each, surface its `status`, its own `message` (the research digest / the curation report), and its `pending_escalations`.
- **`graph_health`** — the closing graph-status summary (card / connection / domain counts, quality signals).

```
## Daily Cycle — {date}

**Status:** {completed | degraded | failed}

### Research
{research child status + digest message}

### Curation
{curation child status + report message}

### Graph Health
{graph_health summary — cards, connections, domains, quality signals}
```

### Step 4: Surface the Pending-Escalation Count

**INPUT:** `pending_escalations` from the run result
**OUTPUT:** An honest count of what `daily.run` could not auto-decide

State the run-level `pending_escalations` count — the items the children's gates escalated and that `daily.run` deliberately did NOT auto-write (D-02/D-03a). Do not editorialize or re-derive them; the Python gates own that judgment. If the count is zero, say so.

> "{N} items were escalated and left for your review — `daily.run` did not auto-decide them."

### Step 5: Point to Interactive Review for Pending Items

**INPUT:** A non-zero `pending_escalations` count
**OUTPUT:** An honest hand-off to the interactive review surfaces

`daily.run` is non-blocking and single-pass — there is no parent resume. To act on escalated items, the user runs a fresh interactive cycle through the children's own review commands:

```bash
construct research review --workspace . --run-id <run_id> --json
construct curation review --workspace . --run-id <run_id> --json
```

Point the user to `construct research review` and `construct curation review` for per-item approve/reject handling on a fresh cycle. This skill never collects those decisions itself.

> **No views refresh step here.** The `daily.run` capability and each of its children regenerate the views data themselves in the Python layer, gated on `views/build/` and `views.auto_regenerate`, as a side effect that never changes a run's status (D-11; rationale in [`adr-0005-views-refresh-ownership.md`](../../../../CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md)).

---

## Validation

- [ ] `construct daily run --workspace . --json` invoked (no inline research / curation / graph-status logic)
- [ ] No gate queue presented and no run resumed — `daily.run` is non-blocking by design
- [ ] Composed result narrated from `DailyRunResult` (`status`, `children`, `graph_health`) with the capability's own counts
- [ ] `pending_escalations` count surfaced honestly
- [ ] User pointed to `construct research review` / `construct curation review` for interactive handling of pending items
- [ ] No direct workspace writes performed by this skill
