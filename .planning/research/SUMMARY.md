# Project Research Summary

**Project:** CONSTRUCT — v0.5 UI-Primary Experience (Proof of Concept)
**Domain:** Browser-first HTTP/UI shell over an existing local-first governed knowledge-graph runtime (Python capability registry + LangGraph HITL workflows)
**Researched:** 2026-07-26
**Confidence:** HIGH

## Executive Summary

v0.5 is not a feature expansion of the knowledge model — every capability the browser needs already exists as one of 28 registry capabilities. The new product surface is *the experience of reaching them without a CLI*, and the milestone is judged on one question: can a person navigate CONSTRUCT unaided? All four researchers converge on the same critical path: **nothing in the browser can be built until an HTTP adapter exists**, and that adapter must be generated from the capability registry — the same auto-discovery loop `mcp/server.py` already uses — rather than hand-written per endpoint. Doing this any other way (a bespoke endpoint here, an envelope dispatcher there) re-creates the exact registry-bypass drift (RT-01/RT-02) the project has already logged and is actively trying to close.

The recommended approach layers cleanly onto the existing L0–L4 architecture: one new Layer 3 adapter (`api/`, sibling of `mcp/`, never hand-edited) plus one new Layer 4 app (the promoted React SPA, served — not rewritten). The stack cost is nearly free — `fastapi` is the only new wheel required, since `mcp`'s dependency tree already resolves `starlette`, `uvicorn`, `python-multipart`, `httpx`, and `sse-starlette`. Document extraction adds `pypdf` + `python-docx` (both pure/near-pure Python, permissively licensed), explicitly rejecting `PyMuPDF` (AGPL), `markitdown`/`unstructured`/`docling` (catastrophic install weight for a local-first tool). Checkpointed LangGraph runs (`research.run`/`curation.run`) map onto REST resources almost by renaming — `run_id` is already the LangGraph `thread_id`, `*.inspect` is already the read model, `*.review` is already the resume — so no new durable state is needed, only a thin executor and a few lifecycle gaps closed (mint `run_id` before start, a "running" status, run listing).

The key risk is not the new code but the *existing* code the new surfaces will expose to untrusted input for the first time. Pitfalls research found live defects — a Streamlit "Gate Review" screen that writes directly to `knowledge.connection.add` bypassing the reviewed workflow entirely, an `input_model` that is declared on every capability but validated by **none** of the three calling adapters, a positional (index-based) HITL decision-resume model that silently applies the wrong decision to the wrong proposal if the queue changes between render and submit, and an `ingestion.py` extraction-status heuristic that stamps "complete" from caller-supplied metadata rather than measured extraction yield — meaning a scanned PDF silently becomes a card that stands for nothing. These are not hypothetical UI risks; they are pre-existing gaps that a browser (an untrusted, drive-by-capable client, unlike the trusted-local CLI/MCP callers) turns from latent debt into exploitable/user-visible failures. Mitigating them (a `registry.invoke()` seam, workspace-id-not-path resolution, `Origin`/`Host` validation, `proposal_id`-keyed decisions with optimistic concurrency, extraction-yield-based status) is cheap and belongs early, not as polish.

## Key Findings

### Recommended Stack

Core additions: **FastAPI** (`>=0.140,<1`) as the HTTP adapter — its native Pydantic v2 object model means the existing `input_model` classes on every `CapabilityRecord` become request bodies and JSON Schemas for free, and two recent features (`app.frontend()` for SPA serving, built-in `EventSourceResponse` for SSE) remove exactly the glue this PoC would otherwise hand-write. **Plain uvicorn** (not `[standard]` — no need for uvloop/websockets machinery on a single local user). **pypdf** (BSD-3, zero deps, pure Python) and **python-docx** (MIT, only compiled dep is `lxml`) for extraction, dispatched by file extension. The existing React 19 / Vite 7 / Tailwind 4 / react-router 7 SPA is **promoted, not upgraded** — pin exact versions and commit a lockfile for the first time; do not take Vite 8 (bundler swap) or bump majors on `lucide-react`/`recharts`/`react-markdown` mid-milestone.

**Core technologies:**
- **fastapi**: HTTP adapter over the capability registry — Pydantic-native, ships SPA serving + SSE built in, the only genuinely new wheel
- **uvicorn (plain)**: ASGI server, already transitively installed via `mcp`; embedded single-worker launch via `construct serve`
- **pypdf**: PDF → text — BSD-3, zero runtime deps, safe across the project's Python 3.11–3.14 span
- **python-docx**: `.docx` → text — MIT; cannot read legacy binary `.doc` at all (see Gaps below)
- **React/Vite/Tailwind/react-router (pinned, not upgraded)**: the SPA already exists and is functionally complete for graph/chart/markdown rendering — promotion is a `git mv` + lockfile commit, not a rewrite

### Expected Features

The guided-action layer is the milestone's hidden dependency and its single highest-leverage new artifact: `help.suggest` is a **diagnosis engine, not an action engine** — it emits reason strings and scored priorities but no verb, no capability id, no destination route. Today an LLM improvises the mapping in chat; with chat demoted, something must own it, or the guided layer degrades to a status widget and the UX verdict comes back "no" for reasons unrelated to the UI itself.

**Must have (table stakes):**
- **A1** priority→action mapping (7 `PRIORITY_MAP` states → verb/route/capability, including "healthy — no action") — the milestone's hidden dependency
- **A4** loop closure — guidance re-evaluates after every mutating action, or users stop trusting it
- **B3** wizard single-commit-point — nothing written to disk until Confirm (local-first constraint: cancel must leave the filesystem exactly as it was)
- **B8** ingestion extraction preview — proves PDF ingestion actually read the file, ships together with real extraction or the wizard is theatre
- **C1/C3/C5/C6/C7** review queue: evidence visible without a click, single-key accept/reject/skip paired with in-queue undo (hard pairing — never ship one without the other), explicit apply-with-summary, durable resume via the existing sqlite checkpointer
- **D4** local/focused graph as the *default* mode, global view opt-in — external research is unanimous that global force-directed graphs degenerate past a few hundred nodes
- **D7** deep-linkable node/article URLs — low cost, unusually high fan-out (unblocks guidance CTAs, review summaries, and wiki↔graph bidirectional links)
- **E1/E2** every core loop completable without opening chat; chat only as scoped, LLM-gated modals — this is the milestone's *measurement precondition*, not a preference

**Should have (competitive):**
- **A9** deterministic, auditable guidance — "derived from your graph, not generated" is a trust claim no PKM competitor can make and it costs nothing to state
- **D14** diagnostic graph overlay rendering `curation.run`'s existing orphan/connection-health output onto the graph — nearly free given the analysis already exists, the strongest differentiator in the browse area
- **B13** dry-run-preview as a product-wide convention across every write surface — "CONSTRUCT never writes behind your back"
- **C11** bulk accept-recommended, reusing the exact rule already shipped for `daily.run` (recommended-and-not-escalate)

**Defer (v2+):**
- **B14** LLM-generated taxonomy suggestions (propose-only; needs an L3-gate-shaped pattern proven first)
- **E7** command palette (rewards experts, irrelevant to an *unaided*-navigation verdict)
- **A11** health-trend snapshots, **C13** event-log deep links, **E6** global search
- Anything requiring auth, sync, or multi-user (explicitly out of scope)

**Explicit anti-features (all four researchers converge these are actively harmful, not just low-priority):** a global always-present chat dock/sidebar (invalidates the measurement); auto-executing guided suggestions or an "accept all" default in the review queue (defeats the propose-then-approve invariant); wiki-as-landing-page and auto-generated topic/hub pages in the wiki (both violate already-locked decisions D5/D8, and the code for the D5 violation — a `workspace_landing==='wiki'` redirect — already exists and must be pinned off, not just avoided); in-place wiki editing (the views layer is a read-only derived projection; editing it is a second, ungoverned write path).

### Architecture Approach

v0.5 integrates as one new Layer 3 adapter (`api/`) plus one new Layer 4 app (the promoted SPA) and essentially nothing else — it does not redesign the L0–L4 model, the registry-as-single-contract principle, or the propose-then-approve HITL invariant. The HTTP surface is generated by looping `registry.list()` exactly as `mcp/server.py` loops `list_mcp_tools()`, so parity with CLI/MCP stays structurally free rather than a maintenance discipline. Workspaces are addressed by id, never by filesystem path, with server-side resolution against an install-root allowlist — the trust boundary a socket introduces that CLI/MCP never needed. Long-running HITL workflows (`research.run`/`curation.run`) need no new state: `run_id` **is** the LangGraph `thread_id`, so a run started in the browser is resumable from the CLI and vice versa, by construction. Two disjoint data kinds share one transport: derived/aggregate reads (cards, graph, wiki) come from the existing views JSON projection; state/decision reads (guidance, gate queues, run status) come from live capability calls — these must never be merged into a second live-parsing read path.

**Major components:**
1. **`api/server.py` + `api/capabilities.py`** — the registry-driven route generator; never hand-edited, the structural guarantee that keeps HTTP, CLI, and MCP in parity
2. **`api/runs.py` + a 1-worker `ThreadPoolExecutor`** — checkpointed LangGraph runs as addressable REST resources (start → 202 + run_id; poll `*.inspect`; resume via `*.review`)
3. **`api/workspaces.py`** — id→path resolution; the HTTP-specific trust boundary that CLI/MCP never required
4. **`pipelines/extraction.py` + `ingest.extract` capability** — a new read-only registry capability (not a UI-only pipeline function), which is what makes both CLI/MCP reachability and the ingestion wizard's review step possible
5. **`web/` (promoted SPA)** — moved, not rewritten; served by `router.frontend()` at the paths (`/data/**`, `/version.json`) the existing pages already fetch, so zero fetch-path changes are needed

### Critical Pitfalls

1. **Second write path bypassing the reviewed workflow** — already live in `ui/gate_review.py`, which calls `knowledge.connection.add` directly with a hard-coded connection type instead of going through `curation.review`'s `Command(resume=...)`. The HTTP adapter must expose **no** direct-write endpoint for anything a workflow owns; approving is only ever `POST /runs/{id}/review`.
2. **`input_model` is documentation, not enforcement** — none of the three current calling conventions (CLI positional, CLI keyword, MCP kwargs) actually validates against the declared Pydantic model; `extra="forbid"` on `CardListInput` is inert today. Adding HTTP forces this question. Fix: one `registry.invoke(cap_id, payload)` seam all three adapters route through, verified with a differential test (same `(cap_id, payload)` → identical `OperationResult` across CLI/MCP/HTTP), not just the set-membership inventory test that already exists and only appears to catch drift.
3. **Positional HITL decision-resume + stale queue = silent misapplied decisions.** `_resolve_decisions` zips decision index against proposal index; a missing decision silently falls back to *approving* the proposal's own recommendation. A browser inserts unbounded human time and a second actor (a concurrent CLI run) between render and resume where the CLI never did. Fix: `proposal_id`-keyed decisions plus an ETag/checkpoint-id optimistic-concurrency check, landing before the review wizards are built.
4. **Extraction that "succeeds" while extracting nothing.** `pypdf` returns empty text with no exception on scanned/image PDFs, and the current `ingestion.py:86-88` heuristic stamps `extraction_status: complete` from caller-supplied title/findings, not measured yield — an upload wizard deriving a title from the filename will mark every scanned or empty PDF as fully extracted, silently. Fix: derive status from measured extractor output; delete the `or title` branch; surface "no extractable text" as a first-class outcome.
5. **Localhost is a public surface.** Browsers enforce same-origin by hostname, not IP — a visited web page can rebind to `127.0.0.1` and drive the local API with no CORS warning (precedent: CVE-2025-66414 against the MCP TypeScript SDK). "Production hardening is out of scope" does not cover this: bind loopback explicitly, validate `Origin`/`Host`, and use a per-launch token — roughly 20 lines that close the drive-by case entirely.

## Implications for Roadmap

Based on combined research, the critical-path ordering is unusually well-constrained: one prerequisite (views contract), one hard gate (HTTP adapter — literally nothing in the browser can exist before it), then extraction/guidance/wizards/browse can mostly parallelize behind the gate, with review wizards needing the run-lifecycle work first and the UX verdict work needing everything else finished. All four researchers independently converge on this shape; PITFALLS.md's own phase numbering (continuing from Phase 17 as P18–P23) is adopted below as the starting structure.

### Phase 1: Data-Contract Reconciliation (views generate ↔ views validate)
**Rationale:** Named as the shared prerequisite by SEED-001 and SEED-003 already, and independently identified by ARCHITECTURE and PITFALLS as needing to go first — building browse/wiki/graph on a projection known to diverge from its own validator means building twice, or building the SPA against dead-documentation Pydantic models. The pinned regression test (`test_views_validate_does_not_yet_accept_generated_bytes`) exists specifically to force this.
**Delivers:** `views/models.py` conformed to the bytes `generate()` actually writes (not the reverse — this is the recommended direction per ARCHITECTURE), the pinning test deleted and replaced with a non-vacuous round-trip.
**Addresses:** No direct FEATURES item, but unblocks D1–D13 (all of Browse/Wiki/Graph) and both evaluation spikes that name it as a prerequisite.
**Avoids:** Pitfall 11 (SPA built on a known-broken projection).

### Phase 2: HTTP Adapter Over the Capability Registry
**Rationale:** The universal hard gate — no UI feature of any kind can exist before this. Can start in parallel with Phase 1 (no shared dependency).
**Delivers:** `api/server.py`, `api/capabilities.py` (registry-generated routes), `api/workspaces.py` (id→path trust boundary), `api/serialize.py` (structured error shape, not the `{"error": str(exc)}` MCP currently uses), `construct serve`, localhost/Origin/Host hardening, the `registry.invoke()` validation seam used by all three adapters.
**Uses:** fastapi, plain uvicorn, python-multipart (all already resolved transitively via `mcp`).
**Implements:** Architecture Pattern 1 (registry-generated routes) and Pattern 2 (workspace identity as trust boundary).
**Avoids:** Pitfalls 3 (unenforced input_model), 4 (unconstrained workspace path), 12 (localhost as public surface), 16 (three-way error-shape fork).

### Phase 3: Document Extraction Pipeline
**Rationale:** Zero dependency on the HTTP API — fully testable through the existing CLI/MCP surfaces today. Architecture and Pitfalls both flag starting this in parallel from day one as the way to de-risk the E2E demo gate before the final phase.
**Delivers:** `pipelines/extraction.py` (pdf/docx/txt/md dispatch) + new `ingest.extract` read-only registry capability; the `ingestion.py` FILE branch calls it instead of writing a blind ref.
**Uses:** pypdf, python-docx (both new pyproject deps).
**Addresses:** B7–B12 (ingest wizard table stakes) at the pipeline level.
**Avoids:** Pitfall 8 (extraction that "succeeds" on nothing — derive status from measured yield, delete the `or title` fallback), Pitfall 9 (hostile file input — defusedxml/XXE, byte caps, magic-byte sniffing not content_type), Pitfall 10 (uploaded bytes have no home in the workspace contract — must be an explicit recorded decision, not a default).

### Phase 4: SPA Promotion (move and serve, don't rewrite)
**Rationale:** Needs Phase 2 (something to serve against) and benefits from Phase 1 (a trustworthy data contract) but is otherwise a mechanical move.
**Delivers:** `git mv` of the skill-template SPA to `web/`, committed `package-lock.json`, `router.frontend()` serving with `/data/**` and `/version.json` paths preserved verbatim (zero fetch-path changes to existing pages), wheel-artifact packaging so `pip install` needs no Node at runtime.
**Uses:** React 19 / Vite 7 / Tailwind 4 / react-router 7 (pinned, not upgraded).
**Avoids:** Pitfall 13 (local-first erosion via a required build toolchain — ship prebuilt `dist/`, never require `npm install` to run the PoC).

### Phase 5: Guided Action Layer (help.suggest → the browser)
**Rationale:** Architecture explicitly recommends sequencing this as early as possible, immediately after the SPA can be served — it is the cheapest item that carries the milestone's actual success criterion, and getting the UX signal early leaves room to react to it.
**Delivers:** A1 priority→action mapping (backend vs. frontend ownership is an open question — see Gaps), A2–A8 (CTA, deep-linked launch, loop closure, evidence disclosure, empty-state, dismiss/snooze, per-domain guidance).
**Addresses:** All of FEATURES Area A table stakes; this phase alone determines whether the milestone's verdict is even answerable.
**Avoids:** The guided-layer-as-status-widget failure mode; must classify `help.py:213`'s "last research was N days ago" as informational, not a nagging call-to-action.

### Phase 6: Ingestion Wizard (upload → extract → route → review)
**Rationale:** Needs Phase 2 (upload endpoint) and Phase 3 (real extraction) — this is the demo path (upload PDF → cards → wiki + graph) and the E2E gate the whole verdict rests on.
**Delivers:** B1–B12 — step indicator, non-destructive back, single-commit-point, extraction preview, overridable routing, partial-success summary, durable job status surviving navigation.
**Uses:** New upload endpoint (multipart → `{workspace}/inbox/`), `ingest.extract`, `ingest.source`.

### Phase 7: Run Resources + the Two HITL Review Wizards
**Rationale:** Needs Phase 2 (API) and the run-lifecycle gaps closed first (mint `run_id` before start, a `RunExecutor`, a "running" status `*.inspect` cannot express today, a run-listing capability so orphaned runs are discoverable). Can proceed in parallel with Phase 6 once Phase 2 lands.
**Delivers:** `api/runs.py` REST mapping of `research.run`/`curation.run` onto addressable resources; the shared queue-of-proposals surface (C1–C10); C11 bulk-accept-recommended reusing the `daily.run` rule.
**Addresses:** FEATURES Area C in full.
**Avoids:** Pitfall 5 (positional decisions / stale-queue — `proposal_id` + ETag), Pitfall 6 (double-resume / concurrent CLI-UI resume — single-flight lock + WAL + busy_timeout), Pitfall 7 (orphaned runs — add the run-list capability), Pitfall 2 (gate queue moving into browser session state and the audit log lying — only a graph node may emit `gate_review_*` events).

### Phase 8: Live-Data Browse (Wiki + Graph)
**Rationale:** Needs Phase 1 (trustworthy contract) and Phase 4 (served SPA); can run in parallel with Phases 6–7.
**Delivers:** D1–D13 — local/focused graph as default, search, filters, orientation, deep-linkable URLs, wiki with resolving links/backlinks/its own index/visible provenance, bidirectional wiki↔graph links, empty/small-graph states.
**Avoids:** Pitfall 14 (two read paths, one stale — choose live-API reads for anything mutable in-session, views-build only for heavy derived projections; expose `build_id` so staleness is shown, not hidden).

### Phase 9: Evaluation Spikes + UX Verdict + E2E Demo Gate
**Rationale:** SEED-001 (CoPilotKit) genuinely needs the HTTP API to evaluate honestly — evaluating it before Phase 2 exists produces a guess, not a verdict. This phase also carries the actual pass/fail judgment for the milestone and must not be left implicit.
**Delivers:** Verdict documents for SEED-001/002/003 (written even on failure); the verdict template written *before* the final UI polish, not retrofitted; the mechanical E2E gate (upload PDF → cards → wiki + graph) run on a fresh, offline workspace by someone who did not build it; honest rendering of degraded workflow states and the no-op "escalate" outcome.
**Avoids:** Pitfall 15 (an unreachable UX verdict — pre-seeded demos that never exercise the empty-workspace path, degraded states rendered as success/spinners, escalate implying an action it doesn't take).

### Phase Ordering Rationale

- **Two true blockers, ordered first:** the views contract (Phase 1) and the HTTP adapter (Phase 2) are named by every researcher as prerequisites everything else depends on — Phase 2 is the harder gate since literally nothing browser-side exists without it, while Phase 1 only blocks *trusting* the browse data, not building the API.
- **Extraction (Phase 3) is deliberately front-loaded in parallel**, not sequenced after the wizard that needs it, because it is independently testable via existing CLI/MCP and de-risks the one part of the E2E demo gate most likely to surprise late (scanned/hostile PDFs).
- **Guided layer (Phase 5) is sequenced early relative to browse/wizards** on Architecture's explicit recommendation: it is cheap, and it is the requirement that actually carries the milestone's success criterion — the earlier the UX signal arrives, the more milestone is left to react to it.
- **Review wizards (Phase 7) are pushed later than ingestion (Phase 6)** because they require more foundational run-lifecycle work (run-id-before-start, an executor, a discoverable "running" state) that does not exist in any form today, whereas ingestion only needs the already-simpler upload+extract path.
- **The verdict phase (Phase 9) is last by construction**, not habit — Pitfalls found that skipping an explicit, pre-written verdict template is itself a documented failure mode ("PoC becomes v0.6's foundation by default" without ever answering its own question).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (HTTP adapter):** the localhost-hardening threat model (Origin/Host validation, per-launch token) and the `registry.invoke()` validation seam design are architecturally significant decisions with real security consequences — worth a research pass during phase planning to confirm no gap is missed for this specific registry's shape.
- **Phase 7 (Review wizards / run resources):** the ETag/optimistic-concurrency design for stale-queue detection, and the WAL/busy_timeout sqlite concurrency contract, are non-trivial LangGraph-checkpointer-specific decisions not fully worked out in this research pass.
- **Phase 9 (Evaluation spikes):** SEED-001 (CoPilotKit) and SEED-003 (open wiki format) are explicitly framed as *evaluations*, not established patterns — by definition under-researched until the spike runs.

Phases with standard patterns (skip research-phase):
- **Phase 1 (views contract fix):** the divergence and its fix are already fully diagnosed with file:line precision in ARCHITECTURE/PITFALLS; this is an implementation task, not a research question.
- **Phase 3 (extraction):** library choice, licensing rejection rationale (PyMuPDF/AGPL), and the hostile-input mitigations (defusedxml, byte caps) are already fully specified.
- **Phase 4 (SPA promotion):** a mechanical move-and-serve with the exact FastAPI primitive (`router.frontend()`) already identified.
- **Phase 5 (guided layer):** the seven-state mapping and UI patterns are fully enumerated in FEATURES.md already.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions read directly from PyPI/npm registry APIs on research date; library behavior confirmed against official FastAPI/Vite/Hatch docs via Context7; local environment introspected directly |
| Features | HIGH (internal facts) / MEDIUM (external UX patterns) | CONSTRUCT-specific facts read from source (`help.py`, `catalog.py`, routes); external wizard/review-queue/graph-view patterns corroborated across 2+ independent sources each |
| Architecture | HIGH | Integration points verified against source line-by-line; transport/library trade-off reasoning MEDIUM-HIGH (some corroborated via web search alongside Context7 docs) |
| Pitfalls | HIGH (in-repo evidence) / MEDIUM (localhost-security ecosystem claims) | Every "already in the repository" pitfall cited by file:line and independently re-verified across two research passes; CVE and DNS-rebinding claims are web-search corroborated |

**Overall confidence:** HIGH

### Gaps to Address

1. **Legacy `.doc` scope narrowing (STACK + ARCHITECTURE convergence).** PROJECT.md's milestone text says "txt, md, pdf, doc," but `python-docx` cannot read legacy binary Word 97-2003 `.doc` at all — it is a different container format, and the only real options (LibreOffice subprocess, unmaintained `antiword`, hand-rolled OLE parsing) are all wrong for a local-first PoC. **Recommendation carried forward from both researchers: support `.docx` only, detect `.doc` and reject with an explicit "convert to .docx first" error, and have this scope narrowing confirmed as a requirements decision** rather than silently assumed during planning.
2. **Who owns the priority→action mapping (A1)?** FEATURES.md surfaces this as genuinely open: a static table in the SPA is fastest, but extending `help.suggest` itself to emit a `suggested_capability`/`action` field would give CLI, MCP, and HTTP one shared contract — consistent with "the registry is the single contract" — at the cost of touching a shipped capability. FEATURES recommends the backend option if roadmap room allows; a frontend-only table is an acceptable shortcut only if explicitly labeled as such. **Needs a decision during requirements, not left implicit.**
3. **Uploaded bytes have no home in the workspace contract (PITFALLS, unresolved).** CONSTRUCT's file ingestion today routes an *existing* path; an upload has no path, and none of the three tempting answers (write into the workspace as an undefined artifact class, keep in temp with dangling provenance, keep nothing) is clearly right. This must be an explicit, recorded decision during Phase 3 planning, not defaulted into existence.
4. **Graph data source at scale (FEATURES, flagged as an open architecture question).** Whether the views JSON payload is the graph's data source or the API serves live traversal materially changes the cost of D2/D3/D4 (search, filter, local/focused default) — gates three P1 browse features and should be pinned down before Phase 8 planning.
5. **Extraction failure taxonomy (FEATURES).** B10's "name the reason and the fix" needs an actual enumerated list of failure modes (scanned PDF, encrypted PDF, unsupported `.doc` variant, empty file, mislabeled type) before error copy can be written — Phase 3 planning should produce this list against the fixture set PITFALLS specifies (image-only PDF, encrypted PDF, zero-byte file, mislabeled-type file, CJK/UTF-16 document, 200-page document).
6. **`gate_review.py`'s disposition is undecided.** All researchers note the live second-write-path defect in the Streamlit ops UI; PITFALLS explicitly states "leaving a second UI that forges gates is worse than either keeping or deleting it" — a decision (fix, fence, or delete) is needed and is not itself a v0.5 feature, but blocking it from view during v0.5 planning would be an omission.

**Defects found in existing (live) code that the roadmap must account for, not just the new build:**
- `ui/gate_review.py:252-281` — the Streamlit bridge-approve button calls `knowledge.connection.add` directly with a hard-coded connection type, bypassing the reviewed workflow's `Command(resume=...)` path entirely (Pitfall 1).
- `input_model` validation is inert across all three existing adapters (CLI, MCP, Streamlit capability-runner) — declared on every capability but enforced nowhere (Pitfall 3); the Streamlit runner even has an in-code admission that some handlers can't accept `**kwargs` from the form yet.
- The HITL resume payload is a **positional decision list** with a write-defaulting fallback: `_resolve_decisions` zips index-to-index, and a missing decision falls back to *approving* the proposal's own recommended action — a write, by default, on ambiguous input (Pitfall 5).
- `ingestion.py:86-88` — `extraction_status` is set to `complete` whenever the caller supplies *any* title or key_findings, regardless of whether text was actually extracted from the file; this predates v0.5 and will silently mislabel every scanned/empty PDF once extraction is wired into the browser upload path unless the heuristic itself is fixed (Pitfall 8).

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/fastapi_tiangolo` — `app.frontend()`/SPA fallback semantics, `UploadFile`, sync `def` threadpool offloading, SSE
- Context7 `/vitejs/vite` — `server.proxy`, `build.outDir`
- Context7 `/websites/hatch_pypa_io` — `[tool.hatch.build.targets.wheel] artifacts` for VCS-ignored build output
- Context7 `/langchain-ai/langgraph` — `Command(resume=…)`, `thread_id`/`checkpoint_id`, interrupt re-execution semantics
- Context7 `/websites/pypdf_readthedocs_io_en_stable` — scanned-PDF text-extraction limits
- PyPI JSON API + npm registry API, fetched 2026-07-26 — authoritative current versions and dependency graphs for fastapi, uvicorn, pypdf, python-docx, and the full frontend dependency set
- Local environment introspection (`.venv` importlib.metadata) — confirmed transitive ASGI stack already installed via `mcp`
- Repo source read directly: `pyproject.toml`, `capabilities/catalog.py`, `capabilities/registry.py`, `mcp/server.py`, `pipelines/ingestion.py`, `llm/curation_run.py`, `llm/research_run.py`, `services/help.py`, `ui/gate_review.py`, `ui/capability_runner.py`, `cli.py`, `views/generate.py`, `views/refresh.py`, `schemas/workspace.py`, `tests/integration/test_views_generate.py`, `.planning/PROJECT.md`, `.planning/STATE.md`

### Secondary (MEDIUM confidence)
- PatternFly Wizard guidelines + independent multi-step-form UX write-ups — wizard table stakes
- Prodigy/Label Studio/Argilla documentation and issue tracker — review-queue keyboard/undo/bulk-action patterns
- Independent Obsidian/Logseq/Roam comparisons — global force-graph degradation past a few hundred nodes
- Vite 8/Rolldown migration announcements — corroborated against npm dist-tags directly

### Tertiary (LOW confidence)
- Post-chat AI UX critiques on chat demotion rationale — opinion-heavy but directionally consistent across sources

---
*Research completed: 2026-07-26*
*Ready for roadmap: yes*
