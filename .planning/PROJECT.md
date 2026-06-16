# CONSTRUCT

## What This Is

CONSTRUCT is a local-first knowledge management system that helps a user collaboratively understand source material from files, notes, and web research. It builds a governed knowledge graph of knowledge nodes and typed connections, then exposes that knowledge through agentic workflows, graph views, and dynamic wiki-style browsing. The current Claude-native implementation is the proof-of-concept foundation; upcoming work hardens that foundation and evolves it toward a clearer product experience.

## Core Value

The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.

## Requirements

### Validated

- ✓ Harden the Claude-native skills and workflows so they are reliable and consistently follow defined data formats — v0.3 (canonical contract + pre-write gates, Phases 1–2).
- ✓ Make the current agentic user experience clearer through documented workflows and dependable next-step guidance — v0.3 (guided workflow operability + help.suggest, Phase 4; graph-health surfacing, Phase 7).
- ✓ Define and deliver the v0.3 foundation that preserves the knowledge model while creating a stable path toward a UI-primary product in v0.4 — v0.3 (capability/CLI/MCP runtime spine + derived-data contracts, Phases 3, 5, 6).

### Active

- [ ] Unify the runtime dispatch surface (RT-01/RT-02): route views/spike/tag command groups through the capability registry so MCP/UI see them — carried from v0.3 audit.
- [ ] Complete deferred runtime behavior: curation-cycle workflow steps (currently no-ops), `views.generate_data`, and view-file emission (ADV-03).
- [ ] Stand up the v0.4 UI-primary experience (browser-first shell) on top of the hardened v0.3 runtime.
- [ ] Close v0.3 verification debt: per-phase VERIFICATION.md, Nyquist VALIDATION.md, and SECURITY.md coverage where missing.

### Out of Scope

- Replacing the existing knowledge model or workspace format — continuity across versions is a core constraint.
- Breaking current Claude-native workflows during the v0.4 UI build — existing user flows must remain usable.

## Context

CONSTRUCT is currently in a proof-of-concept phase and has already gone through multiple iterations. In v0.2, the project established a Claude-native implementation built from agentic skills and workflows. That prototype already supports a collaborative knowledge workflow in which the user and agent work from source files, notes, and web research to build a knowledge graph made of knowledge nodes and typed connections.

The product vision extends beyond the current prototype. The Claude-native approach remains important as the first working embodiment of the system and as the interaction model for v0.3, but it now needs hardening. Current pain points include inconsistent adherence to defined data formats, inconsistent workflow behavior, and insufficient clarity about what the user should do next.

The desired user experience in the near term is still guided by Claude-native skills, especially with clear documentation, stronger workflow contracts, and a dependable help skill that can suggest the next sensible step. In the longer term, v0.4 should present these same underlying capabilities through more obvious UI interactions so the product becomes easier for a broader audience to use.

There are already relevant analyses in the latest specification documents covering capabilities and artifacts. Those documents should inform requirements and roadmap structure rather than re-deriving the product from scratch.

**Current state (after v0.3, 2026-06-16):** v0.3 shipped across 7 phases / 25 plans. The runtime is a Python package (`src/construct/`) with a capability registry, a Click CLI, and a stdio MCP server as the agentic surface; Claude-native skills are thin wrappers over those capabilities. Knowledge lives in a governed workspace (cards/refs/connections + search-seeds/domains/governance YAML) behind pre-write validation gates. Grounded Q&A, synthesis, and bridge detection run on the graph; a Streamlit ops dashboard and view data contracts prepare v0.4. Test suite: 224 passing. The v0.3 milestone audit closes at 0 unsatisfied requirements with documented tech debt (registry-bypass paths RT-01/RT-02, curation no-ops, views emission, verification-coverage gaps) carried into v0.4. Next: scope the v0.4 UI-primary experience.

## Constraints

- **Product continuity**: Preserve the existing knowledge model and workspace format across prototype, v0.3, and v0.4 — the system's continuity depends on shared semantics and files.
- **Sequencing**: Do not pull v0.4 UI-primary work ahead of v0.3 runtime and workflow hardening — the UI must sit on proven foundations.
- **Compatibility**: Protect existing Claude-native workflows while hardening and migrating them — users should not lose current capabilities.
- **Implementation posture**: v0.3 should still be usable through the Claude-native skill/workflow model even as it prepares a richer runtime and interface layer.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat the current Claude-native system as the production-defining prototype, not a throwaway experiment | The existing implementation already embodies the core knowledge workflow and should shape future versions | ✓ Good — v0.3 hardened it into a Python runtime + MCP spine with skills as thin wrappers |
| Use v0.3 to harden workflows and runtime contracts before building the v0.4 UI-primary experience | A clearer UI only helps if the underlying capabilities are reliable and well-bounded | ✓ Good — v0.3 shipped the hardened runtime; v0.4 UI now sits on proven foundations |
| Preserve the knowledge model and workspace format across versions | Cross-version continuity is central to the product architecture and migration story | ✓ Good — workspace format preserved; Phase 1 published a migration playbook |
| Python is the deterministic enforcement layer; skills orchestrate flow; the capability registry is the single contract behind CLI + MCP | Keeps behavior testable and gives agents and (future) UI one surface | ⚠️ Revisit — registry is canonical for core ops, but views/spike/tag groups still bypass it (RT-01/RT-02, v0.4) |
| Fix governed-ingest validation by conforming the data to the gate, not weakening the gate | Keeps validation strict so canonical truth stays trustworthy | ✓ Good — v0.3 (Phase 7, ING-02) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-16 after v0.3 milestone*
