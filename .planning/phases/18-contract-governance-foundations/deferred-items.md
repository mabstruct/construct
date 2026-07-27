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
