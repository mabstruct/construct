---
description: "Evaluate cards for lifecycle promotion or decay by delegating to the Python L3 promotion gate. Use when user says 'evaluate cards', 'check promotions', or during curation cycle."
allowed-tools: Read, Bash(construct), MCP(connect)
---
# Skill: Evaluate Card for Promotion

**Trigger:** User says "evaluate cards", "check promotions", or during a curation cycle's promotion step.
**Agent:** Curator
**Produces:** A set of `PromotionDecision`s (promote / hold / escalate) proposed by the Python gate — presented for review, not written directly by this skill.

---

> **Migrated for Phase 12 (API-04, D-09):** The promotion-threshold ruleset and the ambiguous-card LLM rubric that used to live in this skill's prose are now the Python `card.evaluate` L3 gate (`src/construct/llm/curation_promote.py`). That gate is the **single source of promotion judgment** — this skill no longer carries a duplicate, unguarded judgment path that could drift from the tested gate. This skill is a **thin wrapper**: it invokes `construct card evaluate` and presents the gate's `PromotionDecision` output. The skill drives the conversation; Python owns the judgment.

## Prerequisites

The CLI must be available on `$PATH`. For MCP-based operation, start the server:

```bash
construct mcp &
```

## Procedure

### Step 1: Invoke the Promotion Gate

**INPUT:** Workspace on disk
**OUTPUT:** One `PromotionDecision` per non-mature card (read-only — no writes)
**METHOD:** CLI `construct card evaluate` (the single source of promotion judgment)

Run the gate against the workspace:

```bash
construct card evaluate --workspace . --json
```

Add `--provider <name>` only if the user asked to override the default provider.

**Alternative (MCP):** invoke the `construct_card_evaluate` tool with `{"workspace_path": "."}`.

The gate deterministically pre-filters candidates (non-mature, non-archived cards), applies the governance thresholds and the LLM judgment for borderline cards, and returns a `PromotionDecision` per candidate. It is **read-only**: it proposes, it does not write. There is no inline threshold logic or rubric in this skill — do not re-derive the decision.

### Step 2: Present the Decisions

**INPUT:** The `PromotionDecision` list from Step 1
**OUTPUT:** A clear, reviewable summary for the user

Each decision carries `card_id`, `decision` (`promote` | `hold` | `escalate`), an optional `target_lifecycle` (`growing` | `mature`), a `reasoning` string, and a `method` field. Present them grouped by decision, and **surface the `method` field** so the user can tell escalation types apart:

- `method: rule-based` → a **failure-driven** escalation: the gate's LLM evaluation failed and retried out, so the card was mechanically escalated. This is not a judgment call — it means "the evaluator could not run cleanly," and typically warrants a re-run rather than human deliberation.
- `method: llm-judgment` → a **genuine borderline** decision the model reasoned about. The `reasoning` explains the call; this is the case that actually wants human attention.

> "Promotion scan complete:
> - {N} promote ({seed→growing}: {N}, {growing→mature}: {N})
> - {N} hold — not ready
> - {N} escalate — {X} borderline (llm-judgment), {Y} evaluation failures (rule-based; consider re-running)"

### Step 3: Apply (when part of a curation run)

This skill only **evaluates**. It does not write lifecycle changes on its own.

- When invoked inside a curation cycle, the promotion proposals flow into the consolidated `curation.run` gate queue, and the approved writes are applied by `construct curation review` behind the human gate. Do not promote cards directly from here.
- When invoked standalone at the user's request, present the decisions and let the user drive the curation cycle to apply any approved promotions. Escalations are review-only — surface them for the user's judgment.

---

## Validation

- [ ] `construct card evaluate` invoked (no inline promotion thresholds or rubric in this skill)
- [ ] `PromotionDecision`s presented grouped by decision, with `reasoning` shown
- [ ] `method` field surfaced so rule-based (failure-driven) escalations read distinctly from llm-judgment (borderline) ones
- [ ] No direct lifecycle writes performed by this skill — writes flow through the reviewed curation path
