# Pitfalls Research

**Domain:** Adding a browser UI + local HTTP API + document ingestion to a governed, local-first CLI/MCP knowledge product (CONSTRUCT v0.5 PoC)
**Researched:** 2026-07-26
**Confidence:** HIGH for in-repo evidence (read directly from source), HIGH for library behaviour (Context7/official docs), MEDIUM for localhost-security ecosystem claims (web search)

> The previous milestone's pitfalls research is preserved at `.planning/research/archive-v04/PITFALLS.md`.

## How to read this document

Every pitfall below is either (a) already present in this repository and cited by file:line, or (b) a documented failure mode of a library v0.5 will add. Generic web-development advice has been deliberately excluded.

**Suggested phase names** used in "Phase to address" (numbering continues from Phase 17; the roadmapper may renumber — the topics are what matter):

| Ref | Suggested phase topic |
|-----|----------------------|
| **P18** | Data-contract reconciliation (`views generate` ↔ `views validate`, registry invocation seam) |
| **P19** | HTTP adapter over the capability registry (third adapter, error shape, localhost hardening) |
| **P20** | Document ingestion & real text extraction (upload → extract → route → review) |
| **P21** | SPA promotion + live-data browse / wiki / graph |
| **P22** | Guided action layer + the two HITL review wizards (`research.review`, `curation.review`) |
| **P23** | Evaluation spikes (SEED-001/002/003) + the UX verdict and E2E demo gate |

---

## The recurring class: writer/reader contract forks

Three forks were found and fixed in the week before this milestone started (`.planning/STATE.md` Blockers/Concerns):

1. **Lifecycle key fork** — `schemas/card.py:103` made `lifecycle` optional-with-default so `create_card` never serialized it, while `views/lib/parse_cards.py:7` required the literal key. CLI-created cards were silently dropped from `cards.json`; `views generate` still exited 0.
2. **`archive_card` body destruction** — the body was discarded on read (`_, _, raw = ...`) and re-serialized as the empty section template. Unrecoverable data loss, reachable *unattended* through `curation_run.apply_archives:963`.
3. **Leading-newline accretion** — `parse_card_markdown` returned a body carrying a leading newline; `_card_dict_to_markdown` emitted its own. Every rewrite added a blank line, unbounded.

These are not three unrelated bugs. They share one root cause and three consequences that v0.5 inherits:

- **Root cause:** the contract lived in *two* places (a writer and a reader), and each side was tested against its own idea of the contract. No test ever fed the writer's real output to the real reader. The tests that finally pinned each fix are round-trip tests (`tests/integration/test_views_generate.py`).
- **Consequence 1 — silent success.** In all three cases the failing operation reported success. This system's default failure mode is *a lie in the audit trail*, not a crash. The class is already named in-repo as T-15-14 "audit-trail-that-lies": `views_refresh_hook`'s docstring (`llm/curation_run.py:975-990`) documents removing a hardcoded fake `skipped`, and `workflow.run` was removed in Phase 12 for fake success.
- **Consequence 2 — no backfill.** Every fix was writer-side. There is no migration path. Cards lacking `lifecycle` stay invisible until re-saved; destroyed bodies are gone. **Anything v0.5 writes wrongly is written wrongly forever.**
- **Consequence 3 — a fourth fork is already open and inherited:** `views validate` rejects 3 of the 8 files `views generate` writes (`stats.json`, `<ws>/connections.json`, `<ws>/events.json`), pinned by `test_views_validate_does_not_yet_accept_generated_bytes`.

v0.5 adds **two new writers** (the HTTP adapter and the document extractor) and **one new reader** (the SPA on live data). Treat every pitfall below that mentions a contract as an instance of this class, not as an isolated risk.

---

## Critical Pitfalls

### Pitfall 1: The new surface becomes a second write path that bypasses the workflow

**What goes wrong:**
The UI implements "Approve" as a direct call to a write capability instead of as `Command(resume=…)` against the checkpointed run. The propose-then-reviewed-apply invariant then holds *only for the CLI*, and the browser becomes an unreviewed writer.

**This is already in the repository.** `src/construct/ui/gate_review.py:252-281` — the Streamlit "Gate Review" bridge-approve button calls `registry.get("knowledge.connection.add").handler(...)` **directly**, with a hard-coded `ConnectionType.parallels`, regardless of what the L3 connection-typing gate decided. Compare `llm/curation_run.py:912-923` (`apply_connections`), which reads `payload["connection_type"]` from the reviewed proposal. Two write paths, two different semantics, one of which is not downstream of any `interrupt()`.

**Why it happens:**
`Command(resume=…)` requires holding a `run_id`, re-opening a checkpointer, and reasoning about a paused graph. A direct handler call is one line and demos identically. The registry makes every write capability trivially reachable — `catalog.get_registry()` is importable from anywhere — so the *easy* thing is the *wrong* thing.

**How to avoid:**
- The HTTP adapter exposes **no** direct-write endpoint for anything a workflow owns. Approving a proposal is only ever `POST /runs/{run_id}/review` → `curation.review` / `research.review`.
- Add a contract test asserting the write capabilities that sit behind a gate (`knowledge.card.edit`, `knowledge.card.archive`, `knowledge.connection.add`) are not reachable from the review endpoints — mirroring the existing forbidden-tools guard pattern used on skills.
- Decide explicitly what happens to `src/construct/ui/gate_review.py`. Leaving a second UI that forges gates is worse than either keeping or deleting it.

**Warning signs:**
- Any import of `construct.services.knowledge` or of `curation_run`'s apply nodes inside API/UI code.
- A UI "approve" handler that does not need a `run_id`.
- An approve action whose payload does not round-trip through the checkpointer.

**Phase to address:** **P19** (adapter boundary rule + guard test); enforced again in **P22** (review wizards).

---

### Pitfall 2: The gate queue moves into browser/session state and the audit log starts lying

**What goes wrong:**
The pending-review queue is rendered from a value the client holds, and "approve" mutates client state *plus* writes an audit event — while the canonical checkpoint stays paused forever. The event log records approvals that were never applied.

**This is already in the repository.** `src/construct/ui/gate_review.py:56-57` initialises `st.session_state.gate_queue`; lines 151-169 flip `review_status` in session state and call `_log_gate_event(... "gate_review_approved" ...)`, appending to `log/events.jsonl` — the same append-only audit trail `curation_run._emit` writes to. Nothing is applied. On browser refresh the queue is gone and the events remain.

**Why it happens:**
Session state is the fastest way to make a review UI feel responsive, and event logging is easy to bolt on because `append_event` is non-blocking and never fails loudly.

**How to avoid:**
- **Rule: only a node inside the graph may emit `gate_review_approved` / `gate_review_rejected`.** The API/UI never calls `append_event` directly.
- Every pending-review render is a fresh read of `curation.inspect` / `research.inspect`; a cached client copy may be displayed but never used as the basis of the decision payload.
- Test: after an approve through the API, assert the number of `gate_review_*` events equals the number of proposals actually written, and that a rejected-then-refreshed flow produces zero write events.

**Warning signs:**
- `append_event` imported anywhere under the API/UI layer.
- Any state named `gate_queue` outside `CurationRunState` / research `RunState`.
- Event counts in `log/events.jsonl` exceeding the number of changed cards.

**Phase to address:** **P22** — but the rule must be written into the adapter contract in **P19**.

---

### Pitfall 3: `input_model` is documentation, not enforcement — and the third adapter makes that visible

**What goes wrong:**
The capability registry declares `input_model` for all 28 capabilities, and **no adapter validates against it.** Adding HTTP forces the question, and whichever answer is taken quietly creates a parity fork.

Evidence:
- `mcp/server.py:33` — `result = capability.handler(**kwargs)`. The model is never constructed. `CardListInput.model_config = {"extra": "forbid"}` (`catalog.py:145-147`, added explicitly as an ASVS boundary control) is therefore **inert over MCP** — exactly what code-review item WR-02 recorded.
- `registry.py:63` — `input_model` is used *only* to emit `model_json_schema()` for the MCP tool list.
- `ui/capability_runner.py:197` — the Streamlit form builds from the same JSON Schema and then calls `cap.handler(**inputs)`; lines 292-297 carry an explicit admission: *"Some capability handlers require specific positional arguments and cannot accept `**kwargs` from the form yet."*
- `cli.py` calls handlers **both** ways: positionally (`cap.handler(path)` at :89, :107, :143) and by keyword (`cap.handler(**handler_kwargs)` at :420, :586, :633). RT-03 shims exist specifically to be dual-mode (STATE.md, Phase 07-01).

So there are already three calling conventions and zero validation. An HTTP adapter that *does* validate becomes stricter than CLI and MCP (same input, different outcome by surface). One that *doesn't* passes arbitrary JSON straight into handlers that build `Path` objects.

**Why it happens:**
The registry *looks* like it enforces a contract, so nobody checks. Declaration and enforcement were never wired together, and the gap is invisible until a surface with untrusted input arrives.

**How to avoid:**
- Add one seam: `registry.invoke(cap_id, payload: dict)` that constructs `cap.input_model(**payload)` and dispatches from the validated model. Route **all three** adapters through it. This is the single highest-leverage structural change in the milestone.
- The parity test that **actually catches drift**: a **differential table test** — for a fixed set of `(cap_id, payload)` cases, assert CLI, MCP and HTTP produce the same `OperationResult` fields (`success`, `message`, error reasons).
- The parity test that **only appears to catch drift** (and already exists): inventory/set-membership assertions. `tests/contract/test_artifact_catalog.py` enforces row set-membership, not cardinality (recorded as WR-01) — it proves every capability is *listed*, never that two surfaces *behave* the same.

**Warning signs:**
- Any adapter code doing its own `if not payload.get("workspace")` checks.
- Handler signatures that only work with one adapter's calling convention.
- A bug reproducible over one surface and not another.

**Phase to address:** **P18** (build the seam before the HTTP adapter exists) and **P19** (route the adapter through it; differential test).

---

### Pitfall 4: `workspace` is an unconstrained path, and HTTP turns that into a filesystem primitive

**What goes wrong:**
Almost every input model takes `workspace: Path` with no constraint. Over CLI and stdio-MCP the caller is already the user or their agent. Over HTTP — reachable from any page the user's browser visits (Pitfall 12) — an unconstrained workspace path is an arbitrary-directory read *and write* primitive: `workspace.init` scaffolds, `ingest.source` writes refs, `knowledge.card.create` writes markdown.

Note the asymmetry that already exists: `run_id` **is** guarded (`llm/curation_run.py:64-77`, `_validate_run_id`, kebab-case) explicitly because *"the MCP/CLI shims pass caller-supplied `**kwargs` straight into the input models, so an unvalidated value such as `../../../tmp/evil` would cross into the persistence/path layer."* The same reasoning was applied in Phase 14-04 to refuse an editable LLM-config path in the Streamlit sidebar — *"an editable path wired to a loader would make the ops dashboard an arbitrary-file-read primitive."* Neither guard was ever extended to `workspace`.

**Why it happens:**
"Local-first, single user, my own machine" reads as "no attacker." It isn't: the browser is the attacker's delivery vehicle.

**How to avoid:**
- The API resolves workspaces from a **server-side install-root allowlist**, not from a client-supplied path. Endpoints take a `workspace_id` (a discovered child of the install root), never a filesystem path.
- Extend the identifier guard to `workspace_id`, reusing `KEBAB_CASE_PATTERN`.
- Test: `POST` with `workspace: "../../etc"` returns 400 and touches nothing.

**Warning signs:**
- Any API route whose request body contains a path the server passes through to a handler.
- `Path(payload["workspace"]).resolve()` in adapter code.

**Phase to address:** **P19**.

---

### Pitfall 5: Stale gate state + positional decisions = decisions applied to the wrong proposals

**What goes wrong:**
The review UI renders the queue returned at pause time. The user reads it, walks away, and meanwhile a terminal runs `construct curation run`. The browser then submits decisions. Because the resume payload is a **positional list**, decision *i* is applied to whatever proposal now sits at index *i*.

`llm/curation_run.py:777-796` (`_resolve_decisions`) zips `raw[i]` against `gate_queue[i]`, and `_normalize_decision(None, default)` falls back to the **proposal's own recommended decision** — i.e. a short or misaligned payload silently *approves the gate's recommendation*, which is a write. Proposals have no id: `CurationProposal` (`:164-179`) is `{kind, decision, payload}` only. There is no way for a client to say "this decision belongs to that proposal."

**Why it happens:**
Positional decisions were correct for a CLI where render and resume are one command, milliseconds apart. A browser inserts unbounded human time and a second actor between the two.

**How to avoid:**
- **Give every proposal a stable `proposal_id`** at enqueue time and make the resume payload a map, not a list. Small change to `CurationProposal` / `_resolve_decisions`; eliminates the whole class.
- **Optimistic concurrency:** return the checkpoint id from `graph.get_state(cfg).config["configurable"]["checkpoint_id"]` as an ETag alongside the queue; require `If-Match` on resume; `409 Conflict` on mismatch with the refreshed queue in the body.
- Change the missing-decision fallback from "approve the recommendation" to "reject" for the HTTP path, or make the decision a required field. A default that *writes* is the wrong default for a surface that can lose a request.
- Test: pause a run, mutate the queue, resume with the old payload → assert 409 and zero writes.

**Warning signs:**
- A UI rendering proposals from a value stored at page load and submitting against it.
- Review payloads that are arrays of bare strings.
- An "approve all" button carrying no queue fingerprint.

**Phase to address:** **P22** (ETag + wizard), with the `proposal_id` model change landing in **P18/P19** so the API is never built against the positional shape.

---

### Pitfall 6: Double-resume and concurrent CLI/UI resume of the same checkpoint

**What goes wrong:**
Two `Command(resume=…)` calls hit the same `thread_id`. The only guard is a check-then-act: `review_curation_run:1232` (`if snap.next != ("process_inbox",)`) and `research_run.review_research_run:1056` (WR-05). Two concurrent requests both read `next == (gate,)` and both invoke. LangGraph provides no locking of its own.

Damage is *bounded but real* because the apply nodes were built idempotent (skip-if-at-target `:864`, `add_connection` dedup `:914-919`, skip-if-archived `:960`) — but:
- `gate_review_approved` events **double-fire**: they are emitted per item regardless of whether the write was a no-op (`:872`, `:923`, `:968`).
- Two processes writing `.construct/workflow/curation-run.sqlite` — a long-lived API process holding a persistent connection (`_open_checkpointer`, `check_same_thread=False`) plus a separate CLI process — will produce `database is locked`, surfacing as an opaque 500.

**Why it happens:**
Idempotent apply nodes create false confidence that concurrency is handled. They handle *repetition*, not *interleaving*, and they do not protect the audit log or the checkpoint store.

**How to avoid:**
- Single-flight per `run_id` inside the API process (a lock keyed by run id) **plus** the ETag from Pitfall 5 — the lock stops same-process races, the ETag stops cross-process ones.
- Open the checkpointer with `journal_mode=WAL` and a `busy_timeout`; **decide and record** this rather than discovering it. adr-0004 already sanctions this sqlite file as durable state — extend that record with its concurrency contract.
- Map `sqlite3.OperationalError: database is locked` to a specific 409/503 with a "this run is being reviewed elsewhere" message, never a generic 500.
- Test: fire two concurrent resumes; assert exactly one set of `gate_review_*` events.

**Warning signs:**
- Duplicate `gate_review_approved` entries for the same target in `log/events.jsonl`.
- Intermittent 500s during review that vanish on retry.
- A UI approve button that stays enabled after click.

**Phase to address:** **P22**; the WAL/locking decision belongs in **P19** (it is a property of running a long-lived server against workspace state).

---

### Pitfall 7: Orphaned runs — a run whose id was lost is unreachable and pauses forever

**What goes wrong:**
`run_curation_run` auto-generates a `run_id` when none is supplied (`:1164`). A synchronous `POST /curation/run` that times out (the LLM fan-out in `promotion_review` and `connection_maintenance` is unbounded in wall clock), or a user who refreshes, produces a **second** run — while the first sits paused at `process_inbox` holding archive/promotion proposals over the same cards.

**There is no capability to list runs.** `curation.inspect` requires a `run_id` you must already possess (`:134-141`). A lost id means an unreachable, permanently pending run holding unapplied human-review state.

**Why it happens:**
The CLI hands the run_id back on stdout and a human keeps it. A browser has no equivalent memory, and the missing list capability went unnoticed because no CLI user needed it.

**How to avoid:**
- **Add a run-list capability** (enumerate `thread_id`s in the checkpoint DB with their `next` node and step count). The UI cannot be honest about pending work without it, and the guided layer cannot suggest "you have a review waiting." This is a *runtime* gap, not UI work — it belongs in a capability so CLI and MCP get it too.
- Client-supplied idempotent `run_id` on run-start; reject a start whose id already has a paused run.
- Never make run-start a synchronous request/response. Start → return `run_id` immediately → poll `inspect`.
- Surface pending runs in the guided action layer so an orphan is visible rather than silent.

**Warning signs:**
- Multiple threads in `awaiting_review` in one workspace.
- A UI that cannot answer "what is waiting for me?" without the user pasting an id.

**Phase to address:** **P19** (list capability) and **P22** (render it).

---

### Pitfall 8: Extraction that "succeeds" while extracting nothing

**What goes wrong:**
`pypdf.extract_text()` **cannot** read text from images. A scanned or image-only PDF returns an empty string or OCR noise with **no exception**. The ref and seed card are created; the card body says "Seed card from ingested file"; the graph gains a node standing for content nobody has.

The current code makes this worse. `pipelines/ingestion.py:86-88`:

```python
extraction = (
    ExtractionStatus.complete if (key_findings or title) else ExtractionStatus.partial
)
```

**A caller-supplied title alone stamps `extraction_status: complete`.** An upload wizard that derives a title from the filename — the obvious implementation — will mark every scanned, encrypted or empty PDF as fully extracted. That is the audit-trail-that-lies class, in the ingestion path, on data with no backfill.

**Why it happens:**
Today ingestion is agent-driven — *"extraction is the orchestrator's job, the CLI persists"* (`ingestion.py:70-71`). v0.5 moves extraction *into* the pipeline but the status heuristic is left where it was.

**How to avoid:**
- Derive `extraction_status` from the **extractor's measured output** — characters extracted, pages with zero text, extractor used — never from the presence of caller metadata. Delete the `or title` branch as part of P20.
- Add an explicit failed/empty status and a yield heuristic (e.g. < 100 chars/page across the document → `partial` plus a surfaced reason).
- Tell the user: "This looks like a scanned PDF — CONSTRUCT extracted no text. OCR is out of scope." A visible failure is a far better PoC outcome than a silent empty card.
- Fixture set must include: an image-only PDF, an encrypted PDF, a zero-byte file, a `.pdf` that is actually a JPEG, a CJK/UTF-16 document, and a 200-page document.
- Test: an image-only PDF produces `extraction_status != complete` and a card body that records the failure.

**Warning signs:**
- Cards whose only body content is the seed template.
- `extraction_status: complete` on refs whose card body has no findings.
- The demo only ever uses one known-good PDF.

**Phase to address:** **P20**.

---

### Pitfall 9: Hostile and hostile-by-accident file input

**What goes wrong:**
A `.docx` is a ZIP of XML. Parsing untrusted XML with a default parser exposes XXE (python-docx < 0.8.6, CVE-2016-5851) and entity-expansion "billion laughs" DoS; the ZIP container additionally permits decompression bombs. PDFs can be decompression bombs or malformed in ways that make pure-Python parsing pathologically slow. On a FastAPI `UploadFile`, `filename` and `content_type` are **client-controlled**, and `filename` is the natural (wrong) choice for building `refs/{id}.json`.

**Why it happens:**
"It's my own file on my own machine" — but the upload endpoint is reachable from the browser, and the browser can be driven by a web page (Pitfall 12). Documents are also routinely obtained from third parties.

**How to avoid:**
- Parse document XML with `defusedxml` (or `lxml` with `resolve_entities=False`); pin `python-docx >= 0.8.6`.
- Enforce a byte cap **while streaming**, before anything is parsed. `UploadFile.read()` with no argument reads the whole file into memory, and the spooled temp file will happily fill a laptop's disk.
- Cap page count / zip entry count / total decompressed bytes; run extraction under a wall-clock timeout.
- Sniff type from magic bytes; never trust `content_type`. Never use the client filename as a path component — derive the ref id through the existing `_to_kebab_case` + `_deduplicate_ref_id` path (`ingestion.py:183-186, 315-322`).
- Sanitize extractor errors the way the rest of the codebase does (`_sanitize_error`: class name + first line only) — a parser error message can echo document content into `log/events.jsonl` and the browser.

**Warning signs:**
- `ET.fromstring` or raw `lxml` anywhere in the extraction path.
- No size check before `await file.read()`.
- Extraction that occasionally pins a CPU core.

**Phase to address:** **P20**.

---

### Pitfall 10: Uploaded bytes have no home in the workspace contract

**What goes wrong:**
CONSTRUCT's file ingestion routes an **existing path** (`route_source_to_domain`, `ingestion.py:117`). An upload has no path. Three tempting answers each break something: write it into the workspace (a new artifact class not present in `workspace-contract.md`'s four classes, so `validate_workspace` and the views parsers know nothing about it); keep it in temp (the ref's provenance dangles after reboot); keep nothing (the ref points at a file that never existed and re-extraction is impossible).

**Why it happens:**
Upload is treated as plumbing rather than as a workspace-format question — and workspace-format continuity is a **core project constraint**.

**How to avoid:**
Make it an explicit, recorded decision in P20 planning with the workspace-contract implications named. The PoC-safe answer is probably: extract in a temp dir, persist only extracted text plus a content hash into the ref, and record that re-extraction needs the user's original file. The point is that it must be *decided*, not defaulted into existence.

**Warning signs:**
- New directories appearing under a workspace that `validate_workspace` does not know about.
- Refs whose `url` points at `/tmp` or `/var/folders`.

**Phase to address:** **P20**, decision recorded before implementation.

---

### Pitfall 11: Building the SPA on a projection that is known-broken

**What goes wrong:**
`generate()` validates an *adapted projection* of each file and then writes the **raw parser dict**; `views validate` applies the same models to the bytes on disk with no adapter, and rejects `stats.json`, `demo/connections.json`, `demo/events.json` (pinned exactly by `tests/integration/test_views_generate.py:285`). If the SPA is coded against the written bytes, the Pydantic models become dead documentation and fixing the contract later is a breaking change to every component. If the contract is fixed after the UI exists, the UI breaks.

**Why it happens:**
The SPA can be made to work today by reading whatever is on disk. The mismatch costs nothing until it is load-bearing — which is precisely the shape of the three forks above.

**How to avoid:**
- **Fix the contract first.** It is already named as the shared prerequisite of SEED-001 and SEED-003 and is the natural first phase.
- Completion signal is mechanical: `test_views_validate_does_not_yet_accept_generated_bytes` **must be deleted** — its own docstring says so. Replace it with a `generate → validate` round-trip that cannot pass vacuously (assert files were actually written *and* that all validate), mirroring the "widen the guard, never narrow it" discipline from FIX-03/FIX-04.
- Resolve by conforming the **written bytes** to the models where possible — the standing project decision is "conform the data to the gate, not weaken the gate." Widening the models to accept whatever `generate` happens to emit is the tempting inverse and should require an explicit, argued exception.

**Warning signs:**
- SPA TypeScript types hand-written from observed JSON rather than derived from `views/models.py`.
- Any plan that schedules UI work before P18 lands.

**Phase to address:** **P18** — it must be first.

---

### Pitfall 12: A localhost server is a public surface

**What goes wrong:**
A browser enforces same-origin by **hostname, not IP**. A page the user visits can rebind its own domain to `127.0.0.1` and drive a local API with no CORS error and no warning. This is not theoretical for this product class: CVE-2025-66414 (MCP TypeScript SDK, Dec 2025, CVSS 7.6) let any web page issue arbitrary requests to localhost MCP servers. CONSTRUCT's API would expose filesystem writes, workspace creation, and LLM calls billed to the user's own API keys.

PROJECT.md correctly puts *production hardening (auth, multi-user, remote hosting)* out of scope. **Localhost hardening is not production hardening** and must not be waived by that line.

**Why it happens:**
"It's only localhost" is the most common misconception in local-first tooling, and dev servers default to permissive CORS.

**How to avoid (all cheap, all PoC-appropriate):**
- Bind `127.0.0.1` explicitly, never `0.0.0.0`.
- Validate `Origin` **and** `Host` against an allowlist; 403 otherwise.
- No wildcard CORS; never `allow_credentials` together with `allow_origins=["*"]`.
- A per-launch random token printed by `construct serve` and required by the SPA — roughly 20 lines, and it closes the drive-by case entirely.
- Test: foreign `Origin` → 403; missing token → 401.

**Warning signs:**
- `allow_origins=["*"]` anywhere.
- `--host 0.0.0.0` in any doc, script, or README.
- The API reachable from a phone on the same wifi.

**Phase to address:** **P19**.

---

### Pitfall 13: Local-first erosion — logic migrates into the server, and the build becomes a prerequisite

**What goes wrong:**
Two independent drifts with the same outcome (the product now needs a server and a toolchain):

1. **Logic in the adapter.** Endpoints start aggregating, filtering and shaping — because it is faster than adding a capability. The CLI then cannot do what the UI can, and "start the server" becomes the supported path. The registry's role as the single contract behind every surface is *already* flagged ⚠️ Revisit in PROJECT.md's Key Decisions (views/spike/tag bypass it — RT-01/RT-02). A third adapter with its own logic makes that permanent.
2. **The build toolchain.** React 19 / Vite 7 / Tailwind 4 means `npm install` + `npm run build` before anything renders. Today CONSTRUCT is `pip install` + `construct …`, and the v0.4.1 playbook is deliberately **offline-runnable**. Serving the SPA from a Vite dev server makes a fresh clone unusable offline — and makes the PoC unreproducible by whoever must render the UX verdict.

**How to avoid:**
- **Adapter contains no logic.** Every endpoint is `registry.invoke(cap_id, payload)` plus serialization. Anything the UI needs that no capability provides becomes a *capability* — and is then free over CLI and MCP too. (The run-list gap in Pitfall 7 is the first example.)
- Guard test: the API package imports nothing from `construct.services` / `construct.pipelines` / `construct.llm` except `capabilities.catalog`. Precedent exists — the codebase already enforces an acyclic `llm → views` edge by *replicating* `_sanitize_error` rather than importing across it (`views/refresh.py:44-55`).
- Ship prebuilt SPA assets served as static files by the API. A build step may exist for development but must not be required to run the PoC. Smoke test: fresh clone, no network, `construct serve` → UI renders.

**Warning signs:**
- An endpoint returning a shape no capability returns.
- A README that starts with `npm install`.
- Anything that only works when a dev server is running on a second port.

**Phase to address:** **P19** (adapter rule + import guard), **P21** (static serving + offline smoke test).

---

### Pitfall 14: Two read paths, one of them stale — the "the demo looks broken" moment

**What goes wrong:**
The PoC has both a live API over the registry **and** the `views/build/data/*.json` projection the SPA consumes. Two facts make them diverge visibly:

- **Per-card edits have no views-refresh path at all.** The debounced hooks were deleted with their two live skill registrations in 15-05; `views.per_card_hooks.*` is inert config (v0.6 OQ-3). A card created or edited in the UI therefore does not appear in the wiki/graph until a whole workflow runs.
- **`build_id` / `version.json` churns ~3× per daily cycle** (T-15-12: later views sweeps are full 11-file rebuilds, not near-no-ops), so naive SPA polling will thrash.

Result: the user creates a card in the browser, navigates to the graph, and it isn't there. This is the single most likely moment that destroys the UX verdict.

**How to avoid:**
- Choose **one** read path per surface and write it down: live API reads for anything the user can mutate in-session (cards, refs, help suggestions, review queues); the views build only for heavy derived projections (graph layout, wiki, stats).
- If both are used, expose `build_id` through the API so the SPA can show "graph is N minutes stale — refresh" instead of silently lying, and give the UI an explicit rebuild action calling `views.generate_data`.
- Do **not** re-home the debounce hooks inside the UI layer — that would be a fourth writer of derived data. If a per-edit refresh is needed it belongs in the Python capability layer (adr-0005 already settled that ownership).

**Warning signs:**
- A card visible in one view and absent from another in the same session.
- SPA polling `version.json` on a short interval.
- UI code reading `views/build/data/*.json` from disk instead of over the API.

**Phase to address:** **P21**, informed by **P18**.

---

### Pitfall 15: A UX verdict that cannot actually be reached

**What goes wrong:**
The milestone's success criterion is a *judgement*: can a person navigate CONSTRUCT unaided? That judgement is unreachable if (a) nobody can complete the end-to-end path without a developer present, (b) the demo path is pre-seeded so it never exercises a first-run empty workspace, or (c) the verdict is never written and the PoC becomes v0.6's foundation by default.

Specific traps:
- **The mock/degraded gap.** 16-06 recorded that **no mock search provider exists** — offline runnability comes from commands *degrading* with structured reporting. An offline demo will hit degraded states in `research.run`, `promotion_review` and `connection_maintenance` (provider total-outage → zero proposals, `curation_run.py:565`, `:689`). A UI that renders degradation as a spinner or as "success" makes the system look broken *and* discards the honest signal. Degraded must be a first-class UI state.
- **The empty-workspace path is the hardest and gets tested last.** `help.suggest`'s top priorities are literally `no_workspace` / `empty_domain` (`services/help.py:21-29`, `_score_domain`). The guided layer's entire value claim lives in exactly the state a developer's test workspace is never in.
- **The escalate dead-end.** `apply_promotions` records `escalate` as review-only with **no write** and emits `gate_review_rejected` with detail "escalated (review-only)" (`curation_run.py:849-852`). A UI offering three buttons implies escalate does something. It does not.

**How to avoid:**
- Write the **verdict template first**, in P23 planning, before the UI is built — fixed questions cannot be retrofitted to whatever shipped.
- The mechanical gate runs on a **fresh workspace, offline**, by someone who did not build it. Precedent exists: 16-07's D-09 was satisfied by a human's offline playbook run on a fresh test workspace.
- Build the walking skeleton (thin vertical slice: upload → extract → card → wiki + graph) **before** polishing any wizard. Four half-finished wizards validate nothing.
- Render degraded honestly; render escalate as "flagged — no action taken", or drop the button.
- Time-box the three spikes and require a verdict document **even on failure**. A spike that ran out of time and wrote nothing is the worst outcome.

**Warning signs:**
- The demo script requires editing a config file or running a CLI command "just this once."
- Every screenshot shows a populated workspace.
- Spike work is scheduled after the wizards.

**Phase to address:** **P23** (verdict artifacts, demo gate), with the walking-skeleton sequencing constraint imposed on **P20–P22**.

---

### Pitfall 16: Error shape forks three ways

**What goes wrong:**
`mcp/server.py:36-37` collapses every exception into `{"error": str(exc)}`, losing the structured `OperationError(reason, suggestion)` the services produce — code-review item WR-01. The CLI has its own `--json` shape. HTTP will invent a third: status codes plus a body. Three error vocabularies mean the SPA cannot reliably distinguish "invalid input", "workspace not found", "provider outage" and "bug", and will render a generic red box — or, worse, treat an HTTP 200 carrying `success: false` as success.

**Why it happens:**
Error handling is written per-adapter, at the end, under time pressure.

**How to avoid:**
- One shared serializer (generalize `_serialize_result`) used by MCP and HTTP; HTTP status derived from `OperationResult.success` and the error class, never from whether an exception escaped.
- Preserve `OperationError.reason` **and** `.suggestion` — the suggestion field is exactly what a guided UI should render, and it is currently discarded at the MCP boundary.
- Test: for a known-failing input, assert the same `reason`/`suggestion` strings appear over CLI `--json`, MCP, and HTTP.

**Warning signs:**
- The SPA showing "Something went wrong."
- HTTP 200 with `success: false` handled inconsistently across pages.

**Phase to address:** **P19** — this also closes the inherited WR-01/WR-02 debt.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| HTTP endpoints call `cap.handler(**payload)` directly, like MCP does | No new seam; ships in an afternoon | Third calling convention; `extra="forbid"` stays inert; unvalidated paths from the browser | **Never** — this is the milestone's structural risk |
| UI "approve" writes via `knowledge.*` capabilities instead of `*.review` | Trivial to implement; demos identically | Breaks propose-then-approve; a second write path with different semantics (already happened in `ui/gate_review.py`) | **Never** |
| Positional decision lists over HTTP | Matches the existing CLI resume shape | Decisions land on the wrong proposals when the queue moves | Only until `proposal_id` exists — i.e. one phase |
| SPA reads `views/build/data/*.json` from disk | No API work for browse/wiki/graph | Locks the UI to the unvalidated byte shape; stale after every card edit | Acceptable for the read-only graph/wiki projection **after** P18; never for mutable data |
| `extraction_status` inferred from caller metadata | Already coded; zero work | Refs permanently claim complete extraction of scanned PDFs; no backfill | **Never** — delete the `or title` branch |
| Keeping the Streamlit ops UI alongside the new SPA | Nothing to remove | Two UIs, one of which forges `gate_review_approved` events into the audit log | Only with the fake-gate page removed or fenced |
| Vite dev server as the way to run the UI | Fast inner loop | Offline/fresh-clone use breaks; the UX verdict becomes unreproducible | Development only; never the documented path |
| No mock LLM/search provider for the demo | Avoids building fixtures | The E2E gate can only run with credentials; degraded paths untested | Acceptable **only if** degraded states are first-class UI states and are the tested path |
| Skipping `Origin`/`Host` validation because "auth is out of scope" | Zero work | Any visited page can drive filesystem writes and spend the user's LLM credits | **Never** — it is ~20 lines |
| Synchronous run-start endpoints | Simplest possible API | Browser timeouts create orphaned paused runs holding unapplied decisions | **Never** for `research.run` / `curation.run` |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LangGraph `interrupt()` over HTTP | Doing prep/logging/writes in the interrupted node before `interrupt()` | The node re-executes top-to-bottom on resume — anything before the interrupt double-fires. `process_inbox` (`curation_run.py:738-753`) is already interrupt-only and documented as such; keep it that way |
| LangGraph `update_state` | Using it from the API to "fix" a stuck run | `update_state` writes a fresh checkpoint **without** carrying forward pending writes — it silently clears the pending interrupt and the queued decisions. Never expose it |
| SqliteSaver checkpointer | Assuming one process owns the DB | A long-lived API process plus a CLI process both write `.construct/workflow/*.sqlite`. Set WAL + `busy_timeout`; translate `database is locked` into an honest 409 |
| `mcp/server.py` | Hand-editing it to add HTTP-adjacent tools | MCP parity is free via registry auto-discovery and that file is never hand-edited — the same must be true of the HTTP adapter |
| `pypdf` | Treating a returned string as proof of extraction | Empty/garbage output on scanned PDFs raises nothing. Measure yield; try/except with a `pdfminer.six` fallback; `strict=False` for real-world files; handle `WrongPasswordError` |
| `python-docx` / any DOCX path | Default XML parsing | `defusedxml` or `resolve_entities=False`; pin `>= 0.8.6` (CVE-2016-5851); cap decompressed size and entry count |
| FastAPI `UploadFile` | `await file.read()` with no size argument | No built-in max size; stream in chunks against an explicit byte cap; sniff type; never use client `filename` as a path component |
| CORS / dev server | `allow_origins=["*"]` to make the SPA work | Explicit `http://127.0.0.1:<port>` allowlist + `Origin`/`Host` validation + a per-launch token |
| Tavily / search (existing) | Assuming the UI can rely on search working | `default_provider: mock`, and there is **no** mock *search* provider for offline runs — commands degrade. The UI must render degradation as a state, not an error |
| `help.suggest` | Calling it on every render as the "guided layer" | It globs `cards/*.md` and `refs/*.json` per domain and invokes `graph.status` (`services/help.py:61-145`). Call on navigation, not on render |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous `curation.run` / `research.run` behind one HTTP request | Browser spinner then timeout; user refreshes; duplicate orphaned runs | Start → return `run_id` → poll `inspect` | Immediately — the LLM fan-out is bounded by `concurrency_cap`, not by wall clock |
| SPA polling `version.json` | Constant refetch of all 8–11 files | `build_id` churns ~3× per daily cycle (T-15-12); poll on user action or a long interval, diff `build_id` not `generated_at` | As soon as any workflow runs while the UI is open |
| Full 11-file views rebuild on every workflow | Multi-second stalls after each approve | adr-0005 accepted 3 rebuilds per daily cycle; for the UI, never rebuild synchronously inside a request | ~200+ cards, or several domains |
| `help.suggest` filesystem scan per page load | Sluggish UI, disk churn | Call on navigation; cache per request | A few hundred cards |
| Whole-file extraction inside the request handler | The entire local UI freezes during upload | Extract off the request path with a timeout | A 100-page PDF on a single-worker local server |
| Single-worker uvicorn + blocking sqlite | One slow review blocks all reads | Keep handlers non-blocking, or accept and document single-user serialization | Any second browser tab |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Binding `0.0.0.0` / wildcard CORS on the local API | Any visited web page (or any device on the LAN) can create workspaces, write cards, and spend the user's LLM credits — the CVE-2025-66414 class | Bind `127.0.0.1`; validate `Origin` and `Host`; per-launch token; tests for 403/401 |
| Client-supplied `workspace` path passed through to handlers | Arbitrary directory read/write outside the install root | Server-side workspace allowlist; identifier, not path |
| A new HTTP input model that omits the `run_id` kebab guard | Reopens the checkpoint-path traversal `_validate_run_id` exists to close | Reuse `_validate_run_id`; test `../../../tmp/evil` → 400 |
| Default XML parsing of DOCX | XXE (file read / SSRF) and billion-laughs DoS from a document the user was invited to upload | `defusedxml`; `python-docx >= 0.8.6` |
| Unbounded upload size / decompression | Local disk and memory exhaustion; CPU pin | Byte cap enforced while streaming; decompressed-size and entry caps; extraction timeout |
| Echoing extractor/provider errors verbatim | Document content, or provider text that may carry a key, leaks into `log/events.jsonl` and the browser | Reuse `_sanitize_error` (class name + first line) on every new failure path — the discipline already exists at `curation_run.py:299` and `views/refresh.py:44` |
| Rendering card bodies / extracted text as HTML | Stored XSS from an uploaded document, executing with the local API's authority | Render as text/markdown with sanitization; never `dangerouslySetInnerHTML` on extracted content |
| Exposing a generic `POST /capabilities/{id}` | The Streamlit capability-runner pattern (any capability, any input) becomes remotely drivable | Curated endpoint set, not a generic dispatcher |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Degraded workflow states rendered as spinners or as success | User waits, then trusts an empty result; the honest "provider outage, zero proposals" signal is lost | First-class "degraded" state per step showing `CurationStepResult.reason` — the data already exists |
| An "Escalate" button that writes nothing | User believes they routed something for follow-up; nothing happened, and the log says `gate_review_rejected` | Label it "Flag (no action taken)" or remove it until escalate has a write path |
| Review queue with no proposal context | User approves 40 items they cannot evaluate | Render each proposal's `reasoning` (present in every payload) and link to the card; make "approve all" require explicit confirmation |
| Empty first-run workspace with no guidance | The exact state `help.suggest` was built for is the one the UI was never tested in | Test the guided layer from `no_workspace` forward; wizard order should follow `PRIORITY_MAP` |
| Card created in the UI does not appear in graph/wiki | Looks broken; destroys the UX verdict | Live API reads for mutable data; explicit staleness indicator + rebuild action for the projection |
| "Views refresh" surfaced as a failure | A refresh is a side effect that must never change a workflow's status (adr-0005 / D-12) | Advisory notice, never a failed operation |
| Silent partial extraction | User builds a graph on cards that stand for nothing | Show extracted character count / page coverage in the ingestion review step **before** the card is created |

## "Looks Done But Isn't" Checklist

- [ ] **HTTP adapter:** often missing *input-model validation* — verify `cap.input_model(**payload)` is constructed, and that `extra="forbid"` actually rejects an unknown field over HTTP **and** over MCP
- [ ] **HTTP adapter:** often missing *structured errors* — verify `OperationError.reason` and `.suggestion` survive to the browser
- [ ] **HTTP adapter:** often missing *Origin/Host validation* — verify a foreign `Origin` gets 403
- [ ] **Review wizard:** often missing *stale-queue detection* — verify a resume against a changed queue returns 409 and writes nothing
- [ ] **Review wizard:** often missing *double-submit protection* — verify two concurrent resumes produce exactly one set of `gate_review_*` events
- [ ] **Review wizard:** often missing *run discovery* — verify the UI can list paused runs without the user pasting an id
- [ ] **Extraction:** often missing *honest status* — verify a scanned PDF yields `extraction_status != complete` and a visible reason
- [ ] **Extraction:** often missing *hostile-input handling* — verify a zip bomb, an XXE docx, an encrypted PDF, a 0-byte file and a mislabelled type all fail cleanly with sanitized messages
- [ ] **Views contract:** often missing *the deletion of the pinning test* — verify `test_views_validate_does_not_yet_accept_generated_bytes` is gone and a non-vacuous round-trip replaces it
- [ ] **SPA:** often missing *offline/fresh-clone runnability* — verify `construct serve` renders the UI with no network and no `npm install`
- [ ] **CLI/MCP compatibility:** often missing *regression proof* — verify the full suite (531+) is green and every documented `construct …` invocation still resolves (`_KNOWN_BROKEN` empty, `_DOC_GLOBS` not narrowed)
- [ ] **Spikes:** often missing *the verdict document* — verify each of SEED-001/002/003 produced a written verdict, including any that failed
- [ ] **UX verdict:** often missing *an independent runner* — verify someone who did not build it completed the E2E path on a fresh workspace

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| UI wrote cards/connections without review | **HIGH** | Writer-side fixes have no backfill in this codebase. Identify writes by `author`/`created_by` and event timestamps in `log/events.jsonl`; revert via workspace `git` if the user kept one; then close the second write path. Prevention is the only real answer |
| Extraction stamped `complete` on empty refs | HIGH | Re-scan refs for `extraction_status: complete` with zero-length card bodies, downgrade to `partial`, re-extract from originals if they still exist. Only feasible while the PoC has few users — do it before anyone else runs it |
| Wrong proposals approved via positional drift | HIGH | Reconstruct intent from `gate_review_*` events plus checkpoint history; manually reverse promotions (`edit_card` back) and connections (`connection.remove`). Archived bodies may be unrecoverable |
| Double-resume duplicated events | LOW | Events are append-only and idempotent applies limited real damage; deduplicate in reporting and add the single-flight lock |
| SPA coded against unvalidated views bytes | MEDIUM | Fix the contract, regenerate, update the SPA's types. Cost scales with how many components read the raw shape — which is exactly why P18 goes first |
| Adapter accreted logic | MEDIUM | Extract each behaviour into a capability; the import guard turns regressions back into compile-time errors |
| Local API exposed to the network | LOW if caught pre-release | Change the bind, add Origin/Host validation and a token, rotate any LLM keys used while exposed |
| Orphaned paused runs | LOW | Add the run-list capability; expose a "discard run" path (delete the thread) with an event |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 11 — SPA on a known-broken projection | **P18** | `test_views_validate_does_not_yet_accept_generated_bytes` deleted; non-vacuous `generate → validate` round-trip green |
| 3 — `input_model` unenforced / adapter drift | **P18** (seam) + **P19** (routing) | Differential test: same `(cap_id, payload)` → identical `OperationResult` across CLI/MCP/HTTP; unknown field rejected on all three |
| 1 — second write path | **P19** (rule) + **P22** (wizards) | Guard test: API package imports only `capabilities.catalog`; no gated write capability reachable from a review endpoint |
| 4 — unconstrained `workspace` path | **P19** | `workspace: "../../etc"` → 400, no filesystem effect |
| 12 — localhost as a public surface | **P19** | Foreign `Origin` → 403; missing token → 401; no `0.0.0.0` in any script or doc |
| 16 — error-shape fork | **P19** | Same `reason`/`suggestion` strings over all three adapters for a known-failing input |
| 7 — orphaned/undiscoverable runs | **P19** (list capability) + **P22** (render) | A paused run is listable and resumable without knowing its id |
| 13 — local-first erosion | **P19** + **P21** | Import guard green; fresh-clone offline `construct serve` renders |
| 8 — extraction that succeeds with nothing | **P20** | Image-only PDF → `extraction_status != complete` + surfaced reason; `or title` branch deleted |
| 9 — hostile file input | **P20** | Hostile fixture set all fails cleanly with sanitized messages |
| 10 — uploaded bytes have no home | **P20** | Recorded decision + `validate_workspace` green on a workspace built entirely through the UI |
| 14 — two read paths / stale projection | **P21** | Create a card in the UI → it appears in every surface, or a staleness indicator is shown |
| 5 — stale gate / positional decisions | **P22** (models in P18/P19) | Resume against a changed queue → 409, zero writes; decisions keyed by `proposal_id` |
| 6 — double-resume / CLI-UI concurrency | **P22** (locking decision in P19) | Two concurrent resumes → one set of events; `database is locked` maps to an honest 409 |
| 2 — session-state gate / lying audit log | **P22** (rule in P19) | `gate_review_*` event count equals writes applied; no `append_event` call in UI/API code |
| 15 — unreachable UX verdict, PoC traps | **P23** (constrains P20–P22) | Verdict template written before UI build; E2E run on a fresh offline workspace by an independent person; three spike verdicts exist |

## Sources

**In-repository evidence (HIGH confidence — read directly during this research):**
- `src/construct/llm/curation_run.py` — HITL machine: interrupt-only `process_inbox` (`:738`), positional `_resolve_decisions` (`:777`), write-boundary apply nodes (`:818`, `:879`, `:930`), paused-state guards (`:1173`, `:1232`, `:1283`), `_validate_run_id` (`:64`), `views_refresh_hook` audit-honesty docstring (`:975`)
- `src/construct/llm/research_run.py:1036-1075` — `review_research_run`, WR-05 paused-state guard
- `src/construct/ui/gate_review.py:56, 151-169, 252-281` — session-state gate queue, audit events for unapplied decisions, direct write with hard-coded connection type
- `src/construct/ui/capability_runner.py:170-200, 285-300` — form from JSON Schema, `cap.handler(**inputs)`, explicit calling-convention admission
- `src/construct/mcp/server.py:23-46` — no input-model construction; all exceptions collapsed to `{"error": …}`
- `src/construct/capabilities/registry.py:15-65`, `capabilities/catalog.py:140-160` — `input_model` used only for schema emission; `extra="forbid"` on `CardListInput`
- `src/construct/cli.py:85-768` — mixed positional/keyword handler dispatch
- `src/construct/pipelines/ingestion.py:70-88, 115-124, 296-322` — agent-driven extraction contract, `extraction_status` derived from caller metadata, ref-id derivation
- `src/construct/services/help.py:21-29, 61-145, 193-214` — guided-layer engine and its per-domain filesystem scan
- `src/construct/views/refresh.py:1-55`, `views/generate.py:362-402` — side-effect refresh contract, `build_id` / `version.json`
- `tests/integration/test_views_generate.py:285-325` — the pinned `views validate` divergence
- `.planning/STATE.md` Blockers/Concerns — the three 2026-07-26 contract forks, T-15-12, the 15-05 per-card refresh removal, WR-01/WR-02, 16-06 "no mock search provider"
- `.planning/PROJECT.md` — constraints, out-of-scope, Key Decisions (conform data to the gate; registry as single contract ⚠️ Revisit)

**External:**
- LangGraph HITL semantics — interrupt re-execution on resume, resume values as checkpoint pending writes, `update_state` clearing pending writes, `thread_id` / `checkpoint_id` (Context7, `/langchain-ai/langgraph`) — HIGH
- pypdf text-extraction limits — scanned/image PDFs return nothing without raising, encryption handling, `strict=False`, pdfminer.six fallback (Context7, `/websites/pypdf_readthedocs_io_en_stable`) — HIGH
- FastAPI `UploadFile` — `SpooledTemporaryFile`, no built-in size cap, client-controlled `filename` / `content_type` (Context7, `/websites/fastapi_tiangolo`) — HIGH
- DNS rebinding against localhost services; CVE-2025-66414 (MCP TypeScript SDK, Dec 2025, CVSS 7.6); Origin + Host validation as the mitigation — MEDIUM (web search)
- DOCX/XML attack surface: python-docx XXE CVE-2016-5851, entity expansion, decompression bombs, `defusedxml` — MEDIUM (web search)

---
*Pitfalls research for: browser UI + local HTTP API + document ingestion over a governed local-first CLI/MCP product*
*Researched: 2026-07-26*
