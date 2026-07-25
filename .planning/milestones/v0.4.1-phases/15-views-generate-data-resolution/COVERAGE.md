# API Coverage — CONSTRUCT `views.*` capability surface

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

**What surface is being decided here.** This is **not** a third-party API, SDK, or hosted
service. The detector fired on "removing the capability from the registry and the MCP surface"
(ROADMAP Phase 15 criterion 1), which refers to **CONSTRUCT's own internal capability registry**
(`src/construct/capabilities/catalog.py`) and the MCP tool surface it projects. The matrix below
therefore enumerates the `views.*` capability surface this phase decides the fate of, and records
for each whether Phase 15 wires the real implementation (`INTEGRATE`) or deliberately declines it
(`OPT-OUT`).

Criterion 1 states the fork explicitly — *"either by wiring the real `views/generate.py:175`
implementation **or** by removing the capability from the registry and the MCP surface."* This file
is the record of which side of that fork each capability lands on.

| capability | decision | reason |
|---|---|---|
| `views.generate_data` (registry record + `construct_views_generate_data` MCP tool) | INTEGRATE | D-01 — the permanent-failure lambda at `catalog.py:317` is replaced by a real call into `generate()`. The retire branch of criterion 1 was considered and rejected. |
| `construct views generate` (CLI) | INTEGRATE | D-03 — hand-written Typer command alongside `validate`, calling the generator directly. Forced into existence by deleting `("views","generate")` from `_KNOWN_BROKEN`. |
| `construct views validate` (CLI) | INTEGRATE | Already exists (`cli.py:868-895`); Phase 15 renames its path option to `--install-root` per D-06 so the group names one concept one way. |
| Post-run views refresh inside `curation.run` | INTEGRATE | D-10/D-12 — the `views_refresh_hook` node is wired to actually generate, replacing the deferred-step placeholder. |
| Post-run views refresh inside `research.run` | INTEGRATE | D-12 — a refresh node is appended to the graph before `END`. |
| Post-run views refresh inside `daily.run` | INTEGRATE | D-12 — a sequential refresh helper call inside `run_daily_run`, outside the status aggregation. |
| `views.validate` as a **registry capability / MCP tool** | OPT-OUT | D-03 declines the bounded RT-01/RT-02 exception at `REQUIREMENTS.md:51`. The views group stays a registry holdout; adding a registry record for `validate` is registry unification, deferred to v0.6. |
| `views.refresh` as a **standalone registry capability / MCP tool** | OPT-OUT | D-12 makes the refresh a side effect of the three workflow capabilities, not an independently addressable capability. Exposing it would be new runtime capability — excluded by `REQUIREMENTS.md` Out of Scope for v0.4.1. |
| `views.generate_data` → `events.jsonl` emission (`prd-v03-pipeline-mvp.md:984`) | OPT-OUT | not needed yet — no Phase 15 criterion requires it; CONTEXT.md Deferred Ideas defers it explicitly. Tracked for v0.6. |
| Debounced file-watch auto-regeneration (`debounced_hook.py` / `debounced-hook.sh`) | OPT-OUT | explicitly out of scope — D-09 deletes these with the skill's standalone runtime. Re-homing debounce behaviour in the Python layer is new capability, excluded for v0.4.1 (RESEARCH OQ-3). |
| `cards.json` full spec-§5.2 shape via `_FILE_MODEL_MAP` adapter widening | OPT-OUT | not needed yet — OQ-1 resolved to reading (a), the narrow one. Adapter reshaping is out of scope this phase; "align `cards.json` with spec-v02-data-model §5.2" is recorded as a v0.6 backlog candidate. |

## Assumption-delta checkpoint — recorded once, phase-level

The `assumption-delta` checkpoint fired `detected: true` on a **single** signal:
`kind: pluralization, term: "second"`, matching *"sequenced second because its outcome dictates
Phase 16 and 17 content"* in the ROADMAP section. That is ordinal phase sequencing, not the
introduction of a second variant of a modeled thing — a **false positive**.

The detector runs once over the phase scope, so the decision is phase-level and is recorded once,
in `15-02-PLAN.md`'s `<assumption_delta_decision>` block, as **`no-change`**. It is deliberately not
duplicated into 15-01 / 15-03 / 15-04 / 15-05: five copies of one phase-level `no-change` finding
would imply five independent determinations were made. The checkpoint is advisory and non-blocking.

## Notes for downstream phases

- **Phase 16 (FIX-03)** inherits a `_KNOWN_BROKEN` allowlist of exactly 4 entries after this phase.
- **Phase 17 (DOC-02)** owns `artifact-catalog.md`. The counts it must reconcile change here: one
  CLI command is added (`views generate`), one MCP tool moves from permanent-failure to real, and one
  skill (`construct-views-generate-data`) is reduced to a CLI wrapper. Do not edit the architecture
  doc set in Phase 15.

*Produced at plan time (2026-07-19) per the api-coverage checkpoint; validated at `verify:pre` by
`check api-coverage.verify-pre`.*
