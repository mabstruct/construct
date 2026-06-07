# Phase 1: Workspace & Canonical Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 1-Workspace & Canonical Data Foundation
**Areas discussed:** Workspace Shape, Init Experience, Domain Configuration Model, Validation Posture

---

## Workspace Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Full workspace scaffold now | Create the long-term layout up front, including canonical, derived, and future-use directories/files. | ✓ |
| Phase 1 minimal scaffold | Create only the directories and files directly needed by Phase 1. | |
| Hybrid scaffold | Create the full top-level shape but only seed Phase 1 files with meaningful contents. | |

**User's choice:** Full workspace scaffold now
**Notes:** The workspace contract should be stable from the first run rather than expanded phase by phase.

---

## Init Experience

| Option | Description | Selected |
|--------|-------------|----------|
| Fully guided | Walk through domain scope, taxonomy seeds, source priorities, and research seeds step by step. | |
| Lightly guided with defaults | Ask only essential setup questions and write sensible defaults for the rest. | ✓ |
| Mostly non-interactive | Create defaults and leave follow-up editing to the user. | |

**User's choice:** Lightly guided with defaults
**Notes:** The flow should still feel guided, but not heavy.

---

## Domain Configuration Model

| Option | Description | Selected |
|--------|-------------|----------|
| Shared root files only | Store domain configuration only in root canonical files. | |
| Per-domain folders from the start | Give each domain its own folder/files immediately. | ✓ |
| Mixed model | Keep root canonical config and also create supporting per-domain directories. | |

**User's choice:** Per-domain folders from the start
**Notes:** Follow-up clarification locked a root `domains.yaml` as the canonical registry while per-domain folders hold domain-local setup details.

---

## Validation Posture

| Option | Description | Selected |
|--------|-------------|----------|
| Strict structure, soft quality | Hard-fail canonical/schema breaks, warn on softer quality issues. | ✓ |
| Strict on almost everything | Treat most schema and content conventions as hard errors. | |
| Lenient early | Allow partially formed content and rely mostly on warnings. | |

**User's choice:** Strict structure, soft quality
**Notes:** Canonical integrity matters, but the system should avoid punishing early authoring for non-structural issues.

---

## Claude's Discretion

- Exact init question wording and defaults.
- Exact per-domain file names and warning presentation.

## Deferred Ideas

None.
