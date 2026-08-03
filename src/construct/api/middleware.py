"""The loopback trust boundary — Host, Origin and token, before any dispatch.

HTTP-05 in one class. Everything upstream of ``LocalhostGuard.dispatch``
returning is attacker-controlled: the request arrives over a socket any local
process can open, and — the part that is easy to forget — any *web page* the
user visits can make their browser send a request here.

The control set is **not invented here.** It is the MCP specification's own list
for a local HTTP server — validate ``Origin``, answer 403 when it is present and
invalid, bind loopback, authenticate even locally — published after three
independent DNS-rebinding advisories against MCP SDKs: ``GHSA-w48q-cv73-mx4w``
(TypeScript SDK), ``CVE-2025-66416`` (Python SDK) and ``GHSA-89vp-x53w-74fx``
(rmcp, missing ``Host`` validation). Every one of those was a local server that
was reachable because "it only listens on localhost" was treated as the control
rather than as the deployment shape the controls are needed *for*.

Three checks, in this order (**D-23**), each answering a distinct threat:

1. **Host** (T-19-01, DNS rebinding). An attacker who controls a domain can
   point it at ``127.0.0.1`` and have the victim's browser issue same-origin
   requests to this server. The socket cannot tell that apart from a genuine
   local request — but the ``Host`` header carries the attacker's domain, so
   requiring it to be a loopback literal refuses the rebound request. 400.
2. **Origin** (T-19-12, **D-21**). A cross-origin page's ``fetch`` carries
   ``Origin``. Absent ``Origin`` is *allowed*: ``curl``, the CLI and any
   non-browser client send none, and requiring it would break them for no gain,
   since a browser always sends it cross-origin. 403 — the status the MCP
   specification names for exactly this check, and its exact wording is "if the
   ``Origin`` header is present and invalid".
3. **Token** (T-19-07). ``secrets.compare_digest``, never ``==``: a naive string
   comparison short-circuits on the first differing byte and leaks the token
   prefix through timing. 401.

**D-22 — the token travels in a custom header, never a query string, and no
``CORSMiddleware`` is installed.** With no CORS response headers a browser blocks
every cross-origin *read* of this server, and ``X-Construct-Token`` is not a
CORS-safelisted header, so any cross-origin request carrying it must first pass a
preflight that no policy here answers. The token is therefore also the CSRF
control (T-19-02), which is what lets **D-05**'s single-route JSON envelope make
``Origin`` validation defence in depth rather than the one load-bearing check: a
drive-by *simple* request may only carry ``text/plain``,
``application/x-www-form-urlencoded`` or ``multipart/form-data``, and none of
those reaches a capability with a parsed payload (measured against FastAPI
0.141.1, whose ``strict_content_type`` default also refuses a body sent with no
content type at all; pinned by
``tests/contract/test_http_security.py`` because it is a framework default rather
than something this file enforces). A query-string token, by contrast, would land
in shell history, server access logs and the ``Referer`` header sent to any third
party a page links to (T-19-08).

**Adding a permissive CORS middleware would dismantle exactly that property.**
It is the one edit to this surface that looks like a convenience and is a
vulnerability: it would answer the preflight, make the token header usable
cross-origin, and demote ``Origin`` validation from defence in depth to the sole
remaining check. ``tests/contract/test_http_security.py`` fails if any CORS
middleware appears in the stack.

**No ``TrustedHostMiddleware``, deliberately.** Measured: it never inspects
``Origin``, so it covers only the first of the three checks — and it answers with
a ``PlainTextResponse`` that an exception handler cannot override, which would
give this surface two different error shapes for two refusals of the same
request. Folding the Host check in here is what keeps one shape (D-23).

**This file's blind spot.** A test client sends no ``Origin`` of its own, so an
Origin case that does not set the header *explicitly* proves nothing — it merely
re-tests the absent-Origin path. Every Origin assertion in the contract tests
sets the header, and the absent case asserts that it is absent.
"""
from __future__ import annotations

import secrets
from collections.abc import Iterable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from construct.api import TOKEN_HEADER
from construct.api.errors import error_body


#: The only ``Host`` values this server answers to. ``[::1]`` is the bracketed
#: form a client sends for the IPv6 loopback; the bare ``::1`` never appears in a
#: ``Host`` header because the brackets are what disambiguate it from a port.
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})

#: The scheme a permitted origin carries. Only ``http``: a page served over
#: ``https`` that fetched ``http://127.0.0.1`` would be blocked by the browser as
#: mixed content before this server ever saw it, so an ``https`` loopback origin
#: is not a request shape that exists here.
ALLOWED_ORIGIN_SCHEME = "http"


def allowed_origins(port: str | None = None) -> frozenset[str]:
    """The loopback origins permitted for a given port.

    Derived from ``ALLOWED_HOSTS`` rather than spelled a second time, for the
    same reason ``PATH_SHAPED_KEYS`` is derived from the field maps: a hostname
    added to one list and forgotten in the other is a silent hole, and the
    failure mode of an origin allowlist is silence by construction.

    ``port`` is the port from the request's own ``Host`` header, which by the
    time this is consulted has already been constrained to a loopback literal
    with a numeric port. That is what makes the allowlist follow the **launch
    port**: ``construct serve --port 9000`` puts ``9000`` in every browser's
    ``Host``, so ``http://127.0.0.1:9000`` is permitted without this module
    needing to be told the port, and — the failure this prevents — a non-default
    ``--port`` does not silently make every browser request foreign.

    Deriving from ``Host`` rather than from a constructor argument costs nothing
    in strength. A browser sets ``Origin`` itself and a page cannot forge it; a
    non-browser client can forge it but simply omits it, which D-21 already
    allows. So the value being matched is trustworthy in precisely the case that
    matters, and the port is only ever used to *narrow* which loopback origins
    are accepted for this request.
    """
    if port is None:
        return frozenset(f"{ALLOWED_ORIGIN_SCHEME}://{host}" for host in ALLOWED_HOSTS)
    return frozenset(
        f"{ALLOWED_ORIGIN_SCHEME}://{host}:{port}" for host in ALLOWED_HOSTS
    )


#: The origins permitted when the request's ``Host`` carries no explicit port —
#: i.e. the server is reached on the scheme's default port, which is how a test
#: client and a bare ``http://localhost`` bookmark both address it.
ALLOWED_ORIGINS = allowed_origins()


def _split_host_port(raw: str) -> tuple[str, str | None]:
    """Split a ``Host`` header value into its host and its optional port.

    The split is on the closing bracket when the value is a bracketed IPv6
    literal and on the first colon otherwise. ``"[::1]:8787".split(":", 1)``
    would cut *inside* the address, which is the bug this exists to not have.

    A port that is not a string of digits yields ``None`` for both halves, so
    the caller refuses the request. A malformed authority is not a request shape
    any real client produces, and accepting one would put attacker-controlled
    text into the derived origin set for no reason.
    """
    if raw.startswith("["):
        address, closing, rest = raw.partition("]")
        if not closing:
            return "", None
        host = address + closing
    else:
        host, separator, tail = raw.partition(":")
        rest = separator + tail if separator else ""

    if not rest:
        return host, None
    if not rest.startswith(":"):
        # Only reachable for the bracketed branch: trailing text after the
        # closing bracket that is not a ``:port`` at all.
        return "", None
    port = rest[1:]
    if not port.isdigit():
        return "", None
    return host, port


def _refusal(status_code: int, reason: str) -> JSONResponse:
    """One error shape for every boundary refusal — the shared one.

    Rendered through ``api/errors.py::error_body``, which is the same builder
    the route's typed refusals, the envelope's validation rejection and the
    framework's unknown-route 404 all pass through. That is the concrete
    content of the "``TrustedHostMiddleware`` would give us two shapes"
    objection above, and it only means something if this side actually matches.

    This is the emitter an exception handler cannot reach: the guard answers
    *before* the app, so ``install_error_handlers`` never sees these three
    refusals. Calling the shared builder is the only way they agree, which is
    why the dependency points this way rather than the reverse.

    The reason names the *check*, never the submitted value — the same rule the
    seam's own reason strings follow (T-18-10). Echoing the rejected ``Host`` or
    ``Origin`` back would reflect attacker-controlled text into a response body.
    """
    return JSONResponse(status_code=status_code, content=error_body(reason))


class LocalhostGuard(BaseHTTPMiddleware):
    """Refuse anything that is not a token-bearing loopback request."""

    def __init__(self, app, *, token: str, allowed_origins: Iterable[str] = ()) -> None:
        """``allowed_origins`` is **additional** to the derived loopback set.

        The loopback origins are computed per request from the validated
        ``Host`` (see :func:`allowed_origins`), so a caller that passes nothing
        still gets the right set for whatever ``--port`` this launch used. The
        argument exists for an origin that is genuinely not loopback-derived;
        nothing passes one today, and widening the set stays a visible edit.
        """
        super().__init__(app)
        self.token = token
        self.extra_origins = frozenset(allowed_origins)

    async def dispatch(self, request, call_next):
        host, port = _split_host_port(request.headers.get("host", ""))
        if host not in ALLOWED_HOSTS:
            return _refusal(400, "invalid host")

        origin = request.headers.get("origin")
        if origin is not None and origin not in (
            allowed_origins(port) | self.extra_origins
        ):
            return _refusal(403, "invalid origin")

        supplied = request.headers.get(TOKEN_HEADER.lower(), "")
        # Compared as BYTES. ``compare_digest`` raises ``TypeError`` when either
        # ``str`` carries a non-ASCII code point, and header values reach us
        # latin-1 decoded — so a caller could turn the token check into a 500 by
        # sending one high byte. Encoding first keeps every rejection a 401.
        if not secrets.compare_digest(supplied.encode("utf-8"), self.token.encode("utf-8")):
            return _refusal(401, "missing or invalid token")

        return await call_next(request)
