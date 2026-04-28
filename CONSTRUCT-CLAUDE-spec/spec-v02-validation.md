# spec-v02-validation — Validation, Acceptance, and Fixtures

**Status:** Draft
**Date:** 2026-04-28
**Owner:** ;-)mab
**Closes Epic:** `../CONSTRUCT-CLAUDE-v02-planning/backlog.md` Epic 10
**Related:** all `spec-v02-*.md` (this spec consolidates their acceptance checks) · `architecture-overview.md` §4 · `prd-v02-live-views.md` §9

---

## 1. Scope

This spec defines **how we know v0.2 is done**. It consolidates acceptance checks already scattered across the other v0.2 specs into a single executable plan, defines the fixture workspaces needed to run those checks, and adds adversarial tests for the four architecture invariants.

**In scope:**
- Fixture workspace definitions (small, medium, adversarial)
- Cross-spec acceptance check matrix
- Source-of-truth invariant tests (architecture-overview §4)
- Broken-data resilience tests (data-model §9, data-generation §7)
- End-to-end smoke test sequence
- Performance expectations
- Portability expectations

**Out of scope:**
- Per-spec acceptance check authoring (already in each spec's §10 / acceptance section)
- Automated test framework choice (deferred — v0.2 validation is manual + scripted, not unit-tested)
- CI integration (deferred to v0.2.1)

---

## 2. Decisions Summary

| Concern | Decision |
|---|---|
| Validation style | **Manual + scripted smoke tests.** No unit test framework in v0.2. Each fixture has a `verify.md` describing expected outcome; the human runs the smoke and confirms |
| Fixture location | `tests/fixtures/v02/` at repo root (alongside existing `tests/`) |
| Fixture set | 4 fixtures: `empty`, `single-domain-small`, `multi-domain-medium`, `adversarial-corrupt` |
| Performance targets | Small (≤50 cards): full pipeline (generate→build→up) ≤30s. Medium (≤500 cards): ≤90s. Beyond → not budgeted |
| Browser performance | Knowledge graph 500 nodes ≥30fps. Artifacts table 1000 rows ≤500ms initial render |
| Portability targets | macOS 13+, Linux (Ubuntu 22+ / Fedora 38+). Windows untested in v0.2 |
| Browser targets | Chrome / Firefox / Safari latest stable. No Edge-specific testing |
| Failure validation | Every adversarial fixture run produces a documented expected outcome — never an unexpected crash |
| Acceptance owner | ;-)mab signs off each fixture's `verify.md` before v0.2 ships |

---

## 3. Fixture Workspaces

All fixtures live under `tests/fixtures/v02/`. Each is a complete CONSTRUCT install (with `AGENTS.md`, `.construct/`, workspaces, optionally a `views/` after running views-scaffold).

### 3.1 `empty/`

**Purpose:** No workspaces yet. Validates first-run UX, empty-render code paths.

```
tests/fixtures/v02/empty/
├── AGENTS.md
└── .construct/        (copied from CONSTRUCT-CLAUDE-impl)
```

**Expected outcomes:**
- `views-generate-data`: produces all data files with empty arrays (per data-model §9)
- Landing renders with the "no workspaces yet" empty state (per views §4.1)
- All workspace-scoped routes (`/cosmology/...` etc.) — no workspace exists, so any direct nav resolves to `<NotFound/>`
- `domain-init` triggered on this fixture → bootstraps `construct-up` lazily (per hook-integration §6)

### 3.2 `single-domain-small/`

**Purpose:** Routine smoke fixture. One workspace, realistic but minimal.

```
single-domain-small/
├── AGENTS.md
├── .construct/
└── cosmology/
    ├── domains.yaml          (one domain entry; 4 content_categories)
    ├── governance.yaml
    ├── search-seeds.json
    ├── connections.json      (~15 connections, all 9 types represented)
    ├── cards/                (10 cards; mix of all 10 epistemic_types; lifecycle spread)
    │   ├── card-1.md         (finding, conf=4, mature)
    │   ├── card-2.md         (claim, conf=3, growing)
    │   └── …
    ├── refs/                 (~5 reference JSON files)
    ├── digests/
    │   └── 2026-04-15.md     (one digest, well-formed)
    ├── publish/              (empty)
    ├── log/events.jsonl      (~30 events)
    └── curation-reports/
        └── CURATION-REPORT-2026-04-20.md
```

**Expected outcomes:**
- Every route except `/articles/*` renders with populated content
- `/articles` empty state ("no articles published yet")
- Knowledge graph renders 10 nodes + 15 edges
- All 9 connection types appear in the legend
- Stats: 10 cards, lifecycle spread visible, confidence histogram populated

### 3.3 `multi-domain-medium/`

**Purpose:** Realistic load + multi-workspace aggregation + cross-workspace articles.

```
multi-domain-medium/
├── AGENTS.md
├── .construct/
├── domains.yaml              (root-level — 3 entries with cross_domain_links)
├── cosmology/
│   ├── (full structure: ~100 cards, ~150 connections, 6 digests, 1 article)
├── climate-policy/
│   ├── (~80 cards, ~120 connections, 4 digests, 1 article)
└── ai-alignment/
    └── (~120 cards, ~180 connections, 8 digests, 1 article)
```

**Expected outcomes:**
- Landing renders 3 StatusCards + 3-article strip
- `/articles` renders 3 cards (1 per workspace)
- Each per-workspace dashboard renders correctly
- Knowledge graphs scale (cosmology: 100 nodes; ai-alignment: 120) — well under 500-node budget
- Workspace switcher dropdown lists all 3
- Performance: full `views-generate-data` ≤90s on M1/M2 Mac or comparable Linux

### 3.4 `adversarial-corrupt/`

**Purpose:** Validates invariants and failure isolation. No view should crash; every problem surfaces as a documented warning or partial state.

```
adversarial-corrupt/
├── AGENTS.md
├── .construct/
└── corrupted/
    ├── domains.yaml
    ├── connections.json       (file present but malformed JSON — missing closing brace)
    ├── cards/
    │   ├── valid-1.md         (well-formed)
    │   ├── missing-type.md    (frontmatter omits epistemic_type; required field)
    │   ├── bad-yaml.md        (frontmatter has unbalanced quote)
    │   ├── empty-frontmatter.md  (--- ---\n only)
    │   └── valid-2.md
    ├── digests/
    │   └── 2026-04-15-broken.md  (Summary section present, Top Findings missing)
    └── publish/
        └── orphan-article.md   (frontmatter source_cards: [non-existent-card-id])
```

**Expected outcomes:**
- `views-generate-data` exits zero (catastrophic threshold not reached)
- Warnings logged to `views/build/data/_generation-warnings.log`:
  - `corrupted/cards/missing-type.md: missing required field 'epistemic_type'`
  - `corrupted/cards/bad-yaml.md: YAML parse error: ...`
  - `corrupted/cards/empty-frontmatter.md: missing required field 'id'`
  - `corrupted/connections.json: JSON parse error: ...`
  - `corrupted/digests/2026-04-15-broken.md: missing section 'Top Findings'`
- `cards.json`: 2 valid cards present (valid-1, valid-2). Three corrupt cards excluded.
- `connections.json`: empty connections array (file unparseable)
- `digests.json`: contains 2026-04-15-broken with `parse_status: "partial"` and only the parsed sections
- `articles.json`: contains orphan-article with `source_cards: [{"id": "non-existent-card-id", "status": "missing"}]`
- All views render without crashing
- Knowledge graph shows 2 nodes, 0 edges
- `/articles/orphan-article` renders with one greyed-out source card row labelled "(card removed)"

---

## 4. Cross-Spec Acceptance Matrix

The following rolls up acceptance checks from each spec into a single execution plan. Each row references the spec where the check originates.

### 4.1 Architecture invariants (architecture-overview §4)

| # | Invariant | Test method | Source spec |
|---|---|---|---|
| **I1** | Single-writer to `views/build/data/` | `grep -r "views/build/data" CONSTRUCT-CLAUDE-impl/skills/` returns one writer (views-generate-data) | architecture-overview §4 |
| **I2** | SPA never writes back | `grep -r "method:.*POST\|PUT\|DELETE\|PATCH" views/src/src/` returns nothing; no fetch in SPA source uses non-GET method | architecture-overview §4 |
| **I3** | Safe-delete | `rm -rf <fixture>/views/build/data/ && views-generate-data` produces byte-identical files (excluding `generated_at` envelope field) | data-model §10, data-generation §10 |
| **I4** | No-novel-data | For each schema in `spec-v02-data-model.md` §5, every field traces to a workspace artefact or documented computation | data-model §12.1 |

### 4.2 Source-of-truth integrity (data-model §12)

- [ ] `views/build/data/` directory deletion does not lose any canonical state — workspace files unchanged
- [ ] Two `views-generate-data` runs against unchanged workspace state produce byte-identical files (excluding `generated_at`)
- [ ] No SPA-only fields exist in any data file
- [ ] No skill (other than `views-generate-data`) writes to `views/build/data/` — verifiable by audit grep

### 4.3 Routing and serving (runtime-topology §10 acceptance)

- [ ] `construct-up` claims port from 3001–3009 range, writes `views/server.pid`, reports URL
- [ ] `construct-down` reads PID, terminates process, removes PID file
- [ ] Two simultaneous CONSTRUCT installs (different roots) coexist on different ports
- [ ] Reload at `/<workspace>/digests/<id>` returns the page (proves `serve --single` history fallback)
- [ ] `version.json` polling triggers UPDATE flag within 30s of regen
- [ ] `domain-init` lazily invokes `construct-up` if no server running (hook-integration §6)

### 4.4 Build pipeline (build-pipeline §7)

- [ ] `views-scaffold` on a fresh install creates `views/src/` matching scaffold spec §3
- [ ] `views-scaffold` re-run without `--force` no-ops with the "already exists" message
- [ ] `views-scaffold --force` rebuilds from scratch
- [ ] `views-build` fails clearly when `vite.config.js` has `emptyOutDir: true` or omits the field
- [ ] `views-build` does not delete pre-existing `views/build/{data/*, version.json, server.pid}` (test by creating dummies and rebuilding)

### 4.5 Data generation (data-generation §10)

- [ ] Empty install (no workspaces) produces valid JSON with empty arrays for every collection
- [ ] Single-workspace produces all 8 schemas correctly
- [ ] Multi-workspace produces correct per-workspace + global aggregates
- [ ] Determinism: identical state → identical output (byte-level, modulo `generated_at`)
- [ ] Corrupt card excluded from `cards.json`; warning logged
- [ ] Article with missing source card surfaces as `{"status": "missing"}`
- [ ] `version.json` `build_id` matches every data file's envelope `build_id`
- [ ] No clock-derived data in any `data` payload — only in envelope `generated_at`

### 4.6 Hook integration (hook-integration §11)

- [ ] `research-cycle` / `curation-cycle` / `synthesis` produce fresh data when `views/build/` exists
- [ ] Same skills are no-ops when `views/build/` is absent (no extra log lines)
- [ ] Deliberately broken `views-generate-data` (script renamed) → parent skill succeeds with `⚠ views regeneration failed: ...` warning; workspace state unchanged
- [ ] `card-create` / `card-connect` are unchanged by v0.2 hooks

### 4.7 Views (views §6)

- [ ] All 9 routes plus NotFound render with real data
- [ ] `useFetch` hook returns `{loading, data, error}`; caches per path
- [ ] `useVersionFlag` polls `version.json` and sets `isStale` correctly
- [ ] UPDATE flag invisible when fresh, cyan pill when stale
- [ ] `views/src/src/_mock/` is deleted (mock-to-real swap complete)
- [ ] Filter state is URL-search-param-backed for Articles, Artifacts, Digests
- [ ] No PUT/POST/DELETE in any source file (I2)
- [ ] All views have populated, loading, error, and empty-state renderings

### 4.8 Visual contract (design-prototype §10)

- [ ] CSS custom properties from design-prototype §3.1 declared on `:root`
- [ ] Tailwind registers `font-display: Syne`, `font-body: Manrope`
- [ ] CosmicBG renders 3 layers (gradients + vignette + stars); no rotating rings
- [ ] Layout sets `data-workspace={workspaceId || 'default'}` on outer wrapper
- [ ] Header is sticky; top row always rendered; bottom row only on `/<workspace>/*`
- [ ] No "OpenClaw" string anywhere in SPA
- [ ] Body text contrast ≥4.5:1 on `--bg-base`
- [ ] Desktop (≥1280px) renders without horizontal scroll on every page
- [ ] Tablet (768–1023px) renders gracefully (some compromises acceptable)

---

## 5. End-to-End Smoke Test

Sequence to run on each fixture. Documented as `tests/fixtures/v02/<fixture>/verify.md`.

### 5.1 Procedure

```
1. Set up:
   cd tests/fixtures/v02/<fixture>
   (verify AGENTS.md and .construct/ present)

2. Scaffold (only on first run per fixture):
   "Scaffold the views"     → views-scaffold runs
   Expected: views/src/ created, npm install completes, exit zero

3. Build:
   "Build the views"        → views-build runs
   Expected: views/build/{index.html, assets/} exists; npm run build succeeds

4. Generate data:
   "Update the views"       → views-generate-data runs
   Expected: views/build/data/ populated; views/build/version.json written;
             warnings (if any) match the fixture's expected outcomes

5. Start server:
   "Start CONSTRUCT" / "Show me the views"  → construct-up runs
   Expected: localhost:<port> reported; views/server.pid written

6. Browser test:
   Open URL in browser. Walk through:
   - Landing renders correctly for fixture
   - Each workspace's bottom-row links navigate
   - Knowledge graph renders (or shows empty state if no cards)
   - Artifacts table renders (or shows empty state)
   - Digests list renders (or shows empty state)
   - Articles list renders (or shows empty state)
   - At least one detail page navigated and renders
   - UPDATE flag not visible (no regen yet)

7. Trigger regen:
   Make a small change to a card via Claude (e.g., "add a tag to card-1")
   Expected: card-edit hook fires (if v0.2.1) OR user explicitly says "update views"
   - views-generate-data runs
   - version.json build_id changes
   - Browser shows UPDATE flag within 30s
   - Click flag → page reloads → fresh data renders

8. Stop server:
   "Stop CONSTRUCT" / "End session"  → construct-down runs
   Expected: PID file removed; subsequent browser request fails

9. Source-of-truth check:
   rm -rf views/build/data/
   "Update the views"  → views-generate-data runs
   Expected: byte-identical output to step 4 (excluding generated_at)
```

### 5.2 What's NOT in the smoke test (deferred)

- Mobile viewport (out of scope per design-prototype §7.1)
- Browser-vendor edge cases beyond Chrome/Firefox/Safari latest
- Network failure (e.g., what if the SPA can't reach `/version.json`?)
- Multi-server contention (two CONSTRUCT installs sharing a port — handled by port-collision logic)

---

## 6. Performance Expectations

### 6.1 Pipeline

| Stage | Small (≤50 cards) | Medium (≤500 cards) | Notes |
|---|---|---|---|
| `views-scaffold` (first time) | ≤60s | ≤60s | Network-bound: `npm install` |
| `views-scaffold` (subsequent) | n/a | n/a | Idempotent no-op |
| `views-build` | ≤15s | ≤30s | Vite build |
| `views-generate-data` | ≤2s | ≤10s | Python script |
| `construct-up` (cold) | ≤2s | ≤2s | Process start + port bind |
| **Full first run** | **≤90s** | **≤105s** | Sum of above (one-time cost) |
| **Steady-state regen** | **≤2s** | **≤10s** | views-generate-data only |

These are soft expectations on M1/M2 Mac or comparable Linux (8GB RAM, SSD). v0.2 doesn't enforce; Epic 11 docs note these as guidance.

### 6.2 Browser

| Concern | Target |
|---|---|
| Knowledge graph 500 nodes | ≥30fps after force simulation settles |
| Artifacts table 1000 rows | Initial render ≤500ms |
| Landing dashboard fetch + render | ≤300ms after JSON load |
| Page navigation (route change) | ≤100ms |
| `version.json` polling cost | <10ms per poll (file is ~80 bytes) |

Beyond budget: graceful degradation (e.g., graph renders a warning if >500 nodes; artifacts paginates).

---

## 7. Portability Expectations

### 7.1 OS support

| OS | v0.2 status |
|---|---|
| macOS 13 (Ventura) and later | **Supported** — primary dev environment |
| Ubuntu 22.04 LTS, Fedora 38+ | **Supported** — secondary |
| Other Linux distros | Best-effort (should work, not tested) |
| Windows | **Untested in v0.2.** Vite builds work on Windows, but signal/PID handling and path semantics in skills may differ. v0.3 may add explicit support |

### 7.2 Node + Python

| Tool | Required version | Notes |
|---|---|---|
| Node.js | ≥20 | Vite 8 requirement; pinned via `.nvmrc` |
| npm | bundled with Node | |
| Python | ≥3.10 | matches repo `pyproject.toml`; needed for views-generate-data |

### 7.3 Browser support

| Browser | v0.2 status |
|---|---|
| Chrome latest stable | **Supported** — primary |
| Firefox latest stable | **Supported** |
| Safari latest stable | **Supported** |
| Edge | Untested (likely works since Chromium-based) |
| Older versions | Not supported — uses ES2022 features without polyfill |

### 7.4 Claude surfaces

The skills run wherever Claude can execute Bash, Read, Write, and Edit tools. v0.2 has been designed against:
- Claude Code (CLI)
- Claude Desktop (Mac/Windows app — caveat §7.1)

Web (claude.ai) doesn't currently expose Bash for filesystem skills, so v0.2 isn't operable from the web surface. This is a Claude-platform limitation, not a v0.2 design constraint.

---

## 8. Acceptance Sign-Off

v0.2 is considered shipped when:

- [ ] All checks in §4.1–§4.8 pass on the `single-domain-small` fixture
- [ ] All checks in §4.1–§4.8 pass on the `multi-domain-medium` fixture
- [ ] All adversarial outcomes in §3.4 produce the expected warnings + partial states; no crash
- [ ] Smoke test §5.1 completes successfully on all 4 fixtures
- [ ] Performance targets in §6 are met on at least one supported platform (manual measurement)
- [ ] PRD `prd-v02-live-views.md` is patched per Epic 11 to reflect: `src/data/` → `build/data/`, `serve --single` over Python `http.server`, Epic 5 hooks, etc.
- [ ] `CONSTRUCT-CLAUDE-impl/README.md` updated with v0.2 commands and user phrases (Epic 11)
- [ ] `CONSTRUCT-CLAUDE-v02-planning/` directory archived to `CONSTRUCT-CLAUDE-spec/archive/v02-backlog.md` (per ADR-0002)
- [ ] `CONSTRUCT-CLAUDE-impl/VERSION` flipped from `0.2.0-dev` to `0.2.0`
- [ ] All draft specs flipped from `Status: Draft` to `Status: Accepted`

---

## 9. Open Follow-ups

1. **Automated test framework.** v0.2 validation is manual + scripted. v0.2.1 may add Vitest for the SPA + pytest for `views-generate-data`. Current decision: defer.
2. **CI integration.** No GitHub Actions / CI pipeline for v0.2. Smoke tests are run manually pre-release. v0.3 candidate.
3. **Adversarial fixture coverage.** §3.4 covers the top failure modes. Real-world edge cases (Unicode in card titles, very long markdown bodies, recursive symlinks) not enumerated. Add to fixture set if encountered in practice.
4. **Performance baseline storage.** §6 numbers are point-in-time estimates. v0.2.1 may add a `tests/fixtures/v02/perf-baseline.json` snapshot to detect regressions.
5. **Determinism check across machines.** §4.5 byte-identical determinism is verified on one machine. Cross-machine determinism (different filesystem orderings, locale) is not tested. Should be deterministic by design but not validated.
6. **`verify.md` template.** §5 says each fixture has a `verify.md`. Format isn't specified — could standardise (e.g., a YAML checklist). Defer to fixture-author judgement.

---

## 10. References

- All `spec-v02-*.md` (this spec consolidates their acceptance sections)
- `architecture-overview.md` §4 (the four invariants tested in §4.1)
- `prd-v02-live-views.md` §9 (success criteria — superseded by this spec's §8)
- `tests/` (existing test infrastructure; fixtures go in `tests/fixtures/v02/`)
- `CONSTRUCT-CLAUDE-impl/VERSION` — tracks v0.2.0 readiness gate (§8 last item)
