---
description: "Run a research cycle — web search, extract findings, create seed cards. Use when user says 'research', 'find papers', 'what's new in domain', 'run a research cycle'."
allowed-tools: Read, Bash(construct), WebSearch, WebFetch, MCP(connect)
---

> **Updated for Phase 4:** Ref and seed card creation now delegates to `construct ingest` CLI. Web search and extraction remain LLM-driven. Each step documents its INPUT and OUTPUT.

# Skill: Research Cycle

**Trigger:** User says "research", "find papers", "what's new in {domain}", "run a research cycle", or similar.
**Agent:** Researcher
**Produces:** New ref files, seed cards, cycle digest, event log entries

---

## Procedure

### Step 1: Load Configuration

**INPUT:** Workspace files on disk
**OUTPUT:** Domain config, search seeds, governance thresholds loaded into agent context

Read these workspace files:
- `search-seeds.json` — active search clusters
- `domains.yaml` — domain definitions and categories
- `governance.yaml` — research thresholds (`relevance_threshold`, `card_creation_threshold`, `max_papers_per_cycle`)

If no active clusters exist, tell the user:
> "No search patterns configured. Run domain init first to seed your research."

### Step 2: Select Search Scope

**INPUT:** Domain config, user request
**OUTPUT:** Concrete scope decision (full cycle / domain-specific / targeted)

Determine scope:
- **Full cycle:** All active clusters across all active domains
- **Domain-specific:** User specified a domain → filter clusters to that domain
- **Targeted:** User gave a specific topic → create ad-hoc search queries

### Step 3: Execute Web Search

**INPUT:** Search scope, clusters from `search-seeds.json`, governance thresholds
**OUTPUT:** Raw search results (title, authors, year, venue, URL, abstract/summary)

For each active cluster (prioritized by weight):

1. Formulate search queries from cluster terms
   - Combine terms into effective search strings
   - Add recent date constraints if `last_queried` is set
   - Higher-weight clusters → more query variations (2–4 queries)

2. Execute web searches
   - Use `WebSearch` for each query
   - Collect: title, authors, year, venue, URL, abstract/summary
   - Target academic papers, preprints, technical reports, expert analysis

3. Track what was found
   - Keep running count against `max_papers_per_cycle`
   - Stop searching when limit reached

### Step 4: Extract Findings

**INPUT:** Raw search results, existing refs and cards
**OUTPUT:** Scored findings with relevance, dedup status, content categories

For each result:

1. **Deduplicate:**
   - Check if URL exists in any `refs/*.json` file
   - Check if title closely matches an existing ref (fuzzy)
   - Check if title closely matches an existing card
   - **Skip known items** — log as `skip_duplicate`
   - **Keep novel items** — pass to scoring

2. **Score relevance** (0.0–1.0):
   - Read the domain description from `domains.yaml`
   - Assess: How directly does this advance the domain's core questions?
   - Use the rubric in `.construct/agents/researcher.md`

3. **Extract key findings** (1–5 bullet points per result):
   - What did the paper/article find or argue?
   - What methods were used?
   - What are the implications?

4. **Classify content categories:**
   - Map to the domain's `content_categories` from `domains.yaml`
   - A paper can map to multiple categories

5. **Apply thresholds:**
   - Below `relevance_threshold` (default 0.3): log `skip_low_relevance`, don't ingest
   - Between threshold and `card_creation_threshold` (default 0.6): create ref only, no card
   - Above card threshold: create ref AND draft seed card

### Step 5: Ingest Findings

**INPUT:** Scored findings (from Step 4)
**OUTPUT:** New ref files, new seed cards, event log entries
**METHOD:** CLI `construct ingest source` (replaces inline file writes)

For each finding above the relevance threshold, run the ingestion pipeline via CLI:

**Pass the metadata you extracted in Step 4 via flags** — CONSTRUCT is agent-driven: extraction is your job, the CLI persists what you give it. If you omit the flags the ref falls back to conservative defaults (title = hostname, relevance 0.5, tier 5, no findings), which is the un-enriched stub you want to avoid.

For URL-based findings (papers, articles, web pages):
```bash
construct ingest source {finding_url} \
  --workspace . \
  --domain {domain} \
  --author researcher \
  --title "{finding_title}" \
  --relevance {relevance_score} \
  --tier {source_tier} \
  --year {year} --venue "{venue}" \
  --cluster {search_cluster} \
  --finding "{key_finding_1}" --finding "{key_finding_2}" \
  --category {content_category_1} --category {content_category_2}
```
Repeat `--finding` / `--category` once per item. Omit flags you genuinely don't have (e.g. `--year`/`--venue` for a non-paper). The `--title` flag also drives the `ref_id`, so distinct papers on the same host no longer collide.

For research-note findings (findings extracted from conversation or non-URL sources):
```bash
construct ingest source "research:{finding_title}: {finding_summary}" \
  --workspace . \
  --domain {domain} \
  --author researcher \
  --relevance {relevance_score} \
  --tier {source_tier} \
  --finding "{key_finding}" \
  --category {content_category}
```

The `construct ingest source` command handles:
- Source type detection (URL vs research note vs paper)
- Ref record creation, persisting the metadata you pass (title, year, venue, relevance score, source tier, key findings, content categories) — defaults applied for anything omitted
- Seed card creation, with your key findings written into the card's `## Summary` section and linked back to the ref
- Event logging to `log/events.jsonl`

**Benefits:** Consistent ref/card format, deterministic validation, traceable event log entries.

### Step 6: Compile Digest

**INPUT:** Ingestion results from Step 5, search cluster metadata
**OUTPUT:** Digest markdown file written to `digests/{domain}/`

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

### Step 7: Log Events

**INPUT:** Research cycle results (counts, stats, any errors)
**OUTPUT:** `log/events.jsonl` entries, user confirmation message

1. Log a `research_cycle_complete` event with summary stats to `log/events.jsonl`.
2. Confirm to user:

> "Research cycle complete for {domain}: {N} papers found, {N} ingested, {N} seed cards created. See digest: digests/{domain}/digest-{date}.md"

### Step 8: Views Refresh Hook

**INPUT:** Cycle completion, views config
**OUTPUT:** (Optional) views regeneration triggered

If `views/build/` exists at the install root AND `.construct/config.yaml` does not set `views.auto_regenerate: false`:

**Skip check:** If this skill was invoked as part of `daily-cycle` or another parent workflow that runs multiple hooked skills in sequence, skip this hook — the parent will trigger a single regeneration after all child skills complete. This avoids redundant regeneration (e.g., daily-cycle runs research-cycle → curation-cycle → both would fire hooks; only the last one matters since regen is full and idempotent).

If not skipped:
1. Run `views-generate-data` to refresh the SPA's cached JSON
2. If it succeeds → if `.construct/config.yaml` sets `views.confirm_refresh: true`, append to the report: `✓ views updated (build_id: {id})`. Otherwise, no extra user-facing message (the SPA picks it up via `version.json` polling within 30s).
3. If it fails → append a warning to the report:
   > ⚠ views regeneration failed: {single-line message}. Workspace is intact; run `views-generate-data` manually to refresh the views.
4. Always preserve this skill's success status — the hook is a side effect, not a success condition

If `views/build/` does not exist, or `views.auto_regenerate` is `false` → skip silently (no log, no message).

---

## Validation

- [ ] All ref files are valid JSON
- [ ] All seed cards pass schema validation
- [ ] No duplicate ref IDs
- [ ] Relevance scores are 0.0–1.0
- [ ] Source tiers are 1–5
- [ ] Digest written with accurate counts
- [ ] search-seeds.json updated with timestamps
- [ ] `construct ingest source` command succeeded for each finding
- [ ] Event log entries created
