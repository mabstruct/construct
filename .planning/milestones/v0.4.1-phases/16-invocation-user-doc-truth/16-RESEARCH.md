# Phase 16: Invocation & User-Doc Truth - Research

**Researched:** 2026-07-20
**Domain:** Documentation-truth enforcement over a Typer CLI surface (codebase-internal; no external technology research required)
**Confidence:** HIGH — every claim below was verified by executing against the live tree at commit `16e7668`.

## Summary

This phase has no external technology dimension. There is nothing to look up: no new libraries, no new frameworks, no version decisions. Every question that matters is a question about the current state of this repository, and every one of them is answerable by running code. That is what this research did — the live Typer app was introspected, the guard test's extractor was executed against candidate documents, and the `knowledge.connection.list` template was read end to end. Confidence is HIGH throughout because the findings are execution results, not recollection.

CONTEXT.md's ground truth is **confirmed exactly**: the live surface is 33 leaf commands plus 14 groups (47 valid paths), and `_KNOWN_BROKEN` holds 4 entries appearing as 5 occurrences across 3 files. The baseline suite is **489 passed** (STATE.md's "439" predates Phase 15). D-01's claim that `card list` is near-mechanical against `connection list` is confirmed and is in fact stronger than CONTEXT.md states — `WorkspaceLoader.load_cards()` and `_get_archived_card_ids()` already exist and do most of the work.

Two findings materially change how the planner should sequence this phase, and neither is in CONTEXT.md. First, **`USER_GUIDE.md` and `construct/references/commands.md` contain zero extractable invocations today** — D-11's glob extension is a *no-op* until D-10's CLI column lands, which imposes a hard task ordering. Second, and more seriously, **the guard's anti-vacuity test is global, not per-document** (`test_docs_contain_invocations` asserts a total `> 10` across all docs). A newly-globbed document whose CLI column is formatted so the extractor misses it would pass silently — producing exactly the false green that D-16 exists to prevent, in the very change D-11 introduces. This phase needs a per-doc non-vacuity assertion as a Wave 0 deliverable.

**Primary recommendation:** Land `knowledge card list` first (it is the only code change and unblocks two skill rewrites), then the skill rewrites, then the playbook supersession, and put the doc-glob extension *last* — gated behind a new per-doc non-vacuity guard written before the CLI columns exist.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `knowledge card list` enumeration | Capability registry (`capabilities/catalog.py`) | Service layer (`services/knowledge.py`) | Registry-first is the established pattern; gives CLI+MCP parity for free [VERIFIED: catalog.py:295] |
| Card frontmatter parsing | Storage layer (`storage/workspace.py`) | — | `load_cards()` already owns this; do not re-implement [VERIFIED: workspace.py:147] |
| CLI wrapper / flag surface | `src/construct/cli.py` | — | Thin `_display_result` wrapper, no logic [VERIFIED: cli.py:1453] |
| Invocation-string correctness | Contract test (`test_doc_command_references.py`) | — | Guard *defines* done; docs are the input, not the authority |
| Tool-grant enforcement | Contract test (`test_skill_migration.py`) | — | Static frontmatter guard [VERIFIED: test_skill_migration.py:34] |
| Release validation | `USER-TEST-PLAYBOOK-v041.md` (human-run) | — | D-09 rejected CI automation as out of scope |

## Standard Stack

**No new packages. No installations. No version decisions.** This phase adds one CLI command using facilities that already exist in the tree and edits Markdown.

| Existing facility | Location | Role in this phase |
|---|---|---|
| Typer | `src/construct/cli.py` | Existing CLI framework; `card list` is one more `@card_app.command` [VERIFIED: cli.py] |
| Pydantic | `capabilities/catalog.py` | `CardListInput` model, mirroring `ConnectionListInput` at `:140` [VERIFIED] |
| pytest | `tests/` | 489 tests green at baseline [VERIFIED: `pytest -q`] |

### Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** No registry lookups performed because no package names appear in any recommendation. The `pyproject.toml` dependency set is untouched.

## Runtime State Inventory

This phase renames nothing and migrates no data, but it *removes a file* and *adds a command*, so the equivalent inventory is "what else knows about these":

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `card list` is read-only; no schema or persisted state changes | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None. D-07's offline-by-default playbook explicitly avoids requiring `ANTHROPIC_API_KEY`/Tavily for the core path | None |
| Build artifacts | `test-ws/*/.construct/references/commands.md` — 12 copies, **all gitignored** (`.gitignore:1: test-ws/`) and byte-identical to the source [VERIFIED: `diff -q` + `git check-ignore`] | **None** — see D-11 resolution below |
| Tests asserting counts | Only `>= 15` (`test_capability_registry.py:111`) and `> 25` (`test_doc_command_references.py:177`) — both are lower bounds [VERIFIED: grep] | **None** — adding `card list` breaks no count assertion |

## Resolved: D-11's Open Question (workspace-shipped `commands.md`)

CONTEXT.md D-11 asked the researcher to determine whether `construct/references/commands.md` is templated into new workspaces and whether shipped copies can go stale. **Answer: it is not templated, and the concern is void.**

Evidence [VERIFIED: executed]:
1. `grep -rn "references" src/construct/services/init.py` returns exactly one hit — a comment about an unrelated validation message. **No copy step exists.**
2. A repo-wide search for `cp`/`copy`/`shutil` against `references/` in `claude/` and `src/construct/` returns **nothing**.
3. `git check-ignore -v test-ws/my-construct/.construct/references/commands.md` → `.gitignore:1:test-ws/`. The copies are **untracked local test fixtures**, not tracked artifacts.
4. `diff -q` against the source: **identical**.

**Implication for the planner:** no sync or regeneration mechanism is needed, and no drift-detection task should be created. The copies originate from the older Claude-native skill path exactly as D-11 hypothesised, and they are disposable scratch. The deferred item "Workspace-shipped `commands.md` staleness" can be **closed as not-a-problem** rather than carried forward.

## Broken-Command Inventory (criterion 1 — the concrete work)

`_KNOWN_BROKEN` holds 4 paths. Executing the extractor against the live glob set locates every occurrence [VERIFIED: `_documented()` executed]:

| Allowlist entry | File | Line | Occurrence detail |
|---|---|---|---|
| `knowledge card list` | `construct-synthesis/SKILL.md` | 65 | Fenced block, open-ended synthesis path |
| `knowledge card list` | `construct-synthesis/SKILL.md` | ~159 | Failure-mode table row (inline tick) — **CONTEXT.md notes this** |
| `knowledge card list` | `construct-synthesis/SKILL.md` | ~172 | Validation checklist (inline tick) |
| `knowledge card list` | `construct-gap-analysis/SKILL.md` | 27 | Fenced `bash` block, "Card data" step |
| `knowledge card list` | `construct-gap-analysis/SKILL.md` | ~148 | Validation checklist (inline tick) |
| `knowledge ref list` | `construct-synthesis/SKILL.md` | 71 | Fenced block — no `ref` sub-app exists |
| `workflow run` | `USER-TEST-PLAYBOOK-v03.md` | 276 | Extracted as `workflow run curation-cycle`; the allowlist prefix rule covers it |
| `workflow resume` | `USER-TEST-PLAYBOOK-v03.md` | 291 | — |

Per-document totals across the currently-scanned set [VERIFIED]:

| Document | Invocations | Broken |
|---|---|---|
| `USER-TEST-PLAYBOOK-v03.md` | 22 | 2 |
| `construct-synthesis/SKILL.md` | 4 | 2 |
| `construct-gap-analysis/SKILL.md` | 3 | 1 |
| `construct-card-connect/SKILL.md` | 4 | 0 |
| `construct-spike-run/SKILL.md` | 4 | 0 |
| `construct-card-create`, `card-evaluate`, `curation-cycle`, `workflows/daily-cycle.md` | 3 each | 0 |
| `card-archive`, `card-edit`, `graph-status`, `research-cycle` | 2 each | 0 |
| `views-build`, `views-generate-data`, `workspace-validate` | 1 each | 0 |

**Note:** `workflows/co-authorship.md` and `workflows/cold-start.md` are scanned but contain **zero** `construct ` strings — they are already inside `_DOC_GLOBS` and contribute nothing. Do not mistake their silence for coverage.

**Closing arithmetic:** the allowlist reaches empty via exactly three moves — D-01 makes `card list` resolve (kills 1 entry / 5 occurrences), D-03 rewrites `ref list` out of a still-scanned file (kills 1), D-05 removes both `workflow` steps from a superseded-but-still-globbed file (kills 2).

## The Live Command Registry (criterion 5)

**33 leaves, 14 groups, 47 valid paths** [VERIFIED: `_command_paths(app)` executed]. ROADMAP criterion 5's "25" is wrong, as CONTEXT.md D-12 states. After D-01: **34 leaves**.

```
Leaves (33): ask domain · bridge detect · card evaluate · curation inspect|review|run ·
daily inspect|run · help · ingest source · init · knowledge card archive|create|edit ·
knowledge connection add|list|remove · mcp · research inspect|review|run|score|search ·
spike list|run · status · tag approve|extract|list · validate · views generate|validate ·
workflow status

Groups (14): ask · bridge · card · curation · daily · ingest · knowledge ·
knowledge card · knowledge connection · research · spike · tag · views · workflow
```

**How it is introspected:** `_command_paths()` in the guard test walks `typer.Typer.registered_commands` and `.registered_groups` recursively. There is **no user-facing command that enumerates the surface** — `construct help` is a state-aware suggester, not an inventory. The guard test is the only introspection path, which is why D-12's "point at the test as the live authority" is the right move: it is literally the only mechanical authority that exists.

**The leaf-vs-group distinction is load-bearing.** `workflow` is a *group* with only `status` as a leaf. `workflow run` does not resolve because trailing tokens after a group are read as a subcommand name, whereas trailing tokens after a leaf are positional args (`ingest source ./x` resolves via the `ingest source` leaf). A planner who "fixes" this by loosening `_resolves()` would destroy the test.

## Doc Surface That Must Be Corrected (criteria 3, 4, 5)

Extractor executed against every candidate file [VERIFIED]:

| File | Extractable invocations **today** | Broken | In `_DOC_GLOBS` today? |
|---|---|---|---|
| `CONSTRUCT-CLAUDE-impl/USER_GUIDE.md` | **0** | 0 | No — D-11 adds |
| `construct/references/commands.md` | **0** | 0 | No — D-11 adds |
| `README.md` | **0** | 0 | No (not proposed) |
| `AGENTS.md` | 3 | 0 | No (not proposed) |

### Finding 1 — The zero is the headline

`USER_GUIDE.md` and `commands.md` yield **zero** invocations because both use NL-first tables (`` `research {domain}` ``, `` `init {domain}` ``) that do not begin with the literal token `construct`. D-11 predicted this and asked for empirical confirmation; **confirmed**. The bare `` `construct` `` at `commands.md:15` also does not fire, because `_INVOCATION` requires a following lowercase token.

**Consequence the planner must absorb:** adding these two files to `_DOC_GLOBS` *today* changes nothing and proves nothing. The guard only begins to bite once D-10's CLI column introduces real `construct ...` strings. This is a **task-ordering constraint**, not a free-standing task: the glob extension is only meaningful in or after the change that adds the CLI column.

### Finding 2 — The anti-vacuity guard is global, and that is a real hole

`test_docs_contain_invocations` asserts `sum(len(v) for v in documented.values()) > 10` — a **repo-wide total**, currently ~60. A document added to `_DOC_GLOBS` whose command strings are formatted so the extractor misses them (wrong fence language, a table cell without backticks, a line-wrapped invocation) would sail through: `test_documented_commands_resolve` passes trivially on an empty set, and the global total stays well above 10.

This is precisely the failure mode D-16 was written to forbid — a guard that appears green because of what it *isn't scanning*, one level down from the shrunken-glob risk D-16 names. **Recommend a Wave 0 test** asserting that each doc in a named "must carry invocations" set yields a non-empty invocation set. Write it before the CLI columns land so it goes RED first and proves it can fail.

### Finding 3 — Extractor behaviour the CLI column must respect

`_ARG_START = ^[-<{$"'.,;:)\[/|] | ^[A-Z] | \.\.\.` truncates the path at the first argument-looking token. Confirmed consequences for D-10's third column:
- `construct knowledge card list --domain <domain>` → `("knowledge","card","list")` ✓
- `construct research search {topic}` → `("research","search")` ✓
- Both fenced blocks and inline single-backtick spans are scanned, so a Markdown **table cell** carrying `` `construct daily run` `` fires correctly ✓
- An invocation split across two lines will **not** match (`[ \t]+` deliberately excludes newlines) ✗ — keep each CLI-column invocation on one line.
- "skill-only" / blank rows are inert — the extractor sees nothing. D-10's honesty requirement is mechanically safe.

## `knowledge card list` — Implementation Path (D-01/D-02)

D-01 is confirmed near-mechanical, and cheaper than CONTEXT.md estimates. The template [VERIFIED: read in full]:

| Piece | Template | Notes |
|---|---|---|
| Input model | `ConnectionListInput` — `catalog.py:140` | Mirror as `CardListInput` |
| Registry entry | `knowledge.connection.list` — `catalog.py:295-301` | 7 lines; `cli_name="knowledge.card.list"` |
| CLI wrapper | `connection_list` — `cli.py:1453-1467` | 15 lines: `get_registry().get(...)` → handler → `_display_result` |
| Handler | `list_connections` — `services/knowledge.py:558` | Returns `OperationResult(success, message, data=[...])` |

**Already-existing pieces that do the real work:**
- `WorkspaceLoader.load_cards()` (`storage/workspace.py:147`) parses every card and returns dicts of full frontmatter.
- `_get_archived_card_ids()` (`services/knowledge.py:601`) already implements archive filtering.

### Two concrete hazards in `load_cards()` [VERIFIED: docstring + code read]

1. **It includes the body.** `card_data["body"] = body` at the end of the loop. D-02 requires frontmatter only, never bodies — the handler **must pop `body`**. A naive `return loader.load_cards()` violates D-02 directly and would leak the entire graph's prose through a `--json` enumerate call.
2. **It returns `datetime.date` objects.** The docstring is explicit: `created`/`last_verified` stay as `date` (python-mode dump) because curation decay scans depend on it. `list_connections` by contrast uses `model_dump(mode="json")`. A handler that hands raw `load_cards()` output to `--json` risks a serialization failure or non-ISO output. **Either** re-dump in JSON mode **or** convert the two date fields explicitly. This is the single most likely bug in D-01 and deserves an explicit test.

`lifecycle` is already normalised to a plain string, so that one is safe.

### `knowledge ref list` (D-03)

Not implemented; `construct-synthesis/SKILL.md:71` becomes a scoped `Read` over `refs/`. `Read` is already in synthesis's `allowed-tools`, so **no frontmatter grant changes are needed for D-03** — only D-14's removals touch that line.

## `construct-synthesis` Tool Grants (criterion 3, DEC-01)

Verified [VERIFIED: file read]:
- Frontmatter `:3-8` is **list-style** (`- Read`, `- Bash(construct)`, `- MCP(connect)`, `- WebSearch`, `- WebFetch`), one tool per line.
- `construct-gap-analysis` uses **inline style** (`allowed-tools: Bash(construct), MCP(connect), Read`).

**This is a mechanical trap for D-14.** `test_skill_migration.py:_allowed_tools_line()` returns the *single line* beginning `allowed-tools:` — for synthesis that line is just `allowed-tools:` with the tools on **subsequent lines**. Extending `_MIGRATED_SKILLS` to include `construct-synthesis` without changing the parser produces a **vacuously passing test**: the returned line contains no tool names, so `"WebSearch" not in line` passes even if the grant is still there — and `test_skill_still_delegates_to_cli` would *fail* on the same line for the opposite reason (`Bash(construct)` also absent), which is the signal that will surface the problem.

The planner must therefore treat "extend `test_skill_migration.py` scope" (a CONTEXT.md discretion item) as **requiring a multi-line frontmatter parser**, not a one-word list append. The safest route: parse the YAML frontmatter block properly, or normalise synthesis's frontmatter to inline style as part of D-14's edit. Either is defensible; the decision must be conscious.

Confirmed: `WebSearch`/`WebFetch` appear **only** in frontmatter — zero references in the skill body [VERIFIED: grep]. D-14's "dead grants, removal costs nothing" holds.

## Playbook Supersession (D-05/D-06)

`USER-TEST-PLAYBOOK-v03.md` is 453 lines, §0–§10 plus a results summary [VERIFIED: heading extraction]. Structure maps to v0.3 delivery phases exactly as D-06 describes:

| § | Title | Fate under D-06 |
|---|---|---|
| 0 | Prerequisites & setup (§0.2 fresh smoke workspace) | Carry forward — the reusable asset |
| 1 | Workspace contract & governance (Phase 1) | Carry, re-title by capability |
| 2 | Governed knowledge operations (Phase 2) | Carry; **add `knowledge card list`** |
| 3 | Capability registry, CLI & MCP spine (Phase 3) | Carry |
| 4 | Ingestion (Phase 4) | Carry |
| **5** | **Guided workflow operability** — §5.2 `workflow run`, §5.3 Resume | **Replace** with `research run` → review → resume, and `curation run\|review\|inspect` |
| 6 | Grounded synthesis & bridge detection — *already flagged `requires ANTHROPIC_API_KEY`* | Carry; this flag is D-07's precedent |
| 7 | Derived data & ops UI (Phase 6) | Carry; §7.1 was corrected by Phase 15 D-07 |
| 8 | Governed spikes & tag extraction | Carry |
| 9 | Cross-cutting: machine-readable output | Carry; natural home for D-08's `--json` assertions |
| 10 | Teardown | Carry |
| — | **New** | `daily run\|inspect`, `card evaluate`, `views generate\|validate` |

§5.1 (`help --suggest`) resolves and should survive; only §5.2/§5.3 are broken. Line `:36` carries the stale model-routing reference Phase 14 D-02 fenced here — it lands inside §0.1 Tooling, which is being carried forward, so it must be corrected during the carry rather than assumed gone.

## Loose Ends STATE.md Assigned to Phase 16

Two items in STATE.md's Blockers/Concerns say "Phase 16 to decide". Verified status:

1. **`curation_run.py:417`** — `"; auto_archive_on_decay is set — archiving deferred to Phase 12 "` is **still present** (at `:417`, not `:414`) in `src/construct/llm/curation_run.py`. Phase 12 shipped, so this is a live audit-trail-that-lies. It is a *runtime summary string*, not a documented invocation — outside FIX-03's mechanical criterion but squarely inside the phase's spirit. One-line fix; the planner should decide explicitly rather than let it drift to Phase 17.
2. **`views.per_card_hooks` inert-feature docs** — `README.md` is **already clean** (grep for `per_card_hooks|debounce|auto_regenerate` returns nothing; STATE.md's `:263-264` reference is stale). Only **`construct/references/commands.md:81`** still documents the inert debounce hooks. Since D-10/D-11 already open that file, correcting line 81 is nearly free and closes the item.

## Common Pitfalls

### Pitfall 1: Emptying the allowlist by shrinking the scan
**What goes wrong:** `USER-TEST-PLAYBOOK-v03.md` is deleted and its glob entry removed; `_KNOWN_BROKEN` loses two entries without either command being addressed.
**Why it happens:** it is the path of least resistance and the tests still pass.
**How to avoid:** D-05/D-16 — the v0.4.1 playbook replaces the v0.3 entry in `_DOC_GLOBS`.
**Warning sign:** a diff that removes a `_DOC_GLOBS` line without adding one.

### Pitfall 2: Vacuous glob extension
**What goes wrong:** `USER_GUIDE.md`/`commands.md` join `_DOC_GLOBS` but yield zero invocations; the guard reports green while proving nothing.
**Why it happens:** the anti-vacuity check is a repo-wide total (~60), not per-doc.
**How to avoid:** Wave 0 per-doc non-vacuity test; assert each newly-globbed doc yields ≥ 1 invocation.
**Warning sign:** the two new parametrized `test_documented_commands_resolve` cases pass on the very first run, before any CLI column exists.

### Pitfall 3: `card list` returns bodies or non-serializable dates
**What goes wrong:** handler returns `load_cards()` directly — leaks bodies (violates D-02) and emits `datetime.date` into `--json`.
**How to avoid:** pop `body`; dump in JSON mode. Test both explicitly.
**Warning sign:** `--json` output is large, or dates render as `datetime.date(2026, 7, 20)`.

### Pitfall 4: Vacuous `test_skill_migration` extension
**What goes wrong:** `construct-synthesis` is added to `_MIGRATED_SKILLS`; its multi-line frontmatter defeats the single-line parser and the forbidden-tool assertions pass regardless of the grants.
**How to avoid:** parse the frontmatter block, or normalise synthesis to inline style.
**Warning sign:** `test_skill_drops_forbidden_tools[construct-synthesis]` passes *before* the grants are removed. (`test_skill_still_delegates_to_cli` failing on the same skill is the tell.)

### Pitfall 5: Writing a command count into a doc
**What goes wrong:** "34 commands" replaces "25 commands" and rots on the next command.
**How to avoid:** D-12 — describe by capability group; cite the guard test as the authority.

### Pitfall 6: Loosening `_resolves()` to make `workflow run` pass
**What goes wrong:** the group/leaf distinction is relaxed and the guard stops catching an entire defect class.
**How to avoid:** the fix is removing the string from the doc, never widening the resolver.

## Anti-Patterns to Avoid

- **Backfilling a plausible-looking command** into an empty CLI-column row. D-10 requires honest blanks.
- **Re-implementing card frontmatter parsing** in the handler when `load_cards()` exists.
- **Registering `card list` outside the registry** (the views-group exception is explicitly not a precedent — D-01).
- **Building a `commands.md` sync mechanism** — the shipped copies are gitignored scratch (resolved above).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Enumerating cards with frontmatter | Custom `cards/*.md` walker | `WorkspaceLoader.load_cards()` | Handles parse errors, lifecycle normalisation |
| Archive filtering | New lifecycle check | `_get_archived_card_ids()` (`knowledge.py:601`) | Already used by `list_connections` |
| CLI+MCP parity for `card list` | Separate MCP registration | Registry `cli_name=` — parity is automatic | Phase 11-03 established this |
| Command-surface introspection | New enumeration command | `_command_paths()` in the guard | Only mechanical authority that exists |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv`) |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/python -m pytest tests/contract/test_doc_command_references.py tests/contract/test_skill_migration.py -q` (41 tests, 0.51s) |
| Full suite command | `.venv/bin/python -m pytest -q` |
| **Baseline** | **489 passed, 2 warnings, 8.6s** [VERIFIED] |

> Note: bare `python` fails under pyenv in this repo. Use `.venv/bin/python`.

### Sampling strategy for "every command string resolves"

The guard is **exhaustive, not sampled** — it enumerates every `construct ...` string in every globbed doc and resolves each against the live app. The Nyquist question is therefore not "how often do we sample the docs" but **"how often do we sample the guard's own adequacy"**, because the guard has two demonstrated ways to be silently vacuous (Pitfalls 2 and 4). The minimum validation set must include tests that fail when the guard stops looking.

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | Exists? |
|---|---|---|---|---|
| FIX-03 | `_KNOWN_BROKEN` is empty | contract | `pytest tests/contract/test_doc_command_references.py -q` | ✅ (assertion emerges as entries are deleted) |
| FIX-03 | Every string in every globbed doc resolves | contract | `pytest -k test_documented_commands_resolve` | ✅ |
| FIX-03 | `knowledge card list` resolves | contract | `pytest -k test_command_surface_is_discoverable` | ⚠️ extend — add `("knowledge","card","list")` |
| FIX-03 | `card list` returns frontmatter, **no bodies** (D-02) | unit | `pytest tests/unit/ -k card_list_excludes_body` | ❌ Wave 0 |
| FIX-03 | `card list --json` emits ISO dates, not `date` objects | unit | `pytest tests/unit/ -k card_list_json_serializable` | ❌ Wave 0 |
| FIX-03 | `card list` reaches CLI **and** MCP (parity) | contract | `pytest tests/contract/ -k card_list_cli_mcp` | ❌ Wave 0 |
| DOC-04 | `USER_GUIDE.md` / `commands.md` are scanned | contract | `pytest -k test_documented_commands_resolve` | ⚠️ needs `_DOC_GLOBS` extension |
| DOC-04 | **Each newly-globbed doc yields ≥1 invocation** (anti-vacuity) | contract | `pytest -k test_key_docs_are_not_vacuous` | ❌ **Wave 0 — highest value** |
| DOC-04 | v0.4.1 playbook remains globbed | contract | `pytest -k test_documented_commands_resolve` | ⚠️ glob path update |
| DOC-04 | Playbook offline sections execute (D-09 part 2) | manual | — human run against fresh smoke workspace | ❌ manual by D-09 |
| DEC-01 | synthesis declares no `WebSearch`/`WebFetch` | contract | `pytest tests/contract/test_skill_migration.py -q` | ⚠️ scope + parser fix |
| DEC-01 | synthesis still delegates via `Bash(construct)` | contract | same | ⚠️ same |

### Observable signals

| Signal | Where | Meaning |
|---|---|---|
| `_KNOWN_BROKEN == {}` | source-visible | FIX-03's mechanical criterion (REQUIREMENTS.md:89) |
| `test_known_broken_entries_are_still_broken` count → 0 params | pytest output | Allowlist genuinely empty, not bypassed |
| Per-doc parametrized case count | pytest `-v` IDs | Reveals glob set changes; a **dropped** doc ID is the D-16 red flag |
| Per-doc invocation count ≥ 1 | new Wave 0 test | Guard is actually looking |
| Full suite ≥ 489 | `pytest -q` | No collateral regression |

### Minimum regression-catching set

1. `test_doc_command_references.py` — full file (catches broken strings and, via param IDs, glob shrinkage).
2. New per-doc non-vacuity test — catches the Pitfall 2 false green.
3. `test_skill_migration.py` with a working multi-line parser — catches the Pitfall 4 false green.
4. `card list` unit tests for body-exclusion and JSON date serialization.
5. Full suite for collateral.

Items 2–4 do not exist today. **They are the Wave 0 deliverable**, and 2 and 3 must be written to go RED before their subjects change.

### Wave 0 Gaps

- [ ] Per-doc non-vacuity test in `test_doc_command_references.py` — DOC-04
- [ ] Multi-line frontmatter parser in `test_skill_migration.py` — DEC-01
- [ ] `card list` body-exclusion unit test — FIX-03 / D-02
- [ ] `card list` JSON date-serialization unit test — FIX-03
- [ ] `card list` CLI/MCP parity contract test — FIX-03 / D-01
- [ ] Extend `test_command_surface_is_discoverable` with `("knowledge","card","list")`

*Framework install: none needed.*

## Security Domain

Low-surface phase; one control genuinely applies.

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| **V5 Input Validation** | **yes** | Pydantic `CardListInput` with `extra=forbid`, mirroring `ConnectionListInput` |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Mitigation |
|---|---|---|
| `--workspace` path traversal on `card list` | Information Disclosure | Reuse `WorkspaceLoader`'s existing resolution — do not accept arbitrary paths on a new code path |
| Card **bodies** leaked through an enumerate call | Information Disclosure | D-02 — pop `body`. This is a security rationale for D-02, not only an ergonomic one |
| Playbook requiring real credentials | Credential exposure | D-07 — offline/mock by default; credentialed steps opt-in |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python venv | all tests | ✓ | `.venv` | none needed |
| pytest | contract suite | ✓ | 489 tests green | — |
| Typer | CLI introspection | ✓ | in-tree | — |
| `ANTHROPIC_API_KEY` | playbook §6 only | not checked | — | **D-07: opt-in; core playbook path is offline** |
| Tavily key | live search | not checked | — | **D-07: `default_provider: mock`** |

**Missing with no fallback:** none.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Synthesis's multi-line frontmatter defeats `_allowed_tools_line()` — inferred from reading both the parser and the file, not from executing the extended test | DEC-01 | Low — the fix (parse properly) is correct either way; worst case it is belt-and-braces |
| A2 | `test-ws/` copies of `commands.md` originate from the older Claude-native skill path | D-11 resolution | None — they are gitignored and untracked, so provenance does not affect any task |
| A3 | Line numbers cited as `~159`, `~172`, `~148` are approximate (located by content, not by exact offset) | Broken-command inventory | None — the planner should locate by string, which is more robust anyway |

## Open Questions

1. **Does `test_skill_migration.py`'s parser get fixed, or does synthesis's frontmatter get normalised to inline style?**
   - Known: both close the hole; CONTEXT.md leaves the mechanism to discretion.
   - Recommendation: fix the parser. Normalising the file makes the *data* fit the *test*, which is backwards, and the next multi-line skill reopens the hole.

2. **Is `curation_run.py:417`'s stale "deferred to Phase 12" string in scope?**
   - Known: still present; STATE.md assigns the decision here; it is a runtime string, not a documented invocation.
   - Recommendation: fix it here. One line, and leaving it re-creates the audit-trail-that-lies class this milestone exists to clear.

3. **Do ROADMAP.md / REQUIREMENTS.md get their "25-command surface" text corrected here?**
   - Known: CONTEXT.md leaves this to the planner; the number is factually wrong (33 now, 34 after D-01).
   - Recommendation: correct in place per D-12 (describe, do not count). Leaving a known-false number in the document that defines the phase's success criteria is the exact defect class under repair.

## State of the Art

| Old | Current | When | Impact |
|---|---|---|---|
| "25-command surface" | 33 leaves / 47 paths; 34 after D-01 | Phases 10–15 | D-12 — stop counting |
| "439 tests green" (STATE.md:11 / REQUIREMENTS.md:11) | **489** | Phase 15 | Baseline for regression comparison |
| `workflow run` / `workflow resume` | `research run` → review → resume; `curation run` | Phase 12 D-10 | Drives D-06's §5 rewrite |
| `README.md` per-card-hooks docs | already clean | Phase 15-05 | STATE.md's `:263-264` is stale; only `commands.md:81` remains |

## Sources

### Primary (HIGH confidence — executed against the live tree)
- `_command_paths(app)` — live Typer introspection, 33 leaves / 14 groups
- `_documented()` + `_invocations()` — per-doc invocation and breakage counts
- `pytest -q` — 489 passed baseline; guard subset 41 passed
- `git check-ignore` / `diff -q` — `test-ws/` copy provenance
- Direct reads: `test_doc_command_references.py`, `test_skill_migration.py`, `catalog.py:140,288-310`, `cli.py:1445-1470`, `services/knowledge.py:558-620`, `storage/workspace.py:140-175`, both SKILL.md files, `USER-TEST-PLAYBOOK-v03.md` headings, `README.md`, `AGENTS.md`

### Secondary (MEDIUM)
- `.planning/phases/16-invocation-user-doc-truth/16-CONTEXT.md` — D-01…D-16 (all ground-truth claims independently re-verified)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`

### Tertiary
- None. No web research was required or performed.

## Metadata

**Confidence breakdown:**
- Command surface: HIGH — introspected directly
- Broken inventory: HIGH — extractor executed
- Doc surface: HIGH — extractor executed against every candidate
- `card list` path: HIGH — template and helpers read in full
- Guard vacuity risks: HIGH — read from test source; A1 flagged as inferred
- Playbook structure: HIGH — headings extracted

**Research date:** 2026-07-20
**Valid until:** until the next commit touching `cli.py`, `catalog.py`, or `_DOC_GLOBS` — this is a repo-state snapshot, not durable external knowledge.
