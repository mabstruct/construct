---
phase: 10-durable-human-review-research-run
reviewed: 2026-06-28T15:01:45Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - src/construct/llm/research_run.py
  - src/construct/pipelines/research_dedup.py
  - tests/contract/test_research_run_cli_mcp.py
  - tests/llm/conftest.py
  - tests/llm/test_research_run.py
  - tests/pipelines/test_research_dedup.py
  - pyproject.toml
  - .gitignore
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-06-28T15:01:45Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the durable, human-gated `research.run` workflow: the LangGraph
state/nodes/interrupt-gate/checkpointer wiring (`research_run.py`), the
idempotency primitives (`research_dedup.py`), the capability registration and
dual-mode shims (`catalog.py`), and the CLI commands (`cli.py`).

The interrupt-gate durability design is sound: writes are strictly downstream of
`gate_review` (which is interrupt-only), the checkpointer keeps a long-lived
connection (avoiding the connection-string footgun), error sanitization routes
through `_safe_scoring_cause`/`safe_message` so raw provider text never leaks,
and ref/card IDs are deterministic with skip-if-exists. The rejected ledger
correctly lives under `.construct/` (non-SOT, gitignored).

However, there is one **BLOCKER**: an unvalidated, attacker-controllable
`run_id` flows into a filesystem path in `compile_digest`, producing an
arbitrary-file-write path traversal that is reachable end-to-end through the MCP
surface. There are also several correctness/robustness warnings around the
idempotency claims of the rejected ledger, an `assert`-based security invariant,
inspect/review state guards, and a semantic mismatch in query capping.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Path traversal — unvalidated `run_id` is interpolated into a written file path

**File:** `src/construct/llm/research_run.py:643,682-683` (with `:618`, `:90-96`, `:99-108`)
**Issue:**
`compile_digest` derives the digest filename directly from the run handle:

```python
run_id = state.get("run_id") or state.get("gate_id") or "run"
digest_id = f"digest-{run_id}"
...
md_path = digests_dir / f"{digest_id}.md"
md_path.write_text(markdown, encoding="utf-8")
```

`run_id` originates from `ResearchRunInput.run_id` / `ReviewInput.run_id`, both
typed only as `str` with **no format validation** (no `KEBAB_CASE_PATTERN`, no
slug constraint). `model_config = {"extra": "forbid"}` constrains *which keys*
are accepted, not their *values*. `DigestRecord.id` is likewise an unconstrained
`str` (`views/models.py:224`), and the markdown file is written *before* any
model is constructed, so even a later validation error cannot prevent the write.

The `research.run` / `research.review` MCP tools accept keyword args straight
into these models (`catalog.py:520,529` → `ResearchRunInput(**kwargs)` /
`ReviewInput(**kwargs)`). A caller (or any upstream/untrusted tool input feeding
the agent) can supply:

```
run_id = "../../../../tmp/evil"
```

Starting a run with that `run_id` and then resuming it drives
`compile_digest`, where:

```
workspace/digests / "digest-../../../../tmp/evil.md"
```

resolves out of the workspace tree, writing attacker-controlled markdown to an
arbitrary location. `ref_id`/`card_id` are safe (kebab-validated via
`ref_id_for`), so the digest path is the one unguarded sink. The CLI happens not
to expose `--run-id` on `research run` (it generates the handle), but the MCP
tool and `research.review`/`research.inspect` all accept `run_id` verbatim, so
the vulnerability is reachable.

**Fix:** Validate `run_id` at the trust boundary (the Pydantic models) and reuse
the existing kebab invariant. For example, in both `ResearchRunInput` and
`ReviewInput`/`InspectInput`:

```python
from pydantic import field_validator
from construct.schemas.config import KEBAB_CASE_PATTERN

@field_validator("run_id")
@classmethod
def _validate_run_id(cls, v):
    if v is not None and KEBAB_CASE_PATTERN.fullmatch(v) is None:
        raise ValueError("run_id must be kebab-case ([a-z0-9-])")
    return v
```

Additionally, defense-in-depth in `compile_digest`: derive the filename from a
sanitized slug (mirroring `ref_id_for`) rather than raw `run_id`, and assert the
resolved path stays within the workspace:

```python
md_path = (digests_dir / f"{digest_id}.md").resolve()
if not str(md_path).startswith(str(digests_dir.resolve()) + "/"):
    raise ValueError("digest path escapes workspace")
```

## Warnings

### WR-01: Rejected-ledger append is not idempotent — contradicts the RSCH-05 claim

**File:** `src/construct/pipelines/research_dedup.py:139-167`, `src/construct/llm/research_run.py:576-581`
**Issue:** `append_rejected` unconditionally appends an entry; there is no
skip-if-exists. `ingest_batch`'s docstring (`:476-487`) claims "a rerun or a
mid-batch crash+resume never double-writes (RSCH-05)", but that guarantee only
holds for refs/cards (which are skip-if-exists). When `ingest_batch` re-executes
top-to-bottom after a mid-batch crash+resume (the documented LangGraph
re-execution semantics), every `skip`/`reject` finding processed *before* the
crash point is appended to the ledger a second time, accumulating duplicate
entries. `test_partial_batch_resume_safe` masks this because the only `skip`
finding (shop) is ordered last and is never reached before the crash. The
duplicates are harmless to filtering (`rejected_normalized_urls` dedupes via a
`set`) but cause unbounded ledger growth and falsify the idempotency claim.
**Fix:** Make the append idempotent on `normalized_url`:

```python
ledger = load_rejected_ledger(workspace)
existing = {e.get("normalized_url") for e in ledger["rejected"]}
if normalized_url in existing:
    return
ledger["rejected"].append({...})
```

### WR-02: Security-relevant ID invariant enforced with `assert` (stripped under `-O`)

**File:** `src/construct/pipelines/research_dedup.py:76`
**Issue:** `ref_id_for` validates its output with
`assert KEBAB_CASE_PATTERN.fullmatch(ref_id) is not None`. `assert` is removed
when Python runs with `-O`/`PYTHONOPTIMIZE`, so the only guard that the derived
ID is path-safe disappears in optimized deployments. The preceding regex
(`re.sub(r"[^a-z0-9]+", "-", ...)`) already constrains the slug, so the residual
risk is low, but a load-bearing invariant should not depend on assertions.
**Fix:** Replace with an explicit raise:

```python
if KEBAB_CASE_PATTERN.fullmatch(ref_id) is None:
    raise ValueError(f"derived ref_id is not kebab-valid: {ref_id!r}")
```

### WR-03: `inspect_research_run` reports a nonexistent run as `success=True`

**File:** `src/construct/llm/research_run.py:1009-1011`, `src/construct/capabilities/catalog.py:508-512`
**Issue:** For an unknown `run_id`, `get_state` returns an empty snapshot
(`snap.next == ()`, `snap.values == {}`), so the branch sets
`status = "unknown"`, `message = "No such run."`. `_run_result_to_operation`
then computes `success = result.status != "failed"`, so `"unknown"` →
`success=True`. Inspecting a run that does not exist therefore returns a
"successful" OperationResult. `"unknown"` is also outside the documented status
enum (`awaiting_review | completed | failed`), so downstream consumers that
switch on status have no case for it.
**Fix:** Treat "no such run" as a failure (or a distinct not-found status that
maps to `success=False`):

```python
status = values.get("status", "completed") if values else "not_found"
...
# and in _run_result_to_operation:
success=result.status not in ("failed", "not_found"),
```

### WR-04: `build_queries` caps the number of *queries*, not *papers*

**File:** `src/construct/llm/research_run.py:241-244`
**Issue:** The cap applies the governance `max_papers_per_cycle` to the count of
query strings / clusters (`queries = queries[:cap]`), not to the number of
papers/results. A workspace with `max_papers_per_cycle=5` and 8 active clusters
silently drops 3 *clusters*, while a single remaining cluster may still return
far more than 5 papers downstream. The behavior matches
`test_build_queries_respects_max_papers_per_cycle` (which asserts 2 queries when
cap=2), so the test encodes the mismatch rather than catching it. This is a
correctness/semantics gap against the field's name and intent.
**Fix:** Either rename/document the cap as a per-cycle *cluster* limit, or apply
`max_papers_per_cycle` where results are actually bounded (e.g. truncate
`deduped`/`search_results`, or pass it as the per-query result cap to
`research_search`).

### WR-05: `review_research_run` does not verify the run is actually paused before resuming

**File:** `src/construct/llm/research_run.py:962-987`
**Issue:** `review_research_run` reads the snapshot and immediately calls
`graph.invoke(Command(resume=decisions), cfg)` with no check that
`snap.next == ("gate_review",)`. Resuming a run that is already completed
(or never paused) re-enters the post-gate write nodes — `update_seeds_and_log`
re-appends D-11 audit events via `append_event` (append-only, no idempotency)
and re-stamps `last_queried`/`updated` on clusters, producing duplicate audit
trail entries. `inspect_research_run` guards its branches on `snap.next`;
`review` should apply the same gate.
**Fix:** Short-circuit when not awaiting review:

```python
snap = graph.get_state(cfg)
if snap.next != ("gate_review",):
    return _completion_result(inp.run_id, snap.values or {}, completed=not snap.next)
```

## Info

### IN-01: `normalize_url` drops `:80`/`:443` for all schemes and may raise on a malformed port

**File:** `src/construct/pipelines/research_dedup.py:53-62`
**Issue:** The scheme is forced to `https`, then `:443`/`:80` are stripped
regardless of the original scheme. For dedup keying this is internally
consistent (so it is not a correctness bug), but it means an `http://h:80/` and
a genuinely different `https://h/` collapse together. Separately, `parts.port`
can raise `ValueError` on a malformed authority (e.g. `host:notaport`), which
would propagate out of `deduplicate` since the call is unguarded.
**Fix:** Wrap the port access defensively (`try/except ValueError`) and treat an
unparseable URL as its raw string, or document the intentional collapse.

### IN-02: Repeated function-local `import json`

**File:** `src/construct/llm/research_run.py:301,489,612,723`; `src/construct/cli.py:746,772`
**Issue:** `json` is imported inside several node bodies/commands rather than
once at module top. The lazy imports for `construct.*` modules are justified
(circular-import avoidance), but stdlib `json` has no such constraint — the
repetition is noise.
**Fix:** Import `json` once at module scope.

### IN-03: Digest "approved" count includes findings whose ingest silently failed

**File:** `src/construct/llm/research_run.py:626`, `:582-583`
**Issue:** `ingest_batch` isolates per-finding errors with a broad
`except Exception` (by design, D-08), so a finding can be counted as "approved"
in `compile_digest` (`approved = sum(... d in _INGEST_ACTIONS)`) even though no
ref/card was actually written and the finding was dropped without being
ledgered. The digest summary can therefore overstate the ingest result.
**Fix:** Base the digest's approved/ingested counts on the actual
`refs_created`/`cards_created`/`skipped_existing` returned by `ingest_batch`
rather than recomputing from the decision list.

---

_Reviewed: 2026-06-28T15:01:45Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
