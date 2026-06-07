# Phase 3: Runtime & Command Surface — Specification

**Created:** 2026-04-22
**Ambiguity score:** 0.09 (gate: <= 0.20)
**Requirements:** 7 locked

## Goal

CONSTRUCT provides a local terminal chat REPL that starts the runtime session, accepts natural-language user intents for domain setup and inspection tasks, asks only for missing information, shows a structured confirmation summary before canonical writes, and resumes pending clarification safely after interruption.

## Background

The codebase today contains only Phase 1 workspace tooling: a Typer CLI with `construct init`, `construct validate`, and `construct status`, plus shared services for workspace initialization and validation. The current input model is low-level and fielded: `src/construct/cli.py` prompts directly for values like taxonomy seeds, source priorities, and research seeds, including comma-separated entry for list fields. There is no runtime session model, no orchestrator/curator/researcher lifecycle, no REPL, no chat handler, no event stream with IDs, and no recovery flow for interrupted conversations. Phase 3 is triggered by this gap between the intended product interaction model in the specs and the current bootstrap-only CLI.

Phase 3 also widens the NL-first interaction model to cover workspace bootstrap itself. `construct init` (Phase 1, structured field prompts) remains the deterministic fallback path, while the REPL adds a natural-language bootstrap flow that captures the same canonical inputs (slug, display name, scope, taxonomy seeds, source priorities, research seeds) through clarification instead of fielded entry.

## Requirements

1. **Terminal REPL runtime entrypoint**: Phase 3 must add a terminal chat REPL that is the primary user-facing local interface for this phase.
   - Current: The only interface is a one-shot Typer CLI with `init`, `validate`, and `status`; no conversational runtime surface exists.
   - Target: A terminal REPL command starts the local runtime session, owns that session lifecycle while open, and shuts it down cleanly on exit.
   - Acceptance: Starting the REPL creates runtime state for a local session, exiting the REPL stops it without leaving canonical files in a partial state, and the REPL can be launched repeatedly in a clean way.

2. **Natural-language-first intent handling**: The REPL must accept natural-language user requests as the primary interaction style, with structured input retained only as a fallback.
   - Current: The CLI expects direct field entry and comma-separated lists for some inputs; no natural-language interpretation layer exists.
   - Target: Users can express intents like domain setup, status questions, and gap checks in plain language; the system parses that intent and only falls back to structured entry when needed for correction or expert use.
   - Acceptance: A user can make at least one domain-setup request, one status/inspection request, and one gap-check request in natural language without being forced into field-by-field entry as the default path.

3. **Clarification loop for missing information**: The REPL must gather missing or ambiguous details through multi-turn follow-up questions instead of demanding all fields up front.
   - Current: `construct init` always asks for the full field set in a fixed sequence regardless of how much the user already provided.
   - Target: For supported write flows, the REPL begins from the user’s freeform request, detects what information is missing or ambiguous, and asks only those follow-up questions step by step.
   - Acceptance: For a partially specified domain-setup request, the REPL asks follow-up questions only for fields not already derivable from the user input and does not re-ask already supplied values.

4. **Structured confirmation before canonical writes**: Any REPL action that mutates canonical workspace state must show a structured summary and require explicit confirmation before writing.
   - Current: `construct init` writes canonical domain files immediately after prompt collection, with no explicit pre-write confirmation summary.
   - Target: Before creating or updating canonical files through the REPL, CONSTRUCT presents a plain-language summary plus the structured fields it intends to write, then waits for explicit user approval.
   - Acceptance: A write-capable REPL flow does not modify canonical files until the user confirms the displayed summary, and declining confirmation leaves canonical files unchanged.

5. **Auditable runtime visibility and routing**: The REPL must expose runtime/inspection results in a human-readable form while preserving auditable event references and configured model routing behavior.
   - Current: There is no runtime event model, no event IDs, and no runtime command surface that shows how inspection requests are handled.
   - Target: The runtime produces referenceable event or interaction IDs, inspection/status replies are human-readable in the terminal, and requests route through the configured model-tier rules rather than hardcoded prompt paths.
   - Acceptance: At least one status/inspection action in the REPL returns a human-readable result that includes a referenceable event or interaction ID, and the handling path can be traced to configured routing rather than an inline-only implementation.

6. **Safe interruption recovery for pending clarification**: The runtime must resume pending clarification safely after interruption without requiring full conversation-history restoration.
   - Current: No runtime session exists, so interruption recovery for an in-progress interaction is impossible.
   - Target: If the REPL is interrupted while waiting on a clarification or confirmation needed to finish a supported action, the next REPL start can restore that pending step and continue safely.
   - Acceptance: Interrupting a REPL flow during a pending clarification or confirmation, then restarting the REPL, restores the pending step without corrupting canonical state or requiring the user to restart from scratch.

7. **Natural-language workspace bootstrap**: The REPL must support bootstrapping a new workspace through the same NL + clarification + structured-confirmation flow used for other intents, with `construct init` retained as the structured fallback.
   - Current: Workspace bootstrap is only available through `construct init`, which prompts field-by-field (including comma-separated list entry) and writes canonical files immediately after collection.
   - Target: A user can initiate workspace creation from the REPL using a natural-language request (e.g., "set up a new workspace for my research on X"), the system derives what it can from the request, asks only for missing or ambiguous canonical inputs (slug, display name, scope, taxonomy seeds, source priorities, research seeds), shows a structured summary, and writes the workspace only after explicit confirmation.
   - Acceptance: A user can create a new workspace end-to-end from the REPL without being forced into field-by-field entry; the resulting workspace is schema-valid and indistinguishable from one produced by `construct init`; declining the pre-write confirmation leaves the target path unchanged; `construct init` continues to work unchanged as the structured fallback.

## Boundaries

**In scope:**
- A terminal chat REPL as the primary Phase 3 user-facing interface
- Runtime session start/stop behavior owned by the REPL
- Natural-language-first handling for workspace bootstrap, domain setup, status/inspection, and gap-check interactions
- Step-by-step clarification for missing or ambiguous fields only
- Plain-language plus structured pre-write confirmation summaries
- Human-readable runtime replies with referenceable event or interaction IDs
- Safe resume of pending clarification/confirmation after interruption
- Structured input as a fallback or advanced-mode path only, with `construct init` preserved as the structured workspace-bootstrap fallback

**Out of scope:**
- Browser-based chat UI — browser interaction belongs to Phase 5
- Background research execution — real research workflows belong to Phase 4
- Reference ingestion through chat — that workflow belongs to Phase 4
- Long-running task dashboard or rich monitoring views — activity dashboards belong to Phase 5
- Full conversation-history restoration — Phase 3 only requires restoring pending clarification state
- Silent auto-writes from interpreted user intent — excluded because write actions must remain auditable and confirmed

## Constraints

- The Phase 3 user-facing surface must be terminal-first; browser chat is excluded even if a server layer is introduced underneath.
- Runtime capabilities must remain available as Python callables outside REPL-specific code so later chat/UI/MCP surfaces do not fork business logic.
- Canonical workspace state remains markdown/YAML-first; runtime and recovery state must not become a second source of truth.
- Any canonical mutation triggered from the REPL must require explicit confirmation after a structured summary.
- Recovery scope is limited to pending clarification or confirmation, not full long-term conversational memory.
- Human-readable replies may hide raw schema details by default, but the confirmation surface must still expose the structured fields that will be written.

## Acceptance Criteria

- [ ] A terminal REPL command exists and starts a local runtime session when launched.
- [ ] Exiting the REPL stops the runtime cleanly without leaving partial canonical writes.
- [ ] Supported natural-language requests include workspace bootstrap, domain setup, status/inspection, and gap checks.
- [ ] The REPL asks only for missing or ambiguous fields during a write-capable flow.
- [ ] Before any canonical write, the REPL shows a plain-language summary plus structured fields and waits for explicit confirmation.
- [ ] Declining confirmation leaves canonical files unchanged.
- [ ] At least one inspection/status response includes a referenceable event or interaction ID.
- [ ] Interrupting a pending clarification or confirmation can be resumed safely on the next REPL start.
- [ ] A user can create a schema-valid workspace end-to-end through the REPL NL bootstrap flow without field-by-field entry, and `construct init` still works unchanged as the structured fallback.

## Ambiguity Report

| Dimension           | Score | Min   | Status | Notes |
|---------------------|-------|-------|--------|-------|
| Goal Clarity        | 0.95  | 0.75  | ✓      | Terminal REPL deliverable and supported intent types are explicit |
| Boundary Clarity    | 0.94  | 0.70  | ✓      | Browser chat, Phase 4 workflows, and dashboard work explicitly excluded |
| Constraint Clarity  | 0.83  | 0.65  | ✓      | Runtime ownership, confirmation rule, service-layer rule, and recovery scope locked |
| Acceptance Criteria | 0.90  | 0.70  | ✓      | Eight pass/fail checks cover the required behaviors |
| **Ambiguity**       | 0.09  | <=0.20| ✓      | Gate passed |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective      | Question summary | Decision locked |
|-------|------------------|------------------|-----------------|
| 1 | Researcher | What is the primary user-facing deliverable, what intents must it handle, and when must writes be confirmed? | Phase 3 delivers a terminal chat REPL; it must handle domain setup, status/inspection, and gap checks; all canonical writes require explicit confirmation |
| 2 | Researcher + Simplifier | What is the minimum acceptable REPL, what stays out of scope, and what must be visible before confirmation? | Multi-turn clarification is the minimum acceptable REPL; background research, reference ingestion, and dashboards stay out of scope; pre-write confirmation shows a plain summary plus structured fields |
| 3 | Boundary Keeper | Is browser chat excluded, and does domain setup stop at proposal or actually write after confirmation? | Browser chat is excluded from Phase 3; write-capable flows must confirm and then apply canonical updates |
| 4 | Seed Closer | How does the REPL relate to runtime lifecycle, what recovery is required, and how visible must auditability be? | The REPL starts and owns the runtime session; pending clarification must be resumable after interruption; runtime replies need status plus event/interaction IDs |

---

*Phase: 03-runtime-command-surface*
*Spec created: 2026-04-22*
*Next step: /gsd-discuss-phase 3 — implementation decisions (how to build what's specified above)*
