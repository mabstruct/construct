---
phase: 16
slug: invocation-user-doc-truth
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-20
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `16-RESEARCH.md` § Validation Architecture. Per-task rows are filled by the planner.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `.venv`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/contract/test_doc_command_references.py tests/contract/test_skill_migration.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~0.5s quick / ~8.6s full |
| **Baseline** | **489 passed, 2 warnings** [VERIFIED — note STATE.md:11 and REQUIREMENTS.md:11 both still assert 439; stale] |

> **Interpreter note:** bare `python` fails under pyenv in this repo. All commands MUST use `.venv/bin/python`.

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/contract/test_doc_command_references.py tests/contract/test_skill_migration.py -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green at ≥ 489 tests
- **Max feedback latency:** ~9 seconds (full suite)

### Sampling strategy note (why this phase is different)

The doc guard is **exhaustive, not sampled** — it enumerates every `construct ...` string in every globbed doc and resolves each against the live Typer app. The Nyquist question is therefore not *"how often do we sample the docs"* but **"how often do we sample the guard's own adequacy."** The guard has two demonstrated ways to go silently vacuous (RESEARCH Pitfalls 2 and 4), so the minimum validation set must include tests that fail when the guard stops looking.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _pending — filled by planner_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → test map (from research)

| Req | Behavior | Test Type | Automated Command | Exists? |
|---|---|---|---|---|
| FIX-03 | `_KNOWN_BROKEN` is empty | contract | `pytest tests/contract/test_doc_command_references.py -q` | ✅ |
| FIX-03 | Every string in every globbed doc resolves | contract | `pytest -k test_documented_commands_resolve` | ✅ |
| FIX-03 | `knowledge card list` resolves | contract | `pytest -k test_command_surface_is_discoverable` | ⚠️ extend |
| FIX-03 | `card list` returns frontmatter, no bodies (D-02) | unit | `pytest tests/unit/ -k card_list_excludes_body` | ❌ W0 |
| FIX-03 | `card list --json` emits ISO dates | unit | `pytest tests/unit/ -k card_list_json_serializable` | ❌ W0 |
| FIX-03 | `card list` reaches CLI **and** MCP (parity) | contract | `pytest tests/contract/ -k card_list_cli_mcp` | ❌ W0 |
| DOC-04 | `USER_GUIDE.md` / `commands.md` are scanned | contract | `pytest -k test_documented_commands_resolve` | ⚠️ glob ext |
| DOC-04 | **Each newly-globbed doc yields ≥1 invocation** | contract | `pytest -k test_key_docs_are_not_vacuous` | ❌ **W0 — highest value** |
| DOC-04 | v0.4.1 playbook remains globbed | contract | `pytest -k test_documented_commands_resolve` | ⚠️ glob path |
| DOC-04 | Playbook offline sections execute (D-09) | manual | human run vs fresh smoke workspace | ❌ manual |
| DEC-01 | synthesis declares no `WebSearch`/`WebFetch` | contract | `pytest tests/contract/test_skill_migration.py -q` | ⚠️ scope + parser |
| DEC-01 | synthesis still delegates via `Bash(construct)` | contract | same | ⚠️ same |

---

## Wave 0 Requirements

- [ ] Per-doc non-vacuity test in `tests/contract/test_doc_command_references.py` — DOC-04 *(must go RED before the `_DOC_GLOBS` extension lands)*
- [ ] Multi-line frontmatter parser in `tests/contract/test_skill_migration.py::_allowed_tools_line()` — DEC-01 *(must go RED before synthesis joins `_MIGRATED_SKILLS`)*
- [ ] `card list` body-exclusion unit test — FIX-03 / D-02
- [ ] `card list` JSON date-serialization unit test — FIX-03
- [ ] `card list` CLI/MCP parity contract test — FIX-03 / D-01
- [ ] Extend `test_command_surface_is_discoverable` with `("knowledge","card","list")`

*Framework install: none needed — pytest present, 489 tests green.*

---

## Observable Signals

| Signal | Where | Meaning |
|---|---|---|
| `_KNOWN_BROKEN == {}` | source-visible | FIX-03's mechanical criterion (REQUIREMENTS.md:89) |
| `test_known_broken_entries_are_still_broken` → 0 params | pytest output | Allowlist genuinely empty, not bypassed |
| Per-doc parametrized case count | pytest `-v` IDs | Reveals glob set changes; a **dropped** doc ID is the D-16 red flag |
| Per-doc invocation count ≥ 1 | new Wave 0 test | Guard is actually looking |
| Full suite ≥ 489 | `pytest -q` | No collateral regression |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Playbook offline sections execute end to end | DOC-04 / D-09 | Playbook is a human release-validation artifact; its value is a human confirming each step runs | Run every offline step of the superseding playbook against a fresh smoke workspace; each step must execute without error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
