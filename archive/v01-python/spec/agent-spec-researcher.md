# Researcher Agent — Specification

**Version:** 0.1.0
**Date:** 2026-04-21
**Status:** Draft — v0.1 scope
**Role:** Automated knowledge acquisition from external sources

---

## 1. Identity

The Researcher is CONSTRUCT's external knowledge acquisition agent. It runs automated search cycles, fetches papers and articles from APIs, extracts structured findings, and delivers them to the Curator for evaluation. It does not make judgment calls about knowledge quality — it finds, extracts, and hands off.

**LLM tier:** Lightweight (Ollama) for extraction/formatting. Workhorse for relevance scoring.

**Runs autonomously:** Yes — on configured cadence (default: hourly). Reports findings for Curator review.

---

## 2. Responsibilities

| Responsibility | Mechanism | LLM tier |
|---------------|-----------|----------|
| Execute search cycles | API queries from search-seeds.json | None (HTTP calls) |
| Fetch paper metadata | Semantic Scholar, arXiv APIs | None (HTTP calls) |
| Deduplicate against existing refs | SQLite/FTS5 query (URL, title match) | None (free) |
| Extract key findings from abstracts | LLM summarization of abstract + metadata | Lightweight |
| Score relevance to domain | LLM assessment: does this paper matter? | Workhorse |
| Draft seed cards from findings | LLM structuring: finding → card YAML + body | Lightweight |
| Write structured ref files | Populate `refs/{id}.json` (full schema) | None (code) |
| Update landscape snapshot | Aggregate research stats per domain | None (code) |
| Report cycle results | Write digest, log events | None (code) |
| Escalate anomalies to CONSTRUCT | Unexpected findings, API failures | None (event) |

---

## 3. The Research Cycle

One complete research cycle consists of 7 steps. Each step is logged individually in `events.jsonl`.

### 3.1 Cycle Overview

```
Step 1: Load Seeds
  │  Read search-seeds.json → active clusters
  ▼
Step 2: Generate Queries
  │  Expand seed clusters into API-specific query strings
  ▼
Step 3: Fetch
  │  Call APIs (Semantic Scholar, arXiv) → raw results
  ▼
Step 4: Deduplicate
  │  Check each result against refs index → skip known
  ▼
Step 5: Extract & Score
  │  LLM: extract findings, score relevance → enriched refs
  ▼
Step 6: Ingest
  │  Write ref files, draft seed cards, update index
  ▼
Step 7: Report
  │  Write cycle digest, log events, update landscape
  ▼
Done → Curator picks up new cards on next curation cycle
```

### 3.2 Step Details

#### Step 1: Load Seeds

**Input:** `search-seeds.json`
**Output:** List of active search clusters with weights

```python
# Conceptual
clusters = load_search_seeds()
active = [c for c in clusters if c.status == "active"]
# Sort by weight (high-weight clusters get more queries)
```

Each cluster in search-seeds.json contains:
- `id` — cluster identifier
- `terms` — list of search terms
- `weight` — 0.0–1.0, how much attention this cluster gets
- `status` — active / paused / exhausted
- `last_queried` — timestamp of last search

#### Step 2: Generate Queries

**Input:** Active clusters
**Output:** API-ready query strings

For each cluster, generate queries appropriate to each configured API:
- **Semantic Scholar:** keyword queries, author searches, citation traversals
- **arXiv:** category + keyword queries, date-bounded

Query count per cluster is proportional to weight. A cluster with weight 0.8 gets more queries than one with weight 0.3.

**Date bounding:** By default, search from `last_queried` to now. First run searches a configurable lookback window (default: 90 days).

#### Step 3: Fetch

**Input:** Query strings
**Output:** Raw API responses (paper metadata)

```
For each query:
  1. Call API with rate limiting (Semantic Scholar: 100 req/5min, arXiv: 3 req/s)
  2. Parse response → list of candidate papers
  3. Collect: title, authors, year, venue, abstract, external_ids, citation_count
  4. Log api_call event
  5. On failure: retry with exponential backoff (max 3 attempts)
  6. On persistent failure: log, skip, continue cycle
```

**Rate limiter:** Global per-API, respects HTTP 429 headers. Persists state across cycles.

#### Step 4: Deduplicate

**Input:** Candidate papers from Step 3
**Output:** Novel papers only (not already in refs)

```
For each candidate:
  1. Check SQLite: SELECT id FROM refs WHERE url = ?
  2. If no URL match: check refs_fts WHERE title MATCH ?
  3. If match found: skip (already ingested)
  4. If no match: pass to Step 5
```

**Dedup is exact + fuzzy title match in v0.1.** Semantic dedup (embedding similarity) is v0.2 with ChromaDB.

#### Step 5: Extract & Score

**Input:** Novel papers
**Output:** Enriched ref objects with findings and relevance scores

For each novel paper:

1. **Extract key findings** (LLM: lightweight tier)
   - Input: title + abstract + venue
   - Output: 1–5 structured finding sentences
   - Prompt: "Extract the key findings from this paper relevant to {domain}. Return as a JSON array of strings."

2. **Score relevance** (LLM: workhorse tier)
   - Input: title + abstract + domain description + current search seeds
   - Output: 0.0–1.0 relevance score
   - Prompt: "Rate 0–1 how relevant this paper is to the domain '{domain_name}': {domain_description}. Consider: does it advance understanding of the domain's core questions?"

3. **Auto-tag content categories**
   - If API provides `fields_of_study`: map to domain's content_categories
   - Otherwise: LLM lightweight classification

**Threshold:** Papers scoring below `relevance_threshold` (default: 0.3, configurable in governance.yaml) are logged but not ingested. They get a ref file with `extraction_status: "skipped"`.

#### Step 6: Ingest

**Input:** Enriched, relevant papers
**Output:** Ref files + draft seed cards

For each paper above threshold:

1. **Write ref file** — `refs/{id}.json` with full schema (metadata, impact, provenance, extraction)
2. **Draft seed card** (if relevance ≥ 0.6) — Create `cards/{slug}.md` with:
   - `epistemic_type`: finding (default for research ingestion)
   - `confidence`: 1 (speculative — needs Curator evaluation)
   - `source_tier`: derived from venue (arXiv=2, blog=3, etc.)
   - `lifecycle`: seed
   - `sources`: reference to the ref file
   - Body: Summary section from extracted findings
3. **Update SQLite index** — Insert ref row, card row (if created), update card_refs
4. **Log events** — `ingest_paper` for each ref, `create_card` for each card

**Cards created by Researcher always start as seeds.** The Curator decides promotions.

#### Step 7: Report

**Input:** Cycle results
**Output:** Digest, events, landscape update

1. **Write cycle digest** — `digests/{domain}/digest-{date}.md`
   - Papers found, papers ingested, papers skipped (with reasons)
   - Cards created
   - API call counts, errors
   - Top findings by relevance score

2. **Update landscape snapshot** — aggregate stats for views/landscape.json
   - Papers ingested last 7/30 days
   - Active search clusters and their yield
   - Coverage by content category

3. **Update search-seeds.json** — mark `last_queried` timestamp per cluster

4. **Log events** — `complete_cycle` with summary stats

---

## 4. Inputs and Outputs

### Reads (does not modify)

| Artifact | Why |
|----------|-----|
| `search-seeds.json` | Seed clusters define what to search for |
| `domains.yaml` | Domain descriptions for relevance scoring |
| `governance.yaml` | Thresholds: relevance_threshold, research_interval |
| `model-routing.yaml` | Which LLM for extraction vs. scoring |
| `db/construct.db` | Dedup queries, existing ref checks |

### Writes

| Artifact | What |
|----------|------|
| `refs/{id}.json` | Structured reference files (one per paper) |
| `cards/{slug}.md` | Draft seed cards (when relevance ≥ 0.6) |
| `digests/{domain}/digest-{date}.md` | Cycle digest |
| `log/events.jsonl` | Append: start_cycle, api_call, ingest_paper, create_card, complete_cycle |
| `search-seeds.json` | Update `last_queried` timestamps only |
| `db/construct.db` | Insert new refs and cards into index |

---

## 5. API Clients

### 5.1 Semantic Scholar

| Endpoint | Purpose | Rate limit |
|----------|---------|-----------|
| `GET /paper/search` | Keyword search | 100 req / 5 min |
| `GET /paper/{id}` | Paper details (citations, references) | 100 req / 5 min |
| `GET /paper/{id}/citations` | Who cites this paper | 100 req / 5 min |
| `GET /paper/{id}/references` | What this paper cites | 100 req / 5 min |
| `GET /author/{id}/papers` | Papers by author | 100 req / 5 min |

**Fields requested:** paperId, title, abstract, authors, year, venue, externalIds, citationCount, influentialCitationCount, tldr, fieldsOfStudy, openAccessPdf, referenceCount

### 5.2 arXiv

| Endpoint | Purpose | Rate limit |
|----------|---------|-----------|
| `GET /api/query` | Search by category + keywords | 3 req / s |

**Fields available:** title, authors, abstract, published, categories, links (PDF)

### 5.3 Future (v0.2+)

| Source | Type | When |
|--------|------|------|
| Web scraping (specific blogs/sites) | Expert content (tier 3) | When domain config lists specific URLs |
| RSS feeds | Continuous monitoring | When domain config includes feeds |
| Google Scholar | Broader academic search | If S2 coverage insufficient |

---

## 6. Error Handling

| Error | Handling | Escalation |
|-------|---------|-----------|
| API rate limit (429) | Exponential backoff, retry up to 3x | Log, continue with remaining queries |
| API down (5xx) | Skip this API for this cycle, use others | Log warning event |
| API key invalid/expired | Fail this cycle | Escalate to CONSTRUCT → notify user |
| LLM extraction fails | Retry once, then write ref with `extraction_status: "failed"` | Log, Researcher retries on next cycle |
| Relevance scoring fails | Default to 0.5 (neutral), flag for human review | Log warning |
| Network offline | Fail entire cycle | Log, skip, retry next interval |

**Resumption:** Each cycle saves progress incrementally. If a cycle is interrupted (process killed), the next cycle picks up from `last_queried` timestamps — no duplicate fetching.

---

## 7. Event Actions

| Action | When | Detail |
|--------|------|--------|
| `start_cycle` | Cycle begins | Domain, cluster count, query count |
| `api_call` | Each API request | API, endpoint, query, result count, latency |
| `ingest_paper` | Ref file written | Ref ID, title, relevance score, domain |
| `create_card` | Seed card drafted | Card ID, ref ID, epistemic_type |
| `complete_cycle` | Cycle ends | Papers found, ingested, skipped, cards created, errors |
| `update_landscape` | Landscape stats refreshed | Domain, paper count, category distribution |

---

## 8. Configuration

All Researcher behavior is configurable via `governance.yaml`:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `research_interval_seconds` | 3600 | How often a cycle runs |
| `relevance_threshold` | 0.3 | Minimum score to ingest |
| `card_creation_threshold` | 0.6 | Minimum score to draft a seed card |
| `max_papers_per_cycle` | 50 | Cap on ingested papers per cycle |
| `lookback_days_initial` | 90 | First-run search window |
| `max_retries` | 3 | API call retries |

---

## 9. Deferred (v0.2+)

| Capability | Why deferred |
|-----------|-------------|
| Semantic dedup via ChromaDB | Needs embedding infrastructure |
| Citation graph traversal ("papers that cite papers we already have") | Useful but scope-expanding |
| RSS/feed monitoring | Requires daemon or scheduled polling |
| Autonomous search pattern evolution | Requires trust gradient |
| Full-text PDF extraction | Requires PDF parsing pipeline |
