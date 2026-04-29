# Skill: Views Reset

**Trigger:** User says "Reset the views", "Wipe views state", "Clean views runtime", or similar.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** A clean slate for views — removes runtime artefacts so the next `views-scaffold` → `views-build` → `views-generate-data` → `construct-up` chain starts from zero state. **Never touches workspace data, the skill set, or the design-example reference.**

---

## Procedure

### Step 0: Resolve Install Root

The install root is the directory containing `AGENTS.md` and `.construct/`. All paths below are relative to this root.

If unsure, walk upward from the current working directory looking for `AGENTS.md`. If not found, fail with: `Not a CONSTRUCT installation: missing AGENTS.md.`

### Step 1: Enumerate What Will Be Deleted (Print First)

This is a **fixed allowlist**. The skill must NEVER touch any path outside this list — no glob iteration, no recursion beyond what's named here.

```
<install-root>/views/src/
<install-root>/views/build/
<install-root>/views/server.pid
<install-root>/views/server.log
<install-root>/.construct/skills/views-generate-data/.venv/
```

Print the plan to the user verbatim before any deletion:

```
About to remove (views runtime only — research data is preserved):
  • views/src/                                               (Vite project root)
  • views/build/                                             (compiled SPA + generated data)
  • views/server.pid                                          (server PID file, if present)
  • views/server.log                                          (server log, if present)
  • .construct/skills/views-generate-data/.venv/             (per-skill Python venv)

NOT touched:
  • All workspace directories (cosmology/, philosophy-of-mind/, …)
  • .construct/ skill set + workflows + references + templates
  • AGENTS.md
  • views/design-example/                                     (visual reference)
```

### Step 2: Stop the Server (if running)

Same logic as `construct-down`:

1. Read `views/server.pid`. If missing or empty → skip.
2. Verify the PID is alive (`ps -p <pid>`). If stale → just remove the file.
3. If alive: `kill -TERM <pid>`, poll once per second for up to 5 seconds.
4. If still alive after 5s: `kill -9 <pid>`.
5. Remove `views/server.pid`.

If the process can't be killed (rare — survives both SIGTERM and SIGKILL), fail with: `Could not stop server: PID <pid> survived SIGTERM and SIGKILL. Investigate manually before resetting.`

### Step 3: Remove the Allowlisted Paths

Execute the deletions in order. Each is independent — failure of one shouldn't prevent the others, but log each failure clearly.

```bash
rm -rf <install-root>/views/src
rm -rf <install-root>/views/build
rm -f  <install-root>/views/server.log
rm -rf <install-root>/.construct/skills/views-generate-data/.venv
```

(`server.pid` was already removed by Step 2 if it existed.)

For any `rm` that fails with permission error or other OS error, capture and surface the specific failure. Do not silently swallow.

### Step 4: Verify

After deletion, confirm nothing in the allowlist remains:

```bash
for p in views/src views/build views/server.pid views/server.log .construct/skills/views-generate-data/.venv; do
  test -e "<install-root>/$p" && echo "STILL PRESENT: $p"
done
```

If any path "STILL PRESENT" survives, fail loudly and tell the user.

### Step 5: Report

```
✓ Views reset.
  Removed (or already absent):
    • views/src/
    • views/build/
    • views/server.log
    • .construct/skills/views-generate-data/.venv/
    (server stopped + PID file removed if it was running)

  Preserved:
    • All workspace research data
    • .construct/ skill set
    • AGENTS.md
    • views/design-example/

  Next: "Scaffold the views" to set up fresh, then build → update views → start CONSTRUCT.
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` walking up | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| Server won't die | Survives SIGTERM and SIGKILL | `Could not stop server: PID <pid> survived…` (PID file kept) |
| `rm` permission denied | OS error | `Could not remove <path>: <error>. Check permissions.` |
| Partial delete | Some paths still present after Step 3 | `Reset incomplete; some paths remain: <list>` |

---

## Notes

- **Idempotent.** Re-running on an already-reset install is a clean no-op (nothing to remove). Safe to run repeatedly.
- **Scope is narrow by design.** The fixed allowlist in Step 1 is the contract. To wipe other things (e.g., refresh skills, remove a workspace), use the appropriate other tool — `refresh-construct.sh` for skill updates, manual `rm` for workspace removal (with care!).
- **Per-skill venv removal forces fresh bootstrap** on the next `views-generate-data` invocation. ~5s extra one-time cost. Worth it for "test newly arrived skillset free from side-effects" — old PyYAML version or stale interpreter state can't carry over.
- **NOT a fresh-install replacement.** This does NOT recreate `~/my-construct` from scratch. `.construct/`, `AGENTS.md`, and your workspaces remain. To rebuild from scratch: `rm -rf ~/my-construct` then `setup-construct.sh ~/my-construct` (DESTRUCTIVE — loses workspaces too).
- **Browser tabs.** If you have a tab open against the server, the next request after server shutdown will fail (connection refused). After re-running the chain, reload the tab — the SPA fetches fresh data because the bundle hash changed.
- **Hand-edits to `views/src/`** are LOST on reset. Same posture as `views-scaffold --force`. If you have local SPA changes you want to keep, copy them out first.
