# Phase 16 — Deferred Items

Out-of-scope discoveries found while executing this phase. Logged, not fixed — none was
caused by this phase's changes, and each lives outside the invocation/doc-truth boundary.

## D1 — `help --suggest` health counters disagree with their own payload

**Found during:** 16-06 Task 2, executing the playbook's §5.1 step against a scratch workspace.

**Symptom:** `construct help --suggest -w "$WS"` reports
`Workspace health: 1 domains, 0 cards, 0 connections` in a workspace holding four cards and
one connection. The same `--json` payload's nested `graph_status.cards.total` reports the true
count (`4`), so the top-level `total_cards` / `total_connections` fields and the `graph_status`
block read from different sources. The derived `suggestions[].priority` text inherits the wrong
count and says `Domain exists but is empty` for a populated domain.

**Why deferred:** a suggestion-aggregation defect in `help`, unrelated to invocation
resolution or documentation truth. Fixing it would mean changing runtime behaviour in a
documentation phase.

**Handled by:** `USER-TEST-PLAYBOOK-v041.md` §5.1 documents the behaviour as a known-open
observation and instructs validators to assert only that a domain-grounded suggestion is
produced, so the playbook does not encode a false expectation while the defect stands.

## D2 — Packaged version string lags the milestone

**Found during:** 16-06 Task 1, verifying the version-check step rather than carrying `0.3.0`
forward.

**Symptom:** `construct --version` reports `0.3.20260621182115` while the milestone under
validation is v0.4.1.

**Why deferred:** packaging/release metadata, outside this phase's boundary.

**Handled by:** the playbook asserts that *a* version prints rather than asserting a value —
an exact-match assertion would rot on the next build — and records the mismatch in its
known-open list.

## D3 — `views validate` rejects fields `views generate` writes

**Found during:** 16-06 Task 2, executing §10.

**Symptom:** on a fresh install root, `views generate` succeeds with zero `validation_errors`
and writes 11 files; `views validate` then fails 4 of 8 (`stats.json`, and the per-workspace
`cards.json`, `connections.json`, `events.json`) with Pydantic `extra_forbidden` errors on
fields the generator emits.

**Why deferred:** this is the known-open generator/schema contract question recorded by
Phase 15, already tracked. Not a Phase 16 regression.

**Handled by:** playbook §10.2 states the caveat explicitly and defines what *would* be a real
defect (command failure, malformed JSON, or an error other than a schema mismatch on
generator-written fields), so a validator recognises it rather than refiling it.
