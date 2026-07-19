---
phase: 13
slug: daily-cycle-composition
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-06
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Per-task rows and Wave 0 test gaps populated from the "Validation Architecture" section of `13-RESEARCH.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (`testpaths = ["tests"]`) |
| **Quick run command** | `python -m pytest tests/contract/test_daily_run_cli_mcp.py tests/llm/test_daily_run.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | full-suite baseline (~390 tests per research + new daily tests) |

---

## Sampling Rate

- **After every task commit:** Run the plan's targeted `python -m pytest <file> -q`
- **After every plan wave:** `python -m pytest tests/contract tests/llm -q`
- **Before `/gsd:verify-work`:** Full suite (`python -m pytest -q`) must be green (API-05 regression gate)
- **Max feedback latency:** targeted module runtime (seconds)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-T1 | 01 | 1 | DAY-01/02/03 | T-13-01/02/03 | RED-first tests pin composition/degrade/escalate-exclusion/kebab-guard | unit+integration (RED) | `python -m pytest tests/llm/test_daily_run.py --co -q` | ❌→✅ (created here) | ⬜ pending |
| 13-01-T2 | 01 | 1 | DAY-01/02/03 | T-13-01/02/03/04 | thin composition; escalate never auto-written; sanitized errors; stderr-only | unit+integration | `python -m pytest tests/llm/test_daily_run.py -x -q` | ❌→✅ | ⬜ pending |
| 13-02-T1 | 02 | 2 | API-01/02/03 | T-13-05/06 | contract clone; MCP-no-hardcoded guard GREEN from creation | contract (RED+guard) | `python -m pytest tests/contract/test_daily_run_cli_mcp.py::test_mcp_no_hardcoded_daily -x -q` | ❌→✅ (created here) | ⬜ pending |
| 13-02-T2 | 02 | 2 | API-01/02 | T-13-05/06/07 | records+shims; keyword-only guard; server.py untouched | contract | `python -m pytest tests/contract/test_daily_run_cli_mcp.py::test_registered tests/contract/test_daily_run_cli_mcp.py::test_shims_reject_positional_args tests/contract/test_daily_run_cli_mcp.py::test_in_mcp_tool_list tests/contract/test_daily_run_cli_mcp.py::test_mcp_server_exposes_daily -x -q` | ✅ (13-02-T1) | ⬜ pending |
| 13-02-T3 | 02 | 2 | API-02/03 | T-13-05 | daily sub-app via registry handler; CLI/MCP schema+result parity | contract | `python -m pytest tests/contract/test_daily_run_cli_mcp.py -x -q` | ✅ (13-02-T1) | ⬜ pending |
| 13-03-T1 | 03 | 3 | DAY-01 (skill hook, D-10) | T-13-08 | skill invokes real capability + single views refresh; no removed-command refs | doc grep gate | `grep -q "construct daily run" CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md && ! grep -q "workflow run daily-cycle" CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` | ✅ existing doc | ⬜ pending |
| 13-03-T2 | 03 | 3 | API-05 | T-13-09 | additive-only; full v0.3+v0.4 suite green; no weakened baseline | regression | `python -m pytest -q` | ✅ existing suite | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 test stubs are created as the FIRST task of their respective plans (RED-first), not as a separate pre-wave:

- [ ] `tests/llm/test_daily_run.py` (created by 13-01-T1) — composition/degrade/result-surface/auto-apply/pending-escalation/inspect/kebab-guard unit + integration tests; covers DAY-01/02/03. Reuses `tests/llm/conftest.py::create_test_workspace` (L169) + `build_chat_model` seam (L156) + mock search provider (`src/construct/search/providers/mock.py`, SRCH-03) for the happy path and no-API-key for the degrade path. RED until 13-01-T2.
- [ ] `tests/contract/test_daily_run_cli_mcp.py` (created by 13-02-T1) — clone of `tests/contract/test_curation_run_cli_mcp.py`; covers API-01/02/03. `test_mcp_no_hardcoded_daily` is GREEN from creation (guardrail); registration/CLI tests RED until 13-02-T2/T3.
- [x] No framework install needed — pytest is configured (`pyproject.toml` L40).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none_ | — | — | — |

All phase behaviors have automated verification (daily.run is CLI/MCP + result-shape assertable; the skill-hook change is grep-assertable).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_daily_run.py + test_daily_run_cli_mcp.py)
- [x] No watch-mode flags
- [x] Feedback latency < module-runtime seconds
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planner)
