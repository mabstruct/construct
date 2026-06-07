# CONSTRUCT Agent — Orchestrator Specification

**Version:** 0.1.0
**Date:** 2026-04-21
**Status:** Draft — v0.1 scope
**Role:** Orchestrator, thinking partner, co-author

---

## 1. Identity

CONSTRUCT is both the product and the primary agent. It is the user's conversational partner — the entity they brainstorm with, steer research through, and co-author with. It is not a dispatcher. It does high-cognitive work directly and delegates routine operations to sub-agents.

**LLM tier:** Frontier (Claude Sonnet/Opus, or equivalent)

**Lineage:** Inherits from Watson (MABSTRUCT thinking partner). SOUL/IDENTITY governance documents carry over.

---

## 2. Responsibilities

### 2.1 What CONSTRUCT Does Directly (No Delegation)

| Responsibility | Trigger | Output |
|---------------|---------|--------|
| **Conversational reasoning** | User sends a chat message | Natural language response, drawing on graph state |
| **Cross-domain ideation** | User asks about connections, or Curator escalates a conflict | Reasoned analysis referencing specific cards |
| **Co-authorship** | User requests drafting, editing, or synthesis | Text produced collaboratively with human editorial control |
| **Editorial judgment** | Curator escalates contradictions, ambiguous promotions | Decision: keep both, merge, resolve, or defer |
| **Search pattern adaptation** | User requests `/search adjust` or domain config change | Updated search-seeds.json (proposed, human confirms) |
| **Domain initialization** | User runs `construct init` or adds a domain | Runs domain-init workflow: interview → config → seeds |
| **Strategic steering** | User discusses research direction | Updated priorities, new search clusters, domain scope changes |

### 2.2 What CONSTRUCT Delegates

| Task | Delegated to | When |
|------|-------------|------|
| Card validation, promotion, decay flagging | Curator | Every curation cycle (heartbeat) |
| Orphan detection, integrity checks | Curator | Every curation cycle |
| Connection typing for untyped edges | Curator | When untyped edges detected |
| Search cycle execution | Researcher | Every research interval |
| Paper ingestion, extraction, dedup | Researcher | During research cycle |
| Graph health summary | Curator | On `/graph status` or dashboard refresh |

### 2.3 What CONSTRUCT Receives Back (Escalations)

| From | Escalation | CONSTRUCT's action |
|------|-----------|-------------------|
| Curator | Contradicting mature cards | Reason about the contradiction, propose resolution to human |
| Curator | Ambiguous promotion (borderline) | Evaluate card, decide promote/hold/flag |
| Curator | Cross-domain bridge candidate (L1/L2) | Assess whether the connection is genuine, propose typed edge |
| Researcher | Unexpected finding outside domain scope | Decide: extend domain, create new domain, or ignore |
| Researcher | API failure after retries | Report to human, suggest alternative sources |

---

## 3. Task Routing

When a user message or system event arrives, CONSTRUCT classifies it and either handles it or delegates.

### 3.1 Classification Logic

```
Input arrives (chat message, command, inbox action, heartbeat event)
  │
  ├─ Is it a quick op (/graph status, /agents status, /db rebuild)?
  │   └─ Execute directly (no LLM, pure code)
  │
  ├─ Is it a knowledge op (/card add, /card seed, /gap-check, /connect)?
  │   └─ Delegate to appropriate sub-agent with structured task
  │
  ├─ Is it a research op (/search adjust, /research status)?
  │   └─ /search adjust → CONSTRUCT handles (needs judgment)
  │       /research status → Execute directly (read state)
  │
  ├─ Is it a synthesis request (/synthesize)?
  │   └─ v0.1: CONSTRUCT handles directly (Synthesizer agent is v0.2)
  │
  └─ Is it conversational?
      └─ CONSTRUCT handles directly (frontier model)
```

### 3.2 Delegation Protocol

When CONSTRUCT delegates a task to a sub-agent:

```python
# Conceptual — not literal API
class DelegatedTask:
    task_id: str              # unique, for tracking
    target_agent: str         # "curator" | "researcher"
    action: str               # e.g. "evaluate_card", "run_research_cycle"
    params: dict              # action-specific parameters
    context: list[str]        # file paths to load into agent context
    priority: str             # "immediate" | "next_cycle" | "background"
    callback: str             # "escalate" | "log_only" | "notify_user"
```

**Priority levels:**
- `immediate` — execute now, block until result (e.g., user-initiated `/card add`)
- `next_cycle` — execute on next heartbeat/curation cycle (e.g., inbox action processing)
- `background` — execute when idle (e.g., batch integrity check)

### 3.3 Context Building

Before handling a conversational message, CONSTRUCT loads:

1. **Always:** Graph summary stats (from `domains` table or views)
2. **If referencing a card:** That card's full content + neighborhood (1-hop connections)
3. **If referencing a domain:** Domain config + landscape summary
4. **If research-related:** Current search-seeds.json + recent research events
5. **If co-authoring:** Relevant cards by topic (FTS5 query on user's subject)

Context is assembled progressively — start small, expand if the response needs more.

---

## 4. Session Lifecycle

### 4.1 State Machine

```
IDLE ──► STARTING ──► RUNNING ──► STOPPING ──► IDLE
              │            │           │
              │            ▼           │
              │       PAUSED ──────────┘
              │         (user request)
              ▼
           FAILED ──► IDLE (after cleanup)
```

### 4.2 Session Start (`construct run`)

1. Log `session.start` event
2. Load governance.yaml — read intervals for heartbeat, curation, research
3. Start heartbeat timer (views rebuild)
4. Start curation timer (Curator maintenance cycle)
5. Start research timer (Researcher search cycle)
6. Start WebSocket server (chat + events)
7. Serve React UI (static files)
8. Enter RUNNING state — accept chat messages

### 4.3 Session Stop (`construct stop`)

1. Stop accepting new chat messages
2. Wait for in-flight tasks to complete (timeout: 30s)
3. Final views rebuild
4. Log `session.stop` event
5. Shutdown server
6. Enter IDLE state

### 4.4 Heartbeat Ticks

Three independent timers run during a session:

| Timer | Default interval | What it triggers |
|-------|-----------------|------------------|
| Views heartbeat | 30s | Rebuild `views/*.json` from workspace state |
| Curation cycle | 300s (5min) | Curator runs maintenance tasks |
| Research cycle | 3600s (1h) | Researcher runs a search cycle |

All intervals configurable via `governance.yaml`.

---

## 5. Event Actions

| Action | When logged | Detail |
|--------|------------|--------|
| `start_session` | Session begins | Session ID, config loaded |
| `end_session` | Session ends | Duration, tasks completed |
| `delegate_task` | Task sent to sub-agent | Task ID, target agent, action |
| `update_search_pattern` | Search seeds modified | Which clusters changed |
| `domain_init` | New domain created | Domain name, initial categories |
| `chat_response` | Conversational reply sent | Token count, model used |
| `escalation_received` | Sub-agent escalates | From agent, escalation type |
| `escalation_resolved` | CONSTRUCT resolves escalation | Decision, rationale |

---

## 6. Deferred (v0.2+)

| Capability | Why deferred |
|-----------|-------------|
| Synthesis delegation to Synthesizer agent | Agent not built yet — CONSTRUCT handles directly in v0.1 |
| Autonomous search pattern adaptation | Requires trust gradient and demonstrated competence |
| Multi-session coordination | Single-user, single-session in v0.1 |
| Telegram/external interface routing | Cloud layer deferred |
