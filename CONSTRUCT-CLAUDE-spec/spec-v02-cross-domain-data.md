# spec-v02-cross-domain-data — `bridges.json` and Cross-Domain Scoring

**Status:** Draft
**Date:** 2026-05-09
**Companion PRD:** `prd-v02-cross-domain-cluster.md`

This spec defines the first binding implementation contract for the cross-domain feature cluster: the derived global `bridges.json` file and the scoring model used to decide which bridge candidates are visible in the UI.

Where this spec conflicts with the cross-domain PRD, this spec is authoritative for the data contract.

---

## 1. Summary

The first cross-domain views cut needs one global, deterministic, UI-ready file:

- `views/build/data/bridges.json`

This file supports three product surfaces:

1. the landing-page **Cross-Domain** card,
2. the cross-domain comparison view,
3. the future cross-domain graph mode.

The file must include both:

- **confirmed bridges** — already captured as cross-domain edges in workspace `connections.json`
- **strong candidates** — bridge candidates proposed by `bridge-detect` and persisted in machine-readable form

The UI shows **confirmed + strong candidates**. Weak candidates do not surface by default.

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Primary global contract | `data/bridges.json` |
| Scope | Global / cross-workspace data file, used for user-facing cross-domain features |
| Visibility rule | UI shows confirmed bridges and candidates whose derived score passes the `strong` threshold |
| Candidate score inputs | L1 + L2 + L3 signals combined into one normalized score |
| Default UI emphasis | Top bridge candidates |
| Drill-down target | Cross-domain comparison view |
| Comparison granularity | Up to 3 domains in first cut |
| Whole-install graph default | Bridges-only mode (not all nodes at once) |
| Read/write boundary | `bridges.json` is derived only; any apply/confirm action still routes through skills |

---

## 3. Source Inputs

### 3.1 Confirmed Bridges

Confirmed bridges come from existing cross-domain edges already stored in per-workspace `connections.json`.

An edge is a confirmed bridge when:

1. the `from` card and `to` card resolve to cards in different domains/workspaces,
2. the edge exists in canonical workspace state,
3. the edge's relation type is valid under `references/connection-types.md`.

### 3.2 Candidate Bridges

Candidate bridges come from a new machine-readable artifact written by `bridge-detect`:

- `<workspace>/log/bridge-candidates.json`

This file is **not canonical knowledge**. It is a persisted, derived output of the bridge-detection workflow so views can surface candidates without rerunning Claude reasoning inside the browser.

It must be safe to delete and regenerate.

### 3.3 Card and Domain Metadata

`bridges.json` enriches both confirmed bridges and candidates by joining against:

- `cards/` / `cards.json` data
- `domains.yaml` / `domains.json` data
- `connections.json`
- optional event/log metadata where available

---

## 4. File Layout

Add one global file to the hybrid data layout:

```text
views/build/
└── data/
    ├── domains.json
    ├── articles.json
    ├── stats.json
    ├── bridges.json              (new global cross-domain contract)
    └── <workspace>/...
```

This file follows the standard v0.2 envelope:

```jsonc
{
  "schema_version": "0.2.0",
  "generated_at": "2026-05-09T18:00:00Z",
  "build_id": "abcd1234",
  "data": { ... }
}
```

---

## 5. `bridges.json` Schema

```jsonc
{
  "data": {
    "bridges": [
      {
        "id": "cosmology__philosophy-of-mind__observer-models",
        "status": "confirmed",                  // confirmed | candidate
        "strength_band": "strong",              // strong | medium | weak
        "score": 0.82,                           // 0.00–1.00 normalized, rounded to 2 decimals
        "relation": "parallels",
        "domains": ["cosmology", "philosophy-of-mind"],
        "workspaces": ["cosmology", "philosophy-of-mind"],
        "source": {
          "card_id": "observer-effects",
          "workspace_id": "cosmology",
          "title": "Observer effects in cosmological inference",
          "epistemic_type": "finding",
          "confidence": 4,
          "lifecycle": "growing"
        },
        "target": {
          "card_id": "self-model-observer-loop",
          "workspace_id": "philosophy-of-mind",
          "title": "Self-model observer loop",
          "epistemic_type": "theory",
          "confidence": 3,
          "lifecycle": "seed"
        },
        "signals": {
          "l1_structural": true,
          "l2_category_overlap": {
            "present": true,
            "shared_categories": ["observer-models", "inference"],
            "overlap_score": 0.50
          },
          "l3_reasoned": {
            "present": true,
            "summary": "Both cards model an observer-dependent update loop rather than a passive measurement event.",
            "confidence": 0.90
          }
        },
        "provenance": {
          "candidate_source": "bridge-detect",
          "candidate_workspace_id": "cosmology",
          "candidate_generated_at": "2026-05-09T17:21:00Z",
          "confirmed_via_connection": true,
          "connection_workspace_id": "cosmology"
        },
        "why_it_matters": "Shared observer/update structure across physical and cognitive models.",
        "drilldown": {
          "comparison_domains": ["cosmology", "philosophy-of-mind"],
          "source_artifacts_url": "/cosmology/artifacts?card=observer-effects",
          "target_artifacts_url": "/philosophy-of-mind/artifacts?card=self-model-observer-loop"
        }
      }
    ],
    "summary": {
      "totals": {
        "confirmed": 12,
        "strong_candidates": 7,
        "medium_candidates": 14,
        "weak_candidates": 23
      },
      "top_domain_pairs": [
        {
          "domains": ["cosmology", "philosophy-of-mind"],
          "confirmed": 3,
          "strong_candidates": 2,
          "avg_score": 0.79
        }
      ]
    }
  }
}
```

### 5.1 Required Fields

For every bridge entry:

- `id`
- `status`
- `strength_band`
- `score`
- `relation`
- `domains[]`
- `workspaces[]`
- `source{...}`
- `target{...}`
- `signals{...}`
- `provenance{...}`
- `drilldown{...}`

### 5.2 Optional Fields

- `why_it_matters`
- `signals.l2_category_overlap.shared_categories[]`
- `signals.l3_reasoned.summary`
- any future UI-only convenience fields that are strictly derivable from canonical inputs

---

## 6. Candidate Source Contract

`bridge-detect` must persist the latest machine-readable candidate set to:

- `<workspace>/log/bridge-candidates.json`

Minimum candidate shape before global expansion:

```jsonc
{
  "generated_at": "2026-05-09T17:21:00Z",
  "workspace_id": "cosmology",
  "candidates": [
    {
      "source_card_id": "observer-effects",
      "target_card_id": "self-model-observer-loop",
      "target_workspace_id": "philosophy-of-mind",
      "proposed_relation": "parallels",
      "signals": {
        "l1_structural": true,
        "l2_shared_categories": ["observer-models", "inference"],
        "l3_reasoning": "Both cards model an observer-dependent update loop ..."
      }
    }
  ]
}
```

`views-generate-data` is responsible for expanding these raw candidates into the richer `bridges.json` contract.

---

## 7. Scoring Model

Candidate score is normalized to `0.00–1.00` and rounded to 2 decimals.

### 7.1 Component Weights

| Signal | Weight | Rationale |
|---|---|---|
| L1 structural evidence | `0.30` | Existing cross-domain graph structure is meaningful but not sufficient |
| L2 category overlap | `0.20` | Useful weak signal; highest false-positive risk |
| L3 reasoned similarity | `0.50` | Strongest signal; closest to what users mean by a genuine bridge |

### 7.2 Component Rules

#### L1 structural score

- `1.0` if a direct cross-domain edge exists between the two cards
- `0.0` otherwise

#### L2 overlap score

- `0.0` if no shared categories across domains
- else `min(1.0, shared_category_count / 3)`

This caps category overlap at 3 meaningful shared categories.

#### L3 reasoned score

- `1.0` if bridge-detect marked the pair as a **strong candidate** in its persisted output
- `0.6` if marked as **possible candidate**
- `0.0` if there is no persisted L3 candidate reasoning

### 7.3 Final Score

```text
score =
  (0.30 * l1_structural_score) +
  (0.20 * l2_overlap_score) +
  (0.50 * l3_reasoned_score)
```

### 7.4 Bands

| Band | Rule | UI default |
|---|---|---|
| `strong` | `score >= 0.70` OR `status == confirmed` | visible by default |
| `medium` | `0.45 <= score < 0.70` | hidden by default, filterable |
| `weak` | `score < 0.45` | not shown in first-cut UI |

Confirmed bridges are always included in the `bridges[]` array, even if the derived numeric score is below `0.70`.

---

## 8. Generation Rules

`views-generate-data` must:

1. discover all workspaces,
2. load confirmed cross-domain edges from canonical `connections.json`,
3. load candidate bridge files from `log/bridge-candidates.json` when present,
4. resolve card metadata for both endpoints,
5. compute `score` and `strength_band`,
6. deduplicate entries representing the same domain/card pair,
7. emit one deterministic global `bridges.json` file.

### 8.1 Deduplication

Canonical identity is:

```text
(min(source.workspace_id, target.workspace_id),
 min(source.card_id, target.card_id),
 max(source.workspace_id, target.workspace_id),
 max(target.card_id, source.card_id),
 relation)
```

If both a confirmed edge and a candidate refer to the same bridge:

- keep one entry,
- set `status = confirmed`,
- preserve candidate provenance when available,
- preserve the highest available signal detail.

### 8.2 Sorting

The `bridges[]` array is sorted by:

1. `status` (`confirmed` before `candidate`)
2. `score` descending
3. `domains[0]`
4. `domains[1]`
5. `id`

This preserves determinism.

---

## 9. UI Expectations Derived from the Contract

This data contract is designed to support the product decisions already made:

- **Landing Cross-Domain card:** use `summary.top_domain_pairs` + top `strong` entries from `bridges[]`
- **Comparison route:** open with `drilldown.comparison_domains`
- **Whole-install graph default:** start from `strong` + `confirmed` bridges only, then expand outward if the user asks for more
- **Per-domain cards remain mostly unchanged:** they may show a small bridge count later, but `bridges.json` is primarily for the new Cross-Domain surfaces

---

## 10. Validation Checklist

- [ ] `bridges.json` uses the standard data envelope
- [ ] every bridge entry points to two cards from different domains/workspaces
- [ ] confirmed bridges come only from canonical `connections.json`
- [ ] candidate bridges can be traced to a `bridge-detect` output artifact
- [ ] score is deterministic from the persisted inputs
- [ ] `strong` / `medium` / `weak` bands match the scoring rules above
- [ ] deleting `bridges.json` and regenerating produces identical output for unchanged inputs

---

## 11. Open Follow-ups

1. Should `bridge-detect` write only the latest candidate set, or an append-only history?
2. Should L3 carry richer structure than `strong` / `possible` + free-text reasoning?
3. Should pairwise comparison aggregates remain client-derived from `bridges.json`, or get a separate `cross-domain-stats.json` later?
4. Does the first graph implementation need additional node/edge convenience fields beyond this contract?
