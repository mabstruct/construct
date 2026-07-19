# Phase 14: Durable-State & Config Truth - Research

**Researched:** 2026-07-19
**Domain:** Documentation truth reconciliation + one Streamlit sidebar correction (no new runtime capability)
**Confidence:** HIGH — every claim below was read from disk in this session

## Summary

This is a documentation-truth phase with a very small code footprint. CONTEXT.md (D-01…D-12) has already locked every substantive decision; the purpose of this research is to hand the planner the **exact current on-disk state** of each edit target so tasks can be written as concrete, greppable before/after assertions rather than prose intentions.

All six ground-truth targets were verified directly. The good news: the edit surface is narrower and safer than feared. `tests/contract/test_doc_command_references.py` — the only doc-scanning test in the suite — scans **only** `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md`, `CONSTRUCT-CLAUDE-impl/construct/workflows/*.md`, and `USER-TEST-PLAYBOOK-v03.md`. It does **not** scan `CONSTRUCT-CLAUDE-spec/`. Every document this phase edits, plus the new `adr-0004`, is outside that glob set, so criterion 5 is a pure non-regression check: the suite cannot be perturbed by the doc edits at all. Baseline is **exactly 439 tests collected**, and no test in the repository imports Streamlit or touches `src/construct/ui/`.

The one genuine surprise is a gap in D-10's mechanism. `src/construct/llm/config.py` exposes **no public path-resolution API** — `load_llm_config()` returns an `LlmConfig` object, and the resolution order (explicit arg → `CONSTRUCT_LLM_CONFIG` → `DEFAULT_CONFIG_PATH`) is inlined in its body at lines 70-76. There is no function the Streamlit sidebar can call to *display the effective path*. D-10 requires calling into `config.py` so the two cannot drift; satisfying that literally requires extracting a small resolver. See "Open Questions" Q1 — this is the single decision the planner must make that CONTEXT.md did not anticipate.

Three line-number corrections and two stale-adjacent findings are documented below; all are cheap to absorb if caught at plan time and expensive if caught at execution time.

**Primary recommendation:** Structure the phase as four independent edit groups (adr-0004 → nfrs/architecture citations → workspace-contract/config-topology deprecation fence → Streamlit) with the ADR first, since D-07 makes it the anchor the other two documents cite. Extract `resolve_llm_config_path()` in `config.py` as a pure refactor of existing inlined logic, and have `load_llm_config` call it — that keeps D-10's drift-proofing honest without adding capability.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Durable-state decision record (`adr-0004`) | Spec / docs (`CONSTRUCT-CLAUDE-spec/adrs/`) | — | ADRs are the project's decision-record tier; `nfrs.md` and `architecture-overview.md` cite, never duplicate |
| Invariant correction (`nfrs.md` §2, `architecture-overview.md` §8.2) | Spec / docs | — | Normative claims about the system; no code enforces them |
| Workspace artifact listing (`workspace-contract.md`) | Spec / docs | Schema (`schemas/workspace.py`) is the *enforcer*, untouched per D-12 | Doc describes what schema enforces; adding doc rows does not change enforcement |
| `model-routing.yaml` deprecation notes | Spec / docs | — | D-01 keeps scaffolding intact; this is annotation only |
| LLM config path resolution | Python runtime (`llm/config.py`) | — | Already the authority; the UI must defer to it, not restate it |
| Effective-path display | Streamlit UI (`ui/streamlit_app.py`) | reads from `llm/config.py` | Presentation tier; read-only per D-10, no writes, no behavior |

**Tier discipline note for the planner:** every task in this phase lands in exactly one of two tiers — spec docs, or the UI/config seam. Per CONTEXT.md `<specifics>`, a task that finds itself editing `schemas/`, `storage/`, or `services/` has drifted out of scope. The one permitted exception is the `llm/config.py` refactor discussed in Q1, which is a same-tier extraction, not a cross-tier change.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `.construct/model-routing.yaml` is **kept scaffolded and marked deprecated** — not removed from `services/init.py`. Recorded fate: the runtime's LLM configuration authority is `src/construct/llm/config.yaml`, resolved by `llm/config.py` (explicit arg → `CONSTRUCT_LLM_CONFIG` → packaged default); `model-routing.yaml` is inert and retained only for workspace-contract stability. **Reversal rationale — do not re-litigate:** it is a `REQUIRED_PATHS` entry with a loader, validation branch, generated WORKSPACE.md prose, a golden fixture entry, and ~12 assertions across 5 test files. Removing it properly is a workspace-format change, which v0.4.1 lists Out of Scope.
- **D-02: Edit fence.** Deprecation notes go **only** in: `workspace-contract.md:78`, `config-topology.md:56` and `:135`, and `nfrs.md:72`. **Do not touch** `AGENTS.md:91,134`, `USER-TEST-PLAYBOOK-v03.md:36`, `spec-v04-agentworkflows.md:211,557`, `migrations/phase-1-workspace-contract-migration.md`.
- **D-03:** `config-topology.md` is edited now despite Phase 17 (DOC-02) possibly rewriting it wholesale. Record the collision in the plan. **No cross-phase dependency** — Phase 14 must not block on Phase 17.
- **D-04:** `nfrs.md` §2's Rebuild-guarantee row becomes a **scoped invariant** — the guarantee holds for **knowledge state** (`cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`, `digests/`). Workflow orchestration state is explicitly carved out: `.construct/workflow/*.sqlite` holds **pending human-review decisions not reconstructible from layer 1**. Losing it costs a completed search+scoring cycle and any entered decisions; it never corrupts canonical knowledge. Deliberately stronger than Phase 10 D-02's framing; the stronger claim is canonical.
- **D-05:** `nfrs.md` §2's "The 'No Hidden State' Advantage" is **rewritten scoped to knowledge state, not deleted** — markdown-as-truth portability is still true and `adr-0001` depends on it.
- **D-06:** `architecture-overview.md`'s database anti-pattern is **kept, with an explicit named carve-out** for workflow orchestration state pointing at `adr-0004`. Rule and sanctioned exception must appear in the same place.
- **D-07:** The decision is recorded in a **new `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-*.md`** following the Nygard format of `adr-0001..0003`. Both `nfrs.md` §2 and `architecture-overview.md` §8.2 cite it. Chosen over an Amendment C to `adr-0003` on discoverability grounds.
- **D-08:** `nfrs.md` §4's "Third-party APIs: None" is a **standalone correction**, not folded into `adr-0004`. Name Tavily and its data-egress implication.
- **D-09:** `adr-0004` records that it **discharges Phase 10 D-02's deferred action**. **Archived milestone documents under `.planning/milestones/` are NOT edited.**
- **D-10:** `streamlit_app.py`'s `st.text_input("LLM config path", ...)` becomes a **read-only display of the effective resolved path**, computed by calling into `llm/config.py`'s resolution order so `CONSTRUCT_LLM_CONFIG` is honored. It must **not** be an editable control.
- **D-11:** `provider_override` receives the **same treatment**, recorded as a deliberate scope extension.
- **D-12:** Add `.construct/workflow/*.sqlite`, `.construct/search.yaml`, and `WORKSPACE.md` to `workspace-contract.md`'s artifact tables. **Planner's call:** whether `.construct/workflow/*.sqlite` lands under existing **Support artifacts** or warrants a new durable-state artifact class. If a new class is introduced, `adr-0004` must define it.

### Claude's Discretion

- Exact `adr-0004` filename slug, title wording, and Options-Considered content (must follow `adr-0001..0003` format).
- Precise replacement prose for the `nfrs.md` §2 rebuild-guarantee row and rewritten "No Hidden State" bullets, provided D-04's scoped-invariant substance and the non-reconstructibility claim survive intact.
- Wording of the deprecation notes in the four D-02 fence targets.
- Streamlit rendering mechanism for the read-only display (`st.caption` / `st.text_input(disabled=True)` / `st.code`) and how it imports the resolver without a circular import.
- Classification/placement of `.construct/workflow/*.sqlite` within `workspace-contract.md`.
- Whether `adr-0004` covers `curation-run.sqlite` alongside `research-run.sqlite` in one decision or treats the pattern generically.

### Deferred Ideas (OUT OF SCOPE)

- **Actually deleting `model-routing.yaml`** — a workspace-format change. Candidate for v0.5 or a dedicated cleanup phase.
- **Wiring the Streamlit sidebar controls to real behavior** — new runtime capability; v0.5.
- **`AGENTS.md:91,134`, `USER-TEST-PLAYBOOK-v03.md:36`, `spec-v04-agentworkflows.md:211,557`, `migrations/phase-1-workspace-contract-migration.md`** — stale model-routing references outside the fence; Phase 16/17.
- **Event vocabulary reconciliation** — no overlap with Phase 14's edit set; **do not touch here**.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-03 | Durable-checkpointer decision recorded as intentional architectural change; `.construct/workflow/*.sqlite` holds pending human-review decisions not reconstructible from layer 1; contradicting invariants in `nfrs.md` §2 and `architecture-overview.md:243` updated; `nfrs.md` §4 "Third-party APIs: None" corrected for Tavily; `.construct/workflow/*.sqlite`, `.construct/search.yaml`, `WORKSPACE.md` added to `workspace-contract.md`. **Gates v0.5 design.** | Exact current wording + line numbers of all five claims captured below (§"Current On-Disk State"). Non-reconstructibility claim independently re-verified against `research_run.py` control flow (§"Evidence for D-04"). ADR format captured from `adr-0001..0003`. |
| FIX-02 | Exactly one authoritative LLM config location; Streamlit default points at the file the runtime actually reads; `model-routing.yaml`'s fate decided and recorded in docs that describe it as authoritative. | `llm/config.py` resolution order captured verbatim (lines 49-83); the missing path-resolution API identified (Q1); `streamlit_app.py:24-31` captured; dead-write claim independently confirmed by repo-wide grep. All four D-02 fence targets located with exact current text. |

## Current On-Disk State (the planner's edit map)

Everything in this section was read from disk on 2026-07-19. Line numbers are exact as of commit `4a9edb7`.

### `CONSTRUCT-CLAUDE-spec/nfrs.md`

| Line | Current exact text | Decision | Criterion |
|------|-------------------|----------|-----------|
| 37 | `## 2. Reliability` | section anchor | — |
| **43** | `\| Rebuild guarantee \| Workspace files are self-contained — no hidden state \| No databases, no caches, no derived state that's required \|` | D-04 rewrite | 1 |
| **46** | `### The "No Hidden State" Advantage` | D-05 rewrite (heading may stay) | 1 |
| 48 | `Unlike the Python approach, the Claude-native system has no derived state that can get out of sync:` | D-05 — this lead-in is the strongest false claim in the block | 1 |
| 49-52 | `- No SQLite index to rebuild` / `- No NetworkX graph to recompute` / `- No views/ directory to refresh` / `- Everything is in the files — if the files are correct, the system is correct` | D-05 rewrite; **49 and 52 are directly contradicted** by `.construct/workflow/*.sqlite`; 50 and 51 remain true | 1 |
| **72** | `This is identical to any Claude conversation. Users control what's in their workspace. The \`governance.yaml\` and \`model-routing.yaml\` files are informational in the Claude-native approach — Claude handles all tasks.` | D-02 fence target; strengthen "informational" → name `llm/config.yaml` as authority | 4 |
| 76 | `## 4. Privacy` | section anchor | — |
| **83** | `\| Third-party APIs \| None. Web search replaces dedicated API clients. \|` | D-08 correction | 2 |

**Note on line 72:** it bundles `governance.yaml` with `model-routing.yaml`. `governance.yaml` is genuinely load-bearing (a `REQUIRED_PATHS` source-of-truth artifact per `workspace-contract.md:54`), so calling it "informational" is itself questionable — but that is a *separate* untracked defect. Recommend the planner rewrite only the `model-routing.yaml` clause and leave `governance.yaml` alone, to avoid opening scope. Flag it in the plan as an observation. `[VERIFIED: read from disk]`

**Note for D-08 precision:** `.construct/search.yaml`'s template ships `default_provider: mock`, with `tavily` present as a configured-but-not-default provider using `api_key_env: TAVILY_API_KEY`. The honest §4 correction is therefore *"Tavily Search API — optional, opt-in via `.construct/search.yaml`; when enabled, search queries egress to Tavily"*, not *"CONSTRUCT sends your data to Tavily"*. Over-correcting here would trade one false claim for another. `[VERIFIED: CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml]`

### `CONSTRUCT-CLAUDE-spec/architecture-overview.md`

| Line | Current exact text | Decision | Criterion |
|------|-------------------|----------|-----------|
| 6 | `**Related:** \`adrs/adr-0001-...\` · \`adrs/adr-0002-...\` · \`prd.md\` · ...` | should gain `adr-0004`; **already omits `adr-0003`** — see below | 1 |
| 238 | `### 8.2 Anti-patterns to reject` | section anchor | — |
| 240 | `- "Stash this small piece of state in \`views/build/data/\`..."` | **NOT the target** — see line-number correction below | — |
| **243** | `- "Add a database that owns part of the truth" → reconsider. A database is fine as a derived layer (layer 2 sibling) but never as the truth. Markdown stays canonical.` | **D-06 target** — add named carve-out citing `adr-0004` | 1 |
| 249-251 | `### 9.1 Decisions and principles` listing only `adr-0001` and `adr-0002` | must gain `adr-0004`; **already omits `adr-0003`** | 1 |

**⚠ Line-number correction (HIGH confidence, planner must absorb):** CONTEXT.md D-06 and `<canonical_refs>` both say `architecture-overview.md:240`. The database anti-pattern is at **line 243**. Line 240 is the unrelated `views/build/data/` bullet. ROADMAP criterion 1 and REQUIREMENTS DOC-03 both correctly say `:243`. **Use 243.** A task written against 240 would edit the wrong bullet. `[VERIFIED: read from disk]`

**⚠ Pre-existing staleness the planner must decide on:** `§9.1 Decisions and principles` (lines 249-251) lists only `adr-0001` and `adr-0002`. **`adr-0003` is missing**, as is a reference on line 6. This matters because D-07's entire rationale for choosing a new ADR over an Amendment C was *"a v0.5 planner scanning the `adrs/` index must find it by title."* There is **no `README.md` or index file in `CONSTRUCT-CLAUDE-spec/adrs/`** — the directory listing and `§9.1` *are* the index. Adding `adr-0004` to a list that silently drops `adr-0003` produces a list that is still wrong and undermines the stated rationale. **Recommendation:** add both `adr-0003` and `adr-0004` to §9.1 in the same task. This is a one-line addition squarely inside a file the phase already edits for criterion 1, it is not a fence violation (the fence in D-02 governs *model-routing deprecation notes*, not this file), and it is the difference between D-07's rationale being satisfied and merely asserted. Flag as a discretionary micro-scope extension for explicit planner sign-off. `[VERIFIED: read from disk]`

**Additional context for D-06 wording:** the anti-pattern at 243 is downstream of `§4 The Four Invariants` (lines 97-102), which are scoped to **layer 2 only** (I1/I3/I4 all say "to layer 2"). The four invariants are therefore **not** contradicted by `.construct/workflow/*.sqlite`, because workflow checkpoints are not layer 2. This is a useful precedent for D-06's carve-out phrasing: the carve-out can note that workflow orchestration state sits outside the layer 1/2/3 model entirely, rather than violating it. `[VERIFIED: read from disk]`

### `CONSTRUCT-CLAUDE-spec/workspace-contract.md`

Three artifact tables exist:

| Lines | Table | Current members |
|-------|-------|-----------------|
| 48-56 | **Canonical source-of-truth artifacts** | `cards/*.md`, `refs/*.json`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `log/events.jsonl` |
| 62-65 | **Derived artifacts** | `digests/{domain}/digest-{date}.md`, `publish/{slug}.md` |
| 73-78 | **Support artifacts** | `.construct/`, `AGENTS.md`, `.construct/templates/*`, **`.construct/model-routing.yaml` (line 78 — D-02 fence target)** |

Line 78 exact text: `| \`.construct/model-routing.yaml\` | support | Runtime/provider routing guidance; not part of workspace knowledge state |` `[VERIFIED: read from disk]`

**Also relevant to D-12 — the canonical workspace shape tree at lines 21-34:**

```text
workspace/
├── cards/          refs/          connections.json
├── domains.yaml    governance.yaml    search-seeds.json
├── log/events.jsonl   digests/{domain}/   publish/
```

This tree omits **`.construct/` entirely**, `WORKSPACE.md`, `.construct/search.yaml`, `.construct/workflow/`, and — pre-existing drift — **`inbox/`**, which *is* in `REQUIRED_PATHS` (`schemas/workspace.py:24`). D-12 says "artifact tables"; the tree is a fourth location that criterion 2 arguably also covers ("`workspace-contract.md` lists … among workspace artifacts"). **Planner's call**, but recommend updating the tree for the three D-12 artifacts and explicitly *leaving `inbox/` alone* with a note, since fixing `inbox/` is unrelated drift. `[VERIFIED: read from disk]`

**D-12 classification guidance (the "Support vs new class" call):** the three artifacts are not alike:
- `WORKSPACE.md` — generated prose, scaffolded by `services/init.py:161`. Cleanest fit: **Derived**.
- `.construct/search.yaml` — configuration, scaffolded by `services/init.py:59`. Cleanest fit: **Support** (sits naturally beside `model-routing.yaml`).
- `.construct/workflow/*.sqlite` — **neither**. It is not derived (the existing Derived table says "generated from source-of-truth files or workflow execution", and line 67 asserts derived artifacts are never canonical inputs — but checkpoint state *is* the only holder of pending decisions), and calling it Support ("do not define workspace truth", line 71) directly contradicts D-04's non-reconstructibility claim. **Recommendation: introduce a fourth class** — e.g. "Durable orchestration state" — defined in `adr-0004` per D-12's conditional. Filing it under Support would reintroduce, in the very document being corrected, the falsehood this phase exists to remove.

Note `.construct/workflow/` is **not** in `REQUIRED_PATHS` and is **not** scaffolded by `init.py`; it is created lazily via `db.parent.mkdir(parents=True, exist_ok=True)` at first checkpointer construction. The contract entry should say so — it is an artifact that may legitimately be absent. `[VERIFIED: read from disk]`

### `CONSTRUCT-CLAUDE-spec/config-topology.md`

Exactly two `model-routing` mentions exist — both are D-02 fence targets, and there are no others in the file:

| Line | Current exact text |
|------|-------------------|
| **56** | `    ├── model-routing.yaml             # LLM tier routing (informational)` — inside a fenced template-directory tree (§1, `CONSTRUCT-CLAUDE-impl/construct/templates/`) |
| **135** | `\| \`model-routing.yaml\` \| ✅ (controls routing) \| 🟡 (informational) \| Claude handles all tasks \|` — inside the §3 "Comparison to Python Approach Workspace" table |

`[VERIFIED: grep -n model-routing]`

**Formatting constraint the planner must respect:** line 56 sits inside a ``` fenced ASCII tree with column-aligned comments. A deprecation note there must fit the tree's comment column or the alignment breaks. Recommend a short in-tree marker (`# DEPRECATED — see llm/config.yaml`) rather than a sentence, with any longer note placed in prose below the fence.

**D-03 collision, recorded as required:** Phase 17 (DOC-02) may delete or rewrite `config-topology.md` wholesale — REQUIREMENTS DOC-03… sorry, DOC-02 (line 28) reads "`config-topology.md` is either corrected against the real layout or deleted." Phase 14's two edits here may therefore be discarded by Phase 17. This is accepted per D-03; **no dependency is created and Phase 14 must not block on Phase 17.** The planner should carry this note verbatim into the plan so a Phase 17 executor does not treat the deprecation notes as load-bearing.

### `CONSTRUCT-CLAUDE-spec/adrs/` — format for `adr-0004`

Confirmed present, and **`adr-0004` is the next free number**:
```
adr-0001-claude-native-approach.md
adr-0002-v02-packaging.md
adr-0003-v03-pipeline-v04-ui.md
```
There is **no `README.md` or index file** in the directory. `[VERIFIED: ls]`

**Filename convention:** `adr-000N-<kebab-case-slug>.md` — slug is a compressed decision topic, not a sentence.

**Header block convention** (bold key-value lines immediately after the H1, no YAML frontmatter, followed by `---`):

| Field | adr-0001 | adr-0002 | adr-0003 |
|-------|----------|----------|----------|
| `**Status:**` | Accepted | Accepted | Accepted |
| `**Date:**` | 2026-04-23 | 2026-04-27 | 2026-06-07 |
| `**Accepted:**` | — | 2026-04-27 | — |
| `**Amended:**` | — | — | ×2 (dated, with one-line summary) |
| `**Deciders:**` | `;-)mab` | `;-)mab` | `;-)mab` |
| `**Context:**` | one-paragraph inline | one-paragraph inline | one-paragraph inline |
| `**Supersedes (partially):**` | — | — | present |
| `**Related:**` | — | — | relative markdown links |

**Body section convention** — `adr-0002` is the fullest canonical example and the best template for `adr-0004`:
```
## Context
## Decision
## Options Considered
### Option A: <name> (this decision)
**Pros:** / **Cons:**
### Option B: <name>
### Option C: <name>
## Consequences
### Positive
### Negative
### Neutral
```
`adr-0001` omits `Options Considered`; `adr-0003` uses `## Amendment A/B` blocks *before* `## Decision` to evolve in place. CONTEXT.md `<code_context>` notes D-07 deliberately departs from that amendment pattern — worth one sentence in `adr-0004`'s Context so a future reader understands why this is a new ADR rather than an Amendment C.

**Cross-references `adr-0004` must carry** (per D-07 / D-09 / CONTEXT canonical_refs):
- → `adr-0001` — markdown-as-truth; the claim D-05 preserves
- → `adr-0003` §A.3 — LangGraph as LLM orchestration layer; `adr-0004` is downstream of it
- ← cited by `nfrs.md` §2 and `architecture-overview.md` §8.2 (and §9.1 per the recommendation above)
- discharges Phase 10 D-02's deferred action (D-09) — cite the archived path **read-only**, do not edit it. The archive exists and was confirmed: `.planning/milestones/v0.4-phases/10-durable-human-review-research-run/10-CONTEXT.md`. `[VERIFIED: ls]`

Relative-link depth from `adrs/` to a sibling spec doc is `../<file>.md` (per `adr-0003:12`). Links into the repo root are `../../<path>`.

### `src/construct/llm/config.py` — the authority D-10 must defer to

```python
49: DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
50: _ENV_CONFIG_OVERRIDE = "CONSTRUCT_LLM_CONFIG"
...
62: def load_llm_config(config_path: Path | None = None) -> LlmConfig:
...
70:     path = config_path
71:     if path is None:
72:         env_path = os.environ.get(_ENV_CONFIG_OVERRIDE)
73:         if env_path:
74:             path = Path(env_path)
75:     if path is None:
76:         path = DEFAULT_CONFIG_PATH
77:
78:     if not path.exists():
79:         raise FileNotFoundError(f"GATE_PROVIDER_ERROR: LLM config not found at {path}. ...")
```

Module-level public surface is exactly: `ProviderConfig`, `GateConfig`, `LlmConfig`, `DEFAULT_CONFIG_PATH`, `load_llm_config`. `_load_yaml` and `_ENV_CONFIG_OVERRIDE` are private. **There is no function returning the resolved path.** `[VERIFIED: grep -n '^def |^DEFAULT|^_ENV']`

Note the constant name is `_ENV_CONFIG_OVERRIDE` (private) while its *value* is `CONSTRUCT_LLM_CONFIG`. A UI reading `os.environ["CONSTRUCT_LLM_CONFIG"]` directly would duplicate the string literal — exactly the drift D-10 exists to prevent. See Q1.

### `src/construct/ui/streamlit_app.py` — 43 lines total

```python
13: import streamlit as st          # ← the ONLY import in the file
...
22:     workspace_path = st.text_input("Workspace path", value="test-ws/my-construct", key="workspace_path_widget")
23:     install_root = st.text_input("Install root", value=".", key="install_root_widget")
24:     llm_config = st.text_input("LLM config path", value=".construct/model-routing.yaml", key="llm_config_widget")
25:     provider_override = st.selectbox("Provider override", ["", "anthropic", "openai", "ollama"], key="provider_override_widget")
26:
27:     # Store in session state for page access
28:     st.session_state["workspace_path"] = workspace_path
29:     st.session_state["install_root"] = install_root
30:     st.session_state["llm_config"] = llm_config
31:     st.session_state["provider_override"] = provider_override
```

**Dead-write claim independently re-verified.** Repo-wide grep for `session_state` reads across `src/construct/ui/`:
- `st.session_state["workspace_path"]` — **read** by `dashboard.py:86` and `gate_review.py:71` → **live, do not touch**
- `st.session_state["install_root"]` — **read nowhere** → same latent defect, but **not in scope** (D-10/D-11 name only the two)
- `st.session_state["llm_config"]` — **read nowhere** → D-10 target ✅
- `st.session_state["provider_override"]` — **read nowhere** → D-11 target ✅

`[VERIFIED: grep -rn session_state src/construct/ui/]`

Note `install_root` has the identical defect and is deliberately excluded — CONTEXT.md D-11 extended scope to `provider_override` explicitly and stopped there. The planner should **not** silently extend to `install_root`; if it seems warranted, flag it as a deferred item rather than absorbing it.

**Circular-import risk: none.** `streamlit_app.py` imports only `streamlit`. `construct.llm.config` imports `os`, `pathlib`, `typing`, `ruamel.yaml`, `pydantic` — no `construct.ui` import anywhere in the chain. A top-level `from construct.llm.config import ...` is safe. `[VERIFIED: read both files]`

One caution: `llm/config.py` is a leaf module, but importing `construct.llm.config` triggers `construct/llm/__init__.py`. The planner should confirm that package `__init__` does not eagerly import LangGraph/LangChain — if it does, the Streamlit sidebar would pay a heavy import cost at page load. Cheap to check at plan time; a `from construct.llm.config import X` with a lazily-imported module is fine either way.

### Evidence for D-04's non-reconstructibility claim (independently re-verified)

CONTEXT.md D-04 rests on a control-flow claim; it holds.

| Fact | Location |
|------|----------|
| `gate_review` node contains only `interrupt(...)` | `research_run.py:437`, `interrupt` at `:446` |
| `update_seeds_and_log` is a **separate node**, defined after the gate | `research_run.py:745` |
| **Every** `append_event` call in the module — `:786`, `:794`, `:808`, `:814`, `:820` — lies inside `update_seeds_and_log` (i.e. all ≥ 745) | `research_run.py` |
| Run status while paused | `awaiting_review` (`:936`, `:963`, `:1055`) |
| Checkpoint DB path | `research_run.py:891` — `Path(workspace)/".construct"/"workflow"/"research-run.sqlite"` |
| Sibling checkpointer, structurally identical | `curation_run.py:287` — `.../"curation-run.sqlite"` |

**Conclusion:** while a run sits at `awaiting_review`, zero events have been appended to `log/events.jsonl`. Scored findings and per-finding default decisions exist **only** in `research-run.sqlite`. D-04's claim is exact, not rhetorical — the planner should preserve its specificity per CONTEXT.md `<specifics>`. `[VERIFIED: grep -n append_event/interrupt on research_run.py]`

Both checkpointers use `SqliteSaver(sqlite3.connect(..., check_same_thread=False))` over `.construct/workflow/{name}-run.sqlite`, supporting the discretionary call that `adr-0004` may describe **one generic pattern** covering both files rather than two decisions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Displaying the effective LLM config path in the UI | Re-implement `explicit → env → default` in `streamlit_app.py`; or hardcode `"src/construct/llm/config.yaml"` | A resolver extracted from `llm/config.py` (Q1) | Re-implementing recreates the exact drift D-10 exists to close, one release later |
| Reading the env override | `os.environ.get("CONSTRUCT_LLM_CONFIG")` in the UI | the resolver | Duplicates a string literal that is currently private (`_ENV_CONFIG_OVERRIDE`) |
| Proving criterion 4 | Manual reading of the four fence files | `grep` assertions (see Validation Architecture) | Criterion 4 says "exactly one recorded fate" — a negative claim, provable only by an exhaustive search |
| ADR structure | Invent a format | Copy `adr-0002`'s section skeleton | D-07 requires format parity; `adr-0002` is the fullest instance |
| Deciding whether the suite is at risk | Reason about which docs tests read | The `_DOC_GLOBS` fact below | The scan set is explicit and narrow — read it, don't infer it |

**Key insight:** every criterion in this phase is a claim about *the absence of a false statement*. Absence claims are not verifiable by review — they are verifiable only by exhaustive search. Every task should ship with the grep that proves it.

## Common Pitfalls

### Pitfall 1: Editing `architecture-overview.md:240` instead of `:243`
**What goes wrong:** the `views/build/data/` anti-pattern gets a database carve-out bolted onto it; the actual database anti-pattern is untouched; criterion 1 fails.
**Why it happens:** CONTEXT.md D-06 and `<canonical_refs>` both say `:240`. ROADMAP and REQUIREMENTS say `:243`. **243 is correct.**
**How to avoid:** anchor the task on the *string* `"Add a database that owns part of the truth"`, not the line number.
**Warning signs:** a diff touching a bullet that mentions `views/build/data/`.

### Pitfall 2: Filing `.construct/workflow/*.sqlite` under "Support artifacts"
**What goes wrong:** the Support table's own preamble (line 71) says these artifacts "do not define workspace truth" — the precise falsehood DOC-03 exists to remove. Criterion 2 passes textually while criterion 1's substance is contradicted three files over.
**Why it happens:** it is the path of least resistance, and line 78 (already being edited) is right there.
**How to avoid:** introduce the fourth artifact class per D-12's conditional and define it in `adr-0004`.
**Warning signs:** a `.sqlite` row appearing directly beneath `.construct/model-routing.yaml`.

### Pitfall 3: Deleting the "No Hidden State" section instead of rewriting it
**What goes wrong:** `adr-0001` depends on markdown-as-truth portability; deleting the section removes a still-true, load-bearing claim and creates a new documentation hole.
**Why it happens:** three of four bullets read as false at a glance. In fact **bullets 50 and 51 remain entirely true** (no NetworkX graph, no views/ refresh); only 49 and 52 need scoping.
**How to avoid:** D-05 is explicit — rewrite scoped to knowledge state.
**Warning signs:** a diff with net-negative lines in `nfrs.md` §2 and no replacement prose.

### Pitfall 4: Over-correcting the Tavily privacy row
**What goes wrong:** "Third-party APIs: None" becomes "search data is sent to Tavily", which is false by default — the shipped `search.yaml` sets `default_provider: mock`.
**How to avoid:** state that Tavily is available and opt-in, and that egress occurs when it is enabled.
**Warning signs:** a §4 row with no conditional.

### Pitfall 5: Widening scope to `install_root`, `governance.yaml`, or `inbox/`
**What goes wrong:** each is a real, adjacent, genuinely-broken thing this phase deliberately does not own. Fixing them makes the diff unreviewable against the five criteria.
**How to avoid:** note each as an observation in the plan; edit none.
**Warning signs:** a diff touching `schemas/`, `storage/`, or `services/` — CONTEXT.md `<specifics>` names this as the drift signal.

### Pitfall 6: Treating the `llm/config.py` refactor as forbidden — or as licence
**What goes wrong:** either the plan hand-rolls resolution in the UI (recreating the drift), or it treats "we're allowed to touch config.py" as permission to restructure LLM config loading.
**How to avoid:** the permitted change is a pure extraction of lines 70-76 into a named function that `load_llm_config` then calls. Behavior identical, resolution order identical, no signature change to `load_llm_config`. See Q1.
**Warning signs:** any change to `load_llm_config`'s signature, the `FileNotFoundError` message, or `LlmConfig`.

## Project Constraints

No `./CLAUDE.md` or `./.claude/CLAUDE.md` exists in the repository, and no `.claude/skills/` or `.agents/skills/` directory exists. `.claude/` contains only `settings.local.json` and `worktrees`. `[VERIFIED: ls]`

Governing constraints therefore come from `.planning/REQUIREMENTS.md`:

| Constraint | Source | Implication for this phase |
|------------|--------|---------------------------|
| **No new runtime capability of any kind** | Out of Scope, line 62 | Bars wiring the sidebar to `load_llm_config` (D-10 rationale). The Q1 extraction is a refactor of existing logic, not new capability — but the plan should say so explicitly. |
| **No workspace-format change** | Out of Scope, line 65 | The reason D-01 reversed. `REQUIRED_PATHS`, `schemas/`, `storage/`, `services/init.py` are all untouchable. |
| **Event vocabulary: touch only where DOC-02/DOC-03 already require edits** | Future Requirements, line 54 | Phase 14's files do not define event vocabulary → **no overlap, touch nothing**. |
| **Not rewriting `prd.md` / `development-strategy.md`** | Out of Scope, line 64 | Both contain adjacent stale claims; out of fence. |
| **DOC-03 gates v0.5** | REQUIREMENTS line 29, Future Requirements line 50 | Wording chosen here carries forward — favor precision over brevity in `adr-0004`. |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (`[tool.pytest.ini_options]`, `pyproject.toml:40-42`) |
| Config | `testpaths = ["tests"]`, `pythonpath = [".", "src"]` |
| Interpreter | `.venv/bin/python` (repo venv; `python3` on PATH lacks pytest) |
| Quick run command | `.venv/bin/python -m pytest tests/contract -q` |
| Full suite command | `.venv/bin/python -m pytest -q` |
| **Verified baseline** | **439 tests collected** — `.venv/bin/python -m pytest --collect-only -q` |

### Why criterion 5 is a non-regression check, not a risk

`tests/contract/test_doc_command_references.py:41-45` defines the **only** doc-scanning glob set in the suite:

```python
_DOC_GLOBS = (
    (_IMPL / "claude" / "skills", "*/SKILL.md"),
    (_IMPL / "construct" / "workflows", "*.md"),
    (_REPO_ROOT, "USER-TEST-PLAYBOOK-v03.md"),
)
```

`CONSTRUCT-CLAUDE-spec/` is **not scanned**. Every file this phase edits — `nfrs.md`, `architecture-overview.md`, `workspace-contract.md`, `config-topology.md` — and the new `adr-0004` lie outside it. Additionally, **no test in the repository imports Streamlit or references `src/construct/ui/`** (`grep -rln streamlit tests/` → no matches). `[VERIFIED: read + grep]`

Therefore the expected post-phase state is **exactly 439 tests, all green, `_KNOWN_BROKEN` unchanged at 5 entries**. Any deviation is a signal, not noise.

`_KNOWN_BROKEN` (`test_doc_command_references.py:152-158`) currently holds **5 keys** covering the 6 V41-03 references:
```python
("knowledge","card","list"), ("knowledge","ref","list"),
("views","generate"), ("workflow","run"), ("workflow","resume")
```
A paired test (`test_known_broken_entries_are_still_broken`, `:213`) asserts each is *still* broken, so the allowlist can only shrink. Phase 14 touches none of these commands; the count must be unchanged.

### Phase Criteria → Mechanical Verification Map

Every criterion is mechanically checkable. Commands run from repo root.

| Crit | Requirement | Automated assertion |
|------|-------------|---------------------|
| **1a** | `nfrs.md` §2 no longer asserts no-database / no-required-derived-state | `! grep -qF "No databases, no caches, no derived state that's required" CONSTRUCT-CLAUDE-spec/nfrs.md` |
| **1b** | `nfrs.md` §2 drops the false "No SQLite index" bullet | `! grep -qF "No SQLite index to rebuild" CONSTRUCT-CLAUDE-spec/nfrs.md` |
| **1c** | `nfrs.md` §2 names the sqlite path + non-reconstructibility | `grep -qF '.construct/workflow/' CONSTRUCT-CLAUDE-spec/nfrs.md && grep -qiE 'not reconstructible\|pending human-review' CONSTRUCT-CLAUDE-spec/nfrs.md` |
| **1d** | `architecture-overview.md` DB anti-pattern retained **with** carve-out | `grep -qF "Add a database that owns part of the truth" CONSTRUCT-CLAUDE-spec/architecture-overview.md && grep -qF "adr-0004" CONSTRUCT-CLAUDE-spec/architecture-overview.md` |
| **1e** | `adr-0004` exists and is cited by both docs | `ls CONSTRUCT-CLAUDE-spec/adrs/adr-0004-*.md && grep -qF adr-0004 CONSTRUCT-CLAUDE-spec/nfrs.md && grep -qF adr-0004 CONSTRUCT-CLAUDE-spec/architecture-overview.md` |
| **1f** | `adr-0004` follows Nygard format | `grep -qE '^\*\*Status:\*\*' … && grep -qE '^## Context' && grep -qE '^## Decision' && grep -qE '^## Consequences'` on the adr-0004 file |
| **2a** | three artifacts listed in `workspace-contract.md` | `for a in '.construct/workflow/' '.construct/search.yaml' 'WORKSPACE.md'; do grep -qF "$a" CONSTRUCT-CLAUDE-spec/workspace-contract.md \|\| exit 1; done` |
| **2b** | `nfrs.md` §4 no longer claims no third-party APIs | `! grep -qF "Third-party APIs \| None" CONSTRUCT-CLAUDE-spec/nfrs.md` |
| **2c** | `nfrs.md` §4 names Tavily | `grep -qi tavily CONSTRUCT-CLAUDE-spec/nfrs.md` |
| **3a** | Streamlit no longer advertises `model-routing.yaml` as the LLM config | `! grep -qF 'model-routing.yaml' src/construct/ui/streamlit_app.py` |
| **3b** | Streamlit resolves via `llm/config.py` (drift-proof) | `grep -qE 'from construct\.llm\.config import\|construct\.llm\.config' src/construct/ui/streamlit_app.py` |
| **3c** | control is read-only (no editable text input for the path) | `! grep -qE 'st\.text_input\("LLM config path"' src/construct/ui/streamlit_app.py` — or, if `disabled=True` is chosen, assert `disabled=True` on that line |
| **3d** | env override honored end-to-end | `CONSTRUCT_LLM_CONFIG=/tmp/x.yaml .venv/bin/python -c "from construct.llm.config import <resolver>; assert str(<resolver>())=='/tmp/x.yaml'"` |
| **3e** | resolution order unchanged (regression guard on Q1 refactor) | `.venv/bin/python -c "from construct.llm.config import load_llm_config, DEFAULT_CONFIG_PATH; load_llm_config()"` exits 0 |
| **4a** | no live doc in the fence calls `model-routing.yaml` authoritative | `! grep -nE 'controls routing\|LLM tier routing' CONSTRUCT-CLAUDE-spec/config-topology.md` (absent deprecation marker) |
| **4b** | all four fence targets carry a deprecation marker | `grep -qi deprecat` on each of: `workspace-contract.md` (line-78 row), `config-topology.md` (×2), `nfrs.md` (line-72 sentence) |
| **4c** | `nfrs.md:72` names the real authority | `grep -qF 'llm/config.yaml' CONSTRUCT-CLAUDE-spec/nfrs.md` |
| **4d** | fence respected — untouched files unchanged | `git diff --name-only <base> -- AGENTS.md USER-TEST-PLAYBOOK-v03.md CONSTRUCT-CLAUDE-spec/spec-v04-agentworkflows.md CONSTRUCT-CLAUDE-spec/migrations/ .planning/milestones/` returns **empty** |
| **4e** | D-01 respected — scaffolding intact | `grep -qF 'model-routing.yaml' src/construct/services/init.py && grep -qF '.construct/model-routing.yaml' src/construct/schemas/workspace.py` |
| **5a** | full suite green, count floor | `.venv/bin/python -m pytest -q` → exit 0, **≥ 439 passed** (expected: exactly 439) |
| **5b** | no new `_KNOWN_BROKEN` entries | `.venv/bin/python -c "import sys; sys.path[:0]=['.','src']; from tests.contract.test_doc_command_references import _KNOWN_BROKEN as K; assert len(K)<=5, len(K)"` |

**Criterion 4d is the load-bearing one for D-02.** The edit fence is a *negative* constraint, and a `git diff --name-only` against the phase base commit is the only exhaustive proof of it. Recommend this run as a phase gate, not per-task.

### Sampling Rate

- **Per task commit:** the grep assertion(s) for that task's criterion, plus `.venv/bin/python -m pytest tests/contract -q` for any task touching `src/`
- **Per wave merge:** `.venv/bin/python -m pytest -q` (full 439)
- **Phase gate:** full suite green + criterion 4d fence diff empty + all 5a/5b checks, before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] **None for framework** — pytest is configured and the 439-test baseline is green today.
- [ ] **Optional (planner's call):** a `tests/contract/test_llm_config_resolution.py` covering the Q1 resolver — asserting explicit-arg, `CONSTRUCT_LLM_CONFIG`, and default precedence. This would raise the count above 439 (permitted: criterion 5 is a floor, "≥439"). **Recommended** if Q1 lands as an extraction, since it converts criterion 3d/3e from an ad-hoc shell check into a permanent regression guard on the exact drift this phase exists to close. It is a test, not a capability, so it does not breach the Out-of-Scope constraint.
- [ ] **Not recommended:** a Streamlit smoke test. `src/construct/ui/` has zero test coverage today and adding a Streamlit harness is disproportionate to a 4-line sidebar change.

## Security Domain

This phase writes no code paths that handle untrusted input, and adds no network, auth, or crypto surface. ASVS relevance is minimal but not nil.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface touched |
| V3 Session Management | no | Streamlit `session_state` is per-browser-session UI state, not a security session |
| V4 Access Control | no | Local single-user ops dashboard; no multi-tenancy |
| V5 Input Validation | marginal | D-10 **removes** a free-text input, strictly reducing input surface |
| V6 Cryptography | no | No crypto |
| V7 Error Handling & Logging | **yes** | See below |
| V14 Configuration | **yes** | See below |

### Threat Patterns

| Pattern | STRIDE | Mitigation for this phase |
|---------|--------|---------------------------|
| Filesystem path disclosure in UI | Information Disclosure | D-10 displays a resolved absolute path (e.g. `/Users/<name>/.../config.yaml`) in the sidebar. Acceptable — this is a **localhost single-user ops dashboard**, explicitly "not a product UI" (`streamlit_app.py:20`), and the path is already visible in `FileNotFoundError` messages at `config.py:80`. **Do not** widen it to display *config contents*: `LlmConfig` is structural, but `search.yaml` carries `api_key_env` names and the same display pattern must not be copied there later. |
| Arbitrary path read via editable config field | Tampering | The pre-D-10 `st.text_input` was a free-text path field. Because it was never read, it was inert — but had FIX-02 been "fixed" by wiring it up, it would have become an arbitrary-file-read primitive in the UI. **D-10's read-only choice is the security-correct one**, not merely the scope-correct one. Worth one line in the plan. |
| Env-var override trust | Tampering / V14 | `CONSTRUCT_LLM_CONFIG` is an existing, unchanged trust boundary — a user who can set it already controls the process. The Q1 extraction must not add validation that changes behavior; identical resolution semantics only. |
| Secret leakage through the new display | Information Disclosure | Assert the display shows a **path only**, never file contents. Mechanically: `! grep -qE 'load_llm_config\(\)\.(providers\|gates)' src/construct/ui/streamlit_app.py`. |

**Net effect:** this phase reduces attack surface (one free-text path input removed, one dead selectbox neutralized) and adds one low-sensitivity local path disclosure on a localhost-only dashboard. No new controls required.

## Open Questions

### Q1. `llm/config.py` exposes no path resolver — how does D-10 call into it? **(must be answered at plan time)**

**What we know:** D-10 requires the Streamlit display be "computed by calling into `llm/config.py`'s resolution order so `CONSTRUCT_LLM_CONFIG` is honored and the two cannot drift again." `load_llm_config()` returns `LlmConfig` — a parsed Pydantic object with **no path attribute**. The resolution logic is inlined at `config.py:70-76`, and the env-var name lives in a private `_ENV_CONFIG_OVERRIDE`. There is no public API that returns the effective path.

**What's unclear:** whether extracting one counts as the "new runtime capability" barred by REQUIREMENTS line 62.

**Recommendation — Option A (extract a resolver):**
```python
def resolve_llm_config_path(config_path: Path | None = None) -> Path:
    """Effective config path under the documented resolution order."""
    if config_path is not None:
        return config_path
    env_path = os.environ.get(_ENV_CONFIG_OVERRIDE)
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH
```
and have `load_llm_config` call it (`path = resolve_llm_config_path(config_path)`), preserving the existing `if not path.exists()` branch and error message verbatim.

This is a **pure extraction of existing logic**: no behavior change, no signature change, no new capability — it exposes a value the module already computes. It is also the only option that actually delivers D-10's stated goal, since it makes drift structurally impossible (one code path, two callers). Guard it with criterion 3d/3e and the optional Wave 0 test.

**Rejected — Option B (replicate in the UI):** satisfies criterion 3 textually while recreating the drift D-10 exists to close, and duplicates a currently-private constant.
**Rejected — Option C (hardcode the default path):** ignores `CONSTRUCT_LLM_CONFIG`, which criterion 3 names explicitly.

**Confidence:** HIGH that Option A is correct; the *authorization* is a planner/user call, which is why this is Q1 rather than a recommendation buried in prose.

### Q2. Should `adr-0003` be added to `architecture-overview.md` §9.1 alongside `adr-0004`?

**What we know:** §9.1 lists only `adr-0001` and `adr-0002`; `adr-0003` is missing from both §9.1 and the line-6 Related list. There is no separate ADR index file. D-07's rationale depends on a v0.5 planner finding ADRs "by title."
**What's unclear:** whether fixing a pre-existing omission in a file already being edited counts as scope creep.
**Recommendation:** **yes, add both** — one line, inside a file the phase edits anyway, and it is the difference between D-07's rationale holding and being merely asserted. Flag for explicit sign-off in the plan. If declined, `adr-0004` should at minimum link `adr-0003` directly so the chain is traversable.

### Q3. Does `.construct/workflow/*.sqlite` get a new artifact class?

**What we know:** D-12 leaves this to the planner and requires `adr-0004` to define any new class. The existing Support table's preamble ("do not define workspace truth") contradicts D-04; the Derived table's line 67 ("never canonical inputs") also contradicts it.
**Recommendation:** **new fourth class.** Neither existing table can hold it without reintroducing the falsehood being corrected. Add the class definition to `adr-0004` in the same wave.

### Q4. Does the tree at `workspace-contract.md:21-34` also need updating?

**What we know:** D-12 says "artifact tables"; criterion 2 says "lists … among workspace artifacts." The tree omits `.construct/` entirely, plus all three D-12 artifacts and (pre-existing) `inbox/`.
**Recommendation:** update the tree for the three D-12 artifacts; **leave `inbox/` alone** with an explicit note, as it is unrelated drift. Grep assertion 2a passes either way, so this is a quality call, not a criterion call.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `construct/llm/__init__.py` does not eagerly import LangGraph/LangChain, so a top-level import in the Streamlit sidebar is cheap | streamlit_app / Q1 | Slow page load only; no correctness impact. **Cheap to check at plan time** — grep `src/construct/llm/__init__.py`. |
| A2 | Adding a test file for the Q1 resolver is permitted under "≥439" | Validation Architecture | If criterion 5 were read as *exactly* 439, an added test would read as a violation. ROADMAP says "≥439", so this is low risk — but the planner should state the expected final count explicitly. |
| A3 | Phase 17 will treat the `config-topology.md` deprecation notes as discardable, not load-bearing | D-03 collision | Low — D-03 accepts this explicitly. Carrying the note into the plan is the mitigation. |

Everything else in this document was read directly from disk in this session and is tagged `[VERIFIED]`.

## Sources

### Primary (HIGH confidence — read from disk, 2026-07-19, at commit `4a9edb7`)
- `CONSTRUCT-CLAUDE-spec/nfrs.md` — lines 37-56, 76-84
- `CONSTRUCT-CLAUDE-spec/architecture-overview.md` — lines 1-8, 93-110, 211-263
- `CONSTRUCT-CLAUDE-spec/workspace-contract.md` — lines 1-110
- `CONSTRUCT-CLAUDE-spec/config-topology.md` — lines 45-70, 125-145 + full `model-routing` grep
- `CONSTRUCT-CLAUDE-spec/adrs/` — directory listing; `adr-0001` header + body, `adr-0002` full heading structure, `adr-0003` header + amendment structure
- `src/construct/llm/config.py` — full file (86 lines)
- `src/construct/ui/streamlit_app.py` — full file (43 lines)
- `src/construct/llm/research_run.py` — checkpointer (885-895); `append_event` / `interrupt` / `awaiting_review` call sites
- `src/construct/llm/curation_run.py` — checkpointer (283-292)
- `src/construct/schemas/workspace.py` — `REQUIRED_PATHS` (15-26)
- `src/construct/services/init.py` — scaffolding (58-59), WORKSPACE.md generator (161-176)
- `tests/contract/test_doc_command_references.py` — `_DOC_GLOBS` (41-45), `_KNOWN_BROKEN` (152-158), paired tests (171-221)
- `CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml` — full file (Tavily config, `default_provider: mock`)
- `pyproject.toml` — `[tool.pytest.ini_options]` (40-42)
- `.planning/REQUIREMENTS.md` — lines 18-70
- `.planning/config.json` — `nyquist_validation: true` confirmed
- `.planning/phases/14-durable-state-config-truth/14-CONTEXT.md` — full

### Commands executed (HIGH confidence)
- `.venv/bin/python -m pytest --collect-only -q` → **439 tests collected**
- `grep -rn session_state src/construct/ui/` → dead-write claim confirmed
- `grep -rn tavily -i src/construct/` → `providers/tavily.py`, `registry.py:101-109`, `schemas/config.py:238-279`
- `grep -rn 'workflow.*sqlite\|-run.sqlite' src/construct/` → exactly two checkpointer sites
- `ls .claude/ CONSTRUCT-CLAUDE-spec/adrs/ .planning/milestones/v0.4-phases/10-.../`

### Not consulted
No external documentation, package registry, or web source was needed. This phase installs no packages, so the **Package Legitimacy Audit is not applicable**. No `Environment Availability` audit is required beyond the confirmed `.venv/bin/python` + pytest toolchain, which is present and green.

## Metadata

**Confidence breakdown:**
- Current on-disk state (all edit targets) — **HIGH** — every line read directly this session
- Test baseline & criterion-5 risk — **HIGH** — 439 collected; `_DOC_GLOBS` read directly, proving spec docs are unscanned
- D-04 non-reconstructibility evidence — **HIGH** — re-derived independently from `research_run.py` control flow
- Streamlit dead-write claim — **HIGH** — confirmed by exhaustive repo grep
- ADR format for `adr-0004` — **HIGH** — extracted from all three existing ADRs
- Q1 resolver recommendation — **HIGH** on correctness, **planner decision** on authorization
- Artifact-class recommendation (Q3) — **MEDIUM** — reasoned from the tables' own preambles; D-12 explicitly leaves it open

**Research date:** 2026-07-19
**Valid until:** 2026-08-18 (30 days — spec docs are slow-moving; but re-verify line numbers if any commit lands in `CONSTRUCT-CLAUDE-spec/` before planning)
