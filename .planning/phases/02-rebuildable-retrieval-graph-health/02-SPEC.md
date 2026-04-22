# Phase 2: Rebuildable Retrieval & Graph Health — Specification

**Created:** 2026-04-22
**Ambiguity score:** 0.10 (gate: <= 0.20)
**Requirements:** 4 locked

## Goal

CONSTRUCT rebuilds a disposable SQLite + FTS5 index, NetworkX-backed graph state, and graph-health signals from the canonical markdown + YAML workspace, producing file artifacts in `db/` that downstream phases read to expose search and graph inspection to end users.

## Background

Phase 1 shipped the canonical workspace foundation: a Typer CLI (`construct init|validate|status`), Pydantic schemas (`KnowledgeCard`, `ConnectionRecord`, `ConnectionsFile`, `WorkspaceScaffold`), and a `WorkspaceLoader` that reads cards, `connections.json`, and config YAML from disk. The `db/` directory is reserved in the workspace scaffold and gitignored as rebuildable derived state. Zero references to `sqlite`, `fts5`, or `networkx` exist under `src/construct/` today.

Phase 2 builds the rebuildable derived layer without introducing any user-facing query surface — search and graph inspection are invoked by downstream phases (Phase 3 REPL, Phase 5 browser UI). Phase 2 also defines the `refs/` schema, which Phase 1 reserved as a canonical directory but did not formalize.

CARD-02 (seed intake) was originally mapped to Phase 2 but is remapped to Phase 3 in the same session as this spec — seed intake requires the NL/agent surface that lands in Phase 3.

## Requirements

1. **Reference file schema and validation**: The workspace schema must define canonical reference entries so Phase 2 can index them uniformly with cards.
   - Current: `WorkspaceScaffold` reserves `refs/` as a canonical directory, but no `RefRecord` (or equivalent) Pydantic model exists in `src/construct/schemas/`. References are unindexable today.
   - Target: A canonical reference schema exists and validates ref files in `refs/`; malformed ref files surface clear validation errors matching Phase 1's card-validation pattern.
   - Acceptance: A fixture `refs/*.md` file validates against the new schema, a malformed ref file reports a specific error, and `construct validate` from Phase 1 extends to ref files without regressing card validation.

2. **Rebuildable SQLite + FTS5 index (INDX-01)**: The system must rebuild a SQLite + FTS5 index from canonical cards and refs after `db/` is deleted.
   - Current: No SQLite code, no FTS5 schema, no index build pipeline. `db/` is an empty reserved directory.
   - Target: A rebuild entry point (function or command) reads the canonical workspace, populates `db/index.sqlite` with structured card + ref tables plus an FTS5 virtual table, and is deterministic across repeat runs against the same SOT.
   - Acceptance: After `rm -rf db/` against a seeded fixture workspace, invoking the rebuild entry point produces a `db/index.sqlite` whose contents match fixture expectations. Two consecutive rebuilds against unchanged SOT produce semantically equivalent output (row counts + indexed-field hashes match).

3. **Programmatic full-text retrieval (INDX-02, Phase-2 scope)**: The rebuilt FTS5 index must return accurate full-text matches over both cards and refs via programmatic SQL queries.
   - Current: No index, no retrieval path.
   - Target: The FTS5 index supports full-text queries joining card and ref content with rank ordering; a Python retrieval helper runs a query string against the index and returns matching card and ref records.
   - Acceptance: Given a fixture corpus of cards and refs, a programmatic query against the built FTS5 index returns expected matches with rank ordering verified by test fixtures. The user-facing search surface is explicitly deferred to Phase 3 (REPL) — no CLI search command ships in Phase 2.

4. **Derived graph artifacts with faithful connection semantics (GRAPH-01, GRAPH-02)**: The rebuild must emit file artifacts in `db/` capturing graph state, metrics, and health signals that faithfully represent canonical connection semantics including typed parallel edges.
   - Current: No graph code. `connections.json` permits `(from, to, type)` triples with distinct types between the same ordered pair, but no derivation exists.
   - Target: The rebuild pipeline derives a NetworkX graph from cards + `connections.json`, writes `db/graph.json` (serialized graph), `db/graph-stats.json` (size, components, connectivity metrics), and `db/graph-health.json` (orphan cards, stale cards, bridge nodes). Differently-typed connections between the same ordered pair are preserved and distinguishable in the serialized graph artifact.
   - Acceptance: Against a fixture workspace where card A both `extends` and `contradicts` card B, `db/graph.json` contains both typed edges distinguishable by type. `db/graph-stats.json` reports accurate size, component count, and connectivity for the fixture. `db/graph-health.json` surfaces a known orphan card, a stale card (past a configured threshold), and a known bridge node under documented rules.

## Boundaries

**In scope:**
- Canonical reference schema and validation (extends Phase 1 `construct validate`)
- SQLite + FTS5 index build pipeline from cards and refs in the canonical workspace
- NetworkX-backed graph derivation with typed-parallel-edge preservation
- Serialized graph artifacts in `db/`: `graph.json`, `graph-stats.json`, `graph-health.json`, and `index.sqlite`
- A graph-semantics spike as the first-wave task inside Phase 2: resolves MultiDiGraph vs DiGraph and produces a decision artifact before downstream graph tasks begin

**Out of scope:**
- User-facing CLI commands for search or graph inspection — deferred to Phase 3 REPL
- Incremental or partial index updates — rebuild is the sole mutation path in Phase 2
- Seed intake (CARD-02) — remapped to Phase 3 in this session
- Browser UI for graph or search — deferred to Phase 5
- Remote fetching of reference content — references are local files only
- Semantic search or embeddings — explicitly excluded from v0.1
- Automatic remediation of graph health issues (e.g., auto-archive of stale cards) — violates PROJECT.md's governed-writes principle

## Constraints

- SQLite with FTS5 is the only full-text retrieval layer. No embeddings, no alternative search engines.
- NetworkX is the graph engine. Graph objects remain in-memory; `db/graph.json` is the serialized snapshot.
- Rebuild is the sole mutation path for `db/`. Incremental-update code paths are not permitted in Phase 2.
- Rebuild must be deterministic: two rebuilds against unchanged SOT produce equivalent output under documented equivalence rules.
- Typed parallel edges between the same `(from, to)` ordered pair must be preserved end-to-end (canonical → graph → serialized artifact).
- `db/` is strictly output. No code path outside the retrieval helper may read `db/` as business truth.
- Ref files live under `refs/` and validate against the Requirement-1 schema before indexing.

## Acceptance Criteria

- [ ] A reference-record Pydantic schema exists and validates fixture ref files.
- [ ] `construct validate` reports schema errors on malformed ref files without regressing card validation.
- [ ] Deleting `db/` and running the rebuild entry point recreates `db/index.sqlite` against a fixture workspace.
- [ ] Two consecutive rebuilds against unchanged SOT produce semantically equivalent `db/index.sqlite` (by row count + indexed-field hash).
- [ ] A programmatic FTS5 query against the built index returns expected matches over a cards + refs fixture corpus.
- [ ] A graph-semantics spike artifact documents the MultiDiGraph vs DiGraph decision with test cases for typed parallel edges.
- [ ] `db/graph.json` preserves differently-typed edges between the same `(from, to)` pair distinguishably.
- [ ] `db/graph-stats.json` reports size, component count, and connectivity for a fixture workspace matching expected values.
- [ ] `db/graph-health.json` surfaces known orphan, stale, and bridge nodes from a fixture workspace under documented rules.
- [ ] No user-facing CLI search or graph commands ship in Phase 2.
- [ ] No incremental-update code paths exist for `db/` in Phase 2.

## Ambiguity Report

| Dimension           | Score | Min   | Status | Notes |
|---------------------|-------|-------|--------|-------|
| Goal Clarity        | 0.93  | 0.75  | ✓      | Deliverable is rebuildable derived state in `db/`; user-facing surfaces deferred explicitly |
| Boundary Clarity    | 0.95  | 0.70  | ✓      | CARD-02 remapped; incremental fully excluded; refs in scope; spike as first task inside phase |
| Constraint Clarity  | 0.85  | 0.65  | ✓      | SQLite+FTS5 + NetworkX locked; rebuild-only; typed parallel edges preserved end-to-end |
| Acceptance Criteria | 0.85  | 0.70  | ✓      | All criteria testable via fixtures and programmatic queries |
| **Ambiguity**       | 0.10  | <=0.20| ✓      | Gate passed |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 1 | Researcher | CARD-02 in Phase 2 without agents? Inspection surface without REPL/UI? Graph model for typed parallel edges? | Defer CARD-02 to Phase 3; artifact-only inspection via files in `db/`; spike before locking MultiDiGraph vs DiGraph |
| 2 | Researcher + Simplifier | Remap CARD-02 now or flag only? INDX-02 usability? Rebuild vs incremental? | Remap CARD-02 to Phase 3 now; defer INDX-02 user-facing search to Phase 3; incremental allowed only if rebuild parity preserved (superseded by Round 3 Q7a) |
| 3 | Boundary Keeper | Incremental fully in or out? Spike location? `refs/` scope and schema? | Rebuild-only, incremental fully excluded from Phase 2; spike as first-wave task inside Phase 2; structured ref files with schema defined in this phase |

---

*Phase: 02-rebuildable-retrieval-graph-health*
*Spec created: 2026-04-22*
*Next step: /gsd-discuss-phase 2 — implementation decisions (how to build what's specified above)*
