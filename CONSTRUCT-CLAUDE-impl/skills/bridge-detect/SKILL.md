# Skill: Cross-Domain Bridge Detection

**Trigger:** User says "find connections across domains", "bridge detection", "cross-domain patterns", or during curation cycle Step 5.
**Agent:** Curator (detection) → CONSTRUCT (assessment of genuine parallels)
**Produces:** Bridge candidates with proposed connections, machine-readable `log/bridge-candidates.json`, event log entries

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

Normalize each candidate into a structured record with:

- `source_card_id`
- `target_card_id`
- `target_workspace_id`
- `proposed_relation`
- `candidate_strength` (`strong` or `possible`)
- `signals.l1_structural`
- `signals.l2_shared_categories[]`
- `signals.l3_reasoning`

Only include candidates that involve cards from different domains/workspaces.

### Step 5: Persist Machine-Readable Candidate Set

Before presenting results to the user, write the latest derived candidate set to:

- `<workspace>/log/bridge-candidates.json`

This file is a **derived artifact**, not canonical knowledge. It must always be safe to delete and regenerate.

Write the full latest set, replacing any prior file for this workspace.

Minimum file shape:

```json
{
  "generated_at": "2026-05-10T10:30:00Z",
  "workspace_id": "cosmology",
  "candidates": [
    {
      "source_card_id": "observer-effects",
      "target_card_id": "self-model-observer-loop",
      "target_workspace_id": "philosophy-of-mind",
      "proposed_relation": "parallels",
      "candidate_strength": "strong",
      "signals": {
        "l1_structural": true,
        "l2_shared_categories": ["observer-models", "inference"],
        "l3_reasoning": "Both cards model an observer-dependent update loop rather than a passive measurement event."
      }
    }
  ]
}
```

Persistence rules:

1. If no candidates survive assessment, still write the file with an empty `candidates` array.
2. `workspace_id` is the workspace from which `bridge-detect` was invoked.
3. `target_workspace_id` points to the other endpoint's workspace.
4. Use only `strong` and `possible` for `candidate_strength` in this first cut.
5. Do not include already confirmed bridges in `candidates`; those remain canonical in `connections.json` and can still be listed separately for the user.

### Step 6: Propose Connections

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

When you present the report, mention that the candidate set was also saved to `log/bridge-candidates.json` for views/data generation.

### Step 7: Apply Confirmed Bridges

For each confirmed bridge:
1. Add edge to `connections.json`
2. Log `detect_bridge` event
3. Optionally: create a `connection`-type card documenting the parallel

### Step 8: Report

> "Bridge detection complete: {N} strong candidates, {N} possible. {N} new connections added. Candidate set saved to `log/bridge-candidates.json`."

---

## Validation

- [ ] All proposed bridges involve cards from different domains
- [ ] No duplicate edges proposed
- [ ] Connection types are valid
- [ ] Bridge reasoning is specific, not generic
- [ ] `log/bridge-candidates.json` is written on every run, even when `candidates` is empty
- [ ] `log/bridge-candidates.json` contains only cross-domain candidates and uses the required fields
