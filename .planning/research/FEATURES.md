# Feature Landscape

**Project:** CONSTRUCT
**Domain:** Local-first, agent-powered personal knowledge system
**Researched:** 2026-04-22
**Overall confidence:** HIGH for CONSTRUCT-specific scope, MEDIUM for broader table-stakes positioning

## Framing

For CONSTRUCT, a credible v1 is **not** “Obsidian with chat.” It needs to satisfy baseline expectations from local-first knowledge tools (private local storage, linking, browsing, search, graph visibility) **and** prove the thesis that knowledge can be actively maintained by agents instead of passively stored.

That means the v1 cut should optimize for:

1. **Reliable local knowledge ownership**
2. **Fast capture + inspectable structure**
3. **Agent-assisted research and curation that actually changes the graph**
4. **Human-governed, epistemically legible knowledge growth**

## Table Stakes

Features users will expect from any serious local-first knowledge tool. Missing these makes CONSTRUCT feel incomplete even if the agent story is strong.

| Feature | Why Expected | Complexity | Key Dependencies | Notes for CONSTRUCT |
|---------|--------------|------------|------------------|---------------------|
| Local workspace initialization | v1 must start with a usable workspace, not manual file scaffolding | Low | CLI, templates, config schemas | `construct init` is mandatory for cold start credibility |
| Markdown-backed canonical knowledge store | Local-first users expect inspectable, portable files they own | Medium | Card schema, loader, validators | Non-negotiable product trust feature |
| Friction-light capture (manual card, URL seed, quick capture) | PKM systems live or die on input friction | Medium | Card schema, chat/CLI commands, Researcher ingest path | Must support both structured entry and rough capture |
| Full-text and metadata search | Users expect retrieval by title, content, tag, domain | Medium | SQLite + FTS5, indexing pipeline | Semantic search is not required for v1; exact/FTS is |
| Card detail view with provenance | Users must inspect source, confidence, metadata, and links | Medium | Card schema, views renderer, UI panels | This is where trust is won or lost |
| Graph browsing and filtering | Linked-note users expect visual exploration of connections | Medium | NetworkX graph build, `views/graph.json`, React graph UI | Needs filters for domain, confidence, lifecycle, type |
| Domain setup and configuration | Knowledge work needs scoped domains, seeds, taxonomy, thresholds | Medium | Domain interview, `domains.yaml`, governance config | Important because CONSTRUCT is domain-based, not one undifferentiated vault |
| System status / knowledge health views | Users need to know what agents did and whether the graph is healthy | Medium | Events log, metrics, heartbeat views, dashboard UI | Includes orphan counts, stale cards, agent state |
| Conversational control surface | Agent-powered product needs natural-language steering, not only menus | Medium | Server, WebSocket/chat loop, orchestrator | Chat is table stakes for this category specifically |
| Rebuildability and inspectability | Local-first users expect indexes/views to be disposable and recoverable | Medium | Rebuild CLI, loaders, views pipeline | Important trust differentiator vs opaque AI tools |

## Differentiators

Features that make CONSTRUCT meaningfully better than a normal local knowledge app.

| Feature | Value Proposition | Complexity | Key Dependencies | Why It Differentiates CONSTRUCT |
|---------|-------------------|------------|------------------|---------------------------------|
| Epistemically governed cards | Every card carries confidence, source tier, lifecycle, and typed relations | Medium | Strong card schema, governance rules, validation | Most PKM tools store notes; CONSTRUCT stores governed knowledge |
| Agent-mediated research ingestion | Users can seed a URL/title/question and get structured knowledge cards back | High | Researcher agent, provider integrations, card formatter, curation gates | Turns collection into a system capability, not manual labor |
| Continuous research + curation loop | The graph improves between sessions via scheduled research and maintenance | High | Session runtime, heartbeat, Researcher, Curator, logging | This is the clearest proof of “active knowledge system” |
| Curator-driven graph health management | Automatic orphan detection, decay flagging, promotion/flagging, duplicate checks | Medium | Graph metrics, lifecycle rules, Curator agent | Makes knowledge maintenance proactive instead of user-administered |
| Cross-domain bridge detection (structural + metadata layers) | Surfaces non-obvious relationships across domains | High | NetworkX graph queries, domain taxonomy, typed edges, bridge heuristics | This is CONSTRUCT’s core strategic differentiator |
| Human-governed inbox/write-back workflow | UI actions become governed requests, not direct data mutation | High | Inbox queue, agent processing, response loop, audit log | Preserves trust, reviewability, and agent accountability |
| Tiered local-first model routing | Cheap/local models handle routine work; frontier models handle deep reasoning | Medium | Provider abstraction, routing config, task classification | Makes agentic workflows affordable and practical |
| Knowledge-health-aware interaction | Gap checks, stale card review, confidence distributions, contradiction surfacing | Medium | Graph metrics, curation logic, chat/UI reporting | Users manage knowledge quality, not just quantity |

## Anti-Features

Features CONSTRUCT should deliberately **not** build in v1 because they dilute the thesis, add major complexity, or create false scope pressure.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-user collaboration, auth, roles | Explodes architecture and product surface before core single-user value is proven | Stay single-user/local-first for v1 |
| Cloud sync, hosted dashboard, remote access | Undercuts local-first simplicity and introduces security/sync complexity | Keep workspace local and git-backed |
| Embedding-first semantic search | Adds infra and tuning cost before basic governed graph workflows are proven | Ship solid FTS + metadata search first |
| General-purpose note-app parity (kanban, daily notes, whiteboards, task management) | Pulls CONSTRUCT toward being a broad PKM shell instead of an agentic knowledge system | Focus on knowledge cards, graph, research, curation |
| Plugin marketplace / extensibility platform | Attractive distraction; creates API stability burden too early | Keep v1 opinionated and narrow |
| Broad import/export bridges (Obsidian, Notion, Roam) | Migration plumbing can consume the whole roadmap | Start with native CONSTRUCT workspace only |
| Publication workflow / polished output studio | Valuable later, but v1 must prove collection + curation first | Defer synthesis/publishing to later releases |
| Fully autonomous search-pattern adaptation | High trust risk; can silently drift research priorities | Keep search changes human-triggered |
| Mobile/PWA/chat integrations | Expands surfaces before core desktop/local workflow is solid | Browser UI + CLI only in v1 |

## Feature Dependencies

```text
Workspace init + config loaders → domain setup
Card schema + validators → manual card creation
Card schema + validators → URL seed / quick capture
Card schema + loaders → indexing (SQLite/FTS5)
Card schema + loaders → graph build (NetworkX)
Indexing + graph build → dashboard / status / health metrics
Graph build + views renderer → graph browser
Events log + heartbeat → activity timeline + agent status
LLM provider abstraction + orchestrator → chat control surface
Researcher ingest + card formatter → agent-mediated research ingestion
Researcher ingest + Curator rules → continuous research + curation loop
Graph metrics + Curator rules → health management / stale / orphan review
Domain taxonomy + typed edges + graph queries → cross-domain bridge detection
Inbox queue + agent governance + response loop → governed UI write-back
```

## MVP Recommendation

Prioritize this v1 feature set:

1. **Workspace + domain initialization**
2. **Markdown knowledge cards with validation and metadata**
3. **Fast capture paths: manual card, URL seed, quick capture**
4. **Full-text/metadata retrieval**
5. **Graph browse + card detail inspection**
6. **Chat/command control surface**
7. **Researcher ingestion loop**
8. **Curator health + lifecycle management**
9. **Cross-domain bridge detection (cheap layers only: structural + metadata)**

If v1 gets cut tighter, **do not** cut epistemic metadata, curation health, or governed ingestion. Those are the product thesis. Cut polish before cutting identity.

## Requirements-Scoping Guidance

### Must-have for v1 requirements

- Local workspace creation with valid defaults
- Human-readable card source of truth
- Card creation from both manual entry and lightweight seeds
- Search and retrieval without embeddings
- Graph visualization with useful filtering
- Card detail panel with provenance and epistemic metadata
- Chat/commands to steer research and inspect graph state
- Researcher agent that can ingest real sources into cards
- Curator agent that can detect stale/orphan/duplicate/ambiguous states
- Cross-domain suggestions using graph + metadata heuristics

### Should-have if scope allows

- Batch import from reading lists/bookmarks
- Richer landscape/coverage heatmaps
- Better contradiction review flows
- More nuanced inbox actions from UI

### Defer explicitly

- Semantic embeddings and vector search
- Synthesis/publishing workflows
- Collaboration/sync/cloud
- External integrations and marketplace-style extensibility

## Sources

### Primary product sources

- `.planning/PROJECT.md` — HIGH confidence
- `CONSTRUCT-spec/construct-prd.md` — HIGH confidence
- `CONSTRUCT-spec/construct-product-brief.md` — HIGH confidence
- `CONSTRUCT-spec/construct-user-journeys.md` — HIGH confidence
- `CONSTRUCT-spec/construct-development-strategy.md` — HIGH confidence

### Ecosystem sanity checks

- Obsidian homepage (`https://obsidian.md/`) — MEDIUM confidence for table-stakes expectations; confirms local files, graph, plugins, offline/private positioning
- Zotero homepage (`https://www.zotero.org/`) — MEDIUM confidence for research-tool table stakes; confirms collect/organize/annotate/cite expectations
- Logseq homepage (`https://logseq.com/`) — LOW confidence here; fetch returned minimal content, used only as a weak corroborating signal for privacy-first local knowledge positioning
