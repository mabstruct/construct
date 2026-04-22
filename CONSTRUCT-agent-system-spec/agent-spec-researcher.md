# Researcher Agent — Specification (Claude-Native)

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active
**Role:** Automated knowledge acquisition from external sources
**Implementation:** `CONSTRUCT-agents/agents/researcher.md` + `CONSTRUCT-agents/skills/research-cycle/SKILL.md`

---

## 1. Identity

The Researcher is CONSTRUCT's external knowledge acquisition role. It runs structured search cycles using Claude's web search capability, extracts findings, scores relevance, and delivers seed cards to the workspace for Curator evaluation.

**Runtime:** Claude's web search tool replaces dedicated API clients (Semantic Scholar, arXiv). The search procedure is defined in the `research-cycle` skill.

**Autonomy:** Runs when the user triggers a research cycle. Reports findings inline during the conversation.

---

## 2. Responsibilities

| Responsibility | Mechanism | Notes |
|---------------|-----------|-------|
| Execute search cycles | Web search from `search-seeds.json` patterns | Claude's native web search |
| Extract key findings | Reading and summarizing search results | Claude's native reasoning |
| Score relevance to domain | Assessment against domain description | Uses rubric from `agents/researcher.md` |
| Deduplicate against existing refs | Read `refs/` directory, compare titles/URLs | File listing + comparison |
| Draft seed cards | Structure findings into card YAML + body | Uses `templates/card.md` |
| Write ref files | Create `refs/{id}.json` with structured metadata | File creation |
| Write cycle digests | Summarize what was found | Uses `templates/digest.md` |
| Update search-seeds.json | Record `last_queried` timestamps | File update |
| Escalate anomalies | Flag out-of-scope or contradictory findings | Switch back to CONSTRUCT |

---

## 3. The Research Cycle

### 7-Step Process

Identical structure to the Python approach, but using Claude's native capabilities:

#### Step 1: Load Seeds
- Read `search-seeds.json`
- Filter to active clusters
- Sort by weight (high-weight clusters get more search queries)

#### Step 2: Generate Queries
- For each active cluster, formulate 2–4 web search queries from its terms
- Higher-weight clusters get more query variations
- Add date constraints based on `last_queried`

#### Step 3: Search
- Use Claude's web search for each query
- Collect: title, authors, year, venue, URL, abstract/summary
- Target: academic papers, preprints, technical reports, expert analysis
- Web search replaces the dedicated Semantic Scholar / arXiv API clients

#### Step 4: Deduplicate
- List existing `refs/*.json` files
- For each search result, check if URL or title closely matches existing refs
- Skip known items

#### Step 5: Extract & Score
For each novel result:
1. **Extract key findings** — 1–5 structured finding sentences
2. **Score relevance** — 0.0–1.0 against domain description from `domains.yaml`
3. **Classify content categories** — map to domain taxonomy
4. **Apply thresholds** from `governance.yaml`:
   - Below `relevance_threshold` (0.3): log skip, don't ingest
   - Between threshold and `card_creation_threshold` (0.6): create ref only
   - Above card threshold: create ref AND draft seed card

#### Step 6: Ingest
For each paper above threshold:
1. Write `refs/{id}.json` with full metadata
2. Draft seed card in `cards/` (if above card threshold) using `templates/card.md`
3. Log events to `events.jsonl`

#### Step 7: Report
1. Write digest to `digests/{domain}/digest-{date}.md` using `templates/digest.md`
2. Update `search-seeds.json` timestamps
3. Summarize results to user

---

## 4. Differences from Python Approach

| Aspect | Python approach | Claude-native |
|--------|----------------|---------------|
| Search API | httpx → Semantic Scholar, arXiv | Claude web search |
| Rate limiting | HTTP 429 handling, req/minute counters | Not applicable (Claude manages internally) |
| Dedup mechanism | SQLite query (URL, FTS5 title match) | File listing + title/URL comparison |
| Extraction | LLM API call (lightweight tier) | Claude's native reasoning |
| Scoring | LLM API call (workhorse tier) | Claude's native reasoning |
| Output | Programmatic file creation | Claude file operations |

**Net effect:** Same structured procedure, same output artifacts, different runtime.

---

## 5. Source Tier Assignment

Identical to Python approach. Assigned during ingestion:

| Tier | Source type |
|------|-----------|
| 1 | Published in journal / top conference |
| 2 | arXiv preprint, technical report |
| 3 | Expert blog, conference talk |
| 4 | Wikipedia, tutorial, forum |
| 5 | Social media, unverified |

---

## 6. Escalation

Switch back to CONSTRUCT role when:
- A finding falls outside all configured domains
- A result contradicts established (confidence ≥ 4) cards
- A cluster yields nothing new across multiple cycles (search exhaustion)

---

## 7. Event Logging

Log to `log/events.jsonl`:

| Event | When |
|-------|------|
| `search_query` | Each web search executed |
| `ingest_paper` | Ref file written |
| `create_card` | Seed card drafted |
| `skip_duplicate` | Known item skipped |
| `skip_low_relevance` | Item below threshold |
| `research_cycle_complete` | Full cycle finished |
