# Phase 14: Durable-State & Config Truth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-19
**Phase:** 14-durable-state-config-truth
**Areas discussed:** model-routing.yaml fate, Invariant rewrite strength, Where the record lives, Streamlit config fix shape

---

## model-routing.yaml fate

### Q1 — What is model-routing.yaml's recorded fate? (first pass)

| Option | Description | Selected |
|--------|-------------|----------|
| Delete from scaffolding | Drop the init.py:58 copy; docs record it as removed | ✓ (later reversed) |
| Keep + mark deprecated | Still scaffolded; deprecation notes in workspace-contract.md:78 and config-topology.md:56,135 | |
| Delete scaffolding AND the template | Also remove templates/model-routing.yaml | |

**User's choice:** Delete from scaffolding — **subsequently reversed, see Q4.**

### Q2 — How wide is the edit fence for model-routing.yaml references?

| Option | Description | Selected |
|--------|-------------|----------|
| Criterion-4 targets + nfrs.md only | services/init.py, workspace-contract.md:78, config-topology.md:56,135, nfrs.md:72 | ✓ |
| Every live reference | Also AGENTS.md, USER-TEST-PLAYBOOK-v03.md, spec-v04, migration doc | |
| Criterion-4 targets only | Excludes nfrs.md:72 | |

**User's choice:** Criterion-4 targets + nfrs.md only
**Notes:** Avoids collision with Phase 16's ownership of AGENTS.md and the playbook (which DOC-04 retires anyway).

### Q3 — config-topology.md may be deleted by DOC-02 in Phase 17. How should Phase 14 handle it?

| Option | Description | Selected |
|--------|-------------|----------|
| Edit it anyway, note the collision | Fix lines 56/135 now; record that Phase 17 may supersede | ✓ |
| Defer the topology edits to Phase 17 | Would leave Phase 14 failing its own criterion 4 | |

**User's choice:** Edit it anyway, note the collision
**Notes:** No cross-phase dependency created; criterion 4 stays mechanically checkable now.

### Q4 — Revisit the fate decision given newly surfaced coupling?

Raised by Claude after scouting revealed `.construct/model-routing.yaml` is a `REQUIRED_PATHS` entry (`schemas/workspace.py:25`) with a loader (`storage/workspace.py:95-99`), a `ModelRoutingConfig` model (`schemas/config.py:123`), a validation branch (`services/validation.py:127-131`), generated WORKSPACE.md prose (`services/init.py:175`), a golden fixture entry, and ~12 assertions across 5 test files.

| Option | Description | Selected |
|--------|-------------|----------|
| Switch to keep + deprecated | Doc-only; no code, no test churn, no workspace-format change | ✓ |
| Keep deleting — accept the code work | Genuinely removes the dead file, but is a workspace-format change | |
| Delete scaffolding, defer contract removal | Ships workspaces failing their own required-paths contract | |

**User's choice:** Switch to keep + deprecated
**Notes:** Deleting the scaffold line alone would produce workspaces that fail `REQUIRED_PATHS`. Doing it properly is a workspace-format change, which v0.4.1 lists under Out of Scope, inside a phase whose criterion 5 demands a green suite. Criterion 4 explicitly accepts the deprecate branch. **This reversal is what keeps Phase 14 a documentation-truth phase.**

---

## Invariant rewrite strength

Preceded by a verification pass: every `append_event` call in `research_run.py` (including `research_score_gate_complete` and per-finding `gate_review_approved`/`rejected`) lives in `update_seeds_and_log`, which runs *after* the gate resumes. While a run sits at `awaiting_review`, nothing has been written to layer 1. This confirmed the ROADMAP's stronger claim over Phase 10 D-02's "checkpoint state only" framing.

### Q1 — What replaces nfrs.md:43's rebuild guarantee?

| Option | Description | Selected |
|--------|-------------|----------|
| Scoped invariant | Guarantee holds for knowledge state; workflow sqlite carved out as non-reconstructible pending review state | ✓ |
| Phase 10's "checkpoint state only" wording | Consistent with prior decision, but known to understate the case | |
| Drop the rebuild-guarantee row | Honest by omission; leaves no recorded answer for v0.5 | |

**User's choice:** Scoped invariant

### Q2 — What happens to "The 'No Hidden State' Advantage" (nfrs.md:46-54)?

| Option | Description | Selected |
|--------|-------------|----------|
| Rewrite scoped to knowledge state | Keep the section, rewrite bullets, name checkpoints as the deliberate exception | ✓ |
| Delete the section | Discards a still-valid claim that adr-0001 depends on | |

**User's choice:** Rewrite scoped to knowledge state

### Q3 — How is architecture-overview.md:240's database anti-pattern treated?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep, add the explicit carve-out | Rule plus its one sanctioned exception in the same place | ✓ |
| Rewrite the rule as knowledge-scoped | Terser, but a cold reader never learns the sqlite exists | |

**User's choice:** Keep, add the explicit carve-out

---

## Where the record lives

Context: ADR convention is Nygard-style across adr-0001..0003; adr-0003 already owns LangGraph (§A.3) and evolves via named Amendments A and B.

### Q1 — Where does the durable-checkpointer decision get recorded?

| Option | Description | Selected |
|--------|-------------|----------|
| New adr-0004 | Dedicated ADR cited by nfrs.md and architecture-overview.md; discoverable by title | ✓ |
| Amendment C to adr-0003 | Keeps the layer-model story in one doc, but buried under a milestone-sequencing title | |
| Inline doc edits only | Satisfies criteria literally with no decision record — how this drifted the first time | |

**User's choice:** New adr-0004
**Notes:** DOC-03 gates v0.5; a v0.5 planner scanning the adrs/ index must find it by title.

### Q2 — Does the Tavily / "Third-party APIs: None" correction share the record?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone §4 correction | Fix the nfrs.md §4 Privacy row; keep adr-0004 tightly about durable state | ✓ |
| Fold into adr-0004 | One posture-shift doc, but mixes a privacy fact with a state-architecture decision | |

**User's choice:** Standalone §4 correction
**Notes:** The search-provider spine was decided in Phase 8; this is documentation catching up.

### Q3 — How to close Phase 10's never-executed "update REQUIREMENTS.md Out-of-Scope" action?

| Option | Description | Selected |
|--------|-------------|----------|
| ADR discharges it; don't edit archives | adr-0004 notes it supersedes Phase 10 D-02's deferred action | ✓ |
| Also annotate the archived v0.4 REQUIREMENTS.md | More cross-linking, but mutates a sealed milestone artifact | |

**User's choice:** ADR discharges it; don't edit archives
**Notes:** The archived audit trail is what let this milestone find the drift; rewriting it destroys that.

---

## Streamlit config fix shape

Preceded by a verification pass: `st.session_state["llm_config"]` is written at `streamlit_app.py:30` and read nowhere. Same for `provider_override` at line 31. Every real `load_llm_config` caller passes `None` or its own path. The control is decorative.

### Q1 — What shape should the fix take?

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only resolved display | Non-editable display computed via llm/config.py's resolution order; honors CONSTRUCT_LLM_CONFIG | ✓ |
| Remove the field entirely | Most honest about capability, but criterion 3 reads as expecting the field to exist and be correct | |
| Wire it through to load_llm_config | Genuinely useful, but new runtime capability — barred by milestone Out of Scope | |
| Just correct the literal default | Smallest diff; leaves an editable no-op and can drift again | |

**User's choice:** Read-only resolved display
**Notes:** Correcting only the literal string would trade a wrong default for a silent one.

### Q2 — Is provider_override in scope?

| Option | Description | Selected |
|--------|-------------|----------|
| Same treatment, note it | Identical dead-control bug one line away; recorded as a deliberate scope extension | ✓ |
| Leave it — out of scope | Tightest discipline, but knowingly ships a sibling bug in the block being edited | |

**User's choice:** Same treatment, note it

---

## Claude's Discretion

- adr-0004 filename slug, title wording, and Options-Considered content.
- Exact replacement prose for the nfrs.md §2 rebuild-guarantee row and rewritten "No Hidden State" bullets.
- Wording of deprecation notes across the four fence targets.
- Streamlit rendering mechanism for the read-only display, and circular-import avoidance.
- Placement/classification of `.construct/workflow/*.sqlite` in workspace-contract.md (support class vs. a new durable-state class).
- Whether adr-0004 treats `curation-run.sqlite` and `research-run.sqlite` as one generic pattern or two decisions.

## Deferred Ideas

- Actually deleting `model-routing.yaml` (REQUIRED_PATHS, loader, ModelRoutingConfig, validation branch, WORKSPACE.md generator, golden fixture, ~12 assertions) — workspace-format change; v0.5 or a dedicated cleanup phase.
- Wiring the Streamlit sidebar controls to real behavior — new runtime capability; v0.5.
- Stale model-routing references in AGENTS.md, USER-TEST-PLAYBOOK-v03.md, spec-v04-agentworkflows.md, and the migration doc — owned by Phases 16/17.
- Event vocabulary reconciliation (conflict C4) — no overlap with Phase 14's edits; explicitly not touched here.
