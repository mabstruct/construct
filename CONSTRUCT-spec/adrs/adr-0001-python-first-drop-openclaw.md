---
id: ADR-0001
title: Python-first architecture, drop OpenClaw dependency
status: accepted
date: 2026-04-19
decision-makers: mab (human)
---

# ADR-0001: Python-first architecture, drop OpenClaw dependency

## Context

The product brief (v1.1.0) assumed CONSTRUCT would be built on a stripped-down OpenClaw runtime (Option C in §5, "Local-First, Cloud-Ready"). The capability matching matrix identified 22 carry-over, 20 adapt, 19 build, 15 strip capabilities from OpenClaw.

However, upon review during gap-closing, OpenClaw served only as a runtime loop in the MABSTRUCT workspace — not as essential infrastructure. The TS/JS runtime added a second language without proportional value. The "stripdown" task (estimated Week 1–2) risked being open-ended.

## Decision

**Drop OpenClaw entirely. Build CONSTRUCT as a Python-first application.**

- Python is the sole backend language (agents, graph, storage, research, publish, CLI, server)
- React UI is a build artifact (`vite build` → static files), served by the Python server
- Agent orchestration, session management, heartbeat, and chat interface are built natively in Python
- No TypeScript runtime dependency

## Repo structure (Option D from gap-closing discussion)

```
construct/
├── pyproject.toml
├── src/construct/           # Python — the entire product
│   ├── agents/              # Agent runtime, SOUL/IDENTITY, delegation
│   ├── graph/               # NetworkX build, query, bridge detection
│   ├── storage/             # SQLite indexer, FTS5, rebuild
│   ├── research/            # API clients, ingestion, search patterns
│   ├── views/               # Heartbeat → views/ renderer (internal UI data)
│   ├── workflows/           # BMAD-inspired skill execution engine
│   ├── server.py            # Serves UI + WebSocket for chat + events
│   └── cli.py               # construct init / status / etc.
├── ui/                      # React — built by Vite, served by Python
├── templates/               # Agent templates, default configs, workflow defs
├── scripts/                 # Init, dev tooling
├── specs/                   # Product specs
├── dev/                     # Dev process, ADRs, journal
├── tests/
└── .github/workflows/ci.yml
```

## Consequences

### Positive
- Single primary language — simpler for Claude Code, contributors, and debugging
- No OpenClaw stripdown task (saves Week 1–2 of original plan)
- `pip install construct` + `construct init` = clean OSS onboarding
- Full control over agent runtime — no upstream dependency risk
- Language boundary is clean: Python = product, JS = UI build tool only

### Negative
- Must build agent runtime from scratch (session management, heartbeat, chat WebSocket, LLM provider abstraction)
- Lose OpenClaw's existing chat infrastructure and plugin system
- Lose OpenClaw's Telegram bot integration (must rebuild for v0.2)

### Cascading changes to product brief
- §5 Option C rationale: no longer applies. Architecture is now "Python-native, local-first"
- §6 "Core Runtime — OpenClaw (Stripped)": replaced with native Python runtime
- §6 "Interaction Layer": chat via Python WebSocket server + React, not OpenClaw WebChat
- §6 "Command System": Python CLI + WebSocket commands, not OpenClaw plugins/skills
- §10 Step 5 "Strip OpenClaw": replaced with "Build CONSTRUCT core runtime"
- §10 Step 6 "BMAD workflows": unchanged — SKILL.md definitions are framework-agnostic
- Capability matching matrix: all "✅ CARRY from OpenClaw" items become "🆕 BUILD (native Python)" — but many are simpler to build than to strip
- OpenCode, HIVE evaluations in §6: still valid as future options but no longer needed for v0.1

### What carries over from MABSTRUCT (unchanged)
- SOUL/IDENTITY/EVOLUTION governance model (markdown documents, not code)
- Knowledge card format and graph structure
- Research infrastructure patterns (search seeds, taxonomy, digests, historization)
- BMAD-inspired workflow patterns (SKILL.md format)
- `views/` interface contract (internal UI data layer)
- `publish/` directory for curated external outputs
- Four-category storage model
