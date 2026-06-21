# Phase 6: Derived Data, Ops UI & Governed Spikes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 06-derived-data-ops-ui-governed-spikes
**Areas discussed:** Derived Data Contracts, Ops UI Scope (Streamlit), Spike Framework, Tag/Keyword Pipeline

---

## Derived Data Contracts

| Option | Description | Selected |
|--------|-------------|----------|
| A: Schema declarations | Publish JSON Schema for each views data file | |
| B: Versioned contracts | Add version field to data files + SPA compatibility | |
| C: Contract tests | Pydantic-backed tests validating JSON file shape | |
| D: All of the above | Schemas + version field + contract tests | ✓ |

**User's choice:** Option D — All of the above
**Notes:** Full stability package. Generator validates output against schema before writing.

---

## Ops UI Scope (Streamlit)

| Option | Description | Selected |
|--------|-------------|----------|
| A: Gate review panel only | Review ask.domain Q&A and bridge candidates | |
| B: Gate review + capability runner | Review panel + run CLI capabilities from UI | |
| C: Dashboard + gate review | Graph health dashboard + gate review | |
| D: Full ops suite | Dashboard + capability runner + gate review panel | ✓ |

**User's choice:** Option D — Full ops suite
**Notes:** Three panels: Dashboard (graph health), Gate review (Q&A + bridges), Capability runner (execute any capability).

---

## Spike Framework

| Option | Description | Selected |
|--------|-------------|----------|
| A: Spike runner CLI | construct spike run <tool> with temp isolation | |
| B: Documented procedure | SKILL.md describing safe execution | |
| C: CLI + procedure | Both runner CLI + documented procedures | ✓ |

**User's choice:** Option C — CLI + procedure
**Notes:** Spike runner CLI creates isolated temp workspace copy. SKILL.md per spike type.

---

## Tag/Keyword Pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| A: Spike only | Framework + docs, no pipeline built | |
| B: Spike + candidate pipeline | Pipeline extracting tags to reviewable candidates | |
| C: Full pipeline to search-seeds | Pipeline extracts tags → log/tag-candidates.json → review → search-seeds.json | ✓ |

**User's choice:** Option C — Full pipeline to search-seeds
**Notes:** LLM-assisted extraction from refs. Candidates never auto-accepted — must pass curation review.

---

## Deferred Ideas

- Full v0.5 browser UI — explicitly out of scope.
- Embedding-based retrieval for ask.domain — still deferred.

---

*Phase: 06-derived-data-ops-ui-governed-spikes*
*Discussion logged: 2026-06-11*
