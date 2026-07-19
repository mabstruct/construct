# Phase 9: LLM Provider Factory + research.score - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers two things:

1. **A model-agnostic LLM provider factory** — a `config.yaml`-driven factory that constructs a chat model from a provider key, removing hardcoded `ChatAnthropic(...)` calls from graph nodes (closes the anti-pattern flagged at `spec-v04-agentworkflows.md` line 546).
2. **The `research.score` L3 gate capability** — takes a normalized `SearchResult` list (from the Phase 8 search spine) and produces structured `ScoredFinding` proposals (`relevance_score`, `source_tier`, `key_findings`, `content_categories`, `ingest_action` ∈ {skip, ref_only, ref_and_card}, `reasoning`), governed by `governance.yaml` thresholds, exposed on **both CLI + MCP** via the capability registry, verifiable offline with mock LLM providers.

**Hard boundary — NO workspace writes.** `research.score` produces proposals only. Deduplication, human review, approved ingest, digests, seed updates, and events all belong to `research.run` (Phase 10). The score gate is a pure read-only scoring function (it reads workspace taxonomy for steering, writes nothing).

Requirements: **RSCH-01** (1 requirement).

</domain>

<decisions>
## Implementation Decisions

### LLM Provider Factory
- **D-01:** Build a `config.yaml`-driven provider factory **and retrofit `src/construct/llm/ask_domain.py`** to use it, replacing the hardcoded `ChatAnthropic(...)` at `ask_domain.py:228`. One consistent provider path across gates; pays off the spec-line-546 anti-pattern now. (Accept the ask.domain regression-test surface as part of this phase.)
- **D-02:** Wire **Anthropic + OpenAI + Mock** concretely to prove cross-vendor swap end-to-end. `langchain_anthropic` is already a dependency; add `langchain_openai` as an **optional extra** (mirrors Phase 8's Tavily-as-optional-dependency decision so a base install stays lean). The mock/fake LLM is the offline test oracle.
- **D-03:** Factory is keyed off the existing `llm/config.yaml` provider records (`ProviderConfig.type` → concrete chat model). A `research.score` gate entry is added to `config.yaml` `gates` (tier L3) alongside the existing `ask.domain` gate.

### Scoring Strategy
- **D-04:** **Per-result** structured-output LLM calls (one finding scored per call), run **concurrently with a configurable cap**. Per-item error isolation (a bad/invalid output only loses that finding) while recovering most batch throughput. Cap is configurable (llm/gate config).

### ingest_action Authority
- **D-05:** **The LLM chooses `ingest_action`** (nuanced — can weigh source quality + relevance together), with governance thresholds injected into the prompt. **Python then ceiling-clamps** the action against the score-vs-threshold band so the LLM can never be *more permissive* than governance allows (it may be more conservative): `score < relevance_threshold` caps at `skip`; `score < card_creation_threshold` caps at `ref_only`; otherwise `ref_and_card` is permitted.
- **D-06:** Governance thresholds (`relevance_threshold`, `card_creation_threshold`, `max_papers_per_cycle`) are **echoed in the gate metadata / retrieval block** so success criterion 3 ("thresholds reflected in recommendations") is provable and testable offline.

### source_tier Derivation
- **D-07:** **The LLM judges `source_tier` (1-5)** from the URL + content as part of its structured output. No domain→tier map to maintain; handles unknown sources. (Accept non-determinism; offline tests control output via the mock LLM.)

### Degraded-State Handling
- **D-08:** On an individual result's scoring failure (invalid/unparseable structured output, provider error, timeout): **retry once**, then on continued failure mark it as a `skip` finding with `reasoning: "scoring_failed: <cause>"`, increment retrieval error/retried counters, and set a gate-level `degraded` flag — the gate **still completes** with partial good findings. Aligns with per-result isolation (D-04).
- **D-09 (planner guidance):** A *total* provider outage (every item failing — e.g. auth/config error) should surface as a **gate-level degraded error**, NOT an all-`skip` "success." Distinguish per-item degradation from whole-provider failure.

### Input Plumbing
- **D-10:** `research.score` **accepts a pre-fetched normalized `SearchResults` payload** (file path / stdin / param produced by a prior `research.search`). It does **not** run search itself — it stays a pure scoring gate. Phase 10's `research.run` owns the search→score composition. Keeps the seam clean and avoids duplicating Phase 10 logic.

### content_categories Source
- **D-11:** **Soft workspace-taxonomy steering** — the gate loads the workspace taxonomy (`taxonomy_seeds` / existing card `content_categories`) into the prompt and asks the LLM to *prefer* those categories while allowing new ones when nothing fits. Aligns findings with downstream Phase 10 card creation without suppressing emergent themes.
- **D-12 (contract note):** Because of D-11, `research.score` input **requires a `workspace_path`** to load taxonomy (read-only). This does not violate the no-writes boundary.

### CLI/MCP Result Shape
- **D-13:** The canonical `ResearchScoreGateOutput` (findings + gate metadata + retrieval counts) is the **JSON contract** for MCP and CLI `--json`. The **CLI default additionally prints a human-readable summary table** (url, score, tier, action) plus a degraded/retried notice. Both surfaces share the same underlying structured object (registry parity preserved).

### key_findings Extraction
- **D-14:** LLM extracts **up to 5 `key_findings`, but only for non-`skip` findings**; skipped items get `[]`. Keeps output focused on results that matter for ingest and reduces prompt/output noise on rejects. (Note: a finding clamped to `skip` by D-05 may retain `key_findings` from the LLM; the `reasoning` field carries the rationale — planner to decide whether to clear them on clamp-to-skip.)

### Claude's Discretion
- Scorer system/user prompt wording and structure.
- Exact concurrency cap default value and where it lives in config.
- LangGraph topology for the per-result fan-out (single fan-out node vs. mapped subgraph) — provided it preserves per-item isolation (D-04) and degraded handling (D-08).
- Whether `key_findings` are cleared when an LLM action is clamped down to `skip` (D-14 note).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 9 goal + 4 success criteria; phase sequencing (Phases 8–13).
- `.planning/REQUIREMENTS.md` — RSCH-01 requirement text (line 22).
- `.planning/PROJECT.md` — v0.4 milestone scope, constraints, and product-continuity constraints.

### Specification (primary)
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — Baseline v0.4 spec. Key sections:
  - §6.3 (lines 262–284) — `ScoredFinding` / `ResearchScoreGateOutput` schemas; thresholds from `governance.yaml`.
  - Line 240, 249 — `SearchResult.provider_score`; Tavily field mapping (input shape from Phase 8).
  - Line 479 — `research.score` capability surface (CLI `construct research score`, MCP `construct_research_score`, tier L3, P1).
  - Line 503 — target module paths (`src/construct/llm/research_score.py`).
  - Line 546 — **LLM provider swap / factory-pattern requirement** (the retrofit driver for D-01).
  - §6.6 / line 321 — `research_score_gate_complete` event (logged by Phase 10's run, not here).
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Layer model + LLM tier definitions (L1/L2/L3); informs L3 gate posture.

### Primary code references (patterns to follow)
- `src/construct/llm/ask_domain.py` — Closest analog: LangGraph gate with structured output + `GateMetadata` + `run_gate()` runner. **This is the file being retrofitted (D-01); reuse its `GateMetadata` pattern per spec §6.3.**
- `src/construct/llm/config.py` — `LlmConfig` / `ProviderConfig` / `GateConfig` loader; the factory builds on this.
- `src/construct/llm/config.yaml` — Provider + gate config (add OpenAI provider + `research.score` gate entry).
- `tests/llm/conftest.py` — `MockChatAnthropic` / monkeypatch mock pattern; extend for the score gate's offline tests + invalid-output fixtures.
- `src/construct/search/` (Phase 8) — `SearchResult` schema and result contract that feeds `research.score` input.
- `src/construct/capabilities/catalog.py` + `registry.py` — Capability registration (handler + input/output models) for CLI/MCP auto-exposure.
- `src/construct/cli.py` — Typer command group pattern (`construct research score`).
- `src/construct/mcp/server.py` — MCP auto-discovery from the registry.

### Governance / config
- `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml` — `research:` block: `relevance_threshold` (0.3), `card_creation_threshold` (0.6), `max_papers_per_cycle` (50). Source of the D-05 clamp bands and D-06 echo.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ask_domain.py` gate skeleton** (`run_gate()`, LangGraph builder, `with_structured_output(method="json_schema")`, `GateMetadata`, retrieval-counts pattern, exact-match cache) — directly templatable for `research_score.py`.
- **`tests/llm/conftest.py` `MockChatAnthropic`** — monkeypatch-on-module-symbol mock; extend with a configurable/fake structured-output mock and invalid-output fixtures for offline degraded-state tests (success criterion 4).
- **Phase 8 `SearchResult` + mock search fixtures** — provide the realistic input payloads for `research.score` tests without live providers.
- **`llm/config.py` loader** — already resolves provider/gate config with env override; the factory slots in here.

### Established Patterns
- **Gate I/O models defined in the gate module** (not `catalog.py`) to avoid circular imports — same constraint applies to `ScoredFinding` / `ResearchScoreGateOutput` (cf. ask.domain decision in STATE.md, and Phase 05-02 circular-import note).
- **Registry auto-exposure → CLI + MCP parity for free** (Phase 8 #5); `research.score` follows it.
- **Structured-output via `with_structured_output(..., method="json_schema")`** (ask_domain.py:233) — no tool-choice conflicts.
- **Fail-loud, no silent fallback** on LLM errors (ask_domain.py:255) — D-08 retry-then-skip-with-reason extends this for per-item isolation.

### Integration Points
- New: `src/construct/llm/factory.py` (provider factory) + `src/construct/llm/research_score.py` (gate) per spec line 503.
- Modify: `src/construct/llm/ask_domain.py` (retrofit to factory), `src/construct/llm/config.yaml` (OpenAI provider + research.score gate), `src/construct/capabilities/catalog.py` (register `research.score`), `src/construct/cli.py` (`research score` command + table renderer), `pyproject.toml` (`langchain_openai` optional extra).
- Input contract bridges to Phase 8 `search/` (`SearchResult`) and reads workspace taxonomy via `WorkspaceLoader` (D-12).

</code_context>

<specifics>
## Specific Ideas

- CLI summary table columns: `url`, `score`, `tier`, `action`, with a trailing degraded/retried notice line (D-13).
- `ingest_action` clamp is a one-way ratchet toward conservatism: LLM nuance, governance ceiling (D-05).
- Distinguish per-item degradation (skip + reason) from total provider outage (gate-level error) (D-08/D-09).

</specifics>

<deferred>
## Deferred Ideas

- **OpenAI/other providers as full first-class supported paths** — this phase wires OpenAI to *prove* swap; broader provider catalog hardening is future work.
- **Deterministic source_tier domain map** (considered, rejected for D-07) — could be revisited if LLM tier drift causes downstream promotion-gate instability in Phase 11/12.
- **Strict taxonomy enforcement / category reconciliation** (considered, rejected for D-11 soft-steering) — Phase 10 card creation may later need a reconciliation step if emergent categories proliferate.
- **research.score running search inline** (rejected, D-10) — that composition is explicitly Phase 10 `research.run`.
- **Score-gate result caching** — out of scope; revisit if scoring cost becomes a concern.

None of these are in Phase 9 scope.

</deferred>

---

*Phase: 9-LLM Provider Factory + research.score*
*Context gathered: 2026-06-26*
