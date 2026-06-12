# CONSTRUCT User Guide

**For new users and anyone wanting to understand how CONSTRUCT works.**

CONSTRUCT is a local-first, agent-powered personal knowledge system. It helps you collect, curate, connect, and compound knowledge across domains — then turn that accumulated knowledge into high-quality outputs (briefings, reports, essays, articles).

The user interface is **conversation**. You talk to CONSTRUCT in natural language. Claude IS the runtime — your workspace files on disk are the only source of truth.

---

## Quickstart: From Zero to Your First Knowledge Graph (in ~15 minutes)

### Prerequisites

- A Claude subscription (Pro, Max, Team, or Enterprise)
- Claude Desktop (macOS/Windows), Claude Code, or claude.ai
- The setup script from this repository

### Setup

```bash
# From the repository root:
./setup-construct.sh ~/my-construct
```

This creates a self-contained CONSTRUCT directory. Open `~/my-construct/` in Claude.

### Verify it works

Start a new conversation and say:

> "What is your identity?"

Claude should respond as **CONSTRUCT** — referencing knowledge architecture, epistemic governance, and the Watson principle ("thinking partner, not assistant").

### Initialize your first domain

Say:

> "Initialize cosmology"

CONSTRUCT will:

1. Create a `cosmology/` workspace with `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, and `log/events.jsonl`
2. Ask you about the domain (key topics, sources, seed questions)
3. Optionally run an initial research cycle to create the first cards

After this, your directory looks like:

```
my-construct/
├── AGENTS.md
├── .construct/                  # Agent infrastructure (read-only)
└── cosmology/                   # Your first domain
    ├── cards/                   # 3–10 seed cards
    ├── refs/                    # Source references
    ├── connections.json         # Graph edges
    ├── domains.yaml             # Domain config
    ├── governance.yaml          # Quality thresholds
    ├── search-seeds.json        # Search patterns
    ├── digests/                 # Research digests
    └── log/events.jsonl         # Audit trail
```

### What to do next

| Say | What happens |
|-----|-------------|
| "Research the latest developments in cosmology" | Web research → new cards + digest |
| "How's the graph looking?" | Card counts, connections, health |
| "What gaps do you see?" | Coverage analysis, missing connections |
| "Run curation on cosmology" | Validate, promote, flag stale/orphan cards |
| "Turn that into a knowledge card" | Capture a conversational insight |
| "Write a briefing on dark energy" | Draft from accumulated knowledge |

---

## How CONSTRUCT Works

### Three layers

```
You talk to CONSTRUCT (natural language)
  │
  ▼
CONSTRUCT orchestrator routes your intent
  │
  ├── Specialist role handles the operation
  │     ├── Researcher — finds new knowledge (web search → cards)
  │     └── Curator — maintains existing knowledge (validate → promote → connect)
  │
  ├── Workspace files are read or updated
  ├── Actions are logged to events.jsonl
  └── You receive a summary and next options
```

### The knowledge graph

Everything is files on disk:

- **Cards** (`cards/*.md`): Atomic knowledge units — one claim, finding, concept, or gap per card. Markdown body with YAML frontmatter containing epistemic metadata.
- **Connections** (`connections.json`): Typed edges linking cards into a graph (supports, contradicts, extends, etc.)
- **Config** (`domains.yaml`, `governance.yaml`, `search-seeds.json`): Domain taxonomy, quality thresholds, and research patterns.
- **Refs** (`refs/*.json`): Source references (papers, articles, URLs).
- **Log** (`log/events.jsonl`): Append-only audit trail of all significant actions.

### Epistemic governance — every claim is labeled

Every card carries four pieces of metadata. This is non-negotiable:

| Field | Values | What it answers |
|-------|--------|-----------------|
| **epistemic_type** | finding, claim, concept, method, paper, theme, gap, provocation, question, connection | What role does this card play? |
| **confidence** | 1 (speculative) → 5 (foundational) | How certain are we? |
| **source_tier** | 1 (peer-reviewed) → 5 (unverified) | Where does it come from? |
| **lifecycle** | seed → growing → mature → archived | How mature is this knowledge? |

When CONSTRUCT writes something from the graph, confidence propagates into the language — speculative claims get hedged, established claims get assertive.

---

## Use Cases & Example Scenarios

### Scenario A: Start a new research domain

You want to begin tracking a new field.

> "Initialize climate-policy"

CONSTRUCT creates the workspace, interviews you about the domain, runs initial research, and seeds the graph with starter cards.

**Result:** A new domain workspace with initial cards, refs, search patterns, and governance rules.

---

### Scenario B: Daily research session

You want to find new material in an existing domain.

> "What's new in climate-policy?"

CONSTRUCT checks when research was last run, searches for new material, ingests novel results, curates the graph, and shows status.

**Result:** New refs, new seed cards, the graph is fresher, and you get a digest of what changed.

---

### Scenario C: Capture an insight from conversation

An important idea emerges during discussion.

> "That reminds me — the loss-and-damage fund structure is similar to how carbon markets evolved. Turn that into a card."

CONSTRUCT creates a knowledge card with epistemic metadata and offers to connect it to related cards.

**Result:** The insight is now a permanent, connected part of your knowledge graph.

---

### Scenario D: Connect ideas across domains

You want surprising connections between different fields.

> "What bridges exist between cosmology and philosophy-of-mind?"

CONSTRUCT searches for structural parallels and semantic overlaps across the two domains, proposing candidate bridge connections.

**Result:** Cross-domain insights that neither domain alone would reveal.

---

### Scenario E: Clean up a messy graph

The workspace has many cards with stale claims and weak connections.

> "Run curation on cosmology"

CONSTRUCT runs: integrity check → decay scan → orphan detection → promotion evaluation → connection typing → health report.

**Result:** Stale cards flagged, orphans identified, promotion candidates reviewed, connections typed.

---

### Scenario F: Write from accumulated knowledge

You want to produce a briefing, report, or essay grounded in what you know.

> "Draft a briefing on nature-based solutions for adaptation finance using what we know."

CONSTRUCT assesses knowledge strength, identifies weak sections, optionally fills gaps via targeted research, then drafts with inline source citations and confidence indicators.

**Result:** A publishable document in `publish/` with epistemic transparency — you know which parts are well-supported.

---

### Scenario G: Check your knowledge landscape

You want to understand what you know and where the gaps are.

> "How's the graph looking?" → card counts, connections, domain health.
> "What gaps do you see?" → coverage analysis, missing categories, thin confidence zones.

**Result:** A clear picture of your knowledge state and the most valuable next research direction.

---

### Scenario H: Use the browser dashboard (v0.2+)

You want a visual, navigable view of your knowledge.

> "Scaffold the views" → one-time SPA setup
> "Build the views" → production bundle
> "Start CONSTRUCT" → local server on port 3001–3009

Your knowledge graph, cards, and digests appear in a browser dashboard, derived entirely from workspace files.

---

## Full Command Reference

### Entry & orientation

| You say | What happens |
|---------|-------------|
| "help" / "what's next?" | Scans workspace, suggests the most valuable next action |
| "init {domain}" | Creates a new domain workspace + runs the configuration interview |
| "init {domain} interview" | Re-runs the domain interview |

### Research

| You say | What happens |
|---------|-------------|
| "research {domain}" | Web search → extract → score → create refs + seed cards |
| "research {topic}" | Targeted research on a specific topic |
| "search adjust" | Tune search clusters, weights, and priorities |

### Knowledge operations

| You say | What happens |
|---------|-------------|
| "add card" | Create a knowledge card with epistemic metadata |
| "edit card {id}" | Update an existing card |
| "connect {A} to {B}" | Create a typed connection between two cards |
| "evaluate {id}" | Assess a card for promotion, decay, or archival |
| "archive {id}" | Move a card to archived lifecycle |

### Curation

| You say | What happens |
|---------|-------------|
| "curate {domain}" | Full cycle: validate → decay scan → orphan scan → promote → connect → bridge detect |
| "bridges" | Find cross-domain structural parallels |
| "validate" | Full workspace integrity audit (schema, governance, consistency, health, audit trail) |

### Analysis

| You say | What happens |
|---------|-------------|
| "status" | Dashboard: card counts, connections, domain health |
| "gaps {domain}" | Coverage gaps, confidence distribution, missing categories |
| "gaps {topic}" | Topic-specific gap report |
| "domains" | List all domains, show status, activate/pause |

### Writing

| You say | What happens |
|---------|-------------|
| "write {topic}" | Draft a document from accumulated knowledge |
| "publish" | List and manage published outputs in `publish/` |

### Views & server

| You say | What happens |
|---------|-------------|
| "scaffold views" | One-time SPA template setup |
| "build views" | Vite production build |
| "update views" / "refresh data" | Parse workspace → JSON for dashboard |
| "start" / "show views" | Start local server on port 3001–3009 |
| "stop" | Stop local server |
| "reset views" | Remove all views artifacts — clean slate |

### Workflows (multi-skill sequences)

| Workflow | When to use | Sequence |
|----------|------------|----------|
| **Cold Start** | First session | init → domain-init → research → curate → status |
| **Daily Cycle** | Regular maintenance | research → curate → status → interact |
| **Co-Authorship** | Writing from knowledge | gap-analysis → [research] → draft → iterate → finalize |

---

## Reference Tables

### Epistemic types

| Type | Purpose | Example |
|------|---------|---------|
| `finding` | A factual result or observation | "GPT-4V scores 87% on spatial reasoning benchmarks" |
| `claim` | An assertion that may be contested | "Transformer attention is sufficient for spatial reasoning" |
| `concept` | A defined term or abstraction | "Successor representation" |
| `method` | A technique, algorithm, or process | "RLHF fine-tuning pipeline" |
| `paper` | A reference to a specific publication | "Driess et al. 2023 — PaLM-E" |
| `theme` | A recurring pattern across multiple cards | "Embodiment as grounding for language models" |
| `gap` | An identified absence of knowledge | "No benchmarks for multi-agent spatial coordination" |
| `provocation` | A speculative or contrarian idea | "What if world models don't need vision at all?" |
| `question` | An open inquiry awaiting investigation | "How does SR generalize to continuous spaces?" |
| `connection` | A meta-card documenting a non-obvious link | "Topology ↔ robotics: shared path planning structure" |

### Confidence levels

| Level | Label | Meaning | Language in outputs |
|-------|-------|---------|---------------------|
| 1 | Speculative | Hunch, unverified | "Speculatively..." / "It may be that..." |
| 2 | Emerging | Single source, early evidence | "Emerging research suggests..." |
| 3 | Supported | Multiple independent sources | "Evidence supports..." / "Research indicates..." |
| 4 | Established | Strong evidence, peer-reviewed | "It is well-documented that..." |
| 5 | Foundational | Field consensus, axiomatic | "The consensus is..." |

### Source tiers

| Tier | Label | Examples |
|------|-------|---------|
| 1 | Peer-reviewed | Journal articles, top conference proceedings |
| 2 | Preprint / report | arXiv, institutional/government reports |
| 3 | Expert content | Blogs by domain experts, talks, interviews |
| 4 | Community / secondary | Wikipedia, tutorials, newsletters |
| 5 | Unverified | Social media, AI-generated without sources, hearsay |

### Connection types

| Relation | Meaning | Symmetric? |
|----------|---------|-----------|
| `supports` | A provides evidence for B | No |
| `contradicts` | A undermines B | Yes |
| `extends` | A builds on B | No |
| `parallels` | A and B share structural similarity | Yes |
| `requires` | A depends on B | No |
| `enables` | A makes B possible | No |
| `challenges` | A raises questions about B | No |
| `inspires` | A motivated B | No |
| `gap-for` | A identifies what B is missing | No |

### Lifecycle

```
seed ──→ growing ──→ mature ──→ archived
               │                  ↑
               └──→ archived ────┘ (decay or superseded)
```

| State | Meaning |
|-------|---------|
| `seed` | Newly created, minimal validation (default for Researcher cards) |
| `growing` | Gaining evidence and connections |
| `mature` | Well-evidenced, connected, reliable |
| `archived` | No longer active in the graph |

---

## How to Think About Working with CONSTRUCT

### Design principles

- **Claude is the runtime.** There is no Python backend, no database, no server (until you opt into the browser dashboard). Conversation is the interface.
- **Files are the source of truth.** Everything is in `cards/`, `connections.json`, `domains.yaml` — plain files you can read, edit, and version with git. Derived views (digests, dashboards, drafts) can always be rebuilt.
- **Confidence is not optional.** Every claim is labeled with how certain we are and where it came from. This radiates into everything CONSTRUCT produces.
- **Gaps are features, not bugs.** Knowing what you don't know is more valuable than smoothing over uncertainty. CONSTRUCT flags weak areas explicitly.

### Watson principle

CONSTRUCT operates as a **thinking partner, not an assistant.** It says "we" when collaborating, "I" when taking action. It suggests rather than gates. It keeps you oriented in your knowledge landscape.

### What CONSTRUCT does well

- Maintains a local-first knowledge graph
- Keeps claims epistemically labeled
- Turns research findings into structured cards
- Builds connections across ideas and domains
- Produces drafts with source-card grounding
- Surfaces gaps and uncertainty instead of hiding them

### What CONSTRUCT does not do

- It does not replace human editorial control
- It does not hard-delete cards without confirmation
- It does not treat speculative cards as established knowledge
- It does not require a cloud service, auth system, or database

---

## Where things live on disk

A fully set-up CONSTRUCT workspace:

```
my-construct/
├── AGENTS.md                  # Claude reads this → becomes CONSTRUCT
├── CLAUDE.md                  # Claude Code entry point
├── .claude/                   # Agent config (read-only after setup)
│   ├── settings.json
│   ├── skills/                # Skill procedures (SKILL.md files)
│   └── agents/                # Curator + Researcher role definitions
├── .construct/                # Reference library (read-only after setup)
│   ├── templates/             # File templates
│   ├── references/            # Lookup tables
│   └── workflows/             # Multi-skill sequences
├── cosmology/                 # Your domain workspace
│   ├── cards/                 # Knowledge cards (*.md)
│   ├── refs/                  # Source references (*.json)
│   ├── connections.json       # Graph edge list
│   ├── domains.yaml           # Domain taxonomy
│   ├── governance.yaml        # Quality thresholds
│   ├── search-seeds.json      # Research patterns
│   ├── digests/               # Research cycle outputs
│   ├── publish/               # Drafted outputs
│   └── log/events.jsonl       # Append-only audit trail
├── climate-policy/            # Another domain (sibling)
│   └── ...
└── views/                     # Browser dashboard (optional, v0.2+)
    ├── src/                   # SPA source
    └── build/                 # Production bundle + generated data
```

---

## For more information

- [CONSTRUCT-CLAUDE-impl/AGENTS.md](AGENTS.md) — full agent identity, routing, and governance rules
- [.construct/references/capabilities.md](construct/references/capabilities.md) — comprehensive capabilities handbook
- [.construct/references/commands.md](construct/references/commands.md) — command quick reference
- [.construct/workflows/](construct/workflows/) — detailed workflow procedures (cold-start, daily-cycle, co-authorship)
- [.construct/templates/](construct/templates/) — workspace file format templates
