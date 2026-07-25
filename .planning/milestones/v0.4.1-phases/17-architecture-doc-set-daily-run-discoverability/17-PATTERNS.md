# Phase 17: Architecture Doc Set & daily.run Discoverability - Pattern Map

**Mapped:** 2026-07-25
**Files analyzed:** 9 (2 new source-tree files, 1 test edit, 1 doc rewrite, 1 doc expansion, 1 doc delete, 1 doc deferrer redirect, 2 spec-line edits)
**Analogs found:** 8 / 9 (the one "no analog" is the runtime-inventory catalog section — a structural first-of-kind)

This phase is documentation-truth + one mechanical guard test + one thin skill. The two genuinely NEW files (the catalog guard and the daily skill) have strong, exact analogs already living in the tree; the rest are edits to existing files. Excerpt density below is deliberately front-loaded on the two new files.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/contract/test_artifact_catalog.py` (NEW, D-04/D-05) | test (contract guard) | introspection→assert (batch/transform) | `tests/contract/test_doc_command_references.py` | exact (reuses its helpers) |
| `CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md` (NEW, D-08) | skill spec (Layer 0) | request-response (thin delegator over CLI) | `construct-research-cycle/SKILL.md` + `construct-curation-cycle/SKILL.md` | exact (minus 2 sections) |
| `tests/contract/test_skill_migration.py` (EDIT, D-09) | test (static frontmatter guard) | file-read→assert | itself (`_MIGRATED_SKILLS` list edit) | in-place |
| `CONSTRUCT-CLAUDE-spec/architecture-overview.md` (REWRITE, DOC-01) | doc | n/a (prose) | `adrs/adr-0003-...md` (layer spine authority) | edit-in-place |
| `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` (EXPAND, DOC-02) | doc | n/a (prose) | its own existing sections + new runtime section | partial (new section = no analog) |
| `CONSTRUCT-CLAUDE-spec/config-topology.md` (DELETE, D-06) | doc | n/a | `git rm` | n/a |
| `CONSTRUCT-CLAUDE-spec/README_FIRST.md` (EDIT, D-06) | doc | n/a | deferrer redirect | edit-in-place |
| `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` (2-LINE EDIT, D-07) | doc | n/a | `:211`, `:557` line edits | edit-in-place |

---

## Pattern Assignments

### `tests/contract/test_artifact_catalog.py` (NEW — contract guard, D-04/D-05)

**Analog:** `tests/contract/test_doc_command_references.py` (FIX-04 guard). Research recommends a NEW file that *imports* this analog's helpers rather than re-implementing the Typer walk (Open Question 1, recommended). All line numbers below are in the analog.

**Reusable introspection helpers to import (do NOT re-implement):**
```python
# from tests/contract/test_doc_command_references.py
from construct.cli import app  # line 35
# _command_paths(app) → (LEAF_COMMANDS, COMMAND_GROUPS)   (lines 92-121)
# LEAF_COMMANDS, COMMAND_GROUPS, VALID_PATHS are module-level & importable (lines 120-121)
```

**Typer-walk helper shape** (analog lines 92-121) — collects leaves vs groups; the leaf/group distinction is load-bearing (34 leaves, 14 groups):
```python
def _command_paths(t_app, prefix=()):
    leaves, groups = set(), set()
    for cmd in t_app.registered_commands:
        name = cmd.name or (cmd.callback.__name__.replace("_", "-") if cmd.callback else None)
        if name:
            leaves.add(prefix + (name,))
    for group in t_app.registered_groups:
        name = group.name or (group.typer_instance.info.name if group.typer_instance else None)
        if not name or group.typer_instance is None:
            continue
        sub = prefix + (name,)
        groups.add(sub)
        sub_leaves, sub_groups = _command_paths(group.typer_instance, sub)
        leaves |= sub_leaves; groups |= sub_groups
    return leaves, groups
```

**The three OTHER introspection entry points the new guard must call** (verified live, RESEARCH Finding 4):
```python
from construct.capabilities.catalog import get_registry   # src/construct/capabilities/catalog.py:990

reg = get_registry()
reg.list()            # → list[CapabilityRecord]   LIVE COUNT = 28   (registry.py:42)
reg.list_mcp_tools()  # → list[dict]               LIVE COUNT = 22   (registry.py:55)
```
`CapabilityRecord` fields available to the guard (`src/construct/capabilities/registry.py:16-24`):
```python
@dataclass
class CapabilityRecord:
    id: str                              # e.g. "views.generate_data", "daily.run"
    ...
    cli_name: Optional[str] = None       # only 26 of 28 carry one (holdout: views/spike/tag)
    mcp_tool_name: Optional[str] = None
```
Registry accessors (`registry.py`): `register` (:31), `get` (:36), `list` (:42), `list_by_cli` (:45), `get_by_mcp_name` (:48), `list_mcp_tools` (:55).

Skills introspection (filesystem glob, no import): `CONSTRUCT-CLAUDE-impl/claude/skills/construct-*/` → 24 dirs today, 25 after this phase adds `construct-daily-cycle`. Reuse the analog's `_IMPL` / `_SKILLS_DIR` path anchors (analog lines 37-38, 303).

**Meta-guard (vacuity) pattern to copy** (analog lines 214-222) — MANDATORY per RESEARCH Pitfall 2; without it an import error makes every row-exists assertion pass trivially:
```python
def test_command_surface_is_discoverable() -> None:
    assert ("research", "run") in VALID_PATHS
    assert ("daily", "run") in VALID_PATHS
    assert ("knowledge", "card", "list") in VALID_PATHS
    assert len(VALID_PATHS) > 25
```
Mirror this for the new sources: assert `len(reg.list()) > 25`, `len(reg.list_mcp_tools()) > 20`, and a known skill dir exists — so the four `row ⊇ introspection` assertions can never go vacuous.

**Shrink-only-allowlist discipline to copy** (analog lines 173-206, 279-287): if the guard needs any "known-missing row" allowlist, model it on `_KNOWN_BROKEN` + `test_known_broken_entries_are_still_broken` — an entry may only be removed by making the row exist, never by narrowing scope. NOTE: FIX-04's `_KNOWN_BROKEN` itself must STAY EMPTY (D-09); this is a *pattern* to mirror, not that dict to touch.

**Holdout nuance to encode** (RESEARCH Finding 4, Pitfall 4; `catalog.py:344-348`): the registry (28 caps / 22 MCP) and the Typer app (34 leaves) are TWO distinct sources. Only 26 caps carry `cli_name`; the gap is views/spike/tag, which reach the CLI by an independent path (catalog.py comment: *"the `construct views generate` CLI command reaches the same function by an independent path rather than through this registry"*). Do NOT assert every Typer leaf has a registry id.

---

### `CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md` (NEW — skill spec, D-08)

**Analogs:** `construct-research-cycle/SKILL.md` and `construct-curation-cycle/SKILL.md` (thin-orchestrator template). Copy the frontmatter, migration banner, and thin-delegator body structure — then apply the TWO deliberate omissions.

**Frontmatter `allowed-tools` block to copy verbatim** (both siblings, line 3):
```yaml
---
description: "Run a full daily cycle — delegate to the Python daily.run capability, narrate the composed digest. Use when user says 'daily', 'run the daily cycle', 'catch me up', 'daily digest'."
allowed-tools: Read, Bash(construct), MCP(connect)
---
```
The `allowed-tools` value must be byte-identical to the siblings: `Read, Bash(construct), MCP(connect)` — NO `WebSearch`/`WebFetch`/`Write`/`Edit` (enforced by D-09 guard).

**Migration-banner shape to mirror** (research-cycle line 6 / curation-cycle line 6):
```markdown
> **Migrated for Phase 12 (API-04, D-08):** ... This skill is a **thin orchestrator**:
> it invokes `construct daily run`, narrates the composed result. The skill drives the
> conversation; Python enforces the contracts and owns every side effect.
```

**Invocation pattern to copy** (research-cycle lines 52-56, curation-cycle lines 34-38):
```bash
construct daily run --workspace . --json
```
```markdown
**Alternative (MCP):** invoke the `construct_daily_run` tool with `{"workspace_path": "."}`.
```

**TWO DELIBERATE OMISSIONS — do NOT copy these sibling sections:**
1. **NO interactive gate loop.** Omit the siblings' "Step: Present the Gate Queue" + "Step: Resume via Review" (research-cycle Steps 4-5 lines 60-91; curation-cycle Steps 2-3 lines 42-82). `daily.run` is NON-BLOCKING — it auto-resumes children with each gate's recommended decision (`daily_run.py:15-19`: *"a paused research/curation child is auto-resumed ... daily.run never interrupts for review"*). The skill narrates and surfaces a count; it never collects per-item decisions.
2. **NO views-refresh step.** Omit — but note the siblings do NOT have a refresh *step* either; they carry a "No views refresh step here" callout (research-cycle line 102 / curation-cycle line 115) citing `adr-0005`. The daily skill may carry the same callout for parity, but has nothing to do here (Python layer owns refresh).

**Body structure the skill SHOULD have** (D-08 shape, RESEARCH Finding 8):
1. optionally negotiate a domain focus (light version of research-cycle Step 2, lines 32-42),
2. invoke `construct daily run --workspace . --json`,
3. narrate the composed result — use `DailyRunResult` fields (`daily_run.py:98-105`): `status` (`completed`/`degraded`/`failed`), the child results (research digest, curation report), `graph.status` health summary,
4. surface `pending_escalations` (int, `daily_run.py:105`),
5. honestly point the user to `construct research review` / `construct curation review` for interactive handling on a fresh cycle.

**Validation-checklist pattern to copy** (research-cycle lines 106-113 / curation-cycle lines 119-126): a `- [ ]` checklist asserting the capability was invoked, no inline logic, report relayed with the capability's own counts, no direct workspace writes.

**Command strings that MUST resolve** (all present in live Typer app, VALID_PATHS): `construct daily run`, `construct research review`, `construct curation review`, `construct mcp`. Zero `_KNOWN_BROKEN` additions needed — the FIX-04 guard globs the skills dir automatically (`test_doc_command_references.py:42`).

---

### `tests/contract/test_skill_migration.py` (EDIT — static frontmatter guard, D-09)

**Analog:** the file itself; this is the exact same one-line enrollment Phase 16 D-14 did for `construct-synthesis`.

**The edit** — add one entry to `_MIGRATED_SKILLS` (line 37-42):
```python
_MIGRATED_SKILLS = (
    "construct-research-cycle",
    "construct-curation-cycle",
    "construct-card-evaluate",
    "construct-synthesis",
    "construct-daily-cycle",   # ← D-09 enrollment
)
```
`_FORBIDDEN_TOOLS` (line 45) `= ("WebSearch", "WebFetch", "Write", "Edit")` is unchanged. The three parametrized tests (`test_allowed_tools_text_is_not_vacuous` :77, `test_skill_drops_forbidden_tools` :95, `test_skill_still_delegates_to_cli` :101) automatically extend to the new skill; the daily skill's frontmatter must contain `Bash(construct)` and none of the forbidden tokens.

---

### `CONSTRUCT-CLAUDE-spec/architecture-overview.md` (REWRITE — DOC-01)

**Analog / authority (not a code pattern):** `adrs/adr-0003-v03-pipeline-v04-ui.md:136-150` — the canonical L0-L4 layer vocabulary to adopt as the single spine:
```text
Layer 4  UI shell (v0.5)           Forms, buttons, dashboards, review modals
Layer 3  Invoke surface            CLI (first) → MCP → HTTP  (same capability registry)
Layer 2  Python pipeline runtime   Workflows, orchestration, validation, file I/O
Layer 1  Workspace SOT             Markdown + JSON (unchanged)
Layer 0  Skill specifications      SKILL.md + artifact catalog
LLM gates (cross-cutting)          Invoked only at declared boundaries
```
Targeted edits (RESEARCH Findings 1-3): rewrite §3 (:28-89) onto this numbering, rename views cache → "derived view data" (never "Layer 2"); preserve invariants I1-I4 (:93-104), re-anchored; remove the false-writer claim at `:73` and §8.1 item 4 `:236`; repoint the five `:262` vocab citations to `CONSTRUCT-CLAUDE-impl/construct/references/`; do NOT touch the `spec-v02-data-model.md` citations at `:6, :102, :259` (D-03 — file exists). Ground truth for corrected write-ownership prose: `catalog.py:222-540` (Python runtime owns every write).

### `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` (EXPAND — DOC-02)

Existing sections (Agents :93, Workflows :105, Skills :117, Reference layer :186) stay. The NEW runtime-surface section (capabilities/CLI/MCP rows) has **no analog** — it is a structural first (see No Analog Found). Add the missing `construct-spike-run` skill row. Redirect the two config-topology deferrers (`:37`, `:262`). Counts derive from live introspection (28/34/22/25), never hand-typed.

### `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` (2-LINE EDIT — D-07)

`:211` — mark `.construct/model-routing.yaml` deprecated/inert, name `src/construct/llm/config.yaml` (already at `:209`) the LLM authority. `:557` — update the dual-config-confusion risk row to the resolved state. No code pattern; targeted prose fixes fenced here by Phase 14 D-02 / Phase 16 D-15.

### `config-topology.md` DELETE + `README_FIRST.md:74` redirect (D-06)

`git rm CONSTRUCT-CLAUDE-spec/config-topology.md` (grep-verified zero code/test refs). Redirect `README_FIRST.md:74` → `artifact-catalog.md` + `workspace-contract.md`; remove `artifact-catalog.md:37` and `:262` deferrers.

---

## Shared Patterns

### Guard-defined truth (FIX-04 discipline)
**Source:** `tests/contract/test_doc_command_references.py` (whole file, esp. lines 92-121, 214-222, 279-287)
**Apply to:** `test_artifact_catalog.py`
Derive truth from live introspection; assert doc rows ⊇ introspected surfaces; always pair with a meta-guard against vacuity; any allowlist may only shrink.

### Thin skill delegator (Layer 0 over Layer 3)
**Source:** `construct-research-cycle/SKILL.md`, `construct-curation-cycle/SKILL.md`
**Apply to:** `construct-daily-cycle/SKILL.md`
Frontmatter `allowed-tools: Read, Bash(construct), MCP(connect)`; migration banner; delegate every side effect to `construct ... run`; narrate the capability's own counts; never write to the workspace directly.

### Static frontmatter enrollment
**Source:** `tests/contract/test_skill_migration.py:37-45`
**Apply to:** the same file (add `construct-daily-cycle` to `_MIGRATED_SKILLS`).

### Live-introspection counts, never hand-typed integers
**Source:** `get_registry().list()` / `.list_mcp_tools()` (registry.py:42,55); `_command_paths(app)` (test_doc_command_references.py:92)
**Apply to:** the catalog rows and any narrative count in `artifact-catalog.md` / plan prose. Live: 28 capabilities / 34 CLI leaves / 22 MCP tools / 25 skills. NOTE the corrected capability count is **28, not the 27 in CONTEXT.md D-05** (RESEARCH Finding 4, Pitfall 1) — never hardcode 27.

## No Analog Found

| File / Section | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `artifact-catalog.md` runtime-surface section (capabilities/CLI/MCP rows) | doc | n/a | The current catalog is entirely CONSTRUCT03-audit / Claude-config shaped (agents/skills/workflows). It has NO rows for the L2/L3 Python runtime surface today — this is a structural first, not an edit of an existing table (RESEARCH Finding 5). No in-tree doc analog; planner should follow RESEARCH Finding 4's recommended guard-backed section shape (distinct new "Runtime capabilities (L2/L3)" section, per Open Question 2). |

## Metadata

**Analog search scope:** `tests/contract/`, `CONSTRUCT-CLAUDE-impl/claude/skills/`, `src/construct/capabilities/`, `src/construct/llm/`, `CONSTRUCT-CLAUDE-spec/adrs/`
**Files read for excerpts:** `test_doc_command_references.py`, `test_skill_migration.py`, `construct-research-cycle/SKILL.md`, `construct-curation-cycle/SKILL.md`, `daily_run.py`, `capabilities/catalog.py`, `capabilities/registry.py`
**Pattern extraction date:** 2026-07-25
</content>
</invoke>
