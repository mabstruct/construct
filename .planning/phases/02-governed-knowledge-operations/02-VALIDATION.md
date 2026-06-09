---
phase: 2
slug: governed-knowledge-operations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0+ |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/unit/test_knowledge_operations.py -x -v` |
| **Full suite command** | `python -m pytest tests/ -x -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/test_knowledge_operations.py -x -v`
- **After every plan wave:** Run `python -m pytest tests/ -x -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 02-01-01 | 01 | 1 | ING-03 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_card_create -x` | ⬜ pending |
| 02-01-02 | 01 | 2 | ING-03 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_card_edit -x` | ⬜ pending |
| 02-01-03 | 01 | 2 | ING-03 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_card_archive -x` | ⬜ pending |
| 02-02-01 | 02 | 1 | ING-04 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_connection_add -x` | ⬜ pending |
| 02-02-02 | 02 | 2 | ING-04 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_connection_remove -x` | ⬜ pending |
| 02-02-03 | 02 | 2 | ING-04 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_connection_list -x` | ⬜ pending |
| 02-03-01 | 03 | 1 | ING-02 | N/A (file ops) | unit | `pytest tests/unit/test_knowledge_operations.py::test_source_routing -x` | ⬜ pending |
| 02-03-02 | 03 | 2 | ING-02 | N/A (file ops) | int | `pytest tests/integration/test_knowledge_cli.py -x` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_knowledge_operations.py` — stubs for card CRUD, connection CRUD, source routing
- [ ] `tests/integration/test_knowledge_cli.py` — stubs for CLI integration tests
- [ ] `tests/conftest.py` — already exists with CliRunner fixture

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skill wrappers invoke Python CLI correctly | ING-03, ING-04 | Skills are markdown procedures, not code | Verify SKILL.md calls CLI commands with correct args |
| Structured error messages display in skill flow | ING-03 | Visual/UX behavior | Run card create with invalid data, verify suggestion shown |

*All phase behaviors have automated verification for Python layer.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
