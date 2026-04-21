# CONSTRUCT — Current State

**Last updated:** 2026-04-21
**Last session:** Coherence audit — path fixes across all documents

## What was done

- Product brief gap analysis completed
- ADR-0001: Python-first architecture, drop OpenClaw dependency
- Development process defined (PROCESS.md)
- Non-functional requirements defined (construct-nfrs.md)
- Test strategy defined (construct-test-strategy.md)
- Reference user journeys written (construct-user-journeys.md)
- Canonical knowledge card schema written (knowledge-card-schema.md)
- All data schemas written (construct-data-schemas.md) — 15 schemas covering views, publish, inbox, config, log
- **views/ vs publish/ split** — separated internal UI data layer (views/, disposable, gitignored) from external curated outputs (publish/, git-tracked). Updated all 9 spec documents (102→35 references, all remaining are legitimate publish/ references).
- **CONSTRUCT-product-development directory** created as standalone spec workspace, separated from live MABSTRUCT system
- README_FIRST.md navigation guide created

- **Repo topology spec** written (construct-repo-topology.md) — full directory tree, module ownership, workspace storage model, dependency graph
- **Development strategy** written (construct-development-strategy.md) — 8 phases (0–7), dependency ordering, risk register, v0.1 success criteria
- **Product brief / PRD split** — restructured 1279-line product brief into: product brief v2.0.0 (373 lines, vision + concepts + user interactions) and PRD v1.0.0 (483 lines, architecture + tech stack + storage model + agent specs + MVP scope). No content lost.
- **SQLite schema** written (construct-sqlite-schema.md) — 10 tables, 2 FTS5 virtual tables, query patterns per consumer, indexer behavior, migration strategy
- **Ref schema expanded** (construct-data-schemas.md §1.8) — v1.1: added impact (citations), provenance (retrieval query, search seed), extraction state (status, relevance, key findings, cards generated)
- **Agent specs** written for all three v0.1 agents:
  - agent-spec-construct.md — orchestrator: task routing, delegation protocol, session lifecycle, context building, escalation handling
  - agent-spec-researcher.md — 7-step research cycle, API clients (S2/arXiv), extraction/scoring pipeline, dedup, configuration
  - agent-spec-curator.md — 7-step curation cycle, promotion rules, decay/orphan scanning, connection typing, inbox processing, bridge detection
- **Coherence audit** — cross-document consistency fixes:
  - All nested paths (knowledge/, config/, agents/, memory/) updated to flat workspace layout across: data-schemas, test-strategy, NFRs, user-journeys, knowledge-card-schema, PRD
  - Two-tier promotion rules (seed→growing, growing→mature) now consistent across: governance.yaml schema, agent-spec-curator, PRD §5
  - Added digests/ directory to repo-topology workspace layout
  - Added missing escalation events to data-schemas event catalog
  - Fixed researcher digest output path to digests/{domain}/

## In progress

Nothing — pre-implementation spec work is complete.

## Blocked on

Nothing — next tasks are all actionable.

## Next up

1. Create the separate `construct` git repo — Phase 0 skeleton (per development strategy)
2. Begin Phase 1: Data Foundation

## Key decisions

- CONSTRUCT repo is **completely separate** from mabstruct-workspace — this directory is specs/planning only
- `views/` = internal heartbeat-rebuilt JSON for React UI (disposable, gitignored)
- `publish/` = curated external outputs like articles/reports/exports (git-tracked)
- Flat workspace layout: cards/, refs/, domains.yaml, governance.yaml at root (no knowledge/, config/, agents/ nesting)

## Open questions

- License: Apache-2.0 proposed, not formally decided
- Views rebuild cadence: 30s debounce proposed as default (captured in governance.yaml schema)
