# Skill: Construct Up

**Trigger:** User says "Start CONSTRUCT", "Show me the views", "Bring up views", "Open the views", or similar. Also lazily chained from `domain-init` if no views server is running.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** A running views server on `localhost:<port>` (port in 3001–3009), `views/server.pid` recording the process ID, URL reported to user.
**Spec:** `CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md` §3.1

---

## Procedure

### Step 0: Resolve Install Root

The install root is the directory containing `AGENTS.md` and `.construct/`. All paths below are relative to this root.

If unsure, walk upward from the current working directory looking for `AGENTS.md`. If not found, fail with: `Not a CONSTRUCT installation: missing AGENTS.md.`

### Step 1: Pre-flight Checks

Verify these in order. Fail fast on any missing precondition.

1. **`views/build/index.html` exists.** If missing:
   - Fail with: `views/build/ not found or empty. Run views-build first (or views-scaffold + views-build for a fresh install).`
2. **`views/build/version.json` exists.** Optional but recommended. If missing, log a one-line warning and continue: `Note: views/build/version.json not found — UPDATE flag won't function until views-generate-data has run at least once.`
3. **No server already running for this install.** Check `views/server.pid`:
   - If file exists AND the recorded PID is a live process AND that process is bound to a port in 3001–3009 → fail with: `Server already running at http://localhost:<port>/ (PID <pid>). Use construct-down to stop, then re-run.`
   - If file exists but PID is stale (process gone) → delete the stale `views/server.pid` and continue.

### Step 2: Pick a Free Port

Try ports 3001 through 3009 in order. For each, run:

```bash
lsof -iTCP:<port> -sTCP:LISTEN -n -P 2>/dev/null
```

The first port that produces empty output is free. Use it.

If all 9 ports are occupied, fail with: `All ports 3001–3009 are in use. Stop another CONSTRUCT instance (or non-CONSTRUCT process) and retry.`

### Step 3: Start the Server (detached)

Invoke the `serve` binary **directly** (not via `npm run serve`) so the recorded PID is the actual server process — clean SIGTERM in `construct-down`, no process-group dance.

```bash
cd <install-root>/views/src
nohup ./node_modules/.bin/serve ../build --single -l <port> > <install-root>/views/server.log 2>&1 < /dev/null &
echo $!
```

Capture the PID printed by `echo $!`. This IS the `node` process running `serve` — single process, no wrapper, no parent.

Why direct invocation rather than `npm run serve`:
- `npm run` adds an `sh -c` wrapper layer around `serve`; the captured PID is `npm`, not `serve`
- SIGTERM to npm doesn't always propagate to the child (depends on npm version + signal handling)
- Direct invocation: PID = serve, SIGTERM works deterministically

The flags `--single` (SPA history fallback) and `-l <port>` (listen on chosen port) are non-negotiable. `../build` is relative to `views/src/` per the `package.json` `serve` script — keep it in sync if either path changes.

### Step 4: Verify the Server Started

Wait briefly (~1.5 seconds), then verify:

1. The PID is still alive:
   ```bash
   ps -p <pid> > /dev/null 2>&1 ; echo $?
   ```
   Exit code 0 → alive. Non-zero → server died on startup.

2. The port is now bound:
   ```bash
   lsof -iTCP:<port> -sTCP:LISTEN -n -P 2>/dev/null
   ```
   Non-empty → bound. Empty → server not yet listening.

If either check fails, read the last 30 lines of `<install-root>/views/server.log` and surface them as the failure cause:

```
Server failed to start. Last log lines:
<last 30 lines of views/server.log>
```

Then attempt to kill the PID (best effort) and remove any half-written PID file.

### Step 5: Write PID File

```bash
echo <pid> > <install-root>/views/server.pid
```

The PID file contains a single integer plus a trailing newline. `construct-down` reads this to know what to kill.

### Step 6: Report

Output to the user:

```
✓ CONSTRUCT views server running.
  URL: http://localhost:<port>/
  PID: <pid>
  Log: <install-root>/views/server.log

Stop the server with: "End session" / "Stop CONSTRUCT" / construct-down
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` walking up | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| Build missing | `views/build/index.html` absent | `views/build/ not found or empty. Run views-build first…` |
| Already running | `views/server.pid` is alive | `Server already running at http://localhost:<port>/…` |
| Port exhaustion | All 3001–3009 in use | `All ports 3001–3009 are in use…` |
| Server died on startup | PID not alive after wait | `Server failed to start. Last log lines:\n<…>` |
| Port not bound | PID alive but port unbound | `Server started but isn't listening. Last log lines:\n<…>` |

---

## Notes

- **Cross-platform:** This procedure assumes a POSIX shell (macOS / Linux). Windows behavior is untested in v0.2.
- **No auto-restart:** If the server crashes after a successful start, this skill does not detect it. The next `construct-up` invocation handles the stale PID file. See spec §3.3.
- **No port persistence:** The chosen port is recorded only in the running server's binding (visible via `lsof`) and implicitly in the running process. The next `construct-up` may pick a different free port.
- **`UPDATE` flag dependency:** Once the server is up, the SPA polls `/version.json` for `build_id` changes (per topology spec §4). For this to function, `views-generate-data` must have run at least once. The skill logs a warning if `version.json` is missing but does not block startup.
- **Logs location:** `<install-root>/views/server.log` is overwritten on each start. Move/rename if you need to preserve a prior log.
