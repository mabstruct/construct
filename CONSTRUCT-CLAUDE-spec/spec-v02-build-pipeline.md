# spec-v02-build-pipeline — `views-scaffold` and `views-build` Skills

**Status:** Draft
**Date:** 2026-04-28
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 6
**Related:** `spec-v02-scaffold.md` · `spec-v02-design-prototype.md` · `spec-v02-runtime-topology.md` · `architecture-overview.md` · `prd-v02-live-views.md` §5.2, §5.4

---

## 1. Scope

This spec defines the two skills that **produce the SPA artefact** that the views server hosts:

- `views-scaffold` — one-time setup of `views/src/` from the design spec
- `views-build` — repeatable Vite build producing `views/build/{index.html, assets/}`

**Out of scope:**
- `views-generate-data` (Epic 5 — produces `views/build/data/` and `version.json`)
- `construct-up` / `construct-down` (topology spec — runs the server)
- Per-view UI implementation (Epic 8)

These two skills compose with the others into the full v0.2 lifecycle:

```
                        first-time setup
views-scaffold ─────► views-build ─────► views-generate-data ─────► construct-up
(creates src/)       (builds build/)    (writes data/+version)     (starts server)

                          steady state (after a workspace mutation)
                                views-generate-data
                                (rewrites data/+version)

                          steady state (after SPA source edit, rare)
                                views-build
                                (rebuilds index.html+assets/)
```

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| `views-scaffold` invocation | One-time. Idempotent: re-running is a no-op unless `--force` flag passed |
| `views-scaffold` content source | Template directory at `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/` containing the full SPA source tree per `spec-v02-scaffold.md` |
| `views-build` invocation | Manual or chained from a higher-level skill; not auto-run by `views-generate-data` (data and build are separate writers) |
| Auto-chaining | **None in v0.2.** Each skill runs explicitly in sequence. v0.2.1 may introduce a `views-up` meta-skill that chains scaffold→build→generate-data→up |
| Stale-build detection | **Deferred to v0.2.1.** v0.2 MVP always rebuilds when `views-build` is invoked. Vite is fast enough that this is acceptable |
| `npm install` strategy | `views-build` runs `npm install` if `node_modules/` is missing or stale (lockfile changed); otherwise skips |
| `emptyOutDir: false` reliance | `views-build` MUST verify this is set in `vite.config.js` before invoking Vite — guards the two-writer invariant |
| Helper code | None required. Both skills are procedural shell wrappers around `npm` and file-copy operations |
| Failure isolation | Each skill exits non-zero on failure with a clear single-line message. Caller (Claude or user) decides whether to retry or escalate |

---

## 3. `views-scaffold` Skill

### 3.1 Purpose

Create `views/src/` (the Vite project root for the SPA) populated with:

- `package.json`, `package-lock.json` (after install), `vite.config.js`, `tailwind.config.js` (or inline), `index.html`, `jsconfig.json`, `.nvmrc`, `.gitignore`
- `public/` (initially empty)
- `src/` containing `main.jsx`, `App.jsx`, `routes.jsx`, `index.css`, `components/`, `pages/`, `hooks/`, `lib/`, `_mock/`
- All component stubs and page stubs per `spec-v02-design-prototype.md` §5
- All mock data files per `spec-v02-design-prototype.md` §8.2

### 3.2 Trigger phrases

User-facing:
- "Scaffold the views"
- "Set up the views app"
- "Initialize CONSTRUCT views"

Programmatic: invoked once during first-time CONSTRUCT installation, before `views-build`.

### 3.3 Inputs

- **Required:** Path to the CONSTRUCT installation root (the directory containing `AGENTS.md`, `.construct/`, and target `views/`). Default: current working directory.
- **Optional:** `--force` flag to overwrite an existing `views/src/`. Default: refuse if `views/src/` exists with content.

### 3.4 Procedure

1. Resolve install root. Verify `AGENTS.md` and `.construct/` exist (sanity check that this is a CONSTRUCT install).
2. Resolve target `views/src/`. If it exists and is non-empty:
   - Without `--force`: fail with `"views/src/ already exists. Use --force to overwrite."`
   - With `--force`: remove existing `views/src/` first.
3. Copy template directory `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/` to `views/src/`. The template contains every file listed in §3.1, with placeholders for any version-stamped content.
4. Substitute placeholders in copied files:
   - `{{VERSION}}` → contents of `CONSTRUCT-CLAUDE-impl/VERSION` (e.g., `0.2.0-dev`) — appears in `package.json` `"version"`
5. Run `npm install` from `views/src/`. This populates `node_modules/` and writes `package-lock.json`.
6. Verify install succeeded:
   - `views/src/node_modules/vite/` exists
   - `views/src/package-lock.json` exists
7. Report:
   ```
   ✓ Scaffolded views at <install-root>/views/src/
     Dependencies installed: <count> packages
     Next: run views-build to compile.
   ```

### 3.5 Idempotency

Re-running without `--force` is a no-op (fails with the "already exists" message). Re-running with `--force` is destructive: rebuilds from scratch. There is no merge mode — if the user has hand-edited `views/src/`, `--force` discards their edits.

This is intentional: the scaffold is the spec-derived starting point. Hand-edits should happen *after* scaffold, in the implementer's normal flow (Epic 8). The skill author should not try to preserve user edits.

### 3.6 Failure modes

| Failure | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` at root | `"Not a CONSTRUCT installation: missing AGENTS.md."` |
| `views/src/` exists | Non-empty directory check | `"views/src/ already exists. Use --force to overwrite."` |
| Template missing | `template/` directory not found in skill | `"Scaffold template missing. Reinstall CONSTRUCT-CLAUDE-impl."` |
| `npm install` fails | npm exit code ≠ 0 | `"npm install failed. See: views/src/npm-debug.log"` (do NOT auto-retry) |
| Disk full | OS error during copy | `"Scaffold failed: disk error. <message>"` |

In every failure case, the skill SHOULD attempt to leave the filesystem in a recoverable state (no half-copied scaffold). Practically: do all the copy work to a temp directory, then atomic rename. Defer to skill-author judgement on cross-platform atomicity.

### 3.7 Template directory contents

The template at `CONSTRUCT-CLAUDE-impl/skills/views-scaffold/template/` holds:

```
template/
├── package.json                  (with {{VERSION}} placeholder)
├── vite.config.js
├── jsconfig.json
├── .nvmrc                        (contents: "20")
├── .gitignore                    (node_modules, .vite, dist, build)
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── routes.jsx
    ├── index.css                 (Tailwind directives + theme tokens per design-prototype §3.1)
    ├── components/               (Layout, Header, CosmicBG, etc. — stubs from design-prototype §5)
    ├── pages/                    (10 page stubs from design-prototype §5.5, populated with mock-data imports)
    ├── hooks/                    (empty for Epic 4; Epic 8 adds useFetch, useVersionFlag)
    ├── lib/                      (empty)
    └── _mock/                    (mock JSON files from design-prototype §8.2)
```

The template is the **single source of truth** for what a fresh scaffold contains. Updating the visual contract in `spec-v02-design-prototype.md` requires updating the template. The skill itself contains no codegen logic — it only copies and substitutes placeholders.

---

## 4. `views-build` Skill

### 4.1 Purpose

Run Vite's production build, producing `views/build/{index.html, assets/}` from `views/src/`.

Critically: `views-build` MUST NOT touch `views/build/data/` or `views/build/version.json` (those are owned by `views-generate-data`). The `emptyOutDir: false` config in `vite.config.js` enforces this at the Vite level; this skill verifies it.

### 4.2 Trigger phrases

- "Build the views"
- "Rebuild views"
- "Compile views"

Programmatic: invoked after `views-scaffold` (first time), or whenever the SPA source has changed (rare in production — typical research-cycle does NOT trigger this).

### 4.3 Inputs

- **Required:** Path to the install root (same as scaffold).
- **Optional:** None for v0.2. (v0.2.1 may add `--watch` for dev mode chaining.)

### 4.4 Preconditions

- `views/src/` exists (was scaffolded)
- `views/src/package.json` is readable
- `views/src/vite.config.js` declares `build.emptyOutDir: false`

### 4.5 Procedure

1. Resolve install root.
2. Verify preconditions (§4.4). Each missing precondition is a clean failure with a directive (`"Run views-scaffold first."`).
3. Verify `vite.config.js` has `emptyOutDir: false`. Concretely: grep for `emptyOutDir:\s*false`. If absent or set to `true` → fail with `"vite.config.js must set build.emptyOutDir: false. See spec-v02-scaffold.md §6."`. This is non-negotiable — it guards invariant I3 (safe-delete) for the wrong reason.
4. Check `views/src/node_modules/`. If missing or `package-lock.json` is newer than `node_modules/`'s mtime → run `npm install` first.
5. Run `npm run build` from `views/src/`. Vite writes to `../build/` (i.e., `views/build/`) per `outDir` config.
6. Verify post-build:
   - `views/build/index.html` exists
   - `views/build/assets/` exists and has at least one `.js` file
7. Report:
   ```
   ✓ Built views to <install-root>/views/build/
     Bundle size: <kb>
     Build time: <s>
     Note: views/build/data/ and version.json (if present) were NOT touched.
   ```

### 4.6 Stale-build detection

**Deferred to v0.2.1.** v0.2 MVP always runs the full Vite build when `views-build` is invoked. Vite production build for an app this size completes in 5–15 seconds — fast enough that skip-detection earns little.

When v0.2.1 adds detection, the canonical signal will be: `views/build/_build_meta.json` storing the hash of `views/src/{src/**/*, package.json, vite.config.js, index.html}`. If unchanged → skip Vite invocation, report "already up to date."

### 4.7 Failure modes

| Failure | Detection | User message |
|---|---|---|
| Not scaffolded | No `views/src/` or no `package.json` | `"views/src/ not found. Run views-scaffold first."` |
| Wrong `emptyOutDir` | grep check (§4.5 step 3) | `"vite.config.js must set build.emptyOutDir: false. ..."` |
| `npm install` fails | npm exit code ≠ 0 | `"npm install failed. See: views/src/npm-debug.log"` |
| Vite build fails | npm run build exit code ≠ 0 | `"Vite build failed. Output:\n<last 30 lines of vite output>"` |
| Post-build verification fails | No `views/build/index.html` | `"Build completed but views/build/index.html is missing. Investigate."` |

`views-build` does NOT auto-retry on any failure. Failures surface to the caller for diagnosis.

---

## 5. Skill File Layout

Both skills live under `CONSTRUCT-CLAUDE-impl/skills/` per ADR-0002:

```
CONSTRUCT-CLAUDE-impl/skills/
├── views-scaffold/
│   ├── SKILL.md                  (procedural recipe per §3)
│   └── template/                 (full SPA source tree — §3.7)
└── views-build/
    └── SKILL.md                  (procedural recipe per §4)
```

`views-scaffold/template/` is the largest piece. It is the materialised form of every decision in `spec-v02-scaffold.md` and `spec-v02-design-prototype.md`. Maintenance rule: when those specs change, the template must be regenerated to match. The acceptance check in §7 (template matches spec) catches drift.

---

## 6. Skill Invocation Examples

### 6.1 First-time install

```
User:    "I just cloned CONSTRUCT. Set up the views."
Claude:  [runs views-scaffold]  → "Scaffolded views at ~/my-construct/views/src/. ..."
Claude:  [runs views-build]      → "Built views to ~/my-construct/views/build/. ..."
Claude:  [runs views-generate-data]  → "Wrote data for 0 workspaces."
         (No workspaces yet; data files are empty arrays per data-model spec §9.)
Claude:  [runs construct-up]     → "Server up at http://localhost:3001/"
```

### 6.2 After SPA source edit (rare)

```
User:    "I edited the Layout component. Rebuild."
Claude:  [runs views-build]      → "Built views to ... (5.2s, bundle 287kb)"
         (No regenerate-data needed; data files untouched by build.)
```

### 6.3 After research-cycle (common)

```
[research-cycle hook fires]
Claude:  [runs views-generate-data]  → "Updated data for cosmology workspace. build_id: a3f81c2d"
         (No views-build needed; SPA source unchanged.)
[browser polls version.json, sees new build_id, shows UPDATE flag]
```

The asymmetry between §6.2 and §6.3 is the architectural payoff of the two-writer split (architecture-overview §3.2 / §4 invariants).

---

## 7. Acceptance Checks

This spec is implemented when:

- [ ] `views-scaffold/SKILL.md` exists with procedure per §3.4
- [ ] `views-scaffold/template/` exists and contains every file required by §3.7
- [ ] Running `views-scaffold` on a fresh install creates `views/src/` matching `spec-v02-scaffold.md` §3
- [ ] Re-running `views-scaffold` without `--force` exits cleanly with the "already exists" message
- [ ] `views-scaffold` with `--force` rebuilds from scratch
- [ ] `views-scaffold` calls `npm install` and verifies success
- [ ] `views-build/SKILL.md` exists with procedure per §4.5
- [ ] `views-build` fails clearly when `views/src/` is missing
- [ ] `views-build` fails clearly when `vite.config.js` has `emptyOutDir: true` or omits the setting
- [ ] After `views-build`, `views/build/{index.html, assets/}` exists
- [ ] After `views-build`, any pre-existing `views/build/{data/*, version.json, server.pid}` is **untouched** (test by creating dummy files and rebuilding)
- [ ] Both skills exit non-zero on failure with a single-line summary message
- [ ] Template directory matches the spec contracts (§3.7) — drift check

---

## 8. Open Follow-ups

1. **Cross-platform atomicity** of scaffold copy. Linux/macOS atomic rename is straightforward; Windows differs. Skill author decides — for v0.2 MVP, accept "best effort" with cleanup-on-failure.
2. **Bundle size budget.** §4.5 step 7 reports bundle size but doesn't enforce a budget. Worth setting a soft limit (e.g., warn if `>1MB` total)? Defer to Epic 10 (validation).
3. **Vite version pin** in template. Currently `^8.0.0` per scaffold spec. Caret allows minor upgrades — possible breakage. Worth pinning exact version (`8.0.0`)? Trade-off: stability vs. security patches. Recommendation: caret for v0.2; revisit if it bites.
4. **`--force` confirmation.** v0.2 takes `--force` at face value. Should the skill prompt the user via an LLM-mediated confirmation before destructive action? Probably yes — but spec leaves UX detail to skill author.
5. **Template versioning.** When the spec changes and template is updated, existing v0.2 installations have an *older* scaffold. Migration story is undefined. For v0.2 MVP, accept that re-scaffolding is the only update path.
6. **`views-build` watch mode** for development. Vite has `vite build --watch`. Could be useful when implementing Epic 8. Defer to Epic 8 implementer's choice; not part of skill contract.

---

## 9. References

- `spec-v02-scaffold.md` — directory layout, deps, vite config, scripts (everything the template materialises)
- `spec-v02-design-prototype.md` — visual contract that the component/page stubs in the template implement
- `spec-v02-runtime-topology.md` §3.1 (`construct-up`'s precondition that `views/build/` exists), §10 (no chained build for v0.2)
- `architecture-overview.md` §3.2, §3.3 (two-writer invariant), §4 (the four invariants)
- `prd-v02-live-views.md` §5.2 (`views-build`), §5.4 (`views-scaffold`)
- `adrs/adr-0002-v02-packaging.md` — places these skills in `CONSTRUCT-CLAUDE-impl/skills/`
- `CONSTRUCT-CLAUDE-impl/VERSION` — substituted into `package.json` at scaffold time
