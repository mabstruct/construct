---
description: "Edit a knowledge card's content or metadata. Use when user says 'edit card', 'update confidence', 'change the type of card', or similar."
allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *), Bash(construct knowledge *)
---

> **Updated for Phase 2:** File operations now delegate to `construct knowledge` CLI. The skill drives the conversation; Python enforces contracts.

# Skill: Edit Knowledge Card

**Trigger:** User says "edit card {name}", "update {card}'s confidence", "change the type of {card}", or similar.
**Agent:** CONSTRUCT or Curator
**Produces:** Updated card file, event log entry

---

## Procedure

### Step 1: Identify the Card

Find the card to edit:
1. If user provides card ID → look for `cards/{id}.md`
2. If user provides title → search `cards/*.md` for matching title
3. If ambiguous → list candidates and ask user to pick

Read and display the card's current state.

### Step 2: Determine Changes

Parse what the user wants to change:

| Change type | Field affected | Validation |
|------------|---------------|-----------|
| Confidence | `confidence` | Integer 1–5 |
| Source tier | `source_tier` | Integer 1–5 |
| Epistemic type | `epistemic_type` | Valid enum (see `.construct/references/epistemic-types.md`) |
| Lifecycle | `lifecycle` | Valid enum: seed / growing / mature / archived |
| Domain | `domains` | Must exist in `domains.yaml` |
| Categories | `content_categories` | Must exist in domain's taxonomy |
| Title | `title` | Non-empty string |
| Tags | `tags` | kebab-case list |
| Sources | `sources` | Valid source entries |
| Body content | Markdown body | Non-empty `## Summary` |
| Verification | `last_verified` | Set to today's date |

If the user describes changes in natural language, map to specific fields.

### Step 3: Validate Changes

Before applying:
- Confidence must be 1–5
- Source tier must be 1–5
- Epistemic type must be valid enum
- Domain references must exist in `domains.yaml`
- Category references must exist in the domain's `content_categories`
- If changing lifecycle, check governance rules:
  - Promoting? Check if promotion conditions are met (or explicitly overridden)
  - Archiving? Check if any cards depend on this one

### Step 4: Call Python CLI to Edit Card

Apply changes via the Python CLI. Only include flags for fields the user wants to change:

```bash
construct knowledge card edit "$CARD_ID" \
  --title "$TITLE" \
  --confidence "$CONFIDENCE" \
  --lifecycle "$LIFECYCLE" \
  --author "curator" \
  --json
```

**If the CLI succeeds:** Card is updated. Parse JSON output for confirmation.
**If the CLI fails:** Display structured error (field, reason, suggestion), offer retry.

### Step 5: Update Related State

If confidence or source_tier changed:
- Check if this triggers promotion eligibility
- Inform user if card now qualifies for lifecycle change

If lifecycle changed to archived:
- Note that connections are preserved (archive doesn't remove connections)

### Step 6: Event Logging

The CLI automatically logs the `edit_card` event. No manual log entry needed.

### Step 7: Confirm

> "Updated '{card-title}': {field} changed from {old} to {new}."

---

## Validation

- [ ] CLI returned success with valid JSON output
- [ ] All modified fields are valid per schema
- [ ] Domain and category references exist
- [ ] Card file is valid YAML + markdown after edit
