"""The loopback trust boundary — Host, Origin and token, before any dispatch.

HTTP-05 in one class. Everything upstream of ``LocalhostGuard.dispatch``
returning is attacker-controlled: the request arrives over a socket any local
process can open, and — the part that is easy to forget — any *web page* the
user visits can make their browser send a request here.

Three checks, in this order, each answering a distinct threat:

1. **Host** (T-19-01, DNS rebinding). An attacker who controls a domain can
   point it at ``127.0.0.1`` and have the victim's browser issue same-origin
   requests to this server. The socket cannot tell that apart from a genuine
   local request — but the ``Host`` header carries the attacker's domain, so
   requiring it to be a loopback literal refuses the rebound request. 400.
2. **Origin** (T-19-12). A cross-origin page's ``fetch`` carries ``Origin``.
   Absent ``Origin`` is *allowed*: ``curl``, the CLI and any non-browser client
   send none, and requiring it would break them for no gain, since a browser
   always sends it cross-origin. 403 — the status the MCP specification names
   for exactly this check.
3. **Token** (T-19-07). ``secrets.compare_digest``, never ``==``: a naive string
   comparison short-circuits on the first differing byte and leaks the token
   prefix through timing. 401.

**No ``CORSMiddleware``, deliberately.** With no CORS response headers a browser
blocks every cross-origin *read* of this server, and the non-safelisted
``X-Construct-Token`` forces a preflight no policy answers. Installing permissive
CORS would dismantle the property the single-route envelope shape was chosen for
(T-19-02).

**No ``TrustedHostMiddleware``, deliberately.** It never inspects ``Origin``, so
it covers only the first of the three checks — and it answers with a
``PlainTextResponse`` that an exception handler cannot override, which would give
this surface two different error shapes for two refusals of the same request.
Folding the Host check in here is what keeps one shape.
"""
from __future__ import annotations

import secrets
from collections.abc import Iterable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from construct.api import TOKEN_HEADER


#: The only ``Host`` values this server answers to. ``[::1]`` is the bracketed
#: form a client sends for the IPv6 loopback; the bare ``::1`` never appears in a
#: ``Host`` header because the brackets are what disambiguate it from a port.
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})


def _refusal(status_code: int, reason: str) -> JSONResponse:
    """One error shape for every boundary refusal.

    ``{"detail": ...}`` — the shape FastAPI's own ``HTTPException`` handler
    emits, so a caller parses one body shape whether the request was refused by
    this guard or by the route. That is the concrete content of the
    "``TrustedHostMiddleware`` would give us two shapes" objection above, and it
    only means something if this side actually matches. Plan 19-07 replaces both
    with the shared ``api/errors.py`` body.

    The reason names the *check*, never the submitted value — the same rule the
    seam's own reason strings follow (T-18-10). Echoing the rejected ``Host`` or
    ``Origin`` back would reflect attacker-controlled text into a response body.
    """
    return JSONResponse(status_code=status_code, content={"detail": reason})


class LocalhostGuard(BaseHTTPMiddleware):
    """Refuse anything that is not a token-bearing loopback request."""

    def __init__(self, app, *, token: str, allowed_origins: Iterable[str] = ()) -> None:
        super().__init__(app)
        self.token = token
        self.allowed_origins = frozenset(allowed_origins)

    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "")
        # Strip the port at the FIRST colon. That is correct for ``127.0.0.1:8787``
        # and for ``[::1]:8787`` alike, because the bracketed IPv6 literal keeps
        # its own colons inside the brackets — ``[::1]:8787``.split(":", 1) would
        # cut inside them, so the split is on the closing bracket when present.
        if host.startswith("["):
            host = host.partition("]")[0] + "]"
        else:
            host = host.split(":", 1)[0]
        if host not in ALLOWED_HOSTS:
            return _refusal(400, "invalid host")

        origin = request.headers.get("origin")
        if origin is not None and origin not in self.allowed_origins:
            return _refusal(403, "invalid origin")

        supplied = request.headers.get(TOKEN_HEADER.lower(), "")
        # Compared as BYTES. ``compare_digest`` raises ``TypeError`` when either
        # ``str`` carries a non-ASCII code point, and header values reach us
        # latin-1 decoded — so a caller could turn the token check into a 500 by
        # sending one high byte. Encoding first keeps every rejection a 401.
        if not secrets.compare_digest(supplied.encode("utf-8"), self.token.encode("utf-8")):
            return _refusal(401, "missing or invalid token")

        return await call_next(request)
