# Architecture Research

**Domain:** Local-first knowledge system — adding a browser-first UI (Layer 4) over an existing Python capability runtime
**Project:** CONSTRUCT — v0.5 UI-Primary Experience (Proof of Concept)
**Researched:** 2026-07-26
**Confidence:** HIGH (integration points verified against source; transport/library choices MEDIUM-HIGH)

> **Scope note.** This document does **not** redesign CONSTRUCT. ADR-0003's L0–L4 model, the
> capability registry as the single contract, the propose-then-approve HITL invariant, and the
> workspace format are fixed inputs. Every recommendation below is about *where v0.5 attaches* to
> the system that already exists.

---

## Executive Answer

v0.5 integrates as **one new Layer 3 adapter plus one new Layer 4 app**, and almost nothing else.
The HTTP surface should be **generated from the capability registry by the same loop shape
`mcp/server.py` already uses**, so parity stays free and `api/server.py` is never hand-edited.
Long-running HITL workflows need no new state at all: `run_id` is already the LangGraph `thread_id`,
`*.inspect` is already the read model, `*.review` is already the resume — so a checkpointed run maps
onto a REST resource by renaming, not redesigning. The SPA is **promoted by moving and serving it**,
not rewriting it: if the API preserves the `/data/**` and `/version.json` URL shapes the existing
pages need zero fetch changes. Document extraction belongs in a new pipeline module fronted by a
**new read-only registry capability**, which is both what keeps it reachable from CLI/MCP and what
makes the ingestion wizard's review step possible.

The one hard gate is that **no HTTP surface exists today**. Nothing in the browser can be built
before it.

---

## Standard Architecture

### System Overview — L0–L4 with v0.5 additions

`[NEW]` = does not exist today · `[MOD]` = exists, changes · `[=]` = unchanged

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4 — Product UI (the v0.5 slice; location was "TBD" in ADR-0003)        │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ Guided     │ │ 4 Wizard   │ │ Browse /   │ │ Workspace  │ │ Upload +   │  │
│  │ actions    │ │ flows      │ │ Wiki /     │ │ switcher   │ │ extract    │  │
│  │ (help.     │ │ [NEW]      │ │ Graph      │ │ [=]        │ │ [NEW]      │  │
│  │  suggest)  │ │            │ │ [MOD]      │ │            │ │            │  │
│  │ [NEW]      │ │            │ │            │ │            │ │            │  │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘  │
│        └──────────────┴──────────────┴──────────────┴──────────────┘         │
│                    React 19 / Vite 7 / Tailwind 4 / react-router 7           │
│                    promoted from skill template → repo `web/` [MOD]          │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ HTTP (loopback only)
┌───────────────────────────────────▼──────────────────────────────────────────┐
│  LAYER 3 — Invoke surfaces (all dispatch the SAME capability registry)        │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────────┐   ┌─────────────────────────────┐   │
│  │ Typer CLI    │   │ stdio MCP server │   │ HTTP API  [NEW]             │   │
│  │ cli.py [MOD] │   │ mcp/server.py [=]│   │ api/  — generated routes,   │   │
│  │              │   │ never hand-edited│   │ run resources, SSE, uploads │   │
│  └──────┬───────┘   └────────┬─────────┘   └──────────────┬──────────────┘   │
│         └────────────────────┴────────────────────────────┘                  │
│                              ▼                                               │
│         capabilities/catalog.py — 28 CapabilityRecords   [MOD: +3]           │
│         capabilities/registry.py — the single contract    [=]                │
└───────────────────────────────────┬──────────────────────────────────────────┘
┌───────────────────────────────────▼──────────────────────────────────────────┐
│  LAYER 2 — Python pipeline runtime                                           │
│  services/ · pipelines/ · storage/ · schemas/   [=]                          │
│  pipelines/extraction.py [NEW] · pipelines/ingestion.py [MOD]                │
├──────────────────────────────────────────────────────────────────────────────┤
│  LLM GATES (cross-cutting) — llm/research_run.py, llm/curation_run.py  [MOD] │
│  LangGraph + SqliteSaver @ {ws}/.construct/workflow/*.sqlite  (adr-0004) [=]  │
├──────────────────────────────────────────────────────────────────────────────┤
│  LAYER 3b/2b — Derived views projection                                      │
│  views/generate.py · views/lib/*  [=]  ·  views/models.py  [MOD — the fix]   │
│  → {install_root}/views/build/data/*.json + version.json                     │
├──────────────────────────────────────────────────────────────────────────────┤
│  LAYER 1 — Workspace SOT (cards/ refs/ connections.json … inbox/)  [=]       │
│  LAYER 0 — Skill specs; construct-views-scaffold  [MOD → frozen]            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | v0.5 status |
|-----------|----------------|-------------|
| `capabilities/registry.py` | The single contract: id, Pydantic in/out models, callable handler | `[=]` |
| `capabilities/catalog.py` | 28 registered records + dual-mode shims | `[MOD]` +`views.validate`, +`ingest.extract`, +`workspace.list` |
| `mcp/server.py` | Auto-discovering stdio adapter; never hand-edited | `[=]` — the pattern HTTP copies |
| `api/server.py` | **[NEW]** auto-discovering HTTP adapter over the same loop | NEW |
| `api/runs.py` | **[NEW]** LangGraph runs as addressable REST resources | NEW |
| `api/workspaces.py` | **[NEW]** id→path resolution; the browser never sends a filesystem path | NEW |
| `views/generate.py` | Install-root-scoped projection writer | `[=]` |
| `views/models.py` | Contract models for the projection | `[MOD]` — the byte-contract fix lives here |
| `pipelines/ingestion.py` | Route → ref → seed card → event | `[MOD]` — calls extraction for FILE sources |
| `pipelines/extraction.py` | **[NEW]** path → text + metadata, per-format dispatch | NEW |
| `web/` | **[NEW location]** SPA source, promoted from the skill template | MOVED |

---

## Recommended Project Structure

```
construct/
├── src/construct/
│   ├── api/                      # [NEW] the third registry adapter
│   │   ├── __init__.py
│   │   ├── server.py             #   create_app(): registry loop → routes; mounts SPA
│   │   ├── capabilities.py       #   generic per-capability route generator
│   │   ├── runs.py               #   research/curation runs as resources + RunExecutor
│   │   ├── workspaces.py         #   workspace-id ↔ path resolver (the trust boundary)
│   │   ├── uploads.py            #   multipart → {workspace}/inbox/
│   │   ├── events.py             #   SSE progress channel (tails log/events.jsonl)
│   │   └── serialize.py          #   OperationResult → HTTP; error sanitisation
│   ├── web/dist/                 # [NEW] built SPA, shipped in the wheel (no Node at runtime)
│   ├── capabilities/catalog.py   # [MOD] +views.validate +ingest.extract +workspace.list
│   ├── pipelines/extraction.py   # [NEW] pdf/docx/txt/md → text
│   ├── pipelines/ingestion.py    # [MOD] FILE branch calls extraction
│   ├── views/models.py           # [MOD] conform models to the written bytes
│   ├── cli.py                    # [MOD] `construct serve`; views group → registry
│   ├── mcp/server.py             # [=]  untouched — parity stays free
│   └── ui/                       # [=]  Streamlit ops UI stays; it is not Layer 4
├── web/                          # [NEW] SPA source (git mv from the skill template)
│   ├── package.json  vite.config.js  index.html
│   └── src/{pages,components,hooks,lib}/
└── CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/
                                  # [MOD] FROZEN — kept working, no longer the source of truth
```

### Structure Rationale

- **`api/` as a sibling of `mcp/`, not inside `ui/`.** `src/construct/ui/` is the v0.3 Streamlit ops
  app (`streamlit_app.py`, `dashboard.py`, `gate_review.py`, `capability_runner.py`). It is
  explicitly *not* Layer 4 and it must keep working. Putting the HTTP API there conflates an ops tool
  with a product surface. `api/` next to `mcp/` states the truth: they are peers over one registry.
- **`web/` at repo root, built output vendored into the package.** Source outside the Python package
  (Node tooling does not belong in `src/`), artefact inside it so a `pip install` yields a working
  `construct serve` with **no Node on the user's machine**. Local-first is a product constraint; a
  runtime Node dependency violates it.
- **`views/` untouched.** The projection layer is correct; only its *models* are wrong.

---

## Architectural Patterns

### Pattern 1 — Registry-generated HTTP routes  *(the answer to Q1)*

**Recommendation: generate one typed route per capability by looping the registry. Not a single
generic envelope endpoint, and not 28 hand-written endpoints.**

**What:** `api/capabilities.py` iterates `get_registry().list()` and, for each record, registers
`POST /api/capabilities/{cap.id}` whose request-body annotation *is* `cap.input_model`. Same shape as
`mcp/server.py:27-44` — one loop, a closure per record, module never hand-edited.

```python
# api/capabilities.py — mirrors mcp/server.py's make_handler(capability=cap) closure
def mount_capabilities(router, registry, resolve_ws) -> None:
    for cap in registry.list():
        def make_route(capability=cap):
            InputModel = capability.input_model
            def route(payload: InputModel) -> dict:          # FastAPI validates + documents
                kwargs = resolve_ws(capability, payload)     # id → path; never a raw path
                return serialize(capability.handler(**kwargs))
            return route
        router.add_api_route(
            f"/capabilities/{cap.id}", make_route(),
            methods=["POST"], name=cap.id, summary=cap.name, description=cap.description,
        )
```

**Why this, and not the alternatives:**

| Shape | Drift risk | Ergonomics | Verdict |
|-------|-----------|------------|---------|
| **Generated per-capability routes** | **None** — a new capability *is* a new endpoint, the same guarantee MCP has | Typed OpenAPI per endpoint; free request validation; a TypeScript client is generatable; `/docs` becomes a live capability catalogue | **Recommended** |
| One envelope endpoint `POST /api/invoke {capability_id, input}` | None (same loop-free property) | **Poor** — OpenAPI shows one untyped `dict`; the SPA hand-rolls all 28 payload shapes; validation must be re-implemented inside the handler; errors untyped | Rejected |
| 28 hand-written endpoints | **High** — 28 places to forget; destroys the property that makes MCP parity free; re-creates RT-01/RT-02 on a new surface | Best per-endpoint control | Rejected |

The envelope form is tempting because it is ~15 lines. But it discards the one thing the
Pydantic-model-in-the-registry design was *for*: the input model already exists and is already the
validation boundary, and FastAPI consumes it directly. Paying nothing for typed docs across 28
capabilities is the whole argument.

**Two refinements that must not be skipped:**

1. **The dual-mode shim already works.** HTTP is a *keyword* caller exactly like MCP
   (`capability.handler(**kwargs)`), so every `_*_shim` in `catalog.py` binds unchanged. The shims
   that `raise TypeError` on positional args are only rejecting the CLI form. **No shim changes.**
2. **Do not copy `mcp/server.py`'s error swallow.** `mcp/server.py:36-37` returns
   `{"error": str(exc)}` — raw exception text, filesystem paths and all, with no input-model
   validation at the boundary (this is exactly the logged WR-01/WR-02 debt). HTTP gets validation
   free from FastAPI; `api/serialize.py` must map `OperationResult(success=False)` to a typed error
   body with a sanitised message, reusing the `_sanitize_error` discipline already present in
   `llm/curation_run.py:299` and `views/refresh.py:43`. Optional follow-up (not a v0.5 blocker):
   have `mcp/server.py` adopt the shared `serialize.py` and close WR-01/WR-02.

### Pattern 2 — Workspace identity as the HTTP trust boundary

**What:** the browser addresses workspaces by **id**, never by path. `api/workspaces.py` resolves
`{workspace_id}` against the server's install root using the existing
`views/lib/discover.py:discover_workspaces()`, and injects the resolved `Path` into whichever field
the capability declares (`workspace`, `workspace_path`, `workspace_root`, `install_root`).

**Why it is mandatory:** CLI and MCP are trusted-local callers; HTTP binds a socket. Today
`workspace.init` will scaffold a workspace at any path, and `views.generate_data` creates
`views/build/data/` under any `install_root` — the latter already guarded by
`views/generate.py:install_root_error()`, which is the precedent to generalise. Passing
`{"path": "../../.."}` from a `fetch` call is otherwise an arbitrary-filesystem-write primitive.

**Bonus — it fixes the server's scope for free.** `discover_workspaces` scans the *children* of the
install root (`views/lib/discover.py:16`), the SPA already ships a Landing page and a
`WorkspaceSwitcher`, and adr-0005 makes views refresh install-root scoped. **One server = one install
root = N workspaces** is the natural contract, not a server per workspace.

**Trade-off:** `workspace.init` creates a workspace that does not yet exist and so cannot resolve an
existing id. Handle it as the single declared exception: accept a *name*, kebab-validated, one path
segment, no separators, created under the install root.

### Pattern 3 — Checkpointed runs as addressable REST resources  *(the answer to Q2, part 1)*

**What:** `research.run` / `curation.run` are already resource-shaped, and this is the luckiest fact
in the whole slice. `run_id` **is** the LangGraph `thread_id` (`llm/curation_run.py:1168`), it is
kebab-validated against path traversal (`_validate_run_id`, `curation_run.py:64`), `*.inspect` is a
pure `graph.get_state()` read that never resumes (`curation_run.py:1261`), and `*.review` is
`Command(resume=decisions)` (`curation_run.py:1248`). The REST mapping is a rename:

```
POST /api/workspaces/{ws}/curation/runs                 → curation.run     → 202 {run_id, status}
GET  /api/workspaces/{ws}/curation/runs/{run_id}        → curation.inspect   (read-only)
POST /api/workspaces/{ws}/curation/runs/{run_id}/review → curation.review  {decisions|approve_all}
GET  /api/workspaces/{ws}/curation/runs/{run_id}/events → SSE progress       (additive)
```

Identical for `research`. This is the same threads-and-runs shape the LangGraph server itself uses,
which is corroboration that the modelling is idiomatic rather than invented here.

**The critical property: the HTTP surface adds no new state.** Resume is `thread_id`-addressed and
process-independent — any process that re-compiles the graph over the same
`.construct/workflow/*.sqlite` can `Command(resume=…)`. Therefore the API server may be restarted
between start and review, the browser may be refreshed mid-gate, and **a run started in the browser
is resumable from the CLI or a Claude skill, and vice versa.** That is not a workaround; it is the
adr-0004 durable-state decision paying off, and it is what keeps "don't break Claude-native
workflows" true by construction rather than by discipline.

### Pattern 4 — Start-and-poll as the spine, SSE as garnish, never WebSockets  *(the answer to Q2, part 2)*

**Recommendation: `POST` returns `202 + run_id` immediately; the browser polls the `*.inspect`
endpoint; SSE is added on top as a latency optimisation. WebSockets are rejected.**

| Transport | Fit here | Verdict |
|-----------|----------|---------|
| Synchronous request/response | `run_research_run` blocks for minutes on LLM fan-out. Declaring the route `def` lets FastAPI offload it to a threadpool, but the *client* still waits — no progress, no refresh tolerance, browser/proxy timeouts | Rejected as the only mechanism |
| **Start-and-poll over `*.inspect`** | The authoritative run state is the sqlite checkpoint, and `*.inspect` is already exactly its read model. Survives server restart and browser refresh. Zero new infrastructure | **Recommended spine** |
| **SSE (`fastapi.sse.EventSourceResponse`)** | One-way server→client, plain HTTP, browser `EventSource` reconnects automatically. FastAPI accepts a plain `def` generator and runs it in a threadpool — no async rewrite of the graph code. **A free substrate already exists:** every node calls `_emit(... "workflow_step_complete" ...)` into `log/events.jsonl`, so the stream tails the event log rather than instrumenting the graph | **Recommended addition** |
| WebSockets | Bidirectional, needs hand-rolled reconnect/heartbeat, and the client only ever pushes at two discrete moments (start, review) — both plain POSTs | **Rejected** |

Why the spine must be the checkpoint and not the stream: an SSE connection is in-memory and dies with
a tab close. If the UI's notion of "where is my run" lives in the stream, a refresh loses the gate
queue. If it lives in `*.inspect`, refresh is free — which matters more for a PoC *judged on whether
a person can navigate it unaided* than any latency win.

**Run-lifecycle gaps this exposes — all `[MOD]`, all small, all blocking the two review wizards:**

1. **Mint `run_id` before starting.** Both `ResearchRunInput` and `CurationRunInput` already accept an
   optional kebab-validated `run_id`. The API generates it, returns it in the 202, then starts work.
   Without this the POST has no handle to return.
2. **A tiny `RunExecutor`.** `ThreadPoolExecutor(max_workers=1)` plus `{run_id: future}`, so the API
   can report `running` in the window before the first checkpoint and reject a second concurrent
   start. `BackgroundTasks` is the wrong tool: it runs after the response but the client cannot
   address, poll or cancel it.
3. **Serialize runs per install root.** `_open_checkpointer` opens
   `sqlite3.connect(..., check_same_thread=False)` per call (`curation_run.py:292`); concurrent
   writers on one DB invite lock contention. `max_workers=1` is the correct PoC answer.
4. **Teach the API to say "running".** `inspect_curation_run` returns
   `status="failed" / "No such curation run."` when there are no persisted values
   (`curation_run.py:1292`) — which is *exactly what a just-started run looks like* before its first
   checkpoint lands. The executor's in-memory map supplies the missing third state; `*.inspect`
   itself need not change if the API layers it on. **This is the single most likely source of a
   confusing UI bug in the whole milestone.**

**The invariant that must not bend:** no canonical write happens before approval. In
`curation_run.py:1119-1125` the three apply nodes sit strictly downstream of `process_inbox`'s
`interrupt()`. The UI must never call `*.review` with `approve_all` on the user's behalf as a
convenience — that is the human decision, and auto-pressing it in the browser silently converts a
propose-then-approve architecture into auto-ingest.

### Pattern 5 — Two data *kinds*, one transport  *(the answer to Q3)*

**Recommendation: the API is the single transport, but two legitimate data kinds remain — and they
are disjoint, so this is not a second read path to the same data.**

| Data kind | Source | Endpoints | Why |
|-----------|--------|-----------|-----|
| **Derived / aggregate** — card lists, connections graph, wiki, stats, digests, articles, bridges | The **views JSON projection** | `GET /data/**`, `GET /version.json` (paths preserved verbatim) | `views/lib/parse_cards.py` et al. already do markdown parsing, summary-excerpt derivation and `connects_to` denormalisation, and every SPA page is written against those shapes. Re-deriving live means a second shaping layer — precisely the writer/validator divergence that already bit this project |
| **State / decision** — next-step guidance, gate queues, run status, validation reports, operation results | **Live capability calls** | `POST /api/capabilities/*`, `GET .../runs/{id}` | These must reflect the workspace *as of now*, under mutation. `help.suggest` already reads live via `WorkspaceLoader`; gate queues come from the checkpoint and are not in views at all |

**Do not** add a live `GET /api/workspaces/{ws}/cards` that re-parses markdown per request. It would
be slower *and* would create the two-shapes-for-one-thing problem the pinned test documents.

**Freshness, `version.json` polling, and adr-0005 — this gets *better*, not worse.** Today
`hooks/useVersionFlag.js` polls `/version.json` every 30 s plus on `visibilitychange`, and adr-0005
makes every workflow capability refresh views, so `version.json` churns ~3× per daily cycle. Under an
API the server *knows* when a mutation completed, because it just dispatched the capability:

- **`[MOD]` data-flow change:** every mutating capability response carries the post-mutation
  `build_id`. The SPA invalidates its `useFetch` module cache immediately instead of waiting up to
  30 s. **Poll-for-freshness becomes push-on-mutation.**
- **Keep `useVersionFlag` anyway.** It is the *only* mechanism that notices out-of-band writes — a
  `construct curation run` from the terminal, or a Claude skill mutating the same workspace. Deleting
  it would break the multi-surface story the whole architecture rests on. Demote it from primary
  freshness mechanism to background reconciliation and lengthen the interval.
- **UX consequence worth phasing:** with a build_id in the mutation response the UI can finally
  distinguish "*your* action changed this" (silently refetch) from "*something else* changed this"
  (show `UpdateFlag`). The ~3×-per-cycle churn stops being noise, which is the concern STATE.md
  flagged for re-scoring before SPA polling.

### Pattern 6 — Extraction as a registry capability, not a UI feature  *(the answer to Q5)*

**Recommendation: `pipelines/extraction.py` `[NEW]` + `ingest.extract` as a **registry capability**
`[NEW]` + a one-branch `[MOD]` in `ingestion.py`. Not buried inside `ingestion.py`; never UI-only.**

```
POST /api/workspaces/{ws}/uploads     → writes {workspace}/inbox/<safe-name>          [NEW]
POST /api/capabilities/ingest.extract   {source:"inbox/<name>"} → text + candidates   [READ-ONLY]
        ↓  user reviews what was extracted, confirms/picks a domain
POST /api/capabilities/ingest.source    {source:"inbox/<name>", title, key_findings, domain_hint}
```

**Why a separate capability rather than folding it into `ingest.source`:** the ingestion *wizard* is
`upload → extract → **review** → route → confirm`. A combined capability cannot render the review
step — the user would never see what was extracted before it became a card. Splitting extraction out
as a read-only capability is what makes the wizard possible at all. It is also the piece most likely
to be swapped (SEED-002 graphify), so it wants its own seam.

**Why the registry rather than a bare pipeline module:** the registry is what makes it reachable from
CLI (`construct ingest extract`) and MCP *for free*. A pipeline module only the API calls would be
the first HTTP-only capability and would break "the registry is the single contract" on day one.

**The seam already exists — this is genuinely additive.** `ingest_source` already accepts `title`,
`key_findings`, `content_categories`, `source_tier`, `year`, `venue`
(`pipelines/ingestion.py:48-62`) and already flips `extraction_status` to `complete` when findings or
a title are supplied (`ingestion.py:86-88`). **No input-schema change is required.** The `[MOD]` is
one branch: when `source_type == FILE` and the caller supplied nothing, call
`extraction.extract_text()` instead of writing a blind ref — which closes the "routes a file to a
domain without reading it" gap for CLI and MCP too, not just the UI.

**Upload placement is already sanctioned.** `inbox/` is in `REQUIRED_PATHS` and classified as a
**support path** (`schemas/workspace.py:24, 108-109`) — not canonical, not derived. And
`route_source_to_domain` resolves relative paths against the workspace root
(`services/knowledge.py:770-772`), so the browser sends `"inbox/<name>"` and **never a filesystem
path** — Pattern 2's trust boundary holds with zero new machinery.

**Library recommendation:**

| Format | Library | Why |
|--------|---------|-----|
| `.pdf` | **`pypdf`** | BSD, pure-Python, zero system deps, ~0.024 s/page. Occasional spacing artefacts are acceptable for seed-card summaries |
| `.docx` | **`python-docx`** | Permissive, no system deps |
| `.txt` / `.md` | stdlib | No library needed |

Behind an optional extra (`[extraction]`), matching the existing `search` / `llm-openai` pattern in
`pyproject.toml`.

- **PyMuPDF / pymupdf4llm rejected** despite better markdown output and ~10× speed: **AGPL**, a
  licensing problem for a distributed product. Revisit only under a commercial licence.
- **Docling / unstructured rejected** for v0.5: best semantic segmentation, but heavy ML-model
  installs that fight local-first and are disproportionate to a PoC.
- **⚠️ Open scope question for the roadmapper:** PROJECT.md says "txt, md, pdf, **doc**".
  `python-docx` reads `.docx` only — legacy binary `.doc` requires LibreOffice or `antiword`.
  Recommend supporting `.docx` and rejecting `.doc` with an explicit, actionable error, and
  confirming the reading of "doc" during requirements.

### Pattern 7 — Promote the SPA by moving and serving it, not rewriting it  *(the answer to Q4)*

**The key insight: if the API preserves the `/data/**` and `/version.json` URL shapes, the promoted
SPA needs *zero* fetch-path changes.** Every page fetches `/data/domains.json`,
`/data/${workspace}/cards.json`, etc. (`pages/*.jsx`), and `useVersionFlag` fetches `/version.json`.
Serve the generated build directory at those paths and the existing app runs served, unmodified.
"Promote the SPA" is a **move + serve**; the wizard and guided-action layers are purely additive.

**Serving:** FastAPI now ships a first-class primitive for exactly this —
`router.frontend(path, directory=..., fallback="auto")`. It registers the build as **low-priority**
routes, so `/api/*` and `/data/*` match first and only unmatched `GET`/`HEAD` requests that accept
HTML fall back to `index.html` (missing assets still 404). That is precisely the semantics
react-router 7 client routing needs, without a hand-rolled `StaticFiles` + catch-all.

**Build integration:**

- `git mv` the template to `web/` so history follows. Change `vite.config.js` `outDir` from
  `../build` to `../src/construct/web/dist`. Replace the `{{VERSION}}` placeholder in `package.json`
  — a template artefact that must become a real version.
- `pyproject.toml` `[MOD]`: add `src/construct/web/dist/**` to the wheel artefacts.
- **Do not run `npm run build` from the hatch build hook.** It would make `pip install -e .` require
  a Node toolchain, breaking local-first and every contributor's setup. Build in CI, or — acceptable
  and explicitly declared for a PoC on an isolated branch — commit `dist/`.
- Add `construct serve` to `cli.py` `[MOD]` (uvicorn, default bind `127.0.0.1`).

**What happens to `construct-views-scaffold` and the copies already in workspaces:**

- **Freeze the skill; do not delete it.** PROJECT.md Out of Scope: "Breaking current Claude-native
  workflows during the v0.5 UI build." The skill keeps working at its current commit; it simply stops
  being the source of truth. Mark it legacy in its `SKILL.md`. Deprecation is a **v0.6** decision to
  be taken *after* the UX verdict, not before it.
- **Existing per-workspace `views/build/` copies keep working untouched**, because the data contract
  does not change — same envelope, same paths, same `version.json`. They and the served app coexist.
- Accept the resulting duplication for one milestone. It is the price of not betting the PoC on a
  framework verdict that has not been reached yet (CoPilotKit is evaluated, not adopted).

---

## Data Flow

### Ingestion wizard — the E2E demo path (upload PDF → cards → wiki + graph)

```
Browser: drop file
    │  POST /api/workspaces/{ws}/uploads (multipart)                    [NEW]
    ▼
{workspace}/inbox/<safe-name>          ← support path, already in the scaffold
    │  POST /api/capabilities/ingest.extract {source:"inbox/<n>"}       [NEW cap, READ-ONLY]
    ▼
extraction.extract_text() → {text, title, key_findings}
    │  ── rendered for human review; user confirms/picks domain ──
    ▼
POST /api/capabilities/ingest.source {source, title, key_findings, domain_hint}
    │  ingest_source(): route → refs/{id}.json → seed card → append_event   [existing, unchanged]
    ▼
Layer 1 SOT mutated  →  API response carries the new build_id
    │                                    │
    │  (adr-0005: workflow caps refresh) │  SPA invalidates useFetch cache
    ▼                                    ▼
views/build/data/*.json + version.json   Wiki + Graph re-render on fresh /data/**
```

### HITL review flow — start → pause at gate → present queue → resume

```
POST .../curation/runs                                     ── 202 {run_id, status:"running"}
    │   RunExecutor(max_workers=1) starts run_curation_run(run_id=…)
    │   graph: load_config → integrity → decay → orphan → promotion_review
    │        → connection_maintenance → [gate_queue non-empty?] → process_inbox: interrupt()
    ▼   checkpoint persisted @ {ws}/.construct/workflow/curation-run.sqlite
GET  .../curation/runs/{run_id}       (poll; optional SSE tailing log/events.jsonl)
    │   → curation.inspect → graph.get_state() → {status:"awaiting_review", gate_queue:[…]}
    ▼
Browser renders ONE queue-of-proposals surface (promotion | connection | archive | escalate)
    │   ← research.review shares this surface; its queue is per-finding, not a tagged union
    ▼
POST .../curation/runs/{run_id}/review {decisions:[…]}
    │   → curation.review → Command(resume=decisions) on the SAME thread_id
    ▼   apply_promotions → apply_connections → apply_archives → compile_report
        → views_refresh_hook (required=False; never moves the run status)
    → 200 {status:"completed"|"degraded", build_id}
```

**Process-independence is load-bearing:** every arrow crosses a request boundary and nothing but
`run_id` is carried across. The server may restart at any arrow without losing the run.

### Key data-flow changes vs. today

1. **Reads gain a server.** The SPA moves from statically hosting one workspace's `views/build/` to
   one API server over an install root — matching how `views generate` already discovers workspaces
   as children.
2. **Freshness inverts.** Poll-driven (`version.json`, 30 s) → push-on-mutation (build_id in the
   response), with polling retained for out-of-band CLI/skill writes.
3. **Writes gain a third caller.** Layer 1 is now mutated by CLI, MCP *and* HTTP — all through the
   same registry handlers, so governance gates, event log and validation are identical by
   construction rather than by re-implementation.
4. **Extraction becomes real.** The FILE branch of `ingest_source` stops writing blind refs, on all
   three surfaces at once.

---

## Integration Points

### New vs Modified — the component list

| Component | Path | NEW/MOD | Notes |
|-----------|------|---------|-------|
| HTTP app factory | `src/construct/api/server.py` | **NEW** | `create_app()`; mounts routes, `/data`, SPA |
| Route generator | `src/construct/api/capabilities.py` | **NEW** | The registry loop; never hand-edited |
| Run resources | `src/construct/api/runs.py` | **NEW** | research/curation start · inspect · review |
| Run executor | `src/construct/api/runs.py` | **NEW** | 1-worker pool + `{run_id: future}` |
| Workspace resolver | `src/construct/api/workspaces.py` | **NEW** | id→path; the trust boundary |
| Upload endpoint | `src/construct/api/uploads.py` | **NEW** | multipart → `{ws}/inbox/` |
| SSE channel | `src/construct/api/events.py` | **NEW** | `EventSourceResponse` tailing `log/events.jsonl` |
| Result serialiser | `src/construct/api/serialize.py` | **NEW** | `OperationResult` → HTTP + sanitised errors |
| Extraction pipeline | `src/construct/pipelines/extraction.py` | **NEW** | pdf/docx/txt/md dispatch |
| `ingest.extract` capability | `src/construct/capabilities/catalog.py` | **MOD** | +1 record, read-only |
| `views.validate` capability | `src/construct/capabilities/catalog.py` | **MOD** | +1 record (closes half of RT-01/RT-02) |
| `workspace.list` capability | `src/construct/capabilities/catalog.py` | **MOD** | +1 record; the switcher needs it |
| Views contract models | `src/construct/views/models.py` | **MOD** | The byte-contract fix |
| Ingestion FILE branch | `src/construct/pipelines/ingestion.py` | **MOD** | Calls extraction when the caller supplied nothing |
| `construct serve` | `src/construct/cli.py` | **MOD** | uvicorn launcher, loopback bind |
| `views generate`/`validate` CLI | `src/construct/cli.py` | **MOD** | Route through the registry |
| Packaging | `pyproject.toml` | **MOD** | +fastapi, +uvicorn, +`[extraction]` extra, +wheel artefacts |
| SPA source | `CONSTRUCT-CLAUDE-impl/.../template/` → `web/` | **MOVED** | `git mv`; `outDir` change |
| SPA data hooks | `web/src/hooks/useFetch.js`, `useVersionFlag.js` | **MOD** | Cache invalidation on build_id; longer poll interval |
| Guided actions page | `web/src/pages/*` | **NEW** | Renders `help.suggest` |
| Wizard flows ×4 | `web/src/pages/*` | **NEW** | The two review wizards share one queue surface |
| Scaffold skill | `.../construct-views-scaffold/SKILL.md` | **MOD** | Marked frozen/legacy |
| Pinned characterisation test | `tests/integration/test_views_generate.py:285` | **DELETED** | Its own docstring instructs deletion on resolution |
| `mcp/server.py` | `src/construct/mcp/server.py` | **UNCHANGED** | Parity stays free — do not touch |
| Streamlit ops UI | `src/construct/ui/**` | **UNCHANGED** | Not Layer 4; keeps working |
| Workspace schemas / Layer 1 | `src/construct/schemas/**` | **UNCHANGED** | Product-continuity constraint |

### The 7 non-registry (RT-01/RT-02) leaves — verified and dispositioned

Confirmed by inspection of `cli.py`: `views generate` (:869), `views validate` (:929),
`spike list` (:1054), `spike run` (:1073), `tag extract` (:1148), `tag approve` (:1200),
`tag list` (:1219). Exactly 7.

**Recommendation — a rule, not a list: the registry *is* the HTTP surface. If it is not in the
registry, it is not on HTTP.** Because the adapter is generated from `registry.list()`, exclusion
costs zero code, and the pressure to migrate becomes permanent instead of a special case.

| Group | Disposition | Justification |
|-------|-------------|---------------|
| `views` | **Force through the registry** | `views.generate_data` is *already* a registry record (`catalog.py:337`); only `views validate` is genuinely missing. The byte-contract fix touches `views/models.py` and the `views validate` command anyway, so unifying here is nearly free — and it closes half of RT-01/RT-02 with the smallest blast radius while retiring adr-0005's explicit "registry holdout" note |
| `spike` | **Exclude** | `spike run --tool-path <binary>` executes an arbitrary binary. Exposing it over an unauthenticated HTTP surface is a remote-code-execution primitive. Not used by any of the four wizard flows |
| `tag` | **Exclude** | Not used by any v0.5 flow. Migrate in v0.6 with the rest of RT-01/RT-02 |

**Do not proxy.** A proxy layer is hand-written per-leaf code — i.e. it re-creates exactly the drift
the generated adapter exists to eliminate, in exchange for UI capability nobody asked for.

### The `views generate` ↔ `views validate` byte contract — recommendation

`generate()` validates an **adapted projection** (`generate.py:_FILE_MODEL_MAP` / `_PER_WS_FILES`,
lines 91-163) but writes the **raw parser dict** (`generate.py:373-384`). `views validate`
(`cli.py:929+`) applies the same models to the raw bytes with no adapter, so 3 files are rejected:
`stats.json`, `{ws}/connections.json`, `{ws}/events.json`.

| Option | Effect on the SPA | Effect on existing `views/build/` copies | Verdict |
|--------|-------------------|------------------------------------------|---------|
| **(i) Conform the models to the written bytes** — widen `views/models.py` to the raw parser shapes | **None** — the SPA is already written against these bytes | **None** — existing builds become valid | **Recommended** |
| (ii) Write the adapted projection instead | **Breaks every page** — field names differ (`source`/`target` vs `from`/`to`, `summary` vs `summary_excerpt`) | Breaks every existing build | Rejected |
| (iii) Share the generator's adapter with the validator | None | None | Acceptable fallback — but `views validate` then validates a *projection of* the file rather than the file, a weaker guarantee |

**Naming the tension honestly:** PROJECT.md's standing decision is "fix validation by conforming the
data to the gate, not weakening the gate" (ING-02). That decision is about **canonical truth**
(cards/refs), where strictness protects the knowledge model. Views is a **derived projection** whose
consumer is the SPA and whose author is the generator — there the written bytes *are* the de-facto
contract, and the models are simply describing them wrongly. Option (i) is not weakening a gate; it
is correcting a mis-transcribed spec. Record this as an explicit decision, because on its face it
looks like a reversal.

Whichever is chosen, `tests/integration/test_views_generate.py:285`
(`test_views_validate_does_not_yet_accept_generated_bytes`) **must be deleted**, as its own docstring
instructs — it turns red the moment `validate` starts passing.

### External / internal boundaries

| Boundary | Communication | Considerations |
|----------|---------------|----------------|
| Browser ↔ API | HTTP + SSE, `127.0.0.1` only | No auth by design (PROJECT.md Out of Scope). Bind loopback explicitly; never `0.0.0.0` |
| API ↔ registry | In-process `capability.handler(**kwargs)` | Identical call form to MCP; shims bind unchanged |
| API ↔ LangGraph | `run_id` = `thread_id`; sqlite checkpointer | Process-independent; one writer at a time per install root |
| API ↔ views projection | Static file reads under `views/build/data/` | Preserve `/data/**` + `/version.json` URLs verbatim |
| SPA build ↔ Python package | Vite `outDir` → `src/construct/web/dist`, shipped in the wheel | Node is a **dev** dependency only |
| CLI / MCP ↔ HTTP | No coupling — three peers over one registry | A run started on one surface is resumable on the others |

---

## Suggested Build Order

Dependency-justified. `‖` marks work that can proceed in parallel from day one.

```
        ┌───────────────────────────────────────────────┐
  P-A   │ Views byte contract (views/models.py)         │ ‖  no dependencies
        └────────────────────┬──────────────────────────┘
        ┌───────────────────────────────────────────────┐
  P-B   │ HTTP skeleton: FastAPI dep, create_app,       │ ‖  no dependencies
        │ registry route generator, workspace resolver,  │
        │ serialize.py, `construct serve`                │
        └────────────────────┬──────────────────────────┘
        ┌───────────────────────────────────────────────┐
  P-G   │ extraction.py + ingest.extract capability      │ ‖  no dependencies
        │ (testable via CLI/MCP before any UI exists)    │
        └────────────────────┬──────────────────────────┘
                             ▼ (needs P-B)
  P-C   │ SPA promoted: git mv → web/, outDir, wheel     │
        │ artefacts, router.frontend(), /data+/version   │
                             ▼
  P-E   │ Guided action layer over help.suggest          │  ← EARLIEST UX SIGNAL
                             ▼
  P-D   │ Browse / Wiki / Graph on served data           │  needs P-A + P-C
  P-F   │ Run resources + executor + 2 review wizards    │  needs P-B   (‖ with P-D)
  P-H   │ Workspace + ingestion wizards                  │  needs P-B (+ P-G for ingestion)
                             ▼
  P-S   │ SEED-001 CoPilotKit verdict                    │  needs P-B to evaluate honestly
        │ SEED-002 graphify ‖ SEED-003 open wiki format  │  no dependencies — anytime
```

### What blocks what — stated explicitly

| Item | Blocked by | Why |
|------|-----------|-----|
| **Anything in the browser** | **P-B** | There is no HTTP surface today — Typer CLI + stdio MCP only. This is the hard gate for the whole milestone |
| **Anything visual** | **P-C** | The SPA is a per-workspace skill template, not an app the project serves |
| Browse / Wiki / Graph on live data | **P-A** | Building read endpoints on a contract about to change means building twice. P-A blocks *trusting* views data, not building the API |
| Ingestion wizard | **P-G** | `ingestion.py` routes files without reading them; there is nothing to review |
| Both review wizards | **P-F** | Needs run-id-before-start, the executor, and a "running" state `*.inspect` cannot express today |
| SEED-001 (CoPilotKit) | **P-B** | CoPilotKit needs a runtime endpoint. Evaluating it before one exists produces a guess, not a verdict — SEED-001's own breadcrumbs say exactly this |
| SEED-002 / SEED-003 | nothing | The `spike run` harness already exists; SEED-003 is a projection-emission question sitting beside the views layer |

### Two ordering opinions worth acting on

1. **Put the guided action layer (P-E) as early as possible — immediately after P-C, before the
   browse views.** It is the requirement that actually carries the milestone's success criterion
   ("can a person navigate CONSTRUCT unaided?"), and it is the *cheapest* item on the list:
   `help.suggest` is already a registry capability with a real prioritisation engine
   (`services/help.py:32`), so P-E is a page plus a fetch. Getting the UX verdict signal while there
   is still milestone left to react to it is worth more than one more read-only page.
2. **Start P-G (extraction) in parallel from day one.** Zero dependency on the API, fully testable
   through the existing CLI and MCP surfaces, and it de-risks the E2E demo gate (upload PDF → cards →
   wiki + graph) that the UX verdict mechanically rests on. Discovering PDF-extraction problems in
   the final phase would be the worst possible timing.

---

## Anti-Patterns

### Anti-Pattern 1: "Just one hand-written endpoint for this UI case"

**What people do:** the generated route for some capability is awkward for the SPA, so a bespoke
endpoint is added that calls the service function directly.
**Why it's wrong:** it re-creates RT-01/RT-02 on a brand-new surface within days of opening it. The
existing 7-leaf bypass is a live, logged example of how that ages.
**Do this instead:** fix the *capability* (its input model, or a shim) so all three surfaces improve
together. If the UI needs a genuinely different shape, that is a new capability — which MCP and CLI
then get free.

### Anti-Pattern 2: A second live read path for card/graph data

**What people do:** `GET /api/workspaces/{ws}/cards` re-parses markdown per request "because it's fresher".
**Why it's wrong:** it duplicates shaping already in `views/lib/parse_cards.py` — the exact
generator-vs-validator divergence the pinned test documents, re-created at larger scale.
**Do this instead:** derived/aggregate reads come from the projection; state/decision reads come from
capabilities. Make the projection *fresher* (push-on-mutation), not duplicated.

### Anti-Pattern 3: Holding the run in server memory as the source of truth

**What people do:** the SSE stream or an in-memory dict becomes where "my run" lives.
**Why it's wrong:** a browser refresh or server restart loses the gate queue, discarding the durable
checkpointer property adr-0004 exists to guarantee.
**Do this instead:** the sqlite checkpoint is authoritative; the executor map holds only the
pre-first-checkpoint "running" flag, and SSE is a view over `log/events.jsonl`.

### Anti-Pattern 4: Accepting filesystem paths from the browser

**What people do:** the generated route passes `payload.workspace` straight through, because that is
what the input model declares.
**Why it's wrong:** `workspace.init` and `views.generate_data` create directory trees under whatever
path they are handed. CLI/MCP callers are trusted; a socket is not.
**Do this instead:** the resolver injects paths server-side from ids.
`views/generate.py:install_root_error` is the existing precedent to generalise.

### Anti-Pattern 5: Making Node a runtime dependency

**What people do:** the hatch build hook shells out to `npm run build`.
**Why it's wrong:** `pip install -e .` then requires a Node toolchain; local-first installs break.
**Do this instead:** build in CI or commit `dist/`; ship built assets in the wheel.

### Anti-Pattern 6: Copying `mcp/server.py`'s `{"error": str(exc)}`

**What people do:** the new adapter mirrors the existing one's catch-all.
**Why it's wrong:** raw exception text carries filesystem paths and provider detail; it is already
logged debt (WR-01/WR-02), not a pattern to propagate.
**Do this instead:** FastAPI validates the body from the input model; `serialize.py` maps failures to
typed, sanitised bodies. Optionally back-port to MCP and close WR-01/WR-02.

### Anti-Pattern 7: An "approve all" button the UI presses for the user

**What people do:** the review wizard auto-approves to speed up the demo.
**Why it's wrong:** the graph's whole shape — apply nodes strictly downstream of `interrupt()` —
exists so nothing is written before a *human* decision. `daily.run` may auto-apply recommended
decisions unattended precisely because it excludes `escalate`; a UI button carries no such guard.
**Do this instead:** show the queue and require a decision. `approve_all` may exist as an explicit,
consequence-labelled action — never as a default or an implicit convenience.

### Anti-Pattern 8: Deleting `useVersionFlag` once the API can push build ids

**What people do:** push-on-mutation looks strictly better, so the poller is removed.
**Why it's wrong:** it is the only mechanism that notices writes made by the CLI or a Claude skill —
the multi-surface property the entire architecture rests on.
**Do this instead:** demote it to background reconciliation with a longer interval.

---

## Scaling Considerations

Concurrent-user scaling is not the axis here — this is a local, single-user, loopback-bound PoC and
production hardening (auth, multi-user, remote hosting) is explicitly out of scope. The honest axis
is workspace and graph size.

| Scale | Architecture adjustments |
|-------|--------------------------|
| 1 install root, <5 workspaces, <500 cards | Nothing. Full views rebuild per workflow (adr-0005's accepted 3×-per-cycle cost) is imperceptible; static `/data/**` reads are instant |
| 10+ workspaces, ~5k cards | The fingerprint/incremental gate in `generate.py` already short-circuits unchanged workspaces. The graph page becomes the first pain point — `react-force-graph-2d` degrades before the data layer does. Paginate/filter client-side |
| 50k+ cards | The projection stops fitting one JSON fetch. Split `cards.json` per domain, or introduce a read index. Do **not** answer this with live parsing |

### Scaling priorities

1. **First bottleneck: force-graph rendering**, not I/O. Cap nodes and filter by domain before
   optimising anything server-side.
2. **Second bottleneck: full views-rebuild latency** on mutation, which delays the push-on-mutation
   build_id. Mitigate with the existing incremental fingerprint path before considering a partial
   generator (the per-card refresh path is already logged as a v0.6 candidate, OQ-3).

---

## Sources

- **Codebase (primary, HIGH):** `src/construct/capabilities/catalog.py`, `capabilities/registry.py`,
  `mcp/server.py`, `llm/curation_run.py`, `llm/research_run.py`, `views/generate.py`,
  `views/refresh.py`, `views/lib/discover.py`, `pipelines/ingestion.py`, `services/knowledge.py`,
  `services/help.py`, `schemas/workspace.py`, `cli.py`, `ui/capability_runner.py`,
  `tests/integration/test_views_generate.py`, the views SPA template
- **Project record (HIGH):** `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`,
  `.planning/seeds/SEED-001/002/003`,
  `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md`
- **FastAPI docs via Context7 (HIGH):** `APIRouter.frontend()` SPA serving with client-side-routing
  fallback; `fastapi.sse.EventSourceResponse` with sync and async generators; `BackgroundTasks`
  semantics; automatic threadpool offloading of `def` handlers
- **LangGraph docs via Context7 (HIGH):** `Command(resume=…)` with `thread_id`, `get_state` /
  `get_state_history`, `stream.interrupted` / `stream.interrupts`, the threads-and-runs resource model
- **Web search (MEDIUM):** PDF/DOCX extraction library comparison (pypdf / pdfplumber / PyMuPDF /
  pymupdf4llm / docling / unstructured), including licensing and install-weight trade-offs; SSE vs
  WebSockets vs polling for one-way job progress

---
*Architecture research for: browser-first UI over an existing local-first Python capability runtime*
*Researched: 2026-07-26*
