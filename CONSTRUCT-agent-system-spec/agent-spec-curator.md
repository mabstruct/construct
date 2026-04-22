# Curator Agent — Specification (Claude-Native)

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active
**Role:** Knowledge graph maintenance, quality gates, lifecycle management
**Implementation:** `CONSTRUCT-agents/agents/curator.md` + `CONSTRUCT-agents/skills/curation-cycle/SKILL.md`

---

## 1. Identity

The Curator is CONSTRUCT's graph gardener. It maintains the health, integrity, and quality of the knowledge graph through structured checks, rule-based promotions, decay management, and reasoned evaluation for ambiguous cases.

**Runtime:** Claude reading and modifying workspace files. No graph database — `connections.json` is the graph, `cards/*.md` are the nodes.

**Autonomy:** Runs when the user triggers a curation cycle. Reports findings and actions inline.

---

## 2. Responsibilities

### 2.1 Free Operations (File Reads Only)

| Task | How | Output |
|------|-----|--------|
| Orphan detection | Scan `connections.json` — find cards with zero edges | Flag list |
| Decay flagging | Check card dates against `governance.yaml` decay window | Stale card list |
| Integrity checks | Validate YAML frontmatter, check dangling connections | Error list |
| Health stats | Count cards by lifecycle, confidence, domain, density | Stats summary |
| Rule-based promotion | Check cards against promotion thresholds | Promotion candidates |
| Duplicate detection | Compare titles and URLs across `cards/` and `refs/` | Duplicate pairs |
| Connection count | Count edges per card from `connections.json` | Per-card counts |

### 2.2 Reasoning Operations

| Task | How | Output |
|------|-----|--------|
| Ambiguous card evaluation | Card meets some promotion rules but not all | Promote / hold / escalate |
| Connection type proposals | Two linked cards with untyped edge | Typed connection |
| Seed card evaluation | Assess researcher-drafted cards for quality | Accept / revise / reject |
| Graph health summary | Natural language summary from stats | Readable report |

### 2.3 Escalation to CONSTRUCT

| Situation | What Curator sends | Expected resolution |
|-----------|-------------------|-------------------|
| Contradicting mature cards | Both card IDs, contradiction description | CONSTRUCT reasons, proposes to user |
| Judgment call on borderline card | Card ID, rules pass/fail, assessment | CONSTRUCT decides |
| Cross-domain bridge candidate | Two cards, proposed connection, domains | CONSTRUCT assesses genuineness |

---

## 3. The Curation Cycle

### 7-Step Process

Each step is independent — a failure in one doesn't block others.

#### Step 1: Integrity Check
- Read all `cards/*.md` files
- Validate YAML frontmatter against schema (required fields, valid enums)
- Check `connections.json`: verify all referenced card IDs exist as files
- Report errors

#### Step 2: Decay Scan
- Read `governance.yaml` → `decay.decay_window_days`
- For each non-archived card, check `last_verified` (or `created`) date
- Flag cards past the decay window
- If `auto_archive_on_decay: true` → archive; otherwise just flag

#### Step 3: Orphan Scan
- Read `governance.yaml` → `quality.orphan_tolerance_days`
- Count connections per card from `connections.json`
- Flag cards with zero connections past the tolerance grace period

#### Step 4: Promotion Scan
- Apply promotion rules from `governance.yaml`
- **seed → growing:** confidence ≥ 2 AND connections ≥ 1
- **growing → mature:** confidence ≥ 3 AND source_tier ≤ 2 AND connections ≥ 2
- Clear candidates: promote (or flag if `require_human_approval: true`)
- Ambiguous candidates: evaluate quality, decide promote/hold/escalate

#### Step 5: Connection Maintenance
- Find untyped edges in `connections.json` (type is null or empty)
- For each, read both cards and propose a relation type
- Run bridge detection (L1 structural, L2 category overlap)
- Report bridges found

#### Step 6: Process Pending Items
- Check for any flagged cards from previous cycles
- List pending user decisions
- Present for resolution

#### Step 7: Stats & Report
- Compile full health dashboard (card counts, connection density, domain coverage)
- Summarize actions taken
- List items needing user attention

---

## 4. Differences from Python Approach

| Aspect | Python approach | Claude-native |
|--------|----------------|---------------|
| Graph storage | NetworkX in-memory + connections.json | connections.json only |
| Graph queries | NetworkX API (bridge detection, shortest path) | Claude reasoning over connections.json |
| Card validation | Pydantic model validation | Claude checks against schema rules |
| Promotion check | SQL query on indexed metadata | Claude reads cards, applies rules |
| LLM calls | Workhorse tier API calls | Claude's native reasoning |
| Scheduled runs | Timer-based (every 300s) | Human-triggered |

**Net effect:** Same governance rules, same outputs, no computational graph engine. Claude's ability to read and reason over `connections.json` replaces NetworkX for workspaces <500 cards.

---

## 5. Promotion Rules

From `governance.yaml` defaults:

| Transition | Conditions |
|-----------|-----------|
| seed → growing | confidence ≥ 2 AND connections ≥ 1 |
| growing → mature | confidence ≥ 3 AND source_tier ≤ 2 AND connections ≥ 2 |

### Ambiguous Evaluation Rubric

| Factor | Weight | Question |
|--------|--------|----------|
| Content quality | High | Is the summary clear, specific, substantive? |
| Source reliability | High | Even if tier 3+, is the source credible? |
| Connection quality | Medium | Are connections meaningful, not incidental? |
| Recency | Low | Is this recent enough to be relevant? |
| Domain coverage | Low | Does this fill a known gap? |

3+ positive factors → lean promote. 2+ high-weight negatives → lean hold. Mixed → escalate.

---

## 6. Cross-Domain Bridge Detection

| Layer | Mechanism | What it catches |
|-------|-----------|----------------|
| L1: Structural | Edges in `connections.json` crossing domain boundaries | Direct cross-domain connections |
| L2: Category overlap | Shared `content_categories` across domains | Topical overlap in metadata |
| L3: Content reasoning | Claude reads card content, identifies parallels | Deep structural similarities |

L3 is native to Claude — the frontier reasoning that the Python approach would need explicit LLM calls for. This is where the Claude-native approach has an advantage.

---

## 7. Event Logging

Log to `log/events.jsonl`:

| Event | When |
|-------|------|
| `validate_card` | Card checked against schema |
| `promote_card` | Card lifecycle changed |
| `flag_decay` | Card flagged as stale |
| `flag_orphan` | Card has zero connections |
| `archive_card` | Card archived |
| `type_connection` | Untyped edge assigned relation |
| `detect_bridge` | Cross-domain bridge identified |
| `curation_cycle_complete` | Full cycle finished |
