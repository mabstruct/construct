---
phase: 8
slug: search-provider-spine-contract-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-21
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/search/ -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/search/ -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/contract/ tests/search/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green (228+ baseline tests)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | SRCH-02 | T-8-01 | api_key_env name only, no literal secrets | unit | `.venv/bin/python -m pytest tests/search/test_search_config.py -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | SRCH-03 | — | N/A | unit | `.venv/bin/python -m pytest tests/search/test_search_provider_mock.py -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | SRCH-01 | — | N/A | contract | `.venv/bin/python -m pytest tests/search/test_search_contract.py::test_research_search_normalized -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | SRCH-01 | — | N/A | integration | `.venv/bin/python -m pytest tests/search/test_search_contract.py::test_cli_research_search -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | SRCH-01 | — | N/A | contract | `.venv/bin/python -m pytest tests/contract/test_mcp_contracts.py -k research_search -x` | ❌ W0 | ⬜ pending |
| 08-02-04 | 02 | 2 | SRCH-04 | T-8-02 | structured degraded errors | unit | `.venv/bin/python -m pytest tests/search/test_search_provider_mock.py::test_error_injection -x` | ❌ W0 | ⬜ pending |
| 08-02-05 | 02 | 2 | SRCH-02 | — | caps enforced truncated=True | unit | `.venv/bin/python -m pytest tests/search/test_search_provider_mock.py::test_result_cap -x` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 3 | SRCH-03 | — | N/A | contract | `.venv/bin/python -m pytest tests/search/ -x` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 3 | API-05 | — | regression baseline | regression | `.venv/bin/python -m pytest -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/search/conftest.py` — workspace + mock config fixtures
- [ ] `tests/search/test_search_contract.py` — SRCH-01/03 registry + CLI coverage
- [ ] `tests/search/test_search_config.py` — SRCH-02 schema + validation
- [ ] `tests/search/test_search_provider_mock.py` — SRCH-03/04 mock oracle
- [ ] `tests/fixtures/search/*.json` — Tavily sample + mock happy/error paths
- [ ] Update `tests/contract/test_mcp_contracts.py` — add `construct_research_search`
- [ ] `pyproject.toml` `[project.optional-dependencies] search` for Tavily extra

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Tavily search | SRCH-01 | Requires network + API key | Set TAVILY_API_KEY, switch provider to tavily, run `construct research search "test query"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
