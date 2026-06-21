# CONSTRUCT v0.3 — Tranche 1 MVP

**Status:** Approved — ready for PRD and implementation  
**Date:** 2026-06-07  
**Architecture:** [ADR-0003](../CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md)

---

## Goal

Prove the layered runtime: **Python PIPE → capability registry → CLI + MCP (stdio) → LangGraph L2 gate → Streamlit ops UI** — all against `test-ws/` fixtures, workspace SOT unchanged.

Tranche 1 is **not** v0.5 product UI. It is the minimum backend + agentic invoke + spikes to de-risk v0.5.

---

## Deliverables (1–6)

| # | Deliverable | Description | Done when |
|---|-------------|-------------|-----------|
| **1** | **Capability registry** | Single Python module: capability id, input/output JSON schemas, handler reference, CLI command name, MCP tool name | Registry lists tranche 1 capabilities; schemas validated in tests |
| **2** | **CLI — three PIPE commands** | `construct run validate`, `construct run graph-status`, `construct run views-generate-data` (+ workspace path flags) | Contract tests pass on `test-ws/my-construct/` and `test-ws/ping-eon/` |
| **3** | **MCP — stdio, same three tools** | `construct mcp` (stdio transport); tools mirror CLI 1:1 | Cursor/Claude Desktop can invoke tools; schema matches CLI |
| **4** | **LangGraph spike — L2 “talk to my data”** | Grounded Q&A over a domain workspace; provider config (YAML/env); structured output with card citations | Swap provider in config without code change; answers cite source cards |
| **5** | **Streamlit spike — richer ops UI** | Localhost browser: capability runner, JSON results, **gate review panel** (approve/reject for L2/L3 outputs before optional SOT write) | Can run CLI/MCP capabilities and L2 ask from browser on localhost |
| **6** | **Workflow runner skeleton** | Daily Cycle as step sequence + progress → `log/events.jsonl`; at least orchestrate validate → graph-status → views-generate-data | Single `construct run workflow daily-cycle` emits step events |

---

## Spike decisions (locked)

| Choice | Decision |
|--------|----------|
| **A — LangGraph** | **L2 “talk to my data”** first (not L3 promotion review) |
| **B — Streamlit** | **Richer UI** — capability runner + gate review panel (previews v0.5 modal pattern) |
| **C — MCP transport** | **stdio** first (`construct mcp`); SSE deferred to tranche 2 / cloud |

---

## Capability registry (tranche 1)

| Capability ID | CLI | MCP tool | Layer | LLM |
|---------------|-----|----------|-------|-----|
| `workspace.validate` | `construct run validate` | `construct_validate` | PIPE | — |
| `graph.status` | `construct run graph-status` | `construct_graph_status` | PIPE | — |
| `views.generate_data` | `construct run views-generate-data` | `construct_views_generate_data` | PIPE | — |
| `workflow.daily_cycle` | `construct run workflow daily-cycle` | `construct_run_daily_cycle` | PIPE | — |
| `ask.domain` | `construct run ask` | `construct_ask_domain` | L2 gate | LangGraph |

---

## Repository targets

| Component | Path |
|-----------|------|
| Capability registry | `src/construct/capabilities/` |
| PIPE handlers | `src/construct/pipelines/` |
| LangGraph L2 gate | `src/construct/llm/ask_domain.py` (+ graph definition) |
| Provider config | `src/construct/llm/config.yaml` (or workspace `.construct/config.yaml` extension) |
| CLI | `src/construct/cli.py` |
| MCP server (stdio) | `src/construct/mcp/server.py` |
| Streamlit spike | `src/construct/ui/streamlit_app.py` or `spikes/v03-streamlit/` |
| Tests | `tests/contract/` + `test-ws/` fixtures |
| Workflow events | append to domain `log/events.jsonl` |

---

## Explicitly out of scope (tranche 2+)

- HTTP API for browser UI (v0.5)
- MCP SSE / remote transport
- `research-cycle`, `curation-cycle` full pipelines
- CoPilotKit / v0.2 views write actions
- SQLite indexer
- Cloud deploy

---

## Success criteria (tranche 1 complete)

1. All four PIPE capabilities + daily-cycle skeleton pass **CLI contract tests**.
2. MCP stdio exposes the **same five tools** with matching schemas.
3. **LangGraph L2** answers a domain question with citations; **provider swap** works via config only.
4. **Streamlit** on localhost runs capabilities and shows gate review for L2 output.
5. **Claude skill** (at least one migrated) invokes MCP tool instead of inline file ops — proof of agentic path.
6. No regression to v0.1/v0.2 Claude-native workflows that are not yet migrated (they keep working as today).

---

## Next document

Draft **`CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md`** from this scope — capability schemas, event format, LangGraph gate protocol, MCP tool definitions.
