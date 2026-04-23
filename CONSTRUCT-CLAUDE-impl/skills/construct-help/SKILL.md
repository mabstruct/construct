# Skill: CONSTRUCT Help — Context-Aware Next Steps

**Trigger:** User says "construct", "help", "what can I do?", "what's next?", "suggest something", or any time a session begins.
**Agent:** CONSTRUCT (orchestrator)
**Produces:** Situational suggestion + available commands list

---

## Purpose

This is the **single entry point** for CONSTRUCT. It inspects the current workspace state, identifies the most valuable next action, and presents it as a suggestion the user can accept or decline. It also lists all available commands so the user always knows what's possible.

Think of it as: **"What would a good thinking partner suggest right now?"**

---

## Procedure

### Step 1: Scan Workspace State

Inspect the filesystem to build a situational picture. Check in this exact priority order — **stop at the first match** and use it as the primary suggestion:

#### Priority 1 — No workspace exists
Check if any domain subdirectories exist (directories containing `cards/` and `connections.json`).
If none found:
> "You don't have a domain workspace yet. Want me to set one up? Just tell me a topic — like 'cosmology' or 'climate-policy' — and I'll create the full structure and interview you about what matters."
>
> **→ Say the topic name to start, or pick from the menu below.**

#### Priority 2 — Domain exists but is empty
A domain directory exists but `cards/` is empty and `refs/` is empty.
> "Your **{domain}** workspace is set up but empty — no cards or references yet. Want me to run a research cycle to seed it with initial knowledge?"
>
> **→ `research {domain}` to start, or `add card` to create one manually.**

#### Priority 3 — Domain not interviewed
`domains.yaml` exists but the domain entry has empty `content_categories` and `source_priorities`.
> "**{domain}** hasn't been fully configured — I don't know what categories or sources to focus on. Want me to run the domain interview?"
>
> **→ `init {domain}` to run the interview.**

#### Priority 4 — Cards exist but no connections
`cards/` has files but `connections.json` has zero edges.
> "You have **{N} cards** in **{domain}** but no connections between them. Want me to run a curation cycle to find relationships?"
>
> **→ `curate {domain}` to start.**

#### Priority 5 — Research is stale
`search-seeds.json` shows `last_queried` older than 7 days (or never queried) for active clusters.
> "It's been **{N} days** since the last research cycle in **{domain}**. Want me to check for new material?"
>
> **→ `research {domain}` to run a cycle.**

#### Priority 6 — Pending curation items
Event log or card metadata shows: flagged cards, cards past decay window, orphan cards.
> "There are **{N} items needing attention** in **{domain}**: {brief breakdown — e.g., '3 flagged cards, 2 orphans'}. Want me to run curation?"
>
> **→ `curate {domain}` to clean up.**

#### Priority 7 — Graph is healthy, suggest growth
Everything is in good shape. Suggest the most impactful next action based on graph state:
- If multiple domains exist but few cross-domain connections → suggest bridge detection
- If a domain has many findings but few themes → suggest synthesis
- If categories have uneven coverage → suggest gap analysis
- If everything is genuinely healthy → suggest a new domain or a writing project

> "**{domain}** is in good shape: {N} cards, {N} connections, avg confidence {N.N}. A few ideas:"
> - "Run a **gap analysis** to find weak spots"
> - "**Write something** — I can draft a briefing from what we know"
> - "Start a **new domain** to branch out"
> - "Look for **cross-domain bridges** between {domain-A} and {domain-B}"

### Step 2: Show Available Commands

After the suggestion, always show the command menu. Group by activity:

```
━━━ What you can ask me to do ━━━

Getting started
  init {domain}          Set up a new domain workspace
  init {domain} interview  Re-run the domain configuration interview

Research
  research {domain}      Run a research cycle (web search → refs → seed cards)
  search adjust          Tune search patterns and priorities

Knowledge
  add card               Create a new knowledge card
  edit card {id}         Update an existing card
  connect {a} → {b}     Create a typed connection between cards
  evaluate {id}          Assess a card for promotion or archival

Curation
  curate {domain}        Full curation cycle (validate, decay, orphan, promote, connect)
  bridges                Detect cross-domain connections

Analysis
  status                 Knowledge graph dashboard
  gaps {domain}          Find coverage gaps and weak areas
  gaps {topic}           Topic-specific gap analysis

Writing
  write {topic}          Draft a document from accumulated knowledge
  publish                List and manage published outputs

Housekeeping
  validate               Check workspace integrity
  domains                List and manage domains

Or just talk to me — I'm your thinking partner.
━━━
```

### Step 3: Handle the Response

| User says | Action |
|-----------|--------|
| Accepts the suggestion | Run the suggested skill directly |
| Picks a command from the menu | Route to that skill |
| Says something else entirely | Route via normal AGENTS.md task routing |
| Asks for more detail on a command | Explain what that skill does, then offer to run it |

---

## Multi-Domain Awareness

When multiple domain workspaces exist:

1. **Check all domains** in Step 1, not just one
2. **Lead with the domain that needs the most attention** (emptiest, stalest, most pending items)
3. **Mention other domains briefly** if they also have suggestions:

> "**cosmology** hasn't had research in 12 days — want me to check for new material?
> *(Also: climate-policy has 2 flagged cards needing review)*"

---

## Session Start Behavior

When the user opens a new conversation in the workspace with no specific task, this skill should activate automatically. The daily-cycle workflow's "Check In" (Step 1) overlaps with this — `construct-help` is the lightweight version that always works, even on first use.

---

## Design Principles

- **Always suggest, never block.** The suggestion is an offer, not a gate.
- **One primary suggestion.** Don't overwhelm — the menu is there for exploration.
- **State-aware.** The suggestion must reflect actual workspace state, not a generic prompt.
- **Graceful at any stage.** Works for empty workspaces, mature graphs, and everything between.
- **Commands are natural language.** The menu shows keywords, but the user can phrase things however they want.
