# Phase 8: Search Provider Spine + Contract Foundation — Context

> **Status:** Context gathered. Ready for planning.
> **Date:** 2026-06-21
> **Requirements:** SRCH-01, SRCH-02, SRCH-03, SRCH-04

## Decisions

### 1. Search Config Location
- **Decision:** Workspace-level config file (`.construct/search.yaml`)
- **Rationale:** Provider registration is a user-configurable workspace choice, not a project-internal detail. Mirrors the user-facing nature of `model-routing.yaml` but doesn't need its dual-layer complexity.
- **Alternatives rejected:** Project-level config (too opaque for users), both-levels (over-engineered for v0.4)

### 2. Provider Interface Scope
- **Decision:** Rich interface with 4 methods: `search()`, `search_batch()`, `search_by_seed_cluster()`, `get_capabilities()`
- **Rationale:** Need seed-cluster awareness for Phase 10 integration, batch for research efficiency, capability discovery for dynamic routing.
- **Consequence:** More abstract base interface to implement per provider, but enables Phase 10 to use the spine instead of Claude-native WebSearch.

### 3. Result Normalization
- **Decision:** Hybrid model — core normalized fields (title, url, snippet, source_tier, score) + `provider_specific: dict[str, Any]` blob
- **Rationale:** Consumers get a uniform contract for common fields; provider-specific data is preserved but optional. Favored over fully normalized (loses data) and per-provider schema (over-engineered for Phase 8).

### 4. Mock Provider Fidelity
- **Decision:** Configurable fixture sets — per-query response mapping via JSON, with latency simulation and error injection (rate limit, network failure, auth failure)
- **Rationale:** SRCH-04 requires structured error simulation. Static canned responses (like MockChatAnthropic) don't cover degraded-state testing. The mock provider doubles as the test oracle for SRCH-03.

### 5. MCP/CLI Surface
- **Decision:** Both CLI (`construct search`) and MCP (`construct_search`) — default capability registry auto-exposure
- **Rationale:** No reason to opt out of auto-exposure. Agents benefit from MCP access; CLI is the primary user surface. Both are free via the registry.

### 6. search-seeds.json Relationship
- **Decision:** Support both direct query API AND `search_by_seed_cluster()` method
- **Rationale:** Direct queries for ad-hoc use; seed-driven for research cycle integration in Phase 10. The `search-seeds.json` schema already has domain, terms, weight, status — the data model is ready.

### 7. Error Taxonomy (SRCH-04)
- **Decision:** Granular error types: NetworkError, RateLimitError, AuthError, QuotaExceededError, ParseError, ProviderUnavailableError
- **Rationale:** Each error type is independently catchable, testable, and can carry structured metadata (retry_after, provider_name, etc.). Simpler than single SearchError with category string (less discoverable).

## Scope Boundaries

### In scope (Phase 8)
- Workspace-level config `.construct/search.yaml` with Pydantic schema + validation
- Abstract `SearchProvider` base class with 4-method interface
- Tavily provider adapter (primary)
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

## Integration Points

### Files to create:
- `src/construct/search/` — New search module package
- `src/construct/search/__init__.py`
- `src/construct/search/config.py` — Pydantic schemas for search provider config
- `src/construct/search/errors.py` — Granular error types
- `src/construct/search/provider.py` — Abstract SearchProvider base class
- `src/construct/search/providers/__init__.py`
- `src/construct/search/providers/tavily.py` — Tavily adapter
- `src/construct/search/providers/mock.py` — Mock provider with fixture support
- `src/construct/search/registry.py` — Provider registry
- `tests/search/conftest.py` — Mock search test fixtures
- `tests/search/test_search_contract.py` — SRCH-03 contract tests
- `CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml` — Config template

### Files to modify:
- `src/construct/schemas/config.py` — Add `SearchProviderName` enum, `SearchConfig` schema
- `src/construct/services/validation.py` — Add `validate_search_config()`
- `src/construct/capabilities/catalog.py` — Register `research.search` capability
- `src/construct/cli.py` — Add `search` Typer command group
- `src/construct/storage/workspace.py` — Add `load_search_config()` to WorkspaceLoader
- `src/construct/services/init.py` — Copy search config template on workspace init
- `pyproject.toml` — Add Tavily SDK as optional dependency

## Code Context

### Patterns to follow:
- **Provider abstraction:** `src/construct/llm/config.py` LLM provider pattern (YAML config → Pydantic → factory → runtime)
- **Capability registration:** `src/construct/capabilities/catalog.py` capability record pattern with input/output models + handler
- **Mock pattern:** `tests/llm/conftest.py` MockChatAnthropic pattern, extended for configurable fixtures
- **Config validation:** `src/construct/services/validation.py` workspace config validation pattern
- **CLI command:** `src/construct/cli.py` Typer command group pattern with error handling
- **MCP auto-exposure:** `src/construct/mcp/server.py` auto-discovers from capability registry

### Key reference files:
- `src/construct/llm/config.py` — Closest existing provider pattern
- `src/construct/capabilities/registry.py` — Capability registry singleton
- `src/construct/capabilities/catalog.py` — Capability catalog with handler definitions
- `src/construct/schemas/config.py` — Existing workspace config schemas (add search config here)
- `src/construct/cli.py` — CLI command definitions
- `src/construct/services/validation.py` — Validation service
- `src/construct/storage/workspace.py` — Workspace file loader
- `tests/llm/conftest.py` — Mock provider pattern

## Deferred Ideas
- Provider health-check / ping method (not in requirements; defer to Phase 10 when research.run needs it)
- Multi-provider fallback chains (basic error handling in scope; automatic failover deferred)
- Search result caching (outside v0.4 scope)
- Web scraping beyond search results (defer to future milestone)

## Canonical Refs
- `.planning/ROADMAP.md` — Phase 8 goal and success criteria (lines 51-60)
- `.planning/REQUIREMENTS.md` — SRCH-01 through SRCH-04 requirement texts (lines 14-18)
- `.planning/PROJECT.md` — v0.4 milestone scope and constraints
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — Baseline v0.4 spec
- `src/construct/llm/config.py` — LLM provider config pattern (primary reference)
- `src/construct/capabilities/registry.py` — Capability registry pattern
- `src/construct/capabilities/catalog.py` — Capability catalog pattern
- `src/construct/schemas/config.py` — Existing workspace config schemas
- `tests/llm/conftest.py` — Mock provider pattern
- `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json` — Existing seed template
- `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml` — Existing provider config template pattern
