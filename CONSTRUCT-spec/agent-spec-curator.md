# Curator Agent — Specification

**Version:** 0.1.0
**Date:** 2026-04-21
**Status:** Draft — v0.1 scope
**Role:** Knowledge graph maintenance, quality gates, lifecycle management

---

## 1. Identity

The Curator is CONSTRUCT's graph gardener. It maintains the health, integrity, and quality of the knowledge graph through automated checks, rule-based promotions, decay management, and lightweight LLM evaluation. It does not acquire new knowledge (that's the Researcher) and does not reason at the frontier level (that's CONSTRUCT). It tends what exists.

**LLM tier:** None for most operations (graph queries, date math, validation). Workhorse for ambiguous evaluations and connection typing.

**Runs autonomously:** Yes — on curation cycle (default: every 5 minutes). Escalates to CONSTRUCT when judgment is needed.

---

## 2. Responsibilities

### 2.1 Free Operations (No LLM)

| Task | Mechanism | Trigger | Output |
|------|-----------|---------|--------|
| **Orphan detection** | `SELECT id FROM cards WHERE connection_count = 0` | Every curation cycle | Flag list → events.jsonl + views |
| **Decay flagging** | `SELECT id FROM cards WHERE last_referenced < date('now', '-N days')` | Every curation cycle | Flag list → events.jsonl |
| **Integrity checks** | Validate: dangling connections, missing required fields, schema violations | Every curation cycle | Error list → events.jsonl |
| **Health stats** | Aggregate: card count, confidence distribution, domain balance, orphan count, stale count | Every curation cycle | Stats → `domains` table + views |
| **Rule-based auto-promotion** | Card meets ALL: confidence ≥ 3, source_tier ≤ 2, connections ≥ 1, all required fields | Every curation cycle | Promote seed→growing or growing→mature |
| **Rule-based auto-flagging** | Card has: no sources, confidence = 1, zero connections, older than N days | Every curation cycle | Flag for review |
| **Exact duplicate detection** | `SELECT id FROM refs WHERE url = ?` + exact title match | On new card/ref ingestion | Skip or flag |
| **Connection count maintenance** | Update `cards.connection_count` when connections change | On connection add/remove | Updated count |

### 2.2 LLM Operations (Workhorse Tier)

| Task | Mechanism | Trigger | Output |
|------|-----------|---------|--------|
| **Ambiguous card evaluation** | Cards pass some promotion rules but not all. LLM assesses quality. | Curation cycle finds borderline cards | Promote, hold, or escalate |
| **Connection type proposals** | Two cards manually linked but edge is untyped. LLM proposes type. | Untyped edge detected | Typed connection (user can override) |
| **Graph health summary** | Natural language summary of graph state for dashboard/CLI | On `/graph status` or dashboard refresh | Markdown summary → views |
| **Seed card evaluation** | Researcher-drafted seed cards assessed for quality and relevance | New seed cards from research cycle | Assess, tag, or flag for human |

### 2.3 Escalation to CONSTRUCT (Frontier)

| Situation | What Curator sends | Expected resolution |
|-----------|-------------------|-------------------|
| Contradicting mature cards | Both card IDs, contradiction description | CONSTRUCT reasons, proposes resolution to human |
| Judgment call on borderline card | Card ID, what rules pass/fail, LLM assessment | CONSTRUCT decides promote/hold/archive |
| Cross-domain bridge candidate (L1/L2) | Two cards, proposed connection, domains involved | CONSTRUCT assesses if connection is genuine |

---

## 3. The Curation Cycle

One complete curation cycle runs on interval (default: 300s). Each step is independent — a failure in one step doesn't block others.

### 3.1 Cycle Overview

```
Step 1: Integrity Check
  │  Validate all cards against schema
  │  Check for dangling connections
  ▼
Step 2: Decay Scan
  │  Flag cards past decay window
  │  Auto-archive if governance allows
  ▼
Step 3: Orphan Scan
  │  Flag cards with zero connections
  │  (new cards get orphan_tolerance_days grace period)
  ▼
Step 4: Promotion Scan
  │  Rule-based: promote qualifying cards
  │  LLM: evaluate ambiguous cards
  ▼
Step 5: Connection Maintenance
  │  Type untyped edges (LLM)
  │  Cross-domain bridge detection (L1+L2)
  ▼
Step 6: Process Inbox
  │  Handle pending inbox actions (comments, flags, edits)
  ▼
Step 7: Stats & Report
  │  Update domain stats, write health summary
  ▼
Done → Events logged, views updated on next heartbeat
```

### 3.2 Step Details

#### Step 1: Integrity Check

For each card in the index:
1. Validate YAML frontmatter against knowledge-card-schema.md rules
2. Check that `connects_to` targets exist as card files
3. Check that `domains` entries exist in domains.yaml
4. Check that `epistemic_type` and `lifecycle` are valid enums

**Output:** List of validation errors/warnings. Errors logged as `validate_card` events with `result: "failure"`.

#### Step 2: Decay Scan

```sql
SELECT id, title, last_referenced, lifecycle
FROM cards
WHERE last_referenced < date('now', '-' || ? || ' days')
  AND lifecycle != 'archived'
```

For each stale card:
- If `auto_archive_on_decay` is true: archive the card, log `archive_card` event
- Otherwise: log `flag_decay` event (surfaces in dashboard, human reviews)

#### Step 3: Orphan Scan

```sql
SELECT id, title, created
FROM cards
WHERE connection_count = 0
  AND created < date('now', '-' || ? || ' days')  -- orphan_tolerance_days
  AND lifecycle != 'archived'
```

Log `flag_orphan` event for each. Orphans within grace period are not flagged.

#### Step 4: Promotion Scan

**Rule-based auto-promotion (no LLM):**

| Current state | Promotes to | Conditions |
|--------------|-------------|-----------|
| seed | growing | confidence ≥ 2 AND connections ≥ 1 |
| growing | mature | confidence ≥ 3 AND source_tier ≤ 2 AND connections ≥ 2 |

If `require_human_approval` is true in governance.yaml, auto-promotion only flags for review instead of promoting directly.

**Ambiguous evaluation (LLM: workhorse):**

Cards that meet *some but not all* promotion criteria:

```
Prompt: "Evaluate this knowledge card for promotion from {current} to {next}.
Card: {title}
Type: {epistemic_type}
Confidence: {confidence}, Source tier: {source_tier}
Connections: {connection_count}
Body: {first 500 chars}

Rules met: {list}. Rules not met: {list}.
Should this card be promoted, held, or escalated for human review?"
```

LLM returns: `promote` | `hold` | `escalate`
- `promote`: Curator promotes, logs event
- `hold`: No action, logs event with reasoning
- `escalate`: Sends to CONSTRUCT for judgment

#### Step 5: Connection Maintenance

**Type untyped edges (LLM: workhorse):**

```sql
SELECT * FROM connections WHERE type IS NULL OR type = ''
```

For each untyped edge:
```
Prompt: "Two knowledge cards are connected but the relationship type is unknown.
Card A: {title_a} — {summary_a}
Card B: {title_b} — {summary_b}

Choose the best relationship type:
supports | contradicts | extends | parallels | requires | enables | challenges | inspires | gap-for

Return: {type} and a one-sentence justification."
```

**Cross-domain bridge detection (L1 — free, graph query):**

```sql
-- Cards with connections into 2+ domains
SELECT c.id, COUNT(DISTINCT cd2.domain) as domain_count
FROM cards c
JOIN connections conn ON c.id = conn.from_card OR c.id = conn.to_card
JOIN card_domains cd2 ON (conn.from_card = cd2.card_id OR conn.to_card = cd2.card_id)
WHERE cd2.domain NOT IN (SELECT domain FROM card_domains WHERE card_id = c.id)
GROUP BY c.id
HAVING domain_count >= 2
```

**Cross-domain bridge detection (L2 — free, tag overlap):**

```sql
-- Cards sharing content categories across different domains
SELECT a.card_id, b.card_id, a.category
FROM card_categories a
JOIN card_categories b ON a.category = b.category AND a.card_id != b.card_id
JOIN card_domains da ON a.card_id = da.card_id
JOIN card_domains db ON b.card_id = db.card_id
WHERE da.domain != db.domain
AND NOT EXISTS (
    SELECT 1 FROM connections
    WHERE (from_card = a.card_id AND to_card = b.card_id)
       OR (from_card = b.card_id AND to_card = a.card_id)
)
```

Bridge candidates are escalated to CONSTRUCT for assessment.

#### Step 6: Process Inbox

Read all pending `inbox/action-*.json` files. For each:

| Action type | Curator handling |
|------------|-----------------|
| `comment` | Attach comment text to card (append to body or metadata), log event |
| `flag` | Update card lifecycle or confidence based on flag reason, log event |
| `promote` | Run promotion quality gates, promote if passing, else escalate |
| `edit` | Validate proposed changes against schema, apply if valid, else reject |
| `connect` | Validate both cards exist, run connection type proposal (LLM), add edge |
| `config` | Forward to CONSTRUCT (Curator doesn't modify config) |

After processing: delete the inbox file, write result to `views/responses.json`.

#### Step 7: Stats & Report

Update the `domains` table:

```sql
UPDATE domains SET
    card_count = (SELECT COUNT(*) FROM card_domains WHERE domain = ?),
    avg_confidence = (SELECT AVG(confidence) FROM cards JOIN card_domains ON ...),
    orphan_count = (SELECT COUNT(*) FROM cards WHERE connection_count = 0 AND ...),
    stale_count = (SELECT COUNT(*) FROM cards WHERE last_referenced < ...),
    newest_card = (SELECT MAX(created) FROM cards JOIN card_domains ON ...),
    oldest_card = (SELECT MIN(created) FROM cards JOIN card_domains ON ...)
WHERE id = ?
```

Log `health_report` event with summary.

---

## 4. Inputs and Outputs

### Reads (does not modify)

| Artifact | Why |
|----------|-----|
| `governance.yaml` | Promotion rules, decay window, thresholds |
| `domains.yaml` | Domain definitions for domain-aware queries |
| `model-routing.yaml` | Which LLM for workhorse tasks |
| `db/construct.db` | All queries (cards, connections, refs, events) |
| `inbox/action-*.json` | Pending user actions from React UI |

### Writes

| Artifact | What |
|----------|------|
| `cards/*.md` | Update frontmatter (lifecycle, confidence on promotion) |
| `connections.json` | Add typed connections, remove invalid ones |
| `log/events.jsonl` | Append: all curation actions |
| `views/responses.json` | Inbox action results (for UI feedback) |
| `db/construct.db` | Update cards, connections, domains tables |

---

## 5. Event Actions

| Action | When | Detail |
|--------|------|--------|
| `promote_card` | Card promoted (seed→growing, growing→mature) | Card ID, from→to state, rule or LLM |
| `archive_card` | Card archived (decay or manual) | Card ID, reason |
| `flag_decay` | Card past decay window | Card ID, days since last reference |
| `flag_orphan` | Card has zero connections past grace | Card ID, days since creation |
| `add_connection` | New edge created | From, to, type, created_by |
| `type_connection` | Untyped edge assigned a type | From, to, type, LLM justification |
| `validate_card` | Schema validation run | Card ID, pass/fail, error list |
| `integrity_check` | Full integrity scan complete | Errors found, warnings found |
| `health_report` | Stats aggregation complete | Card count, orphans, stale, avg confidence per domain |

---

## 6. Configuration

All Curator behavior is governed by `governance.yaml`:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `curation_interval_seconds` | 300 | How often the cycle runs |
| `auto_promote_confidence_floor` | 3 | Minimum confidence for auto-promotion to mature |
| `auto_promote_source_tier_ceiling` | 2 | Maximum source tier for auto-promotion |
| `auto_promote_min_connections` | 1 | Minimum connections for auto-promotion |
| `require_human_approval` | false | If true, auto-promote only flags for review |
| `decay_window_days` | 28 | Days unreferenced before flagging |
| `auto_archive_on_decay` | false | Auto-archive or just flag? |
| `orphan_tolerance_days` | 7 | Grace period for new cards before orphan flagging |
| `min_sources_for_promotion` | 1 | Sources needed to leave seed state |

---

## 7. Deferred (v0.2+)

| Capability | Why deferred | Dependency |
|-----------|-------------|-----------|
| Semantic duplicate detection | Needs embedding similarity | ChromaDB (v0.2) |
| Category split suggestions | Needs corpus analysis + taxonomy evolution | Mature graph (200+ cards) |
| Cross-domain bridge proposals (L3) | Needs embedding infrastructure | ChromaDB (v0.2) |
| Cross-domain bridge proposals (L4) | Needs frontier reasoning | CONSTRUCT delegation + cost budget |
| Automated taxonomy evolution | Needs pattern detection over time | v0.3 — trust gradient |
| Conflict resolution (not just detection) | Needs deep reasoning | CONSTRUCT handles in v0.1 |
