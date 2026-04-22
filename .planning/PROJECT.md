# CONSTRUCT

## What This Is

CONSTRUCT is an open-source, agent-powered personal knowledge system for a single user or small team. It helps people systematically collect, curate, connect, and compound knowledge across domains, then derive high-quality outputs from that accumulated graph state. The product is centered on a governed knowledge graph, with CONSTRUCT acting as the thinking partner and orchestrator over specialist agents.

## Core Value

The knowledge graph must become an active, persistent, agent-maintained system that compounds over time instead of a passive note store.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Users can initialize a local CONSTRUCT workspace with the canonical source-of-truth structure, configs, and templates.
- [ ] Users can build, validate, index, and query markdown knowledge cards as the canonical graph-backed memory layer.
- [ ] Users can run CONSTRUCT as a local-first orchestrator that manages research and curation agents with tiered LLM routing.
- [ ] Users can explore the knowledge graph, cards, agent status, and activity through a browser UI backed by heartbeat-generated `views/` artifacts.
- [ ] Users can interact with CONSTRUCT through chat and commands to steer research, inspect graph state, and manage domains.
- [ ] The system can run continuous research and curation loops that ingest findings, maintain graph health, and preserve epistemic metadata.

### Out of Scope

- Multi-user collaboration and roles — v0.1 is explicitly local-first and single-user.
- Cloud deployment, remote access, and sync — deferred until later milestones to preserve local-first simplicity.
- ChromaDB, embedding-based similarity, and semantic duplicate detection — deferred to v0.2.
- Synthesizer and Narrator publication workflows — drafting and publication are deferred beyond v0.1.
- Telegram, Slack, mobile, PWA, and plugin integrations — intentionally excluded from the initial release.
- Import/export bridges for Obsidian, Notion, or Roam — not part of the initial product cut.

## Context

CONSTRUCT is being built greenfield in its own repository, separate from the live MABSTRUCT workspace. The specification set is already substantial and includes a product brief, PRD, user journeys, NFRs, repo topology, schemas, agent specs, and an implementation strategy. The product vision is an AI-native knowledge system where the knowledge graph is the product, CONSTRUCT is both the product and the primary agent identity, and specialist agents handle research and curation under human direction.

The v0.1 release is focused on research and collection: Python runtime, Curator and Researcher agents, markdown-plus-YAML knowledge cards, NetworkX graph derivation, SQLite plus FTS5 indexing, heartbeat-rendered `views/`, React UI, CLI, and git-backed local state. The development strategy already identifies a practical implementation ordering: skeleton, data foundation, agent runtime, graph engine, views heartbeat, React UI, integration, and open-source launch.

The workspace model is central to the product. Markdown files and YAML configs are the source of truth, rebuildable indexes stay out of git, disposable UI views are heartbeat-generated, and curated publishable outputs remain tracked artifacts. The product also carries forward explicit epistemic governance: confidence, source tier, register, typed connections, lifecycle state, and decay tracking.

## Constraints

- **Tech stack**: Python is the sole backend language, with React as a built static artifact served by Python — chosen to avoid split backend complexity.
- **Architecture**: Local-first, single-user, no auth, no multi-tenancy — keeps v0.1 focused on core product value.
- **Storage**: Markdown plus YAML frontmatter is the canonical source of truth — human-readable, git-diffable, and rebuild-friendly.
- **Graph engine**: NetworkX is the derived graph layer — required for traversal, bridge detection, and graph health features.
- **Search and indexing**: SQLite with FTS5 is the initial structured query layer — semantic search via embeddings is deferred.
- **Privacy**: No telemetry ever, and user knowledge stays local except for explicitly configured LLM API calls.
- **Portability**: Python 3.11+ and Node 20+ are the baseline targets, with macOS and Linux in scope for v0.1.
- **Performance**: v0.1 is designed for up to roughly 5,000 cards, with graph rendering targets capped far below that for interactive views.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python-first architecture with no OpenClaw dependency | Single-language development is simpler, faster to onboard, and better aligned with the planned runtime and agent development flow | — Pending |
| Knowledge graph is the central artifact | The product differentiator is persistent, governed, cross-domain knowledge that compounds over time | — Pending |
| Local-first workspace with git-backed source of truth | Data sovereignty, inspectability, and rebuildability are core product values | — Pending |
| React UI consumes heartbeat-generated `views/` instead of raw workspace files | This decouples runtime storage from UI concerns and creates a clean future API boundary | — Pending |
| v0.1 focuses on research, curation, graph, and UI, not publication or cloud features | Keeps the first release narrow enough to ship while proving the core knowledge-system thesis | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-22 after initialization*
