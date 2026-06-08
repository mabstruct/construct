# CONSTRUCT Agent System — Development Process

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active

---

## 1. How Configuration Evolves

Unlike the Python approach where changes go through branches → PRs → CI → merge, the Claude-native approach evolves through:

### 1.1 Edit–Test–Commit Cycle

1. **Edit** a skill, agent definition, or template
2. **Test** by invoking the skill against a workspace
3. **Validate** workspace state after invocation
4. **Commit** the configuration change

### 1.2 What Gets Versioned

| Artifact | Git-tracked | How it changes |
|----------|------------|----------------|
| `CONSTRUCT-CLAUDE-impl/` | Yes | Edit config files directly |
| `CONSTRUCT-CLAUDE-spec/` | Yes | Update specs when design changes |
| Test workspaces | No (gitignored) | Created fresh for validation |

### 1.3 Change Process

**Trivial changes** (fixing a typo in a skill, adjusting a threshold):
- Edit directly, test, commit

**Behavioral changes** (new skill, modified routing, new agent role):
1. Update the relevant spec in `CONSTRUCT-CLAUDE-spec/`
2. Implement the change in `CONSTRUCT-CLAUDE-impl/`
3. Test by running affected skills against a workspace
4. Validate workspace integrity
5. Commit spec + config together

**Schema changes** (modifying card format, connection types, event types):
1. Update `knowledge-card-schema.md` and/or `data-schemas.md`
2. Update affected skills and templates
3. Update reference tables
4. Test full cold-start workflow to validate consistency
5. Commit all changes together

**Workspace contract changes** (canonical vs derived/support classification, workspace paths, ownership rules, write-gate boundaries):
1. Update `workspace-contract.md`
2. Update `artifact-catalog.md`, `data-schemas.md`, and `validation-strategy.md` if any contract boundary or ownership rule moved
3. Update affected templates in `CONSTRUCT-CLAUDE-impl/construct/templates/`
4. Update skill procedures that create, edit, or validate the changed artifact
5. Update runtime validators and write helpers so implementation matches the contract source set
6. Prove the change against the canonical fixture target and/or contract tests
7. Update migration documentation if existing workspaces need reconciliation
8. Commit the synchronized contract change together

---

## 2. Configuration Standards

### 2.1 Skill Files

- Every skill has a SKILL.md in its own directory under `skills/`
- Skills include: trigger description, agent/role, procedure steps, validation checklist
- Skills reference templates and references by relative path
- Skills are self-contained — reading only the skill + referenced files is sufficient to execute it

### 2.2 Agent Definitions

- Root identity in `AGENTS.md` — loaded into every conversation
- Role definitions in `agents/` — loaded when switching to that role
- Roles reference skills, not other roles (no circular dependencies)

### 2.3 Templates

- Templates in `templates/` are "fill in the blanks" — not executed, just patterns
- Templates include all required fields with placeholder values
- Templates include comments explaining optional fields

### 2.4 References

- Reference tables in `references/` are read-only lookup data
- Each reference file covers one concept (epistemic types, confidence, etc.)
- References include decision guidance, not just definitions

### 2.5 Workflows

- Workflows in `workflows/` chain skills in sequence
- Workflows define transition triggers between skills
- Workflows include failure recovery steps

---

## 3. Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Skill directories | kebab-case | `card-create/`, `research-cycle/` |
| Agent files | kebab-case | `curator.md`, `researcher.md` |
| Reference files | kebab-case | `epistemic-types.md`, `source-tiers.md` |
| Template files | file-extension-as-is | `card.md`, `domains.yaml`, `connections.json` |
| Workflow files | kebab-case | `cold-start.md`, `daily-cycle.md` |
| Card IDs | kebab-case, max ~60 chars | `successor-representation-spatial` |
| Domain IDs | kebab-case | `climate-adaptation-policy` |
| Search cluster IDs | `{domain}-{topic}` | `climate-adaptation-policy-core` |

---

## 4. Commit Conventions

Use conventional commits:

```
feat: add card-edit skill
fix: correct promotion rule threshold in card-evaluate
docs: update user journeys with J3 co-authorship detail
refactor: split curation-cycle step 5 into connection-maintenance sub-steps
```

---

## 5. Documentation Guidelines

- Specs in `CONSTRUCT-CLAUDE-spec/` describe WHAT and WHY
- Config in `CONSTRUCT-CLAUDE-impl/` describes HOW (procedurally)
- No duplication — specs reference config, config references specs
- Keep skills self-contained — a skill reader shouldn't need to read 3 other files to understand the procedure

## 6. Phase 1 contract-sync checklist

Use this checklist whenever a canonical artifact contract changes.

| Area | Must update | Why |
|------|-------------|-----|
| Spec contract | `workspace-contract.md`, `knowledge-card-schema.md`, `data-schemas.md`, `validation-strategy.md` | Defines WHAT is canonical and what is rejected before write |
| Ownership matrix | `artifact-catalog.md` | Records the authoritative source set and maintenance obligations |
| Templates | `CONSTRUCT-CLAUDE-impl/construct/templates/*` | Keeps scaffolded file shapes aligned to the contract |
| Skills | Relevant `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md` files | Keeps create/edit/validate procedures aligned to the contract |
| Runtime validators | `src/construct/schemas/`, `src/construct/services/`, `src/construct/storage/` | Ensures implementation follows the contract source set |
| Fixture proof | Canonical workspace fixtures and contract tests | Proves the contract works on real workspace state |
| Migration docs | Phase migration guidance | Prevents existing workspaces from being stranded |

## 7. Phase 1 contract-change rule

The authoritative order for workspace contract changes is:

1. Spec decides the contract.
2. Templates reflect the contract.
3. Skills and runtime validators implement the contract.
4. Fixture proof demonstrates the contract.
5. Migration guidance explains how older workspaces reconcile to the contract.

---

## 8. State Tracking

### CURRENT.md

```markdown
# CONSTRUCT Agent System — Current State

**Last updated:** {date}
**Last change:** {what was done}

## Configuration Status
- Phase 0 (Foundation): ✅ Complete
- Phase 1 (Knowledge Ops): 🟡 Partial — need card-edit, card-archive, card-connect
- Phase 2 (Research & Curation): ✅ Complete
- Phase 3 (Analysis & Synthesis): ✅ Complete
- Phase 4 (Workflows & Integration): 🟡 Partial — need domain-manage, workspace-validate
- Phase 5 (Polish): 🟡 Partial — need consistency review

## Next up
{what to work on next}

## Open questions
{decisions needed}
```
