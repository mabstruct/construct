# Phase 17: Architecture Doc Set & daily.run Discoverability - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

A v0.5 planner reading the architecture doc set sees the system that actually exists, and the flagship v0.4 `daily.run` capability is reachable from Claude-native chat through a skill. Three requirements:

- **DOC-01** — rewrite `architecture-overview.md` against ADR-0003's runtime layer model (adding the omitted Python runtime layer), kill the false "skills are the only writers to layer 1" claim, and fix genuinely-broken doc references.
- **DOC-02** — make `artifact-catalog.md` an honest, staleness-proofed inventory; **delete** `config-topology.md` and redirect its deferrers.
- **UX-01** — a new thin `construct-daily-cycle` skill entry point for `daily.run`.

**Not in this phase:** the workspace contract itself (owned by `workspace-contract.md`, corrected in Phase 14), the doc-command guard (`test_doc_command_references.py`, delivered pre-milestone as FIX-04 and completed empty in Phase 16), any v0.5 UI work, and RT-01/RT-02 registry unification.

**Scope note (deliberate additions, both user-approved):** this phase adds (1) a **new mechanical guard test** for `artifact-catalog.md` (D-05) and (2) a **two-line spec-v04 fix** fenced here by Phases 14/16 (D-08). Neither is scope creep — (1) is the mechanism criterion 2's "counts that match live introspection" requires, and (2) is a documented cross-phase hand-off. Both were explicitly chosen during discussion.

</domain>

<decisions>
## Implementation Decisions

### Layer-model reconciliation (DOC-01, criterion 1)

- **D-01: ADR-0003's runtime stack becomes the single canonical "Layer N" vocabulary in `architecture-overview.md`.** Today the doc tells a *data-flow* story — §3 "The Three Layers" = L1 canonical state (workspace) → L2 **derived state (views cache)** → L3 presentation (SPA) — while `adr-0003` defines a *runtime* stack — L0 skill specs, L1 workspace SOT, **L2 Python pipeline runtime**, L3 invoke surface (CLI→MCP→HTTP), L4 UI shell. **The two docs use "Layer 2" for different things**, and the current doc omits the Python runtime layer entirely. The rewrite adopts `adr-0003`'s numbering as THE spine and re-expresses the one-way data-flow narrative + the four invariants (I1–I4) as **properties within/across those layers**, not as a competing layer numbering. The views cache is referred to as "derived view data" (not "Layer 2") so exactly one "Layer N" vocabulary survives.

  **Rationale:** DOC-01 explicitly names "the four-layer model ADR-0003 describes … including the Python runtime layer, which the document currently omits entirely." Making the runtime stack canonical satisfies that directly. The side-by-side "two orthogonal framings" alternative was rejected — two coexisting "layer" vocabularies is precisely the confusion the requirement exists to remove. **Invariants I1–I4 stay intact** (they are still true and `adr-0001`'s markdown-as-truth claim depends on them); they are re-anchored to the workspace-SOT / derived-view-data relationship rather than deleted.

- **D-02: The false "skills are the only legitimate writers to layer 1" claim is removed; the Python runtime's write-ownership becomes visible.** Current offenders: `architecture-overview.md:73` ("Skills like card-create … write to workspace files") and the §8 decision-tree item 4 ("Skills are the only legitimate writers to layer 1"). Post-v0.4, `research.run` / `curation.run` / `daily.run` — the Python capability runtime — own the writes; skills are thin wrappers that delegate to them (Phase 12 API-04, adr-0005).

  **Exact framing is Claude's discretion** (see below). The user's constraint: the false claim must be gone and the Python runtime's write role must be visible. **Recommended leaning (not locked):** "Layer 2 (the Python runtime) owns every write to layer 1; skills, CLI, MCP, and the future UI reach it only by invoking registered capabilities through the invoke surface — the registry is the single write contract."

- **D-03: The audit named the wrong file — `spec-v02-data-model.md` EXISTS and its citations are valid and KEPT.** DOC-01 and ROADMAP criterion 1 both instruct removing "the citation of the non-existent `spec-v02-data-model.md`." The file is present (`CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md`, created in the v0.2 release in June, **predating** the July 2026-07-19 audit that flagged it), and its citations at `architecture-overview.md:6, :102, :259` are load-bearing (`:102` anchors invariant I4's per-field derivation traceability). **Do not delete them.**

  **The genuinely-broken references** (found by re-auditing at the user's request, replacing the stale named-file instruction) are the **five vocabulary-doc citations at `architecture-overview.md:262`**: `references/epistemic-types.md`, `connection-types.md`, `lifecycle-states.md`, `confidence-levels.md`, `source-tiers.md`. They resolve relative to `CONSTRUCT-CLAUDE-spec/` but the real files live at **`CONSTRUCT-CLAUDE-impl/construct/references/`** (and ship into workspaces at `.construct/references/`). **Fix:** repoint the five citations to the real relative path and note they are workspace-shipped vocabulary docs. **Researcher must run a full resolve-sweep of the entire architecture doc set** (not just architecture-overview.md) to catch sibling broken cross-tree links.

  This parallels Phase 16's "25-command surface" correction: a phase criterion premised on a stale audit fact, corrected on evidence rather than executed literally.

### Inventory staleness-proofing (DOC-02, criteria 2 — capability/CLI/MCP inventory)

- **D-04: `artifact-catalog.md` gets a NEW mechanical guard** (e.g. `tests/contract/test_artifact_catalog.py`) that asserts the catalog's rows match **live introspection** of the registry, the Typer app, and the MCP tool list — so the inventory physically cannot silently rot. This extends FIX-04's guard-defined-truth philosophy to the catalog and directly delivers criterion 2's "counts that match live introspection of the registry and Typer app."

  **Deliberate scope addition, user-approved, and justified-by-criterion.** It is distinct from the "playbook as CI smoke suite" that Phase 16 D-09 declined as out-of-scope new test infra: that was a *runtime smoke harness*; this is a *doc-vs-introspection contract* the criterion explicitly asks for.

- **D-05: Guard coverage** — asserts at minimum **capabilities (registry) + CLI leaves (Typer walk) + MCP tools (server tool list)**. **Skills coverage is recommended** (scan `CONSTRUCT-CLAUDE-impl/claude/skills/*/` — this automatically catches the criterion-named missing `construct-spike-run` row and prevents its recurrence). The **search-spine and LLM-gate rows stay present but narrative** (descriptive, not enumerable from a single registry). Exact coverage is the planner's/researcher's call (user said "you decide"), subject to: capabilities + CLI + MCP asserted, and the `construct-spike-run` skill row present.

  **Retire the stale figures.** REQUIREMENTS.md's "27 capabilities / 25 CLI / 21 MCP" and ROADMAP criterion 2's numbers are stale — post-Phase-16 reality is **27 capabilities / 34 CLI leaves / 22 MCP tools** (Phase 16 D-01/D-04 landed `knowledge card list`). The catalog reflects **live introspection**, never a hand-typed frozen integer.

### config-topology.md fate & remaining config truth (DOC-02, criterion 3)

- **D-06: `config-topology.md` is DELETED and its deferrers redirected.** The file is dated 2026-04-23 and deeply stale across all three sections: §1's skills tree (top-level `skills/` with un-prefixed names) no longer matches the real `claude/skills/construct-*/`, omits `src/construct/` entirely; §3's workspace tree predates `.construct/` and its "Python approach" comparison marks `views/` and workflow-SQLite "❌ not needed" (now false — views generate, `adr-0004` sanctions the SQLite). Its three roles are already owned by docs corrected in this milestone: **workspace artifacts → `workspace-contract.md`** (Phase 14), **capability/CLI/MCP inventory → `artifact-catalog.md`** (this phase), **layer/deployment model → `architecture-overview.md`** (this phase). Correcting it would create a fourth copy of the workspace contract — duplicated truth is how drift starts.

  **Redirect the spec-tree deferrers:** `README_FIRST.md` and `artifact-catalog.md` (both name/point at `config-topology.md`). Planning docs that reference it (`ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`, `STATE.md`, `CONCERNS.md`, the milestone audit) reflect the delete *decision* and are not "deferrers" to rewrite — do not edit the sealed milestone audit. **Nothing is lost by deletion:** the model-routing deprecation truth already lives in `workspace-contract.md:78` and `nfrs.md:72` (Phase 14 D-02).

- **D-07: Close the Phase 14/16 fence — fix `spec-v04-agentworkflows.md:211` and `:557`.** Phase 14 D-02 and Phase 16 D-15 both explicitly deferred these stale model-routing references to "Phase 17's spec pass." `:211` presents `model-routing.yaml` as a live config domain ("Cognitive tier documentation; must not duplicate provider secrets") — mark it deprecated/inert with `llm/config.yaml` named as the LLM authority. `:557`'s dual-config-confusion risk row is updated to reflect the resolved state (model-routing deprecated per Phase 14). Bundle with the DOC-02 config work. These are the last stale model-routing references in the live spec tree.

### daily.run entry point (UX-01)

- **D-08: New `construct-daily-cycle` skill — thin, non-blocking, with an escalation handoff.** No daily skill exists today (siblings `construct-research-cycle` / `construct-curation-cycle` do; there is a `construct/workflows/daily-cycle.md` workflow doc). The new skill mirrors the siblings' thinness (`allowed-tools: Read, Bash(construct), MCP(connect)` — **no `WebSearch`/`WebFetch`/`Write`/`Edit`**) but **omits their interactive gate loop**, because `daily.run` is non-blocking by design (auto-resumes gates with each gate's *recommended* decision, surfaces escalations as a count — Phase 13 D-01/D-02, `daily_run.py:10-11`). Shape:
  1. optionally negotiate a domain focus,
  2. invoke `construct daily run --workspace . --json`,
  3. narrate the composed result (research digest, curation report, graph.status),
  4. surface the **pending-escalation count** and honestly point the user to `construct research review` / `construct curation review` for interactive handling.

- **D-09: Enroll `construct-daily-cycle` in the thin-wrapper forbidden-tools guard** (`tests/contract/test_skill_migration.py`), mirroring Phase 16 D-14's enrollment of `construct-synthesis`, so its `allowed-tools` can never silently regain forbidden tools. Its `construct …` command strings must resolve against the live Typer app — the FIX-04 doc-command guard (`test_doc_command_references.py`) covers the skills glob automatically; **zero `_KNOWN_BROKEN` additions** are permitted.

- **D-10: UX-01's "no-parent-graph decision recorded in a durable document" sub-clause (criterion 5) is ALREADY SATISFIED.** `PROJECT.md` Key Decisions already carries the Phase 13 D-09 row verbatim ("Compose the daily cycle as thin synchronous Python over frozen children, not a parent LangGraph graph/checkpointer … `daily.run` is 268 lines with no parent graph"). It is no longer only in the `daily_run.py:10-11` docstring. **Optionally reinforce** it in the rewritten `architecture-overview.md` (natural, since D-01 now describes the Python runtime layer and its composition), but the criterion does not require a second copy.

### Claude's Discretion

- **D-02's exact prose** for the layer-1 write-ownership framing (recommended leaning noted; user said "you decide").
- **D-05's exact guard coverage** — which surfaces beyond capabilities+CLI+MCP are mechanically asserted vs. narrative (skills coverage recommended; `construct-spike-run` row mandatory).
- Whether the `artifact-catalog.md` guard is a **new** test file or an extension of `test_doc_command_references.py`'s introspection helpers (which already walk the live Typer app recursively).
- The `daily-cycle.md` workflow doc's treatment — keep it (it already points at `construct daily run`) and have the skill reference it; update its stale skill-composition diagram (`research-cycle → curation-cycle → graph-status`) if trivial. Not a required edit.
- How `architecture-overview.md`'s rewrite sequences against the catalog guard and config-topology deletion (wave ordering, plan decomposition across DOC-01 / DOC-02 / UX-01).
- Whether ROADMAP.md / REQUIREMENTS.md's stale "27/25/21" and "non-existent spec-v02-data-model.md" / "25-command" premises are corrected in this phase or flagged for the milestone audit.
- The `construct-daily-cycle` skill's exact procedure wording and `SKILL.md` description/trigger phrasing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documents this phase rewrites / edits / deletes
- `CONSTRUCT-CLAUDE-spec/architecture-overview.md` — DOC-01 primary target. §3 "The Three Layers" (:28–89), §4 invariants I1–I4 (:93–102), §8.2 anti-patterns (:236 decision-tree item 4), Related list (:6), the five broken vocab refs at (:262). **Preserve I1–I4; kill the "skills are the only writers" claim; adopt ADR-0003's layer numbering.**
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — DOC-02 primary target. Declares itself the canonical inventory; gains rows for every capability/CLI/MCP tool/skill + the `construct-spike-run` row, backed by the new guard (D-04/D-05). Also a `config-topology.md` deferrer to redirect (D-06).
- `CONSTRUCT-CLAUDE-spec/config-topology.md` — **DELETED** (D-06).
- `CONSTRUCT-CLAUDE-spec/README_FIRST.md` — `config-topology.md` deferrer; redirect (D-06).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — **`:211` and `:557` only** (D-07). Fenced here by Phase 14 D-02 and Phase 16 D-15.
- `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md` — **EXISTS and is KEPT** (D-03). Do not remove its citations.
- `CONSTRUCT-CLAUDE-impl/construct/references/{epistemic-types,connection-types,lifecycle-states,confidence-levels,source-tiers}.md` — the real home of the five broken citations (D-03).

### The layer model authority (read before rewriting architecture-overview.md)
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — the four/five-layer runtime model D-01 adopts as the spine. "Layer model (permanent)" at :136–148 (L0 skill specs → L1 workspace SOT → L2 Python runtime → L3 invoke surface → L4 UI). **This ADR's "Layer 2" = Python runtime, NOT the views cache.**
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0001-claude-native-approach.md` — markdown-as-truth; the claim invariants I1–I4 protect. Must survive D-01 intact.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md` — the sanctioned `.construct/workflow/*.sqlite` carve-out; the architecture doc set must stay consistent with it (already cited at `architecture-overview.md:243`).
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` — Python layer owns the views refresh; supports D-02's write-ownership framing.

### Guard / introspection mechanisms (read before building the catalog guard)
- `src/construct/capabilities/catalog.py` — the capability registry the guard introspects; source of truth for capability + MCP-tool enumeration.
- `src/construct/cli.py` — the Typer app the guard walks for CLI leaves.
- `src/construct/mcp/server.py` — registry auto-discovery → MCP tool list (never hand-edited).
- `tests/contract/test_doc_command_references.py` — FIX-04 guard; its `_command_paths()` already walks the live Typer app recursively and distinguishes leaves from groups (reusable for D-04). `_DOC_GLOBS` scans the skills dir, so the new daily skill's strings are covered automatically. **`_KNOWN_BROKEN` must stay empty.**
- `tests/contract/test_skill_migration.py` — `_FORBIDDEN_TOOLS` at :34; scope extended to `construct-daily-cycle` by D-09 (the same mechanism Phase 16 D-14 used for `construct-synthesis`).

### daily.run entry point (read before writing the skill)
- `src/construct/llm/daily_run.py:1-20` — the no-parent-graph docstring and the non-blocking / auto-resume-recommended / escalation-count design D-08 must reflect.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md`, `construct-curation-cycle/SKILL.md` — the thin-orchestrator template D-08 mirrors (minus the gate loop). Note their post-Phase-15 state: views-refresh sections removed (adr-0005).
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md` — existing J2 workflow doc; already invokes `construct daily run`. Skill references it (discretion).

### Decisions this phase must not contradict
- `.planning/phases/16-invocation-user-doc-truth/16-CONTEXT.md` — D-01/D-04 (live surface = 34 CLI / 22 MCP), D-12 (no hard command counts in the *user* doc set; the inventory doc's guarded rows are the DOC-02 analogue), D-14 (thin-wrapper guard enrollment pattern D-09 follows).
- `.planning/phases/15-views-generate-data-resolution/15-CONTEXT.md` — D-03 (views group is the registry holdout — the catalog inventory must reflect that honestly), D-11 (views-refresh removed from skills → the daily skill has NO refresh step).
- `.planning/phases/14-durable-state-config-truth/14-CONTEXT.md` — D-01 (`model-routing.yaml` deprecated/inert, `llm/config.yaml` authoritative — D-07 propagates this), D-02 (the edit fence that handed `:211/:557` here), D-07 (new-ADR-for-reversal precedent).
- `.planning/PROJECT.md` Key Decisions — the Phase 13 D-09 no-parent-graph row (satisfies D-10) and the "⚠️ Revisit" registry-coverage row (the catalog must not misrepresent views/spike/tag as registry-routed).

### Milestone framing
- `.planning/ROADMAP.md:164–178` — Phase 17 goal and five success criteria. **Criterion 1's "non-existent spec-v02-data-model.md" is stale (D-03); criterion 2's counts are stale (D-05).**
- `.planning/REQUIREMENTS.md` — DOC-01 (:27), DOC-02 (:28, stale "27/25/21"), UX-01 (:34). Traceability rows :76–80.
- `.planning/milestones/v0.4-MILESTONE-AUDIT.md` — the audit that raised these defects (incl. the mis-named spec-v02-data-model.md finding). **Sealed historical record — do not edit** (Phase 14 D-09).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`test_doc_command_references.py::_command_paths()`** — already walks the live Typer app recursively and separates leaves from groups. The catalog guard (D-04) can reuse this introspection rather than re-implementing a Typer walk.
- **`test_skill_migration.py::_FORBIDDEN_TOOLS`** — the enforcement mechanism D-09 needs already exists; only its scope changes (add `construct-daily-cycle`).
- **`construct-research-cycle` / `construct-curation-cycle` SKILL.md** — the complete thin-orchestrator template for the daily skill: `allowed-tools` shape, migration banner, scope-negotiation → `construct … run` → narrate structure.
- **`daily-cycle.md` workflow doc** — already documents the J2 daily-use journey and invokes `construct daily run`; the skill can point at it.
- **`workspace-contract.md` (Phase 14)** — the authoritative workspace-artifact list that inherits config-topology.md's §3 role after deletion.

### Established Patterns
- **Guard-defined truth (FIX-04).** The milestone's spine: an allowlist that can only shrink, paired still-broken assertions. D-04 extends this pattern to the catalog so the inventory can't silently rot.
- **Registry-first for capabilities; views group is the one recorded holdout** (Phase 15 D-03). The catalog inventory must represent this honestly — do not imply views/spike/tag route through the registry.
- **Named edit fences with recorded crossings** (Phases 14, 15, 16). D-06/D-07 follow it: config-topology.md deleted, spec-v04:211/557 crossed deliberately per prior-phase hand-off.
- **Skills as thin wrappers** (Phase 12 API-04, adr-0005). D-08/D-09 add the daily skill on that trajectory; note `construct-bridge-detect`/`domain-init`/`search-adjust` still violate it and are deferred to v0.6 — do not "fix" them here.

### Integration Points
- New `tests/contract/test_artifact_catalog.py` (or extension) → `capabilities/catalog.py` + `cli.py` Typer app + `mcp/server.py` tool list + `claude/skills/*/` scan — the introspection sources the guard asserts against.
- `tests/contract/test_skill_migration.py` scope → gains `construct-daily-cycle`.
- New `CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md` → invokes `construct daily run` (must resolve under the FIX-04 guard).
- `config-topology.md` deletion → `README_FIRST.md` + `artifact-catalog.md` reference updates.

</code_context>

<specifics>
## Specific Ideas

- **"The audit named the wrong file."** `spec-v02-data-model.md` exists and is load-bearing; the real broken refs are the five `:262` vocabulary docs pointing across trees. If a reviewer reads one line of this context, make it that one — it is the DOC-01 equivalent of Phase 16's "25-command surface" correction.
- **One "Layer N" vocabulary, not two.** The whole DOC-01 payoff is that a v0.5 planner reading `architecture-overview.md` and `adr-0003` sees the *same* layer numbering. Renaming the views cache "derived view data" is the small move that removes the "Layer 2 means two things" trap.
- **The catalog guard is the durable deliverable, not the row edits.** Hand-fixing counts today just resets the rot clock; the guard is what makes DOC-02 stay true.
- **The daily skill has NO views-refresh and NO gate loop** — both are deliberate (Phase 15 D-11 moved refresh into Python; Phase 13 made daily.run non-blocking). A planner tempted to mirror the sibling skills wholesale would reintroduce a gate loop that contradicts the capability's design.

</specifics>

<deferred>
## Deferred Ideas

- **RT-01/RT-02 registry unification for views/spike/tag** — the catalog will honestly show views as the registry holdout; unifying it is v0.6, not this phase (Phase 15 D-03, PROJECT.md "⚠️ Revisit").
- **Thin-wrapper migration for `construct-bridge-detect` / `construct-domain-init` / `construct-search-adjust`** — real debt, logged for v0.6 (`REQUIREMENTS.md:52`). D-08/D-09 do it only for the new daily skill.
- **Actually deleting `model-routing.yaml`** (removing it from `REQUIRED_PATHS`, loader, validation, golden fixture, ~12 assertions) — a workspace-format change, v0.5+ (Phase 14 deferred).
- **Event-vocabulary reconciliation** (`data-schemas.md` `verb_noun` vs code's `noun_verbed`, conflict C4) — touch only where DOC-01/DOC-02 edits already require it; `architecture-overview.md`/`artifact-catalog.md` don't define event vocabulary, so no overlap. Do not touch here.
- **Rewriting `prd.md` / `development-strategy.md`** — stale but not load-bearing for v0.5 planning; explicitly out of scope (`REQUIREMENTS.md:64`).
- **`views validate` accepting the exact bytes `views generate` writes** — Phase 15's recorded known-open contract question; not raised as a Phase 17 gray area. Remains open.

</deferred>

---

*Phase: 17-architecture-doc-set-daily-run-discoverability*
*Context gathered: 2026-07-25*
