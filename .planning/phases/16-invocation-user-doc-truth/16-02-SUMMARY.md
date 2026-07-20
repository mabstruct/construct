---
phase: 16-invocation-user-doc-truth
plan: 02
subsystem: documentation-truth
tags: [doc-truth, audit-trail, curation, roadmap]
status: complete
requires:
  - Phase 12 (curation gate + apply_archives shipped, making the deferral clause false)
  - Phase 14 D-01/D-02 (model-routing.yaml deprecation decision + AGENTS.md edit fence)
  - Phase 15 (moved the suite baseline to 489)
provides:
  - A decay_scan summary that describes runtime behaviour rather than a delivery schedule
  - README product lineage reflecting v0.4 shipped / v0.4.1 in flight
  - AGENTS.md Layer 3 CLI description by capability group with the guard test cited
  - A correct 489-test regression baseline in REQUIREMENTS.md
affects:
  - .planning/ROADMAP.md Phase 16 criterion 5 (Plans 16-03..16-07 verify against the rewritten wording)
tech-stack:
  added: []
  patterns:
    - "Describe behaviour, not delivery schedule — phase references in runtime strings rot"
    - "Cite the mechanical guard test as authority instead of writing a count (D-12)"
key-files:
  created: []
  modified:
    - src/construct/llm/curation_run.py
    - tests/llm/test_curation_run.py
    - tests/llm/test_views_refresh.py
    - README.md
    - AGENTS.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - "Only the false forward-looking 'deferred to Phase 12' clause was removed; the five accurate Phase 12 provenance citations elsewhere in curation_run.py were kept"
  - "views_refresh_hook's region-scoped assertion retained — the scoping reason changed, it did not disappear"
  - "Phase 14's completed '>=439 tests' ROADMAP criterion left as written (sealed record)"
  - "STATE.md verified clean of any 439 assertion — no edit manufactured"
metrics:
  duration: ~14m
  completed: 2026-07-20
requirements_completed: [DOC-04]
---

# Phase 16 Plan 02: Stale Facts Outside the Guard's Reach — Summary

Corrected four stale facts unreachable by `test_doc_command_references.py`: a runtime summary naming a shipped phase as future work, README's product lineage, AGENTS.md's two-command CLI description and its two `model-routing.yaml` references, and the planning documents' stale test baseline and command count.

## Required Records

**(a) Exact replacement wording of the decay summary.** The `if auto:` branch in `decay_scan` now appends:

```
; auto_archive_on_decay is set — this scan reports decay candidates and archives
nothing: each candidate is queued as an archive proposal and is archived only
after explicit operator approval at the review gate
```

This is accurate against the real control flow: `decay_scan` enqueues `CurationProposal(kind="archive")` into `gate_queue`; the archive write happens in the post-gate `apply_archives` node, reached only on resume after human review. No phase number appears. `test_auto_archive_reported_not_acted` now pins the substring `archived only after explicit operator approval`.

**(b) Did `.planning/STATE.md` carry a 439 assertion?** No. `grep -c '439' .planning/STATE.md` returns `0`. The orchestrator brief's premise did not hold, so no edit was made — verified clean rather than manufactured.

**(c) Which ROADMAP phase owns the "≥439 tests" criterion, and why it was left.** `.planning/ROADMAP.md:85`, success criterion 5 of **Phase 14 (Durable-State & Config Truth)**, which is complete. The criterion was accurate when it was met — the suite was at 439 when Phase 14 closed. Rewriting it would falsify a sealed record, the same defect class as editing `v0.4-MILESTONE-AUDIT.md`. Left as written per the plan's explicit fence.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 — decay_scan summary + two pinning tests | `b261f2e` | `curation_run.py`, `test_curation_run.py`, `test_views_refresh.py` |
| 2 — README lineage + AGENTS.md CLI/model-routing | `2fa3399` | `README.md`, `AGENTS.md` |
| 3 — test baseline + 25-command claim | `a0c4a2e` | `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` |

## What Changed

**`curation_run.py`** — string-only edit inside the existing `if auto:` branch. `git diff -U0 | grep -cE '^\s*[+-]\s*(def |if |for |return )'` returns `0`: no control flow moved, `decay["findings"]["auto_archive_on_decay"]` still reports `True`, and no card lifecycle flips.

**`test_views_refresh.py::test_deferred_step_placeholder_is_gone`** — the region scoping was kept but its comment rewritten. The exclusion it described (decay_scan's unrelated instance of the string) is gone, but a second reason survives: `views_refresh_hook`'s own docstring cites the stale string deliberately, to record why the node was rewritten. The `"""`-split in the assertion targets live code, not the history explaining it. The comment now says so.

**`README.md`** — lineage chain gained a `v0.4 shipped` row pointing at `.planning/milestones/v0.4-*` and a `v0.4.1 in flight` row pointing at `.planning/REQUIREMENTS.md`; `v0.5 planned` remains the terminus. The runtime/API and GSD-state "Where to look" rows and both repo-tree annotations were brought into agreement. Fenced `text` format and arrow layout preserved.

**`AGENTS.md:284`** — Layer 3 now enumerates the twelve capability groups and five top-level leaves, states MCP tool definitions are auto-discovered from the capability registry, keeps HTTP routes marked planned, and cites `tests/contract/test_doc_command_references.py` as the mechanical authority. No count written (D-12). Both `model-routing.yaml` references (the YAML languages bullet and the Configuration entry) are marked deprecated and inert with `src/construct/llm/config.yaml` named as the LLM configuration authority, matching Phase 14's recorded decision.

**`.planning/REQUIREMENTS.md`** — 439 → 489, qualified as the baseline at the start of v0.4.1 and explicitly labelled a point-in-time anchor rather than an invariant. The historical `Suite 404 → 439 passed` line in FIX-04's delivery record was left alone: it records what that commit did, and was true.

**`.planning/ROADMAP.md`** — Phase 16 criterion 5 rewritten to require description by capability group with the guard test cited; the release-validation artifact clause left intact. Edited with `Edit`, not `Write`: `grep -c '### Phase'` returns `4` before and after, and the Phase 16 section still lists exactly five numbered criteria.

## Deviations from Plan

**1. [Rule 1 — Over-broad acceptance criterion] Task 1's `grep -c 'Phase 12' curation_run.py == 0` was narrowed**

- **Found during:** Task 1
- **Issue:** The file carries six `Phase 12` references. Five are accurate historical provenance — the module docstring recording that `promotion_review`/`process_inbox` became real nodes in Phase 12, the gate-identifier comments citing Phase 12 CUR-03, `decay_scan`'s own docstring provenance, and `views_refresh_hook`'s docstring citing the stale string to explain why that node was rewritten (T-15-14). Satisfying the criterion literally would have deleted accurate history, which contradicts the plan's own prohibition against falsifying records that were true when written.
- **Fix:** Removed only the one false forward-looking clause at `:417`. Verified with `grep -c 'deferred to Phase 12'`, which now returns `1` — the surviving instance being `views_refresh_hook`'s deliberate historical citation, already excluded by that test's docstring split.
- **Files modified:** `src/construct/llm/curation_run.py`
- **Commit:** `b261f2e`

**2. [Rule 2 — Adjacent falsehood in the same bullet] `AGENTS.md:283` corrected alongside `:284`**

- **Found during:** Task 2
- **Issue:** The Layer 3 `Location:` line immediately above the in-scope `Contains:` bullet read `planned src/construct/mcp/`. MCP has shipped. Writing "MCP tool definitions are auto-discovered from the capability registry" on line 284 while line 283 called MCP planned would have produced a self-contradicting pair.
- **Fix:** `Location:` now reads `src/construct/cli.py` and `src/construct/mcp/` (both live); planned `src/construct/api/`. This is a one-line extension of the plan's own instruction, well inside D-13's scope fence — no broader accuracy pass was attempted.
- **Files modified:** `AGENTS.md`
- **Commit:** `2fa3399`

## Verification

```
.venv/bin/python -m pytest -q
→ 4 failed, 494 passed
```

The four failures are exactly 16-01's expected-RED set (`test_key_docs_are_not_vacuous` ×2 → 16-05, `test_command_surface_is_discoverable` → 16-03, `test_skill_drops_forbidden_tools[construct-synthesis]` → 16-04). No new failure introduced; `tests/llm/test_curation_run.py` and `tests/llm/test_views_refresh.py` pass 37/37 in isolation.

```
grep -rn '25-command\|439 tests green' .planning/ROADMAP.md .planning/REQUIREMENTS.md   → no matches
grep -rn 'more in v0.3\|v0.4 next' README.md AGENTS.md                                  → no matches
git diff --stat .planning/milestones/                                                    → empty
```

All prohibitions hold: no numeric command/capability/MCP count in any edited document, `v0.4-MILESTONE-AUDIT.md` untouched, Phase 14's completed criterion unrewritten, and `auto_archive_on_decay` still report-only.

## Known Stubs

None.

## Threat Flags

None. This plan added no network endpoint, auth path, file access pattern, or schema change. T-16-06 and T-16-07 are mitigated as planned; T-16-08's do-not-edit fence held (verified by empty `git diff --stat .planning/milestones/`).

## Self-Check: PASSED

- `src/construct/llm/curation_run.py` — FOUND
- `tests/llm/test_curation_run.py` — FOUND
- `tests/llm/test_views_refresh.py` — FOUND
- `README.md` — FOUND
- `AGENTS.md` — FOUND
- `.planning/REQUIREMENTS.md` — FOUND
- `.planning/ROADMAP.md` — FOUND
- Commit `b261f2e` — FOUND
- Commit `2fa3399` — FOUND
- Commit `a0c4a2e` — FOUND
