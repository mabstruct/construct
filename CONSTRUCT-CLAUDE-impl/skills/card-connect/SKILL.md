# Skill: Manage Connections

**Trigger:** User says "connect {A} to {B}", "remove connection", "what's connected to {card}", or similar.
**Agent:** Curator or CONSTRUCT
**Produces:** Updated `connections.json`, event log entry

---

## Procedure

### Step 1: Determine Operation

| User says | Operation |
|-----------|----------|
| "Connect A to B" | Add connection |
| "Remove connection between A and B" | Remove connection |
| "What's connected to A?" | List connections |
| "Type the connection between A and B" | Type/retype existing edge |

### Step 2: For ADD — Identify Cards

1. Resolve both card references (ID or title search)
2. Verify both cards exist in `cards/`
3. Check if a connection already exists between them in `connections.json`
   - If same-type edge exists → inform user, skip
   - If different-type edge exists → ask if adding second relation

### Step 3: For ADD — Determine Relation Type

If user specified a type → validate against `.construct/references/connection-types.md`.

If not specified → propose a type:
1. Read both cards' summaries
2. Assess the relationship using the decision flow from `.construct/references/connection-types.md`
3. Propose:
   > "I'd suggest '{relation}': {reasoning}. Confirm, or specify a different type?"

### Step 4: For ADD — Write Connection

Add to `connections.json`:
```json
{
  "from": "{card-a-id}",
  "to": "{card-b-id}",
  "type": "{relation}",
  "note": "{optional note from user or generated}",
  "created": "{today}",
  "created_by": "{curator|human}"
}
```

Increment `connections.json` `version`.

Optionally update the source card's `connects_to` frontmatter for portability.

### Step 5: For REMOVE — Delete Connection

1. Find the matching edge in `connections.json`
2. Remove it
3. Increment version
4. Update the card's `connects_to` frontmatter if it was listed there

### Step 6: For LIST — Show Connections

Read `connections.json` and filter for edges involving the specified card:

```
Connections for '{card-title}':

  → extends: '{other-card-title}'
    Note: "builds on the framework"

  ← supports: '{another-card-title}'
    Note: "provides evidence for this claim"

  ↔ contradicts: '{conflicting-card-title}'
    Note: "disagrees on the mechanism"
```

Show direction (→ outgoing, ← incoming, ↔ symmetric).

### Step 7: For TYPE — Assign Relation

1. Find the existing edge
2. Read both cards' content
3. Propose a relation type with reasoning
4. On confirmation, update the edge's `type` field
5. Increment version

### Step 8: Log Event

For add:
```json
{"ts": "{ISO-8601}", "agent": "{who}", "action": "add_connection", "target": "{from} → {to}", "detail": "type: {relation}", "result": "success"}
```

For remove:
```json
{"ts": "{ISO-8601}", "agent": "{who}", "action": "remove_connection", "target": "{from} → {to}", "detail": "type: {relation}", "result": "success"}
```

For type:
```json
{"ts": "{ISO-8601}", "agent": "{who}", "action": "type_connection", "target": "{from} → {to}", "detail": "type: {relation}", "result": "success"}
```

---

## Validation

- [ ] `connections.json` is valid JSON after modification
- [ ] No duplicate edges (same from + to + type)
- [ ] All card references exist as files
- [ ] Relation type is valid enum
- [ ] Version incremented
- [ ] Event logged
