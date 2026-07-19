---
phase: 14-durable-state-config-truth
verified: 2026-07-19T22:30:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 14: Durable-State & Config Truth Verification Report

**Phase Goal:** A v0.5 planner and a developer configuring LLM behavior each find exactly one true,
recorded answer about where durable state and configuration live.
**Verified:** 2026-07-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `nfrs.md` §2 and `architecture-overview.md:243` no longer assert no-database/no-derived-state; both name `.construct/workflow/*.sqlite` as intentional durable state, not reconstructible from layer 1 | ✓ VERIFIED | `nfrs.md` §2 Rebuild-guarantee row scoped to knowledge state, "No Hidden State" section names the carve-out with "not reconstructible" language and cites `adr-0004`. `architecture-overview.md:243` bullet retains "Add a database that owns part of the truth" → reconsider, with an appended carve-out clause naming `.construct/workflow/*.sqlite`, "not reconstructible from layer 1", and citing `adrs/adr-0004-durable-workflow-checkpoints.md`. Confirmed by direct `sed`/`grep` reads of both files, not SUMMARY claims. |
| 2 | `workspace-contract.md` lists `.construct/workflow/*.sqlite`, `.construct/search.yaml`, `WORKSPACE.md`; `nfrs.md` §4 names Tavily instead of "Third-party APIs: None" | ✓ VERIFIED | `workspace-contract.md` shape tree shows `.construct/` with `search.yaml` and `workflow/` plus `WORKSPACE.md`; a new `### Durable orchestration state` section lists `.construct/workflow/*.sqlite` with role/citation; `.construct/search.yaml` is in the Support table; `WORKSPACE.md` is in the Derived table. `nfrs.md` §4 Third-party APIs row now reads "Tavily web search is available but opt-in... default_provider: mock... egress to Tavily only when selected and API key configured." No "None" claim remains. |
| 3 | Streamlit ops UI's LLM config path default resolves to the file the runtime actually reads, agreeing with `llm/config.py`'s resolution order including `CONSTRUCT_LLM_CONFIG` | ✓ VERIFIED | `src/construct/ui/streamlit_app.py` imports and calls `resolve_llm_config_path()` from `construct.llm.config` directly (line 15, 32) — one code path, two callers (also called by `load_llm_config`, config.py:92). No hardcoded literal, no re-implemented env-var logic in the UI file (`CONSTRUCT_LLM_CONFIG`/`os.environ` absent from streamlit_app.py by design). Read `config.py` directly: `resolve_llm_config_path` implements explicit-arg → `CONSTRUCT_LLM_CONFIG` env var → `DEFAULT_CONFIG_PATH`, matching the docstring and `nfrs.md` §3's description. Editable path/provider controls removed; dead session-state writes removed. |
| 4 | `model-routing.yaml` has exactly one recorded fate — scaffolded and marked deprecated in every doc that currently calls it authoritative (`workspace-contract.md` Support table, `config-topology.md:56,135`) | ✓ VERIFIED | It remains scaffolded: `services/init.py:58` still copies the template; `schemas/workspace.py:25` still lists `.construct/model-routing.yaml` in `REQUIRED_PATHS` (unchanged — confirmed no diff to `schemas/`, `storage/`, `services/` across the whole phase span). Every surviving `model-routing` mention in `workspace-contract.md`, `config-topology.md`, and `nfrs.md` carries a deprecation marker — verified with an exhaustive `grep -civ deprecat` returning 0 in all three files. `nfrs.md` §3 also names `llm/config.yaml` as the real authority. |
| 5 | Full pytest suite green (≥439 tests) with no new `_KNOWN_BROKEN` entries | ✓ VERIFIED | `.venv/bin/python -m pytest -q` → **443 passed**, 0 failed (independently re-run, not taken from SUMMARY). `_KNOWN_BROKEN` imported directly from `tests/contract/test_doc_command_references.py` → 5 entries, identical set to the pre-phase baseline (`views/generate`, `knowledge card list`, `knowledge ref list`, `workflow run`, `workflow resume`) — no new entries added. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Requirement Text Cross-Check (Independent Verification per Orchestrator Request)

**DOC-03 full text** (not just the checkbox): "The durable-checkpointer decision is recorded as an
intentional architectural change — `.construct/workflow/*.sqlite` holds pending human-review decisions
not reconstructible from layer 1 — with the contradicting invariants in `nfrs.md` §2 and
`architecture-overview.md:243` updated, `nfrs.md` §4's 'Third-party APIs: None' corrected for Tavily, and
`.construct/workflow/*.sqlite`, `.construct/search.yaml`, and `WORKSPACE.md` added to
`workspace-contract.md`."

Every clause independently confirmed against live files (see Truths 1–2 above), spanning all three plans
(14-01 for `adr-0004`/`architecture-overview.md`, 14-02 for `nfrs.md`, 14-03 for `workspace-contract.md`).
The requirement's mark is legitimate — all three component plans that jointly satisfy DOC-03's own text
have landed, not just the plan (14-01) that first flipped the checkbox.

**FIX-02 full text**: "Developer configuring LLM behavior finds exactly one authoritative config
location, with the Streamlit ops UI default pointing at the file the runtime actually reads and
`model-routing.yaml`'s fate (deprecate or delete from `services/init.py:58`) decided and recorded in the
docs that currently describe it as authoritative." Confirmed: UI points at the runtime's resolver
(Truth 3); `model-routing.yaml`'s fate is decided (deprecated, scaffolded) and recorded in `nfrs.md` §3,
`workspace-contract.md` Support table, and both `config-topology.md` locations (Truth 4).

### Flawed Acceptance Criteria — Independently Re-Verified

The orchestrator flagged that all four plans reported unsatisfiable acceptance criteria as written, and
asked for independent confirmation the underlying intent holds rather than trusting the executors'
self-reported re-verification. Each was re-derived independently in this session:

| Plan | Flawed criterion | Re-verified intent | Result |
|------|-------------------|---------------------|--------|
| 14-01 | `git diff` `-U3` default context made the `views/build/data/` guard return 1 instead of 0 | Confirmed `views/build/data/` bullet (line 240) is untouched and unrelated to the edited bullet (line 243) — read both directly; the edited bullet's carve-out text is self-contained and the sibling bullet content matches pre-existing content | Independently confirmed via direct file read (not `-U0` diff replay) |
| 14-02 | `grep -cF 'NetworkX'` claimed to return 1 but the file has 2 (§1 line 25 + §2 line 50 bullet) — count was derived from a section-local view | Confirmed via direct `sed`/`grep` read: `nfrs.md` §2 "No NetworkX graph to recompute" bullet is present and intact, plus the unrelated §1 occurrence — both real, neither a fabrication | Independently confirmed |
| 14-03 | `sed -n`/`awk` line-anchored guards for tree-comment alignment collided with a second `model-routing` match with no `#` | Confirmed directly: `config-topology.md` tree line 56 carries `# DEPRECATED — use llm/config.yaml` in the same comment column as sibling lines (verified visually via `sed -n '45,65p'`); §3 comparison table (line ~135) carries `🟡 (DEPRECATED, inert)` in the Claude-native column, Python-approach column left historically accurate | Independently confirmed |
| 14-04 | Task 1's own acceptance criteria required both "4 tests collected" and "import error" simultaneously — mutually exclusive for a module-level import | Confirmed the final state (post-Task 2) is correct: `tests/unit/test_llm_config_resolution.py` collects and passes 4 tests, `resolve_llm_config_path` is a real public function in `config.py`, `load_llm_config` delegates to it (traced by direct code read, not re-running the collection-time RED assertion) | Independently confirmed |

None of these required any document or code content to be altered to force a pass — in every case the
underlying substance was independently readable and correct.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-durable-workflow-checkpoints.md` | New Nygard-format ADR | ✓ VERIFIED | Exists, full Nygard skeleton (Status/Date/Deciders/Context/Related, `## Context`/`## Decision`/`## Options Considered`/`## Consequences`), plus `## Durable orchestration state (artifact class)` and `## Relationship to prior ADRs` sections. States non-reconstructibility with file:line evidence. No `backed up`/`replicated`/`recoverable` claims. |
| `CONSTRUCT-CLAUDE-spec/architecture-overview.md` (§8.2, §9.1, line 6) | Carve-out + complete ADR index | ✓ VERIFIED | All three edits present and correctly anchored. |
| `CONSTRUCT-CLAUDE-spec/nfrs.md` (§2, §3, §4) | Scoped rebuild guarantee, LLM authority, Tavily correction | ✓ VERIFIED | All four regions edited as specified. |
| `CONSTRUCT-CLAUDE-spec/workspace-contract.md` | 3 missing artifacts + 4th class | ✓ VERIFIED | Shape tree, fourth-class section, Support/Derived table rows all present. |
| `CONSTRUCT-CLAUDE-spec/config-topology.md` (line 56, ~135) | Deprecation markers | ✓ VERIFIED | Tree comment and comparison-table row both carry deprecation markers, both name `llm/config.yaml`. |
| `src/construct/llm/config.py::resolve_llm_config_path` | New public resolver | ✓ VERIFIED | Present, pure extraction, `load_llm_config` delegates to it (line 92). |
| `tests/unit/test_llm_config_resolution.py` | New test module | ✓ VERIFIED | 4 tests, all cover the documented behavior, code read confirms correctness (not merely re-trusting "passed" claim — traced logic manually). |
| `src/construct/ui/streamlit_app.py` | Read-only resolved path display | ✓ VERIFIED | Imports and calls `resolve_llm_config_path()`; no editable path/provider controls; dead session-state writes removed; `workspace_path`/`install_root` untouched. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `nfrs.md` §2 | `adrs/adr-0004-durable-workflow-checkpoints.md` | citation | ✓ WIRED | `grep -qF adr-0004` present in the "No Hidden State" carve-out paragraph |
| `architecture-overview.md` §8.2 | `adrs/adr-0004-durable-workflow-checkpoints.md` | citation | ✓ WIRED | Carve-out clause cites the ADR by plain backticked path |
| `workspace-contract.md` fourth class | `adrs/adr-0004-durable-workflow-checkpoints.md` | citation | ✓ WIRED | Trailing rule sentence cites the ADR |
| `src/construct/ui/streamlit_app.py` | `construct.llm.config.resolve_llm_config_path` | direct import + call | ✓ WIRED | `from construct.llm.config import resolve_llm_config_path` (line 15), called at line 32 |
| `load_llm_config` | `resolve_llm_config_path` | delegation | ✓ WIRED | `config.py:92` — `path = resolve_llm_config_path(config_path)` |
| `CONSTRUCT_LLM_CONFIG` env var | `resolve_llm_config_path` → sidebar display | end-to-end | ✓ WIRED | Traced through `config.py` logic; UI never re-implements the env-var check, so the override is honored via the single shared function |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `resolve_llm_config_path` honors explicit arg over env override | Read test + source logic directly (`config.py:74-81`) | Matches documented precedence | ✓ PASS |
| `resolve_llm_config_path` honors `CONSTRUCT_LLM_CONFIG` when no explicit arg | Source trace: `os.environ.get(_ENV_CONFIG_OVERRIDE)` used when `path is None` | Correct | ✓ PASS |
| `_KNOWN_BROKEN` allowlist unchanged | `python -c "...from tests.contract.test_doc_command_references import _KNOWN_BROKEN"` | 5 entries, matches pre-phase baseline | ✓ PASS |
| Full pytest suite | `.venv/bin/python -m pytest -q` | 443 passed, 0 failed | ✓ PASS |

### Prohibitions Verified (Orchestrator-Requested)

| Prohibition | Status | Evidence |
|-------------|--------|----------|
| No edits under `.planning/milestones/` | ✓ HELD | `git status --porcelain .planning/milestones/` — empty |
| No changes to `src/construct/schemas/`, `storage/`, `services/` | ✓ HELD | `git diff --stat 07b410a..HEAD -- src/construct/schemas/ src/construct/storage/ src/construct/services/` — empty across the entire phase span (not just per-plan) |
| `model-routing.yaml` rows annotated, not deleted; remains a `REQUIRED_PATHS` entry | ✓ HELD | `schemas/workspace.py:25` still lists `.construct/model-routing.yaml`; `services/init.py:58` still scaffolds it; every doc mention carries `deprecat*` rather than removal |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DOC-03 | 14-01, 14-02, 14-03 | Durable-checkpointer decision recorded; contradicting invariants corrected | ✓ SATISFIED | See Truths 1–2 and requirement-text cross-check above |
| FIX-02 | 14-02, 14-03, 14-04 | Single authoritative LLM config location; UI agrees with runtime; model-routing.yaml fate decided | ✓ SATISFIED | See Truths 3–4 and requirement-text cross-check above |

No orphaned requirements — REQUIREMENTS.md traceability table maps both DOC-03 and FIX-02 to Phase 14
exclusively, matching both plans' `requirements:` frontmatter.

### Anti-Patterns Found

None. Scanned all eight touched/created files (`adr-0004`, `architecture-overview.md`, `nfrs.md`,
`workspace-contract.md`, `config-topology.md`, `config.py`, `streamlit_app.py`,
`test_llm_config_resolution.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero matches.

### Human Verification Required

None. The one `<human-check>` block in 14-04-PLAN.md (visual confirmation of the Streamlit sidebar
render) is a live-render check with no assertable return value in the test suite, as the plan itself
notes. It does not gate this phase's programmatically-verifiable success criteria, all of which are
satisfied by the resolver-level check (criterion 3d, independently re-run above): `CONSTRUCT_LLM_CONFIG`
demonstrably changes the value `resolve_llm_config_path()` returns, and the UI calls that exact function
with no re-implementation. This is not classified as a phase-blocking human-verification item.

### Gaps Summary

None. All five ROADMAP success criteria verified directly against the live codebase. Both requirement
IDs' full text (not just their checkboxes) independently confirmed satisfied. All four flawed
acceptance-criteria deviations documented by the executors were independently re-derived and found sound.
All three orchestrator-requested prohibitions held. Full suite green at 443 (≥439 floor), `_KNOWN_BROKEN`
unchanged at 5 entries.

---

_Verified: 2026-07-19_
_Verifier: Claude (gsd-verifier)_
