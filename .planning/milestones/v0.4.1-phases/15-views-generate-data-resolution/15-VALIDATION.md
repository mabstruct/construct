---
phase: 15
slug: views-generate-data-resolution
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-19
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `15-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml:40-42` — `testpaths=["tests"]`, `pythonpath=[".", "src"]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py tests/contract/test_doc_command_references.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~6 seconds (baseline: 443 passed, 2 warnings, 6.03s — VERIFIED) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest -q` — the whole suite is 6s, so there is no reason to sample a subset.
- **After every plan wave:** Full suite **plus** `construct views validate --install-root <fresh-root>` reporting all 8 files passing.
- **Before `/gsd-verify-work`:** Full suite green, `_KNOWN_BROKEN` contains exactly 4 entries (5 minus `("views","generate")`), and both the fresh and populated generation tests pass.
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

> Task IDs are assigned by the planner. This table is seeded from the research's
> requirement→test map; `/gsd-validate-phase` reconciles it against the final PLAN.md task list.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | FIX-01 / crit.1 | — | N/A | unit | `pytest tests/unit/test_capability_registry.py -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.1 | — | N/A | integration | `pytest tests/integration/test_views_generate.py::test_fresh_workspace_generates_clean -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.1 | — | N/A | integration | `pytest tests/integration/test_views_generate.py::test_populated_workspace_generates_clean -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.2 | — | N/A | contract | `pytest tests/contract/test_doc_command_references.py -x` | ✅ (self-enforcing) | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.3a | — | N/A | unit | `pytest tests/unit/test_capability_registry.py -k views -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.3b | — | No `sys.path` injection; `views.lib` imports from the installed package | unit | `pytest tests/unit/test_views_lib_imports.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.4 | — | Refresh runs as a side effect; failure never flips workflow status | integration | `pytest tests/llm -k views_refresh -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FIX-01 / crit.5 | — | N/A | full | `.venv/bin/python -m pytest -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Model-edit caution (from research):** `tests/contract/test_views_contracts.py` constructs `BridgeSummary(...)`,
`CardRecord(...)`, and `DomainRecord` directly (lines 103, 110, 261, 335-337). Widening the models is
source-compatible for added-with-default fields, but **deleting the 5 phantom `DomainRecord` fields (F3)
is a breaking change** if any test passes them — grep before deleting. The file uses class-based grouping
(`grep -c "^def test"` → 0), so count tests via `pytest --collect-only`.

---

## Wave 0 Requirements

- [ ] `tests/integration/test_views_generate.py` — fresh + populated generation; covers FIX-01 criterion 1 and closes Pitfall 1 (a fresh workspace has zero cards, so the `CardRecord.connections` fix would otherwise go unverified)
- [ ] `tests/unit/test_views_lib_imports.py` — asserts `construct.views.lib` imports with no `sys.path` mutation; covers criterion 3b
- [ ] Shared fixture: scaffolded install root via `services.init` (harness verified in research) — belongs in `tests/conftest.py` or a views-local `conftest.py`
- [ ] Populated-workspace fixture: reuse `tests/fixtures/v02/multi-domain-medium/` (exists) rather than copying `test-ws/`
- [ ] Framework install: **none needed** — pytest present, suite green at 443

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Daily-cycle post-run refresh emits an honest, actionable skip message | FIX-01 / crit.4 | The remediation *wording* must name a command that exists; an automated test can assert the command string resolves, but a human confirms the message reads as actionable | Run a daily cycle with views generation unavailable; confirm the skip message names only commands present in the CLI surface |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
