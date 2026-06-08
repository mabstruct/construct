# Testing Patterns

**Analysis Date:** 2026-06-08

---

CONSTRUCT has two distinct testing paradigms:

1. **Python runtime** (`tests/`) — pytest with real filesystem, no mocking
2. **Claude-native agent system** (`CONSTRUCT-CLAUDE-spec/validation-strategy.md`) — workspace auditing as the equivalent of CI

---

## Test Framework (Python)

**Runner:**
- pytest ≥ 8.0
- Config: `pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in assertions (no external assertion library)

**CLI Testing:**
- `typer.testing.CliRunner` for CLI integration tests

**Run Commands:**
```bash
# Install deps first
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_schema_contracts.py

# Run specific test
pytest tests/unit/test_schema_contracts.py::test_valid_markdown_card_validates_against_filename

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

**Coverage:**
- Not configured in `pyproject.toml` (no `pytest-cov` in dependencies)
- No coverage threshold enforced

---

## Test File Organization

**Location:**
- Separate `tests/` directory (not co-located with source)
- `tests/unit/` — schema contracts, service logic, bootstrap checks
- `tests/integration/` — CLI end-to-end tests via `typer.testing.CliRunner`

**Naming:**
- Test files: `test_{module_or_concern}.py`
- Test functions: `test_{what_is_being_tested}_{expected_outcome}`

**Structure:**
```
tests/
├── conftest.py                     # Shared fixtures (workspace_path, cli_runner)
├── fixtures/
│   ├── expected-workspace-tree.txt # Golden file for workspace scaffold test
│   ├── invalid/
│   │   ├── domains-missing-path.yaml
│   │   └── invalid-card-no-summary.md
│   └── v02/                        # Claude-native workspace test fixtures
│       ├── adversarial-corrupt/
│       ├── empty/
│       ├── multi-domain-medium/
│       └── single-domain-small/
├── unit/
│   ├── test_bootstrap.py           # Package version, CLI exports, pyproject contract
│   ├── test_schema_contracts.py    # Pydantic model validation, round-trips
│   └── test_validation_service.py  # validate_workspace() service tests
└── integration/
    └── test_init_cli.py            # CLI commands: init, validate, status
```

---

## Test Structure

**Shared Fixtures** (`tests/conftest.py`):
```python
@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path / "workspace"

@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
```

**Private helper functions** for test setup (not fixtures) — prefixed with `_`:
```python
def _write_valid_workspace(root: Path) -> Path:
    """Builds a minimal valid workspace in tmp_path for service tests."""
    (root / "cards").mkdir(parents=True)
    # ...copies templates, writes fixture files...
    return root
```

**Type annotations:** All test functions annotated with `-> None`.

**Test isolation:**
- Each test receives a fresh `tmp_path` from pytest
- No shared mutable state between tests
- CLI tests use `CliRunner` which isolates stdin/stdout

---

## Mocking

**Framework:** None — no mocking library used (no `unittest.mock`, no `pytest-mock`).

**Strategy:** The codebase avoids mocks entirely. Instead:
- File system operations are tested against real temporary directories (`tmp_path`)
- CLI tests use `typer.testing.CliRunner` (provides isolated stdin/stdout without mocking)
- YAML/JSON parsing tested against real inline strings or copied template files
- No network calls in the Python layer (network isolation is natural)

**What is never mocked:**
- File system reads/writes — always use `tmp_path`
- YAML parsing — use real YAML strings
- Pydantic model validation — validate against real dicts

---

## Fixtures and Factories

**Template files** (not test fixtures — these are production templates used in tests):
- Location: `CONSTRUCT-CLAUDE-impl/construct/templates/` (resolved via `Path(__file__).resolve().parents[N] / "templates"`)
- Used in round-trip tests to verify templates parse correctly

**Static fixtures** (`tests/fixtures/`):
- `expected-workspace-tree.txt` — golden file for scaffold structure assertion
- `invalid/invalid-card-no-summary.md` — card file missing `## Summary` section
- `invalid/domains-missing-path.yaml` — malformed domains registry

**Inline test data:** Preferred for single-test scenarios. Long YAML/markdown strings written directly in test bodies:
```python
def test_valid_markdown_card_validates_against_filename() -> None:
    markdown = """---
id: successor-representation-spatial
title: Successor Representation for Spatial Reasoning
...
---

## Summary

Valid card body.
"""
    card, body = parse_card_markdown(markdown, source_path="cards/successor-representation-spatial.md")
```

**Module-level path constants** for resolving fixture directories:
```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "workspace"
INVALID_DIR  = PROJECT_ROOT / "tests" / "fixtures" / "invalid"
```

---

## Error Testing

**Pydantic ValidationError:**
```python
with pytest.raises(ValidationError) as exc_info:
    parse_card_markdown(markdown, source_path="cards/not-kebab.md")

message = str(exc_info.value)
assert "epistemic_type" in message
assert "id" in message
```

**Custom domain errors:**
```python
with pytest.raises(SchemaParseError, match="invalid YAML frontmatter"):
    parse_card_markdown(markdown, source_path="cards/bad-card.md")
```

**CLI exit codes:**
```python
result = runner.invoke(app, ["validate", str(workspace)])

assert result.exit_code == 1
assert "ERROR domains/example-domain/domain.yaml" in result.stdout
```

---

## Test Types

**Unit Tests** (`tests/unit/`):
- **Scope:** Individual Pydantic models, schema parsing functions, package exports
- **Approach:** Pass valid/invalid data directly to `Model.model_validate(...)` or `parse_card_markdown(...)`. No file system needed.
- **Files:** `test_schema_contracts.py`, `test_bootstrap.py`

**Integration Tests** (`tests/integration/`):
- **Scope:** Full CLI commands (`init`, `validate`, `status`) + service layer (`validate_workspace`)
- **Approach:** Build real workspace directory in `tmp_path`, invoke CLI or service, assert on resulting files and output
- **Files:** `test_init_cli.py`, `test_validation_service.py`

**E2E Tests:**
- Not automated via pytest. Covered by Claude-native validation strategy (see below).

---

## CLI Integration Test Pattern

```python
def test_construct_init_creates_full_workspace_scaffold(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"
    expected_tree = sorted(
        line for line in (FIXTURES_DIR / "expected-workspace-tree.txt").read_text().splitlines()
        if line
    )

    result = runner.invoke(
        app,
        ["init", str(workspace)],
        input="example-domain\nExample Domain\nExample scope\nexamples,notes\npeer-reviewed papers\nexample seed\n",
    )

    assert result.exit_code == 0, result.stdout
    assert _tree(workspace) == expected_tree
    assert "Initialized CONSTRUCT workspace" in result.stdout
```

Key pattern: pass multi-line `input=` string to simulate interactive prompts. Assert `exit_code == 0, result.stdout` to get helpful output on failure.

---

## Claude-Native Validation Strategy

The Claude-native agent system (`CONSTRUCT-CLAUDE-impl/`) has no code to unit-test. Its correctness is verified through **workspace auditing**, defined in `CONSTRUCT-CLAUDE-spec/validation-strategy.md`.

### 5-Layer Validation Model

| Layer | What it checks | When |
|-------|---------------|------|
| **Layer 1: Schema** | Files conform to YAML/JSON schemas (required fields, valid enums, valid ranges) | After every write operation, during `construct-workspace-validate` skill |
| **Layer 2: Governance** | Promotion thresholds, decay windows, relevance thresholds from `governance.yaml` respected | During `construct-curation-cycle` |
| **Layer 3: Consistency** | Cross-file references valid (card domains exist, connection targets exist, etc.) | During `construct-curation-cycle` Step 1 (integrity check) |
| **Layer 4: Functional** | User journeys J1 (Cold Start), J2 (Daily Use), J3 (Co-authorship) execute end-to-end | Manual validation against `user-journeys.md` |
| **Layer 5: Audit Trail** | `events.jsonl` contains expected events for all write operations | Post-operation review |

### Validation Embedded in Skills

Every SKILL.md ends with a `### Validation` checklist section. Skills validate output **before writing** and cross-references **after writing**. This is the Claude-native equivalent of unit tests preventing bad code.

### Equivalence to Python Tests

| Python approach | Claude-native equivalent |
|----------------|-------------------------|
| Unit tests (`test_schema_contracts.py`) | Schema validation steps in each SKILL.md |
| Integration tests (`test_init_cli.py`) | Full workflow execution (cold-start, daily-cycle) |
| Contract tests | Validation steps embedded in each skill |
| CI pipeline | Manual `construct-workspace-validate` skill invocation |
| Test fixtures (`tests/fixtures/v02/`) | Test workspace fixtures (`test-ws/my-construct/`, `test-ws/ping-eon/`) |

### Test Workspaces

**`test-ws/my-construct/`** — primary fixture workspace (cosmology, philosophy-of-mind, philosophy-of-physics domains, generated `views/`). Use for exercising skills, workflows, and views against realistic workspace state.

**`test-ws/ping-eon/`** — smaller fixture (api-gateways domain). Use for lightweight skill testing.

---

## Common Patterns

**Round-trip validation:**
```python
def test_default_templates_round_trip_through_models() -> None:
    yaml = YAML(typ="safe")
    domains = yaml.load((FIXTURES / "domains.yaml").read_text())
    domains_model = DomainsRegistry.model_validate(domains)
    assert domains_model.domains["example-domain"].path == "domains/example-domain/domain.yaml"
```

**Checking warning vs. error severity:**
```python
report = validate_workspace(workspace)
assert report.errors == []
assert len(report.warnings) == 1
assert report.by_file["cards/invalid-card-no-summary.md"][0].severity == "warning"
```

**Asserting file output from CLI:**
```python
domains_yaml = (workspace / "domains.yaml").read_text()
assert "domains/example-domain/domain.yaml" in domains_yaml
```

**Golden file tree comparison:**
```python
def _tree(root: Path) -> list[str]:
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{relative}/" if path.is_dir() else relative)
    return sorted(entries)

assert _tree(workspace) == expected_tree  # compare to tests/fixtures/expected-workspace-tree.txt
```

---

*Testing analysis: 2026-06-08*
