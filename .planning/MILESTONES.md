# Milestones

## v0.3 Claude-Native Runtime & Workflow Hardening (Shipped: 2026-06-16)

**Phases completed:** 7 phases (1–7), 25 plans
**Git range:** d62de4a (first commit) → v0.3 tag, retagged to include build hooks/versioning
**Definition of done:** Harden CONSTRUCT's Claude-native runtime and workflow foundation — one canonical artifact contract, reliable knowledge operations, a shared capability/CLI/MCP runtime spine, dependable guided workflows, grounded graph reasoning, and v0.4-facing derived-data contracts — without pulling browser-UI work ahead of proven backend behavior.

**Key accomplishments:**

- **Phase 1 — Contract canon & governance:** Canonical Claude-native workspace contract (schemas, authority rules, pre-write gates) proven against the `test-ws/` fixtures, with a published migration playbook.
- **Phase 2 — Governed knowledge operations:** Reliable card / ref / connection / storage CRUD with non-blocking event logging and source→domain routing.
- **Phase 3 — Capability registry, CLI & MCP spine:** Deterministic capabilities exposed through one shared runtime contract, with a stdio MCP server as the agentic surface.
- **Phase 4 — Guided workflow operability:** State-aware help/ingestion and a WorkflowRunner with persisted state and resume-from-last-successful-step; skills migrated to the CLI/MCP invocation pattern.
- **Phase 5 — Grounded synthesis & graph reasoning:** Bounded question-answering, synthesis, and bridge detection grounded in workspace cards/connections with confidence-aware hedging.
- **Phase 6 — Derived data, ops UI & governed spikes:** Pydantic data contracts for the 8 views files, a Streamlit ops dashboard, and isolated governed spikes (tag extraction, Graphify/InfraNodus evaluation).
- **Phase 7 — Closed the v0.3 audit blockers:** RT-03 (MCP schema parity), ING-02 (ingest cluster validation), and ING-05 (graph.status wiring) — milestone re-audits to **0 unsatisfied requirements** (228 tests passing after final build/versioning work).

**Requirements:** 28/28 mapped · 26 Complete · 2 Partial (RT-01/RT-02 registry-bypass + direct-import command groups, deferred to v0.4) · 0 unsatisfied.

**Known deferred items at close:** 2 UAT items acknowledged and accepted for close (Phase 06 partial UAT — 1 issue / 1 blocked, 0 pending; Phase 07 HUMAN-UAT passed). Plus accepted tech debt catalogued in `milestones/v0.3-MILESTONE-AUDIT.md` (curation-cycle no-op steps, views.generate_data stub, ADV-03 view emission, SPK-04 entry point, CR-02 help.py layout, missing per-phase VERIFICATION/Nyquist/SECURITY coverage). See STATE.md "Deferred Items".

---
