---
id: SEED-002
status: dormant
planted: 2026-07-26
planted_during: v0.4.1 shipped — awaiting v0.5 scoping
trigger_when: when ingestion capability is next scoped (v0.6 candidate) — NOT gated on UI work
scope: medium
---

# SEED-002: Evaluate graphify (graphify.net) as a third-party content-ingestion component

Site: https://graphify.net

## Why This Matters

Promising third-party ingestion could shortcut work CONSTRUCT currently does itself. But note
this is **not a UI topic** — it belongs to the ingestion path, so it should not be gated behind
v0.5 UI scoping (see When to Surface).

There is a naming collision worth resolving early: CONSTRUCT **already ships a spike type called
`graphify`**, but it is explicitly *"Graphify-**style** ingestion analysis"* — a local
placeholder contract, not the graphify.net product. Confirm which is which before comparing.

## When to Surface

**Trigger:** when ingestion capability is next scoped — a v0.6 candidate.

Deliberately *decoupled* from the UI trigger on [[SEED-001]]. This is an ingestion/third-party
question; holding it behind UI work would delay it for no reason. If v0.5 turns out to touch
ingestion, surface it there instead.

## Scope Estimate

**Medium** — the evaluation harness already exists (below), so the build is cheap. The cost is in
the governance and egress questions, which are real design work, not spike work.

## Breadcrumbs

**The evaluation harness already exists — reuse it, don't build one.**

`src/construct/pipelines/spike_runner.py:54-62` registers:

```python
"graphify": SpikeDefinition(
    name="graphify",
    description="Graphify-style ingestion analysis — extract candidate tags and keywords from refs",
    command_template="{tool_path} {workspace_copy}",
    expected_output_paths=["candidates.json", "tags.json"],
)
```

This is a **generic external-binary harness**: it copies the workspace to an isolated temp copy
(skipping `views`/`digests`/`publish`), runs an arbitrary tool via `--tool-path`, enforces a 300s
default timeout, and persists results — without touching canonical truth. Invoke as
`construct spike run graphify --tool-path <binary>`. If graphify.net ships a CLI or API client,
this is the sandbox to evaluate it in, and `infranodus` is the sibling precedent.

Caveat: the `spike` command group is one of the RT-01/RT-02 **registry-bypass** groups — it
reaches its handlers by an independent path rather than through the capability registry
(`.planning/STATE.md` Deferred Items; `PROJECT.md:103`).

**Governance invariants a third-party ingester must not break:**

1. **Pre-write validation gates.** Cards/refs/connections are validated before persistence
   (Phase 1). The standing decision is *"fix validation by conforming the data to the gate, not
   weakening the gate"* (`PROJECT.md` Key Decisions, ING-02). A third-party feed conforms to
   CONSTRUCT's schema, not the reverse.
2. **Propose-then-reviewed-apply.** `research.run` writes nothing before human approval — no
   canonical-write node exists upstream of the `interrupt()`. Auto-ingesting third-party output
   would breach the invariant that makes the graph trustworthy.
3. **Existing ingest path** is `construct ingest source` → ref/seed card creation (Phase 04), with
   reserved manual-ingest/web-ingest clusters seeded to satisfy the validation gate (Phase 07,
   ING-02). A new ingester needs its own cluster or must reuse these.
4. **Card frontmatter contract.** Any writer must emit `lifecycle:` — the writer/parser fork that
   silently dropped CLI-created cards from `views generate` was only closed on 2026-07-26 (quick
   task `260726-m0e`, commit `ac45d0e`), and the fix is **writer-side with no backfill**. A new
   writer that omits it reintroduces the bug.

**Egress / NFR impact:**

Tavily is currently the *only* third-party API, and getting that right took a correction in
Phase 14 — `nfrs.md` §4 previously claimed "Third-party APIs: None". Adding graphify.net makes a
second egress point and requires an `nfrs.md` update plus a `default_provider` story, against a
local-first product constraint (`PROJECT.md` Constraints).

## Notes

Prior evaluation context: `.planning/milestones/v0.3-phases/06-derived-data-ops-ui-governed-spikes/06-CONTEXT.md:31`
(D-06 — per-spike SKILL.md docs for Graphify and InfraNodus describing how to run and interpret results).
