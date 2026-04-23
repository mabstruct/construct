# CONSTRUCT — Claude Agent Configuration

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

## Directory Structure

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
│   ├── workspace-init/SKILL.md    # Initialize a CONSTRUCT workspace
│   ├── domain-init/SKILL.md       # Domain initialization interview
│   ├── card-create/SKILL.md       # Create a knowledge card
│   ├── card-evaluate/SKILL.md     # Evaluate card for promotion
│   ├── research-cycle/SKILL.md    # Run a web research cycle
│   ├── curation-cycle/SKILL.md    # Run graph maintenance
│   ├── gap-analysis/SKILL.md      # Identify knowledge gaps
│   ├── synthesis/SKILL.md         # Draft output from graph state
│   ├── graph-status/SKILL.md      # Report graph health
│   ├── search-adjust/SKILL.md     # Adjust search patterns
│   └── bridge-detect/SKILL.md     # Cross-domain bridge detection
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
    ├── model-routing.yaml         # LLM routing template (for hybrid use)
    ├── search-seeds.json          # Search pattern template
    ├── connections.json           # Empty graph edge list
    └── digest.md                  # Research cycle digest template
```

## Installation

### Prerequisites

- A Claude subscription (Pro, Max, Team, or Enterprise) — needed for artifacts, persistent storage, and MCP connectors
- Claude Desktop app (macOS/Windows) or access to claude.ai
- A local directory for your knowledge workspace (e.g., `~/construct-workspace/`)

### Step 1: Copy agent configuration

Copy the entire `CONSTRUCT-CLAUDE-impl/` directory into your Claude configuration location:

```bash
# macOS — Claude Desktop
cp -r CONSTRUCT-CLAUDE-impl/ ~/.claude/

# Alternative: symlink to keep config in your repo
ln -s "$(pwd)/CONSTRUCT-CLAUDE-impl/AGENTS.md" ~/.claude/AGENTS.md
ln -s "$(pwd)/CONSTRUCT-CLAUDE-impl/agents" ~/.claude/agents
ln -s "$(pwd)/CONSTRUCT-CLAUDE-impl/skills" ~/.claude/skills
ln -s "$(pwd)/CONSTRUCT-CLAUDE-impl/workflows" ~/.claude/workflows
ln -s "$(pwd)/CONSTRUCT-CLAUDE-impl/references" ~/.claude/references
ln -s "$(pwd)/CONSTRUCT-CLAUDE-impl/templates" ~/.claude/templates
```

### Step 2: Verify configuration

Start a new Claude conversation and say:

> "What is your identity?"

Claude should respond as **CONSTRUCT** — referencing knowledge architecture, epistemic governance, and the Watson principle. If Claude responds generically, the `AGENTS.md` file is not being picked up — check the file path.

### Step 3: Point Claude at a workspace directory

Tell Claude where your workspace lives:

> "My workspace is at ~/construct-workspace"

Or, if using Claude Desktop with project directories, open the workspace folder directly.

---

## Basic Usage

### Cold start (first time)

Initialize your workspace and first domain in one go:

> "Initialize a CONSTRUCT workspace and set up a domain for [your topic]"

This runs the `cold-start` workflow, which:
1. Creates the workspace directory structure (`cards/`, `refs/`, `connections.json`, etc.)
2. Populates `governance.yaml` and `model-routing.yaml` from templates
3. Interviews you about your first knowledge domain (goals, boundaries, seed questions)
4. Writes `domains.yaml` and `search-seeds.json`
5. Runs an initial research cycle — producing seed cards and a digest

After cold start, you should see:
```
workspace/
├── cards/           # 3–10 seed cards from initial research
├── refs/            # Source references for those cards
├── connections.json # Initial connections between cards
├── domains.yaml     # Your first domain configured
├── governance.yaml  # Default curation thresholds
├── search-seeds.json
├── digests/         # First research digest
└── log/events.jsonl # Audit trail of all operations
```

### Daily use

**Research a topic:**
> "Research the latest developments in [topic]"

Claude switches to Researcher role, runs web search, extracts findings, creates cards with source references, and produces a digest.

**Check graph status:**
> "How's my knowledge graph looking?"

Returns card counts by domain and lifecycle state, connection statistics, confidence distribution, and flags any issues.

**Curate the graph:**
> "Run curation"

Claude switches to Curator role: validates card integrity, checks for confidence decay on aging cards, promotes strong seeds, flags orphans, and reports what changed.

**Find gaps:**
> "What gaps do you see in [domain]?"

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
> "What surprising connections exist between [domain A] and [domain B]?"

Claude runs bridge detection, identifying structural parallels and shared concepts across domains.

### Domain management

**Add a new domain:**
> "I want to start tracking [new topic]"

Runs the domain initialization interview — asks about scope, boundaries, seed questions, and configures search patterns.

**Pause a domain:**
> "Pause research on [domain]"

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
