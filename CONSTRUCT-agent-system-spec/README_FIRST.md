# CONSTRUCT Agent System — Specification Directory

**Project:** CONSTRUCT — an AI-native knowledge system, implemented as Claude agent configuration
**Approach:** Claude-native (configuration-only, no custom runtime)
**Status:** Specification complete
**Date:** 2026-04-23

---

## What is this directory?

This is the **product specification workspace** for the Claude-native implementation of CONSTRUCT. It is a parallel approach to the Python-based implementation in `CONSTRUCT-spec/`.

**Key difference:** Instead of building a Python backend (FastAPI, SQLite, NetworkX, React), this approach configures Claude to BE the CONSTRUCT system. Claude's native capabilities — dialog, web search, file management, reasoning, session memory — replace the custom runtime entirely.

The solution artifacts (agent definitions, skills, workflows, templates) live in `CONSTRUCT-agents/`.

---

## Relationship to CONSTRUCT-spec/

| Aspect | CONSTRUCT-spec/ (Python) | This directory (Claude-native) |
|--------|--------------------------|-------------------------------|
| **Runtime** | Custom Python backend | Claude IS the runtime |
| **Storage** | SQLite + FTS5 + NetworkX | Markdown files + JSON (Claude reads/writes directly) |
| **UI** | React + D3 + WebSocket | Claude conversation interface |
| **Research** | httpx API clients | Claude's web search |
| **Curation** | Python agent classes | Claude skill invocations |
| **Graph** | NetworkX derived graph | `connections.json` + Claude reasoning |
| **Deployment** | `pip install` + `construct serve` | Copy config to `~/.claude/` |

**What's shared:** The knowledge model, epistemic governance, workspace format, card schema, and conceptual architecture are identical. Only the runtime is different.

---

## How to read this directory

### Core narrative

| # | Document | What it is | Read when |
|---|----------|-----------|-----------|
| 1 | [product-brief.md](product-brief.md) | Product vision adapted for Claude-native delivery | First |
| 2 | [prd.md](prd.md) | Technical requirements for the agent configuration approach | After the brief |
| 3 | [user-journeys.md](user-journeys.md) | Three reference journeys: cold start, daily use, co-authorship | To understand "done" |

### Engineering contracts

| Document | What it defines |
|----------|----------------|
| [data-schemas.md](data-schemas.md) | Workspace file schemas (shared with Python approach) |
| [knowledge-card-schema.md](knowledge-card-schema.md) | Canonical card format (shared) |
| [nfrs.md](nfrs.md) | Non-functional requirements adapted for agent-native delivery |
| [validation-strategy.md](validation-strategy.md) | How to verify correctness without CI/CD |

### Agent specifications

| Document | What it defines |
|----------|----------------|
| [agent-spec-construct.md](agent-spec-construct.md) | CONSTRUCT orchestrator: identity, routing, governance |
| [agent-spec-researcher.md](agent-spec-researcher.md) | Researcher: web search cycles, extraction, ingestion |
| [agent-spec-curator.md](agent-spec-curator.md) | Curator: graph maintenance, promotion, decay, bridges |

### Strategy & process

| Document | What it defines |
|----------|----------------|
| [development-strategy.md](development-strategy.md) | Phased configuration plan, exit criteria |
| [process.md](process.md) | How we build and evolve the agent configuration |
| [config-topology.md](config-topology.md) | Directory layout of `CONSTRUCT-agents/` |

### Decisions

| Document | What it records |
|----------|----------------|
| [adrs/adr-0001-claude-native-approach.md](adrs/adr-0001-claude-native-approach.md) | Decision to implement CONSTRUCT as Claude configuration |

---

## Key decisions

| Decision | Where recorded |
|----------|---------------|
| Claude-native, no custom runtime | ADR-0001 |
| Same workspace format as Python approach | PRD §2 |
| Skills replace code modules | PRD §3 |
| Validation via workspace auditing, not CI | Validation strategy |
| Same epistemic governance model | Product brief §3.4 |

---

## What is NOT decided

| Question | Default proposed |
|----------|-----------------|
| Whether both approaches can coexist | Yes — shared workspace format enables this |
| Claude model version requirements | Claude Sonnet 4 minimum for frontier tasks |
| Claude API vs. Claude Desktop vs. Claude Code | Any Claude surface that supports tools + files |
