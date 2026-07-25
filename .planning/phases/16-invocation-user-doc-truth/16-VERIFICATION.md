---
phase: 16-invocation-user-doc-truth
verified: 2026-07-25T14:05:22Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 16: Invocation & User-Doc Truth — Verification Report

**Phase Goal:** Every command string a user or agent executes from CONSTRUCT's documentation resolves against the live registry and runs.
**Verified:** 2026-07-25T14:05:22Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_KNOWN_BROKEN` is empty and full suite is green; every `construct ...` string in skills, workflow docs, and the release playbook resolves | ✓ VERIFIED | Ran `.venv/bin/python -m pytest -q -p no:cacheprovider` myself: **515 passed, 1 skipped, 0 failed** — exact expected terminal state. Imported the test module directly: `len(_KNOWN_BROKEN) == 0`, `len(_DOC_GLOBS) == 5`. `-v` run of `test_documented_commands_resolve` shows all 30 parametrized docs PASSED (28 skills/workflows + playbook + USER_GUIDE.md + commands.md); the single skip is the empty-parametrize placeholder for `test_known_broken_entries_are_still_broken`, confirming the allowlist is genuinely empty rather than bypassed. |
| 2 | `knowledge card list` / `knowledge ref list` have one recorded decision — real commands or skills rewritten | ✓ VERIFIED | `knowledge card list` is a real Typer leaf (`--domain`, `--include-archived`, `--workspace`, `--json` all present in `--help`), registry-routed via `CapabilityRecord(id="knowledge.card.list", cli_name=..., mcp_tool_name="construct_list_cards")` in `src/construct/capabilities/catalog.py:315-322`, handler `list_cards` in `src/construct/services/knowledge.py`. `knowledge ref list` was never implemented as a CLI command; instead `construct-synthesis/SKILL.md` was rewritten to read `refs/*.json` via the `Read` tool directly, with an explicit note in the skill body: "There is no `ref` sub-app on the CLI... use `Read`." Both halves of the decision are present and mechanically enforced (`test_card_list_cli_mcp.py`, `test_doc_command_references.py`). |
| 3 | `construct-synthesis/SKILL.md` no longer declares `WebSearch`/`WebFetch`, or `PROJECT.md` records a deliberate exception | ✓ VERIFIED | `construct-synthesis/SKILL.md` frontmatter `allowed-tools:` is now `Read, Bash(construct), MCP(connect)` — no `WebSearch`/`WebFetch`. `.planning/PROJECT.md:37` and `:53` record the closure of `spec-v04:436`. Mechanically enforced by `tests/contract/test_skill_migration.py::test_skill_drops_forbidden_tools[construct-synthesis]` (parses both frontmatter dialects, guarded against vacuity by `test_allowed_tools_text_is_not_vacuous`) — both pass in the full suite run. |
| 4 | A user can invoke `research search\|score\|run\|review\|inspect`, `curation run\|review\|inspect`, `daily run\|inspect`, `card evaluate` directly from `USER_GUIDE.md`; `commands.md` lists real commands | ✓ VERIFIED | Grepped `USER_GUIDE.md` directly: all eleven documented invocations present verbatim (`construct research run/search/score/review/inspect --workspace .`, `construct card evaluate --workspace .`, `construct curation run/review/inspect --workspace .`, `construct daily run/inspect --workspace .`). `commands.md` (154 lines, organised into 11 capability-group sections) is under `_DOC_GLOBS` and `_MUST_CARRY_INVOCATIONS`; `test_key_docs_are_not_vacuous[.../commands.md]` and `test_documented_commands_resolve[references/commands.md]` both pass. |
| 5 | Release-validation artifact runs end to end; `README.md`/`AGENTS.md` describe live surface by capability group, no command count, `test_doc_command_references.py` cited as authority | ✓ VERIFIED | `USER-TEST-PLAYBOOK-v03.md` is deleted (`git log` shows commit `f351a7e` superseding it); `USER-TEST-PLAYBOOK-v041.md` exists, is globbed, and passes non-vacuity + resolution tests. `AGENTS.md:285` enumerates CLI by capability group (`ask, bridge, card, curation, daily, ingest, knowledge, research, spike, tag, views, workflow` + top-level leaves) and states "The exact live surface is asserted mechanically by `tests/contract/test_doc_command_references.py` — treat that test as the authority, not any count written in prose." No numeric command count found anywhere in `README.md`/`AGENTS.md`/`.planning/ROADMAP.md`/`.planning/REQUIREMENTS.md` (`grep -rn "25-command|[0-9]+ commands\b"` returns only the accurate 67/32/30-invocation counts documented as test evidence, not a CLI-surface-size claim). `README.md`'s "Product lineage" section correctly shows `v0.4 shipped` / `v0.4.1 in flight` rows. Playbook offline sections were human-executed against a fresh test workspace (16-07 T3, recorded verbatim in `16-VALIDATION.md`), satisfying the "runs," not just "resolves," half of D-09. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/contract/test_doc_command_references.py` | `_KNOWN_BROKEN` empty, `_DOC_GLOBS` = 5 entries | ✓ VERIFIED | Confirmed by direct import: `len(_KNOWN_BROKEN)==0`, `len(_DOC_GLOBS)==5` |
| `tests/contract/test_skill_migration.py` | Multi-dialect frontmatter parser, construct-synthesis in scope | ✓ VERIFIED | `_MIGRATED_SKILLS` includes `construct-synthesis`; `_allowed_tools_text` handles list-style YAML |
| `src/construct/capabilities/catalog.py` | `knowledge.card.list` registry entry | ✓ VERIFIED | Lines 315-322: `id`, `cli_name`, `mcp_tool_name`, `handler=list_cards` all present |
| `src/construct/services/knowledge.py` | `list_cards` handler + `_json_safe` date coercion | ✓ VERIFIED | Present and exercised by `test_card_list_cli_mcp.py` |
| `src/construct/cli.py` | `knowledge card list` Typer leaf | ✓ VERIFIED | `--help` resolves, flags present: `--domain`, `--include-archived`, `--workspace`, `--json` |
| `CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md` | No WebSearch/WebFetch; `ref list` rewritten onto `Read` | ✓ VERIFIED | Frontmatter and body both confirmed |
| `CONSTRUCT-CLAUDE-impl/USER_GUIDE.md` | CLI-invocation column, all named commands present | ✓ VERIFIED | 11/11 grep hits |
| `CONSTRUCT-CLAUDE-impl/construct/references/commands.md` | Real commands listed | ✓ VERIFIED | 154 lines, 11 capability sections, non-vacuous per test |
| `USER-TEST-PLAYBOOK-v041.md` | Supersedes v03, offline sections executable | ✓ VERIFIED | v03 deleted, v041 present, globbed, human-executed |
| `README.md` / `AGENTS.md` | Lineage/CLI description accurate, no count, guard cited | ✓ VERIFIED | Confirmed by direct read + grep for stale count strings |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `catalog.py` capability record | `mcp/server.py` MCP tool list | registry auto-discovery | ✓ WIRED | `test_mcp_no_hardcoded_card_list` proves zero hand-written references to `list_cards`/`construct_list_cards` in `mcp/server.py`; `test_in_mcp_tool_list` / `test_mcp_server_exposes_card_list` prove auto-discovery works |
| `cli.py knowledge card list` | `services/knowledge.py list_cards` | direct handler call via registry `.handler(**kwargs)` | ✓ WIRED | `test_handler_accepts_workspace_keyword`, `test_cli_commands_present` both pass |
| `USER_GUIDE.md` / `commands.md` invocation strings | live Typer app | `_command_paths()` introspection in `test_doc_command_references.py` | ✓ WIRED | All 30 parametrized document cases pass `test_documented_commands_resolve` |
| `construct-synthesis/SKILL.md` refs-acquisition step | `Read` tool | direct instruction replacing `construct knowledge ref list` | ✓ WIRED | SKILL.md body explicitly instructs reading `refs/*.json` via `Read`; no `ref list` string remains anywhere in the doc set (confirmed absent from `_KNOWN_BROKEN` and from grep) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_KNOWN_BROKEN` is genuinely empty | `python -c "...len(t._KNOWN_BROKEN)"` | `0` | ✓ PASS |
| `_DOC_GLOBS` widened to 5 | `python -c "...len(t._DOC_GLOBS)"` | `5` | ✓ PASS |
| Full suite green at documented terminal state | `.venv/bin/python -m pytest -q -p no:cacheprovider` | `515 passed, 1 skipped, 0 failed` | ✓ PASS |
| `knowledge card list --help` resolves and shows documented flags | `python -m construct.cli knowledge card list --help` | exit 0, all 4 flags present | ✓ PASS |
| `construct-synthesis` allowed-tools carries no forbidden grant | direct file read | `Read, Bash(construct), MCP(connect)` | ✓ PASS |
| MCP failure-path serialization (review WR-01 reproduction) | `list_cards(workspace='/tmp/not-a-workspace-xyz')` → `_serialize_result` → `json.dumps` | `TypeError: Object of type OperationError is not JSON serializable` | ✗ FAIL — see Known Issues below |
| MCP boundary input-model enforcement (review WR-02 reproduction) | Read `mcp/server.py` `create_server()` | `capability.handler(**kwargs)` called directly; `capability.input_model` never instantiated | confirms WR-02 as described |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| FIX-03 | 16-01, 16-03, 16-04, 16-06, 16-07 | Every `construct ...` invocation resolves; `card list`/`ref list` decision made | ✓ SATISFIED | REQUIREMENTS.md final row: "Complete (16-06, re-confirmed 16-07)"; independently re-verified `_KNOWN_BROKEN==0`, suite green |
| DEC-01 | 16-01, 16-04 | `construct-synthesis` web-grant removal or documented exception | ✓ SATISFIED | REQUIREMENTS.md final row: "Complete — closed by 16-04"; independently confirmed frontmatter + PROJECT.md |
| DOC-04 | 16-02, 16-05, 16-06, 16-07 | User-doc set covers v0.4 runtime; playbook runs end to end | ✓ SATISFIED | REQUIREMENTS.md final row: "Complete — all four clauses evidenced"; independently confirmed all four clauses (a)-(d) |

No orphaned requirements found — REQUIREMENTS.md maps FIX-03, DEC-01, DOC-04 to Phase 16 exactly once each, and all three appear in at least one plan's `requirements:` frontmatter field.

**Requirement-status integrity check (explicitly requested by orchestrator):** `git log -p -- .planning/REQUIREMENTS.md` shows FIX-03 and DOC-04 were each marked Complete once ahead of their evidence and explicitly reverted:
- FIX-03: marked Complete by 16-03's premature commit, reverted to "Pending — `_KNOWN_BROKEN` holds 2 `workflow` entries; 16-06 closes" (commit `50d7b11`'s sibling revert), then genuinely closed by 16-06 and re-confirmed by 16-07 (widened `_DOC_GLOBS` 3→5 with allowlist still empty — the strongest form of the claim, since it cannot be an artifact of a narrowed scan).
- DOC-04: marked Complete prematurely, explicitly reverted by commit `50d7b11` ("docs(16): revert DOC-04 to Pending — marked complete ahead of its evidence"), then genuinely closed across 16-05/16-06/16-07.
- DEC-01: marked Pending until 16-04, then marked Complete once, matching its actual closure — no premature-then-reverted cycle for this one.

The **final** state in REQUIREMENTS.md (as read at verification time) is evidence-backed for all three: each Complete row cites the specific plan(s), test names, and mechanical signatures (`0 5` over 30 docs; `515 passed, 1 skipped, 0 failed`) that I independently reproduced above, not merely narrative claims.

### Anti-Patterns Found

None introduced by this phase. Scanned all phase-16-modified source files (`knowledge.py`, `catalog.py`, `cli.py`, `curation_run.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero hits. Scanned all phase-16-modified docs (`USER_GUIDE.md`, `commands.md`, `SKILL.md`, `README.md`, `AGENTS.md`, `USER-TEST-PLAYBOOK-v041.md`) — the only "placeholder" hits are legitimate uses describing angle-bracket argument tokens as placeholders for user substitution, not stub markers.

One pre-existing `TBD` was found at `AGENTS.md:294` ("Location: TBD — extend `views/` SPA, adopt CoPilotKit, or hybrid"). `git blame` traces it to commit `2b0ce43` (2026-06-08), well before Phase 16 started (2026-07-20) and unrelated to Phase 16's CLI/doc-truth scope (it documents an undecided Layer 4 UI-shell architecture question, not incomplete Phase 16 work). Not counted as a Phase 16 debt marker.

### Known Issues (from 16-REVIEW.md, independently reproduced)

Two Warnings from the code review were independently reproduced during this verification:

- **WR-01** — MCP failure path for `list_cards` cannot serialize its structured `OperationError`; `_serialize_result` → `json.dumps` raises `TypeError`, silently caught by the handler's blanket `except Exception` and replaced with a generic string. Reproduced directly (see Behavioral Spot-Checks table).
- **WR-02** — `CardListInput`'s `extra="forbid"` is never enforced at the MCP boundary because `create_server()`'s dispatch calls `capability.handler(**kwargs)` directly, never instantiating `capability.input_model`. Confirmed by reading `src/construct/mcp/server.py:30-38` — no `input_model` reference anywhere in the dispatch path.

**Judgement on whether these undermine Phase 16's success criteria:**

- **SC1 ("resolves against the live registry and runs")** is about documentation invocation strings resolving to a real Typer command path and the CLI happy path executing — a static/introspection contract plus a human-executed playbook. Neither WR-01 nor WR-02 touches this: the CLI command resolves and runs correctly; both defects are exclusively on the *MCP failure/validation path*, which is not what SC1 asserts.
- **SC2 ("card list implemented as a real command")** is satisfied at the level the roadmap actually specifies — a real, registry-routed, dual-surface command exists and is auto-discovered by MCP without server edits (`test_mcp_no_hardcoded_card_list`, `test_in_mcp_tool_list` pass). The phase's own SUMMARY oversold "CLI/MCP parity" as unconditional when it in fact only holds on the success path — that is a real overstatement, but the roadmap's SC2 wording does not require flawless error-path parity, only that the command exists and the `card list`/`ref list` decision was made and implemented.
- Both defects root-cause in **shared, unchanged infrastructure** (`src/construct/mcp/server.py` predates this phase) and are newly *reachable*, not newly *introduced*, by this phase's capability. The review classified both as WARNING (not BLOCKER, "not a crash, data-loss, or security-exploit path") — I concur with that severity assessment after independent reproduction.

**Conclusion:** WR-01/WR-02 are real, verified defects and should be tracked as follow-up work (fixing `_serialize_result` to recurse into dataclasses via `asdict`, and routing MCP dispatch through `capability.input_model` for validation/coercion — both fixes are already specified in 16-REVIEW.md). They do not block Phase 16's goal achievement because the phase's success criteria are about invocation-string resolution and command existence, not MCP error-boundary hardening, and the defects are not newly introduced by this phase's diff. Recommend opening a follow-up plan/issue for `src/construct/mcp/server.py` before any phase that expands MCP failure-path guarantees; not a blocker for closing Phase 16.

### Human Verification Required

None. The one human-dependent item required by this phase (D-09 part two — playbook offline sections execute end to end) was already completed and recorded during phase execution (16-07 T3, `16-VALIDATION.md` "Recorded result" section) with the user's direct confirmation ("i verified the playbook on a test space"), no failing steps, and no D-07 (offline-guarantee) violation. No new human verification is introduced by this report's findings — the WR-01/WR-02 follow-up is a developer/engineering decision (fix now vs. track as follow-up), not a UAT-style human check.

### Gaps Summary

No gaps. All 5 roadmap success criteria are independently verified against the live codebase (not merely SUMMARY claims): the mechanical test suite runs green at the exact documented terminal state (515 passed, 1 skipped, 0 failed), `_KNOWN_BROKEN` is genuinely empty, `_DOC_GLOBS` widened to 5, all three requirement IDs (FIX-03, DEC-01, DOC-04) are Complete in REQUIREMENTS.md with evidence-backed final rows (having survived an honest premature-completion-then-revert cycle during execution, which is itself a positive signal for rigor), and the two code-review Warnings are real but scoped to MCP error/validation-boundary infrastructure that predates this phase and does not undermine the phase's stated success criteria.

---

_Verified: 2026-07-25T14:05:22Z_
_Verifier: Claude (gsd-verifier)_
