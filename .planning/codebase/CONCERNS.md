# Codebase Concerns

**Analysis Date:** 2026-06-08

---

## Tech Debt

### Dual Runtime — Python `src/` vs Claude-Native `CONSTRUCT-CLAUDE-impl/`

- Issue: `src/construct/` is the v0.1 Python skeleton — partially implemented (schemas, validation, storage, CLI `init`/`validate`/`status`, no pipelines, no MCP, no capabilities registry). `CONSTRUCT-CLAUDE-impl/` is the fully operational Claude-native runtime. Both coexist in the same repo with no runtime bridge.
- Files: `src/construct/cli.py`, `src/construct/services/`, `src/construct/schemas/`, `CONSTRUCT-CLAUDE-impl/claude/skills/`
- Impact: `src/construct/` has different workspace layout assumptions from Claude-native skills; running `construct validate` (Python) against a Claude-native workspace will produce false errors due to schema mismatch (see below). Developers must not conflate the two runtimes.
- Fix approach: v0.3 revives `src/construct/` surgically per ADR-0003 — add `capabilities/`, `pipelines/`, `llm/`, `mcp/` directories. Retire divergent workspace schema assumptions first.

### Python Workspace Schema Assumes v0.1 Paths (Not Claude-Native)

- Issue: `src/construct/schemas/workspace.py` `REQUIRED_PATHS` includes `domains/`, `workflows/`, `inbox/`, `db/`, `views` — these are v0.1 Python app paths. Real Claude-native workspaces do not have `workflows/`, `inbox/`, or `db/` directories; `views/` is optional (only present after `construct-views-scaffold`). Validating a Claude-native workspace with the Python CLI produces spurious "missing required canonical path" errors.
- Files: `src/construct/schemas/workspace.py` (lines 14–29), `src/construct/services/validation.py`
- Impact: Python `construct validate` is broken for every Claude-native workspace today. The v0.3 contract test target (`workspace.validate` CLI against `test-ws/my-construct/`) will fail until this is reconciled.
- Fix approach: Align `REQUIRED_PATHS` and `WorkspaceScaffold.canonical_paths` with the canonical Claude-native workspace layout defined in `CONSTRUCT-CLAUDE-spec/config-topology.md` and `CONSTRUCT-CLAUDE-impl/construct/templates/`. Remove `domains/`, `workflows/`, `inbox/`, `db/` from required paths; make `views` optional.

### `search-seeds.json` Absent from Python Workspace Schema

- Issue: `search-seeds.json` is a canonical workspace file (present in `CONSTRUCT-CLAUDE-impl/construct/templates/`, managed by `construct-search-adjust` skill), but it does not appear in `WorkspaceScaffold.canonical_paths` or `REQUIRED_PATHS` in `src/construct/schemas/workspace.py`.
- Files: `src/construct/schemas/workspace.py`, `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json`
- Impact: Python validator silently skips `search-seeds.json` schema validation. Corruption or schema drift in this file goes undetected by the Python layer.
- Fix approach: Add `search-seeds.json` to canonical paths and implement schema validation in `validate_workspace()`.

### `pytest` Listed as Runtime Dependency

- Issue: `pyproject.toml` lists `pytest>=8.0` in `[project.dependencies]` (runtime), not under a `[project.optional-dependencies]` dev group. Installing the `construct` package pulls in pytest as a production dependency.
- Files: `pyproject.toml` (line in dependencies block)
- Impact: Unnecessary bloat in installed environments; violates packaging conventions; wheels shipped with test framework.
- Fix approach: Move `pytest>=8.0` to `[project.optional-dependencies]` dev section, e.g., `[project.optional-dependencies] dev = ["pytest>=8.0"]`.

### `views-generate-data` — Standalone Python Codebase Inside a Skill Directory

- Issue: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/` contains ~2,140 lines of Python across `generate.py` (354), `debounced_hook.py` (212), and `lib/` (1,496) covering frontmatter parsing, card/connection/digest/bridge/domain parsing, fingerprinting, stats, and a debounced hook daemon. This is a fully operational Python pipeline embedded in a skill's SKILL.md directory, completely separate from `src/construct/`.
- Files: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/generate.py`, `.../lib/*.py`
- Impact: v0.3 tranche 1 plans to implement `views.generate_data` as a PIPE capability in `src/construct/pipelines/`. There are now two implementations to keep in sync until migration completes. The skill's per-skill venv (`.venv/` inside the skill dir) is a dependency management island; PyYAML is managed separately from the main `pyproject.toml`.
- Fix approach: When implementing v0.3 `views.generate_data` PIPE capability, port `lib/*.py` parsers into `src/construct/pipelines/` and retire the skill-embedded copies. Until migration, treat `generate.py` + `lib/` as the authoritative implementation and do not duplicate logic.

### `config-topology.md` Is Stale

- Issue: `CONSTRUCT-CLAUDE-spec/config-topology.md` shows skill paths as `skills/<name>/SKILL.md` and agent paths as `agents/*.md` directly under `CONSTRUCT-CLAUDE-impl/`. The actual paths are `claude/skills/` and `claude/agents/`. The artifact-catalog itself notes: "partially outdated — defer to this catalog for counts."
- Files: `CONSTRUCT-CLAUDE-spec/config-topology.md`
- Impact: Misleads anyone navigating by topology doc; any automation relying on old paths (e.g., deploy scripts) would fail.
- Fix approach: Update `config-topology.md` to reflect actual paths: `claude/agents/`, `claude/skills/`, `construct/workflows/`, `construct/references/`, `construct/templates/`. This is a low-risk doc-only edit.

---

## Missing Critical Features

### v0.3 Tranche 1 Not Implemented — Zero Code Exists

- Problem: The approved tranche-1 scope (`tranche-1-mvp.md`) requires: capability registry (`src/construct/capabilities/`), PIPE handlers (`src/construct/pipelines/`), CLI `run` subcommands (`construct run validate`, `construct run graph-status`, `construct run views-generate-data`), MCP stdio server (`src/construct/mcp/`), LangGraph L2 gate (`src/construct/llm/`), Streamlit spike (`src/construct/ui/`), and workflow runner skeleton. None of these paths exist.
- Blocks: All v0.3 success criteria. v0.4 UI cannot start until v0.3 tranche 1 ships.

### `test-ws/` Fixture Workspaces Missing

- Problem: `tranche-1-mvp.md` and `prd-v03-pipeline-mvp.md` specify that CLI contract tests run against `test-ws/my-construct/` and `test-ws/ping-eon/` (real CONSTRUCT workspaces). These directories do not exist in the repo. The README references `test-ws/` as an existing fixture directory.
- Files: `CONSTRUCT-CLAUDE-v03-planning/tranche-1-mvp.md` (Deliverable 2), `prd-v03-pipeline-mvp.md` §10
- Blocks: All tranche-1 contract tests. CLI golden-path tests cannot be written until `test-ws/` fixtures exist.
- Fix approach: Create `test-ws/my-construct/` and `test-ws/ping-eon/` from template; populate with enough cards, connections, and domains to exercise `validate`, `graph-status`, and `views-generate-data`.

### v0.3 Dependencies Not in `pyproject.toml`

- Problem: `prd-v03-pipeline-mvp.md` §3 lists required additions: `mcp>=1.0`, `langgraph>=0.2`, `langchain-core>=0.3`, `langchain-anthropic>=0.3`, `streamlit>=1.35`, `jsonschema>=4.21`. None are in `pyproject.toml`.
- Files: `pyproject.toml`
- Blocks: `src/construct/mcp/`, `src/construct/llm/`, and `src/construct/ui/` cannot be implemented until dependencies are declared.
- Fix approach: Add tranche-1 dependencies to `pyproject.toml` at the start of implementation.

### No GSD / `.planning/` State for v0.3 Implementation

- Problem: `.planning/` contains only an empty `codebase/` directory. No phases, roadmap, or task tracking for v0.3 implementation exist. `CONSTRUCT-CLAUDE-v03-planning/README.md` explicitly defers GSD initialization: "When v0.3 moves from planning to implementation, initialize fresh GSD from the v0.3 PRD."
- Files: `.planning/` (empty)
- Impact: No structured task tracking, no phase dependencies, no commit manifest when implementation begins. All v0.3 work will be untracked until GSD is initialized.
- Fix approach: Initialize GSD from `prd-v03-pipeline-mvp.md` + `tranche-1-mvp.md` when implementation begins; do not reuse the archived `archive/v01-python/gsd/`.

---

## Fragile Areas

### Artifact Catalog ↔ `capabilities.md` ↔ SKILL.md Triple-Source Sync

- Files: `CONSTRUCT-CLAUDE-spec/artifact-catalog.md`, `CONSTRUCT-CLAUDE-impl/construct/references/capabilities.md`, `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md`
- Why fragile: Three documents must stay in sync: the master catalog (spec-side inventory), the deployed capabilities handbook (user-facing), and each SKILL.md (executable procedure). The catalog notes a maintenance protocol (update all three on change), but there's no automated check. The catalog also notes `config-topology.md` is "partially outdated" — indicating drift has already occurred.
- Safe modification: Always update the catalog first (master), then capabilities.md and commands.md, then SKILL.md. Never add a skill without a catalog row.
- Test coverage: No automated test verifies catalog ↔ skills ↔ capabilities.md alignment.

### `views-generate-data` Per-Skill Venv and Debounced Hook Daemon

- Files: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/.venv/`, `debounced_hook.py`, `debounced-hook.sh`
- Why fragile: The per-skill venv bootstraps PyYAML independently; if the host Python changes (currently Python 3.14 in `.venv/`), the skill venv may silently break. The debounce daemon uses `fcntl` file locking and background process management — it is "best-effort by design; concurrency hardening is deferred" per SKILL.md notes.
- Safe modification: Do not change Python version or PyYAML version in the skill venv without testing on the target macOS Python. Do not introduce concurrent calls to `debounced-hook.sh` — one instance per workspace is the assumed invariant.
- Test coverage: No tests for debounced hook behavior.

### `DomainsRegistry` Path References — Flat vs Subdirectory Layout

- Files: `src/construct/schemas/config.py` (DomainsRegistry), `src/construct/services/validation.py` (line 84: `domain_path = entry.path`)
- Why fragile: Validation checks that each `domains.yaml` registry entry's `.path` points to an existing file. The `_write_valid_workspace` test creates `domains/example-domain/domain.yaml` (v0.1 subdirectory pattern). Current Claude-native templates use a single flat `domains.yaml` — no per-domain subdirectory files. The two layouts cannot both pass `validate_workspace()` without layout negotiation.
- Safe modification: Until the workspace schema is reconciled (see tech debt above), do not add per-domain path entries to Claude-native `domains.yaml` unless the domain file exists.
- Test coverage: `tests/unit/test_validation_service.py` covers the v0.1 subdirectory layout only.

---

## Test Coverage Gaps

### No Contract Tests for v0.3 Capabilities

- What's not tested: CLI `construct run validate`, `construct run graph-status`, `construct run views-generate-data`, MCP stdio tool schemas, LangGraph L2 ask, Streamlit pages.
- Files: `tests/contract/` — directory does not exist yet
- Risk: v0.3 tranche 1 ships without regression coverage; behavioral drift between CLI and MCP adapters goes undetected.
- Priority: High — required by tranche-1 success criteria item 1 ("all four PIPE capabilities + daily-cycle skeleton pass CLI contract tests")

### No Tests for `views-generate-data` Python Library

- What's not tested: `lib/parse_bridges.py` (438 lines), `lib/parse_digests.py` (255 lines), `generate.py` (354 lines) — zero pytest coverage.
- Files: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/lib/`
- Risk: Parse regressions in the views data pipeline go unnoticed; this is the primary data source for the v0.2 browser dashboard.
- Priority: High before v0.3 migration of this code into `src/construct/pipelines/`.

### No Tests for `construct-workspace-validate` SKILL.md Procedure

- What's not tested: The Claude-native skill's full validation checklist (Layers 1–5 per `spec-v02-validation.md`) — only the Python `validate_workspace()` service is tested, which covers a subset.
- Files: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md`
- Risk: Layers 4–5 (functional spot-check, audit trail) are noted as "stubs returning `not_implemented` findings" in the v0.3 PRD — meaning the spec acknowledges incomplete coverage today.
- Priority: Medium — addressed in tranche 2 per prd-v03 §4.1.

### No Integration Tests for Claude-Native Skills

- What's not tested: None of the 23 SKILL.md procedures are tested end-to-end against real workspace fixtures.
- Files: All `CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md`
- Risk: Skill procedure drift from spec is undetectable without manual workspace auditing (the current validation strategy). Skill regressions require human exercise.
- Priority: Medium — by design until v0.3 MCP integration enables agentic testing.

---

## Performance Bottlenecks

### `validate_workspace()` — Full Workspace Scan on Every Invocation

- Problem: `validate_workspace()` loads all `*.md` files in `cards/` on every call via `iter_cards()`. No caching, no incremental scan.
- Files: `src/construct/services/validation.py`, `src/construct/storage/workspace.py` (`iter_cards`)
- Cause: No fingerprinting or workspace-change detection in the Python layer (in contrast, `views-generate-data` does implement mtime+size fingerprinting).
- Improvement path: Add workspace fingerprint cache to `validate_workspace()` when porting to `src/construct/pipelines/` in v0.3 — pattern already exists in `lib/fingerprint.py`.

---

## Dependencies at Risk

### `ruamel.yaml` — YAML Parser with Non-Standard API

- Risk: `ruamel.yaml` is used instead of `pyyaml` (the more common choice). It has a different API (`YAML(typ="safe")` vs `yaml.safe_load()`). The skill's per-skill venv installs `pyyaml` for `views-generate-data`. Two different YAML libraries are in use across the same codebase.
- Impact: Contributor confusion; future dependency consolidation effort when porting `views-generate-data` parsers (which use `pyyaml`) into `src/construct/`.
- Migration plan: Standardize on one library during v0.3 pipeline migration. `ruamel.yaml` is the better choice for round-trip YAML preservation; port `views-generate-data` parsers to `ruamel.yaml` during migration.

---

## Scaling Limits

### Claude-Native Skills — No Pagination for Large Workspaces

- Current capacity: Workspaces up to ~500 cards are workable per `CONSTRUCT-CLAUDE-spec/prd.md` §1.
- Limit: Skills that read all cards (research-cycle, curation-cycle, graph-status) load entire workspace into Claude's context window. Past ~500 cards, context fills before completion.
- Scaling path: v0.3 Python pipelines with chunked processing; v0.4 SQLite indexer (deferred to v0.3+ per ADR-0003).

---

## Security Considerations

### No Secrets in Repo — Pattern Sound

- Risk: None detected.
- Files: `.env` file not present; `pyproject.toml` has no hardcoded API keys; `CONSTRUCT-CLAUDE-impl/construct/templates/config.yaml` is a template (placeholder only).
- Current mitigation: All LLM provider credentials are env-var or YAML config (v0.3 plan per ADR-0003 §A.3); no secrets in committed files.
- Recommendations: Add `.gitignore` entries for `src/construct/llm/config.yaml` if it ever contains real credentials; keep provider config as YAML template only.

### `views-generate-data` Runs Arbitrary Python in Agent Context

- Risk: The SKILL.md procedure calls `bash <install-root>/.claude/skills/views-generate-data/run.sh <install-root>` — shell execution from within an agent turn. The `allowed-tools: Bash(python3 *)` in the skill header grants Python execution scope.
- Files: `CONSTRUCT-CLAUDE-impl/claude/skills/construct-views-generate-data/SKILL.md`, `run.sh`
- Current mitigation: The script is read-only on workspace files (writes only to `views/build/data/`). No network access in `generate.py`.
- Recommendations: When migrating to v0.3 MCP/CLI, remove `Bash(python3 *)` from skill allowed-tools — skill will invoke MCP tool instead.

---

## Known Bugs

### `prd-v03-pipeline-mvp.md` Untracked — Not in Git

- Symptoms: `git status` shows `?? CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md`. The PRD is the primary binding spec for v0.3 tranche 1 but is not committed.
- Files: `CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md`
- Trigger: File was created in the current session and not yet added to git.
- Workaround: `git add CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md && git commit -m "spec: add v0.3 pipeline MVP PRD (tranche 1)"`

### `README_FIRST.md` Not Updated for v0.3 PRD

- Symptoms: `CONSTRUCT-CLAUDE-spec/README_FIRST.md` core narrative table does not list `prd-v03-pipeline-mvp.md`. The PRD itself notes this in §15: "When this PRD is accepted, add to README_FIRST.md."
- Files: `CONSTRUCT-CLAUDE-spec/README_FIRST.md`, `CONSTRUCT-CLAUDE-spec/prd-v03-pipeline-mvp.md`
- Workaround: After committing the PRD, add row to the "Core narrative" table in README_FIRST.md.

### v0.2 Planning Directory Not Archived

- Symptoms: `CONSTRUCT-CLAUDE-v02-planning/README.md` states "This directory is archived to `spec/archive/v02-backlog.md` once v0.2 ships." v0.2 shipped; directory persists.
- Files: `CONSTRUCT-CLAUDE-v02-planning/`
- Impact: Minor — creates confusion about what constitutes active planning. Historical only.
- Fix: Archive or note-as-complete in README.

---

*Concerns audit: 2026-06-08*
