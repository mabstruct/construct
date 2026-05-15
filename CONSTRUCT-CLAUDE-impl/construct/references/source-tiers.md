# Reference: Source Tiers

The `source_tier` field (integer 1–5) answers: **where does this knowledge come from?**

---

| Tier | Label | Examples | Trust level |
|------|-------|---------|-------------|
| **1** | Peer-reviewed | Published in journal, top conference proceedings (NeurIPS, ICML, Nature, etc.) | Highest — multiple expert reviewers |
| **2** | Preprint / technical report | arXiv papers, institutional reports, official standards, government publications | High — expert-authored but not peer-reviewed |
| **3** | Expert content | Blog posts by domain experts, conference talks, interviews, podcasts by practitioners | Medium — credible but informal |
| **4** | Community / secondary | Wikipedia, tutorials, forum discussions (Stack Overflow), newsletters, textbooks | Lower — useful but needs cross-reference |
| **5** | Unverified | Social media posts, hearsay, AI-generated content without sources, anecdotal | Lowest — treat as hypothesis |

---

## Assignment Rules

- **When ingesting from web search:** Assess the source venue and assign tier accordingly
- **arXiv preprints** are tier 2 (not tier 1 — they aren't peer-reviewed)
- **Expert blogs** (e.g., Karpathy, Lillicrap) are tier 3 — credible but not formal
- **A Wikipedia article** summarizing peer-reviewed work is still tier 4 (secondary source)
- **AI-generated summaries** without citations are tier 5

## Relationship to Confidence

Source tier constrains realistic confidence:

| Source tier | Realistic max confidence |
|------------|--------------------------|
| 1 | 5 (can support foundational claims) |
| 2 | 4 (strong but awaiting peer review) |
| 3 | 3 (supported by expert opinion) |
| 4 | 2 (emerging, needs better sources) |
| 5 | 1 (speculative until verified) |

A single tier-5 source should not produce a confidence-3 card. If multiple tier-3+ sources agree, confidence can exceed the individual source tier ceiling.
