# Phase 9: LLM Provider Factory + research.score - Research

**Researched:** 2026-06-26
**Domain:** LangChain/LangGraph model-agnostic provider construction + L3 structured-output scoring gate
**Confidence:** HIGH (stack/patterns verified against installed packages + current LangChain docs; minor LOW areas flagged)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Build a `config.yaml`-driven provider factory **and retrofit `src/construct/llm/ask_domain.py`** to use it, replacing the hardcoded `ChatAnthropic(...)` at `ask_domain.py:228`. One consistent provider path across gates; pays off the spec-line-546 anti-pattern now. (Accept the ask.domain regression-test surface as part of this phase.)
- **D-02:** Wire **Anthropic + OpenAI + Mock** concretely. `langchain_anthropic` is already a dependency; add `langchain_openai` as an **optional extra** (mirrors Phase 8 Tavily-optional). The mock/fake LLM is the offline test oracle.
- **D-03:** Factory keyed off existing `llm/config.yaml` provider records (`ProviderConfig.type` → concrete chat model). A `research.score` gate entry is added to `config.yaml` `gates` (tier L3) alongside `ask.domain`.
- **D-04:** **Per-result** structured-output LLM calls (one finding per call), run **concurrently with a configurable cap**. Per-item error isolation. Cap configurable (llm/gate config).
- **D-05:** **LLM chooses `ingest_action`**, governance thresholds injected into prompt. **Python then ceiling-clamps**: `score < relevance_threshold` caps at `skip`; `score < card_creation_threshold` caps at `ref_only`; otherwise `ref_and_card` permitted. One-way ratchet toward conservatism.
- **D-06:** Governance thresholds (`relevance_threshold`, `card_creation_threshold`, `max_papers_per_cycle`) **echoed in gate metadata / retrieval block** so success criterion 3 is provable offline.
- **D-07:** **LLM judges `source_tier` (1-5)** from URL + content as structured output. No domain→tier map. Offline tests control output via mock.
- **D-08:** On individual scoring failure (invalid/unparseable output, provider error, timeout): **retry once**, then mark a `skip` finding with `reasoning: "scoring_failed: <cause>"`, increment retrieval error/retried counters, set gate-level `degraded` flag — gate **still completes** with partial good findings.
- **D-09 (planner guidance):** A *total* provider outage (every item failing) surfaces as a **gate-level degraded error**, NOT an all-`skip` "success." Distinguish per-item degradation from whole-provider failure.
- **D-10:** `research.score` **accepts a pre-fetched normalized `SearchResults` payload** (file path / stdin / param). It does **not** run search itself.
- **D-11:** **Soft workspace-taxonomy steering** — load workspace taxonomy (`taxonomy_seeds` / existing card `content_categories`) into prompt, ask LLM to *prefer* those while allowing new ones.
- **D-12 (contract note):** `research.score` input **requires a `workspace_path`** to load taxonomy (read-only). Does not violate no-writes boundary.
- **D-13:** Canonical `ResearchScoreGateOutput` (findings + gate metadata + retrieval counts) is the **JSON contract** for MCP and CLI `--json`. CLI default **additionally prints a human-readable summary table** (url, score, tier, action) + degraded/retried notice. Both surfaces share the same structured object.
- **D-14:** LLM extracts **up to 5 `key_findings`, only for non-`skip` findings**; skipped items get `[]`.

### Claude's Discretion
- Scorer system/user prompt wording and structure.
- Exact concurrency cap default value and where it lives in config.
- LangGraph topology for per-result fan-out (single fan-out node vs. mapped subgraph) — provided it preserves per-item isolation (D-04) and degraded handling (D-08).
- Whether `key_findings` are cleared when an LLM action is clamped down to `skip` (D-14 note).

### Deferred Ideas (OUT OF SCOPE)
- OpenAI/other providers as full first-class supported paths (this phase wires OpenAI only to *prove* swap).
- Deterministic source_tier domain map (rejected for D-07).
- Strict taxonomy enforcement / category reconciliation (rejected for D-11 soft-steering).
- `research.score` running search inline (rejected, D-10 — Phase 10 `research.run` owns it).
- Score-gate result caching (out of scope).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RSCH-01 | User can run `research.score` through CLI/MCP to convert normalized search results into structured, governance-aware finding proposals with relevance, source tier, ingest action, and reasoning. | Factory pattern (Standard Stack), `with_structured_output(method="json_schema")` cross-provider (verified), LangGraph Send fan-out + `max_concurrency` cap (verified), governance threshold load via `WorkspaceLoader.load_governance()`, registry auto-exposure for CLI+MCP parity, mock-LLM offline test oracle. |
</phase_requirements>

## Summary

This phase is a **refactor + greenfield hybrid** on a mature, well-patterned codebase. The hard parts are already solved in-repo: `ask_domain.py` is a complete LangGraph L3-style gate with `with_structured_output(method="json_schema")`, a `GateMetadata` model, a `run_gate()` runner, and retrieval-counts. The `llm/config.py` loader already parses `ProviderConfig.type` and `GateConfig`. Phase 8 shipped a `SearchProviderFactory` that is a near-exact structural template for the new LLM provider factory (resolve config → branch on type → return instance, with optional-dependency lazy import). The capability registry auto-exposes CLI + MCP from one `CapabilityRecord`, so RSCH-01's "CLI + MCP" requirement is free once the handler is registered.

The verified environment is **LangChain 1.x** (langchain-core 1.4.6, langchain-anthropic 1.4.5) and **LangGraph 1.2.4**. Critically, the `langchain` umbrella package is **not installed** — only the granular packages — so `init_chat_model` is **not available** and must not be used; the factory must map `ProviderConfig.type → concrete ChatModel class` directly (mirroring Phase 8's `SearchProviderFactory`). `with_structured_output(..., method="json_schema")` is natively supported by both `ChatAnthropic` and `ChatOpenAI` in these versions (verified against current LangChain docs). `langchain-openai` (latest 1.3.3, official langchain-ai repo) becomes a new optional extra.

The two genuine design risks are (1) **concurrency semantics** — a sync LangGraph `invoke` respects `config={"max_concurrency": N}` via an executor, but the async `ainvoke`/`asyncio.gather` path does **not** bound concurrency, so D-04's cap must be implemented with care; and (2) **degraded-state discrimination** (D-08 vs D-09) — distinguishing per-item failure from total provider outage requires the runner to count failures against total items and promote to a gate-level error when all (or a threshold of) items fail, rather than silently returning an all-`skip` "success."

**Primary recommendation:** Build `src/construct/llm/factory.py` as a direct structural copy of `SearchProviderFactory` (type→class map, lazy `langchain_openai` import, clear `GATE_PROVIDER_ERROR` on missing/unknown provider). Build `src/construct/llm/research_score.py` by templating `ask_domain.py`'s `run_gate()` skeleton, using a **sync** LangGraph fan-out with `Send` (from `langgraph.types`) and a bounded executor (`config={"max_concurrency": cap}`) — or a plain bounded loop/`ThreadPoolExecutor` if the per-item retry/degraded bookkeeping is cleaner outside the graph. Retrofit `ask_domain.py` to call the factory in the same commit set. Extend `tests/llm/conftest.py`'s mock pattern with a configurable structured-output fake + invalid-output fixtures.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Provider construction (type→ChatModel) | LLM/factory layer (`llm/factory.py`) | Config loader (`llm/config.py`) | Single place that knows vendor SDK imports; lazy-imports optional deps. |
| Per-result scoring (LLM call) | L3 gate (`llm/research_score.py`) | Factory (gets the model) | Gate owns prompt + structured schema + per-item isolation. |
| Governance clamp + threshold echo | L3 gate (Python post-LLM) | Workspace loader (reads governance.yaml) | Deterministic policy enforcement must live in Python, not the LLM (D-05). |
| Taxonomy steering input | L3 gate (read-only load) | `WorkspaceLoader` | Gate loads domains/cards read-only into the prompt (D-11/D-12). |
| Input payload plumbing | Capability handler / pipeline shim | CLI/MCP adapters | Accepts pre-fetched SearchResults (file/stdin/param), no search (D-10). |
| CLI table + JSON parity | CLI layer (`cli.py`) + registry | MCP server (auto) | Registry gives MCP parity free; CLI adds the human table (D-13). |
| Scoring orchestration / concurrency | L3 gate runner | LangGraph runtime | Fan-out + bounded concurrency + retry/degraded bookkeeping. |

## Standard Stack

### Core
| Library | Version (verified in venv) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-core` | 1.4.6 `[VERIFIED: importlib.metadata]` | `with_structured_output`, message types, base chat model, fake models | Already the project's LLM substrate (ask_domain.py). |
| `langchain-anthropic` | 1.4.5 `[VERIFIED: importlib.metadata]` | `ChatAnthropic` provider | Already a core dependency (pyproject). |
| `langgraph` | 1.2.4 `[VERIFIED: importlib.metadata]` | Gate graph, `Send` fan-out, `max_concurrency` | Existing gate topology engine. |
| `pydantic` | 2.13.4 `[VERIFIED: importlib.metadata]` | `ScoredFinding`/`ResearchScoreGateOutput` schemas, structured-output target | Whole codebase contract layer. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-openai` | latest 1.3.3 on PyPI `[VERIFIED: PyPI registry]`; official `langchain-ai/langchain` repo `[CITED: docs.langchain.com/oss/python/integrations/chat/openai]` | `ChatOpenAI` provider for cross-vendor swap proof (D-02) | **Optional extra only** — lazy-imported by the factory; absence must degrade gracefully with a clear error. |
| `ruamel.yaml` | already a dep | Load `config.yaml` (existing `_load_yaml`) | No change — factory builds on `load_llm_config()`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct type→class map | `langchain.chat_models.init_chat_model` | **REJECTED for this repo:** `init_chat_model` lives in the `langchain` umbrella package, which is **NOT installed** (`ModuleNotFoundError: No module named 'langchain'` confirmed). Adopting it adds a heavy dependency and contradicts the lean granular-package posture. The direct map mirrors the already-shipped `SearchProviderFactory`. |
| LangGraph `Send` map-reduce subgraph | Plain `ThreadPoolExecutor` over results in one node | Both valid (D-04 discretion). `Send` is idiomatic LangGraph but makes per-item retry/degraded bookkeeping (D-08) and a total-outage promotion (D-09) harder to express than a bounded loop. A single fan-out node with an internal bounded executor may be simpler to make provable offline. |
| `GenericFakeChatModel` for mocks | Custom mock class (existing `MockChatAnthropic` pattern) | `GenericFakeChatModel.with_structured_output` exists but the fake just echoes messages — it will **not** reliably emit schema-valid JSON. The repo's existing `conftest.py` mock (returns a canned structured object from `.invoke()`) is the proven oracle — extend it. |

**Installation (new optional extra):**
```toml
# pyproject.toml — add to [project.optional-dependencies]
llm-openai = ["langchain-openai>=1.2,<2"]
```
`>=1.2,<2` pins the 1.x line that matches langchain-core 1.x. `[VERIFIED: PyPI — 1.3.3 latest, recent releases 1.2.x–1.3.x]`

## Package Legitimacy Audit

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| `langchain-openai` | PyPI | mature, actively released (1.3.3 latest, 1.2.x–1.3.x in last cycle) | github.com/langchain-ai/langchain (official monorepo) | not run (offline) — `[ASSUMED]` per protocol, but first-party LangChain package | **Approved** — official LangChain integration package, imported verbatim in current LangChain docs. |

**Packages removed due to slopcheck [SLOP]:** none.
**Packages flagged [SUS]:** none.

*slopcheck was not run in this session. `langchain-openai` is a first-party LangChain package (same monorepo as the already-trusted `langchain-core`/`langchain-anthropic`) and is imported verbatim in current official docs (`from langchain_openai import ChatOpenAI`). Risk is negligible; planner may still gate the install behind a `checkpoint:human-verify` if policy requires.*

## Architecture Patterns

### System Architecture Diagram

```
                 research.score capability (registry record)
                              │
            ┌─────────────────┴───────────────────┐
        CLI (`construct research score`)      MCP tool (`construct_research_score`)
        --json | default table (D-13)         JSON only (auto from registry)
            └─────────────────┬───────────────────┘
                              ▼
                  handler / pipeline shim
   input: pre-fetched SearchResults payload (file path | stdin | param)  + workspace_path   (D-10/D-12)
                              │
                              ▼
                   run_gate("research.score", input)        ◄── llm/config.py: resolve gate→provider
                              │                                   llm/factory.py: ProviderConfig.type → ChatModel
            ┌─────────────────┼─────────────────────────────┐
            ▼                 ▼                              ▼
   load governance      load taxonomy (read-only)     parse SearchResult[] (Phase-8 schema)
   thresholds (D-06)    domains.yaml + card            title/url/snippet/source_tier/score/...
                        content_categories (D-11)
            └─────────────────┬─────────────────────────────┘
                              ▼
          ┌──────────── FAN-OUT over results (bounded concurrency cap, D-04) ───────────┐
          │   per result:  build prompt (thresholds + taxonomy + result)                 │
          │                structured LLM call  → ScoredFinding (raw)                     │
          │                on error/invalid → retry once → else skip+reason (D-08)        │
          └──────────────────────────────┬────────────────────────────────────────────── ┘
                              ▼
        aggregate + Python ceiling-clamp ingest_action vs thresholds (D-05)
        + total-outage check: all/threshold items failed → gate-level degraded error (D-09)
                              ▼
        ResearchScoreGateOutput { findings[], gate(metadata+thresholds), retrieval{counts} }
                              │  (NO workspace writes — hard boundary)
                              ▼
        wrapped in OperationResult(data=output.model_dump(mode="json"))   ◄── registry contract
```

### Component Responsibilities
| File | New/Modify | Responsibility |
|------|-----------|----------------|
| `src/construct/llm/factory.py` | NEW | `ProviderConfig.type` → instantiated `ChatModel`; lazy import of optional `langchain_openai`; clear `GATE_PROVIDER_ERROR` on unknown/missing provider. |
| `src/construct/llm/research_score.py` | NEW | `ScoredFinding`, `ResearchScoreGateOutput`, the LangGraph gate, fan-out + clamp + degraded logic, `run_gate()`. Models defined **in this module** (avoid circular import with catalog). |
| `src/construct/llm/ask_domain.py` | MODIFY | Replace `ChatAnthropic(...)` at line 228 with `factory.build_chat_model(provider_cfg)`. Keep behavior identical (regression surface, D-01). |
| `src/construct/llm/config.yaml` | MODIFY | Add `research.score` gate entry (provider, temperature, review_required, concurrency cap field). OpenAI provider block already present. |
| `src/construct/llm/config.py` | MODIFY (maybe) | Add a concurrency-cap field to `GateConfig` (D-04, discretion on location). |
| `src/construct/capabilities/catalog.py` | MODIFY | Register `research.score` `CapabilityRecord` (cli_name + mcp_tool_name) following the `ask.domain` wrapping pattern. |
| `src/construct/cli.py` | MODIFY | Add `research score` subcommand under `research_app`; default human table (url/score/tier/action) + degraded notice; `--json` uses `_display_result`. |
| `pyproject.toml` | MODIFY | Add `llm-openai` optional extra. |
| `tests/llm/conftest.py` | MODIFY | Configurable structured-output mock + invalid-output fixtures + degraded/total-outage fixtures. |

### Pattern 1: Provider Factory (mirror SearchProviderFactory)
**What:** Branch on `ProviderConfig.type`, lazy-import optional vendors, return a constructed chat model.
**When to use:** Anywhere a gate needs a chat model — `ask_domain.py` and `research_score.py` both consume it.
**Example (target shape — adapt; verify exact ctor kwargs against installed versions):**
```python
# src/construct/llm/factory.py
from __future__ import annotations
from construct.llm.config import ProviderConfig

def build_chat_model(cfg: ProviderConfig, *, temperature: float = 0.2):
    """Map ProviderConfig.type → a concrete LangChain chat model. Lazy-imports optional vendors."""
    if cfg.type == "langchain_anthropic":
        from langchain_anthropic import ChatAnthropic  # core dep
        return ChatAnthropic(model=cfg.model, temperature=temperature, max_tokens=cfg.max_tokens)
    if cfg.type == "langchain_openai":
        try:
            from langchain_openai import ChatOpenAI  # optional extra
        except ImportError as exc:
            raise RuntimeError(
                "GATE_PROVIDER_ERROR: provider 'langchain_openai' requires the optional "
                "'llm-openai' extra. Install: pip install 'construct[llm-openai]'"
            ) from exc
        return ChatOpenAI(model=cfg.model, temperature=temperature, max_tokens=cfg.max_tokens)
    raise RuntimeError(f"GATE_PROVIDER_ERROR: unknown provider type '{cfg.type}'")
```
*Note:* `ollama` is already in `config.yaml` but is **out of scope** (D-02 wires only Anthropic/OpenAI/Mock). The factory should raise the clear unknown-provider error for it rather than silently supporting it, OR planner may leave a stub branch — discretion.

### Pattern 2: Structured output (cross-provider) — unchanged from ask_domain
**What:** `model.with_structured_output(ScoredFinding, method="json_schema")`.
**Verified:** Both `ChatAnthropic` and `ChatOpenAI` support `method="json_schema"` natively in the installed versions.
```python
# Source: docs.langchain.com/oss/python/integrations/chat/{anthropic,openai}
structured = llm.with_structured_output(ScoredFinding, method="json_schema")
finding = structured.invoke(messages)   # -> ScoredFinding (validated)
```

### Pattern 3: Bounded fan-out with per-item isolation (D-04 + D-08)
**What:** Score N results concurrently, capped, with each item's failure contained.
**Recommended:** A single LangGraph node (or the `run_gate` runner) that uses a bounded `ThreadPoolExecutor` (or LangGraph `Send` with a sync graph and `config={"max_concurrency": cap}`). Each worker does: build prompt → structured `.invoke()` → on exception/validation-error retry **once** → else produce a `skip` finding with `reasoning="scoring_failed: <cause>"` and flag the item failed.
```python
# Conceptual — planner picks Send-subgraph vs executor (discretion).
from concurrent.futures import ThreadPoolExecutor
def score_all(results, score_one, cap):
    failures = 0
    findings = []
    with ThreadPoolExecutor(max_workers=cap) as ex:
        for finding, failed in ex.map(score_one, results):  # score_one handles its own retry+isolation
            findings.append(finding)
            failures += int(failed)
    degraded = failures > 0
    total_outage = failures == len(results) and len(results) > 0   # D-09 promotion signal
    return findings, degraded, total_outage
```

### Anti-Patterns to Avoid
- **Using `init_chat_model`** — not installed; pulls in the `langchain` umbrella. Use the type→class map.
- **Async `ainvoke` / `asyncio.gather` for the cap** — does **NOT** respect `max_concurrency` (verified via LangGraph source). If you go async, bound it yourself with an `asyncio.Semaphore`.
- **Letting the LLM's `ingest_action` win without the Python clamp** — violates D-05; governance must be enforced deterministically.
- **Returning an all-`skip` "success" on total provider failure** — violates D-09; must surface a gate-level degraded error.
- **Defining `ScoredFinding`/`ResearchScoreGateOutput` in `catalog.py`** — circular-import hazard; define in the gate module (established repo constraint).
- **Writing anything to the workspace** — hard boundary; the gate is read-only (taxonomy read is allowed, D-12).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-schema constrained LLM output | Manual JSON parsing + regex repair | `with_structured_output(..., method="json_schema")` | Native provider support; returns validated Pydantic; already the repo pattern. |
| Provider selection | `if provider == "x": import ...` scattered in gates | `llm/factory.py` single map | The whole point of D-01/spec-546; one path. |
| Governance thresholds | Hardcode 0.3/0.6/50 | `WorkspaceLoader.load_governance().research.*` | Already typed (`ResearchConfig`); per-workspace; testable. |
| CLI↔MCP parity | Separate MCP tool defs | Register one `CapabilityRecord` | Registry auto-derives MCP tools + schemas (Phase 8 #5). |
| Config loading | New YAML parser | `load_llm_config()` (`llm/config.py`) | Already resolves explicit path / `CONSTRUCT_LLM_CONFIG` env / default. |
| Offline LLM | Real API in tests | Extend `conftest.py` mock (canned structured object) | Existing proven oracle; no network, deterministic. |
| Result envelope | Bespoke dict | `OperationResult(data=output.model_dump(mode="json"))` | Matches `ask.domain` handler; MCP `_serialize_result` + CLI `_display_result` already consume it. |

**Key insight:** Almost every sub-problem in this phase already has a shipped, tested in-repo solution. The phase is mostly *assembly + one new concurrency/degraded concern*, not invention.

## Common Pitfalls

### Pitfall 1: SearchResult schema drift (spec §6.1 vs. implemented Phase 8)
**What goes wrong:** Spec §6.1 (lines 240+) shows a *draft* `SearchResult` with `provider_score`, `raw_content`, `published_date`, `query`, `cluster_id`, `provider`. The **implemented** Phase 8 `SearchResult` (`src/construct/search/models.py`) is different: `title, url, snippet, source_tier, score, provider_specific, source_domain`. Planning to the spec draft will produce a wrong input contract.
**Why it happens:** Spec predates implementation; CONTEXT.md canonical_refs cite spec line 240 for "input shape."
**How to avoid:** Treat `src/construct/search/models.py` `SearchResult`/`SearchBatchOutput` as the **authoritative input contract**. Note `score` (not `provider_score`) and that `source_tier` is already present (D-07 has the LLM re-judge it — flag that the gate's tier may differ from the provider's).
**Warning signs:** Input model references `provider_score` or `raw_content` keys that don't exist.

### Pitfall 2: `max_concurrency` ignored on the async path
**What goes wrong:** D-04's cap silently does nothing; all N calls fire at once → rate limits / cost spikes.
**Why it happens:** LangGraph sync `invoke` honors `config={"max_concurrency": N}` (executor.map), but `ainvoke`/`asyncio.gather` does **not** (verified in LangGraph 1.2.4 `tool_node.py`).
**How to avoid:** Use the **sync** path with `config={"max_concurrency": cap}`, or a `ThreadPoolExecutor(max_workers=cap)`. If async is chosen, wrap calls in an `asyncio.Semaphore(cap)`.
**Warning signs:** Tests with many results all return instantly; provider rate-limit errors under load.

### Pitfall 3: Conflating per-item degradation with total outage (D-08 vs D-09)
**What goes wrong:** An auth/config error fails every item; gate returns `findings=[all skips], success=True` — a false "success."
**Why it happens:** Per-item isolation (D-08) catches the same exception N times and dutifully produces N skips.
**How to avoid:** Track `failures` vs `len(results)`. If all (or a configured threshold of) items failed with the *same provider-level* cause, promote to a **gate-level degraded error** (`OperationResult(success=False, ...)`), not an all-skip success. Consider classifying the cause: provider/auth/config errors → outage candidate; per-item invalid-output → genuine skip.
**Warning signs:** A run with zero usable findings reports `success=True`.

### Pitfall 4: Anthropic `json_schema` native structured output requires a recent model
**What goes wrong:** `method="json_schema"` may behave differently on older Claude models; real-API edge cases are not offline-testable.
**Why it happens:** Native structured output is a newer Anthropic capability; `config.yaml` pins `claude-sonnet-4-20250514`.
**How to avoid:** Keep `method="json_schema"` (already used by ask.domain). Do not attempt to verify real-provider behavior offline — that's what the mock is for. Flag for live smoke later. `[ASSUMED]` that the pinned model supports json_schema (ask.domain already relies on this).
**Warning signs:** Live (non-test) runs raise structured-output / tool-choice conflicts.

### Pitfall 5: Clamp-to-skip and key_findings (D-14 note)
**What goes wrong:** A finding the LLM scored as `ref_and_card` with 5 key_findings gets clamped to `skip` by D-05, but retains key_findings — inconsistent with "skips get `[]`."
**Why it happens:** D-14 clears key_findings based on the *LLM's* action; the clamp happens *after*.
**How to avoid:** Discretion (D-14 note). Recommended: after the Python clamp, if final `ingest_action == "skip"`, set `key_findings = []` and ensure `reasoning` carries the clamp rationale. Make this a single deterministic post-step so it's testable.
**Warning signs:** Output has `ingest_action="skip"` with non-empty `key_findings`.

## Runtime State Inventory

This phase is an internal **code refactor + greenfield gate** with no persisted/runtime state to migrate.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — gate writes nothing; no datastore keys renamed. | None |
| Live service config | None — no external service config embeds new strings. | None |
| OS-registered state | None. | None |
| Secrets/env vars | New provider needs `OPENAI_API_KEY` at runtime (read by `ChatOpenAI`); `CONSTRUCT_LLM_CONFIG` already supported. No secret renames. Offline tests must not require it. | Document env var; ensure tests use mock. |
| Build artifacts | `pyproject.toml` gains `llm-openai` extra → a fresh `pip install -e '.[llm-openai]'` is needed to exercise the OpenAI path locally; base install stays lean. | Note in plan; CI/test path uses mock, not the extra. |

**The retrofit regression surface (D-01):** `ask_domain.py` line 228 changes from direct `ChatAnthropic(...)` to `factory.build_chat_model(...)`. Existing `tests/llm/` ask.domain tests monkeypatch `construct.llm.ask_domain.ChatAnthropic`. After the retrofit, the monkeypatch target may move (e.g. to `construct.llm.factory.ChatAnthropic` or the factory function). **Planner must update the ask.domain test monkeypatch targets** or keep the symbol importable in `ask_domain` for back-compat.

## Code Examples

### Loading governance thresholds (D-05/D-06)
```python
# Source: src/construct/storage/workspace.py:107 + schemas/config.py:184
from construct.storage.workspace import WorkspaceLoader
gov = WorkspaceLoader(workspace_path).load_governance()
relevance = gov.research.relevance_threshold          # 0.3 default
card_create = gov.research.card_creation_threshold    # 0.6 default
max_papers = gov.research.max_papers_per_cycle        # 50 default
```

### Loading taxonomy for soft-steering (D-11/D-12)
```python
# Source: workspace.py:83 (load_domains_registry) + schemas/config.py:61 (DomainRegistryEntry.content_categories)
reg = WorkspaceLoader(workspace_path).load_domains_registry()
seed_categories = sorted({c for d in reg.domains.values() for c in d.content_categories})
# plus existing card categories (read-only):
card_categories = sorted({
    c for card in WorkspaceLoader(workspace_path).load_cards()
    for c in card.get("content_categories", [])
})
```

### Python ceiling-clamp (D-05) — deterministic, testable
```python
def clamp_action(llm_action: str, score: float, relevance: float, card_create: float) -> str:
    if score < relevance:
        return "skip"
    if score < card_create:
        return "ref_only" if llm_action != "skip" else "skip"
    return llm_action  # ref_and_card permitted; LLM may still be more conservative
```

### Registering the capability (mirror ask.domain, catalog.py:324)
```python
registry.register(CapabilityRecord(
    id="research.score",
    name="Research Score",
    description="Score normalized search results into governance-aware finding proposals (read-only, no writes)",
    input_model=ResearchScoreInput,
    output_model=ResearchScoreGateOutput,   # or OperationResult wrapper, matching ask.domain
    handler=_research_score_shim,            # wraps run_gate(...) → OperationResult(data=...)
    cli_name="research.score",
    mcp_tool_name="construct_research_score",
))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Send` from `langgraph.constants` | `from langgraph.types import Send` | LangGraph v1.0 (deprecation confirmed in 1.2.4) | Use `langgraph.types`; old import warns and is removed in v2. |
| `init_chat_model` as the blessed factory | Not usable here (umbrella `langchain` pkg absent) | n/a | Use explicit type→class map (matches Phase 8). |
| `with_structured_output` defaulting to function/tool calling | `method="json_schema"` native on Anthropic + OpenAI + Gemini | LangChain 1.x | Cross-provider structured output is uniform; ask.domain already uses it. |

**Deprecated/outdated:**
- `langgraph.constants.Send`: deprecated since LangGraph v1.0.
- Spec §6.1 draft `SearchResult` fields (`provider_score`, `raw_content`, etc.): superseded by the implemented Phase 8 model.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pinned model `claude-sonnet-4-20250514` supports `method="json_schema"` native structured output. | Pitfall 4 | Live (non-test) scoring could error; offline tests unaffected. ask.domain already relies on this, so risk is low. |
| A2 | `langchain-openai>=1.2,<2` is compatible with langchain-core 1.4.x. | Standard Stack | OpenAI swap path could fail to import; offline tests (mock) unaffected. Mitigate by installing the extra once and running a live smoke. |
| A3 | `langchain-openai` install is safe (slopcheck not run). | Package Audit | Negligible — first-party LangChain monorepo package, verbatim in official docs. |
| A4 | Mock structured-output via the existing conftest pattern (canned object from `.invoke()`) is sufficient for all four offline test classes. | Validation Architecture | If insufficient, may need a richer fake; pattern already proven for ask.domain. |

## Open Questions

1. **Input payload exact shape (D-10).**
   - What we know: `research.search` emits `ResearchSearchOutput{batches:[SearchBatchOutput...], provider, degraded, warnings}`; each batch has `results:[SearchResult]`.
   - What's unclear: Does `research.score` accept the full `batches` envelope, a flattened `list[SearchResult]`, or both (plus file-path/stdin loading)?
   - Recommendation: Accept a flattened `list[SearchResult]` as the canonical param, with a CLI/handler helper that flattens `batches` from a `--results-file`/stdin JSON. Keep `workspace_path` required (D-12). Planner to lock the input model.

2. **Where the concurrency cap lives (D-04, discretion).**
   - What we know: `GateConfig` (config.py:22) is the natural home; `config.yaml` gates already carry per-gate fields.
   - Recommendation: Add `concurrency_cap: int = <default>` to `GateConfig` and the `research.score` gate block. Default ~5 (LOW confidence on the exact number — tune to provider rate limits).

3. **Send-subgraph vs executor for fan-out (D-04, discretion).**
   - Recommendation: A single fan-out node using a bounded `ThreadPoolExecutor` is the lower-risk choice for expressing D-08 retry + D-09 total-outage promotion clearly and testably. Use LangGraph `Send` only if the planner wants per-item nodes visible in graph traces.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langchain-core` | structured output, fake model | ✓ | 1.4.6 | — |
| `langchain-anthropic` | Anthropic provider | ✓ | 1.4.5 | — |
| `langgraph` | gate graph + fan-out | ✓ | 1.2.4 | — |
| `langgraph-checkpoint` | (not needed this phase — no interrupts) | ✓ | 4.1.1 | — |
| `pydantic` | schemas | ✓ | 2.13.4 | — |
| `langchain-openai` | OpenAI swap proof (D-02) | ✗ (by design) | latest 1.3.3 on PyPI | Optional extra `llm-openai`; mock provides offline coverage; OpenAI path verified only when extra installed. |
| `OPENAI_API_KEY` | live OpenAI calls only | n/a (env) | — | Not needed for tests (mock); only for live swap smoke. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `langchain-openai` (optional extra; mock covers offline tests — success criterion 4 is met without it).

## Validation Architecture

> nyquist_validation is enabled (config.json `workflow.nyquist_validation: true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (`dev` extra) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=`tests`, pythonpath=`.`,`src`) |
| Quick run command | `./.venv/bin/python -m pytest tests/llm/test_research_score.py -x -q` |
| Full suite command | `./.venv/bin/python -m pytest -q` |
| Baseline test count | **253 tests collected** (must stay green — spec §10 acceptance #8 analog; D-01 retrofit must not regress ask.domain). |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| RSCH-01 | research.score runs via registry handler (CLI + MCP parity) | contract | `pytest tests/llm/test_research_score.py::test_registry_handler_cli_mcp_parity -x` | ❌ Wave 0 |
| RSCH-01 | normalized SearchResult[] → ScoredFinding[] with all fields | unit | `pytest tests/llm/test_research_score.py::test_scores_results_with_mock_llm -x` | ❌ Wave 0 |
| RSCH-01 (D-05/06) | governance clamp + thresholds echoed in gate metadata | unit | `pytest tests/llm/test_research_score.py::test_ceiling_clamp_and_threshold_echo -x` | ❌ Wave 0 |
| RSCH-01 (Succ.4) | invalid/unparseable output → retry-once → skip+reason | unit | `pytest tests/llm/test_research_score.py::test_invalid_output_degrades_to_skip -x` | ❌ Wave 0 |
| RSCH-01 (D-09) | total provider outage → gate-level degraded error (not all-skip success) | unit | `pytest tests/llm/test_research_score.py::test_total_outage_is_gate_error -x` | ❌ Wave 0 |
| RSCH-01 (D-01) | ask.domain still passes via factory (no regression) | regression | `pytest tests/llm/ -q` | ✓ exists (update monkeypatch targets) |
| RSCH-01 (factory) | unknown/missing provider → clear GATE_PROVIDER_ERROR | unit | `pytest tests/llm/test_factory.py -x` | ❌ Wave 0 |
| RSCH-01 (D-11) | taxonomy categories injected into prompt (read-only) | unit | `pytest tests/llm/test_research_score.py::test_taxonomy_soft_steering -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `./.venv/bin/python -m pytest tests/llm/test_research_score.py tests/llm/test_factory.py -x -q`
- **Per wave merge:** `./.venv/bin/python -m pytest tests/llm -q`
- **Phase gate:** full suite green (`./.venv/bin/python -m pytest -q`, ≥253 + new) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/llm/test_factory.py` — provider type→class map, lazy-import error, unknown-provider error.
- [ ] `tests/llm/test_research_score.py` — covers RSCH-01 behaviors above.
- [ ] `tests/llm/conftest.py` — extend with: (a) configurable structured-output mock returning a caller-supplied `ScoredFinding`-shaped object, (b) an invalid-output mock (raises / returns unparseable), (c) a total-outage mock (always raises a provider/auth error), (d) sample `SearchResult` fixtures matching the Phase 8 schema.
- [ ] Update existing ask.domain test monkeypatch targets for the factory retrofit (D-01).

*(No framework install gap — pytest present.)*

## Security Domain

> `security_enforcement` not present in config.json → treated as enabled. Scope is local-first, no network in tests.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user auth surface; provider API keys via env only. |
| V3 Session Management | no | Stateless gate. |
| V4 Access Control | yes (boundary) | **Hard no-writes boundary** — gate must not write to workspace SOT (cards/refs/connections/seeds/digests/events). Read-only taxonomy load permitted. Test must assert no workspace mutation. |
| V5 Input Validation | yes | Pydantic `extra="forbid"` on input model; `ScoredFinding` validates ranges (score 0–1, tier 1–5, key_findings max 5, ingest_action Literal). Untrusted LLM output is constrained by `with_structured_output` + post-validation clamp. |
| V6 Cryptography | no | None. |
| V7 Error/Logging | yes | Degraded errors must not leak provider API keys (cf. Phase 8 `_safe_error_message`); reuse that sanitization posture for provider/auth errors. |

### Known Threat Patterns for {LLM scoring gate}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM output over-permissive ingest_action | Elevation of Privilege | Python ceiling-clamp (D-05) — governance is enforced deterministically, LLM can only be more conservative. |
| Prompt injection via SearchResult snippet/url | Tampering | Output constrained to `ScoredFinding` schema; no tool execution; no writes; downstream review (Phase 10) before any SOT change. |
| API key leakage in degraded error messages | Information Disclosure | Sanitize provider/auth error text (mirror `research_search._safe_error_message`); never echo raw exception with credentials. |
| Silent all-skip masking a provider outage | Repudiation / availability | D-09 gate-level degraded error; counters in retrieval block for auditability. |

## Sources

### Primary (HIGH confidence)
- In-repo code (read this session): `ask_domain.py`, `llm/config.py`, `llm/config.yaml`, `tests/llm/conftest.py`, `search/{models,registry,provider,errors,providers/mock}.py`, `pipelines/research_search.py`, `capabilities/{catalog,registry}.py`, `mcp/server.py`, `cli.py`, `storage/workspace.py`, `schemas/config.py`, `services/init.py`.
- Installed package versions via `importlib.metadata`: langchain-core 1.4.6, langchain-anthropic 1.4.5, langgraph 1.2.4, langgraph-checkpoint 4.1.1, pydantic 2.13.4.
- Context7 `/websites/langchain_oss_python` — `with_structured_output(method="json_schema")` for ChatAnthropic + ChatOpenAI (native support confirmed).
- Context7 `/langchain-ai/langgraph` — sync `invoke` respects `max_concurrency` via executor.map; async `ainvoke`/`asyncio.gather` does NOT bound concurrency.
- PyPI `langchain-openai` JSON API — latest 1.3.3, official `langchain-ai/langchain` repo.
- Direct interpreter checks: `langchain` umbrella NOT installed (init_chat_model unavailable); `Send` now from `langgraph.types` (constants import deprecated since v1.0); `GenericFakeChatModel.with_structured_output` exists but echoes messages.

### Secondary (MEDIUM confidence)
- Spec `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §6.1–6.6, §9, §10 (schemas, capability registry entries, acceptance criteria) — note §6.1 SearchResult is a *draft* superseded by implementation.
- `templates/governance.yaml` research block (relevance_threshold 0.3, card_creation_threshold 0.6, max_papers_per_cycle 50).

### Tertiary (LOW confidence)
- Default concurrency cap value (~5) — heuristic, tune to provider limits.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified in the actual venv; factory pattern mirrors shipped Phase 8 code.
- Architecture: HIGH — gate skeleton, registry, config loader all exist and were read directly.
- Concurrency/degraded handling: MEDIUM-HIGH — `max_concurrency` semantics verified from LangGraph source; exact topology is discretion.
- Pitfalls: HIGH — schema drift, async cap, and outage discrimination confirmed against code/docs.
- Live provider behavior (Anthropic json_schema on pinned model): MEDIUM (ASSUMED A1) — not offline-testable.

**Research date:** 2026-06-26
**Valid until:** 2026-07-26 (LangChain/LangGraph 1.x is fast-moving; re-verify versions if planning slips >2 weeks).
