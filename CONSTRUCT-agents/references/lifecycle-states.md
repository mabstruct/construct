# Reference: Lifecycle States

The `lifecycle` field tracks a card's maturity in the knowledge graph.

---

## State Machine

```
seed ──→ growing ──→ mature ──→ archived
                       │
                       └──→ archived (decay or superseded)
```

| State | Meaning | How it gets here | How it leaves |
|-------|---------|-----------------|---------------|
| **seed** | Newly created, minimal validation | Default for new cards (especially from Researcher) | Promoted to `growing` by Curator |
| **growing** | Gaining evidence and connections | Meets seed→growing promotion rules | Promoted to `mature` by Curator |
| **mature** | Well-evidenced, connected, reliable | Meets growing→mature promotion rules | Archived (decay, superseded, or manual) |
| **archived** | No longer active in the graph | Decay timeout, superseded by newer card, or manual archive | Re-promotion possible (rare) |

---

## Promotion Rules (Defaults)

From `governance.yaml`:

| Transition | Conditions |
|-----------|-----------|
| seed → growing | confidence ≥ 2 AND connections ≥ 1 |
| growing → mature | confidence ≥ 3 AND source_tier ≤ 2 AND connections ≥ 2 |

With `require_human_approval: true`, auto-promotion flags for review instead of promoting.

## Archival Triggers

- **Decay:** Card not referenced within `decay_window_days` (default: 28)
- **Superseded:** New card explicitly supersedes this one (`supersedes` field)
- **Manual:** User archives directly
- **Quality:** Card cannot meet minimum quality bar (no valid sources, contradicted by mature evidence)

## Re-Promotion

Archived cards can theoretically return to active lifecycle:
- New evidence surfaces that supports a previously archived card
- User manually resets lifecycle to `seed`
- This is rare and should be explicitly noted in the card

## Cards Never Skip States

A card cannot go from `seed` directly to `mature`. It must pass through `growing`. This ensures incremental validation.
