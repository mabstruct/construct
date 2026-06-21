# Feature Research

**Domain:** CONSTRUCT v0.4 model-agnostic agent workflows
**Project:** CONSTRUCT
**Researched:** 2026-06-21
**Confidence:** HIGH for v0.4 behavior and scope from internal specs; MEDIUM for provider-specific details verified against current Tavily/LangGraph/LangChain docs

## Scope Framing

v0.4 is not a new product surface and not a generic PKM feature expansion. It is the milestone where CONSTRUCT's highest-value multi-step workflows become **testable, model-agnostic Python capabilities** while preserving the existing local-first workspace format and current Claude-native skill UX.

The user should still experience CONSTRUCT as a guided research/curation partner: "run research," "curate the graph," "continue daily cycle." The implementation behind that experience changes: skills stop doing opaque `WebSearch` / `WebFetch` and direct file orchestration; they delegate to CLI/MCP capabilities that execute the same LangGraph/LangChain/Python workflow graphs from any invoke surface.

The v0.4 product promise is therefore: **the same governed workflow runs from CLI, MCP, Streamlit gate review, or thin skills; every LLM/search result is structured and reviewable; no source-of-truth write happens without the existing validation/governance discipline.**

## Feature Landscape

### Table Stakes (Users Expect These)

Features users and agents should be able to rely on in v0.4. Missing these makes agent workflows feel incomplete, untrustworthy, or still Claude-locked.

| Feature | Why Expected | Complexity | Dependencies | User-Centric Behavior |
|---------|--------------|------------|--------------|-----------------------|
| Search provider spine | Research cannot remain coupled to Claude `WebSearch`; users expect repeatable search from CLI/MCP/skills | MEDIUM | v0.3 capability registry, provider config, `search-seeds.json`, governance caps | User/agent can run a configured provider-backed search and receive normalized results, not provider-shaped blobs |
| Mockable default search provider | Workflow tests must not require live web/API calls | MEDIUM | `SearchProvider` protocol, mock fixtures, contract tests | User can trust regressions are caught; agent can run tests offline with deterministic results |
| `research.search` capability | Smallest user-visible proof that search is model-agnostic | MEDIUM | Search provider spine, CLI/MCP registry parity | `construct research search` and MCP return the same `SearchResult` shape with title, URL, snippet/content, score, provider, query, date/domain where known |
| Cost/rate/governance caps for search | Users need predictable cost and bounded research cycles | MEDIUM | `governance.yaml`, `search/config.yaml`, provider response metadata | Research stops at configured query/result limits, reports truncation/degradation, and never silently exceeds caps |
| `research.score` structured L3 gate | Search results are not knowledge until relevance/source/action are judged | HIGH | Normalized search results, LLM provider factory, LangChain structured output, governance thresholds | User sees scored findings with relevance, source tier, key findings, ingest action, and reasoning before any ingest |
| `research.run` end-to-end workflow | Cold start and daily journeys depend on repeatable research → ingest | HIGH | `research.search`, `research.score`, dedup, existing `ingest.source`, gate review, events, workflow state | User says "start researching" and gets a digest: searched N queries, considered N results, approved/skipped N, ingested refs/cards, updated seeds, logged events |
| Deduplication before scoring/ingest | Repeated cycles should compound knowledge, not spam duplicate refs/cards | MEDIUM | Existing `refs/`, card IDs, URL/title normalization, search result contracts | User sees duplicates skipped or linked to existing refs; agent does not ask to review obvious repeats |
| Human review before SOT writes | Epistemic governance requires user approval for L2/L3-driven writes | MEDIUM | v0.3 Streamlit gate review pattern, CLI approve/reject path, workflow state | User can approve/reject/edit batches; reject means no cards/refs/connections/promotions are written |
| Governed ingest of approved findings | Approved research must become canonical workspace artifacts safely | MEDIUM | Existing ingestion pipeline, card/ref schemas, pre-write validation, event log | Approved findings produce valid refs/cards with source tier/confidence metadata and no schema drift |
| Research digest | Users need a clear outcome, not just file mutations | LOW-MEDIUM | Research run state, ingest summary, optional L2 narrative | User receives a concise, auditable summary of what changed, what was skipped, what needs review, and what to do next |
| Real `curation.run` PIPE steps | v0.3 curation placeholders are unacceptable for a workflow milestone | MEDIUM | `workspace.validate`, governance rules, graph/card/ref loaders, `graph.status` | User runs curation and gets actual integrity, decay, orphan, and report results; no silent no-op success |
| Curation promotion gate | Lifecycle changes should be justified, not automatic | HIGH | Card metadata, source/confidence rules, L3 `card.evaluate`/promotion output, human review | User sees promote/hold/escalate recommendations with target lifecycle and reasoning before lifecycle writes |
| Curation connection maintenance gate | Graph quality depends on typed, justified links | HIGH | Existing connection ops, `bridge.detect`, relation vocabulary, L3 typing/proposal gate | User sees proposed connections/types for approval; agent can maintain graph health without direct unreviewed writes |
| Workflow state, progress, pause/resume | Research/curation are long-running multi-step workflows | MEDIUM | v0.3 `WorkflowRunner`/state skeleton or LangGraph checkpoints, events | User can see current step, paused review queue, completed steps, failure reason, and resume/approve later |
| CLI/MCP parity for all new capabilities | Agents and future UI need one contract, not separate behaviors | MEDIUM | Capability registry, schema adapters, MCP tool exposure, CLI commands | Same inputs/outputs/errors whether invoked by terminal, MCP agent, or thin Claude skill |
| Thin research/curation skill migrations | Existing Claude-native UX must remain usable while behavior moves to Python | MEDIUM | Migrated `SKILL.md`, CLI/MCP commands, permission changes | User can keep saying "run research/curation" in Claude; skill delegates and presents results instead of using `WebSearch`/`WebFetch` or writing files directly |
| Event logging for workflow milestones | Local-first auditability is part of trust | LOW-MEDIUM | `log/events.jsonl`, existing event conventions | User/agent can inspect when search, scoring, approval/rejection, ingest, and curation completed |
| Degraded partial-result behavior | Web/API/LLM providers fail; workflows should remain useful | MEDIUM | Error handling, provider status, digest/report fields | User gets partial results with explicit degraded status instead of a total opaque failure when possible |
| Daily-cycle composition after research/curation stabilize | Daily journey expects research → curation → status as one guided path | HIGH | Stable `research.run`, stable `curation.run`, `graph.status`, workflow state | User can run a daily maintenance path only after sub-workflows are trustworthy; v0.4 should not fake it early |

### Differentiators (Competitive Advantage)

Features that make v0.4 valuable beyond simply replacing a skill implementation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Model-agnostic research and curation | CONSTRUCT workflows work from Claude, Cursor/MCP, CLI, and future UI without rewriting the workflow | HIGH | This is the central v0.4 differentiator; search and LLM providers must be config/factory driven |
| Epistemic gates instead of blind automation | Users see why something is relevant, promotable, or link-worthy before it enters canonical knowledge | HIGH | Combines L3 structured output, human review, and governed writes |
| Local-first audited agent workflows | Every workflow mutates only the file workspace and leaves event/history traces | MEDIUM | Strongly aligned with CONSTRUCT's "workspace is database" principle |
| Capability registry as shared product contract | CLI, MCP, skills, Streamlit, and future HTTP/UI can all call one capability surface | MEDIUM | Prevents v0.5 UI from becoming a second implementation |
| Governed search tied to domain seeds | Research follows user-configured domains/clusters and governance thresholds, not generic web browsing | MEDIUM | Makes search feel like knowledge-base maintenance rather than ad hoc querying |
| Review queues as first-class workflow state | Agent work can pause at meaningful human decisions and resume later | MEDIUM-HIGH | LangGraph supports human interrupts/checkpoints; v0.4 should expose them in CONSTRUCT's existing gate idiom |
| Resilient partial workflows | Failed provider calls produce explicit degraded reports and preserve completed steps | MEDIUM | Important for trust during real research cycles with network/provider variability |
| Composable daily cycle | Daily workflow becomes composition of real capabilities, not a brittle prose macro | HIGH | Only valuable after research and curation are stable; otherwise it masks unfinished behavior |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem attractive but should be explicitly rejected or deferred in v0.4.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| v0.5 browser-primary UI shell | Better user onboarding and visual workflow controls | Pulls UI ahead of proven workflow/runtime capabilities | Keep v0.4 CLI/MCP/Streamlit gate surfaces; design contracts for future UI only |
| HTTP API / MCP SSE / cloud deployment | Makes future integration easier | Not required for local workflow validation and expands security/ops scope | Keep stdio MCP + CLI parity; defer remote transports to v0.5+ |
| Skills continuing to use `WebSearch` / `WebFetch` | Faster migration, preserves old behavior | Keeps Claude lock-in, untestability, and duplicate orchestration | Remove from migrated research/curation skill permissions; delegate to `research.*` capabilities |
| Skills writing cards/refs/connections directly | Appears simpler for Claude-native flow | Bypasses pre-write gates, registry contracts, and model-agnostic execution | Skills classify intent, invoke CLI/MCP, present gate/digest results |
| Fully autonomous research ingest | Saves user clicks | Pollutes canonical knowledge with unreviewed L3/search judgments | Default `review_required: true`; approved batches only |
| Fully autonomous promotion/connection maintenance | Makes curation feel magical | Lifecycle and graph structure are high-impact epistemic writes | L3 proposes, human approves/rejects, Python writes through existing ops |
| Hardcoding Anthropic or Tavily inside graph nodes | Easier initial implementation | Violates model/provider-agnostic milestone goal and makes tests brittle | Use provider factories; Tavily is default adapter, mock is required, other providers slot in |
| Moving L1 conversational interviews into LangGraph | Looks like consistent workflow architecture | Domain-init/co-authorship chat is user dialogue, not bounded workflow execution | Keep L1 dialogue in skills/chat; only bounded gates and multi-step workflows move to Python |
| Full co-authorship/authoring graph in core v0.4 | Attractive high-value endpoint | Depends on stable research, gap analysis, synthesis gates; too much LLM surface | Defer to optional P3/W7 after research + curation stabilize |
| Academic provider suite in W1 | Better paper metadata from arXiv/Semantic Scholar | Expands provider scope before the abstraction is proven | Ship Tavily + mock first; add academic adapters after normalized contracts hold |
| SQLite/FTS/vector indexer for dedup | Better scale and fuzzy matching | Adds storage layer before file-based workflow correctness is proven | Use URL/title/ref-card dedup for v0.4 baseline; revisit indexer later |
| Full `views.generate_data` emission as workflow deliverable | Makes daily cycle visually satisfying | ADV-03 is separate view-emission debt, not required for workflow correctness | Optional refresh hook only; do not block workflow phases on views UI/data expansion |
| LLM tag extraction upgrade | Could improve metadata richness | v0.3 explicitly kept tag extraction deterministic; not central to v0.4 workflows | Keep regex/Python tag extraction; use LLM only for declared gates |
| Workspace format rewrite | Cleaner implementation opportunity | Breaks product continuity and migration constraints | Preserve cards/refs/connections/governance/search-seeds contracts |

## User and Agent Behavior Contract

| Capability / Workflow | User Perspective | Agent Perspective | Testable Acceptance |
|-----------------------|------------------|-------------------|---------------------|
| `research.search` | "Search this domain/query" returns bounded, understandable results with source URLs and snippets/content | Invoke CLI/MCP capability; pass query/max/time/provider parameters; never call Claude `WebSearch` | Same normalized schema from CLI and MCP; mock provider test passes without network |
| `research.score` | Sees ranked findings and recommended actions before ingest | Sends normalized results to L3 scorer using provider factory and structured output schema | Output validates against `ScoredFinding`/gate model; thresholds applied from governance |
| `research.run` | One command runs research cycle and pauses for approval before writing | Builds queries from seeds, searches, dedups, scores, queues review, ingests approved items, logs events | On fixture workspace, updates `search-seeds.json` timestamps, creates valid refs/cards only after approval, emits research events |
| Research gate review | Can approve/reject a batch and understand consequences | Presents pending gate queue; resumes workflow with decision; rejected items stop before writes | Reject path writes nothing; approve path continues deterministically |
| `curation.run` PIPE steps | Receives real health/maintenance report | Calls existing validators/loaders/status functions; no placeholder success responses | Integrity step invokes validation; report reflects actual card/connection counts/issues |
| Curation L3 gates | Sees promotion/connection proposals with reasons | Runs bounded structured gates; queues human review before lifecycle/edge writes | Proposed lifecycle/connection changes validate and require approval |
| Workflow state/resume | Can stop at review/failure and continue later | Persists current step, completed steps, gate queue, error, timestamps | Run state records `awaiting_review`, `failed`, and `completed` accurately |
| Thin skills | Existing Claude commands still work but are thinner and safer | Skill routes intent to CLI/MCP and summarizes outputs; no direct web/file orchestration | Migrated skill files remove `WebSearch`, `WebFetch`, `Write`, `Edit` for research/curation |
| CLI/MCP parity | Terminal and agent invocations behave the same | Registry is source of truth; adapters map schemas but do not reimplement logic | MCP tool schemas match CLI kwargs; handler return types are equivalent |

## Feature Dependencies

```text
v0.3 capability registry + CLI/MCP parity
    ├──requires──> new capability records for research.search / research.score / research.run / curation.run
    └──enables──> thin skill migrations

Search provider spine
    ├──requires──> search/config.yaml + env resolution + governance caps
    ├──requires──> mock provider fixtures
    └──enables──> research.search
                      └──enables──> research.score
                                        └──enables──> research.run

Existing ingestion + card/ref schemas + pre-write validation
    └──required-by──> research.run ingest_batch

Existing Streamlit gate review + workflow state skeleton
    ├──required-by──> research.run gate_review
    ├──required-by──> curation.run promotion/connection gates
    └──enables──> pause/resume and human-in-loop workflows

Existing workspace.validate + governance rules + graph.status
    └──enables──> curation.run PIPE steps
                      └──enables──> curation.run L3 gates

Existing bridge.detect + connection operations
    └──required-by──> curation connection maintenance

research.run + curation.run + graph.status
    └──enables──> workflow.daily_cycle composition

Stable CLI/MCP capability contracts
    └──enables──> v0.5 browser-primary UI later
```

### Dependency Notes

- **`research.run` must not start before `research.search` and `research.score` are contract-stable.** Otherwise the workflow graph will embed unstable provider and gate semantics.
- **Human review is a dependency, not polish.** Both research ingest and curation lifecycle/connection writes must pause before SOT mutation.
- **Curation should split PIPE before L3.** Integrity, decay, orphan, and report steps can land before promotion/connection gates; this closes v0.3 no-op debt without waiting on all LLM gates.
- **Daily cycle depends on real sub-workflows.** Do not compose daily-cycle until research and curation produce trustworthy outputs independently.
- **Thin skill migration depends on capability availability.** Update skill permissions only when the corresponding CLI/MCP capability can replace the old behavior.
- **Future UI depends on these contracts.** v0.4 should produce schemas, progress states, and review queues that a v0.5 browser can consume without changing workflow internals.

## MVP Definition

### Launch With (v0.4 Core)

Minimum viable v0.4 agent workflow delivery.

- [ ] Search provider spine with normalized `SearchResult`, default Tavily adapter, required mock provider, config/env resolution, and caps.
- [ ] `research.search` exposed through CLI and MCP with identical schemas and offline contract tests.
- [ ] `research.score` L3 structured gate with Pydantic-validated output, governance thresholds, and provider-factory LLM access.
- [ ] `research.run` search → dedup → score → human review → governed ingest → digest → seed/event update path.
- [ ] `curation.run` real PIPE steps for integrity, decay, orphan scan, report, and optional views refresh hook.
- [ ] Curation promotion and connection-maintenance gates with explicit human approval before lifecycle/edge writes.
- [ ] Workflow state/progress/error/review persistence for long-running or interrupted workflows.
- [ ] CLI/MCP parity for every new v0.4 capability.
- [ ] Thin migrations of research and curation skills removing direct `WebSearch` / `WebFetch` and direct write/edit orchestration.

### Add After Validation (v0.4 Follow-On)

Features to add after core research and curation are independently stable.

- [ ] `workflow.daily_cycle` composition — trigger after `research.run` and `curation.run` both have fixture-backed acceptance tests.
- [ ] CLI-only gate review ergonomics — JSON approve file or explicit `--approve-batch` flow if Streamlit is insufficient for non-UI sessions.
- [ ] Optional L2 narrative digest — add only after deterministic digest fields exist; narrative must not replace structured counts/decisions.
- [ ] Second real search provider or academic adapter — add after mock + Tavily prove the provider interface.
- [ ] `gap.analyze` / authoring skeleton — only if research/curation do not consume milestone capacity.

### Future Consideration (v0.5+ / Separate Track)

- [ ] Browser-primary UI, HTTP API, and rich gate modals — depend on v0.4 stable capability contracts.
- [ ] Full co-authorship graph — depends on stable research/gap/synthesis gates.
- [ ] SQLite/FTS/vector indexer — consider when file-based dedup becomes insufficient.
- [ ] Cloud, remote MCP/SSE, multi-user collaboration — outside local-first v0.4 workflow hardening.
- [ ] Full views data emission expansion — keep tracked separately from agent workflow delivery.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Rationale |
|---------|------------|---------------------|----------|-----------|
| Search provider spine | HIGH | MEDIUM | P1 | Removes Claude lock-in and enables all research work |
| `research.search` | HIGH | MEDIUM | P1 | First testable external acquisition capability |
| `research.score` | HIGH | HIGH | P1 | Prevents raw search from becoming ungoverned knowledge |
| `research.run` | HIGH | HIGH | P1 | Main user-visible research workflow |
| Human review before writes | HIGH | MEDIUM | P1 | Non-negotiable governance control |
| Governed ingest integration | HIGH | MEDIUM | P1 | Converts approved research into canonical workspace artifacts |
| `curation.run` PIPE steps | HIGH | MEDIUM | P1 | Closes v0.3 placeholder debt and restores workflow honesty |
| Curation L3 promotion/connection gates | HIGH | HIGH | P1 | Makes graph maintenance useful and governed |
| CLI/MCP parity | HIGH | MEDIUM | P1 | Required for model-agnostic agent workflows |
| Thin skill migrations | HIGH | MEDIUM | P1 | Preserves current UX while removing opaque Claude-native execution |
| Workflow state/resume | MEDIUM-HIGH | MEDIUM | P1 | Required for human gates and long runs |
| Event logging | MEDIUM | LOW-MEDIUM | P1 | Required for auditability and debugging |
| Daily-cycle composition | MEDIUM-HIGH | HIGH | P2 | Valuable only after research/curation stabilize |
| CLI-only gate ergonomics | MEDIUM | MEDIUM | P2 | Important fallback; Streamlit can cover first pass |
| Academic provider adapter | MEDIUM | MEDIUM-HIGH | P2/P3 | Useful for paper domains but should not block provider spine |
| Gap/authoring graph | MEDIUM | HIGH | P3 | Out of core v0.4 unless earlier workflows finish cleanly |

**Priority key:**
- **P1:** Must have for v0.4 core acceptance.
- **P2:** Add after core workflow contracts validate.
- **P3:** Defer unless milestone capacity remains and dependencies are stable.

## Explicit Deferrals and Non-Goals

- **Do not scope v0.5 UI.** Browser shell, HTTP API, and rich graph/wiki interactions wait for stable workflows.
- **Do not scope unrelated v0.3 debt unless it blocks workflows.** RT-01/RT-02 views/spike/tag registry bypass, ADV-03 full view emission, SPK-04, CR-02, and milestone-wide Nyquist/security cleanup are tracked elsewhere.
- **Do not replace workspace schemas.** Preserve cards, refs, connections, domains, governance, search seeds, and events.
- **Do not convert every skill to Python.** v0.4 focuses research, curation, and daily-cycle composition; L1 dialogue remains Claude/chat-native.
- **Do not promise full autonomy.** Human gates are part of the feature, not friction to remove.

## Sources

- `.planning/PROJECT.md` — v0.4 milestone goal, active requirements, constraints, and out-of-scope boundaries.
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — authoritative workflow topology, capability IDs, data structures, acceptance criteria, and phased next steps.
- `CONSTRUCT-CLAUDE-spec/user-journeys.md` — cold start, daily use, and co-authorship journey expectations.
- `.planning/milestones/v0.3-MILESTONE-AUDIT.md` — accepted v0.3 tech debt motivating curation no-op replacement and workflow focus.
- LangGraph docs via Context7 (`/langchain-ai/langgraph`) — human interrupts and checkpoint persistence support human-in-the-loop, pause/resume workflows.
- LangChain docs via Context7 (`/websites/langchain_oss_python_langchain`) — `with_structured_output(..., method="json_schema")` supports bounded structured LLM gate output.
- Tavily Python SDK docs — search parameters/response fields, `include_raw_content`, `max_results`, `time_range`, result `score`, `raw_content`, and response metadata: https://docs.tavily.com/sdk/python/reference

---
*Feature research for: CONSTRUCT v0.4 Agent Workflows*
*Researched: 2026-06-21*
