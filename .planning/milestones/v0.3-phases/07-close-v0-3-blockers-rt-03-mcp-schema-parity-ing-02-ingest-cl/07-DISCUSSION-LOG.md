# Phase 7: Close v0.3 blockers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 07-close-v0-3-blockers
**Areas discussed:** RT-03 fix strategy, ING-02 fix strategy, Phase scope, Definition of done

---

## RT-03 — MCP schema parity fix

| Option | Description | Selected |
|--------|-------------|----------|
| Adapter shims | Wrap broken handlers in `lambda **kwargs:` adapters in catalog.py mapping schema fields → service args. Matches existing working pattern; localized; low-risk. | ✓ |
| Refactor service signatures | Rename service-fn params to match schema so raw fns can be passed. Cleaner long-term but ripples into CLI + tests (wider blast radius). | |

**User's choice:** Adapter shims (Q1-A)
**Notes:** Keep remediation tight; reuse the half-of-registry pattern that already works. Mandatory companion: a contract test that invokes each handler (current test only checks schema shape).

---

## ING-02 — ingest cluster validation fix

| Option | Description | Selected |
|--------|-------------|----------|
| Seed reserved clusters at init | Add manual-ingest/web-ingest as reserved SearchCluster entries in search-seeds.json + migration + fixture backfill. Validation stays strict; single source of truth. | ✓ |
| Validation exempts reserved clusters | Hardcode reserved-name allowlist in validation.py. No data changes but splits cluster truth across two places. | |
| Require explicit cluster on ingest | Drop the hardcoded fallback; caller must name an existing cluster. Most governed but changes ingest UX. | |

**User's choice:** Seed reserved clusters at init (Q2-A)
**Notes:** Keeps FND-02 write-gate strict; makes the data conform rather than weakening the validator.

---

## Phase scope

| Option | Description | Selected |
|--------|-------------|----------|
| 3 blockers + traceability sync | Fix RT-03/ING-02/ING-05 + handler-invocation test + sync REQUIREMENTS.md & SUMMARY frontmatter. Defer VERIFICATION.md/Nyquist backfill to dedicated runs. | ✓ |
| Blockers only | Only the 3 code fixes + regression test; all bookkeeping debt to backlog. Re-audit would still flag stale traceability. | |
| Full clean close | Also run validate-phase 02/03/04/06 + backfill VERIFICATION.md ×6 in this phase. Most thorough but mixes code + process backfill. | |

**User's choice:** 3 blockers + traceability sync (Q3)
**Notes:** Reaches 0-unsatisfied on re-audit without bloating one closure phase into a verification project.

---

## Definition of done (proof gates)

| Option | Description | Selected |
|--------|-------------|----------|
| All MCP tools invocable | Contract test invokes every MCP tool handler, asserts no TypeError. | ✓ |
| ingest→validate green E2E | ingest source then validate passes on clean workspace + fixtures. | (implicit — subsumed by re-audit) |
| graph.status returns real data | CLI + MCP return real health report; help.suggest surfaces it. | (implicit — subsumed by re-audit) |
| Re-audit passes | /gsd:audit-milestone re-run shows 0 unsatisfied requirements. | ✓ |

**User's choice:** All MCP tools invocable + Re-audit passes (Q4)
**Notes:** The two unselected gates are the verification of ING-02 and ING-05 respectively; they are expected green and are subsumed by the re-audit gate (re-audit cannot pass unless they are fixed). Captured as D-09 implicit verification.

---

## Claude's Discretion

- Exact shim signature per capability (schema field → service arg mapping).
- Whether reserved-cluster seeding lives in the init scaffolder, a migration helper, or both.
- Test file organization (extend test_mcp_contracts.py vs new module).

## Deferred Ideas

- VERIFICATION.md backfill ×6; validate-phase for 02/03/04/06 (Nyquist).
- curation-cycle placeholder steps → real handlers.
- Registry-bypass CLI groups → route through registry.
- views.generate_data stub + unemitted view files (ADV-03 follow-up).
- SPK-04 graph-guided exploration entry point.
