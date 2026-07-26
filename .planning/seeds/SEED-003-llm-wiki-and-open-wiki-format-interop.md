---
id: SEED-003
status: dormant
planted: 2026-07-26
planted_during: v0.4.1 shipped — awaiting v0.5 scoping
trigger_when: when Wiki-view or knowledge-format/interop work is next scoped (v0.5 SPA work or v0.6)
scope: medium
---

# SEED-003: LLM-Wiki alignment and a possible open format for wiki setup

Sources:
- Karpathy LLM-Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Google `knowledge-catalog` mdcode demo: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/toolbox/mdcode/demo

## Why This Matters

**Read the existing analysis before spiking this — most of the positioning question is already
answered, and two decisions are locked.** The genuinely new part is the Google open-format angle.

Already done (2026-04-27):
- `CONSTRUCT-CLAUDE-spec/analysis-karpathi/llm_wiki_mabstruct_analysis.md` — a 566-line strategic
  analysis of LLM-Wiki and its ecosystem vs mabstruct.
- `CONSTRUCT-CLAUDE-spec/analysis-karpathi/llm-wiki.md` — the gist itself, vendored (75 lines).

Its conclusion: LLM-Wiki is a shift from query-time retrieval to **ingest-time synthesis** (raw
sources → LLM-maintained wiki → schema/agent instructions), and it is "highly relevant but
narrower" than CONSTRUCT, which already has a claim layer, typed graph, lifecycle, and
multi-agent governance.

**Locked decisions that constrain any new work here** (D5/D8 in
`CONSTRUCT-CLAUDE-spec/spec-v02-knowledge-views-spike.md`, locked 2026-05-02):
1. **The Wiki is a sibling reading view, not the workspace default.** `/:workspace` lands on the
   dashboard; the Wiki is reached deliberately.
2. **Topic-synthesis / compilation pages are NOT a Wiki responsibility.** The existing `synthesis`
   workflow plus cross-workspace `articles/` own that surface. The Wiki renders the atomic-card
   layer in reading mode only.

Karpathy's "wiki = codebase, LLM = programmer" metaphor pulls toward auto-aggregated topic pages —
which is exactly what D8 rejects. If this seed's work pushes that way, it is a **deliberate D5/D8
repositioning**, not scope creep into the Wiki view.

## When to Surface

**Trigger:** when Wiki-view or knowledge-format/interop work is next scoped.

Two plausible homes, and the format half is the more urgent:
- **v0.5** if the SPA work touches the Wiki reading view (then the positioning half is live).
- **v0.6** for the format/interop half on its own.

## Scope Estimate

**Medium** — the positioning analysis is largely done; the format question is new and lands on the
workspace contract, which is the project's hardest constraint.

## Breadcrumbs

**The new question is interop, not positioning.** The Google `mdcode` demo suggests an open format
for wiki setup — that is a *format/interop* question the April analysis does not cover, and it
collides with the project's strongest constraint:

> "Preserve the existing knowledge model and workspace format across prototype, v0.3, v0.4, and
> v0.5 — the system's continuity depends on shared semantics and files."
> — `PROJECT.md` Constraints; also listed first under Out of Scope.

So the real question to spike is narrow and answerable: **can CONSTRUCT emit/consume an open wiki
format as a projection over its existing workspace, without changing the canonical format?** That
is the same architectural shape as the existing views layer — a read-only derived projection that
never writes back to SOT — so there is a proven pattern to copy rather than a new substrate to
design.

Relevant surfaces if it becomes a projection:
- `views/` derived-data layer: 8–11 generated files, Pydantic contracts, `install_root` contract,
  `src/construct/views/` (vendored Phase 15), `views.generate_data` capability.
- **Blocker inherited from v0.4.1:** `views validate` rejects 3 of 8 files `views generate` writes.
  A new projection format should not be built on an unvalidated one — same prerequisite as
  [[SEED-001]].
- `synthesis` workflow + `articles/` own topic compilation (per D8) — the natural owner if
  LLM-Wiki-style ingest-time synthesis is adopted, *not* the Wiki view.
- `construct-synthesis` skill dropped its `WebSearch`/`WebFetch` grants in Phase 16 (DEC-01) and
  now reads refs via `Read` — relevant if wiki-style ingestion is revisited.

## Notes

Deeper compilation was already logged as "a future improvement to the synthesis workflow" when D8
was locked. That is the thread to pick up, and it is a different thread from the open-format one.
Consider splitting this into two spikes when it surfaces: `format-interop` and
`ingest-time-synthesis`.

Related: [[SEED-001]] (shares the views-validate prerequisite), [[SEED-002]] (ingest-time
synthesis overlaps the ingestion path).
