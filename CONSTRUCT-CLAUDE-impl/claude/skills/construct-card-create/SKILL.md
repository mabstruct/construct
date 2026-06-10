---
description: "Create a knowledge card from user input, URL, or research finding. Use when user says 'add a card', 'capture this', 'note this finding', or pastes a URL/paper."
allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *), Bash(construct knowledge *)
---

> **Updated for Phase 2:** File operations now delegate to `construct knowledge` CLI. The skill drives the conversation; Python enforces contracts.

# Skill: Create Knowledge Card

**Trigger:** User says "add a card", "capture this", "note this finding", pastes a URL/paper, or similar.
**Agent:** CONSTRUCT or Researcher (for research-ingested cards)
**Produces:** New card file in `cards/`, optional connection in `connections.json`, event log entry

---

## Procedure

### Step 1: Determine Source

| User provides | Action |
|--------------|--------|
| A URL or paper reference | Fetch/search for details, extract key findings |
| A concept or idea | Capture directly from conversation |
| A finding from research cycle | Already structured — format into card |

### Step 2: Draft Card Content

Gather or determine:
- **title** — concise, descriptive
- **epistemic_type** — classify using `.construct/references/epistemic-types.md`
- **confidence** — using `.construct/references/confidence-levels.md`
- **source_tier** — using `.construct/references/source-tiers.md`
- **domains** — which domain(s) this belongs to (must exist in `domains.yaml`)
- **content_categories** — from the domain's taxonomy
- **summary** — 1–3 paragraphs: what is this and why it matters

If user provides enough context, draft without asking. If ambiguous, ask only what's missing.

### Step 3: Generate Card ID

- Convert title to kebab-case
- Truncate to reasonable length (max ~60 chars)
- Check uniqueness against existing `cards/` filenames
- Example: "Successor Representation for Spatial Reasoning" → `successor-representation-spatial`

### Step 4: Call Python CLI to Create Card

After drafting the card content, invoke the Python CLI:

```bash
construct knowledge card create \
  --title "$TITLE" \
  --type "$EPISTEMIC_TYPE" \
  --domains "$DOMAINS" \
  --confidence "$CONFIDENCE" \
  --source-tier "$SOURCE_TIER" \
  --categories "$CATEGORIES" \
  --summary "$SUMMARY" \
  --author "construct" \
  --json
```

**If the CLI succeeds:** Parse JSON output. The card file is already written.
**If the CLI fails:** Parse JSON error output. Display structured errors to the user:
> "The card couldn't be created: {field}: {reason}. {suggestion}"
Offer the user a chance to fix.

### Step 5: Suggest Connections

Scan existing cards for potential connections:
- Same domain + related content categories
- Similar titles or topics
- Contradicting or supporting findings

If connections found, propose them:
> "This card might connect to '{other-card-title}'. Relation: {type}. Add this connection?"

If user confirms, add the connection via CLI:
```bash
construct knowledge connection add "$CARD_ID" "$OTHER_ID" --type "$TYPE" --json
```

### Step 6: Event Logging

The CLI automatically logs the `create_card` event. No manual log entry needed.

### Step 7: Views Refresh Hook (Direct Invocation Only)

If this skill was invoked directly by the user (not as part of `research-cycle`, `daily-cycle`, or another parent skill that owns views refresh):

1. If `views/build/` exists at the install root AND `.construct/config.yaml` does not set `views.auto_regenerate: false` AND `.construct/config.yaml` does not set `views.per_card_hooks.enabled: false`:
   - Run:
     ```bash
     bash <install-root>/.claude/skills/views-generate-data/debounced-hook.sh <install-root> card-create
     ```
   - If it succeeds and prints a line, append that line to the report. This only happens when `views.confirm_refresh: true`, and the message is:
     > Note: views refresh scheduled (5s trailing debounce).
   - If it fails, append a warning to the report:
     > ⚠ views refresh scheduling failed: {single-line message}. Card creation still succeeded; run `views-generate-data` manually if needed.
2. Otherwise → skip silently.

### Step 8: Confirm

> "Card '{title}' created as {lifecycle} ({epistemic_type}, confidence {N}). {connection_info}"

---

## Validation

- [ ] CLI returned success with valid JSON output
- [ ] Card ID is unique
- [ ] All required YAML fields present
- [ ] Domain exists in `domains.yaml`
- [ ] Content categories exist in domain definition
- [ ] Confidence is 1–5 integer
- [ ] Source tier is 1–5 integer
- [ ] Epistemic type is valid enum
- [ ] `## Summary` section is non-empty
