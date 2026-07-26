# Phase 18: Contract & Governance Foundations - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Make three contracts honest **before** a browser depends on them. Every item is a repair to code that
exists in the repository today, not new capability:

1. **The views byte contract (VFIX-01)** — `views validate` accepts every file `views generate` writes.
2. **One validating invocation seam (GOV-01)** — CLI and MCP dispatch through a single seam that
   validates payloads against each capability's declared `input_model`. HTTP joins the same seam in
   Phase 19; it is not built here.
3. **The human-review decision model and honest reporting (GOV-02..05)** — decisions name the proposal
   they apply to, a stale queue is rejected with zero writes, no surface writes canonical truth outside
   the resume path, and degraded/escalated outcomes never read as clean success.

**Not in this phase:** the HTTP adapter itself (Phase 19), the review wizards (Phase 22), the ETag's
browser-side use (Phase 22), extraction (Phase 20), any UI build.

</domain>

<decisions>
## Implementation Decisions

### Views byte contract (VFIX-01)

- **D-01:** Reconcile the contract by **conforming `views/models.py` to the raw bytes the generator
  writes** (research option (i)), and drop the `_FILE_MODEL_MAP` / `_PER_WS_FILES` adapter tables in
  `generate.py:92-163` that currently make the writer validate an adapted projection and then write a
  different dict. The SPA already reads these bytes and existing `views/build/` copies become valid, so
  neither breaks. **This must be recorded as an explicit named decision**, because on its face it looks
  like a reversal of PROJECT.md's standing ING-02 decision ("conform the data to the gate, not weaken
  the gate"). It is not: ING-02 governs **canonical truth** (cards/refs), where strictness protects the
  knowledge model. Views is a **derived projection** whose author is the generator and whose consumer is
  the SPA — there the written bytes *are* the de-facto contract and the models were simply transcribed
  wrongly. — **Reversibility:** costly — undoing means re-introducing the adapter tables and re-breaking
  every existing `views/build/` copy plus the SPA components already coded against these field names.

- **D-02:** **`views validate` is promoted to a registry capability in this phase**, alongside the
  existing `views.generate_data` record (`catalog.py:337`). The byte fix already opens `cli.py:929` and
  `views/models.py`, so registration is nearly free; it closes half of RT-01/RT-02 with the smallest
  blast radius, retires adr-0005's explicit "registry holdout" note, and Phase 19's generated HTTP
  adapter then gets it for nothing. The `spike` and `tag` groups stay excluded (`spike run --tool-path`
  is an RCE primitive over HTTP; `tag` is unused by any v0.5 flow).

- **D-03:** The conformed models **relax from `extra="forbid"` to `extra="ignore"`**. All 13 models in
  `views/models.py` are `extra="forbid"` today; after conforming, they describe a floor rather than an
  exact byte-for-byte shape, so a parser field addition does not break `views validate` or existing
  builds. — **Reversibility:** reversible.

- **D-04:** Because D-03 gives up the model-level drift detector, the replacement round-trip guard is
  the **only** thing that can catch the next writer/reader fork, and therefore takes the strict form:
  **enumerate all 8 expected files by name, assert each exists, is non-empty, and validates, and assert
  the written-file count equals 8.** Cardinality, not set-membership — this is the WR-01 lesson from
  `tests/contract/test_artifact_catalog.py`, whose set-membership guard is exactly why its hand-typed
  prose counts can rot. The guard **replaces** `test_views_validate_does_not_yet_accept_generated_bytes`
  (`tests/integration/test_views_generate.py:285`); it is never deleted bare.

### Invocation seam (GOV-01)

- **D-05:** The seam is **strict from day one** — no `_KNOWN_BROKEN`-style allowlist, no leniency mode,
  no per-surface exception. Every capability validates through its `input_model` on both CLI and MCP
  immediately. Anything the 515-test suite surfaces as non-conforming was already calling a capability
  wrongly and is fixed inside this phase rather than recorded as an exception. — **Reversibility:**
  costly — a later relaxation would have to be applied per capability across both surfaces, and the
  differential test would have to encode the relaxation as expected behaviour, which is the parity fork
  GOV-01 exists to close.

- **D-06:** `extra="forbid"` is applied **by default across all 28 capability input models** (today only
  `CardListInput` carries it, `catalog.py:145-147`, added as an ASVS boundary control and currently
  inert over MCP — code-review item WR-02). Any capability that genuinely needs an open payload expresses
  it as a **typed dict field**, never by relaxing the whole model. Research sizes the 28-model audit
  before planning commits.

- **D-07:** The seam calls the handler as **`handler(**model.model_dump())`** — identical to what
  `mcp/server.py:33` already does, so MCP handlers need no signature change and the seam is a pure
  insertion there. The work is normalizing `cli.py`'s three positional call sites (`:89`, `:107`, `:143`)
  and retiring the RT-03 dual-mode shims. Research confirms how many of the 28 handlers fit this shape
  before planning locks it; `ui/capability_runner.py:292-297` already admits some do not accept `**kwargs`.

- **D-08:** The differential parity test drives the **real CLI process and the real MCP dispatch path**
  over a fixture workspace, for a fixed table of `(capability, payload)` cases, asserting identical
  `success` / `message` / error-reason fields — including that an unknown field is rejected on both.
  In-process calls would skip the Typer argument-parsing layer where the positional-call debt actually
  lives. Planner may trade fixture cost against coverage breadth, but must not fall back to
  inventory/set-membership assertions, which prove a capability is *listed*, never that two surfaces
  *behave* the same.

### Review-decision model (GOV-02 / GOV-03)

- **D-09:** Every proposal gets a **stable `proposal_id` assigned at enqueue time**, stored in the
  checkpoint with the proposal, and the resume payload becomes a **map keyed by that id**, replacing the
  positional `zip` in `_resolve_decisions` (`llm/curation_run.py:777-796`). `CurationProposal`
  (`:164-179`) gains the field. Ids are **opaque** (sequence or uuid), not content-derived — guaranteed
  unique, no collision reasoning, and "this id is not in this queue" becomes a clean rejection.
  — **Reversibility:** one-way — the id is persisted into `.construct/workflow/*.sqlite` checkpoints and
  becomes the contract the Phase 19 API and the Phase 22 review wizards are built against; reverting
  would require migrating live checkpoint state back to a positional shape.

- **D-10:** A resume whose decision map **does not cover every queued proposal is rejected in full** —
  zero canonical writes, the run stays paused exactly where it was, and the response names the uncovered
  proposal ids. This replaces the current `_normalize_decision(None, default)` fallback, which silently
  applies the gate's own recommendation — i.e. a short or misaligned payload performs a write.

- **D-11:** Stale-queue detection uses the **LangGraph checkpoint id as an ETag** — returned alongside
  the queue from `graph.get_state(cfg).config["configurable"]["checkpoint_id"]`, required on resume,
  mismatch rejects with zero writes. Free, since LangGraph already maintains it, and it catches any state
  advance rather than only queue changes. Research should confirm the id is stable across a pause in the
  pinned LangGraph version before planning commits.

- **D-12:** Runs already paused in `.construct/workflow/*.sqlite` whose proposals carry no ids are
  **migrated on read** — opaque ids are assigned at checkpoint-load time so pending human-review work is
  not abandoned. This is safe rather than a reintroduction of the positional assumption **because D-10
  still applies**: a resume must carry a complete id-keyed map, so no legacy positional payload can ever
  be applied to a migrated queue. The user re-decides in the new shape; migration preserves only the
  *queue*, never a decision.

### Surface honesty (GOV-04 / GOV-05)

- **D-13:** **`src/construct/ui/gate_review.py` is deleted**, together with its `st.Page` entry in
  `streamlit_app.py:47`. Rationale from live code: its "Pending Q&A Reviews" section is built entirely
  from `st.session_state.gate_queue` (`:56-57`) with no run behind it, and flips `review_status` while
  calling `_log_gate_event(... "gate_review_approved" ...)` (`:151-169`) into the same append-only audit
  trail `curation_run._emit` writes to — approvals recorded for things nothing applied. Its "Bridge
  Candidates" section calls `registry.get("knowledge.connection.add").handler(...)` directly (`:258`)
  with a hard-coded `ConnectionType.parallels`, ignoring whatever the L3 connection-typing gate decided —
  a second canonical writer with different semantics from `apply_connections` (`:912-923`). Neither
  section reviews a `curation.run` / `research.run` queue, so there is no paused checkpoint for them to
  resume into. Dashboard and Capability Runner stay. — **Reversibility:** reversible — the file is
  recoverable from git history, but nothing in v0.5 depends on it.

- **D-14 (planner action):** ROADMAP success criterion 4 for this phase is written as *"Approving a
  proposal in the Streamlit gate-review screen produces exactly the same canonical writes and event
  records as approving it through the reviewed workflow's own resume path"*. After D-13 that screen does
  not exist, so the criterion loses its subject. **Restate it** as: no surface writes canonical truth
  outside the reviewed-workflow resume path (satisfied by removal, guarded by a test), **and** no
  approval event exists for a decision that was never applied. The second half stands independently and
  is enforced by D-16.

- **D-15:** The Phase 11 curation exit-code contract **holds** — a degraded `curation.run` still exits 0
  on purpose. GOV-05 governs what a surface *reports* (status fields, `--json` payloads, MCP results,
  human-readable output), not process exit semantics, which the CLI uses to mean "the command ran".
  Re-opening WR-04 sideways inside a repair phase is precisely what that decision was recorded to
  prevent. Do not change exit codes in this phase.

- **D-16:** `escalate` is **relabelled, counted separately, and given its own event type**. It writes
  nothing (`curation_run.py:849-852`), so: name it for its actual effect on every surface (e.g. "flagged
  — no action taken"); count escalated items in their own bucket so they never fold into an applied or
  success count; and stop emitting `gate_review_rejected` for them — logging a rejection for something
  that was escalated is itself an audit trail that lies, the T-15-14 class this codebase already names.
  The new event type must be threaded through the event-log readers and the views `events.json`
  projection. Additionally, the **event-count invariant lands in this phase** (it is criterion 4): a
  `gate_review_approved` must not be emitted for a write that did not happen — `gate_review_approved`
  currently double-fires per item regardless of no-op writes at `curation_run.py:872`, `:923`, `:968`.

### Post-research corrections (VFIX-01 scope)

Added 2026-07-26 after `18-RESEARCH.md` measured the live repo and invalidated two premises D-01/D-04
rested on. These are **user decisions**, not planner discretion — both enlarge VFIX-01 deliberately.

- **D-17:** **The Python emitter shape (`ts` / `agent` / `action` / …) is canonical for `events.json`,
  chosen and conformed in this phase.** Research found D-01's premise ("the SPA already reads these
  bytes") is true for cards and digests but **false for events**: four mutually incompatible shapes exist
  — the Python emitter, legacy fixture logs (`event` / `timestamp` / `details`), the views model
  (`timestamp` / `type` / `actor` / …), and the SPA reader (`e.actor` / `e.type` / `e.subject.card_id`) —
  and `parse_events` passes lines through verbatim, so "conform to the bytes" had no single referent.
  Rather than paper over it with tolerant aliases, this phase **picks the emitter shape as the contract**
  and conforms **both** the views model **and** the SPA reader to it; legacy fixture-log lines are
  migrated or ignored, not silently accepted. This is the larger option and was chosen knowingly: it
  leaves `events.json` with a real contract instead of a permissive model that only looks like one, and
  it removes the Phase 23 convergence debt the alternative would have created. The new `escalate` event
  type from D-16 threads into this same canonical shape. — **Reversibility:** costly — the SPA reader and
  any existing `views/build/` event copies are conformed together; reverting means re-forking them.

- **D-18:** **`<ws>/stats.json` and `<ws>/curation-history.json` get contract models in this phase.**
  Research found these are the only files `views generate` writes with **no gate at all**. Modelling
  them closes the last silent hole, so the D-04 round-trip guard's coverage claim is 100% of written
  files rather than "most of them". — **Reversibility:** reversible.

- **D-19:** **D-04's cardinality clause is restated as `4 + 6·N_workspaces + 1`.** The literal
  "count equals 8" is arithmetically wrong — the generator writes 10 data files plus `version.json` for a
  single workspace, so the original clause would have failed on its first run. Cardinality-not-set-
  membership (the WR-01 lesson) is **unchanged**; only the arithmetic is corrected. With D-18 landing,
  no file is excluded from the count. The guard still **replaces** rather than deletes
  `test_views_validate_does_not_yet_accept_generated_bytes`.

- **D-20:** **Field renames are fixed as renames, not absorbed by `extra="ignore"`.** Research measured
  `views validate` failing **5 of 8** files on a *populated* install root (not 3), and **4 of those 5**
  fail with `Field required` from field renames — which D-03's `extra="ignore"` does not fix.
  `extra="ignore"` (D-03) still stands for *additive* parser drift; it is not a substitute for
  conforming renamed fields. Note also that `DigestRecord` is a **writer** model
  (`research_run.py:644` writes `digests/digests.json` with it), so renaming its fields changes a
  workspace file, not only a projection — that write path must be conformed in the same task.

### Claude's Discretion

The user delegated these; planner and researcher have latitude within the stated preference:

- **Byte-contract fix shape** (D-01) — user said "you decide"; research option (i) taken, with the ING-02
  tension recorded as a named decision as the ROADMAP requires.
- **Round-trip guard shape** (D-04) — user said "you decide"; strict named-8 + cardinality taken,
  *because* the user's `extra="ignore"` choice (D-03) makes the guard the sole drift detector.
- **`extra="forbid"` coverage** (D-06) — user said "you decide"; forbid-by-default across all 28 taken,
  with the audit sized during research.
- **Differential test target** (D-08) — user said "you decide"; real CLI subprocess + real MCP dispatch
  preferred, planner may trade fixture cost against breadth but not fall back to set-membership.
- **Handler calling convention** (D-07) — user said "you decide"; `handler(**model.model_dump())`
  preferred for smallest blast radius, contingent on research confirming handler fit.
- **Exit-code contract** (D-15) — user said "you decide"; Phase 11 contract held.
- **GOV-05 enforcement shape** (D-16) — user said "you decide"; prefer a **table-driven cross-surface
  test** (CLI human output, CLI `--json`, MCP result) driven against a fixture run forced degraded and a
  fixture run with an escalated item, so Phase 19's HTTP surface joins by adding a row. Result-model-only
  assertions are insufficient: rendering is precisely where the lie has historically happened.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 18: Contract & Governance Foundations" — goal, the 5 success criteria,
  the named decision to record, and the open decision carried in. Note D-14: criterion 4 needs restating.
- `.planning/REQUIREMENTS.md` §§ "Data Contract (VFIX)", "Governance & Contract Integrity (GOV)" —
  VFIX-01 and GOV-01..05 wording; § "Open Questions for Phase Planning" item 6 (`gate_review.py`
  disposition, owned by this phase — resolved as D-13).
- `.planning/PROJECT.md` § "Key Decisions" — the ING-02 row that D-01 must be reconciled against, and the
  adr-0004 / adr-0005 rows.

### Research basis (2026-07-26)
- `.planning/research/PITFALLS.md` — § "The recurring class: writer/reader contract forks" (the root
  cause D-01/D-04 address, and the "no backfill" consequence); Pitfall 1 (second write path — D-13);
  Pitfall 2 (gate queue in session state, audit log lying — D-13); Pitfall 3 (`input_model` is
  documentation not enforcement — D-05..D-08); Pitfall 5 (stale gate state + positional decisions —
  D-09..D-12); Pitfall 11 / line ~304 (views byte contract — D-01); the "escalate dead-end" (~line 402)
  and the escalate-button row (~line 500) behind D-16.
- `.planning/research/ARCHITECTURE.md` § "The `views generate` ↔ `views validate` byte contract —
  recommendation" (the three-option table behind D-01) and § "The 7 non-registry (RT-01/RT-02) leaves"
  (the views/spike/tag disposition behind D-02).
- `.planning/research/SUMMARY.md` — synthesis across the four researchers.

### Architecture decision records
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` — views refresh ownership; carries the
  explicit "registry holdout" note that D-02 retires.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md` — sanctions
  `.construct/workflow/*.sqlite` as durable state holding pending human-review decisions. D-09 and D-12
  write into exactly this state. The concurrency contract extending this ADR is **Phase 19's** (OQ-4),
  not this phase's.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — the permanent L0–L4 runtime model that
  `architecture-overview.md` was rewritten onto in Phase 17.

### Live code the phase repairs
- `src/construct/views/models.py` (13 models, all `extra="forbid"`) and
  `src/construct/views/generate.py:85-163` (`_FILE_MODEL_MAP` / `_PER_WS_FILES`) + `:373-384` (writes the
  raw parser dict) — D-01, D-03.
- `src/construct/cli.py:869` (`views generate`), `:929` (`views validate`) — D-02.
- `tests/integration/test_views_generate.py:285`
  (`test_views_validate_does_not_yet_accept_generated_bytes`) — replaced per D-04.
- `src/construct/capabilities/registry.py` — has `get` / `list` / `list_mcp_tools`; **no `invoke`**.
  `input_model` is used only for `model_json_schema()`. The GOV-01 seam does not exist yet.
- `src/construct/capabilities/catalog.py:145-147` (`CardListInput` `extra="forbid"`, currently inert over
  MCP — WR-02), `:337` (`views.generate_data` record) — D-02, D-06.
- `src/construct/mcp/server.py` (52 lines, `capability.handler(**kwargs)` at `:33`) — the seam is a pure
  insertion here; parity stays free. Research says **do not restructure this file**.
- `src/construct/llm/curation_run.py` — `CurationProposal` `:164-179`; `_resolve_decisions` `:777-796`;
  `apply_promotions` escalate handling `:849-852`; `gate_review_approved` emission `:872`, `:923`, `:968`;
  `apply_connections` `:912-923`; `_validate_run_id` `:64-77` (the identifier-guard pattern to reuse).
- `src/construct/llm/research_run.py` — `review_research_run:1056` (WR-05); the research review gate takes
  the same GOV-02/GOV-03 treatment as curation.
- `src/construct/ui/gate_review.py` (293 lines: `:56-57`, `:151-169`, `:252-281`) and
  `src/construct/ui/streamlit_app.py:47` — deleted per D-13.
- `src/construct/ui/capability_runner.py:197`, `:292-297` — the "cannot accept `**kwargs` from the form
  yet" admission constraining D-07.
- `tests/contract/test_artifact_catalog.py` — the set-membership-not-cardinality guard whose weakness
  (WR-01) motivates D-04's and D-08's shapes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_validate_run_id` (`llm/curation_run.py:64-77`)** — an existing kebab-case identifier guard written
  precisely because "the MCP/CLI shims pass caller-supplied `**kwargs` straight into the input models".
  The same pattern is the model for `proposal_id` validation (D-09) and, in Phase 19, for `workspace_id`.
- **`mcp/server.py`'s registry-driven tool generation (52 lines)** — the structural proof that a surface
  can be generated rather than hand-written. The GOV-01 seam slots under its existing
  `handler(**kwargs)` call with no restructuring.
- **`tests/integration/test_views_generate.py`** — already the round-trip test file; D-04's guard extends
  an existing harness rather than building one.
- **`_KNOWN_BROKEN` / `_DOC_GLOBS` discipline (`tests/contract/test_doc_command_references.py`)** — the
  project's proven "widen the guard, never narrow it" pattern. D-05 deliberately declines the allowlist
  half of it, but the widening discipline governs D-04 and D-08.

### Established Patterns
- **Registry is the single contract behind CLI + MCP** — parity is free via auto-discovery; adding a
  capability must never require editing `mcp/server.py`. D-02 and D-07 must preserve this.
- **Pydantic v2 with `extra="forbid"` at boundaries** — `CurationProposal` and `CardListInput` already
  use it as a security control. D-06 generalizes it; D-03 deliberately exempts the derived views
  projection, and the difference between canonical truth and derived projection is the reason both are
  correct.
- **Propose-then-approve with apply nodes strictly downstream of `interrupt()`** — the invariant D-13
  protects by removing the one surface that violates it.
- **Silent success is this codebase's default failure mode** — named in-repo as T-15-14
  "audit-trail-that-lies". Every decision in this phase is a countermeasure to some instance of it.

### Integration Points
- `registry.invoke()` is new surface area that **Phase 19's generated HTTP adapter routes through**.
  Its signature is a cross-phase contract — Phase 19 can start in parallel but must not fork it.
- `proposal_id` + the checkpoint-id ETag (D-09, D-11) are the contract **Phase 22's review wizards** are
  built against. They land here specifically so the API is never built on the positional shape.
- The conformed views models (D-01) are the data contract **Phase 23's browse/wiki/graph** reads. Getting
  this wrong means building those pages twice.
- `views validate` as a registry capability (D-02) is picked up free by Phase 19's adapter.

</code_context>

<specifics>
## Specific Ideas

- The user explicitly declined an allowlist for the seam (D-05) despite the project's own successful
  `_KNOWN_BROKEN` precedent — the preference is to absorb the fix list inside this phase rather than
  carry a visible exception set forward into the milestone.
- The user chose `extra="ignore"` for the views models (D-03) while simultaneously accepting
  `extra="forbid"` across all 28 capability models (D-06). This is coherent, not contradictory: views is
  a derived projection, capabilities are a trust boundary. Planner should not "harmonize" the two.
- The user chose to preserve pending human-review work (D-12, migrate on read) over the cleaner
  refuse-and-restart. The safety of that choice rests entirely on D-10 — if D-10 is ever weakened, D-12
  becomes unsafe. Treat them as a pair.

</specifics>

<deferred>
## Deferred Ideas

- **Checkpoint concurrency contract (WAL / `busy_timeout` / single-flight locking)** — OQ-4, owned by
  **Phase 19**. D-11's ETag stops cross-process misapplication; it does not stop `database is locked`.
- **The ETag's browser-side use** (`If-Match` / `409 Conflict` semantics, refreshed queue in the body) —
  **Phase 22**. Phase 18 lands the mechanism, not the HTTP behaviour.
- **Giving `escalate` a real write path** — D-16 makes escalate honest about writing nothing; making it
  actually route something for follow-up is new capability, not a Phase 18 repair.
- **A run-list capability** (Pitfall 7 — a run whose id is lost is unreachable) — HTTP-07, **Phase 19**.
- **`card list` MCP-boundary hardening (WR-01/WR-02)** — partially subsumed by D-05/D-06 if the seam
  covers the failure path; whatever the seam does not cover stays carried-forward debt.
- **RT-01/RT-02 registry unification for `spike` and `tag`** — D-02 closes only the `views` half. `spike
  run --tool-path` is deliberately excluded from HTTP as an RCE primitive; `tag` waits for v0.6.
- **`artifact-catalog.md` prose counts** — D-04/D-08 apply the cardinality lesson to *new* guards; fixing
  the catalog guard itself is not in scope here.

</deferred>

---

*Phase: 18-Contract & Governance Foundations*
*Context gathered: 2026-07-26*
