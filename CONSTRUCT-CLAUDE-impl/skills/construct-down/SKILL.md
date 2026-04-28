# Skill: Construct Down

**Trigger:** User says "End session", "Stop CONSTRUCT", "Shut down views", "Take down the views", or similar.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** Stops the running views server (started by `construct-up`); removes `views/server.pid`.
**Spec:** `CONSTRUCT-CLAUDE-spec/spec-v02-runtime-topology.md` §3.4

---

## Procedure

### Step 0: Resolve Install Root

Same as `construct-up` Step 0. The install root is the directory containing `AGENTS.md` and `.construct/`.

### Step 1: Read PID

Check for `<install-root>/views/server.pid`.

- **File missing or empty** → no server is running. Report:
  ```
  No CONSTRUCT views server is running (no PID file found).
  ```
  Exit cleanly. This is not an error.

- **File present** → read the PID (single integer, possibly with trailing whitespace).

### Step 2: Verify the PID is Alive

```bash
ps -p <pid> > /dev/null 2>&1 ; echo $?
```

- **Exit 0** (alive) → continue to Step 3.
- **Non-zero** (stale) → the recorded process is gone. Remove the stale PID file and report:
  ```
  No CONSTRUCT views server is running (PID file was stale; removed).
  ```
  Exit cleanly.

### Step 3: Stop the Process Gracefully

Send SIGTERM:

```bash
kill -TERM <pid>
```

Wait up to 5 seconds for the process to exit. Poll once per second:

```bash
for i in 1 2 3 4 5; do
  ps -p <pid> > /dev/null 2>&1 || break
  sleep 1
done
```

If the process is still alive after 5 seconds, escalate to SIGKILL:

```bash
kill -9 <pid>
```

### Step 4: Verify Process is Gone

```bash
ps -p <pid> > /dev/null 2>&1 ; echo $?
```

- **Non-zero** (gone) → continue.
- **Exit 0** (still alive after SIGKILL) → fail with:
  ```
  Could not stop server: PID <pid> survived SIGTERM and SIGKILL.
  Investigate manually: ps -p <pid>
  ```
  Do NOT remove the PID file; leave the situation diagnosable.

### Step 5: Remove PID File

```bash
rm -f <install-root>/views/server.pid
```

### Step 6: Report

```
✓ CONSTRUCT views server stopped.
  PID <pid> terminated; views/server.pid removed.
```

If the server was killed via SIGKILL (graceful TERM didn't work in time), include a note:

```
Note: server did not respond to SIGTERM within 5s; was killed with SIGKILL.
Check views/server.log if this becomes a pattern.
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` walking up | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| No server running | `views/server.pid` missing | `No CONSTRUCT views server is running (no PID file found).` |
| Stale PID | PID file present but process gone | `No CONSTRUCT views server is running (PID file was stale; removed).` |
| Process won't die | Survives both SIGTERM and SIGKILL | `Could not stop server: PID <pid> survived…` (PID file kept for diagnosis) |

---

## Notes

- **Browser tabs after shutdown:** Open browser tabs pointing at the served URL will start failing on the next request (typically with a connection-refused). This is expected — the SPA is a static site, not a long-lived connection. See spec §10 explicit non-goal.
- **Other CONSTRUCT instances:** This skill stops only the server for *this* install (whose PID is recorded in `views/server.pid` of *this* install root). Other CONSTRUCT instances on other ports are unaffected.
- **In-flight Claude work:** Stopping the views server does not affect any running Claude skills (research-cycle, curation-cycle, etc.). The workspace files remain canonical and continue to be edited by Claude even with the server down. The next `construct-up` will serve fresh data.
- **Cross-platform:** POSIX-only for v0.2. Windows kill semantics differ; not tested.
