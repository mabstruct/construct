---
description: "Archive a knowledge card (set lifecycle to archived). Use when user says 'archive card', 'remove card', 'this card is outdated', or similar."
allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *), Bash(construct knowledge *)
---

> **Updated for Phase 2:** File operations now delegate to `construct knowledge` CLI. The skill drives the conversation; Python enforces contracts.

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

### Step 3: Call Python CLI to Archive Card

Archive the card via the Python CLI:

```bash
construct knowledge card archive "$CARD_ID" --author "curator" --json
```

The CLI updates lifecycle to archived and preserves all connections.

**If the CLI succeeds:** Card is archived. Parse JSON output for confirmation.
**If the CLI fails:** Display structured error and offer retry.

### Step 4: Handle Connections

Connections are preserved automatically by the CLI — they remain in `connections.json` as historical record. Graph views and queries filter archived card connections by default but can include them on request.

### Step 5: Event Logging

The CLI automatically logs the `archive_card` event. No manual log entry needed.

### Step 6: Confirm

> "Card '{title}' archived. {N} connections preserved. {supersedes info if applicable}"

---

## Validation

- [ ] CLI returned success with valid JSON output
- [ ] Card lifecycle is now "archived"
- [ ] connections.json is still valid JSON
- [ ] No new dangling references created
- [ ] Event logged by CLI
