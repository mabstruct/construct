---
phase: 01
slug: workspace-canonical-data-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-22
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/unit -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit -q`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | WORK-01 | T-01-01 | CLI entrypoint is importable and installable without executing unsafe side effects | unit | `python -m pytest tests/unit/test_bootstrap.py -q` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | WORK-01 | T-01-02 | Test harness and fixture workspace exist before feature work depends on them | unit | `python -m pytest tests/unit/test_bootstrap.py -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | WORK-02 / CARD-01 / CARD-04 | T-01-03 | Schemas reject malformed canonical data and distinguish canonical from derived paths | unit | `python -m pytest tests/unit/test_schema_contracts.py -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | WORK-02 / CARD-04 | T-01-04 | Default templates contain editable routing/config values, not embedded secrets | unit | `python -m pytest tests/unit/test_schema_contracts.py -q` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | CARD-03 / CARD-04 | T-01-05 | Validation service surfaces structured errors/warnings without mutating source files | unit | `python -m pytest tests/unit/test_validation_service.py -q` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | CARD-03 | T-01-06 | Invalid fixtures prove malformed YAML and filename/schema problems fail clearly | unit | `python -m pytest tests/unit/test_validation_service.py -q` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 4 | WORK-01 / WORK-03 | T-01-07 | `construct init` constrains writes to the requested workspace path and writes only scaffolded files | integration | `python -m pytest tests/integration/test_init_cli.py -q` | ❌ W0 | ⬜ pending |
| 01-04-02 | 04 | 4 | WORK-01 / WORK-03 / CARD-03 | T-01-08 | CLI commands report validation/status results without treating derived directories as canonical inputs | integration | `python -m pytest tests/integration/test_init_cli.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — pytest configuration and executable package metadata
- [ ] `tests/conftest.py` — shared fixtures and temporary workspace helpers
- [ ] `tests/unit/test_bootstrap.py` — bootstrap assertions for the initial shell

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
