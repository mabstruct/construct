# CONSTRUCT Capabilities Handbook

This document is the user-facing map of what the Claude-native CONSTRUCT
implementation can do today. It explains the available agents, skills,
workflows, intended users, common scenarios, and dependencies.

For command syntax, see `commands.md`. For detailed role behavior, see
`.claude/agents/`. For procedural implementation details, see each
`.claude/skills/*/SKILL.md` file.

---

## 1. What CONSTRUCT is

CONSTRUCT is a local-first, agent-powered personal knowledge system. It helps
you collect, curate, connect, and compound knowledge across domains, then turn
that accumulated knowledge into high-quality outputs.

In the Claude-native implementation, Claude is the runtime:

- Conversation is the primary interface.
- Markdown and JSON files are the canonical database.
- Skills are executable procedures written as Markdown.
- Agent roles are specialized operating modes.
- Workflows are multi-skill sequences for recurring user journeys.

The workspace remains the source of truth. Derived views, digests, dashboards,
and drafts can always be rebuilt from the files.

---

## 2. Who this is for

CONSTRUCT is intended for people who accumulate complex knowledge over time and
want that knowledge to become more useful with each session.

### Primary users

| User | What they need | How CONSTRUCT helps |
|------|----------------|---------------------|
| Independent researcher | Track papers, claims, gaps, and open questions | Research cycles, refs, cards, graph connections, gap analysis |
| Writer or analyst | Produce briefings, essays, reports, and memos from notes | Synthesis workflow with card citations and confidence propagation |
| Founder, strategist, or product thinker | Connect ideas across domains and turn research into decisions | Cross-domain bridge detection, graph status, co-authorship |
| Student or autodidact | Build durable understanding of a field | Domain setup, curated cards, confidence levels, lifecycle states |
| Knowledge-system maintainer | Keep a workspace coherent and auditable | Validation, curation cycles, governance rules, event logs |

### Secondary users

- Agent designers extending CONSTRUCT's skill set.
- Developers maintaining the Claude-native configuration.
- Future implementers who need the same workspace model to work across Claude
  and other runtimes.

---

## 3. Capability model

CONSTRUCT is organized around three layers:

1. **Agents**: operating identities and responsibilities.
2. **Skills**: repeatable procedures for specific operations.
3. **Workflows**: multi-skill sequences that support larger user journeys.

The normal interaction pattern is:

```text
User intent
  -> CONSTRUCT orchestrator routes the request
  -> specialist role or direct skill handles the operation
  -> workspace files are read or updated
  -> significant actions are logged
  -> user receives a calibrated summary and next options
```

---

## 4. Agents

### 4.1 CONSTRUCT orchestrator

**Definition:** `AGENTS.md`

The orchestrator is the main identity. It is the user's thinking partner,
research coordinator, knowledge curator, and co-author.

#### Intended usage

Use the orchestrator for requests that require judgment, conversation,
cross-domain reasoning, synthesis, or task routing.

#### Handles directly

- Conversational reasoning over the workspace.
- Strategic thinking about research direction and scope.
- Domain initialization interviews.
- Cross-domain ideation and bridge assessment.
- Co-authorship and editorial judgment.
- Ambiguous promotion or contradiction resolution.
- Deciding whether an unexpected finding belongs in an existing domain, a new
  domain, or should be ignored.

#### Example scenarios

- "What should I focus on next in cosmology?"
- "How does this climate-policy idea relate to my philosophy-of-science notes?"
- "Draft a position memo using what we know."
- "These two mature cards seem to conflict. Help me resolve them."

---

### 4.2 Curator

**Definition:** `.claude/agents/curator.md`

The Curator is the graph gardener. It tends what already exists.

#### Intended usage

Use the Curator when the task is maintenance, validation, cleanup, graph health,
promotion, decay, or bridge detection.

#### Core responsibilities

- Validate card schemas and required metadata.
- Detect dangling connections and broken references.
- Find orphan cards with no graph edges.
- Flag stale cards based on governance decay windows.
- Evaluate cards for lifecycle promotion.
- Type untyped connections.
- Detect duplicates or near-duplicates.
- Report graph health.
- Detect candidate cross-domain bridges.

#### Bound skills

- `construct-curation-cycle`
- `construct-card-evaluate`
- `construct-graph-status`
- `construct-bridge-detect`

#### Example scenarios

- "Curate the cosmology domain."
- "Which cards are stale?"
- "Do we have orphan cards?"
- "Find bridges between philosophy-of-mind and physics."
- "Can this seed card be promoted?"

---

### 4.3 Researcher

**Definition:** `.claude/agents/researcher.md`

The Researcher is the external knowledge hunter. It finds, extracts, scores,
and ingests new material, then hands it off for later curation.

#### Intended usage

Use the Researcher when the task involves external discovery, paper search, URL
ingestion, article ingestion, or search pattern adjustment.

#### Core responsibilities

- Load active search clusters from `search-seeds.json`.
- Generate search queries.
- Use web search to find papers, articles, reports, and other sources.
- Deduplicate against existing refs and cards.
- Extract key findings.
- Score relevance to the domain.
- Write reference files into `refs/`.
- Draft seed cards into `cards/`.
- Write research digests into `digests/`.
- Escalate anomalies to the orchestrator.

#### Bound skills

- `construct-research-cycle`
- `construct-search-adjust`

#### Example scenarios

- "Research new developments in API gateways."
- "Find papers on dark energy tension."
- "Ingest this article."
- "Adjust search toward empirical work and away from opinion pieces."

---

## 5. Skills

Skills are the executable procedures. Users normally speak in natural language;
CONSTRUCT routes the request to the right skill.

### 5.1 Entry and orientation

| Skill | What it does | Use when |
|-------|--------------|----------|
| `construct-help` | Scans workspace state and suggests next actions with a command menu | Starting a session, asking "help", or asking "what's next?" |

### 5.2 Workspace and domain setup

| Skill | What it does | Use when |
|-------|--------------|----------|
| `construct-workspace-init` | Creates a domain workspace with the canonical Phase 1 layout: `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `log/events.jsonl` (source-of-truth), `digests/`/`publish/` (derived), and `.construct/model-routing.yaml` (support). Templates from `CONSTRUCT-CLAUDE-impl/construct/templates/`. | Starting a new domain workspace |
| `construct-domain-init` | Runs the domain interview and writes domain/search configuration | Defining or revising a domain's scope, sources, and seed questions |
| `construct-domain-manage` | Lists, activates, pauses, edits, or archives domains | Managing active and paused research areas |
| `construct-workspace-validate` | Runs a 5-layer post-write audit: schema compliance, governance policy, cross-file consistency, functional health, and audit-trail completeness. Pre-write rejection is handled separately by each writing skill's validation checklist. | Auditing a workspace or diagnosing inconsistencies |

### 5.3 Card operations

| Skill | What it does | Use when |
|-------|--------------|----------|
| `construct-card-create` | Creates a knowledge card with epistemic metadata | Capturing an idea, claim, finding, gap, or source-derived insight |
| `construct-card-edit` | Updates card body or frontmatter | Correcting, refining, or reclassifying an existing card |
| `construct-card-archive` | Soft-archives a card and handles supersession | Retiring outdated or obsolete knowledge without deleting it |
| `construct-card-connect` | Creates, removes, or queries typed graph connections | Relating two cards with `supports`, `contradicts`, `extends`, etc. |
| `construct-card-evaluate` | Assesses a card for promotion, decay, or flagging | Reviewing whether a card is still valid or ready to mature |

### 5.4 Research and curation

| Skill | What it does | Use when |
|-------|--------------|----------|
| `construct-research-cycle` | Searches, extracts, scores, writes refs, drafts seed cards, and writes a digest | Discovering or ingesting external knowledge |
| `construct-search-adjust` | Tunes clusters, terms, weights, and priorities in `search-seeds.json` | Changing research direction or improving noisy searches |
| `construct-curation-cycle` | Validates, scans for decay/orphans, evaluates promotions, maintains connections, and reports health | Running regular maintenance |
| `construct-bridge-detect` | Finds cross-domain parallels and bridge candidates | Looking for surprising connections across domains |
| `construct-graph-status` | Reports card counts, lifecycle distribution, connection density, confidence, and health indicators | Asking "how is the graph?" or reviewing progress |

### 5.5 Analysis and output

| Skill | What it does | Use when |
|-------|--------------|----------|
| `construct-gap-analysis` | Identifies coverage gaps, weak areas, missing connections, and thin confidence zones | Planning research or checking readiness to write |
| `construct-synthesis` | Drafts outputs from graph context with citations and confidence propagation | Writing briefings, essays, reports, summaries, or publishable artifacts |

### 5.6 Local views and server

| Skill | What it does | Use when |
|-------|--------------|----------|
| `construct-views-scaffold` | Copies the local views SPA template into `views/src/` and prepares the app | First-time dashboard setup |
| `construct-views-build` | Builds the Vite app into `views/build/` | Preparing or refreshing the production dashboard bundle |
| `construct-views-generate-data` | Parses workspace files and writes JSON data into `views/build/data/` | Updating the dashboard data from current cards, refs, and connections |
| `construct-views-reset` | Removes generated views artifacts and per-skill virtualenv state | Resetting the dashboard implementation to a clean slate |
| `construct-up` | Starts the local views server on an available port | Opening the browser dashboard |
| `construct-down` | Stops the local views server and removes the PID file | Shutting down the dashboard server |

---

## 6. Workflows

Workflows are multi-skill sequences for larger journeys.

### 6.1 Cold Start

**Definition:** `.construct/workflows/cold-start.md`

**Purpose:** Take a new user from zero to a working workspace with a first
domain and initial graph.

**Sequence:**

```text
construct-workspace-init
-> construct-domain-init
-> construct-research-cycle
-> construct-curation-cycle
-> construct-graph-status
```

#### Intended usage

Use when creating the first domain or onboarding a fresh CONSTRUCT workspace.

#### Scenario

A user says: "Initialize a workspace for cosmology."

CONSTRUCT creates the workspace structure, runs the domain interview, seeds
search configuration, runs initial research, creates refs and seed cards,
performs light curation, and reports graph status.

---

### 6.2 Daily Cycle

**Definition:** `.construct/workflows/daily-cycle.md`

**Purpose:** Keep an existing domain fresh, coherent, and ready for use.

**Sequence:**

```text
construct-research-cycle
-> construct-curation-cycle
-> construct-graph-status
-> user interaction
```

Possible follow-up branches:

- `construct-card-create`
- `construct-gap-analysis`
- `construct-search-adjust`
- `construct-synthesis`
- direct conversation with the orchestrator

#### Intended usage

Use during regular maintenance sessions or when returning to a workspace after
a gap.

#### Scenario

A user says: "What's new in my API gateways domain?"

CONSTRUCT checks the last research cycle, searches for new material, ingests
novel results, curates the graph, refreshes status, and suggests next actions.

---

### 6.3 Co-Authorship

**Definition:** `.construct/workflows/co-authorship.md`

**Purpose:** Produce a high-quality written output from accumulated knowledge.

**Sequence:**

```text
construct-gap-analysis
-> optional construct-research-cycle
-> construct-synthesis
-> iterate with user
-> finalize
```

#### Intended usage

Use when the user wants a briefing, essay, report, memo, annotated bibliography,
or other publishable artifact.

#### Scenario

A user says: "Draft a briefing on inflation models using what we know."

CONSTRUCT checks graph readiness, reports strong and thin areas, offers to fill
gaps first, drafts from cards with confidence-aware language, cites source
cards, iterates with the user, and finalizes the artifact in `publish/`.

---

## 7. Common use scenarios

### Scenario A: Start a new research domain

Use when the user wants to begin tracking a new field or project.

Typical path:

```text
construct-workspace-init -> construct-domain-init -> construct-research-cycle
```

Result:

- Domain workspace exists.
- Governance and search files are initialized.
- Initial refs and cards are created.
- The graph has a starting shape.

### Scenario B: Capture knowledge from conversation

Use when an important idea emerges during discussion.

Typical path:

```text
construct-card-create -> construct-card-connect -> construct-graph-status
```

Result:

- The insight becomes a card.
- Metadata captures confidence, source tier, epistemic type, and lifecycle.
- Connections place the card in graph context.

### Scenario C: Research what changed

Use when the user asks what is new in a domain or topic.

Typical path:

```text
construct-research-cycle -> construct-curation-cycle -> construct-graph-status
```

Result:

- New sources are found and deduplicated.
- Relevant sources become refs and possibly seed cards.
- A digest records what changed.
- The graph is checked after ingestion.

### Scenario D: Clean up a messy graph

Use when the workspace has many cards, stale claims, or weak connections.

Typical path:

```text
construct-workspace-validate -> construct-curation-cycle -> construct-graph-status
```

Result:

- Schema and connection problems are surfaced.
- Stale or orphan cards are flagged.
- Promotion candidates are identified.
- Health metrics summarize the graph.

### Scenario E: Find cross-domain insight

Use when the user wants surprising connections between domains.

Typical path:

```text
construct-bridge-detect -> construct-card-connect -> construct-synthesis
```

Result:

- Candidate bridges are proposed.
- Strong bridges can become typed graph edges.
- Outputs can highlight cross-domain insight explicitly.

### Scenario F: Write from the graph

Use when the user wants an external artifact.

Typical path:

```text
construct-gap-analysis -> optional construct-research-cycle -> construct-synthesis
```

Result:

- Readiness is assessed before drafting.
- Thin sections are identified rather than hidden.
- The output cites source cards and propagates confidence.

### Scenario G: Use the browser dashboard

Use when the user wants a visual or navigable view of the workspace.

Typical path:

```text
construct-views-scaffold -> construct-views-build -> construct-views-generate-data -> construct-up
```

Result:

- The dashboard app is available locally.
- Data is generated from canonical workspace files.
- The server can be started and stopped without changing the knowledge base.

---

## 8. Dependencies

### Required for core CONSTRUCT usage

| Dependency | Why it is needed |
|------------|------------------|
| Claude with file access | Claude is the runtime and must read/write workspace files |
| A CONSTRUCT install root | Contains `AGENTS.md`, `.claude/`, and `.construct/` |
| Markdown and JSON workspace files | Canonical storage for cards, refs, connections, config, and logs |
| Templates | Provide consistent structure for cards, refs, digests, publish artifacts, and config |
| Reference tables | Define confidence levels, source tiers, epistemic types, lifecycle states, and connection types |

### Required for research capabilities

| Dependency | Why it is needed |
|------------|------------------|
| Web search access | Needed for `construct-research-cycle` |
| Web fetch or article access | Needed when ingesting specific URLs or papers |
| `search-seeds.json` | Provides active clusters, terms, and priorities |
| `governance.yaml` | Provides relevance and card-creation thresholds |

### Required for local views

| Dependency | Why it is needed |
|------------|------------------|
| Node.js 20+ | Builds and serves the Vite/React dashboard |
| Python 3.10+ | Runs data generation helpers |
| `views/src/` | Dashboard source copied by `construct-views-scaffold` |
| `views/build/` | Production bundle and generated data location |

### Optional but useful

| Dependency | Why it is useful |
|------------|------------------|
| Git | Versioning workspace and configuration changes |
| A browser | Viewing the local dashboard |
| Existing source lists, papers, or URLs | Improves domain initialization and research precision |

---

## 9. Operating boundaries

### What CONSTRUCT does well

- Maintains a local-first knowledge graph.
- Keeps claims epistemically labeled.
- Turns research findings into structured cards.
- Builds connections across ideas and domains.
- Produces drafts with source-card grounding.
- Surfaces gaps and uncertainty instead of hiding them.

### What CONSTRUCT does not do by default

- It does not replace human editorial control.
- It does not hard-delete cards without explicit confirmation.
- It does not treat speculative cards as established knowledge.
- It does not require a Python backend, database server, auth system, or cloud
  service for the v0.1/v0.2 Claude-native path.
- It does not make derived views canonical; files remain the source of truth.

---

## 10. Choosing the right capability

| User intent | Start with |
|-------------|------------|
| "I am new; set this up" | Cold Start workflow |
| "What should I do next?" | `construct-help` |
| "Find new material" | Researcher / `construct-research-cycle` |
| "Clean this up" | Curator / `construct-curation-cycle` |
| "Is my graph healthy?" | `construct-graph-status` |
| "What are we missing?" | `construct-gap-analysis` |
| "Connect these ideas" | Orchestrator plus `construct-card-connect` |
| "Find surprising cross-domain links" | `construct-bridge-detect` |
| "Write something from the graph" | Co-Authorship workflow |
| "Show me the dashboard" | `construct-up` after views setup |

---

## 11. Where to look next

- `commands.md`: user-facing command quick reference.
- `.claude/agents/curator.md`: Curator role details.
- `.claude/agents/researcher.md`: Researcher role details.
- `.construct/workflows/cold-start.md`: first-session workflow.
- `.construct/workflows/daily-cycle.md`: regular maintenance workflow.
- `.construct/workflows/co-authorship.md`: writing workflow.
- `.construct/references/`: governance vocabulary and enums.
- `.construct/templates/`: canonical file templates.
