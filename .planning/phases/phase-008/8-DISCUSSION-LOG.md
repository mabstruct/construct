# Phase 8: Search Provider Spine + Contract Foundation — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-21
**Phase:** 8-Search Provider Spine + Contract Foundation
**Areas discussed:** Config location, Interface scope, Result normalization, Mock fidelity, MCP/CLI surface, search-seeds relationship, Error taxonomy

---

## Area 1: Search Config Location

| Option | Description | Selected |
|--------|-------------|----------|
| Workspace-level only | `.construct/search.yaml` — users configure per workspace | ✓ |
| Project-level only | `src/construct/search/config.yaml` — fixed at build time | |
| Both levels | Project defaults + workspace overrides | |

**User's choice:** Workspace-level only
**Notes:** Provider registration is a user-facing workspace choice, mirroring model-routing.yaml but without dual-layer complexity.

---

## Area 2: Provider Interface Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (1 method) | `search(query, max_results, domain_filter?) -> SearchResult` | |
| Rich (3-4 methods) | `search()` + `search_batch()` + `search_by_seed_cluster()` + `get_capabilities()` | ✓ |
| Minimal + capabilities | `search()` + `get_provider_info()` | |

**User's choice:** Rich (3-4 methods)
**Notes:** Seed-cluster awareness needed for Phase 10 integration. Batch for efficiency. Capabilities for dynamic routing.

---

## Area 3: Result Normalization

| Option | Description | Selected |
|--------|-------------|----------|
| Highly normalized | All providers return identical SearchResult | |
| Hybrid (core + extras) | Core fields + `provider_specific: dict[str, Any]` | ✓ |
| Per-provider schema | Discriminated union per provider | |

**User's choice:** Hybrid (core + extras)
**Notes:** Core normalized fields for consumer simplicity, provider-specific blob preserves optional data.

---

## Area 4: Mock Provider Fidelity

| Option | Description | Selected |
|--------|-------------|----------|
| Static canned responses | One fixture file, fixed returns | |
| Configurable fixture sets | Per-query mapping + latency + error injection | ✓ |

**User's choice:** Configurable fixture sets
**Notes:** SRCH-04 requires error simulation (rate limit, network, auth). Static responses inadequate.

---

## Area 5: MCP/CLI Surface

| Option | Description | Selected |
|--------|-------------|----------|
| CLI + MCP (both) | Both surfaces via capability registry | ✓ |
| CLI only | CLI command only | |
| Python API only | Internal service only | |

**User's choice:** CLI + MCP (both)
**Notes:** Default registry behavior; no reason to opt out. Agents use MCP, users use CLI.

---

## Area 6: search-seeds.json Relationship

| Option | Description | Selected |
|--------|-------------|----------|
| Direct queries only | Search accepts query strings only | |
| Both direct + seed-driven | Direct query AND `search_by_seed_cluster()` | ✓ |

**User's choice:** Both direct + seed-driven (after implications explanation)
**Notes:** User asked for implications before deciding. Chose seed-driven to set up Phase 10 integration, avoiding rework later.

---

## Area 7: Error Taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Single SearchError | One class with category + retryable flag | |
| Granular error types | NetworkError, RateLimitError, AuthError, etc. | ✓ |
| Granular + retry strategy | Granular + suggested_retry_delay + fallback_providers | |

**User's choice:** Granular error types
**Notes:** Independently catchable and testable. Each carries structured metadata.

---

## The Agent's Discretion

- Config file naming: Default to `.construct/search.yaml` (user chose workspace-level but didn't specify filename)

## Deferred Ideas

- Provider health-check / ping method — deferred to Phase 10
- Multi-provider automatic failover — not in requirements
- Search result caching — outside v0.4 scope
- Web scraping beyond search results — future milestone
