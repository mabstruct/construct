# spec-v02-runtime-topology — Runtime Topology and User-Facing Entry

**Status:** Draft
**Date:** 2026-04-27
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 7
**Related:** `prd-v02-live-views.md` §3.4, §5.3, §6.1 · `adrs/adr-0002-v02-packaging.md`

---

## 1. Scope

This spec defines, for v0.2 MVP, **how the user starts, browses, and stops CONSTRUCT** when live views are present. It picks the local serving option, names the user-facing entry skill, defines server lifecycle, routing, and the refresh model. It also marks the stable boundary that survives a future cloud-topology swap.

This spec **does not** cover JSON data contracts (Epic 2 / `spec-v02-data-model.md`), per-view UI design (Epic 8), or hook attachment to existing skills (Epic 9 / `prd-v02-live-views.md` §6.1).

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Server scope | One server per CONSTRUCT installation, hosting all workspaces |
| Bootstrap point | New `construct-up` skill; called lazily by `domain-init` if no server running |
| Shutdown | New `construct-down` skill (or "end session" phrase) |
| Local serving option | `serve` (npm package), invoked via `npm run serve` from `views/src/`. `--single` flag is mandatory (SPA history fallback for `BrowserRouter` routes). Node already required by Vite build, so no extra runtime prerequisite. |
| Host | `localhost` only — no `0.0.0.0` exposure |
| Port range | `3001`–`3009`. First instance takes 3001; second instance takes 3002; etc. |
| Process model | Background process surviving Claude conversation closes |
| Auto-start / auto-restart | None. User runs `construct-up` again on crash or reboot |
| PID file | `views/server.pid` (co-located with build output) |
| Refresh model | Manual reload, with `UPDATE` / `NEWS` flag in header when stale |
| Stale-detection mechanism | `views/build/version.json` polled by SPA on tab focus + every ~30s |
| Routing root | `/` — landing dashboard with workspace switcher + cross-workspace articles |
| Workspace routing | `/<workspace>/...` for per-workspace views |
| MVP landing content | Switcher + per-workspace status + cross-workspace articles. Bridges and activity feed deferred to v0.2.1 |

---

## 3. Server Bootstrap and Lifecycle

### 3.1 Bootstrap

The CONSTRUCT install root looks like:

```
~/my-construct/
├── AGENTS.md                # Claude reads this
├── .construct/              # Agent infrastructure (existing v0.1)
├── VERSION                  # mirrors CONSTRUCT-CLAUDE-impl/VERSION at install
├── cosmology/               # workspace
├── climate-policy/          # workspace
└── views/
    ├── src/                 # generated SPA source
    ├── build/               # built static site (served)
    │   └── version.json     # build_id + generated_at
    └── server.pid           # running server's PID (when up)
```

`construct-up` orchestration:

1. Resolve `views/build/`. If missing or empty → fail clearly with "run `views-build` first" (MVP simplification — chained build is v0.2.1).
2. Pick the first free port in `3001..3009`. If all taken → fail clearly with port-exhaustion message.
3. Start the SPA server as a detached process (no terminal attachment) by invoking `npm run serve` from `views/src/`. The `serve` script in `views/src/package.json` resolves to `serve ../build --single -l <port>`. `serve` is a dev dependency, installed by `npm install` during scaffold/build — `npx` network behaviour is not relied on at run time. The `--single` flag is mandatory: it makes the server fall back to `index.html` for unknown paths so client-side routes (`/<workspace>/...`, `/articles/<slug>`) work on direct load and reload.
4. Write `views/server.pid` with the child PID.
5. Report URL `http://localhost:<port>/` to the user.

### 3.2 Lazy bootstrap from `domain-init`

`domain-init` (existing v0.1) gets one additive check at the start:

```
if not server-running():
    run construct-up (silently — single line in the user-facing transcript: "Bringing up views server on http://localhost:3001/")
```

`server-running()` = `views/server.pid` exists AND that PID is alive on the OS. If the PID file is stale (process gone), delete it and re-run `construct-up`.

### 3.3 Lifecycle

- **Survives:** Claude conversation close, terminal close. Server keeps running.
- **Does not survive:** OS reboot, manual `construct-down`, process crash. User explicitly runs `construct-up` again to restart.
- **No watchdog.** A crashed server is detected next time the user runs `construct-up` or `domain-init` (stale PID handling).

### 3.4 Shutdown — `construct-down`

1. Read `views/server.pid`. If missing or stale → no-op, report "no server running."
2. Send SIGTERM to the PID. Wait up to 5s. If still alive, SIGKILL.
3. Remove `views/server.pid`.
4. Report "views server stopped."

User phrases that trigger this: *"end session"*, *"stop CONSTRUCT"*, *"shut down views"*.

---

## 4. Refresh Model — `UPDATE` Flag

### 4.1 Mechanism

On every successful `views-generate-data` run:

1. Compute `build_id` = short hash (e.g., 8-char SHA of concatenated data file digests, or just monotonic int + timestamp — implementation detail, hash preferred for determinism).
2. Write `views/build/version.json`:

   ```json
   {
     "build_id": "a3f81c2d",
     "generated_at": "2026-04-27T14:32:11Z",
     "schema_version": "0.2.0"
   }
   ```

### 4.2 Browser side

The SPA, on load, captures the current `build_id` (the one baked into the loaded data files — also exposed via the same `version.json` fetched at startup).

A small client-side worker:

- On `visibilitychange` to `visible` → fetch `/version.json` (cache-busting query param)
- Every 30s while tab is visible → fetch `/version.json`
- When `fetched.build_id !== loaded.build_id` → set a flag in shared state

A header element observes the flag and renders an **`UPDATE`** pill. Clicking it `window.location.reload()`s.

### 4.3 What this gives, what it doesn't

- ✅ User sees stale-state hint within ~30s of any data regen, without polling data files themselves
- ✅ Zero backend logic — `version.json` is a static file
- ✅ No WebSocket, no SSE, no filesystem watcher
- ❌ No live-replace of view data without reload (deferred to v0.3+)
- ❌ Browser doesn't know *what* changed, only that *something* did

---

## 5. Routing

```
/                              landing dashboard
                               - workspace switcher
                               - per-workspace status panel (papers, cards, edges, landscape preview)
                               - cross-workspace articles strip
/articles                      cross-workspace articles list
/articles/<slug>               single article (with provenance trace)
/<workspace>/                  per-workspace dashboard (PRD §4.1)
/<workspace>/knowledge-graph   PRD §4.2
/<workspace>/landscape         PRD §4.3 (per-workspace domain landscape)
/<workspace>/artifacts         PRD §4.4 (cards browser)
/<workspace>/digests           PRD §4.5 (per-workspace)
/<workspace>/digests/<id>      single digest
```

### 5.1 What's cross-workspace vs. per-workspace

| Artefact | Scope | Rationale |
|---|---|---|
| Articles | Cross | A published synthesis often draws from multiple workspaces; readers want a flat library |
| Digests | Per-workspace | Each digest is the output of one research-cycle in one workspace |
| Knowledge graph | Per-workspace | Cross-domain bridges deferred to v0.2.1 |
| Landscape | Per-workspace | Domain-internal taxonomy view |
| Artifacts (cards) | Per-workspace | Cards live in one workspace |

### 5.2 Workspace discovery

The SPA lists workspaces by reading the `domains.json` data file (Epic 2). The dashboard's workspace switcher iterates `domains.json` entries and renders a panel per workspace.

---

## 6. Landing Dashboard (`/`) — MVP Content

In order of placement on the page:

1. **CONSTRUCT header** — install name, version (from `VERSION` baked into data), generation timestamp
2. **Workspace switcher / status grid** — one panel per workspace, each showing:
   - Workspace name + status (active / paused / archived)
   - Papers (refs count), cards count (with seed/growing/mature/archived breakdown), connections (edges) count
   - Landscape thumbnail / spark — minimum: domain category coverage indicator
   - Last activity timestamp
   - Quick links: → workspace dashboard, → digests, → knowledge graph
3. **Cross-workspace articles strip** — last N published articles across all workspaces, link to `/articles`
4. **Footer** — generation timestamp, install path, view-source link

### 6.1 Deferred to v0.2.1

- **Bridges panel** — cross-domain `bridge-detect` findings on the landing page
- **Recent activity feed** — aggregated `events.jsonl` across all workspaces

These are tracked in `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` (will be re-opened after v0.2 ships).

---

## 7. Port and Process Model

### 7.1 Port allocation

```
range = 3001..3009   # 9 slots → enough for 9 simultaneous CONSTRUCT installations
                     # below 3000 is reserved (common defaults); above 3009 we fail clearly
```

Allocation algorithm in `construct-up`:

```
for port in range:
    if not in_use(port):
        return port
fail "All ports 3001–3009 in use. Stop another CONSTRUCT instance or change port range."
```

`in_use()` = OS-level bind test (try/except a TCP bind on `localhost:<port>`). Not just looking at our own PID files — other apps could be on those ports.

### 7.2 No `0.0.0.0` exposure

Server binds `127.0.0.1` only. This is non-negotiable for v0.2 — no LAN/remote access. Any cross-machine use case is a v0.3 concern.

### 7.3 PID file

- Location: `views/server.pid` (co-located with `views/build/`)
- Content: bare integer PID + newline
- Stale detection: if file exists but PID is not an alive process → treat as no-server, delete and re-bootstrap

---

## 8. Skill Map

### 8.1 New skills (v0.2)

| Skill | Purpose | Composition |
|---|---|---|
| `construct-up` | Bring up the views server for this CONSTRUCT installation | port pick → `npx serve` → write PID → report URL |
| `construct-down` | Stop the views server | read PID → SIGTERM/KILL → remove PID |
| `views-scaffold` | One-time `views/src/` setup from `design-example` | (PRD §5.4) |
| `views-generate-data` | Read workspace files, write JSON to `views/build/data/` and `views/build/version.json` | (PRD §5.1) |
| `views-build` | `npm install && npm run build` from `views/src/` to `views/build/` | (PRD §5.2) |
| `views-serve` | Low-level: start an HTTP server on `views/build/`. Used internally by `construct-up`. | wrapped by `construct-up` |

### 8.2 Modified existing skills (v0.1)

| Skill | Change | Rationale |
|---|---|---|
| `domain-init` | Add lazy `construct-up` check at start (one extra step) | Server bootstraps automatically on first domain init per the user's product framing |

All other v0.1 skills are untouched by this spec. (Hook integration that triggers `views-generate-data` after research/curation/synthesis is Epic 9, not this spec.)

---

## 9. Local → Cloud Topology — The Stable Boundary

### 9.1 Local (v0.2)

```
┌─────────────────────────────────────────────────────────────────┐
│  User's machine                                                 │
│                                                                 │
│   Claude (agent runtime, dialog) ◄─────────► Workspace files    │
│         │                                    (cards, refs,      │
│         │ runs skills:                       connections.json,  │
│         │  views-generate-data               digests/, log/)    │
│         │  views-build                              │           │
│         │                                           │ read      │
│         ▼                                           ▼           │
│   construct-up ────► localhost:3001 ────► views/build/          │
│                      (npx serve)          + version.json        │
│                          ▲                  + data/*.json       │
│                          │                                      │
│                          │                                      │
│                       Browser ◄──── reads JSON, polls version   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Cloud (v0.3+ sketch — not in scope here)

```
┌─ Cloud ─────────────────────────────┐    ┌─ User's machine ─┐
│  Claude (agent in cloud)            │    │   Browser        │
│      │                              │    └────────▲─────────┘
│      │ runs skills                  │             │
│      ▼                              │             │ HTTPS
│  Workspace storage (cloud)          │             │
│      │                              │             │
│      ▼                              │             │
│  Build pipeline ───► Static host ───┼─────────────┘
│                      (CDN / object  │
│                       storage)      │
│                      JSON + SPA     │
└─────────────────────────────────────┘
```

### 9.3 The stable boundary

What survives the local→cloud swap **unchanged**:

- The JSON data contract between agent runtime and SPA (cards.json, connections.json, etc. — Epic 2)
- The SPA itself (just receives JSON from somewhere)
- `version.json` polling protocol
- Routing model (workspace prefixes work identically with any host)

What **changes**:

- Server ownership (local process ↔ cloud host)
- Workspace location (filesystem ↔ cloud storage)
- Auth (none ↔ cloud auth)
- Transport (loopback ↔ HTTPS)

**Implication for v0.2 design:** the JSON contract (`spec-v02-data-model.md`) is the load-bearing artefact. Anything we hardcode about local filesystem paths inside the SPA pollutes the cloud-future. The SPA fetches JSON over HTTP — relative URLs only — and never assumes a workspace path.

---

## 10. Non-goals (v0.2 explicit exclusions)

- ❌ Backend API (no `/api/*` routes — only static files)
- ❌ WebSocket / SSE / live-reload
- ❌ Filesystem watcher
- ❌ Authentication / authorization
- ❌ Edit-in-browser (Claude is the only editor)
- ❌ Search-in-views (deferred per PRD §8 to v0.3)
- ❌ Dialog / agent interaction in browser (the v0.3+ horizon)
- ❌ Multi-machine / LAN access (`0.0.0.0` binding off the table)
- ❌ HTTPS (localhost only, plain HTTP is correct here)
- ❌ Graceful browser-tab handling on server stop (next request 404s — acceptable for MVP)
- ❌ `python -m http.server` as a supported run path. It does not do SPA history fallback, so client-side routes 404 on reload. If a contributor wants to poke at `views/build/` with Python for inspection, that's fine, but it is not the supported `construct-up` path and using it requires switching the SPA to `HashRouter` (rejected for UX reasons)

---

## 11. Open Follow-ups (don't block this spec)

1. **Where does `construct-up` exec the server in the user's process tree?** Detached background via `nohup`-equivalent? `setsid`? Platform differences (macOS vs. Linux)? — implementation detail for the skill author.
2. **What "stale" means for `views/build/`** — if data was regenerated but build isn't rerun, the SPA still loads old JSON. Either auto-rebuild on data change (cheap with Vite's `--watch`) or document the constraint that `views-generate-data` includes a build step. Decision deferred to Epic 5/6 implementation.
3. **Multi-CONSTRUCT discovery** — if user has 3 CONSTRUCT installs running on 3001/3002/3003, is there a "where are they?" command? Not needed for MVP. Could be a global `~/.construct/registry` later.
4. **Port 3001 vs. 3000** — convention in many docs uses 3000. We chose 3001 to leave 3000 free for the very common Node app default. Worth a one-line note in user docs.
5. **`construct-down` and orphan workspaces** — if the user `construct-down`s while a research-cycle is mid-flight, does the cycle still write data? (Yes — Claude is independent of the views server.) Worth saying so explicitly somewhere in user docs.

---

## 12. Acceptance Checks

This spec is implemented when:

- [ ] `construct-up` brings up a server on a port in 3001–3009, writes `views/server.pid`, and reports the URL
- [ ] `construct-down` stops that server cleanly and removes the PID file
- [ ] Running `construct-up` twice in the same install on different ports works (multiple users / multiple instances scenario covered by the range, not by one install starting two servers)
- [ ] `domain-init` lazily invokes `construct-up` if no server running, and skips it if one is running
- [ ] After `views-generate-data` regenerates data, the browser shows an `UPDATE` flag within 30s of tab focus
- [ ] Clicking the flag reloads and the flag clears
- [ ] Closing the Claude conversation does not stop the server
- [ ] Killing the server process (e.g., `kill -9 <pid>`) leaves a stale PID file that the next `construct-up` recovers from cleanly
- [ ] Routing layout matches §5: cross-workspace at root, per-workspace prefixed
- [ ] Landing `/` shows workspace switcher + cross-workspace articles strip with no bridges/activity panels (MVP scope)

---

## 13. References

- `prd-v02-live-views.md` §3.4 (serving), §5.3 (`views-serve`), §6.1 (event hooks)
- `adrs/adr-0002-v02-packaging.md` — places these new skills in `CONSTRUCT-CLAUDE-impl/skills/`
- `views/design-example/` — visual / nav reference
- `CONSTRUCT-CLAUDE-impl/VERSION` — read by data-generation to bake into `version.json`
