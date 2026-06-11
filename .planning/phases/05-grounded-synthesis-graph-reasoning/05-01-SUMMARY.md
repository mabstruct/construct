---
phase: 05-grounded-synthesis-graph-reasoning
plan: 01
subsystem: LLM Infrastructure
tags: [langgraph, langchain, provider-config, test-infrastructure, mock-llm]
requires: []
provides: [llm-package, provider-config, test-fixtures, pyproject-deps]
affects: [pyproject.toml, src/construct/llm/]
tech-stack:
  added:
    - langgraph>=0.2
    - langchain-core>=0.3
    - langchain-anthropic>=1.1.0
  patterns:
    - Pydantic config models with extra="forbid"
    - TypedDict for LangGraph state schemas (reserved)
    - MockChatAnthropic fixture pattern for LLM tests
key-files:
  created:
    - src/construct/llm/__init__.py
    - src/construct/llm/config.py
    - src/construct/llm/config.yaml
    - tests/llm/__init__.py
    - tests/llm/conftest.py
    - tests/llm/test_ask_domain.py
    - tests/bridge/__init__.py
    - tests/bridge/conftest.py
    - tests/bridge/test_bridge_l1.py
    - tests/bridge/test_bridge_l2.py
    - tests/bridge/test_bridge_l3.py
    - tests/bridge/test_bridge_scoring.py
    - tests/contract/__init__.py
    - tests/contract/test_ask_domain_mocked.py
  modified:
    - pyproject.toml
decisions:
  - "langchain-anthropic pinned >=1.1.0 for method='json_schema' support (not >=0.3)"
  - "ProviderConfig includes optional base_url field for Ollama provider"
  - "Config YAML stores only provider metadata — API keys from env vars per D-07"
  - "load_llm_config uses 3-tier resolution: explicit arg -> CONSTRUCT_LLM_CONFIG env -> default path"
metrics:
  duration: ~15 minutes
  completed: "2026-06-11"
  tasks: 3
  files_created: 14
  files_modified: 1
  test_count: 22 (17 passed, 5 skipped)
---

# Phase 5 Plan 01: LLM Package, Provider Config & Test Infrastructure Summary

**One-liner:** Created `src/construct/llm/` package with Pydantic-validated YAML config loader for LLM providers/gates, added LangGraph/LangChain dependencies to `pyproject.toml`, and scaffolded all 14 test infrastructure files for the ask.domain and bridge.detect test suites.

## What Was Built

### Task 1: LangGraph/LangChain Dependencies

Added three dependencies to `pyproject.toml` in alphabetical order:
- `langchain-anthropic>=1.1.0` (NOT >=0.3 — required for `method="json_schema"`)
- `langchain-core>=0.3`
- `langgraph>=0.2`

All packages installed successfully. Verified imports work:
- `from langgraph.graph import StateGraph, START, END` ✓
- `from langchain_anthropic import ChatAnthropic` ✓

### Task 2: LLM Package (`src/construct/llm/`)

**`__init__.py`** — Package entry point with `from __future__ import annotations`.

**`config.py`** — Three Pydantic models with `extra="forbid"`:
- `ProviderConfig`: type, model, max_tokens, timeout_seconds, base_url (optional, for Ollama)
- `GateConfig`: provider, temperature, review_required
- `LlmConfig`: version, default_gate, providers dict, gates dict

`load_llm_config()` function with 3-tier resolution:
1. Explicit `config_path` argument
2. `CONSTRUCT_LLM_CONFIG` environment variable
3. Default `src/construct/llm/config.yaml`

Resolver raises `FileNotFoundError` with `GATE_PROVIDER_ERROR` prefix when config not found.

**`config.yaml`** — Default config with:
- 3 providers: anthropic (claude-sonnet-4-20250514), openai (gpt-4o), ollama (llama3.1)
- 1 gate: ask.domain (provider: anthropic, temperature: 0.2, review_required: true)
- No API keys or secrets stored in YAML

### Task 3: Test Infrastructure (14 files)

Created three test packages with mock fixtures and stub test cases:

**`tests/llm/conftest.py`:**
- `MockChatAnthropic` class with `with_structured_output()` and `invoke()` returning canned `MockSynthesisOutput`
- `MockSynthesisOutput` with answer, cited_card_ids, confidence fields
- `create_test_workspace()` helper using `initialize_workspace()`
- `write_card()` helper for fixture card creation
- `mock_llm` and `test_workspace` pytest fixtures

**`tests/bridge/conftest.py`:**
- `cross_domain_workspace` fixture with two domains (cosmology, philosophy-of-mind)
- Cross-domain connections between cosmo-1 and phil-1
- `_init_second_domain()` helper for multi-domain workspace setup
- `_write_connections()` helper for connections.json fixture

**Test files:**
- `tests/llm/test_ask_domain.py` — provider config load test + import placeholder stub
- `tests/bridge/test_bridge_scoring.py` — 8 parametrized scoring cases covering all band transitions (strong/medium/weak) with 0.30/0.20/0.50 weight verification
- `tests/bridge/test_bridge_l1.py`, `l2.py`, `l3.py` — placeholder stubs for Plan 03
- `tests/contract/test_ask_domain_mocked.py` — CLI contract test placeholder for Plan 02

**Test results:** 17 passed, 5 skipped (planned forward-looking stubs)

## Deviations from Plan

### [Rule 1 - Bug] Fixed missing `base_url` field in ProviderConfig

- **Found during:** Task 2 — config YAML validation
- **Issue:** `ProviderConfig` model had `extra="forbid"` but Ollama provider config in YAML includes `base_url` field, causing `ValidationError`
- **Fix:** Added `base_url: str | None = None` to `ProviderConfig`
- **Files modified:** `src/construct/llm/config.py`
- **Commit:** 0a232a7 (included in task 2)

### [Rule 1 - Bug] Fixed missing `import pytest` in L1/L2/L3 bridge test stubs

- **Found during:** Task 3 — pytest run showed `NameError: name 'pytest' is not defined`
- **Issue:** `test_bridge_l1.py`, `test_bridge_l2.py`, `test_bridge_l3.py` used `pytest.skip()` without importing `pytest`
- **Fix:** Added `import pytest` to all three files
- **Files modified:** `tests/bridge/test_bridge_l1.py`, `test_bridge_l2.py`, `test_bridge_l3.py`
- **Commit:** 5e1cc61 (included in task 3)

### [Rule 1 - Bug] Fixed ruamel.yaml `dumps()` usage in bridge conftest

- **Found during:** Task 3 — code review of `_init_second_domain`
- **Issue:** `ruamel.yaml.YAML()` objects don't have a `dumps()` method; plan example used non-existent API
- **Fix:** Replaced `yaml.dumps(data, ...)` with `StringIO` buffer + `yaml.dump(data, buf)`
- **Files modified:** `tests/bridge/conftest.py`
- **Commit:** 5e1cc61 (included in task 3)

## Threat Surface Scan

No new threat surface introduced beyond what's documented in the plan:
- Config YAML stores only provider metadata (model name, temperature, timeouts)
- No API keys in YAML files
- Pydantic models enforce `extra="forbid"` on all config inputs
- Ruamel.yaml in `safe` mode prevents arbitrary code execution
- File path validated via `Path.exists()` before reading

## Self-Check: PASSED

All 14 created files verified on disk.
All 3 commits verified in git log.
No accidental file deletions detected.

All must-have artifacts verified:
- [x] pyproject.toml: langchain-anthropic>=1.1.0, langchain-core>=0.3, langgraph>=0.2
- [x] src/construct/llm/__init__.py exists (2 lines)
- [x] src/construct/llm/config.py contains `load_llm_config`
- [x] src/construct/llm/config.yaml contains `ask.domain`
- [x] tests/llm/conftest.py contains `MockChatAnthropic`
- [x] tests/bridge/conftest.py contains cross-domain fixture
- [x] tests/llm/test_ask_domain.py (40 lines, ≥10)
- [x] tests/bridge/test_bridge_scoring.py contains `_compute_bridge_score`
- [x] Test discovery: 22 tests collected, 0 import errors
- [x] Provider config: 3 providers loaded correctly
- [x] All commits: aff5051, 0a232a7, 5e1cc61
