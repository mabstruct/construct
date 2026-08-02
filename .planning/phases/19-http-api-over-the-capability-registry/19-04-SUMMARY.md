---
phase: 19-http-api-over-the-capability-registry
plan: 04
subsystem: capabilities
tags: [capability-seam, workspace-id, http-03, path-traversal, install-root, parametrised-tests, pydantic]

# Dependency graph
requires:
  - phase: 19-http-api-over-the-capability-registry
    plan: "01"
    provides: "resolve_workspace_id / resolve_payload_workspace, the measured WORKSPACE_FIELD / INSTALL_ROOT_FIELD maps, CREATE_MODE_CAPABILITIES, the launch-context accessors (D-09), and tests/contract/conftest.py's install-root fixture"
  - phase: 18-capability-seam-consolidation
    provides: "CapabilityRegistry.invoke as the single validating seam (GOV-01) and the typed CapabilityInputError"
  - phase: 15-views-data-contracts
    provides: "discover_workspaces / _is_workspace — the scan that is an allowlist in read mode and a denylist in creation mode"
provides:
  - "Creation mode: resolve_workspace_id(must_exist=False) inverts gate 2, so workspace.init resolves under the launch install root and only where nothing exists (T-18-34 answered)"
  - "Install-root injection: views.* receive launch_install_root() when the field is absent, and refuse workspace_id — zero documented exclusions for HTTP-03"
  - "The classification cardinality guard — a capability registered without a classification fails a test naming it, rather than raising at request time (T-19-18)"
  - "Three parametrised resolver families (coercion / traversal / collision) asserting per capability, not per field name"
affects: [19-05, 19-06, 19-07, 19-08, 19-09, 19-10, 21-static-ui, 22-workspace-creation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One measurement, two readings: the same discover_workspaces scan is an allowlist for read capabilities and a denylist for create-mode ones"
    - "Launch-context injection at the seam instead of a per-surface default, so the CLI flag is untouched and the browser needs no path"
    - "Handler-as-observation-point: the handler is spied on so the assertion names the field and type a value arrived as, without needing credentials or network"
    - "Byte-level tree fingerprints (name + sha256) as the proof of 'rejected with no filesystem effect'"

key-files:
  created: []
  modified:
    - src/construct/capabilities/workspaces.py
    - src/construct/capabilities/registry.py
    - tests/contract/test_capability_seam.py

key-decisions:
  - "D-11 implemented as specified: creation mode inverts the second gate rather than dropping it, and views.* take the install root from launch context"
  - "Creation mode refuses on directory *existence*, not merely on workspace-discoverability — the narrower scan check would let workspace.init write into a half-built or unrelated directory that happens to share the name"
  - "workspace_id is refused for install-root-scoped capabilities rather than resolved: install_root is a different scope AND the authorization boundary itself"
  - "_discover() centralises the deferred import and guards a missing install root, so a mis-configured launch root is the seam's typed error rather than a bare OSError from iterdir()"
  - "The coercion family asserts at the validation boundary with a handler spy (the plan's own sanctioned form), because several workspace-scoped capabilities need an ANTHROPIC_API_KEY, network access, or a real workflow run"
  - "isinstance rather than an identity type check in the coercion family: pydantic resolves Path to the platform's concrete PosixPath, and str/Path are unrelated types so the split is still caught in both directions"

patterns-established:
  - "Family parametrisation driven by WORKSPACE_FIELD's keys — classifying a capability is what enrols it in all three audits, with no table to remember"
  - "A guard's failure message is built from the *offending* ids, not from two sets for a human to diff"

requirements-completed: [HTTP-03]

coverage:
  - id: D1
    description: "Every one of the 29 registered capabilities is classified, and a capability registered without a classification fails a cardinality guard naming it"
    requirement: HTTP-03
    verification:
      - kind: unit
        ref: "tests/contract/test_capability_seam.py#test_the_classification_maps_cover_every_registered_capability"
        status: pass
      - kind: unit
        ref: "tests/contract/test_capability_seam.py#test_the_two_classification_maps_are_disjoint"
        status: pass
      - kind: unit
        ref: "tests/contract/test_capability_seam.py#test_create_mode_capabilities_are_themselves_classified"
        status: pass
      - kind: other
        ref: ".venv/bin/python -c \"from construct.capabilities.workspaces import WORKSPACE_FIELD, INSTALL_ROOT_FIELD; ... assert union == ids; assert disjoint\" (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "workspace.init addressed by workspace_id resolves to install_root/<id> and requires that the directory does NOT already exist — a caller names a directory but never chooses where the bytes land"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_workspace_init_by_id_creates_under_the_launch_install_root_only"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_workspace_init_refuses_an_id_that_already_names_a_workspace"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_workspace_init_refuses_an_id_naming_an_existing_non_workspace"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_a_workspace_created_by_id_is_immediately_addressable_by_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "A views.* capability invoked with no install_root receives the launch install root from the seam; a caller that supplies one still has it honoured, so the CLI's --install-root flag is unchanged"
    requirement: HTTP-03
    verification:
      - kind: unit
        ref: "tests/contract/test_capability_seam.py#test_an_install_root_scoped_capability_takes_the_launch_root_when_absent"
        status: pass
      - kind: unit
        ref: "tests/contract/test_capability_seam.py#test_an_explicit_install_root_is_left_exactly_as_it_arrived"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_views_validate_data_reaches_the_launch_root_with_an_empty_payload"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_views_validate_data_still_honours_a_supplied_install_root"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_an_install_root_scoped_capability_refuses_a_workspace_id"
        status: pass
    human_judgment: false
  - id: D4
    description: "Writing the resolved workspace as a string satisfies both the 13 capabilities whose model declares a str field and the 13 whose model declares a Path field, proven per capability rather than per field name (RESEARCH A2)"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_a_workspace_id_validates_and_arrives_as_the_declared_type (27 cases)"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_a_real_handler_runs_when_addressed_by_id (one case per side of the split, no handler patched)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A traversal-shaped workspace_id is rejected before any filesystem call, and the workspace tree is byte-identical afterwards"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_a_traversal_shaped_workspace_id_touches_nothing (27 cases)"
        status: pass
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_a_traversal_shaped_id_is_refused_in_creation_mode_too"
        status: pass
    human_judgment: false
  - id: D6
    description: "Supplying both workspace_id and the capability's own path field is rejected rather than silently preferring one, with the reason naming the conflicting field"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/contract/test_capability_seam.py#test_a_workspace_id_beside_the_capabilitys_own_field_is_refused (27 cases)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Creation mode and install-root injection are behaviour, not an invoke() parameter — the seam signature is unchanged"
    requirement: HTTP-03
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_seam_has_no_leniency_knob"
        status: pass
    human_judgment: false

# Metrics
duration: 30 min
completed: 2026-08-03
status: complete
---

# Phase 19 Plan 04: Finish HTTP-03 at the Seam — All 29 Capabilities Addressable Summary

**Every registered capability is now reachable by id or by launch context, with zero exclusions: `workspace.init` gets the uniform resolve rule with its second gate inverted into a conflict check, `views.*` receive the install root from launch context, and a classification cardinality guard makes the next unclassified capability fail a test instead of a request.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 2
- **Files modified:** 3 (0 created, 3 modified)
- **Tests added:** 99 (`tests/contract/test_capability_seam.py`: 82 → 181 passing)

## Accomplishments

- **The awkward three are genuinely resolved, not quietly skipped.** `workspace.init` takes `root` and *creates* a directory; the two `views.*` capabilities take `install_root`, which is a different scope from a workspace and is the trust boundary itself. Both got a symmetric addition to the one resolver rather than a special case in the HTTP adapter, so criterion 1 is a claim about **29** capabilities and not about 26.

- **`must_exist=False` inverts gate 2 rather than dropping it.** 19-01 left creation mode as "skip the allowlist"; it now runs the *same* `discover_workspaces` scan and reads membership as a **conflict**. The shape gate stays unconditional — proven by a spy, in creation mode as well as read mode, because creation is precisely where a dropped shape gate would be worst: a traversal-shaped id would name a directory the seam then creates.

- **T-18-34 is answered, not deferred.** The caller supplies a *name*; the seam supplies the *location*. The strongest thing an attacker-controlled `workspace_id` can achieve is a new directory as a direct child of the launch install root. The test does not merely check that the expected directory appeared — it asserts that **nothing else appeared anywhere under `tmp_path`**, which is the assertion that would fail if the id could steer the parent.

- **Install-root injection makes `views.*` reachable from a browser at all.** `install_root` is a `PATH_SHAPED_KEYS` entry, so the HTTP envelope refuses it with 422 before dispatch (D-10). Without injection, those two capabilities would have been exposed and unreachable — a documented exclusion, which is exactly what D-07 forbids. An HTTP caller now reaches them by sending nothing path-shaped, while a supplied `install_root` is left byte-for-byte as it arrived, so the CLI's `--install-root` behaves exactly as before.

- **The str/Path split is measured, not assumed.** RESEARCH assumption A2 was a one-line claim with a 26-capability blast radius. The coercion family now asserts, once per workspace-scoped capability, that the resolved value reaches the handler **in the field and the type that capability's own model declares** — 13 `str`, 13 `Path`, plus `workspace.init`'s `Path`. A resolver test covering one field name could not have covered both sides of the split, because a single capability is only ever on one side.

- **"Rejected with no filesystem effect" is proven at byte level.** The traversal family captures a fingerprint of every path under the install root — names *and* sha256 of file content — before and after each rejection. An exception-type assertion alone would pass for a rejection that created something and then raised.

- **The next unclassified capability fails a test, not a request.** The cardinality guard compares two live measurements, asserts the maps are disjoint, and builds its message from the *unclassified* ids so the failure names the capability the author just added rather than printing two 29-element sets to diff by eye. A third guard catches a misspelled entry in `CREATE_MODE_CAPABILITIES`, which is consulted as `cap_id not in ...` and is therefore silently true for a typo.

## Task Commits

1. **Task 1: Classify all 29 — creation mode for `workspace.init`, launch-context injection for `views.*`** — `58d158a` (feat)
2. **Task 2: Prove the resolver over every workspace-scoped capability — coercion, traversal, collision** — `b480ea8` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `src/construct/capabilities/workspaces.py` (+168/-36) — the inverted gate, `_discover()`, the install-root injection branch, and the docstrings recording why each is uniform seam behaviour rather than a per-surface exception
- `src/construct/capabilities/registry.py` (+12) — one paragraph in `invoke`'s docstring, so the seam's own description stays true now that step 1.5 does two symmetric things instead of one
- `tests/contract/test_capability_seam.py` (+575/-1) — Layer 3 in the module docstring, the three classification guards, the `workspace.init` and `views.*` behavioural cases, and the three parametrised families (81 cases)

## Decisions Made

Beyond the plan's named D-11:

- **Creation mode refuses on *existence*, not on workspace-discoverability.** The plan's action says to invert the `discover_workspaces` membership check; the must-have says the directory must not already exist. Those differ for a directory that exists but does not look like a workspace — a half-built tree, or something unrelated sharing the name. Refusing on both (naming the existing workspace when the scan matched, and naming the collision otherwise) is what makes the must-have true rather than nearly true, and it is the strictly safer reading of T-19-04.

- **`workspace_id` is *refused* for `views.*` rather than resolved.** This retires the scope mismatch 19-01 recorded and handed over. Resolving an id there would hand the capability a single workspace, whose children `discover_workspaces` would scan and find nothing — a silently empty build. The refusal message says so, and points the caller at omitting the key.

- **`_discover()` guards a missing install root.** `discover_workspaces` calls `iterdir()` unguarded, so a launch root that does not exist raised a bare `FileNotFoundError` through the seam. It now yields an empty scan, which surfaces as the seam's own typed `CapabilityInputError` ("names no workspace... Known workspace ids: `<none>`"). A mis-configured launch root is a configuration mistake, and every surface renders the seam's typed errors — none of them render an `OSError` from three frames down.

- **The coercion family observes the handler rather than its outcome.** The plan sanctions asserting at the validation boundary "where a capability cannot run without an LLM key or network". Several of these do (`ask.domain`, the `research` family), and others open a sqlite checkpointer and execute a real workflow. Applying the validation-boundary form *uniformly* keeps the suite credential-free, network-free and fast, and yields a strictly stronger assertion than "it did not raise" — the spy names the field the value landed in and the type it arrived as. Record lookup, id resolution and `model_validate` all run for real; only step 3's callee is observed. Two additional cases (`knowledge.card.list`, `Path`-spelled; `curation.inspect`, `str`-spelled) invoke **real** handlers by id, so the door is separately proven to open on both sides of the split. The reasoning is written into the test docstring so a future reader does not "strengthen" it into a credential-dependent test.

- **`isinstance` rather than `type(...) is` for the declared-type assertion.** Pydantic resolves `Path` to the platform's concrete `PosixPath`, so an identity check failed on all 14 Path-declared capabilities. `isinstance` still catches the split in both directions, since `str` and `Path` are unrelated types.

- **A three-entry override table for payload stubs.** `_minimal_payload`'s heuristic reads `str(annotation)` for the substring `"str"`, which is right for ~20 plain `str` fields and wrong for exactly three: `list[str]` and `DomainInitInput` both contain `"str"` as a substring (the latter via *con-**str**-uct*), and `ResearchSearchInput` enforces a one-of-three rule no per-field stub can satisfy. Enumerated rather than generalised — teaching `_minimal_payload` to build valid values for arbitrary annotations would make it a second, weaker copy of pydantic.

- **Family test names all contain `workspace_id`,** so the plan's acceptance command `pytest tests/contract/test_capability_seam.py -k workspace_id` selects all three families (83 cases) rather than only the first.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Creation mode refuses an existing non-workspace directory, not only an existing workspace**

- **Found during:** Task 1, reconciling the plan's `<action>` (invert the `discover_workspaces` membership check) with its `must_haves.truths` ("requires that the directory does NOT already exist")
- **Issue:** The scan check alone is narrower than existence. `install_root/<id>` could be a half-built workspace, or an unrelated directory sharing the name; `workspace.init` would then have written into a tree it did not create.
- **Fix:** After the scan-based conflict check, a second check on `target.exists()` with its own reason. Both refuse; neither writes.
- **Files modified:** `src/construct/capabilities/workspaces.py`
- **Verification:** `tests/contract/test_capability_seam.py::test_workspace_init_refuses_an_id_naming_an_existing_non_workspace`
- **Committed in:** `58d158a`

**2. [Rule 2 - Missing Critical] A missing or non-directory install root yields an empty scan instead of an `OSError`**

- **Found during:** Task 1, while moving the deferred import into `_discover()`
- **Issue:** `discover_workspaces` calls `install_root.iterdir()` unguarded. A launch root that does not exist (a mistyped `--install-root`, a directory removed under a running server) raised `FileNotFoundError` straight through `invoke`, past every surface's typed-error handling. On the HTTP surface that is an unhandled 500 whose traceback carries a filesystem path — the T-18-10 class of leak.
- **Fix:** `_discover()` returns `{}` when the root is not a directory, so the caller produces the seam's own `CapabilityInputError`.
- **Files modified:** `src/construct/capabilities/workspaces.py`
- **Verification:** covered indirectly by the whole suite (no behaviour regression); the reasoning is recorded in `_discover`'s docstring
- **Committed in:** `58d158a`

**3. [Rule 3 - Blocking] Created a `.venv` symlink so the documented test invocation works in this worktree**

- **Issue:** Every `<verify>` and acceptance criterion invokes `.venv/bin/python`, and a git worktree has no `.venv` — the environment lives at the main checkout root. Same blocker plan 19-01 hit.
- **Fix:** `ln -sfn ../../../.venv .venv`. The repository's own `.gitignore` documents this pattern in a comment and ignores both the directory and the symlink forms.
- **Files modified:** none tracked — the symlink is gitignored and disappears with the worktree.
- **Committed in:** n/a (untracked by design)

**4. [Rule 3 - Blocking] Created the gitignored empty fixture directories locally**

- **Issue:** The two `test_workspace_contract_migration.py::TestFixtureRoot` cases fail in any worktree because `test-ws/` is gitignored and `digests/`, `publish/`, `.construct/` are empty directories git cannot represent. Documented as a known-red baseline in `deferred-items.md`.
- **Fix:** `mkdir -p` those six directories locally so the suite gives a clean signal. They are gitignored and were never staged.
- **Files modified:** none tracked
- **Committed in:** n/a

### Test-design choices that differ from the plan's literal wording

- The plan's Task 2 coercion family says "invoke through the seam, and assert either a successful handler call or a failure attributable to something other than the workspace field's type". The implementation invokes through the seam with the **handler spied on** and asserts the resolved value's landing field and type directly. This is the validation-boundary form the same paragraph sanctions, applied uniformly rather than per-capability — see Decisions Made for why, and the test docstring for the note to future readers. Two unpatched real-handler cases sit beside it.
- The plan says to patch `discover_workspaces` "in the `workspaces` module namespace". It is imported lazily *inside* `_discover()` from its source module, which is what makes it patchable at `construct.views.lib.discover` — the same idiom 19-01's ordering proof uses. Patching the `workspaces` namespace would have had no effect, since no name is bound there.

---

**Total deviations:** 4 auto-fixed (2 missing critical, 2 blocking/environmental)
**Impact on plan:** No scope creep. Both hardening fixes are inside the resolver this plan owns; the two blockers are worktree mechanics. Every plan acceptance criterion is met as written.

## Issues Encountered

None beyond the worktree mechanics above. The two previously-red `test-ws` fixture cases pass once the gitignored empty directories exist locally, confirming they are environmental rather than a Phase 19 regression.

## Known Stubs

None. No `TODO`, `FIXME`, placeholder value, skipped test or unrun `<verify>` was introduced by this plan. Two forward-references remain, both explicit hand-offs with a passing test today:

- `src/construct/api/COVERAGE.md` does not exist yet — it is a later plan's artifact. What this plan owed it is the *absence of anything to exclude*: all 29 capabilities are classified and reachable, asserted by the cardinality guard, so that file can be written with an empty exclusions section.
- RESEARCH assumption **A5** (the per-request `discover_workspaces` scan's cost is negligible) remains genuinely open — see below. It is a performance assumption, not a correctness one, and no test claims otherwise.

## Flagged Assumptions Carried Forward

- **HTTP-03 / unclassified — "review manually".** The spec-less probe fallback's one unresolved row, carried forward per the plan and now the only outstanding item on HTTP-03. The two concrete residues it named are both closed: **A1** (the field map is a static snapshot of today's 29) by the classification cardinality guard, and **A2** (a string satisfies both the str-typed and Path-typed models) by the parametrised coercion family, measured at 13 `str` / 14 `Path`.
- **RESEARCH assumption A5 — the per-request scan's cost.** `discover_workspaces` is recomputed per request (D-02, and creation mode now depends on that recomputation for correctness, not just freshness). Its cost was not measured and only matters for an install root with very many children. Creation mode does **not** make this worse: it runs the same single scan the read path runs. Recorded, not resolved.
- **The `INSTALL_ROOT_FIELD` scope mismatch handed over by 19-01 is now closed** — `workspace_id` is refused there and the root comes from launch context.

## Threat Flags

None. No security-relevant surface outside the plan's `<threat_model>` was introduced. Every register row this plan owns is mitigated and covered:

| Threat | Mitigation shipped | Proven by |
|---|---|---|
| T-19-03 traversal / info disclosure | shape gate strictly before the filesystem gate, in **both** modes | `test_a_traversal_shaped_workspace_id_touches_nothing` (27 cases), `test_a_traversal_shaped_id_is_refused_in_creation_mode_too` |
| T-19-04 `workspace.init` creation mode | resolves under the launch install root only, and asserts absence — caller names, seam locates | `test_workspace_init_by_id_creates_under_the_launch_install_root_only`, `test_workspace_init_refuses_an_id_that_already_names_a_workspace`, `test_workspace_init_refuses_an_id_naming_an_existing_non_workspace` |
| T-19-17 caller-supplied `install_root` | taken from launch context when absent, `workspace_id` refused, and `install_root` still a `PATH_SHAPED_KEYS` entry the envelope refuses with 422 (19-05 completes the HTTP half) | `test_an_install_root_scoped_capability_takes_the_launch_root_when_absent`, `test_an_install_root_scoped_capability_refuses_a_workspace_id` |
| T-19-18 unclassified future capability | cardinality guard fails at registration time naming the capability | `test_the_classification_maps_cover_every_registered_capability`, `test_the_two_classification_maps_are_disjoint`, `test_create_mode_capabilities_are_themselves_classified` |

One additional hardening, recorded rather than claimed as a register row: a missing launch install root no longer escapes as an `OSError` whose traceback would carry a filesystem path (T-18-10 lineage) — see deviation 2.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Ready for the rest of Phase 19.

- **For 19-05 (envelope guard):** `install_root` remains in `PATH_SHAPED_KEYS`, and the seam now supplies it — so refusing the key outright over HTTP no longer makes the two `views.*` capabilities unreachable. That is the precondition 19-05's guard needs.
- **For 19-07 (error boundary):** every new refusal path raises the typed `CapabilityInputError` with a reason carrying no filesystem path, so the sanitizing handler has nothing extra to unpick.
- **For 19-02 / COVERAGE.md:** the exclusions section can be written empty, and the cardinality guard is the mechanical backing for that claim.
- **For Phase 22 (workspace-creation wizard):** `CREATE_MODE_CAPABILITIES` is a set, not an `if cap_id == ...`, and a third guard already catches a misspelled member. Adding a creation capability is one map entry plus one set entry.

**Concerns:** none blocking. The `test-ws` fixture failures documented in `deferred-items.md` will keep appearing in any worktree-based execution unless the empty directories are created locally.

## Self-Check: PASSED

- All 3 modified files exist on disk and carry the changes described.
- Both task commits present in `git log`: `58d158a`, `b480ea8`. Neither commit deletes a tracked file (`git diff --diff-filter=D` empty for both).
- Plan `<verification>` re-run at close-out: `tests/contract tests/integration` → **593 passed / 22 skipped**; full suite `pytest -q` → **957 passed / 22 skipped**; `test_seam_has_no_leniency_knob` → passed.
- Plan acceptance one-liner (`assert union == ids; assert disjoint`) exits 0.
- `pytest tests/contract/test_capability_seam.py -k workspace_id -q` → 83 passed (27 per family, plus the two install-root refusal cases).
- No shared orchestrator artifacts (`STATE.md`, `ROADMAP.md`) modified — worktree mode.

---
*Phase: 19-http-api-over-the-capability-registry*
*Completed: 2026-08-03*
