# CONSTRUCT03 — Planning

## Purpose

CONSTRUCT03 shifts CONSTRUCT from **chat-as-primary-interface** to **UI-as-primary-interface**. Users invoke actions through a solid, structured UI. LLM involvement is reserved for steps that require editorial judgment, ambiguity resolution, or synthesis quality — not for navigation, status, or deterministic operations.

## Master artifact inventory

All skills, agents, workflows, and the CONSTRUCT03 audit framework live in one place:

**[`CONSTRUCT-CLAUDE-spec/artifact-catalog.md`](../CONSTRUCT-CLAUDE-spec/artifact-catalog.md)**

That document is the canonical master. Use it to:

- inventory every Claude-native implementation artifact
- classify each as `UI` · `PIPE` · `LLM` · `HYB` (current vs target)
- plan which chat flows become buttons, wizards, pipelines, or review modals
- track audit progress skill-by-skill

## Related inputs

| Document | Role |
|----------|------|
| [`artifact-catalog.md`](../CONSTRUCT-CLAUDE-spec/artifact-catalog.md) | Master inventory + audit matrix |
| [`commands.md`](../CONSTRUCT-CLAUDE-impl/construct/references/commands.md) | Current user command quick-ref |
| [`user-journeys.md`](../CONSTRUCT-CLAUDE-spec/user-journeys.md) | J1–J3 reference journeys (to be re-mapped to UI) |
| [`prd-v02-cross-domain-cluster.md`](../CONSTRUCT-CLAUDE-spec/prd-v02-cross-domain-cluster.md) | In-flight v0.2.x work — coordinate with C03 UI plans |

## Working rule

When a planning decision conflicts with `artifact-catalog.md` inventory counts or skill names, update the catalog first, then downstream docs.

## Next steps

1. Review each skill's `C03 target` column in the artifact catalog — confirm or revise.
2. Draft CONSTRUCT03 PRD: UI shell, action model, pipeline runtime, LLM grounding gates.
3. Produce per-skill migration notes (`UI` affordance → API → pipeline steps → LLM gates).
