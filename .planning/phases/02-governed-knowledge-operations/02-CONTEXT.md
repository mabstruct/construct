# Phase 2: Governed Knowledge Operations - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Make card, ref, connection, and source-file operations reliable inside the existing workspace model — skills orchestrate, Python enforces contracts.

**Requirements:** ING-02, ING-03, ING-04

</domain>

<decisions>
## Implementation Decisions

### Runtime Model (resolves D-11/D-12 from Phase 1)
- **D-01:** Python is the deterministic enforcement layer. Claude-native skills orchestrate the flow; Python CLI/MCP provides pre-write validation gates and core operation logic.
- **D-02:** Skills remain the user-facing workflow (the "what to do"). Python is the contract enforcer (the "is this valid?"). This is the middle path — resolves the runtime ambiguity without rebuilding everything.
- **D-03:** The `construct knowledge` CLI namespace (e.g. `construct knowledge card create`, `construct knowledge connection add`) is the Python surface for card and connection operations.

### Card CRUD Operations
- **D-04:** Card create, edit, and archive move to full Python CLI/MCP commands. Skills become thin wrappers that call Python. The Python layer handles: field validation, schema enforcement, file persistence, event logging.
- **D-05:** The skill still drives the conversation (prompts user for card content, suggests connections). It calls Python to validate and persist after each user action.
- **D-06:** Archive preserves connections in connections.json. Graph views and queries filter archived card connections by default but can include them on request. Connection history is never deleted on archive.

### Connection Operations
- **D-07:** Connection add, remove, list, and type operations move to Python CLI/MCP. Same pattern as cards — skill orchestrates, Python enforces.
- **D-08:** Python validates connection types against the established vocabulary, detects orphan edges, and supports batch operations.

### Source File Storage (ING-02)
- **D-09:** `inbox/` at workspace root is the staging area for incoming raw source files (PDFs, HTML, notes). An agentic routing process determines the correct target domain.
- **D-10:** After routing, raw sources land in `{domain}/inbox/raw/`. Structured metadata is written to `{domain}/refs/{id}.json`.
- **D-11:** The routing agent can create a new domain if no existing domain matches the source material.
- **D-12:** `refs/{id}.json` remains the canonical structured metadata record. The raw files in `inbox/` are supporting reference material — not source of truth.

### Error Handling
- **D-13:** When Python validation rejects an operation, it returns structured errors (field, reason, suggestion). The skill displays the error and offers the user a chance to fix. Flow is iterative until valid or the user cancels.
- **D-14:** Common fix suggestions are part of the validation response contract. The skill does not auto-apply fixes without user awareness.

### Canonical Refs Template
- **D-15:** The `ref.json` template at `CONSTRUCT-CLAUDE-impl/construct/templates/ref.json` remains the authoritative shape for reference entries. The Python ingestion layer must align to it, not the other way.

### the agent's Discretion
- Exact CLI flag design within the `construct knowledge` namespace.
- Whether `construct knowledge` uses subcommands or nested groups (e.g. `construct knowledge card` as a group with `create`/`edit`/`archive` subcommands).
- Batch operation API shape (batch size, error aggregation per item).
- The routing agent's matching heuristics for inbox → domain assignment.
- Views refresh strategy after write operations (auto-refresh or manual).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, dependency on Phase 1.
- `.planning/REQUIREMENTS.md` — ING-02, ING-03, ING-04 requirements.
- `.planning/PROJECT.md` — Product continuity, compatibility constraints.
- `.planning/STATE.md` — Current progress, Phase 1 decisions.
- `.planning/phases/01-contract-canon-artifact-governance/01-CONTEXT.md` — Prior D-01 through D-12 decisions, especially D-11/D-12 on Python runtime.

### Active contract docs
- `CONSTRUCT-CLAUDE-spec/knowledge-card-schema.md` — Canonical card contract (Python enforcement must align here).
- `CONSTRUCT-CLAUDE-spec/data-schemas.md §2.1` — `refs/{id}.json` schema.
- `CONSTRUCT-CLAUDE-spec/data-schemas.md` — Connection, governance, and domain schemas.
- `CONSTRUCT-CLAUDE-spec/validation-strategy.md` — Validation layers and write-time posture.
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — Master capability inventory, skill ownership.
- `CONSTRUCT-CLAUDE-spec/adrs/adr-0003-v03-pipeline-v04-ui.md` — Runtime layering, CLI→MCP→HTTP path.

### Active skill procedures
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-create/SKILL.md` — Current card creation procedure (will become thin wrapper).
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-edit/SKILL.md` — Current card edit procedure.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-archive/SKILL.md` — Current card archive procedure.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-connect/SKILL.md` — Current connection management procedure.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-evaluate/SKILL.md` — Card evaluation for promotion/decay.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-research-cycle/SKILL.md` — Research cycle with ref ingestion pattern.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-curation-cycle/SKILL.md` — Full maintenance pass.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-domain-init/SKILL.md` — Domain initialization procedure.

### Active implementation
- `src/construct/schemas/card.py` — Existing Pydantic KnowledgeCard model (enforcement target for Python layer).
- `src/construct/schemas/workspace.py` — ConnectionRecord, ConnectionType, WorkspaceScaffold.
- `src/construct/schemas/config.py` — DomainConfig, GovernanceConfig, ModelRoutingConfig.
- `src/construct/services/validation.py` — Existing validate_workspace() entry point.
- `src/construct/cli.py` — Existing Typer CLI (will add `knowledge` command group).
- `src/construct/storage/workspace.py` — Existing WorkspaceLoader patterns.
- `CONSTRUCT-CLAUDE-impl/construct/templates/ref.json` — Authoritative ref entry shape.
- `CONSTRUCT-CLAUDE-impl/construct/templates/card.md` — Authoritative card template.
- `CONSTRUCT-CLAUDE-impl/construct/templates/connections.json` — Authoritative connections template.

### Fixtures
- `test-ws/my-construct/` — Primary test workspace for proof and validation.
- `test-ws/ping-eon/` — Smaller fixture for lighter tests.
- `tests/` — Python test suite (pytest) for CLI and schema tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/construct/schemas/card.py` — Pydantic KnowledgeCard with full epistemic governance fields. The Python card operations CLI will use this as the validation model.
- `src/construct/schemas/workspace.py` — ConnectionRecord with ConnectionType enum, WorkspaceScaffold with canonical path definitions.
- `src/construct/services/validation.py` — `validate_workspace()` returning ValidationReport with errors and warnings. Can be extended for per-card and per-connection validation.
- `src/construct/storage/workspace.py` — WorkspaceLoader with file discovery and typed parse patterns.
- `src/construct/cli.py` — Typer CLI with existing `init` and `validate` commands. Add `knowledge` command group here.
- `CONSTRUCT-CLAUDE-impl/construct/templates/*` — Template files that define the authoritative shape for every artifact.

### Established Patterns
- Skills are markdown procedures with YAML frontmatter, numbered steps, validation checklists.
- CLI commands use Typer with Pydantic-backed validation.
- Workspace files are the only source of truth derived layers must not write back.
- Pre-write validation gates were established in Phase 1 (D-05, D-06).
- Event logging append-only to `log/events.jsonl` on every write operation.

### Integration Points
- `src/construct/cli.py` — Add `construct knowledge` Typer command group with subcommands for card and connection operations.
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-card-*/SKILL.md` — Wrapper the skill procedures to call Python CLI/MCP instead of doing inline file manipulation.
- `CONSTRUCT-CLAUDE-impl/construct/templates/` — If `inbox/` is added as a canonical path, update WorkspaceScaffold and templates.

</code_context>

<specifics>
## Specific Ideas

- `inbox/` at workspace root as a staging area, not a permanent store. Agentic routing moves sources to their domain inboxes.
- The routing agent should be able to auto-create domains when source material doesn't match existing domains.
- Error messages from Python should include fix suggestions that are human-readable, not raw Pydantic validation errors.
- The `construct knowledge` namespace keeps the CLI extensible for future operations (knowledge ref, knowledge domain, knowledge search).
- Archive preserves connection data — connections are filtered, not deleted.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-governed-knowledge-operations*
*Context gathered: 2026-06-09*
