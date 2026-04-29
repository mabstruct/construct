# LLM-Wiki Developments and Comparison with mabstruct.ai

**Date:** 27 April 2026  
**Focus:** New developments around Andrej Karpathy’s LLM-Wiki idea file, related apps/research/discussion, and strategic comparison with mabstruct.ai.

---

## Executive Summary

Andrej Karpathy’s **LLM-Wiki** is not simply “RAG with markdown.” It is a shift from **query-time retrieval** to **ingest-time synthesis**: the LLM reads curated sources, compiles them into a persistent, interlinked wiki, and then uses that wiki as a maintained knowledge substrate.

The core architecture has three layers:

1. **Raw sources** — immutable source material.
2. **Wiki** — LLM-maintained markdown pages with cross-references.
3. **Schema / agent instructions** — rules that guide ingestion, updating, querying, linting, and maintenance.

The post has already produced a visible ecosystem: Claude Code skills, Obsidian/Logseq integrations, MCP-based apps, local-first markdown tools, research-lifecycle platforms, temporal knowledge graphs, and agent-memory research systems. The deeper trend is not “wiki tooling” but **agentic long-term knowledge management**.

Compared with **mabstruct.ai**, the LLM-Wiki pattern is highly relevant but narrower. LLM-Wiki provides a practical pattern for maintaining knowledge artifacts. Mabstruct.ai can be positioned more ambitiously as an **agentic knowledge-construction and conceptual-synthesis system**: a system for long-horizon research, reflection, cross-domain synthesis, and human-governed intellectual development.

---

## 1. Karpathy’s LLM-Wiki Pattern

Karpathy’s gist describes LLM-Wiki as a pattern for building personal knowledge bases with LLMs. It is explicitly an **idea file** meant to be pasted into an LLM agent such as Codex, Claude Code, OpenCode, or similar tools, rather than a complete product specification.

The key idea is that an LLM should not merely retrieve chunks from raw documents at query time. Instead, it should maintain a persistent, evolving wiki:

- Raw material remains immutable.
- The wiki becomes the synthesized, human-readable knowledge layer.
- The agent updates pages, links related ideas, identifies contradictions, and maintains structure over time.

A useful formulation is:

> Obsidian is the IDE.  
> The LLM is the programmer.  
> The wiki is the codebase.

This metaphor is powerful because it turns knowledge work into something closer to software maintenance: diffs, files, links, conventions, schema, and refactoring.

**Primary source:** [Karpathy LLM-Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

---

## 2. Why LLM-Wiki Resonated

LLM-Wiki addresses a real weakness in current AI workflows: most LLM interactions do not compound.

Traditional RAG retrieves chunks and generates answers repeatedly. A new question starts the process again. The system does not necessarily preserve the previous synthesis as an artifact. LLM-Wiki changes this by compiling knowledge into a persistent structure.

| Pattern | Strength | Weakness |
|---|---|---|
| File upload / chat with documents | Easy and grounded | Little durable synthesis |
| Vector RAG | Scales well for retrieval | Weak at evolving conceptual structure |
| Obsidian / Notion / PKM | Human-readable and durable | Maintenance burden is high |
| LLM-Wiki | Compounding, maintained, linkable synthesis | Requires governance and validation |

The practical insight is that personal wikis often fail because maintaining them is laborious. LLM-Wiki delegates much of that maintenance work to the agent: updating summaries, creating links, detecting overlaps, revising stale pages, and preserving citations.

---

## 3. Emerging Apps and Implementations

### 3.1 lucasastorian/llmwiki

This is a direct open-source implementation of Karpathy’s idea. It supports document uploads, Claude integration through MCP, local document indexing, markdown wiki generation, cross-references, and citations.

**Notable characteristics:**

- Open-source implementation of Karpathy’s LLM-Wiki.
- Handles PDFs, articles, notes, office documents, and similar sources.
- Uses an app-like workflow rather than only a conceptual prompt.
- Connects to Claude through MCP.
- Produces markdown wiki output.

**Source:** [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki)

---

### 3.2 Astro-Han/karpathy-llm-wiki

This repository packages the LLM-Wiki pattern as a reusable **Agent Skills-compatible** workflow for Claude Code, Cursor, Codex, and related tools.

**Notable characteristics:**

- Agent skill rather than standalone app.
- Converts raw sources into wiki pages.
- Supports URLs, PDFs, markdown, text, and pasted content.
- Emphasizes citations, linting, and index maintenance.
- Demonstrates the shift from “knowledge app” to “knowledge capability embedded in agents.”

**Source:** [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki)

---

### 3.3 MehmetGoekce/llm-wiki

This implementation is important because it introduces a practical **L1/L2 cache architecture**.

| Layer | Function |
|---|---|
| **L1** | Auto-loaded rules, gotchas, identity, credentials, always-needed context |
| **L2** | Deeper project knowledge, workflows, research, on-demand wiki pages |

The L1/L2 model is a major operational improvement because it acknowledges that not all knowledge should be loaded into the context window. Some knowledge must always be present; deeper knowledge should be retrieved when needed.

**Sources:**

- [MehmetGoekce/llm-wiki](https://github.com/MehmetGoekce/llm-wiki)
- [L1/L2 architecture document](https://github.com/MehmetGoekce/llm-wiki/blob/main/docs/l1-l2-architecture.md)

---

### 3.4 OmegaWiki

OmegaWiki extends the LLM-Wiki concept into a full research-lifecycle platform.

**Notable characteristics:**

- Paper ingestion.
- Knowledge graph construction.
- Gap detection.
- Idea generation.
- Experiment design.
- Paper writing.
- Reviewer-response workflows.

This is significant because it treats the wiki not merely as a personal notes repository, but as an **operating substrate for research work**.

**Source:** [skyllwt/OmegaWiki](https://github.com/skyllwt/OmegaWiki)

---

### 3.5 Memoriki

Memoriki combines LLM-Wiki with a temporal knowledge graph and persistent memory. Its design points toward a mature architecture where markdown pages are only one layer in a richer system.

**Notable characteristics:**

- Markdown wiki pages.
- Semantic search.
- Temporal graph structure.
- MCP-compatible agent access.
- Emphasis on how knowledge changes over time.

This points to a likely direction for serious LLM-Wiki systems: markdown + embeddings + graph + temporal metadata.

**Source:** [Show HN: Memoriki](https://news.ycombinator.com/item?id=47711037)

---

### 3.6 WUPHF / Agent-Maintained Wiki

A recent Hacker News discussion around a Karpathy-style LLM wiki inside WUPHF shows the idea moving from personal knowledge work toward **team-agent operational memory**.

**Notable characteristics:**

- Markdown and Git-based workflow.
- Self-hosted and bring-your-own-keys.
- Designed for AI agents such as Claude Code, Codex, OpenClaw, and local LLMs via OpenCode.
- Can be used as a wiki layer without adopting the full office/product environment.

This is an important shift: LLM-Wiki is becoming not just a user-facing note system, but a shared memory layer for agents and teams.

**Source:** [Show HN: A Karpathy-style LLM wiki your agents maintain](https://news.ycombinator.com/item?id=47899844)

---

## 4. Related Research Developments

### 4.1 ByteRover: Agent-Native Memory

ByteRover is one of the closest research analogues to LLM-Wiki. It argues that existing memory-augmented systems treat memory as an external service, which creates semantic drift between what the agent intended to remember and what the storage pipeline captured.

ByteRover’s alternative is **agent-native memory**: the same LLM that reasons about a task also curates, structures, and retrieves knowledge.

**Key concepts:**

- Hierarchical **Context Tree**.
- File-based knowledge graph.
- Explicit relations.
- Provenance.
- Adaptive Knowledge Lifecycle.
- Importance scoring.
- Maturity tiers.
- Recency decay.
- Progressive retrieval.

This strongly supports the LLM-Wiki direction: durable memory should be human-readable, agent-maintained, and structured.

**Source:** [ByteRover paper](https://arxiv.org/abs/2604.01599)

---

### 4.2 Mem0: Long-Term Agent Memory

Mem0 focuses on scalable long-term memory for agents. It extracts and consolidates salient memories across sessions and supports graph-based variants for relational memory.

Mem0 is less wiki-oriented than LLM-Wiki, but it addresses the same underlying problem: agents need persistent, reusable memory rather than stateless interaction.

**Source:** [Mem0 paper](https://arxiv.org/abs/2504.19413)

---

### 4.3 HippoRAG / HippoRAG 2

HippoRAG uses knowledge graphs and retrieval mechanisms inspired by hippocampal indexing theory. It is relevant because it separates human-readable memory from machine-optimized retrieval.

The implication for LLM-Wiki systems is that markdown alone may not be enough. A mature architecture should likely include:

- human-readable pages,
- a machine-readable knowledge graph,
- semantic retrieval,
- ranking algorithms,
- and provenance-aware reasoning.

**Source:** [HippoRAG GitHub repository](https://github.com/osu-nlp-group/hipporag)

---

### 4.4 M-ASK: Multi-Agent Search and Knowledge

M-ASK decomposes agentic search into two roles:

1. **Search Behavior Agents** — plan and execute search actions.
2. **Knowledge Management Agents** — aggregate, filter, and maintain compact internal context.

This separation is relevant for mabstruct.ai because a serious agentic knowledge system should not use one monolithic agent for everything. Ingestion, synthesis, critique, retrieval, ontology maintenance, and writing are different roles.

**Source:** [M-ASK paper](https://arxiv.org/abs/2601.04703)

---

### 4.5 AgenticScholar

AgenticScholar combines structured scholarly data management, LLM-centric hybrid query planning, and execution DAGs for scholarly corpora.

This connects to the more ambitious LLM-Wiki implementations because it treats knowledge management as pipeline orchestration, not just search or note-taking.

**Source:** [AgenticScholar paper](https://arxiv.org/abs/2603.13774)

---

## 5. Public Discussion: Enthusiasm and Critique

### Enthusiastic View

The enthusiastic view is that LLM-Wiki solves the “AI starts from zero every time” problem. Builders report that synthesis questions improve because the system can reuse compiled knowledge rather than repeatedly retrieving raw chunks.

Common positive themes:

- Knowledge compounds.
- Context-token usage can be reduced.
- Obsidian/Logseq provide a familiar interface.
- Agents can maintain operational memory.
- Markdown + Git makes the system inspectable.

**Example sources:**

- [Reddit: built and tested Karpathy’s LLM-Wiki](https://www.reddit.com/r/AI_Agents/comments/1sqg5ew/spent_a_weekend_actually_understanding_and/)
- [Reddit: Claude Code plugin](https://www.reddit.com/r/ClaudeCode/comments/1scidpz/built_a_claude_code_plugin_that_turns_your/)

---

### Skeptical View

The strongest critiques are not about markdown or implementation difficulty. They are about epistemology and governance.

Common concerns:

- An LLM-maintained wiki can accumulate hallucinated or weakly grounded content.
- “Wiki” may be misleading without human curation and editorial governance.
- Generated notes can create noise.
- Source provenance must be explicit.
- Sensitive documents require local-first or self-hosted deployment.
- Long-lived generated knowledge needs versioning, review, and contradiction tracking.

These critiques are valid and should be treated as design requirements.

---

### Emerging Consensus

The emerging consensus is:

> LLM-Wiki is valuable if treated as machine-assisted knowledge maintenance under human governance, not as an autonomous truth engine.

A serious implementation needs:

- citation-level provenance,
- source-to-claim traceability,
- diffs,
- review status,
- contradiction handling,
- linting,
- stale-content detection,
- access control,
- and human approval workflows.

---

## 6. Comparison with mabstruct.ai

Publicly accessible mabstruct material is limited, but mabstruct.cloud presents the project as a space for “AI, robotics, cosmology, and creative musings,” with reflective writing around AI, life, and the universe.

**Source:** [mabstruct.cloud](https://mabstruct.cloud/)

Based on your description of mabstruct.ai as an **agentic knowledge management system**, the overlap with LLM-Wiki is strong, but mabstruct.ai can be positioned more broadly.

### Core Comparison

| Dimension | Karpathy LLM-Wiki | mabstruct.ai |
|---|---|---|
| Primary object | Maintained markdown wiki | Agentic knowledge/research system |
| Initial scope | Personal knowledge bases | Broader intellectual and research synthesis |
| Content type | Articles, papers, notes, books, documents | Mathematics, cosmology, philosophy, arts, AI, personal research |
| Agent role | Wiki maintainer | Knowledge architect, research companion, synthesis engine |
| Main value | Compounding notes instead of repeated RAG | Long-term conceptual construction |
| Output | Interlinked markdown pages | Essays, maps, ontologies, research trails, conceptual structures |
| Risk | Stale or hallucinated generated pages | Same risk, plus abstraction risk |
| Differentiator | Maintenance automation | Epistemic discipline and cross-domain synthesis |

---

## 7. Where mabstruct.ai Overlaps with LLM-Wiki

Mabstruct appears to share several assumptions with LLM-Wiki:

1. Knowledge should compound over time.
2. The system should maintain structure, not only answer questions.
3. Notes, sources, conversations, and reflections should become durable artifacts.
4. AI should assist in organizing, connecting, and synthesizing ideas.
5. Human review and direction remain central.
6. The long-term artifact is more important than a single chat answer.

---

## 8. Where mabstruct.ai Can Go Beyond LLM-Wiki

LLM-Wiki is mainly a pattern for maintaining a source-grounded wiki. Mabstruct.ai can extend this into a richer **conceptual intelligence layer**.

### Mabstruct Opportunity Stack

| Layer | Mabstruct Opportunity |
|---|---|
| Source layer | Papers, books, notes, conversations, project logs |
| Wiki layer | Stable pages for concepts, people, works, projects, theories |
| Claim layer | Atomic claims with provenance, confidence, and review state |
| Graph layer | Typed relations: supports, contradicts, generalizes, depends-on |
| Research trail layer | How your understanding changes over time |
| Synthesis layer | Essays, conceptual maps, research questions |
| Agent layer | Ingest, critique, compare, synthesize, map, write |
| Governance layer | Review status, contradiction handling, uncertainty markers |
| Personal canon layer | Your evolving intellectual worldview |

This last layer is the real differentiator. LLM-Wiki produces a maintained knowledge base. Mabstruct can produce an evolving intellectual model.

---

## 9. Strategic Positioning for mabstruct.ai

Avoid positioning mabstruct.ai as merely:

> “A personal AI wiki.”

That category is already becoming crowded.

A stronger positioning would be:

> **Mabstruct.ai is an agentic research-memory system. It transforms notes, sources, conversations, and reading projects into a living conceptual architecture: cited, inspectable, interconnected, and continuously refined by specialized AI agents under human review.**

Alternative versions:

### Compact Positioning

> **Mabstruct is a living research architecture maintained by AI agents and governed by human judgment.**

### Visionary Positioning

> **Mabstruct is a personal knowledge civilization: a living map of what you read, think, question, and create. LLM-Wiki maintains the pages; mabstruct maintains the intellectual structure behind them.**

### Technical Positioning

> **Mabstruct combines LLM-Wiki-style compiled markdown, typed knowledge graphs, semantic retrieval, claim-level provenance, and agentic workflows for long-horizon research and synthesis.**

---

## 10. Recommended Architecture for mabstruct.ai

A strong mabstruct.ai architecture should combine the best parts of LLM-Wiki, ByteRover, Memoriki, HippoRAG, M-ASK, and AgenticScholar.

| Component | Purpose |
|---|---|
| Raw vault | Immutable source documents, notes, transcripts, PDFs, web clips |
| Compiled wiki | Human-readable markdown pages |
| Claim store | Atomic claims with provenance and confidence |
| Knowledge graph | Typed entities and relationships |
| Vector / semantic index | Fuzzy retrieval and discovery |
| Temporal layer | Tracks when claims were added, revised, contradicted |
| Agent skills | Ingest, synthesize, compare, critique, lint, query, write |
| Review workflow | Human approval, diffs, review states |
| Research outputs | Essays, maps, briefs, reading trails |
| Personal worldview model | Evolving conceptual structure |

---

## 11. Suggested Agent Roles

| Agent | Function |
|---|---|
| Ingest agent | Converts sources into clean raw markdown and metadata |
| Claim extraction agent | Extracts atomic claims with citations |
| Ontology agent | Maps entities and concepts into the graph |
| Synthesis agent | Updates topic pages and cross-domain essays |
| Critic agent | Finds contradictions, weak claims, missing citations |
| Research agent | Suggests next readings and open questions |
| Writing agent | Produces essays and public-facing reflections |
| Governance agent | Flags unreviewed, speculative, stale, or sensitive content |

This multi-agent structure reflects the M-ASK principle: search, knowledge management, synthesis, and governance should be separated into specialized roles.

---

## 12. Key Risks for mabstruct.ai

### 12.1 Beautiful Synthesis Without Grounding

For domains like mathematics, cosmology, philosophy, and AI, LLMs can produce elegant but false connections. Mabstruct should clearly distinguish:

- established fact,
- extracted claim,
- interpretation,
- analogy,
- speculation,
- personal hypothesis.

### 12.2 Over-Generation

A knowledge system can become polluted by plausible but low-value generated content. The system should avoid producing pages merely because it can.

Mitigation:

- require a purpose for each page,
- track source lineage,
- mark review status,
- periodically prune stale or weak pages.

### 12.3 Markdown-Only Ceiling

Markdown is excellent for human-readable knowledge, but insufficient by itself for deep querying, permissions, structured reasoning, and consistency management.

Mitigation:

- keep markdown as the interface,
- add graph and database layers underneath,
- treat markdown as one projection of a richer knowledge model.

### 12.4 Identity Confusion

If mabstruct is simultaneously blog, wiki, agent, archive, research system, and personal site, users may not understand the product.

Mitigation:

- separate public publication from private knowledge infrastructure,
- clarify the product promise,
- show concrete workflows.

---

## 13. Practical Roadmap

### Phase 1: LLM-Wiki-Compatible Foundation

- `raw/` immutable source layer.
- `wiki/` compiled markdown layer.
- `logs/` ingest and update logs.
- `schema/` agent instructions.
- backlinks and citations.
- Obsidian/Logseq compatibility.

### Phase 2: Claim and Provenance Layer

- atomic claim extraction.
- source-span references.
- confidence and review status.
- contradiction detection.
- claim-to-page mapping.

### Phase 3: Knowledge Graph

Add typed relations such as:

- `Book introduces Concept`
- `Concept generalizes Concept`
- `Theory conflicts_with Theory`
- `Author argues Claim`
- `Claim supported_by Source`
- `Question motivated_by Gap`
- `Essay synthesizes Concepts`

### Phase 4: Agent Workflows

- ingest,
- synthesize,
- critique,
- compare,
- map,
- write,
- research planning.

### Phase 5: Public mabstruct Identity

Turn selected internal structures into public artifacts:

- essays,
- conceptual maps,
- reading trails,
- “how my understanding evolved” pages,
- public/private knowledge split.

---

## 14. Final Assessment

Karpathy’s LLM-Wiki is important because it names a pattern that was already latent in many advanced AI workflows:

> LLMs should maintain durable knowledge artifacts, not merely answer transient questions.

The ecosystem is already forming around this idea: open-source LLM-Wiki apps, Claude Code skills, MCP servers, Obsidian/Logseq workflows, YouTube compilers, temporal knowledge graphs, and team-agent memory systems.

For mabstruct.ai, the opportunity is clear:

> **Do not compete as another AI notes app. Compete as an agentic research-memory and conceptual-synthesis system.**

Your strongest moat is not ingestion. It is not markdown. It is the combination of:

- long-horizon personal research,
- cross-domain synthesis,
- cited conceptual structure,
- agentic maintenance,
- human-governed epistemic discipline,
- and an evolving intellectual identity.

That is meaningfully broader than LLM-Wiki, while still benefiting from its architectural breakthrough.

---

## Source List

1. Andrej Karpathy, **LLM Wiki** — <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>  
2. lucasastorian, **llmwiki** — <https://github.com/lucasastorian/llmwiki>  
3. Astro-Han, **karpathy-llm-wiki** — <https://github.com/Astro-Han/karpathy-llm-wiki>  
4. MehmetGoekce, **llm-wiki** — <https://github.com/MehmetGoekce/llm-wiki>  
5. MehmetGoekce, **L1/L2 architecture** — <https://github.com/MehmetGoekce/llm-wiki/blob/main/docs/l1-l2-architecture.md>  
6. skyllwt, **OmegaWiki** — <https://github.com/skyllwt/OmegaWiki>  
7. Hacker News, **Show HN: Memoriki** — <https://news.ycombinator.com/item?id=47711037>  
8. Hacker News, **Show HN: A Karpathy-style LLM wiki your agents maintain** — <https://news.ycombinator.com/item?id=47899844>  
9. Nguyen et al., **ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context** — <https://arxiv.org/abs/2604.01599>  
10. Mem0, **Long-Term Memory for Agents** — <https://arxiv.org/abs/2504.19413>  
11. OSU NLP Group, **HippoRAG** — <https://github.com/osu-nlp-group/hipporag>  
12. Chen et al., **M-ASK: Multi-Agent Search and Knowledge** — <https://arxiv.org/abs/2601.04703>  
13. Lan et al., **AgenticScholar** — <https://arxiv.org/abs/2603.13774>  
14. Reddit, **Built and tested Karpathy’s LLM-Wiki** — <https://www.reddit.com/r/AI_Agents/comments/1sqg5ew/spent_a_weekend_actually_understanding_and/>  
15. Reddit, **Claude Code plugin discussion** — <https://www.reddit.com/r/ClaudeCode/comments/1scidpz/built_a_claude_code_plugin_that_turns_your/>  
16. mabstruct.cloud — <https://mabstruct.cloud/>  
