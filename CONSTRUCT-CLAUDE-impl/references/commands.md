# CONSTRUCT — Quick Reference

A single-page reference of everything you can ask CONSTRUCT to do.

---

## Starting Point

| Say | What happens |
|-----|-------------|
| `help` / `what's next?` / `construct` | State-aware suggestion + full command menu |

---

## Getting Started

| Command | Skill | What it does |
|---------|-------|-------------|
| `init {domain}` | workspace-init → domain-init | Create a new domain workspace and run the configuration interview |
| `init {domain} interview` | domain-init | Re-run the domain interview to update categories, sources, and search seeds |

## Research

| Command | Skill | What it does |
|---------|-------|-------------|
| `research {domain}` | research-cycle | Web search → extract → score → create refs and seed cards |
| `research {topic}` | research-cycle (targeted) | Focused research on a specific topic within a domain |
| `search adjust` | search-adjust | Tune search clusters, weights, and priorities |

## Knowledge Operations

| Command | Skill | What it does |
|---------|-------|-------------|
| `add card` | card-create | Create a new knowledge card with full epistemic metadata |
| `edit card {id}` | card-edit | Update an existing card's content or metadata |
| `connect {a} → {b}` | card-connect | Create a typed connection between two cards |
| `evaluate {id}` | card-evaluate | Assess a card for promotion, decay, or archival |
| `archive {id}` | card-archive | Move a card to archived lifecycle state |

## Curation

| Command | Skill | What it does |
|---------|-------|-------------|
| `curate {domain}` | curation-cycle | Full cycle: validate → decay scan → orphan scan → promote → connect → bridge detect |
| `bridges` | bridge-detect | Find cross-domain structural parallels and semantic overlaps |
| `validate` | workspace-validate | Check workspace integrity (file structure, schema, references) |

## Analysis

| Command | Skill | What it does |
|---------|-------|-------------|
| `status` | graph-status | Dashboard: card counts, connections, domain health, quality indicators |
| `gaps {domain}` | gap-analysis | Coverage gaps, confidence distribution, missing categories |
| `gaps {topic}` | gap-analysis (scoped) | Topic-specific gap report |
| `domains` | domain-manage | List domains, show status, activate/pause |

## Writing & Publishing

| Command | Skill | What it does |
|---------|-------|-------------|
| `write {topic}` | synthesis (via co-authorship workflow) | Draft a document from accumulated knowledge with epistemic transparency |
| `publish` | synthesis | List and manage published outputs in `publish/` |

---

## Views & Server

| Command | Skill | What it does |
|---------|-------|-------------|
| `scaffold views` | views-scaffold | One-time SPA template setup — copies source, installs Node deps |
| `build views` | views-build | Vite production build into `views/build/` |
| `update views` / `refresh data` | views-generate-data | Parse workspace files → write JSON to `views/build/data/` |
| `start` / `show views` | construct-up | Start local server (port 3001–3009), write PID file |
| `stop` | construct-down | Stop local server, remove PID file |
| `reset views` | views-reset | Remove `views/src/`, `views/build/`, skill venv — clean slate |

**Config:** Copy `.construct/templates/config.yaml` to `.construct/config.yaml` to set `views.auto_regenerate: false` (disable post-skill data refresh), `views.workspace_landing: wiki` (open wiki instead of dashboard when navigating to a workspace), or `views.confirm_refresh: true` (show "✓ views updated" after hook regen).

---

## Workflows (Multi-Skill Sequences)

| Workflow | When to use | Sequence |
|----------|------------|----------|
| **Cold Start** | First-ever session | workspace-init → domain-init → research-cycle → curation-cycle → graph-status |
| **Daily Cycle** | Regular maintenance session | research-cycle → curation-cycle → graph-status → user interaction |
| **Co-Authorship** | Writing from knowledge | gap-analysis → [research-cycle] → synthesis → iterate → finalize |

---

## Natural Language

These commands are **keywords, not syntax**. You can phrase things however you want:

- "What's new in cosmology?" → `research cosmology`
- "Find me papers on dark energy" → `research` (targeted)
- "How's my knowledge looking?" → `status`
- "Write me a briefing on inflation models" → `write` (co-authorship workflow)
- "Any connections between cosmology and climate?" → `bridges`
- "I read an interesting paper..." → `add card`

CONSTRUCT routes natural language to the right skill automatically.
