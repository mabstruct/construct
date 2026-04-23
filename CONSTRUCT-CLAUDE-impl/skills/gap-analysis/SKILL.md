# Skill: Gap Analysis

**Trigger:** User says "what gaps do you see?", "what's missing?", "gap analysis", "find holes", or similar.
**Agent:** CONSTRUCT (orchestrator — requires cross-domain reasoning)
**Produces:** Gap report with actionable recommendations

---

## Procedure

### Step 1: Load Graph State

Read:
- All `cards/*.md` files (frontmatter + summary sections)
- `connections.json` — the edge list
- `domains.yaml` — domain definitions with content categories
- `governance.yaml` — quality thresholds

### Step 2: Coverage Analysis

For each active domain:

**Category coverage:**
- List all `content_categories` from `domains.yaml`
- Count cards per category
- Identify categories with zero or very few cards (< 3)
- These are **category gaps**

**Confidence distribution:**
- Count cards by confidence level per domain
- A domain dominated by confidence 1–2 cards has a **depth gap**
- Categories with only low-confidence cards are particularly weak

**Connection density:**
- Average connections per card
- Categories with below-average connection density are **integration gaps**
- Cards that are mature but poorly connected may be islands

### Step 3: Structural Gap Detection

**Missing cross-domain links:**
- Domains listed in `cross_domain_links` in domains.yaml → check if actual connections exist
- Expected overlaps with no edges are **bridge gaps**

**Epistemic type gaps:**
- Count cards by `epistemic_type` per domain
- Domains with many `finding` cards but no `theme` cards → synthesis gap
- Domains with no `gap` or `question` cards → self-awareness gap
- Domains with no `method` cards → procedural knowledge gap

**Source diversity:**
- Count cards by `source_tier` per domain
- Domains relying entirely on tier 3+ sources → **evidence gap**

### Step 4: Temporal Gaps

- Identify domains or categories where newest card is old (> 30 days)
- These may indicate **stale areas** where research has stopped

### Step 5: Synthesize Findings

Produce a structured gap report:

```markdown
## Knowledge Gap Analysis — {date}

### Critical Gaps (action recommended)
1. **{domain}: {category}** — {gap type}
   Cards: {N}, Avg confidence: {N.N}
   Recommendation: {what to do}

### Moderate Gaps (worth addressing)
...

### Observations
- {cross-domain insights}
- {overall system maturity assessment}

### Suggested Actions
1. Research: {specific search queries to fill gaps}
2. Promote: {cards that could be promoted to close depth gaps}
3. Connect: {cards that should probably be linked}
4. Create: {card types that are missing — gap cards, theme cards, etc.}
```

### Step 6: Offer Follow-up

> "I found {N} gaps. Would you like me to:
> - Research the most critical ones? (I'll run targeted search cycles)
> - Create gap cards to track them? (Marks them as known unknowns)
> - Adjust search patterns to prioritize coverage? (I'll update search-seeds.json)"

---

## Validation

- [ ] All domains analyzed
- [ ] Gap classifications are specific and actionable
- [ ] Recommendations reference concrete cards or categories
- [ ] No false positives (a domain with 2 cards is too young, not gapped)
