# Quick Task 260726-m0e: Card writer vs views parser lifecycle frontmatter contract - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning

<domain>
## Task Boundary

The canonical card writer and the views parser disagree on the card frontmatter contract.

`src/construct/schemas/card.py:103` declares `lifecycle: Lifecycle = Lifecycle.seed` — an optional
field with a default — so `_card_dict_to_markdown` never serializes the key for a fresh card, and
`validate_card_write` passes because Pydantic fills the default. But
`src/construct/views/lib/parse_cards.py:7` lists `lifecycle` in `REQUIRED_FIELDS` and reads *raw*
frontmatter, so it drops the card and emits an advisory warning.

Reproduced end to end on 2026-07-26 (v0.4.1 milestone audit):
`construct init` → `construct knowledge card create` → `construct views generate --install-root .`
reported `11 files written, 0 validation errors, 1 content warnings` and **exited 0**, while
`views/build/data/myws/cards.json` contained `{"cards": []}` and `stats.json` counted 0 cards.
`construct knowledge card list --json` reported the same card with `"lifecycle": "seed"`.

Latent before Phase 15 — until `views.generate_data` stopped being a permanent-failure stub, the
writer/parser round trip was never exercised end to end.

Source: `.planning/milestones/v0.4.1-MILESTONE-AUDIT.md` (gaps.integration[1], gaps.flows[0]).

</domain>

<decisions>
## Implementation Decisions

### Contract owner — the writer

`_card_dict_to_markdown` (`src/construct/services/knowledge.py:98`) must always serialize
`lifecycle`. Frontmatter on disk becomes self-describing: what the file says is what the card is.
This matches the project's canonical-markdown invariant (adr-0001) and keeps the views parser free
of duplicated schema knowledge.

**Locked:** the views parser is NOT made tolerant. `REQUIRED_FIELDS` keeps `lifecycle`.
`parse_cards.py` is not edited.

One serializer covers all three writers — `_card_dict_to_markdown` is called by `create_card`
(`:200`), `update_card` (`:277`), and `archive_card` (`:342`). Note `archive_card:338` already sets
`raw["lifecycle"]` explicitly, which is why cards today only gain the key once archived.

### Existing cards on disk — backfill the three fixtures

Three of eighteen `test-ws/` cards currently lack the key:
- `test-ws/my-construct/cards/a-research-note-about-cosmology-inflation.md`
- `test-ws/smoke202606201640/cards/semantic-caching-cuts-gateway-latency.md`
- `test-ws/smoke202606201640/cards/token-based-rate-limiting.md`

Add `lifecycle: seed` to each.

**This is load-bearing, not cosmetic.** Because the parser stays strict, these three files remain
invisible to `views generate` until backfilled. The two decisions above are coupled — do not
implement one without the other.

> **CORRECTION (post-execution, 2026-07-26):** the second clause of the original rationale — "the
> repo would otherwise keep shipping cards its own generator silently drops" — was **wrong**, and
> the error was mine, not the executor's. All three files are **untracked**: `.gitignore:1` excludes
> `test-ws/`, and these three were never among the 31 force-added paths. Independently verified:
> 15 tracked `test-ws` cards, **all** carrying `lifecycle`. The 15-parsed/3-warnings measurement was
> a property of this working tree only — a fresh clone already parsed 15/15 clean.
>
> The executor applied the edits on disk (local fixtures now parse 18/0) but correctly refused to
> `git add -f` them: force-adding paths excluded at `.gitignore:1` would have silently expanded the
> tracked fixture set with two smoke-run byproducts (`smoke202606201640`, a timestamped workspace
> from 2026-06-20 16:40) — a larger scope violation than the backfill it served. There is no Task 3
> commit, and that is the right outcome. Whether any of the 18 on-disk cards belong in the repo is a
> separate, deliberate call.

### views generate behavior — unchanged

Keep the advisory-warning-and-exit-0 behavior. Do NOT change exit codes, and do NOT alter the
`GenerateReport` shape. `daily.run` / `curation.run` / `research.run` refresh views as a
status-neutral side effect (adr-0005); making drops fatal could flip a shipped workflow's status on
a pre-existing bad card. That is a scoped milestone decision, not a quick task.

The visibility gap is closed by a test instead: a writer-to-parser round trip.

### Claude's Discretion

- **Make the round-trip test derive from the parser, not from a hardcoded field name.** Assert
  `parse_cards.REQUIRED_FIELDS ⊆ set(written_frontmatter.keys())` rather than asserting `lifecycle`
  specifically. That way, if the parser ever adds a required field the writer does not emit, this
  test fails immediately instead of the next reader discovering it in a milestone audit. The
  specific `lifecycle` assertion may exist alongside it as a named regression pin.
- Whether to serialize `lifecycle` by explicitly defaulting it in `create_card`'s data dict, or by
  round-tripping the validated `KnowledgeCard` model back to a dict before serialization. Prefer
  whichever leaves `update_card` / `archive_card` behavior unchanged and does not reorder existing
  frontmatter keys.
- Test placement (`tests/contract/` vs `tests/integration/`) — follow whichever matches the
  existing round-trip precedent.

</decisions>

<specifics>
## Specific Ideas

House style for guards is set by `tests/contract/test_doc_command_references.py` and
`tests/contract/test_artifact_catalog.py`: introspect the live surface, and assert non-vacuity
explicitly so the test cannot pass on an empty set.

Applied here: assert the card file was actually written and its frontmatter parsed to a non-empty
dict *before* asserting field membership, so a writer regression that produces an empty or
unparseable file fails loudly rather than trivially satisfying a subset check.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/milestones/v0.4.1-MILESTONE-AUDIT.md` — the audit that found this (gaps.integration[1],
  gaps.flows[0]); records the live reproduction.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` — views refresh is a
  status-neutral side effect; the reason exit codes stay untouched.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0001-claude-native-approach.md` — markdown-as-truth, the basis for
  putting the contract on the writer.

</canonical_refs>

<known_consequences>
## Known Consequences (record in SUMMARY, do not fix here)

Because the fix is writer-side only, cards already sitting in a **user's** workspace without
`lifecycle` stay invisible to `views generate` until something re-saves them (`card update`,
`card archive`, or a curation promotion). The three repo fixtures are backfilled; real user
workspaces are not reachable from here. Note it in the SUMMARY so it is discoverable if someone
hits it, rather than silently carrying it.

</known_consequences>
