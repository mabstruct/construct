---
phase: 18
slug: contract-governance-foundations
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-02
---

# Phase 18 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

**Register origin:** `register_authored_at_plan_time: true` — all 8 PLAN files carried a parseable
`<threat_model>` block. 33 threats were declared at plan time; this audit added 3 the register
omitted (T-18-33/34/35), for a total of 36.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| MCP client → capability handler | An agent-supplied JSON payload becomes Python kwargs. Before this phase, nothing validated it. | Arbitrary caller-controlled JSON; workspace/install-root paths |
| CLI argv → capability handler | Typer-parsed user input reaching the same handlers by a second, unvalidated path. | Local user input |
| Seam → handler | `registry.invoke` — the one place a validated model becomes a handler call. | Validated model fields only |
| Review payload → apply node | A resume decision map crossing into canonical writes. | Proposal ids, decision tokens, checkpoint-id ETag |
| Capability → filesystem | An agent-supplied `workspace` / `workspace_path` / `install_root` deciding where bytes land. | Directory creation, markdown/JSONL/sqlite writes |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-18-01 | Tampering | Every payload path bypassing `input_model` | high | mitigate | `registry.py:72` validates before `cap.handler`; 26 `cli.py` sites + `capability_runner.py:147` + `help.py:151` on `.invoke`; directory-scoped AST guard | closed |
| T-18-02 | Tampering | `list_mcp_tools` → `add_tool`; unforbidden models | high | mitigate | 29/29 models forbid, held by cardinality not a name set. **Residual:** discoverability half open by D-21 (pinned FastMCP), pinned by test | closed |
| T-18-03 | Elevation of privilege | `_resolve_decisions` short-payload fallback | critical | mitigate | Fallback deleted; `_check_coverage` requires exact set equality, reached before `Command(resume=…)` | closed |
| T-18-04 | Tampering / EoP | Decision applied to a queue that changed (confused deputy) | high | mitigate | `curation_run.py:1709` exact checkpoint-id equality, before coverage and before graph invoke | closed |
| T-18-05 | Elevation of privilege | `ui/gate_review.py` writing canonical truth with no gate | critical | mitigate | Module and nav entry deleted (D-13); source-level invariant test | closed |
| T-18-06 | Repudiation | Unconditional approval emit in all three apply nodes | high | mitigate | Emit moved inside `if res.success:` at `:1277`, `:1362`, `:1414`; disk-read count invariant | closed |
| T-18-07 | Tampering | Agent-supplied `install_root` escaping the installation | high | mitigate | `install_root_error` runs before `generate()`; reason embeds no path | closed |
| T-18-08 | Injection | Caller-supplied `proposal_id` reaching persistence/path layer | high | mitigate | `_validate_proposal_id` as field validator; keys must equal queued ids exactly | closed |
| T-18-09 | Repudiation | Degraded outcome rendered as clean success | high | mitigate | `_verdict_line` qualifies any non-clean outcome on CLI, JSON and MCP | closed |
| T-18-10 | Information disclosure | Rejection reasons rendered to an MCP client | medium | mitigate | **Three declared arms hold; the default boundary does not.** See Open below | **open — below `high` threshold (non-blocking)** |
| T-18-11 | Denial of service | Broad `except Exception` in `mcp/server.py` | low | **accept** | Preserved verbatim; CONTEXT forbids restructuring. See caveat in Accepted Risks | closed (accepted) |
| T-18-12 | Tampering | Models declaring fields their handler never receives | medium | mitigate | `WorkspacePathInput` reduced; `WorkflowStatusInput` added; binding audit over all 29 | closed |
| T-18-13 | Elevation of privilege | `workspace.init` free-form domain payload | medium | mitigate | `domain: DomainInitInput` typed, not dict; malformed-payload rejection test | closed |
| T-18-14 | Repudiation | A guard asserting a name set rather than a count | medium | mitigate | `grep -c "expected = {"` → 0; `REGISTRY_SIZE = 29` tripwire + cardinality | closed |
| T-18-15 | Tampering / data loss | `model_dump()` materialising a default over a stored value | high | mitigate | **Claim was partly false — CR-03.** Now `min_length=1` + `reject_blank` validator; `""`/`"   "` reject with a reason | closed |
| T-18-16 | Elevation of privilege | Registering `spike run --tool-path` | high | mitigate-by-exclusion | No `spike` record; exclusion stated in `artifact-catalog.md:131` | closed |
| T-18-17 | Repudiation | `parse_events` passing unvalidated lines verbatim | high | mitigate | Canonicalise, derive-or-drop, counted warning; no coercion | closed |
| T-18-18 | Tampering / data loss | `DigestRecord` rename invalidating existing stores | high | mitigate | `_migrate_digest_record` + per-record load; fixture test | closed |
| T-18-19 | Tampering | Relaxing models to ignore-extra until they validate anything | medium | mitigate | Per-model rejection tests in `test_views_contracts.py` | closed |
| T-18-20 | Information disclosure | Dropped-line warning echoing raw log content | low | mitigate | Warning names field names + file/line, never content | closed |
| T-18-21 | Tampering | Deleting adapter tables turning a validating writer blind | high | mitigate | `_validate_file_data` survives, reading the shared contract table; no-partial-build invariant | closed |
| T-18-22 | Repudiation | Round-trip guard passing vacuously on an empty fixture | high | mitigate | Populated fixture, two values of N, per-slot non-empty probes, `bridges.json` gap asserted | closed |
| T-18-23 | Cross-site scripting | Event `detail`/`target` rendered by the SPA | low | **accept** | Plain JSX text child; zero `dangerouslySetInnerHTML` in the template | closed (accepted) |
| T-18-24 | Tampering | Blanket approve/reject bypassing the coverage check | high | mitigate | `_build_resume_decisions` expands both flags into a complete map that then passes coverage | closed |
| T-18-25 | DoS / data loss | Legacy id-less checkpoint failing to load | medium | mitigate | `_ensure_proposal_ids` applied to raw dicts before model validation | closed |
| T-18-26 | Denial of service | Concurrent sqlite access to the checkpoint database | medium | **transfer** | → Phase 19 OQ-4. Confirmed no locking added (`busy_timeout\|WAL\|journal_mode` → 0) | closed (transferred) |
| T-18-27 | Repudiation | Approval events for decisions nothing applied | high | mitigate | Writer removed. **CR-02 arm:** `apply_connections` now `!= "approve"` default-deny, matching both siblings | closed |
| T-18-28 | Tampering | A future phase reintroducing a second canonical writer | high | mitigate | Guard walks `rglob("*.py")`; fail-first proven. **Residual → T-18-35** | closed |
| T-18-29 | Denial of service | Removing `gate_review.py` without its nav entry | medium | mitigate | Import-level page-list test | closed |
| T-18-30 | Repudiation | Escalation logged as a rejection | high | mitigate | `_escalate_event` emits `ESCALATED_EVENT_ACTION` with `EventResult.escalated` | closed |
| T-18-31 | Tampering | A GOV-05 fix changing exit-code semantics (D-15) | high | mitigate | Success-flag computation untouched; regression guard written and observed passing first | closed |
| T-18-32 | Information disclosure | Failed-write reason surfacing raw exception text | medium | mitigate | **Claim is false for the OSError class.** See Open below | **open — below `high` threshold (non-blocking)** |
| T-18-33 | EoP / Tampering | Agent-supplied `workspace` on the 6 MCP write capabilities | high | mitigate | **Register hole — see Unregistered Findings.** `_workspace_refusal` at 6 write shims (CR-04, commit `10228e0`) | closed |
| T-18-34 | EoP / Tampering | Agent-supplied `workspace_path` on the run family | high | mitigate | **Found open by this audit; fixed before sign-off.** `_run_workspace_refusal` on all 7 measured shims (commit `191ac80`) | closed |
| T-18-35 | Tampering | Canonical-write guard exemptions granted by substring match | medium | mitigate | WR-05, unfixed by decision. See Open below | **open — below `high` threshold (non-blocking)** |
| T-18-SC | Tampering | npm/pip/cargo installs | high | mitigate | `git diff e53358b..HEAD` matches no `pyproject.toml` / `uv.lock` / `package.json` / lockfile | closed |

*Status: open · closed · open — below `high` threshold (non-blocking)*
*Only open threats at or above `workflow.security_block_on` (`high`) count toward `threats_open`.*

---

## Open Threats (non-blocking)

All three are **medium**, below the `high` block threshold, and are carried deliberately rather than
silently.

### T-18-10 — Information disclosure: filesystem paths reach the MCP client

Confirmed by live reproduction through MCP dispatch:

```
graph.status  {"workspace": "<tmpdir>"}
  message: "[Errno 2] No such file or directory:
            '/var/folders/…/SECRET-PROBE-DIR-yjeg3fkk/connections.json'"
```

**Two channels, and the second is the one code review under-reported:**

1. `mcp/server.py:53-54` — `except Exception as exc: return json.dumps({"error": str(exc)})` (WR-03).
2. **The success path.** `_serialize_result` faithfully serialises `OperationResult.message` and
   `errors[].reason`, and `services/knowledge.py` builds those from `str(exc)` at ~27 sites, plus
   `graph_status.py:66` putting `str(root.resolve())` into `data`. CR-01's fix made this channel work
   *correctly*, which is exactly what makes it leak reliably now.

Sanitising only the `except` clause would not close this.

Every *deliberate* boundary is clean and was verified: seam `CapabilityInputError` reasons are
field+constraint only; `install_root_error` / `workspace_error` reasons name no path;
`IncompleteDecisionMap` / `StaleQueue` safe messages name ids only. The **default** boundary is not.

### T-18-32 — Information disclosure: failed-write reasons carry paths

Same root cause. `_sanitize_error` and `_safe_reason` truncate to the first line but do not strip
paths:

```
_sanitize_error(FileNotFoundError)
  -> "FileNotFoundError: [Errno 2] No such file or directory: '/tmp/…/creds.json'"
```

`failed_writes` is a declared field on `CurationRunResult` and is projected into the result, so these
strings reach CLI, JSON and MCP. Plan 08's claim — "failure reasons reach the result already
sanitized" — is false for the OSError class, because the upstream `OperationResult.message` it trusts
is itself `str(exc)`. **T-18-10 and T-18-32 are one change.**

### T-18-35 — Canonical-write guard exemptions are substring-matched

`exemption_for` in `test_canonical_write_boundary.py:159-180` grants two of its three exemptions by
`"StateGraph(" in source and "interrupt(" in source` — raw text including comments and docstrings, in
a file that uses the AST for `_direct_calls` *specifically because* "a docstring that names
`edit_card` is prose". A new module self-exempts from GOV-04 with one comment line, and
`test_guard_detects_a_planted_canonical_writer` would not catch it.

Graded medium: exploitation needs repo write access, so this is an insider / future-phase vector, not
a remote one.

**→ Phase 19 note:** T-18-10 and T-18-32 become a **criterion 3 failure** for Phase 19, whose success
criterion reads "no raw exception text or filesystem paths in the body". Closing them before the HTTP
adapter is built is cheaper than after.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-18-01 | T-18-11 | Broad `except Exception` in `mcp/server.py` preserved. CONTEXT.md forbids restructuring that file, and the seam raising a typed error is what makes the swallowed string comparable across surfaces. **Caveat: the phase did edit `mcp/server.py` (CR-01, `a9441ed`), so "restructuring is forbidden" no longer fully justifies the accept — a one-line sanitisation is not a restructuring. This accept and T-18-10 should be re-decided together, not each pointing at the other.** | user | 2026-08-02 |
| AR-18-02 | T-18-23 | SPA renders `detail`/`target` through React's default text escaping; no raw-HTML sink exists in the scaffold template (verified: zero `dangerouslySetInnerHTML`). A full browser-side review belongs to Phase 22, when a served shell exists. | user | 2026-08-02 |
| AR-18-03 | T-18-26 | Concurrent sqlite checkpoint access transferred to Phase 19 (OQ-4), which owns the concurrency contract extending adr-0004. Verified honest: no locking was added, and the transfer is recorded in ROADMAP, STATE and CONTEXT with an abstain-at-verify backstop. | user | 2026-08-02 |
| AR-18-04 | T-18-10, T-18-32 | Path-leak pair carried into Phase 19 rather than fixed here: the fix pass was deliberately scoped to code-review blockers. Both are medium, below the `high` block threshold. Recorded as a Phase 19 criterion-3 dependency above. | user | 2026-08-02 |
| AR-18-05 | T-18-35 | Substring-matched guard exemptions (WR-05) carried as test-guard hardening. Requires repo write access to exploit. | user | 2026-08-02 |

---

## Unregistered Findings

Recorded because a threat register that silently omits a reproduced defect is the same repudiation
failure this phase exists to close.

1. **The register missed its own worst reproduced defect (T-18-33).** No threat id in any of the 8
   `<threat_model>` blocks covered agent-supplied `workspace` on the MCP-exposed write capabilities.
   T-18-07 named `install_root` only — the *views* half of an identical control. All six write shims
   went unguarded until code review reproduced arbitrary directory creation returning `success=True`.

2. **T-18-34 was the direct consequence, and this audit found it still open.** CR-04's remediation was
   scoped to the instances the reviewer named rather than to the property `workspace_error`'s own
   docstring states. The audit named three run capabilities; **measuring every registered capability
   found seven** — the `review` and `inspect` pairs create too, because "read-only" describes what
   `inspect` does to the workspace, not what opening a checkpointer does to the filesystem. Fixed in
   `191ac80` with a regression test that *derives* its capability list by measurement, so the trap is
   not rebuilt for the next capability.

3. **Three of eight SUMMARY files carry no `## Threat Flags` section at all** — `18-04`, `18-05`,
   `18-07`. Nine threats were self-reported nowhere; the five summaries that did report all said
   "None". All nine were independently verified closed, but the reporting control failed silently in
   37% of plans.

4. **D-23 accepts an ungated canonical-write path with no threat id.** `pipelines/ingestion.py:246`
   calls `create_card` directly and `ingest.source` is MCP-exposed. The reasoning in `18-CONTEXT.md`
   is sound (ingestion is deliberately ungated under D-04 and never claims review happened), but an
   accepted risk living only in a decisions log should carry a register id so it is re-examined when
   Phase 19 generates the HTTP adapter.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-02 | 36 | 32 | 4 (1 blocking) | gsd-security-auditor |
| 2026-08-02 | 36 | 33 | 3 (0 blocking) | orchestrator — T-18-34 fixed (`191ac80`), re-verified by measurement |

**Audit stance:** the auditor was instructed not to accept a SUMMARY's "Threat Flags: None" as
evidence. All 8 executors self-reported mitigated, and a subsequent code review still found 5
blockers, 4 reproduced against running code. Four "mitigated" claims (T-18-15, T-18-03/24, T-18-10's
CR-01 arm, T-18-02's ordering half) were partly falsified by that review and re-verified here against
the fixes rather than the original claims.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed — 3 open threats remain, all medium, below the `high` block threshold
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-02

**Suite at sign-off:** 802 passed, 18 skipped, 0 failed.
