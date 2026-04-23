# CONSTRUCT Agent System — Non-Functional Requirements

**Version:** 1.0.0
**Date:** 2026-04-23
**Status:** Active

---

## 1. Performance

| Requirement | Target | Notes |
|-------------|--------|-------|
| Workspace init | <2 minutes from start to first domain | Template-based, no compilation |
| Research cycle | <10 minutes for a domain with 3–5 clusters | Web search latency dependent |
| Curation cycle | <5 minutes for ≤500 cards | File reading + reasoning |
| Card creation | <30 seconds for a single card | Direct file write |
| Gap analysis | <5 minutes for ≤500 cards | Full workspace read + reasoning |
| Graph status | <2 minutes for ≤500 cards | File counting + stats |

### Scalability Limit

The Claude-native approach is designed for **≤500 cards**. Beyond that:
- Reading all cards per operation becomes slow
- Claude's context window may not fit full workspace state
- The Python approach (SQLite + NetworkX) becomes the scaling path
- Both approaches share the workspace format — migration is seamless

### Mitigation for Scale

For larger workspaces:
- Skills can read directory listings before full file contents
- Domain-scoped operations (e.g., research for one domain) avoid full workspace reads
- The Python complement adds persistent indexing at v0.3

---

## 2. Reliability

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| Workspace integrity | Card files never corrupted by agent failure | Atomic file writes; cards are small individual files |
| Partial failure | One skill step failing doesn't corrupt workspace | Skills have independent steps |
| Rebuild guarantee | Workspace files are self-contained — no hidden state | No databases, no caches, no derived state that's required |
| Event log durability | `events.jsonl` is append-only | Never truncated or edited by skills |

### The "No Hidden State" Advantage

Unlike the Python approach, the Claude-native system has no derived state that can get out of sync:
- No SQLite index to rebuild
- No NetworkX graph to recompute
- No views/ directory to refresh
- Everything is in the files — if the files are correct, the system is correct

---

## 3. Security

| Requirement | Implementation |
|-------------|----------------|
| Local data | All workspace files stay on the user's machine |
| No secrets in workspace | API keys in Claude's environment, never in workspace files |
| No remote code execution | Agent skills only read/write files — no arbitrary code execution |
| Git-safe | No binary files, no large generated artifacts in workspace |

### Data Sent to Claude

When using CONSTRUCT through Claude, the following data is sent to Anthropic:
- Card content (during skill execution that reads cards)
- Workspace file contents (when skills read configs)
- Web search queries (during research cycles)

This is identical to any Claude conversation. Users control what's in their workspace. The `governance.yaml` and `model-routing.yaml` files are informational in the Claude-native approach — Claude handles all tasks.

---

## 4. Privacy

| Aspect | Policy |
|--------|--------|
| Knowledge graph | Local files. Sent to Claude only during active conversation. |
| Web search | Claude's web search — governed by Anthropic's privacy policy |
| Telemetry | None from CONSTRUCT. Claude's standard telemetry applies. |
| Third-party APIs | None. Web search replaces dedicated API clients. |

---

## 5. Portability

| Target | Status | Notes |
|--------|--------|-------|
| Any Claude surface (Code, Desktop, API) | ✅ | Config files are plain text |
| macOS / Linux / Windows | ✅ | No OS-specific dependencies |
| Other LLM providers | 🟡 | Skills are model-agnostic markdown; agent identity may need adaptation |

### LLM Portability

The configuration is markdown. Any sufficiently capable LLM with:
- File read/write tools
- Web search
- Strong reasoning

...could use these configurations. The skills don't reference Claude-specific APIs. However, the quality depends on frontier-level reasoning for synthesis, cross-domain ideation, and editorial judgment.

---

## 6. Observability

| Artifact | Format | Purpose |
|----------|--------|---------|
| `log/events.jsonl` | Append-only JSONL | Full audit trail |
| `digests/{domain}/` | Markdown | Research cycle reports |
| `graph-status` skill output | Conversation text | Health dashboard on demand |
| Git history | Standard | Version history of all workspace changes |

---

## 7. Accessibility

The interaction surface is Claude's conversation interface. Accessibility is governed by the Claude client (Claude Desktop, Claude Code, API consumer).

---

## 8. Internationalization

English only for v0.1. Knowledge cards can be in any language. Skills and agent prompts are English.

---

## 9. Backwards Compatibility

v0.1 is the first release. No backwards-compatibility obligations.

**Forward-compatibility commitment:** The workspace directory format is the long-term stable interface. Card schema changes will be versioned. Users' knowledge is sacred.

---

## 10. Licensing

Apache-2.0 — consistent with CONSTRUCT-spec/ and prior art.
