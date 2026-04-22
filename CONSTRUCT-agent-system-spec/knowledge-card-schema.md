# CONSTRUCT Agent System — Canonical Knowledge Card Schema

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active — canonical. Identical to CONSTRUCT-spec version for workspace interoperability.

---

## 1. Purpose

This is the single source of truth for knowledge card format. All agent roles, skills, and templates consume cards in this format. This schema is intentionally identical to the Python approach to enable workspace sharing.

---

## 2. Format

**YAML frontmatter + Markdown body.** Standard `---` delimiters. Parseable by any YAML library.

---

## 3. Card File Schema

**Location:** `cards/{id}.md`
**Filename:** equals the `id` field (kebab-case) + `.md`

### 3.1 YAML Frontmatter

```yaml
---
# === REQUIRED FIELDS ===
id: successor-representation-spatial          # kebab-case, globally unique, equals filename
title: "Successor Representation for Spatial Reasoning"
epistemic_type: finding                       # see §4
created: 2026-04-23                           # ISO date
confidence: 3                                 # integer 1–5
source_tier: 2                                # integer 1–5
domains:                                      # list, ≥1 entry, references domains.yaml
  - intelligent-spatial-worlds

# === RECOMMENDED FIELDS ===
content_categories:                           # domain-specific taxonomy labels
  - spatial-reasoning
  - reinforcement-learning
lifecycle: growing                            # seed | growing | mature | archived (default: seed)
sources:
  - type: paper                               # paper | url | digest | observation | conversation
    ref: "2501.10100"
    title: "Spatial SR for VLAs"
connects_to:
  - target: world-model-convergence
    relation: extends
    note: "SR provides the predictive map WM convergence requires"
tags:
  - predictive-maps

# === OPTIONAL FIELDS ===
author: researcher                            # construct | curator | researcher | human
last_verified: 2026-04-23
promoted_from: "digest-2026-04-15"
supersedes: old-card-id
---
```

### 3.2 Markdown Body

```markdown
## Summary
1–3 paragraphs. What is this and why does it matter.

## Evidence
Citations, data points, paper references.

## Significance
Why this matters in context. What it connects to.

## Open Questions
What is unresolved. What would change confidence.
```

`## Summary` is required. Other sections are recommended conventions.

### 3.3 Minimal Valid Card

```yaml
---
id: example-minimal
title: "Minimal Example Card"
epistemic_type: concept
created: 2026-04-23
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

| Type | Purpose |
|------|---------|
| `finding` | A factual result or observation |
| `claim` | An assertion that may be contested |
| `concept` | A defined term or abstraction |
| `method` | A technique, algorithm, or process |
| `paper` | A reference to a specific publication |
| `theme` | A recurring pattern across multiple cards |
| `gap` | An identified absence of knowledge |
| `provocation` | A speculative or contrarian idea |
| `question` | An open inquiry awaiting investigation |
| `connection` | A meta-card documenting a non-obvious link |

## 5. Confidence Levels (1–5)

| Level | Label | Meaning |
|-------|-------|---------|
| 1 | Speculative | Hunch, hypothesis, unverified |
| 2 | Emerging | Early evidence, single source |
| 3 | Supported | Multiple sources, consistent evidence |
| 4 | Established | Strong evidence, peer-reviewed, confirmed |
| 5 | Foundational | Field consensus, axiomatic |

## 6. Source Tiers (1–5)

| Tier | Label | Examples |
|------|-------|---------|
| 1 | Peer-reviewed | Journal, top conference |
| 2 | Preprint/report | arXiv, institutional report |
| 3 | Expert content | Expert blog, talk, interview |
| 4 | Community | Wikipedia, tutorial, forum |
| 5 | Unverified | Social media, hearsay |

## 7. Connection Types

| Relation | Meaning | Symmetric? |
|----------|---------|-----------|
| `supports` | A provides evidence for B | No |
| `contradicts` | A conflicts with B | Yes |
| `extends` | A builds on B | No |
| `parallels` | Structural similarity | Yes |
| `requires` | A depends on B | No |
| `enables` | A makes B possible | No |
| `challenges` | A complicates B | No |
| `inspires` | A motivated B | No |
| `gap-for` | A identifies what B is missing | No |

## 8. Lifecycle States

```
seed → growing → mature → archived
```

| State | Meaning |
|-------|---------|
| seed | Newly created, minimal validation |
| growing | Gaining evidence and connections |
| mature | Well-evidenced, connected, reliable |
| archived | No longer active |
