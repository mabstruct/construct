---
phase: 10
slug: durable-human-review-research-run
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-28
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml / pytest.ini (confirm at Wave 0) |
| **Quick run command** | `uv run pytest tests/llm tests/unit -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~TBD seconds (confirm at Wave 0) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** TBD seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | RSCH-02..05 | — | — | unit/integration | `uv run pytest ...` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Populated by the planner from RESEARCH.md §Validation Architecture — covers RSCH-02 (compose workflow), RSCH-03 (no writes before approval), RSCH-04 (cross-process resume/inspect), RSCH-05 (idempotent rerun), plus the 5 success criteria, all offline-verifiable.*

---

## Wave 0 Requirements

- [ ] Confirm pytest config + quick/full commands and runtime
- [ ] Shared fixtures for offline full-run (mock score-gate, `create_test_workspace`, `sample_search_results` — extend `tests/llm/conftest.py`)
- [ ] Cross-process resume test harness (mirror `tests/unit/test_workflow_runner.py` state/resume pattern for the LangGraph checkpoint)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none expected — research maps all of RSCH-02..05 to deterministic offline tests) | — | — | — |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < TBDs
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
