# Phase 17: Architecture Doc Set & daily.run Discoverability - Research

**Researched:** 2026-07-25
**Domain:** Documentation-truth reconciliation + mechanical guard test + thin Claude skill (existing CONSTRUCT codebase; doc/test archaeology, not web research)
**Confidence:** HIGH (all findings verified against the live working tree with file:line evidence)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** ADR-0003's runtime stack (L0 skill specs → L1 workspace SOT → L2 Python runtime → L3 invoke surface → L4 UI) becomes the single canonical "Layer N" vocabulary in `architecture-overview.md`. The views cache is renamed **"derived view data"** (never "Layer 2"). Invariants I1–I4 survive intact, re-anchored to the workspace-SOT / derived-view-data relationship.
- **D-02:** Remove the false "skills are the only legitimate writers to layer 1" claim (`architecture-overview.md:73` and §8.2 decision-tree item 4 `:236`). Make the Python runtime's write-ownership visible. Exact prose is Claude's discretion; recommended leaning: "Layer 2 (the Python runtime) owns every write to layer 1; skills, CLI, MCP, and the future UI reach it only by invoking registered capabilities through the invoke surface."
- **D-03:** `spec-v02-data-model.md` **EXISTS and is KEPT** — the audit mis-named it. Its citations at `:6, :102, :259` are load-bearing (do not delete). The genuinely-broken references are the **five vocab-doc citations at `architecture-overview.md:262`**. Researcher must run a full resolve-sweep of the entire architecture doc set (done — see below).
- **D-04:** `artifact-catalog.md` gets a NEW mechanical guard (e.g. `tests/contract/test_artifact_catalog.py`) asserting catalog rows match live introspection of registry + Typer app + MCP tool list.
- **D-05:** Guard asserts at minimum capabilities (registry) + CLI leaves (Typer walk) + MCP tools. Skills coverage recommended (catches missing `construct-spike-run` row). Search-spine and LLM-gate rows stay narrative. **Retire stale figures** — catalog reflects live introspection, never a hand-typed integer.
- **D-06:** `config-topology.md` is **DELETED** and its deferrers redirected (`README_FIRST.md`, `artifact-catalog.md`). Redirect targets: workspace-contract.md (workspace artifacts), artifact-catalog.md (capability/CLI/MCP inventory), architecture-overview.md (layer/deployment model). Do not edit sealed planning docs/milestone audit.
- **D-07:** Fix `spec-v04-agentworkflows.md:211` and `:557` (last stale model-routing references in the live spec tree). Mark `model-routing.yaml` deprecated/inert, name `llm/config.yaml` authority; update the dual-config-confusion risk row to the resolved state.
- **D-08:** New thin `construct-daily-cycle` skill: `allowed-tools: Read, Bash(construct), MCP(connect)` — NO WebSearch/WebFetch/Write/Edit. **NO gate loop, NO views-refresh step** (both deliberate per Phase 13 non-blocking design + Phase 15 D-11). Shape: negotiate domain focus → `construct daily run --workspace . --json` → narrate composed result → surface pending-escalation count → point user to `construct research review` / `construct curation review`.
- **D-09:** Enroll `construct-daily-cycle` in `tests/contract/test_skill_migration.py`'s `_MIGRATED_SKILLS`. Its `construct …` strings must pass the FIX-04 guard with **zero `_KNOWN_BROKEN` additions**.
- **D-10:** UX-01 criterion 5 (no-parent-graph decision durably recorded) is **ALREADY SATISFIED** by `PROJECT.md` Key Decisions (Phase 13 D-09 row). Optional reinforcement in the rewritten `architecture-overview.md` is natural but not required.

### Claude's Discretion
- D-02's exact prose for the layer-1 write-ownership framing.
- D-05's exact guard coverage beyond capabilities+CLI+MCP (skills recommended; `construct-spike-run` row mandatory).
- Whether the catalog guard is a **new** `tests/contract/test_artifact_catalog.py` or an extension of `test_doc_command_references.py`'s helpers.
- `daily-cycle.md` workflow doc treatment (keep it; skill references it; update diagram only if trivial — see Finding 8, it is already accurate).
- Wave ordering / plan decomposition across DOC-01 / DOC-02 / UX-01.
- Whether ROADMAP/REQUIREMENTS stale premises are corrected here or flagged for the milestone audit.
- The `construct-daily-cycle` skill's exact procedure wording and description/trigger phrasing.

### Deferred Ideas (OUT OF SCOPE)
- RT-01/RT-02 registry unification for views/spike/tag (catalog shows views as registry holdout honestly; unification is v0.6).
- Thin-wrapper migration for `construct-bridge-detect` / `construct-domain-init` / `construct-search-adjust` (v0.6; only the new daily skill is migrated here).
- Actually deleting `model-routing.yaml` from `REQUIRED_PATHS`/loader/fixtures (workspace-format change, v0.5+).
- Event-vocabulary reconciliation (conflict C4) — no overlap with DOC-01/DOC-02 edits; do not touch.
- Rewriting `prd.md` / `development-strategy.md` (stale but not load-bearing).
- `views validate` accepting exact `views generate` bytes (Phase 15 open contract question; not a Phase 17 gray area).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **DOC-01** | `architecture-overview.md` shows the four/five-layer ADR-0003 model incl. the Python runtime layer; no "skills are the only writers to layer 1" claim; no broken doc references. | Finding 1 (resolve sweep: only the five `:262` vocab links broken; spec-v02-data-model.md verified present), Finding 2 (ADR-0003 layer model text), Finding 3 (the two false-claim offenders located). |
| **DOC-02** | `artifact-catalog.md` becomes an honest, staleness-proofed inventory with rows for every capability/CLI/MCP tool/skill (incl. `construct-spike-run`), backed by a mechanical guard; `config-topology.md` corrected or deleted. | Finding 4 (introspection contract + live counts), Finding 5 (catalog structure gap: no capability/CLI/MCP rows today), Finding 6 (config-topology delete + deferrer map), Finding 7 (spec-v04 fence). |
| **UX-01** | A user can reach `daily.run` from Claude-native chat through a skill; no-parent-graph decision recorded durably. | Finding 8 (thin sibling-skill template, daily_run.py design, migration guard enrollment, daily-cycle.md workflow doc), D-10 (already satisfied in PROJECT.md). |
</phase_requirements>

## Summary

This is a **documentation-truth + guard-test + thin-skill** phase over the existing CONSTRUCT codebase. Every CONTEXT.md decision is already locked; the research task was to surface the concrete, evidence-backed facts that make each decision executable. All findings are verified against the live working tree.

Three headline facts a planner must internalize:

1. **The doc-set resolve-sweep is clean except for exactly five links.** Across the entire architecture doc set (`architecture-overview.md`, `artifact-catalog.md`, `README_FIRST.md`, `config-topology.md`, `spec-v04-agentworkflows.md`, `data-schemas.md`, `nfrs.md`, and their sibling cross-tree citations), every markdown/file citation **RESOLVES** except the five vocabulary-doc citations at `architecture-overview.md:262`. `spec-v02-data-model.md` genuinely exists (D-03 confirmed) and all five ADRs including `adr-0005` resolve. The DOC-01 "broken references" work is therefore small and precisely bounded.

2. **The catalog guard is the durable deliverable, and the catalog needs a structural expansion, not a row edit.** `artifact-catalog.md` today is a **Claude-config inventory** (agents/skills/workflows/references/templates) with a CONSTRUCT03 audit framing — it contains **no rows for capabilities, CLI commands, or MCP tools at all**. DOC-02 criterion 2 requires adding those. The introspection API is known and reusable; the live counts are **28 capabilities / 34 CLI leaves / 22 MCP tools / 24 skill dirs** — note the capability count is **28, not the 27 stated in CONTEXT.md D-05** (see Finding 4, flagged for the planner).

3. **The daily skill is a thin non-blocking wrapper with two deliberate omissions.** It mirrors `construct-research-cycle` / `construct-curation-cycle` (`allowed-tools: Read, Bash(construct), MCP(connect)`) but has **no interactive gate loop** and **no views-refresh step** — both are design constraints, not oversights. The `daily-cycle.md` workflow doc is already accurate and current; the skill can simply reference it.

**Primary recommendation:** Decompose into three plans aligned to the requirements — (A) DOC-01 architecture-overview rewrite, (B) DOC-02 catalog expansion + guard + config-topology deletion + spec-v04 fence, (C) UX-01 daily skill + migration-guard enrollment. Build the catalog guard by **extending `test_doc_command_references.py`'s introspection helpers** (reuse `_command_paths`, `from construct.cli import app`, `get_registry()`), and keep every count in the catalog derived from live introspection so it cannot rot.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Architecture-doc layer narrative (DOC-01) | Documentation (spec tree) | — | Prose describing ADR-0003's L0–L4 runtime stack; no code change. |
| Catalog inventory rows (DOC-02) | Documentation (spec tree) | Test tier (guard) | The rows are doc content; the guard that keeps them honest lives in `tests/contract/`. |
| Catalog guard (D-04/D-05) | Test tier (`tests/contract/`) | Python runtime (introspection sources) | Asserts doc-vs-introspection contract against `catalog.py` registry, `cli.py` Typer app, MCP tool list, skills glob. |
| config-topology deletion + redirects (D-06) | Documentation (spec tree) | — | File removal + citation repointing; no runtime state (verified: nothing in `src/`/`tests/` imports it). |
| daily skill (UX-01) | Layer 0 (skill spec) | Layer 3 invoke surface (`construct daily run`) | Thin orchestrator SKILL.md delegating to the Python `daily.run` capability via CLI/MCP. |
| daily skill forbidden-tools enrollment (D-09) | Test tier (`tests/contract/`) | — | Static frontmatter guard extension. |

## Finding 1 — Doc-Set Resolve Sweep (D-03, MANDATORY)

**Method:** Enumerated every markdown link and backtick file-citation across the architecture doc set and resolved each against the on-disk tree. `[VERIFIED: filesystem]`

**Result: exactly ONE broken reference cluster in the entire architecture doc set — the five vocab docs at `architecture-overview.md:262`.**

### Broken references (turn into edit tasks)

| Citation (as written) | Location | Status | Real on-disk location | Fix |
|-----------------------|----------|--------|----------------------|-----|
| `references/epistemic-types.md` | `architecture-overview.md:262` | **BROKEN** (no `CONSTRUCT-CLAUDE-spec/references/` dir exists) | `CONSTRUCT-CLAUDE-impl/construct/references/epistemic-types.md` | Repoint to real relative path; note these are workspace-shipped vocab docs (ship to `.construct/references/`). |
| `connection-types.md` | `architecture-overview.md:262` | **BROKEN** | `CONSTRUCT-CLAUDE-impl/construct/references/connection-types.md` | as above |
| `lifecycle-states.md` | `architecture-overview.md:262` | **BROKEN** | `CONSTRUCT-CLAUDE-impl/construct/references/lifecycle-states.md` | as above |
| `confidence-levels.md` | `architecture-overview.md:262` | **BROKEN** | `CONSTRUCT-CLAUDE-impl/construct/references/confidence-levels.md` | as above |
| `source-tiers.md` | `architecture-overview.md:262` | **BROKEN** | `CONSTRUCT-CLAUDE-impl/construct/references/source-tiers.md` | as above |

`[VERIFIED: filesystem]` — `ls CONSTRUCT-CLAUDE-spec/references/` → *No such file or directory*; all five exist under `CONSTRUCT-CLAUDE-impl/construct/references/`.

### D-03 confirmation: `spec-v02-data-model.md` EXISTS — do NOT delete its citations

`[VERIFIED: filesystem]` — `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md` present (25,298 bytes, dated May 9 — predates the July 19 audit that mis-flagged it). Its citations at `architecture-overview.md:6`, `:102` (anchors invariant I4's per-field derivation traceability), and `:259` all point at a real file and are **KEPT**.

### Everything else in the architecture doc set RESOLVES

`[VERIFIED: filesystem]` — spot-resolved the cross-tree/relative citations:
- All five ADRs (`adr-0001`…`adr-0005`) resolve; `adr-0005-views-refresh-ownership.md` exists.
- `artifact-catalog.md` cross-tree links: `capabilities.md`, `commands.md`, `AGENTS.md`, `../CONSTRUCT-CLAUDE-v03-planning/README.md` — all resolve.
- `README_FIRST.md` / `data-schemas.md` links (`workspace-contract.md`, `../archive/v01-python/spec/…`) — resolve.
- `spec-v02-runtime-topology.md`, `spec-v02-data-model.md` — resolve.

**Out-of-scope non-doc-link note:** `spec-v04-agentworkflows.md:210` references `src/construct/search/config.yaml` (marked "(new)") which does **not** exist on disk `[VERIFIED: filesystem]`. This is a *planned config path*, not a markdown doc link, and is outside D-07's `:211`/`:557` fence — do not fix it here; flag it for the milestone audit if desired.

## Finding 2 — ADR-0003 Layer Model (the D-01 canonical spine)

`architecture-overview.md` must adopt this verbatim numbering from `adr-0003-v03-pipeline-v04-ui.md:136–150` `[VERIFIED: file read]`:

```text
Layer 4  UI shell (v0.5)           Forms, buttons, dashboards, review modals
Layer 3  Invoke surface            CLI (first) → MCP → HTTP  (same capability registry)
Layer 2  Python pipeline runtime   Workflows, orchestration, validation, file I/O
Layer 1  Workspace SOT             Markdown + JSON (unchanged)
Layer 0  Skill specifications      SKILL.md + artifact catalog (procedure + audit)
LLM gates (cross-cutting)          Invoked only at declared boundaries
```

**Key reconciliation the rewrite must perform (D-01):**
- The current doc's §3 "The Three Layers" is a *data-flow* story: L1 canonical state → **L2 derived state (views cache)** → L3 presentation (SPA). ADR-0003's **L2 = Python pipeline runtime**, NOT the views cache. These two "Layer 2"s are the confusion DOC-01 exists to remove.
- Adopt ADR-0003's L0–L4 as THE spine. Re-express the one-way data-flow narrative + invariants I1–I4 as **properties within/across those layers**. Rename the views cache **"derived view data"** so exactly one "Layer N" vocabulary survives.
- Invariants I1–I4 (`architecture-overview.md:93–104`) stay intact — re-anchor them to the workspace-SOT ↔ derived-view-data relationship. Note I4's test text references `spec-v02-data-model.md` (`:102`) — that citation is KEPT (D-03).

## Finding 3 — The two false-claim offenders (D-02)

`[VERIFIED: file read]` Exact locations to fix:
- **`architecture-overview.md:73`** — "Edits to layer 1 happen exclusively through Claude… Skills like `card-create`, `card-edit`, `research-cycle`, `curation-cycle` write to workspace files." (False post-v0.4.)
- **`architecture-overview.md:236`** — §8.1 decision-tree item 4: "Skills are the only legitimate writers to layer 1." (The named false claim.)
- Also review `:39` ("Edited only by Claude (via skills…)") and `:81` (single-writer-to-layer-2 prose) for consistency with the renamed "derived view data."

**Ground truth (for the corrected prose):** the Python capability runtime owns every write. `catalog.py` registers 28 capabilities whose handlers call `services/knowledge.py` (`create_card`, `edit_card`, `archive_card`, `add_connection`), `research_run`, `curation_run`, `daily_run`, etc. `[VERIFIED: catalog.py:222–540]`. Skills are thin wrappers that delegate via `construct …` CLI/MCP (Phase 12 API-04; see the `construct-research-cycle`/`construct-curation-cycle` migration banners). Recommended framing per D-02 is acceptable as written.

## Finding 4 — Catalog Guard Introspection Contract & Live Counts (D-04/D-05)

**The exact introspection API the new guard must call** `[VERIFIED: live import + execution]`:

| Surface | Introspection call | Import path | Live count |
|---------|--------------------|-------------|------------|
| Registered capabilities | `get_registry().list()` → `list[CapabilityRecord]` | `from construct.capabilities.catalog import get_registry` | **28** |
| MCP tools | `get_registry().list_mcp_tools()` | same | **22** |
| CLI leaf commands | `_command_paths(app)` → `(LEAF_COMMANDS, COMMAND_GROUPS)` | `from construct.cli import app`; reuse helper in `tests/contract/test_doc_command_references.py:92` | **34 leaves** (14 groups) |
| Skills | glob `CONSTRUCT-CLAUDE-impl/claude/skills/construct-*/` | filesystem | **24 dirs** (→ 25 after adding `construct-daily-cycle`) |

`CapabilityRecord` fields available to the guard `[VERIFIED]`: `id, name, description, input_model, output_model, handler, cli_name, mcp_tool_name`. Registry accessors: `get`, `get_by_mcp_name`, `list`, `list_by_cli`, `list_mcp_tools`, `register`.

**⚠️ COUNT DISCREPANCY — flag for the planner:** CONTEXT.md D-05 states "27 capabilities". **Live `get_registry().list()` returns 28** `[VERIFIED: executed]`. There are 28 `registry.register(` calls / 28 unique ids in `catalog.py` (workspace.init … daily.inspect). The 34 CLI-leaf and 22 MCP figures **match** D-05; only the capability figure is off by one (28, not 27). Because D-05 mandates the catalog reflect *live introspection, never a hand-typed integer*, the guard is self-correcting — but any narrative count written in the catalog prose or a plan must use **28**, and the planner should not hardcode 27 anywhere.

**Registry-holdout nuance (Phase 15 D-03) the catalog must represent honestly:** only **26 of 28** capabilities carry a `cli_name`; there are **34** Typer leaves. The gap is the **views/spike/tag** command groups, which are NOT registry-routed (`catalog.py:344–348` explicitly notes `construct views generate` reaches the generator by an independent path; RT-01/RT-02 stay open). So the guard must treat the registry (28 caps / 22 MCP) and the Typer app (34 leaves) as **two distinct introspection sources** and the catalog must not imply views/spike/tag route through the registry.

**Reusable asset (Don't Hand-Roll):** `test_doc_command_references.py:92 _command_paths(t_app, prefix)` already walks the Typer app recursively and separates leaves from groups. `LEAF_COMMANDS`, `COMMAND_GROUPS`, `VALID_PATHS` are module-level and importable. Do not re-implement a Typer walk.

**Recommended guard shape (satisfies D-05 mandatory floor + recommended skills coverage):**
- Assert every `get_registry().list()` id has a catalog row (28).
- Assert every `list_mcp_tools()` entry has a catalog row (22).
- Assert every Typer leaf (`LEAF_COMMANDS`, 34) is represented, distinguishing registry-routed from holdout.
- Assert every `construct-*` skill dir has a catalog row (catches `construct-spike-run`, the criterion-named missing row, and future additions).
- Keep search-spine and LLM-gate rows present but NOT asserted (narrative, per D-05).
- Add a meta-guard (mirror `test_command_surface_is_discoverable` at `:214`) so the introspection can never silently return an empty set and make the suite vacuous.

## Finding 5 — Catalog Structure Gap (DOC-02, scope reality)

`[VERIFIED: full read of artifact-catalog.md]` The current catalog is organized entirely around Claude-native config artifacts:
- Agents (2) — `:93`
- Workflows (3) — `:105`
- Skills (**"23"** hand-typed) — `:117` (lists 23; disk has 24 — **`construct-spike-run` is the missing row**, criterion 2 confirmed)
- Reference layer (5 enums + commands + capabilities) — `:186`
- Hooks & side effects — `:202`
- CONSTRUCT03 audit matrix — `:65`, `:215`

**There are NO rows for the Python runtime surface** — no capabilities, no CLI commands, no MCP tools. DOC-02 criterion 2 requires adding them ("rows for every registered capability, CLI command, and MCP tool… plus the search spine, the LLM gates"). This is a **structural expansion** (a whole new inventory section for the L2/L3 runtime), not a count fix on an existing table. The planner should budget accordingly.

The hand-typed "Skills (23)" and "5 enums" counts become guard-checked once the daily skill (→ 25 dirs) and the new capability/CLI/MCP rows land.

## Finding 6 — config-topology.md Deletion & Deferrer Map (D-06)

`[VERIFIED]` `config-topology.md` is dated 2026-04-23 and stale across all three sections:
- §1 skills tree (`:22–38`) shows top-level `skills/` with un-prefixed names (`research-cycle` not `construct-research-cycle`) and omits `src/construct/`.
- §3 comparison table (`:132–133`) marks `views/` and `db/` "❌ not needed" — false now (views generate; `adr-0004` sanctions workflow SQLite).
- (It already partially absorbed FIX-02: `:56`/`:135` mark `model-routing.yaml` DEPRECATED — but the file is deleted anyway.)

**Safe to delete** `[VERIFIED]`: `grep -rn "config-topology" src/ tests/` → no matches. Nothing in code/tests imports or references it. Its three roles are already owned by milestone-corrected docs (workspace artifacts → `workspace-contract.md`; capability/CLI/MCP inventory → `artifact-catalog.md`; layer/deployment model → `architecture-overview.md`). Model-routing deprecation truth already lives in `workspace-contract.md:78` and `nfrs.md:72`.

**Deferrers to redirect (the complete live spec-tree set)** `[VERIFIED: grep]`:

| File:line | Current reference | Action |
|-----------|-------------------|--------|
| `README_FIRST.md:74` | table row "Directory layout of `CONSTRUCT-CLAUDE-impl/`" → `config-topology.md` | Redirect to `artifact-catalog.md` (config layers) + `workspace-contract.md`; or remove the row. |
| `artifact-catalog.md:37` | "Related documents" row → `config-topology.md` (Directory layout — partially outdated) | Remove the row (the catalog now owns this). |
| `artifact-catalog.md:262` | Maintenance step 6 "Update `config-topology.md` if directory layout changes" | Remove step 6 (nothing to update after deletion). |
| `config-topology.md:82` | self-reference inside the file being deleted | Moot — file removed. |

Planning docs (`ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`, `STATE.md`, `CONCERNS.md`, milestone audit) record the *decision* and are **not** deferrers to rewrite. Do not edit the sealed `v0.4-MILESTONE-AUDIT.md`.

## Finding 7 — spec-v04 Model-Routing Fence (D-07)

`[VERIFIED: file read]` The last two stale model-routing references in the live spec tree:
- **`spec-v04-agentworkflows.md:211`** — config-surfaces table: `.construct/model-routing.yaml (workspace) | Cognitive tier documentation; must not duplicate provider secrets`. Mark it deprecated/inert; name `src/construct/llm/config.yaml` (already listed at `:209`) as the LLM config authority.
- **`spec-v04-agentworkflows.md:557`** — Risks table row: "Dual config confusion (`model-routing.yaml` vs `search.yaml` vs `llm/config.yaml`) … validation warns on conflict". Update to the resolved state (model-routing deprecated per Phase 14 D-01/D-02; `llm/config.yaml` authoritative).

Bundle with the DOC-02 config work (single plan). These crossings were explicitly deferred here by Phase 14 D-02 and Phase 16 D-15.

## Finding 8 — Thin daily-cycle Skill Template (D-08/D-09)

**Sibling template** `[VERIFIED: construct-curation-cycle/SKILL.md + construct-research-cycle/SKILL.md]`:
- Frontmatter: `allowed-tools: Read, Bash(construct), MCP(connect)` (identical in both siblings; matches the `spec-v04:220` migration pattern).
- Structure: migration banner → Prerequisites (`construct mcp &`) → Procedure (invoke `construct <cap> run --workspace . --json`, MCP alternative) → narrate report → Validation checklist.
- Both siblings carry a "**No views refresh step here**" callout citing `adr-0005` (Phase 15 D-11). The daily skill must carry the same.

**The two deliberate omissions vs the siblings (do NOT copy these in):**
1. **NO interactive gate loop.** `daily_run.py:1–30` `[VERIFIED]`: daily.run is NON-BLOCKING (D-01) — it auto-resumes paused research/curation children with each gate's *recommended* decision via `review_*_run(approve_all=True)`, never interrupts for review, and surfaces escalate items as a **pending-escalation count**. The siblings' Step 2/Step 3 approve/reject gate loop must be absent.
2. **NO views-refresh step.** The `daily.run` capability and its children regenerate views in the Python layer (adr-0005). The skill has nothing to do here.

**Recommended skill procedure (per D-08):** (1) optionally negotiate a domain focus → (2) `construct daily run --workspace . --json` (MCP: `construct_daily_run` tool with `{"workspace_path": "."}`) → (3) narrate the composed result (research digest, curation report, `graph.status` health summary) → (4) surface the pending-escalation count → (5) honestly point the user to `construct research review` / `construct curation review` for interactive handling of pending items on a fresh cycle.

**daily-cycle.md workflow doc (discretion):** `[VERIFIED: full read]` It is **already accurate and current** — it invokes `construct daily run --workspace . --json` (`:38`), describes the non-blocking single-pass design (`:41`), carries the no-views-refresh callout (`:99`), and its overview diagram (`research-cycle → curation-cycle → graph-status → [user interaction]`, `:28`) correctly reflects the composition. The skill can simply reference it; **no edit is required** (D-08's "update the diagram if trivial" is effectively a no-op).

**D-09 enrollment** `[VERIFIED: test_skill_migration.py]`:
- Add `"construct-daily-cycle"` to `_MIGRATED_SKILLS` at `test_skill_migration.py:37` (currently 4 entries: research-cycle, curation-cycle, card-evaluate, synthesis).
- `_FORBIDDEN_TOOLS` at `:45` = `("WebSearch", "WebFetch", "Write", "Edit")` — the daily skill's `allowed-tools` must contain none of these and must contain `Bash(construct)` (asserted by `test_skill_still_delegates_to_cli` at `:101`).
- The FIX-04 doc-command guard (`test_doc_command_references.py`) already globs the skills dir (`_DOC_GLOBS` first entry, `:42`), so the daily skill's `construct …` strings are scanned automatically. All strings it will use — `construct daily run`, `construct research review`, `construct curation review`, `construct mcp` — resolve against the live Typer app `[VERIFIED: VALID_PATHS contains ('daily','run'); test asserts it at :218]`. **Zero `_KNOWN_BROKEN` additions** required (the dict is currently empty at `:201` and must stay empty).

## Architecture Patterns

### Pattern 1: Guard-defined truth (extend, don't reinvent)
**What:** A contract test that derives truth from live introspection and fails when the doc drifts. **When:** DOC-02 catalog guard. **How:** import `get_registry()` + `test_doc_command_references` helpers; assert doc rows ⊇ introspected surfaces; include a meta-guard against vacuity. Mirror the shrink-only allowlist discipline of FIX-04.

### Pattern 2: Thin skill delegator (Layer 0 over Layer 3)
**What:** A SKILL.md that owns conversation only and delegates all side effects to `construct …` CLI/MCP. **When:** the daily skill. **How:** copy the sibling frontmatter and banner; delete the gate loop and views-refresh sections.

### Anti-Patterns to Avoid
- **Two "Layer N" vocabularies** — the exact confusion DOC-01 removes. After the rewrite, "Layer 2" must mean only the Python runtime; the views cache is "derived view data."
- **Hand-typing counts into the catalog** — resets the rot clock. Counts must be guard-checked against live introspection (D-05). Do not write "27" (or even "28") as a frozen integer the guard doesn't enforce.
- **Mirroring the sibling skills wholesale** — reintroduces a gate loop that contradicts daily.run's non-blocking design (D-08 specifics note).
- **Deleting `spec-v02-data-model.md` citations** — the audit mis-named it; it exists (D-03).
- **Implying views/spike/tag route through the registry** — they are the recorded holdout (Phase 15 D-03).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Typer command enumeration | A fresh recursive Typer walk | `test_doc_command_references._command_paths(app)` / `LEAF_COMMANDS` | Already handles leaf-vs-group distinction correctly (`:92–121`). |
| Capability enumeration | Parsing `catalog.py` source | `get_registry().list()` | Authoritative live records with typed fields. |
| MCP tool enumeration | Reading `mcp/server.py` | `get_registry().list_mcp_tools()` | Server auto-discovers from the registry; never hand-edited. |
| Skill-frontmatter parsing | A YAML dependency | `test_skill_migration._allowed_tools_text()` | Handles both inline and list dialects (`:48–73`); just add the skill to `_MIGRATED_SKILLS`. |

## Runtime State Inventory

This phase deletes one doc file and repoints citations; it stores no runtime state. All five categories verified:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no datastore keys reference `config-topology.md` or the doc contents. | None. |
| Live service config | None — docs are not consumed by any running service. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | None — model-routing deprecation is doc-only; `model-routing.yaml` itself is NOT deleted this phase (deferred). | None. |
| Build artifacts / installed packages | None — `grep -rn config-topology src/ tests/` returns nothing; no import, no packaged reference, no golden fixture. | None (safe to `git rm` the doc). |

## Common Pitfalls

### Pitfall 1: Hardcoding the "27" capability count
**What goes wrong:** CONTEXT.md D-05 says 27; live is 28. A plan or catalog row written to "27" is born stale. **Avoid:** derive from `get_registry().list()`; if a narrative sentence must state a number, state 28 and let the guard enforce it.

### Pitfall 2: The catalog guard going vacuous
**What goes wrong:** If introspection returns an empty set (import error, renamed accessor), every `row-exists` assertion passes trivially. **Avoid:** add a meta-guard asserting `len(caps) > 25`, `('daily','run') in VALID_PATHS`, etc. — exactly the pattern at `test_doc_command_references.py:214`.

### Pitfall 3: Reintroducing a gate loop in the daily skill
**What goes wrong:** Copying the sibling Step 2/Step 3 approve/reject loop contradicts daily.run's non-blocking auto-resume design. **Avoid:** the daily skill narrates and surfaces a count; it never collects per-item decisions. **Warning sign:** the skill's `allowed-tools` or prose implies a resume/decision step.

### Pitfall 4: Treating registry and Typer as one source
**What goes wrong:** Asserting all 34 CLI leaves must have registry ids fails on views/spike/tag (the holdout). **Avoid:** two independent introspection sources; the catalog marks holdouts explicitly.

## Validation Architecture

Nyquist validation is **ENABLED** (`.planning/config.json` → `workflow.nyquist_validation: true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing; suite ≈515 passed / 1 skipped at Phase 16 close) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/contract/test_artifact_catalog.py tests/contract/test_skill_migration.py tests/contract/test_doc_command_references.py -x` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map
| Req / Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------------|----------|-----------|-------------------|-------------|
| DOC-02 / D-04 / D-05 | Catalog rows match live registry (28), MCP (22), Typer leaves (34), skills (25 incl. spike-run) | contract | `pytest tests/contract/test_artifact_catalog.py -x` | ❌ Wave 0 (new guard) |
| DOC-02 / D-05 | `construct-spike-run` has a catalog row | contract | `pytest tests/contract/test_artifact_catalog.py -k spike -x` | ❌ Wave 0 |
| UX-01 / D-09 | daily skill drops forbidden tools, keeps `Bash(construct)` | contract | `pytest tests/contract/test_skill_migration.py -x` | ✅ (extend `_MIGRATED_SKILLS`) |
| UX-01 / D-09 | daily skill's `construct …` strings all resolve; `_KNOWN_BROKEN` empty | contract | `pytest tests/contract/test_doc_command_references.py -x` | ✅ (auto-scans skills glob) |
| DOC-01 | No broken doc links; no false-writer claim; single layer vocabulary | manual + grep | `grep -n "only legitimate writers" CONSTRUCT-CLAUDE-spec/architecture-overview.md` (must be empty); manual link check of the five `:262` refs | grep automatable; prose = manual review |
| DOC-02 / D-06 | `config-topology.md` deleted; no live spec-tree deferrer remains | grep | `test ! -e CONSTRUCT-CLAUDE-spec/config-topology.md && ! grep -rn config-topology CONSTRUCT-CLAUDE-spec/` | grep automatable |
| DOC-02 / D-07 | spec-v04:211/:557 no longer present model-routing as live authority | grep/manual | `grep -n "model-routing" CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` → each hit deprecated-framed | automatable + manual |

### Sampling Rate
- **Per task commit:** the quick-run contract subset.
- **Per wave merge:** `pytest -q` (full suite; expect green, count grows vs the ~515 anchor — not a regression).
- **Phase gate:** full suite green + the DOC-01/DOC-02/DOC-06/DOC-07 grep assertions all pass, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/contract/test_artifact_catalog.py` — NEW guard (or an extension block inside `test_doc_command_references.py` reusing its helpers) covering registry/MCP/CLI/skills. Covers DOC-02 D-04/D-05.
- [ ] `test_skill_migration.py::_MIGRATED_SKILLS` — add `"construct-daily-cycle"` (one-line edit).
- [ ] No framework install needed (pytest present).

*The D-04/D-05 catalog guard IS the flagship validation mechanism; its assertion targets are the four introspection sources in Finding 4.*

## Environment Availability

Purely code/doc/test changes over the existing repo; no new external tools/services/runtimes. `pytest` and the `construct` CLI are already installed in `.venv` `[VERIFIED: live import + introspection executed]`. No missing dependencies, no fallbacks required.

## Security Domain

Not applicable in substance. This phase touches documentation prose, a contract test, a skill spec, and a file deletion — no authentication, session, access-control, cryptography, or new input-parsing surface is introduced. The one adjacent security-relevant fact is *preserved, not created*: `daily_run.py` already kebab-validates `run_id` against path traversal (`daily_run.py:28–29`) and sanitizes child errors — the new skill only invokes the capability and must not add any tool (`Write`/`Edit`) that could write outside the delegation boundary, which D-09's forbidden-tools guard mechanically enforces.

## State of the Art

| Old (in current docs) | Current (this phase installs) | Why |
|-----------------------|-------------------------------|-----|
| architecture-overview §3 three-layer data-flow model, no Python runtime | ADR-0003 L0–L4 runtime stack as the single layer vocabulary | DOC-01; the doc must describe the system that exists post-v0.4. |
| "Skills are the only legitimate writers to layer 1" | Python runtime (L2) owns writes; skills delegate via invoke surface | Phase 12 API-04 / adr-0005 reality. |
| Hand-typed catalog counts ("23 skills") | Guard-checked live introspection (28 caps / 34 CLI / 22 MCP / 25 skills) | D-04/D-05 anti-rot. |
| `config-topology.md` (2026-04-23, stale) | Deleted; roles owned by workspace-contract / artifact-catalog / architecture-overview | D-06. |
| `model-routing.yaml` as live LLM authority | `llm/config.yaml` authoritative; model-routing deprecated/inert | Phase 14 D-01/D-02; D-07 propagates the last spec-tree refs. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Full pytest suite is currently green and the ~515-test anchor holds (not re-run in this research session; taken from REQUIREMENTS.md traceability). | Validation Architecture | Low — a pre-existing failure would surface at the first wave merge; does not change plan structure. |

*Only one assumed claim. Every other finding is tagged `[VERIFIED: …]` against the live tree.*

## Open Questions

1. **New guard file vs. extension of `test_doc_command_references.py`?**
   - Known: both are viable; the introspection helpers (`_command_paths`, `LEAF_COMMANDS`, `VALID_PATHS`) live in `test_doc_command_references.py` and are importable.
   - Unclear: whether a standalone `test_artifact_catalog.py` (clearer ownership) or an added block (maximal reuse, one import) reads better.
   - Recommendation: **new `tests/contract/test_artifact_catalog.py`** that *imports* the helpers from `test_doc_command_references` — clear ownership + zero duplication. (Planner's call per CONTEXT discretion.)

2. **How does the catalog represent the CONSTRUCT03 audit framing alongside the new runtime inventory?**
   - Known: the existing doc is entirely CONSTRUCT03-audit-shaped; the new capability/CLI/MCP rows are a different lens (runtime surface).
   - Unclear: whether to add a new top-level "Runtime capabilities (L2/L3)" section or interleave.
   - Recommendation: a distinct new section (guard-backed) for the runtime surface, leaving the CONSTRUCT03 skill matrix intact — minimizes churn and keeps the guard's target rows contiguous.

## Sources

### Primary (HIGH confidence — verified against the live working tree)
- `CONSTRUCT-CLAUDE-spec/architecture-overview.md` (full read) — DOC-01 target; layers, invariants, offenders, `:262` refs.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` (full read) — DOC-02 target; structure gap, config-topology deferrers.
- `CONSTRUCT-CLAUDE-spec/config-topology.md`, `README_FIRST.md` (full read) — D-06 delete + deferrer map.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md:128–167` — the L0–L4 layer model (D-01 spine).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md:200–221, 548–564` — D-07 fence points.
- `src/construct/capabilities/catalog.py` (full read) — 28 capabilities, handlers, holdout note.
- `src/construct/llm/daily_run.py:1–60` — non-blocking / no-parent-graph design (D-08).
- `tests/contract/test_doc_command_references.py` (full read) — reusable introspection; empty `_KNOWN_BROKEN`.
- `tests/contract/test_skill_migration.py` (full read) — `_MIGRATED_SKILLS` / `_FORBIDDEN_TOOLS` (D-09).
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md`, `construct-research-cycle/SKILL.md` (read) — thin template + allowed-tools.
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` (full read) — already-accurate workflow doc.
- Live introspection executed in `.venv`: `get_registry().list()`=28, `list_mcp_tools()`=22, `_command_paths(app)`→34 leaves; skills glob=24 dirs; `grep config-topology src/ tests/`=∅.

### Secondary (context, not re-verified)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, phase 14/15/16 CONTEXT decisions (as cited in CONTEXT.md canonical_refs).

## Metadata

**Confidence breakdown:**
- Doc-set resolve sweep (Finding 1): HIGH — filesystem-verified, exhaustive over the architecture doc set.
- Introspection contract & counts (Finding 4): HIGH — executed live; one CONTEXT figure (27→28) corrected with evidence.
- Config-topology delete safety (Finding 6): HIGH — grep-verified no code refs; deferrer set complete.
- Daily skill template (Finding 8): HIGH — sibling files + daily_run.py + guard all read directly.
- Catalog structure gap (Finding 5): HIGH — full read confirms no runtime-surface rows exist today.

**Research date:** 2026-07-25
**Valid until:** ~2026-08-24 for the doc/structure findings (stable); the live *counts* (28/34/22/24) are valid until the next capability/CLI/skill lands — the guard, once built, makes them self-verifying rather than time-bound.
