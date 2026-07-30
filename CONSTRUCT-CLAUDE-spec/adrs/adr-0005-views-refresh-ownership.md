# ADR-0005: The Python Capability Layer Owns the Views Refresh

**Status:** Accepted
**Date:** 2026-07-20
**Deciders:** ;-)mab
**Context:** Phase 13 (v0.4) recorded D-10 — the parent skill owns a single views refresh, implemented as a skill-owned hook invoked after the child skills complete. Phase 15 (v0.4.1) wired the real `views.generate_data` capability and moved the refresh into the Python workflow layer, which reverses D-10. That reversal must be recorded in a live document, because the only other record of D-10 is an archived, read-only v0.4 milestone directory, and a reader who finds the old rule there would otherwise have no way to know it was deliberately overturned. This ADR also records the two decisions ROADMAP Phase 15 criterion 3 requires — the install-root contract and the deployed-skill-directory import coupling.
**Related:** [`adr-0001-claude-native-approach.md`](adr-0001-claude-native-approach.md), [`adr-0003-v03-pipeline-v04-ui.md`](adr-0003-v03-pipeline-v04-ui.md), [`adr-0004-durable-workflow-checkpoints.md`](adr-0004-durable-workflow-checkpoints.md), [`../spec-v02-data-model.md`](../spec-v02-data-model.md), [`../spec-v02-data-generation.md`](../spec-v02-data-generation.md)

---

## Context

Three things were true at the start of Phase 15, and they were mutually inconsistent.

**The capability did not work.** `views.generate_data` was registered in the capability catalog as a permanent-failure lambda returning "Not yet implemented". The real generator existed at `views/generate.py` but nothing reachable called it.

**The skill carried its own implementation.** `construct-views-generate-data` shipped a `generate.py`, a `lib/` parser package, a `requirements.txt`, and a `run.sh` that bootstrapped a per-skill virtual environment. This is the arrangement `adr-0001` and PROJECT.md's D-01 principle — *"Python is the deterministic enforcement layer; skills orchestrate flow"* — exist to prevent: two implementations of one behaviour, only one of which is tested.

**The refresh instruction was in the documents, and it was wrong.** Phase 13 D-10 placed refresh ownership on the parent skill, so `construct-curation-cycle/SKILL.md`, `construct-research-cycle/SKILL.md`, and `workflows/daily-cycle.md` each carried a views-refresh section. Each invoked `construct views generate --workspace .` — an option that did not exist on the command and a value that, had it existed, would have discovered zero workspaces (see the install-root contract below). Each also carried a remediation string telling the reader to run that command manually on failure. So the documented recovery path was a command that could not run.

Two further facts constrain the choice of rule.

`daily.run` **deliberately holds no parent/child graph.** Phase 13 D-09 composed the daily cycle as thin synchronous Python over frozen children rather than a parent LangGraph graph, precisely so that no component needs to reason about its position in a hierarchy. A "the parent refreshes once" rule requires exactly the parent-awareness that D-09 removed: every child must know whether it is running standalone or beneath a parent, and must be told which. That knowledge has no carrier in the current composition.

The generator is **install-root scoped, not workspace scoped.** `views/lib/discover.py:16` iterates the *children* of its argument and returns those that look like workspaces. Passing a single workspace therefore discovers zero workspaces and produces a structurally valid but empty build. The old capability input model named this field `workspace`, so the contract's name actively invited the one call that silently produces nothing.

---

## Decision

**The Python capability layer owns the views refresh, and every workflow capability refreshes.** `research.run`, `curation.run` and `daily.run` each call one shared helper — `construct.views.refresh.refresh_views(install_root)` — at the end of their run. No skill, workflow document, or parent orchestrator carries a refresh step **for a workflow that has a Python capability**.

**The one recorded exemption: `construct-synthesis`.** Synthesis is a skill-only workflow — there is no `synthesis.run` capability and no Python entry point at which a refresh could be hung, so the rule above has nothing to attach to. Rather than leave synthesis silently unable to publish what it produced, it keeps a skill-owned refresh step, narrowed to invoking `construct views generate --install-root <root>` and to the same two gates the Python helper applies. This is an exemption recorded here, not an oversight: the moment synthesis acquires a Python capability the step moves into it and this paragraph is deleted. It is the only skill that carries one; `construct-curation-cycle`, `construct-research-cycle` and `daily-cycle` had theirs removed.

**This supersedes Phase 13's D-10.** D-10 held that the parent owns the single views refresh, implemented as a skill-owned hook. That rule is reversed, not forgotten: the owner moves from the skill layer to the Python layer, and the cardinality moves from one-per-cycle to one-per-workflow-capability. The original record is cited read-only at [`.planning/milestones/v0.4-phases/13-daily-cycle-composition/13-CONTEXT.md`](../../.planning/milestones/v0.4-phases/13-daily-cycle-composition/13-CONTEXT.md) and is deliberately left unedited, on the same reasoning `adr-0004` applied to Phase 10 D-02: an archived audit trail that is rewritten in place stops being evidence that a decision was made and later reversed.

**Every workflow refreshes, rather than only a parent, because that rule needs no parent-awareness.** It is a local property of each capability. A capability that runs refreshes; a capability that does not run does not. Nothing needs to know what invoked it, which keeps D-09's no-parent-graph composition intact.

**The accepted cost, stated exactly.** A daily cycle triggers **three** sweeps rather than one, and `version.json` is therefore written up to three times per cycle while the SPA polls it. The generator's incremental fingerprinting bounds this only partially: a sweep over a genuinely unchanged install root short-circuits and writes nothing, but `daily.run`'s children *mutate the workspace by construction* — research writes refs, cards, a digest and events; curation writes lifecycle changes and events — so in a live cycle each subsequent sweep sees a changed fingerprint and performs a **full rebuild**, measured at 11 files. The honest cost is therefore roughly three full builds per daily cycle, not one build plus two no-ops. `views.auto_regenerate: false` remains the operator kill switch. Any SPA polling or debounce strategy must be designed against the three-writes figure.

**The refresh is a side effect and never a success condition.** A failed or skipped refresh never changes any workflow's reported status. This is enforced structurally rather than by discipline: the helper returns a `RefreshOutcome` type that is deliberately incompatible with each caller's status-aggregation type, so mis-wiring it into a status roll-up requires a deliberate conversion rather than a one-line append. `views.confirm_refresh` is a **verbosity** switch within this rule — when true, a *successful* refresh appends `✓ views updated`; it never gates whether the refresh runs.

**The capability is install-root scoped, and the contract says so.** The single path argument is named `install_root` on both views CLI commands (`construct views generate`, `construct views validate`) and on the capability input model `ViewsGenerateDataInput`. The workspace-lettered `-w` short flag was **removed outright** rather than kept as an alias, because a workspace-named flag on an install-root option preserves in muscle memory exactly the confusion this rename removes. The scope is not incidental: the generator aggregates every discovered workspace into one build output, so the install root is the only argument for which the operation is meaningful.

**The views source parsers are vendored into the shipped package.** They now live at `src/construct/views/lib/`. The distribution packages only `src/construct` (`pyproject.toml`: `packages = ["src/construct"]`), so the previous arrangement — which resolved a path to the deployed skill directory under the repository root and imported the parsers from there — worked only inside a development checkout and raised `ImportError` on an installed CONSTRUCT. The move was a **verbatim relocation, not a rewrite**: no parser logic changed, and intra-package imports were kept explicit-relative so no import line changed either. The consequence is that `construct-views-generate-data` is now a **CLI wrapper** holding no Python, and it therefore requires an installed CONSTRUCT. That loss of standalone operation is the accepted cost of having one implementation instead of two.

---

## Options Considered

### Option A: Move refresh ownership into the Python capability layer, with every workflow refreshing (this decision)

Delete the skill-side implementation and the three documented refresh steps; call one shared helper at the tail of each workflow capability.

**Pros:**
- One implementation of views generation, in the tested layer — realises PROJECT.md's D-01 principle rather than contradicting it
- Needs no parent-awareness, so D-09's deliberately flat `daily.run` composition survives untouched
- The refresh cannot be forgotten by an agent that skips a documented step, because it is no longer a documented step
- Removes three instructions that named a non-existent command option, closing ROADMAP criterion 4 by deletion rather than by correction

**Cons:**
- Three sweeps per daily cycle instead of one, at full rebuild cost in practice — the honest and larger cost recorded above
- The skill stops being standalone and requires an installed CONSTRUCT
- Direct `card-create` / `card-connect` invocations lose their debounced refresh, because the deleted debounce pair had no Python-layer equivalent and building one is new runtime capability that v0.4.1 excludes

### Option B: Keep the skill-owned hook and fix the option name in the three documents

Leave D-10 standing, correct `--workspace .` to `--install-root <root>` in each refresh section, and keep the skill's local generator.

**Pros:**
- Smallest diff; no reversal to record and no ADR needed
- Preserves the per-card debounce path and the skill's standalone operation

**Cons:**
- Preserves two implementations of one behaviour, only one of which any test exercises — the exact drift D-01 exists to prevent
- The parent-owns-one-refresh rule still requires parent-awareness that D-09's composition cannot supply, so the "skip if invoked by a parent" clause remains unenforceable prose
- Leaves the refresh dependent on an agent reliably executing a documented step, which is the reliability problem v0.4.1 was opened to address
- The skill's `lib/` import path still breaks on an installed CONSTRUCT, so criterion 3's second half would remain unresolved

### Option C: Expose the refresh as a standalone registry capability and have each workflow call it through the registry

Register `views.refresh` as its own capability and MCP tool, invoked by the three workflows.

**Pros:**
- Would make the refresh independently addressable and uniformly observable
- Would begin the RT-01/RT-02 registry unification for the views group

**Cons:**
- Adds new runtime capability and a new MCP tool, both listed Out of Scope for v0.4.1
- Registry unification for the views group is declined by this phase's D-03 and deferred to v0.6; doing half of it here would leave the group in a third state that is neither holdout nor unified
- An independently addressable refresh invites callers to treat its result as a gate, which is precisely the property the side-effect rule above exists to deny

---

## Consequences

### Positive

- Views data is refreshed by construction at the end of every workflow, rather than by an agent remembering a documented step.
- The three workflow documents no longer instruct a reader to run a command that cannot resolve, and no remediation string names a non-existent option.
- The generator works against an installed CONSTRUCT, not only inside a development checkout.
- Phase 17 inherits a written reversal of D-10 in the live ADR set and does not need to reconstruct refresh ownership from an archived milestone.

### Negative

- Three full view builds per daily cycle, and up to three `version.json` writes that the SPA polls — addressed by naming the real measured cost above rather than the optimistic fingerprint-no-op version, and by retaining `views.auto_regenerate` as a kill switch.
- The `construct-views-generate-data` skill is no longer standalone — addressed by an explicit missing-executable guard in `run.sh` that names the remedy, rather than letting the failure surface as a shell error.
- Direct per-card edits no longer schedule a refresh, and the `views.per_card_hooks.*` configuration block is consequently inert — a documentation-truth item for a later phase, recorded here so it is not mistaken for a runtime defect.

### Neutral

- The views group remains a **registry holdout**. CLI and MCP reach the generator by two independent paths rather than through one registry record. RT-01/RT-02 stays open, and PROJECT.md's "Python is the deterministic enforcement layer" row keeps its ⚠️ revisit flag, which remains accurate for exactly this reason.
  - **Superseded by Phase 18 / D-02 (2026-07-30).** The paragraph above no longer holds: `views validate` is now the `views.validate_data` registry capability, reached by CLI and MCP through the one seam. The generate side still keeps the independent CLI path this ADR describes (D-03), so the holdout is retired for validate and narrowed — not closed — for generate.
- The refresh is not independently addressable. There is no `views.refresh` capability or MCP tool by design; the behaviour exists only as a tail side effect of the three workflow capabilities.

---

## Views refresh ownership (contract)

This section is the contract the workflow and skill documents consume.

**Owner:** the Python capability layer, via `construct.views.refresh.refresh_views(install_root)`.

**Callers:** `research.run`, `curation.run`, `daily.run` — each exactly once, at the end of its run.

**Gates.** The refresh is skipped, without error, when either holds:

1. `<install_root>/views/build/` does not exist.
2. `<install_root>/.construct/config.yaml` sets `views.auto_regenerate: false`.

The config gate reads the **install root's** `.construct/config.yaml`, not the global LLM config. It is read defensively: a missing file, unparseable YAML, or absent `views` section all resolve to enabled. A malformed config must never be the reason a workflow tail raises.

| Property | Value |
|---|---|
| Return type | `RefreshOutcome` — `skipped` / `succeeded` / `failed`, deliberately incompatible with every caller's status-aggregation type |
| Effect on run status | none, on every branch |
| Raises | never |
| `views.confirm_refresh: true` | appends `✓ views updated` to a **successful** refresh's reason; never gates execution |

**What a `succeeded` outcome does and does not assert.** It asserts that every workspace was discovered, every file was written, and **the generator's projection** of each file satisfied its model. It does **not** assert that the JSON on disk satisfies that model. The generator currently validates an adapted projection while writing the raw parser dict, so `construct views validate` rejects three of the eight files a generation writes (`stats.json`, `<ws>/connections.json`, `<ws>/events.json`). That divergence is an open contract question, pinned by `test_views_validate_does_not_yet_accept_generated_bytes` and deliberately unresolved here. **No consumer — including the v0.5 SPA — may treat a successful refresh as a schema guarantee over the written artefacts.**

**Authority for the data contract.** The premise that the deployed SPA is ground truth for the views data shapes is **not verifiable in-repo**; no deployed SPA is available to inspect. [`spec-v02-data-model.md`](../spec-v02-data-model.md) §5.1/§5.2 is the durable authority for the views data contract, and the parser output reconciled against it is what the models describe.

---

## Relationship to prior ADRs

**ADR-0001 (Claude-native approach) is strengthened, not weakened.** The skill layer remains the interaction model; what changes is that a skill which had grown its own runtime is returned to orchestrating flow. The D-01 principle — Python enforces, skills orchestrate — is now true of the views group in a way it previously was not.

**ADR-0003's four-layer model is unaffected.** Views data is derived output built from layer 1 knowledge files; moving *who triggers the build* between the skill layer and the capability layer does not move the artefact between layers, and no layer invariant is contradicted or extended.

**ADR-0004 supplied the procedural precedent.** Phase 14's D-07 established that a reversal of a recorded decision earns a new numbered ADR rather than an amendment to an existing one, on discoverability grounds: `adrs/` has no README or index, so a decision buried in an amendment block of an unrelated ADR is effectively unfindable. This is a comparable reversal and follows that precedent.

**Supersession of Phase 13 D-10.** D-10's rule — *"the parent owns the single views refresh"*, implemented as a skill-owned hook — is superseded in both of its parts: the owner moves to the Python capability layer, and the cardinality moves from one-per-cycle to one-per-workflow-capability. Phase 17 must read refresh ownership from this ADR and must not re-derive D-10's rule from the archived v0.4 milestone.
