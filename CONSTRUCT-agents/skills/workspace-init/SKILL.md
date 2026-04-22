# Skill: Workspace Initialization

**Trigger:** User says "initialize workspace", "construct init", "set up a knowledge workspace", or similar.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** Full workspace directory structure with template files

---

## Procedure

### Step 1: Choose Location

Ask the user:
> "Where should I create the CONSTRUCT workspace? Give me a directory path, or I'll use the current directory."

Default: current working directory.

### Step 2: Create Directory Structure

Create the following directories and files:

```
{workspace}/
├── cards/                         # Empty — knowledge cards go here
├── refs/                          # Empty — reference entries go here
├── digests/                       # Empty — research digests go here
├── publish/                       # Empty — curated outputs go here
├── log/                           # Audit trail
│   └── events.jsonl               # Empty file (or first event: workspace.init)
├── connections.json               # From template — empty edge list
├── domains.yaml                   # From template — empty domain config
├── governance.yaml                # From template — default thresholds
├── search-seeds.json              # From template — empty seed config
└── .gitignore                     # Ignore transient files
```

Use the templates from `templates/` directory for initial file content.

### Step 3: Write .gitignore

```
# CONSTRUCT workspace gitignore
.env
*.pyc
__pycache__/
.DS_Store
```

### Step 4: Log Initialization Event

Append to `log/events.jsonl`:
```json
{"event": "workspace.init", "timestamp": "{ISO-8601}", "workspace": "{path}"}
```

### Step 5: Prompt for Domain Init

After workspace is created, ask:
> "Workspace ready. Would you like to initialize your first knowledge domain now?"

If yes → chain to `domain-init` skill.

---

## Validation

- [ ] All directories exist
- [ ] `connections.json` is valid JSON with empty connections array
- [ ] `domains.yaml` is valid YAML with empty domains list
- [ ] `governance.yaml` has all required threshold fields
- [ ] `search-seeds.json` is valid JSON with empty clusters array
- [ ] `events.jsonl` has the init event
