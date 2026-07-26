# Phase 18: Contract & Governance Foundations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-26
**Phase:** 18-Contract & Governance Foundations
**Areas discussed:** Views byte contract, Invocation seam, Decision model, Surface honesty

---

## Views byte contract (VFIX-01)

### Q1 — How should the views byte contract be reconciled?

| Option | Description | Selected |
|--------|-------------|----------|
| Conform models to bytes | Research option (i). Widen `views/models.py` to the raw parser shapes, drop the adapter tables. SPA unaffected, existing builds become valid. Looks like an ING-02 reversal and must be recorded. | |
| Share the adapter | Research option (iii). `views validate` applies the generator's adapter before validating. No breakage, but validates a projection of the file rather than the file. | |
| You decide | Take research's recommendation and record the ING-02 tension. | ✓ |

**User's choice:** You decide → option (i) taken.
**Notes:** ROADMAP explicitly names this as the decision that must be recorded rather than slipped in.

### Q2 — Does `views validate` become a registry capability in Phase 18, or later?

| Option | Description | Selected |
|--------|-------------|----------|
| Promote it in Phase 18 | Nearly free while the byte fix is open; closes half of RT-01/RT-02, retires adr-0005's registry-holdout note, Phase 19's adapter gets it for nothing. | ✓ |
| Leave it to Phase 19 | HTTP-02's "the registry is the HTTP surface" rule forces it there anyway; keeps Phase 18 to its six requirements. | |
| You decide | — | |

**User's choice:** Promote it in Phase 18.

### Q3 — What must the replacement round-trip guard assert so it can't pass vacuously?

| Option | Description | Selected |
|--------|-------------|----------|
| Named 8 + cardinality | Enumerate all 8 files by name, assert exists/non-empty/validates, assert count == 8. The WR-01 lesson applied. | |
| Glob and validate all | Glob whatever was written, assert ≥1 file and all validate. Simpler, but green if generate silently writes three files. | |
| You decide | — | ✓ |

**User's choice:** You decide → named 8 + cardinality taken.
**Notes:** Reinforced by the Q4 answer — with `extra="ignore"`, this guard becomes the only drift detector, so the strict form was taken rather than the convenient one.

### Q4 — Should the conformed models keep `extra="forbid"`?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep extra=forbid | Parser field additions fail loudly; catches the next fork. Two-file change for any addition, deliberately. | |
| Relax to extra=ignore | Models become a floor, not an exact description. Parser additions don't break validate or existing builds. Gives up the model-level drift detector. | ✓ |
| You decide | — | |

**User's choice:** Relax to `extra="ignore"`.
**Notes:** Claude flagged the coupling to Q3 at the time — the relaxation moves all drift-detection responsibility onto the round-trip guard.

---

## Invocation seam (GOV-01)

**Framing note:** the ROADMAP already fixes the surface set for this phase (CLI + MCP; HTTP joins in Phase 19), so that was not re-asked.

### Q1 — How strict, how fast?

| Option | Description | Selected |
|--------|-------------|----------|
| Strict, with a shrinking allowlist | Mirrors the `_KNOWN_BROKEN` discipline from Phase 16 — exception set visible, counted, mechanically prevented from growing. | |
| Strict from day one | No allowlist. Latent mismatches become a Phase 18 fix list discovered during execution. | ✓ |
| Strict on MCP, lenient on CLI | Lowest disruption to the human surface, but is exactly the parity fork GOV-01 exists to close. | |

**User's choice:** Strict from day one.

### Q2 — How wide does `extra="forbid"` go across the 28 input models?

| Option | Description | Selected |
|--------|-------------|----------|
| All 28, forbid by default | One rule; open payloads expressed as typed dict fields. Cost: a 28-model audit inside this phase. | |
| Forbid + named exceptions | Smaller audit, but reintroduces per-capability reasoning with no mechanism stopping the exception set from growing. | |
| You decide | — | ✓ |

**User's choice:** You decide → forbid-by-default across all 28, with research sizing the audit.

### Q3 — What should the differential parity test drive?

| Option | Description | Selected |
|--------|-------------|----------|
| Real CLI process + real MCP dispatch | Honest end-to-end; exercises the Typer layer where the positional-call debt lives. Slower, needs a fixture workspace. | |
| In-process call paths | Fast, easy to parameterize, but skips the exact layer the debt sits in. | |
| You decide | — | ✓ |

**User's choice:** You decide → real CLI subprocess + real MCP dispatch preferred; planner may trade fixture cost against breadth but must not fall back to set-membership assertions.

### Q4 — How does `registry.invoke()` call the handler?

| Option | Description | Selected |
|--------|-------------|----------|
| `handler(**model.model_dump())` | Identical to `mcp/server.py:33`; MCP needs no change. Work is normalizing cli.py's three positional sites and retiring RT-03 shims. | |
| `handler(model)` | Typed access, input model stops being ignored documentation. All 28 handler signatures change in one phase. | |
| You decide | — | ✓ |

**User's choice:** You decide → `handler(**model.model_dump())` preferred, contingent on research confirming handler fit.

---

## Review-decision model (GOV-02 / GOV-03)

### Q1 — A resume whose decision map doesn't cover every queued proposal

| Option | Description | Selected |
|--------|-------------|----------|
| Reject the whole resume | Zero writes, run stays paused, response names uncovered ids. Strongest reading of criterion 3. | ✓ |
| Apply covered, leave rest pending | Friendlier to partial review, but makes partial application a normal outcome — the state GOV-05 says must never read as success. | |
| Missing means reject | Inverts the dangerous default without a new run state, but silently discards proposals the user never saw. | |

**User's choice:** Reject the whole resume.

### Q2 — How is a stale queue detected?

| Option | Description | Selected |
|--------|-------------|----------|
| Checkpoint id as ETag | Free (LangGraph maintains it); catches any state advance, not just queue changes. Stricter than "the queue changed". | ✓ |
| Queue content fingerprint | Rejects exactly when the reviewed thing changed; no false invalidations. Second identity mechanism; can miss payload-only changes. | |
| You decide | — | |

**User's choice:** Checkpoint id as ETag.
**Notes:** Research should confirm the id is stable across a pause in the pinned LangGraph version before planning commits.

### Q3 — Where does a `proposal_id`'s value come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Content-derived hash | Stable across a regenerated queue; but structurally identical proposals collide and normalization changes reassign ids. | |
| Opaque id at enqueue | Guaranteed unique, clean "id not in this queue" rejection. Ids don't survive a re-derived queue — which the ETag catches anyway. | ✓ |
| You decide | — | |

**User's choice:** Opaque id at enqueue.

### Q4 — Runs already paused with id-less proposals

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse with a named error | No migration code on the surface where a wrong decision writes canonical truth. Abandons genuinely pending reviews. | |
| Migrate on read | Assign opaque ids at load time; preserves pending human-review work. Migration path runs once and is hard to keep tested. | ✓ |
| You decide | — | |

**User's choice:** Migrate on read.
**Notes:** Claude surfaced the interaction that makes this safe — migration preserves only the *queue*; because Q1 requires a complete id-keyed map, no legacy positional payload can be applied to a migrated queue. The two decisions are a pair.

---

## Surface honesty (GOV-04 / GOV-05)

**Framing note:** Claude surfaced from live code that `gate_review.py` does not review the workflow gates at all — its two sections are session-state Q&A review and bridge candidates, neither of which has a paused checkpoint to resume into. GOV-04's literal wording assumes a target that does not exist.

### Q1 — What happens to `src/construct/ui/gate_review.py`?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete the page | Removes the forged `gate_review_approved` events and the second canonical write path. Nothing in v0.5 depends on it. | ✓ |
| Fence it | Read-only, no writes, no event emission. Preserves bridge-candidate visibility; leaves a page whose purpose was approving things. | |
| Rebuild as a real gate review | Literal reading of GOV-04 — repoint at paused runs, approve via `Command(resume=…)`. Net-new build inside a repair phase, on a UI the milestone is replacing. | |

**User's choice:** Delete the page.
**Notes:** Claude flagged that this leaves ROADMAP success criterion 4 without a subject; captured in CONTEXT.md as D-14 (restate the criterion) rather than left for the planner to reconcile.

### Q2 — Does GOV-05 change the Phase 11 exit-code contract?

| Option | Description | Selected |
|--------|-------------|----------|
| Hold the Phase 11 contract | Degraded exits 0; GOV-05 governs what a surface *says*, not process exit semantics. Keeps WR-04 closed. | |
| Re-decide: degraded exits non-zero | A shell checking `$?` currently reads degraded as success. Reverses a deliberate Phase 11 decision and changes scripting behavior. | |
| You decide | — | ✓ |

**User's choice:** You decide → Phase 11 contract held.
**Notes:** Raised specifically because the Phase 11 decision was deliberate and re-opening WR-04 sideways is what it was recorded to prevent.

### Q3 — How does `escalate` stop implying an action it doesn't take?

| Option | Description | Selected |
|--------|-------------|----------|
| Relabel + count separately + own event | Names its real effect, own bucket so it never folds into a success count, distinct event type instead of `gate_review_rejected`. | ✓ |
| Relabel and count only | Smaller change; leaves the audit trail recording escalations as rejections. | |
| Remove escalate until it writes | Nothing can imply a non-existent action, but loses the L3 gates' ability to express "needs a human beyond this queue". | |

**User's choice:** Relabel + count separately + own event.

### Q4 — What mechanically enforces GOV-05?

| Option | Description | Selected |
|--------|-------------|----------|
| Table-driven cross-surface test | One table over every reporting surface, driven against a forced-degraded run and an escalated item. Phase 19's HTTP joins by adding a row. | |
| Result-model assertions only | Cheaper, pins the contract at source, but rendering is where the lie has historically happened. | |
| You decide | — | ✓ |

**User's choice:** You decide → table-driven cross-surface test preferred.
**Notes:** The event-count invariant (no `gate_review_approved` for a write that never happened; currently double-firing at `curation_run.py:872`, `:923`, `:968`) lands in this phase regardless, as it is success criterion 4.

---

## Claude's Discretion

Areas the user explicitly delegated:

- Byte-contract fix shape → research option (i), with the ING-02 tension recorded as a named decision.
- Round-trip guard shape → strict named-8 + cardinality (forced by the `extra="ignore"` choice).
- `extra="forbid"` coverage across the 28 input models → forbid by default, audit sized during research.
- Differential parity test target → real CLI subprocess + real MCP dispatch preferred.
- Handler calling convention → `handler(**model.model_dump())` preferred, contingent on handler-fit research.
- Exit-code contract under GOV-05 → Phase 11 contract held.
- GOV-05 enforcement shape → table-driven cross-surface test preferred.

## Deferred Ideas

None raised by the user — the discussion stayed inside the phase boundary. Items recorded in CONTEXT.md's
`<deferred>` section are pre-existing phase assignments from the ROADMAP and research (Phase 19 concurrency
contract and run-list capability, Phase 22 ETag HTTP semantics, escalate's future write path, RT-01/RT-02
for `spike`/`tag`, `card list` MCP-boundary residue, `artifact-catalog.md` prose counts), not new ideas
surfaced here.
