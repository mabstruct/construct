# Phase 3: Runtime & Command Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 3-Runtime & Command Surface
**Areas discussed:** Input Style, Clarification Behavior

---

## Input Style

| Option | Description | Selected |
|--------|-------------|----------|
| Natural language only | Users always express intent conversationally and the system never exposes a structured fallback. | |
| Natural language first, structured fallback | Users can speak naturally, while the system preserves a precise structured escape hatch when needed. | ✓ |
| Structured first, natural language secondary | Structured field entry remains the main interface and natural language is only a convenience wrapper. | |

**User's choice:** Natural language first, structured fallback
**Notes:** Comma-separated lists should not be the primary end-user UX. The system should translate user intentions into the internal schema.

---

## Clarification Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Infer silently | Parse the request and proceed without surfacing the interpreted structure unless something fails. | |
| Parse, then confirm/edit | Parse the request first and immediately show a structured interpretation for confirmation or correction. | |
| Ask follow-up questions for missing fields, then show final summary | Use natural language as the starting point, ask only for missing or ambiguous details, then present the completed structure before writing. | ✓ |

**User's choice:** Ask follow-up questions for missing fields, then show final summary
**Notes:** The conversation should not walk every field when the user already provided enough detail. Confirmation should happen through a structured summary before canonical state is written.

---

## Claude's Discretion

- Exact prompt wording.
- Exact structured fallback UX.
- Exact summary format, provided it remains auditable and easy to correct.

## Deferred Ideas

None.

---

## Scope Widening — 2026-04-22

| Question | Decision |
|----------|----------|
| Should workspace bootstrap (not just in-REPL intents) be available through the NL + clarification flow? | Yes — added as Requirement 7 in 03-SPEC.md. |
| Does `construct init` stay, or is it replaced by the NL flow? | Both coexist. `construct init` remains the deterministic structured fallback; the REPL adds the NL bootstrap path. |

**New requirement:** `WORK-04` added to `.planning/REQUIREMENTS.md` and mapped to Phase 3 in `.planning/ROADMAP.md`.

**Trigger:** User flagged that the general-scope ask for NL + AI refinement covered workspace creation, but Phase 3's original intent list was limited to domain setup, status/inspection, and gap checks — leaving initial workspace bootstrap as the only structured-only path.

---

## Workspace Bootstrap — Entry Point (D-09)

| Option | Description | Selected |
|--------|-------------|----------|
| `construct` (no args) detects missing workspace and drops into NL bootstrap | Zero-friction entry, but ambiguous — typos into `construct` with no args would trigger workspace creation. | |
| `construct chat <path>` — unified REPL command, handles bootstrap if missing | Single NL entry surface. Bootstraps when `<path>` has no workspace; resumes session when one exists. | ✓ |
| `construct init <path> --chat` | Flag-gates NL as a secondary mode of the structured command, inverting the spec's NL-first stance. | |
| `construct new <path>` | Adds a third command when the REPL is already the NL entry surface. | |

**User's choice:** `construct chat <path>`
**Notes:** The REPL is already the NL entry surface for Phase 3; making it also handle workspace bootstrap keeps entry points to one. `construct init` remains as the structured fallback.

---

## Workspace Bootstrap — Path Handling (D-10)

| Option | Description | Selected |
|--------|-------------|----------|
| Path as positional argument; NL clarification covers content only | Consistent with `construct init`, `validate`, `status`. Avoids NL parsing of filesystem paths. | ✓ |
| Path asked during clarification | More conversational, but fragile — typos, absolute vs relative, permissions. |  |

**User's choice:** Path stays a positional argument.
**Notes:** NL clarification captures canonical content (slug, display name, scope, taxonomy seeds, source priorities, research seeds). Filesystem paths stay out of the NL loop.

---

## Workspace Bootstrap — Bootstrap + First Domain Coupling (D-11)

| Option | Description | Selected |
|--------|-------------|----------|
| Single continuous NL conversation, internally composed of workspace-bootstrap + domain-setup intents | Matches `construct init` UX in one flow; internal composition keeps domain-setup intent reusable for later "add another domain" flows. | ✓ |
| Two-step: workspace first, then domain-setup as a separate follow-up intent | Conceptually cleaner separation, but more friction for the common "set up a workspace for X" case. |  |

**User's choice:** Single continuous conversation, composed internally of two intents.
**Notes:** Pre-write confirmation shows workspace-level and domain-level fields in one structured summary so the user reviews everything before any canonical write.
