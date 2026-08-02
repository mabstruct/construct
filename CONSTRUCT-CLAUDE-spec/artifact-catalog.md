# CONSTRUCT — Artifact Catalog (Master)

**Version:** 1.0.0
**Date:** 2026-06-06
**Status:** Active — audit baseline for v0.3 pipeline / v0.4 agent workflows / v0.5 UI
**Architecture:** See [`adrs/adr-0003-v03-pipeline-v04-ui.md`](adrs/adr-0003-v03-pipeline-v04-ui.md) — v0.3 implements `PIPE`; v0.4 implements LangGraph workflow capabilities; v0.5 implements `UI` affordances on the v0.4 API.
**Scope:** All Claude-native implementation artifacts in `CONSTRUCT-CLAUDE-impl/`

---

## Purpose

This is the **single canonical inventory** of CONSTRUCT's Claude-native configuration: agents, skills, workflows, and reference layers.

For workspace artifact authority, use the Phase 1 contract source set:

- [`workspace-contract.md`](workspace-contract.md) — canonical workspace shape and canonical/derived/support classification
- [`data-schemas.md`](data-schemas.md) and [`knowledge-card-schema.md`](knowledge-card-schema.md) — canonical artifact schemas
- `CONSTRUCT-CLAUDE-impl/construct/templates/` — canonical initial file shapes
- **this file** — ownership, audit, and synchronization matrix

Use it when you need to:

- see everything the system can do in one place
- trace user phrases → skills → source files
- audit artifacts against a new integration paradigm (CONSTRUCT03)
- decide what becomes a **UI action**, what stays an **internal pipeline**, and where **LLM grounding** is still required

**Related documents (not substitutes):**

| Document | Role |
|----------|------|
| [`artifact-catalog.md`](artifact-catalog.md) | **This file** — master inventory + CONSTRUCT03 audit matrix |
| [`../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md`](../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md) | User-facing capabilities handbook — agents, skills, workflows, scenarios, dependencies (deployed to `.construct/references/`) |
| [`../CONSTRUCT-CLAUDE-impl/construct/references/commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) | User-facing quick reference (commands → skills) |
| [`../CONSTRUCT-CLAUDE-impl/AGENTS.md`](../CONSTRUCT-CLAUDE-impl/AGENTS.md) | Runtime identity, routing, governance |

---

## Configuration layers

```
Layer 1  AGENTS.md              Identity — CONSTRUCT orchestrator
Layer 2  claude/agents/*.md     Sub-roles — Curator, Researcher
Layer 3  claude/skills/*/SKILL.md   Procedures — construct-* skills (count guard-checked)
Layer 4  construct/workflows/*.md   Orchestration — 3 workflows
Layer 5  construct/references/*.md  Vocabulary — enums, commands quick-ref
Layer 6  construct/templates/*        Workspace file formats
```

**Deploy mapping** (via `setup-construct.sh`):

| Source (repo) | Deployed (workspace) |
|---------------|----------------------|
| `CONSTRUCT-CLAUDE-impl/AGENTS.md` | `AGENTS.md` |
| `CONSTRUCT-CLAUDE-impl/claude/agents/` | `.claude/agents/` |
| `CONSTRUCT-CLAUDE-impl/claude/skills/` | `.claude/skills/` |
| `CONSTRUCT-CLAUDE-impl/construct/workflows/` | `.construct/workflows/` |
| `CONSTRUCT-CLAUDE-impl/construct/references/` | `.construct/references/` |
| `CONSTRUCT-CLAUDE-impl/construct/templates/` | `.construct/templates/` |

---

## Runtime capabilities (L2/L3)

The rows below are the **Python runtime surface** — the Layer 2 pipeline runtime and
its Layer 3 invoke surface (CLI → MCP). They are distinct from the CONSTRUCT03
skill matrix above (Layer 0 skill specs) and were absent from earlier revisions of
this catalog.

**These rows are guard-checked, not hand-maintained.**
[`tests/contract/test_artifact_catalog.py`](../tests/contract/test_artifact_catalog.py)
derives the truth from live introspection — `get_registry().list()`,
`get_registry().list_mcp_tools()`, the Typer command tree, and the `construct-*`
skills glob — and fails if any registered capability id, MCP tool name, CLI leaf,
or skill directory is missing a row here. No count in this file is a frozen
hand-typed integer; whatever the code registers at run time is what the guard
enforces.

### Capability registry (id → CLI → MCP)

Every registered capability. A blank CLI or MCP cell means that capability
deliberately exposes no command on that surface (e.g. `graph.status` is MCP-only;
several `knowledge`/`workspace` capabilities are CLI-only). The registry is the
authority for **capability id** and **MCP tool name**; the CLI column shows the
Typer command path that binds to the capability's `cli_name`.

| Capability id | CLI command | MCP tool |
|---------------|-------------|----------|
| `ask.domain` | `construct ask domain` | `construct_ask_domain` |
| `bridge.detect` | `construct bridge detect` | `construct_bridge_detect` |
| `card.evaluate` | `construct card evaluate` | `construct_card_evaluate` |
| `curation.inspect` | `construct curation inspect` | `construct_curation_inspect` |
| `curation.review` | `construct curation review` | `construct_curation_review` |
| `curation.run` | `construct curation run` | `construct_curation_run` |
| `daily.inspect` | `construct daily inspect` | `construct_daily_inspect` |
| `daily.run` | `construct daily run` | `construct_daily_run` |
| `graph.status` | — (MCP-only) | `construct_graph_status` |
| `help.suggest` | `construct help` | `construct_help_suggest` |
| `ingest.source` | `construct ingest source` | `construct_ingest_source` |
| `knowledge.card.archive` | `construct knowledge card archive` | — (CLI-only) |
| `knowledge.card.create` | `construct knowledge card create` | `construct_create_card` |
| `knowledge.card.edit` | `construct knowledge card edit` | `construct_edit_card` |
| `knowledge.card.list` | `construct knowledge card list` | `construct_list_cards` |
| `knowledge.connection.add` | `construct knowledge connection add` | `construct_add_connection` |
| `knowledge.connection.list` | `construct knowledge connection list` | — (CLI-only) |
| `knowledge.connection.remove` | `construct knowledge connection remove` | — (CLI-only) |
| `research.inspect` | `construct research inspect` | `construct_research_inspect` |
| `research.review` | `construct research review` | `construct_research_review` |
| `research.run` | `construct research run` | `construct_research_run` |
| `research.score` | `construct research score` | `construct_research_score` |
| `research.search` | `construct research search` | `construct_research_search` |
| `views.generate_data` | `construct views generate` *(independent path — see holdout note)* | `construct_views_generate_data` |
| `views.validate_data` | `construct views validate` | `construct_views_validate_data` |
| `workflow.status` | `construct workflow status` | — (CLI-only) |
| `workspace.init` | `construct init` | — (CLI-only) |
| `workspace.status` | `construct status` | — (CLI-only) |
| `workspace.validate` | `construct validate` | `construct_validate` |

### Non-registry CLI commands (independent path)

These Typer leaves reach their function by an **independent path — they are NOT
routed through the capability registry** (the residue of the Phase 15 D-03 holdout
for `views`/`spike`/`tag`, plus the `mcp` and `serve` server launchers). They carry
no capability id and no auto-derived MCP tool; the registry (29 caps / 23 MCP tools)
and the Typer app (35 leaves) are two distinct sources, and this table documents the
gap between them explicitly so no reader infers a registry route that does not exist.

`construct views validate` **left this table in Phase 18 (D-02)** — it is the
`views.validate_data` capability now, so it appears in the capability table above.
`spike` stays out on purpose rather than by omission: `spike run --tool-path` is an
arbitrary-executable primitive, and exposing it over MCP (and later HTTP) is a
security decision, not an oversight.

| CLI command | Surface | Notes |
|-------------|---------|-------|
| `construct spike run` | cli | Experiment runner — independent path (SPK); no registry id |
| `construct spike list` | cli | List recorded spikes — independent path |
| `construct tag extract` | cli | Tag extraction (hybrid regex) — independent path |
| `construct tag approve` | cli | Promote extracted tags to search clusters — independent path |
| `construct tag list` | cli | List extracted/approved tags — independent path |
| `construct mcp` | cli | Launch the stdio MCP server — process entry point, not a capability |
| `construct serve` | cli | Launch the loopback HTTP server (Phase 19) — process entry point, not a capability. Every capability it serves is reached through the registry, so `serve` itself has no id, exactly like `mcp` |

> **Holdout note (Phase 15 D-03, narrowed by Phase 18 D-02):** `construct views
> generate` still reaches the views generator by an independent path rather than
> through the capability registry, so `views.generate_data` carries no `cli_name`.
> Its sibling no longer does: `construct views validate` dispatches through the
> seam. Do not read the capability table above as implying `spike`/`tag` route
> through the registry — they do not.

### Search spine & LLM gates (narrative)

Two cross-cutting runtime concerns are **narrative rows** — descriptive, not
enumerable from a single registry, and therefore not asserted by the guard:

- **Search provider spine** — the provider-agnostic search layer behind
  `research.search` / `research.run` (default provider `mock`; Tavily is opt-in).
  It is a shared substrate, not a standalone capability id.
- **LLM grounding gates** — model judgment is invoked only at declared
  boundaries: relevance scoring (`research.score`), promotion (`card.evaluate`),
  connection typing, ask-domain Q&A (`ask.domain`), and synthesis voice. These
  are cross-cutting gates layered onto the capabilities above, not a separate
  enumerable surface.

---

## CONSTRUCT03 audit framework

CONSTRUCT03 shifts from **chat-as-primary-interface** to **UI-as-primary-interface**, with LLM involvement only where editorial judgment, ambiguity, or synthesis quality requires grounding.

### Interaction classes (target paradigm)

| Class | Code | Meaning | CONSTRUCT03 target |
|-------|------|---------|-------------------|
| **UI Action** | `UI` | User invokes via structured control; deterministic input → deterministic or templated output; validation rules, no model discretion on happy path | Primary surface |
| **Pipeline** | `PIPE` | Internal multi-step automation; triggered by UI button, schedule, or upstream pipeline; user sees progress + result, not chat | Runs behind UI |
| **Grounded Decision** | `LLM` | Requires model judgment: ambiguity, contradiction, promotion calls, extraction quality, synthesis voice, cross-domain inference | Chat or modal review **only here** |
| **Hybrid** | `HYB` | UI collects structured intent; LLM executes substantive work; user reviews before commit | Form → LLM → confirm |

### Audit columns (per artifact)

| Column | Values | Question it answers |
|--------|--------|---------------------|
| **Current trigger** | `user` · `workflow` · `hook` · `session` | How is it invoked today? |
| **Current surface** | `chat` · `views-read` · `views+chat` · `cli` | Where does the user interact today? |
| **Mutates SOT** | `yes` · `no` · `derived-only` | Does it write source-of-truth files? |
| **Current class** | `UI` · `PIPE` · `LLM` · `HYB` | How it behaves in v0.2 |
| **C03 target class** | `UI` · `PIPE` · `LLM` · `HYB` · `retire` · `TBD` | How it should behave in CONSTRUCT03 |
| **C03 UI affordance** | free text | Button, panel, wizard step, review modal, etc. |

**Working rule for CONSTRUCT03:** default to `UI` or `PIPE`. Escalate to `LLM` only when a step has no rule-based decision path or when the user explicitly wants co-authorship / editorial dialogue.

---

## Agents (2)

Sub-roles loaded when CONSTRUCT delegates specialized work. Not separate products — behavioral modes.

| Agent | Source | Skills bound | Current class | C03 target | Notes |
|-------|--------|--------------|---------------|------------|-------|
| **CONSTRUCT** (orchestrator) | `AGENTS.md` | All (routes) | `LLM` | `HYB` | Retains routing + editorial escalation; shrinks open-ended chat |
| **Curator** | `claude/agents/curator.md` | curation-cycle, card-evaluate, graph-status, bridge-detect | `LLM` | `PIPE` + `LLM` gates | Pipeline for rule-based checks; LLM only for ambiguous promotion/contradiction |
| **Researcher** | `claude/agents/researcher.md` | research-cycle, search-adjust | `LLM` | `PIPE` + `LLM` gates | Pipeline for search+ingest; LLM for relevance scoring and extraction |

---

## Workflows (3)

Multi-skill orchestration sequences. In CONSTRUCT03, workflows become **internal pipelines** triggered by UI session actions, not chat narratives.

| Workflow | Source | Journey | Skill sequence | Current trigger | Current class | C03 target |
|----------|--------|---------|----------------|-----------------|---------------|------------|
| **Cold Start** | `construct/workflows/cold-start.md` | J1 | workspace-init → domain-init → research-cycle → curation-cycle → graph-status | `user` (chat) | `HYB` | `UI` wizard + `PIPE` + `LLM` at domain interview |
| **Daily Cycle** | `construct/workflows/daily-cycle.md` | J2 | research-cycle → curation-cycle → graph-status → [user branch] | `user` / `session` | `HYB` | `UI` "Run maintenance" → `PIPE`; branch actions become UI buttons |
| **Co-Authorship** | `construct/workflows/co-authorship.md` | J3 | gap-analysis → [research-cycle] → synthesis → iterate → finalize | `user` (chat) | `LLM` | `UI` draft workspace + `LLM` for synthesis/revision loops |

---

## Skills

Canonical list. Source of truth for procedures: `claude/skills/<name>/SKILL.md`.
The set of rows is **guard-checked**: every `construct-*` directory under
`claude/skills/` must have a row here, enforced by
[`tests/contract/test_artifact_catalog.py`](../tests/contract/test_artifact_catalog.py)
(the count is derived from the live glob, never hand-typed).

### Entry & navigation

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-help` | `help`, `what's next?` | no | `session` | chat | `LLM` | `UI` | Home dashboard — suggested next actions as buttons, not chat menu |

### Workspace & domain setup

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-workspace-init` | `init {domain}` | yes | `user` / workflow | chat | `PIPE` | `UI` | "New domain" wizard step 1 — scaffold only |
| `construct-domain-init` | `init {domain}`, `init interview` | yes | `user` / workflow | chat | `HYB` | `HYB` | Domain setup form + LLM-assisted interview for taxonomy/seeds |
| `construct-domain-manage` | `domains` | yes | `user` | chat | `UI` | `UI` | Domain list panel — pause/activate/archive toggles |

### Research

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-research-cycle` | `research {domain\|topic}` | yes | `user` / workflow | chat | `HYB` | `PIPE` + `LLM` | "Run research" button → progress stream → review ingested cards before commit |
| `construct-search-adjust` | `search adjust` | yes | `user` | chat | `HYB` | `UI` | Search seeds editor — structured CRUD on clusters/weights |

### Knowledge operations (cards & connections)

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-card-create` | `add card`, paste URL | yes | `user` | chat | `HYB` | `UI` + `LLM` optional | Card editor form; LLM assist for extraction from URL/paste |
| `construct-card-edit` | `edit card {id}` | yes | `user` / views | chat | `UI` | `UI` | Inline card editor in Artifacts/Wiki |
| `construct-card-connect` | `connect {a} → {b}` | yes | `user` / views | chat | `HYB` | `UI` + `LLM` optional | Connection picker; LLM suggests type when ambiguous |
| `construct-card-evaluate` | `evaluate {id}` | yes | `user` / curation | chat | `LLM` | `LLM` | Promotion review modal — model recommends, user confirms |
| `construct-card-archive` | `archive {id}` | yes | `user` | chat | `UI` | `UI` | Archive action with confirmation dialog |

### Curation & integrity

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-curation-cycle` | `curate {domain}` | yes | `user` / workflow | chat | `PIPE` + `LLM` | `PIPE` + `LLM` gates | "Curate" button → report panel; LLM modal only for flagged items |
| `construct-bridge-detect` | `bridges` | derived | `user` / curation | chat | `LLM` | `PIPE` + `UI` | Cross-domain panel (see v0.2.x specs); candidates as structured list |
| `construct-workspace-validate` | `validate` | no | `user` | chat | `PIPE` | `UI` | Validation results panel — errors/warnings as actionable list |

### Analysis & reporting

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-graph-status` | `status`, `dashboard` | no | `user` / workflow | chat / views | `PIPE` | `UI` | Workspace dashboard (already in views) — retire chat duplicate |
| `construct-gap-analysis` | `gaps {domain\|topic}` | no | `user` / workflow | chat | `LLM` | `UI` + `LLM` | Gap report page; LLM for narrative recommendations only |

### Synthesis & publishing

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-synthesis` | `write {topic}`, `publish` | yes | `user` / workflow | chat | `LLM` | `HYB` | Draft editor + outline approval; LLM generates, user edits in UI |

### Views & server (v0.2 infrastructure)

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-views-scaffold` | `scaffold views` | no (views tree) | `user` | chat / cli | `PIPE` | `PIPE` | First-run setup job — hidden from daily UI |
| `construct-views-build` | `build views` | no | `user` / admin | chat / cli | `PIPE` | `PIPE` | Build step in deploy/update flow |
| `construct-views-generate-data` | `update views`, hooks | derived-only | `user` / hook | chat / auto | `PIPE` | `PIPE` | Auto on mutation; manual "Refresh" button in views chrome |
| `construct-views-reset` | `reset views` | no | `user` | chat | `PIPE` | `UI` | Admin/settings — destructive confirm |
| `construct-up` | `start`, `show views` | no | `user` / domain-init | chat / cli | `PIPE` | `UI` | App launch / status indicator in shell |
| `construct-down` | `stop` | no | `user` | chat / cli | `PIPE` | `UI` | App stop in shell |

### Composed & experimental cycles

| Skill | Command(s) | Mutates SOT | Current trigger | Current surface | Current class | C03 target | C03 UI affordance (proposed) |
|-------|------------|-------------|-----------------|-----------------|---------------|------------|------------------------------|
| `construct-daily-cycle` | `daily`, `catch me up` | yes | `user` / `session` | chat / cli | `PIPE` | `UI` | "Run daily cycle" button → activity feed; thin orchestrator over `daily.run` (non-blocking, auto-applies each gate's recommended decision) |
| `construct-spike-run` | `spike {idea}`, `spikes` | derived | `user` | chat / cli | `PIPE` + `LLM` | `HYB` | Experiment runner — `spike run`/`spike list` surfaced as a lab panel; independent path (not registry-routed) |

---

## Reference layer (5 enums + commands + capabilities)

Not executable — shared vocabulary and user-facing guides. Enum tables become **UI enums**, validation schemas, and tooltips in CONSTRUCT03.

| File | Purpose |
|------|---------|
| `construct/references/epistemic-types.md` | 10 card types |
| `construct/references/confidence-levels.md` | Confidence 1–5 |
| `construct/references/source-tiers.md` | Source tier 1–5 |
| `construct/references/connection-types.md` | 9 edge types |
| `construct/references/lifecycle-states.md` | seed → archived |
| `construct/references/commands.md` | User command quick-ref (syntax subset of this catalog) |
| `construct/references/capabilities.md` | User capabilities handbook (narrative companion — personas, scenarios, dependencies) |

---

## Hooks & side effects (cross-cutting)

These are not separate skills but affect CONSTRUCT03 pipeline design:

| Hook | Host skills | Behavior | C03 target |
|------|-------------|----------|------------|
| Views regen (batch) | research-cycle, curation-cycle, synthesis, daily-cycle terminal | Regenerates `views/build/data/` when `views/build/` exists | `PIPE` — automatic after any SOT mutation |
| Views regen (debounced) | card-create, card-connect | Trailing-edge debounce via `views.per_card_hooks` | `PIPE` |
| Views bootstrap | domain-init | Lazy construct-up if views scaffolded | `PIPE` |
| Skill-chain skip | hooked skills inside daily-cycle | Child hooks defer to parent terminal regen | Preserve in pipeline orchestrator |

---

## CONSTRUCT03 summary matrix

Aggregate view for planning discussions:

| Current class | Skill count | CONSTRUCT03 default disposition |
|---------------|-------------|--------------------------------|
| `PIPE` | 9 | Keep as backend pipelines; expose status in UI |
| `UI` | 4 | Promote to primary interaction surface |
| `HYB` | 7 | Split: structured UI input + pipeline + LLM review gate |
| `LLM` | 3 | Restrict to co-authorship, ambiguous evaluation, gap narrative |

| Area | Chat-primary today | UI-primary target |
|------|-------------------|-------------------|
| Navigation | construct-help | Dashboard + action bar |
| Setup | cold-start via chat | Setup wizard |
| Maintenance | daily-cycle via chat | "Research" / "Curate" buttons + activity feed |
| Card CRUD | chat phrases | Forms, inline edit, connection graph UI |
| Analysis | chat status/gaps | Dashboard, gap report pages |
| Writing | co-authorship chat | Draft workspace with LLM assist panel |
| Admin | chat scaffold/build/up | Settings / first-run only |

---

## Audit procedure (CONSTRUCT03)

For each skill row above:

1. **Confirm** current class against the live `SKILL.md` (procedures may have drifted).
2. **Decide** C03 target class — challenge every `LLM` default.
3. **Specify** UI affordance — screen, control, confirmation pattern.
4. **Define** API boundary — what the UI calls vs what the pipeline runs internally.
5. **Mark** LLM grounding points — explicit user review before any SOT write from model output.
6. **Update** this catalog — set `C03 target` from `TBD` to final class; link to CONSTRUCT03 spec when written.

Track progress in [`../CONSTRUCT-CLAUDE-v03-planning/README.md`](../CONSTRUCT-CLAUDE-v03-planning/README.md).

---

## Maintenance

When adding, renaming, or removing a skill, agent, or workflow:

1. Update the skill/agent/workflow source file
2. Update **this catalog** (required)
3. Update [`commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) if user-facing command syntax changes
4. Update [`capabilities.md`](../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md) if user-facing behavior, scenarios, or dependencies change
5. Update [`AGENTS.md`](../CONSTRUCT-CLAUDE-impl/AGENTS.md) skills table if orchestrator routing changes

**This file is the master inventory.** [`commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) is the deployed command quick-ref; [`capabilities.md`](../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md) is the deployed user handbook derived from it.

## Phase 1 authority set for workspace contracts

The authoritative workspace contract source set for Phase 1 is:

| Layer | Files | Responsibility |
|------|-------|----------------|
| Contract intent | `CONSTRUCT-CLAUDE-spec/workspace-contract.md`, `CONSTRUCT-CLAUDE-spec/data-schemas.md`, `CONSTRUCT-CLAUDE-spec/knowledge-card-schema.md` | Defines canonical workspace shape and artifact rules |
| Initial file shape | `CONSTRUCT-CLAUDE-impl/construct/templates/*` | Shows the expected scaffold and placeholder structure |
| Ownership and sync | `CONSTRUCT-CLAUDE-spec/artifact-catalog.md`, `CONSTRUCT-CLAUDE-spec/process.md` | Names which artifacts must be updated together |

Runtime code, validators, and skill procedures must align to that authority set. When implementation behavior conflicts with the authority set, the authority set wins.
