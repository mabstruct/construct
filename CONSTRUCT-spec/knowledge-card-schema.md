# CONSTRUCT — Canonical Knowledge Card Schema

**Version:** 0.1.0
**Date:** 2026-04-19
**Status:** Draft — canonical. Supersedes `knowledge/KNOWLEDGE_SPEC.md` and `specs/zettelkasten-kg-spec.md`

---

## 1. Purpose

This is the single source of truth for knowledge card format in CONSTRUCT. All agents, the graph engine, the publish step, and the UI consume cards in this format. Prior specs (MABSTRUCT's `KNOWLEDGE_SPEC.md`, the zettelkasten-kg-spec) are historical context; this document governs.

---

## 2. Format Decision

**YAML frontmatter + Markdown body.**

The existing MABSTRUCT cards use inline bold metadata (`**ID:** value`). This is human-readable but not machine-parseable without fragile regex. CONSTRUCT switches to standard YAML frontmatter (`---` delimiters) as proposed by the zettelkasten spec. This is parseable by any YAML library, diffable in git, and the dominant convention in static-site generators and knowledge tools.

**Migration:** Existing MABSTRUCT cards will be migrated by a one-time script (`scripts/migrate-cards.py`). Not a v0.1 blocker — CONSTRUCT starts with an empty `cards/` directory. The migration is only needed if MABSTRUCT content is imported.

---

## 3. Card File Schema

**Location:** `cards/{id}.md`
**Filename:** equals the `id` field (kebab-case) + `.md`

### 3.1 YAML Frontmatter

```yaml
---
# === REQUIRED FIELDS ===

id: successor-representation-spatial          # kebab-case, globally unique, equals filename
title: "Successor Representation for Spatial Reasoning"  # human-readable, quoted if contains colons
epistemic_type: finding                       # enum — see §4
created: 2026-04-19                           # ISO date (YYYY-MM-DD)
confidence: 3                                 # integer 1–5, see §5
source_tier: 2                                # integer 1–5, see §6
domains:                                      # list, ≥1 entry, references domains.yaml
  - intelligent-spatial-worlds

# === RECOMMENDED FIELDS ===

content_categories:                           # list, domain-specific taxonomy labels
  - spatial-reasoning
  - reinforcement-learning
lifecycle: growing                            # enum: seed | growing | mature | archived
                                              # default: seed
sources:                                      # list of source references
  - type: paper                               # enum: paper | url | digest | observation | conversation
    ref: "2501.10100"                         # arXiv ID, URL, digest ID, or free text
    title: "Spatial SR for VLAs"              # optional display title
  - type: url
    ref: "https://example.com/blog-post"

connects_to:                                  # list of typed edges (also stored in connections.json)
  - target: world-model-convergence           # target card ID
    relation: extends                         # enum — see §7
    note: "SR provides the predictive map WM convergence requires"

tags:                                         # list, free-form kebab-case
  - predictive-maps
  - navigation

# === OPTIONAL FIELDS ===

author: researcher                            # who created: construct | curator | researcher | human
last_verified: 2026-04-19                     # ISO date — last time a human or curator confirmed
promoted_from: "digest-2026-04-15"            # free text — provenance of promotion
supersedes: old-card-id                       # card ID this replaces (old card gets archived)
---
```

### 3.2 Markdown Body

```markdown
## Summary

1–3 paragraphs. What is this and why does it matter.

## Evidence

Citations, data points, paper references supporting this card.
Use markdown links where possible. Reference source entries from frontmatter.

## Significance

Why this matters in context. What it connects to. What it changes.

## Open Questions

Optional. What is unresolved. What would increase or decrease confidence.
```

**Body sections are conventions, not enforced schema.** The `## Summary` section is required; others are recommended. Cards may include additional sections (e.g., `## Method` for method-type cards, `## Claim` for claim-type cards).

### 3.3 Minimal Valid Card

The smallest valid card:

```yaml
---
id: example-minimal
title: "Minimal Example Card"
epistemic_type: concept
created: 2026-04-19
confidence: 1
source_tier: 5
domains:
  - example-domain
---

## Summary

This is a seed card with minimal metadata.
```

---

## 4. Epistemic Types

The `epistemic_type` field answers: *what role does this card play in the knowledge graph?*

| Type | Purpose | Example |
|------|---------|---------|
| `finding` | A factual result or observation | "GPT-4V scores 87% on spatial reasoning benchmarks" |
| `claim` | An assertion that may be contested | "Transformer attention is sufficient for spatial reasoning" |
| `concept` | A defined term or abstraction | "Successor representation" |
| `method` | A technique, algorithm, or process | "RLHF fine-tuning pipeline" |
| `paper` | A reference to a specific publication | "Driess et al. 2023 — PaLM-E" |
| `theme` | A recurring pattern across multiple cards | "Embodiment as grounding for language models" |
| `gap` | An identified absence of knowledge | "No benchmarks for multi-agent spatial coordination" |
| `provocation` | A speculative or contrarian idea | "What if world models don't need vision at all?" |
| `question` | An open inquiry awaiting investigation | "How does the SR generalize to continuous state spaces?" |
| `connection` | A meta-card documenting a non-obvious link | "Topology ↔ robotics: shared structure in path planning" |

Enum is fixed in CONSTRUCT core. Adding new types requires a schema version bump.

---

## 5. Confidence Levels

| Level | Label | Meaning | Typical source tier range |
|-------|-------|---------|--------------------------|
| 1 | Speculative | Hunch, hypothesis, unverified observation | 4–5 |
| 2 | Emerging | Early evidence, single source, initial research | 3–5 |
| 3 | Supported | Multiple independent sources, consistent evidence | 2–3 |
| 4 | Established | Strong evidence, peer-reviewed, multiple confirmations | 1–2 |
| 5 | Foundational | Field consensus, textbook knowledge, axiomatic | 1 |

Confidence is assigned by the Curator (rule-based or LLM-assisted) and can be overridden by human.

---

## 6. Source Tiers

| Tier | Label | Examples |
|------|-------|---------|
| 1 | Peer-reviewed | Published in journal / top conference proceedings |
| 2 | Preprint / technical report | arXiv, institutional reports, official standards |
| 3 | Expert content | Blog posts by domain experts, talks, interviews |
| 4 | Community / secondary | Wikipedia, tutorials, forum discussions, newsletters |
| 5 | Unverified | Social media, hearsay, AI-generated without sources |

---

## 7. Connection Types (Edge Relations)

| Relation | Meaning | Symmetric? |
|----------|---------|-----------|
| `supports` | A provides evidence for B | No |
| `contradicts` | A undermines or conflicts with B | Yes |
| `extends` | A builds on or refines B | No |
| `parallels` | A and B share structural similarity across domains | Yes |
| `requires` | A depends on B being true/available | No |
| `enables` | A makes B possible or practical | No |
| `challenges` | A complicates or raises questions about B | No |
| `inspires` | A motivated the creation or thinking behind B | No |
| `gap-for` | A identifies what B is missing | No |

Edges are stored in two places:
1. **In-card** (`connects_to` frontmatter) — for authoring convenience and card portability
2. **In `connections.json`** — the authoritative graph file used by the graph engine

The Curator is responsible for keeping these in sync. On conflict, `connections.json` wins.

---

## 8. Lifecycle States

```
seed ──→ growing ──→ mature ──→ archived
                        │
                        └──→ archived (decay or superseded)
```

| State | Meaning | Transition trigger |
|-------|---------|-------------------|
| `seed` | Newly created, not yet validated | Default on creation |
| `growing` | Has some evidence/connections, actively maintained | Curator promotes when: confidence ≥ 2, ≥ 1 connection |
| `mature` | Well-established, high confidence, richly connected | Curator promotes when: confidence ≥ 3, source_tier ≤ 2, ≥ 2 connections |
| `archived` | No longer active — superseded, decayed, or retracted | Curator archives when: unreferenced for decay_window days, or superseded |

Archived cards are moved to `cards/archive/` (never deleted — preserves history).

---

## 9. Decay Rules

| Rule | Default | Configurable in `governance.yaml` |
|------|---------|----------------------------------------|
| Decay window | 28 days unreferenced | `decay_window_days: 28` |
| Decay action | Flag for review (Curator surfaces to human) | — |
| Auto-archive | Never (human must approve) | `auto_archive_on_decay: false` |

"Referenced" means: cited in a new card, manually viewed/edited, or included in a synthesis output.

---

## 10. Validation Rules

These are enforced by `construct validate` CLI command and by the Curator on every write:

| Rule | Severity |
|------|----------|
| `id` must be kebab-case, ≤80 chars, globally unique | Error |
| `id` must equal filename (without `.md`) | Error |
| `epistemic_type` must be a valid enum value | Error |
| `confidence` must be integer 1–5 | Error |
| `source_tier` must be integer 1–5 | Error |
| `domains` must have ≥1 entry, each referencing a domain in `domains.yaml` | Error |
| `created` must be valid ISO date | Error |
| `lifecycle` must be valid enum if present | Error |
| `connects_to[].target` must reference an existing card ID | Warning (may be pending) |
| `connects_to[].relation` must be a valid enum value | Error |
| `## Summary` section must exist in body | Warning |
| Card with `confidence ≥ 3` should have `source_tier ≤ 3` | Warning |
| Card with `lifecycle: mature` should have `confidence ≥ 3` | Warning |

---

## 11. Schema Versioning

The card schema is versioned via this document. The version is **not stored in each card file** — it is a system-level property.

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-04-19 | Initial canonical schema |

When the schema changes, a migration script is provided in `scripts/migrations/`. Cards written under prior versions remain valid unless the migration is breaking (which requires a major version bump and explicit migration).
