---
phase: 07-close-v0-3-blockers-rt-03-mcp-schema-parity-ing-02-ingest-cl
verified: 2026-06-16T00:00:00Z
status: human_needed
score: 4/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Re-run /gsd:audit-milestone against the current codebase"
    expected: "0 unsatisfied requirements; the three former blockers (RT-03, ING-02, ING-05) show satisfied; RT-01/RT-02 show Partial"
    why_human: "Milestone audit is a full-stack integration check that requires human orchestration of the gsd-verifier tool and review of its JSON output — cannot be meaningfully substituted with grep or pytest"
---

# Phase 7: Close v0.3 Blockers Verification Report

**Phase Goal:** Close the three v0.3 milestone-audit blockers (RT-03 MCP schema parity, ING-02 ingest cluster validation, ING-05 graph.status wiring) so the milestone re-audits to a legitimate green close, without adding new capability.
**Verified:** 2026-06-16
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All MCP tools are invocable with their advertised schema (no TypeError); a contract test invokes each handler | VERIFIED | `test_every_mcp_handler_invokes_without_type_error` passes for all 11 tools; `test_previously_broken_tools_return_result` passes for the 5 RT-03 tools. 12/12 contract tests pass. |
| 2 | `construct ingest source` then `construct validate` passes E2E on a clean workspace and the test-ws fixtures | VERIFIED | `test_ingest_note_then_validate_passes` and `test_ingest_url_then_validate_passes` both pass; `test_fixture_not_mutated_by_run` confirms fixture integrity. Reserved clusters confirmed in both `test-ws/my-construct/search-seeds.json` and `test-ws/ping-eon/search-seeds.json`. |
| 3 | `graph.status` (CLI + MCP) returns the real graph-health report and `help.suggest` surfaces it | VERIFIED | `get_registry().get('graph.status').handler('test-ws/my-construct')` returns `success=True` with keys `['cards', 'connections', 'domains', 'workspace']`. `help.suggest` returns `graph_status` key present=True. Both positional and keyword invocation confirmed by `test_graph_status_accepts_positional_and_keyword`. `test_help_suggest_surfaces_graph_health` passes. |
| 4 | REQUIREMENTS.md traceability + SUMMARY frontmatter match audit-verified reality | VERIFIED | Zero "Pending" rows remain for audit-satisfied requirements. RT-01/RT-02 correctly show "Partial". All 8 target SUMMARYs carry `requirements_completed` frontmatter. Regex check confirms: WF-01, ING-02, ING-03, ING-04, ING-05, ING-06, RT-03, ADV-01 all show "Complete"; RT-01/RT-02 show "Partial". |
| 5 | `/gsd:audit-milestone` re-run shows 0 unsatisfied requirements | UNCERTAIN (human needed) | Cannot run the full milestone audit programmatically. Static evidence strongly supports 0 unsatisfied: the three former blockers are verified closed, traceability records reconciled. Requires human re-run to confirm. |

**Score:** 4/5 truths verified (1 requires human confirmation)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/construct/capabilities/catalog.py` | Dual-mode shims for 5 RT-03 tools + graph.status wired | VERIFIED | `_validate_shim`, `_create_card_shim`, `_edit_card_shim`, `_add_connection_shim`, `_ingest_source_shim` all present. `graph_status` imported and wired at line 262. |
| `tests/contract/test_mcp_contracts.py` | Handler-invocation contract test (D-08.1) | VERIFIED | File contains `test_every_mcp_handler_invokes_without_type_error` iterating `list_mcp_tools()` and calling `capability.handler(**payload)`. Pattern `handler(` confirmed. 12 tests, all passing. |
| `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json` | Reserved manual-ingest and web-ingest clusters | VERIFIED | Both clusters present with `id: "manual-ingest"` and `id: "web-ingest"`, `domain: "ingest"` (placeholder, rewritten at init), `status: "active"`. |
| `test-ws/my-construct/search-seeds.json` | Backfilled reserved clusters | VERIFIED | Contains `manual-ingest` (domain: cosmology) and `web-ingest` (domain: cosmology) alongside existing domain clusters. |
| `test-ws/ping-eon/search-seeds.json` | Backfilled reserved clusters | VERIFIED | Contains `manual-ingest` (domain: api-gateways) and `web-ingest` (domain: api-gateways) alongside existing cluster. |
| `tests/integration/test_ingest_validate_e2e.py` | ING-02 E2E audit repro (now green) | VERIFIED | 3 tests: note ingest, URL ingest, fixture-not-mutated guard. All passing. |
| `src/construct/services/init.py` | Reserved cluster seeding + research_seeds append | VERIFIED | `_write_search_seeds` rewrites placeholder domain to workspace domain and appends research-seed cluster rather than replacing reserved clusters. |
| `src/construct/services/help.py` | Correct `clusters` key + `_RESERVED_INGEST_CLUSTERS` filter | VERIFIED | `_RESERVED_INGEST_CLUSTERS = frozenset({"manual-ingest", "web-ingest"})` at line 18. `seeds.get("clusters", [])` at line 90 (was `"search_clusters"`). Aggregates `last_queried` across non-reserved clusters. |
| `.planning/REQUIREMENTS.md` | Reconciled traceability + checkbox list | VERIFIED | 26 Complete, 2 Partial, 0 Pending. Checkboxes consistent with table. |
| Phase 3/5/6 SUMMARYs (8 files) | `requirements_completed` frontmatter | VERIFIED | All 8 files carry the field: 03-01 [RT-01], 03-02 [RT-01, RT-02], 03-03 [RT-03], 05-01 [ING-06], 05-02 [ADV-01], 05-03 [ADV-02], 06-02 [ADV-04], 06-04 [SPK-02, SPK-03]. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `catalog.py graph.status handler` | `graph_status.py graph_status()` | `lambda workspace: graph_status(workspace)` | WIRED | Import confirmed at line 27; handler at line 262 invokes it. Confirmed returning success=True with real data. |
| `help.py` | `graph.status` capability handler | `cap.handler(workspace_id)` positional call, result.data assigned to `graph_data` | WIRED | Lines 140-143: `cap = registry_caps.get("graph.status"); graph_result = cap.handler(workspace_id); if graph_result.success: graph_data = graph_result.data`. `health["graph_status"] = graph_data` at line 184. |
| `ingestion.py search_cluster fallbacks` | `search-seeds.json reserved clusters` | Reserved clusters seeded at init; backfilled in fixtures | WIRED | `manual-ingest`/`web-ingest` present in all three fixture files; E2E test confirms the chain end-to-end. |
| `validation.py:205 cluster-membership rule` | Seeded reserved clusters | `ingested ref.search_cluster in search_cluster_ids` | WIRED | Validation unchanged; fixtures carry the clusters; E2E test proves zero validation errors after ingest. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `catalog.py` graph.status handler | `graph_status()` return value | `src/construct/pipelines/graph_status.py` — reads workspace cards/connections/domains files | Yes — returns dict with `cards`, `connections`, `domains`, `workspace` keys populated from real workspace data | FLOWING |
| `help.py` `health["graph_status"]` | `graph_data` from `graph_result.data` | Registry handler call → `graph_status()` pipeline | Yes — confirmed `graph_status present: True` with real data in spot-check | FLOWING |
| `test_ingest_validate_e2e.py` | `report.errors` | `validate_workspace()` over ingested fixture copy | Yes — `report.ok == True`, `report.errors == []` after real ingest | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| graph.status returns real health report | `get_registry().get('graph.status').handler('test-ws/my-construct')` | `success=True`, keys: `['cards', 'connections', 'domains', 'workspace']` | PASS |
| help.suggest surfaces graph_status | `get_registry().get('help.suggest').handler('test-ws/my-construct').data` | `graph_status` key present=True | PASS |
| All 5 RT-03 MCP handlers callable | Handler type check for all 5 tools | All return `function callable: True` | PASS |
| Full test suite | `python -m pytest -q` | 224 passed, 0 failed | PASS |
| Contract tests | `python -m pytest tests/contract/test_mcp_contracts.py -x -q` | 12 passed | PASS |
| E2E ingest-validate | `python -m pytest tests/integration/test_ingest_validate_e2e.py -x -q` | 3 passed | PASS |

---

### Probe Execution

No probes declared in plan frontmatter or `scripts/*/tests/probe-*.sh`. The plan's own automated verify commands were run as behavioral spot-checks above. All exit 0.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RT-03 | 07-01-PLAN.md | MCP schema parity — all tools invocable without TypeError | SATISFIED | 5 dual-mode shims wired; 12 contract tests green; REQUIREMENTS.md: Complete |
| ING-02 | 07-02-PLAN.md | Ingest cluster validation — governed ingest passes validate | SATISFIED | Reserved clusters seeded in template + fixtures; E2E test green; REQUIREMENTS.md: Complete |
| ING-05 | 07-01-PLAN.md | graph.status wiring — returns real report, surfaced in help.suggest | SATISFIED | graph.status returns success=True with real data; help.suggest surfaces graph_status key; REQUIREMENTS.md: Complete |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `catalog.py` | 271 | `views.generate_data` stub: `OperationResult(success=False, "Not yet implemented")` | INFO | Pre-existing stub explicitly out of scope per 07-01-PLAN.md ("Leave `views.generate_data` stub untouched"). Not introduced by this phase. |
| `catalog.py` | 480-489 | Curation-cycle workflow steps return no-op placeholders | INFO | Pre-existing (present in commit 8531a11 before phase 07). Out of scope; catalogued in v0.3 audit tech_debt section. |
| `help.py` | 144 | `except (KeyError, Exception)` broad catch swallows non-TypeError graph.status failures | WARNING | Pre-existing, documented as WR-01 in 07-REVIEW.md. The happy path is now proven working (graph_status key present). Left as tracked follow-up per user's scoped decision. |

No `TBD`, `FIXME`, or `XXX` markers found in any phase-modified file.

**Note on CR-02 (deferred, out of scope):** `help.py:suggest` resolves per-domain stats from `root/<domain_id>/` subdirectory layout, but canonical `init` workspaces use a flat layout (`root/cards/`, etc.). This causes `total_cards: 0` for canonical workspaces like `test-ws/my-construct`. Observed in spot-check. This is a pre-existing architectural inconsistency surfaced during the CR-01 fix, explicitly documented in 07-REVIEW.md, and explicitly deferred out of scope by user instruction. The `graph_status` key is still populated correctly (verified above) because it uses the graph_status pipeline rather than help.py's per-domain stat path.

---

### Human Verification Required

#### 1. Milestone Re-Audit

**Test:** Run `/gsd:audit-milestone` against the current codebase on branch `v03ph01-feature`.
**Expected:** Audit reports 0 unsatisfied requirements. The three former blockers (RT-03, ING-02, ING-05) appear satisfied. RT-01 and RT-02 remain Partial (registry-bypass and direct-import paths explicitly deferred to v0.4 backlog). Requirements tally: 26 satisfied, 2 partial, 0 unsatisfied.
**Why human:** The milestone audit is a full-stack verification orchestrated tool that requires human invocation and review of its JSON/markdown output. Static grep and pytest cannot substitute for its cross-reference of runtime behavior, REQUIREMENTS.md traceability, SUMMARY frontmatter, and integration checks.

---

### Gaps Summary

No gaps blocking phase goal achievement. All three v0.3 audit blockers (RT-03, ING-02, ING-05) are closed with verified implementation, wiring, and test coverage. The full suite is green at 224 passed. The one outstanding item is the milestone re-audit confirmation, which is a process step requiring human orchestration rather than a code deficiency.

---

_Verified: 2026-06-16_
_Verifier: Claude (gsd-verifier)_
