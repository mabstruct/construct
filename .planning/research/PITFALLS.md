# Domain Pitfalls

**Domain:** Local-first, agent-powered knowledge system with governed markdown/json workspaces  
**Researched:** 2026-06-08  
**Overall confidence:** HIGH for repo-specific risks, MEDIUM for later runtime/UI migration risks

## Critical Pitfalls

### Pitfall 1: Contract drift across templates, skills, validators, and views
**What goes wrong:** The same artifact gets defined differently in multiple places. A field is required in validation, optional in a skill, absent in a template, or interpreted differently by views/runtime code.

**Why it happens:** CONSTRUCT currently spreads contract knowledge across templates, `SKILL.md` procedures, validation docs, artifact inventory, and view-generation logic. The known pain point in this milestone already confirms this failure mode.

**Consequences:**
- Agents produce structurally valid but semantically inconsistent files
- Validators become noisy or incomplete
- UI/runtime migration bakes in the wrong assumptions
- Small schema changes trigger repo-wide drift and rework

**Warning signs:**
- The same field appears with different requiredness in different docs
- Views/parser code needs one-off exceptions for older or malformed files
- Skills describe “usually” or “if present” behavior for fields that should be deterministic
- Manual cleanup is needed after research or curation cycles

**Prevention strategy:**
- Establish a single canonical contract source for each artifact type
- Generate validators, UI forms, and runtime types from that canonical source
- Add a contract-change checklist: template + validator + skill + catalog + views all updated together
- Treat `artifact-catalog.md` as inventory, not the schema source

**Which phase should address it:** **Phase 1 — Data contract canon and schema hardening**

### Pitfall 2: Dual source of truth for graph edges
**What goes wrong:** Relationship state exists both in card frontmatter (`connects_to`) and in `connections.json`, and the two diverge.

**Why it happens:** The current model asks multiple artifacts to describe the same graph facts. Validation then has to repair consistency after the fact.

**Consequences:**
- Graph views disagree with card detail views
- Orphan/bridge/promotion logic produces inconsistent results
- UI migration inherits ambiguous write semantics
- Future runtime indexing becomes harder because edge truth is unclear

**Warning signs:**
- A card says it connects to another card but no edge exists in `connections.json`
- Editing a card ID requires multi-file repair logic
- “Why is this node disconnected?” becomes a recurring debugging question

**Prevention strategy:**
- Pick one canonical edge store
- Make the other representation derived-only, or remove it entirely
- Ensure one writer owns graph mutation semantics
- Add invariant tests that fail on any edge duplication or disagreement

**Which phase should address it:** **Phase 1 — Data model simplification before runtime/UI work**

### Pitfall 3: Checklist validation instead of enforced write gates
**What goes wrong:** Skills say they validate, but validation remains procedural guidance rather than an enforced mutation gate. Bad writes still land, and cross-file partial updates leak through.

**Why it happens:** In the Claude-native model, many guarantees live in instructions rather than in hard runtime boundaries. Validation is conceptually embedded everywhere, but enforcement is soft.

**Consequences:**
- A card writes successfully while event logging or graph updates fail
- Duplicate refs/cards appear after retries
- Recovery requires manual audit instead of deterministic rollback
- Trust in the workspace declines

**Warning signs:**
- Re-running a skill changes outputs that should be idempotent
- Validation finds issues immediately after a successful skill run
- Users are told “workspace is intact” but derived state or sibling files are not
- The same operation sometimes emits different file shapes

**Prevention strategy:**
- Introduce preflight validation before write and post-commit validation after write
- Use staged mutation plans for multi-file operations
- Make writes atomic per artifact and idempotent per operation
- Add machine-enforced mutation wrappers before a hardened runtime exposes them

**Which phase should address it:** **Phase 2 — Workflow reliability and mutation safety**

### Pitfall 4: Event log becomes non-authoritative theater
**What goes wrong:** `events.jsonl` exists, but not every mutation is logged reliably, consistently, or in replayable form.

**Why it happens:** The current operating model requires significant actions to be logged, but that rule is instruction-based. As new runtime paths and later UI actions appear, logging can silently fragment.

**Consequences:**
- Audit and recovery become unreliable
- UI activity feeds and future diagnostics cannot trust history
- Migration tooling cannot replay or reconcile workspace state
- Compliance with “append-only” becomes nominal, not operational

**Warning signs:**
- Card files exist without matching `create_card` events
- Promotions, archives, or repairs are visible in files but absent in history
- Timestamps are out of order or too coarse to reason about sequencing
- Different skills log different payload shapes for similar actions

**Prevention strategy:**
- Define a versioned event schema and required event set for every mutation class
- Emit events through one shared mutation/logging path
- Add periodic reconciliation: files ↔ events must match
- Design the runtime so UI and agent actions hit the same evented command boundary

**Which phase should address it:** **Phase 2 — Auditability and replayable operations**

### Pitfall 5: Too much agent discretion at the tool boundary
**What goes wrong:** Steps that should be deterministic remain prompt-shaped. The model infers missing parameters, picks file shapes opportunistically, or mutates source-of-truth data without a narrow contract.

**Why it happens:** Chat-native systems start wide and flexible. CONSTRUCT03 explicitly wants to shrink open-ended chat and default to `UI`/`PIPE`, but migration often stalls and leaves “temporary” ambiguity in place.

**Consequences:**
- Same request yields different mutations across sessions
- Governance/domain files become vulnerable to accidental edits
- UI buttons end up wrapping fragile prompts instead of stable commands
- Debugging focuses on prompting rather than system design

**Warning signs:**
- Tool inputs depend on interpretation rather than explicit fields
- A skill succeeds only with carefully phrased user language
- The agent fills missing information instead of requesting or structuring it
- Review/approval gates are inconsistent across skills

**Prevention strategy:**
- Separate deterministic operations from judgment calls now
- Put strict schemas around tool/command inputs where possible
- Require explicit confirmation for source-of-truth writes from ambiguous model output
- Reserve LLM-only paths for synthesis, contradiction handling, and editorial review

**Which phase should address it:** **Phase 2 — Command boundary hardening**, then **Phase 4 — API extraction for UI**

### Pitfall 6: Hidden state sneaks back in through views, caches, and indexes
**What goes wrong:** The product claims “if the files are correct, the system is correct,” but later runtime layers start depending on cached JSON, fingerprints, indexes, or debounced hook state to function correctly.

**Why it happens:** The current view generator already maintains build metadata and debounced hook state. That is reasonable, but dangerous if future runtime/UI code starts treating derived state as authoritative.

**Consequences:**
- UI shows stale or contradictory state
- Bugs disappear after “refresh” because the cache, not the source files, was wrong
- Runtime hardening accidentally recreates the hidden-state fragility the project wants to avoid

**Warning signs:**
- Users must manually rebuild or refresh to trust what they see
- Runtime behavior changes depending on whether a background generator ran
- Derived folders become required for normal operation
- Support/debug advice frequently starts with “try regenerating views”

**Prevention strategy:**
- Keep source-of-truth files authoritative and derived state disposable
- Mark freshness/version status clearly in any UI
- Rebuild indexes/caches from source files automatically and safely
- Make “stale derived state” a warning, never a silent correctness bug

**Which phase should address it:** **Phase 3 — Runtime/index/view boundary hardening**

### Pitfall 7: Local-first without concurrency, backup, and recovery semantics
**What goes wrong:** The system is local-first in storage but not operational semantics. Concurrent edits from agent, UI, editor, Git, or hooks race; recovery paths are unclear; users can lose trust after one malformed or conflicting write.

**Why it happens:** File-based systems feel simple until multiple writers, watchers, background jobs, and manual edits coexist.

**Consequences:**
- Truncated or conflicted JSON/YAML files
- Lost updates from last-write-wins behavior
- File watcher storms or repeated regen cycles
- Fear of manual edits, Git use, or UI adoption

**Warning signs:**
- Mutations occasionally require “run again” to settle
- Background hooks touch files the user did not expect
- Git diffs show unrelated churn after a focused operation
- Same workspace behaves differently depending on whether views/server is running

**Prevention strategy:**
- Add atomic write discipline and a clear multi-writer policy
- Introduce workspace locking or transactional command serialization for hardened runtime paths
- Ship backup/snapshot/recovery workflows early, not after UI launch
- Decide explicitly what happens when files change outside the runtime

**Which phase should address it:** **Phase 3 — Hardened local runtime and recovery model**

### Pitfall 8: Building the UI on top of chat-era workflows instead of stable commands
**What goes wrong:** The UI becomes a thin shell around prompt orchestration. Validation, state transitions, and permissions get duplicated in frontend code because the backend contract is still informal.

**Why it happens:** It is tempting to make UI progress by wrapping existing skills first. For CONSTRUCT, that would freeze prototype behavior instead of extracting the right command/API layer.

**Consequences:**
- Frontend and agent logic diverge
- UI introduces a second interpretation of workflow state
- Later runtime changes force expensive UI rewrites
- “What does this button really do?” maps to prompt internals instead of domain operations

**Warning signs:**
- UI actions are described in terms of chat prompts rather than command contracts
- Frontend performs schema/business-rule validation that the runtime cannot guarantee
- The same operation exists in separate chat, script, and UI implementations

**Prevention strategy:**
- Define stable command/API boundaries before substantive UI work
- Map each artifact-catalog row to `UI`, `PIPE`, `LLM`, or `HYB` with real backend ownership
- Keep LLM review as a bounded step after structured data collection, not the transport layer itself

**Which phase should address it:** **Phase 4 — Runtime/API surface definition**, before **Phase 5 — UI-primary product work**

## Moderate Pitfalls

### Pitfall 9: Governance metadata becomes decorative instead of decision-grade
**What goes wrong:** Confidence, source tier, lifecycle, and epistemic type are filled in mechanically and stop carrying real meaning.

**Prevention strategy:**
- Add rubrics, examples, and audits for metadata quality
- Make promotion/curation explain how governance fields were used
- Surface low-confidence clusters clearly in future UI/views

**Which phase should address it:** **Phase 2 — Governance enforcement**, then **Phase 5 — UI explanation layers**

### Pitfall 10: Scale assumptions leak past the Claude-native limit
**What goes wrong:** Workflows keep assuming whole-workspace reads even though the NFRs explicitly cap the Claude-native path at about 500 cards.

**Prevention strategy:**
- Add domain-scoped operations and persistent indexes in the hardened runtime
- Measure read breadth and mutation cost per workflow
- Do not let UI features assume full-graph materialization is always cheap

**Which phase should address it:** **Phase 3 — Indexing and performance envelope work**

### Pitfall 11: Derived outputs gain accidental user-edit status
**What goes wrong:** Users start editing digests, generated data, or publish artifacts as if they were source-of-truth, creating unclear ownership and merge rules.

**Prevention strategy:**
- Label source-of-truth vs derived artifacts aggressively
- Decide which outputs are editable and which are regenerated
- Enforce write boundaries in tooling and later UI affordances

**Which phase should address it:** **Phase 3 — Artifact boundary hardening**

## Minor Pitfalls

### Pitfall 12: Overfitting workflows to the current test fixtures
**What goes wrong:** Skills and later runtime behavior appear reliable on `test-ws/` but fail on messier real-world workspaces.

**Prevention strategy:**
- Add adversarial fixture workspaces with malformed, partial, and migrated data
- Include migration-era cases, not just happy-path domains

**Which phase should address it:** **Phase 2 — Validation/eval fixtures**

### Pitfall 13: Help/next-step logic becomes stale product choreography
**What goes wrong:** The system tells users what to do next based on outdated assumptions about workflow order or health signals.

**Prevention strategy:**
- Drive next-step suggestions from validated state, not static workflow narratives
- Reuse the same status primitives in chat and later UI dashboards

**Which phase should address it:** **Phase 2 — State-aware workflow guidance**

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Data contract hardening | Contract drift and dual graph truth persist | Canonical schemas, single ownership per artifact, contract diff checklist |
| Phase 2: Workflow reliability | Validation remains advisory; logging remains incomplete | Enforced write gates, idempotent commands, event schema + reconciliation |
| Phase 3: Hardened runtime | Hidden caches/indexes become de facto truth; concurrent writers race | Disposable derived state, lock/serialize writes, recovery/backup model |
| Phase 4: Runtime/API extraction | UI wraps prompts instead of domain commands | Stable command surface, typed inputs, explicit LLM review gates |
| Phase 5: UI-primary product | Frontend duplicates backend rules and hides governance provenance | Shared contracts, backend-owned validation, provenance/freshness visibility |

## Recommended sequencing implication

Do **not** treat the current inconsistency problem as a documentation cleanup. For CONSTRUCT, it is the architectural precursor to every later phase. The safe order is:

1. **Canonicalize data contracts**
2. **Enforce mutation and audit boundaries**
3. **Harden local runtime behavior under multi-writer and derived-state pressure**
4. **Extract stable UI/API commands**
5. **Only then build the UI-primary layer**

## Sources

- `.planning/PROJECT.md` — milestone goals, constraints, current pain point
- `CONSTRUCT-CLAUDE-spec/nfrs.md` — reliability, scale, local-first constraints
- `CONSTRUCT-CLAUDE-spec/validation-strategy.md` — validation model and current enforcement assumptions
- `CONSTRUCT-CLAUDE-spec/artifact-catalog.md` — current artifact inventory and v0.3/v0.4 transition model
- `CONSTRUCT-CLAUDE-impl/AGENTS.md` — operating rules, SOT boundaries, event logging expectations
- `CONSTRUCT-CLAUDE-impl/construct/templates/*` — current artifact shapes
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-{research-cycle,curation-cycle,workspace-validate,views-generate-data}/SKILL.md` — actual workflow and failure-mode behavior
- Anthropic docs: Tool use overview — tool boundaries and inference behavior (**HIGH confidence**)  
  https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- Anthropic docs: Strict tool use — schema-enforced tool inputs (**HIGH confidence**)  
  https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/strict-tool-use
- Anthropic docs: Reduce hallucinations — grounding and verification patterns (**MEDIUM confidence for direct applicability**)  
  https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
- Ink & Switch: *Local-first software* — long-term local-first failure patterns around ownership, sync, and offline semantics (**MEDIUM confidence for direct applicability**)  
  https://www.inkandswitch.com/essay/local-first/
