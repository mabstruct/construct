"""The ASGI app: one route, the whole capability registry (HTTP-01, D-05).

The structural claim ``mcp/server.py`` already proves for the MCP surface, made
again here in a different shape. There is **no route generator and no loop over
the registry**: a single ``POST /api/capabilities/{cap_id}`` is what makes every
capability reachable, because the path parameter *is* the capability id. A
capability added to the catalog is reachable over HTTP the moment it is
registered, with no edit to this file — the same property
``test_mcp_server_names_no_capability`` pins on the MCP side.

**D-06 — ``GET /api/capabilities`` advertises the declared contract.** It
iterates the registry, which is *not* the loop D-05 forbids: the forbidden loop
is one that **generates routes**, because that is the thing a new capability
would have to re-run. Iterating the registry to answer a request is data, not
wiring — the route table is unchanged by a registration, and the body it returns
changes by itself. The discovery route is deliberately not a capability route;
``COVERAGE.md`` records it as such (D-20) so a reader can neither count it as a
capability nor meet it as an undocumented surface.

The route body does no validation of its own beyond the D-10 key refusal below.
Validation is the seam's job (GOV-01): ``get_registry().invoke(cap_id, payload)``
resolves the record, resolves ``workspace_id`` (D-01), validates against the
capability's declared ``extra="forbid"`` model, and only then dispatches. An
adapter that re-checked anything the seam checks would be a second contract that
can drift from the first — the fork the seam exists to close (HTTP-02).

**D-10 — the envelope refuses path-shaped payload keys, server-side.** Under
D-05 the payload arrives from the client verbatim, so "the adapter can only ever
emit ``workspace_id``" is not a property a client can hold. Any key in
``PATH_SHAPED_KEYS`` is refused with 422 before dispatch. This is HTTP's trust
boundary declining caller-supplied filesystem paths — HTTP-03's literal wording
— and it is *not* the rejected adapter-side-resolution alternative: resolution
still happens only inside the seam.

**The result and error boundary is not this module's** (HTTP-04). Success bodies
go through ``capabilities/results.py::serialize_result`` — the same function the
MCP surface calls, so the two cannot answer one capability in two shapes — and
every error body goes through ``api/errors.py::error_body``. Neither has a copy
here; a copy is the drift this phase is about.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from construct.api import CAPABILITY_ROUTE
from construct.api.errors import (
    error_body,
    install_error_handlers,
    status_for_seam_error,
)
from construct.api.middleware import LocalhostGuard
from construct.capabilities.catalog import get_registry
from construct.capabilities.errors import CapabilityError
from construct.capabilities.results import sanitize_exception, serialize_result
from construct.capabilities.workspaces import (
    PATH_SHAPED_KEYS,
    set_launch_install_root,
)


#: Where the discovery endpoint lives (D-06).
#:
#: A sibling of ``CAPABILITY_ROUTE``'s prefix rather than a nested path, so no
#: capability id could ever shadow it: ``/api/capabilities`` carries no path
#: parameter and answers ``GET`` only, while every dispatch is a ``POST`` to
#: ``/api/capabilities/{cap_id}``. Named here rather than in ``construct.api``
#: because, unlike the constants there, nothing outside this module and its
#: tests needs it — ``cli.py`` in particular must keep importing ``construct.api``
#: without the ASGI stack.
DISCOVERY_ROUTE = "/api/capabilities"


class Envelope(BaseModel):
    """The one request body shape (D-05).

    ``extra="forbid"``, like every model in this project: an envelope that
    accepted unknown top-level keys would let a caller smuggle fields past the
    single declared ``payload``, and the seam would never see them.

    ``payload`` defaults to an empty dict so a capability whose model is
    all-optional is callable with ``{}`` — the seam already accepts that shape
    (``test_all_optional_model_accepts_an_empty_payload_and_uses_its_defaults``).
    """

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any] = Field(default_factory=dict)


def create_app(install_root: Path, token: str) -> FastAPI:
    """Build the ASGI app for one launch.

    ``install_root`` and ``token`` are **per-launch state**, which is why this is
    a factory and why ``cli.py`` hands uvicorn the returned instance rather than
    an import string: an import string makes uvicorn re-import the module in a
    fresh interpreter, where neither value exists.
    """
    set_launch_install_root(install_root)

    app = FastAPI(
        title="CONSTRUCT",
        description=(
            "Loopback HTTP surface over the capability registry. Every route "
            "dispatches through CapabilityRegistry.invoke — the same seam the "
            "CLI and MCP surfaces use."
        ),
    )
    # No ``allowed_origins`` argument. The guard derives the permitted loopback
    # origins per request from the already-validated ``Host``, so it follows
    # whatever ``--port`` this launch used without being told; the argument is
    # additive and exists for an origin that is genuinely not loopback-derived.
    # Passing the derived set back in was a redundant second spelling of the
    # allowlist — the failure mode of an origin allowlist is silence, and two
    # copies of one is how that silence gets written.
    app.add_middleware(LocalhostGuard, token=token)

    # All four HTTP error emitters answer in one body (HTTP-04). Two of them are
    # the framework's — the envelope's validation rejection and the router's
    # unknown-route 404 — and this is where they stop being the framework's.
    # The third is the guard, which answers before this app and therefore calls
    # ``error_body`` itself; the fourth is the route below.
    install_error_handlers(app, Envelope)

    @app.get(DISCOVERY_ROUTE)
    async def list_capabilities() -> dict:
        """Advertise every registered capability and its declared input schema.

        **Iterated from ``registry.list()``, never from ``list_mcp_tools()``.**
        The MCP projection skips every capability whose ``mcp_tool_name`` is
        ``None`` — six of the twenty-nine today (``knowledge.card.archive``,
        ``knowledge.connection.list``, ``knowledge.connection.remove``,
        ``workflow.status``, ``workspace.init``, ``workspace.status``). Using it
        here would produce a twenty-three-capability surface that still passes a
        set-membership test, because every id it *did* return would be present
        and correct. That is the WR-01 failure mode this phase is built around,
        and the reason the guard in ``tests/contract/test_http_surface.py``
        asserts cardinality against the registry rather than membership.

        **What this recovers.** Phase 18's D-21 had to concede the
        schema-advertising half of GOV-01 upstream: the pinned MCP library
        offers no schema-override parameter, so a capability's declared
        ``input_model`` could not be published to an MCP client. Nothing about
        that limit is inherent to the *contract*; it was a property of one
        library. Here the schema is published directly, so the declared contract
        finally reaches a caller on at least one surface — which is what lets
        the browser build a form from ``model_json_schema()`` the way
        ``ui/capability_runner.py`` already does in-process.

        **The accepted consequence, stated rather than discovered later.**
        Publishing a schema turns it into a *consumed* contract. Changing an
        input model is now a visible break — a form stops rendering the field it
        used to — instead of a quiet one that surfaces as a validation error on
        somebody's next call. That is the trade D-06 accepts on purpose: a break
        a caller can see is worth more than a schema nobody was told about.

        The ordering is ``registry.list()``'s, which sorts by id. Not
        incidental: a browser rendering this list must not reshuffle it between
        two polls, and dict insertion order would make the order depend on
        import sequence rather than on anything a reader can predict.
        """
        return {
            "capabilities": [
                {
                    "id": capability.id,
                    "name": capability.name,
                    "description": capability.description,
                    "input_schema": capability.input_model.model_json_schema(),
                }
                for capability in get_registry().list()
            ]
        }

    @app.post(CAPABILITY_ROUTE)
    async def invoke_capability(cap_id: str, envelope: Envelope) -> Any:
        """Dispatch one capability. The path parameter is the capability id.

        **D-24 — a capability that ran and reported failure is a 200 with its
        result body.** The result envelope separates *the command ran* from *how
        it went*: ``success`` is the second of those, and the CLI turns it into
        an exit code. Phase 11's decision that a degraded curation run exits 0
        is a statement about that separation, not a quirk of one workflow.
        Mapping a reported failure onto a 4xx here would re-fork the contract the
        exit code already encodes — an agent reading this surface would conclude
        the request was malformed when the request was fine and the *workspace*
        was not. So only the seam's own typed errors carry a status
        (``STATUS_FOR_SEAM_ERROR``), and the guard's three pre-dispatch refusals
        keep 400/403/401.
        """
        offending = sorted(set(envelope.payload) & PATH_SHAPED_KEYS)
        if offending:
            raise HTTPException(
                status_code=422,
                detail=(
                    "path-shaped payload keys are refused at the HTTP boundary: "
                    f"{', '.join(offending)} — address a workspace by id with "
                    "'workspace_id' instead"
                ),
            )

        try:
            result = get_registry().invoke(cap_id, envelope.payload)
            # Serialization is inside the guarded region on purpose. A value
            # ``serialize_result`` cannot project raises
            # ``ResultSerializationError``, which is a bug in the boundary
            # rather than a refusal — but letting it propagate would hand the
            # framework's default handler a traceback to render, and this
            # surface answers a browser. A 500 naming the exception class is
            # loud in the log and silent about the environment.
            return serialize_result(result)
        except CapabilityError as exc:
            status = status_for_seam_error(exc)
            if status is None:
                # A seam error class the status map has never been told about.
                # Rendered as unexpected rather than guessed into a 4xx.
                return _unexpected(exc, cap_id)
            # ``str(exc)`` verbatim, and that is the cross-surface contract:
            # the CLI prints this same string after "ERROR " and MCP returns it
            # as ``{"error": ...}``. The seam's reasons are path-free by
            # construction, so no sanitizing step stands between them and the
            # body — one that did would fork the reason (HTTP-04).
            return JSONResponse(status_code=status, content=error_body(str(exc)))
        except Exception as exc:  # noqa: BLE001 — the boundary, deliberately broad
            return _unexpected(exc, cap_id)

    return app


def _unexpected(exc: Exception, cap_id: str) -> Response:
    """Render an unexpected exception as the project's body, at 500.

    Through ``sanitize_exception``, never ``str(exc)``: ``str(OSError)`` embeds
    the absolute path it failed on (T-18-10, M-4) and 14 measured handlers in
    this codebase raise from that family. The sanitizer never reads the
    message at all, so the class of leak is closed structurally rather than by
    a filter that has to be right about every message shape ever raised.

    The capability id is supplied because the sanitized reason is a bare class
    name; without it a caller with two requests in flight cannot tell which one
    broke. The id came from the caller's own URL, so it discloses nothing the
    caller did not already send.
    """
    return JSONResponse(
        status_code=500, content=error_body(sanitize_exception(exc), cap_id)
    )
