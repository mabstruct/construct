---
phase: 1
slug: contract-canon-artifact-governance
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-08
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit/test_workspace_contracts.py tests/unit/test_artifact_write_gates.py -x` |
| **Full suite command** | `pytest tests/unit/test_workspace_contracts.py tests/unit/test_artifact_write_gates.py tests/integration/test_workspace_contract_migration.py -x` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_workspace_contracts.py tests/unit/test_artifact_write_gates.py -x`
- **After every plan wave:** Run `pytest tests/unit/test_workspace_contracts.py tests/unit/test_artifact_write_gates.py tests/integration/test_workspace_contract_migration.py -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | FND-01, FND-04 | T-01-01 | Canon docs define one authoritative artifact contract | unit | `pytest tests/unit/test_workspace_contracts.py -k canon -x` | ✅ | ⬜ pending |
| 1-01-02 | 01 | 1 | FND-03 | T-01-02 | Templates/spec references align on canonical vs derived artifacts | unit | `pytest tests/unit/test_workspace_contracts.py -k templates -x` | ✅ | ⬜ pending |
| 1-02-01 | 02 | 2 | FND-01, FND-02 | T-01-03 | Runtime scaffold matches canonical layout and rejects drift | unit | `pytest tests/unit/test_workspace_contracts.py -k scaffold -x` | ✅ | ⬜ pending |
| 1-02-02 | 02 | 2 | FND-02 | T-01-04 | Invalid cards/refs/connections/events fail before write | unit | `pytest tests/unit/test_artifact_write_gates.py -k reject -x` | ✅ | ⬜ pending |
| 1-02-03 | 02 | 2 | FND-02, FND-05 | T-01-05 | Post-write audits detect cross-file inconsistencies only after valid writes land | integration | `pytest tests/integration/test_workspace_contract_migration.py -k validate -x` | ✅ | ⬜ pending |
| 1-03-01 | 03 | 3 | FND-03, FND-04 | T-01-06 | Skills/templates invoke and describe the same contract | integration | `pytest tests/integration/test_workspace_contract_migration.py -k skills -x` | ✅ | ⬜ pending |
| 1-03-02 | 03 | 3 | FND-05 | T-01-07 | Fixture workspaces validate against canonical proof target | integration | `pytest tests/integration/test_workspace_contract_migration.py -k fixtures -x` | ✅ | ⬜ pending |
| 1-03-03 | 03 | 3 | FND-06 | T-01-08 | Migration document enumerates safe upgrade path and checks | integration | `pytest tests/integration/test_workspace_contract_migration.py -k migration -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_workspace_contracts.py` — contract canon assertions
- [ ] `tests/unit/test_artifact_write_gates.py` — pre-write rejection coverage
- [ ] `tests/integration/test_workspace_contract_migration.py` — fixture proof + migration coverage

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
