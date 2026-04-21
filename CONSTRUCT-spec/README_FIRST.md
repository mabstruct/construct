# CONSTRUCT Product Development — Read This First

**Project:** CONSTRUCT — an AI-native knowledge system where agents curate what you learn
**Status:** Pre-implementation planning (gap-closing phase)
**Date:** 2026-04-20

---

## What is this directory?

This is the **product development workspace** for CONSTRUCT — separated from the live MABSTRUCT system to avoid mixing two development streams:

1. **This directory** — designing and building the new CONSTRUCT product (greenfield)
2. **The parent workspace** — the running MABSTRUCT research assistant (continuous operation)

Everything needed to understand, plan, and eventually implement CONSTRUCT lives here.

---

## How to read this directory

### Start here — the core narrative

| # | Document | What it is | Read when |
|---|----------|-----------|-----------|
| 1 | [construct-product-brief.md](construct-product-brief.md) | **Product vision.** What CONSTRUCT is, why it exists, core concepts, user interactions. | First. This is the product. |
| 2 | [construct-prd.md](construct-prd.md) | **Technical requirements.** Architecture, tech stack, storage model, interaction protocols, agent specs, MVP scope. | After the brief. This is how we build it. |
| 3 | [product-brief-gap-analysis.md](product-brief-gap-analysis.md) | Review of the brief's readiness for implementation. Lists gaps, risks, and what was missing. | After the PRD. Shows what we closed. |
| 4 | [construct-user-journeys.md](construct-user-journeys.md) | Three reference journeys: cold start, daily use, co-authorship. These are the acceptance scenarios. | To understand what "done" looks like. |

### Supporting specs — the engineering contracts

| Document | What it defines | Depends on |
|----------|----------------|------------|
| [construct-data-schemas.md](construct-data-schemas.md) | JSON/YAML schemas for all 15 structured artifacts (views/, publish/, inbox/, config/, log/) | PRD §3 |
| [construct-sqlite-schema.md](construct-sqlite-schema.md) | SQLite + FTS5 table definitions, query patterns per agent, indexer behavior, migration strategy | PRD §3 |
| [knowledge-card-schema.md](knowledge-card-schema.md) | Canonical knowledge card format (YAML frontmatter + markdown body). Supersedes prior specs. | Product brief §3.1 |
| [zettelkasten-kg-spec.md](zettelkasten-kg-spec.md) | NetworkX graph engine spec (build.py, query.py, graph.json) | PRD §2 |
| [construct-capability-matching.md](construct-capability-matching.md) | Maps CONSTRUCT requirements vs. OpenClaw capabilities. **Historical** — OpenClaw dropped per ADR-0001. | PRD §1 |
| [construct-nfrs.md](construct-nfrs.md) | Non-functional requirements: performance targets, security, privacy, portability, observability | PRD |
| [construct-test-strategy.md](construct-test-strategy.md) | Test layers, CI pipeline, fixtures, LLM mocking, coverage targets | All specs |

### Agent specifications — what each agent does

| Document | What it defines | v0.1 scope? |
|----------|----------------|------------|
| [agent-spec-construct.md](agent-spec-construct.md) | CONSTRUCT orchestrator: task routing, delegation protocol, session lifecycle, context building, escalation handling | Yes |
| [agent-spec-researcher.md](agent-spec-researcher.md) | Researcher: 7-step research cycle, API clients (S2/arXiv), extraction pipeline, dedup, relevance scoring, configuration | Yes |
| [agent-spec-curator.md](agent-spec-curator.md) | Curator: 7-step curation cycle, promotion rules, decay/orphan scanning, connection typing, inbox processing, bridge detection | Yes |

### Strategy & structure — what we build when

| Document | What it defines |
|----------|----------------|
| [construct-repo-topology.md](construct-repo-topology.md) | Full directory tree of the `construct` repo, module ownership, workspace storage model, build & package config |
| [construct-development-strategy.md](construct-development-strategy.md) | Phased implementation plan (Phase 0–7), dependency ordering, risk register, v0.1 success criteria |

### Process — how we build

| Document | What it governs |
|----------|----------------|
| [PROCESS.md](PROCESS.md) | Claude Code development process: session protocol, branching, PR flow, working agreements, code standards |
| [CURRENT.md](CURRENT.md) | Living document: what was last done, what is in progress, what is next. Updated every session. |
| [adrs/](adrs/) | Architecture Decision Records — numbered, immutable once accepted |
| [adrs/adr-0001-python-first-drop-openclaw.md](adrs/adr-0001-python-first-drop-openclaw.md) | **Key decision:** Python-first architecture, OpenClaw dropped entirely |

---

## Key decisions made so far

| Decision | Where recorded |
|----------|---------------|
| Architecture: Python-first, no OpenClaw dependency | ADR-0001 |
| Repo structure: Option D (Python primary, React as build artifact) | ADR-0001 + repo topology |
| Implementation phasing: 8 phases, vertical slices | Development strategy |
| BMAD: adopt patterns, not framework or bridge | PRD §7 + capability matching §6.1 |
| All data stays local, no telemetry ever | NFRs §4 |
| YAML frontmatter for cards (not inline bold metadata) | Knowledge card schema §2 |

## What is NOT yet decided

| Question | Default proposed | Where discussed |
|----------|-----------------|----------------|
| License | Apache-2.0 | Gap analysis §3.7.1 |
| Repo topology formal writeup | ✅ Done | [construct-repo-topology.md](construct-repo-topology.md) |
| Extraction method (greenfield vs. fork) | Greenfield + selective copy-in | Gap analysis Appendix Q3 |

---

## Relationship to the live system

This directory references two specs that also live in the parent workspace's `/specs/`:

- `knowledge-card-schema.md` — copied here as canonical product spec. The `/specs/` copy is the operational version for the running MABSTRUCT system.
- `zettelkasten-kg-spec.md` — copied here. Same pattern.

When CONSTRUCT gets its own repo, this entire directory becomes the starting point. The parent workspace continues as the running MABSTRUCT instance.

---

## Reading order for a new contributor

1. `construct-product-brief.md` — understand the product vision
2. `construct-prd.md` — understand how we build it (architecture, tech stack, scope)
3. `construct-user-journeys.md` — understand what users do
4. `adrs/adr-0001-python-first-drop-openclaw.md` — understand the architecture decision
5. `construct-repo-topology.md` — understand the repo and workspace layout
6. `construct-development-strategy.md` — understand what we build in what order
7. `construct-data-schemas.md` — understand the data contracts
8. `PROCESS.md` — understand how we work
9. `CURRENT.md` — understand where we are right now
