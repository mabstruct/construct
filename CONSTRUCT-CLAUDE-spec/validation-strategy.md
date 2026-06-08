# CONSTRUCT Agent System — Validation Strategy

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active

---

## 1. The Challenge

The Python approach has pytest, CI, contract tests. The Claude-native approach has no code — so how do we verify correctness?

**Answer:** Workspace auditing. If the files are correct, the system is correct.

---

## 2. Validation Layers

Phase 1 distinguishes two enforcement moments:

- **Pre-write rejection:** invalid canonical artifacts are blocked before they become source-of-truth files.
- **Post-write audit:** valid writes are then checked for cross-file consistency, governance, fixture proof, and migration safety.

### Layer 1: Schema Validation (Structural)

Skills produce files. Canonical source-of-truth files must conform to schemas before write.

| Artifact | Validation | When |
|----------|-----------|------|
| `cards/*.md` | YAML frontmatter has all required fields, valid enums, valid ranges | Reject before write; re-audit during `curation-cycle` Step 1 |
| `connections.json` | Valid JSON, no dangling card references, valid connection types, no duplicate edges | Reject before write; re-audit during `curation-cycle` Step 1 |
| `domains.yaml` | Valid YAML, unique domain IDs, valid status enums | Reject before write |
| `governance.yaml` | All required fields present, numeric ranges valid | Reject before write |
| `search-seeds.json` | Valid JSON, weights 0.0–1.0, valid statuses, domain references exist | Reject before write; re-audit after research/search updates |
| `refs/*.json` | Required fields present, relevance 0.0–1.0, source_tier 1–5 | Reject before write; re-audit after `research-cycle` |
| workflow-produced canonical artifacts | Must satisfy their target canonical schema before persistence | Reject before write |
| `log/events.jsonl` | Each line is valid JSON with required fields | Validate at append boundary; audit continuously |

**Every skill includes validation steps.** The "Validation" section at the bottom of each SKILL.md is the checklist.

### Layer 2: Governance Validation (Semantic)

Rules from `governance.yaml` must be respected:

| Rule | Check |
|------|-------|
| Promotion thresholds | No card promoted that doesn't meet criteria (or has explicit override reason) |
| Decay window | Flagged cards are genuinely past the threshold |
| Relevance thresholds | No ref ingested below threshold without explicit reason |
| Source tier assignment | Tier matches the actual source quality |
| Confidence assignment | Confidence matches evidence strength |

**The `curation-cycle` skill is the primary governance validator.** It checks every card against every rule.

### Layer 3: Consistency Validation (Cross-File, Post-Write Audit)

Files reference each other. References must be valid:

| Reference | Must exist |
|-----------|-----------|
| Card `domains` field values | `domains.yaml` entries |
| Card `content_categories` values | Domain's `content_categories` list |
| Card `connects_to` targets | Other card files in `cards/` |
| `connections.json` `from`/`to` | Card files in `cards/` |
| Ref `domain` field | `domains.yaml` entry |
| Search cluster `domain` field | `domains.yaml` entry |
| Publish `source_cards` values | Card files in `cards/` |

**The `curation-cycle` integrity check (Step 1) validates all cross-references.**

### Layer 4: Functional Validation (User Journeys, Post-Write Audit)

The ultimate validation: do the user journeys work?

| Journey | Validation approach |
|---------|-------------------|
| J1: Cold Start | Run the cold-start workflow end-to-end. Workspace exists with valid structure, domain configured, research produced cards, curation validated them. |
| J2: Daily Use | Resume a session, run research + curation, add cards, connect them, check status. All workspace files remain valid. |
| J3: Co-authorship | Synthesize a draft that references real cards, propagates confidence, and produces a valid `publish/` artifact. |

### Layer 5: Audit Trail Validation (Historical, Post-Write Audit)

`events.jsonl` provides a verifiable history:

| Check | How |
|-------|-----|
| Every card creation is logged | `create_card` event for each file in `cards/` |
| Every promotion is logged | `promote_card` event with from/to lifecycle |
| Every research cycle is logged | `research_cycle_complete` with stats |
| Every curation cycle is logged | `curation_cycle_complete` with stats |
| Events have timestamps | All `ts` fields are valid ISO-8601 |
| Events reference real targets | `target` values correspond to actual cards/domains |

---

## 3. Validation Skill

A dedicated validation skill can be invoked to audit the workspace:

**Trigger:** "Validate workspace" or "audit"

**Procedure:**
1. Run Layer 1 (schema) checks on all files
2. Run Layer 2 (governance) checks against governance.yaml
3. Run Layer 3 (consistency) cross-reference checks
4. Report findings:

```
Workspace Validation Report — {date}

Schema: {N} files checked, {N} valid, {N} errors
Governance: {N} rules checked, {N} compliant, {N} violations
Consistency: {N} references checked, {N} valid, {N} dangling

Errors:
- {file}: {error description}

Warnings:
- {file}: {warning description}
```

---

## 4. Comparison to Python Test Strategy

| Python approach | Claude-native equivalent |
|----------------|-------------------------|
| Unit tests (pytest) | Schema validation in skill procedures |
| Integration tests | Full workflow execution (cold-start, daily-cycle) |
| Contract tests (JSON Schema) | Validation steps in each skill |
| CI pipeline | Manual "validate workspace" skill invocation |
| Pre-commit hooks | Skills validate before writing |
| LLM mocking | Not applicable — Claude is the real runtime |

**Phase 1 refinement:** canonical workspace artifacts should no longer rely on post-hoc detection alone. Invalid cards, refs, connections, and workflow-produced canonical outputs are rejected before write; post-write validation handles audit and consistency after a valid write lands.

---

## 5. Continuous Validation Principle

Every skill that writes a file should:
1. Validate the output before writing
2. Validate cross-references after writing
3. Include a "Validation" checklist at the end of the SKILL.md

This isn't a separate step — it's embedded in every operation.

## 6. Phase 1 enforcement boundary summary

| Artifact class | Pre-write behavior | Post-write behavior |
|----------------|--------------------|---------------------|
| `cards/*.md` | Reject invalid card payloads before persistence | Audit links, governance, and fixture proof |
| `refs/*.json` | Reject invalid ref payloads before persistence | Audit domain alignment and downstream card references |
| `connections.json` | Reject invalid graph mutations before persistence | Audit graph-wide consistency and integrity |
| `domains.yaml`, `governance.yaml`, `search-seeds.json` | Reject invalid config mutations before persistence | Audit policy impact and fixture proof |
| `digests/`, `publish/` | Validate workflow output format before write when applicable | Audit user-journey quality and cited-source integrity |
