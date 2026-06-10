---
description: "Evaluate cards for lifecycle promotion or decay. Use when user says 'evaluate cards', 'check promotions', or during curation cycle."
allowed-tools: Read, Bash(construct), MCP(connect)
---
# Skill: Evaluate Card for Promotion

**Trigger:** User says "evaluate cards", "check promotions", or during curation cycle Step 4.
**Agent:** Curator
**Produces:** Card lifecycle updates logged via CLI, event log entries

---

## Prerequisites

The CLI must be available on `$PATH`. For MCP-based operations, start the server:

```bash
construct mcp &
```

## Procedure

### Step 1: Load Governance Rules

Read `governance.yaml` promotion thresholds (this is a small config file — direct read is appropriate):

**INPUT:** `governance.yaml` (workspace root)
**OUTPUT:** Governance thresholds dictionary

- `seed_to_growing_confidence` (default: 2)
- `seed_to_growing_min_connections` (default: 1)
- `growing_to_mature_confidence` (default: 3)
- `growing_to_mature_source_tier` (default: 2)
- `growing_to_mature_min_connections` (default: 2)
- `require_human_approval` (default: false)

### Step 2: Load Card Data

**INPUT:** Workspace `cards/` directory, `connections.json`
**OUTPUT:** Card frontmatter list with connection counts

Read card data via CLI (loads card frontmatter without file-by-file scanning):

```bash
# List cards with structured output
construct knowledge card list --workspace . --json
```

**Note:** If `card list` is not yet implemented, read individual card files with `Read cards/<id>.md` and aggregate manually. Get connection counts from:

```bash
construct knowledge connection list --workspace . --json
```

This returns structured JSON with all cards' frontmatter (id, title, epistemic_type, confidence, source_tier, lifecycle, domains, last_verified, created) and connection data.

### Step 3: Apply Promotion Rules

**INPUT:** Governance thresholds (from Step 1) + card/connection data (from Step 2)
**OUTPUT:** Lists of qualified, ambiguous, and ineligible cards

#### Seed → Growing

Card qualifies if ALL of:
- `lifecycle: seed`
- `confidence >= seed_to_growing_confidence`
- connection count >= `seed_to_growing_min_connections`

#### Growing → Mature

Card qualifies if ALL of:
- `lifecycle: growing`
- `confidence >= growing_to_mature_confidence`
- `source_tier <= growing_to_mature_source_tier`
- connection count >= `growing_to_mature_min_connections`

### Step 4: Handle Clear Promotions

**INPUT:** Qualified cards list + governance rules
**OUTPUT:** Updated card lifecycles

For cards that meet ALL criteria:
- If `require_human_approval: false` → promote directly via CLI (use `construct knowledge card edit --lifecycle`):

  ```bash
  construct knowledge card edit <card-id> --lifecycle growing --author curator --workspace .
  ```

- If `require_human_approval: true` → flag for review, list to user

### Step 5: Evaluate Ambiguous Cards (LLM Judgment)

**INPUT:** Borderline cards + governance thresholds
**OUTPUT:** Promotion decision (promote | hold | escalate)

For cards that meet SOME but not all criteria, apply LLM judgment:

1. Read the card's full content via CLI:

   ```bash
   construct knowledge card get <card-id> --workspace . --json
   ```

   Or read directly: `Read cards/<card-id>.md`

2. Assess:
   - Is the content quality sufficient despite missing a threshold?
   - Is the source reliable enough?
   - Are existing connections meaningful?

3. Decide: `promote` | `hold` | `escalate`

**Promote:** Quality justifies overriding a missing threshold. Update via CLI:

```bash
construct knowledge card edit <card-id> --lifecycle <growing|mature> --author curator --workspace .
```

**Hold:** Not ready. Note why in response.
**Escalate:** Needs human judgment. Present the card's case to the user.

### Step 6: Log Events

**INPUT:** Promotion decisions and card IDs
**OUTPUT:** Event log entries

For each action, append to `log/events.jsonl`:

```json
{"event": "promote_card", "timestamp": "{ISO-8601}", "card_id": "{id}", "from": "seed", "to": "growing", "method": "rule-based|judgment"}
```

Log entries can also be written via CLI:

```bash
construct event log --event promote_card --card <id> --from seed --to growing
```

### Step 7: Report

**OUTPUT:** Human-readable promotion summary

Summarize:

> "Promotion scan complete:
> - {N} cards promoted (seed → growing: {N}, growing → mature: {N})
> - {N} cards held (not ready)
> - {N} cards need your review: {list}"

---

## Evaluation Rubric for Ambiguous Cards

When a card doesn't clearly meet all thresholds, consider:

| Factor | Weight | Question |
|--------|--------|----------|
| Content quality | High | Is the summary clear, specific, and substantive? |
| Source reliability | High | Even if tier 3+, is the source credible for this claim? |
| Connection quality | Medium | Are existing connections meaningful, not just incidental? |
| Recency | Low | Is this recent enough to be relevant? |
| Domain coverage | Low | Does this fill a gap in the domain? |

If 3+ factors are positive → lean promote.
If 2+ factors are negative → lean hold.
If mixed with high-weight negatives → escalate.

---

## Validation

- [ ] Governance rules loaded from `governance.yaml`
- [ ] Card data loaded via CLI (or fallback `Read`)
- [ ] Connection data loaded via `construct knowledge connection list`
- [ ] All promoted cards meet minimum criteria
- [ ] `construct knowledge card edit` used for lifecycle updates
- [ ] Ambiguous cards evaluated against rubric
- [ ] Events logged for every action taken
