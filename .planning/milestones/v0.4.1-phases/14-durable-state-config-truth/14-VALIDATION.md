---
phase: 14
slug: durable-state-config-truth
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-19
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> Seeded from `14-RESEARCH.md` § Validation Architecture (21 mechanical assertions:
> 18 grep/shell + 2 pytest + 1 `git diff --name-only` fence check).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config in `pyproject.toml` `[tool.pytest.ini_options]`, lines 40-42) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/contract -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~60 seconds (full suite) |

**Baseline (verified 2026-07-19 at commit `4a9edb7`):** exactly **439 tests collected**,
`_KNOWN_BROKEN` at **5 entries** (`tests/contract/test_doc_command_references.py:152-158`).

**Criterion 5 risk: LOW.** `_DOC_GLOBS` (`test_doc_command_references.py:41-45`) scans only
`CONSTRUCT-CLAUDE-impl/claude/skills/*/SKILL.md`, `construct/workflows/*.md`, and
`USER-TEST-PLAYBOOK-v03.md` — **not** `CONSTRUCT-CLAUDE-spec/`. No test imports Streamlit.
The doc edits in this phase are therefore invisible to the suite; the only new test surface is
the Q1 resolver.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/contract -q`
- **After every plan wave:** `.venv/bin/python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green at **≥439** collected
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Populated by `/gsd-plan-phase` task breakdown; each row maps to one PLAN.md task.
> Doc-truth tasks verify by grep assertion against a named file + exact string;
> the Q1 resolver task verifies by pytest.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T1 write adr-0004 | 14-01 | 1 | DOC-03 | T-14-01-01/03 | Archive untouched; no unearned durability claim | grep + git | `grep -qE '^## Decision' <adr>` + `[ -z "$(git status --porcelain .planning/milestones/)" ]` | ❌ new | ⬜ pending |
| T2 arch carve-out + ADR index | 14-01 | 1 | DOC-03 | — | N/A | grep | `grep -F 'Add a database that owns part of the truth' arch \| grep -qF adr-0004` | ✅ | ⬜ pending |
| T1 scope §2 invariant | 14-02 | 2 | DOC-03 | T-14-02-03 | Guarantee scoped, not silently weakened | grep | `[ "$(grep -c 'No databases, no caches' nfrs.md)" = 0 ]` + `grep -qF NetworkX nfrs.md` | ✅ | ⬜ pending |
| T2 §3 authority + §4 Tavily | 14-02 | 2 | DOC-03 / FIX-02 | T-14-02-01/02 | Conditional egress claim; real authority named | grep | `grep -qi tavily nfrs.md` + `grep -qF 'llm/config.yaml' nfrs.md` | ✅ | ⬜ pending |
| T1 artifacts + 4th class | 14-03 | 2 | DOC-03 | T-14-03-01/02 | Contract code untouched; sqlite not under Support | grep + pytest | `.venv/bin/python -m pytest tests/unit/test_workspace_contracts.py -q` | ✅ | ⬜ pending |
| T2 deprecate in contract | 14-03 | 2 | FIX-02 | T-14-03-03 | Exhaustive deprecation; scaffolding intact | grep + pytest | `[ "$(grep -i model-routing wc.md \| grep -civ deprecat)" = 0 ]` | ✅ | ⬜ pending |
| T3 deprecate in topology | 14-03 | 2 | FIX-02 | T-14-03-03/04 | Python column preserved as historical | grep + pytest | `[ "$(grep -i model-routing ct.md \| grep -civ deprecat)" = 0 ]` + `pytest -q` | ✅ | ⬜ pending |
| T1 resolver test (RED) | 14-04 | 1 | FIX-02 | — | N/A | unit | `.venv/bin/python -m pytest tests/unit/test_llm_config_resolution.py -q` (expect RED) | ❌ new | ⬜ pending |
| T2 extract resolver (GREEN) | 14-04 | 1 | FIX-02 | T-14-04-04/05 | Identical resolution semantics; no added validation | unit | `.venv/bin/python -m pytest -q` → 443 passed | ✅ | ⬜ pending |
| T3 read-only sidebar | 14-04 | 1 | FIX-02 | T-14-04-01/03 | No editable path field; path-only, never contents | grep + manual | `[ "$(grep -cE 'load_llm_config\(' streamlit_app.py)" = 0 ]` + human-check | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] **Planned as plan 14-04 Task 1 (RED) + Task 2 (GREEN).** Q1 resolved in favour of Option A
      (extract a public resolver); the authorization rationale is recorded in 14-04-PLAN.md
      `<scope_decision>`. Expected final collected count: **443** (439 baseline + 4).
- [ ] `tests/unit/test_llm_config_resolution.py` — covers `resolve_llm_config_path()` (Q1 decision:
      extract a public resolver in `src/construct/llm/config.py`). Must assert all three branches of
      the resolution order: explicit arg → `CONSTRUCT_LLM_CONFIG` env → packaged default, and that
      `load_llm_config()` delegates to it (one code path, two callers — the drift-proofing D-10 requires).

*Existing pytest infrastructure covers everything else; no framework install needed.*

**Note on the ≥439 floor (research assumption A2):** adding the resolver test raises the collected
count above 439. ROADMAP criterion 5 says "≥439", so this is compliant — but the plan must state
the expected final count explicitly so the delta is intentional, not drift.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Streamlit sidebar renders the effective LLM config path as read-only text (not an editable input) | FIX-02 / criterion 3 | No test imports Streamlit; `st.text_input` → static display is a render-level change with no assertable return value | `streamlit run src/construct/ui/streamlit_app.py`; confirm sidebar shows the resolved path as static text with no edit affordance. Re-run with `CONSTRUCT_LLM_CONFIG=/tmp/x.yaml` set and confirm the displayed path changes to match. |
| Same for `provider_override` (D-11) | FIX-02 | Identical dead-control defect, same render-level change | Confirm the provider override is displayed read-only, not as an editable control. |
| D-02 edit fence held | FIX-02 / criterion 4d | Negative constraint — provable only across the whole phase diff, not per-task | `git diff --name-only <phase-base>..HEAD` must not list `AGENTS.md`, `USER-TEST-PLAYBOOK-v03.md`, `spec-v04-agentworkflows.md`, or `migrations/phase-1-workspace-contract-migration.md`. Recommended as a **phase gate**, not a per-task check. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
