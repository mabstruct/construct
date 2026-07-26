---
phase: 18
slug: contract-governance-foundations
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-26
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 18` from `18-RESEARCH.md` § Validation Architecture.
> Task IDs are filled in by the planner; the requirement→test map below is the contract they must satisfy.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = [".", "src"]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/contract tests/unit -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~293 tests quick / 532 tests full |

Collection by directory [VERIFIED via `pytest --collect-only`]: `contract` 171, `llm` 128, `unit` 122,
`integration` 51, `search` 25, `pipelines` 19, `bridge` 16.

> **Correction carried from research:** CONTEXT.md cites "the 515-test suite"; the actual figure is **532**.
> D-05's no-allowlist stance depends on distinguishing failures this phase *caused* from failures it
> *inherited*, so the 532-green baseline must be captured before Wave 1 starts.

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/contract tests/unit -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest -q`
- **Before `/gsd-verify-work`:** Full 532-test suite must be green
- **Max feedback latency:** quick run must stay under ~60 seconds
- **Before Wave 1 starts:** capture the full-suite baseline (research assumption A3)

---

## Per-Task Verification Map

Requirement → test contract from research. The planner fills `Task ID` / `Plan` / `Wave` when plans exist;
no requirement row may be dropped.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | VFIX-01 | — | generate→validate round-trips on a **populated** root; every generated slot passes; record lists non-empty; file cardinality matches `4 + 6·N + 1` (D-19) | integration | `.venv/bin/python -m pytest tests/integration/test_views_generate.py -x` | ✅ (guard **replaces** `:285`) | ⬜ pending |
| TBD | TBD | TBD | VFIX-01 | — | conformed models still reject a genuinely malformed payload — `extra="ignore"` (D-03) did not become "accept anything" | contract | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py -x` | ✅ | ⬜ pending |
| TBD | TBD | TBD | VFIX-01 / D-17 | — | `events.json` validates against the canonical Python-emitter shape, and the SPA reader consumes that same shape | contract | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py -k events -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VFIX-01 / D-18 | — | `stats.json` and `curation-history.json` have contract models and are inside the round-trip guard's count | contract | same file | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VFIX-01 / D-20 | — | `DigestRecord`'s **write** path (`research_run.py:644`) conforms with the model rename — the workspace file matches | llm | `.venv/bin/python -m pytest tests/llm/test_research_run.py -k digest -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | GOV-01 | T-18-01 | same `(capability, payload)` → identical result on real CLI process and real MCP dispatch | integration | `.venv/bin/python -m pytest tests/integration/test_surface_parity.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | GOV-01 | T-18-01 | an unknown field is rejected on **both** surfaces with the same reason | integration | same file | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | GOV-01 | — | every registered capability's model fields bind to its handler (research Finding G3 audit, as a permanent guard) | contract | `.venv/bin/python -m pytest tests/contract/test_capability_seam.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | GOV-01 / D-06 | T-18-02 | all 28 input models carry `extra="forbid"` — cardinality, not membership | contract | same file | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | GOV-02 / D-10 | T-18-03 | incomplete decision map → zero canonical writes, run still paused, uncovered ids named | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k decision -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | GOV-02 / D-12 | — | legacy id-less checkpoint migrates on read and **still** requires a complete map | llm | same file | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | GOV-03 / D-11 | T-18-04 | resume with a stale `checkpoint_id` → rejected, zero writes | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k etag -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | GOV-04 / D-13 | T-18-05 | no canonical writer reachable outside apply nodes (source-level guard, shaped like `test_gate_review_is_interrupt_only` at `test_research_run.py:758`) | llm | `.venv/bin/python -m pytest tests/llm/test_research_run.py -k interrupt_only -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | GOV-04 / D-13 | — | Streamlit app still starts with the `gate_review` page removed | contract | import-level check of `streamlit_app` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | GOV-04 / D-16 | T-18-06 | no `gate_review_approved` emitted when the underlying write failed or was a no-op | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k event -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | GOV-05 | — | degraded run reports degraded on CLI human output, CLI `--json`, and MCP result — table-driven, one row per surface | integration | `.venv/bin/python -m pytest tests/integration/test_surface_honesty.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | GOV-05 / D-16 | — | escalated items appear in their own bucket on every surface and never in an applied/success count | integration | same file | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-15 | — | degraded `curation.run` still exits 0 — the Phase 11 contract is **preserved**, not changed | integration | same file | ❌ W0 — **regression guard, add it** | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_surface_parity.py` — GOV-01 differential CLI↔MCP (needs a `subprocess` helper for the real-CLI arm, per research Pitfall 5)
- [ ] `tests/contract/test_capability_seam.py` — GOV-01 model↔handler binding audit + `extra="forbid"` cardinality
- [ ] `tests/integration/test_surface_honesty.py` — GOV-05 table-driven degraded/escalated across surfaces, plus the D-15 exit-code regression guard
- [ ] Fixture: a `curation.run` forced degraded, and a run with an escalated item (GOV-05 needs both; neither exists today)
- [ ] Fixture: a pre-migration id-less checkpoint (GOV-02 / D-12)
- [ ] Fixture: a **populated** install root (the existing pin test measures on a near-empty fixture where `CardsFile`/`DigestsFile` validate a `[]` — the exact vacuity trap D-04 exists to prevent)
- [ ] No framework install needed — pytest 9.0.3 present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SPA renders events from the canonical emitter shape | VFIX-01 / D-17 | The SPA reader change is verified by contract test at the data layer; visual confirmation that the events list still renders is not automated in this phase (no browser harness until Phase 22) | Run `views generate` against `test-ws/my-construct`, serve `views/build/`, confirm the events list is non-empty and rows show actor/action |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s on the quick run
- [ ] 532-test baseline captured before Wave 1 (D-05 prerequisite)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
