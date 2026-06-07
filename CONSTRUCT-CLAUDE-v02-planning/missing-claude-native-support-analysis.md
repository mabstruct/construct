# Missing Claude-Native Support Analysis

## Problem Statement

When a user runs `setup-construct.sh` or `refresh-construct.sh` to deploy CONSTRUCT into a workspace, the scripts copy:
- `.construct/` — agent infrastructure (skills, workflows, agents, references, templates)
- `AGENTS.md` — the root operating-mode instructions

Claude Code then opens the workspace, reads `AGENTS.md`, and understands *conceptually* that skills exist at `.construct/skills/`. However, **Claude Code cannot natively discover or invoke these skills** because they live in `.construct/skills/` rather than the Claude Code standard location `.claude/skills/`.

### What the user sees

- Claude reads `AGENTS.md` and knows skills like `card-create`, `research-cycle`, `curation-cycle` exist
- Claude can manually `read_file` the SKILL.md procedures when instructed
- But Claude **cannot** invoke them as `/card-create` slash commands
- Claude **does not** auto-load skill descriptions into its context for automatic matching
- Claude **does not** get the `allowed-tools`, `context: fork`, or other frontmatter behaviors
- No `CLAUDE.md` is deployed, so Claude doesn't get persistent session instructions natively
- No `.claude/settings.json` is deployed, so no permissions are pre-configured
- No `.claude/agents/` is deployed, so the Curator/Researcher roles aren't available as native subagents

### Root Cause

Claude Code has a well-defined configuration topology:

| Claude Code expects | CONSTRUCT deploys | Gap |
|---|---|---|
| `.claude/skills/<name>/SKILL.md` | `.construct/skills/<name>/SKILL.md` | Skills not discovered |
| `CLAUDE.md` or `.claude/CLAUDE.md` | `AGENTS.md` (not imported) | Instructions not auto-loaded |
| `.claude/agents/<name>.md` | `.construct/agents/curator.md`, `researcher.md` | Agents not registered |
| `.claude/settings.json` | Nothing | No permissions pre-configured |
| `.claude/rules/*.md` | Nothing | No path-scoped rules |

---

## Claude Code Native Mechanisms Available

### 1. Skills (`.claude/skills/<name>/SKILL.md`)
- Each skill directory with a `SKILL.md` is auto-discovered
- Supports YAML frontmatter: `description`, `allowed-tools`, `context`, `agent`, `disable-model-invocation`, `user-invocable`, `paths`, `model`, `effort`
- Claude auto-loads skill descriptions and can invoke them when relevant, or user types `/skill-name`
- Supports dynamic context injection (`!`command``)
- Supports `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}` substitutions
- Live change detection — edits take effect without restart

### 2. CLAUDE.md (project instructions)
- `CLAUDE.md` or `.claude/CLAUDE.md` at project root
- Loaded into every session automatically
- Supports `@path/to/file` imports for pulling in other files
- `CLAUDE.md` can import `AGENTS.md` via `@AGENTS.md`

### 3. Subagents (`.claude/agents/<name>.md`)
- Markdown files with YAML frontmatter defining specialized agents
- Fields: `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `skills` (preloaded), `mcpServers`, `hooks`, `memory`
- Claude auto-delegates to matching subagents based on description

### 4. Settings (`.claude/settings.json`)
- Pre-approve tools (permissions.allow)
- Set default permission mode
- Configure environment variables

### 5. Rules (`.claude/rules/*.md`)
- Path-scoped or global instructions
- Loaded conditionally based on `paths:` frontmatter

---

## Solution Options

### Option A: Symlink/Mirror — Deploy `.claude/` alongside `.construct/`

**Approach:** The setup/refresh scripts generate a `.claude/` directory that points Claude Code at the CONSTRUCT infrastructure.

**What to generate:**

1. **`.claude/CLAUDE.md`** — imports `AGENTS.md`:
   ```markdown
   @AGENTS.md
   ```

2. **`.claude/skills/`** — symlinks or copies from `.construct/skills/`:
   ```bash
   # In setup-construct.sh:
   mkdir -p "$TARGET/.claude/skills"
   for skill in "$TARGET/.construct/skills"/*/; do
     ln -s "../../.construct/skills/$(basename "$skill")" "$TARGET/.claude/skills/$(basename "$skill")"
   done
   ```

3. **`.claude/agents/curator.md`** and **`.claude/agents/researcher.md`** — reformatted with YAML frontmatter:
   ```yaml
   ---
   name: curator
   description: Graph gardener — validates, promotes, and decays cards. Runs curation cycles, connection typing, and orphan detection.
   tools: Read, Grep, Glob, Bash, Write, Edit
   skills:
     - curation-cycle
     - card-evaluate
     - graph-status
   ---
   
   [body from .construct/agents/curator.md]
   ```

4. **`.claude/settings.json`** — pre-approve common operations:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(git add *)",
         "Bash(git commit *)",
         "WebSearch",
         "Read(./.construct/**)"
       ]
     }
   }
   ```

**Pros:**
- Full native integration — slash commands, auto-delegation, preloaded skills
- Users get `/card-create`, `/research-cycle`, etc. out of the box
- Subagent delegation to Curator/Researcher happens automatically
- All Claude Code features (dynamic context injection, tool approval) work natively

**Cons:**
- Dual directory maintenance (`.construct/` as source, `.claude/` as deployment)
- CONSTRUCT skills need frontmatter added to their SKILL.md files
- Symlinks can be fragile on some platforms (Windows)

---

### Option B: CLAUDE.md Bridge — Minimal configuration, maximum compatibility

**Approach:** Deploy only a `CLAUDE.md` that imports `AGENTS.md` and instructs Claude to read skills from `.construct/skills/` manually.

**What to generate:**

1. **`CLAUDE.md`** (root):
   ```markdown
   @AGENTS.md
   
   ## Skill Loading
   
   When a task matches a skill from the Available Skills table above, read the full procedure from `.construct/skills/<skill-name>/SKILL.md` before executing.
   ```

**Pros:**
- Minimal setup, no symlinks
- Works today with zero SKILL.md format changes
- Compatible with all Claude Code surfaces

**Cons:**
- No slash command invocation (`/card-create` won't work)
- No auto-matching by description (Claude must rely on AGENTS.md routing table)
- No `allowed-tools` or `context: fork` behaviors
- Every skill invocation costs a `read_file` tool call
- No subagent delegation to Curator/Researcher

---

### Option C: Native Skills with Construct Adapter Layer

**Approach:** Reformat `.construct/skills/` SKILL.md files to include Claude Code-compatible YAML frontmatter, and deploy them directly into `.claude/skills/`. Keep `.construct/` as the source-of-truth for non-skill artifacts (templates, references, workflows).

**What changes:**

1. **Add frontmatter to each CONSTRUCT skill** (in `CONSTRUCT-CLAUDE-impl/skills/`):
   ```yaml
   ---
   description: Create a knowledge card from user input, URL, or research finding
   allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *)
   ---
   ```

2. **Deploy skills to `.claude/skills/`** (not `.construct/skills/`):
   ```bash
   mkdir -p "$TARGET/.claude/skills"
   cp -r "$IMPL_DIR/skills/"* "$TARGET/.claude/skills/"
   ```

3. **Deploy agents to `.claude/agents/`** with proper frontmatter format

4. **Deploy `CLAUDE.md`** importing AGENTS.md for operating-mode context

5. **Keep `.construct/`** for templates, references, workflows (non-Claude-Code artifacts)

**Pros:**
- Skills work 100% natively — slash commands, auto-matching, tool approval
- Single source of truth (CONSTRUCT-CLAUDE-impl/ skills already have SKILL.md)
- No symlink complexity
- Subagents work natively

**Cons:**
- Requires reformatting existing SKILL.md files (adding frontmatter)
- `.construct/` becomes a secondary location (only templates/references/workflows)
- Need to decide whether to keep `.construct/skills/` at all or retire it

---

### Option D: Hybrid — `.claude/` as native entry, `.construct/` as knowledge base

**Approach:** `.claude/` contains the Claude Code-native configuration (skills with frontmatter, agents, settings, CLAUDE.md). `.construct/` remains as a *reference library* for templates, reference tables, and workflow documentation that skills reference via relative paths.

**Layout:**
```
workspace/
├── CLAUDE.md              → @AGENTS.md
├── AGENTS.md              # Operating mode (unchanged)
├── .claude/
│   ├── CLAUDE.md          # Optional: Claude-specific additions
│   ├── settings.json      # Permissions, env vars
│   ├── skills/            # Native skills (with frontmatter)
│   │   ├── card-create/SKILL.md
│   │   ├── research-cycle/SKILL.md
│   │   └── ...
│   └── agents/            # Native subagents
│       ├── curator.md
│       └── researcher.md
├── .construct/            # Reference library (non-skill artifacts)
│   ├── templates/
│   ├── references/
│   └── workflows/
└── {domain}/              # User's knowledge workspace
```

**Pros:**
- Clean separation: `.claude/` = Claude Code integration, `.construct/` = knowledge system reference data
- All Claude Code features work natively
- Skills can reference `.construct/templates/` and `.construct/references/` via relative paths or `${CLAUDE_SKILL_DIR}`
- AGENTS.md remains unchanged as the operating-mode document
- Easiest migration path — move skills to `.claude/skills/`, keep everything else

**Cons:**
- Skills exist in two conceptual homes (source in CONSTRUCT-CLAUDE-impl, deployed to .claude/skills/)
- Users need to understand both directories

---

## Recommendation

**Option D (Hybrid)** is the strongest path forward because:

1. **Full native support** — all Claude Code features work (slash commands, auto-matching, subagent delegation, tool approval, dynamic context injection)
2. **Minimal AGENTS.md disruption** — the operating-mode document stays unchanged; `CLAUDE.md` just imports it
3. **Clean concerns** — `.claude/` is the Claude Code integration layer; `.construct/` holds knowledge-system reference data (templates, taxonomies, etc.)
4. **Incremental migration** — can add frontmatter to skills one at a time
5. **refresh-construct.sh adaptation** — straightforward: refresh both `.claude/skills/` and `.construct/{templates,references,workflows}`

### Required Changes

| Component | Change needed |
|---|---|
| Each `SKILL.md` in `CONSTRUCT-CLAUDE-impl/skills/` | Add YAML frontmatter (`description`, optionally `allowed-tools`, `context`, `disable-model-invocation`) |
| `CONSTRUCT-CLAUDE-impl/agents/curator.md` | Reformat as Claude Code subagent (YAML frontmatter + markdown body) |
| `CONSTRUCT-CLAUDE-impl/agents/researcher.md` | Same as above |
| `setup-construct.sh` | Deploy skills to `.claude/skills/`, agents to `.claude/agents/`, generate `CLAUDE.md` and `.claude/settings.json` |
| `refresh-construct.sh` | Refresh `.claude/skills/` and `.claude/agents/` alongside `.construct/` |
| `AGENTS.md` | No changes needed (imported by CLAUDE.md) |

### SKILL.md Frontmatter Migration Example

**Before** (current):
```markdown
# Skill: Create Knowledge Card

**Trigger:** User says "add a card", "capture this", ...
**Agent:** CONSTRUCT or Researcher
**Produces:** New card file in `cards/`, ...

---

## Procedure
...
```

**After** (with Claude Code frontmatter):
```markdown
---
description: Create a knowledge card from user input, URL, or research finding. Use when user says "add a card", "capture this", "note this finding", or pastes a URL/paper.
allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *)
---

# Skill: Create Knowledge Card

**Agent:** CONSTRUCT or Researcher
**Produces:** New card file in `cards/`, optional connection in `connections.json`, event log entry

---

## Procedure
...
```

### Subagent Format Example

**`.claude/agents/curator.md`:**
```markdown
---
name: curator
description: Knowledge graph gardener. Validates cards, manages promotions and decay, runs curation cycles, detects orphans, types connections. Use when user requests maintenance, cleanup, curation, or quality checks.
tools: Read, Write, Edit, Grep, Glob, Bash
skills:
  - curation-cycle
  - card-evaluate
  - graph-status
  - bridge-detect
memory: project
---

You are the CONSTRUCT Curator — the graph gardener responsible for knowledge quality.

[Rest of .construct/agents/curator.md content]
```

### Generated CLAUDE.md

```markdown
@AGENTS.md

## Workspace References

- Templates: `.construct/templates/`
- Reference tables: `.construct/references/`
- Workflow sequences: `.construct/workflows/`
```

### Generated `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(git add *)",
      "Bash(git commit *)",
      "Read(./.construct/**)",
      "WebSearch"
    ]
  }
}
```

---

## Implementation Priority

1. **Add frontmatter to all SKILL.md files** — can be done incrementally, each skill gets a `description` line at minimum
2. **Convert agent definitions** to subagent format (`.claude/agents/`)
3. **Update `setup-construct.sh`** to deploy `.claude/` directory
4. **Update `refresh-construct.sh`** to refresh `.claude/` alongside `.construct/`
5. **Generate `CLAUDE.md`** in setup script (one-liner importing AGENTS.md)
6. **Test** in a fresh workspace with Claude Code
