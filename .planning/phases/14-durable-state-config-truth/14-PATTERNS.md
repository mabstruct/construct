# Phase 14: Durable-State & Config Truth - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 8 (2 new, 6 modified)
**Analogs found:** 8 / 8

This is a documentation-truth phase. For the five spec-doc edits the "analog" is *the surrounding document's own conventions* — sibling table rows, column headers, cross-reference syntax. Those are captured verbatim below so the planner can write before/after assertions instead of prose intentions.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-*.md` (NEW) | decision record | document | `adrs/adr-0002-v02-packaging.md` | exact (fullest template) |
| `src/construct/llm/config.py` (MOD) | config loader | file-I/O / pure resolve | itself — `load_llm_config` lines 62-86 | in-file extraction |
| `tests/unit/test_llm_config_resolution.py` (NEW) | test | request-response | `tests/llm/test_factory.py` (env idiom) + `tests/unit/test_workspace_contracts.py` (unit layout) | role-match (composite) |
| `src/construct/ui/streamlit_app.py` (MOD) | UI sidebar | presentation | itself — lines 18-35 (`st.caption` idiom already present) | in-file |
| `CONSTRUCT-CLAUDE-spec/nfrs.md` (MOD, §2 ×2, §3:72, §4:83) | spec prose + tables | document | sibling rows in the same tables | exact |
| `CONSTRUCT-CLAUDE-spec/architecture-overview.md` (MOD, :6, :243, §9.1) | spec prose + list | document | sibling bullets in §8.2 / §9.1 | exact |
| `CONSTRUCT-CLAUDE-spec/workspace-contract.md` (MOD, tree :21-34, tables :48-78) | spec tables | document | the three existing artifact-class tables | exact |
| `CONSTRUCT-CLAUDE-spec/config-topology.md` (MOD, :56, :135) | spec tree + table | document | sibling tree lines / table rows | exact |

---

## Pattern Assignments

### `CONSTRUCT-CLAUDE-spec/adrs/adr-0004-<slug>.md` (NEW — highest value)

**Analog:** `CONSTRUCT-CLAUDE-spec/adrs/adr-0002-v02-packaging.md` (fullest instance; `adr-0001` omits Options Considered, `adr-0003` uses Amendment blocks).

**Filename convention:** `adr-000N-<kebab-case-slug>.md` — slug is a compressed topic, not a sentence. Existing: `adr-0001-claude-native-approach.md`, `adr-0002-v02-packaging.md`, `adr-0003-v03-pipeline-v04-ui.md`. `adr-0004` is the next free number; there is **no README/index in `adrs/`**.

**Header block** (`adr-0002:1-9`) — bold key-value lines directly under H1, **no YAML frontmatter**, terminated by `---`:

```markdown
# ADR-0002: v0.2 Packaging and Planning Directory Layout

**Status:** Accepted
**Date:** 2026-04-27
**Accepted:** 2026-04-27
**Deciders:** ;-)mab
**Context:** v0.2 (live views) needs a home. `CONSTRUCT-CLAUDE-v02-planning/` was created as a planning workspace. Before any v0.2 implementation work begins, we need to decide where v0.2 source code lives and what role v02/ plays going forward. This is Epic 1 in `CONSTRUCT-CLAUDE-v02-planning/backlog.md`.

---
```

Note: `**Context:**` in the header is a **one-paragraph inline summary**, distinct from and duplicated-in-spirit by the later `## Context` section. `adr-0001` and `adr-0003` both follow this. `**Deciders:** ;-)mab` is verbatim in all three.

**Optional header fields, as used by `adr-0003:1-13`** — include `**Related:**` (adr-0004 must cross-reference adr-0001 and adr-0003 §A.3 per D-07):

```markdown
**Amended:** 2026-06-07 — invoke surfaces (CLI → MCP), UI spike path, LangGraph for LLM layer
**Supersedes (partially):** The monolithic "CONSTRUCT03 = UI shell in one step" framing in [`CONSTRUCT-CLAUDE-v03-planning/README.md`](../../CONSTRUCT-CLAUDE-v03-planning/README.md). ...
**Related:** [`artifact-catalog.md`](../artifact-catalog.md) (PIPE / UI / LLM / HYB audit), [`adr-0001-claude-native-approach.md`](adr-0001-claude-native-approach.md), [`adr-0002-v02-packaging.md`](adr-0002-v02-packaging.md), archived [`archive/v01-python/spec/adrs/adr-0001-python-first-drop-openclaw.md`](../../archive/v01-python/spec/adrs/adr-0001-python-first-drop-openclaw.md)
```

**Link-depth convention (confirmed from the excerpt above):**
- ADR → sibling ADR: `[`adr-0003-v03-pipeline-v04-ui.md`](adr-0003-v03-pipeline-v04-ui.md)` — **bare filename, no `./`**
- ADR → sibling spec doc: `[`artifact-catalog.md`](../artifact-catalog.md)`
- ADR → repo root path: `(../../<path>)` — use this for the read-only citation of `.planning/milestones/v0.4-phases/10-durable-human-review-research-run/10-CONTEXT.md` (D-09)
- Link text is the backticked filename inside the link label.

**Body section skeleton — copy from `adr-0002` (headings at 11/27/35/37/54/69/84/86/93/98):**

```markdown
## Context
## Decision
## Options Considered
### Option A: <name> (this decision)
**Pros:**
- ...
**Cons:**
- ...
### Option B: <name>
### Option C: <name>
## Consequences
### Positive
### Negative
### Neutral
```

Observed details worth matching:
- `---` separators appear between major sections (`adr-0002` after header, after Context, after Decision, after Options Considered, after Consequences).
- Option A carries the parenthetical `(this decision)`; `adr-0003:218-230` instead uses `(rejected)` / `(chosen)` — either is precedented, pick one and be consistent.
- Each Option gets a one-paragraph description **before** its `**Pros:**` / `**Cons:**` lists.
- Consequences bullets are full sentences, often with an em-dash clause giving the mitigation (`adr-0002:95`: "...without checking version metadata — addressed by a clear `VERSION` field...").
- `adr-0002` appends **extra trailing sections after Consequences** (`## Planning Directory Layout (consequence of this decision)` with a table, `## Open Questions Surfaced by This Decision` as a numbered list). This is the precedent for adr-0004 carrying the **new "Durable orchestration state" artifact-class definition** required by D-12/Q3 as its own post-Consequences section.
- `adr-0001:190` has `## Relationship to prior ADRs`; `adr-0003:301` the same. This is the precedent slot for the one sentence explaining why adr-0004 is a new ADR rather than an Amendment C to adr-0003.

**Table style inside ADRs** (`adr-0002:107-115`) — note the compact `|---|---|---|` separator (not padded):

```markdown
| Directory | Role | Lifetime |
|---|---|---|
| `CONSTRUCT-CLAUDE-spec/` | Canonical PRD, ADRs, schemas, agent specs | Permanent — single source of canonical decisions |
```

---

### `src/construct/llm/config.py` (MOD — the Q1 resolver extraction)

**Analog:** the file itself. The extraction is of lines 70-76 into a public function; `load_llm_config` then calls it.

**Current exact state (lines 49-50, 62-86) — read this session:**

```python
DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_ENV_CONFIG_OVERRIDE = "CONSTRUCT_LLM_CONFIG"


def _load_yaml(path: Path) -> dict[str, Any]:
    ...


def load_llm_config(config_path: Path | None = None) -> LlmConfig:
    """Load LLM provider config from YAML.

    Resolution order:
    1. ``config_path`` argument (explicit override)
    2. ``CONSTRUCT_LLM_CONFIG`` environment variable
    3. ``src/construct/llm/config.yaml`` (default)
    """
    path = config_path
    if path is None:
        env_path = os.environ.get(_ENV_CONFIG_OVERRIDE)
        if env_path:
            path = Path(env_path)
    if path is None:
        path = DEFAULT_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"GATE_PROVIDER_ERROR: LLM config not found at {path}. "
            f"Create src/construct/llm/config.yaml or set "
            f"{_ENV_CONFIG_OVERRIDE} environment variable."
        )

    data = _load_yaml(path)
    return LlmConfig(**data)
```

**Docstring style for module-level functions in this file:** one-line summary, then — where behavior is non-obvious — a numbered/labelled block using **double-backtick reST inline literals** (``` ``config_path`` ```), not markdown single backticks. The `Resolution order:` block above is the exact style the new `resolve_llm_config_path` docstring should mirror. Note `_load_yaml` (private, trivial) has **no docstring at all** — brevity is precedented for private helpers, but the new function is public and must carry one.

**Other conventions to preserve:**
- `from __future__ import annotations` at top; `X | None` union syntax in signatures.
- Public names are bare; private names carry a leading underscore (`_load_yaml`, `_ENV_CONFIG_OVERRIDE`). A new **public** `resolve_llm_config_path` correctly joins the public surface (`ProviderConfig`, `GateConfig`, `LlmConfig`, `DEFAULT_CONFIG_PATH`, `load_llm_config`).
- Two blank lines between module-level defs.

**Must survive verbatim (Pitfall 6 guard):** the `if not path.exists():` branch, the exact `FileNotFoundError` message including the `{_ENV_CONFIG_OVERRIDE}` interpolation, and `load_llm_config`'s signature. The extracted call site becomes `path = resolve_llm_config_path(config_path)`.

**Package-init check (RESEARCH A1) — resolved:** `src/construct/llm/__init__.py` is two lines, a docstring plus `from __future__ import annotations`. **No eager LangGraph/LangChain import.** A top-level `from construct.llm.config import resolve_llm_config_path` in the Streamlit sidebar is cheap and safe. Assumption A1 is confirmed; the planner need not re-check.

---

### `tests/unit/test_llm_config_resolution.py` (NEW)

No existing test exercises `CONSTRUCT_LLM_CONFIG`. The pattern is a composite of two analogs.

**Env-isolation + class-grouping idiom — `tests/llm/test_factory.py:1-32`:**

```python
"""Tests for the model-agnostic LLM provider factory (build_chat_model)."""
from __future__ import annotations

import pytest

from construct.llm.config import ProviderConfig
from construct.llm.factory import build_chat_model


class TestAnthropicBranch:
    """type='langchain_anthropic' returns a configured ChatAnthropic."""

    def test_builds_anthropic_with_config_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returned model reflects config model/max_tokens and the passed temperature."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        ...
```

Extract precisely: module docstring naming the unit under test; `from __future__ import annotations`; `import pytest`; absolute `from construct...` imports; **`TestXxx` classes with a docstring stating the behavior contract**; `monkeypatch: pytest.MonkeyPatch` as a typed parameter; `-> None` on every test; a one-line docstring per test method describing the assertion; arrange/act/assert separated by blank lines. Use `monkeypatch.delenv("CONSTRUCT_LLM_CONFIG", raising=False)` for the default-precedence case — `setenv` is the only form currently used in-repo, so `delenv` is new but is the natural sibling.

**`tests/unit/` file-level layout — `tests/unit/test_workspace_contracts.py:1-14`:**

```python
from __future__ import annotations

import json
from pathlib import Path

from ruamel.yaml import YAML

from construct.schemas.config import DomainsRegistry, GovernanceConfig, ModelRoutingConfig, SearchSeedsFile
from construct.schemas.workspace import WorkspaceScaffold
from construct.storage.workspace import WorkspaceLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates"
```

Note `tests/unit/` files use module-level `_snake_case` helper functions (`_write_canonical_workspace(root: Path) -> Path`) and **two blank lines** after the import block before the first constant. `tmp_path: Path` is the standard fixture for filesystem tests (`test_ask_domain.py:76, 200`).

**Existing precedent for asserting on the default path** — `tests/llm/test_ask_domain.py:243-247`:

```python
    def test_provider_config_default_loads(self) -> None:
        """..."""
        from construct.llm.config import DEFAULT_CONFIG_PATH, load_llm_config

        cfg = load_llm_config(DEFAULT_CONFIG_PATH)
```

Function-local imports of `construct.llm.config` are precedented inside test methods.

**Placement note:** RESEARCH suggests `tests/contract/test_llm_config_resolution.py`; the phase prompt says `tests/unit/`. Either directory is collected (`testpaths = ["tests"]`). `tests/unit/` is the better fit — this tests a single pure function's precedence, not a cross-component contract.

---

### `src/construct/ui/streamlit_app.py` (MOD — D-10 / D-11)

**Analog:** the file itself. 43 lines, `import streamlit as st` is the only import (line 13).

**Current sidebar block (lines 17-35) — the read-only idiom D-10 needs is already present at lines 20, 34, 35:**

```python
# Sidebar config (per PRD §10 sidebar spec)
with st.sidebar:
    st.header("CONSTRUCT Ops")
    st.caption("Local ops dashboard — not a product UI")

    workspace_path = st.text_input("Workspace path", value="test-ws/my-construct", key="workspace_path_widget")
    install_root = st.text_input("Install root", value=".", key="install_root_widget")
    llm_config = st.text_input("LLM config path", value=".construct/model-routing.yaml", key="llm_config_widget")
    provider_override = st.selectbox("Provider override", ["", "anthropic", "openai", "ollama"], key="provider_override_widget")

    # Store in session state for page access
    st.session_state["workspace_path"] = workspace_path
    st.session_state["install_root"] = install_root
    st.session_state["llm_config"] = llm_config
    st.session_state["provider_override"] = provider_override

    st.divider()
    st.caption("All executions go through capability registry.")
    st.caption("No SOT writes.")
```

**Local style to match:**
- `st.caption(...)` is the established static/read-only display primitive in this file (three existing uses). Choosing `st.caption` for the resolved path is the lowest-friction option and needs no new idiom.
- Every interactive widget carries an explicit `key="<name>_widget"`. A converted read-only display has no widget key — drop it.
- Long widget calls sit on one line regardless of length; no wrapping precedent exists in this file.
- Comment style: short `#` comments introducing a block (`# Store in session state for page access`, `# Page routing (per PRD §10.1)`). A comment recording *why* the two controls are read-only (citing D-10/D-11) matches local practice.
- Module docstring (lines 1-10) cites decision IDs (`Per ADV-04 and D-03`, `per D-04`). If the docstring is amended, use the same `Per D-10/D-11:` form.

**Must not be disturbed:** `workspace_path` and `install_root` widgets and their `session_state` writes. `st.session_state["workspace_path"]` is **read** by `dashboard.py:86` and `gate_review.py:71`. `install_root` has the identical dead-write defect and is **deliberately out of scope** (Pitfall 5).

---

### `CONSTRUCT-CLAUDE-spec/nfrs.md` (MOD — §2 ×2, §3:72, §4:83)

**Analog:** sibling rows in the same tables.

**§2 Reliability table (lines 39-44) — the shape the D-04 rewrite must conform to.** Three columns, sentence-fragment cells, no trailing periods:

```markdown
| Requirement | Target | Implementation |
|-------------|--------|----------------|
| Workspace integrity | Card files never corrupted by agent failure | Atomic file writes; cards are small individual files |
| Partial failure | One skill step failing doesn't corrupt workspace | Skills have independent steps |
| Rebuild guarantee | Workspace files are self-contained — no hidden state | No databases, no caches, no derived state that's required |
| Event log durability | `events.jsonl` is append-only | Never truncated or edited by skills |
```

Row 3 is the D-04 target. Note sibling cells are short; D-04's scoped invariant plus the `adr-0004` citation will not fit one row cleanly — the precedent for spillover is the prose subsection immediately below the table (§2's "No Hidden State Advantage" heading at line 46). Keep the row terse and carry the detail into the rewritten prose block.

**§2 prose block (lines 46-52) — the D-05 rewrite target, verbatim:**

```markdown
### The "No Hidden State" Advantage

Unlike the Python approach, the Claude-native system has no derived state that can get out of sync:
- No SQLite index to rebuild
- No NetworkX graph to recompute
- No views/ directory to refresh
- Everything is in the files — if the files are correct, the system is correct
```

Shape: `###` heading, one lead-in sentence ending in a colon, then a flat unordered list of short assertions. Bullets 2 and 3 (`NetworkX`, `views/`) remain true and should survive; the lead-in and bullets 1 and 4 need scoping (Pitfall 3 — net-negative lines with no replacement prose is the failure signal).

**§3:72 — D-02 fence target, verbatim (a prose paragraph, not a table row):**

```markdown
This is identical to any Claude conversation. Users control what's in their workspace. The `governance.yaml` and `model-routing.yaml` files are informational in the Claude-native approach — Claude handles all tasks.
```

Rewrite only the `model-routing.yaml` clause; leave `governance.yaml` alone and flag it as an observation (RESEARCH note on line 72).

**§4 Privacy table (lines 78-83) — the D-08 target.** Two columns, `Aspect | Policy`, policy cells are **full sentences with terminal periods** (unlike §2):

```markdown
| Aspect | Policy |
|--------|--------|
| Knowledge graph | Local files. Sent to Claude only during active conversation. |
| Web search | Claude's web search — governed by Anthropic's privacy policy |
| Telemetry | None from CONSTRUCT. Claude's standard telemetry applies. |
| Third-party APIs | None. Web search replaces dedicated API clients. |
```

The `Telemetry` row is the closest stylistic model for a conditional correction: a short declarative followed by the qualifying second sentence. Pitfall 4 requires the replacement to carry a conditional (opt-in via `.construct/search.yaml`; `default_provider: mock`).

**Section separator:** `---` between every top-level `## N.` section.

---

### `CONSTRUCT-CLAUDE-spec/architecture-overview.md` (MOD — :6, :243, §9.1)

**§8.2 anti-pattern bullets (lines 240-243) — D-06 target is the last bullet.** Shape: `- "<quoted temptation>" → <verdict>. <one-to-two-sentence rationale>.`

```markdown
### 8.2 Anti-patterns to reject

- "Stash this small piece of state in `views/build/data/` because it's convenient" → no. If it's facts, layer 1. If it's UI state, browser-local (localStorage), not the cache.
- "Have the browser POST back to a small server endpoint to update X" → no. Browser → Claude → skill → layer 1.
- "Replicate part of the cache into a config file Claude reads" → no. Claude reads layer 1 directly. The cache is for the SPA only.
- "Add a database that owns part of the truth" → reconsider. A database is fine as a derived layer (layer 2 sibling) but never as the truth. Markdown stays canonical.
```

Note the target bullet already reads `→ reconsider` (not `→ no`) — it is the only softened verdict in the list, which makes it structurally hospitable to a named carve-out clause appended in the same bullet. **Anchor the edit on the string `"Add a database that owns part of the truth"`, not on a line number** (Pitfall 1 — CONTEXT says :240, actual is :243).

**§9.1 list (lines 249-251) — Q2 target.** Shape: `` - `adrs/<filename>.md` — <short gloss> ``. Note this list uses **plain backticked paths, not markdown links** (unlike the ADRs' own cross-references):

```markdown
### 9.1 Decisions and principles
- `adrs/adr-0001-claude-native-approach.md` — Claude-native approach; markdown as truth
- `adrs/adr-0002-v02-packaging.md` — v0.2 packaging; in-place implementation in `CONSTRUCT-CLAUDE-impl/`
```

Per the user's resolution of Q2, both `adr-0003` and `adr-0004` are added here in this style.

**Line 6 `**Related:**` list** — backticked paths separated by ` · ` (middle dot), no links:

```markdown
**Related:** `adrs/adr-0001-claude-native-approach.md` · `adrs/adr-0002-v02-packaging.md` · `prd.md` · `prd-v02-live-views.md` · `spec-v02-runtime-topology.md` · `spec-v02-data-model.md`
```

---

### `CONSTRUCT-CLAUDE-spec/workspace-contract.md` (MOD — tree :21-34, tables :48-78)

**Analog:** the three artifact-class tables in the same file. Each is preceded by a `###` heading and a one-sentence preamble that *defines the class*, and some are followed by a rule sentence.

**Canonical table (lines 44-56) — four columns:**

```markdown
### Canonical source-of-truth artifacts

These files define the governed knowledge state. Invalid versions of these artifacts must be rejected before write.

| Path | Class | Role | Canonical authority |
|------|-------|------|---------------------|
| `cards/*.md` | source of truth | Canonical knowledge cards and governed claims | `knowledge-card-schema.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/card.md` |
| `log/events.jsonl` | source of truth audit artifact | Append-only action history for review and proof | `data-schemas.md` |
```

**Derived table (lines 58-67) — three columns, with a trailing rule sentence:**

```markdown
### Derived artifacts

These artifacts are generated from source-of-truth files or workflow execution. They are important, but they are not canonical graph state.

| Path | Class | Role |
|------|-------|------|
| `digests/{domain}/digest-{date}.md` | derived | Research-cycle summaries and review output |
| `publish/{slug}.md` | derived | Curated outward-facing synthesis output |

`digests/` and `publish/` must never be treated as canonical graph inputs.
```

**Support table (lines 69-78) — three columns; line 78 is the D-02 fence target:**

```markdown
### Support artifacts

These artifacts support execution, configuration, or deployment, but they do not define workspace truth.

| Path | Class | Role |
|------|-------|------|
| `.construct/` | support | Deployed agent infrastructure: skills, workflows, references, templates |
| `AGENTS.md` | support | Workspace operating rules for the Claude-native runtime |
| `.construct/templates/*` | support | Authoritative initial shapes for canonical and derived artifacts |
| `.construct/model-routing.yaml` | support | Runtime/provider routing guidance; not part of workspace knowledge state |
```

**Template for a fourth class (Q3/D-12):** copy the Derived-table structure exactly — `###` heading, defining preamble sentence, three-column `Path | Class | Role` table, optional trailing rule sentence. The `Class` cell value is a lowercase noun phrase matching the heading (`source of truth`, `derived`, `support`). The trailing rule sentence is the natural place to note that `.construct/workflow/` is **not** in `REQUIRED_PATHS`, is not scaffolded, and may legitimately be absent (created lazily at first checkpointer construction).

**Canonical shape tree (lines 21-32) — the Q4 target.** RESEARCH rendered this compressed; the actual on-disk form is one entry per line:

```text
workspace/
├── cards/
├── refs/
├── connections.json
├── domains.yaml
├── governance.yaml
├── search-seeds.json
├── log/
│   └── events.jsonl
├── digests/
│   └── {domain}/
└── publish/
```

No trailing comments in this tree (unlike `config-topology.md`). Nesting uses `│   └──`. `└──` marks the final entry — adding entries after `publish/` requires changing `└── publish/` to `├── publish/`. Per the user's Q4 resolution: add the three D-12 artifacts, leave `inbox/` alone with a note.

---

### `CONSTRUCT-CLAUDE-spec/config-topology.md` (MOD — :56, :135)

**:56 — inside a fenced ASCII tree with column-aligned trailing comments.** Sibling lines establish the alignment column (comments begin at a fixed offset):

```text
└── templates/                         # File format templates
    ├── card.md                        # Knowledge card
    ├── domains.yaml                   # Domain taxonomy
    ├── governance.yaml                # Governance thresholds
    ├── model-routing.yaml             # LLM tier routing (informational)
    ├── search-seeds.json              # Search patterns
    ├── connections.json               # Empty graph edge list
```

Comments are **short noun phrases**, no terminal period. A long deprecation sentence here breaks the column alignment — use a short in-tree marker and place any longer note in prose below the fence.

**:135 — §3 comparison table.** Four columns; the two middle cells use emoji status markers with a short parenthetical:

```markdown
| `db/` | ✅ (SQLite) | ❌ (not needed) | No persistent index |
| `views/` | ✅ (heartbeat) | ❌ (not needed) | No React UI |
| `inbox/` | ✅ (UI writeback) | ❌ (not needed) | No async action queue |
| `model-routing.yaml` | ✅ (controls routing) | 🟡 (informational) | Claude handles all tasks |
| `workflows/` | ✅ (SKILL.md files) | ❌ (in config, not workspace) | No async action queue |
```

Marker vocabulary in use: `✅`, `❌`, `🟡`. The deprecation edit must keep the four-column shape and the marker-plus-parenthetical form; the rightmost column is a short rationale phrase.

Also note the `db/` row asserts "No persistent index" — adjacent to, but outside, this phase's fence. Do not touch.

---

## Shared Patterns

### Cross-referencing an ADR from a spec doc
**Source:** `architecture-overview.md:6` and `:249-251`
**Apply to:** `nfrs.md` §2, `architecture-overview.md` §8.2 and §9.1
Spec docs cite ADRs as **plain backticked paths** (`` `adrs/adr-0004-<slug>.md` ``), not markdown links. ADRs cite each other as **markdown links with backticked labels**. Do not mix the two conventions.

### Grep-provable edits
**Source:** RESEARCH "Validation Architecture", criteria 1a-4e
**Apply to:** every doc task
Every criterion in this phase is an *absence* claim. Each edit should be paired with the `grep`/`! grep` assertion that proves it. Anchor assertions on **strings** (e.g. `"Add a database that owns part of the truth"`), never on line numbers — CONTEXT.md's `:240` is already wrong.

### Decision-ID citation in code comments and docstrings
**Source:** `streamlit_app.py:3,8` (`Per ADV-04 and D-03:`, `per D-04`); `workspace-contract.md` preamble sentences
**Apply to:** `streamlit_app.py`, `config.py`
This codebase records *why* inline by naming the decision ID. Both code edits should carry a `D-10` / `D-11` / `Q1` reference.

### Section separators in spec docs
**Source:** `nfrs.md`, `architecture-overview.md`, all three ADRs
**Apply to:** all spec-doc edits
`---` on its own line separates top-level `##` sections. New sections must carry it.

---

## No Analog Found

None. Every file to be created or modified has a direct in-repo analog, including the two new files.

One partial gap worth flagging: **no existing test uses `monkeypatch.delenv`** — `setenv` is the only form present (`test_factory.py`, `test_curation_run_cli_mcp.py`, `test_daily_run_cli_mcp.py`). The default-precedence case in the new test needs `delenv(..., raising=False)`, which is a standard pytest idiom but is new to this repo.

## Metadata

**Analog search scope:** `CONSTRUCT-CLAUDE-spec/adrs/`, `CONSTRUCT-CLAUDE-spec/*.md`, `src/construct/llm/`, `src/construct/ui/`, `tests/unit/`, `tests/llm/`, `tests/contract/`
**Files read this session:** `adr-0002` (full), `adr-0001` + `adr-0003` (headers + heading maps), `llm/config.py` (full), `llm/__init__.py` (full), `ui/streamlit_app.py` (full), `tests/llm/test_factory.py:1-45`, `tests/unit/test_workspace_contracts.py:1-35`, plus targeted ranges of `nfrs.md`, `architecture-overview.md`, `workspace-contract.md`, `config-topology.md`
**Pattern extraction date:** 2026-07-19 (commit `4a9edb7`)
