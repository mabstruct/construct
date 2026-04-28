# Skill: Views Scaffold

**Trigger:** User says "Scaffold the views", "Set up the views app", "Initialize CONSTRUCT views", or similar. Typically invoked once per CONSTRUCT installation, before `views-build`.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** A populated `views/src/` directory (Vite + React + Tailwind project) with all dependencies installed.
**Spec:** `CONSTRUCT-CLAUDE-spec/spec-v02-build-pipeline.md` §3

---

## Procedure

### Step 0: Resolve Install Root

The install root is the directory containing `AGENTS.md` and `.construct/`. All paths below are relative to this root.

If unsure, walk upward from the current working directory looking for `AGENTS.md`. If not found, fail with: `Not a CONSTRUCT installation: missing AGENTS.md.`

### Step 1: Resolve Template Source

The scaffold template lives at:

```
<install-root>/.construct/skills/views-scaffold/template/
```

Verify it exists:

```bash
test -d <install-root>/.construct/skills/views-scaffold/template && echo OK || echo MISSING
```

If missing → fail with: `Scaffold template missing at .construct/skills/views-scaffold/template/. Reinstall the CONSTRUCT skill set.`

### Step 2: Check Existing `views/src/`

```bash
test -e <install-root>/views/src && echo EXISTS || echo CLEAN
```

- **If `views/src/` does not exist** → continue.
- **If `views/src/` exists and is empty** → continue (treat as clean).
- **If `views/src/` exists and is non-empty AND `--force` was NOT passed** → fail with:
  ```
  views/src/ already exists. Use --force to overwrite.
  ```
- **If `views/src/` exists and `--force` was passed** → remove it:
  ```bash
  rm -rf <install-root>/views/src
  ```
  Note: `--force` is destructive. The skill caller should confirm with the user before passing it. The skill itself does not prompt.

### Step 3: Copy Template

Use `cp -a` (archive mode) to preserve permissions and copy hidden files (`.nvmrc`, `.gitignore`):

```bash
mkdir -p <install-root>/views
cp -a <install-root>/.construct/skills/views-scaffold/template/. <install-root>/views/src/
```

The trailing `/.` in the source path is required to copy directory contents (including dotfiles) rather than the directory itself.

Verify the copy:

```bash
test -f <install-root>/views/src/package.json && \
test -f <install-root>/views/src/vite.config.js && \
test -f <install-root>/views/src/index.html && \
test -d <install-root>/views/src/src && \
test -f <install-root>/views/src/.nvmrc && \
echo COPY_OK || echo COPY_INCOMPLETE
```

If anything is missing, fail with: `Template copy incomplete. Check filesystem permissions and disk space.` Then attempt to remove the partial `views/src/` (best effort).

### Step 4: Substitute `{{VERSION}}` Placeholder

The template's `package.json` contains `"version": "{{VERSION}}"`. Replace this with the contents of `<install-root>/.construct/VERSION` (or `<install-root>/VERSION` if `.construct/VERSION` doesn't exist — fall back to `0.2.0-dev`).

```bash
VERSION=$(cat <install-root>/.construct/VERSION 2>/dev/null || cat <install-root>/VERSION 2>/dev/null || echo "0.2.0-dev")
sed -i.bak "s/{{VERSION}}/$VERSION/" <install-root>/views/src/package.json
rm -f <install-root>/views/src/package.json.bak
```

The `-i.bak` form is portable across macOS (BSD sed) and Linux (GNU sed). The `.bak` file is removed immediately.

Verify substitution:

```bash
grep -q "{{VERSION}}" <install-root>/views/src/package.json && echo NOT_SUBSTITUTED || echo OK
```

If `NOT_SUBSTITUTED`, fail with: `VERSION substitution failed. Check sed availability.`

### Step 5: `npm install`

```bash
cd <install-root>/views/src
npm install
```

This typically takes 30–90s for a fresh install (depends on network, npm cache state). Capture exit code.

Verify install succeeded:

```bash
test -d <install-root>/views/src/node_modules/vite && \
test -f <install-root>/views/src/package-lock.json && \
echo INSTALL_OK || echo INSTALL_FAILED
```

If `INSTALL_FAILED` → fail with: `npm install failed. See output above for npm errors.` Do NOT auto-retry; surface the error so the user can diagnose.

### Step 6: Report

Count installed packages from the npm install output (the `added X packages` line). Report:

```
✓ Scaffolded views at <install-root>/views/src/
  Template: .construct/skills/views-scaffold/template/
  Version: <VERSION>
  Dependencies installed: <count> packages
  Next: run `views-build` to compile, then `construct-up` to serve.
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` walking up | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| Template missing | `template/` directory not found | `Scaffold template missing… Reinstall the CONSTRUCT skill set.` |
| `views/src/` already exists | Non-empty directory check | `views/src/ already exists. Use --force to overwrite.` |
| Template copy incomplete | Required files missing post-copy | `Template copy incomplete…` |
| `{{VERSION}}` not substituted | grep finds placeholder after sed | `VERSION substitution failed…` |
| `npm install` fails | Exit code ≠ 0 OR `node_modules/vite` missing | `npm install failed. See output above for npm errors.` |

---

## Notes

- **Idempotency:** Re-running without `--force` is a no-op (fails fast with the "already exists" message). Re-running with `--force` is destructive: the existing `views/src/` is removed before re-scaffold. Hand-edits made to `views/src/` since the last scaffold are LOST. The skill author (CONSTRUCT itself or the user) should confirm before passing `--force`.
- **Network requirement:** `npm install` requires network the first time. Subsequent invocations on the same machine may use the npm cache and run fully offline.
- **Cross-platform:** Tested on macOS. Linux compatible (commands used are POSIX). Windows untested in v0.2.
- **VERSION fallback:** If neither `.construct/VERSION` nor `<install-root>/VERSION` exists, defaults to `0.2.0-dev`. This matches the v0.2 development phase. Future installations should always have a `VERSION` file.
- **What this skill does NOT do:**
  - Run `views-build` — that's a separate skill, invoked next
  - Run `construct-up` — that's the third step
  - Touch any workspace files — only `views/` is affected
