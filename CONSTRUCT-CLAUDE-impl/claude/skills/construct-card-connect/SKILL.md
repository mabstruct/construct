---
description: "Create, remove, or query typed connections between cards. Use when user says 'connect A to B', 'remove connection', 'what's connected to card', or similar."
allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *), Bash(construct knowledge *)
---

> **Updated for Phase 2:** File operations now delegate to `construct knowledge` CLI. The skill drives the conversation; Python enforces contracts.

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

### Step 4: For ADD — Call Python CLI

Add the connection via CLI:

```bash
construct knowledge connection add "$FROM" "$TO" --type "$TYPE" --note "$NOTE" --json
```

**If the CLI succeeds:** Connection is created.
**If the CLI fails:** Display structured error, offer retry.

### Step 5: For REMOVE — Call Python CLI

Remove a connection via CLI:

```bash
construct knowledge connection remove "$FROM" "$TO" --type "$TYPE"
```

### Step 6: For LIST — Call Python CLI

List connections via CLI:

```bash
construct knowledge connection list --card "$CARD_ID" --json
```

Format the output for the user:
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

1. Find the existing edge via CLI: `construct knowledge connection list --card "$CARD_ID" --json`
2. Read both cards' content
3. Propose a relation type with reasoning
4. On confirmation, remove the old edge and add the new: `construct knowledge connection remove` then `construct knowledge connection add`

### Step 8: Event Logging

The CLI automatically logs connection events. No manual log entry needed.

### Step 9: Views Refresh Hook (Direct Invocation Only)

If this skill was invoked directly by the user (not as part of `curation-cycle`, `daily-cycle`, or another parent skill that owns views refresh):

1. If `views/build/` exists at the install root AND `.construct/config.yaml` does not set `views.auto_regenerate: false` AND `.construct/config.yaml` does not set `views.per_card_hooks.enabled: false`:
   - Run:
     ```bash
     bash <install-root>/.claude/skills/views-generate-data/debounced-hook.sh <install-root> card-connect
     ```
   - If it succeeds and prints a line, append that line to the report. This only happens when `views.confirm_refresh: true`, and the message is:
     > Note: views refresh scheduled (5s trailing debounce).
   - If it fails, append a warning to the report:
     > ⚠ views refresh scheduling failed: {single-line message}. Connection update still succeeded; run `views-generate-data` manually if needed.
2. Otherwise → skip silently.

---

## Validation

- [ ] CLI returned success with valid JSON output
- [ ] `connections.json` is valid JSON after modification
- [ ] No duplicate edges (same from + to + type)
- [ ] All card references exist as files
- [ ] Relation type is valid enum
