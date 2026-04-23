# Skill: Evaluate Card for Promotion

**Trigger:** User says "evaluate cards", "check promotions", or during curation cycle Step 4.
**Agent:** Curator
**Produces:** Card lifecycle updates, event log entries

---

## Procedure

### Step 1: Load Governance Rules

Read `governance.yaml` promotion thresholds:
- `seed_to_growing_confidence` (default: 2)
- `seed_to_growing_min_connections` (default: 1)
- `growing_to_mature_confidence` (default: 3)
- `growing_to_mature_source_tier` (default: 2)
- `growing_to_mature_min_connections` (default: 2)
- `require_human_approval` (default: false)

### Step 2: Scan Cards

Read all `cards/*.md` files. For each card, extract frontmatter and count connections from `connections.json`.

### Step 3: Apply Promotion Rules

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

For cards that meet ALL criteria:
- If `require_human_approval: false` → promote directly (update frontmatter)
- If `require_human_approval: true` → flag for review, list to user

### Step 5: Handle Ambiguous Cards

For cards that meet SOME but not all criteria, evaluate:

1. Read the card's full content (summary, evidence, significance)
2. Assess:
   - Is the content quality sufficient despite missing a threshold?
   - Is the source reliable enough?
   - Are existing connections meaningful?
3. Decide: `promote` | `hold` | `escalate`

**Promote:** Quality justifies overriding a missing threshold. Update frontmatter.
**Hold:** Not ready. Note why in response.
**Escalate:** Needs human judgment. Present the card's case to the user.

### Step 6: Update Cards

For each promoted card:
1. Update `lifecycle` field in the card's YAML frontmatter
2. Update `last_verified` to today's date
3. Log event

### Step 7: Report

Summarize:
> "Promotion scan complete:
> - {N} cards promoted (seed → growing: {N}, growing → mature: {N})
> - {N} cards held (not ready)
> - {N} cards need your review: {list}"

### Step 8: Log Events

For each action, append to `log/events.jsonl`:
```json
{"event": "promote_card", "timestamp": "{ISO-8601}", "card_id": "{id}", "from": "seed", "to": "growing", "method": "rule-based|judgment"}
```

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
