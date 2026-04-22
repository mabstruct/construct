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
| `CONSTRUCT-agents/` | Yes | Edit config files directly |
| `CONSTRUCT-agent-system-spec/` | Yes | Update specs when design changes |
| Test workspaces | No (gitignored) | Created fresh for validation |

### 1.3 Change Process

**Trivial changes** (fixing a typo in a skill, adjusting a threshold):
- Edit directly, test, commit

**Behavioral changes** (new skill, modified routing, new agent role):
1. Update the relevant spec in `CONSTRUCT-agent-system-spec/`
2. Implement the change in `CONSTRUCT-agents/`
3. Test by running affected skills against a workspace
4. Validate workspace integrity
5. Commit spec + config together

**Schema changes** (modifying card format, connection types, event types):
1. Update `knowledge-card-schema.md` and/or `data-schemas.md`
2. Update affected skills and templates
3. Update reference tables
4. Test full cold-start workflow to validate consistency
5. Commit all changes together

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

- Specs in `CONSTRUCT-agent-system-spec/` describe WHAT and WHY
- Config in `CONSTRUCT-agents/` describes HOW (procedurally)
- No duplication — specs reference config, config references specs
- Keep skills self-contained — a skill reader shouldn't need to read 3 other files to understand the procedure

---

## 6. State Tracking

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
