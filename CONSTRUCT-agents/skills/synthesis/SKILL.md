# Skill: Synthesis / Drafting

**Trigger:** User says "draft a paper on...", "synthesize...", "write a briefing about...", "summarize the state of...", or similar.
**Agent:** CONSTRUCT (orchestrator — frontier reasoning required)
**Produces:** Draft document in `publish/`, drawing on graph state

---

## Procedure

### Step 1: Understand the Request

Clarify with the user if needed:
- **Topic:** What should the draft cover?
- **Format:** Briefing paper, essay, summary, report, annotated bibliography?
- **Audience:** Expert, general, internal notes?
- **Length:** Executive summary, short brief, or comprehensive?
- **Confidence floor:** Include speculative cards or only established knowledge? (default: confidence ≥ 2)

### Step 2: Gather Source Material

Query the knowledge graph for relevant cards:
1. Filter by domain(s) related to the topic
2. Filter by content categories that match
3. Filter by minimum confidence (from Step 1 or default ≥ 2)
4. Include connected cards (1-hop from directly relevant cards)
5. Sort by relevance to the specific topic

Read each relevant card's full content (summary, evidence, significance).

Also check `refs/` for supporting references.

### Step 3: Assess Knowledge Strength

Before drafting, audit the source material:

```
Source Material Assessment:
- Cards available: {N}
- Confidence distribution: {breakdown}
- Source tier distribution: {breakdown}
- Gaps identified: {list any weak areas}
```

If significant gaps exist, inform the user:
> "The knowledge base has limited coverage on {topic area} — only {N} cards at confidence {N}. The draft will flag these sections. Want me to research these gaps first?"

### Step 4: Create Outline

Produce a structured outline based on the gathered cards:

```markdown
## Proposed Outline

1. {Section} — based on {N} cards (avg confidence: {N})
2. {Section} — based on {N} cards (avg confidence: {N})
3. ...

Confidence indicators:
- Sections marked [STRONG] — well-supported (confidence 3+)
- Sections marked [EMERGING] — limited evidence (confidence 2)
- Sections marked [THIN] — speculative or underexplored
```

Get user approval on outline before drafting.

### Step 5: Draft

Write the draft following these rules:

1. **Cite source cards inline** — reference card IDs or titles
2. **Propagate confidence** — sections drawing from low-confidence cards should note this
3. **Flag gaps** — if a section needs more evidence, say so explicitly
4. **Use epistemic hedging** — match language certainty to confidence levels:
   - Confidence 5: "It is well established that..."
   - Confidence 4: "Strong evidence indicates..."
   - Confidence 3: "Evidence supports..."
   - Confidence 2: "Emerging research suggests..."
   - Confidence 1: "Speculatively, it may be that..."
5. **Cross-domain connections** — highlight when insights cross domain boundaries
6. **List sources** — end with references linking back to cards and refs

### Step 6: Write Output

Save draft to `publish/{slug}.md`:

```markdown
---
title: "{Title}"
type: {briefing|essay|summary|report}
date: {today}
domains: [{domain-ids}]
source_cards: [{card-ids used}]
confidence_floor: {N}
status: draft
---

# {Title}

{Draft content with inline card references}

---

## Sources

| Card | Type | Confidence | Connection |
|------|------|-----------|-----------|
| [{card-title}](../cards/{card-id}.md) | {type} | {N}/5 | {how it contributed} |
```

### Step 7: Review Prompt

Present the draft to the user:
> "Draft ready: publish/{slug}.md
> - Based on {N} cards across {N} domains
> - {N} sections marked STRONG, {N} EMERGING, {N} THIN
>
> Would you like to: review and edit, strengthen thin sections (I'll research), or finalize?"

---

## Validation

- [ ] Every claim in the draft traces to at least one source card
- [ ] Confidence propagation is accurate
- [ ] Gaps are explicitly flagged, not covered up
- [ ] Draft uses appropriate epistemic hedging
- [ ] Source table is complete
- [ ] File saved to `publish/` with valid frontmatter
