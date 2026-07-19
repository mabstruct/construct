---
gsd_state_version: 1.0
milestone: v0.4.1
milestone_name: Surface Integration & Documentation Truth
current_phase: 14
status: planned
stopped_at: Phase 14 planned
last_updated: "2026-07-19T19:54:07.102Z"
last_activity: 2026-07-19
last_activity_desc: Phase 14 planned — 4 plans in 2 waves
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 4
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-07)

**Core value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.  
**Current focus:** v0.4.1 Surface Integration & Documentation Truth — Phases 14–17 roadmapped, 9/9 requirements mapped. Next: `/gsd-execute-phase 14`.

## Current Position

Phase: 14 — Durable-State & Config Truth (planned)
Plan: — (0/4 complete)
Status: Ready to execute
Progress: [░░░░░░░░░░] 0% (0/4 phases)
Last activity: 2026-07-19 — Phase 14 planned: 4 plans in 2 waves (DOC-03, FIX-02)

## Performance Metrics

**Velocity:**

- v0.4 plans completed: 2
- v0.4 total plans: TBD
- v0.3 shipped history: 7 phases / 25 plans

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 8 | TBD | - | - |
| 08 | 3 | - | - |
| 09 | 4 | - | - |
| 10 | 5 | - | - |
| 11 | 3 | - | - |
| 13 | 3 | - | - |

**Recent Trend:**

- Last completed milestone: v0.3 shipped 2026-06-16 with 0 unsatisfied requirements.
- Trend: v0.4 ready to begin planning from Phase 8.

| Phase 09 P02 | 20min | 2 tasks | 5 files |
| Phase 09 P03 | 25min | 2 tasks | 2 files |
| Phase 11 P01 | 20min | 3 tasks | 3 files |
| Phase 11 P02 | 25min | 3 tasks | 1 files |
| Phase 11 P03 | 20min | 3 tasks | 4 files |
| Phase 12 P02 | 15min | 3 tasks | 3 files |
| Phase 12 P03 | 25min | 2 tasks | 2 files |

## Accumulated Context

### Roadmap Evolution

- v0.3 shipped Phases 1–7 and remains preserved in ROADMAP.md with full details archived under `.planning/milestones/`.
- Phase 7 added: Close v0.3 blockers (RT-03 MCP parity, ING-02 ingest cluster, ING-05 graph.status) — from milestone audit 2026-06-15.
- v0.4 started as Agent Workflows milestone: search provider spine, research.run, curation.run, thin skill migrations, and daily-cycle composition. v0.5 UI and unrelated v0.3 carry-over debt remain deferred unless directly required.
- v0.4 continues numbering at Phase 8 and contains 6 phases: search spine, score gate, reviewed research run, curation PIPE, curation gates, daily-cycle composition.
- v0.4.1 continues numbering at Phase 14 and contains 4 phases: durable-state & config truth (14), views.generate_data resolution (15), invocation & user-doc truth (16), architecture doc set & daily.run discoverability (17). Patch milestone — no phase adds runtime capability.
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
- [v0.4.1 Roadmap]: Phases grouped by "what decision unblocks what work", not by requirement-ID prefix — DOC-03/FIX-02 decisions first (Phase 14), then the FIX-01 code decision (Phase 15), then the surfaces that must describe both (Phases 16–17).
- [v0.4.1 Roadmap]: DOC-03 placed in the first phase because it gates v0.5 design; v0.5 planning must not start before Phase 14 lands.
- [v0.4.1 Roadmap]: FIX-01 kept as its own phase despite being a single requirement — its `install_root` vs `workspace` and skill-directory-coupling decisions determine the content of four documented callers rewritten in Phases 16–17.
- [v0.4.1 Roadmap]: DOC-01 deliberately sequenced last of the architecture docs so it is written once, against decisions already made in Phases 14–15.
- [v0.4.1 Roadmap]: FIX-04's shrinking `_KNOWN_BROKEN` allowlist is the completion criterion for FIX-01 and FIX-03 — phase success criteria cite it mechanically rather than in prose.
- [v0.4.1 Roadmap]: FIX-04 is intentionally unmapped to any phase (pre-milestone deliverable, commit `11f20f4`).
- [Phase 09-02]: key_findings cleared on clamp-to-skip with clamp rationale appended to reasoning (D-14 / Pitfall 5)
- [Phase 09-02]: score_one takes a pre-built llm (mock-injectable); factory.build_chat_model seam lives in build_scoring_llm for the Plan 03 runner
- [Phase 09-02]: GovernanceThresholds dataclass decouples clamp/score_one from full GovernanceConfig and carries the D-06 echo fields
- [Phase 09-03]: score_all uses a sync ThreadPoolExecutor(max_workers=cap) for bounded fan-out — async gather does not honor the cap (D-04 / Pitfall 2)
- [Phase 09-03]: degraded (partial item failure) vs total-outage (all provider/auth failures) discriminated by cause — partial degrades, total promotes to a gate error mapped to success=False by the Plan 04 shim (D-08 vs D-09)
- [Phase 09-03]: provider errors sanitized to class name + safe message (mirrors research_search._safe_error_message) — never echo raw text that may carry a key (T-09-03)
- [Phase ?]: [Phase 11-01]: curation fixtures write connections at canonical root connections.json matching WorkspaceLoader.load_connections
- [Phase ?]: [Phase 11-01]: curation contract test imports CurationRunResult lazily so test_mcp_no_hardcoded_curation stays GREEN while the module is unbuilt
- [Phase 11-02]: curation_run is a linear interrupt-free sibling of research_run — findings-only decay/orphan scans, deferred nodes as explicit skipped/required=False steps, D-09 degraded iff a required step failed/skipped
- [Phase 11-02]: _initial_state(inp) single-arg form (matches Plan 01 red suite); run_id derived inside from inp.run_id or _new_run_id()
- [Phase ?]: [Phase 11-03]: curation.run/inspect registered with cli_name+mcp_tool_name; MCP parity free via registry auto-discovery (no mcp/server.py edit); inventory tests grown to match
- [Phase 12-02]: PromotionDecision + CardEvaluateInput defined in curation_promote.py (extra=forbid) to avoid catalog.py circular import; target_lifecycle limited to growing|mature|None; connection-typing input is a bridge_detect candidate pair with a required ConnectionType enum
- [Phase 12-03]: interrupt-only process_inbox keyed by the module constant _CURATION_GATE_ID ("curation.review", never state["gate_id"]); three producers append into ONE operator.add gate_queue before the single pause; empty-queue conditional short-circuit means offline no-mock runs (provider total-outage → zero proposals) complete without pausing, keeping every legacy Phase-11 test green
- [Phase 12-03]: added a minimal resume-only review_curation_run in Plan 03 (its -k target test_single_consolidated_gate calls it) with NO write nodes; Plan 04 grafts the post-gate apply nodes onto the same runner

### Pending Todos

- Execute Phase 14 with `/gsd-execute-phase 14` — 4 plans, 2 waves.
- Phase 15 planning must settle two named decisions before implementation: `install_root` vs `workspace` contract (`catalog.py:149-150` vs `views/generate.py:175`) and the deployed-skill-directory import coupling (`generate.py:43-51`).
- Phase 16 planning must decide `knowledge card list` / `knowledge ref list`: implement, or rewrite `construct-synthesis` and `construct-gap-analysis` onto existing commands.
- Phase 16: retiring `USER-TEST-PLAYBOOK-v03.md` (DOC-04) removes the `workflow run` / `workflow resume` allowlist entries — coordinate so the guard ends empty, not merely unscanned.

### Blockers/Concerns

- No current blockers.
- v0.5 planning is blocked on DOC-03 (Phase 14) — the durable-checkpointer invariant must be settled before a UI-primary shell reasons about resumable gate state.
- Watch scope on FIX-01: RT-01/RT-02 registry unification stays out of v0.4.1 except, if unavoidable, the views command group alone.

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

Last session: 2026-07-19T19:54:07.102Z
Stopped at: Phase 14 planned — 4 plans, 2 waves
Resume file: .planning/phases/14-durable-state-config-truth/14-01-PLAN.md

## Operator Next Steps

- Run `/gsd-execute-phase 14` to execute Durable-State & Config Truth (DOC-03, FIX-02) — Wave 1: 14-01, 14-04; Wave 2: 14-02, 14-03.
- Reference `.planning/milestones/v0.4-MILESTONE-AUDIT.md` throughout — it carries file:line evidence for every requirement.
- Do not start v0.5 planning until Phase 14 lands: DOC-03 gates v0.5 design.
