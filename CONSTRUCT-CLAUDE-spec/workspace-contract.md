# CONSTRUCT — Workspace Contract

**Version:** 1.0.0
**Date:** 2026-06-08
**Status:** Active — Phase 1 canonical workspace and artifact contract
**Authority set:** `CONSTRUCT-CLAUDE-spec/`, `CONSTRUCT-CLAUDE-impl/construct/templates/`, and [`artifact-catalog.md`](artifact-catalog.md)
**Related:** [`knowledge-card-schema.md`](knowledge-card-schema.md), [`data-schemas.md`](data-schemas.md), [`validation-strategy.md`](validation-strategy.md), [`process.md`](process.md)

---

## Purpose

This document is the Phase 1 canonical contract for the CONSTRUCT workspace shape and artifact ownership model.

It resolves drift between the active Claude-native spec/template layer and older runtime assumptions.

## Canonical workspace shape

Phase 1 adopts the active Claude-native workspace shape.

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

This is the only accepted default layout for Phase 1.

- The dormant Python-first layout is **not** a second canonical default.
- Runtime code and validators must reconcile to this contract instead of pulling the contract back toward older `domains/{id}/domain.yaml`, `db/`, `workflows/`, or other archived assumptions.
- Migration from older assumptions is allowed, but long-lived dual-layout support is not the Phase 1 default posture.

## Artifact classes

### Canonical source-of-truth artifacts

These files define the governed knowledge state. Invalid versions of these artifacts must be rejected before write.

| Path | Class | Role | Canonical authority |
|------|-------|------|---------------------|
| `cards/*.md` | source of truth | Canonical knowledge cards and governed claims | `knowledge-card-schema.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/card.md` |
| `refs/*.json` | source of truth | External source records backing cards and research state | `data-schemas.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/ref.json` |
| `connections.json` | source of truth | Typed graph edges between cards | `data-schemas.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/connections.json` |
| `domains.yaml` | source of truth | Domain taxonomy and operating scope | `data-schemas.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/domains.yaml` |
| `governance.yaml` | source of truth | Promotion, decay, quality, and research thresholds | `data-schemas.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/governance.yaml` |
| `search-seeds.json` | source of truth | Search cluster definitions and research steering inputs | `data-schemas.md` + `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json` |
| `log/events.jsonl` | source of truth audit artifact | Append-only action history for review and proof | `data-schemas.md` |

### Derived artifacts

These artifacts are generated from source-of-truth files or workflow execution. They are important, but they are not canonical graph state.

| Path | Class | Role |
|------|-------|------|
| `digests/{domain}/digest-{date}.md` | derived | Research-cycle summaries and review output |
| `publish/{slug}.md` | derived | Curated outward-facing synthesis output |

`digests/` and `publish/` must never be treated as canonical graph inputs.

### Support artifacts

These artifacts support execution, configuration, or deployment, but they do not define workspace truth.

| Path | Class | Role |
|------|-------|------|
| `.construct/` | support | Deployed agent infrastructure: skills, workflows, references, templates |
| `AGENTS.md` | support | Workspace operating rules for the Claude-native runtime |
| `.construct/templates/*` | support | Authoritative initial shapes for canonical and derived artifacts |
| `.construct/model-routing.yaml` | support | Runtime/provider routing guidance; not part of workspace knowledge state |

## Authority and drift rules

When contract sources disagree, apply this order:

1. `CONSTRUCT-CLAUDE-spec/` defines the contract intent and boundaries.
2. `CONSTRUCT-CLAUDE-impl/construct/templates/` defines the expected initial file shapes.
3. [`artifact-catalog.md`](artifact-catalog.md) records ownership, audit, and sync obligations.
4. Runtime code, validators, and skill procedures must conform to the three layers above.

Implementation behavior is not authoritative when it conflicts with this spec/template/catalog source set.

## Write-time enforcement boundary

### Reject before write

The system must reject invalid canonical artifacts before they land on disk for:

- `cards/*.md`
- `refs/*.json`
- `connections.json`
- `domains.yaml`
- `governance.yaml`
- `search-seeds.json`
- workflow-produced canonical artifact mutations

### Audit after write

Post-write validation remains required for:

- cross-file consistency
- lifecycle and governance audits
- fixture proof against canonical workspaces
- migration verification
- user-visible validation reports

## Contract-sync obligations

Any change to a canonical artifact contract must be kept in sync across:

1. `CONSTRUCT-CLAUDE-spec/` contract docs
2. `CONSTRUCT-CLAUDE-impl/construct/templates/`
3. skill procedures that create, edit, or validate the artifact
4. runtime validators and write helpers
5. fixture proof and contract tests
6. migration documentation when the change affects existing workspaces

## Migration stance

Phase 1 chooses one canonical layout plus migration.

- Existing workspaces may need migration guidance.
- Older layout assumptions may be supported only long enough to migrate safely.
- Maintaining two equally valid default contracts is explicitly out of scope.

## Proof target

The canonical proof target for Phase 1 is `test-ws/`.

Historical fixtures under `tests/fixtures/` may remain useful as supporting or regression assets, but they do not redefine the canonical workspace contract.
