# Phase 9: LLM Provider Factory + research.score - Pattern Map

**Mapped:** 2026-06-26
**Files analyzed:** 10 (2 NEW, 6 MODIFY, 1 TEST-MODIFY, 1 TEST-NEW group)
**Analogs found:** 10 / 10 (every target has a shipped in-repo analog)

> Key insight (from RESEARCH.md, confirmed by reading the analogs): this phase is **assembly, not invention**. The factory mirrors `SearchProviderFactory`, the gate templates `ask_domain.py`, registration mirrors the `ask.domain` record, the CLI mirrors `research_search_cmd`, and the mock extends `MockChatAnthropic`. The only genuinely new concern is the bounded fan-out + degraded/total-outage discrimination (D-04/D-08/D-09), which has no exact analog.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/llm/factory.py` | factory/provider | request-response (construct→return) | `src/construct/search/registry.py` `SearchProviderFactory` | role+flow exact |
| `src/construct/llm/research_score.py` | service / L3 gate | batch + transform (fan-out scoring) | `src/construct/llm/ask_domain.py` | role exact, flow partial (fan-out is new) |
| `src/construct/llm/ask_domain.py` | service / L2 gate | request-response | itself (retrofit; 1-line provider swap) | self |
| `src/construct/llm/config.yaml` | config | n/a | itself (add provider+gate block) | self |
| `src/construct/llm/config.py` | config loader | n/a | itself (`GateConfig` field add) | self |
| `src/construct/capabilities/catalog.py` | registry/registration | n/a | `ask.domain` record (catalog.py:324) + `_research_search_shim` (catalog.py:376) | exact |
| `src/construct/cli.py` | controller/CLI | request-response | `research_search_cmd` (cli.py:408) + `ask domain` (cli.py:335) | exact |
| `src/construct/mcp/server.py` | controller/MCP | request-response | itself (auto-discovery — verify, likely no change) | self |
| `pyproject.toml` | config/build | n/a | `search = ["tavily-python..."]` extra (line 24) | exact |
| `tests/llm/conftest.py` | test fixtures | n/a | `MockChatAnthropic` (conftest.py:25) | exact |
| `tests/llm/test_factory.py` + `test_research_score.py` | test | n/a | `tests/llm/test_ask_domain.py` `patched_llm` fixture | role exact |

---

## Pattern Assignments

### `src/construct/llm/factory.py` (NEW — factory, request-response)

**Analog:** `src/construct/search/registry.py` `SearchProviderFactory` (lines 77-116) — the structural template. **Config types analog:** `src/construct/llm/config.py` `ProviderConfig` (lines 12-20).

**Type→class map + lazy optional import** — mirror `SearchProviderFactory.create`'s branch-on-type with the tavily lazy import (registry.py:101-109). The new factory keys off `ProviderConfig.type` (the string values already in `config.yaml`: `langchain_anthropic`, `langchain_openai`, `langchain_ollama`):

```python
# Analog branch shape from search/registry.py:101-109 (lazy import inside the branch):
elif config.default_provider == SearchProviderName.tavily:
    ...
    from construct.search.providers.tavily import TavilySearchProvider   # optional dep, lazy
    provider = TavilySearchProvider(provider_config, provider_name=provider_key)
else:
    raise ProviderUnavailableError(... message=f"unknown provider type: {config.default_provider}")
```

**Target shape** (from RESEARCH.md Pattern 1; ctor kwargs match how `ask_domain.py:228-232` builds `ChatAnthropic`):
```python
from construct.llm.config import ProviderConfig

def build_chat_model(cfg: ProviderConfig, *, temperature: float = 0.2):
    if cfg.type == "langchain_anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=cfg.model, temperature=temperature, max_tokens=cfg.max_tokens)
    if cfg.type == "langchain_openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "GATE_PROVIDER_ERROR: provider 'langchain_openai' requires the optional "
                "'llm-openai' extra. Install: pip install 'construct[llm-openai]'"
            ) from exc
        return ChatOpenAI(model=cfg.model, temperature=temperature, max_tokens=cfg.max_tokens)
    raise RuntimeError(f"GATE_PROVIDER_ERROR: unknown provider type '{cfg.type}'")
```

**Error-message convention to copy:** `GATE_PROVIDER_ERROR:` prefix is the established string for provider-config failures (see `config.py:74` `FileNotFoundError("GATE_PROVIDER_ERROR: LLM config not found...")`). Reuse it for unknown/missing-provider and lazy-import errors so tests can assert on it.

**Delta vs analog:** `SearchProviderFactory` returns a wrapped (`_CappedSearchProvider`) instance and validates `isinstance(provider_config, ...)`; the LLM factory has no cap wrapper and no per-type config subclass — it branches purely on the `cfg.type` string. `ollama` is present in `config.yaml` but OUT OF SCOPE (D-02) — fall through to the unknown-provider error (or leave a stub branch; discretion).

---

### `src/construct/llm/research_score.py` (NEW — L3 gate, batch/transform)

**Analog:** `src/construct/llm/ask_domain.py` (entire file; the gate skeleton). Reuse five structural pieces verbatim-in-shape:

**1. Models defined IN the gate module** (ask_domain.py:46-107) — avoids circular import with `catalog.py`. Define `ScoredFinding`, `ResearchScoreGateOutput`, `ResearchScoreInput`, and reuse the `GateMetadata` pattern:
```python
# ask_domain.py:87-97 — copy this metadata shape, set tier="L3"
class GateMetadata(BaseModel):
    model_config = {"extra": "forbid"}
    gate_id: str
    tier: str = "L2"          # → "L3" for research.score
    review_required: bool = True
    review_status: str = "pending"
    provider: str = ""
    model: str = ""
```
Input model uses the `extra="forbid"` + `Field` range-validation idiom (ask_domain.py:66-74). `ScoredFinding` must validate: `relevance_score` 0-1, `source_tier` 1-5, `key_findings` max 5, `ingest_action` Literal["skip","ref_only","ref_and_card"].

**2. Structured-output call** (ask_domain.py:228-254) — the exact pattern to replicate per-result, BUT swap the hardcoded `ChatAnthropic(...)` for `factory.build_chat_model(...)`:
```python
# ask_domain.py:233 — KEEP method="json_schema" (no tool-choice conflicts)
structured_llm = llm.with_structured_output(ScoredFinding, method="json_schema")
result = structured_llm.invoke(messages)   # -> validated Pydantic
```
The `try/except Exception` around `.invoke()` (ask_domain.py:248-262) is the per-item isolation seed — D-08 extends it to retry-once-then-skip.

**3. Graph builder + `run_gate()` runner** (ask_domain.py:306-326, 346-423) — copy the structure: `load_llm_config(config_path)` → resolve `gate_cfg = config.gates.get(gate_id)` → `provider_key` → `provider_cfg = config.providers.get(...)` (ask_domain.py:371-374), build graph, invoke, assemble `ResearchScoreGateOutput` (mirror the `AskDomainOutput(...)` assembly at ask_domain.py:403-418 with `gate=GateMetadata(...)` + `retrieval={...}` counts).

**4. retrieval-counts block** (ask_domain.py:413-416) — extend with degraded counters: `{"results_total": N, "scored_ok": k, "retried": r, "errors": e, "degraded": bool, "relevance_threshold": .., "card_creation_threshold": .., "max_papers_per_cycle": ..}` (D-06 threshold echo lives here).

**5. Exact-match cache** (ask_domain.py:331-340) — **OMIT.** Score-gate caching is explicitly out of scope (CONTEXT.md Deferred). Do not copy the `_CACHE` block.

**Delta vs analog (the genuinely new code — no analog):**
- **Bounded fan-out (D-04):** No existing gate fans out. Use `ThreadPoolExecutor(max_workers=cap)` (RESEARCH.md Pattern 3) or LangGraph `Send` from `langgraph.types` (NOT `langgraph.constants` — deprecated). Sync path only: async `ainvoke`/`gather` does NOT honor `max_concurrency`.
- **Governance load (D-05/06):** `WorkspaceLoader(workspace_path).load_governance().research.{relevance_threshold, card_creation_threshold, max_papers_per_cycle}` (workspace.py:107, config.py:184-189).
- **Taxonomy soft-steering (D-11/12):** `WorkspaceLoader(workspace_path).load_domains_registry().domains` → each `DomainRegistryEntry.content_categories` (config.py:61-68) into the prompt.
- **Python ceiling-clamp (D-05):** deterministic post-LLM step (RESEARCH.md "Python ceiling-clamp" example).
- **Total-outage promotion (D-09):** track `failures vs len(results)`; all-failed-with-provider-cause → gate-level `OperationResult(success=False)`, not all-skip success.

---

### `src/construct/llm/ask_domain.py` (MODIFY — retrofit, D-01)

**The single behavioral change:** replace the hardcoded constructor at **lines 228-232** with a factory call:
```python
# CURRENT (ask_domain.py:228-232):
llm = ChatAnthropic(
    model=state.get("model", "claude-sonnet-4-20250514"),
    temperature=0.2,
    max_tokens=4096,
)
# AFTER: resolve ProviderConfig from llm/config and call factory.build_chat_model(provider_cfg, temperature=...)
```
The `provider_cfg` is already resolved in `run_gate()` (ask_domain.py:374) but not currently threaded into state. Plan must pass provider/model config into the `llm_synthesize` node (e.g. via state or a closure) so the factory gets the right `ProviderConfig`.

**Regression trap (CONTEXT/RESEARCH D-01):** existing tests monkeypatch `construct.llm.ask_domain.ChatAnthropic` (test_ask_domain.py:58 `monkeypatch.setattr("construct.llm.ask_domain.ChatAnthropic", ...)`). After the retrofit that symbol is no longer the construction site. **Planner must** either (a) repoint the monkeypatch to `construct.llm.factory.build_chat_model`, or (b) keep `ChatAnthropic` importable in `ask_domain` and route through it for back-compat. Recommended: patch `build_chat_model` in the new conftest fixture so both gates share one mock seam. Baseline 253 tests must stay green.

---

### `src/construct/llm/config.yaml` (MODIFY)

**Analog:** itself. OpenAI provider block **already present** (lines 10-14) — no add needed. Add only the gate entry, mirroring the `ask.domain` block (lines 22-25):
```yaml
gates:
  ask.domain:
    provider: anthropic
    temperature: 0.2
    review_required: true
  research.score:            # ADD
    provider: anthropic
    temperature: 0.2
    review_required: true
    concurrency_cap: 5       # D-04 (if cap lives in GateConfig)
```

### `src/construct/llm/config.py` (MODIFY, maybe)

**Analog:** `GateConfig` (lines 22-27). To home the D-04 cap, add one field:
```python
class GateConfig(BaseModel):
    model_config = {"extra": "forbid"}
    provider: str = "anthropic"
    temperature: float = 0.2
    review_required: bool = True
    concurrency_cap: int = 5     # ADD (D-04; default ~5, LOW-confidence — tune to rate limits)
```
Note `model_config = {"extra": "forbid"}` (config.py:24): adding `concurrency_cap:` to `config.yaml` WITHOUT this field will raise a validation error. The two edits are coupled. The default gate dict (config.py:38-40) also `"research.score": GateConfig()` may be added for resilience when the YAML is absent.

---

### `src/construct/capabilities/catalog.py` (MODIFY — registration)

**Analog A — the record:** `ask.domain` `CapabilityRecord` (catalog.py:324-339). The handler wraps `run_gate(...)` output into `OperationResult` with `data=result.model_dump(mode="json")`:
```python
# catalog.py:330-336 — the wrap-into-OperationResult idiom to copy:
handler=lambda **kwargs: (
    lambda result: OperationResult(
        success=result.answer is not None,
        message=result.answer or "No answer could be generated...",
        data=result.model_dump(mode="json"),
    )
)(ask_domain_gate("ask.domain", AskDomainInput(**kwargs))),
cli_name="ask.domain",
mcp_tool_name="construct_ask_domain",
```

**Analog B — the shim** (preferred over the inline lambda for the degraded/total-outage logic): `_research_search_shim` (catalog.py:376-380) — a module-level `def` adapter. Write `_research_score_shim(*args, **kwargs)` that calls `run_gate("research.score", ResearchScoreInput(**kwargs))` and maps to `OperationResult(success=not gate_error, data=output.model_dump(mode="json"))`. D-09: total-outage → `success=False`.

**Imports to add** (mirror catalog.py:29-40 block style):
```python
# ── Research Score imports (Phase 9) ──
from construct.llm.research_score import ResearchScoreInput, ResearchScoreGateOutput, run_gate as research_score_gate
```

**Registration call** (mirror catalog.py:353-362):
```python
registry.register(CapabilityRecord(
    id="research.score",
    name="Research Score",
    description="Score normalized search results into governance-aware finding proposals (read-only, no writes)",
    input_model=ResearchScoreInput,
    output_model=OperationResult,        # matches research.search & ask.domain wrapping
    handler=_research_score_shim,
    cli_name="research.score",
    mcp_tool_name="construct_research_score",
))
```
**Constraint:** `CapabilityRegistry.register` raises on duplicate id (registry.py:32-33). Output is `OperationResult` (dataclass, services/knowledge.py:67-71) carrying the structured `ResearchScoreGateOutput` in `.data` — preserves CLI/MCP parity (D-13).

---

### `src/construct/cli.py` (MODIFY — controller)

**Analog:** `research_search_cmd` (cli.py:408-446) under the existing `research_app` Typer group (cli.py:400-405) — **add the `score` subcommand to this same group.** Plus the `ask domain` retrieval-then-handler shape (cli.py:335-360).

**Pattern to copy** (cli.py:439-446): resolve capability from registry, call handler, display:
```python
try:
    cap = get_registry().get("research.score")
except KeyError:
    typer.echo("ERROR: Capability 'research.score' not found. Ensure Phase 9 is complete.")
    raise typer.Exit(code=1)
result = cap.handler(**handler_kwargs)
_display_result(result, json_output)     # --json path (cli.py:164-191)
```

**Delta vs analog (D-13 human table):** `_display_result` (cli.py:164-191) only prints `✓ {message}` for the default (non-json) path. `research.score` needs an **additional** human-readable summary table (columns: `url, score, tier, action` + trailing degraded/retried notice) BEFORE/instead of the default text branch. Build a small renderer that reads `result.data["findings"]` and prints rows, then falls through to `_display_result(result, json_output)` for the `--json` contract. No `rich.Table` import exists yet in cli.py (uses `typer.echo`) — keep it plain `typer.echo` rows or introduce a minimal table; discretion.

**Input plumbing (D-10):** add options for the pre-fetched `SearchResults` payload — `--results-file` / stdin / param — plus required `--workspace` (D-12). Flatten `batches`→`list[SearchResult]` in a CLI helper (per RESEARCH Open Question 1; planner locks the exact input model).

---

### `src/construct/mcp/server.py` (MODIFY — verify only)

**Analog:** itself. The server auto-discovers every registry tool via `registry.list_mcp_tools()` (server.py:27) and wraps `capability.handler(**kwargs)` → `_serialize_result` (server.py:13-15, `model_dump(mode="json")`). Because `research.score` is registered with `mcp_tool_name="construct_research_score"`, MCP exposure is **free** — likely NO code change. Verify parity with a registry test (RSCH-01 `test_registry_handler_cli_mcp_parity`).

---

### `pyproject.toml` (MODIFY)

**Analog:** the `search = ["tavily-python>=0.7,<1"]` optional extra (line 24) — the Phase 8 optional-dependency precedent (D-02 mirrors it). Add:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
search = ["tavily-python>=0.7,<1"]
llm-openai = ["langchain-openai>=1.2,<2"]    # ADD (D-02)
```
`>=1.2,<2` pins the 1.x line matching the installed langchain-core 1.4.x (RESEARCH Standard Stack).

---

### `tests/llm/conftest.py` (MODIFY) + new test files

**Analog:** `MockChatAnthropic` (conftest.py:25-48) + `mock_llm` fixture (conftest.py:104-107) + `patched_llm` monkeypatch fixture (test_ask_domain.py:55-59).

**The mock seam to copy** (conftest.py:38-48): `.with_structured_output(model_class, **kw)` returns self; `.invoke(messages)` returns a canned structured object:
```python
def with_structured_output(self, model_class, **kwargs):
    self._output_model = model_class
    return self
def invoke(self, messages):
    return MockSynthesisOutput(answer=..., cited_card_ids=[...], confidence="high")
```

**Deltas (Wave 0 fixtures — RESEARCH Validation Architecture):**
- (a) **Configurable structured-output mock** returning a caller-supplied `ScoredFinding`-shaped object (extend the canned-return pattern to accept the object in `__init__`).
- (b) **Invalid-output mock** — `.invoke()` raises or returns unparseable → exercises D-08 retry-then-skip.
- (c) **Total-outage mock** — `.invoke()` always raises a provider/auth error → exercises D-09 gate-level error.
- (d) **Sample `SearchResult` fixtures** matching the **Phase 8 schema** (`title, url, snippet, source_tier, score, provider_specific, source_domain` — search/models.py:10-19), NOT the spec §6.1 draft (`provider_score`/`raw_content` do not exist — Pitfall 1).
- (e) Repoint the ask.domain monkeypatch (test_ask_domain.py:58) to the factory seam (D-01).

---

## Shared Patterns

### Provider construction (factory single-path)
**Source:** new `src/construct/llm/factory.py` (mirrors `search/registry.py:77-116`).
**Apply to:** `ask_domain.py` (retrofit) AND `research_score.py`. Both gates call `build_chat_model(provider_cfg, temperature=gate_cfg.temperature)` instead of constructing `ChatAnthropic` directly. This IS the D-01 / spec-line-546 payoff: one provider path.

### Structured output via json_schema
**Source:** `ask_domain.py:233`.
**Apply to:** every LLM call in `research_score.py`.
```python
structured_llm = llm.with_structured_output(SchemaModel, method="json_schema")
```
Native on both ChatAnthropic and ChatOpenAI in installed versions — no per-provider branching.

### Result envelope (OperationResult wrapper)
**Source:** `ask.domain` handler (catalog.py:330-336), `research_search` (research_search.py:217-220).
**Apply to:** the `research.score` handler/shim.
```python
OperationResult(success=..., message=..., data=output.model_dump(mode="json"))
```
Consumed unchanged by CLI `_display_result` (cli.py:164-191) and MCP `_serialize_result` (mcp/server.py:13-15) → CLI+MCP parity for free.

### Error sanitization (no key leakage)
**Source:** `research_search._safe_error_message` (research_search.py:52-64) + `_build_search_error_result` (67-96).
**Apply to:** `research_score.py` degraded/total-outage errors (D-08/D-09, V7/ASVS). Never echo a raw provider exception that may carry credentials; map auth/config errors to a safe message and put the class name in `OperationError.reason`.

### GateMetadata
**Source:** `ask_domain.py:87-97`.
**Apply to:** `research_score.py` output — copy the model, set `tier="L3"`, populate `provider`/`model` from the resolved `ProviderConfig`.

### Models-in-gate-module (circular-import avoidance)
**Source:** `ask_domain.py:63-107` comment ("defined here to avoid circular imports with catalog.py").
**Apply to:** `ScoredFinding` / `ResearchScoreGateOutput` / `ResearchScoreInput` — define in `research_score.py`, import INTO `catalog.py` (never the reverse).

---

## No Analog Found

Files/concerns with no close in-repo match (planner uses RESEARCH.md patterns + new code):

| Concern | Role | Data Flow | Reason |
|---------|------|-----------|--------|
| Bounded fan-out scorer (in `research_score.py`) | service | batch/concurrent | No existing gate fans out; all current gates are single linear LLM calls (ask_domain is linear). Use RESEARCH Pattern 3 (`ThreadPoolExecutor(max_workers=cap)` sync, or `langgraph.types.Send`). |
| Per-item retry-then-skip + degraded flag (D-08) | service | transform | `ask_domain.py:255-262` catches once and returns a null answer; no retry, no per-item isolation across a batch, no degraded counter. New logic. |
| Total-outage promotion (D-09) | service | transform | No precedent for distinguishing all-items-failed from partial success; `research_search` degrades at the whole-call level, not per-item. New logic. |
| Python ceiling-clamp of LLM action vs governance bands (D-05) | service | transform | No existing deterministic-clamp-over-LLM-output pattern. New (RESEARCH `clamp_action` example). |
| CLI summary table (D-13) | controller | render | `_display_result` (cli.py:164-191) only does `✓ message` / JSON; no tabular renderer exists. New small renderer. |

---

## Metadata

**Analog search scope:** `src/construct/llm/`, `src/construct/search/`, `src/construct/capabilities/`, `src/construct/pipelines/`, `src/construct/storage/`, `src/construct/schemas/`, `src/construct/cli.py`, `src/construct/mcp/`, `tests/llm/`, `pyproject.toml`.
**Files scanned (read in full or targeted):** ask_domain.py, llm/config.py, llm/config.yaml, search/registry.py, search/models.py, capabilities/registry.py, capabilities/catalog.py (targeted), cli.py (targeted), mcp/server.py (grep), pipelines/research_search.py (targeted), schemas/config.py (targeted), storage/workspace.py (targeted), tests/llm/conftest.py, tests/llm/test_ask_domain.py (grep), pyproject.toml.
**Pattern extraction date:** 2026-06-26
</content>
</invoke>
