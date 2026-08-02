"""Loopback HTTP surface over the capability registry (Phase 19).

The third invoke surface, beside ``construct.cli`` and ``construct.mcp``. It adds
no capability vocabulary of its own (HTTP-02): every request reaches a handler
through ``CapabilityRegistry.invoke``, the same seam the other two use, so a
browser can do exactly what the CLI and an MCP agent can do and nothing more.

This package holds only the constants both the server and its callers need.
Importing it must stay free of FastAPI and uvicorn — ``cli.py`` reads
``DEFAULT_API_PORT`` to build ``serve``'s option default, and pulling the ASGI
stack in for a default value is the CLI-startup cost the repo's lazy-import
idiom exists to avoid.
"""
from __future__ import annotations


#: The header carrying the per-launch token.
#:
#: A custom header rather than a query string, deliberately (T-19-08): a
#: query-string token lands in shell history, server access logs and the
#: ``Referer`` sent to any third party the page links to. It also doubles as the
#: CSRF control — ``X-Construct-Token`` is **not** a CORS-safelisted header, so a
#: cross-origin request carrying it must pass a preflight, and no
#: ``CORSMiddleware`` is installed to answer one.
TOKEN_HEADER = "X-Construct-Token"

#: The fixed default port ``construct serve`` binds.
#:
#: Fixed, not ephemeral (D-04): the URL has to be bookmarkable, and stable enough
#: for the Phase 24 verdict playbook to name a literal address. An ephemeral port
#: with auto-open was rejected for exactly that instability. The cost of a fixed
#: default is a collision, which ``serve`` owns with an actionable message rather
#: than a stack trace.
#:
#: 8787 is outside the IANA well-known range, outside the range macOS assigns for
#: ephemeral ports, and not a default of any tool this project already runs
#: (Vite 5173, Streamlit 8501, ``npx serve`` 3000).
DEFAULT_API_PORT = 8787

#: Where the capability envelope route lives. One route, one path parameter —
#: see ``construct.api.app``.
CAPABILITY_ROUTE = "/api/capabilities/{cap_id}"

#: Where ``construct serve`` writes the launch token, relative to the install
#: root, with mode ``0600`` (D-17).
#:
#: A path rather than an ad-hoc string inside ``serve`` because Phase 21 reads
#: this file: a second literal spelled in a second module is how a reader and a
#: writer end up pointing at two different files, and the failure looks like
#: "the UI cannot authenticate" rather than like a typo.
TOKEN_FILE_RELPATH = ".construct/api-token"

__all__ = [
    "CAPABILITY_ROUTE",
    "DEFAULT_API_PORT",
    "TOKEN_FILE_RELPATH",
    "TOKEN_HEADER",
]
