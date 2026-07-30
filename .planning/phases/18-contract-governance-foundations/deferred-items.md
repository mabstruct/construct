# Deferred items — Phase 18

Out-of-scope discoveries logged during execution. Not fixed by the plan that found them.

## From 18-07 (canonical write boundary)

### 1. `pipelines/ingestion.py` calls `create_card` directly — a real GOV-04 finding

- **Found during:** Task 2, while building the category-level guard.
- **What:** `ingest_source` calls `create_card(...)` at `src/construct/pipelines/ingestion.py:246`.
  The module is not an apply node and no review interrupt precedes it — the `ingest.source`
  capability creates a card as its declared product.
- **Why it is not fixed here:** the plan forbids adding a fourth exemption to the guard
  ("stop and surface it"). Deciding whether the invariant is phrased too broadly (canonical
  writes vs. *review-decided* canonical writes) or the ingestion pipeline should route through
  an apply node is a scope change, not an execution detail.
- **How it is tracked instead:** recorded in `tests/contract/test_canonical_write_boundary.py`
  as `UNRESOLVED_DIRECT_CALLERS` — explicitly labelled *not* an exemption, and asserted as a
  baseline that may only shrink (nothing new may join it; an entry that stops being a real
  caller must be deleted rather than left to rot). Also filed in `.planning/WINDOWS.md`.
- **Decision needed from:** a reviewer who can name which side of the invariant is wrong.

### 2. `test_workspace_contract_migration.py` fixture-layout failures (environment, not code)

- **Found during:** Task 1 full-suite run.
- **What:** `TestFixtureRoot::test_my_construct_has_canonical_layout` and
  `::test_ping_eon_has_canonical_layout` fail on `Missing canonical directory: digests/`.
- **Cause:** `test-ws/*/digests/` contains no git-tracked files (`git ls-files` returns 0), so
  git cannot materialise the empty directory in a fresh worktree checkout. The tests assert
  directory presence.
- **Scope:** pre-existing and unrelated to this plan — reproduces on the base commit. Fixing it
  means either adding a `.gitkeep` to the fixture directories or relaxing the assertion; both
  touch fixtures another plan may own.

## From 18-08 (surface honesty)

### 3. `research_run.update_seeds_and_log` emits `gate_review_approved` from the DECISION, not from the write

- **Found during:** Task 1, while checking the plan's conditional clause "give the research
  graph's gate the same treatment **if it has an escalate path**".
- **What the check found:** research_run has **no** escalate path — `grep -c 'escalat'
  src/construct/llm/research_run.py` returns **0** — so the escalate half of the clause is
  genuinely inapplicable and no change was required for it. But the same *approval-without-a-write*
  defect Task 2 fixed in curation exists in the research graph: `update_seeds_and_log`
  (`research_run.py:919-932`) emits `gate_review_approved` for every finding whose **decision** is
  in `_INGEST_ACTIONS`, while `ingest_batch` (`:584-615`) separately tracks `skipped_existing` for
  refs and cards that **already existed and were therefore not written**. An idempotent research
  re-run therefore records approvals for ingests that did not happen — the T-18-06 class, in the
  other graph.
- **Why it is not fixed here:** Task 2's declared `<files>` are `curation_run.py` and
  `tests/llm/test_curation_run.py`; its `<action>` says "in all three apply nodes", meaning
  curation's; and D-16 enumerates exactly three sites, all in `curation_run.py`
  (`:872`, `:923`, `:968`). Fixing research honestly needs assertions in
  `tests/llm/test_research_run.py`, which this plan does not own and which plan 18-06 records as
  recently contended. Fixing it silently — or fixing it without a test — would be worse than
  naming it.
- **Bearing on the phase:** criterion 4's second half ("no approval event exists for a decision
  that was never applied") is **met for the curation graph, proven by the event-count invariant**
  in `tests/llm/test_curation_run.py::test_approval_event_count_equals_applied_count`. Whether the
  criterion was meant to span the research graph as well is a verifier's call, not an executor's.
- **Decision needed from:** phase verification — either accept the curation scoping (as D-23 did
  for GOV-04's ingestion finding) or open a follow-up for the research gate.
