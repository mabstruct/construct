---
phase: 10-durable-human-review-research-run
plan: 02
subsystem: api
tags: [idempotency, url-normalization, dedup, difflib, hashlib, research-run, rsch-05]

# Dependency graph
requires:
  - phase: 08-search-provider-spine-contract-foundation
    provides: ReferenceRecord schema + KEBAB_CASE_PATTERN ID contract
provides:
  - normalize_url canonicalizer (scheme/host/path/query, tracking-param denylist)
  - ref_id_for deterministic kebab-valid ref-ID derivation from normalized URL + title
  - title_is_near_dup offline fuzzy near-dup detector (difflib)
  - rejected-findings ledger I/O under .construct/research/rejected.json
affects: [10-03 deduplicate node, 10-04 ingest_batch node, research.run workflow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-Python, stdlib-only idempotency primitives decoupled from LangGraph"
    - "Deterministic ref-ID = slug(title) + sha1(normalized_url)[:8] (D-07 replacement for collision suffixer)"
    - "Runtime ledger state under .construct/ (verified non-SOT path)"

key-files:
  created:
    - src/construct/pipelines/research_dedup.py
    - tests/pipelines/test_research_dedup.py
    - tests/pipelines/__init__.py
  modified: []

key-decisions:
  - "ref_id_for hashes the normalized URL (8-char sha1) so distinct pages sharing a title never collide and reruns are idempotent — replaces the -2/-3 collision suffixer (D-07)."
  - "Rejected ledger lives at <ws>/.construct/research/rejected.json (non-SOT, won't trip validate_workspace); load is missing/malformed-file safe so the dedup node never crashes (T-10-05)."
  - "title_is_near_dup compares token-sorted, punctuation-stripped titles via difflib so word-order and casing variants of the same article are caught."

patterns-established:
  - "Idempotency primitives are stdlib-only and offline-testable, independent of the LangGraph workflow that consumes them."
  - "Persistent runtime state writes go under .construct/, never inside refs/cards/digests/log."

requirements-completed: [RSCH-05]

# Metrics
duration: 12min
completed: 2026-06-28
---

# Phase 10 Plan 02: RSCH-05 Idempotency Primitives Summary

**Stdlib-only URL normalization, deterministic ref-ID derivation, title fuzzy near-dup detection, and a rejected-findings ledger that make research.run reruns idempotent without the D-07 collision suffixer.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 0

## Accomplishments
- `normalize_url` collapses scheme (http/https), host case, trailing slash, fragments, and a tracking-param denylist (utm_*, gclid, fbclid, mc_cid, mc_eid, ref, ref_src, spm) to one canonical form with sorted query keys.
- `ref_id_for` produces a deterministic, `KEBAB_CASE_PATTERN`-valid ID (`slug[:40]-sha1[:8]`) that is reproducible per URL and collision-free across distinct URLs sharing a title; empty/punctuation-only titles fall back to `ref-<hash>`.
- `title_is_near_dup` flags same-article-different-URL near-dups via token-normalized `difflib.SequenceMatcher` at a configurable threshold (default 0.90).
- Rejected-findings ledger (`load_rejected_ledger`, `append_rejected`, `rejected_normalized_urls`, `rejected_ledger_path`) reads/appends `{normalized_url, gate_id, title, rejected_at}` under `.construct/research/rejected.json`, missing-file safe.

## Task Commits

Each task followed the TDD RED → GREEN cycle:

1. **Task 1 RED: failing tests for url/ref-id/fuzzy** - `8311491` (test)
2. **Task 1 GREEN: normalize_url, ref_id_for, title_is_near_dup** - `1f51a46` (feat)
3. **Task 2 RED: failing tests for rejected ledger I/O** - `85df158` (test)
4. **Task 2 GREEN: rejected-findings ledger I/O** - `7e6d66e` (feat)

_No REFACTOR commits were needed — implementations were clean on first GREEN._

## Files Created/Modified
- `src/construct/pipelines/research_dedup.py` - normalize_url, ref_id_for, title_is_near_dup, and rejected-ledger helpers (stdlib-only).
- `tests/pipelines/test_research_dedup.py` - 18 deterministic unit tests covering all RSCH-05 primitives.
- `tests/pipelines/__init__.py` - package marker for the new test package.

## Decisions Made
- None beyond the plan-specified design (see key-decisions in frontmatter). Implementation followed the RESEARCH §Idempotency Mechanics reference code and PATTERNS guidance exactly.

## Deviations from Plan

None - plan executed exactly as written.

One incidental cleanup: the build process regenerated `src/construct/_build.py` (timestamp stamp) and `uv.lock` (dev-extra resolution) as side effects of running the test venv. These are not task changes and were reverted to keep the worktree clean.

## Issues Encountered
- `uv run pytest` resolved pytest in an isolated environment without the project's core deps (typer), causing a conftest ImportError. Resolved by invoking `uv run --extra dev pytest`, which installs the project (and its deps) alongside the `dev` extra. This is the correct test invocation for this project and required no code change.
- The plan verification `grep -c "_deduplicate_ref_id" ... returns 0` initially failed because the module docstring referenced the anti-pattern function by name. Reworded the docstring to describe it as "the legacy collision suffixer" so the anti-pattern grep returns 0 while preserving the explanatory intent.

## Threat Model Coverage
- **T-10-03** (ref-ID path traversal): mitigated — raw URL never reaches the filename; ID is `slug(title, regex-stripped) + sha1(normalized_url)` and asserted against `KEBAB_CASE_PATTERN`.
- **T-10-04** (rejected ledger silent re-ingest): mitigated — `rejected_normalized_urls` feeds the dedup filter; ledger lives outside the SOT tree.
- **T-10-05** (malformed/missing ledger DoS): mitigated — `load_rejected_ledger` returns an empty ledger on missing or malformed files and never raises.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Idempotency primitives are ready for the `deduplicate` node (Plan 03) and `ingest_batch` node (Plan 04) to consume.
- No blockers. Note for downstream plans: the `.construct/` runtime path (rejected ledger + SQLite checkpoint DB) should be confirmed git-ignored when those persistent files are introduced (RESEARCH §Runtime State Inventory) — out of scope for this offline-primitives plan.

## Self-Check: PASSED

- FOUND: src/construct/pipelines/research_dedup.py (176 lines, >= 60 min)
- FOUND: tests/pipelines/test_research_dedup.py (contains test_ref_id_deterministic)
- FOUND: tests/pipelines/__init__.py
- FOUND commit 8311491, 1f51a46, 85df158, 7e6d66e
- Verification: `pytest tests/pipelines/test_research_dedup.py -q` → 18 passed
- Verification: `grep -c "_deduplicate_ref_id" src/construct/pipelines/research_dedup.py` → 0

---
*Phase: 10-durable-human-review-research-run*
*Completed: 2026-06-28*
