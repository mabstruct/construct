---
phase: 09-llm-provider-factory-research-score
plan: 01
subsystem: llm
tags: [langchain, factory, ask-domain, provider-config, GATE_PROVIDER_ERROR]

requires:
  - phase: 08-search-provider-spine-contract-foundation
    provides: SearchProviderFactory lazy-import pattern analog
provides:
  - build_chat_model factory for all L3 gates
  - llm-openai optional extra in pyproject.toml
  - ask.domain retrofitted to shared factory seam
affects: [09-02, 09-03, 09-04, research.score]

tech-stack:
  added: [langchain-openai optional extra]
  patterns: [lazy-import provider factory, GATE_PROVIDER_ERROR convention, shared monkeypatch seam on construct.llm.factory.build_chat_model]

key-files:
  created: [src/construct/llm/factory.py, tests/llm/test_factory.py]
  modified: [src/construct/llm/ask_domain.py, pyproject.toml, tests/llm/test_ask_domain.py, tests/contract/test_ask_domain_mocked.py, tests/llm/conftest.py]

key-decisions:
  - "Single build_chat_model path for ask.domain and research.score (D-01)"
  - "langchain_openai lazy-import with GATE_PROVIDER_ERROR when llm-openai extra absent (D-02)"
  - "Test monkeypatch seam on construct.llm.factory.build_chat_model, not ask_domain.ChatAnthropic"

patterns-established:
  - "Provider factory: branch-on-type with lazy optional import (mirrors SearchProviderFactory)"
  - "Shared test seam: monkeypatch construct.llm.factory.build_chat_model for all gates"

requirements-completed: [RSCH-01]

duration: 45min
completed: 2026-06-27
---

# Phase 09 Plan 01 Summary

**Model-agnostic LLM provider factory with ask.domain retrofit — single construction path for all gates.**

## Performance

- **Duration:** ~45 min (interrupted, resumed)
- **Tasks:** 4/4 complete
- **Files modified:** 7

## Accomplishments

- Created `build_chat_model(cfg, *, temperature)` mapping `ProviderConfig.type` to ChatAnthropic/ChatOpenAI
- Declared `llm-openai` optional extra; missing package raises clear `GATE_PROVIDER_ERROR`
- Retrofitted `ask_domain.py` to thread `provider_cfg` through state and use factory
- Repointed all test monkeypatch sites to shared `construct.llm.factory.build_chat_model` seam
- Full suite green at 258 tests (baseline 253+)

## Task Commits

1. **Task 1: Package legitimacy checkpoint** — human-approved (langchain-openai official LangChain package)
2. **Task 2: Provider factory + optional extra** - `cb6400d` (test), `6f5f7c8` (feat)
3. **Task 3: ask.domain retrofit + test seam** - `64065e0` (feat)
4. **Task 4: Full-suite regression** — verified 258 passed, 0 failures

## Files Created/Modified

- `src/construct/llm/factory.py` — build_chat_model with anthropic/openai branches
- `src/construct/llm/ask_domain.py` — factory construction, ProviderConfig in state
- `pyproject.toml` — llm-openai optional dependency
- `tests/llm/test_factory.py` — type map, lazy-import, unknown-provider tests
- `tests/llm/test_ask_domain.py` — repointed patched_llm fixture
- `tests/contract/test_ask_domain_mocked.py` — repointed inline monkeypatch
- `tests/llm/conftest.py` — updated MockChatAnthropic docstring

## Self-Check: PASSED

- factory.build_chat_model unit tests pass
- ask.domain mocked tests pass with new seam
- Full suite: 258 passed
- No ChatAnthropic( construction in ask_domain.py
- grep construct.llm.ask_domain.ChatAnthropic in tests/ returns nothing
