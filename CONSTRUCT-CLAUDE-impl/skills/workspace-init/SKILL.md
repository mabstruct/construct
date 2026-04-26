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

Create a subdirectory in the CONSTRUCT root with the domain name:

```
{domain-slug}/
├── cards/                         # Knowledge cards
├── refs/                          # Reference entries
├── digests/                       # Research digests
├── publish/                       # Curated outputs
├── log/                           # Audit trail
│   └── events.jsonl               # First event: workspace.init
├── connections.json               # From .construct/templates/ — empty edge list
├── domains.yaml                   # From .construct/templates/ — pre-filled with this domain
├── governance.yaml                # From .construct/templates/ — default thresholds
├── search-seeds.json              # From .construct/templates/ — empty seed config
└── .gitignore                     # Ignore transient files
```

Use the templates from `.construct/templates/` directory for initial file content.

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

- [ ] Subdirectory `{domain-slug}/` exists with all required directories and files
- [ ] `connections.json` is valid JSON with empty connections array
- [ ] `domains.yaml` is valid YAML with the domain pre-filled
- [ ] `governance.yaml` has all required threshold fields
- [ ] `search-seeds.json` is valid JSON with empty clusters array
- [ ] `events.jsonl` has the init event
- [ ] domain-init interview completed successfully
