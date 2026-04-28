# Skill: Views Generate Data

**Trigger:** User says "Update views", "Rebuild views data", "Refresh data", or similar. Also fired automatically by hook integration after `research-cycle`, `curation-cycle`, `synthesis` per `spec-v02-hook-integration.md` §4.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** All 8 JSON contracts under `views/build/data/` per `spec-v02-data-model.md`, plus `views/build/version.json`. **Sole writer** to those locations (architecture-overview I1).
**Spec:** `CONSTRUCT-CLAUDE-spec/spec-v02-data-generation.md`

---

## Procedure

### Step 0: Resolve Install Root

The install root is the directory containing `AGENTS.md` and `.construct/`. All paths below are relative to this root.

If unsure, walk upward from the current working directory looking for `AGENTS.md`. If not found, fail with: `Not a CONSTRUCT installation: missing AGENTS.md.`

### Step 1: Verify Preconditions

`views/build/` must exist (created by `views-build`):

```bash
test -d <install-root>/views/build && echo OK || echo MISSING
```

If MISSING → fail with: `views/build/ not found. Run views-build first.`

### Step 2: Verify Python + PyYAML Available

The helper script needs Python 3.10+ and PyYAML.

```bash
python3 -c "import sys; assert sys.version_info >= (3, 10)" || echo "BAD_PYTHON"
python3 -c "import yaml" || echo "MISSING_YAML"
```

- If `BAD_PYTHON` → fail with: `Python 3.10+ required. Install or upgrade Python.`
- If `MISSING_YAML` → fail with: `PyYAML missing. Run: pip install pyyaml`

For installations that prefer a virtualenv, the `.construct/` directory may host one — adapt the python invocation accordingly.

### Step 3: Run the Generator

Execute the helper script:

```bash
python3 <install-root>/.construct/skills/views-generate-data/generate.py <install-root>
```

Capture stdout. Capture stderr.

### Step 4: Interpret Outcome

- **Exit 0 (success):** stdout has a structured report:
  ```
  workspaces: 2
    cosmology: 47 cards, 184 connections, 12 digests, 3 articles
    climate-policy: 23 cards, 41 connections, 5 digests, 1 article
  global: 4 articles total
  build_id: a3f81c2d
  warnings: 1 (cosmology/cards/orphaned-finding-2026-04-12.md: missing required field 'epistemic_type')
  ```
  Surface this to the user verbatim (or summarised — count of cards/digests/build_id is the highlight).
- **Exit non-zero (failure):** stderr has a single-line error message. Surface it. Do not retry; the user diagnoses.

### Step 5: Report

```
✓ Views data updated.
  build_id: <8-char-hex>
  workspaces: <N>
  warnings: <N> (or "none")

Browser will show UPDATE flag within 30s if open.
```

---

## Failure-mode Reference

| Trigger | Detection | User message |
|---|---|---|
| Not in a CONSTRUCT install | No `AGENTS.md` | `Not a CONSTRUCT installation: missing AGENTS.md.` |
| Build dir missing | No `views/build/` | `views/build/ not found. Run views-build first.` |
| Bad Python | Version <3.10 | `Python 3.10+ required.` |
| Missing PyYAML | `import yaml` fails | `PyYAML missing. Run: pip install pyyaml` |
| Script catastrophic | Non-zero exit | (stderr passed through verbatim) |

Per-file parse errors are NOT skill failures. They are logged to `views/build/data/_generation-warnings.log` by the script and counted in the report. The skill exits zero in this case.

---

## Notes

- **Sole writer to `views/build/data/`.** Architecture-overview invariant I1. Hook-fired regenerations (research-cycle, curation-cycle, synthesis) all flow through this skill.
- **Determinism.** Two runs on identical workspace state produce byte-identical output (modulo `generated_at`). Verified by safe-delete invariant I3 in validation.
- **Failure isolation.** Per-file errors do not stop the run. The script writes whatever parsed cleanly and surfaces warnings. The agent's parent skill (research-cycle, etc.) is unaffected by views-generate-data warnings.
- **No build invocation.** This skill does NOT run `views-build`. The two are independent writers per architecture-overview §3.2 / §4 invariants.
- **No server interaction.** Server stays running; SPA picks up fresh data on next `/version.json` poll (within 30s).
