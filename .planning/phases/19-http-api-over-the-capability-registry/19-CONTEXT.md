# Phase 19: HTTP API over the Capability Registry - Context

**Gathered:** 2026-08-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a **third adapter** — loopback HTTP — over the same 29-capability registry that CLI and MCP
already route through via `registry.invoke()` (Phase 18, GOV-01). This phase adds **no knowledge
capability**. It adds a surface, plus one genuinely new concept: **a workflow run as an addressable,
pollable, listable resource**.

Delivers HTTP-01..HTTP-07:

1. `construct serve` — one command, loopback-bound (HTTP-01).
2. Routes generated from the registry, with a zero-edit guard (HTTP-02).
3. Workspaces addressed **by id**; paths and traversals rejected (HTTP-03).
4. One error shape across three surfaces — no third fork, no leaked paths or raw exception text
   (HTTP-04, and the carried-in T-18-10/T-18-32 pair).
5. `Origin`/`Host` validation + a per-launch token (HTTP-05).
6. Runs are addressable: start returns an id, status is pollable, and a run started in one surface
   is resumable from the other (HTTP-06).
7. Runs are listable, including paused ones (HTTP-07).

**Not in this phase:** the SPA itself and the guided layer (Phase 21), the wizard flows and the
browser-side `If-Match`/409 behaviour built on D-11's ETag (Phase 22), browse/wiki/graph on live
data (Phase 23), document extraction (Phase 20). Auth, multi-user, and remote hosting are out of
scope for the whole milestone; HTTP-05 is minimal localhost hardening and **is** a trust boundary,
not production hardening.

</domain>

<decisions>
## Implementation Decisions

### Workspace addressing (HTTP-03)

- **D-01: Workspace-id → path resolution lives in the seam (`registry.invoke`), not in the HTTP
  adapter and not by rewriting all 29 input models.** The seam resolves a `workspace_id` key into
  whatever path field the target capability declares, before validation. All three surfaces gain
  id-addressing from one implementation, and traversal rejection is one code path rather than a
  per-surface rule. The rejected alternative — resolving in the adapter — is exactly the shape
  Phase 18's handoff warned about ("solving it above the seam rebuilds the fork GOV-01 closed").
  Accepted cost: the seam gains capability-specific knowledge (a field-name map), so it is no longer
  a pure validate-and-dispatch. — **Reversibility:** costly — the seam is the single contract all
  three surfaces route through; moving the resolution later means re-touching every surface at once.

  **Measured constraint the planner must design against — the field names are not uniform:**

  | Field | Count | Capabilities |
  |---|---|---|
  | `workspace_path: str` | 13 | research.*, curation.*, daily.*, ask.domain, bridge.detect, card.evaluate |
  | `workspace: Path` | 11 | knowledge.*, ingest.source, graph.status, help.suggest, workflow.status |
  | `install_root` | 2 | views.generate_data, views.validate_data |
  | `root` | 1 | workspace.init |
  | `path` | 2 | workspace.status, workspace.validate |

  Five names, two types, and `install_root` is a *different scope* from a workspace — the map is not
  a rename table.

- **D-02: A workspace id is the directory name under the install root; the valid set is the
  `discover_workspaces(install_root)` scan** (`src/construct/views/lib/discover.py:16`), recomputed
  per request rather than cached. No new state, no manifest, and the id is the name the user already
  recognises. A name-shaped validator — the `_validate_run_id` kebab-case guard pattern at
  `llm/curation_run.py:64-77` — rejects `..`, `/`, and absolute paths **before** resolution, so
  membership in the scan is the allowlist and string sanitation is only the first gate.
  Recomputing per request was chosen deliberately over a launch-time cache so a workspace created
  during a session (Phase 22's creation wizard does exactly this) is immediately addressable.

### Server shape and localhost hardening (HTTP-01 / HTTP-05)

- **D-03: FastAPI + uvicorn.** Pydantic v2 is already the input-model layer, so request validation,
  error shapes, and JSON-schema generation line up with what the registry already declares. Accepted
  cost: the heaviest dependency addition in a local-first tool that currently ships no web server
  (`pyproject.toml` has typer, pydantic, mcp, langgraph, streamlit — nothing HTTP). — **Reversibility:**
  costly — swapping later touches the route generator, the middleware carrying HTTP-05's controls,
  and every test that drives the app.

- **D-04: `construct serve` binds `127.0.0.1` on a fixed default port (`--port` overridable) and
  prints the URL.** Predictable and bookmarkable, and it keeps criterion 1's "one command" literally
  true. Ephemeral-port-plus-auto-open was rejected as unstable to reference in the Phase 24 UX-verdict
  playbook. **Planner obligation:** a port collision must produce a clear, actionable message — not a
  traceback. This is a first-run failure mode in the phase everything downstream depends on.

### Route generation and exposure (HTTP-02)

- **D-05: One envelope — `POST /api/capabilities/{id}` with a JSON payload.** Chosen over generated
  per-capability REST routes after the implications were worked through explicitly:
  - The zero-edit guard is near-impossible to drift when there is literally one route; per-capability
    GET/POST classification would need either a new `CapabilityRecord` field (29 declarations to keep
    honest, five registration guards to trip) or a name heuristic — and a heuristic on a generated
    surface is the exact silent-drift class this project has been bitten by twice (`_KNOWN_BROKEN`,
    the catalog's set-membership guard).
  - **Security interaction:** a JSON-body POST is not issuable by a drive-by page without CORS
    preflight, so `Origin`/`Host` validation becomes defence-in-depth. GET reads would make that
    check the single load-bearing control for HTTP-05, with a bug in it being a real read-exfiltration
    path.
  - Adding REST later is **additive** (generate alongside, envelope stays); going the other way means
    deleting URLs the SPA is already coded against.
  - The SPA's data layer becomes one `invoke(capId, payload)` function — which is what Phase 22's
    schema-driven wizards want anyway, since they do not know a route name at build time.

  Knowingly given up: linkable/cacheable data URLs and devtools legibility. Neither is being paid for
  by a single-user local PoC. — **Reversibility:** reversible — additive.

- **D-06: `GET /api/capabilities` is a discovery endpoint** returning each capability's id,
  description, and `model_json_schema()`. Phase 22's wizards generate forms from it the way
  `ui/capability_runner.py` already does for Streamlit, and no hardcoded field list can rot. This
  also **advertises the declared contract on at least one surface** — the half of GOV-01 that Phase
  18's D-21 had to concede when the pinned FastMCP turned out to have no schema-override parameter.
  Accepted consequence: the schema becomes a consumed contract, so changing an input model is a
  visible break rather than a quiet one.

- **D-07: All 29 capabilities are exposed by default; every exclusion is written down with its
  reason in a `COVERAGE.md`.** This is the artifact D-25 named as "genuinely worth writing — just as
  Phase 19 planning input". Full coverage is asserted by the guard, so a capability can never fall
  off the surface by nobody noticing, and criterion 1 stays literally true. Accepted cost: the
  awkward-input capabilities (`views.*` taking `install_root`, `workspace.init` taking `root`) must
  be genuinely resolved here rather than quietly skipped. Note `spike` and `tag` are not in the
  registry at all (Phase 18 D-02 — `spike run --tool-path` is an RCE primitive over HTTP), so they
  are out of scope by construction, not by opt-out.

### Error shape (HTTP-04, criterion 3)

- **D-08: WR-04 is closed on both sides — `from_validation_error`'s `model` parameter becomes
  required, AND HTTP joins 18-03's differential parity test as a third column.** Phase 18's own
  wording is the rationale: "a guarantee a caller can drop is a convention, not a contract" — so the
  footgun is removed at the type level. And criterion 3 must be proven mechanically by the same test
  that already proves CLI↔MCP parity, not by inspection: three of Phase 18's eight green self-reports
  turned out to contradict criteria they claimed met. Accepted cost: the signature change touches
  every existing call site. — **Reversibility:** reversible.

### Claude's Discretion

The user delegated these. A preference is recorded with each — planner and researcher have latitude
within it, but must record the outcome as a named decision.

- **Path-shaped payloads at the seam.** Preference: **id-first** — the seam accepts `workspace_id`
  and resolves it, while a raw path field still works for CLI, existing tests, and workspaces outside
  the install root; the HTTP adapter is generated so it can only ever emit `workspace_id`, guarded by
  a test, so criterion 2 holds by construction. Accepted cost of that preference: two payload shapes
  at the seam, which the parity table must cover. Alternatives weighed: id-only with the CLI
  translating at its own edge (one shape, but breaks a CLI pointed outside the install root), and
  adapter-side path rejection (one line, but re-creates the per-surface policy D-01 exists to avoid).
  **Research should measure how many CLI call sites and tests pass a path today before this is
  locked.**

- **`workspace.init` addressing.** It takes `root` and *creates* a directory, so there is no id yet —
  and T-18-34 was precisely "capabilities creating directories at agent-supplied paths". Options
  weighed: name-only with the server placing it under its own install root (caller cannot choose
  where bytes land — the T-18-34 lesson applied at the surface); a uniform resolve-rule where
  creation asserts *absence* instead of presence; or excluding it from HTTP entirely, which under
  D-07 now requires an explicit COVERAGE.md row and an explicit rewording of criterion 1. **Settle
  this alongside the exposure policy, not separately.**

- **Run execution model.** Preference: **detached subprocess** (`construct <workflow> run --run-id X`)
  for crash isolation, no sqlite-across-threads question, and browser/CLI symmetry falling out for
  free — both are just processes writing the same checkpoint. Alternatives: an in-process worker
  thread (simplest, richer live status, but a restart silently kills a run and this is where OQ-4
  gets sharp), or a bounded thread pool (serializes by construction, but a queued-not-started run is
  a status the checkpoint knows nothing about). Constraint: a synchronous call is **not** an option —
  criterion 5 requires the id to return immediately and the run to be pollable *while still running*.
  **Planner obligation for the subprocess route:** stderr from a failed spawn must surface somewhere
  the browser can see it.

- **Run enumeration (HTTP-07).** Preference: **a new `workflow.list` registry capability** that
  enumerates thread_ids across a workspace's checkpoint dbs and reports each run's status. HTTP picks
  it up free via generated routes, and CLI + MCP gain run listing at the same moment — which is the
  third-peer principle actually paying off rather than HTTP getting a private feature. Alternatives:
  widening the existing `workflow.status` (no new guards, but changes an existing output shape and
  conflates two questions), or having HTTP read the checkpoints directly (fastest, but a browser-only
  feature over durable state the CLI cannot see — the fork this phase's goal sentence forbids).
  **Research must confirm what the pinned `langgraph-checkpoint-sqlite` actually exposes for thread
  enumeration.**

- **OQ-4 — the checkpoint concurrency contract.** Preference: **WAL + `busy_timeout` on every
  checkpointer connection, no locking.** Concurrent readers never block, a writer waits rather than
  erroring, and two racing resumes are already handled correctly by D-11's checkpoint-id ETag — the
  loser rejects with zero writes, which is the right outcome. Alternatives: a server-held per-run
  single-flight lock (clearer message, but the guarantee is one-sided since a CLI resume cannot see
  it — that limitation must be written down, not implied away), or a lockfile visible to both
  processes (real mutual exclusion, but stale-lock recovery is new failure surface whose failure mode
  is a permanently un-resumable run). **The ADR-0004 extension gets written whichever way this lands.**

- **Progress reporting.** Preference: **client polls the inspect endpoint now; SSE deferred to Phase
  21**, which owns the guided layer and will actually see whether chunky progress hurts. Polling costs
  nothing new, works identically for a run the server did not start, and degrades to "refresh the
  page". SSE is genuinely better UX for a long research run but is real new server surface —
  long-lived connections, reconnect, and it must work for runs the server did not start — inside the
  phase that is already the hard gate for everything downstream.

- **T-18-10 / T-18-32 path-leak remediation shape.** Preference: **land a sanitizer at the shared
  boundary so criterion 3 holds mechanically, AND add a shrink-only guard** so the source sites cannot
  grow — the `UNRESOLVED_DIRECT_CALLERS` pattern D-23 already established in this repo. A boundary
  sanitizer alone fixes ~29 sites with one change (and closes MCP's `str(exc)` leak as a side effect)
  but treats symptoms: `services/knowledge.py` keeps building messages from `str(exc)`, so anything
  bypassing the serializer leaks again. Fixing all ~27 sources genuinely removes the leak but is a
  large hand-edit inside a phase already carrying an adapter, a seam change, and a run model.
  **Research should measure how many of the ~27 sites actually reach a serialized body** before the
  split is fixed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 19: HTTP API over the Capability Registry" — goal, the 5 success
  criteria, the OQ-4 open decision, and the research flag on the localhost threat model.
- `.planning/REQUIREMENTS.md` §§ HTTP-01..HTTP-07 (lines 23–29) and the traceability rows (156–162);
  § "Out of Scope" line 140 — "minimal localhost hardening (HTTP-05) is in scope and is a trust
  boundary, not production hardening".
- `.planning/PROJECT.md` § "Active" — the five carried-forward items from Phase 18 that this phase
  owns, especially the T-18-10/T-18-32 pair named as a criterion-3 dependency; § "Out of Scope" —
  no auth/multi-user/remote hosting.

### Phase 18 handoff — the contracts this phase builds on
- `.planning/phases/18-contract-governance-foundations/18-CONTEXT.md` — D-05/D-06/D-07 (the seam is
  strict, `extra="forbid"` across all models, `handler(**model.model_dump())`); D-08 (the differential
  parity test D-08 above extends); D-09/D-11 (`proposal_id` + checkpoint-id ETag — the review contract
  the HTTP review endpoints surface); D-21 (MCP cannot advertise input schemas — the gap D-06 closes
  on HTTP); D-23 (the shrink-only baseline pattern); D-25 (the COVERAGE.md counter-argument D-07 acts on).
- `.planning/phases/18-contract-governance-foundations/18-SECURITY.md` — T-18-10, T-18-32, T-18-34.
- `.planning/phases/18-contract-governance-foundations/18-REVIEW.md` — WR-04 (the optional `model`
  parameter D-08 closes) and the 12 remaining warnings.

### Architecture decision records
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md` — sanctions
  `.construct/workflow/*.sqlite` as durable state. **OQ-4's concurrency contract extends this ADR —
  writing that extension is a Phase 19 deliverable.**
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — the permanent L0–L4 runtime model
  the HTTP adapter must sit within.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` — views refresh ownership; relevant
  because `views.*` are now registry capabilities (Phase 18 D-02) and therefore exposed under D-07.

### Live code this phase touches or generates from
- `src/construct/capabilities/registry.py` — `invoke()` is the seam D-01 extends; note its docstring
  explicitly forbids strict/lenient flags and per-surface exceptions.
- `src/construct/capabilities/errors.py` — `CapabilityInputError.from_validation_error`, whose
  optional `model` parameter D-08 makes required.
- `src/construct/mcp/server.py` (71 lines) — the structural proof that a surface can be *generated*,
  and the model for HTTP's own generator. Also the site of the `str(exc)` leak in its `except` branch.
- `src/construct/capabilities/catalog.py` — the 29 records and their five different workspace field
  names (D-01's table).
- `src/construct/views/lib/discover.py:16` — `discover_workspaces(install_root)`, D-02's allowlist source.
- `src/construct/llm/curation_run.py` — `_open_checkpointer:494-508` (per-workflow-type sqlite db,
  `check_same_thread=False`, no WAL, no `busy_timeout` — OQ-4's subject); `_validate_run_id:64-77`
  (D-02's validator pattern); `inspect_curation_run:1764` (the existing read-only poll primitive);
  `_new_run_id:430`.
- `src/construct/llm/research_run.py:1034-1048` — the same checkpointer pattern for research.
- `src/construct/services/knowledge.py` — the ~27 `str(exc)`-into-`OperationResult.message` sites.
- `src/construct/ui/capability_runner.py` — the existing dynamic-form-from-JSON-Schema precedent D-06
  gives the browser.
- `tests/contract/test_artifact_catalog.py` — the set-membership-not-cardinality weakness (WR-01) that
  D-07's coverage guard must not repeat.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`mcp/server.py`'s registry-driven generation (71 lines)** — a whole surface generated by iterating
  `registry.list_mcp_tools()` and closing over each capability. HTTP's generator is the same shape;
  the file has never been hand-edited to add a capability, which is the guarantee criterion 1 asks
  HTTP to reproduce. Its `_serialize_result` docstring also records why `json.dumps` is deliberately
  left without a `default=` fallback (T-18-10) — the HTTP serializer inherits that reasoning.
- **`discover_workspaces(install_root)` (`views/lib/discover.py:16`)** — already returns the exact set
  D-02 needs, with `_is_workspace` heuristics and exclusions already written.
- **`_validate_run_id` (`llm/curation_run.py:64-77`)** — an existing kebab-case identifier guard,
  written because "the MCP/CLI shims pass caller-supplied `**kwargs` straight into the input models".
  D-02's `workspace_id` validator is the same pattern.
- **`inspect_curation_run` / `inspect_research_run`** — already read persisted checkpoint state
  *without resuming*, surfacing `awaiting_review` with the pending `gate_queue`. HTTP-06's polling
  needs no new read path, only an id.
- **18-03's differential parity table** — D-08 adds a column rather than building a new harness.
- **`ui/capability_runner.py`** — Streamlit already generates forms from `model_json_schema()`;
  D-06 hands the browser the same input the Streamlit UI consumes.

### Established Patterns
- **The registry is the single contract behind every surface; parity is free via auto-discovery.**
  Adding a capability must never require editing a server module. D-05 and D-07 are both chosen to
  preserve this.
- **Guards are widened, never narrowed** (`_KNOWN_BROKEN` / `_DOC_GLOBS`), and **cardinality beats
  set-membership** (WR-01, Phase 18 D-04/D-19). D-07's coverage guard must assert count, not
  membership.
- **Shrink-only baselines for known debt** (D-23's `UNRESOLVED_DIRECT_CALLERS`) — the recommended
  shape for the path-leak source sites.
- **Silent success is this codebase's named default failure mode** (T-15-14, "audit-trail-that-lies").
  Every mechanical guard in this phase is a countermeasure to some instance of it.

### Integration Points
- **`registry.invoke()`** — D-01 changes its behaviour for all three surfaces at once. This is the
  highest-blast-radius change in the phase and belongs early, with the parity test as its gate.
- **`.construct/workflow/*.sqlite`** — the durable state HTTP-06/07 and OQ-4 both act on. It is
  per-workspace and per-workflow-type (`curation-run.sqlite`, and the research equivalent), so
  enumeration must span dbs, not one file.
- **`proposal_id` + checkpoint-id ETag (Phase 18 D-09/D-11)** — Phase 19's review endpoints must
  surface both. Phase 22 owns the browser-side `If-Match`/409 *behaviour*; this phase must not
  foreclose it.
- **`_wrap_resume` is mandatory** for any surface driving the graph directly — a bare id-keyed dict
  is read by LangGraph as an interrupt-id mapping and silently discarded, leaving the run paused with
  no error. Carried forward from Phase 18 explicitly for this phase.
- **`_payload_for`'s miss surfaces as a bare `KeyError`**, and registering a capability trips five
  guards, not one. Derive the route table and test payloads from the registry — never hand-list them.
- **Phase 21** consumes whatever this phase produces for progress reporting and static serving;
  **Phase 22**'s wizards consume D-06's schema endpoint; **Phase 23**'s browse pages consume the
  envelope.

</code_context>

<specifics>
## Specific Ideas

- The user asked for the route-shape implications to be spelled out before deciding, and chose the
  single envelope **after** seeing that (a) the drive-by/preflight property makes `Origin`/`Host`
  defence-in-depth rather than load-bearing, (b) per-capability GET classification has no home in the
  registry today and would rest on a heuristic, and (c) envelope→REST is additive while REST→envelope
  deletes URLs the SPA is coded against. The decision is informed, not default — a planner proposing
  REST routes is re-opening a considered choice and needs new evidence, not new preference.
- The user consistently delegated *mechanism* (execution model, concurrency primitive, listing home,
  leak-fix shape) while locking *contract* (where resolution lives, what an id is, what is exposed,
  what the error guarantee is). Read the discretion items as "pick the mechanism that satisfies the
  locked contract", not as open scope.
- D-07 ("all 29, opt-outs written down") was chosen over a curated allowlist specifically because an
  allowlist weakens the zero-edit guarantee — a new capability would need an allowlist edit, which is
  the drift the guard exists to prevent. If the planner finds a capability that genuinely cannot be
  exposed, the answer is a reasoned COVERAGE.md row, never a silent omission.
- D-06 was chosen partly because it recovers, on HTTP, the schema-discoverability half of GOV-01 that
  Phase 18's D-21 had to concede upstream. Worth stating in the summary — it is a real closure of a
  known-open gap, on a different surface.

</specifics>

<deferred>
## Deferred Ideas

- **SSE / streaming progress** — deferred to Phase 21, which owns the guided layer and can judge
  whether polling's chunky, node-boundary progress actually hurts the UX verdict.
- **Per-capability REST routes** — deferred; additive over D-05's envelope if Phase 21/23 bring
  evidence that the SPA needs them.
- **The ETag's browser-side behaviour** (`If-Match`, `409 Conflict`, refreshed queue in the body) —
  Phase 22, per Phase 18's own deferral. Phase 19 surfaces the ETag; it does not define the retry UX.
- **Serving the SPA's static files** — nominally Phase 21. Raised here only because one token-delivery
  option (server-injected token in `index.html`) would pull static serving forward; if the planner
  picks that option, the pull-forward is a decision to record, not a side effect.
- **API versioning** — not raised as a concern for a single-user local PoC on an isolated branch.
- **RT-01/RT-02 registry unification for `spike` and `tag`** — still deferred (v0.6). `spike run
  --tool-path` is deliberately excluded from HTTP as an RCE primitive.
- **Fixing `tests/contract/test_artifact_catalog.py`'s own set-membership weakness (WR-01)** — this
  phase applies the cardinality lesson to its *new* guards; repairing the catalog guard stays deferred.
- **`card list` MCP-boundary hardening (WR-01/WR-02)** — whatever Phase 18's seam did not cover
  remains carried-forward debt.

</deferred>

---

*Phase: 19-HTTP API over the Capability Registry*
*Context gathered: 2026-08-02*
