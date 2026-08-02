"""MCP stdio server with tools auto-registered from the capability registry."""
from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from construct.capabilities.catalog import get_registry
from construct.capabilities.errors import CapabilityError
from construct.capabilities.results import sanitize_exception, serialize_result


def create_server() -> FastMCP:
    app = FastMCP("construct")

    registry = get_registry()
    for entry in registry.list_mcp_tools():
        cap = registry.get_by_mcp_name(entry["name"])

        def make_handler(capability=cap) -> Any:
            def handler(**kwargs: Any) -> str:
                try:
                    result = registry.invoke(capability.id, kwargs)
                    serialized = serialize_result(result)
                    return json.dumps(serialized, indent=2)
                except CapabilityError as exc:
                    # The seam's typed errors are path-free by construction:
                    # ``CapabilityNotFoundError`` lists capability ids, and
                    # ``CapabilityInputError.from_validation_error`` builds its
                    # reason from field locations and pydantic constraint text
                    # with ``include_input`` and ``include_context`` off
                    # (T-18-10). Rendering their own message is what keeps this
                    # surface's reason identical to the CLI's (GOV-01).
                    return json.dumps({"error": str(exc)})
                except Exception as exc:
                    # M-4: this arm was the last unguarded stringifying arm on a
                    # serialized surface — one bare ``str(exc)`` standing behind
                    # every capability, so any OSError escaping a handler put an
                    # absolute path straight into an MCP body (T-18-10).
                    # ``sanitize_exception`` never reads the message at all.
                    return json.dumps({"error": sanitize_exception(exc)})
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
