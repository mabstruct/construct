# spec-v02-data-generation — `views-generate-data` Skill

**Status:** Accepted
**Date:** 2026-04-28
**Accepted:** 2026-04-29 (verified end-to-end: 11 files written from a multi-card test fixture; envelope correct; determinism verified — `build_id` identical across two runs against unchanged state; `source_cards[]` expansion produces full objects for present cards and `{status: "missing"}` for absent; `connects_to` denormalised correctly; broken card with missing required fields logged + excluded; safe-delete invariant verified by content-stable build_id)
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 5
**Related:** `spec-v02-data-model.md` · `spec-v02-runtime-topology.md` §4 · `architecture-overview.md` §3.2, §4 · `prd-v02-live-views.md` §5.1 · `templates/*` and `references/*` in `CONSTRUCT-CLAUDE-impl/`

---

## 1. Scope

This spec defines the **`views-generate-data` skill**: the only legitimate writer to `views/build/data/` and `views/build/version.json` (architecture-overview invariant I1).

It reads workspace state from canonical files and produces the JSON contracts defined in `spec-v02-data-model.md`.

**In scope:**
- File discovery (which workspaces, which files)
- Per-schema parsing rules (markdown frontmatter, JSON, JSONL)
- Aggregate / cross-cutting computation
- `build_id` hashing and `version.json` write
- Determinism rules and failure handling
- Skill invocation contract (trigger, inputs, outputs, error reporting)

**Out of scope:**
- The JSON shape itself → `spec-v02-data-model.md`
- Build pipeline (`views-scaffold`, `views-build`) → `spec-v02-build-pipeline.md`
- Server lifecycle → `spec-v02-runtime-topology.md`
- Hook integration (which existing v0.1 skills trigger this one) → Epic 9 / `spec-v02-hook-integration.md`

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Implementation strategy | Procedural SKILL.md + Python helper script for the heavy lifting (file scan, frontmatter parse, JSON serialise, hashing). Claude orchestrates; script does the deterministic work |
| Helper script location | `CONSTRUCT-CLAUDE-impl/skills/views-generate-data/generate.py` |
| Python dependencies | Standard library only where possible. `pyyaml` and `python-frontmatter` if frontmatter parsing warrants. Listed in skill's own `requirements.txt`; resolution strategy in §3.3 |
| Regeneration mode | **Full only for v0.2.** Always re-scan everything, always rewrite all files. Incremental regeneration deferred to v0.2.1 |
| Workspace discovery | Scan install root for subdirectories that look like workspaces (presence of `cards/` directory OR `domains.yaml` file). Excluded: `.construct/`, `views/`, dotfiles, anything matching `.gitignore` patterns |
| `domains.yaml` location | Honour both layouts: install-root level (preferred) AND per-workspace level (legacy v0.1). Merge into `domains.json` |
| Failure on corrupt input | Per data-model spec §9: never silently drop. Corrupt cards excluded from `cards.json` but logged with workspace + filename + reason. Other corrupt files surface as `{"parse_status": "partial"}` envelope fields |
| Determinism | Per data-model spec §8: sorted arrays, sorted object keys, no clock-derived data inside payloads. `generated_at` lives in envelope only |
| `build_id` algorithm | `sha256(concat(sorted(data_file_contents)))` truncated to 8 hex chars. Excludes envelope `generated_at` from hash computation (envelope hashed without that field) |
| Empty workspace | Produces valid JSON with empty arrays for every collection. No special-case skipping |
| Skill exits non-zero | Only on catastrophic errors (no install root, IO failure, script missing). Per-file parse errors are logged and continue |

---

## 3. Skill Architecture

### 3.1 Why a helper script

Pure Claude execution would mean: Read → parse → Write for every file (cards alone could be 100+). For each file: 2–3 tool calls. For a medium workspace: hundreds of tool calls per generation, fired on every research-cycle hook. That's slow, expensive, and brittle (tool-call retries can interleave badly).

A small Python script (~150–200 lines) does the deterministic work in one process. The skill's SKILL.md instructs Claude to invoke the script and report the result. This keeps "Claude orchestrates" while pushing tedious work to code.

This is consistent with ADR-0001's "Future Enhancements" section, which explicitly contemplates Python helpers and MCP servers as additive layers, not violations of the Claude-native principle.

### 3.2 Boundary

The script is a **pure function**: workspace files in, JSON files out. No network, no agent calls, no state beyond the filesystem.

```
                                    SKILL.md (procedural)
                                          │
                                          │ Bash: python generate.py <install-root>
                                          ▼
                                    generate.py (deterministic)
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            │ READ                        │                          WRITE
            ▼                             │                             ▼
    workspace files (canonical)           │                  views/build/data/*.json
    cards/, connections.json,             │                  views/build/version.json
    domains.yaml, refs/, digests/,        │
    publish/, log/events.jsonl,           │
    curation-reports/                     │
                                          │
                                          ▼
                                    stdout: summary report
                                    (workspaces processed, counts, errors)
                                          │
                                          ▼
                                    Claude reads stdout, reports to user
```

### 3.3 Python dependency strategy

Three options, pick at implementation time:

- **(a) Stdlib only** — write a minimal frontmatter parser ourselves. Pure Python 3.9+, no `pip install` needed. Recommended for true zero-dep MVP.
- **(b) Vendored deps** — bundle `pyyaml` and `python-frontmatter` into the skill directory. No `pip install` needed but increases skill size.
- **(c) System deps** — declare `pyyaml`, `python-frontmatter` in `requirements.txt`, expect them globally available or via venv.

**Lean (a) stdlib only.** Frontmatter is `--- ... ---` delimited YAML — a 30-line parser handles it. YAML for `domains.yaml` is more complex but our usage is shallow (one-level dict of dicts), and PyYAML is in the existing repo `pyproject.toml`. So actually **(c) with PyYAML only** is fine: leverage the existing Python infrastructure in `pyproject.toml` (the repo already has `.venv/` and `pyproject.toml` from v0.1 Python explorations).

Decision deferred to skill implementation; spec contract is "the script runs and produces correct output."

### 3.4 SKILL.md procedure

1. Resolve install root (default: cwd).
2. Verify install root has `AGENTS.md` and `.construct/` (sanity check).
3. Verify `views/build/` exists (created by `views-build`). If not → fail with `"views/build/ not found. Run views-build first."`
4. Invoke `python <skill-dir>/generate.py <install-root>` via Bash.
5. Read script stdout. Format:
   ```
   workspaces: 2
     cosmology: 47 cards, 184 connections, 12 digests, 3 articles
     climate-policy: 23 cards, 41 connections, 5 digests, 1 article
   global: 4 articles total
   build_id: a3f81c2d
   warnings: 1 (cosmology/cards/orphaned-finding-2026-04-12.md: missing required field 'epistemic_type')
   ```
6. Report to user. If non-zero exit code, report the failure verbatim.

---

## 4. Workspace Discovery

### 4.1 Discovery rule

Iterate immediate subdirectories of the install root. A subdirectory is a **workspace** if any of:

- contains a `cards/` directory, OR
- contains a `domains.yaml` file, OR
- contains both `connections.json` and `governance.yaml`

**Excluded:** any of these names: `.construct`, `views`, `node_modules`, `.venv`, `.git`, `.pytest_cache`, plus any directory starting with `.` or `_`.

### 4.2 Workspace ID

The directory name itself is the workspace ID (per data-model spec §3.2). Must be kebab-case and filesystem-safe — `workspace-init` enforces this in v0.1.

If a discovered directory has a name that's not URL-safe (spaces, unicode, etc.), the script logs a warning and skips it: `"skipped 'My Workspace' (non-URL-safe name; rename or use kebab-case)"`. The data-generation continues with other workspaces.

### 4.3 Per-workspace files

For each workspace, the script expects (all optional — missing files produce empty arrays, not errors):

```
<workspace>/
├── cards/               *.md (frontmatter + body)
├── connections.json     (canonical edges, may be missing for empty workspace)
├── domains.yaml         (legacy v0.1; merged into global if present)
├── refs/                *.json (papers — counted but full data not surfaced in v0.2)
├── digests/             *.md (research-cycle outputs)
├── publish/             *.md (synthesis outputs → cross-workspace articles)
├── log/events.jsonl     (event stream)
└── curation-reports/    *.md (curation-cycle outputs)
```

---

## 5. Per-Schema Parsing Rules

Each subsection refers to its data-model schema by §-number.

### 5.1 `cards.json` (data-model §5.2)

**Source:** `<workspace>/cards/*.md`

Per file:
1. Read file
2. Extract YAML frontmatter (between leading `---` markers)
3. Validate required fields: `id`, `title`, `epistemic_type`, `confidence`, `source_tier`, `lifecycle`. If any missing → log warning, skip card, continue.
4. Parse body (everything after closing `---`)
5. Compute `summary_excerpt` = first 200 chars of the `## Summary` section (or first 200 chars of body if no Summary header), with markdown stripped to plain text
6. Construct card object per data-model §5.2
7. `connects_to` is denormalised from `connections.json` (post-parse step §5.3)

Sort cards by `id` ASC (per data-model §8).

### 5.2 `connections.json` (data-model §5.3)

**Source:** `<workspace>/connections.json`

1. Read JSON. If file missing → produce `{"connections": [], "type_counts": {...all-zero}}`.
2. For each entry in `connections`:
   - Add stable `id` if missing (e.g., `conn-<sha8>(source+target+type)`)
   - Validate `type` is in canonical 9-type list (per `references/connection-types.md`); if not → log warning + assign `type: "unknown"`
3. Compute `type_counts` map.
4. Sort by `(source, target, type)` ASC.

### 5.3 `connects_to` denormalisation (cards.json fixup)

After parsing both `cards.json` and `connections.json`:

For each card, `connects_to` is the deduplicated, sorted list of all card IDs that appear as the *other endpoint* in any connection involving this card (either direction).

This is purely derived; the source of truth for connections remains `connections.json`.

### 5.4 `domains.json` (data-model §5.1, global)

**Sources:**
- `<install-root>/domains.yaml` (preferred for v0.2)
- `<workspace>/domains.yaml` (legacy v0.1) — merged in if root-level absent

For each declared domain:
1. Read taxonomy fields from YAML (`name`, `description`, `status`, `created`, `content_categories`, `source_priorities`, `cross_domain_links`)
2. Compute `metrics` block by inspecting workspace files:
   - `papers` = count of `<workspace>/refs/*.json`
   - `cards` = count of cards (post-parse)
   - `cards_by_lifecycle`, `cards_by_confidence` = histograms over cards
   - `connections` = count of edges
   - `orphan_cards` = cards with zero connections
   - `avg_confidence` = mean over cards
   - `last_research_cycle` = max digest date
   - `last_curation_cycle` = max curation-report date
3. Construct domain entry per data-model §5.1
4. Sort domains by `id` ASC.

### 5.5 `digests.json` (data-model §5.4)

**Source:** `<workspace>/digests/**/*.md`

Per file (one digest per file):
1. Derive `id` from filename (e.g., `2026-04-25-digest.md` → `2026-04-25-digest`)
2. Parse frontmatter if present (date, domain, theme); else extract from headings/lines per `templates/digest.md`
3. Parse Summary section into `summary_text`, `papers_found`, `papers_ingested`, `papers_skipped`, `seed_cards_created`
4. Parse Top Findings section into `top_findings[]` array
5. Parse Search Clusters table into `search_clusters[]`
6. Parse Coverage Notes / Suggested Adjustments sections into their fields
7. Add `raw_path` = relative path from workspace root

If any section fails to parse: include the digest with `parse_status: "partial"` envelope field and only the fields that parsed cleanly. Never drop the digest.

Sort by `date` DESC.

### 5.6 `articles.json` (data-model §5.5, global)

**Source:** `<workspace>/publish/**/*.md` for every workspace

Per file:
1. Read and parse frontmatter (title, type, status, date, domains, source_cards, confidence_floor)
2. Body = everything after frontmatter
3. `excerpt` = first 280 plain-text chars of body
4. `id` = derived from filename or frontmatter slug
5. Resolve `source_cards`:
   - For each card ID in frontmatter, find the matching card across all workspaces
   - If found: emit `{id, workspace_id, title, epistemic_type, confidence, contribution}` (where `contribution` comes from the article's Sources table)
   - If not found: emit `{id, status: "missing"}` per data-model §5.5
6. `workspaces` = set of workspace IDs the source cards live in (deduplicated, sorted)

Sort articles by `date` DESC.

### 5.7 `events.json` (data-model §5.6, per-workspace)

**Source:** `<workspace>/log/events.jsonl`

1. Read last 100 lines of the file (tail). If file missing → empty array.
2. Each line is a JSON object. Parse strictly; lines that fail to parse are logged as warnings and skipped (do NOT halt processing).
3. Filter to documented event types (Epic 9 will codify the allowlist; for v0.2 MVP, accept all event types).
4. Sort by `timestamp` DESC.

### 5.8 `stats.json` (data-model §5.7, global + per-workspace)

**Per-workspace** stats: computed from same workspace's parsed cards + connections + digests + articles + refs. See data-model spec §5.7 for fields.

**Global** stats: aggregation across all workspaces. `totals` are sums; `by_lifecycle` and `by_confidence` are merged histograms; `activity_last_30d` filters event timestamps to last 30 days.

Computation order:
1. Process all per-workspace files first (so per-workspace stats are computed)
2. Then aggregate into global stats

### 5.9 `curation-history.json` (data-model §5.8, per-workspace)

**Source:** `<workspace>/curation-reports/CURATION-REPORT-*.md`

Per file:
1. Derive `id` and `date` from filename
2. Parse summary section (first paragraph after a `## Summary` heading, or first paragraph of body)
3. Parse `deltas` from a structured section (template TBD — currently `daily-cycle.md` workflow doesn't standardise this format). For v0.2 MVP, attempt heuristic extraction (look for `Promoted: N`, `Archived: N`, etc. patterns); fall back to zeros if not found
4. `raw_path` = relative path

Sort by `date` DESC.

---

## 6. Aggregate / Cross-Cutting

### 6.1 `version.json` and `build_id`

After all data files are written:

1. Compute SHA-256 over the deterministic concatenation of:
   - all data file contents, in path-sorted order
   - excluding the `generated_at` field from each file's envelope (because that varies between identical-state runs)
2. Truncate to first 8 hex chars → `build_id`
3. Write `views/build/version.json`:
   ```json
   {
     "schema_version": "0.2.0",
     "build_id": "<8-hex>",
     "generated_at": "<UTC ISO-8601 to second precision>"
   }
   ```

### 6.2 Envelope on every data file

Per data-model §4:

```json
{
  "schema_version": "0.2.0",
  "generated_at": "2026-04-28T14:32:11Z",
  "workspace_id": "cosmology",          // omitted for global files
  "build_id": "a3f81c2d",
  "data": { /* schema-specific */ }
}
```

`build_id` is computed first (over deterministic content), then stamped into all envelopes.

### 6.3 Determinism guarantees

- All array elements sorted by stable key (per-schema rules in §5)
- All object keys serialised alphabetically (`json.dumps(..., sort_keys=True, indent=2)`)
- All timestamps in events truncated to second precision
- `generated_at` is the **only** wall-clock-derived field; lives only in envelopes; excluded from `build_id` computation

Acceptance check (also in `spec-v02-data-model.md` §10): two runs against identical workspace state produce byte-identical files (modulo `generated_at`).

---

## 7. Failure Handling

### 7.1 Categories

| Severity | Examples | Behavior |
|---|---|---|
| **Catastrophic** (skill exits non-zero) | install root not found, no write permission to `views/build/`, generate.py crashes | Single error to stdout, non-zero exit, no partial state written |
| **Per-workspace** | workspace directory unreadable | Skip workspace, log warning, continue |
| **Per-file** (skipped) | corrupt frontmatter, missing required field, JSON parse error | Skip file, log warning, continue |
| **Per-file** (partial) | digest with unparseable section | Include with `parse_status: "partial"`, include only clean fields |

### 7.2 Logging

All warnings collected during a run are written to:
- stdout (so Claude reports to user)
- `views/build/data/_generation-warnings.log` (a small audit trail; included in `build_id` hash so it's deterministic across reruns)

The log file itself is a JSON array, one entry per warning:
```json
[
  {"workspace": "cosmology", "file": "cards/orphaned-finding-2026-04-12.md", "reason": "missing required field 'epistemic_type'"},
  ...
]
```

The SPA does not surface this log; it's for debugging.

### 7.3 Atomicity

Writes use a write-to-temp-then-rename pattern per file:
1. Write JSON content to `<dest>.tmp`
2. `os.rename(<dest>.tmp, <dest>)` (atomic on POSIX)

If the script crashes mid-run, `views/build/data/` may have a mixed state (some files at new build_id, some at old). The next successful run will repair. For v0.2 MVP, we accept this transient mix because:
- The browser sees one global `version.json` (last to be written)
- A reload after the next successful run gets a consistent set
- The SPA is read-only; it doesn't fail when one file lags

A v0.2.1 enhancement could write to a staging directory and atomically swap. Not blocking for MVP.

---

## 8. Regeneration Mode

### 8.1 v0.2 — full only

Every invocation re-scans every workspace, re-parses every file, recomputes every aggregate, rewrites every JSON. Always.

For typical workspaces (≤500 cards), this completes in seconds.

### 8.2 v0.2.1 — incremental (deferred)

Future enhancement: track input file mtimes per output file. Skip files that haven't changed since last generation. Cache aggregates that depend on unchanged inputs.

Why deferred:
- Requires a state file mapping inputs → outputs (more state to maintain)
- Determinism becomes harder to verify
- v0.2 throughput is already adequate
- Easy to retrofit once the full path is proven correct

---

## 9. Skill File Layout

```
CONSTRUCT-CLAUDE-impl/skills/views-generate-data/
├── SKILL.md                     (procedural recipe per §3.4)
├── generate.py                  (main entry point — argv: install-root)
├── lib/                         (broken out for testability)
│   ├── discover.py              (§4 workspace discovery)
│   ├── parse_cards.py           (§5.1)
│   ├── parse_connections.py     (§5.2)
│   ├── parse_domains.py         (§5.4)
│   ├── parse_digests.py         (§5.5)
│   ├── parse_articles.py        (§5.6)
│   ├── parse_events.py          (§5.7)
│   ├── compute_stats.py         (§5.8)
│   ├── parse_curation.py        (§5.9)
│   ├── envelope.py              (§6.2 envelope wrapping)
│   └── build_id.py              (§6.1 hashing)
└── tests/                       (small set of fixtures + test cases)
    ├── fixtures/
    │   ├── small-workspace/
    │   ├── empty-workspace/
    │   └── corrupt-cards-workspace/
    └── test_generate.py
```

Tests are written alongside the implementation but are **not required for v0.2 MVP delivery**. They are validated against this spec via Epic 10 (validation).

---

## 10. Acceptance Checks

This spec is implemented when:

- [ ] `views-generate-data/SKILL.md` exists with procedure per §3.4
- [ ] `views-generate-data/generate.py` exists and is the only writer to `views/build/data/`
- [ ] Running on an empty install (no workspaces) produces valid JSON with empty arrays for every collection (data-model spec §9)
- [ ] Running on a single-workspace install produces all 8 schemas correctly populated
- [ ] Running on a multi-workspace install produces correct per-workspace files plus correct global aggregations
- [ ] **Determinism (data-model spec §8 / arch-overview I3 / I4):** two runs against unchanged workspace state produce byte-identical files (excluding `generated_at`)
- [ ] **Safe-delete (arch-overview I3):** `rm -rf views/build/data/` followed by `views-generate-data` produces byte-identical output
- [ ] Corrupt card (missing required frontmatter field) is logged as a warning and excluded from `cards.json`; other cards unaffected
- [ ] Article referencing a missing card surfaces as `{"status": "missing"}` (data-model spec §5.5)
- [ ] `version.json` is written last and contains the correct `build_id` matching every data file's envelope
- [ ] `views/build/data/_generation-warnings.log` exists when warnings occurred; absent when none
- [ ] Script never writes to `views/build/{index.html, assets/}` (those are owned by `views-build`) — verifiable by file mtime check
- [ ] Skill exits non-zero on catastrophic failure with a single-line error message; exits zero (success) when only per-file warnings occurred
- [ ] No clock-derived data appears in any `data` field — only in envelope `generated_at`

---

## 11. Open Follow-ups

1. **`domains.yaml` migration.** v0.2 honours both root-level and per-workspace layouts. v0.3 may force a single layout. Decision deferred — collect data on which is preferred in practice.
2. **Curation report parsing.** §5.9 says "heuristic extraction" of deltas. The actual `daily-cycle.md` workflow could standardise the report format (e.g., a YAML frontmatter block in CURATION-REPORT-*.md). That's an Epic 9 concern (skill integration). For v0.2, accept partial extraction.
3. **Event-type allowlist.** §5.7 says "accept all event types" for v0.2 MVP. Epic 9 will define the canonical set.
4. **Script's Python version target.** Recommend Python 3.10+ (matches `pyproject.toml` of this repo). Confirm during implementation.
5. **Performance budget.** No explicit timing target for v0.2. Soft expectation: ≤5s for a 500-card workspace. If this is exceeded, consider:
   - Parallel per-workspace processing (multiprocessing)
   - Native YAML/JSON parsers (`ujson`)
   - Incremental mode (v0.2.1)
6. **Concurrent invocation.** What happens if `views-generate-data` is invoked twice simultaneously (e.g., two skills hooking on top of each other)? For v0.2 MVP, recommend a simple lock-file at `views/.generate.lock`. If lock present → second invocation no-ops with "already running" message.

---

## 12. References

- `spec-v02-data-model.md` — every JSON shape this skill produces (the contract)
- `spec-v02-runtime-topology.md` §4 (`version.json` polling — what the SPA does with our output)
- `architecture-overview.md` §3 (three layers), §4 (four invariants — especially I1 single-writer)
- `prd-v02-live-views.md` §5.1 (`views-generate-data` original spec)
- `templates/card.md`, `templates/connections.json`, `templates/digest.md`, `templates/publish.md`, `templates/ref.json`, `templates/domains.yaml` — input file shapes
- `references/epistemic-types.md`, `connection-types.md`, `lifecycle-states.md`, `confidence-levels.md`, `source-tiers.md` — vocabulary the parser validates against
- `adrs/adr-0001-claude-native-approach.md` — "future enhancements" section that legitimises Python helpers
- `adrs/adr-0002-v02-packaging.md` — places this skill at `CONSTRUCT-CLAUDE-impl/skills/views-generate-data/`
- `CONSTRUCT-CLAUDE-impl/VERSION` — `schema_version` value
