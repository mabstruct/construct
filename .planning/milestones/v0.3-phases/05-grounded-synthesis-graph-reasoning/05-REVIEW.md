---
phase: 05-grounded-synthesis-graph-reasoning
reviewed: 2026-06-11T18:30:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - src/construct/llm/__init__.py
  - src/construct/llm/config.py
  - src/construct/llm/ask_domain.py
  - src/construct/pipelines/bridge_detect.py
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
  - src/construct/storage/workspace.py
  - tests/llm/test_ask_domain.py
  - tests/llm/conftest.py
  - tests/bridge/test_bridge_l1.py
  - tests/bridge/test_bridge_l2.py
  - tests/bridge/test_bridge_l3.py
  - tests/bridge/test_bridge_scoring.py
  - tests/bridge/conftest.py
  - tests/contract/test_ask_domain_mocked.py
  - tests/contract/test_mcp_contracts.py
  - tests/unit/test_capability_registry.py
  - CONSTRUCT-CLAUDE-impl/claude/skills/construct-synthesis/SKILL.md
findings:
  critical: 0
  warning: 7
  info: 5
  total: 12
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-06-11T18:30:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Reviewed 18 files covering Phase 05's two new capabilities — `ask.domain` LangGraph L2 gate (6-node StateGraph for grounded Q&A) and `bridge.detect` multi-level pipeline (L1 structural, L2 category overlap, L3 semantic LLM assessment). Also reviewed additions to the CLI, capability registry, workspace storage, and tests.

**Key concerns:**

1. **L2→L3 pipeline math is broken** — due to the `L3_THRESHOLD=0.30` and `L2_WEIGHT=0.20`, no L2-only candidate can ever reach the L3 threshold (max pre_score = 0.20). The L2→L3 branch is effectively dead code.
2. **Config-resolved provider parameters are ignored at LLM invocation** — `llm_synthesize` hardcodes `temperature=0.2` and `max_tokens=4096`, so changes to `config.yaml` have no runtime effect.
3. **Cache key does not include `max_cards` or `provider_override`** — different parameter values for the same question/domain would incorrectly share cached results.
4. **Token usage is never captured on successful LLM calls** — the `AskDomainOutput.token_usage` field is always `None` on success, only populated with an error dict on failure.
5. **Multi-domain cards get non-deterministic domain assignment** — `next(iter(from_domains))` depends on Python's set iteration order.

No critical security vulnerabilities were found. YAML loading uses `safe` mode, no command injection vectors exist, and no hardcoded secrets are present.

---

## Warnings

### WR-01: L2→L3 pipeline branch cannot trigger (dead math)

**File:** `src/construct/pipelines/bridge_detect.py:24-29`
**Issue:** The L3 threshold (`L3_THRESHOLD = 0.30`) combined with `L2_WEIGHT = 0.20` means no L2-only candidate can ever reach L3 assessment. The maximum pre_score for an L2-only candidate is `0.20 * 1.0 = 0.20` (when all three shared categories are present), which is below 0.30.

L1 structural candidates always have `pre_score = 0.30`, so they always qualify. But candidates detected only through L2 category overlap can never proceed to L3 semantic assessment, making the L2→L3 pipeline branch dead.

**Fix:** Either lower `L3_THRESHOLD` to allow L2-only candidates through (e.g., `0.15`), or adjust `L2_WEIGHT` so that full category overlap can cross the threshold:

```python
# Option A: Lower threshold so L2 max (0.20) qualifies
L3_THRESHOLD = 0.15

# Option B: Increase L2 weight so full overlap (3 categories) reaches threshold
L2_WEIGHT = 0.30   # Then 0.30 * 1.0 = 0.30 >= 0.30
L1_WEIGHT = 0.20   # Keep sum = 1.0
L3_WEIGHT = 0.50   # Keep sum = 1.0
```

Whichever option is chosen, the three weights must continue to sum to 1.0.

---

### WR-02: Cache key ignores `max_cards` and `provider_override`

**File:** `src/construct/llm/ask_domain.py:335-336`
**Issue:** The cache key is `f"{domain_id}::{question}"` and does not include `max_cards` or `provider_override`. A call with `max_cards=50` followed by a call with `max_cards=5` (same question and domain) would return the cached 50-card result. Similarly, a call with `provider_override="ollama"` would return the cached Anthropic result.

**Fix:** Include relevant parameters in the cache key:

```python
def _cache_key(domain_id: str, question: str, max_cards: int, provider_override: str | None) -> str:
    provider = provider_override or "default"
    return f"{domain_id}::{max_cards}::{provider}::{question}"
```

And update the call site:

```python
ck = _cache_key(
    input_data.domain_id,
    input_data.question,
    input_data.max_cards,
    input_data.provider_override,
)
```

---

### WR-03: `llm_synthesize` ignores provider config for temperature / max_tokens / timeout

**File:** `src/construct/llm/ask_domain.py:228-232`
**Issue:** The `llm_synthesize` function hardcodes `temperature=0.2` and `max_tokens=4096`, ignoring the resolved provider config from `config.yaml`. The gate config's `temperature` field (line 26 in `config.py`) and the provider config's `max_tokens` and `timeout_seconds` fields have no effect on the actual LLM invocation.

The `state["model"]` is correctly resolved, but everything else is hardcoded.

**Fix:** Pass the full resolved config through state and use it in `llm_synthesize`:

```python
def llm_synthesize(state: AskDomainState) -> dict:
    llm = ChatAnthropic(
        model=state.get("model", "claude-sonnet-4-20250514"),
        temperature=state.get("temperature", 0.2),
        max_tokens=state.get("max_tokens", 4096),
        timeout=state.get("timeout_seconds", 60),
    )
```

And populate these in `run_gate()`:

```python
initial_state["temperature"] = gate_cfg.temperature
initial_state["max_tokens"] = provider_cfg.max_tokens
initial_state["timeout_seconds"] = provider_cfg.timeout_seconds
```

The `AskDomainState` TypedDict would need new fields for these values.

---

### WR-04: Token usage never captured from successful LLM calls

**File:** `src/construct/llm/ask_domain.py:249-254`
**Issue:** After a successful `structured_llm.invoke(messages)` call, the return dict does not include a `token_usage` key. Since the initial state has `token_usage: None`, the output always has `token_usage=None` on success. On error (line 261), `token_usage` contains `{"error": str(exc)}`, which is semantically inconsistent (it's an error report, not usage data).

The `ChatAnthropic` response object contains token usage metadata, but `with_structured_output(method="json_schema")` wraps the call and the raw response is not captured.

**Fix:** Use `invoke` with `return_only_outputs=False` or capture the raw response to extract token counts:

```python
try:
    # Capture both structured output and raw response
    result: SynthesisOutput = structured_llm.invoke(messages)
    
    # Token usage requires raw response — consider using LLM.invoke
    # then parsing structured output separately, or use callbacks
    token_usage = None  # Placeholder — needs LangChain callback approach
    
    return {
        "synthesised_answer": result.answer,
        "cited_card_ids": result.cited_card_ids,
        "llm_confidence": result.confidence,
        "token_usage": token_usage,
    }
```

Alternatively, relax the output contract to document that token_usage is TBD until a callback-based tracking approach is added.

---

### WR-05: Multi-domain cards get non-deterministic domain assignment

**File:** `src/construct/pipelines/bridge_detect.py:139-140`
**Issue:** When a card belongs to multiple domains, `next(iter(from_domains))` picks an arbitrary domain from the set. Python set iteration order is not guaranteed and can vary across runs. This means the same connection may report different `from_domain`/`to_domain` values on different runs.

**Fix:** For multi-domain cards, either join all matching domains, use a deterministic sort, or pick the first alphabetically:

```python
# Option: sort for determinism
"from_domain": ", ".join(sorted(from_domains)) if from_domains else "",

# Option: pick first alphabetically
"from_domain": min(from_domains) if from_domains else "",
```

Also consider whether the `from_domain != to_domains` comparison at line 134 should handle the multi-domain case (e.g., overlapping domain sets should not be a bridge).

---

### WR-06: `extract_citations` always marks review as required/pending

**File:** `src/construct/llm/ask_domain.py:298-299`
**Issue:** The `extract_citations` node always sets `review_required=True` and `review_status="pending"`. This overwrites the empty-context guard in `llm_synthesize` which correctly sets `review_required=False, review_status="not_required"`. When no LLM call was made (no relevant cards), the review status incorrectly shows "pending" even though there is nothing to review.

**Fix:** Only set review flags if the LLM actually produced output:

```python
def extract_citations(state: AskDomainState) -> dict:
    # ... existing citation resolution ...
    
    has_answer = state.get("synthesised_answer") is not None
    return {
        "citations": citations_list,
        "review_required": has_answer,
        "review_status": "pending" if has_answer else "not_required",
    }
```

---

### WR-07: `import warnings` inside exception handler in loop

**File:** `src/construct/storage/workspace.py:154-156`
**Issue:** The `import warnings` statement is inside a `catch` block inside a loop over all card files. On every unparseable card file, Python re-imports the `warnings` module. This is inefficient — especially on workspaces with many cards where a few might be unparseable.

**Fix:** Move the import to the top of the file:

```python
"""Workspace discovery and canonical file loading."""

from __future__ import annotations

import json
import warnings  # <-- add here, not inside except block
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
```

---

## Info

### IN-01: `print()` instead of `logging.warning()` for runtime warning

**File:** `src/construct/llm/ask_domain.py:294`
**Issue:** Missing citation IDs are reported via `print()`. The project uses `logging` elsewhere (e.g., `bridge_detect.py:16` creates `logging.getLogger(__name__)`). Using `logger.warning()` would be more consistent and controllable.

**Fix:**
```python
import logging
logger = logging.getLogger(__name__)

# In extract_citations:
if missing:
    logger.warning("Cited card IDs not in retrieved set: %s", missing)
```

---

### IN-02: L3 test coverage is minimal

**File:** `tests/bridge/test_bridge_l3.py:1-20`
**Issue:** The L3 test file only asserts that two module-level constants (`L3_THRESHOLD` and `MAX_L3_CANDIDATES`) have expected values. There are no tests for the `_l3_semantic` function's behavior — including the skip-when-no-key guard, the max-candidates cost guard, the import error fallback, or the individual candidate assessment error path.

**Suggestion:** Add tests that monkeypatch the LLM dependency and exercise the guard conditions, e.g.:
- `ANTHROPIC_API_KEY` not set → returns `{}`
- Candidates below threshold → returns `{}`
- Qualifying candidate → calls LLM mock and returns verdict
- LLM call fails per-candidate → logs warning, stores `reject` verdict

---

### IN-03: `_l1_structural` silently drops connections involving domainless cards

**File:** `src/construct/pipelines/bridge_detect.py:134`
**Issue:** The condition `if from_domains and to_domains and from_domains != to_domains` excludes connections where either endpoint card has no domains (`from_domains` is an empty set). These connections are silently dropped — no warning is logged.

**Suggestion:** Add a `logger.warning` when a connection is skipped due to missing domain info on either endpoint.

---

### IN-04: `warnings.warn()` vs `logging` pattern inconsistency

**File:** `src/construct/storage/workspace.py:156`
**Issue:** `warnings.warn()` is used for unparseable card notifications. The rest of the project (especially bridge_detect.py) uses `logging.getLogger(__name__).warning()`. Using `logging.warning()` provides more consistent behavior and allows callers to control output.

---

### IN-05: Deep imports inside function bodies

**Files:**
- `src/construct/llm/ask_domain.py:115-116` — `parse_card_markdown` and `WorkspaceLoader` imported inside `load_domain_cards`
- `src/construct/pipelines/bridge_detect.py:334-335` — `ChatAnthropic` and messages imported inside `_l3_semantic`

**Issue:** While the `_l3_semantic` import is inside `try/except ImportError` for graceful degradation (acceptable pattern), the `load_domain_cards` imports are unconditional and incur import overhead on every graph node invocation. The comment in `catalog.py:63` suggests these are placed inside to avoid circular imports, but moving them to module level should be safe since no circular dependency exists between `ask_domain.py` and the imported modules.

---

_Reviewed: 2026-06-11T18:30:00Z_
_Reviewer: gsd-code-reviewer (deepseek-v4-flash-free)_
_Depth: standard_
