# Skill: Cross-Domain Bridge Detection

**Trigger:** User says "find connections across domains", "bridge detection", "cross-domain patterns", or during curation cycle Step 5.
**Agent:** Curator (detection) → CONSTRUCT (assessment of genuine parallels)
**Produces:** Bridge candidates with proposed connections, event log entries

---

## Procedure

### Step 1: Level 1 — Graph Structural Bridges

Scan `connections.json` for cards that connect to cards in different domains:

1. For each connection, check if `from` card and `to` card belong to different domains
2. Cards that appear in cross-domain edges are **structural bridge nodes**
3. Cards connected to 2+ other domains are **hub bridges**

Output:
```
L1 Bridges (structural):
- {card-id} connects {domain-A} ↔ {domain-B} via "{connection-type}"
```

### Step 2: Level 2 — Category Overlap

Scan all cards for shared `content_categories` across different domains:

1. Build a map: category → list of (card-id, domain) pairs
2. Categories that appear in 2+ domains indicate potential parallels
3. Cards sharing categories across domains are **semantic bridge candidates**

Output:
```
L2 Bridges (category overlap):
- Category "{category}" appears in {domain-A} and {domain-B}
  Cards: {card-A} ({domain-A}), {card-B} ({domain-B})
```

### Step 3: Level 3 — Content Similarity

For domains with known `cross_domain_links` in `domains.yaml`:

1. Read the specified overlap topics
2. Search for cards in each linked domain that address those topics
3. Assess whether the content suggests a genuine structural parallel

This requires reading card content, not just metadata.

### Step 4: Assess Candidates

For each bridge candidate, evaluate:

| Factor | Question |
|--------|----------|
| **Genuine parallel?** | Do these cards share real structural similarity, or is it just keyword coincidence? |
| **Connection type** | What relation fits? Usually `parallels`, but could be `extends` or `enables` |
| **Strength** | Is this a strong insight or a superficial link? |
| **Novelty** | Is this connection already captured, or is it new? |

### Step 5: Propose Connections

Present bridge candidates to the user:

```markdown
## Cross-Domain Bridge Candidates

### Strong Candidates
1. **{card-A}** ({domain-A}) ↔ **{card-B}** ({domain-B})
   Proposed relation: parallels
   Reasoning: {why this connection is genuine}

### Possible Candidates
2. ...

### Already Connected
- {card-X} ↔ {card-Y} — edge already exists
```

Ask: "Would you like me to create these connections?"

### Step 6: Apply Confirmed Bridges

For each confirmed bridge:
1. Add edge to `connections.json`
2. Log `detect_bridge` event
3. Optionally: create a `connection`-type card documenting the parallel

### Step 7: Report

> "Bridge detection complete: {N} strong candidates, {N} possible. {N} new connections added."

---

## Validation

- [ ] All proposed bridges involve cards from different domains
- [ ] No duplicate edges proposed
- [ ] Connection types are valid
- [ ] Bridge reasoning is specific, not generic
