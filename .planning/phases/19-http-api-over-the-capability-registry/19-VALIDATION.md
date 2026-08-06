---
phase: 19
slug: http-api-over-the-capability-registry
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-02
validated: 2026-08-06
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
| **Estimated runtime** | ~45 seconds (1126 tests collected as of 2026-08-06; 820 at seeding) |
| **Test client** | `starlette.testclient.TestClient` (via `fastapi.testclient`) — works on installed `httpx` 0.28.1 with a deprecation warning |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/contract -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest -q` (1126 passed, 18 skipped at phase close)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

Task IDs resolved 2026-08-06 against the 10 executed PLAN.md files. `Threat Ref` populated from
each plan's `<threat_model>` block (security capability active — ASVS L1, block on `high`).

**Every row's `Automated Command` was executed on 2026-08-06 and its result recorded — no status
below is inferred from a file existing.** Where the seeded test name differs from the delivered one,
the row carries the delivered name and the drift is noted under the table; a seeded name is a
prediction from research, and silently keeping it would make the map unrunnable.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01/T2 | 19-01 | 1 | HTTP-01 | T-19-11 (high) | Binds 127.0.0.1 only; never 0.0.0.0 | unit | `pytest tests/contract/test_http_surface.py::test_the_bind_address_is_the_loopback_constant` | ✅ | ✅ green (1 passed) |
| 19-01/T2 | 19-01 | 1 | HTTP-01 | — (D-04 operability) | Port collision → actionable message, exit 1, before uvicorn takes over | integration | `pytest tests/contract/test_http_surface.py::test_a_busy_port_exits_one_with_actionable_guidance` | ✅ | ✅ green (1 passed) |
| 19-05/T1 | 19-05 | 2 | HTTP-02 | T-19-19 (medium) | Every registry capability reachable (cardinality, not membership) | contract | `pytest tests/contract/test_http_surface.py::test_every_registered_capability_is_reachable_over_http` | ✅ | ✅ green (1 passed) |
| 19-05/T2 | 19-05 | 2 | HTTP-02 | T-19-19 (medium) | Coverage guard fails when a capability is dropped or unreachable | contract (meta) | `pytest tests/contract/test_http_surface.py -k "coverage_guard or would_notice or never_answers_with_an_empty_list"` | ✅ | ✅ green (3 passed) |
| 19-04/T2 | 19-04 | 2 | HTTP-03 | T-19-03, T-19-04, T-19-17 (high), T-19-18 | `workspace_id` resolves and arrives as the declared type; `../../etc` rejected with **no filesystem effect**; `install_root` never client-supplied | contract | `pytest tests/contract/test_capability_seam.py -k "workspace_id or install_root"` | ✅ | ✅ green (93 passed) |
| 19-05/T2 | 19-05 | 2 | HTTP-03 | T-19-03, T-19-17 (high) | HTTP can never accept or emit a path-shaped key | contract | `pytest tests/contract/test_http_surface.py -k "path_shaped or filesystem_path"` | ✅ | ✅ green (37 passed) |
| 19-07/T2 | 19-07 | 3 | HTTP-04 | T-19-16 (high), T-19-22 | Same reason + suggestion across CLI/MCP/HTTP, byte-identical | contract | `pytest tests/integration/test_surface_parity.py` | ✅ | ✅ green (27 passed) |
| 19-03/T2 · 19-10 | 19-03, 19-07, 19-10 | 1, 3, 5 | HTTP-04 | T-19-05, T-19-06, T-19-15 | No abs path / no `Traceback` in **success or error** bodies — asserted per-surface *and* swept over every invocable capability | contract | `pytest tests/contract/test_result_boundary.py tests/integration/test_surface_parity.py -k "successful or sweep or leaks_the_environment"` | ✅ | ✅ green (5 passed) |
| 19-06/T1 | 19-06 | 2 | HTTP-05 | T-19-01, T-19-12, T-19-07, T-19-02 (high) | Foreign `Host` → 400; foreign `Origin` → 403; missing/wrong token → 401; comparison constant-time | contract | `pytest tests/contract/test_http_security.py` | ✅ | ✅ green (37 passed) |
| 19-06/T2 | 19-06 | 2 | HTTP-05 | T-19-21 (high) | Rejection happens **before dispatch** — workspace byte-identical after a refused write | contract | `pytest tests/contract/test_http_security.py -k "byte_identical or order_host_origin_token or before_the_seam"` | ✅ | ✅ green (subset of the 37 above) |
| 19-09/T1,T2 | 19-09 | 4 | HTTP-06 | T-19-09 (high), T-19-25 (high) | Start returns an id before the workflow begins; pollable while running through the ordinary envelope | integration | `pytest tests/integration/test_http_runs.py -k "answers_with_an_id or pollable"` | ✅ | ✅ green (18 passed for the file) |
| 19-09/T2 | 19-09 | 4 | HTTP-06 | T-19-26 (high), T-19-13 | Browser-started run resumable from CLI, and the reverse — asserted on the cards on disk | integration | `pytest tests/integration/test_http_runs.py -k resumed` | ✅ | ✅ green (subset of the 18) |
| 19-09/T1,T2 | 19-09 | 4 | HTTP-06 | T-19-05 (medium) | Failed spawn is visible: both child streams captured at the advertised relative path | integration | `pytest tests/integration/test_http_runs.py -k "readable_trace or fail_in_the_log or names_the_log"` | ✅ | ✅ green (subset of the 18) |
| 19-08/T1,T2 | 19-08 | 3 | HTTP-07 | T-19-23 (high), T-19-05 | Listing spans all three durable stores — paused runs **and daily receipts** — and never uses the library checkpoint listing | contract | `pytest tests/contract/test_workflow_list.py` | ✅ | ✅ green (20 passed) |
| 19-02/T1 | 19-02 | 1 | OQ-4 | T-19-13, T-19-14 | WAL + `busy_timeout` pinned by assertion on both checkpointers, not inherited | unit | `pytest tests/llm/test_checkpoint_concurrency.py` | ✅ | ✅ green (9 passed) |
| 19-07/T1 | 19-07 | 3 | D-08 | T-19-16 (high) | `from_validation_error` rejects a missing `model` | unit | `pytest tests/integration/test_surface_parity.py -k from_validation_error` | ✅ | ✅ green (1 passed) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Name and location drift between seeding and delivery

Four seeded rows named tests that were never written under those names. The map carries the delivered
names; recorded here so the drift is visible rather than looking like the plan was followed exactly:

| Seeded | Delivered | Note |
|--------|-----------|------|
| `test_serve_binds_loopback_only` | `test_the_bind_address_is_the_loopback_constant` | same behaviour |
| `test_http_payloads_carry_no_path_field` | `test_every_path_shaped_key_is_refused_by_the_envelope`, `test_no_capability_accepts_a_filesystem_path_over_http`, `test_a_path_shaped_key_beside_the_id_is_refused` | one seeded row became three delivered assertions, covering the inbound direction the seeded name did not describe |
| `test_rejection_precedes_any_capability_effect` | `test_a_refused_write_leaves_the_tree_byte_identical` (+ `test_the_checks_run_in_the_order_host_origin_token`) | the delivered form asserts the filesystem, not the ordering alone |
| `tests/contract/test_surface_parity.py`, `test_capability_seam.py -k from_validation_error` | `tests/integration/test_surface_parity.py` | the differential harness lives with the other cross-surface tests, not under `contract/` |

### Threats deliberately not in the map

`T-19-10` (unbounded run spawning / concurrent writers), `T-19-20` (advertised JSON Schemas) and
`T-19-24` (listing cost on a workspace with many runs) are all severity **low** with disposition
**accept** in their plans' threat models. They carry no row here because nothing was built to
mitigate them — recorded so their absence reads as a decision rather than as an oversight.

---

## Wave 0 Requirements

All delivered. `wave_0_complete: true` set 2026-08-06.

- [x] `tests/contract/test_http_surface.py` — stubs for HTTP-01, HTTP-02, HTTP-03 (adapter side)
- [x] `tests/contract/test_http_security.py` — stubs for HTTP-05, incl. the ordering assertion
- [x] `tests/contract/test_surface_parity.py` — stubs for HTTP-04; extends 18-03's differential table
- [x] `tests/contract/test_workflow_list.py` — stubs for HTTP-07, all three stores
- [x] `tests/integration/test_http_runs.py` — stubs for HTTP-06, incl. cross-surface resume + spawn failure
- [x] `tests/llm/test_checkpoint_concurrency.py` — OQ-4 pin (WAL + `busy_timeout`)
- [x] `tests/conftest.py` (or phase-local `conftest.py`) — shared fixture: an app factory + `TestClient`
      with a known token and a temp install root holding ≥2 discoverable workspaces
- [x] Framework install: **none** — pytest 9.0.3 present. Optional: `pip install httpx2` to clear
      the Starlette `TestClient` deprecation warning.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Result |
|----------|-------------|------------|-------------------|--------|
| Real browser reaches the served surface | HTTP-01 | `TestClient` bypasses the network stack — it never proves a real socket is bound to 127.0.0.1 and reachable from a browser process | Start the server with the one-command launcher, open `http://127.0.0.1:<port>` in a browser with the launch token, confirm a capability responds | ✅ **pass** (2026-08-06, 19-10) — loopback URL confirmed, 30 capabilities read from a browser console with `input_schema` populated, `workspace.status` invoked with the token and refused 401 without it |
| Token delivery ergonomics | HTTP-05 | Whether the operator can actually get the per-launch token into the browser is a UX judgement, not an assertion (research Open Question 1) | Launch, read the token from stdout / the `0600` file, use it from a browser request, confirm no token appears in shell history or a `Referer` | ✅ **pass** (2026-08-06, 19-10) — verdict recorded: **needs redesign**. Token file is `0600` and matches stdout, and no token reached a URL or shell history, but manual terminal→console transfer is not a basis for the served shell. Phase 21 must own delivery |

### Third manual-only row, discovered during execution — the cross-origin refusal

| Behavior | Requirement | Why Manual | Test Instructions | Result |
|----------|-------------|------------|-------------------|--------|
| A cross-origin page carrying the token is refused | HTTP-05 | `X-Construct-Token` is not CORS-safelisted, so the design relies on a browser preflighting a drive-by request and no `CORSMiddleware` answering it. `TestClient` sends no `Origin` of its own and `curl` does not implement CORS at all — **only a real browser enforces it** | From a console on a foreign origin, fetch `/api/capabilities` with a valid token header (`HOWTO-verify-phase-19.md` step 6) | ✅ **pass** (2026-08-06, 19-10) — blocked by the browser, no response body. **T-19-02 (drive-by CSRF, high) is now mitigated by measurement, not by design argument** |

This row was not in the original table; it was identified during 19-10 and closed in the same
checkpoint. Note what remains uncoverable: adding a `CORSMiddleware` to the stack would turn this
refusal into a capability list, and no automated test can notice, because nothing in the suite
implements CORS. It belongs in Phase 21's threat model rather than in a test that cannot exist.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s — full suite measured at ~45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ✅ **passed 2026-08-06** — all three manual-only rows resolved by the 19-10 human-verify
checkpoint (see `19-10-SUMMARY.md`), including the cross-origin refusal that verifies assumption A3.
Automated side: full suite **1126 passed, 18 skipped, 0 failed**.

> The frontmatter `status` / `nyquist_compliant` fields and the 16 `TBD` task IDs in the Per-Task
> Verification Map are deliberately untouched. `/gsd-validate-phase` §6 owns them and resolves the
> ids against the executed PLAN.md files; setting them by hand here would record a pass that nothing
> performed. This approval covers the manual rows only.

---

## Validation Audit 2026-08-06

| Metric | Count |
|--------|-------|
| Requirement rows audited | 16 |
| COVERED | 16 |
| PARTIAL | 0 |
| MISSING | 0 |
| Gaps found | 0 |
| Resolved | 0 (none to resolve) |
| Escalated | 0 |
| Rows whose seeded test name or path drifted | 4 (retargeted, not regenerated) |
| Manual-only rows | 3 (all passed at the 19-10 checkpoint) |

**Method.** Task IDs resolved against the 10 executed PLAN.md files; each row cross-referenced to the
delivered test through the `coverage:` blocks in the nine plan SUMMARYs; then **every command in the
map was run** and its result recorded in the Status column. No auditor subagent was spawned, because
gap analysis found nothing to fill — 16 of 16 requirements already carry a green automated assertion.

**What this audit did not do.** It checked that each requirement has a passing test targeting the
named behaviour. It did not re-derive whether the behaviour is the right one — that is the phase's own
verification, and the three high-severity threats it rests on were exercised by hand at the 19-10
checkpoint (loopback reachability, token exposure, cross-origin refusal) precisely because no test
client can reach them.

**Nyquist verdict: COMPLIANT.** Every requirement in the phase (HTTP-01…HTTP-07, plus OQ-4 and D-08)
has automated verification well inside the 90-second latency budget, and the three behaviours that are
structurally unautomatable are recorded as manual-only rows with dated passes rather than left
implicit.
