# CONSTRUCT

Local-first, agent-powered personal knowledge system.

CONSTRUCT systematically collects, curates, connects, and compounds knowledge across domains — and produces high-quality outputs as derived views of accumulated knowledge.

---

## For agents — workspace map

**Active path (default for all work):**

| What | Where |
|------|-------|
| Specification | [`CONSTRUCT-CLAUDE-spec/`](CONSTRUCT-CLAUDE-spec/) — read [`README_FIRST.md`](CONSTRUCT-CLAUDE-spec/README_FIRST.md) first |
| Implementation | [`CONSTRUCT-CLAUDE-impl/`](CONSTRUCT-CLAUDE-impl/) — skills, workflows, templates; read [`AGENTS.md`](CONSTRUCT-CLAUDE-impl/AGENTS.md) for runtime behavior |
| Test fixtures | [`test-ws/`](test-ws/) — not user data |
| Agent rules (repo) | [`AGENTS.md`](AGENTS.md) |

**Do not use as primary sources:**

| What | Where | Why |
|------|-------|-----|
| Python v0.1 spec | [`archive/v01-python/spec/`](archive/v01-python/spec/) | Archived — superseded by Claude-native path |
| Python code | [`src/construct/`](src/construct/), [`tests/`](tests/) | Dormant Phase 1 skeleton |
| v0.3 planning (current) | [`CONSTRUCT-CLAUDE-v03-planning/`](CONSTRUCT-CLAUDE-v03-planning/) | Pipeline/API hardening — ADR-0003 |
| v0.2 planning notes | [`CONSTRUCT-CLAUDE-v02-planning/`](CONSTRUCT-CLAUDE-v02-planning/) | Historical backlog; specs in `CONSTRUCT-CLAUDE-spec/spec-v02-*` |
| GSD (Python track) | [`archive/v01-python/gsd/`](archive/v01-python/gsd/) | Archived — restart fresh GSD for CONSTRUCT03 impl |

---

## Product lineage

One product, evolving runtime and features:

```text
v0.1 Python spec     archive/v01-python/spec/     (archived)
       ↓
Claude-native pivot  CONSTRUCT-CLAUDE-spec/adrs/adr-0001-claude-native-approach.md
       ↓
v0.1 Claude impl     CONSTRUCT-CLAUDE-impl/       (chat + skills + workspace)
       ↓
v0.2 extensions      CONSTRUCT-CLAUDE-spec/spec-v02-*  (local views, cross-domain)
       ↓
v0.3 (planned)       Pipeline/API layer — ADR-0003; CONSTRUCT-CLAUDE-v03-planning/
       ↓
v0.4 (planned)       UI-as-primary shell on v0.3 API
```

The **knowledge model and workspace file format** are shared across all versions.

---

## Getting started

See [`CONSTRUCT-CLAUDE-impl/README.md`](CONSTRUCT-CLAUDE-impl/README.md) for installation and usage.

---

## Knowledge model

- **10 epistemic types** — finding, claim, concept, method, paper, theme, gap, provocation, question, connection
- **Confidence 1–5** — speculative → foundational
- **Source tiers 1–5** — peer-reviewed → unverified
- **Lifecycle** — seed → growing → mature → archived
- **9 connection types** — supports, contradicts, extends, parallels, requires, enables, challenges, inspires, gap-for

Canonical schema: [`CONSTRUCT-CLAUDE-spec/knowledge-card-schema.md`](CONSTRUCT-CLAUDE-spec/knowledge-card-schema.md)

---

## Repository structure

```
construct/
├── CONSTRUCT-CLAUDE-impl/         # ACTIVE — agent configuration (skills, workflows, templates)
├── CONSTRUCT-CLAUDE-spec/         # ACTIVE — living specification (v0.1 + v0.2)
├── CONSTRUCT-CLAUDE-v03-planning/ # v0.3 pipeline/API planning (current) — ADR-0003
├── CONSTRUCT-CLAUDE-v02-planning/ # v0.2 backlog (historical)
├── test-ws/                       # Test workspace fixtures
├── archive/
│   └── v01-python/                # ARCHIVED — v0.1 Python-first spec + GSD
│       ├── README.md
│       ├── spec/                  # Former CONSTRUCT-spec/
│       └── gsd/                   # Former .planning/ (Python GSD)
├── src/construct/                 # DORMANT — partial Python implementation
├── tests/                         # DORMANT — Python tests
├── views/                         # Design examples / views assets
├── AGENTS.md                      # Repository-level agent instructions
└── pyproject.toml                 # Python build config (dormant)
```

---

## Python runtime (archived / dormant)

The original v0.1 plan was a Python application (FastAPI, SQLite, React UI). That path is **paused**, not deleted:

- **Spec:** [`archive/v01-python/spec/`](archive/v01-python/spec/)
- **Code:** [`src/construct/`](src/construct/) — `construct init`, `construct validate`, `construct status`
- **May resume for:** cloud deployment, MCP server, SQLite indexing, custom UI backend

Both approaches share the same workspace format on disk.
