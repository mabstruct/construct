# Roadmap: CONSTRUCT

## Overview

This roadmap hardens CONSTRUCT's Claude-native foundation first (v0.3), then migrates multi-step skill workflows to Python LangGraph/LangChain (v0.4), then reconnects that runtime to the surfaces users and agents touch (v0.4.1), then delivers a browser-first UI-primary shell (v0.5) — without pulling UI work ahead of proven workflow and runtime behavior.

## Milestones

- ✅ **v0.3 Claude-Native Runtime & Workflow Hardening** — Phases 1–7 (shipped 2026-06-16)
- ✅ **v0.4 Agent Workflows (LangGraph / LangChain)** — Phases 8–13 (shipped 2026-07-07)
- ✅ **v0.4.1 Surface Integration & Documentation Truth** — Phases 14–17 (shipped 2026-07-25)
- 🚧 **v0.5 UI-Primary Experience (Proof of Concept)** — Phases 18–24 (roadmapped 2026-07-26)

## Phases

<details>
<summary>✅ v0.3 Claude-Native Runtime & Workflow Hardening (Phases 1–7) — SHIPPED 2026-06-16</summary>

Full phase detail (goals, success criteria, plans) archived in
[`milestones/v0.3-ROADMAP.md`](milestones/v0.3-ROADMAP.md). Milestone audit:
[`milestones/v0.3-MILESTONE-AUDIT.md`](milestones/v0.3-MILESTONE-AUDIT.md).

- [x] **Phase 1: Contract Canon & Artifact Governance** — canonize schemas, write gates, spec-aligned contracts (completed 2026-06-08)
- [x] **Phase 2: Governed Knowledge Operations** — reliable card/ref/connection/storage ops (completed 2026-06-10)
- [x] **Phase 3: Capability Registry, CLI & MCP Spine** — one shared runtime contract + stdio MCP server (completed 2026-06-12)
- [x] **Phase 4: Guided Workflow Operability** — state-aware help/ingestion/workflow runner + resume (completed 2026-06-10)
- [x] **Phase 5: Grounded Synthesis & Graph Reasoning** — bounded Q&A, synthesis, bridge detection (completed 2026-06-11)
- [x] **Phase 6: Derived Data, Ops UI & Governed Spikes** — view data contracts, Streamlit ops UI, governed spikes (completed 2026-06-11)
- [x] **Phase 7: Close v0.3 blockers** — RT-03 MCP schema parity, ING-02 ingest cluster validation, ING-05 graph.status wiring (completed 2026-06-16)

</details>

<details>
<summary>✅ v0.4 Agent Workflows (LangGraph / LangChain) (Phases 8–13) — SHIPPED 2026-07-07</summary>

Full phase detail (goals, success criteria, plans) archived in
[`milestones/v0.4-ROADMAP.md`](milestones/v0.4-ROADMAP.md). Milestone audit:
[`milestones/v0.4-MILESTONE-AUDIT.md`](milestones/v0.4-MILESTONE-AUDIT.md).

**Milestone Goal:** Move CONSTRUCT's highest-value multi-step workflows from opaque Claude-native procedures into testable, model-agnostic LangGraph/LangChain pipelines while preserving the existing workspace format and current skill UX.

- [x] **Phase 8: Search Provider Spine + Contract Foundation** — provider-agnostic `research.search`, normalized search contracts, config/caps, degraded errors, and offline provider tests. (completed 2026-06-21)
- [x] **Phase 9: LLM Provider Factory + research.score** — model-agnostic structured scoring that turns normalized search results into governed finding proposals. (completed 2026-06-28)
- [x] **Phase 10: Durable Human Review + research.run** — reviewed, resumable research workflow with deduplication, approved ingest, digest, seed updates, and events. (completed 2026-06-28)
- [x] **Phase 11: Curation PIPE Steps** — real deterministic curation checks and reports replace v0.3 placeholder success responses. (completed 2026-06-29)
- [x] **Phase 12: Curation L3 Gates + Review Application** — promotion and connection proposals use reusable human review before canonical writes, with migrated skills. (completed 2026-07-05)
- [x] **Phase 13: Daily-Cycle Composition** — parent daily workflow composes stable research and curation capabilities with final CLI/MCP and compatibility parity. (completed 2026-07-07)

</details>

<details>
<summary>✅ v0.4.1 Surface Integration & Documentation Truth (Phases 14–17) — SHIPPED 2026-07-25</summary>

Full phase detail (goals, success criteria, plans) archived in
[`milestones/v0.4.1-ROADMAP.md`](milestones/v0.4.1-ROADMAP.md). Basis audit:
[`milestones/v0.4-MILESTONE-AUDIT.md`](milestones/v0.4-MILESTONE-AUDIT.md).

**Milestone Goal:** Reconnect the sound v0.4 runtime to the surfaces users and agents actually touch — every documented invocation path resolves and executes, the v0.4 runtime is discoverable by both users and agents, and the architecture doc set describes the system that actually exists. Integration defects in shipped work, not new capability.

- [x] **Phase 14: Durable-State & Config Truth** — settle the durable-checkpointer and LLM-config decisions and record them in the invariant docs; gates v0.5 design (DOC-03, FIX-02). (completed 2026-07-19)
- [x] **Phase 15: views.generate_data Resolution** — remove the permanent-failure stub from the MCP surface, vendor the views library, own post-run refresh in the Python layer (FIX-01, adr-0005). (completed 2026-07-20)
- [x] **Phase 16: Invocation & User-Doc Truth** — empty the `_KNOWN_BROKEN` allowlist, close the synthesis tool-grant exception, make the user doc set executable (FIX-03, DEC-01, DOC-04). (completed 2026-07-25)
- [x] **Phase 17: Architecture Doc Set & daily.run Discoverability** — rewrite the architecture inventory against the Phase 14–15 decisions and give the flagship daily cycle a chat entry point (DOC-01, DOC-02, UX-01). (completed 2026-07-25)

</details>

### 🚧 v0.5 UI-Primary Experience — Proof of Concept (Phases 18–24)

**Milestone Goal:** Prove on an isolated branch that a browser-first shell over the v0.4 runtime can guide a user through CONSTRUCT's core loops without touching the CLI — a technical *and* UX proof of concept, judged on whether the guided/wizard model actually makes the system usable unaided.

**Branch:** all v0.5 work lands on `dev-v05` (off `main`, pushed to origin). `main` stays releasable at v0.4.1. The stale `dev-v04` branch is left untouched.

- [x] **Phase 18: Contract & Governance Foundations** - Make the byte contract, the invocation seam, and the review-decision model honest before any browser depends on them (completed 2026-08-02)
- [ ] **Phase 19: HTTP API over the Capability Registry** - The third registry adapter — generated routes, workspace ids, one error shape, loopback hardening, runs as resources
- [ ] **Phase 20: Real Document Extraction** - Ingestion reads the file it routes; "no extractable text" becomes a named outcome, not a silent success
- [ ] **Phase 21: Served App Shell & Guided Action Layer** - The SPA becomes a first-class served app and `help.suggest` becomes an action engine — the earliest UX signal
- [ ] **Phase 22: Wizard Flows** - Workspace creation, document ingestion, and the two HITL review gates completable entirely in the browser
- [ ] **Phase 23: Live-Data Browse — Workspaces, Wiki, Graph** - Find and read the knowledge: workspace list, wiki reading view, focused graph, deep links
- [ ] **Phase 24: Evaluation Spikes, E2E Demo Gate & UX Verdict** - The milestone answers its own question in writing, on evidence

## Phase Details

> Phases 1–17 are shipped; their detail is archived under [`milestones/`](milestones/).
> The sections below are the active v0.5 milestone.

### Phase 18: Contract & Governance Foundations

**Goal**: Every contract a browser will depend on tells the truth before a browser exists — the views projection validates against its own validator, all invocation surfaces validate against one seam, and a human-review decision cannot be misapplied.
**Depends on**: Nothing (first v0.5 phase). Runs in parallel with Phase 19; VFIX-01 does not block the API, only the *trusting* of browse data.
**Requirements**: VFIX-01, GOV-01, GOV-02, GOV-03, GOV-04, GOV-05
**Success Criteria** (what must be TRUE):

  1. `views validate` accepts every one of the 8 files `views generate` writes, proven by a non-vacuous round-trip guard that *replaces* `test_views_validate_does_not_yet_accept_generated_bytes` rather than deleting it.
  2. The same capability id and payload produce an identical structured result whether invoked from the CLI or from MCP, and an unknown field is rejected on both — proven by a differential test over one shared validating seam, not by set-membership inventory.
  3. A human-review decision names the proposal it applies to; a resume against a queue that changed since it was rendered is rejected with zero canonical writes, and a missing decision never falls back to applying a write.
  4. No surface writes canonical truth outside the reviewed workflow's resume path — satisfied by removing the Streamlit gate-review screen (D-13) and guarded by a repo-wide source-level test rather than by the absence of one named file — **and** no approval event exists for a decision that was never applied. *(Restated per D-14: the original wording named the gate-review screen as its subject, and D-13 deletes that screen. Both halves stand independently; the second is enforced by D-16's conditional emission.)*
  5. A degraded or partially-applied run reports degraded on every surface that can report it, and escalated items surface as pending rather than folded into a success count.

**Why first**: All five GOV items are repairs to *live* code found by the research (`ui/gate_review.py:252-281`, inert `input_model` validation, positional `_resolve_decisions`), not new-build concerns. GOV-01 must land with or before the HTTP adapter because HTTP is the surface that forces the question; GOV-02/GOV-03 must land before the review wizards so the API is never built against the positional decision shape.
**Named decision to record**: the views byte-contract fix conforms `views/models.py` to the written bytes. On its face this looks like a reversal of the standing "conform the data to the gate" decision (ING-02) — it is not, because views is a derived projection whose author is the generator, but it must be recorded explicitly as a decision, not slipped in. *(Recorded as D-01; the reconciliation is written into the `views/models.py` module docstring by plan 18-04.)*
**Open decision carried in**: `gate_review.py`'s disposition (fix, fence, or delete) — research states that leaving a second UI that forges gates is worse than either keeping or deleting it. *(Resolved as D-13: delete, with the removal made permanent by a category-level source guard in plan 18-07.)*
**Plans**: 8/8 plans executed

Plans:
**Wave 1**

- [x] 18-01-PLAN.md — GOV-01 tracer: one validating invocation seam, proven end-to-end on one capability across the real CLI process and real MCP dispatch (wave 1)
- [x] 18-04-PLAN.md — VFIX-01: conform the views contract models to the writer bytes, pick the canonical `events.json` shape, model the two ungated files (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 18-02-PLAN.md — GOV-01: forbid-by-default across every capability input model, and the five capabilities whose model does not describe their handler (wave 2)
- [x] 18-05-PLAN.md — VFIX-01: validating writer with no adapter, canonical SPA event reader, and the round-trip guard that replaces the pin test (wave 2)
- [x] 18-06-PLAN.md — GOV-02/GOV-03: proposal-id decisions, complete-coverage rejection, checkpoint-id ETag, migrate-on-read (wave 2, one blocking decision checkpoint)
- [x] 18-07-PLAN.md — GOV-04: delete the second canonical writer and make "exactly one canonical writer" a source-level invariant (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 18-03-PLAN.md — GOV-01: every in-repo caller onto the seam, positional-passthrough shims retired, `views validate` registered as a capability (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 18-08-PLAN.md — GOV-04/GOV-05: honest escalation, approval events only after a write, degraded reads as degraded on all three surfaces (wave 4)

Waves: 1 → {01, 04} · 2 → {02, 05, 06, 07} · 3 → {03} · 4 → {08}. Same-wave plans have zero `files_modified` overlap.

### Phase 19: HTTP API over the Capability Registry

**Goal**: Every registry capability is reachable from a browser over a loopback-bound HTTP surface that is a third peer of CLI and MCP — never a fork of them — and a workflow run is an addressable resource that outlives the process that started it.
**Depends on**: Phase 18 for GOV-01 (the shared validating seam the adapter routes through). Otherwise independent — can start in parallel with Phase 18's VFIX-01 work.
**Requirements**: HTTP-01, HTTP-02, HTTP-03, HTTP-04, HTTP-05, HTTP-06, HTTP-07
**Success Criteria** (what must be TRUE):

  1. A user starts the server with one command and reaches every registry capability from a browser; the server binds loopback only, and adding a capability adds an endpoint with **zero** edits to the server module — guarded by a test, the same structural guarantee `mcp/server.py` already has.
  2. A request naming a workspace by id succeeds; a request carrying a filesystem path or a traversal (`workspace: "../../etc"`) is rejected with no filesystem effect.
  3. A known-failing input returns the same reason and suggestion strings over HTTP as over CLI and MCP — one error shape across three surfaces, with no raw exception text or filesystem paths in the body.
  4. A request carrying a foreign `Origin`/`Host`, or missing the per-launch token, is refused before it reaches a capability.
  5. A workflow run started in the browser returns an id immediately, is pollable while it is still running, appears in a run listing even while paused, and is resumable from the CLI — and a run started from the CLI is resumable in the browser.

**Why this is the hard gate**: CONSTRUCT has no HTTP surface today (Typer CLI + stdio MCP only). Nothing browser-side in Phases 21–24 can exist before this lands.
**Open decision (OQ-4)**: the checkpoint concurrency contract — WAL / `busy_timeout` and single-flight locking for the sqlite checkpointer once a browser and a CLI can both resume the same run. Extends adr-0004.
**Research flag**: the localhost threat model (`Origin`/`Host` validation, per-launch token) and the `registry.invoke()` seam design carry real security consequences — worth a research pass during phase planning.
**Plans**: 3/10 plans executed

Plans:
**Wave 1**

- [x] 19-01-PLAN.md — Tracer: one browser-shaped request crosses the trust boundary, resolves a workspace by id in the seam, and reaches a real capability; plus `construct serve`'s failure modes (wave 1)
- [x] 19-02-PLAN.md — OQ-4: WAL and `busy_timeout` declared and pinned by test on both checkpointers, with the ADR-0004 concurrency extension (wave 1)
- [x] 19-03-PLAN.md — HTTP-04 shared boundary: one serializer and sanitizer for MCP and HTTP, the two success-path path leaks fixed, and a shrink-only baseline (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 19-04-PLAN.md — HTTP-03 at the seam: creation mode for `workspace.init`, launch-context `install_root` for `views.*`, classification cardinality, and the str/Path coercion proof over all 26 (wave 2)
- [ ] 19-05-PLAN.md — HTTP-02: the discovery endpoint, the machine-read COVERAGE ledger, and a non-vacuous cardinality coverage guard (wave 2)
- [ ] 19-06-PLAN.md — HTTP-05: the full Host/Origin/token matrix in one guard, and the proof that rejection precedes any capability effect (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 19-07-PLAN.md — HTTP-04 completion: `model` becomes required, all four HTTP error emitters unified, and the differential parity table gains its third column (wave 3)
- [ ] 19-08-PLAN.md — HTTP-07: `workflow.list` spanning all three durable stores, registered on CLI, MCP and HTTP at once (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 19-09-PLAN.md — HTTP-06: runs as addressable resources — detached spawn, immediate id, pollable while running, cross-surface resume, visible failed spawn (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 19-10-PLAN.md — The two manual-only verifications: a real browser reaches the running server, and the token-delivery ergonomics verdict for Phase 21 (wave 5, one blocking human-verify checkpoint)

Waves: 1 → {01, 02, 03} · 2 → {04, 05, 06} · 3 → {07, 08} · 4 → {09} · 5 → {10}. Same-wave plans have zero `files_modified` overlap.

### Phase 20: Real Document Extraction

**Goal**: Ingesting a document actually reads it — the card it seeds stands for content that was extracted and measured, and a file that yields nothing says so.
**Depends on**: Nothing. **Deliberately front-loaded in parallel with Phases 18–19** — extraction has zero API dependency and is fully testable through the existing CLI and MCP surfaces, which de-risks the E2E demo gate (Phase 24) that the whole verdict mechanically rests on.
**Requirements**: EXTR-01, EXTR-02, EXTR-03, EXTR-04, EXTR-05, EXTR-06
**Success Criteria** (what must be TRUE):

  1. Ingesting a pdf, txt, or md file produces a card seeded from text extracted out of that file — not a ref pointing at an unread file — and the extraction step is reachable as a registry capability from CLI and MCP, not only from a browser.
  2. An image-only, encrypted, or empty PDF is never reported as fully extracted; it reports a named "no extractable text" reason drawn from an enumerated failure taxonomy, and extraction status is derived from measured extractor yield rather than from caller-supplied title or metadata.
  3. A `.doc` or `.docx` file is detected and rejected with a "convert to pdf, txt, or md first" message rather than failing obscurely.
  4. Every fixture in the hostile-input set (oversized, mislabeled content type, XXE payload, zero-byte, CJK/UTF-16, 200-page) fails or succeeds cleanly with a sanitized message and no partial write; type is detected from file contents, never from a client-supplied type.

**Open decision (OQ-1)**: where uploaded bytes live. CONSTRUCT's file ingestion routes an *existing* path; an upload has no path. None of the three options (a new workspace artifact class, temp with dangling provenance, keep nothing and forgo re-extraction) is clearly right — this must be a recorded decision with its workspace-contract implications named, not defaulted into existence.
**Open decision (OQ-3)**: the extraction failure taxonomy — the enumerated list behind EXTR-03's named reasons, plus the fixture set that proves each one.
**Plans**: TBD

### Phase 21: Served App Shell & Guided Action Layer

**Goal**: A user opens a browser, sees the app the project ships, and is told what to do next — the milestone's earliest and cheapest UX signal.
**Depends on**: Phase 19 (there must be something to serve against and to call). Benefits from Phase 18 (a trustworthy data contract) but is not blocked by it.
**Requirements**: SHELL-01, SHELL-02, SHELL-03, GUIDE-01, GUIDE-02, GUIDE-03, GUIDE-04
**Success Criteria** (what must be TRUE):

  1. A user with no Node installed can install CONSTRUCT, run the serve command, and reach the app in a browser — the frontend ships prebuilt and its dependencies are pinned by a committed lockfile.
  2. An already-scaffolded per-workspace views build keeps working unchanged after promotion — nothing a user already has breaks.
  3. `help.suggest` returns a next step carrying a verb, a capability, and a destination for every priority state it can report, identically to CLI, MCP, and HTTP callers.
  4. A user sees prioritized next actions in the browser and launches each one directly from its suggestion, can see the evidence behind it, and never has one execute without explicitly confirming it.
  5. After a mutating action, the guidance list reflects the new workspace state without a manual reload; a healthy workspace renders as informational rather than as a nagging call to action.

**Why sequenced here**: `help.suggest` is a diagnosis engine today — it emits priorities and reasons but no verb, capability, or destination, and an LLM improvises that mapping in chat. With chat demoted, something must own it, or the guided layer degrades to a status widget and the UX verdict comes back "no" for reasons unrelated to the UI. It is also the cheapest item that carries the milestone's actual success criterion, so the signal must arrive while there is still milestone left to react to it.
**Resolved by requirement wording**: GUIDE-01 places the priority→action mapping in the *backend* ("available identically to CLI, MCP, and HTTP callers"), closing the research's open question in favour of one shared contract over a frontend-only lookup table.
**Phase obligation (gates EVAL-05)**: the UX verdict template must be written and committed **in this phase**, before any wizard or browse UI polish begins. A retrofitted verdict template is a documented PoC failure mode — fixed questions cannot be reverse-engineered from whatever shipped. Phase 24 verifies the commit ordering mechanically.
**Plans**: TBD
**UI hint**: yes

### Phase 22: Wizard Flows

**Goal**: A user can complete CONSTRUCT's write loops — create a workspace, ingest a document, and clear both human-review gates — entirely in the browser, without anything being written before they confirm it.
**Depends on**: Phase 18 (GOV-02/GOV-03 — proposal-id decisions and stale-queue detection must exist before the review wizards are built against them), Phase 19 (API + run resources), Phase 20 (real extraction — there is nothing to review without it), Phase 21 (a served shell). Can run in parallel with Phase 23.
**Requirements**: WIZ-01, WIZ-02, WIZ-03, WIZ-04, WIZ-05, WIZ-06, WIZ-07, WIZ-08, WIZ-09
**Success Criteria** (what must be TRUE):

  1. A user creates a workspace and sets up its first domain through a guided multi-step flow without touching the CLI.
  2. A user uploads a document, sees the extracted content previewed and the proposed routing before anything is written to disk, and can override that routing before confirming.
  3. Cancelling any wizard at any step leaves the filesystem exactly as it was — nothing is written before the confirm step — and every wizard shows step progress with non-destructive back navigation.
  4. A user reviews one queue of machine proposals (research findings; curation promotions, connections, and archives) with supporting evidence visible without a click, decides per item, can undo a decision before it is applied, and can accept all recommended items in one explicitly-labeled action with escalate-flagged items excluded.
  5. A review in progress survives navigation, refresh, and process restart — resuming from the durable checkpoint — and after applying, the user sees a summary of what was written and what was skipped, including partial success.

**Constraint that must not bend**: `approve_all` may exist as an explicit, consequence-labelled action; it is never a default and the UI never presses it on the user's behalf. The apply nodes sit strictly downstream of the human interrupt by construction, and a convenience button that inverts that turns propose-then-approve into auto-ingest.
**Research flag**: the ETag / optimistic-concurrency design for stale-queue detection and the sqlite concurrency contract (see OQ-4, Phase 19) are LangGraph-checkpointer-specific and not fully worked out — worth a research pass during phase planning.
**Plans**: TBD
**UI hint**: yes

### Phase 23: Live-Data Browse — Workspaces, Wiki, Graph

**Goal**: A user can find and read their knowledge — across workspaces, as a wiki, and as a graph — on data the running server serves, and can tell when what they are looking at is stale.
**Depends on**: Phase 18 (VFIX-01 — a trustworthy byte contract, or the pages get built twice), Phase 19, Phase 21. Can run in parallel with Phase 22.
**Requirements**: BRWS-01, BRWS-02, BRWS-03, BRWS-04, BRWS-05, BRWS-06, BRWS-07, BRWS-08
**Success Criteria** (what must be TRUE):

  1. A user sees every workspace under the install root and opens any one of them.
  2. A user reads a knowledge card in a wiki reading view where links resolve and provenance is visible — and the workspace landing is the dashboard, with the existing `workspace_landing === 'wiki'` redirect pinned off by a guard rather than merely avoided.
  3. A user opens the graph focused on a single card's local neighbourhood by default, searches and filters it, can tell what they are currently looking at, and opts in to the global view deliberately.
  4. A user moves between the wiki and the graph for the same card in both directions, and every card, wiki page, and graph node has a URL that can be shared and reopened.
  5. An empty or near-empty workspace renders a meaningful state rather than a blank canvas, and a user can tell when displayed data is stale relative to the workspace.

**Locked decisions honored**: D5/D8 (`spec-v02-knowledge-views-spike.md`, 2026-05-02) — the wiki is a sibling reading view, not the workspace default, and topic synthesis stays with the `synthesis` workflow. No auto-generated topic/hub pages; no in-place wiki editing (the views layer is a read-only derived projection).
**Open decision (OQ-2)**: the graph's data source at scale — the views JSON projection or live API traversal. This materially changes the cost of BRWS-04 and BRWS-05 and should be pinned down before planning, not during implementation.
**Plans**: TBD
**UI hint**: yes

### Phase 24: Evaluation Spikes, E2E Demo Gate & UX Verdict

**Goal**: The milestone answers its own question in writing, on evidence — three framework/format verdicts and one UX verdict, backed by a demo path that actually completes.
**Depends on**: Phase 19 (SEED-001 needs the real HTTP API to produce an honest verdict rather than a guess), and Phases 20–23 for the E2E gate and the UX verdict. Last by construction, not by habit.
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):

  1. Three verdict documents exist and each carries a recommendation — CoPilotKit evaluated against the running HTTP API rather than from documentation, graphify.net evaluated in the existing spike sandbox and answering the governance and egress questions, and open-wiki-format answering whether CONSTRUCT can emit an open format as a read-only projection without changing the canonical workspace format. A negative recommendation counts as a verdict; an absent one does not.
  2. On a fresh, offline workspace, a person uploads a PDF and reaches cards they can browse in both the wiki and the graph, with zero CLI intervention.
  3. A written UX verdict answers whether a person can navigate CONSTRUCT unaided, produced by someone actually attempting it on a fresh workspace — against the template whose commit predates the first wizard/browse UI commit, checkable in git history.
  4. The demo path renders degraded runs and escalated items honestly — no spinner or success state stands in for an outcome that did not happen, and "escalate" never implies an action it does not take.

**Open decision (OQ-5)**: does the PoC demo run on a fresh workspace or a fixture? Existing `test-ws/` fixtures carry pre-`4e2b909` damage (destroyed card bodies, newline accretion), which changes what the UX verdict actually measures. EVAL-04/05 currently specify fresh — confirm at planning.
**Research flag**: SEED-001 (CoPilotKit) and SEED-003 (open wiki format) are framed as *evaluations*, not established patterns — by definition under-researched until the spike runs.
**Plans**: TBD

## Coverage (v0.5 — active)

| Requirement | Phase | Status |
|-------------|-------|--------|
| VFIX-01 | Phase 18 | Pending |
| GOV-01 | Phase 18 | Pending |
| GOV-02 | Phase 18 | Pending |
| GOV-03 | Phase 18 | Pending |
| GOV-04 | Phase 18 | Pending |
| GOV-05 | Phase 18 | Pending |
| HTTP-01 | Phase 19 | Pending |
| HTTP-02 | Phase 19 | Pending |
| HTTP-03 | Phase 19 | Pending |
| HTTP-04 | Phase 19 | Pending |
| HTTP-05 | Phase 19 | Pending |
| HTTP-06 | Phase 19 | Pending |
| HTTP-07 | Phase 19 | Pending |
| EXTR-01 | Phase 20 | Pending |
| EXTR-02 | Phase 20 | Pending |
| EXTR-03 | Phase 20 | Pending |
| EXTR-04 | Phase 20 | Pending |
| EXTR-05 | Phase 20 | Pending |
| EXTR-06 | Phase 20 | Pending |
| SHELL-01 | Phase 21 | Pending |
| SHELL-02 | Phase 21 | Pending |
| SHELL-03 | Phase 21 | Pending |
| GUIDE-01 | Phase 21 | Pending |
| GUIDE-02 | Phase 21 | Pending |
| GUIDE-03 | Phase 21 | Pending |
| GUIDE-04 | Phase 21 | Pending |
| WIZ-01 | Phase 22 | Pending |
| WIZ-02 | Phase 22 | Pending |
| WIZ-03 | Phase 22 | Pending |
| WIZ-04 | Phase 22 | Pending |
| WIZ-05 | Phase 22 | Pending |
| WIZ-06 | Phase 22 | Pending |
| WIZ-07 | Phase 22 | Pending |
| WIZ-08 | Phase 22 | Pending |
| WIZ-09 | Phase 22 | Pending |
| BRWS-01 | Phase 23 | Pending |
| BRWS-02 | Phase 23 | Pending |
| BRWS-03 | Phase 23 | Pending |
| BRWS-04 | Phase 23 | Pending |
| BRWS-05 | Phase 23 | Pending |
| BRWS-06 | Phase 23 | Pending |
| BRWS-07 | Phase 23 | Pending |
| BRWS-08 | Phase 23 | Pending |
| EVAL-01 | Phase 24 | Pending |
| EVAL-02 | Phase 24 | Pending |
| EVAL-03 | Phase 24 | Pending |
| EVAL-04 | Phase 24 | Pending |
| EVAL-05 | Phase 24 | Pending |

**Coverage:** 48/48 v0.5 requirements mapped exactly once. Unmapped: 0. Duplicated: 0.

> **Count correction.** `REQUIREMENTS.md` summarised the milestone as "47 total"; the requirement
> list and the traceability table both contain **48** entries (VFIX 1, HTTP 7, GOV 5, EXTR 6,
> SHELL 3, GUIDE 4, WIZ 9, BRWS 8, EVAL 5). The prose count was off by one; no requirement was
> missing. The traceability table in `REQUIREMENTS.md` has been corrected to 48.

### v0.5 Sequencing Rationale

- **Two blockers, ordered first and run in parallel.** Phase 19 (HTTP adapter) is the universal hard
  gate — CONSTRUCT has no HTTP surface today, so literally nothing browser-side exists without it.
  Phase 18 (byte contract + governance seams) is the *other* prerequisite, but it blocks *trusting*
  browse data rather than building the API, so the two proceed together. GOV-01 sits in Phase 18
  because HTTP is the surface that forces the input-model-validation question, and the seam should
  exist before the third adapter routes through it.

- **Extraction (Phase 20) is deliberately front-loaded in parallel**, not sequenced behind the wizard
  that consumes it. It has zero API dependency, is fully testable through the existing CLI and MCP
  surfaces, and it de-risks the part of the E2E demo gate most likely to surprise late (scanned and
  hostile PDFs). Discovering PDF problems in the final phase would be the worst possible timing.

- **The guided layer arrives with the shell (Phase 21), before browse and wizards.** It is the
  cheapest item on the list and the one that actually carries the milestone's success criterion, so
  the UX signal must land while there is still milestone left to react to it. Merging SHELL (3
  mechanical requirements) into the same phase avoids a thin move-and-serve phase that delivers no
  user-observable behaviour on its own.

- **GOV-02/GOV-03 precede the review wizards by construction.** The current HITL resume model is
  positional and a missing decision falls back to *applying a write*. Building the review wizards
  against that shape and repairing it afterwards would mean building twice, on the one surface where
  a wrong decision writes canonical truth.

- **Wizards and browse (Phases 22, 23) are siblings, not a sequence.** They share only the shell and
  the API; they can proceed in parallel once Phase 21 lands.

- **The verdict phase (Phase 24) is last by construction.** SEED-001 needs the real HTTP API to
  produce an honest verdict rather than a guess, and the UX verdict needs the rest finished. But the
  *verdict template* is a Phase 21 obligation — a retrofitted template is itself a documented PoC
  failure mode, because fixed questions cannot be reverse-engineered from whatever shipped.

### v0.5 Open Questions Carried into Phase Planning

Recorded in `REQUIREMENTS.md`, assigned here so none is silently defaulted.

| # | Question | Owning phase |
|---|----------|--------------|
| OQ-1 | Where do uploaded bytes live? An upload has no path; none of the three options is clearly right | Phase 20 |
| OQ-2 | Graph data source at scale — views JSON projection or live API traversal | Phase 23 |
| OQ-3 | Extraction failure taxonomy and the fixture set that proves each reason | Phase 20 |
| OQ-4 | Checkpoint concurrency contract — WAL / `busy_timeout` / single-flight locking (extends adr-0004) | Phase 19 |
| OQ-5 | Does the PoC demo run on a fresh workspace or a fixture? `test-ws/` carries pre-`4e2b909` damage | Phase 24 |

Two further decisions surfaced by research and assigned the same way: `gate_review.py`'s disposition
(fix, fence, or delete) is owned by **Phase 18** alongside GOV-04, and the priority→action mapping's
ownership is already resolved to the backend by GUIDE-01's wording (**Phase 21**).

## Coverage (v0.4.1 — shipped)

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOC-03 | Phase 14 | Complete |
| FIX-02 | Phase 14 | Complete |
| FIX-01 | Phase 15 | Complete |
| FIX-03 | Phase 16 | Complete |
| DEC-01 | Phase 16 | Complete |
| DOC-04 | Phase 16 | Complete |
| DOC-01 | Phase 17 | Complete |
| DOC-02 | Phase 17 | Complete |
| UX-01 | Phase 17 | Complete |

**Coverage:** 9/9 v0.4.1 requirements mapped exactly once and delivered. Unmapped: 0. Duplicated: 0. Full detail archived in [`milestones/v0.4.1-REQUIREMENTS.md`](milestones/v0.4.1-REQUIREMENTS.md).

**Not mapped (by design):** FIX-04 — delivered 2026-07-19 ahead of the milestone (commit `11f20f4`), the pre-milestone guard whose `_KNOWN_BROKEN` allowlist supplied the mechanical completion criteria for Phases 15 and 16.

## Coverage (v0.4 — shipped)

| Requirement group | Requirements | Phase(s) |
|-------------------|--------------|----------|
| Search Provider Spine | SRCH-01, SRCH-02, SRCH-03, SRCH-04 | Phase 8 |
| Research Workflow | RSCH-01, RSCH-02, RSCH-03, RSCH-04, RSCH-05 | Phases 9–10 |
| Curation Workflow | CUR-01, CUR-02, CUR-03, CUR-04, CUR-05 | Phases 11–12 |
| CONSTRUCT API And Runtime Parity | API-01, API-02, API-03, API-04, API-05 | Phases 12–13 |
| Daily-Cycle Composition | DAY-01, DAY-02, DAY-03 | Phase 13 |

**Coverage:** 22/22 v0.4 requirements mapped exactly once and delivered. Full detail archived in [`milestones/v0.4-REQUIREMENTS.md`](milestones/v0.4-REQUIREMENTS.md).

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Contract Canon & Artifact Governance | v0.3 | 4/4 | Complete | 2026-06-08 |
| 2. Governed Knowledge Operations | v0.3 | 3/3 | Complete | 2026-06-10 |
| 3. Capability Registry, CLI & MCP Spine | v0.3 | 3/3 | Complete | 2026-06-12 |
| 4. Guided Workflow Operability | v0.3 | 4/4 | Complete | 2026-06-10 |
| 5. Grounded Synthesis & Graph Reasoning | v0.3 | 4/4 | Complete | 2026-06-11 |
| 6. Derived Data, Ops UI & Governed Spikes | v0.3 | 4/4 | Complete | 2026-06-11 |
| 7. Close v0.3 blockers (RT-03, ING-02, ING-05) | v0.3 | 3/3 | Complete | 2026-06-16 |
| 8. Search Provider Spine + Contract Foundation | v0.4 | 3/3 | Complete | 2026-06-21 |
| 9. LLM Provider Factory + research.score | v0.4 | 4/4 | Complete | 2026-06-28 |
| 10. Durable Human Review + research.run | v0.4 | 5/5 | Complete | 2026-06-28 |
| 11. Curation PIPE Steps | v0.4 | 3/3 | Complete | 2026-06-29 |
| 12. Curation L3 Gates + Review Application | v0.4 | 6/6 | Complete | 2026-07-05 |
| 13. Daily-Cycle Composition | v0.4 | 3/3 | Complete | 2026-07-07 |
| 14. Durable-State & Config Truth | v0.4.1 | 4/4 | Complete | 2026-07-19 |
| 15. views.generate_data Resolution | v0.4.1 | 5/5 | Complete | 2026-07-20 |
| 16. Invocation & User-Doc Truth | v0.4.1 | 7/7 | Complete | 2026-07-25 |
| 17. Architecture Doc Set & daily.run Discoverability | v0.4.1 | 4/4 | Complete | 2026-07-25 |
| 18. Contract & Governance Foundations | v0.5 | 8/8 | In Progress|  |
| 19. HTTP API over the Capability Registry | v0.5 | 3/10 | In Progress|  |
| 20. Real Document Extraction | v0.5 | 0/? | Not started | - |
| 21. Served App Shell & Guided Action Layer | v0.5 | 0/? | Not started | - |
| 22. Wizard Flows | v0.5 | 0/? | Not started | - |
| 23. Live-Data Browse — Workspaces, Wiki, Graph | v0.5 | 0/? | Not started | - |
| 24. Evaluation Spikes, E2E Demo Gate & UX Verdict | v0.5 | 0/? | Not started | - |
