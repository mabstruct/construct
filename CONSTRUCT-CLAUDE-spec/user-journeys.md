# CONSTRUCT Agent System — Reference User Journeys

**Version:** 1.0.0
**Date:** 2026-04-23

---

## J1: Cold Start

**Persona:** Researcher interested in climate adaptation policy. Has Claude access. Runs macOS.

### Steps

1. **Configure Claude**
   - Copy `CONSTRUCT-CLAUDE-impl/` directory to Claude's configuration location
   - Point Claude at a workspace directory (e.g., `~/my-research`)

2. **Initialize workspace**
   - User: "Initialize a CONSTRUCT workspace at ~/my-research"
   - CONSTRUCT runs `workspace-init` skill
   - Creates full directory structure with template files
   - Asks: "Ready. Want to initialize your first domain?"

3. **Initialize a domain (interview)**
   - CONSTRUCT runs `domain-init` skill
   - "What is this domain about?" → "Climate adaptation policy"
   - "Key topics?" → adaptation finance, loss and damage, nature-based solutions...
   - "Key papers, authors, institutions?" → user provides seeds
   - "Which sources matter most?" → academic journals, IPCC reports
   - Result: `domains.yaml` populated, `search-seeds.json` seeded

4. **First research cycle**
   - User: "Start researching"
   - CONSTRUCT switches to Researcher role, runs `research-cycle` skill
   - Web search using seeded clusters
   - Extracts findings, scores relevance, ingests above-threshold papers
   - Creates refs and seed cards
   - Reports: "Found 12 papers, ingested 8, created 5 seed cards"

5. **Initial curation**
   - CONSTRUCT: "New cards from research — curate now?"
   - User: "Yes"
   - Switches to Curator role, runs `curation-cycle` skill
   - Validates new cards, checks connections, computes stats
   - Reports health summary

6. **First exploration**
   - User: "What gaps do you see?"
   - CONSTRUCT runs `gap-analysis` skill
   - Reports: coverage by category, depth by confidence, structural gaps
   - Suggests: research areas, cards that need connections

**Done when:** User has a workspace with 5+ cards, 1 domain configured, research cycle completed, gap analysis shows actionable insights. Elapsed time: **<15 minutes**.

---

## J2: Daily Use (Day 3–7)

**Persona:** Same researcher, third day.

### Morning

1. User starts a new conversation with CONSTRUCT
2. CONSTRUCT reads workspace state:
   > "Welcome back. Your workspace has 35 cards across 6 categories. Last research was 2 days ago. 3 cards flagged for review. Want me to run a research cycle first?"

3. User: "Yes, research first"
4. Researcher cycle runs → 8 new refs, 4 seed cards created

### Midday

5. User reads a paper, pastes URL:
   > "Add this: https://arxiv.org/abs/2406.12345"
6. CONSTRUCT fetches info via web search, creates card and ref
7. Suggests connection to existing card → user confirms

8. User: "Connect the mangrove card to the nature-based solutions card"
9. CONSTRUCT runs `card-connect`, proposes relation type "extends", user confirms

### Evening

10. User: "Give me a status"
11. CONSTRUCT runs `graph-status`:
    > "45 cards (12 seed, 25 growing, 8 mature). 38 connections. 3 orphans. Category coverage: 7/10 categories have cards."

12. User: "Shift focus toward nature-based solutions, less on finance mechanisms"
13. CONSTRUCT runs `search-adjust`, proposes weight changes, user confirms

---

## J3: Co-authorship Session (Day 14+)

**Persona:** Same researcher. 150+ cards in the graph.

### Steps

1. User: "I want to write a briefing paper on nature-based solutions for adaptation finance."
2. CONSTRUCT runs `synthesis` skill:
   - Gathers relevant cards (filtered by topic + confidence ≥ 2)
   - Assesses knowledge strength:
     > "I have 28 relevant cards. Sections on mangrove restoration are strong (confidence 3-4). Coral reef section is thin (2 cards, confidence 1-2). Want me to draft now or research the gaps first?"

3. User: "Research the gaps first"
4. CONSTRUCT runs targeted `research-cycle` for coral reef adaptation
5. Returns with new material, re-assesses
6. Produces outline → user approves → drafts full briefing
7. Draft published to `publish/drafts/nature-based-solutions-briefing.md`
8. User reviews, requests edits → iterate
9. Finalized document with inline confidence indicators and source card references

---

## Acceptance Mapping

| Journey | What it validates |
|---------|-------------------|
| J1 step 2 | `workspace-init` skill creates valid workspace from templates |
| J1 step 3 | `domain-init` skill runs adaptive interview, populates config |
| J1 step 4 | `research-cycle` skill uses web search, creates refs + cards |
| J1 step 5 | `curation-cycle` skill validates, computes stats |
| J1 step 6 | `gap-analysis` skill identifies actionable gaps |
| J2 steps 1-2 | Session resumption with workspace state |
| J2 steps 3-4 | Repeated research cycles accumulate knowledge |
| J2 steps 5-6 | URL ingestion via `card-create` |
| J2 steps 8-9 | `card-connect` skill with type proposal |
| J2 steps 10-11 | `graph-status` produces accurate dashboard |
| J2 steps 12-13 | `search-adjust` modifies patterns with confirmation |
| J3 steps 1-2 | `synthesis` skill assesses knowledge strength |
| J3 steps 3-4 | Targeted research to fill identified gaps |
| J3 steps 6-9 | Full drafting with confidence propagation + iteration |
