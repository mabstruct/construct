# CONSTRUCT — Claude Agent Configuration

**Version:** see [`VERSION`](VERSION) (currently `0.2.0-dev`)
**Purpose:** A complete CONSTRUCT knowledge system implemented as Claude agent configuration.
**Runtime:** Claude handles dialog, sessions, web search, file management, and reasoning natively.
**No code required:** This is a configuration-only project. Claude IS the agent runtime.

---

## Design Principle

Instead of building a Python backend with FastAPI, SQLite, and NetworkX, we configure Claude to BE the CONSTRUCT system. Claude's native capabilities map directly:

| CONSTRUCT Capability | Claude Native Feature |
|---------------------|----------------------|
| Conversational reasoning | Chat / dialog handling |
| Research cycles | Web search + structured extraction |
| Session lifecycle | Conversation persistence |
| Card management | File read/write on workspace |
| Knowledge graph | Markdown files + `connections.json` |
| Curation | Scheduled skill invocation |
| Cross-domain ideation | Frontier reasoning |
| Synthesis / co-authorship | Long-form generation from context |

## Source Structure

This is the development source. For deployment, the setup script assembles a self-contained directory.

```
CONSTRUCT-CLAUDE-impl/
├── README.md                      # This file
├── AGENTS.md                      # Root agent identity (CONSTRUCT orchestrator)
│
├── agents/                        # Agent role definitions
│   ├── curator.md                 # Curator — graph gardener
│   └── researcher.md              # Researcher — knowledge acquisition
│
├── skills/                        # Executable skill definitions
│   ├── workspace-init/SKILL.md    # Initialize a domain workspace (subdirectory)
│   ├── domain-init/SKILL.md       # Domain initialization interview
│   ├── domain-manage/SKILL.md     # Pause, resume, archive domains
│   ├── card-create/SKILL.md       # Create a knowledge card
│   ├── card-edit/SKILL.md         # Edit existing card metadata/content
│   ├── card-archive/SKILL.md      # Archive card with supersedes handling
│   ├── card-connect/SKILL.md      # Manage connections between cards
│   ├── card-evaluate/SKILL.md     # Evaluate card for promotion
│   ├── research-cycle/SKILL.md    # Run a web research cycle
│   ├── curation-cycle/SKILL.md    # Run graph maintenance
│   ├── gap-analysis/SKILL.md      # Identify knowledge gaps
│   ├── synthesis/SKILL.md         # Draft output from graph state
│   ├── graph-status/SKILL.md      # Report graph health
│   ├── search-adjust/SKILL.md     # Adjust search patterns
│   ├── bridge-detect/SKILL.md     # Cross-domain bridge detection
│   └── workspace-validate/SKILL.md # 5-layer workspace integrity audit
│
├── workflows/                     # Multi-skill orchestration sequences
│   ├── cold-start.md              # Full workspace setup (J1)
│   ├── daily-cycle.md             # Research + curate + report (J2)
│   └── co-authorship.md           # Synthesis and drafting (J3)
│
├── references/                    # Lookup tables and enum definitions
│   ├── epistemic-types.md         # 10 card types with usage guidance
│   ├── confidence-levels.md       # 1–5 scale reference
│   ├── source-tiers.md            # 1–5 tier reference
│   ├── connection-types.md        # 9 edge relation definitions
│   └── lifecycle-states.md        # seed → growing → mature → archived
│
└── templates/                     # File templates for workspace artifacts
    ├── card.md                    # Knowledge card template
    ├── domains.yaml               # Domain taxonomy template
    ├── governance.yaml            # Governance thresholds template
    ├── model-routing.yaml         # LLM routing template
    ├── search-seeds.json          # Search pattern template
    ├── connections.json           # Empty graph edge list
    ├── digest.md                  # Research cycle digest template
    ├── ref.json                   # Reference entry template
    └── publish.md                 # Publishable output template
```

## Installation

### Quick Setup (recommended)

Run the setup script from the repository root:

```bash
./setup-construct.sh ~/my-construct
```

This creates a self-contained directory:

```
~/my-construct/
├── AGENTS.md              # Claude reads this → becomes CONSTRUCT
└── .construct/            # Agent infrastructure (hidden)
    ├── agents/
    ├── skills/
    ├── workflows/
    ├── references/
    └── templates/
```

Then open `~/my-construct/` in Claude (Desktop, Code, or claude.ai project) and start working.

### Prerequisites

- A Claude subscription (Pro, Max, Team, or Enterprise) — needed for artifacts, persistent storage, and MCP connectors
- Claude Desktop app (macOS/Windows), Claude Code, or access to claude.ai
- The setup script (`setup-construct.sh`) from this repository

### Verify Setup

Start a new Claude conversation in your CONSTRUCT directory and say:

> "What is your identity?"

Claude should respond as **CONSTRUCT** — referencing knowledge architecture, epistemic governance, and the Watson principle. If Claude responds generically, the `AGENTS.md` file is not being picked up.

---

## Basic Usage

### Cold start (first time)

Initialize your first domain workspace:

> "Initialize cosmology"

This runs workspace-init → domain-init, which:
1. Creates `cosmology/` subdirectory with full workspace structure
2. Populates `governance.yaml` from `.construct/templates/`
3. Interviews you about the domain (goals, key topics, sources, seed questions)
4. Writes `domains.yaml` and `search-seeds.json`
5. Optionally runs an initial research cycle

After cold start, your directory looks like:
```
my-construct/
├── AGENTS.md
├── .construct/              # Agent infrastructure (unchanged)
└── cosmology/               # Your first domain workspace
    ├── cards/               # 3–10 seed cards from initial research
    ├── refs/                # Source references
    ├── connections.json     # Initial connections
    ├── domains.yaml         # Domain configured
    ├── governance.yaml      # Default thresholds
    ├── search-seeds.json    # Search patterns
    ├── digests/             # First research digest
    └── log/events.jsonl     # Audit trail
```

### Adding more domains

> "Initialize climate-policy"

Creates a sibling subdirectory. Each domain workspace is self-contained:
```
my-construct/
├── .construct/
├── cosmology/
├── climate-policy/
└── ...
```

### Daily use

**Research a topic:**
> "Research the latest developments in cosmology"

Claude identifies the `cosmology/` workspace, switches to Researcher role, runs web search, creates cards, and produces a digest.

**Check graph status:**
> "How's the cosmology graph looking?"

Returns card counts by lifecycle state, connection statistics, confidence distribution, and flags any issues.

**Curate the graph:**
> "Run curation on cosmology"

Claude switches to Curator role: validates card integrity, checks for confidence decay, promotes strong seeds, flags orphans, and reports changes.

**Find gaps:**
> "What gaps do you see in cosmology?"

Analyzes coverage, identifies missing connections, and suggests research directions.

**Create a card from conversation:**
> "Turn that into a knowledge card"

After discussing something interesting, Claude extracts the key insight into a properly formatted card with frontmatter, confidence, source tier, and connections.

**Connect ideas:**
> "How does [card A] relate to [card B]?"

Claude analyzes the relationship, proposes a typed connection (supports, contradicts, extends, etc.), and updates `connections.json`.

### Co-authorship

**Draft a briefing:**
> "Draft a briefing on [topic] using what we know"

Claude reads relevant cards, propagates confidence metadata into the draft, and produces a structured output in `publish/` with source attribution.

**Explore cross-domain bridges:**
> "What surprising connections exist between cosmology and climate-policy?"

Claude runs bridge detection across two domain workspaces, identifying structural parallels and shared concepts.

### Domain management

**Add a new domain:**
> "Initialize [new-topic]"

Creates a new subdirectory, runs the domain initialization interview.

**Pause a domain:**
> "Pause research on cosmology"

Marks the domain as paused — curation continues but no new research cycles run.

### Key phrases Claude recognizes

| What you say | What runs |
|-------------|-----------|
| "Initialize a workspace" | `workspace-init` skill |
| "Add a domain for X" | `domain-init` skill |
| "Research X" | `research-cycle` skill (Researcher role) |
| "Curate" / "Run curation" | `curation-cycle` skill (Curator role) |
| "What gaps do you see?" | `gap-analysis` skill |
| "Draft a briefing on X" | `synthesis` skill |
| "Graph status" / "How's the graph?" | `graph-status` skill |
| "Turn that into a card" | `card-create` skill |
| "Connect X to Y" | `card-connect` skill |
| "Evaluate [card]" | `card-evaluate` skill |
| "Adjust search for X" | `search-adjust` skill |
| "Find bridges between X and Y" | `bridge-detect` skill |
| "Validate the workspace" | `workspace-validate` skill |

## What Claude Handles Natively (No Config Needed)

- **Dialog and conversation** — Claude's core capability
- **Web search** — built-in tool for research cycles
- **File operations** — read/write cards, connections, configs
- **Reasoning** — cross-domain ideation, editorial judgment
- **Session memory** — conversation context across turns
- **Scheduling** — user-triggered or conversation-driven cycles

## What This Config Adds

- **Structured identity** — CONSTRUCT personality, voice, behavior rules
- **Agent roles** — Curator and Researcher as specialized modes
- **Repeatable skills** — step-by-step procedures for complex operations
- **Quality gates** — epistemic governance enforced through skill logic
- **Templates** — consistent artifact formats
- **Reference tables** — shared vocabulary for types, tiers, and relations
