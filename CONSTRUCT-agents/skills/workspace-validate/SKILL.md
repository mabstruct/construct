# Skill: Workspace Validation

**Trigger:** User says "validate workspace", "audit", "check integrity", or similar.
**Agent:** CONSTRUCT or Curator
**Produces:** Validation report with findings and recommendations

---

## Procedure

Run all 5 validation layers. Report findings for each.

### Layer 1: Schema Validation

**Cards:**
For each `cards/*.md`:
- [ ] YAML frontmatter parses without error
- [ ] `id` matches filename (without .md extension)
- [ ] Required fields present: `id`, `title`, `epistemic_type`, `created`, `confidence`, `source_tier`, `domains`
- [ ] `confidence` is integer 1–5
- [ ] `source_tier` is integer 1–5
- [ ] `epistemic_type` is valid enum
- [ ] `lifecycle` (if present) is valid: seed / growing / mature / archived
- [ ] `## Summary` section exists in body

**connections.json:**
- [ ] Valid JSON
- [ ] Has `version`, `connection_types`, `connections` fields
- [ ] Each connection has `from`, `to`, `type`, `created`, `created_by`
- [ ] Each `type` is in the `connection_types` list
- [ ] No duplicate edges (same from + to + type)

**domains.yaml:**
- [ ] Valid YAML
- [ ] Each domain has: `name`, `description`, `status`, `created`, `content_categories`
- [ ] Domain IDs are kebab-case and unique
- [ ] `status` values are valid

**governance.yaml:**
- [ ] Valid YAML
- [ ] Has all required sections: `promotion`, `decay`, `quality`, `research`
- [ ] Numeric values are in valid ranges

**search-seeds.json:**
- [ ] Valid JSON
- [ ] Each cluster has: `id`, `domain`, `terms`, `weight`, `status`
- [ ] Weights are 0.0–1.0
- [ ] Statuses are valid

**refs/*.json:**
- [ ] Each is valid JSON
- [ ] Has required fields: `id`, `title`, `url`, `relevance_score`, `source_tier`

**log/events.jsonl:**
- [ ] Each line is valid JSON
- [ ] Each event has: `ts`, `agent`, `action`, `result`

### Layer 2: Governance Validation

- [ ] No seed card has confidence ≥ 3 (should have been promoted to growing)
- [ ] No growing card meets all mature criteria without being promoted (unless `require_human_approval`)
- [ ] No card with source_tier 5 has confidence > 1 (without explicit override)
- [ ] Decay-flagged cards are genuinely past the window
- [ ] Research relevance thresholds are consistent with ingested refs

### Layer 3: Consistency Validation

- [ ] Every card's `domains` entries exist in `domains.yaml`
- [ ] Every card's `content_categories` entries exist in the referenced domain's category list
- [ ] Every card's `connects_to` targets exist as card files
- [ ] Every `connections.json` `from`/`to` references an existing card file
- [ ] Every ref's `domain` exists in `domains.yaml`
- [ ] Every search cluster's `domain` exists in `domains.yaml`
- [ ] Every publish document's `source_cards` reference existing cards

### Layer 4: Functional Spot-Check

- [ ] At least one domain is active
- [ ] At least one search cluster is active (if any domain is active)
- [ ] `events.jsonl` has at least a `workspace_init` event
- [ ] Card count matches file count in `cards/`

### Layer 5: Audit Trail Check

- [ ] Every card file has a corresponding `create_card` event
- [ ] Every promotion has a corresponding `promote_card` event
- [ ] Events are in chronological order
- [ ] No future-dated events

### Report

Present findings as:

```markdown
## Workspace Validation Report — {date}

### Summary
- Files checked: {N}
- Errors: {N}
- Warnings: {N}
- Status: {PASS | FAIL}

### Layer 1: Schema ({N} checks, {N} passed)
{findings}

### Layer 2: Governance ({N} checks, {N} passed)
{findings}

### Layer 3: Consistency ({N} checks, {N} passed)
{findings}

### Layer 4: Functional ({N} checks, {N} passed)
{findings}

### Layer 5: Audit Trail ({N} checks, {N} passed)
{findings}

### Recommendations
- {actionable fix suggestions}
```

---

## Validation

- [ ] All 5 layers executed
- [ ] Every finding is specific (references exact file and field)
- [ ] Recommendations are actionable
- [ ] Report distinguishes errors (must fix) from warnings (should fix)
