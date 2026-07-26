# Stack Research

**Domain:** Local-first knowledge system — adding a browser-first HTTP/UI shell over an existing Python capability registry (CONSTRUCT v0.5 PoC)
**Researched:** 2026-07-26
**Confidence:** HIGH (all versions read directly from the PyPI/npm registry APIs on 2026-07-26; API behaviour confirmed against official FastAPI/Vite/Hatch docs via Context7)

> The previous milestone's stack research is preserved at `.planning/research/archive-v04/STACK.md`.

**Scope boundary:** This is a v0.5 delta only. It assumes the v0.4/v0.4.1 spine — Pydantic models, the 28-capability registry, Typer CLI, stdio MCP server, LangGraph + SqliteSaver workflows, the LLM provider factory, the vendored views library, and the Streamlit ops dashboard — and does **not** re-research or propose replacing any of it. It covers only the three genuinely-absent areas: an HTTP layer, document text extraction, and promoting the views SPA into the repo.

---

## Hard Constraint: Python Version

`pyproject.toml:10` → **`requires-python = ">=3.11"`**. No upper bound.

The working venv (`.venv/bin/python`) is **CPython 3.14.5**. Every addition below therefore has to resolve and ship wheels across **3.11 → 3.14**. That was checked per package, and it is the reason two otherwise-plausible libraries are rejected (see *What NOT to Use*).

Build backend is `hatchling>=1.25` with a custom build hook (`hatch_build.py`, stamps `_build.py`). Package manager is **uv** (`uv.lock` at repo root). Node locally is **v26.4.0 / npm 11.17.0**.

---

## The Single Most Important Finding

**The ASGI stack is already installed.** The `mcp` SDK (1.28.1) — a *core, non-optional* dependency — already pulls in every runtime piece an HTTP layer needs:

```
mcp 1.28.1
  ├── starlette>=0.48.0 (py>=3.14)   → installed: 1.3.1
  ├── uvicorn>=0.31.1                → installed: 0.51.0
  ├── python-multipart>=0.0.9        → installed: 0.0.32
  ├── httpx>=0.27.1,<1.0.0           → installed: 0.28.1
  ├── sse-starlette>=1.6.1           → installed: 3.4.5
  └── anyio>=4.5                     → installed: 4.14.2
```

Adding an HTTP API to CONSTRUCT costs **exactly one new wheel: `fastapi`**. Everything else is already in the resolved environment. This removes the usual "an HTTP layer is a heavy addition to a local-first tool" objection, and it means the API layer cannot meaningfully bloat the install.

(They should still be *declared* explicitly rather than relied on transitively — a future `mcp` release could drop `uvicorn`.)

---

## Recommended Stack

### Core Technologies (new)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **fastapi** | `>=0.140.0,<1.0` (latest 0.140.0, 2026-07-24) | HTTP adapter over the capability registry | The only new wheel required. Its native object model *is* Pydantic v2 — the `BaseModel` input classes already in `catalog.py` become request bodies and JSON Schemas with zero translation. Two features shipped in the last two months remove exactly the glue this PoC would otherwise hand-write: `app.frontend()` (0.138.0 — native SPA serving with client-side-routing fallback) and `fastapi.sse.EventSourceResponse` (0.135.0 — SSE with no extra package). Requires `python>=3.10`, `pydantic>=2.9` — both satisfied. |
| **uvicorn** | `>=0.51.0,<1.0` (latest 0.51.0) | ASGI server | Already installed via `mcp`. Use plain `uvicorn`, **not** `uvicorn[standard]` — `[standard]` drags in `uvloop`, `httptools`, `watchfiles`, `websockets` for throughput this PoC will never need. Run embedded: `uvicorn.run(app, host="127.0.0.1", port=8420)` from a Typer command, single worker. |
| **python-multipart** | `>=0.0.32` (latest 0.0.32) | `multipart/form-data` parsing — required by `UploadFile` | Already installed via `mcp`. FastAPI raises at import time if it is missing when a `File`/`UploadFile` param is declared, so declare it rather than inherit it. Apache-2.0. |
| **pypdf** | `>=6.14.2,<7` (latest 6.14.2, 2026-06-23) | PDF → text | **Zero required runtime dependencies, pure Python, BSD-3-Clause.** Nothing to compile, nothing downloaded at first use, behaves identically on 3.11–3.14. For a local-first tool that must install cleanly on a stranger's machine, that profile beats raw extraction quality. Actively released (six weeks old at research time). |
| **python-docx** | `>=1.2.0,<2` (latest 1.2.0) | `.docx` → text | MIT. Only compiled dep is `lxml` (6.1.1, ships cp314 wheels). The canonical `.docx` reader. **It cannot read legacy binary `.doc`** — see *Legacy `.doc`* below, this is a scope finding the roadmapper needs. |

### Frontend (promoting the existing SPA — pin, do not upgrade)

| Package | Pin | Notes |
|---------|-----|-------|
| `react` / `react-dom` | `19.2.8` | Latest 19.x — no change needed |
| `react-router-dom` | `7.18.1` | Latest 7.x |
| `vite` | `7.3.6` (npm dist-tag `previous`) | **Stay on 7.** Vite 8.1.5 is latest and swaps Rollup/esbuild for Rolldown — see *What NOT to Use*. Node engine `^20.19.0 \|\| >=22.12.0`; local Node 26 satisfies it. |
| `@vitejs/plugin-react` | `4.7.0` | Latest inside the `^4` range the template already declares; supports vite 4–7. (`5.2.0` supports 7‖8; `6.0.4` requires vite `^8` — do not take 6.) |
| `tailwindcss` + `@tailwindcss/vite` | `4.3.3` | Peer range `vite ^5.2 \|\| ^6 \|\| ^7 \|\| ^8` — safe either side of the Vite decision |
| `react-markdown` | `9.x` | Keep. 10.1.0 exists; a major bump in a PoC buys nothing |
| `recharts` | `2.x` | Keep. 3.10.1 exists; same reasoning |
| `lucide-react` | `0.4xx` | Keep. Upstream is now `1.27.0`; a 0.x→1.x jump renames and moves icons |
| `react-force-graph-2d` | `1.29.1` | Latest 1.x — inside the existing `^1.27.0` range |
| `d3` | `7.9.0` | Unchanged |
| `serve` | **remove** | The template's `npm run serve` static server is obsoleted by `app.frontend()` |

**Non-negotiable for promotion: commit `package-lock.json`.** Today the SPA is a *template copied per workspace* with caret ranges and no lockfile — every scaffold resolves differently over time. "First-class app in the repo" without a lockfile just relocates the drift instead of fixing it.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pdfplumber** | `0.11.10` | Layout-aware PDF extraction, tables | **Only if** pypdf's `extract_text()` proves unusable on the demo PDFs. Cost: `pdfminer.six==20260107` + `Pillow>=12.2` + `pypdfium2>=5.9` (binary wheels; all ship py3-none-platform or cp314 builds). Add as an optional extra behind the extractor interface — never the default. |
| **mammoth** | `1.12.0` | `.docx` → HTML/Markdown with structure preserved | **Only if** the ingestion wizard wants headings/lists in the seed-card body rather than flat text. BSD-2, one tiny dep (`cobble`). Better structural fidelity than `python-docx`, which makes you walk `paragraphs` *and* `tables` *and* headers by hand or silently drop text. |
| **httpx** | `0.28.1` (already installed) | Backend for Starlette/FastAPI `TestClient` | Present via `mcp` + `tavily-python`. Declare in the `dev` extra if contract tests use `TestClient`. |
| **filetype** | `1.2.0` | Pure-Python magic-byte sniffing | Only if extension dispatch proves insufficient. MIT, zero deps. For a PoC a 10-line `%PDF-` / `PK\x03\x04` prefix check is enough and adds nothing. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Dependency resolution | Already in use. `uv add fastapi pypdf python-docx && uv lock`. |
| `uvicorn --reload` | Dev API restart | `--reload` needs `watchfiles` (from `uvicorn[standard]`). Either accept manual restarts or put `watchfiles` in the `dev` extra alone. |
| `vite` dev server + proxy | Frontend HMR against the live API | Config below. Removes the need for CORS entirely. |
| `fastapi.testclient.TestClient` | Contract tests over the HTTP adapter | Mirrors the existing `tests/contract/` pattern — an HTTP analogue of `test_artifact_catalog.py` asserting every registry capability has a route. |

---

## Installation

```bash
# Python (uv — repo already has uv.lock)
uv add "fastapi>=0.140,<1" "uvicorn>=0.51,<1" "python-multipart>=0.0.32"
uv add "pypdf>=6.14.2,<7" "python-docx>=1.2.0,<2"
uv lock

# Optional, only if pypdf/python-docx text quality fails the demo
uv add --optional docs-rich "pdfplumber>=0.11.10" "mammoth>=1.12.0"

# Frontend — from the promoted app directory
npm install
npm install --save-exact vite@7.3.6 @vitejs/plugin-react@4.7.0
npm uninstall serve
git add package-lock.json
```

Suggested `pyproject.toml` shape (mirrors the existing `search` / `llm-openai` extras convention):

```toml
dependencies = [
  # ... existing ...
  "pypdf>=6.14.2,<7",        # core: extraction serves CLI/MCP ingest too, not just the UI
  "python-docx>=1.2.0,<2",
]

[project.optional-dependencies]
ui = [
  "fastapi>=0.140,<1",
  "uvicorn>=0.51,<1",
  "python-multipart>=0.0.32",
]

[tool.hatch.build.targets.wheel]
packages = ["src/construct"]
# `artifacts` is the ONLY way to get VCS-ignored build output into the wheel;
# include/exclude respect VCS ignores and will not resurrect a gitignored dist/.
artifacts = ["src/construct/webui/dist/**"]
```

**Why extraction is core but the API is an extra:** `ingest.source` is a registry capability reachable from CLI *and* MCP today. If extraction only works when `[ui]` is installed, those two surfaces silently degrade — exactly the class of surface drift v0.4.1 spent a whole milestone closing. The HTTP server is genuinely optional; text extraction is not.

---

## Integration With the Existing Capability Registry

### 1. Route generation mirrors `mcp/server.py` exactly

`mcp/server.py` is never hand-edited: it loops `registry.list_mcp_tools()` and calls `app.add_tool(...)`. The HTTP adapter should be the same shape over `registry.list()`:

```
GET  /api/capabilities            → mirrors registry.list_mcp_tools(): id, name,
                                    description, input_model.model_json_schema()
POST /api/capabilities/{cap_id}   → validate body with cap.input_model, call
                                    cap.handler(**data), serialize with the SAME
                                    _serialize_result() logic as mcp/server.py:13
```

`CapabilityRecord` (`registry.py:16`) has no `http_*` field. **Do not add one.** Every capability becomes HTTP-reachable by construction, and the existing `tests/contract/test_artifact_catalog.py` introspection guard gets a cheap sibling: assert `len(registry.list()) == len(http_routes)`.

`_serialize_result` should be **lifted out of `mcp/server.py` into a shared module** rather than copy-pasted — otherwise the two adapters drift, which is precisely the FIX-01 failure mode.

### 2. Two concrete FastAPI traps in *this* codebase

- **`from __future__ import annotations` breaks dynamically-generated typed routes.** Every module in `src/construct/` opens with it. If you write `def endpoint(payload: Model)` inside a factory closure, FastAPI's `get_type_hints()` resolves the *string* `"Model"` against module globals — where the closure local does not exist — and route registration fails. Two safe options: (a) omit the future import in the adapter module only, or (b) **recommended** — accept `payload: dict` and validate explicitly with `cap.input_model.model_validate(payload)`, serving the schema from `GET /api/capabilities` so the SPA can render forms from it. Option (b) is what MCP already does, gives schema-driven wizard forms for free, and sidesteps the problem entirely. Cost: no per-capability OpenAPI bodies — acceptable for a PoC, revisit in v0.6.
- **`Path` fields become attacker-controlled over HTTP.** `WorkspacePathInput.path`, `CardListInput.workspace`, `ViewsGenerateDataInput.install_root` are all `pathlib.Path`. Over CLI/MCP these come from a trusted local caller; over HTTP they come from a browser. The pattern already exists in-repo — `catalog.py:566` calls `install_root_error(install_root)` *before* the generator touches the filesystem. **The API should not accept raw paths at all:** expose workspaces by id, resolve id → path server-side against one configured install root, reject anything else. Design decision for the API phase, not a library choice.

### 3. Long-running capabilities and the HITL gates

`research.run` / `curation.run` block for the duration of LLM calls, then pause at a real LangGraph `interrupt()`. Recommended shape, **no new dependencies**:

- Declare invoke endpoints as **`def`, not `async def`**. FastAPI runs sync path operations in an AnyIO worker thread, so a blocking `cap.handler(...)` never stalls the event loop. This is the single most important fact for wrapping 28 synchronous handlers.
- For the long runners, return `202 {"job_id": ...}` and poll `GET /api/jobs/{id}`. Back it with a stdlib `concurrent.futures.ThreadPoolExecutor(max_workers=1)` plus a dict of job records. **The durable state already exists** — `research.inspect` / `curation.inspect` read the SQLite checkpoint and are declared read-only ("never resumes or writes"), so the job record only needs running/failed/done plus the final `OperationResult`. Pending-review state does not need re-inventing.
- **Serialize checkpoint writes.** `research_run.py:933` and `curation_run.py:292` each open `sqlite3.connect(..., check_same_thread=False)` per call. That flag disables Python's guard; it does not make concurrent writers safe. Guard invocation with a per-workspace `threading.Lock`, and set a busy timeout on the connection.
- SSE (`fastapi.sse.EventSourceResponse`, built in since 0.135.0) is available if live progress is wanted, but **polling is the right PoC choice**: trivially debuggable, survives a page reload, and matches the inspect capabilities that already exist.

### 4. Document ingestion wiring

`ingestion.py:115-124` calls `route_source_to_domain()` and derives a title from the filename — the bytes are never opened. The insert point is inside that `SourceType.FILE` branch, before `create_card`:

- New module (e.g. `src/construct/pipelines/extraction.py`) with an extension→extractor map and **deferred imports** — the convention `_views_generate_handler` already follows at `catalog.py:561` — so a missing optional extractor degrades to a clean `OperationError` rather than an ImportError traceback.
- Feed results into existing seams, not new ones: extracted text → `_seed_card_body()`'s `## Summary` section; a successful parse → `ExtractionStatus.complete` instead of the current `key_findings or title` heuristic at `ingestion.py:86-88`; `ReferenceRecord.abstract` already accepts free text (used by the NOTE branch at `ingestion.py:209`).
- Upload endpoint: `UploadFile` → write to a staging dir → call `ingest.source` with the staged path. `UploadFile` spools to disk past ~1 MB automatically, so no streaming work is needed.
- **Cap the upload size explicitly.** Neither FastAPI nor uvicorn imposes a request-body limit by default.

### 5. Legacy `.doc`

The milestone says "txt, md, pdf, doc". **`python-docx` cannot read legacy binary Word 97-2003 `.doc` at all** — a different container format entirely. The only real options are shelling out to LibreOffice (`soffice --convert-to docx`), the unmaintained `antiword`, or hand-rolling OLE parsing with `olefile`.

**Recommendation: support `.docx` only; detect `.doc` and reject with "convert to .docx first".** A subprocess dependency on an external office suite is the wrong shape for a local-first PoC, and legacy `.doc` is not on the demo path (upload a PDF → cards → wiki + graph). **Planners should read "doc" in the milestone scope as "docx" and record the narrowing explicitly.**

For `.txt` / `.md`: stdlib `path.read_text(encoding="utf-8")` with a `UnicodeDecodeError` fallback to `errors="replace"`. No dependency.

---

## SPA Promotion: Concrete Mechanics

**Layout**

```
frontend/                          # source, promoted from the skill template
  package.json, package-lock.json  # lockfile committed
  vite.config.js
  src/
src/construct/webui/
  __init__.py
  server.py                        # FastAPI app; registry-driven routes
  dist/                            # vite build output — gitignored, wheel artifact
```

**`vite.config.js`** (dev proxy — verified against Vite `server.proxy` docs):

```js
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: '../src/construct/webui/dist', emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8420', changeOrigin: false } },
  },
})
```

Same-origin in dev via the proxy → **no CORS middleware, ever**.

**Serving the build** (FastAPI ≥ 0.138.0):

```python
app.frontend("/", directory=Path(__file__).parent / "dist")
```

`fallback="auto"` is the default: `GET`/`HEAD` requests that accept HTML fall back to `index.html` (correct for `react-router-dom`), while a missing `.js`/`.css` still returns a real 404 instead of silently serving HTML. Frontend routes register as low-priority, so `/api/*` always wins. This replaces the `StaticFiles(html=True)` + custom catch-all middleware this problem historically required.

**Shipping in the wheel:** `dist/` is gitignored, and hatchling's `include`/`exclude` respect VCS ignores. The `artifacts` option is the documented escape hatch — it "includes files that are normally ignored by your VCS" and is unaffected by `exclude`. Hence `artifacts = ["src/construct/webui/dist/**"]`. Note the existing `hatch_build.py` hook already runs at wheel/sdist/editable time; if you ever want the frontend built during `hatch build`, that hook is the place — but for a PoC, building manually and committing nothing is simpler and correct.

**Entry point:** a Typer command (`construct ui serve`) that runs `uvicorn.run(app, host="127.0.0.1", port=8420)` and, when `dist/` is absent, prints "run `npm run dev` in `frontend/`" instead of 404-ing mysteriously. Typer 0.27.0 / click 8.4.2 are already installed.

**Note:** the two views JSON-emitting paths (`views generate` CLI, `views.generate_data` capability) reach the generator independently by design (D-03) and can drift. The `views generate` ↔ `views validate` byte-contract reconciliation named as this milestone's shared prerequisite needs **no new dependency** — it is a pure contract fix.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Bare Starlette 1.3.1 (already installed → *zero* new wheels) | If you truly only need ~6 hand-written endpoints. Rejected here: you would hand-write Pydantic validation, JSON-Schema exposure, SPA fallback, and SSE — all four of which FastAPI now ships. One wheel is not worth re-implementing them. |
| FastAPI | Litestar / Flask / Django | Litestar is a genuine peer (also Pydantic-native) but has a smaller ecosystem and none of it is already installed. Flask/Django are WSGI-first and would need a whole second sync/async story for blocking LangGraph calls. |
| pypdf | pdfplumber | Tables, multi-column layout, or coordinate-accurate text matter. Swappable per-format behind the extractor interface. |
| pypdf | PyMuPDF / pymupdf4llm | Best-in-class quality and speed — but AGPL-3.0. See *What NOT to Use*. |
| python-docx | mammoth | You want seed-card bodies to keep headings/lists rather than flat text. Cheap (BSD-2, one tiny dep), and arguably the better default if body structure matters to the wiki view. |
| Polling `/api/jobs/{id}` | SSE via `fastapi.sse.EventSourceResponse` | Live step-by-step progress inside a wizard becomes a UX requirement. Built in since 0.135.0 — no dependency either way, so this stays a pure design decision. |
| `fetch` + `setInterval` | TanStack Query | If job polling, cache invalidation, and refetch-on-focus start being hand-rolled in three places. Defensible, but not day-one. |
| Vite 7.3.6 | Vite 8.1.5 (Rolldown) | v0.6, as a deliberate isolated upgrade. Upstream's documented safe path is two-step — swap to `rolldown-vite` while on Vite 7 first, *then* take Vite 8 — which this PoC has no reason to spend its risk budget on. |
| `POST /api/capabilities/{id}` with dict + `model_validate` | Per-capability typed routes with real OpenAPI bodies | v0.6, once the capability surface stops moving and TS client codegen is wanted. |

---

## What NOT to Use

This is a **local-first proof of concept on a throwaway-able branch**, bound to `127.0.0.1`, single user, single process. `PROJECT.md:100` already declares production hardening out of scope. The tempting-but-wrong additions, specifically:

### Web-service reflexes that do not apply here

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `CORSMiddleware` | The Vite proxy makes dev same-origin and `app.frontend()` makes prod same-origin. There is no cross-origin request to permit. Adding it in a PoC reliably ends as `allow_origins=["*"]`, which then gets inherited by v0.6. | Nothing. Configure `server.proxy`. |
| `fastapi-users`, `python-jose`, `passlib`, `authlib`, `OAuth2PasswordBearer`, JWT | Explicitly out of scope (`PROJECT.md:100`). One user, own machine, loopback. Auth needs a user model, a session store, and a login flow — none of which the workspace format has any concept of. | Bind `127.0.0.1`. That *is* the access-control boundary. |
| `gunicorn`, `uvicorn --workers N`, `--host 0.0.0.0` | Multiple workers means multiple processes writing `.construct/workflow/*.sqlite` through independent `check_same_thread=False` connections. Corrupted or lost HITL checkpoint state — the one piece of durable state ADR-0004 sanctions *precisely because* it is not reconstructible from layer 1. | One `uvicorn.run()` worker on loopback + a per-workspace lock. |
| `slowapi`/rate limiting, `secure` headers middleware, HTTPS/TLS termination, Docker/compose, nginx, Caddy, systemd units | Hosting and hardening, explicitly out of scope. | `construct ui serve`. |
| `pydantic-settings` for API config | v0.4.1's FIX-02 deliberately produced *one* authoritative config path (`resolve_llm_config_path()`). A second settings system re-fragments what that milestone just unified. | The existing YAML config + a CLI flag for port. |
| SQLAlchemy / SQLModel / Alembic | Layer 1 is files (`cards/`, `refs/`, `connections.json`); `.construct/workflow/*.sqlite` is owned by the LangGraph checkpointer. An ORM creates a second source of truth and breaks the rebuild guarantee recorded in ADR-0004 and `workspace-contract.md`. | The existing `WorkspaceLoader` and capability handlers. |
| Celery / RQ / arq / dramatiq / Redis | Every one needs a broker daemon a local-first product cannot assume is running — for a workload of "at most one workflow at a time on one machine". | `concurrent.futures.ThreadPoolExecutor(max_workers=1)` + a dict, ~30 lines. |
| `sse-starlette` as a *declared* dependency | Built into FastAPI since 0.135.0 as `fastapi.sse.EventSourceResponse`. It is already present transitively via `mcp`, which makes accidentally coding against it easy and wrong. | `from fastapi.sse import EventSourceResponse`. |
| `httpx` as a *new* dependency | Already installed (0.28.1) via `mcp` and `tavily-python`. | Declare in `dev` only if `TestClient` is used. |
| `uvicorn[standard]` | Pulls `uvloop`, `httptools`, `watchfiles`, `websockets` — throughput machinery for one local user. | Plain `uvicorn`; add `watchfiles` to `dev` alone if `--reload` is wanted. |
| Mounting Streamlit under the API | The ops dashboard is an ops tool, not the product UI, and Streamlit runs its own Tornado server with its own lifecycle. | Leave it as a separate process. It already coexists fine (it also depends on `starlette>=0.40`). |

### Document-extraction traps

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`markitdown`** | The obvious "one library for every format" pick, and wrong here: it *hard*-depends on `magika~=0.6.1`, which depends on `onnxruntime`. That is a several-hundred-MB ML inference runtime whose job is answering "what type of file is this?" — a question the file extension already answers. Its `[all]` extra additionally pulls Azure SDKs, pandas, and `youtube-transcript-api`. Catastrophic install weight for a local-first tool. | `pypdf` + `python-docx`, dispatched on extension. |
| **`PyMuPDF` / `pymupdf4llm`** | Genuinely the best PDF text/layout extractor available, and a licensing landmine: **AGPL-3.0** or a paid Artifex commercial licence. Any distribution of CONSTRUCT linked against it inherits AGPL obligations. Not a bullet worth biting for "read the text out of a PDF". | `pypdf` (BSD-3). `pdfplumber` if quality forces an upgrade. |
| **`docling`** | Excellent document→structured-markdown converter, but a research-grade ML stack (layout + table-structure models). Ingestion here is one step in a wizard, not the product. | `pypdf`. Revisit under SEED-002 (graphify.net ingestion) if the spike says extraction quality is the bottleneck. |
| **`unstructured`** | Enormous transitive tree (nltk, model downloads), notoriously slow and fragile to install, heavily optionality-gated per format. | `pypdf` + `python-docx`. |
| **`textract`** | Effectively unmaintained, pinned to ancient transitive versions. Will not resolve cleanly on Python 3.11+, let alone the 3.14 dev venv. | Anything else. |
| **Legacy `.doc` via `antiword` or `soffice --convert-to`** | Requires an external binary the installer cannot guarantee, for a format that is not on the demo path. | Detect `.doc`, reject with "convert to .docx". Record the scope narrowing. |
| **`python-magic`** | Needs the `libmagic` system library — an OS-level install step on macOS/Windows — for MIME sniffing. | Extension dispatch; `filetype` (pure Python) or a 10-line magic-byte prefix check if that proves insufficient. |
| **OCR (`pytesseract` + tesseract)** | Requires a system binary. Scanned PDFs are a real limitation of pypdf, but solving them is a different milestone. | Surface "no extractable text; this looks like a scan" as a first-class ingestion outcome. A clear failure beats a silent empty card. |

### Frontend traps

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **CoPilotKit in the promoted app's `package.json`** | `PROJECT.md:59/97` is explicit: evaluated, **not adopted** — SEED-001 produces a verdict for v0.6. A negative verdict must not cost the whole slice. | Keep the spike in a separate throwaway directory with its own `package.json`. Never in the promoted app's manifest. |
| **Vite 8 / Rolldown in this milestone** | Latest (8.1.5, stable 2026-03-12), 10–30× faster builds, and a bundler swap. Upstream's recommended migration is two-step (`rolldown-vite` on Vite 7 first, then Vite 8). This PoC's risk budget belongs to the API and the wizards, not to build tooling. It also forces `@vitejs/plugin-react` 6.x. | `vite@7.3.6` + `@vitejs/plugin-react@4.7.0`, pinned in a committed lockfile. |
| **Bulk-upgrading the SPA's deps during promotion** | `lucide-react` 0.4xx→1.27.0, `react-markdown` 9→10, `recharts` 2→3 are all real major bumps against code that already renders. Debugging icon renames is not a UX verdict. | Pin today's resolved versions, commit the lockfile, upgrade deliberately in v0.6. |
| **Next.js / Remix / SSR / a second frontend framework** | A working React 19 + Vite + Tailwind 4 SPA already exists with graph, chart, and markdown rendering wired. SSR buys nothing for a loopback single-user app and costs a Node runtime in the shipping story. | Promote the SPA that exists. |
| **Redux / MobX** | Global state machinery for a PoC whose state is "which workspace, which wizard step, which job id". | React state + router params. (TanStack Query is a defensible *later* addition — see Alternatives.) |
| **`openapi-typescript` / `orval` client codegen** | Adds a codegen step on a branch that may be thrown away, against a capability surface that is still moving. | Fetch `GET /api/capabilities` at runtime and render schema-driven forms. |
| **`serve`** (existing devDependency) | Obsoleted by `app.frontend()`. | Remove it. |

---

## Stack Patterns by Variant

**If the demo PDFs are text-native (born-digital papers, exports):**
- `pypdf` alone. Zero extra deps; the install stays pure-Python.

**If demo PDFs are multi-column, table-heavy, or scanned:**
- Add `pdfplumber` behind the extractor interface, for PDFs only.
- Scanned/image PDFs need OCR and a system binary — treat as out of scope and fail loudly (see above).

**If the ingestion wizard needs to preview structured body content before committing:**
- Swap `python-docx` for `mammoth` (docx→HTML/Markdown) and keep `pypdf` for PDFs. Have the extractor interface return `(text, warnings)` from day one so this swap is one file.

**If the wizards need live workflow progress rather than a spinner:**
- `fastapi.sse.EventSourceResponse` + `EventSource` in the SPA. No new dependency on either side. Otherwise poll `/api/jobs/{id}` at ~1 s.

**If the API is to be pip-installable and self-contained (post-PoC):**
- Build `dist/` into `src/construct/webui/`, add the `artifacts` glob, and consider driving `npm run build` from the existing `hatch_build.py` hook. Not needed while the branch is throwaway.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `fastapi 0.140.0` | `starlette>=0.46.0` (no upper bound) | Resolves to the installed `starlette 1.3.1`. FastAPI has dropped its `<1.0.0` ceiling — Starlette 1.x is supported. Verified across fastapi 0.135–0.140 metadata. |
| `starlette` | **`>=1.0.1` required** | CVE-2026-48710 / GHSA-86qp-5c8j-p5mr ("BADHOST"): missing Host-header validation poisons `request.url.path`, bypassing path-based checks. Affects `<=1.0.0`, fixed in 1.0.1. Installed 1.3.1 is clear. Low practical impact on loopback, but do not float the floor below 1.0.1. |
| `fastapi 0.140.0` | `pydantic>=2.9.0` | Installed 2.13.4. No conflict with the repo's declared `pydantic>=2.7`, but adding FastAPI effectively raises the real floor to 2.9 — worth updating the declared constraint so it stays honest. |
| `mcp 1.28.1` | `starlette`, `uvicorn>=0.31.1`, `python-multipart>=0.0.9`, `httpx<1.0.0`, `sse-starlette`, `anyio>=4.5` | The reason the ASGI stack is already resolved. On `python>=3.14` it requires `starlette>=0.48.0` and `pydantic>=2.12.0`. |
| `pypdf 6.14.2` | Python `>=3.9`, **no required runtime deps** | Pure Python — nothing to compile on 3.14. |
| `python-docx 1.2.0` | `lxml>=3.1.0`, `typing_extensions>=4.9` | `lxml 6.1.1` ships cp314 wheels. Last upload 2025-06-16 — mature, not abandoned. |
| `pdfplumber 0.11.10` (optional) | `pdfminer.six==20260107`, `Pillow>=12.2.0`, `pypdfium2>=5.9.0` | All 3.14-compatible (`pypdfium2` uses version-agnostic `py3-none-<platform>` wheels). Note the **exact `==` pin** on `pdfminer.six` — it will constrain any other consumer. |
| `vite 7.3.6` / `8.1.5` | Node `^20.19.0 \|\| >=22.12.0` | Local Node 26.4.0 satisfies both. |
| `@vitejs/plugin-react` | `4.7.0`→vite 4–7 · `5.2.0`→vite 4–8 · `6.0.4`→vite `^8` only | Taking plugin-react 6 forces Vite 8. Don't. |
| `@tailwindcss/vite 4.3.3` | `vite ^5.2 \|\| ^6 \|\| ^7 \|\| ^8` | Safe across the Vite 7/8 decision. |
| `streamlit 1.59.2` (existing) | `starlette>=0.40.0` | The ops dashboard already coexists with the ASGI stack. Adding FastAPI creates no resolver conflict. |
| `langgraph-checkpoint-sqlite 3.1.0` | `aiosqlite>=0.20`, `langgraph-checkpoint>=4.1,<5`, `sqlite-vec>=0.1.6` | Unchanged by this milestone. Relevant only as the reason for single-worker + per-workspace lock. |

---

## Sources

- **PyPI JSON API** (`pypi.org/pypi/{pkg}/json`), fetched 2026-07-26 — authoritative current versions, `requires_python`, `requires_dist`, upload dates, wheel filenames for: fastapi 0.140.0 (+ 0.135/0.137/0.138/0.139 starlette pins), uvicorn 0.51.0, starlette 1.3.1, python-multipart 0.0.32, sse-starlette 3.4.6, pypdf 6.14.2, pdfplumber 0.11.10, pymupdf 1.28.0, python-docx 1.2.0, markitdown 0.1.6, magika 1.0.3, docling 2.115.0, mammoth 1.12.0, docx2python 3.6.2, pymupdf4llm 1.28.0, lxml 6.1.1, pillow 12.3.0, pypdfium2 5.12.1, pdfminer.six 20260107, langgraph-checkpoint-sqlite 3.1.0, charset-normalizer 3.4.9, filetype 1.2.0 — **HIGH**
- **npm registry API** (`registry.npmjs.org`), fetched 2026-07-26 — dist-tags, `engines`, `peerDependencies` for vite, @vitejs/plugin-react, @tailwindcss/vite, react, react-dom, react-router-dom, react-markdown, recharts, lucide-react, react-force-graph-2d, d3 — **HIGH**
- **Local environment introspection** (`.venv/bin/python -m importlib.metadata`) — confirmed starlette 1.3.1 / uvicorn 0.51.0 / python-multipart 0.0.32 / httpx 0.28.1 / sse-starlette 3.4.5 / anyio 4.14.2 already installed via `mcp 1.28.1`; CPython 3.14.5; Node 26.4.0 / npm 11.17.0 — **HIGH**
- **Context7 `/websites/fastapi_tiangolo`** — `app.frontend()` / `APIRouter.frontend()` signature and `fallback="auto"` SPA semantics; `UploadFile` usage; sync `def` path operations running in an external threadpool — **HIGH**
- **Context7 `/vitejs/vite`** — `server.proxy` rules and `build.outDir` / backend-integration config — **HIGH**
- **Context7 `/websites/hatch_pypa_io`** — `[tool.hatch.build.targets.wheel] artifacts` as the mechanism for including VCS-ignored build output — **HIGH**
- https://fastapi.tiangolo.com/tutorial/server-sent-events/ — `fastapi.sse.EventSourceResponse` added in FastAPI 0.135.0, no extra package required — **HIGH**
- https://github.com/advisories/GHSA-86qp-5c8j-p5mr — CVE-2026-48710 (BADHOST) affects starlette `<=1.0.0`, fixed 1.0.1 — **HIGH**
- https://vite.dev/blog/announcing-vite8 and https://vite.dev/guide/migration (via web search) — Vite 8.0 stable 2026-03-12, Rolldown as the unified bundler, recommended two-step migration path — **MEDIUM** (release facts corroborated against npm dist-tags read directly)
- https://fastapi.tiangolo.com/tutorial/frontend/ + DeepWiki/community coverage (via web search) — `app.frontend()` introduced in FastAPI 0.138.0 — **MEDIUM** (corroborated by the method existing in the 0.140.0 Context7 reference docs)
- **Repo files read directly:** `pyproject.toml`, `src/construct/capabilities/catalog.py`, `src/construct/capabilities/registry.py`, `src/construct/mcp/server.py`, `src/construct/pipelines/ingestion.py`, `hatch_build.py`, `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/{package.json,vite.config.js}`, `.planning/PROJECT.md` — **HIGH**

---
*Stack research for: local-first knowledge system — v0.5 UI-primary HTTP + document extraction + SPA promotion*
*Researched: 2026-07-26*
