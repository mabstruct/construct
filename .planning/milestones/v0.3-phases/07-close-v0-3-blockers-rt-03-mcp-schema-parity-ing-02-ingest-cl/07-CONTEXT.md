# Phase 7: Close v0.3 blockers - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Remediation phase that closes the three runtime blockers found by the v0.3 milestone audit (`.planning/v0.3-MILESTONE-AUDIT.md`) and syncs traceability bookkeeping so the milestone can re-audit to a legitimate green close. **No new product capability** — every change restores an already-promised v0.3 behavior or corrects records to match reality.

**In scope:**
- RT-03 — make the broken MCP tools invocable (adapter shims).
- ING-02 — make governed ingest produce refs that pass `construct validate` (seed reserved clusters).
- ING-05 — wire the existing `graph_status()` implementation into the registry handler (replace the stub).
- A contract test that **invokes** every MCP tool handler (closes the CI blind spot that hid RT-03).
- Traceability sync — REQUIREMENTS.md status column + SUMMARY `requirements_completed` frontmatter brought in line with what the audit verified.

**Out of scope (deferred):**
- Per-phase `VERIFICATION.md` backfill and `/gsd:validate-phase` runs for phases 02/03/04/06 (Nyquist debt) — handled by their dedicated commands, not this phase.
- `curation-cycle` placeholder steps, registry-bypass dispatch (`tag`/`spike`/`views`/`workflow resume`), unemitted view files, `views.generate_data` stub, SPK-04 entry point — tracked as v0.4 backlog.

</domain>

<decisions>
## Implementation Decisions

### RT-03 — MCP schema parity fix
- **D-01:** Fix via **adapter shims**, not service-signature refactor. Wrap each broken capability's handler in a `lambda **kwargs:` adapter inside `catalog.py` that maps advertised schema field names → the service function's parameter names. This matches the pattern already working for `ask.domain`, `bridge.detect`, `workflow.run`, and `help.suggest` (`catalog.py:247-360`). Change is localized to `catalog.py`; the service layer (`knowledge.py`, `validation.py`) and CLI callers are NOT touched.
- **D-02:** Capabilities needing shims (handler currently passed raw, param names ≠ schema): `validate` (`construct_validate`), `knowledge.card.create` (`construct_create_card`), `knowledge.card.edit` (`construct_edit_card`), `knowledge.connection.add` (`construct_add_connection`), `ingest.source` (`construct_ingest_source`). Planner to confirm the exact set by diffing each `input_model` against its handler signature; any other capability with the same mismatch is in scope.
- **D-03:** A contract test must **invoke** each MCP tool handler with schema-shaped kwargs and assert no `TypeError`. The current `tests/contract/test_mcp_contracts.py` only asserts schema *shape* (never calls a handler) — that gap is why a fully broken MCP write path passed 209 green tests. This test is the structural mechanism that prevents recurrence.

### ING-02 — ingest cluster validation fix
- **D-04:** Fix via **seeding reserved clusters**, not validator allowlist or required-cluster UX change. Add `manual-ingest` and `web-ingest` as reserved `SearchCluster` entries in `search-seeds.json` at workspace init (and in the migration path). Validation (`validation.py:205`) stays strict and unchanged; ingested refs now reference clusters that genuinely exist. Single source of truth stays in `search-seeds.json`.
- **D-05:** Backfill the reserved clusters into the existing `test-ws/` fixtures so the `ingest → validate` E2E passes on them. The ingestion fallbacks at `ingestion.py:162,208` and `knowledge.py:747` keep their `web-ingest`/`manual-ingest` defaults — those names now resolve to seeded clusters.

### ING-05 — graph.status wiring
- **D-06:** Wire the **already-existing** `graph_status()` (`src/construct/pipelines/graph_status.py:12` — complete, 79 lines) into the `graph.status` registry handler, replacing the `lambda **kwargs: OperationResult(success=False, "Not yet implemented — see Plan 02")` stub at `catalog.py:253`. Mirror the working adapter pattern. Surface its result through `help.suggest` instead of swallowing the failure (`help.py:125-130`).

### Phase scope
- **D-07:** Scope = **3 blockers + traceability sync**. Verification/Nyquist backfill (`VERIFICATION.md` ×6, `validate-phase` for 02/03/04/06) is explicitly deferred to dedicated runs — it is process debt, not a milestone blocker, and folding it in would bloat one closure phase into a six-phase verification project.

### Definition of done (proof gates)
- **D-08:** Hard gates that close the phase:
  1. **All MCP tools invocable** — the new handler-invocation contract test (D-03) passes for every MCP tool.
  2. **Re-audit passes** — `/gsd:audit-milestone` re-run shows 0 unsatisfied requirements (status no longer `gaps_found`).
- **D-09:** Implicit verification subsumed by the re-audit gate (not separately gated, but expected green): `ingest source` → `validate` passes E2E on a clean workspace + fixtures (ING-02); `graph.status` returns real data via CLI + MCP and `help.suggest` surfaces it (ING-05).

### Claude's Discretion
- Exact shim signature per capability (how each schema field maps to service args) — planner/executor decide from the live `input_model` and handler.
- Whether reserved-cluster seeding lives in the init scaffolder, a migration helper, or both — implementation detail.
- Test file organization (extend `test_mcp_contracts.py` vs new test module).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit source (the WHY for this phase)
- `.planning/v0.3-MILESTONE-AUDIT.md` — the three blockers with file:line evidence, requirement coverage matrix, and the verification-debt items being deferred.

### RT-03 — MCP parity
- `src/construct/capabilities/catalog.py` — capability registrations; working `lambda **kwargs:` adapters vs broken raw handlers (see ~`:247-360`).
- `src/construct/mcp/server.py` §`create_server` (~`:33`) — `capability.handler(**kwargs)` invocation site.
- `src/construct/services/knowledge.py` — `create_card` (`:136`), `edit_card` (`:221`), `add_connection` (`:347`) handler signatures.
- `src/construct/services/validation.py` — `validate_workspace(root)` signature.
- `src/construct/ui/capability_runner.py` §`:130-139` — same TypeError path in the Streamlit runner (has an explicit `except TypeError` guard acknowledging the gap; should be exercised by the fix too).
- `tests/contract/test_mcp_contracts.py` — current schema-only test to extend with handler invocation.

### ING-02 — ingest cluster validation
- `src/construct/services/validation.py` §`:205` — the cluster-membership rule that rejects unseeded clusters.
- `src/construct/pipelines/ingestion.py` §`:162,:208` — `web-ingest`/`manual-ingest` fallbacks.
- `src/construct/services/knowledge.py` §`:747` — `manual-ingest` fallback on seed-card ref.
- `search-seeds.json` (per-workspace; see `test-ws/*/`) — where reserved clusters must be seeded.

### ING-05 — graph.status
- `src/construct/pipelines/graph_status.py` §`:12` — the complete `graph_status()` implementation to wire in.
- `src/construct/capabilities/catalog.py` §`:247-255` — the stub handler to replace.
- `src/construct/services/help.py` §`:125-130` — where the stub failure is currently swallowed.

### Traceability sync
- `.planning/REQUIREMENTS.md` — traceability table + checkbox list to reconcile (11 entries marked Pending that the audit verified satisfied/partial).
- Phase SUMMARY frontmatter under `.planning/phases/*/` — empty `requirements_completed` for Phase 3 (all), 05-01/02/03, 06-02/04.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Working `lambda **kwargs:` adapter pattern in `catalog.py` (ask.domain/bridge.detect/workflow.run/help.suggest) — the template for every RT-03 shim.
- `graph_status()` in `pipelines/graph_status.py` — complete, returns an `OperationResult` with cards/connections/domains health data; ING-05 is wiring only, not new logic.

### Established Patterns
- Registry-mediated dispatch: capabilities declare `input_model` + `handler`; MCP/UI invoke `handler(**schema_kwargs)`. The contract is "handler accepts the schema's fields" — shims satisfy it without changing services.
- Strict write-time validation (FND-02): validation rejects refs whose `search_cluster` ∉ `search-seeds.json`. The ING-02 fix keeps this strict and makes the data conform, rather than weakening the gate.

### Integration Points
- `catalog.py` handler bindings (all three fixes touch this file).
- `search-seeds.json` seeding at workspace init / migration (ING-02).
- `help.suggest` → `graph.status` consumption (ING-05).

</code_context>

<specifics>
## Specific Ideas

- Re-use the existing working adapter style verbatim — do not invent a new shim abstraction.
- Reproduce the audit's exact ING-02 repro (`construct ingest source …` then `construct validate`) as the E2E check, now expected green.

</specifics>

<deferred>
## Deferred Ideas

- Per-phase `VERIFICATION.md` backfill for all 6 phases — run via `/gsd:verify-work` / dedicated verification, not this phase.
- `/gsd:validate-phase` for phases 02, 03, 04, 06 (Nyquist gaps) — own workflow.
- `curation-cycle` placeholder workflow steps (`catalog.py:349-355`) → real handlers — v0.4 backlog.
- Registry-bypass CLI groups (`tag`/`spike`/`views`/`workflow resume` direct-import) → route through registry — v0.4 backlog.
- `views.generate_data` stub (`catalog.py:262`) + unemitted view files — v0.4 backlog (ADV-03 follow-up).
- SPK-04 graph-guided exploration distinct entry point — v0.4 backlog.

</deferred>

---

*Phase: 7-close-v0-3-blockers*
*Context gathered: 2026-06-15*
