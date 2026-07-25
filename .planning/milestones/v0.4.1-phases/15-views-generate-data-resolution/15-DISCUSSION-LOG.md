# Phase 15: views.generate_data Resolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-19
**Phase:** 15-views-generate-data-resolution
**Areas discussed:** Wire vs. retire, install_root vs workspace, Skill-lib import coupling, Degraded-path messaging

---

## Wire vs. retire

### Q1 — What is views.generate_data's fate?

| Option | Description | Selected |
|--------|-------------|----------|
| Retire from registry + MCP | Delete the capability record and MCP tool; record the honest absence. Cheapest, squarely inside "fix what exists", named as an accepted branch by criterion 1 | |
| Wire it, reconcile contracts | Point the handler at `views/generate.py:175` and fix the 35+ model/parser mismatches so `generate()` returns `success=True` | ✓ |
| Wire it, report honestly | Real call that returns `success=False` with actual validation errors; schema reconciliation logged for v0.5 | |
| You decide | | |

**User's choice:** Wire it, reconcile contracts
**Notes:** Chosen despite the scout probe showing this is a contract-reconciliation job rather than a wiring job, and despite the milestone's "no new runtime capability" boundary. This is the decision that makes Phase 15 large.

### Q2 — Which side of the mismatch moves?

| Option | Description | Selected |
|--------|-------------|----------|
| Widen models to parser output | Parsers + deployed SPA are ground truth; add missing fields, keep `extra="forbid"` | ✓ |
| Relax to `extra="ignore"` | Fastest path to `success=True`; guts the schema-validation guarantee | |
| Narrow parsers to models | Treat `views/models.py` as canonical; strip extra fields in the generator | |
| You decide | | |

**User's choice:** Widen models to parser output
**Notes:** Preserves the deployed SPA and keeps the models strict. The narrow-parsers option was rejected because it changes what lands in `views/build/data/`.

### Q3 — How should the forced `construct views generate` command be added?

| Option | Description | Selected |
|--------|-------------|----------|
| Hand-write alongside validate | Match how the views group already works; no registry change; RT-01/RT-02 stays open | ✓ |
| Route views group through registry | Take the bounded RT-01/RT-02 exception; close the CLI/MCP drift PROJECT.md logged | |
| Registry for generate only | Scope the exception to exactly the forced command | |
| You decide | | |

**User's choice:** Hand-write alongside validate
**Notes:** Declines the bounded RT-01/RT-02 exception that `REQUIREMENTS.md:51` made available. Accepts that CLI and MCP reach the generator by two independent paths.

### Q4 — What is the bar for "wired"?

| Option | Description | Selected |
|--------|-------------|----------|
| `success=True`, warnings allowed | Schema is the gate; content warnings are reporting only | |
| Zero errors and zero warnings | Requires repairing workspace content this phase does not own | |
| Fresh workspace only | Prove against a newly scaffolded workspace; `test-ws/` treated as historical data | ✓ |
| You decide | | |

**User's choice:** Fresh workspace only
**Notes:** Sidesteps the `missing required field(s): lifecycle` fixture-data warnings. Verification must scaffold via `services/init.py` rather than assert against `test-ws/`.

---

## install_root vs workspace

### Q1 — Which is the recorded contract?

| Option | Description | Selected |
|--------|-------------|----------|
| Single workspace | Match the other 26 capabilities and the existing `--workspace .` strings; requires generate() to gain a single-workspace path | |
| Install root | Record views as deliberately install-root-scoped; matches generate() as written | ✓ |
| Accept either, detect | Use `_is_workspace()` to branch — the implicit resolution criterion 3 forbids | |
| You decide | | |

**User's choice:** Install root
**Notes:** Supported by three independent pieces of evidence surfaced during discussion: `discover_workspaces()` scans children only; `views validate` is already install-root-scoped in fact; and the caller docs already say "at the install root".

### Q2 — How far does the rename reach?

| Option | Description | Selected |
|--------|-------------|----------|
| Rename generate, fix docs, leave validate | Accepts an inconsistency inside one Typer group | |
| Rename both commands | `generate` and `validate` both take `--install-root` | ✓ |
| Keep `--workspace` as an alias | Preserves the exact ambiguity criterion 3 asks to eliminate | |
| You decide | | |

**User's choice:** Rename both commands
**Notes:** Makes the group internally consistent; `validate`'s flag was misnamed relative to its own behavior.

### Q3 — How to handle the USER-TEST-PLAYBOOK-v03.md fence collision?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep `-w` as the short flag | Playbook calls keep working untouched; fence holds without any edit | |
| Fix the playbook lines now | Deliberate fence crossing, following Phase 14 D-03's precedent | ✓ |
| Leave the playbook broken | Risks tripping criterion 5 | |
| You decide | | |

**User's choice:** Fix the playbook lines now
**Notes:** Crosses Phase 14 D-02's edit fence knowingly. No cross-phase dependency created — Phase 15 must not block on Phase 16.

---

## Skill-lib import coupling

### Q1 — How is the coupling resolved?

| Option | Description | Selected |
|--------|-------------|----------|
| Vendor into `src/construct/views/lib/` | Move all 15 modules into the package; delete the `sys.path` injection | ✓ |
| Vendor, leave skill copy alone | Two copies of 1,496 lines that will drift | |
| Keep `sys.path`, add honest guard | Cheapest, but leaves the capability unusable from an installed CONSTRUCT | |
| You decide | | |

**User's choice:** Vendor into `src/construct/views/lib/`
**Notes:** `pyproject.toml:38` packages only `src/construct`, so `parents[3]` resolves only inside a dev checkout — an installed CONSTRUCT raises `ImportError` at module load.

### Q2 — What happens to the skill's own copy?

| Option | Description | Selected |
|--------|-------------|----------|
| Skill becomes a CLI wrapper | Delete its `lib/` and `generate.py`; `run.sh` calls `construct views generate` | ✓ |
| Delete skill lib, import from package | Skill keeps its own orchestration but imports the package | |
| Vendor a copy, retire the skill later | Freeze the skill's copy, log retirement for Phase 17 or v0.5 | |
| You decide | | |

**User's choice:** Skill becomes a CLI wrapper
**Notes:** Fully realises PROJECT.md's thin-wrapper principle. Accepted cost: the skill's standalone per-skill-venv bootstrap in `run.sh` goes away, and it now requires an installed CONSTRUCT.

---

## Degraded-path messaging

### Q1 — What happens to `curation_run.py`'s `views_refresh_hook` node?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep node, correct the reason | Report "skill-owned per D-10" instead of the stale "deferred to Phase 12" | |
| Remove the node | Delete a permanently-skipping node that misreports the architecture | |
| Wire the node to generate | Have the capability do the refresh itself | ✓ |
| You decide | | |

**User's choice:** Wire the node to generate
**Notes:** Flagged during discussion as contradicting Phase 13's D-10 and creating a double-refresh when `daily.run` invokes curation as a child. The user confirmed the direction, which forced Q2.

### Q2 — How is D-10 resolved?

| Option | Description | Selected |
|--------|-------------|----------|
| Capability owns it, skills stop | Supersede D-10; remove the views-refresh sections from all three caller docs | ✓ |
| Node refreshes only when unparented | Move the skill docs' "skip if invoked by a parent" rule into Python | |
| Both refresh, dedupe by fingerprint | Leaves the ownership question unanswered | |
| Reconsider — keep node skipped | Revert to correcting the stale reason only | |

**User's choice:** Capability owns it, skills stop
**Notes:** An explicit reversal of a recorded v0.4 decision. Requires a durable supersession note so Phase 17 does not re-derive the old rule.

### Q3 — Which capabilities perform the refresh?

| Option | Description | Selected |
|--------|-------------|----------|
| `daily.run` only, plus `curation.run` standalone | Preserves single-sweep-per-cycle; needs a parent/child signal `daily_run.py` does not track | |
| Every workflow capability refreshes | `curation.run`, `research.run`, `daily.run` each refresh; no parent-awareness needed | ✓ |
| `daily.run` only | Leaves views stale after a direct curation run | |
| You decide | | |

**User's choice:** Every workflow capability refreshes
**Notes:** Accepts three sweeps per daily cycle, mitigated by existing incremental fingerprinting. Compatible with Phase 13 D-09's no-parent-graph design.

---

## Claude's Discretion

- Whether `-w` is retained as the short flag for `--install-root`.
- Exact field names, types, and defaults added to `DomainRecord` / `CardRecord` / `BridgesFile`.
- Internal layout of `src/construct/views/lib/`.
- Where the D-11 supersession is recorded (new ADR vs. PROJECT.md Key Decisions vs. both).
- Whether the three capabilities share one refresh helper or call the generator directly.
- Fate of `debounced_hook.py` and the skill's `requirements.txt`.
- How `OperationResult.message` distinguishes content warnings from contract failures.

## Deferred Ideas

- Registry unification for the views group (RT-01/RT-02) — exception available and declined; stays open for v0.6.
- Thin-wrapper migration for `construct-bridge-detect`, `construct-domain-init`, `construct-search-adjust` — already logged for v0.6.
- Workspace content repair (`missing required field(s): lifecycle` across `test-ws/`) — fixture-data defects, scoped out by D-04.
- `views.generate_data` events.jsonl emission per `prd-v03-pipeline-mvp.md:984` — not required by any Phase 15 criterion.
- MCP tool count and skill inventory updates to `artifact-catalog.md` — owned by Phase 17 (DOC-02).
- Doubled path segments in generator warnings (`my-construct/my-construct/cards/...`) — cosmetic formatter bug noticed during the probe.
