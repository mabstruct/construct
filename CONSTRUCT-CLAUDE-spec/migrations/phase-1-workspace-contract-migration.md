# Phase 1 Workspace Contract Migration

**Document:** CONSTRUCT-CLAUDE-spec/migrations/phase-1-workspace-contract-migration.md
**Applies to:** Phase 1 contract canon (2026-06-08)
**Status:** Active — migration guidance for existing CONSTRUCT workspaces
**Target layout:** The Phase 1 canonical workspace shape defined in `CONSTRUCT-CLAUDE-spec/workspace-contract.md`

---

## Purpose

This document describes how to migrate an existing CONSTRUCT workspace from older
layout assumptions to the Phase 1 canonical contract. The migration is a **one-time
process** per workspace. After migration, all workspaces follow the same canonical
layout. Per D-09, the project does not maintain indefinite dual-layout support.

---

## Pre-Migration Checklist

Before beginning the migration:

- [ ] Identify all CONSTRUCT workspace directories that need migration
- [ ] Verify each workspace is under version control (git)
- [ ] Commit or stash any uncommitted changes
- [ ] Note the current workspace state with `git status`
- [ ] Run `construct validate <workspace>` on each workspace to establish a baseline
- [ ] Read `CONSTRUCT-CLAUDE-spec/workspace-contract.md` to understand the target layout

---

## Artifact-by-Artifact Migration Steps

The Phase 1 canonical workspace layout is:

```
{workspace}/
├── cards/                         # Canonical SOT — knowledge cards
├── refs/                          # Canonical SOT — reference entries
├── connections.json               # Canonical SOT — typed edge list
├── domains.yaml                   # Canonical SOT — domain taxonomy
├── governance.yaml                # Canonical SOT — promotion/decay/research thresholds
├── search-seeds.json              # Canonical SOT — research steering inputs
├── log/
│   └── events.jsonl               # Canonical SOT — audit trail
├── digests/                       # Derived — rebuildable workflow summaries
├── publish/                       # Derived — rebuildable curated outputs
└── .construct/
    └── model-routing.yaml         # Support — runtime provider routing guidance
```

### Step 1: Cards

**Old assumption:** Cards could live in per-domain subdirectories
(`cosmology/cards/`, `philosophy-of-mind/cards/`) or at workspace root (`cards/`).

**New requirement:** All card `*.md` files live in a single flat `cards/` directory
at workspace root.

**Migration action:**
- If your workspace already has `cards/` at root, verify all card files are there.
- If cards are spread across domain subdirectories, move them into `cards/`:
  ```bash
  mkdir -p cards
  find . -maxdepth 2 -type d -name cards -not -path './cards' -exec sh -c 'mv "$1"/*.md ./cards/' _ {} \;
  ```
- Each card's `id` field must match its filename (without `.md`).
- Run `construct validate <workspace>` to verify card schemas.

### Step 2: Refs

**Old assumption:** Refs in per-domain subdirectories
(`cosmology/refs/`, `philosophy-of-mind/refs/`).

**New requirement:** All reference `*.json` files live in a single `refs/` directory
at workspace root.

**Migration action:**
- Move all `*/refs/*.json` files into `./refs/`:
  ```bash
  mkdir -p refs
  find . -maxdepth 2 -type d -name refs -not -path './refs' -exec sh -c 'mv "$1"/*.json ./refs/' _ {} \;
  ```

### Step 3: Connections

**Old assumption:** Each domain had its own `connections.json` in its subdirectory.

**New requirement:** A single `connections.json` at workspace root contains all
typed graph edges.

**Migration action:**
- Merge all per-domain `connections.json` files into one root-level `connections.json`.
  Each connection must have: `from`, `to`, `type`, `created` (date), `created_by`.
- The root `connections.json` must follow this structure:
  ```json
  {
    "version": 1,
    "updated": "2026-06-08",
    "connection_types": ["supports", "contradicts", ...],
    "connections": [...]
  }
  ```
- Run `construct validate <workspace>` to verify.

### Step 4: Domains

**Old assumption:** `domains.yaml` was per-domain or at root with per-domain
`domain.yaml` detail files (`domains/{id}/domain.yaml`).

**New requirement:** One `domains.yaml` at workspace root containing all domain
entries. No per-domain `domain.yaml` files.

**Migration action:**
- Merge all per-domain `domain.yaml` entries into a single root `domains.yaml`.
- The root `domains.yaml` format:
  ```yaml
  domains:
    my-domain:
      name: "My Domain"
      description: "Description"
      status: active
      created: 2026-01-01
      content_categories:
        - category-one
      source_priorities:
        - "peer-reviewed papers"
      cross_domain_links:
        - domain: other-domain
          topics:
            - shared-topic
  ```
- `cross_domain_links` entries are objects (with `domain` and `topics`), not strings.
- Remove the old `domains/` subdirectory after merging.

### Step 5: Governance

**Old assumption:** `governance.yaml` per-domain in domain subdirectories.

**New requirement:** One `governance.yaml` at workspace root.

**Migration action:**
- Pick one `governance.yaml` as the canonical version (prefer the most permissive
  or most recently updated).
- Copy or move it to the workspace root, overwriting any existing file.
- Run `construct validate <workspace>` to verify.

### Step 6: Search Seeds

**Old assumption:** `search-seeds.json` per-domain.

**New requirement:** One `search-seeds.json` at workspace root.

**Migration action:**
- Merge all per-domain `search-seeds.json` `clusters` arrays into a single file.
- Each cluster must reference a domain that exists in `domains.yaml`.
- Run `construct validate <workspace>` to verify.

### Step 7: Event Log

**Old assumption:** `log/events.jsonl` per-domain.

**New requirement:** One `log/events.jsonl` at workspace root.

**Migration action:**
- Merge per-domain event log files chronologically into `log/events.jsonl`.
- Remove old per-domain `log/` directories after merging.
- Run `construct validate <workspace>` to verify.

### Step 8: Derived and Support Artifacts

**Old assumption:** `digests/` and `publish/` could be anywhere.

**New requirement:** `digests/` and `publish/` at workspace root (derived).
`.construct/model-routing.yaml` at workspace root (support).

**Migration action:**
- Create root-level `digests/` and `publish/` directories.
- Move any existing digests and published outputs into them.
- Copy `CONSTRUCT-CLAUDE-impl/construct/templates/model-routing.yaml` to
  `.construct/model-routing.yaml` if it does not exist.

---

## Post-Migration Checklist

After completing all artifact steps:

- [ ] Run `pytest tests/integration/test_workspace_contract_migration.py -k fixtures -x`
      to confirm the migration follows the same proof standard as canonical fixtures
- [ ] Run `construct validate <workspace>` and verify zero errors
- [ ] Run `construct status <workspace>` and verify canonical/derived/support labels
- [ ] Verify all `connections.json` `from`/`to` targets reference existing card files
- [ ] Verify all card `domains` values reference entries in root `domains.yaml`
- [ ] Verify all ref `domain` and search seed `domain` values reference known domains
- [ ] Optionally: verify `log/events.jsonl` contains at least a `workspace_init` event
- [ ] Commit the workspace: `git add -A && git commit -m "migrate: workspace to Phase 1 canonical layout"`

---

## Safety Notes

- **Do not delete old files until after verification.** Keep old domain subdirectories
  until post-migration validation passes, then remove them in a follow-up commit.
- **Rollback:** If validation fails, restore from git (`git checkout -- .`) and
  re-attempt with more careful artifact merge.
- **Backward compatibility:** The Phase 1 contract does not maintain indefinite
  dual-layout support (D-09). After migration, the workspace follows the canonical
  layout only. Old per-domain structures are archived, not supported.
- **Fixture proof:** The canonical `test-ws/` fixtures demonstrate the target layout.
  Refer to `test-ws/my-construct/` and `test-ws/ping-eon/` for reference.
- **Template source:** Initial file contents are sourced from
  `CONSTRUCT-CLAUDE-impl/construct/templates/`, not from `.construct/templates/`
  (which is a deployed copy, not the authoritative source).
- **Write gates:** After migration, invalid canonical artifacts are rejected before
  write. See `CONSTRUCT-CLAUDE-spec/validation-strategy.md` for details. Post-write
  validation (`construct-workspace-validate`) handles cross-file consistency,
  governance audit, and fixture proof.

---

## Rollback Procedure

If the migration causes issues:

1. `git revert HEAD` to undo the migration commit
2. If multiple commits were made, revert them in reverse chronological order
3. Re-run `construct validate <workspace>` to confirm pre-migration state

Rollback preserves the old per-domain layout but prevents access to new Phase 1
runtime features and validations.

---

## Verification

After migration, run these checks:

```bash
# Validate the workspace against the Phase 1 contract
construct validate <workspace>

# Optionally run the same checks that protect canonical fixtures
pytest tests/integration/test_workspace_contract_migration.py -k fixtures -x

# Verify no missing canonical paths or broken artifacts
pytest tests/unit/test_workspace_contracts.py -x
```
