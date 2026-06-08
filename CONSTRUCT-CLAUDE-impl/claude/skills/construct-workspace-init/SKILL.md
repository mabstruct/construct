---
description: "Initialize a CONSTRUCT workspace (create domain subdirectory with cards/, refs/, connections.json, domains.yaml, governance.yaml, search-seeds.json, log/events.jsonl). Use when user says 'initialize workspace', 'initialize [domain]', 'construct init', 'set up a knowledge workspace'."
allowed-tools: Read, Write, Bash(mkdir *), Bash(git add *), Bash(git commit *)
---

# Skill: Workspace Initialization

**Trigger:** User says "initialize workspace", "initialize [domain-name]", "construct init", "set up a knowledge workspace", or similar.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** A domain workspace as a subdirectory of the CONSTRUCT root

---

## Procedure

### Step 1: Determine Domain Name

If the user specified a domain name (e.g., "initialize cosmology"), use it directly.
Otherwise ask:
> "What domain should I set up? Give me a name like 'cosmology' or 'climate-policy'."

Convert to kebab-case: "Quantum Computing" → `quantum-computing`

### Step 2: Create Workspace Subdirectory

Create a subdirectory in the CONSTRUCT root with the domain name.

The canonical workspace layout per the Phase 1 contract (`CONSTRUCT-CLAUDE-spec/workspace-contract.md`):

```
{domain-slug}/
├── cards/                         # Canonical SOT — knowledge cards
├── refs/                          # Canonical SOT — reference entries
├── connections.json               # Canonical SOT — typed edge list
├── domains.yaml                   # Canonical SOT — domain taxonomy
├── governance.yaml                # Canonical SOT — promotion/decay thresholds
├── search-seeds.json              # Canonical SOT — research steering inputs
├── log/
│   └── events.jsonl               # Canonical SOT — audit trail
├── digests/                       # Derived — rebuildable workflow summaries
├── publish/                       # Derived — rebuildable curated outputs
└── .construct/
    └── model-routing.yaml         # Support — runtime provider routing guidance
```

**Artifact classes (from workspace-contract.md):**
- **Source-of-truth (SOT):** `cards/`, `refs/`, `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `log/events.jsonl`
- **Derived:** `digests/`, `publish/` — rebuildable from SOT artifacts, never treated as canonical graph inputs
- **Support:** `.construct/model-routing.yaml` — runtime guidance, not workspace knowledge state

Copy initial file contents from the active templates at `CONSTRUCT-CLAUDE-impl/construct/templates/`.

### Step 3: Pre-fill domains.yaml

Unlike a blank template, pre-fill the domain entry with the domain slug:

```yaml
domains:
  {domain-slug}:
    name: "{Domain Name}"
    description: ""
    status: active
    created: {today ISO date}
    content_categories: []
    source_priorities: []
    cross_domain_links: []
```

### Step 4: Write .gitignore

```
# CONSTRUCT workspace gitignore
.env
*.pyc
__pycache__/
.DS_Store
```

### Step 5: Log Initialization Event

Append to `{domain-slug}/log/events.jsonl`:
```json
{"event": "workspace.init", "timestamp": "{ISO-8601}", "workspace": "{domain-slug}"}
```

### Step 6: Chain to Domain Interview

Immediately chain to `domain-init` skill targeting the new workspace at `{domain-slug}/`. The domain-init interview will fill in description, categories, sources, and search seeds.

---

## Validation

- [ ] Subdirectory `{domain-slug}/` exists with all required directories and files per the canonical layout
- [ ] `cards/`, `refs/`, `domains.yaml`, `governance.yaml`, `search-seeds.json`, `connections.json`, `log/events.jsonl` are created (canonical SOT)
- [ ] `digests/` and `publish/` are created (derived)
- [ ] `.construct/model-routing.yaml` is created (support)
- [ ] `connections.json` is valid JSON with empty connections array
- [ ] `domains.yaml` is valid YAML with the domain pre-filled
- [ ] `governance.yaml` has all required threshold fields
- [ ] `search-seeds.json` is valid JSON with empty clusters array
- [ ] `log/events.jsonl` has the init event
- [ ] Templates are sourced from `CONSTRUCT-CLAUDE-impl/construct/templates/` (the active template directory, not `.construct/templates/` or an archived path)
- [ ] domain-init interview completed successfully
- [ ] No archived layout assumptions (`domains/{id}/domain.yaml`, `db/`, `workflows/`, root `model-routing.yaml`) are introduced
