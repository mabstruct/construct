# Phase 8: Search Provider Spine + Contract Foundation - Pattern Map

**Mapped:** 2026-06-21
**Files analyzed:** 26 (18 create, 8 modify)
**Analogs found:** 24 / 26

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/construct/search/__init__.py` | config | — | `src/construct/llm/__init__.py` | exact |
| `src/construct/search/config.py` | config | file-I/O | `src/construct/llm/config.py` + `WorkspaceLoader.load_model_routing()` | role-match |
| `src/construct/search/errors.py` | utility | transform | `WorkspaceLoadError`, `ArtifactValidationError` | role-match |
| `src/construct/search/models.py` | model | transform | `schemas/config.py` (`SearchCluster`, `ReferenceRecord`) | exact |
| `src/construct/search/provider.py` | provider | request-response | `tests/llm/conftest.py` (`MockChatAnthropic`) | partial |
| `src/construct/search/providers/__init__.py` | config | — | `src/construct/pipelines/__init__.py` | exact |
| `src/construct/search/providers/tavily.py` | provider | request-response | `src/construct/llm/ask_domain.py` (external SDK boundary) | partial |
| `src/construct/search/providers/mock.py` | provider | file-I/O + transform | `tests/llm/conftest.py` (`MockChatAnthropic`) | role-match |
| `src/construct/search/registry.py` | service | transform | `src/construct/capabilities/registry.py` + `llm/config.py` factory | role-match |
| `src/construct/pipelines/research_search.py` | service | request-response | `src/construct/pipelines/graph_status.py` | exact |
| `CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml` | config | file-I/O | `templates/model-routing.yaml` | exact |
| `tests/search/conftest.py` | test | file-I/O | `tests/llm/conftest.py` + `tests/bridge/conftest.py` | exact |
| `tests/search/test_search_contract.py` | test | request-response | `tests/contract/test_mcp_contracts.py` + `test_cli_contracts.py` | exact |
| `tests/search/test_search_config.py` | test | file-I/O | `tests/unit/test_workspace_contracts.py` | exact |
| `tests/search/test_search_provider_mock.py` | test | transform | `tests/llm/test_ask_domain.py` | role-match |
| `tests/fixtures/search/*.json` | config | file-I/O | `CONSTRUCT-CLAUDE-impl/construct/templates/search-seeds.json` | role-match |
| `src/construct/schemas/config.py` | model | file-I/O | existing `ModelRoutingConfig`, `ProviderConfig` | exact |
| `src/construct/services/validation.py` | service | file-I/O | existing `load_model_routing()` block | exact |
| `src/construct/capabilities/catalog.py` | route | request-response | existing `ask.domain` / `bridge.detect` records | exact |
| `src/construct/cli.py` | controller | request-response | `ask_app` / `bridge_app` Typer groups | exact |
| `src/construct/storage/workspace.py` | service | file-I/O | `load_model_routing()` | exact |
| `src/construct/services/init.py` | service | file-I/O | `shutil.copy(model-routing.yaml)` | exact |
| `pyproject.toml` | config | — | existing `[project.optional-dependencies]` | exact |
| `tests/contract/test_mcp_contracts.py` | test | request-response | existing `expected` tool set + `_payload_for` | exact |

## Pattern Assignments

### `src/construct/search/__init__.py` (config)

**Analog:** `src/construct/llm/__init__.py`

**Module docstring pattern** (lines 1-2):

```python
"""LLM provider config and LangGraph gate infrastructure."""
from __future__ import annotations
```

Copy one-line package summary only; no re-exports required unless planner wants public API surface.

---

### `src/construct/search/config.py` (config, file-I/O)

**Analog:** `src/construct/llm/config.py` (project-level YAML loader) + `WorkspaceLoader.load_model_routing()` (workspace-scoped)

Phase 8 uses **workspace-only** config — mirror loader pattern, not `load_llm_config()` resolution order.

**Pydantic model conventions** from `llm/config.py` (lines 12-40):

```python
class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    model_config = {"extra": "forbid"}
    type: str = "langchain_anthropic"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    timeout_seconds: int = 60
    base_url: str | None = None

class LlmConfig(BaseModel):
    """Top-level LLM configuration loaded from YAML."""
    model_config = {"extra": "forbid"}
    version: int = 1
    default_gate: str = "ask.domain"
    providers: dict[str, ProviderConfig] = Field(default_factory=lambda: {
        "anthropic": ProviderConfig(),
    })
```

**Workspace YAML load + ValidationError wrap** from `workspace.py` (lines 94-98):

```python
def load_model_routing(self) -> ModelRoutingConfig:
    try:
        return ModelRoutingConfig.model_validate(self.read_yaml(".construct/model-routing.yaml"))
    except ValidationError as exc:
        raise WorkspaceLoadError(f"invalid .construct/model-routing.yaml: {exc}") from exc
```

Add `load_search_config()` beside this method reading `.construct/search.yaml` → `SearchConfig`.

**api_key_env validator** from `schemas/config.py` (lines 96-110):

```python
class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName
    model: str
    api_key_env: str | None = None

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not ENV_VAR_PATTERN.fullmatch(value):
            raise ValueError("api_key_env must be an environment variable name")
        return value
```

Reuse `ENV_VAR_PATTERN` for Tavily provider blocks.

---

### `src/construct/search/errors.py` (utility, transform)

**Analog:** `WorkspaceLoadError`, `ArtifactValidationError`, `WorkspaceInitError`

No search-specific hierarchy exists yet. Follow domain `ValueError` subclass pattern:

**Base domain error** from `workspace.py` (lines 33-34):

```python
class WorkspaceLoadError(ValueError):
    """Raised when a workspace file cannot be parsed into a schema."""
```

**Artifact validation error** from `validation.py` (lines 50-51):

```python
class ArtifactValidationError(ValueError):
    """Raised when a canonical artifact fails pre-write validation."""
```

**Init error** from `init.py` (lines 35-36):

```python
class WorkspaceInitError(ValueError):
    """Raised when workspace initialization cannot proceed safely."""
```

Implement `SearchError` base with `provider_name` and `message` fields; six subclasses (`NetworkError`, `RateLimitError` with `retry_after_seconds`, `AuthError`, `QuotaExceededError`, `ParseError`, `ProviderUnavailableError`). Chain with `raise NewError(...) from original_exc` per project conventions.

**Handler surfacing** — map to `OperationResult` like `graph_status.py` (lines 74-78):

```python
except (WorkspaceLoadError, OSError) as exc:
    return OperationResult(
        success=False,
        message=str(exc),
        errors=[OperationError(reason=str(exc))],
    )
```

---

### `src/construct/search/models.py` (model, transform)

**Analog:** `src/construct/schemas/config.py`

**Enum + kebab validator** from `SearchCluster` (lines 208-223):

```python
class SearchCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    domain: str
    terms: list[str] = Field(default_factory=list)
    weight: float = Field(ge=0.0, le=1.0)
    status: SearchClusterStatus
    last_queried: datetime | None = None

    @field_validator("id", "domain")
    @classmethod
    def validate_cluster_ids(cls, value: str) -> str:
        if not KEBAB_CASE_PATTERN.fullmatch(value):
            raise ValueError("value must be kebab-case, e.g. 'quantum-gravity'")
        return value
```

**SearchResult** — hybrid locked fields: `title`, `url`, `snippet`, `source_tier`, `score`, `provider_specific: dict[str, Any]` with `extra="forbid"` on core model; use a typed `provider_specific` field with default factory.

**SearchBatchOutput** — `results: list[SearchResult]`, `truncated: bool`, optional `errors` list for degraded batch.

**Capability I/O models** — define `ResearchSearchInput` / `ResearchSearchOutput` in catalog or pipeline module using `AskDomainInput` style from `ask_domain.py` (lines 66-74):

```python
class AskDomainInput(BaseModel):
    """Input for ask.domain grounded Q&A gate."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    domain_id: str
    question: str = Field(..., min_length=1)
    max_cards: int = Field(default=20, ge=1, le=50)
    provider_override: str | None = None
```

---

### `src/construct/search/provider.py` (provider, request-response)

**Analog:** `tests/llm/conftest.py` (`MockChatAnthropic`) — **no ABC exists in codebase**

First `ABC` in project. Mock class shows the **interface contract** pattern (lines 25-48):

```python
class MockChatAnthropic:
    """Simplified mock returning fixed structured output.

    Usage in tests:
        monkeypatch.setattr(
            "construct.llm.ask_domain.ChatAnthropic",
            lambda **kwargs: MockChatAnthropic(),
        )
    """
    def __init__(self, **kwargs: Any) -> None:
        self.model = kwargs.get("model", "claude-sonnet-4-20250514")
        self.temperature = kwargs.get("temperature", 0.2)

    def with_structured_output(self, model_class: Any, **kwargs: Any) -> "MockChatAnthropic":
        self._output_model = model_class
        return self

    def invoke(self, messages: list) -> MockSynthesisOutput:
        """Return a canned SynthesisOutput. Tests override via monkeypatch."""
        return MockSynthesisOutput(
            answer="Mock answer based on provided card context.",
            cited_card_ids=["card-1", "card-2"],
            confidence="high",
        )
```

Define `SearchProvider(ABC)` with four abstract methods: `search()`, `search_batch()`, `search_by_seed_cluster()`, `get_capabilities()`. All return Pydantic models from `models.py`, raise typed errors from `errors.py`.

---

### `src/construct/search/providers/mock.py` (provider, file-I/O + transform)

**Analog:** `tests/llm/conftest.py` — extend beyond static canned responses

**Configurable mock class** (lines 25-48 above) plus JSON fixture loading:

- Per-query fixture map from `tests/fixtures/search/*.json`
- Optional `latency_ms` sleep before return
- Optional `error` block with `type` → raise matching `SearchError` subclass
- Default provider in test workspaces (`default_provider: mock`)

**Workspace helper** from `conftest.py` (lines 54-65):

```python
def create_test_workspace(path: Path, domain_id: str = "test-domain") -> Path:
    """Initialize a minimal CONSTRUCT workspace for testing."""
    domain = DomainInitInput(
        domain_id=domain_id,
        display_name=domain_id.replace("-", " ").title(),
        scope=f"Test domain for {domain_id}.",
        taxonomy_seeds=["test-category"],
        source_priorities=["peer-reviewed papers"],
        research_seeds=["test research"],
    )
    initialize_workspace(path, domain)
    return path
```

Extend test workspace setup to copy/write `.construct/search.yaml` with `default_provider: mock` and `fixture_dir` pointing at `tests/fixtures/search`.

---

### `src/construct/search/providers/tavily.py` (provider, request-response)

**Analog:** `src/construct/llm/ask_domain.py` — external SDK isolated at boundary

**Lazy import guard:** only file that imports `tavily`. On missing optional dep, raise `ProviderUnavailableError` with install hint (`pip install -e '.[search]'`).

**SDK call + exception mapping** (from RESEARCH.md; implement at adapter boundary):

```python
from tavily import (
    TavilyClient,
    InvalidAPIKeyError,
    UsageLimitExceededError,
    TimeoutError as TavilyTimeoutError,
)

try:
    response = client.search(query, max_results=max_results, timeout=timeout)
except InvalidAPIKeyError as exc:
    raise AuthError(provider_name="tavily", message=str(exc)) from exc
except UsageLimitExceededError as exc:
    raise RateLimitError(provider_name="tavily", retry_after_seconds=getattr(exc, "retry_after_seconds", None)) from exc
except TavilyTimeoutError as exc:
    raise NetworkError(provider_name="tavily", message="timeout") from exc
```

**API key from env** — read `api_key_env` name from provider config block; never read literal keys from YAML.

**Normalization** — map Tavily `title`, `url`, `content` → `snippet`; `score` → `score`; stash extras in `provider_specific`; derive `source_domain` via `urllib.parse`.

---

### `src/construct/search/registry.py` (service, transform)

**Analog:** `CapabilityRegistry` factory pattern + `load_llm_config()`

**Registry singleton factory** from `catalog.py` (lines 161-162, 499-503):

```python
def create_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    registry.register(CapabilityRecord(
```

```python
_registry: CapabilityRegistry | None = None

def get_registry() -> CapabilityRegistry:
    global _registry
    if _registry is None:
        _registry = create_registry()
    return _registry
```

`SearchProviderFactory` should:
1. Accept `SearchConfig` + optional workspace `Path`
2. Resolve `default_provider` → instantiate `MockSearchProvider` or `TavilySearchProvider`
3. Enforce caps from `config.caps` before/after provider calls
4. Raise `ProviderUnavailableError` when provider type unknown or SDK missing

**Register lookup** from `registry.py` (lines 36-40):

```python
def get(self, cap_id: str) -> CapabilityRecord:
    if cap_id not in self._capabilities:
        available = ", ".join(sorted(self._capabilities))
        raise KeyError(f"Capability '{cap_id}' not found. Available: {available}")
    return self._capabilities[cap_id]
```

---

### `src/construct/pipelines/research_search.py` (service, request-response)

**Analog:** `src/construct/pipelines/graph_status.py`

**Read-only PIPE handler returning OperationResult** (lines 12-72):

```python
def graph_status(workspace: str | Path) -> OperationResult:
    try:
        root = Path(workspace)
        loader = WorkspaceLoader(root)

        card_total = 0
        lifecycle_counts: dict[str, int] = {}
        domain_card_counts: dict[str, int] = {}

        for card_path in loader.iter_cards():
            card_total += 1
            try:
                markdown = card_path.read_text(encoding="utf-8")
                card, _ = parse_card_markdown(markdown, source_path=card_path)
                lifecycle_counts[card.lifecycle.value] = lifecycle_counts.get(card.lifecycle.value, 0) + 1
                for domain in card.domains:
                    domain_card_counts[domain] = domain_card_counts.get(domain, 0) + 1
            except (SchemaParseError, OSError):
                lifecycle_counts["_unparseable"] = lifecycle_counts.get("_unparseable", 0) + 1

        data = {
            "cards": {
                "total": card_total,
                "by_lifecycle": lifecycle_counts,
                "by_domain": domain_card_counts,
            },
            ...
        }

        return OperationResult(
            success=True,
            message=f"Graph status for {root.name}",
            data=data,
        )
```

`research_search()` should:
- Load config via `loader.load_search_config()`
- Build provider via factory
- Dispatch query / batch / seed_cluster mode from input
- Return `OperationResult(success=True, data=output.model_dump(mode="json"))`
- Catch `SearchError` subclasses → structured `OperationResult` with `success=False`
- **No** calls to `ingest_source`, `append_event`, card/ref/seed write helpers

**Seed cluster read** — `loader.load_search_seeds()` (workspace.py lines 106-110):

```python
def load_search_seeds(self) -> SearchSeedsFile:
    try:
        return SearchSeedsFile.model_validate(self.read_json("search-seeds.json"))
    except ValidationError as exc:
        raise WorkspaceLoadError(f"invalid search-seeds.json: {exc}") from exc
```

---

### `src/construct/schemas/config.py` (model, file-I/O) — MODIFY

**Analog:** existing `ModelRoutingConfig`, `ProviderName`, `ProviderConfig`

Add `SearchProviderName` enum (`mock`, `tavily`) and `SearchConfig` with:
- `version: int`
- `default_provider: SearchProviderName`
- `providers: dict[str, ...]` (discriminated by `type` field)
- `caps: SearchCapsConfig` block

Follow `ModelRoutingConfig` structure (lines 121-147) for cross-field validation. Place workspace schema here (not in `search/config.py`) — `search/config.py` is runtime merge/helper only if needed.

---

### `src/construct/storage/workspace.py` (service, file-I/O) — MODIFY

**Analog:** `load_model_routing()` (lines 94-98)

Add `load_search_config()` immediately after `load_model_routing()` using identical try/except/`WorkspaceLoadError` pattern. Import `SearchConfig` from `schemas.config`.

---

### `src/construct/services/validation.py` (service, file-I/O) — MODIFY

**Analog:** model-routing validation block (lines 127-131)

```python
if loader.resolve(".construct/model-routing.yaml").exists():
    try:
        loader.load_model_routing()
    except WorkspaceLoadError as exc:
        report.add_error(".construct/model-routing.yaml", str(exc))
```

Add parallel block for `.construct/search.yaml`. Implement `validate_search_config()` if planner splits logic — mirror `validate_governance_write()` pattern (lines 85-89):

```python
def validate_governance_write(payload: object) -> GovernanceConfig:
    try:
        return GovernanceConfig.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc
```

Cross-validate seed clusters: reuse existing `search_cluster_ids` / `valid_domains` cross-check at lines 139-152.

---

### `src/construct/services/init.py` (service, file-I/O) — MODIFY

**Analog:** model-routing template copy (lines 58, 22)

```python
TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "CONSTRUCT-CLAUDE-impl" / "construct" / "templates"
```

```python
shutil.copy(TEMPLATE_DIR / "model-routing.yaml", workspace_root / ".construct" / "model-routing.yaml")
```

Add:

```python
shutil.copy(TEMPLATE_DIR / "search.yaml", workspace_root / ".construct" / "search.yaml")
```

Default template `default_provider: mock` per RESEARCH recommendation. Update `_write_workspace_doc()` support-paths bullet to mention `.construct/search.yaml`.

---

### `src/construct/capabilities/catalog.py` (route, request-response) — MODIFY

**Analog:** `ask.domain` + `bridge.detect` registrations + RT-03 shims

**Capability registration** (lines 321-336):

```python
registry.register(CapabilityRecord(
    id="ask.domain",
    name="Ask Domain",
    description="Grounded Q&A with citations over workspace knowledge cards for a domain",
    input_model=AskDomainInput,
    output_model=AskDomainOutput,
    handler=lambda **kwargs: (
        lambda result: OperationResult(
            success=result.answer is not None,
            message=result.answer or "No answer could be generated from available cards.",
            data=result.model_dump(mode="json"),
        )
    )(ask_domain_gate("ask.domain", AskDomainInput(**kwargs))),
    cli_name="ask.domain",
    mcp_tool_name="construct_ask_domain",
))
```

Register `research.search`:

```python
registry.register(CapabilityRecord(
    id="research.search",
    name="Research Search",
    description="Provider-agnostic web search returning normalized results (read-only)",
    input_model=ResearchSearchInput,
    output_model=OperationResult,
    handler=_research_search_shim,  # or research_search directly
    cli_name="research.search",
    mcp_tool_name="construct_research_search",
))
```

**RT-03 shim pattern** (lines 353-359):

```python
def _validate_shim(*args, **kwargs):
    """RT-03 adapter for workspace.validate. Accepts the MCP keyword form
    (``path=`` from WorkspacePathInput) and the CLI positional form
    (cli.py:88 calls ``handler(path)``)."""
    if args:
        return validate_workspace(args[0])
    return validate_workspace(kwargs["path"])
```

---

### `src/construct/cli.py` (controller, request-response) — MODIFY

**Analog:** `ask_app` / `bridge_app` Typer subgroups (lines 327-393)

```python
ask_app = typer.Typer(
    no_args_is_help=True,
    name="ask",
    help="Ask questions grounded in workspace knowledge.",
)
app.add_typer(ask_app)

@ask_app.command()
def domain(
    ctx: typer.Context,
    question: str = typer.Option(..., "--question", "-q", help="Your question about this domain"),
    domain_id: str = typer.Option(..., "--domain", "-d", help="Domain ID to query"),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", "-w"),
    max_cards: int = typer.Option(20, "--max-cards", help="Max cards to consider (1-50)"),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    try:
        cap = get_registry().get("ask.domain")
    except KeyError:
        typer.echo("ERROR: Capability 'ask.domain' not found. Ensure Phase 5 is complete.")
        raise typer.Exit(code=1)
    result = cap.handler(
        workspace_path=str(workspace),
        domain_id=domain_id,
        question=question,
        max_cards=max_cards,
    )
    _display_result(result, json_output)
```

Add `research_app` Typer group (`name="research"`) with `search` subcommand → `construct research search`. Use `get_registry().get("research.search")`, `_display_result(result, json_output)`.

**Result display** (lines 164-191):

```python
def _display_result(result: OperationResult, json_output: bool) -> None:
    """Render an OperationResult to stdout as either JSON or human-readable text."""
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "success": result.success,
                    "message": result.message,
                    "errors": [
                        {"field": e.field, "reason": e.reason, "suggestion": e.suggestion}
                        for e in result.errors
                    ],
                    "data": result.data,
                },
                indent=2,
            )
        )
```

---

### `src/construct/mcp/server.py` (route, request-response) — NO MODIFY

**Analog:** existing auto-exposure loop (lines 26-44)

```python
registry = get_registry()
for entry in registry.list_mcp_tools():
    cap = registry.get_by_mcp_name(entry["name"])

    def make_handler(capability=cap) -> Any:
        def handler(**kwargs: Any) -> str:
            try:
                result = capability.handler(**kwargs)
                serialized = _serialize_result(result)
                return json.dumps(serialized, indent=2)
            except Exception as exc:
                return json.dumps({"error": str(exc)})
        return handler

    app.add_tool(
        fn=make_handler(),
        name=entry["name"],
        description=entry["description"],
    )
```

Registering `mcp_tool_name="construct_research_search"` in catalog auto-exposes MCP — no server.py edit.

---

### `CONSTRUCT-CLAUDE-impl/construct/templates/search.yaml` (config, file-I/O)

**Analog:** `templates/model-routing.yaml`

Mirror structure: version, default provider, named provider blocks, caps section. Default `default_provider: mock`. Tavily block uses `api_key_env: TAVILY_API_KEY` (env name only, never literal secret). See RESEARCH.md recommended template YAML.

---

### `pyproject.toml` (config) — MODIFY

**Analog:** existing optional deps (lines 22-23):

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

Add:

```toml
search = ["tavily-python>=0.7,<1"]
```

---

### `tests/search/conftest.py` (test, file-I/O)

**Analog:** `tests/llm/conftest.py` + `tests/bridge/conftest.py`

**Workspace + mock fixtures** (llm conftest lines 54-65, 104-113):

```python
@pytest.fixture
def test_workspace(tmp_path: Path) -> Path:
    """Create a fresh test workspace with sample cards."""
    ws = tmp_path / "workspace"
    create_test_workspace(ws)
    write_card(ws, "card-1", title="Test Card One", body="Content about testing methods and approaches.")
    ...
    return ws
```

Add:
- `search_workspace` fixture with `.construct/search.yaml` (`default_provider: mock`, `fixture_dir`)
- `mock_search_fixtures_dir` → `tests/fixtures/search`
- Reuse `create_test_workspace` from `tests.llm.conftest`

**Bridge conftest JSON write** (lines 15-25) for optional custom search-seeds overrides.

---

### `tests/search/test_search_contract.py` (test, request-response)

**Analog:** `tests/contract/test_mcp_contracts.py` + `tests/contract/test_cli_contracts.py`

**MCP tool count** (lines 53-70):

```python
def test_mcp_tool_count() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    tool_names = {t["name"] for t in mcp_tools}
    expected = {
        "construct_validate",
        ...
        "construct_bridge_detect",
    }
    assert tool_names == expected
```

Add `construct_research_search` to `expected` set and `_payload_for` dict.

**Handler invocation** (lines 86-118):

```python
def _payload_for(tool_name: str, ws: str) -> dict:
  payloads: dict[str, dict] = {
      "construct_validate": {"path": ws},
      ...
  }
  return payloads[tool_name]
```

**CLI contract** from `test_cli_contracts.py` (lines 17-21):

```python
def test_validate_passes_on_my_construct() -> None:
    ws = _ws("my-construct")
    result = runner.invoke(app, ["validate", str(ws)])
    assert result.exit_code == 0
    assert "0 error" in result.output
```

Test `construct research search --workspace ... --query "quantum gravity" --json`.

Assert normalized `SearchResult` fields; assert no SOT file mutation (refs/cards/seeds/events unchanged).

---

### `tests/search/test_search_config.py` (test, file-I/O)

**Analog:** `tests/unit/test_workspace_contracts.py` (lines 70-93)

```python
def test_template_backed_files_round_trip_through_updated_models_and_loader(workspace_path: Path) -> None:
    workspace = _write_canonical_workspace(workspace_path)
    ...
    routing_model = ModelRoutingConfig.model_validate(
        yaml.load((workspace / ".construct" / "model-routing.yaml").read_text())
    )
    loader = WorkspaceLoader(workspace)
    assert loader.load_model_routing().providers.frontier.provider.value == "anthropic"
```

Add `search.yaml` to `_write_canonical_workspace`; test `loader.load_search_config()` and `validate_workspace` with invalid search config.

---

### `tests/search/test_search_provider_mock.py` (test, transform)

**Analog:** `tests/llm/test_ask_domain.py`

**Monkeypatch mock provider** (lines 54-62):

```python
@pytest.fixture
def patched_llm(monkeypatch: pytest.MonkeyPatch) -> MockChatAnthropic:
    """Replace ChatAnthropic with mock for unit tests."""
    mock = MockChatAnthropic()
    monkeypatch.setattr(
        "construct.llm.ask_domain.ChatAnthropic",
        lambda **kwargs: mock,
    )
    return mock
```

Test each error injection fixture (`RateLimitError`, `NetworkError`, `AuthError`, etc.), result cap truncation (`truncated=True`), and latency simulation. No network; no Tavily import.

---

### `tests/fixtures/search/*.json` (config, file-I/O)

**Analog:** fixture JSON structure from RESEARCH.md + `search-seeds.json` template

Per-query entries with `query`, `latency_ms`, `response.results[]` or `error.type` + metadata. Files: `mock_happy_path.json`, `mock_rate_limit.json`, `tavily_basic.json` (sample response shape for normalization tests).

---

## Shared Patterns

### Workspace YAML → Pydantic → Loader
**Source:** `WorkspaceLoader.load_model_routing()` + `schemas/config.py`
**Apply to:** `storage/workspace.py`, `schemas/config.py`, `validation.py`, `search/config.py`

```python
def load_model_routing(self) -> ModelRoutingConfig:
    try:
        return ModelRoutingConfig.model_validate(self.read_yaml(".construct/model-routing.yaml"))
    except ValidationError as exc:
        raise WorkspaceLoadError(f"invalid .construct/model-routing.yaml: {exc}") from exc
```

### Capability Registry (CLI + MCP parity)
**Source:** `capabilities/catalog.py` + `capabilities/registry.py`
**Apply to:** `catalog.py`, `cli.py`, contract tests

- Register `CapabilityRecord` with `input_model`, `output_model`, `handler`, `cli_name`, `mcp_tool_name`
- RT-03 shim when CLI positional vs MCP kwargs differ
- MCP auto-exposed via `mcp_tool_name` — no `server.py` edit

### OperationResult response envelope
**Source:** `services/knowledge.py` + `cli.py::_display_result`
**Apply to:** `research_search.py`, catalog handler, CLI command

```python
@dataclass
class OperationResult:
    success: bool = True
    message: str = ""
    errors: list[OperationError] = field(default_factory=list)
    data: Any = None
```

### Template copy on init
**Source:** `services/init.py`
**Apply to:** `init.py`, `templates/search.yaml`

```python
shutil.copy(TEMPLATE_DIR / "model-routing.yaml", workspace_root / ".construct" / "model-routing.yaml")
```

### Mock provider for offline tests
**Source:** `tests/llm/conftest.py`
**Apply to:** `providers/mock.py`, `tests/search/conftest.py`, all contract tests

Replace external dependency with configurable fixture class; monkeypatch or default `mock` provider in test workspaces.

### Pydantic v2 model conventions
**Source:** `schemas/config.py`
**Apply to:** all new models in `search/models.py`, `schemas/config.py`

- `model_config = ConfigDict(extra="forbid")`
- `Field(ge=..., le=...)`, `Field(default_factory=list)`
- `@field_validator` + `@classmethod` with human-readable `ValueError` messages
- Enums inherit `(str, Enum)`

### Optional dependency isolation
**Source:** `pyproject.toml` + Tavily adapter boundary
**Apply to:** `pyproject.toml`, `providers/tavily.py`, `registry.py`

Tavily SDK only in `providers/tavily.py`; lazy import; `ProviderUnavailableError` when `[search]` extra not installed.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/construct/search/provider.py` | provider | request-response | First `ABC` in codebase — no abstract base class precedent; use RESEARCH.md 4-method interface + MockChatAnthropic as behavioral contract |
| `src/construct/search/providers/tavily.py` | provider | request-response | First external search SDK adapter — map exceptions per Tavily docs at implementation time; no in-repo HTTP/SDK adapter analog |

## Metadata

**Analog search scope:** `src/construct/llm/`, `src/construct/capabilities/`, `src/construct/pipelines/`, `src/construct/schemas/`, `src/construct/services/`, `src/construct/storage/`, `src/construct/mcp/`, `src/construct/cli.py`, `tests/llm/`, `tests/bridge/`, `tests/contract/`, `tests/unit/`, `CONSTRUCT-CLAUDE-impl/construct/templates/`
**Files scanned:** ~35
**Pattern extraction date:** 2026-06-21

## PATTERN MAPPING COMPLETE

**Phase:** 8 - Search Provider Spine + Contract Foundation
**Files classified:** 26
**Analogs found:** 24 / 26

### Coverage
- Files with exact analog: 16
- Files with role-match analog: 8
- Files with no analog: 2 (`provider.py` ABC, `tavily.py` SDK adapter)

### Key Patterns Identified
- Workspace config follows `load_model_routing()` YAML → Pydantic → `WorkspaceLoadError` chain; search config is workspace-only at `.construct/search.yaml`
- `research.search` registers via `CapabilityRecord` with RT-03 shim; MCP tool `construct_research_search`; CLI subgroup `construct research search`
- PIPE handlers return `OperationResult` read-only like `graph_status.py` — no ingest/event/seed writes in Phase 8
- Mock provider extends `MockChatAnthropic` with JSON fixtures, latency, and error injection; default CI uses `mock` provider
- Tavily SDK isolated in one file behind optional `[search]` extra; six granular `SearchError` subclasses surfaced through `OperationResult`

### File Created
`.planning/phases/08-search-provider-spine-contract-foundation/08-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
