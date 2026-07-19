# Phase 15: views.generate_data Resolution - Research

**Researched:** 2026-07-19
**Domain:** Python data-contract reconciliation, library vendoring, LangGraph workflow node wiring, Typer CLI surface
**Confidence:** HIGH

## Summary

This phase has an unusually complete CONTEXT.md — twelve locked decisions, evidence pre-gathered, alternatives explicitly rejected. Research therefore did **not** explore alternatives. It did three things: reproduced the live probe to confirm the stated evidence, read the parsers and models directly to derive the exact field set D-02 leaves to discretion, and stress-tested the decisions against the code to find consequences the discussion did not surface.

All CONTEXT.md claims verified true against the working tree. Every file:line citation resolved. The probe reproduced exactly: 3 validation errors (18 domains / 16 cards / 1 bridges), `success=False`, files written. [VERIFIED: live execution]

Four findings materially change how this phase should be planned. **(1)** The parser→model pipeline has a *third* layer nobody named: `_FILE_MODEL_MAP` in `generate.py:95-165`, a set of adapter lambdas that reshape parser output before validation. D-02 says "models move, not parsers" — but for `cards.json` the adapter, not the parser, decides the shape. This is the one genuinely open decision left. **(2)** `spec-v02-data-model.md` §5.1/§5.2 independently corroborates the parsers field-for-field, upgrading D-02 from an editorial choice to a spec-conformance fix and supplying the exact names/types the planner needed. **(3)** D-04's done-bar is insufficient as written — a freshly scaffolded workspace surfaces only 2 of the 3 validation errors, so the `CardRecord.connections` fix would go unverified. **(4)** PyYAML is an undeclared transitive dependency that D-08's vendoring converts into a shipped-code import.

**Primary recommendation:** Plan four waves — (0) test scaffolding for the populated-workspace verification D-04 needs, (1) vendor + dependency declaration (D-08/D-09), (2) model/adapter reconciliation to the v0.2 spec shape (D-02), (3) surface wiring + refresh relocation (D-01/D-03/D-05/D-06/D-10/D-11/D-12) and the decision records. Resolve OQ-1 (adapter fate) before Wave 2 starts.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `views.generate_data` is **wired to the real implementation** at `views/generate.py:175`, not retired from the registry. The `OperationResult(success=False, "Not yet implemented — see Plan 02")` lambda at `catalog.py:317` is replaced by a real call. Wiring **requires** the reconciliation in D-02. The retire branch was considered and rejected.
- **D-02:** The **models move, not the parsers.** The skill-lib parsers plus the deployed SPA are ground truth; `views/models.py` is a narrower contract than reality. Add the missing fields to `DomainRecord`, `CardRecord`, and `BridgesFile`, and correct `connections` to `list[str]`. **`model_config = ConfigDict(extra="forbid")` stays on all 17 models.** Relaxing to `extra="ignore"` was explicitly rejected. Narrowing the parsers was rejected because it changes what lands in `views/build/data/`.
- **D-03:** The forced `construct views generate` command is **hand-written alongside `validate`** at `cli.py:868`, calling the generator directly. It does **not** route through the capability registry. Consequence recorded deliberately: CLI and MCP reach the same function via two independent code paths and can drift. RT-01/RT-02 **stays open** for the views group; the bounded exception at `REQUIREMENTS.md:51` is declined.
- **D-04:** **Definition of done for "wired":** `generate()` returns `success=True` with zero `validation_errors` against a **freshly scaffolded workspace** (via `services/init.py`). Historical content in `test-ws/` is **out of scope**. Verification must scaffold a clean workspace rather than assert against `test-ws/`.
- **D-05:** The contract is **install root**, recorded explicitly. `ViewsGenerateDataInput.workspace` becomes `install_root: Path`.
- **D-06:** **Both** views commands are renamed to `--install-root`. The `-w` short flag's fate is the planner's call.
- **D-07:** The **two `USER-TEST-PLAYBOOK-v03.md` invocations are fixed in this phase** (`:333`, `:411`), a deliberate crossing of Phase 14 D-02's edit fence. **No cross-phase dependency is created and Phase 15 must not block on Phase 16.**
- **D-08:** All 15 modules under the skill's `lib/` (~1,496 lines) are **vendored into `src/construct/views/lib/`**, and the `sys.path` injection at `generate.py:43-51` is deleted. This is a **move, not a rewrite**. The parsers' behavior must not change.
- **D-09:** The skill **becomes a CLI wrapper.** Its `lib/` and `generate.py` are deleted; `run.sh` becomes a call to `construct views generate --install-root "$1"`. Accepted cost: the skill stops being standalone; the per-skill venv bootstrap goes away. `requirements.txt` and `debounced_hook.py` need review under the same rule.
- **D-10:** `curation_run.py:981`'s `views_refresh_hook` node is **wired to actually generate**, replacing `_deferred_step("views_refresh_hook")`.
- **D-11:** **Phase 13's D-10 ("parent owns the single views refresh") is superseded.** The Python capability owns the refresh; the views-refresh sections are **removed** from `construct-curation-cycle/SKILL.md` (Step 5), `construct-research-cycle/SKILL.md` (:109-113), and `construct/workflows/daily-cycle.md` (§5). **This reverses a recorded v0.4 decision and must be documented as such** — durable enough that Phase 17 does not re-derive the old rule.
- **D-12:** **Every workflow capability refreshes** — `curation.run`, `research.run`, and `daily.run` each end with a views refresh. Accepted cost: a daily cycle triggers three sweeps; `version.json` churns more than once per run. The refresh must remain a **side effect, not a success condition**, along with the `views/build/` existence check and the `views.auto_regenerate: false` / `views.confirm_refresh: true` config keys.

### Claude's Discretion

- Whether `-w` is retained as the short flag for `--install-root` on either command.
- Exact field names, types, and defaults added to `DomainRecord` / `CardRecord` / `BridgesFile` under D-02 — derive them from what the parsers actually emit, not from the prd.
- Internal layout of `src/construct/views/lib/` (flat module set vs. a `parsers/` subpackage) and whether `views/generate.py` moves alongside it.
- Where the D-11 supersession is recorded (new ADR vs. PROJECT.md Key Decisions vs. both), and its exact wording.
- Whether the three capabilities share one refresh helper or each call the generator directly.
- Fate of `debounced_hook.py` and the skill's `requirements.txt` under D-09.
- How `OperationResult.message` surfaces `GenerateReport.warnings` (content warnings) distinctly from `validation_errors` (contract failures) — D-04 makes only the latter fatal.

### Deferred Ideas (OUT OF SCOPE)

- **Registry unification for the views group (RT-01/RT-02)** — declined by D-03. Stays open for v0.6.
- **Thin-wrapper migration for `construct-bridge-detect`, `construct-domain-init`, `construct-search-adjust`** — logged for v0.6 at `REQUIREMENTS.md:52`.
- **Workspace content repair** — the `missing required field(s): lifecycle` warnings across `test-ws/`. Fixture-data defects, not contract defects.
- **`views.generate_data` events.jsonl emission** — note it if the wiring makes it trivial, otherwise defer.
- **MCP tool count and skill inventory effects** — **Phase 17 (DOC-02) owns this**; do not edit the architecture doc set here.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIX-01 | `views.generate_data` over CLI or MCP yields real data or an honest documented absence; no permanent-failure handler remains; the `install_root` vs `workspace` contract and the deployed-skill-directory coupling are both decided | F1–F6 supply the exact model/adapter field set (criterion 1 + 3a), F6 the vendoring dependency gap (criterion 3b), F5 the verification design (criterion 1), F7 the refresh-node wiring (criterion 4), F11 the suite baseline (criterion 5) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| View data generation (`generate()`) | Python runtime (`views/`) | — | D-01/D-08: one implementation in the deterministic layer |
| Source-file parsing (15 lib modules) | Python runtime (`views/lib/`) | — | D-08 vendors these out of the skill directory; they ship with the package |
| Data-contract validation (17 Pydantic models) | Python runtime (`views/models.py`) | — | `extra="forbid"` is the enforcement gate; stays in the runtime layer |
| CLI invocation (`construct views generate`) | CLI (`cli.py` views_app) | — | D-03: hand-written Typer, deliberately bypasses the registry |
| MCP invocation (`construct_views_generate_data`) | Capability registry (`catalog.py`) | — | D-01: real handler replaces the failure lambda; reaches `generate()` by an independent path |
| Post-run views refresh | Python workflow layer (`llm/*_run.py`) | — | D-11/D-12: moves out of the skill/doc layer entirely; one owner |
| Skill orchestration (`run.sh`) | Claude skill layer | CLI | D-09: reduced to a CLI wrapper; holds no logic |
| Workspace discovery semantics | Python runtime (`views/lib/discover.py`) | — | D-05: defines install-root scoping; the reason the contract is install-root |

## Standard Stack

No new libraries. This phase moves existing code and reconciles existing contracts. The relevant question is not "what to add" but "what the vendored code needs that the package does not declare."

### Core (already declared, `pyproject.toml:11-20`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.7 (2.13 installed) | The 17 view data contracts | Already the project's contract layer [VERIFIED: pyproject.toml + probe output cites errors.pydantic.dev/2.13] |
| typer | >=0.12 | `views_app` CLI group | Already the CLI framework [VERIFIED: pyproject.toml:19] |
| ruamel.yaml | >=0.18 | YAML I/O across 6 runtime modules | The project's declared YAML convention [VERIFIED: grep — `ui/dashboard.py`, `llm/config.py`, `schemas/card.py`, `storage/workspace.py`, `services/init.py`, `services/knowledge.py`] |
| langgraph | >=0.2 | Curation/research/daily graph nodes | Hosts `views_refresh_hook` [VERIFIED: pyproject.toml:14] |

### The undeclared dependency (F6 — decision required)

| Library | Status | Impact |
|---------|--------|--------|
| PyYAML | **Not in `pyproject.toml` dependencies.** Present in `.venv` as 6.0.3 via transitive pull (langchain-core). [VERIFIED: `pip show pyyaml` returns nothing under `[project] dependencies`; `import yaml` succeeds → 6.0.3] | Two modules D-08 vendors (`lib/frontmatter.py`, `lib/parse_domains.py`) do `import yaml` at module load. `views/generate.py:281` also does a function-local `import yaml`. Vendoring makes this a **shipped-code** import that works only by accident of another package's transitive tree. |

**RESOLVED (user, 2026-07-19): Option A — declare `pyyaml>=6` in `pyproject.toml`.** D-08's "move, not a rewrite" invariant is load-bearing for D-02, so the vendored parsers stay untouched. Option B (port to ruamel) is recorded as a v0.6 convention-cleanup item. Original analysis retained:

**Two viable resolutions:**

| Option | Change | Tradeoff |
|--------|--------|----------|
| **A. Declare it** | Add `"pyyaml>=6"` to `pyproject.toml` dependencies | One line; zero behavioural risk; honours D-08's "move, not a rewrite" literally. But adds a second YAML library to a project that standardised on ruamel. |
| **B. Port to ruamel.yaml** | Rewrite the 3 `yaml.safe_load` call sites against `ruamel.yaml.YAML(typ="safe")` | No new dependency; matches the convention in 6 existing modules. But it **is** a rewrite of vendored parser code, which D-08 forbids ("the parsers' behavior must not change"). |

**Recommendation: Option A.** D-08's "move, not a rewrite" is explicit and load-bearing — D-02 depends on the parsers being untouched ground truth. Declaring the dependency preserves that invariant at the cost of one line. Option B is a v0.6 convention-cleanup item, not Phase 15 work.

**Verification commands run:**
```bash
.venv/bin/python -c "import yaml; print(yaml.__version__)"   # 6.0.3
grep -n "dependencies" -A10 pyproject.toml                     # no pyyaml
grep -ln "import yaml" .../lib/*.py                            # frontmatter.py, parse_domains.py
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| PyYAML | PyPI | ~20 yrs | ~300M/mo | github.com/yaml/pyyaml | [OK] | Approved (Option A only) — already resolved in the live venv at 6.0.3 |

**Packages removed due to [SLOP] verdict:** none — this phase installs no new third-party code.
**Packages flagged as suspicious [SUS]:** none.

PyYAML was not discovered by search; it was found already installed and already imported by in-repo code. [VERIFIED: local venv resolution]

## Architecture Patterns

### F1 — The pipeline has THREE layers, not two (the key finding)

CONTEXT.md frames this as parsers vs. models. The code has an undocumented layer between them:

```
skill-lib parsers          _FILE_MODEL_MAP adapters        Pydantic models
(lib/parse_*.py)     →     (generate.py:95-165)      →     (views/models.py)
raw dicts                  reshaped dicts                  validation gate
                           ↑ THIS is what gets
                             validated AND written
```

The adapters actively rename and drop fields. For `cards.json` (`generate.py:118-127`):

```python
# Source: src/construct/views/generate.py:118-127 [VERIFIED: read]
{
    "summary":     c.get("summary_excerpt", c.get("body_markdown", "")),  # renamed
    "connections": c.get("connects_to", []),                              # renamed
    # parser fields dropped entirely: tags, author, created, last_reviewed,
    #                                 sources, body_markdown
}
```

For `domains.json` and `bridges.json` the adapter is a **pass-through** (`generate.py:97-98`) — parser output hits the model verbatim, which is why those two produce `extra_forbidden` and cards produces a type error instead.

**Consequence:** D-02's "models move, not parsers" is unambiguous for domains and bridges. For cards it is ambiguous, because the shape is set by the adapter, and an adapter is not a parser. See OQ-1.

### F2 — `spec-v02-data-model.md` independently corroborates the parsers

Each parser docstring cites the spec ("Per data-model spec §5.1"), and the spec's JSON schemas match the parser output field-for-field. [VERIFIED: `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md:104-165`]

This upgrades D-02 substantially. The decision was reasoned as "the parsers plus the deployed SPA are ground truth" — but no in-tree SPA consumes generated data (see F9), so that leg was weak. The spec supplies a second, stronger leg: the parsers implement a written contract, and `views/models.py` diverges from it. **D-02 is not a preference; it is a spec-conformance fix.**

The spec is also the answer to the discretion item "derive them from what the parsers actually emit" — it names the types the parsers only imply.

### F3 — The models contain phantom fields the parsers never emit

The fix is not purely additive. `DomainRecord` and `BridgeSummary` each carry fields absent from both the parsers and the spec:

**`DomainRecord` (`models.py:91-103`)** [VERIFIED: read]

| Model field | Parser emits? | In spec §5.1? | Disposition |
|---|---|---|---|
| `id`, `name`, `description` | yes | yes | keep |
| `card_count`, `connection_count`, `digest_count`, `article_count`, `keywords` | **no** | **no** | phantom — invented; default to 0/[] and would be written as dead data |
| `status`, `created`, `content_categories`, `source_priorities`, `cross_domain_links`, `metrics` | yes | yes | **missing — add** |

Only 3 of 8 model fields are real. The parser's `metrics` sub-dict (9 keys) carries the counts the phantom scalar fields were reaching for. **Recommendation: delete the 5 phantom fields.** Keeping them writes zeros into `domains.json` that no consumer reads and that contradict `metrics`. Nothing references them anywhere in the repo. [VERIFIED: grep across `src/`, `tests/`, `views/design-example/src/` — zero hits]

**`BridgeSummary` (`models.py`)** [VERIFIED: read] — has `totals` (real), plus `l1_l2_only`, `l3_calls`, `l3_candidates_eligible`, `l3_candidates_total` (parser never emits; `_build_summary` at `parse_bridges.py:320-343` returns exactly `{totals, top_domain_pairs}`). Add `top_domain_pairs`; the L3 fields have a plausible provenance in the bridge-detection gate and are **safer to leave** than the domain phantoms — flag rather than delete.

### F4 — `connections` is provably `list[str]`

Not merely observed in the probe — determined by the code:

```python
# Source: lib/parse_connections.py:79 [VERIFIED: read]
def denormalize_into_cards(cards, connections) -> None:
    ...
    for cid, nset in neighbours.items():
        by_id[cid]["connects_to"] = sorted(nset)   # set of target IDs → list[str], always
```

Corroborated by spec §5.2: `"connects_to": ["other-card-id", ...]` with the explicit note *"`connects_to` is a denormalised list of card IDs this card connects to (any direction). The full edge list with types lives in `connections.json`."* [VERIFIED: spec-v02-data-model.md:159-165]

`CardRecord.connections: list[dict]` is unambiguously wrong regardless of how OQ-1 resolves.

### Recommended structure for D-08

```
src/construct/views/
├── __init__.py
├── generate.py           # keep in place; delete sys.path block (:43-51)
├── models.py             # D-02 edits here
└── lib/                  # NEW — 15 modules moved verbatim
    ├── __init__.py
    ├── discover.py       # install-root semantics (D-05 evidence)
    ├── fingerprint.py    # incremental dedupe (D-12 relies on it)
    ├── frontmatter.py    # imports yaml
    ├── parse_domains.py  # imports yaml
    ├── parse_bridges.py  # 438 lines, largest
    └── ...
```

**Recommendation: flat module set, `generate.py` stays put.** The imports at `generate.py:55-70` become `from construct.views.lib import (...)` — a one-line-per-import change. A `parsers/` subpackage would split `discover`/`fingerprint`/`build_id`/`envelope` (not parsers) from the `parse_*` modules, adding a naming decision for no benefit. Verified module inventory: 15 files, 1,496 lines, largest `parse_bridges.py` (438) and `parse_digests.py` (255). [VERIFIED: `wc -l`]

### Anti-Patterns to Avoid

- **Unifying the views group into the registry.** `views_app` is hand-written Typer (`cli.py:860`) while 26 other capabilities dispatch through `catalog.py`. D-03 preserves this knowingly. Do not "helpfully" fix it.
- **Relaxing `extra="forbid"`.** Explicitly rejected in D-02. It would produce `success=True` while gutting the guarantee.
- **Making the views refresh a success condition.** D-12: side effect only. A failed refresh never flips workflow status.
- **Rewriting parser logic during the D-08 move.** D-02 depends on the parsers being untouched. Move bytes, change only the import lines.
- **Editing the architecture doc set.** Phase 17 owns `artifact-catalog.md` and friends.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verifying generation succeeded | A bespoke JSON field-checker in tests | `construct views validate --install-root <root>` | Already exists (`cli.py:868-895`), already maps all 8 files to their models. Ready-made verification path. |
| Avoiding redundant sweeps under D-12 | A parent/child run tracker | `lib/fingerprint.py` + `generate.py`'s `old_ws_fps`/`changed_ws` pass | Already makes repeat sweeps near-no-ops. This is *why* D-12's three-sweeps rule is acceptable, and why Phase 13 D-09's no-parent-graph survives. |
| Separating fatal from advisory output | A new result structure | `GenerateReport.validation_errors` vs `.warnings` | Already the exact D-04 distinction. Confirmed: fresh workspace → 0 warnings; `test-ws` → content warnings only. |
| Scaffolding a clean workspace for tests | Hand-built fixture dirs | `services/init.initialize_workspace(root, DomainInitInput(...))` | D-04's named target. Signature verified below. |
| Envelope/flat payload handling | New unwrapping logic | `views/models.py::unwrap_payload` (:292) | Already handles both shapes; D-02 does not disturb it. |

**Key insight:** Every mechanism this phase needs already exists. The work is reconciliation and relocation, not construction. The only genuinely new artefacts are the `views generate` CLI command, the refresh helper, and the D-11 decision record.

## Runtime State Inventory

This is a move/refactor phase (D-08 vendoring, D-09 skill reduction, D-11 doc removal). What survives a file-level edit:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `views/build/data/*.json` is a derived cache — spec §2 states "fully rebuildable, never canonical". `_build_meta.json` holds workspace fingerprints; a model shape change makes cached fingerprints match while output shape differs. | Regeneration is the migration. **Delete `views/build/` (or bump a cache key) once after D-02 lands** so fingerprints do not suppress a rewrite of already-current workspaces. Verified mechanism: `fp.load_meta(data_dir)` → `old_ws_fps` → `changed_ws` (`generate.py:194-200`). |
| **Live service config** | None. No external service holds views state. | None — verified: no service config references `views/build`. |
| **OS-registered state** | `debounced-hook.sh` + `debounced_hook.py` in the skill dir — a file-watch hook that shells out to the deleted `generate.py`. If registered anywhere as a Claude hook, it breaks at D-09. | Review under D-09 (already a discretion item). It has its own `import yaml` and its own path assumptions. |
| **Secrets / env vars** | None — views generation reads no secrets. | None. |
| **Build artifacts / installed packages** | The skill's own `.venv/` (present on disk, `.gitignore`d) becomes orphaned at D-09 when `run.sh` stops bootstrapping it. `requirements.txt` (`pyyaml>=6.0`) becomes dead. | Delete both under D-09. Also: an editable install picks up `views/lib/` automatically, but a **built wheel** must include it — `packages = ["src/construct"]` (`pyproject.toml:38`) covers subpackages provided `views/lib/__init__.py` exists. |

## Common Pitfalls

### Pitfall 1 (F5): D-04's done-bar does not exercise the cards fix

**What goes wrong:** A freshly scaffolded workspace has **zero cards**, so `cards.json` is an empty list and `CardRecord.connections` is never instantiated. The done-bar passes with the `list[dict]` bug still present.

**Verified by direct execution** — scaffolded via `services/init.initialize_workspace` then ran `generate()`:

```
FRESH-WORKSPACE success: False
validation_errors: 2          ← domains.json (6 errors), bridges.json (1 error)
warnings: 0
```

Versus the populated `test-ws` probe: **3** errors including `cards.0.connections.0`. The fresh workspace surfaces **2 of 3**. [VERIFIED: both runs executed this session]

**How to avoid:** Verification needs both targets. Fresh workspace proves the D-04 done-bar (`success=True`, zero errors, zero warnings — the zero-warnings result confirms D-04's rationale for excluding `test-ws` content noise is sound). A **populated** workspace with connected cards proves the cards fix. Candidates: `tests/fixtures/v02/multi-domain-medium/` (exists, has `views/` dirs) or a copy of `test-ws/`.

**Warning sign:** a green D-04 check on a workspace whose `cards.json` is `{"cards": []}`.

### Pitfall 2: Fingerprint cache masks the model change

**What goes wrong:** After widening the models, re-running `generate()` against a previously generated root can skip unchanged workspaces — the fingerprint matches, so the new shape is never written.
**How to avoid:** Clear `views/build/` before verification runs, or assert on a fresh output directory.

### Pitfall 3 (F7): `_deferred_step` becomes dead code

**What goes wrong:** D-10 replaces the only call site. `_deferred_step` (`curation_run.py:354`) is referenced exactly twice in the entire `llm/` package — its definition at :354 and its single use at :982, which is `views_refresh_hook`. [VERIFIED: `grep -n "_deferred_step" src/construct/llm/*.py`]

CONTEXT.md asked to "check whether other nodes still use it before altering its signature." Answer: **no other node uses it.** Removing D-10's call orphans the helper, along with its stale `reason="deferred to Phase 12"` string.
**How to avoid:** Delete the helper with its last caller. Leaving it invites a future node to reintroduce fake-success semantics — the exact pattern `workflow.run` was removed for (catalog.py D-10/CUR-05 comment).

### Pitfall 4: Doubled path segments in warnings (located)

CONTEXT.md flagged this as cosmetic and worth a look. Root cause found:

```python
# lib/parse_cards.py:18 — parser already qualifies with the workspace name
rel = f"{workspace.name}/cards/{md_file.name}"
warnings.append({"workspace": workspace.name, "file": rel, ...})

# src/construct/views/generate.py:385-389 — formatter prepends it again
for w in _warnings:
    warnings_list.append(f"{ws}/{f}: {r}")     # → my-construct/my-construct/cards/...
```

**Fix belongs at `generate.py:389`, not in the parsers** — D-08 forbids touching parser behaviour, and the parsers' `file` key is self-consistent (`parse_connections.py` and `parse_domains.py` qualify the same way). Emit `f"{f}: {r}"`, or only prepend when `f` does not already start with `ws`. [VERIFIED: read both sites]

### Pitfall 5: Circular imports — assessed, not a risk

D-12 adds three call sites from `llm/` into `views/`. Direction check: `views/` imports **nothing** from `llm/`; `llm/research_run.py:644` **already** imports `construct.views.models` (function-local, inside `_write_digest`). [VERIFIED: grep both directions]

So the dependency edge `llm → views` already exists and is acyclic. Precedent also exists for the function-local import style, which is the safer pattern if `views/generate.py`'s module-level parser imports prove heavy at CLI startup.

### Pitfall 6: `--workspace .` in the docs D-11 removes

All three refresh sections invoke `construct views generate --workspace .` [VERIFIED: `construct-research-cycle/SKILL.md:109`, `construct-curation-cycle/SKILL.md:122`, `workflows/daily-cycle.md:106`]. Under D-05/D-06 the flag is `--install-root`, and `.` is the wrong value (a workspace, not a root — `discover_workspaces` would find zero children). D-11 removes these sections entirely, so **no rewrite is needed** — but do not "fix" the flag in a section that is being deleted. The remediation string at `:113`/`:128`/`:112` goes with them, resolving criterion 4.

## Code Examples

### The install-root semantics that prove D-05

```python
# Source: lib/discover.py:16 [VERIFIED: read]
def discover_workspaces(install_root: Path) -> list[Path]:
    workspaces = []
    for entry in sorted(install_root.iterdir()):   # CHILDREN only
        if not entry.is_dir():                     # → passing a single workspace
            continue                               #   yields [] and silently
        if _is_workspace(entry):                   #   emits empty views
            workspaces.append(entry)
    return workspaces
```

Combined with `cli.py:893` (`workspace / "views" / "build" / "data"`), the views group is already de facto install-root-scoped and merely misnamed — exactly as D-05 states.

### Canonical domain shape (spec + parser agree)

```jsonc
// Source: CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md:104-130 [CITED]
// Emitted verbatim by lib/parse_domains.py:31-42 [VERIFIED: read]
{
  "id": "cosmology", "name": "Cosmology", "description": "...",
  "status": "active",                              // active | paused | archived
  "created": "2026-04-22",
  "content_categories": ["string"],                // parser: list[str], defaults []
  "source_priorities": ["string"],                 // parser: list[str], defaults []
  "cross_domain_links": [{"to": "climate-policy", "note": "..."}],  // list[dict], defaults []
  "metrics": {
    "papers": 47, "cards": 120,
    "cards_by_lifecycle": {"seed": 18, "growing": 60, "mature": 38, "archived": 4},
    "cards_by_confidence": {"1": 5, "2": 22, "3": 51, "4": 30, "5": 12},
    "connections": 184, "orphan_cards": 3, "avg_confidence": 3.12,
    "last_research_cycle": "2026-04-25", "last_curation_cycle": "2026-04-26"
  }
}
```

Note `cross_domain_links` is `list[dict]` per spec, but `parse_domains.py:39` passes it through with only an `isinstance(list)` guard — element type unvalidated. A nested `CrossDomainLink` model would be *stricter than the parser guarantees* and could fail on legacy `domains.yaml`. **Recommend `list[dict]`** and note the gap.

### Bridges summary shape

```python
# Source: lib/parse_bridges.py:320-343 [VERIFIED: read]
return {"totals": totals,                     # BridgeSummary.totals — exists
        "top_domain_pairs": top_pairs}        # MISSING from BridgeSummary — add
# top_pairs element:
{"domains": ["a", "b"], "confirmed": 3, "strong_candidates": 1, "avg_score": 0.72}
```

→ `top_domain_pairs: list[dict] = Field(default_factory=list)`.

### The failure lambda criterion 1 targets

```python
# Source: src/construct/capabilities/catalog.py:310-318 [VERIFIED: read]
registry.register(CapabilityRecord(
    id="views.generate_data",
    input_model=ViewsGenerateDataInput,               # :149-150 — workspace: Path → install_root: Path (D-05)
    output_model=OperationResult,
    handler=lambda **kwargs: OperationResult(success=False,
             message="Not yet implemented — see Plan 02"),   # :317 — D-01 replaces
    mcp_tool_name="construct_views_generate_data",
))
```

Adjacent pattern for a real handler, same file (`catalog.py:307`): `handler=lambda workspace: graph_status(workspace)`, with a comment noting it must accept both positional and keyword forms. The `views.generate_data` handler should follow suit and map `GenerateReport` → `OperationResult` — surfacing `validation_errors` as fatal and `warnings` as advisory (the open discretion item).

### D-04 verification harness (executed this session — reusable)

```python
# [VERIFIED: run successfully against src/ this session]
from construct.services.init import initialize_workspace, DomainInitInput
from construct.views.generate import generate

initialize_workspace(root / "demo", DomainInitInput(
    domain_id="demo", display_name="Demo", scope="test scope",
    taxonomy_seeds=["t1"], source_priorities=["arxiv"], research_seeds=["seed one"],
))
report = generate(root)          # note: root, NOT root/"demo" — D-05
assert report.success and not report.validation_errors
```

`initialize_workspace` writes `domains.yaml` **inside** the workspace; `parse_domains` handles this via its per-workspace fallback (`parse_domains.py:21-27`), so no root-level `domains.yaml` is required. [VERIFIED: signature `(root: str | Path, domain: DomainInitInput) -> Path`; `DomainInitInput(domain_id, display_name, scope, taxonomy_seeds, source_priorities, research_seeds)`]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Skill-owned views refresh, parent owns the single sweep | Python capability owns it; every workflow refreshes | Phase 15 (D-11/D-12) | Reverses Phase 13 D-10. Must be recorded in a live document — the v0.4 milestone archive is read-only. |
| Skill standalone via per-skill venv bootstrap | Skill requires installed CONSTRUCT | Phase 15 (D-09) | `run.sh`'s PEP-668 workaround retires; `requirements.txt` and the orphaned `.venv/` go with it. |
| Views logic imported from a deployed skill dir via `sys.path` | Vendored into the shipped package | Phase 15 (D-08) | Fixes a genuine install-time `ImportError` — verified: `_PROJECT_ROOT = parents[3]` resolves to repo root, and `pyproject.toml:38` ships only `src/construct`. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 5 phantom `DomainRecord` fields are safe to delete because nothing reads them | F3 | Low — grep across `src/`, `tests/`, and the SPA found zero references, but an out-of-tree deployed SPA could read them. Mitigated by F9: no such consumer is reachable to check. |
| A2 | `BridgeSummary`'s L3 fields should be kept rather than deleted | F3 | Low — they plausibly serve the bridge-detection gate. Keeping an unused optional field is harmless; deleting a used one is not. |
| A3 | `cross_domain_links` should be `list[dict]` rather than a nested model | Code Examples | Low — a stricter model could fail on legacy `domains.yaml` the parser accepts. |
| A4 | Option A (declare PyYAML) is preferable to Option B (port to ruamel) | Standard Stack | Low — turns on reading D-08's "move, not a rewrite" as binding. If the project prefers dependency minimalism, B is defensible but contradicts D-08. |
| A5 | A wheel build picks up `views/lib/` automatically given `__init__.py` | Runtime State | Low — standard hatchling package-directory behaviour, but this project has a custom build hook (`hatch_build.py`) that was not inspected. **Worth one build-and-inspect check.** |

## Open Questions

**OQ-1 — RESOLVED (user, 2026-07-19): reading (a), the narrow one. `views/models.py` moves; `_FILE_MODEL_MAP` is left alone.** Reading (b) is recorded below as a v0.6 candidate. Original analysis retained for the record:

**OQ-1 (was blocking Wave 2): Does D-02 move `views/models.py`, or `_FILE_MODEL_MAP` too?**

- **What we know:** D-02 says "the models move, not the parsers," and rejects narrowing the parsers *because it changes what lands in `views/build/data/`*. For `domains.json` and `bridges.json` there is no ambiguity — the adapters are pass-throughs, so only the models change. For `cards.json` the adapter (`generate.py:118-127`) invents the shape: it renames `connects_to`→`connections` and `summary_excerpt`→`summary`, and drops six parser fields.
- **What's unclear:** an adapter is neither a parser nor a model. D-02 does not say which side of its rule it falls on.
- **Two readings:**
  - **(a) Narrow — models only.** Set `CardRecord.connections: list[str]`, leave adapters alone. Minimal diff; strictly honours "models move, not parsers"; written output is unchanged except for the type correction. **But** it locks in a `cards.json` shape matching neither the parsers nor spec §5.2.
  - **(b) Wide — adapters pass through, models absorb the spec shape.** `cards.json` regains `connects_to`, `summary_excerpt`, `tags`, `author`, `sources`, `body_markdown`. Fully spec-conformant. **But** it changes what lands in `views/build/data/` — precisely what D-02's rejected branch was rejected for, even though the rejection targeted the parsers.
- **Recommendation: (a), the narrow reading.** It is the minimal change that satisfies criterion 1, keeps the diff auditable, and cannot break an unknown consumer. Reading (b) is a genuine improvement but is a data-contract change, and this milestone's own rule is "no new runtime capability — fix what exists" (`REQUIREMENTS.md`, Out of Scope). Record (b) as a v0.6 candidate: *"align `cards.json` with spec-v02-data-model §5.2."*
- **Note for the planner:** F9 weakens the stated rationale in both directions — see below. The recommendation stands on milestone scope, not on SPA risk.
- **DECISION (user, 2026-07-19): (a) narrow — models only.** Set `CardRecord.connections: list[str]`; adapters at `generate.py:95-165` are not touched this phase. Rationale accepted as stated: v0.4.1's "no new runtime capability — fix what exists" rule governs, and the minimal diff cannot break an unverifiable out-of-tree consumer. **Carry to v0.6 backlog:** "align `cards.json` with spec-v02-data-model §5.2" (reading (b)). The planner must treat any adapter reshaping as out of scope.

**OQ-2 (non-blocking): F9 — no in-tree consumer of generated view data exists.**

- **What we know:** D-02 reasons that narrowing parsers "changes what lands in `views/build/data/`, which deployed SPAs already read." Verified: `views/build/` **does not exist** in this repo. The only SPA, `views/design-example/`, imports its own bundled `src/data/*.json` (`Home.jsx:3-4`) and never fetches generated data. No `.jsx` references `card_count`, `metrics`, `connects_to`, or `top_domain_pairs`. [VERIFIED: find + grep]
- **What's unclear:** whether a deployed SPA exists outside this repo. Cannot be determined from here.
- **Recommendation:** Do not weaken D-02 — F2 (spec corroboration) replaces the SPA leg with a stronger one, so the decision holds on better evidence than it was made on. **Record this in the phase summary**: the "deployed SPA is ground truth" premise is unverifiable in-repo, and the v0.2 data-model spec is the durable authority. This matters for Phase 17, which owns the architecture doc set.

**OQ-3 (non-blocking): `debounced_hook.py` fate under D-09.**

- **What we know:** It shells out to the `generate.py` D-09 deletes, has its own `import yaml`, and pairs with `debounced-hook.sh`. Already a discretion item.
- **Recommendation:** delete both alongside `requirements.txt` and the orphaned `.venv/`. If the debounce behaviour is wanted, it belongs in the Python layer — but that is new capability, out of scope for v0.4.1.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | ✓ | 3.13 (`.venv`), `requires-python >=3.11` | — |
| pydantic | Model reconciliation | ✓ | 2.13 | — |
| PyYAML | Vendored `frontmatter.py`, `parse_domains.py` | ✓ (transitive, **undeclared**) | 6.0.3 | Declare it (Option A) or port to ruamel (Option B) — see Standard Stack |
| ruamel.yaml | Existing runtime YAML | ✓ | >=0.18 | — |
| pytest | Verification | ✓ | 9.x | — |
| `test-ws/` populated fixtures | Pitfall 1 verification | ✓ | — | `tests/fixtures/v02/multi-domain-medium/` |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** PyYAML is *available but undeclared* — a packaging defect D-08 promotes into shipped code. Not blocking; requires an explicit one-line decision.

**Note:** the project venv is at `./.venv/`; bare `python3` lacks pydantic. All verification commands must use `.venv/bin/python`. [VERIFIED: bare `python3 -c "import pydantic"` → ModuleNotFoundError]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | `pyproject.toml:40-42` — `testpaths=["tests"]`, `pythonpath=[".", "src"]` |
| Quick run command | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py tests/contract/test_doc_command_references.py -q` |
| Full suite command | `.venv/bin/python -m pytest -q` |

**Baseline: 443 passed, 2 warnings, 6.03s.** [VERIFIED: executed this session] The whole suite runs in six seconds — cheap enough to run the full suite at every task commit rather than a subset.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIX-01 / crit.1 | No failure lambda; MCP handler returns a real result | unit | `pytest tests/unit/test_capability_registry.py -x` | ✅ (extend) |
| FIX-01 / crit.1 | `generate()` → `success=True`, 0 errors on a **fresh** workspace (D-04) | integration | `pytest tests/integration/test_views_generate.py::test_fresh_workspace_generates_clean -x` | ❌ Wave 0 |
| FIX-01 / crit.1 | `generate()` → 0 errors on a **populated** workspace (Pitfall 1 — exercises `CardRecord.connections`) | integration | `pytest tests/integration/test_views_generate.py::test_populated_workspace_generates_clean -x` | ❌ Wave 0 |
| FIX-01 / crit.2 | `("views","generate")` gone from `_KNOWN_BROKEN`; CLI resolves | contract | `pytest tests/contract/test_doc_command_references.py -x` | ✅ (self-enforcing) |
| FIX-01 / crit.3a | `ViewsGenerateDataInput.install_root`; both commands take `--install-root` | unit | `pytest tests/unit/test_capability_registry.py -k views -x` | ✅ (extend) |
| FIX-01 / crit.3b | No `sys.path` injection; `views.lib` imports from the installed package | unit | `pytest tests/unit/test_views_lib_imports.py -x` | ❌ Wave 0 |
| FIX-01 / crit.4 | Refresh runs as a side effect; failure never flips workflow status | integration | `pytest tests/llm -k views_refresh -x` | ❌ Wave 0 |
| FIX-01 / crit.5 | Full suite green, no new `_KNOWN_BROKEN` | full | `.venv/bin/python -m pytest -q` | ✅ |

**Note on the D-02 model edits:** `tests/contract/test_views_contracts.py` constructs `BridgeSummary(...)`, `CardRecord(...)`, and `DomainRecord` directly (lines 103, 110, 261, 335-337). Widening the models is source-compatible for added-with-default fields, but **deleting the 5 phantom `DomainRecord` fields (F3) is a breaking change** if any test passes them. Grep before deleting. The file uses class-based grouping (`grep -c "^def test"` → 0), so count tests via `pytest --collect-only`.

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest -q` — the whole suite is 6s; no reason to sample.
- **Per wave merge:** full suite + `construct views validate --install-root <fresh-root>` reporting all 8 files passing.
- **Phase gate:** full suite green, `_KNOWN_BROKEN` contains exactly 4 entries (5 minus `("views","generate")`), and both the fresh and populated generation tests pass before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/integration/test_views_generate.py` — fresh + populated generation, covers FIX-01 criterion 1 and closes Pitfall 1
- [ ] `tests/unit/test_views_lib_imports.py` — asserts `construct.views.lib` imports with no `sys.path` mutation, covers criterion 3b
- [ ] Shared fixture: scaffolded install root via `services.init` (harness verified above) — belongs in `tests/conftest.py` or a views-local `conftest.py`
- [ ] Populated-workspace fixture selection: reuse `tests/fixtures/v02/multi-domain-medium/` (exists) rather than copying `test-ws/`
- [ ] Framework install: none needed — pytest present, suite green at 443

## Security Domain

`security_enforcement` is not disabled in `.planning/config.json` (key absent → enabled). This phase moves trusted first-party code and edits contracts; it adds no network, auth, or user-input surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface in this phase |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Local-first, single-user; no multi-tenant boundary |
| V5 Input Validation | **yes** | Pydantic models with `extra="forbid"` — the phase's central mechanism. D-02 preserves strictness deliberately. |
| V6 Cryptography | no | `parse_connections._stable_id` uses SHA-256 as a **non-security** content hash for stable IDs; same for `lib/fingerprint.py`. Not a crypto control. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| YAML deserialisation via untrusted `domains.yaml` / card frontmatter | Tampering / EoP | `yaml.safe_load` — **already used** at `parse_domains.py:50` and in `frontmatter.py`. Preserve verbatim through D-08's move; a `yaml.load` regression during vendoring would be a real vulnerability. |
| Path traversal via workspace/card names into `views/build/data/<ws_id>/` | Tampering | `discover_workspaces` iterates real `iterdir()` entries and excludes dotfiles/underscore/known cruft (`discover.py:8-30`). Names are directory names, not user strings. |
| `extra="forbid"` relaxation silently admitting unvalidated fields | Tampering | Explicitly rejected by D-02. Guard it: the phase should not weaken any `model_config`. |
| Vendored code drifting from its reviewed source | Tampering | D-08 is a verbatim move. A byte-level diff of the 15 modules (imports excepted) is the control. |

**Phase-specific security check:** after D-08, `grep -rn "yaml.load\|sys.path" src/construct/views/` should return nothing.

## Sources

### Primary (HIGH confidence)

- Live execution — `generate()` against a `test-ws/` copy: `success=False`, 3 validation errors (18/16/1), matching CONTEXT.md D-01 exactly
- Live execution — `generate()` against a `services/init`-scaffolded fresh workspace: 2 validation errors, 0 warnings (Pitfall 1)
- Live execution — `.venv/bin/python -m pytest -q`: 443 passed, 6.03s
- Direct source reads: `capabilities/catalog.py:140-160,305-325`, `views/generate.py:1-60,95-200,281,385-389`, `views/models.py` (DomainRecord/CardRecord/BridgeSummary/BridgesFile), `cli.py:855-900`, `llm/curation_run.py:975-985`, `tests/contract/test_doc_command_references.py:150-221`, all 15 `lib/*.py` modules, `pyproject.toml`, `services/init.py`
- `CONSTRUCT-CLAUDE-spec/spec-v02-data-model.md:95-175` — §5.1/§5.2 canonical schemas (F2)

### Secondary (MEDIUM confidence)

- `.planning/milestones/v0.4-MILESTONE-AUDIT.md:139-141` — corroborates the three broken `construct views generate` doc references
- `views/design-example/src/` — SPA inspection establishing F9 (absence of a generated-data consumer)

### Tertiary (LOW confidence)

- None. No web search was required; every claim resolved against the working tree or an in-repo spec.

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no new libraries; the one dependency question (PyYAML) verified by direct import and `pyproject.toml` read
- Architecture: **HIGH** — three-layer pipeline confirmed by source read and corroborated by spec; only OQ-1 is a judgement call, and both readings are documented with a recommendation
- Field derivation (D-02 discretion item): **HIGH** — parser source and spec agree field-for-field; probe output confirms
- Pitfalls: **HIGH** — Pitfalls 1, 3, 4, 5 each verified by execution or grep, not inferred
- D-11/D-12 doc surface: **HIGH** — all three refresh sections and the remediation string located at exact lines
- F9 (no SPA consumer): **MEDIUM** — proven absent in-repo; an out-of-tree deployed SPA cannot be ruled out from here

**Research date:** 2026-07-19
**Valid until:** 2026-08-18 (30 days — stable internal codebase; invalidated earlier only if `views/` or the skill directory is edited outside this phase)
