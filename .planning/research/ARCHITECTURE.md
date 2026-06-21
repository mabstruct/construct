# Architecture Patterns

**Domain:** Local-first, agent-powered knowledge system
**Project:** CONSTRUCT
**Researched:** 2026-06-08
**Overall confidence:** HIGH

## Recommended Architecture

CONSTRUCT should keep the architecture already locked by ADR-0003: **workspace SOT first, Python pipeline runtime second, invoke adapters third, UI shell last**. That is the standard low-risk shape for systems that combine deterministic knowledge management with bounded agentic behavior.

```text
Layer 4  UI shell / graph-wiki browser / review modals
         React/Vite views now, richer UI in v0.5
         Never writes workspace files directly

Layer 3  Invoke surfaces
         CLI  -> MCP -> HTTP
         One capability registry, shared schemas, shared errors

Layer 2  Python runtime
         Pipelines, validators, graph ops, file I/O, workflow runner,
         event emission, derived-data generation

LLM gates (cross-cutting, not a primary layer)
         LangGraph subgraphs for ask/review/ambiguous decisions only

Layer 1  Workspace source of truth
         cards/, refs/, domains.yaml, governance.yaml,
         search-seeds.json, connections.json, log/events.jsonl

Layer 0  Skill and workflow specs
         SKILL.md, workflows, artifact catalog = authoritative WHAT
```

This is the right structure for CONSTRUCT because it preserves the current Claude-native prototype, hardens deterministic behavior in code, and gives v0.5 a stable backend instead of a chat-shaped one.

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **Workspace SOT** | Canonical knowledge state and audit trail | Python runtime only |
| **Capability registry** | Maps capability ID -> schemas -> handler -> adapter names | CLI, MCP, HTTP, runtime |
| **Pipeline handlers** | Deterministic validation, parsing, graph updates, derived view generation | Workspace SOT, workflow runner, event logger |
| **Workflow runner** | Orchestrates multi-step flows like Daily Cycle | Pipeline handlers, LangGraph gates, event logger |
| **LangGraph gates** | Bounded L2/L3 model decisions with structured I/O and optional human review | Workflow runner, retrieval helpers, provider config |
| **Retrieval/query helpers** | Read cards/refs/connections and assemble grounded context for `ask.domain` | LangGraph gates, runtime |
| **Event logger** | Append progress and audit events to `log/events.jsonl` | All mutating runtime paths |
| **Derived-data generator** | Rebuilds views/report JSON from workspace files | Pipeline handlers, UI |
| **CLI adapter** | Dev, CI, contract-test invoke surface | Capability registry |
| **MCP server** | Agent tool surface with same contracts as CLI | Capability registry |
| **HTTP API** | v0.5 browser surface; localhost first | Capability registry |
| **Claude skills / thin adapters** | Preserve current UX while delegating deterministic work to MCP/CLI | MCP or CLI |
| **UI shell** | Browse graph/wiki views, launch capabilities, review gated outputs | HTTP first; Streamlit spike may call CLI/MCP locally |

## Data Flow

### 1. Deterministic capability flow

```text
User / agent / UI
   -> CLI | MCP | HTTP
   -> capability registry
   -> Python handler / workflow step
   -> validate inputs
   -> read/write workspace SOT
   -> emit events.jsonl progress
   -> regenerate derived view data when needed
   -> structured result back through same adapter
```

### 2. L2 “talk to my data” flow

```text
Question
   -> ask.domain capability
   -> retrieval over cards/refs/connections
   -> LangGraph subgraph
   -> cited answer + structured metadata
   -> review surface if output could become a write
   -> optional follow-up capability call for any committed mutation
```

### 3. Research/curation workflow flow

```text
Workflow trigger
   -> workflow runner
   -> deterministic steps (validate, ingest, graph metrics, views data)
   -> L3 gate only at ambiguous judgment points
   -> human approve/reject where required
   -> commit SOT changes
   -> append audit events
   -> return report + next actions
```

### 4. v0.5 UI flow

```text
Browser UI
   -> HTTP capability endpoint
   -> same registry/schema as CLI and MCP
   -> pipeline/gate execution
   -> progress stream + result payload
   -> UI renders reports, cards, graph state, review modals
```

## Patterns to Follow

### Pattern 1: One capability contract, many adapters
**What:** Define every operation once in the registry, then expose it via CLI, MCP, and later HTTP.
**When:** All PIPE and L2/L3 capabilities.
**Why:** This is the main risk-reducer. Contract tests hit CLI first; MCP and HTTP stay thin.

### Pattern 2: Files as canonical state, everything else derived
**What:** Keep markdown/JSON/YAML workspace files as the only durable source of truth.
**When:** Always.
**Why:** It preserves continuity across Claude-native, v0.3, v0.4, and v0.5 and avoids migration churn.

### Pattern 3: LLM at named gates only
**What:** Use LangGraph only for `ask.domain`, promotion/review decisions, ambiguity resolution, and synthesis-style steps.
**When:** Only where deterministic rules are insufficient.
**Why:** LangGraph officially supports stateful, durable, human-in-the-loop orchestration; that fits CONSTRUCT's gated judgment model better than ad hoc model calls. Confidence: HIGH.

### Pattern 4: Human review before model-written SOT changes
**What:** Model outputs should usually become proposals, not direct writes.
**When:** L3 evaluation, extraction quality, ambiguous connection typing, synthesis commits.
**Why:** Matches CONSTRUCT's governance model and lowers silent corruption risk.

### Pattern 5: Derived browser views sit above the runtime
**What:** UI reads derived JSON/report data and invokes backend capabilities; it never edits workspace files directly.
**When:** Streamlit spike in v0.3 and full UI in v0.5.
**Why:** Streamlit's documented client-server model is fine for a localhost ops shell, but it should remain a shell over backend capabilities, not become the business-logic layer. Confidence: HIGH.

## Anti-Patterns to Avoid

### Anti-Pattern 1: UI-first write paths
**What:** Letting views, Streamlit, or future React components write cards/connections directly.
**Why bad:** Duplicates rules, bypasses validation, and breaks adapter symmetry.
**Instead:** All writes go through registered capabilities.

### Anti-Pattern 2: Chat-shaped backend contracts
**What:** Exposing freeform prompt endpoints instead of named tools/capabilities.
**Why bad:** Hard to test, impossible to version cleanly, easy to drift from SKILL.md.
**Instead:** MCP/CLI/HTTP stay 1:1 with capability IDs and JSON schemas.

### Anti-Pattern 3: LLM for deterministic work
**What:** Using model calls for validation, file parsing, graph metrics, or template generation.
**Why bad:** Costly, flaky, and contradicts ADR-0003.
**Instead:** Plain Python runtime.

### Anti-Pattern 4: Reintroducing the archived monolith too early
**What:** Pulling in SQLite indexing, remote deployment, heartbeats, or broad app-platform concerns during tranche 1.
**Why bad:** Scope explosion before the capability contracts are proven.
**Instead:** Land registry + CLI + MCP + one LangGraph gate + one workflow skeleton first.

## Suggested Build Order

This is the build order that best reduces risk **for this repo specifically**:

1. **Freeze stable contracts before new surfaces**
   - Finalize capability IDs, input/output schemas, error shapes, idempotency rules.
   - Finalize event schema for `log/events.jsonl`.
   - Confirm workspace file schema remains unchanged.
   - **Why first:** Every later layer depends on this.

2. **Implement deterministic runtime core**
   - `workspace.validate`
   - `graph.status`
   - `views.generate_data`
   - Shared file readers/writers, validators, graph utilities
   - **Why second:** These are low-ambiguity, high-leverage capabilities and create the foundation for CI-style contract testing.

3. **Add capability registry + CLI**
   - CLI becomes the golden invoke path.
   - Contract tests run here first against `test-ws/` fixtures.
   - **Why third:** Fastest path to proving contracts without UI or agent transport complexity.

4. **Add MCP stdio with exact schema parity**
   - Same capability names, same JSON shapes, same errors.
   - Migrate one thin Claude skill to prove agentic invocation.
   - **Why fourth:** Preserves the current Claude-native UX while moving deterministic work out of prompts.

5. **Add workflow runner skeleton**
   - Start with Daily Cycle orchestration.
   - Emit step progress to `events.jsonl`.
   - **Why fifth:** Once atomic capabilities work, orchestration becomes composition rather than invention.

6. **Add first LangGraph gate: `ask.domain`**
   - Retrieval helper + provider-configured LangGraph graph.
   - Structured output with citations.
   - **Why sixth:** This de-risks the LLM architecture without contaminating deterministic paths.

7. **Run Streamlit ops-shell spike**
   - Capability runner, JSON result viewer, gate review panel.
   - No direct SOT writes.
   - **Why seventh:** Lets the team learn UI interaction patterns after backend contracts exist.

8. **Only then design v0.5 UI-primary shell**
   - React/Vite views extension, CoPilotKit, or hybrid based on spike evidence.
   - HTTP becomes the primary UI transport.
   - **Why last:** UI should consume proven contracts, not define them.

## Interfaces That Should Stay Stable Across Versions

| Interface | Why it must stay stable | Version scope |
|-----------|-------------------------|---------------|
| **Workspace file formats** (`cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`) | Core continuity promise across Claude-native, v0.3, v0.4, and v0.5 | v0.2 -> v0.5 |
| **Capability IDs** | Lets skills, tests, MCP tools, and UI all target the same operations | v0.3+ |
| **Capability JSON schemas** | Prevents adapter drift and protects UI generation/testing | v0.3+ |
| **Error catalog / status semantics** | Required for reliable UI and agent handling | v0.3+ |
| **Event schema in `events.jsonl`** | Needed for workflow progress, auditability, and future UI activity feeds | v0.3+ |
| **LLM gate input/output contracts** | Allows provider swaps and UI review modals without rewriting workflow logic | v0.3+ |
| **Provider config shape** | Keeps model routing configurable rather than hard-coded | v0.3+ |
| **Derived views data contract** | Shields the UI shell from backend refactors | v0.3 -> v0.5 |

## Roadmap Implications

- **Phase 1 should be contract hardening**, not feature expansion.
- **Phase 2 should be deterministic runtime + CLI**, because that creates a testable backbone.
- **Phase 3 should be MCP migration for existing Claude skills**, preserving current workflows while reducing prompt fragility.
- **Phase 4 should add workflow orchestration and eventing**, because composition is safer after atomic ops are stable.
- **Phase 5 should add bounded LangGraph gates**, starting with read-mostly `ask.domain`.
- **Phase 6 should be the Streamlit spike**, explicitly as a decision-support artifact for **v0.5**.
- **Phase 7+ can plan the UI-primary shell (v0.5)**, once HTTP and derived-data contracts are clear.

## Source-Backed Conclusions

- **ADR-0003 is the correct architectural spine**: layered runtime, CLI first, MCP second, HTTP later, UI last. Confidence: HIGH.
- **MCP should stay a tool transport, not a second runtime**: official MCP docs define tools/resources/prompts over a client-server protocol with stdio for local servers and HTTP later for remote use. Confidence: HIGH. Source: https://modelcontextprotocol.io/docs/learn/architecture
- **LangGraph fits the L2/L3 gate role**: official docs describe durable, stateful, human-in-the-loop orchestration, which matches CONSTRUCT's review-gated model usage. Confidence: HIGH. Source: https://docs.langchain.com/oss/python/langgraph/overview
- **Streamlit is appropriate only as a localhost ops spike in v0.3**: official docs confirm its client-server model and session behavior; that is good enough for an operator shell, but not a reason to collapse backend boundaries. Confidence: HIGH. Source: https://docs.streamlit.io/develop/concepts/architecture/architecture

## Sources

- Repo source: `/Users/mab/dev/mabstruct/construct/.planning/PROJECT.md`
- Repo source: `/Users/mab/dev/mabstruct/construct/CONSTRUCT-CLAUDE-v03-planning/README.md`
- Repo source: `/Users/mab/dev/mabstruct/construct/CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md`
- Repo source: `/Users/mab/dev/mabstruct/construct/CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md`
- Repo source: `/Users/mab/dev/mabstruct/construct/CONSTRUCT-CLAUDE-spec/config-topology.md`
- Repo source: `/Users/mab/dev/mabstruct/construct/CONSTRUCT-CLAUDE-spec/validation-strategy.md`
- Repo source: `/Users/mab/dev/mabstruct/construct/CONSTRUCT-CLAUDE-spec/artifact-catalog.md`
- Official MCP docs: https://modelcontextprotocol.io/docs/learn/architecture
- Official LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview
- Official Streamlit docs: https://docs.streamlit.io/develop/concepts/architecture/architecture
