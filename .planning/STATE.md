---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: Agent Workflows
status: executing
stopped_at: Phase 8 context gathered
last_updated: "2026-06-21T16:01:14.382Z"
last_activity: 2026-06-21 -- Phase 8 planning complete
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 3
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-21)

**Core value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.  
**Current focus:** v0.4 Agent Workflows — Phase 8 Search Provider Spine + Contract Foundation

## Current Position

Phase: 8 of 13 overall / 1 of 6 in v0.4 (Search Provider Spine + Contract Foundation)  
Plan: Not planned yet  
Status: Ready to execute
Last activity: 2026-06-21 -- Phase 8 planning complete

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- v0.4 plans completed: 0
- v0.4 total plans: TBD
- v0.3 shipped history: 7 phases / 25 plans

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 8 | TBD | - | - |

**Recent Trend:**

- Last completed milestone: v0.3 shipped 2026-06-16 with 0 unsatisfied requirements.
- Trend: v0.4 ready to begin planning from Phase 8.

## Accumulated Context

### Roadmap Evolution

- v0.3 shipped Phases 1–7 and remains preserved in ROADMAP.md with full details archived under `.planning/milestones/`.
- Phase 7 added: Close v0.3 blockers (RT-03 MCP parity, ING-02 ingest cluster, ING-05 graph.status) — from milestone audit 2026-06-15.
- v0.4 started as Agent Workflows milestone: search provider spine, research.run, curation.run, thin skill migrations, and daily-cycle composition. v0.5 UI and unrelated v0.3 carry-over debt remain deferred unless directly required.
- v0.4 continues numbering at Phase 8 and contains 6 phases: search spine, score gate, reviewed research run, curation PIPE, curation gates, daily-cycle composition.
- Scope boundary: keep v0.5 UI, HTTP/cloud, broad RT-01/RT-02 cleanup, full views emission, and historical verification/security debt out unless directly blocking v0.4 workflows.

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

- [Phase 05-02]: Models defined in ask_domain.py (not catalog.py) to avoid circular imports between catalog and run_gate handler.
- [Phase 05-02]: Domain filter checks domain_id in card.domains list (KnowledgeCard schema has plural list).
- [Phase 07-01]: RT-03 shims are dual-mode — positional CLI calls pass straight through to the service fn, keyword MCP calls are marshalled — so one registry handler serves both surfaces without touching cli.py or the service layer.
- [Phase 07-01]: graph.status handler uses `lambda workspace: graph_status(workspace)` so a single param binds both positional (help.py) and keyword (MCP) callers.
- [Phase 07-02]: ING-02 fixed by seeding the data (reserved manual-ingest/web-ingest clusters) to conform to the gate, not by weakening validation.py:205.
- [Phase 07-02]: validation.py:148 DOES cross-check cluster.domain against domains.yaml (plan interface note was wrong) — reserved clusters' placeholder "ingest" domain is rewritten to the workspace domain at init; fixtures reuse an existing domain.
- [Phase 07-02]: research_seeds override now APPENDS the domain seed cluster rather than replacing payload["clusters"], so reserved clusters survive research-seeded init.
- [Phase 07-03]: Traceability status changes bounded strictly to v0.3 audit Final verdicts — nothing marked Complete beyond audit-verified satisfaction.
- [Phase 07-03]: RT-01/RT-02 kept Partial (not Complete) — registry-bypass and direct-import command groups are explicit v0.4 backlog.
- [Phase 07-03]: requirements_completed backfilled per each plan's genuine deliverable read from SUMMARY bodies, not invented coverage.

Recent decisions affecting current work:

- [Roadmap]: Harden Claude-native contracts and workflows before expanding UI surface.
- [Roadmap]: Use v0.3–v0.4 to establish shared runtime contracts and LangGraph workflows, then prepare v0.5-facing derived data and UI.
- [Phase 01]: The canonical workspace contract is the Claude-native layout, not the dormant Python-first layout.
- [Phase 01]: Invalid canonical artifacts are rejected before write; post-write checks handle audit, consistency, and fixture proof.
- [Phase 01]: The authority set is spec plus templates plus artifact catalog; runtime and skills must follow it.
- [Phase 01]: Runtime domain data now lives inline in domains.yaml; archived per-domain YAML paths are no longer canonical.
- [Phase 01]: Pre-write validation helpers reject malformed cards, refs, connections, and events before persistence.
- [Phase 01]: Workspace init now scaffolds the canonical Claude-native layout and logs a workspace_init event.
- [Phase 01]: Fixture workspaces at test-ws/ are the canonical Phase 1 proof target per D-08.
- [Phase 02]: Python is the deterministic enforcement layer; skills orchestrate flow (D-01).
- [Phase 02]: `construct knowledge` CLI namespace is the Python surface for card/connection ops (D-03).
- [Phase 02]: Skills become thin wrappers calling Python CLI (D-04).
- [Phase 02]: Archive preserves connections in connections.json (D-06).
- [Phase 02]: Event log append is non-blocking — OSError writes warning to stderr (D-14 mitigation).
- [Phase 03]: Capability registry uses Pydantic-based model for capability definitions (D-01).
- [Phase 03]: Input/output schemas reference existing Pydantic models directly (D-02).
- [Phase 03]: Handler dispatch uses direct callable references (D-03).
- [Phase 03]: MCP server at src/construct/mcp/server.py uses stdio transport (D-09).
- [Phase 03]: `construct-workspace-validate` is the first skill migrated to MCP (D-07).
- [Phase 04]: Skill migration pattern established: allowed-tools restricted, CLI/MCP invocation, INPUT/OUTPUT documentation.
- [Phase 04]: governance.yaml reading preserved as Read (config file, not data scanning).
- [Phase 04]: LLM-judgment sections preserved for ambiguous promotions and connection typing.
- [Phase 04]: Composed skill pattern: curation-cycle delegates to card-evaluate skill for promotion scan.
- [Phase 04]: construct ingest source is the CLI entry point for ref/seed card creation.
- [Phase 04]: Workflow docs get additive Inputs/Outcome/Error Handling sections; existing procedure preserved.
- [Phase 04]: help CLI command renamed to help_cmd to avoid shadowing Python built-in.
- [Phase 04]: Note text stored as abstract on ReferenceRecord (no dedicated note field).
- [Phase ?]: completed_steps counts only successful steps, enabling resume from the failed step.
- [Phase ?]: No SpikeRunner class — functional module-level pattern matches existing pipelines (bridge_detect, ingestion).
- [Phase ?]: Command injection safety via shlex.quote() + shlex.split() → subprocess.run without shell=True.
- [Phase ?]: register_spike_commands() kept decoupled from cli.py — CLI wiring deferred to future integration.
- [Phase ?]: Streamlit: add streamlit>=1.35 as hard dependency.
- [Phase ?]: Capability runner: dynamic form from JSON Schema per PRD 10.2.
- [Phase ?]: Gate review: approve/reject with typed handler arguments.
- [Phase ?]: Tag extraction uses hybrid regex approach (not LLM) within agent's discretion per D-07.
- [Phase ?]: Approved tags become SearchCluster entries in search-seeds.json (not seeds array).
- [Phase ?]: Confidence scoring: frequency 0-0.5 + length 0-0.3 + substance 0-0.2.

- [v0.4 Roadmap]: Use the research-recommended sequence W1–W6 as Phases 8–13.
- [v0.4 Roadmap]: API/runtime parity is explicit in each relevant phase; final all-capability registry and CLI/MCP parity closes in Phase 13.
- [v0.4 Roadmap]: Human review remains mandatory before research ingest, lifecycle, or connection writes.

### Pending Todos

- Plan Phase 8 with `/gsd-plan-phase 8`.
- During Phase 10/12 planning, decide exact skill migration timing while preserving API-04 closure in Phase 12.

### Blockers/Concerns

- No current blockers.
- Phase 10 needs focused design for WorkflowRunner/LangGraph checkpoint ownership and CLI review UX.
- Phase 12 needs focused design for curation candidate/proposal semantics.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Product Expansion | Full v0.5 browser-first shell | Deferred past v0.4 | 2026-06-21 |
| Runtime cleanup | Broad RT-01/RT-02 registry cleanup for views/spike/tag | Deferred unless blocking workflows | 2026-06-21 |
| Views | Full `views.generate_data` emission | Deferred; optional warning-only hooks allowed | 2026-06-21 |
| Historical debt | v0.3 verification/Nyquist/security documentation gaps | Deferred outside v0.4 core | 2026-06-21 |
| Phase 3 | Full skill migration beyond construct-workspace-validate | Batch 2 complete (Phase 04 P04) | 2026-06-10 |
| Phase 04 | construct knowledge card list CLI command | Not yet implemented (documented in gap-analysis as target pattern) | 2026-06-10 |
| UAT | Phase 06 06-UAT.md [partial] — 1 issue / 1 blocked, 0 pending scenarios | Acknowledged at v0.3 close | 2026-06-16 |
| UAT | Phase 07 07-HUMAN-UAT.md [passed] — milestone re-audit item resolved, 0 pending | Acknowledged at v0.3 close | 2026-06-16 |
| Tech debt (v0.4) | RT-01/RT-02 registry-bypass + direct-import groups; curation no-ops; views.generate_data stub; ADV-03 emission; SPK-04 entry point; CR-02 help.py layout; per-phase VERIFICATION/Nyquist/SECURITY coverage | See milestones/v0.3-MILESTONE-AUDIT.md | 2026-06-16 |

## Session Continuity

Last session: 2026-06-21T15:22:43.663Z
Stopped at: Phase 8 context gathered
Resume file: .planning/phases/phase-008/8-CONTEXT.md
