---
description: "Generate JSON data files for the views dashboard from workspace state. Use when user says 'update views', 'rebuild views data', 'refresh data'."
allowed-tools: Bash(construct views *), Bash(bash */.claude/skills/construct-views-generate-data/run.sh *)
---
# Skill: Views Generate Data

**Trigger:** User says "Update views", "Rebuild views data", "Refresh data", or similar.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** All 8 JSON contracts under `views/build/data/` per `spec-v02-data-model.md`, plus `views/build/version.json`. **Sole writer** to those locations (architecture-overview I1).
**Spec:** `CONSTRUCT-CLAUDE-spec/spec-v02-data-generation.md`
**Implementation:** the Python layer — `construct.views.generate`, reached through `construct views generate`. This skill is a CLI wrapper and holds no generator code (D-09; see [`adr-0005-views-refresh-ownership.md`](../../../../CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md)). There is no skill-local `lib/`, `generate.py`, or virtual environment to look for.

---

## Procedure

### Step 0: Resolve Install Root

The install root is the directory containing `AGENTS.md` and `.construct/`. It is **not** a single workspace: the generator aggregates every workspace discovered beneath the install root, so passing one workspace discovers zero workspaces and produces empty views.

If unsure, walk upward from the current working directory looking for `AGENTS.md`. If not found, fail with: `Not a CONSTRUCT installation: missing AGENTS.md.`

### Step 1: Verify Preconditions

`views/build/` must exist (created by `views-build`):

```bash
test -d <install-root>/views/build && echo OK || echo MISSING
```

If MISSING → fail with: `views/build/ not found. Run views-build first.`

### Step 2: Run the Generator

Invoke the CLI, either directly or through the wrapper script:

```bash
construct views generate --install-root <install-root>
```

```bash
bash <install-root>/.claude/skills/views-generate-data/run.sh <install-root>
```

The wrapper adds only a missing-argument guard and a clear failure if the `construct` executable is not on PATH; it performs no interpreter selection and no dependency bootstrap.

Capture stdout. Capture stderr.

### Step 3: Interpret Outcome

- **Exit 0 (success):** stdout carries a one-line report naming the build id, files written, validation-error count, and content-warning count, followed by any advisory warning lines. Surface it to the user (the build id and counts are the highlight). When nothing changed since the last run the generator short-circuits on its fingerprint and writes no files.
- **Exit 1 (validation errors):** the generator reports at least one validation error. Each is printed as a `✗ validation error:` line. Surface them. Do not retry; the user diagnoses.
- **Other non-zero exit:** stderr has the error. Surface it verbatim.

Content warnings are **advisory** — they describe source material, not contract violations, and do not fail the run.

### Step 4: Report

```
✓ Views data updated.
  build_id: <8-char-hex>
  files written: <N>
  warnings: <N> (or "none")

Browser will show UPDATE flag within 30s if open.
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| Build dir missing | No `views/build/` | `views/build/ not found. Run views-build first.` |
| CONSTRUCT not installed | wrapper exits 127 with `Error: the 'construct' executable is not on PATH.` | (stderr passed through; install hint included) |
| No install root given | wrapper exits 2 with a usage line | (stderr passed through) |
| Validation errors | exit 1, `✗ validation error:` lines on stdout | (surfaced verbatim) |
| Catastrophic failure | non-zero exit | (stderr passed through verbatim) |

Per-file parse errors are NOT skill failures. They are reported as content warnings and counted in the report. The run exits zero in that case.

---

## Notes

- **The implementation lives in the Python layer.** Per D-09 there is one implementation of views data generation, in `construct.views.generate`, and this skill orchestrates flow only. The views source parsers are vendored into the shipped package as `construct.views.lib`, so the generator works against an installed CONSTRUCT rather than only inside a development checkout.
- **Install-root scoped, deliberately.** The single `--install-root` option names the aggregation root. There is no workspace-scoped option; `-w` was removed rather than aliased.
- **Workflows refresh themselves.** `research.run`, `curation.run` and `daily.run` each run their own post-run views refresh in the Python layer (D-11/D-12), so a workflow does not need this skill invoked after it. This skill is for explicit user-requested refreshes.
- **Incremental regeneration.** The generator fingerprints each workspace's source files by mtime+size and short-circuits when nothing changed. Fingerprints live in `views/build/data/_build_meta.json`.
- **Sole writer to `views/build/data/`.** Architecture-overview invariant I1.
- **Determinism.** Two runs on identical workspace state produce byte-identical output (modulo `generated_at`).
- **No build invocation.** This skill does NOT run `views-build`. The two are independent writers per architecture-overview §3.2 / §4 invariants.
- **No server interaction.** Server stays running; SPA picks up fresh data on next `/version.json` poll (within 30s).
