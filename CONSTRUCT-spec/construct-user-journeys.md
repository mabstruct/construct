# CONSTRUCT — Reference User Journeys

**Version:** 0.1.0
**Date:** 2026-04-19

---

## J1: Cold Start (v0.1)

**Persona:** Researcher interested in climate adaptation policy. Has an Anthropic API key. Runs macOS.

### Steps

1. **Clone & install**
   ```bash
   git clone https://github.com/mabstruct/construct.git
   cd construct
   pip install -e .
   cd ui && npm install && npm run build && cd ..
   ```

2. **Initialize workspace**
   ```bash
   construct init ~/my-research
   cd ~/my-research
   ```
   This creates the full workspace from `templates/`: `cards/`, `refs/`, `domains.yaml`, `governance.yaml`, `model-routing.yaml`, `search-seeds.json`, `inbox/`, `log/`, `views/`, `publish/`.

3. **Configure LLM**
   ```bash
   echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
   ```
   Default `model-routing.yaml` routes frontier tasks to Claude, lightweight to Ollama (falls back to Claude if no Ollama).

4. **Initialize a domain (BMAD-inspired interview)**
   ```bash
   construct domain init
   ```
   CONSTRUCT launches an interview-style dialog (in terminal or via `construct serve` in browser):
   - "What is this domain about?" → "Climate adaptation policy"
   - "What are the key topics?" → user lists: adaptation finance, loss and damage, national adaptation plans, nature-based solutions...
   - "Name key papers, authors, or institutions" → user provides seed references
   - "Which sources matter most?" → academic journals, IPCC reports, policy briefs
   - "Any newsletters, RSS feeds, or channels to watch?" → user provides
   
   Output: `domains.yaml` populated, `search-seeds.json` seeded.

5. **Start the system**
   ```bash
   construct serve
   ```
   Opens browser at `http://127.0.0.1:8420`. User sees:
   - React chat interface with CONSTRUCT greeting
   - Empty knowledge graph (zero cards)
   - Agent status: Curator idle, Researcher ready
   - Domain panel showing "Climate Adaptation Policy" with configured seeds

6. **First research cycle**
   User types in chat: "Start researching."
   CONSTRUCT triggers Researcher. Within 2–5 minutes:
   - Researcher queries Semantic Scholar / arXiv with seeded terms
   - Findings ingested as seed-stage cards
   - Curator runs: validates cards, flags duplicates, proposes connections
   - `views/` updated: graph now shows 5–15 cards
   - UI live-refreshes: cards appear on the graph

7. **User explores**
   - Clicks a card → detail panel shows content, source, confidence, connections
   - Graph shows clusters forming around seeded topics
   - User types: "What gaps do you see?" → CONSTRUCT analyzes graph, reports thin areas

**Done when:** User has a workspace with 10+ cards, 1 domain configured, graph rendering in UI, chat dialog works with history. Elapsed time from clone: **<30 minutes**.

---

## J2: Daily Use (v0.1, day 3–7)

**Persona:** Same researcher, third day using CONSTRUCT.

### Morning

1. Opens `http://127.0.0.1:8420` (CONSTRUCT server was left running, or restarts with `construct serve`)
2. Sees overnight activity: Researcher ran a scheduled cycle, 8 new seed cards appeared
3. Curator flagged 2 cards for review (low confidence, ambiguous source)
4. Activity timeline shows: "Researcher: 8 cards ingested. Curator: 2 flagged, 1 promoted."

### Midday

5. User reads a paper and wants to add it:
   - Pastes URL into chat: "Add this: https://arxiv.org/abs/2406.12345"
   - Researcher fetches metadata, creates card, Curator evaluates
   - Card appears in graph within 60s
   
6. User browses graph, notices two cards should be connected:
   - Clicks "Suggest connection" in UI between card A and card B
   - Curator evaluates, proposes connection type ("extends"), user confirms
   - Graph edge appears

### Evening

7. User asks: "Give me a status of the domain."
   - CONSTRUCT reports: 45 cards, 3 clusters, 2 gaps identified, confidence distribution, 5 stale cards flagged
8. User adjusts search: "Shift focus toward nature-based solutions, less on finance mechanisms."
   - CONSTRUCT updates search pattern, confirms changes, next cycle reflects new weights

---

## J3: Co-authorship Session (v0.2 — sketched for coherence)

**Persona:** Same researcher, 3 weeks in. 200+ cards in the graph.

1. User: "I want to write a briefing paper on nature-based solutions for adaptation finance."
2. CONSTRUCT (Synthesizer): pulls relevant cards (filtered by topic + confidence ≥ 3), structures outline, produces draft with inline confidence indicators
3. User reviews draft in UI: sections color-coded by knowledge strength
4. User: "The section on mangrove restoration is thin — what do we have?"
5. CONSTRUCT: shows 3 cards, all confidence 2. "Gap identified. Want me to research this deeper?"
6. User confirms → Researcher runs targeted cycle → new cards flow in → Synthesizer refreshes section
7. Iterate until draft is solid → export as markdown / PDF

---

## Acceptance Mapping

| Journey | v0.1 acceptance criteria it validates |
|---------|--------------------------------------|
| J1 steps 1–2 | `construct init` creates valid workspace from templates |
| J1 step 4 | BMAD-inspired domain initialization interview works |
| J1 steps 5–6 | React chat interface works, agents produce cards, graph renders |
| J1 step 7 | Card detail panel, chat dialog with history, gap analysis |
| J2 steps 1–4 | Heartbeat research cycle, Curator review, activity timeline |
| J2 steps 5–6 | Chat card ingestion, UI connection suggestion, inbox pattern |
| J2 steps 7–8 | Domain status, search pattern adjustment |
| J3 | v0.2 scope — Synthesizer agent, co-authorship workflow |
