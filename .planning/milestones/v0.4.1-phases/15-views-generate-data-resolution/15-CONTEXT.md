# Phase 15: views.generate_data Resolution - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Give `views.generate_data` one honest, working outcome across every surface that names it (FIX-01):

1. Remove the permanent-failure lambda at `capabilities/catalog.py:317` by **wiring the real generator**.
2. Delete `("views", "generate")` from `_KNOWN_BROKEN` — which forces a real `construct views generate` CLI command into existence.
3. Record explicit decisions for the two ambiguities criterion 3 names: **`install_root` vs `workspace`** and the **deployed-skill-directory import coupling**.
4. Make the post-run views refresh honest across curation-cycle, research-cycle, and daily-cycle.

**Scope warning for the planner — read before sizing.** This is *not* a stub-removal phase. The decisions below make it four substantial pieces of work: a data-contract reconciliation (~35+ Pydantic mismatches), a 1,496-line library vendoring, a skill reduced to a CLI wrapper, and a deliberate reversal of a v0.4 architectural decision (Phase 13 D-10). Every one was chosen knowingly. Plan waves accordingly; do not compress.

**Not in scope:** broad RT-01/RT-02 registry unification (see D-03), workspace-format changes, new capabilities beyond the refresh relocation in D-11/D-12.

</domain>

<decisions>
## Implementation Decisions

### Resolution direction (criterion 1)

- **D-01:** `views.generate_data` is **wired to the real implementation** at `views/generate.py:175`, not retired from the registry. The `OperationResult(success=False, "Not yet implemented — see Plan 02")` lambda at `catalog.py:317` is replaced by a real call.

  **Evidence gathered during discussion (do not re-derive):** a live probe ran `generate()` against a copy of `test-ws/`. It executes and writes files, but returns `success=False` because `views/models.py`'s Pydantic contracts disagree with what the skill-lib parsers emit:

  | File | Mismatch |
  |---|---|
  | `domains.json` | 18 `extra_forbidden` — parser emits `status`, `created`, `content_categories`, `source_priorities`, `cross_domain_links`, `metrics`; `DomainRecord` (models.py:91-103) forbids all six |
  | `cards.json` | 16 errors — parser emits `connections` as `list[str]` of card IDs; model expects `list[dict]` |
  | `bridges.json` | `summary.top_domain_pairs` forbidden |

  Wiring therefore **requires** the reconciliation in D-02. The retire branch (also accepted by criterion 1) was considered and rejected.

- **D-02:** The **models move, not the parsers.** The skill-lib parsers plus the deployed SPA are ground truth; `views/models.py` is a narrower contract than reality. Add the missing fields to `DomainRecord`, `CardRecord`, and `BridgesFile`, and correct `connections` to `list[str]`.

  **`model_config = ConfigDict(extra="forbid")` stays on all 17 models.** The models remain strict — they are corrected to describe the real shape, not loosened. Relaxing to `extra="ignore"` was explicitly rejected: it would satisfy `success=True` while gutting D-02's schema-validated-generator guarantee, trading a failing gate for a toothless one.

  Narrowing the parsers to match the models was rejected because it changes what lands in `views/build/data/`, which deployed SPAs already read.

- **D-03:** The forced `construct views generate` command is **hand-written alongside `validate`** at `cli.py:868`, calling the generator directly — matching how the views group already works. It does **not** route through the capability registry.

  **Consequence, recorded deliberately:** CLI and MCP reach the same function via two independent code paths and can drift. RT-01/RT-02 **stays open** for the views group; the bounded exception at `REQUIREMENTS.md:51` is declined. PROJECT.md's "⚠️ Revisit" note on registry coverage remains accurate after this phase.

- **D-04:** **Definition of done for "wired":** `generate()` returns `success=True` with zero `validation_errors` against a **freshly scaffolded workspace** (via `services/init.py`). Historical content in `test-ws/` is **out of scope** — the probe surfaced per-card content warnings (`missing required field(s): lifecycle`) that originate in fixture data this phase does not own.

  Verification must therefore scaffold a clean workspace rather than assert against `test-ws/`.

### install_root vs workspace contract (criterion 3, first half)

- **D-05:** The contract is **install root**, recorded explicitly. `views.generate_data` is deliberately the one install-root-scoped capability: it aggregates every discovered workspace into a single SPA at `<install_root>/views/build/`. `ViewsGenerateDataInput.workspace` becomes `install_root: Path`.

  **Evidence:** `discover_workspaces()` (`lib/discover.py:16`) scans only the *children* of its argument — passing a single workspace finds zero and silently emits empty views. `views validate` at `cli.py:893` already does `workspace / "views" / "build" / "data"`, i.e. it is *de facto* install-root-scoped and merely misnamed. Both the curation-cycle and daily-cycle docs already say "if `views/build/` exists **at the install root**" — install-root was always the intent; only the `--workspace .` flag contradicted it.

- **D-06:** **Both** views commands are renamed to `--install-root`. `generate` and `validate` name the same concept the same way; the group becomes internally consistent and the contract self-evident. The `-w` short flag's fate is the planner's call (see Discretion).

- **D-07:** The **two `USER-TEST-PLAYBOOK-v03.md` invocations are fixed in this phase** (`:333`, `:411` — `construct views validate -w "$WS"`), a deliberate crossing of Phase 14 D-02's edit fence, following the precedent D-03 set for `config-topology.md`. Phase 16 (DOC-04) may retire the playbook wholesale; **no cross-phase dependency is created and Phase 15 must not block on Phase 16.**

### Skill-lib import coupling (criterion 3, second half)

- **D-08:** All 15 modules under `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/lib/` (~1,496 lines) are **vendored into `src/construct/views/lib/`**, and the `sys.path` injection at `generate.py:43-51` is deleted.

  **Evidence:** `pyproject.toml:38` packages only `src/construct`, so the skill lib does not ship. `_PROJECT_ROOT = Path(__file__).resolve().parents[3]` resolves to the repo root — the module imports successfully **only inside a dev checkout**. An installed CONSTRUCT raises `ImportError` at module load, before any handler runs.

  This is a **move, not a rewrite**. The parsers' behavior must not change — D-02 already established them as ground truth.

- **D-09:** The skill **becomes a CLI wrapper.** Its `lib/` and `generate.py` are deleted; `run.sh` becomes a call to `construct views generate --install-root "$1"`. One implementation exists, in the Python layer, realising PROJECT.md's "Python is the deterministic enforcement layer; skills orchestrate flow" principle.

  **Accepted cost, recorded:** the skill stops being standalone. `run.sh` today bootstraps a per-skill venv with PyYAML only (no CONSTRUCT install required); that bootstrap goes away and the skill now requires an installed CONSTRUCT. `requirements.txt` and `debounced_hook.py` need review under the same rule — `debounced_hook.py` shells out to the generator and has its own `yaml` import.

### Views-refresh ownership (criterion 4)

- **D-10:** `curation_run.py:981`'s `views_refresh_hook` node is **wired to actually generate**, replacing `_deferred_step("views_refresh_hook")` and its stale `reason="deferred to Phase 12"`.

- **D-11:** **Phase 13's D-10 ("parent owns the single views refresh", skill-owned hook) is superseded.** The Python capability owns the refresh; the views-refresh sections are **removed** from `construct-curation-cycle/SKILL.md` (Step 5), `construct-research-cycle/SKILL.md` (:109-113), and `construct/workflows/daily-cycle.md` (§5). One owner, in the deterministic layer.

  **This reverses a recorded v0.4 decision and must be documented as such** — a note durable enough that Phase 17 (which owns the architecture doc set) does not re-derive the old rule. Whether that is an ADR, a PROJECT.md Key Decisions row, or both is the planner's call; Phase 14's D-07 chose a new ADR for a comparable reversal on discoverability grounds.

  This also resolves criterion 4 directly: the remediation string `run 'construct views generate' manually` currently names a command that does not exist. After D-03 it *does* exist — but the sections carrying that string are removed anyway.

- **D-12:** **Every workflow capability refreshes** — `curation.run`, `research.run`, and `daily.run` each end with a views refresh. Chosen as the simplest rule that needs no parent-awareness, which matters because `daily_run.py` deliberately tracks no parent/child relationship (Phase 13 D-09, no parent graph).

  **Accepted cost, recorded:** a daily cycle triggers three sweeps. The existing incremental fingerprinting (`lib/fingerprint.py`, `generate.py`'s `old_ws_fps`/`changed_ws` pass) makes the second and third largely no-ops, but `version.json` churns more than once per run and the SPA polls it.

  The refresh must remain a **side effect, not a success condition** — the existing rule that a failed refresh never flips the workflow's status carries forward into the Python implementation, along with the `views/build/` existence check and the `views.auto_regenerate: false` / `views.confirm_refresh: true` config keys the skill docs define.

### Claude's Discretion

- Whether `-w` is retained as the short flag for `--install-root` on either command (it would keep `-w "$WS"` working, but D-07 fixes those call sites anyway).
- Exact field names, types, and defaults added to `DomainRecord` / `CardRecord` / `BridgesFile` under D-02 — derive them from what the parsers actually emit, not from the prd.
- Internal layout of `src/construct/views/lib/` (flat module set vs. a `parsers/` subpackage) and whether `views/generate.py` moves alongside it.
- Where the D-11 supersession is recorded (new ADR vs. PROJECT.md Key Decisions vs. both), and its exact wording.
- Whether the three capabilities share one refresh helper or each call the generator directly.
- Fate of `debounced_hook.py` and the skill's `requirements.txt` under D-09.
- How `OperationResult.message` surfaces `GenerateReport.warnings` (content warnings) distinctly from `validation_errors` (contract failures) — D-04 makes only the latter fatal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Code this phase changes
- `src/construct/capabilities/catalog.py:149-150` — `ViewsGenerateDataInput`; becomes `install_root: Path` per D-05
- `src/construct/capabilities/catalog.py:311-318` — the capability record; **line 317 is the permanent-failure lambda criterion 1 targets**
- `src/construct/views/generate.py:43-51` — the `sys.path` injection deleted by D-08
- `src/construct/views/generate.py:175` — `generate(install_root)`, the real implementation D-01 wires
- `src/construct/views/models.py` — all 17 models use `extra="forbid"`; `DomainRecord` at :91-103, `unwrap_payload` at :292. **D-02 widens these; the strictness stays.**
- `src/construct/cli.py:860-865` — the `views_app` Typer group (hand-written, bypasses the registry — D-03 keeps it that way)
- `src/construct/cli.py:868-895` — `validate`; **:870 is the `--workspace` flag D-06 renames**, :893 is the install-root-scoped path proving D-05
- `src/construct/llm/curation_run.py:354-361` — `_deferred_step`, the stale "deferred to Phase 12" reason
- `src/construct/llm/curation_run.py:981-982, 1026, 1047-1048` — `views_refresh_hook` node and its graph edges (D-10)
- `src/construct/llm/daily_run.py` — no views work today; gains a refresh under D-12
- `src/construct/llm/research_run.py` — no views hook today; gains a refresh under D-12
- `tests/contract/test_doc_command_references.py:152-158` — `_KNOWN_BROKEN`; **`("views", "generate")` at :155 must be deleted (criterion 2)**, along with the paired still-broken assertion
- `pyproject.toml:38` — `packages = ["src/construct"]`, the reason D-08 is necessary

### Skill assets vendored / rewritten
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/lib/` — 15 modules, 1,496 lines, moved by D-08. `discover.py:16` defines install-root semantics; `fingerprint.py` is the dedupe D-12 relies on; `parse_bridges.py` (438) and `parse_digests.py` (255) are the largest
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/generate.py` — deleted by D-09
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/run.sh` — becomes a CLI call; its venv-bootstrap path is what D-09 gives up
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/debounced_hook.py`, `requirements.txt` — review under D-09

### Docs this phase edits
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md:112-132` — Step 5 Views Refresh Hook; removed by D-11
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md:109-113` — same, removed by D-11
- `CONSTRUCT-CLAUDE-impl/construct/workflows/daily-cycle.md:98-116` — §5 Views Refresh; removed by D-11
- `USER-TEST-PLAYBOOK-v03.md:333, 411` — the two `views validate -w "$WS"` calls fixed by D-07. **Phase 14 D-02 fenced this file; D-07 crosses that fence deliberately.**

### Decision precedent (read before implementing D-11)
- `.planning/PROJECT.md:92-104` Key Decisions — especially the "Python is the deterministic enforcement layer" row (still "⚠️ Revisit" after D-03) and the Phase 13 D-09 no-parent-graph row that D-12 depends on
- `.planning/phases/14-durable-state-config-truth/14-CONTEXT.md` — D-02 (edit fence D-07 crosses), D-03 (precedent for crossing it), D-07 (new-ADR-over-amendment reasoning D-11 may follow)
- Phase 13's D-10 in the archived v0.4 milestone — the "parent owns the single views refresh" decision **D-11 supersedes**. Archived milestone docs are **read-only**; record the supersession in a live document.
- `CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md:426-465, 582, 984` — the original `views.generate_data` contract, PRECONDITION_FAILED semantics, and the events.jsonl emission it specifies. **Historical spec — informative, not binding where it conflicts with D-02's parsers-are-truth rule.**

### Milestone constraints
- `.planning/REQUIREMENTS.md:21` — FIX-01, naming both ambiguities criterion 3 requires decided
- `.planning/REQUIREMENTS.md:51` — RT-01/RT-02 bounded exception, **declined by D-03**
- `.planning/REQUIREMENTS.md:57-65` — Out of Scope: no new runtime capability, no workspace-format change
- `.planning/ROADMAP.md:98-109` — Phase 15's five success criteria
- `.planning/ROADMAP.md:113-125, 128-139` — Phases 16 and 17, whose content this phase's outcome dictates (MCP tool count, skill inventory, command surface)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/fingerprint.py` + `generate.py`'s incremental pass (`old_ws_fps` / `changed_ws` / `config_fingerprint` / `articles_fingerprint`) — already makes repeat sweeps cheap. **This is the mechanism that makes D-12's three-sweeps-per-daily-cycle acceptable.**
- `GenerateReport` already separates `validation_errors` from `warnings` — the exact distinction D-04's done-bar needs. No new structure required.
- `views/models.py::unwrap_payload` (:292) already handles both the envelope and flat shapes the generator writes; D-02 does not disturb it.
- `views validate` gives a ready-made verification path: after generation, `construct views validate --install-root <root>` should report all 8 files passing.

### Established Patterns
- **The views group is the registry holdout.** `views_app` is hand-written Typer (`cli.py:860`) while 26 other capabilities dispatch through `catalog.py`. D-03 preserves this knowingly — the planner should not "helpfully" unify it.
- **`extra="forbid"` everywhere** in `views/models.py` is a deliberate contract-tightness convention. D-02 keeps it; only the field sets change.
- **Skills as thin wrappers** — PROJECT.md's stated architecture. D-09 completes it for this skill; note that several other skills (`construct-bridge-detect`, `construct-domain-init`, `construct-search-adjust`) still violate it and are explicitly deferred to v0.6 (`REQUIREMENTS.md:52`).
- **Deferred-step nodes** — `_deferred_step` is a shared helper in `curation_run.py`; check whether other nodes still use it before altering its signature for D-10.

### Integration Points
- `catalog.py` handler → `views/generate.py` → `views/lib/` (post-D-08) — the single chain the CLI and MCP both terminate in, reached via two independent paths per D-03.
- `curation_run.py` / `research_run.py` / `daily_run.py` → the refresh helper (D-12) — three new call sites into the views layer from the LLM workflow layer. Check for circular-import risk; `views/` currently imports nothing from `llm/`.
- `generate()` → `<install_root>/views/build/data/*.json` → deployed SPA. **The SPA is the reason D-02 moves the models rather than the parsers.** Its consumed field set is the real contract.
- `services/init.py` → freshly scaffolded workspace → D-04's verification target.

</code_context>

<specifics>
## Specific Ideas

- The live probe against `test-ws/` is reproducible and worth re-running as the planner's baseline: copy the tree, call `generate(Path(<copy>))`, and read `report.validation_errors`. It produced the exact mismatch list in D-01 and wrote `articles.json`, `stats.json`, `_build_meta.json`, `_generation-warnings.log`, and per-workspace directories — confirming the generator's write path works and only validation fails.
- The probe also surfaced doubled path segments in warnings (`my-construct/my-construct/cards/...`), suggesting `ws_id` is prepended to an already-relative path somewhere in the warning formatter. Cosmetic, but worth a look while in the code.

</specifics>

<deferred>
## Deferred Ideas

- **Registry unification for the views group (RT-01/RT-02)** — the bounded exception was available and declined by D-03. Stays open for v0.6, and PROJECT.md's "⚠️ Revisit" row stays accurate.
- **Thin-wrapper migration for `construct-bridge-detect`, `construct-domain-init`, `construct-search-adjust`** — D-09 does for one skill what these three still need. Already logged for v0.6 at `REQUIREMENTS.md:52`.
- **Workspace content repair** — the `missing required field(s): lifecycle` warnings across `test-ws/` workspaces. D-04 scopes them out; they are fixture-data defects, not contract defects.
- **`views.generate_data` events.jsonl emission** — `prd-v03-pipeline-mvp.md:984` specifies it appends to a nominated workspace log. Not required by any Phase 15 criterion; note it if the wiring makes it trivial, otherwise defer.
- **MCP tool count and skill inventory effects** — D-09's skill reduction and D-11's doc removals change what `artifact-catalog.md` must list. **Phase 17 (DOC-02) owns this**; do not edit the architecture doc set here.

</deferred>

---

*Phase: 15-views-generate-data-resolution*
*Context gathered: 2026-07-19*
