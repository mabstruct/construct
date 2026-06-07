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

## Alternatives considered

**A. Continue OpenClaw stripdown (the original plan in product brief v1.1.0).** Rejected. The stripdown was defined at the documentation level, not the codebase level, and had no clear exit criterion — flagged as R1 (High likelihood / High impact) in the gap analysis. Trading an unbounded TypeScript-adaptation task for a bounded Python rebuild is the whole point of this ADR.

**B. Adopt a Python-native agent framework (LangGraph, CrewAI, Claude Agent SDK).** Rejected for v0.1. Each reintroduces a dependency of the same class we are trying to escape from OpenClaw, with opinionated orchestration models that do not cleanly fit CONSTRUCT's four-category storage + inbox + heartbeat architecture. v0.1 runtime needs (one main agent + four sub-agents, heartbeat loop, subprocess handoffs, file-based state) are modest enough that hand-rolled Python is clearer, more reviewable for Claude Code as dev agent, and keeps the `views/` + `inbox/` contracts framework-agnostic. Revisit for v0.2 if orchestration complexity grows (branching workflows, stateful multi-turn tool-use, durable task queues).

**C. Greenfield Python-first (chosen).** Single runtime, known-bounded rebuild, clean OSS onboarding (`pip install construct`), aligned with Claude Code as primary development agent (gap analysis §3.6.1), and a clean invariant: *Python = product, JS = UI build tool only.*

## Replacements for dropped OpenClaw capabilities

Closes gap analysis §3.3.4 (LLM routing decision owed) and names the specific substitute for each dropped runtime capability:

| Dropped (OpenClaw) | Replacement | Notes |
|--------------------|-------------|-------|
| OC-LLM-01 multi-provider abstraction | **LiteLLM** | Covers Anthropic / OpenAI / Google / Mistral / Ollama in one interface. Supersedes the §6 "deferred option" framing — promote to default. Integration measured in hours. |
| CON-LLM-04 task → model routing | Thin YAML config layer over LiteLLM (`config/model-routing.yaml`) | Custom logic ~100–200 lines; LiteLLM handles provider plumbing. |
| OC-RT-01 session management | Hand-rolled Python session class | v0.1 needs are modest (one active agent + fresh sub-agent per delegation). Framework overkill. |
| OC-RT-02 sub-agent spawning | Python subprocess (or in-process with fresh context) | Mirrors OpenClaw's `sessions_spawn` semantics with a plain OS primitive. |
| OC-RT-03 heartbeat scheduler | `apscheduler` or a minimal asyncio loop | Standard Python tooling; no custom runtime. |
| OC-COM-01 terminal chat | Python REPL (`prompt_toolkit` / `rich`) | Standard. |
| OC-COM-02 WebChat (browser) | FastAPI + WebSocket | Same server that serves the built React UI. |
| OC-SKL-01 skill system | Markdown `SKILL.md` files loaded by a Python workflow engine (BMAD-pattern, already decided in capability matching §6.1.5) | Pattern-level adoption — no framework dependency. |
| OC-FS-02 git auto-commit | Python subprocess wrapper around `git` on heartbeat | Straightforward. |
| — | `log/events.jsonl` append-only event logger | New capability; replaces the implicit OpenClaw logging surface. |

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

### Reversal cost / path dependence

This is a **one-way decision at low cost now, high cost later** — recorded here so future revisits are honest about the asymmetry.

- **Reversing now (pre-implementation):** cheap. Nothing in the active MABSTRUCT workspace depends on this ADR except the unbuilt stripdown task.
- **Reversing at v0.2+ (re-adopt OpenClaw or another runtime):** expensive. Requires rewriting the Python server layer (session, heartbeat, chat WebSocket, sub-agent invocation) around the new runtime.

**Mitigation — keep the load-bearing contracts framework-agnostic** so a future runtime swap (OpenClaw, LangGraph, CrewAI, HIVE, or a successor) touches only the runtime layer, not the product:

- `SKILL.md` workflow format (BMAD-inspired, pattern-level — already decided)
- `views/` JSON schemas (UI-facing, runtime-independent)
- `inbox/` write-back schema (UI → agent, runtime-independent)
- Knowledge card schema + `connections.json` (source of truth, runtime-independent)
- `config/model-routing.yaml` (routes abstract over whichever LLM layer is used)
- `log/events.jsonl` event schema (observability, runtime-independent)

If these contracts stay stable, a runtime swap remains possible even if costly. If they drift into Python-specific assumptions, this decision becomes one-way in practice as well as on paper. Treat schema stability as an architectural principle, not a nice-to-have.

### Cascading changes to product brief
- §5 Option C rationale: no longer applies. Architecture is now "Python-native, local-first"
- §6 "Core Runtime — OpenClaw (Stripped)": replaced with native Python runtime
- §6 "Interaction Layer": chat via Python WebSocket server + React, not OpenClaw WebChat
- §6 "Command System": Python CLI + WebSocket commands, not OpenClaw plugins/skills
- §10 Step 5 "Strip OpenClaw": replaced with "Build CONSTRUCT core runtime"
- §10 Step 6 "BMAD workflows": unchanged — SKILL.md definitions are framework-agnostic
- Capability matching matrix: the original 22 CARRY items do **not** all become BUILD. Most are markdown/governance/documentation artifacts unaffected by the runtime choice and still carry over unchanged (see "What carries over from MABSTRUCT" below). The actual v0.1 *runtime* work introduced by this ADR is bounded and listed immediately below.
- OpenCode, HIVE evaluations in §6: still valid as future options but no longer needed for v0.1

### v0.1 runtime BUILD list (re-scoped)

Rough effort estimates (focused-day ranges) so the total rebuild cost is legible:

| Item | Estimate | Notes |
|------|----------|-------|
| Session / bootstrap framework | 1–2 days | Agent session lifecycle, context loading, shutdown. |
| Sub-agent invocation | ~1 day | Fresh subprocess or in-process context, file-based handoff. |
| Heartbeat scheduler | ~0.5 day | `apscheduler` or asyncio loop + task registry. |
| LLM routing middleware | 0.5–1 day | LiteLLM integration + `model-routing.yaml` parser. |
| Terminal chat REPL | ~0.5 day | `prompt_toolkit` / `rich`. |
| WebChat server | 1–2 days | FastAPI + WebSocket + session binding. |
| Git auto-commit wrapper | ~0.5 day | Subprocess around `git add/commit/push` on heartbeat. |
| Event logger (`log/events.jsonl`) | ~0.5 day | Append-only writer used by all agents. |
| **Total v0.1 runtime rebuild** | **~6–10 focused days** | Comparable to — and better-bounded than — the original OpenClaw stripdown estimate. |

**Unchanged by this ADR** (already accounted for in the capability-matching matrix as BUILD/ADAPT regardless of runtime): SQLite + FTS5 indexer, DB rebuild command, orphan detection, path/bridge queries, React UI components (graph, card detail, domain config, agent status, activity timeline), inbox write-back, response loop, file watching, views/ heartbeat step.

**Still deferred post-v0.1** (unchanged from capability matching v0.1.1): crash recovery, cost tracking, graceful degradation, Telegram bridge, ChromaDB embeddings, export pipeline.

### What carries over from MABSTRUCT (unchanged)
- SOUL/IDENTITY/EVOLUTION governance model (markdown documents, not code)
- Knowledge card format and graph structure
- Research infrastructure patterns (search seeds, taxonomy, digests, historization)
- BMAD-inspired workflow patterns (SKILL.md format)
- `views/` interface contract (internal UI data layer)
- `publish/` directory for curated external outputs
- Four-category storage model
