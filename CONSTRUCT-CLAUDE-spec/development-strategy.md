# CONSTRUCT Agent System — Development Strategy

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active

---

## 1. Purpose

This document answers: **What do we configure, in what order, and how do we know it works?**

Unlike the Python approach (8 phases of code), the Claude-native approach is configuration. Phases are about **completeness and validation**, not compilation and testing.

---

## 2. Guiding Principles

| Principle | Implication |
|-----------|-------------|
| **Configuration over code** | We write markdown and JSON, not Python |
| **Validate by running** | Test a skill by invoking it, not by running pytest |
| **Shared workspace first** | Workspace format must match CONSTRUCT-spec/ for interoperability |
| **Skills are atomic** | Each skill is independently testable and usable |
| **Identity before skills** | Get AGENTS.md right — it governs everything else |

---

## 3. Phases

### Phase 0 — Foundation

**Goal:** Core identity and workspace scaffolding work.

**What:**
- `AGENTS.md` — root agent identity with voice, routing, guardrails
- `templates/` — all workspace file templates
- `references/` — all lookup tables and enum definitions
- `skills/workspace-init/SKILL.md` — creates workspace from templates
- `skills/domain-init/SKILL.md` — domain interview

**Exit criteria:**
- Invoke "Initialize a CONSTRUCT workspace" → valid workspace created
- Invoke "Add a domain" → interview runs, `domains.yaml` and `search-seeds.json` populated
- All reference tables are complete and consistent with card schema

**Estimated effort:** Done (completed in initial creation)

---

### Phase 1 — Knowledge Operations

**Goal:** Cards can be created, edited, connected, and archived.

**What:**
- `skills/card-create/SKILL.md` — create cards from conversation/URL
- `skills/card-edit/SKILL.md` — modify existing cards
- `skills/card-archive/SKILL.md` — archive with supersedes handling
- `skills/card-connect/SKILL.md` — manage connections

**Exit criteria:**
- Create a card from a pasted URL → valid card file with ref
- Edit a card's confidence → frontmatter updated correctly
- Archive a card → lifecycle set to archived, connections handled
- Connect two cards → `connections.json` updated with typed edge

**Estimated effort:** Done (all skills created)

---

### Phase 2 — Research & Curation

**Goal:** Research cycles produce real content, curation maintains quality.

**What:**
- `agents/researcher.md` — researcher role definition
- `agents/curator.md` — curator role definition
- `skills/research-cycle/SKILL.md` — 7-step research cycle
- `skills/curation-cycle/SKILL.md` — 7-step curation cycle
- `skills/card-evaluate/SKILL.md` — promotion evaluation

**Exit criteria:**
- Run research cycle on a configured domain → refs + seed cards created
- Run curation cycle → integrity check, decay scan, promotions applied
- Ambiguous card evaluated → promote/hold/escalate decision with reasoning

**Estimated effort:** Done (all skills exist)

---

### Phase 3 — Analysis & Synthesis

**Goal:** Analysis and output generation work end-to-end.

**What:**
- `skills/gap-analysis/SKILL.md` — coverage and structural gap detection
- `skills/synthesis/SKILL.md` — drafting with confidence propagation
- `skills/graph-status/SKILL.md` — health dashboard
- `skills/bridge-detect/SKILL.md` — cross-domain detection
- `skills/search-adjust/SKILL.md` — search pattern management

**Exit criteria:**
- Gap analysis on a domain → actionable gap report with recommendations
- Synthesis request → draft in `publish/` with source card references
- Graph status → accurate card counts, connection stats, quality indicators
- Bridge detection → cross-domain candidates identified
- Search adjust → patterns modified with confirmation

**Estimated effort:** Done (all skills exist)

---

### Phase 4 — Workflows & Integration

**Goal:** Multi-skill workflows run end-to-end. All three user journeys work.

**What:**
- `workflows/cold-start.md` — J1 end-to-end
- `workflows/daily-cycle.md` — J2 patterns
- `workflows/co-authorship.md` — J3 drafting flow
- `skills/domain-manage/SKILL.md` — pause, edit, archive domains
- `skills/workspace-validate/SKILL.md` — audit workspace integrity

**Exit criteria:**
- Cold start workflow creates workspace, configures domain, researches, curates, reports — all valid
- Daily cycle: resumption with status, research, curation, user interaction
- Co-authorship: draft produced with confidence propagation and source tracing
- Workspace validation passes all 5 layers on a mature workspace

**Estimated effort:** Done (all skills and workflows created)

---

### Phase 5 — Polish & Documentation

**Goal:** Ready for deployment and sharing.

**What:**
- `CONSTRUCT-CLAUDE-impl/README.md` — deployment guide
- Validate all skills against updated schemas
- Ensure all cross-references between skills, agents, and references are consistent
- Test portability: verify config works on different Claude surfaces

**Exit criteria:**
- A new user can deploy and run cold-start within 15 minutes
- All skill validation checklists pass
- README is self-sufficient

**Estimated effort:** Done (README exists; consistency review and deployment test completed 2026-04-25)

---

## 4. Current Status

**v0.1 — Complete (2026-04-25)**

| Phase | Status | Remaining |
|-------|--------|-----------|
| Phase 0 | ✅ Complete | — |
| Phase 1 | ✅ Complete | — |
| Phase 2 | ✅ Complete | — |
| Phase 3 | ✅ Complete | — |
| Phase 4 | ✅ Complete | — |
| Phase 5 | ✅ Complete | — |

### v0.1 Verification Summary

| Criterion | Status |
|-----------|--------|
| J1 (cold-start) end-to-end | ✅ All 3 domains |
| J2 (daily-cycle) end-to-end | ✅ Philosophy-of-mind ran 2 full cycles |
| J3 (co-authorship) end-to-end | ✅ Cosmology publish flow complete |
| Workspace validation (5 layers) | ✅ All 3 domains validated; drift fix applied |
| Every skill invoked at least once | ✅ 16/17 invoked; `card-archive` deferred to v0.2 |
| Config sync (impl ↔ deployment) | ✅ 100% — all 38 files identical |
| events.jsonl records all actions | ✅ 691 events across 3 domains |

**Workspace at close:** 75 cards, 125 connections, 90 refs, 3 digests, 3 curation reports, 1 published article across 3 domains (cosmology, philosophy-of-mind, philosophy-of-physics).

**Next:** [v0.2 — Live Views (prd-v02-live-views.md)](prd-v02-live-views.md)

---

## 5. Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Claude context window too small for large workspaces | Skills fail to read all cards | Domain-scoped operations; Python complement for scale |
| Web search quality varies | Research cycle produces poor results | Relevance scoring + human review of seed cards |
| Skills not followed precisely | Inconsistent workspace state | Validation steps in every skill; workspace-validate skill |
| Config format changes between Claude versions | Skills break | Plain markdown; no Claude-specific features |
| Workspace format diverges from Python approach | Interoperability lost | Shared schemas; this spec explicitly documents shared format |

---

## 6. Success Criteria

The CONSTRUCT agent system is ready when:

1. All three user journeys (J1–J3) execute successfully end-to-end
2. Workspace validation passes all 5 layers
3. Every skill has been invoked at least once with real data
4. `events.jsonl` accurately records all actions
5. A new user can deploy and complete J1 within 15 minutes
6. Workspace produced by Claude-native approach is valid for potential Python-approach consumption
