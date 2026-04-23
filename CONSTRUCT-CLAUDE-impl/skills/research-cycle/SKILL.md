# Skill: Research Cycle

**Trigger:** User says "research", "find papers", "what's new in {domain}", "run a research cycle", or similar.
**Agent:** Researcher
**Produces:** New ref files, seed cards, cycle digest, event log entries

---

## Procedure

### Step 1: Load Configuration

Read these workspace files:
- `search-seeds.json` — active search clusters
- `domains.yaml` — domain definitions and categories
- `governance.yaml` — research thresholds (relevance_threshold, card_creation_threshold, max_papers_per_cycle)

If no active clusters exist, tell the user:
> "No search patterns configured. Run domain init first to seed your research."

### Step 2: Select Search Scope

Determine scope:
- **Full cycle:** All active clusters across all active domains
- **Domain-specific:** User specified a domain → filter clusters to that domain
- **Targeted:** User gave a specific topic → create ad-hoc search queries

### Step 3: Generate & Execute Searches

For each active cluster (prioritized by weight):

1. Formulate search queries from cluster terms
   - Combine terms into effective search strings
   - Add recent date constraints if `last_queried` is set
   - Higher-weight clusters → more query variations (2–4 queries)

2. Execute web searches
   - Use web search for each query
   - Collect: title, authors, year, venue, URL, abstract/summary
   - Target academic papers, preprints, technical reports, expert analysis

3. Track what was found
   - Keep running count against `max_papers_per_cycle`
   - Stop searching when limit reached

### Step 4: Deduplicate

For each result:
1. Check if URL exists in any `refs/*.json` file
2. Check if title closely matches an existing ref (fuzzy)
3. Check if title closely matches an existing card
4. **Skip known items** — log as `skip_duplicate`
5. **Keep novel items** — pass to extraction

### Step 5: Extract & Score

For each novel result:

1. **Extract key findings** (1–5 bullet points):
   - What did the paper/article find or argue?
   - What methods were used?
   - What are the implications?

2. **Score relevance** (0.0–1.0):
   - Read the domain description from `domains.yaml`
   - Assess: How directly does this advance the domain's core questions?
   - Use the rubric in `.construct/agents/researcher.md`

3. **Classify content categories**:
   - Map to the domain's `content_categories` from `domains.yaml`
   - A paper can map to multiple categories

4. **Apply thresholds**:
   - Below `relevance_threshold` (default 0.3): log `skip_low_relevance`, don't ingest
   - Between threshold and `card_creation_threshold` (default 0.6): create ref only, no card
   - Above card threshold: create ref AND draft seed card

### Step 6: Ingest

For each paper above relevance threshold:

**Write ref file** — `refs/{id}.json`:
```json
{
  "id": "{kebab-case-id}",
  "title": "{title}",
  "authors": ["{author1}", "{author2}"],
  "year": {year},
  "venue": "{venue}",
  "url": "{url}",
  "abstract": "{abstract or summary}",
  "relevance_score": {0.0-1.0},
  "key_findings": ["{finding1}", "{finding2}"],
  "content_categories": ["{cat1}", "{cat2}"],
  "source_tier": {1-5},
  "extraction_status": "complete",
  "ingested_date": "{today}"
}
```

**Draft seed card** (if relevance ≥ card_creation_threshold):
- Use `card-create` skill internally
- Set: `confidence: 1`, `lifecycle: seed`, `author: researcher`
- Set `epistemic_type` based on content (usually `finding` or `paper`)

### Step 7: Report

**Write cycle digest** — `digests/{domain}/digest-{date}.md`:

```markdown
# Research Digest — {Domain Name}
**Date:** {today}
**Clusters searched:** {list}

## Summary
- Papers found: {N}
- Papers ingested: {N} (refs created)
- Papers skipped: {N} (duplicates: {N}, low relevance: {N})
- Seed cards created: {N}

## Top Findings
1. **{title}** (relevance: {score}) — {key finding}
2. ...

## Search Clusters
| Cluster | Queries | Results | Ingested |
|---------|---------|---------|----------|
| {id} | {N} | {N} | {N} |

## Next Cycle Suggestions
- {observations about coverage gaps}
- {clusters that may need weight adjustment}
```

**Update search-seeds.json**: Set `last_queried` to now for each searched cluster.

**Log events**: `research_cycle_complete` with summary stats.

**Confirm to user**:
> "Research cycle complete for {domain}: {N} papers found, {N} ingested, {N} seed cards created. See digest: digests/{domain}/digest-{date}.md"

---

## Validation

- [ ] All ref files are valid JSON
- [ ] All seed cards pass schema validation
- [ ] No duplicate ref IDs
- [ ] Relevance scores are 0.0–1.0
- [ ] Source tiers are 1–5
- [ ] Digest written with accurate counts
- [ ] search-seeds.json updated with timestamps
