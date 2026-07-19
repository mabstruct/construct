# Phase 10 — Deferred / Out-of-Scope Items

Discovered during execution but outside the scope of the current plan's changes
(do NOT fix here — they are pre-existing and unrelated to research.run).

## From Plan 10-03 execution (2026-06-28)

- **`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::test_my_construct_has_canonical_layout`** —
  Fails because `test-ws/my-construct/` is missing a canonical `digests/` directory.
  Pre-existing fixture-layout issue; does not reference `research_run` or
  `langgraph-checkpoint-sqlite`. Unrelated to this plan.

- **`tests/integration/test_workspace_contract_migration.py::TestFixtureRoot::test_ping_eon_has_canonical_layout`** —
  Same canonical-layout fixture check for `test-ws/ping-eon/`. Pre-existing,
  unrelated to this plan.

- **`tests/search/test_search_provider_mock.py::test_import_tavily_sdk_when_search_extra_installed`** —
  Not a real failure: requires the `search` extra. Passes under
  `uv run --extra dev --extra search pytest`. Invocation artifact only.
