---
description: "Validate workspace integrity — check file formats, connection consistency, orphan refs. Use when user says 'validate workspace', 'audit', 'check integrity'."
allowed-tools: Read, Grep, Glob, MCP(connect)
---

# Skill: Workspace Validation

**Trigger:** User says "validate workspace", "audit", "check integrity", or similar.
**Agent:** CONSTRUCT or Curator
**Produces:** Validation report with findings and recommendations

---

### Prerequisites

The CONSTRUCT MCP server must be running. If not already started:

```bash
construct mcp &
```

This starts the MCP stdio server in the background. It exposes tools for workspace validation, graph status, and knowledge operations.

### Validation boundaries (Phase 1 contract)

This skill performs **post-write audit** — it checks files that have already been persisted. It does not replace **pre-write rejection**:

| Gate | When | What |
|------|------|------|
| **Pre-write rejection** | Before a canonical artifact lands on disk | Invalid payloads rejected by `construct.services.validation.validate_*_write()` helpers. |
| **Post-write audit** (this skill) | On existing workspace files | Cross-file consistency, governance compliance, graph integrity checked via MCP `construct_validate` tool. |

## Procedure

### 1. Invoke MCP validation tool

Call the `construct_validate` tool with the workspace path:

```json
{
  "tool": "construct_validate",
  "arguments": {
    "path": "<workspace_root>"
  }
}
```

The tool returns a structured validation report with errors and warnings.

### 2. Present results

Format the returned report as:

```markdown
## Workspace Validation Report — {date}

- Errors: {N}
- Warnings: {N}
- Status: {PASS | FAIL}

### Errors
{list each error with path and message}

### Warnings
{list each warning with path and message}
```

---

## Validation

- [ ] MCP `construct_validate` tool called with correct workspace path
- [ ] Tool response received and parsed
- [ ] Report distinguishes errors from warnings
- [ ] Recommendations are actionable
