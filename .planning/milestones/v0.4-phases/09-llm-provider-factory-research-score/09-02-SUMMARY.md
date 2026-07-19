---
phase: 09-llm-provider-factory-research-score
plan: 02
subsystem: llm
tags: [research-score, scored-finding, governance-clamp, langchain, structured-output, taxonomy-steering]

requires:
  - phase: 09-llm-provider-factory-research-score
    provides: build_chat_model factory seam (Plan 01) + shared monkeypatch on construct.llm.factory.build_chat_model
  - phase: 08-search-provider-spine-contract-foundation
    provides: normalized SearchResult/SearchBatchOutput input contract
provides:
  - ScoredFinding / ResearchScoreInput / ResearchScoreGateOutput / L3 GateMetadata (defined in gate module)
  - clamp_action deterministic ceiling-clamp (D-05)
  - score_one single-result scoring with json_schema structured output via factory seam
  - read-only governance + taxonomy loaders (load_governance_thresholds, load_taxonomy_categories)
  - retrieval_echo / build_gate_output threshold echo (D-06)
  - GateConfig.concurrency_cap field + research.score config.yaml gate entry (cap consumed by Plan 03)
  - Wave 0 test infra: ConfigurableStructuredMock, InvalidOutputMock, TotalOutageMock, sample_search_results fixture
affects: [09-03, 09-04, research.score, research.run]

tech-stack:
  added: []
  patterns:
    - "Gate I/O + structured-output models defined in the gate module to avoid catalog circular import"
    - "Deterministic governance ceiling-clamp post-LLM (one-way ratchet toward conservatism)"
    - "score_one takes an already-built llm for offline testability; factory seam (build_scoring_llm) reserved for the Plan 03 runner"

key-files:
  created:
    - src/construct/llm/research_score.py
    - tests/llm/test_research_score.py
  modified:
    - src/construct/llm/config.py
    - src/construct/llm/config.yaml
    - tests/llm/conftest.py

key-decisions:
  - "key_findings cleared on clamp-to-skip with clamp rationale appended to reasoning (resolves D-14 note / Pitfall 5)"
  - "GovernanceThresholds dataclass decouples score_one + clamp from full GovernanceConfig and carries the D-06 echo fields"
  - "score_one accepts a pre-built llm (mock-injectable); build_scoring_llm holds the factory.build_chat_model seam for Plan 03"
  - "Plan 03/04 tests authored as skipped stubs (invalid-output, total-outage, fan-out, registry parity) so later waves fill bodies"

patterns-established:
  - "Configurable structured-output mock returns a caller-supplied ScoredFinding-shaped object; prompt_text() exposes captured prompt for D-11 assertions"
  - "Coupled edit: a new GateConfig field and its config.yaml key land in the same commit (extra=forbid rejects unknown keys otherwise)"

requirements-completed: [RSCH-01]

duration: 20min
completed: 2026-06-28
---

# Phase 9 Plan 02: research.score Single-Result Scoring Core Summary

**Governance-aware single-result scoring: a normalized SearchResult becomes a validated, ceiling-clamped ScoredFinding with thresholds echoed (D-06) and workspace taxonomy soft-injected (D-11) — read-only, offline-testable via mock LLM.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 complete
- **Files created:** 2 / **modified:** 3

## Accomplishments

- `ScoredFinding`, `ResearchScoreInput`, `ResearchScoreGateOutput`, and L3 `GateMetadata` defined in the gate module (circular-import avoidance)
- `clamp_action` enforces governance deterministically (D-05): caps at `skip` below relevance_threshold, at `ref_only` below card_creation_threshold, never promotes a more permissive action
- `score_one` builds the threshold+taxonomy prompt, calls `with_structured_output(ScoredFinding, method="json_schema")` through the Plan 01 factory seam, then post-clamps and clears `key_findings` on clamp-to-skip (D-14)
- Read-only governance + taxonomy loaders (D-12) and `retrieval_echo`/`build_gate_output` threshold echo (D-06)
- `GateConfig.concurrency_cap` (default 5) + `research.score` config.yaml gate entry (cap consumed by Plan 03)
- Wave 0 test infra: configurable structured-output mock, invalid-output mock, total-outage mock, and Phase-8 `sample_search_results` fixture shared with Plan 03

## Task Commits

1. **Task 1: Wave 0 test infra — mocks, fixtures, config cap + gate entry** — `5b0a417` (test) [TDD RED gate]
2. **Task 2: research_score.py — schemas, scoring, clamp, loaders, echo** — `de1a8a4` (feat) [TDD GREEN gate]

**Plan metadata:** (this commit) `docs(09-02)`

## Files Created/Modified

- `src/construct/llm/research_score.py` — gate models, clamp_action, score_one, governance/taxonomy loaders, threshold echo, build_scoring_llm seam
- `tests/llm/test_research_score.py` — real clamp/score_one/threshold/taxonomy/key_findings tests + Plan 03/04 skipped stubs
- `src/construct/llm/config.py` — `GateConfig.concurrency_cap` field + `research.score` default gate
- `src/construct/llm/config.yaml` — `research.score` gate block (provider/temperature/review_required/concurrency_cap)
- `tests/llm/conftest.py` — three new mocks + `make_build_chat_model` seam + `sample_search_results` fixture

## Decisions Made

- Cleared `key_findings` and appended clamp rationale to `reasoning` when an action is clamped to `skip` (D-14 note resolved in favor of consistency / Pitfall 5).
- Introduced a small `GovernanceThresholds` dataclass rather than threading the full `GovernanceConfig`, keeping `clamp`/`score_one` and their tests decoupled while still carrying the D-06 echo fields.
- `score_one` receives an already-built `llm` so it is directly mock-injectable; the `factory.build_chat_model` seam lives in `build_scoring_llm` for the Plan 03 runner to call.

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- RED: `5b0a417` `test(09-02)` — tests authored before `research_score.py` existed (collection failed with `ModuleNotFoundError`, the expected RED).
- GREEN: `de1a8a4` `feat(09-02)` — implementation makes the clamp/score_one/threshold/taxonomy/key_findings tests pass.
- REFACTOR: none required (implementation clean on first pass).

## Issues Encountered

None.

## Known Stubs

The Plan 03/04 tests in `tests/llm/test_research_score.py` are intentionally `@pytest.mark.skip` placeholders (invalid-output degrade D-08, total-outage promotion D-09, full fan-out D-04, registry CLI/MCP parity D-13). They are named so later waves fill the bodies; the fan-out/retry/run_gate runner is explicitly out of Plan 02 scope.

## User Setup Required

None - no external service configuration required (offline mock covers all tests; OpenAI extra unaffected).

## Next Phase Readiness

- Plan 03 can compose `score_one` + `load_governance_thresholds` + `load_taxonomy_categories` + `build_scoring_llm` + `build_gate_output` into the bounded `ThreadPoolExecutor` fan-out with per-item retry (D-08) and total-outage promotion (D-09), using the already-present mocks.
- `GateConfig.concurrency_cap` is in place for the Plan 03 runner.

## Self-Check: PASSED

- `src/construct/llm/research_score.py` — FOUND
- `tests/llm/test_research_score.py` — FOUND
- Commit `5b0a417` — FOUND
- Commit `de1a8a4` — FOUND
- Full suite: 273 passed, 4 skipped (baseline preserved; no regressions)

---
*Phase: 09-llm-provider-factory-research-score*
*Completed: 2026-06-28*
