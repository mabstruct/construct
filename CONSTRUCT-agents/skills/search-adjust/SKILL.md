# Skill: Adjust Search Patterns

**Trigger:** User says "shift focus to...", "less research on...", "add search cluster for...", "adjust search", or similar.
**Agent:** CONSTRUCT (requires judgment on research direction)
**Produces:** Updated `search-seeds.json`, event log entry

---

## Procedure

### Step 1: Understand Intent

Parse what the user wants:

| User says | Action |
|-----------|--------|
| "Focus more on {topic}" | Increase weight of matching clusters, or create new cluster |
| "Less on {topic}" | Decrease weight of matching clusters |
| "Pause research on {topic}" | Set cluster status to "paused" |
| "Resume research on {topic}" | Set cluster status to "active" |
| "Add {terms}" | Create new cluster with those terms |
| "Stop looking for {topic}" | Set cluster status to "exhausted" |

### Step 2: Show Current State

Present current search configuration:

```
Current Search Clusters:
| Cluster | Domain | Terms | Weight | Status | Last Queried |
|---------|--------|-------|--------|--------|-------------|
| {id}    | {dom}  | {t}   | {w}    | {s}    | {date}      |
```

### Step 3: Propose Changes

Describe the proposed changes before applying:

> "I'll make these changes to your search patterns:
> - {cluster-id}: weight {old} → {new}
> - New cluster: {id} with terms [{terms}], weight {N}
> - {cluster-id}: status active → paused
>
> Confirm?"

### Step 4: Apply Changes

Update `search-seeds.json` with confirmed changes.

For new clusters:
```json
{
  "id": "{domain}-{topic-slug}",
  "domain": "{domain-id}",
  "terms": ["{term1}", "{term2}"],
  "weight": {0.0-1.0},
  "status": "active",
  "last_queried": null
}
```

### Step 5: Log Event

```json
{"event": "update_search_pattern", "timestamp": "{ISO-8601}", "changes": [{"cluster": "{id}", "field": "weight", "old": 0.3, "new": 0.7}]}
```

### Step 6: Confirm

> "Search patterns updated. Changes take effect on the next research cycle."

---

## Validation

- [ ] `search-seeds.json` remains valid JSON
- [ ] All weights are 0.0–1.0
- [ ] New cluster IDs are unique
- [ ] Domain references exist in `domains.yaml`
