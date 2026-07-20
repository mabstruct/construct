---
phase: 16-invocation-user-doc-truth
plan: 06
subsystem: release-validation
tags: [documentation, release-validation, invocation-guard, doc-truth, playbook]
requires:
  - "16-01 (the doc-reference guard, its _KNOWN_BROKEN allowlist and _MUST_CARRY_INVOCATIONS)"
  - "16-03 (knowledge card list — the enumerate command the playbook exercises)"
  - "16-04 (skill rewrites that discharged the other two allowlist entries)"
  - "16-05 (the settled command-to-capability mapping and the required-argument surface)"
provides:
  - "USER-TEST-PLAYBOOK-v041.md — the v0.4.1 release-validation artifact, 32 resolving invocations"
  - "_KNOWN_BROKEN empty — FIX-03's mechanical terminal state, with _DOC_GLOBS still at three entries"
  - "An executed offline baseline: every unmarked playbook step run verbatim against a scratch workspace"
affects:
  - "16-07 (glob extension — the playbook is now the third scanned document)"
  - "17 DOC-01/DOC-02 (the known-open observations recorded here are Phase 17 candidates)"
tech-stack:
  added: []
  patterns:
    - "Supersession over deletion: a retired document is replaced in the guard's glob set, never removed from it, so an emptied allowlist cannot be confused with a narrowed scan"
    - "Verdict-from-payload: release assertions read --json status fields because degrade-by-design commands exit 0"
key-files:
  created:
    - USER-TEST-PLAYBOOK-v041.md
    - .planning/phases/16-invocation-user-doc-truth/deferred-items.md
  modified:
    - tests/contract/test_doc_command_references.py
  deleted:
    - USER-TEST-PLAYBOOK-v03.md
decisions:
  - "The two workflow allowlist entries were deleted because their invocations are gone from a document that REMAINS in _DOC_GLOBS — the tuple still holds three entries. The terminal signature is '0 3'; '0 2' would have meant the guard was narrowed rather than satisfied."
  - "The research run -> review -> resume flow is marked credentialed rather than placed in the core path: offline it reports status 'failed' on a scoring provider outage and never reaches the review gate, so an unmarked step would have violated D-07's offline-runnable guarantee."
  - "card evaluate stays in the core offline path despite exiting 1, because it degrades with structured reporting (degraded/total_outage flags) and that reporting is itself the property worth validating."
  - "Card ids are deterministic title slugs, so the playbook uses literal ids instead of v0.3's <CARD_A> placeholders — every command is copy-pasteable verbatim."
  - "There is no mock search provider; the plan's premise of a mock default was inaccurate. Offline runnability is delivered by commands that degrade gracefully, not by a stub provider."
metrics:
  duration: ~55 min
  tasks: 3
  files: 4
  completed: 2026-07-20
status: complete
---

# Phase 16 Plan 06: Playbook supersession and the empty allowlist Summary

`USER-TEST-PLAYBOOK-v041.md` replaces the v0.3 playbook as the v0.4.1 release-validation
artifact — organised by capability, offline-runnable by default, asserting on `--json` status
fields — and `_KNOWN_BROKEN` is now **empty with `_DOC_GLOBS` still holding three entries**,
which is FIX-03's terminal state reached by supersession rather than by narrowing the guard.

## The load-bearing distinction

This plan's whole risk was that an emptied allowlist and a weakened guard look identical in a
test report. They are separated here by a single mechanical signature:

```
_KNOWN_BROKEN = 0 entries    _DOC_GLOBS = 3 entries     ->  "0 3"
```

`0 3` means the two `workflow` invocations died because they are **gone from a document that
is still scanned**. `0 2` would have meant they died because the document stopped being
scanned — FIX-03 satisfied on paper while the test that defines it was destroyed. The glob
entry was **replaced, never removed**: the diff shows one `-` line and one `+` line for both
`_DOC_GLOBS` and `_MUST_CARRY_INVOCATIONS`, and the tuple length assertion pins it.

The reasoning is recorded in the code itself, not only here — the `_KNOWN_BROKEN` comment
block now explains why the dict is empty and warns that an entry may only be removed by making
its command resolve or by deleting the reference from a document that stays in `_DOC_GLOBS`.
A future reader cannot mistake a shrunken glob set for a fix.

## The artifact

**32 distinct resolving invocations** across **53 headings** (the v0.3 file had 22 and 34) —
coverage was carried and extended, never reduced.

| § | Section | Credentialed? |
|---|---------|---------------|
| 0 | Prerequisites & setup (tooling, smoke workspace, install-root marker) | offline |
| 1 | Workspace contract & governance | offline |
| 2 | Governed knowledge operations (CRUD, **enumerate**, archive, events) | offline |
| 3 | Capability registry, CLI & MCP spine | offline |
| 4 | Ingestion | offline |
| 5 | Guided workflow operability (curation run / inspect / review) | offline |
| 6 | **Daily cycle** (new) | offline |
| 7 | **Card evaluation** (new) | offline (degrades) |
| 8.1 | Research search | offline |
| 8.2 | **Durable run → human review → resume** | **`ANTHROPIC_API_KEY`** |
| 9 | Grounded synthesis & graph reasoning | **`ANTHROPIC_API_KEY`** (§9.2 bridge detect runs offline) |
| 10 | Derived data & views (**`views generate`** added) | offline |
| 11 | Governed spikes & tag extraction | offline |
| 12 | Machine-readable output | offline |
| 13 | Teardown | offline |

**Three headings carry a credential marker** (§8.2, §9, §9.1). Everything else runs against a
plain checkout with no secrets. No credential, key, or token value appears anywhere in the file
— including as an illustrative placeholder (`grep -cE 'sk-[A-Za-z0-9]|tvly-[A-Za-z0-9]'` → 0).

**Successor coverage for the two removed commands.** `workflow run` and `workflow resume` were
replaced, not dropped: curation run → inspect → review (§5.3–5.5) exercises the durable
checkpoint round-trip offline, and the research run → review → resume flow (§8.2) exercises the
human-review gate. `workflow status` survives as a read-only query and is checked at §5.2. The
successor note in §5 deliberately names the removed subcommands **without** the `construct`
prefix, so describing them does not re-introduce the very invocations this plan removed.

## Executed, not merely resolved

Per D-09 and the lesson 16-05 recorded, the guard validates that a command **resolves**, not
that it **executes** — it truncates at the first argument-looking token. Every unmarked step
was therefore run verbatim against a fresh scratch workspace. All passed:

| Section | Observed |
|---|---|
| 1.1–1.3 | validate clean; corruption → `exit=1`; restore clean |
| 2.1–2.7 | 2 cards created with the expected slug ids; enumerate returns **no `body` key**; `--domain AI-Gateways` returns 0 (case-sensitive); archive hides the edge (0) but `--include-archived` preserves it (1); 6 event-log lines |
| 3.1 | MCP handshake → **22 tools**, `construct_list_cards` present |
| 4.1–4.2 | both refs created |
| 5.1–5.5 | curation `status: completed`, 6 required steps completed, `views_refresh_hook` skipped; inspect round-trips by run id; review returns `Curation run already complete (no re-review).` |
| 6.1–6.2 | daily **`status: degraded`, exit 0**, children `research.run failed` / `curation.run completed` / `graph.status completed` |
| 7.1 | `card evaluate` → `{"degraded": true, "total_outage": true}` |
| 8.1 | research search → 1 result offline |
| 9.2 | bridge detect → 0 candidates, valid JSON artifact written |
| 10.1–10.2 | generate: 11 files, 0 validation errors; validate: 4 pass / 4 fail (known-open drift) |
| 11.1–11.3 | 5 candidates all pending; approve moves exactly one to approved |
| 12–13 | JSON envelopes well-formed; teardown clean |

§6.1 is the single best justification for D-08 in the whole document: **`daily run` exits `0`
while reporting `status: degraded` with a failed child.** An exit-code assertion would have
reported that cycle as a clean release validation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The carried-forward MCP step did not work**

- **Found during:** Task 1
- **Issue:** v0.3 §3.1 piped a bare `tools/list` into `construct mcp` and asserted a tool list
  came back. It does not — the server rejects it with `-32602 Invalid request parameters`
  because MCP requires an `initialize` handshake first. The v0.3 file even carried a note
  admitting real clients need initialize-first, while its own step asserted otherwise.
- **Fix:** The step now sends the full three-message sequence (initialize →
  notifications/initialized → tools/list) and parses the response. This also made the D-01
  parity check possible: the step now asserts `construct_list_cards` is on the MCP surface.
- **Commit:** `5e1dc7f`

**2. [Rule 1 - Bug] The views section could never have run**

- **Found during:** Task 2
- **Issue:** `views generate|validate` refuse any `--install-root` lacking an `AGENTS.md`
  marker (`views/generate.py:172`), a guard that stops the generator scaffolding a views tree
  into an unrelated directory. v0.3 §0.2 created the install root with a bare `mkdir -p`, so
  every v0.3 views step would have failed with `not a CONSTRUCT installation: missing
  AGENTS.md` for any validator who ran it. The invocations resolved, so no test caught it.
- **Fix:** Added §0.3, which writes the marker, and documented the failure mode.
- **Commit:** `910d2ab`

**3. [Rule 1 - Bug] The expected workspace tree was stale**

- **Found during:** Task 1
- **Issue:** v0.3 §0.2 expected `domains.yaml, search-seeds.json, connections.json, cards/,
  refs/, digests/, log/, .construct/`. `construct init` actually produces `publish/` and
  `WORKSPACE.md` as well, and **no `.construct/` directory** at the top level.
- **Fix:** The expected entry list now matches what `init` produces, verified by running it.
- **Commit:** `5e1dc7f`

**4. [Rule 2 - Correctness] stdout/stderr separation documented**

- **Found during:** Task 2, when my own verification pipeline broke
- **Issue:** Degradation notices go to `stderr` while `--json` goes to `stdout`. A
  `2>&1 | python -c "json.load(...)"` pipeline — the obvious thing for a validator to write —
  corrupts the payload with `promotion_review: provider outage ...` and dies on a
  `JSONDecodeError`. Every JSON-reading step in the playbook would have been a trap.
- **Fix:** All run steps redirect the two streams separately, and the rule is stated in the
  "How to read this document" preamble and restated in §12.1.
- **Commit:** `910d2ab`

### Accepted plan-vs-reality mismatches

**There is no mock search provider.** The plan's must-have and Task 1 action both state that
"the search provider defaults to mock" and that steps run "against the mock/default search
provider". `src/construct/llm/config.yaml` defines exactly three providers — `anthropic`,
`openai`, `ollama` — and every gate routes to `anthropic`. Offline runnability is therefore
delivered by a different mechanism than the plan assumed: commands **degrade with structured
reporting** rather than being served by a stub. The D-07 guarantee still holds in full (every
unmarked section runs credential-free), but the playbook says so accurately.

**`research run` could not stay in the core path.** The plan's must-have asks for "a research
run through durable human review to resume" alongside the offline curation flow. Offline,
`research run` reports `status: failed` with a total scoring outage and never reaches the
review gate, so an unmarked step would have broken D-07's promise that the whole unmarked path
runs on a bare checkout. The flow is present and documented in full at §8.2 with an
`ANTHROPIC_API_KEY` heading marker — which is exactly the escape hatch D-07 defines — and the
offline `failed` outcome is documented so a validator does not read it as a defect. The
durable-checkpoint property the must-have cares about is *additionally* covered offline by
§5.4–5.5, which round-trips a real run by id and exercises the review entry point.

**`curation review` offline exercises the idempotent path, not a live gate.** A curation run
completes offline with an empty `gate_queue`, so there is no paused gate to consume. The step
asserts the honest observable behaviour — `Curation run already complete (no re-review).` with
`status: completed` — which validates that the review entry point recognises a finished run and
declines to double-write. The consuming-a-live-queue path is covered by §8.2.

## Deferred Issues

Three out-of-scope discoveries are logged in
`.planning/phases/16-invocation-user-doc-truth/deferred-items.md` and each is documented in the
playbook's "Known-open observations" list so validators recognise rather than refile them:

1. `help --suggest` reports `0 cards` in a populated workspace while its own `graph_status`
   reports the true count — a suggestion-aggregation defect, not a doc defect.
2. `construct --version` reports a `0.3.` prefix while validating v0.4.1.
3. `views validate` rejects fields `views generate` writes (Phase 15's recorded known-open
   contract question) — 4 of 8 files fail on `extra_forbidden`.

None was caused by this plan. Per the scope boundary, they were logged and not fixed.

## Requirement Traceability

**FIX-03 — complete.** Verified in both halves, mechanically, not assumed:

| Half | Evidence |
|---|---|
| `_KNOWN_BROKEN` is empty | `python -c "...; print(_KNOWN_BROKEN)"` → `{}` |
| The suite is green | `pytest -q` → **513 passed, 1 skipped, 0 failed** |
| The guard was not narrowed | `_DOC_GLOBS` = 3, `_MUST_CARRY_INVOCATIONS` = 3 (both unchanged in length) |

**DOC-04 — I judge it fully discharged.** Clause (d), "`USER-TEST-PLAYBOOK-v03.md` is retired
or superseded so the release-validation artifact runs", is closed by this plan on both limbs:
the v0.3 file is deleted with zero dangling references outside `.planning/`, and the successor
artifact **runs** — every unmarked step was executed verbatim against a scratch workspace, not
merely resolved. Clauses (a) and (b) were discharged by 16-05 and clause (c) by 16-02, as their
summaries record. All four clauses now have evidence.

The one judgement call worth surfacing for review: the credentialed sections (§8.2, §9, §9.1)
were **not** executed, because no `ANTHROPIC_API_KEY` was available. Under D-07 those sections
are opt-in extras rather than gates on the core run, so I read "the release-validation artifact
runs" as satisfied by the offline path executing end to end. If the orchestrator reads clause
(d) as requiring a credentialed run too, DOC-04 should stay open and route to 16-07.

## Test count reconciliation

Entry baseline was **515 passed, 0 failed**; exit is **513 passed, 1 skipped, 0 failed**. The
delta is fully accounted for and no test was lost: the two vanished cases are the
`test_known_broken_entries_are_still_broken` parametrizations for `workflow run` and `workflow
resume`, which cease to exist when their allowlist entries are deleted. The remaining `1
skipped` is that same test parametrized over an empty dict — pytest reports an empty
parametrization as a skip rather than an error, which the plan names as the intended terminal
state.

## Threat Mitigations Applied

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-16-01 (tampering — glob/allowlist) | mitigated | `_DOC_GLOBS` length asserted at 3 in Task 3's verify; the diff replaces rather than removes; the reasoning is recorded in the `_KNOWN_BROKEN` comment block so it survives in-code |
| T-16-04 (info disclosure — credentials) | mitigated | Three credentialed headings; everything unmarked executed offline; `grep -cE 'sk-[A-Za-z0-9]\|tvly-[A-Za-z0-9]'` → 0; the tooling table checks for a key with `${ANTHROPIC_API_KEY:+set}`, which never echoes the value |
| T-16-15 (repudiation — false pass on degraded run) | mitigated | No Pass criterion in the curation, research, or daily sections names an exit code; each reads `status` from the `--json` payload. §6.1 demonstrates the concrete case: exit 0 with `status: degraded` |
| T-16-16 (DoS — smoke workspace) | accepted | The `test-ws/` fixture warning is carried forward; the playbook directs validators to a throwaway install root and tears it down at §13 |
| T-16-SC (supply chain) | accepted | Zero packages installed; `pyproject.toml` untouched |

## Known Stubs

None.

## Self-Check: PASSED

- `USER-TEST-PLAYBOOK-v041.md` — FOUND
- `USER-TEST-PLAYBOOK-v03.md` — CONFIRMED ABSENT
- `.planning/phases/16-invocation-user-doc-truth/deferred-items.md` — FOUND
- `tests/contract/test_doc_command_references.py` — FOUND (modified)
- Commit `5e1dc7f` (Task 1) — FOUND
- Commit `910d2ab` (Task 2) — FOUND
- Commit `f351a7e` (Task 3) — FOUND
