# Phase 13: Daily-Cycle Composition - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 13-daily-cycle-composition
**Areas discussed:** Review handling, Degraded/failure rules, Command surface & id, Composition scope

---

## Review handling

User first clarified freeform: **"user review never blocks — it is optional."** That reframed the pause model: daily-cycle runs children non-blocking and reports pending reviews rather than waiting.

Follow-up — what happens to unreviewed proposals:

| Option | Description | Selected |
|--------|-------------|----------|
| Stay pending, no writes | Children remain parked; nothing written until optional review | |
| Auto-apply gate recommendation | daily-cycle auto-applies recommended decisions unattended | ✓ |
| Discard on next run | Unreviewed proposals expire/recomputed | |

Follow-up — auto-apply safety posture:

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-apply default; escalate stays pending | Apply promote/connection/archive + ingest; escalate never auto-written | ✓ |
| Auto-apply everything incl. escalate | Fully hands-off, writes even undecided cases | |
| Flag-gated, review is default | Safe-by-default, auto-apply only via explicit flag | |

**User's choice:** Non-blocking + auto-apply gate recommendations by default; escalate/undecided stays pending.
**Notes:** This is a deliberate departure from Phase-12's no-unreviewed-writes spine, scoped ONLY to the daily.run composition layer (children keep their own HITL contract). Justified by unattended maintenance + escalate carve-out + full event logging.

---

## Degraded / failure rules

| Option | Description | Selected |
|--------|-------------|----------|
| Isolate + degrade (continue) | Failing child never aborts; parent=degraded with per-child sanitized outcomes | ✓ |
| Halt on first failure | First failure stops the whole cycle; parent=failed | |

**User's choice:** Isolate + degrade.
**Notes:** Matches spec ("web search fails → continue with partial results, report degraded") and curation.run's per-step degrade. Status mirrors _aggregate_status; result surfaces pending-escalation count so a run is never a false "completed" (DAY-03).

---

## Command surface & id

| Option | Description | Selected |
|--------|-------------|----------|
| daily.run / construct daily run | Mirrors research.run + curation.run siblings; MCP parity via auto-discovery | ✓ |
| daily.cycle / construct daily cycle | Keeps 'cycle' name; breaks the `<noun>.run` verb pattern | |
| Revive workflow daily-cycle | Matches v0.3 doc but re-introduces the deleted `workflow` group | |

**User's choice:** daily.run / construct daily run / construct_daily_run (+ daily inspect).
**Notes:** Do not revive the `workflow run/resume` group Phase 12 (D-10) deleted.

---

## Composition scope

| Option | Description | Selected |
|--------|-------------|----------|
| research → curation → graph.status; views excluded | Pure runtime workflow; views stays a skill hook | ✓ |
| Include views-refresh in the capability | Couples runtime to derived-data/views layer | |
| research + curation only (no graph.status node) | Derives health summary instead of calling graph.status | |

**User's choice:** research.run → curation.run → graph.status; views-refresh excluded (skill hook).
**Notes:** daily.run stays a pure runtime workflow; parent skill owns the single post-run views regen.

---

## Claude's Discretion

- Parent status enum surface / result payload shape (mirror curation.run + _aggregate_status).
- Whether daily.run is a thin Python composition of the child run_* functions vs a LangGraph parent graph with subgraph nodes (architecture — research/planning to decide; "compose, don't duplicate" favors reusing child entrypoints).
- Exact auto-apply flag surface (default posture is auto-apply).

## Deferred Ideas

- Scheduled/cron execution of daily.run (non-blocking design enables it; scheduling infra out of scope).
- Per-run --skip-research / focus-domain flags.
- Views-refresh inside the capability (deferred; skill hook for now).
- Merged interactive review gate across children (considered, rejected in favor of non-blocking auto-apply).
