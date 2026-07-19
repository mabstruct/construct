---
phase: 12
slug: curation-l3-gates-review-application
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-30
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 12-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (3.13 venv) |
| **Config file** | repo `pyproject.toml` (existing; `tests/` rooted) |
| **Quick run command** | `.venv/bin/pytest tests/llm/test_curation_run.py tests/llm/test_curation_promote.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -q` |
| **Estimated runtime** | ~quick <30s · full per existing suite |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/pytest tests/llm/test_curation_run.py tests/llm/test_curation_promote.py -x -q`
- **After every plan wave:** `.venv/bin/pytest tests/llm/ tests/contract/ -q`
- **Before `/gsd:verify-work`:** `.venv/bin/pytest tests/ -q` must be green
- **Max feedback latency:** <30 seconds (quick), full suite per existing runtime

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| CUR-02 | `card.evaluate` returns `PromotionDecision` (promote/hold/escalate) with reasoning over non-mature cards | unit | `.venv/bin/pytest tests/llm/test_curation_promote.py -x` | ❌ W0 |
| CUR-02 | per-item retry; failed card → `escalate` + `method="rule-based"` | unit | `.venv/bin/pytest tests/llm/test_curation_promote.py::test_failure_escalates -x` | ❌ W0 |
| CUR-03 | no canonical write before `Command(resume=approve)` | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_no_writes_before_approval -x` | ❌ W0 (mirror research_run test) |
| CUR-03 | approved promotion writes lifecycle; rejected does not | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_reviewed_promotion_applied -x` | ❌ W0 |
| CUR-03 | approved connection typed + written via add_connection; idempotent on rerun | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_reviewed_connection_idempotent -x` | ❌ W0 |
| CUR-03 | auto_archive applied only when approved + `auto_archive_on_decay=true` | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_reviewed_archive_applied -x` | ❌ W0 |
| CUR-03 | single consolidated gate: one gate_id, one resume covers all three proposal types | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_single_consolidated_gate -x` | ❌ W0 |
| CUR-03 | empty gate_queue → completes without pausing | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_empty_queue_no_pause -x` | ❌ W0 |
| CUR-03 | cross-process resume (separate checkpointer open) | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_cross_process_resume -x` | ❌ W0 (mirror research_run test) |
| CUR-04 | inspect reports `awaiting_review` + gate_queue; never resumes | unit | `.venv/bin/pytest tests/llm/test_curation_run.py::test_inspect_pending_review -x` | ❌ W0 (extend `test_inspect_no_rerun`) |
| CUR-04 | events emitted for each step + gate review (spec §6.6) | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_curation_events_emitted -x` | ❌ W0 |
| CUR-05 | no real step emits "placeholder"; deferred-only nodes gone | unit | `.venv/bin/pytest tests/llm/test_curation_run.py::test_steps_return_concrete_findings -x` | ✅ exists (test_curation_run.py:188) |
| CUR-05 | `_get_workflow_steps` curation-cycle lambdas removed; no placeholder reachable from CLI/MCP | contract | `.venv/bin/pytest tests/contract/test_curation_run_cli_mcp.py::test_no_placeholder_curation_path -x` | ❌ W0 |
| CUR-05 | unreviewed canonical write guard: assert no write outside post-gate nodes | integration | `.venv/bin/pytest tests/llm/test_curation_run.py::test_no_unreviewed_writes -x` | ❌ W0 |
| API-04 | migrated skills carry no `WebSearch`/`WebFetch`/`Write` in `allowed-tools` | static/contract | `.venv/bin/pytest tests/contract/test_skill_migration.py -x` | ❌ W0 |
| API parity | `curation.review` / `card.evaluate` registered (cli_name+mcp_tool_name); MCP auto-discovered | contract | `.venv/bin/pytest tests/contract/test_curation_run_cli_mcp.py::test_registered -x` | ✅ extend (test_curation_run_cli_mcp.py:46) |

*Status filled per-task by the planner; Wave 0 (W0) entries must exist before their consuming task runs.*

---

## Wave 0 Requirements

- [ ] `tests/llm/test_curation_promote.py` — CUR-02 (card.evaluate gate, retry/escalate, governance clamp); mirror `tests/llm/test_research_score.py`
- [ ] Connection-typing gate tests (in `test_curation_promote.py` or sibling) — D-05
- [ ] Extend `tests/llm/test_curation_run.py` — reviewed-write + interrupt/resume + consolidated-gate + no-unreviewed-write tests; mirror `tests/llm/test_research_run.py`
- [ ] Extend `tests/contract/test_curation_run_cli_mcp.py` — `curation.review` + `card.evaluate` registration + no-placeholder guard
- [ ] `tests/contract/test_skill_migration.py` — assert the three migrated skills carry no forbidden tools (API-04)
- [ ] Extend `tests/llm/conftest.py` — `PromotionDecision`-shaped `ConfigurableStructuredMock` + connection-type mock seam
- [ ] Framework install — none needed (pytest already present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skill conversational review loop (presents gate queue, collects approve/reject, resumes) | API-04 | Claude-native skill behavior is not unit-testable end-to-end | Run migrated `construct-curation-cycle` skill against `test-ws/my-construct`; confirm it invokes `construct curation run` + drives review with zero direct WebSearch/WebFetch/Write |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01 creates every W0 test)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-01 — plan-check verdict READY-WITH-CONCERNS; warnings W1–W4 resolved in plans. `wave_0_complete` flips true when Plan 01 lands the Wave-0 tests.
