---
gsd_state_version: 1.0
milestone: v0.4.1
milestone_name: Surface Integration & Documentation Truth
current_phase: 17
current_phase_name: Architecture Doc Set & daily.run Discoverability
status: planning
stopped_at: Phase 17 context gathered
last_updated: "2026-07-25T14:45:37.801Z"
last_activity: 2026-07-25
last_activity_desc: Phase 16 complete, transitioned to Phase 17
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 16
  completed_plans: 16
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-07)

**Core value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.  
**Current focus:** Phase 16 — invocation-user-doc-truth

## Current Position

Phase: 17 — Architecture Doc Set & daily.run Discoverability
Plan: Not started
Status: Ready to plan
Progress: [██████████] 100% (0/4 phases)
Last activity: 2026-07-25 — Phase 16 complete, transitioned to Phase 17

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
| 14 | 4 | - | - |
| 15 | 5 | - | - |
| 16 | 7 | - | - |

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
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 14 P01 | 12m | 2 tasks | 2 files |
| Phase 14 P04 | 14m | 3 tasks | 3 files |
| Phase 14 P02 | 9min | 2 tasks | 1 files |
| Phase 14 P03 | ~14m | 3 tasks | 2 files |
| Phase 15 P01 | 21min | 3 tasks | 18 files |
| Phase 15 P02 | 24min | 3 tasks | 4 files |
| Phase 15 P03 | 38min | 3 tasks | 7 files |
| Phase 15 P04 | 34min | 3 tasks | 6 files |
| Phase 15 P05 | ~45min | 3 tasks | 14 files |
| Phase 16 P01 | 3min | 3 tasks | 2 files |
| Phase 16 P02 | ~14m | 3 tasks | 7 files |
| Phase 16 P03 | 25m | 3 tasks | 8 files |
| Phase 16 P04 | 12m | 3 tasks | 4 files |
| Phase 16 P05 | 35 min | 3 tasks | 3 files |
| Phase 16 P06 | ~55 min | 3 tasks | 4 files |
| Phase 16 P07 | ~15 min | 3 tasks | 4 files |

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
- [Phase ?]: .construct/workflow/*.sqlite is sanctioned durable orchestration state holding pending human-review decisions not reconstructible from layer 1 (adr-0004)
- [Phase ?]: The workspace rebuild guarantee is scoped to knowledge state, not the whole workspace (adr-0004)
- [Phase ?]: adr-0004 is a new ADR rather than an amendment to adr-0003, for discoverability; it discharges Phase 10 D-02
- [Phase ?]: [Phase 14-04]: resolve_llm_config_path extracted as a pure refactor so the ops UI and load_llm_config share one resolution code path (D-10/Q1)
- [Phase ?]: [Phase 14-04]: sidebar LLM config path is a read-only caption, not a disabled input — an editable path wired to a loader would make the ops dashboard an arbitrary-file-read primitive
- [Phase 14]: nfrs.md §2's rebuild guarantee is scoped by naming knowledge state explicitly, not by softening wording — a guarantee that lists what it covers stays auditable
- [Phase 14]: nfrs.md §3 names src/construct/llm/config.yaml as the LLM config authority; model-routing.yaml marked deprecated and inert, retained only for REQUIRED_PATHS workspace-contract stability
- [Phase 14]: nfrs.md §4's Tavily row leads with default_provider: mock so a reader stopping after one sentence has a true picture — corrects the record without over-correcting into a false egress claim
- [Phase ?]: `.construct/workflow/*.sqlite` filed under a new fourth artifact class in workspace-contract.md, not Support — the Support preamble's denial of workspace truth is the falsehood DOC-03 removes
- [Phase ?]: model-routing.yaml rows annotated as deprecated rather than deleted in workspace-contract.md and config-topology.md — D-01 keeps it a REQUIRED_PATHS entry
- [Phase ?]: config-topology.md's Python-approach comparison cell left intact as historically accurate; Phase 17 (D-03) may discard these edits wholesale
- [Phase ?]: Views parsers vendored into construct.views.lib via git mv (D-08); intra-package imports kept explicit-relative so zero import lines changed
- [Phase ?]: F6 Option A: declared pyyaml>=6 rather than porting vendored parsers to ruamel.yaml; ruamel port deferred to v0.6
- [Phase ?]: views models are reconciled to parser output, not the other way round: parsers are ground truth, spec-v02-data-model.md corroborates (D-02)
- [Phase ?]: DomainRecord.cross_domain_links typed as a bare list — three element shapes exist in the wild and parse_domains guards it with only isinstance(list)
- [Phase ?]: [Phase 15-03]: GenerateReport->OperationResult: success requires report.success AND zero validation_errors; warnings are advisory and reach only message/data, never errors (D-04)
- [Phase ?]: [Phase 15-03]: -w dropped outright on both views commands rather than kept as an alias — a workspace-lettered flag for an install-root option perpetuates the misnaming D-05/D-06 correct
- [Phase ?]: [Phase 15-03]: views group stays out of the capability registry (D-03) — CLI and MCP reach generate() by independent paths, RT-01/RT-02 stays open, drift covered by tests on both paths
- [Phase ?]: views.confirm_refresh is a verbosity switch, not a pre-run confirmation — it never gates the refresh
- [Phase ?]: The views refresh config gate reads the install root's .construct/config.yaml, not llm/config.py (wrong scope, extra=forbid)
- [Phase ?]: _sanitize_error replicated into the views layer rather than imported, to keep the llm -> views dependency edge one-way
- [Phase ?]: [Phase 15-05]: adr-0005 records the D-11 reversal of Phase 13 D-10 — the Python capability layer owns the views refresh and every workflow capability refreshes; new numbered ADR over amendment, archived D-10 record cited read-only
- [Phase ?]: [Phase 15-05]: the two live debounced-hook.sh registrations in construct-card-create/card-connect were removed with the debounce pair — direct per-card edits now have NO views refresh path, and views.per_card_hooks.* is inert config (v0.6 backlog, OQ-3)
- [Phase ?]: [Phase 15-05]: the three views-refresh doc sections were DELETED rather than corrected — the Python layer owns the behaviour, so the instruction has no correct form in a skill/workflow doc; each file keeps a one-sentence D-11 pointer
- [Phase ?]: Fixed the allowed-tools frontmatter parser to read both dialects rather than reshaping construct-synthesis's list-style frontmatter
- [Phase ?]: Kept test_docs_contain_invocations alongside the new per-doc non-vacuity guard — global regex coverage and per-doc coverage are complements
- [Phase ?]: 16-04: construct-synthesis web grants removed; refs/ lookup rewritten onto Read per D-03 (no ref sub-app)
- [Phase ?]: 16-04: FIX-03 reverted to Pending — 16-03 marked it Complete while _KNOWN_BROKEN still holds 2 workflow entries; 16-06 closes it
- [Phase ?]: Doc CLI cells must execute, not just resolve: the invocation guard validates the command path only, so a cell can pass every contract test and still fail with a Typer usage error when copied verbatim (16-05, 19 such defects found)
- [Phase ?]: 16-06: _KNOWN_BROKEN emptied by supersession, not by narrowing the guard — _DOC_GLOBS still holds 3 entries. Terminal signature is '0 3'; '0 2' would mean the guard was weakened.
- [Phase ?]: 16-06: no mock search provider exists — offline runnability comes from commands degrading with structured reporting, not from a stub provider.
- [Phase ?]: 16-06: research run -> review -> resume is credential-marked (offline it fails on a scoring outage before the review gate); the durable-checkpoint property is additionally covered offline by curation inspect/review.
- [Phase ?]: [Phase 16-07]: _DOC_GLOBS widened 3->5 (USER_GUIDE.md, commands.md); allowlist held empty over the widened surface — signature 0 5, the strongest form of FIX-03 (empty after widening, not narrowing)
- [Phase ?]: [Phase 16-07]: glob extension deliberately last — globbing the user docs before 16-05's CLI columns landed would have passed over an empty invocation set, the drift class the phase eliminates
- [Phase ?]: [Phase 16-07]: D-09 part two satisfied by the HUMAN's offline playbook run on a fresh test workspace, recorded faithfully as a clean pass on user authority; no D-07 violation surfaced

### Pending Todos

- Execute Phase 14 with `/gsd-execute-phase 14` — 4 plans, 2 waves.
- Phase 15 planning must settle two named decisions before implementation: `install_root` vs `workspace` contract (`catalog.py:149-150` vs `views/generate.py:175`) and the deployed-skill-directory import coupling (`generate.py:43-51`).
- Phase 16 planning must decide `knowledge card list` / `knowledge ref list`: implement, or rewrite `construct-synthesis` and `construct-gap-analysis` onto existing commands.
- ~~Phase 16: retiring `USER-TEST-PLAYBOOK-v03.md` (DOC-04) removes the `workflow run` / `workflow resume` allowlist entries — coordinate so the guard ends empty, not merely unscanned.~~ **Resolved by 16-06:** the playbook was superseded rather than deleted — `USER-TEST-PLAYBOOK-v041.md` took its place in `_DOC_GLOBS`, which still holds 3 entries. `_KNOWN_BROKEN` is empty with the suite green. Terminal signature `0 3`, verified.

### Blockers/Concerns

- No current blockers.
- v0.5 planning is blocked on DOC-03 (Phase 14) — the durable-checkpointer invariant must be settled before a UI-primary shell reasons about resumable gate state.
- Watch scope on FIX-01: RT-01/RT-02 registry unification stays out of v0.4.1 except, if unavoidable, the views command group alone.
- generate() validates an adapted projection but writes the raw parser dict, so the schema gate does not validate the bytes the SPA consumes — Plan 03 must decide before wiring a real handler
- views validate rejects 3 of 8 files views generate writes (stats.json, <ws>/connections.json, <ws>/events.json): generate() validates an adapted projection but writes the raw parser dict. Pre-existing, escalated by 15-03 as a Rule 4 contract decision, pinned by test_views_validate_does_not_yet_accept_generated_bytes. Needs an owner before Phase 16/17 SPA contract work.
- T-15-12 mitigation is weaker than the threat register states: a daily cycle's later views sweeps are full 11-file rebuilds (children mutate the workspace), not near-no-ops. version.json churns ~3x per cycle — re-score before Phase 17 SPA polling.
- decay_scan's 'archiving deferred to Phase 12' summary string in curation_run.py:414 is now stale (Phase 12 shipped) — second instance of the T-15-14 audit-trail-that-lies class, out of Plan 04's scope. Phase 16 to decide.
- Direct card-create/card-connect edits no longer refresh views: the debounce pair was deleted with its two live skill registrations (15-05) and has no Python-layer equivalent. views.per_card_hooks.* in templates/config.yaml, references/commands.md:81 and README.md:263-264 now document an inert feature — Phase 16 (DOC-04) doc-truth item; re-homing debounce is a v0.6 candidate (OQ-3).
- DOC-04 is marked Complete in REQUIREMENTS.md but both test_key_docs_are_not_vacuous cases (USER_GUIDE.md, commands.md) still fail. 16-05 owns these docs; flagged by 16-04, not edited (DOC-04 outside 16-04's frontmatter).

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

Last session: 2026-07-25T14:45:37.791Z
Stopped at: Phase 17 context gathered
Resume file: .planning/phases/17-architecture-doc-set-daily-run-discoverability/17-CONTEXT.md

## Operator Next Steps

- Run `/gsd-execute-phase 14` to execute Durable-State & Config Truth (DOC-03, FIX-02) — Wave 1: 14-01, 14-04; Wave 2: 14-02, 14-03.
- Reference `.planning/milestones/v0.4-MILESTONE-AUDIT.md` throughout — it carries file:line evidence for every requirement.
- Do not start v0.5 planning until Phase 14 lands: DOC-03 gates v0.5 design.
