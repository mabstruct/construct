# Skill: Views Build

**Trigger:** User says "Build the views", "Rebuild views", "Compile views", or similar. Invoked after `views-scaffold` (first time), or whenever the SPA source has changed (rare).
**Agent:** CONSTRUCT (orchestrator)
**Produces:** `views/build/index.html` and `views/build/assets/` (Vite output). Does NOT touch `views/build/data/` or `views/build/version.json` — those are owned by `views-generate-data`.
**Spec:** `CONSTRUCT-CLAUDE-spec/spec-v02-build-pipeline.md` §4

---

## Procedure

### Step 0: Resolve Install Root

The install root is the directory containing `AGENTS.md` and `.construct/`. All paths below are relative to this root.

If unsure, walk upward from the current working directory looking for `AGENTS.md`. If not found, fail with: `Not a CONSTRUCT installation: missing AGENTS.md.`

### Step 1: Verify Preconditions

Three checks. Fail fast on any miss.

1. **`views/src/` is scaffolded:**
   ```bash
   test -f <install-root>/views/src/package.json && \
   test -f <install-root>/views/src/vite.config.js && echo OK || echo MISSING
   ```
   If MISSING → fail with: `views/src/ not found or not scaffolded. Run views-scaffold first.`

2. **`vite.config.js` declares `emptyOutDir: false`:**

   This is **non-negotiable** — without it, Vite would wipe `views/build/data/` and `views/build/version.json` on every build, breaking the two-writer architecture (architecture-overview §3.3 / §4 invariant I3).

   ```bash
   grep -E 'emptyOutDir\s*:\s*false' <install-root>/views/src/vite.config.js && echo OK || echo BAD
   ```

   If BAD → fail with:
   ```
   vite.config.js must declare build.emptyOutDir: false to preserve
   views/build/data/ and version.json across rebuilds. See spec-v02-scaffold.md §6.
   ```

3. **Template-version match (soft check):**
   Read `<install-root>/.construct/VERSION` and compare to the `version` field in `views/src/package.json`. Mismatches are non-fatal but worth a one-line warning:
   ```
   ⚠ views/src/ was scaffolded for version <X>; current is <Y>.
     Re-run views-scaffold --force to refresh the scaffold.
   ```
   This is informational; the build proceeds.

### Step 2: Ensure Dependencies Are Installed

Check `node_modules/`:

```bash
test -d <install-root>/views/src/node_modules/vite && echo HAVE_DEPS || echo MISSING_DEPS
```

- **HAVE_DEPS** → skip to Step 3.
- **MISSING_DEPS** → run install:
  ```bash
  cd <install-root>/views/src && npm install
  ```
  If install fails → fail with the npm error.

Optional sanity: if `package-lock.json` mtime is newer than `node_modules/.package-lock.json` mtime, package-lock has been touched since the last install — re-run `npm install`. This catches dependency drift across team members. (For solo use, this almost never triggers.)

### Step 3: Run Vite Build

```bash
cd <install-root>/views/src
npm run build
```

Capture stdout + stderr. Vite emits a structured success summary:

```
vite v7.x.x building for production...
✓ N modules transformed.
../build/index.html                   X.XX kB
../build/assets/index-XXXXXXXX.css    X.XX kB
../build/assets/index-XXXXXXXX.js     X.XX kB
✓ built in Xms
```

If Vite exits non-zero → fail with the last 30 lines of build output:
```
Vite build failed. Last output:
<last 30 lines>
```

### Step 4: Post-Build Verification

Verify the artefacts are in place:

```bash
test -f <install-root>/views/build/index.html && \
test -d <install-root>/views/build/assets && \
test -n "$(ls <install-root>/views/build/assets/*.js 2>/dev/null)" && \
echo OK || echo INCOMPLETE
```

If INCOMPLETE → fail with: `Build completed but views/build/index.html or assets/*.js is missing. Investigate.`

Verify that `views/build/data/` and `views/build/version.json` (if they were present before) survived. Either capture mtimes pre/post or compare contents — for MVP a simple existence check suffices:

```bash
# Pre-build: record what was there
PRE_DATA=$(test -d <install-root>/views/build/data && echo YES || echo NO)
PRE_VER=$(test -f <install-root>/views/build/version.json && echo YES || echo NO)

# (run vite build)

# Post-build: verify nothing was lost
POST_DATA=$(test -d <install-root>/views/build/data && echo YES || echo NO)
POST_VER=$(test -f <install-root>/views/build/version.json && echo YES || echo NO)

[ "$PRE_DATA" = "$POST_DATA" ] && [ "$PRE_VER" = "$POST_VER" ] && echo INVARIANT_OK || echo INVARIANT_BROKEN
```

If `INVARIANT_BROKEN` (data/ or version.json existed pre-build but not post) → fail loudly:
```
INVARIANT VIOLATION: views/build/data/ or version.json was deleted by the build.
This indicates emptyOutDir is misconfigured. Inspect vite.config.js immediately.
```

This protects against silent regressions in the vite config.

### Step 5: Report

Compute approximate bundle size from the build output:

```
✓ Built views to <install-root>/views/build/
  Bundle: <total-kb>kb gzipped
  Build time: <Xms>
  Modules transformed: <count>
  Note: views/build/data/ and version.json (if present) were preserved.
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| Not scaffolded | No `views/src/package.json` | `views/src/ not found or not scaffolded. Run views-scaffold first.` |
| Wrong `emptyOutDir` | grep check fails | `vite.config.js must declare build.emptyOutDir: false…` |
| `npm install` fails | Exit code ≠ 0 | `npm install failed. See output above.` |
| Vite build fails | `npm run build` exit ≠ 0 | `Vite build failed. Last output:\n<…>` |
| Missing post-build outputs | `index.html` or `assets/` not found | `Build completed but views/build/index.html…` |
| INVARIANT VIOLATION | data/ or version.json disappeared | `INVARIANT VIOLATION: views/build/data/…` |

---

## Notes

- **No auto-retry.** Failures surface to the caller for diagnosis.
- **No data regeneration.** This skill does NOT run `views-generate-data`. The two are independent writers (architecture-overview §3.2). To refresh data, the user invokes `views-generate-data` or triggers a v0.1 skill that hooks it (research-cycle, curation-cycle, synthesis).
- **No server start.** This skill does NOT invoke `construct-up`. After build, the user explicitly starts the server (or the SPA tab is reloaded against an already-running server).
- **Stale-build detection deferred** to v0.2.1. Currently always rebuilds when invoked. Vite is fast enough that this is acceptable.
- **Cross-platform:** Tested on macOS. Linux compatible. Windows untested in v0.2.
