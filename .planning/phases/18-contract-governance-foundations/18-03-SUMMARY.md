---
phase: 18-contract-governance-foundations
plan: 03
subsystem: api
tags: [capability-registry, contract-governance, typer, mcp, views, boundary-validation]

# Dependency graph
requires:
  - phase: 18-contract-governance-foundations
    provides: "CapabilityRegistry.invoke — the seam every call site in this plan is converted onto (18-01)"
  - phase: 18-contract-governance-foundations
    provides: "The corrected nine-shim retirement list and the 28→29 registry-size tripwire handoff (18-02)"
  - phase: 18-contract-governance-foundations
    provides: "views/contracts.py — the single file→model table views.validate_data reads instead of a third enumeration (18-05)"
provides:
  - "One dispatch path in the repository: all 24 remaining cli.py handler call sites plus the Streamlit form and the graph.status capability-to-capability call now go through registry.invoke"
  - "A directory-scoped, AST-based source guard that fails the moment a second path appears — no allowlist (D-05)"
  - "views.validate_data — the last hand-written command group registered as a capability, on CLI and MCP (D-02)"
  - "ViewsValidateInput + construct.views.generate.validate_build_data / ValidateReport / BUILD_DATA_RELPATH"
  - "A parity table covering a read, a write, and a views capability, each driven on the real CLI process and real MCP dispatch"
  - "A card-edit read-back regression pin: a title-only edit leaves every unnamed field and the whole body byte-identical (T-18-15)"
affects: [18-04, 18-07, 18-08, phase-19-http-adapter]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-site seam dispatch: each CLI command builds a plain payload dict and catches CapabilityInputError/CapabilityNotFoundError, rendering `ERROR {exc}` + exit 1 — one shape, 25 times, rather than a helper that hides the seam"
    - "Exclude-unset at the call site: a partial-update command omits a key the user did not supply rather than sending a materialised model default"
    - "AST-parsed source guards: a structural rule enforced over the syntax tree, so documenting the anti-pattern does not trip the guard that forbids it"
    - "Derived-and-asserted scope instead of an allowlist: the one module the guard skips is skipped because a test proves it cannot reach the registry"
    - "Parity rows carry their own environment builder and output reader, so each arm gets an identical-but-independent tree and a write capability becomes comparable"
    - "Retire a branch and invert the test that demanded it in the same commit"

key-files:
  created: []
  modified:
    - src/construct/cli.py
    - src/construct/capabilities/catalog.py
    - src/construct/views/generate.py
    - src/construct/services/help.py
    - src/construct/ui/capability_runner.py
    - tests/contract/test_capability_seam.py
    - tests/contract/test_mcp_contracts.py
    - tests/unit/test_capability_registry.py
    - tests/integration/test_surface_parity.py
    - tests/integration/test_knowledge_cli.py
    - CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md
    - CONSTRUCT-CLAUDE-spec/artifact-catalog.md

key-decisions:
  - "No capability needed exclude-unset plumbing at the seam: CardEditInput's content fields all default to None and _build_card_updates filters None, so materialised defaults cannot reach edit_card. The CLI omits unsupplied keys anyway, as a second independent guard"
  - "The 10 hand-rolled `if args: raise TypeError` guards were converted to **kwargs-only signatures rather than left alone — identical behaviour enforced by Python's binding, and it is what makes `grep -c 'if args:'` a meaningful 0"
  - "The source guard is AST-based and scoped to modules that import construct.capabilities; workflow_runner is excluded by a derived, asserted property rather than by an allowlist entry"
  - "views validate's CLI rendering and exit codes were preserved byte-for-byte, verified by diff against output captured before the edit; only the non-install-root message changed, and that is T-18-07 taking effect"
  - "Handlers that are positionally bindable but have no positional caller (list_cards, workflow.status, workspace.status, workspace.init, views.generate_data, help.suggest) were left alone: the plan names only the graph.status lambda, and list_cards is a public service signature outside this plan's scope"

patterns-established:
  - "A guard that punishes writing down its own rationale gets deleted — parse, do not grep"
  - "When a plan retires an invariant, the test asserting that invariant is replaced by its inverse in the same commit, never merely deleted"

requirements-completed: [GOV-01]

coverage:
  - id: D1
    description: "Every in-repo caller dispatches through registry.invoke — no module outside the capability package reaches a handler attribute directly"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_no_registry_aware_module_calls_a_handler_directly"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_the_guard_scans_a_plausible_number_of_modules"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_every_registry_aware_module_is_covered_by_the_guard"
        status: pass
      - kind: other
        ref: "grep -c '\\.handler(' src/construct/cli.py == 0; grep -c 'invoke(' src/construct/cli.py == 26; injected-violation probe fails the guard and passes on revert"
        status: pass
    human_judgment: false
  - id: D2
    description: "No dual-mode positional-passthrough branch remains in the catalog; graph.status is keyword-only"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_no_dual_mode_positional_passthrough_branch_survives"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_the_retired_positional_call_paths_are_gone"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_graph_status_handler_is_keyword_only"
        status: pass
      - kind: contract
        ref: "tests/contract/test_mcp_contracts.py#test_graph_status_is_keyword_only"
        status: pass
    human_judgment: false
  - id: D3
    description: "views validate is the views.validate_data registry capability, reachable on CLI and MCP by the one path"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_views_validate_data_is_registered_on_both_surfaces"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_views_validate_data_shares_the_generate_side_vocabulary"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_registry_size_is_the_declared_tripwire (28 → 29)"
        status: pass
      - kind: other
        ref: "live: `len(r.list()), r.get('views.validate_data').mcp_tool_name` prints `29 construct_views_validate_data`"
        status: pass
    human_judgment: false
  - id: D4
    description: "An agent-supplied install root is rejected by the marker guard before any path is read, and the reason names no filesystem path (T-18-07, T-18-10)"
    requirement: "GOV-01"
    verification:
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_views_validate_data_refuses_a_non_install_root_without_naming_a_path"
        status: pass
      - kind: contract
        ref: "tests/contract/test_capability_seam.py#test_views_validate_data_refuses_a_path_that_is_not_a_directory"
        status: pass
      - kind: other
        ref: "live: `r.invoke('views.validate_data', {'install_root': '/tmp'})` → success=False, message carries no `/tmp` segment"
        status: pass
    human_judgment: false
  - id: D5
    description: "The differential parity table covers a read, a write, and views, each asserted on the real CLI process and real MCP dispatch — never registry inventory"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_success_parity_across_both_real_surfaces (3 parametrized cases)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_undeclared_field_is_rejected_identically_on_both_surfaces (3 parametrized cases)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_surface_parity.py#test_the_parity_table_covers_a_read_a_write_and_a_views_capability"
        status: pass
    human_judgment: false
  - id: D6
    description: "A partial update does not blank a field the caller never named (T-18-15, this plan's authored prohibition)"
    requirement: "GOV-01"
    verification:
      - kind: integration
        ref: "tests/integration/test_knowledge_cli.py#test_card_edit_title_only_leaves_every_unnamed_field_byte_identical"
        status: pass
      - kind: other
        ref: "mutation probe: removing _build_card_updates' `is not None` filter fails this test plus 2 sibling card-edit tests; restored and re-run green"
        status: pass
    human_judgment: false
  - id: D7
    description: "views validate keeps its human output, --json shape, and exit codes"
    requirement: "GOV-01"
    verification:
      - kind: other
        ref: "diff against output captured before the edit: clean run (16 passed, exit 0), failing run (15/1, exit 1), --json, and missing-data-directory message — all four IDENTICAL"
        status: pass
      - kind: integration
        ref: "tests/integration/test_views_generate.py (_validate_slots drives the real `views validate` command)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Exit-code contracts are unchanged by conversion — a degraded curation run still exits 0 (D-15)"
    requirement: "GOV-01"
    verification:
      - kind: other
        ref: "live: `construct curation run --workspace <fixture copy>` on a provider-outage (degraded) run → exit 0"
        status: pass
    human_judgment: false

# Metrics
duration: 61 min
completed: 2026-07-30
status: complete
---

# Phase 18 Plan 03: One Dispatch Path Summary

**Every one of the 26 in-repo capability call sites now goes through `registry.invoke` — the 24 remaining `cli.py` commands, the Streamlit form, and one capability calling another — the positional-passthrough machinery those callers required is gone, and `views validate` joined the registry as the 29th capability.**

## Performance

- **Duration:** 61 min
- **Started:** 2026-07-30T15:25:00Z
- **Completed:** 2026-07-30T16:26:00Z
- **Tasks:** 3 (4 commits — Task 3 ran RED/GREEN)
- **Files modified:** 12 (0 created, 12 modified)

## Accomplishments

- **GOV-01 is now structural, not aspirational.** Plan 01 proved the seam on one capability out of 26 call sites. All 26 are converted, and a test fails the moment a 27th path appears — so the guarantee survives the next contributor rather than the next review.
- **The retirement discharged an ordering constraint rather than just deleting code.** 18-02 pinned "the positional branches must still work" with a test. That test was replaced by its inverse in the same commit that retired the branches, and so was `test_graph_status_accepts_positional_and_keyword` in `test_mcp_contracts.py`. A retired accommodation whose test still demands it is not retired.
- **The data-loss prohibition was tested, not asserted.** A title-only `card edit` is proven to leave every other frontmatter field and the entire markdown body byte-identical, and a mutation probe confirms the test is load-bearing.
- **The parity table went from 1 row to 3 and grew a write.** Each arm now builds its own identical-but-independent environment, which is what makes a write capability comparable at all — a shared tree would have the second arm collide with the first arm's card and the test would compare "created" against "already exists".
- **One capability moved out of the binding audit's blind spot.** Retiring `_validate_shim`'s `*args` gave `workspace.validate` a declared parameter, so signature-audited capabilities went 10 → 12 (of 29) and structural skips went 18 → 17.

## Task Commits

1. **Task 1 — every `cli.py` command dispatches through the seam** — `c551cc7` (feat)
2. **Task 2 — the last in-repo callers routed, positional branches retired, source guard added** — `1f562ac` (feat)
3. **Task 3 RED — failing guards for `views.validate_data` and the three-kind parity table** — `cda5c28` (test)
4. **Task 3 GREEN — `views validate` registered as a capability** — `6868994` (feat)

## Recorded facts the plan asked for

### Every converted call site (24 in Task 1, plus `views validate` in Task 3)

`grep -c '\.handler(' src/construct/cli.py` went **24 → 0**; `grep -c 'invoke(' src/construct/cli.py` is **26** (25 dispatch sites + the `_invoke_handler`-free import line count is incidental — the 25 sites are enumerated below and `knowledge.card.list` was already converted by Plan 01).

| # | CLI command | Capability | Old form | Notes |
|---|---|---|---|---|
| 1 | `construct validate` | `workspace.validate` | positional `handler(path)` | returns `ValidationReport`, not `OperationResult` |
| 2 | `construct status` | `workspace.status` | positional `handler(path)` | returns a list of items |
| 3 | `construct help --suggest` | `help.suggest` | positional `handler(workspace)` | |
| 4 | `construct workflow status` | `workflow.status` | positional `handler(workspace)` | |
| 5 | `construct ingest source` | `ingest.source` | mixed `handler(workspace, source=…)` | 12-field payload |
| 6 | `construct ask domain` | `ask.domain` | keyword | |
| 7 | `construct bridge detect` | `bridge.detect` | keyword | |
| 8 | `construct research search` | `research.search` | `**handler_kwargs` | conditional payload preserves the exactly-one-mode contract |
| 9 | `construct research score` | `research.score` | `**handler_kwargs` | |
| 10 | `construct research run` | `research.run` | `**handler_kwargs` | |
| 11 | `construct research review` | `research.review` | `**handler_kwargs` | decisions map still crosses as a declared field |
| 12 | `construct research inspect` | `research.inspect` | `**handler_kwargs` | |
| 13 | `construct curation run` | `curation.run` | keyword | degraded-exits-0 contract re-verified live |
| 14 | `construct curation inspect` | `curation.inspect` | keyword | |
| 15 | `construct curation review` | `curation.review` | `**handler_kwargs` | |
| 16 | `construct daily run` | `daily.run` | keyword | |
| 17 | `construct daily inspect` | `daily.inspect` | keyword | |
| 18 | `construct knowledge card create` | `knowledge.card.create` | positional `handler(ws, card_data, author=…)` | CLI stopped hand-building `card_data`; the shim's `_build_card_data` is now the only marshaller |
| 19 | `construct knowledge card edit` | `knowledge.card.edit` | positional `handler(ws, id, updates, author=…)` | **partial update — see below** |
| 20 | `construct knowledge card archive` | `knowledge.card.archive` | positional | |
| 21 | `construct card evaluate` | `card.evaluate` | `**handler_kwargs` | |
| 22 | `construct knowledge connection add` | `knowledge.connection.add` | positional + enum | payload carries `ctype.value`, the shape an MCP client sends |
| 23 | `construct knowledge connection remove` | `knowledge.connection.remove` | positional + enum | |
| 24 | `construct knowledge connection list` | `knowledge.connection.list` | mixed | |
| 25 | `construct views validate` | `views.validate_data` | **no capability existed** | Task 3 — the command body became the capability |

Non-CLI callers converted in Task 2: `ui/capability_runner.py:130` (Streamlit form) and `services/help.py:141` (the `graph.status` capability-to-capability call, research OQ-D).

### Which capabilities took exclude-unset treatment? **None needed it at the seam — and that is a measured finding, not an omission.**

The plan anticipated that `model_dump()` materialising defaults would blank stored content, and asked which capabilities needed `exclude_unset` semantics. Measured, **zero** do, because three independent guards already stand between a materialised default and a stored value:

1. **`CardEditInput`'s content fields all default to `None`** (`title`, `confidence`, `source_tier`, `lifecycle`, `summary`). There is no non-`None` default that could overwrite anything.
2. **`_build_card_updates` filters on `is not None`**, so a materialised `None` never enters the `updates` dict that `edit_card` applies via `raw.update(updates)`.
3. **`edit_card` re-guards `_summary`** (`if summary is not None`), which matters because that is the one field written into the markdown *body* — and `_replace_summary_section(body, str(None))` would have written the literal text `"None"` over the user's prose.

`knowledge.card.edit` is the only genuine partial update in the catalog. `ingest.source` looks similar but is a create, and its optional metadata fields were already being passed explicitly as `None` by the pre-conversion CLI, so nothing changed. `research.review` / `curation.review` materialise `decisions=None, approve_all=False, reject_all=False`, which is indistinguishable from the pre-conversion behaviour because both paths construct the same input model.

**A fourth guard was added anyway**, at the CLI call site: `card edit` builds its payload from only the options the user actually supplied, omitting the rest. Guard 2 alone is sufficient today; guard 4 means a future caller must go out of its way to express "blank this". Given this repository has destroyed user prose twice through this class of defect (`archive_card`, commit `4e2b909`, unrecoverable), belt-and-braces was the right trade.

**The mutation probe that proves this is not hand-waving:** removing `_build_card_updates`' `is not None` filter makes `test_card_edit_title_only_leaves_every_unnamed_field_byte_identical` fail, along with two sibling card-edit tests. Worth recording *how* it fails: `KnowledgeCard`'s required-field validation rejects the `None`s, so a frontmatter blanking attempt surfaces as a clean rejection rather than silent corruption. The genuinely dangerous field is `_summary`, guarded separately at guard 3.

### A2 verdict — `pipelines/workflow_runner.py:201` is **OUT of scope**, and here is the evidence

`step.handler(**kwargs)` is **not** a capability handler:

- `WorkflowStep` is a local dataclass (`workflow_runner.py:23-30`) declaring `handler: Callable[..., OperationResult]` **and** `handler_kwargs: dict | None`. `CapabilityRecord` has no `handler_kwargs` field — `hasattr(CapabilityRecord, "handler_kwargs")` is `False`.
- `workflow_runner.py` never imports `construct.capabilities` (asserted on the parsed import statements, including function-scoped imports).
- `grep -rn 'WorkflowStep('` finds constructions **only in `tests/unit/test_workflow_runner.py`**, all passing plain local callables. No production code builds a `WorkflowStep` from a `CapabilityRecord`.

Two different abstractions sharing an attribute name. This is recorded as `test_workflow_runner_is_not_a_capability_caller`, which asserts all three facts — so the reason the guard skips this module is **derived and checked**, not an allowlist entry. The day `workflow_runner` imports the capability package, that test fails and the module joins the guard. This is how D-05's refusal of allowlists was honoured with a genuine exception present.

### `views validate` CLI output, before and after

Captured on a purpose-built install root (`AGENTS.md` marker + copies of both `test-ws` fixtures) **before any edit**, and re-run after. All four cases `diff`-identical:

| Case | Before | After |
|---|---|---|
| Clean run (human) | `Views data validation: 16 passed, 0 failed, 0 missing` + 16 `✓` lines, **exit 0** | **identical** |
| Failing run (corrupt `domains.json`) | `15 passed, 1 failed, 0 missing`, `✗ domains.json` + parse error, **exit 1** | **identical** |
| `--json` | `{"results": [...], "all_passed": true}` | **identical** |
| Valid install root, no build | `ERROR: No views data directory at <root>/views/build/data`, **exit 1** | **identical** |

**One case changed, deliberately:**

| Case | Before | After |
|---|---|---|
| `--install-root /tmp` (a real directory, no CONSTRUCT marker) | `ERROR: No views data directory at /tmp/views/build/data`, exit 1 | `ERROR: not a CONSTRUCT installation: missing AGENTS.md (at /tmp)`, exit 1 |

This is T-18-07 taking effect, not a regression. Registration made `install_root` agent-supplied over MCP, so `install_root_error` became a boundary control and now runs first. The exit code is unchanged. The path in the CLI rendering is appended by the *local* caller — the seam's own reason carries no path segment, which is what `views generate` already does and what `install_root_error`'s docstring prescribes.

### Test counts

| Stage | Passed | Skipped | Failed |
|---|---|---|---|
| Baseline (worktree, after fixture repair) | 684 | 19 | 0 |
| After this plan | **703** | **18** | **0** |

Net **+19 tests**. The skip count *dropped* by one because `workspace.validate`'s shim gained a declared parameter and left the binding audit's `**kwargs` blind spot — signature-audited capabilities went 10/28 → 12/29.

## Files Created/Modified

- `src/construct/cli.py` — 24 commands converted; `views validate`'s body extracted, leaving rendering + exit code; `CardAuthor` / `ConnectionAuthor` imports dropped as dead.
- `src/construct/capabilities/catalog.py` — 9 positional-passthrough branches retired, 10 hand-rolled positional guards converted to `**kwargs`-only signatures, the `graph.status` lambda replaced by keyword-only `_graph_status_handler`, new `ViewsValidateInput` + `_views_validate_handler` + `views.validate_data` record, RT-01/RT-02 holdout comment retired.
- `src/construct/views/generate.py` — new `validate_build_data()` / `ValidateReport` / `BUILD_DATA_RELPATH`; reads `views/contracts.py` rather than re-enumerating the file→model map.
- `src/construct/services/help.py` — the `graph.status` call goes through the seam.
- `src/construct/ui/capability_runner.py` — the Streamlit form dispatches through the seam and renders `CapabilityInputError` inline.
- `tests/contract/test_capability_seam.py` — tripwire 28→29; the AST source guard plus its two scope/non-vacuity guards; the A2 verdict test; the retired-positional-paths inverse; four `views.validate_data` contract tests.
- `tests/integration/test_surface_parity.py` — `ParityCase` NamedTuple with per-row environment builder and output readers; 3 rows; undeclared-field rejection parametrized over the table.
- `tests/integration/test_knowledge_cli.py` — the title-only read-back regression pin.
- `tests/contract/test_mcp_contracts.py` — `construct_views_validate_data` added to the tool-name set and payload table; `test_graph_status_accepts_positional_and_keyword` inverted.
- `tests/unit/test_capability_registry.py` — `views.validate_data` added to the expected-id set.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — `views.validate_data` row added; `construct views validate` removed from the "independent path" table; holdout note narrowed; counts 28/22 → 29/23.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` — one-line supersession note naming Phase 18 and D-02; the ADR is annotated, not rewritten.

## Decisions Made

- **The 10 keyword-only *guards* were converted, not left alone.** 18-02's summary says to leave them; its concern was that retiring a guard would let positional calls silently succeed. Converting `(*args, **kwargs)` + `if args: raise TypeError` into `(**kwargs)` preserves the semantics exactly while letting Python's own binding enforce it — and it is what makes the plan's `grep -c 'if args:' == 0` criterion meaningful rather than something to argue around. No behaviour changed; `TypeError` is still what a positional caller gets.
- **The source guard parses instead of grepping.** A line-regex for `.handler(` flagged three files, two of which were *comments explaining the retired pattern*. A guard that punishes writing down its own rationale gets deleted by the next person, so the guard walks the AST for `Call(func=Attribute(attr="handler"))`.
- **The guard is scoped to modules that import `construct.capabilities`.** This is what let the genuine A2 exception exist without an allowlist: a module that cannot obtain a `CapabilityRecord` cannot be calling a capability handler. The narrowing is itself asserted (`test_every_registry_aware_module_is_covered_by_the_guard`) so it cannot silently collapse.
- **Positionally-bindable handlers with no positional caller were left alone.** `list_cards`, `workflow.status`, `workspace.status`, `workspace.init`, `views.generate_data` and `help.suggest` still bind positionally. The plan names only the `graph.status` lambda, and `list_cards` is a public service signature in `services/knowledge.py` outside this plan's files. The structural guarantee is carried by the source guard, which proves nothing *calls* them that way.
- **`views validate --json` kept its `{"results", "all_passed"}` shape** rather than being harmonised onto `_display_result`'s `OperationResult` envelope. Consistency would have been nicer; preserving observable CLI behaviour is worth more, and the parity harness absorbs the difference in a per-row reader.
- **`views generate`'s CLI path was not converted.** D-03 keeps it independent and the plan's scope note registers `views validate` only. The artifact catalog and adr-0005 now say the holdout is *retired for validate, narrowed for generate* rather than closed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The worktree had no `.venv` and incomplete fixtures**

- **Found during:** Task 1 precondition
- **Issue:** `.venv` and `test-ws/` are gitignored, so a fresh worktree has neither. Identical to 18-01 deviation 1–2 and 18-02 deviation 1–2.
- **Fix:** Symlinked the main checkout's `.venv` (the pattern `.gitignore` explicitly anticipates) and `rsync`'d `test-ws/`. Baseline then measured **684 passed / 19 skipped / 0 failed**, matching the handoff exactly — so every failure this plan could cause was distinguishable from environment noise.
- **Files modified:** none tracked

**2. [Rule 2 - Missing critical] Two tests asserted invariants this plan retires**

- **Found during:** Task 2
- **Issue:** `test_the_positional_cli_call_paths_still_work` (18-02, `test_capability_seam.py`) and `test_graph_status_accepts_positional_and_keyword` (ING-05, `test_mcp_contracts.py`) both demanded the positional call forms the plan instructs me to retire. Deleting them would have removed coverage; leaving them would have blocked the retirement.
- **Fix:** Each was **replaced by its inverse** in the same commit as the retirement, with a docstring recording what it used to assert and why the assertion flipped.
- **Scope note:** `test_mcp_contracts.py` is outside `files_modified`. The change is forced by the plan's own instruction to replace the `graph.status` dual-binding lambda.
- **Committed in:** `1f562ac`

**3. [Rule 2 - Missing critical] Registering a capability tripped four other deliberate tripwires**

- **Found during:** Task 3 GREEN
- **Issue:** The plan names one tripwire (28→29 in `test_capability_seam.py`). Four more exist: the expected-id set in `tests/unit/test_capability_registry.py`, the MCP tool-name set and the `_payload_for` payload table in `tests/contract/test_mcp_contracts.py`, and two artifact-catalog row guards. `_payload_for` raised `KeyError` for the unknown tool, which surfaced as a *never-raise* violation rather than a missing-row message.
- **Fix:** All updated to include `views.validate_data` / `construct_views_validate_data`, none loosened. The artifact catalog also needed `construct views validate` moved out of its "independent path" table and the registry counts corrected 28/22 → 29/23.
- **Files modified:** `tests/unit/test_capability_registry.py`, `tests/contract/test_mcp_contracts.py`, `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — the first two outside `files_modified`, the third named in the plan's Task 3 file list only implicitly.
- **Committed in:** `6868994`

**4. [Improvement, unasked] `research search --queries ""` no longer tracebacks**

- **Found during:** Task 1 smoke testing
- **Issue:** Pre-conversion, an empty `--queries` list reached `_research_search_shim`, which constructed `ResearchSearchInput` and let the resulting `ValidationError` escape as a raw traceback — the thing AGENTS.md § Error Handling forbids.
- **Fix:** Falls out of the conversion for free. The seam now rejects it: `ERROR Invalid input for capability 'research.search': <root>: Value error, queries must contain at least one item when set`, exit 1.
- **Committed in:** `c551cc7`

**5. [Correction] The plan's Task 2 criterion `grep -rn 'handler(' … | grep -vc 'invoke'` counted a docstring**

- **Found during:** Task 2
- **Issue:** The criterion returned 1 — a docstring in `capability_runner.py` recording the pattern that had just been retired.
- **Fix:** Reworded both prose mentions to describe the retired call without writing the literal `handler(` token. The criterion now returns 0 honestly rather than by suppression, and the AST guard is what actually proves the property.
- **Committed in:** `1f562ac`

---

**Total deviations:** 5 (1 blocking environment repair, 2 missing-critical test corrections, 1 unasked improvement, 1 criterion correction)
**Impact on plan:** No scope creep and no architectural change. Deviations 2 and 3 touched four files outside `files_modified`, all of them tests or spec rows made false by changes the plan explicitly instructs. No behaviour differs from what the plan specified, with the one documented exception of the `views validate` non-install-root message, which is T-18-07's intended effect.

## Issues Encountered

**The plan's key-links regex is over-escaped, as the handoff warned.** `pattern: "invoke\\("` fails the automated link check. The targets are real and now doubly so: `src/construct/services/help.py` and `src/construct/ui/capability_runner.py` both contain `invoke(` calls resolving to `CapabilityRegistry.invoke` at `registry.py:47`. Plan-authoring defect, not a wiring gap.

**The parity harness needed a structural change to admit a write capability, and the reason is worth recording.** The original harness built one workspace and drove both arms against it. For a read that is fine; for `knowledge.card.create` the second arm would hit a duplicate-id rejection, and the test would have compared "created" against "already exists" while still asserting *something*. Each arm now builds its own identical-but-independent tree. This is the difference between a parity test and a test that merely runs twice.

**`views validate`'s two pre-file failure modes could not be folded into the per-file report.** An install-root refusal and a missing data directory are not verdicts about a *file*, and rendering them through the per-file table would have put a fabricated filename in front of the user. They are distinct fields on `ValidateReport` and distinct branches in the CLI rendering, which is what let the legacy `ERROR: No views data directory at <path>` message survive byte-identical while the seam's own reason stays path-free.

## Known Stubs

None. No placeholder values, no skipped tests added to mask a failure, and every `<verify>` block in the plan was executed. The 17 structural skips in `test_capability_seam.py` are the pre-existing `**kwargs` binding-audit blind spot documented by 18-02 — one fewer than before this plan, and each carries an explicit reason.

## Deferred Issues

- **`views generate`'s CLI path remains independent of the registry (D-03).** The views group is now half-converted: validate dispatches through the seam, generate does not. Recorded in `artifact-catalog.md` and `adr-0005` as narrowed rather than closed. Converting it is a decision, not a cleanup — `views.generate_data` deliberately carries no `cli_name`.
- **17 of 29 capabilities remain structurally invisible to the binding audit** because their handlers take `**kwargs`. Unchanged in kind from 18-02, improved by one. Giving each shim declared keyword parameters would close it; that is a mechanical but broad edit no plan has yet owned.
- **`WorkflowRunInput` is still a zero-consumer model**, carried forward from 18-02's deferred list. Untouched here.
- **Not written to `.planning/WINDOWS.md`.** That ledger does not exist in this repository, and this plan ran in a parallel worktree where writing a shared cross-phase file risks the single-writer conflict STATE.md has. Recorded here instead.

## Threat Flags

None. No new network endpoint, auth path, or file-access pattern beyond the one the plan specifies and guards.

- **T-18-01 (Tampering — every payload path bypassing `input_model`): mitigated.** All 26 call sites converted; the AST source guard fails on a new bypass and was verified to do so by an injected violation.
- **T-18-07 (Tampering — `views.validate_data`'s newly agent-supplied `install_root`): mitigated.** `install_root_error` runs before any path is read. The refusal test plants a deliberately malformed `domains.json` inside the rejected root, so a guard that ran late would report a parse error instead of a refusal.
- **T-18-10 (Information disclosure — rejection reasons rendered to an MCP client): mitigated.** The install-root refusal is asserted to contain no segment of the rejected path, its basename, or its parent. The CLI appends the path itself, which is the local-caller convention.
- **T-18-15 (Tampering / data loss — `model_dump()` materialising a default over a stored value): mitigated.** Four independent guards, a read-back assertion, and a mutation probe proving the assertion is load-bearing.
- **T-18-16 (EoP — registering `spike run --tool-path`): out of scope by decision, and now stated where a reader will look.** `artifact-catalog.md` records that `spike` stays out of the registry because `--tool-path` is an arbitrary-executable primitive, so it is not closed opportunistically by someone tidying the "independent path" table.
- **T-18-SC: holds. No packages were installed.**

## User Setup Required

None.

## Next Phase Readiness

- **GOV-01 is satisfied.** One dispatch path exists in the repository and a test fails the moment a second appears. `requirements-completed: [GOV-01]` is declared here; REQUIREMENTS.md itself is left to the orchestrator's post-wave write, since the phase's shared-ID gate spans sibling plans.
- **Phase 19's HTTP adapter inherits `views.validate_data` for free.** It carries both `cli_name` and `mcp_tool_name` and is reached only through `registry.invoke`, whose signature is unchanged and still knob-free.
- **The parity table is the extension point.** Phase 19 joins by adding a column (a third arm) to `ParityCase`, not by forking the suite. Rows already carry their own environment builder and output reader, so a capability whose HTTP response shape differs needs a reader, not new test logic.
- **The registry-size tripwire is now 29.** The next capability must bump it deliberately, which is the point.
- **The source guard will fail loudly if a future module calls a handler directly** — including a module that does not exist yet, because the scan is by directory and the scope is by import, not by name list.

## Self-Check: PASSED

- Modified files exist on disk: all 12 verified present via `git diff --stat e6b5c01..HEAD`
- Task commits exist in `git log`: `c551cc7`, `1f562ac`, `cda5c28`, `6868994`
- Plan `<verification>` re-run at close-out: `grep -c '\.handler(' src/construct/cli.py` → **0**; `tests/integration/test_surface_parity.py tests/contract/test_capability_seam.py` → **59 passed / 17 skipped**; full suite → **703 passed / 18 skipped / 0 failed** against a 684/19/0 baseline, no new failures
- Task 1 acceptance criteria executed: `.handler(` → 0; `invoke(` → 26 (≥20); card-edit read-back test passes and fails under mutation; `curation run` on a degraded run → exit 0; every converted site smoke-tested live against a fixture workspace copy
- Task 2 acceptance criteria executed: `grep -rn 'handler(' help.py capability_runner.py | grep -vc 'invoke'` → 0; `grep -c 'if args:' catalog.py` → 0; `graph.status` params `['workspace']`, positional raises `TypeError`; the source guard verified to fail on an injected violation and pass on revert
- Task 3 acceptance criteria executed: `29 construct_views_validate_data`; `views validate` output diff-identical to the pre-edit capture on all four cases; `/tmp` rejection contains no path segment; parity suite passes with 3 table rows; `grep -c 'RT-01\|RT-02'` 1 → 0; adr-0005 carries a line naming Phase 18 and D-02
- No modifications to STATE.md or ROADMAP.md (worktree mode — orchestrator owns those writes)

---
*Phase: 18-contract-governance-foundations*
*Completed: 2026-07-30*
