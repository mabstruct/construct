# CONSTRUCT

Local-first, agent-powered personal knowledge system.

CONSTRUCT systematically collects, curates, connects, and compounds knowledge across domains — and produces high-quality outputs as derived views of accumulated knowledge.

## Two Implementation Approaches

### Claude-Native (Active)

CONSTRUCT implemented as Claude agent configuration — skills, workflows, templates, and reference tables. Claude IS the runtime. No code to build.

- **Configuration:** [`CONSTRUCT-CLAUDE-impl/`](CONSTRUCT-CLAUDE-impl/) — agent identity, 16 skills, 3 workflows, templates, references
- **Specification:** [`CONSTRUCT-CLAUDE-spec/`](CONSTRUCT-CLAUDE-spec/) — PRD, agent specs, data schemas, validation strategy
- **Getting started:** See [`CONSTRUCT-CLAUDE-impl/README.md`](CONSTRUCT-CLAUDE-impl/README.md) for installation and usage

### Python (Dormant)

CONSTRUCT implemented as a Python application — FastAPI, SQLite, Pydantic, React UI. Phase 1 foundation completed, then paused in favor of the Claude-native approach.

- **Specification:** [`CONSTRUCT-spec/`](CONSTRUCT-spec/) — full spec suite (PRD, agent specs, data schemas, SQLite schema, test strategy)
- **Code:** [`src/construct/`](src/construct/) — schemas, services, CLI (`construct init`, `construct validate`, `construct status`)
- **Tests:** [`tests/`](tests/) — unit and integration tests
- **Planning:** [`.planning/`](.planning/) — GSD project state (paused at Phase 1)

The Python approach may resume later for cloud deployment, MCP server integration, or a custom UI layer. Both approaches share the same knowledge model and workspace format.

## Knowledge Model

Both approaches share:
- **10 epistemic types** — finding, claim, concept, method, paper, theme, gap, provocation, question, connection
- **Confidence 1–5** — speculative → foundational
- **Source tiers 1–5** — peer-reviewed → unverified
- **Lifecycle** — seed → growing → mature → archived
- **9 connection types** — supports, contradicts, extends, refines, instantiates, enables, parallels, questions, co-occurs

## Repository Structure

```
construct/
├── CONSTRUCT-CLAUDE-impl/         # ACTIVE — Claude agent configuration
├── CONSTRUCT-CLAUDE-spec/         # ACTIVE — Claude-native specification
├── CONSTRUCT-spec/                # DORMANT — Python specification
├── src/construct/                 # DORMANT — Python implementation
├── tests/                         # DORMANT — Python tests
├── .planning/                     # DORMANT — GSD project state (Python track)
├── AGENTS.md                      # Repository-level agent instructions
├── README.md                      # This file
└── pyproject.toml                 # Python build config
```
