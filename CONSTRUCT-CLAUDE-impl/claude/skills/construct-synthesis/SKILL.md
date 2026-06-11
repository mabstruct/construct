---
description: Create grounded synthesis outputs from workspace knowledge using CLI commands for data acquisition and LLM-driven drafting.
allowed-tools:
  - Read
  - Bash(construct)
  - MCP(connect)
  - WebSearch
  - WebFetch
---

> **Note:** Card knowledge acquisition now uses `construct ask domain` CLI (grounded Q&A)
> and `construct knowledge card list` CLI (card enumeration) instead of inline `Read`
> operations. The `Read` tool is still available for individual card inspection and
> config file reading. `Write` is removed — synthesis output is returned via CLI
> structured output, not written to files.

# Skill: Synthesis / Drafting

**Trigger:** User says "draft a paper on...", "synthesize...", "write a briefing about...", "summarize the state of...", or similar.
**Agent:** CONSTRUCT (orchestrator — frontier reasoning required)
**Produces:** Draft document drawing on workspace knowledge with inline citations and confidence metadata

---

## INPUT

- **Workspace:** A CONSTRUCT workspace directory with knowledge cards
- **Query/Topic:** Natural language question or topic to synthesize about
- **Domain (optional):** Target domain ID for bounded synthesis (default: all domains)
- **Max cards (optional):** Maximum cards to consider (default: 20, max: 50)

## OUTPUT

- **Synthesis:** Natural language synthesis grounded in workspace knowledge cards
- **Citations:** Structured references linking claims to specific card IDs
- **Confidence metadata:**
  - Per-citation confidence (1-5) from each source card's frontmatter `confidence` field
  - Overall aggregate confidence (min/mean/weighted across all cited cards)
  - Inline hedging: claims from low-confidence cards (≤ 2) are explicitly noted (e.g., "A speculative source suggests...")

## Procedure

### Step 1: Understand the Request

Clarify with the user if needed:
- **Topic:** What should the draft cover?
- **Format:** Briefing paper, essay, summary, report, annotated bibliography?
- **Audience:** Expert, general, internal notes?
- **Length:** Executive summary, short brief, or comprehensive?
- **Confidence floor:** Include speculative cards or only established knowledge? (default: confidence ≥ 2)

### Step 2: Acquire Card Knowledge via CLI

Replace inline `Read cards/*.md` with CLI commands:

If the user has a specific question:
```
construct ask domain --domain "<domain>" --question "<question>" --json
```

This returns structured JSON with answer, citations, and confidence metadata. Store the JSON output for reference.

If no specific question (open-ended synthesis), use:
```
construct knowledge card list --domain <domain> --json
```
to enumerate all cards in a domain, then Read the most promising ones individually.

Also check `refs/` for supporting references via:
```
construct knowledge ref list --domain <domain> --json
```

### Step 3: Assess Knowledge Strength

Before drafting, audit the source material:

```
Source Material Assessment:
- Cards available: {N}
- Confidence distribution: {breakdown}
- Source tier distribution: {breakdown}
- Gaps identified: {list any weak areas}
```

If significant gaps exist, inform the user:
> "The knowledge base has limited coverage on {topic area} — only {N} cards at confidence {N}. The draft will flag these sections. Want me to research these gaps first?"

### Step 4: Analyze Confidence Metadata

For each cited card in the ask.domain output, extract the per-citation `confidence` field. Compute aggregate confidence:
- **Min confidence:** The lowest confidence among cited cards
- **Mean confidence:** Average of all cited card confidences
- **Weighted confidence:** Weighted by relevance (heuristic: cards with more body text matching the question get higher weight)

Document these in the synthesis draft metadata.

### Step 5: Draft Synthesis with Inline Confidence Annotation

Using the retrieved card content and confidence metadata, draft the synthesis. Apply these rules:
- Claims from cards with `confidence >= 4`: State directly ("Research shows that...")
- Claims from cards with `confidence == 3`: Use neutral framing ("Current understanding suggests...")
- Claims from cards with `confidence <= 2`: Use explicit hedging ("A speculative source notes..." / "An early-stage finding proposes...")
- Every claim must cite its source card ID parenthetically: "(source: card-xyz-123)"
- If no cards are relevant, state: "The workspace does not contain information about this topic."
- **Cross-domain connections** — highlight when insights cross domain boundaries

End with a structured metadata section:
```markdown
### Synthesis Metadata
- **Cards cited:** {count}
- **Confidence range:** {min} – {max} (per-card confidence)
- **Aggregate confidence:** {mean:.1f} mean | {weighted:.1f} weighted
- **Gate:** ask.domain (L2)
- **Workspace:** {path}
```

### Step 6: Review Prompt

Present the draft to the user:
> "Draft ready.
> - Based on {N} cards across {N} domains
> - Confidence range: {min} – {max}
> - Aggregate confidence: {mean} mean | {weighted} weighted
>
> Would you like to: review and edit, strengthen thin sections (I'll research), or finalize?"

### Step 7: Views Refresh Hook

If `views/build/` exists at the install root AND `.construct/config.yaml` does not set `views.auto_regenerate: false`:

**Skip check:** If this skill was invoked as part of `daily-cycle` or another parent workflow that runs multiple hooked skills in sequence, skip this hook — the parent will trigger a single regeneration after all child skills complete. This avoids redundant regeneration.

If not skipped:
1. Run `views-generate-data` to refresh the SPA's cached JSON
2. If it succeeds → if `.construct/config.yaml` sets `views.confirm_refresh: true`, append to the report: `✓ views updated (build_id: {id})`. Otherwise, no extra user-facing message (the SPA picks it up via `version.json` polling within 30s).
3. If it fails → append a warning to the report:
   > ⚠ views regeneration failed: {single-line message}. Workspace is intact; run `views-generate-data` manually to refresh the views.
4. Always preserve this skill's success status — the hook is a side effect, not a success condition

If `views/build/` does not exist, or `views.auto_regenerate` is `false` → skip silently (no log, no message).

---

## Error Handling

| Error | Cause | Handling |
|-------|-------|----------|
| `construct ask domain` returns no answer | No relevant cards found for the question | Report to user: "Workspace lacks relevant cards." Consider broadening the question or domain. |
| `construct knowledge card list` fails | CLI not available or workspace path wrong | Check workspace path. Fall back to Read cards/*.md for enumeration. |
| Cards cited with confidence < 3 | Source material is speculative or early-stage | Follow hedging rules in Step 5. Never present low-confidence claims as established fact. |
| API key missing for ask.domain | ANTHROPIC_API_KEY not set in environment | Report to user: "LLM gate unavailable. Falling back to card content review." Proceed with manual card review using Read. |

---

## Validation

- [ ] Every claim in the draft traces to at least one source card
- [ ] Confidence propagation is accurate (per-citation + aggregate)
- [ ] Inline hedging applied correctly for each confidence tier (>= 4 direct, == 3 neutral, <= 2 hedge)
- [ ] Gaps are explicitly flagged, not covered up
- [ ] Synthesis Metadata section included with confidence range and aggregate
- [ ] Cards acquired using `construct ask domain` or `construct knowledge card list` CLI commands
