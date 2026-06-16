---
phase: 07-close-v0-3-blockers-rt-03-mcp-schema-parity-ing-02-ingest-cl
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/construct/capabilities/catalog.py
  - src/construct/services/help.py
  - src/construct/services/init.py
  - CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json
  - test-ws/my-construct/search-seeds.json
  - test-ws/ping-eon/search-seeds.json
  - tests/contract/test_mcp_contracts.py
  - tests/integration/test_ingest_validate_e2e.py
  - tests/unit/test_schema_contracts.py
  - tests/unit/test_validation_service.py
  - tests/unit/test_workspace_contracts.py
findings:
  critical: 1
  warning: 7
  info: 4
  total: 12
status: partially_resolved
resolved: [CR-01, WR-06]
open: [WR-01, WR-02, WR-03, WR-04, WR-05, WR-07, IN-01, IN-02, IN-03, IN-04, CR-02]
---

> **Resolution addendum (2026-06-16, commit 880d9e8):**
> - **CR-01 — RESOLVED.** `help.py` now reads the `clusters` key (was `search_clusters`)
>   and aggregates `last_queried` across non-reserved research clusters instead of
>   `clusters[0]`. Reserved ingest clusters are excluded via `_RESERVED_INGEST_CLUSTERS`.
>   Added `_score_domain` tier-4/5 regression tests. Suite: 224 passed.
> - **WR-06 — RESOLVED.** `ingestion.py` NOTE/RESEARCH path now returns a clean
>   `OperationResult` failure when no domain resolves, instead of stamping the
>   validation-failing `_general` domain.
> - **CR-02 — NEW (deferred, out of scope for this fix):** `help.py:suggest` resolves
>   per-domain stats from `root/<domain_id>/` subdirs (cards, refs, connections,
>   search-seeds.json), but the canonical `init` layout writes a single domain at the
>   workspace root (`root/cards/`, `root/search-seeds.json`). Two layouts coexist in
>   `test-ws/` (`semantic*/cosmology/` matches help.py; `ping-eon`/`my-construct` do
>   not). For canonical single-domain workspaces, help.suggest's per-domain card/ref/
>   connection/staleness stats all read 0 / not-found. This is a pre-existing
>   architectural inconsistency surfaced while fixing CR-01; it needs its own decision
>   (normalize the layout, or make help.py layout-aware). Not addressed here.
> - Remaining warnings/info (WR-01..WR-05, WR-07, IN-01..IN-04) left as tracked
>   follow-ups per the user's scoped decision (fix BLOCKER + WR-06 only).

# Phase 7: Code Review Report

**Reviewed:** 2026-06-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 07 closes three v0.3 blockers via adapter shims in `catalog.py` (RT-03 MCP
schema parity), reserved ingest-cluster seeding in `init.py` (ING-02), and
`graph.status` wiring (ING-05). The shims are structurally sound for the happy
path and the regression-gate tests (`test_mcp_contracts.py`) are well-designed.

However, the review surfaced one BLOCKER and several WARNINGs. The most serious
is a stale-research scoring bug in `help.py` that the ING-02 seeding change
directly *introduces*: by always seeding `manual-ingest` as the first cluster,
`_score_domain` now reads `last_queried` from the wrong cluster in any
freshly-initialized workspace, silently disabling the stale-research priority.
The shim layer also has a fragile positional/keyword dispatch and several
swallowed-exception paths that hide real failures behind "success" results.

## Critical Issues

### CR-01: ING-02 seeding breaks help.py stale-research scoring for all freshly-init'd workspaces

**File:** `src/construct/services/help.py:86-93` (interacting with `src/construct/services/init.py:132-149`)

**Issue:** `help.py` computes research staleness from **only the first cluster**:

```python
clusters = seeds.get("search_clusters", [])
if clusters:
    last_queried = clusters[0].get("last_queried")
```

After the ING-02 change, `init.py:_write_search_seeds` seeds the reserved
`manual-ingest` / `web-ingest` clusters *first* (from the template) and
**appends** the domain research-seed cluster last (`init.py:139`). The reserved
clusters always carry `last_queried: null`. Therefore in every freshly-init'd
workspace `clusters[0]` is `manual-ingest`, `last_queried` is `None`,
`research_stale_days` stays `-1`, and `_score_domain` (help.py:195-198) can
never reach priority tier 4 ("research is stale") or tier 5 ("last research N
days ago"). The stale-research suggestion is silently dead for the exact
workspaces this phase creates.

Two independent defects compound here:
1. `clusters[0]` is a fragile heuristic — it assumes the most-recently-queried
   cluster is first. ING-02 invalidated that assumption.
2. The code reads the key `"search_clusters"` (help.py:86) but the schema and
   every seed file use `"clusters"` (config.py:231, template line 3,
   `my-construct`/`ping-eon` seed files). `seeds.get("search_clusters", [])`
   therefore returns `[]` for *all* real workspaces, so the stale-research
   branch is already unreachable — and the ING-02 change locks that in.

The bug is masked because no test exercises the stale path against a real
seeds file: `test_help_suggest_surfaces_graph_health` only asserts the
`graph_status` key exists.

**Fix:** Read the correct key and aggregate across research clusters (excluding
reserved ingest clusters), e.g. take the max `last_queried`:

```python
clusters = seeds.get("clusters", [])  # was "search_clusters"
queried = [
    c.get("last_queried")
    for c in clusters
    if c.get("id") not in {"manual-ingest", "web-ingest"} and c.get("last_queried")
]
if queried:
    last = max(datetime.fromisoformat(q) for q in queried)
    ...
```

Add a regression test that seeds a research cluster with an old `last_queried`
and asserts `_score_domain` returns tier 4.

## Warnings

### WR-01: `except (KeyError, Exception)` swallows every error and is redundant/misleading

**File:** `src/construct/services/help.py:129`

**Issue:** `except (KeyError, Exception)` catches `Exception` — `KeyError` is a
subclass, so naming it is dead/redundant and signals confused intent. More
importantly, this blanket catch silently swallows *any* failure in the
`graph.status` call (including programming errors like `AttributeError`) and
leaves `graph_data = None`, so help.suggest reports a degraded result as success
with no signal. The companion test claims the presence of `graph_status`
"machine-proves the swallow is fixed", but the swallow at this line is still
present — it only proves the happy path works.

**Fix:** Catch the specific expected exceptions and let the rest propagate:

```python
except (KeyError, WorkspaceLoadError, OSError):
    pass
```

### WR-02: Shim positional/keyword dispatch silently mis-routes mixed calls

**File:** `src/construct/capabilities/catalog.py:353-432` (all five `_*_shim` functions)

**Issue:** Every shim branches on `if args:` to decide CLI-positional vs
MCP-keyword mode. If a caller ever passes the workspace positionally *and* any
schema field by keyword (a plausible future call site, or an MCP transport that
positionalizes the first arg), the `if args:` branch runs `create_card(*args,
**kwargs)` and forwards MCP-only kwargs (`title`, `epistemic_type`, `domains`,
…) straight into `create_card`, which does not accept them → `TypeError`. The
dispatch is correct only for the two exact call shapes that exist today; it has
no guard rail and no assertion that exactly one mode is in play.

**Fix:** Make the contract explicit — reject mixed invocation rather than
silently forwarding:

```python
def _create_card_shim(*args, **kwargs):
    if args:
        if kwargs.keys() - {"author"}:
            raise TypeError("positional call must not mix MCP schema kwargs")
        return create_card(*args, **kwargs)
    ...
```

### WR-03: `author`/`created_by` enum coercion raises ValueError on advertised free-text fields

**File:** `src/construct/capabilities/catalog.py:375, 393, 415`

**Issue:** The MCP schemas advertise `author` and `created_by` as plain strings
(`CardCreateInput.author: str = "construct"`, `ConnectionAddInput.created_by:
str = "construct"`). The shims coerce them with `CardAuthor(...)` /
`ConnectionAuthor(...)`, which raise `ValueError` for any value outside the
enum. An MCP client sending an advertised-but-out-of-enum `author` (e.g.
`"researcher-bot"`) gets an unhandled `ValueError` bubbling out of the handler.
The regression test (`test_mcp_contracts.py:134-139`) explicitly swallows
non-TypeError exceptions, so this gap is invisible to CI.

**Fix:** Validate against the enum and return a structured `OperationResult`
(or constrain the schema field to the enum's values so the failure is caught at
input-validation time rather than inside the handler).

### WR-04: `_build_card_data` duplicates `author` then shim passes it again, masking divergence

**File:** `src/construct/capabilities/catalog.py:372-376, 448`

**Issue:** In the MCP path, `_build_card_data` writes `card_data["author"] =
kwargs.get("author", "construct")` (a raw string) *and* the shim separately
passes `author=CardAuthor(...)` to `create_card`. In `create_card` (knowledge.py:159)
`data["author"]` is already present, so the `author=` parameter is silently
ignored. The two sources can diverge (string vs enum) and the parameter is dead.
This contradicts the CLI path (cli.py:771) which relies on the same dual-write,
so the redundancy is at least consistent — but it is a latent maintenance trap.

**Fix:** Pick one source of truth. Drop `author` from `_build_card_data` and let
`create_card`'s `author=` parameter populate it, or drop the `author=` argument
from the shim.

### WR-05: `graph.status` shim drops keyword `workspace`, relies on lambda forwarding

**File:** `src/construct/capabilities/catalog.py:262`

**Issue:** `handler=lambda workspace: graph_status(workspace)` accepts a single
parameter named `workspace`, which works for both `handler(workspace_id)`
(help.py:126) and `handler(workspace=...)` (MCP). However, if any future MCP
schema field is added to `GraphStatusInput` beyond `workspace`, the MCP layer
will call `handler(workspace=..., other=...)` and this lambda raises `TypeError`
on unexpected kwargs — the same RT-03 failure class this phase is closing.
Unlike the other capabilities it has no `**kwargs` tolerance or a named shim.

**Fix:** Use the explicit `**kwargs`-tolerant shim pattern used elsewhere, or
document that `GraphStatusInput` must remain single-field.

### WR-06: `domain or "_general"` fallback can write a ref whose domain fails validation

**File:** `src/construct/pipelines/ingestion.py:207` (exercised by ING-02 e2e path)

**Issue:** For NOTE/RESEARCH ingest with no domain configured, the ref is
written with `domain=domain_id or "_general"`. `_general` is not a real domain
in `domains.yaml`, so `validate_workspace` (validation.py:203) will hard-fail
that ref with "ref domain '_general' is not defined". The ING-02 e2e tests only
exercise the case where a domain *is* present (`domain_hint="cosmology"`), so
this divergent path is untested and reintroduces the same validation-failure
class ING-02 set out to eliminate. (Pre-existing, but in the blast radius of the
ING-02 "governed ingest must validate" guarantee.)

**Fix:** Fail the ingest with a clear `OperationResult` when no domain can be
resolved, rather than stamping a synthetic `_general` domain that cannot pass
validation.

### WR-07: Reserved-cluster domain reassignment mutates shared template-derived dict in-place

**File:** `src/construct/services/init.py:132-134`

**Issue:** `reserved_clusters = payload.get("clusters", [])` then mutates each
`cluster["domain"] = domain.domain_id` in place. `payload` comes from
`json.loads(...)` so it is a fresh object per call (safe today). But the same
in-place-mutation pattern is duplicated across three call sites
(`init.py:_write_search_seeds`, `test_validation_service.py:34-36`,
`test_schema_contracts.py` commentary) with copy-paste comments — a fragile
convention. If `payload` ever becomes a cached/shared template (a plausible
optimization), the reassignment corrupts the template for subsequent inits.

**Fix:** Build new cluster dicts rather than mutating in place, or assert the
payload is freshly parsed at the seam. At minimum, centralize the
"rewrite reserved-cluster domain" logic in one helper instead of duplicating it
across init + two test fixtures.

## Info

### IN-01: Unused imports in graph_status.py

**File:** `src/construct/pipelines/graph_status.py:6-8`

**Issue:** `KnowledgeCard`, `Lifecycle`, `ConnectionType`, and `OperationError`
are imported but `OperationError` is the only one used; `KnowledgeCard`,
`Lifecycle`, and `ConnectionType` are unused (lifecycle/type access goes through
`card.lifecycle.value` / `conn.type.value`).

**Fix:** Remove unused imports.

### IN-02: Unused import in help.py

**File:** `src/construct/services/help.py:10`

**Issue:** `OperationError` is imported from `construct.services.knowledge` but
never referenced in `help.py`.

**Fix:** Remove the unused import.

### IN-03: Reserved-cluster `weight: 0.0` is a magic placeholder with no documentation in the data files

**File:** `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json:9,17`; `test-ws/my-construct/search-seeds.json:34,42`; `test-ws/ping-eon/search-seeds.json:18,26`

**Issue:** The reserved ingest clusters use `weight: 0.0` and `terms: []` as
sentinel values meaning "not a real search cluster." Nothing in the data marks
them as reserved/system clusters; downstream consumers that rank or query
clusters by weight must special-case the IDs by string. The `help.py` stale bug
(CR-01) is a direct consequence of there being no first-class "is this a
research cluster?" distinction.

**Fix:** Consider a `reserved: true` (or `kind: "ingest"`) field on these
clusters so consumers can filter structurally instead of by ID string or weight.

### IN-04: `test_every_mcp_handler_invokes_without_type_error` swallows all non-TypeError outcomes

**File:** `tests/contract/test_mcp_contracts.py:134-139`

**Issue:** The gate only asserts "no TypeError." Real handler failures
(ValueError from enum coercion per WR-03, validation failures, etc.) are caught
and ignored. This is intentional per the docstring, but it means the test gives
false confidence that the MCP tools "work" when it only proves the signature
matches. Pair it with `test_previously_broken_tools_return_result` mentally, but
note the latter covers only 5 of 11 tools.

**Fix:** Document the narrow scope in the test name (e.g.
`_accepts_advertised_schema_without_signature_mismatch`) and add positive-result
assertions for the remaining handlers where a deterministic success path exists.

---

_Reviewed: 2026-06-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
