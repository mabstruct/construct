---
phase: 09
slug: llm-provider-factory-research-score
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-26
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (`dev` extra) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `./.venv/bin/python -m pytest tests/llm -q` |
| **Full suite command** | `./.venv/bin/python -m pytest -q` |
| **Baseline test count** | 253 (must stay green; new Phase 9 tests raise it) |
| **Estimated runtime** | ~1–5 seconds (offline; mock LLM, no network) |

---

## Sampling Rate

- **After every task commit:** `./.venv/bin/python -m pytest tests/llm/test_factory.py tests/llm/test_research_score.py -x -q`
- **After every plan wave:** `./.venv/bin/python -m pytest tests/llm -q`
- **Before `/gsd:verify-work`:** Full suite green (`./.venv/bin/python -m pytest -q`, ≥253 + new)
- **Max feedback latency:** < 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | RSCH-01 | T-09-SC | langchain-openai legitimacy verified before declaring optional extra | checkpoint | (human-verify, pypi.org) | N/A | ⬜ pending |
| 09-01-02 | 01 | 1 | RSCH-01 | T-09-06 | factory maps type→ChatModel; no API key logged; GATE_PROVIDER_ERROR on missing/unknown | unit | `pytest tests/llm/test_factory.py -x -q` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | RSCH-01 | — | ask.domain identical through factory; shared monkeypatch seam | regression | `pytest tests/llm/test_ask_domain.py tests/contract/test_ask_domain_mocked.py -x -q` | ✅ (repoint) | ⬜ pending |
| 09-01-04 | 01 | 1 | RSCH-01 | — | [BLOCKING] no regression across whole suite | regression | `pytest -q` (≥253) | ✅ | ⬜ pending |
| 09-02-01 | 02 | 2 | RSCH-01 | T-09-05 | Wave 0 mocks + Phase-8 SearchResult fixtures; concurrency cap config; no schema drift | unit | `python -c "load_llm_config(...) research.score cap==5"` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | RSCH-01 | T-09-01 / T-09-02 / T-09-05 | LLM picks action+tier; Python ceiling-clamp; thresholds echoed; taxonomy soft-steer; skip⇒key_findings=[]; no writes | unit | `pytest tests/llm/test_research_score.py -k "clamp or threshold or taxonomy or score_one or key_findings" -x -q` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 3 | RSCH-01 | T-09-03 / T-09-04 / T-09-05 | bounded fan-out cap; retry-once-then-skip+reason; total-outage promotion; key-safe errors | unit | `pytest tests/llm/test_research_score.py -k "fanout or cap or retry or skip or outage or sanitiz or degraded" -x -q` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 3 | RSCH-01 | T-09-05 | run_gate assembles output w/ thresholds+counters; no workspace mutation | unit | `pytest tests/llm/test_research_score.py -x -q && pytest tests/llm -q` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 4 | RSCH-01 | T-09-03 / T-09-04 | registered with input/output+CLI+MCP names; outage⇒success=False | contract | `pytest tests/llm/test_research_score_capability.py -x -q` | ❌ W0 | ⬜ pending |
| 09-04-02 | 04 | 4 | RSCH-01 | T-09-V5 / T-09-03 | CLI runs pre-fetched payload; table+JSON parity; validated input | contract | `pytest tests/contract/test_research_score_cli_mcp.py -x -q` | ❌ W0 | ⬜ pending |
| 09-04-03 | 04 | 4 | RSCH-01 | — | MCP parity (construct_research_score discovered); [BLOCKING] full suite green | contract+regression | `pytest -q` (>253) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Created in Plan 01 Task 2 and Plan 02 Task 1 (before the implementations that consume them):

- [ ] `tests/llm/test_factory.py` — provider type→class map, lazy-import error, unknown-provider error (Plan 01 Task 2).
- [ ] `tests/llm/conftest.py` — (a) configurable structured-output mock, (b) invalid-output mock (fail-then-retry), (c) total-outage mock (always provider/auth error), (d) Phase-8 `SearchResult` fixtures, (e) repointed ask.domain monkeypatch seam → `construct.llm.factory.build_chat_model` (Plan 01 Task 3 + Plan 02 Task 1).
- [ ] `tests/llm/test_research_score.py` — scoring/clamp/threshold/taxonomy (Plan 02) + fan-out/retry/skip/outage/run_gate (Plan 03).
- [ ] `tests/llm/test_research_score_capability.py` + `tests/contract/test_research_score_cli_mcp.py` — registry + CLI/MCP parity + outage→failure (Plan 04).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live OpenAI/Anthropic `json_schema` structured output on the pinned models | RSCH-01 | Not offline-testable (real provider, costs, keys); ASSUMED A1/A2 in research | After installing `.[llm-openai]` and exporting keys, run one live `construct research score` with a small real payload; confirm valid ScoredFinding output. Deferred to a live smoke, not a phase gate. |
| langchain-openai package legitimacy | RSCH-01 (T-09-SC) | slopcheck not run offline; first-party LangChain package | Plan 01 Task 1 checkpoint: verify pypi.org/project/langchain-openai. |

*All in-phase behaviors (mock LLM, invalid-output, degraded-state, clamp, parity, no-writes) have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (Wave 0 scaffolds created during execution, before consumers)
