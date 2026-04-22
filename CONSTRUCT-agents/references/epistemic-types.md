# Reference: Epistemic Types

The `epistemic_type` field answers: **what role does this card play in the knowledge graph?**

---

| Type | Purpose | Example | When to use |
|------|---------|---------|-------------|
| `finding` | A factual result or observation | "GPT-4V scores 87% on spatial reasoning benchmarks" | Research output, experimental results, data points |
| `claim` | An assertion that may be contested | "Transformer attention is sufficient for spatial reasoning" | Debatable positions, hypotheses stated as assertions |
| `concept` | A defined term or abstraction | "Successor representation" | Definitions, abstractions, ontological entries |
| `method` | A technique, algorithm, or process | "RLHF fine-tuning pipeline" | How-tos, algorithms, procedures, methodologies |
| `paper` | A reference to a specific publication | "Driess et al. 2023 — PaLM-E" | Papers, articles, reports as first-class knowledge |
| `theme` | A recurring pattern across multiple cards | "Embodiment as grounding for language models" | Meta-patterns that emerge from accumulated findings |
| `gap` | An identified absence of knowledge | "No benchmarks for multi-agent spatial coordination" | Known unknowns — what we need but don't have |
| `provocation` | A speculative or contrarian idea | "What if world models don't need vision at all?" | Deliberately provocative ideas for exploration |
| `question` | An open inquiry awaiting investigation | "How does the SR generalize to continuous spaces?" | Research questions, unresolved inquiries |
| `connection` | A meta-card documenting a non-obvious link | "Topology ↔ robotics: shared path planning structure" | Cross-domain parallels, structural insights |

---

## Usage Notes

- **Research ingestion** defaults to `finding` (factual output from papers)
- **User-captured ideas** are often `claim`, `question`, or `provocation`
- **Curator-generated** cards are often `gap`, `theme`, or `connection`
- **A card's type is fixed at creation** — if a finding evolves into a theme, create a new theme card that references the original
- **The `connection` type is special** — it documents a relationship that's too complex for a simple edge. Use sparingly.
