# CONSTRUCT — Product Brief

**Version:** 2.0.0
**Date:** 2026-04-21
**Authors:** ;-)mab (human) + CONSTRUCT (co-author)
**Status:** Active — pre-implementation planning complete

> Technical architecture, storage model, interaction protocols, and implementation scope are in the companion **[Product Requirements Document (construct-prd.md)](construct-prd.md)**.

---

## 1. What Is CONSTRUCT?

CONSTRUCT is an open-source, agent-powered personal knowledge system. It helps a single user (or small team) systematically collect, curate, connect, and compound knowledge across multiple domains — and then produce high-quality outputs (whitepapers, essays, visualizations, narrative work) as derived views of that accumulated knowledge.

It is not a note-taking app. It is not a chatbot with memory. It is a **knowledge architecture with agency** — where specialized AI agents do the legwork of research, curation, connection-building, and synthesis under human direction, and the knowledge graph is the central artifact everything else serves.

**One-line pitch:** *An AI-native knowledge system where agents curate what you learn, and everything you produce grows from what you know.*

---

## 2. The Problem

### What exists today

| Category | Tools | What's missing |
|----------|-------|----------------|
| Note-taking | Obsidian, Notion, Logseq | No agency. The human does all curation, linking, gap-identification manually. Knowledge rots silently. |
| AI assistants | ChatGPT, Claude, Perplexity | No persistent knowledge. Every conversation starts from zero. No structured memory across sessions. |
| Research tools | Semantic Scholar, Zotero, Elicit | Single-domain. No cross-domain connection-building. No ongoing automated research cycles. |
| Knowledge graphs | Neo4j, Obsidian Graph View | Visualization without curation intelligence. The graph grows but nobody tends it. |
| Agent frameworks | AutoGPT, CrewAI, LangGraph | Task execution, not knowledge accumulation. Agents complete tasks and forget. No institutional memory. |

### The gap

No tool combines all of:

1. **Persistent, structured knowledge** that accumulates across sessions and compounds over time
2. **Active curation agents** that evaluate, connect, flag gaps, and identify decay — not just store
3. **Automated research cycles** that continuously feed the knowledge base under human-steered search patterns
4. **Cross-domain intelligence** — the system notices when a topology paper and a robotics architecture share a structural parallel
5. **Generative output** (papers, essays, narratives, visualizations) derived from knowledge state, not generated from scratch each time
6. **Epistemic governance** — every claim carries its confidence level, source tier, and register label

CONSTRUCT fills this gap.

---

## 3. Core Concepts

### 3.1 The Knowledge Graph Is the Product

Everything else — agents, UI, outputs, visualizations — exists to serve the knowledge graph. The graph is not a feature; it is the system's central nervous system.

A knowledge entry (card/note) is an atomic, structured markdown file with:

- **Epistemic type** — what role this card plays in the graph: finding, theme, gap, provocation, concept, method, paper, claim, question, connection (structural — built into CONSTRUCT)
- **Content categories** — what domain concept this card is about: user-defined taxonomy labels per domain (e.g., "foundation models," "spatial reasoning," "RL algorithms"). Hierarchical when needed, flat to start. Evolve as the domain matures.
- **Confidence level** (1–5) — speculative through foundational
- **Source tiering** (Tier 1–5) — peer-reviewed through unverified
- **Typed connections** — supports, contradicts, extends, parallels, requires, enables, challenges, inspires
- **Domain tags** — from a user-configurable taxonomy
- **Lifecycle state** — seed, growing, mature, archived
- **Decay tracking** — entries not referenced within a configurable window get flagged for review

**Why two classification axes:** Epistemic type answers "show me all gaps" or "show me all contested claims." Content category answers "show me everything about foundation models." Combining them answers "show me all gaps in spatial reasoning" — which is where the real power lives.

The graph is stored as markdown files (source of truth) with a derived computational graph rebuilt on demand for traversal and query. See [knowledge-card-schema.md](knowledge-card-schema.md) for the canonical schema.

### 3.2 CONSTRUCT Is Both the Product and the Agent

CONSTRUCT is the overarching agentic identity — the thinking partner, the cross-domain mind, the one the user talks to. It inherits the Watson principle (think alongside, not behind) and the co-authorship capability, but it is not one agent among many. It is the intelligence layer that orchestrates specialized sub-agents.

The user talks to CONSTRUCT. CONSTRUCT delegates to specialists.

```
Human
  │
  └── CONSTRUCT (thinking partner, co-author, orchestrator)
        │
        ├── Curator       (knowledge graph maintenance, quality gates)
        ├── Researcher     (search cycles, extraction, ingestion)
        ├── Synthesizer    (drafting from graph state)
        └── Narrator       (publication voice rendering)
```

**CONSTRUCT (the identity)** does the high-cognitive work directly: cross-domain ideation, synthesis, editorial judgment, co-authorship, strategic thinking. When you brainstorm with CONSTRUCT, it draws on the Curator's maintained graph, the Researcher's latest findings, and the Synthesizer's drafts. CONSTRUCT doesn't do the maintenance — it does the thinking.

**Sub-agents** are functional specialists:

| Sub-agent | Function | Cognitive demand | Runs autonomously? |
|-----------|----------|------------------|---------------------|
| **Curator** | Promote/reject cards, maintain connections, flag decay, enforce quality gates | Medium | Yes — routine curation on heartbeat. Escalates when judgment needed. |
| **Researcher** | Search cycles, API extraction, structured ingestion, reference resolution | Low–Medium | Yes — runs on configured cadence. Reports findings for Curator review. |
| **Synthesizer** | Draft essays, whitepapers, gap analyses from graph state | High | Partially — produces drafts, CONSTRUCT reviews and edits. |
| **Narrator** (optional) | Render final output in publication voice, register-aware epistemic framing | High | No — CONSTRUCT or human directs. |

The Curator runs cheap (mostly graph queries, occasional workhorse LLM calls). CONSTRUCT only gets involved when the Curator surfaces something that needs judgment: *"Three cards contradict each other. Your call."*

Users can activate, deactivate, or extend sub-agents. The Curator and Researcher are mandatory. The others are opt-in.

> Detailed agent specifications, v0.1 scope boundaries, and LLM tier routing are in the [PRD](construct-prd.md).

### 3.3 The Research Cycle Is Continuous

CONSTRUCT doesn't wait for the user to ask questions. It runs a continuous research loop:

```
Search Pattern → Agent Content Hunt → Ingest into Knowledge Graph
       ↑                                         ↓
       └── User Adapts Pattern ← Landscape Update ← Curator Reviews
```

The search pattern is a first-class, inspectable, historized artifact. The user can see exactly what the system is looking for, how it changed over time, and why. Pattern adaptation is always human-triggered (autonomous adaptation is a future feature with explicit opt-in).

### 3.4 Epistemic Governance Is Not Optional

Every claim in the system carries metadata:

- **Source tier** — where does this come from? (peer-reviewed journal vs. Twitter thread)
- **Confidence** — how sure are we? (speculative vs. foundational)
- **Register** — what mode of thinking produced this? (research, hypothesis, inference, art)

This propagates into all outputs. A whitepaper draft inherits the confidence levels of the knowledge cards it draws from. A visualization can color-code by certainty. The user always knows what they're looking at.

### 3.5 Evolution Is Built In

Agents advance through a version ladder:

```
v0.1  Research & Collection
v0.2  Synthesis & Drafting
v0.3  Co-authorship (human leads)
v0.4  Guided Autonomy (human reviews)
v0.5  Public Voice (human approves)
```

Each advance requires demonstrated competence and explicit human approval. This creates a trust gradient — new agents start constrained, earn autonomy through performance.

### 3.6 Cross-Domain Detection Is the Differentiator

The ability to detect connections across domains — noticing when a topology paper and a robotics architecture share a structural parallel — is CONSTRUCT's differentiating capability. No existing tool does this well.

Cross-domain detection is a **layered capability** that progresses from cheap graph queries to expensive frontier reasoning:

- **Graph structural** — bridge detection, connection propagation across domain boundaries. Free, runs continuously.
- **Keyword/tag overlap** — cards sharing metadata across domains get flagged. Free, runs on curation cycle.
- **Embedding similarity** (v0.2) — semantic matching catches what keyword overlap misses at scale.
- **LLM reasoning** (v0.2+) — frontier model reasons about deep structural parallels invisible to embeddings.

Each layer feeds the one above it. The human remains the final judge of whether a proposed cross-domain parallel is genuine or superficial.

> Detailed layer specifications, triggers, cost models, and release targets are in the [PRD](construct-prd.md).

---

## 4. User Interactions

CONSTRUCT supports these interaction patterns — through whatever UI surfaces are built:

### 4.1 Knowledge Domain Management

#### Initialize a domain

Define a new knowledge domain from scratch. A domain is a bounded area of inquiry with its own taxonomy, search patterns, and source priorities.

- **Name and scope** — what is this domain about? What's inside / outside its boundary?
- **Taxonomy tags** — initial category vocabulary for the domain
- **Search seeds** — initial terms, authors, papers, or questions that anchor the first research cycles
- **Source priorities** — which source types matter most for this domain?
- **Cross-domain connections** — known overlaps with existing domains

#### Configure and update a domain

- Adjust search patterns — add new clusters, deprecate exhausted ones, shift weight
- Evolve the taxonomy — add, rename, merge, or retire category tags
- Tune source tiers — promote or demote source types
- Set thresholds — minimum confidence for auto-promotion, decay window, orphan tolerance
- Pause / resume research cycles without losing state

#### Browse domain state

- Landscape overview — major clusters, sizes, interconnections
- Coverage heatmap — well-populated vs. sparse categories
- Gap inventory — questions without answers, speculative-only clusters
- Confidence distribution — histogram across the domain
- Recency view — what's aging out?

#### Review domain evolution

- Landscape diff — compare snapshots between two dates
- Search pattern history — how research focus migrated over time
- Promotion timeline — when key cards progressed through lifecycle stages
- Connection growth — cluster merging or isolation over time

### 4.2 Knowledge Graph Interaction

#### Browse the graph

- **Force-directed visualization** — nodes = cards, edges = typed connections. Filterable by domain, confidence, type, category, recency.
- **Cluster view** — grouped by domain or category, showing density and cross-cluster bridges
- **Timeline view** — cards arranged chronologically
- **Heatmap** — 2D grid (domain × confidence, category × lifecycle)
- **List view** — sortable, filterable table

#### Drill into a card

- Core content, metadata panel, evidence trail
- Connection map — mini-graph of immediate neighborhood
- Open questions attached to this card
- Full changelog / history
- Decay status

#### Add knowledge

- **Add a card** — full manual entry with all metadata
- **Add a seed** — lightweight: a URL, paper title, question, or hunch. System ingests and structures.
- **Quick capture** — minimal friction paste. System does the rest.
- **Batch import** — bibliography, reading list, or bookmarks

#### Card Types

Cards have two classification axes: **epistemic type** (structural role) and **content category** (domain concept).

**Epistemic types** (built into CONSTRUCT):

| Type | Purpose | Example |
|------|---------|---------|
| **Finding** | A factual result or observation | "GPT-4V scores 87% on spatial reasoning benchmarks" |
| **Claim** | An assertion that may be contested | "Transformer attention is sufficient for spatial reasoning" |
| **Concept** | A defined term or abstraction | "Successor representation" |
| **Method** | A technique, algorithm, or process | "RLHF fine-tuning pipeline" |
| **Paper** | A reference to a specific publication | "Driess et al. 2023 — PaLM-E" |
| **Theme** | A recurring pattern across multiple cards | "Embodiment as grounding for language models" |
| **Gap** | An identified absence of knowledge | "No benchmarks for multi-agent spatial coordination" |
| **Provocation** | A speculative or contrarian idea | "What if world models don't need vision at all?" |
| **Question** | An open inquiry awaiting investigation | "How does the SR generalize to continuous state spaces?" |
| **Connection** | A meta-card documenting a non-obvious link | "Topology ↔ robotics: shared structure in path planning" |

**Content categories** are domain-specific, user-defined taxonomy labels that evolve as the domain matures. Hierarchical when needed, flat to start.

#### Visualization types

| Visualization | What it reveals | Best for |
|---------------|----------------|----------|
| Force-directed graph | Topological structure — clusters, bridges, orphans | Exploring connections |
| Cluster map | Domain/category groupings with inter-cluster edges | Coverage balance |
| Timeline | Temporal evolution of knowledge | Research momentum |
| Confidence heatmap | Distribution of certainty | Solid vs. speculative regions |
| Source-tier overlay | Color-coded by evidence quality | Epistemic strength |
| Decay map | Aging/stale cards highlighted | Maintenance prioritization |
| Path trace | Route between two cards | Understanding connection chains |
| Bridge view | Hub nodes connecting separate clusters | Cross-domain insights |
| Diff view | Graph comparison at two points in time | Evolution review |

### 4.3 Research Configuration

- View current search pattern
- Adjust search seeds — add terms, shift weights, add clusters
- Configure sources — which APIs, feeds, RSS
- Set cadence — research cycle frequency
- Review research history — past digests, ingestions, rejections

### 4.4 Output Generation

CONSTRUCT produces outputs derived from graph state. Every output carries the epistemic metadata of its source cards.

#### Output types

| Output type | Description |
|-------------|-------------|
| **Article** | Long-form, register-aware writing. Targets different audiences. |
| **Overview / Summary** | State-of-knowledge briefing for a domain or topic. |
| **Gap analysis** | Missing knowledge: unanswered questions, thin clusters, contradictions. |
| **Mindmap** | Hierarchical visual export of a topic's structure. |
| **Tutorial** | Educational content with learning progression from the graph. |
| **Exercises** | Practice problems and review questions derived from the graph. |
| **Insight collection** | Best-of digest — cross-domain provocations, breakthroughs. |
| **Landscape report** | Full domain status: coverage, velocity, confidence, gaps. |
| **Whitepaper** | Rigorous, citation-backed deep dive with evidence chains. |
| **Visualization export** | Static/interactive graph renders (HTML, SVG, PNG). |
| **Structured data export** | JSON, CSV, GraphML for downstream tools. |

#### Output workflow

1. **Request** — human specifies type, scope, constraints
2. **Draft** — Synthesizer produces from graph state with card references
3. **Review** — human reviews; CONSTRUCT highlights speculative vs. foundational sections
4. **Iterate** — co-edit: "Strengthen X" pulls more evidence; "This feels weak" triggers gap check
5. **Publish** — final render in target format with metadata preserved or stripped

### 4.5 System Monitoring

- Agent status — active agents, versions, current tasks
- Knowledge health — decay alerts, orphan count, confidence distribution
- Research cycle history — content hunts, ingestions, landscape updates
- Memory log — learned user preferences and corrections

---

## 5. Open-Source Positioning

### The contribution to the ecosystem

No open-source tool currently offers the combination of: structured knowledge with epistemic metadata + active AI curation agents + continuous research automation + cross-domain intelligence + generative output from knowledge state.

| Closest relative | What's different |
|-----------------|------------------|
| Obsidian + plugins | No agency, no automated curation |
| Khoj | AI search, not structured knowledge accumulation |
| Mem.ai | Proprietary, not knowledge-graph-native |
| Logseq + GPT plugins | No continuous research cycle or agent specialization |

CONSTRUCT would be the first open-source system where the knowledge graph is a first-class, governed, agent-maintained artifact — not a byproduct of note-taking.

### Release roadmap

| Release | Theme | Key additions |
|---------|-------|---------------|
| **v0.1** | Research & Collection | Curator + Researcher agents, knowledge graph, React UI, CLI |
| **v0.2** | Synthesis & Drafting | Synthesizer agent, export pipeline, Telegram bridge, ChromaDB |
| **v0.3** | Publication & Collaboration | Narrator agent, publishing pipeline, web dashboard, team features |

> Detailed MVP scope and deferred features are in the [PRD](construct-prd.md).

---

## 6. Naming — Product and Identity Unified

**CONSTRUCT** is both the product name and the overarching agent identity. The product *is* the agent. The agent *is* the product.

When a user says "I asked CONSTRUCT about this," they mean both the system and the entity. This unification is intentional — CONSTRUCT is not a tool that contains an AI assistant. It is an AI-native knowledge system whose primary interface is a thinking partner that shares its name.

**The name works on four levels:**

- **A verb** — "construct knowledge" — active, intentional, not passive accumulation
- **A noun** — "a construct" — a structured, purposeful creation
- **An identity** — CONSTRUCT is the agent you talk to. It inherits the Watson principle (think alongside, not behind), but the name signals that this is a builder, not a sidekick.
- **A reference** — to constructivist epistemology: knowledge is built, not received

**Lineage:** CONSTRUCT inherits from Watson (the thinking partner identity developed in the MABSTRUCT workspace). Watson's SOUL, IDENTITY, voice, and co-authorship principles form the foundation of CONSTRUCT's agent identity.

---

## 7. Open Questions

### Product

1. **How much governance is configurable?** Source tiering, confidence levels, and evolution ladder are currently baked into governance documents. Should users be able to reconfigure these? Probably yes — with good defaults.

2. **Contribution model?** Agent definitions (SOUL, IDENTITY) are governance documents — how do community contributions to agent behavior get reviewed? Propose: PR-based model where governance changes require maintainer review, tooling follows standard open-source flow.

3. **Where does MABSTRUCT end and CONSTRUCT begin?** MABSTRUCT is the personal project. CONSTRUCT is the extracted, generalized framework. The extraction boundary must be clean: CONSTRUCT ships with empty knowledge, configurable agent templates, and example domains — not MABSTRUCT content.

> Technical architecture questions are in the [PRD §12](construct-prd.md).

---

## 8. The Bigger Picture

CONSTRUCT is not just a tool. It's a thesis about how humans and AI should work with knowledge together.

The thesis: **Knowledge systems should be active, not passive. They should curate, not just store. They should connect, not just index. They should produce, not just retrieve. And the human should steer, not operate.**

Current AI tools either do everything for you (ChatGPT: ask a question, get an answer, forget) or nothing for you (Obsidian: organize your own knowledge, manually, forever). CONSTRUCT sits in the productive middle: **AI agents do the systematic work of research, curation, connection-building, and synthesis — the human provides direction, judgment, and editorial authority.**

The knowledge compounds. The agents improve. The outputs get better over time — not because the LLM got smarter, but because the knowledge base grew richer and more connected.

That's the product. That's the open-source contribution. That's the footprint.

---

*This brief will evolve as decisions are made. For technical architecture and implementation requirements, see the companion [PRD](construct-prd.md).*
