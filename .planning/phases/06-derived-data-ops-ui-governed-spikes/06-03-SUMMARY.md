---
phase: 06-derived-data-ops-ui-governed-spikes
plan: 06-03
subsystem: pipelines, skills
tags: spike-runner, isolation, temp-copy, graphify, infranodus, graph-exploration

# Dependency graph
requires:
  - phase: 03-capability-registry-cli-mcp-spine
    provides: CLI patterns, typer command groups, path-based workspace operations
  - phase: 04-guided-workflow-operability
    provides: pipeline functional pattern (standalone functions, dataclass results)
  - phase: 05-grounded-synthesis-graph-reasoning
    provides: bridge_detect pipeline pattern, test workspace fixtures
provides:
  - Spike isolation runner — copies workspace to temp dir, executes external tool, captures output, cleans up
  - Documented SKILL.md procedures for Graphify and InfraNodus spike types
  - CLI command group pattern for spike operations
affects: future plans needing external tool evaluation, tag extraction pipeline, v0.4 UI design input

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Spike isolation pattern — temp workspace copy with derived-dir exclusion
    - Command injection mitigation via shlex.quote() + shlex.split()
    - Structured spike result dataclass with serialization to log/spike-results/

key-files:
  created:
    - src/construct/pipelines/spike_runner.py — SpikeRunner with run_spike, list_spikes, register_spike_commands
    - CONSTRUCT-CLAUDE-impl/claude/skills/construct-spike-run/SKILL.md — Documented spike procedures
  modified: []

key-decisions:
  - "No SpikeRunner class — functional module-level pattern matches existing pipelines (bridge_detect, ingestion)"
  - "Command injection safety via shlex.quote() on path values + shlex.split() → subprocess.run without shell=True"
  - "register_spike_commands() creates typer group for future cli.py wiring — not wired yet, kept decoupled"
  - "Results persist to install_root/log/spike-results/ with fallback to workspace parent"

patterns-established:
  - "Spike isolation: mkdtemp → copy selected canonical files (skip derived) → validate tool → subprocess → capture → persist → finally cleanup"
  - "Spike definitions as KNOWN_SPIKES module-level dict — extensible by adding entries"

requirements-completed: [SPK-01, SPK-04]

# Metrics
duration: 12min
completed: 2026-06-11
---

# Phase 06 Plan 03: Governed Spike Framework Summary

**Spike isolation runner with temp workspace copies and documented Graphify/InfraNodus evaluation procedures**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-11T19:55:00Z
- **Completed:** 2026-06-11T20:07:00Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- Created `src/construct/pipelines/spike_runner.py` — spike isolation runner with `run_spike()`, `list_spikes()`, `register_spike_commands()` per D-05
- Temp workspace isolation: copies canonical items (cards, refs, connections.json, domains.yaml), skips large derived dirs (views/build/, digests/)
- Results persist to `log/spike-results/{tool}-{timestamp}.json` with full capture of outputs, stdout, stderr
- Guaranteed cleanup via try/finally even on failure (T-06-08 mitigation)
- Command injection safety via shlex.quote() + shlex.split() (T-06-09 mitigation)
- Created `CONSTRUCT-CLAUDE-impl/claude/skills/construct-spike-run/SKILL.md` with documented procedures
- Both spike types (Graphify-style, InfraNodus-style) include How to Run, What to Evaluate (tables), and Interpreting Results (tables)
- InfraNodus explicitly noted as spike-only evaluation per D-09

## Task Commits

Each task was committed atomically:

1. **Task 1: Create spike runner pipeline with temp workspace isolation** - `7ab480f` (feat)
2. **Task 2: Document spike procedures as SKILL.md** - `c50bce9` (docs)

**Plan metadata:** `(pending final commit)`

## Files Created
- `src/construct/pipelines/spike_runner.py` — Spike isolation runner (487 lines):
  - `SpikeDefinition` and `SpikeResult` dataclasses
  - `KNOWN_SPIKES` dict with graphify and infranodus definitions
  - `run_spike()` — validates tool, creates temp copy, runs subprocess, captures outputs, persists results, cleans up
  - `list_spikes()` — returns spike definitions for CLI display
  - `register_spike_commands()` — typer command group for future CLI wiring
  - `_copy_workspace()` — copies canonical items, skips derived dirs
  - `_capture_output()` — reads expected output files from temp copy
  - `_persist_result()` — writes structured JSON to log/spike-results/
  - `_display_spike_result()` — renders CLI output
- `CONSTRUCT-CLAUDE-impl/claude/skills/construct-spike-run/SKILL.md` — Spike run skill procedure (203 lines):
  - Prerequisites, step-by-step procedure with CLI examples
  - Graphify section: Purpose, How to Run, What to Evaluate (table), Interpreting Results (table)
  - InfraNodus section: same structure with D-09 spike-only note
  - Failure-mode reference table
  - Validation checklist

## Decisions Made
- **No SpikeRunner class** — Followed existing pipeline convention of module-level functions and dataclasses (matches bridge_detect.py, ingestion.py). The plan's done criteria mentioned a class but the detailed structure specified functions — functional pattern is more consistent.
- **Command injection mitigation** — Used `shlex.quote()` on path values and `shlex.split()` to convert the resolved template to a list before `subprocess.run()`. This avoids `shell=True` while supporting the command template pattern described in the plan.
- **register_spike_commands() kept decoupled** — The CLI wiring function is defined on the module but not imported/called from cli.py yet. It will be wired when the phase 6 CLI integration tasks are reached. This keeps the module testable and importable without typer.
- **install_root fallback** — If install_root is not provided, defaults to workspace parent. This means results are written relative to the workspace's parent directory (e.g., test-ws/log/spike-results/ for test-ws/my-construct).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all tasks completed without issues.

## User Setup Required

None — no external service configuration required. External spike tools (graphify, infranodus) must be installed separately by the user per the SKILL.md prerequisites.

## Next Phase Readiness
- Spike runner is ready for CLI integration (wiring `register_spike_commands` into cli.py)
- SKILL.md documents both spike types for immediate use
- Graphify spike foundation ready for tag extraction pipeline (future Phase 6 plan)
- InfraNodus evaluation framework ready for v0.4 UI design input

---
*Phase: 06-derived-data-ops-ui-governed-spikes*
*Plan: 06-03*
*Completed: 2026-06-11*
