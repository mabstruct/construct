# Phase 17: Architecture Doc Set & daily.run Discoverability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-25
**Phase:** 17-architecture-doc-set-daily-run-discoverability
**Areas discussed:** Layer-model reconciliation, Inventory staleness-proofing, config-topology.md fate, daily.run skill shape

---

## Layer-model reconciliation (DOC-01)

### Q1 — How to reconcile the two "layer" framings?

| Option | Description | Selected |
|--------|-------------|----------|
| ADR-0003 stack as the spine | Make ADR-0003's runtime layers the canonical vocabulary; re-express data-flow + I1–I4 as properties; rename views cache "derived view data" to kill the numbering collision | ✓ |
| Two orthogonal framings side by side | Keep data-flow primary, add runtime stack as a distinct labeled section | |
| You decide | Planner picks | |

**User's choice:** ADR-0003 stack as the spine.
**Notes:** Fully satisfies "the four-layer model ADR-0003 describes, including the Python runtime." Side-by-side rejected as reintroducing the "two Layer 2s" confusion.

### Q2 — How to describe who writes to layer 1?

| Option | Description | Selected |
|--------|-------------|----------|
| Python runtime owns writes | L2 Python runtime owns every write; skills/CLI/MCP/UI invoke capabilities; registry is the write contract | |
| Writes go through capabilities, actor-agnostic | Emphasize the contract over the executor | |
| You decide | Exact framing at planning, false claim gone + Python role visible | ✓ |

**User's choice:** You decide.
**Notes:** Constraint captured: the false "skills are the only writers" claim must go and the Python runtime's write role must be visible. Recommended leaning (Python runtime owns writes) recorded in CONTEXT D-02, not locked.

### Q3 — Handling the "remove non-existent spec-v02-data-model.md citation" instruction

| Option | Description | Selected |
|--------|-------------|----------|
| Keep citations, record the correction | File exists; keep valid citations; record criterion premise as stale | |
| Re-audit for a genuinely-broken ref instead | Sweep for any doc ref that truly doesn't resolve; fix what's actually broken | ✓ |

**User's choice:** Re-audit for a genuinely-broken ref instead.
**Notes:** Live re-audit found the real defect — five vocabulary-doc citations at architecture-overview.md:262 pointing at CONSTRUCT-CLAUDE-spec/ when the files live at CONSTRUCT-CLAUDE-impl/construct/references/. spec-v02-data-model.md resolves fine; the audit named the wrong file.

### Q3b — How to fix the five genuinely-broken references

| Option | Description | Selected |
|--------|-------------|----------|
| Repoint to the real -impl path | Correct relative paths to CONSTRUCT-CLAUDE-impl/construct/references/; sweep the rest of the doc set | ✓ |
| Describe as workspace vocabulary, drop the file links | Reference by workspace location, no cross-tree links | |
| You decide | Planner picks | |

**User's choice:** Repoint to the real -impl path.
**Notes:** Keep spec-v02-data-model.md citations untouched. Researcher does a full resolve-sweep of the whole architecture doc set for siblings.

---

## Inventory staleness-proofing (DOC-02)

### Q1 — How should artifact-catalog.md stay accurate?

| Option | Description | Selected |
|--------|-------------|----------|
| Enumerate rows + cite guard, no frozen totals | Rows per item; counts expressed as "derived from live introspection — see test"; no new infra | |
| Add a mechanical catalog-vs-registry guard | New test asserts catalog rows == live registry/Typer/MCP introspection | ✓ |
| Frozen live-accurate counts | Record today's true numbers as hard figures, accept manual updates | |

**User's choice:** Add a mechanical catalog-vs-registry guard.
**Notes:** Strongest fit for a milestone about truth that stays true; extends FIX-04's philosophy. Noted as a deliberate scope addition, justified by criterion 2, distinct from the CI-smoke-suite Phase 16 D-09 declined.

### Q2 — Which surfaces should the guard assert?

| Option | Description | Selected |
|--------|-------------|----------|
| The 4 introspectable surfaces | capabilities + CLI + MCP + skills (auto-catches construct-spike-run); search-spine/LLM-gates narrative | |
| Core 3 command surfaces only | capabilities + CLI + MCP; skills/spine/gates manual | |
| You decide | Planner scopes, min capabilities+CLI+MCP, spike-run row present | ✓ |

**User's choice:** You decide.
**Notes:** Minimum capabilities+CLI+MCP asserted; skills coverage recommended (catches the missing construct-spike-run row); search-spine + LLM-gates rows narrative. Exact coverage at planning.

---

## config-topology.md fate (DOC-02)

### Q1 — Correct or delete config-topology.md?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete + redirect deferrers | Remove file; redirect README_FIRST.md + artifact-catalog.md to workspace-contract.md / artifact-catalog.md / architecture-overview.md | ✓ |
| Correct it in place | Rewrite against real layout; keeps a single topology doc but re-derives owned content | |
| You decide | Planner decides after confirming deferrers | |

**User's choice:** Delete + redirect deferrers.
**Notes:** File dated 2026-04-23, deeply stale; its three roles already owned by docs corrected this milestone. Model-routing deprecation truth survives in workspace-contract.md:78 + nfrs.md:72, so nothing is lost.

### Q2 — Pick up the fenced spec-v04:211,557 model-routing refs?

| Option | Description | Selected |
|--------|-------------|----------|
| Close the fence — fix both lines | Mark model-routing.yaml deprecated/inert at :211; reflect resolved state in :557 risk row | ✓ |
| Leave it — out of Phase 17's requirements | Defer to a later spec-accuracy pass | |
| You decide | Planner decides bundling | |

**User's choice:** Close the fence — fix both lines.
**Notes:** Honors the Phase 14 D-02 / Phase 16 D-15 hand-off; last stale model-routing refs in the live spec tree; bundled with DOC-02 config work.

---

## daily.run skill shape (UX-01)

### Q1 — Interaction shape for construct-daily-cycle

| Option | Description | Selected |
|--------|-------------|----------|
| Thin non-blocking wrapper + escalation handoff | Optional domain focus → invoke daily run → narrate composed result + escalation count → point to research/curation review; no gate loop | ✓ |
| Minimal invoke-and-narrate | Bare wrapper, no scope negotiation, no escalation handoff | |
| You decide | Planner shapes depth | |

**User's choice:** Thin non-blocking wrapper + escalation handoff.
**Notes:** Mirrors sibling skills' thinness minus their gate loop (daily.run is non-blocking by design). Honest handoff: pending escalations routed to `construct research review` / `construct curation review`.

### Q2 — Enroll in the thin-wrapper guard?

| Option | Description | Selected |
|--------|-------------|----------|
| Enroll in the guard | Add to test_skill_migration.py so allowed-tools can't regain forbidden tools | ✓ |
| Ship thin, don't enroll | Create thin, no guard | |
| You decide | Planner decides | |

**User's choice:** Enroll in the guard.
**Notes:** Mirrors Phase 16 D-14 (construct-synthesis). FIX-04 doc-command guard covers its command strings automatically; zero _KNOWN_BROKEN additions.

---

## Claude's Discretion

- Exact prose for the layer-1 write-ownership framing (Layer model Q2 — "you decide"; recommended leaning recorded).
- Exact guard coverage beyond capabilities+CLI+MCP (Inventory Q2 — "you decide"; skills recommended, spike-run row mandatory).
- New test file vs extension of test_doc_command_references.py's introspection helpers.
- daily-cycle.md workflow doc treatment (keep + reference; update stale diagram if trivial).
- Wave ordering / plan decomposition across DOC-01 / DOC-02 / UX-01.
- Whether ROADMAP/REQUIREMENTS stale premises ("27/25/21", "non-existent spec-v02-data-model.md") are corrected here or flagged for the milestone audit.
- construct-daily-cycle SKILL.md procedure wording, description, trigger.

## Deferred Ideas

- RT-01/RT-02 registry unification (views/spike/tag) — v0.6.
- Thin-wrapper migration for construct-bridge-detect / domain-init / search-adjust — v0.6.
- Actually deleting model-routing.yaml (workspace-format change) — v0.5+.
- Event-vocabulary reconciliation (conflict C4) — no overlap with this phase's edits; do not touch.
- Rewriting prd.md / development-strategy.md — out of scope.
- `views validate` accepting the bytes `views generate` writes — Phase 15 known-open; still open.
