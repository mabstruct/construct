# CONSTRUCT — SQLite Schema (`db/construct.db`)

**Version:** 0.1.0
**Date:** 2026-04-21
**Status:** Draft — canonical reference for the persistent index layer
**Related:** [construct-data-schemas.md](construct-data-schemas.md), [knowledge-card-schema.md](knowledge-card-schema.md), [construct-prd.md](construct-prd.md) §3

---

## 1. Purpose

`db/construct.db` is CONSTRUCT's **query layer** — the single place agents and the views heartbeat go when they need to find, filter, aggregate, or full-text search anything. It indexes data from the source of truth (cards, connections, domains, refs, events) into a form optimized for the queries the system actually runs.

### Invariants

- **Always rebuildable.** `construct rebuild` drops all tables and repopulates from the file-based source of truth. Losing `db/construct.db` costs rebuild time, never data.
- **Never authoritative.** The markdown files, YAML configs, and JSONL logs are the source of truth. The database is a derived index.
- **Single-writer at a time.** The indexer holds a write lock during rebuild. Agents and the heartbeat read concurrently via WAL mode.
- **Schema-versioned.** A `meta` table tracks the schema version. The indexer checks this on startup and migrates or rebuilds as needed.

---

## 2. Pragmas

```sql
PRAGMA journal_mode = WAL;          -- concurrent reads during writes
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;         -- 5s wait on lock contention
```

---

## 3. Tables

### 3.1 `meta`

Schema version and rebuild state. Single row.

```sql
CREATE TABLE meta (
    schema_version  INTEGER NOT NULL,   -- bumped on breaking schema change
    last_rebuild    TEXT    NOT NULL,    -- ISO 8601 timestamp
    card_count      INTEGER NOT NULL DEFAULT 0,
    connection_count INTEGER NOT NULL DEFAULT 0,
    ref_count       INTEGER NOT NULL DEFAULT 0,
    event_count     INTEGER NOT NULL DEFAULT 0
);
```

### 3.2 `cards`

One row per knowledge card. Indexed columns match the filter/sort patterns used by Curator, views heartbeat, and CLI.

```sql
CREATE TABLE cards (
    id              TEXT PRIMARY KEY,   -- card filename stem (e.g. "neural-scaling-laws")
    title           TEXT NOT NULL,
    epistemic_type  TEXT NOT NULL,       -- finding|claim|concept|method|paper|theme|gap|provocation|question|connection
    confidence      INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    source_tier     INTEGER NOT NULL CHECK (source_tier BETWEEN 1 AND 5),
    lifecycle       TEXT NOT NULL,       -- seed|growing|mature|archived
    created         TEXT NOT NULL,       -- ISO 8601 date
    updated         TEXT,                -- ISO 8601 date, NULL if never updated
    last_referenced TEXT,                -- ISO 8601 date, NULL if never referenced
    body_length     INTEGER NOT NULL DEFAULT 0,  -- character count of card body
    source_count    INTEGER NOT NULL DEFAULT 0,  -- number of sources listed
    connection_count INTEGER NOT NULL DEFAULT 0  -- denormalized for fast orphan queries
);

CREATE INDEX idx_cards_type       ON cards (epistemic_type);
CREATE INDEX idx_cards_confidence ON cards (confidence);
CREATE INDEX idx_cards_lifecycle  ON cards (lifecycle);
CREATE INDEX idx_cards_created    ON cards (created);
CREATE INDEX idx_cards_referenced ON cards (last_referenced);
CREATE INDEX idx_cards_orphans    ON cards (connection_count) WHERE connection_count = 0;
```

### 3.3 `card_domains`

Many-to-many: cards belong to one or more domains.

```sql
CREATE TABLE card_domains (
    card_id     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL,           -- key from domains.yaml
    PRIMARY KEY (card_id, domain)
);

CREATE INDEX idx_card_domains_domain ON card_domains (domain);
```

### 3.4 `card_categories`

Many-to-many: cards have content category tags (domain-specific taxonomy).

```sql
CREATE TABLE card_categories (
    card_id     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    category    TEXT NOT NULL,           -- from domain's content_categories
    PRIMARY KEY (card_id, category)
);

CREATE INDEX idx_card_categories_cat ON card_categories (category);
```

### 3.5 `card_tags`

Freeform tags on cards (distinct from typed categories).

```sql
CREATE TABLE card_tags (
    card_id     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL,
    PRIMARY KEY (card_id, tag)
);

CREATE INDEX idx_card_tags_tag ON card_tags (tag);
```

### 3.6 `connections`

Graph edges. Mirrors `connections.json` but queryable.

```sql
CREATE TABLE connections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    from_card   TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    to_card     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,           -- supports|contradicts|extends|parallels|requires|enables|challenges|inspires|gap-for
    note        TEXT,
    created     TEXT NOT NULL,           -- ISO 8601 date
    created_by  TEXT NOT NULL,           -- curator|human|researcher
    UNIQUE (from_card, to_card, type)
);

CREATE INDEX idx_connections_from ON connections (from_card);
CREATE INDEX idx_connections_to   ON connections (to_card);
CREATE INDEX idx_connections_type ON connections (type);
```

### 3.7 `refs`

Reference library. One row per ingested source (paper, URL, report). Mirrors `refs/{id}.json`.

```sql
CREATE TABLE refs (
    id              TEXT PRIMARY KEY,        -- ref filename stem
    title           TEXT NOT NULL,
    url             TEXT,                    -- canonical URL
    open_access_url TEXT,                    -- direct link to full text (nullable)
    source_type     TEXT,                    -- paper|blog|report|talk|book|dataset|code
    authors         TEXT,                    -- JSON array of {name, affiliations[]}
    year            INTEGER,                 -- publication year
    publication_date TEXT,                   -- full ISO 8601 date when available
    venue           TEXT,                    -- where published
    tier            INTEGER CHECK (tier BETWEEN 1 AND 5),  -- source tier
    domain          TEXT,                    -- which domain discovered this ref
    abstract        TEXT,                    -- full abstract
    tldr            TEXT,                    -- one-sentence summary (API or LLM)
    fields_of_study TEXT,                    -- JSON array from API classification
    -- impact
    citation_count           INTEGER,
    influential_citation_count INTEGER,      -- S2: meaningful engagements
    reference_count          INTEGER,        -- how many papers this one cites
    -- provenance
    retrieval_query TEXT,                    -- search term that found this
    search_seed_id  TEXT,                    -- cluster from search-seeds.json
    discovery_session TEXT,                  -- session ID
    -- extraction state
    extraction_status TEXT NOT NULL DEFAULT 'pending',  -- pending|partial|complete|failed
    relevance_score   REAL,                 -- 0–1, Researcher assessment
    key_findings      TEXT,                 -- JSON array of extracted findings
    extracted_at      TEXT,                 -- ISO 8601 timestamp
    -- lifecycle
    ingested    TEXT NOT NULL,              -- ISO 8601 timestamp
    status      TEXT NOT NULL DEFAULT 'active',  -- active|superseded|retracted
    superseded_by TEXT                      -- ref ID of newer version (nullable)
);

CREATE INDEX idx_refs_domain      ON refs (domain);
CREATE INDEX idx_refs_url         ON refs (url) WHERE url IS NOT NULL;
CREATE INDEX idx_refs_title       ON refs (title);
CREATE INDEX idx_refs_status      ON refs (extraction_status);
CREATE INDEX idx_refs_relevance   ON refs (relevance_score) WHERE relevance_score IS NOT NULL;
CREATE INDEX idx_refs_citations   ON refs (citation_count) WHERE citation_count IS NOT NULL;
CREATE INDEX idx_refs_seed        ON refs (search_seed_id) WHERE search_seed_id IS NOT NULL;
```

### 3.8 `card_refs`

Many-to-many: cards cite references.

```sql
CREATE TABLE card_refs (
    card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    ref_id  TEXT NOT NULL REFERENCES refs(id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, ref_id)
);

CREATE INDEX idx_card_refs_ref ON card_refs (ref_id);
```

### 3.9 `events`

Indexed subset of `log/events.jsonl`. Only the last N days are indexed (configurable, default 30). Older events live in the JSONL file only.

```sql
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,           -- ISO 8601
    agent       TEXT NOT NULL,           -- construct|curator|researcher|synthesizer|human
    action      TEXT NOT NULL,           -- card.created|card.promoted|card.archived|connection.added|research.cycle|session.start|session.stop|...
    target      TEXT,                    -- card ID, domain, or NULL
    detail      TEXT,                    -- JSON blob for action-specific data
    session_id  TEXT                     -- links events to a session
);

CREATE INDEX idx_events_timestamp ON events (timestamp);
CREATE INDEX idx_events_agent     ON events (agent);
CREATE INDEX idx_events_action    ON events (action);
CREATE INDEX idx_events_target    ON events (target) WHERE target IS NOT NULL;
CREATE INDEX idx_events_session   ON events (session_id) WHERE session_id IS NOT NULL;
```

### 3.10 `domains`

Denormalized domain stats. One row per domain. Rebuilt from cards + domains.yaml.

```sql
CREATE TABLE domains (
    id              TEXT PRIMARY KEY,    -- key from domains.yaml
    name            TEXT NOT NULL,
    status          TEXT NOT NULL,       -- active|paused|archived
    card_count      INTEGER NOT NULL DEFAULT 0,
    avg_confidence  REAL,
    oldest_card     TEXT,                -- ISO 8601 date
    newest_card     TEXT,                -- ISO 8601 date
    orphan_count    INTEGER NOT NULL DEFAULT 0,
    stale_count     INTEGER NOT NULL DEFAULT 0   -- cards past decay window
);
```

---

## 4. Full-Text Search (FTS5)

### 4.1 `cards_fts`

Full-text index over card content. Used by CLI search, Curator, and the views heartbeat for search-based views.

```sql
CREATE VIRTUAL TABLE cards_fts USING fts5(
    id,                                  -- card ID (unindexed, for joining)
    title,                               -- card title
    body,                                -- full markdown body (stripped of YAML frontmatter)
    domains,                             -- space-separated domain keys
    categories,                          -- space-separated category tags
    tags,                                -- space-separated freeform tags
    content = 'cards',                   -- content table (external content)
    content_rowid = 'rowid',
    tokenize = 'porter unicode61'        -- stemming + unicode normalization
);
```

**Triggers to keep FTS in sync with `cards` table:**

```sql
CREATE TRIGGER cards_ai AFTER INSERT ON cards BEGIN
    INSERT INTO cards_fts (rowid, id, title, body, domains, categories, tags)
    VALUES (new.rowid, new.id, new.title, '', '', '', '');
END;

CREATE TRIGGER cards_ad AFTER DELETE ON cards BEGIN
    INSERT INTO cards_fts (cards_fts, rowid, id, title, body, domains, categories, tags)
    VALUES ('delete', old.rowid, old.id, old.title, '', '', '', '');
END;
```

> **Note:** The `body`, `domains`, `categories`, and `tags` fields are populated by the indexer after insert, not by the trigger. The trigger handles the FTS bookkeeping; the indexer does the content extraction. On full rebuild, the FTS table is dropped and recreated.

### 4.2 `refs_fts`

Full-text index over references. Used by Researcher for duplicate detection ("do we already have this paper?").

```sql
CREATE VIRTUAL TABLE refs_fts USING fts5(
    id,
    title,
    authors,
    content = 'refs',
    content_rowid = 'rowid',
    tokenize = 'porter unicode61'
);
```

---

## 5. Query Patterns by Consumer

These are the queries the schema is designed to serve. Each maps to a documented capability.

### Curator Agent

| Query | SQL pattern | Source |
|-------|------------|--------|
| Find orphans | `SELECT id FROM cards WHERE connection_count = 0` | PRD §5, v0.1 scope |
| Find stale cards | `SELECT id FROM cards WHERE last_referenced < date('now', '-N days')` | PRD §5, governance.yaml decay_window |
| Integrity: dangling connections | `SELECT * FROM connections WHERE from_card NOT IN (SELECT id FROM cards) OR to_card NOT IN (SELECT id FROM cards)` | PRD §5 |
| Confidence distribution | `SELECT confidence, COUNT(*) FROM cards GROUP BY confidence` | Product brief §4.1 |
| Domain balance | `SELECT domain, COUNT(*) FROM card_domains GROUP BY domain` | Product brief §4.1 |
| Cards meeting promotion criteria | `SELECT id FROM cards WHERE confidence >= 3 AND source_tier <= 2 AND connection_count >= 1 AND lifecycle = 'seed'` | PRD §5, Curator rule-based auto-promotion |
| Cards needing flagging | `SELECT id FROM cards WHERE source_count = 0 AND confidence = 1 AND created < date('now', '-N days') AND connection_count = 0` | PRD §5 |
| Exact duplicate detection | `SELECT id, title FROM cards WHERE title = ? OR id IN (SELECT card_id FROM card_refs WHERE ref_id IN (SELECT id FROM refs WHERE url = ?))` | PRD §5 |

### Researcher Agent

| Query | SQL pattern | Source |
|-------|------------|--------|
| Duplicate ref check (URL) | `SELECT id FROM refs WHERE url = ?` | PRD §5, dedup |
| Duplicate ref check (title) | `SELECT id FROM refs_fts WHERE refs_fts MATCH ?` | PRD §5, dedup |
| Pending extraction | `SELECT * FROM refs WHERE extraction_status = 'pending' ORDER BY relevance_score DESC` | Extraction pipeline |
| Failed extraction retry | `SELECT * FROM refs WHERE extraction_status = 'failed' ORDER BY ingested DESC` | Retry logic |
| High-impact unprocessed | `SELECT * FROM refs WHERE extraction_status != 'complete' AND citation_count > ? ORDER BY citation_count DESC` | Prioritization |
| Cards in domain | `SELECT c.* FROM cards c JOIN card_domains cd ON c.id = cd.card_id WHERE cd.domain = ?` | Research scoping |
| Recent refs by domain | `SELECT * FROM refs WHERE domain = ? ORDER BY ingested DESC LIMIT ?` | Research history |
| Refs by search seed | `SELECT * FROM refs WHERE search_seed_id = ? ORDER BY ingested DESC` | Seed effectiveness |
| Refs without cards | `SELECT r.* FROM refs r WHERE r.extraction_status = 'complete' AND r.id NOT IN (SELECT ref_id FROM card_refs)` | Missed extraction |

### Views Heartbeat

| Query | SQL pattern | Source |
|-------|------------|--------|
| All cards for graph.json | `SELECT c.*, GROUP_CONCAT(cd.domain) FROM cards c LEFT JOIN card_domains cd ON c.id = cd.card_id GROUP BY c.id` | construct-data-schemas §2.1 |
| All connections for graph.json | `SELECT * FROM connections` | construct-data-schemas §2.1 |
| Domain landscape stats | `SELECT * FROM domains` | construct-data-schemas §2.3 |
| Recent events | `SELECT * FROM events ORDER BY timestamp DESC LIMIT ?` | construct-data-schemas §2.5 |
| Pending responses | *(not in SQLite — reads `views/responses.json` directly)* | |

### CLI

| Command | Query | Source |
|---------|-------|--------|
| `construct status` | `SELECT * FROM meta` + `SELECT * FROM domains` | Development strategy Phase 1 |
| `construct graph stats` | `SELECT COUNT(*) FROM cards` / `connections` / orphan count / bridge detection (NetworkX) | Development strategy Phase 3 |
| Full-text search | `SELECT id, title, rank FROM cards_fts WHERE cards_fts MATCH ? ORDER BY rank LIMIT ?` | NFR: <100ms for ≤10,000 cards |

---

## 6. Indexer Behavior

### Full Rebuild (`construct rebuild`)

1. Drop all tables and FTS virtual tables
2. Create schema (this document)
3. Walk `cards/` — parse each `*.md`, extract YAML frontmatter, insert into `cards`, `card_domains`, `card_categories`, `card_tags`, `cards_fts`
4. Read `connections.json` — insert into `connections`, update `cards.connection_count`
5. Walk `refs/` — parse each `*.json`, insert into `refs`, `card_refs`, `refs_fts`
6. Read `domains.yaml` — compute stats, insert into `domains`
7. Read `log/events.jsonl` — index last N days into `events`
8. Update `meta` row

**Performance target:** Full rebuild of 500-card workspace in <5 seconds (NFR).

### Incremental Update

The indexer can also update a single card or connection without full rebuild:

- **Card changed:** Re-parse the card file, update `cards` row + associated junction tables + FTS
- **Connection added/removed:** Update `connections` table + `cards.connection_count`
- **Event appended:** Insert new row into `events`

The heartbeat can trigger incremental updates when it detects file changes, avoiding full rebuilds on every cycle.

---

## 7. Migration Strategy

Schema version is tracked in `meta.schema_version`.

| Approach | When |
|----------|------|
| **Rebuild from scratch** | Schema version mismatch (breaking change). Drop everything, reindex. Safe because db/ is always rebuildable. |
| **ALTER TABLE migration** | Additive change (new column with default, new index). Applied in-place. |

For v0.1, the rebuild-from-scratch approach is sufficient. Migration scripts become important only when the database grows large enough that rebuild time matters (>10,000 cards).

---

## 8. Schema Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-04-21 | Initial schema: cards, connections, refs, events, domains, FTS5 |
