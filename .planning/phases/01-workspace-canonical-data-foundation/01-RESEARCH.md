# Phase 01 Research — Workspace & Canonical Data Foundation

**Phase:** 01 — Workspace & Canonical Data Foundation  
**Researched:** 2026-04-22  
**Confidence:** HIGH

## Research Goal

Answer: **What does Phase 1 need in order to plan and implement a stable local workspace contract without letting derived state become canonical?**

## Recommended Implementation Shape

Phase 1 should establish the Python CLI and schema-backed workspace foundation for `construct init`, validation, and canonical file ownership. It should not attempt runtime loops, SQLite indexing, graph derivation, or UI delivery yet. The deliverable is a workspace that is fully scaffolded from day one, strongly validated, and explicit about which paths are canonical versus rebuildable.

## Locked-Decision Translation

| Decision | Planning implication |
|----------|----------------------|
| D-01 | `construct init` creates the full long-term workspace scaffold immediately, not a temporary subset. |
| D-02 | The scaffold includes canonical and derived/rebuildable directories from the first run so later phases extend the same contract. |
| D-03 | `construct init <path>` must be guided, not a raw file copier. |
| D-04 | The interview asks only for essential domain inputs; all other config is emitted as defaults. |
| D-05 | Domain data lives in per-domain folders from the first implementation. |
| D-06 | A root `domains.yaml` remains the canonical domain registry. |
| D-07 | Per-domain files hold domain-local setup details while the root registry is the indexable global overview. |
| D-08 / D-09 | Structural/schema problems are hard errors. |
| D-10 | Non-breaking quality issues surface as warnings. |

## Recommended Workspace Contract

Create this full scaffold on the first `construct init` run:

```text
{workspace}/
├── cards/
├── domains/
│   └── {domain-id}/
│       └── domain.yaml
├── domains.yaml
├── connections.json
├── governance.yaml
├── model-routing.yaml
├── refs/
├── workflows/
├── log/
│   └── events.jsonl
├── inbox/
├── digests/
├── db/
├── views/
├── publish/
│   ├── articles/
│   ├── reports/
│   ├── drafts/
│   └── exports/
├── .gitignore
└── WORKSPACE.md
```

### Domain configuration decision

Use the user decision over the earlier root-only draft layout:

- `domains.yaml` = canonical registry used for indexing/listing domains
- `domains/{domain_id}/domain.yaml` = domain-local setup details, including:
  - `id`
  - `name`
  - `description`
  - `status`
  - `scope`
  - `content_categories`
  - `source_priorities`
  - `research_seeds`
  - `created`

This keeps root registry and per-domain detail separate per D-05, D-06, and D-07.

### Canonical vs derived ownership

Treat these as canonical in Phase 1:

- `cards/`
- `domains.yaml`
- `domains/**/domain.yaml`
- `connections.json`
- `governance.yaml`
- `model-routing.yaml`
- `refs/`
- `workflows/`
- `log/events.jsonl`

Treat these as derived/rebuildable but present from day one:

- `db/`
- `views/`

Treat these as durable workspace support state, not derived truth:

- `inbox/`
- `digests/`
- `publish/`

### Git tracking rule for the scaffold

Follow the accepted repo-topology direction:

- ignore `db/` and `views/`
- keep canonical files tracked
- keep `inbox/` available as durable workspace state rather than treating it as disposable cache

## Schema/Validation Recommendations

### Standard stack for Phase 1

- **Typer** for `construct init`, `construct validate`, and `construct status`
- **Pydantic v2** for workspace, config, card, and connection models
- **ruamel.yaml** for YAML parsing/round-tripping
- **pathlib** for filesystem operations and path validation
- **pytest** for unit/integration tests around schema rules and CLI flows

### Hard-error validation rules

Fail validation when any of these occur:

- malformed YAML
- missing required fields
- invalid enum values
- invalid kebab-case IDs
- filename/card ID mismatch
- root `domains.yaml` entries pointing to missing per-domain files
- duplicate domain IDs
- duplicate connection edges (`from` + `to` + `type`)
- workspace missing required canonical files created by `construct init`

### Warning-only rules

Warn, but do not fail, for:

- card missing `## Summary`
- `connects_to` target not yet present
- mature/high-confidence heuristics that are inconsistent but not schema-breaking
- empty optional collections such as `refs/` or `publish/articles/`

### Connections authority decision

Lock the canonical rule early:

- `connections.json` is authoritative for the graph edge list
- in-card `connects_to` stays authoring convenience only
- validators must reject duplicate canonical edges instead of silently merging them

This addresses the Phase 1/2 concern in `STATE.md` before graph/UI work spreads the wrong assumption.

## Implementation Constraints

### Do not hand-roll

- Do not build a custom CLI parser; use Typer.
- Do not parse YAML with regex or ad-hoc string splitting; use ruamel.yaml.
- Do not let CLI/UI/runtime code open canonical files directly once storage services exist; route through storage/services.

### Architecture patterns to follow

- Python remains the source of truth for schemas and services.
- `construct init` writes a stable contract, then later phases extend it.
- command handlers stay thin wrappers over services.
- `WORKSPACE.md` and command output should explicitly explain canonical vs derived areas to make rebuildability auditable.

## Common Pitfalls For This Phase

1. **Half-scaffold init** — creating only today's folders breaks D-01/D-02 and forces later migration.
2. **Root-only domain config** — conflicts with D-05/D-07 and makes later domain-local growth messy.
3. **Validation as exceptions only** — user needs structured errors and warnings, not stack traces.
4. **Derived-state ambiguity** — if `db/` and `views/` are absent from the scaffold, users cannot see the intended contract.
5. **Direct file writes outside services** — invites split-brain ownership immediately.

## Out of Scope For This Phase

These may appear as empty directories or default config hooks, but they are not implemented behavior in Phase 1:

- SQLite/FTS indexing behavior
- graph derivation and metrics
- heartbeat rendering
- runtime agents and scheduling
- WebSocket/chat/UI behavior
- real research ingestion

## Validation Architecture

### Test framework

- **Framework:** pytest
- **Config source:** `pyproject.toml`
- **Quick command:** `python -m pytest tests/unit -q`
- **Full command:** `python -m pytest -q`

### Required validation layers

1. **Schema tests** for cards, configs, domain registry, per-domain files, and connections.
2. **CLI integration tests** for `construct init`, `construct validate`, and `construct status`.
3. **Workspace contract tests** proving `db/` and `views/` are scaffolded but not treated as canonical inputs.
4. **Negative fixtures** for malformed YAML, missing required fields, invalid enums, and bad filenames.

### Success checks Phase 1 must support

- `construct init <path>` creates the full scaffold with one domain configured.
- `construct validate <path>` returns exit code `1` on structural errors and `0` with warning output for soft issues.
- `construct status <path>` reports canonical-vs-derived workspace categories clearly enough for a user to inspect the contract.

---

*Research complete for planning. No additional discovery round is required because the phase uses established Python/Typer/Pydantic patterns and no new external integration beyond standard local tooling.*
