# Reference: Confidence Levels

The `confidence` field (integer 1–5) answers: **how certain are we about this knowledge?**

---

| Level | Label | Meaning | Typical source tier | Language to use in outputs |
|-------|-------|---------|--------------------|-----------------------------|
| **1** | Speculative | Hunch, hypothesis, unverified observation | 4–5 | "Speculatively..." / "It may be that..." / "One possibility is..." |
| **2** | Emerging | Early evidence, single source, initial research | 3–5 | "Emerging research suggests..." / "Preliminary evidence indicates..." |
| **3** | Supported | Multiple independent sources, consistent evidence | 2–3 | "Evidence supports..." / "Research indicates..." / "Findings suggest..." |
| **4** | Established | Strong evidence, peer-reviewed, multiple confirmations | 1–2 | "Strong evidence indicates..." / "It is well-documented that..." |
| **5** | Foundational | Field consensus, textbook knowledge, axiomatic | 1 | "It is well established that..." / "The consensus is..." |

---

## Assignment Rules

- **Researcher** creates cards at confidence 1 (speculative) by default — the Curator decides upgrades
- **Curator** may upgrade based on promotion rules in `governance.yaml`
- **Human** can override any confidence level directly
- **Confidence cannot decrease below 1** — if you don't trust it at all, archive it
- **Confidence should never exceed evidence** — don't assign 4 based on one preprint

## Propagation in Outputs

When producing synthesis or drafts, confidence propagates:
- A section drawing from confidence 3+ cards → assertive language
- A section drawing from confidence 1–2 cards → hedged language
- A section mixing confidence levels → note the range explicitly
