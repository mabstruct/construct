# CONSTRUCT Agent System — Product Requirements Document

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active
**Companion:** [Product Brief (product-brief.md)](product-brief.md) — vision and concepts

---

This document defines **how** the Claude-native CONSTRUCT is configured. For **what** and **why**, see the product brief.

---

## 1. Architecture Decision

### Claude as Runtime

Instead of building a Python application, CONSTRUCT is delivered as Claude agent configuration. See [ADR-0001](adrs/adr-0001-claude-native-approach.md) for the full decision record.

### Capability Mapping

| CONSTRUCT Requirement | Claude Capability | Configuration Layer |
|----------------------|-------------------|---------------------|
| Conversational reasoning | Chat (native) | `AGENTS.md` — identity, voice, guardrails |
| Task routing | Reasoning (native) | `AGENTS.md` — routing rules |
| Research cycles | Web search (native tool) | `skills/research-cycle/SKILL.md` — structured procedure |
| Curation cycles | File read/write + reasoning | `skills/curation-cycle/SKILL.md` — structured procedure |
| Card management | File operations (native tool) | `skills/card-*/SKILL.md` + `templates/card.md` |
| Knowledge graph | `connections.json` + reasoning | `skills/bridge-detect/SKILL.md` + `templates/connections.json` |
| Synthesis / co-authorship | Long-form generation (native) | `skills/synthesis/SKILL.md` |
| Epistemic governance | Rules in agent identity | `AGENTS.md` §Epistemic Governance + `references/` |
| Session persistence | Conversation context (native) | Workspace files persist state |
| Scheduled cycles | Human-triggered | `workflows/daily-cycle.md` — session pattern |

### What Claude Does NOT Replace

| Capability | Why it's absent | Mitigation |
|-----------|-----------------|-----------|
| Persistent SQL index | Claude reads files each time | Fine for <500 cards; Python complement for scale |
| Graph visualization | Claude is text-based | `graph-status` skill produces text dashboard; future Python UI |
| Timer-based heartbeat | No background process | Human-triggered cycles; workflow cadence suggestions |
| Offline operation | Claude requires network | Workspace files are local — knowledge survives offline |
| Deterministic queries | Claude reasoning vs. SQL | Skills have explicit procedures; `connections.json` is structured |

---

## 2. Workspace Architecture

The workspace directory format is **identical** to the Python approach. This is a deliberate design decision enabling future interoperability.

### Workspace Layout

```
workspace/
├── cards/                    # SOURCE OF TRUTH: Knowledge cards (md + YAML frontmatter)
├── refs/                     # Reference library (per-source JSON)
├── connections.json          # SOURCE OF TRUTH: Knowledge graph edge list
├── domains.yaml              # Domain taxonomy definitions
├── governance.yaml           # Curator thresholds and rules
├── search-seeds.json         # Research search patterns
├── digests/                  # Research cycle outputs
│   └── {domain}/
│       └── digest-{date}.md
├── publish/                  # Curated outputs (articles, reports, drafts)
│   └── drafts/
└── log/
    └── events.jsonl          # Append-only audit trail
```

### Storage Categories

| Category | Git-tracked | Purpose |
|----------|------------|---------|
| **Source of Truth** | Yes | Cards, connections, governance, config, events |
| **Agent Output** | Yes | Refs, digests, publish |
| **Transient** | No (.gitignore) | None in Claude-native (no db/, no views/) |

**Simplification vs. Python approach:** No `db/`, `views/`, or `inbox/` directories. Claude reads source of truth directly. No derived indexes needed.

### Workspace Initialization

The `workspace-init` skill creates this structure from templates in `CONSTRUCT-agents/templates/`.

---

## 3. Configuration Architecture

CONSTRUCT is delivered as a directory of configuration files:

### 3.1 Configuration Layers

```
CONSTRUCT-agents/
├── AGENTS.md                 # Layer 1: Identity — who CONSTRUCT is
├── agents/                   # Layer 2: Roles — specialized modes
├── skills/                   # Layer 3: Procedures — what to do step-by-step
├── workflows/                # Layer 4: Orchestration — multi-skill sequences
├── references/               # Layer 5: Vocabulary — shared lookup tables
└── templates/                # Layer 6: Artifacts — file format templates
```

**Layer 1 — Identity (`AGENTS.md`):**
Root agent definition. Loaded into every conversation. Defines voice, behavior rules, task routing, guardrails, epistemic governance. This is CONSTRUCT's "soul."

**Layer 2 — Roles (`agents/*.md`):**
Specialized behavioral modes. Claude switches into a role when performing domain-specific work. Each role has its own responsibilities, decision rules, and escalation triggers.

**Layer 3 — Skills (`skills/*/SKILL.md`):**
Step-by-step procedures for complex operations. A skill is invoked by name, follows a defined procedure, produces defined outputs, and has validation criteria. Skills are the "code" of this system.

**Layer 4 — Workflows (`workflows/*.md`):**
Multi-skill orchestration sequences. A workflow chains skills together for end-to-end user journeys. Workflows define transition triggers and failure recovery.

**Layer 5 — References (`references/*.md`):**
Shared vocabulary tables. Enum definitions, scoring rubrics, decision guides. Referenced by skills and agents to ensure consistency.

**Layer 6 — Templates (`templates/`):**
File format templates for workspace artifacts. Ensure structural consistency across all created files.

### 3.2 Configuration Deployment

To deploy CONSTRUCT:

1. Copy `CONSTRUCT-agents/` to Claude's configuration directory
2. Point Claude at a workspace directory
3. Start a conversation

No build step. No compilation. No installation.

### 3.3 Skill Invocation

Skills are invoked through natural language matching:

| User says | Skill triggered |
|-----------|----------------|
| "Initialize a workspace" | `workspace-init` |
| "Add a domain" | `domain-init` |
| "Add this paper: {url}" | `card-create` |
| "Research {topic}" | `research-cycle` |
| "Curate" / "Clean up" | `curation-cycle` |
| "What gaps do you see?" | `gap-analysis` |
| "Draft a paper on..." | `synthesis` |
| "Graph status" | `graph-status` |
| "Shift focus to..." | `search-adjust` |
| "Find cross-domain connections" | `bridge-detect` |
| "Edit card {name}" | `card-edit` |
| "Archive card {name}" | `card-archive` |
| "Connect {A} to {B}" | `card-connect` |

CONSTRUCT also invokes skills internally (e.g., `curation-cycle` calls `card-evaluate` logic).

---

## 4. Interaction Model

### 4.1 Conversational Interface

All interaction is through Claude's conversation interface. No separate UI.

**Three interaction modes:**

| Mode | When | Example |
|------|------|---------|
| **Command** | User wants a specific action | "Research spatial reasoning" |
| **Conversational** | User wants to discuss, brainstorm, explore | "What patterns do you see across these domains?" |
| **Skill execution** | Triggered by command or workflow | CONSTRUCT runs `research-cycle` procedure |

During skill execution, CONSTRUCT follows the skill's procedure but maintains conversational tone — reporting progress, asking for clarification, presenting results.

### 4.2 Event Logging

All significant actions are logged to `log/events.jsonl`:

```json
{"ts": "2026-04-23T14:30:00Z", "agent": "researcher", "action": "research_cycle_complete", "detail": "8 papers found, 5 ingested, 3 cards created", "result": "success"}
```

Event schema:
- `ts` — ISO-8601 timestamp
- `agent` — who performed the action (construct / curator / researcher / human)
- `action` — event type (see data-schemas.md §3)
- `target` — optional: card ID, domain, or artifact affected
- `detail` — human-readable description
- `result` — success / failure / escalated

### 4.3 Workspace State as Session Memory

Claude's conversation context is ephemeral. Persistent state lives in workspace files:

| State | Where it persists |
|-------|-------------------|
| Knowledge accumulated | `cards/`, `refs/`, `connections.json` |
| Domain configuration | `domains.yaml`, `search-seeds.json` |
| Governance rules | `governance.yaml` |
| Action history | `log/events.jsonl` |
| Research progress | `digests/`, `search-seeds.json` timestamps |
| Draft outputs | `publish/` |

When starting a new conversation, CONSTRUCT reads workspace state to restore context.

---

## 5. Agent Specifications (Summary)

Detailed specs in `agent-spec-construct.md`, `agent-spec-researcher.md`, `agent-spec-curator.md`.

### CONSTRUCT (Orchestrator)

- Identity: thinking partner, co-author, knowledge architect
- Handles directly: conversation, cross-domain ideation, synthesis, editorial judgment, strategic steering
- Delegates to: Curator (maintenance), Researcher (acquisition)
- Escalation handler: receives from sub-roles when judgment needed

### Researcher (Role)

- Trigger: research requests, URL ingestion
- Process: 7-step cycle (load seeds → search → extract → score → ingest → report)
- Output: ref files, seed cards, digests
- Uses: web search, file creation

### Curator (Role)

- Trigger: curation requests, card evaluation
- Process: 7-step cycle (integrity → decay → orphans → promotions → connections → inbox → report)
- Output: card updates, connection typing, health reports
- Uses: file reading/writing, reasoning for ambiguous evaluations

---

## 6. v0.1 Scope

### Included

| # | Capability | Skill/Config |
|---|-----------|-------------|
| 1 | Workspace initialization | `workspace-init` |
| 2 | Domain initialization interview | `domain-init` |
| 3 | Card creation from conversation or URL | `card-create` |
| 4 | Card editing and updating | `card-edit` |
| 5 | Card archival with supersedes | `card-archive` |
| 6 | Connection management | `card-connect` |
| 7 | Research cycle via web search | `research-cycle` |
| 8 | Curation cycle with governance rules | `curation-cycle` |
| 9 | Card promotion evaluation | `card-evaluate` |
| 10 | Gap analysis | `gap-analysis` |
| 11 | Synthesis / drafting with confidence propagation | `synthesis` |
| 12 | Graph health reporting | `graph-status` |
| 13 | Search pattern adjustment | `search-adjust` |
| 14 | Cross-domain bridge detection (L1+L2+L3) | `bridge-detect` |
| 15 | Domain management (pause, edit, archive) | `domain-manage` |
| 16 | Epistemic governance enforcement | `AGENTS.md` + `references/` |
| 17 | Event logging | All skills log to `events.jsonl` |
| 18 | Cold start workflow | `workflows/cold-start.md` |
| 19 | Daily cycle workflow | `workflows/daily-cycle.md` |
| 20 | Co-authorship workflow | `workflows/co-authorship.md` |

### Excluded (v0.2+)

- Visual graph exploration (no D3/React)
- Persistent SQL indexing (no SQLite)
- Embedding-based similarity (no ChromaDB)
- Automated scheduling (no background heartbeat)
- Multi-user support
- External integrations (Telegram, Slack)

---

## 7. Relationship to Python Approach

The two approaches are **complementary, not competing**:

```
CONSTRUCT-agent-system-spec/   ←  This approach
CONSTRUCT-agents/              ←  Solution artifacts (config files)
                                   Deployed to: ~/.claude/

CONSTRUCT-spec/                ←  Python approach (original)
src/construct/                 ←  Solution artifacts (Python code)
                                   Deployed via: pip install
```

**Shared:**
- Workspace format (identical directory structure)
- Card schema (identical YAML frontmatter + markdown)
- Connection format (identical connections.json)
- Governance rules (identical governance.yaml)
- Domain taxonomy (identical domains.yaml)

**Implication:** A user could start with Claude-native CONSTRUCT, then later add the Python UI layer for graph visualization — both operating on the same workspace.
