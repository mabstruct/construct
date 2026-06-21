# Phase 2: Governed Knowledge Operations — Research

**Researched:** 2026-06-09
**Purpose:** Answer "What do I need to know to PLAN Phase 2 well?"

---

## 1. Standard Stack & Available Abstractions

### Typer CLI Structure
The existing CLI (`src/construct/cli.py`) uses a flat `typer.Typer()` app with `@app.command()` decorators. For Phase 2, we need nested command groups:

```python
# Pattern for nested Typer groups
knowledge_app = typer.Typer()
app.add_typer(knowledge_app, name="knowledge", help="Manage knowledge artifacts")

card_app = typer.Typer()
knowledge_app.add_typer(card_app, name="card", help="Card operations")

@card_app.command()
def create(...): ...

@card_app.command()
def edit(...): ...
```

This gives us: `construct knowledge card create`, `construct knowledge connection add`, etc.

### Existing Pydantic Schemas (reuse targets)
All schemas already exist and are production-grade:
- `KnowledgeCard` (card.py) — full epistemic governance fields, field validators for kebab-case, confidence/source_tier ranges.
- `ConnectionsFile` / `ConnectionRecord` (workspace.py) — ConnectionType enum with all 9 types, dedup validation.
- `ReferenceRecord` (config.py) — full ref fields, extraction_status, domain linkage.
- `EventRecord` (config.py) — ts, agent, action, target, detail, result.

### Existing Validation Layer (reuse targets)
- `validate_card_write()` / `validate_ref_write()` / `validate_connections_write()` in `validation.py` — already provide ArtifactValidationError with structured messages.
- `parse_card_markdown()` in `card.py` — parses + validates in one pass.

### Existing Storage Layer (reuse targets)
- `WorkspaceLoader` — load/save patterns for all canonical file types.
- `iter_cards()` / `iter_refs()` — file discovery.

### Event Logging
- `log/events.jsonl` — append-only audit trail.
- `EventRecord` schema: `{"ts": "...", "agent": "curator|researcher|human|construct", "action": "create_card|edit_card|...", "target": "card-id", "detail": "...", "result": "success|failure|escalated"}`
- Event catalog already defined in data-schemas.md (Section 3.1).

---

## 2. Architecture Patterns

### Skill → Python Invocation Pattern
```
User → Skill (drives conversation)
         ↓
       Python CLI/MCP call (validate + persist)
         ↓
       Structured response (success / error + fix suggestion)
         ↓
       Skill displays result to user
```

Skills will call Python CLI commands and capture output. The CLI returns structured JSON for machine consumption and human-readable text for display.

### Workspace Path Discovery
`WorkspaceLoader(root)` resolves paths relative to workspace root. Each CLI command receives `--workspace PATH` (defaults to cwd) to locate the workspace.

### inbox/ Path Convention
Per D-09/D-10: `inbox/` at workspace root for staging. After routing → `{domain}/inbox/raw/`. The `WorkspaceScaffold` needs updating to include `inbox/` as a support path at minimum.

---

## 3. Don't Hand-Roll

| What | Why not | Use instead |
|------|---------|-------------|
| CLI argument parsing | Complex, error-prone | Typer (already installed) |
| Schema validation | Must match canonical spec | Pydantic models (already exist) |
| YAML parsing | Comment stripping | ruamel.yaml (already installed, used in loader) |
| JSON parsing | Manual error handling | json.loads in workspace loader (already exists) |
| File I/O | Path confusion | WorkspaceLoader (already exists) |
| Event logging | Format drift | Append JSON to log/events.jsonl using EventRecord schema |

---

## 4. Common Pitfalls

### Pitfall: CLI structured output mixing with human-readable output
**Mitigation:** Use `--json` flag on CLI commands. When set, output JSON only (for skill consumption). When absent, output human-readable text (for direct user invocation).

### Pitfall: Pydantic ValidationError leaking raw messages to users
**Mitigation:** Wrap all Pydantic `ValidationError` at CLI boundary. Extract field + reason + suggestion. Use existing `ArtifactValidationError` pattern. Never expose raw Pydantic tracebacks.

### Pitfall: Connection operation breaking connections.json invariants
**Mitigation:** Always read + validate + write connections.json atomically. Never patch in place. Validate file integrity before and after.

### Pitfall: Event log writes failing silently
**Mitigation:** Wrap event append in try/except. Log warning to stderr if event write fails, but do not block the primary operation.

### Pitfall: Archive deleting connections data
**Mitigation:** Per D-06, archive preserves connections. The CLI archive command must NOT delete connections.json entries. Add `?archived=include` filter to connection queries.

### Pitfall: Card edit overwriting file content without backup
**Mitigation:** Card edit should parse existing card, apply field-level changes, write back. Not string-replace. Preserve body content.

### Pitfall: Inbox not being a tracked workspace path
**Mitigation:** Add `inbox/` and `inbox/**` to `WorkspaceScaffold.support_paths` so validation doesn't flag it as unknown.

---

## 5. Key Dependencies

| Dependency | Purpose | Already installed |
|-----------|---------|-----------------|
| typer | CLI framework | ✓ (v0.24.1) |
| pydantic v2 | Schema validation | ✓ (v2.13.3) |
| ruamel.yaml | YAML parsing | ✓ (v0.19.1) |
| pathlib | File I/O | ✓ (stdlib) |
| json | Event log / connections | ✓ (stdlib) |
| datetime | Timestamps for events | ✓ (stdlib) |

No new dependencies are needed for Phase 2.

---

## 6. Connections Vocabulary (from connections.json template)

| Type | Meaning |
|------|---------|
| supports | Evidence for a claim |
| contradicts | Evidence against a claim |
| extends | Adds detail or scope |
| parallels | Similar but independent |
| requires | Depends on |
| enables | Makes possible |
| challenges | Questions or disputes |
| inspires | Source of idea |
| gap-for | Identifies a knowledge gap |

---

## 7. Test Strategy

### Unit Tests (existing patterns in tests/unit/)
- `test_artifact_write_gates.py` — write validation patterns
- `test_schema_contracts.py` — schema contract enforcement
- `test_validation_service.py` — validation service patterns

### Integration Tests (existing patterns in tests/integration/)
- `test_init_cli.py` — CLI integration with CliRunner
- CliRunner pattern: `result = cli_runner.invoke(app, ["knowledge", "card", "create", ...])`

### Phase 2 Test Coverage Needed
- `construct knowledge card create` — validates, persists, logs event
- `construct knowledge card edit` — field-level edit, body preservation
- `construct knowledge card archive` — updates lifecycle, preserves connections
- `construct knowledge connection add` — validates type, checks card existence
- `construct knowledge connection remove` — removes edge, logs event
- `construct knowledge connection list` — filters by card, supports ?archived=include
- Source file routing to `{domain}/inbox/raw/`
- Error messages include fix suggestions
- All operations log to events.jsonl

---

## Validation Architecture

### Pre-write validation (already established in Phase 1)
Each write operation validates through the existing Pydantic model:
```
User input → Pydantic model_validate → ArtifactValidationError on failure → structured error response
```

### Post-write integrity (Phase 2 additions)
After write:
1. Verify file was written (path exists, non-zero)
2. Re-read and validate
3. Append event to log/events.jsonl
4. Return success response

### Error response contract
```python
@dataclass
class OperationError:
    field: str          # e.g., "confidence" or "_general"
    reason: str         # e.g., "must be between 1 and 5"
    suggestion: str     # e.g., "Use a value between 1 and 5. Current card confidence is 7."
```

---

## File Inventory

### Files to Create
- `src/construct/services/knowledge.py` — Card CRUD, connection CRUD, source file logic
- `src/construct/services/event_log.py` — Event logging helpers
- `tests/unit/test_knowledge_operations.py` — Unit tests for knowledge operations
- `tests/integration/test_knowledge_cli.py` — Integration tests for CLI commands

### Files to Modify
- `src/construct/cli.py` — Add `knowledge` command group with card/connection subcommands
- `src/construct/schemas/workspace.py` — Add `inbox/` to `REQUIRED_PATHS` / `canonical_paths` / `support_paths`
- `CONSTRUCT-CLAUDE-impl/construct/templates/connections.json` — Ensure template matches
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md` — Wrap to call Python CLI
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-edit/SKILL.md` — Same
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-archive/SKILL.md` — Same
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md` — Same
