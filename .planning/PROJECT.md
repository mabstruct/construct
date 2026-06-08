# CONSTRUCT

## What This Is

CONSTRUCT is a local-first knowledge management system that helps a user collaboratively understand source material from files, notes, and web research. It builds a governed knowledge graph of knowledge nodes and typed connections, then exposes that knowledge through agentic workflows, graph views, and dynamic wiki-style browsing. The current Claude-native implementation is the proof-of-concept foundation; upcoming work hardens that foundation and evolves it toward a clearer product experience.

## Core Value

The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Harden the Claude-native skills and workflows so they are reliable and consistently follow defined data formats.
- [ ] Make the current agentic user experience clearer through documented workflows and dependable next-step guidance.
- [ ] Define and deliver the v0.3 foundation that preserves the knowledge model while creating a stable path toward a UI-primary product in v0.4.

### Out of Scope

- Full v0.4 browser UI in the current milestone — v0.3 must harden the runtime and workflow foundation first.
- Replacing the existing knowledge model or workspace format — continuity across versions is a core constraint.
- Breaking current Claude-native workflows during hardening or migration — existing user flows must remain usable.

## Context

CONSTRUCT is currently in a proof-of-concept phase and has already gone through multiple iterations. In v0.2, the project established a Claude-native implementation built from agentic skills and workflows. That prototype already supports a collaborative knowledge workflow in which the user and agent work from source files, notes, and web research to build a knowledge graph made of knowledge nodes and typed connections.

The product vision extends beyond the current prototype. The Claude-native approach remains important as the first working embodiment of the system and as the interaction model for v0.3, but it now needs hardening. Current pain points include inconsistent adherence to defined data formats, inconsistent workflow behavior, and insufficient clarity about what the user should do next.

The desired user experience in the near term is still guided by Claude-native skills, especially with clear documentation, stronger workflow contracts, and a dependable help skill that can suggest the next sensible step. In the longer term, v0.4 should present these same underlying capabilities through more obvious UI interactions so the product becomes easier for a broader audience to use.

There are already relevant analyses in the latest specification documents covering capabilities and artifacts. Those documents should inform requirements and roadmap structure rather than re-deriving the product from scratch.

## Constraints

- **Product continuity**: Preserve the existing knowledge model and workspace format across prototype, v0.3, and v0.4 — the system's continuity depends on shared semantics and files.
- **Sequencing**: Do not pull v0.4 UI-primary work ahead of v0.3 runtime and workflow hardening — the UI must sit on proven foundations.
- **Compatibility**: Protect existing Claude-native workflows while hardening and migrating them — users should not lose current capabilities.
- **Implementation posture**: v0.3 should still be usable through the Claude-native skill/workflow model even as it prepares a richer runtime and interface layer.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat the current Claude-native system as the production-defining prototype, not a throwaway experiment | The existing implementation already embodies the core knowledge workflow and should shape future versions | — Pending |
| Use v0.3 to harden workflows and runtime contracts before building the v0.4 UI-primary experience | A clearer UI only helps if the underlying capabilities are reliable and well-bounded | — Pending |
| Preserve the knowledge model and workspace format across versions | Cross-version continuity is central to the product architecture and migration story | — Pending |

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
*Last updated: 2026-06-08 after initialization*
