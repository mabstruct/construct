# CONSTRUCT — Artifact Catalog (Master)

**Version:** 1.0.0  
**Date:** 2026-06-06  
**Status:** Active — audit baseline for v0.3 pipeline / v0.4 UI  
**Architecture:** See [`adrs/adr-0003-v03-pipeline-v04-ui.md`](adrs/adr-0003-v03-pipeline-v04-ui.md) — v0.3 implements `PIPE`; v0.4 implements `UI` affordances on v0.3 API.
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
| [`config-topology.md`](config-topology.md) | Directory layout (partially outdated — defer to this catalog for counts) |

---

## Configuration layers

```
Layer 1  AGENTS.md              Identity — CONSTRUCT orchestrator
Layer 2  claude/agents/*.md     Sub-roles — Curator, Researcher
Layer 3  claude/skills/*/SKILL.md   Procedures — 23 skills
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

## Skills (23)

Canonical list. Source of truth for procedures: `claude/skills/<name>/SKILL.md`.

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
6. Update [`config-topology.md`](config-topology.md) if directory layout changes

**This file is the master inventory.** [`commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) is the deployed command quick-ref; [`capabilities.md`](../CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md) is the deployed user handbook derived from it.

## Phase 1 authority set for workspace contracts

The authoritative workspace contract source set for Phase 1 is:

| Layer | Files | Responsibility |
|------|-------|----------------|
| Contract intent | `CONSTRUCT-CLAUDE-spec/workspace-contract.md`, `CONSTRUCT-CLAUDE-spec/data-schemas.md`, `CONSTRUCT-CLAUDE-spec/knowledge-card-schema.md` | Defines canonical workspace shape and artifact rules |
| Initial file shape | `CONSTRUCT-CLAUDE-impl/construct/templates/*` | Shows the expected scaffold and placeholder structure |
| Ownership and sync | `CONSTRUCT-CLAUDE-spec/artifact-catalog.md`, `CONSTRUCT-CLAUDE-spec/process.md` | Names which artifacts must be updated together |

Runtime code, validators, and skill procedures must align to that authority set. When implementation behavior conflicts with the authority set, the authority set wins.
