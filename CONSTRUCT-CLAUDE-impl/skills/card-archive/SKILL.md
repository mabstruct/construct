# Skill: Archive Knowledge Card

**Trigger:** User says "archive card {name}", "remove {card}", "this card is outdated", or similar.
**Agent:** CONSTRUCT or Curator
**Produces:** Updated card file (lifecycle → archived), updated connections, event log entry

---

## Procedure

### Step 1: Identify the Card

Find the card:
1. If user provides card ID → look for `cards/{id}.md`
2. If user provides title → search for matching title
3. If ambiguous → list candidates

Read and display the card's current state.

### Step 2: Confirm Archival

Before archiving, check:

**Dependencies:**
- Does any other card reference this one in `connects_to`?
- Is this card referenced in any `connections.json` edges?
- Is this card cited in any `publish/` documents?

If dependencies exist, warn the user:
> "This card has {N} connections:
> - {card-B} ({relation})
> - {card-C} ({relation})
>
> Archiving will keep these connections but mark them as pointing to an archived card. Proceed?"

**Supersedes:**
Ask if another card supersedes this one:
> "Does a newer card replace this one? If so, provide the card ID and I'll set the `supersedes` field."

### Step 3: Archive the Card

Update the card's YAML frontmatter:
- Set `lifecycle: archived`
- Set `last_verified: {today}`
- If superseded, note the superseding card in `supersedes` field on the NEW card

### Step 4: Handle Connections

For each connection involving this card in `connections.json`:
- **Keep the connections** — they're historical record
- **Optionally add note:** "target archived on {date}"
- If user wants connections removed → remove them and decrement version

### Step 5: Log Event

```json
{"ts": "{ISO-8601}", "agent": "{who}", "action": "archive_card", "target": "{card-id}", "detail": "lifecycle → archived{, superseded by card-X}", "result": "success"}
```

### Step 6: Confirm

> "Card '{title}' archived. {N} connections preserved. {supersedes info if applicable}"

---

## Validation

- [ ] Card lifecycle is now "archived"
- [ ] connections.json is still valid JSON
- [ ] No new dangling references created
- [ ] Event logged
- [ ] If superseded, the new card's `supersedes` field is set
