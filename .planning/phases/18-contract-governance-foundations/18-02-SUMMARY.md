---
phase: 18-contract-governance-foundations
plan: 02
subsystem: api
tags: [pydantic, capability-registry, contract-governance, boundary-validation, mcp]

# Dependency graph
requires:
  - phase: 18-contract-governance-foundations
    provides: "CapabilityRegistry.invoke — the seam this plan makes enforce something, and the seam that turns a model/handler mismatch into a TypeError at call time"
provides:
  - "extra=\"forbid\" on all 28 registry input models, held as a cardinality guard (forbid count == registry size) rather than a name set"
  - "tests/contract/test_capability_seam.py — permanent forbid-cardinality guard, model-to-handler binding audit, and seam-invocation coverage for the five repaired capabilities"
  - "WorkflowStatusInput / WorkspaceInitInput — two models that describe their handlers instead of a call nobody could make"
  - "Three keyword marshalling shims (knowledge.card.archive / connection.list / connection.remove) that keep the positional CLI paths alive until plan 18-03"
  - "A payload-order-independent reason string from the seam: one rejection renders one message whichever surface asked"
affects: [18-03, 18-04, 18-05, 18-06, 18-07, 18-08, phase-19-http-adapter]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cardinality-over-membership guards: assert a relationship between two live measurements plus one explicit tripwire integer, never a hand-typed name set (WR-01)"
    - "Dual-mode shims with *declared* keyword parameters instead of bare **kwargs, so the binding audit can still see the handler it is auditing"
    - "Total ordering imposed at the seam: pydantic is deterministic per payload, not across payloads, so cross-surface message parity needs an explicit sort"

key-files:
  created:
    - tests/contract/test_capability_seam.py
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/capabilities/errors.py
    - src/construct/capabilities/registry.py

key-decisions:
  - "Forbid-mode written as ConfigDict(extra=\"forbid\") per AGENTS.md § Pydantic Conventions; the two pre-existing plain-dict models were left alone rather than harmonized"
  - "The three new shims declare their keyword parameters rather than taking bare **kwargs, because a **kwargs shim is invisible to the very binding audit this plan adds"
  - "workspace.init needed a shim, not only a model swap: the seam's model_dump() flattens a nested dataclass, so DomainInitInput is re-hydrated at the handler"
  - "The seam's multi-error reason is sorted by model field declaration order (extras by name), closing a cross-surface message fork pydantic's payload-order reporting would otherwise produce"
  - "No exemption set survives in the audit — the five mismatches were repaired, not excused, because an exemption list is the allowlist D-05 refused"

patterns-established:
  - "A guard asserts a relationship plus one deliberate tripwire integer; a capability added without forbid-mode fails on arrival"
  - "Where a signature audit is structurally blind (a **kwargs handler), say so in the test docstring and cover the gap with seam-invocation tests rather than implying coverage"

requirements-completed: []

coverage:
  - id: D1
    description: "Every capability input model in the registry rejects undeclared fields, asserted as a count equal to the registry size rather than a hand-typed name set"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_every_capability_input_model_forbids_undeclared_fields"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_registry_size_is_the_declared_tripwire"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_a_previously_unforbidden_write_model_rejects_an_undeclared_field"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every capability's declared model fields bind to its handler's parameters — no capability can raise TypeError when dispatched through the seam"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_declared_fields_bind_to_the_handler (28 parametrized cases, 0 xfail)"
        status: pass
      - kind: other
        ref: "inspect.signature audit over the live registry prints an empty mismatch list (plan acceptance criterion 2)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The five capabilities whose model did not describe their handler now reach their service through the seam and return an OperationResult"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_card_archive_reaches_its_service_through_the_seam"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_connection_list_reaches_its_service_through_the_seam"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_connection_remove_reaches_its_service_through_the_seam"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_workflow_status_reaches_its_runner_through_the_seam"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_workspace_init_reaches_its_service_with_a_typed_domain"
        status: pass
    human_judgment: false
  - id: D4
    description: "The seam's multi-error reason is byte-identical across runs and independent of payload key insertion order, ordered by model field declaration"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_multi_error_reason_is_byte_identical_across_invocations"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_multi_error_reason_does_not_depend_on_payload_key_order"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_multi_error_reason_follows_model_field_declaration_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "workflow.status no longer declares fields its runner cannot receive, and workspace.init takes a typed nested domain payload rather than an open dict (T-18-13)"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_workflow_status_rejects_the_fields_its_handler_never_accepted"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_workflow_status_declares_its_own_model"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_workspace_init_rejects_a_malformed_domain_payload"
        status: pass
    human_judgment: false
  - id: D6
    description: "The positional CLI call paths for the repaired capabilities keep working until plan 18-03 normalizes cli.py (research Finding G5's ordering constraint)"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_the_positional_cli_call_paths_still_work"
        status: pass
      - kind: other
        ref: "real CLI smoke run: `workflow status`, `knowledge connection list`, `knowledge connection remove`, `knowledge card archive` against a fixture copy — all exit 0 with success output"
        status: pass
    human_judgment: false
  - id: D7
    description: "No capability expresses an open payload by relaxing its whole model; none needed a free-form typed field"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_no_capability_widens_its_whole_model_for_free_form_input"
        status: pass
    human_judgment: false

# Metrics
duration: 27 min
completed: 2026-07-27
status: complete
---

# Phase 18 Plan 02: Forbid by Default and the Model-to-Handler Binding Audit Summary

**Every one of the 28 capability input models now rejects an undeclared field, and the five capabilities whose declared model could not describe their handler were repaired rather than excused — both facts frozen as a live-introspection guard that fails the moment a capability is added unprotected.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-07-27T12:25:00Z
- **Completed:** 2026-07-27T12:52:00Z
- **Tasks:** 2 (4 commits — RED/GREEN per task)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- **Forbid-mode is now universal and enforced as arithmetic.** 14 of 28 records accepted undeclared fields; all 28 now forbid. The guard asserts `forbid_count == len(registry)` plus one explicit registry-size tripwire, so a capability added without protection fails on arrival. There is no `expected = {…}` name set anywhere in the new file.
- **The binding audit is unconditional — no exemption set survived.** All five known mismatches were repaired inside this plan and the `xfail(strict=True)` scaffolding was deleted, because an exemption list is precisely the allowlist D-05 refused.
- **The five capabilities nobody had ever called by keyword now describe what they do.** `knowledge.card.archive`, `knowledge.connection.list` and `knowledge.connection.remove` got keyword marshalling shims; `workflow.status` got its own `WorkflowStatusInput`; `workspace.init` got `WorkspaceInitInput` with a *typed* nested `DomainInitInput` (T-18-13).
- **A real cross-surface message fork was found and closed.** Pydantic reports `extra_forbidden` errors in *payload key insertion order*, so two callers submitting the same logical payload with keys in different orders received two different reason strings for one identical rejection. The seam now imposes a total order (declared fields by declaration, extras by name).
- **The positional CLI paths were verified live, not assumed.** Four `construct` commands were run against a fixture copy and all succeeded, so plan 18-03 inherits a working CLI to normalize.

## Task Commits

1. **Task 1 RED — failing forbid-cardinality and binding-audit guards** — `6567bd5` (test)
2. **Task 1 GREEN — forbid on every capability input model + deterministic reason ordering** — `be9ce47` (feat)
3. **Task 2 RED — failing seam-invocation tests for the five mismatches** — `43446b1` (test)
4. **Task 2 GREEN — the five capabilities repaired, xfail markers removed** — `f1a3d4b` (feat)

## Recorded facts the plan asked for

### Forbid counts, measured live before and after

| | Records forbidding | Registry size |
|---|---|---|
| Before this plan | **14** | 28 |
| After this plan | **28** | 28 |

**Correction to the plan's enumeration (and to research Finding G2).** The plan named **13** capabilities needing forbid-mode; the live registry had **14**. Both G2's prose ("14 of 28 already carry it") and its two lists are wrong in the same place: `workspace.validate` is listed as *already forbidding*, but it shares `WorkspacePathInput` with `workspace.init` and `workspace.status`, and that model carried no config at all. The 14 records were `graph.status`, `help.suggest`, `ingest.source`, `knowledge.card.archive`, `knowledge.card.create`, `knowledge.card.edit`, `knowledge.connection.add`, `knowledge.connection.list`, `knowledge.connection.remove`, `views.generate_data`, `workflow.status`, `workspace.init`, `workspace.status`, **`workspace.validate`**.

They resolve to **12 distinct models**, because `WorkspacePathInput` backs three records: `WorkspacePathInput`, `CardCreateInput`, `CardEditInput`, `CardArchiveInput`, `ConnectionAddInput`, `ConnectionRemoveInput`, `ConnectionListInput`, `GraphStatusInput`, `ViewsGenerateDataInput`, `WorkflowRunInput`, `IngestSourceInput`, `HelpSuggestInput`. This is exactly why the plan insisted on a count rather than a hand-typed number — the hand-typed number was wrong twice before a live measurement corrected it.

### Did any capability need a free-form typed field? **No.**

Not one of the 28 needed a `dict[str, str]` or nested escape hatch. No model was widened, and `test_no_capability_widens_its_whole_model_for_free_form_input` pins that nothing carries `extra="allow"` or `extra="ignore"`.

### The retirement list plan 18-03 inherits

**Nine positional-passthrough branches plus the `graph.status` lambda.** The arithmetic the plan predicted holds, but the *membership* of the pre-existing six differs from research Finding G5's table, which is wrong in both directions:

| # | Shim | Capability | Origin |
|---|------|-----------|--------|
| 1 | `_validate_shim` | `workspace.validate` | pre-existing — **missing from G5's list** |
| 2 | `_research_search_shim` | `research.search` | pre-existing — **missing from G5's list** |
| 3 | `_create_card_shim` | `knowledge.card.create` | pre-existing (G5) |
| 4 | `_edit_card_shim` | `knowledge.card.edit` | pre-existing (G5) |
| 5 | `_add_connection_shim` | `knowledge.connection.add` | pre-existing (G5) |
| 6 | `_ingest_source_shim` | `ingest.source` | pre-existing (G5) |
| 7 | `_archive_card_shim` | `knowledge.card.archive` | **added by this plan** |
| 8 | `_list_connections_shim` | `knowledge.connection.list` | **added by this plan** |
| 9 | `_remove_connection_shim` | `knowledge.connection.remove` | **added by this plan** |
| + | the `graph.status` lambda | `graph.status` | pre-existing positional accommodation for `services/help.py` |

G5 counted `_daily_run_shim` and `_daily_inspect_shim` among its six. Those are keyword-**only guards** — they `raise TypeError` on positional input rather than forwarding it, so they are not passthrough branches and there is nothing in them to retire. Ten such guards exist (`research.score/run/review/inspect`, `curation.run/inspect/review`, `card.evaluate`, `daily.run/inspect`) and all should be left alone. `_views_generate_handler` is adjacent but distinct: a named single parameter that binds both call forms with no branch, and therefore also nothing to retire.

**Ordering constraint restated:** retiring any of the nine before `cli.py` is normalized breaks the CLI. `test_the_positional_cli_call_paths_still_work` fails loudly if one goes early.

### Do `WorkspacePathInput` and `WorkflowRunInput` retain a consumer?

- **`WorkspacePathInput` — yes, two.** `workspace.validate` (`catalog.py:301`) and `workspace.status` (`catalog.py:312`) still use it. It was kept, and it now forbids.
- **`WorkflowRunInput` — no, zero.** `grep -rn "WorkflowRunInput" src tests` returns only its own definition and one docstring mention in the new test. `workflow.run` was deleted by D-10/CUR-05 and `workflow.status` moved to `WorkflowStatusInput`, so nothing references it. **It was retained per the plan's explicit instruction**, with an in-file comment recording the grep result. It is a deletion candidate for a later plan — see Deferred Issues.

## Files Created/Modified

- `tests/contract/test_capability_seam.py` *(new)* — 26 tests + 18 structural skips. Three layers: forbid cardinality (4), the parametrized binding audit (28 cases, of which 18 skip as `**kwargs` handlers), and seam-invocation coverage for the five repaired capabilities plus the positional-CLI regression pin.
- `src/construct/capabilities/catalog.py` — `ConfigDict(extra="forbid")` on 12 models; new `WorkspaceInitInput` and `WorkflowStatusInput`; new `_workspace_init_shim`, `_archive_card_shim`, `_list_connections_shim`, `_remove_connection_shim`; four registry records rewired.
- `src/construct/capabilities/errors.py` — `from_validation_error` takes an optional `model` and sorts errors into a payload-independent total order via a new `_error_order_key` helper.
- `src/construct/capabilities/registry.py` — one call site: hands `cap.input_model` to `from_validation_error`.

## Decisions Made

- **`ConfigDict(extra="forbid")`, not the plain-dict form.** The plan said to copy "the `ConfigDict(extra="forbid")` form already used by `CardListInput` at `catalog.py:145-147`" — but that model actually uses `model_config = {"extra": "forbid"}`. AGENTS.md § Pydantic Conventions mandates `ConfigDict`, and the plan named `ConfigDict` explicitly, so `ConfigDict` won. The two pre-existing plain-dict models (`CardListInput`, `BridgeDetectInput`) were left untouched — the plan's standing instruction is not to harmonize.
- **The new shims declare their keyword parameters instead of taking bare `**kwargs`.** A `**kwargs` handler binds any field name, so the signature audit skips it — which would have made the three shims this plan adds invisible to the audit this plan adds. They use `*args` for the positional CLI branch and named keyword-only parameters for the seam branch, so they are both dual-mode *and* auditable. This is a refinement of the plan's "same dual-mode passthrough" instruction, not a departure from it: the positional branch exists, is documented, and is on the retirement list.
- **`workspace.init` needed a shim, not just a model swap.** The plan says to point the record at a model whose fields bind to `initialize_workspace(root, domain)`. That is necessary but not sufficient: the seam dispatches `handler(**model.model_dump())`, and `model_dump()` flattens the nested `DomainInitInput` dataclass into a plain dict, so the service would have received a dict and failed on attribute access. `_workspace_init_shim` re-hydrates the already-validated dict. It uses plain named parameters (no positional branch) because `construct init` calls `initialize_workspace` directly and never touches this record.
- **`workspace.init` keeps `root`, not `workspace`.** The plan's "keep `workspace` as the public spelling" applies to the three knowledge capabilities; for `workspace.init` it names `root`/`domain` explicitly. `workspace.init` is not MCP-exposed, so no client contract is affected.
- **`ConnectionRemoveInput.conn_type` stays `str`**, coerced in the shim, mirroring `_add_connection_shim` exactly rather than introducing an unasked-for enum-typed divergence between two sibling models.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The worktree had no `.venv`**

- **Found during:** Task 1 precondition
- **Issue:** Every command in the plan is specified as `.venv/bin/python …`; `.venv` is gitignored and absent from a fresh worktree.
- **Fix:** Symlinked the main checkout's `.venv` into the worktree — the sanctioned pattern the repository's own `.gitignore` anticipates, and the same fix plan 18-01 applied.
- **Consequence recorded:** a bare `.venv/bin/python -c …` resolves `construct` to the **main checkout** via the editable install. Every `-c` acceptance-criteria command in this plan was therefore run with `PYTHONPATH` pinned to the worktree's `src`. `pytest` is unaffected (`pythonpath = [".", "src"]` resolves against the worktree rootdir).
- **Files modified:** none tracked

**2. [Rule 3 - Blocking] The worktree's gitignored test fixtures were only partially materialised**

- **Found during:** Task 1 precondition
- **Issue:** 2 tests failed on a supposedly-green baseline — `test-ws/` is gitignored and the worktree copy was missing `digests/` in both fixture workspaces. Identical to plan 18-01's deviation 2.
- **Fix:** `rsync` from the main checkout. Baseline went from `620 passed / 5 skipped / 2 failed` to `626 passed / 1 skipped / 0 failed`, so every failure this plan could cause was distinguishable from environment noise.
- **Files modified:** none tracked

**3. [Rule 2 - Missing critical] The seam's multi-error reason forked across surfaces**

- **Found during:** Task 1
- **Issue:** The plan's must-have truth requires a multi-error reason "ordered by model field declaration order rather than by payload key insertion order". Measured, pydantic does the opposite for `extra_forbidden`: `{"a":1,"zz":1,"aa":2}` and `{"a":1,"aa":2,"zz":1}` produce errors in the submitted order. An MCP client and a CLI call site building the same logical payload with keys in different orders would receive **two different reason strings for one identical rejection** — the contract fork GOV-01 exists to close. Declared-field errors (missing / constraint) already follow declaration order; only extras were affected.
- **Fix:** `CapabilityInputError.from_validation_error` gained an optional `model` parameter and now sorts errors into a total, payload-independent order (declared fields by declaration index, then undeclared by name; the sort is stable so ties keep pydantic's order). `registry.invoke` passes `cap.input_model`.
- **Scope note:** `errors.py` and `registry.py` are outside this plan's `files_modified`. Both are plan 18-01 artifacts and the change is additive — the parameter is optional, so no existing caller breaks.
- **Verification:** `test_multi_error_reason_does_not_depend_on_payload_key_order` fails without it; the full suite passes with it.
- **Committed in:** `be9ce47`

**4. [Correction] The plan's forbid enumeration was one short**

- **Found during:** Task 1
- **Issue:** The plan named 13 capabilities; the live registry had 14. `workspace.validate` shares `WorkspacePathInput` and was mis-listed as already-forbidding by research Finding G2.
- **Fix:** Hardened all 12 distinct models, closing all 14 records. Because the guard asserts a count rather than the plan's list, the correction needed no change to the test.
- **Committed in:** `be9ce47`

**5. [Correction] Research Finding G5's shim list is wrong in both directions**

- **Found during:** Task 2
- **Issue:** G5 lists six dual-mode passthrough shims, two of which (`_daily_run_shim`, `_daily_inspect_shim`) are keyword-only guards that raise on positional input, while two genuine passthrough shims (`_validate_shim`, `_research_search_shim`) are absent.
- **Fix:** Re-derived from source. The corrected retirement list is in "Recorded facts" above. The plan's predicted arithmetic — nine shims plus the `graph.status` lambda — happens to be right; its membership was not.

---

**Total deviations:** 5 (2 blocking environment repairs, 1 missing-critical fix, 2 factual corrections)
**Impact on plan:** No scope creep and no architectural change. Deviation 3 touched two files outside `files_modified`, additively, to satisfy a must-have truth the plan states explicitly. No behaviour differs from what the plan specified.

## Issues Encountered

**The binding audit is structurally blind to `**kwargs` handlers, and this is stated rather than papered over.** 18 of the 28 capabilities dispatch through a `**kwargs` shim, which binds any field name unconditionally, so `Signature.bind` proves nothing about them. Those 18 appear as explicit `pytest.skip`s with a reason, not as silent passes. This is the plan's own audit semantics (its acceptance-criteria script skips `VAR_KEYWORD` handlers), and it is why the three shims added here declare their keyword parameters — extending the blind spot to cover the very capabilities being repaired would have been self-defeating. The seam-invocation tests cover the five repaired capabilities end to end, where the signature check cannot reach.

**`Signature.bind` was chosen over a field-name subset check.** The plan's acceptance script tests only "is every declared field a handler parameter". `bind` additionally catches the reverse — a *required* handler parameter no field supplies — which is exactly how `workspace.init` failed (`missing a required argument: 'root'`). Both formulations flag the same five capabilities before the fix and none after; `bind` is simply the stronger of the two.

## Known Stubs

None. No placeholder values, no skipped tests added to mask a failure (the 18 skips are structural and explained above), and every `<verify>` in the plan was executed.

## Deferred Issues

- **`WorkflowRunInput` is now a zero-consumer model.** Retained on the plan's explicit instruction ("leave `WorkflowRunInput` in place"), with an in-file comment recording that the grep found no consumer. It describes a capability (`workflow.run`) that D-10/CUR-05 deleted. A later plan should remove it; it is not deleted here because the plan's directive was unconditional and a zero-consumer model is inert, not dangerous.
- **Not written to `.planning/WINDOWS.md`.** That ledger does not exist in this repository, and this plan ran in a parallel worktree where writing a shared cross-phase accumulating file risks the same single-writer conflict as STATE.md. Recorded here instead.

## Threat Flags

None. No new network endpoint, auth path, or file-access pattern. The trust-boundary changes all narrow rather than widen:

- **T-18-02 (Tampering — 13/14 unforbidden models, dominated by writes): mitigated.** All 28 records forbid, held by a cardinality guard rather than a list.
- **T-18-12 (Tampering — models declaring fields their handler never receives): mitigated.** Both offending models replaced; the binding audit prevents recurrence.
- **T-18-13 (EoP — `workspace.init` accepting an unvalidated free-form domain payload): mitigated.** `domain` is the typed `DomainInitInput`, validated before any directory is created — `test_workspace_init_rejects_a_malformed_domain_payload` proves a short payload is rejected at the boundary.
- **T-18-14 (Repudiation — a guard asserting a name set): mitigated.** `grep -c 'expected = {'` returns 0; the guard is a count plus one deliberate tripwire integer.
- **T-18-SC: holds. No packages were installed.**

## User Setup Required

None.

## Next Phase Readiness

- **Plan 18-03 inherits nine positional-passthrough branches plus the `graph.status` lambda**, enumerated above with their origins. The ordering constraint is pinned by a test: normalize `cli.py` first, then retire.
- **The registry-size tripwire is 28 and must become 29** when plan 18-03 registers `views validate` (D-02). That edit is deliberate, which is the point.
- **`CapabilityInputError.from_validation_error` now takes an optional third argument.** Plan 18-03's conversions should keep routing through `registry.invoke` (which supplies it) rather than calling the classmethod directly.
- **GOV-01 was not marked complete.** `requirements ready-ids` reports `0/1 ready` — the shared-ID gate correctly holds it open while sibling plans in this phase are still running. `requirements-completed` is empty here on purpose; plan 18-01's SUMMARY already flagged that GOV-01 is not satisfied until 18-03 lands.

## Self-Check: PASSED

- Created file exists on disk: `tests/contract/test_capability_seam.py`
- Task commits exist in `git log`: `6567bd5`, `be9ce47`, `43446b1`, `f1a3d4b`
- Plan `<verification>` re-run at close-out: `tests/contract/test_capability_seam.py` 26 passed / 18 skipped; full suite **652 passed, 19 skipped, 0 failed** against a `626 passed / 1 skipped / 0 failed` baseline — no new failures; forbid count and registry size measured equal at 28
- All Task 1 acceptance criteria executed: forbid count `28 28`; `grep -c 'expected = {'` → `0`; seam suite passes with 44 collected items (≥4); `tests/contract tests/unit` 377 passed
- All Task 2 acceptance criteria executed: `grep -c 'xfail'` → `0`; the binding-audit script prints `[]`; `workflow.status` model name is `WorkflowStatusInput`; full suite green; the four positional CLI paths smoke-tested against a real fixture copy
- `key_links` present: `get_registry()` appears in `tests/contract/test_capability_seam.py` and resolves against `src/construct/capabilities/catalog.py`
- No modifications to STATE.md or ROADMAP.md (worktree mode — orchestrator owns those writes)

---
*Phase: 18-contract-governance-foundations*
*Completed: 2026-07-27*
