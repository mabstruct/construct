# Phase 14: Durable-State & Config Truth - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Make two classes of recorded claim true again:

1. **Durable state (DOC-03)** — record `.construct/workflow/*.sqlite` as an intentional architectural change, and correct the invariants in `nfrs.md` and `architecture-overview.md` that currently deny it. Also correct `nfrs.md` §4's "Third-party APIs: None" (Tavily) and add the three missing workspace artifacts to `workspace-contract.md`.
2. **Config truth (FIX-02)** — give `model-routing.yaml` exactly one recorded fate, and make the Streamlit ops UI stop advertising an LLM config path the runtime never reads.

**This is a documentation-truth phase.** It edits docs and one UI sidebar block. It does **not** change the workspace contract, the workspace format, the LLM config resolution order, or any runtime capability. DOC-03 **gates v0.5 planning**, so the wording chosen here carries forward.

</domain>

<decisions>
## Implementation Decisions

### model-routing.yaml fate (FIX-02, criterion 4)

- **D-01:** `.construct/model-routing.yaml` is **kept scaffolded and marked deprecated** — it is *not* removed from `services/init.py`. The recorded fate is: *the runtime's LLM configuration authority is `src/construct/llm/config.yaml`, resolved by `llm/config.py` (explicit arg → `CONSTRUCT_LLM_CONFIG` → packaged default); `model-routing.yaml` is inert and retained only for workspace-contract stability.*

  **Reversal rationale (important — do not re-litigate):** deletion was selected first, then reversed on evidence. `.construct/model-routing.yaml` is a **`REQUIRED_PATHS` entry** (`src/construct/schemas/workspace.py:25`) with a loader (`storage/workspace.py:95-99`, `ModelRoutingConfig` at `schemas/config.py:123`), a validation branch (`services/validation.py:127-131`), generated `WORKSPACE.md` prose (`services/init.py:175`), a golden fixture entry (`tests/fixtures/expected-workspace-tree.txt`), and ~12 assertions across 5 test files. Removing the scaffold line alone yields workspaces that fail their own required-paths contract; removing it properly is a **workspace-format change**, which v0.4.1 lists under Out of Scope. Criterion 4 explicitly accepts the deprecate branch.

- **D-02:** **Edit fence.** Deprecation notes go only in: `CONSTRUCT-CLAUDE-spec/workspace-contract.md:78`, `CONSTRUCT-CLAUDE-spec/config-topology.md:56` and `:135`, and `CONSTRUCT-CLAUDE-spec/nfrs.md:72`. **Do not touch** `AGENTS.md:91,134`, `USER-TEST-PLAYBOOK-v03.md:36`, `spec-v04-agentworkflows.md:211,557`, or `migrations/phase-1-workspace-contract-migration.md` — those belong to Phase 16 (DOC-04, which retires the playbook) and Phase 17, or are historical spec.

- **D-03:** `config-topology.md` is edited **now** even though Phase 17 (DOC-02) may delete or rewrite the file wholesale. Record the collision in the plan. **No cross-phase dependency is created** — Phase 14 must not block on Phase 17.

### Durable-state invariant rewrite (DOC-03, criterion 1)

- **D-04:** `nfrs.md` §2's Rebuild-guarantee row becomes a **scoped invariant**: the rebuild guarantee holds for **knowledge state** (`cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`, `digests/`). Workflow orchestration state is explicitly carved out and named — `.construct/workflow/*.sqlite` holds **pending human-review decisions that are not reconstructible from layer 1**. Losing it costs a completed search+scoring cycle and any entered decisions; it never corrupts or loses canonical knowledge.

  **Verified fact underpinning this (do not weaken):** every `append_event` call in `research_run.py` — including `research_score_gate_complete` and per-finding `gate_review_approved`/`rejected` — lives in `update_seeds_and_log`, which runs **after** the gate resumes. While a run sits at `awaiting_review`, **nothing has been written to layer 1**; the scored findings and per-finding default decisions exist only in `research-run.sqlite`.

  This is **deliberately stronger** than Phase 10 D-02's "checkpoint state only / SOT stays file-based" framing, which is now known to understate the case. The stronger claim is canonical.

- **D-05:** `nfrs.md` §2's **"The 'No Hidden State' Advantage"** section (currently "No SQLite index to rebuild", "Everything is in the files") is **rewritten scoped to knowledge state, not deleted**. Its underlying claim — markdown-as-truth portability, which `adr-0001` depends on — is still true and load-bearing. Rewrite the bullets to state that *knowledge* has no derived state, naming workflow checkpoints as the one deliberate exception.

- **D-06:** `architecture-overview.md:240`'s anti-pattern ("Add a database that owns part of the truth → reconsider") is **kept, with an explicit named carve-out** for workflow orchestration state that points at `adr-0004`. A reader hitting the rule must see both the rule and its one sanctioned exception in the same place.

### Where the record lives (DOC-03)

- **D-07:** The durable-checkpointer decision is recorded in a **new `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-*.md`**, following the established Nygard format of `adr-0001..0003` (Status / Date / Deciders / Context, then Context / Decision / Options Considered / Consequences). Both `nfrs.md` §2 and `architecture-overview.md` §8.2 cite it. Chosen over an Amendment C to `adr-0003` (which already owns LangGraph at §A.3) because DOC-03 gates v0.5 and a v0.5 planner scanning the `adrs/` index must find it **by title**.

- **D-08:** `nfrs.md` §4's "Third-party APIs: None" is a **standalone correction**, not folded into `adr-0004`. Name Tavily and its data-egress implication in the §4 Privacy table. The search-provider spine was already decided in Phase 8; this is documentation catching up, not a new architectural decision.

- **D-09:** `adr-0004` explicitly records that it **discharges Phase 10 D-02's deferred action** ("update REQUIREMENTS.md Out-of-Scope to record this carve-out"). **Archived milestone documents under `.planning/milestones/` are NOT edited** — they are the sealed historical record of what was known at the time, and that audit trail is what let this milestone find the drift.

### Streamlit LLM config (FIX-02, criterion 3)

- **D-10:** `ui/streamlit_app.py:24`'s `st.text_input("LLM config path", ...)` becomes a **read-only display of the effective resolved path**, computed by calling into `llm/config.py`'s resolution order so `CONSTRUCT_LLM_CONFIG` is honored and the two cannot drift again. It must **not** be an editable control.

  **Rationale:** `st.session_state["llm_config"]` is written at line 30 and **read nowhere**; every real `load_llm_config` caller passes `None` or its own path. Merely correcting the literal default would satisfy criterion 3 on paper while leaving an editable field that does nothing — trading a wrong default for a silent one. Wiring it through to `load_llm_config` would be genuinely useful but is **new runtime capability**, barred by the milestone's Out of Scope; that belongs in v0.5.

- **D-11:** `provider_override` (`streamlit_app.py:25`, stored line 31) has the identical dead-control defect and receives the **same treatment**, recorded as a deliberate scope extension rather than a drive-by edit.

### Workspace contract additions (DOC-03, criterion 2)

- **D-12:** Add `.construct/workflow/*.sqlite`, `.construct/search.yaml`, and `WORKSPACE.md` to `workspace-contract.md`'s artifact tables. Not discussed as a gray area — criterion 2 states it directly. **Planner's call:** whether `.construct/workflow/*.sqlite` lands under the existing **Support artifacts** table or warrants a new durable-state artifact class. If a new class is introduced, `adr-0004` must define it.

### Claude's Discretion

- Exact `adr-0004` filename slug, title wording, and Options-Considered content (must follow `adr-0001..0003` format).
- Precise replacement prose for the `nfrs.md` §2 rebuild-guarantee row and the rewritten "No Hidden State" bullets, provided D-04's scoped-invariant substance and the non-reconstructibility claim survive intact.
- Wording of the deprecation notes in the four D-02 fence targets.
- Streamlit rendering mechanism for the read-only display (`st.caption` / `st.text_input(disabled=True)` / `st.code` — any is acceptable) and how it imports the resolver without a circular import.
- Classification/placement of `.construct/workflow/*.sqlite` within `workspace-contract.md` (see D-12).
- Whether `adr-0004` covers `curation-run.sqlite` alongside `research-run.sqlite` in one decision or treats the pattern generically — both files use the identical `SqliteSaver` pattern (`curation_run.py:287`, `research_run.py:891`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documents this phase edits
- `CONSTRUCT-CLAUDE-spec/nfrs.md` §2 (lines 37-54, Reliability + "No Hidden State Advantage"), §3 (line 72, model-routing "informational"), §4 (line 79, "Third-party APIs: None") — primary DOC-03 target
- `CONSTRUCT-CLAUDE-spec/architecture-overview.md` §8.2 (line 240, database anti-pattern) and §9.1 (ADR reference list — must gain adr-0004)
- `CONSTRUCT-CLAUDE-spec/workspace-contract.md` — artifact-class tables (lines 48-78); line 78 is the model-routing support row
- `CONSTRUCT-CLAUDE-spec/config-topology.md` lines 56 and 135 — templates list and Python-vs-Claude comparison table
- `CONSTRUCT-CLAUDE-spec/adrs/` — **new `adr-0004` created here**

### Decision precedent (read before writing adr-0004)
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0001-claude-native-approach.md` — markdown-as-truth; the claim D-05 must preserve
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` §A.3 — LangGraph as LLM orchestration layer; adr-0004 is downstream of this and must cross-reference it
- `.planning/milestones/v0.4-phases/10-durable-human-review-research-run/10-CONTEXT.md` D-02 — the original SqliteSaver carve-out and its never-executed follow-up action (see D-09). **Read-only — do not edit.**

### Code establishing ground truth
- `src/construct/llm/config.py:49-81` — `DEFAULT_CONFIG_PATH`, `CONSTRUCT_LLM_CONFIG`, `load_llm_config` resolution order. The authority D-10 must defer to.
- `src/construct/ui/streamlit_app.py:17-32` — sidebar block; lines 24/25 are the defects, 30/31 the dead writes
- `src/construct/llm/research_run.py:437-449, 750-825, 891` — `gate_review` interrupt, `update_seeds_and_log` event emission, checkpoint DB path. **Evidence for D-04's non-reconstructibility claim.**
- `src/construct/llm/curation_run.py:285-289` — the sibling checkpointer
- `src/construct/schemas/workspace.py:25` — `REQUIRED_PATHS` including `.construct/model-routing.yaml`. **The reason D-01 was reversed. Do not modify.**
- `src/construct/services/init.py:58, 175` — scaffolding copy and generated WORKSPACE.md prose
- `src/construct/services/validation.py:127-131` — model-routing validation branch

### Milestone constraints
- `.planning/REQUIREMENTS.md` — DOC-03 (line 29), FIX-02 (line 22), Out of Scope (lines 57-65: no new runtime capability, no workspace-format change), Future Requirements line 54 (event-vocabulary reconciliation — touch only where DOC-02/DOC-03 already require edits)
- `.planning/ROADMAP.md` Phase 14 — the five success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `llm/config.py::load_llm_config` — already implements the full resolution order. D-10 calls into it rather than duplicating the logic; this is the drift-proofing mechanism.
- `adrs/adr-0001..0003` — established Nygard template to copy for adr-0004.

### Established Patterns
- **ADR evolution:** `adr-0003` uses named Amendments (A, B) to evolve rather than superseding. D-07 chose a new ADR over Amendment C on discoverability grounds — note the departure.
- **Checkpointer pattern:** `research_run.py:889-893` and `curation_run.py:285-289` are structurally identical — `SqliteSaver(sqlite3.connect(..., check_same_thread=False))` over `.construct/workflow/{name}-run.sqlite`. adr-0004 can describe one pattern covering both.
- **Workspace contract is test-enforced:** `REQUIRED_PATHS` is asserted by `test_workspace_contracts.py`, `test_schema_contracts.py`, `test_artifact_write_gates.py`, and the `expected-workspace-tree.txt` golden fixture. Any workspace-shape change is expensive by design — this is why D-01 reversed.

### Integration Points
- `nfrs.md` §2 ↔ `architecture-overview.md` §8.2 ↔ `adr-0004` — all three must tell one consistent story; the ADR is the anchor and the other two cite it.
- `streamlit_app.py` → `llm/config.py` — a **new import** (D-10). Check for circular-import risk; `streamlit_app.py` currently imports only `streamlit`.
- `workspace-contract.md` ↔ `schemas/workspace.py` — the doc describes what the schema enforces. D-12 adds artifacts to the **doc only**; the schema is untouched.

</code_context>

<specifics>
## Specific Ideas

- **Criterion 4's "exactly one recorded fate"** is the bar: after this phase, no live doc within the D-02 fence should describe `model-routing.yaml` as authoritative or routing-controlling. `nfrs.md:72` already says "informational" — strengthen it to name `llm/config.yaml` as the actual authority.
- **D-04's claim must stay concrete.** "Not reconstructible from layer 1" is defensible because of the verified event-emission ordering. Keep that specificity; generic phrasing like "some state is durable" fails DOC-03's purpose of unblocking v0.5 design.
- **Criterion 5 is the guardrail on scope**: ≥439 tests green, no new `_KNOWN_BROKEN` entries. Under D-01/D-10 the only code touched is `ui/streamlit_app.py`, which has no test coverage — so the suite should be unaffected. If a plan finds itself editing `schemas/`, `storage/`, or `services/`, that is a signal it has drifted out of scope.

</specifics>

<deferred>
## Deferred Ideas

- **Actually deleting `model-routing.yaml`** — removing it from `REQUIRED_PATHS`, the loader, `ModelRoutingConfig`, the validation branch, the WORKSPACE.md generator, the golden fixture, and ~12 test assertions. A legitimate cleanup, but a workspace-format change. Candidate for v0.5 or a dedicated cleanup phase.
- **Wiring the Streamlit sidebar controls to real behavior** — passing `llm_config` / `provider_override` through to `load_llm_config` in the capability runner. New runtime capability; v0.5.
- **`AGENTS.md:91,134`, `USER-TEST-PLAYBOOK-v03.md:36`, `spec-v04-agentworkflows.md:211,557`, `migrations/phase-1-workspace-contract-migration.md`** — stale model-routing references outside this phase's fence. Phase 16 (DOC-04) retires the playbook and touches AGENTS.md; Phase 17 owns the remaining spec docs.
- **Event vocabulary reconciliation** (`REQUIREMENTS.md:54`, conflict C4) — `data-schemas.md` uses `verb_noun`, code emits `noun_verbed`. Scoped as "touch only where DOC-02/DOC-03 already require edits". Phase 14's edits are in `nfrs.md`/`architecture-overview.md`/`workspace-contract.md`, none of which define event vocabulary — so **no overlap; do not touch here.**

</deferred>

---

*Phase: 14-durable-state-config-truth*
*Context gathered: 2026-07-19*
