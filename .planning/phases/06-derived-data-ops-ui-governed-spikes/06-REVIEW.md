---
phase: 06-derived-data-ops-ui-governed-spikes
reviewed: 2026-06-11T15:30:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/construct/views/__init__.py
  - src/construct/views/models.py
  - src/construct/views/generate.py
  - src/construct/ui/__init__.py
  - src/construct/ui/streamlit_app.py
  - src/construct/ui/dashboard.py
  - src/construct/ui/capability_runner.py
  - src/construct/ui/gate_review.py
  - src/construct/pipelines/spike_runner.py
  - src/construct/pipelines/tag_extraction.py
  - src/construct/services/knowledge.py
  - src/construct/cli.py
  - tests/contract/test_views_contracts.py
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-06-11T15:30:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed 13 files from Phase 06 covering the Pydantic views contract models, schema-validated generate pipeline, Streamlit ops dashboard (4 panels), governed spike runner with temp workspace isolation, LLM/hybrid tag extraction pipeline, tag approval wiring in the knowledge service, and CLI command groups for views/spike/tag. Test file (49 contract tests) was also reviewed.

**Overall assessment:** Well-structured code with proper Pydantic v2 conventions, good use of typed exceptions, and adherence to D-08 (no auto-accept of tags). However, there is significant dead code in `generate.py` where `_FILE_MODEL_MAP` / `_PER_WS_FILES` are defined but never used, while identical logic is duplicated in `_validate_file_data`. Similar dead code exists in `spike_runner.py` (`register_spike_commands` is never called). The `gate_review.py` event logging has a copy-paste issue where both approve and reject always log as success. Several minor code quality issues are present.

No critical security issues found. Command injection in spike runner is properly mitigated via `shlex.quote()` + `shlex.split()` + no `shell=True`. Tag candidates correctly start as "pending" per D-08.

---

## Warnings

### WR-01: Dead code — `_FILE_MODEL_MAP` and `_PER_WS_FILES` defined but never used

**Files:**
- `src/construct/views/generate.py:96`
- `src/construct/views/generate.py:111`

**Issue:** Two module-level constants `_FILE_MODEL_MAP` (lines 96-108) and `_PER_WS_FILES` (lines 111-167) are defined with detailed field-mapping lambdas, but are **never referenced** anywhere in the codebase. The actual validation logic lives in `_validate_file_data()` (lines 406-541), which contains nearly identical inline mappings. This is a DRY violation and a maintenance trap — a developer updating the field mappings in one place will not realize they must update the other.

**Fix:** Remove the dead code constants — they are unused and their logic is fully duplicated in `_validate_file_data()`. Or, refactor `_validate_file_data()` to iterate over a single source-of-truth mapping instead of duplicating field definitions.

---

### WR-02: `_log_gate_event` always logs `EventResult.success` for both approve and reject

**File:** `src/construct/ui/gate_review.py:41`

**Issue:**
```python
result = EventResult.success if "approved" in action else EventResult.success
```
Both branches of the conditional return `EventResult.success`. The `EventResult` enum has `success`, `failure`, and `escalated` members — so this was likely intended to use `EventResult.failure` in the reject branch:
```python
result = EventResult.success if "approved" in action else EventResult.failure
```
While the `action` string (e.g., `"gate_review_rejected"`) does correctly distinguish the outcomes in the event log, the `result` field is misleading — a rejection is recorded with `result="success"`.

**Fix:**
```python
result = EventResult.success if "approved" in action else EventResult.failure
```

---

### WR-03: Card confidence/source_tier default to 0 but Pydantic model requires >= 1

**File:** `src/construct/views/generate.py:464-465`

**Issue:** In the `_validate_file_data` card lambda (also in `_PER_WS_FILES` dead code):
```python
"confidence": c.get("confidence", 0),
"source_tier": c.get("source_tier", 0),
```
`CardRecord` constrains these fields to `ge=1` and `le=5` (models.py:171-172). Defaulting to `0` means: if source data is missing these fields, Pydantic validation fails with a confusing message ("confidence must be >= 1") rather than "field missing from input". The entire file is then skipped (line 336-337) without a clear explanation that the source data is incomplete.

If the source parser always produces these fields, this is defense-in-depth. But if a data gap occurs, the error message will mislead debugging.

**Fix:** Either set defaults to the minimum valid value (`1`):
```python
"confidence": c.get("confidence", 1),
"source_tier": c.get("source_tier", 1),
```
Or wrap the field extraction in a try/except that produces a targeted error message about missing fields.

---

### WR-04: Duplicated workspace parsing block in `generate()`

**File:** `src/construct/views/generate.py:228-271`

**Issue:** The workspace parsing logic (parse_cards, parse_connections, denormalize_into_cards, parse_digests, parse_events, parse_curation, refs_count) is duplicated verbatim in two branches:
- Lines 228-247: For workspaces in `changed_ws`
- Lines 253-271: Fallback when `_load_cached_workspace` returns `None`

This is ~40 lines of identical code. Any change to the parsing sequence — e.g., adding a new parser, changing argument order — must be made in both places.

**Fix:** Extract the parsing logic into a helper function:
```python
def _parse_workspace(ws: Path, warnings: list) -> dict:
    cards = parse_cards.parse(ws, warnings)
    connections = parse_connections.parse(ws, warnings)
    parse_connections.denormalize_into_cards(cards, connections["connections"])
    digests = parse_digests.parse(ws, warnings, cards=cards)
    events = parse_events.parse(ws, warnings)
    curation = parse_curation.parse(ws, warnings)
    refs_dir = ws / "refs"
    refs_count = sum(1 for _ in refs_dir.glob("*.json")) if refs_dir.is_dir() else 0
    return {"cards": cards, "connections": connections, "digests": digests,
            "events": events, "curation": curation, "refs_count": refs_count}
```

---

### WR-05: Dead code — `register_spike_commands()` defined but never called

**File:** `src/construct/pipelines/spike_runner.py:272-323`

**Issue:** The function `register_spike_commands()` defines Typer commands (`spike list`, `spike run`) on an injected app instance, but is **never imported or called** anywhere in the codebase. The actual spike CLI commands are defined directly in `cli.py` (lines 472-560), which duplicates the command registration logic. This generates a second parallel implementation that is dead code.

**Fix:** Either:
1. Remove `register_spike_commands()` entirely (the cli.py implementation is the active one), or
2. Wire it up by calling it from the CLI initialization in `cli.py`, removing the inline spike command definitions.

---

## Info

### IN-01: `_data_dir_for()` is unused dead code in test file

**File:** `tests/contract/test_views_contracts.py:81-84`

**Issue:** The helper function `_data_dir_for()` always returns `DATA_DIR` regardless of the `rel` parameter, and is never called anywhere in the test suite. Dead code.

**Fix:** Remove the function.

---

### IN-02: Tautological assertion in test

**File:** `tests/contract/test_views_contracts.py:122`

**Issue:**
```python
assert hasattr(bridges, "model_config")
```
Every Pydantic v2 `BaseModel` instance has `model_config`. This assertion always passes and tests nothing meaningful.

**Fix:** Either remove the assertion or replace it with something that actually validates the model state (e.g., checking specific config values).

---

### IN-03: Duplicated model mapping in CLI `views validate`

**File:** `src/construct/cli.py:362-465`

**Issue:** The `views validate` command defines its own model-mapping logic inline (`model_map` dict at lines 391-396 and per-workspace file types at lines 424-429), duplicating the model-to-file-type mapping that also exists in `generate.py:_validate_file_data()`.

Any change to the views data contracts requires updating mappings in at least two places. Consider sharing a single registry of (file_pattern, model_class) pairs that both validation and generation can reference.

---

### IN-04: Generic type annotations on `_FILE_MODEL_MAP`

**File:** `src/construct/views/generate.py:96`

**Issue:**
```python
_FILE_MODEL_MAP: list[tuple[str, type, callable]] = ...
```
Uses bare `type` and `callable` instead of more specific type hints like `type[BaseModel]` and `Callable[[dict], dict]`. While this module is annotated but not checked at runtime, following project conventions (which favour explicit typing) would improve consistency.

---

### IN-05: Tag extraction docstring says "adjective-noun pairs" but regex is broader

**File:** `src/construct/pipelines/tag_extraction.py:352-369`

**Issue:** Pattern 2 is documented as extracting "adjective-noun pairs (e.g. 'quantum gravity', 'cosmic inflation')" but the regex `[a-z]+(?:\s+[a-z]+){1,2}` matches any 2-3 lowercase word sequences regardless of part of speech. This is not a functional bug — the wider net is fine — but the docstring is misleading about what's matched.

**Fix:** Update the comment/docstring to accurately reflect that Pattern 2 matches any multi-word lowercase phrase, not specifically adjective-noun pairs.

---

### IN-06: `_FILE_MODEL_MAP` and `_PER_WS_FILES` — maintenance risk noted separately

**File:** `src/construct/views/generate.py:96-167`

Already covered under WR-01. Listed separately for severity differentiation.

---

### IN-07: CLI `spike run` does not expose `install_root` parameter

**File:** `src/construct/cli.py:499-530`

**Issue:** The `run_spike()` function accepts an `install_root` parameter (which defaults to `root.parent`), but the CLI command doesn't expose it. For non-standard workspace layouts, users cannot control where `log/spike-results/` is written. Minor — the parent-of-workspace default is reasonable for single-user local-first usage.

---

_Reviewed: 2026-06-11T15:30:00Z_
_Reviewer: gsd-code-reviewer (standard depth)_
_Depth: standard_
