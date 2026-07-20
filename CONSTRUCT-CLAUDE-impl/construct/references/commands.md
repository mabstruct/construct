# CONSTRUCT — Quick Reference

A single-page reference of everything you can ask CONSTRUCT to do.

**Master inventory:** `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` (repository) — all agents, skills, workflows, and CONSTRUCT03 audit matrix. This file is the deployed user-facing subset.
For a fuller capabilities guide covering agents, skills, workflows, users,
scenarios, and dependencies, see `capabilities.md`.

---

## Starting Point

| Say | What happens |
|-----|-------------|
| `help` / `what's next?` / `construct` | State-aware suggestion + full command menu |

---

**Reading the columns:** `Command` is the natural-language keyword, `Skill` is the skill that
handles it, and `CLI` is the equivalent shell invocation where one exists. Skill and CLI are
different axes — a capability may have both, either, or only the skill. A `—` in the CLI column
means the capability is skill-only. Every invocation listed is checked against the live command
surface by `tests/contract/test_doc_command_references.py`; angle-bracket tokens are placeholders.

## Getting Started

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `init {domain}` | construct-workspace-init → construct-domain-init | `construct init <domain>` | Create a new domain workspace — canonical `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `log/events.jsonl`, plus derived `digests/` and `publish/`. Templates sourced from `CONSTRUCT-CLAUDE-impl/construct/templates/`. Runs the configuration interview. |
| `init {domain} interview` | construct-domain-init | — | Re-run the domain interview to update categories, sources, and search seeds |
| `workflow status` | — | `construct workflow status` | Report the state of any paused or in-flight workflow run |
| `mcp` | — | `construct mcp` | Serve the capability surface over MCP for an external client |

## Research

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `research {domain}` | construct-research-cycle | `construct research run --workspace .` | Web search → extract → score → create refs and seed cards |
| `research {topic}` | construct-research-cycle (targeted) | `construct research search --workspace .` | Focused research on a specific topic within a domain |
| `score results` | — | `construct research score` | Rank captured results against the domain's scoring rules |
| `review research` | — | `construct research review` | Approve, reject, or amend the items a paused run has staged |
| `inspect research` | — | `construct research inspect` | Report the per-step state of a completed run |
| `search adjust` | construct-search-adjust | — | Tune search clusters, weights, and priorities |

## Knowledge Operations

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `add card` | construct-card-create | `construct knowledge card create` | Create a new knowledge card with full epistemic metadata |
| `edit card {id}` | construct-card-edit | `construct knowledge card edit` | Update an existing card's content or metadata |
| `list cards` | — | `construct knowledge card list --domain <domain> --json` | Enumerate card frontmatter for a domain — card prose is never returned |
| `connect {a} → {b}` | construct-card-connect | `construct knowledge connection add` | Create a typed connection between two cards |
| `list connections` | — | `construct knowledge connection list --json` | Enumerate the typed edges in the graph |
| `disconnect {a} → {b}` | — | `construct knowledge connection remove` | Remove a typed connection between two cards |
| `evaluate {id}` | construct-card-evaluate | `construct card evaluate` | Assess a card for promotion, decay, or archival |
| `archive {id}` | construct-card-archive | `construct knowledge card archive` | Move a card to archived lifecycle state |

## Curation

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `curate {domain}` | construct-curation-cycle | `construct curation run --workspace .` | Full cycle: validate → decay scan → orphan scan → promote → connect → bridge detect |
| `review curation` | — | `construct curation review` | Approve or reject the promotions and archivals a paused run has staged |
| `inspect curation` | — | `construct curation inspect` | Report the per-step state of a completed cycle |
| `bridges` | construct-bridge-detect | `construct bridge detect` | Find cross-domain structural parallels and semantic overlaps |
| `validate` | construct-workspace-validate | `construct validate` | Post-write audit: 5-layer workspace integrity check covering schema, governance, cross-file consistency, functional health, and audit trail. Pre-write rejection (invalid artifacts blocked before write) is handled by individual skill validation checklists and runtime helpers. |

A curation cycle degrades rather than aborts: a step that cannot complete is recorded in the run
report and the cycle continues. Judge the outcome from the per-step state in the `--json` payload,
not from the process exit code.

## Daily Cycle

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `daily` | — | `construct daily run --workspace .` | Research → curate → status in a single pass over the workspace |
| `inspect daily` | — | `construct daily inspect` | Report the per-step state of the most recent cycle |

A degraded daily run reports its failing step in the payload rather than aborting the cycle —
read the per-step state, not the exit code.

## Ingestion, Spikes & Tags

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `ingest {source}` | — | `construct ingest source <path>` | Pull an external source into `refs/` as a reference entry |
| `spikes` | — | `construct spike list` | List the exploratory spikes defined for the workspace |
| `run spike {id}` | — | `construct spike run` | Execute a single exploratory spike |
| `extract tags` | — | `construct tag extract` | Derive candidate tags from card content |
| `tags` | — | `construct tag list` | List current and candidate tags |
| `approve tags` | — | `construct tag approve` | Promote candidate tags into the workspace vocabulary |

## Analysis

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `status` | construct-graph-status | `construct status` | Dashboard: card counts, connections, domain health, quality indicators |
| `ask {domain}` | — | `construct ask domain` | Answer a question grounded in that domain's knowledge cards |
| `gaps {domain}` | construct-gap-analysis | — | Coverage gaps, confidence distribution, missing categories |
| `gaps {topic}` | construct-gap-analysis (scoped) | — | Topic-specific gap report |
| `domains` | construct-domain-manage | — | List domains, show status, activate/pause |

## Writing & Publishing

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `write {topic}` | construct-synthesis (via co-authorship workflow) | — | Draft a document from accumulated knowledge with epistemic transparency |
| `publish` | construct-synthesis | — | List and manage published outputs in `publish/` |

---

## Views & Server

| Command | Skill | CLI | What it does |
|---------|-------|-----|-------------|
| `scaffold views` | construct-views-scaffold | — | One-time SPA template setup — copies source, installs Node deps |
| `build views` | construct-views-build | — | Vite production build into `views/build/` |
| `update views` / `refresh data` | construct-views-generate-data | `construct views generate` | Parse workspace files → write JSON to `views/build/data/` |
| `validate views` | — | `construct views validate` | Validate the generated dashboard data against its schema |
| `start` / `show views` | construct-up | — | Start local server (port 3001–3009), write PID file |
| `stop` | construct-down | — | Stop local server, remove PID file |
| `reset views` | construct-views-reset | — | Remove `views/src/`, `views/build/`, skill venv — clean slate |

**Config:** Copy `.construct/templates/config.yaml` to `.construct/config.yaml` to set `views.auto_regenerate: false` (disable post-skill data refresh), `views.workspace_landing: wiki` (open wiki instead of dashboard when navigating to a workspace), or `views.confirm_refresh: true` (show "✓ views updated" after hook regen).

**Note on per-card edits:** creating a card or adding a connection directly does **not** trigger a
views refresh — there is no per-card refresh path. Views data is regenerated by the workflow
capabilities (`construct research run`, `construct curation run`, `construct daily run`) or on
demand via `construct views generate`.

---

## Workflows (Multi-Skill Sequences)

| Workflow | When to use | Sequence |
|----------|------------|----------|
| **Cold Start** | First-ever session | construct-workspace-init → construct-domain-init → construct-research-cycle → construct-curation-cycle → construct-graph-status |
| **Daily Cycle** | Regular maintenance session | construct-research-cycle → construct-curation-cycle → construct-graph-status → user interaction |
| **Co-Authorship** | Writing from knowledge | construct-gap-analysis → [construct-research-cycle] → construct-synthesis → iterate → finalize |

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
