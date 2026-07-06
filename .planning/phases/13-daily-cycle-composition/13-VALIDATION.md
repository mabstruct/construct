---
phase: 13
slug: daily-cycle-composition
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-06
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Detailed per-task rows and Wave 0 test gaps are populated from the "Validation Architecture" section of `13-RESEARCH.md` during planning.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `pytest tests/contract/test_daily_run_cli_mcp.py -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~full-suite baseline (390 tests per research) |

---

## Sampling Rate

- **After every task commit:** Run the plan's targeted `pytest <file> -q`
- **After every plan wave:** Run the relevant contract/integration test module
- **Before `/gsd:verify-work`:** Full suite (`pytest -q`) must be green (API-05 regression gate)
- **Max feedback latency:** targeted module runtime (seconds)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _populated by planner from RESEARCH.md Validation Architecture_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test gaps identified in `13-RESEARCH.md` "Validation Architecture" section (Wave 0 test stubs) — planner to enumerate per DAY-01/02/03 and API-01/02/03/05.

*Planner: replace with concrete stub files. If existing infrastructure covers all requirements, state so explicitly.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _populated by planner (expected: none — daily.run is CLI/MCP + result-shape assertable)_ | | | |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < module-runtime seconds
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
