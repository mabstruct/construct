---
id: SEED-001
status: dormant
planted: 2026-07-26
planted_during: v0.4.1 shipped — awaiting v0.5 scoping
trigger_when: when v0.5 UI-Primary Experience scoping begins — this IS the deferred Layer 4 framework decision
scope: medium
---

# SEED-001: Validate CoPilotKit as a possible UI framework for the v0.5 UI-primary shell

Docs: https://docs.copilotkit.ai

## Why This Matters

CoPilotKit is **already a named candidate in the roadmap**, not a new idea — this seed is the
concrete validation of a decision that has been deferred twice.

- `.planning/ROADMAP.md:69` — v0.5 is "extend v0.2 views SPA or CoPilotKit (decision deferred
  until scope is set)".
- `.planning/codebase/ARCHITECTURE.md:62` — Layer 4 location is "TBD — extend `views/` SPA, adopt
  CoPilotKit, or hybrid (**decided post-Streamlit spike in v0.3**)". The Streamlit spike ran
  (Phase 6), but the Layer 4 decision was never made. This is the single largest unresolved
  architectural choice in front of v0.5.

The user's interest is specifically in **CoPilotKit's newer features** — so the spike's research
step must read current docs, not rely on any prior impression of the library.

## When to Surface

**Trigger:** when v0.5 UI-Primary Experience scoping begins.

This should surface at `/gsd-new-milestone` for v0.5. It is a genuine prerequisite — planning a
browser-first shell without settling the framework means the phase breakdown is guesswork.

## Scope Estimate

**Medium** — a comparison spike (CoPilotKit vs extend-the-views-SPA vs hybrid), then a phase or
two to act on the verdict. Best run as a `comparison` spike type (`NNN-a` / `NNN-b`) since two
credible approaches exist and the spike workflow builds those back-to-back with a head-to-head
verdict.

## Breadcrumbs

**Two hard dependencies the spike must confront, not assume:**

1. **There is no Layer 3 HTTP API yet.** `.planning/codebase/ARCHITECTURE.md:64` says Layer 4
   "Depends on: Layer 3 HTTP API". CONSTRUCT today exposes capabilities over a Typer CLI and a
   **stdio** MCP server — no HTTP surface. CoPilotKit needs a runtime endpoint, so the spike must
   answer *what serves it*, and that answer is a v0.5 phase in its own right.
2. **The data contract underneath the SPA is broken.** `views validate` rejects 3 of the 8 files
   `views generate` writes — `generate()` validates an adapted projection but writes the raw
   parser dict. Pinned by `test_views_validate_does_not_yet_accept_generated_bytes`, flagged
   **ownerless** and a v0.5 prerequisite in `.planning/milestones/v0.4.1-MILESTONE-AUDIT.md`.
   Any UI spike sits on top of this.

**Existing UI prior art to compare against:**

- **Views SPA (Layer 3b):** React + Vite, compiled to `{workspace}/views/build/`, source scaffold
  at `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/`, polls
  `version.json` for freshness, read-only, never writes to SOT. The 15-module views library is
  vendored at `src/construct/views/lib/` as of Phase 15.
- **Streamlit ops UI (v0.3 Phase 6):** `src/construct/ui/streamlit_app.py`. Explicitly does
  **not** replace Layer 4 (`.planning/ROADMAP.md:71`). Evidence about the capability-button /
  result-panel pattern, not a decision.
- **Known churn risk:** `version.json` churns ~3x per daily cycle because every workflow
  capability now refreshes views (adr-0005). STATE.md flags this to be re-scored before SPA
  polling — relevant to whatever polls it.

**Constraints that bound the choice:**

- Local-first is a product constraint (`PROJECT.md`); a framework needing hosted services fights it.
- `PROJECT.md` Out of Scope: "Breaking current Claude-native workflows during the v0.5 UI build."
- Chat is to be "demoted to LLM-gated modals only" (`ARCHITECTURE.md:66`) — CoPilotKit's
  chat-centric model may push the opposite way. Worth testing deliberately.

## Notes

Related: [[SEED-003]] (a Wiki/knowledge-format question that also lands on the SPA).
