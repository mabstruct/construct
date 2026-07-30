---
phase: 18-contract-governance-foundations
fixed_at: 2026-07-30T21:40:00Z
review_path: .planning/phases/18-contract-governance-foundations/18-REVIEW.md
iteration: 1
fix_scope: critical_only
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
tests_before: "734 passed, 18 skipped, 0 failed"
tests_after: "765 passed, 18 skipped, 0 failed"
---

# Phase 18: Code Review Fix Report

**Fixed at:** 2026-07-30T21:40:00Z
**Source review:** `.planning/phases/18-contract-governance-foundations/18-REVIEW.md`
**Iteration:** 1
**Scope:** the five Critical findings only (CR-01..CR-05). The 13 Warnings were
explicitly out of scope and none was touched.

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0
- Test suite: **734 passed / 18 skipped / 0 failed → 765 passed / 18 skipped / 0 failed**
  (+31 tests, all new; **no existing test's expectation was changed**)

Every finding was **re-reproduced against running code before the fix and again
after it**. All five reproductions are closed. The five accepted decisions
(D-21, D-03, D-23, D-24) were left untouched — no entry was added to
`UNRESOLVED_DIRECT_CALLERS`, no views model was moved off `extra="ignore"`, no
round-trip assertion was weakened, no FastMCP schema work was attempted, and
`research_run`'s `update_seeds_and_log` was not modified.

## Fixed Issues

### CR-01: MCP returned a serializer TypeError instead of the capability's errors

**Files modified:** `src/construct/mcp/server.py`,
`tests/contract/test_mcp_contracts.py`, `tests/integration/test_surface_parity.py`
**Commit:** `a9441ed`

**Reproduced before:** `{"error": "Object of type OperationError is not JSON serializable"}`
from `construct_views_validate_data` through the real registered tool closure.
**Reproduced after:** the capability's own `errors` list, `success: false`, and no
filesystem path anywhere in the payload.

**Applied fix:** `_serialize_result`'s dataclass branch now uses
`dataclasses.asdict`, which recurses into `OperationError`. The one-level
`{f: getattr(result, f)}` walk was the defect.

`json.dumps` was deliberately **not** given a `default=str` fallback. That would
have made the boundary robust by stringifying any unprojectable value — including
`Path`, putting filesystem locations into a reason rendered straight back to an
MCP client. That is WR-03's territory and the constraint was not to make it
worse. A value this function cannot project is now a bug to fix in the function.

**Test-first:** both tests were written and watched fail first.
- `test_mcp_renders_a_capability_s_errors_rather_than_a_serializer_fault` drives
  the closure `create_server()` actually registers (calling `cap.handler`
  directly returns the dataclass and proves nothing), and re-asserts T-18-10.
- `test_failure_parity_puts_the_capability_s_errors_on_both_surfaces` is the
  failure-case parity arm the review asked for: `views.validate_data` against an
  install root with one corrupted data file, compared across the real CLI
  subprocess and real MCP dispatch. This is the gap that let the defect ship —
  every `PARITY_CASES` row is a *success*, and both rejection tests fail inside
  the seam before a handler ever runs, so nothing reached `_serialize_result`.

### CR-02: `apply_connections` wrote a canonical edge for any token that was not exactly `"reject"`

**Files modified:** `src/construct/llm/curation_run.py`,
`tests/llm/test_curation_run.py`
**Commit:** `7ab7934`

**Reproduced before:** all six of `skip` / `hold` / `no` / a typo / `escalate` /
`""` wrote to `connections.json`. **After:** all six leave it byte-identical.

**Applied fix:** `if decision != "approve"` replaces `if decision == "reject"`,
making the node default-deny like both siblings.

**On the approved vocabulary — the review flagged this as a real question, and the
reviewer's illustrative `("approve", "connect")` is wrong.** Derived, not guessed:

| node | required token | where it comes from |
|---|---|---|
| `apply_promotions` | `"promote"` | the promotion producer's recommended `decision` |
| `apply_archives` | `"archive"` | `CurationProposal(kind="archive", decision="archive", …)` |
| `apply_connections` | `"approve"` | `CurationProposal(kind="connection", decision="approve", …)` |

Each sibling requires exactly its producer's own recommendation, so connections
requiring `"approve"` is the *consistent* reading, not a stricter one.
`_normalize_decision("approve", default)` expands the synonym to that same
recommendation, and `_build_resume_decisions` expands `approve_all` to
`entry["decision"]` — so both the synonym path and the structured per-item path
land on `"approve"`. `grep` finds **no** `"connect"` token anywhere in `src/` or
`tests/`; it does not exist in this codebase. This is the strictest defensible
reading and it is default-deny, as instructed.

**One behaviour change worth naming:** an `escalate` token on a *connection*
proposal now rejects rather than writing. `apply_promotions` has a real escalate
branch; `apply_connections` has no `escalated` bucket in its return, and adding
one would mean touching a graph state channel — out of scope for a blocker fix.
Rejecting is the correct direction (nothing is written either way), but it emits
`gate_review_rejected` for what a user may have meant as an escalation. Worth a
follow-up if connections ever grow an escalate path.

**Test-first:** the six-token parametrised denial test and the positive
"approval still writes" test were written and watched fail (6 of 7 red; the
approval arm was green from the start, which is the point of keeping it).

**Incidental finding, reported not fixed (out of scope):** the tests are driven at
the `apply_connections` node rather than end-to-end, because the
`curation_workspace` fixture's cards produce no bridge candidates, so
`connection_maintenance` enqueues **no connection proposal at all**. That makes
the existing `test_reviewed_connection_idempotent` vacuous today — its
`after_second == after_first` compares two empty sets and its
`len(x) == len(set(x))` is trivially true for a set. Warning-class, not touched.
The node-level tests still resolve decisions through the real
`_decision_map` → `_check_coverage` → `_normalize_decision` path.

### CR-03: `knowledge.card.edit` destroyed stored title/prose when a field arrived as `""`

**Files modified:** `src/construct/capabilities/catalog.py`,
`tests/integration/test_knowledge_cli.py`
**Commit:** `e5b157c`

**Reproduced before**, against a copy of the checked-in `test-ws/my-construct`
fixture: `{"summary": ""}` deleted the card's Summary prose and `{"title": ""}`
blanked the title, both returning `success: True`.
**After:** all three of `{"summary": ""}`, `{"title": ""}`, `{"summary": "   "}`
are rejected with a reason and the card file is byte-identical.

**Applied fix — the model-level constraint, as the constraint preferred.**
`CardEditInput.title` / `lifecycle` / `summary` carry `min_length=1` plus a
`field_validator` on the *stripped* value. `min_length=1` alone is satisfied by
three spaces, and a title of three spaces is a destroyed title.

The seam now **rejects with a reason** rather than accepting a silent no-op,
which is the choice the rest of this phase makes, and the model is the one layer
CLI, MCP and Phase 19's HTTP adapter all share.

**No legitimate caller clears a field on purpose.** `grep` across `src/` and
`tests/` finds no `""` sent to any of these three fields; `_build_card_data`
(create) already drops an empty summary via `if summary:`; `curation_run` calls
`edit_card` directly with a non-empty lifecycle. Clearing was never expressible
— `""` only ever destroyed data. So nothing had to be forced.

`_build_card_updates` keeps a hardened second guard (blank now skipped, not just
`None`). That layer is only reachable by a caller that bypasses the model, and
there a silent skip is right: it destroys nothing. The primary rejection lives at
the model, so the "two independent guards, deliberately both kept" structure
`cli.py` documents is preserved rather than replaced.

**Note on `lifecycle`:** included alongside title/summary. The review's own
suggested guard listed it, and `""` there is a blanking value like any other.

**Test-first:** six parametrised tests (3 fields × blank / whitespace) written
and watched fail, each asserting **both** surfaces — the CLI and the seam an MCP
client reaches — and each reading the card back to assert byte-identity.

### CR-04: agent-supplied `workspace` on write capabilities had no marker guard

**Files modified:** `src/construct/storage/workspace.py`,
`src/construct/capabilities/catalog.py`, `tests/contract/test_capability_seam.py`
**Commit:** `10228e0`

**Reproduced before:** `knowledge.card.create` with
`workspace=/tmp/definitely-not-a-workspace-9x8/secret-dir` returned
`success=True, "Card 't' created as t"` after creating `cards/` and `log/` and
writing into both. **After:** `success=False`, reason `"workspace is not an
existing directory"`, and `/tmp/definitely-not-a-workspace-9x8` does not exist.

**Applied fix — reusing the existing idiom, as instructed.** `workspace_error()`
is the deliberate analogue of `views/generate.py`'s `install_root_error()`: same
`(path) -> str | None` signature, same call-it-first-in-the-shim placement, same
docstring reasoning ("registration is what makes this agent-supplied over MCP, so
the marker check became a boundary control"), and the same convention that **the
reason names no filesystem path** — pinned by an assertion over every path
segment, so WR-03 is not made worse.

It lives in `storage/workspace.py`, the module that already owns
`WorkspaceScaffold` and `REQUIRED_PATHS`, and keys on `domains.yaml`: it is in
`REQUIRED_PATHS`, `initialize_workspace` writes it, and every canonical read goes
through it — so "has this marker" and "was scaffolded by us" are one statement.

Applied to **all six** write shims (`card.create`, `card.edit`, `card.archive`,
`connection.add`, `connection.remove`, `ingest.source`), not only the four
currently on MCP: Phase 19's generated HTTP adapter exposes the rest, and a guard
scoped to "whatever is on MCP today" would need re-auditing then.

**Test-first:** parametrised over an *enumerated* write-capability table — not
discovered from the registry, so the guard cannot go quiet by a capability simply
not being found — plus a positive arm proving a real workspace still writes.
6 of 13 arms were red; **two of them were not merely permitting the write, they
were raising `NotADirectoryError` straight through the MCP boundary.**

### CR-05: the seam's payload-independent error ordering did not hold for nested models

**Files modified:** `src/construct/capabilities/errors.py`,
`tests/contract/test_capability_seam.py`
**Commit:** `9134552`

**Reproduced before:** the same `workspace.init` payload with two nested key
orders produced two different reason strings. **After:** identical, with declared
fields still in declaration order and undeclared ones by name.

**Applied fix:** the rule `from_validation_error`'s docstring already states —
declared fields in declaration order, then undeclared by name — is now applied at
**every level** of the `loc` path instead of only its head.

**Deliberately not the reviewer's `(*rank, loc[1:])` string-tail sort.** That
closes the reported arm and quietly opens another: nested *declared* fields would
come out alphabetically, so `domain.display_name` would report before
`domain.domain_id` even though the sub-model declares `domain_id` first. There is
a dedicated test (`test_nested_declared_field_errors_follow_declaration_order`)
whose whole job is to refuse that shortcut; it uses exactly that discriminating
pair and asserts the pair still discriminates.

`_field_order` reads **both** `model_fields` and `__dataclass_fields__`, because
one `loc` path spans two container shapes: `WorkspaceInitInput` is a `BaseModel`
whose `domain` field is the `DomainInitInput` *dataclass* (T-18-13) — the phase's
own nested-payload example. The key is a tuple of same-shaped `(kind, index,
name)` triples, so different depths compare element-wise then by length and a
top-level error can never tie with a nested one (a tie is what let this hide).

**Test-first:** three tests. The nesting arm was red. The other two —
declaration-order and mixed-depth totality — passed before the fix *by accident*
and are kept as pins on the fix's design; they are what makes the shortcut
above fail.

## Skipped Issues

None.

## Notes for the developer

- **No existing test's expectation was changed.** All 31 new tests are additive;
  the 734 pre-existing passes are untouched.
- **Logic-bug caveat.** CR-02 and CR-03 change *semantics*, not just structure.
  Both are covered by tests that were red before and green after, and both
  reproductions were re-run — but the vocabulary decision in CR-02 (`"approve"`
  as the sole approved connection token) and the escalate-token behaviour change
  noted under it are the two places worth a human read before the phase verifies.
- **Entanglement declared rather than silently widened:**
  - CR-01 touches the same boundary as **WR-03** (raw exception text crossing
    MCP). Not fixed; explicitly *not made worse* — no `default=str` was added,
    and the CR-04 guard's reason names no path.
  - CR-03's model constraint interacts with **WR-07** (the Streamlit runner
    submitting `""` for unnamed optional fields). No regression: the review
    already records `knowledge.card.edit` as unusable from that form because of
    `confidence: ge=1`. WR-07 remains open.
  - CR-02's neighbour **D-24** (`research_run`'s `update_seeds_and_log`) was left
    alone, as instructed.
- **The vacuous `test_reviewed_connection_idempotent`** (see CR-02) is a genuine
  new finding surfaced while fixing CR-02. Reported, not fixed — it is
  warning-class and outside the stated scope.

---

_Fixed: 2026-07-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
