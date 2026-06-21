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
| Runtime/API layer | [`src/construct/`](src/construct/) and [`tests/`](tests/) — active v0.3 pipeline, CLI, MCP, LLM gate, and contract tests |
| GSD state | [`.planning/`](.planning/) — v0.3 shipped; v0.4 is next |
| Test fixtures | [`test-ws/`](test-ws/) — not user data |
| Agent rules (repo) | [`AGENTS.md`](AGENTS.md) |

**Do not use as primary sources:**

| What | Where | Why |
|------|-------|-----|
| Python v0.1 spec | [`archive/v01-python/spec/`](archive/v01-python/spec/) | Archived — superseded by Claude-native path |
| v0.3 planning notes | [`CONSTRUCT-CLAUDE-v03-planning/`](CONSTRUCT-CLAUDE-v03-planning/) | Historical planning — shipped state is in `.planning/` |
| v0.2 planning notes | [`CONSTRUCT-CLAUDE-v02-planning/`](CONSTRUCT-CLAUDE-v02-planning/) | Historical backlog; specs in `CONSTRUCT-CLAUDE-spec/spec-v02-*` |
| GSD (Python track) | [`archive/v01-python/gsd/`](archive/v01-python/gsd/) | Archived — historical Python v0.1 planning run |

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
v0.3 shipped         Pipeline/API layer — src/construct/; .planning/milestones/v0.3-*
       ↓
v0.4 next            UI-as-primary shell on v0.3 API
```

The **knowledge model and workspace file format** are shared across all versions.

---

## Getting started

See [`CONSTRUCT-CLAUDE-impl/USER_GUIDE.md`](CONSTRUCT-CLAUDE-impl/USER_GUIDE.md) for the user guide and quickstart. Installation details in [`CONSTRUCT-CLAUDE-impl/README.md`](CONSTRUCT-CLAUDE-impl/README.md).

---

## Developer environment

Python runtime dependencies, developer tools, and tests are managed through the repository-local `.venv/`. Do not rely on globally installed `python`, `pytest`, or `construct` when working in this repo.

Use the venv directly from the repository root:

```bash
.venv/bin/python -m pytest
```

If the venv needs dependencies refreshed:

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

Activating the venv is also fine, but the effective commands should still resolve to `.venv`:

```bash
source .venv/bin/activate
python -m pytest
```

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
├── CONSTRUCT-CLAUDE-v03-planning/ # v0.3 pipeline/API planning notes (shipped)
├── CONSTRUCT-CLAUDE-v02-planning/ # v0.2 backlog (historical)
├── .planning/                     # ACTIVE — GSD state; v0.3 closed, v0.4 next
├── test-ws/                       # Test workspace fixtures
├── archive/
│   └── v01-python/                # ARCHIVED — v0.1 Python-first spec + GSD
│       ├── README.md
│       ├── spec/                  # Former CONSTRUCT-spec/
│       └── gsd/                   # Former .planning/ (Python GSD)
├── src/construct/                 # ACTIVE — v0.3 pipeline/API runtime
├── tests/                         # ACTIVE — runtime contract/unit/integration tests
├── views/                         # Design examples / views assets
├── AGENTS.md                      # Repository-level agent instructions
└── pyproject.toml                 # Python build config
```

---

## Python runtime

The original v0.1 plan was a full Python application (FastAPI, SQLite, React UI). That path is **paused**, not deleted:

- **Spec:** [`archive/v01-python/spec/`](archive/v01-python/spec/)
- **May resume for:** cloud deployment, SQLite indexing, custom UI backend

The v0.3 milestone revived the Python layer surgically as the deterministic runtime for pipeline, CLI, MCP, LLM-gated, and ops-UI capabilities:

- **Runtime:** [`src/construct/`](src/construct/)
- **Tests:** [`tests/`](tests/)

Both approaches share the same workspace format on disk.
