---
phase: 13-daily-cycle-composition
reviewed: 2026-07-07T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - src/construct/llm/daily_run.py
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - tests/contract/test_daily_run_cli_mcp.py
  - tests/contract/test_mcp_contracts.py
  - tests/llm/test_daily_run.py
  - tests/unit/test_capability_registry.py
  - CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-07-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the thin `daily.run` composition workflow (Phase 13) — `src/construct/llm/daily_run.py`, its registry wiring in `catalog.py`, the `daily` Typer sub-app in `cli.py`, and the four test/workflow artifacts. I cross-checked the load-bearing assumptions against the frozen child modules (`curation_run.py`, `research_run.py`) rather than trusting the docstrings:

- **Escalate exclusion is correct.** `curation_run.py:707` maps an `escalate` promotion verdict to `kind="escalate"`, and daily's count `sum(1 for p in c.gate_queue if p.get("kind") == "escalate")` (`daily_run.py:181`) matches. The apply nodes filter on `promotion`/`connection`/`archive` kinds only, so escalate items are genuinely never written on the `approve_all` resume. D-02/D-03 hold.
- **Path-traversal guard is real.** `run_id` is kebab-validated on both input models before the receipt path join; generated ids (`daily-<stamp>-<hex>`) and the `-research`/`-curation` child suffixes all satisfy `KEBAB_CASE_PATTERN`.
- **Error sanitization holds.** Child failures route through `_sanitize_error`; no raw provider text or secrets leak.
- **Exit-code contract honored.** `degraded → success=True → exit 0` is consistent with the documented curation contract; only a full `failed` aggregate exits 1.
- **MCP parity is free.** `mcp/server.py` is untouched; auto-discovery is proven by `test_mcp_no_hardcoded_daily`.
- Confirmed pydantic 2.13.4 `ValidationError` subclasses `ValueError`, so `inspect_daily_run`'s `except (OSError, ValueError)` does catch a schema-drift receipt (no bug there).

No blockers found: no injection, hardcoded secrets, crash on normal paths, or data-loss risk. The three warnings below are robustness gaps around the module's central "never a false completed" and "non-fatal receipt" guarantees.

## Warnings

### WR-01: Aggregate uses a degrade-forcing blocklist, weakening the "no false completed" invariant

**File:** `src/construct/llm/daily_run.py:132-138`
**Issue:** `_aggregate_daily_status` returns `degraded` only when a child status is in the explicit set `("failed", "degraded", "awaiting_review")`. Because `DailyChildStatus.status` is a free-form `str` (not a `Literal`), any unexpected child status string — e.g. a `"running"` leak from `run_research_run` (`research_run.py:945` defaults `result.get("status", "completed")`), or the `"skipped"` value the `DailyChildStatus` docstring itself advertises — is treated as non-degrading and rolls up to a bare `completed`. For a module whose entire stated purpose (DAY-03) is "never report a false completed," a blocklist inverts the safe default. Today's children only emit `completed`/`failed`, so the false-completed is latent rather than live, but the guard is one child-status change away from silently violating the invariant.
**Fix:** Invert to a whitelist so anything that is not an explicit success degrades:
```python
if children and all(ch.status == "failed" for ch in children):
    return "failed"
if pending_escalations > 0 or any(ch.status != "completed" for ch in children):
    return "degraded"
return "completed"
```
Optionally also constrain `DailyChildStatus.status` to a `Literal[...]` so an unexpected value is rejected at the model boundary.

### WR-02: Pending-escalation count silently dropped to 0 when the curation resume raises

**File:** `src/construct/llm/daily_run.py:177-192`
**Issue:** `pending` is correctly captured from the `awaiting_review` gate queue *before* the resume (Pitfall 5). But if `review_curation_run(approve_all=True)` (`daily_run.py:182`) raises, the `except` block returns a hardcoded `0` for the pending count instead of the already-computed `pending`. The escalate items still weren't written (safe), and the aggregate is still `degraded` (the child is `failed`), but the operator loses all visibility into how many items were escalated and need manual review — the run reports `pending_escalations: 0` when there genuinely were escalations. That defeats the "surface escalations as a pending count" purpose of D-02/D-03a.
**Fix:** Return the already-captured count in the failure path:
```python
    except Exception as exc:  # noqa: BLE001 — isolate + degrade (D-06)
        logger.warning("daily.run: curation child failed: %s", _sanitize_error(exc))
        return DailyChildStatus(
            capability="curation.run", status="failed", run_id=child_run_id,
            pending_escalations=pending, message=_sanitize_error(exc),
        ), pending
```

### WR-03: Receipt-persistence guard catches only `OSError`, so a serialization error aborts the whole run

**File:** `src/construct/llm/daily_run.py:245-249`
**Issue:** The receipt write is documented as "non-fatal — the run result still returns to the caller," but the `try` only catches `OSError`. `graph_health` is an untyped `dict` folded verbatim from `graph_status(...).data`. If any value in it is not JSON-serializable, `result.model_dump(mode="json")` raises `pydantic_core.PydanticSerializationError` (verified: `Unable to serialize unknown type`), and `json.dumps(...)` can raise `TypeError` — neither is an `OSError`. Such an exception escapes `run_daily_run`, is caught by the outer shim `_daily_result_to_operation` (`catalog.py:728`), and converts an otherwise successful/degraded cycle into a hard `success=False, "daily.run failed: PydanticSerializationError"` with the computed result discarded and no receipt written — directly contradicting the "non-fatal" guarantee. Likelihood is low today (the health report is designed for JSON), but the guard is too narrow for a block that promises to swallow persistence failures.
**Fix:** Widen the guard to cover serialization failures, e.g.:
```python
    except (OSError, TypeError, ValueError) as exc:  # non-fatal — result still returns
        logger.warning("daily.run: could not persist receipt %s: %s", path, _sanitize_error(exc))
```
(If `PydanticSerializationError` must be caught explicitly, do the `model_dump(mode="json")` inside the guarded block — it currently runs inside `write_text`'s argument, already within the `try`, so widening the except types is sufficient.)

## Info

### IN-01: `DailyChildStatus.status` documents a `"skipped"` value that is never produced

**File:** `src/construct/llm/daily_run.py:91`
**Issue:** The field comment lists `completed | degraded | failed | awaiting_review | skipped`, but no code path ever emits `"skipped"` (and, per WR-01, the aggregate would silently treat it as non-degrading). Dead/aspirational documentation on a status enum.
**Fix:** Remove `skipped` from the comment, or introduce and handle it explicitly if a skipped-child state is intended (e.g. research skipped when not due, per the workflow doc Step 2).

### IN-02: `inspect_daily_run` reports "No such daily run." for a corrupt-but-present receipt

**File:** `src/construct/llm/daily_run.py:263-268`
**Issue:** When the receipt file exists but is unreadable/corrupt (`OSError`/`ValueError`/`ValidationError`), the function returns the same `"No such daily run."` message used for a genuinely missing run. This conflates "missing" with "corrupt," which is misleading when debugging a truncated or schema-drifted receipt. It intentionally mirrors `inspect_curation_run`, so this is a consistency-preserving nit, not a defect.
**Fix:** Distinguish the two, e.g. return `message="Daily run receipt is unreadable or corrupt."` in the `except` branch while keeping "No such daily run." only for the `not path.exists()` case.

---

_Reviewed: 2026-07-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
