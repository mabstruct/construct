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
| T3 | 18-05 | 2 | VFIX-01 | T-18-22 | generate→validate round-trips on a **populated** root; every generated slot passes; record lists non-empty; file cardinality matches `4 + 6·N + 1` (D-19) | integration | `.venv/bin/python -m pytest tests/integration/test_views_generate.py -x` | ✅ (guard **replaces** `:285`) | ⬜ pending |
| T1 | 18-04 | 1 | VFIX-01 | T-18-19 | conformed models still reject a genuinely malformed payload — `extra="ignore"` (D-03) did not become "accept anything" | contract | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py -x` | ✅ | ⬜ pending |
| T2 | 18-04 | 1 | VFIX-01 / D-17 | T-18-17 | `events.json` validates against the canonical Python-emitter shape | contract | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py -k events -x` | ✅ (extend) | ⬜ pending |
| T2 | 18-05 | 2 | VFIX-01 / D-17 | T-18-17 | the SPA activity reader consumes that same canonical shape | contract | `grep -c 'subject' .../components/ActivityList.jsx` returns 0 and the six canonical accessors are present | ✅ | ⬜ pending |
| T1 | 18-04 | 1 | VFIX-01 / D-18 | — | `<ws>/stats.json` and `<ws>/curation-history.json` have contract models | contract | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py -x` | ✅ (extend) | ⬜ pending |
| T1+T3 | 18-05 | 2 | VFIX-01 / D-18 | T-18-21 | both files are inside the shared contract table and inside the round-trip guard's count | integration | `.venv/bin/python -m pytest tests/integration/test_views_generate.py -x` | ✅ | ⬜ pending |
| T3 | 18-04 | 1 | VFIX-01 / D-20 | T-18-18 | `DigestRecord`'s **write** path (`research_run.py:644`) conforms with the model rename, and a pre-change `digests/digests.json` migrates on read | llm | `.venv/bin/python -m pytest tests/llm/test_research_run.py -k digest -x` | ✅ (extend) | ⬜ pending |
| T1 | 18-01 | 1 | GOV-01 | T-18-01 | same `(capability, payload)` → identical result on real CLI process and real MCP dispatch | integration | `.venv/bin/python -m pytest tests/integration/test_surface_parity.py -x` | ❌ W0 | ⬜ pending |
| T2 | 18-01 | 1 | GOV-01 | T-18-01 | an unknown field is rejected on **both** surfaces with the same reason | integration | same file | ❌ W0 | ⬜ pending |
| T1+T2 | 18-02 | 2 | GOV-01 | T-18-12 | every registered capability's model fields bind to its handler (research Finding G3 audit, as a permanent guard) | contract | `.venv/bin/python -m pytest tests/contract/test_capability_seam.py -x` | ❌ W0 | ⬜ pending |
| T1 | 18-02 | 2 | GOV-01 / D-06 | T-18-02 | every input model carries `extra="forbid"` — cardinality equal to registry size, not membership | contract | same file | ❌ W0 | ⬜ pending |
| T2 | 18-03 | 3 | GOV-01 | T-18-01 | no module outside the capabilities package reaches a handler directly (directory-scoped source guard) | contract | same file | ❌ W0 | ⬜ pending |
| T2 | 18-06 | 2 | GOV-02 / D-10 | T-18-03 | incomplete decision map → zero canonical writes, run still paused, uncovered ids named | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k decision -x` | ✅ (extend) | ⬜ pending |
| T1 | 18-06 | 2 | GOV-02 / D-12 | T-18-25 | legacy id-less checkpoint migrates on read and **still** requires a complete map | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k "proposal_id or migrat" -x` | ✅ (extend) | ⬜ pending |
| T3 | 18-06 | 2 | GOV-03 / D-11 | T-18-04 | resume with a stale `checkpoint_id` → rejected, zero writes; a replayed resume is also rejected | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k etag -x` | ✅ (extend) | ⬜ pending |
| T2 | 18-07 | 2 | GOV-04 / D-13 | T-18-05, T-18-28 | no canonical writer reachable outside apply nodes — repo-wide source guard by directory traversal, plus the widened per-node interrupt-only assertion | contract + llm | `.venv/bin/python -m pytest tests/contract/test_canonical_write_boundary.py tests/llm/test_research_run.py -k "boundary or interrupt_only" -x` | ❌ W0 (new file) + ✅ (extend) | ⬜ pending |
| T1 | 18-07 | 2 | GOV-04 / D-13 | T-18-29 | Streamlit app still starts with the removed page gone; its page list matches the surviving files | contract | `.venv/bin/python -m pytest tests/contract/test_canonical_write_boundary.py -x` | ❌ W0 | ⬜ pending |
| T2 | 18-08 | 4 | GOV-04 / D-16 | T-18-06 | no approval event emitted when the underlying write failed or was a no-op; approval-event count equals applied count | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k event -x` | ✅ (extend) | ⬜ pending |
| T3 | 18-08 | 4 | GOV-05 | T-18-09 | degraded run reports degraded on CLI human output, CLI `--json`, and MCP result — table-driven, one row per surface | integration | `.venv/bin/python -m pytest tests/integration/test_surface_honesty.py -x` | ❌ W0 | ⬜ pending |
| T1+T3 | 18-08 | 4 | GOV-05 / D-16 | T-18-30 | escalated items get their own event action and their own bucket on every surface, never in an applied/success count | integration + llm | `.venv/bin/python -m pytest tests/integration/test_surface_honesty.py tests/llm/test_curation_run.py -k "escalat or event" -x` | ❌ W0 | ⬜ pending |
| T3 | 18-08 | 4 | D-15 | T-18-31 | degraded `curation.run` still exits 0 — the Phase 11 contract is **preserved**, not changed; guard written before the renderer change | integration | `.venv/bin/python -m pytest tests/integration/test_surface_honesty.py -x` | ❌ W0 — **regression guard, add it** | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Each gap is owned by the plan and task named beside it; there is no separate Wave 0 pass.

- [ ] `tests/integration/test_surface_parity.py` — GOV-01 differential CLI↔MCP (needs a `subprocess` helper for the real-CLI arm, per research Pitfall 5) → **18-01 T1**, extended by **18-01 T2** and **18-03 T3**
- [ ] `tests/contract/test_capability_seam.py` — GOV-01 model↔handler binding audit + `extra="forbid"` cardinality → **18-02 T1**, extended by **18-02 T2** and **18-03 T2**
- [ ] `tests/contract/test_canonical_write_boundary.py` — GOV-04 repo-wide canonical-write guard + Streamlit page-list check → **18-07 T1/T2**
- [ ] `tests/integration/test_surface_honesty.py` — GOV-05 table-driven degraded/escalated across surfaces, plus the D-15 exit-code regression guard → **18-08 T3**
- [ ] Fixture: a `curation.run` forced degraded, and a run with an escalated item (GOV-05 needs both; neither exists today) → **18-08 T3**, built through `tests/llm/conftest.create_test_workspace` plus forcing the `status` / `escalated` state channels
- [ ] Fixture: a pre-migration id-less checkpoint (GOV-02 / D-12) → **18-06 T1**, built on `test_open_checkpointer_targets_construct`'s real-`SqliteSaver`-against-tmp_path approach
- [ ] Fixture: a **populated** install root — already exists as `_populated_install_root` / `tests/fixtures/v02/multi-domain-medium`; the replaced pin test measures on a near-empty fixture where the card and digest record models validate an empty list, which is the exact vacuity trap D-04 exists to prevent → **18-05 T3**
- [ ] Baseline: the full-suite green count captured before the first edit (D-05 prerequisite, research assumption A3) → **18-01 T1 `<precondition>`**
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
