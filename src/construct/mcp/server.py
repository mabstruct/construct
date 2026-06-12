"""MCP stdio server with tools auto-registered from the capability registry."""
from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from construct.capabilities.catalog import get_registry
from construct.services.knowledge import OperationResult


def _serialize_result(result: Any) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if hasattr(result, "__dataclass_fields__"):
        return {f: getattr(result, f) for f in result.__dataclass_fields__}
    if isinstance(result, (list, tuple)):
        return {"items": [str(item) for item in result]}
    return {"result": str(result)}


def create_server() -> FastMCP:
    app = FastMCP("construct")

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

    return app


def run_server() -> None:
    """Entry point for `construct mcp` — runs until stdin closes."""
    app = create_server()
    app.run(transport="stdio")
