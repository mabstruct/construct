"""Unit tests for capability registry and catalog."""
from __future__ import annotations

from pydantic import BaseModel

from construct.capabilities.registry import CapabilityRecord, CapabilityRegistry
from construct.capabilities.catalog import get_registry


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
        "graph.status",
        "views.generate_data",
        "workflow.run",
        "workflow.status",
        "ingest.source",
        "help.suggest",
        "ask.domain",
        "bridge.detect",
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
