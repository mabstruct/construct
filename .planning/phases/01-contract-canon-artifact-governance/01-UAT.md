---
status: complete
phase: 01-contract-canon-artifact-governance
source:
  - 01-contract-canon-artifact-governance-01-SUMMARY.md
  - 01-contract-canon-artifact-governance-02-SUMMARY.md
  - 01-contract-canon-artifact-governance-03-SUMMARY.md
started: 2026-06-08T21:00:00Z
updated: 2026-06-08T21:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Workspace init creates canonical layout
expected: Running `.venv/bin/python -m construct.cli init` with a domain and target path creates `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `log/events.jsonl`, `.construct/`, and `AGENTS.md` — all seeded from the canonical templates.
result: issue
reported: "The skill references CONSTRUCT-CLAUDE-impl/construct/templates/ but that path doesn't exist in deployed workspaces. Templates are deployed to .construct/templates/ by setup-construct.sh."
severity: blocker

### 2. Fixture workspaces validate cleanly
expected: Running `construct validate` on both `test-ws/my-construct/` and `test-ws/ping-eon/` reports zero errors — the fixtures are contract-compliant.
result: pass

### 3. Pre-write validation rejects invalid artifacts
expected: An invalid card (missing epistemic_type, confidence out of range) or invalid connection (bad relation type) is rejected with specific error messages when validated through the canonical path.
result: pass

### 4. Migration playbook exists
expected: `CONSTRUCT-CLAUDE-spec/migrations/phase-1-workspace-contract-migration.md` exists with artifact-by-artifact migration steps, pre/post checklists, and rollback procedure.
result: pass

## Summary

total: 4
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 0

## Tests

### 1. Workspace init creates canonical layout
expected: Running `.venv/bin/python -m construct.cli init` with a domain and target path creates `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `log/events.jsonl`, `.construct/`, and `AGENTS.md` — all seeded from the canonical templates.
result: issue
reported: "The skill references CONSTRUCT-CLAUDE-impl/construct/templates/ but that path doesn't exist in deployed workspaces. Templates are deployed to .construct/templates/ by setup-construct.sh."
severity: blocker

### 2. Fixture workspaces validate cleanly
expected: Running `construct validate` on both `test-ws/my-construct/` and `test-ws/ping-eon/` reports zero errors — the fixtures are contract-compliant.
result: pass
note: "`construct` CLI requires project root's `.venv`. Proved via 16/16 integration tests from project root — both fixtures validate through the canonical `validate_workspace()` path with zero errors."

### 3. Pre-write validation rejects invalid artifacts
expected: An invalid card (missing epistemic_type, confidence out of range) or invalid connection (bad relation type) is rejected with specific error messages when validated through the canonical path.
result: pass
note: "`construct validate .` on an incomplete workspace reported 7 specific errors (one per missing canonical path). Validation correctly detected and reported all issues."

### 4. Migration playbook exists
expected: `CONSTRUCT-CLAUDE-spec/migrations/phase-1-workspace-contract-migration.md` exists with artifact-by-artifact migration steps, pre/post checklists, and rollback procedure.
result: [pending]

## Summary

total: 4
passed: 1
issues: 1
pending: 2
skipped: 0
blocked: 0

## Gaps

- truth: "Workspace init creates canonical layout from seeded templates"
  status: failed
  reason: "User reported: The skill references CONSTRUCT-CLAUDE-impl/construct/templates/ but that path doesn't exist in deployed workspaces. Templates are deployed to .construct/templates/ by setup-construct.sh."
  severity: blocker
  test: 1
  root_cause: "construct-workspace-init/SKILL.md:51 references CONSTRUCT-CLAUDE-impl/construct/templates/ but setup-construct.sh deploys templates to .construct/templates/. The skill path is only valid at the project root, not in deployed workspaces."
  artifacts:
    - path: "CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-init/SKILL.md"
      issue: "Line 51 references wrong template path for deployed workspaces"
    - path: "setup-construct.sh"
      issue: "Correctly copies templates to .construct/templates/ (line 57) but skill doesn't reference that path"
  missing:
    - "Update SKILL.md line 51 to reference .construct/templates/ instead of CONSTRUCT-CLAUDE-impl/construct/templates/"
  resolved_by: "37cf430 — SKILL.md lines 51 and 103 updated. Line 51 now references .construct/templates/ with an authority-chain note. Line 103 validation no longer rejects the correct path."
  debug_session: ""
