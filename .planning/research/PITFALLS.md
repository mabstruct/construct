# Pitfalls Research

**Domain:** CONSTRUCT v0.4 model-agnostic agent workflows — search provider spine, research/curation workflows, LangGraph/LangChain gates, human review, CLI/MCP parity, thin skill migrations  
**Researched:** 2026-06-21  
**Confidence:** HIGH for repo-specific risks; HIGH for LangGraph/LangChain/Tavily API capabilities verified through current docs; MEDIUM for product-risk severity estimates

## Scope Guardrail

This file focuses only on pitfalls introduced by **v0.4 Agent Workflows**. It intentionally does **not** re-litigate v0.5 browser UI work, general local-first architecture, or unrelated v0.3 carry-over debt except where that debt can derail `research.search`, `research.score`, `research.run`, `curation.run`, human gates, CLI/MCP parity, or skill migration.

## Roadmap Phase Names Used

| Phase | Name | Primary risk it must retire |
|-------|------|-----------------------------|
| **W1** | Search provider spine | Provider abstraction, config, mockability, normalized search contracts |
| **W2** | Research score gate | L3 scoring/extraction schema, LLM provider factory, threshold semantics |
| **W3** | Research run workflow | End-to-end search → score → review → ingest → digest; research skill migration |
| **W4** | Curation PIPE steps | Replace placeholder no-ops with deterministic integrity/decay/orphan/report handlers |
| **W5** | Curation L3 gates | Promotion/connection gates, durable review, curation skill migration |
| **W6** | Daily-cycle composition | Compose stable research + curation with one parent state/progress model |
| **W7** | Gap + authoring optional | Only after research/curation are stable; avoid scope creep in W1–W6 |

---

## Critical Pitfalls

### Pitfall 1: Search provider abstraction leaks into workflow code

**What goes wrong:**
`research.search` is nominally provider-agnostic, but `research.run` calls Tavily-specific fields, constructors, exceptions, or MCP tools directly. The first provider works, tests pass against happy-path Tavily JSON, and then provider swap fails because the graph depends on Tavily's native shape instead of CONSTRUCT's `SearchResult` / `SearchBatchOutput` contracts.

**Why it happens:**
The fastest implementation path is to wire Tavily inside the graph node. That violates the spec's provider-spine intent and recreates the Claude `WebSearch` lock-in under a new name.

**How to avoid:**
- Implement `src/construct/search/` first with a `SearchProvider` protocol and a factory before any `research.run` graph node exists.
- Make graph nodes accept and return only normalized Pydantic models (`SearchResult`, `SearchBatchOutput`) with `extra="forbid"`.
- Add a `mock` provider as a first-class adapter in W1; treat Tavily as one adapter, not the interface.
- Do not call Tavily MCP directly from skills or graph nodes; wrap it behind the Python provider if ever used.
- Make provider-specific exceptions map to CONSTRUCT operation errors (`quota`, `timeout`, `bad_config`, `partial_results`) at the adapter boundary.

**Warning signs:**
- Imports from `tavily` appear in `src/construct/pipelines/research.py` or LangGraph node modules instead of only `src/construct/search/tavily.py`.
- `research.run` tests monkeypatch Tavily rather than the `SearchProvider` interface.
- Returned data still contains native keys such as `content` instead of normalized `snippet`.
- A provider swap test requires changing graph code.

**Acceptance tests:**
- `research.search` with the mock provider returns only `SearchBatchOutput` / `SearchResult` fields and rejects extra native provider fields.
- Switching config from `provider: tavily` to `provider: mock` changes only config/env, not graph code.
- Contract tests run with no network and no Tavily API key.
- Tavily response keys `title`, `url`, `content`, `score`, optional `raw_content`, `response_time`, and `query` are mapped exactly once in the adapter.

**Phase to address:**
**W1 — Search provider spine**. Do not start W3 until this has a mock provider and provider-swap test.

---

### Pitfall 2: Search config and secrets become ambiguous

**What goes wrong:**
Search configuration is split across `src/construct/search/config.yaml`, `.construct/model-routing.yaml`, `.construct/governance.yaml`, environment variables, and ad-hoc CLI flags. API keys leak into committed workspace files, or the wrong config wins silently. Users cannot tell whether Tavily, mock, Brave, or another provider is active.

**Why it happens:**
v0.3 already has LLM config and workspace governance. v0.4 adds search config with overlapping concerns: provider, rate caps, thresholds, and query limits. It is easy to duplicate fields instead of assigning ownership.

**How to avoid:**
- Keep provider credentials out of workspace files. Store only `api_key_env` in config; read the secret from env.
- Use the spec's resolution order: explicit CLI flag → `CONSTRUCT_SEARCH_CONFIG` env override → repo default YAML.
- Keep governance thresholds (`relevance_threshold`, `card_creation_threshold`, `max_papers_per_cycle`) in workspace governance; keep provider settings and query caps in search config.
- Surface the resolved provider and config source in `research.search --json`, `research.run` digests, and events.
- Validate config at capability start and fail with a typed, actionable error before issuing API calls.

**Warning signs:**
- `.construct/model-routing.yaml` grows `TAVILY_API_KEY` or provider-specific fields.
- Tests set provider by monkeypatching graph internals instead of config/env.
- Missing API key errors appear halfway through a workflow rather than during preflight.
- Digests say "search failed" without naming provider/config source.

**Acceptance tests:**
- Missing Tavily key returns `success=False` with an error explaining the required env var, before any search call.
- `CONSTRUCT_SEARCH_CONFIG` override is honored in tests.
- Workspace files created by `construct init` contain no provider secrets.
- `research.search --json` includes `provider`, `config_source`, `truncated`, and request cap metadata.

**Phase to address:**
**W1 — Search provider spine**.

---

### Pitfall 3: “Model-agnostic” gates still hardcode Anthropic

**What goes wrong:**
`research.score`, `card.evaluate`, and curation L3 gates claim to use routing config, but graph nodes instantiate `ChatAnthropic` directly or assume Anthropic-specific structured-output behavior. Anthropic works; OpenAI/Ollama/mock providers fail or require graph rewrites.

**Why it happens:**
The existing `ask.domain` implementation is a useful v0.3 pattern but currently imports `ChatAnthropic` directly inside `ask_domain.py`. If v0.4 copies that pattern without a provider factory, the milestone misses its model-agnostic goal.

**How to avoid:**
- Add or harden a shared LLM provider factory before W2 gates are implemented.
- Gate modules should ask for `get_chat_model(gate_id, provider_override=None)` and then call `with_structured_output(...)` where supported.
- Keep provider-native structured output where available, but normalize failures into gate errors rather than provider stack traces.
- All L3 gate tests should monkeypatch the factory, not a provider-specific class.
- Preserve `method="json_schema"` for supported providers and document fallback behavior for providers that cannot enforce schema natively.

**Warning signs:**
- `from langchain_anthropic import ChatAnthropic` appears in new v0.4 gate modules.
- Gate inputs accept `provider_override` but it only changes metadata, not the instantiated model.
- Tests pass only when `ANTHROPIC_API_KEY` is present.
- A mock model cannot exercise `research.score` without pretending to be Anthropic.

**Acceptance tests:**
- `research.score` and `card.evaluate` run with a fake provider factory and no real API key.
- A config-driven provider override changes the model metadata returned in `GateMetadata`.
- Static or grep-based regression test fails if new v0.4 gate modules import `ChatAnthropic` directly.
- Invalid provider structured output is rejected by Pydantic and blocks downstream writes.

**Phase to address:**
**W2 — Research score gate**, then reused by **W5 — Curation L3 gates**.

---

### Pitfall 4: Research scoring becomes LLM prose instead of a governed gate

**What goes wrong:**
The L3 scorer returns a narrative summary that the workflow loosely interprets. Relevance, source tier, categories, findings, and ingest action are not schema-validated. Low-quality or hallucinated findings slip into refs/cards because the LLM output is treated as judgment rather than data.

**Why it happens:**
Research extraction feels conversational. The old skill asked the agent to score and extract in prose. v0.4 must convert that into a narrow gate contract, not merely move the prompt into Python.

**How to avoid:**
- Implement `ResearchScoreGateOutput` and `ScoredFinding` exactly as validated Pydantic models with constrained scores, source tiers, and `ingest_action` enum.
- Apply governance thresholds deterministically after scoring: below threshold = skip; between thresholds = ref-only; above card threshold = ref+card.
- Require each `key_findings` item to be grounded in the associated search result URL/content; never allow findings for URLs not present in the input batch.
- Record retrieval counts (`considered`, `selected`, `skipped`) and per-item reasoning for audit.
- Treat score gate output as pending until human review approves it.

**Warning signs:**
- `research.score` returns Markdown or a freeform `dict` instead of a Pydantic model.
- LLM reasoning includes claims not present in snippet/raw content.
- Threshold constants are duplicated in prompts, graph nodes, and ingestion code.
- Tests assert only that “some findings” exist.

**Acceptance tests:**
- A mocked LLM returning `relevance_score: 1.5`, source tier 0, unknown `ingest_action`, or extra fields fails validation.
- Findings below `relevance_threshold` cannot reach ingest.
- Ref-only and ref+card decisions follow governance thresholds exactly.
- Output includes `retrieval.considered`, `retrieval.selected`, and `retrieval.skipped` counts.

**Phase to address:**
**W2 — Research score gate**.

---

### Pitfall 5: Human review is not durable, or writes happen before review

**What goes wrong:**
`research.run` creates refs/cards before the user approves scored findings, or `curation.run` promotes cards/adds connections before a gate review. Alternatively, review exists only in Streamlit `session_state`, so pending gates disappear on restart and CLI-only users cannot proceed.

**Why it happens:**
v0.3 has a useful Streamlit gate-review pattern, but the current panel is largely session-state-backed for Q&A reviews. v0.4 workflows need durable workflow gates, not UI-local review state.

**How to avoid:**
- Persist pending review items in workflow state or a dedicated gate queue file under `log/`, with stable gate IDs and source item IDs.
- Default `review_required: true` for research score, promotion, and connection gates.
- Make `approve` / `reject` the only operations that allow SOT writes after L3 output.
- Provide CLI review commands or `--approve-batch <file>` semantics; Streamlit is optional, not required.
- Log `gate_review_approved` / `gate_review_rejected` consistently before writes continue.

**Warning signs:**
- A rejected finding still leaves a `refs/*.json` file or seed card.
- Pending review items vanish after restarting Streamlit or the CLI process.
- `workflow-state.json` has no `awaiting_review` / `gate_queue` status for paused gates.
- Streamlit is the only way to approve a research or curation workflow.

**Acceptance tests:**
- `research.run` with mocked high-score findings pauses in `awaiting_review` and writes no refs/cards before approval.
- Rejection leaves no new ref/card/promotion/connection and emits a rejection event.
- Pending gate survives process restart and can be approved via CLI.
- Streamlit approval and CLI approval both call the same registry capability or service path.

**Phase to address:**
Start in **W2** for score gate output; enforce end-to-end in **W3** and **W5**.

---

### Pitfall 6: Workflow state splits between LangGraph and `WorkflowRunner`

**What goes wrong:**
LangGraph checkpoints, `WorkflowRunner` state, Streamlit review state, and event logs each tell a different story. Resume works for simple placeholders but not for real gate pauses, failed searches, or daily-cycle child workflows.

**Why it happens:**
v0.3's `WorkflowRunner` persists one `log/workflow-state.json`; LangGraph supports checkpointing and human interrupts using thread/checkpoint IDs. If v0.4 adds LangGraph without deciding how these models interoperate, state becomes split-brain.

**How to avoid:**
- Decide in W2/W3 whether `WorkflowRunner` wraps LangGraph or LangGraph replaces runner internals for migrated workflows.
- Use one public `WorkflowRunState` shape with `status`, `current_step`, `completed_steps`, `gate_queue`, timestamps, and error.
- If using LangGraph interrupts, persist `thread_id` and interrupt IDs so resume can route human responses correctly.
- Namespace workflow runs by `run_id` before daily-cycle composition; avoid one global state file overwriting parallel/child runs.
- Emit `workflow_step_complete` events from the same state transition boundary.

**Warning signs:**
- `construct workflow status` says completed while a gate is still pending.
- Resuming after approval re-runs already completed search/score steps.
- Research and curation overwrite the same `workflow-state.json` during daily-cycle tests.
- LangGraph checkpoint IDs are invisible in CLI/MCP outputs.

**Acceptance tests:**
- A workflow paused at human review can be restarted and resumed without repeating completed provider calls.
- `workflow.status --json` reports `awaiting_review` with gate IDs.
- Two sequential workflow runs do not corrupt or overwrite each other's audit history.
- Daily-cycle child workflow state is visible under the parent without losing child step detail.

**Phase to address:**
Architecture decision by **W2**; implementation in **W3**, **W5**, and **W6**.

---

### Pitfall 7: Curation no-ops survive behind a new name

**What goes wrong:**
`curation.run` is registered and exposed via CLI/MCP, but internally it still calls the v0.3 placeholder step list or returns success messages like “Integrity check placeholder.” The roadmap appears complete while graph maintenance behavior remains imaginary.

**Why it happens:**
The v0.3 audit explicitly accepted WF-02/RT-04: `curation-cycle` placeholder no-ops in `catalog.py`. It is tempting to expose `curation.run` by wrapping the existing `workflow.run curation-cycle` path and defer the real handlers.

**How to avoid:**
- Implement W4 as a real replacement for `_get_workflow_steps("curation-cycle")`, not as a parallel demo path.
- Make integrity call the actual `workspace.validate` capability.
- Make decay/orphan/report deterministic Python modules with returned counts and item lists.
- Fail tests if placeholder messages appear in curation results or events.
- Keep L3 promotion/connection gates out of W4 until deterministic PIPE evidence is reliable.

**Warning signs:**
- `curation.run` completes on an intentionally corrupted workspace.
- Report actions show zero counts for workspaces with known stale/orphan cards.
- Code still contains placeholder messages in curation execution paths.
- The skill validation checklist passes without observing changed counts or real findings.

**Acceptance tests:**
- Corrupt `domains.yaml` or dangling connections cause the integrity step to report validation errors.
- Fixture with an old card flags decay based on governance rules.
- Fixture with an unconnected old card reports an orphan.
- Test fails if any `curation.run` step result message contains `placeholder`.

**Phase to address:**
**W4 — Curation PIPE steps**.

---

### Pitfall 8: LLM overreach in curation replaces deterministic graph logic

**What goes wrong:**
Curation becomes a monolithic LLM graph that reads cards and “decides” integrity, stale state, orphan status, lifecycle changes, and connection maintenance. It is expensive, nondeterministic, hard to test, and violates the tier model.

**Why it happens:**
LangGraph is new and attractive; implementers may use it for everything in the workflow because it handles orchestration. But CONSTRUCT's design is explicit: validation, metrics, decay scans, dedup, and file writes are PIPE, not LLM.

**How to avoid:**
- W4 must run with no LLM key.
- Use L3 only for ambiguous promotion decisions and connection typing after deterministic candidate generation.
- Make every L3 gate input include deterministic evidence: card metadata, citations, graph degree, candidate relation context.
- Keep promotion writes behind human approval unless governance explicitly permits a rule-based promotion.

**Warning signs:**
- `ANTHROPIC_API_KEY` is required for integrity/decay/orphan/report.
- Prompts ask the model to inspect raw `connections.json` for graph health.
- Tests mock LLM to make deterministic counts pass.
- Curation runtime cost scales with every card even for basic validation.

**Acceptance tests:**
- `curation.run --pipe-only` or W4 equivalent passes with no LLM config/API key.
- Deterministic orphan/decay counts are stable across repeated runs.
- Promotion L3 gate receives candidate cards only, not the whole workspace.
- Human rejection of a promotion leaves lifecycle unchanged.

**Phase to address:**
**W4** for PIPE boundaries; **W5** for bounded L3 gates.

---

### Pitfall 9: CLI/MCP parity regresses for new capabilities

**What goes wrong:**
`research.search`, `research.run`, `research.score`, or `curation.run` works in the CLI but not over MCP, or MCP exposes schemas that do not match handler signatures. v0.3 already had RT-03 TypeError failures; v0.4 can repeat them with more complex workflow inputs.

**Why it happens:**
The registry, CLI, and MCP are easy to update unevenly. The current MCP contract tests must be extended whenever new capabilities are added, not treated as one-time v0.3 coverage.

**How to avoid:**
- Every v0.4 capability must be a `CapabilityRecord` with input/output Pydantic models before CLI wiring.
- Add MCP tool name and CLI subcommand in the same plan as the capability.
- Use adapter shims only at registry boundaries; do not let CLI and MCP marshal different semantic inputs.
- Extend `tests/contract/test_mcp_contracts.py` expected tool set and schema-shaped invocation payloads in each phase.

**Warning signs:**
- A new CLI command imports and calls a service directly instead of going through `get_registry()`.
- MCP tool schemas omit fields that CLI requires, or use different field names (`workspace` vs `workspace_path`).
- Contract tests only check tool listing, not handler invocation.
- `--json` output differs structurally from MCP output.

**Acceptance tests:**
- Every new MCP handler invokes with advertised schema-shaped kwargs without `TypeError`.
- CLI `--json` and MCP serialized output share the same top-level fields for each capability.
- Registry tool count and expected names include `construct_research_search`, `construct_research_run`, `construct_research_score` if public, and `construct_curation_run`.
- Direct-import CLI paths are not introduced for v0.4 workflow capabilities.

**Phase to address:**
Every phase **W1–W6**; parity is not a final cleanup task.

---

### Pitfall 10: Research ingest is not idempotent or deduplicated enough

**What goes wrong:**
Repeated research runs create duplicate refs/cards for URL variants, repeated Tavily results, or title-equivalent papers. Existing ref ID dedup appends `-2`, `-3`, which prevents filename collisions but does not prevent semantic duplicates.

**Why it happens:**
The current ingestion pipeline is good at conforming writes to schema, but its `_deduplicate_ref_id` only checks file names. v0.4 research needs pre-ingest dedup against URLs, canonicalized URLs, titles, refs, and cards before the score/ingest boundary.

**How to avoid:**
- Normalize URLs before dedup: strip fragments, normalize trailing slashes, canonicalize DOI/arXiv URLs when possible.
- Deduplicate search results before scoring and again before ingest.
- Check existing `refs/*.json` URL/title and existing card titles/sources.
- Use idempotency keys per research finding (`provider`, `query`, canonical URL, cluster ID) in workflow state/events.
- Count duplicates in digest instead of silently skipping.

**Warning signs:**
- `refs/foo-2.json` appears after rerunning the same search fixture.
- Digest “ingested” count grows on identical mock provider responses.
- Duplicate cards share the same source URL but different IDs.
- Dedup tests assert only unique `ref_id`, not unique source identity.

**Acceptance tests:**
- Running `research.run` twice against the same mock results creates no second ref/card.
- URL variants (`https://x/a`, `https://x/a/`, `https://x/a#section`) dedup to one source unless content identity says otherwise.
- Same title + same source domain is skipped or escalated, not auto-ingested.
- Digest reports duplicate skip counts.

**Phase to address:**
Preliminary URL normalization in **W1**; full research-run idempotency in **W3**.

---

### Pitfall 11: Batch writes are partial, unaudited, or unrecoverable

**What goes wrong:**
A research batch writes some refs/cards, then fails on a later item. A curation batch promotes some cards, then fails adding a connection. The workspace remains valid by schema but semantically half-applied, with incomplete events and no clear recovery path.

**Why it happens:**
File-based SOT makes each write simple, but multi-item workflows need a mutation plan. v0.3 operations are mostly single-command; v0.4 workflows perform batches.

**How to avoid:**
- Build a staged mutation plan after human approval and before writes.
- Validate all candidate refs/cards/connections before writing the first item.
- Write events per item plus a batch summary event with counts and run ID.
- If rollback is not implemented, explicitly mark partial success and make rerun idempotent.
- Run `workspace.validate` after batch writes and fail the workflow if post-validation errors appear.

**Warning signs:**
- Batch loops call `ingest_source` one item at a time without a preflight plan.
- Event log contains item writes but no `research_cycle_complete` / `curation_cycle_complete` summary.
- A failed batch cannot be safely rerun.
- Tests inject failures only before the first write, not mid-batch.

**Acceptance tests:**
- Inject failure after item N in a research batch; rerun completes without duplicating items 1..N.
- Every written ref/card has a corresponding event containing the workflow run ID.
- Post-run `construct validate` returns zero errors for success and partial-success cases.
- Failed batch returns structured partial counts and recovery instructions.

**Phase to address:**
**W3 — Research run workflow** and **W5 — Curation L3 gates**.

---

### Pitfall 12: External provider failures either kill the whole workflow or runaway-retry

**What goes wrong:**
Tavily quota/timeouts cause `research.run` or daily-cycle to fail hard with no useful digest; or retry logic hammers the provider and burns quota. Partial results are discarded even though the spec says web search failures should continue with degraded state.

**Why it happens:**
Search APIs add real failure modes that did not exist in mocked Claude-native prose: invalid keys, usage limits, 429s, timeouts, bad parameters, and result truncation.

**How to avoid:**
- Add query and result caps before provider calls.
- Map provider errors to typed degraded states.
- Retry only safe transient errors with bounded backoff.
- Preserve partial successful query batches and include degraded status in digest/events.
- Do not update `last_queried` as if a failed cluster was successfully searched.

**Warning signs:**
- One failed query aborts all clusters.
- Digest reports “complete” after quota failure.
- Tests never simulate provider exceptions.
- Logs show repeated identical provider calls without cap metadata.

**Acceptance tests:**
- Mock provider raises quota/timeout on one query; workflow returns partial success with warning and preserves successful results.
- Query cap truncates extra queries and sets `truncated: true`.
- Failed clusters do not get a successful `last_queried` timestamp.
- Retry count is bounded and visible in run output.

**Phase to address:**
**W1** adapter errors and caps; **W3** workflow partial-result behavior.

---

### Pitfall 13: `search-seeds.json` updates are semantically wrong

**What goes wrong:**
`last_queried` is updated before human review, for clusters that failed, or for clusters skipped by caps. Tag approvals and manual search-seed edits are clobbered by a workflow rewrite.

**Why it happens:**
The old research skill updated seeds as a final instruction. In Python, it is easy to rewrite the whole JSON file from an in-memory copy without preserving concurrent/manual changes or per-cluster outcomes.

**How to avoid:**
- Update only clusters actually searched, and record status (`searched`, `partial`, `failed`, `skipped_cap`) if schema supports it.
- Preserve unknown fields and ordering where possible.
- Write seeds after review/ingest completion or explicitly distinguish `searched_at` from `ingested_at`.
- Validate `search-seeds.json` after write.
- Include cluster IDs in search, score, digest, and events to maintain traceability.

**Warning signs:**
- All active clusters get the same timestamp after a targeted run.
- Failed provider calls still advance `last_queried`.
- `search-seeds.json` diffs show unrelated formatting/field churn.
- Approved tag candidates disappear after research run.

**Acceptance tests:**
- Targeted run updates only selected clusters.
- Failed cluster timestamp remains unchanged or is marked failed without pretending success.
- Unknown fields in seed entries survive a run.
- `construct validate` passes after seed updates.

**Phase to address:**
**W3 — Research run workflow**.

---

### Pitfall 14: Thin skill migration breaks current Claude-native usability

**What goes wrong:**
Skills remove `WebSearch`/`WebFetch` or file-write tools before replacement capabilities actually work, or they document CLI commands that do not exist. Claude-native users lose the current workflow even though v0.4 is supposed to preserve skill UX while moving orchestration into Python.

**Why it happens:**
Skill migration looks like documentation cleanup, but it is an integration migration. The current research skill still allows `WebSearch`/`WebFetch`; the current curation skill already delegates to CLI/MCP but includes command examples that must be smoke-tested against the actual CLI surface.

**How to avoid:**
- Migrate each skill only after the corresponding capability passes CLI + MCP + fixture smoke tests.
- Replace inline procedure steps with exact, tested CLI/MCP invocations and expected JSON shapes.
- Remove `WebSearch`/`WebFetch` from research only when `research.run` can execute search through Python.
- Keep user-facing trigger language and output expectations stable.
- Add static tests for allowed-tools and command snippets.

**Warning signs:**
- `construct-research-cycle/SKILL.md` still lists `WebSearch`/`WebFetch` after W3.
- Skill commands use flags not supported by `construct`.
- The skill says to write digests/events manually after Python workflow already does it.
- Users must know whether to choose old skill flow vs new CLI flow.

**Acceptance tests:**
- Static test confirms migrated research and curation skills contain no direct `WebSearch` / `WebFetch` / `Write` / `Edit` where prohibited.
- Every fenced `construct ...` command in migrated skills is smoke-tested or generated from command help.
- Claude/Cursor can invoke the migrated capability via MCP using documented tool names.
- Old trigger phrases still route to the migrated skill.

**Phase to address:**
Research skill in **W3**; curation skill in **W5**.

---

### Pitfall 15: Tests rely on live search/LLM and miss contract failures

**What goes wrong:**
CI becomes flaky or skips the important paths because real Tavily/Anthropic keys are unavailable. Happy-path demos work, but schema failures, provider errors, review rejection, resume, and partial writes are untested.

**Why it happens:**
Agent workflows are tempting to validate with live end-to-end runs. The v0.3 playbook already separates LLM-backed smoke tests from deterministic tests; v0.4 must go further with mock providers because search and gates are core workflow dependencies.

**How to avoid:**
- Make mock search and mock LLM providers mandatory fixtures, not optional helpers.
- Contract-test each capability handler through registry, CLI, and MCP with schema-shaped payloads.
- Add negative tests for invalid LLM output, provider exceptions, rejected review, duplicate search results, corrupt state, and mid-batch failures.
- Keep live-provider tests as optional smoke tests outside the default suite.

**Warning signs:**
- Tests are skipped unless `TAVILY_API_KEY` or `ANTHROPIC_API_KEY` exists.
- Assertions check only `success=True`, not SOT diffs/events.
- No tests assert zero writes before human approval.
- MCP coverage is updated after implementation, not in the same phase.

**Acceptance tests:**
- Default `.venv/bin/python -m pytest` passes offline.
- New contract tests cover every v0.4 capability via registry and MCP handler invocation.
- Test suite includes at least one negative fixture per workflow phase: provider failure, invalid gate output, review rejection, duplicate input, resume after pause.
- Live Tavily/LLM smoke tests are explicitly marked and excluded by default.

**Phase to address:**
Every phase **W1–W6**. Testing is a design constraint, not a release hardening step.

---

### Pitfall 16: Daily-cycle composition starts before child workflows are stable

**What goes wrong:**
`workflow.daily_cycle` is wired early and masks child workflow gaps. It double-runs views hooks, overwrites workflow state, hides partial research failure, or reports success even when curation is still placeholder-backed.

**Why it happens:**
Daily cycle is the visible user journey, so it is tempting to wire the parent graph as soon as research and curation have partial demos. The spec explicitly sequences W6 after W3 and W5.

**How to avoid:**
- Treat W6 as composition only; no new research/curation behavior should be invented in the parent.
- Parent workflow must consume child operation results and propagate degraded/awaiting-review status.
- Parent owns a single optional views refresh hook after children complete or pause.
- Parent state must reference child run IDs and not overwrite their details.

**Warning signs:**
- Daily-cycle has its own search, scoring, promotion, or connection logic.
- Parent reports success while child is `awaiting_review`.
- Views refresh runs after both research and curation child steps.
- Fixing a child workflow requires editing daily-cycle logic.

**Acceptance tests:**
- Daily-cycle with research awaiting review pauses and exposes the child gate ID.
- Daily-cycle with search partial failure continues according to spec and reports degraded state.
- Daily-cycle runs exactly one views refresh hook when enabled; hook failure is warning-only.
- Daily-cycle cannot pass if `curation.run` still returns placeholder steps.

**Phase to address:**
**W6 — Daily-cycle composition** only after W3 and W5 acceptance tests pass.

---

## Technical Debt Patterns

Shortcuts that may appear efficient but create v0.4-specific long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode Tavily inside `research.run` | Fast demo | Provider swap impossible; tests need network | Never after W1 begins |
| Keep `ChatAnthropic` direct imports in new gates | Reuses v0.3 `ask.domain` pattern | False model-agnostic claim; mock/provider tests brittle | Only in a throwaway spike, not committed gate code |
| Store review queue in Streamlit session state only | Quick UI approval demo | CLI/MCP users blocked; pending gates disappear | Never for `research.run` / `curation.run` |
| Wrap existing `workflow.run curation-cycle` as `curation.run` | Quick registry entry | Preserves no-op debt under a new capability | Never; W4 exists to remove this |
| Use `ref_id-2` dedup as “good enough” | Avoids filename collision | Semantic duplicates compound across runs | Acceptable only as a fallback after URL/title dedup |
| Live-provider tests only | Proves real API works once | Flaky CI; no negative coverage | Optional smoke suite only |
| Manual skill doc migration without command tests | Fast docs update | Claude-native UX breaks silently | Never for migrated research/curation skills |
| Parent daily-cycle compensates for child gaps | User journey demo sooner | Duplicated logic; hidden child failures | Never; defer W6 |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Tavily Python SDK | Treat native `content` as CONSTRUCT's canonical field; forget optional `raw_content`; ignore quota/timeout exceptions | Map once in adapter: `content` → `snippet`, `score` → `provider_score`, optional `raw_content`; convert exceptions to typed provider errors |
| Search config | Put secrets or provider-specific settings in workspace governance/model routing | Use `api_key_env` and env vars; keep governance thresholds separate from provider config |
| LangChain structured output | Assume every provider enforces schemas identically | Use provider factory + Pydantic validation after model output; test invalid structured output |
| LangGraph interrupts/checkpoints | Pause in graph but not in CONSTRUCT workflow status | Persist `thread_id`/checkpoint/interrupt IDs into the public workflow state or wrap graph state in `WorkflowRunner` |
| Streamlit gate review | Treat UI button state as the gate queue | Make Streamlit a client over a durable gate queue and registry actions |
| MCP server | Add tool schema but not handler invocation tests | Extend schema-shaped handler tests for every new tool |
| Existing `ingest.source` | Let it create seed cards before research gate approval | Call ingest only after human approval; add preflight/idempotency around batch ingest |
| `views.generate_data` hook | Let the current stub fail the workflow | Keep views refresh optional and warning-only until the generator is real; parent W6 triggers once |

---

## Performance and Cost Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Query explosion from weighted clusters | Many provider calls for one cycle; quota errors | `max_queries_per_cycle`, per-cluster caps, truncation metadata | Even small workspaces with many seeds |
| Full raw-content scoring for every result | Slow L3 calls; huge prompts; high token cost | Fetch raw content only for shortlisted results or cap length before L3 | 10+ results with long pages |
| Whole-workspace L3 curation | Curation requires LLM for every card | Deterministic candidate generation; L3 only ambiguous candidates | Hundreds of cards |
| Re-running completed steps after resume | Duplicate provider calls and writes | Persist completed steps, provider call IDs, and gate IDs | Any paused/restarted workflow |
| Duplicate views refresh hooks | Daily-cycle feels slow and noisy | Single parent-owned hook after child workflows | W6 composition |

---

## Security and Privacy Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing provider API keys in search config or workspace files | Secret leakage through Git/workspaces | Store env var names only; add tests/templates that contain no real keys |
| Sending too much local workspace content to LLM gates | Private knowledge exposure and unnecessary cost | Candidate-scoped prompts; include only required evidence; document provider used in metadata |
| Trusting raw web content inside LLM prompts | Prompt injection can affect scoring/extraction decisions | Treat raw content as untrusted evidence; system prompt forbids instructions from sources; validate output schema and require human review |
| Logging raw provider payloads or secrets | Event log becomes sensitive/noisy | Log normalized metadata, counts, URLs, provider/error class; redact credentials and excessive raw content |
| Allowing skills to keep `Write`/`Edit` after migration | Agent bypasses governed Python write gates | Remove direct write tools from migrated research/curation skills; static-test allowed tools |

---

## UX and Migration Pitfalls

These are product risks for v0.4's existing CLI/MCP/skill UX, not v0.5 browser UI work.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Gate review requires Streamlit | CLI/MCP users get stuck at `awaiting_review` | File-backed queue plus CLI approve/reject; Streamlit optional |
| Research skill loses search before `research.run` is stable | Existing Claude-native research request stops working | Migrate after W3 passes; keep clear transition notes until then |
| New commands have inconsistent names | Users/agents cannot predict capability names | Align IDs, CLI, and MCP: `research.search`, `research.run`, `curation.run` |
| Degraded research looks like failure | Users rerun and create duplicates | Return partial-success digest with skipped/failed/ingested counts |
| Curation reports “success” without action detail | Users cannot tell if maintenance actually happened | Report deterministic counts, gate queue items, actions taken, and attention-needed list |
| Over-migrating L1 dialogue into P0/P1 graphs | Strategic/domain conversation becomes rigid | Keep domain-init/search steering/coauthoring dialogue outside W1–W5 |

---

## “Looks Done But Isn't” Checklist

- [ ] **`research.search`:** Often missing mock provider and provider-swap test — verify no network/API key required in default tests.
- [ ] **Search contracts:** Often missing strict Pydantic normalization — verify provider-native fields cannot leak past adapter.
- [ ] **Search config:** Often missing env override and secret hygiene — verify no workspace/template file contains real API key values.
- [ ] **`research.score`:** Often returns plausible JSON but bypasses governance thresholds — verify low/ref-only/card actions with fixtures.
- [ ] **LLM provider agnosticism:** Often metadata-only — verify fake/non-Anthropic provider can run the gate.
- [ ] **Human review:** Often UI-only — verify pending gate survives restart and CLI approval works.
- [ ] **`research.run`:** Often writes before approval — verify no refs/cards are created until approval.
- [ ] **Dedup:** Often filename-only — verify repeated mock run creates zero duplicate refs/cards.
- [ ] **`curation.run`:** Often wraps v0.3 placeholders — verify no output/event contains `placeholder`.
- [ ] **Curation PIPE:** Often accidentally requires an LLM key — verify integrity/decay/orphan/report pass offline.
- [ ] **CLI/MCP parity:** Often schema-only — verify every advertised MCP handler invokes without `TypeError`.
- [ ] **Skills:** Often docs-only migration — verify allowed-tools and command snippets by tests.
- [ ] **Daily cycle:** Often composes too early — verify W6 is blocked until W3/W5 pass and parent adds no child logic.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Tavily leaked into graph code | MEDIUM | Extract adapter boundary, add mock provider, rewrite graph node to consume normalized contract, add provider-swap regression test |
| Writes occurred before review | HIGH | Identify run ID/time window, archive or remove created refs/cards after user confirmation, add pending-review write block and rejection test |
| Duplicate research ingest | MEDIUM | Build duplicate detector over refs/cards, archive duplicates preserving connections, add idempotency key and repeated-run test |
| Curation placeholders shipped | MEDIUM | Fail roadmap gate, replace `_get_workflow_steps` handlers with real W4 modules, add placeholder-grep regression test |
| MCP parity broken | LOW–MEDIUM | Add adapter shim, extend schema-shaped handler tests, verify CLI/MCP output shape alignment |
| Workflow state split-brain | HIGH | Freeze new workflow work, choose runner/checkpointer ownership, migrate state to one public schema, add resume-after-review tests |
| Skill migration broke UX | LOW–MEDIUM | Restore previous skill in branch or add fallback note, fix command docs, add static command/allowed-tools tests before removing fallback |
| Provider quota caused bad seed timestamps | LOW | Revert affected `last_queried` values from Git/events if possible, distinguish searched/failed cluster status in seed update logic |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Search provider abstraction leaks | W1 | Mock + Tavily adapters both satisfy `SearchProvider`; provider swap without graph changes |
| Config/secrets ambiguity | W1 | Env override, missing-key, no-secret template tests |
| Anthropic hardcoding | W2, W5 | Fake provider factory tests; no new direct provider imports in gates |
| Ungoverned research scoring | W2 | Invalid-output and threshold-action tests |
| Non-durable human review / pre-review writes | W2, W3, W5 | Awaiting-review state, no-write-before-approve, CLI approve/reject tests |
| Workflow state split-brain | W2 decision; W3/W5/W6 implementation | Resume-after-review and child-run state tests |
| Curation placeholders | W4 | Real validate/decay/orphan/report fixture tests; placeholder-grep test |
| Curation LLM overreach | W4, W5 | W4 offline tests; W5 candidate-scoped L3 tests |
| CLI/MCP parity drift | Every W phase | Extend MCP expected tools and handler invocation tests per capability |
| Research dedup/idempotency | W1, W3 | Repeated-run and URL-variant dedup tests |
| Partial batch writes | W3, W5 | Mid-batch failure injection + rerun idempotency |
| Provider failures and cost caps | W1, W3 | Quota/timeout/cap/truncation tests with partial digest |
| Seed update semantics | W3 | Targeted/failed cluster timestamp preservation tests |
| Thin skill migration | W3 research; W5 curation | Allowed-tools and command snippet smoke tests |
| Live-only tests | Every W phase | Default pytest offline; live tests marked optional |
| Daily-cycle premature composition | W6 | Parent composition tests gated on W3/W5; one views hook; child status propagation |

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| W1 Search provider spine | Building Tavily adapter as the whole architecture | Protocol + normalized Pydantic contracts + mock provider before Tavily E2E |
| W1 Search config | Secrets/config duplicated across workspace and repo defaults | Explicit resolution order, env-only secrets, config-source metadata |
| W2 Research score gate | LLM output trusted as prose | Strict Pydantic output, deterministic thresholds, invalid-output tests |
| W2 LLM provider factory | Copying `ask.domain` direct Anthropic import pattern | Shared factory first; fake provider test before real provider test |
| W3 Research run | Writes before durable human approval | Persisted gate queue; no SOT writes until approval path executes |
| W3 Research ingest | Duplicate refs/cards compound | URL/title/card/source dedup and repeated-run fixtures |
| W4 Curation PIPE | No-op placeholders renamed | Real handler modules; placeholder regression test |
| W5 Curation gates | Promotions/connections auto-applied | L3 candidates + durable human approval + rejection no-op tests |
| W5 Skill migration | Current Claude-native curation/research UX breaks | Migrate only after capability smoke tests; static allowed-tools and command tests |
| W6 Daily cycle | Parent graph hides child failures | Compose only child capabilities; propagate partial/awaiting-review statuses |

---

## Sources

Repo-specific sources:

- `.planning/PROJECT.md` — v0.4 goal, active requirements, constraints, accepted out-of-scope boundaries (**HIGH confidence**)
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — target graph topologies, capability list, data structures, risks, phased sequence (**HIGH confidence**)
- `.planning/milestones/v0.3-MILESTONE-AUDIT.md` — accepted v0.3 debt: curation no-ops, RT-01/RT-02 bypass, verification gaps (**HIGH confidence**)
- `USER-TEST-PLAYBOOK-v03.md` — existing smoke-test behavior, offline vs LLM-backed expectations, known acceptable v0.4 carry-over (**HIGH confidence**)
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — layer model, LLM tier boundaries, CLI/MCP registry rule, v0.4/v0.5 sequencing (**HIGH confidence**)
- `src/construct/capabilities/catalog.py` — current registry, v0.3 curation placeholder step definitions, `views.generate_data` stub (**HIGH confidence**)
- `src/construct/pipelines/workflow_runner.py` — current single-file workflow state and resume behavior (**HIGH confidence**)
- `src/construct/ui/gate_review.py` — current Streamlit review pattern and session-state queue limitations (**HIGH confidence**)
- `src/construct/pipelines/ingestion.py` — current governed ingest, metadata flags, filename-only ref-id dedup fallback (**HIGH confidence**)
- `src/construct/llm/ask_domain.py` — current LangGraph gate and direct `ChatAnthropic` instantiation pattern to avoid copying blindly (**HIGH confidence**)
- `tests/contract/test_mcp_contracts.py` and `tests/unit/test_workflow_runner.py` — existing parity/resume regression patterns to extend in v0.4 (**HIGH confidence**)
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md` and `construct-curation-cycle/SKILL.md` — current skill migration state and command docs (**HIGH confidence**)

External/current documentation checked:

- LangGraph docs via Context7: human-in-the-loop interrupts, resume by interrupt ID, `thread_id` / `checkpoint_id` config for state management (**HIGH confidence**)  
  Sources surfaced from: `github.com/langchain-ai/langgraph` migration/checkpoint/prebuilt docs
- LangChain docs via Context7: `with_structured_output(..., method="json_schema")`; provider strategies for structured output with Pydantic/JSON Schema (**HIGH confidence**)  
  Sources surfaced from: `docs.langchain.com/oss/python/langchain/models` and `/structured-output`
- Tavily Python docs via Context7: search response fields (`title`, `url`, `content`, `score`, optional `raw_content`, `response_time`, `query`), `include_raw_content="markdown"`, max results, time ranges, and exception classes (**HIGH confidence**)  
  Sources surfaced from: `github.com/tavily-ai/tavily-python` autodocs

---

*Pitfalls research for: CONSTRUCT v0.4 Agent Workflows*  
*Researched: 2026-06-21*
