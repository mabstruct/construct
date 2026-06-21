# Phase 1: Contract Canon & Artifact Governance — Research

**Researched:** 2026-06-08
**Status:** Complete
**Confidence:** High

## Objective

Answer: what must be true to plan contract canon, write gates, fixture proof, and migration work without re-inventing CONSTRUCT's active Claude-native model.

## Standard Stack

- **Contract authority:** `CONSTRUCT-CLAUDE-spec/` + `CONSTRUCT-CLAUDE-impl/construct/templates/` + `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` per D-03/D-04.
- **Runtime enforcement:** Pydantic v2 schemas in `src/construct/schemas/`, loader boundaries in `src/construct/storage/workspace.py`, service-level validation in `src/construct/services/validation.py`.
- **Verification:** pytest against real filesystem fixtures; Claude-native validation remains workspace-audit based.

## Architecture Patterns

1. **One canonical artifact source set** — specs define WHAT, templates show file shape, runtime code enforces HOW.
2. **Workspace files stay canonical** — cards, refs, connections, domains, governance, search seeds, and event log are source-of-truth; `digests/` and `publish/` are derived/support per D-10.
3. **Write gates before mutation** — invalid artifacts should fail before landing; post-write validation is for cross-file integrity, audit, and fixture proof per D-05/D-06.
4. **Single migration path, not parallel layouts** — Phase 1 should pick one canonical layout and document how older runtime assumptions move to it per D-07/D-09.

## Current Drift To Correct

### Authoritative docs disagree on workspace shape

- `CONSTRUCT-CLAUDE-impl/AGENTS.md` describes a domain workspace with `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `digests/`, `publish/`, `log/events.jsonl`.
- `src/construct/schemas/workspace.py` still requires dormant/older paths such as `domains/`, `workflows/`, `db/`, and root `model-routing.yaml`, making the runtime authoritative when it should not be.
- `src/construct/services/init.py` scaffolds the older `domains/{id}/domain.yaml` layout and points `TEMPLATE_DIR` at `CONSTRUCT-CLAUDE-impl/templates`, which is not the active template directory.

### Validation is post-hoc, not pre-write

- `src/construct/services/validation.py` audits an existing workspace but does not expose write-time artifact validation boundaries.
- `construct-workspace-validate` documents five audit layers, but there is no matching runtime contract for refs, events, search seeds, or staged write rejection.

### Canonical artifact coverage is incomplete in runtime code

- `src/construct/schemas/card.py` is close to canonical card spec.
- `src/construct/schemas/config.py` and `workspace.py` still encode archived assumptions (`DomainConfig`, `DomainsRegistry`, `HeartbeatConfig`, root `model-routing.yaml`, nested domain files).
- Runtime has no first-class schema models for `refs/*.json`, `search-seeds.json`, or `log/events.jsonl` even though `data-schemas.md` defines them.

### Fixture proof target is ambiguous in repo state

- Planning/context documents say `test-ws/`.
- Checked-in fixture root is currently `testws/`.
- Phase 1 should make one spelling canonical and update tests/docs in one pass so D-08 has a single proof target.

## Don't Hand Roll

- Do **not** invent a second contract source outside spec + templates + catalog.
- Do **not** keep broad dual-layout compatibility as the default solution.
- Do **not** treat `digests/`, `publish/`, `views/`, or indexes as canonical SOT.
- Do **not** rely on prompt-only skill checklists for write safety once runtime hooks exist.

## Common Pitfalls

1. Updating Python schemas without updating spec/templates/skills in the same phase.
2. Preserving both `test-ws/` and `testws/` as acceptable fixture roots.
3. Calling post-write audits “write validation” without a pre-write rejection path.
4. Letting `connections.json` and card inline links diverge without an explicit ownership rule.
5. Shipping migration notes that describe compatibility vaguely instead of listing artifact-by-artifact changes.

## Architectural Responsibility Map

| Concern | Authoritative Layer | Implementation Layer | Notes |
|--------|----------------------|----------------------|-------|
| Card / ref / connection / event shapes | `CONSTRUCT-CLAUDE-spec/*.md` | `src/construct/schemas/` | Runtime must follow spec, not vice versa |
| Initial file contents | `CONSTRUCT-CLAUDE-impl/construct/templates/` | `src/construct/services/init.py` and skill procedures | Template drift is a contract bug |
| Write rejection | Runtime capability/service layer | `src/construct/services/*` | Enforce before file lands |
| Cross-file audit and fixture proof | Validation service + pytest | `src/construct/services/validation.py`, `tests/` | Post-write checks per D-06 |
| User-visible workflow behavior | Skill procedures + commands/capabilities docs | `CONSTRUCT-CLAUDE-impl/claude/skills/*`, references docs | Must match runtime-backed behavior |
| Migration story | Spec/docs | migration doc + fixture tests | Must be explicit per D-07 |

## Validation Architecture

Phase 1 should plan verification around three layers:

1. **Contract tests** — template files and inline fixtures round-trip through Pydantic models.
2. **Write-gate tests** — invalid card/ref/connection/event payloads are rejected before write helpers persist them.
3. **Fixture proof tests** — the real checked-in workspace fixtures validate cleanly (or fail with intentional, enumerated gaps) using the canonical proof target.

## Planning Implications

- Start with the **canonical contract docs** so later code changes have an unambiguous target.
- Then align **runtime schemas, init, and write gates** to that target.
- Finish by syncing **skills/templates, migration guidance, and fixture proof** so FND-03/FND-05/FND-06 are closed with executable verification.

## Output Expectations For Planner

- At least one plan must implement D-03/D-04 directly in authoritative docs.
- At least one plan must implement D-05/D-06 with real automated tests.
- At least one plan must implement D-07/D-08/D-09 with migration and fixture-proof artifacts.

## Research Complete

Ready for planning.
