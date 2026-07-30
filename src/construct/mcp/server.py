"""MCP stdio server with tools auto-registered from the capability registry."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from construct.capabilities.catalog import get_registry
from construct.services.knowledge import OperationResult


def _serialize_result(result: Any) -> dict:
    """Project a capability's return value onto a JSON-encodable dict.

    The dataclass branch **recurses** (``asdict``), and that is the whole point.
    A one-level ``{f: getattr(result, f)}`` walk returned ``OperationResult`` with
    its ``errors`` list still holding ``OperationError`` dataclasses;
    ``json.dumps`` then raised inside the caller's own ``try`` and every
    structured failure answered ``{"error": "Object of type OperationError is not
    JSON serializable"}``. That dropped the entire error channel on the MCP
    surface — silently, with a well-formed JSON body — so an agent read a bogus
    reason and could not tell a validation failure from an infrastructure fault.
    The CLI rendered the same capability's reasons correctly, which is exactly
    the cross-surface fork GOV-01 exists to close (CR-01).

    ``json.dumps`` is deliberately left without a ``default=`` fallback: coercing
    an unexpected value with ``str()`` would put filesystem paths into a string
    rendered straight back to an MCP client (T-18-10), so a value this function
    cannot project is a bug to fix here, not one to stringify at the boundary.
    """
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
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
                    result = registry.invoke(capability.id, kwargs)
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
