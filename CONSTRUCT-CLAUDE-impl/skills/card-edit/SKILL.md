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

### Step 4: Apply Changes

Update the card's YAML frontmatter and/or markdown body.

If changing the card ID (rare):
1. Rename the file
2. Update all references in `connections.json`
3. Update any cards with `connects_to` pointing to old ID

### Step 5: Update Related State

If confidence or source_tier changed:
- Check if this triggers promotion eligibility
- Inform user if card now qualifies for lifecycle change

If lifecycle changed to archived:
- Check for orphaned connections in `connections.json`
- Flag connections that now point to an archived card

### Step 6: Log Event

```json
{"ts": "{ISO-8601}", "agent": "{who}", "action": "edit_card", "target": "{card-id}", "detail": "{field}: {old} → {new}", "result": "success"}
```

### Step 7: Confirm

> "Updated '{card-title}': {field} changed from {old} to {new}."

---

## Validation

- [ ] All modified fields are valid per schema
- [ ] Domain and category references exist
- [ ] Card file is valid YAML + markdown after edit
- [ ] connections.json references updated if ID changed
- [ ] Event logged
