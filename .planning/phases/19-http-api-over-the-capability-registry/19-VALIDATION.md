---
phase: 19
slug: http-api-over-the-capability-registry
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-02
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase` from `19-RESEARCH.md` § Validation Architecture.
> Task IDs are resolved by `/gsd-validate-phase` once PLAN.md files exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=[".","src"]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/contract -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~90 seconds (820 tests currently collected) |
| **Test client** | `starlette.testclient.TestClient` (via `fastapi.testclient`) — works on installed `httpx` 0.28.1 with a deprecation warning |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/contract -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest -q` (820 + new)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

Seeded at requirement granularity from research. `/gsd-validate-phase` resolves `TBD` task IDs
against the executed PLAN.md files; `Threat Ref` is populated from each plan's `<threat_model>`
block (security capability active — ASVS L1, block on `high`).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | HTTP-01 | — | Binds 127.0.0.1 only; never 0.0.0.0 | unit | `pytest tests/contract/test_http_surface.py::test_serve_binds_loopback_only -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-01 | — | Port collision → actionable message, exit 1 | integration | `pytest tests/contract/test_http_surface.py::test_port_collision_is_actionable -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-02 | — | Every registry capability reachable (cardinality) | contract | `pytest tests/contract/test_http_surface.py::test_every_registry_capability_is_reachable_over_http -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-02 | — | Coverage guard fails when a capability is dropped | contract (meta) | `pytest tests/contract/test_http_surface.py::test_coverage_guard_is_not_vacuous -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-03 | — | `workspace_id` resolves; `../../etc` rejected with **no filesystem effect** | contract | `pytest tests/contract/test_capability_seam.py -k workspace_id -x` | ⚠️ file exists (984 lines); new cases needed | ⬜ pending |
| TBD | TBD | TBD | HTTP-03 | — | HTTP can never emit a path-shaped key | contract | `pytest tests/contract/test_http_surface.py::test_http_payloads_carry_no_path_field -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-04 | — | Same reason + suggestion across CLI/MCP/HTTP | contract | `pytest tests/contract/test_surface_parity.py -x` | ❌ W0 (extends 18-03's table) | ⬜ pending |
| TBD | TBD | TBD | HTTP-04 | — | No abs path / no `Traceback` in **success or error** bodies | contract | `pytest tests/contract/test_surface_parity.py -k no_path_leak -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-05 | — | Foreign `Host` → 400; foreign `Origin` → 403; missing token → 401 | contract | `pytest tests/contract/test_http_security.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-05 | — | Rejection happens **before dispatch** (workspace byte-identical after) | contract | `pytest tests/contract/test_http_security.py::test_rejection_precedes_any_capability_effect -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-06 | — | Start returns id immediately; pollable while running | integration | `pytest tests/integration/test_http_runs.py::test_run_is_pollable_while_running -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-06 | — | Browser-started run resumable from CLI, and the reverse | integration | `pytest tests/integration/test_http_runs.py::test_cross_surface_resume -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-06 | — | Failed spawn surfaces stderr | integration | `pytest tests/integration/test_http_runs.py::test_failed_spawn_is_visible -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HTTP-07 | — | Listing includes paused runs **and daily receipts** (all three stores) | contract | `pytest tests/contract/test_workflow_list.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OQ-4 | — | WAL + `busy_timeout` pinned by assertion, not inherited | unit | `pytest tests/llm/test_checkpoint_concurrency.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-08 | — | `from_validation_error` rejects a missing `model` | unit | `pytest tests/contract/test_capability_seam.py -k from_validation_error -x` | ⚠️ file exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/contract/test_http_surface.py` — stubs for HTTP-01, HTTP-02, HTTP-03 (adapter side)
- [ ] `tests/contract/test_http_security.py` — stubs for HTTP-05, incl. the ordering assertion
- [ ] `tests/contract/test_surface_parity.py` — stubs for HTTP-04; extends 18-03's differential table
- [ ] `tests/contract/test_workflow_list.py` — stubs for HTTP-07, all three stores
- [ ] `tests/integration/test_http_runs.py` — stubs for HTTP-06, incl. cross-surface resume + spawn failure
- [ ] `tests/llm/test_checkpoint_concurrency.py` — OQ-4 pin (WAL + `busy_timeout`)
- [ ] `tests/conftest.py` (or phase-local `conftest.py`) — shared fixture: an app factory + `TestClient`
      with a known token and a temp install root holding ≥2 discoverable workspaces
- [ ] Framework install: **none** — pytest 9.0.3 present. Optional: `pip install httpx2` to clear
      the Starlette `TestClient` deprecation warning.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Result |
|----------|-------------|------------|-------------------|--------|
| Real browser reaches the served surface | HTTP-01 | `TestClient` bypasses the network stack — it never proves a real socket is bound to 127.0.0.1 and reachable from a browser process | Start the server with the one-command launcher, open `http://127.0.0.1:<port>` in a browser with the launch token, confirm a capability responds | ✅ **pass** (2026-08-06, 19-10) — loopback URL confirmed, 30 capabilities read from a browser console with `input_schema` populated, `workspace.status` invoked with the token and refused 401 without it |
| Token delivery ergonomics | HTTP-05 | Whether the operator can actually get the per-launch token into the browser is a UX judgement, not an assertion (research Open Question 1) | Launch, read the token from stdout / the `0600` file, use it from a browser request, confirm no token appears in shell history or a `Referer` | ✅ **pass** (2026-08-06, 19-10) — verdict recorded: **needs redesign**. Token file is `0600` and matches stdout, and no token reached a URL or shell history, but manual terminal→console transfer is not a basis for the served shell. Phase 21 must own delivery |

### ⚠️ Not exercised — assumption A3 remains open

The **cross-origin refusal** (`HOWTO-verify-phase-19.md` step 6) was not run. It is a third
manual-only behaviour that this table did not originally list, and nothing else can substitute for
it: `X-Construct-Token` is not CORS-safelisted, so the design relies on a browser preflighting a
drive-by request and no `CORSMiddleware` answering it. `TestClient` sends no `Origin` of its own and
`curl` does not implement CORS at all.

Consequence: **T-19-02 (drive-by CSRF, high) is mitigated by design and unproven as deployed.**
Carried into Phase 21 as an open item rather than counted in the pass above. One fetch from a browser
console on a foreign origin closes it.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** ✅ **passed 2026-08-06** — both manual-only rows resolved by the 19-10 human-verify
checkpoint (see `19-10-SUMMARY.md`), with the A3 cross-origin gap named above rather than folded into
the pass. Automated side: full suite **1126 passed, 18 skipped, 0 failed**.

> The frontmatter `status` / `nyquist_compliant` fields and the 16 `TBD` task IDs in the Per-Task
> Verification Map are deliberately untouched. `/gsd-validate-phase` §6 owns them and resolves the
> ids against the executed PLAN.md files; setting them by hand here would record a pass that nothing
> performed. This approval covers the manual rows only.
