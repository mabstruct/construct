---
description: "Run a research cycle — negotiate scope, delegate to the Python research capability, drive the human-review gate, narrate the digest. Use when user says 'research', 'find papers', 'what's new in domain', 'run a research cycle'."
allowed-tools: Read, Bash(construct), MCP(connect)
---

> **Migrated for Phase 12 (API-04, D-08):** Web search, relevance scoring, and ingestion are no longer LLM-driven inside this skill. They live in the Python `research.run` capability (Phase 10). This skill is a **thin orchestrator**: it negotiates scope, invokes `construct research run`, drives the approve/reject review loop, and narrates the result. The skill drives the conversation; Python enforces the contracts and owns every side effect. This skill holds no direct web-fetch or workspace-write tool — those side effects flow only through the Python capability, by design.

# Skill: Research Cycle

**Trigger:** User says "research", "find papers", "what's new in {domain}", "run a research cycle", or similar.
**Agent:** Researcher
**Produces:** New ref files, seed cards, cycle digest, event log entries — all written by the Python capability behind the human gate.

---

## Procedure

### Step 1: Load Configuration (read-only)

**INPUT:** Workspace files on disk
**OUTPUT:** Domain config + search seeds in agent context, used only to negotiate scope with the user

Read these small config files so you can talk the user through scope. These are legitimate config reads — you are NOT scoring or ingesting from them:

- `search-seeds.json` — active search clusters
- `domains.yaml` — domain definitions and categories
- `governance.yaml` — research thresholds (informational only; the capability enforces them)

If no active clusters exist, tell the user:
> "No search patterns configured. Run domain init first to seed your research."

### Step 2: Negotiate Search Scope

**INPUT:** Domain config, user request
**OUTPUT:** A concrete scope decision confirmed with the user

Determine and confirm scope conversationally:
- **Full cycle:** all active clusters across all active domains
- **Domain-specific:** user named a domain → that domain's clusters
- **Targeted:** user gave a specific topic → a focused run

Surface the candidate count / expected volume so the user knows what they are approving. Do NOT perform any search yourself — the capability does the searching, scoring, and dedup.

### Step 3: Invoke the Research Capability

**INPUT:** Confirmed scope
**OUTPUT:** A durable research run that pauses at the human-review gate (no writes before approval)
**METHOD:** CLI `construct research run` (owns web search, extraction, scoring, dedup, and the write boundary)

Run the capability against the workspace:

```bash
construct research run --workspace . --json
```

Add `--provider <name>` only if the user asked to override the default provider.

The run executes the deterministic search → score → dedup pipeline and then **pauses** at the review gate, returning `status: awaiting_review` plus a `run_id` and a `gate_queue` of pending findings. It writes nothing to the source of truth until you resume it (Step 5). If the queue is empty, the run completes immediately with a digest — skip to Step 6.

### Step 4: Present the Pending Gate Queue

**INPUT:** `gate_queue` + `run_id` from Step 3
**OUTPUT:** The user's per-item approve/reject decisions

Present the pending findings to the user in a readable form — for each queued finding surface title, source, relevance score, and the capability's recommended ingest action. Let the user:
- approve a subset and reject the rest, or
- approve everything (approve-all), or
- reject everything (reject-all).

Do not editorialize the scores — they come from the Python gate. Your job is to relay them clearly and collect the decision.

### Step 5: Resume via Review

**INPUT:** `run_id` from Step 3 + the user's decisions
**OUTPUT:** Approved findings written (refs + seed cards + event log); rejected findings dropped
**METHOD:** CLI `construct research review` (the write boundary — only approved items are persisted)

Resume the paused run with the collected decisions:

```bash
# Approve everything the user accepted:
construct research review --workspace . --run-id <run_id> --approve-all --json

# Or reject everything:
construct research review --workspace . --run-id <run_id> --reject-all --json

# Or a per-finding decision set (pipe JSON on stdin or pass --decisions-file):
echo '<decisions-json>' | construct research review --workspace . --run-id <run_id> --json
```

Use exactly one of `--approve-all`, `--reject-all`, or a decisions payload. Only approved items are written; the capability handles ref/card creation, dedup, and event logging.

### Step 6: Narrate the Digest

**INPUT:** The review/run result
**OUTPUT:** A concise summary to the user + confirmation

Relay the capability's digest/report back to the user — papers found, ingested, skipped (duplicates / low relevance), seed cards created, and the digest path. Cite the numbers the capability returned; do not recompute them.

> "Research cycle complete for {domain}: {N} findings, {N} ingested, {N} seed cards created. See digest: {path}."

### Step 7: Views Refresh Hook

If this skill was invoked as part of `daily-cycle` or another parent workflow that runs multiple hooked skills in sequence, skip this hook — the parent triggers a single regeneration after all child skills complete.

Otherwise, if `views/build/` exists at the install root AND `.construct/config.yaml` does not set `views.auto_regenerate: false`:

```bash
construct views generate --workspace .
```

- On success: if `.construct/config.yaml` sets `views.confirm_refresh: true`, append `✓ views updated`. Otherwise stay silent (the SPA polls `version.json`).
- On failure: append `⚠ views regeneration failed: {single-line message}. Workspace is intact; run 'construct views generate' manually to refresh the views.`
- Always preserve this skill's success status — the hook is a side effect, not a success condition.

If `views/build/` does not exist, or `views.auto_regenerate` is `false` → skip silently.

---

## Validation

- [ ] Scope negotiated and confirmed with the user before invoking the capability
- [ ] `construct research run` invoked (no inline web search / fetch / scoring / ingestion)
- [ ] Pending `gate_queue` presented; user decisions collected
- [ ] `construct research review` resumed the run — only approved items written
- [ ] Digest/report relayed with the capability's own counts
- [ ] No direct workspace writes performed by this skill
