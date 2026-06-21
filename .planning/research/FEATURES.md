# Feature Landscape

**Domain:** Local-first, agent-powered knowledge system
**Project:** CONSTRUCT
**Researched:** 2026-06-08
**Confidence:** HIGH for near-term scope; MEDIUM for later UI-stage differentiators

## Scope Framing

This is not a generic PKM app roadmap. CONSTRUCT already has a working Claude-native proof of concept, and the next milestone is explicitly about making that system dependable, legible, and contract-safe before expanding the product surface. That means the near-term feature bar is:

1. Preserve the existing knowledge model and workspace format.
2. Make the current agent workflows reliable and self-explanatory.
3. Improve next-step guidance so the product feels operable, not just possible.
4. Defer UI-first ambitions until the underlying workflow and artifact contracts are stable.

## Table Stakes

Features users should expect from CONSTRUCT's next phases. Missing these would make the current product direction feel unfinished or untrustworthy.

| Feature | Why Expected in CONSTRUCT | Complexity | Dependencies | Notes |
|---------|---------------------------|------------|--------------|-------|
| Reliable workspace initialization | New users must get from zero to a valid workspace fast | Low | Templates, workspace contract | Must create correct folders/files every time; broken init poisons every later workflow |
| Domain setup with guided interview | CONSTRUCT is domain-scoped knowledge work, not a blank notebook | Medium | Workspace init, domains/search config schemas | Keep the interview, but tighten outputs and defaults |
| Source ingestion from web, files, notes, and pasted URLs | Core value starts with turning source material into governed knowledge | High | Card template, refs contract, research workflow, file handling rules | Current prototype already implies this; near-term work should harden consistency over breadth |
| Consistent card creation/edit/archive flows | Knowledge cards are the canonical unit of value | Medium | Knowledge card schema, validation rules | Must enforce required metadata, not just create markdown loosely |
| Typed connection management | Without explicit graph links, CONSTRUCT collapses into a note pile | Medium | Card IDs, `connections.json`, connection type vocabulary | Table stake because graph structure is central to the product |
| Workspace validation and data-contract enforcement | Current milestone explicitly targets consistency and reliability | Medium | Templates, schemas, workflow checks | This is a table stake for v0.3 even if many PKM tools treat it as advanced |
| Research cycle with digest output | Users expect a repeatable way to discover and ingest external material | High | Search seeds, refs, cards, digests, dedupe logic | Should optimize for dependable outcomes, not maximum automation |
| Curation / maintenance cycle | A governed knowledge graph needs cleanup, promotion, and stale-card handling | High | Validation, lifecycle rules, connection checks | This is core to CONSTRUCT's promise of compounding knowledge |
| Graph status / health reporting | Users need visibility into graph growth, health, and weak spots | Medium | Accurate card/connection metadata, validation | Text-first reporting is enough now; visual polish is not required |
| Gap analysis | Users need to know what to research or strengthen next | Medium | Graph status, lifecycle/confidence metadata | Important because CONSTRUCT must make the next sensible action clear |
| Next-step guidance / help skill | The milestone explicitly calls out clearer UX and dependable guidance | Medium | Workspace state scan, workflow definitions, command map | This is one of the highest-leverage near-term features |
| Confidence and source-tier propagation in outputs | Epistemic governance is a non-negotiable product invariant | Medium | Card metadata discipline, synthesis workflow | If this is inconsistent, user trust drops sharply |
| Synthesis / drafting from accumulated knowledge | CONSTRUCT is meant to turn graph knowledge into useful outputs | High | Cards, refs, graph links, confidence propagation | Keep it grounded and cited rather than flashy |
| Session resumption from workspace state | Claude context is ephemeral; the workspace must restore continuity | Medium | Accurate files, event log, status/help flow | Critical for a system meant to compound over time |
| Documentation of workflows and expected artifacts | Near-term work explicitly includes hardening docs and guidance | Low | Specs, templates, skills, examples | In this milestone, documentation is product surface, not just support material |

## Differentiators

Features that make CONSTRUCT meaningfully distinct from generic local notes apps or chat-over-files tools.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Epistemically governed knowledge cards | Every unit of knowledge carries confidence, source tier, lifecycle, and type | Medium | Schema discipline, workflow enforcement | This is the deepest product differentiator; preserve it aggressively |
| Agent-orchestrated research → curation → synthesis loop | CONSTRUCT is a collaborator with operating procedures, not just a storage layer | High | Reliable skills/workflows, next-step guidance | The differentiator is structured collaboration, not autonomous magic |
| Cross-domain bridge detection | Finds structural parallels and graph bridges across domains | High | Multi-domain graph integrity, typed connections, reasoning procedures | Strong differentiator once the base graph is trustworthy |
| Local-first, file-native workspace as source of truth | User owns the corpus; derived views can be rebuilt | Medium | Stable file contracts, git-friendly artifacts | Important strategic differentiator versus SaaS PKM tools |
| Dynamic wiki / derived views over the same knowledge base | Lets one graph support multiple browsing and publishing modes | High | Stable schemas, derived data generation, later UI layer | Keep the path open, but do not front-load the UI implementation |
| Governed graph health as an explicit workflow | Treats maintenance as first-class, not incidental | Medium | Curation cycle, status metrics, validation | Most PKM tools do not operationalize this well |
| State-aware "what should I do next?" guidance | Reduces blank-page friction and makes the agent system operable | Medium | Event history, graph status, workflow heuristics | For this milestone, this is both a UX differentiator and a retention lever |
| Shared knowledge model across Claude-native and future UI/runtime layers | Enables a real migration path instead of a rewrite | High | Strict contracts, schema continuity, compatibility discipline | This matters more than adding more surface features now |

## Anti-Features / Explicit Deferrals

Features that should be explicitly deferred because they would distract from the current milestone, destabilize the model, or optimize the wrong layer too early.

| Anti-Feature / Deferral | Why Avoid Now | What to Do Instead |
|-------------------------|----------------|--------------------|
| Full browser-first product shell | v0.4 agent workflows must land before **v0.5** UI-primary work | Keep interfaces text-first; define contracts the future UI can rely on |
| Rich graph visualization as a milestone driver | Visual graph browsing is valuable but not the current bottleneck | Use text-based graph status and keep view-generation contracts stable |
| Replacing the current workspace format or knowledge model | Breaks continuity across prototype, v0.3, and future UI/runtime layers | Harden and document the existing model instead |
| Aggressive autonomous background agents / heartbeat scheduling | The Claude-native system is human-triggered and should stay predictable | Improve daily-cycle guidance and session-start suggestions |
| Multi-user collaboration, permissions, or cloud sync | Adds major product and architecture complexity far outside the milestone | Stay single-user, local-first, git-friendly |
| Embeddings/vector search as foundational work | Not required to validate the core governed-graph workflow | Use explicit graph structure, typed links, and bridge reasoning first |
| Broad external integrations (Slack, Telegram, etc.) | Integration breadth would hide unresolved core workflow issues | Focus on robust ingestion from files, notes, URLs, and web research |
| Full automation of ingestion without review | Risks low-quality cards and erodes trust in epistemic metadata | Keep research + curation loops explicit and inspectable |
| Performance optimization for very large graphs | Current docs position file-based operation as acceptable for modest scale | Optimize correctness, then add indexing as a complementary layer later |
| Marketplace/plugin extensibility as a near-term goal | Too early before the product's own contracts are stable | First stabilize internal skill/workflow boundaries |

## Feature Dependencies

```text
Workspace initialization
  → Domain setup
  → Source ingestion

Schema/templates/contracts
  → Card create/edit/archive
  → Connection management
  → Workspace validation
  → Session resumption

Source ingestion
  → Research cycle
  → Reference library
  → Seed card creation

Card + connection integrity
  → Graph status
  → Gap analysis
  → Curation cycle
  → Bridge detection
  → Synthesis

Graph status + event history
  → Next-step guidance

Stable file contracts
  → Dynamic wiki / local views
  → Future UI-primary product layer
```

## Recommended Scope Structure

### Phase 1 — Foundation hardening
- Workspace/file contract validation
- Template consistency
- Reliable card/ref/connection artifact generation
- Documentation of canonical artifact shapes

### Phase 2 — Workflow reliability and operability
- Harden research, curation, graph-status, and help workflows
- Improve next-step guidance and session resumption
- Clarify user-facing commands and expected outputs

### Phase 3 — Knowledge quality and graph leverage
- Stronger gap analysis
- Better bridge detection
- More dependable synthesis with confidence propagation

### Phase 4 — UI-path preparation, not full UI delivery
- Derived-data contracts for local views/wiki surfaces
- Compatibility layer planning for future UI-primary product work

## MVP Recommendation

Prioritize:
1. **Workflow/data-contract hardening** — because the milestone's main risk is unreliable behavior, not missing surface area.
2. **Help, status, and next-step guidance** — because the current Claude-native UX must become legible and self-steering.
3. **Reliable research → curation → synthesis loop** — because this is the smallest complete expression of CONSTRUCT's product value.

Defer:
- **Full UI-first graph/wiki product shell** — valuable, but only after the contracts and workflows are stable.
- **Scale/performance layers like indexing/vector retrieval** — useful later, but premature before workflow correctness is trusted.
- **Multi-user/cloud/integration expansion** — not aligned with the local-first single-user milestone.

## Sources

- `.planning/PROJECT.md` — milestone goals, constraints, and out-of-scope boundaries
- `README.md` — active product path, knowledge model, and version lineage
- `CONSTRUCT-CLAUDE-spec/product-brief.md` — product concepts, differentiators, and evolution path
- `CONSTRUCT-CLAUDE-spec/prd.md` — current capability scope, exclusions, and workspace architecture
- `CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md` — current user-facing capability map and workflows
- `CONSTRUCT-CLAUDE-spec/user-journeys.md` — expected end-to-end user flows and acceptance mapping
