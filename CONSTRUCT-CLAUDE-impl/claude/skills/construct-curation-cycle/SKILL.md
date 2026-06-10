---
description: "Run a full graph maintenance pass — validate cards, check health, promote/decay lifecycle, detect orphans. Use when user says 'curate', 'clean up the graph', 'check graph health', 'run maintenance'."
allowed-tools: Read, Bash(construct), MCP(connect)
---
# Skill: Curation Cycle

**Trigger:** User says "curate", "clean up the graph", "check graph health", "run maintenance", or similar.
**Agent:** Curator
**Produces:** Updated cards (lifecycle changes via CLI), connection updates, health report, event log entries

---

## Prerequisites

The CLI must be available on `$PATH`. For MCP-based operations, start the server:

```bash
construct mcp &
```

## Procedure

Run all 7 steps. Each step is independent — continue even if one step finds issues.

---

### Step 1: Integrity Check

**INPUT:** Workspace `cards/` directory, `connections.json`
**OUTPUT:** Validation report with errors and warnings

Validate workspace integrity via CLI:

```bash
construct validate --workspace . --json
```

**Alternative (MCP):** Invoke the `construct_validate` tool:

```json
{
  "tool": "construct_validate",
  "arguments": {
    "path": "."
  }
}
```

The validation command checks:

**Required fields:**
- `id`, `title`, `epistemic_type`, `created`, `confidence`, `source_tier`, `domains`

**Value validation:**
- `confidence` is integer 1–5
- `source_tier` is integer 1–5
- `epistemic_type` is valid enum
- `lifecycle` is valid enum: seed | growing | mature | archived
- `domains` entries exist in `domains.yaml`

**Connection integrity:**
- For each edge in `connections.json`, verify both `from` and `to` card IDs exist
- Flag dangling references

**Report findings:**

> "Integrity: {N} cards checked, {N} valid, {N} errors: {error summary}"

---

### Step 2: Decay Scan

**INPUT:** `governance.yaml` decay settings, card lifecycle data
**OUTPUT:** List of stale cards, optionally archived

Read `governance.yaml` → `decay.decay_window_days` (default: 28).

Load card data for lifecycle and last_verified:

```bash
construct knowledge card list --workspace . --json
```

**Note:** If `card list` is not yet implemented, read individual card files via `Read cards/<id>.md` to check `last_verified` and `created` dates.

For each non-archived card:
- Check `last_verified` date (or `created` if never verified)
- If older than decay window → flag as stale

```
Stale: {card-id} — last verified {date}, {N} days ago
```

If `auto_archive_on_decay: true` → archive the card via CLI:

```bash
construct knowledge card archive <card-id> --author curator --workspace .
```

Otherwise → just report.

---

### Step 3: Orphan Scan

**INPUT:** Card lifecycle data (from Step 2), connection data
**OUTPUT:** List of orphan cards with zero connections

Read `governance.yaml` → `quality.orphan_tolerance_days` (default: 7).

Get connection data via CLI:

```bash
construct knowledge connection list --workspace . --json
```

For each non-archived card:
- Count connections where card appears as `from` or `to`
- If zero connections AND card is older than tolerance → flag as orphan

```
Orphan: {card-id} — {N} days old, zero connections
```

For borderline orphan cases, apply LLM judgment: Is the card self-contained and valuable even without connections? If yes, keep it; if it's a dead end, recommend archiving.

---

### Step 4: Promotion Scan

**INPUT:** Card lifecycle data (from Step 2), governance rules (from Step 2)
**OUTPUT:** Promoted cards or escalation list

Invoke the `construct-card-evaluate` skill (see `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md`):

- Apply rule-based promotion for clear candidates (use `construct knowledge card edit --lifecycle`)
- Evaluate ambiguous cards using the evaluation rubric
- Escalate when human judgment needed

> "This step delegates to `construct-card-evaluate` — that skill handles the detailed promotion logic, governance thresholds, and ambiguous-case evaluation."

---

### Step 5: Connection Maintenance

**INPUT:** Current connection list, card summaries
**OUTPUT:** Updated connections.json via CLI

**Type untyped edges:**
- Get current connections:

  ```bash
  construct knowledge connection list --workspace . --json
  ```

- Scan for edges where `type` is null or empty
- For each, read both cards' summaries via `Read cards/<id>.md` (requires card content for LLM judgment)
- Propose a relation type (see `.construct/references/connection-types.md`)
- Add typed connection via CLI:

  ```bash
  construct knowledge connection add <from-id> <to-id> --type <relation> --by curator --workspace .
  ```

- Remove the untyped edge (if replacing an existing connection):

  ```bash
  construct knowledge connection remove <from-id> <to-id> --type <old-type> --workspace .
  ```

**Cross-domain bridge detection:**

Level 1 (graph structure):
- Use connection list from above to find cards that connect to cards in different domains
- These are natural bridge nodes

Level 2 (category overlap):
- Find cards sharing content categories across different domains
- These may indicate structural parallels

Report bridges found:

> "Bridges detected: {card-id} connects {domain-A} ↔ {domain-B} ({relation})"

---

### Step 6: Process Inbox (if applicable)

**INPUT:** User's pending actions (flagged cards, suggested connections)
**OUTPUT:** Confirmed actions processed

If there are any pending user actions:
- List them for the user
- Process confirmed actions using the same CLI commands (edit, archive, connection add/remove)

Optionally check active workflow state:

```bash
construct workflow status --workspace .
```

---

### Step 7: Stats & Report

**INPUT:** Results from Steps 1–6
**OUTPUT:** Human-readable graph health report

Compile and present:

```bash
construct status --workspace . --json
```

Or invoke MCP `construct_graph_status` for the structured health data.

```
## Graph Health Report — {date}

### Overview
- Total cards: {N} (seed: {N}, growing: {N}, mature: {N}, archived: {N})
- Total connections: {N}
- Domains: {N} active

### Quality
- Integrity errors: {N}
- Stale cards (decay): {N}
- Orphan cards: {N}
- Average confidence: {N.N}
- Average connections per card: {N.N}

### Actions Taken
- Cards promoted: {N}
- Connections typed: {N}
- Bridges detected: {N}

### Attention Needed
- {list of escalated items}
- {list of cards needing human review}
```

Log: `curation_cycle_complete` event appended to `log/events.jsonl`.

---

### Step 8: Views Refresh Hook

**OUTPUT:** Optional views regeneration

If `views/build/` exists at the install root AND `.construct/config.yaml` does not set `views.auto_regenerate: false`:

**Skip check:** If this skill was invoked as part of `daily-cycle` or another parent workflow that runs multiple hooked skills in sequence, skip this hook — the parent will trigger a single regeneration after all child skills complete. This avoids redundant regeneration (e.g., daily-cycle runs research-cycle → curation-cycle → both would fire hooks; only the last one matters since regen is full and idempotent).

If not skipped:
1. Run the views generate data capability:

   ```bash
   construct views generate --workspace .
   ```

   Or invoke MCP `construct_views_generate_data`.

2. If it succeeds → if `.construct/config.yaml` sets `views.confirm_refresh: true`, append to the report: `✓ views updated (build_id: {id})`. Otherwise, no extra user-facing message (the SPA picks it up via `version.json` polling within 30s).

3. If it fails → append a warning to the report:

   > ⚠ views regeneration failed: {single-line message}. Workspace is intact; run `views generate` manually to refresh the views.

4. Always preserve this skill's success status — the hook is a side effect, not a success condition

If `views/build/` does not exist, or `views.auto_regenerate` is `false` → skip silently (no log, no message).

---

## Validation

- [ ] Step 1: `construct validate --json` or `construct_validate` MCP tool called correctly
- [ ] Step 2: Card data loaded via CLI or Read; archiving uses `construct knowledge card archive`
- [ ] Step 3: Connection data loaded via `construct knowledge connection list`
- [ ] Step 4: `construct-card-evaluate` skill invoked for promotion decisions
- [ ] Step 5: `construct knowledge connection add/remove` used for connection ops
- [ ] Step 6: Inbox items processed and confirmed
- [ ] Step 7: Health data loaded via `construct status` or `construct_graph_status`
- [ ] Step 8: Views refresh is optional and non-blocking
- [ ] Events logged for every action taken
- [ ] `connections.json` remains valid JSON after all updates
