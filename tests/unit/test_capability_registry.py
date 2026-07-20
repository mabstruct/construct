"""Unit tests for capability registry and catalog."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from construct.capabilities.registry import CapabilityRecord, CapabilityRegistry
from construct.capabilities.catalog import ViewsGenerateDataInput, get_registry


class TestInput(BaseModel):
    name: str


class TestOutput(BaseModel):
    result: str


def _sample_handler(**kwargs: object) -> dict:
    return {"handled": True, **kwargs}


def test_register_and_get() -> None:
    registry = CapabilityRegistry()
    record = CapabilityRecord(
        id="test.cap",
        name="Test Capability",
        description="A test capability",
        input_model=TestInput,
        output_model=TestOutput,
        handler=_sample_handler,
    )
    registry.register(record)
    retrieved = registry.get("test.cap")
    assert retrieved.id == "test.cap"
    assert retrieved.name == "Test Capability"
    assert retrieved.description == "A test capability"
    assert retrieved.input_model is TestInput
    assert retrieved.output_model is TestOutput
    assert retrieved.handler is _sample_handler


def test_register_duplicate_raises() -> None:
    registry = CapabilityRegistry()
    registry.register(CapabilityRecord(
        id="dup", name="First", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler,
    ))
    try:
        registry.register(CapabilityRecord(
            id="dup", name="Second", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler,
        ))
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "dup" in str(exc)


def test_get_unknown_raises() -> None:
    registry = CapabilityRegistry()
    try:
        registry.get("does.not.exist")
        assert False, "Expected KeyError"
    except KeyError as exc:
        assert "does.not.exist" in str(exc)


def test_list_sorted() -> None:
    registry = CapabilityRegistry()
    registry.register(CapabilityRecord(
        id="z.last", name="Z", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler,
    ))
    registry.register(CapabilityRecord(
        id="a.first", name="A", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler,
    ))
    registry.register(CapabilityRecord(
        id="m.middle", name="M", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler,
    ))
    ids = [c.id for c in registry.list()]
    assert ids == ["a.first", "m.middle", "z.last"]


def test_list_mcp_tools() -> None:
    registry = CapabilityRegistry()
    registry.register(CapabilityRecord(
        id="has.mcp", name="Has MCP", description="Has MCP tool", input_model=TestInput, output_model=TestOutput, handler=_sample_handler, mcp_tool_name="has_mcp",
    ))
    registry.register(CapabilityRecord(
        id="no.mcp", name="No MCP", description="No MCP tool", input_model=TestInput, output_model=TestOutput, handler=_sample_handler,
    ))
    tools = registry.list_mcp_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "has_mcp"
    assert tools[0]["description"] == "Has MCP tool"


def test_mcp_tool_schema() -> None:
    registry = CapabilityRegistry()
    registry.register(CapabilityRecord(
        id="schema.test", name="Schema Test", description="Schema test", input_model=TestInput, output_model=TestOutput, handler=_sample_handler, mcp_tool_name="schema_test",
    ))
    tools = registry.list_mcp_tools()
    assert len(tools) == 1
    schema = tools[0]["input_schema"]
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
    assert schema["properties"]["name"]["type"] == "string"


def test_catalog_loads() -> None:
    registry = get_registry()
    assert len(registry) >= 15
    expected_ids = {
        "workspace.init",
        "workspace.validate",
        "workspace.status",
        "knowledge.card.create",
        "knowledge.card.edit",
        "knowledge.card.archive",
        "knowledge.connection.add",
        "knowledge.connection.remove",
        "knowledge.connection.list",
        "knowledge.card.list",
        "graph.status",
        "views.generate_data",
        "workflow.status",
        "ingest.source",
        "help.suggest",
        "ask.domain",
        "bridge.detect",
        "research.search",
        "research.score",
        "research.run",
        "research.review",
        "research.inspect",
        "curation.run",
        "curation.inspect",
        "curation.review",
        "card.evaluate",
        "daily.run",
        "daily.inspect",
    }
    actual_ids = {c.id for c in registry.list()}
    assert actual_ids == expected_ids


def test_get_by_mcp_name() -> None:
    registry = CapabilityRegistry()
    registry.register(CapabilityRecord(
        id="mcp.lookup", name="MCP Lookup", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler, mcp_tool_name="mcp_lookup_test",
    ))
    cap = registry.get_by_mcp_name("mcp_lookup_test")
    assert cap.id == "mcp.lookup"
    try:
        registry.get_by_mcp_name("non_existent")
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_list_by_cli() -> None:
    registry = CapabilityRegistry()
    registry.register(CapabilityRecord(
        id="cli.one", name="CLI One", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler, cli_name="mygroup",
    ))
    registry.register(CapabilityRecord(
        id="cli.two", name="CLI Two", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler, cli_name="mygroup",
    ))
    registry.register(CapabilityRecord(
        id="cli.other", name="CLI Other", description="", input_model=TestInput, output_model=TestOutput, handler=_sample_handler, cli_name="othergroup",
    ))
    grouped = registry.list_by_cli("mygroup")
    assert len(grouped) == 2


# ---------------------------------------------------------------------------
# views.generate_data — V41-01 / FIX-01 (D-01, D-05)
# ---------------------------------------------------------------------------


def _scaffolded_install_root(tmp_path: Path) -> Path:
    """A freshly scaffolded install root containing one workspace.

    Mirrors ``tests/integration/conftest.py::scaffolded_install_root``. It is
    re-declared rather than imported because that fixture lives under a
    different test package's conftest and is not visible here.
    """
    from construct.services.init import DomainInitInput, initialize_workspace

    root = tmp_path / "install"
    root.mkdir()
    # The install-root marker the handler guards on (CR-03).
    (root / "AGENTS.md").write_text("# CONSTRUCT test install root\n", encoding="utf-8")
    initialize_workspace(
        root / "demo",
        DomainInitInput(
            domain_id="demo",
            display_name="Demo",
            scope="test scope",
            taxonomy_seeds=["t1"],
            source_priorities=["arxiv"],
            research_seeds=["seed one"],
        ),
    )
    return root


def test_views_generate_data_handler_is_not_a_permanent_failure(tmp_path: Path) -> None:
    """The registry handler runs the real generator and can report success."""
    root = _scaffolded_install_root(tmp_path)
    cap = get_registry().get("views.generate_data")

    # Keyword form — how ViewsGenerateDataInput / MCP callers invoke it.
    by_keyword = cap.handler(install_root=root)
    assert by_keyword.success is True, (by_keyword.message, by_keyword.errors)
    assert by_keyword.errors == [], by_keyword.errors

    # Positional form — how the in-process callers invoke it (graph.status precedent).
    by_position = cap.handler(root)
    assert by_position.success is True, (by_position.message, by_position.errors)
    assert by_position.errors == []


def _guarded_root(tmp_path: Path, name: str = "install") -> Path:
    """A directory that passes the CR-03 install-root guard but holds no workspaces.

    Used by the tests that monkeypatch ``generate`` — the guard runs first, so a
    bare non-existent path would never reach the code under test.
    """
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# CONSTRUCT test install root\n", encoding="utf-8")
    return root


def test_views_generate_handler_rejects_a_non_install_root(tmp_path: Path) -> None:
    """CR-03: the MCP-reachable handler must not scaffold into an arbitrary path.

    ``install_root`` is agent-supplied over MCP and generate() creates
    ``views/build/data/`` under whatever it is handed, so the AGENTS.md guard has
    to sit at the entrypoint rather than only in ``generate.main()``.
    """
    stranger = tmp_path / "somebody-elses-directory"
    stranger.mkdir()

    result = get_registry().get("views.generate_data").handler(install_root=stranger)

    assert result.success is False
    assert "AGENTS.md" in result.message
    assert not (stranger / "views").exists(), (
        "the handler created a views tree in a directory that is not an install root"
    )


def test_views_generate_handler_never_raises_and_never_leaks(tmp_path: Path, monkeypatch) -> None:
    """CR-02: a raising generator must become an OperationResult, not a traceback.

    Every sibling shim in ``catalog.py`` exists to keep raw exception text — which
    carries filesystem paths — out of the MCP error channel and out of the CLI.
    The views handler was the only one calling straight through.
    """
    import construct.views.generate as gen_mod

    secret = _guarded_root(tmp_path, "leaky-install-root-name")

    def _boom(install_root):
        raise FileNotFoundError(f"No such file or directory: {secret}")

    monkeypatch.setattr(gen_mod, "generate", _boom)

    result = get_registry().get("views.generate_data").handler(install_root=secret)

    assert result.success is False
    assert "FileNotFoundError" in result.message
    rendered = result.message + " ".join(e.reason for e in result.errors)
    assert str(secret) not in rendered, f"handler leaked a filesystem path: {rendered}"


def test_views_generate_data_input_declares_install_root() -> None:
    """D-05: the contract names the install root, which is what generate() takes."""
    fields = set(ViewsGenerateDataInput.model_fields)
    assert "install_root" in fields
    assert "workspace" not in fields


def test_views_generate_validation_errors_are_fatal_and_surfaced(tmp_path: Path, monkeypatch) -> None:
    """D-04: validation errors make the result a failure and reach `errors`."""
    import construct.views.generate as gen_mod
    from construct.views.generate import GenerateReport

    def _fake_generate(install_root):
        return GenerateReport(
            success=False,
            build_id="b-err",
            validation_errors=["cards.json: bad field", "domains.json: bad field"],
            warnings=[],
            total_files_written=3,
        )

    monkeypatch.setattr(gen_mod, "generate", _fake_generate)
    result = get_registry().get("views.generate_data").handler(
        install_root=_guarded_root(tmp_path)
    )

    assert result.success is False
    reasons = [e.reason for e in result.errors]
    assert reasons == ["cards.json: bad field", "domains.json: bad field"]
    assert "2 validation errors" in result.message


def test_views_generate_warnings_alone_are_advisory(tmp_path: Path, monkeypatch) -> None:
    """D-04: content warnings never make the result a failure."""
    import construct.views.generate as gen_mod
    from construct.views.generate import GenerateReport

    def _fake_generate(install_root):
        return GenerateReport(
            success=True,
            build_id="b-warn",
            validation_errors=[],
            warnings=["demo/cards/x.md: missing frontmatter key"],
            total_files_written=8,
        )

    monkeypatch.setattr(gen_mod, "generate", _fake_generate)
    result = get_registry().get("views.generate_data").handler(
        install_root=_guarded_root(tmp_path)
    )

    assert result.success is True
    assert result.errors == []
    assert "1 content warnings" in result.message
    assert "advisory" in result.message
    assert result.data["warnings"] == ["demo/cards/x.md: missing frontmatter key"]
