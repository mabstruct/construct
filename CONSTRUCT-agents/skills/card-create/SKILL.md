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
- **epistemic_type** — classify using `references/epistemic-types.md`
- **confidence** — using `references/confidence-levels.md`
- **source_tier** — using `references/source-tiers.md`
- **domains** — which domain(s) this belongs to (must exist in `domains.yaml`)
- **content_categories** — from the domain's taxonomy
- **summary** — 1–3 paragraphs: what is this and why it matters

If user provides enough context, draft without asking. If ambiguous, ask only what's missing.

### Step 3: Generate Card ID

- Convert title to kebab-case
- Truncate to reasonable length (max ~60 chars)
- Check uniqueness against existing `cards/` filenames
- Example: "Successor Representation for Spatial Reasoning" → `successor-representation-spatial`

### Step 4: Write Card File

Create `cards/{id}.md` using the card template:

```yaml
---
id: {id}
title: "{title}"
epistemic_type: {type}
created: {today}
confidence: {1-5}
source_tier: {1-5}
domains:
  - {domain-id}
content_categories:
  - {category}
lifecycle: seed
sources:
  - type: {paper|url|observation|conversation}
    ref: "{reference}"
    title: "{source title}"
author: {construct|researcher|human}
---

## Summary

{1-3 paragraphs}

## Evidence

{citations, data points — optional for seeds}

## Significance

{why this matters — optional for seeds}

## Open Questions

{what's unresolved — optional}
```

### Step 5: Suggest Connections

Scan existing cards for potential connections:
- Same domain + related content categories
- Similar titles or topics
- Contradicting or supporting findings

If connections found, propose them:
> "This card might connect to '{other-card-title}'. Relation: {type}. Add this connection?"

If user confirms, update `connections.json`.

### Step 6: Log Event

Append to `log/events.jsonl`:
```json
{"event": "create_card", "timestamp": "{ISO-8601}", "card_id": "{id}", "epistemic_type": "{type}", "confidence": {N}, "author": "{who}"}
```

### Step 7: Confirm

> "Card '{title}' created as {lifecycle} ({epistemic_type}, confidence {N}). {connection_info}"

---

## Validation

- [ ] Card ID is unique
- [ ] All required YAML fields present
- [ ] Domain exists in `domains.yaml`
- [ ] Content categories exist in domain definition
- [ ] Confidence is 1–5 integer
- [ ] Source tier is 1–5 integer
- [ ] Epistemic type is valid enum
- [ ] `## Summary` section is non-empty
