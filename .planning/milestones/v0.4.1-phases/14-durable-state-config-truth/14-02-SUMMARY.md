---
phase: 14-durable-state-config-truth
plan: 02
subsystem: spec-documentation
tags: [nfrs, durable-state, tavily, llm-config, documentation-truth, privacy]
requires:
  - phase: 14-01
    provides: "adr-0004-durable-workflow-checkpoints.md — the scoped-guarantee wording and the ADR identifier nfrs.md §2 cites"
  - phase: 14-04
    provides: "resolve_llm_config_path in src/construct/llm/config.py — confirms the resolution order §3 documents"
provides:
  - "nfrs.md §2 rebuild guarantee scoped to knowledge state with the .construct/workflow/*.sqlite carve-out named"
  - "nfrs.md §3 naming src/construct/llm/config.yaml as the LLM configuration authority (consumed by Phases 16-17 doc rewrites)"
  - "nfrs.md §4 honest, conditional Tavily egress statement"
affects:
  - CONSTRUCT-CLAUDE-spec/nfrs.md
  - 14-03 (workspace-contract.md — must tell the same durable-state story)
tech-stack:
  added: []
  patterns: [plain-backticked-adr-citations-in-spec-docs, conditional-privacy-claims]
key-files:
  created: []
  modified:
    - CONSTRUCT-CLAUDE-spec/nfrs.md
key-decisions:
  - "The §2 rebuild guarantee is scoped by naming knowledge state explicitly rather than by softening the wording — the guarantee stays strong where it is true"
  - "The 'No Hidden State' heading was left verbatim; the scoping happens in the lead-in sentence and bullets, so adr-0001's markdown-as-truth reference target is undisturbed"
  - "The §4 Tavily row leads with the mock default so a privacy-sensitive reader's first fact is that nothing egresses by default"
  - "§3's governance.yaml clause was split into its own sentence rather than restructured — the claim is carried through verbatim in substance, keeping the D-02 fence"
patterns-established:
  - "Carve-out prose pattern: scoped lead-in, surviving true bullets, then a named exception paragraph stating blast radius without any protection claim"
requirements-completed: [DOC-03, FIX-02]
coverage:
  - id: D1
    description: "nfrs.md §2's rebuild-guarantee row no longer denies databases/caches/required derived state; it scopes the guarantee to knowledge state and names the workflow-checkpoint carve-out"
    requirement: DOC-03
    verification:
      - kind: other
        ref: "grep -c 'No databases, no caches' CONSTRUCT-CLAUDE-spec/nfrs.md == 0; grep -cF 'Rebuild guarantee' == 1"
        status: pass
      - kind: other
        ref: "Task 1 <verify> automated block → NFRS-SEC2-OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "The 'No Hidden State' section survives as scoped prose with both still-true bullets (NetworkX, views/) intact and .construct/workflow/*.sqlite named as the one non-reconstructible exception, citing adr-0004"
    requirement: DOC-03
    verification:
      - kind: other
        ref: "grep -c 'SQLite index to rebuild' == 0; grep -cF 'views/ directory' == 1; grep -ciE 'not reconstructible' >= 1; grep -cF 'adr-0004' >= 1"
        status: pass
      - kind: other
        ref: "git diff --numstat added-lines > 0 (not a pure deletion)"
        status: pass
    human_judgment: false
  - id: D3
    description: "nfrs.md §3 names src/construct/llm/config.yaml as the LLM configuration authority with its three-step resolution order and marks model-routing.yaml deprecated and inert"
    requirement: FIX-02
    verification:
      - kind: other
        ref: "grep -cF 'llm/config.yaml' >= 1; grep -cF 'CONSTRUCT_LLM_CONFIG' >= 1; grep -ci deprecat >= 1"
        status: pass
      - kind: other
        ref: "resolution order cross-read against src/construct/llm/config.py:62-81 this session"
        status: pass
    human_judgment: false
  - id: D4
    description: "nfrs.md §4 names Tavily as an optional, opt-in third-party search API with its data-egress condition, replacing the false no-third-party-APIs claim"
    requirement: DOC-03
    verification:
      - kind: other
        ref: "grep -c 'Third-party APIs | None' == 0; tavily line carries both an opt-in marker and .construct/search.yaml"
        status: pass
      - kind: other
        ref: "default_provider: mock confirmed in CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml:7"
        status: pass
    human_judgment: true
    rationale: "T-14-02-01 is a privacy statement a reader may act on. Greps prove Tavily is named and a conditional exists, but only a human can judge that the balance is honest in both directions — neither understating egress nor implying data leaves by default."
  - id: D5
    description: "No regression to the test suite or the D-02 edit fence"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m pytest -q → 443 passed"
        status: pass
      - kind: other
        ref: "git status --porcelain over AGENTS.md, USER-TEST-PLAYBOOK-v03.md, spec-v04-agentworkflows.md, migrations/, .planning/milestones/ → empty"
        status: pass
    human_judgment: false
duration: 9min
completed: 2026-07-19
status: complete
---

# Phase 14 Plan 02: nfrs.md Truth Reconciliation Summary

**Scoped `nfrs.md`'s rebuild guarantee to knowledge state with the `.construct/workflow/*.sqlite` carve-out cited to adr-0004, named `src/construct/llm/config.yaml` as the LLM configuration authority with `model-routing.yaml` marked deprecated, and replaced §4's false no-third-party-APIs claim with a conditional Tavily row.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-19T20:07:34Z
- **Completed:** 2026-07-19T20:16:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- §2's rebuild-guarantee row now scopes the guarantee by naming knowledge state (`cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`, `digests/`) and points at the carve-out; the blanket denial of databases, caches, and required derived state is gone from the file entirely.
- The "No Hidden State" section survives as scoped prose — both still-true bullets carried through unchanged — with a new paragraph naming `.construct/workflow/*.sqlite` as holding pending human-review decisions **not reconstructible** from knowledge state, stating the blast radius honestly and claiming no protection.
- §3 names the real LLM config authority and its resolution order, read from `config.py` rather than assumed, and marks `model-routing.yaml` deprecated and inert while explaining why it is retained.
- §4's third-party-API row now names Tavily with an explicit opt-in condition, leading with the shipped `default_provider: mock` so the row corrects the record without over-correcting into a false egress claim.

## Task Commits

1. **Task 1: Scope the §2 rebuild guarantee and rewrite the "No Hidden State" block** — `64b6732` (docs)
2. **Task 2: Name the real LLM config authority at §3 and correct the §4 third-party-API claim** — `258636b` (docs)

## Files Created/Modified

- `CONSTRUCT-CLAUDE-spec/nfrs.md` — four regions edited: §2 rebuild-guarantee table row, §2 "No Hidden State" prose block, §3 config-authority paragraph, §4 privacy-table third-party-API row.

## Decisions Made

- **Scoped by naming, not by softening.** The §2 row names the six knowledge-state artifacts explicitly rather than hedging with qualifiers like "generally" or "in most cases". A guarantee that lists what it covers stays auditable; a hedged one does not.
- **The `### The "No Hidden State" Advantage` heading was left verbatim.** The plan permitted scoping the heading wording. Leaving it alone keeps any existing inbound reference (including adr-0001's dependency on the markdown-as-truth framing) resolvable, and the scoping is unambiguous from the lead-in sentence.
- **The carve-out is a paragraph, not a fifth bullet.** The four bullets are parallel short negative assertions ("No X to Y"); an exception stating blast radius does not fit that shape. A following paragraph preserves the list's rhetorical form while giving the exception the room DOC-03 requires.
- **§4 leads with the mock default.** Ordering the sentence so `default_provider: mock` precedes the egress condition means a reader who stops after one sentence has a true, non-alarming picture — the prohibition's concern.

## Deviations from Plan

### Acceptance criterion unsatisfiable as literally written (documented, not worked around)

**Found during:** Task 1 verification.

**Issue:** The criterion `` grep -cF 'NetworkX' CONSTRUCT-CLAUDE-spec/nfrs.md `` **returns 1** — the still-true bullet survived — actually returns **2**, and could never return 1. The file has always had two `NetworkX` occurrences:

- line 25 — `- The Python approach (SQLite + NetworkX) becomes the scaling path`, in §1's Scalability Limit, **outside this plan's edit fence**
- line 50 — `- No NetworkX graph to recompute`, the bullet the criterion is actually about

`git show HEAD:CONSTRUCT-CLAUDE-spec/nfrs.md | grep -n 'NetworkX'` confirms both were present before any edit in this plan. The criterion's count was derived from the §2-local view of the file in `14-PATTERNS.md` (which quotes only lines 46-52) rather than from a whole-file grep.

**Resolution:** The criterion's *intent* — the still-true bullet survived untouched — was verified with two sound commands instead:

```
grep -n 'NetworkX' CONSTRUCT-CLAUDE-spec/nfrs.md          → lines 25 and 50, both intact
git diff -U0 <file> | grep -E '^[+-]' | grep -v '^[+-][+-][+-]' | grep -c 'NetworkX'  → 0
```

Zero changed lines touch either occurrence. **No file content was altered to satisfy the flawed count** — deleting the §1 line to force the count to 1 would have vandalised an unrelated, true, in-scope-of-nothing sentence to satisfy a typo.

**Note:** the task's own `<verify>` automated block uses `grep -qF 'NetworkX'` — a *presence* test, which passes. Only the prose acceptance-criteria list carries the wrong count, confirming presence was the intended semantics. This is the third instance of this class in Phase 14 (14-01's `-U3` diff-context guard, 14-04's collect-and-fail-import guard).

**Recommendation for the verifier:** treat the criterion as `grep -cF 'NetworkX' >= 1`, matching the `<verify>` block.

### Near-miss worth recording

The Task 2 criterion `` sed -n '68,76p' … | grep -ci deprecat >= 1 `` **passed**, but only incidentally: Task 1 added 6 lines above §3, shifting the deprecation sentence to line 76 — the last line of the range. Any additional line in Task 1 would have pushed it out of the window and produced a spurious failure. The whole-file form in the `<verify>` block (`grep -ci deprecat`) is the robust expression; line-anchored ranges in a file that an earlier task in the same plan grows are inherently fragile. This matches `14-PATTERNS.md`'s own "anchor assertions on strings, never on line numbers" guidance, which this one criterion did not follow.

---

**Total deviations:** 0 auto-fixed. 1 flawed acceptance criterion documented; 1 fragile criterion flagged.
**Impact on plan:** None on delivered content. Every substantive criterion passed on the first verification run; no fix cycles were needed and no Rule 1/2/3 auto-fix or Rule 4 escalation arose.

## Observation for a future phase (not fixed here — outside the D-02 fence)

Per the plan's explicit instruction, the `governance.yaml` claim in §3 was left untouched and is recorded here rather than corrected: **§3 describes `governance.yaml` as "informational in the Claude-native approach — Claude handles all tasks", but it is a `REQUIRED_PATHS` source-of-truth artifact** per `workspace-contract.md`, and its thresholds are read programmatically — `GovernanceThresholds` feeds clamp/scoring in the Phase 09 research-score path. Calling it merely informational looks like the same class of defect as the `model-routing.yaml` claim just fixed. It is untracked by any current requirement; it warrants a requirement in Phase 16 or 17.

## Verification Results

| Check | Result |
|---|---|
| Task 1 automated verify (`NFRS-SEC2-OK`) | Pass |
| Task 2 automated verify (`NFRS-SEC34-OK`) | Pass |
| V1 — criteria 1a/1b, contradicted §2 claims gone | Pass (both 0) |
| V2 — criteria 1c/1e, carve-out named and adr-0004 cited | Pass |
| V3 — criteria 2b/2c, Tavily correction | Pass |
| V4 — criteria 4b/4c, authority named and deprecation marked | Pass |
| V5 — full pytest suite | **443 passed**, 2 warnings, 6.02s (≥ 439 required) |
| V6 — edit fence (D-02) | empty (untouched) |
| `grep -cF 'governance.yaml'` unchanged from pre-edit | 1 → 1 |
| `git status --porcelain CONSTRUCT-CLAUDE-spec/` after both commits | empty |

Note on V5: the floor of 439 was set from 14-01's run; the suite is now 443 because plan 14-04 added four `test_llm_config_resolution.py` tests. No test was modified by this plan.

## Threat Mitigations Applied

- **T-14-02-01 (Information Disclosure, §4 privacy table):** mitigated in both directions. Tavily is named, and the row carries the `opt-in` conditional plus `default_provider: mock` verified against `templates/search.yaml:7`. Neither the original understatement nor an over-corrected unconditional egress claim survives.
- **T-14-02-02 (Tampering, §3 configuration authority):** mitigated. `src/construct/llm/config.yaml` and the `CONSTRUCT_LLM_CONFIG` override are both named, and the order was read from `config.py:62-81` this session rather than restated from the plan.
- **T-14-02-03 (Repudiation, §2 reliability guarantees):** mitigated. The `Rebuild guarantee` row survives (count 1), both still-true bullets survive, and the diff adds 6 lines net-positive — the scoping is not a quiet deletion.
- **T-14-02-04 (Information Disclosure, search.yaml contents):** accepted as planned. The §4 row names the file path and the provider; it reproduces no `api_key_env` value and no secret. `TAVILY_API_KEY` is named as an env-var *name* only, which the shipped template already discloses.

## Known Stubs

None.

## Threat Flags

None — this plan modifies one prose document and introduces no executable surface, network path, auth path, or schema change.

## Issues Encountered

None beyond the flawed acceptance criterion documented under Deviations.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 14-03 (`workspace-contract.md`) is unblocked.** `nfrs.md` §2 and `architecture-overview.md` §8.2 now tell one consistent story anchored on adr-0004; 14-03's fourth artifact-class table should use the same `.construct/workflow/*.sqlite` phrasing and the same "not reconstructible from layer 1" claim so all three documents agree.
- **DOC-03's v0.5 gate is materially discharged for `nfrs.md`.** The durable-checkpointer invariant is now scoped in the reliability spec, so a v0.5 UI shell reasoning about resumable gate state has a true document to read. Full DOC-03 closure still needs 14-03.
- **FIX-02 is complete for `nfrs.md` §3.** `config-topology.md:56` and `:135` still carry the `model-routing.yaml` "controls routing" / "informational" framing — those are 14-03's targets, and the deprecation wording used here (`deprecated and inert — retained only for workspace-contract stability`) is the phrasing to reuse.
- **Carry forward:** the `governance.yaml` observation above, and the recommendation that the verifier treat the `NetworkX` criterion as a presence check.

## Self-Check: PASSED

- `CONSTRUCT-CLAUDE-spec/nfrs.md` — FOUND
- `.planning/phases/14-durable-state-config-truth/14-02-SUMMARY.md` — FOUND
- Commit `64b6732` — FOUND
- Commit `258636b` — FOUND

---
*Phase: 14-durable-state-config-truth*
*Completed: 2026-07-19*
