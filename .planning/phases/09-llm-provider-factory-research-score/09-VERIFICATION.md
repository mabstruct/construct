---
phase: 09-llm-provider-factory-research-score
verified: 2026-06-28T00:00:00Z
status: passed
score: 21/21 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 9: LLM Provider Factory + research.score Verification Report

**Phase Goal:** LLM Provider Factory + research.score — model-agnostic structured scoring that turns normalized search results into governed finding proposals. Expose research.score on both CLI and stdio MCP through the shared capability registry.
**Verified:** 2026-06-28
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Both ask.domain and research.score construct chat models through one factory.build_chat_model path (D-01) | VERIFIED | `ask_domain.py:232` calls `factory.build_chat_model(provider_cfg, temperature=0.2)`; `research_score.py:188` routes through `build_scoring_llm -> factory.build_chat_model`; all tests monkeypatch `construct.llm.factory.build_chat_model` as the single seam |
| 2 | factory.build_chat_model maps ProviderConfig.type to concrete ChatModel for langchain_anthropic and langchain_openai (D-03) | VERIFIED | `factory.py:34-56`: two branches, langchain_anthropic returns ChatAnthropic, langchain_openai lazy-imports ChatOpenAI with ImportError catch |
| 3 | Missing/unknown provider raises a clear GATE_PROVIDER_ERROR (D-02) | VERIFIED | `factory.py:47-50`: GATE_PROVIDER_ERROR for missing llm-openai extra; `factory.py:58`: GATE_PROVIDER_ERROR for unknown type; 4 tests in test_factory.py assert these |
| 4 | ask.domain behaves identically after the retrofit (no regression) | VERIFIED | `grep "ChatAnthropic(" ask_domain.py` returns nothing; `grep "construct.llm.ask_domain.ChatAnthropic" tests/` returns nothing; 289 tests pass |
| 5 | A single normalized SearchResult is scored into a ScoredFinding with relevance_score, source_tier, ingest_action, reasoning, key_findings, content_categories | VERIFIED | `research_score.py:43-61` ScoredFinding class with all required fields and validation ranges |
| 6 | Python deterministically ceiling-clamps ingest_action against governance bands (D-05/D-07) | VERIFIED | `research_score.py:161-176` clamp_action: score < relevance_threshold → "skip"; score < card_creation_threshold → "ref_only" if not skip; LLM conservatism preserved |
| 7 | Governance thresholds (relevance, card_creation, max_papers) are echoed in the gate output so they are provable offline (D-06) | VERIFIED | `research_score.py:123-129` retrieval_echo; `build_gate_output:305-312` includes thresholds; retrieval dict in ResearchScoreGateOutput |
| 8 | Workspace taxonomy categories are loaded read-only and injected into the prompt (D-11/D-12) | VERIFIED | `research_score.py:135-155` load_taxonomy_categories (no writes); `_build_messages:206-236` injects taxonomy_block into system message |
| 9 | Skip findings carry key_findings == [] after the clamp (D-14) | VERIFIED | `research_score.py:274-281`: when final_action == "skip", key_findings cleared and clamp rationale appended to reasoning |
| 10 | A list of SearchResults is scored concurrently with a configurable cap (D-04) | VERIFIED | `research_score.py:451`: `ThreadPoolExecutor(max_workers=workers)` where `workers = max(1, min(cap, len(results)))` |
| 11 | An individual scoring failure retries once, then becomes a skip finding with reasoning 'scoring_failed: <cause>' (D-08) | VERIFIED | `research_score.py:368-396` _score_one_with_retry: 2 attempts; `_skip_finding_for_failure:354-365` builds finding with `reasoning=f"scoring_failed: {safe_cause}"` |
| 12 | A total provider outage surfaces as a gate-level degraded ERROR, not an all-skip success (D-09) | VERIFIED | `research_score.py:467-482`: when `scored_ok==0 and provider_failures==len(results)`, returns ScoreAllResult with `total_outage=True`; `run_gate:524-527` raises ResearchScoreOutageError |
| 13 | Degraded/outage error messages never leak provider API keys (T-09-03) | VERIFIED | `research_score.py:346-351` _safe_scoring_cause: returns class name + safe message only; provider outage returns "provider authentication or configuration error" string |
| 14 | run_gate returns a ResearchScoreGateOutput with findings + gate metadata + retrieval counts, and writes nothing to the workspace | VERIFIED | `research_score.py:497-545` run_gate assembles ResearchScoreGateOutput; `grep "open(\|write_text\|\.write(\|mkdir" research_score.py` returns nothing |
| 15 | research.score is registered in the shared capability registry with input/output models, a CLI name, and an MCP tool name | VERIFIED | `catalog.py:371-380`: CapabilityRecord with id="research.score", input_model=ResearchScoreInput, output_model=OperationResult, cli_name="research.score", mcp_tool_name="construct_research_score" |
| 16 | User can run `construct research score` from the CLI with a pre-fetched SearchResults payload (--results-file / stdin) and a required --workspace (D-10) | VERIFIED | `cli.py:506-553` research_score_cmd: `--workspace` required (positional Option `...`), `--results-file` or stdin fallback, `_load_search_results_json` + `_flatten_search_results_payload` |
| 17 | The CLI default prints a human-readable table (url, score, tier, action) plus a degraded/retried notice; --json emits the canonical ResearchScoreGateOutput (D-13) | VERIFIED | `cli.py:488-503` _render_research_score_table renders header + rows + degraded notice; `--json` path calls `_display_result(result, json_output=True)` which emits canonical JSON; contract test asserts "url\tscore\ttier\taction" in output |
| 18 | The MCP tool construct_research_score and the CLI return the same underlying structured object (registry parity) | VERIFIED | `test_research_score_cli_mcp.py:92-124` test_cli_json_matches_registry_handler_data asserts `cli_payload["data"] == handler_result.data`; MCP auto-discovery confirmed: `construct_research_score` in `registry.list_mcp_tools()` |
| 19 | A total provider outage maps to a failed OperationResult (success=False), not an all-skip success | VERIFIED | `catalog.py:408-412` catches ResearchScoreOutageError and returns `OperationResult(success=False, ...)`; `cli.py:192-193` _display_result raises Exit(code=1) on success=False; test asserts exit_code != 0 |
| 20 | The full test suite stays green at or above the 253-test baseline | VERIFIED | 289 passed, 0 failed, 0 skipped, 0 xfailed |
| 21 | RSCH-01: User can run research.score through the CONSTRUCT CLI/MCP surface to convert normalized search results into structured, governance-aware finding proposals with relevance, source tier, ingest action, and reasoning | VERIFIED | All surfaces wired: CLI (construct research score), MCP (construct_research_score via registry auto-discovery), and direct capability handler — all return ResearchScoreGateOutput-backed OperationResult with governance thresholds echoed |

**Score:** 21/21 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/construct/llm/factory.py` | build_chat_model(cfg: ProviderConfig, *, temperature) -> ChatModel | VERIFIED | 58 lines; `def build_chat_model` present; GATE_PROVIDER_ERROR at 2 sites; no `init_chat_model` |
| `src/construct/llm/research_score.py` | ScoredFinding, ResearchScoreGateOutput, ResearchScoreInput, GateMetadata(L3), score_one(), clamp_action(), governance+taxonomy loaders, score_all(), run_gate() | VERIFIED | 545 lines; all classes/functions present and substantive |
| `src/construct/llm/config.py` | GateConfig.concurrency_cap field | VERIFIED | `concurrency_cap: int = 5` at line 28; "research.score": GateConfig() in default gates at line 41 |
| `src/construct/llm/config.yaml` | research.score gate entry with concurrency_cap | VERIFIED | research.score block at line 26; concurrency_cap: 5 at line 30 |
| `src/construct/capabilities/catalog.py` | research.score CapabilityRecord + _research_score_shim | VERIFIED | Lines 371-380 registration; lines 401-422 _research_score_shim with outage->success=False mapping |
| `src/construct/cli.py` | research score subcommand + table renderer + batch flattening | VERIFIED | research_score_cmd at line 506; _render_research_score_table at line 488; _flatten_search_results_payload at line 451 |
| `pyproject.toml` | llm-openai optional extra | VERIFIED | `llm-openai = ["langchain-openai>=1.2,<2"]` at line 25 |
| `tests/llm/test_factory.py` | Factory type-map, lazy-import error, unknown-provider error tests | VERIFIED | 4 test functions covering all branches |
| `tests/llm/test_research_score.py` | Scoring, clamp, threshold-echo, taxonomy, fan-out, retry, outage tests | VERIFIED | Substantive tests; no remaining stubs/skips |
| `tests/llm/test_research_score_capability.py` | Registration + shim happy/total-outage tests | VERIFIED | 3 tests pass including outage->success=False |
| `tests/contract/test_research_score_cli_mcp.py` | MCP tool list, CLI table render, CLI/registry parity, outage exits nonzero | VERIFIED | 4 tests all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ask_domain.py` | `factory.build_chat_model` | `factory.build_chat_model(provider_cfg, temperature=0.2)` at line 232 | WIRED | Old ChatAnthropic(…) construction gone; factory seam present |
| `research_score.py` | `construct.llm.factory.build_chat_model` | `factory.build_chat_model(provider_cfg, temperature=gate_cfg.temperature)` via build_scoring_llm | WIRED | Module-level `from construct.llm import factory`; method at line 188 |
| `research_score.py` | WorkspaceLoader (read-only) | `load_governance_thresholds` and `load_taxonomy_categories` use `WorkspaceLoader(workspace_path).load_governance()` / `.load_domains_registry()` | WIRED | No write calls; grep confirms |
| `research_score.py` | `ThreadPoolExecutor` | `with ThreadPoolExecutor(max_workers=workers)` at line 451 | WIRED | Bounded fan-out; no asyncio.gather |
| `catalog.py _research_score_shim` | `research_score_gate("research.score", input_data)` | Calls run_gate, catches ResearchScoreOutageError, wraps in OperationResult | WIRED | Lines 407-422 |
| `cli.py research_score_cmd` | registry `research.score` handler | `get_registry().get("research.score").handler(**handler_kwargs)` at line 540 | WIRED | KeyError guard at line 537 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `research_score.py ResearchScoreGateOutput` | `findings: list[ScoredFinding]` | `score_all -> score_one -> llm.with_structured_output(ScoredFinding).invoke(messages)` — real SearchResult data injected into prompt | Yes (tests confirm mock returns actual ScoredFinding objects, not empty lists) | FLOWING |
| `catalog.py _research_score_shim` | `result.data` | `output.model_dump(mode="json")` from ResearchScoreGateOutput | Yes — fully populated from run_gate | FLOWING |
| `cli.py research_score_cmd` | `result.data["findings"]` | Via registry handler -> shim -> run_gate | Yes — same data path | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Registry resolves research.score with correct IDs | `get_registry().get("research.score")` assertions | id=research.score, cli_name=research.score, mcp_tool_name=construct_research_score | PASS |
| construct_research_score in MCP tool list | `get_registry().list_mcp_tools()` | Present in 13-item tool list | PASS |
| Config loads research.score gate with concurrency_cap=5 | `load_llm_config(); gates["research.score"].concurrency_cap` | 5 | PASS |
| Full suite green | `./.venv/bin/python -m pytest -q` | 289 passed, 0 failed, 0 skipped, 3 warnings | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RSCH-01 | 09-01, 09-02, 09-03, 09-04 | User can run research.score through the CONSTRUCT CLI/MCP surface to convert normalized search results into structured, governance-aware finding proposals | SATISFIED | CLI: `construct research score`; MCP: `construct_research_score` auto-discovered; findings include relevance_score, source_tier, ingest_action, reasoning; governance thresholds echoed; REQUIREMENTS.md marks RSCH-01 as `[x] Complete` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none in phase 9 modified files) | — | — | — | No TBD/FIXME/XXX debt markers found in factory.py, research_score.py, catalog.py, cli.py |

### Human Verification Required

None. All observable behaviors are covered by automated tests:
- Table rendering verified by CLI contract test asserting on captured stdout
- Outage->non-zero exit verified by test asserting exit_code != 0
- CLI/MCP parity verified by byte-equality assertion on `data` field
- Governance clamp verified by unit tests at all three bands
- Key-safety verified by sanitization unit tests

### Gaps Summary

No gaps. All 21 must-haves verified at all four levels (exists, substantive, wired, data-flowing). RSCH-01 satisfied. Full suite at 289 passed (above 253 baseline).

---

_Verified: 2026-06-28_
_Verifier: Claude (gsd-verifier)_
