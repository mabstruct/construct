---
phase: 05
slug: grounded-synthesis-graph-reasoning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0+ |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/llm/ tests/bridge/ -x --tb=short -q` |
| **Full suite command** | `pytest tests/ -x --tb=short` |
| **Estimated runtime** | ~60 seconds (mocked LLM) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/llm/ tests/bridge/ -x --tb=short -q`
- **After every plan wave:** Run `pytest tests/ -x --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | ADV-01, ADV-02 | — | N/A (package scaffolding) | unit | `pytest tests/unit/test_capability_registry.py -x -q` | ✅ | ⬜ pending |
| 05-01-02 | 01 | 1 | ADV-01 | T-05-02 | Config references env vars, never stores keys inline | unit | `pytest tests/llm/test_ask_domain.py::test_provider_config -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | ADV-01 | T-05-04 | with_structured_output enforces format; extract_citations validates every ID | unit | `pytest tests/llm/test_ask_domain.py::test_ask_domain_structure -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | ADV-01 | T-05-01 | System prompt restricts LLM to provided context; no tool access | contract | `pytest tests/contract/test_ask_domain_mocked.py -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | ADV-01 | T-05-05 | filter_by_domain blocks out-of-domain cards before LLM | unit | `pytest tests/llm/test_ask_domain.py::test_domain_filtering -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | ADV-02 | T-05-03 | WorkspaceLoader constrains to workspace root; Pydantic validates input | unit | `pytest tests/bridge/test_bridge_l1.py -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 3 | ADV-02 | — | L1+L2 threshold prevents O(N²) LLM calls | unit | `pytest tests/bridge/test_bridge_l3.py::test_l3_threshold -x` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 3 | ADV-02 | — | Scoring matches spec-v02-cross-domain-data.md weights (0.30/0.20/0.50) | unit | `pytest tests/bridge/test_bridge_scoring.py -x` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 3 | ING-06 | — | N/A (SKILL.md documentation) | manual | `MISSING — SKILL.md is documentation, not code` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/llm/test_ask_domain.py` — covers ADV-01, ING-06 (structure, citations, confidence, domain filtering, error paths)
- [ ] `tests/llm/conftest.py` — mock LLM fixtures (MockChatAnthropic returning SynthesisOutput), shared test data, workspace fixtures
- [ ] `tests/bridge/test_bridge_l1.py` — L1 structural edge detection from connections.json
- [ ] `tests/bridge/test_bridge_l2.py` — L2 category overlap scoring across domains
- [ ] `tests/bridge/test_bridge_l3.py` — L3 LLM assessment with mocked LLM; L1+L2 threshold enforcement
- [ ] `tests/bridge/test_bridge_scoring.py` — Scoring model: _compute_bridge_score weights (0.30/0.20/0.50), band assignment
- [ ] `tests/bridge/conftest.py` — workspace fixtures with cross-domain cards, mocked LLM for L3
- [ ] `tests/contract/test_ask_domain_mocked.py` — CLI contract test: full ask domain flow with mocked LLM
- [ ] `tests/eval/reference-ask-domain.json` — Reference dataset for eval (15 examples)
- [ ] `tests/eval/reference-bridge-detect.json` — Reference dataset for bridge eval
- [ ] Framework install: `pip install langgraph langchain-core langchain-anthropic`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Synthesis skill update (SKILL.md) | ING-06 | Documentation-only change in SKILL.md format — no code to test | Verify skill references `construct ask`, `construct knowledge card`, and shows confidence annotation in procedure steps |
| bridges.json output format | ADV-02 | Contract alignment with spec-v02-cross-domain-data.md schema | Validate output JSON matches spec schema: confirmed/strong_candidates structure, scoring model, band assignment |
| ask.domain answer quality | ADV-01 | Requires human judgment on answer accuracy | Run `construct ask --domain "cosmology" --question "..."` on test-ws/my-construct workspace, verify citations point to real cards, answer is grounded. Repeat for 3 scenarios (clear answer, no answer, low confidence). |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
