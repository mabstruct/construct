---
phase: 14-durable-state-config-truth
plan: 04
subsystem: llm-config, ops-ui
tags: [FIX-02, D-10, D-11, refactor, streamlit]
requires:
  - src/construct/llm/config.py (load_llm_config, DEFAULT_CONFIG_PATH)
provides:
  - construct.llm.config.resolve_llm_config_path (public path resolver)
  - Streamlit sidebar read-only effective-config-path display
affects:
  - src/construct/ui/streamlit_app.py
tech-stack:
  added: []
  patterns:
    - "Public resolver extracted so UI and runtime share one code path (drift-proofing)"
    - "st.caption as the read-only display primitive for resolved paths"
key-files:
  created:
    - tests/unit/test_llm_config_resolution.py
  modified:
    - src/construct/llm/config.py
    - src/construct/ui/streamlit_app.py
decisions:
  - "resolve_llm_config_path extracted as a pure refactor (D-10/Q1 Option A) — no validation, caching, .resolve() or .expanduser() added"
  - "Sidebar LLM config path is a read-only st.caption, not a disabled input — an editable path wired to a loader would make the dashboard an arbitrary-file-read primitive"
  - "Provider override converted to a static caption per D-11; install_root left alone as out of scope"
metrics:
  duration: 14m
  completed: 2026-07-19
  tasks: 3
  files: 3
status: complete
---

# Phase 14 Plan 04: LLM Config Path Truth Summary

Extracted `resolve_llm_config_path()` from `load_llm_config` and pointed the Streamlit sidebar at it, so the ops UI displays the path the runtime actually reads instead of a stale literal.

## What Was Built

**`resolve_llm_config_path(config_path: Path | None = None) -> Path`** — new public function in
`src/construct/llm/config.py`. It is the resolution order that was previously inlined in
`load_llm_config`, moved unchanged: explicit argument, then `CONSTRUCT_LLM_CONFIG`, then
`DEFAULT_CONFIG_PATH`. It resolves only — it does not touch the filesystem, validate, or raise.
`load_llm_config` now delegates to it, so there is one implementation with two callers.

**`tests/unit/test_llm_config_resolution.py`** — 4 tests. `TestResolveLlmConfigPath` covers the three
precedence branches; `TestLoadLlmConfigDelegation` monkeypatches the resolver in the module namespace and
asserts `load_llm_config` routes through it. That last test is the regression guard that keeps the
extraction from decaying back into two parallel implementations.

**`src/construct/ui/streamlit_app.py`** — the editable "LLM config path" text input (which defaulted to
`.construct/model-routing.yaml`, a file the runtime never reads) is now a read-only `st.caption` showing
`resolve_llm_config_path()`. The "Provider override" selectbox is now a static caption. Both dead
session-state writes are gone.

## Key Decisions

- **The extraction is a pure refactor.** `load_llm_config`'s signature, docstring, existence check, and
  `FileNotFoundError` message are unchanged. Verified with `git diff -U0` on changed lines only: the
  resolution body, the `if not path.exists()` branch, and the error message appear as unmodified context.
- **Path only, never contents.** The sidebar renders the resolved path and nothing parsed from it.
  `LlmConfig` is structural today, but the same display pattern applied to `.construct/search.yaml` would
  surface `api_key_env` names — path-only is the boundary that stops that from being a natural next step.
  Acceptance asserts `load_llm_config(` never appears in the UI file.
- **Read-only is the security-correct choice, not just the scope-correct one.** The pre-existing free-text
  path field was inert and therefore harmless; "fixing" FIX-02 by wiring it to a real loader would have
  turned the ops dashboard into an arbitrary-file-read primitive (T-14-04-01).
- **The UI does not name the env var.** `CONSTRUCT_LLM_CONFIG` and `os.environ` appear nowhere in
  `streamlit_app.py` — re-stating the order there is the exact drift D-10 exists to close.

## Deviations from Plan

### 1. [Rule 3 — Blocking] Task 1's acceptance criteria were mutually unsatisfiable

**Found during:** Task 1 verification.

**Issue:** Task 1 required, simultaneously, that (a) the module collect 4 tests under
`pytest --collect-only -q`, and (b) the suite be RED *because the import of `resolve_llm_config_path`
fails* — a condition the plan states explicitly ("the import errors. That failure is the expected RED
state"). A module-level `ImportError` aborts collection, so pytest reports `no tests collected, 1 error`
and `grep -c '::'` returns 0, never 4. No correct implementation can satisfy both.

This is the same family of defect the orchestrator flagged from plan 14-01: a shell guard that cannot pass
for any correct edit.

**Resolution:** I did **not** distort the implementation to satisfy it. The available distortion — deferring
the imports into each test body so collection succeeds while tests fail — would have produced a
non-idiomatic module contradicting the plan's own `<read_first>` idiom (top-level absolute
`from construct...` imports, as used in `tests/llm/test_factory.py`), purely to satisfy a contradictory
guard. Instead I kept the idiomatic top-level import, verified every satisfiable Task 1 criterion
(non-zero exit, failure output naming `resolve_llm_config_path`, 4 test functions defined, `delenv`
present, `from __future__` present, `src/` untouched), and deferred the collect-count assertion to Task 2,
where it is meaningful. It passes there: collection reports exactly 4.

**Files modified:** none — this was a verification-procedure deviation, not a code change.

### 2. Comment wording constrained by Task 3's own acceptance criteria

Task 3's action text asks the inline comment to note that wiring the controls through to `load_llm_config`
is deferred to v0.5, but Task 3's acceptance asserts `grep -cE 'load_llm_config\('` returns 0 for that
file. The comment says "the LLM config loader" instead of naming the function with parentheses. Intent
preserved; no functional impact.

## Deferred Observations

- **`install_root` has the identical dead-write defect.** `st.session_state["install_root"]`
  (`streamlit_app.py`) is written and read nowhere — the same defect D-10/D-11 fixed for `llm_config` and
  `provider_override`. D-11 extended scope to exactly two controls and stopped there, so it was left
  untouched by design. Recorded here as the plan directs; a future phase should either wire or remove it.
- `st.session_state["workspace_path"]` **is** read (`dashboard.py:86`, `gate_review.py:71`) and was
  correctly left alone.

## Verification

| Check | Result |
|---|---|
| Criterion 3a — `model-routing` literal gone from the UI | pass (0 occurrences) |
| Criterion 3b — UI resolves via `llm/config.py` | pass |
| Criterion 3c — no editable path control | pass (0 occurrences) |
| Criterion 3d — `CONSTRUCT_LLM_CONFIG=/tmp/x.yaml` honored end-to-end | pass |
| Criterion 3e — resolution order unchanged for real loads | pass |
| Criterion 5a — full suite | **443 passed** (439 baseline + 4) |
| Criterion 5b — `_KNOWN_BROKEN` | 5 entries, unchanged |
| Scope guard — `schemas/`, `storage/`, `services/` untouched | pass (clean) |
| Idempotence — `r() == r()`, no writes, no module state | pass |

## Human Check Outstanding

No test in the repository imports Streamlit, so the render-level change has no assertable return value.
Still to confirm manually:
1. `streamlit run src/construct/ui/streamlit_app.py` — sidebar shows the path as static text with no edit
   affordance, ending in `src/construct/llm/config.yaml`.
2. `CONSTRUCT_LLM_CONFIG=/tmp/x.yaml streamlit run src/construct/ui/streamlit_app.py` — displayed path
   changes to `/tmp/x.yaml`.
3. Provider override renders read-only, not as a dropdown.
4. No provider names, gate settings, or file contents appear in the sidebar — path only.

The resolver half is verified programmatically (criterion 3d above), so what remains is strictly the
Streamlit render.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `f98c991` | test(14-04): failing tests for resolve_llm_config_path |
| 2 | `334ec62` | refactor(14-04): extract resolve_llm_config_path |
| 3 | `bb21b60` | fix(14-04): show effective LLM config path in ops sidebar |

## Self-Check: PASSED

- `src/construct/llm/config.py` — FOUND
- `src/construct/ui/streamlit_app.py` — FOUND
- `tests/unit/test_llm_config_resolution.py` — FOUND
- Commits `f98c991`, `334ec62`, `bb21b60` — all FOUND in `git log`
