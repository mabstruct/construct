---
phase: 11
slug: curation-pipe-steps
status: secured
threats_open: 0
threats_closed: 9
asvs_level: 2
created: 2026-06-29
---

# Security Audit — Phase 11: curation-pipe-steps

**Audited:** 2026-06-29
**ASVS Level:** default (L1/L2)
**Disposition:** SECURED — 9/9 threats closed
**Mode:** Verification only (threat register authored at plan time; no new-threat scan)

The threat register was split across the three plan files (11-01/02/03 `<threat_model>`
blocks). All threats below were verified against the implemented code and the passing
test suite — not against documentation or intent.

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-11-01 | Tampering (run_id → thread_id / checkpoint path) | mitigate | CLOSED | `_validate_run_id` enforces `KEBAB_CASE_PATTERN.fullmatch` (curation_run.py:53-66); bound as `field_validator("run_id")` on `CurationRunInput` (curation_run.py:100) and `CurationInspectInput` (curation_run.py:110); both models `model_config = {"extra": "forbid"}` (curation_run.py:96, 106). Shims construct these models from kwargs so the validator fires at the invoke boundary (catalog.py:601, 610). |
| T-11-02 | Denial of Service (per-node robustness) | mitigate | CLOSED | All five real nodes wrap their body in `try/except Exception` → `_failed_step(...)` with `status="failed"` (integrity_check:294, decay_scan:340, orphan_scan:390, connection_maintenance:420, compile_report:443). `_aggregate_status` (curation_run.py:503-511) rolls a failed required step up to `degraded` (honest, not a crash or false-completed). Verified by `test_run_status_degraded_on_step_failure` (PASS). |
| T-11-03 | Tampering — transport (stdout contamination of MCP JSON-RPC) | mitigate | CLOSED | Module logs via `logger = logging.getLogger(__name__)` (curation_run.py:50) to stderr only. `grep -E "print\("` over curation_run.py → no match (stdout reserved for JSON-RPC). |
| T-11-04 | Tampering (canonical SOT write — D-06) | mitigate | CLOSED | No node writes cards/refs/connections.json/search-seeds.json. `decay_scan` reports `auto_archive_on_decay` and notes "archiving deferred to Phase 12" but appends only `candidate_ids` — no lifecycle mutation (curation_run.py:299-342). `connection_maintenance` writes only derived `log/`+`views/` via `bridge_detect` (curation_run.py:395-422). Verified by `test_no_canonical_writes` and `test_auto_archive_reported_not_acted` (both PASS). |
| T-11-05 | Spoofing (positional injection via dual-mode shim) | mitigate | CLOSED | `_curation_run_shim` (catalog.py:596-602) and `_curation_inspect_shim` (catalog.py:605-611) raise `TypeError` when `args` is non-empty (keyword-only). Verified by `test_shims_reject_positional_args` (PASS). |
| T-11-PL | Spoofing (fake-success / placeholder regression) | mitigate | CLOSED | Real steps emit concrete primitive findings (counts + candidate_ids); `test_steps_return_concrete_findings` asserts no `"placeholder"` substring in summary/reason and a non-empty findings dict for every real step (PASS). |
| T-11-06 | Information Disclosure (provider error text if L3 runs) | accept | CLOSED | Accepted-risk rationale holds in code: `connection_maintenance` wraps `bridge_detect` in `try/except` (curation_run.py:420), and any node failure is reduced by `_sanitize_error` to class-name + first line only (curation_run.py:222-231) — no multi-line/raw provider text leak. L3 auto-skips offline; no new secret introduced (ANTHROPIC_API_KEY only optionally read downstream). See Accepted Risks. |
| T-11-07 | Tampering (legacy placeholder coexistence — D-11) | accept | CLOSED | Accepted-risk condition holds: legacy `workflow.run curation-cycle` fake-success lambdas remain intact under a SEPARATE capability id (`_get_workflow_steps`, catalog.py:730-739); the new real `curation.run` is registered independently (catalog.py:433-452). Criterion #3 targets the real `curation.run` steps, not the legacy path. See Accepted Risks. |
| T-11-SC | Tampering (npm/pip installs) | accept | CLOSED | Accepted-risk condition holds: no package installs this phase — `tech-stack.added: []` in all three SUMMARY files; all deps shipped+vetted Phases 8-10. No supply-chain surface introduced. See Accepted Risks. |

## Accepted Risks Log

- **T-11-06 — Provider error text (Information Disclosure).** Bridge L3 enrichment, if ever
  reached online, has its errors caught by `bridge_detect` and by the curation node's own
  `try/except` + `_sanitize_error` (class-name-only). Offline (no `ANTHROPIC_API_KEY`) L3
  auto-skips. Accepted: no new secret/credential surface is introduced by Phase 11.
- **T-11-07 — Legacy placeholder coexistence (Tampering / D-11).** The legacy
  `workflow.run curation-cycle` placeholder lambdas (catalog.py:730-739) still return
  fake-success. Accepted for this phase because they live under a separate capability id and
  the real deterministic surface is the new `curation.run`. **Carried debt:** Phase 12 / CUR-05
  must remove or redirect the legacy path so the only curation invocation surface is the real
  pipeline.
- **T-11-SC — Supply chain (Tampering).** No installs this phase; accepted with zero new
  dependency surface.

## Unregistered Flags

None. No `## Threat Flags` section was emitted in any Phase 11 SUMMARY; each SUMMARY's
`## Threat Surface` explicitly states "No new trust boundaries beyond the plan's
`<threat_model>`." No new attack surface appeared during implementation without a threat mapping.

## Auditor Notes (non-blocking)

The 11-REVIEW.md flagged WR-01..WR-04 (correctness/robustness, 0 critical). Relevant to the
threat register:

- **WR-03** (orphan_scan inner handler catches only `WorkspaceLoadError`): does NOT reopen
  T-11-02. A missing/unreadable `connections.json` raises `FileNotFoundError`/`OSError`, which
  escapes the inner handler but is still caught by the node's OUTER `except Exception`
  (curation_run.py:390) → honest `failed`/`degraded` step. No unhandled crash and no
  false-completed run, so the T-11-02 mitigation remains effective. The review's point is a
  graceful-degradation nuance, not a security gap.
- **WR-04** (a `degraded` run still yields `OperationResult.success=True` / CLI exit 0): a
  process-signal ergonomics issue for automation, not a declared threat. The per-step status is
  honest (T-11-PL/T-11-02 intent preserved). Out of scope for this audit; noted for follow-up.
- **IN-02**: `_validate_run_id` docstring overstates the path surface (run_id is the LangGraph
  `thread_id`, not a filesystem path component here). The kebab guard is still correct
  defense-in-depth; T-11-01 closed regardless.

These are tracked in 11-REVIEW.md and do not block Phase 11 from a security standpoint.
