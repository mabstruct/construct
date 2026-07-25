---
phase: 15-views-generate-data-resolution
plan: 03
subsystem: capabilities
tags: [capability-registry, cli, typer, mcp, install-root, allowlist, d-03, d-05, tdd]

requires:
  - phase: 15
    plan: 01
    provides: "`construct.views.generate` importable from the installed package, so a registry handler can call it at all"
  - phase: 15
    plan: 02
    provides: "`generate()` returning success=True with zero validation errors, so a real handler can report meaningful success"
provides:
  - "`views.generate_data` capability backed by a real handler, reachable over MCP as `construct_views_generate_data`"
  - "`construct views generate` CLI command (D-03 independent path, not registry-routed)"
  - "`--install-root` as the single path option on both views commands"
  - "`ViewsGenerateDataInput.install_root` — the contract the generator actually implements"
  - "A 4-entry `_KNOWN_BROKEN` allowlist owned entirely by Phase 16"
  - "A characterisation test pinning the writer/validator divergence carried from 15-02"
affects: [15-04, 15-05, 16, 17, views, capabilities]

tech-stack:
  added: []
  patterns:
    - "Named single-parameter handler (not `lambda **kwargs`) so one registry record binds both positional and keyword callers"
    - "Report→OperationResult mapping that keeps fatal and advisory channels lexically distinct in the message"
    - "Characterisation test that pins a known defect's exact shape and is designed to go red when the defect is fixed"

key-files:
  created: []
  modified:
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/unit/test_capability_registry.py
    - tests/integration/test_views_generate.py
    - tests/contract/test_doc_command_references.py
    - tests/contract/test_mcp_contracts.py
    - USER-TEST-PLAYBOOK-v03.md

key-decisions:
  - "GenerateReport→OperationResult: success = report.success AND no validation_errors; each validation error becomes an OperationError(field='views.validation'); warnings live in message and data only, never in errors"
  - "`-w` dropped entirely rather than kept as an alias — a workspace-lettered short flag for an install-root option perpetuates the exact misnaming D-05/D-06 exist to correct"
  - "The playbook's `$WS` held a single workspace, so an `$INSTALL_ROOT` was introduced and `$WS` nested inside it; every non-views `-w \"$WS\"` invocation is unchanged"
  - "The writer/validator divergence carried from 15-02 was NOT resolved here — it is a contract decision with Phase 16/17 consequences, and it is pinned by an explicit characterisation test instead of being silently decided"

requirements-completed: [FIX-01]

coverage:
  - id: D1
    description: "`views.generate_data` resolves to a real handler returning success against a scaffolded install root, by both call forms"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/unit/test_capability_registry.py#test_views_generate_data_handler_is_not_a_permanent_failure"
        status: pass
      - kind: other
        ref: "grep -c 'Not yet implemented' src/construct/capabilities/catalog.py == 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "`ViewsGenerateDataInput` declares `install_root` and not `workspace` (D-05)"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/unit/test_capability_registry.py#test_views_generate_data_input_declares_install_root"
        status: pass
    human_judgment: false
  - id: D3
    description: "Validation errors are fatal; content warnings alone never yield success=False (D-04)"
    requirement: FIX-01
    verification:
      - kind: unit
        ref: "tests/unit/test_capability_registry.py#test_views_generate_validation_errors_are_fatal_and_surfaced"
        status: pass
      - kind: unit
        ref: "tests/unit/test_capability_registry.py#test_views_generate_warnings_alone_are_advisory"
        status: pass
    human_judgment: false
  - id: D4
    description: "`construct views generate --install-root <root>` exists, runs the generator and exits 0 on a scaffolded root"
    requirement: FIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_views_generate_cli_command_generates_clean"
        status: pass
      - kind: other
        ref: "`construct views generate --help` and `views validate --help` both show --install-root; neither shows a workspace-named option"
        status: pass
    human_judgment: false
  - id: D5
    description: "`_KNOWN_BROKEN` holds exactly the four Phase 16 entries and both halves of the guard pass"
    requirement: FIX-01
    verification:
      - kind: contract
        ref: "tests/contract/test_doc_command_references.py — 34 passed; exact-set assertion on the 4 remaining keys; diff is 1 deletion / 0 insertions"
        status: pass
    human_judgment: false
  - id: D6
    description: "`views validate` confirms all 8 generated data files pass their contracts"
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_views_validate_does_not_yet_accept_generated_bytes — 3 of 8 files fail on the raw bytes"
        status: fail
    human_judgment: true
    rationale: "NOT ACHIEVED, and deliberately not repaired inside this plan. generate() validates an adapted projection but writes the raw parser dict, so views validate rejects stats.json, <ws>/connections.json and <ws>/events.json. Resolving it means choosing which shape is canonical — a Phase 16/17 SPA contract decision (Rule 4), not an auto-fix. The current state is pinned by a characterisation test rather than hidden."

duration: 38min
completed: 2026-07-19
status: complete
---

# Phase 15 Plan 03: Wire the real views.generate_data handler Summary

**`views.generate_data` now runs the real generator behind an `install_root`-named contract and reports validation errors as fatal and content warnings as advisory; `construct views generate` exists as an independent CLI path; both views commands take `--install-root`; and the known-broken allowlist has shrunk to its four Phase 16 entries — but `views validate` still rejects 3 of the 8 files the generator writes, because the generator validates a projection and writes the raw dict, and that contract fork is escalated rather than silently decided.**

## Performance

- **Duration:** 38 min
- **Tasks:** 3
- **Files modified:** 7
- **Suite:** 453 → 458 passing

## Task Commits

1. **Task 1 RED: failing tests for the real handler** — `ab625ad` (test)
2. **Task 1 GREEN: wire the handler, rename to `install_root`** — `e6d82ad` (feat)
3. **Task 2 RED: failing test for the CLI command** — `7283044` (test)
4. **Task 2 GREEN: `views generate` command + `--install-root` on both** — `016b471` (feat)
5. **Task 3: delete the views entry from `_KNOWN_BROKEN`** — `cb20b6b` (test)

## The resolved discretion item: GenerateReport → OperationResult

| OperationResult field | Mapping |
|---|---|
| `success` | `bool(report.success) and not report.validation_errors` — warnings never enter this expression |
| `errors` | one `OperationError(field="views.validation", reason=<error>, suggestion="")` per `validation_errors` entry |
| `message` | names build id, files written, validation-error count and content-warning count as four separately labelled quantities. On success with warnings present it appends "the run succeeded; the warnings are advisory and describe source content, not contract violations" |
| `data` | `{build_id, workspace_stats, total_files_written, warnings}` so an MCP caller sees the outcome without a second call |

Errors and warnings are never merged into one list, and the warning list is reachable only through `data` and the message — so no caller can mistake an advisory for a failure.

## The `-w` decision and the call sites it moved

`-w` was **dropped outright** on both views commands, not retained as an alias. Keeping a workspace-lettered short flag on an install-root option would have preserved in muscle memory precisely the confusion D-05/D-06 exist to remove.

Two call sites needed adjustment as a result — one more than the plan predicted:

1. The two `USER-TEST-PLAYBOOK-v03.md` invocations (D-07, anticipated).
2. `tests/contract/test_mcp_contracts.py` — a hardcoded MCP payload table keyed `{"workspace": ws}` for `construct_views_generate_data`. Not anticipated by the plan; see deviations.

## The playbook shell variable did need to change

`$WS` held a **single workspace** (`construct init "$WS"` scaffolds `domains.yaml`, `cards/`, `log/` directly inside it), so passing it to an install-root-scoped command would have discovered zero workspaces and validated an empty build. An `$INSTALL_ROOT` was introduced and `$WS` nested inside it as `$INSTALL_ROOT/ai-gateways`, matching the `ai-gateways` domain slug the playbook already instructs the user to enter. Every non-views `-w "$WS"` invocation in the file is byte-identical to before; the diff is the §0.2 setup block, an explanatory note, and the two views lines.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `OperationError` was not imported into `catalog.py`**

- **Found during:** Task 1.
- **Issue:** The new handler constructs `OperationError` on its failure path, but `catalog.py` imported only `OperationResult`. The two named plan tests both exercise the *success* path, so the list comprehension never evaluated and the suite stayed green over a latent `NameError` that would have fired on the first real validation failure — the exact path the handler exists to report.
- **Fix:** Added `OperationError` to the existing `construct.services.knowledge` import block, and added two tests (`..._validation_errors_are_fatal_and_surfaced`, `..._warnings_alone_are_advisory`) that drive the mapping through a monkeypatched `generate`. These cover the two `<behavior>` clauses the plan declared but its two named tests could not reach.
- **Mutation-checked:** removing the import again turns the error-path test red. The guard has teeth.
- **Committed in:** `e6d82ad`

**2. [Rule 3 - Blocking] MCP contract payload table still keyed on the old field name**

- **Found during:** Task 1, full-suite run.
- **Issue:** `tests/contract/test_mcp_contracts.py::test_every_mcp_handler_invokes_without_type_error` builds each tool's payload from a hardcoded table, which still passed `{"workspace": ws}`. After the D-05 rename the handler raised `TypeError: unexpected keyword argument 'workspace'`. This is the RT-03 gate working correctly.
- **Fix:** One key renamed to `install_root`, and its value changed to `str(Path(ws).parent)` with a comment — passing the workspace itself would have type-checked while modelling the install-root scope wrongly, which is the misuse D-05 exists to prevent.
- **File outside the plan's `files_modified`,** but a mechanical one-key consequence of the rename, not scope expansion.
- **Committed in:** `e6d82ad`

### Acceptance-criterion arithmetic

**3. `grep -c 'lambda \*\*kwargs' src/construct/capabilities/catalog.py` outputs 2, not 0**

The two survivors are at `catalog.py:373` and `:391` — the `help.suggest` and `bridge.detect` records. Neither is the views handler, both predate this plan, and rewriting them is RT-01/RT-02 cleanup that v0.4.1 explicitly defers. The criterion's intent — no keyword-slurping lambda on the **views** record — holds: the views handler is now the named module-level `_views_generate_handler`. Same class as Plan 01's and Plan 02's criterion arithmetic.

**4. Task 2's "full suite green" could not hold until Task 3 landed**

Creating `construct views generate` makes the command resolve, which fires `test_known_broken_entries_are_still_broken[views generate]` — by design, since that paired assertion is what forces the allowlist deletion. The suite was green at every other point and green again after Task 3. This is the guard working, not a defect.

---

**Total deviations:** 2 auto-fixed (Rule 3), 2 criterion clarifications, 1 escalated blocker (below).
**Impact on plan:** No scope creep. Both prohibitions held — nothing was added to or reworded in `_KNOWN_BROKEN` (diff is 1 deletion, 0 insertions), and the views group was **not** migrated into the capability registry.

## Carried-forward blocker: `views validate` does not accept the bytes `views generate` writes

**This plan's Task 2 `<done>` criterion and `<verification>` step 2 are NOT met**, and the shortfall is deliberate.

`generate()` validates an **adapted projection** of each file (its per-file adapters remap `totals` → `total_cards`, `connects_to` → `connections`, `created` → `created_at`, and so on) but writes the **raw parser dict**. `views validate` applies the same Pydantic models to the raw bytes with **no adapter**. The two therefore disagree by construction. On a freshly scaffolded install root:

| File | `generate()` says | `views validate` says |
|---|---|---|
| `bridges.json`, `domains.json`, `articles.json`, `<ws>/cards.json`, `<ws>/digests.json` | pass | pass |
| `stats.json` | pass | **fail** — writes `totals`/`by_confidence`/`by_lifecycle`/`activity_last_30d`; `StatsFile` declares `total_cards`/`total_connections`/… |
| `<ws>/connections.json` | pass | **fail** — writes a `type_counts` block `ConnectionsFile` does not declare |
| `<ws>/events.json` | pass | **fail** — writes `action`/`agent`/`detail`/`result`/`target`/`ts`; `EventRecord` declares `timestamp`/`type`/`actor`/`card_id`/`details` |

**This is pre-existing, not a regression.** Before this plan nothing wired generation, so `views validate` on a fresh root failed with `No views data directory` and never had generator output to disagree with. Wiring the handler is what made the conflict observable — Plan 02 predicted this precisely.

**Why it was not fixed here.** The three available resolutions have materially different blast radii and each touches a locked decision or a file outside this plan's scope:

- **Widen the models to the written bytes** (extends D-02's parsers-are-ground-truth rule) — changes `views/models.py`, the contract Phases 16/17 build the SPA against.
- **Share the generator's adapter with the validator** — makes both surfaces agree while preserving the property that the on-disk bytes are still never validated, which is what 15-02 called "a worse contract than the honest failure."
- **Write the validated projection** — changes the bytes the SPA consumes; the largest blast radius.

That is a Rule 4 architectural decision, not a Rule 1 bug fix, and per the execution brief it is carried forward rather than silently taken.

**What the handler's success signal does and does not cover.** A `success=True` from `views.generate_data` (over MCP) or exit 0 from `construct views generate` means: every workspace was discovered, every file was written, and **the generator's projection of each file** satisfied its model. It does **not** mean the JSON on disk satisfies that model. Any consumer reading `views/build/data/*.json` directly — including the v0.5 SPA — is reading bytes that three of eight files' contracts currently reject. Plans 04/05 and Phases 16/17 must not treat this success signal as a schema guarantee over the written artefacts.

The state is pinned, not hidden, by `test_views_validate_does_not_yet_accept_generated_bytes`, which asserts the exact failing set and is written to go red the moment the divergence is resolved. **Delete that test as part of the fix.**

## Known Stubs

None introduced. The permanent-failure placeholder this plan existed to remove is gone; `grep -c 'Not yet implemented' src/construct/capabilities/catalog.py` returns 0.

## Issues Encountered

- **A false note left standing in the playbook.** `USER-TEST-PLAYBOOK-v03.md` §7.1 still reads "`views.generate_data` is a known v0.4 stub (audit tech debt), so some files may be `missing`." That is no longer true. The plan says "Change nothing else in that file," and Phase 16 (DOC-04) may retire the playbook wholesale, so it was left alone deliberately — flagged here so Phase 16 does not inherit it unknowingly. It is also, coincidentally, now accurate for the wrong reason: files do fail, just from the divergence above rather than from a stub.

## Next Phase Readiness

- **Plans 04 and 05 are unblocked.** The capability is real, the CLI command exists, and the allowlist is at its four Phase 16 entries.
- **Plan 05 (D-11)** should find that `construct views generate` references in skill and workflow docs now resolve rather than failing the guard — as the plan anticipated. Removing those sections remains Plan 05's job.
- **Phase 16 owns all four remaining `_KNOWN_BROKEN` entries.** Retiring the playbook under DOC-04 removes the two `workflow` entries; implementing or rewriting the knowledge sub-app commands removes the other two. Coordinate so the guard ends empty rather than merely unscanned.
- **The writer/validator divergence needs an owner before the SPA contract work.** It is the single largest open item this phase surfaced.

## Self-Check: PASSED

All five commit hashes resolve in `git log`; all seven claimed files exist and carry the claimed changes; full suite green at 458 passed.

---
*Phase: 15-views-generate-data-resolution*
*Completed: 2026-07-19*
