# Workflow: Cold Start

**Maps to:** User Journey J1 (Cold Start)
**Duration:** Single session, ~15–30 minutes
**Purpose:** Take a new user from zero to a working CONSTRUCT workspace with their first domain and initial research.

---

## Overview

```
workspace-init → domain-init → research-cycle → curation-cycle → graph-status
```

---

## Steps

### 1. Initialize Workspace
**Skill:** `workspace-init`

Create the full workspace directory structure. Produces:
- Empty `cards/`, `refs/`, `digests/`, `publish/` directories
- Template `connections.json`, `domains.yaml`, `governance.yaml`, `search-seeds.json`
- `log/events.jsonl` with init event

**Transition:** Prompt user to initialize their first domain.

### 2. Initialize First Domain
**Skill:** `domain-init`

Run the interactive domain interview:
1. What's the domain about?
2. Key topics / sub-areas?
3. Known papers, authors, institutions?
4. Most important source types?
5. Feeds or channels to watch?

Produces: populated `domains.yaml` and `search-seeds.json`.

**Transition:** Prompt user to start first research cycle.

### 3. First Research Cycle
**Skill:** `research-cycle`

Execute a focused research cycle for the new domain:
- Search using the freshly seeded clusters
- Extract and score findings
- Ingest above-threshold papers as refs
- Draft seed cards for high-relevance results

Produces: initial `refs/`, first `cards/`, first digest.

**Transition:** Automatically trigger curation.

### 4. Initial Curation
**Skill:** `curation-cycle`

Run a light curation pass:
- Validate new cards
- Skip decay/orphan scans (everything is new)
- Check for obvious connections between seed cards
- Generate initial graph stats

### 5. First Status Report
**Skill:** `graph-status`

Show the user their knowledge graph:
- Card count by type and lifecycle
- Domain coverage
- Initial connections
- Suggested next steps

### 6. Close Out

Present the user with their options:
> "Your CONSTRUCT workspace is set up with {N} cards across {M} categories in '{domain}'.
>
> What would you like to do next?
> - **Explore:** 'What gaps do you see?' — I'll analyze coverage
> - **Research more:** 'Research {topic}' — targeted search cycle
> - **Add knowledge:** Paste a URL or describe a finding
> - **Discuss:** Ask me anything about your domain — I'll draw on the graph"

---

## Failure Recovery

| Failure point | Recovery |
|--------------|----------|
| Workspace init fails | Check directory permissions, retry |
| Domain interview abandoned | Workspace exists, resume with `domain-init` later |
| Research cycle finds nothing | Broaden search terms, add more clusters, or user provides seed URLs |
| No cards created | Lower relevance thresholds in governance.yaml, or add manually |
