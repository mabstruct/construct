# CONSTRUCT v0.5 — UI-Primary Experience — Baseline Requirements Spec

**Version:** 0.5.0-baseline
**Date:** 2026-06-21
**Status:** Draft — baseline input for v0.5 phase planning (do not start before v0.4 ships)
**Audience:** GSD phase planners, implementers, spec reviewers
**Prerequisite:** v0.4 agent workflows shipped (`research.run`, `curation.run`, registry-unified invoke surface)

**Related (authoritative upstream):**

| Document | Role |
|----------|------|
| [adrs/adr-0003-v03-pipeline-v04-ui.md](adrs/adr-0003-v03-pipeline-v04-ui.md) | Layer 4 UI shell; Amendment B sequencing |
| [spec-v04-agentworkflows.md](spec-v04-agentworkflows.md) | v0.4 workflow capabilities the UI must call |
| [artifact-catalog.md](artifact-catalog.md) | C03 `UI` affordances per skill/workflow |
| [user-journeys.md](user-journeys.md) | J1–J3 — completion criteria for UI-primary delivery |
| [spec-v02-views.md](spec-v02-views.md) | Read-heavy SPA; foundation for write actions |
| [prd-v02-live-views.md](prd-v02-live-views.md) | Views runtime topology |
| [prd-v03-pipeline-mvp.md](prd-v03-pipeline-mvp.md) | Gate review protocol, derived JSON contracts |

---

## 1. Summary

v0.5 delivers the **browser-primary product shell** (Layer 4): structured controls that invoke **v0.4 workflow capabilities** over HTTP, with chat reserved for **L1/L2/L3 modals** only.

**Goals:**

1. **UI-as-primary** — users complete J1–J3 journeys through buttons, wizards, and dashboards—not open-ended chat for PIPE operations.
2. **One contract** — HTTP routes mirror the capability registry (same schemas as CLI/MCP).
3. **Provenance visible** — progress, errors, gate status, and data freshness shown in UI (not buried in transcripts).
4. **Extend v0.2 views** — read paths stay derived-JSON; write paths call Layer 3 HTTP.

**Non-goals:** Cloud-first deploy, multi-user auth, SQLite indexer, replacing Claude/Cursor for L1 dialogue, re-implementing workflow logic in the frontend.

---

## 2. Motivation

| Driver | Why v0.5 (not v0.3/v0.4) |
|--------|----------------------------|
| **Stable invoke targets** | v0.3 proved PIPE + MCP; v0.4 proves multi-step workflows—UI needs both |
| **Broader audience** | Chat-first skills work for power users; product needs obvious affordances |
| **Artifact catalog** | Many skills target `UI` in C03 audit—they need HTTP + components, not SKILL.md prose |
| **Streamlit spike** | v0.3 ops UI validated gate review + capability runner patterns; v0.5 productizes them |

Chat remains for: domain interview (L1), co-authorship voice (L1), grounded ask (L2 panel), promotion/connection review (L3 modals).

---

## 3. Architecture

```text
Layer 4  UI shell (v0.5)     React/Vite SPA (+ optional CoPilotKit panels)
         │                   Capability buttons, wizards, progress, gate modals
Layer 3  HTTP API             FastAPI adapter → same capability registry as CLI/MCP
Layer 2  v0.4 workflows       research.run, curation.run, ask.domain, …
Layer 1  Workspace SOT        unchanged
```

**Invoke rule:** UI never writes SOT directly. All mutations go through registered capabilities (including gate approve/reject endpoints).

**Technology direction (from v0.3 spike — finalize in discuss-phase):**

| Option | Role |
|--------|------|
| **Extend v0.2 views SPA** | Default candidate — graph/read already shipped; add write actions via HTTP |
| **CoPilotKit (optional)** | L1/L2 sidebar or modals if agent-in-the-loop UX needs more than views chrome |
| **Streamlit** | v0.3 ops spike only — not v0.5 product UI |

---

## 4. Headline UI affordances (from artifact catalog)

Map catalog `C03 target: UI` rows to v0.5 components (detail in phase PRD):

| Area | Examples |
|------|----------|
| **Home / help** | State-aware dashboard; suggested next actions as buttons |
| **Research & ingest** | Run research, ingest URL, review batch before commit |
| **Curation** | Curate domain, promotion queue, connection typing review |
| **Graph & views** | Existing views pages + refresh control; cross-domain panel |
| **Authoring** | Draft workspace, outline approve, finalize publish |
| **Admin** | Validate, views reset, domain management forms |

---

## 5. HTTP / API spine (outline)

v0.5 adds **Layer 3 HTTP** — not in v0.4 scope.

| Concern | Requirement |
|---------|-------------|
| **Route shape** | `POST /capabilities/{id}` or RESTful alias per registry entry |
| **Schemas** | OpenAPI generated from Pydantic models (same as MCP `input_schema`) |
| **Progress** | SSE or poll endpoint for long workflows (`research.run`, `curation.run`) |
| **Gate review** | `POST /gates/{gate_id}/approve` \| `reject` — mirrors Streamlit protocol |
| **Views freshness** | UI polls `views/build/version.json`; shows stale indicator |
| **Auth** | Localhost-only for v0.5 baseline; no multi-user |

---

## 6. User journeys — done when (v0.5)

| Journey | UI-primary completion |
|---------|------------------------|
| **J1 Cold start** | Wizard: init → domain setup → research → curation → status (minimal chat) |
| **J2 Daily cycle** | “Run maintenance” runs research + curation; results panel + gate queue |
| **J3 Co-authorship** | Draft editor + L1/L2 modals; publish with citation provenance visible |

---

## 7. Scope

### In scope (v0.5 baseline)

- FastAPI (or equivalent) HTTP adapter over capability registry
- Extend `views/` SPA with write-action panels for core workflows
- Gate review UI (promotion, research ingest batch, L2 ask) — port Streamlit patterns
- Progress/result panels for `research.run`, `curation.run`, `workflow.daily_cycle`
- OpenAPI contract + contract tests (HTTP parity with MCP)

### Out of scope (defer)

- Cloud deploy, auth, multi-tenant
- MCP SSE / remote agents
- Replacing all Claude skills with UI (L1 chat paths remain)
- Full CoPilotKit adoption (optional spike only)
- Mobile layout / responsive polish beyond desktop-first

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| UI duplicates backend rules | Single registry; UI is thin; validation stays Python |
| v0.4 slips block v0.5 | Hard gate: no v0.5 GSD until v0.4 milestone audit passes |
| Views + write UI diverge | Shared OpenAPI types; views read cache, writes go API-only |
| Gate UX without Streamlit | Reuse `gate_review.py` semantics; same event types |

---

## 9. Phased next steps (for GSD)

| Phase | Deliverable |
|-------|-------------|
| **U1** | HTTP adapter + OpenAPI for tranche-1 v0.3/v0.4 capabilities |
| **U2** | Home dashboard + “run research / curate” buttons wired to progress API |
| **U3** | Gate review modals (research batch, promotion queue) |
| **U4** | Extend views SPA — write actions + version freshness UX |
| **U5** | J1–J3 E2E UI walkthrough + USER-TEST-PLAYBOOK-v05 |

**Entry:** `/gsd-new-milestone` after v0.4 close. Produce `prd-v05-ui-primary.md` from this spec.

---

## 10. Traceability

| v0.3/v0.4 artifact | v0.5 consumer |
|--------------------|---------------|
| Streamlit ops UI | Gate review + capability runner UX patterns |
| 8 views JSON files | Read paths unchanged |
| `gate_review.py` event protocol | Approve/reject API + UI modals |
| `spec-v04-agentworkflows.md` capabilities | Primary HTTP invoke targets |

---

## 11. Open questions (discuss-phase)

1. **SPA vs hybrid** — extend v0.2 views only, or views + CoPilotKit for L1/L2?
2. **Progress transport** — SSE vs polling vs WebSocket for workflow steps?
3. **Gate queue persistence** — session-only (Streamlit parity) vs workspace-scoped queue file?
4. **HTTP localhost binding** — fixed port contract for views SPA CORS?

---

## 12. Document history

| Date | Change |
|------|--------|
| 2026-06-21 | Initial baseline — UI-primary deferred from v0.4 to v0.5 per ADR-0003 Amendment B |

---

*This document is input to v0.5 GSD phase planning. It does not supersede v0.2 views data contracts or workspace SOT formats. Implementation bindings belong in `prd-v05-ui-primary.md`.*
