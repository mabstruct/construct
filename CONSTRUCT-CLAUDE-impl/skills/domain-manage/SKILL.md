# Skill: Domain Management

**Trigger:** User says "pause domain", "edit domain", "archive domain", "list domains", or similar.
**Agent:** CONSTRUCT
**Produces:** Updated `domains.yaml`, updated `search-seeds.json`, event log entry

---

## Procedure

### Step 1: Determine Operation

| User says | Operation |
|-----------|----------|
| "List domains" | Show all domains with status and stats |
| "Pause {domain}" | Set domain status to paused |
| "Resume {domain}" | Set domain status to active |
| "Archive {domain}" | Set domain status to archived |
| "Edit {domain}" | Modify domain properties |
| "Add category {cat} to {domain}" | Add content category |
| "Remove category {cat} from {domain}" | Remove content category |

### Step 2: For LIST — Show Domains

Read `domains.yaml` and count cards per domain:

```
Domains:

1. **{name}** ({domain-id}) — {status}
   Categories: {N} | Cards: {N} | Avg confidence: {N.N}
   Last researched: {date}

2. ...
```

### Step 3: For PAUSE — Pause Domain

1. Set domain `status: paused` in `domains.yaml`
2. Set all search clusters for this domain to `status: paused` in `search-seeds.json`
3. Log event

Paused domains:
- Are not included in research cycles
- Cards remain in the graph and are still curated
- Can be resumed at any time

### Step 4: For RESUME — Resume Domain

1. Set domain `status: active` in `domains.yaml`
2. Set search clusters back to `status: active` in `search-seeds.json`
3. Log event

### Step 5: For ARCHIVE — Archive Domain

Confirm with user first:
> "Archiving '{domain}' will:
> - Stop all research for this domain
> - Mark domain as archived (cards stay in graph but aren't actively curated)
> - Search clusters set to exhausted
>
> Cards: {N} | Connections: {N}
> Proceed?"

If confirmed:
1. Set domain `status: archived` in `domains.yaml`
2. Set all clusters to `status: exhausted` in `search-seeds.json`
3. Log event

### Step 6: For EDIT — Modify Properties

Editable properties:
- `name` — display name
- `description` — domain description
- `content_categories` — add or remove categories
- `source_priorities` — reorder or modify
- `cross_domain_links` — add or update
- Search cluster terms and weights (via `search-adjust` skill)

**Category operations:**
- **Add category:** Add to domain's `content_categories` list
- **Remove category:** Only if no cards use this category. If cards exist, warn:
  > "{N} cards use category '{cat}'. Reassign them before removing."

### Step 7: Log Event

```json
{"ts": "{ISO-8601}", "agent": "construct", "action": "domain_{operation}", "target": "{domain-id}", "detail": "{what changed}", "result": "success"}
```

---

## Validation

- [ ] `domains.yaml` is valid YAML after modification
- [ ] Domain IDs remain unique
- [ ] `search-seeds.json` is consistent with domain status
- [ ] No orphaned category references in cards
- [ ] Event logged
