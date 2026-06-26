# Phase 9: LLM Provider Factory + research.score - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 9-LLM Provider Factory + research.score
**Areas discussed:** Factory scope & retrofit, Scoring strategy, ingest_action authority, source_tier derivation, Degraded-state handling, Input plumbing, content_categories source, CLI/MCP result shape, key_findings extraction

---

## Factory Scope & Retrofit

| Option | Description | Selected |
|--------|-------------|----------|
| Retrofit ask.domain too | Build factory AND swap ask_domain.py's hardcoded ChatAnthropic to use it. Closes spec line-546 anti-pattern now; one provider path. | ✓ |
| research.score only | Build factory, use only in research.score; leave ask_domain.py untouched. Smaller blast radius. | |

**User's choice:** Retrofit ask.domain too.

| Option | Description | Selected |
|--------|-------------|----------|
| Anthropic + Mock | Wire real ChatAnthropic + mock for offline tests. No new SDK deps. | |
| Anthropic + OpenAI + Mock | Also wire langchain_openai to prove cross-vendor swap concretely. +1 SDK dep. | ✓ |
| You decide | Let planner/researcher choose. | |

**User's choice:** Anthropic + OpenAI + Mock.
**Notes:** Captured `langchain_openai` as an optional extra to mirror Phase 8's Tavily-as-optional-dependency pattern (base install stays lean).

---

## Scoring Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One call per result | Each result its own structured-output call; per-item error isolation. N calls. | |
| Batch per call | Many results per prompt; cheaper but one bad item risks the batch. | |
| Per-result, concurrency-capped | Per-result calls (isolation) run concurrently with a bounded cap. | ✓ |

**User's choice:** Per-result, concurrency-capped.
**Notes:** Cap to be configurable.

---

## ingest_action Authority

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic Python mapping | LLM returns score; Python maps to action via governance thresholds. | |
| LLM chooses action | Thresholds in prompt; LLM emits ingest_action directly. Nuanced, non-deterministic. | ✓ |
| Hybrid (LLM + Python guard) | LLM proposes; Python clamps to governance-permitted. | (resolved into via follow-up) |

**User's choice:** LLM chooses action — refined by follow-up to add a Python ceiling clamp.

**Follow-up — Guardrail:**

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt + echo, no hard guard | Thresholds in prompt + echoed in metadata; trust LLM fully. | |
| Prompt + ceiling clamp | LLM chooses; Python caps at score-permitted action (never more permissive). | ✓ |
| Prompt + flag mismatch | LLM chooses freely; Python flags (doesn't change) over-threshold actions. | |

**User's choice:** Prompt + ceiling clamp — LLM nuance with a governance ceiling; thresholds echoed in gate metadata for criterion-3 provability.

---

## source_tier Derivation

| Option | Description | Selected |
|--------|-------------|----------|
| LLM judges it | LLM assigns source_tier from URL + content in structured output. | ✓ |
| Deterministic domain map | Config map of URL pattern → tier; predictable, testable, needs maintenance. | |
| Hybrid: map then LLM fallback | Map for known domains, LLM for unknown. | |

**User's choice:** LLM judges it.
**Notes:** Accepted non-determinism; offline tests control output via mock LLM. Deterministic map noted as a revisit option if tier drift destabilizes later promotion gates.

---

## Degraded-State Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip item, continue gate | Failed item → skip finding w/ reason; gate completes degraded. | |
| Skip item + one retry | Retry failed item once, then skip-with-reason; gate completes degraded. | ✓ |
| Fail whole gate | Any item failure aborts research.score with structured error. | |

**User's choice:** Skip item + one retry.
**Notes:** Added planner guidance that a total provider outage (all items failing) should surface as a gate-level degraded error rather than an all-skip "success."

---

## Input Plumbing

| Option | Description | Selected |
|--------|-------------|----------|
| Accept pre-fetched results | research.score takes a normalized SearchResults payload; pure gate. | ✓ |
| Run search inline | research.score takes a query, runs search itself, then scores. | |
| Support both | Accept results OR query (mutually exclusive). | |

**User's choice:** Accept pre-fetched results.
**Notes:** Keeps search→score composition for Phase 10 research.run; clean seam.

---

## content_categories Source

| Option | Description | Selected |
|--------|-------------|----------|
| Workspace taxonomy, soft | Load taxonomy into prompt; prefer existing, allow new when nothing fits. | ✓ |
| Free-form LLM | LLM emits any categories; no workspace coupling. | |
| Strict taxonomy only | Constrain to existing categories (enum); else uncategorized. | |

**User's choice:** Workspace taxonomy, soft.
**Notes:** Implies research.score input requires a workspace_path (read-only taxonomy load).

---

## CLI/MCP Result Shape

| Option | Description | Selected |
|--------|-------------|----------|
| JSON + CLI summary table | Canonical JSON contract for MCP/--json; CLI default also prints a table. | ✓ |
| JSON only | Both surfaces return raw JSON; no special CLI table. | |

**User's choice:** JSON + CLI summary table.

---

## key_findings Extraction

| Option | Description | Selected |
|--------|-------------|----------|
| LLM, non-skip only | Up to 5 key_findings, but only for non-skip findings; skips get []. | ✓ |
| LLM, always | Up to 5 key_findings for every finding regardless of action. | |

**User's choice:** LLM, non-skip only.

---

## Claude's Discretion

- Scorer system/user prompt wording and structure.
- Concurrency cap default value and config location.
- LangGraph topology for the per-result fan-out (single node vs mapped subgraph), provided isolation + degraded handling preserved.
- Whether key_findings are cleared when an LLM action is clamped down to skip.

## Deferred Ideas

- OpenAI/other providers as full first-class supported paths (this phase wires OpenAI to prove swap only).
- Deterministic source_tier domain map (rejected for D-07; revisit if tier drift destabilizes promotion gates).
- Strict taxonomy enforcement / category reconciliation (rejected for D-11 soft-steering).
- research.score running search inline (rejected, D-10 — Phase 10 research.run owns that).
- Score-gate result caching (out of scope).
