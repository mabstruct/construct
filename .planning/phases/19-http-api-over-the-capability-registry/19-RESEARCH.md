# Phase 19: HTTP API over the Capability Registry — Research

**Researched:** 2026-08-02
**Domain:** Loopback HTTP adapter over a Python capability registry; localhost trust boundary; durable workflow runs as addressable resources
**Confidence:** HIGH (every load-bearing claim was measured against this repo's live code or executed against the pinned dependency)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01: Workspace-id → path resolution lives in the seam (`registry.invoke`), not in the HTTP
  adapter and not by rewriting all 29 input models.** The seam resolves a `workspace_id` key into
  whatever path field the target capability declares, before validation. All three surfaces gain
  id-addressing from one implementation, and traversal rejection is one code path rather than a
  per-surface rule. The rejected alternative — resolving in the adapter — is exactly the shape
  Phase 18's handoff warned about ("solving it above the seam rebuilds the fork GOV-01 closed").
  Accepted cost: the seam gains capability-specific knowledge (a field-name map), so it is no longer
  a pure validate-and-dispatch. — **Reversibility:** costly.

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

- **D-03: FastAPI + uvicorn.** Pydantic v2 is already the input-model layer, so request validation,
  error shapes, and JSON-schema generation line up with what the registry already declares. Accepted
  cost: the heaviest dependency addition in a local-first tool that currently ships no web server. —
  **Reversibility:** costly.

- **D-04: `construct serve` binds `127.0.0.1` on a fixed default port (`--port` overridable) and
  prints the URL.** **Planner obligation:** a port collision must produce a clear, actionable message —
  not a traceback.

- **D-05: One envelope — `POST /api/capabilities/{id}` with a JSON payload.** Chosen over generated
  per-capability REST routes: the zero-edit guard cannot drift when there is one route; a JSON-body
  POST is not issuable by a drive-by page without CORS preflight, so `Origin`/`Host` validation
  becomes defence-in-depth; adding REST later is additive. Knowingly given up: linkable/cacheable
  data URLs and devtools legibility. — **Reversibility:** reversible — additive.

- **D-06: `GET /api/capabilities` is a discovery endpoint** returning each capability's id,
  description, and `model_json_schema()`. Closes the schema-discoverability half of GOV-01 that
  Phase 18's D-21 had to concede on MCP.

- **D-07: All 29 capabilities are exposed by default; every exclusion is written down with its
  reason in a `COVERAGE.md`.** Full coverage is asserted by the guard (cardinality, not membership).
  `spike` and `tag` are not in the registry at all, so they are out of scope by construction.

- **D-08: WR-04 is closed on both sides — `from_validation_error`'s `model` parameter becomes
  required, AND HTTP joins 18-03's differential parity test as a third column.** —
  **Reversibility:** reversible.

### Claude's Discretion

The user delegated these. A preference is recorded with each — planner and researcher have latitude
within it, but must record the outcome as a named decision.

- **Path-shaped payloads at the seam.** Preference: **id-first** — the seam accepts `workspace_id`
  and resolves it, while a raw path field still works for CLI, existing tests, and workspaces outside
  the install root; the HTTP adapter is generated so it can only ever emit `workspace_id`, guarded by
  a test. **Research should measure how many CLI call sites and tests pass a path today before this
  is locked.** → **measured, see M-1.**

- **`workspace.init` addressing.** Options: name-only with the server placing it under its own
  install root; a uniform resolve-rule where creation asserts *absence*; or excluding it from HTTP
  entirely (requires an explicit COVERAGE.md row and a rewording of criterion 1). **Settle this
  alongside the exposure policy, not separately.** → **recommendation in § Architecture Patterns,
  Pattern 3.**

- **Run execution model.** Preference: **detached subprocess** (`construct <workflow> run --run-id X`).
  Constraint: a synchronous call is **not** an option. **Planner obligation for the subprocess route:**
  stderr from a failed spawn must surface somewhere the browser can see it.

- **Run enumeration (HTTP-07).** Preference: **a new `workflow.list` registry capability**.
  **Research must confirm what the pinned `langgraph-checkpoint-sqlite` actually exposes for thread
  enumeration.** → **measured, see M-2.**

- **OQ-4 — the checkpoint concurrency contract.** Preference: **WAL + `busy_timeout` on every
  checkpointer connection, no locking.** **The ADR-0004 extension gets written whichever way this
  lands.** → **measured, see M-3 — the premise has changed.**

- **Progress reporting.** Preference: **client polls the inspect endpoint now; SSE deferred to
  Phase 21.**

- **T-18-10 / T-18-32 path-leak remediation shape.** Preference: **a sanitizer at the shared
  boundary AND a shrink-only guard** on the source sites. **Research should measure how many of the
  ~27 sites actually reach a serialized body before the split is fixed.** → **measured, see M-4.**

### Deferred Ideas (OUT OF SCOPE)

- **SSE / streaming progress** — Phase 21.
- **Per-capability REST routes** — deferred; additive over D-05's envelope.
- **The ETag's browser-side behaviour** (`If-Match`, `409 Conflict`, refreshed queue) — Phase 22.
  Phase 19 surfaces the ETag; it does not define the retry UX.
- **Serving the SPA's static files** — nominally Phase 21. If the planner picks the
  server-injected-token-in-`index.html` delivery option, the pull-forward is a decision to record.
- **API versioning** — not a concern for a single-user local PoC.
- **RT-01/RT-02 registry unification for `spike` and `tag`** — v0.6. `spike run --tool-path` is
  deliberately excluded from HTTP as an RCE primitive.
- **Fixing `tests/contract/test_artifact_catalog.py`'s own set-membership weakness (WR-01).**
- **`card list` MCP-boundary hardening (WR-01/WR-02).**
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **HTTP-01** | Start a local API server with one command; binds loopback only. | § Standard Stack (verified zero-new-transitive-dep install); Pattern 1 (`construct serve`); Pitfall 1 (uvicorn exits 3, not 1, on port collision — measured). |
| **HTTP-02** | Every registry capability reachable over HTTP without hand-written per-capability routes, guarded by a test. | Pattern 2 (single envelope; no dynamic route generation needed at all); § Don't Hand-Roll (route table from `registry.list()`, **not** `list_mcp_tools()` — measured: 6 capabilities have no `mcp_tool_name`); § Common Pitfalls 2. |
| **HTTP-03** | Callers address workspaces by id; ids resolve server-side against an install-root allowlist. | M-1 (41 call sites measured); Pattern 3 (the two-gate resolver + the three non-workspace-scoped capabilities); § Security Domain V5. |
| **HTTP-04** | HTTP errors return the same structured result shape as CLI and MCP — no third fork. | Pattern 4 (four distinct error emitters must be unified, three of them FastAPI/Starlette defaults — all measured); M-4 (path-leak site census). |
| **HTTP-05** | Reject drive-by and DNS-rebinding requests via `Origin`/`Host` validation and a per-launch token. | § Security Domain (MCP-spec-derived control set); Pattern 5; measured: `TrustedHostMiddleware` does **not** check `Origin`; a `text/plain` drive-by body already 422s. |
| **HTTP-06** | Runs are addressable — start returns an id, status is pollable, cross-surface resumable. | Pattern 6 (detached subprocess); § Reusable Assets (`inspect_*_run` already read state without resuming); M-3 (concurrency premise corrected). |
| **HTTP-07** | List runs, including paused ones. | M-2 (`SELECT DISTINCT thread_id` is the enumeration primitive); Pattern 7 (**three** durable stores, not two — `daily.run` is a JSON receipt, not a checkpoint). |
</phase_requirements>

---

## Summary

This phase is a third adapter over a registry that already has two, and the good news dominates: the
project's assumed cost centre — "the heaviest dependency addition in a local-first tool that
currently ships no web server" — **is not real**. `uvicorn 0.51.0` and `starlette 1.3.1` are already
installed in `.venv`, pulled in transitively by `mcp` and `streamlit`. FastAPI 0.141.1 declares
`starlette>=0.46.0` with no upper bound, and a `pip install --dry-run` in this venv reports
*"Would install fastapi-0.141.1"* and nothing else. D-03 costs exactly one wheel.

The genuinely hard work is not the server; it is three seams that all three surfaces share. First,
**D-01's workspace-id resolver**: 41 live `registry.invoke` call sites pass a path-shaped key today
(26 of 26 in `cli.py`, 1 in `services/help.py`, 14 of 17 in `tests/`), which decisively confirms the
id-first dual-shape preference — an id-only seam would be a 41-site rewrite inside a phase already
carrying an adapter, a run model and an error contract. Second, **HTTP-04's error shape**: FastAPI
and Starlette between them emit *four* different default error bodies (`{"detail":[…]}` at 422,
`{"detail":"Not Found"}` at 404, `PlainTextResponse("Invalid host header")` at 400 from
`TrustedHostMiddleware`, and an unhandled-exception 500), so "no third fork" requires overriding all
four, and the documented FastAPI handler pattern echoes `exc.body` — the caller's raw payload —
which is precisely the T-18-10 leak class. Third, **HTTP-05**: `TrustedHostMiddleware` was measured
and it validates `Host` only; it never reads `Origin`. Origin validation is custom middleware or it
does not exist.

Two of the phase's open questions were resolved by measurement rather than by argument. **OQ-4's
premise has changed**: `SqliteSaver.setup()` in the pinned `langgraph-checkpoint-sqlite 3.1.0`
already executes `PRAGMA journal_mode=WAL`, WAL persists in the database header, and Python's
`sqlite3.connect` already defaults to `timeout=5.0` i.e. `busy_timeout=5000`. The preferred
"WAL + busy_timeout, no locking" contract is therefore *already in force by accident* — the Phase 19
deliverable is to make it **explicit, asserted by a test, and written into ADR-0004**, plus the one
gap that is real: `SqliteSaver`'s `threading.Lock` is per-instance and gives no cross-process
guarantee. And **HTTP-07's enumeration spans three stores, not two**: `curation-run.sqlite`,
`research-run.sqlite`, and `.construct/workflow/daily/*.json` — `daily.run` persists a JSON receipt
and never pauses, so a `workflow.list` that only reads checkpoint databases will silently omit every
daily run.

**Primary recommendation:** Build the seam changes first (workspace-id resolver + required `model`
parameter + the shared error/leak boundary), gate each on the extended differential parity test, and
only then generate the adapter — which, under D-05's single envelope, is one static route plus two
middlewares and a `COVERAGE.md` cardinality guard, not a route generator.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Capability dispatch + input validation | **L2 Pipeline runtime** (`registry.invoke`) | — | GOV-01: the seam is the single contract; a surface that validates is a fork. |
| Workspace-id → path resolution (HTTP-03) | **L2 Pipeline runtime** (seam) | — | D-01, locked. Resolving in the adapter re-creates the per-surface policy GOV-01 closed. |
| Install-root scope (the allowlist boundary) | **L3 Interface** (`construct serve` launch parameter) | L2 (seam consumes it) | The install root is a *trust-boundary* property of the launched process, not of a request. `install_root` today defaults to `Path.cwd()` at CLI call time (`cli.py:967,1034`). |
| `Origin` / `Host` validation, per-launch token (HTTP-05) | **L3 Interface** (ASGI middleware) | — | Browser-protocol concerns; meaningless to CLI and stdio MCP. Must run *before* dispatch. |
| Error-shape normalisation (HTTP-04) | **L2** for the reason/suggestion strings; **L3** for status-code mapping | — | The strings are the cross-surface contract (CLI+MCP+HTTP); the HTTP status code is HTTP's own vocabulary. |
| Path-leak sanitisation (T-18-10/T-18-32) | **L2 shared serializer boundary** | L2 source sites (shrink-only) | A boundary sanitizer fixes MCP's `str(exc)` leak as a side effect; source-site fixes stop regrowth. |
| Run lifecycle (start / poll / resume) | **L2** (`*_run` / `*_review` / `*_inspect` capabilities) | L3 (process spawn + id return) | Runs are already durable capabilities; HTTP adds addressability, not execution semantics. |
| Run enumeration (HTTP-07) | **L2** (new `workflow.list` capability) | L3 (free via the envelope) | Locked preference: CLI + MCP gain listing at the same moment; a browser-only reader over durable state is the fork the phase goal forbids. |
| Durable run state | **L1/adr-0004** (`.construct/workflow/*`) | — | Per-workspace, per-workflow-type; three stores (see Pattern 7). |
| Progress rendering, wizards, ETag retry UX | **L4 SPA** — *out of scope* | — | Phases 21/22. Phase 19 must not foreclose them. |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | **0.141.1** | HTTP app, Pydantic-native request/response, exception handlers | Locked by D-03. Pydantic v2 is already the input-model layer. `[VERIFIED: PyPI — pip index versions fastapi]` |
| `uvicorn` | **0.51.0 (already installed)** | ASGI server | Already a transitive dep of `mcp` and `streamlit`. `[VERIFIED: pip show uvicorn → Required-by: mcp, streamlit]` |
| `starlette` | **1.3.1 (already installed)** | Middleware primitives (`TrustedHostMiddleware`), TestClient | Already a transitive dep of `mcp`, `sse-starlette`, `streamlit`. `[VERIFIED: pip show starlette]` |
| `pydantic` | 2.13.4 (installed) | Input models — unchanged | Already the registry's declared contract layer. |

**Installation (measured, not assumed):**

```bash
.venv/bin/python -m pip install "fastapi>=0.141,<1"
```

`pip install --dry-run "fastapi>=0.141,<1"` in this venv reports **`Would install fastapi-0.141.1`**
and marks every other requirement — `pydantic>=2.9.0`, `typing-extensions`, `typing-inspection`,
`annotated-doc`, `anyio`, `idna`, `starlette>=0.46.0` — as *already satisfied*.
`[VERIFIED: pip --dry-run in .venv]`

> **Correction to D-03's accepted cost.** The decision recorded "the heaviest dependency addition in
> a local-first tool that currently ships no web server (`pyproject.toml` has typer, pydantic, mcp,
> langgraph, streamlit — nothing HTTP)". The *declared* dependencies contain nothing HTTP, but the
> *installed* environment already contains a full ASGI stack. The real addition is one pure-Python
> wheel with zero new transitive dependencies. This strengthens D-03; it does not reopen it.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx2` | 2.9.1 | Test client transport for `starlette.testclient.TestClient` | **Recommended dev dependency.** Starlette 1.3.1's `testclient` prefers `httpx2` and falls back to `httpx` with a `StarletteDeprecationWarning`. `httpx` 0.28.1 is installed, so tests work today — but on a deprecation path. `[VERIFIED: starlette/testclient.py:30-50]` |
| `secrets` (stdlib) | — | Per-launch token generation | Already the project's idiom (`_new_run_id` uses `secrets.token_hex(3)`). Never `random`. |
| `socket` (stdlib) | — | Pre-flight port availability probe | Owns the port-collision message instead of inheriting uvicorn's `SystemExit(3)`. See Pitfall 1. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Bare Starlette (already installed → literally zero new deps) | Would hand-roll body parsing, validation-error mapping, and `model_json_schema()` exposure for D-06. D-03 is locked and the measured FastAPI cost is one wheel, so this is not worth reopening. |
| `TrustedHostMiddleware` | Hand-written Host check | Do not. It is 40 lines of audited stdlib-adjacent code. But it is **insufficient alone** — see Pattern 5. |
| `starlette.testclient.TestClient` | `httpx.ASGITransport` + `anyio` | ASGITransport avoids the `httpx2` deprecation entirely and needs no new dep, at the cost of async test bodies. Viable fallback if the planner does not want a new dev dep. |

---

## Package Legitimacy Audit

| Package | Registry | Latest release | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `fastapi` | PyPI | 2026-07-29 (0.141.1) | not reported by API | `github.com/fastapi/fastapi` | `SUS` → **cleared** | Approved |
| `uvicorn` | PyPI | 2026-08-01 (0.51.0) | not reported by API | `github.com/Kludex/uvicorn` | `SUS` → **cleared** | Approved (already installed) |
| `httpx2` | PyPI | 2026-07-24 (2.9.1) | not reported by API | `github.com/pydantic/httpx2` | `SUS` → **cleared** | Approved (optional dev dep) |

**Why all three cleared.** The seam's `SUS` verdicts are driven by two signals — `too-new` and
`unknown-downloads`. `too-new` is computed from the **latest release date**, not package age, so
every actively maintained package trips it; and the PyPI JSON API does not expose download counts,
so `unknown-downloads` fires universally for this ecosystem. Both are false positives here, cleared
by independent verification:

- `fastapi` — canonical repo `fastapi/fastapi`, and it is the package Context7's `/websites/fastapi_tiangolo`
  documents. Already the framework named in the locked decision D-03. `[VERIFIED: PyPI + Context7]`
- `uvicorn` — **already installed in this venv** as a dependency of `mcp` and `streamlit`. The repo
  moved from `encode/uvicorn` to `Kludex/uvicorn` (Marcelo Trylesinski is the maintainer);
  corroborated by Context7 resolving Uvicorn to `/kludex/uvicorn` with High source reputation.
  `[VERIFIED: pip show uvicorn + Context7]`
- `httpx2` — maintained by **Pydantic Services Inc.** as the declared continuation of `httpx`
  (which has had no release since 2024). Starlette 1.x's own `testclient` imports `httpx2` by
  preference, which is how it surfaced here at all. `[CITED: pypi.org/project/httpx2/, github.com/pydantic/httpx2]`

**Packages removed due to `SLOP` verdict:** none.
**Packages flagged as suspicious `[SUS]` after review:** none — all three cleared with named
authoritative sources. No `checkpoint:human-verify` task is required for these installs.

No `postinstall`-equivalent hooks: all three ship as pure-Python wheels (`py3-none-any`), so no
build-time script executes. `[VERIFIED: wheel filename fastapi-0.141.1-py3-none-any.whl]`

---

## Measured Findings

> CONTEXT.md named four measurements as prerequisites for locking discretion items. All four were
> executed against this repo and the pinned dependencies. These are the highest-value outputs of
> this research pass.

### M-1 — Path-shaped payloads at the seam: **41 live call sites**

Method: AST scan for `*.invoke("<cap.id>", <dict>)` where the payload dict (literal or a
locally-assigned `payload` variable) contains any of `workspace_path`, `workspace`, `install_root`,
`root`, `path`.

| Location | `registry.invoke` sites | Passing a path-shaped key |
|---|---|---|
| `src/construct/cli.py` | 26 | **26** (100%) |
| `src/construct/services/help.py` | 1 | **1** |
| `src/construct/ui/capability_runner.py` | 0 (payload built dynamically from `model_json_schema()`) | n/a — passes whatever the form yields, including path fields |
| `tests/**` | 17 | **14** |
| **Total** | 44 | **41** |

**Verdict: the id-first dual-shape preference is confirmed by the numbers.** An id-only seam is a
41-site rewrite plus the Streamlit runner's dynamic form, inside a phase already carrying an
adapter, a seam change, a run model, and an error contract. Keep the raw path field working; make
the HTTP adapter structurally incapable of emitting one.

**Planner obligation that follows:** the two payload shapes must both appear in the parity table
(D-08's third column), and the "HTTP can only ever emit `workspace_id`" claim needs its own guard —
a test asserting no HTTP-constructed payload ever carries a key in the path-shaped set.
`[VERIFIED: AST scan, this session]`

### M-2 — What `langgraph-checkpoint-sqlite 3.1.0` exposes for thread enumeration

`SqliteSaver.list(config, *, filter, before, limit)` accepts **`config=None`**, and
`search_where(None, …)` emits no `thread_id` predicate — so `list(None)` does enumerate across every
thread. Executed successfully against a real database. **But** it is the wrong primitive for a
listing endpoint: it yields one `CheckpointTuple` *per checkpoint* (not per thread), deserializes
every checkpoint blob and every pending write through `self.serde`, and orders globally by
`checkpoint_id DESC` with no grouping.

The cheap enumeration is a direct query against the schema `setup()` creates:

```sql
SELECT DISTINCT thread_id FROM checkpoints;
```

Verified to execute against a `SqliteSaver`-created database. Per-run status then comes from the
**existing** read-only primitives — `inspect_curation_run` / `inspect_research_run` already
reconstruct status (including `awaiting_review` with the pending `gate_queue`) via
`graph.get_state` without resuming. `[VERIFIED: inspect.getsource + live execution against langgraph-checkpoint-sqlite 3.1.0]`

Other newly-available methods on the pinned version, none of which this phase needs but which the
planner should know exist rather than reimplement: `delete_thread`, `copy_thread`,
`get_delta_channel_history`, `prune`, `delete_for_runs`, `with_allowlist`.

### M-3 — OQ-4: **the premise has changed — WAL and `busy_timeout` are already in force**

| Claim in CONTEXT.md | Measured reality |
|---|---|
| "`_open_checkpointer:494-508` … **no WAL**" | **False.** `SqliteSaver.setup()` executes `PRAGMA journal_mode=WAL` as the first statement of its `executescript`. Measured `journal_mode` after setup: `wal`. WAL is persisted in the database file header, so a *fresh connection to the same file also reports* `wal` — measured. `-wal` and `-shm` sidecar files are created. |
| "… **no `busy_timeout`**" | **False.** Python's `sqlite3.connect()` defaults to `timeout=5.0`, which sets `PRAGMA busy_timeout=5000`. Measured on both the checkpointer's connection and a fresh one: `5000`. `sqlite3.connect(db, timeout=30.0)` yields `30000`. |
| implied: concurrency is unguarded | **Partly true, and this is the real gap.** `SqliteSaver.__init__` holds `self.lock = threading.Lock()` and every `cursor()` acquires it. That serializes writers **within one process only**. Two processes (a browser-spawned run and a CLI resume) share no lock at all. |

Environment: `sqlite3.sqlite_version = 3.53.2`, `sqlite3.threadsafety = 3` (serialized), Python 3.14.5.
`[VERIFIED: live execution, this session]`

**What this means for the phase.** The locked preference ("WAL + `busy_timeout`, no locking") is
*already the de facto contract* — by library default and stdlib default, not by decision. That is
the worst possible state for a contract: correct today, silently reversible by a dependency bump.
The Phase 19 deliverable is therefore not to *implement* WAL/`busy_timeout` but to:

1. Set both **explicitly** in `_open_checkpointer` (both copies — `curation_run.py:494-508` and
   `research_run.py:1034-1048`) rather than inheriting them.
2. Add a test asserting `PRAGMA journal_mode` is `wal` and `PRAGMA busy_timeout` is the chosen value
   on a checkpointer connection — this is exactly the "silent success is this codebase's named
   default failure mode" countermeasure the project already applies elsewhere.
3. Write the ADR-0004 extension recording that mutual exclusion across processes is **not**
   provided, and that two racing resumes are arbitrated by D-11's checkpoint-id ETag (the loser
   rejects with zero writes) — the limitation must be written down, not implied away.
4. Note explicitly that a 5-second `busy_timeout` may be too short for a curation resume that writes
   many cards; choose a value deliberately.

### M-4 — Path-leak site census: **43 `str(exc)` sites, 14 of them demonstrably path-leaking**

Method: AST classification of every `except` handler whose body contains `str(<the bound exception>)`,
grouped by the exception type(s) caught. `str(OSError)` was confirmed to embed the absolute path
(`"[Errno 2] No such file or directory: '/Users/.../file.md'"`), and `str(pydantic.ValidationError)`
was confirmed to embed `input_value=` — i.e. the caller's submitted payload.

| File | `str(exc)` handlers | Catching OSError-family (**demonstrable path leak**) | Catching domain/pydantic errors |
|---|---|---|---|
| `services/knowledge.py` | 26 | **13** — 9 × `OSError`, 2 × `FileNotFoundError`, 2 × tuples including `OSError` | 13 (`WorkspaceLoadError` ×5, `ArtifactValidationError/PydanticValidationError/ValueError` ×6, `PydanticValidationError/ValueError` ×2) |
| `services/validation.py` | 16 | **0** | 16 (`WorkspaceLoadError` ×7, `ValidationError` ×6, `SchemaParseError/ValidationError` ×2, ×1 other) |
| `mcp/server.py` | 1 | **1** — bare `except Exception` | 0 |
| **Total** | **43** | **14** | 29 |

All 26 `knowledge.py` sites write into `OperationResult.message` or `OperationError.reason`, and
`mcp/server.py:_serialize_result` `asdict`s the whole dataclass — so **every one of them reaches a
serialized body.** The `validation.py` sites reach `ValidateOutput.report`, also serialized.

Two behaviours were probed live and did **not** leak (`knowledge.connection.list` on a corrupt
`connections.json`, `knowledge.connection.add` on a non-workspace) because those paths raise domain
errors with hand-written relative-path messages. That is the useful distinction: **the leak is not
uniform, it is concentrated in the 14 OSError-family handlers plus the MCP catch-all.**

Separately confirmed: `pipelines/graph_status.py:66` writes `"workspace": str(root.resolve())` into
`OperationResult.data` on the **success** path — an absolute path in a serialized body with no
exception involved at all (T-18-32). A boundary *exception* sanitizer will not catch it.

**Verdict on the split.** Land the boundary sanitizer (it closes `mcp/server.py`'s catch-all and
every `knowledge.py`/`validation.py` message in one change), and set the shrink-only baseline at
**14 entries** — the 13 OSError-family handlers in `knowledge.py` plus `mcp/server.py`'s bare
`except Exception` — not at 27 or 43. The 29 domain-error handlers are a different, lower-risk
class and belong in the baseline's documented rationale, not in its shrink target. `graph_status.py:66`
is a **third, separate item**: a success-path data leak requiring its own fix, and it must not be
folded into an exception-sanitizer task where it will be quietly missed.
`[VERIFIED: AST scan + live probes, this session]`

---

## Architecture Patterns

### System Architecture Diagram

```
 ┌──────────┐        ┌──────────┐        ┌───────────────────────────────┐
 │ Terminal │        │  Claude  │        │  Browser (Phases 21–24)       │
 │  (CLI)   │        │  (MCP)   │        │  fetch(POST, JSON, +token)    │
 └────┬─────┘        └────┬─────┘        └───────────────┬───────────────┘
      │ typer cmd         │ stdio                        │ HTTP/1.1 → 127.0.0.1:<port>
      │                   │                              ▼
      │                   │            ╔═══════════ TRUST BOUNDARY ═══════════╗
      │                   │            ║ ① TrustedHostMiddleware              ║
      │                   │            ║    Host ∈ {127.0.0.1, localhost}     ║
      │                   │            ║    else → 400, request ends          ║
      │                   │            ║ ② OriginGuard (CUSTOM — not provided)║
      │                   │            ║    Origin absent OR ∈ allowed        ║
      │                   │            ║    else → 403 (MCP-spec status)      ║
      │                   │            ║ ③ TokenGuard: X-Construct-Token      ║
      │                   │            ║    constant-time compare, else 401   ║
      │                   │            ╚══════════════════╤═══════════════════╝
      │                   │                               ▼
      │                   │            ┌──────────────────────────────────────┐
      │                   │            │ POST /api/capabilities/{cap_id}      │  ← ONE route,
      │                   │            │ GET  /api/capabilities  (D-06 schemas)│    all 29 caps
      │                   │            └──────────────────┬───────────────────┘
      │                   │                               │ {"workspace_id": …, …}
      ▼                   ▼                               ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │                    registry.invoke(cap_id, payload)   ← GOV-01 SEAM        │
 │  1. resolve record          → CapabilityNotFoundError                      │
 │  2. NEW: workspace_id → declared path field (D-01)                         │
 │       a. shape gate: kebab-case; reject "..", "/", absolute  [pre-resolve] │
 │       b. allowlist gate: name ∈ discover_workspaces(install_root)          │
 │       c. write into the model's OWN field name (5 names, 2 types)          │
 │  3. validate against input_model (extra="forbid")                          │
 │       → CapabilityInputError.from_validation_error(cap_id, exc, MODEL)     │
 │            ^^^^^^ D-08 makes `model` REQUIRED                              │
 │  4. handler(**model.model_dump())                                          │
 └───────────────────────────────┬───────────────────────────────────────────┘
                                 ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │  SHARED RESULT/ERROR BOUNDARY (new — serves MCP and HTTP)                  │
 │  • sanitize: no raw exception text, no filesystem paths                    │
 │  • one {reason, suggestion} shape; HTTP adds only a status code            │
 └───────────────────────────────┬───────────────────────────────────────────┘
                                 ▼
 ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────────────┐
 │ Sync capabilities│   │ Run capabilities │   │ workflow.list (NEW)        │
 │ (card, graph, …) │   │ start → run_id   │   │ enumerates THREE stores:   │
 │ return inline    │   │ poll  → inspect_*│   │  curation-run.sqlite       │
 └──────────────────┘   │ resume→ review_* │   │  research-run.sqlite       │
                        │  (_wrap_resume!) │   │  workflow/daily/*.json     │
                        └────────┬─────────┘   └─────────────┬──────────────┘
                                 │ detached subprocess        │ read-only
                                 ▼                            ▼
              ┌─────────────────────────────────────────────────────────┐
              │  {workspace}/.construct/workflow/   (adr-0004, L1)       │
              │  WAL journal + busy_timeout; NO cross-process lock       │
              │  races arbitrated by checkpoint-id ETag (D-11)           │
              └─────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
src/construct/api/                 # ARCHITECTURE.md already reserves this name ("planned src/construct/api/")
├── __init__.py
├── app.py                         # create_app(install_root, token) -> FastAPI. The zero-edit file.
├── middleware.py                  # OriginGuard + TokenGuard (Host handled by TrustedHostMiddleware)
├── errors.py                      # the four handler overrides -> one shape
└── runs.py                        # subprocess spawn, id return, stderr capture

src/construct/capabilities/
├── registry.py                    # invoke() gains step 2 (D-01)
├── workspaces.py         # NEW: workspace_id validator + resolver + field-name map
└── errors.py                      # from_validation_error(model) becomes REQUIRED (D-08)

src/construct/cli.py               # + `serve` command (trips test_doc_command_references.py)
.planning/phases/19-*/COVERAGE.md  # D-07 exposure ledger
tests/contract/
├── test_http_surface.py           # zero-edit guard (cardinality), envelope coverage
├── test_http_security.py          # Host/Origin/token; ordering: reject BEFORE dispatch
├── test_capability_seam.py        # + workspace_id resolution + traversal rejection
└── test_surface_parity.py         # 18-03's table gains a THIRD column
```

### Pattern 1 — `construct serve`: own the failure, not just the success

`uvicorn` raises `SystemExit(3)` on any startup failure including socket binding
(release note 0.50.0: *"Uvicorn now uses a dedicated exit code 3 for all startup failures, including
app loading, socket binding, and lifespan startup errors"*), which was reproduced live. That is not
a traceback — so D-04's obligation is not "avoid a traceback" but "produce something actionable and
exit `1` like every other CONSTRUCT command."

**Do:** probe the port yourself before handing control to uvicorn.

```python
# src/construct/cli.py
@app.command()
def serve(
    port: int = typer.Option(DEFAULT_PORT, "--port"),
    install_root: Path | None = typer.Option(None, "--install-root"),
) -> None:
    """Serve the CONSTRUCT capability API on 127.0.0.1 (loopback only)."""
    root = install_root or Path.cwd()

    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        typer.secho(
            f"ERROR: port {port} is already in use on 127.0.0.1. "
            f"Retry with `construct serve --port {port + 1}`, "
            f"or stop the process holding it (`lsof -i :{port}`).",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)      # project convention; uvicorn would have exited 3
    finally:
        probe.close()                  # small TOCTOU window, acceptable for a local PoC

    token = secrets.token_urlsafe(32)
    typer.echo(f"CONSTRUCT API  http://127.0.0.1:{port}")
    typer.echo(f"token          {token}")
    uvicorn.run(build_app(install_root=root, token=token), host="127.0.0.1", port=port)
```

**Note:** `uvicorn.run(app_instance, …)` (not an import string) is required here because the app
carries per-launch state (`install_root`, `token`). Uvicorn's docs recommend an import string, but
that path only supports `reload`/`workers`, neither of which a single-user local server wants.
`[CITED: uvicorn.dev/deployment]`

**Note on the install root:** there is no persisted install-root concept in the codebase today —
`cli.py:967` and `cli.py:1034` both do `install_root = install_root or Path.cwd()`, resolved at call
time (WR-09). `serve` should follow the same idiom, but the value becomes a **launch-time trust
boundary** rather than a per-call convenience. Record that as a decision.

### Pattern 2 — HTTP-02's zero-edit guard, when there is only one route

Under D-05 there is **no route generator**. `POST /api/capabilities/{cap_id}` is a single static
route with a path parameter; adding a capability adds zero routes and zero lines. That makes the
"never hand-edited" property trivially true — and it makes the *naive* guard vacuous.

The guard must therefore assert **reachability with cardinality**, driven from the registry, and
must not be satisfiable by a subset:

```python
# tests/contract/test_http_surface.py
def test_every_registry_capability_is_reachable_over_http() -> None:
    """Cardinality, not membership (WR-01 / Phase 18 D-04, D-19).

    A set-membership assertion passes when the surface exposes a subset; the
    catalog guard's own weakness is exactly that. Count first, then identity.
    """
    registry = get_registry()
    reachable = {c.id for c in registry.list() if _reaches_dispatch(client, c.id)}
    documented_exclusions = _coverage_md_exclusions()   # D-07: written down, with reasons

    assert len(reachable) + len(documented_exclusions) == len(registry)
    assert reachable | documented_exclusions == {c.id for c in registry.list()}
    assert not (reachable & documented_exclusions)
```

Three details the planner must not lose:

1. **Iterate `registry.list()`, never `registry.list_mcp_tools()`.** Measured: **6 of 29
   capabilities have no `mcp_tool_name`** — `knowledge.card.archive`, `knowledge.connection.list`,
   `knowledge.connection.remove`, `workflow.status`, `workspace.init`, `workspace.status` — and
   `list_mcp_tools()` silently `continue`s past them. Copying `mcp/server.py`'s loop verbatim
   produces a 23-capability surface that passes a membership test. (2 capabilities also have no
   `cli_name`: `graph.status`, `views.generate_data`.) `[VERIFIED: live registry introspection]`
2. **`_reaches_dispatch` must distinguish "route exists" from "capability ran".** A 422 on a missing
   required field proves the id resolved and the model validated — that *is* reachability, and is
   the only assertion available for capabilities that need an LLM key or a real workspace. A 404
   proves it is not reachable. Assert the discriminator explicitly, or the test degrades into
   "every id returns some status code".
3. **Derive test payloads from the registry.** Carried forward from Phase 18: `_payload_for`'s miss
   surfaces as a bare `KeyError`, and registering a capability trips five guards. A hand-listed
   payload table becomes the sixth.

### Pattern 3 — The workspace-id resolver: two gates, one place, three exceptions

```python
# src/construct/capabilities/workspaces.py
WORKSPACE_FIELD: dict[str, str] = {          # measured, exhaustive over the 29
    "ask.domain": "workspace_path", ...      # 13 × workspace_path (str)
    "graph.status": "workspace", ...         # 11 × workspace      (Path)
    "workspace.status": "path", ...          #  2 × path           (Path)
}
WORKSPACE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")   # _validate_run_id's shape

def resolve_workspace_id(cap_id: str, value: str, install_root: Path) -> Path:
    # Gate 1 — SHAPE, before any filesystem contact. Rejects "..", "/", "C:\", "~".
    if not WORKSPACE_ID_PATTERN.fullmatch(value):
        raise CapabilityInputError(cap_id, "workspace_id: must be a kebab-case name, "
                                           "e.g. 'my-construct' — not a path")
    # Gate 2 — ALLOWLIST. Membership in the scan, recomputed per request (D-02).
    known = {p.name: p for p in discover_workspaces(install_root)}
    if value not in known:
        raise CapabilityInputError(cap_id, f"workspace_id: no such workspace "
                                           f"(known: {', '.join(sorted(known))})")
    return known[value]
```

Then in `registry.invoke`, **between** record resolution and model validation:

```python
if "workspace_id" in payload:
    field = WORKSPACE_FIELD.get(cap_id)
    if field is None:
        raise CapabilityInputError(cap_id, "workspace_id: this capability is not workspace-scoped")
    if field in payload:
        raise CapabilityInputError(cap_id, f"workspace_id: cannot be combined with '{field}'")
    payload = {**payload, field: str(resolved)}   # str() — 13 models declare `workspace_path: str`
    payload.pop("workspace_id")
```

**Why the shape gate must precede the allowlist gate.** The allowlist alone is a sufficient
*authorisation* control, but `discover_workspaces` calls `install_root.iterdir()` and `_is_workspace`
does `(path / "cards").is_dir()` — filesystem contact driven by caller-controlled input. Rejecting
the string shape first means a traversal attempt never touches the filesystem at all, which is what
criterion 2's "with no filesystem effect" actually demands. This mirrors `_validate_run_id`'s own
rationale ("the MCP/CLI shims pass caller-supplied `**kwargs` straight into the input models").

**Note the type split:** 13 models declare `workspace_path: str` and 13 declare `Path`
(`workspace`/`path`). Pydantic will coerce `str → Path` but **not** `Path → str` under strict-ish
settings, so emit `str(resolved)` and let the `Path`-typed models coerce. Verify this against
`extra="forbid"` models in a test — it is a one-line assumption with a 26-capability blast radius.

**The three capabilities that are not workspace-scoped.** D-07 says every exclusion needs a written
reason, and criterion 1 says every capability is reachable. Recommended resolution — **no COVERAGE.md
exclusions at all**:

| Capability | Field | Recommendation |
|---|---|---|
| `views.generate_data`, `views.validate_data` | `install_root: Path` | The seam **injects the launch install root**; HTTP callers send no path field for these. Rationale: `install_root` is not a workspace id and is not caller-choosable at all under HTTP-03's threat model — it *is* the trust boundary. The CLI keeps its `--install-root` flag. Record as a named decision: "the seam supplies `install_root` from launch context; the field is not caller-settable over HTTP." |
| `workspace.init` | `root: Path` | Adopt the **uniform resolve-rule that asserts absence**: HTTP sends `workspace_id`, the seam resolves it to `install_root / id` and requires that it does **not** exist. This satisfies T-18-34 directly ("capabilities creating directories at agent-supplied paths") because the caller can name a directory but never choose *where* it lands, and it keeps criterion 1 literally true with zero exclusions. Cost: the resolver needs a `must_exist: bool` mode, so its two gates become {shape, not-in-scan} for creation and {shape, in-scan} for use. That is a small, symmetric addition — not a special case in the adapter. |

`COVERAGE.md` should still be written under D-07, but as a **full 29-row exposure ledger with an
empty exclusions section** — the artifact's value is that a future exclusion has a place to be
justified, not that exclusions exist today.

### Pattern 4 — One error shape means overriding **four** emitters, not one

Measured against a live FastAPI 0.141.1 + Starlette 1.3.1 app:

| Emitter | Status | Default body | Fix |
|---|---|---|---|
| `RequestValidationError` (envelope malformed) | 422 | `{"detail":[{"type":…,"loc":…,"msg":…,"input":"…"}]}` | `@app.exception_handler(RequestValidationError)` → project shape. **`input` echoes the caller's value — must be stripped**, same as the seam's `include_input=False`. |
| `StarletteHTTPException` (unknown route) | 404 | `{"detail":"Not Found"}` | `@app.exception_handler(StarletteHTTPException)` → project shape. |
| `TrustedHostMiddleware` | 400 | `PlainTextResponse("Invalid host header")` | **Cannot be overridden by an exception handler** — middleware responds before the app. Either accept a documented, deliberate exception for pre-dispatch rejections, or write the Host check into the same custom middleware as `Origin` so one code path emits one shape. Recommended: the latter. |
| Unhandled exception in a capability | 500 | traceback to stderr; body depends on config | Catch at the route and route through the shared sanitizing boundary. **Never** `str(exc)` — that is `mcp/server.py`'s existing defect (M-4). |

**Do not use the documented FastAPI pattern.** The official handling-errors page shows:

```python
# ANTI-PATTERN for this project — echoes the caller's raw submitted payload
return JSONResponse(status_code=422,
                    content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}))
```

`exc.body` is the raw request body. Returning it is exactly T-18-10 ("the caller's submitted values —
which may be filesystem paths or other sensitive payload content"), and `errors.py`'s
`from_validation_error` already sets `include_input=False` for that reason. The HTTP handler must
build its reason string the same way the seam does — ideally by *calling* the seam's own helper so
the two cannot drift. `[CITED: fastapi.tiangolo.com/tutorial/handling-errors]`

**Status-code mapping** (HTTP's own vocabulary; the reason/suggestion strings stay identical across
surfaces):

| Seam outcome | HTTP status |
|---|---|
| `CapabilityNotFoundError` | 404 |
| `CapabilityInputError` (incl. `workspace_id` shape/allowlist failures) | 422 |
| `OperationResult(success=False)` — the capability ran and refused | **200** with the result body. Do **not** map to 4xx: GOV-05 separates `success` ("the command ran") from `outcome`, and Phase 11's D-15 (degraded `curation.run` exits 0) is a statement about that flag. Turning `success=False` into an HTTP error re-forks the contract the CLI exit code already encodes. |
| Host / Origin / token rejection | 400 / 403 / 401, pre-dispatch |

### Pattern 5 — Localhost hardening: what the framework gives you and what it does not

Measured behaviours of `TrustedHostMiddleware(allowed_hosts=["127.0.0.1","localhost"])`:

| Request | Result | Note |
|---|---|---|
| `Host: evil.example.com` | **400** `Invalid host header` | ✅ This is the DNS-rebinding defence: after rebinding, the browser still sends the attacker's hostname. |
| `Host: 127.0.0.1:9999` | **200** | Port is stripped (`headers.get("host","").split(":")[0]`). Harmless — an attacker controls hostnames, not the IP literal. |
| `Origin: http://evil.example.com` | **200** | ❌ **Origin is never inspected.** HTTP-05 explicitly requires it; it is custom middleware or it does not exist. |
| `Content-Type: text/plain` body | **422** | ✅ A drive-by *simple request* (no preflight) cannot deliver a parseable JSON payload. D-05's security rationale holds. |
| no `Content-Type`, JSON body | **422** | ✅ Same. |
| `application/x-www-form-urlencoded` | **422** | ✅ Same. |

Set `www_redirect=False`: the default `True` makes the middleware answer a rejected host with a
redirect in some cases, which is not a behaviour a local API should exhibit.

**The custom middleware, per the MCP specification's own control set** — *"servers MUST validate the
Origin header on all incoming connections… if the Origin header is present and invalid, servers MUST
respond with HTTP 403 Forbidden"*:

```python
class LocalhostGuard(BaseHTTPMiddleware):
    """Host + Origin + per-launch token, in that order, before any dispatch."""

    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host not in {"127.0.0.1", "localhost", "[::1]"}:
            return _error(400, "invalid host")                    # rebinding
        origin = request.headers.get("origin")
        if origin is not None and origin not in self.allowed_origins:
            return _error(403, "invalid origin")                  # MCP-spec status
        supplied = request.headers.get("x-construct-token", "")
        if not secrets.compare_digest(supplied, self.token):      # constant-time
            return _error(401, "missing or invalid token")
        return await call_next(request)
```

Three deliberate choices worth recording as decisions:

- **Origin absent → allowed.** `curl` and the CLI send no `Origin`. Requiring it would break every
  non-browser client for no security gain, since a browser always sends `Origin` on cross-origin
  requests. This matches the MCP spec's wording ("if present and invalid").
- **Token in a custom header, not a query string.** `X-Construct-Token` (or `Authorization: Bearer`)
  is itself **not a CORS-safelisted header**, so any cross-origin request carrying it must pass a
  preflight — which will fail, because no `CORSMiddleware` is installed. The token therefore doubles
  as the CSRF control. A query-string token would land in shell history, server logs, and `Referer`.
- **`secrets.compare_digest`, not `==`.** ASVS V6; the project already uses `secrets` for run ids.

**Do not add `CORSMiddleware`.** With no CORS headers, the browser blocks every cross-origin read.
Adding permissive CORS would dismantle the property D-05's route shape was chosen for.

**Test ordering explicitly.** Criterion 4 says rejection happens "before it reaches a capability."
Assert it: a request with a foreign `Origin` naming a *write* capability must leave the workspace
byte-identical. A status-code assertion alone does not prove the capability did not run.

### Pattern 6 — Runs as addressable resources (HTTP-06)

The locked constraint is that a synchronous call is not an option. The preferred mechanism is a
detached subprocess (`construct <workflow> run --run-id X`). What makes this cheap here:

- **The run id can be minted before the process starts.** `_new_run_id()` (`curation_run.py:430`)
  produces `cur-<UTC stamp>-<hex>`, kebab-safe by construction, and both `CurationRunInput` and
  `ResearchRunInput` accept an optional `run_id`. So `POST` mints the id, spawns, and returns
  immediately — criterion 5's "returns an id immediately".
- **Polling needs no new read path.** `inspect_curation_run` / `inspect_research_run` already
  reconstruct status from the persisted checkpoint via `graph.get_state` **without resuming**, and
  surface `awaiting_review` with the pending `gate_queue` *before* the empty-values guard. HTTP-06's
  poll is `curation.inspect` through the existing envelope.
- **Cross-surface resume is free** because both sides are just processes writing the same checkpoint
  file. Nothing in the HTTP layer needs to know who started a run.

**Planner obligations for this route:**

1. **Stderr must be reachable.** A failed spawn (bad `ANTHROPIC_API_KEY`, import error, wrong cwd)
   writes to a pipe nobody reads and the run appears as "no such run" forever — a textbook instance
   of the project's named "silent success / audit-trail-that-lies" failure mode. Redirect to
   `.construct/workflow/logs/<run_id>.err` under the workspace and expose it on the status response.
2. **`_wrap_resume` is mandatory.** Carried forward explicitly for this phase: a bare id-keyed dict
   handed to `Command(resume=…)` is read by LangGraph as an *interrupt-id* mapping (a `proposal_id`
   is a 32-char `uuid4().hex`, exactly the shape of an interrupt id), silently consumed as an empty
   resume, leaving the run paused with zero writes and **no error**. Route every resume through the
   `*_review` capabilities, which already wrap — do not drive the graph from the API layer.
3. **Surface `checkpoint_id` on every run response.** Phase 22 owns the `If-Match`/409 behaviour, but
   Phase 19 must not foreclose it, and `review_*` already requires `checkpoint_id` as the ETag.
4. **The spawned command must exist and must not be `spike`.** Verify the exact CLI invocation
   against `cli.py`; `test_doc_command_references.py` asserts documented commands resolve, and a new
   `serve` command will itself trip that guard.

### Pattern 7 — `workflow.list` must span **three** durable stores

Enumerating checkpoint databases is only two thirds of the answer:

| Store | Path | Contents | Pausable? |
|---|---|---|---|
| Curation checkpoints | `{ws}/.construct/workflow/curation-run.sqlite` | `thread_id` = run id | ✅ pauses at `process_inbox` |
| Research checkpoints | `{ws}/.construct/workflow/research-run.sqlite` | `thread_id` = run id | ✅ pauses at the human gate |
| **Daily receipts** | `{ws}/.construct/workflow/daily/<run_id>.json` | a serialized `DailyRunResult` | ❌ never pauses — `_run_research_child` / `_run_curation_child` auto-resume with `approve_all=True` |

`daily.run` writes a **JSON receipt**, not a checkpoint (`daily_run.py:143`), and
`inspect_daily_run` reads it back with a missing-file → `status="failed"` branch. A `workflow.list`
built only on `SELECT DISTINCT thread_id` therefore reports zero daily runs while `daily.inspect`
happily answers for them — a listing that lies, which is HTTP-07's stated failure mode ("no run
becomes unreachable after its id is lost") reproduced inside its own fix.

Sketched shape:

```python
class WorkflowListInput(BaseModel):
    model_config = ConfigDict(extra="forbid")   # mandatory — the seam validates
    workspace: Path                              # + `workspace_id` via the D-01 resolver
    status: str | None = None                    # optional filter, e.g. "awaiting_review"

# per run: {"run_id", "workflow": "curation"|"research"|"daily", "status", "checkpoint_id"|None}
```

Read status via the existing `inspect_*` primitives rather than re-deriving it — three status
vocabularies already exist and a fourth would be a fork. Note the cost: `inspect_*` deserializes a
checkpoint per run, so a workspace with many runs makes listing O(runs). Acceptable for a local PoC;
worth an explicit note rather than a surprise.

**Registering `workflow.list` trips five guards, not one** (carried forward from Phase 18). Budget
for: the `extra="forbid"` cardinality guard (`test_capability_seam.py:87`), the registry-size
tripwire (`:77`), the declared-fields-bind-to-handler check (`:138`), `_payload_for` in
`test_mcp_contracts.py:102` (a miss is a bare `KeyError`), and `test_doc_command_references.py`.
Plus this phase's own new HTTP coverage guard — six.

### Anti-Patterns to Avoid

- **Copying `mcp/server.py`'s loop verbatim.** It iterates `list_mcp_tools()`, which skips the 6
  capabilities with no `mcp_tool_name`. Measured.
- **`json.dumps(..., default=str)` in the HTTP serializer.** `_serialize_result`'s docstring records
  why the MCP side deliberately has no `default=`: coercing an unexpected value with `str()` puts
  filesystem paths into the response (T-18-10). The HTTP serializer inherits that reasoning.
- **Mapping `OperationResult(success=False)` to a 4xx.** Breaks GOV-05's `success`/`outcome`
  separation and Phase 11's D-15 exit-code contract.
- **Resolving `workspace_id` in the adapter.** D-01 is locked; the Phase 18 handoff names this as
  rebuilding the fork GOV-01 closed.
- **A set-membership coverage guard.** WR-01's exact defect; assert cardinality.
- **`CORSMiddleware` with `allow_origins=["*"]`** — dismantles the property D-05's route shape buys.
- **Driving `graph.invoke(Command(resume=…))` from the API layer** — see `_wrap_resume`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Host-header validation | A hand-written host check | `starlette.middleware.trustedhost.TrustedHostMiddleware` (already installed) — **or** fold it into the custom Origin middleware for one error shape | Port stripping, IPv6 literals, and wildcard semantics are already audited. Only fold it in if the error-shape unification is worth it (it is — see Pattern 4). |
| Workspace enumeration | A new scan or a manifest file | `discover_workspaces(install_root)` (`views/lib/discover.py:16`) | D-02, locked. `_is_workspace` heuristics and `EXCLUDED_NAMES` are already written and already used by the views generator. |
| Run-id / workspace-id validation | A fresh regex | The `_validate_run_id` kebab-case pattern (`llm/curation_run.py:64-77`) | Written for exactly this threat ("shims pass caller-supplied `**kwargs` straight into the input models"). One pattern, one rejection message. |
| Reading run status | New checkpoint queries | `inspect_curation_run` / `inspect_research_run` / `inspect_daily_run` | Already read persisted state without resuming, already surface `awaiting_review` + `gate_queue`, already close the connection in `finally`. |
| Resume payload transport | An id-keyed dict passed to `Command(resume=…)` | `review_curation_run` / `review_research_run` (which call `_wrap_resume`) | A bare dict is silently swallowed as an interrupt-id map — paused run, zero writes, no error. |
| Validation-error reason strings | A new formatter for HTTP | `CapabilityInputError.from_validation_error(cap_id, exc, model)` | D-08 makes `model` required precisely so the generated adapter cannot silently get payload-ordered reasons. Reusing it *is* criterion 3. |
| JSON Schema for wizards | A hand-written field list | `cap.input_model.model_json_schema()` (D-06) | `ui/capability_runner.py` already generates Streamlit forms from it; a hardcoded list rots. |
| WAL / busy_timeout | Custom locking, lockfiles, or a connection pool | Explicit `PRAGMA journal_mode=WAL` + `sqlite3.connect(timeout=…)` — plus D-11's checkpoint-id ETag for race arbitration | Measured: WAL and a 5s busy_timeout are already in force by library and stdlib default. A lockfile adds stale-lock recovery whose failure mode is a permanently un-resumable run. |
| Token comparison | `supplied == expected` | `secrets.compare_digest` | Timing side-channel; ASVS V6. |
| Constant-time random tokens | `random`, `uuid4().hex` | `secrets.token_urlsafe` | Project idiom (`_new_run_id` uses `secrets.token_hex`). |

**Key insight:** almost everything this phase needs already exists one layer down. The failure mode
for Phase 19 is not "we couldn't build it" — it is building a *second* implementation of something
the CLI already has, which is precisely the fork the phase's goal sentence forbids. Every hand-roll
in this table would produce a browser-only behaviour over shared state.

---

## Common Pitfalls

### Pitfall 1: The port-collision traceback that isn't a traceback

**What goes wrong:** `construct serve` on an occupied port exits with code **3** and a bare
`[ERROR] [Errno 48] Address already in use` from uvicorn's logger — no traceback, no guidance, and
an exit code that contradicts every other CONSTRUCT command's `typer.Exit(code=1)`.
**Why it happens:** uvicorn 0.50.0+ deliberately uses `SystemExit(3)` for all startup failures.
**How to avoid:** probe-bind the socket first (Pattern 1) and own both the message and the exit code.
**Warning signs:** an integration test asserting `result.exit_code == 1` that passes because it never
exercises the collision path. `[VERIFIED: live execution against uvicorn 0.51.0]`

### Pitfall 2: The zero-edit guard that proves nothing

**What goes wrong:** with a single envelope route, "`app.py` was never hand-edited" is true by
construction, so a naive guard is vacuous — the exact class of defect as
`test_artifact_catalog.py`'s set-membership weakness (WR-01) and `_KNOWN_BROKEN`'s drift.
**Why it happens:** the guard is written to assert the *mechanism* (no per-capability routes) rather
than the *property* (every capability reachable).
**How to avoid:** cardinality assertion over `registry.list()` + a documented-exclusions set (Pattern 2),
plus an assertion that reachability is distinguishable from a 404.
**Warning signs:** the guard still passes when you delete a capability from the dispatch table.

### Pitfall 3: Enumerating threads by deserializing every checkpoint

**What goes wrong:** `SqliteSaver.list(None)` looks like the enumeration API but yields one tuple
*per checkpoint*, deserializing the state blob and every pending write, globally ordered by
`checkpoint_id DESC` with no thread grouping. A workspace with a few long runs makes the listing
endpoint visibly slow, and the ordering is not what a run list wants.
**How to avoid:** `SELECT DISTINCT thread_id FROM checkpoints`, then per-run status via the existing
`inspect_*` primitives.
**Warning signs:** listing latency that scales with run *length*, not run *count*.
`[VERIFIED: source inspection + live execution]`

### Pitfall 4: A run listing that omits every daily run

**What goes wrong:** `daily.run` persists `.construct/workflow/daily/<run_id>.json`, not a checkpoint.
A checkpoint-only `workflow.list` reports zero daily runs while `daily.inspect` answers for them.
**How to avoid:** span all three stores (Pattern 7) and assert coverage per workflow type in a test
that creates one run of each kind.
**Warning signs:** a `workflow.list` test fixture that only ever runs curation.

### Pitfall 5: The path leak that survives the sanitizer

**What goes wrong:** `pipelines/graph_status.py:66` writes `str(root.resolve())` into
`OperationResult.data` on the **success** path (T-18-32). An exception-boundary sanitizer never sees
it, so criterion 3 fails on a request that succeeded.
**How to avoid:** treat it as a third, separately-tracked item alongside the boundary sanitizer and
the shrink-only baseline (M-4). Assert criterion 3 with a test that greps a *successful* response
body for the install-root string, not only an error body.
**Warning signs:** a criterion-3 test that only exercises failures.

### Pitfall 6: The FastAPI validation handler that echoes the payload

**What goes wrong:** the official `RequestValidationError` handler example returns `exc.body` and
`exc.errors()` (which includes `input`). Both echo caller-submitted values back — T-18-10, on the
one surface the phase promises will not do that.
**How to avoid:** build the reason string through the seam's own `from_validation_error`, which
already sets `include_input=False`/`include_context=False`.
**Warning signs:** a 422 body containing an `input` key. `[CITED: fastapi.tiangolo.com/tutorial/handling-errors]`

### Pitfall 7: Believing OQ-4 is unimplemented

**What goes wrong:** the planner writes a task to "add WAL and busy_timeout", the implementer adds
them, every test passes — and nobody notices they were already in force, so no test ever *pins*
them. A future `langgraph-checkpoint-sqlite` bump that drops `PRAGMA journal_mode=WAL` from `setup()`
silently reverts the concurrency contract.
**How to avoid:** make the task "assert and document", not "add" (M-3).
**Warning signs:** an ADR-0004 extension with no corresponding `PRAGMA` assertion in the suite.

### Pitfall 8: Origin validation that never runs for the CLI

**What goes wrong:** requiring `Origin` on every request breaks `curl`, the CLI, and any scripted
client, because non-browser clients do not send one.
**How to avoid:** "absent → allow; present and not allowlisted → 403", per the MCP specification.
**Warning signs:** a smoke test using `TestClient` (which sends no `Origin`) that would fail against
a real browser, or vice versa.

### Pitfall 9: The `str`/`Path` split at the resolver

**What goes wrong:** 13 models declare `workspace_path: str` and 13 declare `Path`. Writing a
`Path` object into a `str`-typed field under `extra="forbid"` + pydantic v2 coercion rules produces
either a silent stringification or a validation error depending on the model's config — and the
failure surfaces as an unrelated field error.
**How to avoid:** emit `str(resolved)` and let `Path`-typed models coerce; assert both directions in
a parametrised test over all 26 workspace-scoped capabilities.
**Warning signs:** a resolver test that only covers one field name.

---

## Code Examples

### Discovery endpoint (D-06) — the GOV-01 half that MCP could not advertise

```python
# src/construct/api/app.py
@app.get("/api/capabilities")
def list_capabilities() -> dict:
    """Advertise the declared contract. Phase 18 D-21 conceded this on MCP
    (the pinned FastMCP has no schema-override parameter); HTTP recovers it."""
    return {
        "capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "description": cap.description,
                "input_schema": cap.input_model.model_json_schema(),
            }
            for cap in get_registry().list()      # list(), NOT list_mcp_tools()
        ]
    }
```

### The single envelope (D-05)

```python
class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")     # project convention; also blocks smuggling
    payload: dict[str, Any] = Field(default_factory=dict)

@app.post("/api/capabilities/{cap_id}")
def invoke_capability(cap_id: str, envelope: Envelope) -> JSONResponse:
    try:
        result = get_registry().invoke(cap_id, envelope.payload)
    except CapabilityNotFoundError as exc:
        return _project_error(404, exc)            # same reason string as CLI + MCP
    except CapabilityInputError as exc:
        return _project_error(422, exc)
    except Exception as exc:                       # never str(exc) — T-18-10
        return _project_error(500, _sanitized(exc))
    return JSONResponse(_serialize_result(result))  # shared with mcp/server.py
```

### Asserting criterion 3 mechanically (three surfaces, one shape)

```python
# tests/contract/test_surface_parity.py — 18-03's table gains a third column
@pytest.mark.parametrize("cap_id,payload", _known_failing_payloads_from_registry())
def test_one_reason_across_three_surfaces(cap_id, payload, http_client):
    cli  = _reason_from_cli(cap_id, payload)
    mcp  = _reason_from_mcp(cap_id, payload)
    http = _reason_from_http(http_client, cap_id, payload)
    assert cli == mcp == http

    for body in (cli, mcp, http):
        assert "Traceback" not in body
        assert str(INSTALL_ROOT) not in body           # no filesystem paths
        assert not _ABS_PATH_RE.search(body)           # criterion 3, mechanically
```

### Verifying WAL and busy_timeout are pinned, not inherited (M-3)

```python
def test_checkpointer_declares_its_concurrency_contract(tmp_path):
    """OQ-4 / adr-0004 extension. WAL and busy_timeout are currently supplied by
    SqliteSaver.setup() and by sqlite3.connect's timeout=5.0 default. Both are
    correct today and neither is ours — so a dependency bump could revert the
    contract with no test failing. This test is the pin."""
    saver, conn = _open_checkpointer(_workspace(tmp_path))
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000
    finally:
        conn.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on this phase |
|--------------|------------------|--------------|----------------------|
| `starlette` 0.4x pinned by FastAPI with an upper bound | FastAPI 0.141.1 declares `starlette>=0.46.0`, **no upper bound**; Starlette is at 1.3.1 | Starlette 1.0 era | The feared dependency conflict with the `mcp`-installed Starlette does not occur. `[VERIFIED: wheel METADATA]` |
| `httpx` as the Starlette TestClient transport | `httpx2` (Pydantic Services stewardship); `starlette.testclient` imports `httpx2` first, falls back to `httpx` with a deprecation warning | httpx2 2.x / Starlette 1.x | Tests work today on the installed `httpx` 0.28.1, on a deprecation path. `[VERIFIED: starlette/testclient.py]` |
| Uvicorn exiting 1 on startup failure | **Exit code 3 for all startup failures** | uvicorn 0.50.0 | Pitfall 1. `[CITED: uvicorn.dev/release-notes]` |
| Localhost = trusted; no Origin checks on local servers | MCP spec: servers **MUST** validate `Origin`, respond **403** when present and invalid, bind `127.0.0.1`, and authenticate even on localhost | 2025–2026, after DNS-rebinding advisories against MCP SDKs | HTTP-05's control set is not invented here — it is a published standard for this exact deployment shape. |
| `SqliteSaver` requiring manual WAL | `setup()` runs `PRAGMA journal_mode=WAL` itself | langgraph-checkpoint-sqlite 3.x | M-3 — OQ-4's premise. |

**Deprecated / outdated in this context:**

- `mcp/server.py`'s `except Exception: return json.dumps({"error": str(exc)})` — the last unguarded
  `str(exc)` on a serialized surface; the boundary sanitizer closes it as a side effect.
- `CapabilityInputError.from_validation_error(..., model=None)` — D-08 removes the optional form.
- The assumption that `pyproject.toml`'s dependency list describes the installed environment: it
  does not, and that is what makes D-03 cheap.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `WORKSPACE_FIELD` can be a static `{cap_id: field_name}` map because the 29 field names were enumerated exhaustively today. | Pattern 3 | A capability added between now and implementation gains no entry. **Mitigation:** make the map's coverage a cardinality guard — `set(WORKSPACE_FIELD) ∪ NON_WORKSPACE_SCOPED == {c.id for c in registry.list()}` — so registering a capability without classifying it fails a test rather than 500ing at runtime. |
| A2 | Emitting `str(resolved_path)` satisfies both the 13 `str`-typed and 13 `Path`-typed workspace fields under pydantic v2 + `extra="forbid"`. | Pattern 3 / Pitfall 9 | A per-model coercion surprise surfacing as an unrelated field error. **Mitigation:** parametrised test over all 26. Not verified in this session. |
| A3 | `X-Construct-Token` is not CORS-safelisted, so any cross-origin request carrying it is preflighted and blocked absent `CORSMiddleware`. | Pattern 5 | If wrong, the token stops doubling as the CSRF control and `Origin` validation becomes load-bearing — the situation D-05 was chosen to avoid. Standards-derived, not measured here. |
| A4 | Detached-subprocess spawn of `construct <workflow> run --run-id X` works from the server process (cwd, venv resolution, env inheritance including `ANTHROPIC_API_KEY`). | Pattern 6 | The whole HTTP-06 mechanism. **Mitigation:** this deserves the phase's first spike/smoke task, before any adapter work. Not exercised in this session. |
| A5 | `discover_workspaces(install_root)` per-request cost is negligible (one `iterdir` + up to 3 `stat`s per child). | Pattern 3 / D-02 | Only matters for an install root with very many children; a local PoC will not hit it. |
| A6 | The 29 domain-error `str(exc)` handlers (M-4's non-OSError column) do not leak paths. | M-4 | Two were probed live and did not leak; the other 27 were classified by exception type, not executed. A `WorkspaceLoadError` whose message interpolates a path would leak. **Mitigation:** the boundary sanitizer covers them regardless; only the shrink-only baseline's *size* depends on this. |
| A7 | Reusing `_serialize_result` from `mcp/server.py` for the HTTP body is correct and desirable. | Pattern 4 / Code Examples | If the two surfaces need different projections, sharing forces a compromise. Judgement, not measurement — but sharing is the phase's stated principle. |

---

## Open Questions

1. **Where does the per-launch token reach the browser?**
   - What we know: printing it to stdout works for `curl` and for a developer pasting it. Injecting
     it into a server-rendered `index.html` is the smoothest UX.
   - What's unclear: injection requires static serving, which CONTEXT.md names as a Phase 21
     deferral that would be *pulled forward* — "a decision to record, not a side effect."
   - Recommendation: print to stdout for Phase 19, and additionally write it to
     `{install_root}/.construct/api-token` with `0600` so Phase 21 has a file to read without a
     protocol change. Record the choice; do not pull static serving forward.

2. **What `busy_timeout` value?**
   - What we know: 5000 ms is the inherited stdlib default (M-3). A curation resume writing many
     cards holds the write lock for an unbounded interval.
   - What's unclear: the realistic upper bound of a resume's write transaction in this codebase.
   - Recommendation: set it explicitly at 30 000 ms and record the reasoning in the ADR-0004
     extension. A too-short timeout surfaces as `database is locked` mid-resume, which is exactly the
     failure OQ-4 exists to prevent.

3. **Does `install_root` belong on the `views.*` input models at all once HTTP cannot supply it?**
   - What we know: Pattern 3 recommends the seam injects it from launch context; the CLI keeps
     `--install-root`.
   - What's unclear: whether that makes `install_root` a *seam-supplied* field (a new concept —
     a field the caller may not set on one surface) or whether it stays caller-settable with the HTTP
     adapter simply never emitting it.
   - Recommendation: the latter — same shape as the `workspace_id`/path duality in M-1, so there is
     one rule ("HTTP emits ids and nothing path-shaped, guarded by a test") rather than two.

4. **Does `COVERAGE.md` live in the phase directory or the repo?**
   - What we know: D-25 named it "genuinely worth writing — just as Phase 19 planning input."
   - Recommendation: repo-side (e.g. `docs/` or next to the api package) and **machine-read by the
     coverage guard**, so an exclusion cannot be added to prose without the test seeing it. A
     planning-only document cannot participate in the cardinality assertion.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.14.5 (`>=3.11` declared) | — |
| `.venv` interpreter | AGENTS.md mandates it | ✓ | `.venv/bin/python` | — |
| `uvicorn` | HTTP-01 | ✓ **already installed** | 0.51.0 | — |
| `starlette` | HTTP-05 middleware, TestClient | ✓ **already installed** | 1.3.1 | — |
| `fastapi` | HTTP-01/02/04 | ✗ | — | **None needed** — installs with zero new transitive deps (dry-run verified). Bare Starlette is a viable fallback if the install is ever blocked. |
| `httpx` | test client transport | ✓ | 0.28.1 | `httpx2` 2.9.1 (preferred by Starlette 1.x) or `httpx.ASGITransport` |
| `pydantic` | input models | ✓ | 2.13.4 | — |
| `langgraph-checkpoint-sqlite` | HTTP-06/07, OQ-4 | ✓ | 3.1.0 | — |
| `pytest` | validation | ✓ | 9.0.3 | — |
| sqlite3 | checkpoints | ✓ | lib 3.53.2, `threadsafety=3` | — |
| Loopback ports 8000/8080/8765/7401 | HTTP-01 default | ✓ all free at time of research | — | `--port` override + Pitfall 1's message |
| `ANTHROPIC_API_KEY` | end-to-end run smoke tests only | not checked | — | Every existing run parity test degrades offline; follow that pattern. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `fastapi` (one pure-Python wheel; bare Starlette is the fallback).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=[".","src"]`) |
| Quick run command | `.venv/bin/python -m pytest tests/contract -q` |
| Full suite command | `.venv/bin/python -m pytest -q` (**820 tests currently collected**) |
| Test client | `starlette.testclient.TestClient` (via `fastapi.testclient`) — works on installed `httpx` 0.28.1 with a deprecation warning |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HTTP-01 | `serve` binds 127.0.0.1 only; not 0.0.0.0 | unit | `pytest tests/contract/test_http_surface.py::test_serve_binds_loopback_only -x` | ❌ Wave 0 |
| HTTP-01 | Port collision → actionable message, exit 1 | integration | `pytest tests/contract/test_http_surface.py::test_port_collision_is_actionable -x` | ❌ Wave 0 |
| HTTP-02 | Every registry capability reachable (cardinality) | contract | `pytest tests/contract/test_http_surface.py::test_every_registry_capability_is_reachable_over_http -x` | ❌ Wave 0 |
| HTTP-02 | Coverage guard fails when a capability is dropped | contract (meta) | `pytest tests/contract/test_http_surface.py::test_coverage_guard_is_not_vacuous -x` | ❌ Wave 0 |
| HTTP-03 | `workspace_id` resolves; `../../etc` rejected **with no filesystem effect** | contract | `pytest tests/contract/test_capability_seam.py -k workspace_id -x` | ⚠️ file exists (984 lines); new cases needed |
| HTTP-03 | HTTP can never emit a path-shaped key | contract | `pytest tests/contract/test_http_surface.py::test_http_payloads_carry_no_path_field -x` | ❌ Wave 0 |
| HTTP-04 | Same reason+suggestion across CLI/MCP/HTTP | contract | `pytest tests/contract/test_surface_parity.py -x` | ❌ Wave 0 (extends 18-03's table) |
| HTTP-04 | No abs path / no `Traceback` in **success or error** bodies | contract | `pytest tests/contract/test_surface_parity.py -k no_path_leak -x` | ❌ Wave 0 |
| HTTP-05 | Foreign `Host` → 400; foreign `Origin` → 403; missing token → 401 | contract | `pytest tests/contract/test_http_security.py -x` | ❌ Wave 0 |
| HTTP-05 | Rejection happens **before dispatch** (workspace byte-identical after) | contract | `pytest tests/contract/test_http_security.py::test_rejection_precedes_any_capability_effect -x` | ❌ Wave 0 |
| HTTP-06 | Start returns id immediately; pollable while running | integration | `pytest tests/integration/test_http_runs.py::test_run_is_pollable_while_running -x` | ❌ Wave 0 |
| HTTP-06 | Browser-started run resumable from CLI, and the reverse | integration | `pytest tests/integration/test_http_runs.py::test_cross_surface_resume -x` | ❌ Wave 0 |
| HTTP-06 | Failed spawn surfaces stderr | integration | `pytest tests/integration/test_http_runs.py::test_failed_spawn_is_visible -x` | ❌ Wave 0 |
| HTTP-07 | Listing includes paused runs **and daily receipts** | contract | `pytest tests/contract/test_workflow_list.py -x` | ❌ Wave 0 |
| OQ-4 | WAL + busy_timeout pinned by assertion, not inherited | unit | `pytest tests/llm/test_checkpoint_concurrency.py -x` | ❌ Wave 0 |
| D-08 | `from_validation_error` rejects a missing `model` | unit | `pytest tests/contract/test_capability_seam.py -k from_validation_error -x` | ⚠️ file exists |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/contract -q`
- **Per wave merge:** `.venv/bin/python -m pytest -q` (820 + new)
- **Phase gate:** full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/contract/test_http_surface.py` — HTTP-01, HTTP-02, HTTP-03 (adapter side)
- [ ] `tests/contract/test_http_security.py` — HTTP-05, incl. the ordering assertion
- [ ] `tests/contract/test_surface_parity.py` — HTTP-04; extends 18-03's differential table
- [ ] `tests/contract/test_workflow_list.py` — HTTP-07, all three stores
- [ ] `tests/integration/test_http_runs.py` — HTTP-06, incl. cross-surface resume + spawn failure
- [ ] `tests/llm/test_checkpoint_concurrency.py` — OQ-4 pin
- [ ] Shared fixture: an app factory + `TestClient` with a known token and a temp install root
      holding ≥2 discoverable workspaces (`conftest.py`)
- [ ] Framework install: **none** — pytest 9.0.3 present. Optional: `pip install httpx2` to clear
      the Starlette TestClient deprecation warning.

---

## Security Domain

`security_enforcement` is absent from `.planning/config.json` → treated as **enabled**.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | **yes** (minimal) | Per-launch bearer token in a custom header, `secrets.token_urlsafe(32)`, compared with `secrets.compare_digest`. Out of scope: users, sessions, rotation. |
| V3 Session Management | no | No sessions, no cookies. Deliberate: a cookie would be ambient authority and thus CSRF-attackable; a header token is not. Record this as the reason. |
| V4 Access Control | **yes** | The install root is the authorization boundary. `workspace_id` ∈ `discover_workspaces(install_root)` is the allowlist (D-02). |
| V5 Input Validation | **yes** | `registry.invoke` validates against `input_model` with `extra="forbid"` on all 29 (GOV-01, cardinality-guarded). Plus the kebab-case shape gate before any filesystem contact. |
| V6 Cryptography | **yes** (minimal) | `secrets` for generation, `compare_digest` for comparison. Never `random`, never `==`. |
| V7 Error Handling & Logging | **yes** | Criterion 3: no raw exception text, no filesystem paths in any body. Four emitters to unify (Pattern 4); 14 demonstrable leak sites (M-4). |
| V12 File & Resource | **yes** | Path traversal (T-18-34 lineage): shape gate → allowlist gate → resolve. `workspace.init` asserts *absence* under the install root so bytes cannot land at a caller-chosen path. |
| V13 API & Web Service | **yes** | Single JSON envelope; `Content-Type` strictness measured to reject `text/plain`/form bodies with 422; no CORS. |

### Known Threat Patterns for a loopback Python/ASGI API over a filesystem-backed registry

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **DNS rebinding** — attacker domain rebinds to 127.0.0.1; page then reads the local API | Information disclosure / EoP | `Host` allowlist (`TrustedHostMiddleware` or the custom guard), **plus** `Origin` validation → 403. MCP spec mandates both. Measured: `TrustedHostMiddleware` alone does **not** check `Origin`. |
| **Drive-by CSRF** — any page POSTs to `http://127.0.0.1:<port>` | Tampering | JSON `Content-Type` requirement (measured: `text/plain`/form/no-CT all 422) + a non-safelisted token header forcing a preflight that no CORS policy answers. This is why D-05 chose a JSON-body POST envelope. |
| **Path traversal via `workspace_id`** (`"../../etc"`) | Tampering / Info disclosure | Two gates, shape before allowlist, both inside the seam (D-01). Criterion 2 requires **no filesystem effect**, which the ordering delivers. |
| **Directory creation at an attacker-chosen path** (T-18-34) | Tampering | `workspace.init` resolves under the launch install root only and asserts absence; `_run_workspace_refusal` already guards the run family's `workspace_path`. |
| **Filesystem path disclosure in responses** (T-18-10 / T-18-32) | Information disclosure | Boundary sanitizer + shrink-only baseline of 14 + the separate `graph_status.py:66` success-path fix (M-4). |
| **Raw exception text disclosure** | Information disclosure | Ban `str(exc)` at the boundary; `mcp/server.py`'s catch-all is the last one. Never `json.dumps(default=str)`. |
| **Timing attack on the token** | Spoofing | `secrets.compare_digest`. |
| **Token disclosure via logs / `Referer` / shell history** | Information disclosure | Header, never query string. If written to disk, `0600`. |
| **Command injection via the run spawner** | EoP | Spawn with an argument **list**, never `shell=True`; `run_id` is kebab-validated before it reaches the argv. `spike run --tool-path` stays off HTTP entirely (an RCE primitive by design). |
| **Unbounded run spawning** | DoS | Out of scope for a single-user PoC, but worth one sentence in COVERAGE.md rather than silence. |
| **Binding 0.0.0.0 by accident** | EoP | Assert the bind address in a test, not just in the default argument. |

---

## Project Constraints (from AGENTS.md)

The repo has no `CLAUDE.md`; `AGENTS.md` is the equivalent authority. Directives the planner must
honour:

- **Use the repository-local `.venv/` for all Python runtime dependencies, CLI commands, developer
  tools, and tests.** Run pytest as `.venv/bin/python -m pytest` from the repository root — never
  bare `pytest`.
- Refresh dependencies with `.venv/bin/python -m pip install -e '.[dev]'`.
- **Do not introduce cloud-first, multi-user, or auth-heavy architecture.** HTTP-05 is minimal
  localhost hardening; anything beyond it contradicts both AGENTS.md and REQUIREMENTS.md's
  Out-of-Scope table.
- **Do not modify `archive/v01-python/`.** `src/` and `tests/` are the live trees.
- All modules begin with `from __future__ import annotations`; module docstring on every file;
  4-space indent; type annotations on every signature including `-> None`.
- **Every Pydantic model sets `model_config = ConfigDict(extra="forbid")`** — the sole documented
  exception is the derived-views projection models. A new `WorkflowListInput` or `Envelope` without
  it fails `test_capability_seam.py`'s cardinality guard.
- Custom errors are `ValueError` subclasses with `PascalCase…Error` names — **except** the
  capability-seam errors, which subclass `Exception` deliberately and documentedly.
- Always chain: `raise NewError(...) from original_exc`.
- **Never let raw exceptions reach the user in CLI context**; catch domain exceptions, emit
  `typer.echo(f"ERROR {exc}")`, then `raise typer.Exit(code=1)`. The HTTP surface inherits the spirit
  (Pitfall 1 aligns `serve`'s exit code with it).
- No barrel files; import from specific modules.
- Validators raise `ValueError` with human-readable messages **including examples** — the
  `workspace_id` rejection message should follow (`"e.g. 'my-construct' — not a path"`).
- `.planning/` is the live GSD tree; ARCHITECTURE.md already reserves `src/construct/api/` as the
  planned HTTP location and already states "Three invoke surfaces (CLI / MCP / HTTP) all call the
  same capability registry."

---

## Sources

### Primary (HIGH confidence)

- **This repository, read directly** — `capabilities/registry.py`, `capabilities/errors.py`,
  `capabilities/catalog.py` (1414 lines, 29 records), `mcp/server.py` (71 lines),
  `views/lib/discover.py`, `llm/curation_run.py`, `llm/research_run.py`, `llm/daily_run.py`,
  `pipelines/graph_status.py`, `services/knowledge.py`, `services/validation.py`, `cli.py`,
  `ui/capability_runner.py`, `tests/contract/*`, `AGENTS.md`, `.planning/REQUIREMENTS.md`,
  `.planning/PROJECT.md`, `.planning/phases/19-*/19-CONTEXT.md`.
- **Live execution against the pinned environment** — registry introspection (29 capabilities, field
  names, missing `mcp_tool_name`/`cli_name`); AST scans (41 path-shaped invoke sites; 43 `str(exc)`
  handlers classified by exception family); `SqliteSaver` WAL/`busy_timeout`/`list(None)`/`DISTINCT
  thread_id`; FastAPI 0.141.1 + Starlette 1.3.1 probe app (Host/Origin/Content-Type matrix, default
  error bodies); uvicorn port-collision `SystemExit(3)`; `pip install --dry-run`; wheel `METADATA`.
- **Context7 `/websites/fastapi_tiangolo`** — dynamic route registration & `APIRouter`;
  `TrustedHostMiddleware` / `CORSMiddleware`; custom exception handlers.
- **Context7 `/websites/uvicorn_dev`** — programmatic run; release note 0.50.0 (exit code 3);
  socket-binding settings.

### Secondary (MEDIUM confidence)

- MCP specification security guidance for local HTTP servers (`Origin` MUST be validated, 403 on
  invalid, bind 127.0.0.1, authenticate even on localhost) as reported via WebSearch, corroborated by
  three independent advisories: GHSA-w48q-cv73-mx4w (TypeScript SDK), CVE-2025-66416 (Python SDK),
  GHSA-89vp-x53w-74fx (rmcp Host validation).
- `pypi.org/project/httpx2/` and `github.com/pydantic/httpx2` — Pydantic Services stewardship of
  httpx; Starlette TestClient preference.

### Tertiary (LOW confidence)

- None relied upon. A3 (CORS-safelisting of `X-Construct-Token`) is standards-derived but not
  measured in this session and is logged in the Assumptions Log.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Standard stack & install cost | **HIGH** | `pip --dry-run` + wheel METADATA + a working probe venv; the only new artifact is one pure-Python wheel. |
| Workspace-id resolver design (D-01) | **HIGH** | The 29-capability field map was reproduced exactly by introspection; the 41 call sites were counted by AST, not estimated. |
| Error-shape unification (HTTP-04) | **HIGH** | All four default emitters were reproduced against a live app; the `exc.body` anti-pattern is quoted from the official docs. |
| Localhost hardening (HTTP-05) | **HIGH** for the framework behaviour (measured); **MEDIUM** for the control set (standards-derived) | `TrustedHostMiddleware`'s Host-only scope and the Content-Type matrix were executed; the MUST-validate-Origin/403 requirement comes from the MCP spec via search. |
| Checkpoint concurrency (OQ-4) | **HIGH** | WAL, `busy_timeout=5000`, WAL persistence, and the per-instance `threading.Lock` were all executed and observed. |
| Run enumeration (HTTP-07) | **HIGH** | Three stores confirmed from source; `list(None)` and `DISTINCT thread_id` both executed. |
| Path-leak census (M-4) | **HIGH** for counts and classification; **MEDIUM** for "which actually leak in production" | 43 handlers classified by AST; 2 probed live; `str(OSError)`/`str(ValidationError)` leakage confirmed. A6 records the residual. |
| Run execution model (Pattern 6) | **MEDIUM** | Design follows directly from existing primitives, but the subprocess spawn itself was not exercised (A4). Recommended as the phase's first smoke task. |

**Research date:** 2026-08-02
**Valid until:** 2026-09-01 (30 days — FastAPI/Starlette/uvicorn move fast enough that the version
pins should be re-checked if planning slips past this; the in-repo measurements are stable until the
code changes).
