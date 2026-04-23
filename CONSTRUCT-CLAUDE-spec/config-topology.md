# CONSTRUCT Agent System — Configuration Topology

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active

---

## 1. Solution Artifacts (`CONSTRUCT-CLAUDE-impl/`)

The complete CONSTRUCT system as Claude configuration:

```
CONSTRUCT-CLAUDE-impl/
├── README.md                          # Deployment guide and overview
├── AGENTS.md                          # Root agent identity (CONSTRUCT orchestrator)
│
├── agents/                            # Role definitions
│   ├── curator.md                     # Graph gardener, quality gates
│   └── researcher.md                  # Knowledge acquisition
│
├── skills/                            # Executable procedures
│   ├── workspace-init/SKILL.md        # Create workspace from templates
│   ├── domain-init/SKILL.md           # Domain interview
│   ├── domain-manage/SKILL.md         # Pause, edit, archive domains
│   ├── card-create/SKILL.md           # Create knowledge card
│   ├── card-edit/SKILL.md             # Edit existing card
│   ├── card-archive/SKILL.md          # Archive card with supersedes
│   ├── card-connect/SKILL.md          # Manage connections
│   ├── card-evaluate/SKILL.md         # Promotion evaluation
│   ├── research-cycle/SKILL.md        # 7-step research cycle
│   ├── curation-cycle/SKILL.md        # 7-step curation cycle
│   ├── gap-analysis/SKILL.md          # Coverage and structural gaps
│   ├── synthesis/SKILL.md             # Drafting with confidence propagation
│   ├── graph-status/SKILL.md          # Health dashboard
│   ├── search-adjust/SKILL.md         # Search pattern management
│   ├── bridge-detect/SKILL.md         # Cross-domain bridge detection
│   └── workspace-validate/SKILL.md    # Workspace integrity audit
│
├── workflows/                         # Multi-skill sequences
│   ├── cold-start.md                  # J1: First-time setup
│   ├── daily-cycle.md                 # J2: Regular maintenance
│   └── co-authorship.md              # J3: Drafting from knowledge
│
├── references/                        # Lookup tables
│   ├── epistemic-types.md             # 10 card roles
│   ├── confidence-levels.md           # 1–5 certainty scale
│   ├── source-tiers.md               # 1–5 provenance scale
│   ├── connection-types.md            # 9 edge relations
│   └── lifecycle-states.md            # seed → growing → mature → archived
│
└── templates/                         # File format templates
    ├── card.md                        # Knowledge card
    ├── domains.yaml                   # Domain taxonomy
    ├── governance.yaml                # Governance thresholds
    ├── model-routing.yaml             # LLM tier routing (informational)
    ├── search-seeds.json              # Search patterns
    ├── connections.json               # Empty graph edge list
    ├── digest.md                      # Research cycle digest
    ├── ref.json                       # Reference entry
    └── publish.md                     # Output artifact
```

---

## 2. Specification Artifacts (`CONSTRUCT-CLAUDE-spec/`)

Design documentation for the Claude-native approach:

```
CONSTRUCT-CLAUDE-spec/
├── README_FIRST.md                    # Navigation guide
├── product-brief.md                   # Product vision
├── prd.md                             # Technical requirements
├── knowledge-card-schema.md           # Canonical card format
├── data-schemas.md                    # All workspace file schemas
├── user-journeys.md                   # J1–J3 reference journeys
├── nfrs.md                            # Non-functional requirements
├── validation-strategy.md             # How to verify correctness
├── development-strategy.md            # Phased config plan
├── process.md                         # How we evolve the config
├── config-topology.md                 # This file — directory layout
│
├── agent-spec-construct.md            # Orchestrator specification
├── agent-spec-researcher.md           # Researcher specification
├── agent-spec-curator.md              # Curator specification
│
└── adrs/                              # Architecture decisions
    └── adr-0001-claude-native-approach.md
```

---

## 3. Runtime Workspace (Created by Skills)

The workspace created by `workspace-init` and populated by skills:

```
{workspace}/
├── cards/                             # Knowledge cards (md + YAML frontmatter)
│   └── {id}.md
├── refs/                              # Reference entries (JSON per source)
│   └── {id}.json
├── connections.json                   # Knowledge graph edge list
├── domains.yaml                       # Domain taxonomy
├── governance.yaml                    # Governance thresholds
├── search-seeds.json                  # Research search patterns
├── digests/                           # Research cycle reports
│   └── {domain}/
│       └── digest-{date}.md
├── publish/                           # Curated outputs
│   └── drafts/
│       └── {slug}.md
├── log/
│   └── events.jsonl                   # Audit trail
└── .gitignore                         # Ignore transient files
```

### Comparison to Python Approach Workspace

| Directory | Python approach | Claude-native | Notes |
|-----------|----------------|---------------|-------|
| `cards/` | ✅ | ✅ | Identical |
| `refs/` | ✅ | ✅ | Identical |
| `connections.json` | ✅ | ✅ | Identical |
| `domains.yaml` | ✅ | ✅ | Identical |
| `governance.yaml` | ✅ | ✅ | Identical |
| `search-seeds.json` | ✅ | ✅ | Identical |
| `digests/` | ✅ | ✅ | Identical |
| `publish/` | ✅ | ✅ | Identical |
| `log/events.jsonl` | ✅ | ✅ | Identical |
| `db/` | ✅ (SQLite) | ❌ (not needed) | No persistent index |
| `views/` | ✅ (heartbeat) | ❌ (not needed) | No React UI |
| `inbox/` | ✅ (UI writeback) | ❌ (not needed) | No async action queue |
| `model-routing.yaml` | ✅ (controls routing) | 🟡 (informational) | Claude handles all tasks |
| `workflows/` | ✅ (SKILL.md files) | ❌ (in config, not workspace) | Skills live in CONSTRUCT-CLAUDE-impl/ |

**The shared subset is sufficient for workspace portability.** A workspace created by the Claude-native approach can be consumed by a future Python-approach tool (adding indexing, UI, etc.).

---

## 4. Deployment Target

The entire `CONSTRUCT-CLAUDE-impl/` directory is self-contained. Deployment:

```bash
# Copy to Claude's configuration directory
cp -r CONSTRUCT-CLAUDE-impl/ ~/.claude/CONSTRUCT/

# Or symlink for development
ln -s $(pwd)/CONSTRUCT-CLAUDE-impl ~/.claude/CONSTRUCT
```

The exact deployment location depends on the Claude surface:
- **Claude Code:** `~/.claude/` or project-level `.claude/`
- **Claude Desktop:** Application-specific config directory
- **Claude API:** Configuration provided as system prompt + tool definitions
