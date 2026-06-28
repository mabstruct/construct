---
phase: 11
slug: curation-pipe-steps
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-28
approved: 2026-06-28
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (cpython 3.13) |
| **Config file** | `pyproject.toml` + `tests/conftest.py` + `tests/llm/conftest.py` |
| **Quick run command** | `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -x` |
| **Full suite command** | `./.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~3 min (full) |

---

## Sampling Rate

- **After every task commit:** Run `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -x`
- **After every plan wave:** Run `./.venv/bin/python -m pytest tests/llm/ tests/contract/test_curation_run_cli_mcp.py -q`
- **Before `/gsd:verify-work`:** Full suite (`pytest -q`) must be green (API-05 regression)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | CUR-01 | T-11-04 | conftest extended additively; existing suite unaffected | regression | `./.venv/bin/python -m pytest tests/llm/test_research_run.py -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | CUR-01 | T-11-04 / T-11-PL | red suite samples concrete-findings, degraded≠completed, no-canonical-writes | unit/integration | `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -q` (RED expected) | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | CUR-01 | T-11-01 | contract red suite samples registry+CLI+MCP parity; mcp-no-hardcoded guard | contract | `./.venv/bin/python -m pytest tests/contract/test_curation_run_cli_mcp.py -q` (RED expected) | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | CUR-01 | T-11-01 | run_id kebab-validated at input boundary; checkpointer persistent | unit | `./.venv/bin/python -c "from construct.llm.curation_run import CurationRunInput; ..."` | ✅ (W0) | ⬜ pending |
| 11-02-02 | 02 | 2 | CUR-01 | T-11-02 / T-11-04 | real findings + thresholds honored + no canonical writes + per-node failed-not-crash | unit/integration | `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -k "real_findings or deferred or thresholds or no_canonical or auto_archive" -x` | ✅ (W0) | ⬜ pending |
| 11-02-03 | 02 | 2 | CUR-01 | T-11-02 | D-09 aggregation: clean=completed, required failure=degraded; inspect no-rerun | unit | `./.venv/bin/python -m pytest tests/llm/test_curation_run.py -q` | ✅ (W0) | ⬜ pending |
| 11-03-01 | 03 | 3 | CUR-01 | T-11-01 / T-11-05 | registration + keyword-only shims; legacy placeholders untouched | contract | `./.venv/bin/python -m pytest tests/contract/test_curation_run_cli_mcp.py -k "registered or positional or hardcoded" -x` | ✅ (W0) | ⬜ pending |
| 11-03-02 | 03 | 3 | CUR-01 | T-11-01 | CLI sub-app + curation renderer; CLI/MCP schema parity offline | contract | `./.venv/bin/python -m pytest tests/contract/test_curation_run_cli_mcp.py -q` | ✅ (W0) | ⬜ pending |
| 11-03-03 | 03 | 3 | CUR-01 | T-11-07 | full regression (API-05); legacy fake-success flagged for Phase 12 | regression | `./.venv/bin/python -m pytest -q` | ✅ (W0) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/llm/test_curation_run.py` — node + graph + scan-threshold + status-aggregation + no-write + anti-placeholder tests (CUR-01). Created in Plan 01.
- [ ] `tests/contract/test_curation_run_cli_mcp.py` — registry presence, dual-mode shim, MCP auto-discovery, CLI/MCP schema parity, offline smoke (CUR-01). Created in Plan 01.
- [ ] `tests/llm/conftest.py` — extend `write_card` (created/last_verified params) + new `curation_workspace` fixture (deterministic decay/orphan card set + connections.json). Created in Plan 01.
- [ ] Framework install — none (pytest already present).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (both new test files + conftest fixtures created in Plan 01)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-28
