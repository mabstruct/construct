# CONSTRUCT — Non-Functional Requirements

**Version:** 0.1.0
**Date:** 2026-04-19
**Status:** Draft — targets are initial; refine when real measurements exist

---

## 1. Performance

| Requirement | Target (v0.1) | Measurement |
|-------------|---------------|-------------|
| **Graph render** | ≤500 cards rendered at ≥30fps in D3 force-directed view | Chrome DevTools FPS meter on reference hardware |
| **Views step** | <1s for ≤500 cards; <5s for ≤5,000 cards | Wall-clock time of `construct views` |
| **Cold start** | `construct init` → first heartbeat complete in <10s on standard laptop | Wall-clock from command to first `views/` output |
| **CLI response** | Quick ops (`construct status`, `construct graph stats`) respond in <500ms | No LLM call involved — pure computation |
| **SQLite queries** | FTS5 search returns in <100ms for ≤10,000 cards | sqlite3 .timer on |
| **Chat round-trip** | WebSocket message → agent response starts streaming in <2s (excluding LLM latency) | Measured at the server, not including provider response time |

### Scalability limit (acknowledged, not solved in v0.1)

v0.1 architecture is designed for **≤5,000 cards**. Beyond that:
- NetworkX in-memory graph may need persistence or partitioning
- SQLite FTS5 remains viable to ~100k rows
- D3 force-directed graph needs virtualization or clustering above ~1,000 visible nodes
- ChromaDB (v0.2) is the scaling unlock for semantic search

Document this limit in user-facing docs. Do not over-engineer before hitting it.

---

## 2. Reliability

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| **LLM call failure** | Log to `log/events.jsonl`, retry once after 5s, then skip and continue. Next heartbeat retries. | Simple retry decorator on LLM client calls |
| **Agent crash** | Log stack trace to `log/events.jsonl`. Heartbeat re-enters on next cycle. No silent failures. | try/except at heartbeat loop level |
| **Data integrity** | Markdown source of truth is never corrupted by agent failure. Partial writes are detectable. | Write to temp file → atomic rename. Cards are small files. |
| **Rebuild guarantee** | `construct rebuild-db` restores `db/` fully from source of truth files (cards/, refs/, domains.yaml, etc.). Tested in CI. | Integration test that deletes `db/`, rebuilds, asserts parity |

---

## 3. Security

| Requirement | Implementation |
|-------------|----------------|
| **API keys** | Loaded from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) or `.env` file in workspace root. `.env` is in `.gitignore`. |
| **No secrets in output** | API keys, tokens, and credentials must never appear in `views/`, `publish/`, `log/`, `cards/`, or git history. Validated by a pre-commit hook or CI check. |
| **Localhost binding** | Server binds to `127.0.0.1` only. `0.0.0.0` requires explicit `--bind-all` flag with a printed warning. |
| **No remote code execution** | Agents do not execute arbitrary code from LLM output. Agent actions are limited to: file read/write within workspace, LLM API calls, HTTP GET to research APIs. |
| **Dependency audit** | `pip audit` and `npm audit` in CI. No known critical CVEs in dependencies at release time. |

---

## 4. Privacy

**Principle:** User data never leaves the local machine except via user-configured LLM API calls.

| Aspect | Policy |
|--------|--------|
| **Knowledge graph** | Stays on local filesystem. Never synced, uploaded, or phoned home. |
| **LLM API calls** | Only the content the user configured for that task-tier is sent. Users choose their provider and what gets routed where via `model-routing.yaml`. |
| **Telemetry** | **None. Ever.** No usage tracking, no analytics, no crash reporting. Local-first means local-only. |
| **Cloud sync (v0.2+)** | Opt-in only. User chooses destination (GitHub, S3, custom). Never automatic. |

---

## 5. Portability

| Target | v0.1 | v0.2 | Notes |
|--------|------|------|-------|
| **macOS (Apple Silicon + Intel)** | ✅ | ✅ | Primary dev platform |
| **Linux (Ubuntu 22.04+, Fedora 38+)** | ✅ | ✅ | CI runs on Ubuntu |
| **Windows** | ❌ | 🟡 Evaluate | Path handling, shell scripts need cross-platform testing. WSL is a fallback. |

Python 3.11+ required. Node 20+ for UI build only.

---

## 6. Observability

| Artifact | Format | Retention | Purpose |
|----------|--------|-----------|---------|
| `log/events.jsonl` | Append-only JSONL | Indefinite (git-tracked) | Full audit trail of all agent actions |
| `views/events-recent.json` | JSON array | Rolling window (last 7 days) | UI activity timeline |
| `views/agents-status.json` | JSON | Current state only | UI agent panels |
| CLI: `construct status` | Human-readable text | N/A | Quick health check |

Event schema (minimum fields per event):

```json
{
  "ts": "2026-04-19T14:30:00Z",
  "agent": "curator",
  "action": "promote_card",
  "target": "card-id",
  "detail": "confidence 2→3, source tier 2",
  "result": "success"
}
```

---

## 7. Accessibility

v0.1 target: **functional, not certified.**

- Keyboard navigation for all interactive UI elements
- Semantic HTML (`<nav>`, `<main>`, `<article>`, `<button>`, not `<div onClick>`)
- Sufficient color contrast (WCAG AA for text)
- Screen reader: best-effort, not formally tested in v0.1
- Full WCAG AA audit: v0.3 if community requests it

---

## 8. Internationalization

**Out of scope for v0.1.** English only.

- All UI strings are hardcoded in English
- Knowledge cards are in whatever language the user writes (no system constraint)
- i18n framework: defer to v0.3+ if demand exists
- LLM prompts: English only (prompt quality degrades in translation)

---

## 9. Backwards Compatibility

v0.1 is the first release. No backwards-compatibility obligations.

**Forward-compatibility commitment:** the workspace directory format (markdown cards with YAML frontmatter, flat config files) is the long-term stable interface. Schema changes to card format will be versioned and migration scripts provided. Users' knowledge is sacred; breaking it is never acceptable.

---

## 10. Licensing

**Apache-2.0** — consistent with prior art (BMAD, OpenCode, HIVE) and provides patent protections appropriate for an agent-runtime project. See ADR-0002 (pending).
