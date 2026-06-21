# Phase 8: Search Provider Spine + Contract Foundation — Research

**Researched:** 2026-06-21  
**Domain:** Provider-agnostic search spine, workspace config, capability registry (CLI/MCP), offline contract tests  
**Confidence:** HIGH

## Summary

Phase 8 delivers the **search provider spine** — a read-only `research.search` capability exposed through the existing capability registry to CLI and MCP, backed by workspace-level `.construct/search.yaml`, a four-method `SearchProvider` abstraction, Tavily and mock adapters, granular error types, and offline contract tests. No workspace SOT writes (refs, cards, seeds, events) occur in this phase.

The implementation should mirror proven v0.3 patterns: **YAML → Pydantic → factory → handler → registry**, following `src/construct/llm/config.py` for config loading, `src/construct/capabilities/catalog.py` for capability registration with RT-03 dual-mode shims, `src/construct/services/validation.py` for workspace config validation, and `tests/llm/conftest.py` for the mock-provider fixture pattern (extended with per-query JSON mapping, latency, and error injection).

**Primary recommendation:** Build `src/construct/search/` as a self-contained package with workspace-scoped config resolution via `WorkspaceLoader`, register `research.search` in the catalog with both `cli_name="research.search"` and `mcp_tool_name="construct_research_search"`, default all CI/contract tests to the mock provider, and keep Tavily SDK imports isolated inside `providers/tavily.py` behind an optional `pyproject.toml` extra.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 1. Search Config Location
- **Decision:** Workspace-level config file (`.construct/search.yaml`)
- **Rationale:** Provider registration is a user-configurable workspace choice, not a project-internal detail. Mirrors the user-facing nature of `model-routing.yaml` but doesn't need its dual-layer complexity.
- **Alternatives rejected:** Project-level config (too opaque for users), both-levels (over-engineered for v0.4)

#### 2. Provider Interface Scope
- **Decision:** Rich interface with 4 methods: `search()`, `search_batch()`, `search_by_seed_cluster()`, `get_capabilities()`
- **Rationale:** Need seed-cluster awareness for Phase 10 integration, batch for research efficiency, capability discovery for dynamic routing.
- **Consequence:** More abstract base interface to implement per provider, but enables Phase 10 to use the spine instead of Claude-native WebSearch.

#### 3. Result Normalization
- **Decision:** Hybrid model — core normalized fields (title, url, snippet, source_tier, score) + `provider_specific: dict[str, Any]` blob
- **Rationale:** Consumers get a uniform contract for common fields; provider-specific data is preserved but optional. Favored over fully normalized (loses data) and per-provider schema (over-engineered for Phase 8).

#### 4. Mock Provider Fidelity
- **Decision:** Configurable fixture sets — per-query response mapping via JSON, with latency simulation and error injection (rate limit, network failure, auth failure)
- **Rationale:** SRCH-04 requires structured error simulation. Static canned responses (like MockChatAnthropic) don't cover degraded-state testing. The mock provider doubles as the test oracle for SRCH-03.

#### 5. MCP/CLI Surface
- **Decision:** Both CLI (`construct search`) and MCP (`construct_search`) — default capability registry auto-exposure
- **Rationale:** No reason to opt out of auto-exposure. Agents benefit from MCP access; CLI is the primary user surface. Both are free via the registry.

#### 6. search-seeds.json Relationship
- **Decision:** Support both direct query API AND `search_by_seed_cluster()` method
- **Rationale:** Direct queries for ad-hoc use; seed-driven for research cycle integration in Phase 10. The `search-seeds.json` schema already has domain, terms, weight, status — the data model is ready.

#### 7. Error Taxonomy (SRCH-04)
- **Decision:** Granular error types: NetworkError, RateLimitError, AuthError, QuotaExceededError, ParseError, ProviderUnavailableError
- **Rationale:** Each error type is independently catchable, testable, and can carry structured metadata (retry_after, provider_name, etc.). Simpler than single SearchError with category string (less discoverable).

### Scope Boundaries (In scope)
- Workspace-level config `.construct/search.yaml` with Pydantic schema + validation
- Abstract `SearchProvider` base class with 4-method interface
- Tavily provider adapter (primary real provider)
- Mock provider for offline testing (JSON fixtures)
- Provider registry / factory
- `research.search` capability in registry (CLI + MCP)
- Structured error types for all degraded states
- Workspace config validation for search config
- Search-seeds cross-validation (new method validates seed clusters against workspace)

### Not in scope (deferred)
- LLM provider factory for scoring (Phase 9)
- `research.score` capability (Phase 9)
- `research.run` workflow (Phase 10)
- Human review gate (Phase 10)
- Curation PIPE steps (Phase 11)
- Any workspace writes (refs, cards, seeds, events) — search is read-only
- Claude-native skill migration (Phase 12)
- Multi-provider automatic failover (deferred)
- Search result caching (deferred)
- Provider health-check / ping method (deferred)

### Deferred Ideas (OUT OF SCOPE)
- Provider health-check / ping method (not in requirements; defer to Phase 10 when research.run needs it)
- Multi-provider fallback chains (basic error handling in scope; automatic failover deferred)
- Search result caching (outside v0.4 scope)
- Web scraping beyond search results (defer to future milestone)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRCH-01 | User can run provider-agnostic `research.search` through CLI/MCP, returning normalized results without SOT writes | Registry handler + `SearchProvider` factory + `ResearchSearchInput`/`Output` models; CLI `research search` group; MCP auto-exposure via `construct_research_search`; handler must not call ingest/knowledge/seed write services |
| SRCH-02 | Developer can configure providers, API-key env vars, query caps, result caps without changing workflow code | `.construct/search.yaml` Pydantic schema in `schemas/config.py`; `WorkspaceLoader.load_search_config()`; factory reads `api_key_env` from env; caps block in config; init copies template |
| SRCH-03 | Developer can run full search contract test suite offline with mock provider + fixtures | `MockSearchProvider` with JSON fixture dir; `tests/search/test_search_contract.py`; no network/API key in default pytest run; update MCP contract test expected tool set |
| SRCH-04 | User receives structured degraded-state errors on provider fail/timeout/cap hit | Six granular exception classes in `search/errors.py`; mock error injection; cap enforcement returns `truncated=True` + typed errors; handler surfaces errors in `OperationResult` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Search config load/validate | API / Backend (Python) | Storage (workspace files) | Config is workspace YAML; loader validates via Pydantic at capability boundary |
| Provider factory + adapter selection | API / Backend | — | Factory reads workspace config; no invoke-surface logic |
| External search API calls (Tavily) | External service | API / Backend adapter | Tavily SDK called only inside `providers/tavily.py` |
| Result normalization (`SearchResult`) | API / Backend | — | Adapter maps provider JSON → Pydantic models before returning |
| Seed-cluster query building | API / Backend | Storage (read `search-seeds.json`) | Reads seeds read-only; no seed timestamp updates in Phase 8 |
| `research.search` handler | API / Backend | Capability registry | Single handler callable from CLI and MCP |
| CLI `construct research search` | Invoke surface (CLI) | Registry | Typer group delegates to registry handler (RT-03 shim if needed) |
| MCP `construct_research_search` | Invoke surface (MCP) | Registry | Auto-registered from `CapabilityRecord.mcp_tool_name` |
| Mock fixtures + contract tests | Test infrastructure | API / Backend | Tests exercise handler + mock provider; no browser tier |
| Cap enforcement (query/result limits) | API / Backend | — | Enforced in handler or provider wrapper before/after API call |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11` (dev: 3.14.5) | Runtime | Existing project requirement `[VERIFIED: pyproject.toml]` |
| pydantic | `>=2.7` (installed: 2.13.3) | Search models, config schemas, capability I/O | Project-wide contract language; `extra="forbid"` on all models |
| ruamel.yaml | `>=0.18` | Load `.construct/search.yaml` | Already used in `WorkspaceLoader`; round-trip not required for search config |
| typer | `>=0.12` | CLI `research search` command group | Existing CLI framework |
| mcp (FastMCP) | `>=1.0` | MCP stdio auto-exposure | Existing pattern in `mcp/server.py` |
| tavily-python | **0.7.26** (optional extra) | Real Tavily adapter | Official SDK; structured JSON; documented exceptions `[VERIFIED: pip index]` `[CITED: /tavily-ai/tavily-python]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 (dev) | Contract + unit tests | All Phase 8 verification |
| urllib.parse | stdlib | Derive `source_domain` from result URL | Every Tavily/mock normalization |
| json | stdlib | Mock fixture loading | Mock provider only |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Workspace `.construct/search.yaml` | Repo-level `src/construct/search/config.yaml` | **Rejected by user** — workspace-level is locked; prior milestone research assumed repo default |
| `tavily-python` sync client | Tavily MCP server | MCP bypasses registry; violates CLI/MCP parity `[CITED: spec-v04 §8.2]` |
| Single `search()` method | 4-method interface | **Rejected by user** — batch + seed-cluster methods required for Phase 10 |
| Optional `[search]` extra | Hard dependency on tavily | Optional keeps CI/mock-only installs lean; Tavily import guarded in adapter |

**Installation:**

```bash
# Core dev (existing)
.venv/bin/python -m pip install -e '.[dev]'

# Optional: enable real Tavily adapter locally
.venv/bin/python -m pip install -e '.[dev,search]'
```

Recommended `pyproject.toml` addition:

```toml
[project.optional-dependencies]
search = ["tavily-python>=0.7,<1"]
```

**Version verification:** `tavily-python` latest on PyPI: **0.7.26** (verified 2026-06-21 via `pip index versions`).

## Architecture Patterns

### System Architecture Diagram

```text
                    ┌─────────────────────────────────────┐
                    │  Invoke Surfaces                    │
                    │  CLI: construct research search     │
                    │  MCP: construct_research_search     │
                    └─────────────────┬───────────────────┘
                                      │ CapabilityRecord.handler
                    ┌─────────────────▼───────────────────┐
                    │  research.search handler            │
                    │  • validate ResearchSearchInput     │
                    │  • load .construct/search.yaml      │
                    │  • enforce caps                     │
                    │  • NO SOT writes                    │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────▼────────────────────────┐
              │  SearchProviderFactory                         │
              │  config.default_provider → tavily | mock         │
              └───────────────┬────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
  │ MockProvider│    │TavilyProvider│    │ get_capabilities │
  │ JSON fixtures│   │ tavily-python│    │ (capability meta) │
  │ error inject │   │ SDK only here│    └──────────────────┘
  └──────┬──────┘    └──────┬───────┘
         │                  │
         └────────┬─────────┘
                  ▼
         ┌────────────────────┐
         │ SearchBatchOutput  │
         │ list[SearchResult] │
         │ truncated, errors  │
         └─────────┬──────────┘
                   ▼
         ┌────────────────────┐
         │ OperationResult    │
         │ success + data JSON│
         └────────────────────┘

External: Tavily API ←── TavilyProvider only
Read-only: search-seeds.json (for search_by_seed_cluster)
Read-only: domains.yaml (cross-validation only)
```

### Recommended Project Structure

```text
src/construct/search/
├── __init__.py
├── config.py           # load_search_config(workspace), merge caps
├── errors.py           # NetworkError, RateLimitError, AuthError, ...
├── models.py           # SearchResult, SearchBatchOutput, ProviderCapabilities
├── provider.py         # ABC SearchProvider (4 methods)
├── registry.py         # SearchProviderFactory
└── providers/
    ├── __init__.py
    ├── tavily.py       # ONLY file importing tavily
    └── mock.py         # fixture-driven mock

src/construct/schemas/config.py   # SearchProviderName, SearchConfig (workspace schema)
src/construct/pipelines/research_search.py  # OR handler inline in catalog — research.search handler
CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml

tests/
├── search/
│   ├── conftest.py
│   ├── test_search_contract.py      # SRCH-01/03/04
│   ├── test_search_config.py        # SRCH-02
│   └── test_search_provider_mock.py
└── fixtures/search/
    ├── tavily_basic.json
    ├── mock_happy_path.json
    └── mock_rate_limit.json
```

**Note:** CONTEXT lists `cli_name` intent as `construct search`; spec §9.1 proposes `construct research search` with capability id `research.search`. Follow spec CLI nesting (`research` Typer subgroup → `search` command) while keeping capability id `research.search`.

### Pattern 1: Workspace Config Loading (mirror model-routing)

**What:** Add `SearchConfig` to `schemas/config.py`; load via `WorkspaceLoader.load_search_config()` reading `.construct/search.yaml`.

**When to use:** Every `research.search` invocation that needs provider selection.

**Example:**

```python
# Pattern from src/construct/storage/workspace.py — load_model_routing()
def load_search_config(self) -> SearchConfig:
    try:
        return SearchConfig.model_validate(
            self.read_yaml(".construct/search.yaml")
        )
    except ValidationError as exc:
        raise WorkspaceLoadError(f"invalid .construct/search.yaml: {exc}") from exc
```

### Pattern 2: Capability Registration with RT-03 Shim

**What:** Register `research.search` in `catalog.py` with input/output Pydantic models; use shim if CLI passes positional args and MCP passes kwargs.

**When to use:** All registry capabilities (established Phase 7 pattern).

**Example:**

```python
registry.register(CapabilityRecord(
    id="research.search",
    name="Research Search",
    description="Provider-agnostic web search returning normalized results (read-only)",
    input_model=ResearchSearchInput,
    output_model=OperationResult,  # data holds ResearchSearchOutput
    handler=_research_search_shim,
    cli_name="research.search",
    mcp_tool_name="construct_research_search",
))
```

### Pattern 3: Mock Provider with Fixture Map + Error Injection

**What:** Extend `MockChatAnthropic` pattern — JSON files keyed by query string (or regex), optional `sleep_ms`, optional `error_type`.

**When to use:** All contract tests; default provider in test workspaces.

**Example fixture entry:**

```json
{
  "query": "quantum gravity",
  "latency_ms": 50,
  "response": {
    "results": [
      {
        "title": "Fixture Paper",
        "url": "https://example.org/paper",
        "snippet": "Abstract excerpt.",
        "score": 0.91,
        "source_tier": 2
      }
    ]
  }
}
```

```json
{
  "query": "__error_rate_limit__",
  "error": {
    "type": "RateLimitError",
    "retry_after_seconds": 30
  }
}
```

### Pattern 4: Tavily Exception Mapping

**What:** Map Tavily SDK exceptions to CONSTRUCT error types at adapter boundary.

**When to use:** Inside `providers/tavily.py` only.

**Example:**

```python
# Source: [CITED: /tavily-ai/tavily-python — error handling docs]
from tavily import (
    TavilyClient,
    InvalidAPIKeyError,
    UsageLimitExceededError,
    TimeoutError as TavilyTimeoutError,
)

try:
    response = client.search(query, max_results=max_results, timeout=timeout)
except InvalidAPIKeyError as exc:
    raise AuthError(provider_name="tavily", message=str(exc)) from exc
except UsageLimitExceededError as exc:
    raise RateLimitError(provider_name="tavily", retry_after_seconds=getattr(exc, "retry_after_seconds", None)) from exc
except TavilyTimeoutError as exc:
    raise NetworkError(provider_name="tavily", message="timeout") from exc
```

### Anti-Patterns to Avoid

- **Tavily import outside adapter:** Any `from tavily import ...` outside `providers/tavily.py` breaks mock-only CI.
- **Native keys in handler output:** Returning Tavily `content` instead of normalized `snippet` violates SRCH-01 contract.
- **Writing search-seeds `last_queried`:** Deferred to Phase 10; Phase 8 is read-only.
- **Project-level search config:** User locked workspace-level `.construct/search.yaml` only.
- **MCP-only or CLI-only exposure:** Both surfaces required via registry auto-exposure.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client for Tavily | Raw `httpx` calls | `tavily-python` SDK | Auth, response shape, timeouts, documented exceptions |
| YAML parsing | Custom parser | `ruamel.yaml` via `WorkspaceLoader.read_yaml` | Consistent with workspace config stack |
| MCP tool registration | Manual tool list in server.py | `registry.list_mcp_tools()` loop | Existing auto-exposure in `mcp/server.py` |
| CLI JSON output | Ad-hoc print | `_display_result(result, json_output)` | Established CLI pattern |
| Search result schema validation | Dict checks | Pydantic v2 models with `extra="forbid"` | Matches capability registry contract |
| Retry/backoff | Custom loop (Phase 8) | Raise typed errors; defer tenacity to Phase 10 if needed | SRCH-04 wants structured errors, not silent retry |

**Key insight:** The search spine is a **provider adapter + normalization boundary**. Hand-rolling HTTP, retry, or MCP wiring duplicates proven project infrastructure and breaks the v0.3 registry spine.

## Common Pitfalls

### Pitfall 1: Provider Abstraction Leak

**What goes wrong:** Handler or future pipeline imports Tavily directly; tests monkeypatch Tavily instead of `SearchProvider`.

**Why it happens:** Fastest path wires SDK in handler.

**How to avoid:** Factory returns protocol/ABC; only `providers/tavily.py` imports SDK; contract tests use mock provider exclusively.

**Warning signs:** `grep -r "from tavily" src/construct/` returns more than one file.

### Pitfall 2: Config Ownership Confusion

**What goes wrong:** Search caps duplicated in `governance.yaml` and `search.yaml`; API keys committed to workspace files.

**Why it happens:** Overlapping v0.3 config files.

**How to avoid:** `search.yaml` owns provider selection, `api_key_env`, query/result caps; `governance.yaml` owns relevance/card thresholds (Phase 9+). Secrets only via env var names.

**Warning signs:** `api_key:` literal in committed YAML; missing env preflight errors.

### Pitfall 3: SearchResult Schema Drift from Locked Decision

**What goes wrong:** Implementing spec §6.1 `provider_score` only, omitting locked `source_tier` + `score` + `provider_specific`.

**Why it happens:** Spec-v04 predates discuss-phase decisions.

**How to avoid:** Use CONTEXT locked fields; map Tavily `score` → `score`; set default `source_tier` from domain `source_priorities` heuristics or config default; stash extra Tavily fields in `provider_specific`.

**Warning signs:** Contract tests assert fields not in locked model or vice versa.

### Pitfall 4: MCP Contract Test Staleness

**What goes wrong:** Adding `construct_research_search` without updating `tests/contract/test_mcp_contracts.py` expected tool set.

**Why it happens:** Static `expected` set in test file.

**How to avoid:** Update `test_mcp_tool_count` and `_payload_for` when registering new MCP tool; add handler-invocation test per RT-03 pattern.

**Warning signs:** CI passes schema tests but MCP tool missing from expected set.

### Pitfall 5: Accidental SOT Writes

**What goes wrong:** Handler logs `research_search_complete` to `events.jsonl` or updates seed timestamps.

**Why it happens:** Spec §6.6 lists future event types; easy to implement early.

**How to avoid:** Phase 8 handler returns `OperationResult` only; no calls to knowledge/ingestion/init write helpers; explicit code review gate.

**Warning signs:** Handler imports `validate_event_write` or `ingest_source`.

### Pitfall 6: Optional Tavily Not Guarded

**What goes wrong:** ImportError when `tavily-python` not installed and workspace config selects `tavily`.

**Why it happens:** Hard import at module level in factory.

**How to avoid:** Lazy import in Tavily adapter; factory raises `ProviderUnavailableError` with install hint if extra missing.

**Warning signs:** `pytest` collection fails without `[search]` extra even when tests use mock.

## Code Examples

### Tavily search call (verified SDK)

```python
# Source: [CITED: /tavily-ai/tavily-python — TavilyClient.search]
from tavily import TavilyClient

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
response = client.search(
    query="latest quantum gravity results",
    search_depth="basic",
    max_results=5,
    include_raw_content="markdown",
    timeout=30,
)
for item in response["results"]:
    # item: title, url, content, score, optional raw_content, published_date
    ...
```

### Recommended SearchConfig template (workspace)

```yaml
# CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml
version: 1
default_provider: mock

providers:
  mock:
    type: mock
    fixture_dir: tests/fixtures/search
  tavily:
    type: tavily
    api_key_env: TAVILY_API_KEY
    search_depth: basic
    topic: general
    max_results: 5
    include_raw_content: markdown
    timeout_seconds: 30
    include_answer: false

caps:
  max_queries_per_request: 1
  max_results_per_query: 5
  max_batch_queries: 8
  max_raw_content_chars: 20000
  degraded_on_provider_error: true
```

### SearchProvider ABC (locked 4-method interface)

```python
from abc import ABC, abstractmethod

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, *, max_results: int, cluster_id: str | None = None, ...) -> SearchBatchOutput: ...

    @abstractmethod
    def search_batch(self, queries: list[str], *, max_results: int, ...) -> list[SearchBatchOutput]: ...

    @abstractmethod
    def search_by_seed_cluster(self, cluster_id: str, workspace: Path, ...) -> SearchBatchOutput: ...

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities: ...
```

### Error hierarchy (SRCH-04)

```python
class SearchError(Exception):
    provider_name: str
    message: str

class NetworkError(SearchError): ...
class RateLimitError(SearchError):
    retry_after_seconds: float | None = None
class AuthError(SearchError): ...
class QuotaExceededError(SearchError): ...
class ParseError(SearchError): ...
class ProviderUnavailableError(SearchError): ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude `WebSearch` in skills | Python `SearchProvider` + registry capability | v0.4 Phase 8 | Testable, model/agent-agnostic search |
| No search config file | `.construct/search.yaml` per workspace | Phase 8 (locked) | User-visible provider choice |
| Spec `provider_score` field | Locked `score` + `source_tier` + `provider_specific` | Discuss-phase 2026-06-21 | Planner must follow CONTEXT over spec §6.1 |
| Spec repo-level `search/config.yaml` | Workspace-only config | Discuss-phase 2026-06-21 | Loader uses `WorkspaceLoader`, not project default |
| Placeholder research in skills | `research.search` capability (Phase 8); full run Phase 10 | v0.4 roadmap | Incremental delivery |

**Deprecated/outdated:**
- Phase 4 decision preserving WebSearch in skills — superseded by v0.4 spec §8.1 for workflow migration (skill change deferred to Phase 12, but spine lands Phase 8).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MCP tool name is `construct_research_search` (spec §9.1), not `construct_search` (CONTEXT shorthand) | MCP/CLI Surface | Wrong tool name in tests/docs |
| A2 | CLI command path is `construct research search` (Typer subgroup), not top-level `construct search` | MCP/CLI Surface | CLI UX mismatch |
| A3 | `source_tier` on `SearchResult` is a search-time heuristic/default, not the L3 governance tier from Phase 9 | Result Normalization | Duplicate/conflicting tier semantics |
| A4 | `.construct/search.yaml` is copied at init but not added to `REQUIRED_PATHS` until a follow-up — validation warns if missing when search invoked | Config | Init/validate behavior ambiguity |
| A5 | Phase 8 does not emit `research_search_complete` events (deferred with other writes) | Scope | Accidental scope creep |

## Open Questions

1. **Default provider for newly initialized workspaces: `mock` or `tavily`?**
   - What we know: Template should enable offline dev; real research needs Tavily + env key.
   - What's unclear: Whether init defaults to mock with commented Tavily block vs active Tavily stub.
   - Recommendation: Default `mock` in template; document switching to `tavily` in USER_GUIDE; validation passes either if schema valid.

2. **Should `search_by_seed_cluster` reject reserved clusters (`manual-ingest`, `web-ingest`)?**
   - What we know: Reserved clusters exist for ingest validation; help.py excludes them from staleness.
   - What's unclear: Whether research search should block querying them.
   - Recommendation: Allow read/search but document they are not research targets; optional warning in output metadata.

3. **Reconcile CONTEXT MCP name `construct_search` vs spec `construct_research_search`**
   - What we know: Spec §9.1 and MCP naming convention use capability prefix.
   - Recommendation: Use `construct_research_search` per spec; flag A1 for user confirmation if CONTEXT shorthand was intentional.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All implementation | ✓ | 3.14.5 | — |
| pytest | Contract tests | ✓ | 9.0.3 | — |
| pydantic, ruamel.yaml, typer, mcp | Core stack | ✓ | per `.venv` | — |
| tavily-python | Tavily adapter | ✗ | — | Mock provider; optional `[search]` extra |
| TAVILY_API_KEY | Live Tavily searches | ✗ (not set) | — | Mock provider for dev/CI |
| Node.js | Phase 8 | ✗ not required | 26.3.0 installed | N/A |

**Missing dependencies with no fallback:**
- None for Phase 8 delivery — mock provider satisfies SRCH-01–04 without Tavily.

**Missing dependencies with fallback:**
- `tavily-python` / API key — use mock provider; optional integration test marked `@pytest.mark.network` if added later.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/search/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | `research.search` returns normalized results via registry; no SOT mutation | contract | `.venv/bin/python -m pytest tests/search/test_search_contract.py::test_research_search_normalized -x` | ❌ Wave 0 |
| SRCH-01 | CLI invokes capability successfully | integration | `.venv/bin/python -m pytest tests/search/test_search_contract.py::test_cli_research_search -x` | ❌ Wave 0 |
| SRCH-01 | MCP handler accepts schema kwargs without TypeError | contract | `.venv/bin/python -m pytest tests/contract/test_mcp_contracts.py -k research_search -x` | ❌ Wave 0 |
| SRCH-02 | Invalid search.yaml rejected at validation | unit | `.venv/bin/python -m pytest tests/search/test_search_config.py -x` | ❌ Wave 0 |
| SRCH-02 | Caps enforced (`truncated=True`) | unit | `.venv/bin/python -m pytest tests/search/test_search_provider_mock.py::test_result_cap -x` | ❌ Wave 0 |
| SRCH-03 | Full contract suite offline with mock | contract | `.venv/bin/python -m pytest tests/search/ -x` | ❌ Wave 0 |
| SRCH-04 | Each error type raised and surfaced structurally | unit | `.venv/bin/python -m pytest tests/search/test_search_provider_mock.py::test_error_injection -x` | ❌ Wave 0 |
| API-05 | Existing 228 tests still pass | regression | `.venv/bin/python -m pytest -x` | ✅ baseline |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/search/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/contract/ tests/search/ -x`
- **Phase gate:** Full suite green (228+ tests) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/search/conftest.py` — workspace + mock config fixtures
- [ ] `tests/search/test_search_contract.py` — SRCH-01/03 registry + CLI coverage
- [ ] `tests/search/test_search_config.py` — SRCH-02 schema + validation
- [ ] `tests/search/test_search_provider_mock.py` — SRCH-03/04 mock oracle
- [ ] `tests/fixtures/search/*.json` — Tavily sample + mock happy/error paths
- [ ] Update `tests/contract/test_mcp_contracts.py` — add `construct_research_search` to expected set + handler invocation payload
- [ ] Optional: `pyproject.toml` `[project.optional-dependencies] search` + dev install note

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local CLI/MCP, no user auth |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Local-first single user |
| V5 Input Validation | yes | Pydantic input models on capability boundary; URL/string length limits on results |
| V6 Cryptography | partial | API keys from env only; never persist secrets in workspace YAML |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in committed YAML | Information disclosure | `api_key_env` name only; validate no literal secrets in `validate_search_config()` |
| Unvalidated external URLs in results | Spoofing / phishing in downstream ingest | Normalize URLs; pass through Phase 9 scoring; Phase 8 returns data only |
| Provider response injection | Tampering | Parse via Pydantic; map to strict models; `provider_specific` optional blob |
| Query string log leakage | Information disclosure | Do not log full API keys; redact env values in error messages |

## Project Constraints (from AGENTS.md / workspace rules)

- **Claude-native track active:** Python is deterministic Layer 2; skills orchestrate but Phase 8 implements Python capability directly.
- **No archive/v01-python/ changes** unless explicitly requested.
- **No active GSD `.planning/` recreation beyond current v0.4 work.**
- **Use `.venv/bin/python -m pytest`** from repo root for all tests.
- **Capability registry is single contract** behind CLI + MCP — no bypass for new search capability.
- **Epistemic governance:** Phase 8 returns search results only; no card/ref/seed/event writes.
- **Context7 rule:** Library docs fetched for Tavily SDK (completed).

## Sources

### Primary (HIGH confidence)

- `/tavily-ai/tavily-python` (Context7) — `TavilyClient.search` parameters, response fields, exception types
- `src/construct/llm/config.py` — YAML → Pydantic config loader pattern
- `src/construct/capabilities/catalog.py` — CapabilityRecord registration + RT-03 shims
- `src/construct/mcp/server.py` — MCP auto-exposure from registry
- `src/construct/services/validation.py` — workspace validation pattern
- `src/construct/storage/workspace.py` — WorkspaceLoader pattern
- `.planning/phases/08-search-provider-spine-contract-foundation/08-CONTEXT.md` — locked decisions
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` §6.1–6.2, §8, §9.1 — baseline contracts (subordinate to CONTEXT where they conflict)

### Secondary (MEDIUM confidence)

- `.planning/research/STACK.md` — stack/version recommendations (workspace config location adjusted to locked decision)
- `.planning/research/PITFALLS.md` — provider leak and config ambiguity pitfalls
- `.planning/research/ARCHITECTURE.md` — module layout and data flow

### Tertiary (LOW confidence)

- None requiring validation — Tavily exception field names (`retry_after_seconds`) verified in SDK docs snippet but should be confirmed at implementation time against installed 0.7.26.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — Tavily version verified on PyPI; existing project patterns directly observed in codebase
- Architecture: **HIGH** — CONTEXT + catalog/MCP patterns are explicit; file layout confirmed by discuss-phase
- Pitfalls: **HIGH** — documented in project research and spec; provider leak is recurring v0.4 risk

**Research date:** 2026-06-21  
**Valid until:** 2026-07-21 (Tavily SDK stable; revisit if tavily-python 0.8+ releases)

## RESEARCH COMPLETE

**Phase:** 8 - Search Provider Spine + Contract Foundation  
**Confidence:** HIGH

### Key Findings

- Locked decision: **workspace-only** `.construct/search.yaml` (not repo-level config); loader extends `WorkspaceLoader` like `model-routing.yaml`.
- Implement **4-method `SearchProvider`** with mock fixture oracle (latency + error injection) before any Tavily wiring; keep Tavily import isolated in one adapter file behind optional `[search]` extra.
- Register **`research.search`** via existing capability registry with RT-03 shim; MCP tool **`construct_research_search`**; CLI subgroup **`construct research search`**.
- **SearchResult** must follow CONTEXT fields (`score`, `source_tier`, `provider_specific`) — not raw spec §6.1 `provider_score`-only shape.
- Phase 8 is **strictly read-only** — no events, seed updates, refs, or cards; update MCP contract tests when adding the new tool.

### File Created

`.planning/phases/08-search-provider-spine-contract-foundation/08-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | PyPI + Context7 verified Tavily; project deps unchanged except optional extra |
| Architecture | HIGH | Mirrors existing llm/config + catalog + MCP patterns with explicit CONTEXT locks |
| Pitfalls | HIGH | Cross-checked spec, PITFALLS.md, and codebase RT-03/MCP test patterns |

### Open Questions

- Default template provider: mock vs tavily (recommend mock).
- MCP tool naming: `construct_research_search` vs CONTEXT shorthand `construct_search` (recommend spec name).

### Ready for Planning

Research complete. Planner can now create PLAN.md files.
