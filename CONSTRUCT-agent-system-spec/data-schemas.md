# CONSTRUCT Agent System — Data Schemas

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active — canonical reference for all structured data
**Related:** [knowledge-card-schema.md](knowledge-card-schema.md) for card format

---

## Purpose

This document defines the JSON/YAML schemas for every workspace artifact except knowledge cards. These schemas are the contract between agent roles, skills, and workspace files. Skills that produce or consume these artifacts must conform to these schemas.

**Shared with Python approach:** These schemas are intentionally identical to `CONSTRUCT-spec/construct-data-schemas.md` to enable workspace interoperability.

---

## 1. Source of Truth Layer

### 1.1 `connections.json`

The knowledge graph edge list. Written by Curator skills, read by all skills.

```json
{
  "version": 1,
  "updated": "2026-04-23",
  "connection_types": [
    "supports", "contradicts", "extends", "parallels",
    "requires", "enables", "challenges", "inspires", "gap-for"
  ],
  "connections": [
    {
      "from": "card-id-a",
      "to": "card-id-b",
      "type": "extends",
      "note": "A builds on B's framework",
      "created": "2026-04-23",
      "created_by": "curator"
    }
  ]
}
```

**Validation rules:**
- `from` and `to` must reference card IDs that exist as files in `cards/`
- `type` must be a valid connection type
- No duplicate edges (same from + to + type)
- `version` increments on every write
- `created_by` is one of: `curator`, `researcher`, `human`, `construct`

### 1.2 `domains.yaml`

Domain taxonomy definitions. See `templates/domains.yaml` for structure.

```yaml
domains:
  {domain-id}:                          # kebab-case, unique
    name: "{Display Name}"
    description: "{Domain description}"
    status: active                      # active | paused | archived
    created: 2026-04-23
    content_categories:                 # kebab-case list
      - {category-1}
      - {category-2}
    source_priorities:                  # ordered, most important first
      - "{source type 1}"
    cross_domain_links:                 # optional
      - domain: {other-domain-id}
        topics: ["{topic1}"]
```

**Validation rules:**
- Domain IDs are kebab-case, unique
- `status` is one of: `active`, `paused`, `archived`
- `content_categories` entries are kebab-case

### 1.3 `governance.yaml`

Curator thresholds and rules. See `templates/governance.yaml` for full schema.

**Key sections:**
- `promotion` — seed→growing and growing→mature thresholds
- `decay` — decay window, auto-archive toggle
- `quality` — orphan tolerance, minimum sources
- `research` — relevance threshold, card creation threshold, max papers per cycle

### 1.4 `search-seeds.json`

Research search patterns.

```json
{
  "version": 1,
  "updated": "2026-04-23",
  "clusters": [
    {
      "id": "{domain}-{topic-slug}",
      "domain": "{domain-id}",
      "terms": ["{term1}", "{term2}"],
      "weight": 0.8,
      "status": "active",
      "last_queried": "2026-04-23T14:00:00Z"
    }
  ]
}
```

**Validation rules:**
- Cluster IDs are unique
- `domain` references a domain in `domains.yaml`
- `weight` is 0.0–1.0
- `status` is one of: `active`, `paused`, `exhausted`

---

## 2. Agent Output Layer

### 2.1 `refs/{id}.json`

Reference entry for a single external source. Written by Researcher.

```json
{
  "id": "{kebab-case-id}",
  "title": "{Paper/Article Title}",
  "authors": ["{Author A}", "{Author B}"],
  "year": 2026,
  "venue": "{Journal, Conference, or Site}",
  "url": "{source URL}",
  "abstract": "{abstract or summary text}",
  "relevance_score": 0.8,
  "key_findings": ["{finding 1}", "{finding 2}"],
  "content_categories": ["{category1}"],
  "source_tier": 2,
  "extraction_status": "complete",
  "ingested_date": "2026-04-23",
  "domain": "{domain-id}",
  "search_cluster": "{cluster-id}",
  "cards_generated": ["{card-id}"]
}
```

**Validation rules:**
- `id` matches filename (without .json)
- `relevance_score` is 0.0–1.0
- `source_tier` is 1–5
- `extraction_status` is one of: `complete`, `partial`, `skipped`

### 2.2 `digests/{domain}/digest-{date}.md`

Research cycle summary. Written by Researcher. See `templates/digest.md` for format.

### 2.3 `publish/{slug}.md`

Curated output document. Written by synthesis skill. Contains YAML frontmatter with:

```yaml
---
title: "{Title}"
type: briefing                          # briefing | essay | summary | report
date: 2026-04-23
domains: ["{domain-id}"]
source_cards: ["{card-id-1}", "{card-id-2}"]
confidence_floor: 2
status: draft                           # draft | review | final
---
```

---

## 3. Event Log

### 3.1 `log/events.jsonl`

Append-only audit trail. One JSON object per line.

```json
{"ts": "2026-04-23T14:30:00Z", "agent": "curator", "action": "promote_card", "target": "card-id", "detail": "seed → growing, confidence 2, connections 1", "result": "success"}
```

**Required fields:**
- `ts` — ISO-8601 timestamp
- `agent` — `construct`, `curator`, `researcher`, `human`
- `action` — event type (see catalog below)
- `result` — `success`, `failure`, `escalated`

**Optional fields:**
- `target` — card ID, domain, or artifact affected
- `detail` — human-readable description

### Event Catalog

| Event | Agent | When |
|-------|-------|------|
| `workspace_init` | construct | Workspace created |
| `domain_init` | construct | Domain interview completed |
| `session_start` | construct | Conversation begins |
| `session_end` | construct | Conversation ends |
| `create_card` | researcher/human | Card file created |
| `edit_card` | curator/human | Card metadata or content updated |
| `promote_card` | curator | Card lifecycle changed |
| `archive_card` | curator/human | Card moved to archived state |
| `flag_decay` | curator | Card flagged as stale |
| `flag_orphan` | curator | Card has zero connections |
| `validate_card` | curator | Card checked against schema |
| `add_connection` | curator/human | Edge added to connections.json |
| `type_connection` | curator | Untyped edge assigned relation |
| `remove_connection` | curator/human | Edge removed |
| `detect_bridge` | curator | Cross-domain bridge identified |
| `search_query` | researcher | Web search executed |
| `ingest_paper` | researcher | Ref file created |
| `skip_duplicate` | researcher | Known item skipped |
| `skip_low_relevance` | researcher | Item below threshold |
| `research_cycle_complete` | researcher | Full research cycle finished |
| `curation_cycle_complete` | curator | Full curation cycle finished |
| `update_search_pattern` | construct | search-seeds.json modified |
| `publish_artifact` | construct | Draft finalized in publish/ |
| `escalation_received` | construct | Sub-role escalated a decision |
| `escalation_resolved` | construct | Decision made on escalation |
