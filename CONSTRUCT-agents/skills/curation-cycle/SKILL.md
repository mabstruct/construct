# Skill: Curation Cycle

**Trigger:** User says "curate", "clean up the graph", "check graph health", "run maintenance", or similar.
**Agent:** Curator
**Produces:** Updated cards (lifecycle changes), connection updates, health report, event log entries

---

## Procedure

Run all 7 steps. Each step is independent — continue even if one step finds issues.

### Step 1: Integrity Check

Read all `cards/*.md` files and validate each against the card schema:

**Required fields check:**
- `id`, `title`, `epistemic_type`, `created`, `confidence`, `source_tier`, `domains`

**Value validation:**
- `confidence` is integer 1–5
- `source_tier` is integer 1–5
- `epistemic_type` is valid enum (see `references/epistemic-types.md`)
- `lifecycle` is valid enum: seed | growing | mature | archived
- `domains` entries exist in `domains.yaml`

**Connection integrity:**
- For each edge in `connections.json`, verify both `from` and `to` card IDs exist as files in `cards/`
- For each card's `connects_to` frontmatter entries, verify target card exists
- Flag dangling references

**Report findings:**
> "Integrity: {N} cards checked, {N} valid, {N} errors: {error summary}"

### Step 2: Decay Scan

Read `governance.yaml` → `decay.decay_window_days` (default: 28).

For each non-archived card:
- Check `last_verified` date (or `created` if never verified)
- If older than decay window → flag as stale

```
Stale: {card-id} — last verified {date}, {N} days ago
```

If `auto_archive_on_decay: true` → archive the card (update lifecycle to `archived`).
Otherwise → just report.

### Step 3: Orphan Scan

Read `governance.yaml` → `quality.orphan_tolerance_days` (default: 7).

For each non-archived card:
- Count connections in `connections.json` where card appears as `from` or `to`
- If zero connections AND card is older than tolerance → flag as orphan

```
Orphan: {card-id} — {N} days old, zero connections
```

### Step 4: Promotion Scan

Invoke `card-evaluate` skill logic:
- Apply rule-based promotion for clear candidates
- Evaluate ambiguous cards
- Escalate when judgment needed

### Step 5: Connection Maintenance

**Type untyped edges:**
- Scan `connections.json` for edges where `type` is null or empty
- For each, read both cards' summaries
- Propose a relation type (see `references/connection-types.md`)
- Update `connections.json` with proposed type

**Cross-domain bridge detection:**

Level 1 (graph structure):
- Find cards that connect to cards in different domains
- These are natural bridge nodes

Level 2 (category overlap):
- Find cards sharing content categories across different domains
- These may indicate structural parallels

Report bridges found:
> "Bridges detected: {card-id} connects {domain-A} ↔ {domain-B} ({relation})"

### Step 6: Process Inbox (if applicable)

If there are any pending user actions (flagged cards, suggested connections awaiting confirmation):
- List them for the user
- Process confirmed actions

### Step 7: Stats & Report

Compile and present:

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

Log: `curation_cycle_complete` event.

---

## Validation

- [ ] All card files parsed without error
- [ ] connections.json remains valid JSON after updates
- [ ] No card was promoted that doesn't meet minimum criteria
- [ ] All typed connections use valid relation types
- [ ] Events logged for every action taken
