---
phase: 08-search-provider-spine-contract-foundation
reviewed: 2026-06-21T16:30:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - src/construct/search/__init__.py
  - src/construct/search/errors.py
  - src/construct/search/models.py
  - src/construct/search/provider.py
  - src/construct/search/providers/__init__.py
  - src/construct/search/providers/mock.py
  - src/construct/search/providers/tavily.py
  - src/construct/search/registry.py
  - src/construct/schemas/config.py
  - src/construct/pipelines/research_search.py
  - src/construct/storage/workspace.py
  - src/construct/services/validation.py
  - src/construct/services/init.py
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml
  - pyproject.toml
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-06-21T16:30:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 8 delivers a well-structured search provider spine: discriminated `SearchConfig`, a four-method `SearchProvider` ABC, fixture-driven mock and lazy-import Tavily adapters, cap enforcement via `_CappedSearchProvider`, and a read-only `research.search` handler wired through CLI/MCP. Auth errors are correctly redacted at the handler boundary (T-8-05), API keys are env-var references only, and the Tavily SDK import is isolated to `providers/tavily.py`.

No critical bugs or security vulnerabilities were found. Two warnings warrant follow-up: `max_raw_content_chars` is defined in config but never enforced (relevant when Tavily `include_raw_content` is enabled), and non-auth provider errors may leak third-party exception text to callers in degraded mode. Three informational items note unused schema/handler fields and a dead factory parameter.

## Warnings

### WR-01: `max_raw_content_chars` cap is never enforced

**File:** `src/construct/schemas/config.py:247`, `src/construct/search/providers/tavily.py:44-66`
**Issue:** `SearchCapsConfig.max_raw_content_chars` is defined in schema and template but no code truncates or rejects oversized raw content. When Tavily is configured with `include_raw_content: markdown`, large `raw_content` values flow into `provider_specific` via `normalize_tavily_result()` without length checks, bypassing the documented cap and risking oversized JSON payloads in CLI/MCP responses.
**Fix:** Pass `caps.max_raw_content_chars` into the provider layer (via factory or wrapper) and truncate or omit `raw_content` / `content` fields in `normalize_tavily_result()` when length exceeds the cap; set `truncated=True` on the batch when content is clipped.

### WR-02: Third-party exception text exposed in degraded NetworkError responses

**File:** `src/construct/search/providers/tavily.py:175-176`, `src/construct/pipelines/research_search.py:52-55`
**Issue:** Tavily adapter maps unexpected exceptions to `NetworkError(message=str(exc))`. `_safe_error_message()` only redacts `AuthError`; other `SearchError` subclasses pass `exc.message` through to `OperationResult.message`, `OperationError.suggestion`, and CLI `--json` output. Third-party exception strings may include URLs, internal identifiers, or SDK diagnostics.
**Fix:** Use a generic message for degraded-mode network failures at the handler boundary (mirror auth redaction), or map to a fixed string in the Tavily adapter:

```python
def _safe_error_message(exc: SearchError) -> str:
    if isinstance(exc, AuthError):
        return "Authentication failed for search provider"
    if isinstance(exc, NetworkError):
        return "Network or connectivity failure reaching search provider"
    return exc.message
```

## Info

### IN-01: Unused `workspace` parameter on factory

**File:** `src/construct/search/registry.py:81`
**Issue:** `SearchProviderFactory.create(config, workspace=...)` accepts `workspace` but never uses it. `research_search()` passes `loader.root` at `research_search.py:169`. Dead parameter adds API surface confusion.
**Fix:** Remove the parameter until needed, or use it for workspace-relative `fixture_dir` resolution in the mock provider.

### IN-02: `QuotaExceededError` defined but never raised

**File:** `src/construct/search/errors.py:37-38`, `src/construct/search/providers/tavily.py:164-170`
**Issue:** Tavily `UsageLimitExceededError` is mapped to `RateLimitError`, not `QuotaExceededError`. The quota subclass exists in the taxonomy and error exports but is unreachable from adapters.
**Fix:** Map usage-limit failures to `QuotaExceededError` if semantically distinct from rate limits, or document that quota is folded into `RateLimitError` and remove the unused class in a future cleanup.

### IN-03: `SearchBatchOutput.errors` field never populated

**File:** `src/construct/search/models.py:30`, `src/construct/search/providers/mock.py:94-100`
**Issue:** Model includes `errors: list[dict]` for degraded partial batches, but neither mock nor Tavily providers populate it. Partial-failure batch semantics are not implemented.
**Fix:** Defer until partial-batch degraded mode is required; no action needed for Phase 8 gate if single-query default caps remain.

---

_Reviewed: 2026-06-21T16:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
