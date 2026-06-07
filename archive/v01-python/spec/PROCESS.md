# CONSTRUCT — Development Process

**Version:** 0.1.0
**Date:** 2026-04-19
**Status:** Active — governs all implementation work

---

## 1. Development Agent: Claude Code

Claude Code is the primary development agent for CONSTRUCT. This document defines how it operates, what gates its work, and how continuity is maintained across sessions.

### 1.1 Session Protocol

Every Claude Code session working on CONSTRUCT must:

1. **Read** `CLAUDE.md` (repo root) — working agreements, constraints, current priorities
2. **Read** `dev/CURRENT.md` — what is in progress, what was last done, what is next
3. **Check** `dev/decisions/` — if the current task touches an area with an ADR, read it
4. **Plan before code** — for any task touching 3+ files, enter plan mode first. Write the plan to `dev/plans/`. Get human approval before implementing.
5. **Update** `dev/CURRENT.md` at session end — what was done, what is unfinished, what is blocked

### 1.2 Working Agreements

These are hard rules. Claude Code must never violate them.

| Rule | Why |
|------|-----|
| Never push to `main` directly | All work goes through branches → PR → review → merge |
| Never delete `templates/` or `specs/` content without asking | These are governance artifacts |
| Always run `pytest` and `vite build` before proposing a PR | CI will catch it anyway; catch it first |
| Never commit `.env`, API keys, or secrets | Check `.gitignore` before staging |
| Never invent new data schemas | All schemas live in `specs/construct-data-schemas.md`; reference it, don't ad-hoc |
| Plan mode first for multi-file changes | Write plan in `dev/plans/{task-name}.md` before coding |
| One logical change per commit | Don't bundle unrelated changes |
| Conventional commits | `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:` |
| Co-author trailer on all commits | `Co-authored-by: Claude Code <claude@anthropic.com>` |

### 1.3 Branching Strategy

```
main (protected)
  └── feat/agent-runtime
  └── feat/graph-engine
  └── feat/react-ui-scaffold
  └── fix/card-schema-validation
  └── docs/nfrs
```

- Branch names: `{type}/{short-description}` (`feat/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/`)
- Branches are short-lived (1–3 days max)
- Use worktrees for non-trivial tasks when running Claude Code
- Rebase onto main before PR (no merge commits on feature branches)
- Squash merge to main via PR

### 1.4 PR Process

1. Claude Code creates branch, implements, writes tests
2. Claude Code opens PR with summary + test plan
3. Human reviews (or delegates review to a second Claude Code session)
4. CI must pass (pytest + vitest + ruff + tsc + vite build)
5. Human merges to main

### 1.5 Task Decomposition

Large tasks follow this flow:

```
Spec (in specs/)
  → Plan (in dev/plans/{task}.md) — Claude Code proposes, human approves
    → Branch (feat/{task})
      → Implementation + tests
        → PR → review → merge
          → Update dev/CURRENT.md
```

Plans must contain:
- **Goal:** 1-sentence what and why
- **Files to create/modify:** complete list
- **Data contracts:** which schemas are read/written
- **Test plan:** what tests will be added
- **Risks:** what could go wrong
- **Exit criteria:** how to know it is done

### 1.6 Continuity Between Sessions

Claude Code sessions are ephemeral. Continuity is maintained through:

| Artifact | Purpose | Updated by |
|----------|---------|------------|
| `dev/CURRENT.md` | What is happening right now | Claude Code, every session start/end |
| `dev/decisions/adr-*.md` | Why we chose X over Y | Claude Code when a decision is made |
| `dev/plans/*.md` | Implementation plans (approved or in-review) | Claude Code before implementation |
| `CLAUDE.md` | Persistent working agreements for Claude Code | Human or Claude Code (with human approval) |
| Git log | What was actually done | Commit messages |
| PR descriptions | What a change does and why | Claude Code on PR creation |

`dev/CURRENT.md` format:

```markdown
# CONSTRUCT — Current State

**Last updated:** {date}
**Last session:** {what was done}
**In progress:** {branch name, what is being worked on}
**Blocked on:** {anything waiting for human input}
**Next up:** {what the next session should pick up}
**Open questions:** {decisions needed}
```

---

## 2. Code Standards

### 2.1 Python

- **Formatter:** ruff format
- **Linter:** ruff check
- **Type checker:** mypy (strict mode)
- **Min version:** Python 3.11
- **Style:** Google docstring convention (only on public APIs — not every function)
- **Imports:** isort via ruff, absolute imports from `construct.*`

### 2.2 TypeScript / React

- **Formatter:** prettier
- **Linter:** eslint
- **Type checker:** tsc --noEmit
- **Framework:** React 18+ with Vite
- **Styling:** Tailwind CSS
- **State:** Zustand (lightweight, no boilerplate)
- **Components:** functional only, no class components

### 2.3 Shared

- No comments explaining *what* — only *why* (when non-obvious)
- No dead code, no TODO comments in committed code (use GitHub Issues)
- No over-abstraction — three similar lines are better than a premature helper

---

## 3. Definition of Done

A task is done when:

- [ ] Implementation matches the plan (or plan was updated with rationale)
- [ ] Tests pass locally (`pytest` + `vitest`)
- [ ] Linters pass (`ruff check` + `eslint` + `tsc --noEmit`)
- [ ] Build succeeds (`vite build`)
- [ ] No new warnings introduced
- [ ] `dev/CURRENT.md` updated
- [ ] PR opened with summary and test plan
- [ ] CI green

---

## 4. Directory Ownership

| Directory | Owner | May write |
|-----------|-------|-----------|
| `src/construct/agents/` | Agent runtime team | Agent logic, session management, heartbeat |
| `src/construct/graph/` | Graph engine team | NetworkX build, query, publish renderer |
| `src/construct/storage/` | Storage team | SQLite, indexer, rebuild |
| `src/construct/research/` | Research team | API clients, ingestion, search patterns |
| `src/construct/workflows/` | Workflow team | BMAD skill engine, domain init |
| `src/construct/server.py` | Server team | WebSocket, HTTP, static file serving |
| `ui/` | UI team | React components, pages, hooks |
| `templates/` | Governance | Agent SOULs, default configs, workflow defs |
| `specs/` | Planning | Specs, schemas, NFRs |
| `dev/` | Process | ADRs, plans, journal, CURRENT.md |
| `tests/` | Everyone | Tests mirror src/ structure |

("Team" = whoever is working on that area in a given session — typically Claude Code + human.)
