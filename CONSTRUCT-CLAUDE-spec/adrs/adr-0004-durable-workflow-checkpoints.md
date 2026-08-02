# ADR-0004: Durable Workflow Checkpoints as Sanctioned Orchestration State

**Status:** Accepted — extended 2026-08-03 (Phase 19 / D-14) with the [concurrency contract](#concurrency-contract-extension--phase-19-2026-08-03); the original decision is unchanged
**Date:** 2026-07-19
**Deciders:** ;-)mab
**Context:** The canonical spec documents assert that no database owns part of the truth and that the workspace carries no derived state that is required. Phase 10 (v0.4) shipped LangGraph `SqliteSaver` checkpointers that write `.construct/workflow/research-run.sqlite` and `.construct/workflow/curation-run.sqlite`, and those files hold pending human-review decisions that no layer-1 artifact contains. The spec and the code disagree. This ADR records which one is correct and scopes the rebuild guarantee accordingly, so that v0.5 UI planning can design resumable gate state against a written invariant rather than inferring it from source.
**Related:** [`adr-0001-claude-native-approach.md`](adr-0001-claude-native-approach.md), [`adr-0003-v03-pipeline-v04-ui.md`](adr-0003-v03-pipeline-v04-ui.md), [`../nfrs.md`](../nfrs.md), [`../architecture-overview.md`](../architecture-overview.md)

---

## Context

Two canonical claims are in tension with shipped v0.4 behavior.

`nfrs.md` §2 states the rebuild guarantee as *"Workspace files are self-contained — no hidden state"*, implemented by *"No databases, no caches, no derived state that's required"*. `architecture-overview.md` §8.2 rejects *"Add a database that owns part of the truth"*.

Phase 10 shipped two LangGraph `SqliteSaver` checkpointers:

- `src/construct/llm/research_run.py:879-894` (`_open_checkpointer`) opens `SqliteSaver(sqlite3.connect(str(db), check_same_thread=False))` over `.construct/workflow/research-run.sqlite`, creating the parent directory with `mkdir(parents=True, exist_ok=True)`.
- `src/construct/llm/curation_run.py:277-291` is the structurally identical sibling over `.construct/workflow/curation-run.sqlite`.

The question is whether these files merely hold resumable plumbing (harmless, and compatible with the existing claims) or whether they hold facts that exist nowhere else. The control flow answers it concretely:

- `research_run.py:437-449` — `gate_review` contains **only** `interrupt(...)`. Its docstring is explicit that no writes, no event emission, and no non-idempotent prep live in the node, because the interrupted node re-executes top-to-bottom on resume.
- `research_run.py:745` — `update_seeds_and_log` is a **separate node defined after** `gate_review`, and it runs only once the graph resumes.
- `research_run.py:786`, `:794`, `:808`, `:814`, `:820` — **every** `append_event` call in the module sits inside `update_seeds_and_log`. There is no other call site.

The consequence is factual, not speculative: while a run sits at `awaiting_review`, **zero** events have been appended to `log/events.jsonl`. The scored findings and the per-finding default decisions in `gate_queue` exist **only** inside the sqlite checkpoint. Deleting the file at that moment does not lose knowledge — but it does lose work that layer 1 cannot reproduce.

So the drift is real, and it is the spec that is wrong, not the code.

---

## Decision

**`.construct/workflow/*.sqlite` is intentional durable state.** It holds **pending human-review** decisions and their scored findings, and that content is **not reconstructible** from layer 1.

It sits **outside** the layer 1 / layer 2 / layer 3 model rather than violating it. `architecture-overview.md` §4 scopes each of its four invariants explicitly *to layer 2*; workflow orchestration state is not layer 2, so the invariants are neither contradicted nor extended by this decision.

**The rebuild guarantee is scoped to knowledge state.** The guarantee that the workspace is self-contained and reproducible applies to `cards/`, `refs/`, `connections.json`, `search-seeds.json`, `log/events.jsonl`, and `digests/`. Those remain markdown- and file-canonical, with no database owning any part of them.

**Blast radius, stated exactly.** Losing a checkpoint file costs a completed search-and-scoring cycle and any decisions entered but not yet resumed. It never corrupts and never loses canonical knowledge; the affected run is simply re-run from the start. No claim is made here that the file is protected, duplicated, or restorable — it is not, and the honest scope of the loss is the whole of the claim.

**One decision covers both checkpointers.** `research-run.sqlite` and `curation-run.sqlite` are the identical `SqliteSaver(sqlite3.connect(..., check_same_thread=False))` pattern over `.construct/workflow/{name}-run.sqlite`. They are governed as one artifact class, not two special cases.

**The directory is optional.** `.construct/workflow/` is created lazily at first checkpointer construction, is **not** listed in `REQUIRED_PATHS` (`src/construct/schemas/workspace.py:14`), and is not scaffolded. A valid workspace may legitimately have no such directory at all.

---

## Options Considered

### Option A: Record the checkpointer as sanctioned durable state and scope the rebuild guarantee to knowledge state (this decision)

Accept that workflow orchestration state is durable and non-reconstructible, name it as a distinct artifact class, and narrow the rebuild guarantee's wording so it makes a true claim about knowledge state instead of a false claim about the whole workspace.

**Pros:**
- The written record matches shipped behavior, so a v0.5 planner designing resumable gate-state UI reads one specific answer instead of reverse-engineering `research_run.py`
- Preserves the architecturally load-bearing part of the original claim — knowledge stays markdown-canonical and portable
- Requires no runtime change, and therefore cannot regress v0.4 behavior
- Names the blast radius, which is what a user actually needs to know before copying or pruning a workspace

**Cons:**
- The rebuild guarantee becomes a scoped claim rather than an absolute one, which is a genuinely weaker and less quotable property
- Introduces a fourth artifact class that every future workspace-contract reader must learn

### Option B: Make the checkpoint reconstructible by emitting scored findings to `log/events.jsonl` before the gate pauses

Move event emission ahead of the interrupt so that a lost checkpoint can be rebuilt from the append-only log, restoring the absolute rebuild guarantee.

**Pros:**
- Would preserve the original unqualified claim without rewording it
- The audit log would show research activity even for runs abandoned at the gate

**Cons:**
- Changes runtime behavior, which v0.4.1 lists as Out of Scope
- Writes unreviewed findings into the audit log, weakening the RSCH-03 property that the log records approved outcomes rather than proposals
- `gate_review` is documented as re-executing on resume, so pre-gate emission would need separate idempotency machinery to avoid double-firing

### Option C: Drop the durable checkpointer and hold gate state in memory

Remove `SqliteSaver` entirely and keep the pending review in process memory for the lifetime of a single invocation.

**Pros:**
- Restores the literal truth of "no databases" with no rewording at all

**Cons:**
- Removes the resumable human-review capability that Phase 10 shipped, regressing v0.4
- Breaks cross-process resume, which is the entire reason the connection is held open rather than scoped to a context manager
- Trades a working feature for the tidiness of a sentence in a spec document

---

## Consequences

### Positive

- v0.5 can design a resumable gate-state UI against a recorded invariant, rather than against an inference drawn from reading `research_run.py` node ordering.
- The database anti-pattern in `architecture-overview.md` §8.2 becomes enforceable again, because it now has exactly one named exception instead of one silent violation.
- The blast radius of losing `.construct/workflow/` is written down, so pruning or copying a workspace is an informed act.

### Negative

- Workspace portability is now scoped — copying only the knowledge files carries no in-flight reviews across, so a mid-gate run does not survive the move — addressed by naming the bounded cost (one search-and-scoring cycle plus any entered decisions) rather than leaving the reader to discover it.
- The absolute "no hidden state" framing is no longer literally true and must be reworded wherever it appears — addressed by the paired `nfrs.md` §2 edits that accompany this ADR.

### Neutral

- Adds a fourth artifact class to the workspace contract alongside canonical, derived, and support artifacts.
- The `.construct/workflow/` directory's absence remains a normal condition, so no validator or scaffolder gains a new requirement.

---

## Durable orchestration state (artifact class)

This section defines the artifact class named by this decision. It is the definition the workspace contract consumes.

**Class name:** `durable orchestration state`.

**Qualifying test.** An artifact belongs to this class when all three hold:

1. It holds pending decisions or in-flight workflow position that is **not reconstructible** from layer 1.
2. It is **not** canonical knowledge — losing it never invalidates a card, ref, connection, or event.
3. It is **not** derived from canonical knowledge — it cannot be regenerated by re-running a pipeline over existing files.

| Path | Class | Role |
|---|---|---|
| `.construct/workflow/*.sqlite` | durable orchestration state | LangGraph checkpoints holding resumable run position and pending human-review decisions |

`.construct/workflow/` is created lazily at first checkpointer construction, is not in `REQUIRED_PATHS`, and may legitimately be absent from a valid workspace.

**Why it fits neither existing class.** The Support class preamble states that support artifacts *"do not define workspace truth"* — false of a checkpoint holding the only copy of pending decisions. The Derived class asserts that derived artifacts *"must never be treated as canonical graph inputs"* and are generated from source-of-truth files — also false, since the checkpoint is generated from nothing on disk and is the sole input on resume. A third framing was required.

---

## Concurrency contract (extension — Phase 19, 2026-08-03)

This section extends the decision above rather than reversing any part of it. It exists because Phase 19 (HTTP-06) makes a browser-spawned run and a CLI resume act on the **same** checkpoint file. Until that was possible, concurrent access to `.construct/workflow/*.sqlite` was theoretical and the original decision could stay silent on it. It is now operative, so the contract is written down — and, more to the point, the half that is *not* guaranteed is written down too.

### What was found (OQ-4)

The premise the phase opened with was false, and the measurement matters more than the preference.

`SqliteSaver.setup()` already executes `PRAGMA journal_mode=WAL` as the first statement of its own `executescript`. WAL is recorded in the database header, so it persists for the file rather than for the connection that set it. Separately, Python's `sqlite3.connect()` already defaults to `timeout=5.0`, i.e. a 5 000 ms busy timeout.

So the preferred arrangement — WAL, a busy timeout, no locking — was **already in force by library default and stdlib default, not by decision**. That is the worst state a contract can occupy: correct today, silently reversible by a dependency bump, with no test that would notice. A langgraph release that drops its own pragma would have reverted the concurrency guarantee with every test still green.

### The contract (D-14)

Every checkpointer connection in this repo sets both settings **itself**, in `_open_checkpointer` in `src/construct/llm/curation_run.py` and its twin in `src/construct/llm/research_run.py`:

| Setting | Value | Declared by |
|---|---|---|
| `journal_mode` | `WAL` | `conn.execute("PRAGMA journal_mode=WAL")` on the connection, before the `SqliteSaver` is constructed |
| `busy_timeout` | `CHECKPOINT_BUSY_TIMEOUT_MS` — declared as `30_000` ms in both modules | `timeout=CHECKPOINT_BUSY_TIMEOUT_MS / 1000` passed to `sqlite3.connect` |
| locking | none | no lockfile, no mutex, no single-flight gate |

Under WAL, concurrent readers never block, and a writer that meets a held write lock **waits** rather than erroring.

`CHECKPOINT_BUSY_TIMEOUT_MS` is the single authority for the timeout; this ADR names the constant rather than restating its value in prose, so the document cannot drift from the code. The value was raised from the inherited 5 000 ms because a curation resume that writes many cards holds the write lock for an interval this codebase has not bounded, and a too-short timeout surfaces mid-resume as `database is locked` — the exact failure OQ-4 exists to prevent. **It is a reasoned estimate, not a measurement:** the realistic upper bound of a resume's write transaction was not established, and calling it measured would be the kind of false precision this ADR set is written to avoid.

**The pin.** `tests/llm/test_checkpoint_concurrency.py` reads both PRAGMAs back from a **live** checkpointer connection and asserts `journal_mode` is `wal` and `busy_timeout` equals `CHECKPOINT_BUSY_TIMEOUT_MS` — for exact equality, not as a lower bound, so a silent downgrade to the stdlib default fails rather than passing. It also asserts that a second, independently opened connection to the same file reports `wal`, which is what makes the mode meaningful across processes. Without this file the settings would be indistinguishable from the accident they replaced.

### The limitation: there is no cross-process mutual exclusion

Stated plainly, because implying it away is the failure mode this ADR set exists to prevent.

`SqliteSaver.__init__` holds a `threading.Lock` that is acquired on every `cursor()`. That lock serializes writers **within one process only**. Two processes — a server-spawned run and a CLI resume — construct two `SqliteSaver` instances and therefore share **no lock at all**. There is no cross-process mutual exclusion, and none is being added.

WAL plus a busy timeout is not a substitute for one. It makes a writer wait instead of erroring; it does not make two resumes take turns semantically.

### Arbitration: the checkpoint-id ETag, not a lock

Two racing resumes are already decided correctly by the Phase 18 D-11 checkpoint-id ETag. Every resume is a conditional request carrying the `checkpoint_id` it read; the loser's id no longer matches the persisted checkpoint, so it is **rejected with zero canonical writes**. Rejecting the second resume is the right outcome, not a degradation — the losing caller decided against state that no longer exists.

Two alternatives were rejected:

- **A server-held single-flight lock.** Its guarantee would be one-sided: a CLI resume running outside the server cannot see the lock, so the protection would hold only for callers who did not need it. A guarantee that silently does not apply to half its callers is worse than a stated absence.
- **A lockfile.** Stale-lock recovery introduces a failure mode whose symptom is a **permanently un-resumable run** — trading a rare, already-arbitrated race for a durable way to lose access to pending review decisions that exist nowhere else (see the blast radius above).

### Scope

This extension is written for the surface Phase 19 opens. HTTP-06 makes a browser-spawned run and a CLI resume write the same checkpoint database, which is what turned OQ-4 from a hypothetical into a contract that has to be stated. Nothing above changes the artifact class, the rebuild guarantee's scope, or the blast radius recorded earlier in this ADR.

---

## Relationship to prior ADRs

**ADR-0001 (Claude-native approach) is preserved, not retracted.** Knowledge remains markdown-canonical and portable: cards, refs, connections, seeds, events, and digests are files, and no database owns any of them. This ADR **scopes** that claim to knowledge state; it does not weaken the principle that markdown is the truth.

**ADR-0004 is downstream of ADR-0003 §A.3.** Amendment A.3 adopted LangGraph as the LLM orchestration layer. A durable checkpointer is a direct consequence of that choice — a graph with a human-in-the-loop `interrupt` needs somewhere to hold its position — so this decision follows from A.3 rather than competing with it.

**Why a new ADR rather than an Amendment C to ADR-0003.** Discoverability: a v0.5 planner scanning `adrs/` must be able to find this decision by title, and `adrs/` has no README or index, so a decision buried in an amendment block of an unrelated ADR is effectively unfindable.

**Discharge of Phase 10 D-02.** Phase 10 recorded a scope exception for the `SqliteSaver` checkpointer and left a deferred action — *"update `REQUIREMENTS.md` Out-of-Scope to record this carve-out"* — which was never executed. **This ADR discharges that action.** It also supersedes D-02's framing: D-02 described the store as holding *"ONLY resumable LangGraph checkpoint state"* with the SOT *"stays file-based"*, which understated the case, because it did not recognise that pending gate decisions exist nowhere else while a run is paused. The stronger non-reconstructibility claim recorded here replaces it. The original record is cited read-only at [`.planning/milestones/v0.4-phases/10-durable-human-review-research-run/10-CONTEXT.md`](../../.planning/milestones/v0.4-phases/10-durable-human-review-research-run/10-CONTEXT.md) and is deliberately left unedited — that archived audit trail is what surfaced this drift, and its integrity outweighs its consistency with today's decision.
