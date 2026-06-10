# Phase 3: Capability Registry, CLI & MCP Spine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-06-10
**Phase:** 03-capability-registry-cli-mcp-spine
**Mode:** Discuss

## Gray Areas Presented

1. **Registry implementation pattern** — Pydantic-based, decorator-based class, or YAML-driven?
2. **Capability scope for Phase 3** — Only 3 PIPE capabilities, all existing + PIPE, or only new PIPE?
3. **Existing CLI migration** — Direct commands delegate to registry, dual-path with deprecation, or skip `construct run`?
4. **First migrated skill (MCP proof)** — construct-workspace-validate, construct-card-create, or both?
5. **test-ws/ fixtures** — Create in this phase or as prerequisite?

## Areas Selected for Discussion

User selected: Registry implementation pattern, Capability scope, CLI migration, First migrated skill, test-ws/ fixtures
(All 5 areas discussed — none skipped)

## Q&A Record

### Area: Registry implementation pattern

**Q:** How should the capability registry be structured in Python?
- Options: Pydantic-based (Recommended), Decorator-based class, YAML-driven registry file
- **Selection:** Pydantic-based (Recommended)
- Rationale: Reuses existing Pydantic schemas, JSON Schema auto-derived via model_json_schema(), standard Pydantic model validation.

**Q:** For the schema representation: existing Pydantic models or standalone JSON Schema?
- Options: Reference existing Pydantic models, Separate JSON Schema definitions
- **Selection:** Reference existing Pydantic models
- Rationale: One source of truth — the Pydantic model IS the contract. Handlers get typed models, not raw dicts.

**Q:** How should handlers be dispatched from the capability registry?
- Options: Direct callable reference, Module-path resolution
- **Selection:** Direct callable reference
- Rationale: Simple and explicit — calling a capability is cap.handler(**inputs).

### Area: Capability scope for Phase 3

**Q:** Which capabilities get registered in Phase 3?
- Options: 3 PIPE + init, All existing CLI + 3 PIPE, Just 3 new PIPE
- **Selection:** All existing CLI commands + tranche-1 PIPE
- Rationale: Maximum coverage from the start — proves the registry works for all surface types.

### Area: Existing CLI migration

**Q:** How to handle existing direct commands when `construct run <capability>` is introduced?
- Options: Direct commands delegate to registry, Dual-path with deprecation, Skip `construct run` entirely
- **Selection:** Direct commands delegate to registry
- Rationale: Existing paths stay, registry is the dispatch engine. No duplication, no deprecation period needed.

### Area: First migrated skill (MCP proof)

**Q:** Which skill becomes the MCP proof point?
- Options: construct-workspace-validate, construct-card-create, Both
- **Selection:** construct-workspace-validate
- Rationale: ADR-0003 suggestion. Simple PIPE capability with no LLM dependency — clean proof of the agentic MCP path.

### Area: test-ws/ fixtures

**Q:** Create test-ws/ fixtures in this phase or treat as prerequisite?
- Options: Create in this phase (Recommended), Prerequisite before Phase 3
- **Selection:** Create in this phase (Recommended)
- Rationale: Contract tests need real workspace fixtures to prove CLI commands. Avoids blocking Phase 4.

## Decisions Captured

12 decisions (D-01 through D-12) — see CONTEXT.md for full detail.

## Deferred Ideas

- LangGraph L2 ask.domain — Phase 5
- Workflow runner skeleton — Phase 4
- Streamlit ops UI — Phase 6
- Full skill migration beyond construct-workspace-validate — Phase 4
- `construct run <capability>` namespace — not needed

---
*Discussion recorded: 2026-06-10*
