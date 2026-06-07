# Plan 01-02 Summary

## Outcome

Locked the Phase 1 canonical workspace, card, routing, governance, and connection contracts in one schema package, plus default templates and contract tests.

## Changes

- Added `src/construct/schemas/card.py` with canonical knowledge-card models, enums, and markdown frontmatter parsing.
- Added `src/construct/schemas/config.py` with domain registry, per-domain config, model-routing, and governance models.
- Added `src/construct/schemas/workspace.py` with the required workspace scaffold contract and authoritative `connections.json` model that rejects duplicate edges.
- Added `src/construct/schemas/__init__.py` exports for the schema package.
- Added `templates/workspace/domains.yaml`, `templates/workspace/model-routing.yaml`, and `templates/workspace/governance.yaml` as schema-validated defaults for later init work.
- Added `tests/unit/test_schema_contracts.py` covering valid card parsing, malformed YAML, invalid enums and IDs, linked domain models, duplicate connection rejection, required scaffold paths, and template round-trips.

## Verification

- `.venv/bin/python -m pytest tests/unit/test_schema_contracts.py -q`
- `.venv/bin/python -m pytest tests/unit -q`

## Notes

- The root `domains.yaml` registry now explicitly points to `domains/{domain_id}/domain.yaml`, matching the Phase 1 context and research decisions even though the older spec example showed a flatter registry shape.
- Warning-only validation behavior is deferred to the shared validation service in Plan `01-03`; this plan focused on the hard schema contracts and default templates.
