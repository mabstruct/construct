# Skill: Domain Initialization

**Trigger:** User says "add a domain", "initialize domain", "new research domain", or similar. Also chained from `workspace-init`.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** Populated `domains.yaml`, `search-seeds.json` in the domain workspace subdirectory

---

## Procedure

### Step 0: Locate Domain Workspace

If chained from workspace-init → the domain workspace subdirectory is already known.
Otherwise → ask the user which workspace to configure (list existing subdirectories).

All file operations below are relative to the domain workspace subdirectory (e.g., `cosmology/`).

### Step 1: Scope Interview

Run an interview-style dialog. Ask these questions adaptively — skip any the user pre-answered:

1. **"What is this domain about?"**
   → Free text. Becomes the domain `description`.
   → Example: "Climate adaptation policy"

2. **"What are the key topics or sub-areas?"**
   → List. Becomes `content_categories`.
   → Example: adaptation finance, loss and damage, national adaptation plans, nature-based solutions

3. **"Name key papers, authors, or institutions you already know about."**
   → List. Becomes initial search seeds.
   → Don't require this — some users start cold.

4. **"Which sources matter most?"**
   → Ordered list. Becomes `source_priorities`.
   → Example: academic journals, IPCC reports, policy briefs

5. **"Any newsletters, RSS feeds, blogs, or channels to watch?"**
   → Optional list. Additional search seeds.

6. **"Does this domain overlap with any other domains?"**
   → Optional. Becomes `cross_domain_links`.
   → Only ask if workspace already has other domains.

### Step 2: Generate Domain ID

Convert the domain name to kebab-case:
- "Climate Adaptation Policy" → `climate-adaptation-policy`
- Check uniqueness against existing domains in `domains.yaml`

### Step 3: Write Domain Config

Add to `domains.yaml`:

```yaml
domains:
  {domain-id}:
    name: "{Domain Name}"
    description: "{from interview}"
    status: active
    created: {today ISO date}
    content_categories:
      - {category-1}
      - {category-2}
      # ... from interview
    source_priorities:
      - "{priority-1}"
      - "{priority-2}"
    cross_domain_links: []  # or populated from interview
```

### Step 4: Seed Search Patterns

Add clusters to `search-seeds.json`:

```json
{
  "clusters": [
    {
      "id": "{domain-id}-core",
      "domain": "{domain-id}",
      "terms": ["{key terms from interview}"],
      "weight": 0.8,
      "status": "active",
      "last_queried": null
    },
    {
      "id": "{domain-id}-authors",
      "domain": "{domain-id}",
      "terms": ["{author/institution names}"],
      "weight": 0.5,
      "status": "active",
      "last_queried": null
    }
  ]
}
```

Create 2–5 clusters based on interview depth. Core topic cluster gets highest weight.

### Step 5: Create Digests Directory

Create `digests/{domain-id}/` directory inside the domain workspace subdirectory.

### Step 6: Log & Confirm

Log to `log/events.jsonl` (inside the domain workspace subdirectory):
```json
{"event": "domain.init", "timestamp": "{ISO-8601}", "domain": "{domain-id}", "categories_count": {N}, "seed_clusters": {N}}
```

Confirm to user:
> "Domain '{name}' initialized with {N} content categories and {N} search clusters. Ready to run a research cycle? Say 'research' to start."

---

## Validation

- [ ] Domain ID is unique in `domains.yaml`
- [ ] At least 2 content categories defined
- [ ] At least 1 search cluster created
- [ ] `domains.yaml` remains valid YAML after update
- [ ] `search-seeds.json` remains valid JSON after update
