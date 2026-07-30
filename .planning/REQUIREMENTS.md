# Requirements: CONSTRUCT v0.5 — UI-Primary Experience (Proof of Concept)

**Defined:** 2026-07-26
**Core Value:** The system must reliably turn source material into connected, explorable knowledge while making the next sensible action clear to the user.
**Milestone Goal:** Prove on an isolated branch that a browser-first shell over the v0.4 runtime can guide a user through CONSTRUCT's core loops without touching the CLI — judged on whether the guided/wizard model actually makes the system usable unaided.

**Branch:** all v0.5 work lands on `dev-v05` (off `main`, pushed to origin). `main` stays releasable at v0.4.1.

**REQ-ID prefixes are new for v0.5** — `VIEW`, `UI`, and `API` were used in v0.3/v0.4 and are deliberately avoided.

## v0.5 Requirements

### Data Contract (VFIX)

The shared prerequisite named by SEED-001 and SEED-003, and independently by the architecture and pitfalls research. Building browse/wiki/graph on a projection that diverges from its own validator means building twice.

- [x] **VFIX-01**: `views validate` accepts every file `views generate` writes — the byte contract round-trips, and `test_views_validate_does_not_yet_accept_generated_bytes` is replaced by a non-vacuous round-trip guard rather than deleted.

### HTTP API Layer (HTTP)

The universal hard gate — no browser feature of any kind can exist before this. CONSTRUCT has no HTTP surface today.

- [ ] **HTTP-01**: A user can start a local API server with one command, and it binds loopback only.
- [ ] **HTTP-02**: Every registry capability is reachable over HTTP without hand-written per-capability routes — routes are generated from the registry the way `mcp/server.py` already generates MCP tools, guarded by a test so the server file cannot be hand-edited into drift.
- [ ] **HTTP-03**: HTTP callers address workspaces by id, never by filesystem path; ids resolve server-side against an install-root allowlist.
- [ ] **HTTP-04**: HTTP errors return the same structured result shape as CLI and MCP — no third error-shape fork.
- [ ] **HTTP-05**: The API rejects drive-by and DNS-rebinding requests via `Origin`/`Host` validation and a per-launch token.
- [ ] **HTTP-06**: Workflow runs are addressable resources — starting one returns an id, status is pollable, and a run started in the browser is resumable from the CLI and vice versa.
- [ ] **HTTP-07**: A user can list runs, including paused ones, so no run becomes unreachable after its id is lost.

### Governance & Contract Integrity (GOV)

Repairs to defects the research found in **live code**, which a browser turns from latent debt into user-visible failure. These are not new-build concerns.

- [ ] **GOV-01**: CLI, MCP, and HTTP all dispatch through one seam that validates payloads against each capability's declared `input_model`, proven by a differential test (same capability + payload → identical result across all three surfaces).
- [ ] **GOV-02**: Human-review decisions are keyed by proposal id rather than list position, and a missing decision never defaults to applying a write.
- [ ] **GOV-03**: A review queue that went stale between render and submit is detected and rejected rather than silently misapplied.
- [x] **GOV-04**: The Streamlit gate-review screen routes approvals through the reviewed workflow's resume path instead of writing directly, so no surface writes canonical truth outside that path and no approval event is logged for a decision that was never applied.
- [x] **GOV-05**: No surface reports success for a degraded or partially-applied outcome — degraded runs and escalated items render honestly rather than as clean completion.

### Document Extraction (EXTR)

Scoped to **pdf, txt, and md only**. Word formats are excluded by decision (see Out of Scope).

- [ ] **EXTR-01**: Ingesting a pdf, txt, or md file extracts its actual text content, and that content seeds the resulting card — not a ref pointing at an unread file.
- [ ] **EXTR-02**: Extraction status reflects measured extractor yield, never caller-supplied title or metadata, so a scanned or empty PDF is never marked complete.
- [ ] **EXTR-03**: "No extractable text" is a first-class user-visible outcome with a named reason, not a silent success.
- [ ] **EXTR-04**: `.doc` and `.docx` files are detected and rejected with a clear "convert to pdf, txt, or md first" message rather than failing obscurely.
- [ ] **EXTR-05**: Malformed and hostile file input is handled safely — size caps, type detection from file contents rather than client-supplied type, and XXE-safe parsing.
- [ ] **EXTR-06**: Extraction is a registry capability, so CLI and MCP reach it too — it does not become browser-only.

### Served App Shell (SHELL)

- [ ] **SHELL-01**: The views SPA lives in the repo as a first-class app, served by the API at the paths its existing pages already fetch.
- [ ] **SHELL-02**: A user can run the PoC from an install without Node present — the built frontend ships prebuilt, and frontend dependencies are pinned by a committed lockfile.
- [ ] **SHELL-03**: Existing per-workspace views scaffolds keep working — promotion does not break already-scaffolded workspaces.

### Guided Action Layer (GUIDE)

The milestone's hidden dependency. `help.suggest` is a diagnosis engine today — it emits priorities and reasons but no verb, capability, or destination; an LLM improvises that mapping in chat. With chat demoted, something must own it.

- [ ] **GUIDE-01**: `help.suggest` emits an actionable next step (verb, capability, destination) for every priority state it can report, available identically to CLI, MCP, and HTTP callers.
- [ ] **GUIDE-02**: A user sees prioritized next actions in the browser and can launch each one directly from its suggestion.
- [ ] **GUIDE-03**: Guidance re-evaluates after every mutating action, so it reflects current workspace state rather than the state at page load.
- [ ] **GUIDE-04**: A user can see the evidence behind a suggestion, healthy states render as informational rather than as a call to action, and a suggestion never executes without explicit confirmation.

### Wizard Flows (WIZ)

Four flows; the two review gates share one queue-of-proposals surface.

- [ ] **WIZ-01**: A user can create a workspace and set up its first domain through a guided multi-step flow, without the CLI.
- [ ] **WIZ-02**: A user can upload a document and see the extracted content previewed before anything is written to disk.
- [ ] **WIZ-03**: A user can review and override where an ingested document is routed before confirming it.
- [ ] **WIZ-04**: Cancelling any wizard leaves the filesystem exactly as it was — nothing is written before the confirm step.
- [ ] **WIZ-05**: A user can review a queue of machine proposals — research findings, and curation promotions/connections/archives — with the supporting evidence visible without a click, accepting or rejecting per item.
- [ ] **WIZ-06**: A user can accept all recommended proposals in one action, with escalate-flagged items excluded, reusing the rule already shipped for the daily cycle.
- [ ] **WIZ-07**: A review in progress survives navigation, refresh, and process restart, resuming from the durable checkpoint.
- [ ] **WIZ-08**: After applying, a user sees a summary of what was written and what was skipped, including partial success.
- [ ] **WIZ-09**: Every wizard shows step progress and allows non-destructive back navigation, and queue decisions can be undone before they are applied.

### Browse: Workspaces, Wiki, Graph (BRWS)

- [ ] **BRWS-01**: A user can see all workspaces and open any one of them.
- [ ] **BRWS-02**: A user can browse knowledge cards in a wiki reading view where links resolve and provenance is visible.
- [ ] **BRWS-03**: The wiki stays a sibling reading view — the workspace landing is the dashboard, pinned by a guard so the existing `workspace_landing === 'wiki'` redirect cannot re-enable it.
- [ ] **BRWS-04**: A user can explore the knowledge graph from a focused local view by default, with the global view opt-in.
- [ ] **BRWS-05**: A user can search and filter the graph and tell what they are currently looking at.
- [ ] **BRWS-06**: Cards, wiki pages, and graph nodes have deep-linkable URLs.
- [ ] **BRWS-07**: A user can move between the wiki and the graph for the same card in both directions.
- [ ] **BRWS-08**: Empty and small-graph states render meaningfully, and a user can tell when displayed data is stale relative to the workspace.

### Evaluation Spikes & Verdict (EVAL)

Verdict documents, not shipped features. The UX verdict is the milestone's success criterion.

- [ ] **EVAL-01**: A CoPilotKit verdict (SEED-001) states whether it should be adopted for the Layer 4 shell, evaluated against the real HTTP API rather than from documentation — with a recommendation recorded either way.
- [ ] **EVAL-02**: A graphify.net verdict (SEED-002) states whether it belongs in the ingestion path, evaluated in the existing spike sandbox, answering the governance and egress questions.
- [ ] **EVAL-03**: An open-wiki-format verdict (SEED-003) answers whether CONSTRUCT can emit an open format as a read-only projection without changing the canonical workspace format.
- [ ] **EVAL-04**: The end-to-end demo path completes without CLI intervention on a fresh, offline workspace — upload a PDF, see cards created, browse them in the wiki and the graph.
- [ ] **EVAL-05**: A written UX verdict answers whether a person can navigate CONSTRUCT unaided, produced from someone actually attempting it on a fresh workspace, against a template written before the UI was polished.

## Future Requirements

Acknowledged but deferred. Not in the v0.5 roadmap.

### Guided Layer

- **Health-trend snapshots** — guidance over time rather than current state.
- **LLM-generated taxonomy suggestions** during workspace setup — propose-only, needs an L3-gate-shaped pattern proven first.

### Browse & Navigation

- **Global search** across workspaces.
- **Command palette** — rewards experts, irrelevant to an unaided-navigation verdict.
- **Event-log deep links** from cards and runs.
- **Diagnostic graph overlay** rendering curation's orphan/connection-health findings onto the graph — the strongest available differentiator and nearly free once the graph exists, but not needed for the verdict.

### Carried Forward from v0.4.1

- **Per-card views-refresh path** — direct `card-create`/`card-connect` edits have no refresh path after the debounced-hook removal (v0.6, OQ-3).
- **`card list` MCP-boundary hardening** — `OperationError` serialization and input validation on the failure path (WR-01/WR-02). Partially subsumed by GOV-01 if the shared seam covers it.
- **`artifact-catalog.md` prose counts** — guarded by set-membership, not cardinality, so hand-typed counts can rot.
- **RT-01/RT-02 registry unification** for the `spike` and `tag` groups. The `views` group is forced through the registry by VFIX-01/HTTP-02; the rest stays deferred.
- **Thin-wrapper migration** for `construct-bridge-detect` / `construct-domain-init` / `construct-search-adjust`.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Word document extraction (`.doc` and `.docx`) | Decided 2026-07-26. Legacy `.doc` needs an external binary (LibreOffice/antiword) that fights local-first; `.docx` was dropped with it to keep the PoC's extraction surface to pdf/txt/md. Narrower than the milestone's original "txt, md, pdf, doc" wording — a deliberate narrowing, not an oversight. Files are detected and rejected with guidance (EXTR-04). |
| `daily.run` / daily-cycle in the UI | Excluded by user decision so the PoC's guidance signal is not diluted by the most complex composed workflow. |
| Adopting CoPilotKit | Evaluated by spike only (EVAL-01). Building on an unvalidated framework would make a negative verdict cost the whole slice. It must not enter the promoted app's dependencies. |
| Changing the canonical workspace format for open-format interop | The answerable v0.5 question is whether an open format can be emitted as a read-only projection (EVAL-03). Format continuity is the project's hardest constraint. |
| Wiki as workspace landing; auto-generated topic/hub pages in the wiki | Violates locked decisions D5/D8. The D5 violation already exists in code as a config-driven redirect and is pinned off by BRWS-03 rather than merely avoided. |
| In-place wiki editing | The views layer is a read-only derived projection; editing it would be a second, ungoverned write path. |
| A global, always-present chat dock | Not a taste judgment — it makes the UX verdict unmeasurable, because users route around every UI gap and the PoC learns nothing. Chat stays scoped to LLM-gated modals. |
| Auto-executing guided suggestions; "accept all" as a review-queue default | Defeats the propose-then-approve invariant that makes the graph trustworthy. |
| Auth, multi-user, sync, remote hosting, containerization | Local-first proof of concept on an isolated branch, not a deployable service. Minimal localhost hardening (HTTP-05) is in scope and is a trust boundary, not production hardening. |
| Upgrading the frontend major versions (Vite 8, recharts 3, react-markdown 10, lucide-react 1.x) | The SPA is promoted, not upgraded. A bundler swap mid-milestone risks the slice for no verdict value. |
| OCR for scanned PDFs | "No extractable text" is surfaced as a named outcome (EXTR-03) instead. OCR is a separate capability decision. |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VFIX-01 | Phase 18 | Complete |
| GOV-01 | Phase 18 | Pending |
| GOV-02 | Phase 18 | Pending |
| GOV-03 | Phase 18 | Pending |
| GOV-04 | Phase 18 | Complete |
| GOV-05 | Phase 18 | Complete |
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

**Coverage:**

- v0.5 requirements: 48 total (VFIX 1 · HTTP 7 · GOV 5 · EXTR 6 · SHELL 3 · GUIDE 4 · WIZ 9 · BRWS 8 · EVAL 5)
- Mapped to phases: 48 ✓ (roadmap created 2026-07-26, Phases 18–24)
- Unmapped: 0 · Duplicated: 0

> **Count correction (2026-07-26, roadmap creation):** this section previously read "47 total".
> The requirement list and the traceability table both contain 48 entries — the prose count was
> off by one, not a missing requirement. Corrected above.

## Open Questions for Phase Planning

Recorded rather than silently defaulted. Each needs a decision during the owning phase's planning.

1. **Where do uploaded bytes live?** CONSTRUCT's file ingestion routes an *existing* path; an upload has no path. None of the three options (a new workspace artifact class, temp with dangling provenance, keep nothing and forgo re-extraction) is clearly right. Owned by **Phase 20** (Real Document Extraction).
2. **Graph data source at scale** — the views JSON projection or live API traversal. Materially changes the cost of BRWS-04/05. Owned by **Phase 23** (Live-Data Browse).
3. **Extraction failure taxonomy** — the enumerated list behind EXTR-03's named reasons (scanned PDF, encrypted PDF, empty file, mislabeled type, CJK/UTF-16, very large document), and the fixture set that proves each. Owned by **Phase 20** (Real Document Extraction).
4. **Checkpoint concurrency contract** — WAL/busy_timeout and single-flight locking for the sqlite checkpointer once a browser and a CLI can both resume the same run. Extends adr-0004. Owned by **Phase 19** (HTTP API — run resources).
5. **Does the PoC demo run on a fresh workspace or a fixture?** Existing `test-ws/` fixtures carry pre-`4e2b909` damage (destroyed card bodies, newline accretion). This affects what the UX verdict actually measures. EVAL-04/05 currently specify fresh — confirm at planning. Owned by **Phase 24** (Evaluation Spikes & UX Verdict).

Two further decisions surfaced by research and assigned during roadmap creation:

6. **`gate_review.py`'s disposition** — fix, fence, or delete. Research states that leaving a second UI that forges gates is worse than either keeping or deleting it. Owned by **Phase 18** alongside GOV-04.
7. **Who owns the priority→action mapping?** Resolved by requirement wording, not left open: GUIDE-01 places it in the backend ("available identically to CLI, MCP, and HTTP callers"), rejecting a frontend-only lookup table. Owned by **Phase 21**.

---
*Requirements defined: 2026-07-26*
*Basis: `.planning/research/SUMMARY.md` (4 parallel researchers + synthesis, 2026-07-26)*
