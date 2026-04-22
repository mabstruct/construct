# Workflow: Daily Cycle

**Maps to:** User Journey J2 (Daily Use)
**Duration:** Ongoing — triggered by user or can be suggested
**Purpose:** Regular knowledge maintenance: research new material, curate existing graph, report status.

---

## Overview

```
research-cycle → curation-cycle → graph-status → [user interaction]
                                                        │
                                        ┌───────────────┼───────────────┐
                                        ▼               ▼               ▼
                                   card-create    gap-analysis    search-adjust
```

---

## Steps

### 1. Check In

When user starts a session, check the workspace state:
- When was the last research cycle? (`search-seeds.json` → `last_queried` timestamps)
- When was the last curation cycle? (latest `curation_cycle_complete` event in log)
- Are there pending review items? (flagged cards, suggested connections)

Present a brief summary:
> "Welcome back. Since last session:
> - Last research: {date} ({N} days ago)
> - Pending reviews: {N} flagged cards
> - Graph: {N} cards, {N} connections
>
> Shall I run a research cycle? Or would you like to review flagged items first?"

### 2. Research Cycle (if due)
**Skill:** `research-cycle`

Run if last cycle was >24h ago (or user requests).
Report what was found.

### 3. Curation Cycle
**Skill:** `curation-cycle`

Run maintenance:
- Integrity check
- Decay scan (flag stale cards)
- Orphan scan
- Promotion evaluation
- Connection typing
- Bridge detection

Report findings and actions taken.

### 4. User Interaction Phase

Based on curation findings, the user may:

| User action | Skill invoked |
|-------------|---------------|
| "Add this paper: {url}" | `card-create` |
| "Connect card A to card B" | `card-create` (connection portion) |
| "What gaps?" | `gap-analysis` |
| "Shift focus to {topic}" | `search-adjust` |
| "Status" | `graph-status` |
| "Draft something on {topic}" | `synthesis` |
| Free conversation | CONSTRUCT handles directly |

### 5. End of Session

Before the user leaves:
> "Session summary:
> - Research: {N} new refs, {N} new cards
> - Curation: {N} promotions, {N} flags resolved
> - Connections: {N} new edges
> - Actions: {list of user-initiated changes}
>
> Anything to adjust before next session?"

---

## Suggested Cadence

| Activity | Frequency | Notes |
|----------|-----------|-------|
| Research cycle | Daily or on-demand | More frequent for active domains |
| Curation cycle | Every session | Light maintenance |
| Gap analysis | Weekly | Deeper structural review |
| Bridge detection | Weekly | Cross-domain pattern check |
| Full graph status | Every 2–3 sessions | Health dashboard |
| Synthesis | When user wants output | Not routine |

---

## Handling Overnight / Gap Activity

If the user returns after multiple days:
1. Run research cycle (will pick up everything since `last_queried`)
2. Run full curation cycle (may have decay flags)
3. Present a "catch-up" summary with everything that changed
