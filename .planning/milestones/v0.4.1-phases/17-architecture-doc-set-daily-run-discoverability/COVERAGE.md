# Phase 17 — API Coverage Matrix

**Decided:** 2026-07-25 (planner)
**Detector result:** `detected: true` — but on CONSTRUCT's OWN internal MCP invoke-surface, not an external third-party API.

## Why the detector fired (and why this is not an external integration)

The `api-coverage.cjs` detector matched two `mcp` signals in the phase scope:

1. `adopts mcp` — from documenting ADR-0003's runtime layer model where the **invoke surface** is `CLI → MCP → HTTP` (Layer 3). This is CONSTRUCT describing its *own* architecture, not integrating an outside service.
2. `connect mcp` — the new `construct-daily-cycle` skill's `allowed-tools: … MCP(connect)` grant, which lets the skill reach CONSTRUCT's *own local* `construct mcp` stdio server to invoke the `construct_daily_run` tool — the same capability it can reach over the CLI.

**This phase integrates NO external API, SDK, or third-party service.** It edits Markdown docs, adds one pytest contract guard, and adds one thin skill that delegates to the already-shipped `daily.run` capability. There are no new package installs, no network egress added, no credentials.

## Decided matrix — the internal `daily.run` surface the new skill wraps (UX-01)

The only "API surface" this phase touches is CONSTRUCT's own `daily.*` capability group, reached by the daily skill via CLI/MCP. The MCP tool list is auto-discovered from the registry (22 tools); coverage of the *daily group* by the new skill:

| Capability (internal) | Surface | Disposition | Reason |
|-----------------------|---------|-------------|--------|
| `daily.run` (`construct daily run` / `construct_daily_run`) | CLI + MCP | **INTEGRATE** | The skill's core action — invokes it with `--workspace . --json`. |
| `daily.inspect` (`construct daily inspect`) | CLI | OPT-OUT | Reads a *persisted* receipt; the skill runs a fresh cycle. A read-only inspection path is a separate concern, not part of the "run the daily cycle" entry point (D-08). |
| `research.review` (`construct research review`) | CLI | INTEGRATE (reference) | The skill points the user here for interactive handling of escalations (D-08 step 5). |
| `curation.review` (`construct curation review`) | CLI | INTEGRATE (reference) | Same — escalation handoff (D-08 step 5). |

No external-API coverage matrix applies. This file exists to record the decided disposition and satisfy the `api-coverage.verify-pre` gate; there is nothing external to opt into or out of.
