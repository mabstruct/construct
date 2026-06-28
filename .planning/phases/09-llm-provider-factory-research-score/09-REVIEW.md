---
phase: 09-llm-provider-factory-research-score
reviewed: 2026-06-28T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/construct/llm/factory.py
  - src/construct/llm/research_score.py
  - src/construct/llm/config.py
  - src/construct/llm/ask_domain.py
  - src/construct/capabilities/catalog.py
  - src/construct/cli.py
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-06-28
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 9 introduces the model-agnostic provider factory and the `research.score`
L3 gate exposed on CLI + MCP. The per-item error sanitization in
`research_score.py` (`_safe_scoring_cause`, the skip-finding fallback, the
`ScoreAllResult.total_outage` promotion) is genuinely well-constructed: in-loop
provider exceptions are classified and stripped before they reach any surfaced
field, and the total-outage → `OperationResult(success=False)` mapping in
`_research_score_shim` is correct.

However, the sanitization is only as strong as the boundary that encloses it,
and that boundary leaks. The `research.score` shim catches **only**
`ResearchScoreOutageError` — every *pre-flight* provider/config error
(missing config file, unknown provider, missing optional extra, missing API
key during model construction, governance/taxonomy load failure) escapes the
shim entirely. On the MCP surface those escape into `server.py:37`'s blanket
`json.dumps({"error": str(exc)})`, bypassing the entire sanitization layer the
phase built; on the CLI they produce an uncaught traceback. This is the central
defect (CR-01).

The untrusted-payload flattener in `cli.py` also has a validation gap: it
catches `ValidationError`/`JSONDecodeError` but not the `AttributeError` raised
by malformed batch envelopes (WR-01). The `builtins.list` shadow workaround is
correct and necessary (verified: `cli.list` is rebound to a Typer command, not
the builtin) — see IN-01 for the root-cause footgun.

I also reviewed `ask_domain.py` (refactored this phase to route through the
factory) and found two pre-existing correctness/robustness defects surfaced by
the refactor's blast radius (CR-02, WR-03, WR-04).

## Critical Issues

### CR-01: `research.score` pre-flight provider/config errors bypass sanitization and break the `success=False` contract

**File:** `src/construct/capabilities/catalog.py:401-422` (and `src/construct/cli.py:540`, `src/construct/llm/research_score.py:497-514`)
**Issue:**
`_research_score_shim` only translates `ResearchScoreOutageError` into a clean
`OperationResult(success=False, ...)`. Any other exception raised by
`research_score_gate` escapes the shim unhandled. Multiple non-outage failure
paths raise *before* `score_all` ever runs, so they never become a
`ResearchScoreOutageError`:

- `load_llm_config(...)` → `FileNotFoundError` ("GATE_PROVIDER_ERROR: LLM config not found ...") — `research_score.py:504`
- unknown gate → `RuntimeError("GATE_PROVIDER_ERROR: unknown gate ...")` — `research_score.py:507`
- `config.providers["anthropic"]` fallback → `KeyError` when a custom config omits the `anthropic` provider — `research_score.py:510`
- `build_scoring_llm(...)` → `RuntimeError("GATE_PROVIDER_ERROR: ...")` for unknown type / missing `llm-openai` extra, **or** a raw provider construction error (e.g. langchain's "Did not find anthropic_api_key ...") when the API key env var is absent — `research_score.py:514` / `factory.py:46-58`
- `load_governance_thresholds` / `load_taxonomy_categories` failures — `research_score.py:512-513`

Consequences:
1. **Broken contract.** The most common operator error — provider not
   configured / API key not set — does *not* produce `success=False`. On the
   CLI (`cli.py:540`, where `cap.handler(**handler_kwargs)` is not wrapped) it
   emits a Python traceback instead of the gate's documented failure result.
2. **Sanitization bypass.** On MCP, the escaped exception hits the server's
   catch-all `return json.dumps({"error": str(exc)})` — the raw, unsanitized
   provider exception text is surfaced to the client, defeating the T-09-06
   "message never contains provider internals" intent that the in-loop path
   carefully enforces.

**Fix:** Wrap the whole gate invocation in the shim and route every
non-outage failure through the same key-safe sanitizer used in-loop:

```python
def _research_score_shim(*args, **kwargs):
    if args:
        raise TypeError("research.score handler requires keyword arguments")
    input_data = ResearchScoreInput(**kwargs)
    try:
        output = research_score_gate("research.score", input_data)
    except ResearchScoreOutageError as exc:
        return OperationResult(
            success=False, message=exc.safe_message,
            data={"degraded": True, "total_outage": True},
        )
    except Exception as exc:  # pre-flight provider/config failure
        from construct.llm.research_score import _safe_scoring_cause
        return OperationResult(
            success=False,
            message=f"research.score failed: {_safe_scoring_cause(exc)}",
            data={"degraded": True, "total_outage": False},
        )
    ...
```

Mirror the same guard in `cli.py:research_score_cmd` (or rely on the shim) so
the CLI never tracebacks on a misconfigured provider.

### CR-02: `ask.domain` cache key omits `workspace_path` → cross-workspace answer/citation collision

**File:** `src/construct/llm/ask_domain.py:335-336, 365-368, 421-422`
**Issue:** The exact-match cache is keyed by
`f"{domain_id}::{question}"` only. `workspace_path`, `max_cards`, and
`provider_override` are not part of the key. Two different workspaces that share
a `domain_id` (e.g. the common default) and the same question will collide: the
second workspace receives the **first workspace's** cached answer *and its
citations* (card IDs/titles/snippets from an unrelated workspace). This is a
silent data-integrity defect — a grounded-Q&A gate returning fabricated-looking
citations sourced from the wrong knowledge base. (Pre-existing from Phase 5, but
in scope and surfaced by this phase's review.)

**Fix:** Include all answer-determining inputs in the cache key:

```python
def _cache_key(workspace_path: str, domain_id: str, question: str,
               max_cards: int, provider: str | None) -> str:
    return f"{workspace_path}::{domain_id}::{max_cards}::{provider}::{question}"
```

and pass `input_data.workspace_path`, `input_data.max_cards`, and
`input_data.provider_override` at both the read (`run_gate:365`) and write
(`run_gate:422`) sites.

## Warnings

### WR-01: Malformed batch envelope raises uncaught `AttributeError` at the CLI boundary

**File:** `src/construct/cli.py:464-479` (caught at `523-527`)
**Issue:** `research_score_cmd` guards `_load_search_results_json` with
`except (json.JSONDecodeError, ValueError)`. `ValidationError` is a `ValueError`
subclass (verified, pydantic 2.13.4), so bad SearchResult fields are handled —
but `_flatten_search_results_payload` calls `batch.get("results", [])` on each
envelope element without checking it is a dict. A JSON-valid but malformed
payload crashes with an uncaught `AttributeError`. Reproduced:

```
[{"results": [], "provider_name": "x"}, "oops"]   -> AttributeError: 'str' object has no attribute 'get'
{"batches": ["oops"]}                              -> AttributeError
{"batches": "abc"}                                 -> AttributeError (iterates chars)
```

Untrusted stdin/file input should never traceback the CLI.
**Fix:** Validate envelope shape and raise `ValueError` (which the caller
already maps to the clean "invalid results payload" message):

```python
for batch in payload:
    if not isinstance(batch, dict):
        raise ValueError("batch entries must be objects with a 'results' array")
    flat.extend(batch.get("results", []))
```

Apply the same `isinstance(..., dict)` guard to the `payload["batches"]` branch
(and assert `payload["batches"]` is a list).

### WR-02: Factory silently drops `timeout_seconds` and `base_url` from `ProviderConfig`

**File:** `src/construct/llm/factory.py:34-56`
**Issue:** `ProviderConfig` declares `timeout_seconds` and `base_url`
(`config.py:18-19`), but `build_chat_model` threads only `model`,
`temperature`, and `max_tokens` into `ChatAnthropic`/`ChatOpenAI`. Operators who
set `base_url` (self-hosted/proxy endpoints — the main reason that field exists)
or `timeout_seconds` get a silent no-op: the config validates and is ignored.
**Fix:** Pass them through, e.g. `ChatOpenAI(..., timeout=cfg.timeout_seconds,
base_url=cfg.base_url)` and the equivalent kwargs for Anthropic, or remove the
unused fields so config cannot lie about behavior.

### WR-03: `ask.domain` surfaces raw provider exception text in `token_usage`

**File:** `src/construct/llm/ask_domain.py:255-262`
**Issue:** The synthesis node returns `token_usage={"error": str(exc)}` on any
LLM failure. This raw exception string is carried into `AskDomainOutput` and
returned to CLI/MCP clients verbatim — the same provider-internals leakage that
`research_score.py` deliberately sanitizes. Inconsistent and a potential
information-disclosure vector for provider/auth error detail.
**Fix:** Route through a key-safe summarizer (reuse the
`_safe_scoring_cause` pattern) rather than embedding `str(exc)`; record the
exception class name only.

### WR-04: `print()` in `ask.domain` corrupts the MCP stdio JSON-RPC stream

**File:** `src/construct/llm/ask_domain.py:293-294`
**Issue:** `extract_citations` does `print(f"WARNING: cited card IDs not in
retrieved set: {missing}")` to stdout. When `ask.domain` runs under the MCP
stdio server, stdout is the JSON-RPC transport — an unframed `print` corrupts
the protocol stream and can break the tool response whenever the model cites a
card ID outside the retrieved set (a plausible, not exotic, condition).
**Fix:** Use the logging module writing to stderr, or collect the warning into
the structured `retrieval`/output payload instead of printing.

### WR-05: `load_taxonomy_categories` leaves `load_cards()` unguarded

**File:** `src/construct/llm/research_score.py:141-155`
**Issue:** The domains-registry load is defensively wrapped
(`try/except Exception: pass`, lines 144-149) but the subsequent
`loader.load_cards()` loop (line 151) is not. An unparseable/locked card store
therefore aborts the entire gate run with an exception that — per CR-01 —
escapes the shim unsanitized. The asymmetry is also surprising: registry
failure degrades gracefully, card failure is fatal.
**Fix:** Wrap the `load_cards()` iteration in the same defensive guard (taxonomy
is "soft steering", so a load failure should degrade to no categories, not abort
scoring).

### WR-06: Provider-outage substring markers are over-broad → false `total_outage`/`success=False`

**File:** `src/construct/llm/research_score.py:326-343, 462-482`
**Issue:** `_is_provider_outage_cause` classifies via substring match on
`str(exc).lower()` against markers including `"401"`, `"403"`, `"api key"`,
`"unauthorized"`. A non-provider failure whose message merely contains one of
these tokens (e.g. an HTTP 401/403 echoed from a *scraped page*, a "401" token
count, a validation message mentioning "api key") is mistaken for a provider
auth failure. If every item in a batch trips a marker for non-auth reasons,
`score_all` promotes to `total_outage=True` → `OperationResult(success=False)`,
discarding findings that should have been returned as degraded.
**Fix:** Tighten classification — match on exception *type* (auth/permission
error classes) and the explicit `GATE_PROVIDER_ERROR` prefix, and require
word-boundary matches for numeric codes rather than bare substring containment.

## Info

### IN-01: CLI command functions named `list` shadow the builtin (root cause of the `builtins.list` workaround)

**File:** `src/construct/cli.py:690, 855, 460`
**Issue:** `@spike_app.command()` and `@tag_app.command()` both define
`def list(...)` at module scope, rebinding the module global `list` to a Typer
command (verified: `construct.cli.list` is a function, not the builtin). The
`builtins.list` reference at line 460 is a correct and necessary workaround, but
the shadow is a latent footgun — any future bare `list(...)` in this module
breaks silently.
**Fix:** Name the functions descriptively and keep the CLI name explicit, e.g.
`@spike_app.command(name="list")\ndef spike_list(...)`, then drop the
`builtins.list` workaround.

### IN-02: Redundant `GATE_PROVIDER_ERROR` re-check in `_is_provider_outage_cause`

**File:** `src/construct/llm/research_score.py:341-343`
**Issue:** `_PROVIDER_OUTAGE_MARKERS` already contains `"gate_provider_error"`
and the function lowercases the message before matching, so the trailing
`return isinstance(exc, RuntimeError) and "GATE_PROVIDER_ERROR" in str(exc)` is
dead/redundant — the marker loop already returned `True` for that case.
**Fix:** Remove the redundant final check (the marker covers it), or if a
type-narrowed RuntimeError check is intended, make it the sole authority and
drop the string marker.

### IN-03: Anthropic import path unguarded vs. OpenAI; hardcoded `anthropic` fallback

**File:** `src/construct/llm/factory.py:34-41`; `src/construct/llm/research_score.py:510`
**Issue:** The `langchain_openai` branch wraps its import to degrade to a clean
`GATE_PROVIDER_ERROR`, but the `langchain_anthropic` branch imports bare — if
the core dep is ever absent, the user gets a raw `ImportError` instead of the
consistent gate error. Separately, `config.providers["anthropic"]` (research
`run_gate:510`) and the `getattr(..., "anthropic")` defaults assume an
`anthropic` provider always exists; a custom config without it raises `KeyError`
(see CR-01).
**Fix:** Wrap the anthropic import symmetrically, and resolve the provider
fallback via `.get(...)` with an explicit `GATE_PROVIDER_ERROR` when neither the
requested key nor a sane default is present.

---

## Resolution

**Resolved:** 2026-06-28 via `/gsd:code-review 9 --fix` (Critical + Warning scope, single pass).
All 8 Critical and Warning findings were fixed as atomic commits; the 3 Info
findings were left out of scope (IN-02 was incidentally subsumed by the WR-06
rewrite). Test suite went from 289 → **291 passed, 0 skipped** (+2 CR-01
regression tests in `tests/llm/test_research_score_capability.py`).

| Finding | Severity | Status | Commit | Resolution |
|---------|----------|--------|--------|------------|
| CR-01 | critical | ✅ fixed | `0abb5cd` | `_research_score_shim` wraps the whole gate call; pre-flight provider/config errors route through `_safe_scoring_cause` → `OperationResult(success=False, data={"degraded": True, "total_outage": False})`. No CLI traceback, no MCP raw-text leak. |
| CR-02 | critical | ✅ fixed | `d95bd3b` | `ask.domain` cache key now includes `workspace_path`, `max_cards`, and `provider_override` at both read and write sites. |
| WR-01 | warning | ✅ fixed | `adcb267` | `_flatten_search_results_payload` guards each batch element with `isinstance(..., dict)` and asserts `payload["batches"]` is a list, raising `ValueError` (mapped to the clean message). |
| WR-02 | warning | ✅ fixed | `81e1f00` | `build_chat_model` threads `cfg.timeout_seconds`/`cfg.base_url` into `ChatAnthropic` (verified `timeout`/`base_url` against langchain_anthropic 1.4.5) and `ChatOpenAI`. |
| WR-03 | warning | ✅ fixed | `fc5d526` | `ask.domain` synthesis failure records the exception class name only in `token_usage`, never `str(exc)`. |
| WR-04 | warning | ✅ fixed | `89e1d7c` | `extract_citations` logs the missing-citation warning to stderr via `logging` instead of `print()` to stdout. |
| WR-05 | warning | ✅ fixed | `f5ffc05` | `load_taxonomy_categories` wraps the `load_cards()` iteration in the same defensive guard as the registry load. |
| WR-06 | warning | ✅ fixed | `ce8a72f` | `_is_provider_outage_cause` prefers the `GATE_PROVIDER_ERROR` prefix and auth/permission exception types, with word-boundary matching for numeric HTTP codes. |
| IN-01 | info | ⏳ open | — | `list` Typer commands shadow the builtin; the `builtins.list` workaround remains. Tracked tech-debt. |
| IN-02 | info | ✅ subsumed | `ce8a72f` | Redundant `GATE_PROVIDER_ERROR` re-check eliminated by the WR-06 classifier rewrite. |
| IN-03 | info | ⏳ open | — | Unguarded Anthropic import + hardcoded `anthropic` fallback. Tracked tech-debt. |

**Remaining open:** IN-01, IN-03 (Info only). Close with `/gsd:code-review 9 --fix --all`.

---

_Reviewed: 2026-06-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Resolution: 2026-06-28 (gsd-code-fixer, 8/8 Critical+Warning fixed)_
_Depth: standard_
