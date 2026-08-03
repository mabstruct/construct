# HTTP exposure ledger

**This file is read by a test.** `tests/contract/test_http_surface.py` parses the
tables below and asserts, as cardinality rather than as set membership, that the
capabilities reachable over HTTP plus the capabilities listed under
[Exclusions](#exclusions) exhaust the registry exactly. So an exclusion cannot be
introduced in prose: adding one here is what makes the guard's arithmetic work
out, and *not* adding one is what makes an unreachable capability fail the suite.

It lives at `src/construct/api/COVERAGE.md`, beside the package it constrains,
rather than in `.planning/` (D-18). A planning document cannot participate in an
assertion, and the whole reason this artifact is worth writing is that it can.

## How to read it

The parse contract is deliberately dull, so the guard needs no markdown library:

- Section headings are exactly the `##` headings below and must not be renamed.
- Every table is a pipe table whose **first column is a capability id in
  backticks**. The guard strips the backticks and ignores every other column.
- A row is a claim. Prose around a table is for humans and is never parsed.

## Capability table

One row per registered capability, and the guard asserts exactly that: every
registered id appears here once, and nothing appears here that is not registered.
Adding a capability to the registry therefore requires adding a row — the same
class of deliberate tripwire as `REGISTRY_SIZE` in
`tests/contract/test_capability_seam.py`.

"Addressed by" is how a browser names the target, never how the capability's own
model spells it. The spelling is in the third column because the two differ for
27 of the 29 capabilities, and that difference is the whole job of
`WORKSPACE_FIELD` / `INSTALL_ROOT_FIELD` in `construct/capabilities/workspaces.py`.
Every one of those declared field names is a `PATH_SHAPED_KEYS` entry, so a client
may never send it (D-10) — the caller sends `workspace_id` and the seam rewrites.

| Capability id | Addressed by | Declared field | Note |
|---|---|---|---|
| `ask.domain` | `workspace_id` | `workspace_path` | |
| `bridge.detect` | `workspace_id` | `workspace_path` | |
| `card.evaluate` | `workspace_id` | `workspace_path` | |
| `curation.inspect` | `workspace_id` | `workspace_path` | |
| `curation.review` | `workspace_id` | `workspace_path` | |
| `curation.run` | `workspace_id` | `workspace_path` | |
| `daily.inspect` | `workspace_id` | `workspace_path` | |
| `daily.run` | `workspace_id` | `workspace_path` | |
| `graph.status` | `workspace_id` | `workspace` | |
| `help.suggest` | `workspace_id` | `workspace` | |
| `ingest.source` | `workspace_id` | `workspace` | |
| `knowledge.card.archive` | `workspace_id` | `workspace` | No MCP tool name — invisible to `list_mcp_tools()` |
| `knowledge.card.create` | `workspace_id` | `workspace` | |
| `knowledge.card.edit` | `workspace_id` | `workspace` | |
| `knowledge.card.list` | `workspace_id` | `workspace` | |
| `knowledge.connection.add` | `workspace_id` | `workspace` | |
| `knowledge.connection.list` | `workspace_id` | `workspace` | No MCP tool name — invisible to `list_mcp_tools()` |
| `knowledge.connection.remove` | `workspace_id` | `workspace` | No MCP tool name — invisible to `list_mcp_tools()` |
| `research.inspect` | `workspace_id` | `workspace_path` | |
| `research.review` | `workspace_id` | `workspace_path` | |
| `research.run` | `workspace_id` | `workspace_path` | |
| `research.score` | `workspace_id` | `workspace_path` | |
| `research.search` | `workspace_id` | `workspace_path` | |
| `views.generate_data` | launch-supplied `install_root` | `install_root` | Scope mismatch open — see below; plan 19-04 owns it |
| `views.validate_data` | launch-supplied `install_root` | `install_root` | Scope mismatch open — see below; plan 19-04 owns it |
| `workflow.list` | `workspace_id` | `workspace` | D-13: registered with BOTH names, so CLI, MCP and HTTP gain run enumeration at the same moment |
| `workflow.status` | `workspace_id` | `workspace` | No MCP tool name — invisible to `list_mcp_tools()` |
| `workspace.init` | `workspace_id`, creation mode | `root` | Directory must **not** exist yet, so the allowlist gate is skipped (`CREATE_MODE_CAPABILITIES`) |
| `workspace.status` | `workspace_id` | `path` | No MCP tool name — invisible to `list_mcp_tools()` |
| `workspace.validate` | `workspace_id` | `path` | |

Six rows carry "No MCP tool name". They are the measured reason `GET
/api/capabilities` iterates `registry.list()` and not `list_mcp_tools()`: the
latter would return 23 rows, and a membership test over those 23 would pass.

**The `views.*` scope mismatch, recorded rather than smoothed over.** Both views
capabilities are scoped to the install root — `discover_workspaces` scans its
argument's *children*. A `workspace_id` resolves to one workspace, so an
id-addressed views call scans that workspace's children and finds nothing, while
sending `install_root` directly is refused by D-10. Both capabilities are
therefore *reachable* (the id resolves, the model validates, the handler runs)
and not yet *usefully* addressable. Reachability is what this ledger asserts;
usefulness is HTTP-03's completion, which plan 19-04 owns. Writing the gap down
is the point — a ledger that only recorded good news would not be worth parsing.

## Exclusions

Capabilities registered but deliberately **not** reachable over HTTP. The guard
subtracts this table from the registry, so a row here is a licence for a
capability to be unreachable — which is exactly why each one must carry a reason
and a decision reference.

**This table currently has no rows, and that is the finding.** Every registered
capability is reachable. The table exists so that a future exclusion has a place
to be justified in a form a test can see, rather than being introduced as a
sentence somebody skims. Its value is prospective: an exclusion added without a
row here does not "go undocumented", it fails the suite.

| Capability id | Reason it is not reachable | Decision reference |
|---|---|---|

<!-- Zero rows above is intentional. Adding one is a deliberate act: the guard in
     tests/contract/test_http_surface.py parses this table, and a row is what
     lets its cardinality assertion tolerate an unreachable capability. -->

## Non-capability routes

Routes this server exposes that are **not** capability dispatch, and are
therefore outside the zero-edit coverage guard's subject (D-20). Written down so
a reader can neither miscount them as capabilities nor meet them later as an
undocumented surface. The first column is a route, not a capability id.

This table is parsed too, in the one direction that can catch something: every
non-dispatch `/api` route the app actually exposes must appear here. The reverse
does not hold, because a row may be written *before* the plan that adds the
route — which is how `POST /api/runs` was listed before plan 19-09 built it.

| Route | Added by | Why it is not a capability route |
|---|---|---|
| `GET /api/capabilities` | plan 19-05 (D-06) | Discovery. It advertises the registry rather than dispatching through it, so no `CapabilityRegistry.invoke` call happens and there is no capability id to count. |
| `POST /api/runs` | plan 19-09 (D-12) | Run addressability, and the **only** operation the capability envelope structurally cannot express: a capability call is synchronous, while HTTP-06 requires the run id to return immediately with the run pollable while it is still going. Starting is therefore a route; polling and resume stay on the envelope through the existing inspect and review capabilities, which is what keeps this table two rows long rather than growing one row per run operation. |

Both sit behind the same `LocalhostGuard`, so "not a capability route" is a
statement about the coverage guard's subject and never about the trust boundary.

**What `POST /api/runs` does not do, recorded so a later reader does not have to
infer it.** It never drives the workflow graph. A resume is submitted through
`curation.review` / `research.review`, which wrap the decision payload before it
reaches LangGraph — a bare id-keyed map handed to `Command(resume=…)` is read as
an *interrupt-id* mapping, silently consumed as an empty resume, and leaves the
run paused with zero writes and a well-formed success response. That is the one
failure this route's shape is chosen to make unreachable.

## Out of scope by construction

Two things RESEARCH asked not be left silent. Neither is an exclusion — an
exclusion is a *registered* capability made unreachable, and neither of these is
registered — so neither belongs in the table above.

**`spike` and `tag` are not in the registry at all.** They are CLI-only command
groups, so there is nothing for the HTTP surface to opt out of. This is worth
stating because `spike run --tool-path` is a remote-code-execution primitive by
design: it runs a caller-named tool. Its absence from the registry is what keeps
it off every non-CLI surface, and that absence is load-bearing rather than
incidental. A future registration of either would put an RCE primitive one HTTP
POST from a browser page, and would be a security decision, not a coverage fix.

**Unbounded run spawning is accepted, not mitigated (T-19-10).** Nothing limits
how many workflow runs a caller may start. For a single-user server bound to
127.0.0.1 behind a per-launch token, the only caller who can exhaust the machine
is the user who launched it. Recorded here rather than left silent because the
disposition is *accept*: if this surface ever leaves the loopback — or grows a
second user — the acceptance expires and this paragraph is where the next reader
finds out it was a choice.
