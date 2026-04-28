# spec-v02-hook-integration — Skill Hooks for v0.2 Views

**Status:** Draft
**Date:** 2026-04-28
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 9
**Related:** `prd-v02-live-views.md` §6.1 · `spec-v02-runtime-topology.md` §3.2 · `spec-v02-data-generation.md` · `architecture-overview.md` §4

---

## 1. Scope

This spec defines **how v0.1 skills integrate with v0.2 views**, specifically:

- Which v0.1 skills trigger `views-generate-data`
- How `domain-init` lazily brings up the server via `construct-up`
- How hook failures are isolated from parent-skill success
- Concrete edits required to v0.1 skill `SKILL.md` files

It also resolves the **open question** from `prd-v02-live-views.md` §6.1 / `backlog.md` Open Questions: *"Are view-generation hooks mandatory after mutating skills, or optional behind a config flag?"*

**Out of scope:**
- The `views-generate-data` skill itself → `spec-v02-data-generation.md`
- The `construct-up` skill itself → `spec-v02-runtime-topology.md`
- Per-view UI behavior → Epic 8

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Hook mode | **Conditionally automatic.** Hooks fire when `views/build/` exists; otherwise no-op silently. No config flag for v0.2 MVP |
| Skills that hook regen | **Three:** `research-cycle`, `curation-cycle`, `synthesis`. NOT `card-create` or `card-connect` (rationale §4.4) |
| Skill that hooks bootstrap | `domain-init` — lazy `construct-up` invocation if no server is running |
| Failure isolation | A failed `views-generate-data` MUST NOT cause the parent skill to fail. Surfaces as a warning in the parent's report; the mutation that already happened in workspace files is preserved |
| Detection | Each hook checks `views/build/` exists before invoking `views-generate-data`. If absent, hook is a silent no-op |
| Config opt-out for v0.2 | None. If user doesn't want auto-regen, they don't scaffold views |
| Config opt-out for v0.2.1+ | Optional `views.auto_regenerate` field in `<install-root>/.construct/config.yaml`, default `true`. Substrate noted in §8 but not built |
| Daily-cycle workflow | Updated to mention that views are auto-updated as a side effect; user can manually request rebuild |

---

## 3. Hook Taxonomy

Two distinct kinds of hooks in v0.2:

### 3.1 Data-regeneration hooks

Fire after a skill that **mutates workspace state** (cards, connections, digests, articles). The hook runs `views-generate-data` so the SPA's cached JSON catches up.

- Affects: `views/build/data/*.json` and `views/build/version.json`
- Trigger condition: parent skill completed successfully AND `views/build/` exists
- Failure isolation: required (§5)

### 3.2 Bootstrap hooks

Fire to ensure infrastructure exists before the user expects it to. v0.2 has exactly one:

- `domain-init` lazily invokes `construct-up` if the views server is not running

This is per `spec-v02-runtime-topology.md` §3.2 — a one-liner check at the start of `domain-init`.

---

## 4. Skills That Hook Data Regeneration

### 4.1 `research-cycle`

**Why:** Produces new cards, refs, digests, sometimes connections. All of these surface in views.

**Hook point:** After Step 7 (Report) — i.e., after the digest is written and the user has been told the cycle is complete. The hook is the *very last* thing the skill does.

**Behavior:**
1. After Report step, check if `views/build/` exists at install root
2. If yes → invoke `views-generate-data` via Bash
3. If `views-generate-data` succeeds → no extra user-facing message (the SPA picks it up via `version.json` polling within 30 seconds)
4. If `views-generate-data` fails → append a warning line to the report:
   ```
   ⚠ views regeneration failed: <single-line message>. Workspace is intact;
     run `views-generate-data` manually to refresh the views.
   ```
5. Always exit with `research-cycle`'s success status (the cycle did succeed; only the side-effect failed)

### 4.2 `curation-cycle`

**Why:** Promotes/demotes cards, archives, adjusts connections, writes a curation report. All visible in views.

**Hook point:** After Step 7 (Report) — same pattern as `research-cycle`.

**Behavior:** Identical to §4.1 with `curation-cycle` substituted for `research-cycle`.

### 4.3 `synthesis`

**Why:** Writes new articles to `<workspace>/publish/`. These surface as cross-workspace `articles.json` entries with expanded provenance traces.

**Hook point:** After the publish step writes the article file. Before the skill completes.

**Behavior:** Identical to §4.1.

### 4.4 Excluded: `card-create`, `card-connect` — and why

Per the v0.2 PRD §6.1, these were originally listed as candidate hook points. v0.2 **excludes** them. Rationale:

1. **Frequency.** A `research-cycle` may create 10–30 cards plus 5–15 connections in one run. Hooking each individually fires `views-generate-data` 30+ times for a single user request — wasteful.
2. **Scope of mutation.** Within `research-cycle`, the parent skill knows it'll be ending soon and can hook once. Per-card hooks just duplicate the work the parent will do anyway.
3. **Direct invocation.** When the user invokes `card-create` or `card-connect` *directly* (outside a parent skill), they probably want the views to update. The recommended path is: user adds a "rebuild views" phrase if they want immediate freshness, or waits for the next research/curation cycle. v0.2.1 may add per-card hooks with debouncing if this proves painful.
4. **Simplicity.** Three hook points instead of five reduces the integration surface and the failure modes.

This is an explicit deviation from the PRD §6.1 list. The PRD will be patched in Epic 11 to match.

---

## 5. Failure Isolation

### 5.1 Principle

A hook is a **side effect**. It must not change the success/failure outcome of the skill that invoked it.

If `research-cycle` completed all 7 steps successfully but `views-generate-data` then errored, `research-cycle` reports **success with a warning**, not failure. The cards, connections, and digest written during the cycle are intact in the workspace; the only thing missing is the SPA's cache catch-up.

### 5.2 Mechanism

Each hook implementation:

1. Wraps the `views-generate-data` invocation in a try/catch (or shell `|| true` guard)
2. On failure, captures the single-line error message
3. Appends a warning to the parent skill's report block
4. Returns the parent skill's success status unchanged

In SKILL.md procedure terms, the hook step is structured:

```
Step N+1 (hook): Regenerate views (if present)

  - Check: does `views/build/` exist at install root?
    - No  → skip step entirely (no log line, no warning)
    - Yes → continue
  - Invoke `views-generate-data` (via Bash)
    - Exit 0 (success) → no extra output. Done.
    - Non-zero exit  → capture stderr last line.
                       Append to report: "⚠ views regeneration failed: <msg>"
                       Continue. Do NOT propagate failure.
```

### 5.3 What this prevents

- A buggy `views-generate-data` cannot lose a research cycle's output
- A disk-full error during regen doesn't roll back the canonical workspace
- A schema-version mismatch in `views/build/data/` doesn't corrupt the workspace
- The user always sees the parent skill's normal success report, with a clear marker if the side-effect didn't complete

---

## 6. Lazy Bootstrap Hook — `domain-init`

Per `spec-v02-runtime-topology.md` §3.2, `domain-init` ensures the views server is up the *first time* the user touches a domain.

### 6.1 Behavior

At the START of `domain-init` (before the existing v0.1 procedure):

```
Step 0 (bootstrap, new in v0.2): Ensure views server is running

  - Check: does `views/server.pid` exist AND is that PID an alive process?
    - Yes → skip (server is already up)
    - No  → invoke `construct-up`
            Single-line user-facing message: "Bringing up views server on http://localhost:<port>/"
            Continue with normal domain-init procedure
  - On `construct-up` failure: log warning, continue with v0.1 domain-init.
    The user can run `construct-up` manually later.
```

### 6.2 Why `domain-init` and not `workspace-init`

`workspace-init` creates the install root + `.construct/` infrastructure. At that point there are no domains yet, so there's nothing meaningful to display in the views. `domain-init` is the first time CONSTRUCT has actual content — that's the natural moment to bring up the server.

In practice, `workspace-init` and `domain-init` are usually invoked back-to-back in the cold-start flow (per `CONSTRUCT-CLAUDE-impl/workflows/cold-start.md`). The user phrase "Initialize cosmology" runs both. Putting the bootstrap in `domain-init` works for the chained call as well as for direct `domain-init` invocation later.

### 6.3 Failure isolation

Same rule as data hooks (§5). If `construct-up` fails, the user gets a warning but `domain-init` continues. The user can fix the server later (port collision, disk error, etc.) without losing the domain bootstrap work.

---

## 7. Detection of Views Presence

The hook check is one line: **`views/build/` exists at the install root**.

This is sufficient because:

- If `views/build/` doesn't exist, `views-scaffold` and `views-build` haven't run. The user is on a CLI-only workflow. Hooks correctly no-op.
- If `views/build/` exists but the server isn't running, the hook still works — it writes fresh JSON, the user can start the server later.
- If `views/build/` exists and the server is running, the hook is the full happy path.

**Not part of the check:**

- ❌ Whether `construct-up` is actively running (server lifecycle is independent of data freshness)
- ❌ Whether the SPA can render — that's the SPA's problem
- ❌ Whether prior generations succeeded — every regen is full per `spec-v02-data-generation.md` §8

---

## 8. No Config Opt-Out in v0.2

### 8.1 Position

For v0.2 MVP, hooks fire **whenever `views/build/` exists**, with no way to disable.

Rationale:
- Users who don't want hooks simply don't scaffold views
- A config flag is more surface area to maintain and document
- Hook failures don't break parent skills (§5), so the worst case is a warning line — easy to ignore if it happens
- We can add the config later without breaking compat

### 8.2 v0.2.1+ substrate (forward hook)

Should the opt-out become necessary, the hook check evolves from:

```
if (views/build/ exists) → run hook
```

to:

```
if (views/build/ exists AND config.views.auto_regenerate != false) → run hook
```

Where `config` is read from `<install-root>/.construct/config.yaml`:

```yaml
# <install-root>/.construct/config.yaml — added in v0.2.1+
views:
  auto_regenerate: true   # default; set to false to disable hooks
```

The file does not exist in v0.2. Each hook's existing presence-check is the only gating mechanism.

---

## 9. Updates Required to v0.1 Skills

Concrete edits to existing `CONSTRUCT-CLAUDE-impl/skills/*/SKILL.md` files:

| Skill | Edit |
|---|---|
| `research-cycle/SKILL.md` | Append a new step after Step 7 Report, per §4.1 / §5.2 template |
| `curation-cycle/SKILL.md` | Append a new step after Step 7 Report, per §4.2 / §5.2 template |
| `synthesis/SKILL.md` | Append a new step after the publish step, per §4.3 / §5.2 template |
| `domain-init/SKILL.md` | **Prepend** Step 0 bootstrap, per §6.1 |
| `card-create/SKILL.md` | **No edit** for v0.2 |
| `card-connect/SKILL.md` | **No edit** for v0.2 |

The edit pattern for each regen hook is the same — copy the §5.2 template, substitute the parent-skill name. No bespoke logic per skill.

### 9.1 The hook step template (paste into each regen-hooked skill)

```markdown
## Step N+1: Regenerate views (if present) — added in v0.2

This step is a side-effect that catches up the v0.2 views cache.
It does not affect the success/failure of this skill.

1. Check whether `views/build/` exists at the install root.
   - If absent → skip this step entirely. (User has not scaffolded views.)
   - If present → continue.
2. Invoke `views-generate-data` via Bash.
3. On success: no additional output.
4. On non-zero exit:
   - Capture the last line of stderr as `<msg>`
   - Append to the skill's final report:
     `⚠ views regeneration failed: <msg>. Workspace is intact;
      run views-generate-data manually to refresh the views.`
5. Return the skill's normal success status regardless of step outcome.
```

### 9.2 The bootstrap step template (paste into `domain-init/SKILL.md`)

```markdown
## Step 0: Ensure views server is running (if scaffolded) — added in v0.2

1. Check whether `views/server.pid` exists at the install root AND
   the recorded PID is a live process.
   - If yes → skip this step.
   - If no → continue.
2. Check whether `views/build/` exists.
   - If no → skip this step. (User has not scaffolded views; nothing to serve.)
   - If yes → invoke `construct-up`.
3. On `construct-up` success: emit a single line to the user:
   `Bringing up views server on http://localhost:<port>/`
4. On `construct-up` failure:
   - Append a warning to domain-init's final report:
     `⚠ views server failed to start: <msg>. Run construct-up manually
      to retry; domain initialization continues.`
5. Continue with the rest of the existing domain-init procedure.
```

---

## 10. Updates to `daily-cycle.md` Workflow

The v0.1 workflow at `CONSTRUCT-CLAUDE-impl/workflows/daily-cycle.md` orchestrates research-cycle + curation-cycle (+ optional synthesis). Updates needed:

1. **Note the auto-update.** Add a one-paragraph block: "After each step (research, curate, synthesise), the v0.2 views cache is automatically refreshed if scaffolded. The user may keep the browser tab open during the cycle; an `UPDATE` flag will appear when fresh data lands."
2. **Optional explicit rebuild.** Document the user phrase to manually rebuild views if needed (e.g., after editing a card by hand): "Rebuild views" → invokes `views-generate-data`.
3. **No structural change.** The workflow's existing steps remain unchanged. The hooks are side-effects within the existing skill calls.

The exact wording is left to the workflow file edit; this spec defines the contract.

---

## 11. Acceptance Checks

This spec is implemented when:

- [ ] `research-cycle/SKILL.md`, `curation-cycle/SKILL.md`, `synthesis/SKILL.md` each have a final step matching the §9.1 template
- [ ] `domain-init/SKILL.md` has a Step 0 matching the §9.2 template
- [ ] `card-create/SKILL.md` and `card-connect/SKILL.md` are **unchanged** by v0.2 hook integration
- [ ] Running `research-cycle` on an install **without** `views/build/` produces no hook activity (no warning, no extra log lines)
- [ ] Running `research-cycle` on an install **with** `views/build/` produces fresh data files (verifiable: `views/build/version.json` `build_id` differs from before)
- [ ] Running `research-cycle` with a deliberately broken `views-generate-data` (e.g., script renamed) produces a successful research-cycle report **plus** a single `⚠ views regeneration failed: ...` warning line — and the workspace state is unchanged from a normal successful run
- [ ] Running `domain-init` on an install with `views/build/` but no running server triggers `construct-up` and reports the URL
- [ ] Running `domain-init` after `construct-up` is already running results in **no** extra "bringing up server" message
- [ ] `daily-cycle.md` mentions the auto-update behavior and the manual-rebuild phrase

---

## 12. Open Follow-ups

1. **Per-card hooks (v0.2.1).** If `card-create` / `card-connect` direct invocation (outside parent skills) becomes common, add hooks with debouncing (e.g., min 5s between regens, batched if multiple fire in window).
2. **Hook-source detection.** v0.2 hooks fire unconditionally on parent-skill success, even if the parent ran inside another parent (e.g., daily-cycle running curation which would call its own hook). For now this redundancy is harmless (each regen is full and idempotent). v0.2.1 may add a "skill-chain depth" check to suppress redundant child hooks.
3. **Visual confirmation in user message.** §4.1 step 3 says "no extra user-facing message." Some users may want a confirmation ("✓ views updated"). Could be a config preference in v0.2.1.
4. **Server-not-up but data regenerated.** If the user runs `research-cycle` while `views/build/` exists but the server is down, `views-generate-data` writes fresh JSON to disk; nothing serves it. Reasonable behavior for v0.2 (next `construct-up` will pick it up). Document explicitly in `daily-cycle.md`.
5. **Workspace removal hook.** What happens if the user deletes a workspace directory? Currently undefined. v0.2 hooks fire only on mutation of *existing* workspaces; deletion is a pure filesystem op outside the skill graph. The next regen happens to handle this (the deleted workspace simply doesn't appear in `domains.json`). No explicit hook needed.

---

## 13. References

- `prd-v02-live-views.md` §6.1 (original hook list — five skills; this spec narrows to three)
- `spec-v02-runtime-topology.md` §3.2 (lazy `construct-up` from `domain-init`), §3.4 (`construct-down` shutdown)
- `spec-v02-data-generation.md` (the skill that hooks invoke)
- `spec-v02-build-pipeline.md` (the skills that produce `views/build/`)
- `architecture-overview.md` §4 (invariants — hooks preserve I1 single-writer, I2 read-only direction)
- `CONSTRUCT-CLAUDE-impl/skills/research-cycle/SKILL.md`, `curation-cycle/SKILL.md`, `synthesis/SKILL.md`, `domain-init/SKILL.md` — files to edit per §9
- `CONSTRUCT-CLAUDE-impl/workflows/daily-cycle.md` — file to update per §10
