---
phase: 17-architecture-doc-set-daily-run-discoverability
verified: 2026-07-25T19:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 17: Architecture Doc Set & daily.run Discoverability Verification Report

**Phase Goal:** A v0.5 planner reading the architecture doc set sees the system that actually exists, and the flagship v0.4 capability is reachable from the chat interface.
**Verified:** 2026-07-25T19:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `architecture-overview.md` presents ADR-0003's four-layer model incl. Python runtime layer, no surviving single-writer claim, no citation of non-existent `spec-v02-data-model.md` | ✓ VERIFIED | Read full doc §1-§9: single L0-L4 vocabulary throughout, Layer 2 explicitly named "Python Pipeline Runtime" (§3.2), no `Layer 2 — DERIVED STATE` heading remains. `grep -c "only legitimate writers"` == 0, `grep -c "skills are the only"` == 0. §3.1 states "Layer 2 (the Python runtime) owns every write to layer 1." `spec-v02-data-model.md` exists on disk (25KB, `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md`) and is cited 3x (:6, :123, :283) — citation is to a real file, not a broken one. All five previously-broken vocab citations (`epistemic-types.md` etc.) now resolve to `CONSTRUCT-CLAUDE-impl/construct/references/*.md` — verified each file exists on disk. Invariants I1-I4 all present (lines 120-123), re-anchored to workspace-SOT/derived-view-data relationship. |
| 2 | `artifact-catalog.md` has rows for every registered capability, CLI command, MCP tool, search spine, LLM gates, and `construct-spike-run` skill row, counts matching live introspection; a NEW guard mechanically enforces this and is not vacuous | ✓ VERIFIED | `tests/contract/test_artifact_catalog.py` exists (194 lines), imports `LEAF_COMMANDS`/`VALID_PATHS`/`_invocations`/`_code_spans` from `test_doc_command_references` and `get_registry` from `construct.capabilities.catalog` — does not re-implement introspection. `.venv/bin/pytest tests/contract/test_artifact_catalog.py -v` → 5/5 passed (vacuity meta-guard + 4 subset guards for capability ids, MCP tools, Typer leaves, skill dirs). Live introspection confirmed: `get_registry().list()` == 28, `get_registry().list_mcp_tools()` == 22 — matches doc prose exactly today. Catalog contains `construct-spike-run` (line 287) and `construct-daily-cycle` (line 286) rows, a "Runtime capabilities (L2/L3)" section, and a "Search spine & LLM gates (narrative)" section (line 143). `grep -c config-topology artifact-catalog.md` == 0. No hardcoded "27 capabilities" string found. |
| 3 | `config-topology.md` is corrected or deleted, with every deferring document updated; no dangling authority pointer | ✓ VERIFIED | `test ! -e CONSTRUCT-CLAUDE-spec/config-topology.md` passes — file deleted (git-tracked deletion, commit `6273bef`). `grep -rn config-topology CONSTRUCT-CLAUDE-spec/` returns nothing — zero dangling references anywhere in the spec tree. `README_FIRST.md`'s directory-layout row (formerly linking `config-topology.md`) now redirects to `workspace-contract.md` + `artifact-catalog.md` (lines 74-75). |
| 4 | A user can trigger `daily.run` from Claude-native chat through a skill (`construct-daily-cycle`); its command strings pass the FIX-04 guard with zero `_KNOWN_BROKEN` additions | ✓ VERIFIED | `CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md` exists, `allowed-tools: Read, Bash(construct), MCP(connect)` (byte-identical to compliant siblings, no Write/Edit/WebSearch/WebFetch). Skill invokes `construct daily run --workspace . --json` (Step 2), surfaces `pending_escalations` (Step 4), and hands off to `construct research review` / `construct curation review` (Step 5) — no gate-loop, no views-refresh step (explicit "No views refresh step here" callout). `_MIGRATED_SKILLS` in `test_skill_migration.py` includes `"construct-daily-cycle"`; `.venv/bin/pytest tests/contract/test_skill_migration.py -v` → 15/15 passed (5 skills × 3 guards). `_FORBIDDEN_TOOLS` unchanged `("WebSearch", "WebFetch", "Write", "Edit")`. `_KNOWN_BROKEN` in `test_doc_command_references.py` is `{}` (empty dict, confirmed by source read) — zero additions. Full `test_doc_command_references.py` suite: 37 passed, 1 skipped. |
| 5 | The no-parent-graph design decision for `daily.run` is recorded durably (PROJECT.md and/or architecture doc set), not only in the `daily_run.py` docstring | ✓ VERIFIED | `.planning/PROJECT.md:104` records: "Compose the daily cycle as thin synchronous Python over frozen children, not a parent LangGraph graph/checkpointer ... ✓ Good — v0.4 (Phase 13, D-09)". Additionally, `architecture-overview.md:96` (added by this phase) states: "`daily.run` is a thin synchronous Python composition over frozen children ... with no parent LangGraph graph — each child owns its own checkpointer and typed result (Phase 13 D-09)." Two durable, non-docstring locations. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `CONSTRUCT-CLAUDE-spec/architecture-overview.md` | Rewritten onto L0-L4 model | ✓ VERIFIED | Full rewrite confirmed by direct read of §1-§9 |
| `CONSTRUCT-CLAUDE-impl/claude/skills/construct-daily-cycle/SKILL.md` | New thin-wrapper skill | ✓ VERIFIED | Exists, 115 lines, correct frontmatter, delegates to CLI |
| `tests/contract/test_skill_migration.py` | `construct-daily-cycle` enrolled | ✓ VERIFIED | `_MIGRATED_SKILLS` contains entry; 15/15 tests pass |
| `tests/contract/test_artifact_catalog.py` | New introspection guard | ✓ VERIFIED | 194 lines, 5/5 tests pass, imports (not reimplements) FIX-04 helpers |
| `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` | Expanded with runtime surface | ✓ VERIFIED | Runtime capabilities section, spike-run/daily-cycle rows present |
| `CONSTRUCT-CLAUDE-spec/config-topology.md` | Deleted | ✓ VERIFIED | Confirmed absent from disk |
| `CONSTRUCT-CLAUDE-spec/README_FIRST.md` | Redirect updated | ✓ VERIFIED | No config-topology reference; redirects to workspace-contract.md + artifact-catalog.md |
| `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` | Model-routing fence closed | ✓ VERIFIED | :211 and :557 both reframe model-routing.yaml as deprecated, llm/config.yaml as authority |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `construct-daily-cycle` skill | `construct daily run` capability | `Bash(construct)` invocation string | WIRED | Command string present, resolves against live Typer app (`("daily","run") in VALID_PATHS`) |
| `construct-daily-cycle` allowed-tools | `test_skill_migration.py` `_FORBIDDEN_TOOLS` guard | static frontmatter enrollment | WIRED | `_MIGRATED_SKILLS` tuple includes the skill; guard runs and passes |
| `test_artifact_catalog.py` | `get_registry()` / `_command_paths` / skills glob | direct import + filesystem glob | WIRED | Confirmed via source read (lines 52-64); guard executes and passes |
| catalog rows | live introspection | subset (`introspected <= documented`) assertions | WIRED | 4 subset guards + vacuity meta-guard all pass; confirmed non-vacuous (`test_catalog_introspection_is_not_vacuous` asserts >25/>20/known anchors) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-01 | 17-01 | Architecture-overview.md rewrite onto L0-L4 | ✓ SATISFIED | Truth 1 verified above; REQUIREMENTS.md marks Complete |
| DOC-02 | 17-03, 17-04 | Artifact-catalog.md truth + config-topology resolution | ✓ SATISFIED | Truths 2, 3 verified above; REQUIREMENTS.md marks Complete |
| UX-01 | 17-02 | daily.run reachable from chat | ✓ SATISFIED | Truth 4 verified above; REQUIREMENTS.md marks Complete |

No orphaned requirements found — DOC-01, DOC-02, UX-01 all appear in ROADMAP.md's coverage table mapped exactly to Phase 17, and all three plans (17-01, 17-02, 17-03/04) declare them in frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` | ~77, 124-126 | The catalog's new runtime-capabilities section asserts "no count in this file is a frozen hand-typed integer," then states "28 caps / 22 MCP tools / 34 leaves" in prose. All four `test_artifact_catalog.py` guards are set-membership (`introspected <= documented`) subset checks, not cardinality checks — a 29th capability would keep the guard green while the "28 caps" prose silently goes stale. **Confirmed accurate today** (28/22/34 all verified live), so criterion 2 ("counts that match live introspection") is currently satisfied; the guard does not, however, protect the specific integers from future rot. Pre-flagged by code review as WR-01. | ⚠️ Warning (non-blocking) | Future capability/tool/leaf additions could silently make the doc's prose counts stale without failing any test. Recommend either dropping the specific integers from prose or scoping the "no hand-typed integer" claim to just the row tables. |
| `tests/contract/test_skill_migration.py` | 23-27 | Module docstring says "Current scope: the three Phase 12 skills plus `construct-synthesis`" (4 skills) and "Status: RED for `construct-synthesis`" — both stale. Tuple now has 5 skills (daily-cycle added) and the suite is fully GREEN (verified: 15/15 pass, no forbidden tools present). Pre-flagged by code review as WR-02. | ⚠️ Warning (non-blocking) | Misleads a future maintainer about the guard's real status; cosmetic only, guard logic itself is correct and enforced. |
| `CONSTRUCT-CLAUDE-spec/architecture-overview.md` | :292 (§9.4) | Cites `../CONSTRUCT-CLAUDE-impl/VERSION` — confirmed this file does not exist on disk (removed in commit `aac52a7`, June 2026, well before Phase 17). **Pre-existing**, not introduced or touched by any Phase 17 commit (confirmed via `git show` at the pre-phase-17 revision — the line was already present and already broken). The 17-01 plan's backstop truth claimed "a full resolve-sweep... finds no broken citation beyond the five repointed vocab refs," and the 17-01 SUMMARY asserted the sweep found nothing else broken — this VERSION citation contradicts that specific claim, though it is unrelated to DOC-01's actual scope (the false single-writer claim and the spec-v02-data-model.md citation, both of which are correctly resolved). Also independently flagged by code review as IN-01. | ⚠️ Warning (non-blocking, pre-existing) | The doc still has one dangling citation not caused by this phase. Recommend a follow-up fix (add a VERSION file or drop the bullet) but it does not block Phase 17's actual success criteria. |

No blocker-level anti-patterns (no TBD/FIXME/XXX markers without issue references found in phase-modified files).

### Test Execution

- `.venv/bin/pytest tests/contract/test_artifact_catalog.py -v` → 5 passed
- `.venv/bin/pytest tests/contract/test_skill_migration.py -v` → 15 passed
- `.venv/bin/pytest tests/contract/test_doc_command_references.py -q` → 37 passed, 1 skipped; `_KNOWN_BROKEN = {}` confirmed empty by source read
- `.venv/bin/pytest -q` (full suite) → 524 passed, 1 skipped — matches SUMMARY claim exactly

### Human Verification Required

None. The one candidate for human judgment flagged in the 17-01 SUMMARY (D1: "does the rewritten narrative read coherently to a v0.5 planner, and does exactly one Layer N vocabulary survive") was directly checked by this verifier via a full read of `architecture-overview.md` §1-§9: the L0-L4 vocabulary is used consistently throughout every section, the views cache is uniformly called "derived view data," and no second "Layer N" numbering appears anywhere in the document. This satisfies the coherence check without requiring a separate human pass.

### Gaps Summary

No gaps. All 5 roadmap success criteria are verified against the live codebase (not just SUMMARY claims): the doc rewrite is real and internally consistent, the catalog guard is genuine and non-vacuous, config-topology.md is actually deleted with no dangling references, the daily-cycle skill actually exists and is actually enrolled in the forbidden-tools guard, and the no-parent-graph decision is recorded in two durable, non-docstring locations. Three non-blocking WARNING-level anti-patterns are noted above (WR-01 cardinality-rot risk, WR-02 stale docstring, and a pre-existing dangling VERSION citation) — none of them contradict a roadmap success criterion, and all three were already independently caught by the phase's own code review (17-REVIEW.md) as non-critical. Recommend addressing WR-01/WR-02 opportunistically in a future phase; the VERSION citation is out of Phase 17's scope entirely (pre-dates it by roughly two months).

---

_Verified: 2026-07-25T19:15:00Z_
_Verifier: Claude (gsd-verifier)_
