# CONSTRUCT — Test Strategy

**Version:** 0.1.0
**Date:** 2026-04-19
**Status:** Draft

---

## 1. Principles

1. **Tests ship with code.** No PR merges without tests for new functionality.
2. **Agent-written code is especially suspect.** Tests are the safety net against LLM-generated drift.
3. **Fast feedback loop.** `pytest` + `vitest` must complete in <30s locally for the full suite.
4. **Schema tests are the highest-value tests.** They enforce the contract between agents, core, and UI.

---

## 2. Test Layers

### 2.1 Python (pytest)

| Layer | Scope | Location | Runs in CI | Coverage target |
|-------|-------|----------|-----------|----------------|
| **Unit** | Individual functions: graph queries, card parsing, schema validation, views rendering | `tests/unit/` | ✅ | ≥80% on `src/construct/graph/`, `src/construct/storage/` |
| **Integration** | Multi-component flows: card → index → views, research ingest → card creation | `tests/integration/` | ✅ | Key flows covered, not % driven |
| **Contract** | Schema validation: every `views/*.json`, `inbox/*.json`, `log/events.jsonl` entry validates against JSON Schema | `tests/contract/` | ✅ | 100% of schemas |
| **CLI** | `construct init`, `construct status`, `construct views` produce expected output | `tests/cli/` | ✅ | All commands |

### 2.2 TypeScript / React (vitest)

| Layer | Scope | Location | Runs in CI |
|-------|-------|----------|-----------|
| **Component** | React components render correctly given `views/*.json` input | `ui/src/__tests__/` | ✅ |
| **Integration** | Pages load, route correctly, handle empty/loading/error states | `ui/src/__tests__/` | ✅ |

### 2.3 E2E (deferred to v0.2)

Playwright tests exercising the full loop: `construct init` → card creation → `views/` → React UI renders card. Deferred because the WebSocket chat interface needs to stabilize first.

---

## 3. Fixtures

A minimal demo domain ships in `tests/fixtures/`:

```
tests/fixtures/
├── workspace/                    # A tiny but complete workspace
│   ├── cards/                    # Knowledge cards (flat workspace layout)
│   │   ├── concept-neural-scaling.md
│   │   ├── paper-chinchilla.md
│   │   ├── claim-scaling-laws.md
│   │   ├── gap-multimodal-scaling.md
│   │   └── connection-scaling-to-efficiency.md
│   ├── connections.json           # 5 cards, 4 typed edges
│   ├── refs/                      # Reference library
│   ├── domains.yaml               # One domain: "ml-scaling"
│   ├── model-routing.yaml         # All routes → "mock" provider
│   ├── governance.yaml
│   ├── search-seeds.json          # Research search patterns
│   ├── inbox/                     # Pending actions
│   ├── log/
│   │   └── events.jsonl           # 10 sample events
│   ├── digests/                   # Research cycle digests
├── expected_views/                    # Pre-rendered expected output
│   ├── graph.json
│   ├── cards/
│   ├── landscape.json
│   ├── agents-status.json
│   └── events-recent.json
└── schemas/                       # JSON Schema files for validation
    ├── card-frontmatter.schema.json
    ├── connections.schema.json
    ├── graph.schema.json
    ├── event.schema.json
    ├── inbox-action.schema.json
    └── views-response.schema.json
```

This fixture exercises: 5 card types, 4 connection types, all `views/` outputs, 1 domain. It is the **integration test harness** and the **schema contract test baseline**.

---

## 4. LLM Mocking

Tests must run without API keys or Ollama.

| Strategy | Where used |
|----------|-----------|
| **Mock LLM client** | Returns canned responses for known prompts. Used in integration tests. |
| **`model-routing.yaml` → "mock" provider** | The fixture workspace routes all tasks to a mock provider that returns deterministic output. |
| **No LLM unit tests** | Unit tests cover pure logic (graph queries, schema validation, views rendering). They never call an LLM. |
| **Live LLM tests (optional)** | Marked `@pytest.mark.live_llm`. Skipped by default. Run manually: `pytest -m live_llm`. Require API key in env. Not in CI. |

---

## 5. CI Pipeline

GitHub Actions, triggered on PR to `main`:

```yaml
name: CI
on:
  pull_request:
    branches: [main]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/
      - run: mypy src/construct/
      - run: pytest tests/ -v --tb=short

  ui:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd ui && npm ci
      - run: cd ui && npx tsc --noEmit
      - run: cd ui && npx eslint src/
      - run: cd ui && npx vitest run
      - run: cd ui && npx vite build
```

**Gate:** Both jobs must pass before PR can merge.

---

## 6. Pre-commit Hooks (optional but recommended)

```bash
# .pre-commit-config.yaml or scripts/pre-commit.sh
ruff check src/ tests/
ruff format --check src/ tests/
pytest tests/unit/ tests/contract/ -q
```

Fast subset only — full suite runs in CI.

---

## 7. Coverage

| Target | Tool | Threshold |
|--------|------|-----------|
| Python overall | pytest-cov | ≥70% (informational, not gating) |
| `src/construct/graph/` | pytest-cov | ≥80% (gating) |
| `src/construct/storage/` | pytest-cov | ≥80% (gating) |
| Contract tests | manual count | 100% of schemas have validation tests |
| React components | vitest coverage | ≥60% (informational) |

Coverage is a signal, not a religion. High coverage on graph + storage + schemas matters. Low coverage on glue code is acceptable.
