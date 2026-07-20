---
phase: 15-views-generate-data-resolution
verified: 2026-07-20T08:55:50Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "`construct views generate --install-root <root> --json` no longer crashes with an unhandled TypeError; it now emits parseable JSON and exits 0."
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 15: views.generate_data Resolution Verification Report

**Phase Goal:** A user or agent invoking `views.generate_data` over CLI or MCP gets real generated view data or an honest, documented absence — never a permanent-failure stub.
**Verified:** 2026-07-20T08:55:50Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit `b296ff0`)

## Goal Achievement

### Gap Closure Verification (this pass's focus)

The single prior gap — `construct views generate --install-root <root> --json` raising an
unhandled `TypeError` — is **confirmed closed**.

**Root cause, confirmed still present and correctly worked around:** `src/construct/cli.py`
defines two module-level Typer commands named `list` (`spike_app`'s at line 1054, `tag_app`'s at
line 1219). Per Python name resolution, any bare `list(...)` call inside the module resolves at
*call time* against the module's global namespace, so it picks up the later-defined command
function, not the builtin. Confirmed via `grep -n "^def list" src/construct/cli.py` → two hits.

**Fix, verified directly against the live file (not just the SUMMARY's description):**

```python
# cli.py:905-909
# List literals, not `list(...)`: the `tag list` command below shadows
# the builtin in this module's globals, so a bare `list()` call here
# resolves to that Typer command and raises.
"validation_errors": [*report.validation_errors],
"warnings": [*report.warnings],
```

Both call sites use list-literal unpacking (`[*iterable]`), which never performs a name lookup
against `list`, eliminating the collision. `grep -n "\blist(" src/construct/cli.py` confirms no
other bare `list(...)` call remains in the module outside the two `def list(` declarations and
the explanatory comment.

**Live re-verification (fresh scratch install root, not reusing a warm build):**

```
$ construct views generate --install-root <root> --json
{
  "success": true,
  "build_id": "b4003c61",
  "total_files_written": 11,
  "validation_errors": [],
  "warnings": []
}
$ echo $?
0
```

Parseable JSON, `success: true`, real file count, exit 0 — matches the SUMMARY's claim exactly.
(A same-root second invocation reports `total_files_written: 0` because generation is
content-addressed and idempotent — nothing changed to rewrite. This is pre-existing generator
behavior, not a regression from this fix.)

**Regression test, independently mutation-checked by this verifier (not just trusted from the
SUMMARY):** `tests/integration/test_views_generate.py::test_views_generate_json_flag_emits_parseable_json`.
I reverted the two fixed lines back to the original `list(...)` calls, re-ran the test, and it
failed with the exact original defect signature:

```
AssertionError: assert 1 == 0
 +  where 1 = <Result TypeError("argument should be a str or an os.PathLike object
     where __fspath__ returns a str, not 'OptionInfo'")>.exit_code
```

Restored the fix (`git checkout -- src/construct/cli.py`), re-ran — test passes. The test is a
genuine regression guard, not a tautology.

**Full suite:** `.venv/bin/python -m pytest -q` → **489 passed**, 2 warnings (pre-existing,
unrelated Pydantic collection warnings), 0 failures. One net new test versus the prior pass's 488,
matching the regression test added.

**No new anti-patterns introduced by the fix.** The diff touches exactly two lines plus a
3-line explanatory comment; no debt markers, no new stubs, no scope creep.

### Observable Truths (ROADMAP Success Criteria) — re-confirmed

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | No permanent-failure handler for `views.generate_data` remains in `capabilities/catalog.py` | ✓ VERIFIED | `grep -n "Not yet implemented" src/construct/capabilities/catalog.py` — no match. Unaffected by this fix (different file); re-confirmed by direct grep this pass. |
| 2 | `("views", "generate")` is deleted from `_KNOWN_BROKEN` and the paired assertion no longer covers it | ✓ VERIFIED | `_KNOWN_BROKEN` still holds exactly the same 4 non-views entries (`knowledge card list`, `knowledge ref list`, `workflow run`, `workflow resume`), re-confirmed by direct read of `tests/contract/test_doc_command_references.py:151-156` this pass. |
| 3 | `install_root`/`workspace` contract and skill-directory import coupling each have an explicit recorded decision | ✓ VERIFIED | `CONSTRUCT-CLAUDE-spec/adrs/adr-0005-views-refresh-ownership.md` still present (17,493 bytes), unaffected by this fix. |
| 4 | Daily cycle's post-run views refresh produces data or an honest, actionable skip; remediation message never names a nonexistent command | ✓ VERIFIED | `curation_run.py:1015` and `:1049` both still emit `"run 'construct views generate' manually to refresh the views."` — and that command now works correctly in **both** its plain and `--json` forms (the fix strengthens this criterion: previously the remediation was accurate only for the plain form). |
| 5 | Full pytest suite green, no new `_KNOWN_BROKEN` entries, bounded RT-01/RT-02 scope | ✓ VERIFIED | 489 passed (was 488; +1 for the new regression test), 0 failures. `_KNOWN_BROKEN` count unchanged at 4. `lambda **kwargs` survivor count unchanged at 2 (`help.suggest`, `bridge.detect`), confirming the views group was still not migrated into the registry pattern. |

**Score:** 5/5 ROADMAP success criteria verified, plus the below-criteria gap now closed = 6/6.

### Sub-Criterion (below ROADMAP level, from prior gap)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | `construct views generate --install-root <root> --json` runs the generator and exits 0 with parseable JSON — no unhandled crash | ✓ VERIFIED | See Gap Closure Verification above: live re-run, mutation-checked regression test, full suite green. |

### Required Artifacts (delta only — full artifact table unchanged from prior pass, all still verified)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/construct/cli.py` | `construct views generate --install-root [--json]` command | ✓ VERIFIED | Both plain and `--json` forms now confirmed exit 0 with correct output. Upgraded from prior pass's ⚠️ PARTIAL. |

All other artifacts from the prior VERIFICATION.md pass (views/lib modules, models.py, catalog.py
handler, refresh.py, ADR-0005, the CLI-wrapper skill) are unaffected by this commit — re-spot-checked
by grep this pass, no regressions found (see Anti-Patterns section).

### Key Link Verification (delta only)

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `construct views generate --json` CLI | JSON stdout payload | `json.dumps({...})` at cli.py:901-910 | ✓ WIRED | Previously ⚠️ BROKEN — the dict-literal construction itself was always correct; only the two `list(...)` values inside it resolved to the wrong callable. Now fully wired and correct. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `construct views generate --install-root <root> --json` (fresh root) | Live CLI invocation | Exit 0, parseable JSON, `success: true`, 11 files written | ✓ PASS (was ✗ FAIL) |
| Regression test exists and is genuine (not tautological) | Mutation check: revert fix, re-run, restore, re-run | Fails on reverted code with the exact original TypeError, passes on fixed code | ✓ PASS |
| Full suite | `.venv/bin/python -m pytest -q` | 489 passed, 0 failed | ✓ PASS |
| No other bare-builtin/module-command-name collisions remain reachable | `grep -n "\blist(" src/construct/cli.py` + manual check of `validate(`/`status(` bare calls | Only the two fixed sites existed; no other bare calls to `validate(`/`status(` found anywhere in the module or imported elsewhere | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FIX-01 | 15-01..15-05 (fix commit `b296ff0` closes the residual gap) | Real `views.generate_data`, no permanent-failure stub, consistent 4-caller contract, including the CLI `--json` output mode | ✓ SATISFIED | All 5 ROADMAP criteria plus the sub-criterion now verified with no caveats. |

### Anti-Patterns Found

None new. The fix commit (`b296ff0`) touches only `src/construct/cli.py:905-909` (2 code lines +
3 comment lines) and adds one test. No debt markers, no new stubs, no scope creep.

**Re-triage note on IN-02 (carried forward from prior pass):** The code review's IN-02 finding
literally names the `validate`/`status` shadowing pairs (`cli.py:82 vs :909`, `:100 vs :213`) —
it does not literally name the `list`/`list` pair that actually crashed. The crash was the *same
class* of defect (module-level Typer command shadowing a name used elsewhere in the module) but a
different specific instance the review did not enumerate. This verifier checked whether the
`validate`/`status` shadowing IN-02 does name carries the same live-crash risk: `grep`-confirmed
there is no bare `validate(...)` or `status(...)` call anywhere in `cli.py`, and no other module
imports `validate`/`status`/`list` from `construct.cli`. So the remaining IN-02 instances are
genuinely cosmetic (silent re-export only — `from construct.cli import validate` would silently
get the wrong function, but nothing in the codebase does that import). IN-01 (dead test helper),
IN-03 (redundant import), and IN-04 (missing re-export) are unrelated defect shapes with no
bare-call collision mechanism — none carry latent crash risk of this kind. No further action
required for this phase; IN-02's remaining instances can stay deferred as originally triaged.

### Known Open Items (unchanged, still deliberate, still assessed as not compromising the goal)

1. `views validate` rejects 3/8 files `views generate` writes — pinned by
   `test_views_validate_does_not_yet_accept_generated_bytes` (still present and passing in the
   489-test suite), escalated as a Phase 16/17 contract question. Does not affect the CLI/MCP
   generation path this phase's goal is about.
2. Per-card edit refresh path removed with the debounced hook — filed as v0.6 candidate, orthogonal
   to `views.generate_data` invocation.
3. `decay_scan` stale reason at `curation_run.py:417` — different node, out of scope.
4. IN-01/IN-03/IN-04 — cosmetic, reassessed above, no latent crash risk found.

## Gaps Summary

None. The single gap from the prior verification pass is closed, confirmed via live re-invocation,
an independently mutation-checked regression test, and a clean full-suite run. All 5 ROADMAP
success criteria hold, and the phase goal — "real generated view data or an honest, documented
absence — never a permanent-failure stub" — now holds across every caller surface this phase
touches: MCP handler, plain CLI, `--json` CLI, and the CLI-wrapper skill.

---

_Verified: 2026-07-20T08:55:50Z_
_Verifier: Claude (gsd-verifier)_
