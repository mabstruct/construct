# Phase 18: Contract & Governance Foundations - Research

**Researched:** 2026-07-26
**Domain:** Python contract repair — Pydantic v2 boundary models, capability dispatch seam, LangGraph human-in-the-loop checkpoint state, audit-trail honesty
**Confidence:** HIGH (every claim below was executed against the live repository on the pinned toolchain; nothing rests on training knowledge about this codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Views byte contract (VFIX-01)**

- **D-01:** Reconcile the contract by **conforming `views/models.py` to the raw bytes the generator writes** (research option (i)), and drop the `_FILE_MODEL_MAP` / `_PER_WS_FILES` adapter tables in `generate.py:92-163` that currently make the writer validate an adapted projection and then write a different dict. The SPA already reads these bytes and existing `views/build/` copies become valid, so neither breaks. **This must be recorded as an explicit named decision**, because on its face it looks like a reversal of PROJECT.md's standing ING-02 decision ("conform the data to the gate, not weaken the gate"). It is not: ING-02 governs **canonical truth** (cards/refs), where strictness protects the knowledge model. Views is a **derived projection** whose author is the generator and whose consumer is the SPA — there the written bytes *are* the de-facto contract and the models were simply transcribed wrongly. — **Reversibility:** costly — undoing means re-introducing the adapter tables and re-breaking every existing `views/build/` copy plus the SPA components already coded against these field names.

- **D-02:** **`views validate` is promoted to a registry capability in this phase**, alongside the existing `views.generate_data` record (`catalog.py:337`). The byte fix already opens `cli.py:929` and `views/models.py`, so registration is nearly free; it closes half of RT-01/RT-02 with the smallest blast radius, retires adr-0005's explicit "registry holdout" note, and Phase 19's generated HTTP adapter then gets it for nothing. The `spike` and `tag` groups stay excluded (`spike run --tool-path` is an RCE primitive over HTTP; `tag` is unused by any v0.5 flow).

- **D-03:** The conformed models **relax from `extra="forbid"` to `extra="ignore"`**. All 13 models in `views/models.py` are `extra="forbid"` today; after conforming, they describe a floor rather than an exact byte-for-byte shape, so a parser field addition does not break `views validate` or existing builds. — **Reversibility:** reversible.

- **D-04:** Because D-03 gives up the model-level drift detector, the replacement round-trip guard is the **only** thing that can catch the next writer/reader fork, and therefore takes the strict form: **enumerate all 8 expected files by name, assert each exists, is non-empty, and validates, and assert the written-file count equals 8.** Cardinality, not set-membership — this is the WR-01 lesson from `tests/contract/test_artifact_catalog.py`, whose set-membership guard is exactly why its hand-typed prose counts can rot. The guard **replaces** `test_views_validate_does_not_yet_accept_generated_bytes` (`tests/integration/test_views_generate.py:285`); it is never deleted bare.

**Invocation seam (GOV-01)**

- **D-05:** The seam is **strict from day one** — no `_KNOWN_BROKEN`-style allowlist, no leniency mode, no per-surface exception. Every capability validates through its `input_model` on both CLI and MCP immediately. Anything the 515-test suite surfaces as non-conforming was already calling a capability wrongly and is fixed inside this phase rather than recorded as an exception. — **Reversibility:** costly — a later relaxation would have to be applied per capability across both surfaces, and the differential test would have to encode the relaxation as expected behaviour, which is the parity fork GOV-01 exists to close.

- **D-06:** `extra="forbid"` is applied **by default across all 28 capability input models** (today only `CardListInput` carries it, `catalog.py:145-147`, added as an ASVS boundary control and currently inert over MCP — code-review item WR-02). Any capability that genuinely needs an open payload expresses it as a **typed dict field**, never by relaxing the whole model. Research sizes the 28-model audit before planning commits.

- **D-07:** The seam calls the handler as **`handler(**model.model_dump())`** — identical to what `mcp/server.py:33` already does, so MCP handlers need no signature change and the seam is a pure insertion there. The work is normalizing `cli.py`'s three positional call sites (`:89`, `:107`, `:143`) and retiring the RT-03 dual-mode shims. Research confirms how many of the 28 handlers fit this shape before planning locks it; `ui/capability_runner.py:292-297` already admits some do not accept `**kwargs`.

- **D-08:** The differential parity test drives the **real CLI process and the real MCP dispatch path** over a fixture workspace, for a fixed table of `(capability, payload)` cases, asserting identical `success` / `message` / error-reason fields — including that an unknown field is rejected on both. In-process calls would skip the Typer argument-parsing layer where the positional-call debt actually lives. Planner may trade fixture cost against coverage breadth, but must not fall back to inventory/set-membership assertions, which prove a capability is *listed*, never that two surfaces *behave* the same.

**Review-decision model (GOV-02 / GOV-03)**

- **D-09:** Every proposal gets a **stable `proposal_id` assigned at enqueue time**, stored in the checkpoint with the proposal, and the resume payload becomes a **map keyed by that id**, replacing the positional `zip` in `_resolve_decisions` (`llm/curation_run.py:777-796`). `CurationProposal` (`:164-179`) gains the field. Ids are **opaque** (sequence or uuid), not content-derived — guaranteed unique, no collision reasoning, and "this id is not in this queue" becomes a clean rejection. — **Reversibility:** one-way — the id is persisted into `.construct/workflow/*.sqlite` checkpoints and becomes the contract the Phase 19 API and the Phase 22 review wizards are built against; reverting would require migrating live checkpoint state back to a positional shape.

- **D-10:** A resume whose decision map **does not cover every queued proposal is rejected in full** — zero canonical writes, the run stays paused exactly where it was, and the response names the uncovered proposal ids. This replaces the current `_normalize_decision(None, default)` fallback, which silently applies the gate's own recommendation — i.e. a short or misaligned payload performs a write.

- **D-11:** Stale-queue detection uses the **LangGraph checkpoint id as an ETag** — returned alongside the queue from `graph.get_state(cfg).config["configurable"]["checkpoint_id"]`, required on resume, mismatch rejects with zero writes. Free, since LangGraph already maintains it, and it catches any state advance rather than only queue changes. Research should confirm the id is stable across a pause in the pinned LangGraph version before planning commits.

- **D-12:** Runs already paused in `.construct/workflow/*.sqlite` whose proposals carry no ids are **migrated on read** — opaque ids are assigned at checkpoint-load time so pending human-review work is not abandoned. This is safe rather than a reintroduction of the positional assumption **because D-10 still applies**: a resume must carry a complete id-keyed map, so no legacy positional payload can ever be applied to a migrated queue. The user re-decides in the new shape; migration preserves only the *queue*, never a decision.

**Surface honesty (GOV-04 / GOV-05)**

- **D-13:** **`src/construct/ui/gate_review.py` is deleted**, together with its `st.Page` entry in `streamlit_app.py:47`. Rationale from live code: its "Pending Q&A Reviews" section is built entirely from `st.session_state.gate_queue` (`:56-57`) with no run behind it, and flips `review_status` while calling `_log_gate_event(... "gate_review_approved" ...)` (`:151-169`) into the same append-only audit trail `curation_run._emit` writes to — approvals recorded for things nothing applied. Its "Bridge Candidates" section calls `registry.get("knowledge.connection.add").handler(...)` directly (`:258`) with a hard-coded `ConnectionType.parallels`, ignoring whatever the L3 connection-typing gate decided — a second canonical writer with different semantics from `apply_connections` (`:912-923`). Neither section reviews a `curation.run` / `research.run` queue, so there is no paused checkpoint for them to resume into. Dashboard and Capability Runner stay. — **Reversibility:** reversible — the file is recoverable from git history, but nothing in v0.5 depends on it.

- **D-14 (planner action):** ROADMAP success criterion 4 for this phase is written as *"Approving a proposal in the Streamlit gate-review screen produces exactly the same canonical writes and event records as approving it through the reviewed workflow's own resume path"*. After D-13 that screen does not exist, so the criterion loses its subject. **Restate it** as: no surface writes canonical truth outside the reviewed-workflow resume path (satisfied by removal, guarded by a test), **and** no approval event exists for a decision that was never applied. The second half stands independently and is enforced by D-16.

- **D-15:** The Phase 11 curation exit-code contract **holds** — a degraded `curation.run` still exits 0 on purpose. GOV-05 governs what a surface *reports* (status fields, `--json` payloads, MCP results, human-readable output), not process exit semantics, which the CLI uses to mean "the command ran". Re-opening WR-04 sideways inside a repair phase is precisely what that decision was recorded to prevent. Do not change exit codes in this phase.

- **D-16:** `escalate` is **relabelled, counted separately, and given its own event type**. It writes nothing (`curation_run.py:849-852`), so: name it for its actual effect on every surface (e.g. "flagged — no action taken"); count escalated items in their own bucket so they never fold into an applied or success count; and stop emitting `gate_review_rejected` for them — logging a rejection for something that was escalated is itself an audit trail that lies, the T-15-14 class this codebase already names. The new event type must be threaded through the event-log readers and the views `events.json` projection. Additionally, the **event-count invariant lands in this phase** (it is criterion 4): a `gate_review_approved` must not be emitted for a write that did not happen — `gate_review_approved` currently double-fires per item regardless of no-op writes at `curation_run.py:872`, `:923`, `:968`.

### Claude's Discretion

The user delegated these; planner and researcher have latitude within the stated preference:

- **Byte-contract fix shape** (D-01) — user said "you decide"; research option (i) taken, with the ING-02 tension recorded as a named decision as the ROADMAP requires.
- **Round-trip guard shape** (D-04) — user said "you decide"; strict named-8 + cardinality taken, *because* the user's `extra="ignore"` choice (D-03) makes the guard the sole drift detector.
- **`extra="forbid"` coverage** (D-06) — user said "you decide"; forbid-by-default across all 28 taken, with the audit sized during research.
- **Differential test target** (D-08) — user said "you decide"; real CLI subprocess + real MCP dispatch preferred, planner may trade fixture cost against breadth but not fall back to set-membership.
- **Handler calling convention** (D-07) — user said "you decide"; `handler(**model.model_dump())` preferred for smallest blast radius, contingent on research confirming handler fit.
- **Exit-code contract** (D-15) — user said "you decide"; Phase 11 contract held.
- **GOV-05 enforcement shape** (D-16) — user said "you decide"; prefer a **table-driven cross-surface test** (CLI human output, CLI `--json`, MCP result) driven against a fixture run forced degraded and a fixture run with an escalated item, so Phase 19's HTTP surface joins by adding a row. Result-model-only assertions are insufficient: rendering is precisely where the lie has historically happened.

### Deferred Ideas (OUT OF SCOPE)

- **Checkpoint concurrency contract (WAL / `busy_timeout` / single-flight locking)** — OQ-4, owned by **Phase 19**. D-11's ETag stops cross-process misapplication; it does not stop `database is locked`.
- **The ETag's browser-side use** (`If-Match` / `409 Conflict` semantics, refreshed queue in the body) — **Phase 22**. Phase 18 lands the mechanism, not the HTTP behaviour.
- **Giving `escalate` a real write path** — D-16 makes escalate honest about writing nothing; making it actually route something for follow-up is new capability, not a Phase 18 repair.
- **A run-list capability** (Pitfall 7 — a run whose id is lost is unreachable) — HTTP-07, **Phase 19**.
- **`card list` MCP-boundary hardening (WR-01/WR-02)** — partially subsumed by D-05/D-06 if the seam covers the failure path; whatever the seam does not cover stays carried-forward debt.
- **RT-01/RT-02 registry unification for `spike` and `tag`** — D-02 closes only the `views` half. `spike run --tool-path` is deliberately excluded from HTTP as an RCE primitive; `tag` waits for v0.6.
- **`artifact-catalog.md` prose counts** — D-04/D-08 apply the cardinality lesson to *new* guards; fixing the catalog guard itself is not in scope here.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VFIX-01 | `views validate` accepts every file `views generate` writes — the byte contract round-trips, and `test_views_validate_does_not_yet_accept_generated_bytes` is replaced by a non-vacuous round-trip guard rather than deleted. | § "Finding V1–V6" — the complete measured field-level divergence per file, the four-way `events.json` fork, the dual-purpose `DigestRecord`, the real file cardinality (10 data + `version.json`, not 8), and the vacuity trap in the current pin test's fixture. |
| GOV-01 | CLI, MCP, and HTTP all dispatch through one seam that validates payloads against each capability's declared `input_model`. | § "Finding G1–G5" — the exact reason `input_model` is inert (`list_mcp_tools()` computes `input_schema` and discards it), the full 28-capability audit table for D-06 and D-07, the 25 CLI call sites, and the four non-CLI/MCP in-repo callers. |
| GOV-02 | Human-review decisions keyed by proposal id rather than list position; a missing decision never defaults to applying a write. | § "Finding G6" — `CurationProposal` shape and `extra="forbid"` migration consequence; `_resolve_decisions` in both `curation_run.py` and `research_run.py` (the latter already has a second, url-keyed mode that must also go). |
| GOV-03 | A review queue that went stale between render and submit is detected and rejected. | § "Finding G7" — `checkpoint_id` ETag semantics verified empirically on the pinned LangGraph 1.2.9 / checkpoint-sqlite 3.1.0. |
| GOV-04 | No surface writes canonical truth outside the reviewed-workflow resume path; no approval event for a decision never applied. | § "Finding G8" — `gate_review.py`'s two violations confirmed in live code plus its tautological `EventResult` branch; the complete reference set to remove; the `gate_review_approved`-on-failure/no-op emission sites. |
| GOV-05 | No surface reports success for a degraded or partially-applied outcome. | § "Finding G9" — the precise `success = status != "failed"` → `✓` chain, and the fact that `escalated` never reaches any CLI renderer at all. |
</phase_requirements>

## Summary

This phase contains no new capability and no new dependency. Every item is a repair to code that runs today, and the single highest-value thing research can give the planner is **measured ground truth in place of the estimates carried in CONTEXT.md**. Four of those estimates are materially wrong, and each error moves work between plans:

1. **VFIX-01 is roughly twice the size CONTEXT assumes and structurally different in kind.** Against a *populated* install root, `views validate` fails **5 of 8** files, not 3 — and four of those five failures are **field renames producing `Field required` errors**, not merely extra keys. This matters because D-03 (`extra="forbid"` → `extra="ignore"`) fixes only the extra-key half. The rename half requires editing model field names one by one. Separately, the "8 files" framing is arithmetically wrong: the generator writes **10 data files plus `version.json`** for a one-workspace root, two of which (`<ws>/stats.json`, `<ws>/curation-history.json`) have no contract model at all. D-04's "assert the written-file count equals 8" would fail on the first run.

2. **GOV-01's root cause is one line, and D-06 is half the size CONTEXT assumes.** `registry.list_mcp_tools()` carefully computes `input_model.model_json_schema()` and `mcp/server.py` **never passes it to `add_tool`** — FastMCP therefore derives every tool's schema from the generic `handler(**kwargs)` signature. That, precisely, is why `CardListInput`'s `extra="forbid"` is inert (WR-02). And the audit is smaller than feared: **14 of 28 input models already carry `extra="forbid"`**, not one.

3. **D-07 is safer than CONTEXT feared but its blast radius is wider.** **23 of 28 handlers already accept `handler(**model.model_dump())`**; exactly 5 mismatch. Strikingly, those 5 mismatches are 5 of the 6 capabilities that are *not exposed over MCP* — they have never been called by keyword, so their drift was never observable. But CONTEXT's "three positional call sites in `cli.py`" is wrong: there are **25 handler call sites in `cli.py`**, about ten of them positional, plus four more callers outside CLI and MCP entirely.

4. **D-11 is verified, not assumed.** The `checkpoint_id` ETag was executed against the pinned LangGraph: stable across re-reads, stable across a separate process/connection, and changing on both `update_state` and resume. It behaves exactly as D-11 needs.

The one decision research recommends the planner revisit before locking is **D-01 applied to `events.json`**. D-01's justification is "the SPA already reads these bytes" — true for cards and digests, and verified in the SPA source. It is **not** true for events: there are four mutually incompatible event shapes in this repository (the Python emitter, legacy Claude-native fixture logs, the views model, and the SPA component), and "conform to the bytes" is under-determined because the bytes differ per emitter. This is flagged as OQ-A rather than decided here.

**Primary recommendation:** Sequence the phase as *measure → conform → seam → decisions → honesty*, and make the two derived files (`<ws>/stats.json`, `<ws>/curation-history.json`) an explicit in-or-out scope decision in Wave 1 rather than letting the "8 files" phrase carry it implicitly. Treat `events.json` as its own task with its own named decision, not as one row in a bulk model-rename.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Views data contract (`views/models.py`) | Derived projection (L4 read model) | — | Author is `views/generate.py`; consumer is the SPA. Neither canonical truth nor a trust boundary — this is precisely why D-03's `extra="ignore"` is correct here and wrong for capabilities. |
| `views validate` as a capability | Capability registry (L1) | CLI + MCP surfaces | D-02 moves it from a hand-written Typer command to a registry record so Phase 19's generated adapter inherits it. |
| Capability invocation seam (`registry.invoke`) | Capability registry (L1) | CLI, MCP, Streamlit runner, HTTP (Ph19) | The single trust boundary where agent- and user-supplied payloads are validated. `extra="forbid"` belongs here, not in views. |
| Handler execution | Services / pipelines (L2) | — | Handlers must stay ignorant of which surface called them; the seam owns marshalling. |
| Review queue + decisions | LangGraph checkpoint state (L3, `.construct/workflow/*.sqlite`) | Capability layer reads/writes it | `proposal_id` and the checkpoint-id ETag are checkpoint-tier concepts; surfaces only transport them. |
| Canonical writes (cards, connections) | Services (`edit_card`, `add_connection`, `archive_card`) | Reached only from apply nodes downstream of `interrupt()` | GOV-04 is the invariant that no other tier may call these. `gate_review.py` violates it today. |
| Audit trail (`log/events.jsonl`) | Services (`event_log.append_event`) | Read by views `parse_events` and the SPA | GOV-05/D-16's new event type must be threaded emitter → reader → projection → SPA. |
| Degraded/escalated reporting | Surface renderers (`cli.py` `_render_*`, MCP serializer) | Result models | GOV-05's defect lives in rendering, not in the result model — which is why CONTEXT's table-driven cross-surface test is the right shape. |

## Standard Stack

This phase installs **nothing**. Every library it touches is already pinned and installed. Versions below were read from the live interpreter, not from `pyproject.toml` declarations.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.3 | All contract models — views models, capability `input_model`s, `CurationProposal` | Already the project-wide convention; `AGENTS.md` § Pydantic Conventions mandates it [VERIFIED: `.venv` interpreter] |
| langgraph | 1.2.9 | Durable human-in-the-loop graphs; source of the `checkpoint_id` ETag | Already pinned; ADR-0004 sanctions it [VERIFIED: `importlib.metadata`] |
| langgraph-checkpoint-sqlite | 3.1.0 | `SqliteSaver` behind `.construct/workflow/*.sqlite` | Already pinned [VERIFIED: `importlib.metadata`] |
| typer | 0.24.1 | CLI surface whose call sites D-07 normalizes | Already pinned [VERIFIED: STACK.md + `.venv`] |
| mcp (FastMCP) | ≥1.0 | MCP stdio surface; `add_tool` is the GOV-01 defect site | Already pinned [VERIFIED: `src/construct/mcp/server.py` import] |
| pytest | 9.0.3 | Test runner for every guard this phase adds | Already pinned; `testpaths = ["tests"]` [VERIFIED: `pyproject.toml:41-43`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typer.testing.CliRunner` | bundled | In-process CLI invocation | Existing tests use it; **insufficient alone for D-08** — see Pitfall 5 |
| `subprocess` | stdlib | Real-CLI arm of the D-08 differential test | Required by D-08's "real CLI process" wording |
| `mcp.server.fastmcp` | bundled | Real-MCP arm of D-08 | Drive `create_server()`'s registered tool functions, not `capability.handler` directly |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Renaming views model fields to writer names | Pydantic `Field(alias=...)` + `populate_by_name=True` | Keeps both spellings valid and would let `DigestRecord` serve its two masters (see Finding V4). Costs: aliases are a second contract surface, and `model_json_schema()` output changes shape — which Phase 19's generated adapter consumes. **Recommend against** for capability models; **worth the planner's consideration for `DigestRecord` alone.** |
| `handler(**model.model_dump())` | `handler(model)` (pass the model object) | Cleaner typing, but breaks all 28 handlers at once and contradicts D-07. Not viable in a repair phase. |
| Opaque `proposal_id` | Content hash of the payload | D-09 explicitly rejected this; research concurs — `research_run._resolve_decisions` already url-keys and `url` can be `None` or duplicated (Finding G6). |
| `checkpoint_id` as ETag | A hash of the serialized `gate_queue` | Would miss state advances that leave the queue textually identical. D-11's choice is strictly stronger and free. |

**Installation:** none required.

```bash
# Verify the existing environment instead:
.venv/bin/python -m pip install -e '.[dev]'   # only if imports fail
```

## Package Legitimacy Audit

**This phase installs no external packages.** No registry lookups, slopsquat checks, or `postinstall` inspections apply. All libraries named in the Standard Stack are pre-existing pinned dependencies verified present in `.venv` by direct interpreter query [VERIFIED: `importlib.metadata.version`].

| Package | Registry | Status | Verdict | Disposition |
|---------|----------|--------|---------|-------------|
| — | — | No new packages introduced by Phase 18 | n/a | n/a |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

**Planner note:** if any plan proposes adding a dependency (for example a JSON-schema differ, a snapshot-test library, or a UUID helper), that is a scope change — this phase's work is achievable with pydantic, stdlib `uuid`, and pytest alone.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────────────────────────┐
                        │            INVOCATION SURFACES               │
                        └──────────────────────────────────────────────┘
   construct CLI (Typer)        MCP stdio (FastMCP)      Streamlit runner     HTTP (Phase 19)
   25 .handler() call sites     handler(**kwargs)        handler(**inputs)    [not built here]
   ~10 positional               mcp/server.py:33         capability_runner:130
            │                          │                        │                    │
            │  D-07: normalize         │  pure insertion        │  joins later       │  joins later
            ▼                          ▼                        ▼                    ▼
   ╔══════════════════════════════════════════════════════════════════════════════════════╗
   ║   GOV-01 SEAM  registry.invoke(cap_id, payload)   ◄── NEW; does not exist today       ║
   ║   1. registry.get(cap_id)                                                            ║
   ║   2. model = cap.input_model.model_validate(payload)   ← extra="forbid" bites HERE    ║
   ║   3. return cap.handler(**model.model_dump())                                         ║
   ╚══════════════════════════════════════════════════════════════════════════════════════╝
            │                                                        ▲
            │  23/28 handlers fit as-is · 5 MISMATCH must be fixed    │ D-08 differential test
            ▼                                                        │ drives BOTH arms
   ┌──────────────────────┐   ┌───────────────────────┐   ┌─────────────────────────────┐
   │  Read capabilities   │   │  Workflow capabilities│   │  Write capabilities         │
   │  status/validate/    │   │  curation.run         │   │  card.create/edit/archive   │
   │  list/inspect/views  │   │  research.run         │   │  connection.add/remove      │
   └──────────────────────┘   └───────────┬───────────┘   └──────────────┬──────────────┘
                                          │                              ▲
                                          ▼                              │ ONLY reachable
                            ┌─────────────────────────────┐              │ from apply nodes
                            │  LangGraph StateGraph       │              │ (GOV-04 invariant)
                            │  … → gate_review[interrupt] │              │
                            └──────────────┬──────────────┘              │
                                           │ PAUSE                        │
                     ┌─────────────────────▼─────────────────────┐        │
                     │  .construct/workflow/*.sqlite  (ADR-0004) │        │
                     │  gate_queue[] + checkpoint_id             │        │
                     └───────┬───────────────────────────┬───────┘        │
                             │ render queue              │ resume         │
                 ┌───────────▼────────────┐   ┌──────────▼─────────────┐  │
                 │ inspect / review        │   │ GOV-02: decisions are  │  │
                 │ returns queue + ETag    │   │   {proposal_id: verdict}│ │
                 │ (checkpoint_id)         │   │ GOV-03: ETag must match │ │
                 └─────────────────────────┘   │ D-10: incomplete map    │ │
                                               │   → REJECT, zero writes │ │
                                               └──────────┬──────────────┘ │
                                                          │ all checks pass│
                                                          └────────────────┘
                                                                   │
                     ┌─────────────────────────────────────────────▼──────────────────┐
                     │  apply_promotions / apply_connections / apply_archives          │
                     │  → edit_card / add_connection / archive_card   (CANONICAL)      │
                     │  → _emit(...) → event_log.append_event → log/events.jsonl       │
                     │     GOV-05/D-16 defect: approved event fires even on            │
                     │     failed write and on idempotent no-op                        │
                     └─────────────────────────────┬──────────────────────────────────┘
                                                   │
   ╔═══════════════════════════════════════════════▼══════════════════════════════════════╗
   ║  X  DELETED BY D-13: ui/gate_review.py — writes canonically WITHOUT a checkpoint,      ║
   ║     bypassing the entire gate above, and logs gate_review_approved for nothing.        ║
   ╚═══════════════════════════════════════════════════════════════════════════════════════╝

   ── VFIX-01 projection path (independent of the seam) ────────────────────────────────────
   workspace files ─► views/lib/parse_*.py ─► generate.py assembles `files{}` dict
                                                    │
                       D-01 DELETES this step ──►  _validate_file_data (adapter tables)
                                                    │  validates an ADAPTED projection …
                                                    ▼
                                            envelope.wrap → _write_atomic
                                                    │  … then writes the RAW parser dict
                                                    ▼
                              views/build/data/*.json  (10 files + version.json for 1 ws)
                                                    │
                     ┌──────────────────────────────┴──────────────────────────────┐
                     ▼                                                             ▼
        cli.py views validate → unwrap_payload → views/models.py          SPA (React) reads
        covers 8 slots; 5 FAIL today                                      connects_to, summary_excerpt,
                                                                          theme, summary_text, date
```

### Recommended Task Structure

```
Wave 1 — measure & conform (VFIX-01)
├── enumerate the real written-file set (fix D-04's "8")
├── conform views/models.py field-by-field to writer names
├── delete _FILE_MODEL_MAP / _PER_WS_FILES + _validate_file_data
└── replace the pin test with a non-vacuous round-trip guard on a POPULATED fixture

Wave 2 — seam (GOV-01)   [independent of Wave 1; can run parallel]
├── registry.invoke() + input-schema plumbing into add_tool
├── fix the 5 MISMATCH capabilities
├── extra="forbid" across the remaining 14 models
├── normalize cli.py call sites + retire RT-03 shims
└── differential CLI↔MCP parity test

Wave 3 — decisions (GOV-02/03)   [depends on nothing above, but must precede Ph19/Ph22]
├── proposal_id on CurationProposal + enqueue sites
├── id-keyed _resolve_decisions in curation_run AND research_run
├── D-10 complete-coverage rejection
├── D-11 checkpoint_id ETag on inspect/review
└── D-12 migrate-on-read for legacy checkpoints

Wave 4 — honesty (GOV-04/05)
├── delete ui/gate_review.py + streamlit_app.py page entry
├── guard test: no canonical writer outside apply nodes
├── D-16 escalate relabel + own event type + own count
├── gate_review_approved only on an actual write
└── table-driven cross-surface degraded/escalated test
```

### Pattern 1: Validating seam with surface-agnostic handler dispatch

**What:** One function owns "payload → validated model → handler call". Every surface calls it; no surface calls `cap.handler` directly.
**When to use:** GOV-01, and as the contract Phase 19's adapter routes through.
**Example:**

```python
# Source: pattern derived from live src/construct/mcp/server.py:30-38 (which already
# does step 3 correctly) plus the missing steps 1-2. [VERIFIED: live code]
def invoke(self, cap_id: str, payload: dict) -> Any:
    cap = self.get(cap_id)                      # raises KeyError with available list
    model = cap.input_model.model_validate(payload)   # extra="forbid" rejects here
    return cap.handler(**model.model_dump())
```

The seam must return *the same error shape* for a validation failure regardless of surface — that is what D-08's differential test asserts. Note `mcp/server.py` currently swallows every exception into `{"error": str(exc)}` (`:36-37`) while the CLI raises `typer.Exit(1)`; the seam should raise a typed error and let each surface render it, or the differential test will be comparing two different renderings of the same failure.

### Pattern 2: Passing the real input schema to FastMCP

**What:** The registry already computes the JSON Schema; the server must actually hand it to `add_tool`.
**When to use:** GOV-01 — this is the specific fix for WR-02.
**Example:**

```python
# Source: live src/construct/mcp/server.py:40-44 — entry["input_schema"] is computed
# in registry.list_mcp_tools():63 and then DISCARDED here. [VERIFIED: live code]
app.add_tool(
    fn=make_handler(),
    name=entry["name"],
    description=entry["description"],
    # entry["input_schema"] is never passed → FastMCP infers from **kwargs
)
```

**Planner action:** confirm against the installed `mcp` package whether `FastMCP.add_tool` in the pinned version accepts an explicit schema override parameter. If it does not, the seam's own `model_validate` inside `make_handler` still enforces the contract at call time — the advertised schema is then a *discoverability* gap rather than an enforcement gap, and the phase should say so explicitly rather than leave it implied. [ASSUMED: the parameter name and availability were not verified in this session.]

### Pattern 3: Complete-coverage decision map (D-10)

**What:** Reject the whole resume rather than defaulting any single proposal.
**Example:**

```python
# Replaces the positional zip + _normalize_decision(None, default) fallback at
# curation_run.py:777-796. [VERIFIED: live code read]
queued = {p["proposal_id"] for p in gate_queue}
supplied = set(decisions)
missing, unknown = queued - supplied, supplied - queued
if missing or unknown:
    raise ReviewRejected(missing=sorted(missing), unknown=sorted(unknown))
return {pid: decisions[pid] for pid in queued}
```

The rejection must happen **before** any apply node runs — practically, inside the resume capability before `graph.invoke(Command(resume=...))`, not inside a node, because a node-raised error still advances the checkpoint.

### Anti-Patterns to Avoid

- **Relaxing `extra` to make a test pass.** `extra="ignore"` is correct for views (derived projection) and wrong for capabilities (trust boundary). CONTEXT § Specific Ideas explicitly warns the planner not to "harmonize" the two. They are deliberately different.
- **Asserting on a set of filenames instead of a count.** WR-01's lesson; D-04 and D-08 both turn on it.
- **Measuring a round trip on an empty fixture.** See Pitfall 1 — the existing pin test does exactly this and consequently reports 3 failures where a populated root reports 5.
- **Emitting an audit event before the write it claims.** All three current `gate_review_approved` sites do this.
- **Fixing `mcp/server.py` by restructuring it.** CONTEXT is explicit: the seam is an insertion. The file is 52 lines and its registry-driven generation is the structural proof Phase 19 depends on.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stale-queue detection | A hash of the serialized `gate_queue`, a version counter, or a mtime check on the sqlite file | LangGraph's `checkpoint_id` from `graph.get_state(cfg).config["configurable"]["checkpoint_id"]` | Already maintained, monotonic per state advance, stable while paused, stable cross-process — all four verified empirically in this session (Finding G7). A queue hash misses advances that leave the queue textually unchanged. |
| Unique proposal ids | Content hashes, `url`, card_id, or list index | `uuid.uuid4().hex` (stdlib) or a run-scoped counter | D-09 requires opaque. `research_run` already demonstrates the content-derived failure: it keys on `finding.url`, which can be `None` or duplicated across findings. |
| Payload validation at the boundary | Hand-written `if "x" not in payload` checks in each surface | `cap.input_model.model_validate(payload)` | This is the entire point of GOV-01; hand-rolled checks are how the CLI and MCP forked in the first place. |
| Identifier guards for `proposal_id` | A new regex validator | Reuse `_validate_run_id` (`curation_run.py:64-77`) | Named in CONTEXT § Reusable Assets; written for exactly this threat ("MCP/CLI shims pass caller-supplied `**kwargs` straight into the input models"). |
| A populated round-trip fixture | A new hand-built workspace | `_populated_install_root()` / `POPULATED_FIXTURE = tests/fixtures/v02/multi-domain-medium` (`test_views_generate.py:31,55`) | Already exists, already copies-and-clears the build dir to defeat the fingerprint cache. Critical for defeating the vacuity trap. |
| Atomic JSON writes | New write logic | `generate.py::_write_atomic` (`:518-522`) | Already correct (tmp + `replace`). |
| Event serialization | A new event dataclass | `services/event_log.append_event` + `schemas/config.EventRecord` | D-16's new event type must go through this path, not around it. |

**Key insight:** almost everything this phase needs already exists somewhere in the repository — the defects are consistently *two* correct implementations that never learned about each other. `generate.py` correctly computes an adapted projection and correctly writes bytes, but writes the wrong one of the two. `registry.list_mcp_tools()` correctly computes a JSON Schema and `mcp/server.py` correctly registers a tool, but the schema never crosses the gap. `apply_promotions` correctly detects a failed write and correctly emits an audit event, but emits it on both branches. The planner should look for the *existing* correct half before writing a new one.

## Common Pitfalls

### Pitfall 1: The vacuity trap — measuring the byte contract on an empty fixture

**What goes wrong:** `test_views_validate_does_not_yet_accept_generated_bytes` asserts the failing set is exactly `{"stats.json", "demo/connections.json", "demo/events.json"}` — three files. Executed against a populated install root in this session, the failing set is **five**: `stats.json`, `main/cards.json`, `main/connections.json`, `main/digests.json`, `main/events.json` [VERIFIED: `construct views validate` run on a copy of `test-ws/paskunas`].
**Why it happens:** the `scaffolded_install_root` fixture's workspace has no cards and no digests, so `CardsFile` and `DigestsFile` validate a `[]` and the record models are never exercised. Empty-list validation is the canonical vacuous pass.
**How to avoid:** D-04's guard must run on `_populated_install_root()`, and must assert **non-empty record lists** per file — not merely non-empty *files*, which an `{"cards": []}` envelope satisfies. `bridges.json` is the residual risk: even the populated fixture produced an empty `bridges` list, so `BridgeRecord` stays unexercised unless the guard forces bridges into the fixture or asserts the gap explicitly.
**Warning signs:** a guard that goes green without any model edit; a failing-set assertion whose cardinality differs between two fixtures.

### Pitfall 2: `extra="ignore"` does not fix a rename

**What goes wrong:** D-03 is read as the whole fix for VFIX-01, models are relaxed, and 4 of the 5 files still fail — because their errors are `Field required`, not `extra_forbidden`.
**Why it happens:** the adapter tables were doing two jobs at once: dropping extra keys *and* renaming fields. Deleting them (D-01) exposes both. Measured example: `main/cards.json` produced **243 validation errors** across both classes on one fixture.
**How to avoid:** treat each model as a rename task first and an `extra` task second. The complete rename map is in Finding V2 — hand it to the implementer verbatim so nobody re-derives it from a partial error dump.
**Warning signs:** an implementer reporting "relaxed extra, still failing"; a diff that changes only `model_config` lines.

### Pitfall 3: `model_dump()` materializes defaults and erases "unset"

**What goes wrong:** `handler(**model.model_dump())` always passes every field. For a partial-update capability like `knowledge.card.edit`, an explicitly-supplied `title=None` becomes indistinguishable from an omitted `title`.
**Why it happens:** Pydantic fills defaults on validation; `model_dump()` serializes them.
**How to avoid:** verified in this session that today's shims survive this — `_build_card_updates` filters `is not None`, and `CardCreateInput.author` / `CardEditInput.author` default to `"construct"` / `"curator"` rather than `None`, so `kwargs.get(k, fallback)` still yields the intended value [VERIFIED: model-field introspection]. The risk is not present but is one careless default change away. If the planner wants partial-update semantics preserved under the seam, use `model_dump(exclude_unset=True)` for edit-shaped capabilities and document why it differs.
**Warning signs:** a `card edit` that blanks a field the caller did not mention.

### Pitfall 4: `extra="forbid"` on `CurationProposal` breaks reading old checkpoints

**What goes wrong:** D-09 adds `proposal_id` to `CurationProposal`, which is `model_config = {"extra": "forbid"}` (`curation_run.py:174`). Persisted checkpoints from before this phase contain proposals **without** the field. If `proposal_id` is required, validating a legacy checkpoint raises; if the migration path itself constructs the model, it must assign the id *before* validation.
**Why it happens:** the field is added to a model that is both a serialization target and a deserialization source for durable state.
**How to avoid:** D-12's migrate-on-read must inject ids at the raw-dict stage. Note the queue is persisted as **plain dicts** in state, not model instances — `_resolve_decisions` reads `entry.get("decision", "")` (`:790`), confirming dict access. That makes injection straightforward, but it also means nothing validates the queue on the way back in.
**Warning signs:** a paused pre-Phase-18 run that now errors on `curation inspect`.

### Pitfall 5: `CliRunner` is not "the real CLI process"

**What goes wrong:** D-08 is implemented with `typer.testing.CliRunner` because every existing test uses it, and the parity test passes while the actual `construct` binary still diverges.
**Why it happens:** `CliRunner` invokes the app in-process; it does exercise Typer's parameter parsing, but shares the interpreter, the registry singleton (`catalog.get_registry()` caches in a module global at `:988-993`), and any monkeypatching in scope.
**How to avoid:** D-08 explicitly says "the real CLI process". Use `subprocess` with `.venv/bin/python -m construct.cli` for at least the error-shape cases, where a shared-process test is most likely to lie. Reserve `CliRunner` for breadth.
**Warning signs:** a parity suite that passes but whose assertions never touch stderr or the exit code.

### Pitfall 6: Deleting `gate_review.py` without deleting its navigation entry

**What goes wrong:** `streamlit_app.py:47` calls `st.Page("gate_review.py", ...)` and `:49` passes it to `st.navigation([home, runner, gates])`. Removing only the file makes the whole Streamlit app fail to start.
**How to avoid:** both edits in one task. Verified the reference set is small: `streamlit_app.py` is the **only** in-repo reference to the module [VERIFIED: repo-wide grep]. Every other `gate_review` hit is either `research_run.py`'s LangGraph *node* of the same name (unrelated, keep) or the `gate_review_approved` / `gate_review_rejected` event strings (D-16's concern, keep the strings).
**Warning signs:** a plan that lists the file deletion but not `streamlit_app.py`.

### Pitfall 7: Assuming `escalated` merely renders badly

**What goes wrong:** D-16 is scoped as a relabelling job. In fact `escalated` **never reaches any CLI renderer** — `grep escalated src/construct/cli.py` returns nothing [VERIFIED]. `_render_curation_result` (`cli.py:661-678`) prints `status`, `run_id`, per-step lines, and `events`; there is no bucket for escalated items at all.
**How to avoid:** treat D-16 as *adding* a surface field, not renaming one. The state channel exists (`escalated: Annotated[list[str], operator.add]`, `curation_run.py:112`) and the apply node returns it (`:876`); the gap is between the result payload and the renderer.

### Pitfall 8: Two different classes named `EventRecord`

**What goes wrong:** an implementer edits the wrong one. `construct.schemas.config.EventRecord` (`:354-362`) is the **emitter's** model (`ts`, `agent`, `action`, `target`, `detail`, `result`); `construct.views.models.EventRecord` (`:287-296`) is the **views validator's** model (`timestamp`, `type`, `actor`, `card_id`, `details`). They share a name and no fields.
**How to avoid:** always import qualified in this phase's diffs, and name the module in every task instruction.

## Code Examples

### Reproducing the byte-contract divergence (the measurement every VFIX-01 task should start from)

```bash
# Source: executed in this session against a scratch copy of test-ws/paskunas.
# [VERIFIED: live run]
SC=/tmp/scratch
cp -R test-ws/paskunas $SC/pk && rm -rf $SC/pk/views/build
.venv/bin/python -m construct.cli views generate --install-root $SC/pk
#   → Views data generation: build 1c7852cb, 11 files written, 0 validation errors
.venv/bin/python -m construct.cli views validate --install-root $SC/pk
#   → Views data validation: 3 passed, 5 failed, 0 missing
```

The generator reports **zero** validation errors while writing files that the validator rejects — the writer/reader fork in one command pair.

### The checkpoint-id ETag, verified on the pinned LangGraph

```python
# Source: executed in this session on langgraph 1.2.9 + langgraph-checkpoint-sqlite 3.1.0.
# [VERIFIED: live run]
cfg = {"configurable": {"thread_id": run_id}}
graph.invoke(initial_state, cfg)          # pauses at interrupt()
etag = graph.get_state(cfg).config["configurable"]["checkpoint_id"]
# → '1f189225-8588-647c-8001-78b7549b095e'
#   re-read while paused                 → identical
#   read via a SEPARATE sqlite connection→ identical
#   after graph.update_state(...)        → CHANGED
#   after graph.invoke(Command(resume=…))→ CHANGED
```

All four properties D-11 depends on hold. Resume-side check:

```python
snap = graph.get_state(cfg)
current = snap.config["configurable"]["checkpoint_id"]
if supplied_etag != current:
    raise StaleQueue(expected=current, supplied=supplied_etag)   # zero writes
```

### The GOV-01 defect in one diff-sized excerpt

```python
# Source: live src/construct/capabilities/registry.py:55-65 — schema IS computed …
def list_mcp_tools(self) -> list[dict]:
    tools.append({
        "name": cap.mcp_tool_name,
        "description": cap.description,
        "input_schema": cap.input_model.model_json_schema(),   # ← computed
    })

# Source: live src/construct/mcp/server.py:40-44 — … and never used.
app.add_tool(
    fn=make_handler(),          # signature is handler(**kwargs)
    name=entry["name"],
    description=entry["description"],
)                               # entry["input_schema"] dropped on the floor
```

### The GOV-05 defect chain

```python
# Source: live src/construct/capabilities/catalog.py (_daily_result_to_operation, ~:847)
return OperationResult(success=result.status != "failed", ...)   # degraded ⇒ success=True

# Source: live src/construct/cli.py:687-692
if not result.success:
    _display_result(result, json_output=False); return
if result.data:
    _render_curation_result(result.data)      # prints "status: degraded"  ← honest
typer.echo(f"✓ {result.message}")             # prints a green check       ← the lie
```

The result model is honest and the status line is honest; the terminal verdict glyph is not. This is exactly why CONTEXT's D-16 discretion note insists on a *rendering-level* cross-surface test rather than result-model assertions.

### The `gate_review_approved`-without-a-write sites

```python
# Source: live src/construct/llm/curation_run.py, apply_promotions (~:864-872)
if lifecycles.get(card_id) == target:
    promoted.append(card_id)                       # idempotent NO-OP: nothing written
else:
    res = edit_card(...)
    if res.success:  promoted.append(card_id)
    else:            logger.warning(...)           # WRITE FAILED
events.append(_emit(workspace, "gate_review_approved", card_id, f"promote → {target}"))
#              ↑ emitted on ALL THREE paths: success, no-op, and failure
```

The same unconditional-emit shape recurs in `apply_connections` (~`:923`) and `apply_archives` (~`:968`) [VERIFIED: live code read].

## Findings

### Finding V1 — the file cardinality in D-04 is wrong

For a **one-workspace** install root the generator writes:

| Scope | Files | Has a contract model? | Checked by `views validate`? |
|-------|-------|----------------------|------------------------------|
| Global | `domains.json`, `articles.json`, `stats.json`, `bridges.json` | yes (4) | yes |
| Per workspace | `cards.json`, `connections.json`, `digests.json`, `events.json` | yes (4) | yes |
| Per workspace | `stats.json`, `curation-history.json` | **no** | **no** |
| Build root | `version.json` | no | no |
| Build root | `_build_meta.json`, `_generation-warnings.log` | no | no |

`total_files_written` reported **11** on the fixture run (10 data files + `version.json`) [VERIFIED: live run and `generate.py:344-406`]. `views validate` covers **8 slots**, and per-workspace file counts scale with workspace count, so any fixed cardinality assertion must be expressed as `4 + 6·N_workspaces` (+1 for `version.json`), not a literal 8.

**Planner action:** restate D-04's cardinality clause. Recommended form: *assert the set of validated slots is exactly the 8 named ones, that all 8 pass, and that `report.total_files_written == 4 + 6*n_ws + 1`.* Also decide explicitly whether `<ws>/stats.json` and `<ws>/curation-history.json` gain contract models in this phase — they are the only two data files with no gate whatsoever, and D-04's "the guard is the only drift detector" argument applies to them most of all.

### Finding V2 — the complete rename map (hand this to the implementer)

Measured by diffing raw written payload keys against `model_fields` per file [VERIFIED: live introspection]. `→` means "model field ← writer key".

| File | Status | Top-level | Record-level renames | Extra writer keys (need `extra="ignore"`) | Model fields with NO writer source |
|------|--------|-----------|----------------------|-------------------------------------------|-------------------------------------|
| `bridges.json` | PASS | ok | — | — | — (but `bridges` was **empty** — record model unexercised) |
| `domains.json` | PASS | ok | exact match | — | — |
| `articles.json` | PASS | ok | exact match | — | — |
| `stats.json` | **FAIL** | writer emits `totals`, `by_confidence`, `by_lifecycle`, `activity_last_30d`; model declares `total_cards`, `total_connections`, `total_domains`, `total_digests`, `total_articles`, `cards_by_domain` | n/a — whole-file shape mismatch | all 4 | all 6 |
| `<ws>/cards.json` | **FAIL** | ok | `connections ← connects_to`, `summary ← summary_excerpt` | `author`, `body_markdown`, `created`, `last_reviewed`, `sources`, `tags` | — |
| `<ws>/connections.json` | **FAIL** | writer adds `type_counts` | `created_at ← created`, `created_by ← author` | `id` (+ `type_counts` at top level) | — |
| `<ws>/digests.json` | **FAIL** | ok | `domain_id ← domain`, `title ← theme`, `generated_at ← date`, `summary ← summary_text` | `coverage_notes`, `papers_found`, `papers_ingested`, `papers_skipped`, `raw_path`, `search_clusters`, `seed_cards_created`, `suggested_adjustments`, `top_findings` | **`card_ids`** — the adapter hard-codes `[]` (`generate.py:146`); no parser emits it |
| `<ws>/events.json` | **FAIL** | ok | see Finding V3 — under-determined | `from`, `to`, `confidence_set`, … | `details` had no source in the measured fixture |

Note `unwrap_payload` strips only `ENVELOPE_METADATA_KEYS` (`models.py:316-326`), which does **not** include `type_counts` — so that key reaches the model and trips `extra_forbidden`. Confirming: the `stats.json` failure is *four* `extra_forbidden` errors, and `cards.json` produced **243** errors across a mix of `missing` and `extra_forbidden` [VERIFIED: live run].

### Finding V3 — `events.json` has four incompatible shapes; D-01's premise does not hold here

| # | Source | Field names | Evidence |
|---|--------|-------------|----------|
| 1 | **Python emitter** — `schemas/config.EventRecord` via `event_log.append_event` | `ts`, `agent`, `action`, `target`, `detail`, `result` | `schemas/config.py:354-362`, `services/event_log.py:26-33` |
| 2 | **Legacy Claude-native logs** in fixtures | `event`, `timestamp`, `details` / `card` / `author` / `workspace` / `from` / `to` | `test-ws/paskunas/main/log/events.jsonl`, `tests/fixtures/v02/multi-domain-medium/*/log/events.jsonl` |
| 3 | **Views validator** — `views/models.EventRecord` | `timestamp`, `type`, `actor`, `card_id`, `details` | `views/models.py:287-296` |
| 4 | **SPA** — `ActivityList.jsx` | `e.timestamp`, `e.actor`, `e.type`, `e.subject.card_id`, `e.skill` | `CONSTRUCT-CLAUDE-impl/.../components/ActivityList.jsx:10-14,39-45` |

`parse_events.parse` passes JSONL lines through **verbatim** (`parse_events.py:31-36`) — it renames nothing. So `events.json`'s on-disk shape is whatever emitter wrote the log, and "conform the model to the bytes" has no single referent.

Two consequences the planner must weigh:

- Conforming `views/models.EventRecord` to shape #2 (what the fixtures contain) makes `views validate` pass but codifies **legacy** data as the contract, and still would not match shape #1, which is what CONSTRUCT writes today.
- The SPA (shape #4) matches neither #1 nor #2. `prettyType(e.type)` and `e.actor` therefore render blank for every Python-emitted event **right now**. This is a live defect adjacent to, but not created by, this phase.

D-16 requires threading a new event type "through the event-log readers and the views `events.json` projection". That thread is broken today at the emitter→model hop. **Raised as OQ-A.**

### Finding V4 — `DigestRecord` is also a writer model

`llm/research_run.py:644` imports `DigestRecord` and `DigestsFile` from `construct.views.models` and uses them to write the workspace's `digests/digests.json` record store (`compile_digest`, docstring at `:636`) [VERIFIED: live code read]. So `DigestRecord` serves two masters: a *validator* for the derived views projection, and a *writer* for a workspace file.

Renaming its fields to the `parse_digests` spellings (`theme`, `date`, `summary_text`, `domain`) therefore changes what `research.run` writes into the workspace — a change of a different character from "conform a derived projection", and one whose own consumers must be checked. `tests/llm/test_research_run.py:37` also imports `DigestsFile` and will move with it.

**Planner action:** make `DigestRecord` its own task with the two-consumer question answered explicitly. This is the strongest candidate in the phase for the `Field(alias=...)` alternative noted in the Alternatives table — it is the one model where two spellings genuinely have two legitimate authors.

### Finding V5 — the SPA does read writer names (for cards and digests)

D-01's justification verified where it matters most [VERIFIED: grep of the scaffold template SPA]:

- `Artifacts.jsx:211` — `(c.connects_to || []).length`
- `Wiki.jsx:214`, `:401` — `c.summary_excerpt`
- `Wiki.jsx:178`, `Digests.jsx:47`, `DigestDetail.jsx:56` — `d.theme`
- `DigestDetail.jsx:73,77` — `digest.summary_text`
- `Wiki.jsx:178` — `d.date`

So for `cards.json` and `digests.json`, conforming models to the writer is unambiguously the right direction — the SPA is already there. The live SPA is the **scaffold template** at `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-scaffold/template/src/`; `views/design-example/` is a design prototype and matched none of these greps.

### Finding V6 — `_validate_file_data` is the only consumer of the adapter tables

`_FILE_MODEL_MAP` and `_PER_WS_FILES` are referenced only from `_validate_file_data` (`generate.py:484-490`), which is called only from the write loop (`:377`). Files with no table entry fall through to `False` — meaning per-workspace `stats.json` and `curation-history.json` are written **unvalidated today** (`:478-482` says so explicitly). Deleting the tables per D-01 therefore removes generate-time validation entirely unless it is replaced with a direct `model_validate` against the conformed models. **Do not let D-01 silently downgrade `views generate` from validating-writer to blind-writer** — the phase would then depend on `views validate` being run separately, which no workflow guarantees.

### Finding G1 — why `input_model` is inert over MCP (root cause of WR-02)

`registry.list_mcp_tools()` computes `cap.input_model.model_json_schema()` (`registry.py:63`); `mcp/server.py:40-44` passes only `fn`, `name`, `description` to `app.add_tool`. FastMCP derives the advertised schema from the function signature, which is `def handler(**kwargs)` (`:31`) — an open object. Nothing anywhere calls `model_validate` on an MCP payload. `CardListInput`'s `extra="forbid"` is therefore decorative over MCP [VERIFIED: live code read].

This is a *one-hop* fix and it is the whole of GOV-01's MCP arm. The seam's own `model_validate` closes the enforcement gap even if `add_tool` cannot accept an explicit schema; passing the schema additionally closes the *discoverability* gap.

### Finding G2 — D-06 is half the size CONTEXT assumes

**14 of 28** capability input models already carry `extra="forbid"`, not one [VERIFIED: live introspection of `get_registry()`].

Already forbid (14): `ask.domain`, `bridge.detect`, `card.evaluate`, `curation.inspect`, `curation.review`, `curation.run`, `daily.inspect`, `daily.run`, `knowledge.card.list`, `research.inspect`, `research.review`, `research.run`, `research.score`, `research.search`, `workspace.validate`.

Needs forbid added (14): `graph.status`, `help.suggest`, `ingest.source`, `knowledge.card.archive`, `knowledge.card.create`, `knowledge.card.edit`, `knowledge.connection.add`, `knowledge.connection.list`, `knowledge.connection.remove`, `views.generate_data`, `workflow.status`, `workspace.init`, `workspace.status`, plus whichever record D-02 adds for `views validate`.

Note the second list is dominated by the **write** capabilities — the ones where an unexpected field is most dangerous. That is a useful ordering argument for the planner.

### Finding G3 — D-07 handler fit: 23/28 work today, 5 mismatch

Measured by comparing each `input_model`'s field names against its handler's signature [VERIFIED: `inspect.signature` over the live registry].

| Verdict | Count | Meaning |
|---------|-------|---------|
| `KWARGS-OK` | 18 | handler accepts `**kwargs`; `handler(**model.model_dump())` binds unconditionally |
| `EXACT-OK` | 5 | named params only, but field names == param names exactly (`graph.status`, `help.suggest`, `knowledge.card.list`, `views.generate_data`, `workspace.status`) |
| `MISMATCH` | 5 | would raise `TypeError` under the seam |

The five mismatches:

| Capability | Model field | Handler expects | Fix |
|------------|-------------|-----------------|-----|
| `knowledge.card.archive` | `workspace` | `workspace_root` | rename model field or add a marshalling shim |
| `knowledge.connection.list` | `workspace` | `workspace_root` | same |
| `knowledge.connection.remove` | `workspace` | `workspace_root` | same |
| `workflow.status` | `WorkflowRunInput` has `workflow_name`, `start_step` — **and no `workspace` field at all** | `workspace` | the model is simply the wrong model for this handler |
| `workspace.init` | `WorkspacePathInput` has `path` | `root`, `domain` | model does not describe the handler |

**The correlation is the finding.** The six capabilities not exposed over MCP are `knowledge.card.archive`, `knowledge.connection.list`, `knowledge.connection.remove`, `workflow.status`, `workspace.init`, `workspace.status` — and five of those six are exactly the five mismatches. Their `input_model`s have never been used to construct a call, so nothing ever noticed they were wrong. This is Pitfall 3 from the project research ("`input_model` is documentation not enforcement") captured as a measurement rather than an assertion, and it is the strongest single argument for D-05's no-allowlist stance: the allowlist would have been exactly these five, and they are wrong precisely because nobody ever looked.

### Finding G4 — `cli.py` has 25 handler call sites, not 3

`grep -c '\.handler(' src/construct/cli.py` → **25** [VERIFIED]. CONTEXT's D-07 names three (`:89`, `:107`, `:143`). The positional ones extend at least to `:224`, `:1294`, `:1333`, `:1351`, `:1420`, `:1448`, `:1466`, `:1484`; roughly a dozen already use `**handler_kwargs` or explicit keywords and will migrate trivially.

Four **non-CLI, non-MCP** in-repo callers also exist:

| Caller | Line | Disposition |
|--------|------|-------------|
| `ui/capability_runner.py` | `:130` — `cap.handler(**inputs)` | Streamlit page **stays** (D-13 keeps it); should route through the seam so form input is validated |
| `pipelines/workflow_runner.py` | `:201` — `step.handler(**kwargs)` | separate step abstraction; planner must confirm whether it shares the registry |
| `services/help.py` | `:141` — `cap.handler(workspace_id)` | **capability-to-capability positional call**; will break under a strict seam |
| `ui/gate_review.py` | `:259` | deleted by D-13 |

`services/help.py:141` deserves attention: `catalog.py:331` documents that `graph.status`'s handler is deliberately shaped so it "binds both the positional (`help.py:126` calls `handler(workspace_id)`) and keyword" forms. That accommodation is exactly the RT-03 debt D-07 retires, and retiring it changes an internal call path, not just a surface.

**Planner action:** budget GOV-01 against 25 + 4 = 29 call sites and 5 broken capabilities, not 3 call sites.

### Finding G5 — the RT-03 dual-mode shims, enumerated

`catalog.py` carries six shims of the form `if args: passthrough(*args, **kwargs) else: marshal-from-schema` [VERIFIED: `catalog.py:854-940`]:

| Shim | Capability | Mode |
|------|-----------|------|
| `_daily_run_shim` | `daily.run` | keyword-only guard (raises on positional) |
| `_daily_inspect_shim` | `daily.inspect` | keyword-only guard |
| `_create_card_shim` | `knowledge.card.create` | dual-mode + `_build_card_data` marshalling |
| `_edit_card_shim` | `knowledge.card.edit` | dual-mode + `_build_card_updates` marshalling |
| `_add_connection_shim` | `knowledge.connection.add` | dual-mode + enum coercion + `workspace`→`workspace_root` |
| `_ingest_source_shim` | `ingest.source` | dual-mode + `workspace`→`workspace_root` |

Under the seam every call takes the `else` branch, so the `if args:` branches become dead once the CLI is normalized — but **only** once. Retiring them before the CLI call sites are converted breaks `card create`, `card edit`, `connection add`, and `ingest source` at the CLI. Order matters: normalize `cli.py` first, then delete branches.

### Finding G6 — the decision-model shape, both graphs

`CurationProposal` (`curation_run.py:172-179`) is `{"extra": "forbid"}` with fields `kind`, `decision`, `payload` — **no id** [VERIFIED]. `_resolve_decisions` (`:777-796`) zips positionally and falls back to `entry.get("decision", "")` when the payload is short or absent — the D-10 defect, confirmed verbatim.

`research_run._resolve_decisions` (`:479-501`) is **worse in a different way**: it already supports a keyed mode, keyed on `entry["finding"]["url"]`, alongside the positional mode, alongside a no-payload mode — three shapes in one function, all with the same silent-default fallback. `url` is content-derived, may be `None`, and is not guaranteed unique across findings, which is a concrete demonstration of why D-09 chose opaque ids. Both functions must land the same treatment, and `research_run`'s url-keyed branch must be **removed**, not left as a compatible alternative — leaving it is the parity fork GOV-02 exists to close.

The gate queue is persisted as **plain dicts**, not model instances (both functions use `entry.get(...)`), which makes D-12's migrate-on-read injection easy and confirms Pitfall 4's mitigation.

### Finding G7 — `checkpoint_id` as ETag: verified on the pinned stack

Executed against `langgraph 1.2.9` / `langgraph-checkpoint-sqlite 3.1.0` with a minimal `interrupt()` graph over a real `SqliteSaver` [VERIFIED: live run]:

| Property D-11 needs | Result |
|---------------------|--------|
| Present while paused | yes — `1f189225-8588-647c-8001-78b7549b095e` |
| Stable across repeated `get_state` | **yes** |
| Stable across a separate connection / process | **yes** |
| Changes on `update_state` | **yes** |
| Changes after resume | **yes** |

The codebase already reads snapshots this way in four places (`curation_run.py:1172`, `:1229`, `:1278`, and `research_run.py`), so exposing the id costs one dict lookup per call site. [CITED: https://docs.langchain.com/oss/python/langgraph/checkpointers — `StateSnapshot.config` carries `thread_id` and `checkpoint_id`, and a `checkpoint_id` in the config selects a specific historical snapshot.]

That last documented property is a bonus for Phase 22: the same ETag can be replayed to `get_state` to fetch the exact snapshot the user was shown.

**Adjacent observation (not in scope):** the codebase detects interrupts with `"__interrupt__" in result` (`research_run.py:974`), the v1 form; the pinned LangGraph documents a v2 `result.interrupts` API and marks the dict key deprecated [CITED: https://docs.langchain.com/oss/python/langgraph/streaming]. Not this phase's problem — flagged so nobody "fixes" it mid-phase.

### Finding G8 — `gate_review.py`'s violations, confirmed

Every claim in D-13 verified in live code:

- Queue from session state with no run behind it — `if "gate_queue" not in st.session_state: st.session_state.gate_queue = []` (`:56-57`).
- Approval flips a session flag and writes a real audit event — `st.session_state.gate_queue[idx]["review_status"] = "approved"` followed by `_log_gate_event(workspace, "gate_review_approved", ...)` (`:151-160`), into the same `log/events.jsonl` that `curation_run._emit` appends to.
- Second canonical writer — `conn_cap.handler(workspace, ..., ConnectionType.parallels, ...)` (`:258-266`), hard-coded connection type, called **positionally**, bypassing every gate.

One extra defect worth recording in the deletion commit message: `_log_gate_event` computes `result = EventResult.success if "approved" in action else EventResult.success` (`:40`) — both branches are identical, so a *rejection* is written to the audit trail with `result=success`. A tautological ternary is about as literal an instance of T-15-14 as the codebase contains.

Reference set to remove is exactly two things: the file, and `streamlit_app.py:47` + its entry in the `st.navigation([home, runner, gates])` list at `:49`. No test imports it [VERIFIED: repo-wide grep].

### Finding G9 — the GOV-05 defect is in rendering and in a missing field

Two distinct problems, both verified:

1. **Degraded renders as success.** `success = result.status != "failed"` in the catalog's result adapter, then `cli.py:687-692` prints `✓ {message}` for anything with `success=True`. `_render_curation_result` does honestly print `status: degraded` first — so the human surface emits an honest status line and a dishonest verdict glyph in the same output block.
2. **Escalated renders not at all.** `escalated` appears in `curation_run.py` (state channel `:112`, apply node `:851`, `:860`, return `:876`) and **nowhere in `cli.py`** [VERIFIED: grep]. There is no bucket for it in `_render_curation_result` (`:661-678`).

Combined with the unconditional `gate_review_approved` emission documented in the Code Examples section, GOV-05 and D-16 together are: add a field to the renderers, split the count, give escalate its own event type, and make the approved event conditional on an actual write.

## Project Constraints (from AGENTS.md)

`./CLAUDE.md` does not exist; `./AGENTS.md` is the root project instruction file. Actionable directives:

| Directive | Source | Bearing on this phase |
|-----------|--------|----------------------|
| Use the repository-local `.venv/` for all Python runtime, CLI, tools, and tests | AGENTS.md § Workflow | Every command in plans must be `.venv/bin/python ...` |
| Run pytest as `.venv/bin/python -m pytest` from the repo root; **not** bare `pytest` | AGENTS.md § Workflow | Applies to every verification step |
| Refresh deps with `.venv/bin/python -m pip install -e '.[dev]'` | AGENTS.md § Workflow | Only if imports fail |
| Every Pydantic model sets `model_config = ConfigDict(extra="forbid")` | AGENTS.md § Pydantic Conventions | **Direct tension with D-03**, which relaxes the views models to `extra="ignore"`. D-03 is a deliberate, user-locked exception for a derived projection; the planner must record it as such rather than let a reviewer "restore convention". |
| `from __future__ import annotations` at the top of every module | AGENTS.md § Code Style | New modules (the seam) must include it |
| Type annotations on all signatures including `-> None` | AGENTS.md § Code Style | Applies to `registry.invoke` |
| Chain exceptions with `raise NewError(...) from exc`; convert third-party exceptions to domain errors at the boundary | AGENTS.md § Error Handling | The seam converts `pydantic.ValidationError` into a domain error — this is the boundary |
| CLI catches domain exceptions, emits `typer.echo(f"ERROR {exc}")`, then `raise typer.Exit(code=1)`; never let raw exceptions reach the user | AGENTS.md § Error Handling | Constrains how the seam's validation error surfaces on the CLI arm of D-08 |
| Validators raise `ValueError` with human-readable messages including examples | AGENTS.md § Pydantic Conventions | Applies to `proposal_id`'s validator (reuse `_validate_run_id`) |
| `test-ws/` are fixtures, not user data | AGENTS.md § Test workspaces | Safe to copy for round-trip measurement; **never generate into in place** (the existing fixture helper copies first) |

### ⚠ Stale directives that contradict this phase

Two AGENTS.md guardrails are obsolete and, read literally, forbid the entire phase:

- *"Do not modify `archive/v01-python/`, `src/`, or `tests/` unless explicitly resuming the Python approach."*
- *"**No active GSD.** `.planning/` was archived … Do not recreate GSD state until CONSTRUCT03 implementation begins."*

Both are contradicted by the current state of the repository: `.planning/` is the live GSD tree, `STATE.md` records seven shipped v0.3 phases plus v0.4.1, and the whole v0.5 milestone is Python-runtime work in `src/`. The Python approach **was** explicitly resumed. **Planner action:** do not treat these as blockers, and consider a small doc-truth task to correct them — this phase is about contracts telling the truth, and the project's own instruction file currently does not.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `"__interrupt__" in result` dict-key interrupt detection | `result.interrupts` with `version="v2"` | LangGraph 1.x | Codebase uses the deprecated form (`research_run.py:974`). **Out of scope** — noted so nobody changes it opportunistically. |
| Pydantic v1 `class Config` | Pydantic v2 `model_config = ConfigDict(...)` | Pydantic 2.0 | Codebase is fully v2; `CurationProposal` uses the plain-dict form `{"extra": "forbid"}` while views models use `ConfigDict(...)`. Both are valid v2; the inconsistency is cosmetic. |
| Hand-written MCP tool definitions | Registry-driven auto-generation | Phase 6-era | Already done and is this codebase's genuine architectural strength — 52 lines generate every tool. GOV-01 must preserve it; adding a capability must never require editing `mcp/server.py`. |

**Deprecated / outdated in-repo:**

- `views/design-example/` — a design prototype, superseded by the scaffold template SPA. Grepping it for field usage returns nothing relevant; do not use it to justify a contract decision.
- The `_FILE_MODEL_MAP` / `_PER_WS_FILES` adapter tables — deleted by D-01.
- `ui/gate_review.py` — deleted by D-13.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `FastMCP.add_tool` in the pinned `mcp` package accepts an explicit input-schema override | Pattern 2 | If it does not, the advertised MCP schema stays `**kwargs`-derived. **Enforcement is unaffected** (the seam validates at call time), but GOV-01's "one seam, same schema on both surfaces" claim would be true for behaviour and false for discovery. Planner should verify with `inspect.signature(FastMCP.add_tool)` before writing the task. |
| A2 | `pipelines/workflow_runner.py:201`'s `step.handler` refers to the same capability registry rather than a separate step abstraction | Finding G4 | If separate, it is out of scope and the call-site budget drops by one; if shared, it is a fourth surface that must route through the seam. One grep resolves it. |
| A3 | The 532-test suite currently passes on `dev-v05` | Validation Architecture | D-05's "anything the suite surfaces is fixed in-phase" presumes a green baseline. If it is not green, the phase inherits unrelated failures. Baseline must be captured before Wave 1. |
| A4 | No consumer other than `views validate`, the SPA, and `research_run` reads `views/build/data/*.json` field names | Finding V2 | A missed consumer breaks on the rename. Greps covered `src/`, `tests/`, and the scaffold template; a user's own local SPA fork would not be visible. |
| A5 | `<ws>/curation-history.json` genuinely has no contract model anywhere | Finding V1 | If one exists elsewhere it should be wired in rather than a new one written. |

## Open Questions (ALL RESOLVED)

> **Resolution status (added at `/gsd-plan-phase 18`, after this research was written):**
>
> | OQ | Resolved by | Outcome |
> |----|-------------|---------|
> | **OQ-A** | CONTEXT.md **D-17** (user decision at the plan-phase research gate) | **Research's lean was NOT taken.** Instead of tolerant aliases, the **Python emitter shape is canonical**; both the views model (plan 18-04 T2) and the SPA reader (plan 18-05 T2) conform to it. This removes the Phase 23 convergence deferral the tolerant option would have created. |
> | **OQ-B** | CONTEXT.md **D-18** (user decision) | **Both** files get contract models — `stats.json` *and* `curation-history.json` (plan 18-04 T1), not just the stable-shaped one. Related: **D-19** restates D-04's cardinality as `4 + 6·N_workspaces + 1`. |
> | **OQ-C** | Plan **18-05 T1** | Recommendation taken — the writer keeps validating, via direct `model_validate` of the raw dict against the conformed model, preserving the "a run that rejected any file did not produce the build" invariant. |
> | **OQ-D** | Plan **18-03 T2** | Recommendation taken — routed through `registry.invoke("graph.status", {"workspace": workspace_id})`, inside the widened call-site budget (25 `cli.py` sites + 3 external callers, not D-07's assumed 3). |
>
> The original text of each question is preserved below unedited, as the record of what was open at
> research time.

1. **OQ-A — What is `events.json`'s contract, given four incompatible shapes?** (blocks the `events.json` half of VFIX-01) — **RESOLVED by D-17; research's tolerant-alias lean was not taken.**
   - What we know: four shapes exist and are enumerated in Finding V3; `parse_events` renames nothing; the SPA matches neither the current Python emitter nor the legacy fixtures.
   - What's unclear: D-01 says "conform to the bytes", but the bytes differ by emitter. Conforming to the fixtures codifies legacy data; conforming to the Python emitter breaks against every existing workspace log; conforming to the SPA means changing the *emitter*, which is a canonical-write change and squarely inside ING-02's territory rather than outside it.
   - Recommendation: make this its own named decision alongside D-01, decided in `/gsd-plan-phase` before Wave 1 starts. Research's lean is a **tolerant `EventRecord` with aliases covering shapes #1 and #2 plus `extra="ignore"`**, combined with a separate, explicitly-deferred item to converge emitter and SPA in Phase 23 when the browse surface is built. That satisfies VFIX-01 (validate accepts what generate writes) without silently blessing legacy data as the forward contract.

2. **OQ-B — Do `<ws>/stats.json` and `<ws>/curation-history.json` get contract models in this phase?** — **RESOLVED by D-18: both get models, not just `stats.json`.**
   - What we know: they are written with no validation at all, and `views validate` does not look at them (Finding V1, V6).
   - What's unclear: the "8 files" phrasing in ROADMAP/CONTEXT implicitly excludes them, but D-04's own argument ("the guard is the only drift detector") applies most strongly to files with no gate whatsoever.
   - Recommendation: include `<ws>/stats.json` (it has a stable computed shape from `compute_stats.compute_workspace`); defer `curation-history.json` if its shape is not yet stable. Either way, state the choice — do not let the phrase decide.

3. **OQ-C — Does `views generate` keep validating before writing?** — **RESOLVED in plan 18-05 T1: yes, via direct `model_validate`.**
   - What we know: deleting the adapter tables per D-01 removes `_validate_file_data`'s only input (Finding V6).
   - Recommendation: replace it with a direct `model_validate` of the raw dict against the conformed model. After D-01 the adapter is the identity function, so this is nearly free and preserves the "a run that rejected any file did not produce the build" invariant at `generate.py:394-423`, which several existing tests depend on.

4. **OQ-D — How does `services/help.py:141` call `graph.status` under a strict seam?** — **RESOLVED in plan 18-03 T2: via `registry.invoke`.**
   - What we know: it calls `cap.handler(workspace_id)` positionally, and `catalog.py:331` documents the handler as deliberately shaped to accept both forms.
   - Recommendation: route it through `registry.invoke("graph.status", {"workspace": workspace_id})`. Small, but it is an internal caller that D-07's "three CLI call sites" framing does not cover.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (repo `.venv`) | everything | ✓ | 3.14 dev / `>=3.11` required | — |
| pydantic | all contract models | ✓ | 2.13.3 | — |
| langgraph | D-11 ETag, review graphs | ✓ | 1.2.9 | — |
| langgraph-checkpoint-sqlite | checkpoint state | ✓ | 3.1.0 | — |
| pytest | all guards | ✓ | 9.0.3 | — |
| typer | CLI surface | ✓ | 0.24.1 | — |
| mcp (FastMCP) | MCP surface + D-08 | ✓ | importable | — |
| streamlit | D-13 deletion target | ✓ | declared `>=1.35` | not needed to *delete* a page |
| `construct` CLI entry point | D-08 real-process arm | ✓ | `.venv/bin/python -m construct.cli` verified working | — |
| Populated views fixture | D-04 non-vacuous guard | ✓ | `tests/fixtures/v02/multi-domain-medium` | `test-ws/paskunas` (also verified working) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

All availability rows were confirmed by executing the tool or importing the module in this session [VERIFIED: live runs].

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = [".", "src"]`) |
| Quick run command | `.venv/bin/python -m pytest tests/contract tests/unit -q` (~293 tests) |
| Full suite command | `.venv/bin/python -m pytest -q` (532 tests collected) |

Current collection by directory [VERIFIED: `pytest --collect-only`]: `contract` 171, `llm` 128, `unit` 122, `integration` 51, `search` 25, `pipelines` 19, `bridge` 16. CONTEXT cites "the 515-test suite"; the actual figure is **532**.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| VFIX-01 | generate→validate round-trips on a **populated** root; all 8 slots pass; record lists non-empty; file cardinality matches `4+6N+1` | integration | `.venv/bin/python -m pytest tests/integration/test_views_generate.py -x` | ✅ (guard replaces `:285`) |
| VFIX-01 | conformed models still reject a genuinely malformed payload (`extra="ignore"` did not become "accept anything") | contract | `.venv/bin/python -m pytest tests/contract/test_views_contracts.py -x` | ✅ |
| GOV-01 | same `(capability, payload)` → identical result on real CLI process and real MCP dispatch | integration | `.venv/bin/python -m pytest tests/integration/test_surface_parity.py -x` | ❌ Wave 0 |
| GOV-01 | an unknown field is rejected on **both** surfaces with the same reason | integration | same file | ❌ Wave 0 |
| GOV-01 | every registered capability's model fields bind to its handler (the Finding G3 audit, as a permanent guard) | contract | `.venv/bin/python -m pytest tests/contract/test_capability_seam.py -x` | ❌ Wave 0 |
| GOV-01 | all 28 input models carry `extra="forbid"` (cardinality, not membership) | contract | same file | ❌ Wave 0 |
| GOV-02 | incomplete decision map → zero canonical writes, run still paused, uncovered ids named | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k decision -x` | ✅ (extend) |
| GOV-02 | legacy id-less checkpoint migrates on read and still requires a complete map | llm | same file | ✅ (extend) |
| GOV-03 | resume with a stale `checkpoint_id` → rejected, zero writes | llm | `.venv/bin/python -m pytest tests/llm/test_curation_run.py -k etag -x` | ✅ (extend) |
| GOV-04 | no canonical writer reachable outside apply nodes (source-level guard, in the shape of `test_gate_review_is_interrupt_only` at `test_research_run.py:758`) | llm | `.venv/bin/python -m pytest tests/llm/test_research_run.py -k interrupt_only -x` | ✅ (extend) |
| GOV-04 | Streamlit app still starts with the page removed | contract | import-level check of `streamlit_app` | ❌ Wave 0 |
| GOV-04 | no `gate_review_approved` emitted when the underlying write failed or was a no-op | llm | `tests/llm/test_curation_run.py -k event` | ✅ (extend) |
| GOV-05 | degraded run reports degraded on CLI human output, CLI `--json`, and MCP result — table-driven, one row per surface | integration | `.venv/bin/python -m pytest tests/integration/test_surface_honesty.py -x` | ❌ Wave 0 |
| GOV-05 | escalated items appear in their own bucket on every surface and never in an applied/success count | integration | same file | ❌ Wave 0 |
| D-15 | degraded `curation.run` still exits 0 (the Phase 11 contract is *preserved*, not changed) | integration | same file | ❌ Wave 0 — **regression guard, add it** |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/contract tests/unit -q`
- **Per wave merge:** `.venv/bin/python -m pytest -q`
- **Phase gate:** full 532-test suite green before `/gsd-verify-work`
- **Before Wave 1 starts:** capture the baseline (assumption A3) — D-05's no-allowlist stance requires distinguishing failures this phase caused from failures it inherited.

### Wave 0 Gaps

- [ ] `tests/integration/test_surface_parity.py` — GOV-01 differential CLI↔MCP (needs a `subprocess` helper for the real-CLI arm per Pitfall 5)
- [ ] `tests/contract/test_capability_seam.py` — GOV-01 model↔handler binding audit + `extra="forbid"` cardinality
- [ ] `tests/integration/test_surface_honesty.py` — GOV-05 table-driven degraded/escalated across surfaces, plus the D-15 exit-code regression guard
- [ ] Fixture: a `curation.run` forced degraded and a run with an escalated item (GOV-05 needs both; neither exists today)
- [ ] Fixture: a pre-migration id-less checkpoint (GOV-02/D-12)
- [ ] No framework install needed — pytest 9.0.3 present

## Security Domain

`security_enforcement` is not set in `.planning/config.json`, so it is enabled by default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local-first, single-user, no auth surface in v0.5 Phase 18 |
| V3 Session Management | no | No sessions. (Note: `gate_review.py`'s misuse of Streamlit `session_state` as a *queue* is a correctness defect, not a session-security one.) |
| V4 Access Control | **yes** | GOV-04 is an access-control invariant in disguise: canonical writes must be reachable only from apply nodes downstream of `interrupt()`. `gate_review.py` is a privilege-escalation-shaped bug — a surface performing a write it was never authorized by a gate to perform. |
| V5 Input Validation | **yes — the phase's centre of gravity** | `cap.input_model.model_validate` at the seam; `extra="forbid"` on all 28 models; `_validate_run_id`-style guards for `proposal_id` |
| V6 Cryptography | no | `uuid4` for `proposal_id` is an identifier, not a secret. Do not reach for `secrets` or a hash — D-09 requires opacity, not unpredictability. |
| V7 Error Handling & Logging | **yes** | The entire T-15-14 "audit-trail-that-lies" class: `gate_review_approved` without a write, `gate_review_rejected` for an escalation, `EventResult.success` on both ternary branches. An audit log that records events that did not happen is an ASVS V7 defect, not merely a UX one. |
| V12 File Resources | **yes (adjacent)** | `install_root_error` (`generate.py:175-194`) already guards agent-supplied paths; D-02 must preserve it when `views validate` becomes a registry capability, because registration exposes an `install_root` parameter to MCP. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Agent-supplied payload smuggles unexpected fields into a handler | Tampering | `extra="forbid"` **enforced at the seam** — the whole of GOV-01. Today it is declared but not enforced (Finding G1). |
| Agent-supplied path escapes the install root and scaffolds/overwrites elsewhere | Tampering | `install_root_error` marker check; preserve under D-02 |
| Decision payload misapplied to a queue that changed (confused deputy) | Tampering / Elevation | D-11 checkpoint-id ETag, verified (Finding G7) |
| Short/absent decision payload silently performs a write the user never approved | Elevation of Privilege | D-10 complete-coverage rejection — this is the single most security-relevant item in the phase |
| Second write path bypasses the review gate entirely | Elevation of Privilege | D-13 deletion + a source-level guard test |
| Audit trail records approvals for actions never taken | Repudiation | D-16 conditional emission + separate escalate event type |
| Degraded outcome reported as clean success | Repudiation | GOV-05 cross-surface rendering test |
| Path/identifier injection via `proposal_id` from an untrusted resume payload | Injection | Reuse `_validate_run_id`'s kebab-case guard pattern (`curation_run.py:64-77`), written for precisely this reason |

**Note on D-02's exclusions:** CONTEXT's decision to keep `spike run --tool-path` out of the registry is a sound security call and should not be revisited opportunistically — registering it would expose an arbitrary-executable parameter to MCP and, later, HTTP.

## Sources

### Primary (HIGH confidence)

- Live repository code, read directly: `src/construct/views/models.py`, `views/generate.py`, `views/lib/parse_*.py`, `capabilities/registry.py`, `capabilities/catalog.py`, `mcp/server.py`, `cli.py`, `llm/curation_run.py`, `llm/research_run.py`, `services/event_log.py`, `schemas/config.py`, `ui/gate_review.py`, `ui/streamlit_app.py`, `ui/capability_runner.py`
- Live execution: `construct views generate` + `construct views validate` round trip on a copy of `test-ws/paskunas`
- Live execution: registry introspection over all 28 capabilities (`model_fields` × `inspect.signature`)
- Live execution: LangGraph `checkpoint_id` ETag behaviour on a real `SqliteSaver` interrupt graph
- Live execution: `pytest --collect-only` (532 tests), `importlib.metadata` version queries
- Repo-wide greps for reference sets (`gate_review`, `.handler(`, `views.models`, SPA field names)

### Secondary (MEDIUM confidence)

- [CITED: https://docs.langchain.com/oss/python/langgraph/checkpointers] — `StateSnapshot` fields; `checkpoint_id` in config selects a historical snapshot
- [CITED: https://docs.langchain.com/oss/python/langgraph/add-memory] — `get_state` config shape
- [CITED: https://docs.langchain.com/oss/python/langgraph/streaming] — interrupts v1 vs v2
- `.planning/` documents: `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`, `18-CONTEXT.md`
- `AGENTS.md` (root) — project conventions and the stale guardrails noted above

### Tertiary (LOW confidence)

- A1 (`FastMCP.add_tool` schema-override parameter) — not verified in this session; flagged in the Assumptions Log

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — nothing new is installed; every version read from the live interpreter
- Byte-contract divergence (VFIX-01): **HIGH** — measured by execution, not inference; the complete field map came from introspecting written bytes against `model_fields`
- `events.json` resolution: **LOW** — the *facts* are HIGH confidence (four shapes, all located in source) but the correct *decision* is genuinely open; raised as OQ-A rather than recommended as settled
- Seam sizing (GOV-01, D-06, D-07): **HIGH** — every count produced by introspecting the live registry
- Checkpoint ETag (D-11): **HIGH** — empirically verified on the exact pinned versions
- `gate_review.py` disposition (D-13): **HIGH** — every claim in the decision confirmed in live code, plus one additional defect found
- GOV-05 defect location: **HIGH** — traced end to end from result adapter to renderer
- Pitfalls: **HIGH** for those derived from measurement (1, 2, 4, 6, 7, 8); **MEDIUM** for 3 and 5, which are forward-looking risks rather than observed failures

**Research date:** 2026-07-26
**Valid until:** 2026-08-25 (30 days) — findings are keyed to a specific commit on `dev-v05`; the measured counts (532 tests, 25 call sites, 14/28 forbid, 23/28 handler fit, 5-of-8 validate failures) should be re-run if the branch moves substantially before planning.
