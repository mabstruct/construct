# Reference: Connection Types

The relation type on an edge answers: **how are these two cards related?**

---

| Relation | Meaning | Symmetric? | Example |
|----------|---------|-----------|---------|
| `supports` | A provides evidence for B | No (A→B) | Experimental result supports a theoretical claim |
| `contradicts` | A undermines or conflicts with B | Yes (A↔B) | Two findings that disagree |
| `extends` | A builds on or refines B | No (A→B) | A follow-up paper extending prior work |
| `parallels` | A and B share structural similarity | Yes (A↔B) | A topology concept mirrors a robotics architecture |
| `requires` | A depends on B being true/available | No (A→B) | A method requires a specific concept to work |
| `enables` | A makes B possible or practical | No (A→B) | A technique enables a previously impractical approach |
| `challenges` | A raises questions or complications about B | No (A→B) | A finding that complicates an established claim |
| `inspires` | A motivated the creation or thinking behind B | No (A→B) | One idea inspired another |
| `gap-for` | A identifies what B is missing | No (A→B) | A gap card pointing to the concept it's a gap in |

---

## Choosing the Right Type

**Decision flow:**

1. Does one provide evidence for the other? → `supports`
2. Do they disagree? → `contradicts`
3. Does one build on the other? → `extends`
4. Are they similar across different domains? → `parallels`
5. Does one need the other? → `requires`
6. Does one make the other possible? → `enables`
7. Does one complicate the other? → `challenges`
8. Did one motivate the other? → `inspires`
9. Does one identify what the other is missing? → `gap-for`

**When in doubt:**
- If the connection is cross-domain, `parallels` is usually right
- If one came first and the other built on it, `extends`
- If they're in tension but not outright contradictory, `challenges`

## Directionality

For asymmetric relations (A→B):
- `from`: the card that IS the thing (provides evidence, extends, requires, etc.)
- `to`: the card that RECEIVES the relation (is supported, is extended, is required)

For symmetric relations (`contradicts`, `parallels`):
- Direction doesn't matter semantically, but pick one consistently (alphabetical by card ID is fine)

## Multiple Relations

Two cards can have multiple edges with different types. Example:
- Card A `extends` Card B (builds on its framework)
- Card A `challenges` Card B (raises questions about one assumption)

This is normal and informative — don't force a single relation.
