---
phase: 10
slug: durable-human-review-research-run
status: planned
nyquist_compliant: true
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
| **Config file** | pyproject.toml (pytest config) |
| **Quick run command** | `uv run pytest tests/llm tests/pipelines -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | confirm at Wave 0 (10-01 Task 3) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/llm/test_research_run.py -x -q` (+ `tests/pipelines/test_research_dedup.py` for Plan 02)
- **After every plan wave:** `uv run pytest tests/llm tests/pipelines tests/contract -q`
- **Before `/gsd:verify-work`:** `uv run pytest -q` must be green
- **Max feedback latency:** quick run < ~30s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T2 | 10-01 | 1 | RSCH-04 (D-02) | T-10-01 | checkpoint DB git-ignored, SOT stays file-based | smoke | `uv run python -c "from langgraph.checkpoint.sqlite import SqliteSaver"` | ✅ | ⬜ |
| 01-T3 | 10-01 | 1 | RSCH-02..05 | — | red Nyquist suite enumerates all behaviors | collect | `uv run pytest tests/llm/test_research_run.py --collect-only -q` | ✅ new | ⬜ |
| 02-T1 | 10-02 | 1 | RSCH-05 | T-10-03 | ref-ID slug+hash, no path traversal, no suffixer | unit | `uv run pytest tests/pipelines/test_research_dedup.py -k "url or ref_id or fuzzy"` | ✅ new | ⬜ |
| 02-T2 | 10-02 | 1 | RSCH-05 | T-10-04/05 | ledger blocks re-ingest; missing-file safe | unit | `uv run pytest tests/pipelines/test_research_dedup.py -k "ledger or rejected"` | ✅ new | ⬜ |
| 03-T1 | 10-03 | 2 | RSCH-02 | T-10-08/09 | outage caught before gate; stderr-only logging | unit | `uv run pytest tests/llm/test_research_run.py -k "build_queries or deduplicate or score_and_extract"` | ✅ new | ⬜ |
| 03-T2 | 10-03 | 2 | RSCH-03 | T-10-06/07 | no writes before approval; interrupt-only gate | integration | `uv run pytest tests/llm/test_research_run.py -k "no_writes_before_approval or pause"` | ✅ new | ⬜ |
| 04-T1 | 10-04 | 3 | RSCH-03/05 | T-10-10/11/13 | approved-only ingest; deterministic skip-if-exists | integration | `uv run pytest tests/llm/test_research_run.py -k "per_finding or idempotent or partial_batch"` | ✅ new | ⬜ |
| 04-T2 | 10-04 | 3 | RSCH-02 (SC5) | T-10-14 | digest+record, last_queried, D-11 events | integration | `uv run pytest tests/llm/test_research_run.py -k "full_run_offline or run_result_fields"` | ✅ new | ⬜ |
| 04-T3 | 10-04 | 3 | RSCH-04 | T-10-12 | cross-process resume; inspect no-resume | integration | `uv run pytest tests/llm/test_research_run.py -k "cross_process_resume or inspect_no_resume"` | ✅ new | ⬜ |
| 05-T1 | 10-05 | 4 | RSCH-02 | T-10-15 | sanitizing dual-mode shims, no raw provider text | contract | `uv run pytest tests/contract/test_research_run_cli_mcp.py -k registry` | ✅ new | ⬜ |
| 05-T2 | 10-05 | 4 | RSCH-02/03/04 | T-10-16/17 | registry-dispatched CLI; stderr-only | smoke | `uv run construct research run --help` | ✅ new | ⬜ |
| 05-T3 | 10-05 | 4 | RSCH-02 (API-05) | T-10-16 | CLI/MCP parity; mcp/server.py untouched; regression | contract+regression | `uv run pytest tests/contract/test_research_run_cli_mcp.py -q && uv run pytest -q` | ✅ new | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Success-criteria → test mapping:** SC1≡test_full_run_offline (RSCH-02); SC2≡test_no_writes_before_approval (RSCH-03); SC3≡test_cross_process_resume + test_inspect_no_resume (RSCH-04); SC4≡test_idempotent_rerun + test_partial_batch_resume_safe (RSCH-05); SC5≡test_run_result_fields.

---

## Wave 0 Requirements

- [ ] Install `langgraph-checkpoint-sqlite` (10-01 Task 2) — blocking; gated by package-legitimacy checkpoint
- [ ] Confirm pytest config + quick/full commands and runtime (10-01 Task 3)
- [ ] Shared fixtures for offline full-run: tmp-sqlite checkpointer fixture + ScoredFinding batch helper (extend `tests/llm/conftest.py`, 10-01 Task 3)
- [ ] Cross-process resume harness (two SqliteSaver on one DB file; mirror `tests/unit/test_workflow_runner.py` r1/r2)
- [ ] Red `tests/llm/test_research_run.py` enumerating RSCH-02..05 + SC5 (10-01 Task 3)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Package legitimacy of langgraph-checkpoint-sqlite | supply-chain (T-10-SC) | slopcheck unavailable; human confirms langchain-ai authorship on pypi.org | 10-01 Task 1 checkpoint:human-verify, blocking-human |

*All RSCH-02..05 behaviors have automated offline verification; the only manual step is the one-time package-legitimacy gate.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency target set (quick run < ~30s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
