# CONSTRUCT — Data Schemas

**Version:** 0.1.0
**Date:** 2026-04-19
**Status:** Draft — canonical reference for all structured data in CONSTRUCT
**Related:** [knowledge-card-schema.md](knowledge-card-schema.md) for the card format itself

---

## Purpose

This document defines the JSON/YAML schemas for every structured artifact in CONSTRUCT except knowledge cards (covered separately). These schemas are the contract between agents, the Python core, the views step, and the React UI. Code that produces or consumes these artifacts must conform to these schemas. Contract tests in CI validate compliance.

---

## 1. Source of Truth Layer

### 1.1 `connections.json`

The authoritative knowledge graph edge list. Written by the Curator. Read by the graph engine, views step, and agents.

```jsonc
{
  "version": 1,                           // integer, incremented on every write
  "updated": "2026-04-19",                // ISO date
  "connection_types": [                   // enum reference — informational
    "supports", "contradicts", "extends", "parallels",
    "requires", "enables", "challenges", "inspires", "gap-for"
  ],
  "connections": [
    {
      "from": "card-id-a",               // string — must reference existing card
      "to": "card-id-b",                 // string — must reference existing card
      "type": "extends",                  // string — must be in connection_types
      "note": "A builds on B's framework", // string, optional (but recommended)
      "created": "2026-04-19",            // ISO date
      "created_by": "curator"             // enum: curator | human | researcher
    }
  ]
}
```

**Validation:**
- `from` and `to` must reference card IDs that exist in `cards/`
- `type` must be a valid connection type
- No duplicate edges (same from + to + type)
- `version` must increment monotonically

---

### 1.2 `domains.yaml`

Domain taxonomy definitions. Written by human (via domain-init workflow or manual edit). Read by all agents and UI.

```yaml
domains:
  intelligent-spatial-worlds:
    name: "Intelligent Spatial Worlds"
    description: "AI systems that reason about and act in physical/spatial environments"
    status: active                        # enum: active | paused | archived
    created: 2026-04-19
    content_categories:                   # domain-specific taxonomy labels
      - foundation-models
      - spatial-reasoning
      - reinforcement-learning
      - world-models
      - sim-to-real
      - manipulation
      - navigation
      - multi-agent
      - benchmarks
      - safety-alignment
    source_priorities:                    # ordered — most important first
      - "peer-reviewed (arXiv, top venues)"
      - "technical reports (Google, DeepMind, Meta)"
      - "expert blogs (Karpathy, Lillicrap)"
    cross_domain_links:                   # known overlaps with other domains
      - domain: neuroscience
        topics: ["spatial memory", "place cells", "successor representation"]

  # additional domains follow same structure
```

**Validation:**
- Domain IDs are kebab-case, unique
- `status` is one of: `active`, `paused`, `archived`
- `content_categories` entries are kebab-case

---

### 1.3 `model-routing.yaml`

LLM provider and task-tier routing. Written by human. Read by agent runtime.

```yaml
providers:
  frontier:
    provider: anthropic                   # enum: anthropic | openai | google | ollama | mock
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY        # env var name (NOT the key itself)
  workhorse:
    provider: ollama
    model: llama3.3:70b
  lightweight:
    provider: ollama
    model: llama3.2:8b

routing:
  # keys are task identifiers used by agent code
  research_ingestion: lightweight
  card_formatting: lightweight
  source_evaluation: workhorse
  taxonomy_tagging: workhorse
  duplicate_detection: workhorse
  connection_typing: workhorse
  cross_domain_ideation: frontier
  synthesis_drafting: frontier
  co_authorship: frontier
  gap_analysis: frontier
  domain_init_interview: frontier
  chat_conversation: frontier

fallback_chain:                           # if chosen tier fails, try next
  - frontier
  - workhorse
  - lightweight
```

**Validation:**
- Provider names must be valid enum values
- `api_key_env` must not contain actual key values
- All routing task names must map to a defined provider tier
- Fallback chain entries must reference defined tiers

---

### 1.4 `governance.yaml`

Configurable governance thresholds. Written by human. Read by Curator and Researcher.

```yaml
# Curator promotion rules
promotion:
  seed_to_growing_confidence: 2           # card promotes seed→growing if confidence >= this
  seed_to_growing_min_connections: 1      # AND connections >= this
  growing_to_mature_confidence: 3         # card promotes growing→mature if confidence >= this
  growing_to_mature_source_tier: 2        # AND source_tier <= this
  growing_to_mature_min_connections: 2    # AND connections >= this
  require_human_approval: false           # if true, auto-promote only flags for review

# Decay rules
decay:
  decay_window_days: 28                   # days unreferenced before flagging
  auto_archive_on_decay: false            # if true, auto-archive (not just flag)

# Quality gates
quality:
  orphan_tolerance_days: 7                # days a card can exist with 0 connections before flagging
  min_sources_for_promotion: 1            # cards need >= this many sources to reach growing

# Heartbeat
heartbeat:
  views_interval_seconds: 30              # how often views/ is rebuilt
  curation_interval_seconds: 300          # how often Curator runs maintenance
  research_interval_seconds: 3600         # how often Researcher runs a cycle (1h default)

# Research
research:
  relevance_threshold: 0.3                # minimum relevance score to ingest a ref
  card_creation_threshold: 0.6            # minimum relevance score to draft a seed card
  max_papers_per_cycle: 50                # cap on ingested papers per cycle
  lookback_days_initial: 90               # first-run search window
  max_retries: 3                          # API call retries before skipping
```

---

### 1.5 `workflows/*.md`

BMAD-inspired workflow definitions. Markdown files with YAML frontmatter. Written by human or CONSTRUCT.

```yaml
---
id: domain-init
name: "Domain Initialization"
type: interview                           # enum: interview | cycle | review | synthesis
agent: construct                          # which agent runs this
trigger: manual                           # enum: manual | heartbeat | scheduled | event
context_requires:                         # files loaded into agent context before running
  - domains.yaml
  - model-routing.yaml
produces:                                 # artifacts this workflow creates/updates
  - domains.yaml
  - search-seeds.json
---

# Domain Initialization Workflow

## Step 1: Scope Interview
Ask the user to describe the domain...

## Step 2: Taxonomy Seeding
From the scope, propose initial content categories...

## Step 3: Source Configuration
Ask about key papers, authors, institutions, newsletters, RSS...

## Step 4: Search Pattern Generation
Generate initial search-seeds.json with weighted clusters...

## Step 5: Confirmation
Present summary, confirm, write config files.
```

**Validation:**
- `id` is kebab-case, unique across `workflows/`
- `agent` references a valid agent name
- `context_requires` entries are valid file paths
- Body contains at least one `## Step` section

---

### 1.6 `log/events.jsonl`

Append-only audit trail. Written by all agents. Read by publish step and UI.

Each line is a self-contained JSON object:

```jsonc
{
  "ts": "2026-04-19T14:30:00.000Z",      // ISO 8601 with milliseconds
  "agent": "curator",                     // enum: construct | curator | researcher | synthesizer | human
  "action": "promote_card",               // string — action identifier (see action catalog below)
  "target": "successor-representation",   // string — primary artifact affected (card ID, domain name, etc.)
  "detail": "seed → growing; confidence 2, 1 connection", // human-readable detail string
  "result": "success",                    // enum: success | failure | skipped | escalated
  "error": null                           // string or null — error message if result != success
}
```

**Action catalog (v0.1):**

| Agent | Actions |
|-------|---------|
| `curator` | `promote_card`, `archive_card`, `flag_decay`, `flag_orphan`, `add_connection`, `type_connection`, `validate_card`, `integrity_check`, `health_report` |
| `researcher` | `start_cycle`, `complete_cycle`, `ingest_paper`, `create_card`, `update_landscape`, `api_call` |
| `construct` | `start_session`, `end_session`, `delegate_task`, `update_search_pattern`, `domain_init`, `chat_response`, `escalation_received`, `escalation_resolved` |
| `human` | `edit_card`, `override_confidence`, `approve_promotion`, `reject_promotion`, `add_card_manual` |

**Validation:**
- Each line must be valid JSON
- `ts` must be valid ISO 8601
- `agent` must be a known agent
- `result` must be a valid enum value

---

### 1.7 `search-seeds.json`

Research search pattern configuration. Written by CONSTRUCT (via search-adjust workflow). Read by Researcher.

```jsonc
{
  "version": 1,                           // integer, incremented on update
  "generated": "2026-04-19",              // ISO date
  "domain": "intelligent-spatial-worlds", // references domains.yaml
  "changelog": [
    {
      "version": 1,
      "date": "2026-04-19",
      "trigger": "domain-init workflow",  // what caused this version
      "changes": ["Initial seed generation from domain interview"]
    }
  ],
  "clusters": [
    {
      "id": "spatial-reasoning",          // kebab-case, unique within this file
      "name": "Spatial Reasoning in VLAs", // display name
      "search_terms": [                   // 3–10 search query strings
        "spatial reasoning vision language action model 2025 2026",
        "VLA spatial understanding benchmark"
      ],
      "weight": 1.5                       // float 0.1–3.0, higher = more attention
    }
  ],
  "wildcard_terms": [                     // exploratory terms outside clusters
    "unexpected breakthrough robot learning 2026"
  ],
  "sources": {                            // which APIs to query
    "semantic_scholar": true,
    "arxiv": true,
    "web_search": false                   // opt-in per domain
  }
}
```

---

### 1.8 `refs/{id}.json`

Per-source structured reference. Written by Researcher. Read by Curator (duplicate detection, impact assessment), views heartbeat (landscape stats), and publish step.

```jsonc
{
  "_meta": {
    "spec_version": "1.1",
    "extraction_method": "semantic-scholar-api",  // or "arxiv-api", "manual", "web-scrape"
    "fetched_at": "2026-04-19T14:30:00Z",
    "attempts": 1
  },
  "source_paper": {
    "id": "2501.10100",                   // arXiv ID, DOI, or slug
    "title": "Paper Title",
    "authors": [
      { "name": "First Last", "affiliations": ["MIT"] }
    ],
    "year": 2025,
    "publication_date": "2025-01-17",     // full ISO date when available (nullable)
    "venue": "arXiv.org",
    "tier": 2,                            // source tier 1–5
    "url": "https://...",
    "open_access_pdf_url": null,          // direct link to full text (nullable)
    "external_ids": {                     // optional, varies by source
      "arxiv": "2501.10100",
      "doi": "10.1234/...",
      "corpus_id": 123456
    },
    "tags": ["spatial-reasoning", "vla"],  // content_category tags
    "fields_of_study": ["Computer Science", "Artificial Intelligence"],  // API-provided classification (nullable)
    "abstract": "...",
    "tldr": "One-sentence summary from API or LLM extraction",  // nullable
    "superseded_by": null                 // ref ID if a newer version exists (nullable)
  },
  "impact": {                             // nullable block — populated when API provides it
    "citation_count": 42,                 // raw citation count
    "influential_citation_count": 7,      // S2: citations that meaningfully engage with this work
    "reference_count": 35                 // how many papers this one cites
  },
  "provenance": {
    "retrieval_query": "spatial reasoning VLA",       // which search term found this
    "search_seed_id": "cluster-spatial-reasoning",    // which seed/cluster from search-seeds.json
    "discovery_session": "session-2026-04-19-001"     // session that found this
  },
  "extraction": {
    "status": "partial",                  // enum: pending | partial | complete | failed
    "relevance_score": 0.82,             // 0–1, Researcher's assessment at ingestion time (nullable)
    "cards_generated": ["successor-representation-spatial"],  // card IDs created from this ref
    "key_findings": [                     // structured extraction (nullable, populated by LLM)
      "SR provides a predictive map for spatial navigation",
      "Outperforms model-free baselines on continuous state spaces"
    ],
    "extracted_at": "2026-04-19T15:00:00Z"  // when extraction was last run (nullable)
  },
  "references": [                         // cited papers (optional, for graph building)
    {
      "ref_id": "ref-001",
      "title": "Referenced Paper",
      "authors": [{ "name": "Name" }],
      "year": 2024,
      "arxiv_id": null,
      "doi": null,
      "in_corpus": false,                 // true if we also have a ref file for this
      "tags": []
    }
  ]
}
```

**New fields (v1.1):**

| Field | Source | Why |
|-------|--------|-----|
| `publication_date` | API | Full date for recency sorting (year alone is coarse) |
| `open_access_pdf_url` | API | Enables deeper extraction without manual hunting |
| `fields_of_study` | S2 API | Auto-tagging: map to domains without LLM call |
| `tldr` | S2 API or LLM | Saves a frontier call — use API summary when available |
| `superseded_by` | Researcher | Track when v2 of a paper replaces v1 |
| `impact.*` | S2 API | Citation counts signal importance for prioritization |
| `provenance.*` | Researcher | Which query and session found this — audit trail for research cycle |
| `extraction.status` | Researcher | Track whether we've fully processed this ref |
| `extraction.relevance_score` | Researcher (LLM) | Triage: should Curator spend time on this? |
| `extraction.cards_generated` | Researcher | Reverse link: ref → cards (complements card → ref) |
| `extraction.key_findings` | Researcher (LLM) | Structured extraction before card creation |

---

## 2. Views Layer (Disposable, Heartbeat-Rebuilt)

All files in `views/` are rebuilt every heartbeat. The React UI reads exclusively from `views/`. Losing `views/` costs nothing — next heartbeat recreates it.

### 2.1 `views/graph.json`

Knowledge graph in D3-compatible node-link format.

```jsonc
{
  "generated": "2026-04-19T14:30:00Z",
  "stats": {
    "node_count": 150,
    "edge_count": 87,
    "domain_count": 2,
    "orphan_count": 5
  },
  "nodes": [
    {
      "id": "successor-representation",
      "title": "Successor Representation for Spatial Reasoning",
      "epistemic_type": "finding",
      "confidence": 3,
      "source_tier": 2,
      "lifecycle": "growing",
      "domains": ["intelligent-spatial-worlds"],
      "content_categories": ["spatial-reasoning", "reinforcement-learning"],
      "created": "2026-04-19",
      "last_verified": "2026-04-19",
      "connection_count": 3,              // precomputed for UI sizing
      "tags": ["predictive-maps"]
    }
  ],
  "edges": [
    {
      "source": "successor-representation",
      "target": "world-model-convergence",
      "type": "extends",
      "note": "SR provides the predictive map WM convergence requires"
    }
  ]
}
```

**D3 note:** `source` and `target` (not `from`/`to`) to match D3's node-link convention.

---

### 2.2 `views/cards/{id}.json`

Full card detail for the detail panel. One file per card.

```jsonc
{
  "id": "successor-representation",
  "title": "Successor Representation for Spatial Reasoning",
  "epistemic_type": "finding",
  "confidence": 3,
  "source_tier": 2,
  "lifecycle": "growing",
  "domains": ["intelligent-spatial-worlds"],
  "content_categories": ["spatial-reasoning", "reinforcement-learning"],
  "created": "2026-04-19",
  "last_verified": "2026-04-19",
  "author": "researcher",
  "tags": ["predictive-maps", "navigation"],
  "sources": [
    { "type": "paper", "ref": "2501.10100", "title": "Spatial SR for VLAs" }
  ],
  "connections": [
    {
      "target": "world-model-convergence",
      "target_title": "World Model Convergence Thesis",   // denormalized for UI
      "relation": "extends",
      "note": "SR provides the predictive map WM convergence requires",
      "direction": "outgoing"             // "outgoing" = this card → target; "incoming" = target → this card
    }
  ],
  "body": {
    "summary": "Markdown text...",
    "evidence": "Markdown text...",
    "significance": "Markdown text...",
    "open_questions": "Markdown text or null"
  },
  "decay": {
    "days_since_referenced": 5,
    "flagged": false
  }
}
```

---

### 2.3 `views/landscape.json`

Domain coverage and cluster analysis.

```jsonc
{
  "generated": "2026-04-19T14:30:00Z",
  "domains": [
    {
      "id": "intelligent-spatial-worlds",
      "name": "Intelligent Spatial Worlds",
      "status": "active",
      "stats": {
        "total_cards": 150,
        "by_lifecycle": { "seed": 30, "growing": 80, "mature": 35, "archived": 5 },
        "by_confidence": { "1": 10, "2": 25, "3": 60, "4": 40, "5": 15 },
        "by_type": { "finding": 50, "concept": 30, "paper": 25, "claim": 15, "gap": 10, "method": 8, "theme": 5, "question": 4, "provocation": 2, "connection": 1 },
        "orphan_count": 5,
        "avg_confidence": 3.1,
        "stale_count": 8
      },
      "categories": [
        {
          "id": "spatial-reasoning",
          "card_count": 25,
          "avg_confidence": 3.2,
          "latest_card_date": "2026-04-18"
        }
      ],
      "gaps": [
        {
          "card_id": "gap-multiagent-spatial",
          "title": "No benchmarks for multi-agent spatial coordination",
          "confidence": 2
        }
      ],
      "research": {
        "search_seeds_version": 9,
        "last_cycle": "2026-04-19T06:00:00Z",
        "next_cycle": "2026-04-19T07:00:00Z",
        "total_refs": 71
      }
    }
  ]
}
```

---

### 2.4 `views/agents-status.json`

Current agent state for the UI agent panels.

```jsonc
{
  "generated": "2026-04-19T14:30:00Z",
  "agents": [
    {
      "id": "construct",
      "name": "CONSTRUCT",
      "role": "Orchestrator and thinking partner",
      "status": "idle",                   // enum: idle | busy | error | disabled
      "version": "0.1",                   // from IDENTITY.md evolution level
      "last_action": {
        "ts": "2026-04-19T14:25:00Z",
        "action": "chat_response",
        "detail": "Answered question about SR-spatial connection"
      },
      "stats": {
        "sessions_today": 3,
        "actions_today": 12
      }
    },
    {
      "id": "curator",
      "name": "Curator",
      "role": "Knowledge graph maintenance",
      "status": "idle",
      "version": "0.1",
      "last_action": {
        "ts": "2026-04-19T14:20:00Z",
        "action": "integrity_check",
        "detail": "All cards valid, 2 orphans flagged"
      },
      "stats": {
        "promotions_today": 2,
        "flags_today": 3,
        "checks_today": 1
      }
    }
  ]
}
```

---

### 2.5 `views/events-recent.json`

Rolling window of recent events for the activity timeline.

```jsonc
{
  "generated": "2026-04-19T14:30:00Z",
  "window_days": 7,
  "event_count": 156,
  "events": [
    {
      "ts": "2026-04-19T14:30:00.000Z",
      "agent": "curator",
      "action": "promote_card",
      "target": "successor-representation",
      "detail": "seed → growing; confidence 2, 1 connection",
      "result": "success"
    }
    // ... most recent first
  ]
}
```

Same event schema as `log/events.jsonl` entries, wrapped in an array with metadata.

---

### 2.6 `views/responses.json`

Agent responses to UI inbox actions. Keyed by action ID for the React UI to match responses to requests.

```jsonc
{
  "generated": "2026-04-19T14:30:00Z",
  "responses": [
    {
      "action_id": "action-1713536400",   // matches inbox filename
      "type": "confirm",                  // enum: confirm | confirm_with_followup | question | error | info
      "agent": "curator",
      "message": "Card promoted successfully.",
      "options": null,                    // array of strings if type = confirm_with_followup or question
      "ts": "2026-04-19T14:30:05Z"
    },
    {
      "action_id": "action-1713536415",
      "type": "confirm_with_followup",
      "agent": "curator",
      "message": "Archived. 2 connected cards now orphaned.",
      "options": ["Review orphans", "Dismiss"],
      "ts": "2026-04-19T14:30:10Z"
    }
  ]
}
```

---

## 3. Transient Layer

### 3.1 `inbox/action-{timestamp}.json`

User action queue from React UI. Written by UI. Consumed by agents, then moved to `log/processed/` or deleted.

```jsonc
{
  "id": "action-1713536400",             // unique, timestamp-based
  "ts": "2026-04-19T14:00:00Z",          // ISO 8601
  "source": "ui",                         // enum: ui | chat | cli
  "type": "promote",                      // action type — see catalog below
  "target": "draft-card-id",             // primary artifact
  "params": {},                           // action-specific parameters (see below)
  "user_note": "Looks solid, promote it"  // optional human comment
}
```

**Action type catalog:**

| Type | Target | Params | Agent |
|------|--------|--------|-------|
| `promote` | card ID | `{}` | Curator |
| `archive` | card ID | `{ "reason": "superseded" }` | Curator |
| `flag` | card ID | `{ "reason": "stale" }` | Curator |
| `comment` | card ID | `{ "text": "Needs update on methods" }` | Curator |
| `connect` | card ID | `{ "target_card": "other-id" }` | Curator |
| `edit` | card ID | `{ "changes": { "confidence": 4 } }` | Curator |
| `config` | config file path | `{ "changes": { ... } }` | CONSTRUCT |
| `search_adjust` | domain ID | `{ "instructions": "Shift focus to X" }` | CONSTRUCT |
| `research_trigger` | domain ID | `{}` | Researcher |

---

## 4. Schema Validation in Code

All schemas above will have corresponding validation in `src/construct/schemas/`:

```
src/construct/schemas/
├── __init__.py
├── card.py               # Card frontmatter validation (pydantic or dataclass)
├── connections.py         # connections.json validation
├── config.py              # domains.yaml, model-routing.yaml, governance.yaml
├── events.py              # events.jsonl line validation
├── inbox.py               # inbox action validation
├── publish.py             # All views/*.json validation
└── search_seeds.py        # search-seeds.json validation
```

Implementation approach: **Pydantic v2 models** — they generate JSON Schema, validate at runtime, and provide TypeScript-compatible type definitions via `pydantic-to-typescript` (for React UI type safety).

Contract tests in `tests/contract/` validate that:
1. The test fixtures conform to these schemas
2. The views step output conforms to these schemas
3. Agent-written files conform to these schemas

---

## 5. Schema Versioning

| Schema | Version | Date |
|--------|---------|------|
| Knowledge card | 0.1.0 | 2026-04-19 |
| connections.json | 0.1.0 | 2026-04-19 |
| domains.yaml | 0.1.0 | 2026-04-19 |
| model-routing.yaml | 0.1.0 | 2026-04-19 |
| governance.yaml | 0.1.0 | 2026-04-19 |
| log/events.jsonl | 0.1.0 | 2026-04-19 |
| inbox/action-*.json | 0.1.0 | 2026-04-19 |
| views/graph.json | 0.1.0 | 2026-04-19 |
| views/cards/*.json | 0.1.0 | 2026-04-19 |
| views/landscape.json | 0.1.0 | 2026-04-19 |
| views/agents-status.json | 0.1.0 | 2026-04-19 |
| views/events-recent.json | 0.1.0 | 2026-04-19 |
| views/responses.json | 0.1.0 | 2026-04-19 |
| search-seeds.json | 0.1.0 | 2026-04-19 |
| refs/*.json | 0.1.0 | 2026-04-19 |
