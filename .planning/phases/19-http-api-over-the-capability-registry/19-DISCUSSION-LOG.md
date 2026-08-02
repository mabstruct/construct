# Phase 19: HTTP API over the Capability Registry - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-02
**Phase:** 19-HTTP API over the Capability Registry
**Areas discussed:** Workspace addressing (HTTP-03), Run lifecycle & listing (HTTP-06/07), Server shape & localhost hardening (HTTP-01/05), Route generation & exposure policy (HTTP-02)

**Area selection:** all four offered areas were selected.

---

## Workspace addressing (HTTP-03)

### Q1 — Where should workspace-id → path resolution live?

| Option | Description | Selected |
|--------|-------------|----------|
| In the seam (`registry.invoke`) | Seam resolves `workspace_id` into whatever path field the capability declares; all three surfaces gain id-addressing; cost is the seam gaining capability-specific knowledge | ✓ |
| In the HTTP adapter only | Smallest change, seam stays pure; cost is the shape Phase 18 flagged as "rebuilds the fork GOV-01 closed" | |
| In the models (all 29) | One contract everywhere, validator-level traversal rejection; cost is touching all 29 capabilities and every call site | |
| You decide | Defer to research/planner | |

**User's choice:** In the seam.
**Notes:** Presented with the measured field-name table — `workspace_path` (13), `workspace` (11), `install_root` (2), `root` (1), `path` (2). Five names, two types.

### Q2 — What is a workspace id, and where does the valid set come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Directory name under install root | Ids = `discover_workspaces()` output, recomputed per request; kebab validator rejects traversal before resolution | ✓ |
| Directory name + cached manifest | Faster, uniform unknown-id failure; cost is a workspace created mid-session being invisible until refresh | |
| Opaque id in a registry file | Id can never be a path fragment; cost is new state to write and migrate | |
| You decide | | |

**User's choice:** Directory name under install root.
**Notes:** Per-request recomputation matters for Phase 22's workspace-creation wizard.

### Q3 — What happens to path-shaped payloads once the seam resolves ids?

| Option | Description | Selected |
|--------|-------------|----------|
| Seam is id-first; HTTP never sends paths | Both shapes accepted at the seam; HTTP generated so it can only emit `workspace_id`, guarded | |
| Seam is id-only; CLI translates at its edge | One shape; breaks a CLI pointed outside the install root | |
| Seam accepts both; HTTP refuses paths itself | One-line criterion-2 check; per-surface policy | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Preference recorded in CONTEXT.md as id-first. Research to measure how many CLI call sites and tests pass a path today.

### Q4 — How should `workspace.init` be addressed over HTTP?

| Option | Description | Selected |
|--------|-------------|----------|
| Name-only, server places it | Caller cannot choose where bytes land — the T-18-34 lesson at the surface | |
| Same as reads — name resolves, must not exist | Uniform rule; resolution gains an absence mode | |
| Out of scope for Phase 19 | Creation stays CLI-only; needs an explicit criterion-1 rewording | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** To be settled alongside the exposure policy, not separately.

---

## Run lifecycle & listing (HTTP-06/07)

Context presented: `run_id` **is** the LangGraph `thread_id`, stored per-workflow-type in
`.construct/workflow/*.sqlite` inside the workspace. `curation.inspect` / `research.inspect` already
poll persisted state without resuming. No enumeration exists anywhere — a lost id today is a lost run.

### Q1 — What executes a run so POST returns an id immediately?

| Option | Description | Selected |
|--------|-------------|----------|
| Detached subprocess (the CLI) | Crash isolation, no sqlite-across-threads question, browser/CLI symmetry free | |
| Background thread in the server | Simplest; richer live status; a restart kills the run silently | |
| Thread pool with a bounded queue | Serializes by construction; a queued run is a status the checkpoint doesn't know | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Preference recorded as detached subprocess. A synchronous call was explicitly ruled out —
criterion 5 requires the id immediately and pollability while running.

### Q2 — Where should run enumeration (HTTP-07) live?

| Option | Description | Selected |
|--------|-------------|----------|
| New `workflow.list` registry capability | CLI + MCP gain it too; HTTP gets it free | |
| Extend the existing `workflow.status` | No new guards; changes an existing output shape | |
| HTTP reads the checkpoints directly | Fastest; a browser-only feature over state the CLI can't see | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Preference recorded as a new `workflow.list` capability. Research to confirm what the
pinned `langgraph-checkpoint-sqlite` exposes for thread enumeration.

### Q3 — OQ-4, the checkpoint concurrency contract

| Option | Description | Selected |
|--------|-------------|----------|
| WAL + `busy_timeout`, no locking | D-11's ETag rejects the losing resume with zero writes | |
| WAL + single-flight lock per run | Clearer message; guarantee is one-sided (CLI can't see it) | |
| WAL + lockfile visible to both | Real mutual exclusion; stale-lock recovery is new failure surface | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Preference recorded as WAL + `busy_timeout`. The ADR-0004 extension is a deliverable either way.

### Q4 — How does the browser learn a run is progressing?

| Option | Description | Selected |
|--------|-------------|----------|
| Client polls the inspect endpoint | Nothing new; works for CLI-started runs; chunky at node boundaries | |
| SSE stream per run | Better UX for long runs; real new server surface | |
| Poll now, SSE deferred to Phase 21 | Phase 21 owns the guided layer and can judge | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Preference recorded as poll now, SSE deferred to Phase 21.

---

## Server shape & localhost hardening (HTTP-01/05)

### Q1 — Which HTTP stack?

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI + uvicorn | Pydantic v2 already the input layer; schema generation aligns with the registry; heaviest dependency | ✓ |
| Starlette + uvicorn | Lighter; FastAPI's decorator ergonomics partly unused with generated routes; no free OpenAPI | |
| Stdlib `http.server` | Zero deps; single-threaded, hand-rolled middleware for a stated trust boundary | |
| You decide | | |

**User's choice:** FastAPI + uvicorn.
**Notes:** Presented with the fact that `pyproject.toml` ships no web server today.

### Q2 — How does the per-launch token reach the browser?

| Option | Description | Selected |
|--------|-------------|----------|
| Launch URL → httpOnly cookie | Zero SPA code; Origin/Host does the anti-drive-by work | |
| Server injects token into `index.html` | Strongest against CSRF-shaped attacks; requires serving the SPA (Phase 21's job) | |
| URL fragment → sessionStorage | Never sent to a server; script-readable, lost on reload without the fragment | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** To follow the localhost threat-model research pass the ROADMAP already flags. Noted in
CONTEXT.md that option 2 would pull static serving forward from Phase 21.

### Q3 — What does `construct serve` look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed port, prints URL | Predictable, bookmarkable, quotable in the Phase 24 playbook | ✓ |
| Ephemeral port, auto-opens browser | Closest to "one command and you're in"; no stable URL; misbehaves headless | |
| Fixed port + `--open` flag | Both audiences; two paths to document | |
| You decide | | |

**User's choice:** Fixed port, prints URL (`--port` overridable).
**Notes:** Planner obligation recorded — a port collision must produce an actionable message, not a traceback.

### Q4 — Where does the T-18-10/T-18-32 path-leak fix land?

| Option | Description | Selected |
|--------|-------------|----------|
| One sanitizer at the shared boundary | ~29 sites with one change; treats symptoms | |
| Fix the ~27 sources in `services/knowledge.py` | Leak genuinely gone; large hand-edit in an already-full phase | |
| Both — sanitizer now, sources tracked shrink-only | Criterion 3 holds mechanically; debt can't grow (D-23 pattern) | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Preference recorded as the "both" shape. Research to measure how many of the ~27 sites
actually reach a serialized body.

---

## Route generation & exposure policy (HTTP-02)

### Q1 — What shape do the generated routes take?

The first attempt at this question was returned by the user with "implications of this decision not
clear". A written implications analysis was produced before re-asking, covering: what actually
consumes the API (only the SPA and wizards); what GET buys in a browser (linkability, back/forward,
caching — near-worthless for a single-user local tool, real for debugging); the security interaction
(a drive-by page can issue GET but not JSON POST without preflight, so GET reads would make
`Origin`/`Host` the single load-bearing control for HTTP-05); what the zero-edit guard must prove in
each case (per-capability GET/POST classification has no home in the registry, so it rests on a new
field or a heuristic); the asymmetric cost of changing later (envelope→REST additive, REST→envelope
destructive); and what each costs the SPA.

| Option | Description | Selected |
|--------|-------------|----------|
| One envelope: `POST /api/capabilities/{id}` | One route so the guard can't drift; preflight makes Origin/Host defence-in-depth; one `invoke()` for the SPA; REST additive later | ✓ |
| Generated per-capability routes with GET reads | Self-describing URLs, linkability, caching; GET classification rests on a new field or a heuristic; Origin/Host becomes load-bearing | |
| Envelope now, REST if the SPA asks | Identical code; differs only in what CONTEXT.md tells downstream phases | |
| You decide | | |

**User's choice:** One envelope.
**Notes:** Chosen after the implications analysis, not as a default. Recorded in CONTEXT.md as an
informed decision — reopening it requires new evidence, not new preference.

### Q2 — Should the API expose `model_json_schema()`?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — a discovery endpoint | `GET /api/capabilities` with id, description, schema; recovers the discoverability half D-21 conceded on MCP | ✓ |
| Yes, but per-capability only | Same form-generation benefit; SPA still needs a hardcoded list to ask | |
| No — SPA codes against known shapes | Smallest surface; reintroduces the writer/reader fork this codebase keeps paying for | |
| You decide | | |

**User's choice:** Yes — a discovery endpoint.
**Notes:** Presented with Phase 18's D-21 (pinned FastMCP has no schema-override, so MCP structurally
cannot advertise input schemas).

### Q3 — Which of the 29 capabilities does HTTP expose?

| Option | Description | Selected |
|--------|-------------|----------|
| All 29, opt-outs written down | Full coverage guarded; exclusions need a reasoned COVERAGE.md row (the artifact D-25 named) | ✓ |
| All 29, writes gated behind a flag | Read-only default; the flag would be on for every real session — theatre | |
| Curated allowlist for the PoC | Smallest surface; criterion 1 becomes false as written and the zero-edit guarantee weakens | |
| You decide | | |

**User's choice:** All 29, opt-outs written down.
**Notes:** `spike` and `tag` are not in the registry at all (Phase 18 D-02), so they're out by
construction rather than by opt-out.

### Q4 — How is WR-04 closed?

| Option | Description | Selected |
|--------|-------------|----------|
| Make `model` required + extend the parity test | Footgun removed at the type level and criterion 3 proven by the existing parity harness | ✓ |
| Extend the parity test only | Smaller; the footgun survives for the next surface | |
| Make `model` required only | Criterion 3 rests on inspection — how three of Phase 18's green self-reports went wrong | |
| You decide | | |

**User's choice:** Make `model` required + extend the parity test.

---

## Claude's Discretion

Delegated by the user, each with a preference recorded in CONTEXT.md:

- Path-shaped payloads at the seam (preference: id-first).
- `workspace.init` addressing over HTTP (settle with the exposure policy).
- Run execution model (preference: detached subprocess).
- Run enumeration home (preference: a new `workflow.list` capability).
- OQ-4 concurrency primitive (preference: WAL + `busy_timeout`).
- Progress reporting (preference: poll now, SSE to Phase 21).
- T-18-10/T-18-32 path-leak fix shape (preference: boundary sanitizer + shrink-only source guard).

Pattern worth noting: the user locked *contract* questions and delegated *mechanism* questions.

## Deferred Ideas

- SSE / streaming progress → Phase 21.
- Per-capability REST routes → additive later if Phases 21/23 bring evidence.
- The ETag's browser-side `If-Match` / 409 behaviour → Phase 22 (already Phase 18's deferral).
- Serving the SPA's static files → nominally Phase 21; only pulled forward if the token decision
  picks server-injected HTML.
- API versioning → not a concern for a single-user local PoC on an isolated branch.
- RT-01/RT-02 unification for `spike` / `tag` → v0.6.
- Repairing `test_artifact_catalog.py`'s own set-membership weakness (WR-01) → still deferred.
- `card list` MCP-boundary hardening (WR-01/WR-02) → carried-forward debt.

No scope creep was raised during the discussion — every area stayed inside the HTTP-01..07 boundary.
