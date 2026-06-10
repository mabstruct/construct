---
description: "Show knowledge graph health dashboard — card counts, lifecycle distribution, domain coverage, connection types. Use when user says 'status', 'graph health', 'how are things?', 'dashboard'."
allowed-tools: MCP(connect), Bash(construct)
---
# Skill: Graph Status

**Trigger:** User says "status", "graph health", "how are things?", "dashboard", or similar.
**Agent:** Curator (or CONSTRUCT for interpretation)
**Produces:** Natural language health summary with structured data from CLI/MCP

---

## Prerequisites

The CONSTRUCT MCP server must be running, or the CLI must be available on `$PATH`:

```bash
construct mcp &
```

If the MCP server is not started, CLI commands fall back to `construct status --json`.

## Procedure

### Step 1: Invoke Graph Status

Run the MCP tool `construct_graph_status` with the workspace path:

```json
{
  "tool": "construct_graph_status",
  "arguments": {
    "path": "<workspace_root>"
  }
}
```

**Fallback (CLI):** If MCP is unavailable, use:

```bash
construct status --workspace . --json
```

The command returns structured JSON with:

- **cards**: total count, by lifecycle (seed/growing/mature/archived), by domain
- **connections**: total count, by type (supports/contradicts/extends/parallels/requires/enables/challenges/inspires/gap-for)
- **domains**: total count, domain names
- **quality**: stale cards, orphan cards, confidence distribution

### Step 2: Render Health Report

Present the structured data in a readable format:

```
## CONSTRUCT Knowledge Graph — Status

### Cards: {total}
| Lifecycle | Count |
|-----------|-------|
| Seed      | {N}   |
| Growing   | {N}   |
| Mature    | {N}   |
| Archived  | {N}   |

### Connections: {total}
- Average per card: {N.N}
- Most connected: "{card-title}" ({N} connections)
- Orphans: {N}

### Domains
| Domain | Cards | Avg Confidence | Category Coverage |
|--------|-------|---------------|------------------|
| {name} | {N}   | {N.N}         | {N}/{total} ({%}) |

### Quality
- Stale cards: {N}
- Orphan cards: {N}
- Confidence distribution: [1: {N}, 2: {N}, 3: {N}, 4: {N}, 5: {N}]

### Research
- Total references: {N}
- Last research cycle: {date}
- Active search clusters: {N}
```

### Step 3: Interpret (Optional)

If the user wants more than stats, add interpretation:

> **Assessment:** The graph is {young/growing/maturing}. {Domain} has strong coverage in {categories} but gaps in {categories}. {N}% of cards are still seeds — consider running a curation cycle to evaluate promotions. The orphan rate of {N}% suggests {interpretation}.

### Step 4: Suggest Actions

Based on findings:

- High orphan count → "Consider connecting orphan cards or archiving irrelevant ones"
- Many seeds → "Run `evaluate cards` to check for promotions"
- Low research activity → "Run a research cycle to bring in fresh material"
- Stale cards → "Run `curate` to flag and handle decayed cards"
- Coverage gaps → "Run `gap analysis` for a detailed gap report"

---

## Validation

- [ ] MCP `construct_graph_status` tool called with correct workspace path
- [ ] All counts are accurate against CLI/MCP output
- [ ] No double-counting (archived cards separate from totals)
- [ ] Domain names match CLI/MCP output
- [ ] Percentages are calculated correctly
- [ ] Interpretation references actual data, not guesswork
