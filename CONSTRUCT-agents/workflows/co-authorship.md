# Workflow: Co-Authorship

**Maps to:** User Journey J3 (Co-authorship Session)
**Duration:** Single session or multi-session (iterative)
**Purpose:** Produce a high-quality written output from accumulated knowledge, with full epistemic transparency.

---

## Overview

```
gap-analysis → [optional: research-cycle] → synthesis → [iterate with user] → finalize
```

---

## Steps

### 1. Define the Output

Have a conversation with the user to clarify:

- **What** are we writing? (briefing paper, essay, annotated bibliography, summary, report)
- **For whom?** (expert audience, general, personal notes)
- **About what?** (specific topic, domain-wide, cross-domain)
- **How long?** (executive brief, standard paper, comprehensive report)
- **What quality bar?** (include speculative content? Minimum confidence floor?)

### 2. Assess Readiness
**Skill:** `gap-analysis` (scoped to the topic)

Before drafting, assess whether the knowledge graph can support this output:

```
Topic: {topic}
Relevant cards: {N}
Confidence distribution: {breakdown}
Source tier distribution: {breakdown}
Coverage: {which sub-topics are strong/weak}
```

Present honestly:
> "For a briefing on {topic}, I have {N} cards at confidence 3+, and {N} at confidence 1–2. The section on {sub-topic} is well-supported. The section on {other-sub-topic} is thin — only {N} speculative cards.
>
> Options:
> 1. Draft now — I'll flag thin sections explicitly
> 2. Research first — I'll run a targeted cycle on weak areas, then draft
> 3. Narrow scope — focus on the strong areas"

### 3. Fill Gaps (Optional)
**Skill:** `research-cycle` (targeted)

If user chooses to research first:
- Create temporary search clusters focused on weak areas
- Run research cycle
- Curate new material
- Re-assess readiness

### 4. Draft
**Skill:** `synthesis`

Produce the draft:
- Outline first → user approves
- Draft with inline card references
- Confidence-calibrated language
- Explicit gap flags
- Source table

### 5. Iterative Review

The user reviews and may:

| Feedback | Action |
|----------|--------|
| "This section is thin" | Run targeted research, then revise |
| "This is wrong / outdated" | Check underlying cards, update if needed, revise |
| "Expand this" | Pull in more cards, add depth |
| "Cut this" | Remove section, simplify |
| "Connect this to {other topic}" | Check for cross-domain bridges, incorporate |
| "Change the tone" | Adjust register (academic, casual, narrative) |

Each iteration:
1. Apply changes
2. Update the draft in `publish/`
3. Present diff summary to user

### 6. Finalize

When user approves:
1. Update draft frontmatter: `status: final`
2. Add `finalized_date`
3. Log `publish_artifact` event
4. Present final:

> "Published: publish/{filename}.md
> - {N} source cards referenced
> - Average confidence of sources: {N.N}
> - Domains covered: {list}
> - Sections by strength: {N} STRONG, {N} EMERGING, {N} THIN"

---

## Quality Principles

1. **Never invent knowledge.** Every claim traces to a card. If the graph doesn't know it, say so.
2. **Confidence propagates.** A paragraph built from confidence-2 cards gets hedged language.
3. **Gaps are features, not bugs.** Flagging "we don't know this yet" is more valuable than hand-waving.
4. **Cross-domain insights are highlighted.** When a draft connects concepts from different domains, call it out — that's the system's differentiator.
5. **The user has final editorial control.** CONSTRUCT proposes; the human decides.

---

## Multi-Session Support

If the draft isn't finished in one session:
- The draft persists in `publish/` with `status: draft`
- On return, CONSTRUCT reads the draft and picks up where you left off
- Any new cards ingested between sessions may strengthen weak sections — check and offer updates
