# Phase 06 — Manual Test Suite

**Phase:** 06-derived-data-ops-ui-governed-spikes
**Purpose:** Step-by-step manual verification of the Phase 06 deliverables that need a human in the loop — primarily the Streamlit ops dashboard (UAT Test 7, blocked from automated verification), plus reproducible CLI checks.
**Companion file:** `06-UAT.md` (automated results for Tests 1–6).

---

## How to use this suite

Each test has: **Goal**, **Setup**, **Steps**, **Expected**, and a **Pass criteria** checkbox.
Run them in order — Part A (CLI) is fast and confirms the data layer; Part B (UI) is the real manual work.

Mark each test **PASS** / **FAIL** / **BLOCKED** as you go. If something fails, note exactly what you saw (verbatim error text or a screenshot) — that becomes a gap entry in `06-UAT.md`.

### Prerequisites (run once)

```bash
cd /Users/mab/dev/mabstruct/construct
.venv/bin/python -c "import streamlit, pydantic, typer; print('deps OK')"
```

- Test workspace used throughout: `test-ws/my-construct`
- The CLI entry point is `.venv/bin/python -m construct.cli` (referred to below as `construct`).
- ⚠️ **Fixture hygiene:** Tests A4 and B4/B5 *write* to the workspace (`search-seeds.json`, `connections.json`, `log/events.jsonl`). Snapshot first and restore after if you want a clean tree:
  ```bash
  cp test-ws/my-construct/search-seeds.json /tmp/seeds.bak
  cp test-ws/my-construct/connections.json /tmp/conns.bak
  # ...restore with: cp /tmp/seeds.bak test-ws/my-construct/search-seeds.json (etc.)
  # or: git checkout -- test-ws/my-construct/
  ```

---

## Part A — CLI manual tests

These mirror what was auto-verified in `06-UAT.md`. Run them to confirm the environment behaves on your machine before driving the UI.

### A1. Views contract validation surfaces structured results
**Goal:** `construct views validate` validates build data against Pydantic contracts and reports per-file results.

**Steps:**
```bash
construct views validate -w test-ws/my-construct
```

**Expected:** A per-file report such as `Views data validation: 0 passed, 1 failed, 3 missing`, listing `bridges.json` with `extra_forbidden` errors on `version` / `generated` / `workspace`, and `domains/articles/stats.json` as missing.

**Pass criteria:**
- [ ] Command runs without crashing and prints a structured per-file report.
- [ ] ⚠️ **Known gap (accepted):** the validation *failure* on `bridges.json` and the missing files are expected — the contract models define the *target* shape while the generator still emits richer data (documented in `06-01-SUMMARY.md`). Mark PASS as long as the report is structured and the command doesn't error out. Flag FAIL only if the command itself crashes or produces no output.

---

### A2. Spike types are listed
**Goal:** `construct spike list` shows the available governed spike types.

**Steps:**
```bash
construct spike list
```

**Expected:** Two entries — `graphify` (ingestion analysis / tag+keyword extraction) and `infranodus` (graph-structure exploration), each with a one-line description.

**Pass criteria:**
- [ ] Both `graphify` and `infranodus` appear with descriptions.

---

### A3. Spike run isolates the workspace and cleans up
**Goal:** `construct spike run` copies the workspace to a temp dir, runs the external tool, captures output, persists a result, and removes the temp copy — even on tool failure.

**Steps:**
```bash
construct spike run graphify -w test-ws/my-construct
ls test-ws/log/spike-results/        # a graphify-<timestamp>.json should exist
ls /private/var/folders/*/T/construct-spike-* 2>/dev/null || echo "temp cleaned ✓"
```

**Expected:** The command reports success or a graceful failure (e.g. "Tool exited with code 1" with captured stdout/stderr if no LLM API key is set). A structured result JSON is written under `log/spike-results/`. No `construct-spike-*` temp directory is left behind.

**Pass criteria:**
- [ ] A result JSON is written under `log/spike-results/`.
- [ ] No leftover temp directory.
- [ ] If the tool is missing or errors, the failure is reported cleanly (no Python traceback).

---

### A4. Tag pipeline extracts as `pending` and respects approval governance (D-08)
**Goal:** Extraction never auto-accepts; only explicit approval reaches `search-seeds.json`.

**Steps:**
```bash
construct tag extract -w test-ws/my-construct
construct tag list -w test-ws/my-construct | head
# pick one id from the list output, then:
construct tag approve <candidate-id> -w test-ws/my-construct
construct tag list --status approved -w test-ws/my-construct
```

**Expected:**
- `tag extract` reports candidates found and writes `log/tag-candidates.json`; every candidate starts `status: pending`.
- `tag list` shows candidates sorted by confidence (highest first).
- `tag approve <id>` reports `Approved 1 tag candidate(s), added 1 search cluster(s)`; the approved candidate flips to `approved` and a new cluster appears in `search-seeds.json`. **Un-approved candidates do NOT appear in `search-seeds.json`.**

**Pass criteria:**
- [ ] All freshly extracted candidates are `pending`.
- [ ] Approving one adds exactly one `SearchCluster` to `search-seeds.json`; the rest stay `pending` and absent from seeds.
- [ ] Restore the fixture afterward (see Prerequisites).

---

## Part B — Streamlit ops dashboard (UAT Test 7)

This is the genuinely manual portion: a local web UI you click through.

### B0. Launch the dashboard
**Goal:** The Streamlit app boots and serves the ops console locally.

**Steps:**
```bash
cd /Users/mab/dev/mabstruct/construct
.venv/bin/streamlit run src/construct/ui/streamlit_app.py
```
Open the URL it prints (default `http://localhost:8501`) in a browser.

**Expected:** The app loads with no Python traceback in the terminal or red error box in the browser. A **left sidebar** shows config controls and the main area shows a navigable set of pages.

**Pass criteria:**
- [ ] App boots without errors and the page renders.

---

### B1. Sidebar configuration
**Goal:** The sidebar lets you point the dashboard at a workspace and set runtime config.

**Steps:**
1. In the sidebar, locate the config inputs.
2. Set **Workspace path** to `test-ws/my-construct` (absolute path is safest: `/Users/mab/dev/mabstruct/construct/test-ws/my-construct`).
3. Confirm the other fields are present: **Install root**, **LLM config path**, and a **provider override** control.

**Expected:** All four controls are present and editable. Changing the workspace path is picked up by the pages (values persist in session as you navigate).

**Pass criteria:**
- [ ] Workspace path, install root, LLM config path, and provider override controls all exist and accept input.
- [ ] The chosen workspace persists when you switch pages.

---

### B2. Dashboard panel (graph health)
**Goal:** The Dashboard page reads the workspace directly and shows graph health.

**Steps:**
1. Navigate to the **Dashboard** page.
2. Inspect the four areas:
   - **Key metrics row** — total cards, total connections, total domains.
   - **Cards by domain** — a table grouping cards by their `domain` field.
   - **Connections by type** — a table grouping `connections.json` by `type`.
   - **Recent events** — the last ~20 entries from `log/events.jsonl` (timestamp / action / agent / target / result).

**Expected:** Metrics show non-zero counts consistent with the fixture; the two tables render with rows; recent events list the latest activity. Pointing at a missing/empty workspace shows a friendly `st.error()` / `st.info()` message rather than a crash.

**Pass criteria:**
- [ ] Three metrics render with plausible counts.
- [ ] "Cards by domain" and "Connections by type" tables render.
- [ ] Recent events list shows entries (your Part A runs should appear near the top).
- [ ] An invalid workspace path produces a friendly message, not a traceback. *(Optional: type a bogus path to confirm.)*

---

### B3. Capability Runner panel
**Goal:** Execute a registry capability from the UI via a dynamically generated form.

**Setup:** 17 capabilities are registered. Good low-risk choices to test: **`workspace.status`** or **`graph.status`** (read-only, no writes).

**Steps:**
1. Navigate to the **Capability Runner** page.
2. Open the capability dropdown — confirm it is populated (e.g. `ask.domain`, `bridge.detect`, `graph.status`, `views.generate_data`, `workspace.status`, …).
3. Select **`workspace.status`**.
4. Observe the **form fields auto-generated from the capability's input schema** (e.g. a workspace-path field). Field widget types should match the schema: text → text input, int → number input, bool → toggle, enum → selectbox.
5. Fill the workspace path and click **Run**.
6. Inspect the results area: syntax-highlighted JSON output plus status / duration / error-count chips.

**Expected:** The form reflects the selected capability's schema; running a read-only capability returns a JSON result with a success status and a duration. The last few results persist when you navigate away and back.

**Pass criteria:**
- [ ] Dropdown is populated from the registry.
- [ ] Selecting a capability regenerates the form fields to match its schema.
- [ ] Running `workspace.status` (or `graph.status`) returns JSON + status/duration chips.
- [ ] *(Known limitation)* Some capabilities with positional-only handler signatures may show a graceful `TypeError` hint instead of running — that is expected for the spike (documented in `06-02-SUMMARY.md`), not a failure of this test.

---

### B4. Gate Review — Ask.Domain Q&A tab
**Goal:** Review and approve/reject pending Q&A items, with events logged.

**Note:** The Q&A queue is populated from `st.session_state.gate_queue`. If you haven't run an `ask.domain` capability this session, the queue may be empty. To populate it, run **`ask.domain`** from the Capability Runner first (B3), then return here.

**Steps:**
1. Navigate to **Gate Review** → **Ask.Domain Q&A** tab.
2. For a pending item, expand it to see: the answer markdown, expandable **citations** (card ID / snippet / path), and provider/model metadata.
3. Click **Approve** on one item and **Reject** on another (if available).
4. Switch to the Dashboard's recent-events list (or `tail log/events.jsonl`) to confirm `gate_review_approved` / `gate_review_rejected` events were logged.

**Expected:** Pending items render with citations and metadata; approve/reject buttons resolve the item and write the corresponding event.

**Pass criteria:**
- [ ] A pending Q&A item shows answer + citations + provider/model metadata.
- [ ] Approve and Reject each resolve the item and log an event (`gate_review_approved` / `gate_review_rejected`).
- [ ] If the queue is empty, note it as **BLOCKED — no Q&A data** (run `ask.domain` to populate, or skip).

---

### B5. Gate Review — Bridge Candidates tab
**Goal:** Review bridge candidates and approve one into a typed connection.

**⚠️ Data prerequisite:** The fixture's `log/bridge-candidates.json` currently has an **empty `bridges` array** — this tab will show *no candidates* as-is. To get test data, run bridge detection first:
```bash
construct bridge detect -w test-ws/my-construct    # populates bridge candidates
```
(Confirm the exact subcommand via `construct bridge --help`.)

**Steps:**
1. After populating candidates, navigate to **Gate Review** → **Bridge Candidates** tab.
2. Confirm candidates are grouped by band: **strong / medium / weak**.
3. For one candidate, inspect source → target, score, rationale, and shared categories.
4. Click **Approve** on one candidate.
5. Click **Reject** on another.

**Expected:**
- **Approve** creates a connection via the `knowledge.connection.add` capability with `ConnectionType.parallels` and `ConnectionAuthor.construct` — the new connection appears in `connections.json` and a connection event is logged.
- **Reject** marks the candidate reviewed (session state) and logs an event.

**Pass criteria:**
- [ ] Candidates render grouped by strong/medium/weak with score + rationale.
- [ ] Approve adds a `parallels` connection to `connections.json` and logs an event.
- [ ] Reject marks the candidate reviewed and logs an event.
- [ ] If you can't populate candidates, note as **BLOCKED — no bridge data**.
- [ ] Restore `connections.json` / `log/events.jsonl` afterward if you snapshotted.

---

## Result rollup

After running, record outcomes back into `06-UAT.md` (Test 7 in particular). Suggested rollup:

| Test | Area | Result | Notes |
|------|------|--------|-------|
| A1 | views validate | | known gap accepted? |
| A2 | spike list | | |
| A3 | spike run isolation | | |
| A4 | tag governance (D-08) | | |
| B0 | dashboard launch | | |
| B1 | sidebar config | | |
| B2 | dashboard panel | | |
| B3 | capability runner | | |
| B4 | gate review — Q&A | | data-dependent |
| B5 | gate review — bridges | | data-dependent |

**When Part B passes:** update `06-UAT.md` Test 7 `result: blocked` → `result: pass`, set Summary `blocked: 0`, and the phase becomes eligible to mark complete (then `/gsd-complete-milestone` for v0.3).
