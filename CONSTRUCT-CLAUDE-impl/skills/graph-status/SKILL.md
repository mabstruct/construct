# Skill: Graph Status

**Trigger:** User says "graph status", "how's the graph?", "knowledge stats", "dashboard", or similar.
**Agent:** Curator (or CONSTRUCT for interpretation)
**Produces:** Natural language health summary

---

## Procedure

### Step 1: Gather Stats

Read workspace files and compute:

**Card counts:**
- Total cards (excluding archived)
- By lifecycle: seed / growing / mature / archived
- By epistemic type: finding / claim / concept / method / paper / theme / gap / provocation / question / connection
- By domain
- By confidence level (1–5 distribution)

**Connection counts:**
- Total edges in `connections.json`
- By type: supports / contradicts / extends / parallels / requires / enables / challenges / inspires / gap-for
- Average connections per card
- Max connected card (hub)
- Cards with zero connections (orphans)

**Domain health:**
- Cards per domain
- Average confidence per domain
- Category coverage per domain (categories with ≥1 card vs. total categories)

**Research activity:**
- Total refs in `refs/`
- Latest digest date per domain
- Active vs. paused search clusters in `search-seeds.json`

**Quality indicators:**
- Cards past decay window
- Orphan cards past tolerance
- Integrity issues (if recently checked)

### Step 2: Present Summary

Format as a readable dashboard:

```
## CONSTRUCT Knowledge Graph — Status

### Cards: {total}
| Lifecycle | Count |
|----------|-------|
| Seed     | {N}   |
| Growing  | {N}   |
| Mature   | {N}   |
| Archived | {N}   |

### Connections: {total}
- Average per card: {N.N}
- Most connected: "{card-title}" ({N} connections)
- Orphans: {N}

### Domains
| Domain | Cards | Avg Confidence | Category Coverage |
|--------|-------|---------------|------------------|
| {name} | {N}   | {N.N}         | {N}/{total} ({%}) |

### Quality
- Stale cards: {N}
- Orphan cards: {N}
- Confidence distribution: [1: {N}, 2: {N}, 3: {N}, 4: {N}, 5: {N}]

### Research
- Total references: {N}
- Last research cycle: {date}
- Active search clusters: {N}
```

### Step 3: Interpret (Optional)

If the user wants more than stats, add interpretation:

> **Assessment:** The graph is {young/growing/maturing}. {Domain} has strong coverage in {categories} but gaps in {categories}. {N}% of cards are still seeds — consider running a curation cycle to evaluate promotions. The orphan rate of {N}% suggests {interpretation}.

### Step 4: Suggest Actions

Based on findings:
- High orphan count → "Consider connecting orphan cards or archiving irrelevant ones"
- Many seeds → "Run `evaluate cards` to check for promotions"
- Low research activity → "Run a research cycle to bring in fresh material"
- Stale cards → "Run `curate` to flag and handle decayed cards"
- Coverage gaps → "Run `gap analysis` for a detailed gap report"

---

## Validation

- [ ] All counts are accurate against actual files
- [ ] No double-counting (archived cards separate from totals)
- [ ] Domain names match `domains.yaml`
- [ ] Percentages are calculated correctly
