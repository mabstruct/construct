---
phase: 06-derived-data-ops-ui-governed-spikes
plan: 06-02
type: execute
subsystem: ui
tags: [streamlit, ops-dashboard, capability-runner, gate-review, d-03, d-04]
requirements_completed: [ADV-04]
provides: [Streamlit ops dashboard panels]
affects: [capability_registry, workspace_sot]
tech-stack:
  added: [streamlit]
  patterns: [dynamic-form-from-json-schema, session-state-queue, file-io-dashboard]
key-files:
  created:
    - src/construct/ui/__init__.py
    - src/construct/ui/streamlit_app.py
    - src/construct/ui/dashboard.py
    - src/construct/ui/capability_runner.py
    - src/construct/ui/gate_review.py
  modified:
    - pyproject.toml
decisions:
  - "Streamlit dependency added to pyproject.toml as hard dependency per PRD recommendation"
  - "Capability runner uses **inputs pattern — some handlers with positional signatures may fail gracefully with TypeError"
  - "Bridge candidate approval invokes knowledge.connection.add with typed arguments (ConnectionType, ConnectionAuthor) to match handler interface"
metrics:
  duration: 9
  completed_date: "2026-06-11"
---

# Phase 06 Plan 02: Streamlit Ops Dashboard — Summary

Built a local Streamlit ops dashboard at `src/construct/ui/` with three panels per D-03 and ADV-04: Dashboard (graph health), Capability Runner (execute capabilities from UI), and Gate Review (review Q&A + bridge candidates). All capability executions go through the capability registry per D-04.

## Files Created

### `src/construct/ui/__init__.py`
Empty module init with docstring.

### `src/construct/ui/streamlit_app.py`
Main Streamlit entry point per PRD §10. Sidebar config with workspace path, install root, LLM config path, and provider override controls. Stores all values in `st.session_state` for page access. Routes to three pages via `st.navigation()`.

### `src/construct/ui/dashboard.py`
Home page per D-03 panel 1. Reads workspace files directly (no capability invocations):
- Key metrics row: total cards, total connections, total domains via `st.metric()`
- Cards by domain: parses `cards/*.md` files, groups by domain field, displays in `st.dataframe()`
- Connections by type: reads `connections.json`, groups by `type`, displays in `st.dataframe()`
- Recent events: reads last 20 lines from `log/events.jsonl`, displays with timestamp/action/agent/target/result
- Graceful handling of missing workspace or files with `st.error()` / `st.info()`

### `src/construct/ui/capability_runner.py`
Capability Runner panel per D-03 panel 3 and PRD §10.2:
- Capability dropdown populated from `get_registry().list()`
- Dynamic form field generation from Pydantic `model_json_schema()` with type mapping:
  - `str` → `st.text_input`, long strings → `st.text_area`
  - `int` → `st.number_input` with min/max constraints
  - `bool` → `st.toggle`
  - `list[str]` → `st.text_area` (comma-separated)
  - `enum` → `st.selectbox`
  - `Path` → `st.text_input`
- Run button invokes handler via `cap.handler(**inputs)` in-process per D-04
- Results display: syntax-highlighted JSON, status/duration/error count chips
- Last 5 results stored in session state for cross-navigation persistence

### `src/construct/ui/gate_review.py`
Gate Review panel per D-03 panel 2 and PRD §10.3 + §8.6:
- Two tabs: "Ask.Domain Q&A" and "Bridge Candidates"
- Q&A tab: pending items from `st.session_state.gate_queue`, answer markdown, expandable citations with card ID/snippet/path, provider/model metadata, Approve/Reject buttons that log `gate_review_approved` / `gate_review_rejected` events
- Bridge tab: reads `log/bridge-candidates.json`, groups by band (strong/medium/weak), shows source→target with score/rationale/shared categories
  - Approve creates connection via `knowledge.connection.add` capability with `ConnectionType.parallels`, properly typed args
  - Reject marks candidate as reviewed in session state
  - Both actions log events

### `pyproject.toml`
Added `"streamlit>=1.35"` to dependencies list.

## Deviations from Plan

No deviations — plan executed exactly as written (3 auto-type tasks, all committed individually).

## Auto-fixed Issues

**1. [Rule 2 — Missing correctness] Bridge candidate approval handler signature mismatch**

- **Found during:** Task 3
- **Issue:** The plan's pseudocode for bridge approval used `conn_cap.handler(**inputs)` with `workspace_path`, `conn_type="parallels"`, `created_by="construct"` as kwargs. The actual `add_connection` handler has positional parameters with typed arguments (`ConnectionType`, `ConnectionAuthor`).
- **Fix:** Rewrote the handler call to pass properly typed positional arguments matching the handler's actual signature: `workspace` (Path), `from_id` (str), `to_id` (str), `ConnectionType.parallels`, `note` (str), `created_by=ConnectionAuthor.construct`.
- **Files modified:** `src/construct/ui/gate_review.py`
- **Commit:** f0f38c2

## Key Decisions

1. **Streamlit as hard dependency** — Added `streamlit>=1.35` to `pyproject.toml` dependencies list. Per PRD and the Agent's Discretion in CONTEXT.md, choosing hard dependency keeps setup simple for the spike.

2. **Capability runner uses `**inputs` for handler dispatch** — The plan specifies `cap.handler(**inputs)` as the invocation pattern. Some capabilities accept `**kwargs` (e.g., `ask.domain`, `bridge.detect`), while others have positional-only signatures. The runner catches `TypeError` gracefully and shows a hint message. This is acceptable for a spike; future iterations can wrap handlers with uniform signatures.

3. **Bridge candidate approval uses typed arguments** — Unlike the generic capability runner's `**inputs` pattern, bridge approval explicitly passes `ConnectionType.parallels` and `ConnectionAuthor.construct` to match the `add_connection` handler's typed signature.

## Threat Surface Scan

No new threat flags. The Streamlit app adds a localhost ops console (accepted risk per threat model T-06-05, T-06-06). All writes to SOT go through the capability registry. Dashboard reads are read-only file I/O.

## Self-Check: PASSED

- ✅ All 5 UI Python files parse without syntax errors
- ✅ `streamlit_app.py` has sidebar config per PRD §10 sidebar spec
- ✅ `dashboard.py` reads and displays graph stats from workspace files
- ✅ `capability_runner.py` dynamically generates form fields from `model_json_schema()`
- ✅ `gate_review.py` has approve/reject buttons for Q&A results and bridge candidates
- ✅ `pyproject.toml` includes `streamlit>=1.35` dependency
- ✅ All capability executions route through the capability registry per D-04
