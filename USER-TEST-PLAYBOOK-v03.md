# USER TEST PLAYBOOK — CONSTRUCT v0.3

**Purpose:** Smoke-test the main features delivered by the v0.3 milestone ("Claude-Native
Runtime & Workflow Hardening") from a real user's perspective, in a fresh workspace, using
the shipped `construct` CLI, MCP server, and Streamlit ops UI.

**Scope:** Happy-path verification that each headline capability *works end-to-end and
persists correctly* — not exhaustive QA. Each test states a goal, the exact command, the
expected result, and a pass criterion.

- **Version under test:** `construct` 0.3.0
- **Milestone reference:** `.planning/MILESTONES.md`, `.planning/milestones/v0.3-ROADMAP.md`
- **Est. time:** ~20–30 min (≈10 min if you skip the LLM-backed and UI sections)

---

## 0. Prerequisites & setup

### 0.1 Tooling

| Requirement | Why | Check |
|-------------|-----|-------|
| Python ≥ 3.11 | Runtime | `python --version` |
| `construct` installed | CLI under test | `construct --version` → `0.3.0` |
| `ANTHROPIC_API_KEY` | Needed **only** for §6 (`ask domain`) and L3 of `bridge detect` | `echo $ANTHROPIC_API_KEY` |
| Ollama (optional) | `lightweight` routing tier; not required for this playbook | — |

If `construct` is not on your PATH, use the project venv:

```bash
cd /Users/mab/dev/mabstruct/construct
source .venv/bin/activate
construct --version        # expect: 0.3.0
```

> **LLM note:** Routing is defined per-workspace in `.construct/model-routing.yaml`
> (frontier/workhorse → `anthropic`, lightweight → `ollama`). Only §6 requires a live key.
> All other sections are deterministic and run offline.

### 0.2 Create a fresh smoke workspace

Do **not** test against `test-ws/` — those are committed fixtures. Use a throwaway dir.

```bash
export WS="$HOME/construct-smoke"
rm -rf "$WS"            # only if re-running this playbook
construct init "$WS"
```

`init` prompts interactively. Suggested answers:

| Prompt | Answer |
|--------|--------|
| Domain slug | `ai-gateways` |
| Display name | `AI Gateways` |
| Scope/description | `API gateways in the age of AI` |
| Taxonomy seeds (comma-separated) | `routing, auth, observability` |
| Source priorities (comma-separated) | `papers, vendor-docs` |
| Research seeds (comma-separated) | `llm proxy, semantic caching` |

**Expected:** `Initialized CONSTRUCT workspace at <path>`

**Pass:** Command exits 0 and the workspace tree exists:

```bash
ls "$WS"               # expect: domains.yaml, governance.yaml, search-seeds.json,
                       #         connections.json, cards/, refs/, digests/, log/, .construct/
```

> Throughout, commands take `-w "$WS"` (or `--workspace`). The domain id `ai-gateways`
> created above is referenced by later card/ask steps.

---

## 1. Workspace contract & governance (Phase 1)

**Feature:** Canonical Claude-native workspace contract with pre-write validation, plus
`validate` / `status` introspection.

### 1.1 Validate a clean workspace

```bash
construct validate "$WS"
```

**Expected:** `Validation complete: 0 error(s), N warning(s)`
**Pass:** Exit code 0, zero errors.

### 1.2 Inspect ownership categories

```bash
construct status "$WS"
```

**Expected:** A list of canonical / support / derived artifacts each marked `[present]` or
`[missing]`.
**Pass:** Canonical artifacts (domains.yaml, card store, event log) report `present`.

### 1.3 Validation rejects corruption (negative test)

```bash
echo 'not: [valid yaml' >> "$WS/domains.yaml"
construct validate "$WS"; echo "exit=$?"
```

**Expected:** At least one `ERROR ...` line; `exit=1`.
**Pass:** The gate refuses a corrupted canonical artifact. **Then restore:**

```bash
git checkout -- "$WS/domains.yaml" 2>/dev/null || construct init "$WS"   # or recreate WS
```

> If `$WS` is outside the repo, simply `rm -rf "$WS"` and redo §0.2 before continuing.

---

## 2. Governed knowledge operations (Phase 2)

**Feature:** Reliable card and connection CRUD behind validation gates, with event logging
and connection-preserving archive.

### 2.1 Create two cards

```bash
construct knowledge card create -w "$WS" \
  --title "Semantic caching cuts gateway latency" \
  --type finding --domains ai-gateways \
  --confidence 3 --source-tier 2 \
  --summary "Caching embeddings at the gateway reduces repeat-LLM-call latency."

construct knowledge card create -w "$WS" \
  --title "Token-based rate limiting" \
  --type concept --domains ai-gateways \
  --confidence 4 --source-tier 2 \
  --summary "Rate limit on token budget rather than request count for LLM traffic."
```

**Expected:** `✓ ...` success line for each, including the new card id (note both ids).
**Pass:** Two cards created; capture `CARD_A` and `CARD_B` ids for the next steps.

> Valid `--type` values: `finding, claim, concept, method, paper, theme, gap, provocation,
> question, connection`. `--confidence`/`--source-tier` are 1–5.

### 2.2 Edit a card

```bash
construct knowledge card edit <CARD_A> -w "$WS" --confidence 4 --lifecycle growing
```

**Expected:** `✓ ...` with the updated fields.
**Pass:** Re-running with `--json` shows `confidence: 4`, `lifecycle: growing`.

### 2.3 Add a typed connection

```bash
construct knowledge connection add <CARD_A> <CARD_B> -w "$WS" \
  --type supports --note "Caching complements token budgeting"
```

**Expected:** `✓ ...` connection created.
**Pass:** Exit 0.

> Valid `--type` values: `supports, contradicts, extends, parallels, requires, enables,
> challenges, inspires, gap-for`.

### 2.4 List connections

```bash
construct knowledge connection list -w "$WS"
construct knowledge connection list -w "$WS" --card <CARD_A>
```

**Expected:** The `supports` edge between the two cards appears in both outputs.
**Pass:** Edge present; card filter returns only edges touching `CARD_A`.

### 2.5 Archive preserves connections

```bash
construct knowledge card archive <CARD_B> -w "$WS"
construct knowledge connection list -w "$WS" --include-archived
```

**Expected:** Archive succeeds; the connection is still listed with `--include-archived`.
**Pass:** Connection survives archival (Phase 2 decision D-06).

### 2.6 Event log captured the operations

```bash
ls "$WS/log/"          # expect an events/event-log file
```

**Pass:** An event log exists and has grown since §0 (init + creates + edit + archive logged).

---

## 3. Capability registry, CLI & MCP spine (Phase 3)

**Feature:** One shared capability registry behind both the CLI and a stdio MCP server.
Everything above already exercised the registry via the CLI; this section confirms the
**MCP surface** starts and exposes tools.

### 3.1 MCP stdio server starts

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | construct mcp
```

**Expected:** A JSON-RPC response listing tools auto-registered from the registry
(e.g. `workspace.validate`, `knowledge.card.create`, `ask.domain`, `bridge.detect`, …).
**Pass:** Server responds with a non-empty tool list and exits when stdin closes.

> Real agent clients speak a full MCP handshake; the one-shot pipe above is just a liveness
> smoke check. If your client needs initialize-first, register the server as:
> `command: construct, args: ["mcp"]`.

---

## 4. Ingestion (Phase 4)

**Feature:** `construct ingest source` turns a file / URL / note / web-research query into a
ref (and seed cards) with metadata, routed to a domain.

### 4.1 Ingest a local note

```bash
construct ingest source "Gateways increasingly embed LLM routing logic." -w "$WS" \
  --domain ai-gateways --title "Gateway LLM routing note" \
  --tier 3 --finding "Routing logic is moving into the gateway layer" \
  --category trend
```

**Expected:** `✓ ...` with the created ref id.
**Pass:** A new file appears under `"$WS/refs/"`.

### 4.2 Ingest a file

```bash
echo "Notes on semantic caching benchmarks." > /tmp/smoke-source.txt
construct ingest source /tmp/smoke-source.txt -w "$WS" --domain ai-gateways --tier 2
```

**Expected:** `✓ ...` ref created from the file.
**Pass:** Second ref present under `"$WS/refs/"`.

> `ingest source` also accepts a URL or `research:<query>` form. The `research:` form invokes
> the web-research pipeline and is **out of scope** for an offline smoke test — skip unless
> you want to test live research.

---

## 5. Guided workflow operability (Phase 4)

**Feature:** State-aware next-step suggestions (`help --suggest`) and a `WorkflowRunner` with
persisted state + resume-from-last-successful-step.

### 5.1 Workspace-aware suggestion

```bash
construct help --suggest -w "$WS"
```

**Expected:** A suggested next action grounded in current workspace state (e.g. "extract
tags", "run curation-cycle", "detect bridges").
**Pass:** Output is a concrete, state-aware suggestion (not a generic help dump).

### 5.2 Run a workflow

```bash
construct workflow run curation-cycle -w "$WS"
construct workflow status -w "$WS"
```

**Expected:** `run` reports step progress and a result; `status` reports the active/last
workflow and completed-step count.
**Pass:** Workflow executes and state is persisted (status reflects it).

> Per the v0.3 audit, some `curation-cycle` steps are intentional **no-ops** carried as v0.4
> tech debt. The pass criterion here is *workflow orchestration + state persistence + resume
> wiring*, not full curation behavior.

### 5.3 Resume

```bash
construct workflow resume -w "$WS"
```

**Expected:** Resumes from the last saved state (or reports nothing to resume if complete).
**Pass:** Command returns a coherent resume result without re-running completed steps.

---

## 6. Grounded synthesis & graph reasoning (Phase 5) — requires `ANTHROPIC_API_KEY`

**Feature:** Bounded, citation-backed Q&A over a domain's cards (`ask domain`) and
cross-domain bridge detection (`bridge detect`).

> **Skip this section if you have no API key.** These are the only LLM-backed steps.

### 6.1 Grounded domain Q&A

```bash
construct ask domain -w "$WS" -d ai-gateways \
  -q "How can a gateway reduce LLM latency and control cost?"
```

**Expected:** A synthesized answer that **cites the cards** from §2, with a confidence score;
hedges or declines if grounding is weak.
**Pass:** Answer references real card ids/titles (grounded, not hallucinated) and includes
citations + confidence.

### 6.2 Bridge detection

```bash
construct bridge detect -w "$WS"
cat "$WS/log/bridge-candidates.json"
```

**Expected:** L1→L2→L3 pipeline runs and writes `log/bridge-candidates.json`.
**Pass:** The candidates file is written and is valid JSON. (A single-domain smoke workspace
may legitimately yield **0** cross-domain bridges — that is still a pass; the deliverable is
the pipeline + artifact, not a non-empty result.)

---

## 7. Derived data & ops UI (Phase 6)

**Feature:** Pydantic data contracts for the 8 view files (`views validate`) and a local
Streamlit ops dashboard.

### 7.1 Validate view data contracts

```bash
construct views validate -w "$WS"
```

**Expected:** `Views data validation: P passed, F failed, M missing`, one line per file.
**Pass:** **0 failed.** `missing` is acceptable for a fresh workspace whose generator hasn't
emitted every view yet (missing ≠ failure, by design). Any `✗ fail` line is a defect.

> `views.generate_data` is a known v0.4 stub (audit tech debt), so some files may be
> `missing`. This test validates the **schema gate**, which must never pass malformed data.

### 7.2 Streamlit ops dashboard (manual / interactive)

```bash
streamlit run src/construct/ui/streamlit_app.py
```

Then in the browser sidebar set **Workspace path** to your `$WS` and check the three panels:

| Panel | Expected |
|-------|----------|
| 📊 Dashboard | Card / connection / domain counts and recent events for `$WS` |
| ⚡ Capability Runner | Lists registry capabilities; can execute one via a generated form |
| 🔍 Gate Review | Shows `ask.domain` Q&A results / bridge candidates for review |

**Pass:** All three panels load; counts match what you created (≈1–2 cards, 1 connection,
1 domain); a capability run from the Runner succeeds. **No source-of-truth writes from the
UI** — it goes through the registry only.

---

## 8. Governed spikes & tag extraction (Phase 6)

**Feature:** Isolated, governed external-tool spikes, plus hybrid tag extraction where
candidates are **never auto-accepted**.

### 8.1 List spikes

```bash
construct spike list
```

**Expected:** Registered spike types (e.g. `graphify`, `infranodus`) with descriptions.
**Pass:** Non-empty list.

> `construct spike run <tool>` copies the workspace to an isolated dir and invokes an external
> binary. Skip the actual run unless the tool binary is installed — `spike list` is sufficient
> for a smoke test.

### 8.2 Extract tag candidates

```bash
construct tag extract -w "$WS"
construct tag list -w "$WS" --status pending
```

**Expected:** Candidates extracted from `refs/*.json` and written to
`log/tag-candidates.json`; `list` shows them as **pending**.
**Pass:** Candidates exist and are **pending** (not auto-approved — decision D-08).

### 8.3 Approve a candidate (human-gated)

```bash
construct tag approve <CANDIDATE_ID> -w "$WS"
construct tag list -w "$WS" --status approved
```

**Expected:** Only the explicitly approved id moves to `approved` and is written to
`search-seeds.json`.
**Pass:** Approval is explicit and isolated; un-approved candidates stay pending.

---

## 9. Cross-cutting: machine-readable output

Every data command supports `--json` / `-j` for agent/UI consumption.

```bash
construct knowledge connection list -w "$WS" --json
construct views validate -w "$WS" --json
```

**Pass:** Output is well-formed JSON suitable for programmatic use.

---

## 10. Teardown

```bash
rm -rf "$WS" /tmp/smoke-source.txt
```

---

## Results summary

Record outcomes as you go:

| # | Feature (phase) | Result | Notes |
|---|-----------------|--------|-------|
| 0 | Setup & init (P1) | ☐ pass / ☐ fail | |
| 1 | Validate / status / negative (P1) | ☐ / ☐ | |
| 2 | Card + connection CRUD, archive, events (P2) | ☐ / ☐ | |
| 3 | MCP stdio server (P3) | ☐ / ☐ | |
| 4 | Ingestion (P4) | ☐ / ☐ | |
| 5 | help --suggest + workflow run/resume (P4) | ☐ / ☐ | |
| 6 | ask domain + bridge detect (P5) | ☐ / ☐ / ☐ skipped (no key) | |
| 7 | views validate + Streamlit UI (P6) | ☐ / ☐ | |
| 8 | spike list + tag extract/approve (P6) | ☐ / ☐ | |
| 9 | --json output (cross-cutting) | ☐ / ☐ | |

**Known-acceptable observations (v0.4 carry-over, not failures):** some `curation-cycle`
steps are no-ops; some `views` files report `missing` because `views.generate_data` is a
stub; views/spike/tag groups currently bypass the registry (RT-01/RT-02). See
`.planning/milestones/v0.3-MILESTONE-AUDIT.md`.
