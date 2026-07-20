# Phase 16: Invocation & User-Doc Truth - Context

**Gathered:** 2026-07-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Every command string a user or agent executes from CONSTRUCT's documentation resolves against the live registry and runs — proven mechanically by `_KNOWN_BROKEN` in `tests/contract/test_doc_command_references.py` reaching **empty** with the suite green. Scope covers three requirements:

- **FIX-03** — the four allowlisted broken references (`knowledge card list`, `knowledge ref list`, `workflow run`, `workflow resume`).
- **DOC-04** — the user-facing doc set (`USER_GUIDE.md`, `construct/references/commands.md`, `README.md` lineage, `AGENTS.md:284`, the release playbook) describes and can invoke the v0.4 runtime.
- **DEC-01** — `construct-synthesis`'s `WebSearch` / `WebFetch` grants, closing `spec-v04:436`.

**Not in this phase:** the architecture doc set (`architecture-overview.md`, `artifact-catalog.md`, `config-topology.md`) and the `daily.run` Claude-native entry point — Phase 17 owns DOC-01, DOC-02, UX-01.

</domain>

<decisions>
## Implementation Decisions

### Ground truth established during discussion (do not re-derive)

The live Typer app was probed directly. **The surface is 33 leaf commands, not 25.** ROADMAP criterion 5 and the v0.4 audit both say "25" — that number is stale and must not be propagated. After D-01 it becomes 34 CLI leaves / 22 MCP tools.

Full live surface at discussion time:

```
ask domain · bridge detect · card evaluate · curation inspect|review|run ·
daily inspect|run · help · ingest source · init ·
knowledge card archive|create|edit · knowledge connection add|list|remove ·
mcp · research inspect|review|run|score|search · spike list|run · status ·
tag approve|extract|list · validate · views generate|validate · workflow status
```

`_KNOWN_BROKEN` and where each entry lives:

| Entry | Occurrences |
|---|---|
| `knowledge card list` | `construct-synthesis/SKILL.md:65`, `construct-gap-analysis/SKILL.md:27` |
| `knowledge ref list` | `construct-synthesis/SKILL.md:71` — **no `ref` sub-app exists at all** |
| `workflow run` | `USER-TEST-PLAYBOOK-v03.md:276` **only** |
| `workflow resume` | `USER-TEST-PLAYBOOK-v03.md:291` **only** |

### `knowledge card list` / `knowledge ref list` (criterion 2, FIX-03)

- **D-01:** `knowledge card list` is **implemented as a real command**, registered as `knowledge.card.list` in `capabilities/catalog.py` with **full CLI + MCP parity**, mirroring the existing `knowledge.connection.list` (`catalog.py:295`, CLI wrapper `cli.py:1453`).

  **Rationale — this is closing an asymmetry, not adding a capability.** The graph already has an enumerate command for *edges* (`knowledge connection list`) but none for *nodes*. `construct-gap-analysis` needs structured frontmatter for every card (id, title, epistemic_type, confidence, source_tier, domains, content_categories, lifecycle, created, updated) and already consumes `knowledge connection list --json` immediately alongside it. This is the symmetric half of a command pair that exists.

  The "rewrite both skills onto Read globs" branch was considered and **rejected**: it reverses Phase 12 (API-04)'s thin-wrapper direction and pushes frontmatter parsing back into the skill layer.

  **Registry-routed, not hand-written.** This is the `connection list` pattern, *not* Phase 15 D-03's views exception — no new CLI/MCP drift is created.

- **D-02:** `card list` returns **full frontmatter, never card bodies.** Serves gap-analysis in one call with no second pass, and preserves synthesis's "enumerate, then `Read` the promising ones individually" flow because bodies are excluded. Filtering/scoping flags (`--domain`, `--include-archived`) should mirror `connection list`'s shape — see Discretion.

- **D-03:** `knowledge ref list` is **not implemented.** Standing up an entire new `ref` sub-app for one advisory lookup is disproportionate. `construct-synthesis/SKILL.md:71` is rewritten as a **scoped `Read` over `refs/`** — the skill already grants `Read` and already uses it for individual card inspection, so no new tool grant is needed and the step's intent ("also check `refs/` for supporting references") is preserved rather than dropped.

  Logged as a deferred idea, not silently discarded — see `<deferred>`.

- **D-04:** **Surface-count consequence recorded for Phase 17.** D-01 takes the live surface to **34 CLI leaves / 22 MCP tools**. Phase 17's DOC-02 owns the capability/CLI/MCP inventory in `artifact-catalog.md` and must inventory the *post-Phase-16* reality. **No blocking dependency in either direction** — Phase 16 does not edit `artifact-catalog.md`, and Phase 17 must not block on Phase 16.

### Release playbook (criterion 5, DOC-04)

- **D-05:** `USER-TEST-PLAYBOOK-v03.md` is **superseded, not deleted.** A new `USER-TEST-PLAYBOOK-v041.md` is written; the v0.3 file is removed; **the new file stays in the guard's `_DOC_GLOBS`** (`test_doc_command_references.py:_DOC_GLOBS`).

  **This is the load-bearing choice.** `.planning/STATE.md:203` already warns: *"retiring the playbook removes the `workflow run` / `workflow resume` allowlist entries — coordinate so the guard ends empty, not merely unscanned."* Deleting the file and dropping the glob would empty the allowlist by **shrinking what the guard scans** — satisfying FIX-03 on paper while weakening the very test that defines it. Under D-05 those two entries die because the commands are gone from a **still-scanned** document.

  Secondary rationale: `spec-v05-ui-primary.md:152` already anticipates a `USER-TEST-PLAYBOOK-v05`, so the artifact is designed to live on per-version. Deleting outright would leave v0.4.1 with no executable release-validation artifact at all.

- **D-06:** **Coverage** — carry the working v0.3 sections forward (workspace contract & governance, governed knowledge operations, capability registry / CLI / MCP spine, ingestion, grounded synthesis & bridge detection, derived data & ops UI, governed spikes & tag extraction, machine-readable output, teardown), and:
  - replace §5.2 "Run a workflow" / §5.3 "Resume" — whose `workflow run curation-cycle` and `workflow resume` are the two playbook-only allowlist entries — with the **real successor flow**: `research run` → durable human review → resume, and `curation run|review|inspect`;
  - **add** `daily run|inspect`, `card evaluate`, `views generate|validate`, and the new `knowledge card list`;
  - reorganise **by capability**, not by v0.3 phase number — the existing "§1 (Phase 1) … §8 (Phase 6)" structure encodes a delivery history that no longer maps to anything a user cares about.

- **D-07:** **Offline-runnable by default.** Every step must run against the mock/default search provider and offline paths unless **explicitly marked** as requiring credentials — following the v0.3 file's own precedent (§6 is already flagged `— requires ANTHROPIC_API_KEY`). Steps needing `ANTHROPIC_API_KEY` (LLM gates) or a Tavily key (live search) are opt-in extras. Release validation must stay runnable by anyone with a checkout; a playbook that fails for missing secrets cannot serve as a build signal.

- **D-08:** **Assertions read `--json` status fields, not process exit codes**, for `curation run`, `research run`, and `daily run`.

  **Rationale — this encodes an existing decision the playbook would otherwise contradict.** Phase 11 established that a **degraded `curation.run` exits 0 on purpose**; failure surfaces in status output, JSON, and the event log, *not* the exit code. A step asserting "exit 0 = passed" would silently green-light a degraded run. This also matches `daily.run`'s isolate-and-degrade reporting (Phase 13). Expected-result text reads per-step `completed` / `degraded` / `skipped`.

- **D-09:** **Definition of done for "runs end to end"** (criterion 5) is two-part:
  1. `test_doc_command_references.py` proves every string **resolves** against the live Typer app, with `_KNOWN_BROKEN` empty — mechanical and permanent;
  2. the phase **additionally executes the offline sections once** against a freshly scaffolded smoke workspace and records the result.

  Resolution alone is insufficient — a step can resolve and still fail at runtime. Adding the playbook to CI as an automated smoke suite was considered and **rejected as out of scope**: that is new test infrastructure, larger than a documentation-truth phase.

### User-facing doc shape (criterion 4, DOC-04)

- **D-10:** **NL-first framing is preserved; a CLI column is added.** `USER_GUIDE.md`'s "Full Command Reference" (§219–292) and `construct/references/commands.md` both use "You say" → "What happens" tables today. Each table gains a **third column carrying the real `construct ...` invocation**.

  **Rationale:** the NL framing is deliberate — it matches the Claude-native interaction model PROJECT.md names as the near-term UX. Criterion 4 asks for CLI *invocability*, which is an addition, not a replacement. Restructuring CLI-first would demote the product's actual entry path. Rows with no CLI equivalent must show that **honestly** (blank / "skill-only") rather than inventing a command.

  `USER_GUIDE.md` must reach the criterion-named surface: `research search|score|run|review|inspect`, `curation run|review|inspect`, `daily run|inspect`, `card evaluate`.

- **D-11:** **`USER_GUIDE.md` and `construct/references/commands.md` are added to `_DOC_GLOBS`.**

  **Rationale:** neither is scanned today. D-10 puts executable `construct ...` strings into both — without extending the guard, this phase would *create* a fresh crop of unguarded invocation strings, which is precisely the drift class FIX-04 exists to prevent and precisely where DOC-04's defects came from. The requirement that the new strings be correct on day one is the point, not a cost.

  **Verify before relying on it:** the extractor (`_INVOCATION = \bconstruct[ \t]+([a-z][\w \t-]*)`) should not fire on `commands.md`'s existing NL entries (`` `research {domain}` ``, `` `init {domain}` ``) because they do not begin with `construct`, nor on the bare `` `construct` `` at `commands.md:15` because the regex requires a following lowercase token. Planner/researcher must confirm this empirically rather than assume it.

  **Open question for the researcher:** `construct/references/commands.md` appears to be a **workspace-shipped** reference — copies exist at `test-ws/*/.construct/references/commands.md`. A grep of `services/init.py` found no copy step, so the copies may originate from the older Claude-native skill path. Determine whether the source file is templated into new workspaces, and if so, whether shipped copies can go stale relative to the guarded source.

- **D-12:** **No hard command counts anywhere in the doc set.** Docs describe the surface by capability group and never assert a number — any number goes stale the next time a command lands, which is exactly how "25" rotted. Where a count would genuinely help, point at `tests/contract/test_doc_command_references.py` as the live authority.

  **Explicitly recorded:** ROADMAP criterion 5's *"the live 25-command surface"* is factually wrong and reads as **34** after D-01. Do not write "25" into any document. Correcting the ROADMAP/REQUIREMENTS text itself is the planner's call.

- **D-13:** **`AGENTS.md` / `README.md` edits are a bounded, named list** — the fence pattern Phases 14 and 15 both used successfully:
  - `AGENTS.md:284` — currently reads *"CLI subcommands (`init`, `validate`; more in v0.3)"*, describing a two-command CLI. Correct against the live surface (subject to D-12 — no count).
  - `README.md` product-lineage block (`:33–50`) — currently stops at *"v0.4 next — Agent workflows"*; v0.4 shipped 2026-07-07 and v0.4.1 is in flight. Also `:17–18`, `:105–115`'s "ACTIVE — v0.3 pipeline/API runtime" descriptions.
  - `AGENTS.md:91,134` — stale `model-routing.yaml` references that **Phase 14 D-02 explicitly fenced off to this phase**. Picking them up here keeps the hand-off legible.

  A full `AGENTS.md` accuracy pass was **rejected** — it overlaps heavily with the architecture doc set Phase 17's DOC-01 owns.

### `construct-synthesis` tool grants (criterion 3, DEC-01)

- **D-14:** **Both `WebSearch` and `WebFetch` are removed** from `construct-synthesis/SKILL.md`'s `allowed-tools` (lines 7–8), and `tests/contract/test_skill_migration.py`'s scope is **extended to cover `construct-synthesis`** so the grants cannot silently return.

  **Evidence gathered during discussion — this branch is not a judgement call:**
  1. `spec-v04-agentworkflows.md:436` states the rule itself: *"Claude WebSearch | Migration fallback only | **Remove from skill `allowed-tools` when `research.run` ships**."* `research.run` shipped in Phase 10. The condition is satisfied.
  2. **The skill body never uses them.** `WebSearch`/`WebFetch` appear *only* in the frontmatter — zero references anywhere in the procedure. These are dead grants; removal costs nothing at runtime.
  3. `test_skill_migration.py:34` already defines `_FORBIDDEN_TOOLS = ("WebSearch", "WebFetch", "Write", "Edit")` — the enforcement mechanism exists and synthesis is merely outside its scope.
  4. D-03's rewrite puts the `ref list` step on `Read`, which is already granted — nothing in this phase's changes needs web access.

  The "record a reasoned exception in PROJECT.md" branch (permitted by criterion 3) was **rejected**: it would document an exception for capabilities the skill demonstrably does not use — recording a fiction rather than a decision.

- **D-15:** **`spec-v04-agentworkflows.md:436` is marked discharged in this phase.** DEC-01 names that line as the thing being closed, so leaving a live instruction to do work already done would reproduce the exact rot this milestone exists to clear.

  **Fence:** `spec-v04:211` and `:557` (model-routing) stay with **Phase 17**'s spec pass — Phase 14 D-02 deferred them to "Phase 16/17", and keeping them with the rest of the model-routing cleanup keeps the boundary legible. Do not touch them here.

### Commit ordering constraint (spans all areas)

- **D-16:** The allowlist must reach empty by **removal of broken references from scanned documents**, never by narrowing the scan surface. Concretely: `_KNOWN_BROKEN` entries may only be deleted in the same change that makes the corresponding command resolve (`card list` → D-01) or removes it from a document that **remains** in `_DOC_GLOBS` (`workflow run`/`resume` → D-05, `ref list` → D-03). The paired still-broken assertion in `test_doc_command_references.py` enforces the mechanics; this decision records the *intent* so a future reader cannot mistake a shrunken glob set for a fix.

### Claude's Discretion

- Exact flag surface for `knowledge card list` — `--domain` / `--include-archived` / `--workspace` naming and short forms, guided by `connection list`'s existing shape (`--card`/`-c`, `--include-archived`, `--workspace`/`-w`, `--json`/`-j`).
- The `knowledge.card.list` handler's location and internal structure within `capabilities/`, and its JSON envelope shape (subject to D-02: full frontmatter, no bodies).
- Whether `card list` is one commit or shares a plan with the skill rewrites.
- `USER-TEST-PLAYBOOK-v041.md`'s exact filename slug, section numbering, and smoke-workspace setup steps (§0.2's pattern is a reasonable starting point).
- Precise wording of the CLI column headers in `USER_GUIDE.md` / `commands.md`, and how "no CLI equivalent" rows are rendered.
- Whether ROADMAP.md / REQUIREMENTS.md's "25-command surface" text is corrected in this phase or flagged for the milestone audit.
- Exact replacement prose for `AGENTS.md:284` and the `README.md` lineage block, provided D-12 (no hard counts) holds.
- How `test_skill_migration.py`'s scope is extended to `construct-synthesis` (adding to an existing list vs. broadening a glob).
- Plan decomposition across the four areas.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The guard that defines "done"
- `tests/contract/test_doc_command_references.py` — **the mechanical completion criterion.** `_KNOWN_BROKEN` (`:152–157`) must end empty. `_DOC_GLOBS` (`:~30`) is extended by D-11. The extractor regex `_INVOCATION` and the leaf-vs-group distinction in `_command_paths()` govern what counts as a resolving reference.
- `tests/contract/test_skill_migration.py` — `_FORBIDDEN_TOOLS` at `:34`; scope extended by D-14.

### Command surface & registry
- `src/construct/capabilities/catalog.py` — `knowledge.connection.list` at `:295–301` is the pattern D-01 mirrors.
- `src/construct/cli.py` — `connection_list` CLI wrapper at `:1453–1467`; the views group's hand-written exception at `:868`/`:893` is what D-01 deliberately does **not** follow.

### Files this phase edits
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md` — frontmatter `:3–8` (D-14); `card list` at `:65`, `ref list` at `:71` (D-01/D-03); fallback note at `:159`; checklist at `:172`. **Note `:130`** — synthesis carries a views-refresh step that is an *exemption recorded in `adr-0005`*, not a leftover; do not remove it.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-gap-analysis/SKILL.md` — `card list` at `:27`, checklist at `:148`.
- `CONSTRUCT-CLAUDE-impl/USER_GUIDE.md` — "Full Command Reference" `:219–292` (D-10).
- `CONSTRUCT-CLAUDE-impl/construct/references/commands.md` — NL/skill mapping tables (D-10, D-11).
- `USER-TEST-PLAYBOOK-v03.md` — superseded by D-05. Broken steps at `:276`, `:291`. Note `:333`/`:411` were already corrected by Phase 15 D-07, and `:36` carries a stale model-routing reference deferred here by Phase 14 D-02.
- `README.md` — lineage `:33–50`; also `:17–18`, `:105–115` (D-13).
- `AGENTS.md` — `:284` CLI description; `:91`,`:134` model-routing (D-13).
- `CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md` — **`:436` only** (D-15). `:211`/`:557` are fenced to Phase 17.

### Decisions this phase must not contradict
- `.planning/phases/15-views-generate-data-resolution/15-CONTEXT.md` — D-07 (playbook edits already made), D-03 (views CLI/MCP drift accepted), D-11 (views-refresh ownership reversal).
- `.planning/phases/14-durable-state-config-truth/14-CONTEXT.md` — **D-02's edit fence**, which explicitly hands `AGENTS.md:91,134` and `USER-TEST-PLAYBOOK-v03.md:36` to this phase.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` — synthesis's views-refresh exemption (`construct-synthesis/SKILL.md:130`).
- **Phase 11's curation exit-code contract** — a degraded `curation.run` exits 0 by design; failure surfaces in status/JSON/event log. Load-bearing for D-08. Do not "fix" this.

### Milestone framing
- `.planning/ROADMAP.md:130–140` — Phase 16 goal and the five success criteria. **Criterion 5's "25-command surface" is wrong; reads 34.**
- `.planning/REQUIREMENTS.md` — FIX-03 `:23`, DOC-04 `:30`, DEC-01 `:38`, mechanical completion criteria `:86–90`.
- `.planning/milestones/v0.4-MILESTONE-AUDIT.md:142–148`, `:288` — the audit that raised these defects. **Sealed historical record — do not edit** (Phase 14 D-09).
- `.planning/STATE.md:203` — the playbook/allowlist coordination warning underpinning D-05 and D-16.
- `.planning/PROJECT.md` — v0.4.1 milestone scope and Out of Scope list.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`knowledge.connection.list`** (`catalog.py:295`, `cli.py:1453`) — the complete template for D-01: registry entry, CLI wrapper, `--json`/`-j`, `--workspace`/`-w`, filter flag, `--include-archived`, `_display_result`. `card list` should be near-mechanical against it.
- **`test_doc_command_references.py`'s introspection** (`_command_paths`) — already walks the live Typer app recursively and distinguishes leaves from groups. Nothing new is needed to validate the extended globs.
- **`test_skill_migration.py`'s `_FORBIDDEN_TOOLS`** — the enforcement mechanism D-14 needs already exists; only its scope changes.
- **`USER-TEST-PLAYBOOK-v03.md` §0.2** — an existing fresh-smoke-workspace setup recipe the v0.4.1 playbook can carry forward.

### Established Patterns
- **Registry-first for capabilities.** Every knowledge/research/curation/daily command routes through `capabilities/catalog.py` for CLI+MCP parity. The views group is the one recorded exception (Phase 15 D-03) and is explicitly *not* a precedent for D-01.
- **Guard-defined completion.** FIX-04's allowlist "can only shrink" — a paired test asserts each entry is *still broken*, so a landed fix forces its deletion. D-16 records the intent this mechanism enforces.
- **Named edit fences.** Phases 14 and 15 both scoped doc work to explicit file:line lists and recorded deliberate crossings. D-13 and D-15 follow this.
- **Skills as thin wrappers.** Phase 12 (API-04) removed direct `WebSearch`/`WebFetch`/workspace writes from research and curation skills. D-14 finishes the job; D-01/D-03 keep the two remaining skills on that trajectory.

### Integration Points
- `capabilities/catalog.py` — new `knowledge.card.list` registry entry (bumps MCP tools 21 → 22).
- `src/construct/cli.py` — new `card list` wrapper under the existing `knowledge card` sub-app (bumps CLI leaves 33 → 34).
- `tests/contract/test_doc_command_references.py` — `_KNOWN_BROKEN` shrinks to empty; `_DOC_GLOBS` gains two entries.
- `tests/contract/test_skill_migration.py` — scope gains `construct-synthesis`.
- Repo root — `USER-TEST-PLAYBOOK-v03.md` removed, `USER-TEST-PLAYBOOK-v041.md` added.

</code_context>

<specifics>
## Specific Ideas

- **"The guard ends empty, not merely unscanned"** — the phrase from `.planning/STATE.md:203` that D-05 and D-16 exist to honour. If a reviewer reads one line of this context, make it that one.
- The v0.4.1 playbook should be organised **by capability**, not by the v0.3 delivery-phase numbering that currently structures §1–§8.
- Rows in the CLI column with no command equivalent must be shown honestly (blank / "skill-only") — never backfilled with a plausible-looking invented command.
- `card list` returning bodies was explicitly rejected: an enumerate command must not return the whole graph's prose.

</specifics>

<deferred>
## Deferred Ideas

- **`knowledge ref` sub-app with `list`** — the future home if `refs/` ever needs structured enumeration. Deferred because standing up a new sub-app for one advisory lookup in one skill is disproportionate (D-03). Note the resulting asymmetry: cards and connections have enumerate commands; refs do not.
- **Playbook as an automated CI smoke suite** — running the offline sections on every commit would be the strongest guarantee behind criterion 5, but that is new test infrastructure, larger than a documentation-truth phase (rejected in D-09).
- **`spec-v04-agentworkflows.md:211` / `:557`** — stale model-routing references, fenced to Phase 17's spec pass (D-15).
- **`artifact-catalog.md` inventory update to 34 CLI / 22 MCP** — Phase 17 (DOC-02) owns it (D-04).
- **Full `AGENTS.md` accuracy pass** — overlaps Phase 17's DOC-01 architecture doc set (D-13).
- **Workspace-shipped `commands.md` staleness** — if `construct/references/commands.md` is templated into new workspaces, existing workspace copies may drift from the guarded source. Flagged for the researcher in D-11; a sync/regeneration mechanism, if needed, is out of scope here.
- **`views validate` accepting the bytes `views generate` writes** — Phase 15's recorded known-open contract question. Not raised as a Phase 16 gray area; remains open for Phase 17 or later.

</deferred>

---

*Phase: 16-invocation-user-doc-truth*
*Context gathered: 2026-07-20*
