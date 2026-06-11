"""Contract tests for MCP server tool definitions."""
from __future__ import annotations

from construct.capabilities.catalog import get_registry


def test_mcp_tools_match_registry() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    assert len(mcp_tools) >= 4
    for tool in mcp_tools:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "properties" in tool["input_schema"]


def test_mcp_tool_construct_validate_schema() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    validate_tool = next(t for t in mcp_tools if t["name"] == "construct_validate")
    schema = validate_tool["input_schema"]
    assert "path" in schema["properties"]
    assert schema["properties"]["path"]["type"] == "string"


def test_mcp_tool_count() -> None:
    registry = get_registry()
    mcp_tools = registry.list_mcp_tools()
    tool_names = {t["name"] for t in mcp_tools}
    expected = {
        "construct_validate",
        "construct_create_card",
        "construct_edit_card",
        "construct_add_connection",
        "construct_graph_status",
        "construct_views_generate_data",
        "construct_workflow_run",
        "construct_ingest_source",
        "construct_help_suggest",
        "construct_ask_domain",
        "construct_bridge_detect",
    }
    assert tool_names == expected
