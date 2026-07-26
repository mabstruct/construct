# Feature Research

**Domain:** Browser-first shell over a local-first governed knowledge graph (guided actions, wizards, human-in-the-loop review queues, wiki + graph browsing)
**Project:** CONSTRUCT — v0.5 UI-Primary Experience (Proof of Concept)
**Researched:** 2026-07-26
**Confidence:** HIGH for CONSTRUCT-internal facts (read from `src/construct/`, `.planning/PROJECT.md`, the SPA template); MEDIUM for external UX patterns corroborated across two or more independent sources; LOW where a single web source is the only evidence. Confidence tiers obtained via `gsd-tools query classify-confidence --provider websearch [--verified]`.

---

## Scope Framing

v0.5 is not a feature expansion of the knowledge model. Every capability the browser needs already exists as one of the 28 registry capabilities. The new product surface is **the experience of reaching them without a CLI**, and the milestone is judged on a single question: *can a person navigate CONSTRUCT unaided?*

That framing changes what counts as a feature. "Render a graph" is not the feature — "know what to do when you land on the graph and it is empty" is. Accordingly this document weights **loop closure** (does the UI tell me what happened and what is next?) above **surface coverage** (are all 28 capabilities reachable?). A PoC that exposes 8 capabilities inside closed loops passes the UX verdict; one that exposes 28 as disconnected buttons fails it.

Four areas were researched, plus one cross-cutting area (shell and chat demotion) that the question did not name but that determines whether the verdict is even measurable.

### The finding that most affects the verdict

`help.suggest` (`src/construct/services/help.py:32`) is a **diagnosis engine, not an action engine**. Confidence: HIGH (read from source).

Each suggestion it emits is:

```
{ "domain": ..., "priority": "Cards exist but no connections",
  "reason": "'Cosmology' has 3 card(s) but no connections",
  "card_count": 3, "connection_count": 0 }
```

There is no verb, no capability id, no target route. `PRIORITY_MAP` (`help.py:21`) has seven labelled states and `_score_domain` (`help.py:193`) returns six scored ones — but the mapping from *state* to *what the user should click* lives nowhere in the codebase. Today an LLM improvises it in chat. In a browser with chat demoted, **something must own that mapping**, and it is the highest-leverage new artifact in the milestone. If it is skipped, the guided layer degrades to a status widget and the UX verdict is answered "no" for reasons unrelated to the UI.

Note also `help.py:210-213`: a domain with `research_stale_days >= 0` scores priority 5 with the reason "last research was N days ago" — this fires on healthy domains and is a *statement*, not a problem. Rendering it as a call-to-action would be the classic nagging failure. The action mapping must be able to say "nothing to do here."

---

## Feature Landscape

### AREA A — Guided Next-Action Layer

Rendering `help.suggest` so a person knows what to do next.

#### A. Table Stakes

| Feature | Why Expected | Complexity | Dependencies / Notes |
|---------|--------------|------------|----------------------|
| **A1. Priority → action mapping table** | A reason string is not an instruction. Every one of the 7 `PRIORITY_MAP` states must resolve to a named verb, a destination route, and a capability id. Without it the guided layer is a status readout. | **MEDIUM** | `help.suggest`. Static decision table (7 rows) is sufficient — no LLM. Owns the "healthy → no action" case so priority 5/6 render as reassurance, not a task. |
| **A2. One primary CTA per surface, derived from `top_suggestion`** | Users expect a single obvious next step, not a ranked list to triage. `help.suggest` already computes `top_suggestion` (`help.py:180`). | **LOW** | `help.suggest`. The data is already there; this is presentation. |
| **A3. CTA launches the flow directly** | A suggestion that requires the user to then find the right page is not guidance. Clicking "Add connections" must open the connection flow scoped to that domain. | **MEDIUM** | `knowledge.connection.add`, `research.run`, `workspace.init`, `ingest.source` depending on state. Needs deep-linkable routes with domain pre-selected. |
| **A4. Loop closure — guidance re-evaluates after the action** | This is what makes guidance trusted rather than ignored: the user acts, the suggestion visibly changes, and the causal link is proven. If the panel says the same thing after you did the thing, users stop reading it permanently. | **MEDIUM** | `help.suggest` re-invoked after any mutating capability. Requires cache invalidation discipline in the SPA. Corroborated externally (adaptive checklists reorder/remove based on what the user has done) — MEDIUM. |
| **A5. "Why this?" evidence disclosure** | Users who cannot see why a suggestion was made ignore or distrust it. `help.suggest` already carries the evidence (`card_count: 3, connection_count: 0`) — show the counts that triggered the rule. | **LOW** | `help.suggest`. Data already in payload. Externally corroborated across explainable-AI UX sources (LinkedIn "why you're seeing this", Slack AI traceability) — MEDIUM. |
| **A6. Empty/first-run state that is itself the guidance** | `help.py:218` already returns `{"status": "no_workspace", "suggestion": "init"}`. A blank landing page with no workspace is the single most likely place an unaided user gives up. | **LOW** | `help.suggest`, `workspace.init`. `EmptyState.jsx` exists in the SPA template. |
| **A7. Dismiss / snooze a suggestion** | Guidance must be skippable or it becomes an obstacle. Non-dismissible guidance is the most reliably-cited onboarding failure. | **LOW** | Client-side only (localStorage). Deliberately not workspace state — dismissal is a UI preference, not knowledge. |
| **A8. Per-domain guidance, not just global** | `help.suggest` already scores every domain and sorts them (`help.py:126-132`). A multi-domain workspace where guidance only speaks about the worst domain hides the others. | **LOW** | `help.suggest`. Render the sorted `suggestions[]` array on the workspace dashboard, `top_suggestion` in the shell. |

#### A. Differentiators

| Feature | Value Proposition | Complexity | Dependencies / Notes |
|---------|-------------------|------------|----------------------|
| **A9. Deterministic, auditable guidance** | `help.suggest` is pure Python over workspace state — the same state always yields the same suggestion. Competing tools drive onboarding from LLMs or engagement heuristics and cannot promise that. Say so in the UI: "derived from your graph, not generated." | **LOW** | `help.suggest`. Positioning plus one line of copy; the property is already true. This is CONSTRUCT's strongest trust asset in the guided layer and it currently costs nothing to claim. |
| **A10. Guidance surfaced at the point of failure, not only on a dashboard** | An empty graph page that says "no connections yet — here's how" beats a dashboard tile the user never scrolled to. | **MEDIUM** | `help.suggest` + per-page empty states. Requires each page to know which priority state maps to it. |
| **A11. Health trend / "since last visit"** | Turns guidance from a nag into a progress narrative: "you added 4 cards and 6 connections." | **MEDIUM** | `graph.status`, `workflow.status`. Needs a stored prior snapshot — new derived state. Defer past PoC unless cheap. |

#### A. Anti-Features

| Feature | Why Requested | Why Problematic *for CONSTRUCT* | Alternative |
|---------|---------------|--------------------------------|-------------|
| **Modal/interstitial "what's next" on every load** | Guarantees the guidance is seen; standard SaaS onboarding pattern | Single-user local tool opened repeatedly per day. A blocking modal on every launch converts guidance into a dismissal reflex within a week, and the PoC's whole thesis is that guidance is trustworthy | Persistent, non-blocking panel in the shell; modal only for the genuine `no_workspace` first run |
| **"Ask the assistant what to do next" as the guidance entry point** | Cheap to build — chat already renders `help.suggest` today | Directly reinstates chat as the primary interface, which the milestone explicitly demotes. It also makes the verdict unmeasurable: if the guided layer's escape hatch is chat, the experiment tests chat | Structured action mapping (A1). Chat stays an LLM-gated modal for `ask.domain` only |
| **Completion percentage / gamified progress toward a "healthy" graph** | Makes `PRIORITY_MAP`'s 7 levels look like a natural progress metric | A knowledge graph has no finish line. A bar that never reaches 100% reads as permanent failure; one that does reach 100% makes the user stop. It also invites optimizing the metric (adding junk connections) over the knowledge | Named state + reason ("3 cards, no connections"), which is legible and non-scoring |
| **Notification badges / unread counts on nav items** | Familiar; draws attention to pending review queues | Local-first, single-user, no external actors generating events. Badges here mark *the user's own* deferred work back at them — nagging without an author | Inline count on the review surface itself ("2 items awaiting your review"), visible only where relevant |
| **LLM-rewritten suggestion prose** | The raw reason strings are terse | Destroys A9 (determinism), adds latency and an API dependency to the app's most load-bearing surface, and makes guidance non-reproducible across runs — the exact defect v0.4 spent a milestone removing from workflows | Hand-written copy per `PRIORITY_MAP` state (7 strings, written once) |
| **Auto-executing the suggested action** | "Just do it for me" | Every suggestion maps to a canonical write. Auto-execution without review contradicts the propose-before-write posture that `research.run` / `curation.run` enforce | CTA that opens the flow with fields pre-filled; the human still commits |

---

### AREA B — Wizard Flows

Two flows in scope: **B-init** (workspace creation + domain/taxonomy setup) and **B-ingest** (upload → extract → route → review-and-confirm). Sources agree on a stable table-stakes set for multi-step wizards — progress with recognizable step names, non-destructive back, revert-on-cancel, save-and-resume, per-step validation — corroborated across PatternFly design guidelines and multiple independent UX write-ups (MEDIUM).

#### B. Table Stakes

| Feature | Why Expected | Complexity | Dependencies / Notes |
|---------|--------------|------------|----------------------|
| **B1. Step indicator with human step names** | Users need to know where they are and how much remains. Names must be domain words ("Name your domain", "Choose content categories"), never internal labels. | **LOW** | None. Pure UI. |
| **B2. Back that preserves entered data** | Blocking backward movement, or losing input on back, is the most-cited wizard failure. | **LOW** | Client-side wizard state. Trivial if state is held in one object. |
| **B3. Single commit point — nothing written until Confirm** | **The local-first constraint.** Cancel must leave the filesystem exactly as it was. If the wizard calls `workspace.init` at step 1 and the user abandons at step 3, the user is left with a half-configured workspace that `workspace.validate` may reject and that `help.suggest` will then nag about forever. | **MEDIUM** | `workspace.init`, `ingest.source`. Requires staging the full payload client-side and invoking the capability once. Aligns with the existing propose-before-write posture. |
| **B4. Explicit confirm step naming what will be created** | The user is authorizing writes to their own disk. "This will create `cosmology/` with 4 categories and 1 seed card" is the difference between confidence and hesitation. | **LOW–MEDIUM** | `workspace.init` input schema. Cheap if B3 is done — the staged payload *is* the summary. |
| **B5. Per-step validation with immediate, specific errors** | Errors surfaced at submit after four steps are the classic multi-step form failure. | **MEDIUM** | `workspace.validate` for structural rules; client-side for format rules. |
| **B6. Success state that hands off to the next action** | A wizard that ends on "Done" is a dead end and directly costs the UX verdict — the user is now unaided again. End on the created artifact with the next suggestion attached. | **LOW** | `help.suggest` (re-invoked post-creation). This is where A4 loop closure pays off most visibly. |
| **B7 (ingest). Per-file status, real progress, drag-and-drop *plus* a picker** | Batch upload with one shared bar hides which file failed. Drag-and-drop must be an enhancement over a visible file picker, never the only method (accessibility + discoverability). Corroborated — MEDIUM. | **MEDIUM** | New upload endpoint on the HTTP API. |
| **B8 (ingest). Extraction preview — show the text that was actually extracted** | This is the entire point of the new extraction work. `ingest.source` today routes a file and writes a ref + seed card *without reading it*; a wizard that shows a filename and a checkmark proves nothing. Showing extracted text is how a user learns to trust PDF ingestion. | **MEDIUM–HIGH** | New extraction (txt/md/pdf/doc) + `ingest.source`. The preview is also the natural place to surface extraction quality problems (scanned PDF → empty text) before they become bad cards. |
| **B9 (ingest). Destination routing shown and overridable** | The user must see which domain a document is going to and be able to change it. Silent routing is how a workspace becomes untrustworthy. | **LOW–MEDIUM** | `ingest.source`, domains registry (`WorkspaceLoader.load_domains_registry`). |
| **B10 (ingest). Partial-success summary with per-item retry** | Partial success is the *normal* outcome for a mixed batch. The UI must state what succeeded, what failed, why, and what is retryable without re-uploading the successes. Corroborated — MEDIUM. | **MEDIUM** | New API job status. Rejection messages must name reason *and* fix together ("PDF has no extractable text — try an OCR'd copy"). |
| **B11 (ingest). Job status survives navigating away and back** | Extraction is asynchronous. If the user opens the graph mid-extraction and returns to a restarted or stale wizard, they lose trust in the whole system. Corroborated — MEDIUM. | **MEDIUM–HIGH** | New API job state. This is the one place draft/resume is genuinely table stakes rather than nice-to-have. |
| **B12 (ingest). Review of what got created, with links** | "Created 6 cards" is not verification. Link them; let the user open one. | **LOW** | `knowledge.card.list`, existing `CardSidePanel.jsx`. |

#### B. Differentiators

| Feature | Value Proposition | Complexity | Dependencies / Notes |
|---------|-------------------|------------|----------------------|
| **B13. Dry-run preview as a product-wide convention** | Every write surface in CONSTRUCT (research, curation, ingest, init) shows what it will do before doing it. This is already true of the workflows; making the wizards match turns an implementation detail into a legible product promise: *CONSTRUCT never writes behind your back.* | **LOW** (given B3/B4) | Consistency work, not new capability. Strongest single trust differentiator in the milestone. |
| **B14. Taxonomy suggestions derived from the extracted document** | First-run taxonomy setup is the hardest step for a new user (`_score_domain` priority 2, "hasn't been fully configured"). Proposing categories from actual uploaded content beats a blank form. | **HIGH** | Needs an LLM gate. **Propose-only, never auto-apply** — architecturally this is the same shape as an existing L3 gate. Defer past PoC. |
| **B15. Ingest one file end-to-end as the guided first-run path** | Collapses the demo path (upload PDF → cards → wiki + graph) into the onboarding path. One flow proves the whole product. | **MEDIUM** | Composition of B-init + B-ingest. High leverage for the verdict; low new code. |

#### B. Anti-Features

| Feature | Why Requested | Why Problematic *for CONSTRUCT* | Alternative |
|---------|---------------|--------------------------------|-------------|
| **Wizardizing routine operations (create card, add connection)** | Consistency — "everything is a wizard" | Card creation is a form with a few fields. A 3-step wizard around it adds clicks to the most frequent operation and makes the graph feel expensive to edit — directly suppressing the connection-building that `PRIORITY_MAP` state 4 nags about | Single-screen form in a side panel (`CardSidePanel.jsx` already exists); reserve wizards for genuinely multi-stage, multi-write flows |
| **Save-draft on the workspace-creation wizard** | Standard multi-step form advice | The flow is roughly three short steps over about a minute with no async work. A draft store adds persistence, expiry, and a "resume?" prompt for a flow nobody abandons mid-way, and creates exactly the half-state B3 exists to prevent | No drafts for B-init; drafts/job-resume are mandatory for B-ingest, where async extraction genuinely justifies them |
| **LLM auto-fills the domain interview and skips review** | Fastest path past the most tedious step | `content_categories` and `source_priorities` are *governance* data — `help.py:206` treats their absence as a configuration failure, and downstream research scoring depends on them. Silently generated governance is unowned governance; the user cannot later explain their own taxonomy | B14's propose-only form: fields pre-filled, visibly marked as suggestions, edited and confirmed by the human |
| **Wizard that ends by opening chat ("ask me anything about your new workspace")** | Feels helpful and warm | Re-centres chat at the exact moment the guided model must prove itself. If every wizard exits into chat, the UX verdict measures chat's usability, not the UI's | End on the created artifact plus `help.suggest`'s next step (B6) |
| **Cloud/remote import sources (Drive, Notion, URL fetch) in the ingest wizard** | Users have documents in many places | Local-first PoC on an isolated branch with no auth story (explicitly out of scope in PROJECT.md). Each connector adds an auth surface the milestone has ruled out | Local file upload only. `research.run` already covers web-sourced material through a governed path |
| **Progress percentage during extraction** | Feels informative | Extraction time is not linearly predictable across txt/md/pdf/doc; a percentage that stalls at 80% is worse than an honest per-file state machine | Per-file discrete states (queued → extracting → extracted → routed → failed) — both honest and more diagnostic |

---

### AREA C — Human-in-the-Loop Review Queue

One shared surface serving `research.review` and `curation.review`. Both already pause on a real `interrupt()` with a durable checkpointer (`.construct/workflow/*.sqlite`, adr-0004) — HIGH confidence, from PROJECT.md and the v0.4 record. External patterns below are corroborated across annotation tooling (Prodigy, Argilla, Label Studio) and moderation-queue design sources — MEDIUM.

#### C. Table Stakes

| Feature | Why Expected | Complexity | Dependencies / Notes |
|---------|--------------|------------|----------------------|
| **C1. Evidence visible without a second click** | A reviewer cannot approve what they cannot see. A *promote* proposal needs the card body, confidence, and source tier; a *connect* proposal needs both endpoints and the proposed type; an *archive* proposal needs the decay reason. Traceability back to the source is the strongest driver of calibrated trust. | **MEDIUM** | `research.inspect`, `curation.inspect`, `knowledge.connection.list`. `CardSidePanel.jsx`, `ConfidencePill.jsx`, `SourceTierIndicator.jsx` already exist — largely assembly. |
| **C2. Per-item accept / reject (partial approval)** | Already the backend contract (per-finding accept/reject). A UI offering only all-or-nothing throws away the system's best property. | **LOW–MEDIUM** | `research.review`, `curation.review`. Contract already supports it. |
| **C3. Single-key accept / reject / skip** | The reference implementation (Prodigy) puts approve/reject/skip on single keys so reviewers never reach for the mouse; queue review without keyboard flow is exhausting past roughly ten items. | **LOW** | UI only. Highest ratio of perceived quality to implementation cost in the milestone. Key hints must be on screen or they do not exist. |
| **C4. Queue position and remaining count** | "3 of 17" is orientation. Without it a queue feels unbounded and reviewers abandon mid-way, leaving the workflow interrupted. | **LOW** | `research.inspect`, `curation.inspect`. |
| **C5. Change a decision before apply (in-queue undo)** | Prodigy's model: undo is always available and returns the item to the front of the queue. Reviewers *will* misfire on a single-key interface — C3 is only safe if C5 exists. | **MEDIUM** | Client-side decision buffer until apply. This is undo *of a decision*, not of a write — see anti-features. |
| **C6. Explicit apply step with a written summary** | The gap between "I clicked accept 12 times" and "12 cards were promoted, 3 connections added" is where trust is won. AI-proposed changes should never commit automatically; the user sees what will change, selectively accepts, then commits. | **MEDIUM** | `research.review`, `curation.review` resume. Mirrors B3/B4 — same convention, second surface. |
| **C7. Durable resume — close the browser, come back, queue intact** | Normally a hard feature; **CONSTRUCT already has it** via the sqlite checkpointer. The UI must not squander it by holding queue state only in React. | **MEDIUM** | `workflow.status`, `research.inspect`, `curation.inspect`. Genuinely rare among comparable tools and directly supports the local-first story. |
| **C8. Distinguish the two queues** | Research proposals (promote findings) and curation proposals (archive decayed cards, add connections) carry different evidence and different stakes. Specialized queues beat one generic queue. | **LOW–MEDIUM** | Shared shell component, per-workflow item renderers. |
| **C9. Honest partial-failure state on apply** | If 9 of 12 writes land, the UI must say which 3 did not and why. Silent partial application on canonical data is the worst possible failure here. | **MEDIUM** | Review-capability result contract. |
| **C10. Empty-queue state that is not a dead end** | The most common state is "nothing to review." It should say why (no workflow has run) and offer to run one. | **LOW** | `workflow.status`, `research.run`, `curation.run`, `help.suggest`. |

#### C. Differentiators

| Feature | Value Proposition | Complexity | Dependencies / Notes |
|---------|-------------------|------------|----------------------|
| **C11. Bulk "accept all recommended", excluding escalate** | Throughput for large queues — but safely. This is *exactly* the rule v0.4 already shipped for `daily.run` (auto-apply each gate's recommended decision, escalate excluded; Key Decision D-02/D-03). Reusing it in the browser means the unattended and attended paths obey one rule. | **MEDIUM** | `research.review`, `curation.review`. **Never the default action.** Secondary control, must state its scope ("applies 9 of 12; 3 escalations still need you"), must not silently swallow escalations. |
| **C12. Confidence/score shown per proposal** | `research.score` already produces structured scores. Showing them lets reviewers triage. Caveat from the research: confidence indicators help only when users can interpret them — pair the number with the existing confidence vocabulary rather than showing a bare float. | **LOW–MEDIUM** | `research.score`, `card.evaluate`, `ConfidencePill.jsx`. |
| **C13. Link each applied decision to its event-log entry** | Turns the append-only `events.jsonl` audit trail into a visible product feature and substitutes for post-apply undo. | **MEDIUM** | Event log read path (new on the API). |
| **C14. Sort/filter the queue by proposal type or score** | Lets a reviewer clear all connection proposals in one mental mode instead of context-switching per item. | **MEDIUM** | Inspect capabilities. Skip if PoC queues stay small. |

#### C. Anti-Features

| Feature | Why Requested | Why Problematic *for CONSTRUCT* | Alternative |
|---------|---------------|--------------------------------|-------------|
| **"Accept all" as the default or most prominent action** | Fastest way to clear a queue; the reviewer feels productive | Defeats the purpose of a review gate — it makes the human a rubber stamp on canonical writes and turns the whole v0.4 HITL investment into ceremony. High acceptance with low evidence engagement is a documented trust-miscalibration signature | C11: secondary, scoped, escalate-excluded, with an explicit count of what it will and will not touch |
| **Post-apply undo / rollback of committed writes** | "Undo should always work" | Applied decisions are canonical writes plus append-only event-log entries. A rollback path means a second write authority over layer 1 and a mutable audit trail, contradicting the governance model. It is also largely redundant — promote/archive are reversible via `knowledge.card.archive` / `knowledge.card.edit` | C5 (undo before apply) + C13 (traceable event log) + normal card operations for genuine reversals |
| **Multi-reviewer assignment, inter-annotator agreement, reviewer stats** | Label Studio and similar tools have it; looks professional | Single-user, local-first, no auth (explicitly out of scope). Each adds identity plumbing serving zero users | Nothing. Deliberate omission. |
| **Auto-advance immediately after a destructive decision** | Keeps the rhythm going | Combined with single-key input, an accidental keystroke on an archive proposal advances past the mistake before it registers | Auto-advance is acceptable *because* C5 exists — but the last decision must stay visible ("last: archived X — undo") |
| **Inline editing of a proposal's card body inside the queue** | "I'd approve this if I could just fix the wording" | Turns the review surface into a second card editor with its own validation path, competing with `knowledge.card.edit`, and blurs approve-versus-author | Accept, then open the card in the existing editor from the summary (C6) |
| **A chat pane in the queue to "ask about this proposal"** | The evidence is complex; chat seems like the natural explainer | The queue is where chat demotion is most tempting to break, and breaking it means the evidence display (C1) never gets good enough to stand alone. The failure is silent: the UI looks fine and users route around it | Invest the same effort in C1. Genuine open-ended questioning is `ask.domain` in an explicitly LLM-gated modal launched from the card — not from the queue |

---

### AREA D — Knowledge Browsing (Wiki + Graph)

The strongest external finding: **the global force-directed graph is a known failure mode.** It reads well at 50–200 nodes and degenerates into an unreadable hairball past a few hundred; multiple independent comparisons of Obsidian/Logseq/Roam converge on this, and on the conclusion that graph views earn their keep as *filtered, local, diagnostic* tools rather than browse surfaces (MEDIUM, several independent sources). The existing `KnowledgeGraph.jsx` is force-directed — building the PoC around a global view would import a documented failure.

#### D. Table Stakes

| Feature | Why Expected | Complexity | Dependencies / Notes |
|---------|--------------|------------|----------------------|
| **D1. Click a node → detail panel without leaving the graph** | The primary graph interaction. Losing your view position on every inspection makes exploration impossible. | **LOW–MEDIUM** | `knowledge.card.list`, `views.generate_data`. `CardSidePanel.jsx` exists. |
| **D2. Search / find a node by name** | Past roughly 50 nodes, visual scanning fails. This is the graph's address bar. | **MEDIUM** | Node index from the views data. |
| **D3. Filter by domain, epistemic type, confidence, lifecycle** | The documented determinant of whether a graph is useful at all. CONSTRUCT's typed metadata makes this unusually easy — the facets already exist in the model. | **MEDIUM** | `views.generate_data` payload. `FilterChip.jsx` exists. |
| **D4. Local / focused graph — a node plus N hops** | The consistently useful form of graph navigation across every comparable tool. **Recommend this as the graph's default mode**, with the global view as an explicit opt-in. | **MEDIUM–HIGH** | Graph traversal over `knowledge.connection.list` data. The single highest-value graph decision in the milestone. |
| **D5. Orientation: what am I looking at, out of what** | "Showing 42 of 310 cards (filtered: Cosmology, confidence ≥3)" prevents mistaking a filtered view for the whole graph — a real correctness hazard when the graph is a diagnostic tool. | **LOW** | Counts from the views payload. |
| **D6. Reset view / zoom to fit** | Every user gets lost in a force layout. Without an escape they reload the page and lose all filter state. | **LOW** | UI only. |
| **D7. Deep-linkable node and article URLs** | Sharing, bookmarking, and — critically — the mechanism that lets guidance (A3) and review summaries (C6) point at specific knowledge. | **LOW–MEDIUM** | Route params. `routes.jsx` has no node- or article-level route under `/:workspace/knowledge-graph` — needs adding. |
| **D8. Wiki: readable article rendering with resolving internal links** | A wiki whose links do not resolve is broken. | **LOW–MEDIUM** | `views.generate_data`, `knowledge.card.list`. `MarkdownRenderer.jsx` exists. |
| **D9. Wiki: backlinks / "what links here"** | The defining wiki affordance and the cheapest path from reading to exploring. | **MEDIUM** | `knowledge.connection.list`. Data available; needs reverse indexing. |
| **D10. Wiki: an index/entry point that is not the workspace home** | Locked decision D5 makes the wiki a sibling view, so it needs its own front door — an A–Z or by-domain index reachable from nav. | **LOW–MEDIUM** | `knowledge.card.list`. |
| **D11. Provenance visible in the reading view** | Source tier and confidence on every article is what makes this a *governed* knowledge base rather than a note pile. Omitting it makes the wiki generic. | **LOW** | Card frontmatter. `ConfidencePill.jsx`, `SourceTierIndicator.jsx` exist. |
| **D12. Bidirectional wiki ↔ graph links** | What makes the two views one product rather than two demos: from an article, "see connections" opens the local graph focused on that card; from a node, open its article. | **MEDIUM** | D4 + D7. Directly honors locked D5 — graph and wiki are peers linking to each other, neither subordinate. |
| **D13. Empty and small-graph states** | A new workspace has one card and zero connections. A force layout showing one lonely dot is the moment an unaided user concludes the product is broken. | **LOW** | `help.suggest` embedded in the empty state (see A10). |

#### D. Differentiators

| Feature | Value Proposition | Complexity | Dependencies / Notes |
|---------|-------------------|------------|----------------------|
| **D14. Graph as a diagnostic surface — orphans, weak clusters, missing links highlighted** | The external consensus is that graph views are best as cleanup tools. CONSTRUCT already *computes* exactly these findings in `curation.run` (orphan detection, connection health). Rendering curation output onto the graph turns a decorative view into the product's analytical centrepiece — and no PKM competitor has the governed backend to do it. | **MEDIUM–HIGH** | `curation.inspect`, `curation.run`, `graph.status`. **The strongest differentiator in Area D.** |
| **D15. Typed, styled edges** | CONSTRUCT has typed connections; most graph views have undifferentiated links. Colour/label by type and the graph carries semantics, not just topology. | **LOW–MEDIUM** | `knowledge.connection.list`. Cheap; high perceived sophistication. |
| **D16. Confidence-weighted visual encoding** | Speculative and foundational knowledge should not look identical. Encodes the epistemic model visually. | **LOW–MEDIUM** | Card frontmatter. Must stay legible — one encoding channel, not four. |
| **D17. Cross-domain bridges highlighted** | `bridge.detect` exists and is unexercised in any UI. Cross-domain edges are the most interesting thing in a multi-domain graph. | **MEDIUM** | `bridge.detect`. High value-per-cost since the capability is already built. |

#### D. Anti-Features — including patterns that conflict with locked decisions

| Feature | Why Requested | Why Problematic *for CONSTRUCT* | Alternative |
|---------|---------------|--------------------------------|-------------|
| ⚠️ **Wiki as the workspace landing view** | Nearly every PKM product lands on reading. **And the mechanism already exists**: `routes.jsx` `WorkspaceEntry` reads `settings.workspace_landing` and redirects to `/:workspace/wiki` when set to `'wiki'` | **Conflicts with locked decision D5** (wiki is a sibling reading view, not the workspace default). The live redirect is a standing invitation to violate it by config — and a demo recorded with that setting on would misrepresent the shipped product | Keep `WorkspaceDashboard` as the default entry. Either remove the redirect for the PoC or keep it as a non-default, documented opt-in and pin the default with a test |
| ⚠️ **Auto-generated topic / hub / "map of content" pages in the wiki** | The most requested wiki feature in every PKM tool; looks like an obvious win over a flat card list | **Conflicts with locked decision D8** — topic synthesis and compilation belong to the `synthesis` workflow, not the wiki. A wiki that compiles topics quietly becomes a second synthesis engine with no governance, no confidence propagation, and no citation discipline | Wiki renders *cards* and their connections only. Compiled topic pages come from `synthesis`, are stored as artifacts, and the wiki may *link* to them |
| ⚠️ **Editing cards in place in the wiki** | Wikis are editable; it feels natural and users will try | The wiki is a read-only projection of the views layer. In-place editing creates a second writer to canonical data outside the governed write path, and the views data is derived — edits would be silently overwritten on the next `views.generate_data` | Read-only wiki with an explicit "edit this card" action routing to the governed editor (`knowledge.card.edit`) |
| ⚠️ **"Chat with your graph" as the graph's primary affordance** | `ask.domain` exists; a query box over a graph is a compelling demo | Re-centres chat exactly where structured exploration must prove itself, and the failure is invisible — the graph *looks* finished while nobody uses D2/D3/D4 | `ask.domain` as an LLM-gated modal launched from a secondary control; D2 search and D3 filters carry the primary interaction |
| **Global force-directed graph as the default view** | The screenshot everyone wants | Documented to degenerate past a few hundred nodes; the layout is also non-deterministic, so the same workspace looks different every load — corrosive to the trust story A9 builds | D4 local/focused default; global view opt-in with a node-count warning above a threshold |
| **Physics/layout tuning controls (charge, link distance, gravity)** | Every force-graph library exposes them; cheap to wire up | Exposes implementation to the user, invites fiddling instead of thinking, and makes views unreproducible. Users cannot map these parameters to any knowledge question | Two or three named presets at most, or nothing. Spend the effort on D3 filters |
| **3D graph view** | Spectacular in demos | Strictly worse for reading labels and tracing edges; occlusion makes every real question harder. Pure demo-ware, and it would consume PoC budget D4/D14 need | 2D with good filtering |
| **Real-time collaborative cursors / presence in the graph** | Standard in modern knowledge tools | Single-user, local-first, no auth — explicitly out of scope | Nothing |

---

### AREA E — Cross-Cutting Shell (not asked, but decisive for the verdict)

The verdict is "can a person navigate CONSTRUCT unaided." That is answered by the shell as much as by any single flow — and by whether the experiment is even valid.

| Feature | Category | Complexity | Notes |
|---------|----------|------------|-------|
| **E1. Every core loop completable without opening chat** | Table stakes | **MEDIUM** | The measurement precondition. If chat is available as a general fallback, users route around UI gaps and the PoC learns nothing about the guided model. |
| **E2. Chat only as LLM-gated modals at points requiring an LLM** | Table stakes | **MEDIUM** | `ask.domain` is the clear case: scoped, launched from a specific object, closes and returns. Post-chat AI UX consensus favours visible affordances, structured input, and assistance scoped to a surface over a global text field — MEDIUM. |
| **E3. Persistent nav + workspace switcher + breadcrumbs** | Table stakes | **LOW** | `WorkspaceSwitcher.jsx`, `Header.jsx`, `Layout.jsx` exist. |
| **E4. Loading / error / empty state on every page** | Table stakes | **LOW–MEDIUM** | `LoadingState.jsx`, `ErrorState.jsx`, `EmptyState.jsx` exist. With a live API replacing static JSON, error states become reachable for the first time — currently the biggest untested surface. |
| **E5. Honest degraded-mode surfacing** | Table stakes | **MEDIUM** | `curation.run` deliberately exits 0 when degraded; status is carried in the payload, not the exit code. A UI reading only success/failure will report degraded runs as clean successes — a correctness bug the UI can introduce on its own. |
| **E6. Global search across cards** | Differentiator | **MEDIUM** | `knowledge.card.list`. Often the fastest path to "I can find my stuff," which is most of the felt verdict. |
| **E7. Keyboard command palette** | Differentiator | **MEDIUM–HIGH** | Attractive, but for a PoC judged on *unaided* navigation a palette rewards experts and is invisible to the target user. Defer. |
| **Global always-present chat dock/sidebar** | ⚠️ **Anti-feature** | — | The single change most likely to invalidate the milestone. It becomes the path of least resistance, hides every UI gap, and makes the verdict unmeasurable. |
| **Login / accounts / sharing / cloud sync indicators** | ⚠️ **Anti-feature** | — | Explicitly out of scope (no auth, no multi-user, no remote hosting). Even the visual affordances suggest a product this deliberately is not. |

---

## Feature Dependencies

```
[HTTP API over capability registry]              <- everything below depends on this
    |
    +--requires--> [views generate <-> validate byte contract fixed]   (named PoC prerequisite)
    |
    +--enables--> [A. Guided layer]
    |                 └──requires──> [A1 priority->action mapping]   <- the missing artifact
    |                 └──requires──> [A4 loop closure] ──requires──> re-invoke help.suggest post-write
    |
    +--enables--> [B-init wizard] ──requires──> [B3 single commit point]
    |                                              └──enables──> [B4 confirm summary]
    |
    +--enables--> [B-ingest wizard]
    |                 └──requires──> [real text extraction: txt/md/pdf/doc]  <- new
    |                 └──requires──> [B11 durable job status]
    |                 └──requires──> [B8 extraction preview] ──requires──> extraction
    |
    +--enables--> [C. Review queue]
    |                 └──requires──> [C1 evidence display] ──requires──> research.inspect / curation.inspect
    |                 └──requires──> [C7 durable resume] ──requires──> workflow.status + sqlite checkpointer
    |                 └──requires──> [C3 single-key input] ──requires──> [C5 in-queue undo]   (hard pairing)
    |
    +--enables--> [D. Browse]
                      └──requires──> [D4 local/focused graph] ──enables──> [D12 wiki<->graph links]
                      └──requires──> [D7 deep-linkable URLs] ──enables──> A3, C6, D12
                      └──enhances──> [D14 diagnostic graph] ──requires──> curation.inspect

[E1 chat-free core loops] ──conflicts──> [global chat dock]
[D. Wiki] ──conflicts──> [wiki-as-landing (locked D5)] and [wiki topic compilation (locked D8)]
[C11 bulk accept] ──conflicts──> [C6 explicit review] unless scoped to recommended-and-not-escalate
```

### Dependency Notes

- **Everything requires the HTTP API.** The SPA is static-file-fed today; without capability *invocation* over HTTP, wizards and review queues cannot exist at all. This is the milestone's critical path and no UI feature can precede it.
- **A1 is the milestone's hidden dependency.** The guided layer looks like a rendering task and is actually a product-decision task: seven states, seven verbs, seven destinations. Cheap to build, expensive to skip — skipping it means guidance renders as a diagnosis with no next step, and the verdict comes back "no."
- **C3 requires C5.** Single-key accept/reject without undo produces silent mistakes on canonical writes. Ship both or neither.
- **D7 unblocks three areas.** Deep-linkable node/article URLs are how guidance points at work (A3), how review summaries point at results (C6), and how wiki and graph point at each other (D12). Low complexity, unusually high fan-out — do it early.
- **B8 requires real extraction.** The extraction preview is not a UI feature dressed over the existing `ingest.source`; that capability does not read files today. Preview and extraction ship together or the wizard is theatre.
- **D14 is nearly free given curation.** The orphan and connection-health findings already exist as `curation.run` output. Rendering them on the graph is data binding, not new analysis.

---

## MVP Definition

### Launch With (the PoC that answers the verdict)

The mechanical gate is: upload a PDF → cards → wiki + graph. The UX gate is: a person does that unaided.

- [ ] **A1 + A2 + A3 + A6** — guided layer with real action mapping, top CTA, deep-linked launch, first-run empty state. *Without A1 the milestone cannot answer its own question.*
- [ ] **A4** — loop closure. The one behaviour that converts guidance from decoration into a trusted mechanism.
- [ ] **B1–B6** — workspace wizard with single commit point and a handoff ending. Covers `_score_domain` priorities 1 and 2, the states a new user actually starts in.
- [ ] **B7–B12** — ingest wizard with real extraction preview, routing, partial-success handling, durable job status. This is the demo path.
- [ ] **C1–C7, C10** — review queue with evidence, per-item decisions, keyboard flow, in-queue undo, explicit apply, durable resume, non-dead-end empty state.
- [ ] **D1–D13** — graph defaulting to local/focused with filters, search, orientation and reset; wiki with resolving links, backlinks, its own index, visible provenance; bidirectional links between them.
- [ ] **E1–E5** — chat-free core loops, scoped LLM modals, nav, honest states including degraded runs.

### Add After Validation (v0.5.x / v0.6)

- [ ] **C11 bulk accept-recommended** — add once queue sizes prove it necessary; premature bulk actions teach rubber-stamping before the review UI has earned trust.
- [ ] **D14 diagnostic graph overlay** — the standout differentiator, but the base graph must be trustworthy first.
- [ ] **D15 / D16 / D17** — typed edges, confidence encoding, `bridge.detect` overlay. Cheap wins once D1–D13 are stable.
- [ ] **C13 event-log links**, **C12 scores**, **E6 global search**.
- [ ] **A11 health trend** — needs stored snapshots.

### Future Consideration (v0.6+)

- [ ] **B14 LLM taxonomy suggestions** — propose-only; defer until the L3 gate pattern is proven in the browser.
- [ ] **E7 command palette** — rewards experts; irrelevant to an unaided-navigation verdict.
- [ ] **C14 queue sort/filter** — only matters at queue sizes the PoC will not reach.
- [ ] Anything requiring auth, sync, or multi-user — explicitly out of scope by milestone decision.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| A1 priority → action mapping | HIGH | LOW–MEDIUM | **P1** |
| A4 loop closure (re-evaluate after action) | HIGH | MEDIUM | **P1** |
| B3 single commit point (no partial writes) | HIGH | MEDIUM | **P1** |
| B8 extraction preview | HIGH | MEDIUM–HIGH | **P1** |
| C1 evidence display in queue | HIGH | MEDIUM | **P1** |
| C6 explicit apply with summary | HIGH | MEDIUM | **P1** |
| D4 local/focused graph as default | HIGH | MEDIUM–HIGH | **P1** |
| D7 deep-linkable URLs | MEDIUM | LOW–MEDIUM | **P1** (high fan-out) |
| E1 chat-free core loops | HIGH | MEDIUM | **P1** (validity precondition) |
| A5 "why this?" evidence | MEDIUM | LOW | **P1** (cheap trust) |
| C3 + C5 keyboard flow + in-queue undo | HIGH | LOW + MEDIUM | **P1** (ship as a pair) |
| D3 graph filtering | HIGH | MEDIUM | **P1** |
| D11 provenance in wiki | MEDIUM | LOW | **P1** (defines the category) |
| E5 degraded-mode honesty | MEDIUM | MEDIUM | **P1** (correctness, not polish) |
| B10 / B11 partial success + durable job | MEDIUM | MEDIUM–HIGH | **P2** |
| C7 durable queue resume | MEDIUM | MEDIUM | **P2** (backend already does the hard part) |
| D9 backlinks | MEDIUM | MEDIUM | **P2** |
| D14 diagnostic graph overlay | HIGH | MEDIUM–HIGH | **P2** (top differentiator) |
| C11 bulk accept-recommended | MEDIUM | MEDIUM | **P2** (guardrails mandatory) |
| D15 / D16 typed + confidence-weighted edges | MEDIUM | LOW–MEDIUM | **P2** |
| D17 bridge.detect overlay | MEDIUM | MEDIUM | **P3** |
| A11 health trend | LOW | MEDIUM | **P3** |
| B14 LLM taxonomy suggestions | MEDIUM | HIGH | **P3** |
| E7 command palette | LOW | MEDIUM–HIGH | **P3** |

**Priority key:** P1 must ship for the verdict to be answerable · P2 add after core validates · P3 future.

---

## Competitor Feature Analysis

| Feature | Obsidian / Logseq | Prodigy / Label Studio | Notion / Airtable-style import | Our Approach |
|---------|-------------------|------------------------|-------------------------------|--------------|
| **Next-action guidance** | None — the vault is inert; the user supplies all intent | N/A (the task queue *is* the guidance) | Onboarding checklist, adaptive, dismissible | Deterministic, workspace-derived, explainable (A9) — a property no PKM competitor can claim |
| **Graph view** | Global force graph; local graph is the actually-useful mode; degenerates past a few hundred nodes | N/A | N/A | Local/focused by default (D4); global opt-in with warning; typed and confidence-encoded edges (D15/D16) |
| **Wiki / reading** | Notes are the primary surface; graph is the sibling | N/A | Pages are primary | **Inverted by locked D5** — dashboard is the entry, wiki is the sibling. Provenance visible (D11) |
| **Topic hub pages** | User-maintained MOCs, or plugin-generated | N/A | Auto-rollups and linked views | **Explicitly not a wiki responsibility (locked D8)** — owned by `synthesis`, linked from the wiki |
| **Review queue** | None | Single-key accept/reject/skip; always-available undo returning the item to the queue front; Label Studio adds multi-reviewer and agreement metrics | N/A | Prodigy's keyboard + undo model (C3/C5); Label Studio's multi-reviewer features deliberately omitted (single-user) |
| **Bulk approval** | N/A | Bulk mode exists; Argilla has a filed bug where shortcuts silently stop working in bulk mode | Bulk import commits everything | Secondary only, scoped to recommended-and-not-escalate (C11), reusing the shipped `daily.run` rule |
| **Import / extraction** | Drop a file in the vault; no extraction step | N/A | Preview + column mapping + confirm | Preview the *extracted text* (B8), show and allow overriding routing (B9), single commit at confirm (B3) |
| **Provenance** | Backlinks only | Annotation metadata | Source-page links | Confidence + source tier + event log on every card — the category-defining difference |
| **Chat / AI surface** | Plugin sidebars, increasingly global | N/A | Global AI dock | Deliberately demoted to scoped modals (E2); a global dock is treated as an anti-feature |

---

## Constraint-Conflict Register

Common patterns that collide with CONSTRUCT's locked decisions. Flagged for requirements and roadmap.

| Conflicting pattern | Locked decision it violates | Where it can leak in | Recommended handling |
|---------------------|----------------------------|----------------------|----------------------|
| Wiki as the workspace landing page | **D5** — wiki is a sibling reading view, not the default | `routes.jsx` `WorkspaceEntry` already redirects to `/wiki` when `settings.workspace_landing === 'wiki'` | Pin the dashboard default with a test; treat the redirect as non-default opt-in, or remove it for the PoC |
| Auto-generated topic / hub / MOC pages in the wiki | **D8** — topic synthesis belongs to `synthesis` | Any "summarize this tag/domain" affordance added to the wiki | Wiki renders cards + connections only; link out to synthesis artifacts |
| In-place wiki editing | Governed write path; the views layer is a derived read-only projection | A tempting "edit" button on a rendered article | Route to the governed editor (`knowledge.card.edit`); never write through the views layer |
| Global chat dock / chat as fallback | Chat demotion — **and the milestone's own measurement validity** | Any "add an assistant sidebar, it's easy" moment | Scoped LLM modals only (E2). Chat-free completability of every core loop (E1) is a gate, not a preference |
| Chat as the guided-layer entry point | Chat demotion | Reusing today's behaviour, where an agent renders `help.suggest` in prose | Structured action mapping (A1) |
| Auth / sharing / sync / multi-reviewer affordances | Local-first PoC, no auth, no multi-user (PROJECT.md Out of Scope) | Copying patterns wholesale from Label Studio or SaaS onboarding | Omit entirely, including the visual suggestion of them |
| Adopting CoPilotKit-style generative UI as the shell | CoPilotKit is **evaluated, not adopted** (SEED-001) | Spike enthusiasm bleeding into PoC implementation | Keep the spike's output a verdict document; the PoC ships on the existing SPA |

---

## Gaps and Open Questions for Requirements

1. **Who owns the priority → action mapping (A1)?** A static table in the SPA is fastest, but the same mapping is arguably useful to the CLI and MCP surfaces. Extending `help.suggest` to emit a `suggested_capability` / `action` field would give all three adapters one contract — consistent with the registry-as-single-contract principle, at the cost of touching a shipped capability. **Recommend the backend option** if the roadmap has room; the frontend table is an acceptable PoC shortcut only if explicitly labelled as such.
2. **`help.suggest` priority 5 fires on healthy domains** (`help.py:213`, "last research was N days ago"). The action mapping must classify it as informational or the guided layer nags permanently. Worth confirming whether this scoring is intended.
3. **Degraded-status rendering (E5)** needs a decided convention before it is built — the `curation.run` exit-code contract means the UI must read status from the payload, and there is no precedent for how a browser should present "completed with degraded steps."
4. **Graph data source at scale** — whether the views JSON payload is the graph's data source or the HTTP API serves live traversal materially changes D2/D3/D4 cost. An architecture question, but it gates three P1 features.
5. **Extraction failure taxonomy** — B10's "name the reason and the fix" needs an actual list of failure modes from the extraction work (scanned PDF, encrypted PDF, unsupported .doc variant, empty file) before error copy can be written.

---

## Sources

Internal (HIGH confidence — read directly):
- `/Users/mab/dev/mabstruct/construct/.planning/PROJECT.md` — v0.5 milestone scope, Out of Scope, locked decisions D5/D8, Key Decisions D-02/D-03 (recommended-only auto-apply, escalate excluded)
- `/Users/mab/dev/mabstruct/construct/src/construct/services/help.py` — `PRIORITY_MAP` (:21), `suggest()` (:32), `_score_domain()` (:193), `_result()` (:217); suggestion payload shape
- `/Users/mab/dev/mabstruct/construct/src/construct/capabilities/catalog.py` — the 28 capability ids used for dependency mapping
- `.../construct-views-scaffold/template/src/routes.jsx` — route map and the `workspace_landing === 'wiki'` redirect
- `.../construct-views-scaffold/template/src/pages/`, `.../components/` — existing page and component inventory

External (MEDIUM where corroborated across independent sources, LOW where single-source; provider `websearch`, tiers via `gsd-tools query classify-confidence`):
- Wizard patterns — PatternFly Wizard design guidelines plus multiple independent multi-step-form UX write-ups (progress naming, non-destructive back, revert-on-cancel, save-and-resume, per-step validation) — MEDIUM
- Annotation / review tooling — Prodigy web-app docs (key bindings, undo returning tasks to the queue front); Argilla issue #4634 (shortcuts failing in bulk mode); Label Studio vs Prodigy comparisons (multi-reviewer features) — MEDIUM
- Moderation queue design — Stream moderation-queue guide and Moderation API review-queue docs (bulk actions with auto-refresh, per-item confidence, immutable audit records, specialized queues, single-key approve/reject/skip) — MEDIUM
- Graph-view limits — independent Obsidian/Logseq/Roam comparisons converging on hairball degradation past a few hundred nodes, filtering as the determinant of usefulness, local graph as the useful mode, graph-as-cleanup-tool — MEDIUM
- AI suggestion trust — explainable-AI UX sources on provenance, "why you're seeing this", confidence indicators (Google PAIR caveat), acceptance-without-verification as a trust-miscalibration signal, and the argument against "accept all" as a default — MEDIUM
- Upload / async-job UX — per-file status over batch bars, partial-success summaries with per-item retry, drag-and-drop as enhancement not sole method, reason-and-fix error copy, job status surviving navigation — MEDIUM
- Onboarding guidance — adaptive/context-aware checklists outperforming scripted tours, skippability, activation-moment anchoring — MEDIUM
- Chat-demotion rationale — post-chat AI UX critiques (chat as what shipped rather than what worked; structured affordances, previews, and scoped assistance over a global text field) — LOW to MEDIUM (opinion-heavy sources, directionally consistent)

---
*Feature research for: browser-first shell over a local-first governed knowledge graph*
*Researched: 2026-07-26*
