---
phase: 15-views-generate-data-resolution
plan: 02
subsystem: views
tags: [pydantic, contract-models, schema-validation, d-02, tdd]

requires:
  - phase: 15
    plan: 01
    provides: "`construct.views.generate` importable from the shipped package, so generate() could be driven from a test at all"
provides:
  - "`generate()` returning success=True with zero validation errors on both a fresh and a populated install root"
  - "`views/models.py` field sets that describe what the parsers actually emit, with strictness intact"
  - "`scaffolded_install_root` fixture — a real init-scaffolded install root for integration tests"
  - "4 integration tests + 3 contract tests guarding the D-02 reconciliation"
affects: [15-03, 15-04, 15-05, views]

tech-stack:
  added: []
  patterns:
    - "Parsers are ground truth for model field sets; the spec is the corroborating authority, never the sole one"
    - "Populated-fixture integration test alongside the fresh-scaffold test, because a fresh workspace has zero cards and would let card-level defects pass"
    - "Copy the shared fixture and delete its prebuilt views/build so the fingerprint cache cannot short-circuit generation"

key-files:
  created:
    - tests/integration/test_views_generate.py
    - tests/integration/conftest.py
  modified:
    - src/construct/views/models.py
    - tests/contract/test_views_contracts.py

key-decisions:
  - "`cross_domain_links` typed as a bare `list`, not `list[dict]` — three element shapes exist in the wild and the parser guards it with only an isinstance(list) check"
  - "`ArticleRecord` and `EventRecord` reconciled too (Rule 1) — the plan's fresh-workspace probe could not reach them, but the populated root fails without it"
  - "`EventRecord.details` widened to `str | dict | None` rather than normalising in the adapter — parse_events passes raw jsonl through and spec §5.6 declines to enumerate event shapes"
  - "The writer/validator shape divergence in generate.py was documented, not fixed — out of scope, flagged for Plan 03"

requirements-completed: [FIX-01]

coverage:
  - id: D1
    description: "generate() on a freshly scaffolded install root returns success=True with zero validation errors and zero warnings (the D-04 done-bar)"
    requirement: FIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_fresh_workspace_generates_clean"
        status: pass
    human_judgment: false
  - id: D2
    description: "generate() on a populated install root returns zero validation errors, with CardRecord.connections genuinely exercised"
    requirement: FIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_populated_workspace_generates_clean"
        status: pass
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_generated_card_connections_are_id_strings"
        status: pass
    human_judgment: false
  - id: D3
    description: "DomainRecord accepts every field parse_domains.py emits and rejects unknown fields"
    requirement: FIX-01
    verification:
      - kind: contract
        ref: "tests/contract/test_views_contracts.py::TestWidenedDomainRecord"
        status: pass
    human_judgment: false
  - id: D4
    description: "All 17 models still forbid unknown fields after the reconciliation (threat T-15-05)"
    requirement: FIX-01
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_models_still_forbid_unknown_fields"
        status: pass
      - kind: other
        ref: "grep -c '^    model_config = ConfigDict(extra=\"forbid\")' src/construct/views/models.py == 17; ignore/allow count == 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "A card's denormalised connection list is emitted in a stable, specified order (probe edge E3)"
    verification:
      - kind: integration
        ref: "tests/integration/test_views_generate.py#test_generated_card_connections_are_id_strings — asserts connections == sorted(connections)"
        status: partial
    human_judgment: true
    rationale: "The list is asserted equal to its own sorted form on every generated card, which pins the ordering rule. Stability across two successive generate runs of identical input is still not asserted — it remains a backstop truth."
  - id: D6
    description: "An install root with zero workspaces produces valid-but-empty view data rather than erroring (probe edge E2)"
    verification:
      - kind: integration
        ref: "the zero-cards half is covered by test_fresh_workspace_generates_clean; the zero-workspaces half is untested"
        status: partial
    human_judgment: true
    rationale: "A freshly scaffolded workspace has zero cards and generates cleanly, so the empty-collection path through cards/connections/digests/events is proven. An install root containing no workspaces at all is still only a backstop truth."

duration: 24min
completed: 2026-07-19
status: complete
---

# Phase 15 Plan 02: Reconcile the views models with the parsers Summary

**`views/models.py` now describes the shape the vendored parsers actually emit — five phantom `DomainRecord` counters gone, `CardRecord.connections` retyped to card-id strings, `BridgeSummary.top_domain_pairs` added, and `ArticleRecord`/`EventRecord` corrected too — so `generate()` returns `success=True` with zero validation errors on both a fresh and a populated install root, with all 17 models still forbidding unknown fields.**

## Performance

- **Duration:** 24 min
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified)
- **Suite:** 446 → 453 passing

## Accomplishments

- Drove the whole plan TDD-first: the RED commit reproduced the exact failure signature the plan predicted — `domains.json` + `bridges.json` on a fresh root, plus `cards.json` connections on a populated one.
- Reconciled five models against parser ground truth, corroborated field-for-field by `spec-v02-data-model.md` §5.1/§5.2/§5.5/§5.6.
- Closed RESEARCH Pitfall 1 with a populated-fixture test, and Pitfall 2 by deleting the fixture's prebuilt `views/build` so the fingerprint cache cannot short-circuit generation and report a vacuous success.
- Kept the D-02 prohibition intact and made it self-guarding: `test_models_still_forbid_unknown_fields` walks all 17 models and asserts `extra == "forbid"`, so relaxing strictness to make generation pass now turns the suite red.

## Task Commits

1. **Task 1: Write the failing fresh + populated generation tests** — `afd8f23` (test)
2. **Task 2: Reconcile DomainRecord, CardRecord, and BridgeSummary with the parser output** — `102f5f2` (feat)
3. **Task 3: Reconcile the existing views contract tests** — `b6cd889` (test)

## Which populated fixture was used

`tests/fixtures/v02/multi-domain-medium/`, chosen over `single-domain-small` because **both** of its workspaces ship a non-empty `connections.json` whose endpoints are real card ids. Denormalisation therefore produces non-empty `connects_to` lists and `CardRecord.connections` is genuinely exercised. **No connected cards had to be added** — the fixture was sufficient as shipped.

The fixture also ships a prebuilt `views/build/data/`. It carries no `_build-meta.json`, so the fingerprint cache would not actually have short-circuited, but the test copy deletes `views/build` anyway so the guarantee is structural rather than incidental.

## Phantom DomainRecord fields — all five deleted

The grep gate ran over `src/`, `tests/`, and `views/design-example/src/` for each of `card_count`, `connection_count`, `digest_count`, `article_count`, `keywords`. **No `DomainRecord` consumer was found, so all five were deleted.** The hits that exist are unrelated structures, exactly as the plan anticipated:

| Field | Hits outside models.py | Verdict |
|---|---|---|
| `card_count`, `connection_count` | `services/help.py`, `pipelines/graph_status.py`, `tests/unit/test_help.py` | The graph-status / help report — a different structure. Untouched. |
| `digest_count`, `article_count` | none | Pure phantoms. |
| `keywords` | `cli.py`, `pipelines/tag_extraction.py`, `pipelines/spike_runner.py`, a design-example HTML file | Tag-extraction vocabulary and prose. Unrelated. |

## Assertions deleted from `test_views_contracts.py`

**None.** No repair work was required at all: no site in that file constructed a `DomainRecord` with a phantom field, and no site constructed or asserted on a dict-shaped `CardRecord.connections`. The file went 52 → 55 collected, all additions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ArticleRecord` and `EventRecord` were also wrong**

- **Found during:** Task 2, once the populated root got past domains/bridges/cards.
- **Issue:** Two further model/parser disagreements of the identical D-02 class, invisible to the plan's fresh-workspace probe because a scaffolded workspace has no `publish/*.md` and only a single canonical event line.
  - `ArticleRecord` required a `url` field **no parser ever emits**, and forbade the 9 fields `parse_articles` does emit (`type`, `status`, `date`, `domains`, `confidence_floor`, `source_cards`, `body_markdown`, `excerpt`, `raw_path`). Every populated install root failed `articles.json` validation — 20 errors. Spec §5.5 documents the parser's shape exactly and names no `url`.
  - `EventRecord.details` was typed `dict | None`, but `parse_events` passes `log/events.jsonl` lines through verbatim and real logs carry a human-readable string (`"Created card-hubble-tension"`). 15 errors per workspace. Spec §5.6 explicitly declines to enumerate event shapes.
- **Fix:** Both reconciled in the same style and under the same rule as the plan's three named models — describe what the parser emits, keep `extra="forbid"`. `details` became `str | dict | None`; the fix was *not* put in the adapter, because normalising there would have altered what reaches the SPA.
- **Why not Rule 4:** No structural change — same file, same mechanism, same decision (D-02), no new model or dependency. Without it the plan's own success criterion ("zero validation errors on a populated install root") is unreachable.
- **Committed in:** `102f5f2`

**2. [Rule 1 - Bug] `cross_domain_links` cannot be `list[dict]`**

- **Found during:** Task 2.
- **Issue:** The plan specified `list[dict]`. The real `multi-domain-medium` fixture emits a list of bare domain-id **strings**, so `list[dict]` still failed validation. Three shapes exist in the wild: `{"domain", "topics"}` (`schemas/config.py::CrossDomainLink`), `{"to", "note"}` (spec §5.1 prose), and bare strings (the v02 fixtures).
- **Fix:** Typed as a bare `list`. This is the plan's *own* stated rationale (RESEARCH A3 — never stricter than the parser guarantees) applied one level further than the plan's literal type; `parse_domains.py:40` guards with nothing but `isinstance(list)`.
- **Committed in:** `102f5f2`, with both the dict and bare-string shapes asserted in `TestWidenedDomainRecord`.

### Acceptance-criterion arithmetic

**3. `grep -c 'extra="forbid"'` reports 19, not 17**

The criterion counts two prose mentions in the module docstring (line 5) and in `unwrap_payload`'s docstring, on top of the 17 real declarations. The substantive fact holds: `grep -c '^    model_config = ConfigDict(extra="forbid")'` is exactly **17**, ignore/allow is **0**, and `test_models_still_forbid_unknown_fields` proves it programmatically per model. Same class as Plan 01's off-by-one.

**4. `grep -c 'card_count' tests/contract/test_views_contracts.py` reports 1, not 0**

The criterion's intent — no site *constructs* a `DomainRecord` with a phantom field — holds. The single hit is my new `test_widened_domain_still_rejects_unknown_fields`, which asserts `card_count` is **rejected**. Keeping the just-deleted field name there is deliberate: it is a regression guard against the phantom being reintroduced, which a generically-named `nonsense=1` would not provide.

### Test correction during GREEN

**5. The generated `cards.json` uses `connects_to`, not `connections`**

The RED test asserted against a `connections` key that the generated file does not have. `generate()` **validates an adapted projection** of each card (`generate.py:461` maps `connects_to` → `connections`) but **writes the raw parser dict**, so the denormalised list lands on disk under the parser's key. The test now reads `connects_to`, and additionally feeds that on-disk value through `CardRecord(...)` — which proves the stronger property the plan was reaching for: the value the writer emits satisfies the model the validator applies. See the open item below.

---

**Total deviations:** 2 auto-fixed (Rule 1), 2 criterion-arithmetic clarifications, 1 test correction.
**Impact on plan:** No scope creep beyond `models.py`. Every prohibition held — no `model_config` weakened, no validation error suppressed or downgraded, `_FILE_MODEL_MAP` and all parsers untouched (`git diff --stat src/construct/views/generate.py` is empty).

## Issues Encountered

### Open: generate() validates one shape and writes another

`generate()` validates an adapted projection of each per-workspace file but writes the **raw parser dict**. For cards this means the on-disk `cards.json` carries `connects_to`, `body_markdown`, `tags`, `sources`, `author`, `created`, `last_reviewed` — none of which are `CardRecord` fields — while the validator only ever sees the 10-field projection. The schema gate is therefore weaker than it appears: **it does not validate the bytes that reach the SPA.**

This is pre-existing and out of scope here (D-02 covers models, not the write path), but it materially affects Plan 03's "wire a real handler" and Phase 16/17's SPA contract. Flagged for Plan 03 to decide: either write the validated projection, or validate the raw shape.

## RESEARCH OQ-2 — for Phase 17

The "deployed SPA is ground truth" premise is **unverifiable in-repo**. `views/build/` does not exist in the checkout, and `views/design-example/` reads its own bundled data rather than generator output. Nothing in the repository lets you check a model against what a running SPA consumes.

Therefore `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md` is the durable authority for the views data contract, corroborating the parsers rather than competing with them. This plan used it exactly that way, and it held up: §5.1, §5.2, §5.5, and §5.6 each independently confirmed a parser-derived field set. Where spec and parser differed on a detail (§5.1 shows `cross_domain_links` as objects; the fixtures use strings), the parser's looser guarantee won — the model must accept everything the parser can produce.

## Next Phase Readiness

- **Plan 03 is unblocked.** `generate()` no longer always reports failure, so a real `views.generate_data` handler can report meaningful success.
- **Plan 03 should decide the writer/validator divergence** documented above before wiring the handler — a handler that reports "validated" for bytes that were never validated is a worse contract than the current honest failure.
- **Backstop truths still open:** ordering stability across two successive runs, and the zero-workspaces install root. Both are cheap to add if Phase 15 verification wants them promoted.

## Self-Check: PASSED

All claimed artifacts exist on disk; all three commit hashes resolve in `git log`; full suite green at 453 passed.

---
*Phase: 15-views-generate-data-resolution*
*Completed: 2026-07-19*
