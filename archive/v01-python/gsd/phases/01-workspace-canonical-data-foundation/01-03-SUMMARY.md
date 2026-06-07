# Plan 01-03 Summary

## Outcome

Implemented the shared workspace loader and validation service that distinguish canonical, support, and derived paths while returning structured errors and warnings for malformed workspace data.

## Changes

- Added `src/construct/storage/workspace.py` with category-aware workspace inspection, canonical-path checks, and schema-backed loaders for root config, domains, and connections.
- Added `src/construct/services/validation.py` with a structured `ValidationReport`, explicit error and warning findings, and card-level warning rules for missing `## Summary` sections and unresolved `connects_to` targets.
- Added package markers in `src/construct/storage/__init__.py` and `src/construct/services/__init__.py`.
- Added negative fixtures `tests/fixtures/invalid/invalid-card-no-summary.md` and `tests/fixtures/invalid/domains-missing-path.yaml`.
- Added `tests/unit/test_validation_service.py` covering warning-only soft issues, hard failures for malformed config and missing canonical files, and proof that `db/` and `views/` are treated as derived rather than canonical inputs.

## Verification

- `.venv/bin/python -m pytest tests/unit/test_validation_service.py -q`
- `.venv/bin/python -m pytest tests/unit -q`

## Notes

- The validation service currently enforces only canonical-path existence as hard requirements; derived paths are classified and surfaced for later status reporting without blocking validation.
- Card warnings are intentionally separate from hard schema errors so later CLI commands can exit non-zero only for structural failures.
