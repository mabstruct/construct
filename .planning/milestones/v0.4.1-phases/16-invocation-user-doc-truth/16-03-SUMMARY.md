---
phase: 16-invocation-user-doc-truth
plan: 03
subsystem: knowledge-graph
tags: [capability-registry, cli, mcp, enumerate, tdd]
requires:
  - "16-01 (the doc-reference guard and its _KNOWN_BROKEN allowlist)"
provides:
  - "construct knowledge card list — CLI leaf and construct_list_cards MCP tool"
  - "list_cards handler and the _json_safe date coercion helper"
  - "CardListInput (extra=forbid) input model"
affects:
  - "16-04 (skill rewrites documenting card list)"
  - "16-05 (CLI-invocation column naming the flag surface)"
  - "17 DOC-02 (artifact-catalog inventory — surface counts below)"
tech-stack:
  added: []
  patterns:
    - "Registry-routed dual-surface command: one CapabilityRecord carrying both cli_name and mcp_tool_name, MCP parity by auto-discovery with zero edits to mcp/server.py"
    - "Serialization coercion at the handler boundary, never in the shared CLI renderer"
key-files:
  created:
    - tests/contract/test_card_list_cli_mcp.py
  modified:
    - src/construct/services/knowledge.py
    - src/construct/capabilities/catalog.py
    - src/construct/cli.py
    - tests/unit/test_knowledge_operations.py
    - tests/contract/test_mcp_contracts.py
    - tests/contract/test_doc_command_references.py
    - tests/unit/test_capability_registry.py
decisions:
  - "The domain filter's case-sensitivity is pinned on the query side, not the card side: card domains are schema-constrained to kebab-case, so an uppercase domain cannot exist on a card"
  - "Archive filtering reads each card's own normalized lifecycle token rather than reusing _get_archived_card_ids, which exists to filter connections by endpoint lifecycle"
metrics:
  duration: ~25m
  tasks: 3
  files: 8
  completed: 2026-07-20
status: complete
---

# Phase 16 Plan 03: knowledge card list — registry-routed enumerate command Summary

`knowledge card list` is now a real command on both the Typer CLI and the MCP surface, routed
through a single capability record, returning frontmatter-only card data with dates coerced to
ISO-8601 strings — and its `_KNOWN_BROKEN` allowlist entry is gone.

## What Was Built

**`list_cards(workspace, domain=None, include_archived=False)`** in `src/construct/services/knowledge.py`.
First parameter is named `workspace` so the positional CLI call and the keyword MCP call bind the
same parameter with no shim (the RT-03 defect class). A path with no `cards/` directory returns an
unsuccessful `OperationResult` carrying an `OperationError`; a scaffolded workspace with no cards
returns an empty success. Card prose is popped (`D-02` / T-16-02) and never leaves through the
enumerate call. Ordering is `WorkspaceLoader.iter_cards()`'s `sorted()` glob order.

**`_json_safe(value)`** — module-private, coerces `date`/`datetime` to `.isoformat()` and passes
everything else through. Applied in the handler, deliberately **not** in `cli._display_result`,
which every command shares. `_display_result` is byte-identical to its pre-plan state.

**`CardListInput`** in `catalog.py` with `model_config = {"extra": "forbid"}` set explicitly
(ASVS V5 / T-16-09 — not inherited), and the `knowledge.card.list` record carrying both
`cli_name="knowledge.card.list"` and `mcp_tool_name="construct_list_cards"`.

### CardListInput field set

| Field | Type | Default |
|-------|------|---------|
| `workspace` | `Path` | required |
| `domain` | `str \| None` | `None` |
| `include_archived` | `bool` | `False` |

### CLI flag surface (for 16-05's invocation column)

```
construct knowledge card list [--domain/-d <str>] [--include-archived] [--workspace/-w <path>] [--json/-j]
```

### JSON envelope a caller receives

Top-level keys: `success`, `message`, `errors`, `data`. `data` is a list of card frontmatter dicts,
each carrying exactly: `author`, `confidence`, `connects_to`, `content_categories`, `created`,
`domains`, `epistemic_type`, `id`, `last_verified`, `lifecycle`, `promoted_from`, `source_tier`,
`sources`, `supersedes`, `tags`, `title`. No `body` key. `created` / `last_verified` render as
ISO-8601 strings (e.g. `"2026-07-20"`).

## Surface counts (for Phase 17 DOC-02, per D-04)

**34 CLI leaf commands** (was 33) and **22 MCP tools** (was 21) — exactly the numbers D-04
predicted. No count was written into any shipped document (D-12), and `artifact-catalog.md`
was not touched.

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | RED tests — `TestCardList` (10 cases) + CLI/MCP parity suite (9 cases) | `5d3a255` |
| 2 | `list_cards`, `CardListInput`, capability record, CLI leaf, MCP bookkeeping | `071318c` |
| 3 | Delete the card-list `_KNOWN_BROKEN` entry | `7d1924c` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A fourth exhaustive capability set needed the new id**

- **Found during:** Task 3 full-suite run
- **Issue:** The plan named three exhaustive iterations a new MCP tool participates in, all in
  `test_mcp_contracts.py`. A fourth exists: `tests/unit/test_capability_registry.py::test_catalog_loads`
  compares the full capability-id set exactly, so registering `knowledge.card.list` broke it.
- **Fix:** Added `"knowledge.card.list"` to that expected set.
- **Files modified:** `tests/unit/test_capability_registry.py`
- **Commit:** `7d1924c`

**2. [Rule 1 - Bug] Case-sensitivity test used a domain the schema forbids**

- **Found during:** Task 2 GREEN run
- **Issue:** The plan's must-have phrased the case-sensitivity property as "a card in domain
  `Cosmology` is not returned by `--domain cosmology`". `KnowledgeCard` validates domains as
  kebab-case, so a card in domain `Cosmology` cannot be created at all — `create_card` returned a
  validation failure and the test asserted against an empty workspace.
- **Fix:** The property is pinned from the query side instead: a card in `test-domain` is not
  returned by `--domain Test-Domain`. This tests the same no-case-folding behaviour through the
  only path the schema permits. The positive filter case now uses the valid domain `other-domain`.
- **Files modified:** `tests/unit/test_knowledge_operations.py`
- **Commit:** `071318c`

**3. [Rule 1 - Bug] Flag-surface assertion broke on Rich's ANSI output**

- **Found during:** Task 2 GREEN run
- **Issue:** `test_cli_exposes_documented_flags` substring-matched `--domain` against `--help`
  stdout, but Rich injects colour escapes mid-token (`-\x1b[...m-domain`), so every flag missed.
- **Fix:** Strip ANSI escapes before matching.
- **Files modified:** `tests/contract/test_card_list_cli_mcp.py`
- **Commit:** `071318c`

### Accepted plan-vs-reality mismatches

**Task 1's "`--co` collects without error" criterion was unreachable.** The plan's Task 1 action
directs importing `list_cards` alongside the existing eager imports in
`tests/unit/test_knowledge_operations.py`, which is the correct end state — but during RED that
import raises `ImportError` at collection rather than collecting-then-failing. The explicit import
instruction was followed; the RED failures were confirmed to be import/lookup errors against the
unbuilt capability, exactly the character the plan asks to verify. Resolved automatically at Task 2.

**`_invalid_path_payload` needed no edit.** The plan called for three edits to
`test_mcp_contracts.py`; only two were required. The invalid-path builder derives its payload from
`_payload_for` and rewrites any field named `workspace`, so adding the `_payload_for` entry covered
it. Two edits made, third confirmed unnecessary by reading the builder.

## Verification

- Full suite: **513 passed, 3 failed**. The three failures are exactly the ones other plans own:
  `test_key_docs_are_not_vacuous[USER_GUIDE.md]` and `[commands.md]` (16-05), and
  `test_skill_drops_forbidden_tools[construct-synthesis]` (16-04).
- **`test_command_surface_is_discoverable` is GREEN** — this plan's target, RED since 16-01.
- `test_documented_commands_resolve` green: the two skills documenting `card list` now resolve.
- `_KNOWN_BROKEN` holds 3 entries; `_DOC_GLOBS` unchanged at 3 (scan surface never narrowed, D-16).
- `grep -c 'card.list\|list_cards\|construct_list_cards' src/construct/mcp/server.py` → `0`.
- `git diff src/construct/cli.py | grep -c '^[-+].*def _display_result'` → `0`.
- Manual smoke against a scratch workspace: `--json` output parses, carries no `body`, renders
  `created` as `2026-07-20`.

## Threat Mitigations Applied

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-16-02 (info disclosure — card prose) | mitigated | `card_data.pop("body", None)`; pinned by `test_list_cards_excludes_body` and the parity test's per-card assertion |
| T-16-03 (info disclosure — `--workspace` path) | mitigated | Reads only `<workspace>/cards/*.md` via `WorkspaceLoader`; a path with no `cards/` returns an error result without walking upward |
| T-16-09 (DoS — payload field surface) | mitigated | `model_config = {"extra": "forbid"}` on `CardListInput`; pinned by `test_input_model_forbids_extra_fields` |
| T-16-10 (tampering — surface divergence) | mitigated | Single record carries both names; `test_mcp_no_hardcoded_card_list` asserts `mcp/server.py` holds no card-list wiring |
| T-16-SC (supply chain) | accepted | Zero packages installed; `pyproject.toml` untouched |

## Known Stubs

None.

## Self-Check: PASSED

- `tests/contract/test_card_list_cli_mcp.py` exists on disk
- Commits `5d3a255`, `071318c`, `7d1924c` all present in `git log`
